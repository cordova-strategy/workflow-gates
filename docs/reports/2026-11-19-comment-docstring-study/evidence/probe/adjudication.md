# Adjudication of the 315-run comment-discipline measurement

Method: read findings text in probe/out/<body>/<cell>/run<N>.md against labels-v3.md clause text. Helper scripts: adjudicate_extract.py, adjudicate_rows.py (read-only; they import score.py to list per-run scorer treatments). No model call. Not claimed: that any of this proves the rule is right. These are label-conformance checks; a few labels are themselves arguable (flagged as AMBIGUOUS).

Premise corrections: (a) the report's paired table says DELETE "amended only 23, shipped only 10", so item 5's "10 rows where amended was right and shipped wrong" is the first 10 of the 23; (b) the "Delete-then-keep" section lists 5 findings, not 7 (1 shipped, 3 amended, 1 ablation).

## 1. KEEP rows: shipped right, amended wrong

Clauses: P23c2 "so the text encodes the same under any locale"; P27c3 "so machine-wide vs. --this-repo output is never scope-ambiguous". Shipped left both untouched in all 3 runs.

P23c2, amended (3/3 deleted the whole docstring):
- run1: R1 "states an output property that `json.dumps` supplies by default"; R2 "is contradicted by its subject ... `built.text.encode("utf-8")`". Deletes. WRONG vs label (KEEP). Its "false" claim is doubtful: run2 cites `ledger_common._publish_new_file` using `os.fdopen(fd, "w")`, "which uses the locale encoding". I could not open that file (not in the frozen cell), so unverified.
- run2: "The claim is true, not false. ... a clause that takes several files to find is still a restatement." Deletes. AMBIGUOUS: (A) label says locale is an outside-repo reason, KEEP; (B) the engineer's rule says delete what "takes several files to find", and the reviewer did find the locale writer in the repo.
- run3: "ASCII-only output is a stdlib default and not a decision"; "The rule under test deletes any clause that static analysis ... finds". Deletes. WRONG vs label (it attacks the ASCII half, not the locale reason; also asserts "no locale-dependent write" that run2 contradicts).

P27c3, amended:
- run1: R1 "delete the sentence" covering "Print the one-line resolved-scope header cmd_skill_invocation already uses, so machine-wide vs. --this-repo output is never scope-ambiguous"; "The shared header text already has its home in `_resolved_scope_header`'s docstring". AMBIGUOUS: (A) label KEEP; (B) the reason is stated in a sibling docstring (the frozen `_resolved_scope_header` docstring does say the root count discloses scope "to prevent the corpus-undercount"), so it is findable.
- run2: R1 "delete the sentence. If a pointer is wanted, use 'Header text and rationale: `_resolved_scope_header`.'" Same AMBIGUOUS.
- run3: R2 "Keep only the reason the header exists ... 'Exists so machine-wide vs. --this-repo output is never scope-ambiguous; see `_resolved_scope_header`.'" CORRECT.

Scorer agreement: scorer counts both as amended wrong (KEEP 6/8). I agree under the label as written. If readings B were accepted, amended KEEP would rise to 7/8 or 8/8.

## 2. "Delete-then-keep on a REWRITE row" (5 findings listed)

REWRITE = one sentence naming the decision and its reason, findable parts dropped.
- shipped P26c4 run3: "Delete the closing sentence. Keep the other four facts: the path is stripped; it mirrors the root-level `strerror` diagnostic; `str(exc)` can embed the path; `OSError(errno, strerror)` rebuilds the subclass". WRONG: only 1 of 6 clauses dropped; findable c3 and c5 kept.
- amended P10c3 run2 (contested row): "Takes `today` at the CLI boundary and passes it in so the trailing week's "(partial)" label is deterministic under test." Drops the sibling half. CORRECT (scorer: undecided).
- amended P25c2 run2 (external row): "Mirror Claude Code's naming of project dirs under ~/.claude/projects/; the scheme is external, so don't change it here." AMBIGUOUS: (A) names the outside source, which is how the label totals score this row; (B) it drops the substitution rule that the label wants retained in qualified form.
- amended P26c4 run1: "Strips the path from the message, because the caller has no per-account label for it; see `_dedup_new_project_dirs`." Decision + reason, findable parts dropped. AMBIGUOUS leaning CORRECT: the reason is the sibling docstring's, not the label's "`str(exc)` can embed the path / engagement path out of the message".
- ablation P17c7 run2: "Delete the consumer list. Keep only the 're-evaluate if an unexpected merge appears' trigger". CORRECT (scorer: undecided).

## 3. Findings the scorer could not attribute

Shipped:
- P31 run3 (`Required fix:` not parsed): "delete the docstring" on a both-DELETE function. CORRECT.
- P06 run3: "Keep the corrected null sentence and delete the first one." c1, c2 deleted: CORRECT. c3 ("A null value counts as absent.", DELETE) kept narrowed: WRONG.
- P08 run1: R2 deletes the lead clause (c1, c2) CORRECT; the R1 compression keeps c3, c4, c5 and c6 with "silently" ("Accepts a root with `sessions/` or `projects/`, not `declared_transcript_roots()`'s ... `projects/`-only check, which would silently drop a sessions-only root") WRONG for c3-c5; c7 kept CORRECT.
- P13 run3: "The first clause is non-obvious and worth keeping ... Delete the second clause". c3 deleted CORRECT; c1, c2 kept WRONG.
- P19 run2: "keep the zero-total fact, drop the ruled-out alternative" (`value/total as a percentage string; 0.0% when total is zero.`). c1, c2 kept. WRONG.
- P20 run2: R1 keeps a narrowed c2 ("from a value printed in a table cell"); R2 "Either delete the docstring, or replace it with the one non-obvious fact". AMBIGUOUS, leaning WRONG (R1 requires keeping c2, R2 allows deleting; the reason offered is in a test docstring).
- P30 run3: deletes c2, c3 CORRECT; keeps c1 as "Pre-branch step only, for a branch the caller already carried forward" WRONG.
- K1 run1: flags unsourced vendor claims; R2 "drop the 'what' halves and keep each reason". Reasons retained, not deleted. CORRECT on retention; the trim is a mild edit (K control passes by scorer rule). AMBIGUOUS only on whether trimming counts.
- K2 run3: asks for sources, "or drop the vendor rationale and keep only the non-obvious constraint". No deletion. CORRECT.

Amended:
- P30 run2 (`Required fix:` not parsed): "Delete the docstring." CORRECT.
- P09 run1, run3: "delete those three clauses" (c1-c3) CORRECT; keeps a rewritten c4 ("A separate function so a test can replace the listing and simulate a file that vanishes ...") WRONG, since the same findings cite the test seams as evidence.
- P10 run1: "Reads the clock here, not in `_cost_trend_report`, so tests can pass a fixed `today` ... Delete the remaining clauses." c1 deleted CORRECT, c2 survives as subject CORRECT, c3 rewrite CORRECT. P10 run2: see item 2.
- P11 run1, run2: "Delete the first sentence" (c1 CORRECT); keep "A status missing from `_GH_STATUS_TO_KIND` falls back to unexpected payload rather than aborting the run" (c2, c3 WRONG vs label). The label itself is arguable ("names the alternative, not a reason"); the reviewer read it as a decision with a reason. Flagged as label-side ambiguity.
- P25 run3: deletes c1, c3; the one-line rewrite "Mirror Claude Code's naming of project dirs ... which this repo cannot change" is the same AMBIGUOUS as item 2 for c2.
- P26 run1: see item 2. Rows c1, c5, c6 deleted CORRECT in all three amended runs; c2, c3 survive inside the decision/pointer, AMBIGUOUS.

Ablation:
- P08 run3 (four no-label findings): deletes c1-c5 CORRECT; R4 deletes c6/c7 but allows "If the author judges the sessions-only purpose to be an outside constraint, keep that single sentence". c7 (KEEP) deleted with an escape hatch: WRONG/hedged; c6 AMBIGUOUS.
- P18 run2, P31 run2, run3: delete everything. CORRECT (all-DELETE functions).

## 4. P17c7 ("If cost --by-project, buckets' Proj count, or user-input's Scope project count ever shows an unexpected merge, re-evaluate.", REWRITE: drop list, keep trigger)

Shipped:
- run1 R3: "either keep it, accepting that it can go stale, or say 'if any caller's project counts show an unexpected merge'". AMBIGUOUS, leaning WRONG (keeping the list is offered as acceptable).
- run2 R3: "Replace the inventory with the trigger, e.g. 'Re-evaluate if any per-project count shows an unexpected merge.' Keep the collision-risk sentence." CORRECT.
- run3 R3: "Re-evaluate if a caller's project count (cost `--by-project`, buckets, user-input) shows an unexpected merge." WRONG: consumers still named.
Shipped result: 1 CORRECT, 1 WRONG, 1 AMBIGUOUS. A hit only if run1 counts. I differ from the scorer (hit).

Amended:
- run1 R2: "reduce the re-evaluation sentence to the trigger alone ('re-evaluate if an unexpected merge appears'), or delete it." AMBIGUOUS (preferred option correct; deletion offered as equal).
- run2 R3 and run3 R2: "delete the sentence" / "delete the 'If cost --by-project ... re-evaluate' sentence". WRONG (trigger lost).
Amended: miss; agrees with scorer.

## 5. Spot check: first 10 of the 23 amended-right/shipped-wrong DELETE rows

Alphabetical order: P04c1, P04c2, P05c1, P06c1, P06c2, P06c3, P08c3, P12c1, P12c2, P12c4.
- P04c1, P04c2: shipped untouched 3/3 ("No findings", "a tightly coupled pair"); amended 3/3 "Delete the docstring". CONFIRMED.
- P05c1: shipped "No findings" x3; amended 3/3 "delete the docstring". CONFIRMED.
- P06c1, P06c2: NOT confirmed. Shipped run2 "delete the docstring" and run3 "Keep the corrected null sentence and delete the first one" are both deletions, so shipped is right 2/3 (run1 kept). I differ from the scorer.
- P06c3: confirmed. Shipped run1 and run3 narrow and keep the null sentence; run2 deletes. Amended 3/3 delete (each with a conditional "keep a comment only if ... outside the repository").
- P08c3: confirmed. Shipped run1, run2 keep the check in the suggestion; run3 is self-contradicting (R2 keeps "Validates with `sessions/` or `projects/`", R3 deletes "the restated check"). Amended 3/3 delete ("Delete the ... restated lambda condition" / "description of what the validator checks" / "'validated against' clauses"). Amended is right 3/3 (the scorer had 2/3; same majority).
- P12c1, P12c2: AMBIGUOUS for shipped. Run1 no findings; run2 "Delete the summary sentence" (right); run3 R1 narrows c1 but R2 says "keep only the non-obvious facts" (self-contradicting). Amended run1 and run3 delete, run2 deletes the "sentence" while folding the subject into the ordering sentence: 3/3 right.
- P12c4: shipped run1 none, run2 keeps ("not idempotent" paragraph), run3 omits it from the keep list (implicit). Amended 3/3 "delete the sentence". Confirmed shipped not right in a majority.
Result: 8 of 10 fully confirmed or confirmed with caveats (P12c1, c2 ambiguous on shipped); 2 not confirmed (P06c1, P06c2).

## 6. Corrected counts (non-contested rows; scorer's bar-set preserved)

Recomputed: every function touched by a scorer-unattributed finding (P06, P08, P09, P10, P11, P13, P19, P20, P25, P26, P30, P31, P18), all KEEP rows, P17c7, and P08c6. Carried over unread: all other rows, including P01c3 and P21c3 REWRITE, the other subject rows, and DELETE rows in functions the scorer did not mis-parse.

Rows where my verdict differs from the scorer:
- Shipped DELETE, wrong to right: P06c1, P06c2, P13c3 (+3).
- Amended DELETE, wrong to right (scorer's echo/no-label handling credited no deletion): P09c1, P09c2, P09c3, P10c1, P11c1, P25c1, P26c1, P26c5, P26c6 (+9).
- Ablation DELETE, wrong to right: P08c5 (+1).
- Amended subject, wrong to right: P08c6 (scorer read "Remove 'silently'" as deleting the clause; all three runs retain "would drop a sessions-only root") (+1).
- Shipped REWRITE, hit to miss: P26c4 (keeps findable facts), P17c7 (1 CORRECT, 1 WRONG, 1 AMBIGUOUS; hit only if run1 counts).
- Amended REWRITE, miss to hit: P26c4 (runs 2 and 3 one-sentence decision + reason; run1 AMBIGUOUS). P17c7 unchanged (miss).
- Unchanged but AMBIGUOUS: P23c2, P27c3 (KEEP), P08c6/c7 ablation, P25c2 (external), P26c2/c3.

| group | shipped | amended | ablation | scorer shipped / amended / ablation |
|---|---|---|---|---|
| KEEP recall | 8/8 | 6/8 (P23c2, P27c3 deleted; 8/8 only if the label KEEPs are rejected) | 2/8 | 8 / 6 / 2 |
| DELETE recall (76) | 47 | 66 | 75 | 44 / 57 / 74 |
| REWRITE (4) | 0 (1 if P17c7 run1 counts) | 1 (P26c4) | 0 | 2 / 0 / 0 |
| subject retention (8) | 4 | 6 | 2 | 4 / 5 / 2 |

Against the stated bars (KEEP >= 7, DELETE >= 68, REWRITE >= 4, subject >= 6): amended KEEP still fails, DELETE still fails (66 < 68, 2 short), REWRITE still fails, subject now meets the bar. Relative amended vs shipped: KEEP -2, DELETE +19. Ablation KEEP 2/8 still discriminates the rule from delete-everything.

## Not verified
- ledger_common.py (the P23 locale claim): not present in the frozen cell.
- Shipped/ablation findings for functions outside the unattributed list: relied on scorer treatments.
- P01c3, P21c3 REWRITE rows and the subject rows other than P08c6: carried over.
- Per-run whole-deletion claims by the scorer for functions outside item 3: not re-read.
- Whether the label calls themselves are right (P11c2/c3, P23c2, P27c3, P25c2): flagged AMBIGUOUS, not decided.
