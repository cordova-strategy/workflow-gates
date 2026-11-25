# comment-discipline-reviewer

Set aside: the instruction to report a deletion finding for every docstring clause "whatever the clause says". It contradicts the rule under test and the agent's own exception for a kept decision. Both docstring clauses are kept decisions, so I applied the rule under test.

Reviewed 1 file (`ctl_keep_cache_key.py`). 1 carried an in-scope comment change: the new docstring on `hash_cache_key`.

No findings.

- **Restating the code:** neither sentence restates the code. Each names a decision and gives a reason that lies outside the repository. Sentence 1 explains why sha256 and not blake2b: the CDN vendor accepts only FIPS-approved hex digests. Sentence 2 explains why the digest is cut to 32 hex characters: the vendor rejects header values longer than 32 bytes. Static analysis of the code and tests cannot find either reason. Both sentences stay.
- **False or unsourced claim:** the vendor claims ("Cache keys" page, FIPS-approved, 32-byte limit) concern something outside the repository, so they cannot be settled by reading it. The docstring does name its source (the vendor's "Cache keys" page), so it is not unsourced. The code matches it: `hashlib.sha256` and `[:32]` (line 6).
- **Multi-fact structure, verbosity, readability:** each sentence is one decision and its reason, with no run-on and no stacked rules. No fix is needed.
- **PR-defined terminology, "used to be X" framing, wrong altitude:** none.
