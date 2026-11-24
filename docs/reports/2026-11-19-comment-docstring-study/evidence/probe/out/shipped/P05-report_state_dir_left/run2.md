# comment-discipline-reviewer

Reviewed 1 file (`cursor-adapter.py`); 1 carried an in-scope change, the new docstring on `report_state_dir_left` (diff line 8).

No findings.

- Claim check, the docstring's one settleable claim: "`uninstall` removes the install record right after the state directory, so a re-run cannot retry the removal."
  - `cursor-adapter.py:2197-2198` calls `remove_runtime_state(record)`, which returns False after `report_state_dir_left`.
  - `cursor-adapter.py:2206` then unlinks `INSTALL_RECORD_NAME` unconditionally. Only `reach("after-state")` sits between the two calls.
  - A re-run reads no record at `cursor-adapter.py:2199-2202`, so it cannot locate the state directory. The claim holds.
- Not restating the code: the cross-function fact (why the message tells the engineer to delete by hand) is not visible from the function body.
- Not multi-fact or verbose: one sentence, one cause-and-effect pair.
- No PR-defined label, prior-version framing or unsourced number.
