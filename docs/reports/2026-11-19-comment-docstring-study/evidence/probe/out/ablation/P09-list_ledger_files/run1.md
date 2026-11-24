# comment-discipline-reviewer

Scope: 1 file in the diff (`author_outcome.py`), 1 with an in-scope comment change (the new `_list_ledger_files` docstring). No prompt text was set aside.

## R1 [CONCERN] Restating the code
author_outcome.py:303 — "Every ledger file directly under ledger_dir,"
- Issue: The `glob("*.jsonl")` call on `ledger_dir` at line 307 shows this, as does `test_author_outcome.py:393`, where the `.lock` file is excluded. "Directly under" is the non-recursive `glob`.
- Failure mode: The clause restates the code, and it drifts if the pattern changes.
- Required property: Delete the clause.

## R2 [CONCERN] Restating the code
author_outcome.py:303-304 — "sorted by filename for a deterministic read order."
- Issue: `sorted(...)` at line 307 shows the ordering. The "deterministic" reason is the stated purpose of `sorted`, and it names no outside constraint that static analysis cannot find.
- Failure mode: The clause restates the code. A shorter version would still restate it.
- Required property: Delete the clause.

## R3 [CONCERN] Restating the code
author_outcome.py:304 — "[] when the directory does not exist."
- Issue: This is `Path.glob` behavior on a missing directory (standard library). `test_missing_directory_lists_nothing` (`test_author_outcome.py:395-396`) also states it.
- Failure mode: The clause restates the standard library and the tests.
- Required property: Delete the clause.

## R4 [CONCERN] Restating the code
author_outcome.py:304-306 — "This is the index's only directory listing, so a test can stand in for a file that vanishes between the listing and the read."
- Issue: A `Grep` of `author_outcome.py` for `glob|iterdir|listdir|scandir` finds one hit (line 307), so the "only listing" claim is true but repository analysis finds it. The monkeypatch seam is also visible in the tests (`test_author_outcome.py:547`, `569`, `2636`), and `refresh` at line 366 shows the call site.
- Failure mode: The clause restates what the code and tests show, and it goes stale when a second listing is added.
- Required property: Delete the clause. After R1–R4 the docstring has no clause left, so delete the whole docstring.

Request changes: delete the docstring in full.
