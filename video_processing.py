"""
Video compression with ffmpeg — DISABLED for now.

The VPS now receives files that are already compressed (compression is done
upstream, before being dropped into INCOMING_DIR). publisher.py no longer
calls anything from this module. The code is left below, commented out, so
it can easily be re-enabled if needed again.
"""
import logging

logger = logging.getLogger(__name__)


# import subprocess
# import config
#
# def compress_video_to(source_path, output_path):
#     """Compresses source_path with ffmpeg directly into output_path."""
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
#     logger.info("ffmpeg compression: %s", " ".join(cmd))
#     result = subprocess.run(cmd, capture_output=True, text=True)
#     if result.returncode != 0:
#         logger.error("ffmpeg failed for %s: %s", output_path.name, result.stderr[-2000:])
#         cleanup(output_path)
#         raise RuntimeError(f"ffmpeg compression failed for {output_path.name}")


def cleanup(path):
    try:
        if path and path.exists():
            path.unlink()
    except OSError:
        logger.warning("Could not delete temporary file %s", path)
