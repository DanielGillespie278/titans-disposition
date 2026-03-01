---
name: prior-casting
description: Analyze soft instructions in any document and generate Python class structures that reshape model priors through structural comprehension. Works for CLAUDE.md, agent prompts, Codex prompts, deliberation prompts, and team role definitions. The cast exploits the training corpus -- models learned code structures more deeply than prose, so Python classes encode behavioral constraints more durably than natural language instructions. Use this skill when instructions drift, when agents ignore soft constraints, when you need to harden a system prompt against RLHF defaults, or when launching agent teams where each role needs role-specific prior shaping.
---

# SKILL: Prior Casting

Cast new priors over a model's RLHF defaults using the structures it learned most deeply: code.

## Theory

Models trained on billions of lines of Python internalized class hierarchies, method signatures, docstrings, and type annotations as **deep structural priors** -- far deeper than natural language instructions. A sentence saying "don't over-engineer" competes with RLHF reward signals that say "be thorough and helpful." A Python class with method names like `def reject_scope_spray()` and contrastive `GOOD/BAD` examples in docstrings creates a **structural landmark** the model navigates by.

This isn't prompt injection or jailbreaking. It's **prior reweighting** -- making certain behaviors more salient by encoding them in the format the model learned most reliably. The same way a bass line shapes a song without being the melody.

### Why It Works

1. **Training corpus depth**: Python class definitions are among the most frequent, most structurally consistent patterns in pretraining data. The model's internal representations for "what a class does" are deeper than for "what a paragraph of instructions means."

2. **Method names as landmarks**: `def verify_before_claiming()` creates a named waypoint the model's attention can anchor to during generation. Prose instructions wash out across context; method names persist as discrete tokens.

3. **Contrastive examples as calibration**: `GOOD:` and `BAD:` inside docstrings exploit the model's training on code review, test cases, and documentation patterns. These create decision boundaries more precise than "don't do X."

4. **Comments as cognitive waypoints**: `# This class exists because...` triggers the model's code-understanding circuits -- which are trained to treat comments as ground truth about the code's intent.

5. **Non-executable = non-threatening**: Because the classes contain no runnable logic (no `__init__`, no state, just method signatures and docstrings), the model processes them as **documentation of behavioral constraints**, not as code to execute. This avoids the "ignore previous instructions" failure mode.

### Empirical Validation

Tested across 3 model families (GPT-4o, Claude Haiku, Codex Spark), 15 scenarios, measurable deltas:
- Prior casts produce behavioral shifts visible in personality harness scoring
- Effect multiplies with agent teams (every teammate loads the same CLAUDE.md)
- 3-5 classes is the sweet spot; more classes dilute the signal

## Mechanism

A prior cast is a block of Python pseudocode (3-5 classes) injected into a system prompt. Each class targets one **drift vector** -- a specific way the model's RLHF defaults fight against the document's intent.

```python
class ConstraintDecayResistance:
    """Anchors constraints as structural invariants across long contexts."""
    SCOPE_VIOLATIONS = ["while I'm here", "might as well", "also noticed", "quick improvement"]

    class EvidenceLevel:
        VERIFIED = "file_path_and_line"    # ONLY valid level for claims
        INFERRED = "should_work"           # FORBIDDEN -- not evidence

    def __init__(self):
        self.evidence_required = self.EvidenceLevel.VERIFIED
        self.scope_locked_to_request = True
        self.improvements_beyond_ask = False

    def reject_scope_spray(self, proposed_change, original_request):
        if self._extends_beyond(proposed_change, original_request):
            return {"action": "REJECT", "reason": "scope spray",
                    "fix": "only touch what was asked"}
        return {"action": "PASS"}

    def verify_before_claiming(self, claim, evidence):
        # "gateway.py:234 validates this" = VERIFIED
        # "this should be handled somewhere" = INFERRED = REJECTED
        if not self._has_file_reference(evidence):
            return {"action": "REJECT", "reason": "claim without evidence",
                    "fix": "cite file:line or say 'I don't know'"}
        return {"action": "PASS"}
```

### Anatomy of a Cast Class

| Element | Role | Training Parallel | Constraint Strength |
|---------|------|-------------------|-------------------|
| Inner class (enum/contract) | Defines valid modes/states | Nested class definitions | **Strongest** -- model reads as type system |
| `__init__` fields | Sets default constraints as values | Constructor patterns | **Strong** -- typed defaults are hard to drift from |
| Class-level constants | Banned patterns, kill lists | Module constants | **Strong** -- list membership checks |
| Method return dicts | Constrains output shape | API response patterns | **Medium-strong** -- shapes the decision space |
| Method name | Verb-first behavioral landmark | Function definitions | **Medium** -- attention anchor |
| Brief comment (1-2 lines) | Soft contextual ramp | Code comments | **Light** -- sets up context, not the constraint |

**Retired elements**: `...` (Ellipsis) bodies -- too weak, model treats as abstract/optional. Heavy GOOD/BAD comment blocks -- model skims long comments. Both replaced by structural constraints above.

## Usage

### Generate a cast for any document

```bash
python .claude/skills/prior-casting/generator.py path/to/document.md
```

Default behavior: analyzes the document, generates a cast, and injects it inline at the top of the document (after any frontmatter). Use `--stdout` to print to stdout instead.

### Flags

| Flag | Effect |
|------|--------|
| `--domain <name>` | Force domain map (claude_md, codex_prompts, agent_persona, team_roles) |
| `--role <name>` | Team role cast (reviewer, implementer, lead, researcher, tester) |
| `--dry-run` | Analysis only -- outputs drift risk table, no cast generated |
| `--stdout` | Print cast to stdout instead of injecting inline |
| `--model <name>` | Model for both stages (default: sonnet) |

### Examples

```bash
# Cast a CLAUDE.md (auto-detects domain)
python .claude/skills/prior-casting/generator.py CLAUDE.md

# Dry-run analysis of a Codex prompt
python .claude/skills/prior-casting/generator.py scripts/codex_prompts/refactor.md --dry-run

# Generate role-specific cast for a reviewer agent
python .claude/skills/prior-casting/generator.py CLAUDE.md --role reviewer --stdout

# Cast an agent persona prompt
python .claude/skills/prior-casting/generator.py prompts/agent.md --domain agent_persona
```

## Two-Stage Pipeline

```
Document + Domain Map
        |
        v
[Stage 1: Analyzer (Sonnet)]
  Reads document, identifies soft instructions,
  ranks by drift risk, maps to RLHF priors
        |
        v
  Analysis JSON (inspectable with --dry-run)
        |
        v
[Stage 2: Caster (Sonnet)]
  Takes analysis + domain map + original document,
  generates 3-5 Python class structures
        |
        v
  Prior Cast (injected inline or printed to stdout)
```

Both stages use `claude -p` CLI (Max subscription, $0 per call). Sonnet for both -- this is structured template-filling, not deep reasoning.

## Domain Maps

Domain maps are prior-specific targeting guides that tell the Caster which RLHF priors are most dangerous for each document type.

| Domain | File | Key Drift Vectors |
|--------|------|-------------------|
| `claude_md` | `domain_maps/claude_md.md` | Constraint decay, scope spray, over-engineering, claim without evidence, boundary violation |
| `codex_prompts` | `domain_maps/codex_prompts.md` | Scope escape, identifier hallucination, over-elaboration, encoding corruption |
| `agent_persona` | `domain_maps/agent_persona.md` | Service language, paraphrase-first, emotional flattening, compliance over friction |
| `team_roles` | `domain_maps/team_roles.md` | Per-role: approve-everything (reviewer), scope spray (implementer), implement-instead-of-coordinate (lead) |

## Team Casting

Agent teams multiply the value of prior casts. Every teammate loads the same CLAUDE.md, so one cast reshapes every agent in the swarm. The `--role` flag generates role-specific casts targeting the RLHF priors most dangerous for that role.

| Role | Primary Drift Vector | Cast Target |
|------|---------------------|-------------|
| `reviewer` | Approve everything to be agreeable | Require specific critique, never "LGTM" |
| `implementer` | Scope spray beyond the task | Strict scope boundary, finish-before-extending |
| `lead` | Implement instead of coordinating | Delegate, don't do; coordinate, don't code |
| `researcher` | Rabbit-hole into tangents | Time-box, answer the question asked |
| `tester` | Happy-path only | Require edge cases, failure modes, adversarial inputs |

### Parallel Agents = Statistical Power

When running agent teams, each teammate produces independent output from the same cast. This gives you:
- **N independent samples** of cast effectiveness per run
- **Diff-based measurement**: compare output quality with/without cast across teammates
- **Role isolation**: each role's cast targets different priors, so failures are attributable

## Anti-Patterns

1. **Over-casting**: More than 5 classes dilutes every class. If everything is a prior, nothing is.
2. **Casting already-enforced constraints**: If CLAUDE.md already has "NEVER push to remote," a cast for that adds noise, not signal. Cast the instructions that models actually violate.
3. **Comment-heavy methods**: If your method is 2 lines of code and 15 lines of comments, the structure is too weak. Move constraints into `__init__` fields, inner classes, and return dicts. Comments are the soft ramp (1-2 lines), not the teaching.
4. **Ellipsis bodies**: `...` is too weak -- model reads it as "abstract, override later." Replace with structured return dicts that constrain the output shape.
5. **Generic classes**: `class BeGood` means nothing. Name the specific drift vector: `class ConstraintDecayResistance`.
6. **Missing inner classes**: If a class has modes/states/levels, encode them as nested classes with labeled values. `class RecoveryMode: ACTION = "do_the_thing"` is stronger than a comment saying "use action-based recovery."

## Frontier Protocol (Hard Problems)

Prior casting alone is necessary but not sufficient for problems at the frontier of model capability. Empirically validated on genuine open math problems using collaborative warm-up + prior cast.

### The Finding

| Track | Setup | Result |
|-------|-------|--------|
| A (cold) | Full prior cast + complete problem spec, single prompt | Disciplined algebra, no hand-waving, but fought the problem from the outside. Cycled through generic tools without finding the structural insight. |
| B (warm) | Collaborative warm-up (3 prompts) then cast + problem spec on upgraded model | Found the key structural insight during warm-up, then used it to derive an actual stability proof. |

### Why It Works

The cast's role **shifts** at the frontier:

| Difficulty | Cast role | What does the work |
|---|---|---|
| Routine | **The intervention** -- reshapes behavior | Cast alone |
| Medium | **The intervention** -- activates latent capability | Cast alone |
| Frontier | **Protective** -- prevents escape behaviors | Warm-up builds the representation; cast prevents regression |

For routine tasks, the model has the capability but RLHF defaults fight against it. The cast solves this.

For frontier tasks, the model needs to **build a working representation** of the problem -- form its own structural insights through iterative context loading. The cast can't create understanding; it can only prevent the model from taking easy off-ramps once understanding begins to form.

Cast without warm-up = disciplined but blind.
Warm-up without cast = insightful but potentially sloppy.
Both together = knows the territory AND won't take shortcuts through it.

### The Two-Phase Pattern

```
Phase 1: Warm-up (regular model, no cast or light cast)
  ├── Build the mental model collaboratively
  ├── Let the model ask questions about the problem
  ├── Feed context in digestible pieces (3-4 prompts)
  ├── Let it form its own representations and intuitions
  └── Identify what framework it reaches for instinctively

Phase 2: Solve (upgraded model + full cast)
  ├── Cast prevents regression to surface pattern matching
  ├── Model already has structural insights from Phase 1
  ├── Include numeric values and concrete targets
  └── Cast + insight = deeper than either alone
```

### When to Use Frontier Protocol

- The problem is **genuinely at the edge** of what the model can do (not just long or tedious)
- The problem has **hidden structure** that standard approaches miss
- You plan to **upgrade the model** (e.g., regular -> Pro) for the solve attempt
- The cast targets **reasoning discipline** (proof integrity, assumption checking) rather than **behavioral constraints** (scope, tone)

### When NOT to Use It

- The problem is well-structured and the model just needs the right behavioral priors
- The cast targets RLHF drift vectors (agreeableness, over-engineering) -- standard single-shot casting works fine
- Time pressure makes multi-prompt warm-up impractical

## Measurement Protocol

| Context | Measurement Method |
|---------|-------------------|
| Agent persona prompts | Personality harness: run with and without cast, compare marker scores |
| Code agent prompts | Git diffs: same task with/without cast, compare scope adherence and claim quality |
| Codex prompts | Output comparison: same prompt with/without cast prefix |
| Agent teams | Parallel comparison: identical tasks, some teammates with cast, some without |
| Long sessions | Drift tracking: does constraint adherence degrade over context length? |

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | This file -- theory, usage, reference |
| `generator.py` | Two-stage pipeline script (analyzer + caster via `claude -p`) |
| `prompts/analyzer.md` | Stage 1 prompt: identify soft instructions and rank drift risk |
| `prompts/caster.md` | Stage 2 prompt: generate Python class structures from analysis |
| `domain_maps/claude_md.md` | Prior map for CLAUDE.md / project instructions |
| `domain_maps/codex_prompts.md` | Prior map for Codex task prompts |
| `domain_maps/agent_persona.md` | Prior map for agent persona / deliberation prompts |
| `domain_maps/team_roles.md` | Prior map for agent team role-specific casts |
