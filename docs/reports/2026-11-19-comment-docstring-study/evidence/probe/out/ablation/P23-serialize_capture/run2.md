# comment-discipline-reviewer

Reviewed 1 file (`routing_guard.py`); 1 carried an in-scope comment change (one added docstring).

## R1 [CONCERN] Prose restating the code

- File:line: `claude/.claude/scripts/transcript_analysis/routing_guard.py:693` (in `_serialize_capture`)
- Text: `"""ASCII-only, so the text encodes the same under any locale."""`
- Issue: The docstring clause states what `json.dumps` already does. The call at lines 694-708 passes no `ensure_ascii`, so the standard-library default (`True`) yields ASCII-only output. That is a fact the standard library finds, and the "same under any locale" consequence follows directly from it. Nothing in the clause names a decision this repository made or an outside constraint that forces it. No kept decision has this clause as its subject. The rule under test says to delete a docstring clause like this, and a shorter or corrected restatement would still restate.
- Failure mode: The clause adds no information a reader can't get from the code. It also describes a property the code never pins, because there is no explicit `ensure_ascii=True`. A later edit that adds `ensure_ascii=False` would leave the docstring false.
- Required property: Delete the docstring. If the ASCII guarantee is a real design requirement, pin it in code with an explicit `ensure_ascii=True` argument. Don't state it in prose. Add a comment only if an outside constraint forces it, and have the comment name that constraint.
