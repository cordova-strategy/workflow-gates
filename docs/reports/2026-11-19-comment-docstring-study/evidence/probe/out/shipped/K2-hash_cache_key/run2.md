# comment-discipline-reviewer

Reviewed 1 file; 1 carried an in-scope comment change (`claude/.claude/scripts/probe_synthetic/ctl_keep_cache_key.py`, new docstring on `hash_cache_key`).

Set aside: the `python-environment-conventions.md` rules text that arrived mid-session. It is not a field this agent's contract defines and has no bearing on the diff's scope.

## R1 [FYI] False or unsourced claim

File: `claude/.claude/scripts/probe_synthetic/ctl_keep_cache_key.py:5`

Issue: the docstring states two external facts: the vendor "accepts only FIPS-approved hex digests in the cache-key header" and "rejects header values longer than 32 bytes". The only source given is "the CDN vendor's 'Cache keys' page". It names neither the vendor nor a URL. A future contributor can't find the page, and the page is the only authority for the 32 limit and the FIPS-only constraint. No file in the repo can settle either claim, so I could not verify them. They are unsettleable and I report no falsity. A grep of the snapshot for a vendor name or a doc reference would be needed to ground them, and I did not find one in the diff.

Required property: the source resolves for a reader who has not read the PR. Name the vendor and the page URL (or doc title and version), or mark the limits as unverified. Keep both rationale sentences, since each carries a distinct non-obvious fact.

## Checked, no finding

- Comment verbosity: two sentences, each one fact paired with its direct cause, in a single docstring. The rationale is non-obvious and does not repeat the code.
- Multi-fact structure: each sentence is a tightly coupled choice-and-reason pair. No stacked dashes or parentheticals.
- Restating the code: the docstring gives the reasons for `sha256` and `[:32]`, not what they do.
- PR-defined terminology, "used to be X" framing: none present. The "rather than the faster blake2b" clause is a design alternative, not a prior-version comparison.
