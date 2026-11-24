# Plan: an edit-method rule for `code-writer`

## Context

Goal: make `code-writer` read the files it changes with the Read tool and change them with Edit/Write, so its self-review evaluator sees every path it changed.

Ask: in a prior session, the engineer accepted session-drafted wording: read files you intend to change with Read, use Edit for single-site changes, and keep patches allowed for uniform multi-site changes. On that wording, the engineer said this session: "That’s not my literal wording. I think I selected that from some options the orchestrator agent presented to me". Added this session on the carve-out's scope: "Ask the architect. I’d say cross file only". All four plan-added deliverables were kept, via labels "Self-review step 1 edit, Pin test, Design-record bullet, CHANGELOG entry".

Problem: `code-writer` often edits through Bash Python/sed patches instead of Edit. `claude/.claude/hooks/evaluate-code-writer-self-review.py` builds its changed-path set only from successful `EDIT_TOOLS = ("Edit", "Write")` calls (line 52, used in `assess`). A Bash-patched file therefore escapes the evaluator's reviewer-coverage and comment checks. `code-writer.md` states no edit-method rule. Reviewer agents state one for their own findings file (`staff-sdet.md` § "File-based output": "Use the Write tool — not `cat`, `echo`, heredocs, or Python file writes").

Why now: a prior session's root-cause analysis traced the patching to two causes. Auto mode permits script edits. Patches tend to follow Bash-only reads, while Edit requires a prior Read. That session also found that a patch is genuinely cheaper for one uniform change across many files, and dearer for a single-site change.

Intended outcome: a prose edit-method rule in `code-writer.md` § Charter (M1, M2 below), with its Bash carve-out recorded as a known degradation in the send-back design record. The change adds no new hook. If the prose rule proves insufficient, escalate inside the evaluator, not with a new gate. Committed text carries no machine-wide transcript figures.

## Approach

Add one Charter bullet to `code-writer.md` that routes every file change through Read, Edit and Write, with one cross-file Bash exception (M1, M2). Supporting edits are M3-M6. The change adds no hook, no evaluator change and no frontmatter change.

**Assumption ledger**

**Root problem:** the Context's Problem paragraph (rows 1, 2). No rule keeps `code-writer`'s changes on the tools the evaluator sees.

**Givens:**

- **G1 — Auto mode lets Bash write files without a prompt.** The harness and each user's permission settings own that, not this agent body (row 19).
- **G2 — A prose rule binds only as far as the writer follows it.** Claude Code owns whether a subagent honors its body. The fallback the Context names, escalating inside the evaluator, needs its own decision (Out of scope).
- **G3 — No new hook.** The Bash-write gate the engineer floated is undecided, and settling it is outside this plan (row 20).
- **G4 — Committed text carries no machine-wide transcript figures.** `CLAUDE.md` § "Redact private-project-identifying content" owns that bar for this public repository.

**Mechanisms:**

- **M1 — One Charter bullet, inserted between the "Match the conventions" bullet (ends line 22) and the "You do not commit" bullet (starts line 23).** Charter is where the file sets tool-use boundaries, such as who owns git and which commands the writer may run (row 12). Its bar list names the shapes reviewers already bar for their findings file: `cat`, `echo`, heredocs and Python file writes (row 14). It adds `sed -i` and `perl -pi`, the in-place shapes a writer patching existing files reaches for. Its one-sentence reason cites the evaluator fact (row 1), so the writer knows the bar is about visibility, not style. The Read sub-bullet keeps the Ask's "read files you intend to change with Read" for every changed file, the exception's files included (row 5). It also names Bash `cat`/`head`/`sed -n` as not counting, mirroring Self-review step 3's "A Bash `cat` does not count" (`code-writer.md:112`). Rejected:
  - § Implementation baseline. It lists properties of the code written "across every language and stack" (row 12), not how the writer drives its tools.
  - Copying the reviewers' Write-tool line verbatim. That line governs one findings file the reviewer creates. This rule governs every file the writer changes, including in-place edits the reviewers' list does not name.
  - A lighter mechanism than prose. None exists below an instruction in the agent body. Heavier ones, an evaluator change or a gate, are G2's fallback and G3's excluded option.

  `anchors: root, row1, row5, row10, row12, row14`.
- **M2 — The exception is one find-and-replace, literal or pattern, applied the same way to two or more files.** The engineer leaned cross-file only (row 3) and handed the call here (row 4). Cross-file only holds on its merits too (row 8). A within-file identical repeat is one Edit with `replace_all` (row 7). The only within-file case left without a one-call Edit is a pattern whose replacement differs per site. It costs one Edit per site, which this plan accepts so that no single-file change goes dark to the evaluator (row 9). "Literal or pattern" widens the dispatcher's "identical substitution" wording (row 6). The prior-session Ask said "uniform" (row 5), and a cross-file pattern rename has the same cost case as a literal one. The self-review diff then catches an overmatching pattern (M3). "Two or more files" is the definitional edge of cross-file, not a measured break-even (Out of scope). Rejected:
  - Any uniform multi-site change, the prior-session wording. It licenses a within-file patch that `replace_all` makes unnecessary for identical repeats, and every such file loses the path-keyed checks (rows 2, 7).
  - Identical literals only. It forces per-file Edits for a cross-file pattern rename, the case the prior session found cheapest as a patch (row 9), with no visibility gain, since the exception's files escape the evaluator either way.

  `anchors: row2, row3, row4, row5, row6, row7, row8, row9`.
- **M3 — Self-review step 1's scope sentence names the exception's files.** It now scopes "your complete diff" to files Edit/Write calls touched (row 13), which reads as excluding a file the exception changed. The evaluator cannot cover that file, so the writer's own review is the only in-context check, and the scope must include it. The edit keeps the pinned `` `git status --porcelain` `` literal (row 15). `anchors: row2, row13, row15`.
- **M4 — One bullet in `docs/design-decisions/code-writer-self-review-send-back.md` § "Known degradations and unverified paths".** It records that a Bash-changed file never enters the changed-path set, names the R-codes that skip it (row 2), and cites the Charter for the allowed case rather than restating it (`.claude/rules/design-decisions.md`, "Cite, don't restate"). The section is a one-line-per-bullet list that already cites `code-writer.md` § by bare filename (row 18). `anchors: row1, row2, row18`.
- **M5 — `TestCodeWriterEditMethodRule` in `claude-skills/skills/tests/test_agent_body_pins.py`, after `TestCodeWriterTestToFitRule`.** The bullet is the plan's only mechanism, so silently deleting it would reopen the gap with no failing check. The file already pins a code-writer Charter bullet with stable-literal asserts over a whitespace-normalized body (row 17). It pins four literals inside the Charter section: the bar, the Read requirement, the exception's scope, and "find-and-replace". It also pins "find-and-replace" in the Self-review section, so a revert of M3 fails a test. Rejected: no pin, relying on `/agent-review`. That review runs only on a diff that touches the agent, and a later edit's review need not know this bullet carries a hook's coverage. `anchors: row17`.
- **M6 — A `### Changed` entry under `## [Unreleased]` in `CHANGELOG.md`.** The rule changes `code-writer` for every stow consumer on `git pull` (row 22), and recent entries record prose-rule changes of that reach (row 21). `anchors: row21, row22`.

**Assumptions:**

| # | Assumption | Tag |
|---|---|---|
| 1 | The evaluator's changed-path set comes only from successful Edit and Write calls whose path exists inside a repository | `[verified: claude/.claude/hooks/evaluate-code-writer-self-review.py:52, 436-452]` |
| 2 | R1 (path floor, comment-line floor included), R2, R4 and R5 key on that set. R3 does not, so a ledger name without a Read is still sent back | `[verified: claude/.claude/hooks/evaluate-code-writer-self-review.py:8-13, 468-524]` |
| 3 | The carve-out covers changes across files only, not repeats within one file | `[engineer-verified: "I’d say cross file only"]` |
| 4 | The engineer delegated the carve-out decision to plan-architect | `[engineer-verified: "Ask the architect."]` |
| 5 | The prior-session Ask: Read for files you change, Edit for single-site changes, patches for uniform multi-site changes. It was session-drafted wording the engineer selected, not the engineer's own words. Row 3 narrows its multi-site clause to cross-file | `[engineer-verified: "I think I selected that from some options the orchestrator agent presented to me"]` for its provenance only; its content stays `[unverified]` |
| 6 | "One identical substitution across several files" is the dispatching session's option description, not the engineer's words | `[unverified]` |
| 7 | Edit's `replace_all` replaces every occurrence of one string in a file in one call | `[verified: the Edit tool schema available to this session, "replace_all: true replaces every occurrence instead"]` |
| 8 | plan-architect's own judgment: cross-file only, covering literal or pattern find-and-replace, is the narrowest carve-out that keeps the cost case and leaves no single-file change invisible to the evaluator | `[unverified]` — design judgment over rows 2, 7 and 9 |
| 9 | One uniform change across many files costs less as one Bash patch than as per-file Edits, and a single-site patch costs more output tokens than an Edit. The within-file varied-pattern case was not measured | `[unverified]` — prior-session handoff measurement, not rechecked |
| 10 | Patches tend to follow Bash-only reads, and Edit requires a prior Read-tool read | `[unverified]` — prior-session handoff |
| 11 | A ranged Read (`offset`/`limit`) satisfies Edit's prior-Read precondition. If not, Edit errors and the writer re-reads the whole file, so the rule still holds | `[unverified]` |
| 12 | § Charter holds tool-use boundaries (git ownership, which commands to run). § Implementation baseline holds properties of written code "across every language and stack" | `[verified: claude/.claude/agents/code-writer.md:23-30, 44-45]` |
| 13 | Self-review step 1 scopes the diff to "the files your own Edit/Write calls touched this dispatch" | `[verified: claude/.claude/agents/code-writer.md:99-101]` |
| 14 | Ten reviewer agents carry "Use the Write tool — not `cat`, `echo`, heredocs, or Python file writes." for their findings file. `code-writer` is the only agent holding Bash with Edit or Write for implementation, so no sibling agent needs this rule | `[verified: grep of claude/.claude/agents/ for that line and for tools: frontmatter, e.g. staff-sdet.md:116]` |
| 15 | `test_agent_body_pins.py` pins `` `git diff -- <paths>` ``, `` `git status --porcelain` ``, "Never use `git diff HEAD`", "test-to-fit" and "fix the code, not the test". `test_send_back_skipped_self_review.py` pins the domain table, ledger fixture, Return format bullet, frontmatter tools and Self-review heading. The planned edits touch only the `git status --porcelain` sentence, and they keep that literal. Other readers of `code-writer.md` read frontmatter, stems or per-account paths only, and `select-tests.py` is the authority on which tests run | `[verified: claude-skills/skills/tests/test_agent_body_pins.py:21-54; claude/.claude/hooks/tests/test_send_back_skipped_self_review.py:630-765; claude/.claude/scripts/select-tests.py:1063-1070; staff-sdet plan review R4]` |
| 16 | `code-writer.md` has no stated line cap | `[verified: grep of docs/skills.md, test_agent_roster.py and the agent-review skill finds only a skill cap (docs/skills.md:171)]` — not exhaustive |
| 17 | `test_agent_body_pins.py` already pins a code-writer Charter bullet with stable literals, and normalizes whitespace for a wrapped literal | `[verified: claude-skills/skills/tests/test_agent_body_pins.py:10-54]` |
| 18 | The design record's "Known degradations and unverified paths" section is a one-line-per-bullet list, and the record already cites `code-writer.md` § "Self-review pass — mandatory before returning" by bare filename | `[verified: docs/design-decisions/code-writer-self-review-send-back.md:73, 132-139]` |
| 19 | Auto mode permits Bash script edits | `[unverified]` — prior-session handoff |
| 20 | The escalation order is prose rule, then evaluator, then gate, and the Bash-write gate is undecided | `[unverified]` — a prior consult relayed by the handoff |
| 21 | `## [Unreleased]` records prose-rule changes that reach every consumer, e.g. the Main session rule entry. The older test-to-fit Charter rule shipped with no entry | `[verified: CHANGELOG.md:3, 9-12; no CHANGELOG.md match for "test-to-fit"]` |
| 22 | Edits to existing files under `claude/.claude/**` go live on `git pull` | `[verified: CLAUDE.md § "Working in this repo"]` |
| 23 | M3 (Self-review step 1 edit), M5 (pin test), M4 (design-record bullet) and M6 (CHANGELOG entry) stay in this PR | `[engineer-verified: "Self-review step 1 edit, Pin test, Design-record bullet, CHANGELOG entry"]` |

## Critical files

All paths relative to the worktree root. Dispatch one `code-writer`. All five edits state one rule. The pin's literals and the changelog's wording come from the Charter text, so a split would restate it in every prompt.

**`claude/.claude/agents/code-writer.md`** — two edits, nothing else.

Insert this bullet between line 22 (end of "Match the conventions") and line 23 ("You do not commit"):

```markdown
- Change a file's content only with Edit or Write, never through Bash: not
  `sed -i`, `perl -pi`, a Python file write, a heredoc, or an `echo` or `cat`
  redirect. The hook that checks your self-review counts a file as changed
  only from your Edit and Write calls, so a file changed through Bash escapes
  its checks.
  - Read each file you will change with the Read tool, using `offset` and
    `limit` for a range. A Bash `cat`, `head` or `sed -n` does not count.
  - Within one file, use Edit, with `replace_all` for a repeated string.
  - Create a new file with Write.
  - The one exception is a single find-and-replace, literal or pattern,
    applied the same way to two or more files. It may run as one Bash
    command.
```

Replace Self-review step 1's first sub-bullet (lines 99-101) with:

```markdown
   - Scope "your complete diff" to the files your own Edit/Write calls, or a
     cross-file find-and-replace the Charter allows, touched this dispatch;
     cross-check against `git status --porcelain` to catch a path your own
     tracking missed (e.g. a retried or corrected `Write` call).
```

**`claude-skills/skills/tests/test_agent_body_pins.py`** — add this class after `TestCodeWriterTestToFitRule` (ends line 58), with the file's two-blank-line class spacing. It uses the already-imported `_agent_body`, normalized as `TestCodeWriterSelfReviewScope._body` does at line 19, and slices by heading as `TestSkillFidelityReviewerArchitectConsultCheck._section` does (line 245). Add no module-level helper or fixture.

```python
_EDIT_METHOD_EXCEPTION = "find-and-replace"


class TestCodeWriterEditMethodRule:
    """Pin code-writer's Charter bullet that routes file changes through Read, Edit and Write.

    The self-review evaluator sees a changed file only through Edit and Write.
    The exception literal is shared with Self-review step 1, so reverting either site fails a test.
    """

    def _section(self, start_heading: str, end_heading: str) -> str:
        body = " ".join(_agent_body("code-writer").split())
        start = body.index(start_heading)
        end = body.index(end_heading)
        assert start < end, f"{start_heading!r} is expected to precede {end_heading!r}"
        return body[start:end]

    def _charter(self) -> str:
        return self._section("## Charter", "## Implementation baseline")

    def test_bars_bash_file_writes(self):
        """The Charter must bar changing file content through Bash."""
        assert "never through Bash" in self._charter()

    def test_requires_read_tool_for_changed_files(self):
        """The Charter must require a Read-tool read of each file the writer changes."""
        assert "Read each file you will change with the Read tool" in self._charter()

    def test_names_the_bash_exception_cross_file_scope(self):
        """The one Bash exception must name its cross-file scope."""
        charter = self._charter()
        assert _EDIT_METHOD_EXCEPTION in charter
        assert "two or more files" in charter

    def test_self_review_scope_covers_the_exception(self):
        """Self-review step 1 must scope the diff to include the exception's files."""
        assert _EDIT_METHOD_EXCEPTION in self._section("## Self-review pass", "## Return format")
```

**`docs/design-decisions/code-writer-self-review-send-back.md`** — append after line 139, the last bullet of § "Known degradations and unverified paths", as one line:

```markdown
- A file `code-writer` changes through Bash never enters the evaluator's changed-path set, so R1, R2, R4 and R5 do not cover it. `code-writer.md` § "Charter" names the one case it allows.
```

**`CHANGELOG.md`** — add under `## [Unreleased]` → `### Changed` (line 7):

```markdown
- **`code-writer` now changes a file's content only with Edit or Write, and reads a file it will change with the Read tool.** Its self-review hook counts a file as changed only from Edit and Write calls, so a file it changed through Bash escaped that hook's checks. One find-and-replace applied the same way to two or more files may still run as one Bash command, and the hook does not check those files. The change is live on `git pull`.
```

**Do not touch:**

- `claude/.claude/hooks/evaluate-code-writer-self-review.py` and its tests (Out of scope).
- `code-writer.md`'s frontmatter, read by `test_send_back_skipped_self_review.py:759`, `test_agent_roster.py` and `evals/replay_bench/arms.py`.
- Every reviewer agent's Write-tool line.

Projected diff: about 58 lines (Charter bullet +12, step 1 +4/−3, pin class +37, design record +1, CHANGELOG +1).

## Verification

Run from the worktree root.

1. Red before green for the pin, in this order:
   1. Add `TestCodeWriterEditMethodRule` and run `scripts/venv-run.sh pytest claude-skills/skills/tests/test_agent_body_pins.py`. Confirm all four new tests fail with `AssertionError`, not a collection or import error.
   2. Add the Charter bullet. Confirm the first three new tests pass and `test_self_review_scope_covers_the_exception` still fails.
   3. Make the step 1 edit. Confirm the whole file passes, the existing `git status --porcelain` pin included.
   4. Discrimination check: in the working tree, change "two or more files" in the Charter bullet to "one or more files", confirm `test_names_the_bash_exception_cross_file_scope` fails, then restore the text.
2. `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py` — the documented scoped command. Let it derive the set. `code-writer.md` reaches its tests through the `AGENTS_DIR` row (`select-tests.py:1063-1070`).
3. `scripts/venv-run.sh ruff check claude-skills/` — the diff adds Python. No shell file changes, so skip ShellCheck.
4. `/agent-review` on the `code-writer.md` diff, per `.claude/rules/skill-and-agent-self-review.md`, then `/code-review` before the commit and `/ready-for-review` before the push.
5. Manual read no test covers: re-read § Charter top to bottom. Confirm the new bullet does not conflict with the read-only-checks bullet. Confirm step 1's scope sentence and the bullet name the same exception.
6. After merge, not a merge gate: if the prior session's scan scripts survive, rerun its measures over `code-writer` dispatches made after the merge. Report the results to the engineer in session only, never in a committed file or PR body (G4). The measures:
   - the single-file versus cross-file patch share
   - the Bash-first-read share
   - the share of changed paths the evaluator cannot see

   A within-file patch share that stays well above zero is the signal for the evaluator escalation in Out of scope.

## Out of scope

- **Teaching the evaluator to see Bash writes**, from `git status` or by parsing Bash commands. The Context names it as the escalation if the prose rule proves insufficient. It also reverses the evaluator's stated "with no git invocation" design (`evaluate-code-writer-self-review.py:5-6`), so it needs its own decision. Shipping it must revisit the Charter bullet's rationale and `TestCodeWriterEditMethodRule`, which would then enforce a bar whose stated reason no longer holds.
- **A hook that gates Bash writes by command shape.** The engineer floated it, it is undecided (row 20), and this change adds no new hook (G3).
- **A measured file-count threshold for the exception.** "Two or more files" is the definitional edge of cross-file. No cost break-even in this repository supports a higher number, and committed text may not carry the prior session's figures (G4).
- **Formatter, `--fix` linter and codegen runs that rewrite files.** The Charter's checks bullet already limits the writer to read-only checks (`code-writer.md:25-30`). This plan does not revisit that bullet.
- **The reviewer agents' findings-file Write rule.** It already bars Bash writes for its one file and needs no change (row 14).
