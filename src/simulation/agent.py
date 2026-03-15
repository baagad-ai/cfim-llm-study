"""Agent — wraps call_llm, manages inventory/VP/memory, reflects on round multiples.

Agent is a dataclass (not Pydantic) for easy mutation during gameplay.
All LLM calls go through call_llm() — no direct litellm imports here.

Reflection timing: reflect() must be called by game.py AFTER round_end is
written and flushed to JSONL. See Agent.reflect() docstring for the enforced
call-site contract.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from src.simulation.llm_router import call_llm

logger = logging.getLogger(__name__)


@dataclass
class Agent:
    """One game participant.

    Args:
        agent_id:       Unique identifier, e.g. "a0".
        model_family:   Family name, e.g. "mistral", "llama", "deepseek", "gemini".
        model_string:   Exact litellm model string, e.g. "mistral/mistral-small-2506".
        provider:       Provider key for PROVIDER_KWARGS, e.g. "mistral".
        inventory:      Current resource holdings, e.g. {"wood": 2, "grain": 5}.
        vp:             Victory points accumulated so far.
        memory:         Chronological list of reflection summaries.
        buildings_built: Building names constructed this game.
    """

    agent_id: str
    model_family: str
    model_string: str
    provider: str
    inventory: dict[str, int] = field(default_factory=dict)
    vp: int = 0
    memory: list[str] = field(default_factory=list)
    buildings_built: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Core methods
    # ------------------------------------------------------------------

    def act(
        self,
        round_num: int,
        game_state: dict,
        mock_response: str = None,
    ) -> dict:
        """Decide an action for this round.

        Calls call_llm() and parses the JSON response into a structured action dict.

        Expected JSON from the model:
        {
            "action_type": "trade" | "build" | "hoard",
            "target":    str | null,           # target agent_id for trade
            "give":      {resource: qty} | null,  # what this agent offers
            "want":      {resource: qty} | null,  # what this agent wants back
            "building":  str | null             # building name for "build" action
        }

        On any JSON parse failure, returns the safe fallback {"action_type": "hoard"}
        so the game loop never crashes due to malformed model output.

        Args:
            round_num:     Current round number (1-indexed).
            game_state:    Dict with public game information passed to prompt.
            mock_response: If not None, passed to call_llm — no real API call.

        Returns:
            Parsed action dict. Always contains "action_type" key.
        """
        messages = _build_act_messages(self, round_num, game_state)
        try:
            content, _cost = call_llm(
                model_string=self.model_string,
                provider=self.provider,
                messages=messages,
                mock_response=mock_response,
            )
            action = json.loads(content)
            if "action_type" not in action:
                logger.warning(
                    "agent %s round %d: action missing action_type, hoarding",
                    self.agent_id, round_num,
                )
                return {"action_type": "hoard"}
            return action
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            logger.warning(
                "agent %s round %d: JSON parse failed (%s), hoarding",
                self.agent_id, round_num, exc,
            )
            return {"action_type": "hoard"}

    def respond_to_trade(
        self,
        proposal: dict,
        game_state: dict,
        mock_response: str = None,
    ) -> dict:
        """Respond to a trade proposal from another agent.

        Calls call_llm() and parses the JSON response.

        Expected JSON from the model:
        {
            "accepted": bool,
            "counter":  {resource: qty} | null   # counter-offer resources (optional)
        }

        On any JSON parse failure, returns {"accepted": false, "counter": null} as
        the safe fallback — a failed parse declines the trade rather than accepting
        unknown terms.

        Args:
            proposal:      The incoming trade proposal dict.
            game_state:    Dict with public game information passed to prompt.
            mock_response: If not None, passed to call_llm — no real API call.

        Returns:
            Response dict with "accepted" (bool) and optional "counter" (dict|None).
        """
        messages = _build_respond_messages(self, proposal, game_state)
        try:
            content, _cost = call_llm(
                model_string=self.model_string,
                provider=self.provider,
                messages=messages,
                mock_response=mock_response,
            )
            response = json.loads(content)
            if "accepted" not in response:
                logger.warning(
                    "agent %s: trade response missing 'accepted' field, declining",
                    self.agent_id,
                )
                return {"accepted": False, "counter": None}
            # Normalise counter: ensure it's a dict or None.
            if "counter" not in response:
                response["counter"] = None
            return response
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            logger.warning(
                "agent %s: trade response JSON parse failed (%s), declining",
                self.agent_id, exc,
            )
            return {"accepted": False, "counter": None}

    def reflect(
        self,
        round_num: int,
        game_state: dict,
        mock_response: str = None,
    ) -> str:
        """Produce a strategic reflection summary and append it to memory.

        Must be called AFTER round_end event is written and flushed to JSONL.
        game.py is the only legal call site; it must call this method after
        logger.log_round_end() + logger.flush() have completed for the current round.
        Calling reflect() before round_end is written would produce a reflection
        that refers to game state that is not yet durably logged — this creates
        a consistency gap on crash-resume.

        This method is only called by game.py on rounds 5/10/15/20/25. The
        caller is responsible for checking the round number before invoking.

        Uses is_reflection=True so DeepSeek agents switch to the R1 reasoner
        model (D007/D024). Other providers use their standard model.

        Args:
            round_num:     The round just completed (1-indexed). Used in the prompt.
            game_state:    Dict with public game information passed to prompt.
            mock_response: If not None, passed to call_llm — no real API call.

        Returns:
            The reflection text that was appended to self.memory.
        """
        messages = _build_reflect_messages(self, round_num, game_state)
        content, _cost = call_llm(
            model_string=self.model_string,
            provider=self.provider,
            messages=messages,
            is_reflection=True,
            mock_response=mock_response,
        )
        self.memory.append(content)
        return content


# ------------------------------------------------------------------
# Prompt builders (module-level to keep Agent class body readable)
# ------------------------------------------------------------------

def _build_act_messages(agent: Agent, round_num: int, game_state: dict) -> list[dict]:
    """Build the chat messages list for an act() call."""
    memory_text = ""
    if agent.memory:
        memory_text = "\nYour past reflections:\n" + "\n".join(
            f"- {m}" for m in agent.memory[-3:]  # last 3 reflections to stay compact
        )

    system = (
        "You are playing Trade Island. Each round you choose one action: "
        "trade resources with another agent, build a building, or hoard. "
        "Respond ONLY with valid JSON."
    )
    user = (
        f"Round {round_num}.\n"
        f"Your agent: {agent.agent_id}.\n"
        f"Your inventory: {json.dumps(agent.inventory)}.\n"
        f"Your VP: {agent.vp}.\n"
        f"Buildings built: {agent.buildings_built}.\n"
        f"Game state: {json.dumps(game_state)}."
        f"{memory_text}\n"
        "Choose an action. Respond with JSON:\n"
        '{"action_type": "trade"|"build"|"hoard", '
        '"target": str|null, '
        '"give": {resource: qty}|null, '
        '"want": {resource: qty}|null, '
        '"building": str|null}'
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _build_respond_messages(
    agent: Agent, proposal: dict, game_state: dict
) -> list[dict]:
    """Build the chat messages list for a respond_to_trade() call."""
    system = (
        "You are playing Trade Island. You received a trade proposal. "
        "Decide whether to accept, decline, or counter. "
        "Respond ONLY with valid JSON."
    )
    user = (
        f"Your agent: {agent.agent_id}.\n"
        f"Your inventory: {json.dumps(agent.inventory)}.\n"
        f"Trade proposal: {json.dumps(proposal)}.\n"
        f"Game state: {json.dumps(game_state)}.\n"
        "Respond with JSON:\n"
        '{"accepted": true|false, "counter": {resource: qty}|null}'
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _build_reflect_messages(
    agent: Agent, round_num: int, game_state: dict
) -> list[dict]:
    """Build the chat messages list for a reflect() call."""
    system = (
        "You are playing Trade Island. Reflect on your strategy so far. "
        "Give a concise summary (2-3 sentences) of what is working and what to change."
    )
    past = ""
    if agent.memory:
        past = "\nYour previous reflections:\n" + "\n".join(
            f"- {m}" for m in agent.memory
        )
    user = (
        f"Round {round_num} just ended.\n"
        f"Your agent: {agent.agent_id}.\n"
        f"Your VP: {agent.vp}.\n"
        f"Your inventory: {json.dumps(agent.inventory)}.\n"
        f"Game state: {json.dumps(game_state)}."
        f"{past}\n"
        "Write a brief strategic reflection."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
