import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes_proxy_image import router as proxy_image_router
from app.api.routes_runs import router as runs_router
from app.api.routes_sources import router as sources_router
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine
from app.models import delivered_item, run, run_media_item, source  # noqa: F401 — register tables

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Instagram video pipeline", lifespan=lifespan)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sources_router)
app.include_router(runs_router)
app.include_router(proxy_image_router)

_media_root = Path(settings.media_local_root).resolve()
_media_root.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(_media_root)), name="media")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
