"""
Stability gates for TITANS disposition engine.

Runtime checks that prevent M-vector divergence under momentum.
Extracted from the convergence proof (ISS analysis).
"""
from titans_disposition.constants import (
    stability_gate_2step,
    stability_gate_nstep,
    find_stable_eta,
    compute_iss_norm_bound,
    compute_alpha_ceiling,
    verify_lyapunov_condition,
    compute_iss_m_norm_bound,
    compute_iss_s_norm_bound,
    compute_step_size_governor,
)

__all__ = [
    "stability_gate_2step",
    "stability_gate_nstep",
    "find_stable_eta",
    "compute_iss_norm_bound",
    "compute_alpha_ceiling",
    "verify_lyapunov_condition",
    "compute_iss_m_norm_bound",
    "compute_iss_s_norm_bound",
    "compute_step_size_governor",
]
