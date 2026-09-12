"""
Compression vidéo avec ffmpeg avant envoi dans les canaux.
Aucune résolution imposée : la vidéo garde sa résolution d'origine, seule la
compression (CRF, H.264) réduit le poids du fichier.
"""
import logging
import subprocess
import uuid

import config

logger = logging.getLogger(__name__)


def compress_video(source_path, base_name: str, lang_key: str):
    """Compresse source_path avec ffmpeg et retourne le chemin du fichier compressé
    (dans TMP_DIR). Le fichier temporaire doit être supprimé par l'appelant via cleanup()."""
    output_path = config.TMP_DIR / f"{base_name}_{lang_key}_{uuid.uuid4().hex}.mp4"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(source_path),
        "-c:v", "libx264",
        "-preset", config.VIDEO_PRESET,
        "-crf", config.VIDEO_CRF,
        "-c:a", "aac",
        "-b:a", config.AUDIO_BITRATE_VIDEO,
        "-movflags", "+faststart",
        str(output_path),
    ]

    logger.info("Compression ffmpeg : %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("ffmpeg a échoué pour %s (%s) : %s", base_name, lang_key, result.stderr[-2000:])
        raise RuntimeError(f"Échec de compression ffmpeg pour {base_name}_{lang_key}")

    return output_path


def cleanup(path):
    try:
        if path and path.exists():
            path.unlink()
    except OSError:
        logger.warning("Impossible de supprimer le fichier temporaire %s", path)
