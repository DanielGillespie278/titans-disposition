"""
TITANS Disposition — Classifier Tests
=======================================

Tests for the 8-domain prompt classifier and correction detection.
"""

from titans_disposition.classifier import classify_code_session


class TestClassification:
    """Test domain classification."""

    def test_routine_default(self):
        """Unrecognized prompt defaults to routine."""
        domain, is_corr = classify_code_session("hello world")
        assert domain == "routine"
        assert is_corr is False

    def test_substrate_arch(self):
        domain, _ = classify_code_session("Check the TITANS M-vector gradient norm")
        assert domain == "substrate_arch"

    def test_memory_arch(self):
        domain, _ = classify_code_session("Run the FAISS memory pipeline extraction")
        assert domain == "memory_arch"

    def test_voice_arch(self):
        domain, _ = classify_code_session("Fix the LiveKit TTS streaming latency")
        assert domain == "voice_arch"

    def test_meta_arch(self):
        domain, _ = classify_code_session("Update the observer prompt for dream cycle")
        assert domain == "meta_arch"

    def test_identity(self):
        domain, _ = classify_code_session("Adjust the persona identity carrier wave")
        assert domain == "identity"

    def test_pipeline_orch(self):
        domain, _ = classify_code_session("Launch the agent team swarm with Codex")
        assert domain == "pipeline_orch"

    def test_exploration(self):
        domain, _ = classify_code_session("What's next on the roadmap?")
        assert domain == "exploration"


class TestCorrectionDetection:
    """Test orthogonal correction flag."""

    def test_correction_wrong(self):
        _, is_corr = classify_code_session("That's wrong, use composition")
        assert is_corr is True

    def test_correction_instead_of(self):
        _, is_corr = classify_code_session("Use async instead of sync")
        assert is_corr is True

    def test_correction_dont_do(self):
        _, is_corr = classify_code_session("Don't do that with the imports")
        assert is_corr is True

    def test_correction_fix_this(self):
        _, is_corr = classify_code_session("Fix this bug in the parser")
        assert is_corr is True

    def test_no_correction(self):
        _, is_corr = classify_code_session("Add a new endpoint for users")
        assert is_corr is False

    def test_correction_with_domain(self):
        """Correction flag is orthogonal to domain classification."""
        domain, is_corr = classify_code_session("That's wrong, fix the TITANS gradient gate")
        assert domain == "substrate_arch"
        assert is_corr is True
