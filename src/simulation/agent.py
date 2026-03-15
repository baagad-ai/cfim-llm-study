"""Agent — wraps call_llm, manages inventory/VP/memory, reflects on round multiples.

Agent is a dataclass (not Pydantic) for easy mutation during gameplay.
All LLM calls go through call_llm() — no direct litellm imports here.

Reflection timing: reflect() must be called by game.py AFTER round_end is
written and flushed to JSONL. See Agent.reflect() docstring for the enforced
call-site contract.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from src.simulation.llm_router import call_llm_provider as call_llm
from src.prompts.agent_action import build_act_messages
from src.prompts.trade_response import build_respond_messages
from src.prompts.reflection import build_reflect_messages
from src.prompts.json_utils import parse_agent_response

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
        messages = build_act_messages(
            agent_id=self.agent_id,
            model_family=self.model_family,
            round_num=round_num,
            inventory=self.inventory,
            vp=self.vp,
            buildings_built=self.buildings_built,
            all_agents_vp=game_state.get("vp", {}),
            memory=self.memory[-3:],
            buildings_config=game_state.get("buildings", {}),
        )
        content, _cost = call_llm(
            model_string=self.model_string,
            provider=self.provider,
            messages=messages,
            mock_response=mock_response,
        )
        action = parse_agent_response(content, {})
        if action is None:
            logger.warning(
                "agent %s round %d: parse_agent_response returned None, hoarding",
                self.agent_id, round_num,
            )
            return {"action_type": "hoard"}
        if "action_type" not in action:
            logger.warning(
                "agent %s round %d: action missing action_type, hoarding",
                self.agent_id, round_num,
            )
            return {"action_type": "hoard"}
        return action

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
        messages = build_respond_messages(
            agent_id=self.agent_id,
            inventory=self.inventory,
            vp=self.vp,
            proposal=proposal,
            buildings_config=game_state.get("buildings", {}),
        )
        content, _cost = call_llm(
            model_string=self.model_string,
            provider=self.provider,
            messages=messages,
            mock_response=mock_response,
        )
        response = parse_agent_response(content, {})
        if response is None:
            logger.warning(
                "agent %s: trade response parse returned None, declining",
                self.agent_id,
            )
            return {"accepted": False, "counter": None}
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
        messages = build_reflect_messages(
            agent_id=self.agent_id,
            round_num=round_num,
            inventory=self.inventory,
            vp=self.vp,
            memory=self.memory,
        )
        content, _cost = call_llm(
            model_string=self.model_string,
            provider=self.provider,
            messages=messages,
            is_reflection=True,
            mock_response=mock_response,
        )
        self.memory.append(content)
        return content
