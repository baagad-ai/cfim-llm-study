"""Agent action prompt builder for act() LLM calls.

Public API:
    build_act_messages(agent_id, model_family, round_num, inventory, vp,
                       buildings_built, all_agents_vp, memory,
                       buildings_config) -> list[dict]

Token target: ≤108 tok (chars//4 estimate).
System message is fully static — no agent_id, round, or inventory values.
User message carries all dynamic state as a compact 2–3 line tail.
"""

from src.prompts.building_decision import format_building_options
from src.prompts.json_utils import format_inventory


def _build_system(buildings_config: dict) -> str:
    """Build the static system message for agent_action calls.

    Contains: game overview, rules, building options, JSON schema.
    Must NOT contain agent_id, round number, or any inventory value.
    """
    building_str = format_building_options(buildings_config) if buildings_config else ""
    building_line = f"Buildings: {building_str}. " if building_str else ""
    return (
        "You play Trade Island. Each round: trade, build, or hoard. "
        "Goal: most VP wins. "
        f"{building_line}"
        "JSON: {\"action_type\":\"trade\"|\"build\"|\"hoard\","
        "\"target\":str|null,\"give\":{res:qty}|null,"
        "\"want\":{res:qty}|null,\"building\":str|null}"
    )


def build_act_messages(
    agent_id: str,
    model_family: str,  # reserved for future per-family prompt variants
    round_num: int,
    inventory: dict[str, int],
    vp: int,
    buildings_built: list[str],
    all_agents_vp: dict[str, int],
    memory: list[str],
    buildings_config: dict,
) -> list[dict]:
    """Build chat messages for an act() LLM call.

    System message: static game rules + building options + JSON schema.
                    Identical for every agent in every round (cache-able).
    User message:   compact dynamic tail — round, identity, inventory, scores.

    Args:
        agent_id:        This agent's ID, e.g. "a0".
        model_family:    Family name — reserved, not used in prompt text.
        round_num:       Current round number (1-indexed).
        inventory:       Current resource holdings.
        vp:              This agent's current VP.
        buildings_built: Building names this agent has already constructed.
        all_agents_vp:   {agent_id: vp} for all agents (leaderboard).
        memory:          Agent's reflection history (last 3 used).
        buildings_config: Buildings dict from game config.

    Returns:
        [system_message_dict, user_message_dict]
    """
    system = _build_system(buildings_config)

    # VP leaderboard — compact "a0:6 a1:3 a2:3" format.
    scores = " ".join(f"{aid}:{v}" for aid, v in all_agents_vp.items())

    # Last 3 memory entries if any.
    mem_line = ""
    if memory:
        recent = memory[-3:]
        mem_line = " Mem: " + "; ".join(recent)

    built_line = f" Built:{buildings_built}" if buildings_built else ""

    user = (
        f"R{round_num}. You:{agent_id}. Inv:{format_inventory(inventory)}. "
        f"VP:{vp}. Scores:{scores}.{built_line}{mem_line} Act?"
    )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
