"""GameConfig — Pydantic model + named-config factory.

This is the schema contract that every other S02 module references.
Lock field names here; do not drift downstream.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Standard buildings (equal VP per D006)
# ---------------------------------------------------------------------------
_STANDARD_BUILDINGS: dict[str, dict[str, Any]] = {
    "Market": {"cost": {"wood": 2, "stone": 2}, "vp": 3},
    "Granary": {"cost": {"grain": 3, "wood": 1}, "vp": 3},
    "Tower": {"cost": {"stone": 2, "clay": 2}, "vp": 3},
}

# ---------------------------------------------------------------------------
# Model family → (model_string, provider_kwargs) registry
# ---------------------------------------------------------------------------
# Maps short family names (used in from_name / pairwise strings) to the
# exact litellm model string and any provider-level kwargs.
_MODEL_REGISTRY: dict[str, dict[str, Any]] = {
    "mistral": {
        "model_string": "mistral/mistral-small-2506",
        "provider_kwargs": {
            "response_format": {"type": "json_object"},
            "max_tokens": 150,
        },
    },
    "llama": {
        "model_string": "groq/llama-3.3-70b-versatile",
        "provider_kwargs": {
            "response_format": {"type": "json_object"},
            "max_tokens": 150,
        },
    },
    "deepseek": {
        "model_string": "openrouter/deepseek/deepseek-chat",
        "provider_kwargs": {
            "response_format": {"type": "json_object"},
            "max_tokens": 150,
        },
    },
    "gemini": {
        "model_string": "gemini/gemini-2.5-flash",
        "provider_kwargs": {
            "max_tokens": 200,
        },
    },
}

_DEFAULT_GM_MODEL = "mistral/mistral-small-2506"


def _make_agent_entry(agent_id: str, family: str) -> dict[str, Any]:
    """Build one agent_models entry from a family name."""
    reg = _MODEL_REGISTRY[family]
    return {
        "agent_id": agent_id,
        "model_family": family,
        "model_string": reg["model_string"],
        "provider_kwargs": reg["provider_kwargs"],
    }


class GameConfig(BaseModel):
    """Full configuration for one game run.

    Fields are the schema contract — do not rename without updating all
    downstream modules (engine, logger, analysis).
    """

    config_name: str
    num_agents: int = 6
    num_rounds: int = 25
    resources: list[str] = Field(
        default_factory=lambda: ["wood", "stone", "grain", "clay", "fiber"]
    )
    buildings: dict[str, dict[str, Any]] = Field(
        default_factory=lambda: dict(_STANDARD_BUILDINGS)
    )
    hunger_rate: int = 1  # grain consumed per agent per round
    gm_model: str = _DEFAULT_GM_MODEL
    agent_models: list[dict[str, Any]] = Field(default_factory=list)

    # ------------------------------------------------------------------
    # Named-config factory
    # ------------------------------------------------------------------

    @classmethod
    def from_name(cls, name: str) -> "GameConfig":
        """Return a GameConfig for a registered config name.

        Supported names:
          - "mistral-mono"          all 6 agents on mistral-small-2506
          - "phase0"                placeholder — same as mistral-mono for now
          - "pairwise-{A}-{B}"      3 agents of family A + 3 agents of family B
                                    e.g. "pairwise-llama-mistral"
        """
        if name == "mistral-mono":
            return cls._mistral_mono()
        if name == "phase0":
            # TBD mix — placeholder using mistral-mono until phase0 model
            # selection is finalised in S03.
            return cls._mistral_mono(config_name="phase0")
        if name.startswith("pairwise-"):
            return cls._pairwise(name)
        raise ValueError(
            f"Unknown config name: {name!r}. "
            "Valid names: 'mistral-mono', 'phase0', 'pairwise-{{A}}-{{B}}'"
        )

    # ------------------------------------------------------------------
    # Private builders
    # ------------------------------------------------------------------

    @classmethod
    def _mistral_mono(cls, config_name: str = "mistral-mono") -> "GameConfig":
        agents = [
            _make_agent_entry(f"a{i}", "mistral") for i in range(6)
        ]
        return cls(
            config_name=config_name,
            num_agents=6,
            num_rounds=25,
            gm_model=_DEFAULT_GM_MODEL,
            agent_models=agents,
        )

    @classmethod
    def _pairwise(cls, name: str) -> "GameConfig":
        """Parse 'pairwise-{A}-{B}' and build 3A + 3B agent list."""
        # name is like "pairwise-llama-mistral"
        # Split off the "pairwise-" prefix then take first and second tokens.
        # Family names in the registry are single words (no hyphens), so
        # split on "-" and pop the first element ("pairwise").
        parts = name.split("-")
        if len(parts) != 3 or parts[0] != "pairwise":
            raise ValueError(
                f"pairwise config name must be 'pairwise-{{A}}-{{B}}', got: {name!r}"
            )
        family_a, family_b = parts[1], parts[2]
        for fam in (family_a, family_b):
            if fam not in _MODEL_REGISTRY:
                raise ValueError(
                    f"Unknown model family {fam!r}. "
                    f"Known families: {list(_MODEL_REGISTRY)}"
                )
        agents = (
            [_make_agent_entry(f"a{i}", family_a) for i in range(3)]
            + [_make_agent_entry(f"a{i + 3}", family_b) for i in range(3)]
        )
        return cls(
            config_name=name,
            num_agents=6,
            num_rounds=25,
            gm_model=_DEFAULT_GM_MODEL,
            agent_models=agents,
        )
