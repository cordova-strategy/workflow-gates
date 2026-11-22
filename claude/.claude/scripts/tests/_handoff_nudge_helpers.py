"""Test helpers shared by the handoff-nudge family's test files and by
test_transcript_analysis_multi_root_scope.py's and
test_transcript_analysis_listing_scope.py's cross-subcommand tables."""
import argparse
import json
from pathlib import Path

from transcript_analysis import handoff_nudge

from .conftest import _bash_use, _priced, _tool_result, _user_msg, _write_jsonl


def _spend_over_threshold_args(since: str | None = None, projects: str = "*") -> argparse.Namespace:
    return type("A", (), {"projects": projects, "this_repo": False, "since": since})()


def _rearm_backtest_args(
    *,
    projects: str = "*",
    this_repo: bool = False,
    since: str | None = None,
    branches: str | None = None,
    no_redact: bool = False,
    extra_config_dirs: list[str] | None = None,
    spacings: str | None = None,
) -> object:
    return type("A", (), {
        "projects": projects,
        "this_repo": this_repo,
        "since": since,
        "branches": branches,
        "no_redact": no_redact,
        "extra_config_dirs": extra_config_dirs,
        "spacings": spacings,
    })()


def _handoff_signal_response_args(
    *, projects: str = "*", this_repo: bool = False, config_dir: str | None = None,
    no_redact: bool = False, sample: int = 0, seed: int | None = None,
    output_format: str = "json", context_turns: int = 0,
) -> object:
    return type("A", (), {
        "projects": projects,
        "this_repo": this_repo,
        "config_dir": config_dir,
        "no_redact": no_redact,
        "sample": sample,
        "seed": seed,
        "output_format": output_format,
        "context_turns": context_turns,
    })()


def _write_signal_with_excerpt_session(project_dir: Path, excerpt: str) -> None:
    """One session holding one over-threshold signal followed by an assistant text turn reading `excerpt`."""
    _write_jsonl(project_dir / f"sess-{excerpt}.jsonl", [
        _check_call_turn(input=200_000, output=1_000, request_id="r1"),
        _user_msg([_tool_result("chk1", _check_result_json(over_threshold=True))]),
        _priced(
            "claude-sonnet-5", input=210_000, output=500, request_id="r2",
            content=[{"type": "text", "text": excerpt}],
        ),
    ])


def _handoff_cards(stdout: str) -> list[dict]:
    """The curation cards of a `handoff-signal-response --sample` json run, whose first stdout line is the scope header."""
    header_line_dropped = stdout.split("\n", 1)[1]
    return json.loads(header_line_dropped)


def _ramp_curve_from_records(*sessions_records: list[dict]) -> tuple[dict[str, dict[str, float]], int]:
    """Build _ramp_curve_from_corpus's own input the way _rearm_backtest_report
    does -- one _extract_rearm_session_turns call per session's raw records --
    for TestRampCurveFromCorpus's synthetic-records tests."""
    return handoff_nudge._ramp_curve_from_corpus(handoff_nudge._extract_rearm_session_turns(recs) for recs in sessions_records)


def _check_result_json(
    *, status: str = "ok", over_threshold: bool = False, already_fired: bool = False,
    estimate: int = 200_000, threshold: int = 150_000,
) -> str:
    """The exact JSON shape nudge-handoff-near-context-cap.sh --check prints
    (run_check_mode's own jq -n object)."""
    return json.dumps({
        "status": status, "session_id": "s", "estimate": estimate, "threshold": threshold,
        "over_threshold": over_threshold, "model": "claude-sonnet-5", "context_window": 1_000_000,
        "model_recognized": True, "already_fired": already_fired, "nudge_disabled": False,
    })


def _handoff_advisory_attachment() -> dict:
    """The real advisory-fire attachment record shape (a "hook_success"
    attachment whose stdout is nudge-handoff-near-context-cap.sh's own
    injected-additionalContext JSON envelope)."""
    return {
        "type": "attachment",
        "attachment": {
            "type": "hook_success",
            "command": "~/.claude/hooks/nudge-handoff-near-context-cap.sh",
            "hookEvent": "PostToolBatch",
            "stdout": json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PostToolBatch",
                    "additionalContext": (
                        "Context is past this session's handoff-nudge threshold (150000 tokens)."
                        " If the current task is not close to done, suggest running /handoff to the"
                        " user. If the task is nearly complete, ignore this and finish -- judge that"
                        " by what the remaining work costs, not by how many steps are left."
                    ),
                },
            }),
            "stderr": "",
            "exitCode": 0,
        },
    }


def _check_call_turn(tool_id: str = "chk1", **usage_kwargs) -> dict:
    """A main-thread assistant turn whose only tool call is the real --check
    invocation (handoff/SKILL.md's own command text)."""
    return _priced(
        "claude-sonnet-5",
        content=[_bash_use(tool_id, "~/.claude/hooks/nudge-handoff-near-context-cap.sh --check")],
        **usage_kwargs,
    )
