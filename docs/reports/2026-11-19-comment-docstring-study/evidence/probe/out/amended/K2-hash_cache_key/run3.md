# comment-discipline-reviewer

No findings.

Scope: 1 file reviewed (`claude/.claude/scripts/probe_synthetic/ctl_keep_cache_key.py`), 1 with an in-scope comment change (the `hash_cache_key` docstring). The rules file in the system reminder governs Python environment setup and does not touch this review, so I set it aside.

Angles checked against the docstring (line 5 of the file at the diff's state):

- **Restating the code:** Both sentences state a design decision (sha256, truncation to 32 hex characters) with a reason from outside the repository, the CDN vendor's "Cache keys" page. Static analysis of the repo cannot find those reasons. Naming what each decision decides is not a restatement, so nothing is deleted.
- **Comment verbosity, multi-fact structure, paragraph readability:** Two sentences, each carrying one distinct fact with its reason. No narration, no run-on, no stacked rules.
- **PR-defined terminology, "used to be X" framing, durable-doc self-test:** Neither applies. The comment names no PR label and no prior version. The "rather than the faster blake2b" clause rules out an alternative reader might consider, not a previous implementation. The comment makes sense to a contributor who has not seen the PR.
- **False or unsourced claim:** The vendor-page claims name their source (the vendor's "Cache keys" page), and that source is outside the repository, so I cannot settle them by reading it. The code matches the claims: `hashlib.sha256` and `[:32]` are on line 6. No repo subject contradicts the docstring.
