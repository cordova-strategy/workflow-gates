# comment-discipline-reviewer

## R1 [CONCERN] Prose restating the code

- **File and line:** `claude/.claude/scripts/transcript_analysis/scope.py:719` (diff line 8)
- **Offending text:** `"""A subcommand calling this must also be in _SUBCOMMANDS_REFUSING_TOP_LEVEL_CONFIG_DIR."""`
- **Issue:** The docstring has one clause. The rule under test says to delete every docstring clause that is not a non-obvious design decision with a reason static analysis cannot find. This clause names no reason (why a caller must be in the tuple, or what outside the repository forces it). Static analysis of the repository finds the coupling. `cli.py:179` reads the tuple, and the tests at `test_transcript_cli.py:98`, `:160` and `:181` parametrize over it.
- **Production failure mode:** None. It is a comment-discipline defect only. The clause restates a relationship the code and tests already pin down.
- **Required property:** Delete the clause, which leaves the function with no docstring. The tuple's own comment at `scope.py:702` is the home for the coupling. If the pointer is worth keeping, put a reason in it: say why a subcommand that adds `--config-dir` must also refuse the top-level one.

Prior decisions: none supplied. Set-aside prompt text: none.
