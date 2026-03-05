"""
COGNITIVE SUBSTRATE CONSTANTS
=============================

Learning gate constants validated through falsification testing.

HISTORY:
- Original design used golden ratio (phi) derived constants
- Falsification Test 2 (Phi vs Grid Shootout) proved phi-constants underperform
- Standard ML hyperparameters won 4/4 metrics:
  - 67% less drift
  - 40% higher coherence
  - Equal recall
  - Equal convergence speed

The golden ratio remains in this file for:
- Historical reference
- Research mode (opt-in via environment variable)
- Identity coherence thresholds (not yet falsified)
"""

import math
import os
from typing import Any, Dict

import numpy as np

# =============================================================================
# GOLDEN RATIO CONSTANTS (Preserved for Reference)
# =============================================================================

PHI: float = (1 + math.sqrt(5)) / 2  # 1.6180339887...
PHI_INV: float = 1 / PHI             # 0.6180339887... = 1/phi = phi - 1
PHI_INV_2: float = PHI_INV ** 2      # 0.3819660113... = 1/phi^2
PHI_INV_3: float = PHI_INV ** 3      # 0.2360679775... = 1/phi^3

# Verify golden ratio identity: phi^2 = phi + 1
assert abs(PHI ** 2 - (PHI + 1)) < 1e-10, "Golden ratio identity violated"

# =============================================================================
# FIBONACCI SEQUENCE (Temporal Windows - Not Yet Falsified)
# =============================================================================

FIB: list[int] = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]


def fib(n: int) -> int:
    """Get nth Fibonacci number (0-indexed)."""
    if n < len(FIB):
        return FIB[n]
    # Extend if needed
    a, b = FIB[-2], FIB[-1]
    for _ in range(n - len(FIB) + 1):
        a, b = b, a + b
    return b


# =============================================================================
# LEARNING GATE CONSTANTS - EMPIRICALLY VALIDATED
# =============================================================================
# These values won the Phi vs Grid Shootout (Test 2):
# - Standard ML: drift=0.30, coherence=0.06
# - phi-derived:   drift=0.92, coherence=0.04  (FALSIFIED)
# =============================================================================

# Production defaults (empirically validated)
THETA_BASE: float = 0.01   # Learning rate - Standard ML
ALPHA_BASE: float = 0.001  # Weight decay (forgetting) - Standard ML
ETA_BASE: float = 0.9      # Momentum coefficient (Adam beta1) - Standard ML

# =============================================================================
# DEPRECATED: phi-DERIVED CONSTANTS (Research Only)
# =============================================================================
# WARNING: These values produce 67% more drift and 40% less coherence.
# Preserved for research and historical reference only.
# =============================================================================

_THETA_PHI: float = 0.1                    # Original phi-based learning rate
_ALPHA_PHI: float = _THETA_PHI / PHI       # ~0.0618 - FALSIFIED
_ETA_PHI: float = _THETA_PHI * PHI_INV     # ~0.0618 - FALSIFIED


def get_learning_constants() -> Dict[str, Any]:
    """
    Returns learning constants. Override via environment variables.

    Environment:
        TITANS_ALPHA: Weight decay rate (default: 0.001)
        TITANS_THETA: Learning rate (default: 0.01)
        TITANS_ETA: Momentum coefficient (default: 0.9)
        TITANS_USE_PHI: Set to "true" to use deprecated phi-constants (research only)

    Returns:
        Dict with alpha, theta, eta values.
    """
    # Check for research mode (deprecated phi-constants)
    if os.getenv("TITANS_USE_PHI", "false").lower() == "true":
        return {
            "alpha": _ALPHA_PHI,
            "theta": _THETA_PHI,
            "eta": _ETA_PHI,
        }

    # Production: use empirical values with optional overrides
    return {
        "alpha": float(os.getenv("TITANS_ALPHA", str(ALPHA_BASE))),
        "theta": float(os.getenv("TITANS_THETA", str(THETA_BASE))),
        "eta": float(os.getenv("TITANS_ETA", str(ETA_BASE))),
    }


# =============================================================================
# IDENTITY COHERENCE THRESHOLDS (phi-derived, Not Yet Falsified)
# =============================================================================
# These still use phi because they weren't part of Test 2.
# Convergence proof phi analysis confirms these thresholds are very permissive
# (rarely activate in production). Rotation angles 51.8 deg / 67.5 deg / 76.4 deg.
# Principled alternative: spectral gap-derived thresholds (Davis-Kahan bounds).
# =============================================================================

COHERENCE_OPTIMAL: float = PHI_INV      # 0.618 - Full learning allowed
COHERENCE_DAMPEN: float = PHI_INV_2     # 0.382 - Dampened learning
COHERENCE_ALERT: float = PHI_INV_3      # 0.236 - Alert + heavy dampen (also crisis floor)

# =============================================================================
# SPECTRAL COHERENCE THRESHOLDS (Davis-Kahan Derived)
# =============================================================================
# Angular perturbation of top-k singular subspace, mapped to 0-1 coherence.
# More conservative than phi thresholds for OPTIMAL (0.966 > 0.618).
# Active only when TITANS_PRINCIPLED_BOUNDS is True.
# =============================================================================

SPECTRAL_COHERENCE_OPTIMAL: float = math.cos(math.radians(15))  # ~0.966
SPECTRAL_COHERENCE_DAMPEN: float = math.cos(math.radians(45))   # ~0.707
SPECTRAL_COHERENCE_ALERT: float = math.cos(math.radians(75))    # ~0.259

_SPECTRAL_MIN_NORM: float = 1e-8  # Below this, M is too small for meaningful SVD


def compute_spectral_coherence(
    M: np.ndarray,
    M_anchor: np.ndarray,
    top_k: int = 10,
) -> float:
    """
    Compute identity coherence via Davis-Kahan spectral gap bound.

    Measures the angular perturbation of the top-k singular subspace
    between M and M_anchor. Returns a 0-1 coherence score where
    1 = identical subspaces, 0 = orthogonal subspaces.

    The Davis-Kahan sin-theta theorem bounds the canonical angle between
    invariant subspaces by ||Delta||_2 / gap_k, where gap_k = sigma_k - sigma_{k+1}.
    We convert this to a coherence score via cos(arcsin(min(bound, 1))).

    Args:
        M: Current weight matrix (any shape, SVD computed on it).
        M_anchor: Identity anchor weight matrix (same shape as M).
        top_k: Number of dominant singular directions to compare.

    Returns:
        Coherence score in [0, 1]. Falls back to cosine coherence if
        SVD is degenerate (gap_k near zero) or M is near-zero.
    """
    # Edge case: near-zero matrices
    m_norm = np.linalg.norm(M)
    anchor_norm = np.linalg.norm(M_anchor)
    if m_norm < _SPECTRAL_MIN_NORM or anchor_norm < _SPECTRAL_MIN_NORM:
        return 1.0  # Neutral — no drift detectable

    # Clamp top_k to matrix dimensions
    max_k = min(M.shape) if M.ndim >= 2 else 1
    if M.ndim < 2 or max_k < 2:
        # 1D or single-row/col: fall back to cosine similarity
        flat_m = M.flatten()
        flat_a = M_anchor.flatten()
        cos_sim = float(np.dot(flat_m, flat_a) / (m_norm * anchor_norm))
        return max(0.0, cos_sim)

    k = min(top_k, max_k - 1)  # Need at least k+1 singular values for gap
    if k < 1:
        k = 1

    try:
        # Compute SVDs (truncated to k+1 for gap computation)
        U_m, S_m, _ = np.linalg.svd(M, full_matrices=False)
        U_a, S_a, _ = np.linalg.svd(M_anchor, full_matrices=False)

        # Spectral gap: sigma_k - sigma_{k+1} of the anchor
        if k < len(S_a):
            gap_k = float(S_a[k - 1] - S_a[k]) if k < len(S_a) else 0.0
        else:
            gap_k = 0.0

        # If gap is degenerate, fall back to cosine on flattened identity vectors
        if gap_k < _SPECTRAL_MIN_NORM:
            flat_m = (U_m[:, :k] * S_m[:k]).flatten()
            flat_a = (U_a[:, :k] * S_a[:k]).flatten()
            n_m = np.linalg.norm(flat_m)
            n_a = np.linalg.norm(flat_a)
            if n_m < _SPECTRAL_MIN_NORM or n_a < _SPECTRAL_MIN_NORM:
                return 1.0
            return max(0.0, float(np.dot(flat_m, flat_a) / (n_m * n_a)))

        # Perturbation norm
        delta_norm = float(np.linalg.norm(M - M_anchor, ord=2))

        # Davis-Kahan: sin(angle) <= ||Delta||_2 / gap_k
        sin_bound = min(delta_norm / gap_k, 1.0)

        # Convert to coherence: cos(arcsin(sin_bound))
        coherence = math.sqrt(1.0 - sin_bound ** 2)

        return float(coherence)

    except (np.linalg.LinAlgError, ValueError):
        # SVD failed — return neutral (safe)
        return 1.0


# =============================================================================
# SURPRISE THRESHOLDS (Persona-Scaled, Not Yet Falsified)
# =============================================================================

SURPRISE_BASE: float = 0.08  # Base surprise threshold

SURPRISE_THRESHOLD: dict[str, float] = {
    "ARCHITECT": SURPRISE_BASE,                    # 0.08 - Low, capture more when stuck
    "OBSERVER": SURPRISE_BASE * PHI,               # ~0.129 - Neutral
    "SCRIBE": SURPRISE_BASE * PHI * PHI,           # ~0.209 - Decelerating
    "VISIONARY": SURPRISE_BASE * PHI * PHI * PHI,  # ~0.338 - High, preserve flow
}

# =============================================================================
# TEMPORAL WINDOWS (Fibonacci-Governed, Not Yet Falsified)
# =============================================================================

CAPTURE_INTERVAL_MS: dict[str, int] = {
    "ARCHITECT": FIB[3] * 1000,   # 2000ms
    "OBSERVER": FIB[5] * 1000,    # 5000ms
    "SCRIBE": FIB[5] * 1000,      # 5000ms
    "VISIONARY": FIB[7] * 1000,   # 13000ms
}

# Update cycle constants
MOMENTUM_WINDOW: int = FIB[4]        # 3 updates
DECAY_WINDOW: int = FIB[6]           # 8 updates
IDENTITY_DRIFT_WINDOW: int = FIB[8]  # 21 updates
VELOCITY_HISTORY: int = FIB[6]       # 8 samples

# Context construction
RECENT_TURNS_TO_CLAUDE: int = FIB[5]  # 5 turns

# Activity buffer (for velocity computation)
ACTIVITY_BUFFER_SIZE: int = FIB[10]  # 55 events

# =============================================================================
# VARIANT DIMENSIONS
# =============================================================================

EMBEDDING_DIM: int = 1024  # BGE-large standard

MAC_MEMORY_DIM: int = 2048  # Long-range context (largest)
MAG_MEMORY_DIM: int = 1024  # Selective attention
MAL_MEMORY_DIM: int = 1024  # Deep integration

# =============================================================================
# THERMODYNAMIC CONSTANTS (Framework Validated by Test 1)
# =============================================================================

THERMO_MIN_EVENTS: int = 10
THERMO_TEMP_BINS: int = FIB[6]  # 8 bins
THERMO_CORRELATION_THRESHOLD: float = 0.3  # |r| > 0.3 is significant

# =============================================================================
# PRINCIPLED BOUNDS (ISS-Derived, Convergence Proof)
# =============================================================================
# Feature flag: defaults ON. Flip OFF to use legacy clamps.
# =============================================================================

TITANS_PRINCIPLED_BOUNDS: bool = True

# ISS-derived norm caps (from Track B constructive proof)
ISS_M_NORM_CAP: float = 200.0   # ISS bound ~174, +15% margin
ISS_S_NORM_CAP: float = 50.0    # ISS bound ~12.1, generous margin

# Alpha half-life retention target
ALPHA_HALFLIFE_RETENTION: float = 0.95


# ---------------------------------------------------------------------------
# ISS P matrix lookup grid — parameterized by (alpha, eta)
# ---------------------------------------------------------------------------
# The Lyapunov function V = a||M||^2 + b||S||^2 + 2c<M,S> requires a P matrix
# [[a, c], [c, b]] that is positive definite. The contraction factor q tracks
# the compound retention f = (1-alpha)(1-delta).
#
# P entries scale from the production reference (Result 3):
#   - q = f^2 where f = (1-alpha)(1-delta)
#   - a scales with alpha (more forgetting -> tighter M dissipation)
#   - b scales with (1+eta) (more momentum -> larger S coefficient)
#   - c_cross maintains a constant fraction of sqrt(a*b) for PD margin
#
# Grid: alpha in {0.0005, 0.001, 0.005, 0.01}, eta in {0.5, 0.7, 0.9, 0.95}.
# All entries verified positive definite at import time.
# ---------------------------------------------------------------------------

# Production P (proven PD, the reference point)
_P_PRODUCTION = {
    "a": 0.02174,
    "b": 4.46779,
    "c_cross": 0.19763,
    "q": 0.9978,
}

_GRID_ALPHAS = (0.0005, 0.001, 0.005, 0.01)
_GRID_ETAS = (0.5, 0.7, 0.9, 0.95)


def _compute_p_entry(alpha: float, eta: float, delta: float = 0.0001) -> dict:
    """
    Derive P matrix entries for given (alpha, eta, delta).

    Scales from the production reference using relationships from the
    convergence proof. Returns dict with a, b, c_cross, q.
    """
    alpha_ref = ALPHA_BASE  # 0.001
    eta_ref = ETA_BASE      # 0.9

    f = (1 - alpha) * (1 - delta)
    q = f * f

    # Scale a: proportional to alpha. Bounded below at 50% of production.
    a_scale = max(alpha / alpha_ref, 0.5)
    a = _P_PRODUCTION["a"] * a_scale

    # Scale b: proportional to (1+eta)/(1+eta_ref).
    b_scale = (1 + eta) / (1 + eta_ref)
    b = _P_PRODUCTION["b"] * b_scale

    # Scale c_cross: maintain same fraction of sqrt(a*b) as production.
    c_frac = _P_PRODUCTION["c_cross"] / math.sqrt(
        _P_PRODUCTION["a"] * _P_PRODUCTION["b"]
    )
    c_cross = c_frac * math.sqrt(a * b)

    return {"a": a, "b": b, "c_cross": c_cross, "q": q}


def _is_positive_definite(entry: dict) -> bool:
    """Check P = [[a, c], [c, b]] is positive definite: a > 0, det > 0."""
    a, b, c = entry["a"], entry["b"], entry["c_cross"]
    return a > 0 and b > 0 and (a * b - c * c) > 0


def _build_p_grid() -> dict:
    """Pre-compute P matrix entries for the (alpha, eta) grid."""
    grid = {}
    for alpha in _GRID_ALPHAS:
        for eta in _GRID_ETAS:
            entry = _compute_p_entry(alpha, eta)
            if _is_positive_definite(entry):
                grid[(alpha, eta)] = entry
    return grid


# Computed once at import time (pure math, no I/O)
_P_GRID = _build_p_grid()


def _lookup_p(alpha: float, eta: float) -> dict:
    """
    Nearest-neighbor lookup into the P grid.

    Fast path: production defaults return proven production P directly.
    Otherwise finds nearest grid point in (log(alpha), eta) space.
    Falls back to production P if grid is empty.
    """
    if alpha == ALPHA_BASE and eta == ETA_BASE:
        return _P_PRODUCTION

    if not _P_GRID:
        return _P_PRODUCTION

    log_alpha = math.log(max(alpha, 1e-10))
    best_key = None
    best_dist = float("inf")
    for (ga, ge) in _P_GRID:
        log_ga = math.log(ga)
        dist = (log_alpha - log_ga) ** 2 + (eta - ge) ** 2
        if dist < best_dist:
            best_dist = dist
            best_key = (ga, ge)

    if best_key is not None:
        return _P_GRID[best_key]

    return _P_PRODUCTION


def compute_iss_norm_bound(
    alpha: float = ALPHA_BASE,
    delta: float = 0.0001,
    theta: float = THETA_BASE,
    eta: float = ETA_BASE,
    K: float = 0.64,
    V: float = 0.77,
) -> float:
    """
    Compute principled M norm cap from ISS Lyapunov analysis.

    Uses the cross-term Lyapunov V = a||M||^2 + b||S||^2 + 2c<M,S>
    with P matrix values parameterized by (alpha, eta) via a pre-computed
    grid with nearest-neighbor lookup. Falls back to production P values
    (proven positive definite) when inputs match production defaults.

    Returns R_M ~ 174 with production values.
    """
    mu = 1 - delta

    p = _lookup_p(alpha, eta)
    a = p["a"]
    b = p["b"]
    c_cross = p["c_cross"]
    q = p["q"]

    C_P = a * mu**2 + b + 2 * c_cross * mu
    D = math.sqrt(C_P) * 2 * theta * K * V
    R_V = D / (1 - math.sqrt(q))

    a_eff = a - c_cross**2 / b
    R_M = R_V / math.sqrt(a_eff)

    return R_M


def stability_gate_2step(
    k_current: np.ndarray,
    k_prev: np.ndarray,
    alpha: float,
    theta: float,
    eta: float,
) -> tuple[bool, float]:
    """
    Runtime switching stability check (2-step expansion test).

    Builds companion matrices for consecutive key vectors and checks
    whether the two-step product has spectral radius <= 1.

    Targets the switching resonance mechanism: bounded keys CAN produce
    divergent M under momentum when the two-step spectral radius exceeds 1.

    Returns (is_stable, spectral_radius).
    """
    c_t = -2 * theta * float(np.dot(k_current, k_current))
    c_prev = -2 * theta * float(np.dot(k_prev, k_prev))

    f = 1 - alpha  # forgetting retention factor

    B_t = np.array([[f + c_t, eta], [c_t, eta]])
    B_prev = np.array([[f + c_prev, eta], [c_prev, eta]])

    T = B_t @ B_prev
    eigenvalues = np.linalg.eigvals(T)
    rho = float(max(abs(eigenvalues)))

    return (rho <= 1.0, rho)


def stability_gate_nstep(
    k_history: list[np.ndarray],
    alpha: float,
    theta: float,
    eta: float,
    window: int = 4,
) -> tuple[bool, float]:
    """
    Windowed N-step switching stability check.

    Builds the companion matrix B(c_i) for each key in the history window
    and computes the product B_N @ ... @ B_1. Returns (is_stable, rho)
    where rho is the N-th root of the product's spectral radius (so it's
    comparable to the 2-step version).

    Falls back to stability_gate_2step if fewer than 2 keys in history.
    """
    if len(k_history) < 2:
        return (True, 0.0)

    if len(k_history) == 2:
        return stability_gate_2step(
            k_history[-1], k_history[-2], alpha, theta, eta,
        )

    # Use at most `window` recent keys
    keys = list(k_history)[-window:]
    n = len(keys)

    f = 1 - alpha  # forgetting retention factor

    # Build product of companion matrices: B_n @ ... @ B_1
    product = np.eye(2)
    for k in keys:
        c = -2 * theta * float(np.dot(k, k))
        B = np.array([[f + c, eta], [c, eta]])
        product = B @ product

    eigenvalues = np.linalg.eigvals(product)
    rho_product = float(max(abs(eigenvalues)))

    # Take the N-th root so rho is per-step (comparable to 2-step version)
    rho = rho_product ** (1.0 / n)

    return (rho <= 1.0, rho)


def find_stable_eta(
    k_current: np.ndarray,
    k_prev: np.ndarray,
    alpha: float,
    theta: float,
    eta_max: float,
    tol: float = 0.001,
    max_iter: int = 10,
) -> float:
    """
    Binary search for the largest stable eta in [0, eta_max].

    For each candidate eta, computes rho via stability_gate_2step and
    returns the largest eta where rho <= 1.0.

    Runtime: ~10 iterations * 2x2 eigval = <10 microseconds.
    """
    # Check if already stable at eta_max
    is_stable, _ = stability_gate_2step(k_current, k_prev, alpha, theta, eta_max)
    if is_stable:
        return eta_max

    # Check degenerate case: unstable even at eta=0
    is_stable_zero, _ = stability_gate_2step(k_current, k_prev, alpha, theta, 0.0)
    if not is_stable_zero:
        return 0.0

    # Bisect on [0, eta_max]
    lo, hi = 0.0, eta_max
    for _ in range(max_iter):
        mid = (lo + hi) / 2.0
        is_stable_mid, _ = stability_gate_2step(k_current, k_prev, alpha, theta, mid)
        if is_stable_mid:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break

    return lo


def compute_alpha_ceiling(
    retention: float = ALPHA_HALFLIFE_RETENTION,
    horizon: int = 10,
) -> float:
    """
    Retention-derived alpha ceiling.

    Given a target retention fraction r over T steps,
    returns alpha_max = 1 - r^(1/T).

    Replaces the empirical linear ramp (ALPHA_FLOOR to ALPHA_CEIL).
    """
    return 1 - retention ** (1.0 / horizon)


# Conservative caps used when the Lyapunov sufficient condition fails.
LYAPUNOV_FALLBACK_M_CAP: float = 200.0
LYAPUNOV_FALLBACK_S_CAP: float = 50.0

# Safety margin applied to derived norm caps.
ISS_SAFETY_MARGIN: float = 1.15


def compute_lyapunov_intermediates(
    alpha: float = ALPHA_BASE,
    delta: float = 0.0001,
) -> dict[str, float]:
    """Compute shared intermediate values for Lyapunov analysis."""
    f = (1 - alpha) * (1 - delta)
    mu = 1 - delta
    one_minus_f = 1 - f
    return {"f": f, "mu": mu, "one_minus_f": one_minus_f}


def verify_lyapunov_condition(
    alpha: float = ALPHA_BASE,
    delta: float = 0.0001,
    theta: float = THETA_BASE,
    eta: float = ETA_BASE,
    K: float = 0.64,
) -> tuple[bool, float, float]:
    """
    Check the Lyapunov sufficient condition for ISS bounds validity.

    The ISS proof requires:
        theta * K^2 <= (f - eta)^2 / (mu * (f + eta))

    Returns (condition_holds, theta_max, K_crit).
    If condition_holds is False, ISS-derived bounds should not be used.
    """
    vals = compute_lyapunov_intermediates(alpha, delta)
    f, mu = vals["f"], vals["mu"]

    if eta >= f:
        return (False, 0.0, 0.0)

    f_minus_eta = f - eta
    f_plus_eta = f + eta
    rhs = f_minus_eta ** 2 / (mu * f_plus_eta)

    if K <= 1e-15:
        theta_max = float("inf")
    else:
        theta_max = rhs / (K ** 2)

    if theta <= 1e-15:
        K_crit = float("inf")
    else:
        K_crit = math.sqrt(rhs / theta)

    condition_holds = theta <= theta_max
    return (condition_holds, theta_max, K_crit)


def compute_iss_m_norm_bound(
    alpha: float = ALPHA_BASE,
    delta: float = 0.0001,
    theta: float = THETA_BASE,
    eta: float = ETA_BASE,
    K: float = 0.64,
    V: float = 0.77,
) -> float:
    """
    Compute the principled M norm cap from Theorem 1.

    R_M = 2 * theta * K * V * mu * (f + eta) / ((1 - f) * (f - eta))

    Valid when eta < f and the Lyapunov sufficient condition holds.
    """
    vals = compute_lyapunov_intermediates(alpha, delta)
    f, mu, one_minus_f = vals["f"], vals["mu"], vals["one_minus_f"]

    if eta >= f or one_minus_f < 1e-15:
        return LYAPUNOV_FALLBACK_M_CAP

    f_minus_eta = f - eta
    if f_minus_eta < 1e-15:
        return LYAPUNOV_FALLBACK_M_CAP

    R_M = (2.0 * theta * K * V * mu * (f + eta)) / (one_minus_f * f_minus_eta)
    return R_M


def compute_iss_s_norm_bound(
    alpha: float = ALPHA_BASE,
    delta: float = 0.0001,
    theta: float = THETA_BASE,
    eta: float = ETA_BASE,
    K: float = 0.64,
    V: float = 0.77,
) -> float:
    """
    Compute the principled S (momentum) norm cap from Theorem 1.

    R_S = 2 * theta * K * V / (1 - f) * sqrt((f + eta) / eta)
    """
    vals = compute_lyapunov_intermediates(alpha, delta)
    f, one_minus_f = vals["f"], vals["one_minus_f"]

    if eta < 1e-15 or one_minus_f < 1e-15:
        return LYAPUNOV_FALLBACK_S_CAP

    R_S = (2.0 * theta * K * V / one_minus_f) * math.sqrt((f + eta) / eta)
    return R_S


def compute_step_size_governor(
    alpha: float = ALPHA_BASE,
    delta: float = 0.0001,
    eta_eff: float = ETA_BASE,
    k_norm_sq: float = 0.64 ** 2,
) -> float:
    """
    Maximum theta for which the ISS proof holds given current gates and key norm.

    theta_safe = (f - eta)^2 / (mu * (f + eta) * K^2)

    Returns theta_safe. If current theta > theta_safe, the system should
    either reduce theta or fall back to conservative clamps.
    """
    vals = compute_lyapunov_intermediates(alpha, delta)
    f, mu = vals["f"], vals["mu"]

    if eta_eff >= f or k_norm_sq < 1e-15:
        return 0.0

    f_minus_eta = f - eta_eff
    f_plus_eta = f + eta_eff

    return f_minus_eta ** 2 / (mu * f_plus_eta * max(k_norm_sq, 1e-15))


# =============================================================================
# VALIDATION
# =============================================================================


def validate_constants() -> dict[str, bool]:
    """
    Validate constants maintain expected relationships.

    Note: Learning gate ratio validation removed after falsification.
    phi-derivation for learning gates was proven suboptimal.
    """
    results = {}

    # Golden ratio identity (mathematical, still valid)
    results["phi_identity"] = abs(PHI ** 2 - (PHI + 1)) < 1e-10

    # Reciprocal identity (mathematical, still valid)
    results["phi_inv_identity"] = abs(PHI * PHI_INV - 1) < 1e-10

    # Empirical constants are in valid ranges
    results["empirical_alpha_valid"] = 0 < ALPHA_BASE < 0.1
    results["empirical_theta_valid"] = 0 < THETA_BASE < 0.5
    results["empirical_eta_valid"] = 0 < ETA_BASE < 1.0

    # Coherence geometric sequence (not yet falsified)
    results["coherence_sequence"] = all([
        abs(COHERENCE_OPTIMAL / COHERENCE_DAMPEN - PHI) < 1e-10,
        abs(COHERENCE_DAMPEN / COHERENCE_ALERT - PHI) < 1e-10,
    ])

    # Fibonacci sequence (mathematical, always valid)
    results["fibonacci_sequence"] = all(
        FIB[i] == FIB[i-1] + FIB[i-2] for i in range(2, len(FIB))
    )

    return results


if __name__ == "__main__":
    # Self-test
    results = validate_constants()
    print("COGNITIVE SUBSTRATE CONSTANTS VALIDATION")
    print("=" * 50)
    print("\nEMPIRICAL (Validated):")
    print(f"  ALPHA_BASE = {ALPHA_BASE} (weight decay)")
    print(f"  THETA_BASE = {THETA_BASE} (learning rate)")
    print(f"  ETA_BASE   = {ETA_BASE} (momentum)")
    print("\nDEPRECATED (Falsified):")
    print(f"  _ALPHA_PHI = {_ALPHA_PHI:.4f} (67% more drift)")
    print(f"  _THETA_PHI = {_THETA_PHI:.4f}")
    print(f"  _ETA_PHI   = {_ETA_PHI:.4f} (40% less coherence)")
    print("\n" + "=" * 50)
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
    print("=" * 50)
    all_passed = all(results.values())
    print(f"Overall: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
