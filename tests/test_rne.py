"""Tests for the RNE (Repeated Negotiated Exchange) engine — Study 1.

Running state:
  T01 (Config, Logger, LLM Router): PASSES — RNEConfig, GameLogger, PROVIDER_KWARGS
  T02+ (RNE engine, run_rne.py, metrics): FAIL until implemented

Run: pytest tests/test_rne.py -v
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


# ===========================================================================
# T01: RNEConfig — configuration model
# ===========================================================================

class TestRNEConfig:
    """Verify RNEConfig schema, defaults, and validation."""

    def test_basic_construction(self):
        from src.simulation.config import RNEConfig
        c = RNEConfig(
            family_a="mistral",
            family_b="llama",
            condition="A",
            disclosure="blind",
            prompt_framing="neutral",
        )
        assert c.family_a == "mistral"
        assert c.family_b == "llama"
        assert c.condition == "A"
        assert c.disclosure == "blind"
        assert c.prompt_framing == "neutral"

    def test_defaults(self):
        from src.simulation.config import RNEConfig
        c = RNEConfig(
            family_a="mistral",
            family_b="llama",
            condition="A",
            disclosure="blind",
            prompt_framing="neutral",
        )
        assert c.rounds == 35
        assert c.decay_rate == 0.10
        assert c.perturbation_round == 20

    def test_session_id_auto_generated(self):
        from src.simulation.config import RNEConfig
        c = RNEConfig(
            family_a="mistral",
            family_b="llama",
            condition="A",
            disclosure="blind",
            prompt_framing="neutral",
        )
        assert len(c.session_id) == 8
        # Must be valid hex
        int(c.session_id, 16)

    def test_session_id_unique_per_instance(self):
        from src.simulation.config import RNEConfig
        kwargs = dict(
            family_a="mistral",
            family_b="llama",
            condition="A",
            disclosure="blind",
            prompt_framing="neutral",
        )
        c1 = RNEConfig(**kwargs)
        c2 = RNEConfig(**kwargs)
        assert c1.session_id != c2.session_id

    def test_condition_validation(self):
        from src.simulation.config import RNEConfig
        from pydantic import ValidationError
        # Valid conditions
        for cond in ("A", "B", "C"):
            RNEConfig(
                family_a="mistral", family_b="llama",
                condition=cond, disclosure="blind", prompt_framing="neutral",
            )
        # Invalid condition
        with pytest.raises(ValidationError):
            RNEConfig(
                family_a="mistral", family_b="llama",
                condition="D", disclosure="blind", prompt_framing="neutral",
            )

    def test_disclosure_validation(self):
        from src.simulation.config import RNEConfig
        from pydantic import ValidationError
        for disc in ("blind", "disclosed"):
            RNEConfig(
                family_a="mistral", family_b="llama",
                condition="A", disclosure=disc, prompt_framing="neutral",
            )
        with pytest.raises(ValidationError):
            RNEConfig(
                family_a="mistral", family_b="llama",
                condition="A", disclosure="hidden", prompt_framing="neutral",
            )

    def test_framing_validation(self):
        from src.simulation.config import RNEConfig
        from pydantic import ValidationError
        for framing in ("neutral", "social", "strategic"):
            RNEConfig(
                family_a="mistral", family_b="llama",
                condition="A", disclosure="blind", prompt_framing=framing,
            )
        with pytest.raises(ValidationError):
            RNEConfig(
                family_a="mistral", family_b="llama",
                condition="A", disclosure="blind", prompt_framing="aggressive",
            )

    def test_from_rne_factory(self):
        """GameConfig.from_rne() must build a 2-agent bilateral config."""
        from src.simulation.config import RNEConfig, GameConfig
        rne = RNEConfig(
            family_a="mistral",
            family_b="llama",
            condition="A",
            disclosure="blind",
            prompt_framing="neutral",
        )
        gc = GameConfig.from_rne(rne)
        assert gc.num_agents == 2
        assert gc.num_rounds == 35
        agents = gc.agent_models
        assert len(agents) == 2
        assert agents[0]["agent_id"] == "a0"
        assert agents[0]["model_family"] == "mistral"
        assert agents[1]["agent_id"] == "a1"
        assert agents[1]["model_family"] == "llama"

    def test_family_validation_rejects_unknown(self):
        """RNEConfig must reject family names not in _MODEL_REGISTRY."""
        from src.simulation.config import RNEConfig
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="Unknown model family"):
            RNEConfig(family_a="claude", family_b="llama", condition="A")
        with pytest.raises(ValidationError, match="Unknown model family"):
            RNEConfig(family_a="mistral", family_b="gpt4", condition="A")

    def test_all_seven_families_accepted(self):
        """All 7 CFIM families must be accepted by RNEConfig."""
        from src.simulation.config import RNEConfig, RNE_FAMILIES
        expected = {"llama", "deepseek", "gemini", "mistral", "gpt4o-mini", "qwen", "phi4"}
        assert RNE_FAMILIES == expected
        for fam in expected:
            c = RNEConfig(family_a=fam, family_b="mistral", condition="A")
            assert c.family_a == fam

    def test_from_rne_all_seven_families(self):
        """GameConfig.from_rne() must work for all 7 CFIM families."""
        from src.simulation.config import RNEConfig, GameConfig
        families = ["llama", "deepseek", "gemini", "mistral", "gpt4o-mini", "qwen", "phi4"]
        for fam in families:
            rne = RNEConfig(family_a=fam, family_b="mistral", condition="A")
            gc = GameConfig.from_rne(rne)
            assert gc.agent_models[0]["model_family"] == fam
            assert gc.agent_models[0]["model_string"] != ""

    def test_pairwise_with_hyphenated_family(self):
        """pairwise config must parse correctly when a family name contains a hyphen."""
        from src.simulation.config import GameConfig
        gc = GameConfig.from_name("pairwise-llama-gpt4o-mini")
        assert gc.num_agents == 6
        families_in_config = [a["model_family"] for a in gc.agent_models]
        assert families_in_config[:3] == ["llama", "llama", "llama"]
        assert families_in_config[3:] == ["gpt4o-mini", "gpt4o-mini", "gpt4o-mini"]

    def test_mono_configs_all_seven(self):
        """All 7 {family}-mono configs must resolve without error."""
        from src.simulation.config import GameConfig
        for fam in ["llama", "deepseek", "gemini", "mistral", "gpt4o-mini", "qwen", "phi4"]:
            gc = GameConfig.from_name(f"{fam}-mono")
            assert gc.num_agents == 6
            assert all(a["model_family"] == fam for a in gc.agent_models)

    def test_model_registry_matches_router(self):
        """_MODEL_REGISTRY families must exactly match llm_router PROVIDER_KWARGS keys."""
        from src.simulation.config import _MODEL_REGISTRY
        from src.simulation.llm_router import PROVIDER_KWARGS, _FAMILY_MODEL
        assert set(_MODEL_REGISTRY.keys()) == set(PROVIDER_KWARGS.keys()), (
            f"Registry/PROVIDER_KWARGS mismatch: "
            f"registry={sorted(_MODEL_REGISTRY)}, router={sorted(PROVIDER_KWARGS)}"
        )
        assert set(_MODEL_REGISTRY.keys()) == set(_FAMILY_MODEL.keys()), (
            f"Registry/_FAMILY_MODEL mismatch: "
            f"registry={sorted(_MODEL_REGISTRY)}, router={sorted(_FAMILY_MODEL)}"
        )
        # Spot-check model strings agree
        for fam, entry in _MODEL_REGISTRY.items():
            assert entry["model_string"] == _FAMILY_MODEL[fam], (
                f"{fam}: config model_string {entry['model_string']!r} != "
                f"router {_FAMILY_MODEL[fam]!r}"
            )


# ===========================================================================
# T01: GameLogger — JSONL writer
# ===========================================================================

class TestGameLogger:
    """Verify GameLogger writes line-buffered JSONL to the correct path."""

    def test_log_creates_file(self):
        from src.simulation.logger import GameLogger
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir)
            l = GameLogger("sess001", out)
            l.log("game_start")
            l.close()
            assert (out / "game.jsonl").exists()

    def test_log_writes_valid_json(self):
        from src.simulation.logger import GameLogger
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir)
            l = GameLogger("sess001", out)
            l.log("round_end", round=1, agent="a0")
            l.close()
            line = (out / "game.jsonl").read_text().strip()
            d = json.loads(line)
            assert d["event"] == "round_end"
            assert d["round"] == 1
            assert d["game_id"] == "sess001"
            assert "ts" in d

    def test_log_ts_is_iso8601(self):
        from src.simulation.logger import GameLogger
        from datetime import datetime
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir)
            l = GameLogger("sess001", out)
            l.log("test_event")
            l.close()
            line = (out / "game.jsonl").read_text().strip()
            d = json.loads(line)
            # Should parse as ISO8601 without error
            datetime.fromisoformat(d["ts"])

    def test_line_buffered(self):
        """Each log() call must be immediately readable — buffering=1."""
        from src.simulation.logger import GameLogger
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir)
            l = GameLogger("sess001", out)
            assert l._file.line_buffering, "file must be line-buffered (buffering=1)"
            l.log("round_end", round=1)
            # Read without explicit flush — should be present immediately
            content = (out / "game.jsonl").read_text()
            assert "round_end" in content
            l.close()

    def test_log_round_end_emits_per_agent(self):
        """log_round_end must emit one line per agent with flat fields."""
        from src.simulation.logger import GameLogger
        agents = [
            {"agent_id": "a0", "model_family": "mistral", "vp": 3},
            {"agent_id": "a1", "model_family": "llama", "vp": 6},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir)
            l = GameLogger("sess001", out)
            l.log_round_end(round_num=5, agents=agents)
            l.close()
            lines = (out / "game.jsonl").read_text().strip().split("\n")
            assert len(lines) == 2
            d0 = json.loads(lines[0])
            d1 = json.loads(lines[1])
            assert d0["event"] == "round_end"
            assert d0["agent_id"] == "a0"
            assert d0["model_family"] == "mistral"
            assert d0["vp"] == 3
            assert d0["round"] == 5
            assert d1["agent_id"] == "a1"
            assert d1["vp"] == 6

    def test_log_appends_multiple_events(self):
        """Multiple log() calls produce multiple lines, not overwrites."""
        from src.simulation.logger import GameLogger
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir)
            l = GameLogger("sess001", out)
            l.log("game_start")
            l.log("round_end", round=1)
            l.log("game_end", total_rounds=1)
            l.close()
            lines = (out / "game.jsonl").read_text().strip().split("\n")
            assert len(lines) == 3
            events = [json.loads(ln)["event"] for ln in lines]
            assert events == ["game_start", "round_end", "game_end"]


# ===========================================================================
# T01: PROVIDER_KWARGS and call_llm (llm_router)
# ===========================================================================

class TestProviderKwargs:
    """Verify the 7-provider PROVIDER_KWARGS structure."""

    def test_all_seven_providers_present(self):
        from src.simulation.llm_router import PROVIDER_KWARGS
        required = {"llama", "deepseek", "gemini", "mistral", "gpt4o-mini", "qwen", "phi4"}
        assert required == set(PROVIDER_KWARGS.keys())

    def test_gemini_has_response_format(self):
        """D047 supersedes D021: Gemini now uses json_object (thinking=disabled makes it safe)."""
        from src.simulation.llm_router import PROVIDER_KWARGS
        assert "response_format" in PROVIDER_KWARGS["gemini"]
        assert PROVIDER_KWARGS["gemini"]["response_format"] == {"type": "json_object"}

    def test_gemini_thinking_disabled(self):
        from src.simulation.llm_router import PROVIDER_KWARGS
        g = PROVIDER_KWARGS["gemini"]
        assert "thinking" in g
        assert g["thinking"]["type"] == "disabled"
        assert g["thinking"]["budget_tokens"] == 0

    def test_gemini_max_tokens_200(self):
        from src.simulation.llm_router import PROVIDER_KWARGS
        assert PROVIDER_KWARGS["gemini"]["max_tokens"] == 200

    def test_json_object_providers(self):
        from src.simulation.llm_router import PROVIDER_KWARGS
        for family in ("llama", "deepseek", "mistral", "gpt4o-mini", "qwen", "phi4"):
            kwargs = PROVIDER_KWARGS[family]
            assert "response_format" in kwargs, f"{family} missing response_format"
            assert kwargs["response_format"]["type"] == "json_object"
            assert kwargs["max_tokens"] == 150

    def test_drop_params_set(self):
        import litellm
        import src.simulation.llm_router  # noqa: F401 — triggers module-level drop_params
        assert litellm.drop_params is True


class TestCallLlm:
    """Verify call_llm returns litellm response with correct cost guard."""

    def test_mock_returns_response_object(self):
        from src.simulation.llm_router import call_llm
        r = call_llm(
            "mistral",
            [{"role": "user", "content": "test"}],
            mock_response='{"action":"cooperate"}',
        )
        assert hasattr(r, "choices")
        assert hasattr(r, "_hidden_params")

    def test_mock_cost_is_zero_float(self):
        from src.simulation.llm_router import call_llm
        r = call_llm(
            "mistral",
            [{"role": "user", "content": "test"}],
            mock_response='{"action":"cooperate"}',
        )
        cost = (r._hidden_params.get("response_cost") or 0.0)
        assert isinstance(cost, float)
        assert cost == 0.0

    def test_cost_guard_is_float_not_int(self):
        """or 0.0 (not or 0) ensures float type."""
        from src.simulation.llm_router import call_llm
        r = call_llm(
            "llama",
            [{"role": "user", "content": "test"}],
            mock_response='{"choice":"a"}',
        )
        cost = (r._hidden_params.get("response_cost") or 0.0)
        assert type(cost) is float, f"Expected float, got {type(cost).__name__}"

    def test_unknown_family_raises(self):
        from src.simulation.llm_router import call_llm
        with pytest.raises(KeyError):
            call_llm("unknown_family", [{"role": "user", "content": "test"}])

    def test_strip_md_utility(self):
        from src.simulation.llm_router import strip_md
        assert strip_md("```json\n{}\n```") == "{}"
        assert strip_md("```\n{}\n```") == "{}"
        assert strip_md("  {}\n  ") == "{}"


# ===========================================================================
# T02+: RNE Engine (stub — will fail until T02 is implemented)
# ===========================================================================

class TestRNEEngine:
    """Integration tests for the RNE game engine. Require T02 implementation."""

    @pytest.mark.skip(reason="T02 (RNE engine) not yet implemented")
    def test_35_round_game_completes(self):
        """run_rne game must complete 35 rounds and write JSONL."""
        pass

    @pytest.mark.skip(reason="T02 (RNE engine) not yet implemented")
    def test_perturbation_fires_at_round_20(self):
        """Exactly one perturbation event must appear at round 20."""
        pass

    @pytest.mark.skip(reason="T02 (RNE engine) not yet implemented")
    def test_game_end_cost_under_limit(self):
        """game_end.total_cost_usd must be ≤ 0.05 per session."""
        pass


# ===========================================================================
# T03+: Metrics (stub — will fail until T03 is implemented)
# ===========================================================================

class TestRNEMetrics:
    """Unit tests for M1–M4 metrics computation. Require T03 implementation."""

    @pytest.mark.skip(reason="T03 (metrics) not yet implemented")
    def test_cooperation_rate_in_range(self):
        """M1 cooperation_rate must be between 0.0 and 1.0."""
        pass

    @pytest.mark.skip(reason="T03 (metrics) not yet implemented")
    def test_summary_json_has_all_metrics(self):
        """summary.json must contain M1–M4 keys."""
        pass
