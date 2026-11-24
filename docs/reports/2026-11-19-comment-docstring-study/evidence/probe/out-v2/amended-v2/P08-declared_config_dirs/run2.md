# comment-discipline-reviewer

## R1 [CONCERN] False or unsourced claim

`claude/.claude/scripts/post-crash-sessions.py:1915-1917` (the new `_declared_config_dirs` docstring).

Offending text: "the latter would silently drop a sessions-only root".

Issue: `declared_transcript_roots()` does not drop a sessions-only root silently. It calls `declared_roots_matching()`, which prints `declared_transcript_roots: declared root <index> unreadable` to stderr whenever `is_valid` fails (`_config_dir.py:150-152`, predicate at `_config_dir.py:166-169`). The root is dropped with a warning that names it by index. Only an absent or unreadable roots file is silent (`_config_dir.py:123-127`).

Failure mode: a maintainer reads "silently" and trusts the stock helper's failure to be invisible. Or they reason that the warning makes the tighter predicate acceptable.

Required property: the claim says only what the subject supports. Say "drop" with no adverb, or "drop with a stderr warning". The substantive reason, that a sessions-only root is the crashed-fresh-account case, stays.

## R2 [CONCERN] Restating the code (with multi-fact structure)

`claude/.claude/scripts/post-crash-sessions.py:1912-1917`.

Offending text: the whole docstring. It is one long sentence chaining a restatement, a parenthetical pointer and a dash-delimited reason.

Issue: under the rule under test, three clauses restate what the code and `_config_dir.py` show.
- "Declared roots from ~/.claude/transcript-config-dirs (or TRANSCRIPT_CONFIG_DIRS_FILE)" repeats `declared_roots_matching()`'s docstring (`_config_dir.py:90`) and the function name.
- "validated against … sessions/-or-projects/ check" repeats the lambda on line 1920.
- "declared_transcript_roots()'s projects/-only requirement" repeats the lambda at `_config_dir.py:167`.

The decision to keep is the choice of the looser predicate over `declared_transcript_roots()`'s, together with its reason. The pointer to `main()`'s `--config-dir` validation also stays, because it records that the two checks must agree. Packing all of this into one dash-and-parenthesis sentence also fails Multi-fact comment structure.

Proposed replacement:

```python
    """Use the same sessions/-or-projects/ check as main()'s --config-dir
    validation, not declared_transcript_roots()'s projects/-only one.

    The stricter check would drop a sessions-only root, the crashed-fresh-account
    case this tool exists for.
    """
```

If R1's correction is wanted, write "would drop (with a stderr warning)". The first sentence states the decision and the pointer. The second gives the reason. Nothing else survives.

Prior decisions: none supplied. The diff adds only this docstring. The sweep for PR-defined labels and "used to be" phrasing found nothing.
