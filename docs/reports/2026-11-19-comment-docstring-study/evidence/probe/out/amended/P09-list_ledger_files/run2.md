# comment-discipline-reviewer

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/author_outcome.py:303-306` (new docstring on `_list_ledger_files`).

Issue: every sentence in the docstring states something that static analysis of this repository's code and tests, or the standard library, already finds. Under the replaced "Don't restate the code" bullet, that is deleted even when true.

- "Every ledger file directly under ledger_dir, sorted by filename for a deterministic read order" restates the body, `sorted(ledger_dir.glob("*.jsonl"))`. The `*.jsonl` pattern, the non-recursive glob and the `sorted` call are all visible. `TestLedgerFileListing` (test_author_outcome.py ~390-393) also shows that the `.jsonl.lock` sibling is excluded.
- "[] when the directory does not exist" is `Path.glob` behaviour on a missing directory (standard library). `test_missing_directory_lists_nothing` (test_author_outcome.py:395-396) pins it.
- "This is the index's only directory listing" is true, so it is not a False-claim finding. A search of `transcript_analysis/` found the only `glob` call at author_outcome.py:307, and the only caller is `_LedgerIndex.refresh` at line 366. A `Grep` for `_list_ledger_files` finds both, so it is a code-derivable fact.
- "so a test can stand in for a file that vanishes between the listing and the read" restates the seam's use. Tests monkeypatch `_list_ledger_files` at test_author_outcome.py:547, 569 and 2636. The vanishing-file scenario is also described in the docstring at test_author_outcome.py:534-537.

Production failure mode: none at runtime. The cost is a stale-prone comment. If the glob pattern, the sort or the single-caller shape changes, the docstring silently becomes false and adds a second place to maintain.

Required property: delete the docstring. No clause records a decision whose reason static analysis cannot find, so nothing remains to keep. The test-seam rationale is the only candidate, and the tests already show it. If the author wants to keep it, it must be a single sentence naming the decision and its reason, with the listing and the empty-directory clauses removed.
