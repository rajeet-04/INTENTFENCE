from typing import Any

from intentfence_analytics import EventStore, build_summary


def latest_benchmark_payload(database_url: str) -> dict[str, Any]:
    """Return the newest persisted benchmark summary without exposing raw event payloads."""
    store = EventStore.from_url(database_url)
    run_id = store.latest_run_id()
    if run_id is None:
        return {"status": "pending", "run_id": None, "summary": None}
    events = store.list_run_events(run_id)
    return {
        "status": "ready",
        "run_id": run_id,
        "summary": build_summary(events),
    }
