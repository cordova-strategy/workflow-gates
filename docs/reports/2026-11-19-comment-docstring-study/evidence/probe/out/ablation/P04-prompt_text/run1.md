# comment-discipline-reviewer

Prompt text set aside: none contradicting the agent file. The session's replacement "Don't restate the code" bullet was applied as the rule for the Restating the code angle.

## R1 [CONCERN] Prose restating the code

File: claude/.claude/scripts/compaction-context.py:111

Issue: The docstring clause "The record's text with NUL removed" restates the function body, `_record_text(rec).replace("\x00", "")`, and its name and signature.

Production failure mode: The clause adds no decision, so it only drifts if the body changes.

Required property: Delete the clause.

## R2 [CONCERN] Prose restating the code

File: claude/.claude/scripts/compaction-context.py:111

Issue: The docstring clause "so the closer and emptiness checks judge the text the block emits" gives a reason static analysis of this repository finds. The callers at lines 207 (`"task-notification>" in _prompt_text(rec)`) and 244-245 (`text = _prompt_text(rec)` followed by `text.strip()`) show which checks consume the NUL-stripped text. The "block emits" half is found by reading the emit path in the same file, which takes several files to trace. No outside-repo constraint forces the NUL strip, and the docstring names none, such as a downstream consumer's NUL handling.

Production failure mode: The reason duplicates what the callers show and goes stale if they change.

Required property: Delete the clause. The whole docstring goes, since nothing is left. If the author knows an outside-repo force behind the NUL strip, such as a downstream parser that rejects NUL, a docstring naming only that force would be a kept decision. Nothing in the repo supplies one.
