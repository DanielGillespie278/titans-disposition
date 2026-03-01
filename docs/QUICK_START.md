# Quick Start Guide

Get TITANS Disposition running with Claude Code in under 10 minutes.

---

## 1. Installation

```bash
pip install titans-disposition
```

Or install from source for development:

```bash
git clone https://github.com/DanielGillespie278/titans-disposition.git
cd titans-disposition
pip install -e ".[dev]"
```

### Requirements

- Python 3.10+
- numpy (installed automatically)
- Optional: `torch>=2.0` for GPU acceleration (`pip install titans-disposition[gpu]`)
- Optional: `httpx>=0.24` for hook HTTP transport (`pip install titans-disposition[hooks]`)

---

## 2. Initialize Storage

```bash
titans init
```

This creates the following in your project directory:

```
.titans/
  m_vector.json       # The disposition state (initially zero vector)
  gate_history.jsonl   # Audit log of every deposit
  config.json          # Gate priors and classifier settings
```

You should see output like:

```
Initialized TITANS disposition store in .titans/
M-vector dimension: 1024
Gate priors: default (developer_v1 profile)
Ready for deposits.
```

---

## 3. Copy the Claude Code Hook

The hook connects Claude Code to the disposition engine. Every prompt you send gets classified, passed through gradient gates, and deposited into the M vector. The current disposition is then injected into Claude's context.

```bash
# Copy the hook to your Claude hooks directory
cp hooks/claude_code.py ~/.claude/hooks/titans_disposition.py
```

If you installed via pip, the hook file is at:

```bash
# Find the installed location
python -c "import titans_disposition; print(titans_disposition.__path__[0])"
# Then copy from there
cp <path>/hooks/claude_code.py ~/.claude/hooks/titans_disposition.py
```

---

## 4. Register in settings.json

Open your Claude Code settings file:

- **macOS/Linux**: `~/.claude/settings.json`
- **Windows**: `%USERPROFILE%\.claude\settings.json`

Add the hook to the `hooks` section:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "type": "command",
        "command": "python ~/.claude/hooks/titans_disposition.py",
        "timeout": 5
      }
    ]
  }
}
```

If you already have hooks configured, add the TITANS hook to the existing `UserPromptSubmit` array.

---

## 5. Verify It Works

Start a new Claude Code session in your project directory. Send any prompt. You should see a `[TITANS DISPOSITION]` block injected into the context:

```
[TITANS DISPOSITION]
Classification: code_routine
Gate values: alpha=0.010, theta=0.005, eta=0.500, surprise=0.032
M-vector norm: 0.047
Session deposits: 1
```

After a few prompts, the M-vector norm should grow as the system accumulates disposition:

```
[TITANS DISPOSITION]
Classification: code_correction
Gate values: alpha=0.300, theta=0.070, eta=0.900, surprise=0.089
M-vector norm: 0.183
Session deposits: 5
```

### Verifying the Settling Curve

After 20-30 prompts in a session, run:

```bash
titans metrics
```

Expected output:

```
Session: 2026-03-01T14:30:00
Deposits: 27
M-vector norm: 2.341
Gradient norm (last 10): 0.028 (settling)
Classification breakdown:
  code_routine:       18 (67%)
  code_correction:     4 (15%)
  code_architectural:  3 (11%)
  code_debug:          2 (7%)
```

The gradient norm should decrease over a session as the system learns your patterns. This is the settling curve -- the signature of genuine disposition formation.

---

## 6. Running the Self-Improvement Loop

The self-improvement loop scores agent output and adjusts disposition weights. See `docs/SELF_IMPROVEMENT_GUIDE.md` for the full walkthrough.

Quick version:

```bash
# If using the /self-improvement skill in Claude Code
/self-improvement
```

Or manually:

```bash
# 1. Run an agent on a task (produces output)
# 2. Score with the Observer
titans observe --input task_output.json --disposition .claude/dispositions/general-purpose.py

# 3. Analyse patterns
titans analyse --cycles .claude/agents/01-capability-loop/memory/cycles/

# 4. Review suggested weight deltas
# 5. Apply if approved
```

---

## 7. Customizing Gate Priors

Gate priors control how much dispositional weight each interaction type carries. Edit `.titans/config.json`:

```json
{
  "gate_priors": {
    "code_routine": {
      "theta": 0.005,
      "alpha": 0.01,
      "eta": 0.5,
      "description": "Normal development flow. Minimal deposit -- volume shouldn't drown salience."
    },
    "code_correction": {
      "theta": 0.07,
      "alpha": 0.30,
      "eta": 0.9,
      "description": "Developer correcting the agent. Always punches through."
    },
    "code_architectural": {
      "theta": 0.04,
      "alpha": 0.05,
      "eta": 0.70,
      "description": "Structural design decisions. Moderate learning, strong momentum."
    },
    "code_debug": {
      "theta": 0.01,
      "alpha": 0.02,
      "eta": 0.3,
      "description": "Debugging sessions. Low deposit -- troubleshooting is transient."
    }
  }
}
```

### Gate Tuning Guidelines

| Gate | Effect of Increasing | When to Increase | When to Decrease |
|------|---------------------|------------------|------------------|
| **theta** (learn) | More signal absorbed per deposit | System isn't responding to corrections | System is too volatile |
| **alpha** (forget) | Old disposition decays faster | System is stuck on outdated patterns | System keeps forgetting useful patterns |
| **eta** (momentum) | Recent trajectory carries forward | Development has clear direction | Direction changes frequently |

### Validating Your Configuration

After adjusting gate priors, replay your conversation history to verify:

```bash
# Extract prompts from Claude Code logs
titans replay extract ~/.claude/projects/ --output prompts.jsonl

# Replay with your new config
titans replay deposit prompts.jsonl --config .titans/config.json

# Check the settling curve
titans replay analyse replay_trajectory.jsonl --window 100
```

If the settling curve doesn't match your lived experience of the project, the weights need further adjustment. The replay is your test suite.

---

## Troubleshooting

### Hook not firing

- Verify `settings.json` is valid JSON (no trailing commas)
- Check that the hook path is correct and the file exists
- Ensure Python is on your PATH
- Try running the hook manually: `python ~/.claude/hooks/titans_disposition.py < test_input.json`

### M-vector norm not growing

- Check that `.titans/` exists in your project directory
- Verify the hook has write permissions to `.titans/m_vector.json`
- Check `gate_history.jsonl` to see if deposits are being recorded

### Classification seems wrong

- Run `titans classify "your prompt text"` to see what the classifier produces
- Check if your prompts match the regex patterns in the classifier
- Consider adding domain-specific patterns to the classifier configuration

### Performance concerns

- The hook runs in <50ms total (classification <1ms, gate computation <5ms, I/O <40ms)
- If you're seeing latency, check that the `.titans/` directory is on fast local storage, not a network drive
- The M-vector JSON file stays small (~50KB for 1024 dimensions)

---

## Next Steps

- Read `docs/DESIGN_PHILOSOPHY.md` to understand the architectural decisions
- Read `docs/SELF_IMPROVEMENT_GUIDE.md` to run the capability loop
- Explore `docs/research/` for the mathematical foundations
- Check `examples/` for usage patterns

---

*TITANS Disposition v0.1.0*
