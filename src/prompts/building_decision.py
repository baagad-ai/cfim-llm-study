"""Building options formatter for agent_action system message injection.

Public API:
    format_building_options(buildings) -> str

This module contains only helper functions — no LLM calls.
Used by agent_action.py to render the building list in the static system message.
"""

from src.prompts.json_utils import _RESOURCE_INITIALS, _RESOURCE_ORDER


def format_building_options(buildings: dict) -> str:
    """Render building list in compact format for system message injection.

    Example output: "Market(W2 S2→3vp) Granary(G3 W1→3vp) Tower(S2 C2→3vp)"

    Args:
        buildings: Dict mapping building name to {"cost": {resource: qty}, "vp": int}.

    Returns:
        Single-line compact string. Empty string if buildings is empty/None.
    """
    if not buildings:
        return ""

    parts = []
    for name, spec in buildings.items():
        cost: dict = spec.get("cost", {})
        vp: int = spec.get("vp", 0)

        # Render cost in resource-initial order (same ordering as format_inventory).
        cost_parts = []
        for resource in _RESOURCE_ORDER:
            qty = cost.get(resource, 0)
            if qty:
                initial = _RESOURCE_INITIALS[resource]
                cost_parts.append(f"{initial}{qty}")
        # Include any resources not in the standard order (forward-compat).
        for resource, qty in cost.items():
            if resource not in _RESOURCE_ORDER and qty:
                cost_parts.append(f"{resource[:1].upper()}{qty}")

        cost_str = " ".join(cost_parts)
        parts.append(f"{name}({cost_str}→{vp}vp)")

    return " ".join(parts)
