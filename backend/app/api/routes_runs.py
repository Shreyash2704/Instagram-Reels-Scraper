from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.run import Run
from app.schemas.run import RunRead, RunReadList

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("", response_model=RunReadList)
def list_runs(
    db: Session = Depends(get_db),
    source_id: int | None = Query(None, description="Filter runs by source id"),
) -> RunReadList:
    q = db.query(Run).order_by(Run.id.desc())
    if source_id is not None:
        q = q.filter(Run.source_id == source_id)
    rows = q.limit(200).all()
    return RunReadList(items=[RunRead.model_validate(r) for r in rows])


@router.get("/{run_id}", response_model=RunRead)
def get_run(run_id: int, db: Session = Depends(get_db)) -> Run:
    r = db.get(Run, run_id)
    if r is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    return r
