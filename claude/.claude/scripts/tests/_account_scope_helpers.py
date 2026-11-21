"""Helpers shared by the tests of which accounts a narrowed command reads: test_transcript_analysis_listing_scope.py,
test_transcript_analysis_multi_root_scope.py, test_transcript_scope_active_account.py,
test_transcript_skill_invocation.py and test_transcript_handoff_signal_response.py."""

# One distinct value per account in the two-root fixtures, printed raw by whichever field a command exposes.
ACTIVE_ROOT_SENTINEL = "aaaa1111"
DECLARED_ROOT_SENTINEL = "bbbb2222"
NAMED_ACCOUNT_SENTINEL = "cccc3333"
SHARED_PROJECT_SLUG = "-home-user-sharedrepo"

# A literal, not derived from scope._root_count_desc, so it stays an independent pin on the header wording.
ACTIVE_ACCOUNT_CLAUSE = (
    "1 root (active account only; --this-repo or --all-accounts also reads ~/.claude/transcript-config-dirs)"
)


def _sessions_args() -> object:
    """Args object for cmd_sessions listing paths, with no widening flag set."""
    return type("A", (), {"projects": "*", "this_repo": False, "paths": True, "include_subagents": False})()
