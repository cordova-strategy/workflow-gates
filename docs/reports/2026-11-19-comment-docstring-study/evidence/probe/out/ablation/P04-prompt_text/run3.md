# comment-discipline-reviewer

Scope note: 1 file reviewed (`claude/.claude/scripts/compaction-context.py`), 1 carried an in-scope change (one added docstring, line 111 of the snapshot). The dispatch prompt's replacement "Don't restate the code" bullet is applied as the session's rule under test.

## R1 [CONCERN] Prose restating the code

`claude/.claude/scripts/compaction-context.py:111`, first clause of the `_prompt_text` docstring.

- Text: `"The record's text with NUL removed, ..."`
- Issue: The clause restates the body, `_record_text(rec).replace("\x00", "")`. The function name, signature and body show it.
- Why it fails: The rule keeps only a decision's reason that static analysis cannot find. This clause gives none. It does not say why NUL is stripped or what outside the repository forces it.
- Fix: Delete the clause. If the whole docstring goes (see R2), nothing remains.

## R2 [CONCERN] Prose restating the code

`claude/.claude/scripts/compaction-context.py:111`, second clause of the `_prompt_text` docstring.

- Text: `"... so the closer and emptiness checks judge the text the block emits."`
- Issue: The clause names the function's consumers. Static analysis of this repository finds both:
  - the `"task-notification>" in _prompt_text(rec)` check at line 207;
  - the `text.strip()` emptiness check at line 245.
- Why it fails: The rule says to delete anything static analysis of this repository's code finds, even when it is true and takes several files to find. The clause names no outside force behind the NUL strip.
- Fix: Delete the clause, and with it the whole docstring. `_prompt_text` is a one-line helper whose name and body state what it does.
- Alternative: keep a docstring only if the author can state why NUL must be stripped, such as an external producer or consumer that forces it. That reason would have to come from outside this repository. The current text does not state one.

No other angle produced a finding. The docstring uses no PR-defined labels, makes no prior-version comparison, and is a single sentence.
