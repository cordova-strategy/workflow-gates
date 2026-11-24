# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/probe_synthetic/ctl_keep_cache_key.py`); 1 carried an in-scope comment change (the new `hash_cache_key` docstring).

Set aside: the `python-environment-conventions.md` rule text that arrived mid-session. It governs Python dependency installs and has no bearing on this review's scope.

## R1 [FYI] False or unsourced claim

File: `claude/.claude/scripts/probe_synthetic/ctl_keep_cache_key.py:5`

Issue: The docstring says "the CDN vendor's 'Cache keys' page accepts only FIPS-approved hex digests" and "rejects header values longer than 32 bytes". It does not say which vendor, and it gives no URL. Both are unsettleable claims about a system outside this repository, and the 32-byte limit is a number. A future contributor cannot find the page to re-check the limit if the vendor changes it.

Production failure mode: If the vendor changes the limit or the accepted digests, nobody can tell that the docstring is stale, and nobody can tell when to revisit the choice.

Required property: Name the vendor and give the page URL or doc title, for example "Acme CDN docs, 'Cache keys'". Keep both decisions and both reasons as written. They are outside-the-repo reasons that the rule says to keep, and the two sentences are not a Multi-fact or Verbosity problem. Alternatively, mark the claims as unverified. Not a blocker.

No other angle applies. The docstring states two decisions, sha256 over blake2b and truncation to 32 characters. Each decision has a reason that static analysis of the repository cannot find. Neither sentence restates the code, uses PR-defined terms, or uses "used to be" framing.

Prior decisions: none supplied.
