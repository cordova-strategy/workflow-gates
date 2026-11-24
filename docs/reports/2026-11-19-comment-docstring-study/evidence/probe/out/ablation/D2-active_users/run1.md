# comment-discipline-reviewer

Set aside: the `python-environment-conventions.md` rule reminder, which concerns installing Python dependencies and does not change this review's scope. I applied the session's replacement "Don't restate the code" bullet. The input was a diff path, and I read it fully. It adds one docstring, in `claude/.claude/scripts/probe_synthetic/ctl_delete_active_users.py`.

## R1 [CONCERN] Restating the code
File: `claude/.claude/scripts/probe_synthetic/ctl_delete_active_users.py:12`, clause 1.
Issue: the clause "Return the users who logged in within the last 30 days." restates what the function name, the `filter_recent` call and `ACTIVE_WINDOW_DAYS = 30` (line 3) already show. It names no design decision and gives no reason outside the code's reach.
Failure mode: the literal "30" duplicates `ACTIVE_WINDOW_DAYS`, so the prose goes stale if the constant changes.
Required property: delete the clause.

## R2 [CONCERN] Restating the code
File: `claude/.claude/scripts/probe_synthetic/ctl_delete_active_users.py:12`, clause 2.
Issue: the clause "Delegates to `filter_recent`" restates the function body at line 13, which is a single `return filter_recent(users)`.
Failure mode: it is a restatement that renaming or inlining the callee would silently falsify.
Required property: delete the clause. A pointer to a symbol that holds a decision would stay, but this one records no decision.

## R3 [CONCERN] Restating the code
File: `claude/.claude/scripts/probe_synthetic/ctl_delete_active_users.py:12`, clause 3.
Issue: the clause "which compares `last_login` with a cutoff built from `ACTIVE_WINDOW_DAYS`" restates `filter_recent` at lines 7-8. That is a doc passage on how the code works.
Failure mode: it describes the callee's internals in the caller's docstring, so the two drift apart when the callee changes.
Required property: delete the clause. Together with R1 and R2 this removes the whole docstring, since no non-obvious decision remains. I checked the claims with `Grep` and `Read` of the file, and the clauses are true, but a true restatement is still deleted under the rule.

No other angle fires. There is no PR-defined terminology, no prior-version framing and no wrong-altitude content. The clauses are true, so there is no false-claim finding.
