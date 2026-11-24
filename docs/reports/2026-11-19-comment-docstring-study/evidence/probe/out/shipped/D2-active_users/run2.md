# comment-discipline-reviewer

Reviewed 1 file; 1 carried an in-scope comment change (the new docstring on `active_users`).

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/probe_synthetic/ctl_delete_active_users.py:12`

Issue: The docstring is `"""Return the users who logged in within the last 30 days. Delegates to filter_recent, which compares last_login with a cutoff built from ACTIVE_WINDOW_DAYS."""`.

- The second sentence restates the code.
  - "Delegates to filter_recent" repeats the one-line body `return filter_recent(users)` (line 13).
  - "compares last_login with a cutoff built from ACTIVE_WINDOW_DAYS" repeats the body of `filter_recent` (lines 7-8). I read it and the sentence is accurate, so this is a restatement, not a false claim.
- The first sentence's "30 days" copies the value of `ACTIVE_WINDOW_DAYS = 30` (line 3). If the constant changes, the docstring turns false without anyone noticing. This breaks the single-source-of-truth rule in CLAUDE.md §Engineering Judgment.
- The docstring also puts two facts in one very long single-line string.

Production failure mode: When someone changes `ACTIVE_WINDOW_DAYS`, `active_users` documents the wrong window. Readers also pay for a second sentence that tells them nothing the code doesn't.

Required property:
- Delete the second sentence.
- Keep one sentence that defines "active" without hardcoding the number, for example: "Users whose `last_login` falls within `ACTIVE_WINDOW_DAYS`."
- If you judge that even this restates `filter_recent`, delete the docstring entirely.
