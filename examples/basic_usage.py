"""
Basic Usage — TITANS Disposition Engine
========================================

Deposit 10 prompts, read M-vector metrics, inspect state.
Run: python examples/basic_usage.py
"""

import numpy as np
from titans_disposition import DispositionEngine

# Create an engine for a conversation
engine = DispositionEngine(
    conversation_id="demo-session",
    input_dim=64,      # Small dims for this demo
    memory_dim=128,
)

# Simulate a coding session
prompts = [
    "Add error handling to the auth module",
    "Create a new endpoint for user profiles",
    "Fix the login timeout bug",
    "Refactor the database connection pool",
    "That's wrong, use async not sync",
    "Update the README with API examples",
    "Check the TITANS M-vector gradient norm",
    "Add unit tests for the parser",
    "What's next on the roadmap?",
    "Launch the agent team swarm with Codex",
]

print("TITANS Disposition — Basic Usage Demo")
print("=" * 50)

for i, prompt in enumerate(prompts, 1):
    result = engine.deposit(prompt)
    print(
        f"[{i:2d}] {result['domain']:16s} "
        f"{'CORRECTION' if result['is_correction'] else '          '} "
        f"M_norm={result['m_norm']:.4f}"
    )

# Read final metrics
print("\n" + "=" * 50)
metrics = engine.read()
print(f"Final state:")
print(f"  M norm:              {metrics['m_norm']:.4f}")
print(f"  Updates:             {metrics['update_count']}")
print(f"  Crystallization:     {metrics['total_crystallization']:.4f}")

# Inspect M-vector
M = engine.get_m_vector()
print(f"\nM-vector shape:        {M.shape}")
print(f"M-vector dtype:        {M.dtype}")
print(f"Non-zero fraction:     {np.mean(np.abs(M) > 0.001):.2%}")
