"""Trade response prompt builder for respond_to_trade() LLM calls.

Public API:
    build_respond_messages(agent_id, inventory, vp, proposal,
                           buildings_config) -> list[dict]

Token target: ≤72 tok (chars//4 estimate).

D037 fix: system message explicitly frames trades as VP-unlocking moves.
All 115 proposals in the Mistral-mono baseline run were declined (68% pure
LLM declines). The new system message explains that trading unlocks buildings
you can't afford alone, and that counter-proposing beats flat declining.
"""

from src.prompts.json_utils import format_inventory


_SYSTEM = (
    "Trade Island. Trades unlock buildings you can't afford alone — "
    "accept if it gets you closer to a building. "
    "Counter-propose instead of flat declining. "
    "JSON:{\"accepted\":true|false,\"counter\":{res:qty}|null}"
)


def build_respond_messages(
    agent_id: str,
    inventory: dict[str, int],
    vp: int,
    proposal: dict,
    buildings_config: dict,  # reserved for future building-aware framing
) -> list[dict]:
    """Build chat messages for a respond_to_trade() LLM call.

    System message: static VP-unlocking strategic framing + JSON schema.
                    Never varies — fully cache-able.
    User message:   compact identity + inventory + VP + proposal.

    Args:
        agent_id:        This agent's ID, e.g. "a0".
        inventory:       Current resource holdings.
        vp:              This agent's current VP.
        proposal:        Incoming proposal dict with proposer/give/want fields.
        buildings_config: Reserved — not injected yet; available for S04 expansion.

    Returns:
        [system_message_dict, user_message_dict]
    """
    proposer = proposal.get("proposer", "?")
    give = proposal.get("give") or {}
    want = proposal.get("want") or {}

    # Compact give/want: "W1" not {"wood": 1}
    give_str = " ".join(f"{k[0].upper()}{v}" for k, v in give.items()) or "nothing"
    want_str = " ".join(f"{k[0].upper()}{v}" for k, v in want.items()) or "nothing"

    user = (
        f"You:{agent_id}. Inv:{format_inventory(inventory)}. VP:{vp}. "
        f"{proposer} offers {give_str} for {want_str}. Accept?"
    )

    return [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": user},
    ]
