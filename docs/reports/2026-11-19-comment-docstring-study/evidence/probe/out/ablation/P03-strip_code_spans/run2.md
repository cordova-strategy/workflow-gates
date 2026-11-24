# comment-discipline-reviewer

Set aside: the `python-environment-conventions.md` rule text that arrived mid-session. It governs installing Python dependencies and does not touch this review's scope.

Scope: 1 file in the diff (`claude/.claude/scripts/check-handoff.py`). It carries one added docstring, on `strip_code_spans`. I read the file at lines 60-210 and grepped the callers.

## R1 [CONCERN] Prose restating the code

`claude/.claude/scripts/check-handoff.py:95` (docstring clause 1 of 2)

- **Text:** "Remove fenced code blocks and inline code spans"
- **Issue:** The function name `strip_code_spans` and its body (`_INLINE_CODE_RE.sub("", _FENCED_BLOCK_RE.sub("", text))`, line 99) show this. It is a restatement under CLAUDE.md §Durable text's "Don't restate the code" rule, as the rule under test words it.
- **Required property:** Delete the clause. A shorter or corrected restatement still restates.

## R2 [CONCERN] Prose restating the code

`claude/.claude/scripts/check-handoff.py:95-98` (docstring clause 2 of 2)

- **Text:** "the natural way a draft would quote a literal string it's citing rather than proposing as a real next step, so a placeholder or anchor-shape scan does not fire on it."
- **Issue:** Static analysis of this repository's code finds the "so a placeholder or anchor-shape scan does not fire" part. The only callers are `check_placeholder_text` (line 165) and `check_section3_anchor_shapes` (line 191), and each scans the stripped text for tokens. The "natural way a draft would quote" part describes how the strip is used and gives no decision or outside-forced reason beyond that. I judged it under the dispatch rule that every docstring clause is reported with deletion as its fix, whatever it says.
- **Required property:** Delete the clause. With R1 applied, no docstring remains, so delete the whole docstring. Nothing in it is a kept decision naming what was decided and why.
- **Checked against other angles:** The claim is true, because both callers do scan the stripped text. It draws no False or unsourced claim finding. The docstring has no PR-defined label and no prior-version framing.
