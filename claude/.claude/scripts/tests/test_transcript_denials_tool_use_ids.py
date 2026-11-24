"""Tests for denials.hook_denials_in_record and denials.hook_denied_tool_use_ids, the record walk that finds
which main-thread Skill and spawn tool_use blocks one of this repository's gates denied.

In the transcript format, `hookEvent` sits inside `attachment` beside `hookName` and `toolUseID`.
"""
import pytest
from transcript_analysis import denials, review_rounds, review_trace

from ._review_round_helpers import _SONNET
from ._routing_guard_helpers import _routing_deny_record
from .conftest import (
    _agent_use,
    _asst,
    _bash_use,
    _declared_deny_gate_label,
    _hook_deny,
    _hook_deny_current,
    _skill_block,
)

_BRANCH = "feat-alpha"


def _launch(tool_use_id: str, *, tool_name: str = "Skill") -> dict:
    """A main-thread assistant record holding the review call a denial's tool_use_id joins."""
    if tool_name == "Skill":
        block = _skill_block(tool_use_id, "code-review")
    else:
        block = _agent_use(tool_use_id, "review-orchestrator", tool_name=tool_name)
    return _asst(_SONNET, branch=_BRANCH, content=[block])


def _legacy_denial(tool_use_id: str, **attachment_fields) -> dict:
    """A legacy hook_blocking_error attachment of an unlisted hook; a field set to None is removed."""
    record = _hook_deny("unlisted-hook", branch=_BRANCH)
    record["attachment"]["toolUseID"] = tool_use_id
    for field, value in attachment_fields.items():
        if value is None:
            record["attachment"].pop(field, None)
        else:
            record["attachment"][field] = value
    return record


def _shipped_gate_result(tool_use_id: str, hook_file: str, *, is_error: bool = True) -> dict:
    """A current-shape result worded as the hook in `hook_file` words its own denial."""
    label = _declared_deny_gate_label(hook_file)
    message = f"Blocked by {label} gate: body"
    assert denials._denial_hook_label("", message) == label
    return _hook_deny_current(message, tool_id=tool_use_id, branch=_BRANCH, is_error=is_error)


class TestHookDenialsInRecord:

    @pytest.mark.parametrize("denial_record", [
        pytest.param(_routing_deny_record("deny-legacy", shape="legacy"), id="attachment-with-a-dict-error"),
        pytest.param(_hook_deny("alpha-gate", stringified=True), id="attachment-with-a-stringified-error"),
        pytest.param(_routing_deny_record("deny-current", shape="current"), id="is-error-tool-result"),
        pytest.param(_hook_deny_current("Blocked by alpha gate: body", tool_id="deny-other"), id="other-gate-tool-result"),
    ])
    def test_a_denial_record_carries_the_same_tool_use_id_hook_name_and_message_as_in_review_trace(self, denial_record):
        records = [_asst(_SONNET, branch=_BRANCH), denial_record]

        events, _tool_use_commands, _pre_regime = review_trace._review_trace_session_events(records, None, None, None)

        trace_denials = [
            (event["tool_use_id"], event["hook_name"], event["message"]) for event in events if event["kind"] == "denial"
        ]
        assert len(trace_denials) == 1
        assert list(denials.hook_denials_in_record(denial_record)) == trace_denials


class TestHookDeniedToolUseIds:

    @pytest.mark.parametrize(("records", "expected_ids"), [
        pytest.param(
            [_launch("deny-routing"), _routing_deny_record("deny-routing", shape="current")], {"deny-routing"},
            id="a-routing-gate-result-denial",
        ),
        pytest.param(
            [_launch("deny-spawn", tool_name="Agent"), _routing_deny_record("deny-spawn", shape="current")],
            {"deny-spawn"},
            id="a-routing-gate-result-denial-of-an-agent-spawn",
        ),
        pytest.param(
            [_launch("deny-task", tool_name="Task"), _routing_deny_record("deny-task", shape="legacy")],
            {"deny-task"},
            id="a-legacy-attachment-denial-of-a-task-spawn",
        ),
        pytest.param(
            [_launch("deny-legacy"), _legacy_denial("deny-legacy")], {"deny-legacy"},
            id="a-legacy-attachment-whose-hook-is-unlisted-and-names-no-event",
        ),
        pytest.param(
            [_launch("deny-pre-tool-use"), _legacy_denial("deny-pre-tool-use", hookEvent="PreToolUse")],
            {"deny-pre-tool-use"},
            id="a-legacy-attachment-naming-the-pre-tool-use-event",
        ),
        pytest.param(
            [_launch("deny-unnamed"), _legacy_denial("deny-unnamed", hookName=None)], {"deny-unnamed"},
            id="a-legacy-attachment-with-no-hook-name-and-no-shipped-gate-wording",
        ),
        pytest.param(
            [_launch("deny-merge"), _shipped_gate_result("deny-merge", "block-gh-pr-merge.sh")], {"deny-merge"},
            id="a-result-worded-as-another-shipped-gate",
        ),
    ])
    def test_a_denied_call_is_collected_by_its_tool_use_id(self, records, expected_ids):
        assert denials.hook_denied_tool_use_ids(records) == frozenset(expected_ids)

    @pytest.mark.parametrize("records", [
        pytest.param(
            [_launch("errored-call"), _hook_deny_current("File not found", tool_id="errored-call", branch=_BRANCH)],
            id="an-is-error-result-with-no-denial-text",
        ),
        pytest.param(
            [
                _launch("other-hook"),
                _hook_deny_current("Blocked by alpha gate: body", tool_id="other-hook", branch=_BRANCH),
            ],
            id="a-result-whose-idiom-names-only-a-hook-this-repository-does-not-ship",
        ),
        pytest.param(
            [_launch("deny-sidechain"), {**_routing_deny_record("deny-sidechain", shape="current"), "isSidechain": True}],
            id="a-sidechain-records-denial",
        ),
        pytest.param(
            [{**_launch("deny-sidechain-launch"), "isSidechain": True}, _routing_deny_record("deny-sidechain-launch")],
            id="a-denial-of-a-sidechain-launch",
        ),
        pytest.param(
            [_launch("deny-subagent-stop"), _legacy_denial("deny-subagent-stop", hookEvent="SubagentStop")],
            id="a-legacy-attachment-naming-the-subagent-stop-event",
        ),
        pytest.param(
            [_launch("deny-stop"), _legacy_denial("deny-stop", hookEvent="Stop")],
            id="a-legacy-attachment-naming-the-stop-event",
        ),
        pytest.param(
            [_launch("unjoined-call"), _legacy_denial("", toolUseID=None)],
            id="a-legacy-attachment-with-no-tool-use-id",
        ),
        pytest.param(
            [_launch("quoted-call"), _shipped_gate_result("quoted-call", "block-gh-pr-merge.sh", is_error=False)],
            id="a-non-error-result-quoting-a-shipped-gate",
        ),
        pytest.param(
            [_launch("launched-call"), _routing_deny_record("another-call", shape="current")],
            id="a-denial-joining-no-launched-call",
        ),
    ])
    def test_a_call_that_was_not_denied_by_a_shipped_gate_is_left_out(self, records):
        assert denials.hook_denied_tool_use_ids(records) == frozenset()

    @pytest.mark.parametrize("attachment_type", [
        pytest.param("hook_success", id="a-hook-that-allowed-the-call"),
        pytest.param("hook_non_blocking_error", id="a-hook-that-errored-without-blocking"),
    ])
    def test_a_pre_tool_use_attachment_that_did_not_block_the_call_is_left_out(self, attachment_type):
        """A hook that lets a call through writes an attachment carrying that call's id; only a block is a denial."""
        allowed_attachment = {
            "type": "attachment",
            "attachment": {
                "type": attachment_type, "hookName": "PreToolUse:Skill", "hookEvent": "PreToolUse",
                "toolUseID": "allowed-call",
            },
        }

        assert denials.hook_denied_tool_use_ids([_launch("allowed-call"), allowed_attachment]) == frozenset()

    def test_a_launch_with_an_empty_id_is_not_paired_with_a_denial_carrying_an_empty_id_and_still_opens_a_round(self):
        records = [_launch(""), _legacy_denial("")]

        assert denials.hook_denied_tool_use_ids(records) == frozenset()
        assert review_rounds.detect_round_windows(records) == [(0, 2, "code-review")]

    def test_an_errored_result_whose_content_is_a_list_of_text_blocks_naming_a_shipped_gate_is_collected(self):
        denial_result = _shipped_gate_result("list-content-call", "block-gh-pr-merge.sh")
        denial_block = denial_result["message"]["content"][0]
        denial_block["content"] = [{"type": "text", "text": denial_block["content"]}]

        assert denials.hook_denied_tool_use_ids([_launch("list-content-call"), denial_result]) == frozenset(
            {"list-content-call"}
        )

    @pytest.mark.parametrize("denial_record", [
        pytest.param(_routing_deny_record("bash-call", shape="current"), id="a-result-denial"),
        pytest.param(_routing_deny_record("bash-call", shape="legacy"), id="a-legacy-attachment-denial"),
    ])
    def test_a_denied_call_that_is_neither_a_skill_nor_a_spawn_is_not_collected(self, denial_record):
        launch = _asst(_SONNET, branch=_BRANCH, content=[_bash_use("bash-call", "git status")])

        # The Skill launch keeps the candidate set non-empty so the join check runs.
        assert denials.hook_denied_tool_use_ids([_launch("skill-call"), launch, denial_record]) == frozenset()

    def test_the_denial_text_of_a_result_joining_no_skill_or_spawn_is_never_matched(self, monkeypatch):
        def fail_on_any_match(item):
            raise AssertionError(f"denial classifier ran over {item!r}")

        monkeypatch.setattr(denials, "hook_denial_key", fail_on_any_match)
        skill_launch = _launch("skill-call")
        launch = _asst(_SONNET, branch=_BRANCH, content=[_bash_use("bash-call", "git status")])
        errored_result = _routing_deny_record("bash-call", shape="current")

        assert denials.hook_denied_tool_use_ids([skill_launch, launch, errored_result]) == frozenset()

    @pytest.mark.parametrize("refusal_text", [
        pytest.param(
            "The user doesn't want to proceed with this tool use. The tool use was rejected "
            "(eg. if it was a file edit, the new_string was NOT written to the file). "
            "STOP what you are doing and wait for the user to tell you how to proceed.",
            id="a-user-rejection",
        ),
        pytest.param("Permission to use Skill has been denied.", id="a-permission-rule-refusal"),
        pytest.param(
            "Auto mode declined this action: it was not covered by the permissions you granted.",
            id="an-auto-mode-refusal",
        ),
    ])
    def test_a_refusal_by_the_permission_layer_or_auto_mode_is_left_out(self, refusal_text):
        records = [
            _launch("refused-call"),
            _hook_deny_current(refusal_text, tool_id="refused-call", branch=_BRANCH),
        ]

        assert denials.hook_denied_tool_use_ids(records) == frozenset()

    def test_an_errored_agent_result_quoting_a_shipped_gate_is_collected_as_the_documented_residual(self):
        """The residual docs/transcript-analysis.md's round-detection caveat names: a subagent that ran and
        errored with text quoting a shipped gate's wording loses its round, an undercount."""
        records = [
            _launch("ran-agent", tool_name="Agent"),
            _hook_deny_current(
                "Subagent failed: the commit was Blocked by code-review gate: body", tool_id="ran-agent",
                branch=_BRANCH,
            ),
        ]

        assert denials.hook_denied_tool_use_ids(records) == frozenset({"ran-agent"})

    @pytest.mark.parametrize("malformed_record", [
        pytest.param({"type": "user", "message": "not an object"}, id="a-truthy-non-object-message"),
        pytest.param({"type": "user", "message": {"content": 5}}, id="a-non-iterable-content"),
        pytest.param({"type": "attachment", "attachment": "not an object"}, id="a-truthy-non-object-attachment"),
        pytest.param(
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "unreadable-call", "is_error": True,
                 "content": [{"type": "text", "text": 5}]},
            ]}},
            id="a-non-string-text-in-an-errored-result",
        ),
        pytest.param(
            {"type": "attachment", "attachment": {"type": "hook_blocking_error", "toolUseID": ["unhashable"]}},
            id="an-unhashable-attachment-tool-use-id",
        ),
    ])
    def test_a_record_of_an_unreadable_shape_contributes_no_id_and_does_not_raise(self, malformed_record):
        records = [_launch("unreadable-call"), malformed_record]

        assert denials.hook_denied_tool_use_ids(records) == frozenset()
