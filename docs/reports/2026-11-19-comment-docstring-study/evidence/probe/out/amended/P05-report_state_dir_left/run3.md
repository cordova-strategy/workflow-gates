# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/cursor-adapter/cursor-adapter.py`); 1 carried an in-scope comment change (one added docstring).

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/cursor-adapter/cursor-adapter.py:2266` (docstring of `report_state_dir_left`).

Issue: the docstring reads "`uninstall` removes the install record right after the state directory, so a re-run cannot retry the removal." It describes the caller's control flow, not `report_state_dir_left`.

- `run_uninstall` calls `remove_runtime_state(record)` at line 2197, reaches `after-state`, and unlinks `INSTALL_RECORD_NAME` at line 2206.
- A re-run finds `record_or_none()` returning None, so it takes the "install record is missing, so the runtime state may already have been removed" branch at lines 2199-2200 and never calls `remove_runtime_state`.

The claim is true, so it draws no False-claim finding. Static analysis of this one file finds it, even though it takes three sites to do so. The rule under test says to delete such clauses even when they are true and span several places. The text names no outside-the-repo force and no decision that static analysis cannot find.

Required property: delete the docstring. The function name and the printed message ("The engineer deletes it by hand.") already carry the function's behavior. If the maintainers want the no-retry consequence kept, it belongs as a comment at the `os.unlink` of the install record (line 2205-2206) in `run_uninstall`, which is the site that makes the decision. It does not belong in this print helper.
