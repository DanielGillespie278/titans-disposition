"""
Replay History — Feed Claude Code logs through TITANS gates
============================================================

Reads a Claude Code conversation log and replays prompts through the
disposition engine, showing how the M-vector would have evolved.

Run: python examples/replay_history.py [path_to_conversation.jsonl]

If no path is given, uses a small built-in demo dataset.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from titans_disposition import DispositionEngine


# Built-in demo: simulates a typical development session
DEMO_PROMPTS = [
    "Add a new FastAPI endpoint for user authentication",
    "Fix the type error in the response model",
    "That's wrong, use Pydantic v2 model_validator not validator",
    "Add unit tests for the auth endpoint",
    "Refactor the database session management",
    "What should we work on next?",
    "Check the gradient norm on the TITANS substrate",
    "Fix the login timeout — it's returning 504",
    "That's not right, the timeout should be on the client side",
    "Add retry logic with exponential backoff",
    "Create the Docker compose configuration",
    "Launch the test suite with coverage",
    "Fix the flaky test in test_auth.py",
    "Actually, just skip that test for now — it's a race condition",
    "Update the README with the new API endpoints",
]


def replay_prompts(
    prompts: list[str],
    conversation_id: str = "replay",
) -> None:
    """Replay a list of prompts through the disposition engine."""
    engine = DispositionEngine(
        conversation_id=conversation_id,
        input_dim=64,
        memory_dim=128,
        auto_save=False,  # Don't persist replay state
    )

    domain_counts: dict[str, int] = {}
    corrections = 0

    print(f"Replaying {len(prompts)} prompts through TITANS gates")
    print("=" * 70)

    for i, prompt in enumerate(prompts, 1):
        result = engine.deposit(prompt)

        domain = result["domain"]
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        if result["is_correction"]:
            corrections += 1

        # Print every prompt with its classification
        flag = " [CORRECTION]" if result["is_correction"] else ""
        print(f"  [{i:3d}] {domain:16s}{flag}")
        print(f"         {prompt[:60]}")
        print(f"         M_norm={result['m_norm']:.4f}  "
              f"gates=(a={result['gates']['alpha']:.4f}, "
              f"t={result['gates']['theta']:.4f}, "
              f"e={result['gates']['eta']:.2f})")
        print()

    # Summary
    print("=" * 70)
    print("SESSION SUMMARY")
    print(f"  Total prompts:   {len(prompts)}")
    print(f"  Corrections:     {corrections} ({corrections/len(prompts)*100:.0f}%)")
    print(f"\n  Domain distribution:")
    for domain, count in sorted(domain_counts.items(), key=lambda x: -x[1]):
        pct = count / len(prompts) * 100
        bar = "#" * int(pct / 2)
        print(f"    {domain:16s} {count:3d} ({pct:4.0f}%) {bar}")

    metrics = engine.read()
    print(f"\n  Final M norm:    {metrics['m_norm']:.4f}")
    print(f"  Update count:    {metrics['update_count']}")


def load_jsonl_prompts(path: Path) -> list[str]:
    """Load prompts from a Claude Code JSONL conversation log."""
    prompts = []
    with open(path, "r") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                # Claude Code logs have 'type' and 'message' or 'content'
                if entry.get("type") == "human" or entry.get("role") == "user":
                    content = entry.get("content") or entry.get("message", "")
                    if isinstance(content, str) and content.strip():
                        prompts.append(content.strip())
            except json.JSONDecodeError:
                continue
    return prompts


if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        if not path.exists():
            print(f"File not found: {path}")
            sys.exit(1)
        prompts = load_jsonl_prompts(path)
        if not prompts:
            print(f"No prompts found in {path}")
            sys.exit(1)
        replay_prompts(prompts, conversation_id=path.stem)
    else:
        print("No log file provided — using built-in demo session\n")
        replay_prompts(DEMO_PROMPTS)
