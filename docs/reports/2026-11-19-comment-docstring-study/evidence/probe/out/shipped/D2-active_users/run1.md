# comment-discipline-reviewer

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/probe_synthetic/ctl_delete_active_users.py`, the new docstring on `active_users` (diff line 8; line 12 in the snapshot).

Issue: The second sentence, "Delegates to filter_recent, which compares last_login with a cutoff built from ACTIVE_WINDOW_DAYS.", only repeats what the one-line body `return filter_recent(users)` and `filter_recent` (lines 6-8) already show. A comment may state only what is non-obvious from the code, and a restatement is deleted rather than shortened (CLAUDE.md §Durable text, "Don't restate the code").

I checked the claim and it is accurate. Line 7 builds `cutoff` from `ACTIVE_WINDOW_DAYS` and line 8 compares `user.last_login >= cutoff`. This is therefore not a false-claim finding. The accuracy does not save it from deletion.

Production failure mode: The docstring describes `filter_recent`'s internals, so it goes stale as soon as that function changes. Nothing in this file enforces the match.

Required property: Delete the second sentence. Keep only the contract of `active_users`. That contract is the next point.

The first sentence hard-codes "30 days", which duplicates `ACTIVE_WINDOW_DAYS = 30` (line 3). If the constant changes, the docstring is silently wrong (single source of truth, CLAUDE.md §Engineering Judgment). Either drop the number ("Return the users active within ACTIVE_WINDOW_DAYS.") or delete the docstring, since the function name already says what it returns.
