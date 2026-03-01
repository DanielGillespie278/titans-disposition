"""
Code Session Classifier -- Maps prompts to 8 domains + correction flag.

Domain taxonomy:
    routine, memory_arch, voice_arch, substrate_arch,
    meta_arch, pipeline_orch, exploration, identity

Correction is orthogonal -- detected separately via regex patterns.

Classification tiers:
    Tier 1: Prompt text keyword/regex matching (<1ms)
    Tier 2: Default to "routine" when no signal

No LLM call. No file path analysis (not available at API request time).
"""

import re

# --- Correction regex (validated on 4,436 prompts) ---
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

# --- Domain text rules (priority-ordered: first match wins) ---
_DOMAIN_TEXT_RULES: list[tuple[str, re.Pattern]] = [
    # Substrate / TITANS
    ("substrate_arch", re.compile(
        r"\b(?:TITANS|M.?vector|gradient.?(?:gate|norm)|disposition|"
        r"substrate|surprise.?(?:signal|gate|calculator)|"
        r"alpha.?forget|theta.?learn|eta.?momentum|"
        r"Hadamard|inner.?loop|pred.?head)\b", re.I)),
    # Memory architecture
    ("memory_arch", re.compile(
        r"\b(?:transplant|capsule|deposit|FAISS|"
        r"memory.?(?:pipeline|system|substrate|retriev)|"
        r"corpus|extraction|bridge.?dream|"
        r"episodic|consolidat(?:e|ion))\b", re.I)),
    # Voice architecture
    ("voice_arch", re.compile(
        r"\b(?:voice.?(?:router|agent|pipeline|stack|model)|"
        r"TTS|STT|VAD|LiveKit|Deepgram|Whisper|"
        r"Edge.?TTS|Qwen.?TTS|latency|streaming.?voice)\b", re.I)),
    # Meta-architectural
    ("meta_arch", re.compile(
        r"\b(?:backroom|deliberat(?:e|ion)|observer.?(?:prompt|rewrite)|"
        r"cognitive.?ensemble|sentinel|heartbeat|"
        r"hook|self.?(?:direct|evolv|modif|observ)|"
        r"prior.?cast|dream.?cycle|speech.?floor)\b", re.I)),
    # Identity / personality
    ("identity", re.compile(
        r"\b(?:persona(?:lity)?|identity|"
        r"soul|skeleton|costume|SAGE|REBEL|PRIME|"
        r"facilitat(?:e|ion)|tone|tonal|carrier.?wave)\b", re.I)),
    # Pipeline orchestration
    ("pipeline_orch", re.compile(
        r"\b(?:swarm|agent.?team|Codex|orchestrat|"
        r"send.+(?:to|agent)|launch.+(?:agent|team)|"
        r"docker|redis|rebuild|restart.+(?:voice|router|stack)|"
        r"wire|wiring|endpoint|API.?(?:route|endpoint))\b", re.I)),
    # Exploration / strategic (+ ui_arch fold-in)
    ("exploration", re.compile(
        r"\b(?:what.?s.?next|what.?should|where.?do|"
        r"vision|north.?star|strategy|roadmap|"
        r"what.?(?:ideas?|direction|priority)|"
        r"open.?source|product.?story|"
        r"playground|orb|presence|frontend|"
        r"component|CSS|shader|visualization|"
        r"waveform|dashboard|UI)\b", re.I)),
]


def classify_code_session(text: str) -> tuple[str, bool]:
    """
    Classify a prompt into domain + correction flag.

    Args:
        text: User prompt text

    Returns:
        Tuple of (domain, is_correction)
        domain: One of the 8 domains
        is_correction: Whether the user is correcting the agent
    """
    is_correction = bool(_CORRECTION_PATTERNS.search(text))

    for domain, pattern in _DOMAIN_TEXT_RULES:
        if pattern.search(text):
            return domain, is_correction

    return "routine", is_correction


# Public alias for the package API
classify_prompt = classify_code_session
