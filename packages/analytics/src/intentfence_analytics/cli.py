"""Run benchmark scenarios through the production gateway and persist results."""

import argparse
import json

from .adapter import GatewayBenchmarkAuthorizer
from .events import EventStore
from .kpis import build_summary
from .runner import run_benchmark
from .scenarios import load_scenarios_dir


def run_stored_benchmark(scenarios_dir: str, database_path: str) -> dict:
    scenarios = load_scenarios_dir(scenarios_dir)
    store = EventStore.from_url(f"sqlite:///{database_path}")
    result = run_benchmark(scenarios, GatewayBenchmarkAuthorizer())
    store.append_many(list(result.events))
    summary = build_summary(store.list_events(run_id=result.run_id))
    return {"run_id": result.run_id, **summary}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="intentfence-benchmark")
    parser.add_argument("scenarios_dir", help="Directory of scenario JSON files")
    parser.add_argument("database_path", help="SQLite file for persisted benchmark events")
    args = parser.parse_args(argv)
    print(json.dumps(run_stored_benchmark(args.scenarios_dir, args.database_path), indent=2))


if __name__ == "__main__":
    main()
