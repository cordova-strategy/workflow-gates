# comment-discipline-reviewer

Set aside: none. The prompt's replacement "Don't restate the code" bullet governs the Restating-the-code angle. Its keep-decisions-with-reasons clause is applied to the docstring clause that carries a reason.

## R1 [CONCERN] Prose restating the code

cost.py:1123 (added docstring, first line)

Text: `"""CLI entry point for the cost-trend subcommand.`

Issue: The function name `cmd_cost_trend` and its `argparse.Namespace` signature already show that it is the subcommand's CLI entry point. The line records no decision.

Failure mode: A reader parses a clause that tells them nothing the signature doesn't.

Required property: Delete the clause.

## R2 [CONCERN] Prose restating the code

cost.py:1125-1126 (added docstring)

Text: `Reads the wall-clock date exactly once, here, then delegates to _cost_trend_report, which takes `today` as an explicit parameter`

Issue: The body, `_cost_trend_report(args, datetime.now(UTC).date())`, shows the single clock read, the delegation, and the `today` parameter. Line 1191 shows that `_cost_trend_report` takes `today: date`.

Failure mode: The text restates the code. It will drift if the body changes.

Required property: Delete the clauses "reads the wall-clock date exactly once, here", "delegates to _cost_trend_report", and "takes `today` as an explicit parameter". Keep only the decision in R4, with `_cost_trend_report` still named as its subject.

## R3 [CONCERN] Prose restating the code

cost.py:1126-1127 (added docstring)

Text: `the same split _cost_report uses`

Issue: Static analysis of this repository finds the pattern. `_cost_report(args, today, roots)` at line 519 is called with `datetime.now(UTC).date()` at line 272. It repeats a fact the code already shows. The cross-reference is not a pointer to a doc or symbol that holds a decision.

Failure mode: A parallel-structure claim that goes stale if either function changes.

Required property: Delete the clause.

## R4 [FYI] Kept decision: keep it as a single sentence

cost.py:1127-1129 (added docstring)

Text: `so the trailing week's "(partial)" label doesn't depend on a live clock read inside a function under test`

Issue: This clause is a design decision with a reason. The decision is that `_cost_trend_report` receives `today` rather than reading the clock. The reason is testability of the "(partial)" label. Neither the code nor its tests state that reason, so the clause survives. The claim is true: line 1249 builds the "(partial)" label from `today`.

Required property: After R1-R3, the docstring is one sentence, with the subject clause kept so the reason still names what it explains. Example: "`_cost_trend_report` takes `today` as a parameter so the trailing week's "(partial)" label doesn't depend on a live clock read in a function under test."
