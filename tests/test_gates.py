"""
TITANS Disposition — Stability Gate Tests
==========================================

Tests for the principled norm caps and stability gates derived from the
TITANS M-vector convergence proof.

See: docs/research/CONVERGENCE_PROOF.md
"""

from __future__ import annotations

import numpy as np
import pytest

from titans_disposition.constants import (
    ALPHA_BASE,
    THETA_BASE,
    ETA_BASE,
    ISS_M_NORM_CAP,
    ISS_S_NORM_CAP,
    compute_iss_norm_bound,
    stability_gate_2step,
    stability_gate_nstep,
    find_stable_eta,
    compute_alpha_ceiling,
    compute_spectral_coherence,
    _P_PRODUCTION,
    _P_GRID,
    _GRID_ALPHAS,
    _GRID_ETAS,
    _compute_p_entry,
    _is_positive_definite,
    _lookup_p,
    SPECTRAL_COHERENCE_OPTIMAL,
    SPECTRAL_COHERENCE_DAMPEN,
    COHERENCE_OPTIMAL,
    COHERENCE_DAMPEN,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _random_embedding(dim: int = 64, seed: int = 42) -> np.ndarray:
    """Generate a deterministic random L2-normalized embedding."""
    rng = np.random.default_rng(seed)
    vec = rng.standard_normal(dim).astype(np.float64)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec


# ===========================================================================
# 1. compute_iss_norm_bound — Pure math tests
# ===========================================================================

class TestISSNormBound:
    """Verify the ISS Lyapunov norm bound computation."""

    def test_iss_bound_production_values(self):
        """R_M ~ 174 with production constants."""
        R_M = compute_iss_norm_bound(
            alpha=ALPHA_BASE,
            delta=0.0001,
            theta=THETA_BASE,
            eta=ETA_BASE,
            K=0.64,
            V=0.77,
        )
        assert 150.0 < R_M < 200.0, (
            f"ISS bound R_M={R_M:.1f} should be ~174 with production values"
        )

    def test_iss_bound_zero_momentum(self):
        """eta=0 edge case: bound should still be finite and positive."""
        R_M = compute_iss_norm_bound(
            alpha=ALPHA_BASE, delta=0.0001, theta=THETA_BASE,
            eta=0.0, K=0.64, V=0.77,
        )
        assert R_M > 0, "ISS bound must be positive even with eta=0"
        assert np.isfinite(R_M), "ISS bound must be finite"


# ===========================================================================
# 2. stability_gate_2step — Switching stability tests
# ===========================================================================

class TestStabilityGate:
    """Verify the 2-step expansion test."""

    def test_stability_gate_stable_case(self):
        """Identical keys -> spectral radius < 1."""
        rng = np.random.default_rng(42)
        k = rng.standard_normal(64)
        k /= np.linalg.norm(k)

        is_stable, rho = stability_gate_2step(
            k_current=k, k_prev=k,
            alpha=ALPHA_BASE, theta=THETA_BASE, eta=ETA_BASE,
        )
        assert is_stable, f"Identical keys should be stable, got rho={rho}"
        assert rho <= 1.0

    def test_stability_gate_switching_counterexample(self):
        """Alternating keys with large norm difference -> finite rho."""
        rng = np.random.default_rng(99)
        k_small = rng.standard_normal(64)
        k_small = k_small / np.linalg.norm(k_small) * 5.0
        k_large = rng.standard_normal(64)
        k_large = k_large / np.linalg.norm(k_large) * 10.0

        _, rho = stability_gate_2step(
            k_current=k_large, k_prev=k_small,
            alpha=ALPHA_BASE, theta=THETA_BASE, eta=ETA_BASE,
        )
        assert np.isfinite(rho), f"Spectral radius should be finite, got {rho}"
        assert rho > 0


# ===========================================================================
# 3. compute_alpha_ceiling — Retention-derived bound
# ===========================================================================

class TestAlphaCeiling:
    """Verify retention-derived alpha ceiling."""

    def test_alpha_ceiling_basic(self):
        """retention=0.95, T=10 -> reasonable alpha."""
        alpha_max = compute_alpha_ceiling(retention=0.95, horizon=10)
        assert 0.004 < alpha_max < 0.007

    def test_alpha_ceiling_perfect_retention(self):
        """retention=1.0 -> alpha_max=0."""
        alpha_max = compute_alpha_ceiling(retention=1.0, horizon=10)
        assert alpha_max == 0.0

    def test_alpha_ceiling_short_horizon(self):
        """Shorter horizon -> higher alpha allowed."""
        alpha_short = compute_alpha_ceiling(retention=0.95, horizon=3)
        alpha_long = compute_alpha_ceiling(retention=0.95, horizon=30)
        assert alpha_short > alpha_long


# ===========================================================================
# 4. N-step windowed spectral radius
# ===========================================================================

class TestNStepStabilityGate:
    """Verify N-step windowed spectral radius computation."""

    def test_nstep_identical_keys_stable(self):
        rng = np.random.default_rng(42)
        k = rng.standard_normal(64)
        k /= np.linalg.norm(k)

        k_history = [k.copy() for _ in range(4)]
        is_stable, rho = stability_gate_nstep(
            k_history, alpha=ALPHA_BASE, theta=THETA_BASE, eta=ETA_BASE,
        )
        assert is_stable
        assert rho <= 1.0

    def test_nstep_fallback_to_2step(self):
        """With exactly 2 keys, nstep should produce the same result as 2step."""
        rng = np.random.default_rng(42)
        k1 = rng.standard_normal(64)
        k1 /= np.linalg.norm(k1)
        k2 = rng.standard_normal(64)
        k2 /= np.linalg.norm(k2)

        is_stable_2, rho_2 = stability_gate_2step(
            k2, k1, alpha=ALPHA_BASE, theta=THETA_BASE, eta=ETA_BASE,
        )
        is_stable_n, rho_n = stability_gate_nstep(
            [k1, k2], alpha=ALPHA_BASE, theta=THETA_BASE, eta=ETA_BASE,
        )
        assert is_stable_2 == is_stable_n
        assert abs(rho_2 - rho_n) < 1e-10

    def test_nstep_single_key_returns_stable(self):
        k = np.ones(64)
        is_stable, rho = stability_gate_nstep(
            [k], alpha=ALPHA_BASE, theta=THETA_BASE, eta=ETA_BASE,
        )
        assert is_stable
        assert rho == 0.0

    def test_nstep_empty_history_returns_stable(self):
        is_stable, rho = stability_gate_nstep(
            [], alpha=ALPHA_BASE, theta=THETA_BASE, eta=ETA_BASE,
        )
        assert is_stable
        assert rho == 0.0


# ===========================================================================
# 5. Principled eta bisection
# ===========================================================================

class TestFindStableEta:
    """Verify binary search for largest stable eta."""

    def test_find_stable_eta_returns_max_when_stable(self):
        rng = np.random.default_rng(42)
        k = rng.standard_normal(64)
        k /= np.linalg.norm(k)

        eta_safe = find_stable_eta(
            k, k, alpha=ALPHA_BASE, theta=THETA_BASE, eta_max=0.9,
        )
        assert eta_safe == 0.9

    def test_find_stable_eta_result_is_stable(self):
        """The returned eta_safe should produce rho <= 1."""
        rng = np.random.default_rng(42)
        k1 = rng.standard_normal(64)
        k1 = k1 / np.linalg.norm(k1) * 6.0
        k2 = rng.standard_normal(64)
        k2 = k2 / np.linalg.norm(k2) * 4.0

        eta_safe = find_stable_eta(
            k1, k2, alpha=ALPHA_BASE, theta=THETA_BASE, eta_max=0.9,
        )
        is_stable, rho = stability_gate_2step(
            k1, k2, alpha=ALPHA_BASE, theta=THETA_BASE, eta=eta_safe,
        )
        assert is_stable, f"eta_safe={eta_safe} should be stable, got rho={rho}"


# ===========================================================================
# 6. Spectral coherence
# ===========================================================================

class TestSpectralCoherence:
    """Verify Davis-Kahan spectral coherence computation."""

    def test_identical_matrices_return_one(self):
        rng = np.random.default_rng(42)
        M = rng.standard_normal((64, 128))
        coherence = compute_spectral_coherence(M, M.copy(), top_k=10)
        assert abs(coherence - 1.0) < 1e-10

    def test_perturbed_matrix_less_than_one(self):
        rng = np.random.default_rng(42)
        M = rng.standard_normal((64, 128))
        M_perturbed = M + rng.standard_normal((64, 128)) * 5.0
        coherence = compute_spectral_coherence(M, M_perturbed, top_k=10)
        assert 0.0 <= coherence < 1.0

    def test_near_zero_matrix_returns_neutral(self):
        M = np.zeros((64, 128))
        M_anchor = np.random.default_rng(42).standard_normal((64, 128))
        coherence = compute_spectral_coherence(M, M_anchor, top_k=10)
        assert coherence == 1.0

    def test_coherence_in_zero_one_range(self):
        for seed in range(10):
            rng = np.random.default_rng(seed)
            M = rng.standard_normal((32, 64))
            M_anchor = rng.standard_normal((32, 64))
            coherence = compute_spectral_coherence(M, M_anchor, top_k=5)
            assert 0.0 <= coherence <= 1.0

    def test_spectral_thresholds_more_conservative_than_phi(self):
        assert SPECTRAL_COHERENCE_OPTIMAL > COHERENCE_OPTIMAL
        assert SPECTRAL_COHERENCE_DAMPEN > COHERENCE_DAMPEN


# ===========================================================================
# 7. P matrix parameterization
# ===========================================================================

class TestPMatrixParameterization:
    """Verify the ISS P matrix lookup grid."""

    def test_production_lookup_matches_hardcoded(self):
        p = _lookup_p(ALPHA_BASE, ETA_BASE)
        assert p is _P_PRODUCTION
        assert p["a"] == pytest.approx(0.02174)
        assert p["b"] == pytest.approx(4.46779)

    def test_production_bound_unchanged(self):
        R_M = compute_iss_norm_bound(
            alpha=ALPHA_BASE, delta=0.0001, theta=THETA_BASE,
            eta=ETA_BASE, K=0.64, V=0.77,
        )
        assert 170.0 < R_M < 180.0

    def test_grid_has_expected_size(self):
        expected = len(_GRID_ALPHAS) * len(_GRID_ETAS)
        assert len(_P_GRID) == expected

    def test_all_grid_entries_positive_definite(self):
        for key, entry in _P_GRID.items():
            assert _is_positive_definite(entry), f"Grid entry {key} not PD"

    def test_higher_alpha_lower_bound(self):
        R_M_low = compute_iss_norm_bound(alpha=0.0005, eta=0.9)
        R_M_high = compute_iss_norm_bound(alpha=0.01, eta=0.9)
        assert R_M_high < R_M_low

    def test_bound_finite_across_grid(self):
        for alpha in _GRID_ALPHAS:
            for eta in _GRID_ETAS:
                R_M = compute_iss_norm_bound(alpha=alpha, eta=eta)
                assert np.isfinite(R_M) and R_M > 0


def test_verify_lyapunov_condition_production_defaults():
    """Production defaults should satisfy the sufficient condition."""
    from titans_disposition.constants import verify_lyapunov_condition, THETA_BASE

    holds, theta_max, K_crit = verify_lyapunov_condition()
    assert holds, "Production defaults must satisfy Lyapunov condition"
    assert theta_max > THETA_BASE, "theta_max should exceed production theta"
    assert K_crit > 0.64


def test_verify_lyapunov_condition_rejects_large_k():
    """Large spectral norms should fail the sufficient condition."""
    from titans_disposition.constants import verify_lyapunov_condition, THETA_BASE

    holds, theta_max, K_crit = verify_lyapunov_condition(K=5.0)
    assert not holds
    assert theta_max < THETA_BASE
    assert K_crit < 5.0


def test_variant_uses_fallback_caps_when_condition_fails():
    """Variant should use conservative caps when Lyapunov condition fails."""
    from titans_disposition.variant import TITANSVariant, Variant
    from titans_disposition.constants import (
        LYAPUNOV_FALLBACK_M_CAP,
        LYAPUNOV_FALLBACK_S_CAP,
        TITANS_PRINCIPLED_BOUNDS,
    )

    if not TITANS_PRINCIPLED_BOUNDS:
        return

    variant = TITANSVariant(name=Variant.MAC, input_dim=64, memory_dim=128)
    variant.W_K = np.eye(64) * 5.0
    variant.W_V = np.eye(64, 128) * 5.0
    variant._recompute_principled_caps()

    assert variant._principled_m_cap == LYAPUNOV_FALLBACK_M_CAP
    assert variant._principled_s_cap == LYAPUNOV_FALLBACK_S_CAP


def test_iss_m_and_s_bounds_finite():
    """Explicit M and S bounds should be finite for production values."""
    from titans_disposition.constants import (
        compute_iss_m_norm_bound,
        compute_iss_s_norm_bound,
    )

    R_M = compute_iss_m_norm_bound()
    R_S = compute_iss_s_norm_bound()
    assert 100 < R_M < 300, f"R_M should be ~174, got {R_M}"
    assert 5 < R_S < 50, f"R_S should be ~12, got {R_S}"


def test_step_size_governor():
    """Step size governor should return a safe theta above production."""
    from titans_disposition.constants import (
        compute_step_size_governor,
        THETA_BASE,
    )

    theta_safe = compute_step_size_governor()
    assert theta_safe > THETA_BASE, (
        f"Governor should allow production theta: {theta_safe} vs {THETA_BASE}"
    )
