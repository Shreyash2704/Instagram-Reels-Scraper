from typing import Any

from app.models.source import Source, SourceType
from app.integrations.apify.provider import InstagramProvider


class AimscrapeInstagramProvider:
    """Maps our Source model to aimscrape/instagram-scraper actor input."""

    def actor_id(self) -> str:
        return "aimscrape~instagram-scraper"

    def build_run_input(self, source: Source, max_results_per_query: int) -> dict[str, Any]:
        q = self._query_for_source(source)
        # Actor schema: minimum 5 for maxResultsPerQuery
        cap = max(5, int(max_results_per_query))
        return {
            "queries": [q],
            "maxResultsPerQuery": cap,
        }

    def _query_for_source(self, source: Source) -> str:
        if source.type == SourceType.hashtag:
            tag = source.value
            return f"https://www.instagram.com/explore/tags/{tag}/"
        if source.type == SourceType.profile:
            return f"https://www.instagram.com/{source.value}/reels/"
        if source.type == SourceType.profile_tagged:
            return f"https://www.instagram.com/{source.value}/tagged/"
        if source.type == SourceType.post_url:
            return source.value
        raise ValueError(f"unsupported source type: {source.type}")
