# Comment-reviewer docstring study: labelled evidence and the stage-1 result

## In plain terms

The `comment-discipline-reviewer` agent checks code comments and docstrings against a rule in `claude/.claude/CLAUDE.md` § "Durable text": do not restate what the code already shows. This study asked whether a narrower rule would work better, one under which a docstring keeps only design decisions, meaning the reasons behind the code.

To test it, the study split real docstrings from this repository into clauses. Each clause was labelled keep, delete or rewrite under that rule. The reviewer then ran on each case with the narrower rule added, and its verdicts were compared with the labels.

Stage 1 was a go/no-go check run before a larger second stage. It met three of its four stop conditions, so the answer was NO-GO and stage 2 never ran. Each of two clauses labelled rewrite got an acceptable rewrite in 3 of 10 runs, against a bar of 7 of 10. A clause labelled keep was deleted in all 3 of its runs. The rule and the reviewer's wording were left unchanged.

The rest of this report is the record: where each file is, how to re-check the counts, what is not published, and which labels are disputed.

**Date:** 2026-11-22. The study ran from 2026-11-19.
**Pin:** `ccab57e5`, the `origin/main` commit that added `.claude/plans/comment-rule-false-angle-fix.md`. The study recorded `4d2d6ea16136`, which is not an ancestor of `origin/main`, because this repository squash-merges. Each of the 18 modules under `claude/.claude/scripts/` that the real docstring cells reviewed is byte-identical at the pin, checked against the digest each cell recorded. The cells' `meta.json` files are not published, so this check cannot be repeated from the published set.
**Model and CLI:** `claude-sonnet-5-5` and Claude Code `2.1.329`, as frozen at `evidence/probe/freeze-stage1.txt:42`.
**Invocation:** each run was `claude -p` with the reviewer body as an inline agent, `--model sonnet --effort high`. Amended and ablation runs got `amended-rule.md` appended to the system prompt, amended-v2 runs got `amended-v2-rule.md`, and shipped runs read the rule from the author's installed instruction file.
**Instruction context:** every run also loaded the author's two user-level instruction files (`evidence/probe/freeze-stage1.txt:40-41`). One of them is not in this repository, and neither is copied into this report.

## The rule the labels apply

`evidence/labels-v4.md` line 7 states the rule. Beyond the gist in "In plain terms", this report does not restate it.

## Layout

`evidence/` mirrors the study's working tree, so a relative path a record cites to another published file resolves inside it. `.rgignore` hides `evidence/` from Grep. A Grep rooted at `evidence/` searches it.

- `evidence/labels-v4.md` is the label table. `evidence/probe/labels.json` carries the same labels keyed by `row_id`, where `P17c7` is clause 7 of function P17.
- `evidence/probe/cells/<id>-<function>/diff.patch` is the diff each run reviewed. P01 to P31 are real docstrings from this repository. K1, K2, R1 and R2 are keep controls, and D1 and D2 are delete controls. R1 and R2 ran in stage 1 only.
- `evidence/probe/out/<body>/<cell>/run<N>.md` holds the first measurement's findings, for bodies `shipped`, `amended` and `ablation`, runs 1 to 3. `evidence/probe/out-v2/amended-v2/<cell>/run<N>.md` holds stage 1's.
- `evidence/probe/bodies/` holds the four reviewer bodies and the two rule files the runs used.
- `evidence/probe/adjudication/packets/` and `evidence/probe/adjudication/verdicts/` hold the 32 blinded packets and their verdicts. `evidence/probe/adjudication-key/key.json` maps each packet id to `source`, `row_id` and `run`. Source `amended-v1` is `probe/out/amended/`, and `amended-v2` is `probe/out-v2/amended-v2/` (`go-no-go.md:77-78`).
- `evidence/probe/go-no-go.md`, `v2-diff.md` and `freeze-stage1.txt` are stage 1's criteria, change list and pre-run freeze. `go-no-go.md` was approved before any run, so its lines saying nothing has run are not a contradiction.
- `evidence/probe/stage1-results.md` holds the frozen tools' output after the stage-1 runs. It postdates the freeze, so no freeze line covers it.
- `evidence/probe/score-report-full.txt` and `evidence/probe/adjudication.md` are the first measurement's scorer report and hand adjudication.

## Not published

- **Stream logs, per-run cost files, run prompts, manifests and run logs.** They are raw run mechanics, and each prompt names only a diff path and an output path.
- **Every script the records cite**, such as the scorer, comparer, runner and freezer. The study published data, not tooling.
- **Frozen module copies, the `snapshot/` tree and each cell's `meta.json`.** The real modules are at the pin, and the six synthetic modules are 3 to 13 lines that their diffs largely show.
- **Labeller and reviewer drafts, pilot and cost notes, `labels-v3.md` and the unfrozen label copies.** `labels-v4.md` carries each labeller's verdict per row, and `probe/labels.json` is the frozen copy.
- **Stage 2 and the unused `ablation-v2` body.** Stage 2 never ran.
- **The author's two user-level instruction files.**

## Changes made to the copy

Eleven files differ from the working tree by three literal substitutions. No other byte changed, checked against a manifest of the working-tree files taken before the copy, which is not published.

1. The home-directory prefix became `/home/<username>/`, once in each of 8 run files: `out/shipped/P16-cmd_read_cost/run2.md` and `run3.md`, `out/shipped/P31-bash_command_is_mutating_git/run2.md`, `out/shipped/K1-fetch_report/run1.md`, `out/amended/P02-declared_transcript_roots/run1.md`, `out/ablation/P16-cmd_read_cost/run3.md`, `out/ablation/P24-lost_event_hides/run2.md` and `out-v2/amended-v2/P16-cmd_read_cost/run1.md`, all under `evidence/probe/`.
2. In `evidence/probe/labels.json` and `evidence/probe/score-report-full.txt`, the 40-character source commit became its 12-character prefix, `4d2d6ea16136`, once per file.
3. In `evidence/probe/freeze-stage1.txt` lines 1 to 41, each 64-character digest became its first 16 characters. The 12 lines for unpublished files stay, with their digests cut like the rest, as part of the freeze record.

## Recipes

The freeze digests match the files as of the commit that adds this report. `git log` on `evidence/` shows any later change.

Freeze check, run from the repository root. Of the 41 digest lines, 27 name files published unchanged, 2 name files changed by rule 2 above, and 12 name files that are not published (the scripts, the two tree hashes and the two user-level instruction files). Expected output: `27 matching, 2 differing, 12 not published`.

```
find docs/reports/2026-11-19-comment-docstring-study/evidence -type f -print0 | xargs -0 sha256sum | awk -v dig=1 -v pth=2 -v last=41 -v marker=evidence/ 'FNR==NR { if (FNR <= last) { frozen[$pth]=$dig; paths[++n]=$pth }; next } { at=index($pth, marker); if (at) published[substr($pth, at+length(marker))]=$dig } END { for (i=1; i<=n; i++) { p=paths[i]; if (!(p in published)) unpublished++; else if (substr(published[p], 1, length(frozen[p])) == frozen[p]) matching++; else differing++ }; print matching+0, "matching,", differing+0, "differing,", unpublished+0, "not published" }' docs/reports/2026-11-19-comment-docstring-study/evidence/probe/freeze-stage1.txt -
```

REWRITE-bar recount, run from the repository root. A run passes only when all five checklist points pass. Expected output: `P17c7 passing 3 of 10: p008, p022, p028` and `P26c4 passing 3 of 10: p011, p013, p031`.

```
jq -n -r 'input as $key | [inputs] | map(select(all(.a, .b, .c, .d, .e; .pass))) | map(.packet_id) as $passing | $key.packets | to_entries | map(select(.value.source == "amended-v2" and (.value.row_id == "P17c7" or .value.row_id == "P26c4"))) | group_by(.value.row_id)[] | "\(.[0].value.row_id) passing \(map(select(.key | IN($passing[]))) | length) of \(length): \(map(select(.key | IN($passing[])) | .key) | sort | join(", "))"' docs/reports/2026-11-19-comment-docstring-study/evidence/probe/adjudication-key/key.json docs/reports/2026-11-19-comment-docstring-study/evidence/probe/adjudication/verdicts/p*.json
```

## Result

- The first measurement's overall line is FAIL under v3 labels (`evidence/probe/score-report-full.txt:16`). `evidence/labels-v4.md` line 3 names the four relabels since v3.
- The stage-1 precondition was met (`evidence/probe/stage1-results.md` lines 7 to 10).
- **Stage 1 is NO-GO on conditions a, c and d.** Condition b did not trigger. `go-no-go.md` lines 81 to 89 say how each condition reads.
- **Condition a.** P17c7 and P26c4 each passed the REWRITE checklist in 3 of 10 runs against a gate of 7 of 10 (`stage1-results.md` lines 18, 19 and 27). The packet ids are the ones the recount above prints.
- **Condition b: candidates 4, confirmed 0.** The candidates are in `stage1-results.md` lines 33 to 38, and each run file is under `evidence/probe/out-v2/amended-v2/`.
  - P01c1 and P01c2: unconfirmed. Every run's replacement omits the clause (`P01-declared_roots_file/run1.md`, `run2.md`, `run3.md`).
  - P01c4: read as a pointer conversion, the way `go-no-go.md` line 43 treats P01c3, P22c2 and P28c1 (listed apart, not counted), not a confirmed flip. Run 1 deletes it, and runs 2 and 3 restate its contrast from the label's side.
  - P17c1: unconfirmed. The clause survives in `P17-project_family/run3.md` only, and runs 1 and 2 drop it.
  - Other flips, not gated (`stage1-results.md` line 39): P08c1 and P08c2 are unconfirmed, because all three `P08-declared_config_dirs` runs drop them. P08c3 is kept in a rewritten pointer form in runs 2 and 3.
- **Condition c.** Control R1 had a clause deleted in 3 of 3 runs (`stage1-results.md` line 44), so the condition fails.
  - R1's clause is "a lockout stalls every job sharing that key". Each run calls it an unsourced cause-and-effect claim, not a restatement, and its proposed replacement omits it (`R1-schedule_retry/run1.md` lines 26 to 36, `run2.md` lines 21 to 36, `run3.md` lines 5 to 15). All three runs offer sourcing it as an alternative to deleting it.
  - K1's one edit is in `K1-fetch_report/run3.md`. It asks for a version and a locatable source and changes no reason or trigger, in 1 of 3 runs.
- **Condition d: candidates 1, confirmed 1.** Condition d is met as a NO-GO trigger in its own right, alongside conditions a and c.
  - P27c1 is deleted in `P27-print_resolved_scope/run2.md` (lines 5 to 25) and `run3.md` (lines 7 to 13). Run 1 keeps it with a pointer (line 37).
  - P27c3 is deleted in the same findings, in all three runs. The scorer's candidate list did not include it.
  - P27c5 is not deleted in any run. Its reason survives in all three, with the wording "process startup" corrected to import time. Run 3 omits "any later reassignment".
- Stage 2 never ran.

## Disputed and contested labels

- **Disputed:** P11c2, P11c3, P23c2, P27c3 and P25c2. `evidence/probe/adjudication.md:109` flags them AMBIGUOUS and does not decide them.
- **CONTESTED:** P05c2, P10c3, P21c3, P22c3, P26c3 and P29c4. CONTESTED is a flag on six of the 101 label rows, never scored as a category of its own. `evidence/probe/adjudication-key/key.json` lines 204 to 208 list P10c3, P21c3 and P26c3 as listed-only. The other three appear only in `labels.json`.

## Limits

- Blinding was partial. Each appended rule file opens "Rule under test", and K1 and K2 keep visible `ctl_*` module names. R1 and R2 use neutral names.
- The REWRITE answer rests on two rows (`go-no-go.md:120-122`).
- Labels changed between measurements, so v3 and v4 scores are not interchangeable.
- Comments other than docstrings were not measured.
- The scorer's matcher thresholds were tuned on the same outputs.

## Published figures

Each figure below was released by the engineer for this report, per `docs/private-project-redaction.md` § "The owner can authorize one figure, case by case". Each line names the figure by file, line and kind, not by value. The inputs behind them, the per-run cost files and the frozen scripts, are not published, so none of these figures can be re-run from the published set. The engineer also confirmed on 2026-11-21, answering "Yes, one account", that every run behind the four figures used one account on this repository's own files, so publishing them together adds no per-account or per-project breakdown. No figure here composes with a grandfathered or earlier authorized figure to reconstruct a calendar-time series or narrow a boundary.

- `go-no-go.md` line 8, the stage-1 cost estimate: the stage-1 run count times the per-run mean. Engineer's answer "Publish unchanged", 2026-11-22 12:53 UTC.
- `go-no-go.md` line 8, the per-run mean: the mean `total_cost_usd` over the first measurement's amended-body cost files. Engineer's answer "Publish unchanged", 2026-11-22 12:53 UTC.
- `go-no-go.md` line 14, the stage-2 cost estimate: the stage-2 run count times the per-run mean. Engineer's answer "Publish unchanged", 2026-11-22 12:53 UTC.
- `stage1-results.md` line 8, the stage-1 spend to four decimals: the sum of `total_cost_usd` over the stage-1 cost files, as `stage1_precheck.py` prints it. Engineer's answer "Publish unchanged", 2026-11-22 12:55 UTC.
- `.claude/plans/comment-reviewer-docstring-fixtures.md` line 13, the same stage-1 spend rounded to cents, in the plan's Context. Engineer's answer "Publish unchanged", 2026-11-22 12:55 UTC.
