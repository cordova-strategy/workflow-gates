"""Text the `--this-repo`-only commands print about their scope, and the report-parsing and unreadable-path helpers
test_transcript_skill_reinjection.py uses. Each template is spelled out here, not read from `publication_scope`, so a
change to its wording fails a test."""
import contextlib
import os
import stat


def refusal_without_this_repo(command_label: str) -> str:
    return f"{command_label}: requires --this-repo and refuses any --projects scope -- see docs/transcript-analysis.md\n"


def refusal_with_several_roots(command_label: str) -> str:
    return f"{command_label}: resolved to more than one root -- refusing to report a multi-account figure\n"


def scope_header(command_label: str, scope_label: str) -> str:
    title = command_label.upper().replace("-", " ")
    return (
        f"{title} SOURCES ({scope_label}; reads one account (the active account), the working directory's repository"
        " only; ~/.claude/transcript-config-dirs not consulted)"
    )


def labelled_counts(report: str, line_prefix: str) -> dict[str, int]:
    """The `key=count` tokens of the report line starting with `line_prefix`, e.g. `skipped input:`."""
    line = next(line for line in report.splitlines() if line.startswith(line_prefix))
    tokens = line.removeprefix(line_prefix).split()
    return {key: int(value.replace(",", "")) for key, value in (token.split("=") for token in tokens)}


@contextlib.contextmanager
def unreadable(path):
    """Removes every permission bit from `path` and restores the mode it had on entry, before `tmp_path` teardown."""
    original_mode = stat.S_IMODE(os.stat(path).st_mode)
    os.chmod(path, 0o000)
    try:
        yield
    finally:
        os.chmod(path, original_mode)
