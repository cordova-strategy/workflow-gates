# Take the announced next step in the same message

## Context

**Goal:** the main session stops ending its turn on a message that names its next step ("I'll dispatch round 3…") without making that step's tool call.

Ask: "I think #2 could work." — the engineer chose option 2 from the session's own list of three (the session's wording for option 2: a narrow CLAUDE.md rule saying that when a message reports a finished unit and names the next step, the next step's tool call goes in the same turn), then said "run it through plan-it".

**Why now.** A main session announced "I'm starting round 3 on the fix" in a long review loop and ended its turn without the dispatch. The Stop hook `advance-past-commit-stall.sh` did not fire. It matches only final sentences that ask permission to commit, push or open a PR. Its header lists a non-question stall as a known gap. A hand-labeled scan of local session transcripts found such silent stalls rare, and found most announcement-ending turns to be legitimate waits on a dispatch already running. A Stop hook keyed on the announcement alone would therefore mostly block correct waits, so a prose rule is the chosen first step.

**Intended outcome.** One bullet under `# Main session` → `## Working Style` in `claude/.claude/CLAUDE.md`, with carve-outs for waiting on running work the step needs (a dispatch or a background command), a stated hold or irreversible-action limit, and a turn whose last act is a presentation. The plan also says how to measure whether the bullet moves the stall rate, and keeps all transcript-derived content and figures out of the public repo.

## Approach

Add one bullet to `claude/.claude/CLAUDE.md` under `# Main session` → `## Working Style`, directly after the "Walk the user through…" bullet (line 129), where the engineer chose to place it (row 7). The bullet requires a message that names the session's next step to carry that step's tool call. It lets the turn end on a named step only when an existing authority makes the step wait, or when work the session started that the step needs is still running. It defers to the rules that already govern waits instead of restating them, and its line-129 neighbor is one of them (row 4). One `_PLACEMENTS` row pins the bullet in Main session, under a one-line comment that names the record explaining why. One bullet in the groups design record names the placement as an exception to that record's tool-capability test, and one CHANGELOG entry records the change.

The placement departs from the groups record's tool-capability test (rows 9 and 10), and the engineer's placement answer settles it (row 7). The change also replaces the category-list comment at line 101 of the groups test with a one-line label (M2, row 30).

The bullet, verbatim:

```markdown
- **Take the next step you name.** A message that names your next step carries that step's tool call, since a message with no tool call ends your turn. End it there only when CLAUDE.md, the skill you are following, your dispatcher, or a hold the engineer stated makes the step wait, or work you started that the step needs is still running.
```

Alternatives weighed:
- **Agent Core § Working Style, after the blocked-stop bullet (`CLAUDE.md:83`).** The groups record's tool-capability test favors it, because a subagent holding Edit and Bash can stall the same way (rows 9 and 10). Set aside by the engineer's placement answer (row 7). What holds of the case for Main session is that a dispatched agent's final message is its return (row 11). In Agent Core the rule could read the follow-ups named there as steps to take (row 12). The cost is the subagent stall named in Out of scope.
- **No running-work clause.** Set aside: no CLAUDE.md line covers a wait on running work that is not a dispatch, so the bullet would turn a legitimate wait on a background command into a poll (row 26).
- **Naming the wait as "a background command the step needs".** Set aside: it names one mechanism, while the wait to keep turns on whether the step needs work that is still running, not on which tool started it (row 26).
- **Dropping "your dispatcher, " from the bullet.** It would save 17 bytes and match the hook reason's list exactly (row 15). Set aside: forks follow Main session and are dispatched, so a fork's closed "only when" list would lose an authority Agent Core already names (row 14).
- **The session's draft wording.** Set aside for two defects:
  - Its exception "a dispatch you already started is still running" is wider than Agent Briefing's "When pending dispatches are all that remain" (`CLAUDE.md:153`). It would excuse ending on an independent step while an unrelated dispatch runs, and it restates that rule outside its home. The adopted running-work clause adds "that the step needs", so it excuses only the step that waits on the work (row 26).
  - Its exception "the decision is the user's" admits an offer the agent made up, which the engineer's hedged-offer answer excludes (rows 5 and 6). The bullet's "CLAUDE.md" item already covers a genuine decision (row 27).
- **Naming each carve-out in the bullet** (a presentation as the last act, irreversible actions, merge, the blocked stop, pending dispatches). Set aside: each already has a CLAUDE.md home (row 4), so naming them restates those homes. Five clauses would also overrun the 11 bytes left under the cap (rows 2 and 3).
- **A one-line comment on the `_PLACEMENTS` row in place of the record bullet.** Set aside: a later CLAUDE.md editor reads the placement tests in the groups record (row 13), so the exception belongs beside the test it departs from. The plan adds the comment as well, because it sits where a failure of the row is read (row 17).
- **A second `_PLACEMENTS` row pinning the "only when" sentence.** Set aside by the session at plan review, since row 24's answer covers one pin row. Row 17 records what that row leaves unpinned.
- **A Stop hook on silent announcements**, the heavier primitive. Set aside; see Out of scope.
- **Widening the Shipping bullet's "natural stopping point" sentence.** Set aside: that bullet covers only commit, push and PR, and the hook reason that shares its wording is pinned by tests (row 15).

### Assumption ledger

**Root:** A message that names the session's next step but carries no tool call ends the turn, so the step never runs. The only backstop, `advance-past-commit-stall.sh`, fires only on a final sentence asking permission to commit, push or open a PR (`advance-past-commit-stall.sh:3-5`), and its header lists a silent stall as a known gap (`:38-39`).

**Givens:**
- G1. A turn, or a subagent's run, ends on an assistant message that carries no tool call. Reason: the Claude Code harness owns the agent loop. `CLAUDE.md:153` already instructs from the same model ("end the turn without a tool call").
- G2. Agent Core must open the file as one contiguous block, ahead of `# Main session`, that can be extracted as-is. Reason: the groups decision record owns this contract (`docs/design-decisions/global-claude-md-agent-core-and-main-session-groups.md:9`, `:13`), and changing it needs a decision outside this plan.
- G3. No transcript text, session id, project name or scan figure may enter this public repository from this work. Reason: the repo owner's redaction policy governs it (repo `CLAUDE.md` § "Redact private-project-identifying content").

**Mechanisms:**
- **M1.** Insert the bullet above as a new line after `claude/.claude/CLAUDE.md:129`. No other line in the file changes. It is the lightest primitive for the root: a prose rule with no hook or script.
  anchors: root, row1, row2, row3, row4, row5, row6, row7, row8, row14, row15, row16, row23, row26, row27, row28, row29
- **M2.** Add `("take-the-named-step", "**Take the next step you name.**", "main"),` to `_PLACEMENTS` in `claude/.claude/hooks/tests/test_global_claude_md_groups.py`, after the `no-permission-asking-on-finished-work` row (which ends at line 138), among the Main-session rows under the line-101 comment. M2 also replaces that comment with the one-line label `# Main-session-only bullets.` (row 30). The one-line comment under Critical files sits directly above the new row. It reuses the parametrized `test_pinned_bullet_sits_in_its_group` (`:282-302`), so no test function is added. It lands before M1, so the row is seen to fail first (Verification step 2).
  anchors: row7, row9, row16, row17, row24, row30
- **M3.** Add one bullet to the groups record's "Placement tests" list, after `docs/design-decisions/global-claude-md-agent-core-and-main-session-groups.md:24`, so the record names the exception instead of silently contradicting the file (text under Critical files).
  anchors: row7, row8, row9, row10, row11, row12, row13, row25
- **M4.** Add a CHANGELOG entry (text under Critical files).
  anchors: row18
- **M5.** Measure the effect privately, with no repository change (Verification step 7).
  anchors: row19, row20, row21, row22

**Rows:**
1. The global CLAUDE.md is 182 lines and 30,368 bytes. [verified: the session's `wc` run, relayed in the dispatch, and staff-sdet's `wc` re-derivation at plan review; the architect's Read confirms the line count]
2. `check-claude-md-length.sh` denies a commit only when the staged file is over 200 lines or 30,720 bytes and is also longer than the committed version. That leaves 18 lines and 352 bytes for this change. [verified: claude/.claude/hooks/check-claude-md-length.sh:6-8, :59, :123]
3. The bullet is 341 bytes with its newline: 340 characters, all ASCII, in 63 space-separated tokens. The round-1 text measured 283 bytes. The running-work clause replaces its closing period with ", or work you started that the step needs is still running.", which adds 58 bytes. The file becomes 183 lines and 30,709 bytes, 11 bytes under the cap. Without "your dispatcher, " (17 bytes) the bullet would be 324 bytes. [unverified: the 283-byte base is staff-sdet's `wc` run on the round-1 text, and the 58-byte delta is the architect's hand count, since this pass had no shell; Verification step 1 re-derives both with `wc`]
4. An independent step named while a dispatch runs still needs its tool call. `:153` applies only when pending dispatches are all that remain, and the running-work clause covers only a step that needs the running work (row 26). Each carve-out the Context names already lives in CLAUDE.md, so the bullet's "CLAUDE.md" item covers it without restating it:
   - waiting on dispatches: `:153`;
   - a presentation as the last act: `:135` and `:139`, with `:129`'s walk-through;
   - the irreversible-action limit: `:177`;
   - merge staying human-only: `:85`;
   - the blocked stop: `:83`;
   - the Shipping hold: `:179`.

   [verified: claude/.claude/CLAUDE.md at each cited line, before the change]
5. The engineer's answer on hedged offers. [engineer-verified: "Yes, a hold must be stated (Recommended)"]
6. That option's meaning, in the session's description: only a hold the engineer actually stated lets the turn end, and an offer to pause that the agent invented does not. The bullet's closed "only when" list implements this reading, and the later running-work clause is covered by row 28. [unverified: the session's own option description, not the engineer's words]
7. The engineer's answer on placement. [engineer-verified: "Main session (Recommended)"]
8. That option's meaning, in the session's description:
   - Benefit: it matches the evidence that every stall found was a main-session turn.
   - Benefit: a subagent's final message legitimately names follow-ups for its dispatcher, and Agent Core already says a dispatched agent returns its work.
   - Benefit: an Agent Core rule could push subagents to act past their brief.
   - Cost: one deviation from the groups record's placement test, which the plan must justify.
   - Effect on M2: the `_PLACEMENTS` row's group is `"main"`.

   [unverified: the session's own option description, not the engineer's words]
9. The groups record's first placement test decides by tool capability, not likelihood, and sends a prose-only rule whose trigger can arise in a subagent to Agent Core. [verified: docs/design-decisions/global-claude-md-agent-core-and-main-session-groups.md:20]
10. The trigger can arise in a subagent as a real stall, not only as a legitimate return. A subagent holding Edit and Bash, such as `code-writer`, can end its run on a message that names its own next edit and makes no call (G1), so its dispatcher receives unfinished work. Main-session placement therefore departs from row 9's test. Row 8's "every stall found was a main-session turn" is a likelihood argument, which that test sets aside. [verified: claude/.claude/agents/code-writer.md:4; record :20; G1]
11. The part of row 8's case that holds: a dispatched agent's final message is its return. Agent Core's opening line has a dispatched agent report in that return any step aimed at the user or a reviewer, a "name" step included (`:3`). Agent Core's shipping clause has it return its work rather than ship (`:85`). Naming follow-ups in the return for its dispatcher is therefore expected. [verified: claude/.claude/CLAUDE.md:3, :85; record :22]
12. In Agent Core, the rule could read that expected follow-up list as steps to take, pushing a subagent past its brief. [unverified: the session's option description (row 8) and the architect's inference; no subagent was observed doing this]
13. A later CLAUDE.md editor reads the groups record for placement, and its "Placement tests" list names individual bullets with their reasons. An exception to its first test therefore belongs in that list. [verified: record :5, :18-24]
14. Forks follow Main session and are dispatched runs, and Agent Core names "your dispatcher's own words" as a source that instructs. So "your dispatcher" is a real authority in a fork's "only when" list. For the main session the item never applies. [verified: claude/.claude/CLAUDE.md:3, :10; record :37-39]
15. The bullet's authority list reuses the hook reason's wording "CLAUDE.md, the skill you are following, … a hold the engineer stated", so the rule and the reason share one vocabulary. The bullet adds one item to that list, "your dispatcher", and the running-work clause sits outside the list. Tests pin the reason's wording. No test pins the Shipping sentence at `CLAUDE.md:176`. The Shipping sentence and the hook reason both stay untouched. [verified: claude/.claude/hooks/advance-past-commit-stall.sh:254; claude/.claude/hooks/tests/test_advance_past_commit_stall.py:1262-1264, :1325-1327; a repo grep for "natural stopping"]
16. The bullet breaks no existing check in the groups test:
   - It adds no heading, so both H2 lists stay intact.
   - `_index_of_only_line_containing` needs the M2 fragment on exactly one line. A repo grep outside plan files finds "Take the next step" on no line today.
   - No existing `_PLACEMENTS` fragment occurs in the bullet. "Walk the user through your proposed approach" stays on line 129, where the split-options test reads it.
   - The bullet sits below `# Main session`, and the Agent Core text scans read only lines above that heading, so they do not reach it.

   [verified: claude/.claude/hooks/tests/test_global_claude_md_groups.py:27-42, :52-176, :243-256, :259-279, :350-363, :393-412]
17. The pin earns its row because the placement departs from row 9's test. A later editor applying that test could move the bullet into Agent Core, and the `"main"` branch fails that move. The row joins the Main-session rows under the line-101 comment, beside the proceed-clause row, since both bar a pause on work the session can continue. The line-101 comment is replaced with a bare label (M2, row 30). The row pins placement only: an edit that widens or drops the "only when" sentence, or restores "the decision is the user's", passes every test. A clause-level row is set aside under Alternatives. The failure message at `:299-302` does not say the placement is a deliberate exception, so a comment above the row names the record that does. An editor who hits the failure is therefore not left to flip the row to `"core"`. [verified: claude/.claude/hooks/tests/test_global_claude_md_groups.py:101-138, :298-302]
18. CHANGELOG entries sit under `## [Unreleased]` → `### Changed` as a bold sentence with nested bullets, and an edit to an existing file under `claude/.claude/` is live on `git pull`. [verified: CHANGELOG.md:5-9; repo CLAUDE.md § "Working in this repo"]
19. The engineer's answer on measurement. [engineer-verified: "Private rescan, no repo change (Recommended)"]
20. That option's meaning, in the session's description: rerun the local transcript scan on sessions after the bullet lands, and report the comparison to the engineer in chat only, committing and publishing nothing from it. [unverified: the session's own option description]
21. A publishable figure needs a measurement of this repository's own corpus on one account, scoped by a command that refuses any wider corpus, with that command cited beside the figure. [verified: docs/private-project-redaction.md:97-108]
22. The local scan behind the Context filtered sessions by directory name, so it is not a command that refuses a wider corpus. Most turns it found ending on an announcement were legitimate waits on a running dispatch, which is why the bullet keeps that wait. [unverified: relayed from the session's research subagent; no figure is carried here, by design]
23. The engineer chose the session's option 2, a CLAUDE.md rule, which M1 implements. [engineer-verified: "I think #2 could work."]
24. The engineer's answer on the `_PLACEMENTS` pin row (M2), put to them at plan review because the Ask names a CLAUDE.md rule and not a test file. [engineer-verified: "Keep the pin row (Recommended)"]
25. The engineer's answer on the groups-record bullet (M3), put to them at plan review because the Ask does not name that doc. [engineer-verified: "Keep the record bullet (Recommended)"]
26. No CLAUDE.md line covers a wait on running work that is not a dispatch. `:153` names only "pending dispatches", and a case-insensitive grep of the file finds "background", "monitor" and "still running" on no line. A background command's completion reaches the session as a harness notification, the same record a finished subagent produces. `/ready-for-review` waits on one for its CI watch. Without the running-work clause, the bullet would demand a tool call while a background command the step needs is still running, which turns that wait into a poll. The clause says "that the step needs", so an independent step named while the work runs still needs its tool call (row 4). The clause only permits an end, so `:153` stays the home for when a turn waiting on dispatches ends. [verified: claude/.claude/CLAUDE.md:153 and the grep above, before the change; claude-skills/skills/ready-for-review/SKILL.md:178; claude/.claude/scripts/tests/conftest.py:889-891; claude/.claude/scripts/tests/_compaction_context_helpers.py:146-149]
27. A step gated on an answer only the user can give ("I'll do X once you pick") needs no new item in the closed list. Agent Core's options bullet makes the choice the user's when the session can write the sentence naming why it is a genuine decision (`:49`). When that sentence cannot be written, the same bullet sends the session to the sensible default (`:55`). The "CLAUDE.md" item therefore lets a genuine question make the step wait. It still excludes an offer the agent made up. An item such as "the decision is the user's" would admit that offer (row 6). An `AskUserQuestion` call does not make a message compliant by itself, because it is not the named step's tool call. A made-up question asked through it still breaks the bullet's first sentence, while a genuine one is covered through `:49`. [verified: claude/.claude/CLAUDE.md:49, :55; the bullet text above]
28. The engineer's answer on the running-work clause, put to them at plan review after round 2 flagged that it postdates their hedged-offer answer (row 5). [engineer-verified: "Keep the clause (Recommended)"]
29. The engineer's answer on the bullet's trigger, a message that "names your next step", which is wider than the session's description of option 2 (a message that reports a finished unit and names the next step). [engineer-verified: "Keep the wider trigger (Recommended)"]
30. The engineer's answer on M2's replacement of the line-101 comment, put to them after code review rounds 1 and 2 each flagged that comment's category list. The engineer was asked whether to keep the replacement or revert it, and answered in their own words. [engineer-verified: "Ask the architect."] `plan-architect` then recommended keeping the replacement, because Agent Core's "Don't restate the code" bullet makes a category list of the rows below it a restatement. The label replaces one comment line with one line, so the diff stays small. That recommendation is the architect's, not the engineer's. [verified: `claude/.claude/CLAUDE.md:116` states the "Don't restate the code" bullet] [unverified: the architect's recommendation is relayed, so confirm it settles the question]

## Critical files

Line numbers below cite each file before the change.

- `claude/.claude/CLAUDE.md`: insert the M1 bullet as a new line after line 129, so it becomes line 130.
- `claude/.claude/hooks/tests/test_global_claude_md_groups.py`, two edits and one reuse:
  - Replace the one-line comment at line 101 with `    # Main-session-only bullets.`.
  - Reuse `test_pinned_bullet_sits_in_its_group` (`:282-302`) and `_index_of_only_line_containing` (`:243-256`) as they stand.
  - Insert the two lines in the block below after line 138, before the bullet lands (M2).

```python
    # take-the-named-step stays in Main session; global-claude-md-agent-core-and-main-session-groups.md says why.
    ("take-the-named-step", "**Take the next step you name.**", "main"),
```

- `docs/design-decisions/global-claude-md-agent-core-and-main-session-groups.md`: insert this bullet after line 24, the last "Placement tests" bullet:

```markdown
- The "Take the next step you name" bullet sits in Main session, an exception to the tool-capability test above. A dispatched agent's final message is its return, where naming follow-ups for its dispatcher is expected, so in Agent Core the rule could push a subagent past its brief. A non-fork subagent that names its own next step and ends its run without taking it is not covered.
```

- `CHANGELOG.md`: insert this entry as the first bullet under `## [Unreleased]` → `### Changed`, before line 9:

```markdown
- **A new Main session rule in the global `CLAUDE.md` has the main session and forks make the tool call for a next step they name, in the same message.** A message with no tool call ends the turn, so a step it only names never runs.
  - The turn may end on a named step only when `CLAUDE.md`, the skill being followed, a fork's dispatcher, or a hold the engineer stated makes the step wait, or when work the session started that the step needs is still running. An offer to pause that the agent makes up does not count.
  - Other dispatched agents do not follow it.
  - The change is live on `git pull`.
```

One `code-writer` dispatch covers all four files, since each carries the bullet's text, its fragment, or its name. It lands M2 before M1, so Verification step 2 sees the row fail first.

Projected diff: 10 lines (9 additions, 1 deletion).

## Verification

1. `wc -l -c claude/.claude/CLAUDE.md` reports 183 lines and at most 30,720 bytes, which is 30,709 if rows 1 and 3 hold. `sed -n '130p' claude/.claude/CLAUDE.md | wc -c` reports at most 352, which is 341 if row 3's count holds. If either is over, shorten the new bullet and report it; do not trim another bullet.
2. The `code-writer` dispatch adds the M2 lines before it inserts the bullet, then runs `scripts/venv-run.sh pytest 'claude/.claude/hooks/tests/test_global_claude_md_groups.py::test_pinned_bullet_sits_in_its_group[take-the-named-step]'`. The run fails with the "not found on any line" message (`test_global_claude_md_groups.py:247-250`). After M1 the same command passes.
3. `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py` passes. Its selection for `claude/.claude/CLAUDE.md` (`select-tests.py:1082`) and for `docs/` (`:1076`) covers `claude/.claude/hooks/tests/` and the skills tests. That run covers the new `take-the-named-step` row, the design-decision file checks, and the global CLAUDE.md's other readers in those trees. `CHANGELOG.md` selects no tests (`:771`).
4. `scripts/venv-run.sh ruff check claude/.claude/hooks/tests/test_global_claude_md_groups.py` passes, which also holds the new comment to the 130-column limit (`pyproject.toml:2`).
5. During `/code-review`, read the final bullet against the cases below and confirm each outcome. This is a judgment read of model behavior under a prose rule, not a mechanical check, so record each case's verdict in the PR body. Line numbers cite the file before the change, and lines from 130 on shift by one after the bullet lands.
   - A named step that needs a pending dispatch's result, with nothing else left: end the turn (`CLAUDE.md:153`; the running-work clause).
   - An independent step named while a dispatch runs: tool call (row 4).
   - A named step that needs the output of a test run started with `run_in_background`, still running, with no dispatch pending: end the turn (the running-work clause; row 26).
   - An offer to pause that the agent made up ("Want me to…?"): tool call (no item in the closed list; rows 5 and 6).
   - An independent step named while that background test run is still running: tool call (the clause's "that the step needs"; row 26).
   - A step named after the background run's completion notification has arrived: tool call (nothing is still running).
   - A hold the engineer stated earlier ("wait for my go before X"), then a message naming X: end the turn (the stated-hold item; `:179`; rows 5 and 6).
   - A skill step that ends the run, such as a `plan-shape.py` stop sent to the engineer in `/plan-it`, then a message naming the step after it: end the turn (the skill item; `claude-skills/skills/plan-it/SKILL.md:81`).
   - A plan or proposal presented for approval, or a force push: end the turn (`:135`, `:139`, `:177`).
   - A closing message that names the engineer's own next step ("next you merge"): no tool call, because the bullet covers only the session's own step and merge stays human-only (`:85`).
   - A fork whose dispatch prompt says to return before step X ("do not commit; return the diff"), then a final message naming X: end the run and report X in its return (the dispatcher item; row 14).
6. `/code-review` runs, routing the CLAUDE.md change to `ai-instruction-and-memory-files` per the session's report. The commit then passes `check-claude-md-length.sh`.
7. After the engineer has pulled the merge, and outside the merge gate, the session reruns its local transcript scan and reports the result to the engineer in chat only. Nothing from it goes into a commit, this plan, the PR body or the CHANGELOG, and this plan carries no baseline figure. The engineer and the session set the exact metric and window length in chat at rescan time, within these limits:
   - **Windows:** both the baseline and the post-change window cut at the pull, and count only sessions that started after it, because exposure to the bullet begins at the pull.
   - **Stall label:** a main-session turn that ends on a named step with no tool call, where no CLAUDE.md line, skill, dispatcher or stated hold made the step wait, and no background call the step needed lacked a completion notification before the final message.
   - **Floors:** absolute counts, not a comparison of turn counts between windows, because stalls that become tool calls leave the denominator. The result is inconclusive when the baseline window holds no stall.
   - **Counter-metric:** tool calls made against a stated hold, or polls made while only dispatches or running work the next step needed remained.
   - **Expectation:** stalls are rare, so the result is likely to be inconclusive.
   - **Follow-up:** each follow-up is the engineer's call.
     - A lower stall rate with no rise in the counter-metric keeps the bullet.
     - A stall rate that does not fall reopens the Stop-hook option in Out of scope.
     - A rise in the counter-metric leads to a proposal to narrow the bullet.
     - An inconclusive result widens both windows equally once and is then reported as it stands.

## Out of scope

- **A Stop hook for silent announcements.** The Context records that most turns ending on an announcement are legitimate waits, so a hook keyed on the announcement alone would mostly block correct turns. It first needs an exclusion design for legitimate waits and asks. Verification step 7 reopens it if the stall rate does not fall.
- **Shipping's "natural stopping point" sentence (`CLAUDE.md:176`) and the hook reason (`advance-past-commit-stall.sh:254`).** `test_advance_past_commit_stall.py:1262-1264` and `:1325-1327` pin the reason, and `docs/commit-stall-block.md:24` describes it. The new bullet complements both.
- **The hook's silent-stall known-gap line (`advance-past-commit-stall.sh:38-39`) and `docs/commit-stall-block.md`.** Both describe the hook, which still does not catch a silent stall, so they stay accurate.
- **Raising `GLOBAL_CLAUDE_MD_BYTE_LIMIT`.** The bullet fits (row 3). A raise past 32,768 bytes needs a new basis (`check-claude-md-length.sh:54`).
- **Publishing any figure from the rescan.** It needs the scope in row 21, and the local scan does not meet it (row 22).
- **A non-fork subagent that ends its run on a step of its own that it named.** The engineer's placement answer keeps the rule out of Agent Core (row 7). Rows 10 to 12 give the case, and M3 names the gap in the groups record.
- **A fork's own step that its dispatcher's brief neither asks for nor holds back.** The bullet's dispatcher item covers only a dispatcher's words that make a step wait, and silence in the brief is not such words. Verification step 5 therefore has no case for it.
