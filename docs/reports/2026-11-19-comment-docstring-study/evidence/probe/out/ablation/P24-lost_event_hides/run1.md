# comment-discipline-reviewer

## R1 [CONCERN] Prose restating the code

File: claude/.claude/scripts/transcript_analysis/routing_guard.py:864 (added docstring of `_lost_event_hides`).

Offending text: `"""`logged_at` is floored, so a row follows an event only past the event's whole second."""`

Issue: The docstring is one clause, and static analysis of this repository finds everything in it.
- `_LOG_LOGGED_AT_PATTERN` (routing_guard.py:166) accepts only whole-second `YYYY-MM-DDTHH:MM:SSZ` timestamps, so "floored" is visible in the repo.
- `math.floor(event_ts) < row.logged_at` at line 866 shows that a row counts only past the event's whole second.

The clause gives no reason that lives outside the repository, such as the recorder's second-resolution format. The rule under test deletes it even though it is true and takes several files to find. The reader of `_LostEventHides` can reconstruct it from the pattern constant, the `math.floor` call and the signature.

Production failure mode: none. The cost is a docstring that repeats the code and can drift from it.

Required property: Delete the docstring.
- If the author wants to keep the decision to floor the event time, the comment must name an external reason, such as the log recorder writing whole-second timestamps. It must not restate the repo-visible fact that `logged_at` is floored.
- A shorter or corrected restatement still restates.
- Other angles checked: the deletion leaves no wrong-altitude, PR-defined-label, "used to be", or false-claim issue.
