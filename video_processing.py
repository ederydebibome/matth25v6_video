"""
Compression vidéo avec ffmpeg avant envoi dans les canaux.
Aucune résolution imposée : la vidéo garde sa résolution d'origine, seule la
compression (CRF, H.264) réduit le poids du fichier.

Le chemin de sortie est fourni par l'appelant (déterministe, basé sur
<base_name>_compressed_<lang_key>) plutôt que généré aléatoirement : si le
traitement d'un lot est interrompu puis repris, on peut détecter qu'une
compression est déjà terminée simplement en vérifiant que ce fichier existe,
sans avoir à la refaire.
"""
import logging
import subprocess

import config

logger = logging.getLogger(__name__)


def compress_video_to(source_path, output_path):
    """Compresse source_path avec ffmpeg directement vers output_path."""
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
        logger.error("ffmpeg a échoué pour %s : %s", output_path.name, result.stderr[-2000:])
        # Ne jamais laisser un fichier de sortie partiel/corrompu : la reprise
        # le prendrait pour "déjà compressé" et enverrait une vidéo cassée.
        cleanup(output_path)
        raise RuntimeError(f"Échec de compression ffmpeg pour {output_path.name}")


def cleanup(path):
    try:
        if path and path.exists():
            path.unlink()
    except OSError:
        logger.warning("Impossible de supprimer le fichier temporaire %s", path)
