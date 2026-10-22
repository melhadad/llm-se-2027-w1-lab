"""CLI entry points for routing records and processing a day's JSON array."""

import argparse
import sys
from datetime import datetime, timezone
from typing import cast
from pathlib import Path

from triage.batch import InputKind, route_batch
from triage.cli import MAX_ISSUE_BYTES, MAX_SNAPSHOT_BYTES, read_json
from triage.models import TriageRecord
from triage.routing import normalize_received_at, route_issue
from triage.service import Extractor


def _received_at(value: str | None) -> datetime:
    timestamp = datetime.now(timezone.utc) if value is None else datetime.fromisoformat(value.replace("Z", "+00:00"))
    return normalize_received_at(timestamp)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    route = commands.add_parser("route", help="route a validated triage JSON record, without a model")
    route.add_argument("--record", required=True, help="JSON file; - reads stdin")
    route.add_argument("--received-at", help="ISO 8601 timestamp with timezone; defaults to now")
    batch = commands.add_parser("batch", help="process a JSON array with per-item results")
    batch.add_argument("--input", required=True, help="JSON array file; - reads stdin")
    batch.add_argument("--kind", choices=["triage", "issue"], default="triage")
    batch.add_argument("--received-at", help="shared ISO 8601 receipt time with timezone")
    batch.add_argument("--model", help="DSPy model override; only valid with --kind issue")
    args = parser.parse_args(argv)
    try:
        timestamp = _received_at(args.received_at)
        path = args.record if args.command == "route" else args.input
        limit = MAX_ISSUE_BYTES if args.command == "route" else MAX_SNAPSHOT_BYTES
        if path == "-":
            payload = read_json(sys.stdin.buffer, limit)
        else:
            with Path(path).open("rb") as stream:
                payload = read_json(stream, limit)
        if args.command == "route":
            decision = route_issue(TriageRecord.model_validate(payload), timestamp)
            print(decision.model_dump_json(indent=2))
            return 0
        if not isinstance(payload, list):
            raise ValueError("batch input must be an array")
        if args.model and args.kind != "issue":
            raise ValueError("--model is only valid with --kind issue")

        def factory() -> Extractor:
            from triage.extract import DSPyExtractor

            return DSPyExtractor(args.model)

        report = route_batch(
            cast(list[object], payload), kind=cast(InputKind, args.kind),
            received_at=timestamp, extractor_factory=factory,
        )
    except (OSError, ValueError, TypeError, RecursionError, OverflowError):
        print("Routing input error: supply valid JSON, at most 1000 batch items, "
              "a valid project taxonomy, and a receipt timestamp with timezone. "
              "Single records are limited to 1 MiB and batches to 16 MiB.", file=sys.stderr)
        return 2
    print(report.model_dump_json(indent=2))
    return 1 if report.failed else 0
