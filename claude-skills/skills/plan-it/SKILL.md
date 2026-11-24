---
name: plan-it
description: >
  Produces an implementation plan and hands off to /plan-review.
  TRIGGER when: asked for a plan or implementation strategy
  for work spanning multiple files or domains. DO NOT TRIGGER when:
  single-file tweaks, "just implement it" requests, or when a plan
  already exists (use /plan-review instead).
user-invocable: true
argument-hint: "[optional topic or ticket id]"
---

# Plan-it

## Step 1 — Branch + plan file

`.claude/plans/` holds plans that gate a change to this repository — the plan file is provenance for that change, not the deliverable itself. Work that turns out to make no repository change (an audit, a status assessment) still runs this skill end to end, `/plan-review` included; scaffold the plan file here as normal, and Step 7 decides whether it gets committed.

**If plan mode is active:** write the plan to the harness-provided plan path (named in the plan-mode system-reminder). Skip branch creation here — plan mode would block it. Resume the branch-management flow only after `ExitPlanMode` is approved: derive the slug, run `branch-management`, and move the plan file to `.claude/plans/<topic-slug>.md` on the new branch.

**If that write fails** (e.g. a machine-level policy denies the harness-provided path): this is the one case where creating a branch happens before `ExitPlanMode` is approved — not a general license to branch during plan mode, only a recovery once the designated path write has already failed. In a git repository, derive the slug now, create its worktree (`branch-management`'s worktree steps), and write the plan to the repo-relative `.claude/plans/<topic-slug>.md` there instead — a path outside whatever denied the harness-provided one. The branch/worktree already exists by the time `ExitPlanMode` is approved, so skip the post-approval `branch-management` call above; nothing needs to move. Outside a git repository there is no repo-relative path to fall back to — present the full plan as chat text instead of a file and skip `ExitPlanMode`, asking the user to approve conversationally.

**Otherwise:** if on the default branch, invoke the `branch-management` skill to pick a slug and start from a fresh default tip. If already on a feature branch, keep it and derive the slug from the branch name — if the branch name contains `/` (e.g. `GH-42/add-auth`), use only the portion after the last `/`. Plan path is `.claude/plans/<topic-slug>.md` on the implementation branch (per `branch-management`'s "plan files go on the implementation branch" rule).

If `.claude/plans/<topic-slug>.md` already exists, open it for revision in place rather than scaffolding a new file.

## Step 2 — Discovery

Restate the problem, why now, and the intended outcome in one short paragraph. If any of the three is unclear, ask the user before moving on. This becomes the lead of the plan's `## Context` section, with the first sentence stating the goal. Under the goal sentence, add an `Ask:` line: what the engineer asked for, quoted under Step 5's `[engineer-verified]` rules, or carried per the next paragraph, or cited to the ticket it came from. Wording the session drafted and the engineer accepted goes in as `Ask: "<wording>" — accepted via label "<label>"`. `/plan-review` measures the plan against this line.

The `Ask:` line holds the goal, never a decision on how to reach it. When this session resumed from a handoff that has a §1.5, start the line with the Goal entries of its `handoff` §1.5, verbatim, each marked `(carried from a handoff)`, joined onto one line so no carried quote starts a heading line. A later quote changes the goal only when it names that change: the engineer's own directive that drops, adds or replaces part of the goal or its scope, or their selected label or typed answer to a question whose shown text named the change. Only such a quote joins the line. When a quote might change the goal without naming the change, ask the engineer before adding it. Any other later quote is a decision: record it as its own `[engineer-verified: "<quote>"]` ledger row.

## Step 2.5 — Load project-specific layer

If a project-specific layer exists for this skill, load it now. Glob for `.claude/skills/plan-it-*/SKILL.md` from the repo root (resolved via `git rev-parse --show-toplevel`); if exactly one matches, read it with the Read tool — the layer's rules apply to the steps below. If multiple match, list them and stop — that's a config error in the project, not something you can resolve. If none match, proceed without a layer.

## Step 3 — Codebase exploration

Find similar features, the target subsystem, and integration points. Spawn `general-purpose` subagents in parallel when scope warrants — judge fan-out from surface area, do not default to a fixed count. Pass an explicit `model: sonnet` per `CLAUDE.md`'s Model Routing rule. Collect the absolute path of every file each subagent flags, plus its summary, as evidence — not as a design conclusion to hand off unread. The actual design reasoning happens in Step 5, where `plan-architect` reads the files it needs and forms its own conclusions (`subagent-delegation`'s locate-and-report vs. read-and-reason split: comprehension reads belong with whoever reasons over the design, not whoever located the files). Do not use `Explore` here; its read-excerpt window is wrong for design-context analysis.

**Pattern claims require a grep, not a single example.** Before calling a shape "canonical," "the existing pattern," or "how the codebase does X," run `git grep` (or ripgrep) and cite call-site counts (e.g., "12 of 13 modules use form X; exception at `path/to/file:NN`") rather than a single example.

**If the task is a debugging or root-cause investigation** (fixing a reported bug or incident rather than building a new feature), consult `root-cause-analysis` before exploring — establish the full symptom and verify your tools fully ingested their input before forming any hypothesis.

## Step 4 — Clarifying questions

List every underspecified decision (edge cases, error handling, scope boundaries, backward compatibility) and ask the user. Do not proceed until answered or the user delegates the call to you.

## Step 5 — Architecture design

Dispatch `plan-architect` with an explicit `model: "opus"` override to author this section — on every `/plan-it` run, regardless of what model the session itself is anchored to. Pass no `isolation: "worktree"` — the session is already anchored in the implementation branch's worktree, and `plan-architect`'s edits must land in this worktree's plan file.

The dispatch prompt carries:
- `MODE=plan-sections` as the prompt's first line, on every Step 5 dispatch including revision re-dispatches. This literal selects the plan-section grammar — `plan-architect` also serves ad hoc consults, so the mode can no longer be inferred from context.
- The plan file's absolute path as the prompt's second line, on every Step 5 dispatch.
- The Context paragraph from Step 2 and the answers gathered in Step 4, verbatim. Relay each answer as the selected label or the engineer's typed text; mark any option description you relay as your own proposal (CLAUDE.md §Working Style).
- Every Step 3 subagent's findings, framed as evidence rather than conclusions, plus the absolute path of every file it flagged.

Do not add a CLAUDE.md path or read instruction — `plan-architect` loads it automatically at startup, like every subagent except `Explore`/`Plan`.

**Heading lines.** A heading line is a line-start `## ` line outside fenced code, the rule `plan-shape.py` applies to the plan file and the splice below applies to a return. Before the first dispatch, the title and Context, `Ask:` line included, are already in the plan file. The hash below cannot see fences, so Context never carries a line reading exactly `## Approach`, fenced or not; quote that heading inline in backticks. Start each code fence on a line of its own, never on the same line as a list marker such as `-` or `1.`, because `plan-shape.py` does not model list items.

**Prepare.** Before this run's first dispatch, run `python3 ~/.claude/scripts/plan-shape.py prepare '<plan path>'`, passing the plan file's absolute path as one single-quoted literal word. When the file holds only its title and Context, the script appends the four headings with the placeholder under `## Approach`. It never edits a file in any other shape. The placeholder is the first non-blank line under `## Approach`, and it reads exactly `(pending: plan-architect)`. Dispatch only when the command exits 0 and prints `PREPARE: ready`. Otherwise give the engineer every `REASON` line, or the command's error if it printed none, through `AskUserQuestion`, and make no edit or dispatch.

In plan mode, a `plan-path` line for the harness-provided plan path means the script's path rule refuses that path. The run ends there, and the way forward to give the engineer is leaving plan mode and running `/plan-it` again, which starts the plan over under Step 1.

**Before every dispatch.** Make your last edit above `## Approach` first, then run `plan-shape.py`, then take the Context hash below, then dispatch. The run is `prepare` before this run's first dispatch and `check` before every later one. A later dispatch goes ahead only when that `check` exits 0 and prints a `STAGE` line, and any other output is handled as a failed `check` below.

**Context hash.** Run `sed -n '1,/^## Approach$/p' "<plan path>" | sha256sum` immediately before each dispatch, after the `plan-shape.py` run in **Before every dispatch.** Run it again on every return, failed and truncated returns included, before any splice or re-dispatch, and again after any splice. Stop and report to the engineer when any of these holds:

- the two digests differ;
- either digest starts `e3b0c442`, the digest of empty input, which an unreadable path also yields;
- either run printed anything besides its digest line.

After every dispatch, `Read` the plan file. `plan-architect` writes its sections itself, so a successful return carries no `##` headings. When the return carries all four headings as heading lines, in order, splice it in with one `Edit` whose `old_string` is the file's region from its `## Approach` heading line to the end, replacing it with the return from its `## Approach` heading line on, verbatim. Every byte above that heading stays untouched; never use a whole-file `Write`. Relay the return's reason line to the engineer.

**Check.** After every dispatch, once the Context hash and any splice with its own hash are done, run `python3 ~/.claude/scripts/plan-shape.py check '<plan path>'`, passing the path the same way. With or without a splice, the dispatch is complete only when the command exits 0 and prints `CHECK: pass`.

If the returned design names an open decision it left to the user, ask it via `AskUserQuestion` per Step 4 and re-dispatch with the answer rather than settling it in the main session. The plan file's path is already on line 2, so do not re-inject the plan text inline — `plan-architect` holds `Read` and can load its own prior draft.

A failed `check` that exits 0 and prints a `STAGE` line re-dispatches. It prints one only when every `REASON` code is `placeholder`, `headings` or `empty-section`. Any other output goes to the engineer through `AskUserQuestion`, with every `REASON` line or the command's error if it printed none, and no further dispatch or edit of the plan file follows.

Every `plan-shape.py` stop sent to the engineer, from `prepare` or from `check`, except the `plan-path` stop for the harness-provided plan path above, ends the run until the engineer says the plan file is fixed. Then re-run the mode that stopped and act on its new output.

Treat a dispatch as first authoring when the `prepare` or `check` run just before it printed `STAGE: first-authoring`, and as a revision otherwise, including when that run printed no `STAGE` line. When a dispatch ends without a normal return, judge its stage by the run before it, not by the `check` after it.

Re-dispatch, rather than repairing inline, on any of these:
- A return carrying some but not all four headings.
- A failed `check` that prints a `STAGE` line, as above.
- A dispatch that ends without a normal return (a context-limit failure, an error return, or no completion), as follows:
  - At first authoring, re-dispatch when `check` then fails with a `STAGE` line.
  - On a revision, re-dispatch when `check` then passes or fails with a `STAGE` line, because a revision that died partway can pass it.

A near-empty return is the success shape, so never judge it truncated. A re-dispatch is always safe: `plan-architect` reads the plan file as it now stands, so a partial write is revised, not lost.

**Review findings.** Only `plan-architect` edits a plan from its `## Approach` heading down in answer to a `/plan-review` or `/code-review` finding, and it gets a review round's findings together in one revision re-dispatch. After line 2, that prompt carries the findings in place of the Context and Step 3 evidence bullets, with each mark and answer on a prompt line outside every quoted finding:
- Number the findings, each as the review rendered it, under a lead-in naming the review and round, with the findings-file path of each reviewer that wrote one.
- Mark a finding `blocking` when it made a `/plan-review` verdict **Request changes** or `/code-review`'s enforcement-invariant rule covers it.
- Mark the plan `approved` for a `/code-review` round, a plan with a commit on this branch, or a plan the engineer approved this session. A commit is the observable `/plan-review` Step 4 uses for a plan the engineer has already approved.
- When you cannot tell whether a finding is `blocking` or the plan is `approved`, mark the finding `blocking` and the plan `approved`.
- Carry each engineer answer on its own prompt line, in a block that precedes every quoted finding body: the number of the finding it settles, the question it answered, and the selected label or typed text, with any option description marked as your own proposal.

Step 5's **Before every dispatch.**, **Context hash.** and **Check.** apply to this re-dispatch. After the dispatch, check each `[engineer-verified: "<quote>"]` quote it added or changed as the **Quote provenance.** paragraph of `plan-review/SKILL.md` § "Step 4 — Design-fitness gate" says, and ask the engineer about any you cannot find. Also keep each ledger row carrying `[engineer-verified`, from its number through its `anchors:` list, as it stood before the round's first review-findings dispatch. After the round's last return, ask the engineer about any such row removed or changed since then that no answer-block line settles, and about any added `[engineer-verified` tag with no quote to check. On the return:
- Relay each `decline` line to the engineer with its reason.
- Ask each `open` line as an open decision above.
- Re-dispatch once more with only the findings the return gave no line, and ask any still without one as an open decision.

**Engineer answers.** The one exception is the session recording an answer it asked the engineer for: a `/plan-review` Step 4 answer, or an after-approval addition under **Critical files** below. Append one row per answer after the ledger's last row, with the next row number, `anchors: root`, the claim the asking step gives, and the answer quoted byte for byte in the `[engineer-verified: "<quote>"]` tag. Its limits:
- Never edit or renumber an existing row, and change nothing else from `## Approach` down except an added Critical file's path.
- Send every follow-on edit the answer needs to `plan-architect`.
- An answer to an open decision `plan-architect` returned is not this exception, so re-dispatch with it as above.

`claude/.claude/agents/plan-architect.md` § "Design principles" governs how the approach is chosen; the rules below govern what the plan records. Consult `code-review`, `test-conventions`, `verify-sources`, and `ai-instruction-and-memory-files` if their domains are implicated.

**Comment-content discipline.** When a plan prescribes a comment or docstring verbatim, prescribe the durable one-line fact only — the plan's own rationale belongs in the commit message and PR body, per CLAUDE.md §Durable text.

**Name the dispatch split.** Implementation of an approved plan is
delegated to `code-writer` per phase by default (`subagent-delegation`);
the plan decides how a phase divides further, not the session that
implements it. Split a phase into more than one dispatch only when its
steps partition into non-overlapping file sets that are each specifiable
without restating the other's context — then name each dispatch's files
and verification command in **Critical files**. Sequence them whenever
one dispatch's output is the next one's input (a signature and its
callers, a schema and its consumers); parallelize only for genuinely
disjoint file sets, and note that parallel dispatches share the parent's
feature worktree — `CLAUDE.md`'s Agent Briefing bars `isolation:
worktree` for PR-bound work, and overlapping edits in one tree clobber
silently rather than conflict. Do not split when the same shared-state
background would have to be restated in every dispatch prompt: each
agent re-reads the same files in its own context and can resolve the
same open question differently, and no agent's self-review sees the
other's.

**Assumption ledger.** The Approach section carries a structured ledger — recording what was checked and what wasn't, so a later revision can be diffed against it instead of silently drifting from a fact the session already established:
- **One root problem/threat line** stating what the plan solves, followed by the **givens** it accepts — conditions the design treats as fixed that lie beyond its own reach. Each carries a one-sentence reason: another party owns it, a vendor or protocol imposes it, or dissolving the design's dependence on it needs a decision outside this plan. "The engineer decided it" is not such a reason — tag that `[engineer-verified: "<quote>"]` on its own row. A condition the plan *could* change but deliberately won't is not a given — record it in **Out of scope** with its reason. A given with no qualifying reason is an untested premise, and `plan-review` Step 4 fires on it.
- **Per mechanism:** a one-line justification anchored to `anchors: root` or `anchors: row<N>`, so completeness is a real parse, not another judgment call. This is where the over-powered-primitive check lives: if a mechanism is heavier, more privileged, or wider-scope than the task requires — a heavier abstraction, a more privileged execution context, a more complex coordination pattern, a more invasive integration — enumerate at least two lighter primitives from the source documentation/system and justify in one sentence why each fails, anchored to the row it replaces; fewer than two found means re-read the source with the specific question "what mechanisms exist that do NOT require this heavier choice?" before continuing.
- **Every material assumption gets its own row, tagged:**
  - `[verified: <source>]` — checked against code/docs this session, source citable — and prose describing a restriction is not evidence about behavior, so when the claim is what a tool or path can reach, run it and cite the result.
  - `[unverified]` — asserted, load-bearing, not checked; anything downstream inherits the flag.
  - `[engineer-verified: "<quote>"]` — the quote is the engineer's own words from this session or the literal option label they selected, verbatim or a verbatim excerpt.
    - Never quote a file the human wrote; that is `[verified: <file>]`, which carries no override protection.
    - An entry carried in a resumed-from handoff's §1.5 is not from this session, so a ledger row quoting it is `[unverified]`. On the `Ask:` line, `/plan-review` re-confirms it with the engineer.
    - The tag covers only what the quote states, read against the question it answered.
    - An option description you wrote, or an inference from options they didn't pick, goes on its own `[unverified]` row (CLAUDE.md §Working Style).
    - Never silently revise or override the quoted content from your own investigation; a contradiction pauses and asks instead.
    - Use the quoted form on every row you add or change. Bare `[engineer-verified]` tags already in committed plans remain valid; treat the whole claim of such a row as protected, as `plan-review` does.

See `plan-it/REFERENCES.md` for a worked example and the full grammar rationale.

Write the plan with these sections:

1. **Context** — problem, why now, intended outcome (lead with a one-sentence goal, then Step 2's `Ask:` line)
2. **Approach** — chosen design with rationale; note alternatives considered and why they were set aside (inline in this section, not a separate block). Lead with the concluded design in one or two plain-language sentences before the assumption ledger — the ledger is supporting detail for diffing against a later revision, not the reader's entry point.
3. **Critical files** — paths to create/modify, with **reuse opportunities** (existing functions/utilities to call rather than reimplement). When the work changes no repository file — an audit, a status assessment — write `None` plus what the deliverable is instead; that's a real result Step 7 acts on, not a gap to fill with speculative paths. Name every file the diff will touch, tests and docs included: once approved, this list is the change's file limit. A file added after approval needs the engineer's answer first. The session then adds it to the list under **Engineer answers.** above, quoting the answer in the row "`<path>` joins this plan's Critical files", or, if the engineer's answer changes the goal by Step 2's rule, on the Ask line instead. When it names at least one file, end the section with a `Projected diff:` line estimating the changed lines, additions plus deletions, across every file the diff will hold once implemented, leaving out files under `.claude/plans/`.
4. **Verification** — name the project's own documented test command scoped to the diff; reach for a whole-suite invocation only where the project documents that as the command for the case
5. **Out of scope** — always present; `None observed.` when empty

Context sits under `## Context`. Sections 2-5 sit under `## Approach`, `## Critical files`, `## Verification`, and `## Out of scope`, in that order, ending the file. Each section carries at least one non-blank line.

Effort sections are optional. Add one only after a dispatch has returned and passed `check`, above `## Approach`. It describes review surface (file count, domain spread, risk concentration), never hours or days.

## Step 6 — Hand off to /plan-review

Invoke `/plan-review` against the written plan file. It sends its findings to `plan-architect` under Step 5's **Review findings.** paragraph. Re-run it after each **Request changes** verdict, and present the plan only after a round ends **Approve** or **Approve with changes**.

**If plan mode is active:** after `/plan-review` is clean and findings are addressed, call `ExitPlanMode` to request approval. The harness shows the plan file's contents in the approval UI; do not also ask conversationally.

## Step 7 — Commit or unwind the plan, then choose where implementation runs

**If the Critical files section names at least one file:** commit the
reviewed plan to the implementation branch before implementation
begins — it makes an approved plan durable before a phase that
rewrites the working tree, and `handoff` §5 already requires it.

**If it names none:** the plan is the deliverable rather than
provenance for a change, so it isn't committed — `mv` the plan file
out of `.claude/plans/`, remove the branch and worktree created for
it, and route the narrative through the project's own tracker or
documentation tool (see that project's `CLAUDE.md`, or ask the
engineer if undocumented) — the review still counts, it just ships as
findings rather than a commit. Tell the engineer where the plan file moved,
because the path /plan-review gave no longer resolves. Stop here — the choice below is about
where implementation runs, and there is none.

**Sharing the plan.** This applies only on the branch where the plan file was committed above. Share the plan with the engineer by the plan file's own absolute path. Never open a PR, draft or ready, at plan time. When the plan adds a design document or defines a cross-team contract (a schema shape, enum, or API surface other teams or pipelines depend on), readers outside this session may need lead time, so offer to push the branch with no PR:

- Before offering, run `python3 ~/.claude/scripts/plan-push-preflight.py <repo-relative plan path>`, passing the path as one single-quoted literal word, since double quotes still expand `$(...)`. Offer only when it exits 0 and prints both `OFFER: ask` and a `PUSH_COMMAND` line. Otherwise give its `STOP_REASON` line in the reply, or the command's error if it printed none, instead of skipping the offer silently.
- Ask the engineer through `AskUserQuestion`, not a closing chat question. In the question, give every `FACT` line verbatim and in order, then the `PUSH_COMMAND` text as the last line.
- No answer means no push.
- Push only after a yes, by running the `PUSH_COMMAND` text the question showed, exactly as printed, once. A yes covers only that command.
- Autonomous shipping does not waive the question.
- After the push, run the text of its `SHARE_COMMAND` line when it printed one, and give other readers the URL that prints, not the local path.
- If the push fails or a hook denies it, report the error or denial, give no URL, and make no further push attempt.
- If `SHARE_COMMAND` fails or was not printed, say the push landed on the remote branch the question named, and report gh's error when there is one.

Then choose the session. **Continue in this one by default.** A fresh session is not free: it re-pays for context this session already holds, and that rebuild dominates its first several turns, so handing off early costs more than it saves. Run `~/.claude/hooks/nudge-handoff-near-context-cap.sh --check`, following `handoff/SKILL.md` § "Before writing: is a handoff warranted?" for how to read its result: hand off when it says the session is past its threshold. When the check can't resolve a measurement (`"status":"cannot-resolve"` or `"status":"schema-drift"`), say the estimate is unavailable, name the `reason`, and fall back to judgment: the plan boundary is itself a natural seam, weighed against how much of the plan remains.

These are a floor, not the only signal: hand off regardless when any of these apply: the engineer asked; the session is ending anyway; or a `handoff` §2 reason applies on its own terms. Do not quote the raw `session_id` into prose that may reach a commit, PR body, or plan file.

Delegating implementation to `code-writer` is a separate axis, not a tiebreaker: a subagent starts from a fresh context either way, so it neither argues for handing off nor for staying. Whichever session implements, dispatch `code-writer` per phase by default — the plan already fixed scope and approach, so `subagent-delegation`'s decision-made test is satisfied by construction. See `subagent-delegation`'s "Implementation work → `code-writer`" section for the two carve-outs.
