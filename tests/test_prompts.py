"""Tests for src/prompts/ — parser edge cases, token budgets, config shapes, kwarg inspection.

Constraints:
  - NO imports from src.analysis.* (polars stubs would fail if polars absent)
  - NO polars imports
  - All tests use synthetic inputs — no real API calls
"""

from __future__ import annotations

import pytest

from src.prompts.json_utils import (
    format_inventory,
    get_completion_kwargs,
    parse_agent_response,
)
from src.prompts.agent_action import build_act_messages
from src.prompts.trade_response import build_respond_messages
from src.simulation.config import GameConfig, _STANDARD_BUILDINGS


# ---------------------------------------------------------------------------
# TestParseAgentResponse
# ---------------------------------------------------------------------------

class TestParseAgentResponse:
    """parse_agent_response() must handle all documented input shapes."""

    def test_valid_json(self):
        """Plain JSON string — strategy 1 succeeds immediately."""
        result = parse_agent_response('{"action_type": "hoard"}', {})
        assert result == {"action_type": "hoard"}

    def test_fenced_json(self):
        """Markdown code fence — strip_md unwraps it before parse."""
        raw = "```json\n{\"action_type\":\"build\"}\n```"
        result = parse_agent_response(raw, {})
        assert result == {"action_type": "build"}

    def test_json_with_surrounding_text(self):
        """JSON embedded in prose — bracket-counter extraction (strategy 3)."""
        raw = 'Here is my action: {"action_type":"build"} done.'
        result = parse_agent_response(raw, {})
        assert result == {"action_type": "build"}

    def test_truncated_json_returns_none(self):
        """Truncated JSON — all strategies fail; must return exactly None."""
        result = parse_agent_response('{"action_type": "bu', {})
        assert result is None  # not just falsy — must be the sentinel None

    def test_deepseek_think_prefix(self):
        """DeepSeek <think> prefix — strategy 2 (strip_think) recovers the JSON."""
        raw = '<think>I should hoard this round</think>\n{"action_type":"hoard"}'
        result = parse_agent_response(raw, {})
        assert result == {"action_type": "hoard"}


# ---------------------------------------------------------------------------
# TestFormatInventory
# ---------------------------------------------------------------------------

class TestFormatInventory:
    """format_inventory() must produce W S G C F compact strings."""

    def test_compact_format(self):
        """Typical non-zero inventory maps to correct initials and order."""
        result = format_inventory({"wood": 2, "stone": 3, "grain": 4, "clay": 1, "fiber": 0})
        assert result == "W2 S3 G4 C1 F0"

    def test_empty_values(self):
        """Zero counts must appear in output — never omitted."""
        result = format_inventory({"wood": 0, "stone": 0, "grain": 0, "clay": 0, "fiber": 0})
        assert result == "W0 S0 G0 C0 F0"


# ---------------------------------------------------------------------------
# TestTokenBudgets
# ---------------------------------------------------------------------------

class TestTokenBudgets:
    """Prompt token budgets (chars//4 estimate) must stay within targets."""

    _INV = {"wood": 2, "stone": 3, "grain": 4, "clay": 1, "fiber": 0}
    _VP = 6
    _ROUND = 8
    _BUILDINGS = _STANDARD_BUILDINGS

    def test_act_within_budget(self):
        """build_act_messages total chars//4 must be ≤ 108."""
        msgs = build_act_messages(
            agent_id="a0",
            model_family="mistral",
            round_num=self._ROUND,
            inventory=self._INV,
            vp=self._VP,
            buildings_built=[],
            all_agents_vp={"a0": 6, "a1": 3},
            memory=[],
            buildings_config=self._BUILDINGS,
        )
        tok = sum(len(m["content"]) for m in msgs) // 4
        assert tok <= 108, f"act prompt too large: {tok} tok (budget ≤108)"

    def test_respond_within_budget(self):
        """build_respond_messages total chars//4 must be ≤ 72."""
        proposal = {"proposer": "a1", "give": {"wood": 1}, "want": {"grain": 1}}
        msgs = build_respond_messages(
            agent_id="a0",
            inventory=self._INV,
            vp=self._VP,
            proposal=proposal,
            buildings_config=self._BUILDINGS,
        )
        tok = sum(len(m["content"]) for m in msgs) // 4
        assert tok <= 72, f"respond prompt too large: {tok} tok (budget ≤72)"


# ---------------------------------------------------------------------------
# TestPhase0Config
# ---------------------------------------------------------------------------

class TestPhase0Config:
    """GameConfig.from_name('phase0') must be a valid 4-family mix."""

    def _config(self):
        return GameConfig.from_name("phase0")

    def test_phase0_has_four_families(self):
        """All four model families must be present."""
        c = self._config()
        families = {e["model_family"] for e in c.agent_models}
        assert families == {"llama", "deepseek", "gemini", "mistral"}, (
            f"Expected all 4 families, got: {families}"
        )

    def test_phase0_agent_count(self):
        """Exactly 6 agents."""
        c = self._config()
        assert len(c.agent_models) == 6, (
            f"Expected 6 agents, got {len(c.agent_models)}"
        )

    def test_phase0_family_distribution(self):
        """Exact counts: 2 llama, 2 deepseek, 1 gemini, 1 mistral."""
        from collections import Counter
        c = self._config()
        counts = Counter(e["model_family"] for e in c.agent_models)
        assert counts["llama"] == 2, f"Expected 2 llama, got {counts['llama']}"
        assert counts["deepseek"] == 2, f"Expected 2 deepseek, got {counts['deepseek']}"
        assert counts["gemini"] == 1, f"Expected 1 gemini, got {counts['gemini']}"
        assert counts["mistral"] == 1, f"Expected 1 mistral, got {counts['mistral']}"


# ---------------------------------------------------------------------------
# TestMonoConfigs
# ---------------------------------------------------------------------------

class TestMonoConfigs:
    """Mono configs must produce 6 agents all from the same family."""

    def _check_mono(self, name: str, family: str) -> None:
        c = GameConfig.from_name(name)
        assert len(c.agent_models) == 6, (
            f"{name}: expected 6 agents, got {len(c.agent_models)}"
        )
        families = {e["model_family"] for e in c.agent_models}
        assert families == {family}, (
            f"{name}: expected all agents to be {family!r}, got {families}"
        )

    def test_llama_mono(self):
        """llama-mono: 6 agents, all llama."""
        self._check_mono("llama-mono", "llama")

    def test_deepseek_mono(self):
        """deepseek-mono: 6 agents, all deepseek."""
        self._check_mono("deepseek-mono", "deepseek")

    def test_gemini_mono(self):
        """gemini-mono: 6 agents, all gemini."""
        self._check_mono("gemini-mono", "gemini")


# ---------------------------------------------------------------------------
# TestGetCompletionKwargs
# ---------------------------------------------------------------------------

class TestGetCompletionKwargs:
    """get_completion_kwargs() must return correct provider-level kwargs."""

    def test_gemini_no_response_format(self):
        """Gemini does not accept response_format — must not be in kwargs."""
        kwargs = get_completion_kwargs("gemini")
        assert "response_format" not in kwargs, (
            f"gemini kwargs should not contain response_format, got: {kwargs}"
        )

    def test_mistral_has_response_format(self):
        """Mistral supports JSON mode — response_format must be present."""
        kwargs = get_completion_kwargs("mistral")
        assert "response_format" in kwargs, (
            f"mistral kwargs must contain response_format, got: {kwargs}"
        )

    def test_returns_copy(self):
        """Mutating the returned dict must not modify the PROVIDER_KWARGS source."""
        kwargs1 = get_completion_kwargs("mistral")
        kwargs1["__sentinel__"] = True  # mutate

        kwargs2 = get_completion_kwargs("mistral")
        assert "__sentinel__" not in kwargs2, (
            "get_completion_kwargs must return a copy — source was mutated"
        )
