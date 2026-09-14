"""
Orchestration complète du traitement d'un lot ("base_name") :
  1. Publie l'original (sans voix) + les 11 langues (traduction DeepSeek pour
     toutes sauf le fr, qui utilise directement le .txt source).
  2. Supprime chaque vidéo/txt du VPS dès qu'il est publié.
  3. Quand les 12 sont publiées, édite chaque légende pour ajouter les liens
     croisés natifs Telegram vers les 11 autres.
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
import video_processing

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
RETRY_DELAYS_SECONDS = (10, 30)


async def _with_retries(coro_fn, *, label: str):
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return await coro_fn()
        except (TimedOut, NetworkError) as exc:
            if attempt == MAX_ATTEMPTS:
                logger.error("%s : échec définitif après %s tentatives (%s)", label, MAX_ATTEMPTS, exc)
                raise
            delay = RETRY_DELAYS_SECONDS[attempt - 1]
            logger.warning("%s : tentative %s/%s échouée (%s), nouvel essai dans %ss...",
                            label, attempt, MAX_ATTEMPTS, exc, delay)
            await asyncio.sleep(delay)


def build_caption_base(title: str, description: str) -> str:
    """Légende SANS les liens croisés : titre en gras + description (HTML)."""
    safe_title = html.escape(title)
    safe_description = html.escape(description) if description else ""
    if safe_description:
        return f"<b>{safe_title}</b>\n\n{safe_description}"
    return f"<b>{safe_title}</b>"


async def _publish_video(bot: Bot, base_name: str, lang_key: str, video_path, title: str, caption_base: str):
    compressed_path = await asyncio.to_thread(
        video_processing.compress_video, video_path, base_name, lang_key
    )
    try:
        chat_id = config.chat_id_for(lang_key)

        async def _do_send():
            with open(compressed_path, "rb") as f:
                return await bot.send_video(
                    chat_id=chat_id,
                    video=f,
                    caption=caption_base,
                    parse_mode="HTML",
                    supports_streaming=True,
                )

        message = await _with_retries(_do_send, label=f"[{lang_key}] publication {base_name}")
        state_db.upsert_published(
            base_name=base_name,
            lang_key=lang_key,
            channel_username=config.CHANNEL_USERNAMES[lang_key],
            message_id=message.message_id,
            title=title,
            caption_base=caption_base,
        )
        return message.message_id
    finally:
        video_processing.cleanup(compressed_path)


def _unlink_video(batch_dir, stem: str):
    """Supprime la vidéo <stem><extension> si elle existe encore (quelle que soit
    l'extension parmi config.VIDEO_EXTENSIONS)."""
    video = config.find_video(batch_dir, stem)
    if video is not None:
        video.unlink()


async def process_batch(bot: Bot, base_name: str, batch_dir):
    """Traite un lot complet déposé dans batch_dir (voir incoming_watcher.py)."""
    original_txt = batch_dir / f"{base_name}.txt"

    title_fr, description_fr = translator.parse_txt(original_txt.read_text(encoding="utf-8"))
    caption_fr = build_caption_base(title_fr, description_fr)

    # 1) Original (sans voix) — utilise le texte français, pas de langue propre.
    if not state_db.get_published(base_name, "original"):
        logger.info("[%s] Publication de l'original...", base_name)
        original_video = config.find_video(batch_dir, base_name)
        await _publish_video(bot, base_name, "original", original_video, title_fr, caption_fr)
    _unlink_video(batch_dir, base_name)

    # 2) Français — même texte, pas de traduction nécessaire.
    if not state_db.get_published(base_name, "fr"):
        logger.info("[%s] Publication FR...", base_name)
        fr_video = config.find_video(batch_dir, f"{base_name}_fr")
        await _publish_video(bot, base_name, "fr", fr_video, title_fr, caption_fr)
    _unlink_video(batch_dir, f"{base_name}_fr")

    # Le .txt source n'est plus nécessaire une fois original + fr publiés.
    if original_txt.exists():
        original_txt.unlink()

    # 3) Les 10 autres langues — traduction DeepSeek à chaque fois.
    for lang in config.LANGUAGES:
        if lang == "fr":
            continue
        if state_db.get_published(base_name, lang):
            continue

        lang_txt = batch_dir / f"{base_name}_{lang}.txt"

        logger.info("[%s] Traduction DeepSeek -> %s...", base_name, lang)
        title, description = await asyncio.to_thread(
            translator.translate_txt, title_fr, description_fr, lang
        )
        lang_txt.write_text(f"TITRE: {title}\nDESCRIPTION: {description}\n", encoding="utf-8")

        caption = build_caption_base(title, description)
        logger.info("[%s] Publication %s...", base_name, lang)
        lang_video = config.find_video(batch_dir, f"{base_name}_{lang}")
        await _publish_video(bot, base_name, lang, lang_video, title, caption)

        _unlink_video(batch_dir, f"{base_name}_{lang}")
        if lang_txt.exists():
            lang_txt.unlink()

    # 4) Si les 12 sont publiées, on ajoute les liens croisés.
    published_map = state_db.get_all_for_base(base_name)
    if len(published_map) == len(config.ALL_KEYS):
        await apply_cross_links(bot, base_name, published_map)
        await notify_subscribers(bot, base_name, published_map)
    else:
        missing = set(config.ALL_KEYS) - set(published_map.keys())
        logger.warning("[%s] Lot incomplet en base après traitement, manque : %s", base_name, missing)


async def apply_cross_links(bot: Bot, base_name: str, published_map: dict = None):
    """Édite chaque légende publiée pour y ajouter la liste des autres langues,
    avec un lien hypertexte natif Telegram caché derrière le nom de la langue."""
    if published_map is None:
        published_map = state_db.get_all_for_base(base_name)

    for lang_key, pv in published_map.items():
        if pv.cross_links_applied:
            continue

        lines = [i18n.CROSS_LINK_INTRO.get(lang_key, i18n.CROSS_LINK_INTRO["en"])]
        for other_key, other_pv in published_map.items():
            if other_key == lang_key:
                continue
            link = config.channel_link(other_key, other_pv.message_id)
            display = html.escape(config.DISPLAY_NAMES[other_key])
            lines.append(f'<a href="{link}">{display}</a>')

        # NB pointant vers la version modifiable (sans voix) : jamais sur le
        # canal "original" lui-même, puisqu'il EST cette version.
        if lang_key != "original":
            original_pv = published_map.get("original")
            if original_pv is not None:
                note = i18n.EDITABLE_VERSION_NOTE.get(lang_key, i18n.EDITABLE_VERSION_NOTE["en"])
                label = html.escape(i18n.EDITABLE_VERSION_LABEL.get(lang_key, i18n.EDITABLE_VERSION_LABEL["en"]))
                editable_link = config.channel_link("original", original_pv.message_id)
                lines.append("")
                lines.append(note)
                lines.append(f'<a href="{editable_link}">{label}</a>')

        full_caption = pv.caption_base + "\n\n" + "\n".join(lines)
        chat_id = config.chat_id_for(lang_key)

        async def _do_edit(chat_id=chat_id, message_id=pv.message_id, caption=full_caption):
            await bot.edit_message_caption(
                chat_id=chat_id,
                message_id=message_id,
                caption=caption,
                parse_mode="HTML",
            )

        try:
            await _with_retries(_do_edit, label=f"[{lang_key}] liens croisés {base_name}")
            state_db.mark_cross_links_applied(base_name, lang_key)
        except Exception:
            logger.exception("[%s] Échec de l'édition des liens croisés pour %s", base_name, lang_key)


async def notify_subscribers(bot: Bot, base_name: str, published_map: dict):
    """Envoie la newsletter à chaque abonné, dans SA langue d'interface : titre +
    description dans cette langue (toujours présente, car la langue d'UI ne
    peut être que l'une des config.LANGUAGES, donc déjà publiée à ce stade ;
    repli défensif sur l'anglais sinon), la liste des liens vers les autres
    langues (noms traduits dans la langue d'interface du destinataire, cf.
    i18n.LANGUAGE_NAMES), puis le NB pointant vers la version modifiable —
    utile si l'abonné veut traduire vers une langue locale ou non prise en
    charge nativement par le bot."""
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
            if other_key == pv.lang_key:
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
            logger.exception("[%s] Échec de l'envoi de la newsletter à %s", base_name, user_id)
