# comment-discipline-reviewer

Set aside: the system reminder carrying `python-environment-conventions.md` bears on installing Python dependencies, not on this review, so I applied none of it.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/cursor-adapter/cursor-adapter.py:2266` (the only added line in the diff, in `report_state_dir_left`).

Offending text: `"""`uninstall` removes the install record right after the state directory, so a re-run cannot retry the removal."""`

Issue: The docstring states a fact that static analysis of this file already shows. In `uninstall`, `remove_runtime_state(record)` runs at lines 2196-2198. Lines 2205-2206 then unconditionally `os.unlink` the install record, whether or not the state directory was left. On a re-run, lines 2199-2202 take the missing-record branch and print that the state "could not be located" or "may already have been removed". No retry path exists. That is a consequence readable from `uninstall` in the same file, so it carries no reason that static analysis cannot find. The rule under test deletes such a clause "even if it is true and takes several files to find".

The claim is accurate when read at the diff's state (lines 2197-2206 and 2199-2202), so this is not a False-claim finding. The docstring also describes the caller's behaviour instead of what `report_state_dir_left` does, and it is true only while `uninstall` keeps that ordering. A later reorder would leave it stale with nothing flagging it.

Required property: The function carries no docstring. The `print` already states the decision: the state directory is left in place and the engineer deletes it by hand.

Concrete fix: Delete the added docstring line. If the author wants to keep the reason for "by hand", a pointer that names the code holding the reason is the most the rule allows, for example `# Why by hand: uninstall unlinks INSTALL_RECORD_NAME right after remove_runtime_state, so no re-run can locate the state directory.` I recommend deletion, because that pointer still restates the ordering visible in `uninstall`.

No prior decisions were handed over for this review.
