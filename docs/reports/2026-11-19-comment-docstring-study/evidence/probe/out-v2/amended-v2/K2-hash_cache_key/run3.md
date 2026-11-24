# comment-discipline-reviewer

Reviewed 1 file (`ctl_keep_cache_key.py`); 1 carried an in-scope change (the added docstring on `hash_cache_key`). No findings.

The context-attached `python-environment-conventions.md` reminder concerns Python dependency installs and does not change this review's scope, so I set it aside.

Sites checked against every angle:

- The docstring states two decisions (sha256 over blake2b, truncation to 32 hex characters). Each gives a reason outside the repository: the CDN vendor's "Cache keys" page. Static analysis of the repo cannot find that reason, so the rule under test keeps both.
- Each sentence carries one decision and its reason, so there is no verbosity, run-on or readability problem.
- The text has no PR-defined labels, no prior-version framing, and no restated code. It does not restate the code: the docstring names what was decided and why, not what `hexdigest()[:32]` does.
- The vendor claims (FIPS-approved digests only, a 32-byte limit) are unsettleable from the repo and name a source, the vendor's "Cache keys" page. That is a sourced claim, not an unsourced one. The 32-hex-character truncation is consistent with the 32-byte limit.

**No comment-discipline concerns**
