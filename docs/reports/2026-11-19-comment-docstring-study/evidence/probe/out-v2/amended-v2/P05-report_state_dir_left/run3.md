# comment-discipline-reviewer

Set aside: the Python-environment-conventions system reminder is unrelated to this review's scope, so it changes nothing here.

Reviewed 1 file (`claude/.claude/scripts/cursor-adapter/cursor-adapter.py`); 1 comment change in scope (one added docstring).

## R1 [CONCERN] Restating the code

File and line: `claude/.claude/scripts/cursor-adapter/cursor-adapter.py:2266`

Issue: the added docstring reads "`uninstall` removes the install record right after the state directory, so a re-run cannot retry the removal." It describes the control flow of another function, not a decision made in `report_state_dir_left`. Static analysis of this file finds every part of that flow:
- `uninstall` calls `remove_runtime_state(record)` at line 2197, then unlinks the install record at line 2206.
- A re-run with no record reaches the branch at lines 2199-2200, which only prints and never calls `remove_runtime_state`.

The docstring also never says what the function decides. The decision is to leave the directory and tell the engineer to delete it by hand, and that decision is stated only by the print on line 2267. The ordering fact sits in the wrong function: it is a property of `uninstall`'s sequence at 2196-2206, and its only readers there are `uninstall` maintainers.

Production failure mode: a maintainer who reorders `uninstall` so the record is removed later, or who makes the record removal conditional, has no pointer from `uninstall` to this docstring. The docstring then silently goes false, and the "delete it by hand" instruction stays when it no longer applies. A docstring that restates the ordering is also a second place that has to track the ordering.

Required property: the docstring names the decision it explains, gives the reason in the same sentence, and leaves out the walk through `uninstall`'s sequence. Fix, one sentence: `"""Tells the engineer to delete the state directory by hand, because `uninstall` drops the install record next and a re-run could no longer locate the directory."""` Under the strict rule, the part after "because" is still code-findable. If you judge that intent-to-consequence link to be static-findable, delete the docstring, since the print already states the instruction. Do not keep the current wording either way.

Prior decisions: none supplied.
