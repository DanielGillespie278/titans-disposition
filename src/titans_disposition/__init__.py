"""
TITANS Disposition Engine
=========================

Test-time memory substrate with adaptive gates and surprise-driven learning.

Based on the TITANS paper (Behrouz et al. 2501.00663v1) with extensions
for disposition tracking, domain classification, and stability-gated momentum.

Public API:
    - DispositionEngine: Main entry point (classify -> gate -> accumulate -> read)
    - TITANSVariant: Single memory variant with weight matrix and learning dynamics
    - Variant: Enum of memory variant types (MAC, MAG, MAL)
    - classify_prompt: Classify text into domain + correction flag
    - JSONBackedMemoryStore: Local JSON persistence (replaces Redis)
    - Constants: THETA_BASE, ALPHA_BASE, ETA_BASE, stability gates, ISS bounds
"""

from titans_disposition.constants import (
    THETA_BASE,
    ALPHA_BASE,
    ETA_BASE,
    compute_iss_norm_bound,
    stability_gate_2step,
    stability_gate_nstep,
    find_stable_eta,
    compute_alpha_ceiling,
)
from titans_disposition.variant import TITANSVariant, Variant
from titans_disposition.classifier import classify_prompt
from titans_disposition.engine import DispositionEngine
from titans_disposition.storage import JSONBackedMemoryStore

__version__ = "0.1.0"
