# Record that Concise was evaluated and not adopted as the stow default

## Context

Goal: stop the branch from shipping Claude Code's built-in Concise output style as the stow-wide default, and keep the study that measured it as a design record.

Ask: "this is a clear do not ship the study, but the decision is to turn off concise, to not adopt it." On the quality cost the engineer said "I need to know pros and cons to make good decisions." Asked whether to reuse PR #1595, the engineer answered "I would say reuse 1595, right? Because I don't want to ship concise."

Why now: the branch added `"outputStyle": "Concise"` to `claude/.claude/settings.json`, with a pin test, a README subsection, a CHANGELOG bullet and a design record. The record's probes (Sonnet, five prompts per style) show replies about 26% shorter, no readability gain, and dropped content a reader decides from: numbered findings, per-option pros and cons, caveats, a closing priority line. The engineer said of the quality metrics that they do not meet the bar: "quality metrics, doesn't meet the bar".

Intended outcome: no Concise default reaches any stow consumer. The design record stays as the evaluation, stating that Concise was not adopted and why. The replay of the engineer's past prompts and the step 7 quality-goal merge gate in the old plan are cancelled, because the engineer decided without them.

Scope: the branch's own additions are reverted or rewritten. Guidance on presenting information to a human is separate future work.

## Approach

Restore the four files the branch changed only to ship Concise (`claude/.claude/settings.json`, `claude/.claude/hooks/tests/test_hook_alignment.py`, `README.md` and `CHANGELOG.md`) to their merge-base state, so they drop out of PR #1595's diff. Rename the design record to `docs/design-decisions/concise-output-style-not-adopted.md` and reframe it as evaluated and not adopted: the measurement sections stay verbatim, and every section that applies only to a shipped default goes.

One `code-writer` dispatch implements it. After the commit, the session rewrites PR #1595's body and title (M4).

Alternatives weighed:
- **Hand-deleting the added lines with `Edit`.** It works and stays the fallback. Restoring from the merge-base is exact by construction and checkable with one empty `git diff` (row 4).
- **`git revert` of the branch's commits.** Set aside: a revert works per commit, not per file, so every commit would need checking for record and plan hunks that must stay.
- **Keeping the slug `concise-output-style-stow-default`.** Set aside. It names the opposite decision, the rule picks the slug from the decision's title, and once M1 lands nothing links to it (rows 6, 7).
- **A supersession note on the old record plus a new record.** Set aside. Supersession marks a merged decision that a later one overturns. This record never merged, so a superseded file would document a default that never took effect (row 7).
- **The `-declined` suffix, which 9 of the 10 declined records use.** Either fits the filename grammar. `-not-adopted` uses the Ask's own verb and matches `architect-fix-plan-pilot-not-adopted.md` (row 8).
- **A decision-only CHANGELOG bullet, as at `CHANGELOG.md:867-868`.** Set aside: nothing changes for a stow consumer, and 9 of the 10 declined records carry no bullet (row 9).
- **An absence pin, `test_output_style_stays_unset_in_stow_source_settings`, after the `subagentPromptCacheTtl` precedent (row 16).** Set aside. The decision is not to adopt, not to forbid a later adoption, and a later adoption would edit the pin in the same deliberate PR. The pin would catch only a hand edit that adds the key. It is a one-test addition if the engineer wants it.
- **Keeping "Surfaces calibrated on Default output" as a checklist for a revisit.** Set aside. Every bullet describes what a shipped user-scope default would shift. Its file-level checks, such as no harness mentioning `outputStyle`, go stale as the harnesses change, so a revisit must redo them (row 12).
- **Dropping the maintainer's quoted aim from the record's opening.** Set aside. The Length, Readability and "What Concise dropped" sections were built to test that aim, so a reader without it cannot tell what a revisit should re-measure. The quote carries over unchanged from the old record's `:7`, and the earlier plan engineer-verifies it (row 10).
- **Closing PR #1595 and opening a fresh one.** Set aside by the engineer (row 2).

**Assumption ledger**

**Root:** The branch ships `"outputStyle": "Concise"` in the stow-source settings file, with a pin test, a README subsection and a CHANGELOG bullet, although the engineer decided not to adopt Concise (row 1). Its design record frames the probes as backing that shipped default (rows 11, 12).

**Givens:**
- Claude Code's output-style behavior, including Concise's reach to the main conversation and forks. Reason: the vendor owns it, and the record cites its page rather than testing it (row 13).
- The probe figures in the record's measurement sections. Reason: the raw probe replies are not in this repository, so this plan cannot re-derive a figure. It carries each one forward byte-for-byte (M3).

**Mechanisms:**
- **M1.** Restore `claude/.claude/settings.json`, `claude/.claude/hooks/tests/test_hook_alignment.py`, `README.md` and `CHANGELOG.md` to the merge-base with `git restore` (Critical files 1-4). That removes the `outputStyle` line, the pin test, the README subsection with its table-of-contents entry, and the CHANGELOG bullet, and with them both links to the old record.

  anchors: root, row1, row4, row5, row6, row9
- **M2.** `git mv` the record to `docs/design-decisions/concise-output-style-not-adopted.md` (Critical files 5).

  anchors: row6, row7, row8
- **M3.** Rewrite the record: a new title, provenance line and opening paragraph, the measurement sections kept verbatim except two shipping-framed passages and one added "Not measured" bullet, the shipped-default sections deleted, and Sources trimmed to the one entry the kept text cites (Critical files 5).

  anchors: root, row3, row10, row11, row12, row13, row14, row19, row21, row22
- **M4.** After the commit, the session syncs PR #1595's body through `/pr-description` and edits the title by hand, since the title still names shipping Concise (Verification 6).

  anchors: row2, row17, row18

**Rows:**
1. Concise is not adopted, and no stow consumer gets it by default. [engineer-verified: "the decision is to turn off concise, to not adopt it."]
2. The work reuses PR #1595 on the branch `concise-output-style`. [engineer-verified: "I would say reuse 1595, right? Because I don't want to ship concise."]
3. The engineer wants pros and cons to decide from. [engineer-verified: "I need to know pros and cons to make good decisions."] That this calls for the record to keep "Length" and "What Concise kept" beside "What Concise dropped" is this author's reading. [unverified: the quote answered a question about the quality cost, not about the record]
4. The branch's change to each of the four files is exactly the Concise addition: `settings.json:89` (1 line), `test_hook_alignment.py:840-861` (22), `README.md:35` and `:528-535` (9), `CHANGELOG.md:39-41` (3). Those counts match the additions in the session's `git diff --stat origin/main...HEAD`, so restoring each file to the merge-base removes them and nothing else. [verified: reads of each range, and the staff-sdet and staff-product-engineer reviewers' own three-dot diffs this round. Verification 1 re-checks the result.]
5. Nothing else in the tree names `outputStyle`. No hook, `config-keys.psv` row or doc registers the key. Other hits for "concise" and "output style" are unrelated: `respond-pr` and `code-writer.md` prose, `review-pr`'s `.claude/output-styles/**` rows, and `claude/.claude/CLAUDE.md`. [verified: case-insensitive Grep for `concise|outputStyle|output.style`, this revision]
6. Only two files link to the record by path, `README.md:530` and `test_hook_alignment.py:841`, and M1 removes both. [verified: Grep for `concise-output-style-stow-default` outside `agent-reviews/`]
7. The record was added on this branch and has not merged. The slug rule's "never change it after the file merges" therefore does not bar a rename, and its "Choose the slug from the decision's title" calls for one. [verified: `.claude/rules/design-decisions.md:12-15`. That the file is new rests on the session's stat (row 4).]
8. Declined-decision slugs in `docs/design-decisions/`: 9 carry "declined" and 1, `architect-fix-plan-pilot-not-adopted.md`, carries "not-adopted". [verified: Glob `docs/design-decisions/*{not-adopted,declined,rejected}*.md`]
9. Of those ten records, only `explore-haiku-pin-declined-on-measurement.md` appears in `CHANGELOG.md`, in a bullet that announces a shipped eval script (`:853`). Two decision-only bullets exist, at `:867-868`. The Concise bullet sits under `[Unreleased]` and was added by this branch, so removing it edits no released record. [verified: Grep of the nine other slugs in `CHANGELOG.md`, no matches; reads of `CHANGELOG.md:5,39-41,851-870`]
10. The old record quotes the maintainer's aim at `:7`, and the earlier plan tags the same quote `[engineer-verified]` in its ledger. The record carries the quote over unchanged, and this plan's `Ask:` line does not need it. [verified: `git show df56f416:.claude/plans/concise-output-style.md`, line 7 and row 47]
11. Inside the kept range, `:49-130`, two passages assume the style ships. `:117`'s "until ordinary use after the pull" is cut. The `:130` bullet "Delivery through user scope, the path this change ships." is reframed as "Delivery through user scope, the path a stow-wide default would use." That bullet is the only remaining statement that the probes never exercised the delivery path, because every probe set Concise at project-local scope (record `:51`). Every kept cross-reference points at a kept section: "What Concise dropped" at `:125` and "What Concise kept" at `:129`. [verified: Grep of the record for ship, pull, stow and user-scope terms, and a full read]
12. Each deleted range describes a shipped default. `:9-47` covers why the default lives in the tracked file, the per-user override, reach, why `CLAUDE.md` does not name the style, the version floor, and the settings guard with the pin test. `:132-151` covers the surfaces a user-scope Concise would shift and the rollback. One fact in `:33-47` still holds with no default shipped: whether `/config` writes `outputStyle` into the stowed file is untested (row 22). [verified: full read of the record]
13. Of the four Sources entries (`:155-158`), the kept text cites only the output-styles page: the main-conversation and fork reach (the new opening), the destructive-action confirmations (`:127`) and the built-in software-engineering instructions (`:128`). The settings page backs only the precedence claims at `:17` and `:27`. PR #744 and commit `acfbd96d` back only `:15-19` and `:151`. [verified: full read]
14. `test_design_decision_files.py` requires exactly one H1, an italic line-3 provenance line carrying an ISO date, and every relative link resolving. [verified: `test_design_decision_files.py:88,101-102,260-305,484`]
15. `select-tests.py` maps `docs/` to the hooks and skills test trees, so the record alone selects `claude/.claude/hooks/tests/`, which holds `test_hook_alignment.py` and `test_design_decision_files.py`. It reads committed names from `merge-base...HEAD` plus dirty names against `HEAD`, so the four restored files are selected before the commit and drop out after it. [verified: `select-tests.py:1076,1081,1182-1190`]
16. A test pins a settings key's absence when a decision keeps it unset, including one never set: `test_subagentpromptcachettl_stays_unset_in_stow_source_settings`. [verified: `test_hook_alignment.py:862-897`; `docs/design-decisions/main-bucket-prompt-cache-ttl-unset.md:14`]
17. `/pr-description` sync mode edits the body only, with `gh pr edit <n> --body-file`. [verified: `claude-skills/skills/pr-description/SKILL.md:18-24`]
18. PR #1595's title is "Ship Concise as the stow-wide default output style". [verified: `gh pr view 1595 --json title`, run by the staff-sdet reviewer this round]
19. The engineer decided on 2026-11-23, this session's date. [unverified: the dispatch relays the answers undated]
20. The study stays in the repo as the renamed and reframed record. Asked whether to keep the record or revert everything, the engineer selected "Keep and rename (Recommended)". [engineer-verified: "Keep and rename (Recommended)"]
21. The engineer gave one reason for not adopting Concise: "quality metrics, doesn't meet the bar". The record states that reason in those words and presents the probe results as the evidence the evaluation produced. It records no other grounds. [engineer-verified: "quality metrics, doesn't meet the bar"]
22. Whether Claude Code's `/config` writes `outputStyle` into the stowed settings file is untested. `guard-settings-session-keys.sh` does not list `outputStyle` in `GUARDED_KEYS_JSON`, so a tool-written value would pass the guard. The record keeps the question as a "Not measured" bullet and adds no absence pin. [verified: record `:37-39`; `grep outputStyle claude/.claude/hooks/guard-settings-session-keys.sh` prints nothing]

## Critical files

**Dispatch split.** One `code-writer` dispatch (`model: sonnet`) covers all five paths, for two reasons:
- M1 removes the two links to the old slug that M2 retires, so the changes must land in one commit.
- The record rewrite needs the same not-adopted background as the reverts.

The dispatch's verification command is `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py`.

1. `claude/.claude/settings.json` (M1). Restoring drops `:89`, the `outputStyle` line.
2. `claude/.claude/hooks/tests/test_hook_alignment.py` (M1). Restoring drops `:840-861`, the pin test and its two trailing blank lines.
3. `README.md` (M1). Restoring drops the table-of-contents entry at `:35` and the subsection at `:528-535`.
4. `CHANGELOG.md` (M1). Restoring drops the bullet at `:39-41`.

   Recipe for 1-4:
   1. Confirm `git status --porcelain -- <the four paths>` prints nothing, so no uncommitted edit is discarded.
   2. Run `git merge-base HEAD origin/main`.
   3. In a separate call, pass the printed SHA to `git restore --source=<sha> --staged --worktree -- <the four paths>`.
5. `docs/design-decisions/concise-output-style-stow-default.md`, moved with `git mv` to `docs/design-decisions/concise-output-style-not-adopted.md` (M2), then rewritten (M3). Line numbers below are the old file's.
   - Line 1 becomes `# Concise output style not adopted as the stow-wide default`.
   - Line 3 becomes `*2026-11-23.*` (row 19).
   - One opening paragraph replaces `:5` and `:7`. Each item below is its own sentence:
     - The aim, as the old `:7` states it: the maintainer's aim was "hoping that the concise option will produce fewer words, make it easier for a human to read, but will keep like quality output". The quote is copied unchanged (row 10).
     - `claude/.claude/settings.json` sets no `outputStyle`.
     - Claude Code's built-in Concise output style was evaluated as the stow-wide default.
     - Per the output-styles page, it would have reached every stow consumer's main conversation and forks.
     - It was not adopted. The recorded reason is the maintainer's: "quality metrics, doesn't meet the bar" (row 21). The record states no other grounds, and presents the results below as the evidence the evaluation produced.
     - On Sonnet, replies across the five probe prompts were about 26% shorter.
     - The readability proxies showed neither a clear gain nor a clear regression.
     - On exploratory counts at five samples per style, Concise dropped content a reader decides from.
     - The closing priority line, numbered review findings and per-option pros and cons are the three differences that reach a Fisher exact p of about 0.05, before any correction for nine markers.
     - A pointer to "What Concise kept" for what it kept and to "Not measured" for the coverage limits.

     "Default" capitalized names only Claude Code's style.
   - Delete `:9-47`, from "Why the default lives in the tracked file" through the pin-test paragraph. Collapse the doubled blank lines the deletion leaves.
   - Keep `:49-130` byte-for-byte, with three edits:
     - at `:117`, end the last sentence at "stays unobserved.", deleting "until ordinary use after the pull";
     - reword the `:130` bullet to "Delivery through user scope, the path a stow-wide default would use." (row 11);
     - add one "Not measured" bullet after it: "Whether `/config` writes `outputStyle` into `claude/.claude/settings.json`. The probes confirmed that `/output-style` leaves the file unchanged. The `/config` path is untested, and `guard-settings-session-keys.sh` does not list the key, so a written value would pass the guard." (row 22).
   - Delete `:132-151`, "Surfaces calibrated on Default output" and "Maintainer rollback". Collapse the doubled blank lines the deletion leaves.
   - Under Sources, keep only the output-styles entry. Trim its gloss to what the kept text cites: Concise as a built-in style, the main-conversation and fork reach, full-length destructive-action confirmations, and the built-in styles keeping Claude Code's software-engineering instructions. Delete the settings-page, PR #744 and `settings-base-render` entries (row 13).

Reuse: `git restore` from the merge-base for 1-4. The record's measurement sections move verbatim, so no figure is retyped.

Projected diff: ~105 lines against `main` in the new record, not counting this plan file, because the four restored files leave the PR's diff. Against the branch head, the implementation commit changes ~135 lines: 35 removed across the four restored files and ~100 in the record's rewrite.

## Verification

1. **Net diff.** `git diff --stat origin/main...HEAD` lists exactly `.claude/plans/concise-output-style.md` and `docs/design-decisions/concise-output-style-not-adopted.md`, and none of the four restored paths. Before the restore, the same command lists all six files, which shows the stat shrinks (rows 4, 5). This check does not depend on the merge-base SHA the restore used.
2. **No stale reference.** `git grep -n concise-output-style-stow-default -- ':!.claude/plans/'` prints nothing, and `git grep -n outputStyle -- claude/ README.md CHANGELOG.md` prints nothing (rows 5, 6).
3. **Verbatim carry.** Compare the kept range of the old record, pinned at branch head `01aad481`, with the new record. The old extract is `git show 01aad481:docs/design-decisions/concise-output-style-stow-default.md | sed -n '49,130p'`. The new extract runs from the line `## What the scripted probes measured` to the line before `## Sources`. `diff` of the two extracts shows only three hunks: the `:117` sentence, the `:130` bullet and the added `/config` bullet. This catches a changed figure without relying on git's rename detection or on `HEAD~1`.
4. **Scoped suite.** Run `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py` twice: after the restore and the record rewrite but before the commit, and again after the commit. The first run still selects the dependents of the restored files. Both runs select `claude/.claude/hooks/tests/` through the `docs/` row (row 15), which covers `test_design_decision_files.py`'s H1 and provenance checks on the new record (row 14). Both must pass.
5. **Read-through.** One read of the new record finds no sentence that describes Concise as shipped, rolled back or reaching consumers. Every figure in the opening paragraph appears in a kept section.
6. **PR (the session, after the dispatch).**
   1. Run `/code-review` before the commit.
   2. After the commit, run `/pr-description` in sync mode on PR #1595 to reframe the body as evaluated and not adopted. The body states that the branch's earlier commits adding the default stay in history and that the merge method is the human's call, since a squash merge keeps `main`'s history from reading as shipped.
   3. Run `gh pr edit 1595 --title "<title>"`, since sync mode leaves the title alone (rows 17, 18).
   4. Run `/ready-for-review`.

## Out of scope

- **Guidance on presenting information to a human.** The Context names it as separate future work.
- **The replay of the engineer's past prompts and the quality-goal merge gate from the earlier plan.** The Context records both as cancelled, because the engineer decided without them.
- **An absence pin for `outputStyle`.** See Approach's alternatives (row 16). The `/config` question it would have watched is carried in the record's "Not measured" list instead (row 22).
- **A reconsideration trigger in the record.** Six of the ten declined records state a condition that reopens the decision, but the engineer named none, and "Not measured" already lists what the probes did not cover.
- **Rewriting the branch's history.** The commits that shipped Concise, such as `59e8b021`, stay on the branch. Squashing or force-pushing is outside the autonomous-shipping ask, and the merge method is the human's call at merge.
