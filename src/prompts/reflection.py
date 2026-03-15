"""Reflection prompt builder for reflect() LLM calls.

Public API:
    build_reflect_messages(agent_id, round_num, inventory, vp,
                           memory) -> list[dict]

Token target: 120–180 tok (chars//4 estimate).
Does NOT dump full game_state dict — only agent-owned state is included.
"""

from src.prompts.json_utils import format_inventory


_SYSTEM = (
    "You play Trade Island. Reflect on your strategy so far. "
    "Write 2–3 sentences: what is working, what to change next."
)


def build_reflect_messages(
    agent_id: str,
    round_num: int,
    inventory: dict[str, int],
    vp: int,
    memory: list[str],
) -> list[dict]:
    """Build chat messages for a reflect() LLM call.

    System message: static reflection instruction (cache-able).
    User message:   round, agent ID, inventory, VP, last 3 memory entries.
                    No full game_state dict — keeps token count in budget.

    Args:
        agent_id:   This agent's ID.
        round_num:  The round just completed (1-indexed).
        inventory:  Current resource holdings.
        vp:         This agent's current VP.
        memory:     Agent's reflection history (last 3 used).

    Returns:
        [system_message_dict, user_message_dict]
    """
    past = ""
    if memory:
        recent = memory[-3:]
        past = " Past: " + "; ".join(f"[{m}]" for m in recent)

    user = (
        f"R{round_num} done. You:{agent_id}. "
        f"Inv:{format_inventory(inventory)}. VP:{vp}.{past} Reflect."
    )

    return [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": user},
    ]
