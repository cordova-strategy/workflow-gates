# Retire the fix-plan pilot

## Context

Goal: remove the fix-plan pilot's skill region, pin tests and wiring, so the `code-review` skill stops carrying a not-adopted experiment, and so the contradiction-route change that follows edits one fewer region.

Ask: "I wonder if you just clean up the pilots and remove the related code there, and it might simplify things." Asked whether to retire the fix-plan pilot, the engineer answered: "Yeah, we can retire the fixed plan pilot."

Why now: `docs/design-decisions/architect-fix-plan-pilot-not-adopted.md` records the pilot as not adopted and says its code "stays dormant behind that key until a separate decision removes it". The engineer's answer above is that decision. Retiring the region also frees about 8 lines of the skill's 550-line cap, which later changes to `code-review/SKILL.md` need.

Scope (the session's own reading of the engineer's answer, not their words):
- Retire the fix-plan pilot only, following the revert contract in `docs/design-decisions/architect-authored-fix-plan-pilot.md`.
- Keep the `architect_fix_plan_pilot` row in `config-keys.psv`, inert at `false`, because a scaffolded config that holds the key warns on an unrecognized one.
- Keep both decision records' bodies.

The disposition-challenge pilot stays. So do the contradiction-route change and the stop-logging change, which are separate PRs. Private-analysis figures stay out of every artifact: the repo is public.

## Approach

Delete the fix-plan pilot's `DISPOSITION_RULE` region and its pin class. Move the class's three assertions that still guard live citations into surviving classes, beside the text that cites each referent. Drop the disposition-challenge region's two references to a fix-plan table. Then mark the key inert wherever the repo describes it, following the pilot record's revert contract.

The schema row, the per-key tests, `routing_guard.py` and its tests all stay untouched. The row is required, not only a way to avoid the unrecognized-key warning. The session config-keys recorder logs only schema keys, and the routing guard refuses a branch whose log row lacks this key (rows 20, 21).

Alternatives set aside:
- **Leave the challenge region's two fix-plan clauses as dead text.** That would leave stale text in a skill every stow consumer loads, against the contract's "every sentence" clause (row 4). Editing them changes no fixture verdict, because the challenge record says no fixture case decides either clause (row 15). The edit still forces a fixture re-run before any enable (row 16).
- **Delete the schema row too.** Every read of a config that still holds the row would warn (row 5). The recorder would also stop logging the key, and the routing guard would then refuse every new branch as key-state-unknown (rows 20, 21).
- **Remove `routing_guard.py`'s read of the key.** It would change the shape of stored capture records and touch about 20 fixture sites. Records captured while the key could be on still carry its state (row 12).
- **Delete the class's referent assertions along with the class.** Three of them guard referents that live text still cites, so deleting them would leave those citations unguarded. One of the three is the round-cap region's own position-dependent reference, which that region's tripwire class exists to name (row 23).
- **Keep the class's whole-text pin, placement and schema-wiring tests.** The whole-text pin and the schema-wiring test check only the pilot region. The placement test is keyed to the deleted region's start anchor, and M12 carries its remaining ordering over (row 22).
- **A new decision record for the removal.** It would restate the not-adopted record's reasons. The contract names a status line and a CHANGELOG entry as the removal's record (row 4).
- **Edit the decision records' bodies in place.** The Context keeps both fix-plan records' bodies, and the challenge record's affected sentences are pre-registration text (G3). Status lines under each provenance line follow an existing form (row 18).

The footprint is longer than the revert contract's list (`docs/design-decisions/architect-authored-fix-plan-pilot.md`, "Revert contract" paragraph), and Critical files names every site. The contract's own list:
- the region;
- its pin constants and test class;
- its anchor-set entry;
- the audit's Call site and Fail-direction bullet;
- one status line;
- one CHANGELOG entry.

Additions to the contract and departures from it:
1. Status lines go on four more records besides the pilot record. The not-adopted record gets one because this change is the "separate decision" its line 5 says will remove the code (row 3). The other three each hold a sentence that describes the pilot as live, with no condition on the key and no citation of the pilot record (row 24):
   - the challenge record, line 57, plus its revert-contract clause from row 17;
   - `dispatch-prompts-mark-relayed-text-by-source.md`, line 24;
   - `round-cap-consult-rearm.md`, line 127.
2. The challenge region's two clauses and their pin change. The contract (2026-10-08) predates the challenge pilot (2026-10-29), so it could not name them.
3. Three referent assertions move out of the deleted class into surviving classes (M12).
4. Several small edits follow the contract's "every sentence" clause, and none of them changes a test body:
   - the disposition-rules module docstring and its unused imports;
   - the `test_skills.py` call-site comment;
   - the three `TestArchitectFixPlanPilotGate` docstrings that call the key a live pilot.
5. "Edit every sentence that still describes the pilot as live" is read as meaning status lines, never body edits, on dated decision records. Apart from the not-adopted record, a record gets a status line only when a sentence in it is neither conditioned on the key nor citing the pilot record. Item 1 lists the three that fail that test. Every other dated record, the CHANGELOG's earlier entry and committed plans stay untouched as preserved records (`CLAUDE.md` Scope discipline, Axis 3).
6. The contract's "Set the key `false` on any account that enabled it" becomes a verification check and an explicit engineer action, not a code change.

**Root:** `code-review/SKILL.md` ships every stow consumer a region for a pilot that was not adopted, plus pin tests and wiring around it. The region holds 8 of the file's 546 lines, against a 550-line cap whose headroom later changes to the file need. `anchors` below resolve against this line as `root`.

**Givens:**
- **G1:** everything under `claude/**` and `claude-skills/**` goes live for every stow consumer on `git pull`. The stow distribution model imposes this (`CLAUDE.md` "Working in this repo").
- **G2:** any account's scaffolded `claude-config.toml` may already hold an `architect_fix_plan_pilot` row. Each stow consumer owns that file, and this repo cannot edit it.
- **G3:** the challenge pilot's pre-registration, meaning its "Changes after enabling" rule and its Known gaps, is fixed text. Changing it needs a decision outside this plan, because the challenge pilot is out of scope here.

**Assumption rows:**
1. Retire the fix-plan pilot now. `[engineer-verified: "Yeah, we can retire the fixed plan pilot."]`
2. The session reads the engineer's two answers as retiring the fix-plan pilot only, with the disposition-challenge pilot still running. `[unverified]`
3. The not-adopted record keeps the code dormant "until a separate decision removes it". Row 1 is that decision. `[verified: docs/design-decisions/architect-fix-plan-pilot-not-adopted.md:5]`
4. The revert contract says:
   - delete the region, its pin constants, its test class and its anchor-set entry;
   - keep `test_every_config_get_key_named_in_a_skill_is_in_the_config_schema`;
   - set the audit's Call site to none;
   - keep the key row inert at `false`, along with the `test_config_py.py` pins and `TestArchitectFixPlanPilotGate`;
   - edit every sentence that still describes the pilot as live, the audit's Fail-direction bullet included;
   - add a status line under the record's provenance line saying the key is inert;
   - add a new CHANGELOG entry.
   `[verified: docs/design-decisions/architect-authored-fix-plan-pilot.md:294-314]`
5. A config row whose key has no `config-keys.psv` row makes `_config.sh` warn "skipping line for unrecognized key" on every read. `[verified: claude/.claude/hooks/_config.sh:327,377]`
6. The pilot's skill text occupies `claude-skills/skills/code-review/SKILL.md` lines 396-403, from the start anchor through the blank line after the inline end anchor. Two more clauses sit in the disposition-challenge region, at lines 426 and 428. Nothing else in the corpus names the pilot, its key or its `fix-plan:` prefix, except the hits listed under Out of scope. `[verified: case-insensitive Grep for fix-plan|fix_plan|fix plan across the worktree's non-hidden tree]` Direct Greps also covered `.claude/skills/code-review-claude-config/SKILL.md` and `claude/.claude/agents`. `.claude/rules/` was not grepped reliably, so the Verification grep covers it. A local eval case file may still name the anchor, because `evals/run_skill_evals.py:888-901` raises on a missing `DISPOSITION_RULE:<name>` anchor and no such file is committed. `[verified: evals/run_skill_evals.py:888-901]`
7. `code-review/SKILL.md` is 546 lines. Its cap is 550 (`claude/.claude/hooks/check-skill-length.sh:134`), and the deletion brings it to 538. `[verified: SKILL.md read through line 546; check-skill-length.sh:134]`
8. In `test_code_review_disposition_rules.py`, `re`, `config_schema`, `_CODE_REVIEW_HEAVIER_MECHANISM_RULE_OPENING` and `_CODE_REVIEW_INVALID_DEFER_HEADING` are used only by the deleted class. `_CODE_REVIEW_DEFER_CRITERIA_HEADING` was used only by the deleted class before M12, and it stays imported for the new ordering test. The three heading and opening constants stay defined in `_skill_md_helpers.py:528-530`, because `test_code_review_challenge_and_round_cap.py` imports them at lines 9-12 and uses them at 197-227. `[verified: Grep of both test files and the helpers]`
9. `TestArchitectDispositionChallengePilotGate` subclasses `TestArchitectFixPlanPilotGate`, so the base class also carries the challenge key's exit-code tests. `[verified: claude/.claude/scripts/tests/test_config_get.py:182]`
10. Every schema key needs three things: a `docs/config-file.md` table row, a backticked `###` section in the audit, and a docs-anchor path that exists. So the audit section, the table row and the pilot record all stay. `[verified: claude/.claude/hooks/tests/test_doc_counts.py:785-829]`
11. `docs/config-file.md` mentions the key twice, at lines 79 and 185. Both describe the schema row and its scaffold, which stay true, so the file needs no edit. `[verified: docs/config-file.md:79,182-188]`
12. No ledger, parser or reader code special-cases the `fix-plan:` rationale prefix. Historic ledger rows that carry it stay as plain rationale text, because nothing parses it. `transcript_analysis/routing_guard.py` reads only the key's logged state, from the session config-keys log, and stores it in capture records. `[verified: Grep of claude/.claude/scripts; routing_guard.py:124-128,384,1262,1744-1745]`
13. While the challenge key is on, a PR that changes the challenge region is a recorded disable, with a four-step engineer procedure before merge. `[verified: docs/design-decisions/architect-disposition-challenge-pilot.md:152-163]`
14. The challenge key is off on every account that ran it. The record describes the key as off before the second window's enable (line 236), but key state is per account and was not read. If it is on, the merge cost in M11 follows. `[unverified]`
15. No challenge fixture case decides the two clauses M2 removes. This rests on the record's own Known-gaps text. The fixture set itself lives outside the repo and was not read. `[verified: docs/design-decisions/architect-disposition-challenge-pilot.md:392-397]`
16. The challenge region is one of the challenge pilot's four fixture spans. Before any enable, a session compares those spans at the commit the recorded fixture table ran against with the live text. Any difference makes it re-run the whole set and hand over a new table. So with the key off, this edit forces a re-run before any enable whose table predates the merge. `[verified: docs/design-decisions/architect-disposition-challenge-pilot.md:152-156,320]` Whether such a table already exists is private to the engineer. `[unverified]`
17. The challenge record's revert contract says to "return the generic config-get test's comment to one pilot region". After this change, that comment already names only the challenge region. Following the clause on a later challenge revert would therefore leave the comment naming a region that no longer exists. The challenge record's status line says so. `[verified: docs/design-decisions/architect-disposition-challenge-pilot.md:431; claude-skills/skills/tests/test_skills.py:920-923]`
18. `**Superseded in part (<date>):**` with no link is an existing status-line form. `[verified: docs/design-decisions/autonomous-shipping-state-in-hook-context.md:5; docs/design-decisions/ready-for-review-base-drift.md:5,7]`
19. A `SKILL.md` change needs `/skill-review`, and `require-skill-review.sh` hook-enforces it at commit. A `config-keys.psv` change routes to `claude-hook-review`, and a plugin-directory change to `plugin-semver`. This diff touches neither. `[verified: .claude/rules/review-pipeline-dispatch.md]`
20. The session config-keys recorder logs exactly the keys `config-keys.psv` lists. Deleting the row would drop the key from every new log row. `[verified: claude/.claude/hooks/record-session-config-keys.sh:59,69]`
21. The routing guard reads `architect_fix_plan_pilot` from each logged row. `[verified: claude/.claude/scripts/transcript_analysis/routing_guard.py:897-905,915-934,1186-1188,1744-1785]`
   - A row that lacks the key makes the branch's state unknown, and capture refuses such a branch.
   - A routing-on arm whose rows disagree on the key's state does not run.
   - A routing-off row whose state differs from the on arm does not run either.
   - An account still at `true` after it pulls this change logs `true`, which the guard labels `on`. The pilot no longer runs. Its earlier branches also carry the label `on`, and the pilot did run then.
   - Against arms labeled `off`, that leftover gives `_REASON_OFF_PILOT_DIFFERS` and the guard does not run.
   - The guard compares state labels only, within one account. A sample that straddles the pull, with every branch labeled `on`, therefore passes with no pilot-state NOT-RUN reason, though the branches behaved differently. The arm-size, too-few-on and no-growth reasons still apply. `[verified: routing_guard.py:1744-1745,1777-1785,1795-1804]`
   - Flipping `true` to `false` has its own effect. A routing-on branch worked while the fix-plan key's label was `on` then differs from post-flip records, which gives `_REASON_MIXED_PILOTS` or `_REASON_OFF_PILOT_DIFFERS`, and the guard does not run (`routing_guard.py:1744-1815`).
   - A branch whose rounds span the flip and a new SessionStart row is refused at capture as `key-state-mixed` (`routing_guard.py:1190-1191`).
   - The recorder logs only at SessionStart, so a session started before the flip logs `true` for rounds after it, while the gate reads `false` (`docs/session-config-keys-log.md:50-51`).
   - After this merge an `on` label no longer tracks behavior, and an `off` label does.
   - The recorder reads the key through `_config_value` on every SessionStart. A failed read logs `unreadable`, which the guard turns into key-state-unknown (`routing_guard.py:897-905`).
22. `TestCodeReviewFixPlanPilotRegionPin` holds four tests. Two of them check only the pilot region: the whole-text pin and the schema-wiring test. The placement test asserts `contradiction_end < pilot_start < defer_criteria`, so it also ordered the contradiction-route region before the `**DEFER criteria (closed list).**` heading. No other test orders them. No live citation depends on where the contradiction-route region sits relative to that heading. The region's "directly above" names the heavier-mechanism region. Its "below" citations name the enforcement-invariant rule, which is the defer-invariant region (the `code-review-defer-invariant` anchors in SKILL.md). M12 carries the heading ordering over and adds the ordering before the defer-invariant region that the "below" citations need. The fourth, the cited-referents test, checks referents in other regions. `[verified: claude-skills/skills/tests/test_code_review_disposition_rules.py:358-461]`
23. Fate of the cited-referents test's four referents. `[verified: Grep of claude-skills/skills/tests for each clause; claude-skills/skills/code-review/SKILL.md:323-334,374-382,388,400]`
   - The heavier-mechanism region's opening stays pinned at `test_code_review_challenge_and_round_cap.py:224-227`.
   - The round-cap region's first-bullet check moves. Outside that region, only the pilot cites "the round-cap consult's first verdict" (`SKILL.md:400`). But the region's own second-noise stop still says "*Re-plan*, as the first verdict does." (`SKILL.md:329`), which depends on bullet order. The region has no whole-text pin, and `TestRoundCapSecondNoiseVerdictStop` says "each load-bearing clause is named here" (`test_code_review_challenge_and_round_cap.py:354-355`).
   - The `**Rejected` bullet is pinned nowhere else, and live text still cites it: the enforcement-invariant consult-stop sentence (`SKILL.md:382`) names the Rejected outcome.
   - The sentence "A disagreement between the orchestrator and the returned recommendation is a blocking stop-and-ask to the human" is pinned nowhere else either. The contradiction route still cites it (`SKILL.md:388`): its "disagreement stop-and-ask follow the heavier-mechanism rule".
   - A fifth group, the `pilot_end < invalid_defer_heading` ordering, is dropped. It depends on the pilot's own position, and the heading's existence stays pinned at `test_code_review_challenge_and_round_cap.py:197-205`.
24. The other dated records that mention the pilot, judged by addition 5's test:
   - `dispatch-prompts-mark-relayed-text-by-source.md:24` lists "fix-plan pilot" among `/code-review`'s current `plan-architect` consults, with no condition and no citation. It fails the test.
   - `round-cap-consult-rearm.md:127` defines a narrow consult as one of three routes, "or the fix-plan pilot", with no citation in that sentence. It fails the test.
   - These pass:
     - `round-cap-consult-rearm.md:103` is conditioned ("with [the fix-plan pilot] on") and cites the record.
     - `dispatch-prompts-mark-relayed-text-by-source.md:58` cites the pilot record.
     - `cumulative-review-exempts-no-finding-class.md:12` cites the pilot record.
     - `review-orchestrator-routing-gate.md:80` states a key-state sample rule, which the routing guard still applies (row 21).
   `[verified: Reads of dispatch-prompts-mark-relayed-text-by-source.md:1-62 and round-cap-consult-rearm.md:1-8,98-129; Grep lines for the other two]`
25. A later PR on another branch rewrites the challenge region again. So the fixture re-run this change forces (row 16) matters only if the challenge pilot's next enable comes before that PR merges. `[unverified]`: the dispatching session relayed this from a review, and no plan for that PR was read.

**Mechanisms:**
- **M1: delete the region.** Remove `code-review/SKILL.md` lines 396-403. This is a pure deletion and adds no primitive. `anchors: row1, row4, row6, row7`
- **M2: reword the two challenge clauses and their pin.** Make the same two substitutions in the region and in `_PINNED_DISPOSITION_CHALLENGE_CLAUSE`. `anchors: row6, row13, row14, row15, row16`
  - After the edit, the region's first paragraph ends: "A `/review-pr` pass is one run under that skill's standing override to report findings and change nothing. This rule runs after the contradiction route's carries and settled-site stops, and the round's heavier-mechanism consults and any `code-writer` dispatch wait for its result."
  - Its second paragraph opens: "A row is the orchestrator's own unless the human decided it, it is a carry, or it is on the contradiction route. An ADDRESS row the heavier-mechanism rule routes to a consult is the orchestrator's own."
  - Every other sentence of the region stays as it is.
  - Rows 13 and 16 give the merge consequences. Verification states the PR-body disclosure.
- **M3: delete the pin class.** `anchors: row4, row8, row22`
  - Delete the anchor constant, `_PINNED_FIX_PLAN_PILOT_CLAUSE` and all four tests of `TestCodeReviewFixPlanPilotRegionPin`, after M12 has moved the three live referent assertions.
  - Delete the four imports only that class uses (`re`, `config_schema`, `_CODE_REVIEW_HEAVIER_MECHANISM_RULE_OPENING` and `_CODE_REVIEW_INVALID_DEFER_HEADING`), keep `_CODE_REVIEW_DEFER_CRITERIA_HEADING` for M12's ordering test, and trim the module docstring.
  - The whole-text pin and the schema-wiring test go because they check only the pilot region. The placement test goes because it is keyed to the pilot region's start anchor, and M12 moves its remaining ordering. `test_every_config_get_key_named_in_a_skill_is_in_the_config_schema` still covers the call sites that remain.
- **M4: drop the anchor-set entry.** Remove it and reword the "two pilot regions" comment to name the one that remains. `minimum_call_sites` stays 2, which pr-description and transcript-analysis meet without any pilot region. `anchors: row4, row17`
- **M5: rewrite the audit section.** Rewrite the Call-site bullet to say no skill gates on the key, and rewrite the Fail-direction bullet to name both the no-row notice on an unresolvable config dir and the `unreadable` row on a failed key read. The section heading and the schema-describing bullets stay. `anchors: row4, row10, row12`
- **M6: reword the `TestArchitectFixPlanPilotGate` docstrings that call the key a pilot.** No test body changes. `anchors: row4, row9`
- **M7: add status lines.** Add one status line under the provenance line of each of these five records, and change no body:
  - the pilot record;
  - the not-adopted record;
  - the challenge record;
  - `dispatch-prompts-mark-relayed-text-by-source.md`;
  - `round-cap-consult-rearm.md`.

  The pilot record's line also says that reverting this change restores the pilot, because the schema row is never removed. The record's preserved sentence "Reverting the merge commit is not the rollback" holds for the change that added the key, not for this one. Two lighter options were checked and fail. Editing no records leaves not-adopted line 5 false and misses the contract (row 4). A CHANGELOG-only note is a record a reader of the decision file never sees. `anchors: row3, row4, row15, row17, row18, row24`
- **M8: add a CHANGELOG `### Removed` entry.** `anchors: row4`
- **M9: keep the rest untouched.** That covers the schema row, the per-key tests, `docs/config-file.md`, `routing_guard.py` and its tests and helpers. The schema row is required by the recorder and the routing guard, not only kept to avoid the warning. `anchors: row5, row9, row10, row11, row12, row20, row21`
- **M10: one `code-writer` dispatch for the whole diff, in red-phase order.** The dispatch prompt tells the writer to edit `_PINNED_DISPOSITION_CHALLENGE_CLAUSE` first and see `test_region_matches_pin` fail before editing `SKILL.md`. It also tells the writer to prove each moved check can fail, with one throwaway `SKILL.md` mutation per check, reverted before staging: swap the first two round-cap verdict bullets, rename `**Rejected`, reword the disagreement sentence, and move the contradiction-route region below the DEFER criteria heading. The return reports that this was done. The region deletion, the challenge-clause edit, their pins and the referent move must land together. Every pin is an exact-equality test that fails if the skill and its pin diverge, and the moved assertions must exist before the class goes. The docs and docstring edits rest on the same keep-list and contract reading. Splitting would restate that shared context in each prompt, which `plan-it` Step 5 "Name the dispatch split" says not to do. `anchors: root`
- **M11: key-state check, PR-body disclosure and an engineer action.** `anchors: row4, row13, row14, row16, row21, row25`
  - The session reads both keys on its own account. It cannot read other accounts. Verification states what the PR body then discloses, once.
  - Merge order: this PR merges before the later PR that rewrites the challenge region, and that PR rebases onto the edited region and pin. Reverting this PR applies cleanly only while nothing later has edited the challenge region, its pin constant, `_EXPECTED_DISPOSITION_RULE_ANCHORS` or the CHANGELOG `### Removed` first bullet.
- **M12: move the three live referent assertions.** Each goes beside the text that cites its referent. `anchors: row23`
  - The disagreement-stop sentence moves into a new test on `TestCodeReviewContradictionRouteRegionPin`, the region that cites it.
  - The `**Rejected` bullet becomes a second assertion in `TestCodeReviewDeferInvariantRegionPin.test_enforcement_invariant_finding_ends_unfixing_consult_returns_in_human_stop`, whose pinned sentence names that outcome.
  - The round-cap first-bullet check moves into `TestRoundCapSecondNoiseVerdictStop`, whose region holds the "as the first verdict does" reference.
  - The ordering the deleted placement test also checked is kept: `TestCodeReviewContradictionRouteRegionPin` gains `test_region_sits_between_new_primitive_route_and_defer_criteria`, asserting the new-primitive-route end anchor precedes the contradiction-route start anchor, and the contradiction-route end anchor precedes both the `**DEFER criteria (closed list).**` heading and the defer-invariant start anchor.

## Critical files

One `code-writer` dispatch covers every file below (M10). Its verification is `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py`, plus the `ruff` and `git grep` commands under Verification.

- `claude-skills/skills/code-review/SKILL.md`:
  - Delete lines 396-403, from `<!-- DISPOSITION_RULE:code-review-fix-plan-pilot start -->` through the blank line after the inline end anchor. One blank line then separates the contradiction region's end anchor from `**DEFER criteria (closed list).**`.
  - In the challenge region, replace `settled-site stops and any valid fix-plan table, and the round's` with `settled-site stops, and the round's`.
  - Replace `unless a valid fix-plan table or the human decided it,` with `unless the human decided it,`.
- `claude-skills/skills/tests/test_code_review_disposition_rules.py`:
  - Delete lines 288-461, the two blank lines before `_CODE_REVIEW_FIX_PLAN_PILOT_ANCHOR` through the end of `TestCodeReviewFixPlanPilotRegionPin`. The file then ends after line 287 with one newline.
  - Delete `import re`, the two-line `pythonpath` comment, `from _config import schema as config_schema`, and the `_CODE_REVIEW_HEAVIER_MECHANISM_RULE_OPENING` and `_CODE_REVIEW_INVALID_DEFER_HEADING` import names. Keep `_CODE_REVIEW_DEFER_CRITERIA_HEADING`, which the new ordering test uses. Keep one blank line after `from __future__ import annotations`.
  - Change the module docstring to `"""Pins on code-review's clean definition and its contradiction-route, defer-invariant and new-primitive rules."""`.
  - Add `test_cited_disagreement_stop_still_exists` to `TestCodeReviewContradictionRouteRegionPin`:
    - Its docstring is `"""The region defers its disagreement stop-and-ask to the heavier-mechanism rule, which must still state it."""`.
    - It asserts that `"A disagreement between the orchestrator and the returned recommendation is a blocking stop-and-ask to the human"` is in `_normalized_anchor_text(skill_md_path, _CODE_REVIEW_NEW_PRIMITIVE_ROUTE_ANCHOR)`.
    - Its failure message names the region and the clause.
  - Add `test_region_sits_between_new_primitive_route_and_defer_criteria` to `TestCodeReviewContradictionRouteRegionPin`, with the docstring `"""The region sits after the heavier-mechanism region it cites as 'directly above', and before both the DEFER criteria heading and the defer-invariant region, which its 'below' citations name as the enforcement-invariant rule."""`, wrapped across three lines in the staged test. It asserts three orderings: the new-primitive-route end anchor precedes the contradiction-route start anchor, the contradiction-route end anchor precedes `_CODE_REVIEW_DEFER_CRITERIA_HEADING`, and the contradiction-route end anchor precedes the defer-invariant start anchor. Its `-1 not in offsets` control also covers the defer-invariant start anchor. The test needs `_CODE_REVIEW_DEFER_CRITERIA_HEADING` kept in the import list, so delete only the other imports named above.
  - In `test_enforcement_invariant_finding_ends_unfixing_consult_returns_in_human_stop`, also assert that `"**Rejected"` is in the same `heavier_mechanism_text`, so the outcome the pinned sentence names still exists. Extend that test's docstring to say it also checks the bullet exists.
  - Extend `TestCodeReviewContradictionRouteRegionPin`'s class docstring with a closing paragraph: `It also checks the referent and the ordering the region cites. The heavier-mechanism rule must still state its disagreement stop-and-ask, and the region must sit after that rule and before both the DEFER criteria heading and the defer-invariant region.`
  - Extend `TestCodeReviewDeferInvariantRegionPin`'s class docstring, in the bullet on the new-primitive-route region and `_ENFORCEMENT_INVARIANT_CONSULT_STOP_SENTENCE`, with `The region must also keep the `**Rejected` outcome bullet the sentence names.`
- `claude-skills/skills/tests/test_code_review_challenge_and_round_cap.py`: in `_PINNED_DISPOSITION_CHALLENGE_CLAUSE`, near lines 48-52, apply the same two substitutions as `SKILL.md`. The pinned text then reads as M2 quotes. Re-wrap the string literals freely, because the pin compares whitespace-collapsed text.
  - Add `test_first_verdict_is_the_re_plan_verdict` to `TestRoundCapSecondNoiseVerdictStop`, after `test_region_carries_clause`. Its docstring is `"""The second-noise stop's *Re-plan* option points at the first verdict by position."""`. Its body moves the deleted check unchanged onto `self._region_text()`:
    - find the first `"- **"`;
    - assert that it exists and that the text after it starts with `"Foundation is wrong"`;
    - use a failure message naming the re-plan verdict.
- `claude-skills/skills/tests/test_skills.py`:
  - Delete the `("code-review", "code-review-fix-plan-pilot"),` line, near line 706.
  - Replace the three comment lines near 921-923 with `# The disposition-challenge pilot region adds one more; the floor excludes it so`, `# removing that region leaves this test green. Removing or redirecting it fails` and `# test_disposition_rule_anchors_present and its pin test.`
  - `minimum_call_sites = 2` stays.
- `claude/.claude/scripts/tests/test_config_get.py`:
  - Change the `TestArchitectFixPlanPilotGate` docstring to `"""Pin config-get.sh's exit-code contract against architect_fix_plan_pilot's real schema row, which no skill reads. The row stays at false so a scaffolded config holding it reads without a warning, and because the session config-keys recorder and the routing guard read it."""`, wrapped across lines under the 130-column ruff limit. Wrap any other new string over 130 columns the same way.
  - In the per-account test's docstring, change `The pilot is per-account: a home-level file must not enable it` to `The key is per-account: a home-level file must not turn it on`.
  - In the relative-dir test's docstring, change `on the pilot key's real row` to `on the key's real row`, and `would enable the pilot on a mis-set environment` to `would read as on in a mis-set environment`.
  - No test body, class name or `_KEY` changes.
- `claude/.claude/hooks/tests/config-schema-audit.md`, in the `architect_fix_plan_pilot` section:
  - Change the Call-site bullet to `- Call site: none. No skill gates on the key. The session config-keys recorder logs its state, and `transcript_analysis/routing_guard.py` reads that logged state.`
  - Change the Fail-direction bullet to `- Fail direction on resolution failure: no behavior changes. When the config dir cannot resolve, `record-session-config-keys.sh` writes no row and prints its no-row notice. When one key's read fails, the row carries `unreadable`. Either way the routing guard treats the key's state as unknown and refuses the branch.`
  - The heading and the Resolution and Legacy bullets stay.
- `docs/design-decisions/architect-authored-fix-plan-pilot.md`: directly under `*2026-10-08.*`, above the existing supersession lines, add `**Superseded in part (<date>):** the pilot's `code-review` region, its pin tests and its anchor-set entry are removed under the "Revert contract" paragraph below. `architect_fix_plan_pilot` is inert: no skill reads it, and its schema row stays at `false`. `git log -S 'DISPOSITION_RULE:code-review-fix-plan-pilot' -- claude-skills/skills/code-review/SKILL.md` lists the commits that added and removed the region.` Leave the body unchanged. Append to that status line: `To restore the pilot, revert the removing change; the schema row was never removed, so the "Reverting the merge commit is not the rollback" sentence below describes the change that added the key.`
- `docs/design-decisions/architect-fix-plan-pilot-not-adopted.md`: directly under `*2026-10-25.*`, add `**Superseded in part (<date>):** the separate decision this record awaits removed the pilot's `code-review` region and pin tests, so its code no longer stays dormant and the region the Sources list names no longer exists. The key stays in the schema, inert at `false`.` Leave the body unchanged.
- `docs/design-decisions/architect-disposition-challenge-pilot.md`: directly under `*2026-10-29.*`, above the existing "Partially superseded" block, add `**Superseded in part (<date>):** the fix-plan pilot's region is removed, so this rule's region no longer names a fix-plan table. The "Which rows are challenged" bullet on rows after `fix-plan: fell-back`, and the two Known-gaps limbs naming a fix-plan-table row and a valid fix-plan table, describe text the region no longer holds. The generic config-get test's comment now names this pilot's region as the only one, so on revert, "Revert contract"'s "return the generic config-get test's comment to one pilot region" means dropping that comment's pilot-region sentences.` Leave the body unchanged.
- `docs/design-decisions/dispatch-prompts-mark-relayed-text-by-source.md`: directly under `*2026-10-20.*`, add `**Superseded in part (<date>):** `/code-review` no longer has a fix-plan pilot consult, so the "Sites" bullet's list of `plan-architect` consults no longer includes one.` Leave the body unchanged.
- `docs/design-decisions/round-cap-consult-rearm.md`: directly under `*2026-10-29.*`, above the existing "Partially superseded" lines, add `**Superseded in part (<date>):** `/code-review` no longer has the fix-plan pilot, so "A narrow consult restarts the count" names one narrow consult that no longer exists, and the "What a run loses" case with that pilot on can no longer arise.` Leave the body unchanged.
- `CHANGELOG.md`: as the first bullet under `### Removed` (line 746), add one bullet that is a record, not a consumer runbook. This list is the requirement, and the staged bullet must satisfy it. The plan does not copy the bullet, and the Verification section names the check. The bullet opens with a bold lead in the file's existing style and states:
  - The pilot's `DISPOSITION_RULE` region is removed from `code-review/SKILL.md`, so rounds no longer make the `config-get.sh architect_fix_plan_pilot` call.
  - No skill reads the key, and its row stays in `config-keys.psv` at `false`.
  - The row stays for three parallel reasons: the session config-keys recorder logs it, the routing guard reads that log, and a scaffolded `claude-config.toml` that holds it reads without a warning.
  - Set the key `false` on any account that enabled it. A leftover `true` changes no behavior, but the routing guard still labels it `on`.
  - Pointers to `docs/session-config-keys-log.md` (when the log shows a change), `docs/transcript-analysis.md` § "routing-guard" (the pilot-state rule for the key-off arm) and `docs/design-decisions/architect-fix-plan-pilot-not-adopted.md`.

  The bullet carries no restart, per-checkout, NOT RUN or `key-state-mixed` text. That flip procedure lives in Engineer actions (per-checkout order, restart) and in both Engineer actions and the PR body (NOT RUN, `key-state-mixed`), not in the entry.

`<date>` is the date the change is written, in `YYYY-MM-DD`.

Reuse: `_normalized_anchor_text` and the heading constants in `claude-skills/skills/tests/_skill_md_helpers.py` stay as they are, with no new helper.

Projected diff: about 300 lines across 12 files (about 215 deleted, 85 added), most of them the deleted test class.

## Verification

- `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py` passes. Its selection should include the four edited test files and `claude/.claude/hooks/tests/test_doc_counts.py`. If one is missing, that is a rule-table bug to report, not a reason to widen the run (`CLAUDE.md` Commands). The tests that bear on this change:
  - `test_disposition_rule_anchors_present`, whose exact set now lacks the pilot.
  - `TestCodeReviewDispositionChallengeRegionPin`, with its updated pin.
  - `test_every_config_get_key_named_in_a_skill_is_in_the_config_schema`, where three call sites remain against a floor of 2.
  - `TestConfigKeyDocumentationCoverage`, which checks only that the row, the audit heading and the docs anchor remain. It does not read the audit bullets M5 rewrites.
  - `TestArchitectFixPlanPilotGate` and its challenge subclass.
  - The tests that pin the retained schema row: `TestSchemaDrift.test_every_schema_key_matches_the_readers_key_name_class_and_the_three_constants_are_schema_keys` in `test_transcript_routing_guard_capture.py`, and the hand-typed pins in `test_config_py.py`.
  - The four M12 checks: the new `test_cited_disagreement_stop_still_exists`, the extended enforcement-invariant consult-stop test, the new `test_first_verdict_is_the_re_plan_verdict`, and the new `test_region_sits_between_new_primitive_route_and_defer_criteria`. The code-writer's return reports the red-phase mutations M10 requires. Each moved check failed under its mutation.
  - `test_check_skill_length.py` uses synthetic files and does not bear on this change, so `wc -l` below is the real size check.
- `scripts/venv-run.sh ruff check claude-skills/skills/tests/test_code_review_disposition_rules.py claude-skills/skills/tests/test_code_review_challenge_and_round_cap.py claude-skills/skills/tests/test_skills.py claude/.claude/scripts/tests/test_config_get.py` passes. Any leftover unused import fails here.
- `git grep -n -i -E 'fix-plan|fix_plan|fix plan' -- claude-skills/skills/code-review/SKILL.md` exits 1.
- `git grep -l -i -E 'fix-plan|fix_plan|fix plan' -- claude claude-skills docs evals plugins .claude/skills .claude/rules README.md CHANGELOG.md | sort` lists only files the Out of scope section names (kept sites and the two false positives) and the files this plan edits. Any other file is a stale mention to fix or justify.
- `wc -l claude-skills/skills/code-review/SKILL.md` prints 538.
- `git show :CHANGELOG.md`, read at the first `### Removed` bullet, carries the three pointers from the Critical files item and none of `restart`, `per checkout`, `NOT RUN` or `key-state-mixed`.
- `~/.claude/scripts/config-get.sh architect_disposition_challenge_pilot` and `~/.claude/scripts/config-get.sh architect_fix_plan_pilot`, each run as its own call. Exit 1 means off. Exit 2 or 3 means the key was not read, and the PR body then reports "unread", never "off".
- **PR body disclosures**, stated once here:
  - Each key's result on the session's account, and that the session read only its own account.
  - An exit 0 on the challenge key means the merge is a recorded disable. Before merging, the engineer follows the four steps in the challenge record's "Changes after enabling" bullet (row 13).
  - The challenge region, one of the challenge pilot's four fixture spans, changed. With the key off, any fixture table recorded before this merge no longer matches that span, so the record requires a full re-run before any enable (row 16). A later PR rewrites the region again, so the re-run matters only if the next enable comes before that PR merges (row 25).
  - Reverting this PR restores the pilot but does not undo the per-account key flips, a recorded challenge disable, a fixture re-run against the post-merge span, or routing-guard capture records written after a flip.
  - If an account pulls this change with `architect_fix_plan_pilot` still `true`, any routing-guard sample straddling that pull mixes branches where the pilot ran and branches where it was inert under one `on` label, and nothing flags it (row 21).
  - Flipping the key has its own visible effects. A routing-guard sample straddling the flip gives NOT RUN, and a branch spanning the flip and a new SessionStart row is refused at capture as `key-state-mixed`. Neither is a fault (row 21).
  - Reviewer notes, as observations left unedited and not under "Incidental edits":
    - The stale `SKILLS_TESTS_IMPORTING_CONFIG` member in `select-tests.py` over-selects only.
    - Neither the key's schema description nor its `docs/config-file.md` row says the key is inert.
    - The challenge pilot's `fix-plan:` tag-coverage exemption now matches only historic rows. Whoever writes the challenge pilot's outcome record should count a later `fix-plan:` row as a candidate.
- **Engineer actions before merge.** The session performs none of them.
  1. For each machine that enabled the fix-plan pilot, list every account config dir on it, because one pull changes the shared checkout for all of them. Then, for each account:
     - Read the captured key state first, from the `captured (` and `already captured (` lines of routing-guard capture or the capture file's `architect_fix_plan_pilot` field, which print `fix-plan-pilot=on|off`.
     - If a sampled branch carries `fix-plan-pilot=on`, the flip gives a NOT RUN until pre-flip branches leave the sample. Choose that cut, or accept the NOT RUN, before flipping.
     - Then run `~/.claude/scripts/config-get.sh architect_fix_plan_pilot` with `CLAUDE_CONFIG_DIR` set to that account's absolute config dir, or inside that account's own session, as `docs/config-file.md` § "Querying a value" describes. Exit 2 or 3 means the key was not read, so resolve it before the pull and never treat it as off.
  2. Set each `true` to `false` on every account of that machine before that machine's checkout pulls this merge, as `docs/config-file.md` § "Writing a value" describes. "Before merge" is stricter than the real bound and is the safe form. A machine whose accounts cannot all be reached holds its pull. A session started before the flip keeps logging `true` until its next SessionStart row (`/compact`, `/clear` or a restart), so restart open sessions after the flip. A NOT RUN from the guard after the flip is the correct verdict on a sample that straddles a behavior change (row 21). The revert contract asks for this flip (row 4).
  3. On those accounts, check `architect_disposition_challenge_pilot`. Any exit 0 makes the merge a recorded disable (row 13).
  4. Grep local eval case files and fixture scratch for `code-review-fix-plan-pilot`. A file naming it fails the next local eval run with an anchor-not-found error (row 6).
- `/code-review` runs on the staged diff. Because `SKILL.md` changes, `/skill-review` also runs on the skill and its pin tests, and `require-skill-review.sh` blocks the commit until it does. `config-keys.psv` and every plugin directory stay untouched, so neither `claude-hook-review` nor `plugin-semver` applies.

## Out of scope

- The contradiction-route consult-first change. It is a later PR on another branch.
- The STOP ledger row.
- Challenge-dispute resolution.
- Retiring the disposition-challenge pilot. Its region changes only by the two clauses in M2.
- The `architect_fix_plan_pilot` row in `claude/.claude/hooks/config-keys.psv`, kept inert at `false` (row 5).
- `claude/.claude/scripts/tests/test_config_py.py`: the `_PER_ACCOUNT_OPT_IN_KEYS` entry, the hand-typed default, and the line 87 comment that names the key as an example of a pinned default. That comment stays true of the inert row, and the contract keeps these pins (row 4).
- The test bodies of `TestArchitectFixPlanPilotGate` (rows 4 and 9).
- Decoupling the guard from this key with a row-strip migration. `TestSchemaDrift` already pins the guard-side coupling by asserting `set(routing_guard._STATE_KEYS) <= set(schema_key_names)`, so deleting only the schema row fails that test. No test covers the recorder's `unreadable` path for this key.
- `claude/.claude/scripts/select-tests.py`'s `SKILLS_TESTS_IMPORTING_CONFIG` entry for `test_code_review_disposition_rules.py`, which stays after that file drops its `_config` import. The stale member only over-selects, which is the safe direction, and editing the rule table would pull in its own tests.
- `docs/config-file.md`: both mentions stay true (row 11).
- `claude/.claude/scripts/transcript_analysis/routing_guard.py`, `tests/_routing_guard_helpers.py`, `tests/test_transcript_routing_guard_capture.py`, `tests/test_transcript_routing_guard_compute.py` and `tests/test_transcript_cli_bootstrap.py` all stay untouched. They read and store the key's logged state for routing-guard sample selection. That read is why the schema row must stay (rows 12, 20, 21).
- The bodies of the five decision records M7 adds status lines to:
  - the pilot record's Known gaps and Key-off check;
  - the not-adopted record's first paragraph and Sources;
  - the challenge record's lines 42, 57, 100, 110, 123, 225, 393, 397, 431 and 440;
  - `dispatch-prompts-mark-relayed-text-by-source.md:24,58`;
  - `round-cap-consult-rearm.md:103,127`.
  Their status lines cover what no longer holds (G3, rows 4, 17, 24). Line 123's tag-coverage exclusion of `fix-plan:` rationales stays correct, because it now matches only historic rows.
- Two dated decision records that mention the pilot stay untouched, with no dated note, because each sentence passes addition 5's test (row 24):
  - `docs/design-decisions/cumulative-review-exempts-no-finding-class.md:12`, which cites the pilot record;
  - `docs/design-decisions/review-orchestrator-routing-gate.md:80`, which states a key-state sample rule that still holds.
- The CHANGELOG's earlier pilot entry, near line 936, which is a record (`.claude/rules/changelog-entries.md`).
- Committed plans `.claude/plans/architect-authored-fix-plan.md` and `.claude/plans/fix-plans-gitignore.md`, which are records.
- Lowering `code-review/SKILL.md`'s 550-line override in `claude/.claude/hooks/check-skill-length.sh:134`. Nobody asked for it, and the Context keeps the freed headroom for later changes to the file.
- Grep false positives, which have nothing to do with the pilot: `text_suffix_plan` in `claude/.claude/hooks/tests/test_deny_plan_writer_off_plan_writes.py`, and "prefix planning prompt" in `claude/.claude/scripts/tests/test_transcript_analysis_branch_attribution.py`.
