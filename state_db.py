"""
Bot's local DB (bot_state.db).

  - users(telegram_user_id, ui_language, created_at, updated_at)
  - published_videos(base_name, lang_key, channel_username, message_id,
                      title, caption_base, cross_links_applied, published_at)
    lang_key is "original" or one of the language codes (fr/en/it/pt/es/de).
    caption_base = caption WITHOUT the cross-links (bold title + description),
    kept so the full caption can be rebuilt during the final pass without
    depending on the .txt files (deleted in the meantime).
"""
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    telegram_user_id INTEGER PRIMARY KEY,
    ui_language      TEXT NOT NULL,
    subscribed       INTEGER NOT NULL DEFAULT 1,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS published_videos (
    base_name            TEXT NOT NULL,
    lang_key             TEXT NOT NULL,
    channel_username     TEXT NOT NULL,
    message_id           INTEGER NOT NULL,
    title                TEXT NOT NULL,
    caption_base          TEXT NOT NULL,
    is_video             INTEGER NOT NULL DEFAULT 1,
    cross_links_applied  INTEGER NOT NULL DEFAULT 0,
    published_at         TEXT NOT NULL,
    PRIMARY KEY (base_name, lang_key)
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _connect():
    conn = sqlite3.connect(config.STATE_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _connect() as conn:
        conn.executescript(SCHEMA)
        # Migrations: add columns introduced after the table's initial
        # creation (CREATE TABLE IF NOT EXISTS doesn't add them
        # retroactively to an already-existing table).
        try:
            conn.execute("ALTER TABLE users ADD COLUMN subscribed INTEGER NOT NULL DEFAULT 1")
        except sqlite3.OperationalError:
            pass  # column already present
        try:
            conn.execute("ALTER TABLE published_videos ADD COLUMN is_video INTEGER NOT NULL DEFAULT 1")
        except sqlite3.OperationalError:
            pass  # column already present


# ---------------------------------------------------------------------------
# users
# ---------------------------------------------------------------------------
def set_user_language(telegram_user_id: int, ui_language: str):
    now = _now()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO users (telegram_user_id, ui_language, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(telegram_user_id) DO UPDATE SET
                ui_language = excluded.ui_language,
                updated_at = excluded.updated_at
            """,
            (telegram_user_id, ui_language, now, now),
        )


def get_user_language(telegram_user_id: int) -> Optional[str]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT ui_language FROM users WHERE telegram_user_id = ?",
            (telegram_user_id,),
        ).fetchone()
        return row["ui_language"] if row else None


def set_subscribed(telegram_user_id: int, subscribed: bool):
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET subscribed = ?, updated_at = ? WHERE telegram_user_id = ?",
            (1 if subscribed else 0, _now(), telegram_user_id),
        )


def is_subscribed(telegram_user_id: int) -> bool:
    """True if the user is subscribed to the newsletter (default: True,
    including when the user doesn't have a row in the DB yet)."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT subscribed FROM users WHERE telegram_user_id = ?",
            (telegram_user_id,),
        ).fetchone()
        return bool(row["subscribed"]) if row else True


def get_subscribed_users() -> list[tuple[int, str]]:
    """[(telegram_user_id, ui_language), ...] for all newsletter subscribers."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT telegram_user_id, ui_language FROM users WHERE subscribed = 1",
        ).fetchall()
        return [(r["telegram_user_id"], r["ui_language"]) for r in rows]


# ---------------------------------------------------------------------------
# published_videos
# ---------------------------------------------------------------------------
@dataclass
class PublishedVideo:
    base_name: str
    lang_key: str
    channel_username: str
    message_id: int
    title: str
    caption_base: str
    is_video: int
    cross_links_applied: int
    published_at: str


def upsert_published(
    base_name: str,
    lang_key: str,
    channel_username: str,
    message_id: int,
    title: str,
    caption_base: str,
    is_video: bool = True,
):
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO published_videos
                (base_name, lang_key, channel_username, message_id, title, caption_base, is_video, cross_links_applied, published_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
            ON CONFLICT(base_name, lang_key) DO UPDATE SET
                channel_username = excluded.channel_username,
                message_id = excluded.message_id,
                title = excluded.title,
                caption_base = excluded.caption_base,
                is_video = excluded.is_video,
                published_at = excluded.published_at
            """,
            (base_name, lang_key, channel_username, message_id, title, caption_base, 1 if is_video else 0, _now()),
        )


def get_published(base_name: str, lang_key: str) -> Optional[PublishedVideo]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM published_videos WHERE base_name = ? AND lang_key = ?",
            (base_name, lang_key),
        ).fetchone()
        return PublishedVideo(**dict(row)) if row else None


def get_all_for_base(base_name: str) -> dict:
    """{lang_key: PublishedVideo} for one item — used to know whether all 7 are published."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM published_videos WHERE base_name = ?",
            (base_name,),
        ).fetchall()
        return {r["lang_key"]: PublishedVideo(**dict(r)) for r in rows}


def has_any_published(base_name: str) -> bool:
    """
    True if at least one language of this batch has already been
    successfully published. Used to know whether we're resuming a partial
    run (in which case the already-published files have normally already
    been deleted from disk — expected, not an anomaly) or whether this is
    the very first attempt on this batch (in which case checking that the
    files are physically complete makes sense).
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM published_videos WHERE base_name = ? LIMIT 1",
            (base_name,),
        ).fetchone()
        return row is not None


def mark_cross_links_applied(base_name: str, lang_key: str):
    with _connect() as conn:
        conn.execute(
            "UPDATE published_videos SET cross_links_applied = 1 WHERE base_name = ? AND lang_key = ?",
            (base_name, lang_key),
        )


def get_videos_by_language(lang_key: str) -> list:
    """Used by the user menu: list of titles published in one language."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM published_videos
            WHERE lang_key = ?
            ORDER BY published_at DESC
            """,
            (lang_key,),
        ).fetchall()
        return [PublishedVideo(**dict(r)) for r in rows]
