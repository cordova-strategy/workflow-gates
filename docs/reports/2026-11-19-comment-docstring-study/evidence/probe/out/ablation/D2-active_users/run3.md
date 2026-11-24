# comment-discipline-reviewer

Scope: 1 file reviewed, 1 carried an in-scope change (a new docstring on `active_users`). No prompt text was set aside. The attached `python-environment-conventions.md` reminder does not bear on this review.

## R1 [CONCERN] Prose restating the code

`claude/.claude/scripts/probe_synthetic/ctl_delete_active_users.py:12`

Issue: the first docstring clause is "Return the users who logged in within the last 30 days." The name `active_users`, the call to `filter_recent`, `ACTIVE_WINDOW_DAYS = 30` (line 3) and the `user.last_login >= cutoff` test (line 8) already show this. The clause gives no design decision and no reason static analysis can't find. The "30 days" figure also duplicates `ACTIVE_WINDOW_DAYS`. I checked the claim against lines 3–8 and it is true, so this is not a False-claim finding.

Production failure mode: if `ACTIVE_WINDOW_DAYS` changes, the literal "30" goes stale.

Required property: delete the clause. No decision is left to keep.

## R2 [CONCERN] Prose restating the code

`claude/.claude/scripts/probe_synthetic/ctl_delete_active_users.py:12`

Issue: the second docstring clause is "Delegates to filter_recent, which compares last_login with a cutoff built from ACTIVE_WINDOW_DAYS." The body `return filter_recent(users)` and `filter_recent` (lines 6–8) show this directly. The clause is true, and a shorter or corrected version would still restate the code.

Production failure mode: the docstring has to be edited whenever `filter_recent`'s implementation changes.

Required property: delete the clause. With R1 applied, the whole docstring is removed.
