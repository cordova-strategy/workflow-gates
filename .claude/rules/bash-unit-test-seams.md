---
paths:
  - "claude/.claude/hooks/**/*.sh"
  - "claude/.claude/scripts/**/*.sh"
---

## Bash unit-test seams

Where an extracted pure-bash helper belongs, in preference order:

1. Extend an existing sibling lib whose domain already covers it.
2. `claude/.claude/hooks/_lib.sh`, once two or more hooks need the helper.
3. A new `_<topic>-lib.sh` file beside the script, when neither above applies.

Already-seamed libs, as precedent:
- `claude/.claude/scripts/_worktree-lib.sh`
- `claude/.claude/scripts/_stow_migration_lib.sh`
- `claude/.claude/hooks/_lib.sh`, with its lib-level tests in
  `claude/.claude/hooks/tests/test_*lib*.py`.

**Naming: `_<topic>-lib.sh`.** `_stow_migration_lib.sh` is the older
spelling and is not being renamed.

**A `_`-prefixed `.sh` file in a hooks directory is a helper library, not a
hook.** `is_helper_library` in `claude/.claude/tests/helpers.py` is the one
rule the hook checks use to tell the two apart. A new `_<topic>-lib.sh` under
`claude/.claude/hooks/` needs no `docs/hooks.md` entry, no `# hook-class:`
header, and no edit to the hook checks to register it. A hook that
sources the library needs nothing further when its tests use the shared
builders `build_isolated_hook` and `symlink_hooks_lib_chain`. A hook tested
through a hand-built isolated hooks directory that symlinks or copies
`_lib.sh` and `_config.sh` by name must also link or copy the library there. Checks that scan the
content of every `.sh` file there still apply to it, exact-count pins
included. Two tests in `claude/.claude/hooks/tests/` fail it unless both hold:

- A hook, script, or other helper library sources it. A test does not count.
- No `settings.json` or plugin `hooks.json` registers it as a command.

The function-liveness test sources `_lib.sh` before each other library in
`claude/.claude/hooks/`, so a library may depend on `_lib.sh` at source time.
