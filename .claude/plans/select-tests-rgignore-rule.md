# Route the root `.rgignore` in `select-tests.py`

## Context

Goal: give an edit to the repo-root `.rgignore` a defined test selection in `select-tests.py`, so it neither falls through to the full suite by accident nor drops tests that read it.

Ask: "#3 and #4 go for it as well" (GH-1535 follow-up #3, a `select-tests.py` rule for a root-level `.rgignore` with its test); on the open design question: "can't you let the plan-it process decide?"

Why now: GH-1535 added a tracked `.rgignore` listing `.claude/plans/`. No `DOMAIN_RULES` row or test names it today, so an edit to it reaches the `unmatched-path` full-suite fallback, the same as `.gitignore`.

Open design question: CI's `SKIP_REGEX` (`.github/workflows/tests.yml`) names five files and `claude/.claude/tests/test_ci_path_filter.py` pins that set exactly. `.claude/plans/test-suite-boundary-and-selective-ci.md` (G1) says `select-tests.py`'s empty-target set must stay a subset of CI's deny-list. `PLANS_DIR` is an empty-target row yet is not in `SKIP_REGEX`, so G1 is not literally enforced today.

## Approach

Take shape 3. Map `.rgignore` to `claude/.claude/hooks/tests/` (`HOOKS_TESTS_DIR`, the hooks tree below) with an exact-match `CROSS_DOMAIN_EXCEPTIONS` row and its test, and leave CI's `SKIP_REGEX` as it is. Reasons:
- The one test that needs the file sits in the hooks tree (row 1).
  - `test_relative_links_resolve_to_existing_files` in `test_design_decision_files.py` (the link test below) checks that a design-decision doc's link to `.rgignore` resolves.
  - `test_shellcheck.py` also reads its first line, as it does for every tracked file, so the row does not count it as a dependent.
- The table routes each exact-match path to the tests that read it (row 8).
- The table maps root-level files read from the hooks tree to the whole directory (row 17). That also covers readers inside the tree that the contract test cannot see (row 16).
- A non-empty target falls outside G1, which constrains only empty targets (row 6). That settles Context's open design question: neither the merge gate nor `test_ci_path_filter.py` changes.
- A diff that deletes `.rgignore` still runs the link test, locally through the new row and in CI through the full suite (row 4).

No merge-gate behavior changes, because CI still runs the full suite for any diff that touches `.rgignore` (row 4). Of the three files row 14 approves, the diff edits only `CHANGELOG.md`.

Alternatives weighed:
- **Shape 1: add `.rgignore` to CI's `SKIP_REGEX` and give it an empty-target row.** Rejected, because its premise is false. CI's deny-list holds paths "confirmed unread by any test module", and the link test needs `.rgignore` to exist (rows 1, 3). A diff that only deletes the file would then pass CI and leave `main` red (row 5). Closing that would take a detect-step change that stops skipping a deleted deny-listed path, plus a test tying the row to `SKIP_REGEX`: two guards stacked on a premise that does not hold.
- **Shape 1 after removing the doc's link to `.rgignore`, so its premise holds.** Rejected. It edits a file outside the Ask and row 14, and it removes the check that keeps the doc's reference live. It still leaves shape 1's deletion hazard through the exact-set and disk-existence tests (row 5).
- **Shape 2: leave `.rgignore` unmatched and pin it to the full suite, like `.gitignore`.** Rejected. It adds no `select-tests.py` rule, which the Ask names (row 10), and it runs every test tree when the tests that depend on the file sit in one (row 1).
- **An empty-target row in `select-tests.py` alone, as `PLANS_DIR` has.** Rejected. It drops the link test, against the Goal (row 1), and it breaks G1 (rows 6, 7).
- **Target the one file `test_design_decision_files.py` instead of its directory.** Rejected. The directory follows the precedent for root-level files read from the hooks tree, and the table calls over-selection the safe direction (row 17). It also covers readers inside the hooks tree that the contract test cannot see (row 16).

Revising G1, enforcing it with a test, and closing its `PLANS_DIR` gap stay out of this change; see Out of scope.

**Assumption ledger**

**Root:** An edit to the repo-root `.rgignore` matches no `select-tests.py` rule, so it falls open to the full suite (row 2), although every test that depends on the file today sits in the hooks tree (row 1).

**Givens:**
- `.rgignore` takes effect only in ripgrep-based search, which includes Claude Code's Grep tool. Reason: the vendor owns that tool's behavior, and the file's own comments record it as observed, not specified (`.rgignore:1-4`). The test suite runs neither ripgrep nor that tool (row 1).

**Mechanisms:**
- **M1.** In `claude/.claude/scripts/select-tests.py`, add the `RGIGNORE` constant with a comment naming the test that depends on it, an exact-match `CROSS_DOMAIN_EXCEPTIONS` row selecting the hooks tree, and a line in that table's header citation list (Critical files 1). The row turns the fallback into a rule that selects the tree holding every test that depends on the file.

  anchors: root, row1, row2, row6, row8, row12, row13, row17
- **M2.** In `claude/.claude/scripts/tests/test_select_tests.py`, add a test that feeds the literal path `.rgignore` and expects only the hooks tree, and register `_mod.RGIGNORE` in `_EXACT_MATCH_LITERAL_PATH_CONSTANTS` (Critical files 2). The literal path makes a drifted constant fail the test directly. The registration follows the list's own rule that every exact-match constant is checked against the disk.

  anchors: row2, row9, row16
- **M3.** Add one `CHANGELOG.md` bullet at the top of the Unreleased `### Changed` list (Critical files 3).

  anchors: row11, row14

**Rows:**
1. Before this change, one test needs `.rgignore` to exist and one sweep reads its first line. Both sit in the hooks tree, and no test elsewhere touches the file.
   - The link test asserts that every relative link in `docs/design-decisions/*.md` resolves to a file. `plans-hidden-from-grep-not-deleted.md:5` links `../../.rgignore`, so the test needs the file to exist. It does not read the file's content. [verified: `test_design_decision_files.py:468-484`; `docs/design-decisions/plans-hidden-from-grep-not-deleted.md:5`]
   - `test_shellcheck.py` reads the first line of every tracked file for a shebang, `CHANGELOG.md` and the plans included, which the table maps to no target. `.rgignore`'s first line is a `#` comment. [verified: `test_shellcheck.py:10-12,61-69`; `.rgignore:1`]
   - Grep for `rgignore` outside `.claude/plans/` finds only that link and prose at `evals/README.md:465`. [verified: Grep, this revision]
   - No tracked `.py` or `.sh` file invokes `rg`. The tests' `REPO_ROOT` glob calls take `*.md`, `test_*.py` and `plugins/*/hooks/*.sh`, none of which match `.rgignore`. [verified: Grep, this plan's first draft]
   - `test_ci_path_filter.py` lists every tracked file, but only to match each against `SKIP_REGEX`, which does not match `.rgignore`. [verified: `test_ci_path_filter.py:102-110,134-148`; `tests.yml:83`]
2. Today `.rgignore` reaches the `unmatched-path` fallback (`select-tests.py:1104-1111`), because no predicate matches it. After M1, a `.rgignore`-only diff returns the hooks tree alone with reason `domain-selected` (`:1113`). [verified: reads; Grep finds no `rgignore` literal in `select-tests.py`.] A reviewer's run of `select_pytest_targets` on `.rgignore` alone and beside other paths returned `unmatched-path` each time. That is a relayed result, not this author's check. Verification step 1 re-checks it.
3. CI's deny-list comment defines its entries as "paths confirmed unread by any test module", and says a new entry needs that check re-run. `.rgignore` fails the check, because the link test needs the file (row 1). [verified: `.github/workflows/tests.yml:79-83`]
4. CI keeps running the full suite for any diff that touches `.rgignore`, a deletion included. The path stays off `SKIP_REGEX`, and `changed=false` needs every path in the `git diff --name-only` listing to match it. [verified: `tests.yml:77,83-103`] Locally, `select-tests.py` reads the same listing with no `--diff-filter` (`select-tests.py:1161,1164`). A deletion then selects the hooks tree, where the link test fails, and a rename to an unmapped name falls open to the full suite. [verified: `git diff --name-only` lists a deleted path and a renamed path's new name only. Commit `ce8cfdc2` deleted `claude/.claude/hooks/tests/test_cursor_adapter_gate_matrix.py`, and `ab247f0e` renamed `cursor-adapter-check.py` to `cursor_adapter/check.py`. A rename away from `.rgignore` therefore hides the old path, so a move to an unmapped path selects nothing locally, and CI's full suite still catches it.]
5. Under shape 1, a diff that only deletes `.rgignore` would pass CI and leave `main` red. `SKIP_REGEX` would match the deleted path, so CI would skip pytest. Three tests that need the file would then fail on the next code-touching PR:
   - the link test (row 1);
   - `test_skip_regex_matches_exactly_the_intended_deny_list`, whose equality needs every deny-list entry tracked;
   - `test_every_exact_match_literal_path_constant_exists_on_disk` (row 9).

   [verified: `tests.yml:85-103`; `test_ci_path_filter.py:134-148`; `test_select_tests.py:2862-2864`] The row inherits row 4's unverified listing. The exact-set test already gives every deny-listed file this hazard. `.rgignore` differs because its design-decision doc presents a lone deletion as the rollback: "The change is one file to revert." [verified: `docs/design-decisions/plans-hidden-from-grep-not-deleted.md:9`]
6. G1 is `test-suite-boundary-and-selective-ci.md`'s label for the invariant `select-tests-fallback-audit.md` states: "`select-tests.py`'s empty-target set must stay a subset of CI's `SKIP_REGEX` set." It constrains only empty targets, so a non-empty target needs no `SKIP_REGEX` entry. `test_select_tests.py`'s `.gitignore` test docstring and the CI design-decision doc's Sources list record it. [verified: `.claude/plans/test-suite-boundary-and-selective-ci.md:64`; `.claude/plans/select-tests-fallback-audit.md:475-481`; `test_select_tests.py:1315-1318`; `docs/design-decisions/ci-stays-an-unconditional-full-suite-backstop.md:32`]
7. G1 is already not literally true. `PLANS_DIR` maps to `()` (`select-tests.py:749`), but `.claude/plans/` is absent from `SKIP_REGEX` (`tests.yml:83`). `test_nudge_transcript_toolkit.py:119`'s `REPO_ROOT.rglob("*.md")` reads plan content, so plans would fail CI's confirmed-unread criterion. The `PLANS_DIR` row predates G1, and the plan that stated G1 kept it (`select-tests-fallback-audit.md:813-820`). This change neither creates nor widens the gap. [verified: reads; `select-tests.py:499-503`]
8. Each exact-match path is a module constant whose comment names the test that reads it, or states that none does. `PLANS_DIR` and `CHANGELOG_MD` are the empty-target cases. [verified: `select-tests.py:425-528`]
9. `_EXACT_MATCH_LITERAL_PATH_CONSTANTS` feeds `test_every_exact_match_literal_path_constant_exists_on_disk`, which catches a constant drifting from its file on disk. Its comment asks for every constant behind an exact-match predicate, but nothing checks that the list is complete, so M2 adds the entry by hand. The list is built at import, so a missing `RGIGNORE` attribute fails collection of the whole file. The entry makes that test need `.rgignore` on disk, as it already needs `install.sh`, whose row likewise selects only the hooks tree (`select-tests.py:1053`). So a local deletion does not run it, and CI's full suite does. [verified: `test_select_tests.py:2511-2563,2862-2864`; Grep finds no other use]
10. The Ask's parenthetical describes GH-1535 follow-up #3 as "a `select-tests.py` rule for a root-level `.rgignore` with its test". [unverified: that gloss is the session's, and I did not read the follow-up list it summarizes.] Shape 2's rejection leans partly on it.
11. Prior `select-tests.py` rule changes carry a `CHANGELOG.md` bullet, including the one that gave `.claude/plans/` and `CHANGELOG.md` empty targets. No repo rule requires one, so M3 follows precedent. [verified: `CHANGELOG.md:456,611,657`; Grep of `CHANGELOG` in `CONTRIBUTING.md`, `README.md`, `CLAUDE.md` and `.claude/rules/`]
12. The engineer handed the choice among the three shapes to this process. [engineer-verified: "can't you let the plan-it process decide?"] The three shapes are the session's wording, not the engineer's. [unverified: as relayed in the dispatch]
13. `select-tests.py` ships to every stow consumer under `~/.claude/scripts/`, but the new row changes selection only inside a checkout of this repo. It takes its git root from `rev-parse --show-toplevel` and emits only this repo's test paths. [verified: `select-tests.py:558,1141`]
14. The engineer was asked whether the diff may edit three files the Ask does not name (`.github/workflows/tests.yml`, `claude/.claude/tests/test_ci_path_filter.py`, `CHANGELOG.md`) and selected the label below. [engineer-verified: "All three (Recommended)"] The option's description was the session's wording, not the engineer's.
15. The engineer was asked whether they said the Ask line's first quote and selected the label below. [engineer-verified: "Yes, I said it"]
16. `TestCrossDomainReadCompleteness` fails when a test builds a module-level path constant whose selection does not cover that test. After M1, a new module-level `.rgignore` read in a corpus test outside the hooks tree fails it. It resolves only `Path` chains of string literals rooted at `__file__` or a `helpers.py` path constant, so it misses a read built inside a function body, a read through a subprocess, and a read through a markdown link a test resolves, which is how the link test reaches `.rgignore`. Its corpus also omits `evals/`. [verified: `test_select_tests.py:143-161,385-402`; `select-tests.py:756-764`]
17. Root-level files whose tests sit in the hooks tree map to the whole `HOOKS_TESTS_DIR`, as `install.sh` and the root `CLAUDE.md` do. The table calls over-selection "the safe direction". [verified: `select-tests.py:1053,1058,883`]

## Critical files

**Dispatch split.** One `code-writer` dispatch (`model: sonnet`) covers all three files. The red-then-green order in Verification steps 1-2 spans `select-tests.py` and its test, and the `CHANGELOG.md` bullet describes the same row, so splitting would restate both in every prompt.

1. `claude/.claude/scripts/select-tests.py` (M1).
   - After `ROOT_SETTINGS_JSON` (`:519-522`), add `RGIGNORE = ".rgignore"` under the comment `# test_design_decision_files.py (HOOKS_TESTS_DIR) checks that a docs/design-decisions link to this file resolves.`, wrapped to the neighboring comments' width.
   - After the `ROOT_SETTINGS_JSON` row (`:1061`), add `(lambda p: p == RGIGNORE, (HOOKS_TESTS_DIR,)),`.
   - After the header line for `CONFIG_KEYS_PSV` (`:903`), add `# RGIGNORE: see its own comment above for citation.`
2. `claude/.claude/scripts/tests/test_select_tests.py` (M2).
   - After `test_root_claude_md_change_selects_hooks_tests` (`:1547-1555`), add `test_rgignore_change_selects_hooks_tests`. It calls `_mod.select_pytest_targets([".rgignore"])` with the literal path, not `_mod.RGIGNORE`, and asserts `is_full_suite is False` and `target_paths == (_mod.HOOKS_TESTS_DIR,)`. Its docstring reads `test_design_decision_files.py (HOOKS_TESTS_DIR) checks that a docs/design-decisions link to .rgignore resolves.`
   - Add `_mod.RGIGNORE` to `_EXACT_MATCH_LITERAL_PATH_CONSTANTS` directly after `_mod.ROOT_SETTINGS_JSON` (`:2541`).
3. `CHANGELOG.md` (M3). The bullet reads: "**`select-tests.py` now selects `claude/.claude/hooks/tests/` for a change to the repo-root `.rgignore`, instead of the full suite.** A test there checks that a design-decision doc's link to the file resolves."

Reuse: the `test_root_claude_md_change_selects_hooks_tests` shape for M2. `test_every_exact_match_literal_path_constant_exists_on_disk` and `TestCrossDomainReadCompleteness` already cover a new constant and row, so no new helper is needed.

Projected diff: ~15 lines across 3 files.

## Verification

1. **Red.** In the dispatch, add the `RGIGNORE` constant, then its list entry and the new test, without the row. The constant goes first because the exact-match list is built at import (row 9). Run `scripts/venv-run.sh pytest claude/.claude/scripts/tests/test_select_tests.py -k "rgignore or exact_match_literal or every_resolved_path"`. Expect:
   - exactly one failure, `test_rgignore_change_selects_hooks_tests`, with `is_full_suite` true and reason `unmatched-path`;
   - `test_every_exact_match_literal_path_constant_exists_on_disk` passing, because `.rgignore` is tracked (row 9);
   - every other selected test passing.

   A failure with any other reason means a predicate already matches `.rgignore` (row 2). Stop and report it to the session.
2. **Green.** Add the row and the header line, then rerun the same command. Expect every selected test to pass, `test_every_resolved_path_selects_a_target_covering_its_reading_test` included (row 16).
3. **Scoped suite.** Run `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py` and expect a pass. It selects the full suite on its own, because the diff touches `select-tests.py`, a `GLOBAL_TRIGGER_PATHS` member (`select-tests.py:567-571`). That is CLAUDE.md's first case, not a hand-widened run, and it includes the link test.
4. **Lint.** `scripts/venv-run.sh ruff check claude/.claude/` is clean.
5. **PR body** (the session writes it through `/pr-description`):
   - why the target is the hooks tree: the tests in row 1, the link test included;
   - why CI's `SKIP_REGEX` stays unchanged (rows 3, 5);
   - the step 1 failure output.

## Out of scope

- **Revising G1, enforcing it with a test, or closing its `PLANS_DIR` gap (row 7).** This design adds no empty target, so it neither relies on G1 nor touches the gap (row 6). Either fix for the gap revises a recorded invariant and needs its own plan: restating G1 with `PLANS_DIR` as a named exception, or a test that checks every exact-match empty-target path against `SKIP_REGEX` while exempting `PLANS_DIR`.
- **The "one file to revert" line in `plans-hidden-from-grep-not-deleted.md:9`.** The doc's own link already made a lone deletion fail the link test, and after this change the `RGIGNORE` constant, row, test and list entry join the revert (rows 1, 9). Correcting the line would edit a file outside the Ask and row 14. A revert that deletes only `.rgignore` fails its own CI run, which runs the full suite (row 4), so the line misleads no one silently.
- **A nested-path negative control for the new row.** The row is the same `p == CONSTANT` exact match as the `install.sh` and root `CLAUDE.md` rows, and their tests carry none (`test_select_tests.py:1493-1498,1547-1555`).
- **Rows for `.gitignore` or the other `SKIP_REGEX` files.** The Ask names `.rgignore` only. `.gitignore` stays pinned to the full suite by `test_unmatched_path_falls_open_to_full_suite`.
