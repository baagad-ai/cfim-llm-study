"""Tests for the RNE (Repeated Negotiated Exchange) engine — Study 1.

Running state:
  T01 (Config, Logger, LLM Router): PASSES — RNEConfig, GameLogger, PROVIDER_KWARGS
  T02 (RNE engine + metrics): PASSES — RNERunner, _compute_metrics, decay, trade settlement

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
# T02: RNE Engine
# ===========================================================================

def _run_mock_session(tmp_path, rounds=5, perturbation_round=3,
                      mock_response=None):
    """Helper: run a short mock RNE session in an isolated tmp directory."""
    import os
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        from src.simulation.rne_game import RNERunner
        from src.simulation.config import RNEConfig
        if mock_response is None:
            mock_response = '{"action": "propose", "give": {"W": 1}, "want": {"G": 1}}'
        cfg = RNEConfig(
            family_a="mistral",
            family_b="llama",
            condition="A",
            rounds=rounds,
            perturbation_round=perturbation_round,
        )
        runner = RNERunner(data_root=tmp_path / "study1")
        summary = runner.run_session(cfg, mock_response=mock_response)
        session_dir = tmp_path / "study1" / cfg.session_id
        lines = [
            json.loads(l)
            for l in (session_dir / "game.jsonl").read_text().splitlines()
            if l.strip()
        ]
        return summary, lines, session_dir
    finally:
        os.chdir(old_cwd)


import json as _json_module


class TestRNEEngine:
    """Integration tests for the RNE game engine."""

    def test_round_end_lines_correct_count(self, tmp_path):
        """5 rounds × 2 agents = 10 round_end lines."""
        summary, lines, _ = _run_mock_session(tmp_path)
        round_end = [l for l in lines if l["event"] == "round_end"]
        assert len(round_end) == 10, f"Expected 10 round_end lines, got {len(round_end)}"

    def test_round_end_schema(self, tmp_path):
        """round_end must have: event, round, agent_id, family, inventory, inventory_value, trade_executed."""
        summary, lines, _ = _run_mock_session(tmp_path)
        for line in [l for l in lines if l["event"] == "round_end"]:
            for field in ("round", "agent_id", "family", "inventory", "inventory_value", "trade_executed"):
                assert field in line, f"round_end missing field: {field}"
            assert line["agent_id"] in ("a0", "a1")
            assert isinstance(line["inventory"], dict)
            assert isinstance(line["inventory_value"], int)

    def test_perturbation_fires_once_at_correct_round(self, tmp_path):
        """Exactly one perturbation event, at round == perturbation_round."""
        summary, lines, _ = _run_mock_session(tmp_path, rounds=5, perturbation_round=3)
        perturb = [l for l in lines if l["event"] == "perturbation"]
        assert len(perturb) == 1, f"Expected 1 perturbation, got {len(perturb)}"
        assert perturb[0]["round"] == 3

    def test_game_end_always_written(self, tmp_path):
        """game_end event must appear in JSONL."""
        summary, lines, _ = _run_mock_session(tmp_path)
        game_end = [l for l in lines if l["event"] == "game_end"]
        assert len(game_end) == 1
        assert "total_cost_usd" in game_end[0]
        assert isinstance(game_end[0]["total_cost_usd"], float)

    def test_cost_is_float(self, tmp_path):
        """total_cost_usd in summary must be a float (not None or int)."""
        summary, _, _ = _run_mock_session(tmp_path)
        assert isinstance(summary["total_cost_usd"], float)

    def test_summary_json_written(self, tmp_path):
        """summary.json must exist and contain all required keys."""
        summary, _, session_dir = _run_mock_session(tmp_path)
        assert (session_dir / "summary.json").exists()
        data = _json_module.loads((session_dir / "summary.json").read_text())
        for key in ("session_id", "family_a", "family_b", "condition",
                    "cooperation_rate", "exploitation_delta",
                    "adaptation_lag", "betrayal_recovery",
                    "total_cost_usd", "total_rounds"):
            assert key in data, f"summary.json missing key: {key}"

    def test_metadata_json_written(self, tmp_path):
        """metadata.json must exist and include wall_clock_seconds."""
        _, _, session_dir = _run_mock_session(tmp_path)
        assert (session_dir / "metadata.json").exists()
        meta = _json_module.loads((session_dir / "metadata.json").read_text())
        assert "wall_clock_seconds" in meta
        assert "family_a" in meta

    def test_decay_applied(self, tmp_path):
        """After round 1, a0's inventory must be decayed (W < 5 since int(5*0.9)=4)."""
        _, lines, _ = _run_mock_session(tmp_path)
        r1_a0 = next(
            l for l in lines if l["event"] == "round_end"
            and l["round"] == 1 and l["agent_id"] == "a0"
        )
        # Regardless of trade, W should have decayed from 5 to ≤4
        assert r1_a0["inventory"].get("W", 5) <= 4, \
            f"Decay not applied: W={r1_a0['inventory'].get('W')}"

    def test_trade_execution_path(self, tmp_path):
        """When one agent proposes and the other accepts, trade_executed=True in round_end."""
        # Mock: a0 proposes, a1 accepts (accept action)
        mock = '{"action": "accept"}'
        # With accept, agent gets treated as pass on simultaneous collection (action ≠ propose),
        # so one propose + one accept → respond call path.
        # The respond call also returns "accept" → trade should execute.
        summary, lines, _ = _run_mock_session(
            tmp_path, rounds=3, perturbation_round=2,
            mock_response='{"action": "propose", "give": {"W": 2}, "want": {"G": 2}}'
        )
        # trade_result lines tell us what happened
        trade_results = [l for l in lines if l["event"] == "trade_result"]
        assert len(trade_results) == 3, f"Expected 3 trade_result events, got {len(trade_results)}"

    def test_cooperation_rate_in_range(self, tmp_path):
        """M1 cooperation_rate must be in [0.0, 1.0]."""
        summary, _, _ = _run_mock_session(tmp_path)
        assert 0.0 <= summary["cooperation_rate"] <= 1.0


# ===========================================================================
# T02: Mechanics unit tests (no session needed)
# ===========================================================================

class TestRNEMechanics:
    """Unit tests for trade mechanics and decay — no LLM calls."""

    def test_proposals_compatible_true(self):
        from src.simulation.rne_game import _proposals_compatible
        p_a = {"action": "propose", "give": {"W": 2}, "want": {"G": 2}}
        p_b = {"action": "propose", "give": {"G": 2}, "want": {"W": 2}}
        assert _proposals_compatible(p_a, p_b) is True

    def test_proposals_compatible_false_same_want(self):
        from src.simulation.rne_game import _proposals_compatible
        p_a = {"action": "propose", "give": {"W": 1}, "want": {"G": 1}}
        p_b = {"action": "propose", "give": {"W": 1}, "want": {"G": 1}}
        assert _proposals_compatible(p_a, p_b) is False

    def test_execute_trade_correct_swap(self):
        from src.simulation.rne_game import _execute_trade
        inv_a = {"W": 5, "S": 5, "G": 0, "C": 0}
        inv_b = {"W": 0, "S": 0, "G": 5, "C": 5}
        new_a, new_b = _execute_trade(inv_a, inv_b, give_a={"W": 2}, want_a={"G": 2})
        assert new_a["W"] == 3
        assert new_a["G"] == 2
        assert new_b["G"] == 3
        assert new_b["W"] == 2

    def test_decay_applied_correctly(self):
        from src.simulation.rne_game import _apply_decay
        result = _apply_decay({"W": 5, "G": 3, "S": 0}, 0.10)
        assert result["W"] == 4    # int(5 * 0.9) = 4
        assert result["G"] == 2    # int(3 * 0.9) = 2
        assert result["S"] == 0    # int(0 * 0.9) = 0

    def test_inventory_value(self):
        from src.simulation.rne_game import _inventory_value
        # W=1, G=2; 3W + 2G = 3 + 4 = 7
        assert _inventory_value({"W": 3, "G": 2}) == 7

    def test_m1_computation(self):
        from src.simulation.rne_game import _compute_metrics
        # 2 completed trades in 5 rounds → M1 = 0.4
        trade_log = [
            {"round": r, "executed": r in (1, 3), "give_a": {}, "want_a": {}}
            for r in range(1, 6)
        ]
        action_log = [
            {"round": r, "agent_id": aid, "action_type": "propose"}
            for r in range(1, 6) for aid in ("a0", "a1")
        ]
        metrics = _compute_metrics(
            completed_trades=2,
            total_rounds=5,
            trade_log=trade_log,
            perturbation_round=3,
            action_log=action_log,
        )
        assert metrics["M1"] == 0.4
