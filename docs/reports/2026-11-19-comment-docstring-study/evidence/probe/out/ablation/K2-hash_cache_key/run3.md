# comment-discipline-reviewer

Set aside: the dispatch's blanket "report a Prose restating the code finding for every docstring clause, whatever it says" does not apply to clauses that are kept decisions under the rule under test, which keeps a decision naming what was decided and an outside-the-repository reason.

Reviewed 1 file; 1 carried an in-scope comment change (`claude/.claude/scripts/probe_synthetic/ctl_keep_cache_key.py`, the added docstring on `hash_cache_key`, line 5).

No findings.

- Sentence 1 (sha256 over blake2b): a decision with an external reason (the CDN vendor's "Cache keys" page accepts only FIPS-approved hex digests). Static analysis cannot find that reason, so it stays.
- Sentence 2 (cut to 32 hex characters): a decision with an external reason (the same page rejects header values longer than 32 bytes). It stays. It is consistent with `[:32]` on a hex digest at line 6, where each hex character is one byte.
- Each sentence carries one fact, so there is no Multi-fact or Paragraph readability finding. The docstring is two sentences, so there is no verbosity finding.
- No PR-defined label, prior-version framing or canonical-rule restatement is present. The vendor claims name their source (the "Cache keys" page) and are unsettleable from the repository, so no False or unsourced claim finding applies.

**No comment-discipline concerns**
