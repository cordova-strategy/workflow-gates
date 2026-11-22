# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/compaction-context.py`); 1 carried an in-scope comment change (the new `_prompt_text` docstring).

Note: the loaded `python-environment-conventions.md` reminder is unrelated to this review and was set aside.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/compaction-context.py:111`

Offending text: `"""The record's text with NUL removed, so the closer and emptiness checks judge the text the block emits."""`

Issue:
- The clause "The record's text with NUL removed" restates the body (`_record_text(rec).replace("\x00", "")`) and the function name.
- The "so ..." clause names no reason static analysis cannot find. It lists the consumers: the task-notification closer check at line 207, the emptiness check at line 245, and the emitted text at lines 244-256 into `_fenced`. Reading the callers shows all three.
- It also never says what a NUL does to those checks, or what outside the repository forces the strip. That is the part a reader cannot recover from the code.
- "The closer" is ambiguous. The file has a task-notification closer (`task-notification>`, line 207) and `_COMMAND_ARGS_CLOSER` (line 221).

Required property:
- Delete the docstring unless it can state the decision with a reason the code does not show. The decision is that NUL is stripped, and the reason is what a NUL byte breaks.
- Only the author can supply that reason, because it is not in this repository. Examples would be a NUL splitting a marker so the closer check misses it, or a NUL-only prompt passing the emptiness check. I could not confirm either from the repository, so do not write one without checking it.
- If the reason is not known, delete the docstring and keep the code bare. A shorter or corrected paraphrase of the consumer list still restates.
