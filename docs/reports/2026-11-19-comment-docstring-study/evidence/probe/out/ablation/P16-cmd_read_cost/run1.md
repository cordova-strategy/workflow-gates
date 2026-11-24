# comment-discipline-reviewer

Scope: 1 file reviewed (`read_cost.py`), 1 carried an in-scope comment/docstring change. Set aside: the session rule's "a pointer to the doc or symbol that holds a decision stays" exemption, as applied to this docstring, because the agent file requires a deletion finding for every docstring clause in the diff whatever it says.

## R1 [CONCERN] Prose restating the code

File: `claude/.claude/scripts/transcript_analysis/read_cost.py:414`

Issue: the added docstring is `"""See docs/transcript-analysis.md's `read-cost` section for the flags, the unit, and the publication scope."""` on `cmd_read_cost`. It is a docstring clause. The function body is one delegation line, `_read_cost_report(args, _read_cost_roots())`. The docstring states no design decision, only a pointer plus a list of what the doc covers.

Production failure mode: none at runtime. The cost is a docstring that restates what the function name and body already show, and it adds a doc-path reference that can drift.

Required property: delete the docstring. The agent's rule for docstring clauses is deletion, so the fix is deletion even though the clause is a pointer. If the maintainer wants to keep a pointer under the session rule's pointer exemption, they must make that call. The pointer must then be reduced to the path and section name alone, dropping "for the flags, the unit, and the publication scope", which only enumerates the doc's contents.

Verification limits, which are not findings:
- The snapshot has no `docs/` directory, so I could not confirm that `docs/transcript-analysis.md` has a `read-cost` section.
- `Grep` for `read-cost` across `*.md` in the snapshot returned no hits.
- Other source files cite `docs/transcript-analysis.md`, and `read_cost.py:400` does too, so the target likely exists in the full repo.
- If the maintainer keeps the pointer, they should confirm the section exists.
