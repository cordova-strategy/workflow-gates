# comment-discipline-reviewer

Scope note: I read the one file in the diff (`cost.py`) and checked the docstring's claims against it. The rules-file system reminder about Python environments has nothing to do with this review, so I set it aside and ignored it.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/cost.py:1123-1129` (the new `cmd_cost_trend` docstring).

Offending text:

> CLI entry point for the cost-trend subcommand.
> Reads the wall-clock date exactly once, here, then delegates to _cost_trend_report, which takes `today` as an explicit parameter — the same split _cost_report uses so the trailing week's "(partial)" label doesn't depend on a live clock read inside a function under test.

Issue: under the replacement "Don't restate the code" rule, most of this docstring says what static analysis already finds.
- "CLI entry point for the cost-trend subcommand" restates the function name.
- "Reads the wall-clock date exactly once, here" and "delegates to _cost_trend_report, which takes `today` as an explicit parameter" restate the one-line body (`cost.py:1130`) and the callee signature (`cost.py:1191`).
- "the same split _cost_report uses" is findable by reading `cmd_cost` (`cost.py:263-272`) and `_cost_report` (`cost.py:519`).
- The only non-obvious design decision is the reason `today` is injected at the CLI boundary. That reason is the "(partial)" label, which `cost.py:1241-1249` compares against `today`, and the label must not depend on a live clock under test.

The claims are true, so this is not a false-claim finding. I confirmed them at `cost.py:1130`, `1191`, `1241-1249` and `263-272`.

Production failure mode: none at runtime. The cost is comment noise, and future edits to the body or signature will drift from the narrated text.

Required property: delete the summary line and the mechanics narration. Keep one sentence that names the decision and its reason, with no restated mechanics. For example: "Takes `today` at the CLI boundary and passes it in so the trailing week's "(partial)" label is deterministic under test." Drop the "same split _cost_report uses" aside, or keep it only as a bare pointer such as "(as in cmd_cost)". The result is one sentence with no multi-fact or ordering problem.
