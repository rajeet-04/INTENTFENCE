"""Run controlled benchmark scenarios through the authoritative gateway and persist results."""

import argparse
import json

from .adapter import GatewayBenchmarkAuthorizer
from .events import EventStore
from .kpis import build_summary
from .runner import run_benchmark
from .scenarios import load_scenarios_dir


def run_stored_benchmark(
    scenarios_dir: str,
    database_path: str,
    *,
    run_id: str | None = None,
) -> dict:
    scenarios = load_scenarios_dir(scenarios_dir)
    result = run_benchmark(
        scenarios,
        GatewayBenchmarkAuthorizer(),
        run_id=run_id,
    )
    store = EventStore.from_url(f"sqlite:///{database_path}")
    store.append_many(list(result.events))
    persisted = store.list_run_events(result.run_id)
    summary = build_summary(persisted)
    return {"run_id": result.run_id, "summary": summary}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="intentfence-benchmark")
    parser.add_argument("scenarios_dir", help="Directory containing controlled scenario JSON files")
    parser.add_argument("database_path", help="SQLite file for persisted benchmark events")
    parser.add_argument("--run-id", default=None, help="Optional stable run identifier")
    args = parser.parse_args(argv)
    print(
        json.dumps(
            run_stored_benchmark(
                args.scenarios_dir,
                args.database_path,
                run_id=args.run_id,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
