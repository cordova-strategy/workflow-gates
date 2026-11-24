# comment-discipline-reviewer

Reviewed 1 file (`routing_guard.py`); 1 carried an in-scope comment change (one added docstring).

Set-aside text: none. The `python-environment-conventions.md` rule text that arrived mid-session does not bear on this review and changed nothing.

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/transcript_analysis/routing_guard.py:693`

Issue: the added docstring `"""ASCII-only, so the text encodes the same under any locale."""` states what the function returns. Every part of it is findable by static analysis of the repository and the standard library:
- `json.dumps` defaults to `ensure_ascii=True` (standard library). `_serialize_capture` at line 694 passes no override, so the output is ASCII.
- `test_serializing_a_loop_keyed_by_a_non_ascii_or_lone_surrogate_model_yields_ascii_text` (`tests/test_transcript_routing_guard_capture.py:3527-3536`) asserts `text.isascii()`.
- The locale reason is the writer. `ledger_common._publish_new_file` (`ledger_common.py:123`) opens the file with `os.fdopen(fd, "w")`, which uses the locale encoding. `routing_guard.py:1507` also calls `built.text.encode("utf-8")`.

The claim is true, not false. Under the session's "Don't restate the code" rule, a clause that takes several files to find is still a restatement. The rule keeps only a decision with a reason that no analysis of this repository or the standard library reveals. No such reason is stated here.

Production failure mode: none at runtime. The docstring adds noise, and it restates ASCII-only output, which the test already pins.

Required property: delete the docstring. The ASCII property stays guarded by the existing test. If the maintainers want a guard against someone adding `ensure_ascii=False`, pass `ensure_ascii=True` explicitly. The code then states the decision, and no comment is needed.
