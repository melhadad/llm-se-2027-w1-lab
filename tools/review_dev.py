"""Run the triage CLI on 20 reproducibly sampled dev issues and save evidence.

Usage: uv run python tools/review_dev.py
Never reads the sealed test split. Model failures remain failures, not stubbed labels.
"""

import argparse
import json
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from triage.models import TriageRecord
from triage.privacy import redact_secrets

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261015


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data/reviews/dev-triage.json")
    parser.add_argument("--model", help="override LLM_MODEL, for example openai/gpt-6.1-sol")
    args = parser.parse_args()
    rows = json.loads((ROOT / "data/snapshot/dev.json").read_text(encoding="utf-8"))
    rng = random.Random(SEED)
    selected = []
    for repo, count in (("hono", 7), ("litestar", 7), ("textual", 6)):
        pool = sorted((row for row in rows if row["repo"] == repo), key=lambda row: row["number"])
        selected.extend(rng.sample(pool, count))
    results = []
    for index, row in enumerate(selected, start=1):
        command = [sys.executable, "-m", "triage.cli", "--split", "dev",
                   "--repo", row["repo"], "--number", str(row["number"])]
        if args.model:
            command.extend(["--model", args.model])
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=300)
        entry = {
            "repo": row["repo"], "number": row["number"],
            "title": redact_secrets(row["title"]), "url": row["url"],
            "gold_type": row.get("gold_type"), "gold_component": row.get("gold_component"),
            "exit_code": result.returncode,
            "stderr": redact_secrets(result.stderr.strip()), "record": None,
        }
        if result.returncode == 0:
            record = TriageRecord.model_validate_json(result.stdout)
            entry["record"] = record.model_dump()
        results.append(entry)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({
            "source": "data/snapshot/dev.json", "seed": SEED, "model_override": args.model,
            "run_at_utc": datetime.now(timezone.utc).isoformat(), "results": results,
        }, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"{index:02}/20 {row['repo']}#{row['number']} exit={result.returncode}", flush=True)
    successful = sum(entry["record"] is not None for entry in results)
    print(f"Completed: {successful}/20 triage records. Evidence: {args.output}")
    return 0 if successful == 20 else 1


if __name__ == "__main__":
    raise SystemExit(main())
