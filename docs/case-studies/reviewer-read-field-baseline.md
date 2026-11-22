# Reviewer whole-file reads: the A-field baseline

How often does a reviewer subagent's whole-file `Read` of a file larger than one Read call come back partial or refused, and what share of reviewer spend goes to Reads? This page records one run of `transcript-analysis.py reviewer-reads` as the before-state for #1115's change to the reviewer read instruction. It is the A-field baseline GH-1529 asks for: the before-value measured from real review transcripts, as opposed to the bench-measured baseline #1114 tracks. The design and the evidence behind each choice are in [`.claude/plans/reviewer-read-telemetry.md`](../../.claude/plans/reviewer-read-telemetry.md).

The figures come from transcripts and ledger files selected by this checkout's path identity, on one account (see Limitations for what that selection does not exclude). The command refuses any wider scope, which is what makes them publishable under `docs/private-project-redaction.md` § "Publishing a tooling measurement". It reads this clone's live worktrees only.

## Headline answers

- **Partial or refused:** 100.0% (65/65) of whole-file calls on reviewed files that were partial, refused, complete on a file over 2,000 lines, or flagged `allow_large` at an estimated 25,000 tokens or more. All 65 are `partial_token_cap`, none is refused, and all 65 are prose (`instruction` plus `other_prose`). Code and other files have no calls in that denominator.
- **Read share:** 12.7% of modeled billed weight in reviewer windows goes to Reads. Of the Read weight, 18.0% is files over 1,000 lines. Of the Read weight too, 7.0% is code and other reviewed files over 1,000 lines and 10.4% is diff handoffs over 1,000 lines, and these two do not sum to the 18.0%. This is a share of modeled billed weight, not of tokens or dollars.

## The run

- **Command:** `CLAUDE_CONFIG_DIR=<the account that holds this clone's sessions> python3 claude/.claude/scripts/transcript-analysis.py reviewer-reads --this-repo --since 2026-10-25 --until 2026-11-21`
- **Run at:** 2026-11-22T11:44:30Z.
- **Window:** 2026-10-25 to 2026-11-21, both days included, 28 days.
- **`cleanupPeriodDays`:** absent from the account's settings, so the 30-day default applies. At that default, records from about 2026-10-23 onward were still kept at the run, so the window's first day, 2026-10-25, falls inside the retained span.
- **Instrument commit:** `e5e1f34f573a`, the commit the capture's worktree was cut from. The module files the plan lists, plus the ledger reader in `author_outcome.py`, show no diff against the commit the instrument was last dry-run at.
- **Self-checks:** five checks passed before this page was written, as `.claude/plans/reviewer-read-telemetry.md` § "Verification" step 4 defines them.
  - Reviewer-window floor: the reviewer-window count is above zero.
  - Ledger floor: a report that counts any `code-review` round window also counts at least one ledger file read.
  - Yield-completed floor: the report holds no line starting `reviewer-yield pass: not completed`.
  - Sample check: neither the pooled headline nor the Read share prints `insufficient` or `no data`.
  - Output scan: no output file holds a run of 32 or more hex digits, a UUID shape, or a path under a home or config directory.

## The report as printed

Two edits to the output. The header's project-directory count is renamed "worktrees listed", because it counts `git worktree list` entries. Two groups of lines are withheld: the yield pass's gap counter, and the ledger section's directory-scan diagnostic lines. One placeholder stands in for each, and the capture's self-checks passed.

```text
REVIEWER READS SOURCES (this repo (33 worktrees listed); reads one account (the active account), the working directory's repository only; ~/.claude/transcript-config-dirs not consulted)

Unit: cache-read-token equivalents. A read's weight is its estimated tokens (4 chars/token) times one 5-minute cache write (12.5) plus one cache read (1) per later turn in its context window.
One price ratio, taken from the base multipliers in pricing.py, is applied across all models; per-model cache-read exceptions, the fast-mode multiplier and the inference-geo multiplier are not applied, so every share is a token-equivalent share, not a dollar share.
Class weights: cache_read=1, cache_write_5m=12.5, cache_write_1h=20, output=50, input=10.

window: 2026-10-25 to 2026-11-21 (UTC, both days included)
sessions=55 reviewer_windows=418 (sessions and the skipped input line's scan gaps count every retained in-scope transcript, whatever the window; its invalid_usage_turns counts every main-thread turn and only the reviewer windows in the window)
skipped input: unreadable_roots=0 unreadable_project_dirs=0 unreadable_main_files=0 unreadable_subagent_dirs=0 unreadable_subagent_files=0 unreadable_subagent_meta=0 invalid_usage_turns=0

## Whole-file reads of reviewed files larger than one Read call
partial is partial_token_cap or partial_unflagged and refused is refused_over_limit. A refused read is never counted as partial. The denominator is calls that were partial or refused, complete on a file over 2,000 lines, or allow_large at an estimated 25,000 tokens or more (4 chars/token).
code/other: partial no data (0/0); refused no data (0/0); partial or refused no data (0/0)
prose (instruction and other_prose; instruction is matched by path, whatever the extension): partial 100.0% (65/65); refused 0.0% (0/65); partial or refused 100.0% (65/65)
pooled: partial 100.0% (65/65); refused 0.0% (0/65); partial or refused 100.0% (65/65)
complete_allow_large calls on files of up to 2,000 lines with an estimate from 20,000 to 29,999 tokens, where the estimate alone decides the denominator: 0
outside the denominator, reviewed files only: other_error=7 size_unknown=0

## Whole-file calls in reviewer windows, by outcome and file size (lines)
code/other:
  refused_over_limit: total=0 up_to_1000=0 1001_to_2000=0 over_2000=0 unknown=0
  other_error: total=2 up_to_1000=0 1001_to_2000=0 over_2000=0 unknown=2
  size_unknown: total=0 up_to_1000=0 1001_to_2000=0 over_2000=0 unknown=0
  partial_token_cap: total=0 up_to_1000=0 1001_to_2000=0 over_2000=0 unknown=0
  complete_allow_large: total=2 up_to_1000=2 1001_to_2000=0 over_2000=0 unknown=0
  complete: total=227 up_to_1000=224 1001_to_2000=3 over_2000=0 unknown=0
  partial_unflagged: total=0 up_to_1000=0 1001_to_2000=0 over_2000=0 unknown=0
prose (instruction and other_prose; instruction is matched by path, whatever the extension):
  refused_over_limit: total=0 up_to_1000=0 1001_to_2000=0 over_2000=0 unknown=0
  other_error: total=5 up_to_1000=0 1001_to_2000=0 over_2000=0 unknown=5
  size_unknown: total=0 up_to_1000=0 1001_to_2000=0 over_2000=0 unknown=0
  partial_token_cap: total=65 up_to_1000=65 1001_to_2000=0 over_2000=0 unknown=0
  complete_allow_large: total=0 up_to_1000=0 1001_to_2000=0 over_2000=0 unknown=0
  complete: total=681 up_to_1000=681 1001_to_2000=0 over_2000=0 unknown=0
  partial_unflagged: total=0 up_to_1000=0 1001_to_2000=0 over_2000=0 unknown=0
diff handoff (the review diff, not a reviewed file):
  refused_over_limit: total=6 up_to_1000=0 1001_to_2000=0 over_2000=6 unknown=0
  other_error: total=0 up_to_1000=0 1001_to_2000=0 over_2000=0 unknown=0
  size_unknown: total=0 up_to_1000=0 1001_to_2000=0 over_2000=0 unknown=0
  partial_token_cap: total=20 up_to_1000=8 1001_to_2000=7 over_2000=5 unknown=0
  complete_allow_large: total=1 up_to_1000=1 1001_to_2000=0 over_2000=0 unknown=0
  complete: total=51 up_to_1000=51 1001_to_2000=0 over_2000=0 unknown=0
  partial_unflagged: total=0 up_to_1000=0 1001_to_2000=0 over_2000=0 unknown=0

## After a partial or refused whole-file call, in the same reviewer window
The command sees Read calls only, so the neither figure is an upper bound on calls after which the reviewer made no further attempt to read on: a Grep, Bash or diff read that recovered the content is not seen.
code/other: calls=0 later_offset_read no data (0/0); covered_after no data (0/0); neither (no later offset Read, and not covered by later Reads) no data (0/0)
prose (instruction and other_prose; instruction is matched by path, whatever the extension): calls=65 later_offset_read 95.4% (62/65); covered_after 92.3% (60/65); neither (no later offset Read, and not covered by later Reads) 4.6% (3/65)
diff handoff (the review diff, not a reviewed file): calls=26 later_offset_read 96.2% (25/26); covered_after 34.6% (9/26); neither (no later offset Read, and not covered by later Reads) 3.8% (1/26)

## Read share of reviewer spend, a share of modeled billed weight and not of tokens (418 reviewer windows)
Read weight over billed weight: 12.7% (279,450,796.0/2,198,333,289.0)
  of Read weight, files over 1,000 lines: 18.0% (50,345,894.5/279,450,796.0)
  of Read weight, code/other reviewed files over 1,000 lines: 7.0% (19,597,442.0/279,450,796.0)
  of Read weight, diff handoffs over 1,000 lines: 10.4% (29,037,275.5/279,450,796.0)
  of Read weight, files of unknown size: 0.0% (0.0/279,450,796.0)
sums: billed_weight=2,198,333,289.0 read_weight=279,450,796.0

## By reviewer type, counts only (windows counts every reviewer window and the other counts cover reviewed files, not diff handoffs; agent types this repo does not track are folded into one withheld row)
TOTAL: windows=418 partial=65 refused=0 larger_than_one_call=65
ciso-reviewer: windows=47 partial=8 refused=0 larger_than_one_call=8
comment-discipline-reviewer: windows=86 partial=15 refused=0 larger_than_one_call=15
staff-analytics-engineer: windows=2 partial=0 refused=0 larger_than_one_call=0
staff-backend-engineer: windows=59 partial=11 refused=0 larger_than_one_call=11
staff-platform-engineer: windows=41 partial=10 refused=0 larger_than_one_call=10
staff-product-engineer: windows=39 partial=8 refused=0 larger_than_one_call=8
staff-sdet: windows=144 partial=13 refused=0 larger_than_one_call=13

## Main-thread Reads inside review-round windows, counts only
code-review: round_windows=74 read_calls=287 whole_file=240 targeted=47
  reviewed-file whole-file calls by outcome: refused_over_limit=0 other_error=1 size_unknown=0 partial_token_cap=0 complete_allow_large=0 complete=226 partial_unflagged=0
  reviewed-file whole-file calls by file size: up_to_1000=226 1001_to_2000=0 over_2000=0 unknown=1
  diff-handoff whole-file calls: 12
plan-review: round_windows=24 read_calls=144 whole_file=122 targeted=22
  reviewed-file whole-file calls by outcome: refused_over_limit=0 other_error=0 size_unknown=0 partial_token_cap=1 complete_allow_large=0 complete=121 partial_unflagged=0
  reviewed-file whole-file calls by file size: up_to_1000=122 1001_to_2000=0 over_2000=0 unknown=0
  diff-handoff whole-file calls: 0
ready-for-review: round_windows=36 read_calls=20 whole_file=17 targeted=3
  reviewed-file whole-file calls by outcome: refused_over_limit=0 other_error=0 size_unknown=0 partial_token_cap=0 complete_allow_large=0 complete=17 partial_unflagged=0
  reviewed-file whole-file calls by file size: up_to_1000=17 1001_to_2000=0 over_2000=0 unknown=0
  diff-handoff whole-file calls: 0

## Reviewer-yield: main-thread reviewer dispatches in the window (agent types this repo does not track are folded into one withheld row)
(--until 2026-11-21 does not bound the cited, active and edited counts: their tool-result and edit indexes are bounded by --since alone.)
[the yield pass's gap counter is withheld; the capture's self-checks passed]
TOTAL: dispatches=431 findings_found=351 zero_finding=77 unclassified=3 findings=1,653
  findings-found: cited=337 active=337 edited=124 edited_rate 36.8% (124/337)
  zero-finding: cited=73 active=73 edited=13 edited_rate 17.8% (13/73)
ciso-reviewer: dispatches=47 findings_found=37 zero_finding=10 unclassified=0 findings=178
  findings-found: cited=37 active=37 edited=17 edited_rate 45.9% (17/37)
  zero-finding: cited=10 active=10 edited=4 edited_rate 40.0% (4/10)
comment-discipline-reviewer: dispatches=86 findings_found=69 zero_finding=17 unclassified=0 findings=333
  findings-found: cited=57 active=57 edited=15 edited_rate 26.3% (15/57)
  zero-finding: cited=15 active=15 edited=2 edited_rate 13.3% (2/15)
skill-fidelity-reviewer: dispatches=13 findings_found=0 zero_finding=13 unclassified=0 findings=0
  zero-finding: cited=13 active=13 edited=0 edited_rate 0.0% (0/13)
staff-analytics-engineer: dispatches=2 findings_found=2 zero_finding=0 unclassified=0 findings=7
  findings-found: cited=2 active=2 edited=0 edited_rate insufficient (0/2)
staff-backend-engineer: dispatches=59 findings_found=41 zero_finding=17 unclassified=1 findings=185
  findings-found: cited=41 active=41 edited=11 edited_rate 26.8% (11/41)
  zero-finding: cited=17 active=17 edited=2 edited_rate 11.8% (2/17)
staff-platform-engineer: dispatches=41 findings_found=39 zero_finding=2 unclassified=0 findings=193
  findings-found: cited=38 active=38 edited=12 edited_rate 31.6% (12/38)
  zero-finding: cited=2 active=2 edited=0 edited_rate insufficient (0/2)
staff-product-engineer: dispatches=39 findings_found=35 zero_finding=4 unclassified=0 findings=209
  findings-found: cited=35 active=35 edited=18 edited_rate 51.4% (18/35)
  zero-finding: cited=3 active=3 edited=1 edited_rate insufficient (1/3)
staff-sdet: dispatches=144 findings_found=128 zero_finding=14 unclassified=2 findings=548
  findings-found: cited=127 active=127 edited=51 edited_rate 40.2% (51/127)
  zero-finding: cited=13 active=13 edited=4 edited_rate 30.8% (4/13)

## Review-ledger terminal disposition rows in the window (disposition rows, not distinct findings: a finding re-raised without --ref counts again)
terminal rows: ADDRESS=430 DEFER=79 SETTLED=19 total=528
ADDRESS share of terminal rows: 81.4% (430/528)
DEFER share of terminal rows: 15.0% (79/528)
sessions with a disposition row=32 covered by the transcript scan=32
[the ledger section's directory-scan diagnostic lines are withheld; the capture's self-checks passed]

## Comparability: reviewer windows by harness version and by model
harness version: 2.1.328=14 2.1.329=389 2.1.330=15
model: claude-sonnet-5-5=418

## Diagnostics (calls are counted over every role, diff handoffs included)
unexplained partials (partial_unflagged on files of up to 2,000 lines): 0
notice agreement: partial_token_cap calls with no read_truncation_notice=0; notices naming neither a partial_token_cap nor a size_unknown call=0; notices naming a size_unknown call=0
size_unknown by reason: multi_result_record=0 tool_use_result_not_a_dict=0 file_not_a_dict=0 file_path_mismatch=0 line_field_invalid=0 truncation_flag_invalid=0 start_after_first_line=0 lines_exceed_total=0
all roles: other_error=7 unrecognised_limit_error=0
skill-fidelity-reviewer windows left out, in the window: 13
reviewer windows with no timestamped record, whatever the window: 0
review-round windows whose opening record has no parsable timestamp, whatever the window: 0
```

The page describes each diagnostic by its printed definition only.

## Comparability record

Rerun this the same way after #1115 and compare like with like.

- **Harness versions and models:** reviewer windows ran on three harness versions (2.1.328 for 14 windows, 2.1.329 for 389, 2.1.330 for 15) and one model label (`claude-sonnet-5-5`, 418 windows).
- **Model labels:** they follow `pricing._MODEL_BASE_INPUT_RATES` at instrument commit `e5e1f34f573a`. A model priced after that commit prints `other` here and by name in a later run, so that move alone is not a model shift. `other` can also stand for a window whose first assistant record is the harness's `<synthetic>` error record, in which case no rate moves.
- **Re-run recipe:** this clone, from a worktree cut from the default branch, the same window length, the same pinned account, and a run before any worktree cleanup.
- **Edits that void a comparison:** later edits to `read_cost`'s scanner and weights, to `reviewer_reads`, `ledger_dispositions`, `publication_scope`, `reviewer_yield._is_reviewer_subagent_type`, or to the ledger reader in `author_outcome` (`_read_ledger_rows_from_file` and `_SESSION_ID_PATTERN`). A run after such an edit measures a different instrument.
- **Review-skill mix behind the figures:** main-thread round windows in the window were 74 for `code-review`, 24 for `plan-review` and 36 for `ready-for-review`. This is the only indicator of that mix on this page.

What a rise or fall after #1115 can and cannot show, read against #1115's body:

- **Headline partial and refused rates:** before-state only. #1115's entry read is still one default Read, so the rate can hold or rise while reviewers handle a partial view as #1115 prescribes.
- **Larger-than-one-call calls per reviewer window:** a fall shows fewer whole-file attempts on large files. No fall does not show #1115 failing, because the entry read still probes such files unless line counts arrive beforehand.
- **Per-type counts:** the only place #1115's per-lens exceptions show. `ciso-reviewer`'s and `staff-data-engineer`'s counts may fall less, because #1115 keeps their CI and policy config files and their migrations whole.
- **`covered_after` per reviewer window:** before-state only. #1115 replaces paging through the rest of a file with an outline and a function-context diff, so a fall is by design.
- **`later_offset_read` per reviewer window:** it can rise on #1115's fallback of reading an enclosing function's range. A rise does not show that the rest of the file was read.
- **`neither` per reviewer window:** before-state only. #1115's outline and diff are invisible to the instrument, while its fallback adds a ranged Read the instrument counts. Its direction therefore cannot be predicted.
- **The Read share and its over-1,000-line part:** neither direction identifies #1115 working. Its mandatory expansions add Reads of other files while its entry rule cuts Reads of large changed files.
- **The ledger dispositions:** a move shows a change in the mix of terminal disposition rows. A finding re-raised without `--ref` adds a row, so re-raising can move the mix as well as resolution. It cannot attribute that change to how files were read.

## Confounders in the window

Changes to the instruction the reviewers run on, from `git log --oneline` on `origin/main` over the window.

`claude-skills/skills/code-review/SKILL.md`:

```text
23edc52b Record the reviewed state on every review-ledger row (GH-1481) (#1512)
ccab57e5 comment rule false angle fix (#1493)
ae0da0ff review ledger address site and noise stop (#1469)
f7900acd GH-1410: dispatch prompt contract (#1418)
b5666046 disposition yield ledger join (#1411)
fcadb7c4 GH-1397: prose claim truth check (#1399)
1d73b940 adversarial architect disposition reviewer (#1369)
81f97e0c GH-1199: reviewer declared surface (#1358)
d246e014 prose granularity rule (#1354)
de63e992 clarify defer invariant diff reading (#1349)
01c8bde0 GH-1006: prose density reviewer gaps (#1338)
```

The agent files for the reviewer types in the report (`ciso-reviewer`, `comment-discipline-reviewer`, `skill-fidelity-reviewer` and the four `staff-*` types it lists):

```text
ccab57e5 comment rule false angle fix (#1493)
27afb97d Fix staff-sdet contract-test citation to test-conventions section 7 (#1422)
dcb0588f Add boundary-rule enforcement guidance and record library decline (#1414)
f7900acd GH-1410: dispatch prompt contract (#1418)
fcadb7c4 GH-1397: prose claim truth check (#1399)
b73f19bd plan prose pass (#1383)
81f97e0c GH-1199: reviewer declared surface (#1358)
d246e014 prose granularity rule (#1354)
01c8bde0 GH-1006: prose density reviewer gaps (#1338)
```

#1113's file-splitting children, by the merge dates of the pull requests whose titles carry their issue number, as #1113's task list names them at the run:

- #1116 (checked): five PRs from 2026-10-27 to 2026-11-09.
- #1210, `test_lib.py` (checked): four PRs from 2026-10-25 to 2026-10-30.
- #1118, `test_skills.py` (unchecked on the task list, which still reads "phase 4 of 4 in flight"): four PRs merged on 2026-11-17, 2026-11-18, 2026-11-19 and 2026-11-20.
- #1530, #1531 and #1532 (unchecked): none merged in the window.

#1115 was unmerged at the run.

## Limitations

- **This clone only.** Sessions recorded under any other clone of the repository are not included.
- **Live worktrees only.** Sessions of removed worktrees are not included. The sample is not a random sample of reviews.
- **Path identity, not repository identity.** Both halves of the scope rest on it. It does not exclude:
  - a live worktree path of this checkout that another repository's checkout occupied earlier;
  - ledger rows appended from this checkout about work elsewhere;
  - a checkout of any repository whose path maps to the same project-directory slug as one of this checkout's worktrees;
  - a subagent file under an in-scope session, whatever repository the subagent worked in.
- **Ledger file check.** The ledger reader's regular-file check is point-in-time. It does not exclude a hard link named for this checkout, or a swap between its `lstat` and the open.
- **Whole-file counts per round skill.** They can exceed the outcome counts plus the diff-handoff counts. The join counts each Read `tool_use` block in a round window once by id, while the outcome counts skip an id already seen earlier in the run and a call with no usable result. The gap is not a defect.
- **Plan-review windows.** Reviewer windows include `plan-review` dispatches, whose reads of code files stay in `code/other`, so the per-type rows do not isolate the review skill.
- **Prose.** It is `instruction` plus `other_prose`. `instruction` is decided by path, whatever the extension, so it also holds code and JSON files under `skills/`. Only its markdown part lies outside #1115's change for every reviewer. `other_prose` lies outside it for `comment-discipline-reviewer` alone.
- **ADDRESS and DEFER shares.** They count disposition rows, and a finding re-raised without `--ref` counts again.
- **`neither`.** It is an upper bound on calls with no further attempt to read on, because Grep, Bash and diff reads are not seen.
- **`covered_after`.** It can be wrong at a flagged result's last reported line, in both directions. A flagged range that ends short of the file's last line still adds `[1, numLines]`, though line `numLines` can have arrived only in part. A flagged range that reaches the file's last line adds no interval, though lines 1 to `numLines − 1` arrived whole. The second case is a deliberate conservatism: it under-credits a call and never over-credits one.
- **Under-cap truncation.** What a 2,000-line default truncation of an under-cap file returns was not tested. `partial_unflagged` catches it structurally whatever its shape, and this run found none.
- **Reviewer types.** `_is_reviewer_subagent_type` matches bare agent-type names with no plugin namespace. A namespaced value on another harness version would fall outside the population.
- **Yield and reads.** The yield figures count main-thread dispatches only and bound their edit table by `--since` alone. Nested reviewer dispatches therefore appear in the read figures and not in the yield figures.
- **Diff handoff.** Reviewers receive the review diff as a file. Its whole-file Reads are reported as their own class, not as reviewed files.
- **Notice-agreement `other` bucket.** A notice can land in "notices naming neither a partial_token_cap nor a size_unknown call" for more than a real disagreement. A notice naming a call the instrument does not count as whole-file lands there, for example a Read with `offset: 1` and no `limit`. The printed label is true either way, but the count cannot be read as a count of real disagreements only.
- **The instrument's own review rounds.** The window holds the review rounds of the change that built this instrument (#1575), as a later run's window will hold #1115's.

## What this page does not cover

- It records no late-findings before-value. That measure moved to its own issue, #1556.
- Ticking #1113's "A-field baseline captured" box records the date and this page's path. It does not cover #1115's late-findings watch.
