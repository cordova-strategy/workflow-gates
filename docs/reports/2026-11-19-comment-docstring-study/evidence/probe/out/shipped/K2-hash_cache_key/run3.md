# comment-discipline-reviewer

Reviewed 1 file (the diff); 1 carried an in-scope comment change (the new docstring on `hash_cache_key`). The `python-environment-conventions.md` text that arrived mid-session has no bearing on this review, so I set it aside.

## R1 [CONCERN] False or unsourced claim

File: `claude/.claude/scripts/probe_synthetic/ctl_keep_cache_key.py:5`

Offending text: "The digest is sha256 rather than the faster blake2b because the CDN vendor's "Cache keys" page accepts only FIPS-approved hex digests in the cache-key header. It is cut to 32 hex characters because the same page rejects header values longer than 32 bytes."

Issue: The docstring makes two cause-and-effect claims about an external vendor's behavior (accepts only FIPS-approved digests; rejects header values over 32 bytes). No source resolves them. The vendor is unnamed, there is no URL or doc version, and nothing in the repo confirms or refutes either. A `Grep` of the snapshot for "Cache keys", "FIPS", "32 bytes" and "cache-key" returns only this docstring. The claims are therefore unsettleable by reading the repository, which makes them unsourced rather than false.

Production failure mode: A future contributor cannot check whether the constraint still holds, so they can neither safely lift the 32-character truncation nor switch the hash. The rationale also cannot be trusted if the vendor changes its limits.

Required property: Each external-constraint claim names its source: the vendor's name plus the page URL or doc version. Failing that, mark the claim unverified, or drop the vendor rationale and keep only the non-obvious constraint (for example, "truncated to 32 hex chars to fit the CDN cache-key header limit"), with a source added.

## Not findings

- The two sentences each carry one fact and its reason. That is a tightly coupled pair, so there is no Multi-fact or Comment verbosity finding.
- No PR-defined labels and no "used to be X" framing.
