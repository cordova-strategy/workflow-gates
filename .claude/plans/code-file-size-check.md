# Code-file size check (GH-1119 F2)

## Context

Add the repo-local pytest check that caps tracked `.py` and `.sh` files at 1,000 physical lines, with an exception table whose ceilings are exact in both directions, and close GH-1119.

Ask: GH-1119, section "F2 — The check" ("Only F2's PR closes this issue"). This session's rulings, each the option label the engineer selected, with the question it answered:

- "Back to exact, both directions (Recommended)" — to "Which ceiling semantics should F2 build?", asked after this session measured growth against shrink (figures below).
- "No per-file issues (Recommended)" — to "How should F2's exception table track split-pending files?"
- "#1015 governs (Recommended)" — to which of #1015 and #1396 governs the `claude/.claude/tests/helpers.py` row.
- "Confirm all three (Recommended)" — to confirming GH-1119's three plan defaults: physical-line counting; the failure message's content, remedy order and prohibitions; failing a row whose file is gone or whose stored size is at or under 1,000.
- "Second basis, verified in splits (Recommended)" — to "How should F2 treat the Read cap?"
- "Keep all five as recorded (Recommended)" — to what F2's rows say for the five F1 verdicts PR #1546 listed as judgment calls.
- "Exposure + append rule (Recommended)" — to "Should F2 record a recommended order for [splits]?"
- "Not required" — to "Does main require branches to be up to date before merging?"

**Why now.** GH-1119 has two parts. F1, the offender assessment, merged as PR #1546 (`docs/reports/2026-11-19-code-file-size-offenders/findings.md`, pinned at `ab85a627`). `docs/design-decisions/code-file-line-limit.md` says the check ships only after that assessment exists. Nothing enforces the limit yet, and offenders keep growing: PR #1546's body lists 13 offenders resized and 2 removed between the pin and `6cc9e053`.

**What the session's proposals behind those labels were.** The option descriptions were this session's wording, not the engineer's. They are recorded here as the proposals the labels accepted:

- Split-pending rows carry their seam, and an issue number only where one already exists. At the pin 5 rows name one (#1530, #1531, #1532, #1118, #1117). No new per-file issue is filed. This departs from `findings.md:136`, from `.claude/plans/code-file-size-splits.md:217` and `:419`, and from GH-1113's task-list line "Further files get an issue each from F1's 'split pending' verdicts." Editing GH-1113's task list is not part of this change and needs the engineer's separate go-ahead.
- The `helpers.py` row stays a structural exception citing #1015's gates.
- The decision record states reading a file whole in one default Read call as a second reason for the limit. Each later split PR shows that every new part returns from one default Read with no partial-view notice. The enforced check stays the line count only.
- The decision record gains a short paragraph on split order: exposure (size × 90-day commits) ranks candidates, and a split of a file every feature appends to must end the append pattern.

**Semantics history, so the decision record is corrected accurately.** The record rejects upward-only ceilings on the premise that this repo's existing length gates keep a stored ceiling that a shrunken file stays under (`docs/design-decisions/code-file-line-limit.md:43-48`). They store none: `_lib_staged_length_gate` compares the staged blob against the file's own previous version (`claude/.claude/hooks/_lib.sh:3235`). A prior session therefore proposed "growth-receipt" semantics, under which only a PR that grows an exception file edits the table, and the engineer agreed to switch. This session then measured at F1's pin and window, where 334 of 509 non-merge commits changed an offender's length. 325 of those grew an offender and 9 only shrank them. Growth-receipt would therefore have removed 9 table edits. With that figure the engineer selected exact both-direction ceilings again. The outcome matches the record's decision; its stated premise about the existing gates is still wrong and gets corrected.

**Measured inputs from this session.** Each was computed over this repository's own history at pin `ab85a627`, using the report's window and commit definitions, by throwaway scripts that reproduced the report's 334 and 509 before measuring anything else.

- 325 growth commits: 272 grew offenders only, and 53 grew one offender while shrinking another.
- Of the 325, 65 grew `claude/.claude/hooks/_lib.sh`, 45 grew `claude/.claude/tests/helpers.py`, and 89 grew either.
- 294 grew an offender other than the two files split since the pin. 262 grew an offender outside that pair and outside `_lib.sh`, `select-tests.py`, `test_select_tests.py` and `helpers.py`.
- 204 of the 325 growth PRs had an open interval (created to merged) overlapping another PR that grew the same offender, across 33 offenders. This is an upper bound on real collisions, because an open interval does not show when a branch first touched the file.
- In a throwaway repository, two same-base branches that each grew one file by a line and wrote the same new size merged cleanly, leaving the file at 1,202 lines against a stored 1201. Two branches that wrote different sizes conflicted on the table. Under exact ceilings the first case fails the check on the next run.

- In the same throwaway setup, two branches that edited different rows conflicted when the rows were on adjacent lines and merged cleanly when one or more unchanged lines separated them.

**Architect consult on the semantics.** The engineer asked whether the architect agreed with returning to exact ceilings. A `plan-architect` consult agreed, on its own judgment, and named costs the design must record. These are the consult's points, not engineer rulings:

- Growth-receipt's saving is larger per row than per commit. The 53 commits that grew one offender and shrank another would each also have skipped a row edit, so the floor is 62 row edits in the window (9 + 53, the consult's arithmetic over the figures above), not 9.
- The window mostly predates the split epic, so the shrink share will rise while splits land. The 325 was measured with no check in place, and the failure message's first remedy steers new code into new files.
- The 204 counts growth-against-growth overlaps only. Under exact ceilings a grow-against-shrink pair on one offender also conflicts on its row.
- A mismatch that reaches `main` fails every open PR's next run until a one-row fix lands, so the failure message must say what to do when the PR did not change the file.
- The load falls as splits delete rows, but not to zero. `_lib.sh` and `helpers.py` are structural exceptions, and 89 of the window's 509 commits grew one of them.
- The corrected decision record should reject growth-receipt on its own grounds (row conflicts act as a lock on concurrent length changes, no base logic, a table that shows current sizes, the small measured saving). The record's sentence that a shrunken file "keeps its old, larger ceiling" is the wrong part. Its parenthetical describing the existing gates' rule is accurate.
- The consult advised a table layout in which no row's size sits on a line adjacent to another row's size, and advised against requiring up-to-date branches or a merge queue to close the same-size clean merge.

**Evidence the design must account for.**

- The precedent check is `claude/.claude/hooks/tests/test_ticket_reference_discipline.py`. The decision record's Sources line gives its directory as `claude/.claude/scripts/tests/`, which does not exist. The precedent enumerates `git ls-files` under `claude`, `claude-skills` and `plugins` only, and its `select-tests.py` predicate `_is_py_source_under_claude_or_plugins` matches `.py` only. GH-1119 requires this check's predicate to match `.py` and `.sh` anywhere in the repo, which includes `scripts/`, `evals/` and root files such as `install.sh`.
- `claude/.claude/scripts/select-tests.py` (1,444 lines) and `claude/.claude/scripts/tests/test_select_tests.py` (3,898 lines) are themselves offenders, so this change's own edits to them move their rows.
- F1 measured 112 offenders of 685 tracked regular `.py`/`.sh` files, with symlinks excluded and physical lines counted as newline characters. The set has drifted since, so this change re-measures at its own base and again before merge.
- CI (`.github/workflows/tests.yml`) runs on `pull_request` and on pushes to `main`, with `fetch-depth: 0` and no `ref:` input, and has no `merge_group` trigger. `main`'s only required status check is `tests`.
- Open issue #1542 already tracks the redaction hook's scope gap in this checkout, so this change files nothing for it.

**Intended outcome.** A PR that pushes a tracked `.py` or `.sh` file past 1,000 lines, or changes the length of a file with an exception row without updating that row, fails `select-tests.py`'s scoped run locally and fails CI, with a message that names the remedy. The check counts tracked files, so a new file is counted locally only once it is staged. The decision record matches what ships.

## Approach

A new pytest module, `claude/.claude/tests/test_code_file_size.py`, counts the newline bytes of every tracked regular `.py` and `.sh` file. It fails when a file with no row is over 1,000 lines, or when a file with a row differs from that row's ceiling. The rows live in a TOML table at the repository root, `code-file-size-exceptions.toml`, populated from the check's own output and F1's verdicts. `select-tests.py` gains a supplementary-rules table that `main` applies after `select_pytest_targets`, so any changed `.py` or `.sh` path adds the check without counting as a match. `select_pytest_targets`'s own results and its full-suite fallback are unchanged. The decision record is corrected in place to match what ships.

**The check.** Each function below is a seam its controls call directly. The real-repository tests are thin wrappers over the same functions, so a control and the real test cannot exercise different code.
- `count_physical_lines(content: bytes) -> int` returns `content.count(b"\n")`, F1's unit and what `wc -l` prints (row 35). A final line with no newline is not counted, and U+2028 is not a line break.
- `parse_index_listing(raw: bytes) -> list[str]` parses `git ls-files -z --stage` output into the sorted counted paths.
  - A record is `<mode> <object> <stage>\t<path>`, records end in NUL, and each path is decoded with `os.fsdecode`.
  - A path is counted when it ends in `.py` or `.sh` and at least one of its entries has mode `100644` or `100755`. The mode filter mirrors F1's `BLOB_MODES`, so a symlink (`120000`) and a gitlink (`160000`) are not counted (rows 35, 70).
  - Each path appears once, so the up to three entries of an unmerged path collapse to one.
- `count_tracked_code_files(repo_root: Path) -> dict[str, int]` runs that listing in `repo_root` and counts the working-tree bytes of each parsed path whose working-tree file exists.
  - The working tree wins over the index. An unstaged edit is counted, so a commit made with `git add -p` can differ from what the local run counted.
  - An unstaged deletion is not counted, so a deleted file's row reads as not counted.
  - A new file counts once it is staged.
- `load_table(text: str) -> TableLoad` is the shape validator. It returns the rows and a list of problems, each naming its row ("The exception table" below).
- `evaluate(counts, rows) -> list[Violation]` applies the rules below. Each violation carries its kind, an `Enum`, plus the path, count and ceiling, and the list is sorted by path.
- `render(violations, rows) -> str` builds the failure message.
- `size_report(counts, table_text) -> str | None` is the size test's body. It returns `render`'s text, or one table-problem line when `load_table` reports any problem, or `None` when nothing fails.
- `fail_with_report(report: str | None) -> None` returns on `None` and otherwise calls `pytest.fail(report, pytrace=False)`. That prints the message verbatim. A bare `is None` assertion would show it through pytest's truncated repr (row 73).
- `count_tracked_code_files` runs git with `GIT_DIR`, `GIT_WORK_TREE`, `GIT_COMMON_DIR` and `GIT_INDEX_FILE` removed from the environment, because `claude/.claude/tests/` has no conftest that scrubs them (row 74).
- Two tests run against the real repository. The size test passes `size_report` over `count_tracked_code_files(REPO_ROOT)` and the table's text to `fail_with_report`. The shape test asserts that `load_table` reports no problem. The precedent parametrizes per file (row 39). That is set aside because a row whose file is gone has no per-file case, and after a sync the author needs one message listing every value to write.
- One module holds the functions, the real tests and the controls, so the selection names one file and no test imports from another test module.
- Location: `claude/.claude/tests/`, beside the other repo-wide checks (row 51). The epic plan placed it beside `test_ticket_reference_discipline.py` (`.claude/plans/code-file-size-splits.md:255`). That is set aside because the check is not about hooks, and a change to it would then select all of `HOOKS_TESTS_DIR`, which held 35 of F1's offenders (rows 31, 51).
- The module docstring has three parts:
  - one line stating what the check enforces;
  - one line saying a new file counts once staged;
  - citations of `docs/design-decisions/code-file-line-limit.md` and the table's path.

  It also satisfies the in-flight plan that probes for this check (row 44).
- The docs path stays a plain string literal, never a `REPO_ROOT` path chain, because the read-completeness scan resolves such chains (row 68).
- No code, comment or table text uses "F1" or "F2", or a ticket-prefixed identifier (row 43).
- The module imports `REPO_ROOT` and `init_git_repo` from `helpers` as a top-level module, and adds no `__init__.py` (row 40).

**Rules the size test applies to each file.** `evaluate` checks rule 4 first, then rule 2, then rule 3, so each path gets one violation at most.
1. No row, and over 1,000 lines: kind `no row`. A file at exactly 1,000 lines passes.
2. A row, and the file is at or under 1,000 lines: kind `under limit`. The line says to remove the row. It prints no `ceiling =` value and no growth remedies.
3. A row, and the count is over 1,000 and differs from the ceiling: kind `over ceiling` or `under ceiling`. The line prints the count as the value to write. Only `over ceiling` gets the growth remedies.
4. A row whose path is not a counted file: kind `not counted`. The line says the path is not a tracked regular `.py`/`.sh` file, and to remove the row, or to move it to the new path after a rename.

- Boundaries: a row of 1,001 at 1,001 lines passes, a row of 1,002 at 1,001 is `under ceiling`, and a row at 1,000 lines is `under limit` only.
- A row whose `ceiling` is 1,000 or less never reaches `evaluate`. `load_table` rejects it, and `size_report` returns the table problem instead.

Rules 2 and 4, and physical-line counting, are the defaults the engineer confirmed (row 9). Rule 3 in both directions is row 1.

**The failure message.** `render` returns one message, in this order. The additions beyond the content row 10 lists are row 77's.
- A fixed preface line. CI counts this branch merged with `main`, so merge `origin/main` and run the check again before writing any printed value. For a listed file this branch did not change, write nothing and follow the did-not-change procedure at the end.
- Per-file lines, one per violation, sorted by path in Python `str` order. Each names the path and its physical count, then the action for its kind:
  - `no row`: a paste-ready row skeleton. It holds the `["<path>"]` header, `ceiling = <N>`, `verdict = "split pending"`, and `seam` set to a placeholder that `load_table` rejects until it is replaced. It names the row the skeleton goes after in sorted order, or says it is the first row. One line under it says a file that cannot be split takes `verdict = "structural exception"` and a `reason` instead, and that the table header says when.
  - `over ceiling` and `under ceiling`: `ceiling = <N>`. On a structural-exception row, an `over ceiling` line also prints the row's `reason`.
  - `under limit` and `not counted`: the text in the rules above.
- A rename line, when a `no row` line and a `not counted` line both appear. It says a renamed file's row moves to its new path: change the header to the new path, write the ceiling printed for it, keep the row's other fields, and move the row to its sorted position. It adds that for a rename the skeleton's `seam` placeholder and the remedies below do not apply to that path. The growth remedies still print, because the check has no base and cannot tell a rename from a new file (row 20's first ground).
- A remedy block, when any line is growth (`no row` or `over ceiling`). It opens with a fixed heading line that begins "If this branch changed the file", then one numbered remedy per line, in this order:
  1. move the new code into a new module or test file;
  2. split the file along a named seam, such as a subcommand, a domain or a detector;
  3. add or raise the file's row in `code-file-size-exceptions.toml`, with a seam or a reason.

  When any `over ceiling` line is on a structural-exception row, remedies 1 and 2 add "unless the reason printed above rules it out".
- The prohibitions: no positional splits, such as a `_part2` file, and no fitting a file under the limit by deleting comments or joining lines (rows 9, 10).
- A did-not-change procedure, under its own fixed heading line, for a listed file this branch did not change. `render` has no base, so every message prints it, whatever kinds it holds:
  1. Run `git log --oneline origin/main..HEAD -- <path>` and `git status --short -- <path>`. When both print nothing, this branch did not change the file, and the mismatch came from `main`.
  2. Fetch `origin/main`, merge it into the branch, run the check again, and push. The push runs CI on the new merge. Re-running the failed job does not pick up `main` (row 60).
  3. If the line is still there, `main` itself fails. Look for the open fix with `gh pr list --state open --search 'in:title "code-file-size row fix"'`.
     - If one is open, check that it applies every line the check prints at `origin/main`'s tip, and push the missing ones to it. Open no second PR.
     - If none is open, open one PR titled exactly `code-file-size row fix`. It applies every line the check prints at `origin/main`'s tip: a printed value, a new row, or a removed row. A fix that leaves one line unfixed cannot pass `tests`.
     - Make no edit to the row in this branch (row 47).
  4. This PR stays red until that fix merges, because `tests` is required and only a human merges. Then repeat step 2.

  The same route covers two PRs that changed one file to the same new size and merged without a conflict (G2).

**The exception table.** It is TOML, read with stdlib `tomllib` (row 41). Each row is its own table under a quoted-path header line, followed by `ceiling`, `verdict`, and either `seam` with an optional `issue`, or `reason`. Shape only, with values from F1's pin:

```toml
["claude/.claude/hooks/tests/test_marker_script.py"]
ceiling = 7303
verdict = "split pending"
seam = "Test-class families following marker.sh's status and write halves: ..."
issue = 1530
```

- Layout, enforced by `load_table`:
  - each row is declared by its own `["<path>"]` line, never as an inline table or with dotted keys;
  - rows are sorted by path, in Python `str` order;
  - no string value spans lines.

  The later row's header line then sits between any two rows' `ceiling` lines, and no length change edits it. Edits to different rows therefore merge cleanly, and two edits to one row conflict (G2). Sorted rows make two branches that add different rows insert at different points instead of both appending at the end.
- `load_table` runs five stages and stops at the first that reports a problem, so a malformed header does not also report the nested keys it produced. `tomllib` parses an inline-table row, a dotted-key row and a `["<path>"]` row to the same value, so stages 3 and 4 read the raw text (row 54).
  1. Decode with `tomllib.loads`. A decode error, such as conflict markers or a path declared twice, is one problem. It carries the decoder's message and points at the header's conflict rule.
  2. Strings: a triple-quote delimiter (`"""` or `'''`) anywhere in the raw text is a problem, and so is a parsed string value holding a line-break character. The first rule covers a multi-line string whose parsed value holds no line break, such as one with a trimmed first newline or a line-ending backslash (row 75). The second covers a single-line string with an escaped `\n`, and its problem says the value holds a line break.
  3. Headers: the text is split on `\n` only, never with `str.splitlines()`, which also splits on U+2028. Every line whose first non-blank character is `[` must match `^\s*\[\s*"([^"\\]+)"\s*\]\s*(#.*)?$`. That accepts a double-quoted path with optional spaces inside the brackets and an optional trailing comment. Each other form is a problem naming its line:
     - a bare key such as `[install.sh]`, which `tomllib` reads as a table `install` holding `sh`; the problem says to quote the path, as `["install.sh"]`;
     - a literal-string header such as `['a.py']`; the problem says to use double quotes;
     - an array-of-tables header, or a dotted header such as `["a"."b"]`.

     A path holding `"` or `\` would need a TOML escape and cannot be a row. The repository has no such path.
  4. Rows: the list of header-line paths must equal the list of parsed top-level keys, with no path repeated. A parsed key with no header line was declared as an inline table or with dotted keys, and the problem says to give that row its own `["<path>"]` line. A header line with no parsed key is a problem naming its line. The header paths must be in Python `str` order, which is code-point order and matches `git ls-files` for UTF-8 paths. An out-of-order row is a problem naming the row it belongs after.
  5. Schema, per row:
     - The key set is closed.
     - `ceiling` is an `int`, not a `bool`, and is over 1,000.
     - `verdict` is exactly `split pending` or `structural exception`, F1's literals (row 37).
     - A split-pending row needs a non-empty `seam`, and may carry `issue`, a positive `int`.
     - A structural-exception row needs a non-empty `reason`, and takes no `issue`.
     - A `seam` or `reason` equal to the skeleton's placeholder is a problem.
- Header comment:
  - what the file is, and its fields;
  - how to choose a verdict, one line per literal, after findings.md's verdict rule (row 37);
  - that the table is the split backlog, ranked by exposure, with the recipe in the decision record;
  - the conflict rule: resolve conflicts in code files first, then keep either side of each table conflict, run the check, and write the values it prints (`.claude/plans/code-file-size-splits.md:247`);
  - the split rule: each new part of a split returns from one default Read call with no `PARTIAL view` notice, and a part that does not is split further, or the PR says why not (row 62);
  - pointers to the check, the decision record, and `docs/reports/2026-11-19-code-file-size-offenders/findings.md` for verdict rationale and the review bench's harness-closure files.
- Location: the repository root. That is not a stow package, and no domain rule matches it, so a row edit selects only the check, through its own rule. Under `claude/.claude/tests/`, every row edit would select the whole `CLAUDE_TESTS_DIR` domain (row 31). In F1's window, most commits changed an offender's length and would carry a row edit (334 of 509, findings.md's `ceiling_edit_load`).
- Set aside:
  - A Python literal in the test module. About 110 multi-line rows would put the module near its own limit. Ruff's 130-character line length would also wrap F1's longer seam cells (row 42). And as a `.py` file, every row added or removed would change the module's own size.
  - Pipe-separated rows, like `claude/.claude/hooks/config-keys.psv`. One row per line puts every row's size next to its neighbours', so concurrent edits to neighbouring rows conflict (G2).
  - JSON, like `claude/.claude/scripts/cursor-adapter/parity-exceptions.json`. It allows no header comment, and adding or removing the last entry edits the line before it for the comma.

**Populating the table.**
1. Write the check with a header-only table and run it. Its failure output lists every offender and its count: this branch's base, plus this branch's own edits.
2. Cross-check that list against F1's `wc -l` command (row 36).
3. For each offender F1 assessed, carry its verdict verbatim. Its cells map to fields as follows:
   - the Seams cell becomes `seam`;
   - a `#<digits>` last cell becomes `issue`;
   - a structural exception's reason becomes `reason`;
   - `proposed (not filed)` and `; closure-windows` are dropped (rows 5, 6, 38).

   The five judgment calls stay as recorded (row 13).
4. `claude/.claude/tests/helpers.py` keeps its structural-exception verdict. Its reason reads that #1015 declines decomposition until its data and mapping gates hold, and governs over #1396's proposal to decompose the file (rows 7, 8). It adds that a helper one test tree uses goes in that tree's local module, only if Verification step 0 finds that guidance in #1015 (row 65). The message prints this reason beside each `over ceiling` line for the file.
5. An offender F1 did not assess gets a verdict under F1's verdict rule, with a seam named from an outline (row 37). A seam counts only when parts can move without changing how the file is loaded, invoked or installed, so a file whose only seams would change that is a structural exception. The PR description lists each one for the engineer to correct.
6. An F1 offender no longer over 1,000 lines gets no row. The PR description lists each one.
7. A scratch script under `agent-reviews/` checks that each backticked seam symbol still occurs whole-word in its file. A miss goes in the PR description, and the seam is carried as recorded.
8. `select-tests.py` and `test_select_tests.py` take their sizes after this branch's edits, including after each review-fix round. The check prints the new value.
9. The final sync and value rewrite follow **Landing**. A new offender found then goes through step 5.

**Landing.**
- The final sync is the last act before the engineer's merge, and it repeats after every later push, review-fix rounds included:
  1. fetch, and merge the branch's own remote ref, so an update made on GitHub is in the local branch;
  2. merge `origin/main` into the branch, rather than rebasing, because a rebase needs a force-push the autonomous ask does not cover (row 67);
  3. run the check, and write every value it prints. A `no row` line goes through Populating step 5, and an `under limit` or `not counted` line through step 6. Either also updates the PR description's offender lists;
  4. push.
- The did-not-change procedure does not apply to this PR. Every row is its own, and `main` has no table, so the session writes the printed values.
- The PR description tells the merger to:
  1. update the branch from `main` with a merge commit, not a rebase, immediately before merging;
  2. wait for a green `tests` on the resulting commit. If a size line fails, the session runs the final sync above and pushes, and the merger waits again. A line other than a changed ceiling needs the session's judgment, not a one-value edit;
  3. merge promptly once it is green, as one squash commit.
- It also states two consequences (G1):
  - a PR that merges after that green run and changes an offender's length leaves `main` failing, along with each open PR that has a changed path outside `tests.yml`'s skip list (row 59), until a one-row fix lands by the message's route;
  - an open PR that changes an offender's length fails its next run until it edits that row.
- It names the rollback unit: revert the squash commit. If the revert conflicts, remove these together: the check module, the table, `SUPPLEMENTARY_RULES` with its constants and the `main` call that applies it, the table's `CROSS_DOMAIN_EXCEPTIONS` row, and this branch's `test_select_tests.py` additions. Removing only some of them fails CI, through the existence tests over `_FILE_TARGETS` and `_EXACT_MATCH_LITERAL_PATH_CONSTANTS` (row 58).

**PR description.** It carries `Fixes GH-1119`, the Landing items above, and these:
- Needs engineer action. This change performs none of them:
  - GH-1113's task-list line "Further files get an issue each from F1's 'split pending' verdicts", which contradicts the record, and its unchecked box for GH-1119 (row 6);
  - a comment on #1396 pointing at the `helpers.py` row, whose reason says #1015 governs (rows 7, 8).
- Record text that is this session's wording, for the engineer to correct: the reason the record gives for filing no per-file issue (row 64).
- Three departures from GH-1119's F2 text, one line each with its reason (row 71):
  - the check lives in `claude/.claude/tests/`, not beside `test_ticket_reference_discipline.py`;
  - it is selected through a supplementary-rules table that `main` applies, not a `select-tests.py` exception;
  - split-pending rows carry `seam` where F2 asks every row for a non-empty reason.
- The new offenders with their verdicts, the dropped offenders and any seam misses (Verification step 3).
- The decision record's correction, which the record itself does not narrate (row 25).
- The GitHub documentation pages behind rows 60 and 61 (Verification step 0).

**`select-tests.py`.**
- New constants `CODE_FILE_SIZE_TEST_PATH` and `CODE_FILE_SIZE_EXCEPTIONS_TOML`, and a predicate `_is_code_file_change` that matches any path ending in `.py` or `.sh`.
- A new table, `SUPPLEMENTARY_RULES`, in the same `(predicate, targets)` shape. Its one row is `(_is_code_file_change, (CODE_FILE_SIZE_TEST_PATH,))`.
- A new function, `add_supplementary_targets(selection, changed_paths) -> SelectionResult`:
  - A full-suite selection returns unchanged. Every rule-table target sits under a full-suite root, so the full suite already runs it (row 57).
  - Otherwise it adds the targets of every supplementary rule that matches a changed path. The result stays sorted, and its reason stays `domain-selected`.
  - `main` applies it to `select_pytest_targets`'s result, before `resolve_target_paths` (row 56). The call sits in the branch where `changed_paths` is bound, not on the `GitDiffUnavailable` path, which `test_git_diff_unavailable_falls_back_to_full_suite` pins. `select_pytest_targets`'s docstring gains one line saying `main` adds these targets.
- A `CROSS_DOMAIN_EXCEPTIONS` row maps the table's path to `CODE_FILE_SIZE_TEST_PATH`. It counts as a match, so a table-only change selects just the check, the table's only reader.
- Set aside:
  - The supplementary loop inside `select_pytest_targets`. Its per-path results would then gain the check for every `.py` or `.sh` path. That changes about 45 to 51 exact-set assertions, four tuple-equality sites and two exact-argv sites, many needing re-wrapping at ruff's 130 columns (rows 42, 55). Each of those assertions guards one domain mapping, and every later mapping test for a `.py` or `.sh` path would have to restate the check.
  - The same loop, with a shared test helper that adds the check to each expected set. It still edits the same 45 to 51 sites, and every later mapping test must still remember the helper. The composition step states the claim in one place instead.
  - A `CROSS_DOMAIN_EXCEPTIONS` row for every `.py`/`.sh` path. Any match there marks the path matched (row 29). A root `conftest.py` and a plugin `.sh` would then stop falling open, breaking both pinned tests and the README's fail-open promise (row 30).
  - An inline special case in `main`. The table-fidelity tests iterate the rule tables, so a target outside every table escapes them (row 32).
- `test_select_tests.py`:
  - `CODE_FILE_SIZE_TEST_PATH` joins `_FILE_TARGETS`, and `CODE_FILE_SIZE_EXCEPTIONS_TOML` joins `_EXACT_MATCH_LITERAL_PATH_CONSTANTS` (row 58).
  - The three target collectors, at `:2232`, `:2736-2742` and `:2762`, add `SUPPLEMENTARY_RULES`.
  - The exact-argv assertions at `:3192` and `:3281` gain `CODE_FILE_SIZE_TEST_PATH`, because `main` now adds it. They are the only existing assertions that change (row 55).
  - New cases, the one place the supplementary claim is asserted:
    - a table-driven case over `add_supplementary_targets(select_pytest_targets(paths), paths)`, in which a domain-selected `.py` path, `install.sh`, a top-level `scripts/` shell path and an `evals/` `.py` path that a domain rule maps each gain the check. An unmapped `evals/` path falls open and gains nothing;
    - a domain-selected `.md` path does not gain it;
    - a full-suite selection, from a root-level `tool.py`, passes through unchanged with reason `unmatched-path`, beside the two existing fall-open pins;
    - `select_pytest_targets` on the table's path selects exactly the check. This case is the only guard on that row, because the read-completeness test skips a path that falls open (row 34).

**The decision record, `docs/design-decisions/code-file-line-limit.md`.** Every edit is made in place, with no supersession line. `.claude/rules/design-decisions.md` reserves that line for a decision a later one overturns. Here the decision stands and only its reasoning is corrected (row 25). The text carries no "previously claimed" framing, and the PR description and commit message record the correction.
- `:14-17`: the precedent scans tracked `.py`/`.sh` files under `claude/`, `claude-skills/` and `plugins/`, not the whole repository (row 23). Add this check's path, the table's path, and that the check covers every tracked `.py` and `.sh` file.
- `:31-34`, rewritten to claim only what the one sample supports (rows 11, 12, 63):
  - Reading a file whole in one call becomes a second basis for the limit, still with no evidence of where defects start.
  - The Read tool caps one call by tokens, not lines (G3).
  - One measured file returned 956 of its 1,935 lines from one default Read call. A shorter file is more likely to fit, but the limit does not guarantee a whole read.
  - Each split PR shows that every new part returns from one default Read call with no `PARTIAL view` notice. A part that does not is split further, or the PR says why not (row 62).
  - The check itself counts lines only.
  - The `REFERENCES.md` citation goes on one line (row 24).
- `:36-48`:
  - Keep the opening rule and the unbounded-grandfather rejection. Extend `_lib.sh`'s growth with 3,554 lines when this decision was recorded and 6,233 at the assessment's pin (findings.md:170).
  - A stored ceiling that only fails growth lets a shrunken file keep its old ceiling, so later growth spends the slack. This is the existing objection, now attributed to the design it fits.
  - The existing length gates store no ceiling. They deny when NEW > LIMIT and NEW > OLD, where OLD is the file's previous version, so a shrink leaves them no slack (row 21).
  - Adapted here, only a PR that grows an exception file would edit its row. That is rejected on four grounds (row 20):
    - the check would need the PR's base to tell growth from shrinkage;
    - exact rows make every pair of PRs that change one file's length conflict on its row, so the row acts as a lock, where base-relative rows lock only growth against growth;
    - the table keeps showing current sizes;
    - the saving is small. In the assessment's window, 9 of the 334 commits that changed an offender's length only shrank offenders, and 53 more shrank one while growing another, a floor of 62 row edits. The citation is this plan's Context (row 19).
  - The cost of exact ceilings, beside that saving, from the same window (row 19):
    - 204 of the 325 growth PRs had an open interval overlapping another PR that grew the same offender, across 33 offenders. That is an upper bound on row conflicts, because an open interval does not show when a branch first touched the file.
    - 89 of the window's 509 commits grew `_lib.sh` or `helpers.py`, two structural rows that splits do not delete.
    - One line gives the method: the assessment's window and commit definitions, each commit's added and deleted lines per offender, and each growth PR's created-to-merged interval.
    - The window predates the splits, so the shrink share will rise as they land.
  - The residual: two PRs that change one file to the same new size merge cleanly and leave it off its row. `main`'s next run then fails. So does the next run of each open PR with a changed path outside `tests.yml`'s skip list (row 59). Both stay red until a fix merges by the failure message's route. How often this happens is unmeasured. Requiring up-to-date branches or a merge queue is not adopted.
  - Split-pending rows carry an issue only where one exists, and no per-file issue is filed (rows 5, 6). The table is the split backlog. Each row already names its file, its seam and, because ceilings are exact, its current size, which a per-file issue would copy and let go stale (row 64). A row's `issue` names the issue that owns its split, and a row without one has no owner until a PR takes it up.
- A new **Split order.** paragraph (rows 15, 16, 66):
  - Exposure, a file's physical lines times its 90-day commits, ranks split-pending files.
  - The assessment's figures are frozen at its pin, so a re-rank recomputes both. A row's `ceiling` is its physical count. Its 90-day commits are its non-merge commits in the 90 days before HEAD's committer date, following renames, which `git log --follow --no-merges --since=<that date> --format=%h -- <path>` lists. The definition is findings.md's "Window and commits".
  - A split of a file that every feature appends to must also end that append pattern.
- Revisit, first bullet (`:61-63`), reworded as settled: the assessment found 112 offenders of 685 tracked files, 89 of them test code, and the limit stands (rows 69, 76). The second bullet is unchanged, and no bullet is added for the table (row 78).
- Sources:
  - `:78` becomes `claude/.claude/hooks/tests/test_ticket_reference_discipline.py` (row 23).
  - `:79` cites findings.md for `_lib.sh`'s size at the pin, and names `_lib_staged_length_gate` for the gates' rule.
  - `:80` gains a clause: the epic plan's per-file-issue lines and its premise about the existing gates are superseded by this record.
  - `:81` describes the citation as the second basis's measurement, not a feasibility coincidence.
  - Add findings.md, and this plan's Context for the growth, shrink and overlap figures.

**Two sibling texts.**
- `claude-skills/skills/code-review/REFERENCES.md:218-221` cites the record "as a feasibility coincidence", which the second basis contradicts (row 26). It becomes one sentence: the record cites this measurement.
- `findings.md:136` instructs a future actor to file the proposed issues after merge. `docs/reports/README.md` lets such an instruction be marked superseded in place, since leaving it unmarked reads as a live obligation (row 27). One dated superseded line cites the decision record. No finding, table or figure changes.

**The epic plan is not edited.** Lines 257 and 423 carry the wrong premise, and lines 217 and 419 assume per-file issues. All four are that merged plan's record of its reasoning, which `CLAUDE.md`'s Axis 3 decision test keeps read-only. A modified plan file would also join this branch's plan-review set (row 28). The corrected decision record is the single current statement.

**Tests of the check**, in the same module:
- Vacuity guard. The real corpus is non-empty, holds both suffixes, and holds a path outside `claude/`, `claude-skills/` and `plugins/`, which proves the repo-wide reach the precedent lacks.
- Counting controls, on `count_physical_lines`:
  - `b"a\nb"` counts 1;
  - CRLF counts once per `\n`;
  - U+2028 adds no line;
  - empty content counts 0.
- Parser controls, on canned `parse_index_listing` input:
  - a `100755` `.sh` entry is included;
  - `120000` and `160000` entries are excluded;
  - three unmerged entries, stages 1 to 3, for one path yield that path once;
  - a path with a space and a non-ASCII path come back intact;
  - a `.txt` entry is excluded.
- Enumeration controls, on `count_tracked_code_files` over a throwaway repository built with `init_git_repo`:
  - included: a nested `.sh` file, and a new file once staged;
  - excluded: a tracked symlink to a `.py` file, an untracked `.py` file, and a tracked `.sh` file deleted from the working tree;
  - a tracked file edited without staging counts its working-tree lines;
  - a path left unmerged by a conflicting merge is counted once.

  The controls that commit or merge build their environment with `helpers.isolated_git_env`, so a contributor's global git config does not reach them (row 74).
- Rule controls, asserting on `evaluate`'s violations over synthetic counts and rows:
  - with no row, 1,000 lines passes and 1,001 is `no row`;
  - a row of 1,001 at 1,001 passes;
  - a row of 1,002 at 1,001 is `under ceiling`, with count 1,001;
  - a row of 1,001 at 1,002 is `over ceiling`;
  - a row at 1,000 lines is `under limit`, and nothing else;
  - a row whose path is not counted is `not counted`;
  - two violations from out-of-order input come back sorted by path.
- Message controls, asserting on `render`'s text:
  - the remedy block is found by its heading line and parsed by line, and its lines numbered 1 to 3 carry the three remedies in order. The did-not-change procedure's own numbering cannot satisfy it, and a swapped order fails it;
  - both prohibitions appear, and the preface line and the remedy heading's "If this branch changed the file" appear by their fixed text;
  - the did-not-change procedure carries its `git log` and `gh pr list` commands, the fixed fix-PR title, and step 3's "every line the check prints" wording. A message holding only an `under limit` line still prints it;
  - the rename line carries its sorted-position clause and its clause that the placeholder and remedies do not apply;
  - a `no row` skeleton, with its placeholder replaced and inserted after the row it names, makes `load_table` report no problem. With the placeholder left in, `load_table` rejects it;
  - an `over ceiling` line on a structural-exception row prints the row's `reason` and qualifies remedies 1 and 2, and one on a split-pending row does not;
  - a `no row` line and a `not counted` line together add the rename line once, and either alone does not;
  - an `under limit` line prints no `ceiling =` value and no remedy block;
  - a `not counted` line says "not a tracked regular `.py`/`.sh` file".
- Shape controls, on `load_table` over text:
  - accepted: a header with a trailing comment, a header with spaces inside its brackets, a non-ASCII path, a path with a space, and a trailing comment holding U+2028 followed by header-shaped text, which adds no header;
  - rejected, each with a problem naming its row: an inline-table row, a dotted-key row, a bare `[install.sh]` header whose problem says to quote the path, a literal-string header, an array-of-tables header, a single-line string with an escaped `\n`, a triple-quoted string whose first newline is trimmed, a triple-quoted string continued with a line-ending backslash, rows out of order whose problem names the row it belongs after, and each schema rule's violation, `ceiling = true`, a missing `ceiling` and `ceiling = 1000` included;
  - conflict-marker text and a path declared twice each give one decode problem that points at the header's conflict rule.
- `size_report` controls, over synthetic counts and table text:
  - conflicted text, a missing `ceiling` and `ceiling = true` each return one table-problem line, raise nothing, and produce no rule line;
  - counts that all match their rows return `None`;
  - one mismatched row returns text holding that path and the printed value.
- Reporting control: `fail_with_report` on a multi-line report fails with exactly that text, and on `None` returns.
- Perturbation control, in memory over the real counts. Its baseline is an exact row, `{path: count}`, for every counted path over 1,000 lines, so it does not depend on the real table and runs with a header-only one. It first asserts that the baseline is non-empty and that `evaluate` returns nothing for it. `Violation` compares by value over kind, path, count and ceiling. Each perturbation of the baseline's first path in sorted order then yields exactly one violation, asserted in full:
  - lowering its ceiling by one gives `over ceiling`, with that lowered ceiling;
  - dropping its row gives `no row`;
  - adding a row for a path no file has gives `not counted`, naming that added path.

  Verification step 4 stays as first-run evidence.

**Assumption ledger**

**Root:** Nothing enforces the 1,000-line limit on tracked `.py` and `.sh` files, so offenders keep growing. This plan adds the check and its populated exception table, keeps scoped local runs selecting the check, and corrects the decision record to match. It closes GH-1119.

**Givens:**
- G1. Other PRs merge to `main` while this branch is open and after it merges, and they change offender sizes. Reason: other sessions own those branches, and branch protection is a GitHub setting no repository artifact controls. Out of scope says why this plan adds no up-to-date requirement. Row 17 records the setting. `[verified: Context, "Why now" — PR #1546's body lists 13 offenders resized and 2 removed between the pin and 6cc9e053]`
- G2. Git's three-way merge conflicts when both sides change the same or adjacent lines. It merges cleanly when an unchanged line separates the changes, and it merges an identical change on both sides with no conflict. Reason: this is git's merge algorithm. `[verified: Context, "Measured inputs" — this session's throwaway-repository merge tests]`
- G3. The Read tool caps one call by tokens, not lines. Reason: harness behavior. `[verified: claude-skills/skills/code-review/REFERENCES.md:194-216]`
- G4. The repository is public, and this plan file ships in the PR. Reason: visibility is a GitHub setting. `[verified: CLAUDE.md, opening paragraph and "Plans in this repo affect all stow users"]`

**Mechanisms:**
- M1 — One check module in `claude/.claude/tests/`, built from named functions: the line counter, the index-listing parser, the enumerator taking `repo_root`, the table loader, the evaluator returning structured violations, the renderer, and the size test's body. The two real tests wrap them. `anchors: root, row9, row35, row39, row40, row43, row44, row51, row68, row70, row73, row74`
- M2 — A root-level TOML table, one `["<path>"]` table per row, sorted by path, with a closed schema, validated from its text in five stages. It is heavier than an in-module literal. The Approach gives three lighter primitives and why each fails. `anchors: G2, row1, row5, row6, row31, row37, row41, row42, row54, row75`
- M3 — Row rules with a fixed precedence: no row over 1,000 fails, a row must equal the count, and a row at or under 1,000 or for an uncounted path fails. `anchors: row1, row2, row3, row9`
- M4 — One failure message: per-file lines with a row skeleton or a value, the rename line, the remedy block qualified for structural rows, the prohibitions, and the did-not-change procedure. `anchors: G1, G2, row9, row10, row20, row47, row59, row60, row61, row77`
- M5 — `SUPPLEMENTARY_RULES`, applied by `add_supplementary_targets` in `main` after `select_pytest_targets`, plus one `CROSS_DOMAIN_EXCEPTIONS` row for the table. It is heavier than one more `CROSS_DOMAIN_EXCEPTIONS` row. The Approach gives the lighter primitives, the in-function placement's churn, and why each fails. `anchors: root, row29, row30, row31, row32, row33, row55, row56, row57, row58`
- M6 — Population from the check's own output, F1's verdicts carried verbatim, and drift in the PR description. `anchors: G1, row4, row5, row7, row8, row13, row36, row37, row38, row48, row49, row65`
- M7 — Decision-record correction in place with no supersession line, plus the `REFERENCES.md` and `findings.md:136` sibling edits. `anchors: row11, row12, row15, row16, row19, row20, row21, row22, row23, row24, row25, row26, row27, row50, row52, row59, row62, row63, row64, row66, row69, row76, row78`
- M8 — The epic plan stays unedited. `anchors: row28`
- M9 — The check's own tests: the vacuity guard; the counting, parser, enumeration, rule, message, shape and table-problem controls; the perturbation control; and the table row's selection case. `anchors: row34, row35, row39, row40, row41, row54, row70`
- M10 — Three dispatches: the check and its selection; the population; the docs. Dispatches 1 and 3 neither stage nor commit. `anchors: row33, row46, row53, row72`
- M11 — Landing: a merge-based final sync as the last act before the merge, the merger's steps, one squash commit, and the rollback unit. `anchors: G1, row17, row45, row58, row59, row67`
- M12 — The PR description's engineer-action list and the three departures from GH-1119's F2 text. `anchors: row6, row7, row8, row10, row69, row71`

**Assumptions:**
1. `[engineer-verified: "Back to exact, both directions (Recommended)"]` The label answered "Which ceiling semantics should F2 build?". The tag covers one point: a row passes only when its file's physical count equals its ceiling, so a shrink lowers the row.
2. Earlier rulings set the limit at 1,000 lines for production code and for tests. `[verified: .claude/plans/code-file-size-splits.md:549-550, rows 60 and 61]`
3. An earlier ruling already chose both-direction ceilings, and row 1 returns to it. `[verified: .claude/plans/code-file-size-splits.md:551, row 62]`
4. The earlier timing condition, no limit before an offender assessment exists, is met, because the assessment merged. `[verified: .claude/plans/code-file-size-splits.md:518, row 45; docs/reports/2026-11-19-code-file-size-offenders/findings.md:1-4]`
5. `[engineer-verified: "No per-file issues (Recommended)"]` The label answered "How should F2's exception table track split-pending files?".
6. `[unverified]` The proposal behind row 5's label, Context's first proposal bullet, was the dispatching session's. This plan adopts it.
7. `[engineer-verified: "#1015 governs (Recommended)"]` The label answered which of #1015 and #1396 governs the `claude/.claude/tests/helpers.py` row.
8. `[unverified]` The proposal behind row 7's label, Context's second proposal bullet, was the dispatching session's. This plan adopts it.
9. `[engineer-verified: "Confirm all three (Recommended)"]` The label confirmed three plan defaults:
   - physical-line counting;
   - the failure message's content, remedy order and prohibitions;
   - failing a row whose file is gone or whose stored size is at or under 1,000.
10. Those defaults' content: the message prints the file, its count, and the value to write or "remove the row", then lists the three remedies in order, and forbids positional splits and fitting by deleting comments or joining lines. `[verified: .claude/plans/code-file-size-splits.md:243-254, :552-555]` That GH-1119's own F2 section states the same is `[unverified — relayed: the round-1 staff-product-engineer review read the issue and reports a match on message content, remedy order and prohibitions; the issue was not read by this architect]`. Verification step 0 settles it.
11. `[engineer-verified: "Second basis, verified in splits (Recommended)"]` The label answered "How should F2 treat the Read cap?".
12. `[unverified]` The proposal behind row 11's label, Context's third proposal bullet, was the dispatching session's. This plan adopts it.
13. `[engineer-verified: "Keep all five as recorded (Recommended)"]` The label answered what F2's rows say for the five F1 verdicts PR #1546 listed as judgment calls. Which five they are is `[unverified — PR #1546's body was not read by this architect]`. Step 3 of the population carries every F1 verdict unchanged, so the result does not depend on which five.
14. F1's verdict for `helpers.py` is already a structural exception, and its reason names both issues and leaves the ruling open. `[verified: findings.md:70, :171]`
15. `[engineer-verified: "Exposure + append rule (Recommended)"]` The label answered "Should F2 record a recommended order for [splits]?".
16. `[unverified]` The proposal behind row 15's label, Context's fourth proposal bullet, was the dispatching session's. This plan adopts it.
17. `[engineer-verified: "Not required"]` The label answered "Does main require branches to be up to date before merging?". The tag covers the current setting only.
18. `[engineer-verified: "Also measure PR concurrency"]` The label answered whether to run measurements before finalising the plan. The tag covers that the PR-overlap measurement was run.
19. The figures in Context's "Measured inputs": 325 growth and 9 shrink-only commits of 334, 53 mixed, 204 overlapping PRs, and the merge tests. `[verified: Context — computed by the dispatching session's scratch scripts after reproducing findings.md's 334 and 509; not rerun by this architect]`
20. `[unverified]` The architect consult's points, recorded in Context, are recommendations, not engineer rulings. This plan adopts them:
    - reject growth-receipt on its own four grounds;
    - give the message a route for a file the PR did not change;
    - put no row's size on a line adjacent to another row's size;
    - require neither up-to-date branches nor a merge queue.
21. The existing length gates store no ceiling. They compare the staged blob against the file's previous version and deny only when NEW > LIMIT and NEW > OLD. `[verified: claude/.claude/hooks/_lib.sh:3115-3118, :3233-3240]`
22. The decision record's `:43-48` describes the gates' rule accurately but claims a shrunken file "keeps its old, larger ceiling" under it, which row 21 contradicts. `[verified: docs/design-decisions/code-file-line-limit.md:43-48]`
23. The record says the precedent scans "every tracked `.py`/`.sh` file in this repo" and gives its path under `claude/.claude/scripts/tests/`. The precedent lives under `claude/.claude/hooks/tests/` and enumerates `claude`, `claude-skills` and `plugins` only. `[verified: code-file-line-limit.md:14-17, :78; test_ticket_reference_discipline.py:36]`
24. The record's `REFERENCES.md` citation wraps between `:32` and `:33`, and the citation rule requires one line. `[verified: code-file-line-limit.md:32-33; .claude/rules/citation-grammar.md]` Whether `test_skill_citation_grammar.py` scans `docs/design-decisions/` is `[unverified]`.
25. The supersession line marks a decision a later one overturns. Durable docs carry no "used to be" framing. `[verified: .claude/rules/design-decisions.md:28-32; CLAUDE.md § "Durable text"]`
26. `REFERENCES.md` describes the record's use of its measurement as "a feasibility coincidence, not a quality threshold". `[verified: claude-skills/skills/code-review/REFERENCES.md:218-221]`
27. A merged report's one permitted edit is a Status section, plus a superseded mark on an instruction aimed at a future actor. findings.md:136 is such an instruction. `[verified: docs/reports/README.md:8-14; findings.md:136-140]`
28. A plan file is provenance for the change it gated. Axis 3 keeps a text that records something that happened read-only. A modified file under `.claude/plans/` joins the plan-review gate's plan set. `[verified: claude-skills/skills/plan-it/SKILL.md:17; CLAUDE.md § "Scope discipline"; README.md:185]`
29. In `select_pytest_targets`, any `DOMAIN_RULES` or `CROSS_DOMAIN_EXCEPTIONS` match marks a path matched, and only an unmatched path falls open to the full suite. `[verified: claude/.claude/scripts/select-tests.py:1089-1106]`
30. Two tests pin the fallback: a root `conftest.py` and `plugins/npm-semver/scripts/check.sh` must reach `unmatched-path`. The README promises that any change select-tests cannot map with confidence fails open. `[verified: claude/.claude/scripts/tests/test_select_tests.py:1763-1769, :1817-1825; README.md:574]`
31. `HOOKS_DIR` selects `HOOKS_TESTS_DIR`, and `CLAUDE_TESTS_DIR` selects itself. A root path matches no domain rule unless named, so an unnamed root file falls open. `[verified: select-tests.py:736-749; test_select_tests.py:1296]`
32. The fidelity tests iterate `DOMAIN_RULES` and `CROSS_DOMAIN_EXCEPTIONS`, and keep a list of file-naming targets. `[verified: test_select_tests.py:2232, :2565-2570, :2738-2740, :2762]`
33. `select-tests.py` is a global trigger, so this branch's scoped run selects the full suite. `[verified: select-tests.py:562-566]`
34. `TestCrossDomainReadCompleteness` resolves module-level path constants rooted at `__file__` or a `helpers` constant, and skips any candidate whose selection falls open. It therefore does not require the table's `CROSS_DOMAIN_EXCEPTIONS` row. Without the row the table's path falls open and is skipped, and with it the test checks only the row's target. `[verified: select-tests.py:751-759; test_select_tests.py:385-397]` The new case that the table's path selects exactly the check is the row's only guard.
35. F1's unit is the newline count, over tracked regular files with modes `100644` and `100755`, with symlinks excluded. `[verified: findings.md:14, :98, :366, :385-396, :523]`
36. F1's cross-check command is `git ls-files -z -- '*.py' '*.sh' | xargs -0 wc -l` filtered above 1,000 and sorted. `[verified: findings.md:573]`
37. F1's verdict rule, its cell rules and its two verdict literals. `[verified: findings.md:117-132]`
38. The harness-closure windows and the four closure offenders are recorded in findings.md. `[verified: findings.md:142-152]`
39. The precedent's shape: `REPO_ROOT` from `parents[4]`, `git ls-files` under three roots, a module-level corpus, and a non-empty corpus guard. `[verified: test_ticket_reference_discipline.py:28, :34-65]`
40. `helpers.py` provides `REPO_ROOT`, `init_git_repo` and `init_git_repo_with_commit`. `claude/.claude/tests/` stays unpackaged, and `helpers` is imported as a top-level module. `[verified: claude/.claude/tests/helpers.py:32, :1477-1500; .claude/rules/test-tree-packaging.md]`
41. The repository targets Python 3.14, so `tomllib` is in the standard library, and tests already use it. `[verified: pyproject.toml:3; claude/.claude/tests/test_pytest_collection_config.py:106]` Its behaviour on the row forms is row 54.
42. Ruff runs the `E` rules with a 130-character line length. `[verified: pyproject.toml:2, :6]`
43. The ticket-reference scan forbids ticket-prefixed identifiers and phase labels in `.py` files. Durable text forbids PR-defined labels. `[verified: test_ticket_reference_discipline.py:1-18; CLAUDE.md § "Durable text"]`
44. An in-flight plan probes for this check with a Grep for `code-file-line-limit` over `**/*.py`, and needs to name the table. `[verified: .claude/plans/cli-phase-and-test-placement-rule.md:483, :552]`
45. CI runs on `pull_request` and on pushes to `main`, with `fetch-depth: 0` and no `ref:`, and `tests` is `main`'s only required check. `[verified: Context, "Evidence the design must account for", from this session's exploration of .github/workflows/tests.yml; not reopened]`
46. A commit that brings the branch's diff to 400 or more changed lines outside `.claude/plans/` needs the engineer's `Proceed anyway`. `[verified: README.md:200]`
47. A check that also fails at the merge-base is pre-existing drift: sync if the base fixed it, and never edit an unrelated file. `[verified: CLAUDE.md § "Engineering Judgment", "Prove your change caused a failing check"]`
48. Since the pin, `test_skills.py` fell to 936 lines, `test_cursor_adapter_shim.py` was split, and 13 offenders were resized. `[verified: Context, from PR #1546's body; not reopened]`
49. `[unverified — relayed by the dispatching session]` Issue #1117's body says every PR that moves code out of `_lib.sh` must lower its ceiling once this check lands. Exact ceilings enforce that with no further mechanism.
50. The redaction hook's content scans are inert in this checkout, and #1542 tracks that gap. `[verified: Context; .claude/plans/f1-offender-assessment.md:282]` Every new figure passes the composition check before publishing. `[verified: docs/private-project-redaction.md:316-331]`
51. `claude/.claude/tests/` holds repo-wide checks such as `test_ci_path_filter.py`, `test_ci_workflow_gates.py` and `test_pytest_collection_config.py`. `claude/.claude/hooks/tests/` held 35 of F1's offenders. `[verified: Glob of claude/.claude/tests/; .claude/plans/f1-offender-assessment.md:240]`
52. `[engineer-verified: "Include both (Recommended)"]` The label answered whether this change includes two edits GH-1119's F2 section does not name: `claude-skills/skills/code-review/REFERENCES.md:218-221`, and one dated superseded line at findings.md:136.
53. `[engineer-verified: "Proceed anyway"]` The label answered "This plan projects about 1,100 changed lines (an estimate; threshold 400). Split into smaller PRs now, or proceed?".
54. `tomllib` parses `"a.py" = { ceiling = 1001 }`, `"a.py".ceiling = 1001` and a `["a.py"]` table holding `ceiling = 1001` to the same value. It reads a bare `[install.sh]` header as a table `install` holding `sh`. It raises `TOMLDecodeError` on conflict markers and on a path declared twice. `[verified: relayed — round-1 staff-sdet R2 and staff-platform-engineer R4, scratch-directory probes; not rerun by this architect]` The shape controls check each again.
55. Adding the target inside `select_pytest_targets` would change about 45 to 51 exact-set assertions on `target_paths`, tuple-equality sites at `test_select_tests.py:1203, :1215, :1227, :1498`, and the exact-argv assertions at `:3192` and `:3281`. `[verified: relayed — round-1 staff-sdet R4, a static AST scan; not rerun by this architect]` Applying it in `main` changes only `:3192` and `:3281`. The `:3317` case keeps its argv because `CLAUDE_TESTS_DIR` already covers the check, and the other `main` tests that pass a `.py` path assert on stderr text or call order. `[verified: test_select_tests.py:3140-3373, :3385-3405, :3842-3867]`
56. `main` calls `select_pytest_targets` once, between `compute_changed_paths` and `resolve_target_paths`. The only caller outside `select-tests.py` and its tests passes `.md` paths. `[verified: select-tests.py:1385-1393; test_transcript_routing_guard_capture.py:5280-5287]`
57. `test_every_domain_target_sits_under_a_full_suite_root` requires every rule-table target to sit under a `FULL_SUITE_TARGETS` root, and `claude/.claude/` is one. `[verified: test_select_tests.py:2756-2764; select-tests.py:553]`
58. `_EXACT_MATCH_LITERAL_PATH_CONSTANTS` lists every constant behind an exact-match predicate, so a rename that leaves the predicate dead fails a test. `[verified: test_select_tests.py:2511-2563]`
59. `tests.yml` skips pytest for a PR whose every changed path matches `SKIP_REGEX`: `LICENSE`, `CHANGELOG.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md` and `CONTRIBUTING.md`. `[verified: .github/workflows/tests.yml:83-86]`
60. `[unverified]` Re-running a failed `pull_request` job reuses the original run's merge commit, so it does not pick up a later `main`, while a push to the branch does. It stays unverified until Verification step 0 confirms it against GitHub's documentation.
61. `[unverified]` `gh pr list --search` accepts GitHub's `in:title` qualifier, so a fixed title prefix is findable, and it cannot search by changed path (relayed from the round-1 staff-platform-engineer review). It stays unverified until Verification step 0 confirms it.
62. `[engineer-verified: "Accept both (Recommended)"]` The label answered whether to accept two things: the record's softened wording that "the limit does not guarantee a whole read", and the rule that a split part that returns a partial view is split further, or the PR says why not. The table header carries the rule.
63. The one measured default Read returned lines 1-956 of a 1,935-line file under a 25,000-token cap, and the reference calls it one sample. `[verified: claude-skills/skills/code-review/REFERENCES.md:196-211]`
64. `[unverified]` The reason the record gives for filing no per-file issue is this architect's: a row already names its file, its seam and its current size, which an issue would copy and let go stale.
65. `[unverified — relayed from the round-1 staff-product-engineer review; #1015 not read by this architect]` #1015 says a helper one test tree uses goes in that tree's local module. Verification step 0 reads #1015 before the row's reason carries it.
66. findings.md counts a commit when it is reachable from the pin, is not a merge, falls inside the 90-day window, and touches the file's history across renames. `[verified: findings.md:107-115]`
67. The autonomous-shipping ask covers a plain push of the current branch but not a force-push. `[verified: claude/.claude/CLAUDE.md:174-177]`
68. `DOCS_DIR`'s row selects `HOOKS_TESTS_DIR` and `SKILLS_TESTS_DIR`, which do not cover `claude/.claude/tests/`. A module-level `REPO_ROOT` chain to a `docs/` file would therefore fail the read-completeness scan. `[verified: select-tests.py:1046]` That the scan resolves such a chain is `[verified: relayed — round-1 staff-platform-engineer R8]`.
69. The record's first Revisit bullet asks whether the assessment finds an unreasonable number or shape of exceptions. `[verified: docs/design-decisions/code-file-line-limit.md:59-63]` Row 76 is the engineer's ruling on it.
70. Six current offenders have mode `100755`, `install.sh` among them at 1,080 lines. `[verified: relayed — round-1 staff-sdet R2 and R6, git ls-files --stage at HEAD; not rerun by this architect]`
71. `[unverified — relayed from the round-1 staff-product-engineer review; the issue not read by this architect]` GH-1119's F2 text says the check "lives beside `test_ticket_reference_discipline.py`, with its own `select-tests.py` exception" and that "every exception row needs a non-empty reason". Verification step 0 confirms the wording.
72. `[engineer-verified: "Proceed anyway"]` The label answered a second question, asked after this revision projected about 1,510 changed lines against the about 1,100 named in row 53's question: "Split into smaller PRs now, or proceed as one?".
73. `[unverified — relayed from the round-2 staff-platform-engineer review, which read pytest 8.4.2's `_pytest/assertion/rewrite.py:440-475` but ran no test]` A bare `assert report is None` shows a string through a repr capped at 240 characters, or 2,400 with `-v`, while `pytest.fail(report, pytrace=False)` prints it verbatim. Verification step 4 settles it.
74. `claude/.claude/scripts/tests/conftest.py` strips `GIT_DIR`, `GIT_WORK_TREE`, `GIT_COMMON_DIR` and `GIT_INDEX_FILE`, `claude/.claude/tests/` has no conftest, and `helpers.py` provides `isolated_git_env`. `[verified: relayed — round-2 staff-platform-engineer R4, conftest.py:100 and helpers.py:3987; not reopened]`
75. `tomllib` parses a triple-quoted string with a trimmed first newline, or with a line-ending backslash, to a value holding no line break, and a header-shaped line inside one matches the stage-3 pattern. U+2028 is legal in a TOML comment, and `str.splitlines()` splits on it. `[verified: relayed — round-2 staff-sdet R3, scratch probes on Python 3.14; not rerun]` The shape controls check each again.
76. `[engineer-verified: "Assessed, limit stands (Recommended)"]` The label answered what the record should say about its first Revisit bullet, in a question that gave the assessment's 112 offenders of 685 files, 89 test and 23 production.
77. `[engineer-verified: "Accept the additions (Recommended)"]` The label answered whether to accept the message's additions beyond row 10's content: the row skeleton, the rename hint, the structural row's reason and qualifier, and the did-not-change procedure. The preface line and the "If this branch changed the file" heading came after that answer, from round 2, and are `[unverified]` session additions.
78. `[engineer-verified: "No trigger now (Recommended)"]` The label answered "Should the decision record carry [a Revisit trigger tied to the exception table itself]?".

## Critical files

**Dispatch 1, `code-writer`: the check and its selection.** It neither stages nor commits, because the check enumerates the shared index.
- Create `claude/.claude/tests/test_code_file_size.py`, holding the functions, the two real tests and every control.
- Create `code-file-size-exceptions.toml` with only its header comment.
- Modify `claude/.claude/scripts/select-tests.py`: two constants, `_is_code_file_change`, `SUPPLEMENTARY_RULES`, `add_supplementary_targets` and its call in `main`, one docstring line, and one `CROSS_DOMAIN_EXCEPTIONS` row.
- Modify `claude/.claude/scripts/tests/test_select_tests.py`: the two constant lists, the three target collectors, the two argv assertions, and the new cases.
- Verification: `scripts/venv-run.sh pytest claude/.claude/tests/test_code_file_size.py claude/.claude/scripts/tests/test_select_tests.py -n0`. Every control passes, the perturbation control included. The real size test fails, listing every offender, until dispatch 2 runs.

**Dispatch 2, `code-writer`, after dispatch 1: the population.**
- Modify `code-file-size-exceptions.toml` with every row, per "Populating the table". The reconciliation lists go to a scratch file under `agent-reviews/` for the PR description, not to a tracked file.
- Verification: `scripts/venv-run.sh pytest claude/.claude/tests/test_code_file_size.py -n0` passes, and Verification steps 2 and 3 hold.
- The session commits only after this dispatch, so no commit leaves the size test failing.

**Dispatch 3, `code-writer`: the docs.** Its files are disjoint from the other dispatches, and it may run beside dispatch 1 in the shared worktree. It neither stages nor commits. It names `claude/.claude/tests/test_code_file_size.py` and `code-file-size-exceptions.toml` in code spans, never relative links, because dispatch 1 may not have created them yet and `test_design_decision_files.py` resolves relative links.
- Modify `docs/design-decisions/code-file-line-limit.md`.
- Modify `claude-skills/skills/code-review/REFERENCES.md`, lines 218-221 only.
- Modify `docs/reports/2026-11-19-code-file-size-offenders/findings.md`: one superseded line at the Proposed-issues paragraph.
- Verification: `scripts/venv-run.sh pytest claude/.claude/hooks/tests/test_design_decision_files.py claude-skills/skills/tests/test_skill_citation_grammar.py -n0`.

**Reuse:** `helpers.REPO_ROOT` and `helpers.init_git_repo` for the throwaway-repository controls; `tomllib`; `os.fsdecode`; F1's `wc -l` cross-check command (findings.md:573); the precedent's corpus-guard pattern; and, in `select-tests.py`, the existing `(predicate, targets)` tuple shape, `_is_under` and `SelectionResult._replace`.

Projected diff: about 1,560 changed lines. The table is about 580, the check module about 800 after round 2's added controls, the decision record about 75, `test_select_tests.py` about 60, `select-tests.py` about 40, and the two sibling docs about 6. Against the earlier projection of about 1,100, the check module grew with its named seams and added controls. `test_select_tests.py` shrank, because the supplementary target no longer reaches the domain-mapping assertions. Row 72's answer was given at about 1,510, before round 2 added about 50 lines of controls.

## Verification

0. Before dispatch 1:
   - Read GH-1119's F2 section with `gh issue view 1119`. Compare its failure-message content, remedy order and prohibitions against row 10. A difference stops the work for the engineer. Confirm row 71's quoted wording for the PR description's departures list.
   - Read #1015 with `gh issue view 1015`. Population step 4 adds the local-module clause only if #1015 states it (row 65).
   - Confirm rows 60 and 61 against GitHub's documentation through a `verify-sources` dispatch, quoting the lines that settle them. The same dispatch confirms that GitHub's branch update offers a merge commit and a rebase, which Landing's merger step 1 relies on.
     - If row 60 does not hold, the did-not-change procedure's step 2 drops its re-run sentence.
     - If row 61 does not hold, its step 3 gives a search that works.
   - Each row's tag becomes `[verified: <page>]` before the message text is committed.
   - The PR description names the pages.
1. Dispatch 1's command, with a header-only table: every control passes, and the size test's output lists every offender with its count. Save that output under `agent-reviews/`.
2. That list equals F1's cross-check command (findings.md:573), run at HEAD. The paths and counts match, except where a tracked symlink is involved, which the check excludes by mode.
3. Each row's verdict and seam or reason match findings.md for every offender F1 assessed, except `helpers.py`'s reason (rows 7, 8, 65). The seam-symbol scratch check has run. The PR description lists the new offenders with their verdicts, the dropped offenders, and any seam misses.
4. Live probe, as first-run evidence, while no dispatch is running: lower one real row's ceiling by one. The size test then fails, naming that path and its true count. Run it once at default verbosity and once with `-v`: both outputs hold the remedy block's heading and the did-not-change heading in full, which settles row 73. Restore the row. The perturbation control keeps this property under test afterwards.
5. Grep for `code-file-line-limit` with glob `**/*.py` finds `claude/.claude/tests/test_code_file_size.py` (row 44).
6. `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py` passes. It selects the full suite on its own, because `select-tests.py` changed (row 33).
7. `scripts/venv-run.sh ruff check claude/.claude/ claude-skills/ plugins/ evals/` passes.
8. Grep `docs/` for `scripts/tests/test_ticket_reference_discipline` finds no match. The record's `REFERENCES.md` citation sits on one line.
9. Redaction:
   - Grep the staged diff for home-rooted paths, and for tracker IDs outside the `GH-` and `CVE-` allowlist.
   - The record's new figures (9, 33, 53, 62, 89, 204, 325, 334, 509, 6,233) are counts over this repository's own git and pull-request history. Record their composition check against `docs/private-project-redaction.md` § "Remediation" before the first commit (row 50).
10. Landing, per **Landing**: the last push follows a merge of `origin/main`, a run of the check that writes every printed value, and step 6 again. This repeats after every later push. The PR description carries every item under **PR description**.

## Out of scope

- **Editing GH-1113's task-list line.** It needs the engineer's separate go-ahead (row 6).
- **Filing per-file split issues.** The engineer ruled them out (row 5).
- **Editing `.claude/plans/code-file-size-splits.md`**, including lines 217, 247, 257, 419 and 423. It is a merged plan's record (row 28).
- **Revising any finding, table or figure in findings.md.** Only the superseded line is permitted (row 27).
- **Requiring up-to-date branches or a merge queue.** The consult advised against both (row 20). The message's did-not-change route and `main`'s own CI run handle the same-size clean merge.
- **Making the ticket-reference predicate supplementary.** `_is_py_source_under_claude_or_plugins` also suppresses the fallback, for example for `plugins/npm-semver/scripts/check.py` (`test_select_tests.py:1664-1671`). That is pinned behavior and a separate selection decision, to raise with the reviewer.
- **Counting untracked files.** GH-1119 and F1 scope the check to tracked files, and CI's clean checkout has none.
- **Enforcing the Read cap, or counting non-comment lines.** The check counts physical lines only (rows 9, 12).
- **Annotating rows with the harness-closure windows.** Those windows depend on the review bench campaign's state, which findings.md records and the table header points to (row 38).
- **The decision record's second Revisit bullet.** Only the first is reworded (row 76).
- **A Revisit trigger tied to the table**, such as a row count or repeated raises of one row. The engineer ruled it out for now (row 78).
- **Measuring how often equal-delta pairs merge cleanly.** The record states that the rate is unmeasured.
- **Re-checking seams or `issue` state on every run.** The seam check runs once, at population step 7. A recurring check would need seams in a parseable form, and a network call for issue state.
- **Announcing the limit in `CLAUDE.md` or `README.md`.** The failure message carries the remedy, and an always-loaded line is a separate context-cost decision.
- **Splitting any offender.**
- **The redaction hook's scope gap.** #1542 tracks it (row 50).
