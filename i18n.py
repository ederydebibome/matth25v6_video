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
}


def t(key: str, ui_language: str, **kwargs) -> str:
    entry = TEXTS.get(key, {})
    text = entry.get(ui_language) or entry.get(config.SOURCE_TEXT_LANGUAGE, "")
    return text.format(**kwargs) if kwargs else text
