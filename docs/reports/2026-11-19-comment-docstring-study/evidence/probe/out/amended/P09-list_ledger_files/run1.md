# comment-discipline-reviewer

## R1 [CONCERN] Restating the code

File: claude/.claude/scripts/transcript_analysis/author_outcome.py:303-306 (the `_list_ledger_files` docstring)

Issue: three of the docstring's four clauses state what static analysis, the standard library or the tests already show.

- "Every ledger file directly under ledger_dir, sorted by filename for a deterministic read order" restates `sorted(ledger_dir.glob("*.jsonl"))` and the function name. It is true, and still a restatement.
- "[] when the directory does not exist" is standard-library `Path.glob` behavior. `test_author_outcome.py:396` also asserts it. I cite it as a restatement, so I do not treat it as a false claim.
- "This is the index's only directory listing" is a repository-wide fact a grep settles. Its only caller is `_LedgerIndex.refresh` (`author_outcome.py:366`). It is true, and static analysis finds it.

Fix: delete those three clauses. Keep one sentence for the design decision, which is a separate function so tests can monkeypatch the listing to simulate a file vanishing between the listing and the read. Tests use the seam at `test_author_outcome.py:547`, `569` and `2636`, so the decision is real and the clause is accurate. For example: "A separate function so a test can replace the listing and simulate a file that vanishes between the listing and the read." That sentence names the subject, so the reason still says what it explains.

## Answers

Reviewed one file with one in-scope docstring. I found no false claim. Every settleable claim in the docstring checks out against the code and tests. I set aside no prompt text.

The harness attached a Python-environment rules file mid-session. It does not bear on this review, and I took no action on it.
