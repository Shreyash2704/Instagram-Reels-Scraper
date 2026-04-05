from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db, session_factory
from app.models.run import Run, RunStatus
from app.models.source import Source
from app.schemas.run import RunCreateResponse
from app.schemas.source import SourceCreate, SourceRead, SourceReadList
from app.services.pipeline_service import execute_run

router = APIRouter(prefix="/sources", tags=["sources"])


@router.post("", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
def create_source(body: SourceCreate, db: Session = Depends(get_db)) -> Source:
    s = Source(type=body.type, value=body.value)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.get("", response_model=SourceReadList)
def list_sources(db: Session = Depends(get_db)) -> SourceReadList:
    rows = db.query(Source).order_by(Source.id.desc()).all()
    return SourceReadList(items=[SourceRead.model_validate(r) for r in rows])


@router.get("/{source_id}", response_model=SourceRead)
def get_source(source_id: int, db: Session = Depends(get_db)) -> Source:
    s = db.get(Source, source_id)
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Source not found")
    return s


def _run_pipeline_task(run_id: int) -> None:
    db = session_factory()
    try:
        execute_run(db, run_id)
    finally:
        db.close()


@router.post("/{source_id}/run", response_model=RunCreateResponse)
def run_source(
    source_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> RunCreateResponse:
    s = db.get(Source, source_id)
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Source not found")
    run = Run(source_id=source_id, status=RunStatus.pending)
    db.add(run)
    db.commit()
    db.refresh(run)
    settings = get_settings()
    if settings.use_rq:
        from app.jobs.queue import enqueue_run

        enqueue_run(run.id)
    else:
        background_tasks.add_task(_run_pipeline_task, run.id)
    return RunCreateResponse(run_id=run.id, status=run.status)
