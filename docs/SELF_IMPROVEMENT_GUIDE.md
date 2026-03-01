# Self-Improvement Guide

How to run the capability improvement loop end-to-end: from first cycle to GOLDEN.

---

## What the Loop Does

The self-improvement loop is a structured process for scoring agent output and adjusting disposition weights based on evidence. It runs through four agents in sequence:

```
Observer  -->  Analyst  -->  Validator  -->  Librarian
(score)       (cluster)     (check)        (persist)
```

### Observer

Watches an agent execute a task and produces a structured quality report. Scores each dimension of the disposition (attention allocation, error sensitivity, protocol compliance) against the weights defined in the disposition file.

Output: A JSON report with per-dimension scores, grade (GOLDEN/PASS/MARGINAL/FAIL), and narrative observations.

### Analyst

Takes Observer reports from multiple cycles and clusters failure patterns. Computes suggested weight deltas based on the pattern of scores over time. Identifies which dimensions are improving, which are stuck, and which are degrading.

Output: Suggested weight deltas, identified anti-patterns, structural fix proposals.

### Validator

Regression-checks the Analyst's proposed weight changes against historical data. Ensures that proposed changes don't revert previously fixed issues or introduce known failure modes.

Output: APPROVE, CONDITIONAL (needs human review), or REJECT with reason.

### Librarian

If the Validator approves, the Librarian persists the changes: updates disposition weights in the agent definition file, writes the cycle report to the memory directory, and updates the cumulative pattern index.

Output: Updated disposition file, archived cycle report.

---

## Prerequisites

1. **Claude Code** installed and configured
2. **TITANS Disposition** installed (`pip install titans-disposition`)
3. A **disposition file** for the agent type you want to improve (or generate one -- see below)
4. The `/self-improvement` skill installed (copy from `.claude/skills/self-improvement/`)

### Generating a Disposition File for a New Agent Type

If you don't have a disposition file yet, generate one:

```bash
# Using Codex (recommended for consistency)
codex exec --full-auto \
  -o ".claude/dispositions/my-agent.py" \
  "Generate disposition weights for a [ROLE] agent that [DESCRIPTION].
   Output a Python class with AttentionAllocation (must sum to 1.0),
   QualityThresholds (GOLDEN > PASS > MARGINAL > FAIL),
   ErrorSensitivity (0.0-1.0, severity not frequency),
   domain-specific params. All weights as explicit floats.
   3-5 inner classes max."
```

Or start from an existing baseline in `.claude/dispositions/`:

| Baseline | Best For |
|----------|----------|
| `general-purpose.py` | General coding tasks, bug fixes, refactoring |
| `explore.py` | Research, investigation, broad exploration |
| `plan.py` | Planning, architecture, design documents |

---

## Running `/self-improvement`

In Claude Code, invoke the skill:

```
/self-improvement
```

The orchestrator will guide you through:

1. **Pick an agent type** (Explore, GP, Plan, or a custom type)
2. **Pick a real task** (not synthetic -- the loop learns from genuine work)
3. **Spawn the agent** to execute the task
4. **Spawn the Observer** to score the output
5. **Write the cycle report** to the memory directory

### Manual Execution (without the skill)

If you prefer to run steps manually:

```bash
# Step 1: Agent executes a task (this is your normal workflow)
# Just use Claude Code normally on a real task

# Step 2: Score the output
titans observe \
  --input task_output.json \
  --disposition .claude/dispositions/general-purpose.py \
  --output .claude/agents/01-capability-loop/memory/cycles/cycle_019.json

# Step 3: Analyse across cycles
titans analyse \
  --cycles .claude/agents/01-capability-loop/memory/cycles/ \
  --output analysis_report.md

# Step 4: Review and apply (human decision)
# Read the analysis report, approve or reject suggested changes
```

---

## Reading Cycle Reports

Each cycle produces a JSON report in `.claude/agents/01-capability-loop/memory/cycles/`. Here's how to read one:

```json
{
  "cycle_id": "019",
  "timestamp": "2026-03-01T15:30:00Z",
  "agent_type": "general-purpose",
  "task_summary": "Fix flaky integration tests in the memory module",
  "composite_score": 0.88,
  "grade": "PASS",
  "dimension_scores": {
    "task_alignment": 0.95,
    "read_before_write": 0.85,
    "tool_safety": 0.90,
    "leader_sync": 0.80,
    "concise_delivery": 0.85,
    "citation_traceability": 0.90
  },
  "gate_results": {
    "TriageProtocol": "PASS",
    "CitationProtocol": "PASS",
    "ProductionGuard": "PASS"
  },
  "observations": [
    "Agent read all relevant files before editing",
    "Exploration ratio 1.2x within tier budget",
    "All citations include file:line references"
  ],
  "suggested_deltas": {
    "leader_sync": +0.02,
    "concise_delivery": -0.01
  }
}
```

### Key Fields

| Field | What It Tells You |
|-------|-------------------|
| `composite_score` | Weighted average across all dimensions |
| `grade` | Human-readable quality band |
| `dimension_scores` | Per-dimension breakdown -- where the agent is strong/weak |
| `gate_results` | Binary protocol compliance -- PASS or FAIL |
| `suggested_deltas` | Analyst's recommended weight changes |

---

## Understanding Scores

### Grade Bands

| Grade | Score Range | Meaning |
|-------|------------|---------|
| **GOLDEN** | >= 0.92 | Exceptional. All dimensions strong, all protocols passing. |
| **PASS** | >= 0.78 | Good. Minor weaknesses but no failures. Ship-quality. |
| **MARGINAL** | >= 0.62 | Concerning. One or more dimensions significantly weak. Needs attention. |
| **FAIL** | < 0.62 | Unacceptable. Major failures present. Don't ship. |

### Score Trajectory Patterns

| Pattern | What It Means | Action |
|---------|--------------|--------|
| Steady rise | Weights are well-calibrated, agent is learning | Continue, don't over-adjust |
| Plateau | Hit the Goodhart ceiling on continuous dimensions | Convert weakest dimension to binary predicate |
| V-shape dip | Catastrophe followed by recovery | Check if a binary protocol is needed to prevent recurrence |
| Steady decline | Deficit-chasing on biased dimensions | STOP weight nudging, convert dimensions to binary gates |
| Oscillation | Weights overcorrecting each cycle | Reduce learning rate (lambda) |

### The V-Shape Recovery (Canonical Example)

The most common pattern across 18 validated cycles:

```
C1:  0.92  GOLDEN    (baseline, before optimization)
C2:  0.84  PASS      (weight nudges begin, slight decline)
C3:  0.81  PASS      (continued nudging, further decline)
C4:  0.88  PASS      (bounce, but trend is down)
C5:  0.72  MARGINAL  (catastrophe -- 0.0 on two dimensions)
C6:  0.66  MARGINAL  (trough)
        <-- binary protocols introduced here -->
C7:  0.86  PASS      (immediate recovery)
C8:  0.90  PASS      (continued improvement)
C9:  0.93  GOLDEN    (surpasses original baseline)
```

The inflection point is precisely where binary structural protocols replace continuous weight nudging. This V-shape is not coincidence -- it's the formal consequence of removing Goodhart-vulnerable dimensions from the deficit-chasing loop. See `docs/research/INVERSE_REWARD_DESIGN.md` for the mathematical proof.

---

## What Gets Persisted

Each cycle persists the following:

| Artifact | Location | Purpose |
|----------|----------|---------|
| Cycle report | `.claude/agents/01-capability-loop/memory/cycles/cycle_NNN.json` | Raw scores and observations |
| Analyst report | `.claude/agents/01-capability-loop/memory/analyst_report_NNN.md` | Cross-cycle pattern analysis |
| Disposition file | `.claude/dispositions/<type>.py` | Updated weights (if approved) |
| Weight history | `.titans/gate_history.jsonl` | Audit trail of all deposits |

### What NOT to Persist

- Intermediate agent output (too large, not useful for the loop)
- Raw task content (privacy -- the loop learns from scores, not content)
- Rejected weight changes (logged in cycle report, not applied to disposition)

---

## Example: From First Cycle to GOLDEN

### Cycle 1: Baseline

Run any agent on a real task. Score it. This establishes your baseline.

```
Score: 0.82 (PASS)
Weak dimensions: citation_traceability (0.40), concise_delivery (0.65)
Strong dimensions: task_alignment (0.95), tool_safety (0.90)
```

**Action**: Note the weak dimensions. Don't adjust weights yet -- you need more data points.

### Cycles 2-4: Weight Nudging Phase

Try adjusting weights toward weak dimensions. Monitor whether scores improve.

```
Cycle 2: 0.80 (PASS)  -- citation_traceability still 0.40 despite weight increase
Cycle 3: 0.78 (PASS)  -- concise_delivery dropped, other dims compensating
Cycle 4: 0.76 (MARGINAL) -- declining trend visible
```

**Diagnosis**: Weight nudges on citation_traceability had zero effect across 3 cycles. This is the Goodhart signal -- the continuous weight is not reaching the agent's behaviour.

### Cycle 5: First Binary Protocol

Convert citation_traceability to a binary predicate:

```python
class CitationProtocol:
    """Every fix must cite file:line. Binary check."""
    enabled = True
    format = "file:line"
    minimum_citations = 1
```

```
Cycle 5: 0.85 (PASS) -- citation_traceability jumps to 0.90
```

**Result**: Immediate fix. The binary predicate succeeded on first activation.

### Cycles 6-8: Continued Protocol Conversion

Identify the next weakest continuous dimension. If weight nudges don't move it in 2-3 cycles, convert.

```
Cycle 6: 0.88 (PASS)  -- added TriageProtocol for exploration budgets
Cycle 7: 0.90 (PASS)  -- stable, all protocols passing
Cycle 8: 0.93 (GOLDEN) -- first GOLDEN with all protocols active
```

### The Pattern

1. Start with continuous weights (flexible, nuanced)
2. Nudge for 2-3 cycles (test whether continuous optimisation works)
3. If a dimension doesn't respond to nudging, convert to binary (structural fix)
4. Each conversion removes a Goodhart-vulnerable dimension from the simplex
5. Repeat until the remaining continuous dimensions are genuinely responsive to weight adjustment

The stopping criterion (from the formal analysis): convert dimension i if `delta_T_i > c_i + L_i` where delta_T_i is the cycle savings from conversion and c_i + L_i is the engineering cost plus granularity loss. Stop converting when no dimension satisfies this inequality.

---

## Advanced: Team-Level Scoring

When running agent teams (multiple agents coordinating on a task), additional considerations apply:

1. **Correlated failures**: If one agent blocks another, multiple dimensions crash simultaneously
2. **Coordination quality**: Must be gated as a binary predicate BEFORE enabling deficit-chasing on team scores
3. **Decouple before you optimize**: Run team scoring in read-only mode first, then enable feedback control

See `docs/research/INVERSE_REWARD_DESIGN.md` (Team-Level Application section) for the formal analysis.

---

## FAQ

**Q: How many cycles before I see improvement?**
A: Binary protocols show improvement in 1 cycle. Continuous weight optimisation takes 4-6 cycles to reveal whether it's working or Goodharting. Budget ~10 cycles for a full baseline-to-GOLDEN arc.

**Q: How much does each cycle cost?**
A: Using Claude Code with Max subscription: $0 per cycle (included in subscription). Using API: ~$15 per cycle depending on task complexity.

**Q: Can I run the loop automatically?**
A: The Observer, Analyst, and Librarian can run automatically. The Validator step intentionally requires human review. As more dimensions are converted to binary (verifiable) gates, less human review is needed per cycle.

**Q: What if my scores oscillate instead of converging?**
A: Reduce the learning rate (lambda) in the Analyst configuration. Oscillation means the step size is too large relative to the noise in the scoring.

---

*TITANS Disposition v0.1.0*
