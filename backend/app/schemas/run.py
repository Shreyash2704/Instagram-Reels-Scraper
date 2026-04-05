from datetime import datetime

from pydantic import BaseModel

from app.models.run import RunStatus


class RunRead(BaseModel):
    id: int
    source_id: int
    status: RunStatus
    error_message: str | None
    item_count: int
    video_count: int
    delivered_count: int
    destination_status_code: int | None
    apify_dataset_id: str | None
    payload_preview: str | None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    model_config = {"from_attributes": True}


class RunReadList(BaseModel):
    items: list[RunRead]


class RunCreateResponse(BaseModel):
    run_id: int
    status: RunStatus
