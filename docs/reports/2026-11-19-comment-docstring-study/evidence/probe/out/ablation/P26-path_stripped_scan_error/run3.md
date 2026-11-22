# comment-discipline-reviewer

Scope: 1 file reviewed (`scope.py`), 1 with an in-scope change (the new `_path_stripped_scan_error` docstring, lines 207-215 of the file). No dispatcher text was set aside. The rule under test (replacement "Don't restate the code" bullet) was applied to every docstring clause.

The one decision the docstring holds is that the helper strips the raw path from the message. Its reason is that a scan failure must not leak the raw path while paths are redacted. The same reason is already written in `cost.py:687-689`, `context_distribution.py:112-114`, and `scope.py:254-257`. Everything else in the docstring is derivable from the code or the standard library. The docstring has five clauses, so there are five findings.

## R1 [CONCERN] Prose restating the code
scope.py:207-208 (diff lines 8-9)

Text: "Same exception type, with any embedded absolute path removed from the message."

Issue: The clause restates the function's name (`_path_stripped_scan_error`) and its one-line body. "Same exception type" is also a restatement of the signature (`OSError -> OSError`).

Required property: Delete the clause as a standalone summary. This clause is the subject of the one kept decision, so keep the subject inside that decision's sentence. The kept docstring is a single sentence of the form "Strips the path so a scan failure can't leak the raw path under redaction." This sentence also carries the reason that R3 would otherwise delete. Do not leave the reason with no subject.

## R2 [CONCERN] Prose restating the code
scope.py:210-211 (diff lines 11-12)

Text: "Mirrors _iter_scoped_sessions' own root-level diagnostic, which uses `exc.strerror or 'permission denied'` rather than `str(exc)`."

Issue: The "which uses ... rather than `str(exc)`" clause restates scope.py:425 and the function's own return expression. Static analysis finds both.

Required property: Delete the clause that describes the expression. The bare pointer "Mirrors `_iter_scoped_sessions`' root-level diagnostic" may stay if the author wants a pointer to where the same decision is made. It must carry no description of what that code does.

## R3 [CONCERN] Prose restating the code
scope.py:211 (diff line 12)

Text: "`str(exc)` can embed the offending path."

Issue: This clause describes standard-library behavior (`OSError.__str__` includes `filename`). Static analysis of the standard library finds it, even though it is true.

Required property: Delete it. The reason for the decision is the redaction/leak concern, which the sentence R1 keeps. It is not a fact about `str(exc)`.

## R4 [CONCERN] Prose restating the code
scope.py:211-213 (diff lines 12-14)

Text: "`OSError(errno, strerror)` reconstructs the correct subclass (e.g. `PermissionError`) from `errno`."

Issue: This clause describes the standard library's `OSError` constructor and its errno-to-subclass mapping. It also restates the body, `OSError(exc.errno, ...)`.

Required property: Delete it.

## R5 [CONCERN] Prose restating the code
scope.py:213-214 (diff lines 14-15)

Text: "A caller matching on subclass still sees the same type."

Issue: The clause restates the consequence of R4's constructor behavior. The callers are findable by grep (for example the `except PermissionError` sites in `cost.py:686` and `context_distribution.py:111`). The claim is also broader than the code supports, because an `exc` with `errno` of `None` or an unmapped errno comes back as plain `OSError`. That overclaim goes away with the deletion.

Required property: Delete it.
