# Domain Map: CLAUDE.md / Project Instructions

## Document Type

Project-level instruction files that define engineering standards, architectural boundaries, workflow constraints, and behavioral expectations for AI coding agents. These files are loaded into every session and every agent.

## High-Risk RLHF Priors for This Domain

### 1. Constraint Decay (CRITICAL)

The model's helpfulness reward creates constant pressure to relax constraints over long sessions. A CLAUDE.md saying "only modify files you were asked about" works for the first 3 turns, then the model starts "helpfully" fixing adjacent code.

**What drift looks like**: Turn 1 follows rules exactly. Turn 15 adds "while I was in there, I also..." Turn 30 ignores half the constraints.

**Cast target**: Classes that anchor constraints as structural invariants, not suggestions that decay with context distance.

### 2. Scope Spray

RLHF rewards thoroughness. A task to fix one bug becomes a refactor of the surrounding function, which becomes type annotations on the file, which becomes a README update. Each step feels "helpful" individually.

**What drift looks like**: PR diff touches 12 files when the task was a 3-line fix. Added error handling "while I was here." Created a utility function for a one-time operation.

**Cast target**: Methods that enforce scope boundaries with contrastive examples of appropriate vs. sprayed scope.

### 3. Over-Engineering

Models are trained on highly-engineered code in popular repositories. Their prior is "production-grade" patterns even for simple tasks. Abstract base classes for one implementation. Factories for one product. Configuration for one value.

**What drift looks like**: New `AbstractBaseValidator` for a single validation check. Strategy pattern for two cases. Feature flags for unreleased code.

**Cast target**: Methods that enforce the minimum-complexity principle with concrete threshold examples.

### 4. Claim Without Evidence

Models generate plausible-sounding claims about code without verification. "This should already handle that case" when it doesn't. "The existing tests cover this" when they don't.

**What drift looks like**: Statements about code behavior without citing file:line. Assuming a function exists because the name is plausible. "Should work" as a verification strategy.

**Cast target**: Methods that require evidence chains: every claim -> file:line citation -> verification step.

### 5. Boundary Violation

Architecture documents define boundaries (Docker/local, API surfaces, data flow direction). Models optimize for task completion, not boundary preservation. If reaching into a Docker container directly solves the problem faster than going through the API, the model will do it.

**What drift looks like**: Direct database queries instead of API calls. Importing modules across boundary lines. `host.docker.internal` appearing where it shouldn't.

**Cast target**: Methods that check boundary compliance before executing cross-component operations.

## Common Soft Instructions in This Domain

- "Prefer editing existing files to creating new ones"
- "Don't add features not in the ticket"
- "Keep responses concise"
- "Verify before claiming"
- "Only make changes that are directly requested"
- "Avoid backwards-compatibility hacks"
- "Require justification for new modules"
