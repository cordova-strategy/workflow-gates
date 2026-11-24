# comment-discipline-reviewer

Scope: 1 file reviewed (`claude/.claude/scripts/transcript_analysis/read_cost.py`), 1 added docstring in scope (`cmd_read_cost`, line 414). The `python-environment-conventions.md` rules block that arrived mid-session governs Python installs, not comment review, and I set it aside.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/read_cost.py:414`

Text: `"""See docs/transcript-analysis.md's `read-cost` section for the flags, the unit, and the publication scope."""`

Issue: The docstring states no decision. It is a table of contents for the doc. Two of its three items fall under the rule's "delete" clause:
- "The flags" are what the subparser registration in this module already shows.
- "The unit" is a feature description that the module docstring (lines 1-3) and the report code carry.

Only "the publication scope" names a decision: no wider scope than one account's current repo, and aggregate-only output. The code already enforces it in `_refuse_wider_scope` (lines 396-410). The error message at line 400 and the module docstring (lines 5-6) already point to `docs/transcript-analysis.md` for it.

Production failure mode: The three-item list tells a reader what the doc covers and not why the command behaves as it does. It will drift as the doc's section list changes, and it adds a second pointer to a decision that two other sites already point to.

Required property: Keep the pointer only for the decision it holds, and drop the list of flags and unit. Proposed replacement:

`"""Refuses any scope wider than one account's current repository; the reason is in docs/transcript-analysis.md's `read-cost` section."""`

If the reason is not in that section, delete the docstring. The module docstring and `_refuse_wider_scope` already cover the decision.

## R2 [FYI] False or unsourced claim (unverified, no finding)

File: `claude/.claude/scripts/transcript_analysis/read_cost.py:414`

Issue: The docstring claims `docs/transcript-analysis.md` has a `read-cost` section covering flags, the unit and the publication scope. That claim is settleable, but the snapshot has no `docs/` directory, so I could not read the subject.

Evidence:
- `Glob **/docs/**` returned nothing.
- `Glob **/transcript-analysis.md` returned nothing.
- Sibling comments cite "docs/transcript-analysis.md's read-cost Output bullet" (`test_transcript_read_cost_accumulation.py:211`) and "read-cost Known limits" (`test_transcript_read_cost_accumulation.py:527`, `test_transcript_read_cost_scan_window.py:235`). These suggest a read-cost section exists, but they are not the doc itself.
- Under the rule, only the subject can contradict a claim, so I report no finding.

Required property: Before merge, confirm that the section exists under that heading and holds the reason for the publication scope. R1's replacement depends on it.
