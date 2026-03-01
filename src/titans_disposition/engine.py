"""
DispositionEngine -- the main entry point for TITANS disposition.

Wraps: classify -> compute surprise -> gate -> accumulate -> read.
In-process, no HTTP. Persistence via JSONBackedMemoryStore.
"""

import logging
from typing import Any, Optional

import numpy as np

from titans_disposition.classifier import classify_code_session
from titans_disposition.variant import TITANSVariant, Variant
from titans_disposition.storage import JSONBackedMemoryStore
from titans_disposition.constants import EMBEDDING_DIM

logger = logging.getLogger(__name__)

# Gate priors: maps surprise type (domain + optional _correction suffix)
# to gate overrides. Correction always punches through with high alpha/theta.
GATE_PRIORS: dict[str, dict[str, float]] = {
    "code_routine": {"theta": 0.005, "alpha": 0.01},
    "code_correction": {"theta": 0.07, "alpha": 0.30},
    "code_routine_correction": {"theta": 0.07, "alpha": 0.30},
    "code_substrate_arch": {"theta": 0.04, "alpha": 0.05, "eta": 0.70},
    "code_substrate_arch_correction": {"theta": 0.07, "alpha": 0.30},
    "code_memory_arch": {"theta": 0.04, "alpha": 0.05, "eta": 0.70},
    "code_memory_arch_correction": {"theta": 0.07, "alpha": 0.30},
    "code_voice_arch": {"theta": 0.04, "alpha": 0.05, "eta": 0.70},
    "code_voice_arch_correction": {"theta": 0.07, "alpha": 0.30},
    "code_meta_arch": {"theta": 0.04, "alpha": 0.05, "eta": 0.70},
    "code_meta_arch_correction": {"theta": 0.07, "alpha": 0.30},
    "code_identity": {"theta": 0.03, "alpha": 0.04, "eta": 0.50},
    "code_identity_correction": {"theta": 0.07, "alpha": 0.30},
    "code_pipeline_orch": {"theta": 0.02, "alpha": 0.02, "eta": 0.50},
    "code_pipeline_orch_correction": {"theta": 0.07, "alpha": 0.30},
    "code_exploration": {"theta": 0.01, "alpha": 0.01, "eta": 0.30},
    "code_exploration_correction": {"theta": 0.07, "alpha": 0.30},
}


def _text_to_embedding(text: str, dim: int = EMBEDDING_DIM) -> np.ndarray:
    """
    Convert text to a deterministic pseudo-embedding.

    This is a lightweight hash-based embedding for use when no external
    embedding model is available. For production use, replace with
    a real embedding model (e.g., BGE-large-en-v1.5).

    The hash is deterministic: same text always produces the same vector.
    Vectors are L2-normalized.
    """
    import hashlib
    # Create deterministic seed from text
    text_hash = hashlib.sha256(text.encode("utf-8")).digest()
    # Use the hash as a seed for reproducible random vector
    seed = int.from_bytes(text_hash[:4], "big")
    rng = np.random.RandomState(seed)
    vec = rng.randn(dim).astype(np.float32)
    # L2 normalize
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec


class DispositionEngine:
    """
    Main entry point for TITANS disposition tracking.

    Wraps the full pipeline: classify -> compute surprise -> gate -> accumulate -> read.
    In-process, no HTTP dependencies. Persistence via JSONBackedMemoryStore.

    Usage:
        engine = DispositionEngine("my-session")
        result = engine.deposit("fix the memory leak in the connection pool")
        print(result)  # {'domain': 'memory_arch', 'correction': False, 'surprise': 0.42, ...}

        metrics = engine.read()
        print(metrics)  # {'m_norm': 12.3, 'update_count': 5, ...}
    """

    def __init__(
        self,
        conversation_id: str = "default",
        storage_dir: Optional[str] = None,
        input_dim: int = EMBEDDING_DIM,
        memory_dim: int = 1024,
        embed_fn: Any = None,
    ):
        """
        Initialize the disposition engine.

        Args:
            conversation_id: Unique identifier for this conversation/session
            storage_dir: Directory for JSON state persistence (default: ~/.config/titans-disposition/states/)
            input_dim: Embedding dimension (default: 1024 for BGE-large)
            memory_dim: Memory matrix column dimension
            embed_fn: Optional callable(text: str) -> np.ndarray for text embedding.
                      If None, uses a deterministic hash-based pseudo-embedding.
        """
        self.conversation_id = conversation_id
        self.input_dim = input_dim
        self.memory_dim = memory_dim
        self._embed_fn = embed_fn or (lambda text: _text_to_embedding(text, input_dim))

        # Storage
        self._store = JSONBackedMemoryStore(storage_dir=storage_dir)

        # Load or create variant
        loaded = self._store.load(conversation_id)
        if loaded is not None:
            self._variant = loaded
            logger.info(
                f"Loaded existing state for conversation={conversation_id} "
                f"(update_count={self._variant.update_count})"
            )
        else:
            self._variant = TITANSVariant(
                name=Variant.DEFAULT,
                input_dim=input_dim,
                memory_dim=memory_dim,
            )
            logger.info(f"Created new state for conversation={conversation_id}")

    def deposit(self, text: str) -> dict[str, Any]:
        """
        Process a text input through the full TITANS pipeline.

        Pipeline:
            1. Classify text into domain + correction flag
            2. Convert text to embedding
            3. Compute surprise (V2 associative memory loss)
            4. Compute data-dependent gates
            5. Apply gate priors based on domain/correction
            6. Update weights
            7. Auto-save state
            8. Return metrics

        Args:
            text: Input text (prompt, message, etc.)

        Returns:
            Dict with:
                - domain: Classified domain
                - correction: Whether this is a correction
                - surprise_type: Combined type key (e.g., "code_memory_arch_correction")
                - surprise: Surprise score (0-1)
                - loss: Associative memory loss
                - gates: Dict of alpha, theta, eta (effective values)
                - m_norm: Current M matrix norm
                - update_count: Total updates applied
                - delta_norm: Norm of the weight change from this deposit
        """
        # 1. Classify
        domain, is_correction = classify_code_session(text)

        # Build surprise type key
        surprise_type = f"code_{domain}"
        if is_correction:
            surprise_type += "_correction"

        # 2. Embed
        embedding = self._embed_fn(text)
        if embedding.shape[0] != self.input_dim:
            # Pad or truncate
            if embedding.shape[0] < self.input_dim:
                embedding = np.pad(embedding, (0, self.input_dim - embedding.shape[0]))
            else:
                embedding = embedding[:self.input_dim]

        # 3. Compute surprise (V2 path)
        surprise, gradient = self._variant.compute_surprise_v2(embedding)

        # 4. Compute data-dependent gates
        alpha, theta, eta = self._variant.compute_gates(embedding)

        # 5. Apply gate priors from classification
        priors = GATE_PRIORS.get(surprise_type, {})
        if "alpha" in priors:
            alpha = max(alpha, priors["alpha"])
        if "theta" in priors:
            theta = max(theta, priors["theta"])
        if "eta" in priors:
            eta = priors["eta"]  # eta prior overrides (not max)

        # Compute loss for metrics
        loss = float(self._variant._v2_loss_sum / max(self._variant._v2_call_count, 1))

        # Log gate update
        self._variant.log_gate_update(
            alpha=alpha,
            theta=theta,
            eta_raw=eta,
            eta_effective=eta,
            surprise=surprise,
            grad_norm=float(np.linalg.norm(gradient)),
            loss=loss,
        )

        # 6. Update weights (V2 path)
        delta = self._variant.update_weights_v2(
            gradient=gradient,
            alpha=alpha,
            theta=theta,
            eta=eta,
        )

        delta_norm = float(np.linalg.norm(delta))
        m_norm = float(np.linalg.norm(self._variant.M))

        # 7. Auto-save
        self._store.save(self.conversation_id, self._variant)

        # 8. Return metrics
        return {
            "domain": domain,
            "is_correction": is_correction,
            "surprise_type": surprise_type,
            "surprise": surprise,
            "loss": loss,
            "gates": {
                "alpha": alpha,
                "theta": theta,
                "eta": eta,
            },
            "m_norm": m_norm,
            "update_count": self._variant.update_count,
            "delta_norm": delta_norm,
        }

    def read(self) -> dict[str, Any]:
        """
        Read current M-vector metrics.

        Returns:
            Dict with m_norm, gates, update_count, and full variant stats
        """
        stats = self._variant.get_stats()
        return {
            "conversation_id": self.conversation_id,
            "m_norm": stats["matrix_norm"],
            "update_count": stats["update_count"],
            "total_crystallization": stats["total_crystallization"],
            "surprise_scale": stats["surprise_scale"],
            "v2_metrics": stats.get("v2_metrics"),
        }

    def get_m_vector(self) -> np.ndarray:
        """
        Return the raw M weight matrix.

        Shape: [input_dim, memory_dim]
        """
        return self._variant.M.copy()

    def reset(self) -> None:
        """Reset to initial state and clear persisted data."""
        self._variant.reset()
        self._store.delete(self.conversation_id)
        logger.info(f"Reset state for conversation={self.conversation_id}")

    def save(self) -> None:
        """Explicitly save current state to disk."""
        self._store.save(self.conversation_id, self._variant)

    def load(self) -> bool:
        """
        Explicitly load state from disk.

        Returns:
            True if state was loaded, False if no saved state found
        """
        loaded = self._store.load(self.conversation_id)
        if loaded is not None:
            self._variant = loaded
            return True
        return False
