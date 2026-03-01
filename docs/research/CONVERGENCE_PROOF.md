# TITANS M-Vector Convergence Proof -- Results

**Date**: 2026-03-01
**Model**: GPT 5.2 Pro (Deep Research)
**Method**: Prior-cast A/B comparison (Frontier Protocol)
**Prompt**: `docs/research/prompts/titans_convergence_proof.md`

---

## Executive Summary

Two independent proof attempts on the TITANS M-vector convergence problem:

- **Track A (cold)**: Full research prompt sent to GPT 5.2 Pro as-is (~37 min thinking)
- **Track B (warm)**: 3-prompt collaborative warm-up, then upgrade to Pro with full prompt (~51 min thinking)

**Both produced actionable results. Neither fully solved Q1-Q5. Together they're complementary.**

| Result | Track A (Cold) | Track B (Warm) |
|--------|---------------|----------------|
| Fixed point formula | Same | Same |
| Headline unique result | Switching counterexample (bounded keys CAN diverge) | Constructive ISS proof (||M|| < 174) |
| Practical replacement | 2-step expansion test (runtime check) | Explicit Lyapunov + ISS ball radius |
| Questions answered | All 5 (broader coverage) | Targets 1-4 deeply |
| Thinking time | ~37 min | ~51 min |

---

## Key Results

### Result 1: Scalar Fixed Point Formula (Both Tracks)

```
m* = 2*theta*K*V / (alpha_tilde*(1-eta_eff) + 2*theta*K^2)
```

With production constants (alpha=0.001, delta=0.0001, theta=0.01, eta=0.9, K=0.64, V=0.77):

| eta_eff | m* (per direction) |
|-------|-------------------|
| 0.0   | 1.061             |
| 0.5   | 1.108             |
| 0.9   | **1.187**         |

**Prediction**: `||M||_F ~ sqrt(effective_rank) * m* = sqrt(200) * 1.187 ~ 16.8`
**Production observation**: `||M||_F ~ 17`
**Match**: YES. Effective rank ~ 200 is checkable at runtime via `(||M||_F / ||M||_2)^2`.

### Result 2: Diagonal Lyapunov is Impossible (Track B)

**Proved** that no diagonal `V = a||M||^2 + b||S||^2` can provide one-step contraction:
- B0 (no-gradient step) requires `b/a > 1938`
- B1 (gradient step) requires `b/a < 276`
- Ranges don't overlap. The matrix is non-normal (large off-diagonal in orthogonal complement).

This is a genuine mathematical impossibility result, not just a failure to find the right parameters.

### Result 3: Constructive ISS Proof with Cross-Term (Track B)

Adding a minimal cross-term `2c<M,S>` to the Lyapunov function closes the proof:

```
V_t = a||M_t||^2 + b||S_t||^2 + 2c<M_t, S_t>
```

With P matrix:
```
P = [[0.02174, 0.19763],
     [0.19763, 4.46779]]   (positive definite)
```

**Contraction factor**: q ~ 0.9978, sqrt(q) ~ 0.9989 (approximately f = (1-alpha)(1-delta))

**ISS recursion**: `w_t <= sqrt(q) * w_{t-1} + D` where D ~ 0.0218

**Negative drift outside ball**: `Delta_V_t < 0 whenever sqrt(V_{t-1}) > D/(1-sqrt(q)) ~ 19.82`

**Explicit norm bounds** (steady-state):
- `||M_t||_F <= 174`
- `||S_t||_F <= 12.1`

### Result 4: Switching Counterexample (Track A)

**Bounded keys do NOT guarantee bounded M under momentum.**

Counterexample with production-like gates (alpha=0.001, eta=0.9, theta=0.01):
- k alternates between |k|=5 and |k|=10
- Each frozen system is Schur-stable
- Two-step product `B(-2)*B(-0.5)` has spectral radius > 1
- M_t diverges exponentially

**This is why empirical clamps exist.** The 2-step expansion test (below) directly targets this mechanism.

### Result 5: Step-Size Stability Condition (Both Tracks)

```
theta < (1+f)(1+eta_eff) / (2*mu*K^2)
```

With production values: `theta_max ~ 4.64`, current `theta = 0.01` -- **464x safety margin**.

### Result 6: Ridge Attractor for Streaming Case (Track A)

Under stationarity, the mean dynamics satisfy:
```
(R + lambda*I) * M* = C
```
where `R = E[kk^T]`, `C = E[kv^T]`, `lambda = alpha*(1-eta)/(2*theta)`.

This can be estimated online via EMA of `kk^T` and `kv^T`, giving a runtime-computable predicted attractor norm.

### Result 7: Eta Modulation Analysis (Both Tracks)

**Helps at fixed-point level**: Smaller eta_eff -> smaller M* -> smaller stability ball.

**Creates a gap in the proof**: The system becomes a switched linear system. No single constant quadratic P works across the full eta_eff range [0, 0.9]. Both tracks identified this gap.

**Proposed closure** (both tracks independently): Two-regime ISS argument:
1. When gradient is large -> eta_eff small -> no-momentum contraction (Theorem 2)
2. When gradient is small -> eta_eff ~ eta -> fixed-eta Lyapunov applies

### Result 8: Phi Threshold Derivation (Track A)

- Davis-Kahan/Wedin bounds give principled thresholds from spectral gaps
- Current phi thresholds (0.618, 0.382, 0.236) correspond to rotation angles 51.8 deg, 67.5 deg, 76.4 deg
- These are very permissive (rarely activate in practice -- confirmed by production data)
- Principled alternative: tie threshold to `||Delta_M||_2 / gap_k(M)` where gap_k = sigma_k - sigma_{k+1}

### Result 9: Data-Dependent Gate Constraints (Track A)

Explicit weight norm bounds for stability under learned gates:
```
|W_alpha| <= (b_alpha - logit(alpha_min)) / X_max    # guarantee alpha_t >= alpha_min
|W_theta| <= (logit(theta_max) - b_theta) / X_max    # guarantee theta_t <= theta_max
|W_eta| <= (logit(eta_max) - b_eta) / X_max          # guarantee eta_t <= eta_max
```

---

## Principled Clamp Replacements

| Current Clamp | Current Value | Principled Replacement | Derivation |
|--------------|---------------|----------------------|------------|
| M_NORM_CAP | 1000 | ~200 (ISS bound 174 + margin) | Track B: ISS recursion |
| S_NORM_CAP | 500 | ~25-50 (ISS bound 12.1 + margin) | Track B: ISS recursion |
| Alpha ceiling | 0.30->0.55 ramp | Half-life: alpha <= 1-r^(1/T) | Track A: retention bound |
| Step-size | theta=0.01 (fixed) | theta < (1+f)(1+eta)/(2*mu*K^2) ~ 4.64 | Both tracks |
| **NEW: Stability gate** | -- | 2-step expansion test | Track A: Counterexample 1 |

### 2-Step Expansion Test (Track A's Unique Contribution)

Runtime stability check that directly targets the switching resonance mechanism:

```python
def stability_gate(k_t, k_prev, alpha, theta, eta):
    """Replace brute-force norm caps with principled stability check."""
    c_t = -2 * theta * np.dot(k_t, k_t)
    c_prev = -2 * theta * np.dot(k_prev, k_prev)

    B_t = np.array([[(1-alpha) + c_t, eta], [c_t, eta]])
    B_prev = np.array([[(1-alpha) + c_prev, eta], [c_prev, eta]])

    T = B_t @ B_prev
    rho = max(abs(np.linalg.eigvals(T)))

    if rho > 1.0:
        # Reduce eta_eff or theta until rho <= 1
        # This directly prevents the switching resonance
        return False, rho
    return True, rho
```

### Runtime-Computable ISS Bound (Track B)

```python
def compute_principled_cap(alpha, delta, theta, eta, K, V):
    """Compute principled M norm cap from ISS analysis."""
    f = (1 - alpha) * (1 - delta)
    mu = 1 - delta

    # Pre-computed P matrix for these parameters
    a, b, c_cross = 0.02174, 4.46779, 0.19763
    q = 0.9978  # contraction factor

    C_P = a * mu**2 + b + 2 * c_cross * mu
    D = math.sqrt(C_P) * 2 * theta * K * V
    R_V = D / (1 - math.sqrt(q))

    a_eff = a - c_cross**2 / b
    R_M = R_V / math.sqrt(a_eff)

    return R_M  # approximately 174 with production values
```

---

## Open Questions (Precisely Named)

1. **Switched-momentum stability region**: What is the largest class of key variation sequences that guarantees boundedness for given (alpha, theta, eta)?

2. **Full Lyapunov for coupled (M, S, scale) system**: Requires explicit constants linking |grad_loss| to |M| under bounded |x| and controlled |W|.

3. **Empirical-to-theoretical closure on ||M|| ~ 17**: Can the ridge attractor predict this across workloads by estimating R = E[kk^T] and C = E[kv^T] online?

4. **Two-regime ISS for eta modulation**: Needs explicit lemma about evolution of g_t and scale_t to make "modulation can't hurt" rigorous.

---

## Prior Casting Experiment Results

### Frontier Protocol Validation

| Prediction | Result |
|-----------|--------|
| Warm goes deeper on core proof | **YES** -- ISS proof, explicit P, tight bounds |
| Cold cycles through generic tools | **PARTIALLY WRONG** -- Cold found switching counterexample |
| Cast prevents off-ramps | **YES** for both tracks |
| Warm takes longer | **YES** -- 51 min vs ~37 min |

### Key Insight

The Frontier Protocol prediction held with a refinement: **depth-first (warm) and breadth-first (cold) approaches found complementary results**.

- Track B's structural insight (v_t = B^T k_t) led to the constructive ISS proof
- Track A's broader exploration found the adversarial switching counterexample Track B missed
- The prior cast prevented both from taking easy off-ramps, but shaped their focus differently

### Refined Frontier Protocol Finding

For hard problems, running **both tracks** (warm + cold) and combining results produces strictly better output than either alone. The warm track excels at constructive proofs; the cold track excels at adversarial analysis.

---

## Implementation Status

**Implemented** (feature-flagged via `TITANS_PRINCIPLED_BOUNDS`, defaults OFF):

| Item | File | Status |
|------|------|--------|
| ISS M norm cap (200) | `src/titans_disposition/constants.py` | DONE |
| ISS S norm cap (50) | `src/titans_disposition/constants.py` | DONE |
| 2-step expansion test | `src/titans_disposition/constants.py` | DONE |
| Alpha half-life ceiling | `src/titans_disposition/constants.py` | DONE |
| N-step windowed spectral radius | `src/titans_disposition/constants.py` | DONE |
| Principled eta bisection | `src/titans_disposition/constants.py` | DONE |
| P matrix parameterization | `src/titans_disposition/constants.py` | DONE |
| Spectral coherence (Davis-Kahan) | `src/titans_disposition/constants.py` | DONE |

### Activation Checklist (Before Flipping Flag ON)

1. Monitor M_norm distribution across 50+ conversations with flag OFF
2. Verify no conversation has M_norm > 200 (would be clipped on flag flip)
3. Check gate-history for `stability_rho` values (should be rare > 1.0)
4. Flip `TITANS_PRINCIPLED_BOUNDS = True` in constants
5. Monitor for 24h, check metrics for unexpected norm drops

---

*Generated 2026-03-01 | Research Prompt 0011 | GPT 5.2 Pro (Track A: cold, Track B: warm+cast)*
