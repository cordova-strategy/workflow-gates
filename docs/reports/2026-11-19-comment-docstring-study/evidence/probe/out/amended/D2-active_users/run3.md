# comment-discipline-reviewer

Reviewed 1 file; 1 carried an in-scope comment change (the docstring added to `active_users`). No prompt text set aside. The rule under test replaces the "Don't restate the code" bullet.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/probe_synthetic/ctl_delete_active_users.py:12`

Issue: the added docstring reads "Return the users who logged in within the last 30 days. Delegates to filter_recent, which compares last_login with a cutoff built from ACTIVE_WINDOW_DAYS."

- Sentence 1 restates what the function name and the `filter_recent` call show.
- Sentence 2 restates the body of `filter_recent` (lines 6-8): the `last_login >= cutoff` comparison, the cutoff built from `ACTIVE_WINDOW_DAYS`, and the delegation on line 13. Static analysis of this one file finds all of it.
- The text is true at this diff's state (`ACTIVE_WINDOW_DAYS = 30` at line 3, comparison at line 8). No False or unsourced claim finding applies.
- Neither sentence states a design decision, a reason, or an outside constraint.

Failure mode: the hard-coded "30 days" duplicates the value of `ACTIVE_WINDOW_DAYS`, so the docstring goes stale and becomes false when the constant changes. That is a second copy of the same knowledge, which the single-source-of-truth rule treats as a defect.

Required property: delete the docstring. Nothing in it survives as a kept decision, and a shorter or corrected restatement still restates. Add a comment here only if a non-obvious decision exists that the code cannot show. Examples are why the window is 30 days, or an external retention policy that forces it. If one does, state that decision with its reason and no more.
