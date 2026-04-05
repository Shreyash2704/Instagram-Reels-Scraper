from typing import Any, Protocol

from app.models.source import Source


class InstagramProvider(Protocol):
    def build_run_input(self, source: Source, max_results_per_query: int) -> dict[str, Any]: ...

    def actor_id(self) -> str: ...
