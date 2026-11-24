# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/read_cost.py`). 1 file carried a docstring change in scope.

Set aside: the rule-under-test sentence "A pointer to the doc or symbol that holds a decision stays." The agent file requires a Prose restating the code finding for every docstring clause "whatever the clause says", and the two conflict on this one clause. The agent file wins, so R1 is reported. The dispatcher should decide whether the pointer carve-out overrides it.

## R1 [CONCERN] Prose restating the code

File:line: `claude/.claude/scripts/transcript_analysis/read_cost.py:414`

Issue: the added docstring on `cmd_read_cost` reads `"""See docs/transcript-analysis.md's `read-cost` section for the flags, the unit, and the publication scope."""`. It is the function's only docstring clause. The function body is one line that delegates to `_read_cost_report(args, _read_cost_roots())`. The clause states no decision with a reason that static analysis cannot find. Its trailing part, "for the flags, the unit, and the publication scope", summarizes what the doc section contains, and reading the doc finds that.

Production failure mode: none beyond drift. The summary list can go stale when the doc section is reorganized, and it adds nothing to the pointer.

Required property: delete the docstring clause. The pointer's target is real. `docs/transcript-analysis.md:1577` is `## read-cost`, with Flags (line 1581), Unit (line 1586) and Output, "Aggregates only" (line 1595). The summary list is therefore not false, just redundant. If the dispatcher keeps the pointer under the rule-under-test carve-out, trim it to the pointer alone: `See docs/transcript-analysis.md's `read-cost` section.` Drop the "for the flags, the unit, and the publication scope" list.

Notes:
- The target doc is not in the review snapshot. I verified it in `/home/<username>/MyCode/claude-config/docs/transcript-analysis.md`.
- No other angle applies. The docstring has no PR-defined label, no "used to be" framing and no unsourced number. It is one sentence, so the verbosity, multi-fact and paragraph-readability angles do not apply.
