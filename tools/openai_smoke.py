"""Run the one-sentence Chat Completions example: uv run python tools/openai_smoke.py."""

from __future__ import annotations

import os
from pathlib import Path
import sys

from dotenv import load_dotenv
from openai import APIConnectionError, APIStatusError, OpenAI


def main() -> int:
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    if not os.getenv("OPENAI_API_KEY"):
        print("Set OPENAI_API_KEY in .env before running this example.", file=sys.stderr)
        return 1

    try:
        with OpenAI(timeout=30.0, max_retries=0) as client:
            response = client.chat.completions.create(
                model="gpt-5-mini",
                messages=[{
                    "role": "user",
                    "content": "Explain what is an AI agent in one sentence.",
                }],
            )
        print(response.choices[0].message.content)
    except APIConnectionError:
        print("Could not connect to the OpenAI API.", file=sys.stderr)
        return 1
    except APIStatusError as exc:
        if exc.code == "insufficient_quota":
            message = "OpenAI API quota is exhausted; check API billing and project limits."
        elif exc.status_code == 429:
            message = "OpenAI API returned HTTP 429; check request limits and available API quota."
        else:
            message = f"OpenAI API request failed (HTTP {exc.status_code})."
        print(message, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
