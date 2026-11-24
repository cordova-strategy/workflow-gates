# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/author_outcome.py`); 1 carried an in-scope comment change. The `system-reminder` carrying `python-environment-conventions.md` is about installing Python dependencies and has no bearing on this review, so I set it aside.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/author_outcome.py:303-306` (new docstring on `_list_ledger_files`)

Offending text:

> Every ledger file directly under ledger_dir, sorted by filename for a deterministic read order. [] when the directory does not exist. This is the index's only directory listing, so a test can stand in for a file that vanishes between the listing and the read.

Issue: Under the "Don't restate the code" rule, only the last sentence's decision survives.
- Sentence 1 restates `sorted(ledger_dir.glob("*.jsonl"))`. The glob, its "directly under" scope and the sort all show in the one-line body, and "deterministic read order" is the plain reason for any `sorted`, not a reason static analysis cannot find.
- Sentence 2 restates standard-library behavior: `Path.glob` on a missing directory yields nothing. The test at `tests/test_author_outcome.py:396` already pins it.
- The clause "the index's only directory listing" in sentence 3 is a repository-wide fact that static analysis finds. I checked it and it is true: `author_outcome.py:307` holds the only `glob`, `iterdir`, `listdir`, `scandir`, `walk` or `rglob`, and `_LedgerIndex.refresh` at line 366 is the only caller. Being true does not keep it.
- The decision half of sentence 3 stays. The function exists as a seam so tests can monkeypatch it and simulate a file vanishing between listing and read. The tests do this at `tests/test_author_outcome.py:547`, `569` and `2636`.

Production failure mode: None at runtime. The cost is a docstring that restates the body twice over and buries the one decision, which a reader must pick out of three sentences.

Required property: Keep one sentence for the test-seam decision and delete the rest.

Concrete fix, replacing the whole docstring:

```python
    """A separate function so tests can monkeypatch it to simulate a file
    vanishing between the listing and the read."""
```

This is one tightly coupled fact with its reason. It adds no other angle's violation, and the claim it makes matches the tests that patch `_list_ledger_files`.

No other findings. I found no PR-defined terminology, prior-version framing or unsourced claims, and I found no false claim.
