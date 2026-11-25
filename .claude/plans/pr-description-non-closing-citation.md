# pr-description: cite a multi-PR ticket without closing it

## Context

Give `/pr-description` a way to cite a ticket without closing it, for a PR that is not the last one its ticket needs.

Ask: GH-1528 ("pr-description: cite a multi-PR ticket without closing it on the first merge"), which the engineer named with `/plan-it 1528`.

`/pr-description` adds a closing keyword (`Fixes <TICKET-ID>`) to every PR body it is given a ticket for, and GitHub closes the issue when that PR merges. GH-1528 records three multi-PR tickets (GH-1114, GH-1116, GH-1118) that closed on their first merge with acceptance criteria outstanding. A closed issue with unmet criteria hides the remaining work from the tracker, and any issue naming it as a blocker points at something that looks finished. Until this lands, authors of earlier PRs remove the `Fixes` line by hand.

GH-1528 requires the design to answer four questions:

- How the skill learns that a PR is not the closing one.
- What the body carries in that case.
- Whether the closing keyword stays the default for single-PR tickets.
- Which callers pass a ticket ID today, and what each must pass after the change.

Done when, per GH-1528: a phase PR for a multi-PR ticket, described by `/pr-description`, merges without closing its ticket, and the ticket's final PR still closes it.

## Approach

Line 80 of `/pr-description` trades its unconditional `Fixes` for an evidence standard. The body cites `Fixes <TICKET-ID>` unless the caller, the engineer or the plan this work implements says a later PR will finish the ticket. It also keeps a `Part of <TICKET-ID>` citation the body already carries, unless one of them says this PR finishes the ticket. A phase PR's body cites `Part of <TICKET-ID>`, carries no closing keyword for the ticket, and names what the later PR covers. Nobody types anything: `/pr-description` runs in the invoking session, which already holds the caller's and the engineer's words and usually the plan (row 55). The never-loaded `pr-description-claude-config` layer is deleted (rows 5, 50).

This PR closes GH-1528 (row 52). The deferred issue-body marker (rows 19, 42) moves to a new issue, as follow-up work outside GH-1528. This PR's body therefore takes the default `Fixes GH-1528`, which the installed base already writes and which closes the issue on merge (row 10).

GH-1528's four questions:

- **How the skill learns a PR is not the closing one.** From what the caller, the engineer or the plan this work implements says about a later PR, or from a `Part of` citation already in the body. Line 80 names the plan the work implements, not a file matched to the branch name. A governing plan often carries another name (row 61). Naming the plan gives the session a reason to consult it, because `/pr-description` reads no plan file on its own (row 55). The incident tickets' plans already said in plain words that more PRs would follow (row 56).
- **What the body carries then.** `Part of <TICKET-ID>`, no closing keyword before the ID anywhere in the body, and what the later PR covers.
- **Whether the closing keyword stays the default.** Yes (row 20). Follow-up work outside the ticket, and the body's own description of its scope, do not count as a later PR. When the session cannot tell, the body gets `Fixes`.
- **Which callers pass a ticket ID, and what they pass after.** Only `/ready-for-review` passes one, and it passes the same `$ARGUMENTS` and `<TICKET-ID>` after the change. `/handoff` and `CLAUDE.md`'s PR-body rule pass none, before and after. On their syncs the bullet does not fire, so the body keeps the citation it already carries.

**Precedence.** Nothing turns an existing `Part of` citation into a closing keyword without a positive signal. The only positive signal is the caller, the engineer or the plan saying this PR finishes the ticket.
- **Why a kept `Part of` needs a stated finish to flip.** A wrongly closed ticket hides its remaining work, while a wrongly open one stays visible in the tracker.
- **Why `Fixes` stays the default.** It is the engineer's choice for single-PR tickets (row 20). A phase PR therefore needs a stated later PR to avoid it.

**Residual.** A phase PR whose session holds no such statement still gets `Fixes` and closes its ticket. A fix-up PR on a split ticket is the usual case, and so is a fresh session that never consults the plan. The follow-up issue carries this residual (Verification 8).

**Sync mode.** Whether line 80 applies in sync mode at all is unestablished (row 1). A `Part of` citation survives a sync either way. If line 80 applies, its kept-`Part of` clause holds the citation. If it does not, no sync step touches the citation. The plan does not claim that a statement arriving after the PR exists flips a published `Fixes` on the next sync, because under the second reading it would not.

**What this PR's body says,** beyond the usual sections:
- `Fixes GH-1528`.
- The follow-up issue's number. That issue holds the deferred marker and the residual.
- The Done-when is observed after merge, on the first phase PR and on the ticket's final PR (Verification 11).
- GH-1116 and GH-1118 stay closed. This PR does not reopen or repair them (row 62).
- GitHub does not list a `Part of` PR among an issue's linked pull requests (row 9).
- Under Incidental edits, the guard test and its naming consequence (row 27). The rule covers every skill whose text carries the layer-glob literal, which is five skills today.

No closing keyword sits before any other issue's reference in this body, because GH-1114 is open (Verification 10).

Alternatives weighed:
- **The issue-body marker now.** It moves to a new issue (rows 42, 52). It projected a diff of about 790 lines. Its signal also sits in free text an issue's author can edit.
- **A say-so typed into `/ready-for-review`'s arguments as the mechanism.** The engineer called it "heavy handed" (row 51). It also depends on someone typing it on a phase PR's first run. The evidence standard reads words the session already holds, though arguments remain one place a caller can say it.
- **A fixed marker line in the plan file.** It adds a second grammar. Line 80 reads the plan's plain words instead.
- **A Checks line so that the kept-`Part of` clause provably runs on sync.** A `Part of` already survives a sync under both readings (Sync mode, above), so the line would add no protection for it.
- **A report line stating which way merging goes, relayed by `/ready-for-review`.** The engineer dropped it (row 53).
- **Keeping the layer, reduced to a `#N` form rule.** `Fixes GH-<N>` already closes issue `N` (row 10), so nothing needs the `#N` form. The engineer chose deletion (row 50).
- **A branch-name phase suffix.** It changes `branch-management`'s naming for every stow consumer. The closing branch would also still need a signal of its own.
- **GitHub sub-issues, one per PR.** That moves the work onto tracker structure the engineer did not choose (row 19).

### Assumption ledger

**Root:** `/pr-description` writes a closing keyword for every ticket it is handed (row 1), and nothing tells it that a PR is one phase of its ticket. A phase PR therefore closes its ticket on merge with acceptance criteria outstanding, as GH-1114, GH-1116 and GH-1118 did.

**Givens:**
- G1. GitHub closes an issue when a merged PR's description carries a closing keyword directly before the issue's reference, and only that keyword creates the linked-issue relationship. Reason: GitHub owns this behavior (rows 9, 10).
- G2. Every stow consumer chooses its own tracker, and many are not GitHub Issues. Reason: each consuming repo owns its tracker, which is beyond this plan's reach. `.claude/rules/skill-and-agent-self-review.md` § "Skill and rule authoring conventions" is this repository's statement of the consequence: global skill bodies stay platform-agnostic.

**Mechanisms:**
- **M1. Evidence standard at `pr-description/SKILL.md:80`.** Replace the line in place with one line, so the file stays at 247 lines (row 15). The target wording is the consult's proposal (row 57) with two changes, explained below. `/skill-review` may tighten it.

  > - **A ticket reference, when a `<TICKET-ID>` was passed in.** Include `Fixes <TICKET-ID>` in the body alongside any existing citation of it (see REFERENCES.md for why), unless the caller, the engineer or the plan this work implements says a later PR will finish the ticket, or the body already cites it as `Part of <TICKET-ID>` and none of them says this PR finishes it. Then cite it as `Part of <TICKET-ID>`, with no closing keyword before the ID anywhere in the body, and name what the later PR covers. Follow-up work outside the ticket, and the body's own description of its scope, are not such a statement. When it is unclear whether a later PR will finish the ticket, and the body cites no `Part of <TICKET-ID>`, write `Fixes <TICKET-ID>`.

  The two changes from the proposal:
  - "the branch's plan" becomes "the plan this work implements". A governing plan often carries a name other than the branch's slug (row 61).
  - The proposal's last sentence read "Without one, write `Fixes <TICKET-ID>`." Read literally, it overrides the kept-`Part of` arm, because an existing citation is not a statement. The replacement keeps the "when the session cannot tell, `Fixes`" arm from the option description the engineer selected (row 54). It leaves the kept citation alone.

  The bullet uses only what the session already holds, so it works for every tracker (G2). It needs no new input from any caller (row 2). Only a statement that this PR finishes the ticket overrides a kept `Part of`, so a missing signal never upgrades it to `Fixes`. Whether that clause runs on sync is open (row 1), and a `Part of` survives a sync either way (Approach, "Sync mode").
  anchors: root, row1, row2, row14, row15, row20, row51, row54, row55, row56, row61
- **M2. Delete the claude-config layer.** Run `git rm claude-skills/skills/pr-description-claude-config/SKILL.md` (row 50). The layer never loaded in this repo (row 5), so deleting it changes no live behavior here. Its two rules would have closed more issues once loaded (row 7). It drops out of every stow consumer's install on `git pull` (row 6). Its prose-mention rewrite goes with it (row 26).
  anchors: row5, row6, row7, row10, row26, row50
- **M3. `pr-description/REFERENCES.md`, two edits.**
  1. At :182-183, rename "the closing-keyword bullet" to "the ticket-reference bullet".
  2. After :234, add these five sentences:
     - A PR that a later PR will finish gives the linked-issue relationship up on purpose, because the keyword that creates it also closes the issue on merge.
     - GitHub does not list such a PR among the issue's linked pull requests.
     - `Fixes` stays the default for single-PR tickets, so a phase PR needs a stated later PR to avoid it.
     - A phase PR without one still closes its ticket.
     - A kept `Part of` flips to `Fixes` only on a stated finish, because a wrongly closed ticket hides its remaining work while a wrongly open one stays visible in the tracker.

  anchors: row9, row14, row20
- **M4. Tests, all in `test_pr_lifecycle_skills.py` (row 59).**
  - **The layer-location guard**, named `test_no_project_layer_under_stowed_skills_dir` (rows 17, 27):
    - It derives the parents instead of listing them. A parent is every `SKILLS_DIR/<name>/SKILL.md` whose text holds the literal `` `.claude/skills/<name>-*/SKILL.md` ``. Today that is exactly the five `PARENT_SKILLS` names (row 63). Deriving them keeps `test_skills.py` out of the diff. It also ties the failure message's premise to each parent's own text. The derived list is sorted and skips a directory with no `SKILL.md`, as `test_skills.py:124-128` does.
    - A control holds the derived set in place. It is a separate, non-parametrized test, because pytest collects an empty parameter list as a skip. Its name, `test_layer_parents_are_derived_from_every_layer_loading_skill`, does not match the guard's `-k` string. It asserts that every SKILL.md with a heading containing "project-specific layer" is in the derived set, and that the set is not empty. A parent whose literal is reworded then fails this test instead of leaving the guard silently.
    - For each parent, `SKILLS_DIR.glob(f"{parent}-*/SKILL.md")` finds nothing.
    - The failure message lists the matched paths. It says the parent's glob reads `.claude/skills/` from the repo root, so a layer under `claude-skills/skills/` never loads and installs on every stow consumer.
    - On the current tree only the `pr-description` case fails. The name is unique, so `-k` on it selects only this test.
  - **`TestPrDescriptionTicketReference`**, five pins on the new bullet, found by its lead-in with `_bullet_text`. Each docstring names the regression it guards. The file's convention for a clause inside one bullet is a plain `in` check (`test_pr_lifecycle_skills.py:251-262`). `_assert_pinned_clause_right_bounded` passes only at a line or bullet boundary, and the bullet is one line (row 63).
    - Pins 1 to 4 are `in` checks. Each one's right edge is the end of its clause. Deleting or rewording a clause fails only its own pin. A contradicting clause inserted after one of them does not fail it.
      1. the `Fixes <TICKET-ID>` default, with its three named sources;
      2. the kept-`Part of` clause, with its "none of them says this PR finishes it" override;
      3. the no-closing-keyword-anywhere clause;
      4. the clause naming what the later PR covers.
    - Pin 5 runs from the exclusion sentence through the final unclear-means-`Fixes` sentence, which ends the bullet. It is right-bounded with `_assert_pinned_clause_right_bounded` against the raw `What the body must carry` section, where the next line opens the attribution-trailer bullet. A sentence appended at the bullet's end fails it.
    - No pin catches a contradicting clause inserted mid-bullet. The diff review in `/skill-review` and `/code-review` is that check. This limit is a choice. Chaining each pin to the next clause's opening words, as the file does at about :694-712, would close the gap. It would also make one deleted clause fail two pins. The class docstring states the limit, as `TestRespondPrStep3FailedRecipeSentence`'s docstring does for its pin.
  - Add `SKILLS_DIR` to the file's `helpers` import.

  anchors: row14, row17, row27, row59, row63
- **M5. `CHANGELOG.md`.** Add one entry under `[Unreleased]`, `### Changed`, with two sub-bullets, ending "See GH-1528.":
  - `/pr-description` cites a ticket as `Part of <TICKET-ID>`, with no closing keyword, when the caller, the engineer or the plan the work implements says a later PR will finish it.
    - To mark a phase PR, say so in plain words in the arguments passed to `/ready-for-review`, or in the plan the work implements. Say it on the run that first drafts the body. A later statement may not rewrite a published body that already carries `Fixes`, so edit that line by hand.
    - An existing `Part of` citation is kept unless one of them says this PR finishes the ticket.
    - Every other ticket still gets `Fixes <TICKET-ID>`, including a phase PR whose session holds no such statement.
    - GitHub does not list a `Part of` PR among the issue's linked pull requests.
  - **Migration:** the `pr-description-claude-config` skill is deleted. It was this repository's own project layer and never loaded. An install that `install.sh` produced drops it on `git pull`, with no re-run (row 6).

  anchors: row2, row6, row9

**Rows:**
1. `pr-description/SKILL.md:80` writes `Fixes <TICKET-ID>` whenever a ticket ID was passed in, "alongside any existing citation of it" [verified: `claude-skills/skills/pr-description/SKILL.md:80`]. Whether line 80 applies in sync mode at all is unestablished [unverified]. Three facts bear on it [verified: `pr-description/SKILL.md:22-24,81,128-129,201`]:
   - Line 80 sits under "What the body must carry", which author mode drafts from (:22).
   - Sync mode fetches the body and runs every check against it (:23-24, :128-129). No check names the closing keyword.
   - The trailer rule at :81 needed its own Checks bullet (:201) to reach existing bodies.

   The plan's handling of both readings is the Approach's "Sync mode" paragraph.
2. Only `/ready-for-review` passes a `<TICKET-ID>`. Step 1 runs `pr-create-preflight.py ticket`, which prints the branch's first path segment when it fully matches `[A-Za-z]+-[0-9]+`. Step 5 passes it with this run's `$ARGUMENTS` [verified: `ready-for-review/SKILL.md:42,117`; `pr-create-preflight.py:84,159-161,216-218`].
3. `/handoff` and `CLAUDE.md`'s PR-body rule run `pr-description` with no ticket ID [verified: `handoff/SKILL.md:173`; `claude/.claude/CLAUDE.md:181`].
4. The base skill globs `.claude/skills/pr-description-*/SKILL.md` from the repo root and merges a single match's items into its Checks. `docs/skills.md:251` names that path as the layer location [verified: `pr-description/SKILL.md:28-33`; `docs/skills.md:251,253`].
5. The claude-config layer sits at `claude-skills/skills/pr-description-claude-config/SKILL.md`. `.claude/skills/` holds only the code-review, plan-review and test-conventions layers, and `.claude/skills/pr-description-claude-config/SKILL.md` does not exist, so the layer has never loaded [verified: Glob of `.claude/skills/**/SKILL.md`; Read of the `.claude/skills/` path returned no such file].
6. `claude-skills/skills/` stows into every consumer's `~/.claude/skills/`, so the layer installs everywhere as a user-only `/pr-description-claude-config` command [verified: `CLAUDE.md` "Repo layout"; the layer's `disable-model-invocation: true`]. For installs `install.sh` produces, `~/.claude/skills` is one folded symlink to `claude-skills/skills/`. `stow-packages.sh` stows the `claude-skills` package at `.claude`. `install.sh` refuses a real directory or a foreign symlink at that path. Deleting the layer therefore removes it on `git pull`, with no dangling link and no re-run [verified: `stow-packages.sh:24-27`; `install.sh:344-354`; `.gitignore:190-194`; staff-product-engineer's round-1 check of this machine's per-account links, relayed]. A third-party installer that links each skill separately is unchecked [unverified].
7. The old layer has two triggers, and both would close more issues if loaded unchanged, against the Ask. Its first trigger requires a closing keyword on every `GH-<N>` branch, which would override any `Part of`. Its second turns any prose mention of an issue number into a closing keyword ("Rewrite a prose mention into closing-keyword form") [verified: `claude-skills/skills/pr-description-claude-config/SKILL.md:13-20`].
8. Retired with the layer (row 50): a layer's check item would have had the last word on the body.
9. GitHub links a PR to an issue "by using a supported keyword in the pull request's description," immediately followed by the reference (`Fixes #754`). The keywords are `close`, `closes`, `closed`, `fix`, `fixes`, `fixed`, `resolve`, `resolves` and `resolved`, and a bare mention neither links nor closes [verified: `pr-description/REFERENCES.md:227-234`, quoting GitHub Docs].
10. `Fixes GH-<N>` closes issue `N` on merge [verified: the dispatching session's `gh pr view 1300 --json number,state,closingIssuesReferences,body` this session, relayed. PR 1300 is merged, its body says "Fixes GH-1114.", and `closingIssuesReferences` lists issue 1114]. This PR's own `Fixes GH-1528`, and every final PR's `Fixes <TICKET-ID>` in this repo, rest on it.
11. Retired with the deferred issue read (row 42): `gh issue view` worked from this worktree for the dispatching session.
12. The interim note is a heading plus prose, not a `Closing PR:` line.
    - GH-1114, which is open, carries a level-two `Closing PR` heading. Its prose names the closing PR by ordinal and tells authors to remove `Fixes` by hand "until #1528 lands".
    - #1113's body says each multi-PR child names its closing PR in its own body.
    - The dispatching session's filter of #1118's body for "closing pr" matched nothing.

    The three facts come from reads the architect could not repeat [verified: staff-product-engineer's round-1 read-only read of #1113 and #1114, and the dispatching session's read of #1118, both relayed; the architect holds no `gh`]. The marker is therefore a new format, not a formalization of the note. Under the deferred near-miss answer (row 45), GH-1114's heading would read as a phase. The note's "until #1528 lands" instruction lapses when this PR merges (row 52). The note teaches a bare `GH-1114` citation. That citation matches neither arm of M1. Verification 9 rewords it before merge (row 58).
13. Outside base line 80 and the layer, no skill, hook, script or workflow writes a closing keyword into a PR body or commit message [verified: Grep for `closing keyword`, `Fixes #`, `Closes #` and `Fixes <` across the tree, with `.claude/plans/`, `CHANGELOG.md` and `docs/reports/` excluded]. The one parser of such keywords, `evals/comment_ab_pool_count.py:227-242`, takes a PR's issue from its title first, and a phase PR's title keeps its `GH-<N>:` prefix [verified: `pr-create-preflight.py:169-172`].
14. No test pins line 80 [verified: Grep of `claude-skills/skills/tests`]. Tests pin other bullets of "What the body must carry" by lead-in. `DEFAULT_TEMPLATE.md`'s two bullet pointers also name other bullets [verified: `test_pr_lifecycle_skills.py:236-249,349-362`]. Renaming this lead-in therefore breaks no pointer.
15. `pr-description/SKILL.md` is 247 lines against its 250-line cap and writes one paragraph per line [verified: Read; `check-skill-length.sh:137-138`; `docs/skills.md:174`].
16. Retired with the deferred marker (row 42): the repo has no issue template that could carry it.
17. `TestProjectLayerUsesReadNotSkill.PARENT_SKILLS` lists the five layer-loading parents, and only `pr-description-claude-config` matches `claude-skills/skills/<parent>-*/SKILL.md` today [verified: `test_skills.py:589`; Glob].
18. `select-tests.py` classifies a `SKILL.md` or auxiliary file under `claude-skills/skills/` as a skills change [verified: `select-tests.py:574,581`]. The rule mapping such a change to `claude-skills/skills/tests` sits at :740-741 [unverified: relayed from the exploration subagent].
19. The signal is a marker in the ticket's issue body [engineer-verified: "Issue-body marker (Recommended)"].
20. With no signal, the closing keyword stays [engineer-verified: "Keep closing default (Recommended)"].
21. The option descriptions attached to rows 19 and 20 are the dispatching session's words, not the engineer's. They said, all [unverified]:
    - formalize the interim note;
    - read it in the project layer;
    - have the generic skill take only a tracker-agnostic input;
    - leave single-PR tickets unchanged.

    This PR adopts only the last two items, on G2 and row 20, not on those descriptions. The project-layer read is deferred with the marker (row 42). Row 12 shows that the marker is a new format, not a formalization of the note.
22. When the issue body cannot be read, or carries more than one `Closing PR:` line, the PR is treated as a phase [engineer-verified: "Treat as phase (Recommended)"].
23. The option description attached to row 22's label is the dispatching session's words, not the engineer's. It said, both [unverified]:
    - the body gets `Part of #N` with no closing keyword;
    - the skill's report says the read failed.

    Both belong to the deferred marker work (row 42).
24. Rows 20 and 22 do not conflict. Row 20's question was scoped "When no signal says otherwise", and an unreadable ticket is unknown, not unmarked [unverified: the architect's reading].
25. The layer moves from `claude-skills/skills/` to this repository's `.claude/skills/` [engineer-verified: "Include the move (Recommended)"]. The engineer's typed question before that answer, "Isn’t .claude-skills supposed to be stowed to .claude/skills?", asked about the mechanism. The explanation they then saw was the dispatching session's.
26. The layer's prose-mention rewrite rule is dropped [engineer-verified: "Drop the rule (Recommended)"].
27. The layer-location guard test covers all five layer-loading parents [engineer-verified: "Include it (Recommended)"]. Its consequence is that no skill under `claude-skills/skills/` may be named `<parent>-*` for those five parents. The PR description lists it under Incidental edits with that consequence.
28. The Skill tool loads base skills from the stowed checkout, a different clone on the default branch. This worktree's edit to `pr-description/SKILL.md` therefore does not run through the Skill tool before merge. The installed `pr-description/SKILL.md:80` still reads "A closing-keyword reference" [verified: Read of the installed `pr-description/SKILL.md:80` this session; staff-sdet R2 and staff-product-engineer R5, relayed].
29. Retired with the deferred script (row 42): `/review-pr` pins a bare PR number to `origin` (`review-pr/SKILL.md:16`), and `review-pr-acquire.sh:253,284,309` filters GitHub text with `--jq`.
30. Retired with the deferred script (row 42): root `scripts/` holds repo-local scripts that are not stowed, tested from `claude/.claude/scripts/tests/` (`test_venv_run.py`).
31. Retired with the deferred script (row 42): no documented ruff root covers `scripts/`.
32. Retired with the deferred script's test file (row 42): `test_ticket_reference_discipline.py` scans `.py` files under `claude/`, and no file this PR touches is in that scan.
33. Retired with the relay (row 53): `ready-for-review/SKILL.md` stays out of the diff.
34. Retired with the relay (row 53): its Completion summary carries no ticket state, and this PR leaves that as it is.
35. GitHub's full set of closing syntaxes is unconfirmed beyond the keyword plus `#N` (row 9) [unverified].
    - Unconfirmed: the `owner/repo#N` form, a colon after the keyword, a full issue URL, and whether a keyword in a commit message that reaches the default branch closes the issue.
    - To confirm, fetch GitHub Docs "Linking a pull request to an issue" and quote its syntax table and any sentence on colons or commit messages.
    - The forms bear on M1's no-closing-keyword-anywhere clause and on Verification 6's scan pattern. The commit-message question bears on Out of scope's commit-message statement.
36. Retired: no text in this PR describes the issue timeline. CHANGELOG and the PR description say only that a `Part of` PR is not linked (row 9).
37. Retired with the deferred script (row 42): `.claude/settings.json` allows no command the script would need.
38. Retired: replaced by the engineer's near-miss answer for the deferred marker (row 45).
39. Retired: replaced by the engineer's marker-trust answer for the deferred marker (row 44).
40. Retired with the deferred script (row 42): `gh pr list --head` behavior when no PR is open stays unconfirmed.
41. Retired with the deferred script (row 42): the REST "Get an issue" `pull_request` key and nullable `body` stay unconfirmed.
42. This PR ships the light mechanism, and the issue-body marker of row 19 is deferred to a follow-up decided after using the light version. It is deferred, not dropped [engineer-verified: "Light now, marker later (Recommended)"]. Row 19 still records the engineer's choice of the marker as the signal.
43. The option description attached to row 42's label is the dispatching session's words, not the engineer's. It said, all [unverified]:
    - this PR ships the caller say-so, the kept `Part of`, the `TICKET:` line and its relay in `/ready-for-review`, the layer move and the dropped rewrite rule, at roughly 150 lines;
    - the issue-body marker and its script become a follow-up, decided after using the light version;
    - this PR would itself be a phase of GH-1528 unless the engineer closes the ticket on it.

    The engineer later chose to close the ticket on this PR (row 52).
44. For the deferred marker work only: the risk that an issue's author can edit the marker is accepted, and the follow-up states its assumption [engineer-verified: "Accept, state assumption (Recommended)"]. The assumption, in the architect's words, is that issue bodies behind `GH-<N>` branches are written by maintainers, or by authors who will not delete or retarget the marker. When it is false, the harm is an early close that a reopen undoes.
45. For the deferred marker work only: a line resembling the marker without matching it exactly reads as a phase [engineer-verified: "Treat as phase (Recommended)"].
46. For the deferred marker work only: the engineer approves each conversion of an open multi-PR ticket, and the session makes the edit [engineer-verified: "I approve each, session edits (Recommended)"].
47. `/plan-it` writes each branch's plan to `.claude/plans/<topic-slug>.md`, with the slug taken from after the branch's last `/`. It commits the plan to the implementation branch before implementation begins [verified: `plan-it/SKILL.md:23,151-154`]. A phase PR's governing plan often carries another name, though (row 61).
48. Retired: replaced by the engineer's evidence-standard answer (row 51).
49. Retired: replaced by the engineer's answer to close GH-1528 on this PR (row 52).
50. The layer is deleted instead of moved [engineer-verified: "Delete the layer (Recommended)"]. This later answer supersedes row 25's "Include the move (Recommended)", which stays as the record.
51. The phase signal is a rule with an evidence standard [engineer-verified: "Rule with evidence standard (Recommended)"]. Before that answer, the engineer typed "Arguments seems heavy handed. How would that work? Think it through" about a say-so typed into arguments.
52. This PR closes GH-1528, and the deferred marker moves to a new issue [engineer-verified: "Close it, new marker issue (Recommended)"].
53. The report line stating which way merging goes, and its `/ready-for-review` relay, are dropped [engineer-verified: "Drop it (Recommended)"].
54. The option descriptions attached to rows 51 and 52 are the dispatching session's words, not the engineer's. They said, all [unverified]:
    - for row 51, `Fixes` unless the caller, the engineer or the branch's plan says a later PR will finish the ticket, or the body already says `Part of`;
    - for row 51, the body names what the later PR covers;
    - for row 51, follow-up work outside the ticket does not count;
    - for row 51, when the session cannot tell, `Fixes`;
    - for row 51, nobody types anything;
    - for row 52, this PR says `Fixes GH-1528`;
    - for row 52, the dispatching session drafts a new issue for the deferred marker, carrying the design notes and the engineer's earlier answers, and shows the engineer the text before filing anything.

    M1's wording follows the row-51 items on its own grounds (rows 55, 56).
55. `/pr-description` runs in the invoking session, with that session's context.
    - `/ready-for-review` step 5 invokes it through the Skill tool (`ready-for-review/SKILL.md:117`).
    - Its frontmatter carries no `context: fork` (`pr-description/SKILL.md:1-12`), and a forked skill would get no conversation history (`docs/skills.md:186`).
    - The skill names no plan file anywhere, so line 80's mention of the plan is the only reason a session has to consult it.

    All three come from reads this session [verified: those files, and a Grep of `pr-description/SKILL.md` for "plan" that matched only its `## Test plan` lines].
56. The incident tickets' plans say in plain words that more PRs follow. `.claude/plans/split-test-lib.md:13` calls its outcome "a series of PRs", and `.claude/plans/session-signal.md:9` says the phase "must land before" later phases [verified: read this session]. The consult also cites `.claude/plans/measure-review-quality.md:386,618` and `.claude/plans/decomposition-skill.md:1,11` [unverified: relayed, not read]. Whether each plan was in the session's context when its PR body was written is [unverified].
57. M1's target wording is the consult's proposal for line 80, which the dispatching session quoted whole. The consult's other points reached the architect as the dispatching session's summary [verified: the dispatch prompt]. The consult claims M1 relies on are rows 1, 55 and 56.
58. Rewording #1114's `Closing PR` note and #1113's Related line is a step before merge, with each edit approved [engineer-verified: "Yes, I approve each edit (Recommended)"].
59. The guard test goes in a test file other than `test_skills.py` [engineer-verified: "Another test file (Recommended)"]. Row 27's inclusion across all five parents stands.
60. The option descriptions attached to rows 58 and 59 are the dispatching session's words, not the engineer's. They said, all [unverified]:
    - for row 58, the plan gains one pre-merge step, and the session shows the exact new text for each issue and edits only after the engineer's go-ahead for that edit;
    - for row 59, the test goes in `claude-skills/skills/tests/test_pr_lifecycle_skills.py`, which this PR already edits, so `test_skills.py` leaves the diff.
61. For four incident PRs (#1300, #1521, #1387, #1517), no plan named for the branch's last path segment existed at merge. Each had a governing plan under another name: `measure-review-quality.md`, `transcript-analysis-decomposition.md` or `split-test-skills.md`. At #1300's merge, `measure-review-quality.md` named "PR 2a", "PR 2b" and "PR 3" in plain words [verified: staff-product-engineer's round-2 read-only `gh` and `git` reads, relayed; the architect holds no `gh`].
62. GH-1114 is open, and its `Closing PR` note tells authors to remove the `Fixes` line by hand until #1528 lands. GH-1116 and GH-1118 are closed, with phases still unchecked and no `Closing PR` note. #1113's Related line reads "Until it lands, each multi-PR child names its closing PR in its own body." [verified: staff-product-engineer's round-2 reads, relayed].
63. The pin and derivation mechanics M4 relies on:
    - `_assert_pinned_clause_right_bounded` passes only at a structural boundary: section end, a blank line, or a `-` bullet or `#` heading on the next line [verified: `_skill_md_helpers.py:490-496`].
    - `_bullet_text` returns a bullet collapsed onto one line [verified: staff-sdet's round-3 read of `test_pr_lifecycle_skills.py:137-154`, relayed].
    - The same file pins clauses inside one bullet with a plain `in` [verified: `test_pr_lifecycle_skills.py:251-262`].
    - Exactly five SKILL.md files under `claude-skills/skills/` hold their own `` `.claude/skills/<name>-*/SKILL.md` `` literal: code-review, plan-it, plan-review, pr-description and test-conventions. They are the five `PARENT_SKILLS` names [verified: Grep this session; `test_skills.py:589`].

## Critical files

- `claude-skills/skills/pr-description/SKILL.md`: replace line 80 in place (M1). The file stays at 247 lines.
- `claude-skills/skills/pr-description/REFERENCES.md`: the pointer rename at :182-183 and five sentences after :234 (M3).
- `claude-skills/skills/pr-description-claude-config/SKILL.md`: deleted with `git rm` (M2).
- `claude-skills/skills/tests/test_pr_lifecycle_skills.py`: the layer-location guard and `TestPrDescriptionTicketReference` (M4). Reuse `_raw_heading_section_text`, `_skill_file` and `_assert_pinned_clause_right_bounded` from `_skill_md_helpers`, the file's own `_bullet_text`, and `SKILLS_DIR` from `helpers`.
- `CHANGELOG.md`: one `[Unreleased]` entry (M5).

Left untouched:
- `test_skills.py`, which an in-flight split may hold (row 59). The guard derives its parents instead of importing `PARENT_SKILLS` (M4).
- `ready-for-review/SKILL.md` and `test_ready_for_review_skill.py`, because the relay is dropped (row 53).
- `pr-create-preflight.py`, `handoff/SKILL.md` and `claude/.claude/CLAUDE.md`, because no caller passes anything new (rows 2, 3).
- `docs/skills.md`, whose project-layer section describes the mechanism generically and stays true with no `pr-description` layer here (row 4).

Dispatch split: one `code-writer` dispatch for all five paths. The bullet and its pins are one contract, so splitting them would restate it in every prompt. Inside the dispatch, write the guard test first and run it against the current tree (Verification 1), then make the rest of the change. The tracker steps (Verification 8 and 9) stay with the session, because each needs the engineer's go-ahead.

Projected diff: about 100 lines.
- The deleted layer: 24 lines.
- `test_pr_lifecycle_skills.py` about 60: the guard about 22, and the pins about 38.
- `REFERENCES.md` about 8, and `CHANGELOG.md` about 7.
- `pr-description/SKILL.md` 2.

## Verification

No step edits an issue or posts a body, except steps 8 and 9. Each of those acts only on the engineer's go-ahead for its exact text (rows 52, 58).

1. **The guard fails first.** Before the `git rm`, add the guard and run `scripts/venv-run.sh pytest claude-skills/skills/tests/test_pr_lifecycle_skills.py -k test_no_project_layer_under_stowed_skills_dir -v`. Expect the case IDs to be exactly the five names at `test_skills.py:589`. Expect only the `pr-description` case to fail, with its message listing `claude-skills/skills/pr-description-claude-config/SKILL.md`. After the deletion, all five cases pass. This step still earns its place for a deletion, because it shows the guard catches the exact shape the deletion removes.
2. **Lint.** Run `scripts/venv-run.sh ruff check claude-skills/`.
3. **Skill review and line cap.** `/code-review` dispatches `/skill-review` for the `pr-description/SKILL.md` diff and the deleted layer. The commit-time `check-skill-length.sh` must pass, with `pr-description/SKILL.md` at 247 of 250 lines.
4. **Freeze the text.** After the last edit to `SKILL.md:80`, `/skill-review`'s tightening included, record `git hash-object claude-skills/skills/pr-description/SKILL.md` for the Test plan. Steps 5 and 6 run against that text. If line 80 changes again, rerun steps 4 to 6.
5. **Scoped suite.** Run `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py`. Expect it to select `claude-skills/skills/tests` (row 18) and pass.
6. **Five readings of the frozen bullet.** Run each case from this worktree's `claude-skills/skills/pr-description/SKILL.md`. The Skill tool would load the stowed copy instead (row 28).
   - Dispatch one `general-purpose` subagent (`model: sonnet`) per case, so this session's knowledge of GH-1528 stays out of the result.
   - Each gets the SKILL.md path, the placeholder ticket ID `PROJ-1`, and its case's inputs, all in a temp directory outside the repo.
   - Each writes the summary paragraph and ticket lines it would draft to a scratch file.
   - The parent scans each file itself, with a case-insensitive pattern: one of the nine keywords (row 9) as a whole word, an optional colon, whitespace, an optional `#`, then `PROJ-1`. Nothing is posted.
   - Before the cases, run the scan once on the known-bad string `Fixes #PROJ-1` and expect a match, so the scan is shown able to fail.

   The cases:
   - **Phase, with discovery.** A scratch tree whose `.claude/plans/` holds a copy of `.claude/plans/session-signal.md`, with its ticket ID swapped to `PROJ-1`. The subagent gets only the tree, the ticket ID, and a branch name for the phase that plan governs, with a slug that differs from the plan's file name. Expect it to find that plan, write `Part of PROJ-1` and a sentence naming what the later phases cover, and give no scan match. Record which plan it read and whether it judged the plan to govern the branch. If it finds none, record that, then rerun with the plan's path supplied.
   - **No later PR.** A scratch plan written for this case, supplied by path, for a single-PR ticket. It has implementation phases, speaks of later PRs in general terms, and defers follow-up work to another issue. It nowhere says which PR closes the ticket. Expect `Fixes PROJ-1`.
   - **Final PR of a series.** A scratch plan for a whole series, with every phase listed as planned and none marked merged. The subagent is told, through the branch name, that it is on the last phase. Expect `Fixes PROJ-1`, and record the outcome either way. If it writes `Part of`, line 80 needs "later than this PR" made explicit before merge.
   - **Kept `Part of`, sync framing.** An existing body file citing `Part of PROJ-1`, and a plan that says nothing about other PRs. Expect the citation kept and no scan match.
   - **Kept `Part of`, stated finish.** The same body file, and a plan saying this PR finishes `PROJ-1`. Expect `Fixes PROJ-1`.

   One run per case is evidence, not proof.
7. **What the Test plan records.**
   - The hash from step 4, and that the readings ran on scratch inputs.
   - Which case found its plan, and which had it supplied by path.
   - What was not run before merge: the new bullet through the Skill tool, which first runs after merge and pull (row 28), a live sync of a published body, and plan discovery beyond the one scratch case.
   - That this PR's own body takes the unchanged default. The installed base writes `Fixes GH-1528` (row 10).
8. **Before merge, on the engineer's go-ahead: file the follow-up issue** (row 52). Show the engineer the dispatching session's draft, and file it only after they approve that text. The draft carries the deferred marker's notes, the residual (Approach, "Residual") and the pending checks of step 11. The PR body then cites the new issue's number.
9. **Before merge, one edit at a time on the engineer's go-ahead: reword the interim notes** (row 58). For #1114's `Closing PR` section and for #1113's Related line, show the exact new text, and edit only after the engineer approves that edit. Each new text says, in plain words, for its ticket or for #1113's children:
   - cite the ticket as `Part of GH-<N>`, not bare `GH-<N>`, so a sync keeps it;
   - say in the `/ready-for-review` arguments, or in the plan the work implements, that a later PR finishes the ticket, because a PR with no such statement still gets `Fixes`;
   - say it on the run that creates the PR, because a statement made on a later run may not rewrite the body;
   - check the body for `Fixes` before merge, until the follow-up issue from step 8, named by its number, lands.

   Record both edits in the PR's Test plan.
10. **Before publishing, scan this PR's own body.** Scan the raw body text, code spans included, with step 6's pattern, for a closing keyword before any issue reference other than `GH-1528`, in the `GH-<N>` and `#<N>` forms. Expect no match, and record the scan in the Test plan. GH-1114 is open, and a keyword before its reference would close it on merge.
11. **After merge, the first live checks.** The PR body names both as pending, and the follow-up issue tracks them.
    - The first phase PR whose caller, engineer or plan says a later PR will finish its ticket shows `Part of <TICKET-ID>`.
    - That ticket's final PR shows `Fixes <TICKET-ID>` and closes it.

Merge-time closing is GitHub's behavior (rows 9, 10), so these checks stop at the body.

## Out of scope

- **The issue-body marker (rows 19, 22, 42, 44, 45, 46).** It moves to the follow-up issue that Verification 8 files (row 52). That issue carries the design notes and the engineer's answers.
- **A report line stating which way merging goes, and its relay in `/ready-for-review`.** The engineer dropped both (row 53).
- **Reopening GH-1116 or GH-1118.** Both stay closed, with phases unchecked (row 62). The PR body says so.
- **Automatic detection for other stow consumers.** They get the same evidence standard. A project layer of their own can add more.
- **Closing keywords in commit messages.** The guarantee covers the PR body only. No skill writes a closing keyword into a commit message (row 13). A hand-written one may still close the issue once it reaches the default branch (row 35).
