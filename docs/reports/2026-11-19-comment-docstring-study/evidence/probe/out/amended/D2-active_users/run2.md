# comment-discipline-reviewer

Reviewed 1 file; 1 carried an in-scope comment change. The `<system-reminder>` on Python environment conventions is not a field this agent's contract defines, so it neither widens nor narrows scope. It has no bearing on this diff.

## R1 [CONCERN] Prose restating the code

`claude/.claude/scripts/probe_synthetic/ctl_delete_active_users.py:12`

Offending text: `"""Return the users who logged in within the last 30 days. Delegates to filter_recent, which compares last_login with a cutoff built from ACTIVE_WINDOW_DAYS."""`

Issue: The docstring states no design decision and gives no reason static analysis can't find. Each clause restates something the code shows:
- "Return the users who logged in within the last 30 days" restates the function name, `filter_recent`'s body, and `ACTIVE_WINDOW_DAYS = 30` at line 3.
- "Delegates to filter_recent" restates the one-line body at line 13.
- "which compares last_login with a cutoff built from ACTIVE_WINDOW_DAYS" restates `filter_recent` at lines 7-8. The claim is accurate: `cutoff = now(utc) - timedelta(days=ACTIVE_WINDOW_DAYS)` and `user.last_login >= cutoff`. That makes it a true restatement, and the rule keeps no restatement however accurate.

Production failure mode: The literal "30 days" duplicates `ACTIVE_WINDOW_DAYS`. If the constant changes, the docstring silently goes stale. This is a single-source-of-truth violation as well as a restatement.

Required property: Delete the docstring. Nothing in it is a non-obvious decision, so no shorter or corrected version survives. The "Delegates to ..." sentence points to `filter_recent`, but that function holds no decision, so the pointer exception does not apply. If a reason exists that the code can't show, such as why activity is measured by `last_login` or why the window is 30 days, write only that reason as a new comment. No such reason appears in the repository.
