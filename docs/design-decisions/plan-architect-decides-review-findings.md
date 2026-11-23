# `plan-architect` is the only writer of a plan's sections in answer to review findings

*2026-11-22.*

`/plan-review` and `/code-review` findings that call for a plan edit go to one `plan-architect` revision re-dispatch, which accepts, declines or opens each finding and applies only what it accepts. The rule, and its one exception for engineer answers, is in `plan-it/SKILL.md` § "Step 5 — Architecture design". `plan-review`, `code-review`, `review-orchestrator`, `subagent-delegation` and `plan-it` Step 6 point there. This file records why, not what.

## Why the architect decides

Before this change, three routes let another writer change a plan's sections after a review: `/plan-review`'s session applied the prose fixes it accepted, `plan-it` Step 6 told an unnamed actor to address findings, and `/code-review` fixed a plan-file edit inline or through `code-writer`. Each added text that no engineer decision asked for, and each such edit gave the next review round something new to find. One writer that holds the plan's recorded decisions and its `## Out of scope` list can decline a finding that a defensive edit would only appease.

## Why skill text and not a hook

A `PreToolUse` hook sees a tool call's input and the calling agent's type, never the finding behind an edit. Allowing the session's own writes while denying a finding-driven one would need byte-offset matching over `old_string` in bash, the shape [plan-architect-writes-its-own-plan-sections.md](plan-architect-writes-its-own-plan-sections.md) already rejected. `require-plan-review.sh` re-arms on any plan edit made after `/plan-review` writes its completion marker, so a stray edit there costs a review round rather than shipping unreviewed, the same backstop [code-review-fix-route-plan-architect.md](code-review-fix-route-plan-architect.md) relies on. The marker hashes the plan as it stands when written, so it also covers any edit made earlier in that `/plan-review` run, and only skill text keeps a stray edit out of that window. The engineer chose skill text.

## Why engineer answers are the one exception

The session that asked the engineer holds the quote. A templated, append-only row (next row number, `anchors: root`, a fixed claim, the answer byte for byte) carries no design text, so it gives a later review nothing to find. Every follow-on edit the answer needs still goes to `plan-architect`.

## Why a prose-only round always ends **Approve with changes**

The verdict is written before the architect decides, so it cannot depend on what the architect accepts. A round whose only findings are plan prose therefore ends **Approve with changes**, and the completion marker follows the dispatch.

## Ordering

- `/plan-review` dispatches after `marker.sh deactivate plan-review`. A Step 5 stop, an errored dispatch or the plan-mode path stop then cannot leave the active marker live, and no gate needs that marker for the dispatch.
- In a `/code-review` round `code-writer` runs before `plan-architect`, because a plan edit re-arms the plan-review gate and would deny `code-writer`'s non-plan writes.

## Cost

Each review round with findings adds one Opus dispatch, plus at most one for findings the return left without a line, besides Step 5's own re-dispatches.

## Accepted residuals

- The `code-review` ledger keeps a declined ADDRESS row as logged, as a rejected heavier-mechanism consult leaves it, except that a finding the enforcement-invariant rule covers ends in that rule's blocking stop-and-ask with its keep logged.
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

Cell A's fixture and bar replace those of Verification step 7 in `.claude/plans/architect-owns-plan-revisions.md`, which does not mark the plan `approved` and expects `1. accept`.

Cells A and A-i to A-iv ran on the final `plan-architect.md`. Cells V, RR and C ran on earlier text of the files they read, and `code-review/SKILL.md`'s **Fix route:** line has since gained a sentence that their bars do not test.

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
