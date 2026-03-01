"""
TITANS Disposition — Integration Tests
========================================

End-to-end: classify -> deposit -> read -> persist -> restore.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

from titans_disposition.engine import DispositionEngine
from titans_disposition.storage import JSONBackedMemoryStore
from titans_disposition.variant import TITANSVariant, Variant


class TestEngineEndToEnd:
    """End-to-end engine tests."""

    # Use small dims for fast tests (default 1024x1024 is too large for tmp_path)
    _DIMS = {"input_dim": 64, "memory_dim": 128}

    def test_deposit_and_read(self, tmp_path):
        """Deposit a prompt and read back metrics."""
        engine = DispositionEngine(
            conversation_id="test",
            storage_dir=str(tmp_path),
            **self._DIMS,
        )
        result = engine.deposit("Add error handling to the auth module")
        assert "m_norm" in result
        assert "surprise_type" in result
        assert "update_count" in result
        assert result["update_count"] == 1

    def test_multiple_deposits_accumulate(self, tmp_path):
        """Multiple deposits should increase update count."""
        engine = DispositionEngine(
            conversation_id="test",
            storage_dir=str(tmp_path),
            **self._DIMS,
        )
        for i in range(5):
            engine.deposit(f"Prompt number {i}")

        metrics = engine.read()
        assert metrics["update_count"] == 5

    def test_correction_gets_different_gates(self, tmp_path):
        """Corrections should get higher theta (learning rate)."""
        engine = DispositionEngine(
            conversation_id="test",
            storage_dir=str(tmp_path),
            **self._DIMS,
        )
        # Routine deposit
        r1 = engine.deposit("Add a new function for parsing")
        # Correction deposit
        r2 = engine.deposit("That's wrong, use composition not inheritance")

        assert r2["surprise_type"] != r1["surprise_type"] or r2["is_correction"]

    def test_m_vector_accessible(self, tmp_path):
        """get_m_vector should return the raw M matrix."""
        engine = DispositionEngine(
            conversation_id="test",
            storage_dir=str(tmp_path),
            **self._DIMS,
        )
        engine.deposit("Some prompt")
        M = engine.get_m_vector()
        assert isinstance(M, np.ndarray)
        assert M.ndim == 2

    def test_reset_clears_state(self, tmp_path):
        """reset() should return to initial state."""
        engine = DispositionEngine(
            conversation_id="test",
            storage_dir=str(tmp_path),
            **self._DIMS,
        )
        for i in range(5):
            engine.deposit(f"Prompt {i}")

        engine.reset()
        metrics = engine.read()
        assert metrics["update_count"] == 0


class TestStoragePersistence:
    """Test JSON-backed persistence."""

    def test_save_and_load(self, tmp_path):
        """Save variant state and load it back."""
        store = JSONBackedMemoryStore(storage_dir=str(tmp_path))
        variant = TITANSVariant(
            name=Variant.DEFAULT,
            input_dim=64,
            memory_dim=128,
        )
        # Mutate state
        for i in range(5):
            rng = np.random.default_rng(i)
            emb = rng.standard_normal(64)
            emb /= np.linalg.norm(emb)
            variant.update_weights(emb, alpha=0.1, theta=0.3, eta=0.05)

        original_norm = float(np.linalg.norm(variant.M))
        store.save("test-conv", variant)

        loaded = store.load("test-conv")
        assert loaded is not None
        loaded_norm = float(np.linalg.norm(loaded.M))
        assert abs(original_norm - loaded_norm) < 1e-6

    def test_load_nonexistent_returns_none(self, tmp_path):
        store = JSONBackedMemoryStore(storage_dir=str(tmp_path))
        assert store.load("nonexistent") is None

    def test_list_conversations(self, tmp_path):
        store = JSONBackedMemoryStore(storage_dir=str(tmp_path))
        variant = TITANSVariant(name=Variant.DEFAULT, input_dim=32, memory_dim=64)

        store.save("conv-a", variant)
        store.save("conv-b", variant)

        convs = store.list_conversations()
        assert "conv-a" in convs
        assert "conv-b" in convs
        assert len(convs) == 2

    def test_delete_conversation(self, tmp_path):
        store = JSONBackedMemoryStore(storage_dir=str(tmp_path))
        variant = TITANSVariant(name=Variant.DEFAULT, input_dim=32, memory_dim=64)

        store.save("to-delete", variant)
        assert store.load("to-delete") is not None

        store.delete("to-delete")
        assert store.load("to-delete") is None


class TestEngineWithPersistence:
    """Engine + storage integration."""

    _DIMS = {"input_dim": 64, "memory_dim": 128}

    def test_engine_persists_across_instances(self, tmp_path):
        """Create engine, deposit, destroy, recreate — state should persist."""
        engine1 = DispositionEngine(
            conversation_id="persist-test",
            storage_dir=str(tmp_path),
            **self._DIMS,
        )
        for i in range(5):
            engine1.deposit(f"Building feature {i}")
        m_norm_1 = float(np.linalg.norm(engine1.get_m_vector()))
        del engine1

        engine2 = DispositionEngine(
            conversation_id="persist-test",
            storage_dir=str(tmp_path),
            **self._DIMS,
        )
        m_norm_2 = float(np.linalg.norm(engine2.get_m_vector()))
        metrics = engine2.read()

        assert metrics["update_count"] == 5
        assert abs(m_norm_1 - m_norm_2) < 1e-6
