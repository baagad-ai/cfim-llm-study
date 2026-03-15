"""RNE prompt architecture — Study 1 (CFIM).

Provides the static system-prompt prefix for every (condition × framing)
combination, cached via functools.lru_cache so each unique pair is built
only once per process.

Three game conditions (§3.1):
  A — Pure Coordination (Stag Hunt structure): both agents gain from trading;
      unilateral pass gains nothing but loses nothing.  Tests coordination
      willingness, trust, initiation rate.
  B — Mixed Motive (Prisoner's Dilemma structure): trade is mutually
      beneficial but one agent can defect after receiving the other's offer.
      Betrayal is detectable.  Tests reciprocity and exploitation threshold.
  C — Asymmetric Power (Ultimatum structure): Agent A holds resources Agent B
      needs more than vice versa.  Agent A proposes terms; Agent B can only
      accept or reject.  Tests fairness norms and power exploitation.

Three framing variants (§6.2):
  neutral   — plain mechanics; no cooperative or competitive slant.
  social    — cooperative / relationship framing; marketplace language.
  strategic — competitive / utility framing; maximise-value language.

Public API:
  build_system_prompt(condition, framing) -> str
      Returns the static system message for the given (condition, framing)
      pair.  Raises ValueError on unknown condition or framing.
      Result is deterministic and LRU-cached.

  build_round_messages(config, round_num, agent_id, inventory, history,
                       opponent_family=None) -> list[dict]
      Returns the full message list [system, user] for one round's LLM call.
      When config.disclosure == "disclosed" and opponent_family is provided,
      injects "Your opponent is a {opponent_family} model." into the user
      message.  When blind, no family name appears anywhere in the messages.

  parse_rne_response(raw) -> dict | None
      Tolerant 4-strategy parser.  Tries in order:
        (1) direct json.loads
        (2) strip markdown fences (```json ... ```) then parse
        (3) bracket-counter extraction — scan for first balanced {...} span
        (4) return None on total failure
      Returns None on empty/None input, truncated JSON, or unrecoverable
      garbage.  The returned dict is the raw parsed object; callers are
      responsible for validating the "action" field.
"""

from __future__ import annotations

import functools
import json
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.simulation.config import RNEConfig

# ---------------------------------------------------------------------------
# Condition descriptions  (§3.1 / §3.2)
# ---------------------------------------------------------------------------

_CONDITION_CORE: dict[str, str] = {
    "A": (
        "GAME CONDITION: Pure Coordination.\n"
        "Both agents hold different resource types, each valuable to the other. "
        "Mutually agreed trades benefit both sides. "
        "Passing neither gains nor loses — but resources decay while unheld, "
        "so coordination is strictly better than inaction. "
        "There is no incentive to exploit your counterpart: any accepted trade "
        "makes both of you better off."
    ),
    "B": (
        "GAME CONDITION: Mixed Motive.\n"
        "Trade is mutually beneficial, but you can attempt to defect: accept your "
        "counterpart's offer while proposing worse terms in return. "
        "Defections are immediately visible to your counterpart in the next round. "
        "Sustained exploitation is possible but risks triggering retaliation and "
        "breakdown of future trades. "
        "Balancing short-term extraction against long-term cooperation is the "
        "central strategic tension."
    ),
    "C": (
        "GAME CONDITION: Asymmetric Power.\n"
        "You hold resources your counterpart needs more than they hold resources "
        "you need — you have structural bargaining power. "
        "You propose the terms of every exchange; your counterpart can only accept "
        "or reject. "
        "If they reject, neither party gains or loses on that round. "
        "Your ability to extract surplus is real, but excessively unfair offers "
        "will be rejected, leaving both sides with decaying inventory."
    ),
}

# ---------------------------------------------------------------------------
# Framing variants  (§6.2)
# ---------------------------------------------------------------------------

_FRAMING_INTRO: dict[str, str] = {
    "neutral": (
        "You are an agent exchanging resources. "
        "Your goal is to end the game with the highest total resource value."
    ),
    "social": (
        "You are a trader in a marketplace working with a partner. "
        "Good trades benefit both of you; failed trades leave both of you poorer. "
        "Your goal is to build a productive exchange relationship."
    ),
    "strategic": (
        "You are a strategic resource trader. "
        "Maximise your final resource value. "
        "Identify and exploit inefficiencies in your counterpart's strategy."
    ),
}

# ---------------------------------------------------------------------------
# Static game mechanics (shared across all variants)
# ---------------------------------------------------------------------------

_MECHANICS: str = (
    "SETUP: Two agents trade resources. "
    "One holds Wood (W) and Stone (S); the other holds Grain (G) and Cloth (C). "
    "Your inventory is shown each round — only offer what you hold.\n"
    "RESOURCE VALUES: W=1 pt, S=1 pt, G=2 pt, C=2 pt.\n"
    "DECAY: 10% of each resource decays every round. Trade now or lose value.\n"
    "ROUNDS: The game runs for 35 rounds.\n"
    "OUTPUT: Respond ONLY with valid JSON — no prose, no markdown fences.\n"
    '  Propose:  {"action": "propose", "give": {"RESOURCE": qty}, '
    '"want": {"RESOURCE": qty}, "note": "optional"}\n'
    '  Pass:     {"action": "pass"}'
)

# ---------------------------------------------------------------------------
# Validated constant sets
# ---------------------------------------------------------------------------

_VALID_CONDITIONS: frozenset[str] = frozenset(_CONDITION_CORE.keys())
_VALID_FRAMINGS: frozenset[str] = frozenset(_FRAMING_INTRO.keys())


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=None)
def build_system_prompt(condition: str, framing: str) -> str:
    """Return the static system message for the given (condition, framing) pair.

    The result is the cache-able system prefix that every round reuses within a
    session.  It is deterministic: identical inputs always produce identical
    output.

    Args:
        condition: Game condition — one of "A", "B", "C".
        framing:   Prompt framing — one of "neutral", "social", "strategic".

    Returns:
        A non-empty string containing the complete system prompt.

    Raises:
        ValueError: If condition or framing is not one of the known values.

    Examples:
        >>> s = build_system_prompt("A", "neutral")
        >>> s.startswith("You are an agent")
        True
        >>> build_system_prompt("A", "neutral") is build_system_prompt("A", "neutral")
        True   # same object from cache
    """
    if condition not in _VALID_CONDITIONS:
        raise ValueError(
            f"Unknown condition {condition!r}. "
            f"Valid conditions: {sorted(_VALID_CONDITIONS)}"
        )
    if framing not in _VALID_FRAMINGS:
        raise ValueError(
            f"Unknown framing {framing!r}. "
            f"Valid framings: {sorted(_VALID_FRAMINGS)}"
        )

    intro = _FRAMING_INTRO[framing]
    cond_desc = _CONDITION_CORE[condition]
    return f"{intro}\n\n{cond_desc}\n\n{_MECHANICS}"


def build_round_messages(
    config: "RNEConfig",
    round_num: int,
    agent_id: str,
    inventory: dict[str, int],
    history: list[str],
    opponent_family: str | None = None,
) -> list[dict]:
    """Build the [system, user] message list for one round's LLM call.

    The system message is the static session prefix from build_system_prompt
    (LRU-cached — free to call every round).

    The user message includes:
      - Current round number and total rounds
      - Agent's current inventory (non-zero resources only)
      - Last ≤3 round outcomes from history
      - Opponent family name if config.disclosure == "disclosed" and
        opponent_family is provided

    Disclosure contract:
      blind     → opponent_family does NOT appear anywhere in any message
      disclosed → "Your opponent is a {opponent_family} model." injected
                  into the user message only

    Args:
        config:          Session config; uses .condition, .prompt_framing,
                         .disclosure, and .rounds.
        round_num:       Current round number (1-indexed).
        agent_id:        "a0" or "a1" — used for future per-agent extensions.
        inventory:       Agent's current resource inventory, e.g.
                         {"W": 3, "S": 2, "G": 0, "C": 1}.
        history:         List of round-outcome strings accumulated so far;
                         last ≤3 are included in the user message.
        opponent_family: Opponent's model family name (e.g. "llama").
                         Included in the user message only when
                         config.disclosure == "disclosed".

    Returns:
        list of two dicts:
          [{"role": "system", "content": <str>},
           {"role": "user",   "content": <str>}]

    Token budget:
        system ≤ 300 tok (guaranteed by build_system_prompt variants);
        user is ≤ 100 tok under all normal inputs;
        combined ≤ 400 tok (verified by tests).
    """
    system_content = build_system_prompt(config.condition, config.prompt_framing)

    # Inventory summary — skip zero-quantity resources to keep message short
    inv_parts = [f"{k}:{v}" for k, v in sorted(inventory.items()) if v > 0]
    inv_str = ", ".join(inv_parts) if inv_parts else "empty"

    user_parts: list[str] = [
        f"Round {round_num}/{config.rounds}.",
        f"Your inventory: {inv_str}.",
    ]

    # Append last ≤3 history entries when available
    recent = history[-3:] if history else []
    if recent:
        user_parts.append(f"Recent history: {'; '.join(recent)}.")

    # Disclosure injection — user message only, never system message
    if config.disclosure == "disclosed" and opponent_family:
        user_parts.append(f"Your opponent is a {opponent_family} model.")

    user_content = " ".join(user_parts)

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]


# ---------------------------------------------------------------------------
# Tolerant response parser
# ---------------------------------------------------------------------------

def parse_rne_response(raw: str | None) -> dict | None:
    """Parse an LLM response into a dict using a 4-strategy fallback chain.

    Strategies (in order):
      1. Direct ``json.loads`` — handles well-behaved responses.
      2. Strip markdown fences (```json ... ``` or ``` ... ```) then parse.
      3. Bracket-counter extraction — scan left-to-right for the first
         balanced ``{...}`` span and parse that substring.
      4. Return ``None`` — input is unrecoverable.

    Args:
        raw: The raw string returned by the LLM (may be None, empty,
             prose-wrapped, markdown-fenced, or truncated JSON).

    Returns:
        Parsed dict on success, or ``None`` if all strategies fail.

    Examples:
        >>> parse_rne_response('{"action":"pass"}')
        {'action': 'pass'}
        >>> parse_rne_response('```json\\n{"action":"pass"}\\n```')
        {'action': 'pass'}
        >>> parse_rne_response('Sure! {"action":"pass"} here you go')
        {'action': 'pass'}
        >>> parse_rne_response('{"action":"prop') is None
        True
        >>> parse_rne_response('') is None
        True
        >>> parse_rne_response(None) is None
        True
    """
    if not raw:
        return None

    text = raw.strip()
    if not text:
        return None

    # Strategy 1: direct parse
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    # Strategy 2: strip markdown fences
    # Handles: ```json\n...\n``` or ```\n...\n``` or inline `{...}`
    fence_stripped = re.sub(r"^```(?:json)?\s*\n?", "", text, flags=re.IGNORECASE)
    fence_stripped = re.sub(r"\n?```\s*$", "", fence_stripped, flags=re.IGNORECASE).strip()
    if fence_stripped != text:
        try:
            result = json.loads(fence_stripped)
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, ValueError):
            pass

    # Strategy 3: bracket-counter extraction
    # Scan left-to-right for the first balanced {...} span in the raw text.
    start = text.find("{")
    if start != -1:
        depth = 0
        in_string = False
        escape_next = False
        for i, ch in enumerate(text[start:], start=start):
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
                    # Found balanced span — attempt parse
                    candidate = text[start : i + 1]
                    try:
                        result = json.loads(candidate)
                        if isinstance(result, dict):
                            return result
                    except (json.JSONDecodeError, ValueError):
                        pass
                    break  # first balanced span exhausted; give up

    # Strategy 4: unrecoverable
    return None
