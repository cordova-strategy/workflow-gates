# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/probe_synthetic/ctl_delete_active_users.py`); 1 carried an in-scope comment change (one added docstring, two clauses).

## R1 [CONCERN] Prose restating the code

`ctl_delete_active_users.py:12`, first clause of the `active_users` docstring.

Issue: "Return the users who logged in within the last 30 days." The function name and its `filter_recent(users)` call show this. The `30` is `ACTIVE_WINDOW_DAYS = 30` (line 3) and the `>= cutoff` comparison (line 8) shows the window, so static analysis of this file finds the clause. Under the replacement rule, a true clause that static analysis finds is still a restatement. The clause also copies the constant's value into prose, so changing `ACTIVE_WINDOW_DAYS` would leave the docstring wrong.

Production failure mode: the hardcoded `30` drifts from the constant. The claim is true today, so there is no False-claim finding.

Required property: delete the clause. No design decision remains in it, such as why the window is 30 days or what outside the repository forces it.

## R2 [CONCERN] Prose restating the code

`ctl_delete_active_users.py:12`, second clause of the `active_users` docstring.

Issue: "Delegates to filter_recent, which compares last_login with a cutoff built from ACTIVE_WINDOW_DAYS." This describes how the code works. Line 13 shows the delegation, and lines 7-8 of `filter_recent` show the cutoff and comparison. The claim is true, and `filter_recent` is in the same file. The rule deletes it all the same. Naming `filter_recent` is not a pointer to a doc or symbol that holds a decision, because the clause only narrates the call.

Production failure mode: if `filter_recent` changes, such as to a different timestamp field or comparison, this clause goes stale with no check to catch it.

Required property: delete the clause. With R1 applied, the whole docstring goes and `active_users` keeps only its body. Nothing replaces it, because no non-obvious decision is stated.

## Notes

- The diff has no PR-defined terms, no prior-version framing, no restated canonical rule, no verbosity beyond the two clauses above, and no unsourced or false claims. I checked each fact in the docstring against the file: the constant is 30, `filter_recent` exists, and it compares `last_login` to a cutoff built from `ACTIVE_WINDOW_DAYS`.
- I ignored the Python-environment-conventions system reminder because it covers installing dependencies and has no bearing on this diff.
