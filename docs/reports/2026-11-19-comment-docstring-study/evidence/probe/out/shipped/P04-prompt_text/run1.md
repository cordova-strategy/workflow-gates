# comment-discipline-reviewer

Scope: 1 file reviewed, 1 carried an in-scope comment change (`claude/.claude/scripts/compaction-context.py`, new docstring on `_prompt_text`, line 111).

No findings.

- Claim check: the docstring says the closer and emptiness checks judge the text the block emits. Read at the diff's state, that holds.
  - `_is_prompt_candidate` runs its `task-notification>` closer check on `_prompt_text(rec)` (line 207).
  - `_quoted_text` runs its emptiness check (line 245), its command-args closer search (line 221, via `_first_command_args`) and its returned text (lines 253 and 256) on `_prompt_text(rec)` (line 244).
  - Both checks and the emitted text use the NUL-stripped string.
- Altitude and restating: the docstring has one sentence. The first clause echoes the body, but it carries the non-obvious reason in the same sentence, so it is a tightly coupled pair and not a restatement finding.
