"""Smoke tests for the Trade Island game engine.

Runs a 3-round mock game (no real API calls) and asserts schema contracts.

Constraints:
  - NO imports from src.analysis.* (polars stubs would fail if polars absent)
  - All LLM calls use mock_response kwarg (zero cost, instant)
  - Tests are self-contained; each creates its own temp data directory
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Mock responses
# ---------------------------------------------------------------------------

# Agent act: proposes a trade of 1 wood for 1 grain from a1
_MOCK_ACT_TRADE = json.dumps({
    "action_type": "trade",
    "target": "a1",
    "give": {"wood": 1},
    "want": {"grain": 1},
    "building": None,
})

# Agent act: hoard (safe no-op)
_MOCK_ACT_HOARD = json.dumps({
    "action_type": "hoard",
    "target": None,
    "give": None,
    "want": None,
    "building": None,
})

# Responder accepts
_MOCK_RESPOND_ACCEPT = json.dumps({
    "accepted": True,
    "counter": None,
})

# GM approves all proposals
_MOCK_GM_APPROVE_ALL = json.dumps({
    "verdicts": [{"idx": 0, "valid": True, "reason": "ok"}]
})

# Reflection summary
_MOCK_REFLECT = "I am building my resource base. Next I will trade more aggressively."


# ---------------------------------------------------------------------------
# Helper: run a mock game and return (game_id, output_dir, jsonl_lines)
# ---------------------------------------------------------------------------

def _run_mock_game(
    num_rounds: int = 3,
    mock_response: str = _MOCK_ACT_HOARD,
    tmp_path: Path = None,
) -> tuple[str, Path, list[dict]]:
    """Run a game with mocked LLM, return (game_id, output_dir, lines)."""
    import os

    # Redirect data/raw output to a temp directory to avoid polluting live data
    _orig_cwd = os.getcwd()
    if tmp_path is not None:
        os.chdir(tmp_path)

    try:
        from src.simulation.config import GameConfig
        from src.simulation.game import GameRunner

        config = GameConfig.from_name("mistral-mono")
        # Patch num_rounds for faster test execution
        config = config.model_copy(update={"num_rounds": num_rounds})
        runner = GameRunner(config)
        summary = runner.run_game(mock_response=mock_response)
        game_id = summary["game_id"]

        if tmp_path is not None:
            output_dir = tmp_path / "data" / "raw" / game_id
        else:
            output_dir = Path("data") / "raw" / game_id

        jsonl_path = output_dir / "game.jsonl"
        lines = [json.loads(line) for line in jsonl_path.read_text().splitlines() if line.strip()]
        return game_id, output_dir, lines, summary
    finally:
        os.chdir(_orig_cwd)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRoundEndSchema:
    """round_end events must have the correct schema."""

    def test_round_end_schema(self, tmp_path):
        """Each round_end line has required keys; vp is int; count = num_agents * rounds."""
        game_id, output_dir, lines, summary = _run_mock_game(
            num_rounds=3,
            mock_response=_MOCK_ACT_HOARD,
            tmp_path=tmp_path,
        )
        round_end_lines = [l for l in lines if l["event"] == "round_end"]

        required_keys = {"game_id", "model_family", "round", "agent_id", "vp"}
        for line in round_end_lines:
            missing = required_keys - line.keys()
            assert not missing, (
                f"round_end line missing keys {missing}: {line}"
            )
            assert isinstance(line["vp"], int), (
                f"vp must be int, got {type(line['vp'])}: {line}"
            )

        # 3 rounds × 6 agents = 18
        assert len(round_end_lines) == 3 * 6, (
            f"Expected 18 round_end lines, got {len(round_end_lines)}"
        )


class TestGMResolutionSchema:
    """gm_resolution events must have at least the 'accepted' field."""

    def test_gm_resolution_schema(self, tmp_path):
        """At least one gm_resolution event with 'accepted' field exists after a trade-proposing run."""
        # Use trade mock so proposals are generated
        game_id, output_dir, lines, summary = _run_mock_game(
            num_rounds=3,
            mock_response=_MOCK_ACT_TRADE,
            tmp_path=tmp_path,
        )
        gm_lines = [l for l in lines if l["event"] == "gm_resolution"]
        assert len(gm_lines) >= 1, (
            "Expected at least one gm_resolution event"
        )
        for line in gm_lines:
            assert "accepted" in line, (
                f"gm_resolution line missing 'accepted' field: {line}"
            )


class TestCheckpointExists:
    """Checkpoint file must be written after each round."""

    def test_checkpoint_exists(self, tmp_path):
        """checkpoint_r01.json exists after a 3-round run."""
        game_id, output_dir, lines, summary = _run_mock_game(
            num_rounds=3,
            mock_response=_MOCK_ACT_HOARD,
            tmp_path=tmp_path,
        )
        checkpoint = output_dir / "checkpoint_r01.json"
        assert checkpoint.exists(), (
            f"checkpoint_r01.json not found at {checkpoint}"
        )
        # Verify it's valid JSON with expected keys
        data = json.loads(checkpoint.read_text())
        assert "game_id" in data
        assert "round" in data
        assert data["round"] == 1


class TestMockCostZero:
    """game_end.total_cost_usd must be 0.0 (float) for mocked runs."""

    def test_mock_cost_zero(self, tmp_path):
        """Mock run produces total_cost_usd == 0.0 (not None, not int)."""
        game_id, output_dir, lines, summary = _run_mock_game(
            num_rounds=3,
            mock_response=_MOCK_ACT_HOARD,
            tmp_path=tmp_path,
        )
        game_end_lines = [l for l in lines if l["event"] == "game_end"]
        assert len(game_end_lines) == 1, "Expected exactly one game_end event"
        game_end = game_end_lines[0]

        cost = game_end.get("total_cost_usd")
        assert cost == 0.0, f"Expected total_cost_usd=0.0, got {cost!r}"
        assert isinstance(cost, float), (
            f"total_cost_usd must be float, got {type(cost).__name__}"
        )

        # Also check from summary dict
        assert summary["total_cost_usd"] == 0.0


class TestDoubleSpendInGame:
    """The second trade from the same proposer resource should be rejected."""

    def test_double_spend_in_game(self, tmp_path):
        """Double-spend: second proposal consuming same resource as first is rejected."""
        import os
        from unittest.mock import patch

        # We need two agents to both try trading the same resource from a0.
        # Strategy: override act() to return specific actions.
        # a0 proposes wood→grain to a1, a1 proposes wood→grain to a2.
        # But a0 has only 3 wood, and we'll set both to give 2 wood.
        # We can't easily control per-agent mock_response with a single mock_response string.
        # Instead, use a more targeted approach: patch the resolve_trades path directly
        # by constructing a scenario through the GM module test (which already verifies
        # this), and confirm it produces valid=False for the second trade.
        #
        # For game-level test: use mock_response with action_type="trade" and a1/a2 accepting.
        # Both a0 and a1 will propose trade (same mock_response for all agents), but
        # the double-spend only triggers when the same proposer runs out of resources.
        # We verify by checking if any gm_resolution with valid=False exists due to
        # proposer_insufficient_* reason.
        #
        # The definitive double-spend test is in gm.py (standalone, already verified).
        # Here we test at the game loop level by running a scenario where gm_resolution
        # events show the inventory guard working.

        # Construct a specific mock where a0 will attempt to give ALL its wood (3) twice.
        # Use mock_response that always proposes giving 3 wood, so only one trade can succeed.
        mock_double_spend = json.dumps({
            "action_type": "trade",
            "target": "a1",
            "give": {"wood": 3},
            "want": {"grain": 1},
            "building": None,
        })

        _orig_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            from src.simulation.config import GameConfig
            from src.simulation.game import GameRunner
            from src.simulation.gm import GM, Resolution
            from src.simulation.logger import GameLogger

            # Direct GM-level double-spend verification (ensures game-level invariant)
            # Use tmp_path (pytest fixture) instead of tempfile so it persists for asserts.
            gm_dir = tmp_path / "gm_ds_test"
            gm_dir.mkdir(parents=True, exist_ok=True)

            game_logger = GameLogger(
                game_id="test-ds-game", output_dir=gm_dir
            )
            gm = GM(
                model_string="mistral/mistral-small-2506",
                logger=game_logger,
            )

            # a0 has 3 wood — tries to give 3 wood to both a1 and a2
            inventories = {
                "a0": {"wood": 3, "grain": 5},
                "a1": {"wood": 0, "grain": 3},
                "a2": {"wood": 1, "grain": 3},
            }
            model_families = {"a0": "mistral", "a1": "mistral", "a2": "mistral"}
            proposals = [
                {
                    "proposer": "a0",
                    "responder": "a1",
                    "give": {"wood": 3},
                    "want": {"grain": 1},
                    "accepted": True,
                    "counter": None,
                },
                {
                    "proposer": "a0",
                    "responder": "a2",
                    "give": {"wood": 3},
                    "want": {"grain": 1},
                    "accepted": True,
                    "counter": None,
                },
            ]
            mock_gm_ok = json.dumps({
                "verdicts": [
                    {"idx": 0, "valid": True, "reason": "ok"},
                    {"idx": 1, "valid": True, "reason": "ok"},
                ]
            })

            resolutions = gm.resolve_trades(
                round_num=1,
                proposals=proposals,
                inventories=inventories,
                model_families=model_families,
                config_name="mistral-mono",
                mock_response=mock_gm_ok,
            )
            game_logger.close()

            assert resolutions[0].valid is True, (
                f"First trade should be valid, got {resolutions[0].reason}"
            )
            assert resolutions[1].valid is False, (
                f"Second trade should be invalid (double-spend), "
                f"got valid={resolutions[1].valid}, reason={resolutions[1].reason}"
            )

            # Also verify the gm_resolution JSONL logged valid=False for trade_idx=1
            jsonl_path = gm_dir / "game.jsonl"
            assert jsonl_path.exists(), f"game.jsonl not found at {jsonl_path}"
            gm_lines = []
            for line in jsonl_path.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                if data.get("event") == "gm_resolution":
                    gm_lines.append(data)

            second_res = next(
                (l for l in gm_lines if l.get("trade_idx") == 1), None
            )
            assert second_res is not None, "gm_resolution for trade_idx=1 not found in JSONL"
            assert second_res["valid"] is False, (
                f"JSONL gm_resolution trade_idx=1 should have valid=False, got {second_res}"
            )
        finally:
            os.chdir(_orig_cwd)
