"""
Central configuration for the multilingual video bot.
Separate project from the Matthieu 25:6 (audio) bot — same config style, different repo.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Directories (VPS side)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent

# Directory where the PC drops batches (videos + .txt) via SFTP
INCOMING_DIR = Path(os.getenv("INCOMING_DIR") or (BASE_DIR / "data" / "incoming"))

# Temporary working directory (ffmpeg compression, cleaned up after use)
TMP_DIR = Path(os.getenv("TMP_DIR") or (BASE_DIR / "data" / "tmp"))

# Bot's local DB (tracks publications + users)
STATE_DB_PATH = Path(os.getenv("STATE_DB_PATH") or (BASE_DIR / "data" / "bot_state.db"))

INCOMING_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)
STATE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "")  # To be set in .env

# Languages with voice-over. "original" is handled separately (no voice,
# sound effects only) but follows the same publication pipeline.
LANGUAGES = ["fr", "en", "it", "pt", "es", "de", "ru", "zh", "hi", "ar", "ja"]

# Source language of the .txt file dropped by the user (no DeepSeek
# translation needed for this one). Concerns ONLY the video content
# pipeline (the .txt is written in French on the production side).
SOURCE_TEXT_LANGUAGE = "fr"

# Default UI language when the user's own is unknown (not chosen yet).
# English, as the international language, rather than French.
DEFAULT_UI_LANGUAGE = "en"

# All publication "keys" (channels), including the original.
ALL_KEYS = ["original"] + LANGUAGES

# One public channel per language + one for the original.
# Set the username WITHOUT the @ in .env (e.g. CHANNEL_USERNAME_FR=mychannel_fr)
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
    """chat_id usable by the Telegram API for a public channel (@username)."""
    return f"@{CHANNEL_USERNAMES[key]}"


def channel_link(key: str, message_id: int) -> str:
    """Native Telegram link to a specific message in a public channel."""
    return f"https://t.me/{CHANNEL_USERNAMES[key]}/{message_id}"


# Display name (native script) for each language, used in cross-links and
# the user menu. "original" is displayed as "Version originale" (French
# text), since the original video has no language of its own.
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
# DeepSeek (translation of the .txt only — never the bot's UI)
# ---------------------------------------------------------------------------
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL") or "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL") or "deepseek-chat"

# System prompt sent to DeepSeek for translation (see translator.py).
# ONLY in .env, never hardcoded here (do not version this formula in the
# code). {lang_name} is replaced with the English name of the target
# language (French, Japanese, Arabic...), see DEEPSEEK_LANG_NAMES below.
DEEPSEEK_SYSTEM_PROMPT = os.getenv("DEEPSEEK_SYSTEM_PROMPT", "")

# Language names in English, used only for the DeepSeek translation prompt
# above (DISPLAY_NAMES below is in native script, for the interface
# buttons — a different use case).
DEEPSEEK_LANG_NAMES = {
    "fr": "French",
    "en": "English",
    "it": "Italian",
    "pt": "Portuguese",
    "es": "Spanish",
    "de": "German",
    "ru": "Russian",
    "zh": "Chinese",
    "hi": "Hindi",
    "ar": "Arabic",
    "ja": "Japanese",
}

# ---------------------------------------------------------------------------
# Video compression (ffmpeg) — CRF (constant quality), without forcing a resolution
# ---------------------------------------------------------------------------
VIDEO_CRF = os.getenv("VIDEO_CRF") or "23"
VIDEO_PRESET = os.getenv("VIDEO_PRESET") or "medium"
AUDIO_BITRATE_VIDEO = os.getenv("AUDIO_BITRATE_VIDEO") or "128k"

# ---------------------------------------------------------------------------
# File size limit (standard Telegram Bot API)
# ---------------------------------------------------------------------------
# Beyond this, sending isn't even attempted (see publisher._publish_video): a
# text message (title + description) is published instead, left for a human
# operator to attach the video to afterwards.
MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

# ---------------------------------------------------------------------------
# VPS-side watcher (detects complete batches dropped in INCOMING_DIR)
# ---------------------------------------------------------------------------
INCOMING_POLL_SECONDS = int(os.getenv("INCOMING_POLL_SECONDS") or "15")

# Accepted video extensions on input (the PC can drop any of these
# extensions). The video produced by video_processing.py as output, on
# the other hand, is always encoded as .mp4.
VIDEO_EXTENSIONS = [".mp4", ".mov", ".mkv", ".avi", ".webm"]


def find_video(directory: Path, stem: str):
    """Looks for <stem><extension> in directory, for any extension among
    VIDEO_EXTENSIONS. Returns the Path found, or None if absent."""
    for ext in VIDEO_EXTENSIONS:
        candidate = directory / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    return None


# Files expected for a batch "a_name" to be considered complete:
#   a_name.<ext>                (original, no voice-over)
#   a_name.txt                  (title + description, in French)
#   a_name_fr.<ext> ... a_name_ja.<ext>   (one dubbed video per language)
def missing_batch_files(batch_dir: Path, base_name: str) -> list[str]:
    """Returns the list of missing files for a batch to be complete."""
    missing = []
    if find_video(batch_dir, base_name) is None:
        missing.append(f"{base_name}.<ext>")
    if not (batch_dir / f"{base_name}.txt").exists():
        missing.append(f"{base_name}.txt")
    for lang in LANGUAGES:
        if find_video(batch_dir, f"{base_name}_{lang}") is None:
            missing.append(f"{base_name}_{lang}.<ext>")
    return missing
