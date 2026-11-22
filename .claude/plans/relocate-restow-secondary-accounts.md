# Re-point declared secondary Claude config accounts when the checkout is relocated

## Context

Goal: make `relocate-claude-config` re-link every secondary Claude config account declared in `~/.claude/transcript-config-dirs`, not only `~/.claude`, after the checkout moves. This plan is PR 2 of four: PR 1, PR 2, PR 2b and PR 3. PR 1 (merged as `585527f7`) re-links the personal `claude-skills` package, exits 3 on a failed follow-up and guards the backup dir. PR 3 is `git worktree repair` over the moved checkout's linked worktrees.

Ask: "The move must re-link every Claude config account on the machine programmatically, not by hand." (engineer, handoff goal), plus "Reuse transcript-config-dirs (Recommended)" and "Wait for PR 2 and PR 3" (option labels the engineer selected during PR 1), plus "step 1 sounds good" (engineer, approving the PR 2 design in the handoff, which had the script re-stow each listed dir). Asked which mechanism to use, the engineer selected "Re-point in place (Recommended)", which supersedes the re-stow mechanism. Asked whether marketplace registration belongs in this PR, the engineer typed "No manual steps please. That just leads to errors. So probably split PR links in this one marketplace in next. Ask the architect." This PR therefore re-points links only. Marketplace registration for listed accounts is the next PR, so that the goal leaves no manual step for a link this repo made. The engineer chose to accept a left-alone link as a residual (row47).

Why now: the checkout is about to move to a new location. After the move, a secondary account's config dir still holds symlinks into the old path. A session under that account then loads none of this repo's settings, hooks or skills, and a later stow run from the new location treats the stale links as conflicts. Today the script's closing text lists those accounts as manual work.

Intended outcome:

- With `~/.claude/transcript-config-dirs` present, each listed dir other than `~/.claude` has its links re-pointed at the new location, in place, by M1's rule. A dir with nothing to re-point is left alone. With no file when this step runs, no listed dir is touched.
- A copy of each replaced link goes to the backup dir, and nothing is deleted. Each copy gets a name unique to its link, so two same-basename links in one run no longer overwrite each other's backup. Backup names change whether or not the file exists. This closes the deferred collision finding from PR 1.
- A listed account gains no link it did not already hold, so no untracked-entry filter is needed.
- `transcript-config-dirs` is the only contract. The script and its docs name no private repository and depend on none.
- A failed account does not stop the run and feeds the existing exit 3 and `--repair` retry line.
- The README "Repo relocation" section, `docs/scripts.md` and `CHANGELOG.md` are updated. The "Not done by this command" accounts bullet narrows to unlisted dirs plus the listed accounts' marketplace registration, which the next PR automates.
- The next PR (PR 2b) automates marketplace registration for the listed accounts and removes that remaining manual step. This plan records it as out of scope here.

Constraints and scope guards:

- Keep the plan and diff small; PR 1's diff overshot its estimate, so split if the projection runs high.
- Stay out of the files a peer branch owns: CI config, `CODE_OF_CONDUCT`, `CONTRIBUTING`, `SECURITY`, `_lib.sh`, `deny-private-project-refs.sh`, `require-stow-reminder.sh` and their tests. Never run `git remote set-url`.
- Plan and docs use placeholder paths and names only (public repo).
- The deferred EXIT-trap retry-line change is a separate follow-up unless the design folds it in at near-zero cost.

## Approach

Once the move's own steps have run, both modes read `~/.claude/transcript-config-dirs`. In each listed dir other than `~/.claude` and the checkout, they re-point every link that sits at one of this repo's package paths, no longer resolves, and has text ending in that path. They find those links by probing only the positions the checkout's packages hold. Each link is copied to a uniquely named backup, then replaced by an atomic rename. The run prints one outcome line per dir and feeds a failed dir into the existing exit 3 and `--repair` retry.

The design re-points links in place rather than re-stowing (M1). So a listed dir gains no link it did not already hold, and no `git` call or untracked-entry filter is needed. The walk takes its positions from the checkout, never from a listing of the account's tree, so it reads no name the account holds. For a destination whose package roots are real directories, the checkout's package subtrees also bound how far it goes (M1, Out of scope on a linked package root). Backup names become unique per link (M3), which also closes PR 1's deferred same-name collision. The pass runs after the manifest write and the installed-copy refresh, so a listed dir that blocks cannot hold up the relocation itself (M4).

A listed account's marketplace registration stays manual in this PR, and the closing text names it as that account's remaining step. The engineer accepted a link the run reports as left alone as a further residual (M4, row47). The next PR, PR 2b, automates it (row26, row27, Out of scope). The cut is clean in both directions. This PR's links, docs and tests stand alone, and PR 2b reuses its reader, runner loop, failure label and test builders unchanged. Set aside:

- Folding registration in here. The existing sync function has two arms a listed account must not take (row25), so it needs a variant plus a `claude` shim per account in the tests, on a diff already near 880 lines.
- Landing M3 first as its own PR. M1's backups need it (row9), and moving it out cuts about 60 lines while adding a fifth PR and a merge dependency, leaving this one near 820.

**Root problem.** After a move, each config dir listed in `~/.claude/transcript-config-dirs` keeps stow-made links into the old checkout, which no longer resolve. A session under that account then loads none of this repo's settings, hooks or skills, and the script leaves those dirs to the user.

**Givens** (fixed, outside this design's reach):

- **G1 — the repo depends on no other repository.** A repo rule, so the script and docs name no installer for secondary accounts. [verified: `CLAUDE.md` § "Working in this repo"]
- **G2 — a peer branch owns CI config, `CODE_OF_CONDUCT`, `CONTRIBUTING`, `SECURITY`, `_lib.sh`, `deny-private-project-refs.sh`, `require-stow-reminder.sh` and their tests.** Another party owns them. [unverified: relayed by the dispatcher]
- **G3 — GNU Stow's ownership rule (row7).** Vendor behavior that decides whether an account's own installer can later restow over a re-pointed link.
- **G4 — whatever populated a listed dir is outside this repo.** Another party owns it, so this repo does not know which entries it linked or which it ignored (row6).

**Rows:**

1. The script runs as a real-file copy at `~/.local/bin/relocate-claude-config`, sources nothing, and must not depend on `~/.claude` being intact. So it cannot load `_config_dir.py` or any helper from beside `$0`. [verified: `relocate-claude-config.sh:1-14`]
2. `_config_dir.py`'s `declared_roots_matching` owns the roots-file grammar. [verified: `_config_dir.py:89-158`]
    - It splits the file with `str.splitlines()`, which handles CRLF.
    - It trims ASCII whitespace padding.
    - It skips blank lines and lines starting with `#`.
    - It replaces a leading `~` or `~/` with `$HOME`.
    - It skips a line that is not absolute or not a directory, with a warning naming its line number only, because "the path identifies an engagement".
    - It drops a line whose resolved path an earlier line gave.
    - An absent or unreadable file is a silent no-op.
3. `cleanup-merged-branches.sh`'s `read_configured_roots` is the bash form of the same grammar, which `_config_dir.py`'s docstring names as its source. That script runs top-level code, so it is not a sourceable library. [verified: `cleanup-merged-branches.sh:255-290`; `_config_dir.py:103-110`]
4. `stow-packages.sh` lists `claude` targeting `.` and `claude-skills` targeting `.claude`. The script's `RELINK_PACKAGES` copy of the non-`claude` row is pinned by `test_stow_packages.py`. [verified: `stow-packages.sh:26-29`; `relocate-claude-config.sh:66-68`; `test_stow_packages.py:87-117`]
5. A config dir named by `CLAUDE_CONFIG_DIR` takes the place of `~/.claude`. So in a listed dir, the `claude` package's `.claude/` subtree and the `claude-skills` package mirror at the dir's top, and `claude/.local/bin` maps to `~/.local/bin`, which no config dir holds. [verified: `_config_dir.py:22-41`; row4]
6. `stow-packages.sh`'s header names a downstream consumer that installs this repo's content into a non-`$HOME` config dir. What that consumer links, and with which ignores, is not in this repo. [verified: `stow-packages.sh:4-10`]
7. Stow counts a link as its own when its text is relative and, joined to the link's parent, falls under the stow dir. It treats any other link at a package path as a conflict. It resolves its target and stow dirs to physical paths. [unverified: PR 1's plan rows 4 and 83 record reading Stow 2.4.1 `Stow.pm`; not re-read this session. The ownership test pins the case this plan relies on.] Stow also refuses a package when a real file sits at one of its paths. [unverified: not re-read this session]
8. After a move, every link a listed dir holds into the old checkout no longer resolves. [unverified: follows from the links' text naming the old path; PR 1's plan row 9] The manifest records the old path until `finish_relocation` rewrites it, and that rewrite runs before an exit 3, so a `--repair` retry after an exit 3 cannot learn the old location. [verified: `relocate-claude-config.sh:110-116, 441-446, 608-613`]
9. `_quarantine_if_dangling` moves a dangling link to `$BACKUP_DIR/<basename>.$$`, so two same-named links in one run share a backup name and the later move replaces the earlier backup. [verified: `relocate-claude-config.sh:322-345`] Every listed account holds a `hooks` link, so `--repair` with one listed account would collide on every run. [unverified: inferred from row5]
10. Existing tests read backups only as `<name>.*` entries at the top of the backup dir, and match `could not move <path> into <backup dir>`. [verified: `test_relocate_claude_config.py:513, 571-573, 600-604, 978, 1000, 1118, 1273, 1300, 1319, 1343`]
11. Userland behavior the design relies on, on BSD and GNU. The new tests exercise each on macOS locally and on CI's Linux.
    - `mktemp <dir>/<prefix>.XXXXXX` creates a new empty regular file under a unique name, accepts a dotted prefix, and fails when `<dir>` is missing or unwritable. [verified on macOS by the round-1 platform review; unverified on GNU]
    - `ln -s -- <text> <name>` with no force flag fails when `<name>` exists, and creates the link inside `<name>` when `<name>` is a directory or a link to one. [unverified; the round-3 SDET review observed the link-to-directory case on macOS]
    - Without `--`, `ln` parses a `<text>` that starts with `-` as options. [unverified: the round-3 SDET review]
    - `ln -sf -- <text> <file>` replaces a regular file, on BSD by unlinking it and then creating the link. [unverified]
    - `mv -f -- <link> <dest>` within one directory renames over a `<dest>` that is a dangling symlink, atomically. [unverified: rename(2) semantics]
    - `mv -f` of a symlink onto a regular file replaces the file, and across filesystems it copies and then unlinks. [unverified: round-1 platform review R8]
    - `mv` onto a destination that is a symlink to a directory moves the source into that directory. [unverified: PR 1's plan row 11]
12. `relink_packages` runs each unit as an `if` condition, records a failure and never aborts. `report_relink_outcome` lists the failures and ends with the `--repair` line, and both modes then exit 3. [verified: `relocate-claude-config.sh:480-493, 523-565, 608-613, 632-637`]
13. Three test lines read `RELINK_FAILED_PACKAGES` by name. [verified: `test_relocate_claude_config.py:916, 919, 947`]
14. The closing text's first manual bullet and README "Repo relocation" list every other account, listed ones included, as manual, with `register-marketplace` for its marketplace registration. [verified: `relocate-claude-config.sh:508-518`; `README.md:471-474`] Of that text, existing tests assert only the `Not done by this command:` heading. [verified: `test_relocate_claude_config.py:227, 399`; a grep of every `test_*.py` for `register-marketplace` and `transcript-config-dirs` finds neither relocate test file]
15. The header names `<new-path>` as semi-trusted and says an agent can be steered into running the script. [verified: `relocate-claude-config.sh:16-25`] That the script's output can then reach an agent transcript is this plan's reading. [unverified: the header does not say it] The run's own process runs no code from `<new-path>`, but the run installs `<new-path>`'s copy of this script into `~/.local/bin` and links `<new-path>`'s hooks and skills into `~/.claude`. Both modes run `stow --adopt claude` from `<new-path>`, then `relink_packages` stows its `claude-skills` into `~/.claude`. [verified: `relocate-claude-config.sh:441-446, 475, 487, 604-608, 628-632`]
16. `test_relocate_claude_config.py` is 1,397 lines, over the repo's 1,000-line limit for test files. [verified: line 1397 is the file's last line, and the round-2 SDET review's `wc -l` gives 1,397; `docs/design-decisions/code-file-line-limit.md:19`] `claude/.claude/scripts/tests/` is a package, so a sibling test module imports in relative form, which `TestNoBareSameDirectorySiblingImports` allows. [verified: `claude/.claude/scripts/tests/__init__.py`; `.claude/rules/test-tree-packaging.md`] Its families mostly share helpers through `_<family>_helpers.py` modules, and one module, `test_transcript_review_rounds.py:42`, imports from a sibling test module. [unverified: the round-1 SDET review's count]
17. `TestClaudeCliMissing` runs the script with a PATH of named tools, and its comment says that list holds every external tool the script calls. Its run writes no roots file and leaves no dangling link, so it reaches none of this PR's new tool calls. [verified: `test_relocate_claude_config.py:704-739`]
18. The scripts conftest sets `TRANSCRIPT_CONFIG_DIRS_FILE` to a missing file in an autouse fixture, and `_script_env` copies the environment into each run. So a script-side reader honoring that variable would not see a test's roots file. [verified: `conftest.py:1701-1710`; `test_relocate_claude_config.py:156-163`]
19. The roots file is the account list. [engineer-verified: "Reuse transcript-config-dirs (Recommended)"]
20. The goal is programmatic re-linking of every account. [engineer-verified: "The move must re-link every Claude config account on the machine programmatically, not by hand."] "Every account" means every account listed in the roots file. [verified: PR 1's plan row 27 records "Declared accounts only (Recommended)" as the engineer's label]
21. The engineer approved going ahead with this PR. [engineer-verified: "step 1 sounds good"] Asked which mechanism to use, the engineer chose re-pointing in place over re-stowing. [engineer-verified: "Re-point in place (Recommended)"]
22. With no readable roots file when the pass runs, the pass does nothing and prints nothing. With one, a listed dir with nothing to re-point is not written, and each replaced link's text is kept in a backup copy. [unverified: the session's Context, relayed from the handoff]
23. PR 1's plan recorded these as PR 2's inherited design. [verified: `.claude/plans/relocate-restow-accounts.md:389-397`; its row 29 marks the design as the session's relay of an architect consult]
    - Re-point listed dirs in place, restoring each dir's previous links.
    - Replace each stale link atomically: a sibling temporary link with no force flag, a re-check that the destination still dangles, then `mv -f`, removing the temporary link on any failure.
    - State in the header and README that `--repair` re-points every declared account, with a crafted-destination `--repair` test holding an allow and a deny assertion.
    - Read the roots file through `<new-path>`'s `_config_dir.py`, name a dir by ordinal with a durable ordinal-to-path map, and take the backup dir from `mktemp -d`.
24. The Context's "A listed account gains no link it did not already hold" is met by replacing only links a dir already holds. A re-pointed link gets relative text as Stow writes it, whatever form its old text had. [unverified: this plan's reading]
25. `sync_marketplace_registration` adds a registration when the account has none. [verified: `relocate-claude-config.sh:415-421`] It re-registers an account recorded at any other path, whether or not that path still exists. [verified: `relocate-claude-config.sh:423-438`]
26. Asked whether marketplace registration belongs in this PR, the engineer asked for no manual steps and proposed splitting it into the next PR, leaving the call to this plan. [engineer-verified: "No manual steps please. That just leads to errors. So probably split PR links in this one marketplace in next. Ask the architect."]
27. This PR re-points links only, and PR 2b automates the listed accounts' marketplace registration. So once PR 2b lands, a listed account needs no manual step for a link the shape rule recognizes. A link the run reports as left alone stays the residual the engineer accepted (row47). [unverified: this plan's judgment on the split row26 proposes]
28. Asked whether to split this plan, whose `Projected diff:` is about 450 changed lines, into smaller PRs, the engineer chose to keep one PR. [engineer-verified: "Proceed anyway"]
29. Asked whether the unique-backup-name change (M3) is in scope for this PR, the engineer chose to keep it. [engineer-verified: "In scope (Recommended)"]
30. Asked whether the `Ask:` line's first quote is their wording and still stands, the engineer confirmed it. [engineer-verified: "Yes, my wording, still stands"]
31. Asked how to handle the finding that `--repair <new-path>` now reaches every listed account, the engineer chose disclosure. [engineer-verified: "Disclose it (Recommended)"]
32. The selected option keeps `--repair` re-pointing listed accounts, and states in the header that `--repair`'s destination reaches every listed account, and in README and CHANGELOG that it is trusted for each of them. [unverified: the dispatching session's option description, not the engineer's words]
33. The script runs under `set -euo pipefail`. A unit run as an `if` condition has errexit off, so each of its steps checks its own status. `relink_packages` cannot fail and ends `return 0`, so its bare call in the errexit-on main shell cannot abort. [verified: `relocate-claude-config.sh:61, 448-452, 480-493`]
34. `relink_packages` resets the failure array on entry. [verified: `relocate-claude-config.sh:482`]
35. `_readlink_f` prints a physical path when `readlink` exists, or returns 1 with no output and with `readlink`'s own stderr discarded. `canonicalize_for_comparison` falls back to its input instead. Without `readlink` it resolves only the parent and appends the final name, so a final-component link stays unresolved. [verified: `relocate-claude-config.sh:127-151`]
36. Beyond the shared path validation, `--repair` checks its destination only for `.claude-plugin/marketplace.json`. [verified: `relocate-claude-config.sh:104-106, 303-305, 619-624`]
37. `docs/transcript-analysis.md` § "Corpus scope: the declared-roots file" is the roots file's contract home and names its other reader. [verified: `docs/transcript-analysis.md:76-88`]
38. The script already hardcodes the `claude` package's `.claude` subtree when it resolves the live checkout. [verified: `relocate-claude-config.sh:173`]
39. `TestRelinkPackagesBatch` sources the script and calls a unit directly, and the old test module defines `_plant_unusable_backup_dir` and `_BACKUP_DIR_REFUSAL_FRAGMENTS`. [verified: `test_relocate_claude_config.py:403-422, 897-958`]
40. A relative link's text resolves from the directory that physically holds the link. Probing a named entry needs search permission on its parent only, and a probe under a directory without it reports the entry absent. [unverified: POSIX path resolution; the nested, symlinked-parent and unsearchable test cases pin it]
41. The roots file is an ordinary file in `~/.claude` that no hook guards. [unverified: the round-1 security review's grep of `claude/.claude/hooks/`]
42. After round 1 raised the `Projected diff:` to about 710 changed lines, asked whether to split or proceed, the engineer chose to keep one PR. [engineer-verified: "Proceed anyway (Recommended)"]
43. Asked whether `docs/transcript-analysis.md` belongs in this PR's Critical files, the engineer chose to keep it. [engineer-verified: "Keep it (Recommended)"]
44. `finish_relocation` runs the marketplace sync, the manifest write and the installed-copy refresh in the errexit-on main shell. Of the runners' state, `report_relink_outcome` reads only the failure array, and both modes call it after `finish_relocation`, just before the exit-3 check. [verified: `relocate-claude-config.sh:441-446, 523-565, 608-613, 632-637`]
45. Bash evaluates an indexed array's subscript as arithmetic, which runs a command substitution inside it, so a name from the checkout, the account or the roots file used as a subscript can run code. An associative array does not evaluate its key, but an empty associative key aborts the command that uses it. [unverified: the dispatching session's and the round-2 and round-3 platform reviews' probes on bash 5.3, none on CI's bash 5.2] The repo's shell floor is bash 5.2, so the design adds no version check and no bash 3.2 fallback. [verified: `README.md:111`; `.claude/rules/shell-floor.md`]
46. shellcheck 0.11 reports SC2034 only for a name nothing in the file reads, and a helper function's read counts. It reports SC2030 and SC2031 when a helper that reads a subshell-bodied function's locals is defined after that function, and neither when the helper comes first. [unverified: the round-3 platform review's probe with shellcheck 0.11.0, not re-run this session] The repo pins shellcheck 0.11 and sets no `severity=`, so the default `style` floor reports every level. [verified: `requirements-dev.txt:5`; `.shellcheckrc:12-14`] In the script, `_quarantine_if_dangling` sits above `_relink_package`. [verified: `relocate-claude-config.sh:332, 453`]
47. Asked whether a link left alone, because the shape rule does not recognise it, is an acceptable residual manual step for a listed account, the engineer chose to accept it. [engineer-verified: "Acceptable residual (Recommended)"]
48. Asked again, with the projection at about 830 changed lines and the round-3 fixes adding roughly 60 to 100, whether to split or proceed, the engineer chose to keep one PR. [engineer-verified: "Proceed anyway"]
49. Python's `str.splitlines()` also breaks a line at a lone CR, VT, FF and several other separators, which bash's `read` does not. So a roots file holding one gives the two readers different line numbers. [unverified: the round-3 SDET review, from Python's documented `str.splitlines` boundaries; not re-read this session]
50. Removed: the walk applies no `test -L` at a root, whose `/.` form follows the link. The exposure is recorded in Out of scope (row53).
51. After round 3 raised the `Projected diff:` to about 1,000 changed lines, asked whether to split or proceed, the engineer chose to keep one PR. [engineer-verified: "Proceed anyway"]
52. Asked whether both modes keep the shape rule, re-pointing any dangling link of this repo's layout whichever checkout its text named, the engineer chose to keep it in both modes. [engineer-verified: "Keep in both modes (Recommended)"]
53. After round 7, asked whether to apply the architect's cuts to the plan, the engineer chose all five. The cuts: the disclosure that the checkout can supply the roots file and its test, the remedy text reduced to deleting the dir's line, the duplicate reader-state test, `temp-name-taken` collapsed to one case, and the root physical-path check with its tests. [engineer-verified: "Cuts 1-5 (Recommended)"] The reasons are the architect's, not the engineer's: the repo already says the file is the user's, and the same stow already links the destination's hooks. [unverified: the round-7 architect consult]
54. The plan's declaration is `declared: production, untrusted-input`, with the actors cooperative. A cooperative human or agent runs this command, so a finding that needs a hostile human to craft a value is out of scope. A value that a steered cooperative agent could emit, or that arrives through content the agent read, is in scope. The two axes differ: actor intent is cooperative, and input trust is not assumed. The engineer said: "We are dealing with cooperative agents and cooperative humans." [engineer-verified: "We are dealing with cooperative agents and cooperative humans."] "Cuts 1-5 (Recommended)" (row53) was chosen against the earlier Out of scope text. Asked again whether cut 5 (removing the root physical-path check) should stay once its re-pointing exposure was restated, the engineer gave the statement quoted above and selected no label. The plan treats that statement as keeping cut 5. [unverified: the dispatching session's reading] The tier wording follows a peer session's reading of `ROUTING.md`'s cumulative ladder. [unverified: the peer's interim finding, not re-read by this session]
55. After round 10 re-derived the `Projected diff:` at about 1,300 changed lines, asked whether to split or proceed, the engineer chose to keep one PR. [engineer-verified: "Proceed anyway"]
56. A listed dir that the reader or runner cannot use (unreachable, not a directory, or `readlink` absent) prints its warning, is reported in the closing text's unlisted-dirs bullet as not re-linked, and does not change the exit status or stop the `Done.` line. A user re-links it by correcting the line or making the dir reachable, then running `--repair`. This is the plan's own choice, which row47 does not cover. [unverified: the plan's judgment, from M2 and M4]
57. The test files beyond `test_relocate_claude_config_declared_dirs.py` (helpers, integration, probes, roots_file) were each accepted by the engineer in earlier sessions, under the labels "Split the integration tests out (Recommended)", "Yes, stage it (Recommended)" and "Apply all three (Recommended)". [unverified: the labels come from the handoff and were not re-checked against the engineer's messages this session]

**Mechanism justifications:**

- **M1 — re-point stale links in place, at positions taken from the checkout** (anchors: root, row5, row6, row7, row8, row11, row15, row21, row22, row23, row24, row31, row32, row33, row36, row37, row38, row40, row41, row45, row46).
  - `_repoint_declared_dir <new-real> <dir-real> <line> <root>...` is a function whose body is a subshell, like `_relink_package`, run as an `if` condition (row33). Both paths are physical, from the runner (M4). Its walk and per-link helpers share its locals through bash's dynamic scope, so no counter reaches the main shell. Those helpers sit above it in the file (M7, row46). Every variable that changes from one level of the walk to the next is `local` to the function that sets it.
  - The walk:
    - It starts at the listed dir, position `.`. For each root whose `<new-real>/<root>/<rel>` is a real directory (`-d` and not `-L`), it takes each entry name under it, globbed with `nullglob` and `dotglob`, as a child position.
    - At position `.` only the directory test applies, since `-L` on `<root>/.` resolves the root. The no-follow test applies from one level below each root.
    - The checkout side thus applies the same no-follow test as the account side at every level below a root.
    - A position two roots share is visited once. A name from a later root is skipped when an earlier root walked at the same position holds that name (`-e` or `-L`).
    - No array subscript takes a name or path read from the checkout, the account or the roots file. So no such name is evaluated as arithmetic (row45).
    - Before probing inside a directory, it checks search permission on it. Without it, it prints `could not search <rel> in the dir on line <N> of ~/.claude/transcript-config-dirs` through `err` (on stderr, as the script's other error lines are), with `.` for the dir itself, counts the directory as not searched, and marks the unit failed.
    - A position holding a symlink is classified below. A position holding a real directory (`-d` and not `-L`) is recursed into. Anything else, absent included, is skipped.
    - It never lists a directory the account holds, so it reads no name the account holds. For a destination whose package roots are real directories, it also never enters `projects/` or plugin clones (Out of scope, linked package root).
    - For such a destination, it never descends through a link, on either side (Out of scope, linked package root).
    - For such a destination, the checkout's package subtrees bound its length (Out of scope, linked package root).
    - It is plain recursion at the unit's own shell level, with no pipeline and no `cd`.
  - Classifying a link at `<rel>`:
    - Its old text is read with `readlink -n -- "$path"`, which has no `-f` and so no fallback. The status is checked and stderr is discarded. A failed status takes the failed-step handling below with cause `could not read its text`. A trailing `x` sentinel is appended inside the `$(...)` and stripped after, so the text is byte-exact. A link whose text ends in a newline therefore fails the ends-with match below and is left alone and counted, never re-pointed or backed up.
    - A link that resolves is skipped.
    - A dangling link is a candidate for the first root whose `<new-real>/<root>/<rel>` exists and whose `/<root>/<rel>` ends its text. The comparison is a literal string match, with the expansion quoted inside `[[ … == *"…" ]]`.
    - A dangling link that matches no root is left alone and counted. Stdout names it: `left <rel> alone in the dir on line <N> of ~/.claude/transcript-config-dirs: it does not resolve and is not recognized as this repo's link`.
    - A candidate is re-pointed whether its old text names this checkout's old location or another checkout of this layout, absolute or relative. That includes a checkout on a volume not mounted during the run. A `--repair` retry cannot tell these apart (row8). The backup copy keeps the old text.
  - Re-pointing a candidate, with each tool's stderr discarded (M6):
    1. Check that nothing exists at `<parent>/.<name>.relocate-claude-config.$$`, by `-e` or `-L`, then create the new link there with `ln -s` and no force flag (row11). Its text is `_relative_path <parent> <new-real>/<root>/<rel>` (M5), where `<parent>` is the link's own physical parent. The `$(...)` that captures this text into `new_text` appends a trailing `x` and strips it after, so a checkout entry name ending in a newline keeps it.
    2. Check that the temporary link resolves (`-e`). It sits in the position's own directory, so the renamed link resolves the same way. A wrong text fails here instead of replacing one dangling link with another.
    3. Allocate a backup name with `_new_backup_path <name>.L<line>` (M3), and write the old text there with `ln -sf`.
    4. Re-check that the position still holds a link that does not resolve.
    5. `mv -f` the temporary link over it, a rename within one directory (row11).
    6. Print `re-pointed <rel> in the dir on line <N> of ~/.claude/transcript-config-dirs; its old link is in <backup>`.
  - A failed step removes only what this unit created, each with `rm -f --`:
    - the temporary link, once its own `ln -s` succeeded;
    - after a failed backup write, the name the allocator returned.
  - A failed step then prints `could not re-point <rel> in the dir on line <N> of ~/.claude/transcript-config-dirs: <cause>` through `err` (on stderr), counts the link as failed, and moves on to the next position. The cause is a fixed phrase per step:
    - classification, a failed `readlink`: `could not read its text`;
    - step 1, a taken temporary name: `its temporary name is taken`;
    - step 1, a failed `ln -s`: `could not create the new link`;
    - step 2: `the new link does not resolve`;
    - step 3: `could not copy it into the backup dir`;
    - step 4: `it changed during the run`;
    - step 5: `could not rename the new link over it`.
  - The unit returns 1 when a link could not be re-pointed or a directory could not be searched. A left-alone link does not fail it.
  - The old link stays in place until the rename, so the retry's walk finds it again. The account-dir write comes first, so an unwritable dir fails before any backup is made. Only a failed re-check or rename leaves a backup copy, so each retry before the fix can add one more.
  - The unit's last line is `the dir on line <N> of ~/.claude/transcript-config-dirs: re-pointed <K>, could not re-point <F>, left <U> alone, could not search <S>`. `<S>` counts directories and the rest count links. So a dir the unit could not search never prints the line a clean dir prints. The line prints whether or not the unit failed.
  - The roots are `claude/.claude`, plus each `RELINK_PACKAGES` package whose target is `.claude` (row4, row5). The `claude/.claude` literal mirrors the one at `:173` (row38).
  - The relative text means Stow counts the link as its own, so the account's own installer can restow over it (row7).
  - The shape rule needs no old location, so both modes run the same code (row8).
  - The run adds no link a dir did not already hold (row24). In a run that is not killed, the temporary link exists only between steps 1 and 5.
  - Trust, the one statement of where the list comes from:
    - The pass reads `~/.claude/transcript-config-dirs` after both modes stow `claude` (as `stow --adopt claude`) and then `claude-skills` from `<new-path>` into `~/.claude` (row15). The file is the user's, and a checkout copy reaches `~/.claude` only through one of those two stows, which already link the destination's hooks and skills (row15).
    - `--repair <new-path>` re-points every listed account's candidates into a `<new-path>` that passed only the canary check (row36).
    - The header, README and CHANGELOG say that `--repair`'s destination reaches every listed account, not only `~/.claude` (row31).
    - The roots file is unguarded (row41), so `docs/transcript-analysis.md`, the file's contract home, says listing a dir gives this command write access to its links (row37).
  - Set aside:
    - `find . -mindepth 1 -type l` over the listed dir, under `cd -P`.
      - It reads every name in the account's tree, session and project dirs included, and its own stderr prints them (M6).
      - Only the account's tree bounds it, so a listed `$HOME` or `/` makes it unbounded.
      - In a `find | while` pipeline, an `exit` inside the loop ends only the loop, and `find`'s status either fails the dir on any unreadable subdirectory or is lost (round-1 platform review R1).
    - A `local -A` visited set keyed by position. A checkout name is safe as a key only while the array stays associative, since an indexed array's subscript evaluates it as arithmetic, and an empty key aborts the command that uses it. The earlier-root probe needs no subscript (row45).
    - Depth 1 only, as the `--repair` sweep does. Stow writes per-entry links inside a real directory the account holds at a package path, and a depth-1 pass would leave those stale with exit 0.
    - `ln -sfn` over the old link. On BSD it unlinks and then creates (row11), so a failed create leaves the position empty and the retry has no link to find.
    - Restoring the old link from its backup after a failed `ln -sfn`. The restore can fail for the same reason the create did.
    - GNU `mv -T` or BSD `mv -h` for the rename. Neither exists on the other userland [unverified], and step 4's re-check narrows the case they guard to a same-user race (Out of scope).
    - Re-stowing each package into the dir from the new location.
      - It links every entry, untracked ones included, unless the run filters by the checkout's tracked list, which means running `git` against `<new-path>`'s own `.git/config` (row15).
      - It applies this repo's link policy over the account installer's (row6).
      - Stow refuses a whole package when the account holds a real file at any of its paths (row7).
      - Its one gain, linking entries tracked since the account was last installed, is that installer's job.
    - Re-stowing with an `--ignore` for each entry the dir did not link. It reproduces this design's link set through regex-escaped names and a stow package named `.claude`.
    - Absolute link text. Stow would not own the link, so the account installer's next stow would refuse on every re-pointed link (row7).
    - Matching link text against the old checkout path. A `--repair` retry cannot learn it (row8).
    - Tying `--repair`'s destination to the moved checkout by a signal `<new-path>` cannot supply. The engineer chose disclosure instead (row31).
- **M2 — a bash reader of the roots file, pinned to `_config_dir.py` by a parity test** (anchors: row1, row2, row3, row15, row18, row19, row33, row35, row45, row49).
  - `read_declared_config_dirs` fills `DECLARED_CONFIG_DIRS` with `<line>\t<physical path>` rows by row 2's grammar, with `read_configured_roots`'s `~` expansion and last-line handling (row3).
  - It resets `DECLARED_CONFIG_DIRS` on entry, as `relink_packages` resets its failure array (row34), so a second call does not append the same rows again.
  - Before its first probe of a line, it prints `checking line <N> of ~/.claude/transcript-config-dirs` on stdout, so a run that blocks on a listed dir's mount shows which line (M4). A line that fails the absolute-path check is never probed and prints no such line.
  - A line that is not absolute, or not an existing directory, gets one stderr warning naming its line number only: `line <N> of ~/.claude/transcript-config-dirs is not an absolute path to an existing directory, so that dir is not re-linked`.
  - A line whose physical path `_readlink_f` cannot give (row35) gets the same warning, since the run cannot use that dir. So the reader never stores an empty path, which the walk would join under `/`.
  - A line whose physical path an earlier row already holds is dropped silently, as `_config_dir.py` dedupes by resolved path. The check is a linear scan of the rows with a plain string comparison, since a set would need an associative array (row45).
  - A lone CR, VT or FF numbers lines differently here than in `_config_dir.py` (row49, Out of scope).
  - It returns 0 at once, silently, unless the file is a regular file it can read, and its loop's redirect carries `|| return 0`. So a missing, unreadable, directory or empty file yields no rows and cannot abort the errexit-on main shell (row33). With the loop on the left of `||`, errexit is off in its body, so each step there checks its own status.
  - It reads `$HOME/.claude/transcript-config-dirs` and nothing else. Tests set `HOME`, and the conftest's value for `TRANSCRIPT_CONFIG_DIRS_FILE` would hide each test's file (row18).
  - This is the script's second copy of a small repo fact, after `RELINK_PACKAGES`, held the same way: `CLAUDE.md` § "Engineering Judgment"'s exception (3), with a test that fails on drift (row4).
  - Set aside:
    - Running `<new-path>`'s `_config_dir.py` through `python3 -I -B -c`, as PR 1's plan proposed (row23). It is the single home, but it would be the first code from `<new-path>` the script's own process runs (row15), and it adds `python3` to the one script meant to work when everything else is broken (row1).
    - Running `~/.claude/scripts/_config_dir.py`. After the `claude` stow it is the same `<new-path>` file, and before it the link can be broken (row1).
    - Sourcing `cleanup-merged-branches.sh`, which runs top-level code (row3) and sits beside `$0` (row1).
    - An associative `seen` set keyed by physical path. An empty key from a failed `_readlink_f` aborts the command that uses it (row45).
- **M3 — a unique backup name for every moved or copied link, with the backup-dir refusal at the allocator** (anchors: row9, row10, row11, row22, row39).
  - `_new_backup_path <stem>` runs `_ensure_backup_dir_is_usable`, then `mkdir -p` on `$BACKUP_DIR`, then prints the result of `mktemp "$BACKUP_DIR/<stem>.XXXXXX"`. Callers run it in `$(...)`, so the refusal's `exit 1` ends only that substitution and the caller sees a failed status.
  - The refusal now sits at the one allocator both callers use, so M1 gets it at the moment of use. The early calls at `:352`, `:375` and `:570` stay, and `_quarantine_if_dangling`'s own call at `:337` goes, since the allocator now makes it.
  - `_quarantine_if_dangling` allocates with its link's basename as the stem, prints today's `quarantining dangling` line with the name, then runs `mv -f` of the link onto the empty file. A failed allocation or move prints today's `could not move <path> into $BACKUP_DIR` and exits 1, and a failed move first removes the empty file.
  - M1 allocates with `<name>.L<line>` as the stem, so a copy's name says which roots-file line it came from.
  - The flat `<stem>.<suffix>` layout keeps every existing backup reader green (row10). The destination is always a regular file this run just created, so `mv` never lands inside a pre-existing directory (row11).
  - Backup names change with or without a roots file.
  - The comment saying same-named links share one backup name is deleted.
  - Set aside:
    - A per-run `mktemp -d` dir, which the Context names. The units are subshells, so a path created lazily inside one does not reach the next, and one created up front leaves an empty dir after every run that moves nothing. It still needs unique names inside, and it changes every backup reader in the existing tests (row10).
    - A counter suffix. An increment inside a subshell unit does not reach the parent.
    - A per-run record mapping each copy to its account path, position and new target, with an owner-only backup dir (round-1 security review R5).
      - The `L<line>` stem says which line a copy came from, and the account's own re-pointed link shows what replaced it.
      - The record would be a second file of account paths that no command ever cleans up.
      - A copy's text reveals nothing the account dir's own links do not, so the mode adds no protection.
- **M4 — runner, failure label and closing text** (anchors: row12, row13, row14, row15, row20, row25, row26, row27, row33, row34, row35, row37, row44, row47).
  - `relink_declared_dirs <new-path>` runs in both modes after `finish_relocation` and before `report_relink_outcome`, called bare as `relink_packages` is. Every fallible command in it is checked, and it ends `return 0` (row33).
    - It first runs `command -v readlink`, the test `_readlink_f` uses. When `readlink` is absent and the roots file is a readable regular file, it prints one `err`, `readlink is not available, so no dir listed in ~/.claude/transcript-config-dirs is re-linked`, and returns 0, before the reader or any probe of a listed dir. With `readlink` absent and no such file it returns 0 and prints nothing, as row22 requires. The `_readlink_f` fallback leaves a final-component link unresolved on `<new-path>`, `~/.claude` and each listed dir, so containment and dedupe would compare unresolved paths. So no listed dir is walked without `readlink`.
    - It then calls the reader. So every probe of a listed dir, the reader's included, runs after the marketplace sync, the manifest write and the installed-copy refresh (row44).
    - The call is bare, not an `if` or `||` condition, because the reader is a function that cannot fail, so errexit stays on inside it.
    - A listed dir that blocks, such as one on an unreachable mount, then holds up only this pass and the closing text. Interrupting the run leaves the move, the stows, the manifest and the installed copy done. It prints no closing text, so an error line printed earlier for a package that failed is not repeated there. The retry is `--repair`. The last `checking` or `walking` line printed names the line that blocked (M2).
    - `report_relink_outcome` still runs last, because it reads the failure array this runner appends to (row44).
    - The trade: a `finish_relocation` step that aborts under errexit now also skips this pass, as it already skips the closing text. The pass placed before it would instead let a blocked dir leave the manifest stale, and the `--repair` retry would block on the same dir.
    - It returns at once when the reader found no rows.
  - It computes the physical paths of `<new-path>` and `~/.claude` with `canonicalize_for_comparison` (row35) once.
  - Then for each row:
    - A dir whose physical path equals `~/.claude`'s gets `the dir on line <N> of ~/.claude/transcript-config-dirs is ~/.claude, which the stows above cover` on stdout.
    - A dir that is the checkout, or whose physical path starts with the checkout's physical path plus `/`, gets `the dir on line <N> of ~/.claude/transcript-config-dirs lies inside the checkout, which this command never re-links` on stdout. So the re-pointing pass never writes inside the checkout.
    - Any other dir first gets `walking the dir on line <N> of ~/.claude/transcript-config-dirs` on stdout, so a run that blocks inside the walk shows which line. It then runs `if ! _repoint_declared_dir …; then`. A failed one gets one `err`, `re-pointing the dir on line <N> of ~/.claude/transcript-config-dirs failed`, and is appended to the failure array as `transcript-config-dirs:line-<N>`. The runner never resets that array, because `relink_packages` already did (row34).
  - A listed ancestor of the checkout or of `~/.claude`, `$HOME` included, is walked like any other dir. M1 probes it only at package positions under it, which the runner test's ancestor cases pin.
  - `RELINK_FAILED_PACKAGES` becomes `RELINK_FAILURES` at its eight code sites and in the comment at `:479` (row13).
  - The closing text's resolve paragraph gains three sentences:
    - A `transcript-config-dirs:line-<N>` entry is the dir on line <N> of ~/.claude/transcript-config-dirs.
    - The errors above it name each link it could not re-point, with the cause, and each directory it could not search.
    - Fix that cause, such as a dir this command cannot search or write, or delete the dir's line from ~/.claude/transcript-config-dirs so this command leaves it alone, which also drops it from the transcript tools' scan.
  - The first manual bullet splits in two:
    - The unlisted-dirs bullet, in these sentences:
      - Config dirs not listed in ~/.claude/transcript-config-dirs, or listed there and reported above as not re-linked, keep their links into the old location.
      - A session under such an account loads none of this repo's settings, hooks or skills until its dir is re-linked.
      - To have this command re-link one, list its absolute path in that file, or correct the line a warning above names, or make its dir reachable. Then run `relocate-claude-config --repair [--allow-outside-home] <new-path>`, with the flag when this run passed it.
      - Listing a dir there gives this command write access to its links, whether or not the transcript tools scan it, so list one only if you want that.
      - This command did not touch a link reported above as left alone, so re-link or remove it yourself.
    - The registration bullet: Any other account that registered this repo's marketplace, listed or not, still records it at the old location. `CLAUDE_CONFIG_DIR=<dir> register-marketplace` re-points it once that account's `settings.json` resolves.
  - A failed link gets its own `could not re-point` line and the resolve paragraph's fix, never a `left … alone` line. So the left-alone sentence and the retry instruction never name the same link.
  - Once M1 has re-pointed a listed account's links, the registration bullet is that account's only manual step, unless a link is reported as left alone, a residual the engineer accepted (row47), or its dir as not re-linked, a residual this plan chose (row56). PR 2b removes the registration step for listed accounts by narrowing that one bullet to unlisted ones (Out of scope).
  - No existing test asserts either bullet (row14). The four-token list under the integration test bullets says which test asserts what.
  - `--repair` is the retry: a re-pointed link resolves and is skipped, and one left in place is found again (M1).
  - Set aside: a `sed -n <N>p` hint in the resolve text (round-1 product review R8). The label already names the file and the line.
- **M5 — `_relative_path <from-dir> <to-path>`** (anchors: row7, row11, row35, row40).
  - Pure bash. It climbs `<from-dir>` with `dirname` until `<to-path>` equals it or starts with it plus `/`, adding one `../` per climb, then appends the rest of `<to-path>`. Equal paths give `.`.
  - The climb stops at `/`, which every absolute path lies under, so it always ends. The prefix test strips a trailing `/` from the start before appending `/`, so a start of `/` tests against the prefix `/`, not `//`.
  - Callers pass physical paths with no trailing slash: the link's own parent under the listed dir's physical path, and `<new-path>`'s physical path (row35). That matches how Stow resolves its own dirs (row7) and how relative text resolves (row40).
  - Set aside:
    - GNU `ln -r` and `realpath --relative-to`, which BSD userland lacks. [unverified]
    - `python3`'s `os.path.relpath`, which adds the dependency M2 avoids and is logic `shell-script-conventions.md` keeps out of inline `python3 -c`.
    - Perl's `File::Spec->abs2rel`, which adds the script's first direct `perl` call to replace about fifteen lines of bash.
- **M6 — messages name a listed dir by its line number only, and no tool's stderr passes through** (anchors: row2, row15, row23).
  - Same reason as `_config_dir.py`'s (row2), since the script's output can reach an agent transcript (row15).
  - Every tool M1 calls has its stderr discarded, and each failure surfaces as one of the script's own fixed-shape lines. Those lines name a listed dir only by line number, and a link only by its position under a package root. For a destination whose package roots are real directories, that position comes from the checkout (Out of scope, linked package root).
  - The `checking` and `walking` progress lines and each failure's cause are fixed-shape too.
  - A backup name holds only the link's basename and line number.
  - Set aside: PR 1's plan's ordinal-to-path map in the backup dir (row23). The line number already resolves against the user's own file.
- **M7 — tests in two layers, with failure seams that need no root** (anchors: row16, row17, row28, row33, row39, row42, row46).
  - Unit layer: tests source the script and call `_repoint_declared_dir`, `relink_declared_dirs`, `read_declared_config_dirs`, `_relative_path`, `_quarantine_if_dangling` and `print_manual_steps` directly, as `TestRelinkPackagesBatch` does (row39). It carries the decision table, containment, failure paths and roots-file states.
  - Integration layer: two tests, each run in both modes, for wiring only. They cover call order, outcome lines, exit 3 with the printed retry, and the unlisted-dirs closing text.
  - Failure seams:
    - Sourced tests define a bash `ln` or `mv` function that fails for one named path and runs `command ln` or `command mv` otherwise. The script calls `ln`, `mv` and `rm` by bare name, never through `command` or an absolute path, so the function intercepts them.
    - The `ln` function treats any flag argument whose letters include `f`, such as `-sf` or `-sfn`, as forced. The temporary-link case's function, when forced, removes its destination before failing, as BSD `ln -f` does when its create fails. A mutation back to `ln -sfn` then leaves the position empty. The function stops scanning flags at `--`, so a dash-led link text after `--` that contains an `f` is not read as a flag.
    - Each failing `ln` and `mv` function also writes a real-shaped message, such as `ln: <path>: Permission denied`, that names its full path argument to stderr. So the failure test's `acct-` assertion pins the stderr discard for the temporary link's `ln -s` and the rename's `mv` without root.
    - A function that fails for `hooks` matches both `<dir>/hooks` and `<dir>/.hooks.relocate-claude-config.<pid>`. The backup-copy case's function matches only paths under the backup dir.
    - The integration exit-3 test puts an `mv` shim in a directory of its own, first on PATH for the first run only. It passes every other call to the real `mv` by an absolute path the test resolves before the run, since the primary run's own checkout move calls `mv`.
    - Only the unwritable, unsearchable, unsearchable-nested and unreadable-file cases set modes, under `requires_non_root`. Each restores modes in `finally` before any assertion, since a `0o644` dir blocks reading its own links.
  - Every sourced call of a unit runs as an `if` condition, as the runner calls it, so errexit is off as in production. The survive test instead calls the runner bare, with errexit on, as production calls it (row33). Every call also runs under a `subprocess` timeout, so a loop that never ends fails instead of hanging CI.
  - The walk and per-link helpers sit above `_repoint_declared_dir` in the file, as `_quarantine_if_dangling` sits above `_relink_package`. So shellcheck reports neither SC2030 nor SC2031 on the locals they share, and SC2034 never fires on a local a helper reads (row46). No `disable` line is planned. If Verification 2 still reports SC2030 or SC2031 after that order, one `# shellcheck disable=SC2030,SC2031` on the unit carries the one-line rationale `CLAUDE.md` § "Engineering Judgment" requires, naming the alternative considered and why it does not apply.
  - The new test files import their run helpers from `.test_relocate_claude_config` (row16).
  - Set aside:
    - Moving those helpers into a `_relocate_helpers.py` module both files import (round-1 SDET review R9). It moves about 180 lines, which adds about 360 changed lines to a PR the engineer accepted at about 710 (row42). The relative import is allowed and has a precedent in the same directory (row16). Splitting the over-limit file is the place for that move (Out of scope).
    - Extending `TestClaudeCliMissing`'s tool tuple. Its run reaches none of the new tools (row17), so its comment narrows instead.
    - A `chmod 0o555` integration case for exit 3. The `mv` shim covers the same wiring without root, and the unit layer keeps the real-permission cases.

## Critical files

Comments and docs added below state durable one-line facts only, with no plan terms. One `code-writer` dispatch covers every file: the tests exercise the new functions and the docs describe them, so a split would restate the same background in each prompt.

- **Modify `claude/.claude/scripts/relocate-claude-config.sh`.**
  - Header:
    - The summary (`:9-14`) gains one sentence: both modes also re-point links in each config dir listed in `~/.claude/transcript-config-dirs`.
    - The threat-model paragraph (`:16-25`) gains one sentence: a `--repair` destination that passes only the canary check reaches every account listed in `~/.claude/transcript-config-dirs`, not only `~/.claude` (M1, row31).
    - Exit code `3` (`:54-59`) reads that linking a package, or re-pointing a listed config dir, named on stderr failed.
    - `usage()` (`:71-82`) gains one line under the two modes: both modes also re-point links in each config dir listed in `~/.claude/transcript-config-dirs`. No test pins usage text, as none does today.
  - Globals after `RELINK_PACKAGES` (`:68`): `DECLARED_DIRS_FILE="$HOME/.claude/transcript-config-dirs"` and `DECLARED_CONFIG_DIRS=()`. `RELINK_FAILED_PACKAGES` becomes `RELINK_FAILURES` at its eight code sites and in the `:479` comment (M4).
  - New functions, in this order in the file, so each helper sits above the unit whose locals it reads (M7, row46):
    - `_new_backup_path` (M3).
    - `read_declared_config_dirs`, whose one-line comment names `_config_dir.py`'s `declared_roots_matching` as the grammar's home and the test that keeps the two equal (M2).
    - `_relative_path` (M5).
    - The walk and the per-link re-point, as two helpers (M1, M6).
    - `_repoint_declared_dir`, which calls them (M1).
    - `relink_declared_dirs` (M4).
  - `_quarantine_if_dangling` (`:322-345`) calls `_new_backup_path`, drops its own `_ensure_backup_dir_is_usable` call, and runs `mv -f` onto the allocated name. Its same-name comment (`:328-329`) is deleted (M3).
  - `relocate_repo` (`:609`) and `repair_repo` (`:633`) call `relink_declared_dirs "$new_path"` right after `finish_relocation` and before `report_relink_outcome` (M4).
  - `report_relink_outcome`'s resolve paragraph (`:561`) and `print_manual_steps`'s first bullet (`:511-513`) change as M4 says.
  - Reuse `_readlink_f`, `canonicalize_for_comparison`, `_ensure_backup_dir_is_usable`, `err` and the `[relocate-claude-config]` stdout prefix.
- **Modify `claude/.claude/scripts/tests/test_relocate_claude_config.py`** — only the three `RELINK_FAILED_PACKAGES` references (`:916, 919, 947`), and `TestClaudeCliMissing`'s comment (`:715-718`), which narrows to every external tool this run reaches (M7, row17). New tests go to the new file below, because this one is already over the 1,000-line limit (row16).
- **Create five new files under `claude/.claude/scripts/tests/`, split to stay under the 1,000-line limit (row16, row57).**
  - `test_relocate_claude_config_declared_dirs.py`: the decision-table and unit tests, split at the listed-config-dirs seam (M7). The test and builder names below live here unless a bullet says otherwise.
  - `_declared_dirs_helpers.py`: shared scene builders.
  - `test_relocate_claude_config_declared_dirs_integration.py`: full-script wiring.
  - `test_relocate_claude_config_declared_dirs_probes.py`: reader and runner probes.
  - `test_relocate_claude_config_declared_dirs_roots_file.py`: roots-file reader and runner parity.
- **About the first file above**, the listed-config-dirs split (M7):
  - It imports `_SCRIPT`, `requires_non_root`, `_make_repo`, `_stow`, `_script_env`, `_claude_shim`, `_relocation_args_for_mode`, `_run_printed_retry_line`, `_plant_unusable_backup_dir`, `_BACKUP_DIR_REFUSAL_FRAGMENTS`, `_AWKWARD_DESTINATION_NAME` and `_backup_entry_names` from `.test_relocate_claude_config` (row16, row39). It imports `_config_dir` as `test__config_dir.py:9-10` does.
  - Builders:
    - One writes `home/.claude/transcript-config-dirs` from a list of lines, optionally with no final newline.
    - One adds entries to the new checkout's package trees.
    - One makes a stale link whose text is `os.path.relpath` of its target from the link's physical parent, as Stow writes it, or the absolute target on request.
    - One writes the `ln` and `mv` functions by M7's seam rules.
    - One runs a bash snippet that sources the script and calls a function under a `subprocess` timeout, in a scratch working directory. It takes an ordered list of calls, with an optional bash fragment between them, and prints a distinct delimiter line after each call. A test reads each call's output slice separately, and the calls run in one shell. By default it calls each function as an `if` condition. Its bare mode calls each one bare, with errexit on as sourcing leaves it. Every sourced call goes through it.
    - One parses a run's stdout into each outcome line's four counts and its `left … alone` lines.
    - `helpers.build_path_without("readlink", <farm dir>)` gives the `no-readlink` ids their PATH. [verified: `claude/.claude/tests/helpers.py:2934`; the scripts tests import `helpers` as `conftest.py:36` does]
  - Fixtures use synthetic names that all carry an `acct-` marker, the missing dir's included, and no real account or home path.
  - Outcome counts below are written as re-pointed, could not re-point and left alone, each read through the outcome-line parser. The fourth, could not search, is 0 unless a test gives it.
  - Unit layer, sourced:
    - `test_repoint_decision_table`, parametrized with one id per case. Each case is one listed dir, run through `_repoint_declared_dir` directly.
      - Each case asserts the unit's return status, each link's state, the backup entries, the outcome line's counts and any `left … alone` line.
      - Each also asserts that neither stream holds `acct-`.
      - The unit returns 0 in every case but `unsearchable-nested`.
      - The ids:
        - `stale-relative`: a dangling `hooks` link into the old checkout is re-pointed with relative text and resolves into the new checkout. The per-link line names a backup path that exists, matches `hooks.L<N>.*` and holds the pre-run text.
        - `stale-absolute`: the same with absolute old text. The new text is relative.
        - `stale-nested`: the new checkout gains a second hook file whose name starts with `.`. The account holds a real `hooks/` dir with a dangling link for each hook file, followed in glob order by a dangling `scripts` link. All three are re-pointed with text computed from their own parents, and resolve.
        - `stale-other-checkout`: a dangling link into a second, nonexistent checkout of this layout is re-pointed, and its backup holds its own text.
        - `dash-led-text`: the old checkout sat inside the listed dir under a name starting with `-`, so the stale `hooks` link's relative text starts with `-`. It is re-pointed, and its backup holds the old text (row11).
        - `awkward-name`: a new-checkout entry and stale link whose name holds a leading `-`, a space, `$`, `]`, a backtick, `@`, `*`, `\` and `$(touch injected)` are re-pointed. No `injected` file appears in the scratch working directory, a tripwire for a name passed through `eval`. A second awkward name is a real directory present in both checkout and account, holding a stale link, so quoting reaches the glob base and the recursion argument as well as the leaf expansions.
        - `live-link`: a link at a checkout position that resolves is unchanged, with no backup. Its text ends in a second existing checkout's `claude/.claude/<rel>` form, so only the skip for a link that resolves keeps it unchanged.
        - `other-shape`: a dangling link at a position the new checkout holds, whose text ends elsewhere.
        - `near-miss-text`: a dangling `skills` link whose text ends in `x-claude-skills/skills`.
        - `wrong-root-text`: a dangling `hooks` link whose text ends in `claude-skills/hooks`, which the new checkout lacks.
        - `trailing-newline-text`: a dangling `hooks` link whose text is a valid old-checkout path followed by one newline. It leaves no backup.
        - `glob-in-name`: a dangling link at a new-checkout position `star*`, whose text ends in `claude/.claude/star-other`.
        - `newline-ending-name`: a dangling link at a new-checkout position whose entry name ends in a newline, with a sibling entry of the same name without it. The link is re-pointed, resolves to its own entry, and its text names that entry.
        - The ids `other-shape`, `near-miss-text`, `wrong-root-text`, `glob-in-name` and `trailing-newline-text` each leave their link unchanged, with counts 0, 0 and 1 and a `left <rel> alone` line naming it.
        - `not-a-checkout-position`: a dangling `retired` link the new checkout has no entry for is unchanged and not counted.
        - `under-a-linked-dir`: `hooks` is a live link to a second checkout's `claude/.claude/hooks/`, which holds a dangling shape-matching `_lib.sh` link. That link is unchanged.
        - `linked-checkout-dir`: the new checkout's `claude/.claude/linked` is a link to a directory holding `inner`. The account holds a real `linked/` dir with a dangling `inner` link whose text ends in `claude/.claude/linked/inner`. That link is unchanged, all four counts are 0, and neither stream names `inner`.
        - `shared-position`: both roots hold a real `shared/` dir, one holding `a` and the other `b`. The account's real `shared/` holds a dangling `a` whose text ends in `claude/.claude/shared/a`, and a dangling `b` whose text ends elsewhere. The counts are 1, 0 and 1.
        - `unsearchable-nested`, `requires_non_root`: the account's real `hooks/` dir is `0o644` and holds a dangling hook link. The unit returns 1, the link is unchanged, the counts are 0, 0, 0 and 1, and stderr holds the `could not search hooks` line. Modes are restored in `finally` before any assertion.
    - `test_failure_keeps_the_old_link_and_leaves_no_strays`, parametrized over the failure. The dir holds dangling `hooks` and `scripts` links.
      - The cases:
        - `temp-link`: an `ln` function fails for any destination in the listed dir named for `hooks`, first removing that destination when forced (M7). No `hooks.L<N>.*` entry is made.
        - `bad-text`: an `ln` function creates `hooks`' temporary link with text that does not resolve. No `hooks.L<N>.*` entry is made.
        - `backup-copy`: an `ln` function fails, without removing anything, for a backup name starting `hooks.`. No `hooks.*` entry is left.
        - `recheck-dir`: once `hooks`' temporary link exists, an `ln` function replaces `<dir>/hooks` with an empty real directory. One `hooks.L<N>.*` copy is left.
        - `recheck-live`: the same, replacing `<dir>/hooks` with a live link. One `hooks.L<N>.*` copy is left.
        - `rename`: an `mv` function fails for `<dir>/hooks`. One `hooks.L<N>.*` copy is left.
        - `unwritable`, `requires_non_root`: the listed dir is `0o555`, so both links fail on the real `ln`, and no `hooks.L<N>.*` or `scripts.L<N>.*` entry is made.
        - `unsearchable`, `requires_non_root`: the listed dir is `0o644`, so no position is probed, and stderr holds the `could not search .` line.
        - `temp-name-taken`: the snippet plants a real directory holding a file at `<dir>/.hooks.relocate-claude-config.$$` before the call, since the unit's subshell keeps its parent's `$$`. Without the pre-check, `ln -s` would create the link inside that directory (row11). The planted directory is unchanged and still holds only its own file, and no `hooks.L<N>.*` entry is made.
      - Every case's unit returns 1, and the outcome-line parser finds no `left … alone` line. Its other assertions are the ones Verification 3's mutations naming this test need.
    - `test_backup_dir_refusal_reaches_the_repoint_unit`, parametrized over `symlink` and `regular file` through `_plant_unusable_backup_dir`. The unit returns 1, the link is unchanged, no `.relocate-claude-config.` entry remains, `observe()` still equals `untouched`, and stderr holds the matching refusal fragment (M3).
    - `test_a_dir_with_nothing_to_re_point_is_not_written`, with no stale link in the listed dir. Its seam functions record every `ln`, `mv`, `rm` and `mktemp` call, and the record is empty. The unit returns 0 and the counts are 0, 0 and 0. A second id, `requires_non_root`, makes the listed dir `0o555` and runs the real tools. It also returns 0 with the counts at 0, 0 and 0, and no backup dir exists.
    - `test_runner_skips_home_claude_and_the_checkout_and_bounds_ancestors`, parametrized.
      - `home-claude` and `inside-checkout`: a listed `~/.claude`, or a listed dir inside the new checkout, holds a dangling shape-matching `hooks` link whose new target exists. The link is unchanged, and stdout holds the matching skip line with the line number. Neither stream holds the `acct-` marker in either case. `home-claude`'s fixture has no `acct-` path component, so `[home-claude-symlinked]` and `[inside-checkout]` pin that the skip line carries the dir's line number and not its path. In `inside-checkout` the listed dir's name carries `acct-`.
      - `home-claude-symlinked`: the test's `HOME` is itself a symlink, named `acct-home-link`, to the real home directory, named `acct-real-home`, so `$HOME/.claude` as typed differs from its physical path. The listed line is `~/.claude`. Its dangling shape-matching `hooks` link is unchanged, and stdout holds the `~/.claude` skip line with the line number.
      - `sibling-prefix`: the listed dir sits beside the new checkout and its physical path starts with the checkout's path plus a suffix, so it is not inside the checkout. Its dangling shape-matching `hooks` link is re-pointed. The runner's containment test matches the checkout itself and paths under it plus a `/` boundary.
      - `home` and `checkout-parent`: the listed dir is `$HOME`, an ancestor of `~/.claude` and the checkout, or a dir holding the checkout but not `~/.claude`. A dangling shape-matching `hooks` link directly under it is re-pointed.
      - In `checkout-parent` the new checkout's name starts with `-`, so the new relative text starts with `-` too. The re-pointed link resolves, and its text equals `os.path.relpath` from its physical parent (row11).
      - Each ancestor case also plants a dangling decoy, whose text ends in `claude/.claude/hooks`, inside `~/.claude` (`home`) or the checkout (`checkout-parent`). The decoy keeps its text, the checkout's other entries are unchanged, and the outcome line's counts are exactly 1, 0 and 0.
    - `test_runner_appends_failures_and_follows_relink_packages_targets`.
      - `RELINK_FAILURES` starts as `earlier-pkg`, and `RELINK_PACKAGES` adds an `other-pkg` row with target `.other`, whose `thing` entry the new checkout holds.
      - `acct-a` fails through an `mv` function. `acct-b` holds a stale `hooks` link and a dangling `thing` link whose text ends in `other-pkg/thing`.
      - The runner returns 0, and the array reads `earlier-pkg transcript-config-dirs:line-<N>`, where `<N>` is `acct-a`'s line number. `acct-b/hooks` is re-pointed, and `acct-b/thing` is unchanged.
    - Four runner tests share one setup builder, each with one assertion focus. The builder makes a listed dir whose name holds a space, `$` and `*`, and a new checkout named `_AWKWARD_DESTINATION_NAME`. It writes a roots file that lists `acct-a` through a symlinked parent and then directly, with `<new-path>` spelled through a symlinked parent. `acct-a` holds a stale shape-matching `hooks` link.
      - `test_runner_resolves_symlinked_and_awkward_paths`: the re-pointed link's text equals `os.path.relpath` from its physical parent to the physical target.
      - `test_runner_dedupes_a_dir_listed_twice`: one outcome line prints.
      - `test_runner_second_call_is_idempotent`: a second call in the same shell prints `re-pointed 0` and adds no backup entry. It asserts the exact outcome-line count and counts for the second call's slice only.
      - `test_runner_resets_declared_rows_on_each_call`: after a first call, the test rewrites the roots file to list a different `acct-` dir, holding a stale shape-matching `hooks` link, and calls the runner again in the same shell. That call re-points only the new dir and prints no outcome line for the first. The second roots file lists the new `acct-` dir at a line number the first call did not use, so an outcome line left over from the first call cannot look like the second call's line. The test asserts the exact outcome-line count and counts for the second call's slice only.
    - `test_reader_and_runner_survive_every_roots_file_state`, parametrized with one id per roots-file state. It calls only the runner, which calls the reader (M4), in the builder's bare mode (M7). The reader's warnings therefore reach stderr once per run.
      - The ids:
        - `missing`, `directory`, `empty` and `comment-only`;
        - `unreadable`: mode `0o000`, `requires_non_root`;
        - `readlink-fails`: the file lists an existing `acct-` dir, and a sourced `readlink` function returns 1, which `_readlink_f` finds through `command -v`;
        - `last-relative`, `last-missing-dir` and `last-duplicate`: the last line is skipped, as a relative line, a missing dir, or an exact duplicate of an `acct-` dir on the line before it.
        - `no-readlink`: PATH comes from `helpers.build_path_without("readlink", <farm dir>)`, and the file lists an existing `acct-` dir with a stale `hooks` link. The runner's precondition returns before the reader. The runner returns 0, stderr holds one `readlink is not available` line, stdout holds no `checking`, `walking` or outcome line, and `hooks` keeps its text.
        - `no-readlink-no-file`: the same PATH and no roots file. The runner returns 0, and neither stream holds `readlink is not available` (row22).
      - The sentinel line printed after the call appears.
      - Each of the first five states lists no dir. It plants an `acct-unlisted` dir beside `~/.claude`, which the file does not list, holding a stale shape-matching `hooks` link whose new target exists. That link keeps its text.
      - Stderr holds only the state's reader warnings, by line number, once each. `no-readlink` holds only its precondition line, and `no-readlink-no-file` holds nothing.
      - Every id re-points nothing and leaves no backup dir, since the `acct-` dir that `readlink-fails` and the `last-*` ids list holds no stale link.
    - `test_reader_matches_config_dir_parser`.
      - The roots file holds, one per line:
        - a comment;
        - a blank line;
        - a padded `~/` line;
        - a tab-padded line;
        - a CRLF line;
        - `~`;
        - a path with a mid-line `#`;
        - a `~acct-user/x` line;
        - a relative line;
        - a missing dir;
        - an existing absolute path that is a regular file;
        - an exact duplicate;
        - a duplicate through a symlinked parent;
        - an existing dir whose name holds `]`, a backtick, `@`, `*`, `\` and `$(touch injected)`;
        - that line's exact duplicate;
        - a last line with no final newline.
      - The regular-file row exists because `readlink -f` fails on a missing path on macOS, so the missing-dir row alone can reach the same warning through the readlink-failure arm. Only the directory check rejects a regular file on every userland.
      - It holds no lone CR, VT or FF, on which the two sides number lines differently (row49).
      - No `injected` file appears in either side's working directory.
      - Both sides run in a scratch working directory that holds a real directory named as the relative line, so only the absolute-path check rejects it.
      - Bash prints `DECLARED_CONFIG_DIRS`, and the test drops the reader's `checking line` lines before comparing. Python calls `_config_dir.declared_roots_matching(lambda path: True, warn_prefix=...)` with `HOME` and `TRANSCRIPT_CONFIG_DIRS_FILE` monkeypatched.
      - Bash's paths equal Python's paths after resolving, as ordered lists. The warned line numbers are equal, with one extraction helper per side.
      - Each bash row's line number names the physical line that holds its path.
      - A roots path that is a directory gives empty, silent results on both sides.
    - `test_relative_path`, parametrized (M5):
      - sibling subtrees;
      - a descendant;
      - a shared name prefix (`/a/b` to `/a/bc/d` gives `../bc/d`);
      - different first components (`/a/b` to `/c/d` gives `../../c/d`);
      - `/` as the start;
      - a target that is an ancestor of the start;
      - equal paths;
      - a path with a space.
    - `test_same_named_dangling_links_get_their_own_backups`: `_quarantine_if_dangling` on dangling `~/.claude/dup-name` and `~/.local/bin/dup-name` with different text leaves two `dup-name.*` entries, each holding its own text (M3).
    - `test_a_failed_quarantine_move_leaves_no_placeholder`: with an `mv` function that fails, `_quarantine_if_dangling` exits 1, the link stays, and the backup dir holds no entry (M3).
    - `test_stow_owns_a_repointed_link`, parametrized over the two roots with ids `claude-skills` and `claude`, after `_repoint_declared_dir` re-points `acct-a` (row7).
      - `claude-skills`: `stow -D -d <new> -t <acct-a> claude-skills` removes `acct-a/skills`.
      - `claude`: `stow -D -d <new>/claude -t <acct-a> .claude` removes `acct-a/hooks`.
      - If Stow rejects the `claude` invocation, the implementer stops and reports it rather than weakening the assertion.
  - Integration layer, full runs:
    - `test_both_modes_repoint_listed_dirs_and_report_each`, parametrized over primary and `--repair`. Its `--repair` arm is the `--repair` destination test PR 1's plan asked for (row23), since `_make_repo` builds a destination that passes only the canary check (row36).
      - The roots file lists a comment, `~/.claude`, `acct-a`, `acct-missing`, `acct-b` and `acct-c`.
      - The accounts:
        - `acct-a` holds a stale `hooks` link, a real `skills/` dir with a stale `skills/example` link, and a stale `retired` link.
        - `acct-b` holds real files and a dangling `scripts` link whose text ends in `elsewhere/scripts`. It holds no entry named `skills`, a position the new checkout holds, so its listing assertion fails if the run creates a link there.
        - `acct-c` holds a live `hooks` link into a second checkout that exists.
        - `acct-unlisted`, a sibling of the listed dirs that the file does not list, holds a stale shape-matching `hooks` link whose new target exists.
      - The run exits 0. `acct-a/hooks` and `acct-a/skills/example` resolve into the new checkout. `retired`, `acct-c/hooks`, `acct-unlisted/hooks` and `acct-b`'s listing are unchanged. The backup text, the `~/.claude` skip line and the reader warning are pinned at the unit layer (the decision table's backup check, the runner cases and the roots-file tests), not here.
      - Stdout holds one outcome line per account: `acct-a` 2, 0 and 0, `acct-b` 0, 0 and 1, and `acct-c` 0, 0 and 0. It also holds a `left scripts` line for `acct-b`. `acct-b`'s old link text appears in neither stream.
      - The `checking line <N>` and `walking the dir on line <N>` progress lines are asserted by the two probes-file tests, not here.
      - The closing text is asserted on four stable tokens, not whole sentences, each in exactly one test:
        - The integration success test asserts the retry-command tokens `relocate-claude-config --repair [--allow-outside-home]` and the write-access token `gives this command write access to its links`.
        - `test_manual_steps_name_the_retry_flag_and_give_registration_its_own_bullet` asserts `register-marketplace` and `with the flag when this run passed it`. It calls `print_manual_steps` through `_run_sourced`. It also asserts that the bullet holding the `register-marketplace` line opens with text naming `marketplace`, which fails when registration merges into another bullet.
    - `test_a_failed_dir_exits_3_and_the_printed_retry_repoints_it`, parametrized over primary and `--repair` through `_relocation_args_for_mode`. `acct-a` is listed before `acct-b`.
      - An `mv` shim fails for `acct-a/hooks` only (M7). Before failing, it copies the manifest, `~/.claude-config-source`, to a record file.
      - The run exits 3. Stderr holds `re-linking failed for: transcript-config-dirs:line-<N>`, where `<N>` is `acct-a`'s line number, and the `could not rename the new link over it` cause. It also holds the runner's `re-pointing the dir on line <N> of ~/.claude/transcript-config-dirs failed` err, with `acct-a`'s line number. It holds no `acct-`.
      - The closing text is asserted on stable tokens only: that label and the printed retry command with its flags, which `_run_printed_retry_line` below runs.
      - `acct-a`'s outcome line reads 0, 1 and 0.
      - The test first checks that the manifest is absent or names another path. The record then equals the manifest after the run, so the pass ran after the manifest write.
      - `acct-a/hooks` keeps its text, `acct-b/hooks` is re-pointed, and `~/.claude/hooks` resolves into the new checkout.
      - `_run_printed_retry_line`, run without the shim, exits 0, and `acct-a/hooks` resolves into the new checkout.
- **Modify `README.md`**, only inside `### Repo relocation`:
  - Delete the sentence saying same-named links share one backup name (`:447`).
  - In the `claude-skills` bullet (`:450`), the backup name becomes `<name>.<suffix>`, unique to each move.
  - A bullet after it, with nested items:
    - Both modes also re-point links in each config dir listed in `~/.claude/transcript-config-dirs`, other than `~/.claude` and any dir inside the checkout. With no such file in `~/.claude` when this step runs, it does nothing.
    - A link at one of this repo's package paths in that dir, nested ones included, now points to that path in the new checkout when it no longer resolves and its text ends in `/claude/.claude/<path>` or `/claude-skills/<path>` for its own `<path>`. The new text is relative, as Stow writes it.
    - This holds whichever checkout the old text named, one on a volume not mounted during the run included. The backup copy keeps the old link text.
    - A copy of each old link goes to `~/.claude-config-relocate-backup/<name>.L<line>.<suffix>` first. A failed replacement leaves the old link in place, and each retry before the fix can add another copy.
    - Nothing else in the dir changes, so an entry tracked since that account was last installed stays unlinked until its own installer runs.
    - Output names a listed dir only by its line number. One line per dir gives how many links it re-pointed, could not re-point, and left alone, and how many directories it could not search. Each link left alone is named on its own line, and this command did not touch it, so re-link or remove it yourself.
    - This step runs after the relocation's own steps, so interrupting a run that blocks on a listed dir, such as one on an unreachable mount, leaves those steps done, though an error printed earlier for a package that failed is not repeated in a closing line.
    - The run prints `checking line <N> of ~/.claude/transcript-config-dirs` before it first probes a listed dir, and `walking the dir on line <N> …` before it walks one. The last such line an interrupted run printed names the line to take out of the list or make reachable.
    - An interrupted run prints no closing text: no `Done.` line, reminders, manual steps or retry line. The retry is `relocate-claude-config --repair [--allow-outside-home] <new-path>`, with the flag when the first run passed it. When it succeeds it prints `Done.` and the manual steps. It does not print the primary form's reminder that open shells and Claude Code sessions still hold the old path, so reopen them.
    - An interrupted run can leave a `.<name>.relocate-claude-config.<pid>` link beside the link it was replacing. It is safe to delete. It can also leave an empty file in `~/.claude-config-relocate-backup`, which is safe to delete too.
    - `--repair <new-path>` re-points every listed account's matching links into `<new-path>`, so that destination is trusted for every listed account, not only `~/.claude`.
    - Listing a dir in the file gives this command write access to its links. Taking it out of the list keeps the command away from it, and also drops it from the transcript tools' scan (`docs/transcript-analysis.md` § "Corpus scope: the declared-roots file"). This command accepts any existing absolute directory in the file, including one the transcript tools skip.
  - The exit-3 bullet (`:451-457`) adds a listed dir to what can fail. Its lead sentence becomes: "Exit 3 means the checkout has already moved, or `--repair` already linked the `claude` package, and re-linking a package, or re-pointing a listed config dir, named on stderr failed." It adds a cause, shown as `transcript-config-dirs:line-<N>`, in these cases:
    - a dir this command cannot search;
    - an unwritable listed dir, or an unwritable dir under it, when one of its links needs re-pointing there (a dir with nothing to re-point is not written);
    - an unwritable backup dir, when some listed dir holds a link that needs re-pointing;
    - a link it cannot re-point for another reason.
    The error line above names which. It also adds the other way out: delete the dir's line from `~/.claude/transcript-config-dirs`.
  - The accounts bullet (`:472`) splits into M4's unlisted-dirs and registration bullets. The unlisted-dirs bullet gives the retry as `relocate-claude-config --repair [--allow-outside-home] <new-path>`, with the flag when the first run passed it, and does not repeat the write-access sentence, which the re-pointing bullet above states. The registration bullet keeps today's sentence that `register-marketplace` takes effect only once that account's `settings.json` resolves, and exits 0 with "nothing to register" otherwise.
- **Modify `docs/scripts.md`** — in the `relocate-claude-config.sh` bullet (`:463`), the clause "Both modes also re-link `claude-skills` and exit 3 when that fails" becomes: both modes also re-link `claude-skills` and re-point links in each config dir listed in `~/.claude/transcript-config-dirs`, and exit 3 when either fails.
- **Modify `docs/transcript-analysis.md`** — § "Corpus scope: the declared-roots file" (`:88`) gains one sentence. `relocate-claude-config` also reads the file and re-points links in each listed dir after the checkout moves, so listing a dir gives that command write access to its links, and that command accepts any existing absolute directory in the file, including one the transcript tools skip (row37).
- **Modify `CHANGELOG.md`** — one new `### Changed` bullet under `[Unreleased]`. PR 1's bullet (`:48-53`) is a record and stays as written.
  - Lead: `relocate-claude-config` now re-points, in both modes, links in each config dir listed in `~/.claude/transcript-config-dirs` other than `~/.claude`, keeping a copy of each old link in `~/.claude-config-relocate-backup`.
  - Listing a dir there now gives this command write access to its links, whether or not the transcript tools scan it.
  - `--repair <new-path>` reaches every listed account, so its destination is trusted for each of them.
  - A dangling link at one of this repo's package paths is re-pointed when its text ends in that path, whichever checkout its text named.
  - A run that exited 0 before can exit 3 now, when a dir under a listed dir, or the listed dir itself, cannot be searched. It can also exit 3 when a link needs re-pointing and its listed dir, a dir under it, or the backup dir is unwritable (a dir with nothing to re-point is not written), or when a link cannot be re-pointed for another reason. The retry is `--repair`.
  - Backups now get a unique `<name>.<suffix>` name, with or without the file, so two same-named links in one run no longer replace each other's backup.
  - No clause about what stays manual. PR 2b's own bullet would land beside it in the same `[Unreleased]` section and contradict it.
  - **Migration:** run `./install.sh` before your next relocation, because `git pull` does not refresh the installed copy.
  - **Migration:** after a relocation that left a listed account's links pointing at the old location, run `./install.sh` from the checkout, then `relocate-claude-config --repair [--allow-outside-home] <checkout path>` with the flag when the first run passed it.

Projected diff: ~1,300 changed lines, additions plus deletions (relocate script ~350, new test files ~900, `README.md` ~35, existing test file ~10, `CHANGELOG.md` ~15, `docs/scripts.md` ~2, `docs/transcript-analysis.md` ~3). That is above the about 1,000 the engineer accepted at row51, and the engineer then chose to proceed (row55). PR 1's script and tests ran about 1.7x and 2.6x over its projection by `git diff --numstat`, so the earlier ~880 was low. [unverified: an estimate from this plan's own lists, not measured] The script would reach about 1,000 lines (687 now plus the changed lines). Row16's limit makes that a split question. Row1 rules out a sourced sibling. The fallback is landing M3 and its tests as their own PR (about 60 lines). The new tests split across five files by seam (Critical files), so the "new test files ~900" figure is the total across them. After the code is written, a `wc -l` and `git diff --numstat` of the diff gives the real figure, which goes in the PR body.

## Verification

1. **Scoped suite:** `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py`. It selects `claude/.claude/scripts/tests/`, which holds both relocate test files, plus whatever else its rule table maps a script change to.
   - Every pre-existing relocate test passes with only the rename and comment edits. None writes a roots file, so together they show that without the file, links and exit codes are unchanged. Backup names change by design (M3).
   - Every new test passes, unit and integration layers alike. A `requires_non_root` case that skips is reported as skipped, not as passing.
2. **Lint:** `scripts/list-shell-files.sh | xargs -0 scripts/venv-run.sh shellcheck` and `scripts/venv-run.sh ruff check claude/.claude/ claude-skills/ plugins/ evals/`.
3. **Mutation checks, reverted before commit.** Each names the test or case id that must fail. Run them non-root. A mutation whose only catcher is a `requires_non_root` case counts as unverified when that case skips.
   - M1, the walk and classification:
     - Write absolute link text: `test_stow_owns_a_repointed_link[claude-skills]` and `[claude]`.
     - Drop the skip for a link that resolves: `[live-link]` and `test_runner_second_call_is_idempotent`.
     - Drop the text-shape match: `[other-shape]` and `[near-miss-text]`.
     - Drop the leading `/` from the suffix: `[near-miss-text]`.
     - Leave the pattern's expansion unquoted: `[glob-in-name]`.
     - Drop the new-target existence check: `[wrong-root-text]`.
     - Read the old text with plain `$(readlink -- "$path")` instead of `readlink -n` plus the sentinel: `[trailing-newline-text]`.
     - Drop the `new_text` sentinel (`; printf x` and the `%x` strip): `[newline-ending-name]`.
     - Descend through a linked directory on the account side: `[under-a-linked-dir]`.
     - Test the checkout side with `-d` alone, without the `-L` exclusion: `[linked-checkout-dir]`.
     - Drop the earlier-root check: `[shared-position]`.
     - Drop `dotglob`: `[stale-nested]`.
     - Drop `local` from the walk's position variable: `[stale-nested]`.
     - Stop at depth 1: `[stale-nested]` and the integration test's `skills/example` assertion.
     - Compute the text from the listed dir instead of the link's parent: `[stale-nested]`.
     - Drop the search-permission check: the failure test's `[unsearchable]`. Apply it only at the dir itself: `[unsearchable-nested]`.
     - Walk the listed dir's own entries instead of the checkout's: the runner test's `[home]` and `[checkout-parent]` counts, and `[not-a-checkout-position]`.
     - Return 1 when a link is left alone: the return-status assertions of `[other-shape]`, `[near-miss-text]`, `[wrong-root-text]` and `[glob-in-name]`, and the integration success test's exit code.
     - Count a failed link as left alone: the failure test's count assertion.
     - Drop the left-alone line: the same four ids' line assertion and the integration success test.
     - Unquote the position in one path expansion in an argument position, where word splitting applies: `[awkward-name]`. Unquote `<dir-real>` or `<new-real>` in one: `test_runner_resolves_symlinked_and_awkward_paths`. An unquoted expansion inside `[[ ]]` or an assignment does not split, so it is no mutation.
     - Pass the position through `eval` in one path expansion: `[awkward-name]`'s `injected` assertion.
     - Key an indexed array by a name taken from the checkout: `[awkward-name]`'s `injected` assertion.
     - Index the reader's seen-paths by physical path in an indexed array: `test_reader_matches_config_dir_parser`'s `injected` check.
     - Exit the unit at the first failed link: the failure test's `scripts` assertion.
     - Replace the temporary link and rename with `ln -sfn` over the old link: the failure test's `[temp-link]`. Seed this one against the written `ln` function before reporting the pass, since its detection rests on the function's flag match.
     - Drop the temporary link's resolve check: `[bad-text]`. Drop the temporary link's removal after that check fails: `[bad-text]`.
     - Drop the re-check before the rename: `[recheck-dir]` and `[recheck-live]`.
     - Drop the temporary link's removal after a failed rename: `[rename]`.
     - Drop the backup name's removal after a failed copy: `[backup-copy]`.
     - Skip the temporary link's removal when the allocator refuses: `test_backup_dir_refusal_reaches_the_repoint_unit`'s stray assertion.
     - Drop the pre-check on the temporary name: `[temp-name-taken]`.
     - Drop `--` from the backup copy's `ln -sf`: `[dash-led-text]`. Drop it from the temporary link's `ln -s`: the runner test's `[checkout-parent]`.
     - Print one cause for every failed step: the failure test's cause assertions.
     - Let the temporary link's `ln -s` stderr through: `[unwritable]` and the failure test's `acct-` assertion in `[temp-link]`. Let `mv`'s stderr through in the rename: the same assertion in `[rename]`.
     - Print the dir's path instead of its line number: every decision-table id's `acct-` assertion.
     - Drop the outcome line: the decision table's count assertions and the integration test.
     - Leave the search count at 0 when a search fails: `[unsearchable]` and `[unsearchable-nested]`.
     - Print a `left … alone` line for a failed link: the failure test's no-`left` assertion.
     - Match only relative old text: `[stale-absolute]`. Match the old text against one old checkout path, as the set-aside design would: `[stale-other-checkout]`.
     - Create a link at a checkout position the account lacks: the integration success test's `acct-b` listing.
   - M2, the reader:
     - Delete each of these, one at a time: `test_reader_matches_config_dir_parser` fails for every one.
       - the `#` skip;
       - the `~/` expansion;
       - the `~` expansion;
       - the CRLF strip;
       - the padding trim;
       - the absolute-path check;
       - the directory check;
       - the dedupe;
       - the last-line arm.
     - Treat `#` anywhere in a line as a comment start: the same test's mid-line `#` row.
     - Drop the readable-regular-file guard: `test_reader_and_runner_survive_every_roots_file_state`'s `[directory]` and `[unreadable]`.
     - Drop `|| return 0` from the reader's loop: the same test's `[last-relative]`, `[last-missing-dir]` and `[last-duplicate]`. Seed this one against the written reader before reporting the pass, since whether the loop's status leaks depends on how a skipped line's arm ends.
     - Use `_readlink_f`'s output with no failure check: the same test's `[readlink-fails]`.
     - Drop the reset: `test_runner_resets_declared_rows_on_each_call`.
     - Drop the dedupe, besides the parity test's failure above: `test_runner_dedupes_a_dir_listed_twice`.
     - Drop the `checking line` line: `test_reader_names_a_line_before_it_probes_the_path` (probes file).
   - M3, the allocator:
     - Change `_new_backup_path` back to `<stem>.$$`: `test_same_named_dangling_links_get_their_own_backups`.
     - Drop the refusal from `_new_backup_path`: `test_backup_dir_refusal_reaches_the_repoint_unit`.
     - Drop the empty file's removal in `_quarantine_if_dangling`: `test_a_failed_quarantine_move_leaves_no_placeholder`.
     - Drop the `L<line>` stem: `[stale-relative]`'s backup-name assertion.
   - M4, the runner and closing text:
     - Reset the failure array in the runner, then separately ignore a failed unit: `test_runner_appends_failures_and_follows_relink_packages_targets`.
     - Call the runner before `relink_packages`, once per call site: `test_a_failed_dir_exits_3_and_the_printed_retry_repoints_it`'s exit code, in that site's mode.
     - Call the runner before `finish_relocation`, once per call site: the same test's record assertion, in that site's mode.
     - Call the runner after `report_relink_outcome`, once per call site: the same test's stderr-label assertion, in that site's mode.
     - Drop the `readlink` precondition: `[no-readlink]`. Drop its roots-file condition: `[no-readlink-no-file]`.
     - Walk a dir the file does not list, such as the siblings of each listed dir or, when the file yields no rows, the siblings of `~/.claude`: the integration success test's `acct-unlisted` assertion and `test_reader_and_runner_survive_every_roots_file_state`'s five no-dir ids.
     - Probe write permission on the listed dir before walking it: `test_a_dir_with_nothing_to_re_point_is_not_written`'s `0o555` id, which would exit 3 for a healthy read-only account.
     - Test containment with a prefix match that has no `/` boundary: `test_runner_skips_home_claude_and_the_checkout_and_bounds_ancestors`'s `[sibling-prefix]`.
     - Drop the `walking` line: `test_runner_names_each_walked_line_before_its_outcome_and_no_skipped_line` (probes file).
     - Take every `RELINK_PACKAGES` row as a root: the runner test's `acct-b/thing` assertion.
     - Drop the `~/.claude` skip, then separately the inside-checkout skip: `test_runner_skips_home_claude_and_the_checkout_and_bounds_ancestors`'s `[home-claude]` and `[inside-checkout]`.
     - Compare `~/.claude` unresolved instead of by physical path: the same test's `[home-claude-symlinked]`.
     - Print the listed dir's path in the runner's skip line: the same test's `[home-claude-symlinked]` and `[inside-checkout]`.
     - Pass `<new-path>` unresolved: `test_runner_resolves_symlinked_and_awkward_paths`.
     - Drop the runner's `re-pointing the dir on line <N> … failed` err: `test_a_failed_dir_exits_3_and_the_printed_retry_repoints_it`'s stderr assertion for that err, in both modes.
     - Read the roots file from `<new-path>`'s `claude/.claude/transcript-config-dirs` instead of `~/.claude/transcript-config-dirs`: `test_both_modes_repoint_listed_dirs_and_report_each`, in both arms, because its roots file is written only into `home/.claude` and the checkout ships none.
     - Delete the registration bullet: `test_manual_steps_name_the_retry_flag_and_give_registration_its_own_bullet`'s `register-marketplace` assertion.
     - Delete the unlisted-dirs bullet's `--repair` sentence: the integration success test's retry-command assertion.
     - Delete the bracketed `[--allow-outside-home]` from its printed command: the integration success test's retry-command assertion.
     - Delete its `with the flag when this run passed it` clause: the unit test's flag-clause assertion.
     - Delete the unlisted-dirs bullet's write-access sentence: the integration success test's write-access token assertion.
     - Leave the old first bullet unsplit, so registration merges into another bullet: the new unit test's assertion that the bullet holding the `register-marketplace` line opens with text naming `marketplace`.
   - M5:
     - Match the prefix without the trailing `/`: the shared-prefix case.
     - Drop the trailing-`/` strip, which is what stops the climb at `/`: the `/`-start case and the different-first-components case, which fail by their timeout.
4. **The real move is not part of this plan's verification.** The engineer's own rename waits for PR 2 and PR 3 ("Wait for PR 2 and PR 3", in the Ask). By this plan's reading of "No manual steps please", it also waits for PR 2b, after which a listed account's only manual step is a link the run reports as left alone, or a listed dir it reports as not re-linked (row27, row47, row56).
5. **Installed copy (engineer, after merge):** run `./install.sh` from the checkout, then `cmp ~/.claude/scripts/relocate-claude-config.sh ~/.local/bin/relocate-claude-config` exits 0 (row1).
6. **Cross-filesystem `mv -f` probe (before merge):** the implementer records one probe on macOS, and the engineer one on GNU/Linux if the implementer has none, with the symlink and the destination file on different filesystems. Run `mv -f -- <symlink> <existing regular file>`. Exit 0 with the destination now a symlink carrying the source's text confirms row11. A refusal means `_new_backup_path` must not pre-create the destination, and M3 is revised before merge. The new tests run on one filesystem, so they do not cover this.

## Out of scope

- **Marketplace registration of listed accounts — the next PR, PR 2b** (row26, row27). Here it stays manual through M4's registration bullet, which PR 2b narrows to unlisted accounts. Starting notes for PR 2b's own plan, not prescriptions:
  - Function to start from: the script's own `sync_marketplace_registration` (`relocate-claude-config.sh:400-439`), run once per listed dir with `CLAUDE_CONFIG_DIR` set to that dir. `register-marketplace` already runs per account that way (`register-marketplace.sh:4-9`). Calling `register-marketplace` itself instead would be the first code from `<new-path>` the script runs (row15), and it also adds other marketplaces and installs plugins (`register-marketplace.sh:106-144`).
  - Hazard: its no-registration arm (`relocate-claude-config.sh:415-421`) adds a registration to an account that holds none (row25). That account would gain a registration it never held, which M1 never does for a link (row24).
  - Sibling hazard: its remove-and-add arm (`relocate-claude-config.sh:423-438`) re-registers an account recorded at a different checkout that still exists. That is the registration form of the integration test's `acct-c`, which M1 leaves alone.
  - Reusable from this PR unchanged: `read_declared_config_dirs` (M2), `relink_declared_dirs`'s per-dir loop with its two skips, `RELINK_FAILURES` with its `transcript-config-dirs:line-<N>` label (M4), line-number-only messages (M6), and the new test file's roots-file and account builders.
  - Left to PR 2b's plan: whether a listed account's failed registration joins exit 3, since the existing function never fails the run.
- **Config dirs not listed in the roots file** (row20).
- **Where the roots file comes from:** see M1's Trust bullet. No supply disclosure, test or remedy text is added (row53).
- **A `--repair` destination whose package root is a link.** The walk does not test whether a package root is a link, so it walks a linked root. Such a destination can then make the run print a listed account's entry names that also exist under the link's target. It can also re-point matching stale links through the linked root, as for any content of a destination the run trusts (row31). The re-pointing pass writes nothing inside the linked root's target: M1's temporary link and `mv` land in the account's own physical parent, and the backup lands in the backup dir (M1, M3).
- **A run with `readlink` absent:** M4 states the runner's precondition. [unverified: whether any machine this script targets lacks `readlink`]
- **Entries tracked since a listed account was last installed.** They stay unlinked until that account's own installer runs (M1).
- **A listed dir that is itself a dangling link**, such as an account folded whole into the old checkout. The reader skips it with its not-an-existing-directory warning, and the unlisted-dirs bullet covers a listed dir reported as not re-linked (M4). Re-pointing it would recreate the fold, which keeps the account's own state inside the checkout.
- **The race between M1's re-check and its rename.** A dangling link that starts resolving to a directory inside that window gets the temporary link moved into that directory. Only a same-user change to the account dir can cause it, and that user can already write there directly. The re-check itself is tested (`[recheck-dir]`, `[recheck-live]`), and the window after it is not.
- **Leftovers of a killed run.**
  - A kill between M1's create and its rename leaves the temporary link, which resolves into the new checkout. README names its pattern as safe to delete.
  - A kill between the allocator's `mktemp` and its `ln -sf`, or `_quarantine_if_dangling`'s `mv -f`, leaves an empty file in the backup dir.
  - No later run removes either. An INT and TERM `trap` in the unit would, but the script sets no trap today, and trap handling belongs with the deferred EXIT-trap follow-up below (round-2 platform review R6).
- **A time bound on the walk.** The pass runs after `finish_relocation` (M4), so a probe on a hung mount blocks only this pass and the closing text, as it blocks any other reader of that dir. README tells the user to interrupt, then take out of the list or fix the line the last `checking` or `walking` line names. For a destination whose package roots are real directories, the checkout bounds how many probes run (see the linked-package-root entry above).
  - Whether an interrupt takes effect on a hard-mounted dir is not checked here, so README makes no claim about it (round-3 platform review R4).
- **Roots-file lines that Python and bash split differently** (row49). A lone CR, VT, FF or other separator `str.splitlines` breaks on but `read` does not gives the two readers different line numbers. No path list needs those characters, and mirroring them in bash adds a translation step for no real file, so the parity fixture holds none.
- **The EXIT-trap retry line for post-move failures**, PR 1's deferred follow-up. It touches every post-move exit path and the README's exit-1 text, so it costs well above zero here.
- **`git worktree repair` for linked worktrees** — PR 3.
- **Stow resource files and `STOW_DIR`.** This PR adds no `stow` call.
- **Moving the relocate test helpers into a `_relocate_helpers.py` module** (round-1 SDET review R9). It belongs with the split of the over-limit `test_relocate_claude_config.py`, not in this PR (M7).
- **A per-run backup record and an owner-only backup dir** (round-1 security review R5). M3 sets both aside.
- **`cleanup-merged-branches.sh`'s `read_configured_roots`**, the second copy of the roots grammar after `_config_dir.py`, which no parity test pins (round-1 product review R9). This PR's bash reader is the third copy. This PR does not edit that script.
- **A run where a package and a listed dir both fail** (round-1 SDET review R6). The runner test pins the append, and the exit-3 test pins the call order in both modes, which together cover the loss it guards against.
- **PR 1's CHANGELOG bullet**, whose "stay manual" clause is a record (`.claude/rules/changelog-entries.md`). The new bullet records this change.
- **Peer-owned files** (G2).
