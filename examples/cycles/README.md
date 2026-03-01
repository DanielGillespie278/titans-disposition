# Improvement Cycle Examples

These JSON files document two improvement cycles from development:

## cycle_013.json — The Turning Point

Cycle 013 was the first cycle where **structural protocols** activated:

- **TriageProtocol**: Exploration ratio dropped from 4.6x to 1.13x on first activation
- **CitationProtocol**: Citation accuracy went from 0/4 to 5/5
- Overall score: 0.66 (lowest in the series at that point)

The low score was expected — protocols were untested and the cycle was experimental. But the *directional signals* were unmistakable: binary structural changes succeed in O(1) where continuous weight nudges fail.

## cycle_016.json — First GOLDEN

Cycle 016 was the first to achieve GOLDEN status (>= 0.90):

- Score: 0.93
- All structural protocols stable for 3+ consecutive cycles
- First cycle to come in under budget (0.88x exploration ratio)
- Task-relevant exploration was near-perfect

The gap from 013 to 016 illustrates the key insight from the [Inverse Reward Design](../../docs/research/INVERSE_REWARD_DESIGN.md) research: deficit-chasing on weight deltas produces active decline, but structural protocols succeed immediately and compound.

## How to Read Cycle Reports

Each JSON file contains:

| Field | Type | Meaning |
|-------|------|---------|
| `cycle_id` | int | Sequential cycle number |
| `timestamp` | string | When the cycle ran |
| `score` | float | Observer composite score (0-1) |
| `band` | string | GOLDEN (>=0.90), PASS (>=0.70), MARGINAL (>=0.50), FAIL (<0.50) |
| `dimensions` | object | Per-dimension scores (D1-D6) |
| `gate_scores` | object | Binary gate pass/fail results |
| `continuous_scores` | object | Continuous quality metrics |
| `protocols_active` | list | Which structural protocols were active |
| `weight_changes` | object | Disposition weight adjustments applied |
