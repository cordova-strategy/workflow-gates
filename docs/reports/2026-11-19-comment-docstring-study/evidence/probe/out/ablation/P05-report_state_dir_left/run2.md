# comment-discipline-reviewer

Scope note: I set aside nothing from the prompt. The `diff:` and `findings_path:` fields match the input contract. One file in the diff, `cursor-adapter.py`, carries one added docstring.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/cursor-adapter/cursor-adapter.py:2266`, inside `report_state_dir_left`.

Offending text: `"""`uninstall` removes the install record right after the state directory, so a re-run cannot retry the removal."""`

Issue: The docstring has one clause, and it restates code that static analysis of this repository finds.
- Line 2197 calls `remove_runtime_state(record)`.
- Line 2206 then unlinks `INSTALL_RECORD_NAME`, with only `reach("after-state")` between them.
- Lines 2199-2200 show the consequence on a re-run: a missing record prints "the runtime state may already have been removed by an earlier `uninstall`" and does not retry.
- The claim is true, so it draws no False-claim finding. It is findable from this file alone, so the "Don't restate the code" rule treats it as a restatement.
- It also describes `uninstall`'s sequencing, not what `report_state_dir_left` does. The function only prints a message.
- The existing message text already tells the reader the outcome ("The engineer deletes it by hand.").

Required property: Delete the docstring. It holds no clause that records a design decision with a reason static analysis cannot find, so nothing stays. The fix leaves `report_state_dir_left` with no docstring, which is consistent with the rule: the name, signature and message are self-explanatory. If you want the "no retry" fact kept as a decision, it belongs at the `os.unlink(... INSTALL_RECORD_NAME)` call site near line 2205. It would need a reason beyond the ordering itself, such as why the record is removed before the state directory is confirmed gone.
