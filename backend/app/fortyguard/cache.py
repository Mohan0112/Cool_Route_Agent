import hashlib
import json
import sqlite3
import threading
from pathlib import Path
from typing import Optional


class ResponseCache:
    """SQLite-backed cache keyed by sha256(endpoint + normalized params). Only terminal
    'succeeded' results are ever stored -- failed FortyGuard calls cost nothing anyway,
    so there's no billing reason to cache them, and caching a transient failure would be wrong.
    """

    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._lock = threading.Lock()
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_entries (
                    cache_key TEXT PRIMARY KEY,
                    endpoint TEXT NOT NULL,
                    params_json TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now'))
                )
                """
            )
            conn.execute("PRAGMA journal_mode=WAL")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path, check_same_thread=False)

    @staticmethod
    def make_key(endpoint: str, params: dict) -> str:
        normalized = json.dumps(_normalize(params), sort_keys=True)
        return hashlib.sha256(f"{endpoint}:{normalized}".encode()).hexdigest()

    def get(self, endpoint: str, params: dict) -> Optional[dict]:
        # The cache is a pure optimization -- concurrent tool calls (multiple routes' heat
        # checked at once) can occasionally collide on the underlying SQLite file (confirmed by
        # testing: a fresh cache file briefly hit "attempt to write a readonly database" under
        # concurrent access, likely OneDrive's file sync interfering with SQLite's WAL locking,
        # since this project lives in a synced folder). A cache miss/failure must never break a
        # real API call, so any DB error here just falls through to a live call instead.
        key = self.make_key(endpoint, params)
        try:
            with self._lock, self._connect() as conn:
                row = conn.execute("SELECT result_json FROM cache_entries WHERE cache_key = ?", (key,)).fetchone()
            return json.loads(row[0]) if row else None
        except sqlite3.Error:
            return None

    def put(self, endpoint: str, params: dict, result: dict) -> None:
        key = self.make_key(endpoint, params)
        try:
            with self._lock, self._connect() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO cache_entries (cache_key, endpoint, params_json, result_json) VALUES (?, ?, ?, ?)",
                    (key, endpoint, json.dumps(_normalize(params)), json.dumps(result)),
                )
        except sqlite3.Error:
            pass


def _normalize(params: dict) -> dict:
    """Rounds lat/lon to ~11m precision so near-identical queries still hit the cache."""
    def round_floats(obj):
        if isinstance(obj, float):
            return round(obj, 4)
        if isinstance(obj, dict):
            return {k: round_floats(v) for k, v in sorted(obj.items())}
        if isinstance(obj, list):
            return [round_floats(v) for v in obj]
        return obj

    return round_floats(params)
