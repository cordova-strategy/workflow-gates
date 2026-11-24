# comment-discipline-reviewer

Scope: 1 file reviewed, 1 carried an in-scope comment change (the new `_serialize_capture` docstring). Rule under test (the replacement "Don't restate the code" bullet) applied in place of the CLAUDE.md bullet.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/routing_guard.py:693`

Offending text: `"""ASCII-only, so the text encodes the same under any locale."""`

Issue: The docstring states no decision. `json.dumps` returns ASCII-only text because `ensure_ascii` defaults to `True` in the standard library, and the call passes no override. That is what static analysis of the stdlib finds, so the rule says to delete it even though it is true.

The stated reason does not hold either. The only consumer, `text_bytes = built.text.encode("utf-8")` at line 1507, names its encoding explicitly, so locale never affects the bytes (grep of `routing_guard.py` for `encode(`, `encoding`, `ensure_ascii` gives only lines 604 and 1507). The "so ... any locale" clause therefore gives a reason the code does not depend on.

Required property: no docstring on `_serialize_capture` that restates the default. If the author intends to forbid a future `ensure_ascii=False`, the docstring must name that decision and give a reason this repository actually forces, such as a byte-for-byte comparison of captures that needs stable escaping. No such reason is stated in the diff or the file, so the fix is deletion.

Fix: delete line 693. Nothing remains to keep.
