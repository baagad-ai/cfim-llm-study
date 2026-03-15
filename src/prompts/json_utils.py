"""Tolerant JSON parser and prompt formatting helpers for src/prompts/.

Public API:
    parse_agent_response(raw, schema) -> dict | None
    format_inventory(inv) -> str
    get_completion_kwargs(model_family) -> dict

Parser strategy chain (parse_agent_response):
    1. strip_md(raw) → json.loads()           — direct parse after fence strip
    2. strip_think(stripped) → json.loads()   — handles DeepSeek <think> prefix
    3. extract_first_json_object(text) → json.loads()  — JSON embedded in text
    4. return None                             — truncated or unrecoverable

Note: model_family keys in PROVIDER_KWARGS match the model_family strings used in
GameConfig (e.g. 'gemini', 'mistral', 'deepseek', 'groq').  No mapping needed.
"""

import json
import logging
import re

# NOTE: PROVIDER_KWARGS and strip_md are imported lazily (inside functions) to
# break a circular import: src.prompts.json_utils → src.simulation.llm_router
# triggers src.simulation.__init__ → game.py → agent.py → src.prompts, which
# re-enters json_utils before it is fully initialised.  Lazy import defers
# the dependency until the first function call, at which point both packages
# are fully loaded.

logger = logging.getLogger(__name__)

# Fixed resource ordering — deterministic output for prompt injection.
_RESOURCE_ORDER = ["wood", "stone", "grain", "clay", "fiber"]
_RESOURCE_INITIALS = {"wood": "W", "stone": "S", "grain": "G", "clay": "C", "fiber": "F"}


# ---------------------------------------------------------------------------
# format_inventory
# ---------------------------------------------------------------------------

def format_inventory(inv: dict[str, int]) -> str:
    """Return compact inventory string in fixed W S G C F order.

    Example: format_inventory({'wood':2,'stone':3,'grain':4,'clay':1,'fiber':0}) → 'W2 S3 G4 C1 F0'
    """
    parts = []
    for resource in _RESOURCE_ORDER:
        initial = _RESOURCE_INITIALS[resource]
        count = inv.get(resource, 0)
        parts.append(f"{initial}{count}")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# strip_think
# ---------------------------------------------------------------------------

def strip_think(text: str) -> str:
    """Remove leading <think>...</think> block (DeepSeek R1/V3.2 output).

    Handles multiline think blocks via re.DOTALL.  Only strips a leading block —
    a think block in the middle of the string is left intact (not expected in practice).
    """
    return re.sub(r"^<think>.*?</think>\s*", "", text, flags=re.DOTALL).strip()


# ---------------------------------------------------------------------------
# extract_first_json_object
# ---------------------------------------------------------------------------

def extract_first_json_object(text: str) -> str | None:
    """Extract the first complete JSON object using a bracket counter.

    Finds the first '{', then scans forward counting open/close braces.
    Returns the substring when the count reaches 0 (balanced braces found).
    Returns None if no '{' or braces never balance (truncated).

    Deliberately avoids re.search(r'\\{.*\\}', ...) — that captures the wrong
    span on strings with multiple JSON fragments or trailing text.
    """
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False

    for i in range(start, len(text)):
        ch = text[i]

        if escape_next:
            escape_next = False
            continue

        if ch == "\\" and in_string:
            escape_next = True
            continue

        if ch == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    # Braces never balanced — truncated or malformed.
    return None


# ---------------------------------------------------------------------------
# parse_agent_response
# ---------------------------------------------------------------------------

def parse_agent_response(raw: str, schema: dict) -> dict | None:
    """Multi-strategy tolerant JSON parser.  Returns None on unrecoverable failure.

    Strategy chain:
      1. strip_md(raw) → json.loads()          — fence-wrapped JSON (Gemini)
      2. strip_think(stripped) → json.loads()  — <think> prefix (DeepSeek)
      3. extract_first_json_object → json.loads() — JSON embedded in prose
      4. return None                            — truncated / unrecoverable

    Only catches json.JSONDecodeError, ValueError, TypeError.  Any other exception
    (e.g. a regex bug in strip_think) propagates so tests surface it immediately.

    The 'schema' parameter is reserved for future schema-guided repair; currently
    unused but required by the public API to keep callers forward-compatible.
    """
    from src.simulation.llm_router import strip_md  # lazy — avoids circular import at module init

    raw_preview = raw[:80] if raw else ""

    # Strategy 1: direct parse after fence strip.
    stripped = strip_md(raw)
    try:
        return json.loads(stripped)
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    # Strategy 2: strip <think> prefix then parse.
    no_think = strip_think(stripped)
    if no_think != stripped:
        logger.warning(
            "parse_agent_response: strategy 1 failed, trying strategy 2 (strip_think). "
            "Input preview: %r",
            raw_preview,
        )
        try:
            return json.loads(no_think)
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
    else:
        # No think block present — skip the redundant log, move straight to strategy 3.
        no_think = stripped

    # Strategy 3: extract first JSON object by bracket counter.
    logger.warning(
        "parse_agent_response: strategies 1–2 failed, trying strategy 3 (extract_first_json_object). "
        "Input preview: %r",
        raw_preview,
    )
    candidate = extract_first_json_object(no_think)
    if candidate is not None:
        try:
            return json.loads(candidate)
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    # Strategy 4: unrecoverable.
    logger.warning(
        "parse_agent_response: all strategies failed, returning None (truncated or unrecoverable). "
        "Input preview: %r",
        raw_preview,
    )
    return None


# ---------------------------------------------------------------------------
# get_completion_kwargs
# ---------------------------------------------------------------------------

def get_completion_kwargs(model_family: str) -> dict:
    """Return a shallow copy of PROVIDER_KWARGS for the given model_family.

    Raises KeyError if model_family is not registered — callers must handle
    missing families explicitly rather than silently getting empty kwargs.

    The model_family string matches the provider key in PROVIDER_KWARGS
    (e.g. 'gemini', 'mistral', 'deepseek', 'groq').
    """
    from src.simulation.llm_router import PROVIDER_KWARGS  # lazy — avoids circular import at module init
    return dict(PROVIDER_KWARGS[model_family])
