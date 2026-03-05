"""
TITANS VARIANT
==============

Single memory variant (MAC, MAG, or MAL).
Owns its weight matrix and learning dynamics.

THE learning step happens here:
M_new = (1 - alpha) * M_old + theta * update + eta * momentum

This is where patterns crystallize into weights.
"""

from __future__ import annotations

import time
from collections import deque
from enum import Enum
from typing import Optional, Any
import numpy as np

# GPU acceleration: use PyTorch CUDA when available
try:
    import torch as _torch
    _GPU_AVAILABLE = _torch.cuda.is_available()
except ImportError:
    _torch = None  # type: ignore[assignment]
    _GPU_AVAILABLE = False

from titans_disposition.constants import (
    DECAY_WINDOW,
    EMBEDDING_DIM,
    MAC_MEMORY_DIM,
    MAG_MEMORY_DIM,
    MAL_MEMORY_DIM,
    THETA_BASE,
    ALPHA_BASE,
    ETA_BASE,
    TITANS_PRINCIPLED_BOUNDS,
    ISS_M_NORM_CAP,
    ISS_S_NORM_CAP,
    LYAPUNOV_FALLBACK_M_CAP,
    LYAPUNOV_FALLBACK_S_CAP,
    ISS_SAFETY_MARGIN,
    verify_lyapunov_condition,
    compute_iss_m_norm_bound,
    compute_iss_s_norm_bound,
    compute_step_size_governor,
    compute_alpha_ceiling,
    stability_gate_2step,
    stability_gate_nstep,
    find_stable_eta,
)


class Variant(str, Enum):
    """Memory variant types."""
    MAC = "mac"
    MAG = "mag"
    MAL = "mal"
    DEFAULT = "default"


# Memory dimensions by variant
VARIANT_DIMS: dict[Variant, int] = {
    Variant.MAC: MAC_MEMORY_DIM,  # 2048
    Variant.MAG: MAG_MEMORY_DIM,  # 1024
    Variant.MAL: MAL_MEMORY_DIM,  # 1024
}


class TITANSVariant:
    """
    Single memory variant with weight matrix and learning dynamics.

    Each variant owns:
    - M: Weight matrix [input_dim, memory_dim] - THE cognitive substrate
    - momentum: Momentum buffer for smooth learning
    - embedding_history: For surprise computation
    """

    def __init__(
        self,
        name: Variant = Variant.DEFAULT,
        input_dim: int = EMBEDDING_DIM,
        memory_dim: Optional[int] = None,
        init_scale: float = 0.01,
    ):
        self.name = name
        self.input_dim = input_dim
        self.memory_dim = memory_dim or VARIANT_DIMS.get(name, 1024)

        # Weight matrix - THE cognitive substrate
        # Small random initialization
        self.M = np.random.randn(input_dim, self.memory_dim) * init_scale

        # Momentum buffer for smooth learning
        self.momentum = np.zeros((input_dim, self.memory_dim))

        # History for surprise computation
        self.embedding_history: deque[np.ndarray] = deque(maxlen=DECAY_WINDOW)

        # Running statistics for surprise normalization
        self._error_history: deque[float] = deque(maxlen=100)
        self._surprise_scale: float = 1.0

        # Statistics
        self.update_count: int = 0
        self.decay_count: int = 0
        self.total_crystallization: float = 0.0

        # -- V2 Paper-Aligned State (Behrouz et al. 2501.00663v1) --
        # K/V/Q projections (Paper Eq. 11)
        self.W_K = np.random.randn(input_dim, input_dim) * init_scale
        self.W_V = np.random.randn(input_dim, self.memory_dim) * init_scale
        self.W_Q = np.random.randn(input_dim, input_dim) * init_scale

        # Data-dependent gate projections (Paper Eq. 13-14)
        # Warm start: W=0, bias=sigmoid^{-1}(constant) so initial output matches V1
        self.W_alpha = np.zeros(input_dim)
        self.b_alpha = float(np.log(ALPHA_BASE / (1 - ALPHA_BASE)))
        self.W_theta = np.zeros(input_dim)
        self.b_theta = float(np.log(THETA_BASE / (1 - THETA_BASE)))
        self.W_eta = np.zeros(input_dim)
        self.b_eta = float(np.log(ETA_BASE / (1 - ETA_BASE)))

        # Accumulated momentum buffer (Paper Eq. 14)
        self.surprise_momentum = np.zeros((input_dim, self.memory_dim))

        # Gradient history for V2 surprise normalization
        self._grad_history: deque[float] = deque(maxlen=100)
        self._grad_scale: float = 1.0

        # V2 telemetry accumulators
        self._v2_gate_alpha_sum: float = 0.0
        self._v2_gate_theta_sum: float = 0.0
        self._v2_gate_eta_sum: float = 0.0
        self._v2_grad_norm_sum: float = 0.0
        self._v2_loss_sum: float = 0.0
        self._v2_call_count: int = 0

        # Per-update gate log (diagnostic ring buffer)
        self._v2_gate_log: deque[dict] = deque(maxlen=200)

        # Key history for N-step stability gate (principled bounds)
        self._k_history: deque[np.ndarray] = deque(maxlen=4)

        # Cached principled caps (recomputed when gates change significantly)
        self._principled_m_cap: float = ISS_M_NORM_CAP
        self._principled_s_cap: float = ISS_S_NORM_CAP
        self._caps_alpha: float = ALPHA_BASE  # gate values used for current caps
        self._caps_eta: float = ETA_BASE
        self._caps_recompute_interval: int = 100  # check every N updates
        if TITANS_PRINCIPLED_BOUNDS:
            self._recompute_principled_caps()

        # GPU acceleration for V2 path
        self._gpu: dict[str, Any] | None = None
        if _GPU_AVAILABLE:
            self._init_gpu()

    def compute_surprise(self, embedding: np.ndarray) -> float:
        """
        Compute surprise = prediction error.

        How unexpected is this input given current state?
        Returns 0-1 normalized surprise score.
        """
        embedding = np.nan_to_num(embedding, nan=0.0, posinf=1.0, neginf=-1.0)
        if len(self.embedding_history) < 2:
            self.embedding_history.append(embedding)
            return 0.5  # Neutral during cold start

        # Predict expected embedding from recent history
        # Simple: weighted average of recent embeddings
        predicted = self._predict_embedding()

        # Surprise = L2 distance from prediction
        predicted = np.nan_to_num(predicted, nan=0.0, posinf=1.0, neginf=-1.0)
        error = float(np.linalg.norm(embedding - predicted))

        # Track error history for normalization
        self._error_history.append(error)

        # Update surprise scale (running mean of errors)
        if len(self._error_history) >= 10:
            self._surprise_scale = max(0.1, np.mean(list(self._error_history)))

        # Normalize to 0-1 using exponential mapping
        surprise = 1 - np.exp(-error / self._surprise_scale)

        self.embedding_history.append(embedding)
        return float(np.clip(surprise, 0.0, 1.0))

    def update_weights(
        self,
        embedding: np.ndarray,
        alpha: float,
        theta: float,
        eta: float,
        scale: float = 1.0,
    ) -> np.ndarray:
        """
        THE learning step.

        M_new = (1 - alpha*scale) * M_old + theta*scale * update + eta*scale * momentum

        Args:
            embedding: Input embedding [input_dim]
            alpha: Forget rate
            theta: Learning rate
            eta: Momentum rate
            scale: Scale factor (from identity coherence)

        Returns:
            Weight delta (M_new - M_old) for thermodynamic tracking.
        """
        # Compute update term via outer product
        # embedding [input_dim] @ resonance [memory_dim] -> [input_dim, memory_dim]
        embedding = np.nan_to_num(embedding, nan=0.0, posinf=1.0, neginf=-1.0)
        resonance = self._query_memory_normalized(embedding)
        update = np.outer(embedding, resonance)

        # Store old M for delta computation
        M_old = self.M.copy()

        # Apply learning equation
        self.M = (
            (1 - alpha * scale) * self.M +
            (theta * scale) * update +
            (eta * scale) * self.momentum
        )
        self.M = np.nan_to_num(self.M, nan=0.0, posinf=1.0, neginf=-1.0)

        # Safety belt: cap matrix norm to prevent numeric explosion
        # Equilibrium norm is ~17 for standard gate constants.
        # Principled: ISS bound ~174 (+margin -> 200). Legacy: 1000.
        m_cap = self._principled_m_cap if TITANS_PRINCIPLED_BOUNDS else 1000.0
        m_norm = np.linalg.norm(self.M)
        if np.isfinite(m_norm) and m_norm > m_cap:
            self.M = self.M * (m_cap / m_norm)

        # Update momentum for next step
        self.momentum = np.nan_to_num(theta * update, nan=0.0, posinf=1.0, neginf=-1.0)

        # Track statistics
        self.update_count += 1
        delta = self.M - M_old
        self.total_crystallization += float(np.linalg.norm(delta))

        return delta

    # -- GPU Acceleration -------------------------------------------------------

    def _init_gpu(self) -> None:
        """Move V2 matrices to GPU for accelerated computation."""
        dev = _torch.device('cuda')
        self._gpu = {
            'dev': dev,
            'M': _torch.tensor(self.M, device=dev, dtype=_torch.float32),
            'W_K': _torch.tensor(self.W_K, device=dev, dtype=_torch.float32),
            'W_V': _torch.tensor(self.W_V, device=dev, dtype=_torch.float32),
            'W_Q': _torch.tensor(self.W_Q, device=dev, dtype=_torch.float32),
            'W_alpha': _torch.tensor(self.W_alpha, device=dev, dtype=_torch.float32),
            'b_alpha': _torch.tensor(self.b_alpha, device=dev, dtype=_torch.float32),
            'W_theta': _torch.tensor(self.W_theta, device=dev, dtype=_torch.float32),
            'b_theta': _torch.tensor(self.b_theta, device=dev, dtype=_torch.float32),
            'W_eta': _torch.tensor(self.W_eta, device=dev, dtype=_torch.float32),
            'b_eta': _torch.tensor(self.b_eta, device=dev, dtype=_torch.float32),
            'S': _torch.tensor(self.surprise_momentum, device=dev, dtype=_torch.float32),
        }

    def _sync_gpu_to_cpu(self) -> None:
        """Sync GPU M and momentum back to numpy (float32 -- no cast)."""
        if self._gpu is None:
            return
        self.M = self._gpu['M'].cpu().numpy()
        self.surprise_momentum = self._gpu['S'].cpu().numpy()

    def _sync_cpu_to_gpu(self) -> None:
        """Sync numpy M to GPU (after decay or external modification)."""
        if self._gpu is None:
            return
        dev = self._gpu['dev']
        self._gpu['M'] = _torch.tensor(self.M, device=dev, dtype=_torch.float32)

    # -- V2 Paper-Aligned Methods (Behrouz et al. 2501.00663v1) ----------------

    def compute_surprise_v2(
        self, embedding: np.ndarray
    ) -> tuple[float, np.ndarray]:
        """
        Paper Eq. 12: Associative memory loss surprise.

        l(M; x_t) = ||M.T @ k_t - v_t||^2

        Returns (surprise_score, gradient_matrix) where gradient is
        nabla_M l = 2 * outer(k, M.T @ k - v).
        """
        embedding = np.nan_to_num(embedding, nan=0.0, posinf=1.0, neginf=-1.0)

        if self._gpu is not None:
            # -- GPU path --
            g = self._gpu
            emb = _torch.tensor(embedding, device=g['dev'], dtype=_torch.float32)
            k = emb @ g['W_K']
            v = emb @ g['W_V']
            prediction = g['M'].T @ k
            error = prediction - v
            loss = float(error.square().sum().item())
            gradient_t = 2.0 * _torch.outer(k, error)
            grad_norm = float(gradient_t.norm().item())
            gradient = gradient_t.cpu().numpy()
        else:
            # -- CPU path --
            k = embedding @ self.W_K
            v = embedding @ self.W_V
            prediction = self.M.T @ k
            error = prediction - v
            loss = float(np.sum(error ** 2))
            gradient = 2.0 * np.outer(k, error)
            grad_norm = float(np.linalg.norm(gradient))

        # Cache key vector for N-step stability gate
        k_np = k.cpu().numpy() if self._gpu is not None else k
        self._k_history.append(k_np.copy())

        # Surprise from gradient norm (shared)
        self._grad_history.append(grad_norm)
        if len(self._grad_history) >= 10:
            self._grad_scale = max(0.1, float(np.mean(list(self._grad_history))))

        surprise = 1.0 - np.exp(-grad_norm / self._grad_scale)
        surprise = float(np.clip(surprise, 0.0, 1.0))

        # Telemetry
        self._v2_grad_norm_sum += grad_norm
        self._v2_loss_sum += loss
        self._v2_call_count += 1

        # Keep embedding history for compatibility
        self.embedding_history.append(embedding)

        return surprise, gradient

    def compute_gates(
        self, embedding: np.ndarray
    ) -> tuple[float, float, float]:
        """
        Paper Eq. 13-14: Data-dependent gates via sigmoid projection.

        alpha_t in [0,1] forget gate
        theta_t in [0,1] learn gate
        eta_t in [0,1] momentum gate

        Warm start: W=0 so output = sigmoid(bias) = V1 constant.
        """
        embedding = np.nan_to_num(embedding, nan=0.0, posinf=1.0, neginf=-1.0)

        if self._gpu is not None:
            # -- GPU path --
            g = self._gpu
            emb = _torch.tensor(embedding, device=g['dev'], dtype=_torch.float32)
            alpha = float(_torch.sigmoid(emb @ g['W_alpha'] + g['b_alpha']).item())
            theta = float(_torch.sigmoid(emb @ g['W_theta'] + g['b_theta']).item())
            eta = float(_torch.sigmoid(emb @ g['W_eta'] + g['b_eta']).item())
        else:
            # -- CPU path --
            alpha = float(
                1.0 / (1.0 + np.exp(-(embedding @ self.W_alpha + self.b_alpha)))
            )
            theta = float(
                1.0 / (1.0 + np.exp(-(embedding @ self.W_theta + self.b_theta)))
            )
            eta = float(
                1.0 / (1.0 + np.exp(-(embedding @ self.W_eta + self.b_eta)))
            )

        # Safety clamp: prevent catastrophic forgetting via unconstrained alpha.
        # Without this, a single adversarial embedding could erase ~100% of M.
        if TITANS_PRINCIPLED_BOUNDS:
            # Principled: half-life retention bound (convergence proof).
            # alpha_max = 1 - r^(1/T) where r=0.95 retention over T=10 steps.
            max_alpha = compute_alpha_ceiling()
        else:
            # Legacy: maturity-gated linear ramp.
            ALPHA_FLOOR = 0.30  # Conservative -- identity not yet stable
            ALPHA_CEIL = 0.55   # Relaxed
            RAMP_START = 5      # Begin relaxation
            RAMP_END = 15       # Full relaxation
            progress = max(0.0, min(1.0, (self.update_count - RAMP_START) / (RAMP_END - RAMP_START)))
            max_alpha = ALPHA_FLOOR + progress * (ALPHA_CEIL - ALPHA_FLOOR)
        if alpha > max_alpha:
            alpha = max_alpha

        # Telemetry
        self._v2_gate_alpha_sum += alpha
        self._v2_gate_theta_sum += theta
        self._v2_gate_eta_sum += eta

        return alpha, theta, eta

    def log_gate_update(
        self,
        alpha: float,
        theta: float,
        eta_raw: float,
        eta_effective: float,
        surprise: float,
        grad_norm: float,
        loss: float,
    ) -> None:
        """Record per-update gate values for diagnostic analysis."""
        # Compute alpha ceiling for observability
        if TITANS_PRINCIPLED_BOUNDS:
            alpha_max = compute_alpha_ceiling()
        else:
            ALPHA_FLOOR = 0.30
            ALPHA_CEIL = 0.55
            RAMP_START = 5
            RAMP_END = 15
            progress = max(0.0, min(1.0, (self.update_count - RAMP_START) / (RAMP_END - RAMP_START)))
            alpha_max = ALPHA_FLOOR + progress * (ALPHA_CEIL - ALPHA_FLOOR)

        entry: dict[str, Any] = {
            "ts": time.time(),
            "alpha": alpha,
            "alpha_max": alpha_max,
            "theta": theta,
            "eta_raw": eta_raw,
            "eta_effective": eta_effective,
            "surprise": surprise,
            "grad_norm": grad_norm,
            "loss": loss,
            "update_count": self.update_count,
            "m_norm": float(np.linalg.norm(self.M)),
            "s_norm": float(np.linalg.norm(self.surprise_momentum)),
        }

        # Enrich with principled bounds diagnostics
        if TITANS_PRINCIPLED_BOUNDS:
            entry["principled_m_cap"] = self._principled_m_cap
            entry["principled_s_cap"] = self._principled_s_cap
            if len(self._k_history) >= 2:
                _, rho = stability_gate_nstep(
                    list(self._k_history), alpha, theta, eta_raw,
                )
                entry["stability_rho"] = rho
            else:
                entry["stability_rho"] = 0.0

        self._v2_gate_log.append(entry)

    def update_weights_v2(
        self,
        gradient: np.ndarray,
        alpha: float,
        theta: float,
        eta: float,
    ) -> np.ndarray:
        """
        Paper Eq. 13-14: Memory update with accumulated momentum.

        S_t = eta * S_{t-1} - theta * grad_l(M; x_t)   (Eq. 14)
        M_t = (1 - alpha) * M_{t-1} + S_t               (Eq. 13)

        Returns:
            Weight delta (M_new - M_old) for thermodynamic tracking.
        """
        # Periodic recompute of caps from runtime gate means
        if (
            TITANS_PRINCIPLED_BOUNDS
            and self._v2_call_count > 0
            and self._v2_call_count % self._caps_recompute_interval == 0
        ):
            n = self._v2_call_count
            mean_alpha = self._v2_gate_alpha_sum / n
            mean_eta = self._v2_gate_eta_sum / n
            # Recompute if gate means drifted >20% from cached values
            alpha_drift = abs(mean_alpha - self._caps_alpha) / max(self._caps_alpha, 1e-10)
            eta_drift = abs(mean_eta - self._caps_eta) / max(self._caps_eta, 1e-10)
            if alpha_drift > 0.2 or eta_drift > 0.2:
                self._recompute_principled_caps(alpha=mean_alpha, eta=mean_eta)

        s_cap = self._principled_s_cap if TITANS_PRINCIPLED_BOUNDS else 500.0
        m_cap = self._principled_m_cap if TITANS_PRINCIPLED_BOUNDS else 1000.0

        # N-step windowed expansion test + principled eta bisection
        eta_eff = eta
        if TITANS_PRINCIPLED_BOUNDS and len(self._k_history) >= 2:
            is_stable, rho = stability_gate_nstep(
                list(self._k_history), alpha, theta, eta,
            )
            if not is_stable:
                # Bisect on 2-step (last two keys) for eta_safe
                eta_eff = find_stable_eta(
                    self._k_history[-1], self._k_history[-2],
                    alpha, theta, eta,
                )

        if self._gpu is not None:
            # -- GPU path --
            g = self._gpu
            grad_t = _torch.tensor(gradient, device=g['dev'], dtype=_torch.float32)

            # Momentum (Eq. 14)
            g['S'] = eta_eff * g['S'] - theta * grad_t
            g['S'] = _torch.nan_to_num(g['S'], nan=0.0, posinf=1.0, neginf=-1.0)
            s_norm = float(g['S'].norm().item())
            if s_norm > s_cap:
                g['S'] *= s_cap / s_norm

            M_old = g['M'].clone()

            # Memory update (Eq. 13)
            g['M'] = (1.0 - alpha) * g['M'] + g['S']
            g['M'] = _torch.nan_to_num(g['M'], nan=0.0, posinf=1.0, neginf=-1.0)
            m_norm = float(g['M'].norm().item())
            if m_norm > m_cap:
                g['M'] *= m_cap / m_norm

            # Delta on GPU, then sync everything to CPU
            delta_t = g['M'] - M_old
            self.update_count += 1
            delta_norm = float(delta_t.norm().item())
            self.total_crystallization += delta_norm
            self._sync_gpu_to_cpu()
            delta = delta_t.cpu().numpy()
            return delta

        # -- CPU path --
        self.surprise_momentum = (
            eta_eff * self.surprise_momentum - theta * gradient
        )
        self.surprise_momentum = np.nan_to_num(
            self.surprise_momentum, nan=0.0, posinf=1.0, neginf=-1.0
        )
        s_norm = np.linalg.norm(self.surprise_momentum)
        if np.isfinite(s_norm) and s_norm > s_cap:
            self.surprise_momentum *= s_cap / s_norm

        M_old = self.M.copy()
        self.M = (1.0 - alpha) * self.M + self.surprise_momentum
        self.M = np.nan_to_num(self.M, nan=0.0, posinf=1.0, neginf=-1.0)
        m_norm = np.linalg.norm(self.M)
        if np.isfinite(m_norm) and m_norm > m_cap:
            self.M *= m_cap / m_norm

        self.update_count += 1
        delta = self.M - M_old
        self.total_crystallization += float(np.linalg.norm(delta))
        return delta

    def query_v2(self, embedding: np.ndarray) -> np.ndarray:
        """
        Paper-aligned retrieval using learned W_Q projection.

        y_t = M.T @ (x_t @ W_Q)
        """
        embedding = np.nan_to_num(embedding, nan=0.0, posinf=1.0, neginf=-1.0)
        if self._gpu is not None:
            g = self._gpu
            emb = _torch.tensor(embedding, device=g['dev'], dtype=_torch.float32)
            q = emb @ g['W_Q']
            result = g['M'].T @ q
            return np.nan_to_num(result.cpu().numpy(), nan=0.0, posinf=1.0, neginf=-1.0)
        q = embedding @ self.W_Q
        return np.nan_to_num(self.M.T @ q, nan=0.0, posinf=1.0, neginf=-1.0)

    # -- End V2 Methods --------------------------------------------------------

    def _recompute_principled_caps(
        self, alpha: float = ALPHA_BASE, eta: float = ETA_BASE,
    ) -> None:
        """Recompute ISS norm caps from given gate values.

        Guards on Lyapunov sufficient condition: if the condition fails
        (e.g. large spectral norms), falls back to conservative fixed caps
        instead of using proof-derived bounds outside the theorem's validity.
        """
        # Estimate spectral norms from weight matrices.
        K = float(np.linalg.norm(self.W_K, ord=2)) if hasattr(self, "W_K") else 0.64
        V = float(np.linalg.norm(self.W_V, ord=2)) if hasattr(self, "W_V") else 0.77

        condition_holds, theta_max, K_crit = verify_lyapunov_condition(
            alpha=alpha, eta=eta, K=K,
        )
        theta_safe = compute_step_size_governor(
            alpha=alpha, eta_eff=eta, k_norm_sq=K ** 2,
        )

        if not condition_holds:
            self._principled_m_cap = LYAPUNOV_FALLBACK_M_CAP
            self._principled_s_cap = LYAPUNOV_FALLBACK_S_CAP
        else:
            self._principled_m_cap = (
                compute_iss_m_norm_bound(alpha=alpha, eta=eta, K=K, V=V)
                * ISS_SAFETY_MARGIN
            )
            self._principled_s_cap = max(
                25.0,
                compute_iss_s_norm_bound(alpha=alpha, eta=eta, K=K, V=V),
            )

        # Keep local values available for debugging without widening public API.
        self._lyapunov_theta_max = min(theta_max, theta_safe)
        self._lyapunov_k_crit = K_crit
        self._caps_alpha = alpha
        self._caps_eta = eta

    def decay(self, base_rate: float, multiplier: float = 1.0) -> None:
        """
        Adaptive forgetting.

        M = M * (1 - rate*multiplier)

        Called every cycle to allow graceful forgetting.
        """
        rate = base_rate * multiplier
        self.M *= (1 - rate)
        self.decay_count += 1
        # Keep GPU copy in sync after CPU-side decay
        self._sync_cpu_to_gpu()

    def query(self, embedding: np.ndarray) -> np.ndarray:
        """
        Query memory with embedding, get resonance pattern.

        Returns [memory_dim] vector representing how the input
        resonates with stored patterns.
        """
        embedding = np.nan_to_num(embedding, nan=0.0, posinf=1.0, neginf=-1.0)
        return np.nan_to_num(self.M.T @ embedding, nan=0.0, posinf=1.0, neginf=-1.0)

    def _query_memory_normalized(self, embedding: np.ndarray) -> np.ndarray:
        """
        Internal query with normalization for update computation.
        """
        embedding = np.nan_to_num(embedding, nan=0.0, posinf=1.0, neginf=-1.0)
        resonance = np.nan_to_num(self.M.T @ embedding, nan=0.0, posinf=1.0, neginf=-1.0)

        norm = np.linalg.norm(resonance)
        if np.isfinite(norm) and norm > 0:
            resonance = resonance / norm
        else:
            resonance = np.zeros_like(resonance)

        return resonance

    def _predict_embedding(self) -> np.ndarray:
        """
        Predict expected embedding from recent history.

        Uses exponentially weighted average of recent embeddings.
        """
        if not self.embedding_history:
            return np.zeros(self.input_dim)

        history = list(self.embedding_history)

        # Exponential weights (more recent = higher weight)
        weights = np.exp(np.linspace(-1, 0, len(history)))
        weights /= weights.sum()

        # Weighted average
        predicted = np.zeros(self.input_dim)
        for w, emb in zip(weights, history):
            predicted += w * emb

        return predicted

    def get_stats(self) -> dict:
        """Get variant statistics for monitoring."""
        M_norm = float(np.linalg.norm(self.M))
        M_sparsity = float(np.mean(np.abs(self.M) < 0.01))

        stats = {
            "name": self.name.value,
            "input_dim": self.input_dim,
            "memory_dim": self.memory_dim,
            "matrix_norm": M_norm,
            "matrix_sparsity": M_sparsity,
            "update_count": self.update_count,
            "decay_count": self.decay_count,
            "total_crystallization": self.total_crystallization,
            "history_size": len(self.embedding_history),
            "surprise_scale": self._surprise_scale,
        }

        # V2 telemetry (only populated when V2 path is active)
        if self._v2_call_count > 0:
            n = self._v2_call_count
            stats["v2_metrics"] = {
                "gate_alpha_mean": self._v2_gate_alpha_sum / n,
                "gate_theta_mean": self._v2_gate_theta_sum / n,
                "gate_eta_mean": self._v2_gate_eta_sum / n,
                "gradient_norm_mean": self._v2_grad_norm_sum / n,
                "momentum_norm": float(np.linalg.norm(self.surprise_momentum)),
                "associative_loss_mean": self._v2_loss_sum / n,
            }

        # Per-update gate log -- last 50 entries
        if self._v2_gate_log:
            stats["v2_gate_log"] = list(self._v2_gate_log)[-50:]

        return stats

    def save_state(self) -> dict[str, Any]:
        """Save variant state for persistence."""
        state = {
            "name": self.name.value,
            "M": self.M.tolist(),
            "momentum": self.momentum.tolist(),
            "update_count": self.update_count,
            "decay_count": self.decay_count,
            "total_crystallization": self.total_crystallization,
            "surprise_scale": self._surprise_scale,
            # V2 state
            "W_K": self.W_K.tolist(),
            "W_V": self.W_V.tolist(),
            "W_Q": self.W_Q.tolist(),
            "W_alpha": self.W_alpha.tolist(),
            "b_alpha": self.b_alpha,
            "W_theta": self.W_theta.tolist(),
            "b_theta": self.b_theta,
            "W_eta": self.W_eta.tolist(),
            "b_eta": self.b_eta,
            "surprise_momentum": self.surprise_momentum.tolist(),
            "grad_scale": self._grad_scale,
        }
        return state

    @classmethod
    def load_state(cls, state: dict[str, Any]) -> "TITANSVariant":
        """Load variant from saved state."""
        variant = cls(
            name=Variant(state["name"]),
            input_dim=len(state["M"]),
            memory_dim=len(state["M"][0]),
        )
        variant.M = np.array(state["M"])
        variant.momentum = np.array(state["momentum"])
        variant.update_count = state["update_count"]
        variant.decay_count = state["decay_count"]
        variant.total_crystallization = state["total_crystallization"]
        variant._surprise_scale = state.get("surprise_scale", 1.0)

        # V2 state (backward-compatible -- absent in pre-V2 saves)
        if "W_K" in state:
            variant.W_K = np.array(state["W_K"])
            variant.W_V = np.array(state["W_V"])
            variant.W_Q = np.array(state["W_Q"])
            variant.W_alpha = np.array(state["W_alpha"])
            variant.b_alpha = state["b_alpha"]
            variant.W_theta = np.array(state["W_theta"])
            variant.b_theta = state["b_theta"]
            variant.W_eta = np.array(state["W_eta"])
            variant.b_eta = state["b_eta"]
            variant.surprise_momentum = np.array(state["surprise_momentum"])
            variant._grad_scale = state.get("grad_scale", 1.0)

        # Re-init GPU with loaded weights
        if _GPU_AVAILABLE:
            variant._init_gpu()

        return variant

    def compute_surprise_scalar(self, embedding: np.ndarray) -> float:
        """Loss-based surprise for a single embedding against current M state."""
        k = embedding @ self.W_K
        v = embedding @ self.W_V
        pred = self.M.T @ k
        error_sq = np.sum((pred - v) ** 2)
        return float(1.0 - np.exp(-error_sq / self._grad_scale))

    def compute_surprise_scalar_batch(self, embeddings: np.ndarray) -> np.ndarray:
        """Batched surprise for N embeddings. BLAS-vectorized, no Python loop."""
        K = embeddings @ self.W_K
        V = embeddings @ self.W_V
        Pred = K @ self.M
        errors_sq = np.sum((Pred - V) ** 2, axis=1)
        return 1.0 - np.exp(-errors_sq / self._grad_scale)

    def reset(self, init_scale: float = 0.01) -> None:
        """Reset variant to initial state."""
        self.M = np.random.randn(self.input_dim, self.memory_dim) * init_scale
        self.momentum = np.zeros((self.input_dim, self.memory_dim))
        self.embedding_history.clear()
        self._error_history.clear()
        self._surprise_scale = 1.0
        self.update_count = 0
        self.decay_count = 0
        self.total_crystallization = 0.0

        # V2 state reset
        self.W_K = np.random.randn(self.input_dim, self.input_dim) * init_scale
        self.W_V = np.random.randn(self.input_dim, self.memory_dim) * init_scale
        self.W_Q = np.random.randn(self.input_dim, self.input_dim) * init_scale
        self.W_alpha = np.zeros(self.input_dim)
        self.b_alpha = float(np.log(ALPHA_BASE / (1 - ALPHA_BASE)))
        self.W_theta = np.zeros(self.input_dim)
        self.b_theta = float(np.log(THETA_BASE / (1 - THETA_BASE)))
        self.W_eta = np.zeros(self.input_dim)
        self.b_eta = float(np.log(ETA_BASE / (1 - ETA_BASE)))
        self.surprise_momentum = np.zeros((self.input_dim, self.memory_dim))
        self._grad_history.clear()
        self._grad_scale = 1.0
        self._v2_gate_alpha_sum = 0.0
        self._v2_gate_theta_sum = 0.0
        self._v2_gate_eta_sum = 0.0
        self._v2_grad_norm_sum = 0.0
        self._v2_loss_sum = 0.0
        self._v2_call_count = 0
        self._v2_gate_log.clear()

        # Principled bounds state
        self._k_history.clear()
        self._principled_m_cap = ISS_M_NORM_CAP
        self._principled_s_cap = ISS_S_NORM_CAP
        self._caps_alpha = ALPHA_BASE
        self._caps_eta = ETA_BASE

        # Re-init GPU with fresh weights
        if _GPU_AVAILABLE:
            self._init_gpu()
