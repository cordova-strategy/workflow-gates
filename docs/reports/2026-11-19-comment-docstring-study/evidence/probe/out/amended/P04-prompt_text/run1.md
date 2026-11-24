# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/compaction-context.py`); 1 carried an in-scope comment change (the new `_prompt_text` docstring).

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/compaction-context.py:111`

Offending text: `"""The record's text with NUL removed, so the closer and emptiness checks judge the text the block emits."""`

Issue: the docstring has two parts, and both are findable by static analysis of this repository.
- "The record's text with NUL removed" restates the body, `_record_text(rec).replace("\x00", "")`.
- The reason names the callers' checks: the task-notification closer test (line 207) and the `text.strip()` emptiness test (line 245), plus the block's emitted text. Reading `_quoted_text`, `_quoted_message` and `_render_block` shows that the text those checks judge is the text the block emits. The tests confirm it: `test_prompt_with_no_text_once_nul_is_stripped_takes_no_message_slot`, `test_tilde_run_joined_by_stripping_nul_is_fenced_on_the_stripped_text`, and the no-origin prompt with a `</task-notif\x00ication>` closer. The repo shows both the strip and its reason. The amended rule says to delete anything static analysis of this repository's code and tests finds, even when it takes several files to find.

Accuracy check: the claim itself is true. Every emitted path (`_quoted_text`, then `_cut_to_budget`, `_fenced`, `_slash_invocation_quote`) derives from `_prompt_text`'s output, and the tests assert `"\x00" not in block`. The finding is a restatement, not a false claim.

Production failure mode: none. This is comment bloat, and it names two call-site checks that can drift if another caller is added.

Required property: delete the docstring. `_prompt_text` is a one-line helper whose name and body already say what it does.

Exception: if the NUL strip is forced by a constraint outside this repository (for example, the hook or stdout consumer cannot carry NUL), keep one sentence that names that constraint and cite where it is documented. The diff and the repo do not show such a source, so deletion is the default.

Fix-vs-angle check: deleting the docstring creates no other-angle violation. It is a Prose restating the code finding, not Comment verbosity, because the text is one sentence.

Prior decisions: none supplied.
