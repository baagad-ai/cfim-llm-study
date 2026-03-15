"""src/prompts — prompt builders and tolerant JSON parser.

Public re-exports from json_utils:
    parse_agent_response  — multi-strategy tolerant parser; returns None on failure
    format_inventory      — compact W2 S3 G4 C1 F0 resource string
    get_completion_kwargs — per-provider kwarg lookup for S04 format-ablation callers
"""

from src.prompts.json_utils import (
    format_inventory,
    get_completion_kwargs,
    parse_agent_response,
)

__all__ = [
    "parse_agent_response",
    "format_inventory",
    "get_completion_kwargs",
]
