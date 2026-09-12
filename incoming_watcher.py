"""
Surveille INCOMING_DIR côté VPS pour détecter les lots complets déposés par le PC.

Convention de dépôt (à respecter côté watcher_local.py / script SFTP) :
  INCOMING_DIR/<base_name>/<base_name>.mp4
  INCOMING_DIR/<base_name>/<base_name>.txt
  INCOMING_DIR/<base_name>/<base_name>_fr.<ext>  ... _ja.<ext> (11 langues,
                                                    <ext> parmi config.VIDEO_EXTENSIONS)
  INCOMING_DIR/<base_name>/.ready              <-- créé en DERNIER, une fois
                                                    tout le reste bien transféré.
Le marqueur ".ready" est nécessaire pour ne jamais traiter un lot dont le
transfert SFTP est encore en cours (fichiers arrivant un par un).
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
        logger.warning("[%s] Marqueur .ready présent mais fichiers manquants : %s", base_name, missing)
        return False
    return True


async def run_forever(bot: Bot):
    logger.info("Watcher incoming démarré (poll toutes les %ss)", config.INCOMING_POLL_SECONDS)
    while True:
        try:
            for batch_dir in _find_ready_batches():
                base_name = batch_dir.name

                # La vérification de complétude physique ne fait sens QUE sur la
                # toute première tentative (avant que rien n'ait été supprimé).
                # Si une langue a déjà été publiée pour ce lot, on est en train de
                # reprendre après un échec partiel : les fichiers déjà publiés ont
                # normalement déjà été supprimés (attendu, pas une anomalie) —
                # publisher.process_batch sait reprendre où il s'était arrêté via
                # state_db, sans avoir besoin des fichiers déjà traités.
                if not state_db.has_any_published(base_name):
                    if not _batch_is_complete(batch_dir):
                        continue

                logger.info("[%s] Lot détecté, traitement...", base_name)
                try:
                    await publisher.process_batch(bot, base_name, batch_dir)
                except Exception:
                    logger.exception("[%s] Échec du traitement du lot", base_name)
                    continue

                # Nettoyage final : le marqueur + le dossier (les fichiers ont déjà
                # été supprimés au fur et à mesure par publisher.process_batch).
                marker = batch_dir / READY_MARKER
                if marker.exists():
                    marker.unlink()
                try:
                    batch_dir.rmdir()
                except OSError:
                    logger.warning("[%s] Dossier non vide après traitement, fichiers restants : %s",
                                    base_name, list(batch_dir.iterdir()))
        except Exception:
            logger.exception("Erreur inattendue dans la boucle du watcher incoming")

        await asyncio.sleep(config.INCOMING_POLL_SECONDS)
