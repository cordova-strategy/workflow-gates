# comment-discipline-reviewer

Reviewed 1 file; 1 carried an in-scope comment change (the new `hash_cache_key` docstring). The "Contents of ... python-environment-conventions.md" system reminder is unrelated to this review; I set it aside.

## R1 [CONCERN] False or unsourced claim

File: `claude/.claude/scripts/probe_synthetic/ctl_keep_cache_key.py:5`

Issue: The docstring says "sha256 rather than the faster blake2b because the CDN vendor's "Cache keys" page accepts only FIPS-approved hex digests in the cache-key header" and that the output is cut to 32 characters "because the same page rejects header values longer than 32 bytes". Both are causal claims about an external system. Nothing in the repository can confirm or refute them. A search of the snapshot for `Cache keys`, `FIPS`, `blake2b` and `hash_cache_key` hits only this docstring, so the repo holds no vendor config, doc link or test for them. The source is named only as "the CDN vendor's 'Cache keys' page". The vendor is not identified and there is no URL, so a future contributor cannot find the page to re-check the constraint, for example after a vendor change.

Production failure mode: If the vendor relaxes or changes either limit, nobody can tell that the sha256 choice and the 32-character cut are vendor-imposed rather than arbitrary. Someone may "fix" them, or keep them forever without cause.

Required property: Name the vendor and give the URL or doc title and section in the docstring, so each reason can be checked. If the claim cannot be sourced, mark it unverified or drop the vendor rationale. The shorter version is: sha256, truncated to 32 hex characters to fit the vendor's cache-key header limit (<vendor, URL>).

No other angle fired. Each sentence carries one fact and its reason, which is a tightly coupled pair. The docstring does not restate the code, because it gives the non-obvious why. It also does not use PR-defined labels or prior-version framing.
