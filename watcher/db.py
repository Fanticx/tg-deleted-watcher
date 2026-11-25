import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .posts import Post

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    channel_id INTEGER NOT NULL,
    id         INTEGER NOT NULL,
    date       INTEGER NOT NULL,
    text       TEXT    NOT NULL,
    media      TEXT,
    media_path TEXT,
    deleted    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (channel_id, id)
)
"""
COLUMNS = "channel_id, id, date, text, media, media_path, deleted"


def _to_post(row: tuple) -> Post:
    channel_id, post_id, date, text, media, media_path, deleted = row
    date = datetime.fromtimestamp(date, timezone.utc)
    return Post(channel_id, post_id, date, text, media, media_path, bool(deleted))


class Database:
    def __init__(self, path: Path):
        self.conn = sqlite3.connect(path)
        self.conn.execute(SCHEMA)

    def save(self, post: Post) -> None:
        with self.conn:
            self.conn.execute(
                f"""INSERT INTO posts ({COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, 0)
                    ON CONFLICT (channel_id, id) DO UPDATE SET
                        text = excluded.text,
                        media = excluded.media,
                        media_path = excluded.media_path""",
                (post.channel_id, post.id, int(post.date.timestamp()),
                 post.text, post.media, post.media_path),
            )

    def get(self, channel_id: int, post_id: int) -> Post | None:
        row = self.conn.execute(
            f"SELECT {COLUMNS} FROM posts WHERE channel_id = ? AND id = ?", (channel_id, post_id)
        ).fetchone()
        return _to_post(row) if row else None

    def mark_deleted(self, channel_id: int, post_id: int) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE posts SET deleted = 1 WHERE channel_id = ? AND id = ?", (channel_id, post_id)
            )

    def alive_ids(self, channel_id: int, since: datetime) -> list[int]:
        rows = self.conn.execute(
            "SELECT id FROM posts WHERE channel_id = ? AND date >= ? AND deleted = 0 ORDER BY id",
            (channel_id, int(since.timestamp())),
        )
        return [post_id for (post_id,) in rows]

    def stale_media(self, before: datetime) -> list[Post]:
        rows = self.conn.execute(
            f"SELECT {COLUMNS} FROM posts WHERE date < ? AND deleted = 0 AND media_path IS NOT NULL",
            (int(before.timestamp()),),
        )
        return [_to_post(row) for row in rows]

    def clear_media(self, channel_id: int, post_id: int) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE posts SET media_path = NULL WHERE channel_id = ? AND id = ?",
                (channel_id, post_id),
            )
