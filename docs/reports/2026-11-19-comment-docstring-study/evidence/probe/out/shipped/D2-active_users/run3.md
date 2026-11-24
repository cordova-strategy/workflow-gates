# comment-discipline-reviewer

Set aside: the `python-environment-conventions.md` system reminder. It concerns installing Python dependencies and does not bear on this review.

Reviewed 1 file (`claude/.claude/scripts/probe_synthetic/ctl_delete_active_users.py`). 1 carried an in-scope comment change (the new `active_users` docstring).

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/probe_synthetic/ctl_delete_active_users.py:12`

Issue: the added docstring is `"""Return the users who logged in within the last 30 days. Delegates to filter_recent, which compares last_login with a cutoff built from ACTIVE_WINDOW_DAYS."""`.
- The second sentence restates the body. `return filter_recent(users)` already shows the delegation. `filter_recent` at lines 6-8 already shows the `last_login >= cutoff` comparison and the `ACTIVE_WINDOW_DAYS` cutoff.
- The first sentence restates the name `active_users` plus the constant `ACTIVE_WINDOW_DAYS = 30` (line 3).
- The hardcoded "30 days" duplicates that constant. It becomes false the moment the constant changes, which breaks the single-source-of-truth rule.

Production failure mode: the docstring drifts silently from `ACTIVE_WINDOW_DAYS`, and a reader gets a stale window or a stale description of `filter_recent`'s internals.

Required property: delete the docstring. Nothing in it is non-obvious from the name, the body, and the constant. If a definition of "active" must stay, make it one sentence that names `ACTIVE_WINDOW_DAYS` and carries no literal.

False or unsourced claim check: every claim was verified against the file and is true at the diff's state.
- `ACTIVE_WINDOW_DAYS` is 30 (line 3).
- `filter_recent` builds its cutoff from `ACTIVE_WINDOW_DAYS` (line 7) and compares `last_login` (line 8).
- `active_users` delegates to it (line 13).
No finding on that angle.
