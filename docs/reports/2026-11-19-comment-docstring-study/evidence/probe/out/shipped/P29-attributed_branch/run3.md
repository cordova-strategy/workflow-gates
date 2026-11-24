# comment-discipline-reviewer

Reviewed 1 file (`scope.py`); it carries one in-scope change, the new `_attributed_branch` docstring (diff lines 8-13).

## R1 [CONCERN] False or unsourced claim

File: `claude/.claude/scripts/transcript_analysis/scope.py:1087-1088`

Issue: the docstring says "Returns None — the "?" sentinel (see cmd_review_trace's docstring for the carry-forward convention this parallels)". Three parts of that do not hold:
- The function returns `None` and never produces "?". The "?" comes from each caller's own `or "?"` (`review_trace.py:308`, and `cost.py:827` via `attributed_branch or "?"`).
- Most callers map `None` to the empty string instead: `buckets.py:35`, `duration.py:32`, `fail_seq.py:64`, `judgment_pair.py:73`, `pr_link.py:65`, `struggle.py:59`, `subagent_mix.py:186,358`, `subagents.py:135,149` and `user_input.py:181` all use `or ""`. `skill_invocation.py:128` and `skill_pair.py:58` also use `or ""`. So `None` is not "the '?' sentinel".
- "Carry-forward convention this parallels" is contradicted by `scope.py:982-984`. That docstring says the branch index is "Unlike cmd_review_trace's position-based carry-forward". `_attributed_branch` resolves by timestamp through `_timeline_entry`, not by carry-forward. `review_trace.py` reaches the carry-forward through `_attribute_carried_branch` (`scope.py:1094`), a different function.

A narrower inaccuracy: `_branch_tag` (`scope.py:970-974`) also treats an empty or non-string `gitBranch` as absent. So "with no gitBranch" is narrower than what actually yields None.

Production failure mode: a maintainer who trusts the docstring will assume every consumer shows "?" for an unresolved record. They will also assume `_attributed_branch` shares review-trace's carry-forward semantics, and may "fix" one to match the other.

Required property: state only what `None` means here, with no sentinel or parallel claim. For example: "Returns None when no branch resolves: a main-thread record without a usable gitBranch, or a sidechain record in a session whose main thread carries none. Callers choose how to render None." Delete the `cmd_review_trace` cross-reference.

## R2 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/scope.py:1085-1086`

Issue: "the timeline step (_timeline_entry) followed by the pre-branch step (_attribute_pre_branch)" restates the one-line body `_attribute_pre_branch(*_timeline_entry(rec, ctx), ctx.pre_branch_run)`. The two helpers' own docstrings already define each step.

Required property: delete the sentence. If an opening line is kept, it should say only what is non-obvious: the function resolves a record's effective branch for per-record consumers such as `--branches`.

## R3 [CONCERN] Multi-fact comment structure

File: `claude/.claude/scripts/transcript_analysis/scope.py:1087-1090`

Issue: one sentence chains the return value, a dash-wrapped sentinel aside, a parenthetical cross-reference, and two separate None conditions.

Required property: after R1's fix, split it into one sentence per independent fact. Where the two None cases stay together, put them in a short two-item list, so the reader does not have to find the boundary between the conditions inside the run-on.
