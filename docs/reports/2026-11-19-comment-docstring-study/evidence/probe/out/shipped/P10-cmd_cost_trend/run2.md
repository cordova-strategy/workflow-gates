# comment-discipline-reviewer

Reviewed 1 diff file (`cost.py`), 1 site in scope (the new `cmd_cost_trend` docstring). The dispatch named no text that contradicts the agent file, so nothing was set aside.

## R1 [CONCERN] False or unsourced claim

`claude/.claude/scripts/transcript_analysis/cost.py:1125-1128` (diff lines 8-14)

Issue: the docstring says `_cost_trend_report` takes `today` as a parameter, "the same split _cost_report uses so the trailing week's '(partial)' label doesn't depend on a live clock read". The subject only supports half of that.
- `_cost_report(args, today, roots)` at cost.py:519 does take `today`, and `cmd_cost` reads the clock once at cost.py:272.
- Within `_cost_report`, `today` feeds only `pricing._rate_expired(model, today)` (cost.py:850) and the stale-pricing notice (cost.py:1003).
- Grepping cost.py for `partial` finds hits only in `_cost_trend_report` (cost.py:1196, 1249).
- So `_cost_report` has no "(partial)" label, and its `today` parameter exists for the pricing-expiry check, not for the reason given.

Production failure mode: a future contributor reads that `_cost_report` pins `today` for a partial-week label. They look for one and conclude the docstring, or `_cost_report`, is broken.

Required property: state only what the code supports. For example, "`today` is a parameter, not a clock read inside `_cost_trend_report`, so tests can pin which week gets the '(partial)' label (cost.py:1249)." Drop the claim about why `_cost_report` takes `today`.

## R2 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/cost.py:1123-1126` (diff lines 8-11)

Offending text: "CLI entry point for the cost-trend subcommand. Reads the wall-clock date exactly once, here, then delegates to _cost_trend_report, which takes `today` as an explicit parameter".

Issue: the function name, its `args: argparse.Namespace` signature, and its one-line body (`_cost_trend_report(args, datetime.now(UTC).date())`) already show that it is the CLI entry point, reads the date, and delegates. Per §Durable text "Don't restate the code".

Required property: delete the restating sentences. The only non-obvious fact is why `today` is injected (testability of the partial-week label), and the corrected sentence from R1 covers it. A shorter or corrected restatement still restates, so keep nothing beyond that single rationale sentence. Do not add a cross-reference to `_cost_report`.
