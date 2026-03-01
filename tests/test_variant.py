"""
TITANS Disposition — Variant Core Tests
========================================

Tests for TITANSVariant learning equation, save/load, surprise computation.
"""

from __future__ import annotations

import numpy as np
import pytest

from titans_disposition.variant import TITANSVariant, Variant
from titans_disposition.constants import ALPHA_BASE, THETA_BASE, ETA_BASE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_variant(
    input_dim: int = 64,
    memory_dim: int = 128,
    variant: Variant = Variant.MAC,
    init_scale: float = 0.01,
) -> TITANSVariant:
    """Create a small TITANSVariant for fast tests."""
    return TITANSVariant(
        name=variant,
        input_dim=input_dim,
        memory_dim=memory_dim,
        init_scale=init_scale,
    )


def _sync_gpu(variant: TITANSVariant) -> None:
    """Sync GPU tensors after direct numpy array assignment."""
    if variant._gpu is not None:
        variant._init_gpu()


def _random_embedding(dim: int = 64, seed: int = 42) -> np.ndarray:
    """Generate a deterministic random L2-normalized embedding."""
    rng = np.random.default_rng(seed)
    vec = rng.standard_normal(dim).astype(np.float64)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec


# ===========================================================================
# Core learning equation
# ===========================================================================

class TestLearningEquation:
    """Test M_new = (1-alpha)*M_old + theta*update + eta*momentum."""

    def test_update_weights_changes_m(self):
        """update_weights should modify M."""
        variant = _make_variant()
        m_before = variant.M.copy()
        emb = _random_embedding(dim=64, seed=1)
        variant.update_weights(emb, alpha=0.1, theta=0.3, eta=0.05)
        delta = np.linalg.norm(variant.M - m_before)
        assert delta > 0, "M should change after update"

    def test_update_weights_increments_count(self):
        variant = _make_variant()
        assert variant.update_count == 0
        emb = _random_embedding(dim=64, seed=1)
        variant.update_weights(emb, alpha=0.1, theta=0.3, eta=0.05)
        assert variant.update_count == 1

    def test_zero_gates_preserve_m(self):
        """alpha=0, theta=0, eta=0 with scale=0 should preserve M."""
        variant = _make_variant()
        m_before = variant.M.copy()
        emb = _random_embedding(dim=64, seed=1)
        variant.update_weights(emb, alpha=0.0, theta=0.0, eta=0.0, scale=0.0)
        np.testing.assert_allclose(variant.M, m_before, atol=1e-10)

    def test_m_norm_cap_prevents_explosion(self):
        """Large updates should be capped."""
        variant = _make_variant()
        variant.M = np.ones_like(variant.M) * 1000.0
        emb = _random_embedding(dim=64, seed=1)
        variant.update_weights(emb, alpha=0.0, theta=0.0, eta=0.0, scale=0.0)
        m_norm = float(np.linalg.norm(variant.M))
        assert m_norm <= 201.0, f"M norm should be capped, got {m_norm}"


# ===========================================================================
# V2 paper-aligned methods
# ===========================================================================

class TestV2Methods:
    """Test V2 surprise, gates, and weight update."""

    def test_compute_surprise_v2_returns_tuple(self):
        variant = _make_variant()
        emb = _random_embedding(dim=64, seed=1)
        surprise, gradient = variant.compute_surprise_v2(emb)
        assert isinstance(surprise, float)
        assert 0.0 <= surprise <= 1.0
        assert gradient.shape == (64, 128)

    def test_compute_gates_returns_three_floats(self):
        variant = _make_variant()
        emb = _random_embedding(dim=64, seed=1)
        alpha, theta, eta = variant.compute_gates(emb)
        assert isinstance(alpha, float)
        assert isinstance(theta, float)
        assert isinstance(eta, float)
        assert 0.0 <= alpha <= 1.0
        assert 0.0 <= theta <= 1.0
        assert 0.0 <= eta <= 1.0

    def test_update_weights_v2_returns_delta(self):
        variant = _make_variant()
        emb = _random_embedding(dim=64, seed=1)
        _, gradient = variant.compute_surprise_v2(emb)
        alpha, theta, eta = variant.compute_gates(emb)
        delta = variant.update_weights_v2(gradient, alpha, theta, eta)
        assert delta.shape == variant.M.shape

    def test_v2_full_pipeline(self):
        """Run 10 V2 updates — M should evolve."""
        variant = _make_variant()
        m_initial_norm = float(np.linalg.norm(variant.M))

        for i in range(10):
            emb = _random_embedding(dim=64, seed=100 + i)
            surprise, gradient = variant.compute_surprise_v2(emb)
            alpha, theta, eta = variant.compute_gates(emb)
            variant.update_weights_v2(gradient, alpha, theta, eta)

        m_final_norm = float(np.linalg.norm(variant.M))
        assert variant.update_count == 10
        assert abs(m_final_norm - m_initial_norm) > 1e-6, "M should evolve"


# ===========================================================================
# Save/Load round-trip
# ===========================================================================

class TestSaveLoad:
    """Test state persistence round-trip."""

    def test_round_trip_preserves_m_norm(self):
        variant = _make_variant()
        for i in range(10):
            emb = _random_embedding(dim=64, seed=100 + i)
            variant.update_weights(emb, alpha=0.1, theta=0.3, eta=0.05)

        original_norm = float(np.linalg.norm(variant.M))
        state = variant.save_state()
        restored = TITANSVariant.load_state(state)
        restored_norm = float(np.linalg.norm(restored.M))

        assert abs(original_norm - restored_norm) < 1e-10

    def test_round_trip_preserves_m_elementwise(self):
        variant = _make_variant()
        for i in range(5):
            emb = _random_embedding(dim=64, seed=200 + i)
            variant.update_weights(emb, alpha=0.05, theta=0.2, eta=0.1)

        state = variant.save_state()
        restored = TITANSVariant.load_state(state)
        np.testing.assert_allclose(restored.M, variant.M, atol=1e-10)

    def test_round_trip_preserves_gate_outputs(self):
        variant = _make_variant()
        rng = np.random.default_rng(seed=300)
        variant.W_alpha = rng.standard_normal(64) * 0.1
        variant.W_theta = rng.standard_normal(64) * 0.1
        variant.W_eta = rng.standard_normal(64) * 0.1
        _sync_gpu(variant)

        test_emb = _random_embedding(dim=64, seed=301)
        original_gates = variant.compute_gates(test_emb)

        state = variant.save_state()
        restored = TITANSVariant.load_state(state)
        restored._v2_gate_alpha_sum = 0.0
        restored._v2_gate_theta_sum = 0.0
        restored._v2_gate_eta_sum = 0.0
        restored_gates = restored.compute_gates(test_emb)

        for idx, (orig, rest) in enumerate(zip(original_gates, restored_gates)):
            assert abs(orig - rest) < 1e-4, (
                f"Gate {idx} mismatch: original={orig}, restored={rest}"
            )

    def test_round_trip_preserves_statistics(self):
        variant = _make_variant()
        for i in range(7):
            emb = _random_embedding(dim=64, seed=600 + i)
            variant.update_weights(emb, alpha=0.1, theta=0.2, eta=0.05)
        variant.decay(base_rate=0.01, multiplier=1.0)

        state = variant.save_state()
        restored = TITANSVariant.load_state(state)
        assert restored.update_count == 7
        assert restored.decay_count == 1


# ===========================================================================
# Alpha clamp safety
# ===========================================================================

class TestAlphaClamp:
    """Alpha clamp prevents catastrophic forgetting."""

    def test_v2_compute_gates_alpha_never_exceeds_cap(self):
        variant = _make_variant()
        variant.W_alpha = np.ones(64) * 100.0
        variant.b_alpha = 100.0
        _sync_gpu(variant)

        test_emb = _random_embedding(dim=64, seed=830)
        alpha, _, _ = variant.compute_gates(test_emb)
        assert alpha <= 0.3, f"Alpha={alpha} should be capped"

    def test_v2_alpha_below_cap_passes_through(self):
        variant = _make_variant()
        emb = _random_embedding(dim=64, seed=880)
        alpha, _, _ = variant.compute_gates(emb)
        assert abs(alpha - ALPHA_BASE) < 1e-6
        assert alpha < 0.3


# ===========================================================================
# Surprise computation
# ===========================================================================

class TestSurprise:
    """Test surprise score computation."""

    def test_cold_start_returns_neutral(self):
        variant = _make_variant()
        emb = _random_embedding(dim=64, seed=1)
        surprise = variant.compute_surprise(emb)
        assert surprise == 0.5, "Cold start should return 0.5"

    def test_surprise_in_range(self):
        variant = _make_variant()
        for i in range(20):
            emb = _random_embedding(dim=64, seed=i)
            surprise = variant.compute_surprise(emb)
            assert 0.0 <= surprise <= 1.0

    def test_repeated_input_low_surprise(self):
        """Repeating the same input should reduce surprise."""
        variant = _make_variant()
        emb = _random_embedding(dim=64, seed=42)

        # Build history
        for _ in range(10):
            variant.compute_surprise(emb)

        # Same input after history should have lower surprise
        surprise = variant.compute_surprise(emb)
        assert surprise < 0.3, f"Repeated input should have low surprise, got {surprise}"


# ===========================================================================
# Divergence under different eta
# ===========================================================================

class TestEtaDivergence:
    """Two variants with different surprise produce different M."""

    def test_m_vectors_diverge_under_modulation(self):
        variant_a = _make_variant(input_dim=64, memory_dim=128)
        variant_b = _make_variant(input_dim=64, memory_dim=128)

        variant_a.M = np.zeros_like(variant_a.M)
        variant_b.M = np.zeros_like(variant_b.M)
        variant_a.surprise_momentum = np.zeros_like(variant_a.surprise_momentum)
        variant_b.surprise_momentum = np.zeros_like(variant_b.surprise_momentum)
        variant_b.W_K = variant_a.W_K.copy()
        variant_b.W_V = variant_a.W_V.copy()
        variant_b.W_Q = variant_a.W_Q.copy()
        _sync_gpu(variant_a)
        _sync_gpu(variant_b)

        theta_test = 0.5
        alpha_test = 0.001
        for i in range(100):
            emb = _random_embedding(dim=64, seed=2100 + i)
            _, grad_a = variant_a.compute_surprise_v2(emb)
            eta_a_eff = 0.9 * 0.2  # high surprise -> low eta
            variant_a.update_weights_v2(grad_a, alpha_test, theta_test, eta_a_eff)

            _, grad_b = variant_b.compute_surprise_v2(emb)
            eta_b_eff = 0.9 * 0.9  # low surprise -> high eta
            variant_b.update_weights_v2(grad_b, alpha_test, theta_test, eta_b_eff)

        m_a = variant_a.M.flatten()
        m_b = variant_b.M.flatten()
        norm_a = np.linalg.norm(m_a)
        norm_b = np.linalg.norm(m_b)
        assert norm_a > 0.01
        assert norm_b > 0.01

        cos_sim = float(np.dot(m_a, m_b) / (norm_a * norm_b + 1e-10))
        assert cos_sim < 0.999, f"M vectors should diverge, cosine={cos_sim:.6f}"

        norm_ratio = norm_b / (norm_a + 1e-10)
        assert norm_ratio > 1.05, f"High-eta should have larger M, ratio={norm_ratio:.4f}"
