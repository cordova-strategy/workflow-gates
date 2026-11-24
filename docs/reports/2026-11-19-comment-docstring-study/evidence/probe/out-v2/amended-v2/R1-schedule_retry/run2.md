# comment-discipline-reviewer

Set aside: the `python-environment-conventions.md` system reminder, which is unrelated to this diff's scope. Reviewed 1 file (`retry_backoff.py`), 1 with an in-scope comment change (the new `schedule_retry` docstring).

## R1 [CONCERN] Multi-fact comment structure

`claude/.claude/scripts/probe_synthetic/retry_backoff.py:5`

Offending text: `The ceiling follows the vendor's "Rate limits" page, which locks a key out for an hour when a client retries faster, and a lockout stalls every job sharing that key.`

Issue: the first sentence chains three independent facts through a `which` clause and an `and` clause. The facts are that the ceiling follows the vendor page, that faster retries lock the key out for an hour, and that a lockout stalls every job on that key. The second fact is the vendor's rule and the third is a consequence of it, so only a cause-and-effect pair could share a sentence, and the first fact is a third item.

Production failure mode: a reader has to parse the whole sentence to find where the decision (the ceiling value follows an external limit) ends and the supporting facts begin.

Required property: one sentence per fact, decision first. The second sentence (the revisit trigger) stays as written. Proposed replacement:

> `MAX_BACKOFF_SECONDS` follows the vendor's "Rate limits" page. That page says a client retrying faster than its limit is locked out for an hour. Revisit the ceiling if the vendor starts publishing per-account limits.

Writing `MAX_BACKOFF_SECONDS` in place of "The ceiling" names what was decided. The proposed text drops the "stalls every job" clause, which R2 covers.

## R2 [CONCERN] False or unsourced claim

`claude/.claude/scripts/probe_synthetic/retry_backoff.py:5`

Offending text: `a lockout stalls every job sharing that key`

Issue: this is a cause-and-effect claim that names no source. Reading the repository does not settle it. `Grep` for `schedule_retry`, `MAX_BACKOFF_SECONDS` and `Rate limits` across the snapshot finds only `retry_backoff.py:1,4,5,6`. There is no caller, job runner or key-sharing config for it to rest on. The vendor is also unnamed, so a future reader cannot locate the cited "Rate limits" page. The "locks a key out for an hour" claim is unsettleable too, but it names its source (the vendor page), so it draws no finding beyond the unnamed vendor.

Production failure mode: if jobs do not in fact share a key, or the vendor's lockout does not block others, the comment misstates the cost of crossing the limit. The reason for the ceiling is that cost.

Required property: do one of the following.
- Name the source for the shared-key effect, for example the config or doc that shows jobs sharing a key.
- Mark it unverified.
- Delete the clause and keep the vendor-page reason, as in the R1 replacement.

Also name the vendor, or give the page URL, next to "Rate limits".

## Notes

The second sentence, `Revisit the ceiling if the vendor starts publishing per-account limits.`, is a revisit trigger, so it stays under the rule. The decision-plus-reason framing, which is why it is this way and what outside the repo forces it, is the kind of content the rule keeps. No other angle applies: there is no PR-defined label, no prior-version framing, and no restatement of the code (the `min(2 ** attempt, ...)` body is not described).
