# comment-discipline-reviewer

Set aside: the `python-environment-conventions.md` reminder that arrived mid-session. It governs Python dependency installs and has no bearing on this review.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/cursor-adapter/cursor-adapter.py:2266` (the only added line in the diff; the file was read in the unchanged snapshot at lines 2170-2320).

Offending text: `"""`uninstall` removes the install record right after the state directory, so a re-run cannot retry the removal."""`

Issue: The docstring describes how a different function, `uninstall`, sequences its steps. Static analysis of this file finds that sequence and its consequence. `remove_runtime_state(record)` runs at line 2197, and the unconditional `os.unlink` of `INSTALL_RECORD_NAME` follows at line 2206. On a re-run `record` is `None`, so `remove_runtime_state` is never called (lines 2196-2203). The claim is true, which makes it a restatement under the rule under test: the rule deletes anything static analysis finds, even when true and spread over several sites. The docstring also names no decision that `report_state_dir_left` itself makes, and the function is only a `print`. It sits at the wrong altitude too: a fact about `uninstall`'s ordering belongs at the `os.unlink` site, not on the reporting helper.

Production failure mode: None at runtime. The cost is a docstring that restates another function's control flow and goes stale silently if `uninstall`'s ordering changes.

Required property: Delete the docstring. The function name and its `Left {state_dir} in place: {reason} The engineer deletes it by hand.` message already state what it does. The "by hand" instruction is the visible consequence. Keeping the "why" at all would need a comment at line 2205 stating the decision to unlink the record regardless of whether the state dir was left, with a reason that static analysis cannot find. The diff supplies no such reason, so delete rather than relocate.
