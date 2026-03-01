#!/usr/bin/env python3
"""
GLOBAL UserPromptSubmit hook - Bidirectional TITANS disposition tracking.

WRITE: Classifies each prompt into a coarse surprise type and deposits it
       into the local M vector via DispositionEngine.deposit().
       Source channel = "claude_code" for provenance tracking.

READ:  Queries DispositionEngine.read() for the current M vector state.

ACCUMULATE: Tracks rolling domain distribution per session + cross-session
            trajectory. Detects pivots via compound rare-domain spike (>8pp).

GUIDE: Translates disposition numbers into behavioral guidance for Claude.

CONVERGE: Compares per-conversation M state with aggregate to detect
          cross-channel disposition divergence.

Output: [TITANS M-VECTOR] block + [SESSION DISPOSITION] + [DOMAIN TRAJECTORY]
        + optional [CROSS-CHANNEL] injected into Claude's context.

Stdout -> injected as <user-prompt-submit-hook> context visible to Claude.
Stderr -> terminal feedback for the user.

Setup:
  pip install titans-disposition
  Register this hook in .claude/settings.json under hooks.UserPromptSubmit
"""
import sys
import json
import logging
import re
import time
from datetime import date, timedelta
from pathlib import Path

# Configure logging
LOG_FILE = Path.home() / ".cache" / "titans-disposition" / "hooks.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("hooks.global.disposition")

# Try importing the disposition engine
try:
    from titans_disposition import DispositionEngine, classify_prompt as td_classify
    _ENGINE = DispositionEngine()
except ImportError:
    _ENGINE = None
    td_classify = None

# Configuration
QUERY_TIMEOUT = 3.0  # seconds (fits within 5s hook timeout)
SNAPSHOT_FILE = Path.home() / ".cache" / "titans-disposition" / "m_vector_snapshot.json"
CONVERSATION_ID = "claude-code"

# Delta thresholds -- below these, report STABLE
NORM_DELTA_THRESHOLD = 0.001
ENTROPY_DELTA_THRESHOLD = 0.001

# --- Session Accumulation (Feature 1) ---
SESSION_FILE = Path.home() / ".cache" / "titans-disposition" / "session_domains.json"
SESSION_TIMEOUT = 7200  # 2 hours -- reset session after this gap

# --- Cross-Session Trajectory (Feature 3) ---
TRAJECTORY_FILE = Path.home() / ".cache" / "titans-disposition" / "domain_trajectory.json"
TRAJECTORY_DAYS = 7  # keep last 7 days

# --- Domain Baselines (from validated weight profile) ---
DOMAIN_BASELINES = {
    "routine": 31.7,
    "pipeline_orch": 21.2,
    "exploration": 16.6,
    "meta_arch": 15.8,
    "voice_arch": 7.3,
    "identity": 2.7,
    "memory_arch": 2.3,
    "substrate_arch": 1.9,
}
RARE_DOMAINS = {d for d, pct in DOMAIN_BASELINES.items() if pct < 5.0}
PIVOT_SPIKE_THRESHOLD = 8.0  # pp above baseline -- compound rare-domain spike

# --- Cross-Channel Convergence (Feature 4) ---
CROSS_CHANNEL_DIVERGENCE = 0.5  # M_norm delta to report

# --- Prompt Classification (V4) ---
# 8 domains + correction flag (orthogonal). V4 three-tier classifier:
#   Tier 1 = text keyword/regex (<1ms) -- authoritative
#   Tier 2 = session momentum carry (for short/ambiguous prompts)
#   Tier 3 = default routine
#
# Domain: routine, memory_arch, voice_arch, substrate_arch,
#         meta_arch, pipeline_orch, exploration, identity
# Correction: orthogonal binary flag (user correcting Claude)

# Correction signals: user correcting Claude
_CORRECTION_PATTERNS = re.compile(
    r"\b(?:"
    r"wrong|that'?s wrong|"
    r"instead of|use .+ instead|"
    r"don'?t do|stop doing|"
    r"fix this|fix the|"
    r"that'?s not (?:right|correct|what)|"
    r"should be .+|should have|"
    r"not what i (?:asked|meant|wanted)|"
    r"you missed|you forgot|"
    r"incorrect|"
    r"actually[, ]+(?:it|the|that|you|we|i)|"
    r"no[, ]+(?:that|it|the|this|you|we) "
    r")\b",
    re.IGNORECASE,
)

# Domain text rules -- priority-ordered, first match wins.
# V4: expanded with natural-language triggers.
_DOMAIN_TEXT_RULES = [
    ("substrate_arch", re.compile(
        r"\b(?:TITANS|M.?vector|gradient.?(?:gate|norm)|disposition|"
        r"substrate|surprise.?(?:signal|gate|calculator|classif|type)|"
        r"alpha.?forget|theta.?learn|eta.?momentum|"
        r"Hadamard|inner.?loop|pred.?head|"
        r"M.?norm|M.?probe|probe.?(?:script|m|result|snapshot)|"
        r"semantic.?(?:anchor|probe|decode)|nearest.?neighbor|"
        r"cosine.?sim|learning.?rate|gate.?(?:value|profile|s look|s respond)|"
        r"code.?channel|voice.?channel|cross.?channel|"
        r"M.?state|federation|complementary|redundant|"
        r"convergence|divergen|aggregate.?(?:M|norm)|"
        r"per.?type.?eta|momentum.?(?:track|decay|carry)|"
        r"hysteresis|tau.?(?:high|low)|dual.?threshold|"
        r"embedding.?(?:space|dim)|BGE|"
        r"gradient.?health|starved|classifier|classif)\b", re.IGNORECASE)),
    ("memory_arch", re.compile(
        r"\b(?:transplant|capsule|deposit|FAISS|"
        r"memory.?(?:pipeline|system|substrate|retriev|tree|garden|hook)|"
        r"corpus|extraction|bridge.?dream|"
        r"episodic|consolidat(?:e|ion)|"
        r"memory.?(?:store|query|embed|search|prune)|"
        r"capsule.?(?:stats|cleanup|ranking)|"
        r"staleness|salience.?decay|"
        r"rem.?sleep|recall|"
        r"conversation.?(?:id|history))\b", re.IGNORECASE)),
    ("voice_arch", re.compile(
        r"\b(?:voice.?(?:router|agent|pipeline|stack|model|DNA)|"
        r"TTS|STT|VAD|LiveKit|Deepgram|Whisper|"
        r"Edge.?TTS|streaming.?voice|"
        r"voice.?skeleton|"
        r"speech.?(?:speed|mode|timing)|"
        r"proactive.?(?:speech|engagement)|"
        r"speak.?gate|local.?voice)\b", re.IGNORECASE)),
    ("meta_arch", re.compile(
        r"\b(?:backroom|deliberat(?:e|ion)|observer.?(?:prompt|rewrite)|"
        r"cognitive.?ensemble|sentinel|heartbeat|"
        r"hook|self.?(?:direct|evolv|modif|observ)|"
        r"prior.?cast|dream.?cycle|speech.?floor|"
        r"CLAUDE\.md|doc.?(?:verify|coherence)|"
        r"anti.?pattern|pattern.?heal|"
        r"dream.?(?:agent|packet|report)|"
        r"self.?improve|improvement.?ledger|"
        r"overnight.?train|LoRA|QLoRA|adapter)\b", re.IGNORECASE)),
    ("identity", re.compile(
        r"\b(?:persona(?:lity)?|identity|"
        r"soul|skeleton|costume|SAGE|REBEL|PRIME|"
        r"facilitat(?:e|ion)|tone|tonal|carrier.?wave|"
        r"identity.?(?:drift|fidelity|measure|interferom)|"
        r"I1|I2|I3|I4|dolphin|sycophancy|"
        r"voice.?DNA|behavioral.?(?:pattern|marker)|"
        r"correction.?(?:record|log))\b", re.IGNORECASE)),
    ("pipeline_orch", re.compile(
        r"\b(?:swarm|agent.?team|orchestrat|"
        r"docker|redis|rebuild|restart|"
        r"wire|wiring|endpoint|API.?(?:route|endpoint)|"
        r"deploy|container|docker.?compose|"
        r"curl|API.?(?:quick|reference|call)|"
        r"health.?(?:check|aggregate))\b", re.IGNORECASE)),
    ("exploration", re.compile(
        r"\b(?:what.?s.?next|what.?should|where.?do|"
        r"vision|north.?star|strategy|roadmap|"
        r"playground|orb|presence|frontend|"
        r"dashboard|UI|"
        r"research.?(?:prompt|question|paper)|"
        r"deep.?research|arXiv|"
        r"concept.?archaeology|parked.?concept)\b", re.IGNORECASE)),
]

# --- Session Momentum (V4) ---
# Hysteresis-inspired carry: if recent non-routine turns were classified to
# a specific domain, short/ambiguous prompts inherit that domain. Decays
# with time gap (not turn count) so a break resets momentum.
#
# High threshold to enter: need 2+ recent non-routine turns in same domain.
# Low threshold to exit: 5min without a turn or explicit routine keyword.
MOMENTUM_FILE = Path.home() / ".cache" / "titans-disposition" / "domain_momentum.json"
MOMENTUM_ENTER_COUNT = 2     # consecutive non-routine turns to establish momentum
MOMENTUM_DECAY_SECONDS = 300  # 5 min -- stale momentum resets to routine
MOMENTUM_SHORT_THRESHOLD = 80  # prompts shorter than this are "ambiguous"

# Momentum breakers: terms that are unambiguously off-domain for ANY technical
# streak. If these appear in a short prompt, momentum carry is suppressed even
# if the prompt would otherwise be "ambiguous." Two categories:
#
# 1. Off-domain topics: general non-technical content
# 2. Code-action verbs: "fix", "add", "rename" -- these are task directives that
#    indicate a genuine domain shift to routine work, not a continuation of
#    an architectural discussion.
_MOMENTUM_BREAKERS = re.compile(
    r"\b(?:"
    # Off-domain topics
    r"weather|lunch|dinner|coffee|"
    r"break|grocery|shopping|pizza|playlist|"
    # Code-action verbs (task directives = routine, not continuation)
    r"fix (?:the |a |this )|add (?:a |the )|rename |remove (?:the |that )|"
    r"delete (?:the |that )|commit (?:that|this|it)|"
    r"run the tests|format the code|clean up|"
    r"docstring|unused import|update the version"
    r")\b",
    re.IGNORECASE,
)


def load_momentum() -> dict:
    """Load domain momentum state."""
    try:
        if MOMENTUM_FILE.exists():
            data = json.loads(MOMENTUM_FILE.read_text(encoding="utf-8"))
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {"domain": None, "streak": 0, "last_update": 0.0}


def save_momentum(momentum: dict) -> None:
    try:
        MOMENTUM_FILE.parent.mkdir(parents=True, exist_ok=True)
        MOMENTUM_FILE.write_text(
            json.dumps(momentum, separators=(",", ":")), encoding="utf-8"
        )
    except OSError:
        pass


def update_momentum(momentum: dict, domain: str) -> dict:
    """Update momentum state after a classification.

    If the domain matches the current momentum domain, increment streak.
    If it's a different non-routine domain, reset streak to 1.
    If it's routine (from regex), don't update -- momentum may override.
    """
    now = time.time()

    # Check staleness -- if too long since last turn, reset
    if now - momentum.get("last_update", 0) > MOMENTUM_DECAY_SECONDS:
        momentum = {"domain": None, "streak": 0, "last_update": now}

    if domain == "routine":
        # Routine doesn't build momentum, but doesn't break it either
        # (the carry will apply on the next call to classify_with_momentum)
        momentum["last_update"] = now
        return momentum

    if domain == momentum.get("domain"):
        momentum["streak"] = momentum.get("streak", 0) + 1
    else:
        momentum["domain"] = domain
        momentum["streak"] = 1

    momentum["last_update"] = now
    return momentum


def classify_prompt(text: str) -> tuple[str, bool]:
    """
    Classify prompt into domain + correction flag (V4).

    Returns (surprise_type, is_correction):
      surprise_type: "code_{domain}" for GATE_PRIORS lookup
      is_correction: orthogonal correction flag

    V4: Three tiers:
      1. Text keyword/regex match (<1ms) -- authoritative, always wins
      2. Session momentum carry -- for short/ambiguous prompts when recent
         turns established a non-routine domain (hysteresis decay)
      3. Default routine -- genuinely unclassifiable prompts
    """
    is_correction = bool(_CORRECTION_PATTERNS.search(text))

    # Tier 1: keyword match -- authoritative
    for domain, pattern in _DOMAIN_TEXT_RULES:
        if pattern.search(text):
            return f"code_{domain}", is_correction

    # Tier 2: session momentum carry for short/ambiguous prompts
    # Suppressed if prompt contains a momentum breaker (unambiguous domain shift)
    stripped = text.strip()
    if len(stripped) < MOMENTUM_SHORT_THRESHOLD and not _MOMENTUM_BREAKERS.search(stripped):
        try:
            momentum = load_momentum()
            time_since = time.time() - momentum.get("last_update", 0)
            has_domain = momentum.get("domain") is not None
            has_streak = momentum.get("streak", 0) >= MOMENTUM_ENTER_COUNT
            is_fresh = time_since < MOMENTUM_DECAY_SECONDS

            if has_domain and has_streak and is_fresh:
                return f"code_{momentum['domain']}", is_correction
        except Exception:
            pass

    # Tier 3: default
    return "code_routine", is_correction


def load_snapshot() -> dict | None:
    """Load previous M vector snapshot from cache."""
    try:
        if SNAPSHOT_FILE.exists():
            data = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
            return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.debug("Failed to load M vector snapshot: %s", exc)
    return None


def save_snapshot(snapshot: dict) -> None:
    """Save current M vector snapshot to cache."""
    try:
        SNAPSHOT_FILE.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_FILE.write_text(
            json.dumps(snapshot, separators=(",", ":")),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.debug("Failed to save M vector snapshot: %s", exc)


def deposit_to_engine(prompt_text: str, surprise_type: str, is_correction: bool = False) -> dict | None:
    """
    WRITE: Deposit classified prompt into local DispositionEngine.

    Returns a dict with gate response or None on failure.
    """
    if _ENGINE is None:
        return None

    try:
        result = _ENGINE.deposit(
            text=prompt_text[:2000],
            conversation_id=CONVERSATION_ID,
            surprise_type=surprise_type,
            is_correction=is_correction,
            source_channel="claude_code",
        )
        return result
    except Exception as exc:
        logger.warning("DispositionEngine deposit error: %s", exc)
        return None


def read_from_engine() -> dict | None:
    """
    READ: Query DispositionEngine for current M vector metrics.

    Returns per-conversation metrics dict or None on failure.
    """
    if _ENGINE is None:
        return None

    try:
        result = _ENGINE.read(conversation_id=CONVERSATION_ID)
        return result
    except Exception as exc:
        logger.warning("DispositionEngine read error: %s", exc)
        return None


def read_aggregate_from_engine() -> dict | None:
    """
    READ: Query DispositionEngine for aggregate M state across all channels.

    Returns aggregate metrics dict or None on failure.
    """
    if _ENGINE is None:
        return None

    try:
        result = _ENGINE.read()  # no conversation_id = aggregate
        return result
    except Exception as exc:
        logger.debug("DispositionEngine aggregate read error: %s", exc)
        return None


# --- Feature 1: Session Accumulation ---

def load_session() -> dict:
    """Load or initialize session domain accumulator."""
    try:
        if SESSION_FILE.exists():
            data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
            # Reset if session timed out
            if time.time() - data.get("last_update", 0) > SESSION_TIMEOUT:
                return _new_session()
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return _new_session()


def _new_session() -> dict:
    return {
        "last_update": time.time(),
        "prompt_count": 0,
        "correction_count": 0,
        "domains": {},
    }


def update_session(session: dict, domain: str, is_correction: bool) -> dict:
    """Increment domain count and correction count."""
    session["prompt_count"] += 1
    session["domains"][domain] = session["domains"].get(domain, 0) + 1
    if is_correction:
        session["correction_count"] += 1
    session["last_update"] = time.time()
    return session


def save_session(session: dict) -> None:
    try:
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        SESSION_FILE.write_text(
            json.dumps(session, separators=(",", ":")), encoding="utf-8"
        )
    except OSError as exc:
        logger.debug("Failed to save session: %s", exc)


def compute_session_distribution(session: dict) -> dict[str, float]:
    """Compute domain distribution as percentages."""
    total = session.get("prompt_count", 0)
    if total == 0:
        return {}
    return {
        d: round(count / total * 100, 1)
        for d, count in sorted(
            session.get("domains", {}).items(),
            key=lambda x: x[1],
            reverse=True,
        )
    }


def detect_pivot(distribution: dict[str, float]) -> tuple[bool, float, list[str]]:
    """
    Compound rare-domain spike test.
    Returns (is_pivot, spike_sum_pp, top_spiking_domains).
    """
    spike_sum = 0.0
    spiking = []
    for domain in RARE_DOMAINS:
        pct = distribution.get(domain, 0.0)
        baseline = DOMAIN_BASELINES.get(domain, 0.0)
        delta = pct - baseline
        if delta > 0:
            spike_sum += delta
            spiking.append(f"{domain}+{delta:.1f}pp")
    return spike_sum >= PIVOT_SPIKE_THRESHOLD, spike_sum, spiking


# --- Feature 2: Disposition-Aware Context Injection ---

def format_disposition_guidance(
    distribution: dict[str, float],
    correction_rate: float,
    is_pivot: bool,
    prompt_count: int,
) -> str:
    """
    Translate session numbers into behavioral guidance.
    Returns a compact [SESSION DISPOSITION] block.
    """
    if prompt_count < 3:
        return "[SESSION DISPOSITION] early session (n<3), insufficient data"

    observations = []

    # Pivot detection -- highest priority
    if is_pivot:
        observations.append("PIVOT detected: shifting into rare domain territory, stay adaptive")

    # Dominant rare domain -- deep-dive signal
    for domain in RARE_DOMAINS:
        pct = distribution.get(domain, 0.0)
        if pct >= 20.0:
            observations.append(f"deep-dive mode ({domain} at {pct:.0f}%): go deeper not broader")
            break

    # Correction density
    if correction_rate >= 0.30:
        observations.append(f"high correction rate ({correction_rate:.0%}): verify before claiming, slow down")
    elif correction_rate >= 0.15:
        observations.append(f"moderate corrections ({correction_rate:.0%}): double-check assumptions")

    # Routine-heavy session
    routine_pct = distribution.get("routine", 0.0)
    if routine_pct >= 70.0 and not is_pivot:
        observations.append("routine session: execution mode, be concise")

    if not observations:
        # Find dominant domain for a neutral read
        top = next(iter(distribution), "routine")
        observations.append(f"steady state: primary domain {top} ({distribution.get(top, 0):.0f}%)")

    return "[SESSION DISPOSITION] " + ". ".join(observations[:2])


# --- Feature 3: Cross-Session Trajectory ---

def load_trajectory() -> dict:
    """Load daily domain trajectory (last N days)."""
    try:
        if TRAJECTORY_FILE.exists():
            data = json.loads(TRAJECTORY_FILE.read_text(encoding="utf-8"))
            # Prune entries older than TRAJECTORY_DAYS
            cutoff = (date.today() - timedelta(days=TRAJECTORY_DAYS)).isoformat()
            return {k: v for k, v in data.items() if k >= cutoff}
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def update_trajectory(trajectory: dict, domain: str) -> dict:
    """Increment today's domain count in trajectory."""
    today = date.today().isoformat()
    if today not in trajectory:
        trajectory[today] = {}
    trajectory[today][domain] = trajectory[today].get(domain, 0) + 1
    return trajectory


def save_trajectory(trajectory: dict) -> None:
    try:
        TRAJECTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        TRAJECTORY_FILE.write_text(
            json.dumps(trajectory, separators=(",", ":")), encoding="utf-8"
        )
    except OSError as exc:
        logger.debug("Failed to save trajectory: %s", exc)


def format_trajectory(trajectory: dict) -> str | None:
    """
    Format [DOMAIN TRAJECTORY] block from recent days.
    Returns None if no history.
    """
    if not trajectory:
        return None

    # Aggregate last 3 days (or whatever is available)
    recent_dates = sorted(trajectory.keys(), reverse=True)[:3]
    if not recent_dates:
        return None

    merged = {}
    total = 0
    for d in recent_dates:
        for domain, count in trajectory[d].items():
            merged[domain] = merged.get(domain, 0) + count
            total += count

    if total == 0:
        return None

    # Top 3 domains by percentage
    ranked = sorted(merged.items(), key=lambda x: x[1], reverse=True)[:3]
    parts = [f"{domain} {count/total*100:.0f}%" for domain, count in ranked]
    days_label = f"last {len(recent_dates)}d"

    return f"[DOMAIN TRAJECTORY] {days_label}: {', '.join(parts)} (n={total})"


# --- Feature 4: Cross-Channel Convergence ---

def format_cross_channel(
    aggregate: dict | None, per_conv: dict | None
) -> str | None:
    """
    Compare aggregate M state with per-conversation.
    Returns [CROSS-CHANNEL] block if divergent, None otherwise.
    """
    if not aggregate or not per_conv:
        return None

    agg_norm = aggregate.get("coherence_score", 0.0)
    conv_norm = per_conv.get("coherence_score", 0.0)
    delta = abs(agg_norm - conv_norm)

    if delta < CROSS_CHANNEL_DIVERGENCE:
        return None

    direction = "ahead" if agg_norm > conv_norm else "behind"
    return (
        f"[CROSS-CHANNEL] aggregate M_norm={agg_norm:.4f} "
        f"vs code-only={conv_norm:.4f} (delta={delta:.4f}, aggregate {direction}). "
        f"Other channels have shifted disposition."
    )


def format_m_vector_block(
    metrics: dict | None,
    prev: dict | None,
    write_result: dict | None,
    surprise_type: str,
) -> str:
    """
    Format the [TITANS M-VECTOR] block for stdout injection.

    Compact format: write result + disposition fingerprint + gates + delta.
    """
    lines = ["[TITANS M-VECTOR]"]

    # Line 1: Write result (what the deposit looked like)
    if write_result and write_result.get("success"):
        lines.append(
            f"  write: type={surprise_type}  "
            f"surprise={write_result.get('surprise', 0):.3f}  "
            f"grad_norm={write_result.get('gradient_norm', 0):.4f}  "
            f"alpha={write_result.get('alpha_forget', 0):.3f}  "
            f"theta={write_result.get('theta_learn', 0):.4f}  "
            f"eta={write_result.get('eta_momentum', 0):.3f}"
        )
    elif write_result:
        lines.append(f"  write: FAILED (success=false)")
    else:
        lines.append(f"  write: SKIPPED (engine unavailable)")

    # Extract current values from read
    entropy = metrics.get("attention_entropy", 0.0) if metrics else 0.0
    utilization = metrics.get("memory_utilization", 0.0) if metrics else 0.0
    coherence = metrics.get("coherence_score", 0.0) if metrics else 0.0
    mem_size = metrics.get("memory_size", 0) if metrics else 0

    # Line 2: Disposition fingerprint
    lines.append(
        f"  M_norm={coherence:.4f}  entropy={entropy:.4f}  "
        f"utilization={utilization:.4f}  dim={mem_size}"
    )

    # Line 3: Adaptive gates from read (if available)
    gates = metrics.get("surprise_gates") if metrics else None
    if gates:
        lines.append(
            f"  gates: alpha={gates.get('alpha_forget', 0):.3f}  "
            f"theta={gates.get('theta_learn', 0):.3f}  "
            f"eta={gates.get('eta_momentum', 0):.3f}  "
            f"surprise={gates.get('surprise', 0):.4f}"
        )

    # Line 4: Delta from previous snapshot
    if prev is None:
        lines.append("  delta: FIRST READ (no previous snapshot)")
    elif metrics is None:
        lines.append("  delta: UNKNOWN (read failed)")
    else:
        prev_coherence = prev.get("coherence_score", 0.0)
        prev_entropy = prev.get("attention_entropy", 0.0)

        d_norm = abs(coherence - prev_coherence)
        d_entropy = abs(entropy - prev_entropy)

        changed = (
            d_norm > NORM_DELTA_THRESHOLD
            or d_entropy > ENTROPY_DELTA_THRESHOLD
        )

        if changed:
            lines.append(
                f"  delta: CHANGED  "
                f"dM_norm={coherence - prev_coherence:+.4f}  "
                f"dEntropy={entropy - prev_entropy:+.4f}"
            )
        else:
            lines.append("  delta: STABLE (no disposition drift)")

    return "\n".join(lines)


def main():
    start = time.monotonic()

    # Read hook input from stdin (required by UserPromptSubmit protocol)
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        return

    if not isinstance(hook_input, dict):
        return

    # Extract prompt text for classification + write
    prompt_text = hook_input.get("prompt", "")
    if not prompt_text:
        return

    # Classify prompt into domain + correction flag (<1ms)
    surprise_type, is_correction = classify_prompt(prompt_text)
    # Extract bare domain name (strip "code_" prefix)
    domain = surprise_type.removeprefix("code_")

    # --- V4: Update domain momentum (after classify, before session) ---
    try:
        momentum = load_momentum()
        momentum = update_momentum(momentum, domain)
        save_momentum(momentum)
    except Exception as exc:
        logger.debug("Momentum update error: %s", exc)

    # --- Feature 1: Session Accumulation ---
    try:
        session = load_session()
        session = update_session(session, domain, is_correction)
        save_session(session)
        distribution = compute_session_distribution(session)
        is_pivot, spike_sum, spiking = detect_pivot(distribution)
        prompt_count = session.get("prompt_count", 0)
        correction_rate = (
            session["correction_count"] / prompt_count if prompt_count > 0 else 0.0
        )
    except Exception as exc:
        logger.debug("Session accumulation error: %s", exc)
        distribution = {}
        is_pivot, spike_sum, spiking = False, 0.0, []
        prompt_count, correction_rate = 0, 0.0

    # --- Feature 3: Cross-Session Trajectory ---
    try:
        trajectory = load_trajectory()
        trajectory = update_trajectory(trajectory, domain)
        save_trajectory(trajectory)
    except Exception as exc:
        logger.debug("Trajectory error: %s", exc)
        trajectory = {}

    # WRITE: Deposit into M vector via DispositionEngine
    # Failure does NOT prevent read
    write_result = deposit_to_engine(prompt_text, surprise_type, is_correction)
    if write_result:
        logger.debug(
            "Disposition deposit: type=%s surprise=%.3f",
            surprise_type,
            write_result.get("surprise", 0),
        )

    # READ: Query per-conversation metrics + aggregate
    metrics = read_from_engine()
    aggregate = read_aggregate_from_engine()

    # Load previous snapshot for delta computation
    prev = load_snapshot()

    # Format the core M-vector block (existing)
    block = format_m_vector_block(metrics, prev, write_result, surprise_type)

    # --- Feature 1: Session distribution line ---
    try:
        if distribution and prompt_count >= 2:
            top3 = list(distribution.items())[:3]
            dist_str = ", ".join(f"{d}={p:.0f}%" for d, p in top3)
            pivot_tag = f"  PIVOT(+{spike_sum:.1f}pp: {','.join(spiking)})" if is_pivot else ""
            block += f"\n  session: n={prompt_count} corr={correction_rate:.0%} [{dist_str}]{pivot_tag}"
    except Exception as exc:
        logger.debug("Session format error: %s", exc)

    # --- Feature 2: Disposition Guidance ---
    try:
        guidance = format_disposition_guidance(
            distribution, correction_rate, is_pivot, prompt_count
        )
        block += f"\n{guidance}"
    except Exception as exc:
        logger.debug("Disposition guidance error: %s", exc)

    # --- Feature 3: Trajectory ---
    try:
        traj_line = format_trajectory(trajectory)
        if traj_line:
            block += f"\n{traj_line}"
    except Exception as exc:
        logger.debug("Trajectory format error: %s", exc)

    # --- Feature 4: Cross-Channel Convergence ---
    try:
        cross = format_cross_channel(aggregate, metrics)
        if cross:
            block += f"\n{cross}"
    except Exception as exc:
        logger.debug("Cross-channel error: %s", exc)

    # Save current as new snapshot (for next comparison)
    if metrics:
        save_snapshot({
            "coherence_score": metrics.get("coherence_score", 0.0),
            "attention_entropy": metrics.get("attention_entropy", 0.0),
            "memory_utilization": metrics.get("memory_utilization", 0.0),
            "memory_size": metrics.get("memory_size", 0),
            "surprise_gates": metrics.get("surprise_gates"),
            "timestamp": time.time(),
        })

    # Output to stdout (injected into Claude context)
    print(block)

    # Feedback on stderr (visible to user in terminal)
    elapsed = time.monotonic() - start
    coherence = metrics.get("coherence_score", 0.0) if metrics else 0.0
    corr_tag = "+corr" if is_correction else ""
    w_status = f"wrote:{surprise_type}{corr_tag}" if write_result else "write:skip"
    if prev and metrics:
        d = abs(coherence - prev.get("coherence_score", 0.0))
        r_status = "CHANGED" if d > NORM_DELTA_THRESHOLD else "stable"
    elif metrics:
        r_status = "first read"
    else:
        r_status = "read:skip"
    pivot_tag = " PIVOT" if is_pivot else ""
    print(
        f"~ M: {coherence:.4f} ({w_status}, {r_status}, n={prompt_count}{pivot_tag}, {elapsed*1000:.0f}ms)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
