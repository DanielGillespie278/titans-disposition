"""
TITANS Memory State Module

Implements the learnable memory state that applies computed gates (alpha, theta, eta)
to update memory using the documented formula:

    M_new = (1 - alpha) * M_old + theta * update + eta * momentum

Architecture:
    1. MemoryState class holds learnable memory vector
    2. apply_gates() implements the TITANS formula
    3. Memory state is per-conversation (keyed by conversation_id)
    4. MemoryStateStore provides in-memory state management
"""

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class MemoryState:
    """
    Learnable memory state for TITANS attention augmentation.

    The memory vector M evolves over time based on surprise-gated learning:
    - alpha (alpha_forget): How much old memory to retain (0 = keep all, 1 = forget all)
    - theta (theta_learn): How much new information to incorporate
    - eta (eta_momentum): How much to use the momentum term

    Formula: M_new = (1 - alpha) * M_old + theta * update + eta * momentum

    Attributes:
        M: The learnable memory vector
        prev_update: Previous update for momentum calculation
        dim: Dimensionality of the memory vector
        version: Number of updates applied
        conversation_id: Key for persistence (optional)
    """

    M: np.ndarray
    prev_update: np.ndarray
    dim: int
    version: int = 0
    conversation_id: str | None = None
    _last_gates: dict[str, float] = field(default_factory=dict)

    @classmethod
    def create(cls, dim: int, conversation_id: str | None = None) -> "MemoryState":
        """
        Factory method to create a new memory state.

        Args:
            dim: Dimensionality of the memory vector
            conversation_id: Optional key for persistence

        Returns:
            Initialized MemoryState with zero vectors
        """
        return cls(
            M=np.zeros(dim, dtype=np.float32),
            prev_update=np.zeros(dim, dtype=np.float32),
            dim=dim,
            version=0,
            conversation_id=conversation_id,
        )

    def apply_gates(
        self,
        update: np.ndarray,
        gates: dict[str, float],
    ) -> np.ndarray:
        """
        Apply TITANS gates to update memory state.

        This is the core learning operation.
        The gates (alpha, theta, eta) come from surprise-modulated adaptation.

        Args:
            update: New information vector
            gates: Dict containing:
                - alpha_forget: Forgetting rate (0-1)
                - theta_learn: Learning rate (0-1)
                - eta_momentum: Momentum coefficient (0-1)

        Returns:
            Updated memory vector M_new

        Formula:
            M_new = (1 - alpha) * M_old + theta * update + eta * prev_update
        """
        # Extract gate values with defaults
        alpha = gates.get("alpha_forget", 0.1)
        theta = gates.get("theta_learn", 0.3)
        eta = gates.get("eta_momentum", 0.1)

        # Identity protection: clamp alpha to prevent catastrophic forgetting.
        # Without this, a single API call with alpha=1.0 erases M entirely.
        #
        # Maturity-gated relaxation: mature M vectors tolerate higher forgetting.
        # Linear ramp 0.30 -> 0.55 over updates 5-15.
        ALPHA_FLOOR = 0.30
        ALPHA_CEIL = 0.55
        RAMP_START = 5
        RAMP_END = 15
        progress = max(0.0, min(1.0, (self.version - RAMP_START) / (RAMP_END - RAMP_START)))
        max_alpha = ALPHA_FLOOR + progress * (ALPHA_CEIL - ALPHA_FLOOR)
        if alpha > max_alpha:
            logger.warning(
                f"[IDENTITY-GUARD] alpha_forget={alpha:.3f} exceeds maturity-gated max "
                f"{max_alpha:.3f} (version={self.version}); clamping"
            )
            alpha = max_alpha

        # Ensure update has correct shape
        if update.shape != self.M.shape:
            if update.size > 0:
                # Resize by taking first dim elements or padding with zeros
                if update.size >= self.dim:
                    update = update.flatten()[:self.dim]
                else:
                    update = np.pad(update.flatten(), (0, self.dim - update.size))
            else:
                update = np.zeros(self.dim, dtype=np.float32)

        # Apply the TITANS formula
        # M_new = (1 - alpha) * M_old + theta * update + eta * momentum
        M_new = (1 - alpha) * self.M + theta * update + eta * self.prev_update

        # NaN/Inf guard: if M_new is corrupted, preserve old state
        if not np.all(np.isfinite(M_new)):
            logger.warning(
                f"[SURPRISE-GUARD] M_new contains NaN/Inf after gate application "
                f"(alpha={alpha:.3f}, theta={theta:.3f}, eta={eta:.3f}). "
                f"Preserving previous M (version={self.version})."
            )
            M_new = self.M.copy()

        # Store for next iteration
        self.M = M_new.astype(np.float32)
        self.prev_update = update.astype(np.float32)
        self.version += 1

        # Preserve surprise + gradient_norm for downstream consumers
        surprise = gates.get("surprise", 0.0)
        gradient_norm = gates.get("gradient_norm", 0.0)
        self._last_gates = {
            "alpha_forget": alpha,
            "theta_learn": theta,
            "eta_momentum": eta,
            "surprise": surprise,
            "gradient_norm": gradient_norm,
        }

        logger.debug(
            f"MemoryState.apply_gates: version={self.version}, "
            f"alpha={alpha:.3f}, theta={theta:.3f}, eta={eta:.3f}, "
            f"M_norm={np.linalg.norm(self.M):.4f}"
        )

        return self.M

    # =========================================================================
    # Convenience Methods (Stable Interface)
    # These decouple consumers from internal dict structure.
    # =========================================================================

    def get_surprise_score(self) -> float:
        """Get current surprise level from gates.

        Stable interface - decouples consumers from internal dict structure.
        Returns 0.0 if no gates applied yet or surprise not in gates.
        """
        if not self._last_gates:
            return 0.0
        return self._last_gates.get("surprise", 0.0)

    def get_momentum(self) -> float:
        """Get current momentum (eta) from gates.

        Stable interface - decouples consumers from internal dict structure.
        """
        if not self._last_gates:
            return 0.0
        return self._last_gates.get("eta_momentum", 0.0)

    def get_forget_rate(self) -> float:
        """Get current forget rate (alpha) from gates.

        Stable interface - decouples consumers from internal dict structure.
        """
        if not self._last_gates:
            return 0.0
        return self._last_gates.get("alpha_forget", 0.0)

    def get_learn_rate(self) -> float:
        """Get current learn rate (theta) from gates.

        Stable interface - decouples consumers from internal dict structure.
        """
        if not self._last_gates:
            return 0.0
        return self._last_gates.get("theta_learn", 0.0)

    # =========================================================================

    def get_metrics(self) -> dict[str, Any]:
        """
        Get current memory state metrics for observability.

        Returns:
            Dict with memory statistics
        """
        return {
            "version": self.version,
            "dim": self.dim,
            "M_norm": float(np.linalg.norm(self.M)),
            "M_mean": float(np.mean(self.M)),
            "M_std": float(np.std(self.M)),
            "prev_update_norm": float(np.linalg.norm(self.prev_update)),
            "last_gates": self._last_gates,
            "conversation_id": self.conversation_id,
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for persistence."""
        return {
            "M": self.M.tolist(),
            "prev_update": self.prev_update.tolist(),
            "dim": self.dim,
            "version": self.version,
            "conversation_id": self.conversation_id,
            "last_gates": self._last_gates,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryState":
        """Deserialize from dict."""
        return cls(
            M=np.array(data["M"], dtype=np.float32),
            prev_update=np.array(data["prev_update"], dtype=np.float32),
            dim=data["dim"],
            version=data.get("version", 0),
            conversation_id=data.get("conversation_id"),
            _last_gates=data.get("last_gates", {}),
        )


class MemoryStateStore:
    """
    In-memory store for memory states (keyed by conversation_id).
    """

    def __init__(self, default_dim: int = 512):
        self._states: dict[str, MemoryState] = {}
        self._default_dim = default_dim
        self._active_id: str | None = None

    def set_active(self, conversation_id: str) -> None:
        """Track which conversation is currently active."""
        self._active_id = conversation_id

    def get_active_id(self) -> str | None:
        """Return the active conversation ID, or None."""
        return self._active_id

    def seed_from_active(self, new_conversation_id: str) -> bool:
        """Seed a new conversation's M from the current active conversation.

        Used when a new session starts -- preserves M vector continuity
        instead of starting from zeros.
        """
        if not self._active_id or self._active_id not in self._states:
            return False
        if new_conversation_id == self._active_id:
            return False

        source = self._states[self._active_id]
        new_state = MemoryState.create(dim=source.dim, conversation_id=new_conversation_id)
        new_state.M = source.M.copy()
        new_state.prev_update = source.prev_update.copy()
        new_state.version = source.version
        self._states[new_conversation_id] = new_state
        self._active_id = new_conversation_id
        logger.info(
            f"[TITANS-SEED] Seeded {new_conversation_id} from {source.conversation_id} "
            f"(version={source.version}, M_norm={float(np.linalg.norm(source.M)):.4f})"
        )
        return True

    def get_or_create(
        self,
        conversation_id: str,
        dim: int | None = None,
    ) -> MemoryState:
        """Get existing memory state or create new one."""
        if conversation_id not in self._states:
            self._states[conversation_id] = MemoryState.create(
                dim=dim or self._default_dim,
                conversation_id=conversation_id,
            )
            logger.info(
                f"Created new MemoryState for conversation={conversation_id}"
            )
        return self._states[conversation_id]

    def get(self, conversation_id: str) -> MemoryState | None:
        """Get memory state if exists."""
        return self._states.get(conversation_id)

    def clear(self, conversation_id: str) -> bool:
        """Clear memory state for conversation."""
        if conversation_id in self._states:
            del self._states[conversation_id]
            return True
        return False

    def list_conversations(self) -> list:
        """List all conversation IDs with memory state."""
        return list(self._states.keys())

    def get_all_metrics(self) -> dict[str, dict[str, Any]]:
        """Get metrics for all memory states."""
        return {
            conv_id: state.get_metrics()
            for conv_id, state in self._states.items()
        }


# Global store singleton
_memory_store: MemoryStateStore | None = None


def get_memory_store(default_dim: int = 512) -> MemoryStateStore:
    """Get or create the global memory state store."""
    global _memory_store
    if _memory_store is None:
        _memory_store = MemoryStateStore(default_dim=default_dim)
    return _memory_store
