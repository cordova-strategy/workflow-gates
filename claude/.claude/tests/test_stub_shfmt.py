"""Contract tests for the shfmt helpers in helpers.py: `write_stub_shfmt`, `require_shfmt` and `production_shfmt_argv`."""
from __future__ import annotations

import subprocess
import time

import helpers
import pytest
from helpers import (
    StubShfmtCall,
    _sourced_value,
    decode_shfmt_argv,
    production_shfmt_argv,
    require_shfmt,
    write_stub_shfmt,
)


def test_a_parse_call_prints_the_tree_and_logs_argv_stdin_and_working_directory(tmp_path):
    working_directory = tmp_path / "work"
    working_directory.mkdir()
    stub = write_stub_shfmt(tmp_path / "shfmt", tree='{"Type":"File"}', exit_status=3)

    result = subprocess.run(
        [str(stub.path), "-ln", "bash", "--to-json"], input=b"echo hi\n", capture_output=True, cwd=working_directory, check=False
    )

    assert (result.returncode, result.stdout) == (3, b'{"Type":"File"}')
    assert stub.calls() == [
        StubShfmtCall(argv=["-ln", "bash", "--to-json"], stdin=b"echo hi\n", cwd=str(working_directory.resolve()))
    ]


def test_a_version_call_prints_the_version_line_and_reads_no_stdin(tmp_path):
    stub = write_stub_shfmt(tmp_path / "shfmt", tree="unused", version_line="v3.14.0")

    result = subprocess.run([str(stub.path), "--version"], capture_output=True, check=False)

    assert (result.returncode, result.stdout) == (0, b"v3.14.0\n")
    assert [call.argv for call in stub.calls()] == [["--version"]]
    assert stub.calls()[0].stdin == b""


def test_the_default_version_line_is_the_empty_line_a_macports_build_prints(tmp_path):
    stub = write_stub_shfmt(tmp_path / "shfmt")

    result = subprocess.run([str(stub.path), "--version"], capture_output=True, check=False)

    assert result.stdout == b"\n"


def test_stderr_line_is_written_before_the_exit(tmp_path):
    stub = write_stub_shfmt(tmp_path / "shfmt", stderr_line="1:1: boom", exit_status=1)

    result = subprocess.run([str(stub.path)], input=b"", capture_output=True, check=False)

    assert (result.returncode, result.stderr) == (1, b"1:1: boom\n")


def test_calls_accumulate_in_order(tmp_path):
    stub = write_stub_shfmt(tmp_path / "shfmt")

    subprocess.run([str(stub.path), "first"], input=b"one", capture_output=True, check=True)
    subprocess.run([str(stub.path), "second"], input=b"two", capture_output=True, check=True)

    assert [(call.argv, call.stdin) for call in stub.calls()] == [(["first"], b"one"), (["second"], b"two")]


@pytest.mark.timing
@pytest.mark.parametrize("ignore_sigterm", [False, True], ids=["honors-sigterm", "ignores-sigterm"])
def test_a_hanging_parse_call_ends_on_sigterm_only_when_it_honors_it(tmp_path, ignore_sigterm):
    # The hang only has to outlast the test, which kills the process in `finally`.
    stub = write_stub_shfmt(tmp_path / "shfmt", hang_parse_seconds=60, ignore_sigterm=ignore_sigterm)
    process = subprocess.Popen([str(stub.path)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    process.stdin.write(b"echo hi\n")
    process.stdin.close()
    try:
        # The stub writes its stdin log just before it hangs, so that file shows it is into the hang.
        # The stub either writes that file or exits, so this loop ends.
        while not (stub.log_dir / "call-0.stdin").exists():
            assert process.poll() is None, "the stub exited before it hung"
            time.sleep(0.01)
        process.terminate()
        # Neither wait has a vendor source. 1 s only has to show the process outlived the SIGTERM, and 10 s bounds a prompt exit.
        if ignore_sigterm:
            with pytest.raises(subprocess.TimeoutExpired):
                process.wait(timeout=1)
        else:
            assert process.wait(timeout=10) == -15
    finally:
        process.kill()
        process.wait()
        process.stdout.close()
        process.stderr.close()


def test_a_hanging_version_call_leaves_a_parse_call_unaffected(tmp_path):
    stub = write_stub_shfmt(tmp_path / "shfmt", tree="ok", hang_version_seconds=60)

    result = subprocess.run([str(stub.path)], input=b"", capture_output=True, check=False)

    assert result.stdout == b"ok"


@pytest.mark.timing
def test_a_hanging_version_call_outlasts_the_caller_until_it_is_killed(tmp_path):
    stub = write_stub_shfmt(tmp_path / "shfmt", version_line="v3.14.0", hang_version_seconds=60)
    process = subprocess.Popen([str(stub.path), "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        # No vendor source: a stub that did not hang would exit in milliseconds, so 1 s only has to show it is still running.
        with pytest.raises(subprocess.TimeoutExpired):
            process.wait(timeout=1)
    finally:
        process.kill()
        process.wait()
        process.stdout.close()
        process.stderr.close()


def test_a_version_call_honors_the_exit_status_and_the_stderr_line(tmp_path):
    stub = write_stub_shfmt(tmp_path / "shfmt", version_line="v3.14.0", exit_status=4, stderr_line="version boom")

    result = subprocess.run([str(stub.path), "--version"], capture_output=True, check=False)

    assert (result.returncode, result.stdout, result.stderr) == (4, b"v3.14.0\n", b"version boom\n")


@pytest.mark.parametrize(
    "sent_bytes",
    [b"a\r\nb\r", b"\xff", b"a\xffb", b"x\n", b"x\n\n\n", b"\n\n", b" leading space", b"", b"\\", b"\\\n"],
    ids=[
        "carriage-returns", "lone-0xff", "0xff-in-text", "one-newline",
        "trailing-newlines", "only-newlines", "leading-space", "empty", "lone-backslash", "backslash-newline-pair",
    ],
)
def test_the_logged_stdin_equals_the_bytes_sent(tmp_path, sent_bytes):
    stub = write_stub_shfmt(tmp_path / "shfmt")

    subprocess.run([str(stub.path)], input=sent_bytes, capture_output=True, check=True)

    assert [call.stdin for call in stub.calls()] == [sent_bytes]


def test_a_call_with_no_argument_logs_an_empty_argv_distinct_from_one_empty_argument(tmp_path):
    stub = write_stub_shfmt(tmp_path / "shfmt")

    subprocess.run([str(stub.path)], input=b"", capture_output=True, check=True)
    subprocess.run([str(stub.path), ""], input=b"", capture_output=True, check=True)

    assert [call.argv for call in stub.calls()] == [[], [""]]


class TestRequireShfmt:
    def test_returns_when_shfmt_is_on_path(self, tmp_path, monkeypatch):
        write_stub_shfmt(tmp_path / "shfmt")
        monkeypatch.setenv("PATH", str(tmp_path))
        require_shfmt()

    def test_skips_outside_ci_naming_the_workflow_that_pins_the_build(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PATH", str(tmp_path))
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
        with pytest.raises(pytest.skip.Exception, match=r"install the build that \.github/workflows/tests\.yml pins"):
            require_shfmt()

    def test_fails_under_github_actions(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PATH", str(tmp_path))
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        with pytest.raises(pytest.fail.Exception, match="shfmt missing in CI"):
            require_shfmt()


def test_production_shfmt_argv_is_the_shell_arrays_words():
    argv = production_shfmt_argv()
    assert argv[0] == "shfmt"
    assert all(argv)
    positions = [argv.index(word) for word in ("-ln", "bash", "--to-json")]
    assert positions == sorted(positions)
    assert argv[argv.index("-ln") + 1] == "bash"


class TestDecodeShfmtArgv:
    def test_returns_each_nul_terminated_word(self):
        assert decode_shfmt_argv(b"shfmt\0-ln\0bash\0") == ["shfmt", "-ln", "bash"]

    @pytest.mark.parametrize(
        "printed_words",
        [b"", b"\0", b"shfmt\0\0--to-json\0"],
        ids=["nothing-printed", "unset-array", "empty-word"],
    )
    def test_fails_with_the_named_message_on_no_word_or_an_empty_word(self, printed_words):
        with pytest.raises(AssertionError, match="_LIB_SHFMT_ARGV gave no word or an empty word"):
            decode_shfmt_argv(printed_words)


class TestLibShReaders:
    """`production_shfmt_argv` and `_sourced_value` share one reader, which carries a refused source's cause to the report."""

    @pytest.fixture
    def lib_that_refuses_to_source(self, tmp_path, monkeypatch):
        refusing_lib = tmp_path / "_lib.sh"
        refusing_lib.write_text("echo 'older than the bash this repo requires' >&2\nreturn 1\n")
        monkeypatch.setattr(helpers, "_LIB_SH", refusing_lib)

    @pytest.mark.parametrize(
        "read_from_lib",
        [production_shfmt_argv, lambda: _sourced_value("ANY_NAME")],
        ids=["production-shfmt-argv", "sourced-value"],
    )
    def test_a_lib_that_refuses_to_source_fails_with_its_stderr_and_exit_status(self, lib_that_refuses_to_source, read_from_lib):
        with pytest.raises(AssertionError, match="exited 1: older than the bash this repo requires"):
            read_from_lib()

    def test_a_lib_path_holding_a_quote_and_a_space_still_sources(self, tmp_path, monkeypatch):
        odd_directory = tmp_path / "it's a dir"
        odd_directory.mkdir()
        odd_lib = odd_directory / "_lib.sh"
        odd_lib.write_text("_LIB_SHFMT_ARGV=(shfmt -ln bash --to-json)\n")
        monkeypatch.setattr(helpers, "_LIB_SH", odd_lib)
        assert production_shfmt_argv() == ["shfmt", "-ln", "bash", "--to-json"]
