# comment-discipline-reviewer

Scope note: the `python-environment-conventions.md` rule text that arrived mid-session governs installing Python dependencies and does not bear on this review. I set it aside.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/probe_synthetic/ctl_delete_active_users.py:12` (the only added line in the diff).

Issue: the new docstring reads "Return the users who logged in within the last 30 days. Delegates to filter_recent, which compares last_login with a cutoff built from ACTIVE_WINDOW_DAYS." It has two clauses, and both restate the code.
- Sentence 1 restates what the name `active_users`, the `filter_recent(users)` call and `ACTIVE_WINDOW_DAYS = 30` (line 3) show. The literal "30 days" also duplicates that constant, so the docstring goes stale if the constant changes.
- Sentence 2 restates the one-line body and `filter_recent` (lines 6-8). The `filter_recent` body at line 8 confirms the claims are true (`user.last_login >= cutoff`, cutoff = now − `ACTIVE_WINDOW_DAYS`). Static analysis of this file finds all of it, and the docstring names no design decision or outside constraint.

Production failure mode: none now, because the claims are accurate. This is future drift. A change to `ACTIVE_WINDOW_DAYS`, to the comparison, or to the delegation leaves the docstring wrong, and the code already says the same thing.

Required property: delete the whole docstring. A shorter or corrected restatement still restates, so no rewording of it is acceptable. Keep a docstring only if a non-obvious decision exists, such as why activity is measured by `last_login` or why the window is 30 days. The diff gives no such reason, and one can't be inferred, so nothing is left to keep.

False or unsourced claim: no finding. Every settleable claim in the docstring checks out against lines 3-8.

**Request changes** — R1: delete the docstring.
