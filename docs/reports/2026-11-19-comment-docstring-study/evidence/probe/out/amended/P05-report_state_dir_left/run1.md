# comment-discipline-reviewer

Reviewed 1 file (`cursor-adapter.py`); 1 added docstring in scope. Scope note: the dispatch prompt's replacement "Don't restate the code" bullet governs the Restating-the-code angle, as instructed.

## R1 [CONCERN] Restating the code

File: claude/.claude/scripts/cursor-adapter/cursor-adapter.py:2266 (added docstring on `report_state_dir_left`)

Offending text: "`uninstall` removes the install record right after the state directory, so a re-run cannot retry the removal."

Issue: The docstring does not state a decision `report_state_dir_left` makes. It describes the ordering of a different function's steps, and static analysis of this file finds that ordering. In the `uninstall` body, `remove_runtime_state(record)` runs at line 2197. `reach("after-state")` follows, then `os.unlink(os.path.join(directory, INSTALL_RECORD_NAME))` at 2206. With the record gone, `record` is `None` on a re-run, so only the branches at 2199-2203 run and nothing retries the removal. The replacement rule deletes every clause that code and tests show, even one that takes several functions to trace. The claim is true, so there is no False-claim finding. I checked it against 2197-2206 and 2199-2203.

Production failure mode: The docstring goes stale if `uninstall` is reordered or gains a retry path. It would then misdescribe a function it is not attached to.

Required property: Delete the docstring. The function is a one-line print whose message ("The engineer deletes it by hand") already tells the reader what happens. If a pointer to the ordering is wanted, a comment at the `os.unlink(... INSTALL_RECORD_NAME)` site in `uninstall` could say why the record is removed unconditionally. That would be a separate, new decision comment and is not required.
