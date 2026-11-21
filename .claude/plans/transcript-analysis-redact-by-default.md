# GH-1157: close transcript-analysis's unredacted multi-root output paths

## Context

Stop `transcript-analysis` from reading and printing another account's transcripts by accident: commands that print raw paths, text or names read only the active account unless `--this-repo` bounds the scan to this repository or `--all-accounts` asks for every account.

Ask: "GH-1157: close the unredacted multi-root output paths in transcript-analysis." The engineer first wrote "Decision already made: redact by default, with --no-redact as the opt-out. Do not reopen it." and later reopened that decision themselves: "I almost think redacting by default is overcmplicated, and --no-redact forcing is maybe better than these custom labels whic hseems overcomplicated. I'm now wondering what the benefit of this default redaction is at all." On the scoping design the session then proposed (listings read the active account by default, aggregate tables relabel above one account, shared refusal helper with a backstop in both resolvers, `read-scope` numbering fix): "Ok I think the recommended option looks good to me but have Fable adversarially review it." After a second review round the engineer wrote "I think we're being a little too paranoid with redaction." Further constraints and answers the engineer gave, quoted in the order given; a later answer replaces an earlier one where a bullet says so:

- "One shared --no-redact refusal helper; the issue names resolve_scan_roots in transcript_analysis/scope.py as its home."
- "Removing --redact is a breaking flag change and needs a CHANGELOG.md Migration note."
- "Check which session holds GH-1116 (the transcript-analysis decomposition) and which files it owns before choosing where edits land."
- "Split into more than one PR if the plan says so, and say where the split is."
- "Tests use synthetic fixtures only. No output from a real multi-root run goes into the plan, a test, or a PR body."
- "re-resolve every cited site by symbol, and audit each sibling subcommand for the same unredacted-output shape instead of trusting the list."
- On free text, typed in answer to the question of what text-printing commands should do: "transcript-analysis should NOT redact free text because it's useful for analysis and experimentation."
- On whether to change `post-crash-sessions.py`'s own opt-in `--redact` in this plan: selected label "Leave it out (Recommended)".
- On whether `--this-repo` should keep this repo's own branch names readable on every branch-printing command: selected label "Yes, disclose (Recommended)".
- On whether `subagents`, `subagent-mix` and `review-round-cost` should also switch to redacted-by-default on a single root, with `--no-redact`, as a fourth PR: selected label "No, drop PR 4 (Recommended)".
- On whether the `--no-redact` refusal should also be backstopped inside both root resolvers: selected label "Backstop in both resolvers (Recommended)".
- On whether a branch counts as this repo's own only when a main-thread record's working directory is inside this repo's worktrees: selected label "Require cwd in this repo (Recommended)".
- On agent-type and hook names this repo does not track, above one root: selected labels "Hide untracked names (Recommended)" and "One label per name (Recommended)".
- On whether the branch, session and project labelers move into one shared helper: selected label "Keep the refactor (Recommended)".
- On two earlier answers (that `sessions --paths` would need `--no-redact`, and that `user-input` would lose `--redact`): selected label "Withdraw both (Recommended)".
- On the same branch worked from several accounts: "Sometimes for my own repos, I will use multiple claude accounts for the same branch - it does happen, so we should consider this case. But I want to know if including it would cause overengineering." Then, on whether the text listings keep pooling every account under `--this-repo` and narrow to the active account only at `--projects` scope: selected label "Pool under --this-repo (Recommended)".
- On whether to add an `--all-accounts` flag that pools the text listings raw: selected label "Drop the flag (Recommended)".
- On whether `audit-routing` keeps `--redact`: selected label "Keep --redact there (Recommended)".
- On whether `skill-invocation --projects GLOB` narrows to the active account or relabels its skill names above one account: selected label "Narrow to active account (Recommended)".
- On whether the one shared branch rule (readable only if typed, or attested under `--this-repo`) also replaces the three rules `subagents`, `subagent-mix` and `review-round-cost` use today: selected label "Apply it to all six (Recommended)".
- On whether `review-trace` relabels its per-session path header above one account: selected label "Leave paths raw".
- On whether `reviewer-yield --redact` becomes a real opt-in instead of being removed: selected label "Make it a real opt-in (Recommended)".
- On whether losing a single pooled sample across accounts changes the choice to drop `--all-accounts`: selected label "Keep pooling for samples only". The session told the engineer this leaves audit finding S6 open.
- On whether `buckets`, `duration` and `struggle` read only the active account unless `--this-repo` (pooled and raw under it), with `subagents`, `subagent-mix` and `review-round-cost` left as they are today: selected label "Narrow the three (Recommended)". The question said this replaces "Apply it to all six". The session's reading is that it also leaves "Yes, disclose", "Require cwd in this repo" and "Keep the refactor" with nothing to apply to.
- On whether the `review-trace` timeline stops hiding untracked hook and agent-type names: selected label "Drop it (Recommended)". The question said hook names would then be hidden nowhere.
- On whether `reviewer-yield`'s relabelling of untracked agent types also switches on automatically above one account: selected label "Opt-in only".
- On whether this change covers `token-analyzer.py` and `analyze-context.py --top`: selected label "Leave them out (Recommended)".
- On whether `audit-routing-samples` and `handoff-signal-response --sample` print the existing DO NOT PUBLISH line on stderr when they read more than one account: selected label "Keep the banner (Recommended)".
- On whether `transcript-narrative` Step 2's `sessions --paths` gains `--this-repo`, typed: "--this-repo is fine but will it stil allow the option to pool?"
- On what `audit-routing` should do above one account, typed in place of an option, excerpted: "Yo if we retract my decision to redact account names, how bad is that? I honestly don't think it's that big of a deal and I think we're finding more edge cases and it's getting complicated"
- On whether the plan drops all new relabelling and uses one rule instead (commands that print raw names, paths or text read the active account by default, `--this-repo` pools this repo across accounts, and a new `--all-accounts` flag pools everything raw): selected label "One rule with --all-accounts (Recommended)". The question said this applies to the seven narrowed commands plus `audit-routing` and the four sample commands, and replaces "Drop the flag" and "Keep pooling for samples only".
- On how a pooled `--all-accounts` run marks itself, given that `review-cost-by-size --all-accounts` prints a DO NOT PUBLISH line: selected label "Help text only (Recommended)".
- On code review's request that a widened run print the DO NOT PUBLISH line in-band, replacing the answer above for `--all-accounts` only: selected label "Banner on --all-accounts only (Recommended)". Plan-review then found four gaps in that line, and a plan-architect consult recommended returning to the earlier answer. The engineer withdrew the banner: selected label "Withdraw it: help text only (Recommended)". The answer two bullets up stands.
- On whether PR 1 stays whole at a projected 900 changed lines or splits into seven commands then five: selected label "Keep it whole (Recommended)".
- On whether PR 1 adds a validator refusing an absolute `--projects` value at every root count, leaving `user_input.py`'s identical defect to the follow-up issue: selected label "Add the validator (Recommended)".
- On whether PR 1 splits after review fixes raise its projection to about 1,350 changed lines: selected label "Proceed anyway".

Problem: a multi-root scan reads transcripts from more than one account.

- Some subcommands print raw transcript paths, raw message text, or other identifying fields from that scan.
- The refusal that guards `--no-redact` on a multi-root scan is duplicated per subcommand instead of shared.
- GH-1157 tracks both from the 2026-08-22 discovery audit (findings S4, S5, S6, S7, S15, I1, SC5).

Why now:

- The issue is `priority:high`.
- Unredacted cross-account output cannot be recalled once an agent publishes it.
- The issue's 2026-11-19 status comment confirms the `review_trace.py` sites are still open on the default branch.

Intended outcome, with the exceptions the Approach lists:

- Twelve commands read only the active account's root by default. The Approach's Terms list them as the narrowed commands.
- Under `--this-repo` those commands pool every declared root and print raw, limited to this repository's sessions.
- Under a new `--all-accounts` flag they pool every declared root and print raw.
- The top-level `--config-dir` still names one account.
- A run that read the active account alone says so in its scope header.
- Nothing is relabelled that prints raw today. `audit-routing` keeps its opt-in `--redact`.
- `audit-routing-samples` and `handoff-signal-response --sample` print the existing DO NOT PUBLISH line on stderr when they read more than one root.
- An absolute `--projects` value exits 2 with one stderr line at every root count, before any scan or redact-map build.
- `reviewer-yield --redact` relabels agent types this repo does not track, at any root count, and nothing relabels there without it.
- `subagents`, `subagent-mix`, `review-round-cost` and the subcommands that already redact at every root count keep their behavior.
- One shared helper refuses `--no-redact` above one root, and both root resolvers backstop it.
- Free text is never redacted, so no text listing is safe to publish as printed.
- `--all-accounts` is the one flag added, and no flag is removed.
- Docs, the skills that run the tool, and tests match the new behavior.

State of GH-1116 at planning time, checked 2026-11-19 against `origin/main` at `b7129175`:

- The issue is closed.
- `claude/.claude/scripts/transcript-analysis.py` is a 14-line entry point, and every subcommand lives under `claude/.claude/scripts/transcript_analysis/`.
- No open PR, remote branch, or local worktree carries GH-1116 work.
- All edits therefore land in `transcript_analysis/`.

## Approach

The twelve narrowed commands below read the active account unless `--this-repo` or a new `--all-accounts` widens them, and a second PR makes two existing redaction flags do what their help says.

Terms, held for the whole plan:
- **Narrowed commands**: `review-trace`'s timeline (`--deny-only` included, `--deny-summary` not), `judgment-pair`, `sessions`, `skill-invocation --projects GLOB`, `buckets`, `duration`, `struggle`, `audit-routing`, `audit-routing-samples`, `turn-shape-samples`, `turn-shape-holdout-samples` and `handoff-signal-response --sample`.
- **Pooled modes**: `review-trace --deny-summary`, `handoff-signal-response` without `--sample`, and `skill-invocation` without `--projects`. They read every declared root by default, as today.
- **`--no-redact` family**: `cost`, `cache-efficiency`, `cache-rebuild`, `context-composition`, `context-distribution`, `edit-format`, `handoff-signal-response`, `plan-boundary`, `read-scope` and `rearm-backtest`.

Two PRs, the second branched from the default tip after the first merges (row 7):
1. **One scope rule** (M1-M4). It closes audit findings S4, S5, S6, S15 and S7's three tables by narrowing (`.claude/plans/discovery-audit-remediation-plan.md:635-654`).
2. **Redaction flags that do what they say** (M5, M6). It closes SC5 and I1 and no leak, so it lands last.

Why this split:
- The banner (M4) joins PR 1. It fires only above one root, which on its two commands only PR 1's `--this-repo` and `--all-accounts` routes reach. It edits the two functions PR 1 narrows. Its tests reuse PR 1's two-root runs.
- `reviewer-yield --redact` (M5) joins the refusal (M6). Both make an existing redaction flag do what its help says, and neither closes a leak. On its own, M5 is about 130 lines that would pay a second review cycle and a second `/skill-review` for one table.
- PR 1 stays whole (row 26). Splitting it into the seven earlier commands and the five later ones would edit the active-account list, the header clause's pins, the `transcript-analysis/SKILL.md` paragraph and the Migration entry twice, each half with its own `/skill-review`. It would also leave the one rule applied to seven commands between merges.

Order and reverts:
- PR 1 goes first. It closes every leak in the plan, and PR 2's backstop edits `resolve_scan_roots`, which PR 1 changes.
- Revert newest first. PR 2 edits `resolve_scan_roots`, and the refusal block beside PR 1's narrowing and banner lines in `cmd_handoff_signal_response`. Both PRs edit `docs/transcript-analysis.md:103`, `transcript-analysis/SKILL.md`, `test_transcript_cli.py`, `test_transcript_package_module_prefixes.py` and `CHANGELOG.md`. An out-of-order revert therefore needs conflict resolution, not a plain `git revert`.

Closure:
- PR 2's body closes GH-1157.
- The remnants left open go in one follow-up issue: `fail-seq`'s part of S7, `post-crash-sessions.py`, `token-analyzer.py`, `analyze-context.py --top`, `user_input.py`'s absolute `--projects` crash, the `.` and `./` `--projects` crash in `_scan_root_transcripts`' four callers at one root, and the `review-loop-cost-audit/SKILL.md:35` label mismatch. The engineer approves that issue when PR 2 is opened, and the plan does not file it.

Alternatives weighed:
- **Relabel the branch tables above one root through a shared labeler**, an earlier revision. Set aside by row 13. It added attestation, a labeler class and per-account rows, and it changed the Branch cell that skills copy into `--branches`.
- **Relabel `audit-routing` above one root without `--redact`**, the previous revision. Set aside by row 19.
- **Narrow by default inside `resolve_scan_roots`.** Set aside: the 14 other in-package callers would each pass a keyword to keep pooling, and so would `analyze-context.py` and `token-analyzer.py`, which row 23 leaves unchanged (row 28).
- **Make `--this-repo` and `--all-accounts` mutually exclusive.** Set aside under M3.
- **A refusal line that names a way to narrow.** Set aside: nine of the ten family members cannot narrow below the declared roots (row 39), so the line names only dropping `--no-redact`.
- **Change the shared `--this-repo` help and override it where it is false.** Set aside: finding every registrant whose `--this-repo` does not pool needs a read of all 40 `_add_project_scope_args` call sites, and at least three would each pass an override (row 57).

### Assumption ledger

**Root:** A multi-root scan reads more than one account's transcripts. The narrowed commands print another account's raw paths, text, names or session IDs from it by default (rows 29, 34, 37). `reviewer-yield --redact` is a no-op (row 38). The `--no-redact` refusal is inlined ten times with drifting wording (row 39).

**Givens:**
- G1. Claude Code writes each transcript at `<config-dir>/projects/<cwd slug>/<session-id>.jsonl` and stamps `gitBranch` and `cwd` on records, so a path, slug, session ID or branch identifies a project and an account. Reason: the vendor owns the transcript format.
- G2. The plan, tests and PR bodies carry placeholders and synthetic fixtures only. Reason: the repo-root `CLAUDE.md` § "Redact private-project-identifying content" binds every contribution to this public repository.

**Mechanisms:**
- **M1 (PR 1).** The narrowed commands read the active account by default.
  - `scope._narrows_to_active_account(args) -> bool` returns true when none of `--this-repo`, `--all-accounts` and the top-level `--config-dir` is set. It reads all three with `getattr`, since hand-built test namespaces lack them.
  - `resolve_scan_roots(parsed, *, active_account_only: bool = False)`: after the `--config-dir` return, `True` returns `[_projects_dir()]` without reading the declared-roots file.
  - Each narrowed command computes `active_account_only` once into one local, and passes that local to its resolver call and every header call:
    - `review-trace`: `_narrows_to_active_account(args) and not deny_summary`, so `--deny-summary` stays pooled.
    - `skill-invocation`: `_narrows_to_active_account(args) and bool(projects_arg)`, so its default this-repo scope stays pooled. Its multi-root `--projects` branch stays, since `--all-accounts` reaches it.
    - `handoff-signal-response`: `_narrows_to_active_account(args) and bool(sample_n)`, with `sample_n` read before the resolver call, so the aggregate report stays pooled. Its benchmark pass reuses the same roots, so a narrowed sample's benchmark covers the active account too (row 29).
    - The other nine: `_narrows_to_active_account(args)`.
  - Under `--this-repo` every narrowed command pools every declared root and prints raw, as today (row 11).
  - `audit-routing` gains no relabelling. Its `--redact` keeps working on whatever roots the run resolved (rows 18, 19).
  - Lighter primitives checked:
    - a changed resolver default, set aside under Alternatives;
    - a `resolve_listing_roots` wrapper returning roots and flag, which adds a second resolver entry point and still leaves each header call to thread the flag.

  anchors: root, row11, row12, row13, row14, row18, row19, row28, row29, row30, row31
- **M2 (PR 1).** The header says when a narrowed command skipped declared roots.
  - `_root_count_desc(roots, *, active_account_only=False)` keeps its absent and unreadable wordings first. Then, at one root with the flag, it returns `1 root (active account only; --this-repo or --all-accounts also reads ~/.claude/transcript-config-dirs)`.
  - That clause holds for any present roots file, an empty one included (row 32).
  - `_resolved_scope_header` and `print_resolved_scope` take the same keyword and pass it through.
  - The flag is false under `--all-accounts`. Under the top-level `--config-dir` the header keeps row 33's wording.

  anchors: row32, row33, row44
- **M3 (PR 1).** `--all-accounts` widens a narrowed command to every declared root.
  - `scope._add_all_accounts_arg(parser) -> None`, beside `_add_project_scope_args`, registers `--all-accounts` as `store_true` outside the `--projects`/`--this-repo` group, with the help `Read every account ~/.claude/transcript-config-dirs declares, not the active account's alone. The output carries every declared account's raw names, paths and text and is not for publication (see docs/private-project-redaction.md).`
  - The help, the docs bullet (M8) and the `N roots` clause every header prints are the flag's markers (row 54).
  - Each of the twelve narrowed subcommands' registrars calls it once, and no other registrar does. A pooled mode accepts the flag and reads what it reads without it.
  - It reads the same accounts as the existing `--all-accounts` on `pr-cost` and `review-cost-by-size`: every declared account in one run (row 51). Those two keep their own registration and help, since each help text is specific to its ledger.
  - Beside `--this-repo` it changes nothing, since `--this-repo` already reads every declared root. Both existing registrants accept the two together.
  - Beside `--projects GLOB` it reads the glob in every declared root, under the one-level glob rule that applies above one root. That is the subdirectory fallback's pooled route.
  - Beside the top-level `--config-dir` it exits 2 (row 55). After its existing refusal block, `cli.main()` prints `<subcommand>: --all-accounts is refused with the top-level --config-dir, which names one account; drop one of them` on stderr when `getattr(parsed, "all_accounts", False)` is set. Only the twelve narrowed subcommands reach that check (row 56).
  - No caller can meet that pair before PR 1, since the twelve do not register `--all-accounts` today (row 51). The refusal therefore carries no Migration bullet.
  - Under the flag the header reads `N roots`, or row 32's one-root wording when no other root resolves.
  - Mutual exclusion with `--this-repo` was set aside. It needs a runtime check, because `--this-repo` already sits in the `--projects` group (row 52), and it would refuse a pairing both existing registrants accept.
  - Lighter primitives checked:
    - a top-level `--config-dir` run per account, which cannot pool one sample or one table;
    - `--this-repo`, which bounds the run to this repository.
  - Other handlings of the `--config-dir` pair checked:
    - letting `--config-dir` win, which prints one account's rows as complete to a caller who asked for every account;
    - a header naming `--config-dir` as the reason for one root, which threads a second reason through `_root_count_desc` and every header call;
    - the check inside `_narrows_to_active_account`, which turns a predicate into an exit path for twelve callers.

  anchors: row12, row32, row51, row52, row54, row55, row56
- **M4 (PR 1).** `audit-routing-samples` and `handoff-signal-response --sample` print `scope._DO_NOT_PUBLISH_BANNER` on stderr above one root, which on those two now takes `--this-repo` or `--all-accounts`. Stderr keeps their JSON stdout parseable.

  anchors: row20, row37
- **M5 (PR 2).** `reviewer-yield --redact` relabels untracked agent types.
  - `redaction._untracked_agent_type_labels(agent_types) -> dict[str, str]` maps each name in `_repo_tracked_agent_type_names()` to itself. It maps each other name to `agent-type-<N>`, numbered from 1 over the sorted distinct untracked names alone.
  - The labels are stable within one run, not across runs, since the run's window and scope decide which untracked names it numbers.
  - Under `--redact`, `cmd_reviewer_yield` builds that map once from `agg` and prints both tables' `AgentType` through it, at any root count.
  - Without `--redact` both tables print raw.

  anchors: row17, row38
- **M6 (PR 2).** The shared `--no-redact` refusal, and I1.
  - `scope._refuse_no_redact_above_one_root(args, roots, subcommand) -> None` prints `<subcommand>: --no-redact is refused when more than one root is in scope; drop --no-redact` on stderr, and exits 2, when `getattr(args, "no_redact", False)` meets more than one root.
  - `scope.resolve_redaction(args, roots, subcommand) -> bool` calls the refusal and returns `not getattr(args, "no_redact", False)`.
  - Backstops (row 5): `resolve_scan_roots` calls the refusal on the roots it returns, labelled `getattr(parsed, "subcommand", None) or "transcript-analysis"`. `_resolve_cost_roots` replaces its own block with the same call.
  - Nine family sites replace their `redact` read and inline block with one `resolve_redaction` call on their own scan roots. `cost` keeps its early raw read, which its `--summary` and `--share-only` refusals use, and replaces only its block with the refusal call.
  - `handoff-signal-response --sample --no-redact` succeeds on a default run, since M1 narrows it to one root. The resolver backstop and `resolve_redaction` both refuse it under `--this-repo` or `--all-accounts` above one root. PR 1 already rewrites that flag's help (M8).
  - I1: `_read_scope_report` merges each session into `per_account[ordinal - 1]`, with the ordinal from `scope._redaction_ordinals(scan_roots)`. `_print_read_scope_report`'s `account-{idx + 1}` then follows sorted resolved path with no change.
  - Lighter primitives checked:
    - the backstops alone, since neither resolver returns the redact decision, and a direct report-function caller passes roots no resolver produced;
    - the inline blocks as they stand, which fail row 4.

  anchors: row4, row5, row39, row40, row41, row42
- **M7.** Tests.
  - Every test uses synthetic fixtures (row 8).
  - Every narrowed command has three cases over two declared roots: a default run prints the active root's sentinel only, and an `--all-accounts` run and a `--this-repo` run each print both roots' sentinels.
  - Every absence assertion shares its test with a positive control proving the run printed rows, or that the excluded record is readable.
  - A test sets `all_accounts` on a namespace after building it, so no shared args factory or helper gains a keyword (row 45).
  - An args factory or session builder that two test files use moves to that family's `T/_<family>_helpers.py`, which `.claude/rules/transcript-analysis-tests.md` names as the home for one family's shared helpers.
  - Placement (row 43):
    - each helper's tests sit in its module's file;
    - each invariant across modules sits in its own `test_transcript_analysis_<invariant>.py`;
    - a file that would cross 1,000 lines gets a seam file instead.
  - Each new test file (row 43):
    - joins `TEST_FILES`;
    - reads at least one `<module>.<name>` through `from transcript_analysis import <module>`;
    - never uses `from transcript_analysis.<m> import`.

  anchors: row8, row43, row44, row45
- **M8.** Docs, skills, help text and `CHANGELOG.md`.
  - The active-account list under `docs/transcript-analysis.md` § "Corpus scope: the declared-roots file" is the one statement of which commands narrow, how `--all-accounts` combines, and that its output is not for publication. Other sites point to it.
  - Wherever a skill or doc tells a reader how to get the pooled view, it names both routes: `--this-repo` for this repository, `--all-accounts` for everything. Widening is for a question that needs accounts beyond the active one, not a routine rerun.
  - The eleven narrowed registrars that call `_add_project_scope_args` pass `this_repo_help=scope._POOLED_THIS_REPO_HELP`, which reads `Scope to this repo's own worktrees, read from every declared account (see docs/transcript-analysis.md).` The shared default stays, since `read-cost` and `cost-counts` take it and read one account (row 57).
  - `handoff-signal-response`'s `--no-redact` help and doc bullet say a default `--sample` run reads one root, in place of advising `--this-repo`.
  - `handoff-signal-response`'s docs say a default `--sample` run ranks its cards and computes `exceeds_startup_burn_benchmark` over the active account only (row 29).
  - Callers that run a narrowed command without `--this-repo` (row 46):
    - `transcript-narrative`'s Step 2 `sessions --paths` and its two `duration` runs gain `--this-repo`, matching that skill's other repo-scoped steps (row 50).
    - `error-mode-analysis` says a `--projects` glob on `buckets` or `review-trace` reads the active account, and that adding `--all-accounts` to span accounts is the user's call, not the routine fallback. Its Step 7 holds whichever scope Step 1 used.
    - `transcript-analysis/SKILL.md`'s examples and decision-table rows gain nothing. The paragraph added after its pinned `:20` sentence covers them.
    - The `audit-routing --redact` advice in `transcript-analysis/SKILL.md:103` and `transcript-narrative/SKILL.md:87` gains nothing. Its default now reads one account, and above one root it meets row 35's abort.
    - `token-analyzer.py:188` names `audit-routing` with no scope and stays, since row 23 leaves that script unchanged.
  - `turn-shape-holdout-samples`' docs say one calibration pass holds its scope flags fixed across `--offset` pages, since the scope sets the shuffled population (row 53).
  - Each PR's `CHANGELOG.md` entry carries one Migration bullet per behavior a script or agent meets. Each bullet names the old invocation, the new one, and what a stdout parser sees (row 6).

  anchors: row6, row10, row23, row29, row35, row36, row46, row47, row49, row50, row53, row54, row57

**Rows:**
1. [engineer-verified: "I think we're being a little too paranoid with redaction."] This revision's direction; Context's Intended outcome is the cut it sets.
2. [engineer-verified: "Ok I think the recommended option looks good to me"] The option was the scoping design Context's `Ask:` line describes. Rows 13, 16, 17 and 19 replaced its table relabelling and name hiding.
3. [engineer-verified: "I'm now wondering what the benefit of this default redaction is at all."] The engineer reopened their earlier "Decision already made: redact by default, with --no-redact as the opt-out. Do not reopen it.", so that quote no longer binds this plan.
4. [engineer-verified: "One shared --no-redact refusal helper; the issue names resolve_scan_roots in transcript_analysis/scope.py as its home."]
5. [engineer-verified: "Backstop in both resolvers (Recommended)"]
6. [engineer-verified: "Removing --redact is a breaking flag change and needs a CHANGELOG.md Migration note."] No flag is removed now, so this binds nothing directly.
7. [engineer-verified: "Split into more than one PR if the plan says so, and say where the split is."]
8. [engineer-verified: "Tests use synthetic fixtures only. No output from a real multi-root run goes into the plan, a test, or a PR body."]
9. [engineer-verified: "re-resolve every cited site by symbol, and audit each sibling subcommand for the same unredacted-output shape instead of trusting the list."] Line numbers here are at `b7129175`, and every dispatch re-resolves them by symbol. Rows 30 and 31 are the audit.
10. [engineer-verified: "transcript-analysis should NOT redact free text because it's useful for analysis and experimentation."] An identifier inside free text prints as recorded, so no listing is publish-safe as printed.
11. [engineer-verified: "Pool under --this-repo (Recommended)"] Selected after the engineer wrote "Sometimes for my own repos, I will use multiple claude accounts for the same branch".
12. [engineer-verified: "One rule with --all-accounts (Recommended)"] The question named the seven earlier commands plus `audit-routing` and the four sample commands, and said the rule drops all new relabelling.
13. [engineer-verified: "Narrow the three (Recommended)"] `buckets`, `duration` and `struggle` join the narrowed commands.
14. [engineer-verified: "Narrow to active account (Recommended)"] `skill-invocation --projects GLOB` narrows instead of relabelling its skill names.
15. [engineer-verified: "Drop the flag (Recommended)"; "Keep pooling for samples only"] Row 12's question said it replaces both, so neither binds this plan.
16. [engineer-verified: "Drop it (Recommended)"] `review-trace`'s timeline keeps printing untracked hook and agent-type names.
17. [engineer-verified: "Make it a real opt-in (Recommended)"; "Opt-in only"; "One label per name (Recommended)"] `reviewer-yield --redact` relabels untracked agent types with one label per name, and nothing relabels there without it.
18. [engineer-verified: "Keep --redact there (Recommended)"] `audit-routing` keeps `--redact` as it is today, at every root count.
19. [engineer-verified: "I honestly don't think it's that big of a deal"; "One rule with --all-accounts (Recommended)"] `audit-routing` relabels nothing without `--redact`, at any root count. The first quote answered what `audit-routing` should do above one account.
20. [engineer-verified: "Keep the banner (Recommended)"] `audit-routing-samples` and `handoff-signal-response --sample` print the existing do-not-publish line on stderr when they read more than one root. The session's note, not the engineer's: on `handoff-signal-response --sample` that line overstates, since session IDs print as `session-N` by default and what prints raw is excerpt and `forward_context` text. The existing line stays.
21. [engineer-verified: "No, drop PR 4 (Recommended)"] `subagents`, `subagent-mix` and `review-round-cost` keep their behavior, raw at one root, and gain no `--no-redact`.
22. [engineer-verified: "Withdraw both (Recommended)"] `sessions --paths` needs no `--no-redact`, and `user-input` keeps `--redact`.
23. [engineer-verified: "Leave it out (Recommended)"; "Leave them out (Recommended)"] `post-crash-sessions.py`, `token-analyzer.py` and `analyze-context.py --top` are unchanged.
24. [engineer-verified: "Leave paths raw"] `review-trace`'s per-session path line stays raw above one root, under `--this-repo` or `--all-accounts`.
25. [unverified: the session's reading recorded in Context] "Yes, disclose (Recommended)", "Require cwd in this repo (Recommended)", "Keep the refactor (Recommended)", "Apply it to all six (Recommended)" and "Hide untracked names (Recommended)" shaped the relabelling that rows 13, 16 and 17 replaced. They apply to nothing beyond row 17's opt-in.
26. [engineer-verified: "Proceed anyway"; "Keep it whole (Recommended)"] "Proceed anyway" was selected on plan-review's question whether to split a plan projecting more than 400 changed lines into smaller PRs or proceed. "Keep it whole (Recommended)" was selected on whether PR 1 stays whole at a projected 900 changed lines or splits into seven commands then five. The current projection is under Projected diff. "Proceed anyway" was selected again at about 1,350 for PR 1.
27. [engineer-verified: "Check which session holds GH-1116 (the transcript-analysis decomposition) and which files it owns before choosing where edits land."] Context's state check found GH-1116 closed with no open work, so every edit lands under `transcript_analysis/`.
28. `resolve_scan_roots` (`scope.py:472-506`) returns the top-level `--config-dir`'s `projects/` before it reads the declared-roots file (`:493-495`). It has 26 call sites in the package. Twelve of them are the narrowed commands'. Two more sit outside the package, `analyze-context.py:295` and `token-analyzer.py:208`. [verified: read; grep of `resolve_scan_roots(`]
29. The narrowed commands' sites at `b7129175`. [verified: reads]
    - `review_trace.py`: resolver `:792`, `--deny-summary` header `:800`, timeline header `:822`, raw path `:859`.
    - `judgment_pair.py`: resolver `:35`, headers `:158` (zero match), `:169` (`--out` file) and `:172`, raw block `:145-152`.
    - `sessions.py`: resolver `:38`, stderr header `:42`, raw path `:44`.
    - `skill_invocation.py`: resolver `:93`, inlined multi-root `--projects` branch `:96-106`, header `:164`.
    - `buckets.py` `:18`, `:20` and `:71`; `duration.py` `:23`, `:25` and `:55`; `struggle.py` `:49`, `:51` and `:83`, each a resolver, a header and a raw branch cell.
    - `audit_routing.py`: `cmd_audit_routing`'s resolver `:82`, header `:89` and raw session and project cells `:246-247`; `cmd_audit_routing_samples`' resolver `:612` and stderr header `:615`.
    - `turn_shape.py`: `cmd_turn_shape_samples`' resolver `:285`, stderr header `:288` and raw `session=` line `:309`; `cmd_turn_shape_holdout_samples`' resolver `:345`, stderr header `:348` and raw `session=` line `:382`.
    - `handoff_signal_response.py`: resolver `:560`, `sample_n` read `:562`, refusal `:565-572`, header `:584`, and a benchmark pass over the same `roots` at `:600-604`.
30. Sibling audit of the 46 subcommands `add_parser(` registers. [verified: reads and grep]
    - Narrowed here: the twelve (row 29).
    - Relabel above one root: `subagents`, `subagent-mix` and `review-round-cost` (`_root_scoped_display_label` call sites).
    - Active account only: `period-cost`, `cost-counts`, `read-cost`, `routing-guard`, `user-input`, and `review-cost-by-size` without `--all-accounts` (`docs/transcript-analysis.md:78-86`).
    - Redacted aggregates: the nine `--no-redact` family members besides `handoff-signal-response`.
    - Typed input only: `fail-seq` (`--branches` is required, `fail_seq.py:129`) and `friction-count`, which reads one typed transcript path (`friction_count.py:284`).
    - `reviewer-yield` prints every agent type raw, pooled (row 38).
31. The rest of row 30's 46. [verified: this session's reads of `commit_gate.py:72` and `:150-183`, `author_outcome.py:953-971`, `audit_routing.py:554-592`, `spend_over_threshold.py:76-97`, `cost_ledger.py:351-396`, `instrument_authoring.py:353-391`, `pr_cost.py:607-656` and `:981`, and `pr_cost_export.py:94-124`; round-3 staff-backend-engineer's reads of `skill-pair`, `workstream-cost`, `pr-link` and `turn-shape`; round-3 staff-product-engineer's and staff-backend-engineer's `cost-trend` traces; round-3 ciso-reviewer's `--deny-summary` trace]
    - `pr-link` prints only typed branches (`pr_link.py:42`, `:148`).
    - `pr-cost` prints repo and branch labels through `redaction._assign_root_scoped_redact_label` (`pr_cost.py:621`, `:655`, `:981`). `pr-cost-export` relabels every identifying row field (`pr_cost_export.py:117-124`).
    - `cost-trend` always redacts: it reads `no_redact` through `getattr` but registers no such flag (`cost.py:1203-1225`).
    - `skill-pair`, `workstream-cost` and `turn-shape` print counts, ages and weekly figures, with no session ID or scan-derived label.
    - `commit-gate` prints ISO-week and permission-mode buckets with counts. `author-outcome` prints the typed `--agent` and outcome counts. `audit-routing-shape` prints bucket tables. `spend-over-threshold` prints weekly dollar figures. `cost-ledger` prints ledger rows and week strings. `instrument-authoring` prints call-shape counts. None prints a scan-derived label.
    - `review-trace --deny-summary` bounds hook names through `denials._denial_hook_label`.
32. `_root_count_desc` (`scope.py:635-657`) returns its absent and unreadable wordings first, and otherwise `declared but contributed no additional root`. `declared_roots_file_state` returns `present` for an empty, comments-only or all-invalid file (`_config_dir.py:67-70`). [verified: reads]
33. Under the top-level `--config-dir` with a present roots file, every subcommand's one-root header prints `declared but contributed no additional root`, though the run never read the file. [verified: reads of `scope.py:493-495` and `:650-657`]
34. `cmd_audit_routing` reads `--redact` at `audit_routing.py:77` and builds the redact map only under it (`:91`). Without it, `:246-247` print raw session IDs and project labels from every root. Under it, `_build_redact_map` returns flat `private-project-N` labels at one root and `account-<K>/private-project-N` above one (`redaction.py:122-163`). [verified: reads]
35. `_root_index_for_path` (`scope.py:870-904`) resolves the path and raises an uncaught `AssertionError` for a project directory symlinked outside every root. Its message names `cost:` whichever command raised it (`:900-903`). `cmd_audit_routing` calls it under multi-root redaction (`audit_routing.py:120-122`). The multi-root iterators yield the unresolved `root/<project dir>/<file>` path (`scope.py:359`, `:418`, `:465-466`). [verified: reads]
36. `_build_redact_map` reads every root's transcripts with subagents (`redaction.py:75-99`, `:153-165`). `docs/transcript-analysis.md:100` records about 16 s per root for a subagent-inclusive scan on one workstation. [verified: reads]
37. `audit-routing-samples` prints no banner, which `turn_shape.py:277-280` notes. `handoff-signal-response` prints one only under `--no-redact` (`handoff_signal_response.py:579-581`), while its `--sample` cards print raw excerpt text (`:480-481`). Both turn-shape sample commands print the banner on both streams (`turn_shape.py:302-303`, `:375-376`). [verified: reads; grep of `_DO_NOT_PUBLISH_BANNER`]
38. `reviewer-yield --redact` is a documented no-op (`reviewer_yield.py:667-672`, `:783-790`), and both tables print `AgentType` raw from `agg` (`:719-757`). `redaction._repo_tracked_agent_type_names()` (`redaction.py:262-303`) returns git-tracked agent stems plus the built-ins, and the built-ins alone when git fails. [verified: reads]
39. Ten family modules inline the `--no-redact` refusal. [verified: grep of `refused when more than one root`; reads]
    - Nine say `(--config-dir was given)`, as does `_resolve_cost_roots` (`scope.py:800-806`).
    - `handoff_signal_response.py:565-572` and its help (`:659-664`) advise `--this-repo`, which never removes a root.
    - The nine besides `handoff-signal-response` are in `_SUBCOMMANDS_REFUSING_TOP_LEVEL_CONFIG_DIR` (`scope.py:702-708`) and resolve through `_resolve_cost_roots`, so they cannot narrow below the declared roots.
40. No test pins the refusal wording. `test_transcript_cost.py:789-797` expects `_resolve_cost_roots` itself to exit 2 with `--no-redact` on stderr, which the backstop keeps. [verified: grep of the old wording; read]
41. I1 is open: `_read_scope_report` merges each session into `per_account[idx]` by scan-order index (`read_scope.py:453`), and `_print_read_scope_report` labels entry `idx` as `account-{idx + 1}` (`:580`). [verified: read]
42. [unverified: carried from the prior revision's grep and read and round-2 staff-backend-engineer's answers; not reopened] Only the ten family modules register `--no-redact`, `analyze-context.py` and `token-analyzer.py` never mention it, and argparse stores the subcommand name as `subcommand` (`cli.py:116`).
43. `.claude/rules/transcript-analysis-tests.md` splits a test file that would cross the 1,000-line limit at a named seam. `test_transcript_scope.py` has 913 lines, `test_transcript_handoff_signal_response.py` 904, `test_transcript_scope_scan.py` 773 and `test_transcript_reviewer_yield.py` 2,307. `test_transcript_package_module_prefixes.py` fails a package-importing test file missing from `TEST_FILES` (`:62`, `:528-537`). [verified: rule file; line counts by grep; read]
44. Pins the edits keep. [verified: reads]
    - `test_skills.py:3180-3198` pins the `transcript-analysis/SKILL.md:20` sentence verbatim.
    - `test_transcript_analysis_multi_root_scope.py:500-548` pins the absent-state literal in both transcript skills, and transcript-narrative's `SESSIONS SOURCES` sentence.
    - `test_nudge_transcript_toolkit.py:217` requires "union" in the hook's context.
    - `test_transcript_scope.py:903-908` pins the shared `--this-repo` help.
45. Tests that narrowing changes. [verified: reads; grep of `_two_declared_roots(` and `TRANSCRIPT_CONFIG_DIRS_FILE` over the narrowed commands' test files; read of `test_transcript_scope.py:680-695`]
    - In `test_transcript_analysis_multi_root_scope.py`:
      - `TestRootsThreadingSpy`'s rows for the seven narrowed `_UNCONDITIONAL_HEADER_CASES` members (`:77-126`, `:298-330`);
      - its `review-trace` and `skill-invocation` glob tests (`:332-380`);
      - the `audit-routing-samples` JSON test (`:458-475`);
      - the `judgment-pair --out` test (`:477-497`).
    - In `test_transcript_scope.py`: the declared-root `buckets` test (`:704-719`), and the `skill-invocation` multi-segment test (`:680-695`). That test's one-argument `resolve_scan_roots` stub (`:691`) raises `TypeError` on M1's keyword, so the stub is what changes.
    - The args factories for `audit-routing`, `review-trace`, `judgment-pair`, `skill-invocation` and `audit-routing-samples` build fixed-key namespaces with no `all_accounts` parameter, and `TestRootsThreadingSpy`'s spies take `(*a, **k)`, so they survive the keyword. This bullet is carried from round-3 staff-backend-engineer's and staff-sdet's reads.
    - `test_transcript_audit_routing.py:349-370`, whose `--redact` run expects two accounts' labels.
    - `test_transcript_handoff_signal_response.py:54-64`, whose `sample=5` case expects a refusal over two declared roots.
46. Callers that run a narrowed command without `--this-repo`. [verified: reads; grep of the twelve commands' names outside tests, plans and dated records; round-3 staff-product-engineer's grep]
    - `transcript-narrative/SKILL.md:30`, `:53` and `:68`, and its `audit-routing --redact` advice at `:87`.
    - `error-mode-analysis/SKILL.md:145`.
    - `transcript-analysis/SKILL.md:41`, `:58`, `:127`, `:140` and `:143`, its decision-table rows at `:30`, `:32`, `:33`, `:36` and `:39`, and its `audit-routing --redact` advice at `:103`. M8's disposition for the examples covers the decision-table rows.
    - `token-analyzer.py:188`, which names `audit-routing` in a printed hint.
    - `ready-for-review/SKILL.md:113` passes `--this-repo`.
47. Agent-facing text the narrowing makes stale. [verified: reads]
    - `nudge-transcript-toolkit.sh:6-7` and `:126`, `docs/hooks.md:212`, `README.md:81` and `ready-for-review/SKILL.md:103`.
    - `docs/transcript-analysis.md:53`, `:55`, `:100`, `:101`, `:2362`, `:2618` and `:2675`.
    - The narrowed commands' `--this-repo` bullets in `docs/transcript-analysis.md` at `:123`, `:186`, `:211`, `:495`, `:604`, `:640`, `:2534`, `:2622` and `:2651`, each reading "instead of a machine-wide glob", and `:2355`, which calls the startup-burn benchmark "this one corpus-wide figure".
    - `docs/private-project-redaction.md:186`, which lists "any subcommand at its default machine-wide scope" as a wider-corpus read, and `error-mode-analysis/SKILL.md:27`, which offers `--projects GLOB` as a cross-repo scope.
    - `handoff_signal_response.py`'s `--no-redact` help (`:659-664`) and `cmd_turn_shape_samples`' docstring (`turn_shape.py:277-280`).
    - Separately, `transcript-narrative/SKILL.md:84` already says only `audit-routing` has `--redact`, which `user-input --redact` contradicts (row 22).
48. `scope.py` has 1,161 lines, above the 1,000-line target that nothing enforces yet, and this plan grows it by about 60. [verified: line count by grep]
49. A `SKILL.md` commit needs `/skill-review`, which a hook enforces. [verified: `.claude/rules/review-pipeline-dispatch.md`]
50. [engineer-verified: "--this-repo is fine"] `transcript-narrative`'s Step 2 `sessions --paths` gains `--this-repo`, which bounds it to this repository as Steps 1 and 4 already are.
51. `pr-cost` and `review-cost-by-size` already register `--all-accounts` (`pr_cost.py:1220-1227`, `review_cost_by_size.py:333-340`). Each reads every declared account in one run, and neither calls a shared helper. Both accept the flag beside `--this-repo`, and `review-cost-by-size` requires `--this-repo` (`:276-284`). `review-cost-by-size`'s flag prints a private-view banner on both streams (`:58-62`, `:286-290`). [verified: reads; grep of `--all-accounts` in the package]
52. `_add_project_scope_args` puts `--projects` and `--this-repo` in one mutually exclusive group (`scope.py:509-521`). Eleven of the twelve narrowed subcommands call it, and `skill-invocation` builds its own group (`skill_invocation.py:265-277`). [verified: read; grep of `_add_project_scope_args(`]
53. `cmd_turn_shape_holdout_samples` shuffles every candidate in scope with a fixed default seed and pages them by `--offset` (`turn_shape.py:358-361`). A different scope therefore yields a different shuffled population, and an earlier pass's pages no longer line up. [verified: read]
54. [engineer-verified: "Help text only (Recommended)"] Selected on how a pooled `--all-accounts` run marks itself, given that `review-cost-by-size --all-accounts` prints a DO NOT PUBLISH line. The `--all-accounts` help and the docs bullet are the marker beside the `N roots` clause of M2's header, and no runtime marker is added beyond M4's two banners. Context records a later "Banner on --all-accounts only (Recommended)" answer, which the engineer then withdrew.
55. [unverified: the session's default, not an engineer answer] On the twelve narrowed subcommands, the top-level `--config-dir` together with `--all-accounts` exits 2 with one stderr line naming the contradiction, in place of reading the `--config-dir` root alone.
56. `cli.main()` exits 2 on the top-level `--config-dir` for every member of `_SUBCOMMANDS_REFUSING_TOP_LEVEL_CONFIG_DIR` before it dispatches (`cli.py:171-199`), and `pr-cost` and `review-cost-by-size` are members (`scope.py:702-708`). A check placed after that block therefore reaches only the twelve narrowed subcommands among `--all-accounts` registrants. [verified: reads]
57. `_add_project_scope_args` has 40 call sites, and only `review-cost-by-size` passes `this_repo_help` (`review_cost_by_size.py:326-332`). `read-cost` and `cost-counts` take the default help and read the active account alone (`read_cost.py:390`, `subagent_mix.py:528`). `pr-cost` refuses more than one root without `--all-accounts`. [verified: grep of `_add_project_scope_args(`; round-3 staff-product-engineer's reads of `read_cost.py`, `subagent_mix.py` and `pr_cost.py`]
58. [engineer-verified: "Add the validator (Recommended)"] Selected on whether PR 1 refuses an absolute `--projects` value, leaving `user_input.py` to the follow-up issue. The placement is a plan-architect consult's recommendation, not the engineer's answer. A guard in `corpus.iter_sessions` runs only on the first `next()`, after `audit-routing --redact` has built its redact map. An argparse `type=` reaches 40 registrants, breaks `TestProjectsFlagHasNoArgparseType` and needs a parser-driven test layer. A runtime check inside `_resolve_project_scope` runs before every scan and redact-map build, since each caller resolves scope first (`audit_routing.py:89` before `:92`; `cost.py:641` before `:685`). [unverified: that `Path(value).anchor` refuses every value `Path.glob` rejects on Pythons older than the 3.14 CI interpreter]

## Critical files

`TA/` means `claude/.claude/scripts/transcript_analysis/`, and `T/` means `claude/.claude/scripts/tests/`.
- Each PR is one phase and one `code-writer` dispatch. A PR's docs and skills quote the header literal and behavior its code defines, so a second dispatch would restate that background.
- This plan file is committed in PR 1.
- Every dispatch runs the Verification section's commands.
- Each narrowed command's module takes M1's flag threading and M3's `_add_all_accounts_arg` call. Each of the eleven that call `_add_project_scope_args` also takes M8's `this_repo_help`. A file item below adds only what is specific to that file.

**PR 1, one code-writer dispatch.** Files:
- `TA/scope.py`:
  - adds M1's `_narrows_to_active_account`, M3's `_add_all_accounts_arg` beside `_add_project_scope_args`, and M8's `_POOLED_THIS_REPO_HELP`;
  - `resolve_scan_roots` gains M1's `active_account_only` keyword and one docstring sentence on it;
  - `_root_count_desc`, `_resolved_scope_header` and `print_resolved_scope` gain M2's keyword;
  - adds `_refuse_absolute_projects_glob(projects_glob, subcommand)`, which exits 2 on stderr with `<subcommand>: --projects: must be a glob under each root's projects/ directory, not an absolute path; --this-repo scopes to this repository` when `Path(projects_glob).anchor` is non-empty. It is a syntactic check with no `resolve`, `expanduser` or stat call, and `_resolve_project_scope` calls it after its `--this-repo` return and before its root-count branch, so it refuses at every root count.
- `TA/cli.py`: `main()` refuses `--all-accounts` beside the top-level `--config-dir` after its existing refusal block (M3).
- `TA/review_trace.py`, `TA/buckets.py`, `TA/duration.py` and `TA/struggle.py`: the shared edits only.
- `TA/judgment_pair.py`: `cmd_judgment_pair` passes M1's local to all three of its header calls.
- `TA/sessions.py`: `cmd_sessions`' docstring says it reads the active account unless `--this-repo`, `--all-accounts` or the top-level `--config-dir` sets the scope.
- `TA/skill_invocation.py`:
  - `cmd_skill_invocation` reads `projects_arg` before resolving roots;
  - its multi-root `--projects` branch (`:96-106`) stays, for `--all-accounts`;
  - the `--projects` help adds `An explicit glob reads the active account only, unless --all-accounts.`;
  - `cmd_skill_invocation` calls `_refuse_absolute_projects_glob` inside `if projects_arg:`, before its root-count branch;
  - its own `--this-repo` help stays, since it builds its own group (row 52).
- `TA/audit_routing.py`: `cmd_audit_routing_samples` prints the banner on stderr after its header above one root (M4), and `--redact` is unchanged.
- `TA/turn_shape.py`: `cmd_turn_shape_samples`' docstring says `audit-routing-samples` prints the banner on stderr above one root.
- `TA/handoff_signal_response.py`:
  - `cmd_handoff_signal_response` reads `sample_n` before resolving roots;
  - it prints the banner on stderr when `--sample` runs above one root (M4);
  - the `--no-redact` help ends `Refused when more than one root is in scope; a --sample run without --this-repo or --all-accounts reads the active account alone.` in place of its `--this-repo` advice.
- New `T/test_transcript_scope_active_account.py`:
  - `_narrows_to_active_account` is true with none of the three set, and false under `this_repo=True`, under `all_accounts=True` and under a set `config_dir`;
  - with `scope.declared_transcript_roots` patched to raise, the resolver with the keyword returns the active root alone;
  - the resolver without the keyword returns both roots over `_two_declared_roots`;
  - a top-level `config_dir` wins over the keyword;
  - `_root_count_desc` with the keyword returns M2's clause for a roots file that lists a root and for an empty one;
  - the absent and unreadable wordings are unchanged under the keyword, and two roots still read `2 roots`;
  - on a parser `_add_project_scope_args` built, `_add_all_accounts_arg` parses `--all-accounts` to `parsed.all_accounts is True` and its absence to `False`, and raises no mutual-exclusion error beside `--this-repo` or beside `--projects GLOB`.
- New `T/_turn_shape_helpers.py`: `_turn_shape_samples_args` and `_turn_shape_holdout_samples_args` move here from `T/test_transcript_turn_shape.py`.
- `T/test_transcript_turn_shape.py`: imports the two moved factories from `_turn_shape_helpers.py`.
- `T/_handoff_nudge_helpers.py`: gains `_handoff_signal_response_args`, moved from `T/test_transcript_handoff_signal_response.py`, and one two-root session builder that writes a signal and an excerpt per root. The listing-scope table and that test file's new tests share the builder.
- New `T/test_transcript_analysis_listing_scope.py`:
  - One case table covers the twelve narrowed commands. Each row carries its own record builder, its args factory from `conftest.py` or a family helper module, and its header's stream: stderr for `sessions`, `audit-routing-samples`, `turn-shape-samples` and `turn-shape-holdout-samples`, and stdout for the rest.
  - Each builder writes both roots' sessions under one shared project slug, and puts a distinct 8-character alphanumeric sentinel per root in a field its command prints raw:
    - the session file stem for `review-trace`, `judgment-pair`, `sessions`, `audit-routing`, `audit-routing-samples`, `turn-shape-samples` and `turn-shape-holdout-samples`;
    - the skill name for `skill-invocation --projects '*'`;
    - the branch for `buckets`, `duration` and `struggle`;
    - the excerpt text for `handoff-signal-response --sample`.
  - A default run over `_two_declared_roots` prints the active root's sentinel, prints the declared root's on neither stream, and carries M2's clause on the row's header stream.
  - The same run with `all_accounts=True` prints both sentinels and `2 roots`.
  - The same run with `this_repo=True` and `_this_repo_slugs` set to the shared slug prints both sentinels and `2 roots`. The `skill-invocation` row runs it with no `projects`, and with `scope._repo_scoped_project_slugs` patched to return that slug.
  - `buckets` with both `this_repo=True` and `all_accounts=True` prints the header and rows the `this_repo=True` run prints.
  - `buckets` with `this_repo=True`, over two roots that each hold a session on one shared branch, prints one row for that branch with `Sess` 2.
  - A `judgment-pair` run matching nothing prints M2's clause above `No judgment pairs found.`.
  - Under a set top-level `config_dir`:
    - `buckets` prints the `config_dir` root's sentinel and a header without `active account only`;
    - the same run with `this_repo=True` prints a header without `active account only`.
  - Pooled modes over `_two_declared_roots`:
    - `review-trace --deny-summary` prints `2 roots` and `scanning root 2/2...`;
    - `handoff-signal-response`'s aggregate run prints `2 roots` and `scanning root 2/2...`, and no banner;
    - `skill-invocation` without `--projects` prints `2 roots`.
  - One banner test each for `audit-routing-samples` and `handoff-signal-response --sample`:
    - a default run's stdout parses as JSON and holds a record carrying the active root's sentinel, and its stderr carries no banner;
    - runs under `all_accounts=True` and under `this_repo=True` print the banner on stderr, and their stdout still parses as JSON, below the header line for `handoff-signal-response`.
- `T/test_transcript_analysis_multi_root_scope.py`:
  - each `_UNCONDITIONAL_HEADER_CASES` row gains a `narrowed` flag, true on `buckets`, `struggle`, `duration`, `judgment-pair`, `sessions`, `audit-routing` and `audit-routing-samples`. `TestRootsThreadingSpy`'s parametrized test sets `all_accounts=True` on a flagged row's built namespace, so it still pins that scope and header receive one multi-root list;
  - `test_review_trace_scope_and_header_receive_identical_multi_root_list` and `test_skill_invocation_glob_scope_receives_the_multi_root_list_as_is` set `all_accounts=True` for the same reason;
  - `test_audit_routing_samples_stdout_still_parses_as_json_across_declared_roots` sets `all_accounts=True` and also asserts the banner on stderr;
  - `test_judgment_pair_out_file_still_one_header_line_across_declared_roots` sets `all_accounts=True`, under the name `test_judgment_pair_out_file_one_header_line_under_all_accounts`;
  - a new `test_judgment_pair_out_file_header_names_the_active_account_read` asserts that line 1 is `JUDGMENT PAIR SOURCES (*; 1 root (active account only; --this-repo or --all-accounts also reads ~/.claude/transcript-config-dirs))` and the file holds one block;
  - `TestSkillFilesQuoteRootCountDescLiteral` gains an assertion over an empty roots file. It derives `_root_count_desc([root], active_account_only=True)`, asserts the result differs from the absent-state literal, and asserts the result appears whole in `transcript-analysis/SKILL.md`.
- `T/test_transcript_scope.py`:
  - `test_skill_invocation_multi_root_rejects_a_multi_segment_projects_value_at_runtime` drops its one-argument `resolve_scan_roots` stub. Over `_two_declared_roots` with the real resolver, `projects="a/b"` with `all_accounts=True` exits 2 with `--projects` on stderr. The same value without the flag exits 0 over the active root alone;
  - `test_sessions_found_via_declared_root_despite_nonexistent_projects_dir` runs `buckets` with `all_accounts=True`;
  - a new test calls `_resolve_project_scope` with `projects="/abs/*"` over one root and asserts exit 2 with `--projects` on stderr and empty stdout, and the same call with `projects="*"` still returns its generator. On the base the absolute call returns a generator.
- `T/test_transcript_skill_invocation.py`: an absolute `--projects` over one root exits 2 with `--projects` on stderr. Then, over `_two_declared_roots` with a distinct skill name per root:
  - `--projects '*'` with `all_accounts=True` prints both skill names;
  - `--projects 'sub/<slug>'` exits 0 and counts a nested active-root session's skill;
  - `--projects '../../<declared-account>/projects/*'` prints `No skill invocations found.` and not the declared root's skill. The glob's parent, resolved from the active root, is the declared root's `projects/`.
- `T/test_transcript_audit_routing.py`:
  - `test_same_raw_label_under_two_roots_resolves_to_distinct_account_tokens` sets `all_accounts=True`;
  - a new test runs `redact=True, projects="/abs/*"` over one root with no declared-roots file and asserts exit 2 and no call to `redaction._build_redact_map`. On the base the map is built and `NotImplementedError` follows;
  - a new test runs `redact=True` over `_two_declared_roots` with no widening flag. A spy on `redaction._build_redact_map` records the active root alone. The active root's session prints with a flat `private-project-<N>` label and no `account-` prefix, and the declared root's project label does not print;
  - the same test's `this_repo=True` run, with slugs preset, prints `account-<K>/` prefixed labels.
- `T/test_transcript_handoff_signal_response.py`:
  - imports `_handoff_signal_response_args` and the two-root builder from `_handoff_nudge_helpers.py`;
  - `test_no_redact_refused_with_multi_root`'s `sample=5` case runs under `all_accounts=True` and under `this_repo=True` with `_this_repo_slugs` preset. Each asserts exit 2, `--no-redact` and `more than one root` on stderr, and empty stdout;
  - a new test runs `--sample 5 --no-redact` over `_two_declared_roots` with no widening flag, and asserts a normal return, the banner on both streams, the active root's raw session ID, and not the declared root's.
- `T/test_transcript_cli.py`:
  - a walk of `_subparsers_by_name(build_parser())` asserts that the set registering `--all-accounts` equals the twelve narrowed subcommand names plus `pr-cost` and `review-cost-by-size`;
  - a second walk asserts that the set whose `--this-repo` help equals `scope._POOLED_THIS_REPO_HELP` equals the eleven narrowed names besides `skill-invocation`. `TestAddProjectScopeArgsThisRepoHelp` (`test_transcript_scope.py:903-908`) keeps pinning the unchanged default;
  - over a seeded top-level `--config-dir`, each narrowed name with `--all-accounts` and any argument its parser requires exits 2 through `cli.main()`, with the refusal line on stderr and empty stdout. The same `buckets` argv without `--all-accounts` prints the seeded branch.
- `T/test_transcript_package_module_prefixes.py`: `TEST_FILES` gains the two new test files.
- `claude/.claude/hooks/nudge-transcript-toolkit.sh`: the `:126` context and the `:6-7` comment say the aggregate subcommands union declared roots by default and `sessions --paths` does under `--this-repo` or `--all-accounts`. Both keep the word "union", which `test_nudge_transcript_toolkit.py:217` checks.
- `docs/hooks.md`: `:212` says the context names how the toolkit unions declared roots.
- `README.md`: `:81`'s exception clause points to `docs/transcript-analysis.md` § "Corpus scope: the declared-roots file" in place of its two examples.
- `docs/scripts.md`: one sentence under `token-analyzer.py`'s bullet says `analyze-context.py --top` and `token-analyzer.py` print project names and session IDs from every declared account.
- `docs/transcript-analysis.md`:
  - `:53` says the default outside `skill-invocation` reads every project, and defers to "Corpus scope: the declared-roots file" for which accounts;
  - `:55` says the timeline reads the active account's projects by default and every declared account under `--this-repo` or `--all-accounts`, and that `--deny-summary` pools by default;
  - the subdirectory-fallback bullet (`:60-66`) says the fallback glob reads the active account only on a narrowed command, and adding `--all-accounts` reads it in every declared account. It also says an absolute `--projects` value exits 2 and `--this-repo` is the route to this repository;
  - the active-account list (`:78-86`) gains one bullet for the narrowed commands, whose sub-bullets:
    - name the twelve narrowed commands;
    - state M3's combination rules with `--this-repo` and `--projects GLOB`;
    - say the top-level `--config-dir` beside `--all-accounts` exits 2;
    - name the three pooled modes, where `--all-accounts` changes nothing;
    - say the `--all-accounts` output carries every declared account's raw names, paths and text and is not for publication, citing `docs/private-project-redaction.md` § "A wider corpus goes to the owner, never into a public artifact";
  - the header paragraph (`:90`) gives M2's clause;
  - `:100`'s narrowing-control sentence says the narrowed commands already read one root by default;
  - `:101` says `audit-routing --redact` reads every declared root's transcripts only under `--this-repo` or `--all-accounts`;
  - the three-bucket paragraph (`:103`):
    - replaces the narrowed commands in its "every other subcommand" list with a pointer to the active-account list;
    - moves `subagents` beside `subagent-mix` and `review-round-cost`;
    - says `audit-routing-samples` and `handoff-signal-response --sample` print the banner on stderr above one root;
    - says free text prints raw under every flag;
  - each narrowed command's flag list:
    - gains an `--all-accounts` bullet that points to "Corpus scope: the declared-roots file". On `review-trace`, `skill-invocation` and `handoff-signal-response` it adds that the flag changes nothing for the pooled mode;
    - its `--this-repo` bullet at `:123`, `:186`, `:211`, `:495`, `:604`, `:640`, `:2534`, `:2622` and `:2651` says `in every declared account` in place of `instead of a machine-wide glob`;
  - `skill-invocation`'s `--projects` bullet (`:453`) says an explicit glob reads the active account only, unless `--all-accounts`;
  - the startup-burn benchmark paragraph (`:2355`) says the benchmark covers the same scope as the rows it judges, in place of "this one corpus-wide figure";
  - `handoff-signal-response`'s `--sample N` bullet (`:2363`) says a default run ranks its top N and computes each card's `exceeds_startup_burn_benchmark` over the active account only, so its cards are not comparable to a census run's benchmark without `--all-accounts`;
  - `handoff-signal-response`'s `--no-redact` bullet (`:2362`) replaces its `--this-repo` advice with M8's one-root note;
  - `turn-shape-samples`' banner paragraph (`:2618`) says `audit-routing-samples` prints the banner on stderr above one root;
  - `turn-shape-holdout-samples`' "Stable population" bullet (`:2675`):
    - says one pass keeps its `--projects`, `--this-repo` and `--all-accounts` flags identical across invocations, since they set the population `--offset` pages through;
    - says a pass over every declared account passes `--all-accounts` on every page (row 53).
- `docs/private-project-redaction.md`: `:186` names `--all-accounts` and `--this-repo` on the narrowed commands as wider-corpus reads beside `pr-cost --all-accounts`. It points to `docs/transcript-analysis.md` § "Corpus scope: the declared-roots file" for the list, and keeps "any other subcommand at its default machine-wide scope".
- `claude-skills/skills/transcript-analysis/SKILL.md`:
  - a new paragraph after the pinned `:20` sentence:
    - says a header reading `1 root (active account only; --this-repo or --all-accounts also reads ~/.claude/transcript-config-dirs)`, quoted whole, covered the active account only;
    - says to widen a run, add `--all-accounts` to the same command;
    - says `--this-repo` replaces `--projects` and bounds the run to this repo's live worktrees;
    - says widening is for a question that needs accounts beyond the active one, not a routine rerun;
  - `:107` says the `*` default covers the active account only on the subcommands `docs/transcript-analysis.md` § "Corpus scope: the declared-roots file" lists;
  - `:108`:
    - names `review-trace`'s timeline, `buckets`, `struggle` and `duration` as reading the active account unless `--this-repo` or `--all-accounts`;
    - names `fail-seq`, `subagents`, `pr-link`, `review-trace --deny-summary`, `handoff-signal-response` without `--sample`, and `skill-invocation` without `--projects` as pooling every declared account;
    - keeps the top-level `--config-dir` as the one control that bounds a run to one named account.
- `claude-skills/skills/transcript-narrative/SKILL.md`:
  - `:30` runs `sessions --paths --this-repo --include-subagents` (row 50);
  - `:33`'s second sentence says the scope label then reads `this repo (...)` and the root-count clause says how many accounts were read. It also says Step 2 reads this repo's live worktrees only, and points to `docs/transcript-analysis.md`'s subdirectory-session fallback for sessions outside them. The pinned first sentence stays (row 44);
  - `:53` and `:68` run `duration --this-repo --branches <branch>`;
  - `:84` says no subcommand's `--redact` touches quoted prompts, in place of naming `audit-routing` as the one flag (row 47).
- `claude-skills/skills/error-mode-analysis/SKILL.md`:
  - `:25` says an unscoped run reads every project, not this repo's alone;
  - `:27` says a `--projects` glob on `buckets` or `review-trace` reads the active account only, and that adding `--all-accounts` to span every declared account is the user's call, not a routine fallback;
  - `:142` holds `--branches` and whichever scope Step 1 used constant across sub-windows: `--this-repo`, or `--projects '<glob>'` with or without `--all-accounts`;
  - `:145` runs `review-trace --this-repo --since <window-start> --until <window-end>`, Step 1's default scope.
- `CHANGELOG.md`: an `### Changed` entry with these Migration bullets:
  - a script that needs the previous output adds `--all-accounts`. The twelve narrowed commands, named, read only the active account's projects on a machine that declares more roots, and they exit 0 with fewer rows or smaller per-row figures. `review-trace` narrows only without `--deny-summary`, `skill-invocation` only with `--projects`, and `handoff-signal-response` only with `--sample`, and their other modes keep reading every declared account. `--all-accounts` reproduces the previous output, and also combines with `--projects GLOB`. `--this-repo` also reads every declared account, but bounds the run to this repository's sessions;
  - `sessions --paths` prints fewer paths on stdout and states why only in its stderr header, so a script reading stdout alone sees a shorter list with exit 0;
  - a default `audit-routing --redact` run reads one root, so its project labels lose their `account-<K>/` prefix. `--this-repo` or `--all-accounts` restores the prefixed labels;
  - `turn-shape-holdout-samples` shuffles a smaller population on a default run. A calibration pass paged with `--offset` that began before this change adds `--all-accounts` to every later invocation to keep its population;
  - a default `handoff-signal-response --sample` run ranks its top N, and computes each card's `exceeds_startup_burn_benchmark` and the `--format md` benchmark line, over the active account only. Its cards are therefore not comparable to a census run's pooled benchmark. `--all-accounts` restores the pooled ranking and benchmark;
  - `handoff-signal-response --sample --no-redact` now runs on a default invocation where it exited 2, and prints raw session IDs under the banner. It still exits 2 under `--this-repo` or `--all-accounts` above one root;
  - `audit-routing-samples` and `handoff-signal-response --sample` print a `DO NOT PUBLISH` line on stderr above one root, and stdout is unchanged;
  - the narrowed commands' one-root header clause reads `1 root (active account only; --this-repo or --all-accounts also reads ~/.claude/transcript-config-dirs)`, so a wrapper matching `declared but contributed no additional root` on a default narrowed run no longer matches. The three pooled modes and the widened or `--config-dir` runs still print the old text;
  - the four sample commands (`audit-routing-samples`, `turn-shape-samples`, `turn-shape-holdout-samples` and `handoff-signal-response --sample`) keep their row count but draw it from the smaller population, so a seeded run returns a different sample with exit 0. Their scope header is on stderr only, and `--all-accounts` re-draws over the old population;
  - an absolute `--projects` value exits 2 with one stderr line at every root count. On a default narrowed run at one root it raised an uncaught `NotImplementedError` (exit 1) under this change's narrowing, and above one root it exited 2 with the one-level message. A value containing `/` or `**`, or equal to `.` or `..`, exited 2 above one root and is accepted on a default narrowed run, and it still exits 2 under `--all-accounts`.

**PR 2, one code-writer dispatch.** Files:
- `TA/redaction.py`: adds M5's `_untracked_agent_type_labels`.
- `TA/reviewer_yield.py`: `cmd_reviewer_yield` prints both tables' `AgentType` through M5's map under `--redact`, and its docstring paragraph and `--redact` help describe the relabel.
- `TA/scope.py`: adds M6's `_refuse_no_redact_above_one_root` and `resolve_redaction`, both backstops, and `_resolve_cost_roots`' docstring sentence on the refusal.
- `TA/cost.py`: `_cost_report`'s inline block becomes the refusal call.
- `TA/cache_efficiency.py`, `TA/cache_rebuild.py`, `TA/context_composition.py`, `TA/context_distribution.py`, `TA/edit_format.py`, `TA/plan_boundary.py`, `TA/rearm_backtest.py` and `TA/handoff_signal_response.py`: each file's `redact` read and inline block become one `resolve_redaction` call.
- `TA/read_scope.py`: the same `resolve_redaction` swap, and `_read_scope_report` takes M6's I1 change.
- `T/test_transcript_redaction.py`: with `_repo_tracked_agent_type_names` patched, `_untracked_agent_type_labels` maps a tracked name to itself, two untracked names to `agent-type-1` and `agent-type-2` in sorted order, and a repeated name to one label.
- New `T/test_transcript_reviewer_yield_redaction.py`: with `_repo_tracked_agent_type_names` patched, a one-root `--redact` run prints a tracked type raw and an untracked type as `agent-type-1` in both tables, without its raw name, and the same corpus without `--redact` prints both raw.
- `T/test_transcript_reviewer_yield.py`: `test_redact_flag_is_true_no_op` is deleted.
- New `T/test_transcript_scope_no_redact.py`:
  - `resolve_redaction` returns `False` at one root with the flag, and `True` at two roots without the flag or with no `no_redact` attribute;
  - at two roots with the flag it exits 2, printing the line on stderr and nothing on stdout;
  - each resolver refuses two roots with the flag, and passes a namespace with no `no_redact`.
- `T/test_transcript_cli.py`: a walk of `_subparsers_by_name(build_parser())` asserts that the set registering `--no-redact` equals the ten family names, then runs each as `[name, "--no-redact"]` over `_two_declared_roots` through the file's parse-and-dispatch entry, asserting exit 2, the line on stderr and empty stdout.
- `T/test_transcript_read_scope.py`: given roots in scan order with the active root sorting last and a different read count per root, `_read_scope_report` prints the root that sorts first as `account-1`, first, with its own count.
- `T/test_transcript_package_module_prefixes.py`: `TEST_FILES` gains the two new test files.
- `docs/transcript-analysis.md`:
  - `:103` says `reviewer-yield --redact` relabels untracked agent types;
  - `reviewer-yield`'s `--redact` bullet (`:325`) states M5's rule, numbers the labels over untracked names alone, and says they are stable within one run, not across runs.
- `docs/transcript-analysis-architecture.md`: the inline-refusal sentences at `:550-552`, `:571-572` and `:583-584` name the shared helper.
- `claude-skills/skills/transcript-analysis/SKILL.md`: `:92` adds `reviewer-yield --redact`.
- `CHANGELOG.md`: an `### Changed` entry with these Migration bullets:
  - `reviewer-yield --redact` prints each agent type this repo does not track as `agent-type-<N>`, so a caller wanting raw names drops `--redact`. Output without it is unchanged;
  - the ten family subcommands' refusal reads `<subcommand>: --no-redact is refused when more than one root is in scope; drop --no-redact`, still on stderr with exit 2, so a wrapper matching `(--config-dir was given)` or `scope to a single` matches the new text instead;
  - `read-scope` numbers per-account rows by sorted resolved root path, so they renumber on a machine whose active root does not sort first.

Projected diff: about 1,650 changed lines, about 1,270 in PR 1 and 380 in PR 2. [unverified estimate]

## Verification

- In every dispatch, run `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py`, which is `CLAUDE.md`'s scoped test command and widens on its own when the diff needs it. Then run `scripts/venv-run.sh ruff check claude/.claude/scripts/`.
- PR 1 edits a hook, so its dispatch also runs `scripts/list-shell-files.sh | xargs -0 scripts/venv-run.sh shellcheck`.
- Write each behavior test before its change, and watch it fail on its PR's base. In PR 1:
  - the default-run cases print the declared root's sentinel;
  - the header cases find no M2 clause;
  - the banner tests find no banner on a widened run;
  - the `--all-accounts` registrant walk finds `pr-cost` and `review-cost-by-size` alone, and the `--this-repo` help walk finds no registrant;
  - the `--config-dir` refusal cases print argparse's unrecognized-argument error, not the refusal line;
  - the default `audit-routing --redact` case builds its map over both roots;
  - the unflagged multi-segment `--projects` case, the `sub/<slug>` case and the `..` case exit 2 on the multi-root one-level check;
  - the new helper and keyword tests find no such helper or keyword;
  - an absolute `--projects` over one root returns a generator from `_resolve_project_scope` instead of exiting 2, and `audit-routing --redact` with it builds the redact map before `NotImplementedError` is raised.
- In PR 2:
  - the `reviewer-yield` case prints the untracked name raw;
  - the `resolve_scan_roots` backstop case refuses nothing;
  - the I1 case numbers accounts by scan order.
- These PR 1 cases are guards that pass on the base, since the base pools every declared root and never prints M2's clause:
  - every `--this-repo` and `--all-accounts` widening case, the `audit-routing --redact` `this_repo=True` run included;
  - the pooled-mode cases;
  - the `buckets` both-flags case and the same-branch case;
  - the top-level `config_dir` header cases;
  - the `handoff-signal-response` refusal case under both widening routes;
  - the multi-segment `--projects` case under `all_accounts=True`, and the `'*'` control in the `..` test.
- No step runs `transcript-analysis.py` against a real transcript corpus. Evidence comes from the `_two_declared_roots`, `fake_projects` and `fake_config_dir_factory` fixtures, and PR bodies cite test names, never tool output (row 8, G2).
- Both PRs edit `SKILL.md` files, so each runs `/skill-review` before its commit (row 49). No PR edits an agent file.

## Out of scope

- `post-crash-sessions.py`, `token-analyzer.py` and `analyze-context.py --top` keep printing every declared account's project names and session IDs (row 23). PR 1's `docs/scripts.md` sentence states it for the last two, and Approach's follow-up issue carries all three.
- Under `--this-repo` or `--all-accounts`, `review-trace`'s `###` line and `sessions --paths` print each declared account's config-dir path (row 24 for `review-trace`, rows 12 and 22 for `sessions --paths`). `--this-repo` bounds the project directory, not that path segment. `review-trace` also reads every subagent file under an in-repo session, whatever repo the subagent worked in.
- `review-trace`'s timeline keeps printing hook and agent-type names raw, under any pooled run too (row 16).
- `reviewer-yield` keeps pooling every declared account by default, and prints untracked agent-type names raw without `--redact` (row 17).
- `audit-routing-samples` and `handoff-signal-response --sample` print raw prompt text, tool-call input paths and excerpts at one root with no banner on either stream, while both turn-shape sample commands print the banner on every run (row 20).
- `skill-invocation`'s default scope under `--include-subagents` reads subagent files under this repo's sessions in every declared account, so it can print another project's skill names. `docs/transcript-analysis.md`'s Limits already states this.
- `fail-seq` keeps pooling identically named branches across accounts, which leaves S7's `fail-seq` part open for Approach's follow-up issue. It prints only typed branch names.
- Under the top-level `--config-dir`, the one-root header keeps row 33's wording.
- `user_input.py` registers its own `--projects` and calls `corpus.iter_sessions` with the raw value, so an absolute value raises an uncaught `NotImplementedError` there. The command reads the active account only and has no pooling flag, so the defect is a crash and no leak. The plan does not cause it and the command is not narrowed, so it goes to Approach's follow-up issue.
- `review-loop-cost-audit/SKILL.md:35` takes a set difference between `buckets --this-repo`'s bare branch cell and `review-round-cost --this-repo`'s `account-<K>/` cell above one root. That mismatch predates this plan and is a follow-up.
- `subagents`, `subagent-mix` and `review-round-cost` keep their relabelling and disclose rules (row 21).
- `subagents`, `subagent-mix`, `review-round-cost`, `cost`, `cache-efficiency`, `cache-rebuild`, `edit-format`, `read-scope`, and `audit-routing --redact` under `--this-repo` or `--all-accounts`, keep aborting on a project directory symlinked outside every root (rows 18, 35). The abort's message names `cost:` whichever command raised it.
- `pr-cost` and `review-cost-by-size` keep their own `--all-accounts` registration and help text (row 51). `review-cost-by-size --all-accounts` prints a private-view banner on both streams, and the new flag on the twelve prints none (row 54).
- `ready-for-review/SKILL.md:103` keeps saying `review-trace` "defaults machine-wide". After PR 1 that default reads every project of one account, which is still not repo-scoped, so the sentence's instruction to pass `--this-repo` stays correct. The wording fix would cost a `/skill-review` of that skill.
- Several private projects in one account print raw at one root, since nothing redacts by default at one root (row 3).
- The top-level `--config-dir` and `--all-accounts` reach other accounts' directories and print them raw. Scoping here is output hygiene, not an access boundary. Transcript text an agent reads can ask it to rerun with `--all-accounts`, and only the flag's help and the docs say the output is not for publication (row 54). `--this-repo` also reads every declared account and says nothing of it.
- Text a hook echoes into its deny message prints raw with the rest of free text (row 10).
- The nine `_resolve_cost_roots` members of the `--no-redact` family still cannot narrow below the declared roots, so their `--no-redact` stays unusable on a machine that declares roots (row 39).
- Splitting `scope.py` below the 1,000-line target (row 48).
- Historical records are not edited: dated reports, `docs/case-studies/`, earlier plan files and past `CHANGELOG.md` entries.
- Round-2 reviewer asks declined:
  - A guard test classifying every subcommand (ciso-reviewer R2, staff-sdet R8). It needs a hand-kept 46-entry map restating rows 30 and 31, and declining it is the author's judgment. The residual: a new subcommand that prints raw text or paths pools by default, and every planned test stays green, since M1's keyword is opt-in and the CLI walks pin only the `--all-accounts` registrants and the pooled `--this-repo` help.
  - An allowlist over the 26 in-package `resolve_scan_roots(` call sites was weighed and declined, also as the author's judgment: it forces a pooled-or-narrowed entry per new caller but cannot check what that caller prints.
  - A publish notice on every text listing and `--out` file (ciso-reviewer R5). `docs/transcript-analysis.md:103` and `transcript-analysis/SKILL.md:92` and `:102` carry the raw-output limit (row 10). The header clause names only which accounts were read.
  - A test pinning that free text prints raw (ciso-reviewer R5). No code path redacts free text, so the test would pin the absence of a feature the engineer declined (row 10).
  - One banner rule across the six branch tables (ciso-reviewer R5). Row 54 settles it for widened runs: the `--all-accounts` help and the docs are the marker, and the banner stays where row 20 put it. `subagents`, `subagent-mix` and `review-round-cost` keep the banner they print today (row 21).
