# comment-discipline-reviewer

Scope note: one file in the diff (`scope.py`), one added docstring in scope. The `python-environment-conventions.md` system reminder is unrelated to this review and was set aside.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/scope.py:207-215` (`_path_stripped_scan_error` docstring)

Issue: the docstring is five sentences. Only one states a decision with a reason the code and stdlib don't show. The rest restate what the code and the stdlib show, against the rule under test ("delete everything static analysis of this repository's code and tests, or the standard library, finds, even if true"):

- "Same exception type, with any embedded absolute path removed from the message." restates the function name and its one-line body.
- "Mirrors _iter_scoped_sessions' own root-level diagnostic, which uses `exc.strerror or 'permission denied'`" restates line 425, which a grep finds.
- "`str(exc)` can embed the offending path." is stdlib `OSError.__str__` behavior.
- "`OSError(errno, strerror)` reconstructs the correct subclass (e.g. `PermissionError`) from `errno`." is stdlib constructor behavior. It names the mechanism, not the decision.
- "A caller matching on subclass still sees the same type." is the one kept decision. It is real: cost.py:686 and :1217, context_composition.py:352 and context_distribution.py:111 all `except PermissionError`.

Required property: keep the decision and its reason, delete the rest. The reason the path is stripped already lives in `_dedup_new_project_dirs`' docstring (scope.py:254-257), so point there instead of restating it.

Proposed replacement:

```python
    """Rebuild `exc` from `errno` and `strerror` alone, dropping its path.

    Rebuilding from `errno` keeps the subclass (e.g. `PermissionError`)
    that callers catch. Why the path is dropped: see
    `_dedup_new_project_dirs`.
    """
```

## R2 [FYI] Multi-fact comment structure / Paragraph readability

`scope.py:207-215`

Issue: if R1 is not applied, the docstring's first sentence is a noun-phrase fragment ("Same exception type, with …") that splits across a line. The instruction-bearing fact, the subclass guarantee, comes last, after the rationale about `str(exc)` and the mirror pointer.

Required property: applying the R1 replacement resolves this, because the decision leads and the pointer follows as its own sentence.

## Prior decisions

None supplied.
