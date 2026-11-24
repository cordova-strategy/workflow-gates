# Helper-library naming rule for hooks directories

## Context

Make a new `_`-prefixed `.sh` helper library in a hooks directory pass CI without editing any per-test registry, by replacing the exact-name list `_HELPER_LIBRARY_NAMES` with one shared naming-rule predicate and pairing it with an invariant that stops a real hook from exempting itself by filename.

Ask: GH-1434, "Widen _HELPER_LIBRARY_NAMES to a naming rule so a third hooks-directory helper passes CI" (sub-issue of GH-1117).

**Problem.** `claude/.claude/hooks/tests/test_hook_alignment.py` identifies helper libraries by the exact two-name set `{"_lib.sh", "_config.sh"}`. A third helper library in a hooks directory is treated as a hook, so it fails the `docs/hooks.md` entry check, the `# hook-class:` header check, and `test_lib_source_hooks_exhaustive`. Several other registries hard-code the same two names: the liveness test, `build_isolated_hook` and `symlink_hooks_lib_chain` in `claude/.claude/tests/helpers.py`, and `test_lib_session_identity.py`. `.claude/rules/bash-unit-test-seams.md` therefore tells contributors to land hook-side extractions in `_lib.sh` until the guard is widened.

**Why now.** GH-1434 is a prerequisite for the resume-continuity pilot (GH-1436), which adds a consumer-sourced sibling library with a source-time dependency check. The liveness probe sources each library alone, so that sibling would fail it today.

**Intended outcome.** The issue's "Done when": a new `_<topic>-lib.sh` in the hooks directory, sourced by one hook or script, passes CI with no edit to any registry file other than the shared predicate. The issue's six scope items define the work:

1. Replace the name list with the rule "a `.sh` file in a hooks directory whose name starts with `_` is a helper library", covering `claude/.claude/hooks/` and `plugins/*/hooks/`.
2. Route every registry that names the libraries through one shared predicate.
3. Make the liveness probe source `_lib.sh` first, so a sibling with a source-time dependency check passes.
4. Keep `test_all_hooks_and_libs_includes_every_lib_sh` passing alongside other helpers.
5. Add the paired invariant: every `_`-prefixed file is sourced by at least one hook or script, and is registered as no hook's command, including in `plugins/*/hooks/hooks.json`.
6. Rewrite the "fails CI today" paragraph of `.claude/rules/bash-unit-test-seams.md`. GH-1436 owns that file's preference list and its "Already-seamed libs" list.

**Risk the issue names.** After widening, a real hook named with a leading `_` could exempt itself from the hook checks by filename alone. The invariant in item 5 guards against it.

## Approach

Add one predicate, `is_helper_library`, to `claude/.claude/tests/helpers.py`, and route every registry that names the libraries through it, except the session-identity filter the engineer chose to keep (row 23). Any `_`-prefixed `.sh` file in a hooks directory is then a helper library, with no per-test edit. Pair the rule with two checks. Every helper library must be sourced by another shipped shell file of its own tree, and no hook config may register one as a command. The liveness probe sources `_lib.sh` before each other library. Seeded permanent tests pin each behavior that only a third library would otherwise exercise.

**Predicate.** Two functions go in `helpers.py` beside `_hook_class`, because every consumer already imports from it. That includes `claude/.claude/scripts/tests/test_cursor_adapter_translate.py` and `helpers.py`'s own isolated-hook builders.
- `is_helper_library(file_name: str) -> bool` is true for a name that starts with `_` and ends in `.sh`. It takes a bare file name, because the registered half holds only the name `_hook_command_script_name` returns (row 32). Every path caller passes `path.name`.
- `helper_libraries(hooks_dir: Path) -> list[Path]` returns the sorted helper libraries directly in `hooks_dir`.
- The prescribed predicate docstring is: "A `_`-prefixed `.sh` file in a hooks directory is a sourced helper library, not a hook."

On today's tree the predicate selects exactly the six files `_HELPER_LIBRARY_NAMES` excludes now (row 1). Every derived collection below is therefore unchanged, except where stated.

**Predicate tests**, in a new `claude/.claude/tests/test_helper_library_rule.py`, beside the other `helpers.py` self-tests. It imports `helpers` as a module, as `test_installed_locale_finder.py:5` does.
- `test_is_helper_library` has seven rows. It is true for `_lib.sh`, `_config.sh` and `_topic-lib.sh`, and false for `hook.sh`, `__init__.py`, `_x.py` and `_x.sh.bak`.
- `test_helper_libraries_lists_direct_helper_libraries_sorted` seeds `_b.sh`, `_a.sh`, `hook.sh`, `__init__.py`, `_x.sh.bak` and `nested/_c.sh` under `tmp_path`. It expects exactly `[_a.sh, _b.sh]`.
- The two builder tests in this file are under "Isolated-hook builders" below.

**Hook checks in `claude/.claude/hooks/tests/test_hook_alignment.py`** (cited as T below).
- Delete `_HELPER_LIBRARY_NAMES` and its comment (T:102-105).
- `_all_hook_files` takes `include_helper_libraries` in place of `include_lib`. Off, it drops every file whose name `is_helper_library` accepts. On, it drops nothing.
- `_all_hook_files` keeps its name, which two design-decision docs cite (row 2).
- `ALL_HOOKS`, `_MAIN_HOOKS`, `GATE_HOOKS`, `_LIB_SOURCE_HOOKS`, and every test parametrized over them stay unchanged on today's tree.
- `ALL_HOOKS_AND_LIBS` now also holds `_config.sh`. That adds one passing case to `test_no_gnu_backslash_s_regex_extension` (row 3). `_PIPE_LINT_FILES` and its comment (T:1403-1405) go. `test_no_pipe_into_early_exit_grep` parametrizes over `ALL_HOOKS_AND_LIBS` directly, with the same ids.
- `test_all_hooks_and_libs_includes_every_lib_sh` keeps its name and its one-`_lib.sh`-per-hooks-directory assertion. Its `len(ALL_HOOKS) + expected_lib_count` equality becomes a set equality: `set(ALL_HOOKS_AND_LIBS)` equals `set(ALL_HOOKS)` joined with every path `helper_libraries(d)` returns, for the main and each plugin hooks directory. It fails if the include-on branch drops a real hook or adds a non-hook file. A third helper library passes it.
- Rewrite `_all_hook_files`'s docstring to the facts that still hold:
  - Only the `\s` and early-exit-grep detectors opt in.
  - The bare-xargs check stays off helper libraries, because `_lib.sh` holds status-checked `xargs -n1` sites in `_lib_command_words` and `_lib_commit_fragment_has_worktree_target`.
  - The bare-jq and inline-matcher checks stay off helper libraries, because `_lib.sh` defines the primitive each one detects.

  Drop the `_config.sh` count rationale, which no longer applies.
- Several docstrings name the pair as the exclusion set; change each to "helper library":
  - The module docstring (T:3-4, T:6-7, T:29-36, T:51-55). Add one Layer 1 bullet: no hook config registers a helper library as a command.
  - T:1289-1295, T:1414, T:1637-1638, and T:1842. At T:1842, `ALL_HOOKS` excludes every helper library, not only `_lib.sh`.

**Paired invariant, sourced half**, in a new module `claude/.claude/hooks/tests/test_helper_library_sourcing.py` (cited as S below). T is a recorded split-pending size offender (row 27), so these tests start outside it. `select-tests.py` already selects S for every change that could add a sourcer (row 12).
- `_HELPER_LIBRARIES` holds the repo-relative path of each `ALL_HOOKS_AND_LIBS` entry whose name `is_helper_library` accepts. S imports `ALL_HOOKS_AND_LIBS` from T, so the hooks-directory set keeps one home.
- `_sources_helper_library(sourcer, text, library)` takes the two repo-relative paths and the sourcer's text. It returns true when all four conditions hold:
  1. The sourcer is not the library.
  2. Both sit in the same tree: the same `plugins/<name>/` directory, or both outside `plugins/` (G1).
  3. A line of the sourcer is a source statement for the library's name. The shape is optional leading whitespace, an optional `if ! `, then `.` or `source`, then a double-quoted operand ending `/<name>"`. The intended matcher is `^\s*(?:if\s+!\s+)?(?:\.|source)\s+"(?P<directory>.*)/(?P<name>_[\w.-]+\.sh)"`.
  4. The operand's directory part ends in a `/hooks` segment. Or the sourcer sits in the library's own directory, and the directory part is one of `${0%/*}`, `$(dirname "$0")`, `$(dirname "${BASH_SOURCE[0]}")`.
- Two further rules fix which files count as sourcers:
  - Another helper library counts, so `_config.sh` passes on `_lib.sh:25` alone.
  - A file under a `tests` segment never counts, because `_shipped_shell_files()` excludes it.
- `_unsourced_helper_libraries(libraries, texts)` returns, in order, each library that no entry of the path-to-text mapping `texts` sources.
- `test_every_helper_library_is_sourced_by_a_shipped_shell_file` is parametrized over `_HELPER_LIBRARIES`, with the paths as ids. It asserts that `_unsourced_helper_libraries([library], texts)` is empty. `texts` maps each `_shipped_shell_files()` path to its `_read_text` content. A `functools.cache` function builds it, and the test body calls that function, so importing S runs no subprocess and reads no file. Import both functions from `test_shell_dialect.py`, as `test_bash_floor.py:39` imports the first.

Every source shape in use today meets the four conditions (rows 7, 8).

The failure message names the library and lists the accepted shapes. From the library's own directory, those are `${0%/*}`, `$(dirname "$0")` and `$(dirname "${BASH_SOURCE[0]}")`. From anywhere in its tree, the shape is a double-quoted operand whose directory part ends in `/hooks`. The message says that a sourcer file not yet `git add`ed is not scanned (row 9). It ends by telling the contributor to drop the leading `_` if the file is a hook.

S's controls:
- `test_sources_helper_library_control_table` pins `_sources_helper_library` with nine synthetic rows. These forms count:
  - the same-directory `${0%/*}` form;
  - the scripts-side `$(dirname "$0")/../hooks/` form;
  - `install.sh`'s `$REPO_DIR/claude/.claude/hooks/` form;
  - the plugin `${CLAUDE_PLUGIN_ROOT}/hooks/` form.

  These do not count:
  - a plugin sourcer for a main library;
  - a sourcer in a different plugin;
  - a scripts-directory same-directory source of a same-named library;
  - a comment line;
  - the library sourcing itself.
- `test_unsourced_helper_libraries_control` has two rows over a seeded corpus for `claude/.claude/hooks/_topic-lib.sh`. In `sourced`, a hook in the same directory sources it, and the result is empty. In `unsourced`, that hook names it only in a comment, and the result is the library.
- `test_helper_libraries_include_lib_sh_and_config_sh` asserts that `_HELPER_LIBRARIES` holds `claude/.claude/hooks/_lib.sh` and `claude/.claude/hooks/_config.sh`. It is an inclusion floor, so a third library needs no edit to it. Without it, an empty `_HELPER_LIBRARIES` would leave the sourced test with no cases, which pytest skips (row 31).

The check guards against honest mistakes, not evasion. A heredoc line shaped like a source statement passes it, and so do two libraries that source only each other.

**Paired invariant, registered half**, in T. The edits:
1. In `_gate_registration_problems` (T:3536), add a check after `_hook_command_script_name` resolves a name and before the `known_scripts` check. When `is_helper_library(script_name)` is true, append a problem that names the script and says it is a helper library registered as a hook command, which is sourced and never registered. Then `continue`.
2. Extend the docstring's command rule with "and is not a helper library".
3. Add `_topic-lib.sh` to `_CONTROL_KNOWN_SCRIPTS`.
4. Add one `_REGISTRATION_CONTROL_TABLE` row, `id="helper-library-registered-as-command"`, that registers `_topic-lib.sh` under `Stop` and expects "helper library" (row 30).

`test_gate_handlers_register_with_on_failure_block` already walks every handler in `claude/.claude/settings.json` and every `plugins/*/hooks/hooks.json`, so the check covers every registration surface (rows 10, 11). In `_hook_config_files`, every real helper library is a known script. Edit 3 gives the control row that same shape, so the row proves the new check fires, not the "does not resolve" one.

**Liveness probe** (`test_shell_lib_function_liveness.py`).
- `_MAIN_HELPER_LIBRARIES = helper_libraries(HOOKS_DIR)` replaces `[_LIB_SH, _CONFIG_SH]` in both tests and in the union inside the scanned-versus-declared test. Keep the `ids=lambda path: path.name` function, so ids stay the same.
- `_CONFIG_SH` goes. `_LIB_SH` stays as the dependency root.
- Add `_functions_declared_after_sourcing(library_paths)`. It holds today's `subprocess.run` call and PATH-only environment, sources each path in order, then runs `declare -F`. One form is `for library; do . "$library"; done; declare -F` with the paths as arguments.
- `_shell_declared_functions(lib_path)` calls it with `_LIB_SH`, then `lib_path` unless it is `_LIB_SH`. `_lib.sh` already sources `_config.sh`, so `_config.sh` gets sourced a second time, which is safe (row 4).
- Add `test_a_library_needing_lib_sh_at_source_time_declares_its_functions`. A `tmp_path` seed's first command is `declare -F _lib_jq >/dev/null || return 1`, and it defines one function. The test asserts that `_shell_declared_functions` returns that function. Its control calls `_functions_declared_after_sourcing` with the seed alone, so it differs from the seed call only in the path list, and asserts the function is absent. The test therefore fails if the probe stops sourcing `_lib.sh` first (rows 5, 26).
- Plugin libraries stay out, because the corpus excludes `plugins/` (G1).
- Update the module docstring (:3, :50-52), the test docstring (:154-156), and the failure message (:178) to say "helper library of `claude/.claude/hooks/`".

**Isolated-hook builders** (`helpers.py`).
- `build_isolated_hook` (:1242) symlinks every `helper_libraries(HOOKS_DIR)` entry in place of the two literal lines (:1257-1258). `config-keys.psv` stays under `schema_text` control.
- `symlink_hooks_lib_chain` (:2622) loops `_symlink_if_absent` over the same list, plus the literal `config-keys.psv`. That file is data, not a helper library.
- Each builder calls `helper_libraries(HOOKS_DIR)` in its own body, never through a module-level constant, so a test can repoint `helpers.HOOKS_DIR` (row 25).
- Trim both docstrings to "every helper library". Keep the fact that `_config.sh` and `config-keys.psv` are BASH_SOURCE-relative siblings.

A hook that starts sourcing a new library then runs in every isolated directory without a caller edit. Two tests in `test_helper_library_rule.py` pin that. Each monkeypatches `helpers.HOOKS_DIR` to a `tmp_path` directory seeded with `_lib.sh`, `_config.sh`, `_topic-lib.sh`, `config-keys.psv` and `hook.sh`. The seeded directory is not named `isolated-hooks`, which `build_isolated_hook` creates under `tmp_path`. Neither test module defines a module-level path constant built from `HOOKS_DIR` or `REPO_ROOT`.
- `test_symlink_hooks_lib_chain_links_every_helper_library` expects the destination to hold exactly the three libraries and `config-keys.psv`, each resolving into the seeded directory.
- `test_build_isolated_hook_links_every_helper_library` calls the builder with the default `schema_text` and no `extra_links`. It expects the isolated directory to hold exactly `hook.sh` and the three libraries, each resolving into the seeded directory.

**Other filters.** `test_cursor_adapter_translate.py:1351` replaces `hook.name.startswith("_")` with `is_helper_library(hook.name)`, and adds it to that file's `helpers` import (:16). `test_lib_session_identity.py` gets no edit. Its `path.name != "_lib.sh"` filter (:153-156) keeps `_config.sh` and every future helper library under the session-id path check (rows 23, 24). That check's docstring names a new file that forgets the guard as the case it exists for (:146-148). This departs from GH-1434 scope item 2 for that one file.

**Rules paragraph.** Replace the "fails CI today" paragraph of `.claude/rules/bash-unit-test-seams.md` with the text below. The naming paragraph above it and both GH-1436-owned lists stay (row 21).

```markdown
**A `_`-prefixed `.sh` file in a hooks directory is a helper library, not a
hook.** `is_helper_library` in `claude/.claude/tests/helpers.py` is the one
rule the hook checks use to tell the two apart. A new `_<topic>-lib.sh` under
`claude/.claude/hooks/` needs no `docs/hooks.md` entry, no `# hook-class:`
header, and no test edit to register it. Checks that scan the content of
every `.sh` file there still apply to it, exact-count pins included. Two
tests in `claude/.claude/hooks/tests/` fail it unless both hold:

- A hook, script, or other helper library sources it. A test does not count.
- No `settings.json` or plugin `hooks.json` registers it as a command.

The function-liveness test sources `_lib.sh` before each other library in
`claude/.claude/hooks/`, so a library may depend on `_lib.sh` at source time.
```

**Coverage principle.**
- A check that sweeps `_lib.sh` today sweeps every helper library.
- A check that skips helper libraries by the name list or the `_` prefix today skips every helper library.
- The session-id check is the one exception. It skips only files named `_lib.sh`, so it keeps scanning `_config.sh` and every new helper library (row 23).

Existing files keep exactly today's coverage, except that the `\s` check gains `_config.sh`. Out of scope says why the skipping checks are not widened to sibling libraries here.

**Alternatives set aside.**
- Predicate home in `claude/.claude/hooks/tests/_lib_sh_helpers.py`. It avoids the full-suite trigger. But `helpers.py` and `scripts/tests/` cannot import from the hooks test package without a path hack, and `helpers.py` changes anyway (row 13).
- `is_helper_library` typed over `Path`, or over `str | Path`. The rule reads only the name, and the registered half holds only a name (row 32).
- Literal names kept in the isolated-hook builders, with callers passing `extra_links`. A hook that starts sourcing a new library would then need every isolated-hook caller of it edited. That is the registry edit the Done-when rules out.
- Registered half done by dropping helper libraries from `_hook_config_files`' `known_scripts`. It is one line. But the failure reads "does not resolve to a hook script" with no reason. The control table passes its own `known_scripts`, so it cannot exercise the filter either.
- Lighter primitives checked for the sourced half:
  - A bare substring match of the library's name in any shipped shell file. Every plugin `_lib.sh` would pass on another tree's mention, and comments would count.
  - Reusing `_LIB_SOURCE_LINE_RE` (T:2799). It matches only `_lib.sh` in two `$0` forms, so `_config.sh` and the `${CLAUDE_PLUGIN_ROOT}` plugin form fail.
  - Following ShellCheck `source=` directives. Not every sourcer carries one.
- The sourced half kept in T. T is already recorded for a split (row 27).
- `_HELPER_LIBRARIES` built in S by globbing the hooks directories again. It would restate T's directory set (T:98-99).
- A liveness probe that sources every main library in one shell. It loses the per-library attribution of the scanned-is-a-subset-of-declared assertion. Sourcing each library alone, as today, fails GH-1436's sibling (row 6).
- `test_lib_session_identity` widened to scan `_lib.sh` as well. Main `_lib.sh` matches its pattern only in comments (row 14), so `_lib.sh` alone would satisfy the test's anti-vacuity assertion.

**Assumption ledger**

**Root:** A new `_`-prefixed helper library in a hooks directory fails CI, because the hook checks and several test registries name the two existing libraries literally. The naming rule that replaces those names must not let a real hook escape the hook checks by its filename.

**Givens:**
- G1. Each plugin's hooks source that plugin's own vendored `_lib.sh`, never the stowed one. Reason: a plugin installs through the marketplace, independent of stow. `[verified: test_shell_lib_function_liveness.py:14-16; test_lib_session_identity.py:184-186]`

**Mechanisms:**
- M1 — One predicate and one enumerator in `helpers.py`, called by every registry except the session-identity filter, with control tests in `test_helper_library_rule.py`. `anchors: root, row1, row13, row23, row32`
- M2 — `_all_hook_files(include_helper_libraries=...)`. `_config.sh` folds into `ALL_HOOKS_AND_LIBS`, `_PIPE_LINT_FILES` goes, and `test_all_hooks_and_libs_includes_every_lib_sh` becomes a set equality against `helper_libraries`. `anchors: root, row1, row2, row3, row18`
- M3 — The sourced half in S: a parametrized test, the `_sources_helper_library` rule, the `_unsourced_helper_libraries` aggregate, their controls, and an inclusion floor, reusing `_shipped_shell_files()` and T's `ALL_HOOKS_AND_LIBS`. It is heavier than a substring check. "Alternatives set aside" lists three lighter primitives and why each fails. `anchors: root, G1, row7, row8, row9, row12, row27, row31`
- M4 — The registered half: a helper-library check inside `_gate_registration_problems`, plus one control-table row. `anchors: root, row10, row11, row30, row32`
- M5 — The liveness probe sources `_lib.sh` first, enumerates libraries through the predicate, and gains a seeded test with a sourced-alone control. `anchors: root, G1, row4, row5, row6, row26`
- M6 — The isolated-hook builders link every main helper library, pinned by two seeded tests. `anchors: root, row1, row16, row25`
- M7 — The cursor-adapter filter routes through the predicate. The session-identity filter keeps its `_lib.sh`-by-name exclusion. The unlisted content globs stay as they are. `anchors: row14, row15, row17, row23, row24`
- M8 — The rules paragraph is rewritten, and the GH-1436-owned lists are left alone. `anchors: root, row17, row19, row21`

**Assumptions:**
1. `[verified: Glob claude/.claude/hooks/_* → __init__.py, _config.sh, _lib.sh; Glob plugins/*/hooks/* → one _lib.sh per plugin, no other _-prefixed file]` Today the `_`-prefixed `.sh` files in hooks directories are exactly the six that `_HELPER_LIBRARY_NAMES` excludes. So the predicate leaves `ALL_HOOKS`, both builders' link sets, and the liveness parametrization unchanged.
2. `[verified: Grep _HELPER_LIBRARY_NAMES|_all_hook_files|include_lib outside .claude/plans]` `_HELPER_LIBRARY_NAMES` has one code use, at T:128. `include_lib` appears only in T. The two design-decision docs cite `_all_hook_files()` by name, and their claims stay true.
3. `[verified: Grep \\s in claude/.claude/hooks/_config.sh → no match]` Folding `_config.sh` into `ALL_HOOKS_AND_LIBS` adds a `\s` case that passes.
4. `[verified: Grep readonly|declare -r|typeset -r over hooks/_*.sh → no declaration; _config.sh:72 "Not readonly, so a second source does not fail."]` Sourcing `_config.sh` again after `_lib.sh` has sourced it does not fail.
5. `[verified: test_shell_lib_function_liveness.py:142-148, :166-168]` The probe's exit status is `declare -F`'s. A library whose source-time check returns 1 declares none of its functions, so it fails only the scanned-is-a-subset-of-declared assertion. `check=True` trips only on `exit`.
6. `[unverified — relayed from GH-1434 through this plan's Context, "Why now"]` GH-1436's sibling library checks at source time that `_lib.sh` is loaded. The probe handles that check whether it returns or exits.
7. `[verified: Grep ^[[:space:]]*(if ! )?(\.|source) .*/_[A-Za-z0-9_.-]+\.sh outside tests/]` Every production source line for a hooks-directory library takes one of two forms. One is a same-directory expression: `${0%/*}`, `$(dirname "${BASH_SOURCE[0]}")`, or `$(dirname "$0")` for scripts-directory siblings. The other is a directory part ending in `/hooks`: `$(dirname "$0")/../hooks`, `$SCRIPT_DIR/../hooks`, `$(dirname -- "$resolved")/../hooks`, `$REPO_DIR/claude/.claude/hooks`, or `${CLAUDE_PLUGIN_ROOT}/hooks`.
8. `[verified: same Grep as row 7]` Every current helper library has a sourcer under the rule:
   - Main `_lib.sh`: every hook in `_LIB_SOURCE_HOOKS`.
   - `_config.sh`: `_lib.sh:25`, `config-get.sh:39`, `migrate-legacy-config.sh:28`, `worktree-removal-status.sh:36`, and `install.sh:30`.
   - The four plugin `_lib.sh` files: `require-npm-version-bump.sh:111`, `require-plugin-version-bump.sh:75`, `require-skill-review.sh:120`, and `validate-migration-filename.sh:38`.
9. `[verified: test_shell_dialect.py:73-74, :116-125; test_bash_floor.py:39]` `_shipped_shell_files()` is cached. It lists tracked shell files through `scripts/list-shell-files.sh`, as repo-relative paths, minus any path with a `tests` segment. A sibling test module already imports it. An untracked sourcer is invisible to it, as it is to the liveness corpus.
10. `[verified: Grep "hooks"|command in .claude/settings.json → none; Grep hooks in plugins/*/.claude-plugin/plugin.json → descriptions only; Grep ^hooks: in SKILL.md and agent files → none]` Hook registrations live only in `claude/.claude/settings.json` and `plugins/*/hooks/hooks.json`. `_hook_config_files` (T:3730-3735) walks exactly those files.
11. `[verified: T:3510-3525, :3551-3560]` `_gate_registration_problems` already flags any handler whose command is not exactly one `~/.claude/hooks/<x>.sh` or `${CLAUDE_PLUGIN_ROOT}/hooks/<x>.sh` token, after any env assignments. Checking the resolved name therefore covers every handler shape.
12. `[verified: select-tests.py:737, :1006, :1010, :1048, :1050]` A change under `claude/.claude/hooks/`, `plugins/*/hooks/`, `claude/.claude/scripts/*.sh`, `install.sh`, or root `scripts/` selects `claude/.claude/hooks/tests`. A sourcer edit therefore reruns the new invariant with no `select-tests.py` edit.
13. `[verified: select-tests.py:562-566]` Editing `helpers.py` selects the full suite.
14. `[verified: Grep /\$\{?SESSION_ID\b over **/hooks/_*.sh → _lib.sh:551, :853, :3419, all comments]` Among the six helper libraries, only main `_lib.sh` matches the session-id path-build pattern, and only in comments. `_config.sh`, the one library that check scans today, never matches it.
15. `[verified: test_cursor_adapter_translate.py:16, :1351]` That file applies the `_`-prefix rule inline and imports from `helpers`.
16. `[verified: Grep build_isolated_hook( → 9 call sites, extra_links only WC_TOTAL_ROW_AWK_PROGRAM; helpers.py:2635-2637 uses _symlink_if_absent]` No caller passes a helper library as `hook` or in `extra_links`, so linking every library collides with no caller's own link. `symlink_hooks_lib_chain` stays idempotent.
17. `[verified: test_hook_command_normalization.py:76-88, :125; test_cursor_adapter_gate_matrix.py:1312; test_transcript_denials.py:337-341; test_default_branch_resolution_is_shared.py:32-36; test_cursor_adapter_translate.py:660-673, :689, :745-750, :776-778]` The hooks-directory `*.sh` globs the issue does not list select files by content or by header, and none holds a list of helper libraries. So a new library needs no entry in them. Their content-derived pins apply to it exactly as to `_lib.sh`. The two `HOOKS_DIR.glob("*.sh")` globs re-read here, which already include `_lib.sh`, pin:
    - the exact count of 13 `_lib_split_fragments "$VAR"` call sites;
    - one payload-field case per file that mentions `$INPUT`;
    - the `EMITTED_KEY_CASES` table.
18. `[verified: T:108-127, :1840-1842; _lib.sh:1261, :1280]` The bare-jq, inline-matcher, bare-xargs, and cumulative-review checks skip `_lib.sh` because `_lib.sh` defines what each detects, or holds status-checked uses of it.
19. `[verified: Grep bash-unit-test-seams outside .claude/plans → none]` No test or doc pins the rules file's text.
20. `[verified: docs/design-decisions/code-file-line-limit.md:50-57; Glob for a line-limit test file → none]` No code-file line-limit check runs yet, so growing T trips nothing.
21. `[unverified — relayed from GH-1434, scope item 6]` GH-1436 owns the preference list and the "Already-seamed libs" list in `.claude/rules/bash-unit-test-seams.md`.
22. `[engineer-verified: "Include it (Recommended)"]` `claude/.claude/scripts/tests/test_cursor_adapter_translate.py`, which GH-1434's scope list does not name, is in this plan's Critical files. The quote answers "Include this file in the plan?".
23. `[engineer-verified: "Keep scanning libraries (Recommended)"]` `test_lib_session_identity.py` keeps scanning helper libraries. The quote answers the dispatching session's question on how the plan should handle `test_lib_session_identity.py:153-156`, given the reviewer's finding that routing it through the predicate exempts `_config.sh` and every future helper library from the session-id path check.
24. `[unverified — the dispatching session's option description for row 23's label, not the engineer's words]` That option reads: leave the `_lib.sh`-by-name exclusion as it is, so new helper libraries stay under the session-id check, and record that this departs from GH-1434 scope item 2 for this one file. This plan reads the label that way, so `test_lib_session_identity.py` gets no edit.
25. `[verified: helpers.py:34, :1257-1258, :2635-2637; test_installed_locale_finder.py:5, :15]` Both builders read the module global `HOOKS_DIR` at call time, and a `claude/.claude/tests/` module already monkeypatches a `helpers` attribute. A test that repoints `helpers.HOOKS_DIR` therefore reaches both builders, as long as each calls `helper_libraries(HOOKS_DIR)` in its body.
26. `[verified: test_shell_lib_function_liveness.py:136-149; _lib.sh:39]` `_shell_declared_functions` sources whatever path it is given under a PATH-only environment, and `_lib_jq` is a column-0 function of `_lib.sh`. A seed that returns 1 unless `_lib_jq` is declared therefore declares its function only when `_lib.sh` was sourced first.
27. `[verified: docs/reports/2026-11-19-code-file-size-offenders/findings.md:187]` T, at 3,756 lines, is recorded as "split pending" under #1532.
28. `[verified: select-tests.py:737-738, :1010, :1023, :1151-1156, :1381-1391]` A hooks-directory `.sh` change selects `claude/.claude/hooks/tests` and `claude/.claude/scripts/tests`. A `claude/.claude/scripts/*.sh` change selects those two plus `claude-skills/skills/tests`. `select-tests.py` diffs against the merge-base and takes no paths to select for. In a worktree that holds this branch's `helpers.py` change, it selects the full suite instead.
29. `[verified: nudge-memory-store-audit.sh:2, :65; ensure-account-dir.sh:10; Grep nudge-memory-store-audit\.sh|ensure-account-dir\.sh over **/test_*.py → test_cursor_adapter_gate_matrix.py:548, :1103, T:327-363, test_nudge_memory_store_audit.py:29, test_ensure_account_dir.py:14]` The probe's hook is informational and bootstraps `_lib.sh` at :65 through `${0%/*}`. The probe's script sources `_lib.sh` at :10 through `$(dirname "$0")/../hooks/`. No test that names either file copies its source chain by name. `run_skill_command` (`helpers.py:2674`, `:2698-2703`) stages `ensure-account-dir.sh` behind `symlink_hooks_lib_chain`, so the probe's skills-domain run exercises that builder for the probe library.
30. `[verified: T:3589-3599, :3679-3685]` Each `_REGISTRATION_CONTROL_TABLE` row carries an `id=` string, and the test asserts that the row's one problem contains the expected text.
31. `[verified: requirements-dev.txt pins pytest==8.*; _pytest/mark/structures.py get_empty_parameterset_mark in the shared venv's pytest 8.4.2; Grep empty_parameter_set_mark outside plans → none]` pytest skips a test whose parametrization is empty, and this repo sets no `empty_parameter_set_mark` override.
32. `[verified: T:3510, :3557-3558]` `_hook_command_script_name` returns `str | None`, a bare script name compared against `known_scripts`.
33. `[engineer-verified: "Proceed anyway"]` This plan ships as one PR at its `Projected diff:` of about 440 changed lines. The quote answers "This plan projects about 440 changed lines (an estimate; threshold 400). Split into smaller PRs now, or proceed?".
34. `[unverified — relayed from the staff-sdet round-2 findings, R1, citing require-worktree-for-file-writes.sh:154-166 and cleanup-merged-branches.sh:96-98; not run]` A write inside the probe worktree makes the worktree gate lock it, and `git worktree remove --force` refuses a locked worktree.

## Critical files

- `claude/.claude/tests/helpers.py`: the predicate, the enumerator, and the builder changes, under Approach "Predicate" and "Isolated-hook builders". Reuse `_symlink_if_absent` (:2601).
- `claude/.claude/tests/test_helper_library_rule.py` (new): the tests under "Predicate tests" and "Isolated-hook builders".
- `claude/.claude/hooks/tests/test_hook_alignment.py`: the edits under "Hook checks" and "Paired invariant, registered half". Reuse `_hook_command_script_name` (:3510), `_REGISTRATION_CONTROL_TABLE` (:3589), and `_PLUGIN_HOOKS_DIRS` (:99).
- `claude/.claude/hooks/tests/test_helper_library_sourcing.py` (new): everything under "Paired invariant, sourced half". Reuse `_shipped_shell_files` and `_read_text` (`test_shell_dialect.py:116`, :128), and `ALL_HOOKS_AND_LIBS` (T:163).
- `claude/.claude/hooks/tests/test_shell_lib_function_liveness.py`: the edits under "Liveness probe".
- `claude/.claude/scripts/tests/test_cursor_adapter_translate.py`: route the inline `_` check at :1351 through `is_helper_library`.
- `.claude/rules/bash-unit-test-seams.md`: replace the "fails CI today" paragraph.

`claude/.claude/hooks/tests/test_lib_session_identity.py` is not edited (Approach, "Other filters").

Dispatch: one `code-writer` dispatch covers all seven files. S imports T's `ALL_HOOKS_AND_LIBS`, and every other file consumes the predicate's signature, so a split would restate both in each prompt. Every verification run on this branch selects the full suite, because `helpers.py` changes (row 13), so a split would also add a second full-suite run. Its verification command is Verification step 2.

Projected diff: ~440 lines.

## Verification

1. Before the `code-writer` dispatch, collect the ids of the three existing test modules the diff edits. Run `scripts/venv-run.sh pytest --collect-only -q -n0 claude/.claude/hooks/tests/test_hook_alignment.py claude/.claude/hooks/tests/test_shell_lib_function_liveness.py claude/.claude/scripts/tests/test_cursor_adapter_translate.py`. Keep only the lines containing `::`, sort them, and save the result outside the repository. After implementation, repeat into a second file. Expected, with module paths shortened here:
   - `comm -23` of the first file against the second prints nothing, so no id is removed or renamed.
   - `comm -13` of the same pair prints exactly these ids:
     - `test_hook_alignment.py::test_no_gnu_backslash_s_regex_extension[claude/.claude/hooks/_config.sh]`;
     - `test_hook_alignment.py::test_gate_registration_problems_control_table[helper-library-registered-as-command]`;
     - `test_shell_lib_function_liveness.py::test_a_library_needing_lib_sh_at_source_time_declares_its_functions`.

   The unchanged ids prove the predicate changed no hook's classification. The same collection over the two new modules lists:
   - in S: six `test_every_helper_library_is_sourced_by_a_shipped_shell_file` ids, one per row-1 library; nine `test_sources_helper_library_control_table` ids; the `sourced` and `unsourced` ids of `test_unsourced_helper_libraries_control`; and `test_helper_libraries_include_lib_sh_and_config_sh`;
   - in `test_helper_library_rule.py`: seven `test_is_helper_library` ids, `test_helper_libraries_lists_direct_helper_libraries_sorted`, `test_symlink_hooks_lib_chain_links_every_helper_library`, and `test_build_isolated_hook_links_every_helper_library`.
2. `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py` selects the full suite on its own, since `helpers.py` is a global trigger, and the run passes.
3. `scripts/venv-run.sh ruff check claude/.claude/ claude-skills/ plugins/ evals/` reports no violations.
4. Run a Done-when probe in a disposable worktree, once the implementation is committed. The probe edits no file in this worktree.
   1. Run `git worktree add --detach <probe-dir> HEAD`, where `<probe-dir>` is a new directory outside this worktree. Run every later sub-step from `<probe-dir>`.
   2. Add `claude/.claude/hooks/_probe-lib.sh`. Its first line is `#!/usr/bin/env bash`, as at `_config.sh:1`. Its first command is `declare -F _lib_jq >/dev/null || return 1`, and it defines one no-op function, `_probe_lib_marker`. Its content stays clear of the content pins in row 17, so the probe claims only the name- and glob-based checks.
   3. Source it from one informational hook and one script, each just after its `_lib.sh` source (row 29), and call `_probe_lib_marker` on the next line:
      - in `claude/.claude/hooks/nudge-memory-store-audit.sh`, after the bootstrap block that opens at :65, with `. "${0%/*}/_probe-lib.sh"`;
      - in `claude/.claude/scripts/ensure-account-dir.sh`, after :10, with `. "$(dirname "$0")/../hooks/_probe-lib.sh"`.
   4. `git add` the three files, so every `git ls-files`-based check sees them as CI would (row 9).
   5. Run `scripts/venv-run.sh pytest -q claude/.claude/hooks/tests claude/.claude/scripts/tests claude-skills/skills/tests`. These are the domains `select-tests.py` selects for the three paths. They are named here because `select-tests.py` itself selects the full suite in this worktree (row 28). Expected: all pass, with no registry edited.
   6. Delete both added source lines, and run `scripts/venv-run.sh pytest -q claude/.claude/hooks/tests/test_helper_library_sourcing.py -k sourced_by`. Expected: exactly one failure, for `[claude/.claude/hooks/_probe-lib.sh]`, whose message lists the accepted source shapes.
   7. From this worktree, run `git worktree unlock <probe-dir>`, then `git worktree remove --force <probe-dir>`, each naming the directory sub-step 1 created. The unlock is expected to be needed, because the file-write gate locks a linked worktree on its first write (row 34). If the unlock reports the worktree is not locked, go on to the removal. `--force` discards the probe's staged files, which is the intent.

   The registration control-table row, which step 2 runs, covers the registered-as-command negative, so the probe does not edit `settings.json`.
5. `git grep -n _HELPER_LIBRARY_NAMES -- . ':!.claude/plans'` prints nothing.

## Out of scope

- Widening the checks that skip helper libraries to sibling libraries: bare-jq, inline-matcher, bare-xargs, and the cumulative-review tripwire. Each skips `_lib.sh` because `_lib.sh` defines what it detects, or holds status-checked uses of it (row 18). Widening needs per-check adjudication, and no sibling library exists yet to adjudicate.
- Routing `test_lib_session_identity.py:153-156` through `is_helper_library`. GH-1434 scope item 2 covers that filter, but the engineer chose to keep it scanning helper libraries (rows 23, 24).
- Exempting helper libraries from the hooks-directory content scans the issue does not list (row 17), or from `test_config_lib.py:2579` and `test_review_ledger_script.py:1078`. None of them lists helper libraries. Their content-derived pins, such as the exact `_lib_split_fragments` call-site count, apply to a new library as to `_lib.sh`. Taking libraries out of a count that is about hooks is a separate decision.
- Widening the sourced-half matcher to further correct spellings: `${BASH_SOURCE[0]%/*}`, a `$HOOK_DIR`-style variable, a single-quoted operand, or a `[ -f … ] && .` prefix. None occurs in the tree today (row 7), and the failure message lists the accepted shapes.
- Literal `_lib.sh`/`_config.sh`/`config-keys.psv` chains that copy one file's real source dependencies. Examples are T:3099, T:3078, `test_bash_floor.py`, `test_marker_script.py`, and `test_pr_cost_section.py`. They record what a specific file sources, not which files are helper libraries.
- The preference list and the "Already-seamed libs" list in `.claude/rules/bash-unit-test-seams.md`. This plan could edit them and does not, because GH-1434 assigns them to GH-1436 (row 21).
- `_`-prefixed libraries under `claude/.claude/scripts/` and the filter at `claude-skills/skills/tests/test_handoff_and_resume_skills.py:374`. The rule covers hooks directories only.
- Plan files that record `_HELPER_LIBRARY_NAMES`, such as `.claude/plans/lighten-subprocess-tests.md:123`. They are preserved records.
- Hardening the sourced check against deliberate evasion, such as a source-shaped heredoc line or mutually sourcing libraries. These are CI tests over contributor-authored files that PR review already sees.
