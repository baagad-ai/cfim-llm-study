"""GameConfig — Pydantic model + named-config factory.

This is the schema contract that every other module references.
Lock field names here; do not drift downstream.

Two config classes live here:
  GameConfig  — Trade Island (Study 2 / Harbour) and legacy phase0 calibration runs.
  RNEConfig   — Study 1: Repeated Negotiated Exchange (CFIM primary experiment).

_MODEL_REGISTRY is the single source of truth for all 7 CFIM families.
It must stay in sync with llm_router.py _FAMILY_MODEL / PROVIDER_KWARGS.
The 7 families are: llama, deepseek, gemini, mistral, gpt4o-mini, qwen, phi4.
(Claude Haiku excluded — D004/§3.5 budget constraint.)
"""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Standard buildings for Trade Island / Harbour (equal VP per D006)
# ---------------------------------------------------------------------------
_STANDARD_BUILDINGS: dict[str, dict[str, Any]] = {
    "Market": {"cost": {"wood": 2, "stone": 2}, "vp": 3},
    "Granary": {"cost": {"grain": 3, "wood": 1}, "vp": 3},
    "Tower": {"cost": {"stone": 2, "clay": 2}, "vp": 3},
}

# ---------------------------------------------------------------------------
# Model family registry — authoritative for ALL 7 CFIM Study 1 families.
#
# Sync contract: this dict must match llm_router.py _FAMILY_MODEL and
# PROVIDER_KWARGS exactly.  When adding a family, update all three.
#
# Gemini kwargs reflect D047: response_format=json_object re-enabled now that
# thinking=disabled is confirmed working (D021 superseded).
# ---------------------------------------------------------------------------
_MODEL_REGISTRY: dict[str, dict[str, Any]] = {
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
            "thinking": {"type": "disabled", "budget_tokens": 0},
            "response_format": {"type": "json_object"},  # D047: re-enabled
            "max_tokens": 200,
        },
    },
    "mistral": {
        "model_string": "mistral/mistral-small-2506",
        "provider_kwargs": {
            "response_format": {"type": "json_object"},
            "max_tokens": 150,
        },
    },
    "gpt4o-mini": {
        "model_string": "openai/gpt-4o-mini",
        "provider_kwargs": {
            "response_format": {"type": "json_object"},
            "max_tokens": 150,
        },
    },
    "qwen": {
        "model_string": "together_ai/Qwen/Qwen2.5-72B-Instruct-Turbo",
        "provider_kwargs": {
            "response_format": {"type": "json_object"},
            "max_tokens": 150,
        },
    },
    "phi4": {
        "model_string": "together_ai/microsoft/phi-4",
        "provider_kwargs": {
            "response_format": {"type": "json_object"},
            "max_tokens": 150,
        },
    },
}

# Convenience set for validation — keeps RNEConfig validator in sync automatically.
RNE_FAMILIES: frozenset[str] = frozenset(_MODEL_REGISTRY.keys())

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
          - "{family}-mono"         all 6 agents on one family
                                    family ∈ {llama, deepseek, gemini, mistral,
                                              gpt4o-mini, qwen, phi4}
          - "phase0"                4-family mix: 2×llama + 2×deepseek + 1×gemini + 1×mistral
          - "pairwise-{A}-{B}"      3 agents of family A + 3 agents of family B
                                    e.g. "pairwise-llama-mistral"
        """
        if name == "phase0":
            return cls._mixed_4family()
        if name.endswith("-mono"):
            family = name[: -len("-mono")]
            return cls._mono(family)
        if name.startswith("pairwise-"):
            return cls._pairwise(name)
        valid_monos = sorted(f"{f}-mono" for f in _MODEL_REGISTRY)
        raise ValueError(
            f"Unknown config name: {name!r}. "
            f"Valid mono names: {valid_monos}; "
            "also: 'phase0', 'pairwise-{A}-{B}'"
        )

    # ------------------------------------------------------------------
    # Private builders
    # ------------------------------------------------------------------

    @classmethod
    def _mono(cls, family: str) -> "GameConfig":
        """Build a 6-agent mono config where all agents use the same family."""
        if family not in _MODEL_REGISTRY:
            raise ValueError(
                f"Unknown model family {family!r}. "
                f"Known families: {list(_MODEL_REGISTRY)}"
            )
        agents = [_make_agent_entry(f"a{i}", family) for i in range(6)]
        return cls(
            config_name=f"{family}-mono",
            num_agents=6,
            num_rounds=25,
            gm_model=_DEFAULT_GM_MODEL,
            agent_models=agents,
        )

    @classmethod
    def _mixed_4family(cls) -> "GameConfig":
        """Build the phase0 4-family mix: 2×llama + 2×deepseek + 1×gemini + 1×mistral."""
        agents = [
            _make_agent_entry("a0", "llama"),
            _make_agent_entry("a1", "llama"),
            _make_agent_entry("a2", "deepseek"),
            _make_agent_entry("a3", "deepseek"),
            _make_agent_entry("a4", "gemini"),
            _make_agent_entry("a5", "mistral"),
        ]
        return cls(
            config_name="phase0",
            num_agents=6,
            num_rounds=25,
            gm_model=_DEFAULT_GM_MODEL,
            agent_models=agents,
        )

    @classmethod
    def _pairwise(cls, name: str) -> "GameConfig":
        """Parse 'pairwise-{A}-{B}' and build 3A + 3B agent list.

        Family names may contain hyphens (e.g. 'gpt4o-mini'), so we match
        greedily: try every split position after 'pairwise-' and pick the
        first one where both halves are registered family names.
        """
        prefix = "pairwise-"
        remainder = name[len(prefix):]  # e.g. "llama-gpt4o-mini"
        # Try each possible split position
        families = list(_MODEL_REGISTRY.keys())
        match: tuple[str, str] | None = None
        for fa in families:
            if remainder.startswith(fa + "-"):
                fb = remainder[len(fa) + 1:]
                if fb in _MODEL_REGISTRY:
                    match = (fa, fb)
                    break
        if match is None:
            raise ValueError(
                f"pairwise config {name!r} could not be parsed into two known families. "
                f"Known families: {sorted(_MODEL_REGISTRY)}. "
                "Format: 'pairwise-{A}-{B}' where A and B are family names."
            )
        family_a, family_b = match
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

    @classmethod
    def from_rne(cls, rne: "RNEConfig") -> "GameConfig":
        """Build a GameConfig from an RNEConfig for a 2-agent bilateral game.

        Creates exactly 2 agents: a0 uses family_a, a1 uses family_b.
        Rounds are set from rne.rounds (default 35 for Study 1).

        Args:
            rne: Fully-specified RNEConfig instance.

        Returns:
            GameConfig wired for the RNE 2-agent bilateral game.
        """
        agents = [
            _make_agent_entry("a0", rne.family_a),
            _make_agent_entry("a1", rne.family_b),
        ]
        return cls(
            config_name=f"rne-{rne.family_a}-{rne.family_b}-{rne.condition}",
            num_agents=2,
            num_rounds=rne.rounds,
            gm_model=_DEFAULT_GM_MODEL,
            agent_models=agents,
        )


# ---------------------------------------------------------------------------
# RNEConfig — Study 1: Repeated Negotiated Exchange
# ---------------------------------------------------------------------------

class RNEConfig(BaseModel):
    """Configuration for one Study 1 (RNE) session.

    Fields are locked; downstream engine, logger, and analysis all depend
    on exact field names.  Do not rename without coordinating S01 changes.

    Attributes:
        family_a:           Model family for agent a0.
                            Must be a key in _MODEL_REGISTRY / RNE_FAMILIES.
        family_b:           Model family for agent a1. Same constraint.
        condition:          Experimental condition: A (coordination), B (mixed
                            motive), or C (asymmetric power) — see §3.2.
        disclosure:         Identity disclosure sub-condition per §3.3.
        prompt_framing:     Prompt framing robustness factor per §6.2.
        rounds:             Number of negotiation rounds (default 35, see §8 Q2).
        decay_rate:         Per-round resource decay (default 0.10, see §8 Q3).
        perturbation_round: Round at which opponent strategy switches (default 20).
        session_id:         8-char hex ID auto-generated from UUID4.
    """

    family_a: str
    family_b: str
    condition: Literal["A", "B", "C"]
    disclosure: Literal["blind", "disclosed"] = "blind"
    prompt_framing: Literal["neutral", "social", "strategic"] = "neutral"
    rounds: int = 35
    decay_rate: float = 0.10
    perturbation_round: int = 20
    session_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])

    model_config = {"frozen": False}  # allow post-init mutation if needed

    @field_validator("family_a", "family_b")
    @classmethod
    def _validate_family(cls, v: str) -> str:
        if v not in RNE_FAMILIES:
            raise ValueError(
                f"Unknown model family {v!r}. "
                f"Valid families: {sorted(RNE_FAMILIES)}"
            )
        return v
