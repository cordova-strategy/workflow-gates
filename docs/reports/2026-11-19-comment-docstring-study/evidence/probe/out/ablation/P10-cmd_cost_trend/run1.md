# comment-discipline-reviewer

Scope: 1 file reviewed (`cost.py`), 1 carrying an in-scope change (the new `cmd_cost_trend` docstring, diff lines 8-14). No prompt text contradicted this file's scope. The system reminder carrying `python-environment-conventions.md` concerns installing Python dependencies and does not bear on this review, so I set it aside.

## R1 [CONCERN] False or unsourced claim

`cost.py:1125-1128`, the docstring clause "the same split _cost_report uses so the trailing week's "(partial)" label doesn't depend on a live clock read".

- **Issue:** The claim is settleable, and `_cost_report` contradicts it. `_cost_report` (`cost.py:519`) has no "(partial)" label. `Grep` for `partial` in `cost.py` hits only `cost.py:1127`, `1196` and `1249`, all in the cost-trend path. `_cost_report` takes `today` for pricing expiry (`pricing._rate_expired(model, today)` at `cost.py:850`, and the STALE PRICING notice at `cost.py:1003`). The split is real, but the stated purpose is not what `_cost_report` uses it for.
- **Production failure mode:** A maintainer reads the docstring and looks for "(partial)" handling in `_cost_report`. They find none and conclude the two functions diverge, or they wrongly assume `cost` labels partial weeks.
- **Required property:** The narrowest supported statement is that `_cost_report` also takes `today` as a parameter. That statement restates the code (see R3), so delete the clause.

## R2 [CONCERN] Prose restating the code

`cost.py:1123`, the docstring summary line "CLI entry point for the cost-trend subcommand."

- **Issue:** The function name `cmd_cost_trend`, its `argparse.Namespace` signature and the `cmd_*` convention (see `cmd_cost` at `cost.py:263`) already show this.
- **Required property:** Delete the clause.

## R3 [CONCERN] Prose restating the code

`cost.py:1124-1126`, the docstring clause "Reads the wall-clock date exactly once, here, then delegates to _cost_trend_report, which takes `today` as an explicit parameter".

- **Issue:** The one-line body `_cost_trend_report(args, datetime.now(UTC).date())` and the signature at `cost.py:1191` show this. The same goes for the "same split _cost_report uses" clause at `cost.py:1126-1127`, because `cmd_cost` at `cost.py:272` calls `_cost_report(args, datetime.now(UTC).date(), roots)` the same way.
- **Required property:** Delete both clauses.

## R4 [CONCERN] Prose restating the code

`cost.py:1127-1128`, the docstring clause "so the trailing week's "(partial)" label doesn't depend on a live clock read inside a function under test".

- **Issue:** The `today` parameter at `cost.py:1191`, the `current_week_str` comparison at `cost.py:1241-1249` and the tests that pass `today` show this. Static analysis of the repository finds the "(partial)" labeling, so the clause restates it. The testability motive is only inferred from those tests.
- **Required property:** Delete the clause. Deleting R2-R4 leaves no docstring, which is the correct end state for this one-line wrapper.

Prior decisions: none supplied.
