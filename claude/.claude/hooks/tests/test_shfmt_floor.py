"""Tests for tests.yml's shfmt pin -- the CI step that installs the shfmt build the shell-syntax-tree tests run on.

Sections:

- the pin's literals: a dotted version and a SHA-256 digest;
- the step's place: it runs in both legs, after the stow step;
- the runner's shfmt is the pin, which shows the step ran;
- the step's `run:` body, executed against stub `curl`, `sudo`, `install` and `shfmt` commands and the real `sha256sum`.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
from helpers import ci_test_slice_job

_PIN_STEP_ID = "pin-shfmt"
_STOW_STEP_NAME = "Install stow and direnv"

# Bounds a hung local bash run; no vendor value applies.
_BASH_RUN_TIMEOUT_SECONDS = 60

_BASH = shutil.which("bash") or "bash"

# Where the step installs shfmt on the runner, which is also where the step requires `command -v shfmt` to resolve.
_CI_SHFMT_INSTALL_PATH = "/usr/local/bin/shfmt"


def _pin_step() -> dict:
    """The `pin-shfmt` step of tests.yml's `test-slice` job, located by id."""
    pin_steps = [step for step in ci_test_slice_job()["steps"] if step.get("id") == _PIN_STEP_ID]
    assert len(pin_steps) == 1, (
        f"Expected exactly one step with id: {_PIN_STEP_ID} in tests.yml -- did the step move or get renamed?"
    )
    return pin_steps[0]


def _pin_step_env() -> dict:
    return _pin_step().get("env", {})


def _output_of(result: subprocess.CompletedProcess) -> str:
    return f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"


class TestPinLiterals:
    def test_the_version_is_a_quoted_dotted_three_field_version(self) -> None:
        pinned_version = _pin_step_env().get("CI_SHFMT_VERSION")
        assert isinstance(pinned_version, str), f"CI_SHFMT_VERSION must be a quoted string, got {pinned_version!r}"
        assert re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", pinned_version), pinned_version

    def test_the_digest_is_a_quoted_lowercase_sha256_hex_literal(self) -> None:
        pinned_digest = _pin_step_env().get("CI_SHFMT_SHA256")
        assert isinstance(pinned_digest, str), f"CI_SHFMT_SHA256 must be a quoted string, got {pinned_digest!r}"
        assert re.fullmatch(r"[0-9a-f]{64}", pinned_digest), pinned_digest


class TestPinStepPlacement:
    def test_the_step_runs_in_both_legs(self) -> None:
        condition = _pin_step()["if"]
        assert "steps.detect.outputs.changed == 'true'" in condition
        assert "matrix.slice" not in condition, f"the pin step must not name a leg: {condition!r}"

    def test_the_step_runs_after_the_stow_step(self) -> None:
        step_ids_and_names = [(step.get("id"), step.get("name")) for step in ci_test_slice_job()["steps"]]
        pin_position = next(i for i, (step_id, _) in enumerate(step_ids_and_names) if step_id == _PIN_STEP_ID)
        stow_position = next(i for i, (_, name) in enumerate(step_ids_and_names) if name == _STOW_STEP_NAME)
        assert stow_position < pin_position

    def test_the_step_precedes_every_pytest_step(self) -> None:
        steps = ci_test_slice_job()["steps"]
        pin_position = next(i for i, step in enumerate(steps) if step.get("id") == _PIN_STEP_ID)
        pytest_positions = [i for i, step in enumerate(steps) if str(step.get("run", "")).startswith("pytest")]
        assert pytest_positions, "vacuous check: no step whose run starts with pytest was found"
        assert all(pin_position < position for position in pytest_positions), (pin_position, pytest_positions)


@pytest.mark.skipif(
    not os.environ.get("GITHUB_ACTIONS"),
    reason="CI-only: compares the pinned build to the runner's installed shfmt",
)
def test_ci_shfmt_equals_the_pin() -> None:
    pinned_version = _pin_step_env()["CI_SHFMT_VERSION"]
    assert shutil.which("shfmt") == _CI_SHFMT_INSTALL_PATH, (
        f"CI resolves shfmt to {shutil.which('shfmt')!r}, not the {_CI_SHFMT_INSTALL_PATH} the {_PIN_STEP_ID} step installs"
    )
    running_shfmt = subprocess.run(
        ["shfmt", "--version"], capture_output=True, text=True, check=True, timeout=_BASH_RUN_TIMEOUT_SECONDS
    ).stdout.strip()
    assert running_shfmt.removeprefix("v") == pinned_version, (
        f"CI's `shfmt --version` printed {running_shfmt!r} but tests.yml's {_PIN_STEP_ID} step pins {pinned_version}."
        f" Either the step did not run before the tests, or the pin and the build it installs differ."
    )


# Differs from the workflow pin so a version hard-coded in the step body fails the tests.
_FIXTURE_VERSION = "9.99.0"
_FIXTURE_ASSET_BYTES = b"fixture shfmt bytes"
_FIXTURE_DIGEST = hashlib.sha256(_FIXTURE_ASSET_BYTES).hexdigest()
_OTHER_DIGEST = hashlib.sha256(b"other bytes").hexdigest()

# The logging stubs record `sudo ` ahead of a call that came through `sudo`.
# Each argument is logged wrapped in `<` `>`, so a space inside one argument stays visible.
_LOGGING_LINE = """{ printf '%s%s' "${STUB_VIA_SUDO:+sudo }" "${0##*/}"; printf ' <%s>' "$@"; printf '\\n'; } >> "$STUB_LOG"\n"""
_LOGGING_STUB = "#!/bin/bash\n" + _LOGGING_LINE
# The `curl` stub writes STUB_CURL_BODY to the path after `--output`.
# It exits 22 after an error line of its own when STUB_CURL_FAILS is set.
_CURL_STUB = (
    "#!/bin/bash\n"
    + _LOGGING_LINE
    + """if [ -n "${STUB_CURL_FAILS:-}" ]; then
  echo "curl: (22) stub fetch failed" >&2
  exit 22
fi
output=""
while [ "$#" -gt 0 ]; do
  [ "$1" = "--output" ] && output="$2"
  shift
done
printf '%s' "$STUB_CURL_BODY" > "$output"
"""
)
# `sudo` accepts only `install`, running the sibling stub with STUB_VIA_SUDO set, and exits 2 on any other command.
_SUDO_STUB = """#!/bin/bash
case "$1" in
  install) STUB_VIA_SUDO=1 exec "${0%/*}/$1" "${@:2}" ;;
  *) echo "sudo stub: unstubbed command $1" >&2; exit 2 ;;
esac
"""
# The `install` stub installs nothing. It logs the SHA-256 of the file it was asked to install, at the call, on a line of its own.
_INSTALL_STUB = _LOGGING_STUB + """read -r installed_digest _ < <(sha256sum "$3")
printf 'installed-digest <%s>\\n' "$installed_digest" >> "$STUB_LOG"
"""
# `shfmt` is a stub of its own, which the step's resolved-path check and final version print reach.
_SHFMT_STUB = _LOGGING_STUB + "echo 'v9.99.0'\n"

# The step's own sentences for a failed fetch and a failed check; the stubs' and sha256sum's lines do not contain them.
_FETCH_FAILURE_SENTENCE = "failed, so no digest was checked"
_DIGEST_FAILURE_SENTENCE = "does not match CI_SHFMT_SHA256"
_RESOLVED_PATH_FAILURE_SENTENCE = "so the tests would not parse with the pinned build"


def _write_executable(path: Path, text: str) -> None:
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def _require_sha256sum() -> str:
    """The real `sha256sum` the step's check runs. Skips locally without one, and fails under GITHUB_ACTIONS."""
    sha256sum_path = shutil.which("sha256sum")
    if sha256sum_path:
        return sha256sum_path
    if os.environ.get("GITHUB_ACTIONS"):
        pytest.fail("sha256sum missing in CI -- the pin step's check needs it")
    pytest.skip("sha256sum not installed; the pin step's check needs it")


def _run_pin_step(
    tmp_path: Path, *, env_overrides: dict[str, str] | None = None, another_shfmt_first_on_path: bool = False
) -> tuple[subprocess.CompletedProcess, list[str]]:
    """Run the `pin-shfmt` step's `run:` body under bash against stub commands; return the result and the stubs' call log.

    The stubs' directory stands in for /usr/local/bin.
    With `another_shfmt_first_on_path`, a second stub shfmt precedes it on PATH.
    """
    real_sha256sum = _require_sha256sum()
    real_mktemp = shutil.which("mktemp")
    assert real_mktemp, "no mktemp on PATH"
    stub_dir = tmp_path / "stubs"
    stub_dir.mkdir()
    for command, text in {
        "curl": _CURL_STUB,
        "sudo": _SUDO_STUB,
        "install": _INSTALL_STUB,
        "shfmt": _SHFMT_STUB,
    }.items():
        _write_executable(stub_dir / command, text)
    path_entries = [str(stub_dir)]
    if another_shfmt_first_on_path:
        other_dir = tmp_path / "other-shfmt"
        other_dir.mkdir()
        _write_executable(other_dir / "shfmt", _SHFMT_STUB)
        path_entries.insert(0, str(other_dir))
    (stub_dir / "sha256sum").symlink_to(real_sha256sum)
    (stub_dir / "mktemp").symlink_to(real_mktemp)
    call_log = tmp_path / "stub-calls.log"
    call_log.touch()
    script_path = tmp_path / "pin-shfmt-step.sh"
    script_path.write_text(_pin_step()["run"])

    env = {
        "PATH": os.pathsep.join(path_entries),
        "CI_SHFMT_INSTALL_DIR": str(stub_dir),
        "HOME": str(tmp_path),
        "TMPDIR": str(tmp_path),
        "STUB_LOG": str(call_log),
        "STUB_CURL_BODY": _FIXTURE_ASSET_BYTES.decode(),
        "CI_SHFMT_VERSION": _FIXTURE_VERSION,
        "CI_SHFMT_SHA256": _FIXTURE_DIGEST,
        **(env_overrides or {}),
    }
    result = subprocess.run(
        [_BASH, str(script_path)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        timeout=_BASH_RUN_TIMEOUT_SECONDS,
    )
    return result, call_log.read_text().splitlines()


def _calls_to(call_log: list[str], command: str) -> list[str]:
    return [line for line in call_log if line.startswith((f"{command} ", f"sudo {command} "))]


def _arguments_of(call_line: str) -> list[str]:
    return re.findall(r"<([^>]*)>", call_line)


class TestPinStepRunBody:
    """The fetch, the digest check and the install decide what CI runs on, so the `run:` body executes here against stubs."""

    def test_a_matching_digest_installs_the_downloaded_bytes_after_the_check_and_prints_the_version(
        self, tmp_path: Path
    ) -> None:
        result, call_log = _run_pin_step(tmp_path)

        assert result.returncode == 0, _output_of(result)
        assert [line.split(" ", 1)[0] for line in call_log] == ["curl", "sudo", "installed-digest", "shfmt"], call_log
        install_calls = _calls_to(call_log, "install")
        assert len(install_calls) == 1, call_log
        install_arguments = _arguments_of(install_calls[0])
        assert install_arguments[:2] == ["-m", "0755"], install_calls
        assert install_arguments[3] == str(tmp_path / "stubs" / "shfmt")
        assert _arguments_of(call_log[2]) == [_FIXTURE_DIGEST]
        assert _arguments_of(_calls_to(call_log, "shfmt")[0]) == ["--version"]
        assert f"shfmt resolved on PATH: {tmp_path / 'stubs' / 'shfmt'}" in result.stdout, _output_of(result)

    def test_the_fetch_carries_the_bounding_and_https_only_flags(self, tmp_path: Path) -> None:
        result, call_log = _run_pin_step(tmp_path)

        assert result.returncode == 0, _output_of(result)
        curl_arguments = _arguments_of(_calls_to(call_log, "curl")[0])
        for flag in ("--retry", "--retry-max-time", "--max-time"):
            assert flag in curl_arguments, curl_arguments
            assert curl_arguments[curl_arguments.index(flag) + 1].isdigit(), (flag, curl_arguments)
        for flag in ("--proto", "--proto-redir"):
            assert curl_arguments[curl_arguments.index(flag) + 1] == "=https", (flag, curl_arguments)

    def test_another_shfmt_earlier_on_path_exits_1_naming_the_resolved_path_after_the_install(self, tmp_path: Path) -> None:
        result, call_log = _run_pin_step(tmp_path, another_shfmt_first_on_path=True)

        assert result.returncode == 1, _output_of(result)
        assert _RESOLVED_PATH_FAILURE_SENTENCE in result.stderr, _output_of(result)
        assert str(tmp_path / "other-shfmt" / "shfmt") in result.stderr, _output_of(result)
        assert len(_calls_to(call_log, "install")) == 1, call_log
        assert _calls_to(call_log, "shfmt") == [], call_log

    def test_the_fetch_url_holds_the_version_from_the_env_and_not_the_workflow_pin(self, tmp_path: Path) -> None:
        result, call_log = _run_pin_step(tmp_path)

        assert result.returncode == 0, _output_of(result)
        fetched_urls = [argument for argument in _arguments_of(_calls_to(call_log, "curl")[0]) if "://" in argument]
        assert fetched_urls == [
            f"https://github.com/mvdan/sh/releases/download/v{_FIXTURE_VERSION}/shfmt_v{_FIXTURE_VERSION}_linux_amd64"
        ]
        assert _pin_step_env()["CI_SHFMT_VERSION"] not in fetched_urls[0]

    def test_a_digest_mismatch_exits_non_zero_names_the_check_and_makes_no_install_call(self, tmp_path: Path) -> None:
        result, call_log = _run_pin_step(tmp_path, env_overrides={"CI_SHFMT_SHA256": _OTHER_DIGEST})

        assert result.returncode != 0, _output_of(result)
        assert _DIGEST_FAILURE_SENTENCE in result.stderr, _output_of(result)
        assert _calls_to(call_log, "curl"), call_log
        assert _calls_to(call_log, "install") == [], call_log
        assert _calls_to(call_log, "shfmt") == [], call_log

    def test_a_failed_fetch_exits_1_names_the_fetch_and_makes_no_install_call(self, tmp_path: Path) -> None:
        result, call_log = _run_pin_step(tmp_path, env_overrides={"STUB_CURL_FAILS": "1"})

        assert result.returncode == 1, _output_of(result)
        assert _FETCH_FAILURE_SENTENCE in result.stderr, _output_of(result)
        assert "re-run the job first" in result.stderr, _output_of(result)
        assert _DIGEST_FAILURE_SENTENCE not in result.stderr, _output_of(result)
        assert "curl: (22) stub fetch failed" in result.stderr, _output_of(result)
        assert _calls_to(call_log, "install") == [], call_log
        assert _calls_to(call_log, "shfmt") == [], call_log

    @pytest.mark.parametrize("missing_key", ["CI_SHFMT_VERSION", "CI_SHFMT_SHA256"])
    def test_a_missing_key_exits_non_zero_naming_the_key_before_any_call(self, tmp_path: Path, missing_key: str) -> None:
        result, call_log = _run_pin_step(tmp_path, env_overrides={missing_key: ""})

        assert result.returncode != 0, _output_of(result)
        assert missing_key in result.stderr, _output_of(result)
        assert call_log == [], call_log
