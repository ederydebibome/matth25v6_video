"""
Watches INCOMING_DIR on the VPS side to detect complete batches dropped by the PC.

Drop convention (must be respected by watcher_local.py / the SFTP script):
  INCOMING_DIR/<base_name>/<base_name>.mp4
  INCOMING_DIR/<base_name>/<base_name>.txt
  INCOMING_DIR/<base_name>/<base_name>_fr.<ext>  ... _ja.<ext> (11 languages,
                                                    <ext> among config.VIDEO_EXTENSIONS)
  INCOMING_DIR/<base_name>/.ready              <-- created LAST, once
                                                    everything else has been transferred.
The ".ready" marker is needed to never process a batch whose SFTP transfer
is still in progress (files arriving one by one).
"""
import asyncio
import logging

from telegram import Bot

import config
import publisher
import state_db

logger = logging.getLogger(__name__)

READY_MARKER = ".ready"


def _find_ready_batches():
    if not config.INCOMING_DIR.exists():
        return []
    batches = []
    for entry in config.INCOMING_DIR.iterdir():
        if entry.is_dir() and (entry / READY_MARKER).exists():
            batches.append(entry)
    return batches


def _batch_is_complete(batch_dir) -> bool:
    base_name = batch_dir.name
    missing = config.missing_batch_files(batch_dir, base_name)
    if missing:
        logger.warning("[%s] .ready marker present but files missing: %s", base_name, missing)
        return False
    return True


async def run_forever(bot: Bot):
    logger.info("Incoming watcher started (polling every %ss)", config.INCOMING_POLL_SECONDS)
    while True:
        try:
            for batch_dir in _find_ready_batches():
                base_name = batch_dir.name

                # The physical completeness check only makes sense on the
                # very first attempt (before anything has been deleted). If
                # a language has already been published for this batch,
                # we're resuming after a partial failure: the already-
                # published files have normally already been deleted
                # (expected, not an anomaly) — publisher.process_batch knows
                # how to resume where it left off via state_db, without
                # needing the already-processed files.
                if not state_db.has_any_published(base_name):
                    if not _batch_is_complete(batch_dir):
                        continue

                logger.info("[%s] Batch detected, processing...", base_name)
                try:
                    await publisher.process_batch(bot, base_name, batch_dir)
                except Exception:
                    logger.exception("[%s] Failed to process batch", base_name)
                    continue

                # Only clean up (marker + folder) if all 12 languages are
                # confirmed published in the DB: process_batch can return
                # without an exception while still being incomplete (missing
                # source text/video, processing interrupted during
                # compression/publication...). In that case the marker is
                # left in place to retry on the next pass.
                published_map = state_db.get_all_for_base(base_name)
                if len(published_map) != len(config.ALL_KEYS):
                    logger.warning(
                        "[%s] Batch not fully published yet (%s/%s), will retry on the next pass.",
                        base_name, len(published_map), len(config.ALL_KEYS),
                    )
                    continue

                # Final cleanup: the marker + the folder (the files —
                # originals, compressed versions and translation .txt files —
                # have already been deleted along the way by
                # publisher.process_batch).
                marker = batch_dir / READY_MARKER
                if marker.exists():
                    marker.unlink()
                try:
                    batch_dir.rmdir()
                except OSError:
                    logger.warning("[%s] Folder not empty after processing, remaining files: %s",
                                    base_name, list(batch_dir.iterdir()))
        except Exception:
            logger.exception("Unexpected error in the incoming watcher loop")

        await asyncio.sleep(config.INCOMING_POLL_SECONDS)
