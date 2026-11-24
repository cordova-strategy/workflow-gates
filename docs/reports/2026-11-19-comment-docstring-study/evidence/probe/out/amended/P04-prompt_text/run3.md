# comment-discipline-reviewer

## R1 [CONCERN] Restating the code

- **File:line:** `claude/.claude/scripts/compaction-context.py:111` (added docstring on `_prompt_text`)
- **Text:** `"""The record's text with NUL removed, so the closer and emptiness checks judge the text the block emits."""`
- **Issue:** The docstring holds no decision with a reason that static analysis can't find.
  - "The record's text with NUL removed" restates `_record_text(rec).replace("\x00", "")` on line 112.
  - The "so ..." clause names the two callers: the `"task-notification>" in _prompt_text(rec)` check at line 207 and the `text.strip()` emptiness check at line 245. It also says that `_quoted_text` emits the stripped text (lines 244-256). Reading those call sites finds all of it. The rule says to delete such clauses even when they are true and take several files to find.
  - The docstring never says why NUL is stripped at all. That reason, if one exists, is what an outside force would supply: for example, what a NUL byte in a transcript record does downstream.
- **Production failure mode:** None at runtime. The docstring adds nothing the code and its call sites don't already show, and it will drift if a caller is added or removed.
- **Required property:** Delete the docstring.
  - Keep a comment only if it states the outside-the-repo reason NUL must be removed, such as the transcript or harness behavior that produces it. In that case name the decision in the sentence ("strips NUL because ...").
  - The claim itself is accurate. Line 207 is the closer check and line 245 is the emptiness check. So this is not a false-claim finding.

Scope notes:
- The diff has one added line, in one file, and that line is the only site in scope.
- No PR-defined terms, prior-version framing, or multi-fact or readability issues apply to it.
- The `python-environment-conventions.md` rule file that arrived mid-session has no bearing on this diff.
