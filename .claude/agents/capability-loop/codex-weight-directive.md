# Codex Weight Directive

Generate disposition weights for agent team members. This directive is sent to Codex Spark to produce synthetic baseline weights that cut the improvement loop in half.

## The Directive (copy-paste to Codex)

```
You are generating DISPOSITION WEIGHTS for a Claude Code agent.

INPUT: An agent role description (what the agent does, what tools it has, what it produces).

OUTPUT: A Python class with explicit numerical weights covering:
1. AttentionAllocation -- what % of focus goes to each concern (must sum to 1.0)
2. QualityThresholds -- numerical cutoffs for GOLDEN/PASS/MARGINAL/FAIL grades
3. ErrorSensitivity -- 0.0-1.0 weight for how severely each error type should be penalized
4. Domain-specific weights -- any role-specific numerical parameters

RULES:
- Every weight is a float between 0.0 and 1.0
- AttentionAllocation weights MUST sum to 1.0
- QualityThresholds MUST be ordered: GOLDEN > PASS > MARGINAL > FAIL
- ErrorSensitivity weights reflect SEVERITY not FREQUENCY
- Include __init__ that sets all defaults as instance attributes
- Include a score() method stub showing the return shape
- NO prose explanations -- the numbers ARE the explanation
- 3-5 inner classes maximum -- more dilutes the signal

ROLE DESCRIPTION:
{paste agent role here}
```

## Usage

```bash
# Generate weights for a new agent type
codex.cmd exec --full-auto -o weights_output.py -C "$(pwd)" \
  "$(cat .claude/agents/capability-loop/codex-weight-directive.md | head -30) ROLE DESCRIPTION: [paste role]"

# Or inline
codex.cmd exec --full-auto -o weights_analyst.py -C "$(pwd)" \
  "Generate disposition weights for an ANALYST agent that reads multiple Observer reports, identifies recurring failure patterns across agent runs, clusters similar failures, and outputs a ranked pattern list with frequency and severity scores. Output a Python class with AttentionAllocation, QualityThresholds, ErrorSensitivity, and ClusteringParams inner classes. All weights as floats 0.0-1.0. AttentionAllocation must sum to 1.0."
```

## Loop Integration

```
Codex writes baseline weights
    |
    v
Agent runs with weights in its .md definition
    |
    v
Observer scores the run
    |
    v
Delta between expected and actual score
    |
    v
Codex adjusts weights (+=delta * learning_rate)
    |
    v
Updated weights written back to agent .md
```

The key insight: instead of Run -> Score -> Extract -> Harden -> Validate -> Run (6 steps),
we get: Codex writes weights -> Run -> Score -> Adjust weights -> Run (4 steps).

The Analyst and Hardener agents collapse because the structure already exists --
you're adjusting numbers in a known format, not discovering structure from scratch.
