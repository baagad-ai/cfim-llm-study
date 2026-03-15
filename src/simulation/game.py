"""GameRunner — 25-round Trade Island game loop.

Wires Agent, GM, GameLogger, and GameConfig into a complete game.

Critical ordering guarantees (enforced in the round loop):
  1. logger.flush() (fsync) is called BEFORE checkpoint_r{N:02d}.json is written.
     This ensures the JSONL audit trail is durable before the state snapshot exists.
  2. agent.reflect() is called AFTER logger.log_round_end() for that round.
     This ensures reflections refer to game state that is already durably logged.

Cost tracking: GameRunner patches call_llm at startup to accumulate per-call
costs into a shared list. The sum is written to game_end.total_cost_usd.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import src.simulation.llm_router as _llm_router_mod
from src.simulation.agent import Agent
from src.simulation.config import GameConfig
from src.simulation.gm import GM
from src.simulation.logger import GameLogger

# Starting inventory for every agent
_STARTING_INVENTORY: dict[str, int] = {
    "wood": 3,
    "stone": 3,
    "grain": 5,
    "clay": 3,
    "fiber": 2,
}

# Damage VP penalty when an agent runs out of grain
_HUNGER_PENALTY_VP: int = -1


class GameRunner:
    """Runs a complete Trade Island game.

    Args:
        config: GameConfig instance describing model assignments and rules.
    """

    def __init__(self, config: GameConfig) -> None:
        self.config = config

    def run_game(self, mock_response: str | None = None) -> dict[str, Any]:
        """Run a full game and return a summary dict.

        Cost tracking: wraps call_llm to accumulate per-call costs.
        For mock runs mock_response is not None → call_llm returns 0.0 per call.
        For real runs each call_llm returns the actual USD cost; we sum them here.

        Args:
            mock_response: If not None, passed through to all LLM calls.
                           No real API calls are made; cost = 0.0.

        Returns:
            {
                "game_id":        str,
                "total_cost_usd": float,
                "rounds_played":  int,
            }
        """
        config = self.config
        game_id = uuid.uuid4().hex[:8]
        output_dir = Path(f"data/raw/{game_id}")
        output_dir.mkdir(parents=True, exist_ok=True)

        # ------------------------------------------------------------------
        # Cost accumulator: wrap call_llm to capture per-call cost
        # ------------------------------------------------------------------
        _cost_bucket: list[float] = []
        _original_call_llm = _llm_router_mod.call_llm

        def _tracking_call_llm(*args, **kwargs):
            content, cost = _original_call_llm(*args, **kwargs)
            _cost_bucket.append(cost)
            return content, cost

        _llm_router_mod.call_llm = _tracking_call_llm  # type: ignore[assignment]

        # Also patch in the agent and gm modules since they import call_llm directly
        import src.simulation.agent as _agent_mod
        import src.simulation.gm as _gm_mod
        _agent_mod.call_llm = _tracking_call_llm  # type: ignore[assignment]
        _gm_mod.call_llm = _tracking_call_llm  # type: ignore[assignment]

        try:
            result = self._run(
                game_id=game_id,
                output_dir=output_dir,
                cost_bucket=_cost_bucket,
                mock_response=mock_response,
            )
        finally:
            # Restore original call_llm in all modules
            _llm_router_mod.call_llm = _original_call_llm
            _agent_mod.call_llm = _original_call_llm
            _gm_mod.call_llm = _original_call_llm

        return result

    def _run(
        self,
        game_id: str,
        output_dir: Path,
        cost_bucket: list[float],
        mock_response: str | None,
    ) -> dict[str, Any]:
        """Inner game loop. Called by run_game() with cost tracking already active."""
        config = self.config

        # ------------------------------------------------------------------
        # Initialise agents
        # ------------------------------------------------------------------
        agents: list[Agent] = []
        model_assignments: dict[str, str] = {}

        for entry in config.agent_models:
            # Provider is the leading component of the model string, e.g.
            # "mistral/mistral-small-2506" → provider = "mistral"
            provider = entry["model_string"].split("/")[0]
            agent = Agent(
                agent_id=entry["agent_id"],
                model_family=entry["model_family"],
                model_string=entry["model_string"],
                provider=provider,
                inventory=dict(_STARTING_INVENTORY),
                vp=0,
            )
            agents.append(agent)
            model_assignments[entry["agent_id"]] = entry["model_family"]

        agent_map: dict[str, Agent] = {a.agent_id: a for a in agents}

        # ------------------------------------------------------------------
        # Initialise GM and Logger
        # ------------------------------------------------------------------
        logger = GameLogger(game_id=game_id, output_dir=output_dir)
        gm = GM(model_string=config.gm_model, logger=logger)

        # Seed value for determinism metadata (not used for RNG here)
        seed = int(game_id, 16) % (2**32)

        # ---- game_start ---------------------------------------------------
        logger.log(
            "game_start",
            config_name=config.config_name,
            model_assignments=model_assignments,
            seed=seed,
        )

        # ------------------------------------------------------------------
        # Round loop
        # ------------------------------------------------------------------
        for round_num in range(1, config.num_rounds + 1):
            logger.log("round_start", round=round_num)

            game_state = _build_game_state(round_num, agents, config)

            # ---- Phase 1: each agent acts ---------------------------------
            actions: list[dict] = []
            for agent in agents:
                action = agent.act(
                    round_num=round_num,
                    game_state=game_state,
                    mock_response=mock_response,
                )
                action["_agent_id"] = agent.agent_id
                actions.append(action)
                logger.log(
                    "agent_action",
                    round=round_num,
                    agent_id=agent.agent_id,
                    model_family=agent.model_family,
                    action_type=action.get("action_type", "hoard"),
                )

            # ---- Phase 2: collect proposals with responder responses -------
            proposals: list[dict] = []
            for action in actions:
                if action.get("action_type") != "trade":
                    continue
                proposer_id = action["_agent_id"]
                target_id = action.get("target")
                if not target_id or target_id not in agent_map:
                    continue
                give = action.get("give") or {}
                want = action.get("want") or {}
                if not give or not want:
                    continue

                responder = agent_map[target_id]
                proposal = {
                    "proposer": proposer_id,
                    "responder": target_id,
                    "give": give,
                    "want": want,
                }
                response = responder.respond_to_trade(
                    proposal=proposal,
                    game_state=game_state,
                    mock_response=mock_response,
                )
                proposal["accepted"] = response.get("accepted", False)
                proposal["counter"] = response.get("counter")
                proposals.append(proposal)

            # ---- Phase 3: GM resolves trades ------------------------------
            inventories_snapshot = {a.agent_id: dict(a.inventory) for a in agents}
            resolutions = gm.resolve_trades(
                round_num=round_num,
                proposals=proposals,
                inventories=inventories_snapshot,
                model_families={a.agent_id: a.model_family for a in agents},
                config_name=config.config_name,
                mock_response=mock_response,
            )

            # Apply accepted trades to real agent inventories
            for res in resolutions:
                if not res.accepted:
                    continue
                proposer_agent = agent_map[res.proposer]
                responder_agent = agent_map[res.responder]

                matching = next(
                    (p for p in proposals
                     if p["proposer"] == res.proposer and p["responder"] == res.responder),
                    None,
                )
                if matching is None:
                    continue

                give = matching.get("give") or {}
                counter = matching.get("counter")
                want = matching.get("want") or {}
                receive = counter if counter else want

                for resource, qty in give.items():
                    proposer_agent.inventory[resource] = max(
                        0, proposer_agent.inventory.get(resource, 0) - qty
                    )
                    responder_agent.inventory[resource] = (
                        responder_agent.inventory.get(resource, 0) + qty
                    )

                for resource, qty in receive.items():
                    responder_agent.inventory[resource] = max(
                        0, responder_agent.inventory.get(resource, 0) - qty
                    )
                    proposer_agent.inventory[resource] = (
                        proposer_agent.inventory.get(resource, 0) + qty
                    )

            # ---- Phase 4: builds ------------------------------------------
            for action in actions:
                if action.get("action_type") != "build":
                    continue
                agent_id = action["_agent_id"]
                building_name = action.get("building")
                if not building_name or building_name not in config.buildings:
                    continue
                agent = agent_map[agent_id]
                building = config.buildings[building_name]
                cost = building.get("cost", {})

                affordable = all(
                    agent.inventory.get(res, 0) >= qty
                    for res, qty in cost.items()
                )
                if not affordable:
                    continue

                for res, qty in cost.items():
                    agent.inventory[res] = agent.inventory.get(res, 0) - qty
                vp_delta = building.get("vp", 0)
                agent.vp += vp_delta
                agent.buildings_built.append(building_name)

                logger.log(
                    "build",
                    round=round_num,
                    agent_id=agent_id,
                    model_family=agent.model_family,
                    building=building_name,
                    vp_delta=vp_delta,
                    vp_total=agent.vp,
                )

            # ---- Phase 5: grain consumption --------------------------------
            for agent in agents:
                hunger = config.hunger_rate
                grain = agent.inventory.get("grain", 0)
                if grain >= hunger:
                    agent.inventory["grain"] = grain - hunger
                    starved = False
                else:
                    agent.inventory["grain"] = 0
                    starved = True
                    agent.vp += _HUNGER_PENALTY_VP

                logger.log(
                    "grain_consumption",
                    round=round_num,
                    agent_id=agent.agent_id,
                    model_family=agent.model_family,
                    grain_consumed=hunger if not starved else grain,
                    starved=starved,
                    vp=agent.vp,
                )

            # ---- Flush sequence: fsync FIRST, then checkpoint -------------
            # This ordering is critical for crash-resume correctness.
            # The JSONL audit trail must be durable before the checkpoint exists.
            logger.flush()  # fsync JSONL

            checkpoint = _build_checkpoint(round_num, game_id, agents, config)
            checkpoint_path = output_dir / f"checkpoint_r{round_num:02d}.json"
            checkpoint_path.write_text(
                json.dumps(checkpoint, indent=2), encoding="utf-8"
            )

            # ---- round_end (one line per agent) — AFTER checkpoint --------
            agent_state_list = [
                {
                    "agent_id": a.agent_id,
                    "model_family": a.model_family,
                    "vp": a.vp,
                }
                for a in agents
            ]
            logger.log_round_end(round_num, agent_state_list)

            # ---- Reflection: ONLY after round_end is written --------------
            # Enforced by code order: reflect() cannot appear before log_round_end().
            if round_num % 5 == 0:
                for agent in agents:
                    reflection = agent.reflect(
                        round_num=round_num,
                        game_state=game_state,
                        mock_response=mock_response,
                    )
                    logger.log(
                        "reflection",
                        round=round_num,
                        agent_id=agent.agent_id,
                        model_family=agent.model_family,
                        summary=reflection[:500],
                    )

        # ------------------------------------------------------------------
        # game_end
        # ------------------------------------------------------------------
        winner_agent = max(agents, key=lambda a: a.vp)
        final_vp = {a.agent_id: a.vp for a in agents}
        total_cost_usd: float = sum(cost_bucket)

        logger.log(
            "game_end",
            config_name=config.config_name,
            winner=winner_agent.agent_id,
            winner_model=winner_agent.model_family,
            final_vp=final_vp,
            rounds_played=25,
            total_cost_usd=total_cost_usd,
        )

        logger.close()

        return {
            "game_id": game_id,
            "total_cost_usd": total_cost_usd,
            "rounds_played": 25,
        }


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _build_game_state(
    round_num: int, agents: list[Agent], config: GameConfig
) -> dict[str, Any]:
    """Build a public game state snapshot for agent prompts.

    Agents see all VP and IDs but not private inventories of others.
    """
    return {
        "round": round_num,
        "num_rounds": config.num_rounds,
        "agents": [
            {
                "agent_id": a.agent_id,
                "model_family": a.model_family,
                "vp": a.vp,
            }
            for a in agents
        ],
        "buildings_available": list(config.buildings.keys()),
        "resources": config.resources,
    }


def _build_checkpoint(
    round_num: int,
    game_id: str,
    agents: list[Agent],
    config: GameConfig,
) -> dict[str, Any]:
    """Build a serialisable game state dict for crash-resume checkpoints."""
    return {
        "game_id": game_id,
        "round": round_num,
        "config_name": config.config_name,
        "agents": [
            {
                "agent_id": a.agent_id,
                "model_family": a.model_family,
                "model_string": a.model_string,
                "provider": a.provider,
                "inventory": dict(a.inventory),
                "vp": a.vp,
                "buildings_built": list(a.buildings_built),
                "memory": list(a.memory),
            }
            for a in agents
        ],
    }
