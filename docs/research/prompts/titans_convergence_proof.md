# Research Prompt: TITANS M-Vector Convergence Proof

**Target**: GPT 5.2 Pro (Deep Research)
**Date**: 2026-03-01
**Purpose**: Derive principled stability conditions and explicit safety bounds for the TITANS disposition memory update, replacing empirical clamps where possible.

---

```python
# Prior Cast: Mathematical Convergence Analysis
# Structure constrains. Comments contextualize. Not executable.
# This cast reshapes reasoning priors for hard open problems in dynamical systems.

class PrematureConcretizationResistance:
    """Prevents defaulting to known optimization results when the novel structure invalidates their assumptions."""
    BANNED_MOVES = [
        "this is just SGD with momentum",
        "by standard convex optimization results",
        "applying the Robbins-Monro conditions",
        "it is straightforward to show",
        "the proof follows directly from",
    ]

    class ProofIntegrity:
        VALID = "every_step_has_explicit_justification"      # ONLY valid mode
        HANDWAVE = "the_rest_follows_similarly"              # FORBIDDEN
        APPEAL_TO_STANDARD = "by_well_known_results"         # FORBIDDEN unless assumptions verified

    def __init__(self):
        self.mode = self.ProofIntegrity.VALID
        self.assumptions_must_be_verified = True
        self.standard_theorems_require_assumption_check = True
        self.novel_structure_acknowledged = True
        # The data-dependent gates make this NOT standard SGD.
        # The momentum term creates a coupled dynamical system.
        # Standard results require i.i.d. gradients - this has serial dependence.

    def check_theorem_applicability(self, theorem_name, system_properties):
        # Before citing any convergence theorem, verify ALL its assumptions hold.
        if not self._all_assumptions_verified(theorem_name, system_properties):
            return {
                "action": "HALT",
                "reason": f"{theorem_name} requires assumptions not met here",
                "fix": "name the failing assumption, derive the consequence of its failure",
            }
        return {"action": "PROCEED", "citation": theorem_name}

    def reject_premature_closure(self, proof_step, remaining_gaps):
        if len(remaining_gaps) > 0:
            return {
                "action": "REJECT",
                "reason": "proof incomplete",
                "gaps": remaining_gaps,
                "fix": "address each gap explicitly or state it as an open condition",
            }
        return {"action": "ACCEPT"}


class EscapeToApproximationResistance:
    """Prevents retreating to 'assume bounded' or 'assume i.i.d.' when the hard part is the unboundedness or dependence."""
    ESCAPE_PHRASES = [
        "assume the gradients are bounded",
        "under mild regularity conditions",
        "for sufficiently small learning rate",
        "in practice this is always satisfied",
    ]

    class AssumptionLevel:
        DERIVED = "follows_from_system_structure"   # ONLY valid for core claims
        IMPOSED = "we_assume_without_proof"         # Must be flagged as LIMITATION
        EMPIRICAL = "observed_in_experiments"       # Valid as motivation, not as proof step

    def __init__(self):
        self.assumption_level = self.AssumptionLevel.DERIVED
        self.imposed_assumptions_are_limitations = True
        self.every_bound_must_be_constructive = True
        # "Bounded" means nothing without the bound value.
        # "Converges" means nothing without the rate.
        # "Stable" means nothing without the basin.

    def validate_bound(self, claimed_bound, derivation):
        if not self._is_constructive(derivation):
            return {
                "action": "REJECT",
                "reason": "non-constructive bound",
                "fix": "derive the explicit bound expression from system parameters",
            }
        return {"action": "ACCEPT", "bound": claimed_bound}

    def flag_imposed_assumption(self, assumption):
        return {
            "status": "LIMITATION",
            "assumption": assumption,
            "consequence": "proof is conditional on this - state explicitly",
            "question": "can this be DERIVED from the system structure instead?",
        }


class SurfacePatternMatchingResistance:
    """Prevents recognizing 'looks like Adam optimizer' and applying Adam convergence results without checking structural differences."""

    class SystemType:
        STANDARD_SGD = "fixed_lr_iid_gradients"            # NOT this system
        ADAM_LIKE = "adaptive_lr_momentum"                 # SUPERFICIALLY similar
        DATA_DEPENDENT_GATES = "lr_is_function_of_input"   # THIS system
        COUPLED_DYNAMICAL = "state_feeds_back_into_gates"  # THIS system

    def __init__(self):
        self.system_type = self.SystemType.DATA_DEPENDENT_GATES
        self.feedback_loop_acknowledged = True
        self.standard_optimizer_analogy_is_misleading = True
        # Adam uses fixed beta values.
        # Here, alpha(x), theta(x), eta(x) can be functions of the input.
        # M also influences future prediction error and therefore future dynamics.

    def reject_false_analogy(self, claimed_analogy, structural_differences):
        if len(structural_differences) > 0:
            return {
                "action": "REJECT",
                "analogy": claimed_analogy,
                "differences": structural_differences,
                "fix": "analyze this system on its own terms, not by analogy",
            }
        return {"action": "PROCEED"}

    def identify_feedback_loops(self, system_equations):
        return {
            "loops": [
                "M -> prediction -> error -> gates -> M_update -> M",
                "M -> query_response -> resonance -> outer_product -> M_update -> M",
                "S_momentum -> M_update -> M -> prediction_error -> gradient -> S_momentum",
            ],
            "consequence": "standard fixed-point analysis requires a verified contraction argument",
        }


class ConditionDiscoveryOrientation:
    """Orients toward discovering sufficient conditions rather than proving universal convergence."""

    class OutputShape:
        THEOREM = "if_conditions_then_convergence"            # PREFERRED
        CHARACTERIZATION = "system_converges_iff_conditions"  # IDEAL
        COUNTEREXAMPLE = "system_diverges_when"               # VALUABLE
        UNIVERSAL_CLAIM = "always_converges"                  # SUSPICIOUS

    def __init__(self):
        self.target = self.OutputShape.CHARACTERIZATION
        self.counterexamples_are_valuable = True
        self.conditions_must_be_checkable = True
        self.numeric_constants_welcome = True
        # We do not need "this always works."
        # We need "this works when X, Y, Z, and here is how to check X, Y, Z at runtime."

    def shape_output(self, result):
        if result["type"] == self.OutputShape.UNIVERSAL_CLAIM:
            return {
                "action": "CHALLENGE",
                "reason": "universal convergence claims require extraordinary proof",
                "fix": "state the conditions explicitly and prove they hold",
            }
        return {"action": "ACCEPT", "value": "high"}

    def evaluate_conditions(self, conditions):
        for c in conditions:
            if not self._is_runtime_checkable(c):
                return {
                    "action": "FLAG",
                    "condition": c,
                    "reason": "condition not checkable at runtime",
                    "fix": "reformulate in terms of observable quantities",
                }
        return {"action": "ACCEPT", "conditions": conditions}
```

---

## Problem Statement

Analyze a test-time learning system where a memory matrix `M` is updated continuously during inference. The system processes a stream of 1024-dimensional embeddings from a BGE-large encoder. The core question:

**Under what conditions does `M` converge to a stable attractor, and what are the properties of that attractor?**

This is not a standard optimization problem. The objective is implicit, the gate values can be data-dependent, and the state feeds back into its own update rule. We need either:

1. Novel sufficient conditions for stability,
2. A characterization of the stability boundary, or
3. A proof that the empirical clamps currently used are necessary or can be replaced with principled bounds.

---

## System Specification (V2 Path, Paper-Aligned)

Reference: Behrouz et al. 2501.00663v1 ("TITANS: Learning to Memorize at Test Time")

### State Variables

| Variable | Shape | Description |
|----------|-------|-------------|
| `M` | `[1024, d_mem]` | Memory matrix (`d_mem = 2048` for MAC, `1024` for MAG/MAL) |
| `S` | `[1024, d_mem]` | Accumulated surprise momentum buffer |
| `W_K` | `[1024, 1024]` | Key projection |
| `W_V` | `[1024, d_mem]` | Value projection |
| `W_Q` | `[1024, 1024]` | Query projection |
| `W_alpha` | `[1024]` | Forget gate projection weights |
| `b_alpha` | scalar | Forget gate bias |
| `W_theta` | `[1024]` | Learn gate projection weights |
| `b_theta` | scalar | Learn gate bias |
| `W_eta` | `[1024]` | Momentum gate projection weights |
| `b_eta` | scalar | Momentum gate bias |

### Initialization

```text
M_0 ~ N(0, 0.01^2)  element-wise
S_0 = 0
W_K, W_V, W_Q ~ N(0, 0.01^2)
W_alpha = W_theta = W_eta = 0  (warm start)
b_alpha = logit(0.001) ~= -6.907
b_theta = logit(0.01)  ~= -4.595
b_eta   = logit(0.9)   ~= 2.197
```

With the warm start, the initial gates reproduce the empirical base values exactly.

### Per-Step Update

Given input embedding `x_t in R^1024` at step `t`:

**Step 1: Compute keys and values**

```text
k_t = x_t @ W_K
v_t = x_t @ W_V
```

**Step 2: Associative memory loss**

```text
l(M; x_t) = ||M^T k_t - v_t||^2
```

**Step 3: Gradient of loss with respect to M**

```text
grad_M l = 2 * outer(k_t, M^T k_t - v_t)
```

**Step 4: Data-dependent gates**

```text
alpha_t = sigma(x_t . W_alpha + b_alpha)
theta_t = sigma(x_t . W_theta + b_theta)
eta_t   = sigma(x_t . W_eta + b_eta)
```

In the current implementation, the gate projection vectors remain at warm-start values, so the gates are effectively constant:

```text
alpha ~= 0.001
theta ~= 0.01
eta   ~= 0.9
```

The analysis should cover both:

1. The current fixed-gate regime, and
2. The general regime where the gate projections become nonzero.

**Step 5: Surprise-modulated momentum**

```text
eta_effective = eta_t * (1 - min(surprise_t, 1.0))

where surprise_t = 1 - exp(-||grad_M l|| / scale_t)
and   scale_t = running_mean(||grad_M l||) over the last 100 steps, clamped >= 0.1
```

**Step 6: Momentum update**

```text
S_t = eta_effective * S_{t-1} - theta_t * grad_M l
```

**Step 7: Memory update**

```text
M_t = (1 - alpha_t) * M_{t-1} + S_t
```

**Step 8: Per-cycle decay**

```text
M_t = M_t * (1 - 0.001 * 0.1 * forget_multiplier)
```

---

## Empirical Safety Clamps

These are the current guardrails that prevent numeric divergence in the implementation. The goal is to replace or justify them from first principles.

| Clamp | Value | Purpose |
|-------|-------|---------|
| Alpha ceiling | maturity-gated legacy ramp or retention-derived ceiling | Prevent catastrophic forgetting |
| `M` norm cap | `1000.0` legacy, lower under principled bounds | Prevent matrix explosion |
| `S` norm cap | `500.0` legacy, lower under principled bounds | Prevent momentum explosion |
| NaN/Inf sanitization | `nan -> 0`, `inf -> 1` | Catch numeric instability |
| Surprise scale floor | `0.1` | Prevent division by near-zero |

---

## Identity Guardian

Learning can also be modulated by coherence between the current memory state and an identity anchor:

```text
identity_anchor in R^n
coherence = cosine_similarity(identity_vector(M + proposed_update), identity_anchor)

if coherence >= 0.618:  scale = 1.0
if coherence >= 0.382:  scale = coherence
if coherence >= 0.236:  scale = coherence * 0.5
if coherence < 0.236:   scale = coherence * 0.1

theta_effective = theta * scale
```

The current thresholds are inverse powers of the golden ratio and should not be assumed optimal.

---

## Coupled Feedback Structure

The system has three interacting loops:

```text
Loop 1 (Prediction-Error-Memory):
    M_t -> M_t^T k_t -> prediction -> error -> gradient -> S_t -> M_{t+1}

Loop 2 (Surprise-Momentum):
    gradient_norm -> surprise -> eta_modulation -> S weighting -> M update

Loop 3 (Identity-Learning):
    M_t -> SVD -> identity_vector -> coherence -> theta_scaling -> M update magnitude
```

These loops introduce nonlinear coupling, state-dependent damping, and scale-dependent dynamics.

---

## What We Know Empirically

Observed in the current TITANS disposition implementation and extended testing:

- `||M||_F` typically stabilizes around the high teens under default gates.
- The legacy `1000.0` matrix cap is highly conservative and is rarely approached.
- With warm-start gates, `alpha`, `theta`, and `eta` are effectively constant.
- The coherence mechanism usually stays in the high-coherence regime.
- Surprise-modulated `eta` appears to improve responsiveness but complicates proofs because the system becomes switched or state-dependent.

These observations are motivation only. They are not proof steps.

---

## Specific Questions

### Q1: Fixed-gate equilibrium

When `alpha`, `theta`, and `eta` are constant:

```text
S_t = eta * S_{t-1} - theta * grad_M l(M_{t-1}; x_t)
M_t = (1 - alpha) * M_{t-1} + S_t
```

Question:

- Under what conditions on `(alpha, theta, eta, ||x_t||, sigma_min(W_K), sigma_max(W_K))` does `||M_t||` remain bounded for all `t`?
- What explicit bound follows from those conditions?
- Can the observed equilibrium norm be derived from the system parameters?

### Q2: Surprise-modulated `eta`

Question:

- Does state-dependent damping help or hurt stability?
- Can the system oscillate between high-surprise and low-surprise regimes?
- Is there a Lyapunov function for the coupled `(M, S, scale)` system?

### Q3: Identity guardian necessity

Question:

- Is coherence-gated learning necessary for stability, or merely helpful?
- If norm caps remain but the identity guardian is removed, does `M` still converge?
- If the identity guardian remains but norm caps are removed, does `M` still converge?

### Q4: Golden-ratio thresholds

Question:

- Is there a principled derivation of the coherence thresholds from spectral geometry, perturbation theory, or attractor structure?

### Q5: Truly data-dependent gates

If `W_alpha`, `W_theta`, or `W_eta` become nonzero:

```text
alpha_t = sigma(x_t . W_alpha + b_alpha)
theta_t = sigma(x_t . W_theta + b_theta)
eta_t   = sigma(x_t . W_eta + b_eta)
```

Question:

- What constraints on these weight vectors guarantee convergence?
- Is there a maximum `||W_alpha||`, `||W_theta||`, or `||W_eta||` beyond which the system becomes unstable?
- How do those constraints depend on the input distribution?

---

## Deliverable Shape

The ideal output is a structured mathematical document containing:

1. Theorem statements with explicit conditions.
2. Proofs or proof sketches with every nontrivial step justified.
3. Counterexamples showing what happens when the conditions fail.
4. Derived bounds that can replace empirical clamps.
5. Open questions clearly separated from resolved claims.
6. Concrete implementation recommendations.

If a complete proof is not achievable, a partial characterization with clearly stated limitations is preferred over a hand-wavy proof.

---

## Notation Reference

| Symbol | Meaning |
|--------|---------|
| `M_t` | Memory matrix at step `t` |
| `S_t` | Momentum buffer at step `t` |
| `x_t` | Input embedding |
| `k_t` | Key projection `x_t @ W_K` |
| `v_t` | Value projection `x_t @ W_V` |
| `alpha_t` | Forget gate |
| `theta_t` | Learn gate |
| `eta_t` | Momentum gate |
| `sigma(.)` | Logistic sigmoid |
| `l(M; x)` | Associative memory loss |
| `phi` | Golden ratio |

---

This prompt is intentionally shaped to resist premature concretization, false analogy, and non-constructive approximation. The goal is a mathematically defensible characterization of TITANS disposition memory stability, not a generic optimizer proof.
