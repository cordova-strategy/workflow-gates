# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/compaction-context.py`); 1 carried an in-scope comment change (the new `_prompt_text` docstring, diff line 8).

## R1 [CONCERN] Prose restating the code
- **File:line:** `claude/.claude/scripts/compaction-context.py:111` (diff.patch:8)
- **Clause:** "The record's text with NUL removed"
- **Issue:** The clause restates the body `_record_text(rec).replace("\x00", "")` and the name `_prompt_text`.
- **Fix:** Delete the clause.

## R2 [CONCERN] Prose restating the code
- **File:line:** `claude/.claude/scripts/compaction-context.py:111` (diff.patch:8)
- **Clause:** "so the closer and emptiness checks judge the text the block emits"
- **Issue:** Static analysis of this repository finds this clause. The callers at lines 207 (`"task-notification>" in _prompt_text(rec)`) and 244 (`text.strip()`) show which checks consume the helper. The "closer" check and the block-emission path are likewise in this repository's code. I found no reason from outside the repository for stripping NUL (a harness or format constraint) stated or implied in the diff.
- **Fix:** Delete the clause. With both clauses gone, the docstring is empty, so delete the whole docstring. If a repo-external reason for the NUL strip exists, such as a downstream consumer that truncates at NUL, replace the docstring with one sentence naming that constraint and the decision (NUL is stripped).
