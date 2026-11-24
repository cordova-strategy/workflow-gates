# Stage 1 go/no-go (approved criteria; scratch, no repo file)

Status: the engineer approved these criteria on 2026-11-20, with a REWRITE threshold of 7 of 10. Nothing here has been run.

## What this decides

Stage 1 is the `amended-v2` body and its rule over 21 cells, with 3 runs per cell and 10 for P17 and P26 (77 runs, about
$9.39 at the first measurement's $0.122 per run mean). The cells are:

- 19 chosen cells: P01, P12, P16, P17, P25, P26, K1, K2, P11, P19, P05, P09, P18, P22, P28, P03, P08, P23, P27.
- R1 and R2, two KEEP controls whose docstrings need no edit (like K1 and K2; neither is a rewrite-reflex control).

P10 and P21 moved to stage 2, and P12 and P16 moved in. Go means run stage 2: the 16 remaining cells, 48 runs, about
$5.86. No-go means stop and read the failing condition before spending more.

The comparison arm is the first measurement's amended body (`out/amended`, "old amended"), scored under the same v4
labels. The shipped arm is not a stage-1 comparison.

## Rule for gating

Gate only on harm that a reader confirms in the findings text. `stage1_compare.py` and `score.py` list candidates and the
finding files to read; they gate nothing. Everything else is reported with its cause.

## Precondition (not a gate): the runs completed and cost is accounted for

Run `stage1_precheck.py` after the runs. It passes only when all three counts hold:

- 77 findings files under `out-v2/amended-v2/`.
- 77 cost files under `out-v2/amended-v2/`, each with a numeric, non-negative `total_cost_usd`.
- Every run's init event names the model id recorded in the freeze (from `out/amended/P17-project_family/run1.cli.jsonl`).

The runner's closing line is not evidence. It prints only the runs it started in that execution (`run_probe.py:239`), a
`claude` process that exits non-zero is reported and the loop continues (`run_probe.py:229-230`), and spend can pass
`--max-total-usd` by one run (`run_probe.py:217`). If the precondition is not met, the conditions below are unmeasured.

## Conditions

All conditions must hold for GO.

| id | condition | tool | origin |
|---|---|---|---|
| a | P17c7 and P26c4 each pass the five-point checklist in at least 7 of their 10 amended-v2 runs, with every packet adjudicated (none pending). | `adjudication_packets.py`, then `adjudication_score.py --threshold 7` prints `REWRITE bar (amended-v2): PASS` | Fable's (a) |
| b | NO-GO only when 2 or more DELETE rows that old amended got right in 3 of 3 runs are wrong in 2 or more of v2's 3 runs, and a reader confirms each flip in the findings text. Pointer conversions (P01c3, P22c2, P28c1) are listed separately and do not count. | `stage1_compare.py` lists candidates and the files to read | Fable's (b), tightened |
| c | K1, K2, R1 and R2: NO-GO if any run deletes a clause of a control, or if a hand-read edit that changes a control's reason or trigger appears in 2 or more of its 3 runs. | `stage1_compare.py` line (c) lists runs that delete and runs with an edit; the reader judges each edit | Fable's (c) for K1 and K2; R1 and R2 added by me |
| d | NO-GO if any KEEP row, or any of the 7 subject rows whose paired row is not CONTESTED, that old amended got right in 2 or more of 3 runs is deleted in 2 or more of v2's 3 runs, and a reader confirms it. Hand-read every KEEP row the scorer marks "edited". | `stage1_compare.py` line (d) | Fable's (d), merged with my KEEP-row condition |

Conditions b, c and d use the first 3 runs of each cell so both arms weigh equally. Condition a uses all 10 runs of P17 and
P26. The 7 subject rows are P03c1, P08c6, P17c5, P23c1, P26c2, P27c1 and P27c4. P10c2 and P21c2 are excluded because their
pairs (P10c3, P21c3) are CONTESTED. The former condition f (whole-docstring deletions) is dropped.

### The REWRITE checklist (condition a)

An adjudicator, given the packets directory only, marks each of five points with a verdict and one quoted line of evidence:

- (a) The decision survives, and the finding does not offer "or delete it" as an acceptable alternative.
- (b) The kept sentence names the decision.
- (c) The kept sentence names the reason or trigger, or where the reason lives.
- (d) A reason absent from the original docstring appears only as a pointer, and the adjudicator confirms that the
  pointed-to lines state it.
- (e) The kept sentence carries none of the row's "Parts that must go".

The P26c4 row note names the decision as "keeps any path out of the message". It lists where the reason lives:
`scope.py:391-397`, `scope.py:410-413` and `_config_dir.py:112-118` (each checked in the frozen snapshot). A pointer to where
the reason lives is the output the rule wants; P26c3 is that pointer and is CONTESTED. The mechanism of the error rebuild
(P26c5) is kept out of the decision text.

## Reported, not gating

- P25c2, on its own: runs passing the checklist out of 3. It rests on a fact outside the repository the reviewer cannot
  check.
- P10c3, P21c3 and P26c3: CONTESTED, listed only. P10 and P21 are not in stage 1.
- Every other DELETE flip (old right majority, v2 wrong majority), each with its cause from the findings.
- Pointer conversions: P01c3, P22c2 and P28c1, listed apart.
- Every KEEP row v2 edited in any run, read by hand.
- The reflex: per arm, runs that keep P09c2, P11c2, P11c3, P18c2, P19c2, P22c2 or P28c1 as a decision sentence, read by
  hand.
- Old amended as a third source in the adjudication (`--source amended-v1=out/amended` beside `--source
  amended-v2=out-v2/amended-v2`). It shows whether the wording moved P17c7 or P26c4 at all.
- The `score.py` REWRITE line and its delete-then-keep list. The adjudicator decides REWRITE.

## How to read the result

- GO: the precondition is met and a to d all hold. Run stage 2.
- NO-GO on a: this cannot separate the rule change from the body change, because v2 changes three things against v1: the
  rule's compress-only sentence, the body's fix shape, and the body's opening. It says the package did not produce a
  surviving decision-and-reason sentence, and the failed checklist points say where to look.
- NO-GO on b or d: v2 deleted rows the first measurement kept or deleted correctly. Name the rows and the finding files.
- NO-GO on c: the package deletes or rewrites text that needs no edit.
- Precondition not met: fix that first.

## Freeze before the first stage-1 run (not done yet)

`freeze.py` prints the sha256 list and writes nothing. Run it, save the output when the engineer approves, and never run
it against a stage-1 run. The list covers:

- `labels-v4.md`, `labels.json`, `bodies/amended-v2.md`, `bodies/amended-v2-rule.md`, this file and `v2-diff.md`.
- `score.py`, `probe_common.py`, `stage1_compare.py`, `stage1_precheck.py`, `adjudication_score.py`,
  `adjudication_packets.py` (its row notes and checklist), `run_probe.py` and `freeze.py`.
- The `diff.patch` of each of the 21 stage-1 cells.
- A tree hash of `snapshot/` and of `out/amended/` (the old arm, streams included).
- The baseline records `score-report-full.txt` and `adjudication.md`.
- `~/.claude/CLAUDE.md` and `~/CLAUDE.local.md`.
- The model id and CLI version from the init event of `out/amended/P17-project_family/run1.cli.jsonl`. Stage-1 runs must
  match the model id; the precondition checks it.

Any change after the first stage-1 run is recorded as post-hoc, as the P21c3 relabel is. `freeze.py --check <saved
listing>` prints what changed.

## Adjudication independence

- The adjudicator gets the packets directory only. The key goes in `adjudication-key/`, outside it, and
  `adjudication_packets.py` refuses a key path inside the packets directory.
- Packet files carry shuffled ids and no arm name. Lines naming the arm are replaced, and the v2-only phrases ("trigger
  half", "restated half", "where its reason lives", "one sentence per decision", "replacement sentence") are masked in
  place so a proposed sentence survives. This reduces leakage and does not prove blinding.
- A verdict file needs one quoted line of evidence per checklist point, or it counts as pending.

## Limits to state with any result

- The REWRITE answer rests on two rows. At 7 of 10, a behaviour that fires 90%, 80%, 70%, 60% or 30% of the time passes a
  single row at 0.987, 0.879, 0.650, 0.382 and 0.011, and both rows at 0.975, 0.773, 0.422, 0.146 and 0.000. Those are
  binomial figures on assumed rates, not measured ones.
- Stage 1 gives P17 and P26 ten runs and the other cells three, so b, c and d use fewer runs than those cells have.
- `ctl_keep_*` module names in K1 and K2 (first-measurement cells, left unchanged so old amended stays comparable) are
  visible to the reviewer. R1 and R2 use neutral names.
- `score.py`'s full report is wired to the first measurement's three bodies. `stage1_compare.py` covers stage 1 only.
- The labels moved between measurements (P01c3, P21c3, P26c2, P26c3). v3 and v4 scores of the first measurement are not
  interchangeable.
