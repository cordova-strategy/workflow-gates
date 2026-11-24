# comment-discipline-reviewer

Scope: 1 file reviewed, 1 carried an in-scope comment change (new docstring on `_off_table`). One line of the dispatch prompt's system context (the python-environment-conventions rules file) has no bearing on this review and was set aside.

## R1 [CONCERN] False or unsourced claim

File: `claude/.claude/scripts/cursor-adapter/hook-shim.py:1158`

Issue: The docstring says "A null value counts as absent." The subject, `_off_table` at lines 1157-1159, supports that only for known keys. The condition is `key not in known or (value is not None and not _is_known(...))`. The `value is not None` guard sits only on the type-check branch. An unknown key with a `None` value hits `key not in known` first and returns True. So `_off_table({"bogus": None}, KNOWN_TOP_KEYS)` is True, and a null unknown key is not treated as absent.

Production failure mode: A reader trusts the docstring, assumes `{"newField": null}` passes, and misjudges when `carries_unknown_field` (line 1162) fires. That function uses `_off_table` to flag unknown output fields.

Required property: State the narrowest claim the code supports. For example: "A null value of a known key counts as absent; any key outside `known` counts regardless of its value." The first sentence ("a key outside `known`, or a known key of another type") matches the code. It stays correct only if the "any" kind is noted: a known key of kind `"any"` never fails the type check. That is optional.

## Answers

No specific questions were posed.
