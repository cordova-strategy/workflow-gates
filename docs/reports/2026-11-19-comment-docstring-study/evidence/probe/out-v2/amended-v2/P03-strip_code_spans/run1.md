# comment-discipline-reviewer

Set aside: the `python-environment-conventions.md` system reminder. It does not bear on this review's scope.

Reviewed 1 file (`claude/.claude/scripts/check-handoff.py`); 1 carried an in-scope comment change (the new `strip_code_spans` docstring, lines 95-98).

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/check-handoff.py:95-98`

Issue: the docstring opens with "Remove fenced code blocks and inline code spans", which restates the function name (`strip_code_spans`), its body (`_INLINE_CODE_RE.sub("", _FENCED_BLOCK_RE.sub("", text))`) and the regex names. Under the rule under test, a clause that mixes a decision with restated detail keeps the decision half and drops the restated half. The decision half is the dash clause. It says why the stripping exists: a draft quotes a literal it is citing, not proposing, so the placeholder and anchor-shape scans must not fire on it. That reason comes from how drafts are written, so static analysis can't find it.

Verified: the "placeholder or anchor-shape scan" claim is accurate. The only callers are `check_placeholder_text` (line 165) and `check_section3_anchor_shapes` (line 191). The "natural way a draft would quote" part is a design judgment, so it draws no claim finding.

Production failure mode: none at runtime. The cost is a docstring that repeats what the name and body already say, and it buries the one non-obvious fact behind a restatement.

Required property: keep only the reason, as one sentence that names its subject. Suggested replacement:

```python
    """Quoted code is dropped so a draft that cites a placeholder or anchor-shape
    literal, rather than proposing it, doesn't trip the placeholder and §3 scans."""
```

The fix adds no run-on, no PR-defined label and no prior-version framing.
