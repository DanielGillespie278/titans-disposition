# Inverse Reward Design in Self-Improvement Loops

> *This research was conducted during development of the titans-disposition engine, analyzing 18 improvement cycles. All dimension names in running-text examples are abstracted as D1-D6. Mathematical formulas and formal results are preserved as-is.*

**Status**: Active research | **Date**: 2026-03-01
**Research prompt**: `docs/research/prompts/inverse_reward_design.md`
**Warm-up prompt**: `docs/research/prompts/goodhart_ceiling_warmup.md`
**Methodology**: Prior-cast Frontier Protocol (Claude warm-up + GPT 5.2 Pro deep solve)

---

## Core Finding

Deficit-chasing on a simplex with nonuniform proxy bias produces **active decline**, not plateau. The decline is exactly proportional to score variance:

```
R_next = R_current - eta * d * Var(s)
```

where `eta` = learning rate, `d` = number of simplex-coupled dimensions, `s` = per-dimension proxy scores.

**Implication**: Catastrophe-style failures (scores hitting 0.0) spike Var(s), causing large one-step drops. This is the formal explanation for the 0.92 -> 0.66 decline observed in cycles C1-C6.

---

## Established Results (validated against 16-cycle data)

### 1. Simplex Decline Mechanism

The deficit-chasing update rule increases weight on dimensions the Observer scores as weak:

```
delta_i proportional to (s_bar - s_i)
```

Equilibrium: equal proxy scores across all dimensions. With zero-sum capability budget C:

```
R*_inf = (C + sum(b_i)) / d
```

**Validated**: d=6, sum(b)=-0.40, observed ~0.66 implies C=4.36. After converting 3 dims to binary (d=3, sum(b_remaining)=-0.05), observed ~0.93 implies C'=2.84. Consistent.

### 2. C Is Not Constant (Catastrophe Dominance)

C_t varies: C_C1=5.90, C_C5=3.35, C_C6=4.55, C_C9=5.12. Variance dominated by catastrophic binary-like failures (0.0 scores), not smooth reallocation.

### 3. Binary Predicates Converge in O(1)

All three structural protocols (TriageProtocol, CitationProtocol, ProductionGuard) succeeded on first activation and remained stable for 3-4 consecutive cycles.

---

## Formal Results (from GPT 5.2 Pro + Claude review)

### Convergence Rate (Theorem 1)

Under linear effort-coupling (q = Cw) and interior regime:

```
||w_t - w*||_2 <= |1 - eta*C|^t * ||w_0 - w*||_2
```

Geometric convergence to fixed point w* = (1/d)1 - (b - b_bar*1)/C.

**Condition**: eta in (0, 2/C). Step size must be small enough.
**Limitation**: Assumes interior regime (no weights hit 0) and linear response. Catastrophes violate linearity.

### One-Step Decline Identity (Proposition -- strongest result)

For a single deficit-chasing step holding scores s fixed:

```
R_next - R = -eta * d * Var(s)
```

When true qualities are roughly equal, Var(s) ~ Var(b), giving:

```
R_next - R ~ -eta * d * Var(b)
```

Maximum decline rate: -eta * d / 4 (since Var(s) <= 1/4 for [0,1]-valued scores).

### Var(s) Per Cycle (numerical validation)

| Cycle | d | Var(s) | d * Var(s) | Context |
|-------|---|--------|------------|---------|
| C1 | 6 | 0.00556 | 0.0333 | All high, tight |
| C5 | 6 | 0.16368 | 0.9821 | **Two 0.0 catastrophes** |
| C6 | 6 | 0.06868 | 0.4121 | One very low + spread |
| C9 | 5 | 0.00170 | 0.00852 | Post-protocol, tight |

Cycle C5 is ~30x worse than C1 in d*Var(s). Catastrophe spikes variance.

### Optimal Label Allocation (Q4.2 -- most actionable new result)

Human labels (n_i) across remaining continuous dimensions should follow:

```
n_i* = N * a_i^(2/3) / sum_j(a_j^(2/3))
```

where a_i = w_i * sigma * sqrt(2 * ln(2d / delta)).

Minimal achievable gap: (sum a_i^(2/3))^(3/2) / sqrt(N).

Cycle savings from converting dimension j:

```
delta_T_j = [S^3 - (S - a_j^(2/3))^3] / (B * epsilon^2)
```

### Z-Scoring Finite-Sample Bound

At T=16 with sigma=0.05, d=6, delta=0.05:

```
|mu_hat_i - mu_i| <= 0.05 * sqrt(2 * ln(240) / 16) ~ 0.04
```

Same order as moderate biases (0.05-0.10). Z-scoring is marginally useful at T=16, reliably useful by T~30.

---

## Sequential Conversion ROI (recomputed after each step)

Parameters: B=1 (one serious continuous judgment per cycle), epsilon=0.05, sigma=0.05, delta=0.05.

### Remaining continuous dimensions

| Dimension | w_i | Bias b_i | a_i | a_i^(2/3) |
|-----------|-----|----------|-----|-----------|
| D1 | 0.28 | ~0.00 | 0.04332 | 0.1246 |
| D2 | 0.18 | ~-0.05 | 0.02785 | 0.0917 |
| D3 | 0.10 | -0.10 | 0.01547 | 0.0622 |

### Step-by-step with diminishing returns

| Step | Convert | delta_T (marginal) | c_j | ROI (delta_T/c_j) | Verdict |
|------|---------|---:|---:|---:|---------|
| 1st | D3 | 4.60 | 1.0 | **4.60** | Convert |
| 2nd | D2 | 3.27 | 1.5 | **2.18** | Convert |
| 3rd | D1 | 0.77 | 3.5 | **0.22** | **Stop** |

**Stopping criterion**: Convert dimension i next if delta_T_i > c_i + L_i (where L_i = granularity loss from binarizing). Stop when no dimension satisfies this.

**Why D1 stops**: With only 1 continuous dimension remaining, all labels go to it automatically -- there's no allocation problem to solve, so the conversion saves almost nothing.

### Engineering cost estimates (c_j)

**D3 (c=1.0 cycle)**:
TriageProtocol already provides infrastructure. Gate = "exploration ratio <= 1.5x of tier budget." One cycle to formalize threshold + validate.

**D2 (c=1.5 cycles)**:
Gate = "Edit on existing file requires prior Read/Grep on that file." Clean tool-sequence predicate. Edge cases: Glob output, new file creation. 1 cycle implement + 0.5 cycle validate.

**D1 (c=3.5 cycles)**:
Inherently subjective. Would need 3-4 verifiable sub-predicates per task type. Better strategy: decompose into cheap sub-gates over time + z-score the residual continuous signal.

---

## Decision Rule (operationalizable)

### When to convert a dimension to binary

Convert dimension i if ANY of:

1. **Catastrophe rate**: Lower confidence bound LCB(p_i) >= p_0 (testable at T=16 via Hoeffding)
2. **Non-responsiveness**: Upper confidence bound UCB(beta_i) < beta_min (needs active perturbation for power)
3. **Cycle savings exceed cost**: delta_T_i > c_i + L_i (the Q4.2 formula)

### When to stop converting

When for every remaining continuous dimension i in the loop:
```
delta_T_i <= c_i + L_i
```

### When z-scoring beats conversion

For the last 1-2 continuous dimensions where conversion cost is high, z-score instead:
```
s_hat_i = (s_i - mu_hat_i) / (sigma_hat_i + epsilon)
```
This removes bias-driven drift without engineering cost, at the expense of noise in early estimates.

---

## Controller Wiring Change (Section 5 -- zero conversion cost)

**Problem**: Gate failures feed into deficit-chasing weight deltas, creating the catastrophe -> variance spike -> reallocation feedback loop.

**Fix**: Route gate failures to a separate pathway.

1. Observer tags each dimension score as `gate_result` (pass/fail from protocol check) or `continuous_score` (Observer's judgment)
2. Analyst computes weight deltas ONLY from continuous scores on dimensions whose gate passed
3. Gate failures route to `suggested_structural_fix` (propose new/modified protocol), not weight deltas

**Effect**: Removes the exact feedback loop that creates the worst troughs. A gate failure on D4 no longer drains weight from D1 via deficit-chasing.

---

## PAC-Bayes Connection (Q6 -- weakest section, needs grounding)

The disposition file maps to a PAC-Bayes prior. True risk is bounded by:

```
True risk <= Empirical proxy risk + epsilon_u + sqrt((KL(Q||P) + ln(2*sqrt(n)/delta)) / (2n))
```

where epsilon_u = proxy gap on unverifiable dimensions.

Converting dimensions to verifiable shrinks epsilon_u, tightening the bound structurally.

**Gap**: KL(Q||P) for the actual disposition file vs a uniform prior is not yet estimated. This would tell us whether the current disposition complexity is justified.

**Gap**: i.i.d. task assumption is violated (tasks are non-stationary). Either holdout evaluation or online/martingale PAC-Bayes needed for a valid guarantee.

---

## Team-Level Application: Correlated Failure Risk

The individual-level analysis implicitly assumes dimensional independence: a 0.0 on D4 doesn't drag D5 to 0.0. At team level, this assumption breaks.

### The Problem: Correlated Catastrophes

A team coordination failure is not one dimension crashing -- it's a shockwave across multiple dimensions simultaneously. If agent A blocks agent B:
- **task_completion** drops (work was blocked)
- **efficiency** drops (agents waited)
- **coordination_quality** drops (handoff failed)

Three dimensions crashing together spikes Var(s) far harder than any single-agent catastrophe.

### Numerical Grounding

| Scenario | d | Var(s) | d * Var(s) | Context |
|----------|---|--------|------------|---------|
| GP catastrophe (C5) | 6 | 0.164 | 0.982 | Two independent 0.0 scores |
| Team GOLDEN (C10) | 6 | 0.00094 | 0.006 | Everything worked |
| Team GOLDEN (C11) | 6 | 0.00123 | 0.007 | Everything worked |
| **Team catastrophe (projected)** | **6** | **~0.25** | **~1.5** | **3 correlated 0.0 scores** |

A team catastrophe with correlated failures produces d*Var(s) ~ 1.5 -- worse than the GP C5 catastrophe (0.982) that took several cycles to recover from. A single bad team cycle could overshoot in one step what individual GP accumulated over multiple cycles.

### Mitigation: Correlation-Risk-First Conversion

**Principle**: At team level, gate conversion priority should be driven by **correlation risk**, not just individual convertibility or ROI.

The individual-level ROI ranking (delta_T_j / c_j) assumes independent dimensions. At team level, converting the highest-correlation dimension first reduces Var(s) across *multiple* correlated dimensions simultaneously, giving outsized returns that the individual ROI formula doesn't capture.

**Team-level conversion priority order:**

| Priority | Dimension | Rationale | Gate Definition |
|----------|-----------|-----------|-----------------|
| 1st | coordination_quality | Highest correlation risk -- cascades into task_completion + efficiency | "Zero task overlap between agents AND verification gated after all tracks complete" (yes/no) |
| 2nd | citation_traceability | Already a gate at individual level; trivial to promote | "Every fix cites file:line" (yes/no) |
| 3rd-4th | Remaining dimensions | Rank by individual delta_T/c once correlation risk is contained | Per-dimension analysis |

Converting coordination_quality and citation_traceability drops d from 6 to 4 and removes the two dimensions most prone to correlated failure spikes.

### Operational Rule: Decouple Before You Optimize

**Do not run deficit-chasing weight updates on team-level scores until coordination_quality is gated.** Score teams continuously (the Observer reports are valuable for diagnosis), but don't feed team scores into the Analyst's weight-delta computation until the simplex is safe.

This follows the same principle as running monitoring in read-only mode before letting it trigger automated responses. The observational value is immediate; the feedback control requires a safe operating envelope first.

### Generalized Decision Procedure

For any new agent team type:
1. Enumerate the team-level scoring dimensions
2. Identify which dimensions have **structural coupling** (failure in one implies failure in another)
3. Convert the most-coupled dimensions to binary gates FIRST, regardless of individual delta_T/c
4. Only enable deficit-chasing weight updates on the remaining independent continuous dimensions
5. Use the individual-level delta_T/c ranking for conversion priority within the independent set

---

## Transferability to Other Agent Types

The formal results are structural (properties of the mechanism, not of any specific agent type):

- **Cost reduction**: The first agent type took 16 cycles of empirical discovery. Future agent types need ~4-6 cycles to calibrate biases, then apply the conversion schedule. ~$60-90/agent vs ~$240.
- **Better baselines**: Disposition generation tools can produce dispositions with correct binary/continuous structure from day one.
- **Semi-autonomous operation**: As w_v approaches 1.0, the loop needs less human review. The terminal evaluator sets quality floor and conversion thresholds.

---

## References

- Hadfield-Menell et al. (2017). Inverse Reward Design.
- Ng & Russell (2000). Algorithms for Inverse Reinforcement Learning.
- Manheim & Garrabrant (2019). Categorizing Variants of Goodhart's Law.

---

*Last Updated: 2026-03-01 | Research Prompt 0012*
