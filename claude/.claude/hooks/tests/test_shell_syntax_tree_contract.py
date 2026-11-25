"""Contract tests for shell-syntax-tree.py: its exit statuses, strict tree check, encoding, isolation and import pin.

The classes up to `TestKnownSetsAreConsistent` need no shfmt, so a run without shfmt still pins the
module's behavior on hand-built trees. Only one case there can skip: the locale case, which skips
when no installed locale gives the interpreter a non-UTF-8 stdio. The classes below that line run real shfmt,
with `_LIB_SHFMT_ARGV`: the conformance corpus that confirms every set in the module against
real output, the dialect-only samples, the dialect pin and the child-position matrix. Each skips
locally when shfmt is not installed and fails under GITHUB_ACTIONS.
"""
from __future__ import annotations

import ast
import io
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from helpers import production_shfmt_argv, write_stub_shfmt

from . import _shell_syntax_tree_runners as shell_syntax_tree_runners
from . import conftest as hooks_conftest
from ._shell_syntax_tree_runners import (
    CHILD_POSITION_MATRIX,
    COMMAND_HOLDING_TYPES,
    MODULE_PATH,
    SUBPROCESS_HANG_GUARD_SECONDS,
    iter_objects,
    project_words,
    real_shfmt_identity,
    run_module,
    run_shfmt,
    shell_syntax_tree,
    shfmt_exit_note,
    simple_commands,
)

TREE = shell_syntax_tree
PLACEHOLDER = TREE.EXPANSION_PLACEHOLDER


def position() -> dict:
    return {"Offset": 0, "Line": 1, "Col": 1}


def lit(value: str) -> dict:
    return {"Type": "Lit", "ValuePos": position(), "ValueEnd": position(), "Value": value}


def untyped_lit(value: str) -> dict:
    """A `Lit` held in a struct field of type `*Lit`, which shfmt writes without a `Type`."""
    return {key: field for key, field in lit(value).items() if key != "Type"}


def word(*parts: dict) -> dict:
    return {"Parts": list(parts)}


def call_expr(*words: str) -> dict:
    return {"Type": "CallExpr", "Args": [word(lit(value)) for value in words]}


def stmt(command: dict) -> dict:
    return {"Position": position(), "Cmd": command}


def file_tree(*stmts: dict) -> dict:
    return {"Type": "File", "Stmts": list(stmts)}


def tree_json(tree: dict) -> bytes:
    return json.dumps(tree).encode("utf-8")


def valid_tree() -> dict:
    return file_tree(stmt(call_expr("gh", "pr", "create", "--body-file", "/y")))


def binary_cmd(operator: str) -> dict:
    return {
        "Type": "BinaryCmd",
        "OpPos": position(),
        "Op": operator,
        "X": stmt(call_expr("a")),
        "Y": stmt(call_expr("b")),
    }


def extglob_in_a_command(pattern: str) -> dict:
    extglob = {"Type": "ExtGlob", "OpPos": position(), "Op": "@(", "Pattern": untyped_lit(pattern)}
    return file_tree(stmt({"Type": "CallExpr", "Args": [word(lit("echo")), word(extglob)]}))


def _patch_standard_streams(monkeypatch, *, stdin_bytes, stdout_buffer=None, stderr_buffer=None, encoding=None):
    """Replace sys.stdin/stdout/stderr with wrappers this test owns, in place of capsys.

    Patching sys.stdout alongside capsys makes monkeypatch's teardown restore capsys's
    already-closed stream, which fails pytest's own final flush under `-s`.
    `encoding` is the text encoding of the three wrappers, and None takes the locale's.
    """
    stdout_buffer = io.BytesIO() if stdout_buffer is None else stdout_buffer
    stderr_buffer = io.BytesIO() if stderr_buffer is None else stderr_buffer
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(stdin_bytes), encoding=encoding))
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(stdout_buffer, encoding=encoding))
    monkeypatch.setattr(sys, "stderr", io.TextIOWrapper(stderr_buffer, encoding=encoding, write_through=True))


class TestWordsOnHandBuiltTrees:
    def test_each_simple_command_projects_its_args_then_one_blank_line(self):
        tree = file_tree(stmt(call_expr("git", "commit", "-F", "/x")), stmt(call_expr("echo", "hi")))
        result = run_module(tree_json(tree))
        assert result.returncode == 0
        assert result.stdout == b"git\ncommit\n-F\n/x\n\necho\nhi\n\n"

    def test_a_command_with_assignments_only_adds_nothing(self):
        assignment_only = {"Type": "CallExpr", "Assigns": [{"Name": untyped_lit("x"), "Value": word(lit("1"))}]}
        result = run_module(tree_json(file_tree(stmt(assignment_only))))
        assert (result.returncode, result.stdout) == (0, b"")

    def test_empty_file_projects_nothing(self):
        result = run_module(tree_json({"Type": "File"}))
        assert (result.returncode, result.stdout) == (0, b"")

    def test_nested_command_words_follow_the_enclosing_command(self):
        inner_statement = stmt(call_expr("cat"))
        substitution = {"Type": "CmdSubst", "Left": position(), "Right": position(), "Stmts": [inner_statement]}
        outer = {"Type": "CallExpr", "Args": [word(lit("echo")), word(substitution)]}
        result = run_module(tree_json(file_tree(stmt(outer))))
        assert result.stdout == b"echo\n$(expansion)\n\ncat\n\n"

    def test_word_parts_flatten_by_kind(self):
        parts = [
            lit("a\\ b"),
            {"Type": "SglQuoted", "Left": position(), "Right": position(), "Value": "c\\d"},
            {"Type": "SglQuoted", "Left": position(), "Right": position(), "Dollar": True, "Value": "e"},
            {"Type": "DblQuoted", "Left": position(), "Right": position(), "Parts": [lit('f\\"g\\h'), lit("i\nj")]},
            {"Type": "DblQuoted", "Left": position(), "Right": position(), "Dollar": True, "Parts": [lit("k")]},
            {"Type": "ParamExp", "Dollar": position(), "Param": untyped_lit("X")},
        ]
        tree = file_tree(stmt({"Type": "CallExpr", "Args": [word(*parts)]}))
        result = run_module(tree_json(tree))
        assert result.stdout.decode("utf-8") == 'a bc\\d$(expansion)f"g\\hi j$(expansion)$(expansion)\n\n'

    def test_a_param_expansion_without_a_dollar_projects_to_the_placeholder(self):
        """shfmt writes a bare array subscript inside arithmetic as a `ParamExp` with no `Dollar`."""
        bare_subscript = {"Type": "ParamExp", "Short": True, "Param": untyped_lit("a")}
        tree = file_tree(stmt({"Type": "CallExpr", "Args": [word(lit("echo")), word(bare_subscript)]}))
        result = run_module(tree_json(tree))
        assert (result.returncode, result.stdout) == (0, b"echo\n$(expansion)\n\n")

    @pytest.mark.parametrize("ensure_ascii", [True, False], ids=["escaped-json", "raw-utf8-json"])
    def test_multibyte_words_are_utf8_whatever_encoding_the_text_streams_carry(self, monkeypatch, ensure_ascii):
        """In-process with latin-1 text wrappers, so a switch to text-mode stdio fails with no locale installed."""
        tree_text = json.dumps(file_tree(stmt(call_expr("echo", "é日本"))), ensure_ascii=ensure_ascii)
        stdout_buffer = io.BytesIO()
        _patch_standard_streams(
            monkeypatch, stdin_bytes=tree_text.encode("utf-8"), stdout_buffer=stdout_buffer, encoding="latin-1"
        )
        assert TREE.main(["shell-syntax-tree.py", "words"]) == 0
        assert stdout_buffer.getvalue() == "echo\né日本\n\n".encode()

    @pytest.mark.parametrize("ensure_ascii", [True, False], ids=["escaped-json", "raw-utf8-json"])
    def test_multibyte_words_are_utf8_under_a_locale_whose_stdio_is_not_utf8(self, ensure_ascii):
        """CPython coerces `LC_ALL=C` to UTF-8, so only a locale with another charset shows a text-mode stdio.

        Skips when `locale -a` lists no such locale. CI does not generate one today, so it skips there too.
        """
        locale_name = _installed_locale_with_non_utf8_stdio()
        tree_text = json.dumps(file_tree(stmt(call_expr("echo", "é日本"))), ensure_ascii=ensure_ascii)
        result = run_module(tree_text.encode("utf-8"), env={"LC_ALL": locale_name, "PATH": ""})
        assert (result.returncode, result.stdout) == (0, "echo\né日本\n\n".encode()), result.stderr

    def test_a_tree_nested_far_deeper_than_the_recursion_limit_projects(self):
        """The JSON text is built by hand because `json.dumps` recurses and would hit the limit first."""
        depth = 10_000
        position_text = json.dumps(position())
        statement_open = f'{{"Position":{position_text},"Cmd":'
        block_open = f'{{"Type":"Block","Lbrace":{position_text},"Rbrace":{position_text},"Stmts":[{statement_open}'
        block_close = "}]}"
        document = (
            '{"Type":"File","Stmts":['
            + statement_open
            + block_open * depth
            + json.dumps(call_expr("deep"))
            + block_close * (depth + 1)
        )
        result = run_module(document.encode("utf-8"))
        assert (result.returncode, result.stdout) == (0, b"deep\n\n")


def _installed_locale_with_non_utf8_stdio() -> str:
    """The first locale from `locale -a` under which the interpreter's stdio encoding is not UTF-8.

    `helpers.installed_locale_where` lists only UTF-8 locales, so it cannot find one.
    """
    try:
        listed = subprocess.run(
            ["locale", "-a"], capture_output=True, text=True, check=True, timeout=SUBPROCESS_HANG_GUARD_SECONDS
        ).stdout.split()
    except (FileNotFoundError, subprocess.CalledProcessError):
        pytest.skip("`locale -a` is unavailable, so no non-UTF-8 locale can be found")
    for name in listed:
        if "utf" in name.lower() or name in ("C", "POSIX"):
            continue
        probe = subprocess.run(
            [sys.executable, "-I", "-S", "-c", "import sys; print(sys.stdout.encoding)"],
            env={"LC_ALL": name, "PATH": ""},
            capture_output=True,
            check=False,
            timeout=SUBPROCESS_HANG_GUARD_SECONDS,
        )
        encoding = probe.stdout.decode().strip().lower().replace("-", "").replace("_", "")
        if probe.returncode == 0 and encoding and encoding != "utf8":
            return name
    pytest.skip("no installed locale gives the interpreter a non-UTF-8 stdio encoding")


UNRECOGNIZED_TREES = {
    "unknown-type": lambda: file_tree(stmt({"Type": "Mystery"})),
    "bash-rejected-type": lambda: file_tree(stmt({"Type": "TestDecl", "Position": position(), "Body": stmt(call_expr("a"))})),
    "unknown-operator": lambda: file_tree(stmt(binary_cmd("&"))),
    "operator-as-a-number": lambda: file_tree(stmt({**binary_cmd("&&"), "Op": 11})),
    "unknown-key": lambda: file_tree(stmt({**call_expr("a"), "Extra": "x"})),
    "missing-always-present-key": lambda: file_tree(
        stmt({"Type": "CallExpr", "Args": [word({"Type": "Lit", "ValuePos": position(), "ValueEnd": position()})]})
    ),
    "renamed-args": lambda: file_tree(stmt({"Type": "CallExpr", "Arguments": [word(lit("a"))]})),
    "renamed-background": lambda: file_tree({**stmt(call_expr("a")), "InBackground": True}),
    "renamed-dollar-on-sgl-quoted": lambda: file_tree(
        stmt(
            {
                "Type": "CallExpr",
                "Args": [word({"Type": "SglQuoted", "Left": position(), "Right": position(), "AnsiC": True, "Value": "x"})],
            }
        )
    ),
    "renamed-dollar-on-dbl-quoted": lambda: file_tree(
        stmt(
            {
                "Type": "CallExpr",
                "Args": [
                    word({"Type": "DblQuoted", "Left": position(), "Right": position(), "Locale": True, "Parts": [lit("x")]})
                ],
            }
        )
    ),
    "root-is-not-a-file": lambda: call_expr("a"),
    "root-is-not-an-object": lambda: ["File"],
    "type-on-an-untyped-object": lambda: file_tree({**stmt(call_expr("a")), "Type": "Stmt"}),
    "object-where-a-list-belongs": lambda: file_tree(stmt({"Type": "CallExpr", "Args": word(lit("a"))})),
    "list-where-a-scalar-belongs": lambda: file_tree(stmt({"Type": "CallExpr", "Args": [word({**lit("a"), "Value": ["a"]})]})),
    "position-without-line": lambda: file_tree({**stmt(call_expr("a")), "Position": {"Offset": 0, "Col": 1}}),
    "extglob-pattern-holding-a-substitution": lambda: extglob_in_a_command("$(x)|b"),
}


class TestUnrecognizedTreesExit5:
    @pytest.mark.parametrize("build_tree", UNRECOGNIZED_TREES.values(), ids=UNRECOGNIZED_TREES.keys())
    def test_exit_5_and_nothing_on_stdout(self, build_tree):
        result = run_module(tree_json(build_tree()))
        assert result.returncode == 5, result.stderr
        assert result.stdout == b""

    @pytest.mark.parametrize("operator", sorted(TREE.KNOWN_BINARY_OPERATORS))
    def test_every_known_binary_operator_is_recognized(self, operator):
        result = run_module(tree_json(file_tree(stmt(binary_cmd(operator)))))
        assert result.returncode == 0, result.stderr
        assert result.stdout == b"a\n\nb\n\n"

    def test_an_extglob_pattern_without_a_substitution_is_recognized(self):
        result = run_module(tree_json(extglob_in_a_command("a|b")))
        assert (result.returncode, result.stdout) == (0, b"echo\n$(expansion)\n\n")

    def test_conservation_mismatch_exits_5(self, monkeypatch):
        """The projection must visit as many CallExpr objects as the tree holds."""
        monkeypatch.setattr(TREE, "iter_call_exprs", lambda tree: iter(()))
        _patch_standard_streams(monkeypatch, stdin_bytes=tree_json(valid_tree()))
        assert TREE.main(["shell-syntax-tree.py", "words"]) == 5


def _lit_with(**changes) -> dict:
    return {**lit("x"), **changes}


def _tree_with_a_word_part(part: dict) -> dict:
    return file_tree(stmt({"Type": "CallExpr", "Args": [word(part)]}))


HAND_BUILT_REJECTIONS = {
    "null-where-a-scalar-belongs": (
        lambda: _tree_with_a_word_part(_lit_with(Value=None)),
        "field Value holds a value that is not a scalar",
    ),
    "type-that-is-not-a-string": (
        lambda: _tree_with_a_word_part(_lit_with(Type=["Lit"])),
        "an object carries a Type that is not a known node type",
    ),
    "position-with-an-extra-key": (
        lambda: _tree_with_a_word_part(_lit_with(ValuePos={**position(), "Extra": 1})),
        "a position object does not have the keys Offset, Line and Col",
    ),
    "pos-that-is-not-a-position": (
        lambda: _tree_with_a_word_part(_lit_with(Pos="x")),
        "a position object does not have the keys Offset, Line and Col",
    ),
}


class TestHandBuiltRejectionsNameTheirCondition:
    @pytest.mark.parametrize(
        ("build_tree", "diagnostic"), HAND_BUILT_REJECTIONS.values(), ids=HAND_BUILT_REJECTIONS.keys()
    )
    def test_exit_5_naming_the_condition(self, build_tree, diagnostic):
        result = run_module(tree_json(build_tree()))
        assert result.returncode == 5, result.stderr
        assert result.stdout == b""
        assert diagnostic in result.stderr.decode()


class TestDroppedKeyLimit:
    """Pins the dropped-key limit stated at ALWAYS_PRESENT_KEYS in shell-syntax-tree.py.

    Each case drops such a key from a statement holding a git write, and the module exits 0 with no words.
    A case flips when the check starts detecting the drop.
    """

    @pytest.mark.parametrize(
        "drop_the_key",
        [
            lambda statement: statement.pop("Cmd"),
            lambda statement: statement["Cmd"].pop("Args"),
        ],
        ids=["Stmt.Cmd", "CallExpr.Args"],
    )
    def test_the_statement_projects_no_words_and_the_tree_is_recognized(self, drop_the_key):
        tree = file_tree(stmt(call_expr("git", "push", "origin", "HEAD")))
        drop_the_key(tree["Stmts"][0])
        result = run_module(tree_json(tree))
        assert (result.returncode, result.stdout) == (0, b"")


class TestInternalFaultsExit2:
    @pytest.mark.parametrize(
        "stdin_bytes",
        [
            b"not json",
            b"",
            b'{"Type": "File"',
            b'{"Type":"File","Name":"\xff"}',
            b"[" * 1_000_000,
            b'{"Type":"File","Stmts":[{"Position":{"Offset":0,"Line":1,"Col":1},"Cmd":{"Type":"CallExpr","Args":[{"Parts":[{"Type":"Lit","ValuePos":{"Offset":0,"Line":1,"Col":1},"ValueEnd":{"Offset":0,"Line":1,"Col":1},"Value":"\\ud800"}]}]}}]}',
        ],
        ids=["garbage", "empty", "truncated", "invalid-utf8", "nested-past-the-json-reader", "lone-surrogate-word"],
    )
    def test_exit_2_never_1_and_nothing_on_stdout(self, stdin_bytes):
        result = run_module(stdin_bytes)
        assert result.returncode == 2, result.stderr
        assert result.stdout == b""

    @pytest.mark.parametrize(
        "arguments",
        [[], ["words", "extra"], ["bogus"]],
        ids=["none", "extra", "bogus"],
    )
    def test_bad_usage_exits_2(self, arguments):
        result = subprocess.run(
            [sys.executable, "-I", "-S", str(MODULE_PATH), *arguments],
            input=tree_json(valid_tree()),
            capture_output=True,
            check=False,
            timeout=SUBPROCESS_HANG_GUARD_SECONDS,
        )
        assert result.returncode == 2
        assert result.stdout == b""

    def test_internal_exception_exits_2_never_1(self, monkeypatch):
        def raise_runtime_error(_tree):
            raise RuntimeError("forced")

        monkeypatch.setitem(TREE.PROJECTIONS, "words", raise_runtime_error)
        stderr_buffer = io.BytesIO()
        _patch_standard_streams(monkeypatch, stdin_bytes=tree_json(valid_tree()), stderr_buffer=stderr_buffer)
        assert TREE.main(["shell-syntax-tree.py", "words"]) == 2
        assert "RuntimeError" in stderr_buffer.getvalue().decode()

    def test_value_error_from_the_stdout_write_exits_2(self, monkeypatch):
        stdout_buffer = io.BytesIO()
        stderr_buffer = io.BytesIO()
        _patch_standard_streams(
            monkeypatch, stdin_bytes=tree_json(valid_tree()), stdout_buffer=stdout_buffer, stderr_buffer=stderr_buffer
        )
        stdout_buffer.close()
        assert TREE.main(["shell-syntax-tree.py", "words"]) == 2
        assert "ValueError" in stderr_buffer.getvalue().decode()


CANARY = "CANARY-7f3a91"

# Each input holds the canary in a key or in a `Lit.Value`, and fails with the status beside it.
# A truncated document fails in the JSON reader, and a lone surrogate fails in the encoder.
STDERR_CANARY_INPUTS = {
    "key-in-a-tree-with-an-unknown-key": (tree_json(file_tree(stmt({**call_expr("a"), CANARY: "x"}))), 5),
    "literal-value-beside-an-unknown-key": (tree_json(file_tree(stmt({**call_expr(CANARY), "Extra": "x"}))), 5),
    "extglob-pattern-holding-a-substitution": (tree_json(extglob_in_a_command(f"$({CANARY})|b")), 5),
    "key-in-truncated-json": (f'{{"Type":"File","{CANARY}":'.encode(), 2),
    "literal-value-with-a-lone-surrogate": (tree_json(file_tree(stmt(call_expr("echo", CANARY + "\ud800")))), 2),
}


class TestStderrNeverEchoesTreeText:
    @pytest.mark.parametrize(
        ("stdin_bytes", "expected_status"), STDERR_CANARY_INPUTS.values(), ids=STDERR_CANARY_INPUTS.keys()
    )
    def test_the_diagnostic_names_the_failure_and_not_the_tree_text(self, stdin_bytes, expected_status):
        result = run_module(stdin_bytes)
        assert result.returncode == expected_status
        assert result.stderr != b"", "a vacuous check: the module wrote no diagnostic"
        assert CANARY.encode() not in result.stderr


class TestInterpreterIsolation:
    def test_planted_stdlib_module_beside_the_script_is_not_imported(self, tmp_path):
        script_copy = tmp_path / "shell-syntax-tree.py"
        shutil.copy(MODULE_PATH, script_copy)
        (tmp_path / "json.py").write_text('raise RuntimeError("planted json.py imported")\n')
        without_isolation = subprocess.run(
            [sys.executable, "-S", str(script_copy), "words"],
            input=tree_json(valid_tree()),
            capture_output=True,
            check=False,
            timeout=SUBPROCESS_HANG_GUARD_SECONDS,
        )
        assert without_isolation.returncode != 0, "precondition: without -I the planted json.py is on sys.path"

        result = run_module(tree_json(valid_tree()), script_path=script_copy)

        assert result.returncode == 0, result.stderr
        assert result.stdout == b"gh\npr\ncreate\n--body-file\n/y\n\n"


# The modules the script may import. Each gives it no process, network, filesystem or dynamic-code capability.
ALLOWED_MODULE_IMPORTS = frozenset({"json", "sys"})


def _top_level_imports(script_path) -> set[str]:
    tree = ast.parse(script_path.read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "relative imports cannot resolve for a standalone script"
            imported.add(node.module.split(".")[0])
    return imported


def test_script_imports_only_the_allowlisted_modules():
    """The interpreter flags `-I -S` keep a sibling or site module from loading, and this pin covers the script's own imports.

    An allowlist rejects any new import for review, where a denylist would pass a capability it did not name.
    """
    imported = _top_level_imports(MODULE_PATH)
    assert imported, "vacuous pin: the script's imports were not found"
    assert imported <= ALLOWED_MODULE_IMPORTS


def test_the_import_pin_detects_an_import_outside_the_allowlist(tmp_path):
    """Guards the pin above against going vacuous: an import outside the allowlist must be seen as one."""
    script_with_extra_imports = tmp_path / "with_extra_imports.py"
    script_with_extra_imports.write_text("import json\nimport re\nfrom subprocess import run\n")
    assert _top_level_imports(script_with_extra_imports) - ALLOWED_MODULE_IMPORTS == {"re", "subprocess"}


class TestReportHeaderNamesAMissingShfmt:
    """The hooks conftest's header line, called with `shutil.which` patched to each outcome."""

    def test_the_line_names_shfmt_when_it_is_not_on_path(self, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda command: None)
        header = hooks_conftest.pytest_report_header(config=None)
        assert header is not None
        assert "shfmt" in header

    def test_there_is_no_line_when_shfmt_is_found(self, monkeypatch):
        monkeypatch.setattr(shutil, "which", lambda command: f"/usr/bin/{command}")
        assert hooks_conftest.pytest_report_header(config=None) is None


class TestRealShfmtIdentity:
    """The failure-message helper, run against stub shfmt files first on a PATH that holds nothing else."""

    @pytest.fixture(autouse=True)
    def _fresh_identity_cache(self):
        real_shfmt_identity.cache_clear()
        yield
        real_shfmt_identity.cache_clear()

    @staticmethod
    def _stub_dir_on_path(monkeypatch, tmp_path) -> Path:
        stub_dir = tmp_path / "stubs"
        stub_dir.mkdir()
        monkeypatch.setenv("PATH", str(stub_dir))
        return stub_dir

    def test_it_says_so_when_no_shfmt_is_on_path(self, monkeypatch, tmp_path):
        self._stub_dir_on_path(monkeypatch, tmp_path)

        assert real_shfmt_identity() == "no shfmt on PATH"

    def test_it_names_the_file_and_the_version_line_and_not_the_directory(self, monkeypatch, tmp_path):
        stub_dir = self._stub_dir_on_path(monkeypatch, tmp_path)
        write_stub_shfmt(stub_dir / "shfmt", version_line="v9.99.0")

        identity = real_shfmt_identity()

        assert identity == "shfmt: v9.99.0"
        assert str(tmp_path) not in identity

    def test_it_says_the_build_prints_no_version_when_the_version_line_is_empty(self, monkeypatch, tmp_path):
        stub_dir = self._stub_dir_on_path(monkeypatch, tmp_path)
        write_stub_shfmt(stub_dir / "shfmt", version_line="")

        assert real_shfmt_identity() == "shfmt: prints no version"

    def test_it_names_a_probe_that_cannot_launch_and_does_not_raise(self, monkeypatch, tmp_path):
        stub_dir = self._stub_dir_on_path(monkeypatch, tmp_path)
        unlaunchable_shfmt = stub_dir / "shfmt"
        unlaunchable_shfmt.write_text("#!/nonexistent/interpreter\n")
        unlaunchable_shfmt.chmod(0o755)

        assert real_shfmt_identity() == "shfmt: its --version probe failed with FileNotFoundError"

    def test_it_names_a_probe_that_outlasts_the_hang_guard_and_does_not_raise(self, monkeypatch, tmp_path):
        stub_dir = self._stub_dir_on_path(monkeypatch, tmp_path)
        write_stub_shfmt(stub_dir / "shfmt", version_line="v9.99.0", hang_version_seconds=30)
        monkeypatch.setenv("PATH", os.pathsep.join([str(stub_dir), os.defpath]))
        # Shortens the guard so the hung probe ends in a second.
        monkeypatch.setattr(shell_syntax_tree_runners, "SUBPROCESS_HANG_GUARD_SECONDS", 1)

        assert real_shfmt_identity() == "shfmt: its --version probe failed with TimeoutExpired"


def test_production_shfmt_argv_selects_the_bash_dialect():
    """Needs only bash, which reads the argv from `_lib.sh`."""
    assert production_shfmt_argv() == ["shfmt", "-ln", "bash", "--to-json"]


class TestKnownSetsAreConsistent:
    def test_placeholder_begins_with_a_dollar_so_callers_read_it_as_an_expansion(self):
        assert PLACEHOLDER.startswith("$")

    def test_every_known_node_type_has_a_field_table(self):
        assert set(TREE.NODE_FIELDS) >= TREE.KNOWN_NODE_TYPES

    def test_bash_rejected_types_are_not_known(self):
        assert not TREE.KNOWN_NODE_TYPES & TREE.BASH_REJECTED_NODE_TYPES

    @pytest.mark.parametrize("struct_name", sorted(TREE.ALWAYS_PRESENT_KEYS))
    def test_every_always_present_key_is_a_field_of_its_struct(self, struct_name):
        assert set(TREE.ALWAYS_PRESENT_KEYS[struct_name]) <= set(TREE.NODE_FIELDS[struct_name])

    @pytest.mark.parametrize("struct_name", sorted(TREE.NODE_FIELDS))
    def test_every_field_kind_names_a_struct_with_a_field_table(self, struct_name):
        plain_kinds = {"pos", "scalar", "typed", "typed[]"}
        for field_name, kind in TREE.NODE_FIELDS[struct_name].items():
            if kind not in plain_kinds:
                assert kind.removesuffix("[]") in TREE.NODE_FIELDS, (struct_name, field_name)


# ---- Real shfmt from here down. ----

# Every construct the module's sets and projections must handle, one command each. The corpus holds
# only valid bash: the test asserts shfmt accepts each.
CONFORMANCE_CORPUS = [
    "", "# only a comment\n", "a", "a b c", "a && b", "a || b", "a | b", "a |& b", "a; b", "a &", "a\nb",
    "! a", "time", "time a", "time -p a", "{ a; }", "(a)", "a && b || c | d &",
    "if a; then b; elif c; then d; else e; fi", "while a; do b; done", "until a; do b; done",
    "for i in 1 2; do a; done", "for i; do a; done", "for ((i=0;i<3;i++)); do a; done",
    "select x in a b; do c; done", "case $x in a) b;; c|d) e;& f) g;;& *) h;; esac", "case x in a) b ;; esac # trailing",
    "case x in\na) b\nesac", "f() { a; }", "function f { a; }", "function f() { a; }", "coproc a", "coproc N { a; }",
    "[[ -f x && ! -d y || x == y* ]]", "[[ ( -z a ) ]]", "[[ a =~ ^b ]]", "(( 1 + 2 * 3 ))", "(( x++ ))", "(( (1+2) ))",
    "let x=1+2 y=3", "declare -a x=(1 2 3)", "local x=1 y", "export A=1", "readonly -p", "declare -A m=([k]=v [j]=w)",
    "x=1 y=2 a", "x=1", "x+=1", "arr=(a b c)", "arr+=(d)", "arr[1]=x", "arr=(\n a # c\n b\n)", "x=()", "x=",
    "a > f", "a >> f", "a < f", "a 2>&1", "a &> f", "a >| f", "a <> f", "a <<< w", "a {fd}> f", "a 3< f", "> f",
    "cat <<EOF\nbody $x `c`\nEOF\n", "cat <<'EOF'\nbody `c`\nEOF\n", "cat <<-EOF\n\tbody\n\tEOF\n",
    "cat <<EOF\nEOF\n", "cat <<A <<B\n1\nA\n2\nB\n",
    "a $(b)", "a `b`", 'a "$(b)"', "a $((1+2))", "a $[1+2]", "a <(b)", "a >(b)",
    "a ${x}", "a $x", "a ${x:-d}", "a ${x:=d}", "a ${x:+d}", "a ${x:?d}", "a ${#x}", "a ${!x}", "a ${x%p}", "a ${x%%p}",
    "a ${x#p}", "a ${x##p}", "a ${x/p/r}", "a ${x//p/r}", "a ${x:1:2}", "a ${x[1]}", "a ${x[@]}", "a ${!p*}", "a ${!p@}",
    "a ${x^^}", "a ${x@Q}", "a ${x:-$(b)}", "a ${x:-}", "a ${x/}",
    "a 'sq'", 'a "dq"', "a $'ansi\\n'", 'a $"loc"', "a ''", 'a ""', "a x'y'z", 'a x"$y"z',
    "a {1,2}", "a ?(x) *(y) +(z) @(w) !(v)", "a x@(b|c)y", "a *.txt [ab]? ~ ~/x",
    "a # comment", "a\\\nb", 'a "b\\"c"', "a \\a",
    "echo $(( x ? 1 : 2 ))", "echo $(( -x + +y * !z ))", "echo $(( x = y += 1 ))", "echo $(( (1) ))", "echo $((x++ + ++y))",
    "echo $((1<<3))", "echo ${x:$(b):2}", "a=$(b) c", "a=<(b)", "x[$(a)]=1",
    # A bare array subscript inside arithmetic or an index is a `ParamExp` with no `Dollar`.
    "echo $((a[0]))", "echo $(( a[1] ))", "a=$(( b[1] ))", "(( a[i]++ ))", "(( a[0] ))", "if ((a[i])); then a; fi",
    "let a[0]=1", "echo ${a[b[0]]}", "echo ${x:a[0]:b[1]}", "for ((i=0;i<n[0];i++)); do a; done", "a[b[0]]=1",
    'git commit -m "$((a[0]))"', "((count[$k]++)); gh pr create --body-file f",
    "for i in $(a) \"$b\"; do c; done", "case $(a) in $(b)) c;; esac", "[[ $(a) == $(b) ]]", "(( $(a) ))",
    "arr=($(a) $(b))", "declare x=$(a)", "a > $(b)", "a 2> >(b)", "a <<< $(b)",
    "{ a; b; } & c", "( a ) | b", "a |\n b", "a &&\n b",
    "a=1 b+=2 e", "declare -n r=x", 'a "$@" "$*" $# $? $$ $! $0 $1 ${10}',
    "[ -d x ] && cd x; git push", "cd /a && git -C /b status; (cd /c; git push) | cat",
    "echo a; echo b", "a;b;c", "a\n# c1\n# c2\nb", "case x in\n# c\na) b ;;\n# d\nesac", "{ a\n# last\n}",
    "echo é 日本語",
    # Each of these writes a field that no earlier entry does: a comment before a closer (the `Last` fields), a funsub's
    # `TempFile` and `ReplyVar`, and the brace form of `for`.
    "x=(\n a\n# last\n)", "case x in\na) b\n# c\n;;\nesac", "echo $(a\n# c\n)", "echo ${ a; }", "echo ${| a; }",
    "for i in 1 2; { a; }", "for i in 1; do a\n# c\ndone", "if a\n# c\nthen b; fi", "if a; then b\n# c\nfi",
    "cat <(a\n# c\n)", "(a\n# c\n)", "while a\n# c\ndo b; done", "while a; do b\n# c\ndone",
]  # fmt: skip

# Node types whose fields hold no list of statements, word or other node that could hold a command.
NODE_TYPES_HOLDING_NO_COMMAND = frozenset({"Lit", "SglQuoted"})

# Node types whose raw text can hold a substitution the walker cannot reach, so the module denies the text instead.
NODE_TYPES_DENIED_WHEN_THEIR_TEXT_HOLDS_A_SUBSTITUTION = frozenset({"ExtGlob"})

# Dialect-only samples that `-ln bash` rejects, and the dialect that parses each into its node type.
BASH_REJECTED_SAMPLES = {
    "TestDecl": ('@test "x" { echo hi; }\n', "bats"),
    "FlagsArithm": ("echo ${a[(r)x]}", "zsh"),
}

# Fields that no bash command tried makes shfmt write. Each maps to the shfmt arguments and sample whose tree writes it:
# another dialect, or a file name given to shfmt. A test parses each sample and checks the tree holds the field.
# `IfClause.ThenLast` maps to None: none of bash, posix, mksh and zsh wrote it for any `if` shape with comments tried,
# though the Go struct holds the field, so no writer was found.
# A corpus tree that gains a field flips the field-coverage test, which then moves it out of this mapping.
DIALECT_ONLY_FIELD_WRITERS = {
    ("ArithmCmd", "Unsigned"): (["-ln", "mksh"], "((# 1 + 2))"),
    ("ArithmExp", "Unsigned"): (["-ln", "mksh"], "echo $((# 1 + 2))"),
    ("CaseClause", "Braces"): (["-ln", "mksh"], "case x { a) b;; }"),
    ("File", "Name"): (["-ln", "bash", "--filename", "x.sh"], "a"),
    ("FuncDecl", "Names"): (["-ln", "zsh"], "function a b { :; }"),
    ("IfClause", "ThenLast"): None,
    ("ParamExp", "Flags"): (["-ln", "zsh"], "echo ${(f)x}"),
    ("ParamExp", "GlobSubst"): (["-ln", "zsh"], "echo ${~x}"),
    ("ParamExp", "IsSet"): (["-ln", "zsh"], "echo ${+x}"),
    ("ParamExp", "Modifiers"): (["-ln", "zsh"], "echo ${x:h}"),
    ("ParamExp", "NestedParam"): (["-ln", "zsh"], "echo ${${x}}"),
    ("ParamExp", "RcExpand"): (["-ln", "zsh"], "echo ${^x}"),
    ("ParamExp", "Split"): (["-ln", "zsh"], "echo ${=x}"),
    ("ParamExp", "Width"): (["-ln", "mksh"], "echo ${%x}"),
    ("Stmt", "Coprocess"): (["-ln", "mksh"], "a |&"),
    ("Stmt", "Disown"): (["-ln", "zsh"], "a &|"),
}
DIALECT_ONLY_FIELDS = frozenset(DIALECT_ONLY_FIELD_WRITERS)

COMMAND_UNDER_TEST = "gh pr create --body-file /y"
COMMAND_WORDS_UNDER_TEST = ["gh", "pr", "create", "--body-file", "/y"]


def _iter_structs(tree) -> Iterator[tuple[str, dict]]:
    """Every Go struct the tree encodes, as its name and object, from `Type` keys and the field table."""
    stack = [(tree, "typed")]
    while stack:
        node, kind = stack.pop()
        struct_name = node["Type"] if kind == "typed" else kind
        yield struct_name, node
        for key, value in node.items():
            field_kind = TREE.NODE_FIELDS[struct_name].get(key)
            if field_kind in (None, "pos", "scalar"):
                continue
            children = value if field_kind.endswith("[]") else [value]
            element_kind = "typed" if field_kind.startswith("typed") else field_kind.removesuffix("[]")
            stack.extend((child, element_kind) for child in children)


def _structs_in(tree) -> set[str]:
    return {struct_name for struct_name, _ in _iter_structs(tree)}


def _types_in(tree) -> set[str]:
    return {node["Type"] for node in iter_objects(tree) if "Type" in node}


def _shfmt_tree(command: str) -> dict:
    parsed = run_shfmt(command)
    assert parsed.returncode == 0, f"{shfmt_exit_note(parsed)} on {command!r}"
    return json.loads(parsed.stdout)


def _tables_follow_the_pin() -> str:
    """Names the shfmt that ran and says which build the module's tables follow, for a table-versus-corpus failure."""
    return (
        f"{real_shfmt_identity()}; the module's tables follow the build .github/workflows/tests.yml pins,"
        " so edit them only against that build"
    )


def _tree_without_key(corpus_trees: dict, struct_name: str, key: str) -> dict:
    """A copy of the first corpus tree that holds `struct_name`, with `key` deleted from its first such object."""
    for tree in corpus_trees.values():
        tree_copy = json.loads(json.dumps(tree))
        for found_struct, node in _iter_structs(tree_copy):
            if found_struct == struct_name:
                del node[key]
                return tree_copy
    raise AssertionError(f"no corpus tree holds a {struct_name}")


def _tree_with_unknown_key(corpus_trees: dict, struct_name: str) -> dict:
    """A copy of the first corpus tree that holds `struct_name`, with the CANARY key added to its first such object."""
    for tree in corpus_trees.values():
        tree_copy = json.loads(json.dumps(tree))
        for found_struct, node in _iter_structs(tree_copy):
            if found_struct == struct_name:
                node[CANARY] = "x"
                return tree_copy
    raise AssertionError(f"no corpus tree holds a {struct_name}")


@pytest.fixture(scope="module")
def corpus_trees():
    return {command: _shfmt_tree(command) for command in CONFORMANCE_CORPUS}


ALWAYS_PRESENT_KEY_CASES = [(struct_name, key) for struct_name, keys in sorted(TREE.ALWAYS_PRESENT_KEYS.items()) for key in keys]


class TestConformanceCorpus:
    @pytest.mark.parametrize("command", CONFORMANCE_CORPUS, ids=[repr(command) for command in CONFORMANCE_CORPUS])
    def test_every_tree_passes_the_strict_check_and_projects(self, corpus_trees, command):
        tree = corpus_trees[command]
        raw_count = TREE.check_tree(tree)
        _, visited = TREE.project_words(tree)
        assert visited == raw_count

    def test_known_node_types_equal_the_types_the_corpus_produces(self, corpus_trees):
        observed_types = set().union(*(_types_in(tree) for tree in corpus_trees.values()))
        assert observed_types - TREE.KNOWN_NODE_TYPES == set(), (
            f"a corpus Type is missing from KNOWN_NODE_TYPES: {_tables_follow_the_pin()}"
        )
        assert TREE.KNOWN_NODE_TYPES - observed_types == set(), (
            f"a KNOWN_NODE_TYPES entry has no conformance case: {_tables_follow_the_pin()}"
        )

    def test_known_binary_operators_equal_the_operators_the_corpus_produces(self, corpus_trees):
        operators = {
            node["Op"]
            for tree in corpus_trees.values()
            for node in iter_objects(tree)
            if node.get("Type") == "BinaryCmd"
        }
        assert operators == TREE.KNOWN_BINARY_OPERATORS, _tables_follow_the_pin()

    def test_the_field_table_covers_exactly_the_structs_shfmt_encodes_for_bash(self, corpus_trees):
        observed_structs = set().union(*(_structs_in(tree) for tree in corpus_trees.values()))
        never_encoded_for_bash = TREE.BASH_REJECTED_NODE_TYPES | {"BraceExp"}
        assert observed_structs <= set(TREE.NODE_FIELDS), _tables_follow_the_pin()
        assert set(TREE.NODE_FIELDS) - observed_structs == never_encoded_for_bash, _tables_follow_the_pin()

    def test_every_field_of_an_encoded_struct_is_in_a_corpus_tree_or_the_named_dialect_only_fields(self, corpus_trees):
        """A field name no tree confirms could be misspelled, and the module would then deny valid commands carrying it."""
        corpus_fields = {
            (struct_name, key)
            for tree in corpus_trees.values()
            for struct_name, node in _iter_structs(tree)
            for key in node
        }
        never_encoded_for_bash = TREE.BASH_REJECTED_NODE_TYPES | {"BraceExp"}
        table_fields = {
            (struct_name, key)
            for struct_name, fields in TREE.NODE_FIELDS.items()
            if struct_name not in never_encoded_for_bash
            for key in fields
        }
        assert table_fields - corpus_fields == DIALECT_ONLY_FIELDS, (
            f"a field has no corpus tree, or a listed one now has: {_tables_follow_the_pin()}"
        )

    def test_only_if_clause_then_last_has_no_writer(self):
        """A field mapped to None drops out of the writer test below, so a second one must be a deliberate edit."""
        fields_without_a_writer = {field for field, writer in DIALECT_ONLY_FIELD_WRITERS.items() if writer is None}
        assert fields_without_a_writer == {("IfClause", "ThenLast")}

    @pytest.mark.parametrize(
        ("struct_name", "key"),
        sorted(field for field, writer in DIALECT_ONLY_FIELD_WRITERS.items() if writer is not None),
        ids=[f"{s}.{k}" for s, k in sorted(f for f, w in DIALECT_ONLY_FIELD_WRITERS.items() if w is not None)],
    )
    def test_each_dialect_only_field_is_written_by_the_dialect_or_file_name_it_names(self, struct_name, key):
        shfmt_arguments, sample = DIALECT_ONLY_FIELD_WRITERS[(struct_name, key)]
        parsed = run_shfmt(sample, argv=["shfmt", *shfmt_arguments, "--to-json"])
        assert parsed.returncode == 0, shfmt_exit_note(parsed)
        tree = json.loads(parsed.stdout)
        assert any(found == struct_name and key in node for found, node in _iter_structs(tree))

    def test_every_struct_with_an_always_present_key_set_appears_in_the_corpus(self, corpus_trees):
        observed_structs = set().union(*(_structs_in(tree) for tree in corpus_trees.values()))
        assert set(TREE.ALWAYS_PRESENT_KEYS) <= observed_structs, _tables_follow_the_pin()

    @pytest.mark.parametrize(
        ("struct_name", "key"),
        ALWAYS_PRESENT_KEY_CASES,
        ids=[f"{struct_name}.{key}" for struct_name, key in ALWAYS_PRESENT_KEY_CASES],
    )
    def test_a_real_tree_without_an_always_present_key_exits_5(self, corpus_trees, struct_name, key):
        """A listed key that shfmt stopped writing, or one nobody lists, must not pass the strict check."""
        tree = _tree_without_key(corpus_trees, struct_name, key)
        result = run_module(json.dumps(tree).encode("utf-8"))
        assert result.returncode == 5, result.stderr
        assert result.stdout == b""
        assert f"a {struct_name} object lacks the key {key}" in result.stderr.decode()

    def test_stmt_background_negated_and_dollar_flags_use_the_names_the_module_reads(self):
        statement = _shfmt_tree("a &")["Stmts"][0]
        assert statement["Background"] is True
        assert _shfmt_tree("! a")["Stmts"][0]["Negated"] is True
        ansi_c_part = _shfmt_tree("echo $'x'")["Stmts"][0]["Cmd"]["Args"][1]["Parts"][0]
        locale_part = _shfmt_tree('echo $"x"')["Stmts"][0]["Cmd"]["Args"][1]["Parts"][0]
        assert (ansi_c_part["Type"], ansi_c_part["Dollar"]) == ("SglQuoted", True)
        assert (locale_part["Type"], locale_part["Dollar"]) == ("DblQuoted", True)

    def test_binary_operator_is_a_string(self):
        assert _shfmt_tree("a |& b")["Stmts"][0]["Cmd"]["Op"] == "|&"

    def test_an_empty_command_is_a_file_with_only_a_type_and_a_comment_only_command_has_no_stmts(self):
        assert _shfmt_tree("") == {"Type": "File"}
        comment_only = _shfmt_tree("# git commit -F x\n")
        assert "Stmts" not in comment_only
        assert comment_only["Last"][0]["Text"] == " git commit -F x"


# Keys the encoder writes on every node it can: the type tag and the offsets of the node's span.
# The module checks the type and the offsets apart from ALWAYS_PRESENT_KEYS.
KEYS_ON_EVERY_ENCODED_NODE = frozenset({"Type", "Pos", "End"})

# Keys that every corpus instance of a struct holds but a valid command can omit, each with a command that omits it.
# ALWAYS_PRESENT_KEYS leaves them out.
KEYS_A_VALID_COMMAND_CAN_OMIT = {
    ("ArrayElem", "Value"): "x=([1]=)",
    ("CStyleLoop", "Init"): "for ((;;)); do a; done",
    ("CStyleLoop", "Cond"): "for ((;;)); do a; done",
    ("CStyleLoop", "Post"): "for ((;;)); do a; done",
    ("CaseClause", "Items"): "case x in esac",
    ("CaseItem", "Stmts"): "case x in a) ;; esac",
    ("CmdSubst", "Stmts"): "echo $()",
    ("Comment", "Text"): "#\n",
    ("DeclClause", "Args"): "declare",
    ("ProcSubst", "Stmts"): "cat <()",
    ("Slice", "Length"): "a ${x:1}",
    ("Slice", "Offset"): "a ${x::1}",
}

# The unlisted exceptions that ALWAYS_PRESENT_KEYS names in shell-syntax-tree.py, which every corpus instance of a struct holds.
# Adding one to the table moves it out of this set.
KEYS_PRESENT_ON_EVERY_VALID_INSTANCE_BUT_NOT_LISTED = frozenset({
    ("CaseItem", "Op"), ("ForClause", "DoPos"), ("ForClause", "DonePos"), ("IfClause", "FiPos"),
})  # fmt: skip

# The seven keys the table lists because no valid command omits them, each with the empty forms real shfmt rejects.
# Each form makes shfmt exit 1, so a shfmt that accepted one would make its key omittable.
# The extglob form is `echo @()`: the bare `@()` fails as a function declaration, which says nothing about the pattern.
EMPTY_FORMS_BY_LISTED_KEY = {
    ("Block", "Stmts"): ["{ }", "{ # c\n}"],
    ("Subshell", "Stmts"): ["( )", "( # c\n)"],
    ("IfClause", "Then"): [
        "if a; then ; fi", "if a; then b; else ; fi", "if a; then b; elif c; then ; fi", "if a; then # c\nfi",
    ],
    ("WhileClause", "Cond"): ["while ; do a; done", "until ; do a; done"],
    ("WhileClause", "Do"): ["while a; do ; done", "until a; do ; done", "while a; do # c\ndone"],
    ("ForClause", "Do"): ["for i; do done", "select x in a; do done", "for ((;;)); do done"],
    ("ExtGlob", "Pattern"): ["echo @()"],
}  # fmt: skip


def _keys_on_every_instance_of_each_struct(trees) -> dict[str, set[str]]:
    common: dict[str, set[str]] = {}
    for tree in trees:
        for struct_name, node in _iter_structs(tree):
            common[struct_name] = set(node) if struct_name not in common else common[struct_name] & set(node)
    return common


class TestAlwaysPresentKeysFollowTheCorpus:
    """The table's definition is the keys real shfmt writes on every instance, so it is checked against real instances."""

    def test_the_table_equals_the_keys_on_every_corpus_instance_less_the_named_exceptions(self, corpus_trees):
        named_exceptions = set(KEYS_A_VALID_COMMAND_CAN_OMIT) | KEYS_PRESENT_ON_EVERY_VALID_INSTANCE_BUT_NOT_LISTED
        expected = {}
        for struct_name, keys in _keys_on_every_instance_of_each_struct(corpus_trees.values()).items():
            listed = {
                key for key in keys - KEYS_ON_EVERY_ENCODED_NODE if (struct_name, key) not in named_exceptions
            }
            if listed:
                expected[struct_name] = listed
        assert expected == {struct_name: set(keys) for struct_name, keys in TREE.ALWAYS_PRESENT_KEYS.items()}, (
            _tables_follow_the_pin()
        )

    @pytest.mark.parametrize(
        ("struct_name", "key"),
        sorted(KEYS_A_VALID_COMMAND_CAN_OMIT),
        ids=[f"{struct_name}.{key}" for struct_name, key in sorted(KEYS_A_VALID_COMMAND_CAN_OMIT)],
    )
    def test_each_omittable_key_is_omitted_by_its_command(self, struct_name, key):
        tree = _shfmt_tree(KEYS_A_VALID_COMMAND_CAN_OMIT[(struct_name, key)])
        assert any(found == struct_name and key not in node for found, node in _iter_structs(tree))

    @pytest.mark.parametrize(
        ("struct_name", "key"),
        sorted(KEYS_PRESENT_ON_EVERY_VALID_INSTANCE_BUT_NOT_LISTED),
        ids=[f"{struct_name}.{key}" for struct_name, key in sorted(KEYS_PRESENT_ON_EVERY_VALID_INSTANCE_BUT_NOT_LISTED)],
    )
    def test_each_unlisted_key_is_on_every_corpus_instance(self, corpus_trees, struct_name, key):
        keys_on_every_instance = _keys_on_every_instance_of_each_struct(corpus_trees.values())
        assert key in keys_on_every_instance[struct_name]

    @pytest.mark.parametrize(
        ("struct_name", "key", "empty_form"),
        [(struct_name, key, form) for (struct_name, key), forms in EMPTY_FORMS_BY_LISTED_KEY.items() for form in forms],
        ids=[
            f"{struct_name}.{key}-{form!r}"
            for (struct_name, key), forms in EMPTY_FORMS_BY_LISTED_KEY.items()
            for form in forms
        ],
    )
    def test_real_shfmt_rejects_the_empty_form_that_would_make_a_listed_key_omittable(self, struct_name, key, empty_form):
        """Pins each form's exit 1 and not shfmt's error text, which differs by build."""
        parsed = run_shfmt(empty_form)
        assert parsed.returncode == 1, (
            f"{struct_name}.{key} could be omitted: shfmt accepted {empty_form!r}; {shfmt_exit_note(parsed)}"
        )
        assert parsed.stdout == b""

    @pytest.mark.parametrize(
        ("struct_name", "key"), sorted(EMPTY_FORMS_BY_LISTED_KEY), ids=[f"{s}.{k}" for s, k in sorted(EMPTY_FORMS_BY_LISTED_KEY)]
    )
    def test_each_key_with_a_rejected_empty_form_is_in_the_table_and_its_deletion_exits_5_naming_it(
        self, corpus_trees, struct_name, key
    ):
        assert key in TREE.ALWAYS_PRESENT_KEYS[struct_name]
        result = run_module(json.dumps(_tree_without_key(corpus_trees, struct_name, key)).encode("utf-8"))
        assert result.returncode == 5, result.stderr
        assert result.stdout == b""
        assert f"a {struct_name} object lacks the key {key}" in result.stderr.decode()

    @pytest.mark.parametrize("struct_name", sorted(set(TREE.NODE_FIELDS) - (TREE.BASH_REJECTED_NODE_TYPES | {"BraceExp"})))
    def test_an_unknown_key_on_the_first_corpus_instance_of_each_struct_exits_5_without_echoing_the_key(
        self, corpus_trees, struct_name
    ):
        tree = _tree_with_unknown_key(corpus_trees, struct_name)
        result = run_module(json.dumps(tree).encode("utf-8"))
        assert result.returncode == 5, result.stderr
        assert result.stdout == b""
        assert f"a {struct_name} object has an unknown key" in result.stderr.decode()
        assert CANARY.encode() not in result.stderr


class TestBareSubscriptArithmetic:
    """Arithmetic with a bare array subscript sits beside a gated command and must not deny it."""

    @pytest.mark.parametrize(
        ("command", "expected_commands"),
        [
            ('git commit -m "$((a[0]))"', [["git", "commit", "-m", PLACEHOLDER]]),
            ("((count[$k]++)); gh pr create --body-file f", [["gh", "pr", "create", "--body-file", "f"]]),
            ("let a[0]=1; git push", [["git", "push"]]),
            ("for ((i=0;i<n[0];i++)); do git push; done", [["git", "push"]]),
        ],
        ids=["inside-a-quoted-arithmetic-expansion", "increment-command", "let", "c-style-for"],
    )
    def test_the_command_beside_the_arithmetic_projects(self, command, expected_commands):
        assert simple_commands(command) == expected_commands


# The four substitution markers the strict check denies in an extglob pattern, and the places one can sit in it.
# A check that narrowed to the pattern's start or its first alternative would pass the first position alone.
EXTGLOB_SUBSTITUTION_MARKERS = {
    "command-substitution": "$(echo RAN)",
    "backticks": "`echo RAN`",
    "input-process-substitution": "<(echo RAN)",
    "output-process-substitution": ">(echo RAN)",
}
EXTGLOB_MARKER_POSITIONS = {
    "first": "{marker}|b",
    "after-a-bar": "a|{marker}",
    "mid-literal": "a{marker}b",
}
EXTGLOB_PATTERNS_HOLDING_A_SUBSTITUTION = {
    f"{marker_name}-{position_name}": position.format(marker=marker)
    for marker_name, marker in EXTGLOB_SUBSTITUTION_MARKERS.items()
    for position_name, position in EXTGLOB_MARKER_POSITIONS.items()
}


class TestExtGlobPatterns:
    def test_a_plain_pattern_projects_to_the_placeholder(self):
        assert simple_commands("echo x@(a|b)y") == [["echo", f"x{PLACEHOLDER}y"]]

    @pytest.mark.parametrize(
        "template",
        [
            "echo @({pattern})",
            "[[ x == a@({pattern}) ]]",
            "x=@({pattern})",
            "declare x=@({pattern})",
            "cat > @({pattern})",
            "case x in a@({pattern})) :;; esac",
            "for i in @({pattern}); do :; done",
        ],
        ids=["argument", "double-bracket", "assignment", "declaration", "redirect-target", "case-pattern", "for-word-list"],
    )
    @pytest.mark.parametrize(
        "pattern", EXTGLOB_PATTERNS_HOLDING_A_SUBSTITUTION.values(), ids=EXTGLOB_PATTERNS_HOLDING_A_SUBSTITUTION.keys()
    )
    def test_a_pattern_holding_a_substitution_exits_5(self, template, pattern):
        projected = project_words(template.replace("{pattern}", pattern))
        assert projected.returncode == 5, projected.stderr
        assert projected.stdout == b""
        assert b"RAN" not in projected.stderr

    @pytest.mark.parametrize("operator", ["?(", "*(", "+(", "@(", "!("], ids=["question", "star", "plus", "at", "bang"])
    def test_the_deny_holds_under_each_of_the_five_extglob_operators(self, operator):
        """A check keyed to one operator would pass the other four, and the walker cannot see a command in the pattern."""
        projected = project_words(f"echo {operator}a|$(echo RAN))")
        assert projected.returncode == 5, projected.stderr
        assert projected.stdout == b""
        assert b"RAN" not in projected.stderr


class TestBashRejectedNodeTypes:
    def test_samples_cover_exactly_the_rejected_set(self):
        assert set(BASH_REJECTED_SAMPLES) == TREE.BASH_REJECTED_NODE_TYPES

    @pytest.mark.parametrize("node_type", sorted(BASH_REJECTED_SAMPLES))
    def test_bash_rejects_the_sample_and_its_own_dialect_parses_it_to_the_type(self, node_type):
        sample, dialect = BASH_REJECTED_SAMPLES[node_type]
        rejected = run_shfmt(sample)
        assert rejected.returncode == 1, shfmt_exit_note(rejected)
        assert rejected.stdout == b""
        dialect_parse = run_shfmt(sample, argv=["shfmt", "-ln", dialect, "--to-json"])
        assert dialect_parse.returncode == 0, shfmt_exit_note(dialect_parse)
        assert node_type in _types_in(json.loads(dialect_parse.stdout))


class TestDialectIsPinnedToBash:
    """shfmt infers the dialect from a leading shebang on stdin, so each case has a control with the flag removed."""

    BATS_BY_SHEBANG = "#!/usr/bin/env bats\n" + BASH_REJECTED_SAMPLES["TestDecl"][0]
    BASH_UNDER_A_POSIX_SHEBANG = "#!/bin/sh\necho <(ls)"

    @staticmethod
    def _production_argv_without_the_dialect_flag() -> list[str]:
        argv = production_shfmt_argv()
        flag_index = argv.index("-ln")
        return argv[:flag_index] + argv[flag_index + 2 :]

    def test_a_bats_shebang_does_not_switch_the_dialect(self):
        with_flag = run_shfmt(self.BATS_BY_SHEBANG)
        assert with_flag.returncode == 1, shfmt_exit_note(with_flag)
        without_flag = run_shfmt(self.BATS_BY_SHEBANG, argv=self._production_argv_without_the_dialect_flag())
        assert without_flag.returncode == 0, f"control: the default dialect follows the shebang; {shfmt_exit_note(without_flag)}"

    def test_a_posix_shebang_does_not_narrow_the_dialect(self):
        with_flag = run_shfmt(self.BASH_UNDER_A_POSIX_SHEBANG)
        assert with_flag.returncode == 0, shfmt_exit_note(with_flag)
        without_flag = run_shfmt(self.BASH_UNDER_A_POSIX_SHEBANG, argv=self._production_argv_without_the_dialect_flag())
        assert without_flag.returncode == 1, f"control: the default dialect follows the shebang; {shfmt_exit_note(without_flag)}"


class TestEmptyLitOverDeny:
    """Pins the Lit.Value over-deny stated at ALWAYS_PRESENT_KEYS in shell-syntax-tree.py.

    Each case flips when a closure of the over-deny lands, or when shfmt starts writing an empty `Value`.
    Any closure must keep a missing `Value` on a non-empty `Lit` denying with exit 5, as the deletion case below checks.
    """

    COMMANDS = {
        "heredoc-line-ending-in-a-backslash-before-an-expansion": "cat <<EOF\nrun foo \\\n$ARGS\nEOF\n",
        "extglob-holding-only-a-continuation": "echo @(\\\n)",
    }

    @pytest.mark.parametrize("command", COMMANDS.values(), ids=COMMANDS.keys())
    def test_a_valid_command_that_leaves_a_lit_empty_exits_5_naming_the_key(self, command):
        valid_parse = run_shfmt(command)
        assert valid_parse.returncode == 0, f"the command is valid for shfmt; {shfmt_exit_note(valid_parse)}"
        projected = project_words(command)
        assert projected.returncode == 5, projected.stderr
        assert projected.stdout == b""
        assert "a Lit object lacks the key Value" in projected.stderr.decode()


class TestLitValueDeletionOnANonEmptyLit:
    """Names the key itself, so it does not shrink with ALWAYS_PRESENT_KEYS: a missing `Value` on a non-empty `Lit` exits 5.

    Any closure of the empty-`Lit` over-deny must keep this case green.
    `Lit.Value` carries every literal word, so a shfmt that stopped writing it would otherwise hide every word with exit 0.
    """

    def test_a_real_tree_with_value_deleted_from_a_non_empty_lit_exits_5_naming_the_key(self):
        tree = _shfmt_tree("echo hi")
        non_empty_lits = [node for struct_name, node in _iter_structs(tree) if struct_name == "Lit" and node.get("Value")]
        assert non_empty_lits, "vacuous case: the tree holds no non-empty Lit"
        del non_empty_lits[0]["Value"]
        result = run_module(json.dumps(tree).encode("utf-8"))
        assert result.returncode == 5, result.stderr
        assert result.stdout == b""
        assert "a Lit object lacks the key Value" in result.stderr.decode()


class TestHostileEditorconfigDoesNotChangeTheTree:
    """A cwd `.editorconfig` with another dialect must not change what the production argv yields from stdin.

    The command is a process substitution, whose result depends on the dialect, so a dialect change shows as an exit status.
    """

    HOSTILE_EDITORCONFIG = "root = true\n\n[*]\nshell_variant = posix\n"
    COMMAND = "echo <(ls)"

    def test_the_production_argv_yields_the_clean_directory_result(self, tmp_path):
        hostile_directory = tmp_path / "hostile"
        clean_directory = tmp_path / "clean"
        hostile_directory.mkdir()
        clean_directory.mkdir()
        (hostile_directory / ".editorconfig").write_text(self.HOSTILE_EDITORCONFIG)
        control_argv = [*TestDialectIsPinnedToBash._production_argv_without_the_dialect_flag(), "--filename", "x.sh"]

        control_in_hostile = run_shfmt(self.COMMAND, argv=control_argv, cwd=hostile_directory)
        control_in_clean = run_shfmt(self.COMMAND, argv=control_argv, cwd=clean_directory)
        control_results = [(result.returncode, result.stdout) for result in (control_in_hostile, control_in_clean)]
        if control_results[0] == control_results[1]:
            reason = "the control, `--filename x.sh` without `-ln bash`, gives the same result in a hostile and a clean directory"
            if os.environ.get("GITHUB_ACTIONS"):
                pytest.fail(f"{reason}, so the case would pass vacuously on CI's shfmt")
            pytest.skip(f"{reason} on this shfmt build, so the case would pass vacuously")

        production_in_hostile = run_shfmt(self.COMMAND, cwd=hostile_directory)
        production_in_clean = run_shfmt(self.COMMAND, cwd=clean_directory)
        assert production_in_clean.returncode == 0, shfmt_exit_note(production_in_clean)
        assert (production_in_hostile.returncode, production_in_hostile.stdout) == (
            production_in_clean.returncode,
            production_in_clean.stdout,
        ), f"in the hostile directory, {shfmt_exit_note(production_in_hostile)}"


def _types_above_the_command(tree) -> list[frozenset[str]]:
    """The `Type` of each object on the path from the root to every `CallExpr` holding COMMAND_WORDS_UNDER_TEST."""
    paths = []
    stack = [(tree, ())]
    while stack:
        value, types_above = stack.pop()
        if isinstance(value, dict):
            if "Type" in value:
                types_above = (*types_above, value["Type"])
            command_words = [TREE.flatten_word(arg) for arg in value.get("Args", ())]
            if value.get("Type") == "CallExpr" and command_words == COMMAND_WORDS_UNDER_TEST:
                paths.append(frozenset(types_above))
            stack.extend((child, types_above) for child in value.values())
        elif isinstance(value, list):
            stack.extend((child, types_above) for child in value)
    return paths


class TestChildPositionMatrix:
    @pytest.mark.parametrize("row", CHILD_POSITION_MATRIX, ids=[row.construct for row in CHILD_POSITION_MATRIX])
    def test_a_command_in_the_position_surfaces_in_words(self, row):
        command = row.template.replace("{command}", COMMAND_UNDER_TEST)
        assert COMMAND_WORDS_UNDER_TEST in simple_commands(command)

    @pytest.mark.parametrize("row", CHILD_POSITION_MATRIX, ids=[row.construct for row in CHILD_POSITION_MATRIX])
    def test_the_command_sits_under_each_holder_type_the_row_names(self, row):
        tree = _shfmt_tree(row.template.replace("{command}", COMMAND_UNDER_TEST))
        paths = _types_above_the_command(tree)
        assert any(row.holder_types <= types_above for types_above in paths), (row.holder_types, [sorted(p) for p in paths])

    def test_every_known_node_type_is_in_the_matrix_or_holds_no_command_or_is_denied_for_its_text(self):
        accounted_for = (
            COMMAND_HOLDING_TYPES
            | NODE_TYPES_HOLDING_NO_COMMAND
            | NODE_TYPES_DENIED_WHEN_THEIR_TEXT_HOLDS_A_SUBSTITUTION
        )
        assert accounted_for >= TREE.KNOWN_NODE_TYPES
        assert not COMMAND_HOLDING_TYPES & NODE_TYPES_HOLDING_NO_COMMAND
        assert not COMMAND_HOLDING_TYPES & NODE_TYPES_DENIED_WHEN_THEIR_TEXT_HOLDS_A_SUBSTITUTION
        assert not NODE_TYPES_HOLDING_NO_COMMAND & NODE_TYPES_DENIED_WHEN_THEIR_TEXT_HOLDS_A_SUBSTITUTION
        assert COMMAND_HOLDING_TYPES <= TREE.KNOWN_NODE_TYPES

    @pytest.mark.parametrize("node_type", sorted(NODE_TYPES_HOLDING_NO_COMMAND))
    def test_a_type_that_holds_no_command_has_only_position_and_scalar_fields(self, node_type):
        assert set(TREE.NODE_FIELDS[node_type].values()) <= {"pos", "scalar"}

    @pytest.mark.parametrize("node_type", sorted(NODE_TYPES_DENIED_WHEN_THEIR_TEXT_HOLDS_A_SUBSTITUTION))
    def test_a_type_denied_for_its_text_has_only_position_scalar_and_literal_fields(self, node_type):
        assert set(TREE.NODE_FIELDS[node_type].values()) <= {"pos", "scalar", "Lit"}
