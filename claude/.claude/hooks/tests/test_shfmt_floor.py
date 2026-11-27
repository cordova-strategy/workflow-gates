"""Tests for tests.yml's shfmt pin -- the CI step that installs the shfmt build the shell-syntax-tree tests run on.

Sections:

- the pin's literals: a dotted version and a SHA-256 digest;
- the step's place: it runs in both legs, after the stow step;
- the runner's shfmt is the pin, which shows the step ran;
- the step's `run:` body, executed against stub `curl` and `sudo`, a stub shfmt asset, the real `install` and `sha256sum`.
"""
from __future__ import annotations

import hashlib
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import NamedTuple

import pytest
from helpers import (
    PIN_STEP_LOGGING_STUB,
    StubShfmt,
    ci_test_slice_job,
    ci_test_slice_step,
    ci_tests_workflow,
    pin_step_calls_to,
    pin_step_sudo_stub,
    run_pin_step_script,
    write_stub_shfmt,
)
from helpers import completed_process_output as _output_of

_PIN_STEP_ID = "pin-shfmt"
_STOW_STEP_NAME = "Install stow and direnv"
_INSTALL_DIR_SEAM = "CI_SHFMT_INSTALL_DIR"

# Bounds a hung local bash run; no vendor value applies.
_BASH_RUN_TIMEOUT_SECONDS = 60

# Where the step installs shfmt on the runner, which is also where the step requires `command -v shfmt` to resolve.
_CI_SHFMT_INSTALL_PATH = "/usr/local/bin/shfmt"


def _pin_step() -> dict:
    return ci_test_slice_step(_PIN_STEP_ID)


def _pin_step_env() -> dict:
    return _pin_step().get("env", {})


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

    def test_no_workflow_job_or_step_env_sets_the_install_dir_seam(self) -> None:
        workflow = ci_tests_workflow()
        assert any(
            "CI_SHFMT_VERSION" in block for block in _env_blocks_of(workflow)
        ), "vacuous check: the pin step's env was not scanned"
        assert not _env_blocks_setting_the_install_dir_seam(workflow)


def _env_blocks_of(workflow: dict) -> list[dict]:
    """The workflow's own `env:` block, then each job's and each step's."""
    env_blocks = [workflow.get("env") or {}]
    for job in workflow["jobs"].values():
        env_blocks.append(job.get("env") or {})
        env_blocks.extend(step.get("env") or {} for step in job.get("steps") or [])
    return env_blocks


def _env_blocks_setting_the_install_dir_seam(workflow: dict) -> list[dict]:
    return [block for block in _env_blocks_of(workflow) if _INSTALL_DIR_SEAM in block]


class TestInstallDirSeamScan:
    """The scan flags the seam at each level of `env:`, and passes a workflow that does not set it."""

    SEAM_VALUE = {_INSTALL_DIR_SEAM: "/elsewhere"}

    def test_a_workflow_with_no_seam_in_any_env_block_is_clean(self) -> None:
        workflow = {"env": {"A": "1"}, "jobs": {"job": {"env": {"B": "2"}, "steps": [{"env": {"C": "3"}}, {"run": "true"}]}}}

        assert _env_blocks_setting_the_install_dir_seam(workflow) == []

    def test_a_workflow_with_no_env_blocks_at_all_is_clean(self) -> None:
        assert _env_blocks_setting_the_install_dir_seam({"jobs": {"job": {"steps": [{"run": "true"}]}}}) == []

    @pytest.mark.parametrize("level", ["workflow", "job", "step"])
    def test_the_seam_set_at_any_level_is_flagged(self, level: str) -> None:
        workflow = {"jobs": {"job": {"steps": [{"run": "true"}]}}}
        if level == "workflow":
            workflow["env"] = self.SEAM_VALUE
        elif level == "job":
            workflow["jobs"]["job"]["env"] = self.SEAM_VALUE
        else:
            workflow["jobs"]["job"]["steps"][0]["env"] = self.SEAM_VALUE

        assert _env_blocks_setting_the_install_dir_seam(workflow) == [self.SEAM_VALUE]


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
_OTHER_DIGEST = hashlib.sha256(b"other bytes").hexdigest()

# The `curl` stub writes STUB_CURL_BODY to the path after `--output`.
# It exits 22 after an error line of its own when STUB_CURL_FAILS is set.
_CURL_STUB = (
    PIN_STEP_LOGGING_STUB
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
# The `install` stub logs the SHA-256 of the file it was asked to install, at the call, on a line of its own.
# It then runs the real `install` on that file, or on STUB_INSTALL_ALTERNATE_SOURCE when that is set,
# so the installed bytes are checkable.
_INSTALL_STUB = (
    PIN_STEP_LOGGING_STUB
    + """read -r installed_digest _ < <(sha256sum "$3")
printf 'installed-digest <%s>\\n' "$installed_digest" >> "$STUB_LOG"
[ -z "${STUB_INSTALL_ALTERNATE_SOURCE:-}" ] || set -- "$1" "$2" "$STUB_INSTALL_ALTERNATE_SOURCE" "$4"
exec "$STUB_REAL_INSTALL" "$@"
"""
)

# A clause of the step's own message for each failure, held by that message and no other of the step's.
# The stubs' and sha256sum's lines do not contain them.
_FETCH_FAILURE_SENTENCE = "failed, so no digest was checked"
_DIGEST_FAILURE_SENTENCE = "so the binary was not installed"
_INSTALLED_DIGEST_FAILURE_SENTENCE = "The SHA-256 of the installed"
_RESOLVED_PATH_FAILURE_SENTENCE = "on PATH, not the installed"


def _require_sha256sum() -> str:
    """The real `sha256sum` the step's check runs. Skips locally without one, and fails under GITHUB_ACTIONS."""
    sha256sum_path = shutil.which("sha256sum")
    if sha256sum_path:
        return sha256sum_path
    if os.environ.get("GITHUB_ACTIONS"):
        pytest.fail("sha256sum missing in CI -- the pin step's check needs it")
    pytest.skip("sha256sum not installed; the pin step's check needs it")


class _PinStepRun(NamedTuple):
    result: subprocess.CompletedProcess
    call_log: list[str]
    asset_shfmt: StubShfmt  # The stub shfmt curl serves. Its installed copy logs to the same place.
    other_shfmt: StubShfmt | None
    asset_digest: str
    install_dir: Path


def _run_pin_step(
    tmp_path: Path,
    *,
    env_overrides: dict[str, str] | None = None,
    another_shfmt_first_on_path: bool = False,
    install_dir_on_path: bool = True,
    default_install_dir: bool = False,
) -> _PinStepRun:
    """Run the `pin-shfmt` step's `run:` body under bash against stub commands, a stub shfmt asset and the real `install`.

    The stubs' directory stands in for /usr/local/bin and is on PATH, unless `install_dir_on_path` is False.
    With `another_shfmt_first_on_path`, a second stub shfmt precedes it on PATH.
    With `default_install_dir`, the step gets no install directory, so its destination is /usr/local/bin
    and the `sudo` stub refuses the install, which writes nothing outside `tmp_path`.
    """
    real_sha256sum = _require_sha256sum()
    real_mktemp = shutil.which("mktemp")
    real_install = shutil.which("install")
    assert real_mktemp, "no mktemp on PATH"
    assert real_install, "no install on PATH"
    stub_dir = tmp_path / "stubs"
    stub_dir.mkdir()
    asset_dir = tmp_path / "asset"
    asset_dir.mkdir()
    asset_shfmt = write_stub_shfmt(asset_dir / "shfmt", version_line=f"v{_FIXTURE_VERSION}")
    asset_text = asset_shfmt.path.read_text()
    asset_digest = hashlib.sha256(asset_text.encode()).hexdigest()
    (stub_dir / "sha256sum").symlink_to(real_sha256sum)
    (stub_dir / "mktemp").symlink_to(real_mktemp)

    install_dir = stub_dir
    if not install_dir_on_path:
        install_dir = tmp_path / "off-path-install"
        install_dir.mkdir()
    path_entries = [str(stub_dir)]
    other_shfmt = None
    if another_shfmt_first_on_path:
        other_dir = tmp_path / "other-shfmt"
        other_dir.mkdir()
        other_shfmt = write_stub_shfmt(other_dir / "shfmt", version_line=f"v{_FIXTURE_VERSION}")
        path_entries.insert(0, str(other_dir))

    env = {
        "PATH": os.pathsep.join(path_entries),
        "TMPDIR": str(tmp_path),
        "STUB_CURL_BODY": asset_text,
        "STUB_REAL_INSTALL": real_install,
        "CI_SHFMT_VERSION": _FIXTURE_VERSION,
        "CI_SHFMT_SHA256": asset_digest,
    }
    if not default_install_dir:
        env[_INSTALL_DIR_SEAM] = str(install_dir)
    env.update(env_overrides or {})
    result, call_log = run_pin_step_script(
        tmp_path,
        _pin_step()["run"],
        stub_dir=stub_dir,
        stub_texts={
            "curl": _CURL_STUB,
            "sudo": pin_step_sudo_stub("install", install_root=tmp_path),
            "install": _INSTALL_STUB,
        },
        env=env,
        timeout_seconds=_BASH_RUN_TIMEOUT_SECONDS,
    )
    return _PinStepRun(result, call_log, asset_shfmt, other_shfmt, asset_digest, install_dir)


def _arguments_of(call_line: str) -> list[str]:
    return re.findall(r"<([^>]*)>", call_line)


class TestPinStepRunBody:
    """The fetch, the digest checks and the install decide what CI runs on, so the `run:` body executes here against stubs."""

    def test_a_matching_digest_installs_the_downloaded_bytes_after_the_check_and_prints_the_version(
        self, tmp_path: Path
    ) -> None:
        run = _run_pin_step(tmp_path)

        assert run.result.returncode == 0, _output_of(run.result)
        assert [line.split(" ", 1)[0] for line in run.call_log] == ["curl", "sudo", "installed-digest"], run.call_log
        install_calls = pin_step_calls_to(run.call_log, "install")
        assert len(install_calls) == 1, run.call_log
        install_arguments = _arguments_of(install_calls[0])
        assert install_arguments[:2] == ["-m", "0755"], install_calls
        assert install_arguments[3] == str(run.install_dir / "shfmt")
        assert _arguments_of(run.call_log[2]) == [run.asset_digest]
        assert [call.argv for call in run.asset_shfmt.calls()] == [["--version"]]
        assert f"shfmt resolved on PATH: {run.install_dir / 'shfmt'}" in run.result.stdout, _output_of(run.result)

    def test_the_fetch_carries_the_bounding_and_https_only_flags(self, tmp_path: Path) -> None:
        run = _run_pin_step(tmp_path)

        assert run.result.returncode == 0, _output_of(run.result)
        curl_arguments = _arguments_of(pin_step_calls_to(run.call_log, "curl")[0])
        for flag in ("--retry", "--retry-max-time", "--max-time"):
            assert flag in curl_arguments, curl_arguments
            assert curl_arguments[curl_arguments.index(flag) + 1].isdigit(), (flag, curl_arguments)
        for flag in ("--proto", "--proto-redir"):
            assert curl_arguments[curl_arguments.index(flag) + 1] == "=https", (flag, curl_arguments)

    def test_the_retry_window_exceeds_one_attempts_cap_so_a_timed_out_attempt_can_retry(self, tmp_path: Path) -> None:
        run = _run_pin_step(tmp_path)

        assert run.result.returncode == 0, _output_of(run.result)
        curl_arguments = _arguments_of(pin_step_calls_to(run.call_log, "curl")[0])
        retry_window_seconds = int(curl_arguments[curl_arguments.index("--retry-max-time") + 1])
        attempt_cap_seconds = int(curl_arguments[curl_arguments.index("--max-time") + 1])
        assert retry_window_seconds > attempt_cap_seconds, curl_arguments

    def test_the_fetch_fails_on_http_errors_follows_redirects_and_shows_its_error(self, tmp_path: Path) -> None:
        run = _run_pin_step(tmp_path)

        assert run.result.returncode == 0, _output_of(run.result)
        curl_arguments = _arguments_of(pin_step_calls_to(run.call_log, "curl")[0])
        for flag in ("--fail", "--location", "--silent", "--show-error"):
            assert flag in curl_arguments, (flag, curl_arguments)

    def test_another_shfmt_earlier_on_path_exits_1_naming_the_resolved_path_after_the_install(self, tmp_path: Path) -> None:
        run = _run_pin_step(tmp_path, another_shfmt_first_on_path=True)

        assert run.result.returncode == 1, _output_of(run.result)
        assert _RESOLVED_PATH_FAILURE_SENTENCE in run.result.stderr, _output_of(run.result)
        assert str(tmp_path / "other-shfmt" / "shfmt") in run.result.stderr, _output_of(run.result)
        assert len(pin_step_calls_to(run.call_log, "install")) == 1, run.call_log
        assert run.asset_shfmt.calls() == []
        assert run.other_shfmt is not None
        assert run.other_shfmt.calls() == []

    def test_an_install_dir_off_path_exits_1_reporting_that_no_shfmt_was_found(self, tmp_path: Path) -> None:
        run = _run_pin_step(tmp_path, install_dir_on_path=False)

        assert run.result.returncode == 1, _output_of(run.result)
        assert _RESOLVED_PATH_FAILURE_SENTENCE in run.result.stderr, _output_of(run.result)
        assert "shfmt resolves to 'none found'" in run.result.stderr, _output_of(run.result)
        assert len(pin_step_calls_to(run.call_log, "install")) == 1, run.call_log
        assert run.asset_shfmt.calls() == []

    def test_the_default_install_dir_is_usr_local_bin(self, tmp_path: Path) -> None:
        run = _run_pin_step(tmp_path, default_install_dir=True)

        install_calls = pin_step_calls_to(run.call_log, "install")
        assert len(install_calls) == 1, (run.call_log, _output_of(run.result))
        assert _arguments_of(install_calls[0])[3] == _CI_SHFMT_INSTALL_PATH

    def test_the_fetch_url_holds_the_version_from_the_env_and_not_the_workflow_pin(self, tmp_path: Path) -> None:
        run = _run_pin_step(tmp_path)

        assert run.result.returncode == 0, _output_of(run.result)
        fetched_urls = [
            argument for argument in _arguments_of(pin_step_calls_to(run.call_log, "curl")[0]) if "://" in argument
        ]
        assert fetched_urls == [
            f"https://github.com/mvdan/sh/releases/download/v{_FIXTURE_VERSION}/shfmt_v{_FIXTURE_VERSION}_linux_amd64"
        ]
        assert _pin_step_env()["CI_SHFMT_VERSION"] not in fetched_urls[0]

    def test_a_digest_mismatch_exits_non_zero_names_the_check_and_makes_no_install_call(self, tmp_path: Path) -> None:
        run = _run_pin_step(tmp_path, env_overrides={"CI_SHFMT_SHA256": _OTHER_DIGEST})

        assert run.result.returncode != 0, _output_of(run.result)
        assert _DIGEST_FAILURE_SENTENCE in run.result.stderr, _output_of(run.result)
        assert pin_step_calls_to(run.call_log, "curl"), run.call_log
        assert pin_step_calls_to(run.call_log, "install") == [], run.call_log
        assert run.asset_shfmt.calls() == []

    def test_installed_bytes_that_differ_from_the_checked_bytes_exit_1_naming_the_installed_file(
        self, tmp_path: Path
    ) -> None:
        # A logging stub shfmt with other bytes, so a run of the installed file would show in its log.
        alternate_dir = tmp_path / "alternate"
        alternate_dir.mkdir()
        alternate_shfmt = write_stub_shfmt(alternate_dir / "shfmt", version_line="v0.0.1")

        run = _run_pin_step(tmp_path, env_overrides={"STUB_INSTALL_ALTERNATE_SOURCE": str(alternate_shfmt.path)})

        assert run.result.returncode == 1, _output_of(run.result)
        assert _INSTALLED_DIGEST_FAILURE_SENTENCE in run.result.stderr, _output_of(run.result)
        assert str(run.install_dir / "shfmt") in run.result.stderr, _output_of(run.result)
        assert _DIGEST_FAILURE_SENTENCE not in run.result.stderr, _output_of(run.result)
        assert len(pin_step_calls_to(run.call_log, "install")) == 1, run.call_log
        assert alternate_shfmt.calls() == []

    def test_a_failed_fetch_exits_1_names_the_fetch_and_makes_no_install_call(self, tmp_path: Path) -> None:
        run = _run_pin_step(tmp_path, env_overrides={"STUB_CURL_FAILS": "1"})

        assert run.result.returncode == 1, _output_of(run.result)
        assert _FETCH_FAILURE_SENTENCE in run.result.stderr, _output_of(run.result)
        assert "re-run the job first" in run.result.stderr, _output_of(run.result)
        assert _DIGEST_FAILURE_SENTENCE not in run.result.stderr, _output_of(run.result)
        assert "curl: (22) stub fetch failed" in run.result.stderr, _output_of(run.result)
        assert pin_step_calls_to(run.call_log, "install") == [], run.call_log
        assert run.asset_shfmt.calls() == []

    @pytest.mark.parametrize("missing_key", ["CI_SHFMT_VERSION", "CI_SHFMT_SHA256"])
    def test_a_missing_key_exits_non_zero_naming_the_key_before_any_call(self, tmp_path: Path, missing_key: str) -> None:
        run = _run_pin_step(tmp_path, env_overrides={missing_key: ""})

        assert run.result.returncode != 0, _output_of(run.result)
        assert missing_key in run.result.stderr, _output_of(run.result)
        assert run.call_log == [], run.call_log


class TestSudoStubInstallRoot:
    """The run-body tests run the real `install`, so the `sudo` stub is what keeps a step that ignores the seam inside tmp_path.

    The test's `outside` directory stands in for /usr/local/bin and is itself under tmp_path.
    """

    def _sudo_install(self, tmp_path: Path, destination: str) -> tuple[subprocess.CompletedProcess, list[str]]:
        real_install = shutil.which("install")
        assert real_install, "no install on PATH"
        stub_dir = tmp_path / "stubs"
        stub_dir.mkdir()
        (tmp_path / "allowed").mkdir()
        (tmp_path / "outside").mkdir()
        source_file = tmp_path / "source"
        source_file.write_text("payload")
        return run_pin_step_script(
            tmp_path,
            f"sudo install -m 0755 {shlex.quote(str(source_file))} {shlex.quote(destination)}\n",
            stub_dir=stub_dir,
            stub_texts={
                "sudo": pin_step_sudo_stub("install", install_root=tmp_path / "allowed"),
                "install": f'#!/bin/bash\nexec {shlex.quote(real_install)} "$@"\n',
            },
            env={"PATH": str(stub_dir)},
            timeout_seconds=_BASH_RUN_TIMEOUT_SECONDS,
        )

    def test_a_destination_under_the_root_is_installed(self, tmp_path: Path) -> None:
        installed_file = tmp_path / "allowed" / "shfmt"

        result, _ = self._sudo_install(tmp_path, str(installed_file))

        assert result.returncode == 0, _output_of(result)
        assert installed_file.read_text() == "payload"

    @pytest.mark.parametrize(
        "destination_parts",
        [("outside", "shfmt"), ("allowed", "..", "outside", "shfmt")],
        ids=["outside-the-root", "dot-dot-out-of-the-root"],
    )
    def test_a_destination_outside_the_root_is_refused_and_nothing_is_written(
        self, tmp_path: Path, destination_parts: tuple[str, ...]
    ) -> None:
        result, call_log = self._sudo_install(tmp_path, str(tmp_path.joinpath(*destination_parts)))

        assert result.returncode == 2, _output_of(result)
        assert "refusing to install" in result.stderr, _output_of(result)
        assert not (tmp_path / "outside" / "shfmt").exists()
        assert len(pin_step_calls_to(call_log, "install")) == 1, call_log
