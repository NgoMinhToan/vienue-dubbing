import json
import sqlite3
import threading
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone


class Conflict(ValueError):
    pass


class Store:
    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        with self.connection() as db:
            db.execute("CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, data TEXT NOT NULL)")

    def connection(self):
        return sqlite3.connect(self.root / "projects.sqlite3", timeout=30)

    def directory(self, id):
        if len(id) != 32 or any(c not in "0123456789abcdef" for c in id):
            raise KeyError(id)
        return self.root / "projects" / id

    def get(self, id):
        self.directory(id)
        with self.connection() as db:
            row = db.execute("SELECT data FROM projects WHERE id=?", (id,)).fetchone()
        if not row:
            raise KeyError(id)
        return json.loads(row[0])

    def list(self):
        with self.connection() as db:
            rows = db.execute("SELECT data FROM projects").fetchall()
        return sorted([json.loads(r[0]) for r in rows], key=lambda p: p["updated"], reverse=True)

    def save(self, project, expected=None):
        with self.lock, self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT data FROM projects WHERE id=?", (project["id"],)).fetchone()
            if expected is not None and (not row or json.loads(row[0])["revision"] != expected):
                raise Conflict("Dự án đã thay đổi. Nạp lại trước khi lưu.")
            # Restoring an old queued version must still use today's global rules for new work.
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='pronunciation'").fetchone():
                dictionary = db.execute("SELECT data FROM pronunciation WHERE id=1").fetchone()
                if dictionary:
                    project["pronunciation"] = json.loads(dictionary[0])
            project["updated"] = datetime.now(timezone.utc).isoformat()
            db.execute("INSERT OR REPLACE INTO projects VALUES (?, ?)", (project["id"], json.dumps(project)))
        return project

    def create(self):
        id = uuid4().hex
        directory = self.directory(id)
        directory.mkdir(parents=True)
        for name in ("clips", "renders"):
            (directory / name).mkdir()
        return id, directory

    def delete(self, id):
        with self.lock, self.connection() as db:
            db.execute("DELETE FROM projects WHERE id=?", (id,))
