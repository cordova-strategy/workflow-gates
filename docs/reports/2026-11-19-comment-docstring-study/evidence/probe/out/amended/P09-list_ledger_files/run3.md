# comment-discipline-reviewer

Reviewed 1 file (`author_outcome.py`); 1 added docstring in scope. I set aside the loaded `python-environment-conventions.md` reminder because it does not touch this review.

## R1 [CONCERN] Prose restating the code

`claude/.claude/scripts/transcript_analysis/author_outcome.py:303-306`, the new docstring on `_list_ledger_files`.

Offending text: "Every ledger file directly under ledger_dir, sorted by filename for a deterministic read order. [] when the directory does not exist. This is the index's only directory listing, so a test can stand in for a file that vanishes between the listing and the read."

Issue: three of the four clauses are findable by static analysis and violate the "Don't restate the code" rule.
- "Every ledger file directly under ledger_dir, sorted by filename" restates `sorted(ledger_dir.glob("*.jsonl"))`. A non-recursive glob and `sorted` are both visible on line 307.
- "[] when the directory does not exist" is standard-library behavior: `Path.glob` yields nothing for a missing directory. It is also asserted by `test_author_outcome.py:396`.
- "the index's only directory listing" is a settleable claim, and it is true. A grep of `author_outcome.py` finds one `glob` call (line 307) and one caller (line 366). A repository search finds the claim, so it restates the code. It is not a false claim.

The one clause that is a design decision is that the listing is its own function so a test can stand in for a file that vanishes between listing and reading. Test seams exist at `test_author_outcome.py:547`, `569` and `2636`. It states what was decided and why.

Required property: delete the first three clauses and keep one sentence naming the seam decision and its reason. For example: "Kept as its own function so a test can stand in for a file that vanishes between the listing and the read." Keep "the listing" in that sentence so the reason still names what it explains.

Prior decisions: none supplied.
