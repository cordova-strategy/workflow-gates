# comment-discipline-reviewer

Reviewed 1 file (`cursor-adapter.py`); 1 added docstring in scope. Text set aside: none.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/cursor-adapter/cursor-adapter.py:2266`

Issue: the added docstring reads "`uninstall` removes the install record right after the state directory, so a re-run cannot retry the removal."

The claim is true. Reading the code confirms it:
- Lines 2196-2198 call `remove_runtime_state(record)`.
- Line 2206 then unlinks `INSTALL_RECORD_NAME` unconditionally, even when the state directory was left in place.
- On a re-run, `record` is `None`, so `remove_runtime_state` is never reached (lines 2199-2200).

So this is not a False-claim finding.

Failure mode: the docstring describes `uninstall`'s ordering, not a decision made by `report_state_dir_left`. Static analysis of this repository finds that ordering by reading `uninstall` a few lines up, even though it spans two functions. Under the "Don't restate the code" rule, a clause the repo's code shows is deleted even when true. A reason that explains why the message tells the engineer to delete by hand is still findable in the repository, so it does not qualify as a reason static analysis cannot find. The function's name and body already show that it prints that the directory was left and who removes it.

Required property: delete the docstring. No outside-the-repository constraint forces the manual deletion, so nothing in it survives the rule. If the author wants a pointer for the reader, the only thing that would stay is a reference to the symbol that holds the decision (the record-unlink step in `uninstall`, line 2206). That pointer must not restate the ordering.
