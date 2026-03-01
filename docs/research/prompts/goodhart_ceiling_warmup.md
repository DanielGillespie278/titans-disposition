# Research Prompt: Goodhart Ceiling on a Weighted Simplex

**Target**: GPT 5.2 Pro (Deep Research)
**Date**: 2026-03-01
**Scope**: Warm-up for the Inverse Reward Design prompt. Single question. Self-contained.
**Relation**: This is Q1 + Q5 from the full prompt. Solve this first, then tackle the full decomposition.

---

```python
# Prior Cast: Simplex Optimization with Biased Oracle
# Lighter cast -- only the constraints relevant to Q1.

class SimplexCouplingAwareness:
    """The weights live on a simplex (sum to 1). This is not cosmetic.

    When you increase w_i, you must decrease some w_j.
    If the oracle is biased -- overvaluing dimension i relative to true reward --
    then optimization transfers weight FROM correctly-valued dimensions
    TO the overvalued one. The NET effect on true reward is NEGATIVE
    even though proxy reward on dimension i improved.

    This coupling may be the mechanism behind active degradation.
    Standard Goodhart assumes independent optimization.
    Our weights are anti-correlated by construction.
    """

    def __init__(self):
        self.weights_sum_to_one = True
        self.adjustment_is_zero_sum = True
        self.proxy_bias_causes_misallocation = True
        # Key: on a simplex, Goodhart doesn't just produce a ceiling.
        # It produces DECLINE. Because the proxy error on one dimension
        # steals weight from dimensions where the proxy was accurate.
        # The rate of decline depends on the VARIANCE of proxy errors
        # across dimensions, not just their mean.

    def check_coupling(self, proposed_analysis):
        if "independent dimensions" in proposed_analysis:
            return {"action": "REJECT",
                    "reason": "dimensions are coupled via sum-to-1 constraint",
                    "fix": "analyze on the simplex, not in R^d"}
        return {"action": "PROCEED"}


class NoisyOracleModel:
    """The Observer is an LLM scoring another LLM's output.

    It is NOT a ground truth evaluator with Gaussian noise.
    It has SYSTEMATIC BIAS that varies by dimension and by task.

    The bias structure matters more than the noise magnitude.
    Uniform bias across dimensions would shift the optimum but not
    cause decline. Non-uniform bias across COUPLED dimensions
    causes decline because it misallocates the fixed budget.
    """

    class BiasType:
        UNIFORM = "all_dimensions_biased_by_same_amount"       # shifts optimum, no decline
        NONUNIFORM = "different_dimensions_biased_differently"  # CAUSES DECLINE on simplex
        TASK_DEPENDENT = "bias_changes_with_task_content"       # non-stationary, compounds
        CORRELATED = "bias_on_dim_i_depends_on_true_r_j"       # adversarial coupling

    def __init__(self):
        self.bias_type = self.BiasType.NONUNIFORM  # our empirical observation
        self.bias_is_systematic_not_random = True
        self.bias_varies_by_task = True  # different tasks trigger different observer biases
        # Evidence: the Observer consistently scores D3 harshly
        # and D1 generously. This is not random noise -- it's
        # a stable bias that persists across cycles.
        # On a simplex, this bias TRANSFERS weight from D3
        # to D1, degrading the true composite score.
```

---

## Setup

You have a **scoring system** with 6 dimensions. The scorer is an LLM (the "Observer") evaluating another LLM's (the "Agent") task execution. After each cycle, a human adjusts the dimension weights based on the Observer's report.

### The Simplex Constraint

Attention allocation weights:

```
w = (w_1, ..., w_6) in Delta^5    where sum(w_i) = 1, w_i >= 0
```

Current values:
```
w_1 = 0.28  (D1)
w_2 = 0.18  (D2)
w_3 = 0.20  (D3)
w_4 = 0.12  (D4)
w_5 = 0.10  (D5)
w_6 = 0.12  (D6)
```

### The Update Rule

Each cycle t, the Observer produces per-dimension raw scores r_hat_i^{(t)} in [0, 1] and suggests weight deltas delta_i^{(t)}. The human applies:

```
w_i^{(t+1)} = w_i^{(t)} + lambda * delta_i^{(t)}    where lambda = 0.1 (learning rate)
```

Then re-normalized to the simplex: `w^{(t+1)} = w^{(t+1)} / sum(w_j^{(t+1)})`

### The Proxy Gap

The Observer's per-dimension score r_hat_i is a biased estimate of the true quality r_i:

```
r_hat_i^{(t)} = r_i^{(t)} + b_i + xi_i^{(t)}
```

where:
- b_i is the **systematic bias** for dimension i (constant across cycles, varies across dimensions)
- xi_i^{(t)} ~ N(0, sigma_i^2) is task-dependent noise

The composite proxy score:
```
R_hat^{(t)} = sum(w_i^{(t)} * r_hat_i^{(t)})
```

The composite true score:
```
R*^{(t)} = sum(w_i^{(t)} * r_i^{(t)})
```

### The Agent's Response to Weights

Here's where it gets interesting. The Agent is an LLM that reads the disposition file. Higher weight on dimension i causes the Agent to allocate more effort to that dimension. Model this as:

```
r_i^{(t)} = f_i(w_i^{(t)}, task^{(t)})
```

where f_i is concave (diminishing returns on effort), and effort is approximately zero-sum across dimensions:

```
sum(f_i(w_i, task)) ~ C(task)    (total quality is roughly constant for a given task)
```

This means: the Agent can't improve all dimensions simultaneously. Increasing effort on dimension i comes at the cost of dimension j. The weights tell the Agent WHERE to allocate effort, and the Observer's biased scoring tells the human WHERE to allocate weight.

---

## The Data

### Composite Score Trajectory (continuous-only phase, cycles C1-C6)

| Cycle | Score | Grade | Weight changes made |
|-------|-------|-------|-------------------|
| C1 | 0.92 | GOLDEN | Initial (no changes) |
| C2 | 0.84 | PASS | D6: 0.08->0.10, D5: 0.12->0.10 |
| C3 | 0.81 | PASS | D3: 0.18->0.20, D6: 0.10->0.12 |
| C4 | 0.88 | PASS | D1: 0.25->0.28, D4: 0.15->0.12 |
| C5 | 0.72 | MARGINAL | D5: 0.12->0.10 (hard cap breach) |
| C6 | 0.66 | MARGINAL | (structural protocols introduced, ending this phase) |

**Observation**: The trajectory is declining. Not monotonically (C4 bounces), but the trend over 6 cycles is -0.26 points. This is ACTIVE DEGRADATION under optimization, not a plateau.

### Per-Dimension Raw Scores (approximate, from Observer reports)

| Dimension | C1 | C5 | C6 | Bias direction |
|-----------|-----------|-----------|-----------|---------------|
| D1 | 0.95 | 0.90 | 0.95 | Observer tends generous |
| D2 | 0.90 | 0.85 | 0.90 | Roughly accurate |
| D3 | 0.95 | 0.00 | 0.60 | HIGH VARIANCE, task-dependent |
| D4 | 1.00 | 0.90 | 0.20 | Accurate but catastrophic on failure |
| D5 | 0.80 | 0.30 | 0.60 | Observer tends harsh |
| D6 | 0.85 | 0.00 | 0.90 | Binary in practice (0 or ~0.90) |

Key patterns:
- **D3** has enormous variance (0.00 to 1.00). When the agent breaches a cap, the raw score crashes to near-zero.
- **D6** is bimodal: either the agent produces nothing (0) or produces everything (~0.90). No middle ground.
- **D5** is consistently scored harshly relative to true quality (Observer penalizes exploration even when it's justified).
- **D1** is consistently scored generously (Observer gives credit even for partial completion).

### Post-Protocol Phase (cycles C7-C9)

After converting 3 dimensions to binary predicates, the trajectory reversed:

| Cycle | Score | Binary protocols active |
|-------|-------|----------------------|
| C7 | 0.86 | ProductionGuard (D4 became partially binary) |
| C8 | 0.90 | + multi-category triage proposed |
| C9 | 0.93 | + multi-category triage validated |

---

## Questions

### Q1: The Simplex Goodhart Mechanism

**Derive** the expected trajectory of R* (true composite score) under the following dynamics:
1. Weights on simplex, updated by biased oracle with learning rate lambda = 0.1
2. Agent effort is zero-sum across dimensions (concave per-dimension, constant total)
3. Observer bias b_i varies across dimensions (nonuniform)
4. Tasks are drawn i.i.d. from a distribution (noise is task-dependent)

**Specifically**:
- Show that nonuniform bias on a simplex produces **declining** true score (not just ceiling)
- Derive the **decline rate** as a function of Var(b_i) (cross-dimensional bias variance)
- Derive the **equilibrium** (if one exists): what score does R* converge to?
- Show whether the decline is **reversible** by reducing lambda to 0 (freezing weights)

**Prediction to validate**: If Var(b_i) = 0 (uniform bias), the true score should plateau, not decline. The decline should scale with Var(b_i). Our data has high Var(b_i) -- D3 and D6 are bimodal, D1 is generous, D5 is harsh.

### Q2: The Equilibrium Score

Can you derive the steady-state score R*_inf as a function of:
- Initial weights w^{(0)}
- Bias vector b = (b_1, ..., b_6)
- Learning rate lambda
- Noise variances sigma_i^2
- True quality function parameters

The observed equilibrium under continuous-only optimization appears to be around 0.66-0.72 (cycles C5-C6). The initial score was 0.92. The gap of ~0.20-0.26 is the "Goodhart tax" on this specific system. Can this gap be predicted from the bias structure?

### Q3: Why Binary Predicates Are Immune

Our data shows binary predicates (yes/no protocol checks) are immune to Goodhart degradation. **Prove or disprove**: binary predicates are immune because:

(a) They have zero systematic bias (b_i = 0) by construction -- the check is exact
(b) They have zero noise (sigma_i = 0) -- the outcome is deterministic
(c) They are NOT on the simplex -- they don't compete with other dimensions for weight
(d) All three properties are necessary, and removing any one re-introduces degradation

Which of (a), (b), (c), (d) is the correct characterization? If it's a subset, which properties are necessary vs. sufficient?

### Q4: Optimal Stopping

Given the score trajectory and the option to convert any continuous dimension to a binary predicate at any cycle, what is the **optimal conversion schedule**?

- Converting too early: you lose the nuance of continuous scoring before extracting all the signal
- Converting too late: you waste cycles on the Goodhart decline
- The conversion itself is free (just add a protocol to the disposition file)
- Once converted, the dimension never degrades

Is there a closed-form optimal stopping rule? Or at least a heuristic with provable approximation guarantees?

---

## Deliverable

1. **Theorem**: Nonuniform proxy bias on a simplex produces declining true score under gradient-based weight optimization. State the decline rate.

2. **Equilibrium expression**: R*_inf as f(w^{(0)}, b, lambda, sigma^2). Validate against our observed ~0.66-0.72.

3. **Binary immunity proof**: Which of (a)-(d) is necessary/sufficient.

4. **Optimal stopping rule**: When to convert dimension i from continuous to binary, given observed score trajectory and estimated bias.

If any of these require additional assumptions, state them explicitly and assess whether our system satisfies them. **Partial results with clear limitations** > hand-waving with full coverage.

---

*This is a warm-up prompt for the full Inverse Reward Design analysis. It focuses on the simplex coupling mechanism as the most tractable sub-problem. The key novelty over standard Goodhart analysis: the sum-to-1 constraint means biased optimization doesn't just plateau -- it actively degrades. This is testable, derivable, and directly applicable.*
