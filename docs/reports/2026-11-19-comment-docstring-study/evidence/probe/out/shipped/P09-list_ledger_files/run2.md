# comment-discipline-reviewer

Scope: 1 file in the diff (`author_outcome.py`), 1 with an in-scope comment change (the new `_list_ledger_files` docstring). I set aside one block of text in the conversation: a `python-environment-conventions.md` rules reminder that arrived mid-task. It has nothing to do with this review, so I ignored it.

Claims checked against the repo:
- "[] when the directory does not exist": `test_author_outcome.py:396` asserts `_list_ledger_files(tmp_path / "review-narrative-ledger") == []`.
- "the index's only directory listing": the only `glob`, `iterdir`, `listdir` or `scandir` call in `author_outcome.py` is line 307. The only caller is `_LedgerIndex.refresh` at line 366.
- "a test can stand in for a file that vanishes": `test_author_outcome.py:547`, `:569` and `:2636` monkeypatch `ao._list_ledger_files`.

All three hold, so there is no False or unsourced claim finding.

## R1 [FYI] Comment verbosity

File: `claude/.claude/scripts/transcript_analysis/author_outcome.py:305-306`

Issue: the last docstring sentence is "This is the index's only directory listing, so a test can stand in for a file that vanishes between the listing and the read."

- The "only directory listing" half records a property of the whole module. It goes stale silently if a second listing is ever added, and it does not change how a caller uses the function.
- The "stand in for a file that vanishes" half is the non-obvious fact worth keeping. It is also worded loosely: the tests stub the function to return a path that no longer exists, and nothing "stands in for" the file.

Required property: keep one sentence that names the test seam and drop the module-wide "only listing" claim. For example: "Tests monkeypatch this to simulate a file that vanishes between listing and reading." The first two sentences (sort order, `[]` for a missing directory) carry distinct non-obvious facts and stay.
