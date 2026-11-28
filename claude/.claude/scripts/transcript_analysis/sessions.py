"""The sessions command: cmd_sessions, the resolved scope's transcript paths one per line,
plus split subagent files under --include-subagents, and its subparser registration.

Imports corpus and scope by module (attribute access, not by name) -- see
scope.py's own top-of-file comment for why.
"""
from __future__ import annotations

import argparse
import sys

from transcript_analysis import corpus, scope


def cmd_sessions(args: argparse.Namespace) -> None:
    """Emit transcript file paths for the resolved scope, one absolute path per line.

    Reads the active account unless --this-repo, --all-accounts or the top-level
    --config-dir sets the scope.

    --paths is required: it names the one action this subcommand supports today,
    leaving room for a second sessions action later without a bare `sessions`
    invocation silently doing nothing. Sourced from scope.resolve_scan_roots plus
    scope._resolve_project_scope (not a flat glob). Scope follows `--this-repo`'s
    rule; see "Scoping to this repo" in docs/transcript-analysis.md.
    --include-subagents additionally emits each split subagent
    file's own path, listed by the same corpus._session_source_files call
    read_session_file uses -- <session>/subagents/*.jsonl under the main
    file's own directory -- rather than a flat glob across the whole scope.
    The reader drops an unreadable or empty subagent file from its merge and
    this command still prints it. The resolved-scope header goes to stderr,
    matching audit-routing-samples' convention — stdout here is meant to be
    piped to xargs/Read, not mixed with a header line.
    """
    if not bool(getattr(args, "paths", False)):
        print("sessions: --paths is required (no other sessions action exists yet)", file=sys.stderr)
        sys.exit(2)

    include_subagents = bool(getattr(args, "include_subagents", False))
    active_account_only = scope._narrows_to_active_account(args)
    roots = scope.resolve_scan_roots(args, active_account_only=active_account_only)
    session_iter, scope_label = scope._resolve_project_scope(
        args, "sessions", include_subagents=include_subagents, roots=roots
    )
    scope.print_resolved_scope("sessions", scope_label, roots, file=sys.stderr, active_account_only=active_account_only)
    for jsonl, _records in session_iter:
        print(jsonl)
        if include_subagents:
            for sub_jsonl in corpus._session_source_files(jsonl, include_subagents)[1:]:
                print(sub_jsonl)


def _add_sessions_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Register the sessions subparser on build_parser()'s subparsers action,
    binding cmd_sessions through set_defaults(func=...).
    """
    p_sessions = subparsers.add_parser(
        "sessions",
        help="Emit transcript file paths for the resolved scope, one absolute path per line.",
    )
    scope._add_project_scope_args(p_sessions, this_repo_help=scope._POOLED_THIS_REPO_HELP)
    scope._add_all_accounts_arg(p_sessions)
    p_sessions.add_argument(
        "--paths", action="store_true",
        help="Print one absolute transcript path per line (the only sessions action today; required).",
    )
    p_sessions.add_argument(
        "--include-subagents", action="store_true",
        help="Also emit split subagent transcript paths under <session>/subagents/*.jsonl.",
    )
    p_sessions.set_defaults(func=cmd_sessions)
