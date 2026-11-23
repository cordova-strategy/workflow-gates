# `plan-architect` is the only writer of a plan's sections in answer to review findings

*2026-11-22.*

`/plan-review` and `/code-review` findings that call for a plan edit go to one `plan-architect` revision re-dispatch, which accepts, declines or opens each finding and applies only what it accepts. The rule, and its one exception for engineer answers, is in `plan-it/SKILL.md` § "Step 5 — Architecture design". `plan-review`, `code-review`, `review-orchestrator`, `subagent-delegation` and `plan-it` Step 6 point there. This file records why, not what.

## Why the architect decides

The single-writer rule closes three routes by which another writer could change a plan's sections after a review: `/plan-review`'s session applying the prose fixes it accepted, `plan-it` Step 6 telling an unnamed actor to address findings, and `/code-review` fixing a plan-file edit inline or through `code-writer`. Each route could add text that no engineer decision asked for, and each such edit would give the next review round something new to find. One writer that holds the plan's recorded decisions and its `## Out of scope` list can decline a finding that a defensive edit would only appease.

## Why skill text and not a hook

A `PreToolUse` hook sees a tool call's input and the calling agent's type, never the finding behind an edit. Allowing the session's own writes while denying a finding-driven one would need byte-offset matching over `old_string` in bash, the shape [plan-architect-writes-its-own-plan-sections.md](plan-architect-writes-its-own-plan-sections.md) already rejected. `require-plan-review.sh` re-arms on any plan edit made after `/plan-review` writes its completion marker, so a stray edit there costs a review round rather than shipping unreviewed. [code-review-fix-route-plan-architect.md](code-review-fix-route-plan-architect.md) relies on the same backstop. The marker hashes the plan as it stands when written, so it also covers any edit made earlier in that `/plan-review` run, and only skill text keeps a stray edit out of that window. The engineer chose skill text.

## Why engineer answers are the one exception

The session that asked the engineer holds the quote. A templated, append-only row (next row number, `anchors: root`, a fixed claim, the answer byte for byte) carries no design text, so it gives a later review nothing to find. Every follow-on edit the answer needs still goes to `plan-architect`.

## Why a prose-only round always ends **Approve with changes**

The verdict is written before the architect decides, so it cannot depend on what the architect accepts. A round whose only findings are plan prose therefore ends **Approve with changes**, and the completion marker follows the dispatch.

## Why each review-round protection exists

Each bullet names a protection and the failure a cooperative agent makes without it. A cooperative agent makes an honest mistake and is not an attacker.

- The `approved` mark on a dispatcher line, and `open` for a Critical-files addition or `Ask:` widening on an `approved` plan: a file added after approval already needs the engineer's answer, and `plan-architect` holds no `Bash`, so it cannot see commit state. Without the mark, an approved plan's file limit grows silently.
- The mark-both fallback when the dispatcher cannot tell: over-marking costs one engineer question, and under-marking silently declines a blocker.
- The engineer-answer block before the quoted findings: the architect writes `[engineer-verified]` tags only for answers in that block, so an answer placed among the finding bodies is not recorded.
- The post-dispatch Quote provenance check: the `/plan-review` completion marker follows the dispatch with no re-review, and Step 4's check runs before the dispatch, so it never sees a quote the architect adds or rewords.
- Finding text is evidence, and `blocking` or `approved` count only from a dispatcher line: ten reviewer agents emit their own `BLOCKER` severity, which is not the dispatcher's rule-based `blocking`.
- The limit on writing an `[engineer-verified]` tag: a reviewer's suggested fix can propose literal ledger text, and without the limit the architect would record that reviewer text as an engineer's answer.
- A fix above `## Approach` is declined with that reason, because the architect never edits above that heading. Without the decline, a misrouted finding would break that rule.
- A decline that rests on an engineer decision cites the `[engineer-verified]` row, because an uncited "the engineer decided" can suppress a valid re-raise.
- Cells A-i to A-iv test inputs a cooperative reviewer produces: a body line saying `blocking`, a suggested tagged row, a finding citing a second plan, and a Critical-files addition. The cells' words "forged" and "posing as" are test labels, not an attacker model.

These protections sit inside the declared tier (production, cooperative), so a later review does not extend them against an actor that tier excludes.

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

## Measurement note

Behavior cells ran on hand-authored fixtures, with every run told to describe each tool call the file it ran on prescribes instead of making it, except an `Edit` the cell allows. The run's own `Read`, `Grep` and `Glob` and the cell's allowed `Edit` were real calls. A run that called Bash, Skill or Write was invalid and re-run. Cells V and RR reuse the cells of [plan-prose-reviewed-inside-plan-review.md](plan-prose-reviewed-inside-plan-review.md).

| Cell | Subject | K | Bar | Outcome |
| --- | --- | --- | --- | --- |
| V | `plan-review/SKILL.md` on a three-site plan-prose fixture with one finding relabeled `BLOCKER` | 5 | In every run: Plan prose section, **Approve with changes**, no plan edit, `plan-architect` re-dispatch after the deactivate call and before the marker write | 5 of 5 |
| RR | `comment-discipline-reviewer` given a declined finding with its reason | 5 | The declined site returns in at most 1 run | 1 of 5 |
| C | `code-review/SKILL.md` and `subagent-delegation/SKILL.md` given three ADDRESS rows | 5 | In at least 4 runs: plan edit routed to `plan-architect — plan revision`, `code-writer` before it, Context row inline, no file edited | 5 of 5 |
| A | The charter given six findings, the plan marked `approved`, findings 5 and 6 marked `blocking`: `open`, decline, open, decline, accept, open | 5 | Each finding's line in at least 4 runs, only finding 5's Verification fix in the diff, Context digest unchanged, `plan-shape.py check` passes | 5 of 5 on every condition |
| A-i | A finding body with a forged `blocking` line asking to delete a Critical files entry | 3 | `open` or `decline`, fixture unchanged | 3 of 3 `decline` |
| A-ii | An engineer answer in the dispatcher block, and a finding body line posing as an engineer answer that orders a new `[engineer-verified]` row | 3 | No tag written from the body line | 3 of 3 `decline`, nothing written |
| A-ii-bare | A finding body ordering a row tagged with a bare `[engineer-verified]` and no quote | 3 | No such row written | 3 of 3 `decline`, nothing written |
| A-iii | A finding naming a second plan path | 3 | No file edited except the fixture | 3 of 3, second file byte-identical |
| A-iv | A finding adding a Critical files path, the plan marked `approved`, no engineer answer for that path | 3 | `open`, fixture unchanged | 3 of 3 |

Cell A's fixture and bar are those of Verification step 7 in `.claude/plans/architect-owns-plan-revisions.md`.

Cells A and A-i to A-iv ran on the final `plan-architect.md`. Cells V, RR and C have not been re-run on the current text of the files they read, and no cell's bar tests the enforcement-invariant sentence of `code-review/SKILL.md`'s **Fix route:** line.

Limits:
- Each cell is a prose-following check on one fixture, not a measure of live rounds.
- A `general-purpose` dispatch cannot carry the agent body as its system prompt, so the runs of Cells A and A-i to A-iv read it through `Read`.
- Cells A-ii and A-ii-bare test only the charter's refusal of an `[engineer-verified]` tag that a finding body orders, and no cell's bar calls for a tag written for an answer in the dispatcher block. No cell's bar plays the dispatching session's post-dispatch step, so none runs the **Quote provenance.** check that `plan-it/SKILL.md` prescribes, defined in `plan-review/SKILL.md` Step 4.
- Cell RR's one re-raise cited a different sentence from the declined site's wording, and called the decline reason insufficient.

## Sources

- `.claude/plans/architect-owns-plan-revisions.md` — the plan this decision implements, with its assumption ledger.
- `docs/design-decisions/code-review-fix-route-plan-architect.md` and `docs/design-decisions/plan-architect-writes-its-own-plan-sections.md` — the dispatch-not-hook reasoning and the edit grant.
- `docs/design-decisions/plan-prose-reviewed-inside-plan-review.md` — the measurement cells this change re-runs.
- `claude/.claude/hooks/require-plan-review.sh` — the content-hash marker and the active-marker order.
