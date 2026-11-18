# Scope `--this-repo` by project-dir slug prefix so removed worktrees stay in

## Context

Goal: make `transcript-analysis --this-repo` include the project directories of this repo's removed worktrees, so own-repo figures stop under-counting, and make the resolved-scope header show how many matched directories are live worktrees versus removed ones.

Ask: GitHub issue #1202, "transcript-analysis --this-repo drops project dirs of removed worktrees, under-counting this repo". The engineer asked to move on to #1202's scoping pass with "I think move on to 1202's scoping pass. and you should probably do that in a new session", then answered "yes" to proceeding with `/plan-it`.

Why now: a worktree removed after its PR merges leaves its transcript project directory behind, and `_repo_scoped_project_slugs` in `scope.py` builds the scope from the live `git worktree list` only, so every `--this-repo` figure silently drops those directories. The issue reports 41 of 142 directories resolved on one account, which is unverified here because it needs the engineer's corpus.

Intended outcome: `--this-repo` admits a project directory when its name is a live worktree slug, or starts with the main checkout's slug plus `--claude-worktrees-`. The header prints matched directories split live versus unlisted. One matcher in `scope.py` replaces the private copies in `routing_guard.py` and `redaction.py`, and `skill_invocation.py` uses it too.

Every stow consumer is affected: the change is under `claude/.claude/scripts/transcript_analysis/`, which installs to every contributor.

The engineer's answers on the redaction exposure, the publication instruments and the review-round decisions are ledger rows 1, 2, 26, 29, 30, 31, 37, 38, 39, 40, 41 and 42. Each row quotes the label the engineer selected. Row 3 holds the fact that every `--this-repo` figure changes on purpose.

Evidence from the scoping pass, read directly by the session, not yet reviewed by the design author. Paths are under `claude/.claude/scripts/transcript_analysis/` unless noted.
- `scope.py:96-203` `_repo_scoped_project_slugs` runs `git worktree list --porcelain`, guards cwd containment and `git rev-parse --show-toplevel` identity, then returns `[_path_to_project_slug(p) for p in worktree_paths]`. Its docstring at :107-113 argues against a prefix glob.
- `scope.py:592-610` `_resolve_project_scope`'s `this_repo` branch caches the list on `args._this_repo_slugs`, runs a zero-match check against `--config-dir`, and returns the header label `this repo ({len(slugs)} project dirs)`.
- `scope.py:374-431` `_iter_scoped_sessions` admits a root's directory when `p.name in wanted`, one exact-name set per call, across every root.
- `routing_guard.py:84` defines `_WORKTREE_SLUG_INFIX = "--claude-worktrees-"`.
- `routing_guard.py:949-958` `_capture_scope` already adds orphan directories.
- It lists the root and keeps names that start with `slugs[0] + _WORKTREE_SLUG_INFIX`.
- It relies on `git worktree list` printing the main worktree first, which G3 records.
- `skill_invocation.py:110` calls `scope._iter_scoped_sessions(scope._repo_scoped_project_slugs(), ...)` directly, outside the cached path.
- `redaction.py:31` defines its own `_WORKTREE_SUFFIX_RE = re.compile(r"--claude-worktrees-.+$")` for `_project_family`.
- Readers of the cached `args._this_repo_slugs`: `cost.py:678` and `:1211`, `context_composition.py:346`, `context_distribution.py:99`. Row 7 holds the per-root fact about `pr_cost.py`.
- Tests pin the old header text. Critical files lists them and Verification step 1 names their node IDs. Plan documents under `.claude/plans/` also quote it and are preserved records, not edited.
- No `SKILL.md` quotes the `SOURCES (this repo` header (verified: `git grep` over `claude-skills/**/SKILL.md`, no match).
- Docs naming the old behavior: `docs/transcript-analysis.md` lines 50, 60, 68, 71, 73, 1496, 1842-1845 and 1895, and `docs/transcript-analysis-architecture.md:57-59`. The header examples at `docs/transcript-analysis.md:129, 516, 973, 1509` show the old header format.
- `scope.py` is 1,161 lines against the 1,000-line limit in `docs/design-decisions/code-file-line-limit.md`. That document says the check ships only after an offender assessment, and no pytest check or exception table for it exists in the repo (verified: no test file references it).
- Tests belong in the file named for their subject per `.claude/rules/transcript-analysis-tests.md`: scope behavior in `tests/test_transcript_scope.py`.

Open design points the architect settles:
- Whether the matcher lives in `scope.py` or a new module.
- How the root-independent matcher is cached so `pr_cost.py`'s per-root loop does not drop a root.
- Whether worktrees outside `.claude/worktrees/` need the exact-match rule kept. The session's read is yes, so a live worktree anywhere still matches.

Architect's earlier design for the plan to weigh, a proposal and not an engineer decision:
- One admission rule in `scope.py`: a directory is in scope if its name is a live worktree slug, or starts with the main slug plus the infix. Keep the exact-match rule alongside it.
- Cache a root-independent matcher, never a per-root slug list, so the second root in `pr_cost.py` and multi-root `--config-dir` runs are not silently dropped, and scanned counts agree with priced sessions.
- Move five places together:
  - `_resolve_project_scope`, for the zero-match check and the header.
  - `skill_invocation.py:110`.
  - `routing_guard._capture_scope`, dropping its private copy.
  - `_WORKTREE_SLUG_INFIX`, moved to `scope.py`.
  - `redaction.py:31`, referencing that constant.
- Edit these docs:
  - `transcript-analysis.md` :68 becomes the rule plus the remaining gap.
  - :71 "four gaps" becomes three.
  - :1496 loses its limit.
  - :1842-1845 loses the second lookup.
  - :1895 describes `--this-repo` as a whole.
  - The `scope.py:107-113` rationale is rewritten against prefix matching.
  - The sentence naming `cmd_<snake>` may ride along in `docs/transcript-analysis-architecture.md` as a labeled incidental edit.
- One PR for #1202, kept apart from #1157.

## Approach

`--this-repo` admits a project directory when its name is a live worktree's slug, or when it starts with the first listed worktree's slug plus `--claude-worktrees-` and is longer than that prefix. `scope.py` holds the one rule. `_iter_scoped_sessions` and `_scan_root_transcripts` build it from the live-slug list they already receive. Every `--this-repo` reader, `skill-invocation`'s default scope, the evals miner and `routing-guard --capture` therefore read removed worktrees' directories with no edit where they call it. The header label becomes `this repo (<N> project dirs: <L> live, <U> unlisted)`, counted on each call over that call's own roots.

**Every `--this-repo` figure changes on purpose (row 3).** The engineer accepted the widened disclosure gates, publication instruments and further consumers (rows 1, 2 and 26). The engineer also chose to leave the pre-clearance doc alone, to accept the lossy-slug residual and to keep the header split (rows 29-31). `pr-cost --record` keeps its refusal unchanged (row 22).

Line numbers are at the branch's HEAD before any edit. Modules are under `claude/.claude/scripts/transcript_analysis/`, tests under `claude/.claude/scripts/tests/`.

**The rule** (M1; rows 8, 9, 20, 35, 36), in `scope.py` after `_path_to_project_slug` (:85-93):
- `_WORKTREE_SLUG_INFIX = "--claude-worktrees-"` moves here from routing_guard.py:84. Its comment: "A linked worktree under `<main>/.claude/worktrees/` slugs to the main checkout's slug, this infix, then its directory name."
- `_RepoProjectDirMatcher(NamedTuple)` holds `live_slugs: frozenset[str]` and `worktrees_dir_prefix: str | None`.
  - `is_live(name)` is membership in `live_slugs`.
  - `admits(name)` is `is_live(name)`, or a non-None prefix that `name` starts with and is longer than.
  - Comparison is plain `str`, never `fnmatch` or `Path.glob`, for the metacharacter reason at :383-387.
- `_repo_project_dir_matcher(slugs: Sequence[str])` sets the prefix to `slugs[0] + _WORKTREE_SLUG_INFIX`, or to None when `slugs` is empty, so an empty list admits nothing. The prefix is never `""`, which would admit every directory. Its docstring: "`slugs[0]` is the first worktree `git worktree list` prints, as `_repo_scoped_project_slugs` returns it."
- `_repo_scoped_project_slugs` keeps its return value. Its docstring (:97-118) changes in four places:
  - It states that the first slug is the first worktree git lists: the main checkout, or a bare repository's directory (G3, row 36).
  - The minimization-control sentence (:99-104) names `_RepoProjectDirMatcher`, built from these slugs, as the control. It defers to docs/transcript-analysis.md "Scoping to this repo" for what the matcher admits, and drops "matched as exact dir names".
  - The argument against a prefix match (:107-110) becomes a pointer to `_RepoProjectDirMatcher` plus the residuals row 8 names.
  - The subdirectory exception (:110-113) narrows to the main checkout's subdirectories and to worktrees outside `<main>/.claude/worktrees/`. It says the documented prefix glob covers only the main checkout's subdirectories.
- `_add_project_scope_args` (:509-521) follows M8. Its docstring's "an identity-based minimization control" (:513) names `_RepoProjectDirMatcher` instead. The `--this-repo` help (:520) becomes "Scope to the project dirs of this repo's live worktrees, and of removed worktrees under the main checkout's .claude/worktrees/ (see docs/transcript-analysis.md for what else it admits)."

**Admission** (M2; rows 4, 5, 7):
- `_iter_scoped_sessions` (:374-431) builds the matcher once from `slugs` and filters :418 with `matcher.admits(p.name)`. Its docstring (:378-389) states the rule by reference to `_RepoProjectDirMatcher` and keeps the no-glob and dedup facts.
- `_scan_root_transcripts` (:811-867), when `slugs` is given, lists the root with `_list_dir_recording_gaps(root, None, _SCAN_GAP_ROOT)` and keeps the entries the matcher admits, in place of `root / slug` at :850. Its docstring (:831-841) follows. The per-root `scanned N transcripts` lines at cost.py:685, :1216, context_composition.py:351 and context_distribution.py:110 then count the same directories the report prices.
- `args._this_repo_slugs` stays the live-slug list. It depends on no root, so each of pr_cost.py's per-root calls applies the rule to its own root (row 7).

**Counts and header** (M3, M4; rows 3, 10, 18, 31, 32, 34):
- `_resolved_project_dir(candidate) -> Path | None` is extracted from `_dedup_new_project_dirs` (:261-264). It returns a directory's resolved path, and None for an absent entry or a non-directory. Any other `OSError` propagates. `_dedup_new_project_dirs` calls it and behaves as before.
- `_RepoProjectDirCounts(NamedTuple)` holds `live: int` and `unlisted: int`.
- `_repo_project_dir_counts(slugs, roots, *, scan_gaps=None)` lists each root with `_list_dir_recording_gaps(root, scan_gaps, _SCAN_GAP_ROOT)` and keeps the entries the matcher admits. Across all roots it counts each once per resolved path, as the iterator reads them (:270):
  - An entry `_resolved_project_dir` maps to None does not count.
  - An entry it raises on counts, keyed on its unresolved path, because the iterator records that entry as a `project-dir` gap or raises (row 18). The count never drops it silently.
  - A counted entry is `live` when `is_live(name)` holds, else `unlisted`.
- `_resolve_project_scope`'s `this_repo` branch (:592-610) calls it without `scan_gaps`, because the iterator records root gaps itself (:419-421).
  - Under `--config-dir`, `live + unlisted == 0` replaces the `any(... .is_dir())` check at :598.
  - The zero-match message names `len(slugs)` live worktree slugs and says the `.claude/worktrees/` prefix was checked too. It prints no slug, prefix or path, so it drops today's echo of the `--config-dir` value (:601, row 34).
  - The label is `f"this repo ({live + unlisted} project dirs: {live} live, {unlisted} unlisted)"`. It holds no `;`, because `_resolved_scope_header` (:676) separates its own clauses with one.
  - The docstring's multi-root paragraph (:558-562) and zero-match paragraph (:564-571) follow.
- "unlisted" counts every counted directory whose name no listed worktree has: a removed worktree's, and each over-inclusion row 8 names that git does not list.
- cost.py:703-708 is a comment only. Its clause "that count comes from `git worktree list` (this repo's own local worktrees), not account identity" gives way to two sentences. One says the count is listed from this account's project directories. The other says `--summary` never prints it.

**Routing guard** (M5; rows 13, 14, 20), in routing_guard.py:
- `_WORKTREE_SLUG_INFIX` (:84) is deleted.
- `_capture_scope` keeps :949-955. Lines :956-961 become one `scope._repo_project_dir_counts(slugs, [root], scan_gaps=scan_gaps)` call and a return of `_CaptureScope(slugs, counts.live + counts.unlisted)`. Passing `scan_gaps` keeps the root-gap record :957 makes today.
- The unlisted-branch refusal (:1349-1357) names one lookup: `review-trace` with the same top-level `--config-dir`, `--deny-only` and `--this-repo`. The clause "and, if no row matches that minute, once with --projects='<main-project-slug>…*' for a removed worktree's sessions" goes.

**Redaction** (M6; row 19), redaction.py:28-31: `_WORKTREE_SUFFIX_RE = re.compile(re.escape(scope._WORKTREE_SLUG_INFIX) + r".+$")`, with the comment above it citing `scope._WORKTREE_SLUG_INFIX`. `_project_family` behaves as before.

**Scope statements** (M8; rows 2, 8). skill_invocation.py changes text only, so that no statement calls its default scope "own worktrees only" or names `_repo_scoped_project_slugs` as the control:
- :31-34: the read covers this repo's admitted project dirs, which can include a foreign clone under its worktrees directory. `scope._RepoProjectDirMatcher` enforces the minimization upstream.
- The OUTPUT INVARIANT comment (:77-92) names `scope._RepoProjectDirMatcher` as the control and points to docs/transcript-analysis.md "Scoping to this repo" for what it admits.
- The `--projects` help (:268-269) says "Default: the --this-repo scope (see docs/transcript-analysis.md)" in place of "this repo's own worktrees only (publish-safe without --include-subagents)". The `--this-repo` help (:274-275) says the command already defaults to the `--this-repo` scope.

**Tests and docs** are listed under Critical files. In the docs, `docs/transcript-analysis.md:50` becomes the one home of the rule, the label and the count's definition, and every other site defers to it.

**Size.** scope.py grows by about 60 lines, and routing_guard.py stays above 2,000 (row 11). Both already exceed G4's cap, and splitting them is out of scope. The new scope tests go in `tests/test_transcript_scope_worktree_admission.py` from the start, because they would take test_transcript_scope.py past 1,000 lines (row 33). Its seam is the worktree-prefix admission and the header's live/unlisted counts. No existing class moves.

**Alternatives set aside:**
- Caching a matcher object on `args` in place of the slug list, the earlier design's proposal. The list already depends on no root (row 7), and the matcher is a pure function of it. Replacing the cache rewrites 31 seeding lines in 8 test files (row 5) for no change in behavior.
- Caching a per-root list of matched directory names. pr_cost.py's per-root loop would reuse the first root's list for the second (row 7).
- Passing a matcher into `_iter_scoped_sessions` and `_scan_root_transcripts` in place of `slugs`. It changes seven direct test calls (test_transcript_scope.py:432, :458; test_transcript_scope_scan.py:178, :336, :357, :424, :623) and evals/review_bench/mine_review_rounds.py:65 for no change in behavior. The first-listed contract is stated once, on `_repo_project_dir_matcher`.
- The prefix rule alone, without exact live names. It drops a live worktree outside `<main>/.claude/worktrees/`, which test_transcript_scope.py:250-262 pins at `/other/wt`.
- The main slug as a prefix with no infix. It admits a sibling `<repo>-fork` and every main-checkout subdirectory, the collision docs/transcript-analysis.md:67 names.
- Finding the main checkout through `git rev-parse --git-common-dir`. That adds a third subprocess for an order git already guarantees (G3).
- A new module for the rule, to keep scope.py from growing. Moving about 60 lines out leaves scope.py over G4's cap, and a new module needs its own test file and architecture-doc section.
- Labeling the second count `removed`. The matcher knows only that git lists no worktree by that name, and row 8's subdirectory sessions, nested worktrees and foreign clones are not removed worktrees.
- Counting distinct names across roots. The iterator reads one directory per resolved path (:270), so one name can be two directories read, and a symlinked alias is two names for one directory.
- Counting with `Path.is_dir()`, the predicate of the :598 check. It drops an existing directory whose stat fails, which the iterator records as a gap (row 18).
- Documenting the `--projects` glob fallback only. Every `--this-repo` figure would keep under-counting.

**Assumption ledger.**

**Root:** `--this-repo`, `skill-invocation`'s default scope, the evals miner and the per-root scan lines admit a project directory only when its name equals a live worktree's slug (scope.py:418, :598, :850). A removed worktree's directory, which Claude Code leaves behind (G2), therefore drops out of every own-repo figure. Routing-guard capture admits it through a private copy of the rule (routing_guard.py:956-958). redaction.py:31 holds another copy of the slug infix. `[verified: read]`

**Givens:**
- G1. Claude Code names a project directory by replacing every `/` and `.` in the session's startup cwd with `-`. Reason: Claude Code owns the naming. `[verified: scope.py:85-93; test_transcript_scope.py:389-404]`
- G2. Claude Code leaves a removed worktree's project directory in place, and git no longer lists the worktree. Reason: Claude Code owns its project directories and git owns the worktree list. `[unverified]`: docs/transcript-analysis.md:68 states it, and #1202 rests on it. No corpus was checked this session, and Verification step 3 checks one. routing_guard.py:956-958 and its test at test_transcript_routing_guard_capture.py:2386 already handle the case.
- G3. `git worktree list` prints the main worktree first. Reason: git imposes the order. `[verified: git-worktree(1), /Library/Developer/CommandLineTools/usr/share/man/man1/git-worktree.1:159, "The main worktree is listed first, followed by each of the linked worktrees."; the session saw the same order in this checkout's porcelain output]`
- G4. Code and test files are capped at 1,000 lines, and nothing enforces the cap until an offender assessment exists. Reason: `docs/design-decisions/code-file-line-limit.md` owns the cap. `[verified: :19-21, :50-57]`
- G5. Agents run `select-tests.py`, not the full suite. Reason: the repo `CLAUDE.md` § "Commands" owns the rule. `[verified: CLAUDE.md]`
- G6. A test goes in the file named for its subject, and a file that would cross the cap splits at a named seam. Reason: `.claude/rules/transcript-analysis-tests.md` owns placement. `[verified: read]`

**Rows:**
1. The engineer accepts the redaction exposure. `[engineer-verified: "Accept (Recommended)"]`, the label selected when asked whether to accept three effects of widening `--this-repo`. They are the widened raw-branch-printing gate (subagent_mix.py:251, review_rounds.py:1439), the widened `cost --summary` (cost.py:547), and admitting a foreign repo cloned under `<main>/.claude/worktrees/`. The tag covers only those three.
2. The engineer accepts the wider scope for four more publication instruments that read `--this-repo`. They are `cost-counts --this-repo` (`pr-cost-section.sh`'s second block), `review-cost-by-size --this-repo`, `read-cost --this-repo`, and `skill-invocation`'s default scope. `[engineer-verified: "Accept all four (Recommended)"]`, the label selected when asked whether to accept the wider scope for those four, given that `docs/private-project-redaction.md:154-155` makes a diff that widens that scope a P1 finding. The tag covers only those four.
3. Every `--this-repo` figure changes. Removed worktrees' sessions enter the totals. The label's count changes from `len(slugs)` (scope.py:609) to admitted directories present, once per resolved path. `[verified: read of scope.py:592-610]`
4. Admission reaches its consumers only through the two scope.py functions. `[verified: Grep over the repository, plans excluded, for "_repo_scoped_project_slugs|_iter_scoped_sessions\(|_scan_root_transcripts\("; Grep under transcript_analysis/ for "_resolve_project_scope(" and "_this_repo_slugs"]`
   - 45 `_resolve_project_scope` call sites in 34 modules, `skill_invocation.py:110`, `routing_guard.py:1166` and `evals/review_bench/mine_review_rounds.py:65` reach it through `_iter_scoped_sessions`.
   - The four `_this_repo_slugs` readers (cost.py:678, :1211, context_composition.py:346, context_distribution.py:99) reach it through `_scan_root_transcripts`.
   - `pr-cost-section.sh:38, :46`, `skill-fidelity-report.sh:16, :23` and the skills that run `--this-repo` commands reach it through those same CLI paths.
5. 31 lines in 8 test files seed `args._this_repo_slugs` with a list. Keeping the cache a list keeps them valid. `[verified: Grep]`
6. No existing test expects a `<first-slug>--claude-worktrees-<x>` directory to be excluded under `--this-repo`. `[verified: Grep for "claude-worktrees" under tests/ and evals/]`
   - The hits in test_transcript_buckets.py:76-161, test_transcript_cost.py:1389-1409, test_transcript_user_input.py:382, :422 and test_transcript_corpus.py:225-231 run without `--this-repo`.
   - test_transcript_skill_invocation.py:599-632 lists that directory as a live worktree.
   - test_transcript_routing_guard_capture.py:2386 expects the directory to be read.
   - evals/ has no hit.
7. pr_cost.py calls `_resolve_project_scope` with `roots=[root]`, at :493 and once per root at :767-774, on one `args`. Anything cached on `args` must not depend on a root. `[verified: read]`
8. The prefix rule admits more than removed worktrees. Each counts as unlisted unless git lists it. `[verified: scope.py:93's transform, applied by hand]`
   - A session started in a subdirectory of a linked worktree under `<main>/.claude/worktrees/`, live or removed.
   - A worktree nested in a linked worktree's own `.claude/worktrees/`, such as `-repo-main--claude-worktrees-live--claude-worktrees-x`. Its name extends an in-tree slug with the infix, so it starts with the prefix.
   - A foreign repo cloned under `<main>/.claude/worktrees/`, row 1's accepted exposure.
   - Any path whose slug happens to start with the prefix, such as a sibling directory named `<repo>--claude-worktrees-x`. This is the lossy-slug residual row 30 accepts, which test_transcript_scope.py:463-495 already pins for exact names.

   It does not admit a sibling `<repo>-fork`, the bare `<main-slug>--claude-worktrees-`, a main-checkout subdirectory, or a live slug outside `<main>/.claude/worktrees/` extended with the infix.
9. A removed worktree that lived outside `<main>/.claude/worktrees/` stays excluded. Once git stops listing it, nothing in its slug ties it to this repo. `[verified: scope.py:93]`
10. Every run now reads every removed worktree's sessions. Their directories stay (G2), so read time grows with their number. That growth is the Ask's own effect. Counting adds one directory listing per root per `_resolve_project_scope` call, also at the call sites that discard the label (pr_cost.py:493, subagent_mix.py:530, cost_ledger.py). cost_ledger.py makes the most calls in one run, four. `[verified: cost_ledger.py:505 calls _print_cost_ledger_read, which calls _resolve_project_scope at :377; the same report calls it at :606, :615 and :616; Grep for "_resolve_project_scope(" finds no other command with more than two]`. Neither cost is measured. The PR description carries one sentence: read time now grows with the number of removed worktrees' directories.
11. Line counts: scope.py 1,161, routing_guard.py 2,115, redaction.py 303, test_transcript_scope.py 899, test_transcript_scope_scan.py 773, test_transcript_skill_invocation.py 662, test_transcript_cost_counts.py 847. `[verified: Grep line counts]`
12. `docs/transcript-analysis-architecture.md:46-47` says scope.py owns "the `--this-repo` project-slug machinery", which stays true. Its :797-800 records where scope.py's tests live, so it names the new file. No `cmd_<snake>` sentence exists there for the earlier design's incidental edit. `[verified: Grep; read of :44-60, :792-803]`
13. The refusal's second lookup (routing_guard.py:1349-1357) and docs/transcript-analysis.md:1838-1847 exist only because `--this-repo` skipped removed worktrees. After the change, capture (routing_guard.py:1166) and `review-trace --this-repo` under the same top-level `--config-dir`, which resolves to that one root (scope.py:493-495), admit the same directories. `[verified: read]`
14. Two tests pin the refusal's `--projects` form: test_transcript_routing_guard_compute.py:1931-1962 (the `projects-glob` parameter) and test_transcript_routing_guard_capture.py:2104-2108 (the `"--projects="` token). Each gains an assertion that fails until M5 lands. `[verified: Grep]`
15. Seven tests pin the old label through production code. Critical files lists their edits, and Verification step 1 their node IDs. test_transcript_scope.py:851-852 passes the label to `_resolved_scope_header` as a literal, so it pins no label and stays unedited. test_transcript_review_cost_by_size.py:801-811 compares the docs sample at docs/transcript-analysis.md:1509 with a real header, every figure masked, so that sample changes with the label. `[verified: Grep for "project dirs\)"; read of test_transcript_review_cost_by_size.py:103-126, :801-811]`
16. `require-diff-size-prompt.sh` gates a branch diff of 400 or more changed lines outside `.claude/plans/`. `[unverified]`, carried from `.claude/plans/cli-registrar-flag-sweep.md` G4 and not re-read.
17. docs/case-studies/handoff-signal-response.md:21, docs/cost-levers-considered.md:663 and plan files under `.claude/plans/` quote old header counts from dated runs. They are preserved records. `[verified: read]`
18. The count reuses the stat-and-resolve step `_dedup_new_project_dirs` applies (scope.py:259-269). That step reads an absent entry or a non-directory as absent, and any other `OSError` as a gap or a raise. Counting with it agrees with what the iterator reads or records. `[verified: read of scope.py:219-273]`
19. The `.claude/worktrees/` matchers in reviewer_yield.py:277-282 and period_cost.py:193 work on absolute paths, not project-directory slugs, so they are not copies of this rule. `[verified: Grep for "claude-worktrees|claude/worktrees" under claude/.claude/scripts/]`
20. routing_guard.py:958 excludes a name equal to the bare prefix (`entry.name != orphan_prefix`). `admits`' length check keeps that behavior. `[verified: read]`
21. The Context's earlier design is a proposal, not an engineer decision. This plan departs from it in two places. It caches the slug list rather than a matcher, and its architecture-doc edit names a test file instead of the `cmd_<snake>` sentence (row 12). `[verified: plan Context]`
22. `pr-cost --record`, the one instrument in docs/private-project-redaction.md:110-135 that neither row 1 nor row 2 names, reads `--this-repo` only when the caller passes it (pr_cost.py:1199 registers the flag). Its refusal (:114-118) counts resolved roots, and this change filters directories inside a root without changing which roots resolve. Its `--this-repo` figures widen under row 3. A foreign clone enters them under row 1. `[verified: read of pr_cost.py:767-774, :1199; docs/private-project-redaction.md:114-118]`
23. The routing-guard consolidation (M5, deleting its private copy of the rule and the refusal's second lookup, with the two routing-guard tests and docs :1838-1847) belongs in this PR. `[engineer-verified: "Keep in this PR (Recommended)"]`, the label selected when asked whether to keep that consolidation beyond the Ask in this PR. The tag covers only that.
24. The redaction.py:31 regex built from `scope._WORKTREE_SLUG_INFIX` (M6) and the cost.py:703-708 comment edit belong in this PR. `[engineer-verified: "Keep both (Recommended)"]`, the label selected when asked whether to keep those two small edits. The tag covers only those two.
25. The Ask line's first quote is the engineer's own wording. `[engineer-verified: "Yes, my words"]`, the label selected when asked whether the quoted wording was theirs. The tag covers only that.
26. The engineer accepts the widened scope for three more consumers as intended: the raw-branch gate at subagents.py:182 (`disclose=this_repo and key in main_thread_branches`), the benchmark miner at `evals/review_bench/mine_review_rounds.py:64-65`, and `skill-fidelity-report.sh:16, :23`. `[engineer-verified: "Accept all, record it (Recommended)"]`, the label selected when asked how to treat those three consumers of the widened scope. The tag covers only those three.
27. A search for every `this_repo`-keyed disclosure gate finds four. Rows 1 and 26 cover subagent_mix.py:251, review_rounds.py:1439 and subagents.py:182. `[verified: Grep for "disclose\s*=|this_repo and|if .*this_repo\b" over every non-test .py file in the repository]`
   - The fourth, subagent_mix.py:263, discloses an agent-type name only when `redaction._repo_tracked_agent_type_names()` lists it. A newly admitted directory therefore discloses no name outside that allowlist.
   - `cost-counts` applies the same allowlist unconditionally (subagent_mix.py:450-479), and the new cost-counts test pins it on an unlisted directory.
   - The package's other `this_repo` reads (cost.py:547, read_cost.py:398, review_cost_by_size.py:320, subagent_mix.py:510, review_rounds.py:834) are refusals, which this change leaves alone.
28. `skill-fidelity-report.sh` keys both of its reports on the current branch name (:6, :16, :23). A removed worktree's sessions on an earlier branch of the same name now join that evidence, so the fidelity reviewer can see a dispatch from the earlier branch. The main checkout's earlier sessions on that name already joined it. The PR description states this caveat. `[verified: read of skill-fidelity-report.sh]`; how the fidelity reviewer reads the report is the backend review's account, not re-read.
29. `docs/private-project-redaction.md` stays unchanged. `[engineer-verified: "Leave the doc alone"]`, the label selected when asked whether to add a sentence to its :139-155 pre-clearance naming the accepted foreign-clone residual. The tag covers only that.
   - The PR description therefore states the residual: a foreign repo cloned under `<main>/.claude/worktrees/` now enters both `pr-cost-section.sh` blocks and the other publication instruments.
   - It also states that routing-guard capture's earlier read of such a clone sets no precedent for publication, because capture's output carries a DO NOT PUBLISH banner (routing_guard.py:91-98).
30. No recorded-`cwd` check guards prefix-only admission, so row 8's lossy-slug lookalikes stay admitted. `[engineer-verified: "Accept the residual (Recommended)"]`, the label selected when asked whether to add that check or accept the lossy-slug residual. The tag covers only that.
31. The `read-cost` and `review-cost-by-size` headers keep the split. `[engineer-verified: "Keep the split (Recommended)"]`, the label selected when asked whether those two headers keep the live/removed split. The tag covers only keeping the split.
32. The split puts a new figure in those two publication instruments' headers: counts of this repo's project directories on the active account, which both commands read alone (docs/private-project-redaction.md:124-135). It passes the check in `docs/private-project-redaction.md` § "New figures against the grandfathered set" (:304-319). `[verified: read of :97-166, :304-348; Grep for "project dirs|project directories|project-dir" over docs/case-studies/, docs/case-studies.md and docs/cost-levers-considered.md]`
   - That check asks whether a new figure lets a reader subtract it from a figure Remediation lists (:321-348) down to a non-this-repo remainder.
   - One listed document holds a project-dir count, cost-levers-considered.md:663's `118 project dirs`. That count came from the old label, which counted listed worktrees and no root, so a per-account directory count subtracts from nothing there.
33. The new scope tests run about 215 lines, which would take test_transcript_scope.py (row 11) past G4's cap. They therefore go in their own file (G4, G6). `[verified: read]`
   - `TEST_FILES` in test_transcript_package_module_prefixes.py:61-142 must list the new file. That file's test fails on a test file that imports `transcript_analysis` and is missing from the list (:6-9).
   - The module docstrings at test_transcript_scope.py:1 and test_transcript_scope_scan.py:1 say where scope.py's other tests live, and docs/transcript-analysis-architecture.md:797-800 records it too.
34. The zero-match message (scope.py:599-605) echoes the `--config-dir` value. No test pins its text beyond `--config-dir` and the subcommand name (test_transcript_cli.py:94-96). `[verified: Grep for "matched zero project directories|candidate worktree"; read]`
35. `_repo_scoped_project_slugs` never returns an empty list (scope.py:146-151), but a seeded `args._this_repo_slugs` or a direct caller can pass one. Today an empty list reads nothing at :418 and :850. `[verified: read]`
36. In a bare-repository layout, git lists the bare repository first, so the prefix comes from the bare directory's slug. A removed worktree outside `<bare>/.claude/worktrees/` then stays excluded, as row 9 says. `[verified: git-worktree(1), /Library/Developer/CommandLineTools/usr/share/man/man1/git-worktree.1:517, whose list example prints "/path/to/bare-source (bare)" first, and :593-594, whose porcelain example opens with "worktree /path/to/bare-source" then "bare"]`. The `bare-first` test stub copies that porcelain shape.
37. The plan proceeds as one PR at its projected size. `[engineer-verified: "Proceed anyway"]`, the option selected when asked whether to split a plan projecting about 590 changed lines, past the 400-line threshold, or proceed. The tag covers only that.
38. The header's second count is worded "unlisted". `[engineer-verified: "unlisted (Recommended)"]`, the label selected when asked which word to use. The tag covers only the word.
39. The added files beyond issue #1202's ask stay in this PR: the new scope test file with its `TEST_FILES` and architecture-doc companion edits, the stale "publish-safe" and "own worktrees only" text in `skill_invocation.py` and `scope.py`, and docs sections :454, :1800 and :2395. `[engineer-verified: "Keep all in this PR (Recommended)"]`, the label selected when asked whether to keep those files in this PR. The tag covers only that.
40. `CHANGELOG.md` gains one `[Unreleased]` > `### Changed` entry with a "What moves" clause. `tests/conftest.py` gains the shared git-listing stub. Both files were added after approval, on code-review round 1's findings. `[engineer-verified: "CHANGELOG.md (Recommended)"]` and `[engineer-verified: "tests/conftest.py (Recommended)"]`, the labels selected when asked whether to add each file to this PR. The tags cover only the two additions.
41. `claude/.claude/scripts/tests/test_transcript_shared_fixtures.py` gains a unit test of the shared git-listing stub, as `.claude/rules/transcript-analysis-tests.md:28-30` requires for a helper in conftest.py. `[engineer-verified: "Add the test (Recommended)"]`, the label selected when asked whether to add that test file. The tag covers only that addition.
42. The plan proceeds as one PR at its projected size of about 720 changed lines. `[engineer-verified: "Proceed anyway"]`, the option selected when asked again, at about 720 lines, whether to split or proceed. The tag covers only that.

**Mechanisms:**
- M1: the rule in scope.py. `anchors: root, G1, G3, row8, row9, row20, row30, row35, row36`. Lighter primitives checked:
  - A bare `(name, slugs) -> bool` predicate rebuilds the live set for every entry and gives the header no live/unlisted split.
  - An `fnmatch` pattern `<main-slug>--claude-worktrees-*` widens on a metacharacter in the slug (scope.py:383-387; test_transcript_skill_invocation.py:594-597).
- M2: `_iter_scoped_sessions` and `_scan_root_transcripts` build the matcher from the `slugs` they already take. `anchors: root, row4, row5, row7`.
- M3: `_repo_project_dir_counts` serves the header, the `--config-dir` zero-match check and capture's progress total. `anchors: root, row3, row10, row18, row34`. Lighter primitives checked:
  - `Path.is_dir()` per admitted name drops a stat failure the iterator records (row 18).
  - A count of distinct names disagrees with the directories the iterator reads (scope.py:270).
- M4: the label format. `anchors: row3, row15, row31, row32`.
- M5: routing_guard.py drops its copy of the rule and the second lookup. `anchors: root, row13, row14, row20`.
- M6: redaction.py's regex built from the shared constant. `anchors: root, row19`.
- M7: one `code-writer` dispatch. `anchors: row4, row11, row16, row33`.
- M8: skill_invocation.py's scope statements and scope.py's flag help point to the rule's home. `anchors: row2, row8`.

## Critical files

**Dispatch: one `code-writer`, no split** (M7). The tests and docs depend on the label and the helper names the scope.py edit sets, and the routing-guard edit calls the new helper. A split would restate the same background in every brief. The brief requires:
- Verification steps 1 and 2. The return carries each run's summary line, every failing node ID with its failure kind, and the failing IDs under each of step 2's mutations.
- The test placement under **Size** in the Approach.
- Tests that call only functions existing before the change and spell `--claude-worktrees-` as a literal, so step 1 fails on behavior, never on an import or a missing attribute.
- Placeholders or illustrative figures only, never a figure from a real corpus, in any test, doc or return.
- No staging and no commits.

**Modify, production.** Every stow consumer runs these after `git pull`.
- `claude/.claude/scripts/transcript_analysis/scope.py`: M1-M4, and M8's flag help.
- `claude/.claude/scripts/transcript_analysis/routing_guard.py`: M5.
- `claude/.claude/scripts/transcript_analysis/redaction.py`: M6.
- `claude/.claude/scripts/transcript_analysis/skill_invocation.py`: M8, text only.
- `claude/.claude/scripts/transcript_analysis/cost.py`: the comment at :703-708 only.

**New, test:** `claude/.claude/scripts/tests/test_transcript_scope_worktree_admission.py`. Its one-line module docstring names its seam: scope.py's `--this-repo` worktree-prefix admission and the resolved-scope header's live/unlisted counts. One helper writes one session per named directory, with the directory name as its branch.
- `TestThisRepoAdmitsUnlistedWorktreeDirs`:
  - `test_prefix_admits_unlisted_worktree_dirs_and_rejects_near_misses`. The slugs are `["-repo-main", "-repo-main--claude-worktrees-live", "-elsewhere-wt"]`. The root holds those three, then `-repo-main--claude-worktrees-gone`, `-repo-main--claude-worktrees-live--claude-worktrees-nested`, `-repo-main--claude-worktrees-`, `-repo-main-fork`, `-elsewhere-wt--claude-worktrees-x` and `-home-user-unrelated`. `_iter_scoped_sessions` reads exactly the first five.
  - `test_a_glob_metacharacter_in_the_main_slug_is_matched_literally`. With slugs `["-r*-main"]`, `-r*-main--claude-worktrees-y` is read and `-rX-main--claude-worktrees-y` is not.
  - `test_empty_slugs_admit_nothing`. Over a root holding `-repo-main--claude-worktrees-gone` and `--claude-worktrees-x`, `_iter_scoped_sessions` reads nothing and `_scan_root_transcripts(root, "*", slugs=[])` returns `(0, 0)`. A `_resolve_project_scope` call seeded with `[]` labels `this repo (0 project dirs: 0 live, 0 unlisted)`.
  - `test_one_args_reused_across_per_root_calls_reads_each_roots_unlisted_dir`. One `args` seeded with `_this_repo_slugs=["-repo-main"]` goes to `_resolve_project_scope(args, "pr-cost", roots=[root_a])`, then to the same call with `roots=[root_b]`. Only root_b holds `-repo-main--claude-worktrees-gone`. The second call yields that session and labels `this repo (1 project dirs: 0 live, 1 unlisted)`.
  - `test_unseeded_scope_takes_the_prefix_from_the_first_listed_worktree`, with git stubbed by the shared `_stub_git_worktree_listing` helper, in two cases:
    - `linked-cwd`: git lists `/repo/main`, then `/repo/main/.claude/worktrees/live`, and cwd and `--show-toplevel` are the linked one. A root holding `-repo-main`, `-repo-main--claude-worktrees-live`, `-repo-main--claude-worktrees-gone` and `-home-user-unrelated` reads the first three, labelled `3 project dirs: 2 live, 1 unlisted`.
    - `bare-first`: git lists `/srv/app.git` with a `bare` line, then `/srv/wt/live`, which holds cwd. The porcelain is hand-written, because `_worktree_porcelain` (conftest.py:1511) prints HEAD and branch lines for every path. `-srv-app-git--claude-worktrees-gone` is read and `-srv-wt-live--claude-worktrees-x` is not (row 36).
  - `test_lookalike_sibling_and_foreign_clone_dirs_are_admitted_as_an_accepted_residual`. With slugs `["-repo-main"]`, the root holds two directories, each with one session:
    - `-repo-main--claude-worktrees-x`, whose record carries `"cwd": "/repo/main--claude-worktrees-x"`, a sibling directory beside the main checkout.
    - `-repo-main--claude-worktrees-clone`, whose record carries branch `foreign-clone`, a foreign repo cloned under the worktrees directory.

    `_iter_scoped_sessions` reads both. The docstring takes test_transcript_scope.py:466-473's form: it names both cases as a known, accepted residual risk of prefix admission, and says a change that alters that posture in either direction must fail this test. The docstring cites no plan row. This is the test that pins row 30's residual.
- `TestThisRepoProjectDirCounts`:
  - `test_a_live_linked_worktree_dir_counts_live_once_and_never_unlisted`. The slugs are `["-repo-main", "-repo-main--claude-worktrees-live", "-repo-main--claude-worktrees-nodir"]`. The root holds the first two and `-repo-main--claude-worktrees-gone`. The label is `this repo (3 project dirs: 2 live, 1 unlisted)`.
  - `test_counts_follow_resolved_paths_across_roots`. The slugs are `["-repo-main"]`. root_a holds `-repo-main` and `-repo-main--claude-worktrees-gone`, root_b holds `-repo-main--claude-worktrees-gone` and `-repo-main--claude-worktrees-other`, and a third root is a symlink to root_a. Four sessions are read, and the label is `this repo (4 project dirs: 1 live, 3 unlisted)`.
  - `test_scan_count_session_count_and_header_agree`. One root holds `-repo-main`, `-repo-main--claude-worktrees-gone`, the bare prefix and `-repo-main-fork`, each with one transcript. It also holds a regular file named `-repo-main--claude-worktrees-file` and a symlink `-repo-main--claude-worktrees-alias` to the `gone` directory. With slugs `["-repo-main"]`, `_scan_root_transcripts(...)[0]`, the sessions `_iter_scoped_sessions` yields and the label's total all equal 2.
  - `test_an_unreadable_admitted_dir_counts_and_the_read_records_its_gap`, skipped under root as at test_transcript_scope_scan.py:19. A root with read but not search permission holds `-repo-main--claude-worktrees-gone`. The label counts it as unlisted, and the iterator records one `project-dir` gap in the `scan_gaps` passed to `_resolve_project_scope`.
  - `test_config_dir_with_only_near_miss_dirs_exits_1_naming_counts_only`. With `config_dir` set and slugs `["-repo-main", "-elsewhere-wt"]`, a root holding only `-repo-main-fork`, `-repo-main--claude-worktrees-` and `-elsewhere-wt--claude-worktrees-x` exits 1. Stderr names the two live slugs checked, by count, and holds no slug and no path.
  - `test_config_dir_with_only_an_unlisted_dir_reads_it`. With `config_dir` set, a root holding only `-repo-main--claude-worktrees-gone` yields its session and labels `this repo (1 project dirs: 0 live, 1 unlisted)`.

**Modify, test.**
- `claude/.claude/scripts/tests/test_transcript_scope.py`: :380 and :562 take `1 project dirs: 1 live, 0 unlisted`. Its module docstring (:1) names both sibling files. :851-852 stays as it is (row 15).
- `claude/.claude/scripts/tests/test_transcript_scope_scan.py:1`: "test_transcript_scope.py holds scope.py's other tests" becomes a pointer to test_transcript_scope.py's docstring.
- `claude/.claude/scripts/tests/test_transcript_package_module_prefixes.py`: `TEST_FILES` (:61-142) lists the new file after :136.
- `claude/.claude/scripts/tests/test_transcript_cli.py:325`, `claude/.claude/scripts/tests/test_transcript_cost.py:620` and `claude/.claude/scripts/tests/test_transcript_read_cost_command.py:78`: `1 project dirs: 1 live, 0 unlisted`.
- `claude/.claude/scripts/tests/test_transcript_review_cost_by_size.py:29-30`: `_HEADER_ACTIVE_ACCOUNT` takes `1 project dirs: 1 live, 0 unlisted`. `_HEADER_EVERY_ACCOUNT` takes `2 project dirs: 2 live, 0 unlisted`, because `_two_root_corpus` (:441-463) puts `_PROJECT_SLUG` under both roots.
- `claude/.claude/scripts/tests/test_transcript_skill_invocation.py`: `TestSkillInvocationRepoScope` gains `test_a_removed_worktree_dir_is_in_default_scope_and_a_fork_is_not` after :632, with the shared `_stub_git_worktree_listing` helper. `-repo--claude-worktrees-gone` holds one skill, which appears, and `-repo-fork` holds another, which does not.
- `claude/.claude/scripts/tests/test_transcript_cost_counts.py`: `TestCostCounts` gains `test_an_untracked_agent_type_in_an_unlisted_worktree_dir_is_withheld` after :662, built like :648-662. The untracked spawn sits only in `-home-user-testrepo--claude-worktrees-foreign` beside `fake_projects`. The output holds the withheld row and not the untracked name.
- `claude/.claude/scripts/tests/test_transcript_routing_guard_compute.py:1931-1962`: the `projects-glob` parameter goes. The test asserts that the remedy holds `--this-repo` and no word starting `--projects`, and that it still parses through `build_parser()`. `_SLUG_PLACEHOLDER` and `_A_MAIN_CHECKOUT` (:1919-1920) go if nothing else reads them.
- `claude/.claude/scripts/tests/test_transcript_routing_guard_capture.py`:
  - :2104-2108: `"--projects="` leaves the load-bearing tokens, and an assertion that `--projects` is absent from `outcome.err` follows.
  - :2386-2398: a directory named for the main checkout's own slug, with one session, joins the orphan test. It is the count's live term, and the orphan is its unlisted term. The test then asserts `scanning project directory 1 of 2`. A capture count that dropped either term would print `1 of 1` (routing_guard.py:1169).

**Modify, docs:** `docs/transcript-analysis.md`.
- :50 replaces "It resolves *this checkout's* worktrees by identity — … — the same minimization control …" with the rule's one home:
  - The rule: a live worktree's exact slug, or a name that starts with the first listed worktree's slug plus `--claude-worktrees-` and is longer than that prefix. The first listed worktree is the main checkout, or the bare repository in a bare layout. `skill-invocation`'s default scope and `routing-guard --capture` share the rule.
  - The label `this repo (<N> project dirs: <L> live, <U> unlisted)`. A directory is unlisted when no `git worktree list` entry has that name. `<N>` counts admitted directories present across the scanned roots, once per resolved path, so one worktree's directory under two accounts counts twice. An admitted directory that exists but cannot be read still counts.
  - `<L>` counts directories named for a worktree `git worktree list` prints, including one whose checkout is gone but not yet pruned. A live worktree with no session yet adds nothing. `<U>` counts the unlisted ones: removed worktrees' directories and the over-inclusions under :60 and :61.
- :56 gains one sentence after its single-account caveat: the over-inclusions under :60, a repo cloned under `<main>/.claude/worktrees/` among them, contribute their branch strings to `--this-repo` output too.
- :60 adds two over-inclusions:
  - A repo cloned under `<main>/.claude/worktrees/` is read as this repo's and counts as unlisted. `cost --summary` counts it under its `this repository only` caption.
  - A path whose slug starts with the prefix, such as a sibling directory named `<repo>--claude-worktrees-x`, is admitted too (row 30).
- :61 drops "`--this-repo`'s exact-identity match excludes it" and states three cases:
  - A session started in a subdirectory of a linked worktree under `<main>/.claude/worktrees/`, and a worktree nested in a linked worktree's own `.claude/worktrees/`, now match. Each counts as unlisted unless git lists it.
  - A session started in a main-checkout subdirectory is still excluded. The `--git-common-dir` glob covers it, because that glob starts with the main checkout's slug.
  - A session started in a subdirectory of a worktree outside `<main>/.claude/worktrees/` is still excluded, and no prefix route reaches it. The only route is an explicit `--projects` glob built from that worktree's own path slug.
- :68 becomes the remaining gap: a removed worktree that lived outside `<main>/.claude/worktrees/`, in a bare layout too (row 36). It says no prefix route reaches that directory, as :60 says "There is no fallback for this". The only route is an explicit `--projects` glob built from that path's own slug. It also says that a `--branches` filter now matches a removed worktree's sessions on an earlier branch of the same name (row 28). Its `skill-invocation` sentence and its pointer to a separate lookup go.
- :71 still counts four gaps. Its second sentence becomes one sentence per fact:
  - A slug collision shares a live worktree's directory, so the count does not move.
  - A foreign clone under the worktrees directory adds to the unlisted count.
  - `cost --summary` prints no such header.
  - The "Transcript files scanned" column is the one `cost --summary` figure that moves whatever the branch and date filters.
- :73 and :693: "identity match" and "worktree-identity match" become "admission rule".
- :451: `skill-invocation`'s scope defers to "Scoping to this repo" in place of "matched by exact directory identity".
- :454: "this repo's own worktrees only (publish-safe without `--include-subagents`; see Limits)" becomes "the `--this-repo` scope (see "Scoping to this repo" for what it admits, and Limits for `--include-subagents`)". :455's "already defaults to this repo's own worktrees" becomes "already defaults to the `--this-repo` scope".
- :496: "required before quoting output publicly (see below)" becomes "required, but not sufficient, before quoting output publicly (see "Scoping to this repo" above for what it admits and why its output can span accounts)". The flag bullet's "by identity" goes with the sweep of all 22 bullets under "Code-review round 1 additions".
- :1496: only a PR whose removed worktree lived outside `<main>/.claude/worktrees/` is absent, and its pointer names the rewritten :68 bullet.
- :1800: "the two deny lookups" becomes "the deny lookup".
- :1838-1847 keep one lookup. :1842 and the second-lookup paragraph at :1845 go. "**The deny lookups.** Run both" (:1838) and "run both lookups" (:1847) become singular.
- :1895: capture reads the directories `--this-repo` admits, so the over-inclusions under "Scoping to this repo" apply to it. Any use of the word there says "unlisted directories", because :1894 uses "unlisted" for a branch the note omits.
- :2395: `N` equals the directories under that account's `projects/` named for a live worktree, or starting with the first listed worktree's slug plus `--claude-worktrees-` and longer than that prefix. That slug is the first path `git worktree list` prints, with every `/` and `.` replaced by `-` as the `tr` in :65's command does. `L` counts the live worktrees that have one.
- Header samples at :129, :516, :973, :1724, :2344 and :2392 take `N project dirs: L live, U unlisted`. The :1509 sample's figures are illustrative filler that row 15's test masks, so it takes `3 project dirs: 1 live, 2 unlisted`.

**Modify, docs:** `docs/transcript-analysis-architecture.md:797-800` names the new test file and its seam beside test_transcript_scope_scan.py (row 33).

**Code-review round 1 additions (rows 40 and 41).**
- `claude/.claude/scripts/tests/conftest.py`: `_stub_git_worktree_listing(monkeypatch, porcelain, cwd, toplevel)` goes beside `_worktree_porcelain` (:1511). It stubs the `worktree list --porcelain` and `rev-parse --show-toplevel` calls and the `os.getcwd` patch, taking porcelain, cwd and toplevel as arguments so the `bare-first` case can pass hand-written porcelain. The new scope test file and `TestSkillInvocationRepoScope`'s new test adopt it. Older inline copies stay. conftest.py is over G4's cap, and splitting it is out of scope.
- `claude/.claude/scripts/tests/test_transcript_shared_fixtures.py`: one unit test of that helper (row 41).
- The helper lands before the tests that call it, in Verification step 1's order.
- `claude/.claude/scripts/tests/test_transcript_scope_worktree_admission.py` gains a case where `<main-slug>--claude-worktrees-x` sits mid-name (slugs `["-work-app"]`, directory `-data-work-app--claude-worktrees-x`) and is not admitted. It also gains a parametrized test over `_repo_project_dir_matcher(slugs).admits` and `.is_live`, one id per rule.
- The stale comments at test_transcript_scope_scan.py:328-330 and :413-415 and test_transcript_scope.py:467-468 and :536-544 are reworded to the admission rule and the counts helper.
- scope.py's `--config-dir` zero-match path reports a root that cannot be listed as that cause, not as "matched zero project directories", with a test for a root at mode 0o311 that skips under root. The zero-match message names the main checkout's worktrees-directory prefix, and the routing-guard refusal's `review-trace` argument list reads unambiguously. skill_invocation.py's `--projects` and `--this-repo` help reuse the scope.py one-sentence scope statement.
- docs/transcript-analysis.md: :2169 says the PR-body block reads the directories `--this-repo` admits. The 22 per-subcommand "own worktrees by identity" bullets lose "by identity" and point to "Scoping to this repo". :50 drops "the same minimization control ... since it shipped". This overrides :292's keep and Out of scope's keep of those bullets.
- CHANGELOG.md: one `[Unreleased]` > `### Changed` entry, in the form of the `user-input` entry, with these facts and no real-corpus figure.
  - `--this-repo` also reads removed worktrees' directories under `<main>/.claude/worktrees/`. One that lived outside that directory stays excluded, bare layouts included, and the entry points to "Scoping to this repo" for the over-inclusions and the wider publication instruments.
  - The header is `this repo (<N> project dirs: <L> live, <U> unlisted)`, and `<N>` now counts admitted directories present, once per resolved path.
  - The routing-guard refusal names one `review-trace --deny-only --this-repo` lookup.
  - `cost-ledger` rows recorded with `--this-repo` before and after the change are not comparable.

**Also in the diff:** `.claude/plans/this-repo-removed-worktree-scope.md`, `CHANGELOG.md` and the two test files above.

**Reuse:**
- `_list_dir_recording_gaps` (scope.py:308-323) for every new listing.
- `_dedup_new_project_dirs` (:234-273), unchanged in behavior. Its stat-and-resolve step becomes `_resolved_project_dir`, which the count shares.
- `_path_to_project_slug` (:85-93).
- From `tests/conftest.py`: `_write_jsonl` (:40), `_worktree_porcelain` (:1511), `fake_projects` (:1525) and `_asst`.

Projected diff, about 735 lines:
- CHANGELOG.md: about 12.
- tests/conftest.py: about 18.
- test_transcript_shared_fixtures.py: about 15.
- Code-review round 1's fixes: about 65, spread across the files in this list.
- scope.py: about 185.
- routing_guard.py: about 15.
- redaction.py: about 5.
- skill_invocation.py: about 14.
- cost.py: about 10.
- The new test file: about 215.
- test_transcript_skill_invocation.py: about 30.
- test_transcript_cost_counts.py: about 22.
- test_transcript_routing_guard_compute.py: about 30.
- test_transcript_routing_guard_capture.py: about 15.
- The label edits, the two test docstrings and `TEST_FILES`: about 20.
- docs/transcript-analysis.md: about 66.
- docs/transcript-analysis-architecture.md: about 4.

That is past row 16's 400.

## Verification

Run from the worktree root (G5).

1. Red first.
   - Order: add the conftest.py helper first, then the new test file and every test edit under Critical files, before any production or doc edit. Doc edits wait too, because test_transcript_review_cost_by_size.py:801-811 compares the :1509 sample with the real header.
   - Command: run `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py`, and confirm the run collected the new file. A missing file is a rule-table gap to report, never a reason to widen the run by hand (`CLAUDE.md` § "Commands").
   - Expected result: the run fails, and every failure is behavioral: an assertion failure, or the `SystemExit` of today's zero-match refusal. No failure is a collection, import or attribute error. The return names each failing ID's failure kind.
   - The failing node IDs are exactly these:
     - Every test in test_transcript_scope_worktree_admission.py, both cases of the parametrized one included.
     - test_transcript_skill_invocation.py::TestSkillInvocationRepoScope::test_a_removed_worktree_dir_is_in_default_scope_and_a_fork_is_not.
     - test_transcript_cost_counts.py::TestCostCounts::test_an_untracked_agent_type_in_an_unlisted_worktree_dir_is_withheld.
     - The seven label pins (row 15):
       - test_transcript_cli.py::test_read_cost_this_repo_runs_to_a_report_through_main
       - test_transcript_cost.py::TestCost::test_this_repo_scopes_via_resolve_project_scope
       - test_transcript_read_cost_command.py::TestScopeRefusal::test_header_states_the_active_account_the_working_directorys_repository_and_the_unconsulted_roots_file
       - test_transcript_review_cost_by_size.py::TestCmdReviewCostBySize::test_default_mode_reads_the_active_root_alone_and_prints_rows_after_every_aggregate
       - test_transcript_review_cost_by_size.py::TestCmdReviewCostBySize::test_all_accounts_merges_every_root_and_marks_both_streams_do_not_publish
       - test_transcript_scope.py::TestResolveProjectScope::test_resolved_scope_header_renders_under_this_repo_and_under_a_glob
       - test_transcript_scope.py::TestThisRepoUnionsAcrossRoots::test_this_repo_allow_case_when_only_a_non_first_root_matches
     - test_transcript_routing_guard_compute.py::TestUnlistedDenyRemedyCommand::test_the_named_review_trace_command_parses_in_each_scope_form, under whatever name its one remaining form gives it.
     - test_transcript_routing_guard_capture.py::TestReconcileDenies::test_end_to_end_an_unlisted_branch_deny_refuses_and_publishes_nothing.
   - The edited capture orphan test (`TestScope`, :2386) passes before and after, because it pins M5's count against today's.
   - Report any other failing ID, and any listed ID that passes. A listed test that passes before the fix guards nothing until it gains an assertion that fails.
2. After the production and doc edits:
   - `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py` passes. For any failure, rerun its node IDs at the merge-base, per `CLAUDE.md`'s "Prove your change caused a failing check". An ID that fails only on this branch blocks. Report the run's summary line, with zero failed.
   - The deny halves are shown red. Loosen `admits` one way at a time, and run `scripts/venv-run.sh pytest claude/.claude/scripts/tests/test_transcript_scope_worktree_admission.py` under each. The first mutation drops the length check. The second sets the prefix to the bare first slug, with no infix. Under each, `test_prefix_admits_unlisted_worktree_dirs_and_rejects_near_misses` and `test_config_dir_with_only_near_miss_dirs_exits_1_naming_counts_only` must fail. Restore `admits`, rerun the file, and report the failing IDs under each mutation.
   - `git diff CHANGELOG.md` shows one `[Unreleased]` > `### Changed` entry naming the four facts under "Code-review round 1 additions", since no test checks it.
   - `git grep -n "project dirs)" -- docs` prints only `docs/cost-levers-considered.md:663`, a preserved record (row 17). Any other hit is a header sample the doc edit missed.
3. The engineer runs this step outside any agent session, and records the result in the PR description's test plan.
   - Run `read-cost --this-repo` or `review-cost-by-size --this-repo`, which read the active account alone, or another `--this-repo` command whose header reads `1 root`. A header over several roots sums their directories and reads as a false mismatch.
   - Count the directories under that account's `projects/` that the rewritten docs/transcript-analysis.md:2395 sanity check defines.
   - Record two booleans and no figure, because the figures are per-account (`CLAUDE.md` § "Redact private-project-identifying content"). One is whether `<N>` equals that count. The other is whether `<U>` is above zero.
   - The second boolean is the one check of G2 against a real corpus. It shows G2 only when one unlisted directory belongs to a worktree the engineer removed.

## Out of scope

- **Splitting scope.py or routing_guard.py under G4** (sizes in row 11). Enforcement waits on the offender assessment that code-file-line-limit.md:50-57 requires. This change adds about 60 lines to scope.py.
- **A count in `skill-invocation`'s header.** Its label (skill_invocation.py:156-164) never carried one. It gains the rule through `_iter_scoped_sessions`, and its label stays as it is.
- **Printing the counts in the two `pr-cost-section.sh` blocks.** `cost --summary` prints no resolved-scope header (cost.py:703-708), and `cost-counts` discards its label (subagent_mix.py:530). docs/private-project-redaction.md:152-154 says a change to what the block prints reopens its bar. The rewritten docs :71 says which `cost --summary` figure the widening moves whatever the filters (cost.py:323).
- **A removed worktree that lived outside `<main>/.claude/worktrees/`, and a session started in a subdirectory of a worktree outside it.** No slug pattern ties either to this repo (row 9). The only route to either is an explicit `--projects` glob built from that path's own slug, as the rewritten docs :61 and :68 say.
- **Sessions started in a main-checkout subdirectory.** Their slugs extend the main checkout's slug with no infix, as a sibling `<repo>-fork`'s does (docs/transcript-analysis.md:67). The `--git-common-dir` glob at docs/transcript-analysis.md:61-67 stays their documented route.
- **`docs/private-project-redaction.md`**, by the engineer's choice (row 29). The PR description states the foreign-clone residual instead.
- **Rewording the per-subcommand `--this-repo` flag bullets beyond dropping "by identity".** The sweep under "Code-review round 1 additions" changes only that clause and adds the pointer to "Scoping to this repo".
- **Scope statements in files this change does not otherwise edit.** Each stays true, or already defers to "Scoping to this repo":
  - `claude/.claude/scripts/transcript_analysis/sessions.py:22` says a main session file reaches `sessions` through the scope path every other subcommand uses, which stays true.
  - `claude-skills/skills/transcript-analysis/SKILL.md:108` makes only the account-scope claim, which stays true. Its :107 already defers to "Scoping to this repo" for what `--this-repo` admits.
  - `evals/review_bench/mine_review_rounds.py:47` and `evals/run_review_bench.py:2085` say the miner is scoped to this repo's own worktrees on one root. The removed worktrees the rule adds are this repo's own, and row 26 accepts the miner's widening.

  Editing any of them would add a file beyond the sets of rows 39 to 41.
- **Skill bodies that run `--this-repo` commands.** None quotes the header or the exact-name rule (Context). review-loop-cost-audit/SKILL.md:159 names same-named-branch pooling across roots only, and the PR description carries row 28's case inside one root.
- **Recomputing a figure already published, such as a merged PR's cost block.** Those record past runs. The PR description lists the instruments whose figures move (rows 2, 3 and 26).
  - #1202's Related note says "the published numbers may need a re-run once this is fixed". The PR description answers it with this sentence: "No re-run is planned for the seven documents under docs/case-studies/ that cite `--this-repo` figures, or for docs/cost-levers-considered.md, because each records a dated run."
  - If the engineer wants a re-run decision tracked instead, the PR description links a follow-up issue naming those eight documents.
- **The dated header counts in docs/case-studies/handoff-signal-response.md:21, docs/cost-levers-considered.md:663 and plan files under `.claude/plans/`.** They are preserved records (row 17).
- **`docs/transcript-analysis-architecture.md` beyond :797-800, including the earlier design's `cmd_<snake>` edit** (row 12).
- **The path-form `.claude/worktrees/` matchers in reviewer_yield.py:277-282 and period_cost.py:193** (row 19), and the test literal `_WORKTREE_INFIX` at test_transcript_routing_guard_capture.py:102, a DAMP test value.
- **#1157.** It ships in its own PR, apart from #1202.
