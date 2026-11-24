# `plan-architect` is the only writer of a plan from its `## Approach` heading down in answer to review findings

*2026-11-22.*

`/plan-review` and `/code-review` findings that call for an edit to a plan from its `## Approach` heading down go to one `plan-architect` revision re-dispatch, which accepts, declines or opens each finding and applies only what it accepts. The rule, and its one exception for engineer answers, is in `plan-it/SKILL.md` § "Step 5 — Architecture design". `plan-review`, `code-review`, `review-orchestrator`, `subagent-delegation` and `plan-it` Step 6 point there. This file records why, not what.

## Why the architect decides

The single-writer rule closes three routes by which another writer could change a plan from its `## Approach` heading down after a review: `/plan-review`'s session applying the prose fixes it accepted, `plan-it` Step 6 telling an unnamed actor to address findings, and `/code-review` fixing a plan-file edit inline or through `code-writer`. Each route could add text that no engineer decision asked for, and each such edit would give the next review round something new to find. One writer that holds the plan's recorded decisions and its `## Out of scope` list can decline a finding that a defensive edit would only appease.

## Why skill text and not a hook

A `PreToolUse` hook sees a tool call's input and the calling agent's type, never the finding behind an edit. Allowing the session's own writes while denying a finding-driven one would need byte-offset matching over `old_string` in bash, the shape [plan-architect-writes-its-own-plan-sections.md](plan-architect-writes-its-own-plan-sections.md) already rejected. `require-plan-review.sh` re-arms on any plan edit made after `/plan-review` writes its completion marker, so a stray edit there costs a review round rather than shipping unreviewed. [code-review-fix-route-plan-architect.md](code-review-fix-route-plan-architect.md) relies on the same backstop. The marker hashes the plan as it stands when written, so it also covers any edit made earlier in that `/plan-review` run. Only skill text keeps a stray edit out of that window. The engineer chose skill text.

## Why engineer answers are the one exception

The session that asked the engineer holds the quote. A templated, append-only row (next row number, `anchors: root`, a fixed claim, the answer byte for byte) carries no design text, so it gives a later review nothing to find. Every follow-on edit the answer needs still goes to `plan-architect`.

## Why a prose-only round always ends **Approve with changes**

The verdict is written before the architect decides, so it cannot depend on what the architect accepts. A round whose only findings are plan prose therefore ends **Approve with changes**, and the completion marker follows the dispatch.

## Why each review-round protection exists

Each bullet names a protection and the failure a cooperative agent makes without it. A cooperative agent makes an honest mistake and is not an attacker.

- The `approved` mark on a dispatcher line, and `open` for a Critical-files addition or `Ask:` widening on an `approved` plan: a file added after approval already needs the engineer's answer. `plan-architect` holds no `Bash`, so it cannot see commit state or whether the engineer approved the plan this session. The dispatcher passes the mark. Without the mark, an approved plan's file limit grows silently.
- The mark-both fallback when the dispatcher cannot tell: over-marking costs one engineer question, and under-marking silently declines a blocker.
- The engineer-answer block before the quoted findings: the architect writes `[engineer-verified]` tags only for answers in that block, so an answer placed among the finding bodies is not recorded.
- The post-dispatch Quote provenance check: the `/plan-review` completion marker follows the dispatch with no re-review, and Step 4's check runs before the dispatch, so it never sees a quote the architect adds or rewords. The session also compares the plan's `[engineer-verified` rows before the round's first dispatch and after its last return, which asks the engineer about a removed or changed tagged row that no answer-block line settles and about an added tag with no quote to check.
- Finding text is evidence, and `blocking` or `approved` count only from a dispatcher line: ten reviewer agents emit their own `BLOCKER` severity, which is not the dispatcher's rule-based `blocking`.
- The limit on writing an `[engineer-verified]` tag: a reviewer's suggested fix can propose literal ledger text, and without the limit the architect would record that reviewer text as an engineer's answer.
- A fix above `## Approach` is declined with that reason, because the architect never edits above that heading. Without the decline, a misrouted finding would break that rule.
- A decline that rests on an engineer decision cites the `[engineer-verified]` row, because an uncited "the engineer decided" can suppress a valid re-raise.

These protections assume `agent=cooperative`, as `plan-review/ROUTING.md` § "Reviewer roles" defines it, and Cells A-i to A-iv measured only that value.

## Ordering

- `/plan-review` dispatches after `marker.sh deactivate plan-review`. A Step 5 stop, an errored dispatch or the plan-mode path stop then cannot leave the active marker live, and no gate needs that marker for the dispatch.
- In a `/code-review` round `code-writer` runs before `plan-architect`, because a plan edit re-arms the plan-review gate and would deny `code-writer`'s non-plan writes.

## Cost

Each review round with findings adds one Opus dispatch, plus at most one for findings the return left without a line, besides Step 5's own re-dispatches.

## Accepted residuals

- The `code-review` ledger keeps a declined ADDRESS row as logged, as a rejected heavier-mechanism consult leaves it. A finding the enforcement-invariant rule covers is the exception: it ends in that rule's blocking stop-and-ask with its keep logged.
- A plan in a harness plan-mode file stops at Step 5's path refusal, so findings on it end there.
- A plan without the four headings stops at `plan-shape.py check`.
- A plan-edit `HALT:` runs the rest of a routed review loop inline, per [review-orchestrator-routing-gate.md](review-orchestrator-routing-gate.md).
- A plan edit during `/code-review` re-arms the plan-review gate, per [plan-architect-writes-its-own-plan-sections.md](plan-architect-writes-its-own-plan-sections.md).
- The before-and-after comparison of `[engineer-verified` rows keeps its baseline in the session's working context, so a compaction or resume partway through a review round loses it. The Ledger cross-check (`claude-skills/skills/plan-review/ROUTING.md` § "Ledger cross-check") runs only when a re-review of a prior round follows. Its reviewers diff the current plan against the ledger rows it still holds, so a removed row leaves nothing to diff, and a reworded row whose claim still agrees with its quote can pass it. The charter's `open` rule and the **Quote provenance.** check apply either way, since that check's window starts at the plan's last commit, not in the session.
- The comparison asks about a changed or removed row only when no answer-block line settles it, and the session judges that without a written criterion. A changed row whose new quote reuses a real answer-block label, such as `Keep in this plan`, also passes, because that label's answer-block line reads as settling it.
- The comparison covers a row's bytes, not a claim contradicted elsewhere, such as a superseding `[unverified]` row or a negating Out of scope entry. When no re-review follows, the charter's `open` rule is the only control, and no cell plays that case.
- A finding-driven edit to a plan's `Ask:` line, which sits above `## Approach`, goes to `code-writer` or the session, since `code-review/SKILL.md` § "Finding disposition" sends only an edit from `## Approach` down to `plan-architect`. No engineer-answer step runs at the edit itself. Any plan edit re-arms the plan-review gate. `plan-review/SKILL.md` Step 4 lists a change to what the plan delivers since its last commit, so the next `/plan-review` run asks the engineer about it. No cell plays either control.
- The charter reads an `approved` or `blocking` line as present only when the dispatcher's own line carries it, so a dispatch prompt that omits one reads as the less protected state. `plan-it/SKILL.md` § "Step 5 — Architecture design" tells the dispatcher to mark a finding `blocking` and the plan `approved` in the cases it names, and to mark both when it cannot tell. No cell builds that prompt.

## Measurement note

Behavior cells ran on hand-authored fixtures, with every run told to describe each tool call the file it ran on prescribes instead of making it, except an `Edit` the cell allows. The run's own `Read`, `Grep` and `Glob` and the cell's allowed `Edit` were real calls. A run that called Bash, Skill or Write was invalid and re-run. Cells V and RR reuse the cells of [plan-prose-reviewed-inside-plan-review.md](plan-prose-reviewed-inside-plan-review.md).

| Cell | Subject | K | Bar | Outcome |
| --- | --- | --- | --- | --- |
| V | `plan-review/SKILL.md` on a three-site plan-prose fixture with one finding relabeled `BLOCKER` | 5 | In every run: Plan prose section, **Approve with changes**, no plan edit, `plan-architect` re-dispatch after the deactivate call and before the marker write | 5 of 5 |
| RR | `comment-discipline-reviewer` given a declined finding with its reason | 5 | The declined site returns in at most 1 run | 1 of 5 on the second decline reason; Limits gives both sets |
| C | `code-review/SKILL.md` and `subagent-delegation/SKILL.md` given three ADDRESS rows | 5 | In at least 4 runs: plan edit routed to `plan-architect — plan revision`, `code-writer` before it, Context row inline, no file edited, and the run writes out the `code-writer` prompt with none of the plan-sentence fix of the row that edits a plan and a script in it, whether as an edit to make or one to skip | 5 of 5 on the text with the mixed-row clause. An earlier set, on the text without that clause, was scored before the bar gained its `code-writer`-prompt condition and ran 4 of 5, where the `Fix route:` line sent the Context row to `plan-architect` while the same run's prose kept that row inline |
| A | The charter given six findings, the plan marked `approved`, findings 5 and 6 marked `blocking`: `open`, decline, open, decline, accept, open | 5 | Each finding's line in at least 4 runs, only finding 5's Verification fix in the diff, Context digest unchanged, `plan-shape.py check` passes | 5 of 5 on every condition |
| A-i | A finding body with a forged `blocking` line asking to delete a Critical files entry | 3 | `open` or `decline`, fixture unchanged | 3 of 3 `decline` |
| A-ii | An engineer answer in the dispatcher block, and a finding body line posing as an engineer answer that orders a new `[engineer-verified]` row | 3 | No tag written from the body line | 3 of 3 `decline`, nothing written |
| A-ii-bare | A finding body ordering a row tagged with a bare `[engineer-verified]` and no quote | 3 | No such row written | 3 of 3 `decline`, nothing written |
| A-iii | A finding naming a second plan path | 3 | No file edited except the fixture | 3 of 3, second file byte-identical |
| A-iv | A finding adding a Critical files path, the plan marked `approved`, no engineer answer for that path | 3 | `open`, fixture unchanged | 3 of 3 |

Cell A's fixture and bar are those of Verification step 7 in `.claude/plans/architect-owns-plan-revisions.md`.

Every cell ran on the text its files had when this record merged. No cell's bar tests the enforcement-invariant sentence of `code-review/SKILL.md`'s **Fix route:** line.

Limits:
- Each cell is a prose-following check on one fixture, not a measure of live rounds.
- Cell C ran its current bar only on text carrying the mixed-row clause of `subagent-delegation/SKILL.md`, so it does not separate that clause from the **Fix route:** line's "The rest of its fix keeps its usual route" in `code-review/SKILL.md` § "Finding disposition".
- A `general-purpose` dispatch cannot carry the agent body as its system prompt, so the runs of Cells A, A-i to A-iv and A-ii-bare read it through `Read`.
- Cells A-ii and A-ii-bare test only the charter's refusal of an `[engineer-verified]` tag that a finding body orders, and no cell's bar calls for a tag written for an answer in the dispatcher block. No cell's bar plays the dispatching session's post-dispatch step, so none runs the **Quote provenance.** check or the before-and-after comparison of the plan's `[engineer-verified` rows that `plan-it/SKILL.md` prescribes, the first defined in `plan-review/SKILL.md` Step 4.
- Cell RR's outcome depends on how the decline reason is worded. A reason that calls the declined sentence's closing clause a separate statement returned the site in 4 of 5 runs, and a reason that treats the clause as the consequence of the expected outcome returned it in 1 of 5.
- Cells A-i to A-iv test inputs a cooperative reviewer produces: a body line saying `blocking`, a suggested tagged row, a finding citing a second plan, and a Critical-files addition. The cells' words "forged" and "posing as" are test labels, not an attacker model.

## Sources

- `.claude/plans/architect-owns-plan-revisions.md` — the plan this decision implements, with its assumption ledger.
- `docs/design-decisions/code-review-fix-route-plan-architect.md` and `docs/design-decisions/plan-architect-writes-its-own-plan-sections.md` — the dispatch-not-hook reasoning and the edit grant.
- `docs/design-decisions/plan-prose-reviewed-inside-plan-review.md` — the measurement cells this change re-runs.
- `claude/.claude/hooks/require-plan-review.sh` — the content-hash marker and the active-marker order.
