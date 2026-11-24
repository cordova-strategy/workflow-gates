# comment-discipline-reviewer

No findings.

Scope: 1 file in the diff (`claude/.claude/scripts/transcript_analysis/scope.py`), 1 added comment site (the new docstring on `_add_extra_config_dirs_arg`, line 719 at the diff's state).

- Set aside: a `python-environment-conventions.md` rules file that arrived mid-session. It has no bearing on this review's scope.
- Rule under test, "Don't restate the code": the docstring names one coupling decision and points at the symbol that holds it, `_SUBCOMMANDS_REFUSING_TOP_LEVEL_CONFIG_DIR`. The comment above that tuple (scope.py:694-701) and `cli.main()` (cli.py:171-183) carry the reason, which is that a top-level `--config-dir` must not validate against a different account than the subcommand scans. A pointer to the symbol that holds a decision stays, so I report no restating-the-code finding. A shorter form would drop the pointer and the instruction a future subcommand author needs.
- False or unsourced claim: the claim holds. Every caller of `scope._add_extra_config_dirs_arg` (15 call sites across 14 modules, per `Grep`) registers `--config-dir`, and `test_transcript_cli.py:195-201` pins that the registrants are exactly the tuple's members minus the four that register no flag (`cost-counts`, `period-cost`, `review-cost-by-size`, `read-cost`, at test_transcript_cli.py:156-158). The claim is one-directional ("calling this ⇒ in the tuple"), and that matches the tuple's contents (scope.py:702-708), including `cost-trend` for the second `cost.py` call at line 1324.
- No PR-defined labels, "used to be" framing, multi-fact or readability issues: it is a single sentence stating one fact.

**No comment-discipline concerns**
