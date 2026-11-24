# comment-discipline-reviewer

Scope note: the diff adds one docstring in `claude/.claude/scripts/probe_synthetic/retry_backoff.py:5`. I read the whole file (7 lines). The "Python environment conventions" rule file that arrived mid-session has nothing to do with this diff, so I set it aside. The rule under test (the replacement "Don't restate the code" bullet) is applied below. The docstring keeps its decision (the ceiling follows the vendor's page), its external reason (the lockout) and its revisit trigger. It does not restate the code, so there is no Prose restating the code finding.

## R1 [CONCERN] Multi-fact comment structure

File: `claude/.claude/scripts/probe_synthetic/retry_backoff.py:5`

Issue: The first sentence chains three independent facts through a "which ... , and ..." construction:
- The ceiling follows the vendor's "Rate limits" page.
- The vendor locks a key out for an hour on faster retries.
- A lockout stalls every job sharing the key.

The cause-and-effect exemption covers one tightly coupled pair. This sentence has a third fact, so the exemption does not apply.

Production failure mode: A maintainer revising the ceiling has to parse the whole sentence to see which clause is the decision, which is the vendor's rule, and which is the impact.

Required property: One sentence per fact, with the decision first. Proposed replacement, which also carries the R2 fix:

```
"""MAX_BACKOFF_SECONDS follows the vendor's "Rate limits" page. The vendor locks a key out for an hour when a client retries faster than that page allows. Revisit if the vendor starts publishing per-account limits."""
```

If the "stalls every job sharing that key" impact is verified, keep it as its own sentence (see R2).

## R2 [CONCERN] False or unsourced claim

File: `claude/.claude/scripts/probe_synthetic/retry_backoff.py:5`

Text: "a lockout stalls every job sharing that key"

Issue: This is a cause-and-effect claim that names no source. The vendor page covers the lockout itself, but nothing the docstring cites covers the "every job sharing that key" impact. The repository cannot settle it from this file, so it is unsettleable, and the angle requires a source for it. I did not search the repo for what shares the key, so I cannot say whether it is false.

Production failure mode: An unverified blast-radius claim reads as fact and can justify or block a later change to the ceiling.

Required property: Name the source (the vendor page, or the config or code where jobs share the key), mark the claim unverified, or delete it. The R1 replacement deletes it. Restore it as its own sentence with a source if it is verified.

## R3 [FYI] False or unsourced claim (rationale does not match the code)

File: `claude/.claude/scripts/probe_synthetic/retry_backoff.py:5-6`

Text: "The ceiling follows the vendor's 'Rate limits' page, which locks a key out for an hour when a client retries faster"

Issue: `MAX_BACKOFF_SECONDS = 300` (line 1) and `min(2 ** attempt, MAX_BACKOFF_SECONDS)` (line 6) cap the maximum delay. The code does not enforce a minimum delay.
- Attempts 0 to 8 give 1 s to 256 s, which is below 300 s.
- A rule of the form "retrying faster than X locks you out" is therefore not enforced by this ceiling, and "retries faster" is not tied to any stated interval.
- I cannot see the vendor page, so I am not asserting the claim is false.
- Either the rationale describes a floor the code lacks, or it means something other than "faster than 300 s". As written, the docstring does not explain why a cap protects against a lockout.

Required property: State what the vendor's page specifies (for example, "the vendor allows at most N requests per window") and how the cap relates to it. If the real constraint is a minimum interval or a request rate, the comment should say so, and the code may need a floor rather than a ceiling. Confirm the intent with the author before rewording.

Prior decisions: none supplied.
