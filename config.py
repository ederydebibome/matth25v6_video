"""
Configuration centrale du bot vidéo multilingue.
Projet séparé du bot Matthieu 25:6 (audio) — même style de config, autre repo.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Dossiers (côté VPS)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent

# Dossier où le PC dépose les lots (vidéos + .txt) via SFTP
INCOMING_DIR = Path(os.getenv("INCOMING_DIR") or (BASE_DIR / "data" / "incoming"))

# Dossier de travail temporaire (compression ffmpeg, nettoyé après usage)
TMP_DIR = Path(os.getenv("TMP_DIR") or (BASE_DIR / "data" / "tmp"))

# DB locale du bot (suivi des publications + utilisateurs)
STATE_DB_PATH = Path(os.getenv("STATE_DB_PATH") or (BASE_DIR / "data" / "bot_state.db"))

INCOMING_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)
STATE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "")  # À renseigner dans .env

# Langues avec voix off. "original" est géré à part (pas de voix, effets
# sonores seulement) mais suit le même pipeline de publication.
LANGUAGES = ["fr", "en", "it", "pt", "es", "de", "ru", "zh", "hi", "ar", "ja"]

# Langue source du fichier .txt déposé par l'utilisateur (pas besoin de
# traduction DeepSeek pour celle-ci). Concerne UNIQUEMENT le pipeline de
# contenu vidéo (le .txt est rédigé en français côté production).
SOURCE_TEXT_LANGUAGE = "fr"

# Langue d'UI par défaut quand celle de l'utilisateur est inconnue (pas
# encore choisie). L'anglais, langue internationale, plutôt que le français.
DEFAULT_UI_LANGUAGE = "en"

# Toutes les "clés" de publication (canaux), y compris l'original.
ALL_KEYS = ["original"] + LANGUAGES

# Un canal public par langue + un pour l'original.
# Renseigner dans .env le nom d'utilisateur SANS le @ (ex: CHANNEL_USERNAME_FR=monchannel_fr)
CHANNEL_USERNAMES = {
    "original": os.getenv("CHANNEL_USERNAME_ORIGINAL", ""),
    "fr": os.getenv("CHANNEL_USERNAME_FR", ""),
    "en": os.getenv("CHANNEL_USERNAME_EN", ""),
    "it": os.getenv("CHANNEL_USERNAME_IT", ""),
    "pt": os.getenv("CHANNEL_USERNAME_PT", ""),
    "es": os.getenv("CHANNEL_USERNAME_ES", ""),
    "de": os.getenv("CHANNEL_USERNAME_DE", ""),
    "ru": os.getenv("CHANNEL_USERNAME_RU", ""),
    "zh": os.getenv("CHANNEL_USERNAME_ZH", ""),
    "hi": os.getenv("CHANNEL_USERNAME_HI", ""),
    "ar": os.getenv("CHANNEL_USERNAME_AR", ""),
    "ja": os.getenv("CHANNEL_USERNAME_JA", ""),
}


def chat_id_for(key: str) -> str:
    """chat_id utilisable par l'API Telegram pour un canal public (@username)."""
    return f"@{CHANNEL_USERNAMES[key]}"


def channel_link(key: str, message_id: int) -> str:
    """Lien natif Telegram vers un message précis d'un canal public."""
    return f"https://t.me/{CHANNEL_USERNAMES[key]}/{message_id}"


# Nom affiché (natif) pour chaque langue, utilisé dans les liens croisés et le menu utilisateur.
# "original" est affiché comme "Version originale" (texte en français), la vidéo
# originale n'ayant pas de langue propre.
DISPLAY_NAMES = {
    "original": "Version originale",
    "fr": "Français",
    "en": "English",
    "it": "Italiano",
    "pt": "Português",
    "es": "Español",
    "de": "Deutsch",
    "ru": "Русский",
    "zh": "中文",
    "hi": "हिन्दी",
    "ar": "العربية",
    "ja": "日本語",
}

# ---------------------------------------------------------------------------
# DeepSeek (traduction du .txt uniquement — jamais l'UI du bot)
# ---------------------------------------------------------------------------
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL") or "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL") or "deepseek-chat"

# ---------------------------------------------------------------------------
# Compression vidéo (ffmpeg) — CRF (qualité constante), sans forcer de résolution
# ---------------------------------------------------------------------------
VIDEO_CRF = os.getenv("VIDEO_CRF") or "23"
VIDEO_PRESET = os.getenv("VIDEO_PRESET") or "medium"
AUDIO_BITRATE_VIDEO = os.getenv("AUDIO_BITRATE_VIDEO") or "128k"

# ---------------------------------------------------------------------------
# Limite de taille de fichier (API Bot Telegram standard)
# ---------------------------------------------------------------------------
# Au-delà, l'envoi n'est même pas tenté (voir publisher._publish_video) : un
# message texte (titre + description) est publié à la place, à charge pour un
# opérateur humain d'y attacher la vidéo ensuite.
MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024  # 50 Mo

# ---------------------------------------------------------------------------
# Watcher côté VPS (détection des lots complets déposés dans INCOMING_DIR)
# ---------------------------------------------------------------------------
INCOMING_POLL_SECONDS = int(os.getenv("INCOMING_POLL_SECONDS") or "15")

# Extensions vidéo acceptées en entrée (le PC peut déposer n'importe laquelle
# de ces extensions). La vidéo produite par video_processing.py en sortie,
# elle, est toujours encodée en .mp4.
VIDEO_EXTENSIONS = [".mp4", ".mov", ".mkv", ".avi", ".webm"]


def find_video(directory: Path, stem: str):
    """Cherche <stem><extension> dans directory, quelle que soit l'extension
    parmi VIDEO_EXTENSIONS. Retourne le Path trouvé, ou None si absent."""
    for ext in VIDEO_EXTENSIONS:
        candidate = directory / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    return None


# Fichiers attendus pour qu'un lot "un_nom" soit considéré complet :
#   un_nom.<ext>                (original, sans voix)
#   un_nom.txt                  (titre + description, en français)
#   un_nom_fr.<ext> ... un_nom_ja.<ext>   (une vidéo doublée par langue)
def missing_batch_files(batch_dir: Path, base_name: str) -> list[str]:
    """Retourne la liste des fichiers manquants pour qu'un lot soit complet."""
    missing = []
    if find_video(batch_dir, base_name) is None:
        missing.append(f"{base_name}.<ext>")
    if not (batch_dir / f"{base_name}.txt").exists():
        missing.append(f"{base_name}.txt")
    for lang in LANGUAGES:
        if find_video(batch_dir, f"{base_name}_{lang}") is None:
            missing.append(f"{base_name}_{lang}.<ext>")
    return missing
