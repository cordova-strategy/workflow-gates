# comment-discipline-reviewer

Set aside: the `python-environment-conventions.md` rule text that arrived mid-review. It is not part of the diff and has no bearing on its scope.

Reviewed 1 file (`claude/.claude/scripts/check-handoff.py`), 1 carrying an in-scope comment change (the new `strip_code_spans` docstring).

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/check-handoff.py:95-98` (diff lines 8-11).

Issue: The docstring opens with "Remove fenced code blocks and inline code spans". The function name `strip_code_spans` and its body (`_INLINE_CODE_RE.sub("", _FENCED_BLOCK_RE.sub("", text))`) already show this. The remaining clause is the only non-obvious fact: stripping keeps a quoted literal from firing the placeholder and anchor-shape scans. I read the call sites at lines 165 (`check_placeholder_text`) and 191 (`check_section3_anchor_shapes`), and that clause is accurate. So no false-claim finding.

Production failure mode: none. This costs reader attention, and the docstring buries the one useful fact behind a restatement and a dash-chained aside ("the natural way a draft would quote…").

Required property: delete the restating first clause and lead with the purpose, in one sentence. For example: "Strips quoted literals so the placeholder and anchor-shape scans don't fire on text a draft is citing rather than proposing." Keep both scans named, since they are the facts that make the docstring non-obvious.
