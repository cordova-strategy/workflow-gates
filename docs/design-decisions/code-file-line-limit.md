# This repo caps code-file length at 1,000 lines, via a repo-local pytest check

*2026-09-25.*

`.claude/plans/code-file-size-splits.md`'s child issue F ("Code-file size
policy") records this decision. It applies only to `claude-config` itself,
not to any repo that installs its stowed packages.

**Mechanism: a repo-local pytest check, not a hook.** Anything under
`claude/.claude/hooks/` installs into every stow consumer's own repository
(`CLAUDE.md`'s "Plans in this repo affect all stow users" section), so a
hook enforcing this repo's own file-length convention would impose it on
every downstream repo regardless of that repo's own conventions. A
repo-local pytest check has an existing precedent doing exactly this job
for a different rule: `test_ticket_reference_discipline.py` already scans
the tracked `.py`/`.sh` files under `claude/`, `claude-skills/` and
`plugins/`, and carries its own `select-tests.py` exception so a scoped
local run still selects it. This rule's check is
`claude/.claude/tests/test_code_file_size.py`, and its exception table is
`code-file-size-exceptions.toml` at the repository root. The check covers
every tracked `.py` and `.sh` file in the repository, `scripts/`, `evals/`
and root files included.

**Limit: 1,000 lines, for production and test files alike.** This is
where the surveyed linters' own defaults converge, not a defect
threshold — no primary study links file length to defect rates or to
LLM review effectiveness (an absence checked for, not merely unclaimed).
pylint's `too-many-lines` check, SonarQube's `S104`, and SwiftLint's
`file_length` *error* level (its *warning* level fires at 400) all default
to 1,000. Checkstyle's `FileLength` check defaults to 2,000, and ESLint's
`max-lines` rule — off by default, so its own docs' example config is the
convention being cited — defaults to 300 when enabled. ruff and ShellCheck
carry no file-length rule of any kind. No surveyed tool sets a separate
default for test files, which is why this repo's test-file limit matches
its production-file limit instead of following some other convention.

Reading a file whole in one default Read call is a second basis for the
limit, with no evidence of where defects start either. The Read tool caps
one call by tokens, not lines. One measured file returned 956 of its 1,935
lines from one default call, as
`claude-skills/skills/code-review/REFERENCES.md` § "Read-tool per-call token cap"
records. A shorter file is more likely to fit, but the limit does not
guarantee a whole read. Each split PR shows that every new part returns from
one default Read call with no `PARTIAL view` notice. A part that does not is
split further, or the PR says why not. The check itself counts lines only.

**Exception ceilings are exact, in both directions.** An exception row
passes only when its file's physical line count equals the row's
recorded ceiling — a shrink must lower its own ceiling, not merely stay
under a stale one. This rejects three lighter alternatives.

An unbounded grandfather list (no ceiling at all) lets exceptions grow
without limit, which is what happened to `_lib.sh` absent any check: 1,232
lines when a prior audit first proposed splitting it, 1,497 at a later
discovery pass, 3,554 when this decision was recorded, and 6,233 at the
assessment's pin (`docs/reports/2026-11-19-code-file-size-offenders/findings.md`).

An upward-only stored ceiling, which fails growth but not shrinkage, lets a
shrunken file keep its old ceiling, so later growth spends the slack with no
reviewed edit forcing a conscious decision.

The existing length gates store no such ceiling. `_lib_staged_length_gate`
denies when `NEW > LIMIT and NEW > OLD`, where `OLD` is the file's
previous version, so a shrink leaves them no slack. Adapted here, only a PR
that grows an exception file would edit its row. That is rejected on four
grounds:

- The check would need the PR's base to tell growth from shrinkage.
- Exact rows make every pair of PRs that change one file's length conflict
  on its row, so the row acts as a lock. Base-relative rows lock only
  growth against growth.
- The table keeps showing current sizes.
- The saving is small. In the assessment's window, 9 of the 334 commits
  that changed an offender's length only shrank offenders, and 53 more
  shrank one while growing another, a floor of 62 row edits.

The cost of exact ceilings, beside that saving, comes from the same window:

- 204 of the 325 growth PRs had an open interval overlapping another PR
  that grew the same offender, across 33 offenders. That is an upper bound
  on row conflicts, because an open interval does not show when a branch
  first touched the file.
- 89 of the window's 509 commits grew `_lib.sh` or `helpers.py`, two
  structural rows that splits do not delete.
- The window predates the splits, so the shrink share will rise as they
  land.

Method for every figure in this section other than `_lib.sh`'s sizes: counts
over this repository's own history, using the assessment's window and commit
definitions, each commit's added and deleted lines per offender, and each
growth PR's created-to-merged interval. The figures are in
`.claude/plans/code-file-size-check.md` § "Context".

The residual: two PRs that change one file to the same new size merge
cleanly and leave it off its row. `main`'s next run then fails. So does the
next run of each open PR with a changed path outside `tests.yml`'s skip
list. Both stay red until a fix merges by the failure message's route. How
often this happens is unmeasured. Requiring up-to-date branches or a merge
queue is not adopted.

Split-pending rows carry an issue only where one exists, and no per-file
issue is filed. The table is the split backlog. Each row already names its
file, its seam and, because ceilings are exact, its current size, which a
per-file issue would copy and let go stale. A row's `issue` names the issue
that owns its split, and a row without one has no owner until a PR takes it
up.

**Split order.** Exposure, a file's physical lines times its 90-day
commits, ranks split-pending files. The assessment's figures are frozen at
its pin, so a re-rank recomputes both. A row's `ceiling` is its physical
count. Its 90-day commits are its non-merge commits in the 90 days before
HEAD's committer date, following renames, which
`git log --follow --no-merges --since=<that date> --format=%h -- <path>`
lists. The definition is the assessment's "Window and commits". A split of a
file that every feature appends to must also end that append pattern.

**Timing: the check ships only after an offender assessment exists.** The
limit and the exception mechanism are decided, but nothing enforces them
until F1 (the offender assessment) records, for every file already over
1,000 lines, its size, its 90-day commit count, and a verdict — split
pending or structural exception with a reason. That ordering exists so
the number and shape of today's offenders inform the exception table
before the check can fail a PR over them, rather than the check landing
first and forcing an unreviewed guess at every exception row.

**Revisit** if any of:

- The assessment found 112 offenders of 685 tracked files, 89 of them test
  code, and the limit stands. A later inventory that finds an unreasonable
  number or shape of exceptions reopens it — the engineer's own stated
  condition for imposing it.
- A primary study linking file length to review-defect rates or to LLM
  review effectiveness is found, which would ground the limit in
  something other than linter-default convergence.

## Sources

- pylint, `too-many-lines` (`C0302`) — <https://github.com/pylint-dev/pylint/blob/main/pylint/checkers/format.py> — `"default": 1000,` on the `max-module-lines` option. Fetched 2026-09-25.
- SonarSource, `sonar-python` `TooManyLinesInFileCheck` (S104) — <https://raw.githubusercontent.com/SonarSource/sonar-python/master/python-checks/src/main/java/org/sonar/python/checks/TooManyLinesInFileCheck.java> — `private static final int DEFAULT = 1000;`. `rules.sonarsource.com` itself was unreachable when fetched; verified against the check's own source instead. Fetched 2026-09-25.
- Checkstyle, *FileLength* — <https://checkstyle.sourceforge.io/checks/sizes/filelength.html> — `max ... int ... 2000`. Fetched 2026-09-25.
- SwiftLint, *file_length* — <https://realm.github.io/SwiftLint/file_length.html> — `warning | 400` / `error | 1000`. Fetched 2026-09-25.
- ESLint, *max-lines* — <https://eslint.org/docs/latest/rules/max-lines> — `"max" (default 300) enforces a maximum number of lines in a file`; the rule itself is not enabled by default. Fetched 2026-09-25.
- ruff, full rules list — <https://docs.astral.sh/ruff/rules/> — no rule addresses file length, file size, or line-count limits. Fetched 2026-09-25.
- ShellCheck, wiki check index — <https://www.shellcheck.net/wiki/> — no rule addresses file length. Fetched 2026-09-25.
- `CLAUDE.md` — "Plans in this repo affect all stow users" — why a hook is rejected in favor of a repo-local check.
- `claude/.claude/hooks/tests/test_ticket_reference_discipline.py` and its `select-tests.py` exception — the existing precedent this check's mechanism follows.
- `docs/reports/2026-11-19-code-file-size-offenders/findings.md` — the offender assessment, including `_lib.sh`'s size at its pin and the window and commit definitions.
- `claude/.claude/hooks/_lib.sh` — `_lib_staged_length_gate` and its `NEW > LIMIT and NEW > OLD` rule, and the unbounded-grandfather-list failure mode being avoided.
- `.claude/plans/code-file-size-splits.md` — child issue F's full design, the engineer's decisions (rows 43–46, 60–62), and G4's absence-of-evidence finding. Its per-file-issue lines and its premise about the existing gates are superseded by this record.
- `claude-skills/skills/code-review/REFERENCES.md` § "Read-tool per-call token cap" — the measurement behind the Read-call basis for the limit above.
- `.claude/plans/code-file-size-check.md` § "Context" — the growth, shrink and overlap figures.
