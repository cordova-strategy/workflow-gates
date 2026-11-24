# comment-discipline-reviewer

Reviewed 1 file (`scope.py`); 1 carried an in-scope comment change: the new one-line docstring on `_add_extra_config_dirs_arg` (scope.py:719).

No comment-discipline concerns.

- The docstring is an instruction (a rule for callers), not a factual claim, so False or unsourced claim does not apply.
- The rule matches the code anyway. Every subcommand calling `scope._add_extra_config_dirs_arg` is a member of `_SUBCOMMANDS_REFUSING_TOP_LEVEL_CONFIG_DIR` (scope.py:702-708). `test_subcommands_registering_their_own_config_dir_are_exactly_the_expected_set` (test_transcript_cli.py:195) pins the same relationship.
- The coupling is not visible from the function body, so Prose restating the code does not apply.
- The sentence leads with the instruction and carries one fact. There is no PR-defined label or "used to be" framing.
