# Repair linked worktrees when relocating the checkout

## Context

Goal: make `relocate-claude-config` run `git worktree repair` over the linked worktrees under `<checkout>/.claude/worktrees/*` after it moves the checkout, so the checkout can live at a new path without every linked worktree losing its link to it.

Ask: "Yeah, start PR3 now." (engineer, answering whether to start the third relocation PR). Engineer selections on design questions: "Exception row (Recommended)" for how the change satisfies the code-file-size gate, and "No prune, report only (Recommended)" for whether the relocation also runs `git worktree prune`.

Why now: the first two relocation PRs re-link the stow packages and re-point the listed config dirs. Linked worktrees are the remaining step that README "Repo relocation" and the script's closing text still leave manual. The checkout move waits on this PR.

Intended outcome: after `relocate-claude-config <new-path>` (and `--repair`), every linked worktree up to two levels under `<new-path>/.claude/worktrees/` has working admin links in both directions, unless git reports an error for it. A repair git reports as failed, or a failed listing, makes the script exit 3 with the `--repair` retry line, as for the other failed follow-ups. A record whose path does not exist is reported and the script still exits 0, because no retry clears it. Nothing is deleted or pruned.

## Approach

Both modes run one `git worktree repair` from the moved checkout as their last pass. It names each real directory holding a `.git` file one or two levels under `<new-path>/.claude/worktrees/`, the two shapes the branch-naming convention produces (row5). Before the repair, the run prints one line for each existing record it does not name, because git's sweep reaches those too. After it, the run reports each record whose path does not exist and still exits 0.

The design guards the shapes this repo's own tooling produces and no more. Row18 gives the ground for each finding it declines. The engineer chose this lean shape (row36, row37). The pass is a subshell unit like the two re-link passes. It runs after the listed-config-dir pass (M4). It runs git only when the checkout's `.git` is a real directory, with git's upward repository search stopped at the checkout's parent, after unsetting the four repository-location variables `worktree-ensure.sh` unsets (M3). The candidates come from the checkout's own directory, because after a move git's records name the old paths (M1). One `git worktree list --porcelain` reader serves the announcement before the repair and the missing-record report after it (M2, M6). The script grows past 1,000 lines and takes a `structural exception` row (M5). The new tests go in a new file (M5).

**Root problem.** After the checkout moves, each linked worktree's `.git` file still names `<old-path>/.git/worktrees/<id>`, and the checkout's record of each worktree inside it still names the worktree's old path. So git fails inside those worktrees, and the checkout sees them as missing. The script's closing text leaves `git worktree repair` to the user (row3).

**Givens** (fixed, outside this design's reach):

- **G1 — the script runs as a standalone real-file copy and sources nothing.** It must keep working when `~/.claude` is broken, so dissolving this needs a decision outside this plan. [verified: `relocate-claude-config.sh:1-16`; `install.sh:477-480`]
- **G2 — git owns the worktree admin files and what `git worktree repair` and `git worktree list` do.** Vendor behavior, so the design calls git rather than editing its files (rows 9-13).
- **G3 — the code-file-size gate.** A repo rule caps each tracked `.py` and `.sh` file at 1,000 lines and holds an over-limit file to an exact ceiling. [verified: `docs/design-decisions/code-file-line-limit.md:24, 47-50`]
- **G4 — a peer branch owns CI config, the community docs, `_lib.sh`, `deny-private-project-refs.sh`, `require-stow-reminder.sh` and README URL lines.** Another party owns them. [unverified: relayed by the dispatcher]
- **G5 — the repo depends on no other repository.** A repo rule, so the script and docs name no outside tool for this step. [verified: `CLAUDE.md` § "Working in this repo"]

**Rows:**

1. The engineer asked for this PR. [engineer-verified: "Yeah, start PR3 now."]
2. Both modes call `relink_packages`, `finish_relocation`, `relink_declared_dirs` and `report_relink_outcome` in that order, then exit 3 when `RELINK_FAILURES` is non-empty. `relink_packages` resets that array, and `relink_declared_dirs` appends `transcript-config-dirs:line-<N>` to it. [verified: `relocate-claude-config.sh:496-509, 772-775, 899-905, 924-930`]
3. A unit is a function whose body is a subshell, run as an `if` condition with errexit off, so its `shopt` changes and locals end with it. Its runner is called bare, appends to `RELINK_FAILURES`, and ends `return 0`. [verified: `relocate-claude-config.sh:464-509, 712-778`] `print_manual_steps` tells the user to run `git worktree repair` for every linked worktree. [verified: `relocate-claude-config.sh:804`] No code in the repo runs it. [verified: this session's greps of `*.py` and `*.md` for `worktree repair`, which found only `test_relocate_claude_config.py` and `README.md`; the script by Read]
4. Of the closing text, the relocate tests pin the `Not done by this command:` heading and, at `test_relocate_claude_config.py:594`, the substring `git worktree repair` in the exit-3 stderr. [verified: a grep of the relocate test files]
5. `worktree-ensure.sh` puts a branch's worktree at `<checkout>/.claude/worktrees/<branch>`, and branch names follow `<TICKET-ID>/<topic-slug>`, or `<topic-slug>` alone with no ticket system. So a worktree named by that convention sits one or two levels below `.claude/worktrees/`. [verified: `worktree-ensure.sh:192`; `branch-management/SKILL.md:20-22`] `worktree-ensure.sh` does not enforce the convention, because its name check and `git check-ref-format` both allow any number of `/`. `git check-ref-format` does refuse a component that begins with a dot. [verified: `_worktree-lib.sh:526-538`; `git-check-ref-format.adoc:30-32` in git 2.56.0's documentation] A Glob of this repository's main checkout found linked worktrees at both depths and none at the third. [verified: Globs run this session] README shows only the first-level shape. [verified: `README.md:329, 493`] `--repair` never learns the old location. [verified: `relocate-claude-config.sh:207-209`; `.claude/plans/relocate-restow-secondary-accounts.md` row 8]
6. `worktree-ensure.sh` refuses a branch name outside ASCII letters, digits, `.`, `_`, `/` and `-` before any write. Its check lists each character, then runs `git check-ref-format --branch`. So no worktree it creates holds a space or a newline in its path below the checkout. [verified: `worktree-ensure.sh:9-10, 94-105`; `_worktree-lib.sh:518-538`] A worktree the harness's own worktree tool makes follows a name rule of its own. [unverified: relayed by the dispatching session]
7. `_make_repo` builds a fake checkout that is not a git repository. [verified: `_relocate_helpers.py:39-65`] No relocate test makes one a repository. [verified: this session's grep of the relocate test files for `git init`, `init_git_repo` and `_init_repo`, which found none] `git -C <dir>` in a directory with no `.git` searches upward for a repository. [unverified: git's repository discovery, not run; case e pins the gate against it]
8. `_script_env` copies the test process's environment, so an inherited repository variable reaches every script run. [verified: `_relocate_helpers.py:160-169`] git exports `GIT_DIR`, `GIT_WORK_TREE` and the like to a hook's environment. [verified: `githooks.adoc:30-35` in git 2.56.0's documentation] The repo's git floor is 2.43. README requires it, `install.sh` enforces it at install, and nothing checks it at run time. CI pins git 2.43.0. [verified: `README.md:113`; `install.sh:105-136`; `.github/workflows/tests.yml:150`] Rows 9-13 and 40-42 were probed on git 2.56.0 only, so their behavior on 2.43 stays open until Verification 1's rerun or CI. [unverified]
9. git's documentation for the both-moved case: "If both the main worktree and linked worktrees have been moved or copied manually, then running `repair` in the main worktree and specifying the new _<path>_ of each linked worktree will reestablish all connections in both directions." [verified: `git-worktree.adoc:166-169` in Homebrew git 2.56.0's documentation] A scratch probe on git 2.56.0 confirmed it: a moved main checkout with three moved inner worktrees and one unmoved outside worktree had every link repaired in both directions. [verified: probe run this session, `git -C <new> worktree repair -- <inner paths>`; test case a pins it]
10. The probe on git 2.56.0 confirmed each clause below. [verified: probe run this session; cases a, b and c pin them]
    - `git worktree repair <path>...` repairs each named path, then sweeps every record whose path exists and fixes that worktree's `.git` file.
    - One failing path does not stop the others. Any failure makes the exit status non-zero, and prints an `error:` line naming its path on stderr.
    - The sweep skips a record whose path does not exist, silently.
    - With `--` and no path, it repairs by the sweep alone.
11. `git worktree repair` neither reads a worktree's lock nor touches its working tree. So a locked or dirty worktree is repaired like any other and keeps its lock and its changes. [verified: probe on git 2.56.0 kept the lock file and an untracked file; test case a pins it]
12. Two linked worktrees named `dup`, one at `<checkout>/.claude/worktrees/dup` and one elsewhere, got record ids `dup` and `dup1`. The inside one, added first, got `dup`, and the outside one, added second, got `dup1`. After the checkout moved, `git -C <new> worktree repair -- <new>/.claude/worktrees/dup` exited 0 and printed a `repair:` line for each, and both worktrees' `git rev-parse --git-common-dir` named `<new>/.git`. [verified: probe on git 2.56.0] So no probe named a path whose record id carries a suffix. Case a's `TICKET-2/nested`, added after `TICKET-1/nested`, pins that shape. [unverified: its id `nested1` is inferred from this probe's order]
13. `git worktree list --porcelain` prints a `worktree <path>` line as the first attribute of each record. [verified as documentation: `git-worktree.adoc:460-469`] A path holding a space and a non-ASCII letter printed verbatim in the probe. [verified: probe on git 2.56.0; case a pins the space] The porcelain section names quoting without `-z` only for a lock reason, so only a newline in a path splits a record. [unverified: inferred from `git-worktree.adoc:501-503`] git 2.56.0 creates a linked worktree at a path holding a newline when asked directly. [verified: probe on git 2.56.0] `-z`, which ends each attribute with a NUL, arrived in git 2.36. [verified: `RelNotes/2.36.0.adoc:110-112` in git 2.56.0's documentation]
14. Asked how the change meets the code-file-size gate, the engineer chose an exception row. [engineer-verified: "Exception row (Recommended)"] Asked whether the relocation also runs `git worktree prune`, the engineer chose not to. [engineer-verified: "No prune, report only (Recommended)"]
15. The option descriptions are the dispatching session's, not the engineer's words. [unverified: the dispatching session's descriptions]
    - The exception row is a `structural exception` row whose reason is the standalone real-file copy.
    - "Report only" lists a missing path, a locked worktree or a failed repair in the closing output, and deletes nothing. Row27 settles how a missing path ends the run.
16. This plan reports a locked worktree only when its path does not exist, because a locked worktree that exists is repaired (row11). That narrows row15's description for that one case. Asked whether a locked worktree whose directory exists should be repaired or reported, the engineer chose to repair it. [engineer-verified: "Repair existing ones (Recommended)"]
17. The run already trusts `<new-path>` with code. Both modes stow its `claude` package, hooks included, into `~/.claude` and install its copy of this script into `~/.local/bin`. [verified: `relocate-claude-config.sh:461, 897, 922`] For the listed-accounts reach of `--repair`, the engineer chose disclosure in the header, README and CHANGELOG. [verified: `relocate-claude-config.sh:28-29`; `.claude/plans/relocate-restow-secondary-accounts.md` row 31]
18. Every step after destination validation inherits row17's trust, and the header puts the script's security investment in that validation. [verified: `relocate-claude-config.sh:22-23`] So this plan declines a review finding that needs a destination shape `worktree-ensure.sh` never produces (row5, row6). git's sweep gives such a destination no privilege the stowed hooks have not already given it. The decline rests on that fact, not on `CLAUDE.md` § "Hook threat model", whose waivers cover gate hooks only. [unverified: this plan's scope rule] Where a probe settles what git does, a decline rests on the probe instead (row41, row42). The declined findings, one line each:
    - Round-1 ciso R2, its `rev-parse` identity compare and full variable list: a crafted `.git` directory, and variables an operator sets on purpose (row38). Its `-d` and `! -L` gate is adopted (M3).
    - Round-1 ciso R3 (iii): the engineer's announcement answers a record naming an existing outside directory (row29), and case a pins it.
    - Round-1 ciso R3 (iv) and round-2 sdet R6: the full variable list is dropped (row38).
    - Round-2 ciso R1 (b)-(d), and (a) beyond the announcement's set difference (row35): a recorded entry whose `.git` is missing or a symbolic link. git's sweep writes nothing through a symbolically linked `.git` (row42). A missing `.git` sits in an existing record, which the announcement names before the repair (M6).
    - Round-3 ciso R1 (b): in the copied-checkout shape it names, git left the original's record unchanged (row41).
    - Round-3 ciso R2: row42's probe answers it, so the announcement needs no clause about writing through a link.
    - Round-2 ciso R2: a checkout `.git` directory whose `commondir` names another repository.
    - Round-2 ciso R3: the announce-before-repair order is two adjacent statements, cheaper to read than to shim. The config channel went with the full list. Case a now pins `%q` on the destination and on a record path. Case b's retry pins the no-announce negative.
    - Round-2 ciso R4: git's own lines stay raw (Out of scope).
    - Round-2 ciso R5: a record whose path is a dangling symbolic link.
    - Round-1 sdet R5: `GIT_DIR` alone shows the `unset` line runs, and the other three names sit on that line.
    - Round-2 sdet R2: failing every listing shows that a failed listing fails the unit. Which read failed changes no exit code. Case f's unchanged `.git` pins that the repair does not run after a failed first read.
    - Round-2 sdet R4: the decoy-repository gate cases it names are cut, and case d keeps the same-id decoy record it endorses.
    - Round-2 sdet R5: a checkout `.git` that is a symbolic link. Case e's `.git` file pins the same branch.
    - Round-2 sdet R1: the newline-name case it names is cut.
    - Round-1 platform R4, restated as scope: no worktree `worktree-ensure.sh` creates holds a newline (row6). A split path yields only a false missing-record line and exit 0 (row13, row27).
19. The exceptions table keys each row by quoted path, in sorted order, and a structural exception takes `ceiling`, `verdict` and `reason`. Its verdict rule reads "every seam would change how the file is loaded, invoked or installed, so the file stays whole". `post-crash-sessions.py` and `select-tests.py` are the neighbouring rows. [verified: `code-file-size-exceptions.toml:1-12, 246-251`] The gate passes a row only when the file's line count equals its ceiling. [verified: `docs/design-decisions/code-file-line-limit.md:47-50`]
20. The script is 980 lines. [verified: this session's line count by Grep] The design adds about 80, so it ends near 1,060. [unverified: this plan's estimate]
21. `test_relocate_claude_config.py` is 954 lines and `test_relocate_claude_config_declared_dirs.py` is 939. [verified: this session's line count by Grep] The relocate test files share fixtures through `_relocate_helpers.py`. [verified: `_relocate_helpers.py:1-10`]
22. The new test file can build on these helpers. [verified: `conftest.py:100-117, 1795-1805, 1944-1955`; `helpers.py:1487-1497, 4038-4060`; `_relocate_helpers.py:39, 304-335`]
    - `isolated_git_env` drops every `GIT_CONFIG_*` variable from a base environment and turns off the global and system config files.
    - `_make_repo` takes the directory to build its checkout in as its first argument.
    - The scripts conftest's `_git` runs git under `_clean_env()`. That removes `GIT_DIR`, `GIT_WORK_TREE`, `GIT_COMMON_DIR` and `GIT_INDEX_FILE`, the four names row38 unsets.
    - `_init_repo` calls `init_git_repo` with no `env`, and `_commit` and `_lock_worktree` pass none, so each inherits the caller's environment.
    - `init_git_repo` takes an `env` for every git call it makes.
    - `_break_worktree_git_link` writes `gitdir: /nonexistent/gitdir` into a directory's `.git`.
    - `_run_sourced` sources the script, runs a `prelude`, then runs each call as an `if` condition. With `bare` set it runs the call plainly with errexit on, as production calls a runner.
23. The earlier CHANGELOG relocate bullet saying linked worktrees stay manual is a record, so a new bullet records this change. [verified: `CHANGELOG.md:113`; `.claude/rules/changelog-entries.md`]
24. The listed-config-dir pass can block on an unreachable mount, and README tells the user to interrupt it. [verified: `README.md:457-459`]
25. `select-tests.py` selects `claude/.claude/tests/test_code_file_size.py` for a `.py` change and for a table change. [verified: `select-tests.py:203-208, 1101, 1116`] It selects `claude/.claude/scripts/tests/` for a script change. [verified: `.claude/plans/relocate-restow-secondary-accounts.md` Verification 1, citing `select-tests.py`]
26. Asked whether the plan's `Ask:` quote is a fair quote, the engineer confirmed it. [engineer-verified: "Yes, keep the quote"] Asked about the 425-line projection, the engineer chose to proceed. [engineer-verified: "Proceed anyway"]
27. Asked how a record whose path does not exist should end the run, the engineer chose to report it and exit 0. [engineer-verified: "Report, exit 0 (Recommended)"]
28. The description under row27's label is the dispatching session's. It lists each missing-path record in the output and the manual steps, and prunes nothing. It reserves exit 3 and the retry line for what a retry can fix, such as a git repair error or a failed listing. [unverified: the dispatching session's option description] This plan also applies that reservation to a checkout `.git` that is a symbolic link or not a directory (M3), which a retry alone cannot change either. [unverified: this plan's extension] A `.git` directory git will not open makes the first listing fail, which exits 3 with the retry line, as any failed listing does (M2, row40). [unverified: inferred from row40's probe; case g pins it]
29. For the reach of git's sweep, the engineer chose disclosure plus a stdout line. [engineer-verified: "Disclose plus stdout line (Recommended)"]
30. The description under row29's label is the dispatching session's. [unverified: the dispatching session's option description and relay]
    - No gate and no refusal.
    - Disclosure in the script header, README and CHANGELOG.
    - In both modes, before the repair, one stdout line per existing record outside `<new-real>/.claude/worktrees/` that the sweep will reach, with the undo `git -C <other checkout> worktree repair <path>`.
    - It replaces the engineer's earlier "Pre-repair scoping gate (Recommended)" selection.
31. The script prints its retry path through `%q`. [verified: `relocate-claude-config.sh:854`] `_walk_declared_position` reads and updates its caller's locals. [verified: `relocate-claude-config.sh:642-730`]
32. A config dir left unlinked loads none of this repo's settings, hooks or skills until it is re-linked. [verified: `relocate-claude-config.sh:796-797`]
33. git prints its `repair:` lines on stdout and its `error:` lines on stderr. [unverified: recollection of git's `report_repair`; case b asserts only the `error:` stream]
34. No documented option scopes or skips the sweep. The synopsis is `git worktree repair [<path>...]`, and `--relative-paths` is the only option that names `repair`. [verified as documentation: `git-worktree.adoc:19, 149-169, 229-236`]
35. This plan widens row30's stdout line to every existing record the run does not pass to git, inside `.claude/worktrees/` included, because the sweep reaches those too (row10). [unverified: this plan's extension of the engineer's choice]
36. The engineer chose the lean plan, offered after an independent review of the test machinery against the threat model. [engineer-verified: "Adopt the lean plan (Recommended)"]
37. The description under row36's label is the dispatching session's: revise this plan to the independent architect's end state, answer each declined finding with one plan row, and first verify the branch-name character restriction (row6). That end state's specifics, and this plan's reading of them, are not the engineer's words. That the engineer asked for that review is the dispatching session's relay. [unverified: the dispatching session's option description and relay]
38. `git rev-parse --local-env-vars` lists fifteen repository-local names on git 2.56.0. [verified: probe on git 2.56.0] The unit unsets the four that `worktree-ensure.sh` unsets: `GIT_DIR`, `GIT_WORK_TREE`, `GIT_COMMON_DIR` and `GIT_INDEX_FILE`. [verified: `worktree-ensure.sh:13, 76`] The other eleven, such as `GIT_CONFIG_PARAMETERS` and `GIT_OBJECT_DIRECTORY`, are an accepted residual. git sets the location names in a hook's environment (row8), and an operator sets the rest only on purpose. [unverified: no run set the other eleven, so their effect on `worktree repair` and `worktree list` is unchecked]
39. On macOS, `mktemp -d` returns a `/var/folders/...` path, and `git rev-parse --absolute-git-dir` prints its `/private/var/folders/...` form, the one `cd -P && pwd` prints. [verified: probe on git 2.56.0] `canonicalize_for_comparison` was not compared against git's form. No kept mechanism compares the two unresolved, because M6 resolves each record path with `_readlink_f`, which `canonicalize_for_comparison` also calls. [verified: `relocate-claude-config.sh:134-158`]
40. The probe gave a checkout's `.git` two shapes, an empty directory and a directory holding only `HEAD`, each nested in a repository that records a worktree. [verified: probe on git 2.56.0 with `GIT_CONFIG_GLOBAL=/dev/null`, for the first four clauses below]
    - With no ceiling, `git -C <checkout> worktree list` and `worktree repair` acted on the ancestor repository.
    - With `GIT_CEILING_DIRECTORIES` set to the checkout's physical parent, both failed with `not a git repository`.
    - Under the same ceiling a valid nested repository listed normally, and a valid repository under a ceiling of `/` listed normally too.
    - An empty value did not bound the search, because the listing showed the ancestor. So a checkout whose parent is the root gets `/`, not the empty `${new_real%/*}`. [unverified: that `/` bounds the search for a root-parent checkout, not run]
    - git does not chdir up into a ceiling directory, and the ceiling excludes neither the current directory nor a `GIT_DIR` set in the environment. [verified as documentation: `git.adoc:555-568` in git 2.56.0's documentation]
    - So git still follows a gitfile or symbolic link at `<new-real>/.git`, which is why the `-d` and `! -L` gate stays. [unverified: inferred from `git.adoc:559-561`]
    - The repo already sets the variable in production code. [verified: `claude/.claude/scripts/transcript_analysis/gh_cli.py:183-184`]
41. In a copied checkout with the original still present, `git -C <copy> worktree repair -- <copy>/.claude/worktrees/w` rewrote only the copy's own record and the copy's worktree `.git`. The original's `.git/worktrees/w/gitdir` was byte-identical afterward. [verified: probe on git 2.56.0]
42. Two probes gave a recorded worktree a symbolically linked `.git`: in one it linked to a file reading `gitdir: /nonexistent`, and in the other it dangled. After `git worktree repair --`, the exit status was 0 and each `.git` was still a symbolic link. The target file was unchanged, and the dangling target was not created. [verified: probe on git 2.56.0] So git's sweep writes nothing through a symbolically linked `.git`.
43. On a review finding that the `.git` gate predicts where git's repository search stops, the engineer chose the ceiling. [engineer-verified: "Adopt ceiling, bounded re-review (Recommended)"]
44. The specifics under row43's label are the dispatching session's proposal. The ceiling replaces the `HEAD`-file test, and `-d` and `! -L` stay. The same round's two other findings fold in as case h and Verification 1's undo probe. Row18's decline does not reach this case, because README names honest producers of a partial `.git`, a sync-tool restore and a crash mid-relocation. [unverified: dispatcher's proposal; `README.md:447` names those producers]

**Mechanism justifications:**

- **M1 — one `git worktree repair` from the checkout, naming each real worktree directory up to two levels under `.claude/worktrees/`** (anchors: root, row5, row9, row10, row11, row12, row31, row33).
  - `<new-real>` is `canonicalize_for_comparison "$new_path"`, so every path the unit passes is absolute and physical.
  - The walk `_collect_worktree_candidates` fills the unit's candidate array, the way `_walk_declared_position` updates its caller's locals (row31). The unit sets `nullglob` and leaves `dotglob` off, because no branch-name component begins with a dot (row5). The walk globs `<new-real>/.claude/worktrees/*`:
    - A candidate is a real directory, not a symbolic link, whose `.git` is a regular file and not a symbolic link. One `[[ ]]` tests the entry with `-d` and `! -L`, and its `.git` with `-f` and `! -L`. The walk never looks inside one, so a submodule's `.git` file inside a worktree is never named.
    - A first-level real directory with no `.git` is a ticket directory, and the walk applies the candidate test to its entries.
    - Every other entry is skipped silently.
  - Two levels is what the branch-naming convention produces, and `worktree-ensure.sh` does not enforce it (row5). A worktree nested deeper is reported as missing after the repair (M2), and the run still exits 0. README states the bound.
  - The unit runs `git -C "$new_real" worktree repair -- <candidate>...` once. With no candidates it still runs, so the sweep repairs an unmoved worktree elsewhere (row10). A non-zero status sets the unit's failure flag.
  - A locked or dirty worktree is named like any other (row11). Two worktrees sharing a basename both repair (row12). A `--repair` retry repeats the call.
  - git's `repair:` and `error:` lines name each path, so the script adds no per-path label (row33).
  - Set aside:
    - One call per candidate. It runs the sweep once per worktree, and git's `error:` lines already name each failed path (row10).
    - Discovering worktrees from `git worktree list`. After the move each record names the old path, which `--repair` cannot map to the new one (row5).
    - The no-path call alone. The sweep skips a record whose path is missing, so it finds no worktree that moved (row10).
    - An unbounded walk. Through a worktree whose own `.git` is missing, it would descend into that worktree's whole tree.
    - Rewriting the `.git` and `gitdir` files directly. It reimplements git's admin format, relative-path mode included (G2).
- **M2 — one record reader, run before and after the repair** (anchors: row6, row10, row13, row14, row15, row16, row27, row28, row31).
  - `_read_worktree_records` declares `listing` with `local` on its own line, so its assignment keeps git's status: `listing=$(git -C "$new_real" worktree list --porcelain) || return 1`.
  - The unit calls the reader twice, so the reader empties `record_paths` and resets its first-record flag at its top. Case c's exact count pins the reset.
  - An `IFS= read -r` loop over a here-string of `$listing` then adds the path of each `worktree ` line after the first, the main worktree, to the unit's `record_paths` array (row13, row31). It uses no pipeline or process substitution, so the array and the status stay in the unit.
  - Before the repair, a failed read fails the unit and the repair does not run, so git writes nothing the run has not first named (M6).
  - After the repair, the unit reads the records again. For each record whose path fails `-e`, it prints through `err` `the checkout records a linked worktree at <path>, which does not exist, so it was not repaired`. A locked record is reported too (row16).
  - A missing record does not fail the unit (row27). A failed read does, because a retry can clear it (row28).
  - The unit keeps one failure flag across the repair call and this read, and runs both on every pass, so one run names both kinds of failure (case b).
  - The report names what the repair cannot reach: a moved worktree outside `.claude/worktrees/`, one nested deeper than two levels, one on an unmounted volume, and one deleted by hand. Each is a record `git worktree prune` would remove unless it is locked. Reporting it is what "report only" asks for in place of pruning (row14, row15).
  - A path holding a newline splits across lines, and its pieces are reported as missing. The run still exits 0 (row27), and no worktree `worktree-ensure.sh` creates holds one (row6).
  - Set aside:
    - The `prunable` attribute. git omits it for a locked record, and locking is the documented guard for a worktree on a device that is not always mounted. [unverified: inferred from `git-worktree.adoc:114-122`] Case c's locked record pins the `-e` test.
    - `git worktree prune --dry-run`. It names records by id rather than path, and skips locked records. [unverified]
    - Reading `.git/worktrees/*/gitdir` directly (G2).
    - The `-z` listing read with `mapfile` from a process substitution. The substitution's status is lost, so git's status would have to ride in as a field, a mechanism only a newline path needs (row13).
    - A `| while read` loop. It runs in a pipeline subshell, so a failure flag it sets is lost.
- **M3 — run git only on the checkout's own `.git` directory** (anchors: row7, row8, row17, row18, row28, row38, row40, row43, row44).
  - The runner returns at once, silently, when `<new-real>/.git` neither exists nor is a symbolic link. So a checkout with no `.git` runs no git, and git searches no parent directory (row7).
  - Otherwise the runner requires `[[ -d "$new_real/.git" && ! -L "$new_real/.git" ]]`, because the ceiling below does not stop git following a gitfile or symbolic link (row40). When that fails, it prints through `err` `<new-real>/.git is a symbolic link or not a directory, so no linked worktree was repaired`, and does not fail, because a retry alone cannot change that (row28).
  - The unit unsets the four names `worktree-ensure.sh` unsets (row38). Its one-line comment: inherited repository variables, which git exports to hooks, would send these calls to another repository (row8).
  - The unit then exports `GIT_CEILING_DIRECTORIES` set to `<new-real>`'s parent, or `/` when that parent is the root, since an empty value bounds nothing (row40). Its one-line comment: git then opens `<new-real>/.git` or fails, never a parent repository. A `.git` git will not open fails the first listing (row28).
  - Running git in `<new-path>` reads that repository's config, which adds no trust the run had not already given `<new-path>` (row17). An ownership mismatch fails with git's own message, and the unit adds no `safe.directory` override.
  - Set aside:
    - A `.git`-exists check alone. A gitfile or symbolic link there names another repository.
    - Comparing `git rev-parse --path-format=absolute --git-dir --git-common-dir` with `<new-real>/.git`, and unsetting every name `git rev-parse --local-env-vars` prints. Each guards only a crafted destination or a variable an operator sets on purpose (row18, row38).
    - Scrubbing the variables in `_script_env` only. A real run started with them set would still reach another repository.
    - A `HEAD`-file test in the gate. git fell through to the ancestor from a `.git` holding only `HEAD` too (row40).
    - Exporting `GIT_DIR=<new-real>/.git`. It also ends the search, but it may skip git's ownership check, which this unit relies on. [unverified]
- **M4 — runner, label, placement and closing text** (anchors: row2, row3, row4, row24, row31, row32).
  - `repair_linked_worktrees <new-path>` is the bare-called runner. After M3's checks it prints `repairing linked worktrees of <new-real>` on stdout, then runs the unit as `if ! _repair_linked_worktrees …; then`. On failure it prints `err "repairing linked worktrees failed"` and appends `linked-worktrees` to `RELINK_FAILURES`. It ends `return 0`.
  - Both modes call it after `relink_declared_dirs` and before `report_relink_outcome`, and case a pins that order. A config dir left unlinked loads none of this repo's hooks (row32), which costs more than git failing inside a worktree. git stats every recorded path, so a record on a stalled mount can block this pass, as a stalled mount can block the listed-dir pass (row24). This pass must not hold that one up. Set aside:
    - Before `relink_declared_dirs`. A stalled record would then hold up every listed account's hooks.
    - Before `finish_relocation`. The manifest and installed-copy writes would wait behind git.
  - `print_manual_steps` replaces its worktree bullet with: "A linked worktree reported above as not repaired, or every one when the run said it repaired none, is not linked to the checkout. Run `git -C <new-path> worktree repair <path>` with its current path once it is reachable, or remove its record yourself if you no longer need it. `git worktree prune` removes every unlocked record whose path does not exist."
  - `report_relink_outcome`'s resolve text gains one `echo` after the `transcript-config-dirs` sentence. It holds no backticks, since it is double-quoted: "A linked-worktrees entry means git reported an error above for a linked worktree, or listing the checkout's worktrees failed. Fix the cause the error names, such as a .git file that names no repository or an ownership mismatch. This command never prunes or deletes a worktree."
  - Every path the script prints from git's records or from the checkout goes through `%q`, as the retry line's path does (row31). So a destination name holding a space stays one token. git's own lines print the same names raw (Out of scope).
  - The test at `test_relocate_claude_config.py:594` asserts `worktree repair` instead, which the new manual-steps bullet holds (row4).
- **M5 — an exception row for the script, and a new test file** (anchors: G1, G3, row14, row15, row19, row20, row21, row22, row39).
  - The script ends near 1,060 lines. Its row goes between `post-crash-sessions.py` and `select-tests.py`, with these fields:
    - `ceiling`, the final `wc -l` of the script;
    - `verdict = "structural exception"`;
    - `reason = "install.sh installs it as a standalone real-file copy at ~/.local/bin/relocate-claude-config that must run while ~/.claude is broken, so it sources no sibling file and every split would change how it is installed (the script's header; install.sh's real-file-copy step)."`
  - Any later change to the script must also update the row's ceiling (row19).
  - The new tests go in `test_relocate_claude_config_worktrees.py`, named for its seam, so neither near-limit test file grows (row21).
  - Its fixture git calls run under `isolated_git_env` over `_clean_env`, through the file's own `_fixture_git` and through `init_git_repo` with that `env`. So neither a contributor's global config, such as `worktree.useRelativePaths`, nor one of the four inherited repository variables reaches a fixture. `_init_repo`, `_commit`, `_lock_worktree` and `_git` would leave one or both in place (row22).
  - Every fixture worktree is added with `git worktree add --detach` at a `Path.resolve()` path, and tests compare paths in that form (row39).
  - Mode-parametrized whole-script runs cover the wiring, the closing text and the retry. Cases that exercise only the unit call the runner through `_run_sourced` with `bare=True`, as production calls it, with real git as the oracle (row22).
  - Set aside:
    - A sourced sibling file, which G1 rules out.
    - Trimming about 60 lines of unrelated script text to stay under the limit. That is churn outside this change (Scope discipline, Axis 4).
    - An `env` parameter on the conftest helpers. It edits a shared fixture file for one caller, and `init_git_repo` already takes one.
- **M6 — name the sweep's reach before the repair, and disclose it** (anchors: row10, row17, row29, row30, row34, row35, row41).
  - No documented option scopes the sweep (row34), and the engineer chose disclosure plus a stdout line (row29).
  - Before the repair, both modes print one stdout line for each record whose path exists and whose physical path, by `_readlink_f`, is not one of the unit's candidates: `git worktree repair also reaches <path>, which this checkout records, and may write its .git file to name this checkout. If it belonged to another checkout, link it back with: git -C <other checkout> worktree repair <path>`.
  - That set is what the sweep reaches beyond the named paths (row10, row35). In a copied checkout, a named path whose `.git` still names the original's record did not lead git to rewrite that record (row41). The line also prints for a worktree already linked to this checkout, since telling the two apart would mean reading each worktree's `.git` target.
  - Following the listed-accounts precedent (row17), the header's threat paragraph, README and CHANGELOG each gain one sentence. It says that a `--repair` destination's worktree records choose which existing directories `git worktree repair` may write a `.git` file in, and that the run names each one it does not pass to git before the repair.
  - Set aside:
    - Disclosure alone. The user would learn which worktrees the sweep touched only from git's `repair:` lines, after the write.
    - A pre-repair scoping gate that refuses the repair. The engineer replaced it with this design (row30).
    - Dropping the repair from `--repair`. Its main case, an out-of-band move, would stay manual.

## Critical files

Comments and docs added below state durable one-line facts only, with no plan terms. One `code-writer` dispatch covers every file. The table row's ceiling and the tests depend on the script's final shape. The docs describe the same behavior. So a split would restate the design in each prompt.

- **Modify `claude/.claude/scripts/relocate-claude-config.sh`.**
  - Header:
    - The summary sentence at `:14-15` adds that both modes run `git worktree repair` for the checkout's linked worktrees.
    - The threat paragraph (`:18-29`) gains M6's sentence after `:28-29`.
    - Exit code 3 (`:58-60`) reads that linking a package, re-pointing a listed config dir, or repairing the checkout's linked worktrees, named on stderr, failed.
  - `usage()` (`:82`) adds that both modes repair the checkout's linked worktrees.
  - New functions after `relink_declared_dirs` (`:778`), each with a one-line comment, in this order: the walk `_collect_worktree_candidates` (M1), the record reader `_read_worktree_records` (M2), the unit `_repair_linked_worktrees` (M1, M2, M3, M6) and the runner `repair_linked_worktrees` (M3, M4).
  - `relocate_repo` (`:901-902`) and `repair_repo` (`:926-927`) call `repair_linked_worktrees "$new_path"` between `relink_declared_dirs` and `report_relink_outcome` (M4).
  - `print_manual_steps` (`:804`) and `report_relink_outcome`'s resolve text (`:852`) change as M4 says.
  - The comment above `report_relink_outcome` (`:810-812`) and its failure sentence (`:841-843`) name only a package or a listed dir, so both also name the linked-worktrees failure.
  - Reuse `canonicalize_for_comparison`, `_readlink_f`, `err`, `RELINK_FAILURES`, the `[relocate-claude-config]` stdout prefix, the `%q` print at `:854`, and the subshell-unit and bare-runner shape of `_relink_package` and `relink_packages`.
- **Create `claude/.claude/scripts/tests/test_relocate_claude_config_worktrees.py`**, with eight test functions and ten cases.
  - Fixture conventions, unless a case says otherwise:
    - fixture git runs as M5 says;
    - each case's checkout is a `_make_repo` checkout made a git repository with one commit;
    - its linked worktrees are added under `<checkout>/.claude/worktrees/`;
    - `TICKET-1` and `TICKET-2` name ticket directories.
  - Assertion conventions:
    - assertions read exit codes, `RELINK_FAILURES`, paths and file contents, never git's message wording, which is localized;
    - a path in output is compared as `str(path.resolve())`;
    - a script sentence is matched by a fixed phrase from it, such as `which does not exist` for the missing-record sentence.
  - "Links resolve in both directions" means two things:
    - `git rev-parse --git-common-dir` inside the worktree resolves to `<new-path>/.git`;
    - `git worktree list --porcelain` in the checkout prints the worktree's new path.
  - Whole-script cases set up as the existing whole-script success tests do. `[primary, repair]` means parametrized over both modes. Cases b and c take their destination and args from `_relocation_args_for_mode`.
    - a. `[primary, repair]`.
      - Setup:
        - its destination and args, built as `_build_real_skills_dir_failure` builds them (`test_relocate_claude_config.py:410-426`): `_AWKWARD_DESTINATION_NAME`, which holds a space, under `home` for primary, and under `tmp_path` with `--repair --allow-outside-home` for repair;
        - a plain, a locked, a dirty, a `TICKET-1/nested` and a `TICKET-2/nested` worktree, all added before the repair arm's rename, the last after the other `nested` (row12);
        - in the plain one, `sub/.git`, a file reading `gitdir: /nonexistent/gitdir`;
        - an unmoved linked worktree outside the checkout, whose name holds a space;
        - a one-entry `~/.claude/transcript-config-dirs` naming an empty directory outside the checkout.
      - Assertions:
        - the run exits 0;
        - every worktree's links resolve in both directions, the outside one's included;
        - the lock file, the uncommitted change and the `sub/.git` text survive;
        - exactly one stdout line holds `also reaches`;
        - that line names the outside worktree's path with its space escaped as `\ `;
        - the `repairing linked worktrees of` line shows the destination's space escaped as `\ `, the way `%q` prints it;
        - the `walking the dir on line 1` line comes before the `repairing linked worktrees of` line.
    - b. Primary mode.
      - Setup:
        - a directory under `.claude/worktrees/` that no record names, whose `.git` reads `gitdir: /nonexistent/gitdir` (`_break_worktree_git_link`);
        - a plain worktree;
        - a linked worktree outside the checkout, renamed away before the run.
      - Assertions:
        - the run exits 3;
        - stderr names the broken directory's path;
        - stderr holds the missing-record sentence for the renamed-away worktree's recorded path, so the read ran after the failed repair;
        - the failure line names `linked-worktrees`;
        - the last line is the `--repair` retry;
        - the plain worktree's links resolve;
        - after the test deletes the broken directory's `.git`, the printed retry line, run with `_run_printed_retry_line`, exits 0;
        - that retry's stdout has no `also reaches` line.
    - c. Primary mode.
      - Setup:
        - no `.claude/worktrees` directory;
        - two linked worktrees outside the checkout, both renamed away before the run, one of them locked;
        - a third outside worktree left in place.
      - Assertions:
        - the run exits 0;
        - stderr holds the missing-record sentence exactly twice, once naming the locked worktree's recorded path;
        - both renamed-away records under `<new-path>/.git/worktrees/` still exist;
        - the third worktree's links resolve in both directions;
        - stdout holds `Done.`;
        - stdout holds the manual steps' `worktree repair`.
  - Sourced cases call the runner through `_run_sourced` with `bare=True` after the test renames the checkout, as an out-of-band move would. Each asserts `returncode == 0` and `call_statuses == [0]`, because under `bare` a non-zero runner status ends the shell before its marker prints. A following step prints `RELINK_FAILURES`.
    - d. Setup: one worktree, and a prelude that exports `GIT_DIR` at a decoy repository holding a record with the same id as that worktree. Assertions:
      - `RELINK_FAILURES` stays empty;
      - the worktree's links resolve in both directions;
      - every decoy admin file is byte-identical.
    - e. Parametrized over the checkout's `.git`.
      - Parameters:
        - none, in a plain `_make_repo` checkout;
        - a `.git` file reading `gitdir: /nonexistent/gitdir`.
      - Assertions:
        - under each, `RELINK_FAILURES` stays empty;
        - under each, stdout has no `repairing linked worktrees` line;
        - under the file, stderr holds `no linked worktree was repaired`.
    - f. Setup: one plain worktree, and a prelude `git` function that fails every `worktree list` call and passes every other call to `command git`. Assertions:
      - `RELINK_FAILURES` holds `linked-worktrees`;
      - the plain worktree's `.git` text is unchanged, so the repair did not run after the failed first read.
    - g. Setup: the checkout, built and renamed inside another repository's work tree, holds a worktree `w`. The other repository records a worktree with the id `w` at an existing path. The test then replaces the checkout's `.git` with a directory holding only a valid `HEAD` file. Assertions:
      - `RELINK_FAILURES` holds `linked-worktrees`;
      - every admin file of the other repository is byte-identical;
      - stdout has no `also reaches` line.
    - h. Setup: one plain worktree, then, after the rename, a worktree added from the moved checkout at `.claude/worktrees/TICKET-1/a/b`, a third level the walk does not name. Assertions:
      - `RELINK_FAILURES` stays empty;
      - exactly one stdout line holds `also reaches`, and it names the third-level worktree's path, so the plain worktree's old recorded path, which does not exist, is not announced.
  - Reuse from `._relocate_helpers`: `_make_repo`, `_stow`, `_claude_shim`, `_run_script`, `_relocation_args_for_mode`, `_AWKWARD_DESTINATION_NAME`, `_last_nonempty_line`, `_run_printed_retry_line`, `_run_sourced` and `_SUBPROCESS_TIMEOUT_SECONDS`. Reuse `_clean_env` and `_break_worktree_git_link` from `.conftest`, and `init_git_repo` and `isolated_git_env` from `helpers`. Neither `_relocate_helpers.py` nor the conftest changes.
- **Modify `claude/.claude/scripts/tests/test_relocate_claude_config.py`.** Line 594's assertion changes as M4 says.
- **Modify `code-file-size-exceptions.toml`.** Add M5's row in sorted position, then run `test_exception_table_shape` for the canonical layout.
- **Modify `README.md`, § "Repo relocation".**
  - A new bullet after the listed-config-dir bullet (`:451-464`) and before the exit-3 bullet (`:465`), with these sub-bullets:
    - Both modes run `git worktree repair` in the checkout last, when its `.git` is a directory. It names each real directory holding a `.git` file at `<new-path>/.claude/worktrees/<name>` or `<new-path>/.claude/worktrees/<ticket>/<name>`, the two shapes this repo's branch-naming convention produces. So each of those worktrees and the checkout link to each other again, a locked or dirty one included. One nested deeper is reported as not repaired.
    - The same repair reaches every other existing linked worktree the checkout records, such as an unmoved one outside it. M6's sentence follows. To link one back to another checkout, run `git -C <other checkout> worktree repair <path>`.
    - A checkout whose `.git` is a symbolic link or not a directory is reported, and no worktree is repaired.
    - After the repair, the output names each linked worktree the checkout records at a path that does not exist, such as one outside the checkout that moved, one on an unmounted volume, or one deleted by hand. The run still exits 0, and nothing is pruned or deleted.
    - The run prints `repairing linked worktrees of <path>` before git runs. git reads every recorded worktree's path, so one on an unreachable mount can block it. Interrupt the run, make that mount reachable or unmount it, and recover as the listed-dir bullet's interrupted-run steps (`:459-461`) describe.
  - The exit-3 bullet (`:465`) names repairing the checkout's linked worktrees beside the other two causes. Its causes list gains `linked-worktrees`: an error git reports for a linked worktree or a failed listing, such as an ownership mismatch git reports or a `.git` directory git does not open as a repository.
  - The manual bullet at `:493` becomes the README form of M4's manual-steps bullet.
- **Modify `docs/scripts.md`.** At `:463`, "re-link `claude-skills` and re-point links in each config dir listed in `~/.claude/transcript-config-dirs`, and exit 3 when either fails" becomes a list of three that adds "run `git worktree repair` for the checkout's linked worktrees", with "when any of them fails".
- **Modify `CHANGELOG.md`.** Add a bullet under `## [Unreleased]` → `### Changed`, after the listed-config-dir bullet (`:115-125`). Line 113 stays as written (row23). Its sub-bullets:
  - Both modes run `git worktree repair` for the linked worktrees under `<checkout>/.claude/worktrees/`, one ticket directory deep included. The same run reaches every other existing linked worktree the checkout records.
  - M6's sentence.
  - A record whose path does not exist is reported, and the run still exits 0. Nothing is pruned or deleted.
  - A run that exited 0 before can exit 3 now, with `--repair` as the retry. That happens when git reports an error for a linked worktree or listing the checkout's worktrees fails.
  - **Migration:** run `./install.sh` before your next relocation, because `git pull` does not refresh the installed copy.
  - **Migration:** for linked worktrees a past relocation left unlinked, run `./install.sh` from the checkout, then `relocate-claude-config --repair [--allow-outside-home] <checkout path>`, with the flag when the first run passed it.

Projected diff: ~415 changed lines, additions plus deletions. By file: relocate script ~87, the new test file ~295, `README.md` ~18, `CHANGELOG.md` ~8, `code-file-size-exceptions.toml` 5, `test_relocate_claude_config.py` 2, `docs/scripts.md` 2. [unverified: this plan's estimates] That is below the ~425 the engineer chose to proceed with (row26). PR 1's script and tests ran about 1.7x and 2.6x over its projection (`.claude/plans/relocate-restow-secondary-accounts.md`'s `Projected diff:` line), so this figure is likely low. An overrun like PR 1's on the tests alone would pass ~425. The PR body gives the real figure from `git diff --numstat`.

## Verification

1. **Git probes.** Run each in a scratch repository under a fresh `mktemp -d`, with `GIT_CONFIG_GLOBAL=/dev/null` and `GIT_CONFIG_NOSYSTEM=1` set, and record `git --version` and each result in the PR body.
   - **The printed undo (M6), on the local git.** Copy a checkout that records an unmoved outside worktree, keep the original, and run the copy's `git worktree repair --`. When the outside worktree's `.git` then names the copy, run `git -C <original> worktree repair <path>` and check that both links resolve to the original again. When it still names the original, no re-point happened, the undo is not needed, and that is the result to record. An undo that fails goes back to this plan before the PR opens, because M6's line prints it.
   - **Rerun on git 2.43.** Rows 9-13 and 40-42 rest on probes run on git 2.56.0, row40's ceiling results included. When a git 2.43 binary is available locally, rerun them. When none is, the 2.43 floor stays unverified locally, and CI's pinned git 2.43.0 running the new test file, case g included, is the check (row8).
2. **Scoped suite:** `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py`. Stage the new test file and the table row first, because the size gate counts only paths in the index.
   - Every new case passes in both modes where parametrized, and every existing relocate test passes with only the line-594 edit.
   - `test_code_file_sizes` and `test_exception_table_shape` pass with the new row (row19, row25).
3. **Lint:** `scripts/list-shell-files.sh | xargs -0 scripts/venv-run.sh shellcheck` and `scripts/venv-run.sh ruff check claude/.claude/ claude-skills/ plugins/ evals/`.
4. **Mutation checks, reverted before commit.** Each names the case that must fail.
   - Drop the runner's `.git` checks: case e, no `.git`.
   - Drop only the symbolic-link-or-not-a-directory branch: case e, the `.git` file.
   - Drop the ceiling: case g.
   - Walk a third level, so a third-level worktree is named to git and not announced: case h.
   - Drop the variable `unset`: case d.
   - Glob one level only: case a, through its nested worktrees.
   - Look inside a candidate: case a, through `sub/.git`.
   - Call `git worktree repair` with no candidate paths: case a, in both modes.
   - Skip the repair call when there are no candidates: case c, through its unmoved worktree.
   - Drop the pre-repair line: case a.
   - Announce candidates too: case b, through its retry.
   - Announce outside-only records: case h.
   - Drop the existence test from the announcement: case h.
   - Print the destination or a record path raw instead of through `%q`: case a.
   - Call the runner before `relink_declared_dirs`: case a.
   - Stop a failed repair call from failing the unit: case b.
   - Drop the post-repair read, or skip it after a failed repair: case b.
   - Fail the unit on a missing record: case c.
   - Test `prunable` instead of `-e`: case c, through its locked record.
   - Insert a `git worktree prune` before the post-repair read: case c, whose records must survive.
   - Ignore both reads' failures: case f.
   - Run the repair after a failed first read: case f, through the unchanged `.git`.
   - Left unpinned:
     - The symbolic-link tests in the gate and in the candidate test. They guard shapes row18 declines.
     - The three names besides `GIT_DIR` on the `unset` line.
     - The ceiling's `/` value for a checkout whose parent is the root, which no test can place. [unverified: git's ceiling handling of a root entry, not run]
5. **Installed copy (engineer, after merge):** run `./install.sh` from the checkout, then `cmp ~/.claude/scripts/relocate-claude-config.sh ~/.local/bin/relocate-claude-config` exits 0 (G1).
6. **The real move is not part of this plan's verification.** The engineer runs it once this PR merges (Context).

## Out of scope

- **Pruning, deleting or unlocking any worktree or record** (row14). The closing text names the user's own options.
- **Keeping git's sweep off a recorded worktree the run does not name.** No documented option scopes it (row34), and the engineer chose disclosure plus a stdout line (row29). That includes a checkout copied rather than moved before `--repair`. There the sweep may re-point the original's unmoved outside worktrees to the copy, as it repaired the probe's unmoved outside worktree (row9), and Verification 1's undo probe settles whether it does. The stdout line names each one with its undo. A named worktree whose `.git` still names the original's record did not lead git to rewrite that record (row41).
- **Destination shapes `worktree-ensure.sh` never produces** (row18). A crafted destination that plants one already runs code through the stowed hooks (row17). They include:
  - another repository's worktree under `.claude/worktrees/`;
  - a symbolically linked `.claude/worktrees`.
- **A symbolic link under `.claude/worktrees/`, or a recorded worktree whose `.git` is one.** The walk names neither (M1), and the announcement names each recorded one before the repair (M6). git's sweep writes nothing through a symbolically linked `.git` (row42).
- **A worktree path holding a newline** (row6, row13). The listing splits it, the pieces are reported as missing, and the run still exits 0.
- **The eleven repository-local variables the unit does not unset** (row38).
- **A `:` in the checkout's parent path.** git splits `GIT_CEILING_DIRECTORIES` on `:`, so such a ceiling bounds nothing and git can still reach an ancestor repository when `.git` is invalid. [verified: probe on git 2.56.0, a parent path holding a colon, with and without a trailing slash] It needs a colon in the path, an invalid `.git`, and an ancestor repository together, so the plan accepts it.
- **Quoting git's own output.** git's `repair:` and `error:` lines print destination-controlled paths as they are, so a crafted name can still forge a line there. `%q` keeps only the script's own lines unambiguous. Quoting git's lines would mean capturing and rewriting git's output.
- **A count of candidates or of missing records.** No total is printed. A recorded worktree the walk misses is named before the repair when its recorded path exists (M6), or after it when that path does not (M2).
- **Relative worktree links** (`worktree.useRelativePaths`, `git-worktree.adoc:229-236`). They would let links survive a move with no repair. Adopting them changes every user's worktree link format, and which release added them is not checked.
- **A run-time git version check.** The 2.43 floor is checked at install only (row8), and this change adds no other check.
- **Marketplace registration for listed accounts (PR 2b) and the deferred EXIT-trap retry line.** Both stay as `.claude/plans/relocate-restow-secondary-accounts.md` § "Out of scope" records them.
- **Peer-owned files** (G4).
- **The earlier CHANGELOG relocate bullet** (row23).
