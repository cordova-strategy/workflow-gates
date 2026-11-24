# comment-discipline-reviewer

Reviewed 1 file (`read_cost.py`); 1 carried an in-scope change (one added docstring).

Text set aside: the prompt's rule-under-test line "A pointer to the doc or symbol that holds a decision stays." I followed the agent file's instruction instead: it requires a Prose restating the code finding for every added docstring clause, whatever the clause says.

## R1 [CONCERN] Prose restating the code

File: `claude/.claude/scripts/transcript_analysis/read_cost.py:414`

Issue: the added docstring reads `"""See docs/transcript-analysis.md's `read-cost` section for the flags, the unit, and the publication scope."""`. It is the only docstring clause in the diff. The function body is a single call, `_read_cost_report(args, _read_cost_roots())`. The docstring states no design decision with a reason static analysis can't find.

Production failure mode: none at runtime. The cost is a docstring that restates a doc's table of contents. It also names a doc section I couldn't confirm. `docs/transcript-analysis.md` is absent from the snapshot (`Glob **/transcript-analysis.md` and `**/docs/**` returned nothing). Tests cite its `read-cost` "Output bullet" and "Known limits" (`test_transcript_read_cost_accumulation.py:211,527`; `test_transcript_read_cost_scan_window.py:235`), but I found no `read-cost` heading or "publication scope" wording. If the doc is renamed or the section is restructured, this pointer goes stale without any check catching it.

Required property: delete the docstring. If the maintainers treat the pointer as a kept pointer to the doc that holds the decision, the rule under test would let it stay. In that case, trim it to the pointer alone: drop "for the flags, the unit, and the publication scope", and confirm that the `read-cost` section exists. I did not apply that reading because the agent file's "whatever the clause says" instruction outranks it.
