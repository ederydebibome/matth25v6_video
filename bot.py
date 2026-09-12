"""
Bot utilisateur : /start -> langue UI -> langue de contenu -> liste des titres -> envoi.
Les textes affichés viennent uniquement de i18n.py (jamais de DeepSeek).
"""
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

import config
import i18n
import state_db

logger = logging.getLogger(__name__)


def _language_keyboard(prefix: str) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(config.DISPLAY_NAMES[lang], callback_data=f"{prefix}:{lang}")
        for lang in config.LANGUAGES
    ]
    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ui_language = state_db.get_user_language(user_id) or config.SOURCE_TEXT_LANGUAGE
    await update.message.reply_text(
        i18n.t("choose_ui_language", ui_language),
        reply_markup=_language_keyboard("ui_lang"),
    )


async def on_ui_language_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ui_language = query.data.split(":", 1)[1]
    state_db.set_user_language(update.effective_user.id, ui_language)

    await query.edit_message_text(
        i18n.t("choose_content_language", ui_language),
        reply_markup=_language_keyboard("content_lang"),
    )


async def on_content_language_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    content_lang = query.data.split(":", 1)[1]

    user_id = update.effective_user.id
    ui_language = state_db.get_user_language(user_id) or config.SOURCE_TEXT_LANGUAGE

    videos = state_db.get_videos_by_language(content_lang)
    if not videos:
        await query.edit_message_text(i18n.t("no_videos_yet", ui_language))
        return

    buttons = [
        [InlineKeyboardButton(v.title, callback_data=f"video:{content_lang}:{v.base_name}")]
        for v in videos
    ]
    buttons.append([InlineKeyboardButton(i18n.t("back_to_menu", ui_language), callback_data="back_to_menu")])

    await query.edit_message_text(
        i18n.t("choose_video", ui_language),
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def on_video_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, content_lang, base_name = query.data.split(":", 2)

    user_id = update.effective_user.id
    ui_language = state_db.get_user_language(user_id) or config.SOURCE_TEXT_LANGUAGE

    video = state_db.get_published(base_name, content_lang)
    if not video:
        await query.edit_message_text(i18n.t("no_videos_yet", ui_language))
        return

    await context.bot.copy_message(
        chat_id=user_id,
        from_chat_id=f"@{video.channel_username}",
        message_id=video.message_id,
    )


async def on_back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    ui_language = state_db.get_user_language(user_id) or config.SOURCE_TEXT_LANGUAGE
    await query.edit_message_text(
        i18n.t("choose_content_language", ui_language),
        reply_markup=_language_keyboard("content_lang"),
    )


def register_handlers(application: Application):
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(on_ui_language_chosen, pattern=r"^ui_lang:"))
    application.add_handler(CallbackQueryHandler(on_content_language_chosen, pattern=r"^content_lang:"))
    application.add_handler(CallbackQueryHandler(on_video_chosen, pattern=r"^video:"))
    application.add_handler(CallbackQueryHandler(on_back_to_menu, pattern=r"^back_to_menu$"))
