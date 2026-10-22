"""One issue in, one JSON triage record on stdout."""

import argparse
import json
import sys
from pathlib import Path
from typing import BinaryIO, cast

from pydantic import ValidationError

from triage.models import Issue
from triage.service import triage_issue

ROOT = Path(__file__).resolve().parents[2]
MAX_ISSUE_BYTES = 1024 * 1024
MAX_SNAPSHOT_BYTES = 16 * 1024 * 1024


def read_json(stream: BinaryIO, max_bytes: int) -> object:
    """Bound allocation before decoding and parsing, including ignored fields."""
    raw = stream.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError("JSON input exceeds the byte limit")
    return json.loads(raw.decode("utf-8-sig"))


def load_issue(args: argparse.Namespace) -> Issue:
    if args.split:
        if not args.repo or args.number is None:
            raise ValueError("--split requires --repo and --number")
        path = ROOT / "data" / "snapshot" / f"{args.split}.json"
        with path.open("rb") as stream:
            rows = read_json(stream, MAX_SNAPSHOT_BYTES)
        if not isinstance(rows, list):
            raise ValueError("snapshot must contain an array")
        matches: list[Issue] = []
        for row in cast(list[object], rows):
            if isinstance(row, dict):
                entry = cast(dict[str, object], row)
                if entry.get("repo") == args.repo and entry.get("number") == args.number:
                    matches.append(Issue.model_validate(entry))
        if len(matches) != 1:
            raise ValueError("expected exactly one matching issue in the snapshot")
        return matches[0]
    if args.number is not None:
        raise ValueError("--number is only used with --split")
    if args.issue == "-":
        payload = read_json(sys.stdin.buffer, MAX_ISSUE_BYTES)
    else:
        with Path(args.issue).open("rb") as stream:
            payload = read_json(stream, MAX_ISSUE_BYTES)
    if args.repo:
        if not isinstance(payload, dict):
            raise ValueError("input must be a single issue object")
        payload = {**cast(dict[str, object], payload), "repo": args.repo}
    return Issue.model_validate(payload)


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if arguments and arguments[0] in ("route", "batch"):
        from triage.routing_cli import main as routing_main

        return routing_main(arguments)
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--issue", metavar="PATH", help="single issue JSON file; - reads stdin")
    source.add_argument("--split", choices=["train", "dev"], help="select from an unsealed snapshot")
    parser.add_argument("--repo", choices=["litestar", "hono", "textual"])
    parser.add_argument("--number", type=int)
    parser.add_argument("--model", help="DSPy provider/model; defaults to LLM_MODEL in .env")
    args = parser.parse_args(arguments)
    try:
        issue = load_issue(args)
    except (OSError, ValueError, RecursionError):
        print("Invalid input: supply one issue with repo, positive number, nonblank title, and body; "
              "issue JSON must be at most 1 MiB and snapshots at most 16 MiB; "
              "snapshot selection requires a matching --repo and --number.", file=sys.stderr)
        return 2
    try:
        from triage.extract import DSPyExtractor

        extractor = DSPyExtractor(args.model)
    except Exception:
        # Initialization exceptions may include provider credentials or URLs.
        print("Configuration error: check LLM_MODEL, the provider API key in .env, "
              "and installed dependencies.", file=sys.stderr)
        return 2
    try:
        record = triage_issue(issue, extractor)
    except (ValidationError, ValueError):
        print("Triage failed: model output did not satisfy the triage schema or project taxonomy.",
              file=sys.stderr)
        return 1
    except Exception:
        # Provider exceptions can contain credentials or issue text. Do not echo them.
        print("Triage failed: model request failed. Check credentials, model access, and connectivity.",
              file=sys.stderr)
        return 1
    print(record.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
