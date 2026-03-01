# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-01

### Added
- TITANS disposition engine with gradient-gated M-vector accumulation
- 8-domain prompt classifier with correction detection
- V2 paper-aligned learning (Behrouz et al. 2501.00663)
- Stability gates: 2-step, N-step windowed spectral radius, eta bisection
- ISS-derived principled norm bounds from convergence proof
- JSON-backed persistence (replaces Redis for standalone use)
- Claude Code UserPromptSubmit hook with session tracking
- Self-improvement loop: Observer, Analyst, Validator, Librarian agents
- Three disposition baselines: general-purpose, explore, plan
- Prior-casting skill for behavioral constraint encoding
- Research docs: Inverse Reward Design proof, Convergence analysis
- Examples: basic_usage.py, replay_history.py
