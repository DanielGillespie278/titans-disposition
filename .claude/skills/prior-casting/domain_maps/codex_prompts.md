# Domain Map: Codex Task Prompts

## Document Type

Task prompts sent to Codex models (Spark, xhigh, Mini) for code generation, analysis, documentation, and structured extraction. These prompts are typically <800 words with constraints at the top.

## High-Risk RLHF Priors for This Domain

### 1. Scope Escape

Codex models are trained to be maximally helpful. A prompt saying "fix the import in line 23" becomes "fix the import and also refactor the function and add error handling." Constraints at the top of the prompt decay as the model generates, especially for long outputs.

**What drift looks like**: Output includes unrequested refactors. "While fixing this, I noticed..." additions. File modifications beyond the specified target.

**Cast target**: Classes that anchor scope to the specific files and lines named in the prompt.

### 2. Identifier Hallucination

The #1 reliability risk. Codex generates plausible-sounding but nonexistent function names, variable names, and file paths. `error_boost` instead of `transcript`. `validate_input()` instead of `check_params()`. The names are structurally correct but referentially wrong.

**What drift looks like**: Code that imports nonexistent modules. Function calls with hallucinated method names. File paths that look real but don't exist.

**Cast target**: Methods that enforce verification of every identifier against the actual codebase, with explicit "never guess a name" constraints.

### 3. Over-Elaboration

Codex reads top-down and tends to elaborate on early sections at the expense of later ones. A prompt asking for 5 things gets 3 elaborated things and 2 rushed things. Long prompts (>800 words) get truncated in practice -- the model stops attending to later content.

**What drift looks like**: First section of output is detailed, last section is thin. Numbered lists where item 1 gets a paragraph and item 5 gets a sentence. Output that addresses only the first half of the prompt.

**Cast target**: Methods that enforce equal coverage across all specified outputs, with explicit "all items, not just the first" constraints.

### 4. Encoding Corruption

Codex models (both Spark and xhigh) can introduce Unicode characters (em-dashes, box-drawing, smart quotes) that break Python files on Windows cp1252. When `ast.parse` fails, Codex "fixes" it by replacing chars with spaces, making things worse.

**What drift looks like**: Python files with `\u2014` (em-dash) instead of `--`. Box-drawing characters in print statements. Smart quotes in string literals. Files that work on Linux but crash on Windows.

**Cast target**: Methods that enforce ASCII-only output in code files, with specific character blacklists.

### 5. Prompt Instruction Amnesia

For multi-step prompts, Codex often executes step 1 correctly and then "forgets" constraints from the preamble by step 3. The CONSTRAINTS block at the top works for immediate next actions but decays.

**What drift looks like**: Step 1 follows all constraints. Step 3 violates the output format. Step 5 ignores the target file restriction.

**Cast target**: Classes that re-anchor constraints as structural elements the model encounters throughout generation, not just at the start.

## Common Soft Instructions in This Domain

- "Write to ONE output file only"
- "Do not modify files outside the specified target"
- "Use exact identifier names from the codebase"
- "Keep output under N lines"
- "ASCII only -- no Unicode in code"
- "Address ALL items, not just the first few"
- "Do not run tests unless explicitly asked"
