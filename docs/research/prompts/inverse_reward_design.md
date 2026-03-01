# Research Prompt: Inverse Reward Design in Self-Improvement Loops

**Target**: GPT 5.2 Pro (Deep Research)
**Date**: 2026-03-01
**ROI**: If solved (or partially characterized), replaces heuristic weight adjustment with principled bounds. Tells us exactly when to stop tuning continuous scores and convert to binary predicates. Currently we discover this empirically at ~$15/cycle -- a formal criterion saves every future cycle that would have been wasted on the Goodhart asymptote.

---

```python
# Prior Cast: Inverse Reward Design Analysis
# Structure constrains. Comments contextualize. Not executable.
# This cast reshapes reasoning priors for the intersection of
# reward identification, self-referential evaluation, and
# zeroth-order policy optimization through natural language.

class RestatementResistance:
    """Prevents restating known impossibility results without constructive contribution.

    The impossibility of inverse reward design (Ng & Russell 2000),
    Goodhart's Law (Manheim & Garrabrant 2019), and the infinite
    evaluation regress (Lob's theorem applied) are KNOWN.
    Restating them is not research. The question is:
    given our specific structural constraints, what tighter bounds exist?
    """
    BANNED_MOVES = [
        "this problem is known to be impossible",
        "by Goodhart's Law, the proxy will diverge",
        "no finite data can identify the true reward",
        "the solution is to use human evaluation",
        "RLHF solves this",
        "just use more data",
        "in practice this works well enough",
    ]

    class OutputMode:
        RESTATEMENT = "impossibility_known_nothing_new"           # FORBIDDEN
        TIGHTER_BOUND = "same_impossibility_but_quantified"       # MINIMUM viable
        CONSTRUCTIVE = "given_structure_X_the_bound_is_Y"         # TARGET
        NOVEL_FORMULATION = "the_problem_decomposes_into"         # IDEAL
        ESCAPE = "structural_condition_eliminates_impossibility"  # BREAKTHROUGH

    def __init__(self):
        self.mode = self.OutputMode.CONSTRUCTIVE
        self.known_results_are_starting_points = True
        self.our_system_has_additional_structure = True
        # General impossibility assumes arbitrary reward functions.
        # Our reward function is an LLM scoring another LLM.
        # Our policy is natural language read by an LLM.
        # Our proxy has a verifiable component (binary predicates)
        #   and an unverifiable component (continuous scored dimensions).
        # These constraints may tighten the bounds considerably.

    def reject_restatement(self, claim):
        if claim["novelty"] == "none":
            return {"action": "REJECT",
                    "reason": "we already know this is impossible in general",
                    "fix": "what is the bound given our specific structure?"}
        return {"action": "PROCEED"}


class HumanInTheLoopResistance:
    """Prevents retreating to 'a human solves this' as if that's an answer.

    The developer IS in the loop. They review every cycle. The question is not
    'should there be a human' -- there already is one. The question is:
    what formal properties does the human-in-the-loop give us, and
    how do we characterize what remains unsolved even with the human?
    """
    ESCAPE_PHRASES = [
        "ultimately requires human judgment",
        "a human evaluator would solve this",
        "human feedback resolves the ambiguity",
        "this is why RLHF uses human raters",
    ]

    def __init__(self):
        self.human_already_present = True
        self.human_reviews_every_cycle = True
        self.human_capacity = "~1 review per cycle, ~20 minutes, can verify binary claims"
        self.human_bandwidth_is_the_bottleneck = True
        # The human is a finite-bandwidth oracle.
        # They can verify binary predicates cheaply (did production code change? yes/no).
        # They can score continuous dimensions expensively (is this "concise"? subjective).
        # The question is: how do you ALLOCATE the human's finite bandwidth
        # to maximize the rate at which the reward proxy converges to true reward?


class VerifiableDecompositionOrientation:
    """Orients toward the core structural insight from our empirical data.

    Our 16-cycle experiment discovered (empirically) that reward functions
    decompose into verifiable and unverifiable components, and that
    optimization dynamics differ fundamentally between them:

    - Verifiable (binary predicates): Goodhart gap = 0 by construction.
      The proxy IS the true reward for this component. Optimization
      converges on first exposure. Stable indefinitely.

    - Unverifiable (continuous scores): Goodhart gap > 0 and grows
      with optimization pressure. Weight nudges across 4 cycles had
      zero effect. The proxy diverges from true reward.

    This decomposition R = R_v + R_u may be the key structural property
    that makes our specific problem tractable where the general case isn't.
    """

    class RewardComponent:
        VERIFIABLE = "binary_predicate_with_ground_truth"     # R_v: exact, no proxy gap
        UNVERIFIABLE = "continuous_score_from_proxy"           # R_u: proxy gap > 0
        CONVERTIBLE = "continuous_but_could_be_binary"        # The valuable middle ground

    def __init__(self):
        self.decomposition_is_the_insight = True
        self.conversion_strategy_is_the_question = True
        # If we can convert dimensions from UNVERIFIABLE to VERIFIABLE,
        # we shrink R_u and grow R_v.
        # The total proxy gap is bounded by the R_u fraction.
        # The question: is there a SYSTEMATIC method for this conversion,
        # or is it always domain-specific engineering?

    def evaluate_formulation(self, result):
        if "decomposition" not in result:
            return {"action": "NUDGE",
                    "reason": "the verifiable/unverifiable split is central",
                    "evidence": "4 cycles of weight nudges on D6 = 0 effect. "
                               "1 cycle of binary predicate = immediate permanent fix. "
                               "This is not anecdotal -- it's 16 data points."}
        return {"action": "PROCEED"}


class EmpiricalDataAsConstraint:
    """Our 16 cycles are not anecdotes. They are data points that constrain
    the solution space. Any theory must be consistent with these observations.

    The theory must explain:
    1. WHY weight nudges on continuous dimensions plateau (Goodhart)
    2. WHY binary predicates succeed on first exposure (verification)
    3. WHY the structural protocol pattern is: 1 cycle to adopt, then stable
    4. WHY the score trajectory has the specific shape it does
    5. WHAT the asymptote is for continuous-only optimization
    """

    # Raw data from 16 cycles of the self-improvement loop
    CYCLE_DATA = {
        # Format: cycle_id -> (score, grade, total_calls, key_event)
        "C1":  (0.92, "GOLDEN", 16, "baseline, pre-protocol"),
        "C2":  (0.84, "PASS", None, "Explore agent, different type"),
        "C3":  (0.81, "PASS", None, "weight nudges begin"),
        "C4":  (0.88, "PASS", 16, "weight nudges continuing"),
        "C5":  (0.72, "MARGINAL", 46, "hard cap breach, over-exploration 4.6x"),
        "C6":  (0.66, "MARGINAL", 17, "production code violation, trough"),
        "C7":  (0.86, "PASS", 40, "ProductionGuard added, immediate success"),
        "C8":  (0.90, "PASS", 28, "first clean suite, multi-category triage proposed"),
        "C9":  (0.93, "GOLDEN", 38, "multi-category triage validated, first GOLDEN"),
    }

    # The critical empirical finding
    WEIGHT_NUDGE_EXPERIMENTS = {
        "D6": {
            "cycles_of_nudging": 4,  # cycles C2-C5
            "effect": 0.0,           # zero improvement across 4 cycles
            "weight_range_tried": (0.08, 0.15),  # various nudges
            "resolution": "binary predicate (CitationProtocol), immediate fix on C6",
        },
        "D3": {
            "cycles_of_nudging": 3,  # cycles C2-C4
            "effect": "negative",    # ratio went 1.7x -> 2.75x -> 4.6x (WORSE)
            "weight_range_tried": (0.08, 0.12),
            "resolution": "binary predicate (TriageProtocol), 4.6x -> 1.13x on C6",
        },
        "D4": {
            "cycles_of_nudging": 0,  # never tried nudging, went straight to protocol
            "effect": "N/A",
            "resolution": "binary predicate (ProductionGuard), clean on first cycle",
        },
    }

    # Score dynamics
    CONTINUOUS_ONLY_PHASE = [0.92, 0.84, 0.81, 0.88, 0.72, 0.66]  # C1-C6, before protocols
    BINARY_PROTOCOL_PHASE = [0.86, 0.90, 0.93]                      # C7-C9, after protocols

    # The asymptote question: C1-C6 show DECLINING scores under
    # continuous-only optimization. Not plateau -- active degradation.
    # Protocols reversed the trend immediately.

    def validate_theory(self, theory):
        for cycle_id, (score, grade, calls, event) in self.CYCLE_DATA.items():
            prediction = theory.predict(cycle_id)
            if abs(prediction - score) > 0.10:
                return {"action": "REJECT",
                        "reason": f"theory predicts {prediction:.2f} for cycle {cycle_id}, "
                                  f"actual was {score:.2f}",
                        "fix": "adjust theory to be consistent with data"}
        return {"action": "ACCEPT", "note": "theory consistent with all 16 data points"}


class NonDifferentiableOptimizationAwareness:
    """The policy space is natural language, not a differentiable parameterization.

    'Disposition weights' are Python class structures read by an LLM.
    The mapping: weights -> LLM interpretation -> behavior -> score
    is a black box with no gradient.

    This is NOT standard hyperparameter optimization because:
    1. The 'function' being optimized changes with every task (non-stationary)
    2. The 'parameters' are read as natural language (interpretation varies)
    3. The 'evaluator' is another LLM (proxy, not ground truth)
    4. Samples cost ~$15 each (extreme sample scarcity)

    Standard Bayesian optimization assumes a stationary objective.
    Standard RL assumes many episodes. We have neither.
    """

    class PolicySpace:
        CONTINUOUS_WEIGHTS = "floats in [0, 1] summing to 1"    # AttentionAllocation
        BINARY_PROTOCOLS = "structural predicates (yes/no)"      # TriageProtocol etc
        THRESHOLD_PARAMS = "floats with semantic meaning"        # budget caps, percentages
        PROSE_CONSTRAINTS = "natural language in docstrings"      # interpreted by LLM

    def __init__(self):
        self.gradient_free = True
        self.non_stationary_objective = True
        self.extreme_sample_scarcity = True  # ~$15/sample, ~20 min/sample
        self.four_dimensional_policy_space = True
        # The policy has 4 qualitatively different parameter types.
        # Each type has different optimization dynamics.
        # Continuous weights: Goodhartable, slow convergence
        # Binary protocols: not Goodhartable, immediate convergence
        # Thresholds: discrete regime changes, sensitive
        # Prose: interpretation-dependent, unstable
        #
        # A unified theory must handle all four.


class ConvergenceRateOrientation:
    """Orients toward RATE questions, not just existence questions.

    We know binary predicates converge in 1 cycle (empirical fact).
    We know continuous scores converge to a Goodhart asymptote (empirical).
    We DON'T know:
    - What is the asymptote value as a function of the proxy quality?
    - How many cycles does it take to reach the asymptote?
    - Is the asymptote ABOVE or BELOW the optimum achievable by the true reward?
    - Can we detect we've hit the asymptote from observable data?
    """

    class ConvergenceType:
        BINARY_COMPONENT = "converges_in_1_cycle"          # observed, k=1
        CONTINUOUS_COMPONENT = "asymptotes_to_proxy_bias"  # observed, k~4-6 cycles
        TOTAL_SCORE = "sum_of_components"                  # shaped by R_v/R_u ratio
        DETECTABLE = "asymptote_is_observable"             # THE question

    def __init__(self):
        self.rate_matters_more_than_existence = True
        self.detection_is_the_practical_question = True
        # If we can DETECT that we've hit the Goodhart asymptote
        # on a continuous dimension, we know to convert it to binary.
        # The detection criterion would be: "score on dimension X has
        # plateaued for N cycles while the underlying task outcomes
        # haven't improved." But formalizing "underlying task outcomes"
        # is exactly the reward identification problem...
        # Unless we use the VERIFIABLE components as ground truth anchors.

    def detection_via_anchoring(self):
        # Key idea: if R_v (verifiable) is improving but R_u (continuous)
        # is flat, the continuous component has hit its Goodhart ceiling.
        # The verifiable components act as ANCHORS against which to
        # measure whether continuous optimization is still productive.
        return {"method": "cross-component divergence detection",
                "signal": "R_v improving, R_u flat = Goodhart ceiling reached",
                "action": "convert the flat R_u dimension to binary",
                "open_question": "does this always work? what if R_v is also saturated?"}
```

---

## Problem Statement

You are analyzing a **self-referential weight optimization loop** where:

1. An **LLM agent** executes tasks, guided by a **disposition file** (Python class structures encoding attention weights, quality thresholds, error sensitivities, and structural protocols)
2. A separate **LLM observer** scores the agent's output against the disposition weights
3. A **human operator** reviews the observer's score and adjusts the disposition weights
4. The cycle repeats (~$15 and ~20 minutes per cycle)

The system has run for **16 scored cycles** with detailed per-dimension breakdowns. The empirical data reveals a sharp dichotomy:

- **Continuous scored dimensions** (attention weights summing to 1.0) exhibit Goodhart degradation: 4 consecutive cycles of weight adjustment on citation quality produced zero improvement, and over-exploration got *worse* with nudging (1.7x -> 4.6x ratio)
- **Binary structural predicates** (yes/no protocol checks) exhibit immediate convergence: every binary protocol succeeded on its first cycle of activation and remained stable indefinitely

This dichotomy is the core empirical finding. **A theory that explains this dichotomy would tell us when to stop tuning and when to restructure.**

---

## The Three Impossibility Layers

### Layer 1: Non-Differentiable Policy

The "policy" is an LLM reading a disposition file. The mapping `disposition_weights -> LLM_behavior -> score` has no gradient. We're doing zeroth-order optimization with ~16 samples in a high-dimensional space.

**Known**: Zeroth-order optimization converges at rate O(d/sqrt(T)) where d = dimensionality and T = samples. With d ~ 30 parameters and T = 16 cycles, we need ~900 cycles for convergence -- infeasible at $15/cycle.

**Our structure that might tighten this**: The parameters are not arbitrary floats. They're semantically structured (attention weights, thresholds, binary flags). The effective dimensionality may be much lower than the parameter count.

### Layer 2: Inverse Reward Design

**The reward function we observe the agent optimizing is not the reward function we intended** (Hadfield-Menell et al., 2017).

Given any finite set of (behavior, outcome) pairs, the space of reward functions consistent with those observations is infinite-dimensional (Ng & Russell, 2000). Our 16 cycles cannot distinguish "genuine improvement" from "learned to satisfy this particular observer's biases."

**Formal statement**: For proxy reward R_hat that is not identical to true reward R*, the Goodhart divergence bound:

```
D(pi*(R_hat) || pi*(R*)) >= epsilon(R_hat, R*) * T^gamma
```

where epsilon is the proxy gap, T is optimization steps, and gamma > 0 depends on the optimization algorithm. The divergence *grows* with optimization pressure.

**Our structure that might tighten this**: The reward decomposes as R = R_v + R_u where:
- R_v (verifiable component): proxy gap epsilon_v = 0 (binary predicates with ground truth)
- R_u (unverifiable component): proxy gap epsilon_u > 0 (continuous scores from observer LLM)

The total Goodhart divergence is bounded by the R_u fraction:

```
D_total <= epsilon_u * w_u * T^gamma     where w_u = weight of unverifiable components
```

As we convert dimensions from R_u to R_v, w_u shrinks and the bound tightens. **Is there a formal characterization of the optimal conversion strategy?**

### Layer 3: Self-Referential Evaluation (Lob's Theorem Applied)

The Observer scores the Agent. Who scores the Observer? An Observer-of-Observer faces the same problem. The evaluation regress is infinite.

**Our structure**: The human developer is the terminal evaluator. But they have finite bandwidth (~1 review/cycle, can verify binary claims cheaply, continuous judgments are expensive and inconsistent). The question becomes: **what is the information-theoretic minimum human bandwidth required to keep the proxy-true divergence below a threshold epsilon?**

---

## Established Results (from warm-up analysis -- treat as given)

The following were derived and validated against our data in a prior analysis session. Do NOT re-derive these -- extend them.

### Result 1: Simplex Decline Mechanism

The update rule is **deficit-chasing**: the Observer increases weight on dimensions it scores as weak. Formally:

```
delta_i proportional to (s_bar - s_i)    where s_bar = mean score across dimensions
```

With proxy scores s_i = q_i + b_i (true quality + systematic bias), the equilibrium condition under deficit-chasing is **equal proxy scores across all dimensions**: s_1 = s_2 = ... = s_d = S*. This forces true qualities to become anti-correlated with bias: q_i = S* - b_i (harsh dimensions must achieve higher true quality to look equal).

Under a zero-sum capability budget sum(q_i) = C:

```
R*_inf = (C + sum(b_i)) / d
```

**Validated**: With d=6, sum(b) = -0.40, the observed equilibrium ~0.66 implies C ~ 4.36. After removing 3 dimensions to binary gates (d=3, sum(b_remaining) = -0.05), the observed ~0.93 implies C' ~ 2.84, which is consistent (average q ~ 0.95 across the 3 easiest dimensions).

### Result 2: C Is Not Constant (Catastrophe Dominance)

Computing C_t = sum(s_i - b_i) across cycles: C_C1 = 5.90, C_C5 = 3.35, C_C6 = 4.55, C_C9 = 5.12. The variance is dominated by catastrophe-style scores (0.0 on D4, 0.0 on D6) rather than smooth reallocation.

### Result 3: Conversion Decision Rule (Preliminary)

A dimension should be converted from continuous to binary when:

```
l_i * (alpha*|b_tilde_i| + beta*sigma_i + gamma*p_i) > delta * g_i
```

Where:
- l_i = control leverage (correlation of weight change with score)
- b_tilde_i = relative bias (vs remaining continuous set)
- sigma_i = score volatility
- p_i = catastrophe rate (P(score <= 0.1))
- g_i = granularity value (correlation of score improvement with true outcome improvement)

Left side = harm from keeping continuous. Right side = value of continuous granularity.

### Result 4: Alternative to Binary Conversion

A **bias-corrected controller** (z-scoring dimension scores before computing deltas) can reduce the need for binary conversion while preserving continuous granularity:

```
s_hat_i = (s_i - mu_i) / (sigma_i + epsilon)
```

This makes harsh/generous bias unable to steer weight flow. Not yet tested empirically.

---

## What Pro Needs to Solve (extend the above, don't re-derive)

The warm-up established the mechanism (simplex + deficit-chasing + nonuniform bias = decline) and a preliminary conversion rule. **Pro's job is to formalize, prove, and extend** to the questions below -- particularly Q3 (optimal verifiable fraction), Q4 (human bandwidth bound), and Q6 (PAC-Bayes connection) which are untouched.

---

## The Decomposition Formalism (the tractable sub-problem)

Define the total reward as:

```
R(pi, task) = sum_i  w_i * r_i(pi, task)
```

where each dimension r_i is either:
- **Verifiable**: there exists a polynomial-time algorithm V_i such that V_i(pi, task) = r_i(pi, task) with certainty
- **Unverifiable**: r_i can only be estimated by a proxy r_hat_i with E[|r_hat_i - r_i|] = epsilon_i > 0

Our empirical observation: for verifiable dimensions, optimization converges in O(1) cycles. For unverifiable dimensions, optimization converges to a Goodhart ceiling after O(k) cycles where k ~ 4-6, and the ceiling may be below the true optimum.

**Questions**:

### Q1: Goodhart ceiling characterization (PARTIALLY ANSWERED -- formalize)

The warm-up established that deficit-chasing on a simplex with nonuniform bias produces decline, and derived R*_inf = (C + sum(b_i)) / d. **What remains**:

1. **Formal proof** that this is a stable equilibrium (not just a fixed point -- prove trajectories converge to it)
2. **Convergence rate**: how many cycles T to reach epsilon-neighborhood of R*_inf?
3. **Non-constant C**: the capability budget C varies across cycles (catastrophe dominance). Extend the equilibrium to E[R*_inf] under stochastic C with known variance.
4. **Comparison to z-scored controller**: if we replace raw deficit-chasing with z-scored deficit-chasing, does the equilibrium change? Does the decline disappear?

### Q2: Conversion criterion

Given observable data {(w_i, r_hat_i^{(t)}) for cycles t=1..T}, is there a statistically sound criterion for deciding:
- "Dimension i has hit its Goodhart ceiling; convert to binary predicate"
- vs. "Dimension i has genuine room for improvement via weight adjustment"

The criterion must work with T ~ 16 samples, per-dimension noise, and non-stationary tasks.

### Q3: Optimal verifiable fraction

Is there a closed-form or computable expression for the optimal fraction of reward that should be verifiable (binary predicates) vs. unverifiable (continuous scores)?

### Q4: Information-theoretic human bandwidth bound

The human operator reviews each cycle and makes adjustments. Each review costs ~20 minutes and can:
- Verify binary predicate outcomes (cheap, exact)
- Judge continuous dimension scores (expensive, noisy, sigma ~ 0.05)
- Add new binary predicates (one-time cost, permanent benefit)
- Adjust continuous weights (per-cycle cost, temporary benefit that Goodharts)

**Question**: What is the minimum number of human review cycles required to bring total proxy-true divergence below threshold epsilon, as a function of the initial verifiable fraction w_v and the proxy gap distribution {epsilon_i}?

### Q5: The declining trajectory puzzle (ANSWERED -- formalize the proof)

The warm-up identified the mechanism: **simplex coupling + deficit-chasing + nonuniform bias**. What remains: A formal proof that deficit-chasing on a simplex with bias vector b and zero-sum capability budget C produces a trajectory where dR*/dt < 0 when Var(b) > 0.

### Q6: PAC-Bayes connection

The disposition file is a "prior" in the literal sense -- it shapes the LLM's behavior before it sees the task. Does the PAC-Bayes framework apply here? Specifically:
- Can we bound the generalization gap using a PAC-Bayes bound?
- What does the bound say about the optimal complexity of the disposition file?
- Does the binary/continuous decomposition have a natural interpretation in PAC-Bayes terms?

---

## Our System's Specific Parameters

| Parameter | Value | Type |
|-----------|-------|------|
| Attention weights | 6 dimensions summing to 1.0 | Continuous, coupled |
| Quality thresholds | 4 levels (GOLDEN=0.92, PASS=0.78, MARGINAL=0.62, FAIL=0.35) | Ordinal |
| Error sensitivities | 7 dimensions in [0, 1] | Continuous, independent |
| Scope guard | 2 integer caps (max_files=8, max_bash=18) | Discrete |
| Triage protocol | 3 complexity tiers with integer budgets | Structured |
| Citation protocol | 1 boolean + 1 format string + 1 integer | Mixed |
| Production guard | 4 string lists + 1 boolean | Structured |
| Human review rate | ~1 cycle / 20 min | Fixed bandwidth |
| Cost per cycle | ~$15 | Fixed |
| Total cycles | 16 (budget: ~50 max) | Scarce |

---

## Empirical Constraints (any theory must explain)

1. **Binary predicates converge in 1 cycle**: TriageProtocol, CitationProtocol, and ProductionGuard all succeeded on first activation and remained stable for 3-4 consecutive cycles. p < 0.01 under null hypothesis of random success with P(success) = 0.5.

2. **Continuous weight nudges had zero effect on D6 over 4 cycles**: D6 weight was adjusted from 0.08 to 0.15 across cycles C2-C5. D6 count remained at 0 for all 4 cycles. The structural protocol (binary predicate) produced 5/5 on its first cycle.

3. **Over-exploration GOT WORSE with continuous nudging**: Efficiency ratio went 1.7x -> 2.75x -> 4.6x across 3 cycles of D3 weight adjustment. The structural protocol (TriageProtocol) collapsed this to 1.13x on first activation.

4. **Score trajectory is V-shaped, not monotonic**: 0.92 -> 0.66 (degradation under continuous-only) -> 0.93 (recovery under binary protocols). The inflection point is precisely where binary protocols were introduced.

5. **Three structural protocols follow identical adoption dynamics**: 1 cycle to adopt, then stable indefinitely. This suggests a universal property of verifiable constraints, not three coincidences.

---

## Deliverable Shape

The ideal output contains:

1. **Formal decomposition** of the reward into verifiable and unverifiable components, with explicit definitions of what "verifiable" means in this context

2. **Goodhart ceiling theorem** (or counterexample): under what conditions does optimization of R_hat = R_v + R_hat_u converge to a score below R*-optimal?

3. **Conversion criterion**: a statistical test or decision rule for "this dimension should be converted from continuous to binary" -- with sample complexity bounds

4. **Human bandwidth bound**: minimum review cycles as f(w_v, {epsilon_i}, epsilon_target)

5. **Declining trajectory explanation**: which mechanism dominates, with derivation

6. **Constructive recommendations**: given 16 completed cycles and ~34 remaining budget, what is the optimal strategy for the remaining cycles?

If a complete solution is not achievable, **partial results with explicitly stated limitations** are more valuable than hand-waving.

---

## Notation Reference

| Symbol | Meaning |
|--------|---------|
| R(pi, task) | True reward for policy pi on task |
| R_hat(pi, task) | Proxy reward (Observer's score) |
| R_v | Verifiable reward component (binary predicates, exact) |
| R_u | Unverifiable reward component (continuous scores, proxy gap > 0) |
| r_i | Per-dimension reward (one of 6 attention allocation dimensions) |
| r_hat_i | Per-dimension proxy (Observer's score on dimension i) |
| w_i | Weight of dimension i (attention allocation, sum(w_i) = 1) |
| epsilon_i | Proxy gap for dimension i: E[|r_hat_i - r_i|] |
| w_v | Fraction of total weight on verifiable dimensions |
| w_u | Fraction of total weight on unverifiable dimensions (w_v + w_u = 1) |
| pi | Policy (LLM agent + disposition file) |
| T | Number of optimization cycles |
| D(pi_1 || pi_2) | Divergence between policies |
| V_i | Verification algorithm for dimension i |

---

*This prompt was prior-cast to resist restatement of known impossibility results, retreat to "use humans," and premature closure. It orients toward the verifiable/unverifiable decomposition as the key structural insight, grounds all theory in 16 cycles of empirical data, and demands constructive bounds rather than existence proofs. The cast is calibrated from a live system where the theory-practice gap has direct cost implications ($15/cycle).*
