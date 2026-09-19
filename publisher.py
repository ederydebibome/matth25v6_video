"""
Full orchestration of processing one batch ("base_name"), in 3 phases:
  1. Translation (DeepSeek) of the 10 dubbed languages, written to
     persistent .txt files — resumable: if the .txt already exists, it
     isn't retranslated.
  2. Grouped publication of the 12 (original + 11 languages), with a
     1-second gap between each send — resumable via published_videos. The
     videos arrive already compressed in INCOMING_DIR (no compression is
     done by the VPS for now, see video_processing.py).
  3. Once all 12 are published: edit the messages to add the native
     Telegram cross-links, then send the newsletter to subscribers.

Self-healing: if the source .txt (fr) has disappeared from disk (batch
interrupted before the end), it is automatically rebuilt from what's
already published in the DB (published_videos.title / caption_base of
"fr", or "original" as a fallback) — no manual intervention needed.

"File too large" fallback: if a video exceeds config.MAX_UPLOAD_SIZE_BYTES
(the standard Telegram API limit, 50 MB), sending is NOT attempted (no
pointless network round-trip, and waiting wouldn't change its size anyway):
a text message (title + description) is published immediately instead,
whose message_id is recorded in the DB as if it were the video's — the
pipeline (cross-links, newsletter) doesn't need to know it's a fallback,
only the message_id matters to it. The source file is then deleted from the
VPS as in the normal case (the batch must not stay stuck): it's up to a
human operator to spot these "text only" publications (is_video=0 in the
DB) and edit the message to attach the video, outside the automatic
pipeline. See _publish_video.
"""
import asyncio
import html
import logging

from telegram import Bot
from telegram.error import NetworkError, TimedOut

import config
import i18n
import state_db
import translator

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
RETRY_DELAYS_SECONDS = (10, 30)
PUBLISH_GAP_SECONDS = 1


async def _with_retries(coro_fn, *, label: str):
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return await coro_fn()
        except (TimedOut, NetworkError) as exc:
            if attempt == MAX_ATTEMPTS:
                logger.error("%s: final failure after %s attempts (%s)", label, MAX_ATTEMPTS, exc)
                raise
            delay = RETRY_DELAYS_SECONDS[attempt - 1]
            logger.warning("%s: attempt %s/%s failed (%s), retrying in %ss...",
                            label, attempt, MAX_ATTEMPTS, exc, delay)
            await asyncio.sleep(delay)


def build_caption_base(title: str, description: str) -> str:
    """Caption WITHOUT the cross-links: bold title + description (HTML)."""
    safe_title = html.escape(title)
    safe_description = html.escape(description) if description else ""
    if safe_description:
        return f"<b>{safe_title}</b>\n\n{safe_description}"
    return f"<b>{safe_title}</b>"


def _description_from_caption(caption_base: str, title: str) -> str:
    """Inverse of build_caption_base(): strips the <b>title</b> and un-escapes the HTML."""
    prefix = f"<b>{html.escape(title)}</b>"
    remainder = caption_base[len(prefix):] if caption_base.startswith(prefix) else caption_base
    remainder = remainder.lstrip("\n")
    return html.unescape(remainder) if remainder else ""


def _ensure_source_txt(base_name: str, batch_dir) -> bool:
    """Ensures <base_name>.txt exists. If it has disappeared (batch
    interrupted by an older version of the pipeline that deleted it too
    early), rebuilds it from published_videos ("fr", or "original"
    otherwise). Returns False if that's impossible (nothing in the DB either)."""
    txt_path = batch_dir / f"{base_name}.txt"
    if txt_path.exists():
        return True

    published = state_db.get_all_for_base(base_name)
    source = published.get("fr") or published.get("original")
    if source is None:
        return False

    description = _description_from_caption(source.caption_base, source.title)
    txt_path.write_text(f"TITRE: {source.title}\nDESCRIPTION: {description}\n", encoding="utf-8")
    logger.warning("[%s] Missing source .txt: automatically rebuilt from the database.", base_name)
    return True


def _unlink_video(batch_dir, stem: str):
    """Deletes the video <stem><extension> if it still exists (whatever its
    extension among config.VIDEO_EXTENSIONS)."""
    video = config.find_video(batch_dir, stem)
    if video is not None:
        video.unlink()


def _stem_for(base_name: str, key: str) -> str:
    return base_name if key == "original" else f"{base_name}_{key}"


async def _publish_video(bot: Bot, base_name: str, lang_key: str, video_path, title: str, caption_base: str) -> bool:
    """Publishes the video (already compressed upstream, sent as-is).
    Returns True if an actual video was sent, False if the text fallback
    was used.

    If the file exceeds config.MAX_UPLOAD_SIZE_BYTES, sending isn't
    attempted at all (no point uploading a file that will be rejected
    anyway): a text message (title + description) is published
    immediately instead. Its message_id is recorded in the DB in place of
    a video's, with is_video=False — it's up to the operator to edit that
    message afterwards to attach the video.
    If Telegram rejects the send anyway for the same reason (edge case
    where the estimated size was close to the limit), the same fallback applies.
    """
    chat_id = config.chat_id_for(lang_key)
    size = video_path.stat().st_size
    too_large = size > config.MAX_UPLOAD_SIZE_BYTES
    is_video = False

    if too_large:
        logger.warning(
            "[%s] '%s' is %.1f MB (> %.0f MB): video send not attempted, immediate text fallback.",
            base_name, lang_key, size / (1024 * 1024), config.MAX_UPLOAD_SIZE_BYTES / (1024 * 1024),
        )
    else:
        async def _do_send():
            with open(video_path, "rb") as f:
                return await bot.send_video(
                    chat_id=chat_id,
                    video=f,
                    caption=caption_base,
                    parse_mode="HTML",
                    supports_streaming=True,
                )

        try:
            message = await _with_retries(_do_send, label=f"[{lang_key}] publication {base_name}")
            is_video = True
        except Exception as exc:
            if "too large" not in str(exc).lower() and "too big" not in str(exc).lower():
                raise
            logger.warning("[%s] '%s' rejected by Telegram as too large, immediate text fallback.",
                            base_name, lang_key)

    if not is_video:
        async def _do_send_fallback():
            return await bot.send_message(chat_id=chat_id, text=caption_base, parse_mode="HTML")

        message = await _with_retries(
            _do_send_fallback, label=f"[{lang_key}] publication (text fallback) {base_name}"
        )

    state_db.upsert_published(
        base_name=base_name,
        lang_key=lang_key,
        channel_username=config.CHANNEL_USERNAMES[lang_key],
        message_id=message.message_id,
        title=title,
        caption_base=caption_base,
        is_video=is_video,
    )
    return is_video


def _cleanup_after_publish(batch_dir, base_name: str, lang_key: str):
    _unlink_video(batch_dir, _stem_for(base_name, lang_key))
    if lang_key not in ("original", "fr"):
        lang_txt = batch_dir / f"{base_name}_{lang_key}.txt"
        if lang_txt.exists():
            lang_txt.unlink()


async def process_batch(bot: Bot, base_name: str, batch_dir):
    """Processes one complete batch dropped in batch_dir (see incoming_watcher.py)."""
    original_txt = batch_dir / f"{base_name}.txt"

    if not _ensure_source_txt(base_name, batch_dir):
        logger.error(
            "[%s] Missing source .txt and nothing in the DB to rebuild it — batch stuck, manual intervention needed.",
            base_name,
        )
        return

    title_fr, description_fr = translator.parse_txt(original_txt.read_text(encoding="utf-8"))
    caption_fr = build_caption_base(title_fr, description_fr)

    content = {
        "fr": (title_fr, caption_fr),
    }

    # ---- Phase 1: translation (resumable) --------------------------------
    for lang in config.LANGUAGES:
        if lang == "fr" or state_db.get_published(base_name, lang):
            continue

        lang_txt = batch_dir / f"{base_name}_{lang}.txt"
        if lang_txt.exists():
            title, description = translator.parse_txt(lang_txt.read_text(encoding="utf-8"))
        else:
            logger.info("[%s] DeepSeek translation -> %s...", base_name, lang)
            title, description = await asyncio.to_thread(
                translator.translate_txt, title_fr, description_fr, lang
            )
            lang_txt.write_text(f"TITRE: {title}\nDESCRIPTION: {description}\n", encoding="utf-8")

        content[lang] = (title, build_caption_base(title, description))

    # "original" uses the ENGLISH text (not French): it's the version
    # meant to be reworked by other editors.
    if not state_db.get_published(base_name, "original"):
        if "en" in content:
            content["original"] = content["en"]
        else:
            en_published = state_db.get_published(base_name, "en")
            if en_published is None:
                logger.error("[%s] English text not found for the 'original' caption.", base_name)
                return
            content["original"] = (en_published.title, en_published.caption_base)

    # ---- Phase 2: grouped publication, 1s gap -----------------------------
    # The 12 files are already compressed (dropped as-is in batch_dir): no
    # compression happens here.
    for key in config.ALL_KEYS:
        if state_db.get_published(base_name, key):
            continue

        video_path = config.find_video(batch_dir, _stem_for(base_name, key))
        if video_path is None:
            logger.error("[%s] Missing source video for '%s', batch incomplete.", base_name, key)
            return

        title, caption = content[key]
        logger.info("[%s] Publishing %s...", base_name, key)
        await _publish_video(bot, base_name, key, video_path, title, caption)
        _cleanup_after_publish(batch_dir, base_name, key)
        await asyncio.sleep(PUBLISH_GAP_SECONDS)

    # ---- Phase 3: cross-links + newsletter, once all 12 are published ----
    published_map = state_db.get_all_for_base(base_name)
    if len(published_map) == len(config.ALL_KEYS):
        await apply_cross_links(bot, base_name, published_map)
        await notify_subscribers(bot, base_name, published_map)
        if original_txt.exists():
            original_txt.unlink()
    else:
        missing = set(config.ALL_KEYS) - set(published_map.keys())
        logger.warning("[%s] Batch incomplete in the DB after processing, missing: %s", base_name, missing)


async def apply_cross_links(bot: Bot, base_name: str, published_map: dict = None):
    """Edits each published message to add the list of other languages,
    with a native Telegram hyperlink hidden behind the language name.
    "original" is never listed among the other languages (the NB below
    already points to it, no need to list it twice)."""
    if published_map is None:
        published_map = state_db.get_all_for_base(base_name)

    for lang_key, pv in published_map.items():
        if pv.cross_links_applied:
            continue

        lines = [i18n.CROSS_LINK_INTRO.get(lang_key, i18n.CROSS_LINK_INTRO["en"])]
        for other_key, other_pv in published_map.items():
            if other_key in (lang_key, "original"):
                continue
            link = config.channel_link(other_key, other_pv.message_id)
            display = html.escape(config.DISPLAY_NAMES[other_key])
            lines.append(f'<a href="{link}">{display}</a>')

        # NB pointing to the editable (voice-free) version: never on the
        # "original" channel itself, since it IS that version.
        if lang_key != "original":
            original_pv = published_map.get("original")
            if original_pv is not None:
                note = i18n.EDITABLE_VERSION_NOTE.get(lang_key, i18n.EDITABLE_VERSION_NOTE["en"])
                label = html.escape(i18n.EDITABLE_VERSION_LABEL.get(lang_key, i18n.EDITABLE_VERSION_LABEL["en"]))
                editable_link = config.channel_link("original", original_pv.message_id)
                lines.append("")
                lines.append(note)
                lines.append(f'<a href="{editable_link}">{label}</a>')

        full_text = pv.caption_base + "\n\n" + "\n".join(lines)
        chat_id = config.chat_id_for(lang_key)

        if pv.is_video:
            async def _do_edit(chat_id=chat_id, message_id=pv.message_id, caption=full_text):
                await bot.edit_message_caption(
                    chat_id=chat_id,
                    message_id=message_id,
                    caption=caption,
                    parse_mode="HTML",
                )
        else:
            # "File too large" fallback: this is a TEXT message, not a
            # video — edit_message_caption only applies to media, a text
            # message needs edit_message_text.
            async def _do_edit(chat_id=chat_id, message_id=pv.message_id, text=full_text):
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    parse_mode="HTML",
                )

        try:
            await _with_retries(_do_edit, label=f"[{lang_key}] cross-links {base_name}")
            state_db.mark_cross_links_applied(base_name, lang_key)
        except Exception:
            logger.exception("[%s] Failed to edit cross-links for %s", base_name, lang_key)


async def notify_subscribers(bot: Bot, base_name: str, published_map: dict):
    """Sends the newsletter to each subscriber, in THEIR interface language:
    title + description in that language (always present, since the UI
    language can only be one of config.LANGUAGES, so already published at
    this stage; defensive fallback to English otherwise), the list of links
    to the other languages (names translated into the recipient's interface
    language, see i18n.LANGUAGE_NAMES, "original" excluded — already
    covered by the NB), then the NB pointing to the editable version —
    useful if the subscriber wants to translate into a local language or
    one not natively supported by the bot."""
    subscribers = state_db.get_subscribed_users()
    if not subscribers:
        return

    original_pv = published_map.get("original")

    for user_id, ui_language in subscribers:
        pv = published_map.get(ui_language) or published_map.get(config.DEFAULT_UI_LANGUAGE)
        if pv is None:
            continue

        lines = [
            i18n.t("new_video_available_title", ui_language),
            "",
            pv.caption_base,
            "",
            i18n.CROSS_LINK_INTRO.get(ui_language, i18n.CROSS_LINK_INTRO["en"]),
        ]
        for other_key, other_pv in published_map.items():
            if other_key == "original":
                continue
            link = config.channel_link(other_key, other_pv.message_id)
            display = html.escape(i18n.language_name(other_key, ui_language))
            lines.append(f'<a href="{link}">{display}</a>')

        if original_pv is not None:
            note = i18n.EDITABLE_VERSION_NOTE.get(ui_language, i18n.EDITABLE_VERSION_NOTE["en"])
            label = html.escape(i18n.EDITABLE_VERSION_LABEL.get(ui_language, i18n.EDITABLE_VERSION_LABEL["en"]))
            editable_link = config.channel_link("original", original_pv.message_id)
            lines.append("")
            lines.append(note)
            lines.append(f'<a href="{editable_link}">{label}</a>')

        try:
            async def _do_send(user_id=user_id, text="\n".join(lines)):
                await bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")

            await _with_retries(_do_send, label=f"newsletter -> {user_id}")
        except Exception:
            logger.exception("[%s] Failed to send the newsletter to %s", base_name, user_id)
