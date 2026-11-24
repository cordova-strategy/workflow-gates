# comment-discipline-reviewer

Scope: 1 file reviewed (`claude/.claude/scripts/transcript_analysis/scope.py`), 1 added docstring in scope (`_path_stripped_scan_error`, lines 207-215 of the post-diff file).

The auto-attached `python-environment-conventions.md` rule file governs dependency installs and does not bear on this diff. I set it aside and applied nothing from it.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/scope.py:207-215`

Offending text:

> Same exception type, with any embedded absolute path removed from the message. Mirrors _iter_scoped_sessions' own root-level diagnostic, which uses `exc.strerror or 'permission denied'` rather than `str(exc)`. `str(exc)` can embed the offending path. `OSError(errno, strerror)` reconstructs the correct subclass (e.g. `PermissionError`) from `errno`. A caller matching on subclass still sees the same type.

Issue: under the rule under test, only the non-obvious decisions stay, each with a reason static analysis cannot find. Most of this docstring is findable by reading the code or the standard library, so it restates.

- "Same exception type, with any embedded absolute path removed" restates the function name and its one-line body.
- "Mirrors `_iter_scoped_sessions`' … `exc.strerror or 'permission denied'`" is findable at `scope.py:425`.
- "`str(exc)` can embed the offending path" is standard-library behavior.
- "`OSError(errno, strerror)` reconstructs the correct subclass … from `errno`" is standard-library behavior.
- "A caller matching on subclass still sees the same type" restates the previous sentence. A shorter or corrected restatement still restates, so these are deleted, not tightened.

Two decisions are non-obvious and still need their reasons:

- **Why the path is stripped.** A raw config-dir path in a propagated error would leak account/client identity into a `--redact` run. This level, unlike the root level, has no per-account ordinal to label the path with. The reason is stated at `scope.py:410-413` and `scope.py:254-257`, but not in this docstring.
- **Why the error is built from `exc.errno`.** The `except PermissionError` handlers must still match. They sit at `cost.py:686` and `cost.py:1217`, and `scope.py:855` names them. Neither this docstring nor the diff names them.

Production failure mode: a future editor sees only stdlib trivia. They may "simplify" to `OSError(exc.strerror)`, which loses the subclass and breaks the `PermissionError` handlers. They may also swap in `str(exc)` and leak a raw path in redacted runs.

Required property: one sentence per kept decision, each naming its subject and reason, with the rest deleted. Suggested replacement:

```python
    """Strip the path from `exc`'s message so a propagated scan error cannot
    leak a raw config-dir path into a --redact run (see the comment in
    `_iter_scoped_sessions`). Built from `exc.errno` so the callers'
    `except PermissionError` handlers in cost.py still match.
    """
```

The replacement avoids the stdlib restatement, so the false-claim angle does not apply to it. The deleted "same exception type" sentence would also have been imprecise, since the type is not preserved when `exc.errno` is `None` or maps to no subclass. That imprecision is a further reason to delete the sentence, not to correct it.

## Prior decisions

None supplied. This is a first review.
