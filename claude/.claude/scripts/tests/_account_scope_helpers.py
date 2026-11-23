"""Helpers shared by the tests of which accounts a narrowed command reads: test_transcript_analysis_listing_scope.py,
test_transcript_analysis_multi_root_scope.py, test_transcript_scope_active_account.py,
test_transcript_skill_invocation.py and test_transcript_handoff_signal_response.py."""
from collections.abc import Callable
from pathlib import Path

from ._skill_helpers import _review_asst, _user_reply
from .conftest import _skill_use_rec, _write_jsonl

# One distinct value per account in the two-root fixtures, printed raw by whichever field a command exposes.
ACTIVE_ROOT_SENTINEL = "aaaa1111"
DECLARED_ROOT_SENTINEL = "bbbb2222"
NAMED_ACCOUNT_SENTINEL = "cccc3333"
SHARED_PROJECT_SLUG = "-home-user-sharedrepo"
SESSION_TS = "2026-05-20T10:00:00.000Z"

# A literal, not derived from scope._root_count_desc, so it stays an independent pin on the header wording.
ACTIVE_ACCOUNT_CLAUSE = (
    "1 root (active account only; --this-repo or --all-accounts also reads ~/.claude/transcript-config-dirs)"
)


def _sessions_args() -> object:
    """Args object for cmd_sessions listing paths, with no widening flag set."""
    return type("A", (), {"projects": "*", "this_repo": False, "paths": True, "include_subagents": False})()


def seed_one_session_per_root(
    roots: list[Path],
    write_session: Callable[[Path, str], None],
    project_slug: str = SHARED_PROJECT_SLUG,
    markers: tuple[str, ...] = (ACTIVE_ROOT_SENTINEL, DECLARED_ROOT_SENTINEL),
) -> None:
    """Seed each root's `project_slug` directory with one session carrying that root's marker.

    `roots` and `markers` must have the same length (zip strict), so a root added to a fixture without a marker
    fails here instead of seeding a root that no "not in output" assertion can detect.
    """
    for root, marker in zip(roots, markers, strict=True):
        project_dir = root / project_slug
        project_dir.mkdir(parents=True, exist_ok=True)
        write_session(project_dir, marker)


def write_skill_name_session(project_dir: Path, marker: str) -> None:
    """One session invoking a skill named `marker`, printed raw by skill-invocation."""
    _write_jsonl(project_dir / "sess.jsonl", [_skill_use_rec(marker, SESSION_TS)])


def write_judgment_pair_session(project_dir: Path, marker: str) -> None:
    """One code-review skill use, its review text and the user's reply, with `marker` in the file name and the review text."""
    _write_jsonl(project_dir / f"{marker}.jsonl", [
        _skill_use_rec("code-review", SESSION_TS),
        _review_asst(f"Logic error in retry loop ({marker}).", "2026-05-20T10:01:00.000Z"),
        _user_reply("Will fix the retry logic."),
    ])
