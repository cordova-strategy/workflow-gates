# comment-discipline-reviewer

Set aside: no prompt text contradicts the agent file. The python-environment-conventions reminder is unrelated to this diff.

Scope: 1 file reviewed (`scope.py`), 1 carries an in-scope comment change (one new docstring).

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/transcript_analysis/scope.py:719`

Issue: the added docstring reads `"""A subcommand calling this must also be in _SUBCOMMANDS_REFUSING_TOP_LEVEL_CONFIG_DIR."""`. It states a cross-file invariant and gives no reason for it.

Why it fails: the rule under test keeps only a decision with a reason that static analysis cannot find, and deletes anything that analysis of this repository's code and tests finds, "even if it is true and takes several files to find". Static analysis finds this invariant:
- Every `scope._add_extra_config_dirs_arg` caller is in the tuple at `scope.py:702-708`. I checked all 16 call sites across 15 modules. `cost.py` has two calls, for `cost` and `cost-trend`.
- `test_transcript_cli.py:195-201` (`test_subcommands_registering_their_own_config_dir_are_exactly_the_expected_set`) asserts that the registrants equal the tuple minus the four members that build their own root. A violation fails that test.

The claim is true, so this is not a False-claim finding. The "why" already lives in the comment above the tuple (`scope.py:694-701`), which is the single source for it. The docstring is also not a pointer to a decision: it states a requirement and carries no reason.

Required property: delete the docstring. The function name and the test already say what it does. If the maintainers want a pointer anyway, it would have to name the decision it points to. The tuple comment at `scope.py:694` already does that, so the docstring adds nothing.

Checked against the other angles: deleting leaves no text that could break another angle.
