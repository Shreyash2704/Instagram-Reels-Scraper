from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from app.models.run import Run, RunStatus
from app.models.source import Source, SourceType
from app.schemas.pipeline import VideoPayloadItem
from app.services.media_storage import _safe_filename, download_to_local_file


def test_safe_filename() -> None:
    item = VideoPayloadItem(
        source_type="profile",
        source_value="x",
        instagram_shortcode="Ab_c-12",
        is_video=True,
        video_url="https://example/v.mp4",
    )
    assert _safe_filename(item) == "Ab_c-12"


def test_download_to_local_file_writes(tmp_path: Path) -> None:
    settings = Settings(
        media_local_root=str(tmp_path),
        max_bytes_per_video=10_000,
        download_timeout_sec=30.0,
    )
    dest = tmp_path / "out.bin"

    mock_response = MagicMock()
    mock_response.iter_bytes = lambda chunk_size=64 * 1024: [b"hello", b"world"]
    mock_response.raise_for_status = MagicMock()

    stream_cm = MagicMock()
    stream_cm.__enter__.return_value = mock_response
    stream_cm.__exit__.return_value = None

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.stream = MagicMock(return_value=stream_cm)

    with patch("app.services.media_storage.httpx.Client", return_value=mock_client):
        n = download_to_local_file("https://cdn.example/v.mp4", dest, settings)

    assert n == 10
    assert dest.read_bytes() == b"helloworld"


@pytest.fixture
def db_session():
    import app.models  # noqa: F401 — register models with Base.metadata

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.db.base import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def test_attach_stored_media_local_records_row(db_session, tmp_path: Path) -> None:
    from app.services.media_storage import attach_stored_media

    src = Source(type=SourceType.profile, value="demo")
    db_session.add(src)
    db_session.commit()
    run = Run(source_id=src.id, status=RunStatus.running)
    db_session.add(run)
    db_session.commit()

    item = VideoPayloadItem(
        source_type="profile",
        source_value="demo",
        instagram_shortcode="abc",
        is_video=True,
        video_url="https://cdn.example/v.mp4",
    )

    settings = Settings(
        media_storage="local",
        media_local_root=str(tmp_path),
        max_bytes_per_video=10_000,
        download_timeout_sec=30.0,
        pipeline_fail_closed=False,
    )

    mock_response = MagicMock()
    mock_response.iter_bytes = lambda chunk_size=64 * 1024: [b"x" * 100]
    mock_response.raise_for_status = MagicMock()

    stream_cm = MagicMock()
    stream_cm.__enter__.return_value = mock_response
    stream_cm.__exit__.return_value = None

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.stream = MagicMock(return_value=stream_cm)

    with patch("app.services.media_storage.httpx.Client", return_value=mock_client):
        errs = attach_stored_media(db_session, run, [item], settings)

    assert errs == []
    assert item.stored_path == f"{run.id}/abc.mp4"
    from app.models.run_media_item import RunMediaItem

    rows = db_session.query(RunMediaItem).filter_by(run_id=run.id).all()
    assert len(rows) == 1
    assert rows[0].size_bytes == 100
