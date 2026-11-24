# comment-discipline-reviewer

Scope: 1 file reviewed (`claude/.claude/scripts/transcript_analysis/scope.py`), 1 with an in-scope comment change (the new docstring on `_path_stripped_scan_error`, lines 207-215). No prompt text was set aside.

The docstring has five clauses. Under the session's "Don't restate the code" rule, each is deleted unless it is a pointer or a design decision with a reason static analysis cannot find. The function body is one line, so deleting every clause leaves no docstring. If the author wants a trace of the decision, the pointer in R2 is the only part that may stay.

## R1 [CONCERN] Restating the code
File: scope.py:207-208
Issue: "Same exception type, with any embedded absolute path removed from the message." This restates what the one-line body and the `-> OSError` signature show: a new `OSError` is built from `errno` and `strerror` only.
Failure mode: A reader gets the function's name and body again. The clause is also broader than the code. Dropping `filename` is by construction, but "any embedded absolute path" is not checked against `strerror`.
Required property: Delete the clause.

## R2 [CONCERN] Restating the code
File: scope.py:210-211
Issue: "Mirrors _iter_scoped_sessions' own root-level diagnostic, which uses `exc.strerror or 'permission denied'` rather than `str(exc)`." The elaboration after "which uses" restates the body (`exc.strerror or "permission denied"`), and the same expression sits at scope.py:425. I checked the claim and it is true.
Failure mode: A second copy of an expression that is already visible in two places.
Required property: Delete the "which uses ... rather than `str(exc)`" elaboration. The pointer to the symbol that holds the decision may stay, for example "Mirrors `_iter_scoped_sessions`' root-level diagnostic." The decision's rationale already lives in that function's docstring (scope.py:391-397) and in `_dedup_new_project_dirs` (scope.py:254-257).

## R3 [CONCERN] Restating the code
File: scope.py:211-212
Issue: "`str(exc)` can embed the offending path." This is standard-library behavior that static analysis of CPython finds. It is the reason for the decision, but the rule deletes reasons the standard library supplies.
Failure mode: It explains stdlib behavior, not a repository constraint.
Required property: Delete the clause. The reason is already stated at scope.py:396-397 and 255-257.

## R4 [CONCERN] Restating the code
File: scope.py:212-213
Issue: "`OSError(errno, strerror)` reconstructs the correct subclass (e.g. `PermissionError`) from `errno`." This is documented `OSError` constructor behavior in the standard library.
Failure mode: It teaches stdlib semantics and is not a decision of this repository.
Required property: Delete the clause.

## R5 [CONCERN] Restating the code
File: scope.py:213-214
Issue: "A caller matching on subclass still sees the same type." This is a consequence of R4's stdlib behavior, so it restates what static analysis of the stdlib finds. It is also not guaranteed when `exc.errno` is `None` or unmapped, because the result is then a plain `OSError`.
Failure mode: It restates stdlib behavior and overstates it in the edge case.
Required property: Delete the clause.
