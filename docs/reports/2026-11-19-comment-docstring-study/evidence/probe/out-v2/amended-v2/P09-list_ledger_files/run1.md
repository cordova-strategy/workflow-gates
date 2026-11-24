# comment-discipline-reviewer

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/author_outcome.py:303-306`

Issue: The new docstring on `_list_ledger_files` states four things. Each is something the code, its tests or the standard library already shows, and none gives a reason static analysis cannot find.

- "Every ledger file directly under ledger_dir": this is `ledger_dir.glob("*.jsonl")` at line 307. It is also loose, because the glob matches `.jsonl` only, and `test_author_outcome.py:391,393` shows a `.jsonl.lock` file is excluded.
- "sorted by filename for a deterministic read order": this is `sorted(...)` at line 307. `test_author_outcome.py:387-393` pins the order.
- "[] when the directory does not exist": this is standard-library `Path.glob` behavior on a missing directory. `test_author_outcome.py:395-396` pins it.
- "the index's only directory listing, so a test can stand in for a file that vanishes between the listing and the read": the claim is true.
  - `Grep` for `glob|iterdir|listdir|scandir|walk(` in `author_outcome.py` hits only line 307.
  - The sole caller is `_LedgerIndex.refresh` at line 366.
  - Three tests monkeypatch the function: `test_author_outcome.py:547`, `569` and `2636`.
  - Static analysis of the repository finds all of this, and the vanish scenario is already documented in the test docstring at `test_author_outcome.py:534-539`. Under the rule under test, a clause that takes several files to find is still a restatement.

Failure mode: A reader pays to read four sentences that tell them nothing the one-line body doesn't. The sentences also go stale silently if the glob pattern or the number of listing sites changes.

Required property: Delete the docstring. Nothing in it names a decision with a reason that static analysis cannot find. If the author wants the seam kept explicit, the only candidate is a pointer to the test that documents it, such as "Test seam: see `test_file_vanishing_between_listing_and_open_is_not_found`". That pointer is optional.
