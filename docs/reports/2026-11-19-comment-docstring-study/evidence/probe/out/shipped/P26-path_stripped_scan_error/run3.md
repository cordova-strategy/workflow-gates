# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/transcript_analysis/scope.py`); 1 carried an in-scope change, the new docstring on `_path_stripped_scan_error`.

## R1 [FYI] Comment verbosity

- **File:line:** `claude/.claude/scripts/transcript_analysis/scope.py:207-215`
- **Issue:** The docstring's last sentence, "A caller matching on subclass still sees the same type.", says again what the opening line ("Same exception type, …") and the preceding sentence ("reconstructs the correct subclass … from `errno`") already say. It adds no fact.
- **Production failure mode:** None at runtime. The cost is a longer docstring whose closing sentence a reader must parse before finding that it adds nothing.
- **Required property:** Delete the closing sentence. Keep the other four facts: the path is stripped; it mirrors the root-level `strerror` diagnostic; `str(exc)` can embed the path; `OSError(errno, strerror)` rebuilds the subclass from `errno`.

## Checked, no finding

- **False or unsourced claim.** Each settleable claim in the docstring holds at the diff's state:
  - The root-level diagnostic uses `exc.strerror or 'permission denied'` at `scope.py:425`.
  - `OSError(errno, strerror)` picking the errno-mapped subclass is standard CPython behavior.
  - The "same type" claim holds for every `OSError` that `_stat_mode_unless_absent()` and `resolve()` raise, because CPython builds those with the errno-mapped subclass. It would fail for an `OSError` with `errno=None`, which the caller at line 267 cannot produce, so I did not flag it.
- **Single source of truth.** The "`str(exc)` embeds the path" rationale also appears at `scope.py:396-397` and, in part, at `scope.py:254-257`. Each site explains a different caller's behavior, so I did not flag them as duplication.
- **PR-defined terminology, "used to be X" framing, restating the code, wrong altitude.** None found in the added text.
