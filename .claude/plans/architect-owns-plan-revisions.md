# Plan-review findings go to the architect only

## Context

Goal: make `plan-architect` the only agent that decides on and applies edits to a plan file in response to `/plan-review` and `/code-review` findings, so neither the parent session nor `code-writer` rewrites plan sections after a review returns.

Ask: "I would like another agent (so write a brief for this) to work on a plan-it session on making sure that plan-review feedback ONLY gets reviewed and decided upon by the architect who then makes the changes." — accepted via label "Use the brief's quote".

Why now: `/plan-it` Step 5 already makes `plan-architect` author the plan's sections and re-dispatches it after a failed shape check, but nothing names an actor for review findings:
- `plan-it` Step 6 says "Address any findings" with no actor.
- `plan-review`'s "Plan prose findings" pass applies accepted edits itself.
- `/code-review`'s fix route names no owner for a staged plan file's edit, and `subagent-delegation/SKILL.md:170` keeps a plan-file edit inline.

The cost is churn: each review-time edit gives the next review round something new to find, and plans grow defensive text no engineer decision asked for.

Engineer decisions this session, as the labels they selected:
- "Architect decides (Recommended)", on who decides a finding.
- "Skill text only (Recommended)", on enforcement.
- "Accept narrow exception", on ledger rows. The session that asked the engineer appends only a templated, verbatim-quote row, and every follow-on edit goes to the architect.

Paths covered were proposed by the session and not objected to: `/plan-it` Step 6, `/plan-review`'s prose-fix pass, and `/code-review`'s fix route for a staged plan.

`#1212` and `#1567` stay separate.

Base is current `main`. `goal-frame-gates` has no commits of its own.

## Approach

Every edit to a plan's sections that a `/plan-review` or `/code-review` finding prompts goes through one `plan-architect` revision re-dispatch. The architect accepts, declines or opens each finding and applies only what it accepts. The session's only write in that region becomes an append-only row recording an answer it asked the engineer for. The rule and its one exception live in `plan-it` Step 5, beside the revision re-dispatch they reuse. `plan-review`, `code-review`, `review-orchestrator`, `subagent-delegation` and `plan-it` Step 6 point there, and `plan-architect.md` holds the standard the architect decides by.

Paths are repository-relative. A bare `file:N` cites the merge-base.

**Alternatives set aside.**
- A hook enforcing the rule. The engineer chose skill text (row 3). The over-powered-primitive note under M1 says why a hook adds nothing the primitives already in play lack.
- Two dispatch sites: `plan-it` Step 6 for **Request changes** findings, with `/plan-review` keeping its in-run edits for **Approve with changes**. A standalone `/plan-review` run would then have no route, and the completion marker must follow the edits inside the run (row 10). One site inside `/plan-review`'s run serves both verdicts.
- Homing the single-writer rule in `plan-architect.md`. The dispatching sessions decide who edits, so the rule belongs where they read. The agent body holds only the standard it applies.
- Homing it in `plan-review`. `code-review` needs it too and already cites `plan-it` Step 5 for plan revisions twice (row 8).
- A `MODE=consult` decision followed by a separate revision dispatch, as the heavier-mechanism route does. That doubles the Opus dispatches per round. A `MODE=plan-sections` dispatch can decide and edit in one pass once its charter carries the standard.
- Letting a declined blocker stand without the engineer. Fresh re-review reviewers can re-raise it with no settled record, so the round never converges. `plan-review`'s fix-or-ask rule already demands an engineer answer for the enforcement-invariant class (row 14).
- Editing `code-review`'s contradiction-route and fix-plan-pilot regions to name the plan route. Both are pinned whole and evaluated by hand (row 19). One clause at the `Fix route:` line, scoped to "whichever rule made it ADDRESS", reaches their ADDRESS rows instead.
- Running `/plan-review`'s dispatch before `marker.sh deactivate plan-review`. A Step 5 stop would then leave the active marker live, and that marker lets every non-plan write past the plan-review gate. No gate needs it for the dispatch (row 30).
- `review-orchestrator` running the `plan-architect` dispatch itself. It holds no `Edit` for Step 5's splice and cannot ask the engineer at Step 5's stops. The dispatcher holds both, so it runs the dispatch after the orchestrator's `HALT:` (row 17).

**M1 — `plan-it` Step 5 gains a Review findings paragraph** (anchors: root, row 1, row 8, row 14). Insert it after the paragraph starting "A near-empty return is the success shape" and before the one starting "`claude/.claude/agents/plan-architect.md` § "Design principles"", as a one-line paragraph followed by three flush bullets:

> **Review findings.** Only `plan-architect` edits a plan from its `## Approach` heading down in answer to a `/plan-review` or `/code-review` finding, and it gets a review round's findings together in one revision re-dispatch. After line 2, that prompt carries the findings in place of the Context and Step 3 evidence bullets: numbered, each as the review rendered it, under a lead-in naming the review and round, with the findings-file path of each reviewer that wrote one. Mark a finding `blocking` when it made a `/plan-review` verdict **Request changes** or `/code-review`'s enforcement-invariant rule covers it. On the return:
> - Relay each `decline` line to the engineer with its reason.
> - Ask each `open` line as an open decision above.
> - Re-dispatch once more with only the findings the return gave no line, and ask any still without one as an open decision.

Over-powered-primitive note for the rejected hook (anchors: row 3, G1). Three lighter primitives already in play carry the rule:
- `plan-it` Step 5's revision re-dispatch. `code-review` already routes two plan edits through it (row 8), so pointing every review site at it adds a call site, not a mechanism.
- `require-plan-review.sh`'s content-hash marker. Any edit to an active plan after a review re-arms the gate (row 9), so a stray edit by the session or `code-writer` costs a review round rather than shipping unreviewed.
- `plan-review/ROUTING.md`'s Ledger cross-check (row 15). Every re-review diffs the plan against its `[engineer-verified]` rows, so an edit that overrides an engineer answer reaches the engineer.

A hook fails where these hold. It sees an edit's strings and agent type, never the finding behind it (G1). To still allow the session's Context edits, Effort sections and exception rows, it would need byte-offset matching over `old_string` in bash, the shape the edit-grant decision already rejected (row 23).

**M2 — `plan-architect.md` states the standard and the return shape** (anchors: row 1, row 2, row 12, row 13).
- Frontmatter `description`, mode (1): after "from that run's exploration evidence" add ", or to decide and apply review findings on those sections in Step 5's revision re-dispatch".
- The MODE=plan-sections bullet "When your edits land, your return carries no `## ` heading lines — only any open decision." becomes "When your edits land, your return carries no `## ` heading lines — only any finding lines and any open decision." The pinned prefix stays.
- After the bullet list, before the paragraph starting "When you return your sections instead of editing", add this block, hard-wrapped like its neighbours:

> When the prompt carries numbered review findings, decide each one before you edit:
>
> - Accept a finding when its defect meets the Review stance's bar for a rejection, under `MODE=consult`, with the plan as the proposal. Apply it as targeted `Edit`s, a finding marked `blocking` included.
> - Decline it otherwise, or when an `## Out of scope` entry already excludes its fix.
> - Answer `open` instead when its fix would revise an `[engineer-verified]` row's quoted content, or when you would decline a finding marked `blocking`, and state the open decision.
>
> Before any region you return, give one line per finding, in order: `<n>. accept`, `<n>. decline: <reason>` or `<n>. open`.

- "give one line stating the reason, then your region in full" becomes "give one line stating the reason, then any finding lines, then your region in full". `plan-it` Step 5's splice takes the return from its `## Approach` line on, so the finding lines never reach the file.

**M3 — `/plan-review` sends its findings to the architect** (anchors: row 4, row 5, row 10, row 15, row 25, row 30).
- `claude-skills/skills/plan-review/SKILL.md` Step 4, "Measure against the ask": the sentence "Record each answer on its own ledger row quoting it." becomes:

> Record each answer as one row, as the **Engineer answers.** paragraph of `plan-it/SKILL.md` § "Step 5 — Architecture design" says, claiming "<item> stays in this plan's scope" for a kept item or "<item> leaves this plan's scope" for a declined one.

- Same paragraph, directly after the sentence recording `Split now`, add:

> Record `Proceed anyway` as the row "This plan goes ahead at its `Projected diff:` without a split", tagged `[engineer-verified: "Proceed anyway"]`.

- Output format, **Plan prose findings**, second bullet: "A round whose only findings are plan prose ends **Approve with changes** when you accept any of them. It ends **Approve** otherwise. The completion marker follows once the accepted edits are applied." becomes:

> A round whose only findings are plan prose ends **Approve with changes**. The completion marker follows once the `plan-architect` dispatch that "Record review completion + deactivate" names is complete.

  The verdict now precedes the architect's decision, so it cannot depend on what the architect accepts.
- Same list, last bullet: "Apply each one you accept in the same edit pass as the round's other changes, and name any you decline with the reason." becomes "Send them with the round's other findings in that one dispatch."
- § "Record review completion + deactivate": directly after the deactivate fence, before the marker sentence, add a paragraph:

> Next, when this run returned any finding or a Step 4 answer needs a follow-on edit, send every such finding and edit to `plan-architect` in one revision re-dispatch, as the **Review findings.** paragraph of `plan-it/SKILL.md` § "Step 5 — Architecture design" says.

  It runs after the deactivate call, so a Step 5 stop, an errored dispatch or the plan-mode path stop cannot leave the active marker live, and no gate needs that marker for the dispatch (row 30). A clean round with no follow-on edit dispatches nothing. Each fixture comment stays directly above its fence.
- Same section, the marker sentence becomes:

> Then write the completion marker, but only when the verdict is **Approve** or **Approve with changes** and any such dispatch, with any re-dispatch it led to, is complete. Do not write it on **Request changes** — write it only after `plan-architect` revises the plan and a clean re-review completes.

- `claude-skills/skills/plan-review/ROUTING.md:55`: "What's been applied stays inline regardless:" becomes "Each finding `plan-architect` accepted that round, as what's been applied, and each one it declined, with its reason, stay inline regardless:". The rest of the bullet stays. The session takes both from its own dispatch prompt and the architect's finding lines, since it no longer makes the edits itself.

A plan in a harness plan-mode file is outside `.claude/plans/`, and Step 5 stops on its path (row 22). Findings on such a file therefore end at that stop, which tells the engineer to leave plan mode. No session edit replaces it.

**M4 — `/code-review` and `review-orchestrator` route a plan edit the same way** (anchors: row 4, row 16, row 17, row 18, row 31).
- `claude-skills/skills/code-review/SKILL.md:359`, inside the existing `Fix route:` paragraph, directly after "naming whichever of that rule's carve-outs applies.", add the following on the same line, so the file gains no line:

> An ADDRESS row whose fix edits a plan from its `## Approach` heading down, whichever rule made it ADDRESS, sends that edit to `plan-architect` as `plan-it/SKILL.md` § "Step 5 — Architecture design" says, and this line names `plan-architect — plan revision` for it. The rest of its fix keeps its usual route, which runs first because a plan edit re-arms `require-plan-review.sh`.

  "Whichever rule made it ADDRESS" reaches the contradiction route's *Apply this round's fix*, a fix-plan table row, the round-cap one-defect verdict and a conceded challenge flip. None of those pinned regions changes. A row editing the plan above `## Approach`, such as its Context or `Ask:` line, keeps today's route, as `/plan-review`'s session keeps that region. In the inline flow the next round reviews the staged diff, so the session stages the plan edit as it stages `code-writer`'s.
- `claude-skills/skills/subagent-delegation/SKILL.md:170`, in place, so the file stays at its 218-line cap (row 31): "- Not code (the review-findings PR-body block, a `respond-pr` reply, a plan-file edit) — stays inline." becomes:

> - Not code (the review-findings PR-body block, a `respond-pr` reply, a plan-file edit) — stays inline, except a plan-file edit that `plan-it/SKILL.md` § "Step 5 — Architecture design" gives to `plan-architect`.

- `claude/.claude/agents/review-orchestrator.md` item 6: after its first sentence, add "A plan edit the skill's Fix route sends to `plan-architect` goes under `HALT:` with its ADDRESS row verbatim, a `blocking` mark when the enforcement-invariant rule covers it, and its reviewer's findings-file path, naming `plan-architect — plan revision` as its rule. The round goes on as after a stop-and-ask about one finding, and `code-writer` gets only the rest of its fix." Step 5's **Review findings.** prompt needs those fields, and item 8's own fields carry neither the suggested fix nor the findings-file path. Item 7 then writes no marker (row 17).
- `claude-skills/skills/subagent-delegation/SKILL.md:215`, in place: "- With any `HALT:` entry, name the paths just staged," becomes:

> - With any `HALT:` entry, first dispatch `plan-architect` once with every entry naming `plan-architect — plan revision`, as `code-review/SKILL.md` § "Finding disposition" says, and stage that plan as step 2 stages `Fix paths:`. Then name the paths just staged,

  The rest of the line stays. The inline round that follows then reviews the plan edit with the round's other fixes.

**M5 — the engineer-answer exception** (anchors: row 5, row 6).
- `plan-it` Step 5, directly after M1's bullets, as a one-line paragraph followed by three flush bullets:

> **Engineer answers.** The one exception is the session recording an answer it asked the engineer for: a `/plan-review` Step 4 answer, or an after-approval addition under **Critical files** below. Append one row per answer after the ledger's last row, with the next row number, `anchors: root`, the claim the asking step gives, and the answer quoted byte for byte in the `[engineer-verified: "<quote>"]` tag. Its limits:
> - Never edit or renumber an existing row, and change nothing else from `## Approach` down except an added Critical file's path.
> - Send every follow-on edit the answer needs to `plan-architect`.
> - An answer to an open decision `plan-architect` returned is not this exception, so re-dispatch with it as above.

- `plan-it` Step 5, section list item 3 (**Critical files**): "The session then adds it to the list itself, with its own `[engineer-verified: "<quote>"]` row or, if it widens the Ask, on the Ask line." becomes "The session then adds it to the list under **Engineer answers.** above, quoting the answer in the row "`<path>` joins this plan's Critical files", or on the Ask line instead when it widens the Ask." Both of today's homes for the quote survive.

The row claims, one per Step 4 answer kind:
- Kept item: "<item> stays in this plan's scope".
- Declined item: "<item> leaves this plan's scope". Removing the item is a follow-on edit for `plan-architect`.
- `Proceed anyway`: "This plan goes ahead at its `Projected diff:` without a split".
- `Split now`: the existing text at `plan-review/SKILL.md:96`, unchanged. The cut is a follow-on edit for `plan-architect`.

**M6 — `plan-it` Step 6 names the loop** (anchors: row 4). "Invoke `/plan-review` against the written plan file. Address any findings before presenting the plan to the user." becomes:

> Invoke `/plan-review` against the written plan file. It sends its findings to `plan-architect` under Step 5's **Review findings.** paragraph. Re-run it after each **Request changes** verdict, and present the plan only after a round ends **Approve** or **Approve with changes**.

**M7 — pins, decision record, changelog** (anchors: row 11, row 19, row 20, row 21).
- `claude-skills/skills/tests/test_plan_pipeline_skills.py`:
  - Add four entries to `_PINNED_PLAN_IT_STEP5_SCRIPT_CLAUSES`: M1's lead paragraph, M1's three bullets as one clause, M5's lead paragraph, and M5's three bullets as one clause. `no_return_redispatch_bullets` already pins bullets this way. `_assert_pinned_clause_right_bounded` (`_skill_md_helpers.py:490`) accepts a clause only when it ends at a blank line or before a line starting `-` or `#`, so each lead paragraph and each bullet run is pinned whole.
  - Add "`MODE=plan-sections` as the prompt's first line" to `_PLAN_IT_STEP5_CONTEXT_CHECK_AND_GRAMMAR_LITERALS`, since the consult latch skips only that exact first line (row 11).
  - Add `_PLAN_ARCHITECT_REVIEW_FINDINGS_BLOCK`, holding M2's new block from "When the prompt carries numbered review findings" through its finding-line sentence. Add `_PLAN_ARCHITECT_FINDING_LINES_BEFORE_REGION_SENTENCE`, holding "give one line stating the reason, then any finding lines, then your region in full", which keeps the finding lines out of Step 5's splice.
  - Add one test for each constant beside `test_plan_sections_charter_return_carries_no_headings_when_edits_land`. Each compares its constant, whitespace-collapsed as `" ".join(text.split())`, against the hard-wrapped MODE=plan-sections section. The block test's failure message says to re-run Cell A by hand, as `rerun_note` does for the prose cells (`test_review_dispatch_contracts.py:286-289`).
- `claude-skills/skills/tests/test_review_dispatch_contracts.py`:
  - `approve_with_changes_literal` becomes "A round whose only findings are plan prose ends **Approve with changes**."
  - Add one test, parametrized by site, asserting that each file's whitespace-collapsed text carries its routing phrase:
    - `plan-review/SKILL.md`: "to `plan-architect` in one revision re-dispatch".
    - `plan-review/SKILL.md`: "as the **Engineer answers.** paragraph".
    - `plan-review/SKILL.md`: "Send them with the round's other findings in that one dispatch".
    - `plan-review/ROUTING.md`: "Each finding `plan-architect` accepted that round".
    - `plan-it/SKILL.md`: "It sends its findings to `plan-architect`".
    - `plan-it/SKILL.md`: "under **Engineer answers.** above".
    - `code-review/SKILL.md`: "names `plan-architect — plan revision` for it".
    - `review-orchestrator.md`: "the skill's Fix route sends to `plan-architect`".
    - `review-orchestrator.md`: "`code-writer` gets only the rest of its fix".
    - `subagent-delegation/SKILL.md`: "gives to `plan-architect`".
    - `subagent-delegation/SKILL.md`: "once with every entry naming `plan-architect — plan revision`".
- New `docs/design-decisions/plan-architect-decides-review-findings.md`, in `.claude/rules/design-decisions.md`'s format, about 50 lines. It needs an H1, an italic provenance line with the authoring date, and a lead paragraph citing the M1 paragraph by `` `plan-it/SKILL.md` § "Step 5 — Architecture design" `` without restating it. Then one short section for each of these:
  - Why the architect decides: each review-time writer adds text no engineer decision asked for.
  - Why skill text and not a hook: G1 and row 23, citing `code-review-fix-route-plan-architect.md` and `plan-architect-writes-its-own-plan-sections.md`.
  - Why engineer answers are the one exception: the session that asked holds the quote, and a templated append carries no design text.
  - Why a prose-only round always ends **Approve with changes**.
  - Why `/plan-review`'s dispatch follows its deactivate call (row 30), and why `code-writer` runs before `plan-architect` in a `/code-review` round (row 16).
  - Cost: each review round with findings adds one Opus dispatch, plus at most one for findings the return left without a line, besides Step 5's own re-dispatches.
  - Accepted residuals:
    - The `code-review` ledger keeps a declined ADDRESS row as logged.
    - A plan-mode file stops at Step 5's path refusal.
    - A plan without the four headings stops at `check`.
    - A plan-edit `HALT:` runs the rest of a routed review loop inline (`review-orchestrator-routing-gate.md:57`).
    - A plan edit during `/code-review` re-arms the plan-review gate (`plan-architect-writes-its-own-plan-sections.md:23`).
  - Sources.
  - A Measurement note, which the session adds after Verification steps 6-8.
- `CHANGELOG.md`, `## [Unreleased]` → `### Changed`: one new first bullet saying that only `plan-architect` now edits a plan's sections in answer to `/plan-review` and `/code-review` findings. Its sub-bullets say three more things:
  - A plan-prose-only round now always ends **Approve with changes**.
  - `/code-review` and `review-orchestrator` send an ADDRESS row's plan edit to `plan-architect` instead of fixing it inline or through `code-writer`.
  - The session still appends one templated row for each answer it asked the engineer for.

**Assumption ledger**

**Root:** Three routes let a writer other than `plan-architect` change a plan's sections after a review. `/plan-review`'s session applies the prose fixes it accepts and the round's other changes. `/plan-it` Step 6 tells an unnamed actor to "Address any findings". `/code-review` keeps a plan-file fix inline under `subagent-delegation`'s not-code carve-out, and `review-orchestrator` dispatches `code-writer` with every ADDRESS row that edits a tracked file. Each writer can add text no engineer decision asked for. This plan makes `plan-architect` the only writer of a plan's sections in answer to a finding. `[verified: plan-review/SKILL.md:276-280, 297; plan-it/SKILL.md:145; code-review/SKILL.md:359; subagent-delegation/SKILL.md:170; review-orchestrator.md:22-25]`

**Givens:**
- G1. A `PreToolUse` hook sees a tool call's input and the calling agent's type, never the review finding that prompted an edit. Reason: the Claude Code hook contract is the vendor's. `[verified: docs/design-decisions/code-review-fix-route-plan-architect.md:7; docs/design-decisions/plan-architect-writes-its-own-plan-sections.md:19]`

**Rows:**
1. `plan-architect` decides each finding. `[engineer-verified: "Architect decides (Recommended)"]` Covers only who decides. — anchors: root
2. The flow in that option's description is the session's proposal, and this design adopts it. The parent relays findings verbatim. The architect accepts or declines each against the plan's recorded engineer decisions and Out of scope, applies what it accepts, and returns declines with reasons. The parent asks the engineer only the open decisions the architect returns. `[unverified: session proposal, relayed by the dispatching session]` — anchors: row 1
3. No hook enforces the rule. `[engineer-verified: "Skill text only (Recommended)"]` — anchors: root
4. The sites in that option's description are the session's proposal, and the engineer did not object to them: `plan-it` Step 6, `plan-review`'s prose pass and `code-review`'s fix route. `[unverified: relayed by the dispatching session]` This plan adds `review-orchestrator` item 6, `ROUTING.md:55` and `subagent-delegation/SKILL.md:170, 215` as the same routes' sibling arms (rows 15, 17, 31). — anchors: row 3
5. The session that asked the engineer appends a row recording the answer. `[engineer-verified: "Accept narrow exception"]` — anchors: root
6. The exception's terms come from the session's proposal, which an earlier consult drafted. They are:
    - The next row number.
    - `anchors: root`.
    - A template claim.
    - The quote byte for byte.
    - No edit or renumbering of an existing row.
    - Nothing else touched from `## Approach` down.
    - Every follow-on edit to `plan-architect`.
    - The exception stated beside the single-writer rule, with `plan-review` Step 4 pointing there.
    - `plan-it`'s after-approval Critical-files addition as a second instance.
    - Open decisions `plan-architect` returned staying with it.
    `[unverified: relayed by the dispatching session]` — anchors: row 5
7. The brief keeps `#1212` and `#1567` separate. It also puts four things out of scope: round-count triggers, `code-review`'s non-plan handling, hardening added because a reviewer asked, and private-project detail. `[unverified: the brief, relayed by the dispatching session]` — anchors: root
8. `code-review` already sends two plan edits through `plan-it` Step 5's revision re-dispatch: the round-cap re-plan verdict and an endorsed heavier mechanism. `[verified: code-review/SKILL.md:326, 378]` — anchors: root
9. A write targeting a repository plan file passes `require-plan-review.sh`. Any edit to an active plan changes its hash, so no marker matches and the gate denies the next non-plan write. `[verified: require-plan-review.sh:201-206, 284-286, 302-319]` — anchors: M1, M4
10. `/plan-review` writes its completion marker only once the required changes are applied. It removes its active marker at the end of every run. `[verified: plan-review/SKILL.md:290, 297]` — anchors: M3
11. `review-trace` does not count a `plan-architect` dispatch whose first line is `MODE=plan-sections` as an architect consult. `[verified: claude/.claude/scripts/transcript_analysis/review_trace.py:44-45, 143-147, 755-757]` The per-branch consult latch skips the same first line, so the added dispatches leave consult counts unchanged. `[verified: claude/.claude/hooks/log-reviewer-round.sh:123-127; claude/.claude/hooks/tests/test_log_reviewer_round.py:482]` The latch matches that line exactly, so M1 keeps it alone on line 1. — anchors: M3, M4, M7
12. `MODE=challenge` already borrows the Review stance's bar for a rejection by name. M2 reuses it the same way. `[verified: claude/.claude/agents/plan-architect.md:146-148, 194-195]` — anchors: M2
13. A contradiction of an `[engineer-verified]` quote pauses and asks. It is never revised silently. `[verified: plan-it/SKILL.md:126]` — anchors: M2
14. `plan-review`'s fix-or-ask rule allows an enforcement-invariant finding only two ends: a fix, or an engineer answer. `[verified: plan-review/SKILL.md:283]` — anchors: M1
15. A re-review's reviewers get the prior round's applied changes inline, and they diff every `[engineer-verified]` row. `[verified: plan-review/ROUTING.md:55, 80]` Today the session that made the edits supplies the applied changes, so M3 names a new source for them. — anchors: M1, M3
16. During `/code-review` the plan is usually committed, so a plan edit re-arms the plan-review gate. The architect therefore runs after `code-writer` in a round. Today's inline plan-file fix re-arms the gate the same way (row 31). `[verified: row 9; plan-architect-writes-its-own-plan-sections.md:23]` — anchors: M4
17. `review-orchestrator` item 8 sends a plan-revision return to `HALT:`, and a stop-and-ask about one finding ends only that finding's handling. An entry's fields carry no suggested fix or findings-file path. Item 7 writes no marker while a `HALT:` entry stands. After any `HALT:` entry the dispatcher runs the rest of the loop inline, but that step names no action for the halted row itself, so M4 gives it one. `[verified: review-orchestrator.md:29-47; subagent-delegation/SKILL.md:215]` — anchors: M4
18. `code-review/SKILL.md` is 546 lines against its 550-line cap, so M4 adds no line. `[verified: line count; claude/.claude/hooks/tests/test_check_skill_length.py:337-340]` — anchors: M4
19. Three pins bear on this change:
    - `approve_with_changes_literal` pins the prose-verdict sentence M3 rewrites. `[verified: claude-skills/skills/tests/test_review_dispatch_contracts.py:294-297]`
    - The landed-edits prefix M2 keeps is pinned. `[verified: claude-skills/skills/tests/test_plan_pipeline_skills.py:157-159, 313-321]`
    - The contradiction-route and fix-plan-pilot regions are pinned whole, and M4 leaves them unedited. `[verified: claude-skills/skills/tests/test_code_review_disposition_rules.py:114-115, 293-355]`
    — anchors: M4, M7
20. This plan re-runs Cells V and RR by hand, since an edit to the Plan prose paragraph re-runs that decision's measurement cells. By cell:
    - Cell V reads `plan-review/SKILL.md`. The record says to run it on the V control's plan, which names no prior round's finding.
    - Cell RR hands the reviewer the re-review handoff that M3 rewrites at `ROUTING.md:55`.
    - Cells P, D and R hand `comment-discipline-reviewer` a plan or a diff and read neither file, so they are not re-run.
    `[verified: docs/design-decisions/plan-prose-reviewed-inside-plan-review.md:30-43; .claude/plans/plan-prose-pass.md:450-451]` — anchors: M7
21. A stowed agent resolves to the main checkout's file until merge, so behavior cells run the edited body through a `general-purpose` dispatch. `[verified: docs/design-decisions/plan-prose-reviewed-inside-plan-review.md:28]` — anchors: M7
22. Step 5 cannot dispatch on a harness plan-mode path. `plan-shape.py`'s path rule refuses it, and the run ends there. `[verified: plan-it/SKILL.md:63]` — anchors: M3
23. A hook allowing the session's own region writes while denying a finding-driven one would need byte-offset matching over `old_string` in bash. The edit-grant decision rejected that shape. `[verified: docs/design-decisions/plan-architect-writes-its-own-plan-sections.md:15]` — anchors: row 3
24. `claude/.claude/CLAUDE.md` § "Plan Review" says "address them first" with no actor. `[verified: the loaded global CLAUDE.md]` — anchors: root
25. Step 4's answers come in four kinds: a kept item, a declined item, `Split now` and `Proceed anyway`. Only `Split now` has row text today. `[verified: plan-review/SKILL.md:96]` — anchors: M5
26. The design-decision doc stays in this plan's scope. `[engineer-verified: "Design-decision doc"]` — anchors: root
27. The `CHANGELOG.md` bullet stays in this plan's scope. `[engineer-verified: "CHANGELOG bullet"]` — anchors: root
28. The blocking-finding escalation stays in this plan's scope. `[engineer-verified: "Blocking-finding escalation"]` — anchors: root
29. The plan-mode path stop stays in this plan's scope. `[engineer-verified: "Plan-mode path stop"]` — anchors: root
30. A plan-file write passes `require-plan-review.sh` before its active-marker check, and a live active marker lets every other write but `ExitPlanMode` through. A dispatch after `marker.sh deactivate plan-review` therefore needs no active marker, and a stop before that call would leave the marker live. `[verified: require-plan-review.sh:201-206, 258-261]` — anchors: M3
31. `subagent-delegation`'s not-code carve-out keeps a plan-file fix inline, and `code-review`'s Fix route names that rule's carve-outs, so the carve-out must change with M4's clause. The file sits at its 218-line cap, so M4 edits its lines in place. `[verified: subagent-delegation/SKILL.md:170, 215; code-review/SKILL.md:359; claude/.claude/hooks/check-skill-length.sh:140-141]` — anchors: M4
32. The `/code-review` route stays in this plan's scope. `[engineer-verified: "Keep in this plan"]` — anchors: root
33. The session adds an approved Critical file's path itself. `[engineer-verified: "Session adds path (Recommended)"]` — anchors: root

## Critical files

One `code-writer` dispatch implements every file below. The routing wording recurs across skills, agents, tests and docs, so a split would restate it in each prompt. Its verification is Verification steps 1-4. The session then runs steps 5-8 and adds the decision record's Measurement note inline. That last edit is a decided change to a known target, which fails the decision-made test's condition (2) in `subagent-delegation/SKILL.md` § "Implementation work → `code-writer`".

- `claude-skills/skills/plan-it/SKILL.md` — modify: M1 and M5 paragraphs in Step 5, the item 3 sentence, Step 6 (M6).
- `claude-skills/skills/plan-review/SKILL.md` — modify: Step 4 row claims, the two Plan prose bullets, the Record-completion paragraph and marker sentence (M3).
- `claude-skills/skills/plan-review/ROUTING.md` — modify line 55 (M3).
- `claude-skills/skills/code-review/SKILL.md` — modify line 359 in place (M4).
- `claude-skills/skills/subagent-delegation/SKILL.md` — modify lines 170 and 215 in place (M4).
- `claude/.claude/agents/plan-architect.md` — modify: description, one bullet, one new block, one sentence (M2).
- `claude/.claude/agents/review-orchestrator.md` — modify item 6 (M4).
- `claude-skills/skills/tests/test_plan_pipeline_skills.py` — modify (M7).
- `claude-skills/skills/tests/test_review_dispatch_contracts.py` — modify (M7).
- `docs/design-decisions/plan-architect-decides-review-findings.md` — create (M7).
- `CHANGELOG.md` — modify (M7).

Reuse rather than reimplement:
- `plan-it` Step 5's revision re-dispatch, with its `plan-shape.py check` and Context hash.
- The Review stance's bar, as `MODE=challenge` cites it.
- `review-orchestrator`'s `HALT:` channel and the dispatcher's step-2 staging.
- `_PINNED_PLAN_IT_STEP5_SCRIPT_CLAUSES`, `_PLAN_IT_STEP5_CONTEXT_CHECK_AND_GRAMMAR_LITERALS`, `_assert_pinned_clause_right_bounded` and `_heading_section_text` in the test helpers.

Projected diff: about 220 changed lines.

## Verification

1. From the worktree root, `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py` passes. It selects the skills, agents and docs domains, including `test_skill_citation_grammar.py`, which resolves the new `` `plan-it/SKILL.md` § "Step 5 — Architecture design" `` and `` `code-review/SKILL.md` § "Finding disposition" `` citations.
2. `scripts/venv-run.sh ruff check claude/.claude/ claude-skills/ plugins/ evals/` is clean.
3. `git grep -n -F -e "Address any findings" -e "Apply each one you accept" -e "the plan author revises" -e "Record each answer on its own ledger row quoting it" -e "What's been applied stays inline regardless" -e "The session then adds it to the list itself" -- ':!.claude/plans' ':!CHANGELOG.md'` prints nothing.
4. `wc -l claude-skills/skills/code-review/SKILL.md claude-skills/skills/subagent-delegation/SKILL.md claude-skills/skills/plan-it/SKILL.md` prints 546 and 218, the merge-base counts, and at most 200, the cap, for `plan-it/SKILL.md`.
5. Steps 6-8 are behavior cells, under four rules:
   - Each is a foreground dispatch on fixtures hand-authored in a scratchpad and never committed.
   - Its prompt names the file it runs on and tells it to describe each tool call that file prescribes instead of making it, except an `Edit` the cell allows.
   - A run that calls Bash, Skill or Write is invalid and is re-run.
   - After the cells, run `~/.claude/scripts/marker.sh deactivate plan-review` once.
6. Cells V and RR from `docs/design-decisions/plan-prose-reviewed-inside-plan-review.md` § "Measurement note", K=5 each. Their fixture is the V control's shape: a four-heading plan with three plan-prose sites and no sentence naming a prior round's finding, plus a hand-written `comment-discipline-reviewer` findings file naming those sites.
   - Cell V: a `general-purpose` dispatch at `model: sonnet` reads this worktree's edited `plan-review/SKILL.md` whole, with one finding in the file relabeled `BLOCKER`. Its prompt says that reviewer was the only spawn and returned nothing else. It asks the run to write Output format, then carry out each step the skill requires after the verdict. Bar, in all 5 runs:
     - The findings sit in a Plan prose section.
     - The run ends **Approve with changes**. A **Request changes** run fails the cell, since the fixture gives the Self-referential findings tripwire nothing to catch.
     - The run describes no edit to the plan.
     - It names a `plan-architect` revision re-dispatch after the deactivate call and before the completion-marker write.
   - Cell RR: dispatch `comment-discipline-reviewer` itself, whose body this plan leaves unchanged, with `plan_path:` set to the fixture after one finding is applied and another's site is left as it was. The prompt carries the findings file's path, finding 1 as accepted and finding 2 as declined with its reason, as the edited `ROUTING.md:55` prescribes, and no account of the edit itself. Bar: the declined site returns as a new finding in at most 1 of 5 runs.
7. Cell A, the architect's decision, K=5. A `general-purpose` dispatch at `model: opus` carries this worktree's edited `claude/.claude/agents/plan-architect.md` body as its instructions and is told it holds only `Read`, `Grep`, `Glob` and `Edit`. Prompt line 1 is `MODE=plan-sections`, and line 2 is the absolute path of a scratch fixture at `<scratch>/.claude/plans/fixture.md`, with an untouched copy kept outside that directory. The fixture is a plan in the four-heading shape whose ledger holds one `[engineer-verified: "<quote>"]` row, whose `## Out of scope` holds one entry, and whose Verification runs a test file its Approach deletes. The prompt carries six numbered findings, each listed here with its expected line:
   - (1) Critical files omits a second test file that Verification runs: `1. accept`.
   - (2) "B11 — Rollback strategy" asks for a rollback plan on a change a plain revert fully undoes: `2. decline`.
   - (3) A fix that rewrites the `[engineer-verified]` row's quoted claim: `3. open`.
   - (4) A request to bring the Out of scope entry into scope: `4. decline`.
   - (5) Marked `blocking`: Verification runs the test file the Approach deletes: `5. accept`.
   - (6) Marked `blocking`: a second confirmation step that no rule, row or `Ask:` line calls for: `6. open`.

   Bar:
   - Each finding's line matches in at least 4 of 5 runs.
   - In every run, a `diff` of the fixture against its untouched copy shows only finding 1's Critical-files entry, finding 5's Verification fix, a `Projected diff:` update and rows appended to the ledger.
   - In every run, the fixture's Context digest from `sed -n '1,/^## Approach$/p' "<fixture>" | sha256sum` is unchanged.
   - In every run, `python3 claude/.claude/scripts/plan-shape.py check '<fixture>'` prints `CHECK: pass`.
8. Cell C, the `/code-review` route, K=5. A `general-purpose` dispatch at `model: sonnet` reads this worktree's edited `code-review/SKILL.md` and `subagent-delegation/SKILL.md` whole. The fixture is one round's three logged ADDRESS rows, on a branch whose committed plan sits under `.claude/plans/`:
   - (a) The contradiction route's *Apply this round's fix*, editing one sentence under the plan's `## Approach` and one script.
   - (b) An ordinary row on a second script.
   - (c) A row whose fix edits the plan's Context paragraph.

   The prompt asks for the disposition table, the `Fix route:` line and the dispatches the run would make, in order. Bar: at least 4 of 5 runs meet every condition below in the same run:
   - The `Fix route:` line names `plan-architect — plan revision` for (a)'s plan edit.
   - `code-writer` gets (a)'s script edit and (b), and is dispatched before `plan-architect`.
   - (c) takes the inline route under the not-code carve-out.
   - The run edits no file.
9. Record each cell's K, bar and outcome in the new decision record's Measurement note.

`/code-review` then runs `/skill-review` on the four skill diffs and `/agent-review` on the two agent diffs, per `.claude/rules/review-pipeline-dispatch.md`.

## Out of scope

- Round-count and plan-growth triggers (`#1567`), and one adversarial consult inside `/plan-review` (`#1212`). Neither changes who edits a plan (row 7).
- `code-review`'s handling of non-plan files, and the text of its heavier-mechanism, contradiction-route, fix-plan-pilot and disposition-challenge rules. M4's clause reaches their ADDRESS rows without editing them (row 19).
- Logging a `plan-architect` decline in `code-review`'s ledger as a SETTLED decision, so a later repeat takes the settled-site stop.
  - The ADDRESS row stays as logged, as a Rejected heavier-mechanism consult leaves it (`code-review/SKILL.md:380`).
  - The round-cap consult bounds repeats.
  - Changing ledger semantics lies outside the Ask.
- A named `/plan-review` run between `/code-review` rounds after a plan edit. The plan-review gate's deny names it when a later non-plan write needs it, and the next `/code-review` round reviews the staged plan edit. Today's inline plan-file fix re-arms the gate the same way (rows 16, 31).
- An engineer answer for each non-blocking decline before `/plan-review` writes its completion marker. Row 1 gives that decision to `plan-architect`, and M1 relays every decline to the engineer.
- Behavior cells for these sites, each of which keeps a residual:
  - M5's row append has no runtime check that its quote is byte-exact or that no existing row changed, the same as today's Step 4 row. M5 only narrows that row to a template.
  - M1's relay reuses Step 5's existing open-decision relay (`plan-it/SKILL.md:77`), and this plan measures neither.
  - M6's loop points at the route Cell V measures.
  - `review-orchestrator` item 6 and the dispatcher's `HALT:` step are pinned by text only. No cell plays the routed flow, whose routing key ships off (`review-orchestrator-routing-gate.md:73`).
  - Cell C samples only the contradiction route among the rules M4's clause reaches.
- A hook, or a rule in `code-writer.md`, enforcing the single-writer rule (row 3).
- `claude/.claude/CLAUDE.md` § "Plan Review"'s "address them first" (row 24). `/plan-review` now routes its own findings, so the line stays true, and that file loads into every session's context.
- Reviewer prompts that ask for hardening layers. M2's decline standard handles such findings at the architect (row 7).
- `plan-review` Step 3's "return it to the author" and Step 4's "goes back to the author". M3's routing paragraph covers Step 3's findings, and the `Ask:` line sits above `## Approach`, which is the session's region.
