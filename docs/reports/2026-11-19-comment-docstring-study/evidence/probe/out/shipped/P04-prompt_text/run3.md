# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/compaction-context.py`); 1 carried an in-scope comment change (the added `_prompt_text` docstring at line 111).

Set aside: the `<system-reminder>` carrying `python-environment-conventions.md`. It governs Python dependency installs and does not change this review's scope.

No findings.

- Comment verbosity, Multi-fact comment structure and Paragraph readability: the docstring is one sentence. It pairs a fact (NUL removal) with its direct reason, which is a tightly coupled pair.
- Prose restating the code: the NUL removal clause is visible in the body. The `so the closer and emptiness checks judge…` clause is the non-obvious why, so the docstring does not merely restate.
- False or unsourced claim: the claim holds. `_is_prompt_candidate` runs the `task-notification>` closer check on `_prompt_text(rec)` (line 207). `_quoted_text` runs the emptiness check `text.strip()` on `_prompt_text(rec)` (lines 244-245) and returns that same text as the quoted output. "The block" resolves to the state block defined in the module docstring (line 6).
- PR-defined terminology, "Used to be X" framing, Wrong altitude and Restated canonical rule: none present.

**No comment-discipline concerns**
