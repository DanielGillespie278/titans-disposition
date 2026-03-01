# TITANS Disposition Roadmap

Planned features and release timeline. We follow semver -- patch releases for additions, minor versions for new capabilities, no breaking changes without a major bump.

---

## v0.1.x -- Foundation

### v0.1.1 -- Hadamard Codebook Classifier
Upgrade the classifier from regex-only to Hadamard-coded orthogonal targets. 8x8 orthogonal category vectors with 3.2x better domain separation than one-hot encoding. Pure numpy, <1ms inference.

### v0.1.2 -- M-Vector Probe Tools
Interpretability toolkit. Embed text anchors, compute cosine similarity against the M-vector, and produce a human-readable report of what the disposition encodes. Includes settling curve tracking across sessions.

### v0.1.3 -- Session Momentum Classifier
3-tier classification with session momentum carry. Short ambiguous prompts ("fix it") inherit the most recent non-routine domain when momentum is fresh (2-turn entry, 5-minute decay). Momentum breakers for off-domain context switches.

---

## v0.2.x -- Behavioral Intelligence

### v0.2.0 -- Behavioral Pattern Store
Surprise-gated behavioral calibrations. Patterns enter from corrections, observations, or surprise spikes. 3-layer identity boundary defense (keyword + regex + poison detection). Candidate/active lifecycle with auto-promotion after 3 reinforcements. Contradiction decay with supersession lineage tracking.

### v0.2.1 -- Temporal Context Vector
3-channel temporal awareness: conversation pace, focus trajectory, and drift rate. Adds time-awareness to disposition -- the agent can distinguish a focused sprint from scattered exploration.

### v0.2.2 -- Presence Gate Modulator
Engagement-aware theta scaling. Active coding boosts learning rate by 1.5x. Idle periods drop it to 0.5x. Surprise-driven boosts on novel spikes. The disposition adapts to your engagement level, not just your words.

---

## v0.3.x -- Platform Ecosystem

### v0.3.0 -- MCP Server Mode
Expose disposition as MCP tools: `titans_deposit`, `titans_read`, `titans_status`, `titans_classify`. Any MCP-compatible agent (Claude Desktop, custom agents) gets persistent disposition without a hook.

### v0.3.1 -- Edge Deployment (Pi / ARM64)
Run disposition tracking on a Raspberry Pi or any edge device. HTTP bridge for memory queries, pattern storage, and temporal context. Tested on Pi 5 ARM64.

### v0.3.2 -- Settling Curve Visualization
CLI tool that produces settling curve charts from disposition history. Gradient norm convergence, regime detection, correction persistence. `titans curve` gives you the visual proof that your agent is learning.

---

## v0.4.x -- Community

### v0.4.0 -- Team Disposition
Shared M-vector across multiple agents or collaborators. Correct one agent, all agents in the team feel it. Federation protocol for syncing disposition state across instances.

### v0.4.1 -- VS Code Extension
Status bar integration showing M-norm, current domain, and correction rate. Click for the settling curve.

### v0.4.2 -- Community Weight Profiles
Repository of validated disposition profiles: backend Python, frontend React, data science, DevOps. Each includes tuned gate priors and the validation data proving they work. Contribute yours.

### v0.4.3 -- Cursor / Copilot / Windsurf Hooks
Integration hooks for other AI coding agents. Same disposition engine, different front-end.

### v0.4.4 -- Codex Support
Native integration with OpenAI Codex agents. Disposition tracking for Codex-orchestrated tasks -- each Codex worker inherits the team's M-vector and contributes corrections back. Works with both `codex exec` CLI and the Codex API.

---

## Contributing

The most impactful contributions right now:

1. **Weight profiles** -- run the engine against your own development history and submit validated gate priors
2. **Classifier patterns** -- better regex rules for the 8-domain taxonomy, especially edge cases
3. **Editor hooks** -- integration with Cursor, Copilot, Windsurf, or other agents
4. **Improvement cycle reports** -- run `/self-improvement` on real projects and share what you learn

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.
