# comment-discipline-reviewer

Reviewed 1 diff file (`routing_guard.py`); 1 carried an in-scope comment change (the new `_serialize_capture` docstring). Set aside: the system-reminder attaching `python-environment-conventions.md`; it concerns installing Python dependencies, defines no review field, and does not touch this scope.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/routing_guard.py:693`

Issue: the added docstring `"""ASCII-only, so the text encodes the same under any locale."""` states what the standard library already shows. `json.dumps` defaults to `ensure_ascii=True`. The call at lines 694-708 passes no `ensure_ascii`, so ASCII-only output is a stdlib default and not a decision recorded in this repository's code. The rule under test deletes any clause that static analysis of the code or the standard library finds, even when true.

Production failure mode: the stated reason is also not what the code relies on. The only consumer of the serialized text, `built.text.encode("utf-8")` at line 1507 (via `_BuiltRow` at line 1269), names the encoding explicitly. `str.encode` with an explicit codec is locale-independent whether or not the text is ASCII. The only other `encode` call is the branch hash at line 604, which also names `"utf-8"`. Grep for `encoding=|write_text|write_bytes` found no locale-dependent write of this text. So the docstring implies a locale hazard this code does not have, and a later reader may keep ASCII-only output, or an explicit `ensure_ascii=True`, for a reason that does not exist.

Required property: delete the docstring. The function name and the `json.dumps` call already show what it does. Keep a comment only if the code is changed to set `ensure_ascii` explicitly, or if some consumer outside this file needs ASCII output. In that case the comment must name that consumer as the reason, because that is a fact static analysis cannot find.
