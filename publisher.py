"""
Orchestration complète du traitement d'un lot ("base_name"), en 4 phases :
  1. Traduction (DeepSeek) des 10 langues doublées, écrite dans des .txt
     persistants — résumable : si le .txt existe déjà, on ne retraduit pas.
  2. Compression ffmpeg des 12 vidéos (original + 11 langues) vers un chemin
     déterministe — résumable : si le fichier compressé existe déjà, on ne
     recompresse pas.
  3. Une fois les 12 compressions prêtes, publication groupée des 12, avec
     1 seconde d'écart entre chaque envoi — résumable via published_videos.
  4. Quand les 12 sont publiées : édition des légendes pour ajouter les liens
     croisés natifs Telegram, puis newsletter aux abonnés.

Auto-réparation : si le .txt source (fr) a disparu du disque (lot interrompu
avant la fin), il est reconstruit automatiquement à partir de ce qui est déjà
publié en base (published_videos.title / caption_base de "fr", ou "original"
à défaut) — aucune intervention manuelle nécessaire.

Repli "fichier trop volumineux" : si l'envoi d'une vidéo échoue parce qu'elle
dépasse la limite de l'API Telegram standard (50 Mo), un message texte
(titre + description) est publié à sa place et son message_id enregistré en
base comme si c'était celui de la vidéo — le pipeline (liens croisés,
newsletter) n'en a pas connaissance et continue normalement. Le fichier
source est ensuite supprimé du VPS comme dans le cas normal (le lot ne doit
pas rester bloqué) : c'est à l'opérateur humain de repérer ces publications
"texte seul" et d'éditer le message pour y attacher la vidéo (recompressée
ou envoyée via un serveur d'API local), en dehors du pipeline automatique.
Voir _is_file_too_large_error / _publish_video.
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
PUBLISH_GAP_SECONDS = 1


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


def _description_from_caption(caption_base: str, title: str) -> str:
    """Inverse de build_caption_base() : retire le <b>titre</b> et dé-échappe le HTML."""
    prefix = f"<b>{html.escape(title)}</b>"
    remainder = caption_base[len(prefix):] if caption_base.startswith(prefix) else caption_base
    remainder = remainder.lstrip("\n")
    return html.unescape(remainder) if remainder else ""


def _ensure_source_txt(base_name: str, batch_dir) -> bool:
    """S'assure que <base_name>.txt existe. S'il a disparu (lot interrompu
    par une ancienne version du pipeline qui le supprimait trop tôt), le
    reconstruit à partir de published_videos ("fr", sinon "original").
    Retourne False si impossible (rien en base non plus)."""
    txt_path = batch_dir / f"{base_name}.txt"
    if txt_path.exists():
        return True

    published = state_db.get_all_for_base(base_name)
    source = published.get("fr") or published.get("original")
    if source is None:
        return False

    description = _description_from_caption(source.caption_base, source.title)
    txt_path.write_text(f"TITRE: {source.title}\nDESCRIPTION: {description}\n", encoding="utf-8")
    logger.warning("[%s] .txt source manquant : reconstruit automatiquement depuis la base.", base_name)
    return True


def _unlink_video(batch_dir, stem: str):
    """Supprime la vidéo <stem><extension> si elle existe encore (quelle que soit
    l'extension parmi config.VIDEO_EXTENSIONS)."""
    video = config.find_video(batch_dir, stem)
    if video is not None:
        video.unlink()


def _stem_for(base_name: str, key: str) -> str:
    return base_name if key == "original" else f"{base_name}_{key}"


def _compressed_path_for(base_name: str, key: str):
    return config.TMP_DIR / f"{base_name}_compressed_{key}.mp4"


# Mots-clés cherchés dans le message d'erreur Telegram pour identifier un rejet
# lié à la taille du fichier (soit un 413 HTTP brut sans JSON valide quand pas
# de serveur d'API local, soit le "Bad Request: file is too big" renvoyé par
# l'API standard). Ce n'est pas un code d'erreur structuré côté Telegram, donc
# on reste sur une détection texte, volontairement large.
_SIZE_ERROR_MARKERS = ("too large", "too big", "413", "entity too large")


def _is_file_too_large_error(exc: Exception) -> bool:
    return any(marker in str(exc).lower() for marker in _SIZE_ERROR_MARKERS)


async def _publish_video(bot: Bot, base_name: str, lang_key: str, video_path, title: str, caption_base: str) -> bool:
    """Publie la vidéo. Retourne True si une vraie vidéo a été envoyée.

    Si l'envoi échoue spécifiquement parce que le fichier est trop volumineux
    pour l'API Telegram standard (>50 Mo, cf. _is_file_too_large_error), on
    publie à la place un message texte (titre + description) et on enregistre
    SON message_id en base comme si c'était celui de la vidéo : le pipeline
    (liens croisés, newsletter, phase 4) n'a pas besoin de savoir qu'il s'agit
    d'un repli, seul le message_id compte pour lui. Le fichier source est
    ensuite supprimé normalement par _cleanup_after_publish, comme pour une
    vraie vidéo publiée — c'est à l'opérateur d'éditer le message texte
    manuellement pour y attacher la vidéo par la suite.
    Toute autre erreur est laissée à se propager normalement.
    """
    chat_id = config.chat_id_for(lang_key)

    async def _do_send():
        with open(video_path, "rb") as f:
            return await bot.send_video(
                chat_id=chat_id,
                video=f,
                caption=caption_base,
                parse_mode="HTML",
                supports_streaming=True,
            )

    is_video = True
    try:
        message = await _with_retries(_do_send, label=f"[{lang_key}] publication {base_name}")
    except Exception as exc:
        if not _is_file_too_large_error(exc):
            raise
        is_video = False

        async def _do_send_fallback():
            return await bot.send_message(chat_id=chat_id, text=caption_base, parse_mode="HTML")

        message = await _with_retries(
            _do_send_fallback, label=f"[{lang_key}] publication (repli texte) {base_name}"
        )

    state_db.upsert_published(
        base_name=base_name,
        lang_key=lang_key,
        channel_username=config.CHANNEL_USERNAMES[lang_key],
        message_id=message.message_id,
        title=title,
        caption_base=caption_base,
    )
    return is_video


def _cleanup_after_publish(batch_dir, base_name: str, lang_key: str):
    _unlink_video(batch_dir, _stem_for(base_name, lang_key))
    if lang_key not in ("original", "fr"):
        lang_txt = batch_dir / f"{base_name}_{lang_key}.txt"
        if lang_txt.exists():
            lang_txt.unlink()
    video_processing.cleanup(_compressed_path_for(base_name, lang_key))


async def process_batch(bot: Bot, base_name: str, batch_dir):
    """Traite un lot complet déposé dans batch_dir (voir incoming_watcher.py)."""
    original_txt = batch_dir / f"{base_name}.txt"

    if not _ensure_source_txt(base_name, batch_dir):
        logger.error(
            "[%s] .txt source manquant et rien en base pour le reconstruire — lot bloqué, intervention nécessaire.",
            base_name,
        )
        return

    title_fr, description_fr = translator.parse_txt(original_txt.read_text(encoding="utf-8"))
    caption_fr = build_caption_base(title_fr, description_fr)

    content = {
        "fr": (title_fr, caption_fr),
    }

    # ---- Phase 1 : traduction (résumable) -------------------------------
    for lang in config.LANGUAGES:
        if lang == "fr" or state_db.get_published(base_name, lang):
            continue

        lang_txt = batch_dir / f"{base_name}_{lang}.txt"
        if lang_txt.exists():
            title, description = translator.parse_txt(lang_txt.read_text(encoding="utf-8"))
        else:
            logger.info("[%s] Traduction DeepSeek -> %s...", base_name, lang)
            title, description = await asyncio.to_thread(
                translator.translate_txt, title_fr, description_fr, lang
            )
            lang_txt.write_text(f"TITRE: {title}\nDESCRIPTION: {description}\n", encoding="utf-8")

        content[lang] = (title, build_caption_base(title, description))

    # "original" utilise le texte ANGLAIS (pas français) : c'est la version
    # destinée à être retravaillée par d'autres monteurs.
    if not state_db.get_published(base_name, "original"):
        if "en" in content:
            content["original"] = content["en"]
        else:
            en_published = state_db.get_published(base_name, "en")
            if en_published is None:
                logger.error("[%s] Texte anglais introuvable pour la légende de 'original'.", base_name)
                return
            content["original"] = (en_published.title, en_published.caption_base)

    # ---- Phase 2 : compression de tout le lot (résumable) ---------------
    # "original" n'est JAMAIS compressé : c'est la version destinée à être
    # remontée par d'autres monteurs, elle doit rester en pleine qualité.
    for key in config.ALL_KEYS:
        if state_db.get_published(base_name, key):
            continue  # déjà publié lors d'une tentative précédente

        if key == "original":
            if config.find_video(batch_dir, _stem_for(base_name, key)) is None:
                logger.error("[%s] Vidéo source manquante pour 'original', lot incomplet.", base_name)
                return
            continue

        compressed_path = _compressed_path_for(base_name, key)
        if compressed_path.exists():
            continue  # déjà compressé lors d'une tentative précédente

        source_video = config.find_video(batch_dir, _stem_for(base_name, key))
        if source_video is None:
            logger.error("[%s] Vidéo source manquante pour '%s', lot incomplet.", base_name, key)
            return

        logger.info("[%s] Compression %s...", base_name, key)
        await asyncio.to_thread(video_processing.compress_video_to, source_video, compressed_path)

    # ---- Phase 3 : publication groupée, 1s d'écart -----------------------
    for key in config.ALL_KEYS:
        if state_db.get_published(base_name, key):
            continue

        title, caption = content[key]
        if key == "original":
            video_path = config.find_video(batch_dir, _stem_for(base_name, key))
            if video_path is None:
                logger.error("[%s] Vidéo source manquante pour 'original', lot incomplet.", base_name)
                return
        else:
            video_path = _compressed_path_for(base_name, key)

        logger.info("[%s] Publication %s...", base_name, key)
        await _publish_video(bot, base_name, key, video_path, title, caption)
        _cleanup_after_publish(batch_dir, base_name, key)
        await asyncio.sleep(PUBLISH_GAP_SECONDS)

    # ---- Phase 4 : liens croisés + newsletter, une fois les 12 publiées --
    published_map = state_db.get_all_for_base(base_name)
    if len(published_map) == len(config.ALL_KEYS):
        await apply_cross_links(bot, base_name, published_map)
        await notify_subscribers(bot, base_name, published_map)
        if original_txt.exists():
            original_txt.unlink()
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
