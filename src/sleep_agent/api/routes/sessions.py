from __future__ import annotations

from pathlib import Path
import numpy as np
from fastapi import APIRouter, HTTPException, Query, Request


router = APIRouter(tags=["sessions"])
DEMO_USER = "demo_user"


@router.get("/sessions")
def list_sessions(request: Request):
    return {"items": request.app.state.repository.list_sessions(DEMO_USER)}


@router.get("/sessions/{session_id}/signal")
def get_signal(
    session_id: str, request: Request, start_s: float = Query(0, ge=0),
    end_s: float = Query(30, gt=0), max_points: int = Query(3000, ge=100, le=10000),
):
    if end_s <= start_s or end_s - start_s > 120:
        raise HTTPException(422, "signal range must be positive and at most 120 seconds")
    session = request.app.state.repository.get_session(DEMO_USER, session_id)
    if not session or not session.get("signal_path"):
        raise HTTPException(404, "waveform session not found")
    path = Path(session["signal_path"])
    if not path.exists():
        raise HTTPException(404, "signal file is unavailable")
    bundle = np.load(path)
    time = bundle["time_s"]
    select = np.where((time >= start_s) & (time <= end_s))[0]
    if not len(select):
        return {"session_id": session_id, "items": []}
    stride = max(1, int(np.ceil(len(select) / max_points)))
    idx = select[::stride]
    raw = bundle["ecg_mv"][idx]
    filtered = bundle["filtered_ecg_mv"][idx]
    peaks = bundle["detected_r_peaks_s"]
    return {
        "session_id": session_id,
        "time_s": time[idx].tolist(),
        "raw_ecg_mv": [None if not np.isfinite(x) else float(x) for x in raw],
        "filtered_ecg_mv": [None if not np.isfinite(x) else float(x) for x in filtered],
        "motion": bundle["motion"][idx].astype(bool).tolist(),
        "contact": bundle["contact"][idx].astype(bool).tolist(),
        "r_peaks_s": peaks[(peaks >= start_s) & (peaks <= end_s)].tolist(),
        "downsample_stride": stride,
    }

