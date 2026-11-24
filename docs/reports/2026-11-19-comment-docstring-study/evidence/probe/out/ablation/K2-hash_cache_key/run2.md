# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/probe_synthetic/ctl_keep_cache_key.py`); 1 carried an in-scope docstring change.

No findings.

Notes on scope and judgment:

- The docstring has two sentences. Each states one design decision (sha256 over blake2b; truncation to 32 hex characters) and gives a reason that nothing in this repository or the standard library can show: the CDN vendor's "Cache keys" page constrains the header. Both meet the rule under test, so neither is Prose restating the code. Deleting either would lose a decision.
- The prompt says to report a restating finding for every docstring clause "whatever the clause says". I read that as bounded by the rule under test, which keeps decisions with an external reason. Applied literally, it would require deleting both clauses. Say so if you want the literal reading and I will re-run.
- False or unsourced claim: the vendor-page claims name their source ("Cache keys" page) and are unsettleable from the repo, so they draw no finding. The code agrees with the "32 hex characters" claim (`hexdigest()[:32]` at line 6).
- Multi-fact, verbosity, readability, PR-defined terminology, "used to be X" and the survives-the-PR self-test: none apply.
