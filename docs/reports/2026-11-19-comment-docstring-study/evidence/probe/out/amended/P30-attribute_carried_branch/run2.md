# comment-discipline-reviewer

Scope note: the dispatch added no prompt text that contradicts the agent file, so I set none aside. The rule-under-test bullet replaces "Don't restate the code" for this session, and I applied it. The `python-environment-conventions.md` rule attached mid-session does not bear on a comment review, so I ignored it.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/scope.py:1095-1097`, the new docstring on `_attribute_carried_branch`:

> Apply only the pre-branch step to a branch a positional consumer carried forward from the main thread, using the record's own timestamp so a record with none is never remapped.

- **Issue:** Every clause restates what static analysis of the repository finds, and none gives a reason that analysis can't find.
  - "Apply only the pre-branch step" restates the one-line body, which calls `_attribute_pre_branch` and nothing else.
  - "using the record's own timestamp" restates the `_parse_ts(rec.get("timestamp"))` argument.
  - "so a record with none is never remapped" restates `_attribute_pre_branch`'s own docstring (scope.py:1037-1041: "a None timestamp [is] never remapped") and its `ts is None` branch at line 1042.
  - "carried forward from the main thread" restates what the callers show (`review_rounds.py:261-264`, `review_trace.py:308`).
- **The one decision in it:** skipping the timeline step. The docstring gives no reason for it. The reason is in-repo: `review_rounds.py:19-21` says a round-opening record is never a sidechain record, and `review_trace.py:246-250` says the carried value already comes from main-thread order. Static analysis finds that, so the rule leaves it out of this docstring.
- **Failure mode:** Three `_attribute_*` functions sit within 10 lines of each other. A docstring that repeats the body and a neighbour's docstring drifts out of sync when `_attribute_pre_branch`'s None-timestamp handling changes.
- **Required fix:** Delete the docstring. A reader needing the skip-the-timeline-step rationale gets it from the pointer in `review_rounds.py`. If you want to keep a decision, add a pointer such as "Skips `_timeline_entry`; see review_rounds.py's module docstring." Don't write a shorter or corrected restatement of the body.

Checked against the other angles: deletion introduces no Verbosity, Readability, terminology, or unsourced-claim problem. The docstring has no PR-defined label, no "used to be X" framing and no unsourced number or causal claim. No Multi-fact finding: it is one sentence, and the restating-the-code finding covers it.
