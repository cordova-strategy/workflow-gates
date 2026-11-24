# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/post-crash-sessions.py`); 1 carried an in-scope comment change (the new docstring on `_has_indeterminate_liveness`).

Set aside: the dispatch's "Rule under test" bullet replaces CLAUDE.md's "Don't restate the code" bullet for this session, and I applied it. The `python-environment-conventions.md` rules file that loaded mid-review is irrelevant to a comment-discipline review and changed nothing.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/post-crash-sessions.py:1048-1051` (the added docstring).

Issue: The docstring is "True when any entry in `entries` carries indeterminate liveness under `source_name` in `liveness` -- used to withhold Confirmed-clean-exit promotion when a same-session sibling from the *other* evidence source hasn't resolved to live or dead."

- The first clause restates the function's name, signature and one-line body (`any(liveness[(source_name, e.pid)] == "indeterminate" for e in entries)`).
- The "used to withhold ... promotion" clause describes the sole production caller. Static analysis finds that caller at line 1237, where `lookup_sibling_indeterminate` feeds `dead_after_boot_fully_confirmed` at line 1242.
- The one non-obvious decision here is why an indeterminate lookup sibling blocks confirmation. The call-site comment at lines 1234-1236 already holds it, and the comment at 1270-1273 holds the related rule.
- The docstring also hard-codes the caller's "other evidence source" framing into a generic helper. The tests at `tests/test_post_crash_sessions.py:1835` call it with `"registry"`.

Production failure mode: the docstring adds no decision of its own and duplicates the call-site comments. Its caller-specific wording would go stale if a second caller appeared.

Required property: delete the docstring. No clause names a decision or an outside constraint that static analysis cannot find. The "why" is already at the call site, so nothing needs relocating. A shorter or corrected version would still restate the code.
