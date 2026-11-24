# comment-discipline-reviewer

Set aside: the `python-environment-conventions.md` reminder that arrived mid-task. It is unrelated to comment review and does not change scope.

Reviewed 1 file (`scope.py`); 1 carried an in-scope comment change: the new one-line docstring on `_add_extra_config_dirs_arg` (scope.py:719).

No findings. The docstring is a single sentence stating a non-obvious constraint, so it is neither verbose nor multi-fact, and it does not restate the code. It uses no PR-defined label or prior-version framing. It is an instruction rather than a factual claim. Reading the code confirms it anyway: every `scope._add_extra_config_dirs_arg` caller found by Grep is a subcommand in the `_SUBCOMMANDS_REFUSING_TOP_LEVEL_CONFIG_DIR` tuple (scope.py:702-708).

**No comment-discipline concerns**
