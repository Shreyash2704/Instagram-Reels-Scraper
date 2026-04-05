import re
from datetime import datetime
from typing import Self

from pydantic import BaseModel, model_validator

from app.models.source import SourceType

USERNAME_RE = re.compile(r"^[A-Za-z0-9._]{1,64}$")
POST_URL_RE = re.compile(
    r"^https?://(?:www\.|m\.)?instagram\.com/(?:p|reel)/[A-Za-z0-9_-]+/?(?:\?.*)?$",
    re.IGNORECASE,
)


class SourceCreate(BaseModel):
    type: SourceType
    value: str

    @model_validator(mode="after")
    def normalize_value(self) -> Self:
        v = self.value.strip()
        if not v:
            raise ValueError("value must not be empty")
        if self.type == SourceType.hashtag:
            v = v.lstrip("#").strip()
            if not re.match(r"^[A-Za-z0-9_]+$", v):
                raise ValueError("invalid hashtag (use letters, numbers, underscore)")
        elif self.type in (SourceType.profile, SourceType.profile_tagged):
            v = v.lstrip("@").strip()
            if not USERNAME_RE.match(v):
                raise ValueError("invalid Instagram username")
        elif self.type == SourceType.post_url:
            if not POST_URL_RE.match(v):
                raise ValueError("invalid Instagram post or reel URL")
        self.value = v
        return self


class SourceRead(BaseModel):
    id: int
    type: SourceType
    value: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class SourceReadList(BaseModel):
    items: list[SourceRead]
