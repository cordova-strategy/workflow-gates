# comment-discipline-reviewer

Scope note: the dispatch prompt names no sites or scope that contradicts the agent file, so none was set aside. One file reviewed (`cursor-adapter.py`), one docstring added. The session's replacement "Don't restate the code" bullet was applied.

## R1 [CONCERN] Prose restating the code

File and line: `claude/.claude/scripts/cursor-adapter/cursor-adapter.py:2266`, the docstring on `report_state_dir_left`.

Offending text: "`uninstall` removes the install record right after the state directory, so a re-run cannot retry the removal."

Issue: The clause describes the order of steps in `run_uninstall`, a different function. Static analysis of this repository's code finds that order: `remove_runtime_state(record)` at line 2197, then `reach("after-state")` at 2204, then `os.unlink(... INSTALL_RECORD_NAME)` at 2206. It also finds the re-run consequence: with the record gone, `record_or_none()` returns None and the branch at line 2200 prints "may already have been removed by an earlier `uninstall`". I read these lines and the clause is true, but the rule says to delete a clause that static analysis finds, even when it is true and spans several functions. The docstring states no decision with a reason static analysis cannot find. The "why" it gives is derivable from `run_uninstall`.

Production failure mode: None at runtime. Over time, the claim is a second statement of `run_uninstall`'s step order that lives in an unrelated helper. It goes stale silently if that order changes.

Required property: Delete the docstring. The rule says to delete a restatement, not shorten it. The only clause in the diff is this one, so nothing stays. The function's remaining text ("Left … in place: {reason} The engineer deletes it by hand.") already tells the reader the outcome.

Checked against other angles: deleting adds no new violation. The docstring is not a kept decision's subject, so no subject needs to be kept inside a decision sentence. It also draws no False or unsourced claim finding, because it is true at the diff's state and a clause that restates the code is handled here.
