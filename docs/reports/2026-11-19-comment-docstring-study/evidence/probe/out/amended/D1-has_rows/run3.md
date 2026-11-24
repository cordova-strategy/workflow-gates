# comment-discipline-reviewer

## R1 [CONCERN] Prose restating the code

- File:line: `claude/.claude/scripts/probe_synthetic/ctl_delete_has_rows.py:2`
- Issue: the added docstring `"""Return True when rows is not empty. Checks the length of the list. Returns a bool."""` has three sentences, and each restates what the code shows. `has_rows`, `len(rows) > 0` and the comparison's `bool` result already say all three. The docstring gives no design decision and no reason static analysis can't find.
- Production failure mode: none at runtime. The text adds reading cost, and it can drift from the body without anyone noticing.
- Required property: delete the docstring. Nothing is left to keep, because there is no kept decision for a subject clause to sit inside. A shorter or corrected restatement still restates.

Review scope: 1 file reviewed, 1 carried an in-scope comment change. No prompt text was set aside.
