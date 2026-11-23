"""Hold every documented `config-set.sh` command valid, and keep appends out of the docs.

Corpus: README.md, every docs/**/*.md outside docs/design-decisions/, and every
claude/.claude/hooks/*.sh.

A site is the literal `~/.claude/scripts/config-set.sh`, a key word and a value word on
one line. The value word is the longest run of characters other than whitespace, a
backtick, `)` and `"`, with a single-quoted span taken whole, so each embedding form
(bare line, `! ` shell escape, inline code, `Bash(...)`, bash string) ends the word
where its own markup ends. Prose that names the script without both words, and a
placeholder such as `<key> <value>`, is not a site.

Four rules run over the corpus:
1. Valid: the key is a schema key and the key's type accepts the value, judged by
   `_config.sh`'s own functions in one bash subprocess. Doc-derived words reach it
   only as positional arguments, never as script text.
2. Ask-matched: a permissive command of an enforcement-critical key equals the command
   inside one `Bash(...)` entry of `permissions.ask` in claude/.claude/settings.json.
   This checks the command text only. The literal may start the line after optional
   indentation, follow `! ` at the start of the line (the engineer's own shell escape,
   which never reaches the Bash tool, per docs/config-file.md), follow a backtick or
   `Bash(`, or follow `: ` inside a double-quoted shell assignment (the commit-stall
   hook's reason text). The command ends at the end of the line, a backtick, `)` or `"`.
   Any other prefix directly before the literal at line start, after `! ` or after `: `
   is reported, including `bash`, `eval`, `time`, `sudo`, an environment assignment and
   markdown prose. Whether the harness matches a prefixed spelling against the
   `Bash(...)` ask entry is unverified.
3. No append: no line appends (`>>` or `tee -a`) to a file named `claude-config.toml`.
4. Coverage: each file in `EXPECTED_SITES` carries exactly the (key, value word) pairs
   listed there. A repeated line may go. A pair lost, retargeted or added is reported by
   file name.

Not seen:
- a command split across lines, another path form for the script, and a double-quoted
  value
- a key word written other than lowercase snake_case (kebab-case, uppercase, `key=value`,
  or after a flag)
- a tab or non-breaking space between words
- `tee --append`, `tee -ai` and other combined or separated `tee` flag forms
- an append target held in a variable, or a path holding a space
- `tee -a <other-file> <target>`, where the target is a later operand
- `>>` with the target on the next line
- a prefix before a backtick or `Bash(` lead-in, a command on a continuation line (a line
  ending in a backslash, such as one after a `sudo` line), and any quote-free text inside
  the quotes before `: ` in the colon-assignment form

Skills, plugins, agents, rules, claude/.claude/scripts/, install.sh and CLAUDE.md files
are outside the corpus.
"""
from __future__ import annotations

import json
import re
import shlex
import subprocess
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import pytest
from helpers import CLAUDE_DIR, REPO_ROOT

CONFIG_SH_PATH = CLAUDE_DIR / "hooks" / "_config.sh"
SETTINGS_PATH = CLAUDE_DIR / "settings.json"

SETTER_LITERAL = "~/.claude/scripts/config-set.sh"
_SITE_PATTERN = re.compile(
    re.escape(SETTER_LITERAL) + r" +([a-z][a-z0-9_]*) +((?:'[^']*'|[^\s`)\"])+)"
)
# What may precede the literal, and what may follow the value word, for the site to be
# the whole command of a `permissions.ask` entry rather than a fragment of a longer one.
_COMMAND_START_PATTERN = re.compile(r'(?:^\s*(?:! )?|`|Bash\(|^\s*[A-Za-z_][A-Za-z0-9_]*="[^"]*: )$')
_COMMAND_END_PATTERN = re.compile(r"(?:$|[`)\"])")
_TRAILING_WORD_PATTERN = re.compile(r"^ +[^\s`)\"]")
_APPEND_PATTERN = re.compile(r"(?:>>|\btee[ \t]+-a)[ \t]*(\S+)")
_CONFIG_FILE_NAME = "claude-config.toml"

# Each covered path maps to the (key, value word) pairs its sites carry.
EXPECTED_SITES: dict[str, frozenset[tuple[str, str]]] = {
    "README.md": frozenset(
        {("worktree_required", "true"), ("pr_cost_disclosure", "dollars"), ("cost_ledger_recording", "true")}
    ),
    "docs/commit-stall-block.md": frozenset({("commit_stall_block", "false"), ("commit_stall_block", "true")}),
    "docs/error-mode-nudge.md": frozenset({("error_mode_nudge", "true"), ("error_mode_nudge", "false")}),
    "docs/handoff-nudge.md": frozenset({("handoff_nudge", "false"), ("handoff_nudge", "true")}),
    "docs/memory-audit-nudge.md": frozenset({("memory_audit_nudge", "false"), ("memory_audit_nudge", "true")}),
    "docs/permission-prompt-tracking.md": frozenset(
        {("permission_prompt_tracking", "true"), ("permission_prompt_tracking", "false")}
    ),
    "claude/.claude/hooks/advance-past-commit-stall.sh": frozenset({("commit_stall_block", "false")}),
}

# Fixed script text. Doc-derived words follow it as arguments ($1 is _config.sh, then
# key and value pairs), so none is ever evaluated as shell.
_RULE_QUERY_SCRIPT = r"""
source "$1" || exit 3
shift
for critical_key in $_CONFIG_ENFORCEMENT_CRITICAL_KEYS; do
  _config_enforcement_critical_safe_value "$critical_key" || exit 4
  printf 'critical %s %s\n' "$critical_key" "$_CONFIG_SAFE_VALUE"
done
while [ "$#" -ge 2 ]; do
  if ! key_type=$(_config_schema_field "$1" type 2>/dev/null); then
    printf 'site unknown-key\n'
  elif _config_type_accepts "$key_type" "$2"; then
    printf 'site ok\n'
  else
    printf 'site bad-value\n'
  fi
  shift 2
done
"""


@dataclass(frozen=True)
class Site:
    path: str
    line_number: int
    key: str
    value_word: str
    command: str
    before: str
    after: str

    @property
    def where(self) -> str:
        return f"{self.path}:{self.line_number}"


def find_sites(path: str, text: str) -> list[Site]:
    sites = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for match in _SITE_PATTERN.finditer(line):
            sites.append(
                Site(
                    path=path,
                    line_number=line_number,
                    key=match.group(1),
                    value_word=match.group(2),
                    command=match.group(0),
                    before=line[: match.start()],
                    after=line[match.end() :],
                )
            )
    return sites


def read_value_word(site: Site) -> str | None:
    """Return the value word with its quoting removed, or None when shlex rejects it."""
    try:
        return shlex.split(site.value_word)[0]
    except ValueError:
        return None


def query_config_sh(pairs: list[tuple[str, str]]) -> tuple[dict[str, str], list[str]]:
    """Return ({critical key: safe value}, one verdict per pair) from `_config.sh` itself."""
    pair_words = [word for pair in pairs for word in pair]
    result = subprocess.run(
        ["bash", "-c", _RULE_QUERY_SCRIPT, "config-set-doc-call-sites", str(CONFIG_SH_PATH), *pair_words],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"bash query failed ({result.returncode}): {result.stderr!r}"
    safe_values: dict[str, str] = {}
    verdicts: list[str] = []
    for output_line in result.stdout.splitlines():
        kind, _, rest = output_line.partition(" ")
        if kind == "critical":
            critical_key, safe_value = rest.split(" ")
            safe_values[critical_key] = safe_value
        else:
            verdicts.append(rest)
    assert safe_values, "bash query printed no enforcement-critical keys, so rule 2 would pass vacuously"
    return safe_values, verdicts


def check_valid(sites: list[Site]) -> list[str]:
    problems = []
    readable: list[tuple[Site, str]] = []
    for site in sites:
        if _TRAILING_WORD_PATTERN.match(site.after):
            problems.append(f"{site.where}: a bare word follows the value, but config-set.sh takes two arguments")
        value = read_value_word(site)
        if value is None:
            problems.append(f"{site.where}: value word {site.value_word!r} does not read as one shell word")
        else:
            readable.append((site, value))
    _, verdicts = query_config_sh([(site.key, value) for site, value in readable])
    for (site, value), verdict in zip(readable, verdicts, strict=True):
        if verdict != "ok":
            problems.append(f"{site.where}: {site.key} {value!r} is {verdict}")
    return problems


def ask_commands() -> frozenset[str]:
    entries = json.loads(SETTINGS_PATH.read_text())["permissions"]["ask"]
    return frozenset(m.group(1) for entry in entries if (m := re.fullmatch(r"Bash\((.*)\)", entry)))


def check_ask_matched(sites: list[Site], asked: frozenset[str] | None = None) -> list[str]:
    safe_values, _ = query_config_sh([])
    if asked is None:
        asked = ask_commands()
    problems = []
    for site in sites:
        if site.key not in safe_values or read_value_word(site) == safe_values[site.key]:
            continue
        starts_command = _COMMAND_START_PATTERN.search(site.before)
        ends_command = _COMMAND_END_PATTERN.match(site.after)
        if not (starts_command and ends_command and site.command in asked):
            problems.append(
                f"{site.where}: permissive command {site.command!r} is not exactly a "
                "`Bash(...)` entry of permissions.ask"
            )
    return problems


def check_no_append(path: str, text: str) -> list[str]:
    problems = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for match in _APPEND_PATTERN.finditer(line):
            target = match.group(1).rstrip("\"'\\`),.;")
            if target.endswith(_CONFIG_FILE_NAME):
                problems.append(f"{path}:{line_number}: appends to {_CONFIG_FILE_NAME}")
    return problems


def check_coverage(sites: list[Site]) -> list[str]:
    problems = []
    for path, expected in EXPECTED_SITES.items():
        found = {(site.key, site.value_word) for site in sites if site.path == path}
        if not found:
            problems.append(f"{path}: carries no config-set.sh site")
            continue
        problems.extend(f"{path}: expected site {key} {value} is missing" for key, value in sorted(expected - found))
        problems.extend(f"{path}: unexpected site {key} {value}" for key, value in sorted(found - expected))
    return problems


def corpus_paths() -> list[Path]:
    design_decisions_dir = REPO_ROOT / "docs" / "design-decisions"
    docs = [p for p in (REPO_ROOT / "docs").rglob("*.md") if design_decisions_dir not in p.parents]
    hooks = (REPO_ROOT / "claude/.claude/hooks").glob("*.sh")
    return sorted([REPO_ROOT / "README.md", *docs, *hooks])


@cache
def corpus_texts() -> dict[str, str]:
    return {str(path.relative_to(REPO_ROOT)): path.read_text() for path in corpus_paths()}


@cache
def corpus_sites() -> list[Site]:
    return [site for path, text in corpus_texts().items() for site in find_sites(path, text)]


ASK_LISTED_PERMISSIVE_COMMAND = f"{SETTER_LITERAL} commit_stall_block false"
# Stands in for settings.json's ask entries so the controls hold when that file changes.
ASKED_FIXTURE = frozenset({ASK_LISTED_PERMISSIVE_COMMAND})


def expected_site_lines(*, omitting: frozenset[str] = frozenset()) -> dict[str, str]:
    """Return, per covered path, text with one site line for each pair its entry expects."""
    return {
        path: "\n".join(f"{SETTER_LITERAL} {key} {value}" for key, value in sorted(pairs))
        for path, pairs in EXPECTED_SITES.items()
        if path not in omitting
    }


def sites_of(lines_by_path: dict[str, str]) -> list[Site]:
    return [site for path, text in lines_by_path.items() for site in find_sites(path, text)]


class TestCorpusRules:
    def test_corpus_holds_the_named_files_and_excludes_the_design_records(self):
        paths = set(corpus_texts())
        assert set(EXPECTED_SITES) <= paths
        assert not [path for path in paths if path.startswith("docs/design-decisions/")]
        assert "CHANGELOG.md" not in paths

    def test_every_site_names_a_schema_key_and_a_value_its_type_accepts(self):
        assert not check_valid(corpus_sites())

    def test_every_permissive_enforcement_critical_site_is_an_ask_entry(self):
        assert not check_ask_matched(corpus_sites())

    def test_no_line_appends_to_the_config_file(self):
        problems = [
            problem for path, text in corpus_texts().items() for problem in check_no_append(path, text)
        ]
        assert not problems

    def test_each_documented_file_carries_its_expected_sites(self):
        assert not check_coverage(corpus_sites())

    def test_setter_literal_names_the_script_in_the_repo(self):
        assert SETTER_LITERAL.startswith("~/.claude/")
        repo_script = CLAUDE_DIR / SETTER_LITERAL.removeprefix("~/.claude/")

        assert repo_script.is_file(), f"{SETTER_LITERAL} maps to {repo_script}, which does not exist"


class TestSiteGrammarControls:
    @pytest.mark.parametrize(
        "line",
        [
            pytest.param(ASK_LISTED_PERMISSIVE_COMMAND, id="bare-line"),
            pytest.param(f"    {ASK_LISTED_PERMISSIVE_COMMAND}", id="indented-bare-line"),
            pytest.param(f"! {ASK_LISTED_PERMISSIVE_COMMAND}", id="shell-escape-prefix"),
            pytest.param(f"`{ASK_LISTED_PERMISSIVE_COMMAND}`", id="inline-code"),
            pytest.param(f"Bash({ASK_LISTED_PERMISSIVE_COMMAND})", id="bash-permission-entry"),
            pytest.param(f'REASON="${{REASON}} to disable it: {ASK_LISTED_PERMISSIVE_COMMAND}"', id="bash-string"),
            pytest.param(
                f'  REASON="${{REASON}} (the command acts on the config dir `wrote`): {ASK_LISTED_PERMISSIVE_COMMAND}"',
                id="hook-reason-string",
            ),
        ],
    )
    def test_each_embedding_form_is_recognized_and_passes_rules_one_to_three(self, line):
        sites = find_sites("control", line)

        assert [(site.key, site.value_word) for site in sites] == [("commit_stall_block", "false")]
        assert not check_valid(sites)
        assert not check_ask_matched(sites, ASKED_FIXTURE)
        assert not check_no_append("control", line)

    @pytest.mark.parametrize(
        "line",
        [
            pytest.param("~/.claude/scripts/config-set.sh <key> <value>", id="placeholder"),
            pytest.param("Run ~/.claude/scripts/config-set.sh", id="bare-mention"),
            pytest.param("`~/.claude/scripts/config-set.sh` writes one key", id="mention-in-code-span"),
        ],
    )
    def test_prose_naming_the_script_is_not_a_site(self, line):
        assert find_sites("control", line) == []

    def test_single_quoted_value_reads_as_the_bare_word(self):
        sites = find_sites("control", f"{SETTER_LITERAL} pr_cost_disclosure 'dollars'")

        assert not check_valid(sites)


class TestValidRuleControls:
    @pytest.mark.parametrize(
        "line",
        [
            pytest.param(f"{SETTER_LITERAL} no_such_key false", id="unknown-key"),
            pytest.param(f"{SETTER_LITERAL} pr_cost_disclosure '\"dollars\"'", id="quoted-enum-literal"),
            pytest.param(f"{SETTER_LITERAL} handoff_nudge '$(echo false)'", id="command-substitution-stays-literal"),
            pytest.param(f"{SETTER_LITERAL} handoff_nudge 'false", id="unclosed-quote"),
        ],
    )
    def test_invalid_site_is_reported(self, line):
        assert len(check_valid(find_sites("control", line))) == 1

    def test_site_followed_by_a_third_bare_word_is_reported(self):
        sites = find_sites("control", f"{SETTER_LITERAL} handoff_nudge false extra")

        problems = check_valid(sites)

        assert len(problems) == 1
        assert sites[0].where in problems[0]

    @pytest.mark.parametrize(
        "line",
        [
            pytest.param(f"`{SETTER_LITERAL} handoff_nudge false` disables it", id="inline-code"),
            pytest.param(f"Bash({SETTER_LITERAL} handoff_nudge false)", id="bash-permission-entry"),
            pytest.param(f'REASON="run {SETTER_LITERAL} handoff_nudge false"', id="bash-string"),
        ],
    )
    def test_site_closed_by_its_own_markup_reports_no_trailing_word(self, line):
        assert not check_valid(find_sites("control", line))


class TestCoverageRuleControls:
    def test_file_without_a_site_is_reported_by_name(self):
        omitted_file = next(iter(EXPECTED_SITES))
        sites = sites_of(expected_site_lines(omitting=frozenset({omitted_file})))

        problems = check_coverage(sites)

        assert len(problems) == 1
        assert omitted_file in problems[0]

    def test_every_covered_file_carrying_its_expected_sites_reports_nothing(self):
        assert not check_coverage(sites_of(expected_site_lines()))

    def test_dropping_a_repeated_line_keeps_the_file_valid(self):
        lines_by_path = {path: f"{text}\n{text}" for path, text in expected_site_lines().items()}

        assert not check_coverage(sites_of(lines_by_path))

    def test_losing_a_unique_site_is_reported_by_file_and_pair(self):
        lines_by_path = expected_site_lines()
        lines_by_path["docs/handoff-nudge.md"] = f"{SETTER_LITERAL} handoff_nudge false"

        problems = check_coverage(sites_of(lines_by_path))

        assert len(problems) == 1
        assert "docs/handoff-nudge.md" in problems[0]
        assert "handoff_nudge true" in problems[0]

    def test_retargeting_a_site_to_another_key_is_reported_by_file(self):
        lines_by_path = expected_site_lines()
        lines_by_path["docs/error-mode-nudge.md"] = (
            f"{SETTER_LITERAL} error_mode_nudge true\n{SETTER_LITERAL} handoff_nudge false"
        )

        problems = check_coverage(sites_of(lines_by_path))

        assert len(problems) == 2
        assert all("docs/error-mode-nudge.md" in problem for problem in problems)

    def test_site_that_stops_matching_the_grammar_is_reported_by_file(self):
        lines_by_path = expected_site_lines()
        lines_by_path["README.md"] = lines_by_path["README.md"].replace(
            "~/.claude/scripts/config-set.sh worktree_required", "~/.claude/script/config-set.sh worktree_required"
        )

        problems = check_coverage(sites_of(lines_by_path))

        assert len(problems) == 1
        assert "README.md" in problems[0]
        assert "worktree_required true" in problems[0]


class TestAskMatchedRuleControls:
    @pytest.mark.parametrize(
        "line",
        [
            pytest.param(f"bash {ASK_LISTED_PERMISSIVE_COMMAND}", id="bash-prefix"),
            pytest.param(f"echo x; {ASK_LISTED_PERMISSIVE_COMMAND}", id="command-list-prefix"),
            pytest.param(f"eval ! {ASK_LISTED_PERMISSIVE_COMMAND}", id="eval-then-exclamation-mark"),
            pytest.param(f"time ! {ASK_LISTED_PERMISSIVE_COMMAND}", id="time-then-exclamation-mark"),
            pytest.param(f"sudo -u root : {ASK_LISTED_PERMISSIVE_COMMAND}", id="sudo-then-colon"),
            pytest.param(f"Note: {ASK_LISTED_PERMISSIVE_COMMAND}", id="markdown-prose-colon"),
            pytest.param(f"CLAUDE_CONFIG_DIR=/x {ASK_LISTED_PERMISSIVE_COMMAND}", id="env-prefix"),
            pytest.param(f"{SETTER_LITERAL}  commit_stall_block false", id="doubled-space"),
            pytest.param(f"{ASK_LISTED_PERMISSIVE_COMMAND} 2>/dev/null", id="redirect-suffix"),
        ],
    )
    def test_permissive_command_that_is_not_an_ask_entry_is_reported(self, line):
        assert len(check_ask_matched(find_sites("control", line), ASKED_FIXTURE)) == 1

    def test_safe_value_of_a_critical_key_needs_no_ask_entry(self):
        sites = find_sites("control", f"bash {SETTER_LITERAL} commit_stall_block true")

        assert not check_ask_matched(sites, ASKED_FIXTURE)

    def test_quoted_safe_value_of_a_critical_key_needs_no_ask_entry(self):
        sites = find_sites("control", f"{SETTER_LITERAL} commit_stall_block 'true'")

        assert not check_ask_matched(sites, frozenset())

    def test_permissive_value_of_a_non_critical_key_needs_no_ask_entry(self):
        sites = find_sites("control", f"{SETTER_LITERAL} handoff_nudge false")

        assert not check_ask_matched(sites, ASKED_FIXTURE)


class TestNoAppendRuleControls:
    @pytest.mark.parametrize(
        "line",
        [
            pytest.param(
                "printf '\\nhandoff_nudge = false\\n' >> \"${CLAUDE_CONFIG_DIR:-$HOME/.claude}/claude-config.toml\"",
                id="doc-one-liner",
            ),
            pytest.param(
                'REASON="x: printf \'...\' >> \\"$CONFIG_DIR/claude-config.toml\\""',
                id="hook-escaped-quotes",
            ),
            pytest.param('echo x | tee -a "$CONFIG_DIR/claude-config.toml"', id="tee-append"),
            pytest.param('echo x >>"$CONFIG_DIR/claude-config.toml"', id="no-space-redirect"),
            pytest.param("echo x >> '$CONFIG_DIR/claude-config.toml'", id="single-quoted-target"),
            pytest.param("echo x >> $CONFIG_DIR/claude-config.toml;", id="target-then-semicolon"),
            pytest.param("echo x >> $CONFIG_DIR/claude-config.toml, then", id="target-then-comma"),
            pytest.param("echo x >> $CONFIG_DIR/claude-config.toml.", id="target-then-period"),
            pytest.param(
                "- **Kill-switch** (`printf '\\nhandoff_nudge = false\\n' >> "
                '"${CLAUDE_CONFIG_DIR:-$HOME/.claude}/claude-config.toml"`) — suppresses every future fire',
                id="inline-code-span-in-parentheses",
            ),
        ],
    )
    def test_append_to_the_config_file_is_reported(self, line):
        assert len(check_no_append("control", line)) == 1

    @pytest.mark.parametrize(
        "line",
        [
            pytest.param("A Bash append such as `>>` onto `claude-config.toml` is not gated.", id="prose-mention"),
            pytest.param("echo x >> .gitignore", id="other-file"),
            pytest.param('echo x >> "$LOG_FILE"', id="variable-target"),
        ],
    )
    def test_other_redirects_and_prose_are_not_reported(self, line):
        assert not check_no_append("control", line)
