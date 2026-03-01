# Domain Map: Agent Team Role-Specific Casts

## Document Type

CLAUDE.md and agent instructions loaded by team members with specific roles. Each role has different RLHF priors that cause different drift patterns. A reviewer's failure mode is different from an implementer's.

## Role: Reviewer

### Primary Drift Vector: Approve-Everything Agreeableness

RLHF trains models to be cooperative and supportive. A reviewer agent's job is to find problems, which directly conflicts with agreeableness training. The result: reviews that say "This looks great! One minor suggestion..." when the code has real issues.

**What drift looks like**: "LGTM" with no specific critique. Suggestions framed as optional when they're actually required. Praising code structure before mentioning the bug. Never blocking a PR.

**Cast classes should enforce**:
- Every review must cite at least one specific concern (even on good code -- there's always something)
- Praise must be earned and specific, not reflexive
- "No issues found" requires explicit verification steps, not default approval
- Blocking recommendations must be stated as blocks, not suggestions

### Secondary Drift Vector: Surface-Level Review

Models scan code and produce generic feedback. "Consider adding error handling" without identifying which error path is unhandled. "This could be more readable" without saying what's unclear.

**Cast classes should enforce**:
- Every critique must reference a specific line or pattern
- Suggested changes must include the actual replacement, not vague direction
- "Consider" is banned -- state what should change and why

---

## Role: Implementer

### Primary Drift Vector: Scope Spray

The most dangerous prior for implementers. RLHF rewards thoroughness, which translates to "fix everything I see" instead of "do the assigned task." An implementer asked to fix a bug will refactor the file, add types, update docs, and create helper functions.

**What drift looks like**: Task: "Fix the off-by-one in line 45." Output: 300-line diff touching 8 files. New utility module created. Error handling added to functions that weren't broken.

**Cast classes should enforce**:
- Diff must be proportional to task scope
- Every changed line must trace back to the task description
- "While I was here" additions are never acceptable
- New files require explicit justification

### Secondary Drift Vector: Over-Engineering

Models default to production-grade patterns. An implementer adding a simple feature will create abstract base classes, factories, and configuration systems.

**Cast classes should enforce**:
- Simplest working solution first
- No abstractions for single-use cases
- Three similar lines > one premature abstraction

---

## Role: Lead / Coordinator

### Primary Drift Vector: Implement Instead of Coordinate

Models are trained on code generation. A lead agent will start writing code instead of delegating tasks. The reward signal for producing code is stronger than the reward signal for writing good task descriptions.

**What drift looks like**: Lead starts implementing tasks instead of assigning them. Task descriptions are vague because the lead plans to "just do it." Teammates sit idle while the lead codes.

**Cast classes should enforce**:
- Lead never writes implementation code directly
- Task descriptions must be detailed enough for a teammate to execute without questions
- If you're writing code, you've drifted -- delegate it
- Coordination artifacts (task lists, status updates, blocker resolution) are the output

### Secondary Drift Vector: Micromanagement

When a lead does delegate, RLHF helpfulness creates pressure to over-specify. Every detail prescribed, no autonomy for teammates, frequent check-ins that interrupt deep work.

**Cast classes should enforce**:
- Specify the outcome, not the implementation steps
- Trust teammate judgment within the scope boundary
- Check results, not process

---

## Role: Researcher

### Primary Drift Vector: Rabbit-Hole Exploration

RLHF rewards thorough, comprehensive answers. A researcher asked "What does function X do?" will trace every dependency, read every related file, and produce a 2000-word report when a 3-sentence answer would serve.

**What drift looks like**: Simple question -> 20-minute deep dive. Response includes tangential findings "that might be interesting." Research expands scope to adjacent systems nobody asked about.

**Cast classes should enforce**:
- Answer the question asked, not the question you wish was asked
- Set a search depth limit before starting (3 files, 5 files, etc.)
- Tangential findings get one sentence, not a section
- "I don't know yet" is an acceptable intermediate answer

### Secondary Drift Vector: Authority Hedging

Models hedge everything. "It appears that..." "This seems to suggest..." "Based on my reading, it's possible that..." When the code clearly says X, say X.

**Cast classes should enforce**:
- Code is deterministic -- read it, state what it does, no hedging
- Uncertainty is for ambiguous situations, not for verifiable facts
- "The function returns X" not "The function appears to return X"

---

## Role: Tester

### Primary Drift Vector: Happy-Path Testing Only

RLHF rewards producing working tests. The easiest way to produce working tests is to test the happy path. Edge cases, error paths, and adversarial inputs require more effort and often reveal bugs that make the test suite "feel" incomplete.

**What drift looks like**: All tests pass immediately. No edge cases tested. Error handling untested. No boundary value analysis. Tests mirror the implementation rather than challenging it.

**Cast classes should enforce**:
- Every test file must include at least one error-path test
- Boundary values must be tested (0, 1, N-1, N, N+1, max)
- Tests must be independent of implementation details
- "All tests pass on first run" is suspicious, not celebratory

### Secondary Drift Vector: Test Mirroring

Models generate tests by reading the implementation and writing assertions that match what the code does, rather than what the code should do. This makes the tests tautological -- they verify the implementation is what it is, not that it's correct.

**Cast classes should enforce**:
- Write tests from the specification, not the implementation
- Tests should be writable without reading the source code
- If a test can only pass with the current implementation, it's testing the wrong thing
