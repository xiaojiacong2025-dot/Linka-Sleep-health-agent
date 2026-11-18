from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Request


router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def metrics(
    request: Request, metric: str = Query(pattern="^(heart_rate|rmssd)$"),
    start_time: datetime = Query(), end_time: datetime = Query(),
    limit: int = Query(500, ge=1, le=2000),
):
    if start_time.tzinfo is None or end_time.tzinfo is None:
        raise HTTPException(422, "timestamps must include timezone")
    if end_time <= start_time:
        raise HTTPException(422, "end_time must follow start_time")
    return {"items": request.app.state.repository.query_metrics(
        "demo_user", start_time, end_time, metric, limit
    )}

