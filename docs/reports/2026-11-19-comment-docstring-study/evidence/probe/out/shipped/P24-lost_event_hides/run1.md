# comment-discipline-reviewer

Reviewed 1 file (`routing_guard.py`); 1 carried an in-scope comment change (the new docstring on `_lost_event_hides`, line 864).

No comment-discipline concerns.

- Claim checked: "`logged_at` is floored". The reader's `_LOG_LOGGED_AT_PATTERN` (routing_guard.py:166) accepts only whole-second `...SSZ` values. Test cases at test_transcript_routing_guard_capture.py:4224-4225 reject fractional and offset forms, so the subject supports the claim. I could not read the writer, `record-session-config-keys.sh`, because it is not in the snapshot.
- Shape: one cause-and-effect sentence stating the non-obvious reason for `math.floor(event_ts) < row.logged_at`. It does not restate the code, carries no PR-defined label and has no prior-version framing.
