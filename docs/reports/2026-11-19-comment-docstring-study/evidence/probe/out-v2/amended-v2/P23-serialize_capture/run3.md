# comment-discipline-reviewer

Reviewed 1 file (`routing_guard.py`); 1 carried an in-scope comment change (one added docstring at line 693).

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/routing_guard.py:693`

Issue: the docstring reads `"""ASCII-only, so the text encodes the same under any locale."""`. The `json.dumps` call at lines 694-708 passes no `ensure_ascii`, so the ASCII-only output is the standard library's default (`ensure_ascii=True`). The function makes no decision here. The docstring describes what `json.dumps` already does, which the rule's "Delete every other clause, including anything … the standard library finds" covers. The payload is also built only from ints, bools, fixed keys and the `_STATE_ON`/`_STATE_OFF` values, so the repo's own code shows the output is ASCII.

Failure mode: the docstring pins no decision, so it won't flag a future `ensure_ascii=False` edit. It reads like a contract and gives a reviewer nothing to act on.

Required property: delete the docstring. If a decision is intended (ASCII output is required), express it in the code with an explicit `ensure_ascii=True` and a one-sentence reason that names an outside constraint. R2 shows no such constraint exists in this repo.

## R2 [CONCERN] False or unsourced claim

`claude/.claude/scripts/transcript_analysis/routing_guard.py:693`

Issue: the docstring's reason, "so the text encodes the same under any locale", names the wrong cause. `json.dumps` returns a `str` and never consults the locale. The only encoding step I found is `built.text.encode("utf-8")` at line 1507 (grep for `encoding|encode\(|write_text|\.write\(` found no other hits). That call pins UTF-8 explicitly, so locale independence comes from the explicit codec and not from the text being ASCII. The claim is only partly supported by its subject.

Failure mode: a reader concludes that locale-independence depends on ASCII-only output. They then either keep `ensure_ascii` for a reason that doesn't exist or drop the explicit `utf-8` believing ASCII covers it.

Required property: delete the claim, which R1 already requires. If anything is kept, the narrowest supported statement is that the text is encoded with an explicit UTF-8 codec at line 1507. That statement belongs at that call site only if it records a decision, and it should not be duplicated here.

Prior decisions: none supplied.

**Request changes**: delete the docstring.
