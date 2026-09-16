"""
Bot utilisateur : /start -> langue UI -> menu principal -> liste des titres -> envoi.
Les textes affichés viennent uniquement de i18n.py (jamais de DeepSeek).

Menu principal = sélection de la langue de consultation des vidéos, plus deux
boutons toujours présents : changer la langue de l'interface, et s'abonner /
se désabonner de la newsletter (état courant reflété dans le libellé).
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
    """Clavier du menu principal : langues de contenu + changer langue UI +
    dé/réabonnement newsletter (libellé selon l'état actuel de l'utilisateur)."""
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
    """Un seul bouton : c'est en cliquant dessus que le menu principal
    s'affiche (réutilise on_back_to_menu) — pas le menu complet directement
    après chaque message du bot."""
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

    # Crée/mets à jour la ligne utilisateur, PUIS réabonne systématiquement :
    # passer par /start (donc par cet écran) réabonne un utilisateur qui
    # s'était désabonné, comme demandé.
    state_db.set_user_language(user_id, ui_language)
    state_db.set_subscribed(user_id, True)

    # Confirmation d'abonnement (avec le rappel de /quit pour se désabonner),
    # affichée avec le menu principal.
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
    """Bouton "Changer la langue de l'interface" depuis le menu principal."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    ui_language = state_db.get_user_language(user_id) or config.DEFAULT_UI_LANGUAGE
    await query.edit_message_text(
        i18n.t("choose_ui_language", ui_language),
        reply_markup=_language_keyboard("ui_lang"),
    )


async def on_newsletter_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bouton d'abonnement/désabonnement depuis le menu principal : bascule
    l'état, confirme (texte différent selon le sens), puis affiche le bouton
    "Nouvelle demande" — pas le menu complet, comme partout ailleurs après
    une action du bot."""
    query = update.callback_query
    await query.answer()
    action = query.data.split(":", 1)[1]  # "sub" ou "unsub"
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

    # Le menu ne doit pas s'afficher en entier après chaque message du bot
    # (sauf newsletter) : un seul bouton "Nouvelle demande", qui affiche le
    # menu au clic. Nouveau message, jamais une édition de l'ancien (qui
    # resterait, lui, plus haut dans l'historique, au-dessus de la vidéo).
    await context.bot.send_message(
        chat_id=user_id,
        text=i18n.t("new_request_button", ui_language),
        reply_markup=_new_request_keyboard(ui_language),
    )


async def quit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /quit : désabonnement direct de la newsletter."""
    user_id = update.effective_user.id
    ui_language = state_db.get_user_language(user_id) or config.DEFAULT_UI_LANGUAGE
    state_db.set_subscribed(user_id, False)
    await update.message.reply_text(i18n.t("newsletter_unsubscribed", ui_language))
    await update.message.reply_text(
        i18n.t("new_request_button", ui_language),
        reply_markup=_new_request_keyboard(ui_language),
    )


async def on_any_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """N'importe quel message (texte ou autre) hors commande affiche le
    bouton "Nouvelle demande" (le menu s'affiche seulement au clic dessus).
    Si l'utilisateur n'a encore jamais fait /start, on lui montre d'abord le
    choix de la langue de l'interface."""
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
    # Doit être ajouté après les CommandHandler ci-dessus : ~filters.COMMAND
    # exclut déjà /start et /quit, donc l'ordre n'a pas d'incidence, mais on
    # le garde en dernier par convention (handler "attrape-tout").
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, on_any_message))
