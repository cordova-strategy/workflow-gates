# comment-discipline-reviewer

Scope: 1 file in the diff (`claude/.claude/scripts/transcript_analysis/scope.py`), 1 comment in scope (the new `_attributed_branch` docstring, lines 1085-1090 of the snapshot). I set aside the `python-environment-conventions.md` rule text that arrived mid-session. It names no site and does not change my scope.

## R1 [CONCERN] False or unsourced claim

`scope.py:1087-1088`: "Returns None — the "?" sentinel (see cmd_review_trace's docstring for the carry-forward convention this parallels)".

Issue: two claims in this clause are contradicted by the code.
- **"None is the '?' sentinel".** `_attributed_branch` returns `None` and nothing else. Most callers turn `None` into `""`, not `"?"`:
  - `buckets.py:35`, `duration.py:32`, `fail_seq.py:64`, `judgment_pair.py:73`, `pr_link.py:65`, `struggle.py:59`, `subagent_mix.py:186` and `:358`, `subagents.py:135` and `:149`, and `user_input.py:181` all use `or ""`.
  - `skill_invocation.py:128` and `skill_pair.py:58` also use `or ""`.
  - Only `cost.py:827` (`attributed_branch or "?"`) renders `"?"`. `cost.py:489-499` documents `"?"` as that consumer's unresolved-branch label.
- **"Parallels the carry-forward convention".** `cmd_review_trace`'s docstring (`review_trace.py:767-774`) says an event takes the last non-empty branch carried forward. For a main-thread record with no `gitBranch`, `_attributed_branch` returns `None` through `_timeline_entry` (`scope.py:1076`) and does not carry anything forward. `_session_branch_index`'s docstring (`scope.py:981-983`) says the timeline is "Unlike cmd_review_trace's position-based carry-forward".

Failure mode: a reader filtering with `--branches` will expect a `"?"` bucket, or carried-forward branches, that most consumers never produce.

Required property: state only what the function does. For example, "Returns None when the record has no resolvable branch; callers choose how to render it (cost.py shows `?`)." Drop the "parallels" cross-reference, or say the function differs from `cmd_review_trace`'s carry-forward.

## R2 [CONCERN] Multi-fact comment structure

`scope.py:1085-1090`: the docstring is one sentence plus one long sentence. The second chains an em-dash aside, a parenthetical cross-reference, and two separate None conditions.

Issue: a reader must parse the whole sentence to separate the sentinel claim, the pointer to another docstring, and the two None cases.

Required property: one sentence per fact. Put what the function does first. Then give the None cases as their own sentence, or as a two-item list (main-thread record with no `gitBranch`; sidechain record in a session with no branch-bearing main-thread record). Keep any caller-rendering fact as a separate sentence. This must come after R1's content fix, so the fix does not reintroduce the "?" or "parallels" claims.

## R3 [FYI] Restating the code

`scope.py:1085-1086` and `:1088-1090`: "the timeline step (_timeline_entry) followed by the pre-branch step (_attribute_pre_branch)", and the two None conditions.

Issue: the one-line body, `_attribute_pre_branch(*_timeline_entry(rec, ctx), ctx.pre_branch_run)`, already shows the composition. `_timeline_entry`'s docstring (`scope.py:1067-1072`) already states the two None cases, so this duplicates its single source of truth.

Required property: delete the composition clause. Keep only the non-obvious purpose ("the branch a record counts toward for --branches filtering") and, if wanted, a pointer to `_timeline_entry` for the None cases instead of a restatement.
