# comment-discipline-reviewer

Scope: 1 file reviewed (`claude/.claude/scripts/probe_synthetic/retry_backoff.py`), 1 in-scope change (the new `schedule_retry` docstring). I read the file at the diff's state. No prompt text was set aside.

## R1 [CONCERN] False or unsourced claim

`retry_backoff.py:5`. Offending text: "a lockout stalls every job sharing that key" and "The ceiling follows the vendor's "Rate limits" page".

- **Issue:** the stall claim is a cause-and-effect claim with no source. Nothing in the repo shows which jobs share a key (`Grep` for `MAX_BACKOFF_SECONDS|Rate limits|lock` found no such reference), and the vendor's page is not cited for it.
- **Issue:** the page is named only as "the vendor's 'Rate limits' page". A contributor can't tell which vendor or find the page. This also fails the survives-the-PR self-test.
- **Failure mode:** the comment states a consequence a future reader cannot verify, and the pointer doesn't resolve.
- **Required property:**
  - Name the vendor and the page URL, so the vendor's numbers have a source.
  - Either attribute the stall claim to a source (for example the doc or config that shows the jobs share a key) or delete it.
  - Suggested wording: `Vendor <name>'s "Rate limits" page (<URL>) locks a key out for an hour when a client retries faster than it allows.`

## R2 [CONCERN] False or unsourced claim (rationale does not match the code)

`retry_backoff.py:5-6`. Offending text: "locks a key out for an hour when a client retries faster" as the reason for the ceiling.

- **Issue:** `min(2 ** attempt, MAX_BACKOFF_SECONDS)` (line 6) caps the delay from above at 300 seconds. A cap on the delay does not protect against retrying too fast. Early attempts retry after 1s, 2s and 4s.
- **Issue:** a lockout for retrying faster would be prevented by a floor, not a ceiling. The stated reason therefore doesn't explain this constant.
- **Failure mode:** a reader trusts a rationale that doesn't match the mechanism. They may tune or remove the ceiling for the wrong reason.
- **Required property:** the author should check what the vendor page actually specifies and state the real reason for the 300-second cap. If the page requires a minimum retry interval, the comment should say so and the code should enforce it. I can't settle this from the repo because the page is external.

## R3 [CONCERN] Multi-fact comment structure

`retry_backoff.py:5`. Offending text: the first sentence chains three facts ("follows the vendor's page, which locks a key out for an hour when a client retries faster, and a lockout stalls every job sharing that key").

- **Issue:** the sentence runs together three independent facts. They are what sets the ceiling, what the vendor does on violation, and what a lockout costs here. Only the first two are tightly coupled.
- **Required property:** use one sentence per fact. The revisit trigger can stay as its own sentence, which it already is. Combined with R1, the fix is:
  `Vendor <name>'s "Rate limits" page (<URL>) sets this ceiling. The vendor locks a key out for an hour when a client violates it. Revisit if the vendor starts publishing per-account limits.`
  Add a stall sentence only if it gets a source.

## R4 [FYI] Wrong altitude

`retry_backoff.py:5`. The vendor-driven decision is about `MAX_BACKOFF_SECONDS` (line 1), but the docstring sits on `schedule_retry`.

- **Issue:** "The ceiling" has no referent inside the docstring, and the decision is attached to the wrong symbol.
- **Required property:** move the comment to a comment on the constant, where the value lives. Keep at most a pointer on the function.

## Prior decisions

None supplied.
