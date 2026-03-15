"""GM prompt builders for trade validation LLM calls.

Public API:
    build_gm_messages(round_num, proposals) -> list[dict]
    build_simple_gm_messages(proposals) -> list[dict]

Both functions return a full messages list (not the raw prompt string).
Prompt text extracted verbatim from gm.py — no behavioral changes in this module.
The two-attempt retry logic stays in gm.py; only the prompt text lives here.
"""


def _build_gm_prompt(round_num: int, proposals: list[dict]) -> str:
    """Build the batch validation prompt for the GM LLM.

    Verbatim extraction from gm._build_gm_prompt.
    """
    lines = [
        f"Round {round_num}. Validate these trade proposals.",
        "For each, check: is the trade fair and legal given Trade Island rules?",
        "Proposals:",
    ]
    for i, p in enumerate(proposals):
        lines.append(
            f"  [{i}] {p.get('proposer')} gives {p.get('give')} "
            f"to {p.get('responder')} for {p.get('want')}. "
            f"Responder accepted: {p.get('accepted')}."
        )
    lines.append(
        'Respond with JSON: {"verdicts": [{"idx": 0, "valid": true, "reason": "..."}, ...]}'
    )
    return "\n".join(lines)


def _build_simple_gm_prompt(proposals: list[dict]) -> str:
    """Simplified retry prompt for GM when first parse fails.

    Verbatim extraction from gm._build_simple_gm_prompt.
    """
    lines = ["Validate trades. JSON only."]
    for i, p in enumerate(proposals):
        lines.append(f"Trade {i}: proposer={p.get('proposer')}, responder={p.get('responder')}")
    lines.append('{"verdicts":[{"idx":0,"valid":true,"reason":"ok"}]}')
    return "\n".join(lines)


def build_gm_messages(round_num: int, proposals: list[dict]) -> list[dict]:
    """Build the full messages list for the primary GM validation call.

    Returns:
        [system_message_dict, user_message_dict]
    """
    return [
        {
            "role": "system",
            "content": "You are the Game Master for Trade Island. Validate trades. Respond ONLY with JSON.",
        },
        {
            "role": "user",
            "content": _build_gm_prompt(round_num, proposals),
        },
    ]


def build_simple_gm_messages(proposals: list[dict]) -> list[dict]:
    """Build the full messages list for the simplified GM retry call.

    Returns:
        [system_message_dict, user_message_dict]
    """
    return [
        {
            "role": "system",
            "content": "You are a trade validator. Respond ONLY with JSON.",
        },
        {
            "role": "user",
            "content": _build_simple_gm_prompt(proposals),
        },
    ]
