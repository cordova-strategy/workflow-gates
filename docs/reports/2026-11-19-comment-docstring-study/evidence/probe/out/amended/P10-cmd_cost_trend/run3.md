# comment-discipline-reviewer

## R1 [CONCERN] Restating the code
cost.py:1123-1129 (new docstring on `cmd_cost_trend`).

Issue: The docstring is "CLI entry point for the cost-trend subcommand. Reads the wall-clock date exactly once, here, then delegates to _cost_trend_report, which takes `today` as an explicit parameter — the same split _cost_report uses ...". Nearly every clause restates what the code shows:
- The function name and the single body line (`_cost_trend_report(args, datetime.now(UTC).date())`) show that it is the entry point, reads the clock once and delegates.
- The `_cost_trend_report(args, today: date)` signature at cost.py:1191 shows that `today` is an explicit parameter.
- The identical split in `_cost_report` (cost.py:272 and :519) is findable by static analysis of the repo.

Failure mode: The restated clauses add reading cost and will drift from the code.

Required property: Delete the docstring, or keep only the one decision a reader can't see from the code. That decision is that the clock is read at the CLI edge so tests can pass a fixed `today` to `_cost_trend_report`. If kept, it should be a single sentence, with no "entry point" or "delegates" clauses and no "exactly once, here".

## R2 [CONCERN] False or unsourced claim
cost.py:1125-1128.

Issue: The docstring says the split is "the same split _cost_report uses so the trailing week's '(partial)' label doesn't depend on a live clock read". The `(partial)` label exists only in `_cost_trend_report` (cost.py:1196, :1249). `_cost_report` has no partial label. Its `today` is used only for pricing expiry (cost.py:850, via `pricing._rate_expired`). The split is the same shape in both, but the reason the sentence attributes to it applies to only one of them, so the "same split ... so" claim is only partly supported.

Required property: If any of the sentence is kept, state only what the subject supports. That is, `_cost_trend_report` takes `today` so its "(partial)" trailing-week label is deterministic under test. Drop the `_cost_report` comparison, which R1 also removes.
