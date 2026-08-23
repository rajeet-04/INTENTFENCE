import re
from collections.abc import Iterable

from pydantic import ValidationError

from .models import CitationSource

_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")


def _clean(value: object, *, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    return _CONTROL_CHARACTERS.sub("", value).strip()[:limit]


def normalize_search_sources(
    results: object,
    *,
    limit: int = 10,
) -> tuple[CitationSource, ...]:
    if not isinstance(results, Iterable) or isinstance(results, (str, bytes, dict)):
        return ()
    sources: list[CitationSource] = []
    seen_urls: set[str] = set()
    for item in results:
        if not isinstance(item, dict):
            continue
        title = _clean(item.get("title"), limit=240)
        url = _clean(item.get("url"), limit=2048)
        snippet = _clean(
            item.get("content") or item.get("snippet") or item.get("description"),
            limit=500,
        )
        if not title or not url or url in seen_urls:
            continue
        try:
            source = CitationSource(
                title=title,
                url=url,
                snippet=snippet or None,
            )
        except ValidationError:
            continue
        normalized_url = str(source.url)
        if normalized_url in seen_urls:
            continue
        seen_urls.add(normalized_url)
        sources.append(source)
        if len(sources) >= limit:
            break
    return tuple(sources)


def normalize_fetch_source(url: str, payload: object) -> tuple[CitationSource, ...]:
    if not isinstance(payload, dict):
        return ()
    title = _clean(payload.get("title"), limit=240) or "Fetched source"
    snippet = _clean(
        payload.get("content") or payload.get("text") or payload.get("description"),
        limit=500,
    )
    try:
        return (
            CitationSource(title=title, url=url, snippet=snippet or None),
        )
    except ValidationError:
        return ()
