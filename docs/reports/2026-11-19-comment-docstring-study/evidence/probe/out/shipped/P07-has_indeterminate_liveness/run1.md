# comment-discipline-reviewer

Set aside: the `python-environment-conventions.md` rules text that arrived mid-session. It names no site or scope for this review, so it changes nothing here.

Reviewed 1 file (`claude/.claude/scripts/post-crash-sessions.py`); 1 carried an in-scope change (one new docstring on `_has_indeterminate_liveness`).

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/post-crash-sessions.py:1048-1051`

Issue: the docstring reads "True when any entry in `entries` carries indeterminate liveness under `source_name` in `liveness` -- used to withhold Confirmed-clean-exit promotion when a same-session sibling from the *other* evidence source hasn't resolved to live or dead."
- Its first clause only repeats the one-line body, `any(liveness[(source_name, e.pid)] == "indeterminate" for e in entries)`, and the function name. The signature and types already show the inputs.
- Its second clause describes the sole caller's purpose, not this helper. The only call is at line 1237: `_has_indeterminate_liveness(lookup_entries, liveness, "lookup")`. The caller's own comments already hold that rationale at lines 1234-1236 and 1270-1273.
- "The *other* evidence source" is true only relative to the registry branch that calls it. The helper takes any `source_name`, so the phrase goes stale or misleads once a second caller exists.
- I checked the claim against the code and it holds at this diff's state. `dead_after_boot_fully_confirmed` (lines 1238-1243) includes `not lookup_sibling_indeterminate`, and "indeterminate" is a distinct third state from "live" and "dead" (lines 524-540). It is therefore not a False or unsourced claim, but it is a restatement.

Production failure mode: the docstring duplicates the caller's rationale (single-source-of-truth violation). It drifts from the caller if the call site changes.

Required property: delete the docstring. A shorter or corrected restatement still restates. The line 1234-1236 comment at the call site already carries the non-obvious "why", so nothing is lost.
