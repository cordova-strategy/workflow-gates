# comment-discipline-reviewer

Reviewed 1 file (scope.py); 1 docstring added in scope (`_attributed_branch`, scope.py:1085-1090). No text set aside. Under the session's "Don't restate the code" rule every clause below is deleted, so the whole docstring goes.

## R1 [CONCERN] Prose restating the code

scope.py:1085, clause "Resolve one record's branch for --branches filtering".

Issue: the name `_attributed_branch`, its `rec` and `ctx` parameters and its `str | None` return type already say this. The `--branches` consumers are found by grepping the callers (e.g. cost.py:827).

Fix: delete the clause.

## R2 [CONCERN] Prose restating the code

scope.py:1085-1086, clause "the timeline step (_timeline_entry) followed by the pre-branch step (_attribute_pre_branch)".

Issue: the one-line body at scope.py:1091 shows this call chain. Both callees carry their own docstrings (scope.py:1037, scope.py:1064).

Fix: delete the clause. No decision is named here, only the order of calls.

## R3 [CONCERN] Prose restating the code

scope.py:1088-1090, clause "for a main-thread record with no gitBranch, and for a sidechain record in a session with no branch-bearing main-thread record".

Issue: this is the None-return condition. It restates `_timeline_entry`'s branches (scope.py:1075-1078) and its docstring (scope.py:1071-1072). It also leaves out the pre-branch step's passthrough. Even a corrected version of the clause would still restate.

Fix: delete the clause.

## R4 [CONCERN] Prose restating the code, with an inaccurate pointer

scope.py:1087-1088, clause "Returns None — the "?" sentinel (see cmd_review_trace's docstring for the carry-forward convention this parallels)".

Issue:
- `_attributed_branch` returns plain None. The "?" mapping happens in its callers (review_trace.py:308 uses `... or "?"`, and cost.py:827 uses `attributed_branch or "?"`), so a grep finds it.
- The pointer would be kept if it led to a decision, but it leads to none here. cmd_review_trace's docstring (review_trace.py:767-774) describes last-non-empty carry-forward. `_attributed_branch` does not carry forward. It uses the timeline lookup, and the carry-forward consumer is `_attribute_carried_branch` (scope.py:1094). "Parallels" therefore overstates the relationship, and a reader following the pointer finds a different mechanism.

Fix: delete the whole clause, pointer included. If the "?" convention needs a home, it is review_trace.py's docstring, which already holds it.

**Request changes**: delete the docstring. Nothing in it is a non-obvious design decision with a reason static analysis cannot find.
