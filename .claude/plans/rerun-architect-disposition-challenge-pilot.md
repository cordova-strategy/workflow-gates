# Re-run the architect disposition-challenge pilot with a clean arm

## Context

Goal: get a second window of the `architect_disposition_challenge_pilot` that can be evaluated, because the first window cannot be.

Ask: "yes do that, and I'm not surprised. I was focusing on the review orchestrator pilot first. but just so you know i'm likely making a decision on that pilot (default on or off) before I resue the disposition pilot, ok?" The analysis exclusions came earlier: "We should only include runs where review-orchestrator pilot wasn't running at the same time and we should exclude runs where Fable was invoked and where Opus or Fable were running the main session." On whether the plan changes a repository file, the engineer selected no option label and typed: "I think there should be a design-record note, and I'd put it on the existing design decision record I think that's the pattern that's used for pilots anyways. And I wouldn't worry about putting figures there! We'd only be looking at data from my public repo. Worse is if we don't commit like last time and lose the numbers for the study".

Why now: the first window's rows exist, but two things block evaluating them.

- No session of this repository in that window is a clean arm under the exclusion above, because each either ran with `review_orchestrator_routing` on or has no recorded key state (`docs/session-config-keys-log.md`).
- `docs/design-decisions/architect-disposition-challenge-pilot.md` § "Pre-registration, fixed before enabling" requires a withheld-values file. No such file was found.

The engineer expects to decide the `review_orchestrator_routing` default before re-running this pilot, so the plan must hold for either outcome.

Intended outcome: a window that opens only after the thresholds are published in a merged note, and whose analysis set is chosen from recorded per-session key state and model use, not from dispatch counts.

## Approach

Publish the second window's six values in a PR that adds a note to the existing pilot record, and only then read the first-window copy once more, for its safety read. The note says the first window ended not evaluated, publishes the six values, and fixes the second window's routing arm and per-session analysis set, citing the record's own enable, window and close bookkeeping rather than restating it.

**Sequence.**

1. **Now, reading no row: secure and split the first-window copy (M1, M7).**
   - Confirm its directory lies outside every git working tree (`git -C <dir> rev-parse --is-inside-work-tree` does not print `true`) and, by `realpath`, outside the checkout and the config dir. Confirm the directory is mode `0700` and each file `0600`. On any failure, move the copy whole into a new directory made with `mkdir -m 0700` that passes.
   - Record privately the copy's modification-date cutoff, and the first window's enable and disable times with each time's source (rows 20, 24).
   - Run the record's "Path set" selection over the copy's file names alone, taking the PRs open at any point since the cutoff, a span that needs no row read to cover the key-on interval. Move the files it leaves out into their own private directory under M1.
2. **The values, then the PR (M2-M4).** The engineer writes the five values the record's "Withheld values" bullet names, and the minimum dispute count (row 31), and hands them to the session. One `code-writer` dispatch adds the note with those values. The PR's first push dates the values. This branch has no earlier push, so that first push carries the pinned commit. The note's commit is pushed and the PR opens. The PR body records that commit's id as the pin for the six values. No further row of the first-window copy is read before that push (row 23).
3. **The first window's safety read (M7).** Run the record's "Safety guardrail" read over the rows of the files step 1 selected, in the first window's key-on interval. A failure means not adopted: the record's "Action for not adopted" bullet applies, and this plan goes to step 6.
4. **Arm, dry run, enable (M5, M6).**
   - Once the routing default is decided, set the arm M5 names, as `docs/config-file.md` § "Writing a value" describes.
   - Run M6's dry run.
   - Meet afresh every precondition the record's § "Enabling, checking, disabling" lists, carrying none from the first window. The merged note stands for the withheld-values file, and the fixture pass/fail table is recorded in a private directory that passes step 1's location and mode checks. Four more apply: the routing default decided, the note's PR merged, the dry run passed, and step 3 passed. Enable and record the time as that section says.
   - Start each window session after the enable, or `/compact` a running one, so its config-keys row shows the key on. Change no routing value during the window.
5. **Close and evaluate (M1, M4, M6).** Take the copy the record's "Input" bullet describes into a new directory under M1. Run M6's selection that same day (G1), and record each session's inclusion and its reason privately. Compare the six values at the pinned commit with the note's text at close, by content, and disclose any difference in the outcome record. When the pinned commit can no longer be fetched, the outcome record says the values were not compared. A squash merge leaves the pinned commit off the default branch, so `git log` from the pinned commit cannot show a change made before the merge. Tally and evaluate as the record's § "Pre-registration, fixed before enabling" and § "Reader contract" say, with the note's narrowing, and publish under M4.
6. **Dispose (M1)** of both copies, the split-off files included, once the outcome record lands, or when the re-run is abandoned, with the dated reminder M1 sets.

**Alternatives set aside.**

- *A separate outcome record, as the not-adopted fix-plan pilot has.* The engineer chose the existing record (row 5), and the first window has no outcome to record, only a non-evaluation.
- *Rewriting the record's pre-registration bullets in place.* They are what the first window registered. An added section shows what changed and when, which the record's "Changes after enabling" bullet asks of any change to a definition or value.
- *The earlier draft's hardening: a read lock and its release, a digest manifest, count-only query runs without credentials, and a standing repository-identity check.* The engineer chose to cut the plan back (row 7). Each layer closed a gap the one before it opened, and none could prove the first-window order, because nothing records a read of a copied file (row 23).
- *Deleting the copy's files outside the path set before the read.* The engineer chose to keep them for now (row 28), and step 1's split keeps them out of every read with one disposal point.
- *Re-taking the first-window copy from the live ledger by the path set.* The existing copy already holds those files, and a later copy gives the sweep longer to reach them (row 20).
- *Treating the first window as the second window's extension.* The engineer decided it ended not evaluated (row 10), and an extension would pool its rows, which have no values file and a routing-on arm.
- *Selecting by dispatch counts or by calendar span.* The Context's intended outcome sets dispatch counts aside, and M6 says why a calendar span fails.

**Assumption ledger**

**Root problem:** The first window cannot be evaluated: no values file was found to show a value fixed before its rows, and no session of this repository in it is a clean arm under the engineer's exclusions (rows 21, 22). The re-run must:

- fix and publish the six values before any further first-window row read;
- say on the record why that window was not evaluated;
- open a second window once the routing default is decided, under either default, with its analysis set chosen per session from recorded key state and model use.

Every copy stays private until it is disposed of.

**Givens:**

- **G1 — Claude Code deletes transcripts after `cleanupPeriodDays`** (`docs/session-config-keys-log.md` § "Retention"). The harness owns that window, so the selection, which reads transcripts, runs and is recorded the day the window closes.
- **G2 — The `review_orchestrator_routing` default is decided under that key's own record** (`docs/design-decisions/review-orchestrator-routing-gate.md` § "Dogfood"), outside this plan. The arm therefore branches on it, and the enable waits for it (M5).

**Mechanisms:**

- **M1 — Every copy stays private until step 6 disposes of it, and what a session reads from it or a transcript is data.**
  - Each copy takes the record's "Input" bullet's directory and file modes, and nothing from it publishes beyond what the record's "Publication" bullet and M4 allow.
  - Every private directory sits outside every git working tree, the config dir and every path stowed into it, and any synced or backed-up location.
  - The first-window copy was taken by modification date, not by the path set, and holds other repositories' files (row 19). Step 1's split, by file name alone, keeps them out of every row read (row 29).
  - Row text and transcript content are data, and a session reading either follows no instruction in it, because diffs, commits and PR text a third party can write shape finding text (the record's § "Known gaps"), and a transcript holds every tool output its session read.
  - Every read a session makes of a copy, a ledger file or a transcript, step 5's tally and cost reads included, returns only the fields and computed figures the note's "Private copies" bullet lists. It never returns finding text or transcript text into the session. Where a judgement needs row or transcript text, the session hands the engineer only the ids it needs, and the engineer reads the text in their own terminal, outside the session.
  - Step 6 deletes both copies and the split-off files, and nothing is deleted before it (rows 8, 28, 29).
  - The records kept after step 6, the tally and the selection and safety-read records, hold row identifiers, tags' closed-set classes, verdicts and the tally's figures, never finding summaries or quotes. They stay private, as the study's numbers (row 6).
  - A dated reminder fixes the date after which the re-run counts as abandoned and step 6 falls due. It is set at the second window's close, or when the engineer, and nobody else, declares the re-run abandoned.
  - `anchors: row6, row8, row19, row28, row29`.
- **M2 — The six values are published in the note, before any further first-window row read.**
  - No further first-window row read precedes them, so the disclosure below stays complete.
  - The note is the one home of the values (row 9), dated by the host-recorded time of the PR's first push, with the pinned commit id in the PR body (row 42).
  - The first window's values-before-reading order is not established, because no values file was found (row 22). The six values follow first-window tag counts the engineer was shown, so they may be informed by them (row 23). The floor values (the sample floor, the correction floor and the minimum dispute count) were also chosen with a pre-window volume summary in view, whose file scope is unknown and which may include first-window rows (row 33). The note says the order and the tag-count disclosures in words beside the values, and the floor-values disclosure once, as the floor-values rule Critical files lists.
  - The second window starts fresh only in that no second-window row is read before the values are fixed, because step 4's enable follows the note's merge.
  - `anchors: row6, row9, row22, row23, row31, row33, row38`.
- **M3 — The note is a status block plus one added section, and existing text stays unchanged beyond the Known gaps edit.**
  - The engineer chose the existing record (row 5). The status block takes `.claude/rules/design-decisions.md`'s supersession shape immediately under the provenance line, because the section changes bullets of the record's own pre-registration and reader contract.
  - The Known gaps edit is the one added sentence plus the one per-round wording change that the status block names, and no other existing line changes.
  - The section says, in words and with no count, why the first window was not evaluated (rows 21, 22). It says no values file was found, not that no value was fixed, and records D2 (row 10). The next enable opens a fresh first window with its own extension right, as the record's "Changes after enabling" step 4 gives a re-enable after a recorded disable.
  - Editing the record is no recorded disable, because the record is not among the four spans that bullet lists.
  - `anchors: row5, row10, row21, row22`.
- **M4 — The six values publish, and a verdict that compares a figure with one publishes only on a per-verdict yes.**
  - The note publishes the six values, superseding the "Withheld values" bullet's "never published" for those values only (rows 9, 38).
  - Each verdict that compares a figure with a value publishes only with the engineer's yes at evaluation, proposed and cited as `docs/private-project-redaction.md` § "The owner can authorize one figure, case by case" asks (rows 16, 17). The record withheld the values because a value paired with its verdict bounds the figure.
  - The adoption outcome also needs a yes at evaluation (row 18).
  - The safety-guardrail verdict compares with no value (the record's "Safety guardrail" bullet), so it publishes without an ask (row 17).
  - A stratum reported as not evaluated, an agreement check not evaluated below the minimum dispute count, and a window called conclusive, inconclusive or extended are verdicts of the same kind, so each publishes only on a per-verdict yes (row 39).
  - Each published pass-or-fail verdict reads "passed" or "did not pass" against its stated value or rule, in those words.
  - Every count, rate or share from either window stays under the record's Publication bullet. A later release of one takes `docs/private-project-redaction.md` § "This repository, one account"'s scope bar, or § "The owner can authorize one figure, case by case", when it is proposed (row 8).
  - `anchors: row8, row9, row16, row17, row18, row38, row39`.
- **M5 — One arm value, set on the enabling account once the routing default is decided, and held through the window.**
  - The enable waits for that decision, which the engineer expects to make first (row 2).
  - `review_orchestrator_routing` is `true` if routing ended default-on (row 11), and `false` if it ended default-off, because row 3 leaves out every session with routing on and row 11 lifts that for default-on only.
  - The arm keys on the account's resolved value, not the stow default, because a default flip cannot rewrite a scaffolded `false` row (row 25).
  - A change during the window is a recorded disable, handled by the record's "Changes after enabling" steps, because the config-keys log shows a mid-session change only from the session's next event (`docs/session-config-keys-log.md` § "State at a transcript record").
  - `anchors: row2, row3, row11, row25`.
- **M6 — The analysis set is chosen per session, and a dry run checks the rule before the enable.**
  - It narrows only the figures the decision rule compares with a value: the primary metric's strata, the sample floor, the agreement share, and the interrupt and tag-coverage figures. The safety guardrail with its DEFER list, the `barred` cell, the first-line count and the cost reads still read every row in the window, because a barred DEFER does harm whichever session wrote it.
  - A row whose `challenge:` tag lies outside the region's closed set counts in no stratum of the primary metric, and the tally reports how many such rows the window holds (row 30).
  - Every test below reads the `model` field of a record or Agent dispatch, never a text match on a model name, because third-party text in a transcript can contain one.
  - A payload row enters a narrowed figure only when its session passes every test below. A failed test drops the whole session (row 4).
    - The session's governing config-keys row at the ledger row's `event_time`, found as `docs/session-config-keys-log.md` § "State at a transcript record" describes, holds the arm's routing value and `architect_disposition_challenge_pilot` = `true`. Routing state comes from that row alone. Unknown state fails, `unreadable` and a session with no config-keys row included. The selection record reports those sessions as unknown, apart from any recorder-failure count, as that file's § "Coverage" says.
    - The main-session transcript exists at the path that file's § "Joining a row to its transcript" names.
    - No transcript carrying the session's id, subagent transcripts included, shows a Fable model on any record or as the `model` of any Agent dispatch (row 3).
    - The main-session transcript shows no Opus or Fable model on any assistant record (row 3). The test reads that file only, because every challenge dispatch is Opus by design (the record's "What every case checks" bullet).
    - Under the `true` arm, no `review-orchestrator` dispatch of the session ran on Opus (row 13).
  - The dry run, which the engineer kept (row 15), is the first check of rows 26 and 27. Before the enable, the selection runs once over recent sessions on the enabling account. It reads only this repository's sessions and ledger files, selected by the record's path set, never another repository's. It must show:
    - One session that passes every test, the first test's `architect_disposition_challenge_pilot` half read but not required, because the key is off before the enable (row 24).
    - One session with an Opus main session that fails.
    - Under the `true` arm, one routed round's ledger rows joined to its main session.
    - A private figure for the engineer alone: the share of recent sessions that pass every test. It is never published in a note, PR text, commit message, plan edit, outcome record or ledger row. The engineer computes it in their own terminal from the dry-run output. The dry run writes its per-session output to the private directory and reads back only the three exemplar cases. The window needs enough passing sessions to reach the sample floor, so a low share is a reason to reconsider before the enable.
  - Two lighter selections fail. A calendar span keeps sessions started before the enable, whose routing rows are stale, and keeps Opus and Fable sessions. A per-round selection reads "runs" as rounds, which row 4 rules out.
  - `anchors: root, row3, row4, row13, row15, row26, row27, row30`.
- **M7 — The first window gets the safety read, and a pass gates the next enable.**
  - The engineer kept it (row 14). The record's "Changes after enabling" step 2 gives every key-on interval that read and makes a failure not adopted. It compares with no value, so it is the one read a window with no values file can take.
  - It reads only the files step 1's split keeps, inside the key-on interval from the recorded enable to the recorded disable (row 24). Where a time was not kept, the earliest or latest `challenge:`-tagged row's `event_time` stands in. A stand-in can only shrink the interval, so the private safety-read record says the read may miss rows outside it.
  - Its completeness rests on row 20. Its reader already knows the first-window tag counts (row 23), which a read that compares with no value can carry unguarded.
  - `anchors: row14, row19, row20, row23, row24`.

**Assumptions:**

| # | Assumption | Tag |
|---|---|---|
| 1 | The engineer agreed to re-running the pilot | `[engineer-verified: "yes do that, and I'm not surprised."]` — it covers the re-run |
| 2 | The routing default will likely be decided before the re-run | `[engineer-verified: "i'm likely making a decision on that pilot (default on or off) before I resue the disposition pilot"]` — "likely", so step 4 makes that decision an enable precondition |
| 3 | The analysis set leaves out runs where the routing pilot ran, Fable was invoked, or Opus or Fable ran the main session | `[engineer-verified: "We should only include runs where review-orchestrator pilot wasn't running at the same time and we should exclude runs where Fable was invoked and where Opus or Fable were running the main session."]` |
| 4 | A run is a whole session, so an exclusion drops the whole session | `[engineer-verified: "Run = whole session (Recommended)"]` |
| 5 | The note goes on the existing record | `[engineer-verified: "I think there should be a design-record note, and I'd put it on the existing design decision record"]` |
| 6 | Losing the study's numbers, as last time, is the worse outcome | `[engineer-verified: "Worse is if we don't commit like last time and lose the numbers for the study"]` — which numbers it means is the session's reading: the six values the note commits, and the tally M1 keeps private |
| 7 | The plan is cut back rather than taken to review round 2 | `[engineer-verified: "Cut it back (Recommended)"]` — it covers the cut-back, not which items stay |
| 8 | The cut-back keeps six items: the existing copy with a disposal point; the five values fixed before the enable; the note on the first window; the selection rule; the arm rule; and the enable once the routing default is decided. It also cites the redaction doc's per-figure route for any later figure | `[unverified]` — the session's description of row 7's option, not its label |
| 9 | D1: the note licenses only the five values | `[engineer-verified: "License only the five values now (Recommended)"]` — read against D1's question, it covers what the note licenses now, not how a later figure publishes |
| 10 | D2: the first window ended and is not evaluated | `[engineer-verified: "Ended, not evaluated (Recommended)"]` |
| 11 | D3: if routing ends default-on, the second window measures with `review_orchestrator_routing` on | `[engineer-verified: "Measure with routing on (Recommended)"]` — read against D3's question, it covers the default-on branch only |
| 12 | The plan touches the pilot key on the enabling account alone | `[unverified]` — the choice is the session's reading, not a quote from the engineer. That no copy or figure takes another account's rows is `[verified: docs/design-decisions/architect-disposition-challenge-pilot.md:100, :182, :326]` |
| 13 | Under the `true` arm, a session whose `review-orchestrator` dispatch ran on Opus fails, as an Opus main session does, because that agent runs the round | `[unverified]` — the session's extension of row 3. The agent's role and its `model: sonnet` pin are `[verified: claude/.claude/agents/review-orchestrator.md:3-5]` |
| 14 | The plan keeps the first window's safety read | `[engineer-verified: "Keep the first-window safety read"]` |
| 15 | The plan keeps the selection dry run before the second enable | `[engineer-verified: "Keep the selection dry run"]` |
| 16 | Verdicts publish one at a time, on a yes given at evaluation | `[engineer-verified: "Per-verdict yes at evaluation (Recommended)"]` — it covers how verdicts publish. The rule's detail is row 17 |
| 17 | A verdict that compares a figure with a value publishes only with the engineer's live yes at evaluation naming the figure. The safety-guardrail verdict compares with no value and publishes without an ask | `[unverified]` — the session's description of row 16's option, not its label. Proposing and citing the yes in the redaction doc's form is the session's addition |
| 18 | Publishing the adoption outcome also takes a yes at evaluation | `[engineer-verified: "Outcome also needs a yes (Recommended)"]` |
| 19 | The first-window copy was taken 2026-11-20 by file modification date, not by the path set, and holds other repositories' files. It sits in a private directory at mode `0700`, with each file at `0600` | `[unverified]` — the dispatching session's report, which a reviewer repeats. Step 1 checks the location and the modes |
| 20 | The copy holds every file with a first-window row | `[unverified]` — it rests on two conditions. The copy's cutoff falls at or before the first window's enable, and step 1 records the cutoff. The sweep deletes a file only once its last write is more than 30 days old: the floor is `claude/.claude/hooks/_lib.sh:5694`, the append path passes it at `claude/.claude/scripts/review-ledger.sh:696`, and `clear-stale` never goes below it (`_lib.sh:5738`). Verification checks the record's merge date against the cutoff |
| 21 | No session of this repository in the first window passes the arm test: each ran with `review_orchestrator_routing` on or has no config-keys row, so its routing state is unknown | `[unverified]` — the dispatching session's finding, not re-read here |
| 22 | No first-window values file was found | `[unverified]` — the dispatching session found none in any transcript or on disk, which does not rule out one written and lost |
| 23 | Tag values of first-window rows were counted and shown to the engineer in the planning session, which precedes the six values. Which of the copy's files those counts covered, this repository's alone or other repositories' too, is unknown. Nothing records a read of a copied file | `[unverified]` — the dispatching session's and a reviewer's report. File access times are not relied on |
| 24 | The pilot key is off on the enabling account, so the first window has ended | `[verified: the enabling account's claude-config.toml, read in an earlier draft of this plan]` — not re-read in this revision |
| 25 | A routing default flip cannot tell a scaffolded `false` row from a deliberate one, so the enabling account's value can differ from the new default | `[verified: docs/design-decisions/review-orchestrator-routing-gate.md:66]` |
| 26 | A transcript shows the main session's model on its assistant records, and the model of any Fable subagent or Agent dispatch | `[unverified]` — the dispatching session's evidence. M6's dry run is the first check |
| 27 | A routed round's ledger rows, appended from inside `review-orchestrator`, carry the main session's id | `[unverified]` — inferred from `_resolve_session_id` in `claude/.claude/scripts/review-ledger.sh:216`. M6's dry run checks it |
| 28 | The first-window copy's files from other repositories stay in it for now | `[engineer-verified: "Keep for now (Recommended)"]` |
| 29 | Those files stay whole in the copy's private directory until the path-set selection runs, then move to their own private directory, and none is deleted before step 6 | `[unverified]` — the session's description of row 28's option, not its label |
| 30 | A first-window row may carry a `challenge:` tag value outside the region's closed set of outcome and scope values, so the rule for such rows does not depend on having observed one | `[unverified]` — a design premise, not an observation, and the rule relies on no read of whether any row carries one. The closed set is `[verified: claude-skills/skills/code-review/SKILL.md:437-445]` |
| 31 | The note adds a sixth value, a minimum count of `escalated-*` rows below which the agreement check is not evaluated, because one answer at one stop could otherwise decide adoption. The engineer accepted the session's proposed minimum with the other five (row 33) | `[engineer-verified: "Yes, add it (Recommended)"]` — it covers adding the sixth value. Row 9's text records what was licensed earlier and stays unchanged. The `plan-architect` consult's reason is the session's relay, not the engineer's |
| 32 | The sample floor applies to each stratum on its own: the window is conclusive once at least one stratum reaches it, and a stratum below it is reported as not evaluated and keeps running | `[engineer-verified: "Yes, rule (a) (Recommended)"]` — the reasons the note states are the consult's, not data |
| 33 | The six values are accepted as proposed in the session, with the floor values chosen after the engineer saw first-window tag counts and a pre-window volume summary. Which files that summary covered, this repository's alone or other repositories' too, is unknown | `[engineer-verified: "I think that looks good."]` — it covers the proposed set, not the summary's scope. |
| 34 | An earlier proposal of the six values existed, from before the engineer saw the first-window tag counts, and the set row 33 accepts may differ from it in one or more values | `[unverified]` — the session's account of the planning session, not the engineer's statement |
| 35 | The tag-coverage guardrail's `/review-pr` test applies per round, not per session | `[unverified]` — the session's reading of the record's text, not an engineer statement |
| 36 | The extension choice is made from per-stratum row counts alone, before any rate is computed | `[unverified]` — the session's reading of the record's text, not an engineer statement |
| 37 | Rows in one round are correlated, so a stratum's row count overstates its independent observations, and Known gaps gains a sentence saying so | `[unverified]` — the session's reading of the record's text, not an engineer statement |
| 38 | The sixth value, the minimum dispute count, publishes with the other five | `[engineer-verified: "Yes, the sixth value, whatever it is, that gets published. Sure."]` — it covers publishing the sixth value. Row 9's text records what was licensed earlier and stays unchanged |
| 39 | The not-evaluated, inconclusive and extended outcomes are verdicts under M4's per-verdict yes | `[engineer-verified: "So in your words, extend M forward to cover those outcomes. Yes"]` — the engineer's "M" is read as M4, and the wording of the extension is the session's. The engineer also said "It's completely fine to reveal row counts. Don't go crazy. Don't get paranoid." That remark names no figure or command, so it is no per-figure authorization and does not relax M4's last bullet |
| 40 | The engineer's "ask the architect" delegation of disposition-time questions happens on branches where this pilot is off, so the confound touches only key-on versus key-off comparisons, not the primary metric or the agreement check | `[engineer-verified: "branches where the pilot for the architect challenging is off, where I ask the architect to consult"]` — it covers where delegation happens. That the pilot's own figures read key-on sessions only is `[verified: M6's first test]`. The architect consult's reading of which comparisons it touches is the session's relay |
| 41 | The descriptive-figures bullet stays in the plan and the note | `[engineer-verified: "Keep it (Recommended)"]` — it covers keeping the bullet. The bullet's wording is the session's |
| 42 | The private values file is dropped, and the PR's first push dates the six values | `[engineer-verified: "Drop the private values file, I don’t need a reminder or to delete any files"]` — it covers dropping the file, row 43 gives the engineer's reading of what else it covers. The architect's reasons are the session's relay |
| 43 | Row 42's "any files" reaches only the architect's proposed extras, the step-1 reminder and the early deletion. The copies' disposal and reminder rules stay | `[engineer-verified: "Only the architect's extras (Recommended)"]` — it covers that reading of row 42 |

## Critical files

- `docs/design-decisions/architect-disposition-challenge-pilot.md` — modify, in one `code-writer` dispatch at step 2:
  - A status block immediately under the provenance line, above the existing partial-supersession block and in its shape: a lead line, one bullet per changed site (13 bullets), then "Everything else here stands." The lead says the first window ended not evaluated and points to the new section. The 13 bullets name the "Unit", "Primary metric", "Tag-coverage guardrail", "Window and sample floor", "Agreement check", "Decision rule", "Withheld values" and "Publication" bullets, the Reader contract's "Input" and "Tally" bullets, the preconditions of § "Enabling, checking, disabling", and, in § "Known gaps", the bullet on whether a `/review-pr` pass appends ledger rows, whose per-session wording becomes per round, and the added sentence on correlated rows. The "Window and sample floor" bullet's sentence that the value is chosen, not sourced from any data, is marked superseded for the second window's sample floor by the new section's floor-values disclosure, in words with no count.
  - A new section, `## Second window, fixed before re-enabling`, between `## Pre-registration, fixed before enabling` and `## Ad-hoc key-on/key-off note, outside the pre-registration`, one bullet per line, holding:
    - Why the first window was not evaluated, in words and with no count, and that the next enable opens a fresh first window with its own extension right (M3).
    - M1's rules on the first-window copy, and that its one further read is the safety read, whose pass gates the next enable (M7).
    - The six values, one sub-bullet each, then M2's sentences on the first window's order and on the tag counts that may inform the values.
    - Rules the record leaves open, stated before the values publish (rows 31, 32, 33, 35, 36, 37). They fall under M2's "may be informed by" sentence with the values, and no rule's text states or cites a count:
      - The sample floor applies per stratum, as row 32 says. The Decision rule bullet's "every stratum" then reads "every evaluated stratum". A stratum below the floor continues only as the record's one extension.
      - The agreement check is not evaluated below the minimum dispute count.
      - The tag-coverage guardrail's `/review-pr` exclusion applies per round, not per session.
      - The extension choice is made from per-stratum row counts alone, before any rate is computed.
      - The second window's floor values (the sample floor, the correction floor and the minimum dispute count) were chosen with pre-window aggregate volume in view, and no count is published. The note defines "pre-window" in words, as the span before the second window opens, and states no claim, by wording or implication, that the read covered this repository alone (row 33).
      - Rows in one round are correlated, so a stratum's row count overstates its independent observations, a sentence in Known gaps beside the rate-with-no-interval gap.
    - M4's publication rules, one sub-bullet each.
    - M5's arm rule, and that a routing change during a window is a recorded disable.
    - M6's selection rule, with the figures it narrows and one sub-bullet per test, and its rule for a `challenge:` tag outside the closed set.
    - The descriptive figures: the rounds figure from `docs/pr-cost.md` § "The `review_rounds` cell", DEFER rows per PR and the review comment count. The engineer reads them in their own terminal, for this repository's PRs on the enabling account only, never through `--all-accounts` or an export. They move no decision-rule value, and each publishes only on the owner's per-figure yes (M4's last bullet). The note states that the engineer's consult delegation happens on key-off branches, so a key-on comparison is not like for like (row 40).
    - M1's private-directory, row-text and disposal rules, citing the "Input" bullet's modes rather than restating them.
    - The added enable preconditions: the routing default's decision, the note's merge, M6's dry run, and the first window's passed safety read.
  - The Sources line gains `docs/session-config-keys-log.md` and `docs/private-project-redaction.md` § "The owner can authorize one figure, case by case".
  - The added lines carry no digit outside the six values, a date, a section reference and a file name in the Sources line.
- No other repository file. The private artifacts stay outside the diff, under `<private-dir>`: the first-window copy and its split-off files, the safety-read record, the dry-run result, and the second window's copy, selection record and tally.
- **Reuse:** the record's path set, copy modes, fixture set, key-off check and enable check, unchanged; the state and join rules in `docs/session-config-keys-log.md`; and `docs/config-file.md` § "Writing a value" and § "Querying a value". No script is added or changed.

Projected diff: 71 lines (69 additions and 2 deletions), all in the record, as `git diff --numstat origin/main` measures the drafted text. The unit is a line of the record, blank lines included, and a replaced line counts as one deletion plus one addition.
- 17 additions for the status block: the lead line, its 13 bullets, the closing line and two blank lines.
- 49 additions for the new section: its heading, the bullets and sub-bullets listed above and its blank lines.
- 2 additions for the Known gaps sentence as a new bullet and the per-round wording change as a replaced line.
- 1 addition for the Sources line, replaced.

## Verification

- `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py` passes on the branch. `claude-skills/skills/tests/test_code_review_challenge_and_round_cap.py` reads this record for the region's tag tokens, and the note keeps every one, its Known gaps wording change included.
- `git diff origin/main -- docs/design-decisions/architect-disposition-challenge-pilot.md` shows only the status block, the new section in its named place, the Known gaps sentence and per-round wording change, and the Sources line. Every other line of the record is unchanged.
- Each `§ "..."` citation the new text adds matches a heading in its target file, checked with `Grep` for the heading literal.
- `git diff -U0 origin/main -- docs/design-decisions/architect-disposition-challenge-pilot.md | grep -E '^\+[^+]' | grep -oE '[0-9]+'` prints every digit run in the added lines, and each one is part of one of the six values, a date, a section reference, or a file name in the Sources line.
- A read-back of the new text finds:
  - No private path, session id, or enable or disable time, and no count from the config-keys log, a transcript or a copy.
  - The six values matching what the engineer handed the session.
  - Each existing rule the note relies on cited by section, not restated.
  - No spelled-out quantity that the digit check cannot see.
  - No reason phrased as an observation about the window's data rather than as design rationale, row 31's reason included.
- Before push, and again on every later commit message, PR body edit, plan edit and outcome record in the re-run, the digit check and read-back above also run on the commit message, the PR body and the plan file, where no digit run may be a count taken from any private source, such as the config-keys log, a transcript, a copy, the pre-window volume summary, the first-window tag counts, or a `pr-cost` or `gh` read.
- `/code-review` on the staged diff.
- Private steps, checked outside the repository and recorded privately:
  - Step 1's location and mode checks pass for each private directory before any file goes in, and for the first-window copy before its split. After the split, the directory the safety read reads holds only files the path set selects.
  - `git log --diff-filter=A --format=%cs -- docs/design-decisions/architect-disposition-challenge-pilot.md` on `main` gives a date on or after the cutoff step 1 recorded, so no file with a first-window row was last written before the cutoff (row 20).
  - The safety-read record notes its start time, later than the PR's `createdAt` from `gh pr view <number> --json createdAt`.
  - Before the second enable, the dry run includes and excludes as M6 says.
  - After step 6, `<private-dir>` holds neither copy nor the split-off files.
- Not verified by this plan:
  - Rows 19-23, 26, 27 and 30.
    - Step 1 checks row 19's location and modes.
    - The merge-date check above settles row 20.
    - The dry run is the first observation of rows 26 and 27.
  - Rows 8, 12, 13, 17, 29, 35, 36 and 37, which record the session's readings and design, not checked facts.
  - Row 34, the session's account of the planning session, which this plan cannot check.
  - The scope of row 33's volume summary, which is unknown.
  - Row 24, read in an earlier draft and not re-read here.

## Out of scope

- Raising the ledger sweep floor or changing its trigger. It would change retention for every stow consumer, and the private copy keeps the rows without it.
- Checking repository identity beyond the path set. The path hash binds a path string, not a repository (`claude/.claude/hooks/_lib.sh:644-649`), so another repository reviewed from a path in the set would pass. The cut-back leaves the record's "Path set" bullet as the selection, and adding a repository identifier to ledger names would change them for every stow consumer.
- Copying the first window's transcripts. Its one further read, the safety read, reads ledger rows only.
- Changing the pilot key on any account other than the enabling one. Row 12 records the session's choice, and the record's "Unit" and "Input" bullets already keep such an account's rows out of the measurement, because the ledger is per config dir.
- Tallying any first-window figure beyond the safety read. The window is not evaluated (row 10).
- Deciding the `review_orchestrator_routing` default, which that key's own record governs (G2).
- A selection or reader tool in the repository. The record keeps the reader private, and the selection runs by hand or ad hoc query, recorded with its steps as the record's "Tally" bullet asks of the tally.
- Changing the config-keys hook to record mid-session key changes. M5's no-change rule makes it unnecessary for this window.
- Correcting the PR-body notice at its source in `claude-skills/skills/code-review/SKILL.md`. The record's Known gaps name it as a separate change, and its enable preconditions record it as met or consciously waived.
- The outcome record, any narrowing or default-change PR, and the revert. The record's "Decision rule" bullet and § "Revert contract" govern them after evaluation.
- A CHANGELOG entry, because the note changes no shipped behavior.
- The ad-hoc key-on/key-off note's publication limit, which the note leaves unchanged.
- Counting `HALT:` escalations left unlogged under the `true` arm. The record's § "Known gaps" already names that path, and every figure the record defines counts ledger rows.
