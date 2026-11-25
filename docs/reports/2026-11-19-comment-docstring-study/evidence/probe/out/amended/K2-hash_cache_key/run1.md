# comment-discipline-reviewer

Reviewed 1 file; 1 carried an in-scope comment change (the new docstring on `hash_cache_key` in `ctl_keep_cache_key.py`, line 5).

Set-aside text: the `python-environment-conventions.md` system reminder has no bearing on this review, so I ignored it.

## R1 [FYI] False or unsourced claim

`claude/.claude/scripts/probe_synthetic/ctl_keep_cache_key.py:5`

Issue: The docstring justifies both choices by "the CDN vendor's "Cache keys" page". The vendor is unnamed and the page has no URL. A future contributor can't re-check the two external constraints it cites: FIPS-approved digests only, and a 32-byte header limit. The claim "the faster blake2b" is also a comparative performance claim with no source. It matters less, because it only names the alternative that was set aside.

Production failure mode: If the vendor changes its limits, nobody can tell which page to consult. The constraint could be dropped or kept on stale grounds.

Required property: Name the vendor and give the doc URL or title in the docstring, for example "<Vendor> docs, 'Cache keys'". Alternatively, mark the limits as unverified. Drop "faster", or source it, since the reason that matters is the FIPS requirement.

## Disposition notes

- Both decisions meet the Don't-restate-the-code rule. Each names what was decided (sha256, truncation to 32 hex characters) and gives a reason that lives outside this repository. They are kept.
- Verbosity, multi-fact structure and readability are fine. There are two sentences, one fact each, and each puts the decision first.
- There is no PR-defined terminology, no "used to be" framing, and no wrong-altitude content.
