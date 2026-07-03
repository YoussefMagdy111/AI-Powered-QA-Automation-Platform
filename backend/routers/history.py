"""
backend/routers/history.py — CRUD endpoints for run history (per-user)
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.db import get_conn
from backend.auth_utils import require_auth

router = APIRouter()

MAX_RUNS = 100


class RunEntry(BaseModel):
    id: str
    ts: int
    label: str = ""
    preview: str
    tc_count: int
    coverage: Optional[float] = None
    overall_risk: Optional[str] = None
    user_story: str
    tc_list: list
    report_raw: str
    report_data: dict
    review_data: dict


class LabelUpdate(BaseModel):
    label: str


def _row_to_dict(row) -> dict:
    d = dict(row)
    for key in ("tc_list", "report_data", "review_data"):
        try:
            d[key] = json.loads(d[key] or "null") or ([] if key == "tc_list" else {})
        except Exception:
            d[key] = [] if key == "tc_list" else {}
    if "label" not in d or d["label"] is None:
        d["label"] = ""
    return d


@router.get("/api/history")
def get_history(user: dict = Depends(require_auth)):
    uid = user["user_id"]
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM runs WHERE user_id=? ORDER BY ts DESC LIMIT ?",
            (uid, MAX_RUNS),
        ).fetchall()
    return {"runs": [_row_to_dict(r) for r in rows]}


@router.get("/api/history/{run_id}")
def get_run(run_id: str, user: dict = Depends(require_auth)):
    uid = user["user_id"]
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM runs WHERE id=? AND user_id=?", (run_id, uid)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    return _row_to_dict(row)


@router.post("/api/history")
def save_run(entry: RunEntry, user: dict = Depends(require_auth)):
    uid = user["user_id"]
    with get_conn() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM runs WHERE user_id=?", (uid,)
        ).fetchone()[0]
        if count >= MAX_RUNS:
            oldest = conn.execute(
                "SELECT id FROM runs WHERE user_id=? ORDER BY ts ASC LIMIT ?",
                (uid, count - MAX_RUNS + 1),
            ).fetchall()
            for row in oldest:
                conn.execute("DELETE FROM runs WHERE id=?", (row["id"],))

        conn.execute(
            """INSERT OR REPLACE INTO runs
               (id, user_id, ts, label, preview, tc_count, coverage, overall_risk,
                user_story, tc_list, report_raw, report_data, review_data)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                entry.id, uid, entry.ts, entry.label, entry.preview, entry.tc_count,
                entry.coverage, entry.overall_risk, entry.user_story,
                json.dumps(entry.tc_list),
                entry.report_raw,
                json.dumps(entry.report_data),
                json.dumps(entry.review_data),
            ),
        )
        conn.commit()
    return {"success": True, "id": entry.id}


@router.patch("/api/history/{run_id}")
def update_label(run_id: str, body: LabelUpdate, user: dict = Depends(require_auth)):
    uid = user["user_id"]
    with get_conn() as conn:
        result = conn.execute(
            "UPDATE runs SET label=? WHERE id=? AND user_id=?",
            (body.label.strip(), run_id, uid),
        )
        conn.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"success": True}


@router.delete("/api/history/{run_id}")
def delete_run(run_id: str, user: dict = Depends(require_auth)):
    uid = user["user_id"]
    with get_conn() as conn:
        result = conn.execute(
            "DELETE FROM runs WHERE id=? AND user_id=?", (run_id, uid)
        )
        conn.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"success": True}


@router.delete("/api/history")
def clear_history(user: dict = Depends(require_auth)):
    uid = user["user_id"]
    with get_conn() as conn:
        conn.execute("DELETE FROM runs WHERE user_id=?", (uid,))
        conn.commit()
    return {"success": True}
