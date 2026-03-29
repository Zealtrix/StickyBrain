from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from platformdirs import user_data_dir

from sticky_brain.models import Note, utc_now_iso

APP_AUTHOR = "StickyBrain"
APP_NAME = "StickyBrain"


def app_storage_dir() -> Path:
    storage_dir = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


def default_db_path() -> Path:
    override = os.environ.get("STICKY_BRAIN_DB_PATH", "").strip()
    if override:
        custom_path = Path(override).expanduser()
        custom_path.parent.mkdir(parents=True, exist_ok=True)
        return custom_path
    return app_storage_dir() / "sticky_brain.db"


class NoteRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT '',
                body TEXT NOT NULL DEFAULT '',
                tags_json TEXT NOT NULL DEFAULT '[]',
                category TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                pinned INTEGER NOT NULL DEFAULT 0,
                sensitive INTEGER NOT NULL DEFAULT 0,
                color TEXT NOT NULL DEFAULT '#FFF4A3',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                embedding_json TEXT,
                embedding_hash TEXT
            )
            """
        )
        self.conn.commit()

    def list_notes(self) -> list[Note]:
        rows = self.conn.execute(
            """
            SELECT *
            FROM notes
            ORDER BY pinned DESC, datetime(updated_at) DESC, title COLLATE NOCASE ASC
            """
        ).fetchall()
        return [self._row_to_note(row) for row in rows]

    def get_note(self, note_id: str) -> Note | None:
        row = self.conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        return self._row_to_note(row) if row else None

    def upsert(self, note: Note) -> Note:
        note.updated_at = utc_now_iso()
        self.conn.execute(
            """
            INSERT INTO notes (
                id, title, body, tags_json, category, status, pinned, sensitive, color,
                created_at, updated_at, embedding_json, embedding_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                body = excluded.body,
                tags_json = excluded.tags_json,
                category = excluded.category,
                status = excluded.status,
                pinned = excluded.pinned,
                sensitive = excluded.sensitive,
                color = excluded.color,
                updated_at = excluded.updated_at,
                embedding_json = excluded.embedding_json,
                embedding_hash = excluded.embedding_hash
            """,
            (
                note.id,
                note.title,
                note.body,
                json.dumps(note.tags),
                note.category,
                note.status,
                int(note.pinned),
                int(note.sensitive),
                note.color,
                note.created_at,
                note.updated_at,
                note.embedding_json,
                note.embedding_hash,
            ),
        )
        self.conn.commit()
        return note

    def delete(self, note_id: str) -> None:
        self.conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    @staticmethod
    def _row_to_note(row: sqlite3.Row) -> Note:
        return Note(
            id=row["id"],
            title=row["title"],
            body=row["body"],
            tags=Note.normalize_tags(json.loads(row["tags_json"])),
            category=row["category"],
            status=row["status"],
            pinned=bool(row["pinned"]),
            sensitive=bool(row["sensitive"]),
            color=row["color"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            embedding_json=row["embedding_json"],
            embedding_hash=row["embedding_hash"],
        )
