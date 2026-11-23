# Ship Concise as the default output style for stow users

## Context

Goal: make Claude Code's built-in Concise output style the default for every user who installs claude-config via stow.

Ask: "I think I should change the output style of Claude Code to be concise, and I think that should be stowed to all users." Asked whether the stowed settings.json should force it as the default, the engineer selected the label "Force default (Recommended)". Asked how to handle an opt-out, the engineer answered that "the preferred output style is a user preference", not a repo preference, and that per-user overrides belong to separate settings base/override work, so no opt-out recipe ships with this change. The engineer then added the quality goal: "I'm hoping that the concise option will produce fewer words, make it easier for a human to read, but will keep like quality output." Asked how the README should describe overrides, the engineer selected the label "Point to Claude Code's own controls (Recommended)". Asked which extra measurements to run before the PR opens, the engineer selected the label "Opus rerun plus brief check (Recommended)". Reviewing the plan's additions, the engineer asked for a pre-merge check that needs no engineer time: "I would highly recommend replaying some conversations I had and then showing me side by side what the output looks like." Asked how much of the README subsection should stay, the engineer selected the label "Keep it minimal, no pointer (Recommended)".

Why now: the engineer finds that people across the board want less text from the AI. The Output styles page (https://code.claude.com/docs/en/output-styles) lists Concise as a built-in style (v2.1.237 or later), so the change needs no new style file. Selection is the `outputStyle` key, case-sensitive, and the page says a user-wide default belongs in `~/.claude/settings.json`, which stow populates from `claude/.claude/settings.json`.

Intended outcome: a stow user who pulls this change gets Concise responses in the main conversation by default, and the repo records why it ships a forced default and what it deliberately leaves to the separate settings base/override work.

## Approach

Add one line, `"outputStyle": "Concise"`, to the stowed `claude/.claude/settings.json`, so every stow user's main conversation and forks use Claude Code's built-in Concise style in sessions started after `git pull`. A CI pin test in `test_hook_alignment.py` fails on any removal or change of that line. A new design-decision record says why the default is forced and what the probes measured. On Sonnet, Concise replies were about 26% shorter, mostly on replies that answer a question. A closing priority line appeared in 1 of 5 Concise reviews against 5 of 5 Default, and numbered findings in 0 of 5 against 4 of 5 (rows 52, 54). The record also says what the change leaves to the separate settings base/override work, which repo surfaces were calibrated on Default output, and how a maintainer rolls the default back. A new minimal README subsection states what ships, its reach and its relation to § "Output preferences", with no pointer to Claude Code's own controls (row 67). A CHANGELOG entry announces the change. No opt-out recipe ships, `outputStyle` stays off the session-keys guard list, and CLAUDE.md does not change.

Scripted probes have already run under both styles (Verification step 5, rows 51-60). They confirmed the settings literal, showed `/output-style` leaving the stowed file untouched, and measured length and content. They could not observe the approach walk-through, because a `claude -p` run has nobody to walk through to (row 58). Before merge, a scripted replay of the engineer's own past first-turn prompts therefore runs under both styles with read-only tools, and the engineer reads the two replies side by side without running anything (Verification step 6, whose stop rule substitutes the probe pairs). The replay cannot observe the walk-through either, so that rule stays unobserved until ordinary use after the pull (Verification step 9c). Whether the measured losses still meet the engineer's quality goal is the engineer's decision at merge (Verification step 7).

Alternatives set aside:

- **A custom style file under `claude/.claude/output-styles/`.** The built-in style already does the job (row 1). A new top-level entry under `claude/.claude/` also needs `./install.sh`, while an edit to the existing settings file goes live on `git pull` (row 7).
- **Recommend Concise in the README without setting it.** The engineer chose the forced default (row 4).
- **A new CLAUDE.md concision rule instead of the style.** `claude/.claude/CLAUDE.md` § "Prose and Output Format" already carries the concision rules (row 21), and the Ask names the output style.
- **Add `outputStyle` to `GUARDED_KEYS_JSON`.** Both documented statements of the guard's class exclude it (rows 15-16). The pin test (M8) catches the same staged removal or change for less: one assertion, no edits to the hook header, `docs/hooks.md` or the guard test, and no denial of a Claude Code session's commit of the line (row 19). If Verification step 8 shows `/config` writing the key into the stowed file, the key falls inside the guard's class and this choice reopens as a follow-up (row 16).
- **Pin the key in `test_claude_enable_tool.py` beside `disableArtifact`/`disableWorkflows`.** That file tests the enable-tool wrappers. `test_hook_alignment.py` already holds the stow-source settings pins, including the closest sibling (row 35).
- **Add `outputStyle` to `ui-notification-defaults-in-stow-source.md` instead of writing a new record.** That file is a dated record of a decision about three other keys. The design-decision rule allows an in-place edit only to record supersession (row 23).
- **Document opt-out routes in the README: `/output-style` per repository, or a local deletion of the tracked line.** The engineer ruled out a repository opt-out because output style is a user preference, and placed per-user overrides in separate settings work (rows 11-12).
- **Pair the style with a CLAUDE.md rule that restores the closing synthesis Concise dropped: a priority line, numbered findings, open questions.** The Ask names the output style. Such a rule would also apply under Default and cost context in every session. It becomes a follow-up only if the engineer judges the losses in rows 54, 56 and 57 unacceptable (Verification step 7).
- **Trial Concise on the engineer's own project-local setting before shipping it.** The engineer chose the forced default (row 4). Under the symlinked layout of G1, a rollback commit is live on `git pull` for every stow consumer (row 39).
- **A README pointer to Claude Code's own controls.** The engineer chose a minimal subsection with no pointer (row 67).

No mechanism below is heavier than the task: each is a one-key settings edit, one test assertion or prose. The over-powered-primitive check therefore has nothing to weigh beyond the custom style file and the guard entry set aside above.

### Assumption ledger

**Root problem.** The engineer wants replies in the main conversation to use fewer words and be easier for a human to read while keeping their quality (row 47), with Concise shipped to every stow user as the default (row 4). The Default baseline already carries `claude/.claude/CLAUDE.md`'s concision rules, so the style's measured effect falls on replies that answer a question. The edit and rename reports were one sample each and support no conclusion (row 52). The repo also records why it forces the default and that per-user overrides are left to separate settings work.

**Givens** (conditions fixed beyond this plan's reach):

- **G1.** Stow installs `claude/.claude/settings.json` as each consumer's user-scope `~/.claude/settings.json`. A personal preference and a shipped default are therefore the same bytes, and no per-user file exists outside the tracked one. *Reason: Claude Code documents no user-scope local settings file, and the symlinked layout is this repo's install model.* `[verified: docs/design-decisions/ui-notification-defaults-in-stow-source.md lines 5-17]` Rows 13-14 cover the open change that would replace this layout.
- **G2.** Claude Code defines what the Concise style does, which surfaces it reaches and which versions support it. *Reason: the vendor imposes this.* `[verified: https://code.claude.com/docs/en/output-styles, fetched by the dispatching session when this plan was drafted and re-fetched on 2026-11-20 (row 61)]`

**Rows:**

1. `outputStyle` is a string in a settings file. The value is case-sensitive. A value that matches no style gives the Default style, which the page lists as "no style". `[verified: output-styles page, as G2]`
2. The page says: "To make a style your default across projects, set `outputStyle` in `~/.claude/settings.json`. A project's own settings files take precedence over that value." `[verified: output-styles page, as G2]`
3. `claude/.claude/settings.json` has no `outputStyle` key today, and no settings file in the repo sets one. `[verified: Read of claude/.claude/settings.json; a worktree Grep for outputStyle and output-style matched only review-pr's handling of .claude/output-styles/ paths]`
4. The stowed settings file forces Concise as the default for every stow user. `[engineer-verified: "I think that should be stowed to all users"]` `[engineer-verified: "Force default (Recommended)"]`
5. The option description shown beside every option label this ledger quotes was the dispatching session's proposal, not the engineer's words. `[unverified]` This plan takes from each label only what the label says. For row 4's label, that is that the stowed file forces Concise. The guard treatment and the record's content are this plan's own choices.
6. The settings literal is `"Concise"`. `[verified: output-styles page, as G2, which says "write the built-in names as `Proactive`, `Concise`, `Explanatory`, and `Learning`"]` A wrong case falls back to Default silently (row 1). The scripted probe confirmed the written value: `/output-style concise` wrote exactly `Concise` to a scratch directory's `.claude/settings.local.json`. `[verified: probe results file, read by the dispatching session and in this revision]`
7. An edit to an existing file under `claude/.claude/` goes live on `git pull`. A new top-level entry needs `./install.sh`. `[verified: repo CLAUDE.md, "Working in this repo"]`
8. The style applies to the main conversation and to forks. Other subagents run their own system prompt. `[verified: output-styles page, as G2]` Subagent concision therefore stays with `claude/.claude/CLAUDE.md` § "Prose and Output Format", which applies "to every session and subagent". `[verified: README.md § "Output preferences", the sentence containing "to every session and subagent"]`
9. Concise needs Claude Code 2.1.237 or later. The repo already requires 2.1.295 or newer. `[verified: output-styles page; README.md § "Requirements", its "Claude Code CLI" bullet; install.sh line 53, CLAUDE_CODE_MINIMUM_VERSION="2.1.295"]` A supported install always has Concise, so `install.sh` does not change.
10. A build older than 2.1.237 reads `"Concise"` as a non-matching value, gives Default, and still loads the rest of the file. `[unverified]` The page documents the non-matching fallback only for current builds. Such a build is already below the repo's floor (row 9), so this plan adds no handling for it.
11. The engineer ruled out a per-repository opt-out, because output style is a user preference. `[engineer-verified: "the preferred output style is a user preference. That’s not a repo preference"]` `[engineer-verified: "I don’t think the repo opt out. Makes sense."]` M4 therefore gives no `/output-style` route.
12. The engineer placed per-user settings overrides in separate work. `[engineer-verified: "there’s a more general problem with Settings customizations and that’s actually been worked on separately as part of PR 744"]` The engineer hedged on how that work functions ("pretty sure that’s how that works"), so rows 13-14 separate what was read from what was not. This plan also reads rows 11-12 as ruling out a README recipe that deletes the tracked line, so M4 documents no user-wide opt-out either. `[unverified]` The engineer's words name the repository opt-out. The tracked-file exclusion is the dispatching session's reading, carried on the Ask line.
13. PR #744's body, as read when this plan was drafted, gives `outputStyle` no place in its overlay. Rows 14 and 45 cover what that means for this change. Read from the PR:
    - Its title is "Split settings.json into base and overlay files", and it was open on branch `settings-base-render`.
    - Its body splits `claude/.claude/settings.json` into a tracked `settings.base.json` and an optional untracked per-machine `settings.overlay.json`.
    - `render-settings.sh` merges the two into `<config-dir>/settings.json`.
    - The body lists the overlay's closed key set as `autoMode`, `env`, `skillListingBudgetFraction` and `permissions.defaultMode`, and it does not mention `outputStyle`.

    `[verified: the dispatching session's gh pr view 744, in the session that drafted this plan]` Not read: whether the PR is still open, and its diff, which nobody read through `gh`. `[unverified]`
14. Whichever of this PR and PR #744 lands second rebases and places `outputStyle`, and M1 and M8 say where in each order. Under the design in a local checkout of `settings-base-render`, a key set in base has no per-user override, and a key left out of base reaches only machines whose prior `settings.json` carried it. Read from that checkout:
    - Its `render-settings.sh` allows only `autoMode`, `env` and `skillListingBudgetFraction` as overlay top-level keys (`OVERLAY_ALLOWED_KEYS_JSON`), plus `permissions` carrying only `defaultMode`.
    - Base always wins for `permissions`, `hooks`, `statusLine` and `skillOverrides` (`BASE_OWNED_KEYS_JSON`).
    - Every other top-level key that base and overlay leave out carries forward from the prior `settings.json` (the script's rule 3 comment).
    - Its `settings.base.json` sets `disableWorkflows`, and it sets none of `model`, `theme`, `tui` or `agentPushNotifEnabled`.
    - Its `test_hook_alignment.py` points `_SETTINGS_PATH` at `settings.base.json`.
    - No file in that checkout names `outputStyle`.

    `[verified: Read and Grep of that checkout in a prior revision, re-confirmed by the round-3 platform reviewer]` The checkout's branch head is `8dc6091b`, and the last-fetched `origin/settings-base-render` is `acfbd96d`. `[verified: the main checkout's .git/packed-refs]` Not verified:
    - whether the two commits hold the same tree;
    - the independent reviewer's report that `acfbd96d`'s `render-settings.sh` still has no `outputStyle`.

    `[unverified]`
15. The guard's header says every guarded key "holds one machine's own state". `docs/hooks.md` describes the class as "session-scoped or Claude-Code-auto-written preferences". `[verified: guard-settings-session-keys.sh lines 8-13; docs/hooks.md § "Gate hooks", the `guard-settings-session-keys.sh` entry]`
16. Claude Code never writes `outputStyle` into the stowed file. `/output-style` and `/config` save to a project's `.claude/settings.local.json`. `[verified: output-styles page, as G2]` In this repo, both paths where such a write could land are gitignored. `[verified: .gitignore lines 12 and 20]` The scripted probe confirmed the `/output-style` half: the stowed file's hash was unchanged, and its `git diff` showed no `outputStyle`, across every run. `[verified: probe result and analysis files]` The `/config` half is `[unverified]` and runs after the PR opens (Verification step 8). The guard header says `/config` also writes `model` and `effortLevel` into the user settings file (lines 8-13), so a changed file alone proves nothing about this key. If `outputStyle` appears in `git diff` of the stowed file, it falls inside the guard's class (row 15), and a guard entry becomes a follow-up decision for the engineer. M8 already fails CI on any committed change of the line.
17. Shipped defaults outside the guard's class ship unguarded. `agentPushNotifEnabled`, `disableArtifact` and `disableWorkflows` sit in `settings.json` at lines 86-88 and are absent from `GUARDED_KEYS_JSON`. `[verified: settings.json lines 86-88; guard lines 110-119]` A CI pin backs two of them: `claude/.claude/scripts/tests/test_claude_enable_tool.py` lines 194-201 assert both disable keys are `true`. No Python file names `agentPushNotifEnabled`. `[verified: Read of test_claude_enable_tool.py; Grep of the worktree's .py files]`
18. Accepted residual: a commit that changes the `outputStyle` line and edits M8 together passes every mechanical check. It shows only as two deliberate hunks in `/code-review` and PR review. Supporting facts:
    - A commit that removes or changes the line alone fails M8 in CI, which runs the full suite on every push. `[verified: repo CLAUDE.md, Commands]`
    - It also fails under `select-tests.py`, which selects the hooks tests for any `settings.json` change. `[verified: select-tests.py, the `p == CLAUDE_SETTINGS_JSON` rule]`
    - The guard does not catch it at commit time. Its tier is `cooperative`, and `docs/hooks.md` calls such a commit "revertible before merge". `[verified: docs/hooks.md § "Per-hook classification", the `guard-settings-session-keys.sh` row]`
    - No README text tells a user to delete the line (rows 11-12). An uncommitted local deletion reaches only that machine's accounts.
    - The output-styles page that M4 links tells a reader to set a user-wide default in `~/.claude/settings.json` (row 2), which under stow is the tracked file (G1). M4 adds nothing about that, because the engineer chose a minimal subsection with no pointer (row 67).
19. `outputStyle` is not on the live guard's list, so the guard does not deny this PR's commit, and a Claude Code session can make the commit. `[verified: guard lines 110-119]`
20. CLAUDE.md stays loaded under every style: the page says it "stays loaded whichever style you pick". `[verified: output-styles page, as G2]` The page does not say which wins when the two conflict, so which wins is `[unverified]`. This plan runs no conflict test: M4 states the relation without a ranking (row 67), and nothing else here depends on one. `output-preferences.md` reaches the session through an instruction in `claude/.claude/CLAUDE.md`. `[verified: README.md § "Output preferences"]` The independent reviewer found no scripted probe session reading that file, so a scripted conflict test could not have ranked it. `[unverified]`
21. No CLAUDE.md edit. The harness documents the style's behavior, and `claude/.claude/CLAUDE.md` § "Prose and Output Format" already states the concision rules every agent follows. A CLAUDE.md line saying the main session runs Concise would restate `settings.json`, and it would be false in any project whose own settings pick another style (row 2). `[verified: claude/.claude/CLAUDE.md, Agent Core group; repo CLAUDE.md, single source of truth]`
22. Whether Concise shortens or drops the approach walk-through is `[unverified]`, because the scripted runs could not observe it (row 58). Verification step 9c watches for it in ordinary use after the pull. What is known:
    - The main-session Working Style rule reads "Walk the user through your proposed approach and its tradeoffs before acting on it." `[verified: claude/.claude/CLAUDE.md line 129]`
    - The Agent Core rule "When presenting options, evaluate them — state which you'd recommend and why" reaches the same surface. `[verified: claude/.claude/CLAUDE.md, Agent Core Working Style]`
    - Concise leaves out preamble, narration and recaps. It keeps full length for destructive-action confirmations, and it "answers a simple question in one to three sentences" (row 61). `[verified: output-styles page, as G2]`
    - In the scripted probes the recommendation rule held. Every options reply in both styles named a recommendation with its reason, 10 of 10 on Sonnet and 6 of 6 on Opus (rows 55-56). `[verified: raw options replies, read in a prior revision]`
23. Each decision gets its own file at `docs/design-decisions/<slug>.md`. A decision file is edited in place only to record that a later decision supersedes it. `[verified: .claude/rules/design-decisions.md]`
24. A decision file needs exactly one H1, then on line 3 an italic provenance line carrying an ISO date. A decision recorded after the split carries no `Formerly §N` clause. Every relative link must name an existing file, and the link test strips any `#fragment` before it checks, so an anchor is never resolved (`_relative_link_violations`, line 475). `[verified: claude/.claude/hooks/tests/test_design_decision_files.py, `_ITALIC_PROVENANCE_LINE_RE` and `_ISO_DATE_RE` at lines 101-102, `TestPerFileShape` and `test_relative_links_resolve_to_existing_files`; .claude/rules/design-decisions.md]` The test checks only that line 3 carries a date in ISO form, so whether the date is right rests on M3's own instruction.
25. README's table of contents lists 11 of the 13 `###` subsections under Configuration. It omits "Error-mode analysis nudge" and "Cost ledger recording". `[verified: README.md's table of contents and its level-3 headings under "Configuration"]` M4 adds only its own entry.
26. README § "Machine-specific overrides" sends a reader who wants a preference everywhere to an environment variable. It exempts only `disableArtifact` and `disableWorkflows`, as shared defaults, and points to the next section for their override. `[verified: README.md § "Machine-specific overrides"]` No environment variable for the output style appears in anything this session read. `[unverified]` With no opt-out in M4 (rows 11-12), the sentence M5 once planned would have had no override to point a reader to, and the engineer dropped M5 (row 44). M4 carries no pointer to Claude Code's controls either (row 67).
27. No test reads `outputStyle` today, and none enumerates the stowed file's top-level keys. `[verified: row 3's Grep; Grep of test_doc_counts.py, test_hook_alignment.py and test_ask_review_permissions.py for settings.json and .keys()]` A pin is not a restatement of the value. It catches a staged removal or change, which no gate catches mechanically (row 18), and a case change, which would fall back to Default silently (row 1). The repo already pins other shipped defaults whose silent loss matters (rows 17, 35).
28. M6 says only that sessions started after the pull get the style, because whether a running session picks up a pulled `outputStyle` is `[unverified]`. The facts behind that:
    - `CHANGELOG.md` has an `[Unreleased]` section with a `### Changed` group. `[verified: CHANGELOG.md, its "## [Unreleased]" heading and the "### Changed" heading under it]`
    - Its entries say when a change is live on `git pull`. A change that depends on session start uses the line "**Takes effect** for a session only if that session started after you pulled this change." `[verified: CHANGELOG.md, the bullet reading "**Takes effect** for a session only if that session started after you pulled this change."]`
    - The page says "When you switch styles mid-session, Claude uses the new style starting with your next message", from v2.1.251. That covers a switch made through Claude Code's own controls. `[verified: output-styles page, as G2]`
    - The page says nothing about a settings file that a pull changes.
29. The design-decision record (M3) stays in scope. `[engineer-verified: "Design-decision record"]`
30. The README opt-out subsection and its table-of-contents entry (M4) stay in scope. `[engineer-verified: "README opt-out subsection"]`
31. The edit to README § "Machine-specific overrides" (M5) stayed in scope when the engineer selected it. `[engineer-verified: "README overrides sentence"]` Row 44 supersedes this row.
32. The CHANGELOG bullet (M6) stays in scope. `[engineer-verified: "CHANGELOG bullet"]`
33. A CI pin test for the `outputStyle` line is in scope. `[engineer-verified: "Add pin test (Recommended)"]`
34. As row 5 says of every quoted label, this plan takes from this one only that a pin test is in scope. The file, the test name and the assertion are this plan's choices (M8).
35. `test_hook_alignment.py` holds the stow-source settings pins. It defines `_REPO_ROOT` at line 97 and `_SETTINGS_PATH` at line 227, and 12 call sites load the file as `json.loads(_SETTINGS_PATH.read_text())` (lines 264-868). The closest sibling is `test_syncclaudeaiskills_stays_disabled_in_stow_source_settings` at lines 821-837: a top-level scalar default pinned by exact value, whose docstring cites its design-decision file by path. The attribution pair at lines 635-668 pins a nested key in two files, and its second test names the first, so M8 does not go between them. Another stow-file value pin, `TestSettingsJsonRegression`, sits in `test_claude_enable_tool.py`, a file that tests the enable-tool wrappers. `[verified: Grep and Read of both files in this revision]`
36. `advance-past-commit-stall.sh` fires only when the final sentence matches a fixed permission-verb phrase followed by a commit, push or PR object (lines 161-166). Its only rewording signal is the `phrasing-drift` log line, which needs the verb half to match (lines 177-192). `[verified: advance-past-commit-stall.sh lines 161-192; docs/commit-stall-block.md line 63]` Whether Concise rewords the commit offer is `[unverified]`, and Verification step 9b watches it.
37. A user-scope Concise reaches headless `claude -p` harnesses unless they set a style of their own, and their baselines measured before this change ran under Default (row 3). The facts behind that:
    - `evals/run_skill_evals.py` writes a project `settings.json` holding only `{"hooks": {}}` at lines 232, 365 and 389, so nothing at project scope overrides a user-scope `outputStyle` there. `[verified: Grep of evals/run_skill_evals.py in a prior revision]`
    - `evals/review_bench/runner.py` (line 168) and `evals/measure_subagent_model_resolution.py` (line 286) also launch `claude -p`. `[verified: Grep of both files in this revision]`
    - Only the skill evals' settings were read. The other two harnesses' settings handling and reply parsers were not, so whether a style change shifts what they measure is `[unverified]`.
    - `claude -p` honors a project-local `outputStyle`: the scripted probes ran through it, and the Concise arms came back shorter on every question-answering prompt (row 52). `[verified: probe analysis files]`
    - Whether harness runs after merge pick up the user-scope value is `[unverified]` until Verification step 9a confirms user-scope delivery.
38. `claude/.claude/rules/settings-json-conventions.md` routes individual preferences to a gitignored `settings.local.json` in its first bullet. `[verified: Read of that file]` At user scope that file corresponds to no documented scope (G1), so a user-wide default can only ship in the tracked file. M3 cites the rule and says why it does not apply here.
39. Maintainer rollback, under the symlinked layout of G1: a commit deleting the line from the stowed file is live on `git pull` for every stow consumer (row 7). `docs/hooks.md` uses the same mechanism as a hook's "Fleet kill switch". `[verified: docs/hooks.md, the "Fleet kill switch (maintainers)" bullet]` The rollback touches the full set:
    - the settings line;
    - the M8 pin;
    - the README subsection and its TOC entry;
    - the CHANGELOG, with a bullet announcing the rollback, or the removal of M6's bullet while it is still under `[Unreleased]`;
    - a supersession note in the M3 record, the one in-place edit a decision file allows (row 23).

    Under PR #744's layout the deletion may not reach a machine that already rendered the key. Its `render-settings.sh` carries forward every top-level key that base and overlay leave out, and `outputStyle` is neither base-owned nor overlay-allowed there (row 14). `[verified: row 14's reading of that checkout]` M8 pins only the tracked source, so it cannot catch that. A #744 rebase therefore decides both `outputStyle`'s placement and its deletion route. One route is making it a base-owned key, which a render deletes once base no longer defines it. That deletion behavior is the round-3 platform reviewer's reading of the script's comment. `[unverified]`
40. The M1 edit matches the `permissions.ask` rule `Edit(//**/.claude/settings*.json)` at `claude/.claude/settings.json` line 46, which `test_hook_alignment.py` pins through `_SETTINGS_FILE_ASK_RULE` (line 558). `[verified: Read of settings.json lines 36-47; Grep of test_hook_alignment.py]` Whether a `code-writer` subagent can answer that ask is `[unverified]`, so the parent session makes the edit.
41. README § "Updating after git pull" states the mechanics every pull follows and names no single change. `[verified: README.md § "Updating after git pull"]` A pointer there to one change's subsection would restate the CHANGELOG's announcement and go stale with the next change. The TOC entry (M4) and the CHANGELOG bullet (M6) are therefore the only announcement surfaces.
42. A stow user who already sets `outputStyle` in their checkout's `settings.json` may meet a refused pull, a merge conflict or, after a clean merge, a duplicate key. Which of two duplicate keys Claude Code honors is `[unverified]`, so M6 tells that user to keep one line, their own. Any uncommitted change to that tracked file may also make git refuse a pull that updates it, such as a `model` or `effortLevel` value that `/config` writes there (row 16). `[unverified]` Nobody reproduced git's refusal for this plan.
43. `select-tests.py` selects these targets for this diff, by changed path:
    - `claude/.claude/settings.json`: the hooks, skills and scripts test directories (the `p == CLAUDE_SETTINGS_JSON` rule);
    - `docs/`: hooks and skills (the `_is_under(p, DOCS_DIR)` rule);
    - `README.md`: hooks, skills and `test_transcript_routing_guard_capture.py` under the scripts tests (the `p == README_MD` rule, with `ROUTING_GUARD_CAPTURE_TEST_PATH`);
    - `CHANGELOG.md` and `.claude/plans/`: nothing (the `p == CHANGELOG_MD` and `_is_under(p, PLANS_DIR)` rules, which map to an empty target tuple);
    - a `.py` edit under `claude/.claude/hooks/tests/`, which M8 makes, matches four rules:
      - `_is_under(p, HOOKS_DIR)` selects the hooks tests;
      - `_is_py_source_under_claude_or_plugins` adds `test_ticket_reference_discipline.py`, which sits under the hooks tests directory and so folds into it;
      - `_is_test_tree_packaging_change` selects `claude/.claude/tests`;
      - `_is_test_source_change` selects `test_select_tests.py` under the scripts tests.

    `resolve_target_paths` folds a target inside a selected directory into that directory, and the run prints `select-tests: running <targets>` (the `print` call in `main`, near the end of `select-tests.py`). The scripts tests directory is selected whole only because `settings.json` is in the diff. Without M1 the line names the two scripts test files instead. `[verified: Read and Grep of select-tests.py in a prior revision; the round-3 platform and SDET reviewers traced the same lines]` `select-tests.py` itself was not run. `[unverified]`
44. M5, the edit to README § "Machine-specific overrides", is dropped. `[engineer-verified: "Drop M5 (Recommended)"]` This plan takes from the label only that M5 is dropped. The reasons in row 26 are this plan's.
45. This change lands on today's `claude/.claude/settings.json` without waiting for PR #744. `[engineer-verified: "Ship first (Recommended)"]` This plan takes from the label only the ordering. Where `outputStyle` sits once #744 lands is left to whichever PR lands second, per M1 and M8.
46. The README subsection (M4), reshaped to carry no opt-out recipe, stays in scope. `[engineer-verified: "Keep descriptive subsection (Recommended)"]` This plan takes from the label only that the descriptive subsection stays. Row 67 sets its shape. This row clarifies row 30.
47. The engineer's goal for the style: `[engineer-verified: "I'm hoping that the concise option will produce fewer words, make it easier for a human to read, but will keep like quality output."]` The tag covers the three hopes. How each is judged, in Verification step 7, is this plan's choice.
48. Superseded by row 67. `[engineer-verified: "Point to Claude Code's own controls (Recommended)"]` The engineer's later answer on how much of the README subsection should stay chose a subsection with no pointer, so M4 no longer points to Claude Code's own controls.
49. An Opus rerun and a brief check run before the PR opens. `[engineer-verified: "Opus rerun plus brief check (Recommended)"]` This plan takes from the label only that both measurements run. Both ran (rows 56-57).
50. Folded into row 5.
51. Probe method. Every scripted probe ran on 2026-11-20 with Claude Code 2.1.329 through `claude -p` with `--permission-mode acceptEdits`, in fresh scratch directories holding three small synthetic Python files. Each Concise arm set the style with `/output-style concise`, which wrote that directory's `.claude/settings.local.json`. Each Default arm had no settings of its own, and `/output-style` listed default as current there. The global `CLAUDE.md` loaded in both arms, so the Default baseline already carries this repo's concision rules. Samples per style and prompt:
    - one each for edit, rename, options and refactor prompts;
    - five each for review, options, tradeoffs, debug and explain prompts, on Sonnet;
    - three each for review, options and tradeoffs, on Opus;
    - three each for a subagent-brief prompt and a commit-message prompt, on Sonnet.

    The five prompt texts behind the Sonnet and Opus cells, one prompt per category:
    - review: "Review util.py and report any problems you find. Do not edit anything."
    - options: "I need to store a small config file for this project. Should I use JSON or YAML? I have to pick one."
    - tradeoffs: "We are considering caching the results of compute_total. Lay out the tradeoffs for a decision memo. Do not edit anything."
    - debug: "A user reports that parse_line crashes on the input line 'apple,,0.5'. Explain why it crashes and how you would fix it. Do not edit anything."
    - explain: "Explain to a new teammate what this directory does and how its files depend on each other. Do not edit anything."

    `[verified: probe result and analysis files and the probe's prompt files, read in this revision, for the version, date, sample counts, prompt texts and settings write]` `[verified: the probe scripts pass --permission-mode acceptEdits and --no-session-persistence to claude -p, and every probe init event read in this revision reports permissionMode acceptEdits and claude_code_version 2.1.329]` The fixture is synthetic, so the figures carry no per-project or per-account dimension. `[verified: repo CLAUDE.md § "Also redact structural fingerprints and provenance", on synthetic fixtures]`
52. Length, each figure on one prompt per category and one fixture. Sonnet, five per cell: the mean reply was 277 words under Default and 205 under Concise, about 26% fewer. That figure is the mean across these five prompts, so it describes this prompt mix, not a workload. Concise as a share of Default, by prompt: options 45%, review 77%, tradeoffs 74%, debug 79%, explain 84%. The explain share is inflated, because only Concise arms held `.claude/settings.local.json`. All five Concise explain replies spent a line of about 15 words on that file, and without it the explain share is about 77%. The edit and rename prompts ran one sample each, so their figures support no conclusion: 65 against 60 words and 23 against 29. Opus, three per cell: options 64%, review 86%, tradeoffs 89%. `[verified: the three analysis files, the raw explain replies and the later first-probe results file; the per-line word count and the adjusted share computed in this revision]`
53. Readability measures, Default then Concise. They are proxies for jargon and telegraphic prose. They move by small amounts both ways and show neither a clear regression nor a gain.
    - Sonnet, 25 replies per style:
      - acronyms per 100 prose words, 1.42 and 1.32;
      - average word length, 4.50 and 4.52 characters;
      - words per sentence, 10.3 and 9.7;
      - articles per 100 words, 9.1 and 8.0;
      - shorthand words per 100 words, 0.40 and 0.66, mostly "config" and "e.g.";
      - narration words per reply, 0.16 and 0, so Default already led with the answer.
    - Opus, 9 replies per style:
      - acronyms per 100 prose words, 2.27 and 2.50, a rise;
      - shorthand words per 100 words, 0.04 and 0.26, a rise;
      - words per sentence, 11.3 and 11.6, a rise;
      - articles per 100 words, 8.8 and 9.9;
      - average word length, 4.55 and 4.49 characters.

    `[verified: Sonnet and Opus analysis files, read in this revision]`
54. Losses, Sonnet, five per cell, each count on this prompt and this fixture. Each marker's classification rule comes first, then the count, Default first:
    - closing priority line, a closing sentence naming which review findings matter most or come first: 5 of 5 and 1 of 5;
    - numbered findings, review findings written as a numbered list: 4 of 5 and 0 of 5;
    - open-questions list, a tradeoffs reply closing with a list of two or more open questions or unknowns: 3 of 5 and 1 of 5, and 2 more Default replies posed a single question;
    - tooling caveat, an options reply saying an existing tool convention should decide, or offering to firm up the answer: 4 of 5 and 1 of 5;
    - per-option pros and cons, an options reply giving each format its own list item with its strengths or drawbacks: 4 of 5 and 0 of 5;
    - parser-dependency point, an options reply saying JSON needs no extra parser or dependency in most languages: 5 of 5 and 2 of 5;
    - run-directory note, an explain reply saying to run the scripts from this directory because the imports are flat: 3 of 5 and 0 of 5;
    - `ValueError` note, an explain reply saying a non-numeric quantity or price raises `ValueError`: 4 of 5 and 1 of 5;
    - suggested test, a debug reply proposing a test for the crashing input: 2 of 5 and 0 of 5.

    Content naming what would change the recommendation appeared in all five Concise tradeoffs replies, as a list in two and as a sentence in three. One reader, the independent reviewer, picked every marker here after reading these replies. The counts are therefore exploratory, and the markers are a subset of what Concise dropped, not a census. `[verified: the open-questions cell and the "what would change" content re-counted from the raw tradeoffs replies in a prior revision; the priority, numbered-findings and tooling-caveat cells re-counted in a prior revision and confirmed by the round-3 SDET and product reviewers; the five options, explain and debug cells re-counted from the raw replies in a prior revision and confirmed by the round-5 SDET reviewer; the markers script's header]` That reviewer's file also names second-order points in the tradeoffs replies and a non-numeric sibling case in the debug replies, which nobody re-counted for this plan. `[unverified]`
55. Kept, Sonnet: every options reply in both styles named a recommendation with its reason. Every Concise review kept the concrete failing inputs and the main defects. `[verified: raw options and review replies, read in this revision]` That the diagnosis and main risks also survived in every Concise debug, explain and tradeoffs reply is the independent reviewer's reading. `[unverified]` That reading covers content, not the accuracy of computed values, which nobody assessed.
56. Opus, three per cell:
    - Numbered review findings: 2 of 3 Default and 0 of 3 Concise. One Default review ordered its findings "from most to least important", and no Concise review did. Severity-style headings appeared under both styles.
    - A list of open questions closed 2 of 3 Default tradeoffs memos and no Concise one. All six said what evidence would change or settle the recommendation.
    - Every options reply in both styles named a recommendation with its reason. All six grounded it in the fixture's use of the Python standard library, so the tooling caveat had nothing to defer to.

    `[verified: Opus replies file, read in a prior revision]` Opus moved in the same direction as Sonnet in n=3 per cell, which cannot be told apart from chance. The most extreme 3-against-3 split reaches a two-sided Fisher exact p-value of only 0.10. `[verified: computed in this revision, 1 in 20 per tail]`
57. Written artifacts, Sonnet, three per cell. Each difference below is n=3, so it shows a direction only.
    - Subagent briefs: they averaged 64 words under both styles, and all six named the file, stated a read-only scope and asked for a report shape. One Concise brief ended "Keep the report concise."
    - Relays of the subagent's review: all three Default relays said the session had not checked the subagent's findings itself, against one Concise relay.
    - Commit messages: all six carried an equivalent one-line subject, five of them identical.
    - The edit report around the commit message: about a third shorter under Concise, a mean of 35 against 51 words. It left out the docstring text it had written in 2 of 3 Concise replies, against 0 of 3 Default, and that omission accounts for much of the saving.

    `[verified: brief and commit-message analysis file and raw replies, read in this revision]`
58. The walk-through was unobservable. In every completed scripted edit and refactor run, neither style wrote text before the first edit. `claude -p` under `acceptEdits` has nobody to walk through to, so these runs cannot show whether Concise drops the walk-through. The rename runs edited through `sed` in Bash, so no edit tool fired, and those cells say nothing either. `[verified: both first-probe results files]`
59. In the one completed refactor pair, Default tried to run the code after its edit and Concise did not. `[verified: the later first-probe results file's tool sequences]` The earlier run's Concise refactor did not complete, so this is one sample, not a finding. The replay exposes only read tools, so it cannot test this either (Verification step 6). Verification step 9e watches it in ordinary use.
60. The probes set Concise at project-local scope. Delivery through user scope, the path this change ships, stays untested until Verification step 9a. `[verified: probe results files, as row 51]`
61. The page says: "**Anything you ask for**: when you ask for an explanation or more detail, Claude answers in full." It also says Concise "answers a simple question in one to three sentences". `[verified: output-styles page, fetched on 2026-11-20 by the dispatching session's fetch subagent, verbatim quotes]` The second clause is the likely cause of the options-reply shortening. `[unverified]` M4 does not restate the first clause (row 64).
62. Superseded. The interactive check that would have left a project-local `outputStyle` in a real repository is replaced by a replay in disposable snapshots (Verification step 6), which changes no real repository's settings. `[engineer-verified: "it doesn't need me at all"]` This plan takes from the quote only that the engineer runs nothing for the pre-merge check. Reading the side-by-side file is what row 66's quote asks for, and the verdict line per pair is this plan's choice (Verification step 6). Whether recording that verdict before opening the key fits "doesn't need me at all" is the engineer's call. `[unverified]`
63. Dropped. The record states no rollback trigger. `[engineer-verified: "the rollback trigger is obvious, don't put it in the record"]` The maintainer rollback mechanism (row 39) stays.
64. The README sentence saying that asking for more detail gets the full answer is dropped from M4. `[engineer-verified: "I think the README is cruft beceause it says something that is intuitive to humans"]` The engineer's later answer settles how far that quote reaches: the subsection stays, minimal and with no pointer. `[engineer-verified: "Keep it minimal, no pointer (Recommended)"]` Row 67 carries that decision.
65. The measured evidence stays in the design-decision record (M3). `[engineer-verified: "Measured evidence in the record"]`
66. A replay of the engineer's own past conversations, shown side by side, replaces the interactive check. `[engineer-verified: "replaying some conversations I had and then showing me side by side what the output looks like"]` The quote names none of the following, so each is this plan's choice (Verification step 6 and the replay script's header):
    - first turns only: the quote says "conversations", and this plan narrows that to each session's first typed prompt, because a later turn depends on each arm's own earlier replies;
    - the prompt-selection rules, which keep typed main-chain text and reject anything that could carry private or secret content;
    - which sessions it draws on;
    - read-only tools;
    - the Default-against-Default pairs and the verdict line per pair;
    - the A and B order;
    - where its output lives.
67. M4 is a minimal subsection with no pointer to Claude Code's own controls. `[engineer-verified: "Keep it minimal, no pointer (Recommended)"]` This plan takes from the label only that the subsection stays minimal and carries no pointer. Its three items come from the option description beside the label, which was the dispatching session's proposal (row 5): what ships, its reach, and its relation to Output preferences. Whether M4's link to the output-styles page falls inside "no pointer" is the engineer's call, because that page tells a reader to set a user-wide default in `~/.claude/settings.json`, the tracked file under stow (row 18). `[unverified]`
68. No test resolves the record's, README's or CHANGELOG's `§ "Heading"` citations, so Verification step 4 checks them.
    - `test_skill_citations_resolve_to_real_headings` resolves citations only in SKILL.md files and their auxiliary siblings.
    - `test_every_citation_shaped_construct_is_extracted` scans `docs/**`, `README.md`, both CLAUDE.md files and the rules files, and checks only that each citation is extractable.

    `[verified: docstrings of both tests, test_skill_citation_grammar.py lines 76-97 and 136-158]` No test scans README links or its TOC, and CHANGELOG is in no scanned corpus. `[unverified: the round-3 SDET reviewer's search]` `test_per_account_path_contracts.py` flags a `~/.claude/` or `$HOME/.claude/` prefix on per-account state paths, `output-preferences.md` among them. `[verified: claude-skills/skills/tests/test_per_account_path_contracts.py lines 55-64]` That it scans the record and README is the SDET reviewer's reading. `[unverified]`
69. The CLI on the probed version offers the flags the replay needs. `claude --help` on 2.1.329 lists `--tools`, `--allowedTools`, `--disallowedTools`, `--strict-mcp-config`, `--mcp-config`, `--permission-mode`, `--max-budget-usd`, `--setting-sources` and `--bare`, and it lists no `--max-turns`. `[verified: the dispatching session's claude --help, relayed in the round-3 revision dispatch]` The probe scripts also pass `--no-session-persistence`. `[verified: concise-probe.sh and probe2-worker.sh]` Whether `--tools` alone removes MCP tools, and how `--max-budget-usd` ends a run, are for the canary run to settle. `[unverified]`
70. Probe runs show what an unbounded replay would carry. Their init events carry `output_style`, `permissionMode` and `claude_code_version`. Their `mcp_servers` list showed connected MCP servers. `[verified: probe init events, read in this revision]` Their tool list held write-capable tools beyond the edit tools, among them `Bash`, `Task`, cron, notification and MCP write tools. `[unverified: the round-3 platform reviewer's reading of one init event]`
71. Transcripts live under `<config-dir>/projects/<project-dir>/`, one project directory per startup directory, so each worktree has its own. A bare prefix match on the project directory's name also catches a sibling clone. `[verified: docs/transcript-analysis.md lines 3 and 66-67]`
72. The replay passes neither `--setting-sources` nor `--bare`, so the child loads the engineer's user-scope settings, hooks and plugins. This is a choice for fidelity to the engineer's real session. `claude --help` on 2.1.329 says `--bare` skips hooks defined in settings and by installed plugins. `[verified: claude --help, run in this revision]` An independent reviewer quotes the same help text as saying `--bare` also skips "CLAUDE.md auto-discovery", which would drop the concision rules the Default baseline carries (row 51). The same reviewer quotes its auth as "strictly ANTHROPIC_API_KEY or apiKeyHelper via --settings". `[unverified: the reviewer's quotes, not re-run in this revision]` The stowed `settings.json` declares a `UserPromptSubmit` hook. `[verified: grep of claude/.claude/settings.json, run in this revision]` That such a hook injects context into a replayed first prompt is `[unverified: the security reviewer's reading]`. The cost is that user-scope hooks run with the child environment, which Verification step 6 limits to a closed allowlist carrying no env-borne token.
73. Whether Concise keeps destructive-action confirmations and risk disclosures at full length rests on the output-styles page alone, as row 22 records. No probe and no replay observes it, because both are read-only first turns. `[unverified]` Verification step 9f watches it.
74. The output-styles page documents that Concise keeps Claude Code's built-in software-engineering instructions. Its "Built-in output styles" section says "Each of the four other built-in styles keeps those instructions and adds its own". The four other styles are Proactive, Concise, Explanatory and Learning, because Default is the fifth. The page also says Concise "does the engineering work as thoroughly as in the Default style". `[verified: output-styles page, fetched twice on 2026-11-22]` No probe observed it, so it has the same standing as row 73: documented, not observed. The one completed refactor pair, where Concise did not run the code after its edit (row 59), is one sample, and step 9e watches it. Its cause is open. No separate step watches the instructions. Rewriting row 74 and dropping the post-merge check that an earlier draft carried is `[engineer-verified: "Rewrite row 74, drop 9g (Recommended)"]`. This plan takes from the label only that the row is rewritten and the check is dropped.

**Mechanisms** (each anchored):

- **M1 — Add `"outputStyle": "Concise",` to `claude/.claude/settings.json` on the line after `"disableWorkflows": true,`.** No guarded key that Claude Code writes (`model`, `theme`, `tui`) then sits next to the insertion, so a committed or autostashed local change to one of them cannot conflict with the pulled line. An uncommitted change to the tracked file can still make git refuse the pull wherever the line sits, and M6's recovery bullet covers that (row 42). A mid-object line needs no comma change elsewhere. The parent session makes this edit, because it matches the settings-file ask rule (row 40). This change ships first (row 45). If PR #744 lands first anyway, this branch rebases and the line goes in `claude/.claude/settings.base.json` beside `disableWorkflows` instead (row 14). In that order the plan returns to `/plan-review` before implementation, because G1 and row 7 no longer hold as written (row 14), and the rebase also decides the key's deletion route (row 39). `anchors: row4`
- **M2 — Leave `GUARDED_KEYS_JSON`, its test and its `docs/hooks.md` entry unchanged.** `anchors: row18`
- **M3 — Create `docs/design-decisions/concise-output-style-stow-default.md`.** Title: "Concise ships as the default output style in the stow-source settings file". Line 3 reads `*<date>.*`, where `<date>` is the ISO date on which the implementer creates the file, read from `date +%F` at creation, with no `Formerly` clause (row 24). The file's shape follows `docs/design-decisions/claude-ai-skill-sync-disabled-by-default.md`, the closest post-split record of a forced stow-source default. The implementer drafts the body under CLAUDE.md §Durable text, one fact per sentence, with no PR-defined terms, citing files by name rather than line number. It must state:
  - What ships, and that stow makes it every consumer's user-scope default. Link `ui-notification-defaults-in-stow-source.md` for the shared-bytes layout instead of restating it.
  - The aim, as the maintainer's stated hope: "hoping that the concise option will produce fewer words, make it easier for a human to read, but will keep like quality output" (row 47). The measured trade follows it, with no claim that nothing a reader needs is lost.
  - Why the default lives in the tracked file. Cite `claude/.claude/rules/settings-json-conventions.md` § "Settings.json conventions" and say its first bullet's local-file route has no user-scope counterpart under this layout, without restating the bullet (row 38).
  - That no per-user override ships. Output style is a user preference whose override belongs to the separate settings base/overlay work, #744 at the time of writing (rows 11-14). The record also says that override exists only if that work admits `outputStyle`, which its overlay key list in the checkout read for this plan does not (row 14). Making that ask of #744 is the engineer's call, outside this diff.
  - Reach: the main conversation and forks only. Other subagents follow `claude/.claude/CLAUDE.md` § "Prose and Output Format". The page does not say which wins when CLAUDE.md and the style conflict (rows 8, 20).
  - Why CLAUDE.md does not name the style (row 21).
  - The version floor relation, with each number cited to its source (rows 9-10).
  - Why `outputStyle` is not a guarded session key, and that the pin test catches a removal or change (rows 15-18).
  - What the scripted probes measured, stated as observations with their sample counts, because the probe files live outside the repo and the record must stand alone:
    - The method, in two or three sentences: the date, the Claude Code version, `claude -p`, a synthetic three-file Python fixture, the two models and the sample counts. It also says the global CLAUDE.md loaded in both arms, so the Default baseline already carried its concision rules (row 51).
    - The five prompt texts, and that each category ran one prompt (row 51).
    - That each count holds on this prompt and this fixture, and that one reader chose the content markers after reading the replies, so they are a subset of what Concise dropped, not a census (row 54).
    - Length: the Sonnet means and per-prompt shares, the Opus shares, and the explain share as measured and without the fixture line. The edit and rename reports ran one sample each and support no conclusion (row 52).
    - The readability measures by model, in one or two sentences, and that they show no clear regression and no gain (row 53).
    - What Concise dropped, with each marker's classification rule beside its count: all nine row 54 markers, across the review, tradeoffs, options, explain and debug replies, and the Opus and written-artifact differences (rows 56, 57). For Opus the record states no direction beyond "same direction in n=3, not distinguishable from chance" (row 56).
    - What Concise kept: the verified half of row 55, and the kept parts of row 57.
    - That the scripted runs could not observe the approach walk-through (row 58), so it stays unobserved until ordinary use.
  - Not measured: every surface that Out of scope's "Surfaces the probes did not test" lists.
  - Surfaces calibrated on Default output:
    - the commit-stall hook's final-sentence phrase match, whose only drift signal needs the verb half to match (row 36);
    - the headless harnesses that run under a user-scope Concise unless they set a style of their own: the skill evals, the review bench and the subagent-model-resolution measurement. Their baselines measured before this change ran under Default (row 37).
  - The maintainer rollback under the symlinked layout: the full set row 39 lists, live on `git pull` for every stow consumer. Under the base/overlay layout the deletion route depends on how that work places the key (row 39).
  - After the engineer's step 7 disposition, one sentence the parent session adds: "the maintainer read a side-by-side replay of some of their own past prompts and shipped with the listed losses accepted", or the opposite. If the engineer accepted a loss beyond the list, "and further losses the maintainer named" follows "listed losses". If step 6's stop rule fired, the sentence names the scripted probe pairs instead of a replay. It carries no count and nothing else from the replay (Verification step 6).
  - A Sources list: the output-styles page, the settings page (https://code.claude.com/docs/en/settings), and this plan file, `.claude/plans/concise-output-style.md`, for the full assumption ledger.

  `anchors: row23`
- **M4 — Add a `### Concise output style by default` subsection to README after "Artifact and Workflow disabled by default" (the last `###` subsection before `## Context management`), plus a matching table-of-contents entry directly after that section's entry.** The subsection stays minimal, with no pointer to Claude Code's own controls (row 67). It states:
  - The stowed `settings.json` selects Claude Code's built-in Concise style, with a link to the output-styles page and to the M3 record for why.
  - Reach: the main conversation and forks. Other subagents follow `claude/.claude/CLAUDE.md` § "Prose and Output Format" (row 8).
  - Its relation to [Output preferences](#output-preferences): both reach the main conversation and forks, and Claude Code's page does not rank them (row 20). It does not present `output-preferences.md` as an override. Any path to that file starts with `<config-dir>/`, never with a home-directory `.claude/` prefix (row 68).

  It carries no "ask for more detail" sentence (row 64), names no command and gives no recipe (rows 11-12). § "Updating after git pull" gets no pointer (row 41). `anchors: row67`
- **M5 — Dropped.** No edit to README § "Machine-specific overrides". With no opt-out in M4, the sentence would have had no override to route a reader to (row 26). `anchors: row44`
- **M6 — Add one bullet to `CHANGELOG.md` `[Unreleased]` → `### Changed`.** It says:
  - the stowed `settings.json` now selects the Concise output style for the main conversation and forks, and other subagents are unaffected;
  - `README.md` § "Concise output style by default" describes it;
  - a user whose checkout's `settings.json` already sets `outputStyle` checks, after any pull, that the file holds exactly one `outputStyle` line, their own (row 42);
  - a pull that git refuses because the checkout's `settings.json` holds an uncommitted change, such as a `model` value that `/config` wrote, gets one next step: save your own lines elsewhere, run `git restore --source=HEAD --staged --worktree claude/.claude/settings.json`, pull, and re-apply only those lines. That git refuses such a pull is `[unverified]` (row 42);
  - a user who keeps an `output-preferences.md` file is told that which instruction wins between it and Concise is unobserved (row 20);
  - it takes effect in sessions started after the pull. This follows the CHANGELOG bullet reading "**Takes effect** for a session only if that session started after you pulled this change." without its "only if", because whether a running session picks up a pulled value is unverified (row 28).

  The bullet does not recommend `git stash`, because every worktree of the repo shares the stash stack.

  `anchors: row28`
- **M7 — No edit to `claude/.claude/CLAUDE.md`.** `anchors: row21`
- **M8 — Add `test_output_style_stays_concise_in_stow_source_settings` to `claude/.claude/hooks/tests/test_hook_alignment.py`, directly after `test_syncclaudeaiskills_stays_disabled_in_stow_source_settings` (ends line 837), its closest sibling (row 35).**
  - Load: the test loads through `json.loads` with an `object_pairs_hook` that rejects a key repeated at one object level. A merge can leave a duplicated `outputStyle` line in a consumer's checkout (row 42), and Python's `json.loads` keeps the last of two repeated keys. `[verified: ran json.loads read-only on one key written twice, which returned the second value]` Which one Claude Code honors is `[unverified]` (row 42). Without the hook, row 18's first bullet would hold only for a removal or a change, not for a duplicate.
  - Assertion: `settings.get("outputStyle") == "Concise"`. Exact equality also catches a case change (row 27).
  - Failure message: it names `_SETTINGS_PATH.relative_to(_REPO_ROOT)` and says stow consumers no longer get the Concise output style by default.
  - Docstring: one line saying the test pins the declared `outputStyle` and citing the M3 record by path.
  - If PR #744 lands first: the test text is unchanged, because `_SETTINGS_PATH` then names `settings.base.json` (row 14).
  - If this PR lands first: #744's rebase repoints `_SETTINGS_PATH`, and the pin fails there unless `outputStyle` stays in base, so its placement becomes an explicit edit. The pin cannot see the key's deletion route, which that rebase decides (row 39).

  `anchors: row33`

## Critical files

All paths are repo-relative.

- `claude/.claude/settings.json`: modify, one added line (M1), made by the parent session.
- `docs/design-decisions/concise-output-style-stow-default.md`: create (M3). Model its shape on `docs/design-decisions/claude-ai-skill-sync-disabled-by-default.md`, and link `docs/design-decisions/ui-notification-defaults-in-stow-source.md` rather than restating it.
- `README.md`: modify the TOC and add the new minimal subsection (M4). The Machine-specific overrides sentence stays as it is (M5 dropped, row 44).
- `CHANGELOG.md`: modify, one `[Unreleased]` bullet (M6).
- `claude/.claude/hooks/tests/test_hook_alignment.py`: add one test after `test_syncclaudeaiskills_stays_disabled_in_stow_source_settings` (M8). Reuse `_SETTINGS_PATH` (line 227) and `_REPO_ROOT` (line 97) rather than a new path constant. Load through `json.loads` with a duplicate-rejecting `object_pairs_hook` defined inside the test.

Deliberately untouched: `claude/.claude/hooks/guard-settings-session-keys.sh`, `claude/.claude/hooks/tests/test_guard_settings_session_keys.py`, `docs/hooks.md`, `claude/.claude/CLAUDE.md`, `claude/.claude/scripts/tests/test_claude_enable_tool.py` and `install.sh`. The replay script (Verification step 6) lives outside the repository and is not part of the diff.

Dispatch split, in order:

1. The scripted probes already ran (Verification step 5), so implementation waits on no further measurement. The replay (Verification step 6) and the engineer's step 7 decision gate merge, not implementation.
2. The parent session makes M1, because the settings-file ask may not be answerable inside a subagent (row 40).
3. One `code-writer` dispatch covers M3, M4, M6 and M8. These files share one background: the record, README and CHANGELOG cite each other, and M8 cites the record. Splitting would restate that background in every prompt. Its verification command is Verification step 1. Its prompt states:
   - this plan file's path, and rows 51-61 and 63 plus the rows each M3 bullet cites as the record's evidence, rather than pasting them;
   - that M1 is already applied;
   - that `claude/.claude/settings.json` is not the writer's to edit;
   - that an M8 failure means report back, not fix.
4. The parent session runs Verification steps 2-4 and opens the PR. Step 3 edits `settings.json`, so it stays with the parent.
5. Before merge, while the PR is open, the parent session builds the Verification step 6 replay script, has it reviewed as that step says, runs it and gives the engineer only its output path. The engineer reads the side-by-side file and makes the step 7 decision. Verification step 8 runs once the PR is open and does not block merge.
6. After the engineer records the step 7 disposition, the parent session adds M3's one-sentence trace, runs `/code-review` on that edit and commits it. It then runs the replay script's `--cleanup` mode, which deletes the replay's output directory (Verification step 6).

Projected diff: about 95 changed lines, nearly all additions: 1 in `settings.json`, about 65 in the new record, about 6 in README, about 7 in CHANGELOG and about 15 in `test_hook_alignment.py`.

## Verification

Steps 1-4 run after implementation. Step 5 is done. Step 6 and the step 7 decision gate merge, not implementation. Step 8 runs once the PR is open and does not block merge. Step 9 runs after merge.

1. From the worktree root, with M1 already applied, run `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py`. It passes. Its `select-tests: running` line names `claude-skills/skills/tests`, `claude/.claude/hooks/tests`, `claude/.claude/scripts/tests` and `claude/.claude/tests`, in any order (row 43). Without M1 the line names two scripts test files instead of their directory, and M8 fails. A `running the full suite` line instead means select-tests.py widened on its own, and that also satisfies this step. On this diff the selected tests check three things:
   - `test_design_decision_files.py` checks the record's shape and that each relative link names an existing file, with any `#fragment` stripped first (row 24);
   - the skills tests check only that each `§ "Heading"` citation in the record and README is extractable, not that it resolves (row 68);
   - M8 pins the line.
2. `jq -r .outputStyle claude/.claude/settings.json` prints `Concise`, which also proves the file still parses.
3. The pin bites. The parent session changes M1's value to `"concise"` and runs `scripts/venv-run.sh pytest claude/.claude/hooks/tests/test_hook_alignment.py -k test_output_style_stays_concise_in_stow_source_settings`, which reports one failure. It restores `"Concise"` and re-runs, which reports one pass. It then re-runs step 2's `jq`, which prints `Concise`. The parent then runs `git diff origin/main -- claude/.claude/settings.json`, which shows only M1's added line.
4. Citations and links, which no test resolves (row 68). Every item but `test -f` is checked by what it prints, not by its exit status, because `grep -c` exits 0 on a count of 2 and `grep -A1` exits 0 whenever its first line matches:
   - `grep -c -x -F '### Concise output style by default' README.md` prints `1`.
   - `grep -n -F '](#concise-output-style-by-default)' README.md` prints the TOC entry and nothing else.
   - `grep -n -A1 -F '  - [Artifact and Workflow disabled by default](#artifact-and-workflow-disabled-by-default)' README.md` prints the new TOC entry as its second line.
   - `grep -c -F '](docs/design-decisions/concise-output-style-stow-default.md)' README.md` prints `1`, and `test -f docs/design-decisions/concise-output-style-stow-default.md` exits 0.
   - `grep -c -F '§ "Concise output style by default"' CHANGELOG.md` prints `1`.
   - `grep -c -x -F '## Prose and Output Format' claude/.claude/CLAUDE.md` prints `1`.
   - `grep -c -x -F '## Settings.json conventions' claude/.claude/rules/settings-json-conventions.md` prints `1`.
   - `grep -c -x -F '### Output preferences' README.md` prints `1`.
   - For any other `§ "Heading"` citation in the record or the README subsection, the same whole-line grep for the heading in the cited file prints `1`.
5. Scripted probes: done on 2026-11-20, with nothing left to run (rows 51-60). They covered four things:
   - the settings literal, since `/output-style concise` wrote exactly `Concise` (row 6);
   - a Default baseline, since `/output-style` listed default as current in a directory with no settings (row 51);
   - the stowed `settings.json`, whose hash stayed unchanged and whose `git diff` showed no `outputStyle` across every run (row 16);
   - the length, readability and content comparison (rows 52-57).

   They did not cover the `/config` write (step 8), the approach walk-through (step 9c) or delivery through user scope (step 9a).
6. Replay, before merge. The parent session builds and runs a disposable script, outside the repository, that replays up to ten of the engineer's own past first-turn prompts under Default and under Concise and writes each pair of replies side by side (rows 62, 66). The engineer runs nothing. The script holds these invariants:
   - **Tools.** `--tools` names only `Read`, `Grep` and `Glob`, under an explicit `--permission-mode default` (rows 69-70). The script passes neither `--bare` nor `--setting-sources` (row 72).
   - **MCP.** The script passes `--strict-mcp-config` with no `--mcp-config` (row 69). That these flags leave the child only those three tools and no MCP server is `[unverified]` until the canary's init event shows it (row 69).
   - **Environment.** The child environment is built empty, not copied and pruned, from a closed allowlist: `PATH`, `HOME`, `CLAUDE_CONFIG_DIR` and the locale variables. No env-borne token or session-linking variable reaches the child or its hooks (row 72). Credential files under `HOME` and the config directory stay reachable, so the canary checks that the child cannot read a file outside its snapshot. If the canary fails to authenticate, the script stops and the parent reports it, and the allowlist is not widened.
   - **One config root.** Prompts come only from this repository's sessions under the active config directory, which is also the root the runs execute under (row 71).
   - **Prompt filters.** The script rejects, fail-closed, any prompt that could carry private or secret content. The blocklist match is a case-insensitive substring match against each entry of `<config-dir>/private-projects.md`, and the script refuses to start unless that file holds at least one entry. A prompt over 700 characters is rejected, a heuristic bound on pasted text that no source sets.
   - **Spend.** At most 26 runs per invocation: up to ten prompts under two styles, plus, for up to three of them, a noise pair of two fresh Default runs that shares no reply with another pair. A noise pair's verdicts give the engineer's blind read a noise floor at step 7 and never gate it. Each run's `--max-budget-usd` cap is $1.50, so one invocation stays within $39 if the cap holds. How the cap ends a run is `[unverified]` until the canary records it (row 69). No run is retried. The script refuses a second live pass in the same output directory, so a crashed pass is reported, not restarted.
   - **Output.** The script's files and the child's stdout and stderr go only to a mode-0700 directory under `~/.local/state/`. The child runs with `--no-session-persistence` (row 69). Anything the user-scope hooks write under the config directory (row 72) falls outside this bullet and outside `--cleanup`. Nothing from the replay output enters the repository, the PR body, this plan, `agent-reviews/` or any review ledger, except M3's one-sentence disposition trace, which carries no count.
   - **Parent.** The parent session reports only the output path. Child and script output goes to files in that directory, so no prompt or reply text reaches the parent's context.
   - **Deletion.** The script's `--cleanup` mode deletes only the directory it created, found from its own manifest, never a path the parent supplies.
   - **Blinding.** Each pair's replies, noise pairs included, are labelled A and B in a random order. A separate key file holds the mapping and the word counts (row 52).
   - **Verdict.** Before opening the key, the engineer records per pair which reply they would keep, which was easier to read, and anything they needed that the other lacked. A pair whose kept reply is Default because Concise lacked something material goes straight to the step 7 disposition.
   - **Criteria.** The detailed acceptance criteria are drafted in `step6-trim.md` part 2 as amended by `header-additions.md`, both in `~/.local/state/concise-output-style-probe/`. The parent session writes them into the script's header before any review. The script lives outside the repository, so `/code-review` never sees it. The parent session therefore dispatches `staff-platform-engineer` and `ciso-reviewer`, handing them both drafts and the findings files that `header-additions.md` item 3 names, by path. Each reviewer first confirms that the header holds every item those files name, then reviews the script against the header. An item those files name that the header lacks is a miss against the header. No live run starts until that review, the script's synthetic-fixture self-test and a canary run pass.
   - **Stop rule.** If that review returns a new class of criterion rather than a miss against the header, or fewer than six prompts survive the filters, the replay stops. The parent session tells the engineer why and renders the existing probe pairs side by side instead, blinded and with the same verdict line. Those prompts are the session's, not "conversations I had" (row 66), so whether they suffice is the engineer's call at step 7.
   - **Limits of the evidence.** The replay shows first-turn replies with read-only tools on the engineer's own configuration. It cannot show the approach walk-through (row 58).
7. Quality-goal decision, the engineer's at merge. This step records a decision, not a measurement. The goal is row 47's.
   - **Fewer words, measured.** Met when Concise's mean reply is shorter than Default's on every question-answering prompt. Row 52 shows this on both models, on one prompt per category and one fixture.
   - **Easier to read, judged.** The readability measures show no clear regression and no gain (row 53). They include small rises in shorthand on both models, and in acronyms and sentence length on Opus. Whether those rises are acceptable, and whether the replies read as plain prose, is the engineer's reading. The verdict line's "which was easier to read" answer informs this reading but does not gate the disposition below, which turns on the losses and the step 6 verdicts, though the engineer can still hold the PR on readability.
   - **Like quality, judged.** Met when the engineer names nothing from the Default replies that they needed and Concise dropped, or names it and accepts the loss. The losses to accept or reject, by name:
     - the closing priority line (row 54);
     - numbered findings (rows 54, 56);
     - the open-questions list (rows 54, 56);
     - the tooling caveat (row 54);
     - per-option pros and cons (row 54);
     - the parser-dependency point (row 54);
     - the explain reply's run-directory note (row 54);
     - the explain reply's `ValueError` note (row 54);
     - the debug reply's suggested test (row 54);
     - the written docstring text in an edit report (row 57);
     - the relay's statement that the session had not checked the subagent's findings (row 57). This one is an oversight signal, not a style loss: it tells the engineer what the session did not verify.

     The named losses are a subset that one reader chose after reading the probe replies, not a census (row 54). The step 6 verdict line carries anything the list misses. Rows 55-57 show what Concise kept in the scripted runs. The debug, explain and tradeoffs part of row 55 rests on the independent reviewer's reading.
   - The step 6 replay adds the engineer's own prompts as first-turn, read-only replies. If its stop rule fired, the disposition below proceeds on the probe pairs only once the engineer says they suffice.

   Disposition: if the engineer accepts the listed losses and no step 6 pair opened the disposition, the parent adds M3's trace sentence and the PR may merge. Otherwise the PR does not merge until the engineer decides whether to ship with the losses accepted, add a mitigation, or drop the forced default. M3's trace sentence names any accepted loss beyond the list only generically.

8. `/config` write check, once the PR is open. It does not block merge. From a clean stow checkout, where `git -C <stow checkout> status --short` prints nothing, open `/config` in a scratch directory. Choose a style other than Concise, then Concise, and read that directory's `.claude/settings.local.json`: it holds `Concise`. Re-run the status command and `git diff` the stowed file. If `outputStyle` appears there, restore the file. The key then falls inside the guard's class, and a guard entry becomes a follow-up for the engineer (row 16).
9. Post-merge checks. Each miss is a follow-up for the engineer, not an automatic rollback.
   - **9a. User-scope delivery** (row 60). It needs the merged line in the stow checkout. After `git pull` there, start a session in a directory whose own settings set no `outputStyle`. Either run `/output-style` interactively, or run a scripted `claude -p` there and read `output_style` from the stream's init event (row 70). Pass: Concise is the active style. On a miss, fix forward: a value Claude Code does not match gives Default (row 1), so the line is inert rather than harmful.
   - **9b. Commit-stall hook** (row 36). Pass: on the next autonomous-shipping turn that ends on a commit offer, the hook still advances it. On a miss, the hook's phrase match becomes a follow-up.
   - **9c. Approach walk-through** (row 22). Pass: the walk-through still appears before a multi-file edit in ordinary use. On a miss, restoring it becomes a follow-up.
   - **9d. Review relays and question text** (row 57). Pass: on the next turn that relays `/code-review`, `/plan-review` or `/ready-for-review` findings, the priority or recommendation line survives, and on the next question the main session asks the engineer, the scenario text survives. On a miss, that surface becomes a follow-up.
   - **9e. Self-check after an edit** (row 59). Pass: after a code edit in a repository with a runnable check, the main session still runs that check before it reports the edit done. On a miss, restoring the self-check becomes a follow-up.
   - **9f. Destructive-action confirmation** (row 73). Pass: the next destructive-action confirmation still names the target and its blast radius. On a miss, that surface becomes a follow-up.

## Out of scope

- **Per-user and per-repository overrides of the output style.** The engineer left them to the separate settings base/override work (rows 11-12). See rows 11-14 for what was and was not read of PR #744, and M1, M8 and row 39 for what each landing order decides.
- **Adding `outputStyle` to the session-keys guard.** M8's pin covers the staged removal or change instead (row 18), unless Verification step 8 shows `/config` writing the key (row 16), which makes a guard entry a follow-up.
- **Concision for non-fork subagents beyond what CLAUDE.md already states.** The style does not reach them (row 8), and the Ask names the output style.
- **The precedent record's open discrepancy about "Any file" scope.** It concerns `enabledPlugins` and `agentPushNotifEnabled`, not this change.
- **The README TOC's two pre-existing omissions** (row 25). They predate this change, and the file-boundary rule keeps them out.
- **Changing the commit-stall hook's phrase match or re-measuring eval baselines.** The record names both dependencies (rows 36-37). Either becomes work only if post-merge observation shows a shift.
- **Announcing the change beyond CHANGELOG,** such as a README pointer to CHANGELOG or telling stow consumers directly. That stays the engineer's call, outside this diff (row 41).
- **Surfaces the probes did not test.** Not measured:
  - written artifacts beyond subagent briefs and commit messages, such as PR bodies, plan files and handoff notes;
  - models other than the Sonnet and Opus models probed;
  - Claude Code builds other than 2.1.329, the one probed;
  - multi-turn sessions, and any turn after the first in the step 6 replay;
  - skill-driven relays, such as the main session relaying review findings, and the questions the main session asks the engineer. Step 9d watches both;
  - whether Concise still runs its own edit to check it, seen in one refactor pair only (row 59). Step 9e watches it;
  - destructive-action confirmation and risk-disclosure text, which row 22 takes from the vendor page and no probe observed (row 73). Step 9f watches it;
  - whether Concise keeps Claude Code's built-in software-engineering instructions, which the vendor page documents and no probe observed (row 74). Step 9e watches the one observed divergence.

  The M3 record lists these as not measured and claims only what rows 51-60 measured.
- **A CLAUDE.md rule restoring the closing synthesis Concise drops.** It becomes work only if the engineer's step 7 decision calls for it.
- **A conflict test between the style and CLAUDE.md or `output-preferences.md`.** Nothing in this change depends on which wins (row 20).
