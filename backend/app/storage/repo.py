import json
import uuid
from typing import Optional

from .db import Database


class RunRepo:
    def __init__(self, db: Database):
        self._db = db

    def create_run(self, agent_kind: str, user_message: str) -> str:
        run_id = str(uuid.uuid4())
        with self._db.lock, self._db.connect() as conn:
            conn.execute(
                "INSERT INTO agent_runs (run_id, agent_kind, user_message) VALUES (?, ?, ?)",
                (run_id, agent_kind, user_message),
            )
        return run_id

    def append_event(self, run_id: str, seq: int, event_type: str, data: dict) -> None:
        with self._db.lock, self._db.connect() as conn:
            conn.execute(
                "INSERT INTO agent_events (run_id, seq, type, data_json) VALUES (?, ?, ?, ?)",
                (run_id, seq, event_type, json.dumps(data)),
            )

    def finish_run(self, run_id: str, status: str, final_result: Optional[dict]) -> None:
        with self._db.lock, self._db.connect() as conn:
            conn.execute(
                "UPDATE agent_runs SET status = ?, final_result_json = ? WHERE run_id = ?",
                (status, json.dumps(final_result) if final_result is not None else None, run_id),
            )

    def get_run(self, run_id: str) -> Optional[dict]:
        with self._db.lock, self._db.connect() as conn:
            run = conn.execute("SELECT * FROM agent_runs WHERE run_id = ?", (run_id,)).fetchone()
            if not run:
                return None
            events = conn.execute(
                "SELECT seq, type, data_json, created_at FROM agent_events WHERE run_id = ? ORDER BY seq", (run_id,)
            ).fetchall()
        return {
            "run_id": run["run_id"],
            "agent_kind": run["agent_kind"],
            "user_message": run["user_message"],
            "status": run["status"],
            "final_result": json.loads(run["final_result_json"]) if run["final_result_json"] else None,
            "created_at": run["created_at"],
            "events": [
                {"seq": e["seq"], "type": e["type"], "data": json.loads(e["data_json"]), "created_at": e["created_at"]}
                for e in events
            ],
        }
