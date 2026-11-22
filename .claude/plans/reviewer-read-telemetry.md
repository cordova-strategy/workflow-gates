# Reviewer-read telemetry and the A-field baseline

## Context

Goal: measure how reviewer subagents actually read files today, and record that measurement as the A-field baseline before the reviewer read methodology changes.

Ask: GH-1529, "A2 — Reviewer-read telemetry, then capture the A-field baseline" (the issue body is the request; the engineer invoked `/plan-it GH-1529`). Where the issue has A2 add to `read_scope.py`, the engineer chose a new module instead: "A new `reviewer_reads` module with its own `reviewer-reads` subcommand, leaving `read_scope.py` untouched" — accepted via label "New reviewer_reads module (Recommended)". The engineer later widened the request to a before-value for #1115's late-findings watch: "yes, add it to this plan", answering whether this plan should capture one. After plan review the engineer took it back out: "Move to its own issue (Recommended)", answering how late findings should proceed.

Nine reviewer agent bodies and the `code-review` base checklist tell reviewers to read every changed file fully. That instruction is silently partial on any file larger than one Read call, and nothing measures how often that happens. Epic #1113 replaces the instruction in child #1115, and gates that change on two baselines. The bench baseline belongs to #1114. This plan delivers the other one, the field baseline, drawn from real review transcripts.

A1 (#1128) extracted the `read-scope` instrument into `claude/.claude/scripts/transcript_analysis/read_scope.py`. It separates main-thread Reads from subagent Reads and nothing finer. A2 adds what the epic needs to see:

- a reviewer-subagent split;
- a touched-file-size bucket;
- main-thread Reads inside review-round windows;
- a count of reviewer Reads that returned a `PARTIAL view` notice, and how many of those the reviewer followed with further paged Reads.

A2 reports these alongside the existing field signals: reviewer-yield's verdict mix and cited-path edit overlap, and review-ledger ADDRESS/DEFER rates. GH-1529 makes the ledger rates conditional on this plan finding ledgers aggregable across sessions; the Approach states that finding.

#1115's acceptance adds a watch that GH-1529 does not mention: "After merge: A-field watches late findings (issues raised in a later review round on code an earlier round had in scope) over a window. A rise reopens this issue." A rise needs a before-value. This plan does not capture one: the engineer moved that measure to its own issue under #1113, and Out of scope records why.

Why now: transcripts and review ledgers age out on a rolling retention window, and #1115 must not merge before the field baseline is captured. A #1115 merge first would make the pre-change measurement unrecoverable.

Intended outcome, in GH-1529's acceptance terms:

- A2 answers how often reviewers' "full" reads of files larger than one Read call were actually partial.
- A2 answers what share of reviewer tokens went to Read, and what share of that went to files over 1,000 lines.
- The A-field baseline is captured from transcripts that predate #1115's merge, and #1113's "A-field baseline captured" checkbox records the date and where the measurement lives.

Constraints the issue sets:

- A2 outputs size buckets only, never file paths, matching read-scope's redaction design.
- Any figure it publishes follows `docs/private-project-redaction.md` § "Publishing a tooling measurement".
- `transcript_analysis/read_cost.py` already splits whole-file Read spend by main thread and subagent type, and is checked for reuse before a second split is added.

## Approach

Add a `reviewer-reads` subcommand, in a new `transcript_analysis/reviewer_reads.py`, that measures how reviewer subagents read files over an explicit date window and counts the review ledger's terminal dispositions. It refuses any corpus wider than this repository on one account, for its ledger section as for its transcripts. PR 1 ships the instrument. PR 2, cut after PR 1 merges, runs it once from this clone and records its report as the A-field baseline on a new case-study page.

The command reads each Read's outcome from the structured `toolUseResult.file` record the harness writes beside the result (row 6). It opens only ledger files named for one of this checkout's worktree paths, the same path identity `--this-repo` scopes transcripts by (M15).

The engineer settled these choices:
- The instrument lives in its own module and leaves `read_scope.py` untouched (row 30).
- The capture runs from this clone only (row 75), which supersedes row 15's second sentence.
- The work ships as two PRs (row 31). PR 1 proceeds at about 4,250 lines (row 89). Row 93 records that the branch now measures above that.
- The diff-handoff kind, the per-type rows and coverage stay, in reduced forms (row 34).
- Late findings move to their own issue (row 51), which supersedes row 36.

**What `reviewer-reads` reports.** Every figure is an aggregate. No path, session id, project name, ledger id or untracked agent-type name is printed, on stdout or on stderr. Stderr can also carry an API request id, through pricing's two request-id notices, as read-cost's stderr does (row 77). Stderr is read by the session and never published.

- **Populations.**
  - *Reviewer windows*: subagent transcripts, read through `read_cost._read_subagent_windows`, whose `.meta.json` `agentType` passes `reviewer_yield._is_reviewer_subagent_type` and whose first timestamped record falls in the window.
    - `skill-fidelity-reviewer` windows are left out (M17).
    - A reviewer dispatched by another subagent is included, because the harness writes every nested dispatch into the same `subagents/` directory (`corpus.py`:31-35).
  - *Main-thread round Reads*: main-thread Read calls whose `tool_use` block lies inside a `review_rounds.detect_round_windows` window whose opening record falls in the window, split by round skill (`review_rounds.REVIEW_SKILLS`).
  - The window runs from `--since` at 00:00:00Z up to, not including, 00:00:00Z on the day after `--until`.
- **File roles.**
  - A *diff handoff* is a file whose parent directory is named exactly `code-review-diff-markers` or `cumulative-review-diff-markers`. Those are the two directories `pr-diff-against-base.sh`:76 and :86 write reviewers' diffs into. Every other file is a *reviewed file*.
  - Reviewed files split by `read_cost._file_kind` into `code/other` and prose. Prose is its `instruction` and `other_prose` kinds (row 72).
  - `instruction` is decided by path, whatever the extension, so prose also holds code and JSON files under `skills/`. The printed label for prose names both kinds and says `instruction` is matched by path.
  - The headline and the outcome tables count reviewed files only. A partial read of the review diff and a partial read of a changed file mean different things for #1115.
- **Outcome of each whole-file Read.** A whole-file call has no `offset` and no `limit`, the predicate `read_cost.py`:224 already applies. The predicate applies to failed calls as to successful ones. Each whole-file call takes the first class below that fits, so a call whose fields overlap two classes has one answer (M4):
  1. `refused_over_limit`: a failed call whose error text holds `exceeds maximum allowed`, the phrase both refusal wordings share (row 7). The phrase matches case-sensitively, so a differently cased copy falls to class 2. The reviewer got no lines.
  2. `other_error`: any other failed call. One whose text holds `File content (`, or `exceed`, `maximum` or `too large` in any case, also counts as `unrecognised_limit_error`. A nonzero count there means the harness used a refusal wording the instrument does not know.
  3. `size_unknown`: a success whose structured fields failed a check (M2). It prints by reason.
  4. `partial_token_cap`: `truncatedByTokenCap: true`, whatever `startLine`, `numLines` and `allow_large` say.
  5. `size_unknown` under the reason `start_after_first_line`: `startLine` above 1.
  6. `size_unknown` under the reason `lines_exceed_total`: `numLines` above `totalLines`.
  7. `complete_allow_large`: `numLines` equal to `totalLines`, with `allow_large: true`.
  8. `complete`: `numLines` equal to `totalLines`. An empty file, with both counts 0 and `startLine` 0 or 1, is complete.
  9. `partial_unflagged`: `numLines` below `totalLines`. That is the 2,000-line default limit, or a harness version without the flag.
- **Targeted calls**, which carry an `offset` or a `limit`, take no outcome class, a refused one included.
  - They enter no outcome table, no headline count and no follow-up population, so the headline's numerator and denominator hold whole-file calls alone.
  - In reviewer windows:
    - A targeted call appears in the call counts only as a later Read under follow-up and coverage.
    - A refused `limit`-only call therefore leaves no trace in the call counts.
    - A successful targeted call adds its weight to the Read share.
    - A successful targeted call's `totalLines` can set the size bucket of a whole-file call on the same path in the same window that has none of its own.
  - Main-thread round Reads count them beside whole-file calls.
- **Size bucket**, by the file's `totalLines`: up to 1,000, an empty file included; 1,001–2,000; over 2,000; unknown. A call without its own `totalLines` takes the largest one any call saw for that path in the same window.
- **Headline, for GH-1529's first question.**
  - *Partial* means `partial_token_cap` or `partial_unflagged`. *Refused* means `refused_over_limit`. The report prints them apart and never calls a refused read partial.
  - A whole-file call is *larger than one Read call* when any of these holds:
    - it is partial or refused;
    - it is `complete` or `complete_allow_large` on a file over 2,000 lines;
    - it is `complete_allow_large` with estimated tokens of 25,000 or more at 4 characters per token (G3).
  - A plain `complete` call came back whole from one default call, so the harness's own count put it under the cap. Its estimate therefore never moves it into the denominator.
  - The headline is partial calls, refused calls and their sum, each over the larger-than-one-call reviewed-file calls. It prints for `code/other`, for prose, and pooled.
  - Beside it prints the count of `complete_allow_large` calls on files of 2,000 lines or fewer whose estimated tokens fall from 20,000 to 29,999. In that band the estimate alone decides whether a call enters the denominator.
  - `other_error` and `size_unknown` calls stay out of the denominator. Their counts print beside it.
- **Follow-up and coverage**, reviewer windows only, per partial or refused whole-file call (M6):
  - A call's place in its window is its `call_order`, the position of the first `tool_use` block carrying its id (row 88).
  - `later_offset_read`: a later Read of the same path in the same window carries `offset`, whether it succeeded or failed.
  - `covered_after`: the union of `[startLine, startLine + numLines − 1]` over the call itself and that window's later successful Reads of the path covers `[1, totalLines]`.
    - The union is computed over intervals, never over a set of line numbers.
    - A Read whose structured fields are `None` adds no interval.
    - A result flagged `truncatedByTokenCap` whose reported range reaches the file's last line adds no interval, because the flag means the result stopped before the end of the file (row 90). A flagged result that ends short of the last line still adds its reported range.
    - A call whose file size is unknown is never covered.
  - `neither`: no later offset Read and not covered after. Its printed label says what it counts: no later offset Read, and not covered by later Reads.
    - It is an upper bound on calls after which the reviewer made no further attempt to read on, because the instrument sees Read calls only. A recovery by Grep, Bash or a diff read is not seen, and its call counts here.
  - All three print for `code/other`, for prose, and for diff handoffs.
- **Read share of reviewer spend, for GH-1529's second question.**
  - The share is the reviewer windows' summed `read_cost._read_weight` over successful Reads, divided by those windows' own summed billed weight from `read_cost._new_billed_weight` (row 29). Its label says it is a share of modeled billed weight, not of tokens.
  - These parts of that Read weight print as shares of it:
    - Read weight on files over 1,000 lines, pooled and for `code/other` reviewed files;
    - the diff-handoff part of the over-1,000-line weight;
    - the unknown-size part.
  - Raw sums print with the shares, under read-cost's own unit caption.
- **Rates.** Every rate prints with its numerator and denominator (M16).
  - A zero denominator prints `no data (0/0)`, never `0.0%`.
  - A count denominator below 10 prints `insufficient (n/d)`.
  - A share of billed or Read weight takes the same floor on the number of reviewer windows behind it.
- **Per reviewer type**, as counts only (M14):
  - Each tracked reviewer type, plus a total, prints windows, and partial, refused and larger-than-one-call reviewed-file calls.
  - Rates and weights print pooled, never per type.
  - Untracked names fold into one row labelled `subagent_mix._WITHHELD_AGENT_TYPE_LABEL`, as read-cost folds them (row 20). The fold is local to `reviewer_reads.py`, because read-cost's builds its own row type (dispatch 1c).
- **Main-thread round Reads**, per round skill, as counts with no rate:
  - round windows that opened in the window;
  - Read calls inside them, whole-file and targeted;
  - whole-file reviewed-file calls by outcome class, and by size bucket;
  - whole-file diff-handoff calls.
  - The join and the outcome classes count different populations.
    - The join counts each Read `tool_use` block in a round window once by id, dropping only repeats inside that window.
    - The outcome and bucket counts take only calls `read_cost._scan_window` classified. The scan skips an id already seen in an earlier window or file of the run, and a call with no usable result (`read_cost.py`:377-417).
    - Such a call counts among the whole-file calls and in no outcome, so the outcome counts plus the diff-handoff calls can fall short of the whole-file calls. That gap is not a defect, and the page must not read it as one (Capture step 9).
- **Reviewer-yield.** `reviewer_yield.compute_reviewer_yield_data` runs over a second, subagent-inclusive iterator built from the same single root and scope (M9). It renders with the same fold: dispatches, verdict mix, findings, and cited/active/edited.
  - The report repeats reviewer-yield's caveat that `--until` does not bound the edit table (`reviewer_yield.py`:729-730).
  - The second pass keeps its own gap counter. On a completed pass it prints that counter's total on this section's line. Only the first pass's counter feeds the skipped-input line.
  - When the shared `reviewer_yield` or `corpus` code raises an `AttributeError`, `TypeError`, `ValueError` or `RecursionError` on a record or sidecar it cannot take, the pass ends (`reviewer_reads.py`:756-761).
    - A field of the wrong type can come from a record or a sidecar. JSON nested past the decoder's stack reaches this catch only from a `.meta.json` sidecar.
    - A transcript line nested that deep, or holding an integer over the interpreter's digit limit, never reaches it. `corpus._parse_jsonl_records` lets either exception out (`corpus.py`:111-116), so the run ends with a traceback in the first pass, before the yield pass. This PR leaves that as it is (Out of scope).
    - One fixed notice, starting `reviewer-yield pass: not completed`, prints in place of the gap-counter line and the yield rows. It names the four exception classes and prints no count. The exception text is dropped, because it can hold record content.
    - The exit status stays 0, so Verification step 4's yield-completed floor checks the report for the notice.
    - Any other exception propagates.
- **Review-ledger dispositions** (M10), over the files `publication_scope._this_repo_ledger_files` selects (M15):
  - A selected file counts as unreadable, and none of its rows count, when it is not a regular file at its `lstat`, when its read prints anything, or when the read raises `ValueError` or `RecursionError` (M15, M20).
  - Each row is reduced on read to `session_id`, `disposition`, `decided_by`, `id`, `ref` and `event_time` (M20).
  - Each kept field has one rule for absence and one for a wrong type:
    - A row whose `disposition` is absent or not a string is left out under `disposition`.
    - A row whose `event_time` is absent, not a string, or not the writer's `YYYY-MM-DDTHH:MM:SSZ` form is left out under `event_time` (row 79).
    - An absent or empty `id`, `ref` or `decided_by` reads as no value. A present one that is not a string leaves the row out under that field.
    - `session_id`:
      - It comes from the row alone, never from the file name (row 12).
      - A row without a valid one enters the disposition counts and no session line.
      - A non-string one leaves the row out under that field.
  - A *disposition row* is an ADDRESS, DEFER or SETTLED row that is not a carry.
    - The ledger's own *decision* is a narrower set, a non-carry DEFER or SETTLED row with an id (row 79). The report, the docs and the page therefore say "disposition row".
    - CLEAN and CONSULT rows are neither. Any other `disposition` string counts as unknown and never prints by value.
    - An id-less disposition row is counted apart. It supersedes nothing and is never terminal.
  - A disposition row is superseded when a later disposition row in the same file, in file order, names its `id` as `ref` with an `event_time` before the window's end.
    - File order is append order, and a superseder always follows the row it names, because `append` accepts a `--ref` only to a row already in that file (row 78).
    - A self-`ref` is never later than itself. In a `ref` cycle only the later row supersedes, so no chain drops.
  - A terminal row is an unsuperseded disposition row with an id whose `event_time` falls in the window.
  - It counts decisions, not distinct findings. A finding re-raised in a later round without `--ref` counts again.
  - It prints terminal rows by disposition, and their ADDRESS and DEFER shares under the rate rule. Both shares are over all terminal rows, so SETTLED's share is the remainder.
  - For the capturer, it prints id-less disposition rows, unknown dispositions, rows left out by field, ledger files read, unreadable ledger files, and whether the ledger directory is present, absent or unreadable. Listing gaps go to a counter the ledger section owns, never to the skipped-input line.
  - It prints sessions with a disposition row in the window, and how many of those the transcript scan covered.
- **Comparability** (M19): reviewer windows by harness version and by model.
  - A window's version is the `version` of its first record carrying one.
    - It prints only when it is a string that fully matches ASCII digits joined by dots, in two to four parts of one to four digits each.
    - Any other value prints as `other`. A window whose records carry none prints as `unknown`.
  - A window's model is its first assistant record's `message.model`.
    - It prints by name only when it is a string that is a key of pricing's `_MODEL_BASE_INPUT_RATES`, a model priced by prompt length such as `claude-haiku-5-5` included (row 92).
    - Any other value, a non-string included, prints as `other`, and the run goes on (row 82).
- **Diagnostics.**
  - Read-cost's skipped-input line and `pricing._warn_if_subagent_format_drift`.
  - Reviewer windows with no timestamped record, and review-round windows whose opening record has no parsable timestamp (`round_windows_without_timestamp`). Neither count is limited to the date window, because an untimestamped window cannot be placed in it.
  - `skill-fidelity-reviewer` windows left out (M17).
  - Unexplained partials: `partial_unflagged` calls on files of 2,000 lines or fewer. The default line limit cannot explain them.
  - Notice agreement (row 5), as three counts:
    - `partial_token_cap` calls that no `read_truncation_notice` record names;
    - such records that name neither a `partial_token_cap` call nor a `size_unknown` one;
    - such records that name a `size_unknown` call. That call's fields failed a check, so the pairing cannot be tested on it. A batched record (`multi_result_record`) is the expected cause.
  - `size_unknown` calls by reason, and `other_error` calls with their `unrecognised_limit_error` part.
    - The reason names are module constants, because an after-run compares them.
    - The largest reason is expected to be `multi_result_record`. That is the harness writing one record for several results (row 6), not an instrument defect.

**Delivery: two PRs** (M12).
- PR 1, on this branch, carries Phase 1's three dispatches and this plan file, which ships with the implementation it plans (row 47).
  - Its body cites GH-1529 with no closing keyword. `/pr-description` adds a `Fixes` line by default, which comes out by hand (row 26).
  - Before it opens, the session drafts the late-findings issue under #1113 (row 52).
    - The draft states that #1115 should not merge until a late-findings before-value exists or the owner accepts losing it.
    - The draft names the clock: transcripts and ledger files age out on the same rolling windows as this baseline's inputs (G1, row 38).
    - The draft asks the epic's owner to add an unchecked late-findings item to #1113's task list, listed as blocking #1115, or to amend #1115's "Blocked by" line. The epic is the owner's (G4), so the session edits neither issue.
    - The session asks the engineer to approve the text before posting it, and posts nothing without that approval.
    - Once it is posted, PR 1's and PR 2's bodies cite it by number.
  - Before it opens, a dry run of the capture and the self-checks runs (Verification step 3).
  - Its body states three things, none of them a figure:
    - The worktree-cleanup hold: from the first dry run until PR 2's capture run passes Verification step 4's checks, neither cleanup script runs without `--dry-run`, from any directory, `cleanup-merged-branches --all-projects` included (row 65). A removed worktree's sessions and ledger files leave the scope (row 15).
    - The commit the last dry run ran at, as its 12-character short id. A full commit id trips the redaction gate's long-hex detector (row 66).
    - The re-dry-run rule: a later commit touching `reviewer_reads`, `read_cost`, `ledger_dispositions`, `publication_scope` or `reviewer_yield` needs a fresh dry run before the engineer merges.
  - Its body also states PR 1's changed-line count, measured when it opens, beside the about 4,250 lines row 89 answered (row 93). That count sizes the diff and is not a figure from the corpus.
- PR 2 runs on a new branch cut from the default branch after PR 1 merges. It carries the capture page and its index line, edits no plan file, and cites this plan by its merged path.
  - Its body's only closing line is `Fixes #1529`.
  - Its body states that a revert of PR 1 must follow a revert of PR 2, because the page cites PR 1's command and its redaction-doc bullet.
  - Its body states that ticking #1113's "A-field baseline captured" box does not cover #1115's late-findings watch.
  - Its body repeats the late-findings issue's request to the epic's owner, and cites the issue by number.

**Capture (PR 2).** One run, from the PR 2 worktree (row 75).

1. Cut PR 2's branch and worktree per `branch-management`. Its `worktree-ensure.sh` starts the worktree from the fetched default tip (row 64), so no other checkout is updated.
2. Run `git diff --stat <dry-run commit> HEAD --` over the five instrument modules' files, with the 12-character commit id PR 1's body names, as is.
   - A nonempty diff, or a commit git cannot find, means the merged instrument was never dry-run.
   - In that case Verification step 4's by-hand trace also runs on this capture.
3. Compute the window in UTC, with Python, immediately before the run.
   - `<U>` is the UTC day before the run. `<S>` is 27 days before `<U>`.
   - Look up `cleanupPeriodDays` with `grep -o` for that one key in the pinned account's `settings.json`, so no other setting enters the session. An absent key means the 30-day default (G1).
   - A value below 30 moves `<S>` to that value less three days before `<U>`.
   - The window then ends at least 24 hours before day `<S>`'s oldest records can age out. It also sits inside the 30-day ledger sweep floor (row 38).
4. Pin the account holding this clone's sessions. The command sets `CLAUDE_CONFIG_DIR` to that literal directory (row 63). The value appears in no artifact, which Verification step 6 checks.
5. Run the command once.
   - First create the scratch directory in its own call: `mktemp -d /tmp/reviewer-reads.XXXXXX`. Later calls spell the printed path out literally, double-quoted.
   - Then, from the PR 2 worktree's root, in the background: `CLAUDE_CONFIG_DIR="<dir>" python3 claude/.claude/scripts/transcript-analysis.py reviewer-reads --this-repo --since <S> --until <U> > "<scratch>/stdout.txt" 2> "<scratch>/stderr.txt"`.
   - Two shapes in that command are unverified: the literal assignment and the redirect outside the worktree (row 85). If the session's Bash guard refuses either, the engineer runs the whole command in a separate terminal, and the session reads the two files.
   - The dry run records which shapes the guard accepted. The guard's refusals do not reproduce on demand (row 85), so this run is its own test.
6. Run Verification steps 4 and 5 before writing the page.
   - Only once Verification step 4's checks pass does the session tell the engineer the cleanup hold is released.
   - A failed check keeps the hold, so a re-run sees the same worktrees.
   - The engineer's go-ahead at a sample-check stop counts as that check passing, so the release follows it, while a request to re-run keeps the hold.
7. `docs/case-studies/reviewer-read-field-baseline.md` states:
   - the command with the directory elided, the run timestamp, the window, and `cleanupPeriodDays` as read or as absent, with no path;
   - the instrument commit, as the PR 2 worktree's 12-character short commit id;
   - the report as printed, less the ledger section's lines for the capturer and the yield pass's gap counter, with one line in their place stating that Verification step 4's checks passed;
   - the header's project-directory count under the name "worktrees listed", because it counts `git worktree list` entries (row 81);
   - the headline answers to GH-1529's two questions, worded as "partial or refused" and as a share of modeled billed weight;
   - the comparability record in step 8;
   - as confounders, `git log --oneline` over the window for `claude-skills/skills/code-review/SKILL.md` and the agent files the population matches, and the merge dates of #1113's file-splitting children as #1113's task list names them at the run;
   - that #1115 was unmerged at the run;
   - the limitations in step 9;
   - that it records no late-findings before-value, and that the measure moved to its own issue (row 51), cited by number. If no issue has been posted by PR 2, the page says instead that no issue has been opened;
   - that ticking #1113's box does not cover #1115's late-findings watch.
   - The page uses none of `pooled across`, `machine-wide`, `cross-machine` or `multi-account`, the phrases a doc test reserves for grandfathered pages (row 83).
8. The comparability record names:
   - the version and model counts from the report;
   - the model labels' reference: they follow pricing's `_MODEL_BASE_INPUT_RATES` at the instrument commit step 7 names. A model priced after that commit prints `other` here and by name in an after-run, so that move alone is not a model shift (M19);
   - the re-run recipe: this clone, from a worktree cut from the default branch, the same window length, the same pinned account, and a run before any worktree cleanup;
   - the modules whose later edits void a comparison: `read_cost`'s scanner and weights, `reviewer_reads`, `ledger_dispositions`, `publication_scope`, and `reviewer_yield._is_reviewer_subagent_type`;
   - the main-thread round counts per skill, as the only indicator of the review-skill mix behind the reviewer figures;
   - per figure, what a rise or fall after #1115 can and cannot show, read against #1115's body as row 59 records it:
     - Headline partial and refused rates: before-state only. #1115's entry read is still one default Read, so the rate can hold or rise while reviewers handle a partial view as #1115 prescribes.
     - Larger-than-one-call calls per reviewer window: a fall shows fewer whole-file attempts on large files. No fall does not show #1115 failing, because the entry read still probes such files unless line counts arrive beforehand.
     - Per-type counts are the only place #1115's per-lens exceptions show. `ciso-reviewer`'s and `staff-data-engineer`'s counts may fall less, because #1115 keeps their CI and policy config files and their migrations whole.
     - `covered_after` per reviewer window: before-state only. #1115 replaces paging through the rest of a file with an outline and a function-context diff, so a fall is by design.
     - `later_offset_read` per reviewer window: it can rise on #1115's fallback of reading an enclosing function's range. A rise does not show that the rest of the file was read.
     - `neither` per reviewer window: before-state only. #1115's outline and diff are invisible to the instrument, while its fallback adds a ranged Read the instrument counts. Its direction therefore cannot be predicted.
     - The Read share and its over-1,000-line part: neither direction identifies #1115 working. Its mandatory expansions add Reads of other files while its entry rule cuts Reads of large changed files.
     - The ledger dispositions: a move shows a change in the mix of terminal disposition rows. A finding re-raised without `--ref` adds a row, so re-raising can move the mix as well as resolution. It cannot attribute that change to how files were read.
9. The limitations the page lists:
   - rows 9, 11, 18 and 23;
   - this clone only: sessions recorded under any other clone of the repository are not included (row 75);
   - live worktrees only, so removed worktrees' sessions are not included (row 15), and the sample is not a random sample of reviews;
   - both halves of the scope rest on path identity, not repository identity, so the scope does not exclude the cases row 84 lists;
   - the ledger reader's regular-file check does not exclude a hard link named for this checkout, or a swap between its `lstat` and the open (M15);
   - per round skill, the whole-file calls can exceed the outcome counts plus the diff-handoff calls, for the reason Approach's Main-thread round Reads states. The page states that the gap is not a defect;
   - reviewer windows include plan-review dispatches, whose reads of code files stay in `code/other`, and per-type rows do not isolate the review skill (M17);
   - prose is `instruction` plus `other_prose` (row 72). `instruction` is decided by path, whatever the extension, so it also holds code and JSON files under `skills/`. Only its markdown part lies outside #1115 for every reviewer. `other_prose` lies outside it for `comment-discipline-reviewer` alone (row 59);
   - ADDRESS and DEFER shares count disposition rows, and a finding re-raised without `--ref` counts again;
   - `neither` is an upper bound on calls with no further attempt to read on, because Grep, Bash and diff reads are not seen;
   - `covered_after` can be wrong at a flagged result's last reported line, in both directions (row 90):
     - A flagged range that ends short of the file's last line still adds `[1, numLines]`, though line `numLines` can have arrived only in part. A later Read from `numLines + 1` can then make `covered_after` true with that line never fully read.
     - A flagged range that reaches the file's last line adds no interval, though lines 1 to `numLines − 1` arrived whole. A later Read of only the last line then leaves `covered_after` false for a fully read file.
     - Dropping the whole range in the second case is a deliberate conservatism: it under-credits a call and never over-credits one. No field the instrument reads records which lines arrived whole. Keeping all but the last line would therefore rest on row 90's reading of the cut, which covers two harness versions only.
     - `docs/transcript-analysis.md`'s `reviewer-reads` Known limits carries the same statement. It lands in a PR 1 doc commit before PR 1 opens.
   - the window holds this change's own review rounds, as an after-run's window will hold #1115's.
10. PR 2 closes GH-1529 and no other issue. One human step follows its merge (G4): ticking #1113's "A-field baseline captured" box with the date and the page's path. PR 2's body and the page (step 7) state what that tick does not cover.

**Assumption ledger**

**Root:** Reviewer agents are told to read every changed file fully, and a whole-file Read stops at the Read tool's per-call limits. Nothing measures how often reviewers' whole-file reads come back partial or refused, whether reviewers read the rest, or what share of their spend goes to Read. #1115 changes that instruction. The field measurement must therefore be captured from pre-change transcripts and ledgers first.

**Givens:**
- G1. Transcripts age out under Claude Code's `cleanupPeriodDays`, default 30 days. Reason: the harness owns transcript retention. `[verified: docs/pr-cost.md:3]`
- G2. A published figure from this repository's own corpus must come from a command that refuses a wider corpus, cited beside the figure. Every new figure also takes the grandfathered-set check. Reason: `CLAUDE.md` binds every contribution to that policy, and loosening it needs the owner's decision outside this plan. `[verified: CLAUDE.md:162-171; docs/private-project-redaction.md:97-149, :316-331]`
- G3. The Read tool caps one call at 25,000 tokens. It reads up to 2,000 lines by default. The harness decides the shape of a truncated result. Reason: the harness owns tool behavior. `[verified: claude-skills/skills/code-review/REFERENCES.md:194-216; this session's Read tool description, "Reads up to 2000 lines by default."]`
- G4. #1113 gates #1115 on this baseline, and #1113's checkbox and #1115's merge order belong to the epic's owner. Reason: another party owns the epic. `[verified: gh issue view output for GH-1529 and #1113, read by the main session on 2026-11-20; GH-1529 says "#1115 (B) may not merge before the A-field baseline is captured."; #1113's task list, headed "Status as of 2026-11-19.", holds "A-field baseline captured (date, where the measurement lives)" and "#1115 — B: Reviewer read methodology (blocked by both checkboxes above)"]`

**Mechanisms:**
- M1 — A new `reviewer-reads` subcommand in a new module. `anchors: row16, row17, row24, row30, G2`
  - It is heavier than adding lines to an existing report. The lighter primitives each fail:
    - Extending `read-scope`: it has no agent type, no billed weight, no file size and no scope refusal. A2 would therefore reuse none of it. `read_scope.py` would also pass the 1,000-line limit. `anchors: row17, row24`
    - Extending `read-cost`: its report has no date window, and `read_cost.py` would pass the limit. `anchors: row16, row24`
    - A one-off script: G2 needs a refusing command a reader can re-run, and #1115's after-measurement re-runs the same command over a later window. `anchors: G2`
- M2 — `read_cost._scan_window` carries each Read's structured result fields, its failed calls and the truncation-notice ids, so one scanner pairs Read calls for both reports. `anchors: row5, row6, row7, row8, row16, row60, row61, row87, row88`
  - Each structured field is checked before use. A failed check leaves the field `None` and names the check, and those names print as the `size_unknown` reasons. They test rows 6 and 10 against this repository's corpus on every run.
  - A failed call keeps only its limit-refusal class (M4), never its error text.
  - Rejected: parsing the `PARTIAL view` text out of the result. Whether the result text carries it at all is unverified (row 5), and it names only the token-cap case. `anchors: row5`
  - Rejected: `read_truncation_notice` records as the primary signal. They cover the token-cap case only and give no size for a complete or paged Read. They stay as the notice-agreement cross-check. `anchors: row5, row6`
  - Rejected: a second scanner in the new module. It would duplicate the pairing, turn-count and compaction-window logic read-cost's weights depend on.
- M3 — Read-cost's single-account root, scope refusal and scope header move into a new `publication_scope.py`, with the command label as a parameter. `anchors: G2, row16, row24, row68`
  - `scope.py` owns scope refusals (`scope.py`:694-708), but it already has 1,161 lines (row 24). A new module limits `scope.py`'s growth to one extracted function (M15) and one tuple entry.
  - Rejected: calling read-cost's helpers as they stand. They print `read-cost:` in another command's refusals.
  - Rejected: copying them. A reader re-running the refusal must be checking one rule.
- M4 — Outcomes are classified from structured fields. `partial_unflagged` stays apart from `partial_token_cap`, and refused calls stay apart from both. `anchors: row5, row6, row7, row8, row9, row10`
  - One precedence order, Approach's numbered outcome list, gives every overlapping record one class.
  - A refusal is recognised by the phrase both known wordings share, not by either wording, because the wording differs by call shape (row 7). A refusal-shaped text the phrase misses prints as `unrecognised_limit_error`.
  - Rejected: one wording per call shape. A harness version that rewords either would move refusals into `other_error` with no signal.
- M5 — Size buckets break at 1,000 and 2,000 lines, beside the diff-handoff role and `read_cost._file_kind`'s prose split. `anchors: row6, row9, row23, row72, G3`
  - 1,000 is GH-1529's own threshold and the rough single-call page (G3). 2,000 is the default line limit (G3).
  - The headline's denominator is defined by file size, so it matches GH-1529's "files larger than one Read call". `anchors: G3`
  - The token estimate applies only to `complete_allow_large`, the one complete class the harness's own cap does not vouch for. `anchors: G3`
  - Diff-handoff calls print as their own rows. `anchors: row34, row35`
- M6 — Follow-up and coverage are counted per partial or refused call, as `later_offset_read`, `covered_after` and `neither`. `anchors: row6, row7, row34, row90`
  - A later offset Read can be a targeted read of one function. `covered_after` is therefore the figure for reading the rest.
  - A flagged result whose range reaches the file's last line adds no interval, because a flagged range reaches `totalLines` only when its last reported line arrived in part (row 90). Capture step 9's limitations state the bias this leaves in both directions, and why the whole range drops. `anchors: row90`
  - `neither` is an upper bound on calls with no further attempt to read on, because the instrument sees Read calls only.
  - Rejected: the bench-compatible paged-follow-up count. The reduced forms cut it, and the bench's own partial detection may read zero (row 21). `anchors: row21, row34`
- M7 — The Read share divides by the reviewer windows' own billed weight. `anchors: row2, row29`
- M8 — Main-thread round Reads join to round windows by `tool_use` id over deduplicated records. `anchors: row19`
- M9 — Reviewer-yield is embedded through `compute_reviewer_yield_data` and folded, and `_is_reviewer_subagent_type` stays in `reviewer_yield.py`. `anchors: row18, row20, row22`
  - The second iterator is a second pass over the corpus, built from the one root `publication_scope` returns.
  - Rejected: teeing one iterator, which buffers every session's records.
- M10 — Ledger dispositions count each decision chain's terminal row, as of the window's end. `anchors: row1, row12, row13, row42, row53, row78, row79`
  - Only superseders before the window's end count. A re-run of the same window therefore gives the same counts while the files survive.
  - Carries are left out on both sides. A DEFER that is only carried stays its chain's terminal row.
  - Supersession follows file order, which the writer makes append order (row 78).
  - Rejected: a strictly later `event_time`. It has one-second resolution (row 78), so two appends in one second would supersede nothing. `anchors: row78`
  - Rejected: a rate from `disposition` and `round` alone. It counts every carry and re-log as a new decision. `anchors: row13`
- M11 — `--since DATE` and `--until DATE` are both required, through `scope._parse_absolute_window_args` with `type=scope._iso_date`. `anchors: G1, row18`
  - A missing date exits 2 before any scan.
  - `_iso_date` accepts an unpadded date such as `2026-1-5`. `corpus._parse_ts` then rejects it. `_parse_absolute_window_args` therefore returns no bound for it (`scope.py`:1121-1161; staff-backend-engineer's round-3 interpreter check). A flag whose returned bound is none exits 2 before any scan, with the command label.
  - The order check compares the two returned values. It exits 2 before any scan when `since_ts` is not below `until_epoch`, the 00:00:00Z after the `--until` day, which is exactly `--since` after `--until`.
  - Rejected: `--since Nd`. A relative window cannot be re-run to the same figures, and `read_scope.py`:610-613's flag bounds only growth.
- M12 — Two PRs. PR 1 ships the instrument and this plan. PR 2, on a new branch cut from the default branch after PR 1 merges, captures once from its own worktree, records the page, and closes GH-1529. `anchors: row3, row15, row26, row27, row28, row31, row32, row47, row50, row75, G1, G4`
  - Rejected: one PR. Row 4 chose it, and row 31 supersedes it.
  - Rejected: PR 2 on this branch. A branch cut from the updated default branch holds exactly the merged command, whatever merge method PR 1 lands by.
  - Rejected: a plan file in PR 2. It would restate this plan, and a new or modified plan file arms `require-plan-review.sh` for a page-only change. `anchors: row47`
- M13 — Retired. It placed late findings for #1115's watch, which moved to its own issue. `anchors: row51`
- M14 — Per-type rows print counts only, and rates and weights stay pooled. `anchors: row20, row34, row35`
  - Rejected: per-type billed weight and Read weight. No figure the report states reads them, and the per-lens exceptions #1115 keeps show in the counts (row 59). `anchors: row59`
- M15 — Ledger files are selected by their repository-hash slot against this checkout's worktree paths. `anchors: row14, row53, row73, row74, row80, row84, row91, G2`
  - The repository hash is the sha256 of the worktree path `review-ledger.sh` ran in (row 53). The command hashes each path `scope._repo_worktree_paths` returns, as printed and as resolved, and opens only files whose name matches.
  - Of those it reads only regular files, by a point-in-time `lstat` check on the name. A symlink or other non-regular entry is refused before any open, as the writer refuses one (row 91), so a matching symlink never contributes its target's rows. `anchors: row91`
    - The check is not an atomic no-follow open, and it does not detect a hard link, which is a regular file. The writer's own check has the same two limits (row 91).
    - A hard link named for this checkout, or a swap between the `lstat` and the open, therefore still reads rows stored under another name.
    - Either needs same-user write access to the ledger directory. The threat model this change was reviewed under, untrusted transcript content, does not supply that actor (ledger id `476e30a33ba4`'s rationale). The docs section and the page list both as known limits.
  - One call to `_repo_worktree_paths` feeds both the transcript scope and the ledger scope, so the two cannot see different worktree sets. A command-level test counts that call.
  - The hash mirrors a one-line formula whose home is `_marker_lib_repo_hash`. A test runs both on the same paths, so the copy cannot drift.
  - A unit case with a symlinked worktree path fails if either the printed or the resolved half is dropped.
  - A hash miss on every path would read as an empty ledger. Verification step 4's ledger floor tells the two apart from two printed counts, because every `/code-review` round appends a ledger row (row 80).
  - Path identity leaves the non-exclusions row 84 lists. The redaction-doc bullet, the docs section and the page each state them.
  - It is heavier than reading every ledger file. The lighter primitives each fail:
    - Attributing rows by session alone: a session that started here can append to another repository's ledger, and those rows would count. `anchors: row14`
    - The rendered ledger block in this repository's PR bodies: `render` publishes live decisions only, and reading PR bodies needs `gh` and the network. `anchors: row74`
    - Leaving the ledger dispositions out: row 1 includes them. `anchors: row1`
  - Declined: a second identity layer beyond the path, such as tree resolution. The transcript scope beside it is path identity too (row 53), so a stricter rule on the ledger half would not strengthen the page's scope.
    - The regular-file rule is not such a layer. It holds the reader to the writer's own rule (row 91) and leaves path identity as the scope.
    - That rule reverses round 3's DEFER of the finding that a non-regular entry would be opened (ledger id `476e30a33ba4`). The DEFER rested on a dangling symlink staying listed so its open counts it. The plan no longer relies on that DEFER.
- M16 — Rates print `no data` at a zero denominator and `insufficient` below a floor of 10. `anchors: row54`
  - The shape follows reviewer-yield's Active floor and its `insufficient` label, which `cost_ledger` reuses. The label is imported from `reviewer_yield`.
  - The floor is the command's own constant, so a later change to reviewer-yield's floor cannot shift this baseline's comparison.
- M17 — The reviewer population leaves out `skill-fidelity-reviewer`, keeps plan-review dispatches, and splits reviewed files into `code/other` and prose. `anchors: row57, row58, row59, row72`
  - `skill-fidelity-reviewer`'s body carries no read-every-changed-file instruction, so #1115's change does not reach it (row 57). Its windows print as a left-out count.
  - Plan-review and code-review dispatches of one reviewer type share the instruction #1115 replaces, and `.meta.json` names no dispatching skill (row 58). The prose split separates their plan-file reads.
  - Rejected: joining `.meta.json`'s `toolUseId` to a main-thread round window. A reviewer a subagent dispatched names a call no main-thread window holds (row 18), so the join would leave those windows unattributed. `anchors: row18`
- M18 — Failed Reads are deduplicated by their own seen-id set, which read-cost never passes. `anchors: row60, row88`
  - A failed call's id enters the set at its first failure. A replay therefore counts once within a window as across windows (row 88).
  - A call's `call_order` comes from the first `tool_use` block carrying its id, and a replayed block takes no new number. A Read between the two blocks therefore still orders after the call.
  - Rejected: adding failed ids to the success set. A replayed failed Read would then raise read-cost's `repeated_reads` figure, against the test row 60 cites.
  - Rejected: no deduplication. A replayed failed Read would count twice in `refused_over_limit` or `other_error`, moving the headline's numerator and denominator together.
- M19 — Reviewer windows are counted by harness version and by model, so an after-run can see whether either moved. `anchors: row70, row82, row92, G3`
  - Values print only in a known form, because a record's text is untrusted input.
  - The version takes a bounded ASCII full match.
  - The model prints only as a string that is a key of pricing's `_MODEL_BASE_INPUT_RATES`. The string check precedes the lookup, so an unhashable value never reaches it and no `TypeError` path remains (row 82).
  - Rejected: `pricing._model_rates` as the test. It returns `None` for a model priced by prompt length, so `claude-haiku-5-5` would print as `other`. `anchors: row92`
  - Known limit: the label depends on pricing's table at the run's commit. A model unpriced at the capture prints `other`, and an after-run whose table has gained it prints it by name, so the move can read as a model shift that did not happen. The page's comparability record names the instrument commit as the table's reference (Capture step 8).
- M20 — The ledger reader's stderr passes through a buffer, and a file whose read printed anything counts as unreadable. `anchors: row62`
  - `author_outcome._read_ledger_rows_from_file` prints the file's path on an open failure, and that name carries the repository hash and a session id. `routing_guard` already wraps a reader this way.
  - Rows are reduced to the six fields M10 reads right after the read, so no later diagnostic can reach a finding or a quote.
  - The reader catches neither `ValueError`, which a line holding an integer over the interpreter's digit limit raises, nor `RecursionError`, which a line nested past the decoder's stack raises. The command catches both, counts the file unreadable, and drops the exception unreported (`ledger_dispositions.py`:142-145).
  - Rejected: changing `author_outcome`'s own line. Its own command prints it, and the file has 993 lines (row 24).

**Assumptions:**
1. The ledger reader is included and reads counts only. `[engineer-verified: "Include, counts only (Recommended)"]`
2. The reviewer Read share is on the billed-weight basis. `[engineer-verified: "Billed weight (Recommended)"]`
3. The baseline lives on a repository page produced by a refusing mode. `[engineer-verified: "Repo page, refusing mode (Recommended)"]`
4. One PR carries the instrument and the baseline. `[engineer-verified: "One PR, instrument + baseline (Recommended)"]` Superseded by row 31, the engineer's later answer.
5. A truncated whole-file Read comes with a `PARTIAL view` notice. `REFERENCES.md` records the notice's text but not which transcript record carries it. `[verified: claude-skills/skills/code-review/REFERENCES.md:196-203]` In the records staff-backend-engineer's round-2 scan read, the notice's record has three properties:
   - it is a separate `attachment` record;
   - its `attachment.type` is `read_truncation_notice`;
   - its `attachment.toolUseID`, inside the `attachment` object and not on the record's top level, names the Read call.
   - `[verified: a count-only grep of this clone's own subagent transcripts for records holding a read_truncation_notice attachment: each such record carries one toolUseID, inside the attachment object, none before the attachment key]`
   - Whether the result text also carries the notice is `[unverified]`. The notice-agreement diagnostic tests the pairing on every run.
6. The `user` record carrying a Read result has three properties:
   - a top-level `toolUseResult.file` with `filePath`, `startLine`, `numLines` and `totalLines`, on paged Reads as on whole-file ones;
   - `truncatedByTokenCap` only on a truncated result;
   - `toolUseResult` as `None` when the record holds two or more `tool_result` blocks.
   - `[verified: staff-backend-engineer's round-2 bounded read-only scan of transcript records, shape evidence only]`
   - Another harness version can differ, so M2's checks and the `size_unknown` reasons test the shape on every run.
   - Repository docs record a top-level `toolUseResult` on other tools' result records. `[verified: docs/precompact-hook-behavior.md:148, :165]`
7. A Read refused for size fails with a wording that depends on the call's shape. `[verified: staff-backend-engineer's round-2 bounded read-only scan of transcript records, shape evidence only]`
   - A whole-file call over the byte-size limit reads `File content (N.NKB) exceeds maximum allowed size (NKB)`.
   - A paged call whose page exceeds the token cap reads `File content (N tokens) exceeds maximum allowed tokens (25000)`.
   - A whole-file call over the token cap returns a truncated success flagged `truncatedByTokenCap`, not an error.
   - The byte-size limit's value and the doc that states it are `[unverified]`. G3's source covers only the token cap.
   - Another harness version may word either refusal differently, which `unrecognised_limit_error` shows.
8. Read-cost's `whole_file` predicate tests only `offset` and `limit`, so a call passing `allow_large: true` with neither counts as whole-file. `[verified: read_cost.py:224]` Whether reviewers pass `allow_large` is unmeasured. `[unverified]`
9. What a 2,000-line default truncation of an under-cap file returns is not tested here. `partial_unflagged` catches it structurally whatever its shape. `[unverified]`
10. A complete Read reports `startLine + numLines − 1 == totalLines`. `[verified: staff-backend-engineer's round-2 bounded read-only scan of transcript records, shape evidence only]` The unexplained-partial diagnostic tests it on every run.
11. `_is_reviewer_subagent_type` matches bare agent-type names with no plugin namespace. `[verified: reviewer_yield.py:21-24, :347-352]` `.meta.json` `agentType` values are bare names in the records staff-backend-engineer's round-2 scan read. `[verified: that scan, shape evidence only]` A namespaced value on another version would fall outside the population.
12. Ledgers are aggregable within this repository, which is the finding GH-1529's ledger rates are conditional on.
    - A ledger file is named for the worktree path its rows were appended in, so this repository's files can be selected by name (row 53).
    - `author_outcome._row_session_id` attributes each row to a session. For a row with no `session_id` it falls back to the file name's second slot, which in a branch-keyed file is a branch hash. `[verified: author_outcome.py:310-336]` M10 therefore reads `session_id` from the row alone.
    - Every row gets a script-stamped `id`, and a `--ref` resolves within one ledger file. `[verified: docs/scripts.md:192, :279]`
    - Whether this repository's live ledger files hold rows from before ids existed is unmeasured, so M10 counts id-less disposition rows apart. `[unverified]`
13. Four row kinds re-log or retire a decision:
    - a carry (`--decided-by carry`) re-logs a live DEFER or engineer SETTLED decision by `--ref` and records a repeat raised that round;
    - a `--relog` row re-logs its `--ref` decision;
    - an ADDRESS with `--ref` closes the decision;
    - a DEFER or SETTLED with `--ref` supersedes it.
    - `[verified: review-ledger.sh:84-117; _review-ledger-lib.sh:277]`
14. Attributing ledger rows by session alone would count an in-scope session's rows written for another repository, because the ledger directory holds every repository's files. `[verified: author_outcome.py:302-307, :327-336]` M15 selects files by this checkout's worktree paths instead.
15. `--this-repo` reads only the current checkout's live `git worktree list` entries, so removed worktrees and other clones are skipped. `[verified: scope.py:96-203; docs/transcript-analysis.md:59, :67]` The capture runs from both clones, separately. `[engineer-verified: "Both clones, run separately (Recommended)"]` That second sentence is superseded by row 75, the engineer's later answer.
16. Read-cost already has the needed machinery. `[verified: read_cost.py]`
    - `_scan_window` (:172-256) pairs Read calls, drops failed calls and result text, and counts turns per compaction window.
    - `_read_subagent_windows` (:361-370) yields per-agent windows typed by `.meta.json`.
    - `_billed_weight`, `_read_weight` and `_new_billed_weight` (:157-169, :259-268) price them.
    - `_read_cost_roots`, `_refuse_wider_scope` and `_scope_header` (:388-422) hardcode the `read-cost` label.
17. `read_scope.py` (623 lines) splits Reads by `isSidechain` only (:301, :331), knows no agent type or file size, and refuses no wider scope. `[verified: read_scope.py]`
18. `compute_reviewer_yield_data` has four properties. `[verified: reviewer_yield.py:497-519, :553-555]`
    - It takes `since_ts` and `until_ts`.
    - It needs a subagent-inclusive iterator.
    - It counts only main-thread dispatches.
    - It bounds its edit table by `since_ts` alone.
    - Nested reviewer dispatches therefore appear in the read figures and not in the yield figures.
19. `review_rounds.detect_round_windows` returns record-index windows over deduplicated main-thread records, and deduplication merges an API call's blocks rather than dropping them. `[verified: review_rounds.py:197-236; pricing.py:256-282]`
20. Read-cost folds agent-type names this repository does not track into one withheld row, while reviewer-yield prints raw names. `[verified: read_cost.py:373-385, :441, :561-568; reviewer_yield.py:719-724]`
21. The bench counts a partial Read by a `PARTIAL view` substring in text built from `tool_result` content alone. `[verified: evals/review_bench/runner.py:103, :704-719, :835]` If the notice sits outside the result text (row 5), that count reads zero. Whether the bench's own sessions share that shape is unchecked. `[unverified]`
22. `code-file-size-splits.md` defers relocating `_is_reviewer_subagent_type` until A2 becomes a third in-package consumer. A2 imports `reviewer_yield` by module for `compute_reviewer_yield_data` anyway, so relocating the predicate removes no import. `[verified: .claude/plans/code-file-size-splits.md:395-398, :667]`
23. Reviewers receive the review diff as a file under `<config-dir>/code-review-diff-markers/` or `<config-dir>/cumulative-review-diff-markers/`. `[verified: pr-diff-against-base.sh:76, :86]` How often reviewers' whole-file Reads of those files come back partial is unmeasured. `[unverified]`
24. Line counts on this base:
    - `read_scope.py`: 623;
    - `read_cost.py`: 626;
    - `reviewer_yield.py`: 791;
    - `author_outcome.py`: 993;
    - `scope.py`: 1,161;
    - `tests/conftest.py`, which this plan grows: 1,973;
    - `test_transcript_scope.py`: 913;
    - `test_transcript_cli_bootstrap.py`, which it leaves alone: 1,440.
    - No test on this base enforces the 1,000-line limit.
    - `[verified: Grep line counts; docs/design-decisions/code-file-line-limit.md:19, :50-57; no line-limit test found under any tests directory]`
25. `select-tests.py` maps any change under `claude/.claude/scripts/` to that tree's whole test directory. `[verified: Step 3 research report of select-tests.py:734, not reopened]`
26. GH-1529's body says "Only the PR that records the A-field baseline closes this issue." It also says an earlier PR cites the issue with no closing keyword. It says `/pr-description` adds `Fixes` by default (#1528). That line therefore comes out by hand until #1528 lands. `[verified: gh issue view output for GH-1529, read by the main session on 2026-11-20]` PR 1 records no baseline, so its body carries no closing keyword. PR 2 records it, so its body's only closing line is `Fixes #1529`.
27. `docs/private-project-redaction.md` § "New figures against the grandfathered set" says to check a new figure "against Remediation's named list". That list names whole pages and named sections, `targeted-read-discipline.md` and `markdown-context-ingestion.md` among them. `[verified: docs/private-project-redaction.md:316-326, :339-360]` That entries on it also print review-dispatch, round and verdict counts is `[unverified: ciso-reviewer's round-2 read of three of its pages]`, so the check runs against every entry.
28. #1113's task list, headed "Status as of 2026-11-19.", shows #1115 unchecked and "blocked by both checkboxes above". `[verified: gh issue view output for #1113, read by the main session on 2026-11-20]` That is the epic's status on that date, not #1115's merge state at the capture run, so the capture run checks again that #1115 is unmerged (Verification step 6). `[unverified: #1115's merge state at the capture run]`
29. `read-cost` prints each agent type's Read share against the corpus's total billed weight, and states its unit at :515-527. `[verified: read_cost.py:500-502, :529]`
30. GH-1529 has A2 add to `read_scope.py`: "A1 (#1128) extracted `read-scope` into `claude/.claude/scripts/transcript_analysis/read_scope.py`. A2 adds to it:". `[verified: gh issue view output for GH-1529, read by the main session on 2026-11-20]` The plan adds a new module instead and leaves `read_scope.py` untouched (M1). `[engineer-verified: "New reviewer_reads module (Recommended)"]`
31. The work ships as two PRs, the instrument first and the capture page second. `[engineer-verified: "Two PRs (Recommended)"]`
32. The PR split's details come from the session's description of the consult's recommendation, not the engineer's words. PR 1 is the instrument. It cites GH-1529 with no closing keyword. Its verification gains a local dry run of the capture command and self-checks. That run's output stays out of the PR body. PR 2 is the capture page and index line, closes GH-1529, and runs the merged command from each clone's updated checkout. `[unverified]` This revision runs once, from the PR 2 worktree, instead (row 75), so no other checkout is updated.
33. The plan proceeds at its projected size instead of splitting further. `[engineer-verified: "Proceed anyway"]` The question it answered gave a projection of about 2,200 lines. Rows 48 and 50 record the later projections.
34. The report keeps the diff-handoff kind, the per-reviewer-type rows and coverage, `[engineer-verified: "Diff-handoff kind, Per-reviewer-type rows, Coverage + bench count"]` in the consult's reduced forms, which cut the bench-compatible paged-follow-up count. `[engineer-verified: "Apply reduced forms (Recommended)"]`
35. The reduced forms' content comes from the session's description of the consult, not the engineer's words:
    - the headline and the outcome-by-bucket table over `other` files only;
    - diff-handoff as one row of outcome counts, `followed_up` and `covered`, plus its part of the over-1,000-line Read share as one figure;
    - per-type rows as counts only, with rates pooled and the withheld-label fold kept;
    - `covered` kept, and `paged_followup_calls` with its failed subset cut.
    - `[unverified]`
    - This revision renames `followed_up` to `later_offset_read`, narrows `covered` to `covered_after`, and adds `neither` (M6).
36. The baseline records a before-value for #1115's late-findings watch. `[engineer-verified: "yes, add it to this plan"]` Superseded by row 51, the engineer's later answer.
37. #1115's acceptance holds the watch: "After merge: A-field watches late findings (issues raised in a later review round on code an earlier round had in scope) over a window. A rise reopens this issue." #1113's body does not mention it. `[verified: gh issue view output for #1115 and #1113, read by the main session on 2026-11-20]`
38. `review-ledger.sh append` sweeps ledger files idle longer than a 30-day floor, by mtime. `[verified: review-ledger.sh:294-325, :695-696; author_outcome.py:127-132]`
39. From schema 6 every ledger row stores `reviewed_head` and `reviewed_tree`, best-effort, and `append` pins each non-empty tree under the local ref `refs/review-ledger/<YYYY-MM>/<tree id>`. `docs/scripts.md`:246-277 documents placing a later round's rows inside or outside the delta between two rounds' trees. `[verified: review-ledger.sh:546-557, :583-602; _review-ledger-lib.sh:577-585; docs/scripts.md:193-277]`
40. The cost-levers register announces schema-6 state in a follow-up dated 2026-11-17. `[verified: docs/cost-levers-considered.md:758]`
41. Retired with the late-findings count (row 51).
42. Ledger files are named `<repo hash>.<slot>.jsonl`, where the slot is a branch hash or, in a session file, the session id its rows carry. `author_outcome` already lists, reads and attributes them through `_list_ledger_files`, `_read_ledger_rows_from_file`, `_ledger_file_session_component` and `_row_session_id`. `[verified: author_outcome.py:262-336]`
43. Retired with the late-findings count (row 51).
44. Retired with the late-findings count (row 51).
45. Retired with the late-findings count (row 51).
46. Retired with the late-findings count (row 51).
47. `CLAUDE.md` says "a plan committed under `.claude/plans/` ships in the same PR as the implementation", and `require-plan-review.sh` gates edits only while an uncommitted or modified plan file exists. `[verified: CLAUDE.md:93; README.md:184]` That no other gate requires a plan on PR 2's branch is unchecked. `[unverified]`
48. PR 1 proceeds at its projection of about 2,600 lines, asked as "PR 1 at about 2,600 lines: proceed, or split?". `[engineer-verified: "proceed"]` Rows 50 and 89 record the later projections.
49. The `Ask:` line's quoted wording for the new-module choice stands as written. `[engineer-verified: "Accept that wording (Recommended)"]`
50. PR 1 proceeds at its projection of about 3,600 lines (Critical files), asked as "projects PR 1 at about 3,600 changed lines … up from the about 2,600 you approved. … Proceed at that size, or split?". `[engineer-verified: "Proceed anyway (Recommended)"]` The option's description, one PR built in three dispatches that each finish green, is the session's, not the engineer's words. `[unverified]` The projection is above the about 2,600 lines row 48 answered. The late-findings count's removal lowered it. The round-1 test design, the ledger-file scope and the report's new diagnostics raised it by more. Row 89 records the later projection.
51. Late findings, the before-value row 36 added, move to their own issue under #1113. `[engineer-verified: "Move to its own issue (Recommended)"]`
52. That option's content comes from the session's description, not the engineer's words. `[unverified]`
    - This plan returns to the read baseline and the ledger dispositions.
    - #1115 then needs its own gate on a late-findings before-value.
    - The session drafts any issue text or comment for the engineer's approval and posts nothing without it.
53. `review-ledger.sh` names a ledger file `<repo hash>.<slot>.jsonl`. The repo hash is the sha256 of the `git rev-parse --show-toplevel` string printed where the append ran. `[verified: review-ledger.sh:233-248; claude/.claude/hooks/_lib.sh:654-658, :1216-1222, :5793-5800, :5822-5839]`
    - A hooks test already re-derives that formula in Python. `[verified: claude/.claude/hooks/tests/conftest.py:124]`
    - The hash binds path identity, not repository identity. `[verified: claude/.claude/hooks/_lib.sh:644-649]`
    - `--this-repo` scopes transcripts by path identity too, slugging each `git worktree list` path. `[verified: scope.py:85-93, :142-153, :203]`
    - That `git worktree list --porcelain` prints each worktree path as the same string `--show-toplevel` prints there is `[unverified]`, so M15 also hashes the resolved path. Dispatch 1a's real-repository test checks it on the test platform.
54. `render._pct_of` prints `0.0%` for a zero denominator. `[verified: render.py:84-92]` Reviewer-yield prints `insufficient` below an Active floor of 10, and `cost_ledger` reuses that label and floor. `[verified: reviewer_yield.py:46-49, :751-752; cost_ledger.py:323-347]`
55. `test_architecture_doc_documents_every_package_module` fails while a package module has no `### <module>.py` heading in `docs/transcript-analysis-architecture.md`. `[verified: tests/test_transcript_analysis_architecture_doc.py:35-49]` `test_transcript_package_module_prefixes.py` lists package modules and the test files that import them. `[verified: tests/test_transcript_package_module_prefixes.py:27-145]`
56. `docs/transcript-analysis.md` names `read-cost` in three enumerations. `[verified: docs/transcript-analysis.md:34-36, :78-86, :90-94]`
    - Commands that record an unresolvable project directory as a scan gap (:34-36).
    - Active-account-only scans (:78-86).
    - Scope headers that print no root count (:90-94).
57. `_is_reviewer_subagent_type` matches `skill-fidelity-reviewer`. `[verified: reviewer_yield.py:21-24]` Its body carries no read-every-changed-file instruction, while several reviewer bodies do. `[verified: Grep of claude/.claude/agents/*.md; ciso-reviewer.md:51, comment-discipline-reviewer.md:229, staff-backend-engineer.md:63, staff-platform-engineer.md:63, staff-sdet.md:57]`
58. A subagent's `.meta.json` holds `agentType`, `description`, `toolUseId` and `spawnDepth`, and names no dispatching skill. `[verified: tests/conftest.py:818-837, whose docstring says it matches the on-disk shape]`
59. #1115's live body sets the rules M17's population and the page's comparability record and limitations lean on. `[unverified: staff-product-engineer's round-2 and round-3 quotes of #1115's live body, not read by this plan's author]`
    - Its entry read is a default Read: "If one default Read call returns the whole changed file (no `PARTIAL view` notice), read the whole file. Otherwise, read the file's outline ... and the diff with function context."
    - Where git cannot identify the enclosing function, it says to "locate the enclosing function with Grep and read that range."
    - It says line counts supplied beforehand "belong" with #1103's orchestrator-written inputs.
    - It adds "mandatory expansions": consumer call sites, callers, callees and sibling arms.
    - It keeps `ciso-reviewer`'s CI and policy config files "whole at any size", and `staff-data-engineer`'s migrations "whole and in order (unchanged)".
    - It puts "markdown instruction files" out of scope, and `comment-discipline-reviewer` keeps "Markdown docs ... read whole". Its entry rule has no markdown carve-out for the other reviewers, so `other_prose` falls inside #1115 for them.
    - It leaves `skill-fidelity-reviewer` out of scope.
    - This replaces the round-1 summary, which held only in this qualified form.
60. `_scan_window` marks a tool id seen only for a kept successful result, and a test pins that a failed Read leaves its id unseen. `[verified: read_cost.py:217-231; tests/test_transcript_read_cost_scan_window.py:403-406]`
61. The review bench's own fixture models a denied call's `toolUseResult` as an `Error:` string, not a dict. `[verified: evals/test_replay_bench_checks_support.py:167-180]` Whether a failed Read's record has that shape is `[unverified]`, so the scanner treats any non-dict `toolUseResult` as missing.
62. `author_outcome._read_ledger_rows_from_file` prints the ledger file's path to stderr on any open failure. `[verified: author_outcome.py:287-292]` `routing_guard` captures a reader's stderr in a buffer and prints one fixed notice instead. `[verified: routing_guard.py:570-577]`
63. `config_dir()` takes the account from `CLAUDE_CONFIG_DIR` when it is set, else `~/.claude`. `[verified: _config_dir.py:22-41]` Read-cost's refusal checks how many roots resolved, not which root. `[verified: read_cost.py:396-410]`
64. `worktree-ensure.sh` fetches and starts a new branch's worktree from the default tip. `[verified: claude-skills/skills/branch-management/SKILL.md:56-59]` The git-writes gate allows a git write only from a linked worktree of the session's repository. `[verified: claude/.claude/hooks/require-worktree-for-git-writes.sh:33-41]`
65. `cleanup-merged-branches` and `cleanup-idle-open-pr-worktrees` remove worktrees, and the latter has a `--dry-run` form. `[verified: docs/scripts.md:379-404]`
66. `deny-private-project-refs` scans a commit's staged added lines and message, and a `gh pr create` or `gh pr edit` command's text and body file. Its long-hex detector fires on 32 or more hex digits or a UUID shape, and its home-path detector on a path rooted at a home directory. `[verified: docs/private-project-redaction.md:18-29, :72-73]`
67. A closing keyword in a commit message that reaches the default branch also closes the issue. `[unverified: staff-platform-engineer's recollection of GitHub's behavior, not re-fetched]` Verification step 6 checks commit messages either way.
68. A line-limit check ships only after F1's offender assessment, and its exception ceilings are exact in both directions. `[verified: docs/design-decisions/code-file-line-limit.md:36-57]` F1's assessment sits on the default branch after this base and lists `scope.py` and `author_outcome.py` as split-pending. `[unverified: staff-backend-engineer's round-1 report of commit 791b5609, not read]`
69. A figure from a refusing this-repository command takes only the check against the grandfathered set, and an uncited in-session answer settles it. `[verified: docs/private-project-redaction.md:105-108, :316-326]` The whole-report authorization form governs owner-authorized wider-corpus figures. `[verified: docs/private-project-redaction.md:199-244]`
70. Transcript records carry the harness version in a top-level `version` key. `[unverified]` The bench's fixture models one. `[verified: evals/test_replay_bench_checks_support.py:179]` A window whose records carry none prints as `unknown`.
71. The repository's docs name the ledger's stale-file sweep but not its period. `[verified: docs/scripts.md:215]` Row 38 reads a 30-day idle floor from the code.
72. `read_cost._file_kind` classifies a path as `instruction` (under `/skills/`, `/agents/` or `/rules/`, or a `CLAUDE.md`), `other_prose` (`.md`, `.mdx` or `.txt`), or `code/other`. `[verified: read_cost.py:52-56, :150-154]` The `instruction` test checks no extension, so a `.py` or `.json` file under `/skills/` is `instruction`. This repository's `claude-skills/skills/` holds both kinds, such as `review-pr/audit-execution-surface.py` and the skills' `evals/trigger-cases.json` files. `[verified: read_cost.py:148-154; Glob of claude-skills/skills/]`
73. `scope._list_dir_recording_gaps` lists with `iterdir` and records an unreadable directory as a gap. `author_outcome._list_ledger_files` uses `glob`, which returns nothing for an unreadable directory. `[verified: scope.py:308-322; author_outcome.py:302-307]`
74. `review-ledger.sh render` builds the PR-body block from the resolved ledger file's live decisions only. `[verified: docs/scripts.md:282]`
75. The capture runs from this clone only. `[engineer-verified: "One clone only (Recommended)"]` This answers the round-2 findings whose only surface was the second clone's run: a `cd` that might not persist into the next call, the other checkout's repository identity and account, and the hand-summed combined report.
76. That option's content comes from the session's description, not the engineer's words: capture from this clone alone, and state on the page that the other clone's sessions are not included. The description says this removes the cross-directory run, the identity and account checks and the hand-summing, at the cost of a smaller sample. `[unverified]` The page's limitation in Capture step 9 rests on it.
77. Pricing prints an API request id to stderr in two notices: the usage-drift warning, and the non-contiguous-run notice `dedup_turns_by_request_id` emits. `[verified: pricing.py:416-431, :463-484]` The output scan's shapes are not built for a request id, so the scan does not cover them.
78. `append` checks a `--ref` before it writes the row, and a `--ref` resolves within one ledger file (row 12). A superseder therefore always follows the row it names in file order. `event_time` is stamped at one-second resolution. `[verified: review-ledger.sh:521-524, :546]`
79. The ledger's own shape check accepts only the writer's `YYYY-MM-DDTHH:MM:SSZ` form of `event_time`, and its `is_decision` is a non-carry DEFER or SETTLED row with a non-empty id. `[verified: _review-ledger-lib.sh:653-666]` The writer always emits `ref`, `decided_by`, `reviewers` and `session_id`, empty when unset, and appends an `id` last. `[verified: review-ledger.sh:583-609]`
80. `/code-review` appends a CLEAN ledger row for a clean round and for a marker short-circuit. `[verified: claude-skills/skills/code-review/SKILL.md:27, :458]` Its other rounds log their findings' dispositions. `[unverified]`
81. The scope header's `this repo (N project dirs)` counts the slugs `git worktree list` yielded, not the directories that held sessions, so it is never zero. `[verified: scope.py:607-610]`
82. `pricing._model_rates` looks a model up with `dict.get`, which raises `TypeError` for an unhashable value such as a list or a dict. `[verified: pricing.py:225-233]` The command no longer calls `_model_rates`. It tests that the model is a string before its membership test on `_MODEL_BASE_INPUT_RATES`, and a list or a dict model prints as `other`. `[verified: reviewer_reads.py:326-336; tests/test_transcript_reviewer_reads.py:795-796]`
83. `test_case_study_pooled_figure_markers_are_registered_or_new` fails when a case-study page holds `pooled across`, `machine-wide`, `cross-machine` or `multi-account` and is neither on Remediation's list nor allowlisted, and its allowlist is empty. `[verified: claude-skills/skills/tests/test_doc_cross_references.py:507-550]` `_PER_ACCOUNT_STATE_PATH_RE` matches home-rooted per-account state paths, `<name>-markers/` directories included. `[verified: claude-skills/skills/tests/test_per_account_path_contracts.py:55-64]` That every `docs/**/*.md` file outside `reports/` and `case-studies/` is scanned with it is `[unverified: staff-platform-engineer's round-2 read of :154-162]`.
84. Path identity, which both halves of the scope rest on, does not exclude these cases: `[verified: claude/.claude/hooks/_lib.sh:644-649; docs/transcript-analysis.md:59; scope.py:104-106]`
    - a live worktree path of this checkout that another repository's checkout occupied earlier, whose sessions and ledger files then match as this repository's;
    - ledger rows appended from this checkout about work elsewhere;
    - a checkout of any repository whose path maps to the same project-directory slug as one of this checkout's worktrees;
    - a subagent file under an in-scope session, whatever repository the subagent worked in.
85. `docs/worktree-bash-guard.md` records that the guard's refusals do not reproduce on demand and may depend on more than command text. `[verified: docs/worktree-bash-guard.md:122-136]` Whether it refuses a literal `CLAUDE_CONFIG_DIR=` prefix, or a redirect to a path outside the worktree, is `[unverified]`.
86. `read-cost` registers only the scope arguments, so it has no date filter, and two runs over a live corpus differ by every session written between them. `[verified: read_cost.py:616-626]`
87. `_ReadEvent` has six fields on this base: `path`, `whole_file`, `tokens`, `lines`, `remaining_turns` and `edited_later`. `[verified: read_cost.py:59-67]`
88. The harness can write a Read call's `tool_use` block twice in one transcript, and a failed call's error result twice. `[verified: staff-backend-engineer's round-2 bounded read-only scan of transcript records, shape evidence only]` Read-cost today pends a failed call again on its replayed block, because only a successful result marks an id seen. `[verified: read_cost.py:217-231]`
89. PR 1 proceeds at its projection of about 4,250 lines (Critical files), asked as "PR 1 now projects about 4,250 changed lines (an estimate; you approved about 3,600) … Proceed at that size, split, or cut the review-ledger ADDRESS/DEFER counts …?". `[engineer-verified: "Proceed anyway"]` The option's description, everything in one PR at about 4,250 lines built in three dispatches that each finish green, is the session's, not the engineer's words. `[unverified]` Cutting row 1's ledger counts was a separate option the engineer did not choose, so row 1 stands. The round-2 test cases account for most of the rise above about 3,600.
90. The Read tool sets `truncatedByTokenCap` and the line fields as follows. `[verified: an architect consult's local read of the installed Read implementation in Claude Code 2.1.318 and 2.1.330]`
    - A flagged result comes only from a call with no `limit` and an `offset` absent or at most 1, so it starts at line 1.
    - When the harness cuts by lines, `numLines` is the delivered count and stays below `totalLines`.
    - When it cuts by characters, because a line is too long to fit, `numLines` counts the lines the delivered text touches. The last reported line then arrived in part, and the range can reach `totalLines`.
    - A paged call over the cap fails, so it adds no interval.
    - A flagged range that ends short of `totalLines` can therefore end on a line that arrived in part, and the instrument cannot tell that case from a cut by lines.
    - Whether older harness versions behave the same, and what the third parameter of the auto-pagination condition does, is `[unverified]`.
91. `review-ledger.sh` refuses a ledger or lock path that is a symlink, dangling or not, or anything but a regular file, before it appends or reads rows. Its own comment states the check's two limits: "a point-in-time test, not an atomic no-follow open, and it does not detect a hard link, which is a regular file". `[verified: _review-ledger-lib.sh:612-625, :638; review-ledger.sh:604]`
92. `pricing._model_rates` returns `None` for a model in `_LONG_PROMPT_TIERS`, though that model is also a key of `_MODEL_BASE_INPUT_RATES`. `claude-haiku-5-5` is such a model. `[verified: pricing.py:92-119, :135-138, :225-233]`
93. PR 1 measures about 6,160 changed lines on this branch: about 1,610 code, 4,300 tests and 245 docs, from `git diff main --numstat` excluding this plan and `agent-reviews/`. `[unverified: staff-backend-engineer's plan-review count, not re-run by this plan's author]`
    - That is above the about 4,250 lines row 89's "Proceed anyway" answered. Whether that answer holds at this size has not been asked. `[unverified]`
    - PR 1's body states the changed-line count measured when it opens (Delivery).

## Critical files

Each dispatch prompt states the directed growth of any file it edits that already has 1,000 lines or more (row 24): `scope.py` in 1a and 1c, and `tests/conftest.py` in 1a and 1b. The 1b prompt states `author_outcome.py`'s resulting count, 996.

**PR 1, Phase 1, dispatch 1a: shared machinery** (`code-writer`; read-cost's output must not change, with the one exception the `_agent_type_for` bullet below states).
- Create `claude/.claude/scripts/transcript_analysis/publication_scope.py`, about 90 lines:
  - read-cost's `_read_cost_roots`, `_refuse_wider_scope` and `_scope_header`, moved with the command label as a parameter. Read-cost's messages and header stay byte-identical.
  - `_ledger_repo_hash(path)`, the sha256 of the path string. Its docstring names `_marker_lib_repo_hash` as the formula's home (row 53).
  - `_this_repo_ledger_files(ledger_dir, worktree_paths, gaps)`: the entries directly under `ledger_dir` whose name's first slot equals the hash of a worktree path, as printed or as resolved.
    - It lists through `scope._list_dir_recording_gaps` (row 73), into the counter its caller passes.
    - It drops an entry only by name or by `is_dir()`. `is_dir()` follows links, so a directory and a symlink to a directory both drop here, and neither is counted anywhere. They are the one exception to a matching entry that is not a regular file counting as unreadable, and the docs section states it.
    - Any other entry with a matching name stays listed, a dangling symlink included.
    - Dispatch 1b's reader refuses a non-regular entry unopened.
    - It opens no file, and keeps no count of other files.
- Modify `claude/.claude/scripts/transcript_analysis/scope.py`, 1,161 to about 1,166 lines: extract `_repo_worktree_paths(command_label)` from `_repo_scoped_project_slugs` (:96-203), which then maps its result to slugs.
- Modify `claude/.claude/scripts/transcript_analysis/read_cost.py`, 626 to about 800 lines:
  - `_ReadEvent` gains defaulted fields `tool_use_id`, `offset`, `allow_large`, `start_line`, `num_lines`, `total_lines`, `truncated_by_token_cap`, `structured_status` and `call_order`.
  - A new `_FailedRead` (`path`, `tool_use_id`, `whole_file`, `offset`, `limit_refusal`, `call_order`) lands in a new `_WindowScan.failed_reads`, defaulting to an empty tuple.
    - `limit_refusal` is `recognised`, `unrecognised` or `none`, under Approach's rules for `refused_over_limit` and `unrecognised_limit_error`. The two patterns are module constants.
    - It is read from the result's `content`, as a string or as its text blocks joined. The text itself is not kept.
  - A new `_WindowScan.truncation_notice_tool_use_ids` holds the `attachment.toolUseID` of each `attachment` record whose `attachment.type` is `read_truncation_notice`. It is collected before the conversation-record filter at :187, which `attachment` records do not pass.
  - `_scan_window` takes an optional `seen_failed_tool_use_ids` set (M18). A failed call's id enters it at the first failure, so a replay in the same window or a later one is skipped, and never counts in `repeated_reads`.
  - `call_order` is the record-order position of the first `tool_use` block carrying a Read's id (row 88). A replayed block takes no new number. The pending entry's other fields keep read-cost's existing handling, so read-cost's figures do not change.
  - Structured fields come from the result record's top-level `toolUseResult.file` when all three conditions hold:
    - the record holds exactly one `tool_result` block;
    - `toolUseResult` and its `file` are dicts, and `filePath` equals the call's `file_path`;
    - each line field is a non-negative int that is not a bool, and the flag, when present, is a bool. An absent flag reads as false (row 6).
  - Otherwise each field is `None`, and `structured_status` names the first failed condition from a closed set of module constants, `multi_result_record` first. Token counting and `events` are the same either way.
  - The unit caption (:514-527) moves into its own function, and `_skipped_input_line` takes the gap counter and the invalid-usage count.
  - `_count_window_diagnostics` (:271-275) keeps its ordering note and calls a new helper that updates the seen-id sets and returns the invalid-usage count. Both commands call that helper after `_new_billed_weight`.
  - It calls the moved helpers with `"read-cost"`.
  - A new `_read_call(block)` returns a Read `tool_use` block's id, path, input and whole-file flag, or `None` unless the block is a Read with a non-empty path and a non-empty id. It is the one Read predicate: `_scan_window` pairs calls through it, and reviewer-reads' main-thread round join applies it too (dispatch 1c).
  - `_agent_type_for` also catches `RecursionError`, so a `.meta.json` nested past the JSON decoder's stack counts a `_GAP_SUBAGENT_META` gap and reads as an unknown agent type. A run over such a sidecar used to crash and now completes. That is the only change to read-cost's output. No run that completed before changes output.
- Modify `claude/.claude/scripts/tests/conftest.py`, 1,973 to about 1,995 lines, for builders the read-cost and reviewer-reads families share:
  - `_read_result` takes an optional `tool_use_result` placed at the record's top level;
  - a new `_read_truncation_notice(tool_id)` builds the attachment record;
  - `_read_use` takes an optional `allow_large`, absent by default.
- Modify `claude/.claude/scripts/tests/test_transcript_read_cost_command.py`, 93 to about 125 lines. First add tests asserting the exact full stderr of the three refusals, run against the unmodified module. Then move the two root-helper tests (:82-93) out.
- Modify `claude/.claude/scripts/tests/test_transcript_read_cost_report.py`, 513 to about 600 lines, with every new test written first and run against the unmodified module:
  - the exact `skipped input:` line and the full unit caption;
  - one `read-cost` run over a seeded corpus holding structured results, a truncation notice, a failed Read and a replayed `tool_use` block. Its full stdout equals the run over the same corpus stripped of `toolUseResult` keys and `attachment` records.
- Modify `claude/.claude/scripts/tests/test_transcript_read_cost_scan_window.py`, 406 to about 830 lines:
  - each new field from a whole-file record and from a paged record, and an absent flag reading as false;
  - one parametrized case over malformed shapes:
    - `toolUseResult` as a string, a list and `None`;
    - `file` not a dict;
    - `filePath` not a string;
    - a line field as `True`, negative, a float and a numeric string;
    - the flag as `"true"` and as `1`.
    - Each shape leaves its fields `None` and raises nothing, and its `structured_status` is asserted per shape.
    - The six existing `_ReadEvent` fields (row 87) and `repeated_reads` equal those from the same record without `toolUseResult`.
  - a mismatched `filePath`, a record holding two results (`multi_result_record`), and a malformed `toolUseResult` beside a success text, with token counting unchanged;
  - failed calls, one parametrized case on `limit_refusal`:
    - both wordings in row 7, each on a whole-file and on a paged call, are `recognised`;
    - a `File content (` text with another wording is `unrecognised`;
    - `exceed`, `maximum` and `too large`, each in lower and in upper case with no `File content (`, are `unrecognised`;
    - the recognised phrase in upper case is `unrecognised`, because it matches case-sensitively;
    - one refusal as a string, as a list of text blocks, and as a text block beside a non-text block is `recognised` in each form, and a list holding only a non-text block is `none`;
    - a missing-file error is `none`;
    - a call with `limit` and no `offset`, and a string `toolUseResult` (row 61), are each kept with their class;
    - every case asserts that no `_FailedRead` field holds any part of its error text;
  - a failed call replayed inside one window, as its `tool_use` block, its error, the block again and the error again: one `failed_reads` entry;
  - a failed call replayed in two windows sharing one `seen_failed_tool_use_ids`: one entry, and `repeated_reads` unchanged;
  - `call_order`: a same-path Read between a call's two `tool_use` blocks orders after the call;
  - truncation-notice ids, one notice placed before any conversation record.
- Modify `claude/.claude/scripts/tests/_read_cost_helpers.py`: `_file_record`, the structured-result builder, moves here, so `test_transcript_read_cost_scan_window.py` and `_reviewer_reads_helpers.py` import one copy.
- Modify `claude/.claude/scripts/tests/test_transcript_read_cost_subagent_reading.py`: a `.meta.json` nested past the JSON decoder's stack reads as an unknown agent type and counts one `_GAP_SUBAGENT_META` gap.
- Create `claude/.claude/scripts/tests/test_transcript_publication_scope.py`, about 245 lines:
  - the two moved root-helper tests;
  - under a second label, the header, and the refusals without `--this-repo`, with `--projects` and with two roots. The reviewer-reads command test keeps only its own wiring case of these;
  - `_ledger_repo_hash` equals `_marker_lib_repo_hash`, sourced from `claude/.claude/hooks/_lib.sh` in bash as `claude/.claude/hooks/tests/test_marker_lib.py`:164 calls it, for an ASCII path, a path with a space and a non-ASCII path;
  - over a temporary repository with a linked worktree, the hash of the `git rev-parse --show-toplevel` string from each worktree is among the hashes `_this_repo_ledger_files` matches. The test removes `conftest._INHERITED_GIT_VARIABLES` from the environment and sets the working directory itself;
  - `_this_repo_ledger_files` keeps a branch file and a session file of each worktree, and a dangling symlink with a matching name. It drops a foreign-hash file, a removed worktree's file, a name with no dot, a non-`.jsonl` name and a directory;
  - with a symlinked worktree path in a stubbed path list: a file named for the printed path's hash is kept, a file named for the resolved path's hash is kept, and a file named for neither is dropped;
  - an absent ledger directory yields no files and no gap, and an unreadable one records a gap.
- Modify `claude/.claude/scripts/tests/test_transcript_scope.py`, 913 to about 930 lines: `_repo_worktree_paths` returns the porcelain paths in order and fails closed as `_repo_scoped_project_slugs` does.
- Modify `claude/.claude/scripts/tests/test_transcript_package_module_prefixes.py`: list the module and its test file.
- Modify `docs/transcript-analysis-architecture.md`: a `### publication_scope.py` entry, and the `### read_cost.py` entry (:359-365) updated for the moved helpers.
- Verification: steps 1 and 2.

**PR 1, Phase 1, dispatch 1b: ledger dispositions** (`code-writer`, after 1a is committed, because it imports `publication_scope`).
- Create `claude/.claude/scripts/transcript_analysis/ledger_dispositions.py`, about 225 lines: one entry point that takes the config root, the worktree paths, the window and the scanned session ids, and returns the counts under Approach's ledger section.
  - It takes no transcript gap counter, so an unreadable ledger directory cannot reach the skipped-input line.
  - It `lstat`s each file first, and counts it unreadable without opening it unless it is a regular file, as the writer refuses a symlinked or non-regular ledger path (row 91). A symlink named for this checkout therefore never contributes its target's rows.
  - The check has the writer's two limits: it does not detect a hard link, and it is not an atomic no-follow open (M15).
  - It reads each file through `author_outcome._read_ledger_rows_from_file` under `contextlib.redirect_stderr` into a buffer, and catches the two decode exceptions M20 names.
  - It reduces each row at once to the six fields M10 reads, then applies Approach's absence and type rules, the closed disposition vocabulary and file-order supersession.
  - Its docstring states the output invariant and the ledger fields it reads.
- Modify `claude/.claude/scripts/transcript_analysis/author_outcome.py`, 993 to 996 lines: DEFER, CLEAN and carry constants beside its ledger enum mirrors (:78-88). That comment also names `--decided-by`.
- Modify `claude/.claude/scripts/tests/conftest.py`, to about 2,040 lines:
  - `_ledger_row` takes optional `id`, `ref`, `decided_by` and `reviewers`, absent by default, so existing rows do not change.
  - A new `_write_this_repo_ledger_file(config_dir_root, worktree_path, slot, rows)` names the file with `publication_scope._ledger_repo_hash` through `_write_named_ledger_file`.
  - A new `_WINDOW_EDGE_TIMESTAMPS`, the one edge matrix 1b's and 1c's tests share. Each row is a triple: timestamp, ledger expectation, transcript expectation. The two expectations differ on an offset, because the ledger accepts only the writer's form (row 79) and transcripts go through `corpus._parse_ts`, which converts it (`corpus.py`:220-240).
    - `--since` at 00:00:00Z: in, in;
    - the last second of `--until`: in, in;
    - the next day's 00:00:00Z: out, out;
    - 00:30:00+02:00 on the day after `--until`, which is 22:30:00Z on `--until`: left out under `event_time`, in. Its wall clock read as UTC falls out, so conversion decides it;
    - an unparsable timestamp: left out under `event_time`, out as untimestamped.
- Create `claude/.claude/scripts/tests/test_transcript_ledger_dispositions.py`, about 890 lines:
  - a local builder in the writer's full shape, the default for every case: empty-string `ref` and `decided_by`, a `reviewers` list, a `session_id` and an `id` (row 79). Rows with absent keys appear only as the legacy cases below;
  - terminal rows: an ADDRESS, a DEFER and a SETTLED; `--relog` and `--ref` supersession; a chain across two sessions in one file; carries left out on both sides; a carry of a DEFER decided before the window;
  - supersession edges:
    - a self-`ref`;
    - a two-row `ref` cycle, where only the later row supersedes;
    - a superseder in the same second;
    - a superseder after the window;
    - the same `id` in two files;
    - CONSULT rows;
    - id-less disposition rows, counted apart, superseding nothing and never terminal;
  - one parametrized case per kept field with a wrong type (`disposition`, `id`, `ref`, `decided_by`, `event_time`, `session_id`), each left out under its printed reason;
  - legacy rows: no `ref` or `decided_by` key reads as empty, and no `id` makes the row id-less. A row with no `session_id` stays in the dispositions and out of the session lines, in a branch-keyed file as in a session file;
  - `event_time` over `_WINDOW_EDGE_TIMESTAMPS`, against each row's ledger expectation;
  - an unknown `disposition` string, counted as unknown and absent from every returned key and value;
  - a foreign-hash file holding an in-scope session's rows, excluded;
  - an absent and an unreadable ledger directory, each with its own state;
  - an unreadable file made by a dangling symlink with an in-scope name, so the case runs as root too: counted, with its path absent from both streams;
  - a symlink with an in-scope name pointing at a foreign-hash ledger file: none of its target's rows count and it counts as one unreadable file, while the regular file beside it is still read;
  - a named pipe with an in-scope name: one unreadable file, never opened.
    - The read runs in a worker thread joined with a deadline, so a regression that opens the pipe fails instead of hanging. The dev requirements carry no timeout plugin.
    - The case skips on a platform without `os.mkfifo`;
  - a symlink with an in-scope name pointing at a directory: dropped by the selector and not counted unreadable (dispatch 1a);
  - a line nested past the decoder's stack, and a line holding an integer over the digit limit, each in a file beside a valid row: that file counts as one unreadable file with none of its rows, and the exception text reaches neither stream (M20);
  - a `_leak_sentinel` value in `finding`, `rationale` and `engineer_quote`, which never reaches output;
  - sessions with a disposition row, and how many of those the scan covered;
  - one writer-to-reader test:
    - The real `review-ledger.sh append`, run in a temporary repository's linked worktree, writes a DEFER, re-logs it with `--relog`, and closes it with an ADDRESS by `--ref`.
    - The selector picks the file by worktree path, nothing is left out by field, and the ADDRESS is the one terminal row.
    - It builds the repository and worktree with `conftest._git` or `helpers.init_git_repo(env=...)`, and runs `append` under `conftest._clean_env(HOME=..., CLAUDE_CONFIG_DIR=None)`, so no inherited git variable redirects git (`conftest.py`:100-117). The rest of its environment follows `test_author_outcome.py`'s `TestReviewLedgerSubprocessIntegration` (:1191-1208).
    - `append` prints no row id, so the test reads each id back from the file.
    - The ADDRESS names the relog row's id, not the DEFER's. The relog retires the DEFER, and `_review_ledger_check_not_retired` refuses a retired `--ref` (`_review-ledger-lib.sh`:878, `review-ledger.sh`:637).
- Modify `claude/.claude/scripts/tests/test_transcript_package_module_prefixes.py`: list the module and its test file.
- Modify `docs/transcript-analysis-architecture.md`: a `### ledger_dispositions.py` entry. It claims no more for the regular-file check than M15 states.
- Verification: step 1.

**PR 1, Phase 1, dispatch 1c: the subcommand** (`code-writer`, after 1b is committed, since it consumes both earlier dispatches. It edits `scope.py`, the prefix test and the architecture doc again, in sequence).
- Create `claude/.claude/scripts/transcript_analysis/reviewer_reads.py`, about 975 lines: `cmd_reviewer_reads`, `_add_reviewer_reads_subparser`, and the accumulation and report under Approach. The module docstring states the output invariant and its request-id exception (row 77).
  - It calls `scope._repo_worktree_paths` once, seeds `args._this_repo_slugs` from the result, and passes the same paths to `ledger_dispositions` (M15).
  - It builds the reviewer-yield iterator with `scope._resolve_project_scope(..., include_subagents=True)` over the one root `publication_scope` returns, never through `scope.resolve_scan_roots`.
  - The outcome classes, their precedence and the `size_unknown` reasons it adds are module constants.
  - Its own fold sums each untracked agent type's integer counts into the withheld row, for the per-type rows and the yield rows alike. `read_cost._fold_untracked_agent_types` builds and merges read-cost's `_AgentTypeRow` (`read_cost.py`:373-385), so it cannot take these rows.
- Modify `claude/.claude/scripts/transcript_analysis/cli.py`, 205 to about 209 lines: import and register the subparser beside read-cost's (:59-62, :136-137).
- Modify `claude/.claude/scripts/transcript_analysis/scope.py`: add `reviewer-reads` to `_SUBCOMMANDS_REFUSING_TOP_LEVEL_CONFIG_DIR` (:702), and to its comment's list of commands that build their own single root.
- Create `claude/.claude/scripts/tests/_reviewer_reads_helpers.py`, about 170 lines, for the three reviewer-reads test files:
  - a reviewer window, written through `conftest._write_subagent_dispatch`, with a `spawn_depth` for a nested dispatch;
  - a reviewer-window turn carrying a timestamp, a `version` and `usage`, which `_read_cost_helpers._turn` does not carry;
  - a Read exchange carrying a structured result, with `allow_large` through `conftest._read_use`, and a failed Read exchange;
  - a main-thread round window;
  - an args builder that stubs `scope._repo_worktree_paths` with a call counter.
- Create `claude/.claude/scripts/tests/test_transcript_reviewer_reads.py`, 998 lines, for accumulation:
  - each outcome class, at the bucket edges 0, 1,000, 1,001, 2,000, 2,001 and unknown;
  - one parametrized precedence table over every adjacent pair in Approach's numbered list that can overlap, each row with its expected class or reason written in the table:
    - the cap flag with `numLines` equal to `totalLines`, with `allow_large`, with `startLine` above 1, and with `numLines` above `totalLines`: `partial_token_cap`;
    - a record whose raw cap flag is true but which fails a check: `size_unknown` under that check;
    - `startLine` above 1 alone, with `numLines` above `totalLines`, and with `numLines` equal to `totalLines` and `allow_large`: `start_after_first_line`;
    - `numLines` above `totalLines` alone and with `allow_large`: `lines_exceed_total`;
    - `allow_large` with `numLines` below `totalLines`: `partial_unflagged`;
    - an empty file at `startLine` 0 and at 1: `complete`;
    - a recognised refusal, whose text also holds the unrecognised triggers: `refused_over_limit`;
    - an unrecognised refusal: `other_error`, counted under `unrecognised_limit_error`;
  - the larger-than-one-call denominator: which classes enter, and which stay out (`complete` within both limits, `other_error`, `size_unknown`, diff handoffs), with the prose and `code/other` split. A plain `complete` call at 25,000 estimated tokens stays out, and `complete_allow_large` calls at 24,999 and 25,000 fall on either side;
  - the band count at 19,999, 20,000, 29,999 and 30,000 estimated tokens, counting `complete_allow_large` calls only. One estimate inside the band counts at 2,000 lines and not at 2,001;
  - targeted refusals: a refused paged call with the token wording and a refused `limit`-only call, each after a partial whole-file call of the same path.
    - Neither takes an outcome class, enters the headline's numerator or denominator, or joins the follow-up population.
    - The paged one makes the partial call `later_offset_read`. The `limit`-only one moves no reviewer-window count;
  - the largest-`totalLines` fallback within one window, including a failed call bucketed from a later paged Read;
  - diff handoffs by exact parent directory name, with a nested and a prefixed lookalike counted as reviewed files;
  - `later_offset_read` with an `offset` of 0, a Read before the partial call, a later offset Read of another path, and one in another window;
  - `covered_after`:
    - overlapping and gapped ranges;
    - a Read before the call, and another window's Reads;
    - a later Read whose structured fields are `None`;
    - a call of unknown size;
    - a `totalLines` of 10**12, which returns at once;
    - a call that is `neither`;
    - flagged ranges, through the printed follow-up line, in `test_transcript_reviewer_reads_command.py`'s `test_a_token_cap_flagged_call_reaching_the_last_line_adds_no_coverage_to_the_printed_follow_up`:
      - A flagged call whose range reaches the file's last line is not covered by itself and counts as `neither`.
      - A flagged call that ends short of the last line is covered by a later paged Read;
  - a nested reviewer dispatch, counted in the read figures and not in the yield figures (row 18);
  - the Read share: `skill-fidelity-reviewer` and non-reviewer windows outside both sides, billed weight deduplicated by message id, and the parts reconciling to the Read weight;
  - per-type rows and the withheld fold, with an untracked `staff-` name;
  - main-thread round Reads:
    - a Read split across duplicate records at a window start and at its end;
    - Reads at `window.start` and `window.end - 1`;
    - adjacent windows of two skills;
    - a Read in no window;
    - a window opening before `--since`;
  - window edges over `_WINDOW_EDGE_TIMESTAMPS`, against each row's transcript expectation, for reviewer windows and round windows. A reviewer window with no timestamped record, and a round window whose opening record's timestamp is absent or unparsable, each count in their own diagnostic;
  - comparability, parametrized:
    - hostile values for the version and the model: an int, a list, a dict, `None`, `"1.2.3\n"`, a non-ASCII digit, a path, 32 hex digits, an overlong string, and a valid value;
    - the version's bounds: `"1"`, `"1.2.3.4.5"`, `"12345.1"`, `"1.12345"` and a 33-digit string with one dot print as `other`, and `"1.2"`, `"1234.1234.1234.1234"` and `"2.1.0"` print as themselves;
    - each value prints as `other`, `unknown` or its valid form, raises nothing, and appears nowhere else in the output;
    - every key of pricing's `_MODEL_BASE_INPUT_RATES` prints by name, `claude-haiku-5-5` included (row 92);
  - each diagnostic made nonzero by a seeded mismatch: an unexplained partial, a `partial_token_cap` with no notice, each `size_unknown` reason, an `unrecognised_limit_error`, and a `skill-fidelity-reviewer` window left out;
  - notice agreement, parametrized over the call a notice names, with all three counts asserted:
    - a `partial_token_cap` call agrees and moves no count;
    - a `size_unknown` call under `multi_result_record` moves only the third count;
    - a `partial_unflagged` call, a `complete` call and no call each move the second count.
- Create `claude/.claude/scripts/tests/test_transcript_reviewer_reads_report.py`, about 610 lines:
  - one hand-computed fixture in the style of `TestPrintedFigures` (`test_transcript_read_cost_report.py`:314), with each printed figure asserted against its own expected value. It holds every outcome class, ADDRESS, DEFER and SETTLED terminal rows with their shares, per-type rows, the yield section and the left-out count;
  - `no data (0/0)` and `insufficient (n/d)` for each rate, at zero, below the floor and at it;
  - the yield section's wiring: `compute_reviewer_yield_data` receives the window's `since_ts` and the next day's 00:00:00Z as `until_ts`, untracked names fold, the `--until` caveat line prints, and the second pass's gap counter prints on its own line and not in the skipped-input line;
  - the not-completed yield branch:
    - In this file: `test_a_yield_pass_that_could_not_complete_prints_one_fixed_notice_and_no_rows` and `test_a_sidecar_the_shared_yield_code_cannot_read_leaves_the_rest_of_the_report_intact`.
    - Through the command, in `test_transcript_reviewer_reads_command.py`'s `TestYieldPassOverHostileInput`: `test_a_decode_failure_in_the_yield_pass_prints_the_fixed_notice_and_leaves_the_rest_of_the_report` and `test_a_field_shape_the_shared_yield_code_cannot_take_ends_the_pass_with_a_fixed_notice`.
    - The case that stays completed, in the same class: `test_a_non_object_line_and_a_non_object_message_leave_the_yield_pass_complete`.
- Create `claude/.claude/scripts/tests/test_transcript_reviewer_reads_command.py`, about 685 lines:
  - the real registrar round-trip;
  - refusal without `--this-repo` under the command's own label, without either date, with `--since` after `--until`, and with an unpadded `--since` and an unpadded `--until` such as `2026-1-5`, each exiting 2 before any scan; `--since` equal to `--until` accepted. The rest of the refusal matrix lives in `test_transcript_publication_scope.py`;
  - the header;
  - with a declared second root, the transcript scan, the yield iterator and the ledger read each see only the first root;
  - a ledger directory holding an in-scope worktree's file and a foreign-hash file an in-scope session wrote. Through the command, the in-scope rows count, the foreign rows do not, and the stubbed `_repo_worktree_paths` ran once;
  - one run through `main()` over a seeded corpus with a `_leak_sentinel` value in each input channel:
    - The channels:
      - a Read path, and a diff-handoff directory name;
      - a `.meta.json` `agentType`, and a dispatch `subagent_type`;
      - a session id in a transcript name and in a ledger row;
      - a ledger `id`, `ref` and `finding`;
      - a project-directory slug;
      - a version, and a model;
      - an unreadable ledger file made by a dangling symlink;
      - a failed whole-file Read's error text, once as a string and once as text blocks, with the sentinel inside a path in the text. Its positive control is the `other_error` count.
    - The `agentType` and `subagent_type` sentinels each start `staff-`, so the reviewer predicate accepts them and the withheld fold must hide them.
    - Each channel has a positive control: the same run asserts that its sentinel-bearing record moved a printed count.
    - `_LEAK_SENTINEL_PREFIX` is absent from stdout and stderr;
  - a non-contiguous same-`requestId` run in the main-thread records, after resetting `pricing._non_contiguous_merge_notices_logged`: stdout holds no request id, and stderr holds it only in that notice (row 77);
  - one run of the script in a fresh interpreter: a refusal exits 2 with the command label. It sits here, not in `test_transcript_cli_bootstrap.py`, which already has 1,440 lines (row 24).
- Modify `claude/.claude/scripts/tests/test_transcript_cli.py`: add `reviewer-reads` to `_REFUSING_SUBCOMMANDS_WITHOUT_THEIR_OWN_CONFIG_DIR_FLAG` (:156-157).
- Modify `claude/.claude/scripts/tests/test_transcript_package_module_prefixes.py`: list the module and the three test files.
- Modify `docs/transcript-analysis.md`, 2,675 to about 2,875 lines:
  - a `## reviewer-reads` section covering flags and their date rule, scope, populations, outcome classes and their precedence, targeted calls, the prose bucket's path rule, the headline, rates and their markers, the unit, the ledger-file scope with its directory exception (dispatch 1a), path identity's non-exclusions (row 84), and publication;
  - among the section's Known limits, each as the plan states it:
    - the regular-file check's two limits, a hard link and a swap between the `lstat` and the open (M15);
    - a transcript line nested past the decoder's stack, or holding an integer over the digit limit, ends the run before the yield pass (Approach, Reviewer-yield);
    - the round counts' gap between whole-file calls and outcome plus diff-handoff counts (Approach, Main-thread round Reads);
    - the model label's dependence on pricing's table (M19);
  - `reviewer-reads` added to the three enumerations that name `read-cost` (row 56).
  - The section shows no sample output. Every config-directory path in it is written `<config-dir>/...`, never home-rooted (row 83).
- Modify `docs/transcript-analysis-architecture.md`: a `### reviewer_reads.py` entry.
- Modify `docs/private-project-redaction.md`: a `reviewer-reads --this-repo` bullet beside read-cost's (:142-147). It states that the ledger section opens only files keyed to this checkout's worktrees, and that both halves rest on path identity, not repository identity, with row 84's non-exclusions and the regular-file check's two limits (M15). Its paths take the `<config-dir>/...` form.
- Modify `CHANGELOG.md`: an `[Unreleased]` entry for the subcommand.
- Verification: step 1.

**PR 2, Phase 2: capture and page** (main session, not delegated, because it carries the composition-check result to the owner).
- Create `docs/case-studies/reviewer-read-field-baseline.md`, with the contents under Approach's Capture steps 7 to 9.
- Modify `docs/case-studies.md`: one index line, carrying no figure.
- Verification: steps 4 to 7.

**Reuse, not reimplement:**
- `read_cost`: `_scan_window`, `_read_call` (the one Read predicate `_scan_window` and the main-thread round join share), `_read_subagent_windows`, `_new_billed_weight`, `_read_weight`, `_SeenIds`, `_file_kind`, `_skipped_input_line`, and the extracted caption and diagnostics helpers.
- `pricing`: `_cache_read_equivalent_weights`, `dedup_turns_by_request_id`, `_warn_if_subagent_format_drift`, `_MODEL_BASE_INPUT_RATES`.
- `review_rounds`: `detect_round_windows`, `REVIEW_SKILLS`.
- `reviewer_yield`: `_is_reviewer_subagent_type`, `compute_reviewer_yield_data`, `_REVIEWER_YIELD_INSUFFICIENT`.
- `author_outcome`: `_read_ledger_rows_from_file`, `_SESSION_ID_PATTERN`, and its disposition constants.
- `redaction._repo_tracked_agent_type_names`, `subagent_mix._WITHHELD_AGENT_TYPE_LABEL`.
- `scope`: `_add_project_scope_args`, `_iso_date`, `_parse_absolute_window_args`, `_resolve_project_scope`, `_list_dir_recording_gaps`.
- `corpus._parse_ts`, and `render._pct_of` for a nonzero denominator.
- `routing_guard._classify_capture_opt_in`'s stderr-buffer pattern (row 62), as a pattern, not an import.
- Tests: `conftest._write_subagent_dispatch`, `_write_named_ledger_file`, `_read_use`, `_asst`, `_INHERITED_GIT_VARIABLES`, `_clean_env`, `_git`, `_read_cost_helpers._turn`, `_review_round_corpus_helpers._leak_sentinel` and `_LEAK_SENTINEL_PREFIX`, and `helpers.init_git_repo` and `init_git_repo_with_commit` (`claude/.claude/tests/helpers.py`:1477, :1490).

Projected diff: about 6,160 lines in PR 1 (about 1,610 code, 4,300 tests and 245 docs), as measured on the branch (row 93), and about 200 lines in PR 2. Row 89 records the engineer's decision at about 4,250 lines, and row 93 records that this figure exceeds it.

## Verification

1. After each Phase 1 dispatch, run `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py` and `scripts/venv-run.sh ruff check claude/.claude/scripts/`.
   - `select-tests.py` maps these paths to the whole scripts test directory (row 25) and selects the doc tests for the edited docs.
   - Each dispatch's file list carries what its own new module needs to pass that run, the architecture-doc and module-prefix tests included (row 55).
2. Dispatch 1a preserves read-cost's behavior:
   - Its new characterization tests, the seeded-corpus stdout comparison among them, pass against the unmodified `read_cost.py`, and again after the change.
   - Its diff changes no existing assertion in `test_transcript_read_cost_accumulation.py`, `test_transcript_read_cost_report.py`, `test_transcript_read_cost_subagent_reading.py`, or `test_transcript_cli.py`'s read-cost tests.
   - One named exception, dispatch 1a's `_agent_type_for` bullet. Its new case in `test_transcript_read_cost_subagent_reading.py` pins new behavior, not old, so it is not one of the characterization tests above.
   - No live run is compared. `read-cost` has no date filter (row 86), so two runs over a live corpus differ by every session written between them.
3. Before PR 1 opens:
   - Rebase onto the default branch. If a line-limit check has landed (row 68), ask the engineer before adding its exception file to this PR.
   - Dry-run Capture steps 3 to 5 from this worktree, with this worktree's script, then run the self-checks in step 4. The session records which command shapes the guard accepted (row 85).
   - A failure is an instrument fix inside PR 1, followed by a fresh dry run.
   - A later PR 1 commit that touches the five instrument modules gets a fresh dry run before the engineer merges, and the body's dry-run commit is updated.
   - The worktree-cleanup hold PR 1's body states starts at the first dry run. No dry run releases it; only Capture step 6 does.
   - Keep-out rule: no figure, record text, error text or path from any dry run reaches an artifact either PR produces.
     - That covers committed files of every kind, docstrings, test values and the CHANGELOG included, and `/pr-description` output.
     - It covers PR and issue comments, and ledger rows' finding and rationale text, which `review-ledger.sh render` copies into PR 1's body (row 74).
     - Test and doc values are synthetic, and the docs section shows no sample output.
     - PR 2's page is the only home for a figure, and only for the capture run's.
4. Self-checks, on every dry run and on the PR 2 run, before the page is written:
   - Reviewer-window floor: the reviewer-window count is above zero. The header's project-directory count gets no floor, because it counts worktrees listed and is never zero (row 81).
   - Ledger floor: when the report counts any `code-review` round window, it also counts at least one ledger file read. Every `/code-review` round appends a ledger row (row 80), so a zero there is a hash miss, not an empty ledger (M15).
   - Yield-completed floor: the report holds no line starting `reviewer-yield pass: not completed`. The command prints that notice in place of the yield rows, prints no count on it, and still exits 0, so a capture that prints it fails this check.
     - The pass ends on a record or sidecar field the shared code cannot take (Approach, Reviewer-yield), so a re-run over the same corpus prints the notice again.
     - A notice that reproduces on a re-run stops the capture, and the session asks the engineer, as the sample check does.
     - The engineer then decides between a fix to the shared code that cannot take the field and publishing the page with the missing yield section disclosed.
     - The worktree-cleanup hold stays on until that decision. A decision to publish counts as this check passing, as a go-ahead at a sample-check stop does (Capture step 6). A decision to fix keeps the hold until a re-run passes.
   - Sample check: when the pooled headline or the Read share prints `insufficient` or `no data`, the session tells the engineer. At PR 2 it also stops, and asks the engineer before the page claims a baseline or PR 2 closes GH-1529.
   - By-hand trace, at every dry run, and at PR 2 only when Capture step 2 found a diff:
     - Its reads stay inside the project directories named by this clone's `git worktree list` slugs, under the pinned account's `projects/` directory. No other file under the account directory is read.
     - It traces a nonzero unexplained-partial count, each of the first two notice-agreement counts when nonzero, the largest `size_unknown` reason, and a nonzero `unrecognised_limit_error` count.
     - It also groups `other_error` calls by their error text's opening words with digits replaced, and traces the largest group.
     - The largest `size_unknown` reason is expected to be `multi_result_record`, the harness's batching shape (row 6), not a defect.
     - The third notice-agreement count, notices naming a `size_unknown` call, is expected to be nonzero wherever batched records (`multi_result_record`) occur, not a defect.
     - A cause in the instrument is a PR 1 fix. At PR 2 it stops the capture. A cause in the harness stays in the session.
   - Nothing from the trace is published. The page describes each diagnostic it prints by that diagnostic's fixed definition only.
   - Output scan: no stdout or stderr file of any run holds a run of 32 or more hex digits, a UUID shape, or a path under a home directory or the config directory. These are the redaction gate's own thresholds (row 66). A request id on stderr is expected (row 77).
   - In PR 2, a failed floor or output scan stops the capture, and the session asks the engineer, because the fix is an instrument change outside PR 2's files.
5. In PR 2, check the page's figures per `docs/private-project-redaction.md` § "New figures against the grandfathered set", against every entry on that doc's § "Remediation" list (row 27).
   - For each entry, the session records the figure categories it compared, or why it ruled the entry out, such as no overlapping window.
   - The session states the result to the engineer in session whatever it finds.
   - If a figure could compose with an entry, the session asks the owner before committing the page.
   - PR 2's body names each entry with the categories compared or the reason it was ruled out.
   - The whole-report authorization form is not used, because it governs wider-corpus figures (row 69).
   - The page's commit, and each PR's body and title, pass `deny-private-project-refs` (row 66).
6. Artifact checks, before each commit and each `gh pr create` or `gh pr edit`, in either PR:
   - Pinned account: `grep -F` the page, the PR body file and the branch's commit messages for the pinned directory's full string, for its last two path components joined, and for its last component unless that is `.claude`. The session states the result to the engineer.
   - Closing keywords: `grep -Eio` over `git log origin/main..HEAD --format=%B`, the title and the body file, with the pattern `(^|[^[:alnum:]])(close[sd]?|fix(e[sd])?|resolve[sd]?)[[:space:]]*:?[[:space:]]*([[:alnum:]_.-]+/[[:alnum:]_.-]+)?(#|gh-)[0-9]+` (row 67).
     - PR 1 needs zero matches.
     - PR 2 needs exactly one, `Fixes #1529`.
     - The check runs again after any title or body edit.
   - In PR 2, confirm #1115 is unmerged at the capture run (row 28). The page states it.
   - In PR 2, the page and both PR bodies carry the late-findings issue's number. If no issue has been posted by then, the page says no issue has been opened.
7. In PR 2, before its push, run `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py`. Its rule for `docs/` paths (`select-tests.py`:1041) selects the doc tests, the marker-phrase and state-path tests among them (row 83).

## Out of scope

- A late-findings before-value for #1115's watch (row 37). The engineer moved it to its own issue under #1113 (row 51). As a result, #1115's "A rise reopens this issue" clause has no before-value until the new issue delivers one. The session drafts that issue's text before PR 1 opens (Delivery, row 52).
  - The round-1 plan review found these faults in the measure this plan carried:
    - Its definition counts code no earlier round had in scope, so its after-value can rise when #1115 works as designed.
    - Recorded trees exist on ledger rows only from schema 6 on (rows 39 and 40), so only rounds appended since then can be placed.
    - It needs ledger rows scoped to this repository. M15 now provides that scope, which the new issue can reuse.
    - It needs a git call hardened against the working directory, output decoding, and the reader's environment and diff config.
  - No repository doc states how long review ledgers are retained (row 71). How long pre-#1115 ledger rows stay readable for the new issue is unverified beyond the code's 30-day idle floor (row 38).
- Widening `--this-repo` to removed worktrees or other clones. Every publication instrument depends on that scope primitive. Widening it would widen `cost --this-repo --summary`. That call is one of the two `docs/private-project-redaction.md`:151-167 pre-clears. That section makes a diff widening it a P1 finding. Row 75's decision accepts the coverage gap instead, and the page states it.
- Fixing the bench's partial-Read detection (row 21). It belongs to #1114's `evals/review_bench/runner.py`. Raise it on #1114. This plan prints no bench-compatible count (M6), so no figure here waits on that fix.
- Sharing a structured-result parser with the bench. `runner.py` keeps its own pins (:101, :103) and imports nothing from `transcript_analysis`.
- Relocating `_is_reviewer_subagent_type`, for the reason row 22 records.
- Changing reviewer-yield's main-thread-only dispatch population or its since-only edit table (row 18). The page states both.
- Changing `author_outcome._read_ledger_rows_from_file`'s open-failure line. This command captures it (M20).
- Skipping a transcript line nested past the decoder's stack, or holding an integer over the interpreter's digit limit, in `corpus._parse_jsonl_records`. Such a line ends the run with a traceback for every command that parses transcripts through it (`corpus.py`:111-116), so skipping it would change those commands' output too. The docs section lists it as a known limit (Approach, Reviewer-yield).
- Changing or suppressing pricing's two request-id notices on stderr (row 77). Read-cost prints them the same way, stderr is read by the session and never published, and Approach names the exception. A 1c test seeds the non-contiguous-run notice and checks that stderr holds its request id only there.
- Carrying the dry run's figures to PR 2. PR 2 compares against no dry-run figure, so none needs a carrier. PR 1's body carries the hold, the dry-run commit and the re-dry-run rule, none of them a figure.
- Comparing the capture's worktree count against the dry run's. The page states the count the capture saw, and a smaller count describes a smaller sample correctly.
- A literal search for the dry run's figures through PR 1's diff, body and rendered ledger block. Its small counts match line numbers and test values throughout a diff of this size, so it cannot tell a leak from a coincidence. The keep-out rule removes the docs section's sample output, the likeliest channel, instead.
- A by-hand hash of each worktree path at the dry run. The ledger floor catches a miss on every path from two printed counts, and a unit case covers each half of the printed-or-resolved rule.
- Ending the window before this branch's first review. Those reviews ran under the pre-#1115 instruction like any other, so the page states them as a limitation instead.
- Per-type billed weight and Read weight, and the ledger's CLEAN count. No figure the report states reads them (M14), and GH-1529 asks for ADDRESS and DEFER rates only.
- Reading the merge dialog's squash message. The session cannot see it, and merge stays the engineer's step (`block-gh-pr-merge.sh`).
- A billed share for main-thread round Reads. GH-1529's token question asks about reviewer tokens only.
- Ticking #1113's checkbox, a human step after PR 2 merges (G4).
- Any edit to `read_scope.py`. The engineer chose a new module instead (row 30).
- Raising the 30-day ledger sweep floor (row 38). The in-scope sessions come from transcripts, which age out at the same 30-day default (G1), so a longer floor would widen no window. The floor is also shared hook-library state every stow consumer runs (`author_outcome.py`:127-129).
- Committed verbatim transcript records as test fixtures. A verbatim record carries the provenance `docs/private-project-redaction.md` governs. The report's diagnostics check the real record shapes on every run instead, which a frozen fixture would not.
- Splitting reviewer windows by the skill that dispatched them, for the reason M17 records.
