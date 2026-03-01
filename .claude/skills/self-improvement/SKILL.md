---
name: self-improvement
description: "Run the agent capability improvement loop. Spawns agents on real tasks, scores their output with Observer disposition weights, extracts failure patterns, and persists learnings. Codex writes synthetic baseline weights for new agent types. Use when the user says 'run the loop', 'improve agents', 'self-improvement cycle', or after a batch of agent team runs to score and extract patterns."
tags: [agents, improvement, scoring, codex, disposition, weights]
---

# Self-Improvement Loop

Run agents. Score them. Extract patterns. Adjust weights. Compound.

## When to Use

- User says "run the loop", "self-improvement", "improve agents"
- After a `/swarm` run to score team output quality
- To generate Codex disposition weights for a new agent type
- To review accumulated cycle data and extract cross-cycle patterns

## When NOT to Use

- Single agent tasks that don't need scoring
- Production monitoring

---

## The Loop (4 steps)

```
1. BASELINE    Codex writes disposition weights from agent role description
2. RUN         Agent executes a real task
3. SCORE       Observer scores output using disposition weights
4. ADJUST      Patterns extracted, weights updated, learnings persisted
```

## Quick Start

### Run a single cycle

```
/self-improvement

1. Pick an agent type (Explore, GP, Plan)
2. Pick a real task
3. Spawn the agent
4. Spawn the Observer to score it
5. Write cycle report to memory/cycles/
```

### Generate Codex weights for a new agent type

```
codex.cmd exec --full-auto \
  -o ".claude/agents/capability-loop/memory/agents/{type}_weights.py" \
  -C "$(pwd)" \
  "Generate disposition weights for a {ROLE} agent that {DESCRIPTION}.
   Output a Python class with AttentionAllocation (must sum to 1.0),
   QualityThresholds (GOLDEN > PASS > MARGINAL > FAIL),
   ErrorSensitivity (0.0-1.0, severity not frequency),
   domain-specific params. All weights as explicit floats.
   3-5 inner classes max."
```

### Review accumulated cycles

Read `glob .claude/agents/capability-loop/memory/cycles/*.json` and extract cross-cycle patterns.

---

## Agent Roster

| Agent | Model | Role | Definition |
|-------|-------|------|------------|
| **Orchestrator** | Opus | Runs the loop | `.claude/agents/capability-loop/orchestrator.md` |
| **Observer** | Sonnet | Scores agent output | `.claude/agents/capability-loop/observer.md` |
| **Analyst** | Haiku | Finds cross-run patterns | `.claude/agents/capability-loop/analyst.md` |
| **Validator** | Sonnet | Regression checks | `.claude/agents/capability-loop/validator.md` |
| **Librarian** | Haiku | Persists learnings | `.claude/agents/capability-loop/librarian.md` |

## Codex-Generated Weight Baselines

| Agent Type | File | Key Finding |
|------------|------|-------------|
| Explore | `memory/agents/explore_weights.py` | NARROW_SCOPE_MISS=0.89 highest |
| General-purpose | `memory/agents/general_purpose_weights.py` | DESTRUCTIVE_BASH=0.98 highest |
| Plan | `memory/agents/plan_weights.py` | NO_CODEBASE_READ=1.00 highest |

## Scoring Protocol

Observer uses these disposition weights:

```python
class AttentionAllocation:
    FAILURE_MODE_DETECTION = 0.40
    TASK_COMPLETION = 0.25
    EFFICIENCY = 0.15
    CORRECTNESS = 0.20

class QualityThresholds:
    GOLDEN = 0.90
    PASS = 0.70
    MARGINAL = 0.50
    FAIL = 0.30
```

## Weight Adjustment Formula

```python
new_weight = old_weight + (delta * LEARNING_RATE)
new_weight = clamp(0.0, 1.0, new_weight)
LEARNING_RATE = 0.1  # 10% of suggested change per cycle
```

## Storage

```
.claude/agents/capability-loop/
├── orchestrator.md, observer.md, analyst.md, validator.md, librarian.md
├── codex-weight-directive.md
└── memory/
    ├── agents/{type}_weights.py    # Codex-generated baselines
    └── cycles/cycle_{NNN}.json     # Scored cycle reports
```

## Key Insight

Codex-written weights give agents a strong baseline without manual tuning. The loop then refines from there. This cuts the improvement cycle in half -- you skip the discovery phase and go straight to adjustment.
