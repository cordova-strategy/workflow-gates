# GH-1533: record pass kind on review-ledger rows

## Context

Make every review-ledger row say which kind of pass wrote it, so counts split by pass kind come from a script instead of a hand scan.

Ask: "GH-1533: record pass kind on review-ledger rows." The engineer added: "It lists two open choices (the value set, and whether append refuses a row with no pass kind); recommend one for each in the plan." Constraints, in the engineer's words:

- "code-review/SKILL.md is at its line cap (see GH-1351). Offset every line you add there, or put the rule in review-ledger.sh as a fail-closed check instead of prose."
- "Bump the ledger schema version and state the reader rule for older rows in docs/scripts.md."
- "Keep the unrouted contract that review-pr, ready-for-review and review-orchestrator share."
- "Out of scope: fix shape, and any new report."

**Problem.** A ledger row does not record whether its round was a staged-diff round or a cumulative pass. GH-1533 cites `docs/cost-levers-considered.md`, which records the gap as "no row field marks a pass kind". The pass kind lives in `/ready-for-review`'s disposition record, not in the ledger.

**Why now.** GH-1533 lists three places that stopped at this gap:

- Two register sections took pass kind from local findings files by hand.
- `docs/design-decisions/defect-class-exit-rule.md` § "Revisit trigger" waits on "a fresh snapshot taken after the ledger records pass kind and fix shape".
- The register did not measure clean cumulative re-passes.

Another hand scan would repeat those studies.

**Intended outcome.**

- `review-ledger.sh append` accepts and stores a pass-kind value under a bumped schema version.
- Every skill and agent that appends a row passes the value.
- `docs/scripts.md` states how a reader treats rows written before the bump.

This change records the field only; fix shape and any report that reads the field are separate work.

The issue leaves two choices to this plan, and the plan recommends one for each:

1. The value set: at least staged and cumulative, and whether a round run from `/review-pr` is its own value.
2. Whether `append` refuses a row with no pass kind or records it as undeclared.

## Approach

`review-ledger.sh append` gains a required `--pass-kind` flag with four values: `staged`, `cumulative`, `review-pr` and `other`. Each new row stores the value as `pass_kind` under `schema_version` 7. The script refuses an append without a valid value, and the rejection says what each value means. `/code-review` fixes the value once per round in Step 0.1, from the subject it already identifies, and its four append templates pass it. No other skill or agent gains an instruction. `/ready-for-review` loses one sentence fragment that turns false.

**The two open choices.**

1. **Value set: `staged`, `cumulative`, `review-pr` and `other`, with `/review-pr` as its own value (M2).** The challenge pilot already needs `/review-pr` rounds by name (row 13). Folded into `cumulative`, a `/review-pr` pass could read as an exit pass in a replay keyed on this field (row 33). `other` exists because the flag is required, and `/code-review` also runs on subjects that are none of the three (row 11).
2. **`append` refuses a row with no pass kind (M1).** This follows the model of `--round`, the lane flags and the ADDRESS `--source` (row 15). It also avoids the silent empty values that the one optional pair left behind (row 16). The cost is an exit 2 for a session that loaded `/code-review` before a pull, and for any outside caller. The rejection says what each value means, so a caller holding no Step 0.1 sentence can correct its call from the message alone (M11). Refusal also means no row at schema 7 or above is undeclared, so the reader rule has one fewer state.

The rest of the design, one fact per item:

- `pass_kind` sits right after `round` in the built row, which keeps the `"disposition":"CONSULT","rationale":"noise"` run the noise count greps for (M5).
- `pass_kind` joins the dedup include list at `review-ledger.sh:671` and stays out of the retry check's exclude list at `_review-ledger-lib.sh:884` (M4).
- `_REVIEW_LEDGER_PASS_KINDS=(staged cumulative review-pr other)`, `_review_ledger_pass_kind_hint` and `_review_ledger_validate_pass_kind VALUE` join the lib beside the CONSULT verdict helpers (M6). The hint's comment reads "Appended to every --pass-kind rejection, so the message alone tells a caller how to correct its call.", as its siblings' comments do.
- The script calls the validator right after `_review_ledger_validate_lanes` (`review-ledger.sh:496`), the last check that needs no I/O. Every existing rejection test therefore still meets its own message first, and a refused append writes nothing.
- The validator prints one stderr line per rejection (M11):
  - An empty or absent value: `review-ledger.sh: --pass-kind is required and missing. ` followed by the hint.
  - Any other value outside the four: `review-ledger.sh: --pass-kind '<value>' is not a pass kind. ` followed by the hint.
  - The hint, verbatim: `The value names what the round reviewed: cumulative in /ready-for-review step 3's cumulative pass, review-pr in a /review-pr pass, staged in any other round whose diff under review is exactly git diff --cached (a default-branch commit included), and other for any other subject. Pass one of: staged, cumulative, review-pr, other`
  - The hint builds its closing listing from the array, as `_review_ledger_consult_hint` (`_review-ledger-lib.sh:60-64`) does, and the listing ends the line.
- `--pass-kind` joins the value-flag arity list (`review-ledger.sh:383`) and the parse loop. It is not added to `EMPTY_VALUE_FLAGS`, because an empty value is already rejected as missing.
- `_LEDGER_SCHEMA_VERSION` becomes 7.
- The usage text changes in three places:
  - The synopsis names `--pass-kind staged|cumulative|review-pr|other` unbracketed beside `--round <N>`.
  - One sentence follows the `--round` sentence: `--pass-kind is required and names the kind of pass the round ran; code-review/SKILL.md's Step 0.1 says which value a round passes.`
  - The dedup field list at `:118-121` gains `pass_kind` after `round`.
- `code-review/SKILL.md:25`, the Step 0.1 paragraph that already fixes the round number, gains one sentence at its end, verbatim: "Also fix this round's pass kind, and pass `--pass-kind <kind>` to every append after this step, where `<kind>` is `cumulative` in `/ready-for-review` step 3's cumulative pass, `review-pr` in a `/review-pr` pass, `staged` in any other round whose diff under review is exactly `git diff --cached`, a default-branch commit included, and `other` for any other subject." The text after "where `<kind>` is" holds no period before the sentence's end, because the parity test reads it up to the first period (row 22).
- The four append template spans gain the flag:
  - `:27` (Step 0.1 CLEAN) gets `--pass-kind staged` after `--authoring-effort high`. Its "(this round's number)" becomes "(this round's number, and `staged` whatever invoked this skill, because the check matched the staged diff)" (M13).
  - `:458` (main CLEAN) gets `--pass-kind <kind>` after `--authoring-effort high`.
  - `:449` (per-finding) gets `--pass-kind <kind>` after `--authoring-effort high`, which keeps the `--round <N> --source` pin (row 23). Its sentence "`--round <N>` is the round number Step 0.1 tracks." becomes "`--round <N>` and `--pass-kind <kind>` take the round number and pass kind Step 0.1 tracks."
  - `:333` (CONSULT) gets `--pass-kind <kind>` after `--round <N>`. Its "where `<N>` is the round number Step 0.1 tracks" becomes "where `<N>` and `<kind>` are the round number and pass kind Step 0.1 tracks".
- `code-review/SKILL.md:460`'s retry list "an invalid `--authoring-agent`/`--authoring-effort`/`--round` value" gains `/--pass-kind`.
- `ready-for-review/SKILL.md:93`'s "The branch ledger holds each disposition canonically; this record is canonical for the pass kind and Outcome the ledger has no column for." becomes "The branch ledger holds each disposition and its pass kind canonically; this record is canonical for the Outcome the ledger has no column for." (M8).
- `docs/scripts.md` gains a **Pass kind.** bullet after the **Lanes.** bullet (ending `:191`). It states the reader rule and the retry outcome per row type, and Critical files gives its text (M4, M7, M14).
- `CHANGELOG.md` gains an `[Unreleased]` / `### Changed` entry, which Critical files gives (M7, M12).
- Two comments in `review-ledger.sh` change:
  - `:38-39` gains "and its pass kind only from rows with 7 or more".
  - `:644-645` becomes "A row written before schema 5 has no reviewers key, and one before schema 7 no pass_kind key, so neither dedups against a newer row."
- Rollback is a revert (M12). It needs no data step. The CHANGELOG entry tells the engineer who pulls the change which sessions to restart, and tells the engineer deciding a revert which sessions to restart after it.
- Nothing else changes. These stay as they are:
  - `review-pr/SKILL.md`.
  - `review-orchestrator.md`.
  - `subagent-delegation/SKILL.md`.
  - `require-review-orchestrator-routing.sh` and every `unrouted` args shape.
  - `show`, `render` and `--trend`.
  - `author_outcome.py`.
  - `_review_ledger_check_not_retired`. It already compares every field outside the per-attempt set, so it covers `pass_kind` unedited.
  - `docs/scripts.md:280`. It says the retry check compares every field outside the per-attempt set, which stays true.

**Assumption ledger.**

**Root:** a ledger row does not say which kind of review pass wrote it. A count split by pass kind therefore needs a hand scan of disposition records and findings files, not a script over the ledger.

**Givens:**

- **G1.** Rows already written sit in each stow consumer's own `<config-dir>/review-narrative-ledger/` and carry no pass kind. Reason: those files belong to each user, not to this repository, and no row ever captured the pass kind it ran under. `[verified: review-ledger.sh:345, :583-602]`
- **G2.** A running session keeps the `code-review/SKILL.md` text it loaded, while the stowed `review-ledger.sh` changes for every stow consumer on `git pull`. Reason: the harness loads skill text at invocation, and the stow install links the script in place. `[verified: CLAUDE.md § "Working in this repo", "go live on git pull"; review-ledger.sh:412-414; CHANGELOG.md:156, :164]`

**Rows:**

1. `[engineer-verified: "GH-1533: record pass kind on review-ledger rows."]` The Ask.
2. `[engineer-verified: "It lists two open choices (the value set, and whether append refuses a row with no pass kind); recommend one for each in the plan."]` The engineer delegated both choices to this plan.
3. `[engineer-verified: "code-review/SKILL.md is at its line cap (see GH-1351). Offset every line you add there, or put the rule in review-ledger.sh as a fail-closed check instead of prose."]`
4. `[engineer-verified: "Bump the ledger schema version and state the reader rule for older rows in docs/scripts.md."]`
5. `[engineer-verified: "Keep the unrouted contract that review-pr, ready-for-review and review-orchestrator share."]`
6. `[engineer-verified: "Out of scope: fix shape, and any new report."]`
7. `[engineer-verified: "Physical lines (Recommended)"]` The engineer selected this label when asked whether "line" in row 3 means a physical line, the unit `check-skill-length.sh` counts (row 30). The question stated that the plan adds zero physical lines to `code-review/SKILL.md` and grows six existing lines by about 90 words in total. The plan merges no paragraphs. The refusal itself lives in the script, the other route row 3 offers.
8. `[verified: grep of "append code-review" and "review-ledger.sh append" outside tests and plans; review-orchestrator.md:16-19; ready-for-review/SKILL.md:91; review-pr/SKILL.md:86]` Only `code-review/SKILL.md` holds append commands. `/ready-for-review`, `/review-pr` and `review-orchestrator` reach `append` only by running `/code-review`. GH-1533's Scope bullet about the `ready-for-review` body passing the value therefore has no append there to edit.
9. `[verified: code-review/SKILL.md:50, :244, :426]` `/code-review` already identifies its subject on each invocation. Step 0.6's discriminator asks whether the diff under review is "exactly `git diff --cached` on a `HEAD` that is not the default branch". The `scope:` tag names `RFR cumulative pass`, and `:426` defines a `/review-pr` pass.
10. `[verified: ready-for-review/SKILL.md:91; review-pr/SKILL.md:86; require-review-orchestrator-routing.sh:16-17; subagent-delegation/SKILL.md:215 per the exploration summary]` A cumulative pass and a `/review-pr` pass both pass args `unrouted <path>`. The HALT fallback passes `unrouted` alone for a staged round. The args alone therefore do not tell the kinds apart.
11. `[verified: code-review/SKILL.md:46-50, :303]` `/code-review` also runs as a presentation-path review and as an ad-hoc review, which `:46-47` list among the contexts that typically run unnarrowed. `:50` classifies those contexts by the diff under review, not by which context fired. Only `:303` names a subject with no git diff: "a pasted-snippet or ad-hoc review with no git diff behind it at all". Nothing in the file says which diff a presentation-path review reads.
12. `[verified: docs/design-decisions/defect-class-exit-rule.md:47, :49; ready-for-review/SKILL.md:93]` The exit-rule replay counts "a branch's first recorded cumulative pass with no ADDRESS-class row". It takes a recorded pass from a surviving disposition record, which `/ready-for-review` writes, and the record never mentions `/review-pr`.
13. `[verified: docs/design-decisions/architect-disposition-challenge-pilot.md:106]` The challenge pilot's tag-coverage tally leaves out `/review-pr` rounds. Today it needs a transcript read to find them, because "neither skill text settles whether such a pass appends ledger rows".
14. `[unverified]` Whether a `/review-pr` pass appends ledger rows today. The design does not depend on it, because any row such a pass writes says `review-pr`.
15. `[verified: review-ledger.sh:423-439; CHANGELOG.md:152-157, :158-165]` Three earlier declared inputs are refused when absent: `--round`, a lane on ADDRESS, DEFER and SETTLED, and `--source` on ADDRESS. Each CHANGELOG entry tells callers outside `/code-review` to pass the flag.
16. `[verified: review-ledger.sh:463-473; test_author_outcome.py:1902]` The one optional declared pair, `--authoring-agent` and `--authoring-effort`, stores `""` when omitted, and the author-outcome reader carries a case for that empty value.
17. `[verified: review-ledger.sh:412-419; code-review/SKILL.md:460]` Unrecognized flags exit 2, so a pre-pull session can meet a changed flag set. The `:460` text such a session holds corrects and retries a listed set of rejections, never skipping them, and a missing `--pass-kind` is not in that set. That text reports a rejection with no correction to the engineer with the script's reason.
18. `[verified: review-ledger.sh:639-645, :671; _review-ledger-lib.sh:874-886]` The dedup key is an include list of every declared field, `authoring_agent`, `authoring_effort` and `reviewers` among them. It leaves out the stamped or captured fields: `schema_version`, `event_time`, `id`, `reviewed_head` and `reviewed_tree`. The retry check compares every field outside its exclude list, which matches that key.
19. `[verified: code-review/SKILL.md:327; test_review_ledger_script.py:2072-2084]` The noise count greps `show --out` rows for `"disposition":"CONSULT","rationale":"noise"`, and an existing test pins that run in a shown row.
20. `[verified: review-ledger.sh:583-602]` One `jq -nc` object literal builds the row, so a field's position in that literal is its position in the stored line.
21. `[verified: _review-ledger-lib.sh:23, :59-64, :93-113; test_review_ledger_lib.py:308-311]` The lib already holds the closed-set pattern: `_REVIEW_LEDGER_CONSULT_VERDICTS`, `_review_ledger_consult_hint` and `_review_ledger_validate_consult`. Their input matrix lives in `TestValidateRoundCapVerdict`.
22. `[verified: test_review_ledger_script.py:2027-2070, :2094-2167]` The verdict parity tests read the skill's words from a "where `<verdict>` is ..." sentence up to its first period. They compare those words with the script's `Pass one of:` listing and its usage text. The flag parity tests require every `append` flag in the usage text to appear in a skill template span, and the reverse.
23. `[verified: test_review_ledger_wiring.py:45, :62, :220, :225; test_code_review_challenge_and_round_cap.py:378-382]` Several text pins hold:
    - `--authoring-effort high` appears exactly three times, and `--reviewer '<lane>'` once.
    - The substrings `--round <N> --source '<file:line>' [--decided-by` and `--defer-criterion '<name>' --ref '<id>' --relog --cited-line '<file:line>']` are pinned.
    - The CONSULT command is pinned through `--round <N>` and its closing backtick.
24. `[verified: grep of review-ledger.sh across test files; test_lib_cursor_identity.py:73, :960; test_author_outcome.py:1202-1208, :1226-1325]` Seven test files run the real `append` and expect a row:
    - `test_review_ledger_script.py`.
    - `test_announce_branch_review_history.py:116`.
    - `test_require_code_review.py:893`.
    - `test_enforce_marker_script_shape.py:2878`.
    - `test_author_outcome.py:1202-1208`, one helper behind six calls.
    - `test_branch_records_archive.py:141`.
    - `test_lib_cursor_identity.py:960`, through the `_append_args` it imports from `test_review_ledger_script.py` (`:73`). It needs no edit while `_append_args` defaults `pass_kind` to `"staged"`.
25. `[verified: ready-for-review/SKILL.md:93]` The disposition-record paragraph says the record "is canonical for the pass kind and Outcome the ledger has no column for". Once the ledger stores the field, that is false.
26. `[verified: defect-class-exit-rule.md:3, :143-145; cost-levers-considered.md:758 per the exploration summary]` The Revisit trigger and the 2026-11-17 follow-up paragraph are dated records.
27. `[verified: grep of "pass kind" and "pass-kind" under docs/]` Four lines in design-decision records say the ledger lacks a pass kind:
    - `branch-scoped-review-ledger.md:5` and `:240`.
    - `round-cap-consult-rearm.md:90`.
    - `architect-disposition-challenge-pilot.md:94`.

    This change removes a premise of each line but overturns none of the decisions they record.
28. `[verified: CHANGELOG.md:87-92, :152-157; grep of CHANGELOG in README.md, CONTRIBUTING.md, docs/ and .claude/rules/]` The schema-6 change and the lane change each got an `[Unreleased]` entry. No doc requires one.
29. `[verified: select-tests.py:732-745]` For this file set the domain rules select `claude/.claude/hooks/tests`, `claude/.claude/scripts/tests` and `claude-skills/skills/tests`. `CHANGELOG.md` selects nothing.
30. `[verified: check-skill-length.sh:130-145; hooks/_lib.sh:3233-3240]` The skill-length gate counts physical lines (`awk 'END{print NR}'` over the staged file), with a cap of 550 for `code-review/SKILL.md` and 200 for `ready-for-review/SKILL.md`.
31. `[engineer-verified: "Keep the entry (Recommended)"]` The engineer selected this label when asked whether the `CHANGELOG.md` entry, which the Ask does not name, stays in this plan.
32. `[unverified]` Whether a session holding the pre-pull `:460` text treats a `--pass-kind` rejection that states each value's meaning as one it can correct, or reports it to the engineer (row 17).
33. `[unverified]` A later replay keyed on the ledger's `pass_kind`, which the Revisit trigger (`defect-class-exit-rule.md:145`) waits on without specifying, would read a `/review-pr` pass labelled `cumulative` as a cumulative pass and could take it for an exit pass.
34. `[verified: review-ledger.sh:412-419, :671, :784; _review-ledger-lib.sh:884-886; scripts/tests/conftest.py:979-980]` What a revert leaves:
    - The reverted script rejects `--pass-kind` as an unknown argument, with exit 2 and the usage text.
    - Rows at schema 7 stay readable. The readers read no version field and read rows by key, `show` prints each whole row through `tojson`, and the dedup projection ignores a key it does not list.
    - The reverted retry check still sees `pass_kind` on a schema-7 retirer, so a retry against one is rejected as no longer live.
35. `[verified: test_review_ledger_script.py:3126-3141, :3219-3232]` The two earlier schema bumps split on retry. A retry against a retirer from before schema 5, which has no `reviewers` key, is rejected as no longer live. A retry against a retirer from before schema 6, which has no reviewed state, adds no row.
36. `[verified: ready-for-review/SKILL.md:15, :17, :43, :91; marker.sh:1110-1122; review-pr/SKILL.md:86]` In `/ready-for-review`'s documented flow, Step 0.1's short-circuit cannot fire in the cumulative invocation:
    - Step 1 requires a clean working tree, and each fix lands as a commit before the loop returns to step 2.
    - `marker.sh check code-review` reads an empty staged diff as `no-match`, a case its comment names for step 3.
    - `ready-for-review/SKILL.md` does not say whether the short-circuit applies there, and nothing re-checks the index between step 2 and step 3.
    - `review-pr/SKILL.md:86` says the short-circuit does not apply in a `/review-pr` pass.
37. `[verified: test_review_ledger_lib.py:43-46, :616-626, :1962-1977, :1987-1993]` The lib tests import `_DEDUP_KEY_CHANGES` from the script tests. `test_the_fixture_row_has_exactly_the_keys_the_script_writes` compares the lib's `_row` keys with it, and `test_the_differing_field_cases_name_every_dedup_key_field` compares `_RETIRER_KEY_FIELD_CHANGES` with it. Neither lib table holds `pass_kind`, and `_row` is at schema 6.
38. `[verified: test_review_ledger_script.py:2094-2112, :2155-2167; test_review_ledger_wiring.py:26-50]` The flag parity tests compare the usage text's flags with the union of every template span's flags, so one span carrying a flag satisfies both directions. The `--authoring-effort high` literal is pinned by an exact count of 3.
39. `[verified: docs/scripts.md:251-253, :257; test_review_ledger_script.py:3854-3857]` Rounds are whole groups by `session_id` and `round`, whatever their schema, with CONSULT rows left out. A pair needs an ADDRESS row in round N, and its tally is per row of round N+1. Test fixtures write rows with no `schema_version` key.
40. `[verified: _review-ledger-lib.sh:66-83; review-ledger.sh:269-292]` Two rejections already state the meaning of what they ask for: the lane hint glosses each non-agent lane, and the missing-`--round` message explains the round number.
41. `[verified: code-review/SKILL.md:25; author_outcome.py:105, :818-821 per the round-2 review]` Step 0.1 defines the round number as a count of `/code-review` invocations and passes one value to every append of a round, so one `session_id` and `round` group holds one invocation's rows. That holds only while the session tracks its counter. `author_outcome.py` already treats a session whose ledger round sequence does not match its round-opens as untrusted.
42. `[verified: marker.sh:1099-1100; hooks/_lib.sh:1828-1829]` While a merge, rebase, cherry-pick or revert is in progress, the marker check hashes `git diff --cached "$BASE"`, the staged diff relative to that base, not plain `git diff --cached`.

**Mechanisms:**

**M1. A required `--pass-kind` with a closed value set, refused when absent.** `anchors: root, row2, row3, row15, row16, row17`. This is the recommendation for open choice 2, and G2 is the cost it accepts. Five other primitives fail:

- An optional flag that stores `""` as undeclared, the `--authoring-agent` model (row 16). A pre-pull session or an outside caller would then write undeclared rows silently and with no end date, and every reader would carry a fifth state at schema 7 and above. Refusal turns the same staleness into one exit 2 whose message carries the fix (M11).
- Deriving the kind from git state, such as the index tree against HEAD's tree. A cumulative pass, a `/review-pr` pass and an ad-hoc review of a clean tree all show the index equal to HEAD (rows 10, 11), and schema-6 rows already let a reader compute that much.
- Deriving it from marker state. `/ready-for-review`'s active marker spans step 3's staged fix-commit rounds as well as its cumulative pass (`ready-for-review/SKILL.md:30-35`, `:91`), so it cannot tell them apart.
- A token in the args, or an environment variable set by the invoking skill. A new args word changes the contract row 5 keeps, and `code-review/SKILL.md:303` reads the path as whatever follows `unrouted`. An environment variable does not survive across Bash tool calls.
- A `--rationale` prefix, as the challenge pilot's `<scope>` is. CLEAN rows take no `--rationale` (`review-ledger.sh:450-453`), so clean rounds would carry no kind.

What refusal costs beyond recording `""`: test edits in six of row 24's seven files. Both choices need the template edits and the CONSULT pin change.

**M2. Four values, two named for an invocation and two for a diff, in a stated order.** `anchors: row2, row9, row10, row11, row12, row13, row33`. This is the recommendation for open choice 1.

- `cumulative`: `/ready-for-review` step 3's cumulative PR-vs-base pass.
- `review-pr`: a `/review-pr` pass.
- `staged`: any other round whose diff under review is exactly `git diff --cached`, on any branch. That covers every commit-gate round, routed or not, the HALT fallback, a commit to the default branch, and an ad-hoc or presentation-path review whose diff is exactly the staged diff. Step 0.1's short-circuit passes it in every invocation (M13).
- `other`: any other subject, such as a commit range, a diff that also holds unstaged changes, or a review with no git diff behind it (row 11).

The Step 0.1 sentence lists the two invocation values first and gives `staged` to "any other round", so a round that two descriptions fit gets one value. `staged` keys on the diff, not on which context fired, as `:50` does for narrowing (row 11). Step 0.1's sentence drops Step 0.6's default-branch qualifier (row 9) and says so inline. A default-branch commit is therefore `staged`. `:244`'s example tag calls that case a "cumulative diff", and the tag does not decide the value.

A commit-gate round is also `staged` while a merge, rebase, cherry-pick or revert is in progress. The gate then reads the staged diff relative to that operation's base (row 42), and it is still the staged diff the round reviews. The sentence's "exactly `git diff --cached`" is `:50`'s own wording for the same rounds, so the two read alike.

Four other value sets fail:

- `staged` and `cumulative` alone. A `/review-pr` pass folded into `cumulative` could read as an exit pass (rows 12 and 33), and a required flag would leave a review with no git diff behind it no honest value.
- Three values without `other`. This fails on a review with no git diff behind it alone.
- The pilot's `narrowed` and `unnarrowed`. A default-branch commit is a staged round that runs unnarrowed (`code-review/SKILL.md:48`, `:244`), so the pair does not separate staged rounds from cumulative passes.
- `/review-pr` folded into `other`. The pilot tally needs those rounds by name (row 13).

**M3. Step 0.1 fixes the kind, inside the paragraph that already fixes the per-round value, and each template carries `--pass-kind <kind>`.** `anchors: row3, row7, row8, row9, row10`. Neither SKILL.md gains a physical line. Four alternatives were set aside:

- A new paragraph. It adds a line that needs an offsetting deletion, and the existing paragraph is already the home of the rule that every append in a round passes the same value.
- Value meanings in `--help` only. Each round would have to run `--help`, or fail one append, before it knew the value.
- An instruction in `/ready-for-review` and `/review-pr`. Neither holds an append (row 8). Each sits at or one line under its 200-line cap (row 30 and the exploration summary). A routed `review-orchestrator` round would get no instruction.
- Reading the kind from the args. Row 10 rules this out.

**M4. `pass_kind` is in the dedup key and is compared by the retry check, as `reviewers` is.** `anchors: row18, row35`. Declared inputs go in the dedup key, and lanes did. Captured or stamped values stay out of it, and the reviewed state did. `pass_kind` is declared, and it is the same for every append of one round. The retry check must compare every field the key holds, because a retry that passed the check and then missed the dedup would land a second row retiring the same decision.

An append that repeats a landed row with another `pass_kind` is therefore not a retry. Its outcome by row type, which the docs bullet states:

- A ref-less row or a carry lands as a second row. Its round then holds two values and reads as unknown (M14), and a per-row tally counts that finding twice.
- Any other `--ref` row is rejected as no longer live, so a landed `--ref` row's pass kind is final.
- A `--ref` append that landed before the pull, retried after it, is rejected as no longer live, because the landed row has no `pass_kind`. `docs/scripts.md:280`'s no-op covers only a retry with the same fields, which this is not. A retry against a pre-schema-5 retirer already meets the same rejection for `reviewers` (row 35).

Two alternatives were set aside:

- Out of both the key and the retry check, as the reviewed state is. Every retry would then be a no-op, the pull-window one included. A changed retry would also exit 0 and keep the first value. A session correcting a label would then wrongly believe it had. Its round would carry the wrong kind with nothing marking it. Under the chosen design the same correction either marks the round unknown or is refused aloud. The pull-window `--ref` retry this would fix needs a lost response and a pull between two attempts.
- In the key but out of the retry check. A retry with another value would pass the check, miss the dedup and retire one decision twice.

**M5. The field sits right after `round`.** `anchors: row19, row20`. A field between `disposition` and `rationale` would break the noise grep and its pinned test. After `round` also keeps it beside the round's other per-round value.

**M6. Validation and its hint live in the lib, with the matrix in the lib's tests.** `anchors: row21`. This follows `.claude/rules/bash-unit-test-seams.md` item 1, extending a sibling lib whose domain covers it. The subprocess tests keep one case per branch, per `shell-script-conventions.md`.

**M7. The reader rule goes in `docs/scripts.md`, and the CHANGELOG gets an entry.** `anchors: row4, row15, row28, root`. The bullet cites `code-review/SKILL.md` § "Step 0.1 — Short-circuit already-reviewed diff" for what each value marks rather than restating the mapping. M14 sets the rule's grain, and M4 the retry outcomes it states. The CHANGELOG entry follows row 28's precedent. It carries the migration notice G2 makes necessary and the restart the lane entry asked for (row 15), and M12 adds the revert text.

**M8. `ready-for-review/SKILL.md:93` drops its pass-kind claim within its own line.** `anchors: row25, row30`. The record stays canonical for Outcome only, and the ledger becomes the one home of the pass kind.

**M9. Dated and decision records stay as written.** `anchors: row6, row26, row27`. Scope discipline Axis 3 makes the dated records read-only. `.claude/rules/design-decisions.md` edits a decision record only when a later decision overturns it, and this change overturns none (row 27). The Revisit trigger stays half met until fix shape lands, which row 6 puts out of scope.

**M10. One `code-writer` dispatch covers every file.** `anchors: row22, row23, row24`. The parity tests read the Step 0.1 sentence, the rejection text and the usage text together. A split would restate the flag name, the value set, the field position and the sentence shape in every prompt.

**M11. The rejection states each value's meaning.** `anchors: G2, row17, row32, row40`. The callers that meet the rejection are a session whose loaded skill predates the flag (G2) and an outside caller. Neither holds the Step 0.1 sentence. A message that only pointed at Step 0.1 would point a stale session at text it lacks, and the `:460` text that session holds names no correction for a missing flag (row 17). The hint therefore carries the mapping, as the lane hint glosses its lanes and the missing-`--round` message explains the round number (row 40).

The mapping then has two homes, Step 0.1 and the hint. `CLAUDE.md` § "Engineering Judgment" names instructional prose that must stand alone as an exception to single source of truth, and a rejection read by a caller without the skill is that case. The parity tests pin the value set across Step 0.1, the hint and the usage text (M15). Two alternatives were set aside:

- A pointer to Step 0.1 alone. A stale session holds the old Step 0.1, so it would guess from four bare words or stop.
- An instruction to re-read the skill from disk. An outside caller has no skill to read, and the step depends on the session finding its stowed skill file, which the old `:460` never asks it to do.

A value a stale session declares from the hint is its reading of its own round, the reading Step 0.1 asks of a fresh session. Nothing in the row tells the two apart. Whether a stale session corrects from the hint or reports the rejection is row 32's open fact. Either way the validator runs before any I/O, so no row lands without a valid value. The CHANGELOG entry asks for a restart, so the first append after the pull is not rejected at all.

**M12. Rollback is a revert, and the CHANGELOG says what it leaves.** `anchors: G2, row34`. A revert needs no data step, because the reverted script reads rows at schema 7 (row 34). It leaves two things:

- G2's window, flipped. A session that loaded the new `/code-review` passes `--pass-kind` to a script that rejects it as an unknown argument, on every append, until the session restarts.
- A `--ref` retry against a schema-7 retirer, rejected as no longer live. This is the reverse of M4's pull-window case, and it is as narrow.

The CHANGELOG entry states the data safety and the restart, and this plan keeps the `--ref` residual. A revert deletes that entry with the rest of the change. The entry therefore reaches the engineer deciding the revert, not a stow consumer who pulls it, as the schema-6 entry's revert note does (`CHANGELOG.md:93`). A config switch that turns the requirement off was set aside: it adds a key and a second code path for a window that a restart closes.

**M13. Step 0.1's short-circuit CLEAN append passes `staged` literally.** `anchors: row11, row36, row42`. The short-circuit matches only the staged diff's marker, read relative to a base while a merge, rebase, cherry-pick or revert is in progress (row 42). `staged` is therefore true of its row in every invocation (M2). A literal needs no judgment, so the row cannot read `cumulative` in an invocation where no cumulative review ran, which would corrupt the clean-cumulative-re-pass count. In `/ready-for-review`'s documented flow the short-circuit never fires in the cumulative invocation, and `/review-pr` bars it (row 36). Two alternatives were set aside:

- Letting the Step 0.1 sentence's order decide. In an invocation from `/ready-for-review` step 3 the sentence picks `cumulative`, for a row no cumulative review wrote.
- Barring the short-circuit there, as `review-pr/SKILL.md:86` does for its own pass. That changes `/ready-for-review`'s behavior, which the Ask does not cover, in a file at its line cap (row 30). Out of scope records it.

**M14. The reader rule has one grain, the round.** `anchors: row4, row39, row41, root`. A round's rows come from one `/code-review` invocation (row 41), so they share one subject, and the pass kind belongs to the round. Each row only records it.

- A round's pass kind is the one value its rows at schema 7 or more hold. With no such row, or with two values among them, it is unknown, and unknown is none of the four.
- Every row of a round counts under that value, a row below schema 7 included. A pair's tally, which is per row of round N+1 (row 39), therefore counts under round N+1's kind.
- A row below schema 7 takes its round's kind on the round number alone (row 41). The docs bullet says so, so a count can leave out a session whose round sequence it does not trust.
- A CONSULT row is left out of its round, as `docs/scripts.md:251` has it, and counts under its own value. Below schema 7 it counts as unknown even when its round has a known kind, because a CONSULT row can be appended with no `/code-review` round in flight.
- A row whose `schema_version` is absent or not a number counts as below 7, because fixtures and early rows carry none (row 39).

A per-row grain was set aside. A round that straddles the pull would then count its schema-6 rows as unknown and its schema-7 rows as their kind, so a per-row count and a per-round count of one file would disagree. Which round labels a pair in a report is report design, which row 6 puts out of scope.

**M15. Tests pin each template, each message and each stored value.** `anchors: row22, row23, row24, row37, row38`.

- The flag parity tests compare sets, so one span carrying `--pass-kind` satisfies them (row 38). A per-span pin in `test_review_ledger_wiring.py`, beside the `--authoring-effort high` count it follows, catches a span that drops or doubles the flag.
- The subprocess rejection cases assert the whole message line, as the missing-`--round` case does (`test_review_ledger_script.py:810-816`), so an exit 2 from another branch cannot pass them.
- A CLEAN row and a CONSULT row each assert their stored value, because clean cumulative re-passes are the count the issue exists for.
- The lib fixtures that mirror the row's keys gain `pass_kind` (row 37), and two cells pin M4's old-schema outcomes, one at each layer.

## Critical files

Implementation:

1. `claude/.claude/scripts/_review-ledger-lib.sh`. Adds `_REVIEW_LEDGER_PASS_KINDS`, `_review_ledger_pass_kind_hint` and `_review_ledger_validate_pass_kind VALUE`, as the Approach gives them. They sit beside `_REVIEW_LEDGER_CONSULT_VERDICTS` (`:23`), `_review_ledger_consult_hint` (`:59-64`) and `_review_ledger_validate_consult` (`:101-113`). Reuse `_review_ledger_reject` (`:46-49`) for both rejections and `_lib_list_contains` (`hooks/_lib.sh:5074`) for membership, as lane validation does (`:254`). The validator performs no I/O, prints its reason to stderr and returns 1. The retry check (`:870-891`) is unchanged (M4).
2. `claude/.claude/scripts/review-ledger.sh`, in file order:
   - `:38-40`: the schema comment and constant, per the Approach's schema and comment bullets.
   - `:47-63`: the usage synopsis and the `--pass-kind` sentence, per the Approach's usage bullet.
   - `:118-121`: the usage text's dedup field list, per the same bullet.
   - `:364-380`: a `PASS_KIND=""` initialization beside `ROUND=""`.
   - `:383`: `--pass-kind` in the value-flag arity list.
   - `:395-411`: a `--pass-kind) PASS_KIND="$2"; shift 2 ;;` parse arm.
   - After `:496`: `_review_ledger_validate_pass_kind "$PASS_KIND" || exit 2`.
   - `:583-602`: `--arg pass_kind "$PASS_KIND"`, and `pass_kind: $pass_kind` right after `round: $round` in the object literal (M5).
   - `:644-645`: the dedup comment, per the Approach's comment bullet.
   - `:671`: `pass_kind` right after `round` in the include list (M4).
3. `claude-skills/skills/code-review/SKILL.md`. Changes lines `:25`, `:27`, `:333`, `:449`, `:458` and `:460` as the Approach gives them, with net zero lines.
4. `claude-skills/skills/ready-for-review/SKILL.md`. Changes `:93` as the Approach gives it, with net zero lines.
5. `docs/scripts.md`. Adds this bullet after `:191`, at the **Lanes.** bullet's indent:
   - **Pass kind.** From schema 7 each row stores `pass_kind`, one of `staged`, `cumulative`, `review-pr` or `other`. `code-review/SKILL.md` § "Step 0.1 — Short-circuit already-reviewed diff" says which value a round passes.
     - `append` refuses a row without one of the four, so every row at schema 7 or more holds one.
     - A row is below schema 7 when its `schema_version` is absent, not a number, or less than 7. Such a row has no `pass_kind`.
     - A pass kind belongs to a round, as "To compare two rounds" below forms rounds. A round's pass kind is the one value its rows at schema 7 or more hold. A round with no such row, or with two values among them, has an unknown pass kind, which is none of the four.
     - Every row of a round counts under its round's pass kind, a row below schema 7 included. A pair's tally of round N+1's rows therefore counts under round N+1's pass kind.
     - A row below schema 7 takes its round's pass kind on the round number alone, so the count is only as good as that session's round sequence.
     - A CONSULT row is left out of its round, as "To compare two rounds" has it. It counts under its own `pass_kind`, or as unknown below schema 7 even when its round has a known pass kind.
     - The value is the appending session's declaration. Nothing checks it against the diff the round reviewed.
     - `pass_kind` is in the dedup key, so an append that repeats a landed row with another value is not a retry:
       - A ref-less row or a carry lands as a second row. Its round then holds two values, and a per-row tally counts that finding twice.
       - Any other `--ref` row is rejected as no longer live, so a landed `--ref` row's pass kind is final.
       - A `--ref` append that landed before schema 7, retried after it, is rejected as no longer live, because the landed row has no `pass_kind`.
     - `show` prints `pass_kind`, and `render` does not.
6. `CHANGELOG.md`. Adds this entry first under `## [Unreleased]` / `### Changed`:
   - **`review-ledger.sh append` now requires `--pass-kind` and records it on each row.**
     - Each new row stores `pass_kind` (`staged`, `cumulative`, `review-pr` or `other`), and `schema_version` is now 7. `docs/scripts.md`'s `review-ledger.sh` entry says how to read rows written before schema 7.
     - `/code-review` passes the value on every append, and `/ready-for-review`'s disposition record is no longer the home of a pass's kind.
     - **Migration:** an `append` without a valid `--pass-kind` now exits 2 and writes nothing, and the rejection says what each value means. Any caller outside the stowed `/code-review` skill must pass the flag.
     - Restart any session that loaded `/code-review` before the pull: a restart avoids a rejected first call.
     - The change is live on `git pull`.
     - Reverting it needs no data change, because the reverted script's readers ignore the added field. After a revert, restart any session that loaded `/code-review` since the pull, because the reverted script rejects `--pass-kind` as an unknown argument.

Tests:

7. `claude/.claude/hooks/tests/test_review_ledger_script.py`. The edits are:
   - `_append_args` gains `pass_kind: str | None = "staged"` among its optional valued flags. The `"staged"` default is load-bearing for `test_lib_cursor_identity.py` (row 24).
   - `_round_cap_verdict_args` gains a `pass_kind: str = "staged"` parameter that it passes as `--pass-kind`.
   - Each hand-built append that expects a row gains `--pass-kind staged`. A hand-built append that expects a rejection needs none, because it is rejected before the validator runs.
   - The schema is 7 at `_row_envelope_bytes` (`:170`, with `"pass_kind": "staged"` after `"round"`), `:983`, `:1002`, `:1546` and `:3889`.
   - The happy-path dict at `:351-370` moves to schema 7 and gains `"pass_kind": "staged"` after `"round"`.
   - `_DEDUP_KEY_CHANGES` gains `"pass_kind": "cumulative"`. Its cases then show a ref-less row with another value landing a second row, and a `--ref` retry with another value rejected as no longer live (M4).
   - `TestReviewLedgerDedupKey` gains a case modeled on `:985-1002`. It appends a CLEAN row, rewrites it with `pass_kind` deleted and `schema_version` 6, appends it again, and asserts two rows whose schema versions are `[6, 7]`.
   - The show test at `:3873-3892` also asserts that the schema-7 row shows `pass_kind` `staged` and the schema-2 row shows no `pass_kind`.
   - The CONSULT case at `:1537-1546` passes `pass_kind="review-pr"` and asserts the stored `pass_kind` is `review-pr`.
   - Two module-level helpers hold the expected rejection text once, `_pass_kind_missing_line()` and `_pass_kind_unknown_line(value)`. The subprocess cases below use them, and `test_review_ledger_lib.py` imports them beside `_DEDUP_KEY_CHANGES`.
   - A new `TestReviewLedgerPassKind` covers one subprocess case per branch, each with a seeded session and every other flag valid:
     - Absent: exit 2, no ledger file, and stderr holds the whole missing-value line the Approach gives.
     - `cumulative-pass`: exit 2, no ledger file, and stderr holds the whole unknown-value line for that value.
     - A CLEAN row with `--pass-kind cumulative` lands with `pass_kind` `cumulative` and `schema_version` 7.
   - The same class holds parity cases modeled on `TestRoundCapVerdictSkillParity`:
     - The words come from Step 0.1's "where `<kind>` is ..." sentence up to its first period, read as `_skill_round_cap_verdict_words` reads its own. They keep each backticked token that `re.fullmatch(r"[a-z][a-z-]*", token)` accepts, which drops `/ready-for-review`, `/review-pr` and `git diff --cached`.
     - Exactly four words appear. This count also guards against a skill name leaking in through a looser match.
     - Each word is accepted.
     - The set equals the rejection's `Pass one of:` listing.
     - The set equals the usage synopsis's alternatives, read from the first `--pass-kind` followed by `|`-joined words.
8. `claude/.claude/scripts/tests/test_review_ledger_lib.py`. The edits are:
   - A new `TestValidatePassKind`, modeled on `TestValidateRoundCapVerdict`. It accepts each of the four values. It rejects `""` with the missing-value line. It rejects `Staged`, ` staged`, `staged `, `review_pr` and `cumulative-pass` with the unknown-value line for each. Every rejection ends with the four-value listing. The expected lines come from the two helpers item 7 defines, imported at `:43-46`.
   - `_row` (`:616-626`) moves to `schema_version` 7 and gains `"pass_kind": "staged"` after `"round"`, which `:1973-1974` needs (row 37).
   - `_RETIRER_KEY_FIELD_CHANGES` (`:1962-1969`) gains `"pass_kind": "cumulative"`, which `:1976-1977` needs. Its parametrized case at `:1995` then pins at the lib layer that the retry check compares `pass_kind`.
   - The retry at `:1991` moves to `schema_version` 7.
   - `TestCheckNotRetired` gains a case beside `:1987-1993`. A retirer at `schema_version` 6 with `pass_kind` deleted, and a retry identical to it apart from a `pass_kind` and its per-attempt fields, is rejected as no longer live (M4).
9. `claude-skills/skills/tests/test_code_review_challenge_and_round_cap.py`. The CONSULT pin at `:379-381` ends `--round <N> --pass-kind <kind>` and then the backtick.
10. `claude/.claude/hooks/tests/test_announce_branch_review_history.py` (`:116-120`), `claude/.claude/hooks/tests/test_require_code_review.py` (`:893-895`), `claude/.claude/hooks/tests/test_enforce_marker_script_shape.py` (`:2878`) and `claude/.claude/scripts/tests/test_branch_records_archive.py` (`:141-142`). Each real `append` gains `--pass-kind staged`.
11. `claude/.claude/scripts/tests/test_author_outcome.py`. `_run_append` (`:1202-1208`) puts `--pass-kind staged` after `append code-review` once, for its six calls.
12. `claude-skills/skills/tests/test_review_ledger_wiring.py`. Adds `TestReviewLedgerPassKindLiteral` beside `TestReviewLedgerAuthoringEffortLiteral` (M15). It takes every inline code span of `code-review/SKILL.md` that holds both `review-ledger.sh append` and `--disposition`, and asserts:
    - There are four such spans.
    - Each holds `--pass-kind ` exactly once.
    - The span inside Step 0.1's section, read with `_heading_section_text` and `_CODE_REVIEW_STEP_0_1_HEADING` (`_skill_md_helpers.py:540`), passes `staged`, and the other three pass `<kind>`.

`claude/.claude/hooks/tests/test_lib_cursor_identity.py` also runs the real `append`, and needs no edit (row 24).

Dispatch split: one `code-writer` dispatch carries files 1-12 (M10), with Verification steps 1-4 as its commands. The session then runs `/code-review`, which invokes `/skill-review` for files 3 and 4, before the commit.

Projected diff: about 315 lines changed across these 15 files, mostly tests: about 130 in file 7, 55 in file 8, 30 in file 12 and 15 across files 9-11. Of the rest, files 1 and 2 take about 50, files 3 and 4 about 14, and files 5 and 6 about 22.

## Verification

1. `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py` passes from the worktree root. For this file set it selects `claude/.claude/hooks/tests`, `claude/.claude/scripts/tests` and `claude-skills/skills/tests` (row 29). The run includes these tests:
   - The new `TestReviewLedgerPassKind`, `TestValidatePassKind` and `TestReviewLedgerPassKindLiteral`.
   - `TestRoundCapVerdictSkillParity`, whose noise-row case guards the field position (M5).
   - `TestReviewLedgerSkillFlagParity`, which pins `--pass-kind` in the usage text and the template spans as sets.
   - The `_DEDUP_KEY_CHANGES` cases in `TestReviewLedgerDedupKey` and `TestReviewLedgerRefRetry`. They show a ref-less row with another `pass_kind` landing a second row, and a `--ref` retry with another `pass_kind` rejected as no longer live (M4).
   - The two old-schema cells: a schema-6 row without `pass_kind` that an append does not dedup against, and a retry rejected against a retirer without `pass_kind` (M4).
   - `TestCheckNotRetired`, whose `_RETIRER_KEY_FIELD_CHANGES` case covers `pass_kind` at the lib layer.
   - `test_review_ledger_wiring.py`, `test_code_review_challenge_and_round_cap.py` and `test_lib_cursor_identity.py`.
2. `scripts/venv-run.sh ruff check claude/.claude/ claude-skills/ plugins/ evals/` reports nothing.
3. `scripts/list-shell-files.sh | xargs -0 scripts/venv-run.sh shellcheck` reports nothing.
4. Before the commit, `git diff --numstat HEAD -- claude-skills/skills/code-review/SKILL.md claude-skills/skills/ready-for-review/SKILL.md` shows equal added and deleted counts on each output line (rows 3 and 7). `check-skill-length.sh` enforces the caps again at commit.
5. `/code-review`, and `/skill-review` for both SKILL.md files (hook-enforced, `.claude/rules/review-pipeline-dispatch.md`), run before the commit.

## Out of scope

- A fix-shape field (row 6).
- Any report or reader that consumes `pass_kind`, including `render`, `show --trend`, `transcript-analysis.py author-outcome` and the defect-class replay (row 6).
- Which round labels a pair in a count split by pass kind. Under M14 a pair's tally counts under round N+1's kind. A staged fix round follows a dirty cumulative pass. The cumulative stratum of that count is therefore empty by construction. The plan's reviewers traced this from the skill text and did not run it on a ledger file. A count labelled by round N's kind is a new report (row 6).
- A read-back for a pass kind lost to compaction before the round's first append. `code-review/SKILL.md:25` reads the round number back from `show`, but no row of the round has landed yet to carry its kind. Such a session re-derives the kind from the invocation's args and subject, as Step 0.1 asks. A read-back would need a stored per-round state this plan does not add.
- Rewording Step 0.1's "exactly `git diff --cached`" to name the base-relative staged diff of an in-progress merge, rebase, cherry-pick or revert. `:50` uses the same words for the same rounds, and M2 states that those rounds are `staged`.
- Which rows make a round clean in the clean-cumulative-re-pass count. `ready-for-review/SKILL.md:93` counts a DEFER as resolved, while a CLEAN row means zero findings, so the report that reads the field picks one (row 6).
- Backfilling or rewriting rows written before schema 7 (G1). M14 counts them under their round's kind, or as unknown.
- Barring Step 0.1's short-circuit in `/ready-for-review` step 3's invocation, as `review-pr/SKILL.md:86` bars it in a `/review-pr` pass. It does not fire there in the documented flow, and its row says `staged` either way (M13, row 36).
- A way to correct a landed `--ref` row's pass kind. M4 makes it final, and the docs bullet says so.
- A test that the hint's value meanings match Step 0.1's word for word. The parity tests pin the value set only (M11).
- The challenge pilot's `challenge:<outcome>:<scope>` tag (`code-review/SKILL.md:437-445`). Its record says it exists because the ledger lacked this field (`architect-disposition-challenge-pilot.md:94`). Dropping or re-deriving it would change that pilot's pre-registered strata (`:98-103`), so the call belongs to the pilot's owner.
- Rewording `code-review/SKILL.md:244`'s example tag that calls a default-branch commit a "cumulative diff". Step 0.1's sentence names a default-branch commit as `staged` inline, so the tag does not decide the value (M2).
- Editing the dated and decision records of rows 26 and 27 (M9).
- Checking the declared value against the round's subject, for example against `/review-pr`'s provenance file. The value is a declaration, as a lane is (`docs/scripts.md:188`).
- Settling whether a `/review-pr` pass appends ledger rows (row 14).
- Splitting `test_review_ledger_script.py`, already past the 1,000-line limit that `docs/design-decisions/code-file-line-limit.md` sets and that nothing yet enforces.
