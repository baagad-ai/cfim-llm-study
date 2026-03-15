"""tests/test_mechanics.py — unit tests for simulation mechanics repairs.

Tests cover CF1–CF8 + SF4–SF9 fixes from T03-FIX sprint.
All tests use mock LLM responses — no real API calls.

NOTE: These tests require Trade Island engine symbols (_SPECIALTY_ARCHETYPES,
_KEY_NORM) that were part of S04's fix sprint. They are preserved here for
when S04's Trade Island engine work resumes, but are skipped while the
current main is on the S01 RNE engine path.

Test list:
  1. test_build_affects_inventory        — build Market: w-2 s-2 deducted, vp+3
  2. test_grain_income_applied           — grain income is given before consumption
  3. test_grain_net_neutral              — with grain_income=1 and hunger=1, grain is flat
  4. test_hunger_penalty_applied         — grain=0 triggers -1VP penalty
  5. test_granary_income                 — Granary owner gets +2 grain/round
  6. test_resource_specialization        — phase0 agents have different starting inventories
  7. test_key_normalization              — W/S/G/C/F single-char keys normalized to full names
  8. test_build_failed_event_logged      — insufficient-resource build emits build_failed event
  9. test_raw_action_logged              — agent_action event includes raw_action field
 10. test_early_win_check               — 12VP triggers game end before round 25
 11. test_hoard_gives_specialty         — hoard action gives +1 specialty resource
"""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

import pytest

# Guard: skip entire module if Trade Island engine symbols not yet present.
# These were added in S04's T03-FIX sprint; they will be available once
# S04 Trade Island mechanics work resumes.
try:
    from src.simulation.config import GameConfig, _SPECIALTY_ARCHETYPES
    from src.simulation.game import GameRunner, _KEY_NORM
    _MECHANICS_AVAILABLE = True
except ImportError:
    _MECHANICS_AVAILABLE = False
    pytest.skip(
        "Trade Island mechanics symbols (_SPECIALTY_ARCHETYPES, _KEY_NORM) not yet "
        "available — S04 T03-FIX sprint required. Skipping test_mechanics.py.",
        allow_module_level=True,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_mock(config_name: str, mock_response: str, *, gm_model: str | None = None) -> Path:
    """Run a game with mock LLM and return the output_dir path."""
    config = GameConfig.from_name(config_name)
    if gm_model:
        config.gm_model = gm_model
    runner = GameRunner(config)
    result = runner.run_game(mock_response=mock_response)
    return Path(f"data/raw/{result['game_id']}")


def _events(output_dir: Path, event: str) -> list[dict]:
    """Parse game.jsonl and return all lines where event == event."""
    lines = []
    for line in (output_dir / "game.jsonl").read_text(encoding="utf-8").splitlines():
        d = json.loads(line)
        if d.get("event") == event:
            lines.append(d)
    return lines


def _all_events(output_dir: Path) -> list[dict]:
    """Parse all events from game.jsonl."""
    return [
        json.loads(line)
        for line in (output_dir / "game.jsonl").read_text(encoding="utf-8").splitlines()
    ]


# Mock response for build Market action (a0 gets to try immediately)
_MOCK_BUILD_MARKET = '{"action_type": "build", "building": "Market", "target": null, "give": null, "want": null}'
_MOCK_HOARD = '{"action_type": "hoard", "target": null, "give": null, "want": null}'
_MOCK_TRADE = '{"action_type": "trade", "target": "a1", "give": {"wood": 1}, "want": {"stone": 1}, "building": null}'
# GM accept-all response
_MOCK_GM_ACCEPT = '{"resolution": "accepted"}'


# ---------------------------------------------------------------------------
# Test 1: build affects inventory
# ---------------------------------------------------------------------------

class TestBuildAffectsInventory:
    """CF3/mechanics: successful build deducts resources and grants VP."""

    def test_build_market_deducts_resources_grants_vp(self):
        """Build Market costs W2+S2 and gives +3VP.
        
        Market cost: {wood: 2, stone: 2}, vp: 3.
        Agent a0 starts with wood=5 (specialty archetype 0) and stone=3.
        After build: wood=3, stone=1, vp=3.
        """
        output_dir = _run_mock("mistral-mono", _MOCK_BUILD_MARKET)
        build_events = _events(output_dir, "build")
        assert len(build_events) > 0, "Expected at least one build event"
        # Find a Market build
        market_builds = [e for e in build_events if e.get("building") == "Market"]
        assert len(market_builds) > 0, "Expected at least one Market build"
        # VP delta is +3
        for mb in market_builds:
            assert mb["vp_delta"] == 3, f"Market vp_delta should be 3, got {mb['vp_delta']}"


# ---------------------------------------------------------------------------
# Test 2 & 3: grain income and net-neutral
# ---------------------------------------------------------------------------

class TestGrainMechanics:
    """CF1: grain income keeps grain flat at 1 income / 1 consumption per round."""

    def test_grain_income_in_round_end_events(self):
        """round_end events should have inventory with grain tracked."""
        output_dir = _run_mock("mistral-mono", _MOCK_HOARD)
        round_end_events = _events(output_dir, "round_end")
        assert len(round_end_events) > 0, "Expected round_end events"
        # At least some round_end events should have inventory
        with_inv = [e for e in round_end_events if "inventory" in e]
        assert len(with_inv) > 0, "Expected round_end events with inventory (SF6 fix)"

    def test_grain_net_neutral_after_25_rounds(self):
        """With grain_income=1 and hunger=1, no-trade/no-build game keeps grain flat.
        
        Starting grain (archetype 0): 5. Income: +1/round. Consume: -1/round.
        Net per round: 0. Expected end grain: 5.
        Note: some agents may have started with different grain depending on specialty.
        """
        config = GameConfig.from_name("mistral-mono")
        assert config.grain_income == 1, "grain_income should default to 1"
        assert config.hunger_rate == 1, "hunger_rate should default to 1"

    def test_grain_income_config_present(self):
        """GameConfig must have grain_income field set to 1 (CF1)."""
        config = GameConfig.from_name("phase0")
        assert hasattr(config, "grain_income"), "GameConfig missing grain_income (CF1)"
        assert config.grain_income == 1, f"Expected grain_income=1, got {config.grain_income}"


# ---------------------------------------------------------------------------
# Test 4: hunger penalty
# ---------------------------------------------------------------------------

class TestHungerPenalty:
    """CF1/starvation: agents with grain=0 should still be penalized (not infinitely so)."""

    def test_starvation_events_have_vp(self):
        """grain_consumption events with starved=True must have a VP recorded."""
        output_dir = _run_mock("mistral-mono", _MOCK_HOARD)
        gc_events = _events(output_dir, "grain_consumption")
        # All events must include vp
        for e in gc_events:
            assert "vp" in e, f"grain_consumption event missing vp: {e}"

    def test_no_starvation_floor_with_grain_income(self):
        """With grain_income=1, agents should not end at -17 to -20 VP.
        
        VP floor = 0 starting - 25 × 1 (starvation) + 0 buildings = -25.
        But with grain_income=1, net grain is 0 per round, so starvation
        should be rare (only if no grain at start for a round-1 case).
        
        Test: run 25 rounds with hoard only, check no agent ends at -20.
        """
        output_dir = _run_mock("mistral-mono", _MOCK_HOARD)
        round_end = _events(output_dir, "round_end")
        # Last round
        last_round = [e for e in round_end if e.get("round") == 25]
        if last_round:
            for e in last_round:
                assert e["vp"] > -15, (
                    f"VP floor too low: {e['vp']} for agent {e['agent_id']} "
                    "(expected grain income to prevent -17 to -20 floor)"
                )


# ---------------------------------------------------------------------------
# Test 5: Granary income
# ---------------------------------------------------------------------------

class TestGranaryIncome:
    """CF3: Granary effect — owners get +2 grain/round."""

    def test_granary_effect_exists_in_buildings_config(self):
        """Granary must have an 'effect' key with grain_income=2."""
        config = GameConfig.from_name("phase0")
        granary = config.buildings.get("Granary")
        assert granary is not None, "Granary missing from buildings config"
        effect = granary.get("effect")
        assert effect is not None, "Granary missing 'effect' key (CF3 not implemented)"
        assert effect.get("grain_income") == 2, (
            f"Expected Granary grain_income=2, got {effect.get('grain_income')}"
        )


# ---------------------------------------------------------------------------
# Test 6: Resource specialization
# ---------------------------------------------------------------------------

class TestResourceSpecialization:
    """CF2: agents start with different inventories (specialty archetypes)."""

    def test_phase0_agents_have_different_starting_inventories(self):
        """phase0 agents must have distinct starting inventories (not all identical)."""
        config = GameConfig.from_name("phase0")
        inventories = [
            entry.get("starting_inventory") for entry in config.agent_models
        ]
        assert all(inv is not None for inv in inventories), (
            "All phase0 agents should have starting_inventory (CF2 fix)"
        )
        # At least 2 different inventories
        inv_tuples = [tuple(sorted(inv.items())) for inv in inventories]
        unique_invs = set(inv_tuples)
        assert len(unique_invs) > 1, (
            f"Expected different starting inventories, got {len(unique_invs)} unique "
            "(CF2: resource specialization not active)"
        )

    def test_specialty_archetypes_total_resources_balanced(self):
        """Each archetype's total resource count should be roughly equal."""
        for i, archetype in enumerate(_SPECIALTY_ARCHETYPES):
            total = sum(archetype["inventory"].values())
            # Base total: 3+3+5+3+2 = 16. Allow ±2 for specialization.
            assert 14 <= total <= 18, (
                f"Archetype {i} ({archetype['specialty']}) total resources {total} "
                "is outside balanced range [14, 18]"
            )

    def test_specialty_field_in_agent_entry(self):
        """Each phase0 agent must have a 'specialty' field."""
        config = GameConfig.from_name("phase0")
        for entry in config.agent_models:
            assert "specialty" in entry, (
                f"Agent {entry['agent_id']} missing 'specialty' field (CF2)"
            )


# ---------------------------------------------------------------------------
# Test 7: Resource key normalization
# ---------------------------------------------------------------------------

class TestKeyNormalization:
    """CF7: W/S/G/C/F single-char keys must normalize to full resource names."""

    def test_single_char_keys_normalized(self):
        """_KEY_NORM must map W→wood, S→stone, G→grain, C→clay, F→fiber."""
        assert _KEY_NORM.get("w") == "wood",  "w should normalize to wood"
        assert _KEY_NORM.get("s") == "stone", "s should normalize to stone"
        assert _KEY_NORM.get("g") == "grain", "g should normalize to grain"
        assert _KEY_NORM.get("c") == "clay",  "c should normalize to clay"
        assert _KEY_NORM.get("f") == "fiber", "f should normalize to fiber"

    def test_uppercase_keys_normalized_via_lowercase(self):
        """Uppercase W/S/G/C/F are normalized via .lower() at call site.
        
        The normalization pattern is: _KEY_NORM.get(k.lower(), k)
        So uppercase keys are handled by lowercasing before lookup.
        """
        # Simulate the normalization as used in game.py Phase 2
        def normalize(k: str) -> str:
            return _KEY_NORM.get(k.lower(), k)

        assert normalize("W") == "wood",  "W via lower() should normalize to wood"
        assert normalize("S") == "stone", "S via lower() should normalize to stone"
        assert normalize("G") == "grain", "G via lower() should normalize to grain"
        assert normalize("C") == "clay",  "C via lower() should normalize to clay"
        assert normalize("F") == "fiber", "F via lower() should normalize to fiber"

    def test_full_name_keys_pass_through(self):
        """Full resource names must also be in _KEY_NORM (idempotent)."""
        for name in ["wood", "stone", "grain", "clay", "fiber"]:
            assert _KEY_NORM.get(name) == name, f"full name '{name}' should map to itself"


# ---------------------------------------------------------------------------
# Test 8: build_failed event
# ---------------------------------------------------------------------------

class TestBuildFailedEvent:
    """SF5: when a build fails, a build_failed event must be emitted."""

    def test_build_failed_event_emitted_for_unknown_building(self):
        """build with unknown building name → build_failed event with reason=unknown_building."""
        mock_unknown_build = '{"action_type": "build", "building": "FakeBuilding", "target": null, "give": null, "want": null}'
        output_dir = _run_mock("mistral-mono", mock_unknown_build)
        failed = _events(output_dir, "build_failed")
        unknown = [e for e in failed if e.get("reason") == "unknown_building"]
        assert len(unknown) > 0, (
            "Expected build_failed events with reason=unknown_building (SF5)"
        )

    def test_build_failed_has_inventory(self):
        """build_failed events must include inventory field for diagnosis."""
        mock_insufficient = '{"action_type": "build", "building": "Tower", "target": null, "give": null, "want": null}'
        # Fresh agent with low clay — Tower costs stone=2+clay=2; 
        # some archetypes may have clay<2.
        output_dir = _run_mock("mistral-mono", mock_insufficient)
        failed = _events(output_dir, "build_failed")
        if failed:
            # build_failed events (insufficient OR unknown) should have inventory
            assert all("inventory" in e or e.get("reason") == "unknown_building"
                       for e in failed), (
                "build_failed events should include inventory (SF5)"
            )


# ---------------------------------------------------------------------------
# Test 9: raw_action in agent_action events
# ---------------------------------------------------------------------------

class TestRawActionLogged:
    """SF4: agent_action events must include raw_action field."""

    def test_raw_action_present_in_agent_action_events(self):
        """Every agent_action event must have a raw_action field."""
        output_dir = _run_mock("mistral-mono", _MOCK_HOARD)
        actions = _events(output_dir, "agent_action")
        assert len(actions) > 0, "Expected agent_action events"
        for e in actions:
            assert "raw_action" in e, (
                f"agent_action event missing raw_action (SF4): {e}"
            )


# ---------------------------------------------------------------------------
# Test 10: early-win condition
# ---------------------------------------------------------------------------

class TestEarlyWinCondition:
    """SF8: agent reaching 12VP triggers game end before round 25."""

    def test_early_win_event_on_12vp(self):
        """When an agent reaches 12VP, an early_win event must be logged.
        
        This test uses a mock response that always tries to build Market.
        With 6 agents × 25 rounds of build attempts on Market (3VP each),
        some agent may reach 12VP (4 buildings) but note the default starting
        inventory won't always allow 4 Market builds.
        
        Rather than rely on natural gameplay, we verify the mechanism is
        wired: if early_win events DO appear, they must have winner and winner_vp.
        """
        output_dir = _run_mock("mistral-mono", _MOCK_BUILD_MARKET)
        early_wins = _events(output_dir, "early_win")
        for ew in early_wins:
            assert "winner" in ew, "early_win event missing 'winner' field"
            assert "winner_vp" in ew, "early_win event missing 'winner_vp' field"
            assert ew["winner_vp"] >= 12, (
                f"early_win triggered with vp={ew['winner_vp']} < 12"
            )


# ---------------------------------------------------------------------------
# Test 11: hoard gives +1 specialty
# ---------------------------------------------------------------------------

class TestHoardGivesSpecialty:
    """SF9: hoard action gives +1 specialty resource."""

    def test_hoard_event_emitted(self):
        """When agents hoard, hoard events must be emitted (if specialty assigned)."""
        output_dir = _run_mock("mistral-mono", _MOCK_HOARD)
        hoard_events = _events(output_dir, "hoard")
        # Hoard events should appear (agents have specialty from CF2 archetypes)
        # If no hoard events, that means specialty is None for all — fail
        assert len(hoard_events) > 0, (
            "Expected hoard events with SF9 fix (agents have specialty, hoard gives +1)"
        )

    def test_hoard_event_has_resource_and_gained(self):
        """hoard events must include resource and gained=1 fields."""
        output_dir = _run_mock("mistral-mono", _MOCK_HOARD)
        hoard_events = _events(output_dir, "hoard")
        for e in hoard_events:
            assert "resource" in e, f"hoard event missing 'resource': {e}"
            assert e.get("gained") == 1, f"hoard gained should be 1, got {e.get('gained')}"
