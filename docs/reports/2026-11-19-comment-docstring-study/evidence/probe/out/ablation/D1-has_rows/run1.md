# comment-discipline-reviewer

Reviewed 1 file; 1 carried an in-scope comment change (the docstring on `has_rows`). The prompt's text set aside: none.

## R1 [CONCERN] Prose restating the code

`claude/.claude/scripts/probe_synthetic/ctl_delete_has_rows.py:2`

Issue: the clause `Return True when rows is not empty.` restates `return len(rows) > 0` and the function name `has_rows`.

Production failure mode: none at runtime. The docstring adds a second statement of the behavior that must stay in sync with the code.

Required property: delete this clause. It records no design decision and no outside constraint.

## R2 [CONCERN] Prose restating the code

`claude/.claude/scripts/probe_synthetic/ctl_delete_has_rows.py:2`

Issue: the clause `Checks the length of the list.` restates `len(rows)`. The "list" claim also does not appear in the code, which accepts any sized container.

Production failure mode: the docstring can mislead a reader about accepted types.

Required property: delete this clause. Nothing is left to correct or shorten, because a corrected restatement still restates.

## R3 [CONCERN] Prose restating the code

`claude/.claude/scripts/probe_synthetic/ctl_delete_has_rows.py:2`

Issue: the clause `Returns a bool.` restates the `> 0` comparison, which a reader sees yields a bool.

Production failure mode: none at runtime. It is noise that must be maintained.

Required property: delete this clause. With R1–R3 applied, the whole docstring goes and the function body stays alone. No clause states a decision, so there is nothing to keep.
