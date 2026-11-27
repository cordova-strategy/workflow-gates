"""Tests for the `words` projection of shell-syntax-tree.py, run on real shfmt.

Each case pipes a Bash command through shfmt run with `_LIB_SHFMT_ARGV`
and the module, then asserts the words bash itself sees.
`simple_commands` returns one word list per simple command, in the order the
module writes them: a command's own words come before the commands nested in
its arguments.

A test that runs shfmt skips locally when shfmt is not installed and fails under
GITHUB_ACTIONS. The module's contract tests that need no shfmt live in
test_shell_syntax_tree_contract.py.
"""
from __future__ import annotations

import itertools
import json
import os
import sys
import unicodedata

import pytest
from helpers import HEREDOC_BODY_WITH_GAP_APOSTROPHE, heredoc_substitution

from ._shell_syntax_tree_runners import (
    AGREEMENT,
    AGREES,
    FLAG_AND_PATH,
    FLAG_WORD,
    HIDDEN,
    MEMBER,
    MEMBER_OUTCOMES,
    PATH_WORD,
    RENAMED_FLAG,
    SHOWN,
    UNGUARDED_DIVERGENCE_AGREEMENT_CASES,
    UNGUARDED_DIVERGENCE_FIXTURES,
    UNGUARDED_DIVERGENCE_MEMBERS,
    differences_from_real_bash,
    holds_flag_and_path,
    iter_objects,
    project_words,
    real_bash_version_line,
    run_real_bash,
    run_shfmt,
    shell_syntax_tree,
    shfmt_exit_note,
    simple_commands,
)

PLACEHOLDER = shell_syntax_tree.EXPANSION_PLACEHOLDER


def flat_words(command: str) -> list[str]:
    return [word for words in simple_commands(command) for word in words]


class TestHeredocBodies:
    def test_multiline_double_quoted_value_flattens_to_one_word_before_next_flag(self):
        words = flat_words('git commit -m "line one\nline two" -F /x')
        assert words == ["git", "commit", "-m", "line one line two", "-F", "/x"]

    def test_heredoc_in_substitution_with_odd_quotes_and_backticks_is_not_a_word(self):
        command = (
            "gh pr create --body \"$(cat <<'EOF'\n"
            "it's \"odd\" and \"unbalanced\n"
            "a `backtick` line, don't\n"
            "EOF\n"
            ')" --body-file /x'
        )
        assert simple_commands(command) == [
            ["gh", "pr", "create", "--body", PLACEHOLDER, "--body-file", "/x"],
            ["cat"],
        ]

    def test_shared_allow_guard_fixture_command_projects_without_the_heredoc_body(self):
        command = f"git commit -m {heredoc_substitution(HEREDOC_BODY_WITH_GAP_APOSTROPHE)} -F /x"
        assert simple_commands(command) == [
            ["git", "commit", "-m", PLACEHOLDER, "-F", "/x"],
            ["cat"],
        ]

    def test_two_heredoc_substitutions_chained_with_and(self):
        command = (
            "git commit -m \"$(cat <<'EOF'\nfirst it's\nEOF\n)\" && "
            "gh pr create --body \"$(cat <<'EOF'\nsecond \"odd\nEOF\n)\" --body-file /x"
        )
        assert simple_commands(command) == [
            ["git", "commit", "-m", PLACEHOLDER],
            ["cat"],
            ["gh", "pr", "create", "--body", PLACEHOLDER, "--body-file", "/x"],
            ["cat"],
        ]

    def test_tail_of_opener_line_survives(self):
        command = "cat <<EOF && gh pr create --body-file /x\nbody text it's\nEOF"
        assert simple_commands(command) == [["cat"], ["gh", "pr", "create", "--body-file", "/x"]]

    def test_dash_heredoc_with_tab_indented_terminator(self):
        command = "cat <<-EOF\n\tbody -F /evil\n\tEOF\ngh pr create --body-file /x"
        assert simple_commands(command) == [["cat"], ["gh", "pr", "create", "--body-file", "/x"]]

    def test_plain_heredoc_does_not_strip_tabs_from_terminator(self):
        command = "cat <<EOF\nbody\n\tEOF\nEOF\ngh pr create --body-file /x"
        assert simple_commands(command) == [["cat"], ["gh", "pr", "create", "--body-file", "/x"]]

    @pytest.mark.parametrize(
        "opener",
        ["<<\\EOF", '<<"EOF"', "<< EOF", "<< 'EOF'"],
        ids=["backslash-prefixed", "double-quoted", "blank-then-bare", "blank-then-quoted"],
    )
    def test_delimiter_spelling_does_not_change_where_the_body_ends(self, opener):
        command = f"cat {opener}\nbody it's -F /evil\nEOF\ngh pr create --body-file /x"
        assert simple_commands(command) == [["cat"], ["gh", "pr", "create", "--body-file", "/x"]]

    def test_here_string_is_not_an_opener(self):
        assert simple_commands("cat <<<EOF\nkeep --body-file /x\nEOF") == [
            ["cat"],
            ["keep", "--body-file", "/x"],
            ["EOF"],
        ]

    def test_quoted_opener_mention_without_terminator_drops_nothing(self):
        command = 'echo "see <<EOF for setup"\ngh pr create --body-file /x'
        assert simple_commands(command) == [
            ["echo", "see <<EOF for setup"],
            ["gh", "pr", "create", "--body-file", "/x"],
        ]

    @pytest.mark.parametrize("separator", ["\u2028", "\x0c"], ids=["u2028", "form-feed"])
    def test_body_line_holding_a_non_lf_line_break_stays_in_the_body(self, separator):
        command = f"cat <<'EOF'\nx{separator}EOF\n-F /evil\nEOF\ngh pr create --body-file /x"
        assert simple_commands(command) == [["cat"], ["gh", "pr", "create", "--body-file", "/x"]]

    def test_two_openers_on_one_line_drop_both_bodies(self):
        command = "cat <<A <<B\nfirst -F /evil1\nA\nsecond -F /evil2\nB\ngh pr create --body-file /x"
        assert simple_commands(command) == [["cat"], ["gh", "pr", "create", "--body-file", "/x"]]


class TestLineContinuationsAndComments:
    def test_backslash_newline_without_indentation_joins_lines(self):
        assert flat_words("gh pr create \\\n--body-file /x") == ["gh", "pr", "create", "--body-file", "/x"]

    def test_escaped_backslash_before_newline_is_not_a_continuation(self):
        assert simple_commands("echo a\\\\\nb") == [["echo", "a\\"], ["b"]]

    @pytest.mark.parametrize(
        "comment_lines",
        ["# it's the plan\n", "  \t# it's indented\n", "# note \\\n"],
        ids=["apostrophe", "indented-apostrophe", "ends-in-backslash"],
    )
    def test_comment_line_before_command_adds_no_words_and_joins_no_line(self, comment_lines):
        assert simple_commands(comment_lines + "gh pr create --body-file /x") == [
            ["gh", "pr", "create", "--body-file", "/x"]
        ]

    def test_mid_word_hash_stays_in_its_word(self):
        assert flat_words("git commit -m Fix#12 -F /x/msg") == ["git", "commit", "-m", "Fix#12", "-F", "/x/msg"]

    def test_hash_inside_path_keeps_whole_path_and_following_flags(self):
        words = flat_words("gh pr create --body-file /tmp/dir#1/body.md --repo r")
        assert words == ["gh", "pr", "create", "--body-file", "/tmp/dir#1/body.md", "--repo", "r"]

    def test_quoted_line_that_is_exactly_a_flag_never_equals_the_flag_word(self):
        words = flat_words('gh pr create --body "intro\n-F\n/evil\nmore" --repo r')
        assert "-F" not in words
        assert words == ["gh", "pr", "create", "--body", "intro -F /evil more", "--repo", "r"]


class TestWordShapes:
    def test_single_line_word_of_200_kb_then_flag(self):
        words = flat_words("echo " + "x" * 200_000 + " -F /x")
        assert words[-2:] == ["-F", "/x"]
        assert len(words[1]) == 200_000

    @pytest.mark.parametrize(
        ("command", "expected"),
        [
            ("gh pr create --body-file=/x", ["gh", "pr", "create", "--body-file=/x"]),
            ("git commit -F=/x", ["git", "commit", "-F=/x"]),
            ("git commit -F '/path with space/msg'", ["git", "commit", "-F", "/path with space/msg"]),
            ("git commit -m 'a b' --file=/x -F '/p q/r'", ["git", "commit", "-m", "a b", "--file=/x", "-F", "/p q/r"]),
            ('git commit -m "a b" -F=/x', ["git", "commit", "-m", "a b", "-F=/x"]),
            ("a\\ b c", ["a b", "c"]),
            (
                "gh pr create --body-file /x --repo owner/name",
                ["gh", "pr", "create", "--body-file", "/x", "--repo", "owner/name"],
            ),
            ("git commit -m 'it\"s' -F /x", ["git", "commit", "-m", 'it"s', "-F", "/x"]),
        ],
    )
    def test_equals_form_quoted_path_and_plain_words(self, command, expected):
        assert flat_words(command) == expected

    @pytest.mark.parametrize(
        "command",
        [b"git commit -F /x/\xff/msg\n", b"echo 'a\xffb'", b"echo a # \xff\n", b"cat <<E\n\xff\nE\n"],
        ids=["in-a-word", "in-single-quotes", "in-a-comment", "in-a-heredoc-body"],
    )
    def test_non_utf8_byte_anywhere_in_the_command_makes_shfmt_reject_it_with_exit_1(self, command):
        """shfmt neither carries a non-UTF-8 byte into its JSON nor replaces it: it exits 1 and prints no tree."""
        parsed = run_shfmt(command)
        assert parsed.returncode == 1, shfmt_exit_note(parsed)
        assert parsed.stdout == b""

    def test_valid_multibyte_utf8_round_trips_through_the_entry_point(self):
        command = "git commit -m “quoted”—dash -F /x/é.md"
        assert flat_words(command) == ["git", "commit", "-m", "“quoted”—dash", "-F", "/x/é.md"]

    def test_replacement_character_in_a_word_projects_to_its_three_utf8_bytes(self):
        """jq writes U+FFFD for a non-UTF-8 byte in a gate's payload, so that is the form a gate's word holds."""
        projected = project_words("git commit -F /x/�/msg")
        assert projected.returncode == 0
        assert projected.stdout == b"git\ncommit\n-F\n/x/\xef\xbf\xbd/msg\n\n"

    @pytest.mark.parametrize("command", ["", "# git commit -F /dirty.md\n"], ids=["empty", "comment-only"])
    def test_empty_command_and_comment_only_command_project_no_words(self, command):
        projected = project_words(command)
        assert projected.returncode == 0
        assert projected.stdout == b""

    def test_a_trailing_backslash_newline_is_a_continuation(self):
        assert flat_words("echo trailing\\\n") == ["echo", "trailing"]

    def test_a_final_unescaped_backslash_with_no_newline_stays_in_the_word_as_bash_prints_it(self):
        projected = project_words("echo a\\")
        assert (projected.returncode, projected.stdout) == (0, b"echo\na\\\n\n")

    @pytest.mark.parametrize(
        ("command", "expected_stdout"),
        [
            ('echo "" x -F /y', b"echo\n\nx\n-F\n/y\n\n"),
            ("echo '' x -F /y", b"echo\n\nx\n-F\n/y\n\n"),
            ('echo a ""', b"echo\na\n\n\n"),
            ("echo a ''", b"echo\na\n\n\n"),
            ('git commit -F "" -m x', b"git\ncommit\n-F\n\n-m\nx\n\n"),
        ],
        ids=["double-quoted-inside", "single-quoted-inside", "double-quoted-last", "single-quoted-last", "after-a-flag"],
    )
    def test_an_empty_word_projects_to_a_blank_line_at_its_position(self, command, expected_stdout):
        """`simple_commands` drops an empty word as the command separator, so this reads the raw stdout."""
        projected = project_words(command)
        assert (projected.returncode, projected.stdout) == (0, expected_stdout)


class TestInvalidBashIsRejectedByShfmt:
    @pytest.mark.parametrize(
        "command",
        [
            "git commit -m it's -F /x",
            'gh pr create --title "unterminated --body-file /x',
            "echo $(",
            "echo `",
            "cat <<EOF\nabc\n",
            "echo ${(f)x}",
        ],
        ids=["lone-apostrophe", "unterminated-double-quote", "unclosed-substitution", "unclosed-backtick",
             "unterminated-heredoc", "zsh-only-expansion-flag"],
    )  # fmt: skip
    def test_exit_1_and_no_tree(self, command):
        parsed = run_shfmt(command)
        assert parsed.returncode == 1, shfmt_exit_note(parsed)
        assert parsed.stdout == b""


class TestBackslashAndQuoteHandling:
    """Pins the words bash sees for backslash, quote and echo-option handling."""

    def test_backslash_newline_joins_the_lines_into_one_word(self):
        assert flat_words("a\\\nb") == ["ab"]

    def test_escaped_double_quote_inside_double_quotes_is_part_of_the_word(self):
        assert flat_words('echo "say \\"hi\\" now" x') == ["echo", 'say "hi" now', "x"]

    def test_backslash_pair_inside_double_quotes_yields_one_backslash(self):
        assert flat_words(r'echo "a\\b" x') == ["echo", "a\\b", "x"]

    @pytest.mark.parametrize("flag_like_word", ["-e", "-n", "-E"])
    def test_echo_option_words_are_kept(self, flag_like_word):
        assert flat_words(f"foo {flag_like_word} bar") == ["foo", flag_like_word, "bar"]


class TestResidualShapes:
    """Pins the words bash sees for each shape that split-command-words.py's docstring lists as a residual over-deny."""

    def test_substitution_with_inner_quotes_that_left_flat_quote_parity_open(self):
        command = 'gh pr create --title "$(echo "it\'s")" --body-file /x'
        assert simple_commands(command) == [
            ["gh", "pr", "create", "--title", PLACEHOLDER, "--body-file", "/x"],
            ["echo", "it's"],
        ]

    def test_ansi_c_string_with_an_escaped_apostrophe(self):
        assert simple_commands("git commit -m $'it\\'s' -F /x") == [
            ["git", "commit", "-m", PLACEHOLDER, "-F", "/x"]
        ]

    def test_inline_comment_holding_an_unbalanced_quote(self):
        assert flat_words("git commit -F /x  # don't amend\n") == ["git", "commit", "-F", "/x"]

    def test_closing_quote_on_a_line_starting_with_hash(self):
        assert flat_words('git commit -m "Fix parser\n\n#123" -F /x\n') == [
            "git", "commit", "-m", "Fix parser  #123", "-F", "/x",
        ]  # fmt: skip

    def test_quoted_opener_mention_followed_by_matching_line_keeps_the_lines_between(self):
        command = (
            'echo "see <<WORD in text"\ngh pr create --body-file /y --repo r\nWORD\n'
            "gh pr create --body-file /z"
        )
        assert simple_commands(command) == [
            ["echo", "see <<WORD in text"],
            ["gh", "pr", "create", "--body-file", "/y", "--repo", "r"],
            ["WORD"],
            ["gh", "pr", "create", "--body-file", "/z"],
        ]

    @pytest.mark.parametrize(
        ("command", "word_between_the_commands"),
        [
            ("# create it via <<EOF\ngh pr create --body-file /y\nEOF\ngh pr create --body-file /z", "EOF"),
            ("echo $((1<<3))\ngh pr create --body-file /y\n3\ngh pr create --body-file /z", "3"),
        ],
        ids=["opener-in-comment-line", "arithmetic-shift"],
    )
    def test_opener_in_a_comment_line_or_arithmetic_shift_keeps_the_lines_between(self, command, word_between_the_commands):
        assert simple_commands(command)[-3:] == [
            ["gh", "pr", "create", "--body-file", "/y"],
            [word_between_the_commands],
            ["gh", "pr", "create", "--body-file", "/z"],
        ]

    def test_comment_looking_line_inside_a_quoted_value_does_not_hide_the_next_flag(self):
        command = 'gh pr create --title "x\n# " --body-file /hidden --title "z\nfinal"'
        assert flat_words(command) == [
            "gh", "pr", "create", "--title", "x # ", "--body-file", "/hidden", "--title", "z final",
        ]  # fmt: skip

    def test_apostrophes_in_inline_comments_on_two_lines_do_not_fold_the_lines_between(self):
        command = (
            "tool-a --file /tmp/msg.txt  # don't amend\n"
            "tool-b create --title \"x\" --body-file /tmp/body.md  # it's ready"
        )
        assert simple_commands(command) == [
            ["tool-a", "--file", "/tmp/msg.txt"],
            ["tool-b", "create", "--title", "x", "--body-file", "/tmp/body.md"],
        ]


def _comment_texts(tree) -> list[str]:
    """The `Text` of every `Comment` in a shfmt tree, which the tree carries under a `Comments` key."""
    return [comment["Text"] for node in iter_objects(tree) for comment in node.get("Comments", [])]


class TestCarriageReturnBeforeAHash:
    """The two premises of a carriage return before `#`: shfmt reads the carriage return as a
    blank where bash reads it as an ordinary word character."""

    COMMAND = "echo x\r# -F /dirty.md"

    def test_shfmt_puts_the_flag_and_path_inside_a_comment_so_the_projection_drops_them(self):
        parsed = run_shfmt(self.COMMAND)
        assert parsed.returncode == 0, shfmt_exit_note(parsed)
        assert _comment_texts(json.loads(parsed.stdout)) == [" -F /dirty.md"]
        assert flat_words(self.COMMAND) == ["echo", "x"]

    def test_bash_passes_the_carriage_return_hash_flag_and_path_as_three_words(self):
        bash_output = run_real_bash("printf '%s\\0' x\r# -F /dirty.md").stdout
        assert bash_output.decode("utf-8").split("\0")[:-1] == ["x\r#", "-F", "/dirty.md"], real_bash_version_line()


# Each entry is the words before the flag's value word, and the text that value word starts with.
ATTACHED_FLAG_PREFIXES = [
    ([], "--body-file="), ([], "--template="), ([], "-F="), ([], "-T="), ([], "--file="), ([], "--input="),
    (["-f"], "body=@"), (["-F"], "body=@"), (["--field"], "body=@"), (["--raw-field"], "body=@"),
]  # fmt: skip

EXPANSION_SPELLINGS = {
    "parameter": "$F",
    "braced-parameter": "${F}",
    "command-substitution": "$(printf /x)",
    "backticks": "`printf /x`",
    "arithmetic": "$((1+1))",
    "ansi-c": "$'x'",
    "double-quoted-parameter": '"$F"',
    "double-quoted-substitution": '"$(printf /x)"',
}


class TestAttachedFlagForms:
    @pytest.mark.parametrize(
        ("words_before_the_value", "value_prefix"),
        ATTACHED_FLAG_PREFIXES,
        ids=[" ".join([*words_before, prefix]) for words_before, prefix in ATTACHED_FLAG_PREFIXES],
    )
    @pytest.mark.parametrize("spelling", EXPANSION_SPELLINGS.values(), ids=EXPANSION_SPELLINGS.keys())
    def test_prefix_survives_and_the_value_becomes_the_placeholder(self, words_before_the_value, value_prefix, spelling):
        command = " ".join(["tool", *words_before_the_value, value_prefix + spelling])
        assert simple_commands(command)[0] == ["tool", *words_before_the_value, value_prefix + PLACEHOLDER]

    def test_literal_text_on_both_sides_of_an_expansion_survives(self):
        assert simple_commands("$HOME/bin/git push --body-file=/a/${X}/b") == [
            [PLACEHOLDER + "/bin/git", "push", "--body-file=/a/" + PLACEHOLDER + "/b"]
        ]

    def test_placeholder_inside_double_quotes_keeps_the_literal_text_around_it(self):
        assert flat_words('tool "pre-$X-post"') == ["tool", f"pre-{PLACEHOLDER}-post"]


# Each realistic command, and the gated commands whose words its projection must carry.
SMOKE_COMMANDS = {
    "heredoc-body-substitution": (
        "gh pr create --title t --body \"$(cat <<'EOF'\n## Summary\n- one `x`\n\nIt's done.\nEOF\n)\"",
        [["gh", "pr", "create", "--title", "t", "--body", PLACEHOLDER]],
    ),
    "heredoc-commit-message": ("git commit -F - <<'EOF'\nsubject\n\nbody line\nEOF", [["git", "commit", "-F", "-"]]),
    "and-chain": (
        "git add -A && git commit -m 'msg' && git push origin HEAD",
        [["git", "add", "-A"], ["git", "commit", "-m", "msg"], ["git", "push", "origin", "HEAD"]],
    ),
    "for-loop": (
        "for f in a b c; do gh pr create --body-file \"$f\"; done",
        [["gh", "pr", "create", "--body-file", PLACEHOLDER]],
    ),
    "double-bracket-guard": (
        "[[ -f notes.md ]] && gh pr create --body-file notes.md",
        [["gh", "pr", "create", "--body-file", "notes.md"]],
    ),
}


@pytest.mark.parametrize(("command", "gated_commands"), SMOKE_COMMANDS.values(), ids=SMOKE_COMMANDS.keys())
def test_realistic_command_exits_0_with_the_gated_commands_words(command, gated_commands):
    projected = project_words(command)
    assert projected.returncode == 0, projected.stderr
    commands = simple_commands(command)
    for gated_command in gated_commands:
        assert gated_command in commands


class TestBackslashDecoding:
    @pytest.mark.parametrize(
        ("command", "expected_words"),
        [
            (r"echo \-F /y", ["echo", "-F", "/y"]),
            (r"echo \a", ["echo", "a"]),
            (r'echo "b\"c"', ["echo", 'b"c']),
            (r'echo "\$x"', ["echo", "$x"]),
            (r'echo "\a"', ["echo", "\\a"]),
        ],
        ids=["unquoted-flag", "unquoted-letter", "double-quoted-quote", "double-quoted-dollar", "double-quoted-letter"],
    )
    def test_each_form_yields_the_word_bash_sees(self, command, expected_words):
        assert flat_words(command) == expected_words

    @pytest.mark.parametrize(
        "last_word",
        [None, "a\\", "\\", "\\\\\\"],
        ids=["no-final-backslash", "letter-then-backslash", "backslash-alone", "escaped-backslash-then-backslash"],
    )
    def test_words_equal_what_real_bash_prints_for_a_generated_set_of_literal_only_words(self, last_word):
        """A `last_word` ends the command on an odd run of backslashes, with no newline after it."""
        words_under_test = _generated_literal_only_words() + ([] if last_word is None else [last_word])
        command = "printf '%s\\0' " + " ".join(words_under_test)
        bash_output = run_real_bash(command).stdout
        bash_words = bash_output.decode("utf-8").split("\0")[:-1]
        module_commands = simple_commands(command)
        assert len(module_commands) == 1
        assert module_commands[0][2:] == bash_words, real_bash_version_line()
        assert len(bash_words) == len(words_under_test) > 300


# Fragments with no `$`, backtick, glob character, brace or leading `~` that a backslash does not escape,
# so bash expands nothing in a word built from them.
_UNQUOTED_FRAGMENTS = ["a", "\\a", "\\\\", "\\-F", "\\ ", "\\é", "é", "\\$", '\\"', "\\'", "\\;", "\\\\\\\\", "\\\n"]
_DOUBLE_QUOTED_FRAGMENTS = ["a", "\\a", "\\\\", "\\$", "\\`", '\\"', "\\é", "é", " ", "\\\n", "#"]


def _generated_literal_only_words() -> list[str]:
    unquoted_words = [
        "".join(fragments)
        for length in (1, 2)
        for fragments in itertools.product(_UNQUOTED_FRAGMENTS, repeat=length)
    ]
    double_quoted_words = [
        '"' + "".join(fragments) + '"'
        for length in (1, 2)
        for fragments in itertools.product(_DOUBLE_QUOTED_FRAGMENTS, repeat=length)
    ]
    mixed_words = [
        unquoted_before + '"' + inside + '"' + unquoted_after
        for unquoted_before, inside, unquoted_after in itertools.product(
            ["a", "\\a", "\\\\"], _DOUBLE_QUOTED_FRAGMENTS, ["b", "\\ ", "\\$"]
        )
    ]
    # A word that is only backslash-newlines is no word, or an empty word, which the module's blank-line
    # separator cannot show, so it is left out.
    return [
        word
        for word in unquoted_words + double_quoted_words + mixed_words
        if word.replace("\\\n", "") not in ("", '""')
    ]


# Bash's metacharacters, quotes, `\`, `$` and backtick, `#`, the glob and brace characters, `~`, and the
# carriage return, which shfmt reads as a blank where bash keeps it in the word.
_BASH_SYNTAX_CHARACTERS = frozenset(" \t\n|&;()<>'\"\\$`#*?[]{}~\r")

_WORD_POSITIONS = {
    "mid-word": "x{c}y",
    "word-start": "{c}x",
    "word-end": "x{c}",
    "before-hash": "x{c}#",
}


def _characters_outside_bashs_syntax_set() -> list[str]:
    latin_1_range = [chr(code_point) for code_point in range(0x01, 0x100)]
    whitespace_and_format_characters = [
        chr(code_point)
        for code_point in range(0x100, sys.maxunicode + 1)
        if unicodedata.category(chr(code_point)) in ("Zs", "Zl", "Zp", "Cf")
    ]
    return [
        character
        for character in latin_1_range + whitespace_and_format_characters
        if character not in _BASH_SYNTAX_CHARACTERS
    ]


class TestCharactersShfmtAndBashReadAlike:
    """A tripwire against a shfmt build that reads one of these characters as bash does not.

    No current defect is guarded: it holds at the shfmt build CI pins and no other. A character it
    catches needs the denial the carriage return gets.
    """

    @pytest.mark.parametrize("position_template", _WORD_POSITIONS.values(), ids=_WORD_POSITIONS.keys())
    def test_each_word_equals_what_real_bash_prints(self, position_template):
        characters = _characters_outside_bashs_syntax_set()
        words_under_test = [position_template.format(c=character) for character in characters]
        # The `-F /y` tail shows a `#` read as a comment start: the words after it vanish.
        command = "printf '%s\\0' " + " ".join(words_under_test) + " -F /y"
        bash_output = run_real_bash(command, env={**os.environ, "LC_ALL": "C"}).stdout
        bash_words = bash_output.decode("utf-8").split("\0")[:-1]
        module_commands = simple_commands(command)
        assert len(module_commands) == 1
        module_words = module_commands[0][2:]
        assert len(bash_words) == len(words_under_test) + 2
        divergent_characters = [
            f"U+{ord(character):04X}"
            for character, module_word, bash_word in zip(characters, module_words, bash_words, strict=False)
            if module_word != bash_word
        ]
        assert module_words == bash_words, f"first divergent characters: {divergent_characters[:5]} ({real_bash_version_line()})"


# Each shape is a command as written, its text for bash with `w ` before each command name outside a
# substitution, and the module's commands that sit inside a substitution or on a pipe's left. A pipe's
# left command prints into the pipe, so bash's output never shows it.
CONTINUATION_SHAPES = {
    "gh-api-call-with-field-flags": (
        "gh api repos/o/r/pulls/1/comments \\\n-X POST \\\n-f body='a reply' \\\n-F in_reply_to=1",
        "w gh api repos/o/r/pulls/1/comments \\\n-X POST \\\n-f body='a reply' \\\n-F in_reply_to=1",
        frozenset(),
    ),
    "commit-with-a-flag-on-the-next-line": ("git commit \\\n-m x", "w git commit \\\n-m x", frozenset()),
    "cd-chain": ("cd x && \\\ngit status", "w cd x && \\\nw git status", frozenset()),
    "quoted-heredoc-whose-last-line-ends-in-a-backslash": (
        "gh pr create --body-file /x --body \"$(cat <<'EOF'\nsnippet\nlast line \\\nEOF\n)\"",
        "w gh pr create --body-file /x --body \"$(cat <<'EOF'\nsnippet\nlast line \\\nEOF\n)\"",
        frozenset({"cat"}),
    ),
    "quoted-heredoc-with-a-blank-line-before-the-terminator": (
        "gh pr create --body-file /x --body \"$(cat <<'EOF'\nsnippet\nlast line \\\n\nEOF\n)\"",
        "w gh pr create --body-file /x --body \"$(cat <<'EOF'\nsnippet\nlast line \\\n\nEOF\n)\"",
        frozenset({"cat"}),
    ),
    "unquoted-heredoc-holding-snippet-lines": (
        'gh pr create --body-file /x --body "$(cat <<EOF\ngit commit \\\n  -m x\ngh api -X POST \\\n  -f a=b\nEOF\n)"',
        'w gh pr create --body-file /x --body "$(cat <<EOF\ngit commit \\\n  -m x\ngh api -X POST \\\n  -f a=b\nEOF\n)"',
        frozenset({"cat"}),
    ),
    "pipe-followed-by-a-continuation": (
        "echo y | \\\n  gh pr create --body-file /x --body \"$(cat <<'EOF'\nbody\nEOF\n)\"",
        "w echo y | \\\n  w gh pr create --body-file /x --body \"$(cat <<'EOF'\nbody\nEOF\n)\"",
        frozenset({"cat", "echo"}),
    ),
    "continuation-inside-double-quotes": (
        'gh pr create --body-file /x --title "multi \\\nline title"',
        'w gh pr create --body-file /x --title "multi \\\nline title"',
        frozenset(),
    ),
}


class TestModuleWordsEqualWhatRealBashPrints:
    """Runs each command through the module, and its `w`-prefixed text through real bash with only builtins available.

    An agreement case run on a bash that hides its flag-and-path call shows as a differing command count or word list.
    """

    @pytest.mark.parametrize(
        ("command", "bash_command", "nested_command_names"),
        [pytest.param(*shape, id=shape_id) for shape_id, shape in CONTINUATION_SHAPES.items()]
        + [
            pytest.param(case.command, case.bash_command, case.nested_command_names, id=case.id)
            for case in UNGUARDED_DIVERGENCE_AGREEMENT_CASES
        ],
    )
    def test_each_command_and_agreement_case_matches(self, command, bash_command, nested_command_names):
        differences = differences_from_real_bash(command, bash_command, nested_command_names)
        assert differences == [], f"{real_bash_version_line()}: {differences}"


EXPECTED_MEMBER_IDS = frozenset(
    {
        "delimiter-mismatch-delimiter-quoted-in-a-non-last-part",
        "delimiter-mismatch-double-quoted-delimiter-holding-a-backslash",
        "delimiter-mismatch-ansi-c-delimiter-decoding-to-the-terminator",
        "delimiter-mismatch-locale-delimiter-holding-a-backslash",
        "heredoc-in-backtick-substitution-closing-on-the-opener-line",
        "heredoc-in-backtick-substitution-quoted-delimiter-that-is-a-command-line",
        "heredoc-in-backtick-substitution-body-holding-a-bare-backtick",
        "extglob-pattern-holding-a-brace-substitution",
        "stdin-fed-to-an-interpreter-heredoc-to-a-shell",
        "stdin-fed-to-an-interpreter-hand-off-across-statements",
        "stdin-fed-to-an-interpreter-that-is-not-a-shell",
        "backslash-newline-continuation-splitting-a-heredoc-terminator",
        "backslash-newline-heredoc-body-whose-first-line-is-a-lone-backslash",
        "backslash-newline-comment-ending-in-a-backslash-on-a-heredoc-opener-line",
        "backslash-newline-quoted-heredoc-in-backticks-with-a-split-terminator",
        "backslash-newline-single-quoted-words-split-inside-backticks",
        "backslash-newline-between-dollar-and-open-parenthesis",
        "backslash-newline-before-a-single-quoted-part-of-a-flag",
        "backslash-newline-before-a-double-quoted-part-of-a-flag",
        "backslash-newline-trailing-comment-ending-in-a-backslash",
        "flush-comment-in-a-subshell",
        "flush-comment-in-a-quoted-command-substitution",
        "flush-comment-in-a-process-substitution",
        "flush-comment-in-backticks",
        "flush-comment-in-a-case-arm",
        "flush-comment-after-an-expansion-in-a-subshell",
        "flush-comment-in-an-array-literal",
        "flush-comment-in-a-declared-array-literal",
        "flush-comment-after-array-literal-closer",
        "flush-comment-after-extglob-closer",
    }
)

# The flush-comment class's boundary forms, each with the agreement case that pins it and the text it must hold.
FLUSH_COMMENT_BOUNDARY_FORMS = {
    "top level": ("agreement-flush-comment-at-top-level", 'git commit -m "x"# -F /dirty.md'),
    "inside braces": ("agreement-flush-comment-in-braces", '{ git commit -m "x"# -F /dirty.md\n}'),
    "after an expansion at top level": (
        "agreement-flush-comment-after-an-expansion-at-top-level",
        "git commit -m $x# -F /dirty.md",
    ),
}

# Each container and closer pair of a below-floor bash's heredoc-in-a-substitution hide: the agreement case that covers
# it, and the container's opener with the closer on the heredoc body's first line.
CONTAINER_CLOSER_PAIRS = {
    "command substitution closed by `)`, unquoted assignment": (
        "agreement-command-substitution-closer-in-an-unquoted-assignment",
        "x=$(cat <<'EOF'\n1)\n",
    ),
    "command substitution closed by `)`, export": (
        "agreement-command-substitution-closer-in-an-export",
        "export x=$(cat <<'EOF'\n1)\n",
    ),
    "process substitution closed by `)`": ("agreement-process-substitution-closer", "<(cat <<'EOF'\n1)\n"),
    "parameter default closed by `}`": ("agreement-parameter-default-closer", "${x:-$(cat <<'EOF'\n}\n"),
    "array subscript closed by `]`": ("agreement-array-subscript-closer", "a[$(cat <<'EOF'\n1]\n"),
    "one-line opener closing the substitution": ("agreement-one-line-opener-closing-the-substitution", "x=$(: <<EOF)\n"),
}


class TestUnguardedDivergenceFixtureList:
    """The list is what the pins, the comparison and later suites read, so a dropped or mistyped entry must fail here."""

    def test_every_entry_is_a_member_or_an_agreement_case_and_the_two_filters_split_the_list(self):
        assert {fixture.kind for fixture in UNGUARDED_DIVERGENCE_FIXTURES} <= {MEMBER, AGREEMENT}
        assert len(UNGUARDED_DIVERGENCE_MEMBERS) + len(UNGUARDED_DIVERGENCE_AGREEMENT_CASES) == len(UNGUARDED_DIVERGENCE_FIXTURES)

    def test_ids_are_unique(self):
        ids = [fixture.id for fixture in UNGUARDED_DIVERGENCE_FIXTURES]
        assert len(ids) == len(set(ids))

    def test_the_ids_equal_the_named_expected_set(self):
        expected_agreement_ids = {agreement_id for agreement_id, _ in CONTAINER_CLOSER_PAIRS.values()} | {
            agreement_id for agreement_id, _ in FLUSH_COMMENT_BOUNDARY_FORMS.values()
        }
        assert {fixture.id for fixture in UNGUARDED_DIVERGENCE_MEMBERS} == EXPECTED_MEMBER_IDS
        assert {fixture.id for fixture in UNGUARDED_DIVERGENCE_AGREEMENT_CASES} == expected_agreement_ids
        assert len(UNGUARDED_DIVERGENCE_FIXTURES) == len(EXPECTED_MEMBER_IDS) + len(expected_agreement_ids)

    @pytest.mark.parametrize(
        ("agreement_id", "flush_comment_text"), FLUSH_COMMENT_BOUNDARY_FORMS.values(), ids=FLUSH_COMMENT_BOUNDARY_FORMS.keys()
    )
    def test_each_flush_comment_boundary_form_has_an_agreement_case_holding_it(self, agreement_id, flush_comment_text):
        matching_cases = [case for case in UNGUARDED_DIVERGENCE_AGREEMENT_CASES if case.id == agreement_id]
        assert len(matching_cases) == 1
        assert flush_comment_text in matching_cases[0].command
        assert matching_cases[0].bash_command.endswith("\n")
        assert "w git commit" in matching_cases[0].bash_command

    @pytest.mark.parametrize(
        ("agreement_id", "container_and_closer_text"), CONTAINER_CLOSER_PAIRS.values(), ids=CONTAINER_CLOSER_PAIRS.keys()
    )
    def test_each_container_and_closer_pair_has_an_agreement_case_holding_it(self, agreement_id, container_and_closer_text):
        matching_cases = [case for case in UNGUARDED_DIVERGENCE_AGREEMENT_CASES if case.id == agreement_id]
        assert len(matching_cases) == 1
        assert container_and_closer_text in matching_cases[0].command
        assert container_and_closer_text in matching_cases[0].bash_command

    @pytest.mark.parametrize(
        "fixture", UNGUARDED_DIVERGENCE_FIXTURES, ids=[fixture.id for fixture in UNGUARDED_DIVERGENCE_FIXTURES]
    )
    def test_each_entry_states_an_outcome_valid_for_its_kind_and_the_builds_it_was_seen_on(self, fixture):
        allowed_outcomes = MEMBER_OUTCOMES if fixture.kind == MEMBER else {AGREES}
        assert fixture.outcome in allowed_outcomes
        assert fixture.seen_on.strip() != ""
        assert (fixture.bash_command is not None) == (fixture.kind == AGREEMENT)


class TestUnguardedDivergenceMembersAsShfmtReadsThem:
    """Pins shfmt's reading of each member on CI's build, with no bash involved."""

    @pytest.mark.parametrize("member", UNGUARDED_DIVERGENCE_MEMBERS, ids=[member.id for member in UNGUARDED_DIVERGENCE_MEMBERS])
    def test_member_projects_to_its_stated_outcome(self, member):
        commands = simple_commands(member.command)
        words = [word for command_words in commands for word in command_words]
        if member.outcome == HIDDEN:
            assert FLAG_WORD not in words
            assert PATH_WORD not in words
            if member.visible_head_words:
                assert any(set(member.visible_head_words) <= set(command_words) for command_words in commands), commands
            if member.unflushed_twin is not None:
                twin_commands = simple_commands(member.unflushed_twin)
                assert any(holds_flag_and_path(command_words) for command_words in twin_commands)
        elif member.outcome == SHOWN:
            assert any(holds_flag_and_path(command_words) for command_words in commands)
        else:
            assert member.outcome == RENAMED_FLAG
            assert FLAG_WORD not in words
            assert any("-$F" in command_words and PATH_WORD in command_words for command_words in commands)


# Records each call to `git` as its NUL-terminated arguments on stderr, which a substitution does not capture.
# `cat` waits for a process substitution's subshell to finish, so its call is not lost when the script ends.
# `bash` stands in for a nested shell that reads its commands from standard input, since the PATH holds no bash.
BASH_GIT_CALL_TRACER = (
    "git() { printf '%s\\0' \"$@\" >&2; printf '\\n' >&2; }\n"
    "cat() { local drained; if [ -n \"${1-}\" ]; then read -r -d '' drained < \"$1\" || true; fi; }\n"
    "bash() { local script; read -r -d '' script || true; eval \"$script\"; }\n"
)
FLUSH_COMMENT_MEMBERS = [member for member in UNGUARDED_DIVERGENCE_MEMBERS if member.id.startswith("flush-comment-")]


def _git_calls_bash_makes(script: str) -> tuple[list[list[str]], int]:
    """The `git` calls real bash makes while running `script`, and its exit status."""
    result = run_real_bash(BASH_GIT_CALL_TRACER + script, isolated=True, check=False)
    calls = [
        [argument.decode() for argument in line.split(b"\0")[:-1]]
        for line in result.stderr.split(b"\n")
        if b"\0" in line
    ]
    return calls, result.returncode


def _makes_the_flag_and_path_call(calls: list[list[str]]) -> bool:
    return any(holds_flag_and_path(call) for call in calls)


class TestFlushCommentMembersDifferFromTheirSpacedFormOnBash:
    """Keeps each pin a record of a divergence: bash reads a flush `#` as part of the word, and a spaced one as a comment.

    A failure on a new entry means the entry is wrong, not the module.
    """

    @pytest.mark.parametrize("member", FLUSH_COMMENT_MEMBERS, ids=[member.id for member in FLUSH_COMMENT_MEMBERS])
    def test_bash_runs_the_flag_and_path_the_flush_form_hides_and_not_the_spaced_form(self, member):
        flush_calls, _ = _git_calls_bash_makes(member.command)
        spaced_calls, spaced_status = _git_calls_bash_makes(member.command.replace("# ", " # "))
        assert _makes_the_flag_and_path_call(flush_calls), (real_bash_version_line(), flush_calls)
        assert spaced_status == 0, (real_bash_version_line(), spaced_status)
        assert not any(FLAG_WORD in call for call in spaced_calls), (real_bash_version_line(), spaced_calls)
        if member.visible_head_words:
            visible_call = [call for call in spaced_calls if {"commit", "-m"} <= set(call)]
            assert visible_call, (real_bash_version_line(), spaced_calls)

    def test_the_list_holds_the_ten_flush_members(self):
        assert len(FLUSH_COMMENT_MEMBERS) == 10


# Members whose bash side no case runs: the extglob member needs bash 5.3's `${ }` form, and the one fed to `make`
# runs in another program. Their bash side rests on the builds their `seen_on` entries name.
# Each fixture's text is still checked to hold the shared flag-and-path line, so a fixture edited to hold nothing fails.
MEMBERS_BASH_IS_NOT_RUN_ON = frozenset(
    {"extglob-pattern-holding-a-brace-substitution", "stdin-fed-to-an-interpreter-that-is-not-a-shell"}
)
# The SHOWN members, which hide no line from the module. Bash reads the first one's body as literal text.
# The trailing-comment one differs in grouping: shfmt puts both lines in one command and bash runs two, which its own case checks.
# The RENAMED_FLAG members stay in the checked set, since bash makes the call.
MEMBERS_WITHOUT_A_HIDDEN_LINE_FOR_BASH = frozenset(
    {"delimiter-mismatch-delimiter-quoted-in-a-non-last-part", "backslash-newline-trailing-comment-ending-in-a-backslash"}
)
BASH_RUN_MEMBERS = [
    member
    for member in UNGUARDED_DIVERGENCE_MEMBERS
    if not member.id.startswith("flush-comment-")
    and member.id not in MEMBERS_BASH_IS_NOT_RUN_ON
    and member.id not in MEMBERS_WITHOUT_A_HIDDEN_LINE_FOR_BASH
]


class TestOtherMembersAreDivergencesOnBash:
    """Keeps each pin a record of a divergence for the members whose text bash runs directly.

    A failure on a new entry means the entry is wrong, not the module.
    """

    @pytest.mark.parametrize("member", BASH_RUN_MEMBERS, ids=[member.id for member in BASH_RUN_MEMBERS])
    def test_bash_makes_the_flag_and_path_call_the_module_hides(self, member):
        calls, _ = _git_calls_bash_makes(member.command)
        assert _makes_the_flag_and_path_call(calls), (real_bash_version_line(), calls)

    @pytest.mark.parametrize("member_id", sorted(MEMBERS_BASH_IS_NOT_RUN_ON))
    def test_the_fixture_of_a_member_bash_is_not_run_on_holds_the_flag_and_path_line(self, member_id):
        member = next(m for m in UNGUARDED_DIVERGENCE_MEMBERS if m.id == member_id)
        assert FLAG_AND_PATH in member.command

    def test_the_trailing_comment_member_is_one_command_for_the_module_and_two_for_bash(self):
        member = next(
            m for m in UNGUARDED_DIVERGENCE_MEMBERS if m.id == "backslash-newline-trailing-comment-ending-in-a-backslash"
        )
        module_commands = [
            command_words
            for command_words in simple_commands(member.command)
            if holds_flag_and_path(command_words)
        ]
        assert [command_words[0] for command_words in module_commands] == list(member.visible_head_words)
        bash_calls, _ = _git_calls_bash_makes(member.command)
        assert _makes_the_flag_and_path_call(bash_calls), (real_bash_version_line(), bash_calls)

    def test_bash_makes_no_such_call_for_the_member_it_reads_as_literal_text(self):
        member = next(m for m in UNGUARDED_DIVERGENCE_MEMBERS if m.id == "delimiter-mismatch-delimiter-quoted-in-a-non-last-part")
        calls, status = _git_calls_bash_makes(member.command)
        assert status == 0, (real_bash_version_line(), status)
        assert not _makes_the_flag_and_path_call(calls), (real_bash_version_line(), calls)

    def test_bash_makes_the_call_when_the_delimiter_has_no_quoted_part(self):
        """The control for the case above: the same body under an unquoted delimiter is expanded, so bash does run the call."""
        member = next(m for m in UNGUARDED_DIVERGENCE_MEMBERS if m.id == "delimiter-mismatch-delimiter-quoted-in-a-non-last-part")
        unquoted_delimiter_text = member.command.replace('<<E"O"F', "<<EOF")
        assert unquoted_delimiter_text != member.command
        calls, status = _git_calls_bash_makes(unquoted_delimiter_text)
        assert status == 0, (real_bash_version_line(), status)
        assert _makes_the_flag_and_path_call(calls), (real_bash_version_line(), calls)


class TestSameLineCaseControl:
    """The flush `#` is the cause of the flush-comment class: on one line it also makes shfmt reject the command."""

    COMMAND = 'case x in x) git commit -m "x"# -F /dirty.md ;; esac'
    NO_HASH_TWIN = 'case x in x) git commit -m "x" -F /dirty.md ;; esac'

    def test_the_command_makes_shfmt_exit_1(self):
        parsed = run_shfmt(self.COMMAND)
        assert parsed.returncode == 1, shfmt_exit_note(parsed)

    def test_the_twin_without_the_hash_exits_0_and_projects_the_flag_and_path_in_one_command(self):
        commands = simple_commands(self.NO_HASH_TWIN)
        assert any(holds_flag_and_path(command_words) for command_words in commands)


class TestContinuationBeforeDollarOrHash:
    """Bash joins `$`, a backslash-newline and `$` or `#` into `$$` or `$#` and expands it. The module keeps both characters."""

    def test_the_joined_special_parameters_stay_as_written(self):
        assert simple_commands("echo $\\\n$ x $\\\n# y") == [["echo", "$$", "x", "$#", "y"]]


class TestExtGlobPatternBoundary:
    """A parameter expansion in an extglob pattern stays outside the strict check's substitution markers."""

    @pytest.mark.parametrize(
        "command", ["[[ x == @($x|b) ]]", "[[ x == @(${x}|b) ]]"], ids=["parameter", "braced-parameter"]
    )
    def test_a_parameter_expansion_in_the_pattern_exits_0(self, command):
        projected = project_words(command)
        assert projected.returncode == 0, projected.stderr
