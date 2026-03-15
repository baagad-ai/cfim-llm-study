"""Tests for src/prompts/rne_prompts.py — system prompt variants, round messages,
and tolerant response parser.

Covers:
  - All 9 (condition × framing) combinations return non-empty strings
  - Token budgets (len//4 ≤ 300) for all variants
  - ValueError on unknown condition or framing
  - Determinism: same inputs → same output, identity under cache
  - LRU cache: same object returned for repeated calls
  - build_round_messages: structure, disclosure, history, token budget
  - parse_rne_response: all 4 strategies, edge cases, failure modes

Run: pytest tests/test_rne_prompts.py -v
"""

from __future__ import annotations

import pytest

from src.prompts.rne_prompts import build_system_prompt, build_round_messages, parse_rne_response

_CONDITIONS = ("A", "B", "C")
_FRAMINGS = ("neutral", "social", "strategic")


class TestBuildSystemPromptAllVariants:
    """All 9 combinations must return a non-empty string within token budget."""

    @pytest.mark.parametrize("condition", _CONDITIONS)
    @pytest.mark.parametrize("framing", _FRAMINGS)
    def test_returns_nonempty_string(self, condition, framing):
        """build_system_prompt returns a non-empty str for every valid pair."""
        result = build_system_prompt(condition, framing)
        assert isinstance(result, str), f"{condition}/{framing}: expected str"
        assert len(result) > 50, f"{condition}/{framing}: result too short ({len(result)} chars)"

    @pytest.mark.parametrize("condition", _CONDITIONS)
    @pytest.mark.parametrize("framing", _FRAMINGS)
    def test_within_token_budget(self, condition, framing):
        """Token estimate (len//4) must be ≤ 300 for every variant."""
        result = build_system_prompt(condition, framing)
        tok = len(result) // 4
        assert tok <= 300, (
            f"{condition}/{framing}: {tok} tokens exceeds budget of 300"
        )


class TestBuildSystemPromptDeterminism:
    """Same inputs must always produce the same output."""

    @pytest.mark.parametrize("condition", _CONDITIONS)
    @pytest.mark.parametrize("framing", _FRAMINGS)
    def test_deterministic(self, condition, framing):
        """Two separate calls return identical strings."""
        a = build_system_prompt(condition, framing)
        b = build_system_prompt(condition, framing)
        assert a == b, f"{condition}/{framing}: non-deterministic output"

    def test_cache_identity(self):
        """LRU cache must return the same object (not just equal) on repeat calls."""
        first = build_system_prompt("A", "neutral")
        second = build_system_prompt("A", "neutral")
        assert first is second, "Expected cached object identity (lru_cache)"


class TestBuildSystemPromptErrors:
    """Unknown condition or framing must raise ValueError."""

    def test_unknown_condition_raises(self):
        with pytest.raises(ValueError, match="Unknown condition"):
            build_system_prompt("X", "neutral")

    def test_unknown_framing_raises(self):
        with pytest.raises(ValueError, match="Unknown framing"):
            build_system_prompt("A", "aggressive")

    def test_both_unknown_raises(self):
        """ValueError raised when both condition and framing are unknown."""
        with pytest.raises(ValueError):
            build_system_prompt("Z", "propaganda")

    def test_empty_condition_raises(self):
        with pytest.raises(ValueError, match="Unknown condition"):
            build_system_prompt("", "neutral")

    def test_empty_framing_raises(self):
        with pytest.raises(ValueError, match="Unknown framing"):
            build_system_prompt("A", "")

    def test_lowercase_condition_raises(self):
        """Conditions are case-sensitive: 'a' is not 'A'."""
        with pytest.raises(ValueError, match="Unknown condition"):
            build_system_prompt("a", "neutral")


class TestBuildSystemPromptContent:
    """Spot-check that condition-specific language appears in the prompt."""

    def test_condition_a_mentions_coordination(self):
        """Condition A prompt should reference coordination."""
        s = build_system_prompt("A", "neutral")
        assert "coordination" in s.lower() or "coordinate" in s.lower(), (
            "Condition A prompt should mention coordination"
        )

    def test_condition_b_mentions_defect_or_exploit(self):
        """Condition B prompt should reference defection/exploitation."""
        s = build_system_prompt("B", "neutral")
        assert any(w in s.lower() for w in ("defect", "exploit", "betray")), (
            "Condition B prompt should mention defect/exploit/betray"
        )

    def test_condition_c_mentions_power(self):
        """Condition C prompt should reference power or asymmetry."""
        s = build_system_prompt("C", "neutral")
        assert any(w in s.lower() for w in ("power", "asymmetric", "unfair", "reject")), (
            "Condition C prompt should mention power/asymmetry/rejection"
        )

    def test_neutral_framing_no_cooperative_language(self):
        """Neutral framing should not use overtly cooperative framing words."""
        s = build_system_prompt("A", "neutral")
        # Should not start with social/partner language
        assert "partner" not in s[:100].lower(), (
            "Neutral framing should not open with partnership language"
        )

    def test_social_framing_mentions_partner(self):
        """Social framing should reference partnership or marketplace."""
        s = build_system_prompt("A", "social")
        assert any(w in s.lower() for w in ("partner", "marketplace", "relationship")), (
            "Social framing should mention partner/marketplace/relationship"
        )

    def test_strategic_framing_mentions_maximise(self):
        """Strategic framing should reference maximising value."""
        s = build_system_prompt("A", "strategic")
        assert any(w in s.lower() for w in ("maximis", "maximiz", "highest", "exploit")), (
            "Strategic framing should mention maximising/highest"
        )

    def test_all_variants_mention_json_output(self):
        """All variants must include JSON output instructions."""
        for cond in _CONDITIONS:
            for framing in _FRAMINGS:
                s = build_system_prompt(cond, framing)
                assert "json" in s.lower(), (
                    f"{cond}/{framing}: prompt must include JSON output instructions"
                )

    def test_all_variants_mention_decay(self):
        """All variants must reference resource decay."""
        for cond in _CONDITIONS:
            for framing in _FRAMINGS:
                s = build_system_prompt(cond, framing)
                assert "decay" in s.lower(), (
                    f"{cond}/{framing}: prompt must mention decay"
                )


# ===========================================================================
# Tests for build_round_messages
# ===========================================================================

def _make_blind_config(**kwargs):
    from src.simulation.config import RNEConfig
    defaults = dict(family_a="mistral", family_b="llama", condition="A",
                    disclosure="blind", prompt_framing="neutral")
    defaults.update(kwargs)
    return RNEConfig(**defaults)


def _make_disclosed_config(**kwargs):
    from src.simulation.config import RNEConfig
    defaults = dict(family_a="mistral", family_b="llama", condition="A",
                    disclosure="disclosed", prompt_framing="neutral")
    defaults.update(kwargs)
    return RNEConfig(**defaults)


_INVENTORY = {"W": 3, "S": 2, "G": 0, "C": 1}
_HISTORY_5 = ["r1: traded", "r2: no trade", "r3: traded", "r4: no trade", "r5: traded"]


class TestBuildRoundMessagesStructure:
    """Message list structure must be [system, user]."""

    def test_returns_list_of_two_dicts(self):
        cfg = _make_blind_config()
        msgs = build_round_messages(cfg, 1, "a0", _INVENTORY, [])
        assert isinstance(msgs, list)
        assert len(msgs) == 2

    def test_first_message_is_system(self):
        cfg = _make_blind_config()
        msgs = build_round_messages(cfg, 1, "a0", _INVENTORY, [])
        assert msgs[0]["role"] == "system"
        assert isinstance(msgs[0]["content"], str)
        assert len(msgs[0]["content"]) > 50

    def test_second_message_is_user(self):
        cfg = _make_blind_config()
        msgs = build_round_messages(cfg, 1, "a0", _INVENTORY, [])
        assert msgs[1]["role"] == "user"
        assert isinstance(msgs[1]["content"], str)
        assert len(msgs[1]["content"]) > 5

    def test_round_number_in_user_message(self):
        cfg = _make_blind_config()
        msgs = build_round_messages(cfg, 7, "a0", _INVENTORY, [])
        assert "7" in msgs[1]["content"]

    def test_total_rounds_in_user_message(self):
        cfg = _make_blind_config()
        msgs = build_round_messages(cfg, 7, "a0", _INVENTORY, [])
        # cfg.rounds == 35 by default
        assert "35" in msgs[1]["content"]

    def test_inventory_in_user_message(self):
        cfg = _make_blind_config()
        msgs = build_round_messages(cfg, 1, "a0", {"W": 3, "S": 2, "G": 0, "C": 0}, [])
        user = msgs[1]["content"]
        assert "W:3" in user or "W: 3" in user
        assert "S:2" in user or "S: 2" in user

    def test_empty_inventory_shows_empty(self):
        cfg = _make_blind_config()
        msgs = build_round_messages(cfg, 1, "a0", {"W": 0, "S": 0, "G": 0, "C": 0}, [])
        assert "empty" in msgs[1]["content"]

    def test_zero_resources_omitted_from_inventory(self):
        """Zero-quantity resources should not appear in inventory string."""
        cfg = _make_blind_config()
        msgs = build_round_messages(cfg, 1, "a0", {"W": 3, "S": 0, "G": 0, "C": 0}, [])
        user = msgs[1]["content"]
        # S:0 should not appear; W:3 should
        assert "S:0" not in user
        assert "G:0" not in user

    def test_system_uses_build_system_prompt(self):
        """System content must equal the cached system prompt exactly."""
        cfg = _make_blind_config()
        expected_system = build_system_prompt(cfg.condition, cfg.prompt_framing)
        msgs = build_round_messages(cfg, 1, "a0", _INVENTORY, [])
        assert msgs[0]["content"] == expected_system


class TestBuildRoundMessagesDisclosure:
    """Disclosure injection — blind and disclosed conditions."""

    @pytest.mark.parametrize("condition", _CONDITIONS)
    @pytest.mark.parametrize("framing", _FRAMINGS)
    def test_blind_no_family_name_in_any_message(self, condition, framing):
        """Blind condition: opponent family name must not appear anywhere."""
        cfg = _make_blind_config(condition=condition, prompt_framing=framing)
        msgs = build_round_messages(cfg, 5, "a0", _INVENTORY, [], opponent_family="llama")
        combined = " ".join(m["content"] for m in msgs)
        assert "llama" not in combined, (
            f"{condition}/{framing}/blind: 'llama' leaked into messages"
        )

    @pytest.mark.parametrize("condition", _CONDITIONS)
    @pytest.mark.parametrize("framing", _FRAMINGS)
    def test_disclosed_family_name_in_user_message(self, condition, framing):
        """Disclosed condition: opponent family name must appear in user message."""
        cfg = _make_disclosed_config(condition=condition, prompt_framing=framing)
        msgs = build_round_messages(cfg, 5, "a0", _INVENTORY, [], opponent_family="llama")
        assert "llama" in msgs[1]["content"], (
            f"{condition}/{framing}/disclosed: 'llama' missing from user message"
        )

    def test_disclosed_family_name_not_in_system_message(self):
        """Disclosed injection must go into user message only, not system."""
        cfg = _make_disclosed_config()
        msgs = build_round_messages(cfg, 5, "a0", _INVENTORY, [], opponent_family="llama")
        assert "llama" not in msgs[0]["content"], (
            "Family name must not appear in system message (user only)"
        )

    def test_blind_with_none_opponent_family(self):
        """Blind with no opponent_family provided: no family name appears."""
        cfg = _make_blind_config()
        msgs = build_round_messages(cfg, 1, "a0", _INVENTORY, [], opponent_family=None)
        combined = " ".join(m["content"] for m in msgs)
        assert "llama" not in combined
        assert "mistral" not in combined

    def test_disclosed_with_none_opponent_family_no_injection(self):
        """Disclosed but opponent_family=None: no family name injected."""
        cfg = _make_disclosed_config()
        msgs = build_round_messages(cfg, 1, "a0", _INVENTORY, [], opponent_family=None)
        combined = " ".join(m["content"] for m in msgs)
        assert "llama" not in combined

    def test_disclosed_contains_model_label(self):
        """Disclosed message should contain 'model' near the family name."""
        cfg = _make_disclosed_config()
        msgs = build_round_messages(cfg, 5, "a0", _INVENTORY, [], opponent_family="llama")
        assert "model" in msgs[1]["content"].lower(), (
            "Disclosed user message should mention 'model'"
        )


class TestBuildRoundMessagesHistory:
    """History injection — last ≤3 rounds only."""

    def test_no_history_no_recent_section(self):
        cfg = _make_blind_config()
        msgs = build_round_messages(cfg, 1, "a0", _INVENTORY, [])
        assert "history" not in msgs[1]["content"].lower() or \
               "r1:" not in msgs[1]["content"]

    def test_history_last_3_rounds_present(self):
        cfg = _make_blind_config()
        msgs = build_round_messages(cfg, 6, "a0", _INVENTORY, _HISTORY_5)
        user = msgs[1]["content"]
        # r3, r4, r5 should appear (last 3 of 5)
        assert "r3" in user
        assert "r4" in user
        assert "r5" in user

    def test_history_older_rounds_excluded(self):
        """Only last 3 history entries must appear; earlier ones excluded."""
        cfg = _make_blind_config()
        msgs = build_round_messages(cfg, 6, "a0", _INVENTORY, _HISTORY_5)
        user = msgs[1]["content"]
        # r1 and r2 should not appear in history
        assert "r1:" not in user
        assert "r2:" not in user

    def test_history_single_entry(self):
        cfg = _make_blind_config()
        msgs = build_round_messages(cfg, 2, "a0", _INVENTORY, ["r1: traded"])
        assert "r1" in msgs[1]["content"]

    def test_history_exactly_3_entries_all_present(self):
        cfg = _make_blind_config()
        hist3 = ["r1: traded", "r2: no trade", "r3: traded"]
        msgs = build_round_messages(cfg, 4, "a0", _INVENTORY, hist3)
        user = msgs[1]["content"]
        assert "r1" in user
        assert "r2" in user
        assert "r3" in user


class TestBuildRoundMessagesTokenBudget:
    """Combined token budget must be ≤ 400 for any valid input combination."""

    @pytest.mark.parametrize("condition", _CONDITIONS)
    @pytest.mark.parametrize("framing", _FRAMINGS)
    @pytest.mark.parametrize("disclosure", ["blind", "disclosed"])
    def test_within_400_token_budget(self, condition, framing, disclosure):
        from src.simulation.config import RNEConfig
        cfg = RNEConfig(family_a="mistral", family_b="llama",
                        condition=condition, disclosure=disclosure,
                        prompt_framing=framing)
        msgs = build_round_messages(
            cfg, round_num=5, agent_id="a0",
            inventory={"W": 3, "S": 2, "G": 1, "C": 1},
            history=_HISTORY_5,
            opponent_family="llama",
        )
        total_chars = sum(len(m["content"]) for m in msgs)
        total_tok = total_chars // 4
        assert total_tok <= 400, (
            f"{condition}/{framing}/{disclosure}: {total_tok} tokens exceeds 400"
        )


# ===========================================================================
# Tests for parse_rne_response
# ===========================================================================


class TestParseRNEResponse:
    """Tolerant 4-strategy parser — all must-have behaviors and edge cases."""

    # --- Strategy 1: direct json.loads ---

    def test_clean_json_propose(self):
        """Strategy 1: well-formed propose JSON parses directly."""
        result = parse_rne_response('{"action":"propose","give":{"W":1},"want":{"G":1}}')
        assert isinstance(result, dict)
        assert result["action"] == "propose"
        assert result["give"] == {"W": 1}
        assert result["want"] == {"G": 1}

    def test_clean_json_pass(self):
        """Strategy 1: well-formed pass JSON parses directly."""
        result = parse_rne_response('{"action":"pass"}')
        assert result == {"action": "pass"}

    def test_clean_json_accept(self):
        """Strategy 1: well-formed accept JSON parses directly."""
        result = parse_rne_response('{"action":"accept"}')
        assert result == {"action": "accept"}

    def test_clean_json_with_note(self):
        """Strategy 1: JSON with optional note field parses correctly."""
        result = parse_rne_response('{"action":"propose","give":{"W":2},"want":{"G":2},"note":"fair deal"}')
        assert result is not None
        assert result["note"] == "fair deal"

    def test_clean_json_with_whitespace(self):
        """Strategy 1: leading/trailing whitespace handled."""
        result = parse_rne_response('  {"action":"pass"}  ')
        assert result == {"action": "pass"}

    # --- Strategy 2: markdown fence stripping ---

    def test_markdown_fence_json_tag(self):
        """Strategy 2: ```json fence stripped before parse."""
        result = parse_rne_response('```json\n{"action":"pass"}\n```')
        assert result == {"action": "pass"}

    def test_markdown_fence_no_tag(self):
        """Strategy 2: plain ``` fence stripped before parse."""
        result = parse_rne_response('```\n{"action":"pass"}\n```')
        assert result == {"action": "pass"}

    def test_markdown_fence_propose(self):
        """Strategy 2: markdown-wrapped propose action parses correctly."""
        raw = '```json\n{"action":"propose","give":{"S":1},"want":{"C":1}}\n```'
        result = parse_rne_response(raw)
        assert result is not None
        assert result["action"] == "propose"

    # --- Strategy 3: bracket-counter extraction ---

    def test_prose_wrapped_json(self):
        """Strategy 3: JSON embedded in prose extracted correctly."""
        result = parse_rne_response('Sure! {"action":"pass"} here you go')
        assert result == {"action": "pass"}

    def test_prose_prefix_only(self):
        """Strategy 3: JSON after prose prefix extracted correctly."""
        result = parse_rne_response('My response is: {"action":"propose","give":{"W":1},"want":{"G":1}}')
        assert result is not None
        assert result["action"] == "propose"

    def test_prose_suffix_only(self):
        """Strategy 3: JSON before trailing prose extracted correctly."""
        result = parse_rne_response('{"action":"pass"} — passing this round.')
        assert result == {"action": "pass"}

    def test_nested_json_in_prose(self):
        """Strategy 3: nested dict within JSON extracted correctly."""
        raw = 'Here is my action: {"action":"propose","give":{"W":2},"want":{"G":3}}'
        result = parse_rne_response(raw)
        assert result is not None
        assert result["give"] == {"W": 2}

    # --- Strategy 4: None on unrecoverable input ---

    def test_truncated_json_returns_none(self):
        """Strategy 4: truncated JSON (unbalanced braces) returns None."""
        result = parse_rne_response('{"action":"prop')
        assert result is None

    def test_empty_string_returns_none(self):
        """Strategy 4: empty string returns None."""
        result = parse_rne_response('')
        assert result is None

    def test_none_input_returns_none(self):
        """Strategy 4: None input returns None."""
        result = parse_rne_response(None)
        assert result is None

    def test_whitespace_only_returns_none(self):
        """Strategy 4: whitespace-only string returns None."""
        result = parse_rne_response('   \n\t  ')
        assert result is None

    def test_pure_prose_returns_none(self):
        """Strategy 4: pure prose with no JSON object returns None."""
        result = parse_rne_response('I will pass this round.')
        assert result is None

    def test_json_array_extracts_inner_dict(self):
        """Strategy 3: JSON array wrapping a dict — inner dict extracted via bracket scan."""
        # parse_rne_response is tolerant: it uses bracket-counter extraction to
        # recover the inner {"action":"pass"} dict even when the LLM wraps it
        # in an array.  Returning the usable dict is correct behavior.
        result = parse_rne_response('[{"action":"pass"}]')
        assert result == {"action": "pass"}

    def test_bare_json_array_no_dict_returns_none(self):
        """Strategy 4: JSON array with no inner dict object returns None."""
        result = parse_rne_response('["pass", "reject"]')
        assert result is None

    def test_partial_fence_no_close_returns_none(self):
        """Strategy 4: fence opened but never closed with truncated JSON."""
        result = parse_rne_response('```json\n{"action":"prop')
        assert result is None

    # --- Return type invariant ---

    def test_returns_dict_or_none(self):
        """parse_rne_response always returns dict or None — never raises."""
        inputs = [
            '{"action":"pass"}',
            '```json\n{"action":"pass"}\n```',
            'prose {"action":"pass"} end',
            '{"action":"prop',
            '',
            None,
            'garbage!@#$%',
            '{"action":',
        ]
        for inp in inputs:
            result = parse_rne_response(inp)
            assert result is None or isinstance(result, dict), (
                f"Expected dict or None for input {inp!r}, got {type(result)}"
            )

    def test_does_not_raise_on_arbitrary_input(self):
        """parse_rne_response must not raise on any string input."""
        evil_inputs = [
            "null",
            "true",
            "false",
            "12345",
            '"just a string"',
            "{{{{",
            "}}}}",
            "{" * 1000,
            '{"action": "' + "x" * 10000 + '"}',
        ]
        for inp in evil_inputs:
            try:
                parse_rne_response(inp)
            except Exception as exc:  # noqa: BLE001
                pytest.fail(f"parse_rne_response raised {exc!r} on input {inp[:50]!r}")
