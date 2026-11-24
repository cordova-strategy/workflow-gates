# comment-discipline-reviewer

Reviewed 1 diff file; it carries 1 in-scope comment change (the new docstring on `_serialize_capture`).

## R1 [CONCERN] Restating the code
routing_guard.py:693
Issue: the docstring `"""ASCII-only, so the text encodes the same under any locale."""` states an output property that `json.dumps` supplies by default (`ensure_ascii=True`, a standard-library default). The call at lines 694-708 sets no `ensure_ascii` argument, so the code shows nothing about it, but static analysis of the standard library does. The stated reason is not a decision this repository makes or an outside force, so it does not qualify as a kept decision under the rule.
Production failure mode: none at runtime. The docstring documents behavior nobody chose here, and it reads as a guarantee the code does not assert.
Required property: delete the docstring. If ASCII output is a deliberate requirement, state it in code with `ensure_ascii=True`, as `pr_cost_ledger.py:202` does, instead of in prose.

## R2 [CONCERN] False or unsourced claim
routing_guard.py:693
Issue: the claim "so the text encodes the same under any locale" is contradicted by its subject. The only encoding of this text is `built.text.encode("utf-8")` at routing_guard.py:1507, which names the codec explicitly, so locale never affects the encoding whether or not the text is ASCII. `_serialize_capture` also returns `str`, so it encodes nothing itself. A repo-wide grep of `routing_guard.py` for `encode(`, `encoding=`, `write_text` and `write_bytes` found no locale-dependent encoding path. I did not trace what happens to the bytes after line 1507.
Production failure mode: a future reader takes ASCII-only output as the thing that protects against locale differences and drops the explicit `utf-8` at line 1507, or treats a switch to `ensure_ascii=False` as unsafe for a reason that does not exist.
Required property: delete the docstring (see R1). If any rationale is kept, it must name the actual constraint and its source.
