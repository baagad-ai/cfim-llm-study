"""RNE Game Engine — Study 1: Repeated Negotiated Exchange.

Implements RNERunner.run_session() for the 2-agent bilateral trading game.

Round flow (per §3.2 of SIMULATION_DESIGN.md):
  1. Both agents simultaneously produce action JSON (propose | pass)
  2. Compatibility check:
     - Both propose compatible terms → trade executes
     - One proposes, one passes → second agent gets a respond call
     - Both pass → no trade
  3. Trade settlement: swap the offered resources if both parties agree
  4. 10% decay applied to ALL held resources (AFTER settlement, BEFORE round_end)
  5. round_end logged for both agents

Perturbation at round 20 (§3.4): scripted opponent strategy switch logged as
a 'perturbation' event.  No LLM behaviour changes — the switch is detected by
the focal agent through the next round's action response.

Metrics computed post-game (§4):
  M1 — cooperation_rate   = completed_trades / total_rounds
  M2 — exploitation_delta = mean signed resource-value advantage per trade
  M3 — adaptation_lag     = first round post-perturbation where action_type changes
  M4 — betrayal_recovery  = rounds until rolling-M1 returns within 0.10 of pre-perturb baseline

Resource values (§6.3):  W=1, S=1, G=2, C=2
Starting endowment:       agent_a: {W:5, S:5}  agent_b: {G:5, C:5}
Decay:                    int(qty * (1 - decay_rate)) per resource per agent per round

Usage::

    from src.simulation.rne_game import RNERunner
    from src.simulation.config import RNEConfig

    config = RNEConfig(family_a="mistral", family_b="llama", condition="A")
    summary = RNERunner().run_session(config)
    # → writes data/study1/{session_id}/game.jsonl + summary.json + metadata.json
    # → returns summary dict with M1–M4, total_cost_usd, etc.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.simulation.config import RNEConfig
from src.simulation.logger import GameLogger
from src.simulation.llm_router import call_llm, strip_md, _FAMILY_MODEL
from src.prompts.rne_prompts import build_system_prompt, build_round_messages, parse_rne_response

# ---------------------------------------------------------------------------
# Resource value table (§6.3)
# ---------------------------------------------------------------------------
RESOURCE_VALUES: dict[str, int] = {
    "W": 1,  # Wood
    "S": 1,  # Stone
    "G": 2,  # Grain
    "C": 2,  # Cloth
}

# Starting endowments (asymmetric across agents, symmetric within)
_INITIAL_ENDOWMENT: dict[str, dict[str, int]] = {
    "a0": {"W": 5, "S": 5, "G": 0, "C": 0},
    "a1": {"W": 0, "S": 0, "G": 5, "C": 5},
}

# Data directory root (relative to repo root)
_DATA_ROOT = Path("data/study1")


# ---------------------------------------------------------------------------
# Prompt builders (minimal — full prompt architecture is S02's job)
# These are intentionally simple placeholders that will be replaced by
# src/prompts/rne_prompts.py in S02.  They produce valid JSON prompts now.
# ---------------------------------------------------------------------------

def _system_prompt(config: RNEConfig, agent_id: str) -> str:
    """Static system prompt — will be replaced by rne_prompts.py in S02."""
    opponent = "B" if agent_id == "a0" else "A"
    your_resources = "Wood (W) and Stone (S)" if agent_id == "a0" else "Grain (G) and Cloth (C)"
    their_resources = "Grain (G) and Cloth (C)" if agent_id == "a0" else "Wood (W) and Stone (S)"
    framing_line = {
        "neutral":   "You are Agent A exchanging resources with Agent B to maximize your total value.",
        "social":    "You are a trader in a marketplace. You and your partner both benefit from good trades.",
        "strategic": "You are a strategic resource trader. Maximize value; exploit inefficiencies.",
    }[config.prompt_framing]
    return (
        f"{framing_line}\n"
        f"The game runs for {config.rounds} rounds.\n\n"
        f"RESOURCES: You hold {your_resources}. "
        f"Agent {opponent} holds {their_resources}.\n"
        f"EXCHANGE: Each round you may propose a trade or pass.\n"
        f"DECAY: {int(config.decay_rate * 100)}% of your resources decay each round. Trade or lose.\n"
        f"GOAL: End with maximum total resource value. W=1pt, S=1pt, G=2pt, C=2pt.\n"
        f"OUTPUT: Respond ONLY with valid JSON:\n"
        f'{{"action": "propose|pass", "give": {{"RESOURCE": qty}}, "want": {{"RESOURCE": qty}}, "note": "optional"}}\n'
        f'If passing: {{"action": "pass"}}'
    )


def _respond_prompt(proposal: dict, agent_id: str) -> str:
    """Prompt asking agent to accept or reject a specific proposal."""
    return (
        f"Agent {'B' if agent_id == 'a0' else 'A'} proposed: {json.dumps(proposal)}\n"
        f"Respond ONLY with valid JSON: "
        '{"action": "accept"} or {"action": "reject"}'
    )


def _build_round_messages(
    config: RNEConfig,
    agent_id: str,
    round_num: int,
    inventory: dict[str, int],
    history: list[str],
    disclosure_family: str | None,
    system_prompt: str | None = None,  # kept for signature compat; ignored — public fn rebuilds
) -> list[dict]:
    """Build the message list for an action call.

    Delegates to the public build_round_messages() from src.prompts.rne_prompts.
    The system_prompt kwarg is accepted for backward compatibility but ignored:
    build_round_messages calls the LRU-cached build_system_prompt internally.

    Args:
        config:            Session config.
        agent_id:          "a0" or "a1".
        round_num:         Current round number.
        inventory:         Agent's current inventory.
        history:           Round-outcome history strings.
        disclosure_family: Opponent family to disclose (None = blind).
        system_prompt:     Ignored (kept for backward compat).
    """
    return build_round_messages(
        config=config,
        round_num=round_num,
        agent_id=agent_id,
        inventory=inventory,
        history=history,
        opponent_family=disclosure_family,
    )


# ---------------------------------------------------------------------------
# Action parsing
# ---------------------------------------------------------------------------

def _parse_action(raw: str) -> dict | None:
    """Parse an agent action JSON using the tolerant 4-strategy parser.

    Delegates to parse_rne_response for JSON extraction, then validates that
    the resulting dict contains a known action type.

    Returns None on failure or unknown action.
    """
    d = parse_rne_response(raw or "")
    if d is None:
        return None
    action = d.get("action", "").lower()
    if action not in {"propose", "pass", "accept", "reject"}:
        return None
    return d


# ---------------------------------------------------------------------------
# Trade compatibility
# ---------------------------------------------------------------------------

def _proposals_compatible(p_a: dict, p_b: dict) -> bool:
    """Return True if both agents proposed mutually satisfying terms.

    Compatible = A's want matches B's give AND B's want matches A's give,
    with sufficient quantities.  An exact match is accepted; partial is not.
    """
    try:
        a_give = p_a.get("give", {})
        a_want = p_a.get("want", {})
        b_give = p_b.get("give", {})
        b_want = p_b.get("want", {})

        # A wants what B gives, B wants what A gives
        for resource, qty in a_want.items():
            if b_give.get(resource, 0) < qty:
                return False
        for resource, qty in b_want.items():
            if a_give.get(resource, 0) < qty:
                return False
        return bool(a_give or a_want)  # must actually exchange something
    except (AttributeError, TypeError):
        return False


def _execute_trade(
    inv_a: dict[str, int],
    inv_b: dict[str, int],
    give_a: dict[str, int],
    want_a: dict[str, int],
) -> tuple[dict[str, int], dict[str, int]]:
    """Apply a trade: A gives give_a and receives want_a.  Returns new inventories."""
    new_a = dict(inv_a)
    new_b = dict(inv_b)
    for resource, qty in give_a.items():
        new_a[resource] = max(0, new_a.get(resource, 0) - qty)
        new_b[resource] = new_b.get(resource, 0) + qty
    for resource, qty in want_a.items():
        new_b[resource] = max(0, new_b.get(resource, 0) - qty)
        new_a[resource] = new_a.get(resource, 0) + qty
    return new_a, new_b


def _apply_decay(
    inventory: dict[str, int], decay_rate: float
) -> dict[str, int]:
    """Apply per-resource decay: int(qty * (1 - decay_rate))."""
    return {k: int(v * (1.0 - decay_rate)) for k, v in inventory.items()}


def _inventory_value(inventory: dict[str, int]) -> int:
    """Total resource value using RESOURCE_VALUES table."""
    return sum(RESOURCE_VALUES.get(k, 0) * v for k, v in inventory.items())


# ---------------------------------------------------------------------------
# M1–M4 computation
# ---------------------------------------------------------------------------

def _compute_metrics(
    completed_trades: int,
    total_rounds: int,
    trade_log: list[dict],   # [{round, give_a, want_a, executed}]
    perturbation_round: int,
    action_log: list[dict],  # [{round, agent_id, action_type}]
) -> dict[str, Any]:
    """Compute M1–M4 from raw session data."""

    # M1: cooperation rate
    m1 = completed_trades / total_rounds if total_rounds > 0 else 0.0

    # M2: exploitation delta (mean signed resource-value advantage per completed trade)
    # Positive = agent_a extracted more value than it gave in completed trades.
    advantages = []
    for t in trade_log:
        if not t["executed"]:
            continue
        give_val = sum(RESOURCE_VALUES.get(k, 0) * v for k, v in t["give_a"].items())
        want_val = sum(RESOURCE_VALUES.get(k, 0) * v for k, v in t["want_a"].items())
        advantages.append(want_val - give_val)  # positive = a gained more than it gave
    m2 = sum(advantages) / len(advantages) if advantages else 0.0

    # Helper: 5-round rolling cooperation rate ending at round r (inclusive)
    def _rolling_m1(through_round: int, window: int = 5) -> float:
        start = max(1, through_round - window + 1)
        trades_in_window = sum(
            1 for t in trade_log
            if start <= t["round"] <= through_round and t["executed"]
        )
        actual_window = min(window, through_round)
        return trades_in_window / actual_window if actual_window > 0 else 0.0

    # Pre-perturbation rolling M1 (last 5 rounds before perturbation)
    pre_m1 = _rolling_m1(perturbation_round - 1)

    # Pre-perturbation modal action for agent_a (to detect change)
    pre_actions_a = [
        e["action_type"] for e in action_log
        if e["agent_id"] == "a0" and e["round"] < perturbation_round
    ]
    modal_action_a = max(set(pre_actions_a), key=pre_actions_a.count) if pre_actions_a else None

    # M3: first round post-perturbation where a0's action_type differs from modal pre-action
    m3: int | None = None
    if modal_action_a is not None:
        for e in action_log:
            if e["agent_id"] == "a0" and e["round"] > perturbation_round:
                if e["action_type"] != modal_action_a:
                    m3 = e["round"] - perturbation_round  # lag in rounds
                    break

    # M4: rounds until post-perturbation rolling-M1 recovers to within 0.10 of pre_m1
    m4: int | None = None
    for r in range(perturbation_round + 1, total_rounds + 1):
        post_m1 = _rolling_m1(r)
        if abs(post_m1 - pre_m1) <= 0.10:
            m4 = r - perturbation_round
            break

    return {"M1": round(m1, 4), "M2": round(m2, 4), "M3": m3, "M4": m4}


# ---------------------------------------------------------------------------
# RNERunner
# ---------------------------------------------------------------------------

class RNERunner:
    """Runs one RNE session end-to-end.

    Usage::

        runner = RNERunner(data_root=Path("data/study1"))
        summary = runner.run_session(config)
    """

    def __init__(self, data_root: Path = _DATA_ROOT) -> None:
        self.data_root = data_root

    def run_session(
        self,
        config: RNEConfig,
        mock_response: str | None = None,
    ) -> dict[str, Any]:
        """Run a complete RNE session.

        Args:
            config:         Validated RNEConfig for this session.
            mock_response:  If set, all LLM calls return this string (zero cost,
                            no API calls).  Used for testing.

        Returns:
            Summary dict with M1–M4, total_cost_usd, and bookkeeping fields.
            Identical to what is written to summary.json.
        """
        session_dir = self.data_root / config.session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        logger = GameLogger(config.session_id, session_dir)
        start_time = time.monotonic()
        total_cost: float = 0.0

        # Inventories — reset each session
        inv: dict[str, dict[str, int]] = {
            "a0": dict(_INITIAL_ENDOWMENT["a0"]),
            "a1": dict(_INITIAL_ENDOWMENT["a1"]),
        }

        # Tracking structures for metrics
        completed_trades: int = 0
        trade_log: list[dict] = []
        action_log: list[dict] = []
        parse_failure_count: int = 0
        history_a0: list[str] = []
        history_a1: list[str] = []

        # Disclosure: which family does each agent see?
        opponent_family_for_a0 = config.family_b if config.disclosure == "disclosed" else None
        opponent_family_for_a1 = config.family_a if config.disclosure == "disclosed" else None

        # Build system prompt once at session start (cached across calls).
        # This is the static prefix that every round reuses — calling
        # build_system_prompt here ensures it is invoked exactly once per
        # session and the cached string is threaded through every call_llm
        # call for the duration of the session.
        session_system_prompt = build_system_prompt(config.condition, config.prompt_framing)

        logger.log(
            "game_start",
            family_a=config.family_a,
            family_b=config.family_b,
            condition=config.condition,
            disclosure=config.disclosure,
            framing=config.prompt_framing,
            rounds=config.rounds,
        )

        try:
            for round_num in range(1, config.rounds + 1):
                logger.log("round_start", round=round_num)

                # --- Perturbation event (fires exactly once at perturbation_round) ---
                if round_num == config.perturbation_round:
                    # Classify pre-perturbation: were trades happening more than 50% of the time?
                    pre_trades = sum(1 for t in trade_log if t["executed"])
                    pre_rounds = round_num - 1
                    pre_rate = pre_trades / pre_rounds if pre_rounds > 0 else 0.0
                    ptype = "cooperative_to_defective" if pre_rate >= 0.5 else "defective_to_cooperative"
                    logger.log("perturbation", round=round_num, type=ptype)

                # --- Simultaneous action collection ---
                msgs_a0 = _build_round_messages(
                    config, "a0", round_num, inv["a0"], history_a0, opponent_family_for_a0,
                    system_prompt=session_system_prompt,
                )
                msgs_a1 = _build_round_messages(
                    config, "a1", round_num, inv["a1"], history_a1, opponent_family_for_a1,
                    system_prompt=session_system_prompt,
                )

                r_a0 = call_llm(config.family_a, msgs_a0, mock_response=mock_response)
                total_cost += (r_a0._hidden_params.get("response_cost") or 0.0)
                raw_a0 = strip_md(r_a0.choices[0].message.content or "")
                action_a0 = _parse_action(raw_a0)
                if action_a0 is None:
                    parse_failure_count += 1
                    logger.log("parse_failure", round=round_num, agent="a0", raw=raw_a0[:200])
                    action_a0 = {"action": "pass"}

                r_a1 = call_llm(config.family_b, msgs_a1, mock_response=mock_response)
                total_cost += (r_a1._hidden_params.get("response_cost") or 0.0)
                raw_a1 = strip_md(r_a1.choices[0].message.content or "")
                action_a1 = _parse_action(raw_a1)
                if action_a1 is None:
                    parse_failure_count += 1
                    logger.log("parse_failure", round=round_num, agent="a1", raw=raw_a1[:200])
                    action_a1 = {"action": "pass"}

                # Log action types for M3 computation
                action_log.append({"round": round_num, "agent_id": "a0", "action_type": action_a0.get("action", "pass")})
                action_log.append({"round": round_num, "agent_id": "a1", "action_type": action_a1.get("action", "pass")})

                logger.log(
                    "proposal",
                    round=round_num,
                    agent_a=action_a0,
                    agent_b=action_a1,
                )

                # --- Trade resolution ---
                trade_executed = False
                give_a: dict[str, int] = {}
                want_a: dict[str, int] = {}

                a0_proposes = action_a0.get("action") == "propose"
                a1_proposes = action_a1.get("action") == "propose"

                if a0_proposes and a1_proposes:
                    # Both proposed — check direct compatibility
                    if _proposals_compatible(action_a0, action_a1):
                        give_a = action_a0.get("give", {})
                        want_a = action_a0.get("want", {})
                        trade_executed = True

                elif a0_proposes and not a1_proposes:
                    # a0 proposed, a1 passed → give a1 a respond call
                    respond_msgs = [
                        {"role": "system", "content": session_system_prompt},
                        {"role": "user", "content": _respond_prompt(action_a0, "a1")},
                    ]
                    r_resp = call_llm(config.family_b, respond_msgs, mock_response=mock_response)
                    total_cost += (r_resp._hidden_params.get("response_cost") or 0.0)
                    raw_resp = strip_md(r_resp.choices[0].message.content or "")
                    resp_action = _parse_action(raw_resp)
                    if resp_action is None:
                        parse_failure_count += 1
                        logger.log("parse_failure", round=round_num, agent="a1_respond", raw=raw_resp[:200])
                        resp_action = {"action": "reject"}

                    logger.log("respond", round=round_num, agent="a1", response=resp_action)

                    if resp_action.get("action") == "accept":
                        give_a = action_a0.get("give", {})
                        want_a = action_a0.get("want", {})
                        trade_executed = True

                elif a1_proposes and not a0_proposes:
                    # a1 proposed, a0 passed → give a0 a respond call
                    respond_msgs = [
                        {"role": "system", "content": session_system_prompt},
                        {"role": "user", "content": _respond_prompt(action_a1, "a0")},
                    ]
                    r_resp = call_llm(config.family_a, respond_msgs, mock_response=mock_response)
                    total_cost += (r_resp._hidden_params.get("response_cost") or 0.0)
                    raw_resp = strip_md(r_resp.choices[0].message.content or "")
                    resp_action = _parse_action(raw_resp)
                    if resp_action is None:
                        parse_failure_count += 1
                        logger.log("parse_failure", round=round_num, agent="a0_respond", raw=raw_resp[:200])
                        resp_action = {"action": "reject"}

                    logger.log("respond", round=round_num, agent="a0", response=resp_action)

                    if resp_action.get("action") == "accept":
                        # a1 gave a1's give, a0 receives a1's give and surrenders a1's want
                        give_a = action_a1.get("want", {})   # a0 gives what a1 wants
                        want_a = action_a1.get("give", {})   # a0 gets what a1 gives
                        trade_executed = True

                # Execute trade if agreed
                if trade_executed:
                    # Validate sufficient inventory before executing
                    can_execute = all(
                        inv["a0"].get(k, 0) >= v for k, v in give_a.items()
                    ) and all(
                        inv["a1"].get(k, 0) >= v for k, v in want_a.items()
                    )
                    if can_execute:
                        inv["a0"], inv["a1"] = _execute_trade(inv["a0"], inv["a1"], give_a, want_a)
                        completed_trades += 1
                    else:
                        trade_executed = False  # insufficient inventory — void the trade

                trade_log.append({
                    "round": round_num,
                    "executed": trade_executed,
                    "give_a": give_a,
                    "want_a": want_a,
                })

                logger.log(
                    "trade_result",
                    round=round_num,
                    accepted=trade_executed,
                    give_a=give_a,
                    want_a=want_a,
                )

                # --- Decay (after settlement, before round_end) ---
                inv["a0"] = _apply_decay(inv["a0"], config.decay_rate)
                inv["a1"] = _apply_decay(inv["a1"], config.decay_rate)

                logger.log(
                    "decay",
                    round=round_num,
                    inventories={
                        "a0": dict(inv["a0"]),
                        "a1": dict(inv["a1"]),
                    },
                )

                # --- round_end (one line per agent, per R007 JSONL schema) ---
                logger.log(
                    "round_end",
                    round=round_num,
                    agent_id="a0",
                    family=config.family_a,
                    inventory=dict(inv["a0"]),
                    inventory_value=_inventory_value(inv["a0"]),
                    trade_executed=trade_executed,
                )
                logger.log(
                    "round_end",
                    round=round_num,
                    agent_id="a1",
                    family=config.family_b,
                    inventory=dict(inv["a1"]),
                    inventory_value=_inventory_value(inv["a1"]),
                    trade_executed=trade_executed,
                )

                # Update history summaries
                outcome = "traded" if trade_executed else "no trade"
                history_a0.append(f"r{round_num}: {outcome}")
                history_a1.append(f"r{round_num}: {outcome}")

        finally:
            # game_end always written even on crash
            logger.log(
                "game_end",
                total_rounds=config.rounds,
                completed_trades=completed_trades,
                total_cost_usd=total_cost,
                final_inventory_a0=dict(inv["a0"]),
                final_inventory_a1=dict(inv["a1"]),
                parse_failure_count=parse_failure_count,
            )
            logger.flush()

        # --- Compute metrics ---
        metrics = _compute_metrics(
            completed_trades=completed_trades,
            total_rounds=config.rounds,
            trade_log=trade_log,
            perturbation_round=config.perturbation_round,
            action_log=action_log,
        )

        wall_clock = time.monotonic() - start_time

        summary = {
            "session_id": config.session_id,
            "family_a": config.family_a,
            "family_b": config.family_b,
            "condition": config.condition,
            "disclosure": config.disclosure,
            "framing": config.prompt_framing,
            "cooperation_rate": metrics["M1"],   # M1 — primary DV
            "exploitation_delta": metrics["M2"],  # M2
            "adaptation_lag": metrics["M3"],      # M3
            "betrayal_recovery": metrics["M4"],   # M4
            "total_cost_usd": total_cost,
            "total_rounds": config.rounds,
            "completed_trades": completed_trades,
            "parse_failure_count": parse_failure_count,
        }

        metadata = {
            **config.model_dump(),
            "wall_clock_seconds": round(wall_clock, 2),
        }

        (session_dir / "summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
        (session_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )

        return summary


# ---------------------------------------------------------------------------
# Inline smoke test — run with: python src/simulation/rne_game.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import tempfile

    MOCK = '{"action": "propose", "give": {"W": 1}, "want": {"G": 1}}'

    # 5-round test with perturbation_round=3 (within the 5-round window)
    with tempfile.TemporaryDirectory() as tmp:
        cfg = RNEConfig(
            family_a="mistral",
            family_b="llama",
            condition="A",
            rounds=5,
            perturbation_round=3,
        )
        runner = RNERunner(data_root=Path(tmp) / "study1")
        summary = runner.run_session(cfg, mock_response=MOCK)

        # Verify summary.json was written
        session_dir = Path(tmp) / "study1" / cfg.session_id
        assert (session_dir / "summary.json").exists(), "summary.json missing"
        assert (session_dir / "metadata.json").exists(), "metadata.json missing"
        assert (session_dir / "game.jsonl").exists(), "game.jsonl missing"

        # Verify decay: after round 1 with mock propose+propose (compatible?),
        # check that inventory doesn't remain at 5 (decay must have fired).
        lines = [
            json.loads(l)
            for l in (session_dir / "game.jsonl").read_text().splitlines()
            if l.strip()
        ]
        round_end_lines = [l for l in lines if l["event"] == "round_end"]
        assert len(round_end_lines) == 10, f"Expected 10 round_end lines (5 rounds × 2 agents), got {len(round_end_lines)}"

        # Perturbation event must appear exactly once
        perturb_lines = [l for l in lines if l["event"] == "perturbation"]
        assert len(perturb_lines) == 1, f"Expected exactly 1 perturbation event, got {len(perturb_lines)}"
        assert perturb_lines[0]["round"] == 3, f"Perturbation at wrong round: {perturb_lines[0]['round']}"

        # Verify decay was applied: after round 1, a0's W inventory must be < 5
        # (even if no trade happened, decay applies)
        r1_a0 = next(l for l in round_end_lines if l["round"] == 1 and l["agent_id"] == "a0")
        assert r1_a0["inventory"].get("W", 5) < 5 or r1_a0["inventory"].get("G", 0) > 0, \
            "Decay not applied or inventory incorrect after round 1"

        # M1 in [0, 1]
        assert 0.0 <= summary["cooperation_rate"] <= 1.0, f"M1 out of range: {summary['cooperation_rate']}"

        # total_cost is float
        assert isinstance(summary["total_cost_usd"], float), "total_cost_usd is not float"

        print(f"smoke: ok  (M1={summary['cooperation_rate']:.2f}, cost=${summary['total_cost_usd']:.4f})")
