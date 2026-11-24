# comment-discipline-reviewer

Scope: 1 file reviewed (`claude/.claude/scripts/transcript_analysis/scope.py`), 1 carried an in-scope change (the new docstring on `_path_stripped_scan_error`, lines 207-215 of the snapshot).

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/scope.py:207-215`

Issue: the added docstring is five sentences, and almost every clause restates something static analysis or the standard library already shows:
- "Same exception type, with any embedded absolute path removed from the message" restates the function name and its one-line body.
- "Mirrors `_iter_scoped_sessions`' own root-level diagnostic, which uses `exc.strerror or 'permission denied'`" restates the body's expression and a sibling's code (confirmed at `scope.py:425`).
- "`str(exc)` can embed the offending path" is stdlib `OSError.__str__` behavior.
- "`OSError(errno, strerror)` reconstructs the correct subclass (e.g. `PermissionError`) from `errno`" is stdlib behavior.
- "A caller matching on subclass still sees the same type" restates the previous sentence.

The claims are true, so there is no False-claim finding. The rule deletes them anyway, "even if true".

The only decision here is that the path is stripped from a propagated scan error. Its reason already lives in the `_dedup_new_project_dirs` docstring (`scope.py:254-257`): this level has no per-account ordinal to label the path with. The new docstring states no reason of its own.

Production failure mode: the docstring will drift from the one-line body and duplicates the reason held in `_dedup_new_project_dirs`. That breaks single-source-of-truth.

Required property: keep the decision and point to where its reason lives, then delete the rest. Proposed replacement:

```python
    """Strip the path from the message of a propagated scan error; see
    `_dedup_new_project_dirs` for why."""
```

The `PermissionError` subclass-preservation point is a stdlib fact, so it needs no comment. If the author wants it kept, it has to be a reason static analysis cannot find, and it is not one.
