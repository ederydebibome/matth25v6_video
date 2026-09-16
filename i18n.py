"""
Traductions des textes de l'interface du bot ET de la phrase d'introduction
des liens croisés dans les légendes. Ce sont des textes STATIQUES, écrits une
fois pour toutes ici — jamais générés par DeepSeek (qui ne sert qu'au contenu
titre/description des vidéos, cf. translator.py).
"""
import config

# Phrase affichée avant la liste des langues disponibles, dans la langue de CHAQUE canal.
# Le canal "original" utilise la phrase française (pas de langue propre).
CROSS_LINK_INTRO = {
    "original": "Cette vidéo est aussi disponible en :",
    "fr": "Cette vidéo est aussi disponible en :",
    "en": "This video is also available in:",
    "it": "Questo video è disponibile anche in:",
    "pt": "Este vídeo também está disponível em:",
    "es": "Este vídeo también está disponible en:",
    "de": "Dieses Video ist auch verfügbar auf:",
    "ru": "Это видео также доступно на:",
    "zh": "这段视频还提供以下语言版本：",
    "hi": "यह वीडियो इन भाषाओं में भी उपलब्ध है:",
    "ar": "هذا الفيديو متاح أيضًا باللغات التالية:",
    "ja": "この動画は以下の言語でもご覧いただけます：",
}

# Note affichée dans la légende de chaque canal doublé (jamais sur "original",
# qui EST la version modifiable), expliquant l'existence de la version
# modifiable/sans voix, pour qui voudrait la traduire dans une autre langue.
# Traduction idiomatique par langue plutôt que littérale (ex. "NB" devient
# "Hinweis" en allemand, "Примечание" en russe, etc. — jamais de tiret cadratin).
EDITABLE_VERSION_NOTE = {
    "fr": "NB : cette vidéo est aussi disponible dans une version modifiable, pour celles et ceux qui souhaitent la traduire dans une autre langue.",
    "en": "Note: this video is also available in an editable version, for anyone who would like to translate it into another language.",
    "it": "N.B.: questo video è disponibile anche in una versione modificabile, per chi desidera tradurlo in un'altra lingua.",
    "pt": "Nota: este vídeo também está disponível numa versão editável, para quem quiser traduzi-lo para outro idioma.",
    "es": "Nota: este vídeo también está disponible en una versión editable, para quienes quieran traducirlo a otro idioma.",
    "de": "Hinweis: Dieses Video ist auch in einer bearbeitbaren Version verfügbar, für alle, die es in eine andere Sprache übersetzen möchten.",
    "ru": "Примечание: это видео также доступно в редактируемой версии для тех, кто хочет перевести его на другой язык.",
    "zh": "备注：本视频也提供可编辑版本，方便有需要翻译成其他语言的用户使用。",
    "hi": "टिप्पणी: यह वीडियो एक संपादन योग्य संस्करण में भी उपलब्ध है, उन लोगों के लिए जो इसे किसी अन्य भाषा में अनुवाद करना चाहते हैं।",
    "ar": "ملاحظة: يتوفر هذا الفيديو أيضًا بنسخة قابلة للتعديل، لمن يريد ترجمته إلى لغة أخرى.",
    "ja": "備考:この動画は編集可能なバージョンでもご覧いただけます。他の言語に翻訳したい方はご利用ください。",
}

# Libellé du lien hypertexte natif pointant vers le canal "original".
EDITABLE_VERSION_LABEL = {
    "fr": "Version modifiable",
    "en": "Editable version",
    "it": "Versione modificabile",
    "pt": "Versão editável",
    "es": "Versión editable",
    "de": "Bearbeitbare Version",
    "ru": "Редактируемая версия",
    "zh": "可编辑版本",
    "hi": "संपादन योग्य संस्करण",
    "ar": "نسخة قابلة للتعديل",
    "ja": "編集可能なバージョン",
}

# Nom de chaque langue (clé de canal), traduit dans CHAQUE langue d'interface
# possible. Contrairement à config.DISPLAY_NAMES (toujours en forme native,
# ex. "Deutsch"), ceci sert à afficher "Allemand"/"German"/"Alemão"... selon
# la langue d'interface du destinataire (utilisé dans la newsletter).
LANGUAGE_NAMES = {
    "fr": {
        "original": "Version originale", "fr": "Français", "en": "Anglais", "it": "Italien",
        "pt": "Portugais", "es": "Espagnol", "de": "Allemand", "ru": "Russe",
        "zh": "Chinois", "hi": "Hindi", "ar": "Arabe", "ja": "Japonais",
    },
    "en": {
        "original": "Original version", "fr": "French", "en": "English", "it": "Italian",
        "pt": "Portuguese", "es": "Spanish", "de": "German", "ru": "Russian",
        "zh": "Chinese", "hi": "Hindi", "ar": "Arabic", "ja": "Japanese",
    },
    "it": {
        "original": "Versione originale", "fr": "Francese", "en": "Inglese", "it": "Italiano",
        "pt": "Portoghese", "es": "Spagnolo", "de": "Tedesco", "ru": "Russo",
        "zh": "Cinese", "hi": "Hindi", "ar": "Arabo", "ja": "Giapponese",
    },
    "pt": {
        "original": "Versão original", "fr": "Francês", "en": "Inglês", "it": "Italiano",
        "pt": "Português", "es": "Espanhol", "de": "Alemão", "ru": "Russo",
        "zh": "Chinês", "hi": "Hindi", "ar": "Árabe", "ja": "Japonês",
    },
    "es": {
        "original": "Versión original", "fr": "Francés", "en": "Inglés", "it": "Italiano",
        "pt": "Portugués", "es": "Español", "de": "Alemán", "ru": "Ruso",
        "zh": "Chino", "hi": "Hindi", "ar": "Árabe", "ja": "Japonés",
    },
    "de": {
        "original": "Originalversion", "fr": "Französisch", "en": "Englisch", "it": "Italienisch",
        "pt": "Portugiesisch", "es": "Spanisch", "de": "Deutsch", "ru": "Russisch",
        "zh": "Chinesisch", "hi": "Hindi", "ar": "Arabisch", "ja": "Japanisch",
    },
    "ru": {
        "original": "Оригинальная версия", "fr": "Французский", "en": "Английский", "it": "Итальянский",
        "pt": "Португальский", "es": "Испанский", "de": "Немецкий", "ru": "Русский",
        "zh": "Китайский", "hi": "Хинди", "ar": "Арабский", "ja": "Японский",
    },
    "zh": {
        "original": "原始版本", "fr": "法语", "en": "英语", "it": "意大利语",
        "pt": "葡萄牙语", "es": "西班牙语", "de": "德语", "ru": "俄语",
        "zh": "中文", "hi": "印地语", "ar": "阿拉伯语", "ja": "日语",
    },
    "hi": {
        "original": "मूल संस्करण", "fr": "फ़्रेंच", "en": "अंग्रेज़ी", "it": "इटैलियन",
        "pt": "पॉर्चुगीज़", "es": "स्पैनिश", "de": "जर्मन", "ru": "रूसी",
        "zh": "चीनी", "hi": "हिन्दी", "ar": "अरबी", "ja": "जापानी",
    },
    "ar": {
        "original": "النسخة الأصلية", "fr": "الفرنسية", "en": "الإنجليزية", "it": "الإيطالية",
        "pt": "البرتغالية", "es": "الإسبانية", "de": "الألمانية", "ru": "الروسية",
        "zh": "الصينية", "hi": "الهندية", "ar": "العربية", "ja": "اليابانية",
    },
    "ja": {
        "original": "オリジナル版", "fr": "フランス語", "en": "英語", "it": "イタリア語",
        "pt": "ポルトガル語", "es": "スペイン語", "de": "ドイツ語", "ru": "ロシア語",
        "zh": "中国語", "hi": "ヒンディー語", "ar": "アラビア語", "ja": "日本語",
    },
}


def language_name(lang_key: str, ui_language: str) -> str:
    """Nom de lang_key, traduit dans ui_language (repli sur config.DISPLAY_NAMES)."""
    return LANGUAGE_NAMES.get(ui_language, {}).get(lang_key) or config.DISPLAY_NAMES[lang_key]


TEXTS = {
    "choose_ui_language": {
        "fr": "Bonjour ! Choisissez la langue de l'interface :",
        "en": "Welcome! Choose the interface language:",
        "it": "Benvenuto! Scegli la lingua dell'interfaccia:",
        "pt": "Bem-vindo! Escolha o idioma da interface:",
        "es": "¡Bienvenido! Elige el idioma de la interfaz:",
        "de": "Willkommen! Wähle die Sprache der Oberfläche:",
        "ru": "Добро пожаловать! Выберите язык интерфейса:",
        "zh": "你好！请选择界面语言：",
        "hi": "नमस्ते! कृपया इंटरफ़ेस की भाषा चुनें:",
        "ar": "مرحبًا! اختر لغة الواجهة:",
        "ja": "こんにちは！インターフェースの言語を選択してください：",
    },
    "choose_content_language": {
        "fr": "Dans quelle langue veux-tu consulter les vidéos ?",
        "en": "In which language would you like to browse the videos?",
        "it": "In quale lingua vuoi consultare i video?",
        "pt": "Em que idioma deseja consultar os vídeos?",
        "es": "¿En qué idioma deseas consultar los vídeos?",
        "de": "In welcher Sprache möchtest du die Videos ansehen?",
        "ru": "На каком языке вы хотите смотреть видео?",
        "zh": "您想以哪种语言观看视频？",
        "hi": "आप किस भाषा में वीडियो देखना चाहेंगे?",
        "ar": "بأي لغة تريد مشاهدة الفيديوهات؟",
        "ja": "どの言語で動画をご覧になりますか？",
    },
    "choose_video": {
        "fr": "Sélectionne une vidéo :",
        "en": "Select a video:",
        "it": "Seleziona un video:",
        "pt": "Selecione um vídeo:",
        "es": "Selecciona un vídeo:",
        "de": "Wähle ein Video:",
        "ru": "Выберите видео:",
        "zh": "请选择一个视频：",
        "hi": "एक वीडियो चुनें:",
        "ar": "اختر فيديو:",
        "ja": "動画を選択してください：",
    },
    "no_videos_yet": {
        "fr": "Aucune vidéo disponible dans cette langue pour le moment.",
        "en": "No videos available in this language yet.",
        "it": "Nessun video disponibile in questa lingua per ora.",
        "pt": "Nenhum vídeo disponível neste idioma por enquanto.",
        "es": "Todavía no hay vídeos disponibles en este idioma.",
        "de": "Noch keine Videos in dieser Sprache verfügbar.",
        "ru": "Пока нет доступных видео на этом языке.",
        "zh": "目前该语言暂无可用视频。",
        "hi": "फ़िलहाल इस भाषा में कोई वीडियो उपलब्ध नहीं है।",
        "ar": "لا توجد فيديوهات متاحة بهذه اللغة حاليًا.",
        "ja": "現在、この言語で利用できる動画はありません。",
    },
    "sending_video": {
        "fr": "Envoi de la vidéo en cours...",
        "en": "Sending the video...",
        "it": "Invio del video in corso...",
        "pt": "Enviando o vídeo...",
        "es": "Enviando el vídeo...",
        "de": "Video wird gesendet...",
        "ru": "Отправка видео...",
        "zh": "正在发送视频…",
        "hi": "वीडियो भेजा जा रहा है...",
        "ar": "جارٍ إرسال الفيديو...",
        "ja": "動画を送信しています…",
    },
    "video_sent": {
        "fr": "✅ Vidéo envoyée.",
        "en": "✅ Video sent.",
        "it": "✅ Video inviato.",
        "pt": "✅ Vídeo enviado.",
        "es": "✅ Vídeo enviado.",
        "de": "✅ Video gesendet.",
        "ru": "✅ Видео отправлено.",
        "zh": "✅ 视频已发送。",
        "hi": "✅ वीडियो भेज दिया गया है।",
        "ar": "✅ تم إرسال الفيديو.",
        "ja": "✅ 動画を送信しました。",
    },
    "back_to_menu": {
        "fr": "⬅️ Menu principal",
        "en": "⬅️ Main menu",
        "it": "⬅️ Menu principale",
        "pt": "⬅️ Menu principal",
        "es": "⬅️ Menú principal",
        "de": "⬅️ Hauptmenü",
        "ru": "⬅️ Главное меню",
        "zh": "⬅️ 主菜单",
        "hi": "⬅️ मुख्य मेनू",
        "ar": "⬅️ القائمة الرئيسية",
        "ja": "⬅️ メインメニュー",
    },
    "new_request_button": {
        "fr": "🔄 Nouvelle demande",
        "en": "🔄 New request",
        "it": "🔄 Nuova richiesta",
        "pt": "🔄 Novo pedido",
        "es": "🔄 Nueva solicitud",
        "de": "🔄 Neue Anfrage",
        "ru": "🔄 Новый запрос",
        "zh": "🔄 新请求",
        "hi": "🔄 नया अनुरोध",
        "ar": "🔄 طلب جديد",
        "ja": "🔄 新しいリクエスト",
    },
    "new_video_available_title": {
        "fr": "🎬 Nouvelle vidéo disponible !",
        "en": "🎬 New video available!",
        "it": "🎬 Nuovo video disponibile!",
        "pt": "🎬 Novo vídeo disponível!",
        "es": "🎬 ¡Nuevo vídeo disponible!",
        "de": "🎬 Neues Video verfügbar!",
        "ru": "🎬 Доступно новое видео!",
        "zh": "🎬 新视频已发布！",
        "hi": "🎬 नया वीडियो उपलब्ध है!",
        "ar": "🎬 فيديو جديد متاح!",
        "ja": "🎬 新しい動画が公開されました！",
    },
    "newsletter_subscribed": {
        "fr": "🔔 Tu es abonné(e) à la newsletter : tu seras averti(e) dès qu'une nouvelle vidéo est disponible.",
        "en": "🔔 You're subscribed to the newsletter: you'll be notified as soon as a new video is available.",
        "it": "🔔 Sei iscritto/a alla newsletter: sarai avvisato/a non appena un nuovo video è disponibile.",
        "pt": "🔔 Você está inscrito(a) na newsletter: será avisado(a) assim que um novo vídeo estiver disponível.",
        "es": "🔔 Estás suscrito/a al boletín: se te avisará en cuanto haya un nuevo vídeo disponible.",
        "de": "🔔 Du bist für den Newsletter angemeldet: du wirst benachrichtigt, sobald ein neues Video verfügbar ist.",
        "ru": "🔔 Вы подписаны на рассылку: вы получите уведомление, как только появится новое видео.",
        "zh": "🔔 您已订阅新闻推送：新视频发布后会立即通知您。",
        "hi": "🔔 आप न्यूज़लेटर के लिए सदस्यता ले चुके हैं: नया वीडियो उपलब्ध होते ही आपको सूचित किया जाएगा।",
        "ar": "🔔 أنت مشترك في النشرة الإخبارية: سيتم إعلامك فور توفر فيديو جديد.",
        "ja": "🔔 ニュースレターに登録済みです。新しい動画が公開されるとお知らせします。",
    },
    "newsletter_unsubscribed": {
        "fr": "🔕 Tu es désabonné(e). Tu ne recevras plus de notification pour les nouvelles vidéos.",
        "en": "🔕 You're unsubscribed. You won't receive notifications for new videos anymore.",
        "it": "🔕 Ti sei disiscritto/a. Non riceverai più notifiche per i nuovi video.",
        "pt": "🔕 Você cancelou a inscrição. Não receberá mais notificações de novos vídeos.",
        "es": "🔕 Te has dado de baja. Ya no recibirás notificaciones de nuevos vídeos.",
        "de": "🔕 Du bist abgemeldet. Du erhältst keine Benachrichtigungen mehr für neue Videos.",
        "ru": "🔕 Вы отписались. Вы больше не будете получать уведомления о новых видео.",
        "zh": "🔕 您已取消订阅，将不再收到新视频通知。",
        "hi": "🔕 आपने सदस्यता समाप्त कर दी है। अब आपको नए वीडियो की सूचना नहीं मिलेगी।",
        "ar": "🔕 لقد ألغيت الاشتراك. لن تتلقى إشعارات بالفيديوهات الجديدة بعد الآن.",
        "ja": "🔕 登録を解除しました。今後、新しい動画の通知は届きません。",
    },
    "unsubscribe_button": {
        "fr": "🔕 Se désabonner",
        "en": "🔕 Unsubscribe",
        "it": "🔕 Disiscriviti",
        "pt": "🔕 Cancelar inscrição",
        "es": "🔕 Darse de baja",
        "de": "🔕 Abmelden",
        "ru": "🔕 Отписаться",
        "zh": "🔕 取消订阅",
        "hi": "🔕 सदस्यता समाप्त करें",
        "ar": "🔕 إلغاء الاشتراك",
        "ja": "🔕 登録解除",
    },
    "resubscribe_button": {
        "fr": "🔔 Se réabonner",
        "en": "🔔 Resubscribe",
        "it": "🔔 Iscriviti di nuovo",
        "pt": "🔔 Inscrever-se novamente",
        "es": "🔔 Volver a suscribirse",
        "de": "🔔 Erneut anmelden",
        "ru": "🔔 Подписаться снова",
        "zh": "🔔 重新订阅",
        "hi": "🔔 फिर से सदस्यता लें",
        "ar": "🔔 إعادة الاشتراك",
        "ja": "🔔 再登録",
    },
    "start_subscribed_notice": {
        "fr": "🔔 Tu es abonné(e) à la newsletter : tu seras averti(e) dès qu'une nouvelle vidéo est disponible. Envoie /quit à tout moment pour te désabonner.",
        "en": "🔔 You're subscribed to the newsletter: you'll be notified as soon as a new video is available. Send /quit at any time to unsubscribe.",
        "it": "🔔 Sei iscritto/a alla newsletter: sarai avvisato/a non appena un nuovo video è disponibile. Invia /quit in qualsiasi momento per disiscriverti.",
        "pt": "🔔 Você está inscrito(a) na newsletter: será avisado(a) assim que um novo vídeo estiver disponível. Envie /quit a qualquer momento para cancelar a inscrição.",
        "es": "🔔 Estás suscrito/a al boletín: se te avisará en cuanto haya un nuevo vídeo disponible. Envía /quit en cualquier momento para darte de baja.",
        "de": "🔔 Du bist für den Newsletter angemeldet: du wirst benachrichtigt, sobald ein neues Video verfügbar ist. Sende jederzeit /quit, um dich abzumelden.",
        "ru": "🔔 Вы подписаны на рассылку: вы получите уведомление, как только появится новое видео. Отправьте /quit в любой момент, чтобы отписаться.",
        "zh": "🔔 您已订阅新闻推送：新视频发布后会立即通知您。随时发送 /quit 即可取消订阅。",
        "hi": "🔔 आप न्यूज़लेटर के लिए सदस्यता ले चुके हैं: नया वीडियो उपलब्ध होते ही आपको सूचित किया जाएगा। सदस्यता समाप्त करने के लिए किसी भी समय /quit भेजें।",
        "ar": "🔔 أنت مشترك في النشرة الإخبارية: سيتم إعلامك فور توفر فيديو جديد. أرسل /quit في أي وقت لإلغاء الاشتراك.",
        "ja": "🔔 ニュースレターに登録済みです。新しい動画が公開されるとお知らせします。登録を解除するには、いつでも /quit を送信してください。",
    },
    "change_ui_language_button": {
        "fr": "🌐 Changer la langue de l'interface",
        "en": "🌐 Change interface language",
        "it": "🌐 Cambia lingua dell'interfaccia",
        "pt": "🌐 Alterar idioma da interface",
        "es": "🌐 Cambiar idioma de la interfaz",
        "de": "🌐 Sprache der Oberfläche ändern",
        "ru": "🌐 Изменить язык интерфейса",
        "zh": "🌐 更改界面语言",
        "hi": "🌐 इंटरफ़ेस की भाषा बदलें",
        "ar": "🌐 تغيير لغة الواجهة",
        "ja": "🌐 インターフェースの言語を変更",
    },
}


def t(key: str, ui_language: str, **kwargs) -> str:
    entry = TEXTS.get(key, {})
    text = entry.get(ui_language) or entry.get(config.DEFAULT_UI_LANGUAGE, "")
    return text.format(**kwargs) if kwargs else text
