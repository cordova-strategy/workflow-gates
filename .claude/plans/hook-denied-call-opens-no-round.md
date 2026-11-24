# Fix: a hook-denied call opens no review round (GH-1131)

## Context

Goal: make the shared round detector stop counting a `Skill` or `review-orchestrator` call that one of this repository's gates denied as a review round, and ship that fix with a re-record rule inside plain `pr-cost --record`, so the command every machine already runs does the re-record, as the first of two PRs toward the routing study.

Ask: "What I'd recommend here is to make it so that you can be accurate for phantom rounds for past recorded ledgers and then fix the underlying bug so that phantom rounds are not counted going forward." On this PR's split and size the engineer said: "I'm planning to have this complete in a week", "This is still way too complicated and over-engineered", and "same script, same heuristic, no exceptions", and accepted starting this plan with "Sure." They also said: "don't put any dates, please, in the plan, because it's based on number of PRs, not time".

Why now: when the routing gate denies a `Skill(code-review)` call and the review runs through the orchestrator instead, the detector counts the denied call as a round and the orchestrator dispatch as a second one. Every round consumer, and every pr-cost ledger row whose branch had such a denied call, therefore overcounts. A comparison of routed and unrouted review rounds cannot be trusted until this is fixed and the rows are recounted.

Intended outcome: after this PR, no round-window consumer counts a call one of this repository's gates denied as a round, except `routing-guard`, which keeps the overhead definition the routing-gate record fixed before that guard runs. Invocation counters (`subagent-mix`, `judgment-pair`, `skill-invocation`) still count a denied `Skill` call as an invocation, because they do not detect rounds. Plain `pr-cost --record` re-records a captured PR whose row is below the current rule when the surviving transcripts reproduce the row's figures, and every machine runs that same command.

Publication limit: this plan, its commit and its PR carry no per-account, per-machine or per-branch figure.

Selections for this plan, each from the engineer:
- Per-round `spawn_open` flag: "Drop it (Recommended)".
- Re-record script, first selection: "Yes, all old-rule PRs, flag session drops (Recommended)". Superseded by "Yes, use the check (Recommended)", which "Check inside pr-cost (Recommended)" then superseded.
- Several accounts, where `pr-cost` accepts a re-record only with `--all-accounts`: "Accept, script prints every change (Recommended)". Superseded by the one-account pin below.
- Scan-first script: "Yes, use the check (Recommended)". Superseded by "Check inside pr-cost (Recommended)", then "Yes" to the rewrite around it.
- Where the check runs, live: "Check inside pr-cost (Recommended)".
- One-account pin and newest-first order for a driving script: the engineer answered the proposal "I think I agree with you but what does the architect think?", and the architect advised both. Superseded by the walk mode below, which has no script to pin.
- Walk mode, superseded by the fold below: the engineer wrote "I think option A is good because it's simpler, but just to be safe, can you get Fable's take?", and then "go" after the architect and Fable both advised it. Option A, agent wording, is a `--record` mode with no `--pr` that walks each account's below-rule rows inside `pr-cost`; the option not chosen is the driving script. The recoverable-row count was run at the engineer's "Sure count first", and the engineer then said "go". The plan states no count.
- Fold, live: after the architect and Fable both advised it, the engineer typed "I accept that, \"fold\"". The fold, agent wording, puts the unchanged-figures check into plain `--record`'s already-captured skip, with no new flag or mode, and reverses the documented rule that an unforced re-record of a captured PR refuses. The options not chosen are the trimmed walk and a split into two PRs.
- Pre-merge rehearsal, live: the engineer wrote "sure, pre-merge rehearsral is fine." and "you gotta minimize what I run manually though. please script as much as possible." and "go". Each engineer-run step is therefore one command that a script does the work for.
- Round 5 disposition, live: the engineer's "go" accepted the session's proposal to take the round 5 findings listed in its verdict and to relabel the three rows whose tags claimed more than their quotes as unverified, with the quotes beside them.
- Round 6 disposition, live: after the architect's advice on the round 6 findings, the engineer answered "Agreed" to the session's relay of it. The relay, agent wording, took the rehearsal fix, the test and docs fixes it listed and the ledger-tag fixes, and declined the rest. Its three picks: the already-captured line stays unedited with docs wording only; a persistent refusal keeps exit 0 with no new summary line; all nine beyond-the-Ask items are accepted as stated. It also made any failed breakdown check on an unforced re-record a skip, under one rule that an unforced re-record either writes a row whose every cell passes or skips, with exit 0 when no `--pr` is given.
- `routing-guard`, live: "Keep the guard's definition (Recommended)", so `routing-guard` keeps counting a denied call as a round.
- Routing-gate record, live: "Routing-gate record edits", which covers the two stale GH-1131 sentences in the record. On its line 78: "Leave it, note for study PR (Recommended)".
- Size, live: "Proceed anyway", answered at about 950 changed lines after earlier answers at about 1,400 and about 800. The plan's recount for the fold with the round 6 fixes is about 710 to 760, an estimate whose range `Projected diff:` states. "Cut it (Recommended)" removed the miner test.

Why the design moved. Round 1 of `/plan-review` found that a child `pr-cost` run can write rows outside the script's worklist and permanently store smaller figures for a partly aged PR. The engineer said the script "needs to bring a report" but "the expectation should NOT be that I manually run the commands", because "I will NOT be able to judge each partly aged PR". Round 2 found that a script predicting `pr-cost`'s write decision from outside has gaps no patch closes, so the check moved into `pr-cost` as an opt-in flag on `--force`; the engineer wrote "Ask the architect to review that choice" and "What does Fable think?", then answered "Yes" to rewriting the plan around it. Round 3 found stray writes and an unclear report, which a one-account pin and an exit-status report answered. Round 4 found that most remaining concerns sat at the boundary where a parent script launches one `pr-cost` child per PR and reads its exit status, so the walk moved into `pr-cost` and the script went away. Round 5 then found the walk's findings clustering on its target set and its separate report, and the architect and Fable both advised folding the check into plain `--record`, which the engineer accepted. On the extras, the engineer answered "Have the architect adversarially review those additions", and the plan applies that review's verdicts.

Out of this PR: the study command, any look or calendar date, retention changes, and the decision to retire `routing-guard`. The study command is a second PR with its own plan.

## Approach

A `Skill` or `review-orchestrator` spawn call that one of this repository's gates denied opens no review round and ends no round window, and `REVIEW_ROUND_RULE` becomes 2. Plain `pr-cost --record`, the command every machine already runs, then re-records a captured row below that rule when the account's fresh scan reproduces the row's figures and every cell of the new row passes its check, and skips the row otherwise.

**Which denials count.** A `tool_use` block is denied when a non-sidechain record of the same session holds one of two shapes for its id:
- a legacy `hook_blocking_error` attachment, from any hook, whose `attachment.toolUseID` is a non-empty string and whose `attachment.hookEvent` is absent or `PreToolUse` (rows 4, 38, 74);
- an `is_error` tool_result whose text `_denial_hook_label` reads as a member of `_DENIAL_HOOK_LABELS`, the labels of the gates this repository ships (row 3).

These still open a round:
- an ordinary errored call;
- in the current shape, a denial by a hook this repository does not ship;
- a legacy attachment with no usable id;
- a call the permission layer, auto mode or the user refused (row 41).

One over-match remains: an errored `Agent` result that names a shipped gate loses its round even when the subagent ran (row 37).

**The detector fix.**
- `denials.hook_denials_in_record(rec)` is `routing_guard._hook_denials_in_record`, moved and made public with its body unchanged (rows 5, 6).
- `denials.hook_denied_tool_use_ids(records) -> frozenset[str]` walks the session's non-sidechain records through `hook_denials_in_record`, as `_record_routing_denies` does (routing_guard.py:1033-1036). It keeps the non-empty `str` ids of the two shapes above. It reads each record's shape and `attachment.hookEvent` from the record itself, because the yielded tuple carries neither (row 74).
- In `review_rounds.py`, one helper drops the content blocks whose `id` is in the denied set.
  - `_round_open_skill(rec, denied_tool_use_ids)` and `round_opened_by_spawn(rec, *, denied_tool_use_ids)` match on the blocks that remain.
  - The keyword is required, so no caller pairs detected windows with an empty set by accident.
- `detect_round_windows(records, *, denied_tool_use_ids=None)` computes the set when the argument `is None`, because an empty set is falsy. It passes the set to the open check (:223) and the window-end check (:232) (row 1).
- `REVIEW_ROUND_RULE` becomes 2. Its comment adds three edits to what bumps it: changing `_HOOK_DENIAL_SIGNATURE`, changing `_DENIAL_HOOK_NAME_PATTERNS`, and removing or renaming a `_DENIAL_HOOK_LABELS` entry. `_DENIAL_HOOK_LABELS` gains a one-line comment pointing there (rows 40, 80).
- `routing_guard._add_session_facts` passes a module-level empty set at `detect_round_windows` (:1095), `author_outcome._code_review_rounds` (:1100) and `round_opened_by_spawn` (:1149) (rows 8, 10).
  - The constant's one-line comment says routing-guard's recorded overhead definition counts a denied call as a round.
  - The local `denied_tool_use_ids` at :1099 and its read at :1148 become `routing_denied_ids`, so the routing-deny set does not carry the new keyword's name one line above :1149 (row 105).
  - `_CAPTURE_REVISION` stays 1.
- `author_outcome._code_review_rounds(records, denied_tool_use_ids=None)` passes the keyword through to `detect_round_windows`.
- The review-bench miner computes the set once per session and passes it to both calls (mine_review_rounds.py:192, :199). `select-tests.py`'s `_REVIEW_BENCH_SCRIPTS_DEPENDENCIES` gains `transcript_analysis/denials.py` (row 11).

A denied call's turns stay in the round window open before it, or fall outside every window when none is open. A denied spawn inside an open window counts in that round's `dangling`, as any unlaunched dispatch does (row 45).

**The re-record inside plain `--record`.** It adds no flag, mode or argument check (row 18). It reverses `docs/pr-cost.md:271`'s rule that an unforced re-record of a captured row refuses, but only for a row that meets the predicate below (rows 20, 81, 82). Plain `--force` is unchanged (row 17). Row 34 lists the choices that go past the fold as Context describes it.

The predicate is a pure `_reproduces_older_rule_row(prior_row, agg, fresh_status) -> bool` beside `_review_rounds_force_refusal`. It holds only when all of these do (rows 19, 22, 83):
- `prior_row` and `agg` are not `None`.
- `prior_row["review_rounds"]` is not `None`, and its `rule` is below `REVIEW_ROUND_RULE`.
- `session_count`, `turn_count` and the five `*_tokens` columns equal `len(agg["sessions"])`, `agg["turn_count"]` and the five `agg["tokens"]` values, as `_new_pr_cost_row` maps them (:573-578).
- `agg["last_activity_ts"]` is no later than `corpus._parse_ts(prior_row["captured_at"])`.
- `fresh_status` is `ok`, or `prior_row["status"]` is not `ok`.

No other column is compared. The dollar columns, `rate_stamp`, `unpriced_*`, `invalid_usage_records`, the other agg-derived columns and the enrichment columns may differ (row 108). The predicate names no rule value, so a later bump re-records the same way.

Its call sites (rows 16, 84):
- The hint at :1029 skips when its advisory row exists and `not (force or _reproduces_older_rule_row(hint_row, branch_totals.get(branch), row_status))`. Every input exists by then, so a run whose captured rows all fail the predicate still makes no round scan (row 83).
- Under the per-branch lock, `overwrite_captured = force or _reproduces_older_rule_row(already, branch_totals.get(branch), row_status)` replaces `force` in the check at :1056.
- The guard at :1117 and `_append_pr_cost_ledger_row` at :1133 read `overwrite_captured`, so the guard runs before every overwrite (row 89).

The hint and the locked check read different rows, so each evaluates the predicate on its own row. Only the locked value decides the write.

**Without `--force`, a re-record writes a row whose every cell passes, or skips** (rows 21, 85, 86, 99). A skipped row needs no command, because the next plain `--record` retries it.
- A row that fails the predicate prints today's already-captured line, unchanged (row 96).
- A row that passes the predicate is skipped at the guard site, in the guard's `continue`, when its new rounds cell is empty or its new breakdown failed its check, whatever the prior breakdown held (row 66). An empty rounds cell comes only from a failed round pass, a failed cell check or a build error (row 85).
- That skip prints one line, `pr-cost:   PR #<n> for machine=<m>: refusing to re-record (<reason>); see docs/pr-cost.md`. The reason is the guard's own, or `the per-model breakdown failed its <rule> check`.
- Both skips leave the ledger unchanged and take the already-captured skip's exit. A single-account `--pr` run exits 1. Any other run `continue`s without setting `force_refused`, so it exits 0 and prints no new summary line (row 97).
- A written re-record therefore never reaches the failed-cells footer, and a scheduled plain `--record` never starts exiting 1 because of an old row.

With `--force`, the guard keeps its `refusing --force` line and its exit 1, and a failed breakdown check still writes the row and reaches the footer, as today.

**Rows that stay below the rule.** `review-cost-by-size` keeps excluding each such row, which is the standing signal and needs no new output (row 90):
- A row whose branch has no surviving activity, under every design. Its branch is not in `branch_totals`, so a run without `--pr` never visits it (rows 59, 70).
- A row whose surviving transcripts no longer reproduce its figures, including a run under different scope flags from the capture's (row 65).
- The other PR's row when a branch name was reused, because the branch resolves to one PR (row 55).
- A row whose PR has left the merged list (row 57).
- An `ok` row whose fresh enrichment is degraded, until `gh` recovers (row 22).
- A row skipped because a new cell failed, until the cause is fixed (row 99).

Each write is an atomic replace, so an interrupted run loses no written row (row 25).

**Residuals of the re-record.**
- The fold does not compare `dangling`. A meta sidecar lost while its transcript survives lowers a round's priced agent cost but not its round count, and the new cell records the loss as `dangling` (row 92).
- A transcript lost between the scalar scan and the round scan can shrink a re-recorded cell while the predicate holds (row 93).
- On a machine whose clock reads earlier than a captured row's `captured_at`, each run appends a row that never becomes current (row 94).

**Rollback.** Once any row is at rule 2, a revert hides those rows from `review-cost-by-size`, and the reverted checkout cannot re-record them (row 39). Recovery is therefore forward-only. A defect fix that changes which records open a round needs a second bump (row 80). So does a fix to a predicate or guard defect, because the rows that defect wrote already sit at the current rule (rows 39, 91). That bump re-excludes every rule-2 row, and the next `--record` re-records only the rows whose transcripts still reproduce their figures. The assumptions whose failure would force it are rows 38 and 52.

**Text.** The detection rule has one home, a new bullet in `docs/transcript-analysis.md`'s "Round detection caveats" under `review-round-cost`. The re-record exception has one home, a new paragraph in `docs/pr-cost.md` § "The re-record contract". Every other site points at those, the CHANGELOG entry included (row 88).

**Alternatives set aside.**
- **`hook_denial_key`'s idiom alone as the signal.** It matches gate wording anywhere in an errored result, so an errored `Agent` result whose subagent ran would lose its round (row 3).
- **routing-guard's own join.** It covers one gate's denial of one skill, so a denied spawn, or another gate's denied `Skill`, would still count (row 7).
- **A harness launch record as the spawn signal.** `detect_round_windows` sees records only, so every caller would have to pass the session's path, for a residual with no known producing shape (rows 37, 45).
- **A stored per-round flag instead of a recount.** The engineer dropped it (row 9), and no flag can correct a row whose transcripts are gone (G3).
- **Moving `routing-guard` to the new rule.** The engineer kept its definition (row 8).
- **A test pinning the third empty-set site in `_add_session_facts`.** Renaming the routing-deny local removes the name collision that would invite the wrong set, at no test cost (row 105).
- **Pinning `_DENIAL_HOOK_LABELS` to a literal per rule.** A new gate's label changes no earlier transcript's reading, so a pin would force a bump, and a re-record cycle, for every new gate (row 40).
- **Rewriting the denial patterns for linear time.** This change adds no input shape that routing-guard's capture does not already match (row 43).
- **The walk mode, `pr-cost --record --if-unchanged`.** Round 5's findings clustered on its target set and its separate report, and the engineer accepted the fold (rows 60, 81).
- **A split into two PRs.** The engineer accepted the fold over it (row 81). A detector PR alone would leave every older row excluded until the second PR shipped.
- **A driving script that runs one `--force` child per PR.** Round 4 found most remaining concerns at the boundary where the script launched children and read their exit status (rows 60, 61).
- **A script that predicts pr-cost's writes from outside and checks the ledgers afterwards.** Each gap in the prediction surfaced only after a permanent append, and the engineer chose the check inside pr-cost (row 28).
- **Checking the figures under plain `--force`.** Row 17 says why.
- **Exiting 1 on an unforced refusal.** A scheduled `--record` would exit 1 on every run while the cause lasted, for a row it leaves exactly as it was, and the engineer kept exit 0 (rows 86, 97).
- **Refusing only an empty breakdown over a populated one.** It would compare the two breakdowns, and a skip loses nothing, because the next plain `--record` retries the row (row 99).
- **Editing the already-captured line.** The engineer kept it unedited, with docs wording only (row 96).
- **Evaluating the predicate only under the lock.** The hint would then send every captured row below the rule into the round scan, and the predicate needs nothing from that scan (row 83).
- **A shared helper for the seven columns' derivation.** A drift between `_new_pr_cost_row` and the predicate can only make the predicate fail, which skips the row.
- **Comparing summed `dangling` between the two cells.** Row 92 says why the shape it catches can be left as a residual.
- **A clock check.** The residual needs a machine clock that runs behind its own earlier capture, and the rows it appends never become current, so the harm stays in ledger history (row 94).
- **A dry-run mode.** The predicate decides each row, so a preview would hand the engineer a per-PR judgment they said they cannot make (row 49). Verification 5 instead rehearses the real run on a copy and reports counts and booleans only.

**Assumption ledger**

**Root:** Round detection opens a round on any review `Skill` or `review-orchestrator` spawn `tool_use` block and never reads whether a hook denied it (row 1), and only a re-record from surviving transcripts can correct a recorded cell (G3).

**Givens:**
- G1. A hook denial reaches a transcript only as an `is_error` tool_result whose text the gate wrote, or as a legacy `hook_blocking_error` attachment. The current shape carries no structured hook identity. Reason: Claude Code's transcript format imposes it (`denials.py:26-39`).
- G2. Transcripts age out after `cleanupPeriodDays`, and nothing records when a PR's first session began. Reason: Claude Code's retention imposes it (`docs/pr-cost.md:271`).
- G3. A recorded cell stores nothing that separates a denied round-open from a real one. Reason: those rows are already written on every recording machine (`docs/pr-cost.md:76`, `:91-98`).

**Mechanisms:**
- **M1.** The denied-id set lives in `denials.py`, an enumerated gate label corroborates a text denial, and the record walk moves there without new guards. anchors: root, row3, row4, row5, row6, row7, row38, row50, row51, row52, row74, row104
  - Over-powered check. Two lighter primitives fail. `hook_denial_key` alone over-matches an ordinary errored result (row 3). routing-guard's join covers one gate's denial of one skill (row 7).
- **M2.** The detector drops denied blocks at both its open check and its window-end check, and the rule becomes 2. anchors: root, row1, row2, row14, row40, row45, row80
- **M3.** Default callers change on purpose, routing-guard passes an empty set under a renamed local, and the miner passes the computed set. anchors: row2, row8, row10, row11, row105
- **M4.** Plain `--record` re-records a row below the rule when its fresh scan reproduces the row and every new cell passes, through one pure predicate at the two already-captured checks and one skip at the guard site, and it turns every unforced non-write outcome into a skip. anchors: row16, row17, row18, row19, row20, row21, row22, row25, row28, row34, row54, row55, row57, row59, row63, row65, row66, row67, row69, row70, row71, row75, row76, row81, row82, row83, row84, row85, row86, row87, row89, row90, row91, row92, row93, row94, row96, row97, row98, row99, row100, row103, row107, row108
  - Over-powered check. Reversing a documented contract is wider than leaving it alone. Two lighter primitives fail. Leaving older rows excluded leaves the Ask's past ledgers uncorrected (root). A documented `--force --pr N` per PR needs a per-PR command and a per-PR judgment, both of which the engineer ruled out (rows 48, 49).
- **M5.** Every machine's existing `--record` does the re-record with no new command, and each engineer-run Verification step is one scripted command. anchors: row24, row30, row31, row48, row49, row60, row61, row62, row64, row68, row73, row77, row78, row79, row95, row101, row102
- **M6.** Each fact has one text home, and the other sites point at it. anchors: row12, row32, row33, row42, row51, row56, row88, row106

**Rows:**
1. `_round_open_skill` reads only `tool_use` blocks and the `/slash` tag. `detect_round_windows` calls it for the open check (:223) and the window end (:232), so a denied block both opens a round and ends the previous window. [verified: review_rounds.py:142-236]
2. Non-test callers: [verified: an earlier revision's Grep; the routing_guard.py, author_outcome.py and mine_review_rounds.py sites re-read]
   - `detect_round_windows`: review_rounds.py:545 and :607, routing_guard.py:1095, author_outcome.py:241, review_trace.py:591, mine_review_rounds.py:192.
   - `round_opened_by_spawn`: routing_guard.py:1149 and mine_review_rounds.py:199.
   - `_code_review_rounds`: routing_guard.py:1100 and author_outcome.py:794.
   - `_round_open_skill`: no caller outside review_rounds.py.
3. `hook_denial_key` marks any `is_error` result whose text matches a loose idiom (`denials.py:40-45`, `:84-90`). `_denial_hook_label` returns `"unmatched"` unless the extracted name is in `_DENIAL_HOOK_LABELS` (`:128-167`, `:261-283`). The routing gate's label, "review-orchestrator routing", is a member (`:156`). [verified]
4. The attachment shape is matched exactly on `hook_blocking_error` (`denials.py:79-83`) with no shipped-gate check, so a legacy denial by any hook counts. `_denial_hook_label` reads an unenumerated `hookName` as unmatched (`:273-275`), so applying the label check to attachments would drop real legacy denials. [verified: denials.py from an earlier revision's read; the any-hook reading from the round-4 product review]
5. `_hook_denials_in_record` (routing_guard.py:975-996) has one production caller (:1036) and one test caller (test_transcript_routing_guard_capture.py:1647). `denials.py` imports only `corpus` and `render` (`:15`), so `review_rounds` importing it makes no cycle. [verified]
6. Three record shapes raise in that record walk: [verified: earlier revisions' reads; pr_cost.py:1089-1133 read this revision]
   - a truthy user `content` that is not iterable (routing_guard.py:990);
   - an `attachment` that is a truthy non-object, because `hook_denial_key` calls `.get` on it (`denials.py:80-81`);
   - a text block whose `text` is not a string, because `render._content_text` joins it (render.py:27-32).

   The same unguarded record walk already runs in three readers:
   - `review-trace` (review_trace.py:388, :450-453);
   - `friction-count` (friction_count.py:40, :53);
   - routing-guard's capture (routing_guard.py:978, :990-993).

   In `pr-cost`, which writes the cells the study reads:
   - A round-pass crash is caught (pr_cost.py:522-530).
   - The row is then built with an empty cell (:1093-1094, :1097-1100).
   - The guard refuses to replace a captured cell after that pass failed (:439, :458-463). Under an unforced re-record it runs because :1117 reads `overwrite_captured`.
   - A crash therefore never writes a wrong cell.
7. routing-guard's join counts a text denial only when its label is the routing gate's and its id joins a `Skill(code-review)` tool_use of the session (routing_guard.py:1024-1053). [verified]
8. routing-guard keeps counting a denied call as a round. [engineer-verified: "Keep the guard's definition (Recommended)"]
9. No `spawn_open` key and no ledger field. [engineer-verified: "Drop it (Recommended)"]
10. With an empty set the filter drops nothing, so routing-guard's windows, spans and `spawn_open` match today's. `_add_session_facts` makes no other round-detecting call, so `_CAPTURE_REVISION` stays 1. Two tests pin the retained definition and stay unedited: [verified: routing_guard.py:1092-1150; the test sites from an earlier revision's read]
    - `TestRowLines.test_the_captured_line_of_a_key_on_row_with_a_null_growth_loop_equals_a_literal` (test_transcript_routing_guard_capture.py:3256-3270);
    - `test_a_deny_already_counted_in_an_earlier_session_still_marks_this_sessions_denied_skill_open` (:1658-1670).
11. `_REVIEW_BENCH_SCRIPTS_DEPENDENCIES` (select-tests.py:134-145) lacks `denials.py`, and a ground-truth import walk checks it (:130-133). [verified]
12. `_COST_COUNTS_ROUNDS_CAPTION` (subagent_mix.py:482-487) is public PR-body text, pinned as a literal at test_transcript_cost_counts.py:288-293 and sampled at `docs/transcript-analysis.md:2017`. All three stay unedited (row 51). [verified: earlier revisions' reads]
13. Existing test lines that must change: [verified: the pr-cost, cost-counts and capture lines read; the seven review-rounds lines from an earlier revision's Grep]
    - the seven `round_opened_by_spawn` calls at test_transcript_review_rounds.py:2052, 2187, 2193, 2199, 2203, 2209 and 2210;
    - `_FOUR_ROUND_CELL`'s `"rule": 1` (test_transcript_pr_cost.py:2333);
    - the agreement test at test_transcript_routing_guard_capture.py:1630-1647, with its imports `review_trace` (:27) and `_hook_deny_current` (:84), which nothing else in that file uses.
14. `_GOLDEN_ROUND_PROJECTIONS_BY_RULE` holds only key 1 and is append-only (test_transcript_review_rounds.py:1615-1617). The test asserts its largest key equals `REVIEW_ROUND_RULE` (:1760), and every shape id has a hand-written skill sequence (:1748-1749). [verified]
15. Literal rule-1 cells that stay: test_transcript_pr_cost.py:2875, 2961 and 3506, `_pr_cost_helpers.py:563`, test_transcript_pr_cost_ledger.py:1583, 1589 and 1970, and the force-guard unit cases (test_transcript_pr_cost.py:3231-3343), which pass literal rules to a pure function. [verified: an earlier revision's reads; the unit cases' literals re-read by Grep in an earlier revision]
16. A `--record` write runs on the account's own scan (pr_cost.py:793-797) under a per-branch lock (:1040-1143). The account-level lock at :954-966 covers only the advisory read that the hint at :1029 uses. The guard (:1117-1131) compares only the rounds cell and allows any higher-rule re-record (:453-475). `force` decides the overwrite at :1029, :1056, :1117 and :1133. Without `--pr`, `target_branches` is `sorted(branch_totals)` (:976), so each name appears once. [verified: pr_cost.py:1020-1200 read this revision; the rest from an earlier revision's read]
17. `docs/pr-cost.md` documents plain `--force` as the re-record after an attribution change that moves the figures (:271, :356). Checking the figures under plain `--force` would refuse that re-record. [verified]
18. The fold adds no flag and no argument check, so the parser (pr_cost.py:1203-1272) and the checks at :753-770 stay unchanged, and no test needs to reach the parser. [verified: every site the fold touches sits in the branch loop at :1029-1133]
19. A row's `session_count`, `turn_count` and five `*_tokens` columns come from the branch aggregate (pr_cost.py:548-578). The aggregate tracks `last_activity_ts` as a float epoch from `corpus._parse_ts` (cost.py:117-123, corpus.py:233-240). `captured_at` is a second-truncated ISO string (pr_cost.py:1090). The ledger parser validates it with `datetime.fromisoformat` (pr_cost_ledger.py:417-426), so every parsed row's `captured_at` also parses through `corpus._parse_ts`. The int columns parse to `int` (:444-448). [verified: pr_cost.py:1090 read this revision; the rest from earlier revisions' reads and the round-5 backend review's]
20. Plain `--record` never overwrites a captured row today. The hint at pr_cost.py:1029 and the locked check at :1056 skip it, and a single-account `--pr` run exits 1 there. `docs/pr-cost.md:271` states the rule as "An unforced re-record of an already-captured `(host, repo, pr_number, machine)` refuses and names `--force`." [verified: read this revision]
21. Under `--all-accounts`, a `--force` guard refusal sets `force_refused` and `continue`s (pr_cost.py:1128-1131), and the run exits 1 after every branch (:1199-1200). A row written with a failed cell check also makes the run exit 1 at the end (:1109-1116, :1155-1175, :1199-1200). Every other `continue` leaves the exit at 0, as the ambiguous-join skip does (:1003-1009). A ledger parse failure (:1049-1051), an append or write error (:1134-1141) or the lock timeout (pr_cost_ledger.py:742-765) ends the run at once with exit 1. [verified: pr_cost.py:1020-1200 read this revision; :1003-1009 and the lock timeout from an earlier revision's read]
22. A failed enrichment writes a degraded `status` with zero-valued commit, review-comment and proxy columns, and the run exits 0 (pr_cost.py:988-1014, `docs/pr-cost.md:230`). [verified]
23. `_latest_pr_cost_row` returns the latest row by `captured_at` for one host, repository, PR and optional machine (pr_cost_ledger.py:558-598). `review-cost-by-size` keeps a PR only when exactly one cell-carrying current row exists across accounts, its join is not `low` and its rule is current (ledger_rounds.py:82-93), and it keys on the origin's host and repository (review_cost_by_size.py:298-299). [verified: earlier revisions' reads]
24. `--record` resolves the machine identity at pr_cost.py:938-942 and mints `<config-dir>/machine-id` when the file is absent (ledger_common.py:63-98, :146-172). `PR_COST_LEDGER_PATH` never redirects that file (`docs/pr-cost.md:528`). A rehearsal against an account with no `machine-id` would therefore write one into the real config directory. [verified: earlier revisions' reads]
25. Each ledger write is an atomic replace (pr_cost_ledger.py:687-739) under the per-branch lock (row 16). [verified: pr_cost_ledger.py:687-712 read this revision]
26. The pr-cost round fixtures `_ledger_rows`, `_arrange_round_run` and `_run_record` are local to test_transcript_pr_cost.py (:1715, :2352, :2369), and `_pr_cost_args` lists each flag explicitly (_pr_cost_helpers.py:276-302). The four-round corpus's turns carry fixed past timestamps (test_transcript_pr_cost.py:2315-2327). [verified: :2352 and :2369 read this revision; the rest from an earlier revision's read]
27. `test_an_allowed_forced_recapture_appends_a_superseding_row_and_exits_0` (test_transcript_pr_cost.py:3430-3446) forces over `_sample_pr_cost_row`, whose `input_tokens` of 300 differ from the four-round corpus's (_pr_cost_helpers.py:436-462, test_transcript_pr_cost.py:2332-2349). Unedited, it keeps pinning plain `--force`. [verified]
28. The re-record check runs inside pr-cost. [engineer-verified: "Check inside pr-cost (Recommended)"]
29. History, superseded by the fold (row 81): the plan was rewritten around the flag Context describes, which accepted a re-record only when the new figures equal the old row and the branch has no activity after capture, and a loop over the PRs with one current old-rule row. Extras the Ask does not call for were dropped. [unverified: the engineer's answer to the rewrite was "Yes", which does not state that extras are dropped; row 34 lists the extras the fold keeps]
30. The same re-record and one rule run on every machine, with no exceptions. [engineer-verified: "same script, same heuristic, no exceptions"]
31. The re-record takes no date, and the plan names none. [engineer-verified: "don't put any dates, please, in the plan, because it's based on number of PRs, not time"]
32. The routing-gate record changes at :62's GH-1131 sentence and its whole :63 bullet. [unverified: the engineer selected "Routing-gate record edits", which by itself does not cover rewriting the whole :63 bullet]
33. The routing-gate record's line 78 stays unedited and is named as an input to the study PR's plan. [engineer-verified: "Leave it, note for study PR (Recommended)"]
34. These choices go past the fold as Context describes it, each resting on a cited code row: [unverified: the plan's own reading and the advisors' advice as the session relayed it, not the engineer's words]
    - the status condition (row 22);
    - a skip, not a refusal, for every unforced non-write outcome, with the already-captured skip's exit (rows 21, 86, 99);
    - the `refusing to re-record` wording (row 67);
    - evaluating the predicate at the hint as well as under the lock (rows 83, 84).
35. The routing-gate record's line 80 stays unedited, because nothing this change does makes it false. [unverified: the plan's own reading]
36. On real transcripts, the branch's `review-round-cost` round total is at most the merge-base's on every account, and lower on a key-on account. [unverified: Verification 4 settles it]
37. Residual: an errored `Agent` result whose text names a shipped gate drops its round, an undercount. The caveat bullet states it. [unverified: no harness shape that returns one was found; the one `Agent|Task` PostToolUse hook in this repo's settings is the logger `log-reviewer-round.sh` (settings.json:621-629), per an earlier revision's read]
38. No repo fixture shows a non-`PreToolUse` `hook_blocking_error` attachment whose `toolUseID` joins a launched call. The `hookEvent` filter guards that case, and it errs toward counting the round, the pre-fix behavior. [unverified: no legacy transcript was read]
39. `ledger_rounds.py:91` excludes any cell whose `rule` differs from the current one, and a checkout with a lower rule cannot `--force` over a higher-rule row (pr_cost.py:464-465). [verified]
40. `TestDenialHookLabelEnumeration` requires each hook's deny wording to be a member of `_DENIAL_HOOK_LABELS` (denials.py:116-127). A new gate therefore ships with its label, and no earlier transcript reads differently. Removing or renaming an entry does change how earlier transcripts read. So does editing `_HOOK_DENIAL_SIGNATURE` (:40) or `_DENIAL_HOOK_NAME_PATTERNS` (:254), which decide the same reading. [verified: the two symbols located by Grep in an earlier revision; their role from rows 3 and 43]
41. The non-hook refusals are the `toolDenialKind` friction family: `user-rejected`, `automode-blocked`, `automode-unavailable` and `interrupted` (denials.py:342-385). [verified: an earlier revision's read]
42. Readers that count `Skill` calls rather than rounds include skill_invocation.py:136, judgment_pair.py:64, period_cost.py:221, review_trace.py:320 and subagent_mix.py:228. [verified: an earlier revision's Grep]
43. The signature's third alternative (`denials.py:43`) and the name patterns (`:98-114`) can backtrack on a long whitespace run. routing-guard's capture already runs the same matcher over every errored result of every session (routing_guard.py:989-996, :1033-1036), so this change adds no input shape. [verified: patterns and record walk read; the backtracking itself from the round-1 security review, not re-run]
44. The study PR changes neither detection nor pricing, so this is the only bump before it. [unverified: the study PR has no plan yet]
45. A denied spawn has no launch record, so `_price_dispatch` counts it in its round's `dangling` (review_rounds.py:347-354). The launch record is read per session path (`corpus._index_subagent_dispatches(jsonl)`), and `detect_round_windows` receives records only (review_rounds.py:197). [verified: earlier revisions' reads]
46. `author_outcome.py` is 993 lines, under the 1,000-line limit, and nothing enforces the limit yet (`docs/design-decisions/code-file-line-limit.md:50-57`). `pr_cost.py` is already past it, since its subparser ends at :1272. Each test goes in the file named for its subject (`.claude/rules/transcript-analysis-tests.md`). [verified: earlier revisions' reads]
47. The `Projected diff:` figure is the plan's own bottom-up estimate, not a count, and Critical files states it in one place. [unverified]
48. The engineer runs no per-PR command by hand. [engineer-verified: "the expectation should NOT be that I manually run the commands"]
49. The engineer cannot judge PRs one at a time. [engineer-verified: "I will NOT be able to judge each partly aged PR"]
50. The additions the Ask does not call for go to an architect for adversarial review. [engineer-verified: "Have the architect adversarially review those additions"]
51. That review: [unverified: the session's relay of the consult, not the engineer's words]
    - cut the record walk's crash guards, the caption sentence and three `docs/transcript-analysis.md` edits;
    - shrank the caveat bullet;
    - kept the degraded-status refusal and the no-prior-row skip.
52. Real transcripts do not produce the three shapes row 6 lists. [unverified: the consult's inference; no corpus was read]
53. The engineer chose to proceed at the size Context's size selection names. [engineer-verified: "Proceed anyway"]
54. A window ends at the next round-open or fresh user prompt (review_rounds.py:220-236). Every spawn block in a window's records is priced, and one with no `dispatch_index` entry or no readable transcript counts in `dangling` (:340-358, :451-467). Dropping a denied round-open merges its window into the one before it, or into none. With the same files, a session's summed `dangling` therefore cannot rise. A window's records take its opening record's branch (:252-271), so a merged window spanning a branch change can raise one branch's sum. A lost meta sidecar with a surviving transcript misses `dispatch_index` and raises `dangling` while the seven figures stay equal. [verified: review_rounds.py:197-471 from an earlier revision's read; that `dispatch_index` reads the meta sidecars from the round-3 backend review's read of corpus.py:21-81]
55. A branch matches every merged PR with its name (pr_cost.py:983). With more than one match, `_resolve_branch_pr` picks by SHA overlap, then `mergedAt`, and grades the join `low` (:196-204). `already` and the new row key on the resolved PR (:1053-1055, :1101-1108). Another PR's row under the same branch name is therefore never `already`. [verified: :1053-1108 read this revision; :196-204 and :983 from an earlier revision's read]
56. The PR refers to GH-1131 without closing it, because the invocation counters still count a denied call (row 42). The routing-gate record's :62 keeps a clause saying so. [unverified: the round-3 consult's advice as the session relayed it, not the engineer's words]
57. pr-cost lists at most the 1,000 most recent merged PRs (gh_cli.py:56, :459), and a branch with no merged match is skipped before the hint (pr_cost.py:983-986). [verified: earlier revisions' reads]
58. The planned review-bench miner test is cut. [engineer-verified: "Cut it (Recommended)"]
59. A branch with no surviving activity builds no cell (pr_cost.py:1091-1092, :1097-1100), and the guard refuses an empty cell over a captured one (:456-463). [verified]
60. Option A, the walk mode, replaced the driving script, and the fold later replaced the walk (row 81). [unverified: the engineer wrote "I think option A is good because it's simpler, but just to be safe, can you get Fable's take?" and, after both advisors advised it, "go"]
61. Option A's description is the session's wording, which the engineer selected and then answered with "go". It describes a `--record` mode with no `--pr` that walks each account's below-rule rows inside `pr-cost` and re-records a row only when the unchanged-figures check passes. [unverified: an option description the session wrote, not the engineer's words]
62. Row 30's "same script" now reads as plain `pr-cost --record`, the command every machine already runs, with that machine's own flags. [unverified: the session's reading of the quote once the script and the walk were dropped]
63. The architect consult and Fable both advised the fold, and their description shaped the predicate, its call sites and the skip rule. Rows 16, 21, 66, 83, 85 and 91 verify the code each claim rests on, and row 84 corrects one. [unverified: the session's relay of two advisors' claims, not the engineer's words]
64. The plan states no figure for how many rows the fold re-records, which depends on how many transcripts survive. [unverified: the plan cites no measurement, under Context's publication limit]
65. The figures come from `_resolve_project_scope` over the run's own `--projects` or `--this-repo` (pr_cost.py:793-797, scope.py:509-520). A run whose scope differs from the original capture's can therefore give other figures, and the predicate then skips the row. [verified: earlier revisions' reads]
66. `_review_rounds_force_refusal` refuses any empty new cell over a captured one (pr_cost.py:456-463). The breakdown check runs before the guard. On failure it empties `model_breakdown` and keeps the error in `failed_breakdown_check` (:1111-1116), and the error carries `rule` and `cause` (:281-284). The guard site can therefore read both cells' outcomes before any write. [verified: pr_cost.py:281-284 and :1111-1131 read this revision; :456-463 from an earlier revision's read]
67. The guard's refusal line names `--force` (pr_cost.py:1122-1127). `docs/pr-cost.md:293` shows that line, and :296 states its exits. [verified: read this revision]
68. The `recorded PR #N` line prints to stdout (pr_cost.py:1146). The per-PR lines, the guard's refusal line and the failed-cells footer print to stderr (:1122-1127, :1157-1170, :1192-1198). [verified: read this revision]
69. The latest row is chosen by `captured_at` string order, with the last appended row winning a tie (pr_cost_ledger.py:581-582). `_collapse_pr_cost_rows_to_current` applies that per (host, repo, PR, machine) key (:585-598). A new row whose `captured_at` sorts before its prior row's therefore never becomes current. [verified: an earlier revision's read]
70. Without `--pr`, `target_branches` is `sorted(branch_totals)` (pr_cost.py:976), so a branch with no surviving activity is never visited. With `--pr`, such a branch reaches the loop with no `branch_totals` entry (:974, :1089). [verified: :1089 read this revision; :974-976 from an earlier revision's read]
71. The enrichment `gh pr view` calls run for every matched PR at pr_cost.py:990-1000, before the already-captured hint at :1029, so the fold adds no `gh` call. [verified: an earlier revision's read]
72. The new cases reuse these test helpers: `_assume_hand_computed_dollar_rates` (test_transcript_pr_cost.py:1117), `_fail_check_on_calls` (:1679-1692), `_fail_the_pass` (:2746), `_spy_on_scans` (_pr_cost_helpers.py:706), `_write_ledger_row_on_lock_acquire` (:724), `_fake_pr_cost_subprocess_run`'s `gh_pr_view_failure_stderr` (:312-327), `_FORCE_REFUSAL_STEM`, `_force_refusal_line` and `_already_captured_line` (_pr_cost_helpers.py:175, :202-213), and `ledger_rounds.select_ledger_prs` (ledger_rounds.py:107). `_routing_deny_record` takes a tool_use id and either shape (_routing_guard_helpers.py:38-58). [verified: the pr-cost helpers read this revision; `_assume_hand_computed_dollar_rates`, `select_ledger_prs` and `_routing_deny_record` from an earlier revision's read]
73. `PR_COST_LEDGER_PATH` is refused only under `--all-accounts` across more than one resolved root (pr_cost.py:731-741), so a single-account run can write to a copy. [verified: an earlier revision's read]
74. `hook_denials_in_record` yields `(tool_use_id, hook_name, message)`, and `hook_name` is empty both for a tool_result and for an attachment with no `hookName` (routing_guard.py:975-996). A legacy record keeps `hookName` and `toolUseID` under `attachment` (conftest.py:1425-1434), and the repo's real-shape fixtures keep `hookEvent` there too. [verified: conftest.py read this revision; the yielded tuple from the round-5 backend review's read; `hookEvent`'s placement from the round-6 testing review's read, not re-read]
75. The session's round 5 disposition is accepted. [engineer-verified: "go"]
76. That disposition, in the session's wording, takes the round 5 findings its verdict lists, declines the ones it names, and relabels rows 29, 60 and 32 as unverified with their quotes beside them. [unverified: the session's proposal, not the engineer's words]
77. A pre-merge rehearsal runs. [engineer-verified: "sure, pre-merge rehearsral is fine."]
78. Each engineer-run step is scripted. [engineer-verified: "you gotta minimize what I run manually though. please script as much as possible."]
79. Each engineer-run step is one command. Its script lives in the engineer's local probes directory, outside the PR, and prints only exit statuses, booleans and line counts. [unverified: the session's dispatch, not the engineer's words]
80. `REVIEW_ROUND_RULE`'s comment requires a bump with any change to which records open a round (review_rounds.py:46-50). [verified: an earlier revision's read]
81. The fold replaces the walk. [engineer-verified: "I accept that, \"fold\""]
82. The fold, in the session's wording that the engineer accepted, puts the unchanged-figures check into plain `--record`'s already-captured skip, with no new flag or mode, and reverses the documented rule that an unforced re-record of a captured PR refuses. [unverified: Context's agent wording, not the engineer's words]
83. Every predicate input exists before the hint: `branch_totals` from the scalar scan (pr_cost.py:797), the advisory rows (:958) and `row_status` (:1011-1014). The round scan runs only after the hint (:1036-1038). [verified: :1036-1038 read this revision; the rest from an earlier revision's read]
84. The advisors described one `overwrite_captured` value read at :1029, :1056, :1117 and :1133. The hint reads the advisory `existing_rows`, and the locked check reads `current_rows` (pr_cost.py:1029-1031, :1053-1055). One predicate is therefore evaluated at each, and the locked value feeds :1117 and :1133. [verified: read this revision; the advisors' claim is the session's relay]
85. With a captured cell below the current rule, `_review_rounds_force_refusal` refuses only an empty new cell (pr_cost.py:456-468). `_build_review_rounds_cell` always returns a cell (:345-354), so the empty cell comes from a failed pass, a failed check or a build error (:422-435, :1091-1100). The `no local transcript activity` reason cannot arise, because the predicate requires an `agg`. [verified: :1091-1100 read this revision; the rest from an earlier revision's read]
86. Plain `--record` runs on a schedule on some machines, and its exit 1 tells the caller that rows need attention (`docs/pr-cost.md:155`, :173). [verified: an earlier revision's read]
87. No existing already-captured assertion flips: [verified: the seeds read and the rule-1 seeds located by Grep in an earlier revision; :2711-2743 re-read this revision]
    - test_transcript_pr_cost.py:1885 and test_transcript_pr_cost_gh.py:728 seed through a real `--record`, so the row is at the current rule;
    - test_transcript_pr_cost.py:2527, :2725 and test_transcript_pr_cost_gh.py:762 seed `_sample_pr_cost_row`, whose `review_rounds` defaults to `None` (_pr_cost_helpers.py:458);
    - test_transcript_pr_cost.py:2205 seeds rows under headers that predate the `review_rounds` column (_pr_cost_helpers.py:524-541);
    - the rule-1 cells seeded before a `--record` run sit under a PR that run never visits (test_transcript_pr_cost.py:3090) or run with `--force` (:3109).
88. The changed contract's consumers: [verified: docs/pr-cost.md:250-305 and docs/transcript-analysis.md:1194-1205 read this revision; :155-:189 and :531 from an earlier revision's read]
    - `docs/pr-cost.md:255`, :271, :275, :296 and :442 change.
    - :155 and :157 stay true, because an unforced re-record either writes a row whose every cell passes or skips, so the fold adds no exit-1 cause beyond today's single-account `--pr` skip.
    - :173 and :189 stay true, because a row recorded during a failed pass carries no cell.
    - :531 stays true, because a second machine's transcripts do not reproduce the first's figures.
    - `docs/transcript-analysis.md:1199` gains "for a row this run recorded", because a run whose pass failed can now record nothing and exit 0. The rest of :1197-1205 stays true.
    - `_print_already_captured` (pr_cost.py:661-666), its callers at :1032 and :1057, and `_already_captured_line` (_pr_cost_helpers.py:209-213) stay unedited (row 96).
89. `_append_pr_cost_ledger_row` raises only when `already` exists and its flag is false (pr_cost_ledger.py:613-617). pr-cost passes `overwrite_captured` after the locked check has already skipped that case, so the error stays unreachable from pr-cost. Its only other callers are its own tests (test_transcript_pr_cost_ledger.py:57-77). [verified: an earlier revision's Grep]
90. `review-cost-by-size` prints one count per exclusion reason (review_cost_by_size.py:240-241), and `EXCLUDED_RULE` covers a cell whose `rule` differs from the current one (ledger_rounds.py:19, :91-92). [verified: an earlier revision's read]
91. A built cell carries `REVIEW_ROUND_RULE` (pr_cost.py:349), so a re-recorded row fails the predicate on every later run. [verified: an earlier revision's read]
92. Residual, `dangling`: a meta sidecar lost while its transcript survives raises the new cell's `dangling` and lowers that round's priced agent cost, while the seven figures stay equal (row 54). Round opens come from main-thread blocks (row 1), so the round count the fix corrects does not move. The new cell stores each round's `dangling` (pr_cost.py:333), and the append-only ledger keeps the superseded row (pr_cost_ledger.py:601-618). [verified: the mechanism; unverified: how often cleanup separates a sidecar from its transcript]
93. Residual, scan gap: the scalar scan (pr_cost.py:797) and the round scan (:1038) read the transcripts separately, so a transcript lost between them can shrink a re-recorded cell while the predicate holds. [verified: the two reads; unverified: how often cleanup runs between them]
94. Residual, clock: `captured_at` is the wall clock at write time (pr_cost.py:1090). On a machine whose clock reads earlier than a captured row's `captured_at`, the re-recorded row never becomes current (row 69), so each later `--record` appends another until the clock passes it. [verified: the mechanism]
95. The rehearsal runs on a copy of one account's ledger. [unverified: the session's design, resting on rows 24 and 73, not the engineer's words]
96. Round 6 pick, as the session's relay put it: the already-captured line stays unedited, and only docs wording addresses it. [engineer-verified: "Agreed"]
97. Round 6 pick, as the relay put it: a persistent refusal keeps exit 0, with no new summary line. [engineer-verified: "Agreed"]
98. Round 6 pick, as the relay put it: the nine beyond-the-Ask items the round-6 product review lists are accepted as stated. [engineer-verified: "Agreed"]
99. Round 6 rule, as the relay put it: an unforced re-record either writes a row whose every cell passes, or skips and needs no command, because the next plain `--record` retries it; a run without `--pr` exits 0, and a single-account `--pr` run exits 1 as before (the refusal cases under Tests). Any failed breakdown check on an unforced re-record is therefore a skip. [engineer-verified: "Agreed"]
100. Rows 96 to 99 word the relay in the session's terms, and the relay's list of round 6 findings taken and declined is the session's too. [unverified: the session's relay of the architect's consult, not the engineer's words]
101. `pr-cost` is a member of `_SUBCOMMANDS_REFUSING_TOP_LEVEL_CONFIG_DIR` (scope.py:702-708), and `main()` refuses a top-level `--config-dir` for each member (cli.py:177-185). [verified: read this revision; the exit status 2 from the round-6 platform review's read of cli.py:171-196]
102. Setting `CLAUDE_CONFIG_DIR` and `TRANSCRIPT_CONFIG_DIRS_FILE` together replaces the resolved root set (`docs/transcript-analysis.md:109`), so an empty roots file leaves only the one account's root. [unverified: the doc states it and no run confirmed it; Verification 5's `not rehearsed` line reports a run that exits 2]
103. `_write_ledger_row_on_lock_acquire` writes `[row]` alone (_pr_cost_helpers.py:724-737), and `_write_pr_cost_ledger_file` refuses a rewrite that drops or changes a prior row (pr_cost_ledger.py:648-668, :708). Its two callers write over no prior row (test_transcript_pr_cost.py:2728-2743, test_transcript_pr_cost_gh.py:752-763), so appending to the current rows changes neither. [verified: read this revision; "no prior row" inferred from each caller's single-row assertion]
104. A loader-free test file that imports `transcript_analysis` must be in `TEST_FILES` (test_transcript_package_module_prefixes.py:62, :527-538). Each listed file needs a `<module>.<name>` read the attribute check sees (:476-481), and none may hold a `from transcript_analysis.<m> import` line (:460-471). [verified: the test names and docstrings located by Grep this revision]
105. At routing_guard.py:1099 the local `denied_tool_use_ids` holds the routing-deny set, read again at :1148, one line above the `round_opened_by_spawn` call at :1149 that takes the new keyword. [verified: read this revision]
106. `docs/transcript-analysis-architecture.md` lists `review_rounds.py`'s imports without `denials` (:249-250) and names `turn_shape.py` and `friction_count.py` as `denials.py`'s readers (:325-326). `routing_guard.py` already imports `denials` (routing_guard.py:45-55), and its section says so (:770). [verified: read this revision]
107. An auth-shaped `gh pr view` failure writes a degraded-network status with no retry (test_transcript_pr_cost_gh.py:75-105). [verified: read this revision]
108. `opus_dollars`, `opus_dollar_share_pct`, `sum_context_at_turn`, `mean_context_at_turn` and `model_breakdown` come from the same agg the predicate reads (pr_cost.py:579-589). [verified: located by Grep this revision]
109. `pr_cost_ledger._write_pr_cost_ledger_file` refuses to change a row already on disk, so a seed step cannot rewrite one in place (pr_cost_ledger.py:648-668, :708-729; test_transcript_pr_cost_ledger.py:1153-1164 pins it). [unverified: three round 7 reviewers read it; this session did not]
110. The integration corpus's cache token columns are 0, and every planned rule case is relative to `REVIEW_ROUND_RULE`, so a swapped cache-column mapping or a hardcoded rule value passes them; the pure table's distinct token values and the patched-constant case guard both. [unverified: round 7 sdet traced it from reads]
111. The `_pr_cost_report` docstring (pr_cost.py:693-707) says a failed-cell re-record is still written. [unverified: round 7 backend read it]
112. An empty `PR_COST_LEDGER_PATH` counts as unset (pr_cost_ledger.py:139-145), and the merge-base worktree needs an EXIT trap to be removed after a failed run. Neither script is tracked, so no gate reads them. [unverified: round 7 platform read it]

## Critical files

One `code-writer` dispatch. The fold's tests seed cells one rule below `REVIEW_ROUND_RULE` and expect rows at it, and `test_transcript_pr_cost.py` and the CHANGELOG each hold both halves of the change. No split therefore leaves two dispatches that each stand without the other's context.

**Production.**
- `claude/.claude/scripts/transcript_analysis/denials.py`: adds `hook_denials_in_record` (moved unchanged) and `hook_denied_tool_use_ids`, and the one-line comment at `_DENIAL_HOOK_LABELS`.
- `claude/.claude/scripts/transcript_analysis/routing_guard.py`: deletes `_hook_denials_in_record`, calls `denials.hook_denials_in_record` at :1036, passes the commented empty-set constant at the three calls, and renames the local at :1099 and :1148 to `routing_denied_ids` (row 105).
- `claude/.claude/scripts/transcript_analysis/review_rounds.py`: the block filter, the three signatures and their docstrings, `REVIEW_ROUND_RULE = 2` and its comment, and `denials` in the module docstring's import list.
- `claude/.claude/scripts/transcript_analysis/author_outcome.py`: the `_code_review_rounds` keyword. Net growth is at most 2 lines, so it stays at or under 1,000 (row 46).
- `claude/.claude/scripts/transcript_analysis/pr_cost.py`:
  - `_reproduces_older_rule_row` beside `_review_rounds_force_refusal`, with a one-line docstring pointing at `docs/pr-cost.md` § "The re-record contract";
  - the hint at :1029 and the locked check at :1056 call it, and `overwrite_captured` replaces `force` at :1117 and :1133;
  - at the guard site, when `force` is false and the rounds guard allows the row, a failed breakdown check sets the refusal reason `the per-model breakdown failed its <rule> check` (row 66);
  - the guard's line reads `refusing to re-record (<reason>)` when `force` is false, and only `force` sets `force_refused` (:1117-1131);
  - the `_pr_cost_report` docstring (:693-707) no longer says a failed-cell re-record "is still written" without `--force` (row 111);
  - it reuses `corpus._parse_ts`, `review_rounds.REVIEW_ROUND_RULE` and `pr_cost_ledger._PR_COST_STATUS_OK`.
- `evals/review_bench/mine_review_rounds.py`: imports `denials` and passes the set to both calls.
- `claude/.claude/scripts/select-tests.py`: `denials.py` joins `_REVIEW_BENCH_SCRIPTS_DEPENDENCIES`.

**Tests.** Each bullet names what it proves.
- New `claude/.claude/scripts/tests/test_transcript_denials_tool_use_ids.py`, a named seam beside the over-limit `test_transcript_denials.py` (row 46). Each case asserts the exact returned id set. `_hook_deny` keeps `hookName` and `toolUseID` under `rec["attachment"]` and derives the id from the hook name (row 74), so a case that needs a specific id or `attachment.hookEvent` edits `rec["attachment"]`.
  - The agreement test, moved from the capture file and calling `denials.hook_denials_in_record`, with inline values for that file's local `_ts` and `_BRANCH`. Proves the moved record walk still yields what `review-trace` reads as denials.
  - Collected, one case each. Proves both shapes count, for every shipped gate, with shape and `attachment.hookEvent` read from the record (row 74).
    - a routing-gate result denial (`_routing_deny_record`);
    - a legacy attachment whose `hookName` is unlisted and that has no `hookEvent` (`_hook_deny`);
    - a legacy attachment whose `rec["attachment"]` carries `hookEvent: "PreToolUse"`;
    - a legacy attachment with no `hookName`, a usable `toolUseID`, and text naming no shipped gate;
    - a result carrying another shipped gate's wording, bound to its label.
  - Left out, one case each, each returning `frozenset()`. Proves an ordinary error, and a denial with no usable id, keep their round.
    - an `is_error` result with no denial text;
    - a result whose idiom names only a hook this repository does not ship;
    - a sidechain record's denial;
    - a legacy attachment whose `rec["attachment"]["hookEvent"]` names another event;
    - a legacy attachment with an empty `toolUseID`;
    - a legacy attachment with no `toolUseID`;
    - a non-error result whose text quotes a shipped gate's wording.
- `claude/.claude/scripts/tests/test_transcript_package_module_prefixes.py`: `TEST_FILES` gains the new file. The new file binds `denials` and `review_trace` through an unaliased `from transcript_analysis import ...`, reads them as `<module>.<name>`, and holds no `from transcript_analysis.<m> import` line (row 104).
- `claude/.claude/scripts/tests/test_transcript_routing_guard_capture.py`: only the agreement test and the two import names leave (row 13). The two tests row 10 names stay unedited.
- `claude/.claude/scripts/tests/test_transcript_review_rounds.py`, home of the shape registry and the golden table:
  - The seven calls gain `denied_tool_use_ids=frozenset()`.
  - Shape `denied_calls_inside_an_open_round`, registered in `_ROUND_SHAPE_CORPUS_BUILDERS` and `_EXPECTED_SKILLS_BY_SHAPE`. Each turn carries distinct input token counts. Proves through pricing that a denied call of either shape neither opens nor ends a round, and that a denied spawn counts in `dangling` (row 45).
    - An inline `Skill(code-review)` round opens.
    - Inside its window come a `review-orchestrator` spawn denied through `_routing_deny_record(<spawn id>, shape="legacy")` and a `Skill(code-review)` denied through `shape="current"`.
    - A launched `review-orchestrator` spawn then opens the second round.
    - The first round's projection holds both denied turns and `dangling == 1`.
  - `_GOLDEN_ROUND_PROJECTIONS_BY_RULE[2]` is assigned in the class body after the literal, as rule 1's projections plus the new shape's hand-derived projection, so rule 1's block stays unedited (row 14).
  - A record holding a denied `Skill(code-review)` and an undenied orchestrator spawn opens one round, by the spawn. `round_opened_by_spawn` returns True with the set and False with `frozenset()`. Proves the per-block filter and the keyword.
  - The new shape's records under `denied_tool_use_ids=frozenset()` open one round per call, as today. Proves the empty-set path routing-guard relies on.
- `claude/.claude/scripts/tests/test_author_outcome.py`: `_code_review_rounds` over a denied `Skill(code-review)` then a launched spawn returns only the spawn's span by default, and both spans with `denied_tool_use_ids=frozenset()`. Proves the passthrough keeps `None` as its default.
- `claude/.claude/scripts/tests/test_transcript_pr_cost.py`:
  - `_FOUR_ROUND_CELL`'s rule reads `review_rounds.REVIEW_ROUND_RULE`.
  - A table test of `_reproduces_older_rule_row` beside the force-guard unit cases (:3231-3343). Its base is a `_sample_pr_cost_row` with a cell one rule below `REVIEW_ROUND_RULE`, and an agg from `cost._new_pr_cost_agg()` with matching `sessions` and `turn_count`, and a distinct nonzero value in each of the five token columns, because the integration corpus leaves the cache columns at 0 (row 110), and a `last_activity_ts` equal to the parsed `captured_at`. Proves each condition and each ignored column.
    - the base holds;
    - each of the seven figures, one lower and one higher, fails (parametrized);
    - a `None` prior row, a `None` agg and a `None` cell each fail;
    - a cell at `REVIEW_ROUND_RULE` and one above it each fail, and with `REVIEW_ROUND_RULE` patched to its value plus one, a cell at the old value holds (row 110);
    - `last_activity_ts` one second after `captured_at` fails;
    - a prior `ok` row with either degraded fresh status fails, and a degraded prior row with `ok` or either degraded fresh status holds;
    - the base still holds with these columns changed: every dollar column, `opus_dollars`, `opus_dollar_share_pct`, `sum_context_at_turn`, `mean_context_at_turn`, `model_breakdown`, `rate_stamp`, `unpriced_turns`, `unpriced_tokens`, `invalid_usage_records` and every enrichment column (row 108).
  - A new class beside `TestReviewRoundsForceGuardIntegration` (:3346), whose fixtures are local to this file (row 26), runs through the real writer.
    - Each case seeds the four-round corpus through `_arrange_round_run` and a plain `_run_record`. It then rewrites the seeded row's cell to `_FOUR_ROUND_CELL`'s rounds plus one extra `code-review` round, under rule `REVIEW_ROUND_RULE - 1`. The writer refuses to change a row already on disk (pr_cost_ledger.py:648-668, :708-729), so the seed step unlinks the ledger file and writes the rewritten row through `pr_cost_ledger._write_pr_cost_ledger_file` into the empty path (row 109).
    - A case that compares with `_FOUR_ROUND_CELL` carries `@pytest.mark.usefixtures("_assume_hand_computed_dollar_rates")`.

    The cases:
    - Accept, then re-run, parametrized over no flags and `pr=1`. The seed's `rate_stamp` and `cache_read_usd` are also rewritten. Before the run, `ledger_rounds.select_ledger_prs` excludes the PR under `EXCLUDED_RULE`. `_run_record` returns without `SystemExit` and appends one row whose `supersedes` is the seed's `captured_at` and whose cell equals `_FOUR_ROUND_CELL`. `select_ledger_prs` then lists the PR with every exclusion count 0. A second plain `_run_record` prints `_already_captured_line(1)`, returns, and leaves the ledger's bytes unchanged. Proves the ignored columns, the unforced write path, the `--pr` accept's exit 0 and a re-run that changes nothing.
    - Figure mismatch. With the seed's `turn_count` raised by one, a plain `_run_record` prints `_already_captured_line(1)`, returns, and leaves the bytes unchanged, and `_spy_on_scans` records no round scan. Proves the predicate decides at the hint, before the scan.
    - Status at the hint. After seeding, `subprocess.run` is re-faked with `gh_pr_view_failure_stderr` set to the auth-shaped text (row 107), so the fresh status is degraded over the seed's `ok`. A plain `_run_record` prints `_already_captured_line(1)`, returns, leaves the bytes unchanged, and `_spy_on_scans` records no round scan. Proves the hint passes the resolved PR's `row_status`.
    - Locked row differs from the hint's. After seeding, `_write_ledger_row_on_lock_acquire` appends a copy of the seed whose cell's `rule` is `REVIEW_ROUND_RULE`. A plain `_run_record` prints `_already_captured_line(1)` and returns. The ledger then holds only the seed and that copy, and `_spy_on_scans` records one round scan. Proves the locked row, not the hint's value, decides the write.
    - Refusal, parametrized. Each case applies its failure after seeding and leaves the bytes unchanged.
      - `_fail_the_pass`, no flags: prints the unforced refusal line with `_REASON_PASS_FAILED` and returns without `SystemExit`.
      - `_fail_the_pass`, `pr=1`: prints the same line and exits 1.
      - `_fail_the_pass`, `pr=1, force=True`: prints `_force_refusal_line` with the same reason and exits 1.
      - `_fail_check_on_calls(monkeypatch, {1})`, no flags: prints the unforced refusal line with `the per-model breakdown failed its dollars check`, prints no failed-cells footer, and returns without `SystemExit`.

      Proves the unforced skip for both cells, its single-account `--pr` exit, and that plain `--force` keeps its exit 1.
  - No two-root `--all-accounts` case. The predicate's inputs are the per-account loop's own locals (pr_cost.py:789-797, :954-966), and the unforced skip under `--all-accounts` takes the same `continue` the no-flag case proves.
  - The forced test row 27 names and the assertions row 87 names stay unedited. The projected diff allows up to 30 lines in case one flips anyway.
- `claude/.claude/scripts/tests/_pr_cost_helpers.py`:
  - `_UNFORCED_REFUSAL_STEM` and `_unforced_refusal_line(pr_number, machine, reason)` beside `_FORCE_REFUSAL_STEM` (:175) and `_force_refusal_line` (:202-203).
  - `_write_ledger_row_on_lock_acquire` appends its row to the rows `pr_cost_ledger._read_prior_pr_cost_ledger` returns, instead of writing it alone, so a seeded ledger keeps its prior rows (row 103).

**Docs.**
- `docs/transcript-analysis.md`:
  - The caveat bullet under "Round detection caveats" (:1265-1276), the rule's one home. It states:
    - the two denial shapes;
    - in the current shape, a denial by a hook this repository does not ship still opens a round, while a legacy attachment from any hook does not;
    - `routing-guard` alone still counts a denied call as a round;
    - an errored `Agent` result naming a shipped gate loses its round, an undercount (row 37).
  - :1270 gains one clause: a dispatch one of this repository's gates denied is not a round, pointing at the new bullet.
  - :1696, :1717 and :2007 add that a dispatch one of this repository's gates denied is not a round, pointing at the caveat, because both otherwise count every never-run dispatch.
  - :1199 reads "the review-round pass or a cell's write-time check failed for a row this run recorded;" (row 88).
- `docs/transcript-analysis-architecture.md` (row 106):
  - `review_rounds.py`'s import list (:249-250) gains `denials`.
  - `denials.py`'s readers (:325-326) gain `review_rounds.py`, reading `hook_denied_tool_use_ids`, and `routing_guard.py`, reading `hook_denials_in_record`.
- `docs/pr-cost.md`:
  - :271's first sentence gains "unless the row meets the exception in the next paragraph".
  - A new paragraph after :271, the exception's one home, in three sentences:
    - An unforced `--record` re-records a captured row whose `review_rounds` cell is below the current round `rule` when all three of its conditions hold, given as a list: this run reproduces the row's `session_count`, `turn_count` and five `*_tokens` values; the branch has no activity after the row's `captured_at`; and the enrichment status is `ok` or the row's status was already degraded.
    - "A row the exception skips, or refuses because a cell of the new row failed, needs no command: the next plain `--record` retries it, and a run without `--pr` exits 0."
    - "Forcing a row the exception leaves below the rule is the aged-transcript judgment the paragraph above warns about."
  - :255's last sentence gains "unless a captured row meets the re-record exception in "The re-record contract"".
  - :275 reads "Every `--force` re-capture, and every re-record under the exception above, per PR:".
  - :296 gains two sentences. Without `--force`, a re-record under the exception prints `refusing to re-record (<reason>)` in place of the line above, where `<reason>` can also be a failed per-model breakdown check, and skips the PR as an already-captured one is. The `--force --pr N` steps in the reason bullets below apply only under `--force`.
  - :442's causes gain "a re-record after a review-round rule change", and "four" becomes "five".
- `docs/design-decisions/review-orchestrator-routing-gate.md`, lines :62-63 only (row 32):
  - In :62, the GH-1131 sentence becomes "Round detection treats a gate-denied block as no round, except in `routing-guard`. The invocation counters still count a gate-denied `Skill(code-review)` call, and GH-1131 tracks them." (row 56)
  - :63 becomes "A denied `Skill` call still leaves its `tool_use` block in the transcript. Round detection drops that block everywhere except `routing-guard`, whose overhead definition below counts it."
- `CHANGELOG.md`, under `### Fixed` (:910), one bullet, `**A call one of this repository's gates denied no longer counts as a review round.**`, with nested bullets:
  - `**Cause:**` detection read a call's `tool_use` block and never whether a hook denied it, so a routing-gate denial of `Skill(code-review)` and the `review-orchestrator` dispatch after it counted as two rounds.
  - `**Affected:**` `review-round-cost`, `cost-counts` and the PR-body "Review rounds" table, `author-outcome`, `review-trace`'s round labels, `pr-cost`'s `review_rounds` cell and the review-bench miner. `routing-guard` still counts the denied call, and readers that count calls rather than rounds still count it.
  - `**Migration:**` Until the next `--record`, `review-cost-by-size` excludes every row recorded before this change. That run re-records each row whose surviving transcripts reproduce its figures (see `docs/pr-cost.md` § "The re-record contract"), and `review-cost-by-size` excludes the rest.
  - `**Re-runs:**` a re-run over the same transcripts can give different figures than one made before this fix, following the convention at :927, :928 and :938.

Verify: `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py` and the ruff command in Verification.

Projected diff: about 710 to 760 changed lines, an estimate in a range of about 660 to 790 (row 47). About 190 are production, about 490 tests and about 65 docs. The range includes up to 30 lines for an existing test the fold flips, though row 87 expects none. The Verification scripts live outside the PR and are not counted.

## Verification

1. `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py` passes. It may widen itself because `select-tests.py` changed, and that is its decision.
2. `scripts/venv-run.sh ruff check claude/.claude/ claude-skills/ plugins/ evals/` is clean.
3. Diff checks against the merge-base, run by the session:
   - `test_transcript_review_rounds.py` deletes lines only at the seven `round_opened_by_spawn` calls, and none inside rule 1's projections.
   - `test_transcript_routing_guard_capture.py` loses only the agreement test and the `review_trace` and `_hook_deny_current` import names.
   - The forced test row 27 names, `_print_already_captured`, `_already_captured_line` and the assertions row 87 names are unedited.
   - `wc -l` shows `author_outcome.py` at 1,000 lines or fewer.

Steps 4 and 5 are the engineer's, and each is one command (rows 78, 79). For each one, the session writes a script into the engineer's local probes directory, `<probes-dir>` below, which sits outside this PR and every git tree. Neither script is committed, and neither is listed in Critical files. Each prints only exit statuses, booleans and line counts, never a PR number, a branch, or a per-account cost or round figure. Everything else a script's runs print goes to files under `<probes-dir>`.

4. Real-transcript check (row 36): `bash <probes-dir>/round-totals-check.sh <key-off config dir> <key-on config dir>`, run while no Claude Code session is working. The script:
   - adds a worktree at the merge-base under `<probes-dir>`, and removes it with `git worktree remove` from an EXIT trap, so a failed run leaves none registered (row 112);
   - for each account, runs `python3 claude/.claude/scripts/transcript-analysis.py --config-dir <account> review-round-cost --this-repo` from the merge-base worktree's root, then from this branch's worktree root, then from the merge-base worktree's root again, back to back, because `--this-repo` reads `git worktree list`;
   - prints each run's exit status and three booleans: `stable`, that each account's two merge-base `Totals:` round counts match; on each account the branch's count is no higher than the merge-base's; and on the key-on account it is lower.

   A `no` on `stable` means rerun the step. Investigate any other `no` before merge.
5. Pre-merge rehearsal (rows 24, 73, 77, 95): `bash <probes-dir>/record-rehearsal.sh <config dir> <the flags that account passes to --record, less --all-accounts>`. It covers one account, because `--all-accounts` across more than one root refuses `PR_COST_LEDGER_PATH`. The script:
   - stops before any run when `<config dir>/machine-id` is absent, so the rehearsal never mints an identity;
   - stops before any run unless the copy's path is non-empty and absolute and the copy is byte-equal to its source, because an empty `PR_COST_LEDGER_PATH` counts as unset and would send the runs to the real ledger (row 112);
   - copies that account's ledger, keeping its mode, into a new directory under `<probes-dir>`, and sets `PR_COST_LEDGER_PATH` to the copy's absolute path;
   - pins the account by setting `CLAUDE_CONFIG_DIR=<config dir>` and pointing `TRANSCRIPT_CONFIG_DIRS_FILE` at an empty file it creates under `<probes-dir>`, and passes no top-level `--config-dir`, which `pr-cost` refuses (rows 101, 102);
   - from this branch's worktree root, runs `python3 claude/.claude/scripts/transcript-analysis.py pr-cost --record <flags>` twice;
   - prints `not rehearsed` and stops when either run exits 2;
   - prints each run's exit status and whether its stderr holds a traceback;
   - prints each run's count of `pr-cost: recorded PR #` lines and of `refusing` lines, and whether its failed-cells count line appeared (row 68);
   - prints whether the copy's bytes are identical before and after the second run;
   - reads the copy with `pr_cost_ledger._parse_pr_cost_ledger_file_text` and prints two booleans. `exercised` says run 1 appended at least one row whose `supersedes` is set. `figures match` says each such row's seven figure columns equal the superseded row's, and no skill in its cell has more rounds than in the superseded cell.

   The runs write only the copy and its `.lock` file, and their `gh` calls only read. Investigate a traceback, a `refusing` line, `not rehearsed`, a nonzero exit without the failed-cells line, or a `no` before merge.

   Before the session hands over either script, it runs `bash -n` and shellcheck on it (row 112). Step 4's `Totals:` line is absent on an empty scope, and the script prints that as a `no`, not as a pass.
6. The PR body, via `/pr-description`, records the booleans from steps 4 and 5 and no figure. It scopes "denied" to this repository's gates and refers to GH-1131 without closing it (row 56).

## Out of scope

- The study command, any look or calendar date, retention changes, and retiring `routing-guard`, as Context states.
- The re-record on real ledgers, which each machine's next ordinary `--record` makes after it pulls this change. Verification 5 rehearses it on a copy of one ledger.
- Inputs the study PR's plan must take:
  - Every machine that recorded rows for the study's repository has run `--record` from a checkout of it that contains this change.
  - `review-cost-by-size` excludes the rows still below the rule (row 90).
  - Rows recorded under the repository's name before its transfer (`CHANGELOG.md:9-16`) are keyed to that name, which `review-cost-by-size` does not read (row 23).
  - The routing-gate record's :78 stays unedited (row 33). It says the guard's rounds are "as `review-round-cost --skill code-review` prints them", and that command no longer prints a denied round-open.
  - The record's :80 stays unedited (row 35). Thinning removes the oldest PRs first, so an arm can fall short of the sample :80 fixes. A re-recorded row is only as complete as the row it replaced.
  - The re-record's counts, PR numbers and machine identity are owner-only figures, per `docs/private-project-redaction.md` § "A wider corpus goes to the owner, never into a public artifact".
  - Whether the study changes detection or pricing, because either bumps the rule again (row 44).
- A pointer to the re-record contract inside `review-cost-by-size`'s excluded-rule line (round-5 product R5 and platform R3), left to the engineer's call. The CHANGELOG Migration bullet is the discovery path meanwhile.
- The invocation counters (`subagent-mix`, `judgment-pair`, `skill-invocation`) still counting a gate-denied `Skill` call, which GH-1131 stays open to track (rows 42, 56).
- Renaming `_append_pr_cost_ledger_row`'s `force` parameter, whose docstring names `--force` as its source. pr-cost passes it `overwrite_captured`, and its error stays unreachable from pr-cost (row 89).
- Calls the permission layer, auto mode or the user refused (row 41).
- Guards for the record shapes row 6 lists (rows 51, 52).
- A launch-record check for spawns, and leaving denied spawns out of `dangling`, a pricing change that would bump the rule again (row 45).
- Linear-time denial patterns (row 43).
- `review-loop-cost-audit`'s gate-denial trigger class. The round-2 backend review read the skill as taking denials from `review-trace --deny-summary`, which this change leaves alone. This revision did not read the skill.
- Plain `--pr N` resolving to another PR, which still writes that PR's row (row 55).
- Splitting any over-limit file, `pr_cost.py` and `test_transcript_pr_cost.py` included (row 46).
- A test that the miner passes the same set to both calls (rows 11, 58). A forgotten argument at `round_opened_by_spawn` is a `TypeError` under the required keyword, which the existing `_collect_round_entries` tests reach (evals/test_review_bench_mining.py:2267). `detect_round_windows` computes the same set itself when none is passed. A wrong set at either call goes uncaught, as the round-3 testing reviewer's finding (sdet R10) states.
- Round-3 findings declined, by reviewer:
  - sdet:
    - R5 and R6, moot.
    - R8, a Verification 4 upper bound.
    - R10, a same-record miner case.
    - R14, a `spawn_open` case.
  - ciso:
    - R6, operating-condition docs.
    - R7, a per-child time bound.
    - R8, cell and join comparisons.
  - platform:
    - R4, an exception handler.
    - R6, cost itemization.
  - product: R6, re-stamp notes.
  - backend: R5, re-stamp notes.
- Round-4 findings not taken, by reviewer:
  - sdet: R3 to R5, moot once the script is gone.
  - ciso: R2 to R5, moot.
  - backend: R1 and R2, moot.
  - platform: R1 to R3, moot.
  - product, moot: R1, R2, R6 and R8.
  - product, declined: R4 (two more PR-body claims), and R7's cohort and rollback sentences and its second CHANGELOG line.
- Round-5 findings not taken, by reviewer:
  - backend: R3 and R6, moot with the walk gone.
  - platform: R1 and R2, moot with the walk gone. R3 is the pointer item above.
  - ciso: R2 and R6, moot with the walk gone.
  - sdet: R7, moot now that the `dangling` condition is cut (row 92).
  - product: R5, the pointer item above.
  - comment-discipline: R1 and R2, moot with the walk gone.
- Round-6 findings not taken, by reviewer (row 100):
  - backend: R6's naming of Verification 5 in the Rollback paragraph.
  - sdet:
    - R1's second half, a status case at the locked site.
    - R4's test, replaced by the rename (row 105).
    - R5's parametrization over every unlisted column.
    - R6, test-order details.
    - R7, a non-string id case.
    - R8, moot under the breakdown skip (row 99).
  - platform:
    - R1's one-root boolean.
    - R2's below-rule counts, scan-count line and elapsed seconds.
    - R4, the first-run cost sentence.
    - R5's reading rule.
    - R7's docs clock sentence.
  - ciso:
    - R2, exit 1 on an unforced refusal (row 97).
    - R3's edit of the already-captured line (row 96).
    - R4's third case, moot because the hint reads `branch_totals.get(branch)`.
    - R5's breakdown and rule booleans.
    - R6's `dangling` check.
  - product:
    - R1's edit of the already-captured line (row 96).
    - R2's re-record visibility text, reading rule and :74 edit.
    - R4's :74 and :178 edits.
    - R8's pointer from "the rest" to the docs paragraph.
  - comment-discipline:
    - R1's Context edits and its :78 and :80 deduplication.
