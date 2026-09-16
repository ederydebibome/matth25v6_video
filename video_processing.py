"""
Compression vidéo avec ffmpeg — DÉSACTIVÉE pour l'instant.

Le VPS reçoit désormais des fichiers déjà compressés (compression faite en
amont, avant dépôt dans INCOMING_DIR). publisher.py n'appelle plus rien de ce
module. Le code est laissé ci-dessous en commentaire pour pouvoir le
réactiver facilement si le besoin revient.
"""
import logging

logger = logging.getLogger(__name__)


# import subprocess
# import config
#
# def compress_video_to(source_path, output_path):
#     """Compresse source_path avec ffmpeg directement vers output_path."""
#     cmd = [
#         "ffmpeg", "-y",
#         "-i", str(source_path),
#         "-c:v", "libx264",
#         "-preset", config.VIDEO_PRESET,
#         "-crf", config.VIDEO_CRF,
#         "-c:a", "aac",
#         "-b:a", config.AUDIO_BITRATE_VIDEO,
#         "-movflags", "+faststart",
#         str(output_path),
#     ]
#
#     logger.info("Compression ffmpeg : %s", " ".join(cmd))
#     result = subprocess.run(cmd, capture_output=True, text=True)
#     if result.returncode != 0:
#         logger.error("ffmpeg a échoué pour %s : %s", output_path.name, result.stderr[-2000:])
#         cleanup(output_path)
#         raise RuntimeError(f"Échec de compression ffmpeg pour {output_path.name}")


def cleanup(path):
    try:
        if path and path.exists():
            path.unlink()
    except OSError:
        logger.warning("Impossible de supprimer le fichier temporaire %s", path)
