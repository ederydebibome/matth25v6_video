"""
User-facing bot: /start -> UI language -> main menu -> title list -> send.
All displayed text comes from i18n.py only (never from DeepSeek).

Main menu = video content-language selection, plus two buttons always
present: change interface language, and subscribe/unsubscribe from the
newsletter (current state reflected in the label).
"""
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

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


def _main_menu_keyboard(user_id: int, ui_language: str) -> InlineKeyboardMarkup:
    """Main menu keyboard: content languages + change UI language +
    subscribe/unsubscribe newsletter (label depends on the user's current state)."""
    rows = list(_language_keyboard("content_lang").inline_keyboard)

    rows.append([
        InlineKeyboardButton(i18n.t("change_ui_language_button", ui_language), callback_data="change_ui_lang"),
    ])

    if state_db.is_subscribed(user_id):
        newsletter_button = InlineKeyboardButton(
            i18n.t("unsubscribe_button", ui_language), callback_data="newsletter:unsub"
        )
    else:
        newsletter_button = InlineKeyboardButton(
            i18n.t("resubscribe_button", ui_language), callback_data="newsletter:sub"
        )
    rows.append([newsletter_button])

    return InlineKeyboardMarkup(rows)


def _new_request_keyboard(ui_language: str) -> InlineKeyboardMarkup:
    """A single button: clicking it is what displays the main menu (reuses
    on_back_to_menu) — not the full menu directly after every bot message."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(i18n.t("new_request_button", ui_language), callback_data="back_to_menu")]]
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ui_language = state_db.get_user_language(user_id) or config.DEFAULT_UI_LANGUAGE
    await update.message.reply_text(
        i18n.t("choose_ui_language", ui_language),
        reply_markup=_language_keyboard("ui_lang"),
    )


async def on_ui_language_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ui_language = query.data.split(":", 1)[1]
    user_id = update.effective_user.id

    # Create/update the user row, THEN always resubscribe: going through
    # /start (and therefore this screen) resubscribes a user who had
    # unsubscribed, as requested.
    state_db.set_user_language(user_id, ui_language)
    state_db.set_subscribed(user_id, True)

    # Subscription confirmation (with the /quit reminder to unsubscribe),
    # shown together with the main menu.
    menu_text = (
        i18n.t("choose_content_language", ui_language)
        + "\n\n"
        + i18n.t("start_subscribed_notice", ui_language)
    )
    await query.edit_message_text(
        menu_text,
        reply_markup=_main_menu_keyboard(user_id, ui_language),
    )


async def on_change_ui_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """"Change interface language" button from the main menu."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    ui_language = state_db.get_user_language(user_id) or config.DEFAULT_UI_LANGUAGE
    await query.edit_message_text(
        i18n.t("choose_ui_language", ui_language),
        reply_markup=_language_keyboard("ui_lang"),
    )


async def on_newsletter_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Subscribe/unsubscribe button from the main menu: toggles the state,
    confirms (different text depending on direction), then shows the
    "New request" button — not the full menu, like everywhere else after
    a bot action."""
    query = update.callback_query
    await query.answer()
    action = query.data.split(":", 1)[1]  # "sub" or "unsub"
    user_id = update.effective_user.id
    ui_language = state_db.get_user_language(user_id) or config.DEFAULT_UI_LANGUAGE

    state_db.set_subscribed(user_id, action == "sub")

    confirmation_key = "newsletter_subscribed" if action == "sub" else "newsletter_unsubscribed"
    await query.edit_message_text(
        i18n.t(confirmation_key, ui_language),
        reply_markup=_new_request_keyboard(ui_language),
    )


async def on_content_language_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    content_lang = query.data.split(":", 1)[1]

    user_id = update.effective_user.id
    ui_language = state_db.get_user_language(user_id) or config.DEFAULT_UI_LANGUAGE

    videos = state_db.get_videos_by_language(content_lang)
    if not videos:
        await query.edit_message_text(
            i18n.t("no_videos_yet", ui_language),
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(i18n.t("back_to_menu", ui_language), callback_data="back_to_menu")]]
            ),
        )
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
    ui_language = state_db.get_user_language(user_id) or config.DEFAULT_UI_LANGUAGE

    video = state_db.get_published(base_name, content_lang)
    if not video:
        await query.edit_message_text(i18n.t("no_videos_yet", ui_language))
        return

    await context.bot.copy_message(
        chat_id=user_id,
        from_chat_id=f"@{video.channel_username}",
        message_id=video.message_id,
    )

    # The menu must not appear in full after every bot message (except the
    # newsletter): just a single "New request" button, which shows the menu
    # on click. Always a new message, never an edit of the old one (which
    # would stay higher up in the history, above the video).
    await context.bot.send_message(
        chat_id=user_id,
        text=i18n.t("new_request_button", ui_language),
        reply_markup=_new_request_keyboard(ui_language),
    )


async def quit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/quit command: direct newsletter unsubscription."""
    user_id = update.effective_user.id
    ui_language = state_db.get_user_language(user_id) or config.DEFAULT_UI_LANGUAGE
    state_db.set_subscribed(user_id, False)
    await update.message.reply_text(i18n.t("newsletter_unsubscribed", ui_language))
    await update.message.reply_text(
        i18n.t("new_request_button", ui_language),
        reply_markup=_new_request_keyboard(ui_language),
    )


async def on_any_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Any message (text or other) other than a command shows the
    "New request" button (the menu only appears on click). If the user has
    never done /start yet, show the interface language choice first."""
    if update.message is None:
        return

    user_id = update.effective_user.id
    ui_language = state_db.get_user_language(user_id)

    if ui_language is None:
        await update.message.reply_text(
            i18n.t("choose_ui_language", config.DEFAULT_UI_LANGUAGE),
            reply_markup=_language_keyboard("ui_lang"),
        )
        return

    await update.message.reply_text(
        i18n.t("new_request_button", ui_language),
        reply_markup=_new_request_keyboard(ui_language),
    )


async def on_back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    ui_language = state_db.get_user_language(user_id) or config.DEFAULT_UI_LANGUAGE
    await query.edit_message_text(
        i18n.t("choose_content_language", ui_language),
        reply_markup=_main_menu_keyboard(user_id, ui_language),
    )


def register_handlers(application: Application):
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("quit", quit_cmd))
    application.add_handler(CallbackQueryHandler(on_ui_language_chosen, pattern=r"^ui_lang:"))
    application.add_handler(CallbackQueryHandler(on_change_ui_language, pattern=r"^change_ui_lang$"))
    application.add_handler(CallbackQueryHandler(on_content_language_chosen, pattern=r"^content_lang:"))
    application.add_handler(CallbackQueryHandler(on_video_chosen, pattern=r"^video:"))
    application.add_handler(CallbackQueryHandler(on_back_to_menu, pattern=r"^back_to_menu$"))
    application.add_handler(CallbackQueryHandler(on_newsletter_toggle, pattern=r"^newsletter:"))
    # Must be added after the CommandHandlers above: ~filters.COMMAND already
    # excludes /start and /quit, so the order doesn't actually matter, but
    # it's kept last by convention (catch-all handler).
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, on_any_message))
