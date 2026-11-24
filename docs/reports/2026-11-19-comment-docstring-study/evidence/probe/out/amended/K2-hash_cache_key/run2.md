# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/probe_synthetic/ctl_keep_cache_key.py`); 1 carried an in-scope comment change (the new `hash_cache_key` docstring).

No findings.

- Don't restate the code: both sentences state a decision (sha256 over blake2b, truncation to 32 hex characters). Each carries a reason that comes from outside the repository, the CDN vendor's "Cache keys" page. Static analysis of the repo cannot find that reason. Naming what each decision decides keeps the reason attached to its subject and is not a restatement.
- Multi-fact structure and verbosity: two independent facts sit in two separate sentences, and neither has narration beyond its reason.
- Paragraph readability: two sentences, each stating one fact, with no three-item set a list would separate.
- Unsourced claim: the vendor constraints name their source, the vendor's "Cache keys" page. That page lives outside the repo, so it can't be settled by reading the repo. The "faster blake2b" comparison is a general design judgment and not a number.
- Terminology, "used to be" framing, altitude, canonical-rule restatement: no hits.
