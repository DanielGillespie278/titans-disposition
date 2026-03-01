# Design Philosophy

This document captures the design principles behind the TITANS Disposition Engine -- the recurring decisions that shaped the architecture and the instincts that guide future development.

---

## M Vector is State, Not Storage

**The M vector is not storage. It is state.**

The difference matters for everything built on top of it. Storage is a notebook -- you write things in, look things up, the notebook doesn't change from having things written in it. State is a personality -- every experience changes the thing itself. You don't "look up" how to respond; the state *is* the accumulated result of every experience.

The M vector doesn't *contain* memories. It *is* the accumulated effect of all memories. There is no "where is memory X stored in M" -- that question doesn't make sense for a recurrent state, the same way "where in your personality is your first day of school stored" doesn't make sense. It's distributed through the whole thing.

**Anyone new to the codebase will instinctively want to treat M like a database.** This documentation exists to prevent that. Don't build retrieval interfaces that misunderstand what M actually is. Retrieval stores (FAISS, vector DBs) are for retrieval. M is the disposition.

---

## Three Papers, Three Contributions

The current TITANS architecture didn't emerge from a single paper. It grew from three distinct intellectual inputs, each contributing a different dimension:

| Paper | Contribution | Dimension |
|-------|-------------|-----------|
| **nGPT** (Nov 2024) | Hypersphere normalization | **Geometry** -- what shape the space should be |
| **TITANS** (Behrouz et al., arXiv 2501.00663) | Surprise-gated encoding | **Attention** -- when to pay attention |
| **Huginn** (arXiv 2502.05171) | Persistent latent recurrence | **Ontology** -- what kind of thing memory fundamentally is |

### nGPT -- The Geometry

Memory representations should live on a unit sphere. On a hypersphere, distances are meaningful, interpolation is well-defined, and things can't drift past the surface. This gives you mathematical *properties* on your memory space, not just contents.

### TITANS -- The Attention

Test-time memory updates with surprise-gated encoding. The system should learn *proportionally to how surprised it is*. Predictable inputs get minimal encoding. Novel inputs get aggressive state updates.

### Huginn -- The Recurrence

The most fundamental piece -- the idea that memory is a *state that updates with each input*, not a store you write to. The formula `s_i = R(e, s_{i-1})` says: the current state is a function of the current input and the previous state. That's recurrence. That's what makes M a personality rather than a notebook.

---

## The Four Instincts (Decision Compass)

These four principles were derived *empirically* from consistent behaviour across 25 months of development. They are not principles decided in advance -- they are principles that were *followed consistently*, even when external pressure pushed elsewhere. That makes them high-trust signals about what the system actually needs.

### North: Geometric Guarantees on Memory

Memory should have mathematical *properties*, not just contents. A sphere has properties -- things can't drift past the surface, distances are meaningful, interpolation is well-defined. This instinct says: don't just store things, store them in a space where the geometry itself prevents pathological behaviour.

**Decision filter**: When someone proposes a memory feature, ask "does this respect or violate the geometry?"

### East: Surprise-Proportional Learning

The system should care more about things that are unexpected. Spend cognitive resources proportionally to novelty. If something is completely predictable, spend near-zero effort encoding it. If something breaks all predictions, go all-in.

**Decision filter**: When someone proposes a learning mechanism, ask "does this learn more from surprising inputs?"

### South: Compression Over Storage

Don't remember *everything* -- distil experiences into compressed dispositions. The M vector doesn't store "the developer said X on Tuesday" -- it stores the *effect* of that statement, compressed into the state.

**Decision filter**: When someone proposes expanding memory capacity, ask "are we storing more, or compressing better?"

### West: Intentional Forgetting

Forgetting isn't failure, it's maintenance. A system that never forgets drowns in its own history. The system should *actively decide* what to release.

**Decision filter**: When someone proposes making memory more persistent, ask "what's the forgetting strategy?"

### Using the Compass

When evaluating any architectural decision:
- Serves **one** direction -- probably aligned with trajectory
- Serves **two or three** -- probably critical path
- Serves **none** -- probably scope creep that wandered in from someone else's vision

---

## Design Decisions

### Why Gradient Gates, Not Direct Writes

The M vector could be updated by simple addition: `M += embed(prompt)`. Instead, we route through gradient gates (alpha, theta, eta, surprise). This adds complexity but provides three critical properties:

1. **Signal-to-noise ratio**: Routine deposits are attenuated (theta=0.005), corrections punch through (theta=0.07). Without gating, 40 routine prompts would overwhelm 1 correction.
2. **Momentum**: The eta gate carries forward recent trajectory, giving the system short-term memory of direction, not just position.
3. **Forgetting**: The alpha gate decays old disposition, preventing the vector from drifting ever further from zero. Without decay, M grows without bound.

### Why Regex Classification, Not LLM Classification

The prompt classifier uses regex patterns, not an LLM call. This is a deliberate tradeoff:

- **Latency**: Regex runs in <1ms. An LLM call takes 200ms-2s. The classifier runs on every prompt.
- **Determinism**: Same input always produces same classification. No temperature variance.
- **Cost**: Zero marginal cost per classification.
- **Accuracy**: ~85-90% for the 8-domain classifier. Good enough to set gate priors. Misclassification is bounded in impact because it only affects gate *priors*, not the gradient signal itself.

The 10-15% misclassification rate is acceptable because gate priors are soft -- they set the initial learning rate, but the gradient signal itself corrects for miscategorisation over time.

### Why JSON Persistence, Not Redis/Postgres

For the standalone open-source package, we chose JSON file persistence over database backends:

- **Zero dependencies**: `pip install titans-disposition` works without Docker, Redis, or Postgres.
- **Inspectable**: Developers can `cat` their disposition state and understand it.
- **Portable**: Copy one file to move your disposition.
- **Sufficient**: At ~1 prompt/minute peak, JSON read/write latency is irrelevant. The bottleneck is the human, not the storage.

For production deployments with high throughput, Redis or Postgres backends can be added without changing the core engine.

### Why Python Classes for Disposition Files, Not YAML/JSON

Disposition weights are encoded as Python class structures with explicit floats, docstrings, and inner classes. Not config files. This is a deliberate application of **prior casting** -- the insight that Python class structures reshape LLM reasoning priors more effectively than equivalent prose or config.

```python
class AttentionAllocation:
    """Where effort goes. Must sum to 1.0."""
    task_alignment = 0.28
    tool_safety = 0.20
    read_before_write = 0.18
```

An LLM reading this Python class interprets the structure, the types, the constraints (sum to 1.0), and the semantic names simultaneously. The same information in YAML would be parsed but not *structured* in the model's reasoning.

---

## What We Didn't Build (Parked Concepts)

These concepts were designed with implementation detail but parked because they weren't needed yet. They're documented here because they represent genuine architectural insights worth revisiting.

### Orthogonal Noise Injection via Gram-Schmidt

**What it does**: Projects noise into directions that are currently underrepresented in M, using Gram-Schmidt orthogonalisation to ensure injected diversity is *exactly* in the collapsing dimensions.

**Why it matters**: The current convergence levers (eta, alpha, theta) all work through *learning dynamics* -- they adjust rates and hope the system finds a diverse equilibrium. Orthogonal noise works through *geometry* -- it directly injects diversity into the directions that are collapsing. These are orthogonal approaches to the convergence problem, which means they compose rather than compete.

**Revisit when**: Pairwise similarity monitoring shows M-vector dimensions collapsing above 0.78.

### Max-Surprise Component

**Formula**: `surprise = 0.5 * mean((p-q)^2) + 0.5 * max((p-q)^2)`

**What it does**: Current system uses scalar MSE for surprise. The max component catches worst-case deviation that mean smooths away -- one dimension completely taken over while the average looks fine.

**Revisit when**: Surprise gate logs show cases where eta should have dropped but didn't because mean MSE was low despite one dimension diverging.

### Explanation Auto-Encoder

**What it does**: Compressed abstract representations of WHY something was remembered, not just WHAT.

**Revisit when**: Enriched decoder work matures and the question becomes "why does M say this?"

### Memory Constitution (Governance)

**What it does**: Formal governance rules for what enters/exits persistent memory.

**Revisit when**: Quality formalisation beyond ad-hoc gates is needed.

---

## Process: Parking Concepts

When parking any concept, write:

```
## PARKED: [Concept Name]
**Date**: [when]
**Reason**: [why -- technical limitation? priority shift? infrastructure not ready?]
**Revisit when**: [specific trigger condition]
**Key insight**: [the one thing worth preserving]
```

Never need a full archaeological dig to rediscover why something was deferred.

---

*This is a living document. Update when new design decisions are made or parked concepts are activated.*
