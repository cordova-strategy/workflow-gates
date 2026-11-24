"""Roots-file seam of relocate-claude-config.sh: reader and runner state handling, and parity with _config_dir.py."""
from __future__ import annotations

import os
import re
from pathlib import Path

import _config_dir
import pytest
from helpers import build_path_without

from ._declared_dirs_helpers import (
    _READER_WARNING,
    _ROOTS_LABEL,
    _outcomes,
    _runner_scene_base,
    _stale_link,
    _write_roots_file,
)
from ._relocate_helpers import _run_sourced, requires_non_root

# ---------------------------------------------------------------------------
# Roots-file states: the runner never aborts the errexit-on main shell
# ---------------------------------------------------------------------------

_NO_DIR_STATES = ("missing", "directory", "empty", "comment-only", "unreadable")


@pytest.mark.parametrize(
    "state",
    [
        pytest.param("unreadable", marks=requires_non_root) if state == "unreadable" else state
        for state in (
            *_NO_DIR_STATES,
            "readlink-fails",
            "last-relative",
            "last-missing-dir",
            "last-duplicate",
            "no-readlink",
            "no-readlink-no-file",
        )
    ],
)
def test_reader_and_runner_survive_every_roots_file_state(tmp_path: Path, state: str) -> None:
    scene = _runner_scene_base(tmp_path)
    old_repo = tmp_path / "old-repo"
    roots_file = scene.home / ".claude" / "transcript-config-dirs"
    listed = tmp_path / "acct-listed"
    listed.mkdir()
    (tmp_path / "scratch" / "acct-relative").mkdir()
    unlisted_text = ""
    if state in _NO_DIR_STATES:
        unlisted = scene.home / "acct-unlisted"
        unlisted_text = _stale_link(unlisted, "hooks", old_repo)
    prelude = ""
    path = None
    expected_warning_lines: list[int] = []
    listed_lines = {
        "readlink-fails": [str(listed)],
        "last-relative": [str(listed), "acct-relative"],
        "last-missing-dir": [str(listed), str(tmp_path / "acct-missing")],
        "last-duplicate": [str(listed), str(listed)],
    }
    if state == "directory":
        roots_file.mkdir()
    elif state == "empty":
        roots_file.write_text("")
    elif state == "comment-only":
        roots_file.write_text("# only a comment\n")
    elif state == "unreadable":
        roots_file.write_text("/never/read\n")
        roots_file.chmod(0o000)
    elif state == "readlink-fails":
        _write_roots_file(scene.home, listed_lines[state])
        prelude = "readlink() { return 1; }\n"
        expected_warning_lines = [1]
    elif state in listed_lines:
        _write_roots_file(scene.home, listed_lines[state])
        expected_warning_lines = [] if state == "last-duplicate" else [2]
    elif state == "no-readlink":
        _write_roots_file(scene.home, [str(listed)])
        unlisted_text = _stale_link(listed, "hooks", old_repo)
        farm = tmp_path / "farm"
        farm.mkdir()
        path = build_path_without("readlink", farm)
    elif state == "no-readlink-no-file":
        farm = tmp_path / "farm"
        farm.mkdir()
        path = build_path_without("readlink", farm)
    try:
        run = _run_sourced(
            scene.home,
            [["relink_declared_dirs", str(scene.new_repo)], 'echo "survived"'],
            cwd=scene.scratch,
            prelude=prelude,
            bare=True,
            path=path,
        )
    finally:
        if state == "unreadable":
            roots_file.chmod(0o644)

    assert run.returncode == 0, run.stderr
    assert "survived\n" in run.tail
    expected_stderr = [
        f"relocate-claude-config: {_READER_WARNING.format(line=line)}" for line in expected_warning_lines
    ]
    if state == "no-readlink":
        expected_stderr = [
            f"relocate-claude-config: readlink is not available, so no dir listed in {_ROOTS_LABEL} is re-linked"
        ]
        assert "checking" not in run.stdout and "walking" not in run.stdout
        assert _outcomes(run.stdout) == []
    assert run.stderr.splitlines() == expected_stderr
    if state in _NO_DIR_STATES:
        assert os.readlink(scene.home / "acct-unlisted" / "hooks") == unlisted_text
    if state == "no-readlink":
        assert os.readlink(listed / "hooks") == unlisted_text
    assert not (scene.home / ".claude-config-relocate-backup").exists()


# ---------------------------------------------------------------------------
# The bash reader against _config_dir.py's parser
# ---------------------------------------------------------------------------


def _warned_lines(stderr: str, pattern: str) -> list[int]:
    return [int(match.group(1)) for match in re.finditer(pattern, stderr)]


def test_reader_matches_config_dir_parser(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    # Only the absolute-path check rejects the relative line: a real directory has its name.
    (scratch / "acct-relative").mkdir()
    padded = home / "acct-padded"
    tab_padded = tmp_path / "acct-tab"
    crlf = tmp_path / "acct-crlf"
    mid_hash = tmp_path / "acct-mid#line"
    regular_file = tmp_path / "acct-regular-file"
    linked_dir = tmp_path / "real-parent" / "acct-linked"
    awkward = tmp_path / "acct-w]`@*\\$(touch injected)"
    non_ascii = tmp_path / "acct-caf\u00e9-\u65e5\u672c"
    last = tmp_path / "acct-last"
    for directory in (padded, tab_padded, crlf, mid_hash, linked_dir, awkward, non_ascii, last):
        directory.mkdir(parents=True)
    regular_file.write_text("not a directory\n")
    (tmp_path / "link-parent").symlink_to(tmp_path / "real-parent")
    lines = [
        "# a comment",
        "",
        "   # an indented comment",
        "   ",
        "\r",
        "  ~/acct-padded  ",
        f"\t{tab_padded}\t",
        f"{crlf}\r",
        "~",
        str(mid_hash),
        "~acct-user/x",
        "acct-relative",
        str(tmp_path / "acct-missing"),
        str(regular_file),
        str(tab_padded),
        str(linked_dir),
        str(tmp_path / "link-parent" / "acct-linked"),
        str(awkward),
        str(awkward),
        str(non_ascii),
        str(last),
    ]
    roots_file = _write_roots_file(home, lines, final_newline=False)

    run = _run_sourced(
        home,
        [["read_declared_config_dirs"], 'printf "%s\\n" "${DECLARED_CONFIG_DIRS[@]}"'],
        cwd=scratch,
    )
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("TRANSCRIPT_CONFIG_DIRS_FILE", str(roots_file))
    monkeypatch.chdir(scratch)
    python_roots = _config_dir.declared_roots_matching(Path.is_dir, warn_prefix="parity")
    python_warned = _warned_lines(capsys.readouterr().err, r"declared root (\d+) unreadable")

    assert run.call_statuses == [0], run.stderr
    bash_rows = [row.split("\t", 1) for row in run.stdout.splitlines() if "\t" in row]
    assert [Path(path) for _, path in bash_rows] == [root.resolve() for root in python_roots]
    assert _warned_lines(run.stderr, r"line (\d+) of ~/\.claude/transcript-config-dirs is not an absolute") == python_warned
    for line_number, path in bash_rows:
        listed_line = lines[int(line_number) - 1].strip()
        listed_line = str(home) if listed_line == "~" else listed_line.replace("~/", f"{home}/", 1)
        assert Path(listed_line).resolve() == Path(path)
    assert not (scratch / "injected").exists()


def test_reader_and_parser_both_give_nothing_for_a_directory_roots_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = tmp_path / "home"
    (home / ".claude" / "transcript-config-dirs").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("TRANSCRIPT_CONFIG_DIRS_FILE", str(home / ".claude" / "transcript-config-dirs"))
    capsys.readouterr()

    run = _run_sourced(home, [["read_declared_config_dirs"], 'echo "rows=${#DECLARED_CONFIG_DIRS[@]}"'], cwd=tmp_path)
    python_roots = _config_dir.declared_roots_matching(Path.is_dir, warn_prefix="parity")

    assert run.call_statuses == [0], run.stderr
    assert "rows=0\n" in run.tail
    assert run.stderr == ""
    assert python_roots == []
    assert capsys.readouterr().err == ""
