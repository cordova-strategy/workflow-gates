# Commit the comment-reviewer docstring study as labeled fixtures

## Context

Goal: commit the labeled evidence from the 2026-11 study of `comment-discipline-reviewer` against the engineer's docstring rule, so the data and its adjudication survive transcript sweeps, without changing the reviewer body or the rule text.

Ask: "you should definitely plan to commit the fixtures and not defer" (the engineer's words as quoted in the prior session's handoff, not typed in this session). Scope answers this session: "Evidence, no raw streams (Recommended)" and "Data only, no tooling (Recommended)". Hold: no edit to `claude/.claude/CLAUDE.md:116` or `claude/.claude/agents/comment-discipline-reviewer.md`; the engineer chose to stop and record the stage-1 result rather than change the reviewer wording (selected "number one", then asked what option 2 meant and was told it adds no reviewing work for them).

Why now: the study ran in scratch under `~/.local/state/comment-cells-2026-11-19/` and the transcripts that hold its provenance are swept. The engineer's rule: "A docstring exists to state a non-obvious design decision. Anything a reader can find by static analysis (callers, callee behavior, exception types, tests) doesn't belong, even if it's true and takes some reading to find."

What was measured, all in scratch:
- First measurement: 315 runs (35 cells x 3 bodies x 3 runs) of shipped, amended and ablation reviewer bodies over 31 real docstrings (P01-P31) and 4 synthetic controls (K1, K2, D1, D2). Labels v4 (`labels-v4.md`): 101 clause rows, KEEP 8, REWRITE 5, KEEP AS SUBJECT 9, DELETE 79, CONTESTED 6 (P05c2, P10c3, P21c3, P22c3, P26c3, P29c4).
- Stage 1: 77 runs of the amended-v2 body over 21 cells (P17 and P26 ten runs each), frozen by hash before running (`freeze-stage1.txt`), $10.41 spent (row 28). Result NO-GO: the REWRITE bar passed 3 of 10 on P17c7 and 3 of 10 on P26c4 against a gate of 7 of 10; control R1 had a clause deleted in 3 of 3 runs as an unsourced claim, not a restatement; no confirmed DELETE-row harm beyond one P17c1 run. Adjudication: 32 blinded packets, verdicts in `adjudication/verdicts/`, key in `adjudication-key/key.json`.
- Known label disputes to record as disputes: P23c2, P27c3, P11c2, P11c3, P25c2. Limits to state: partial blinding (the wrapper says "Rule under test"; K1/K2 `ctl_*` names visible), the REWRITE answer rests on two rows, labels changed between measurements (v3 vs v4 scores not interchangeable), comments not just docstrings were unmeasured, matcher thresholds were tuned on the same outputs.

Redaction constraint: the repo is public. The cells are this repo's own scripts, but findings and diffs may carry home-rooted absolute paths, long hex, and tracker-shaped IDs that the always-on detectors reject. No figure may carry a per-project, per-account or per-engagement dimension.

## Approach

Publish the study as a dated report, `docs/reports/2026-11-19-comment-docstring-study/`. Its `evidence/` subdirectory holds 508 files copied at their scratch-relative paths from a checked backup of the scratch tree, with three named substitutions that clear the redaction gate. An authored `findings.md` maps the layout and states the result, the disputed labels and the limits. One section in `docs/design-decisions/prose-restating-code-is-deleted.md` records why the restating bullet keeps its wording, `docs/reports/README.md` gains the report's row, and `.rgignore` hides `evidence/` from Grep. An untracked marker arms the redaction gate for this worktree. No test, script, `select-tests.py` rule or changelog entry is added.

**Destination.** `docs/reports/` holds dated, pinned, unedited empirical records of the workflow this repo ships (row 13), and this study is one. The `docs/**` rule in `select-tests.py` already covers any depth below `docs/reports/`, so the new path needs no rule-table entry (row 15). No `.py` or `.sh` file lands, so pytest collection, `norecursedirs`, ruff and ShellCheck are untouched. `.rgignore` matches no `select-tests.py` rule, so the selector runs the full suite on its own (row 39). `docs/` is not a stow package, so no stow consumer's `~/.claude` changes (row 16).

**What reads it.** No test reads `evidence/`, because the data is a record, not a regression fixture. `paragraph-readability.json` has a test because it pins angle text that ships, so a rewording is caught (row 17). The wording this study measured never shipped, so there is no live text to pin. Pinning the shipped reviewer instead would make every later reviewer edit touch a study record. No existing report has a test either (row 13). `findings.md` states that the freeze digests match the files as of the commit that adds the report, and that `git log` on `evidence/` shows any later change (row 33). The readers are `findings.md` and the decision record, which cite files in `evidence/`, and anyone re-running the two recipes that need only the committed files (M3). Grep skips `evidence/` (M10), so a search for the reviewer or a study function returns live definitions, not 392 reviewer outputs and the unshipped reviewer bodies and rule files.

**Layout (M1).** `evidence/` mirrors the scratch root, so every relative path a copied record cites to another published file resolves inside it: `go-no-go.md` cites `out-v2/amended-v2/` and `adjudication-key/`, and `freeze-stage1.txt` lists `probe/...` paths. The records also cite scripts, manifests, stream logs and the unused `ablation-v2` body, none of which is published. `findings.md` documents this mapping:
- `evidence/labels-v4.md` is the label table. `evidence/probe/labels.json` carries the same labels keyed by `row_id`, where `P17c7` is clause 7 of function P17.
- `evidence/probe/cells/<id>-<function>/diff.patch` is the diff each run reviewed. P01 to P31 are real docstrings from this repo. K1, K2, R1 and R2 are keep controls, and D1 and D2 are delete controls. R1 and R2 ran in stage 1 only.
- `evidence/probe/out/<body>/<cell>/run<N>.md` holds the first measurement's findings, for bodies `shipped`, `amended` and `ablation`, runs 1 to 3. `evidence/probe/out-v2/amended-v2/<cell>/run<N>.md` holds stage 1's.
- `evidence/probe/bodies/` holds the four reviewer bodies and the two rule files the runs used (row 19).
- `evidence/probe/adjudication/packets/` and `evidence/probe/adjudication/verdicts/` hold the 32 blinded packets and their verdicts. `evidence/probe/adjudication-key/key.json` maps each packet id to `source`, `row_id` and `run`. Source `amended-v1` is `probe/out/amended/`, and `amended-v2` is `probe/out-v2/amended-v2/` (`go-no-go.md:77-78`).
- `evidence/probe/go-no-go.md`, `v2-diff.md` and `freeze-stage1.txt` are stage 1's criteria, change list and pre-run freeze. `go-no-go.md` was approved before any run, so its lines saying nothing has run are not a contradiction.
- `evidence/probe/stage1-results.md` holds the frozen tools' output after the stage-1 runs. It postdates the freeze, so no freeze line covers it (row 12).
- `evidence/probe/score-report-full.txt` and `adjudication.md` are the first measurement's scorer report and hand adjudication.

**Sanitization (M2).** A one-time script in the scratch tree, never staged, makes three literal substitutions. Each asserts its expected match count and aborts the copy otherwise:
1. In the 8 run files that cite the author's checkout by absolute path, the home-directory prefix becomes `/home/<username>/`, once per file.
2. In `probe/labels.json` and `probe/score-report-full.txt`, the 40-character source commit becomes its 12-character prefix, `4d2d6ea16136`, once per file.
3. In `probe/freeze-stage1.txt` lines 1 to 41, each 64-character sha256 digest becomes its first 16 characters.

No other byte changes, and `stage1-results.md` needs none (row 12). The 12 truncated digests of unpublished files stay, because they belong to the freeze record and a 64-bit prefix only confirms a copy its holder already has. `findings.md` lists the 11 changed files and the three rules without quoting any removed value (rows 8, 9).

**Copying safely and checking the copy (M3).** The scratch tree is the study's only copy (G2) and is still being written (row 44), so the session fixes the sources before any script written for this change runs:
- It writes a sha256 manifest of the 508 allowlisted files and copies them with plain `cp` into a backup directory under `~/.local/state/`, outside the scratch tree (Verification step 0). From then on, the manifest is the allowlist.
- The copy script reads only the backup, so the scratch tree is never its input. It opens each source read-only and writes only under `docs/reports/2026-11-19-comment-docstring-study/evidence.tmp/`, which it creates. It refuses to start when `evidence/` or `evidence.tmp/` exists, and a leftover `evidence.tmp/` from a killed run is deleted by that path before a rerun. It renames `evidence.tmp/` to `evidence/` only after every assertion passes, and on any failure it removes only the directory it created.
- After the copy, the manifest is re-checked against both the scratch tree and the backup. Verification steps 1 to 4 compare against the manifest, not the live tree.

The undo is stated in advance. Until staging, `evidence/` is untracked, and deleting it and any `evidence.tmp/` is a complete undo that leaves the scratch tree and backup untouched. After staging, unstage by path. The push is the point of no return, because a public PR ref keeps the objects after a squash merge, so every redaction check runs before it.

Two checks need only the committed files, and `findings.md` gives each as a one-statement recipe run from the repository root, with no `$(...)`, brace group or shell loop:
- One pipeline: `find` lists the files under `evidence/`, `xargs -0 sha256sum` hashes them, and `awk` matches each of `freeze-stage1.txt` lines 1 to 41 to a hashed path by its second field and compares digest prefixes. It prints 27 matching, 2 differing by design and 12 not published (row 10). `awk` strips each hashed path through `evidence/` and counts a path absent from the copy as not published. It reads the second field as a literal string, so the `~` on lines 40 and 41 is never expanded and the file count trailing lines 36 and 37 is ignored. It names its fields through `-v` variables, so the recipe holds no dollar sign followed by a digit (Verification step 9).
- A `jq` command over `key.json` and the verdict files recounts the stage-1 bar, under the rule that a run passes only when all five checklist points pass (row 7).

**Report (M4).** `findings.md`, about 130 lines, in this order:
- A header with the date, the pinned commit per Verification step 7, the model and CLI version as frozen, and the invocation (row 19). It states that every run also loaded the author's user-level instruction files, one of which is not in this repository.
- The rule the labels apply, cited as `evidence/labels-v4.md` line 7, not restated.
- The layout map above. It adds that `.rgignore` hides `evidence/` from Grep, and that a Grep rooted at `evidence/` searches it (Verification step 11).
- What is not published, with one reason each (Out of scope). It states that the scripts, manifests and stream logs the records cite are not published.
- The 11 changed files and the three substitution rules.
- The two recipes from M3, each with its expected output. Beside them goes one sentence: the freeze digests match the files as of the commit that adds the report, and `git log` on `evidence/` shows any later change.
- The result, citing the records rather than restating their lists:
  - The first measurement's overall line is FAIL under v3 labels (`score-report-full.txt:16`). `labels-v4.md` line 3 names the four relabels since v3.
  - The stage-1 precondition was met (`stage1-results.md` lines 7 to 10).
  - Stage 1 is NO-GO. P17c7 and P26c4 each passed the REWRITE checklist in 3 of 10 runs against a gate of 7 of 10 (`stage1-results.md` lines 18, 19 and 27), at the packet ids the `jq` recipe prints (row 7).
  - Condition c: control R1 had a clause deleted in 3 of 3 runs (`stage1-results.md` line 44). The reason for the deletion appears only as Verification step 8 records it.
  - Conditions b and d: "candidates N, confirmed M" for each, naming every unconfirmed candidate by run file, as Verification step 8 records them (row 37).
  - Stage 2 never ran.
- The disputed labels P11c2, P11c3, P23c2, P27c3 and P25c2, flagged and not decided at `adjudication.md:109`. The six CONTESTED rows P05c2, P10c3, P21c3, P22c3, P26c3 and P29c4, never scored (row 11). `key.json` lists P10c3, P21c3 and P26c3 as listed-only, and the other three appear only in the labels (row 38).
- The limits:
  - Blinding was partial: each rule file opens "Rule under test" (row 20), and K1 and K2 keep visible `ctl_*` module names.
  - The REWRITE answer rests on two rows (`go-no-go.md:120-122`).
  - Labels changed between measurements, so v3 and v4 scores are not interchangeable.
  - Comments other than docstrings were not measured.
  - The scorer's matcher thresholds were tuned on the same outputs.
- The published figures, one line per engineer answer, per `docs/private-project-redaction.md` § "The owner can authorize one figure, case by case" (row 45). Each line names each figure's file, line and kind, how it was derived, and the engineer's in-session answer with its date. It names figures by location, not value, so `findings.md` publishes no figure a second time. Each line says the figures' inputs, the per-run cost files and frozen scripts, are not published.
  - One line enumerates the three figures at `go-no-go.md` lines 8 and 14 and cites, for now, "Publish unchanged (Recommended)", 2026-11-21 (row 22), as a placeholder that step 17 replaces with one live answer per figure.
  - The stage-1 spend at `stage1-results.md` line 8 cites "Yes, publish it (Recommended)" and 2026-11-21 (row 42), also as a placeholder that step 17 replaces.

**Decision record (M5).** A section headed `## Why the restating bullet is not narrowed to design decisions` goes immediately before the `## Sources` section of `prose-restating-code-is-deleted.md`. It states three facts:
- A rewording that keeps only design decisions with a reason static analysis cannot find was measured on labelled docstrings from this repository, and it failed the bar fixed before its runs.
- The maintainer chose to stop there, so the bullet and `comment-discipline-reviewer` keep their wording.
- The report, linked as `../reports/2026-11-19-comment-docstring-study/findings.md`, holds the evidence, the disputed labels and the limits. `test_design_decision_files.py` resolves each relative link to a file (`:475-476`), so the link names `findings.md`, not the directory.

The section carries no figure and no study label, so the report stays the only home of both. It cites the bullet rather than restating it, per the "Cite, don't restate" bullet of `.claude/rules/design-decisions.md`.

**README row (M6).** One row goes above the existing 2026-11-19 row. It links `findings.md` and gives a one-sentence subject, without figures, naming the labelled docstrings, the reviewer outputs and the blinded adjudication behind the stage-1 result.

**Review scope (M8).** In each per-commit `/code-review`, the session tells every spawned reviewer that `evidence/` is out of scope, to pathspec-exclude it when printing a diff, and to use `--numstat` for it, as `.claude/plans/drop-remaining-home-paths.md` M-5 did for its fixtures. Reviewers review `findings.md`, the README row, the two record edits, `.rgignore` and this plan. `evidence/` is a verbatim copy whose checks are mechanical. This PR's review route is the code-review gates, not `/review-pr` (row 29).

`comment-discipline-reviewer` does not spawn in per-commit rounds. It runs in `/ready-for-review`'s cumulative pass, which reviews the whole diff unnarrowed (row 40). That reviewer has no carve-out for preserved records, so there it would judge 392 reviewer outputs as durable text (row 18). The engineer authorized excluding `evidence/` from that pass for this PR (row 41). Prompt text cannot apply it, because that reviewer and `skill-fidelity-reviewer` read only the diff file they are handed (row 47). So the session writes a second cumulative diff file with `evidence/` pathspec-excluded and a one-line `--shortstat` summary of it, and hands that path to both reviewers in place of the `DIFF_FILE:` path (Verification step 18). `/ready-for-review` step 3 still records the whole diff as the `cumulative-review` subject. After a clean pass, that marker therefore certifies this branch's exact bytes as reviewed under row 41's exclusion, not as reviewed whole. The session records the exclusion and the file's path on the `Spawn decisions` line, which states the deviation from step 3's `DIFF_FILE:` path for step 4's reviewer.

**Arming the redaction gate (M9).** The gate scans nothing in this checkout until a marker exists (G1). Before the gate probe, the session creates `.claude/private-projects-optin` at the worktree root, holding the comment `docs/private-project-redaction.md` § "Opting in another repository" gives, and never stages it (rows 31, 34). It appends the marker's path to the file `git rev-parse --git-path info/exclude` names, as `findings-path-suffix.sh` does for `agent-reviews/`, so `git status` never lists the marker (row 36). Every worktree of this checkout shares that file, and the entry only hides one file name. Without the entry, `/ready-for-review` step 1 would halt on an untracked file. The armed gate then scans the real commit and every later commit and PR command in this worktree. `deny-pii-in-commits.sh` checks only credentials on this machine (row 35), so a direct scan of the staged index covers personal data and, for every class but the blocklist, the lines both gates drop (Verification step 13). Blocklist coverage of those dropped lines, 40 repo-relative path lines by ciso-reviewer's count, is unverified.

**Hiding the evidence from Grep (M10).** `.rgignore` gains the line `docs/reports/2026-11-19-comment-docstring-study/evidence/` (row 30). `plans-hidden-from-grep-not-deleted.md` line 5 says the file lists `.claude/plans/`. That sentence changes to say it lists `.claude/plans/` among the paths it hides, and nothing else in the record changes. No test reads `.rgignore` (row 39).

**Alternatives set aside.**
- **`evals/fixtures/<dir>`.** Each fixture directory there has its own `select-tests.py` constant and predicate, and an unmapped one widens to the full suite with reason `unmatched-path`. It would need a new rule and a `test_select_tests.py` case. Its directories also hold inputs an eval runs against, and nothing runs against this data.
- **`claude/.claude/hooks/tests/fixtures/`, the paragraph-readability precedent.** `claude/` is stowed into every contributor's `~/.claude`. In a checkout its origin URL arms, the redaction gate skips that tree (G1), so a residual detector match there would commit unseen. Its precedent fixture pins live text, which this study lacks.
- **`docs/case-studies/`.** It holds indexed narrative accounts, not data bundles.
- **A tripwire test in the shape of `evals/test_main_session_rule_adherence_fixtures.py`, or a hash-pin of the 27 freeze prefixes.** The tripwire exists because its scrubber is not in the repository, which is also true here. Both are set aside for three reasons:
  - `docs/reports/README.md` says reports are not edited, and no report has a test (row 13).
  - The freeze digests and `git log` already show any later edit, and `findings.md` says so.
  - The engineer chose no tooling, then asked whether a test is needed, and plan-architect advised none (rows 2, 3, 33).
- **Checking the copy against the live scratch tree, or relying on the freeze pre-check.** The freeze covers 29 of the 508 files. A script that edited its source in place would still compare equal to that source. A manifest taken before any script runs, and a backup the script copies from, keep the original out of its reach (M3).
- **Deleting the marker before `/ready-for-review`, or committing it.** Deletion leaves that skill's fix commits and `gh pr create` unscanned, and the engineer chose not to commit the marker (row 31).
- **A restructured layout**, such as `runs/first/` and `runs/stage1/`. It breaks the relative paths cited inside `go-no-go.md`, `adjudication.md` and `freeze-stage1.txt`.
- **Breaking each hex value with a non-hex character, or swapping the home path for a repo-relative one.** The first reads as corruption, and the second hides the substitution. A prefix stays checkable, and a named placeholder reads as deliberate (`.claude/plans/drop-remaining-home-paths.md` § "Approach").
- **A new design-decision file.** The decision is the reason the restating bullet keeps its wording, which is the existing record's subject (row 14).
- **One `code-writer` dispatch.** Critical files gives the split.

No mechanism here is heavier than a checked file copy with three literal substitutions, one untracked marker and one ignore line. The gate probe reuses the real gates rather than re-implementing their detectors (row 24), and the direct scan reads its five regexes from the installed `_lib.sh` rather than retyping them.

### Assumption ledger

**Root:** The study's evidence and its blinded adjudication exist only in a scratch tree on the author's machine and in swept transcripts. A durable public copy needs a home, a layout that keeps the cell-to-run-to-label mapping and the blinding key, and a sanitization that clears the redaction gate while changing nothing it does not name.

**Givens:**
- **G1.** The redaction gate is armed only when the origin URL contains `claude-config` or the worktree root holds `.claude/private-projects-optin`, and neither holds for this checkout. Once armed, it scans every added line of the staged diff except one whose content begins with `++`, and the origin-URL arm also skips `claude/.claude/hooks/tests/**`. Its home-rooted-path and long-hex detectors are always on with no allowlist. Reason: the gate's scope and coverage are gate-design decisions outside this plan (`.claude/plans/drop-remaining-home-paths.md` G-1), and the scope test that misses this checkout is the gate owner's to fix. [verified: `deny-private-project-refs.sh:482-489`, `:630`; `_lib.sh:4953`, `:4956`; ciso-reviewer's read of this checkout's origin URL and `.claude/`, this session]
- **G2.** The scratch tree is the study's only copy, and its findings are model outputs that a re-run would not reproduce. Reason: the vendor owns sampling, and the runs' instruction context included files outside this repository (row 19). [verified: scratch tree read; `freeze-stage1.txt:40-41`]
- **G3.** Autonomous shipping is active for this repository, so the engineer's request to commit these fixtures authorizes the commit, a plain push of this branch and the PR without a further ask. The engineer stated no hold on shipping in the planning session. An engineer-originated restriction on shipping stops step 18 in whatever form it reaches the session (live, handoff or summary), and a line that could be either a hold or a generic not-authorized line is asked about, not proceeded on. Reason: the shipping policy is the harness's and the engineer's, outside this plan. [engineer-verified: "autonomous shipping is active by default not sure why you're asking that"] The quote covers that autonomous shipping is active. [verified: the session-start notice states autonomous shipping is active] [verified: the helper script `autonomous-shipping-active.sh` is absent on this machine, which does not signal a hold]

**Rows:**
1. [engineer-verified: "Evidence, no raw streams (Recommended)"] The commit holds the study's evidence and no stream logs.
2. [engineer-verified: "Data only, no tooling (Recommended)"] No study script is committed.
3. [unverified] The option descriptions behind rows 1 and 2 were the session's own proposal: labels v4, the 35 docstring diffs, the 392 findings files, the 32 verdicts plus key, the go/no-go table, and no `probe/` script. This plan adds evidence files that description did not list: the reviewer bodies and rule files the runs used, the two stage-1 control diffs (37 diffs in all), the 32 blinded packets, `v2-diff.md`, `freeze-stage1.txt`, `score-report-full.txt`, `adjudication.md` and `stage1-results.md`. None is a stream or a script, and counting them within rows 1 and 2 is plan-architect's reading. The plan also reads "Data only, no tooling" as excluding a new test; that reading is plan-architect's, and row 33 records the engineer's agreement that no test is needed.
4. [unverified] "you should definitely plan to commit the fixtures and not defer" reaches this plan through a prior session's handoff, per the `Ask:` line, so it carries no engineer-verified tag.
5. [engineer-verified: "number one"] The engineer chose to stop and record the stage-1 result rather than change the reviewer wording. The option's meaning, and the Hold on `claude/.claude/CLAUDE.md:116` and `comment-discipline-reviewer.md`, are the session's relay on the `Ask:` line.
6. [verified: Grep file and line counts over the scratch tree; `probe/stage1-results.md` read] The 508 files are:
   - 315 run files under `probe/out/` (35 cells, 3 bodies, 3 runs each) and 77 under `probe/out-v2/amended-v2/`;
   - 37 `diff.patch`, 32 packets, 32 verdicts and `key.json` with 32 entries;
   - 6 body and rule files;
   - `labels-v4.md`, `labels.json`, and six stage and baseline records, `stage1-results.md` included.

   Their per-file line counts total 16,040: 15,987 for the other 507 and 53 for `stage1-results.md`.
7. [verified: the verdict files holding `"pass": false`, read against `key.json` under the all-five-points rule at the scratch `probe/adjudication_score.py:61-65`; `stage1-results.md:18-19`; staff-sdet's `jq` recount, this session] Source `amended-v2` passed P17c7 in 3 of 10 runs (p008, p022, p028) and P26c4 in 3 of 10 (p011, p013, p031). Both match the Context.
8. [verified: Grep over the 507 candidates with the `_lib.sh` home-rooted and long-hex regexes, the tracker shape, and approximations of the other three detectors] The findings are:
   - Home-rooted matches sit in 8 run files only, once each, inside a code span, each the author's checkout root.
   - Long-hex matches are the source commit at `labels.json:4` and `score-report-full.txt:1`, and the 41 digests in `freeze-stage1.txt`.
   - The only tracker-shaped token is `UTF-8`, which the allowlist passes (`deny-private-project-refs.sh:512`).
   - The IPv4, SSH-key-path and internal-hostname approximations match nothing.
   - A grep for distinctive terms from the author's unpublished user-level instruction file matched only that file's own name, at `go-no-go.md:102` and `freeze-stage1.txt:41`.
   - A dollar sign followed by a digit appears only at `go-no-go.md` lines 8 and 14 and `stage1-results.md` line 8 (ciso-reviewer's and staff-sdet's greps, this session).

   The blocklist and `deny-pii-in-commits.sh` are left to the gate probe (Verification step 15). Verification steps 5 and 13 repeat the structural checks on the copy and on the staged set.
9. [verified: `_lib.sh:4953`, `:4956`; `docs/private-project-redaction.md:72-73`; `.claude/plans/drop-remaining-home-paths.md` row 8] `/home/<username>/` does not match the home-rooted detector, because `<` is outside its character class. A hex run under 32 characters does not match the long-hex detector.
10. [verified: `freeze-stage1.txt` read] Lines 1 to 41 are digests:
    - 27 name files this plan publishes unchanged (lines 1, 3 to 6, 15 to 35, and 39).
    - 2 name files it changes (lines 2 and 38).
    - 12 name files it does not publish: scripts (lines 7 to 14), tree hashes (36, 37) and user-level instruction files (40, 41).

    Line 42 records the model and CLI version. Lines 36 and 37 end in a parenthesized file count, and lines 40 and 41 begin with `~`.
11. [verified: `probe/adjudication.md:109`; `labels.json`, whose six rows with `"contested": true` are P05c2, P10c3, P21c3, P22c3, P26c3 and P29c4] The five disputed labels are flagged AMBIGUOUS and not decided. The six CONTESTED rows match the Context's list.
12. [verified: `probe/stage1-results.md` read whole] The frozen tools' output after the stage-1 runs is `stage1-results.md`: the precondition at lines 7 to 10, the bar result at lines 18, 19 and 27, and the candidate lists for conditions b, c and d at lines 33 to 49. It holds no home-rooted path, long hex or tracker-shaped token, so M2 leaves it unchanged. Its line 8 carries the stage-1 spend to four decimals (row 42). It is published, so `findings.md` cites it rather than session output.
13. [verified: `docs/reports/README.md`] A report is dated, pinned to a commit in its header, left unedited except for a dated Status section, and indexed by a README row, newest first.
14. [verified: `.claude/rules/design-decisions.md` "No index" bullet; `docs/design-decisions.md` read; `prose-restating-code-is-deleted.md:1-5`] No design-decision index exists, so the exploration's index entry does not apply. `prose-restating-code-is-deleted.md` is the record whose subject is the restating bullet.
15. [verified: `select-tests.py:461`, `:1051`; `test_select_tests.py:1470-1479`; `_skill_md_helpers.py:543-555`; `pyproject.toml:37-42`; `.github/workflows/tests.yml:238`] A `docs/**` path at any depth selects `HOOKS_TESTS_DIR` and `SKILLS_TESTS_DIR`. The state-path contract skips `docs/reports/**`. pytest collects no `.md`, `.json`, `.patch` or `.txt` file, and ruff lints four directories that exclude `docs/`.
16. [verified: `stow-packages.sh:26-29`; a grep of `CHANGELOG.md` for the four existing reports found none] Only `claude/` and `claude-skills/` are stowed, and no existing report has a changelog entry. This change alters nothing a stow user loads, so it gets none.
17. [verified: `test_design_decision_files.py:55-63`; `paragraph-readability.json` read] The paragraph-readability fixture's test pins the shipped angle text's hash.
18. [verified: `comment-discipline-reviewer.md:55-70`; `.claude/plans/drop-remaining-home-paths.md` M-5] The reviewer's scope exempts plan files but not preserved records. The precedent told reviewers to pathspec-exclude a fixture directory.
19. [verified: the scratch `probe/run_probe.py:30`, `:40-43`, `:58-59`; `freeze-stage1.txt:42`] Each run was `claude -p` with the body as an inline agent, at `--model sonnet --effort high`. Amended and ablation runs got `amended-rule.md` appended to the system prompt, amended-v2 runs got `amended-v2-rule.md`, and shipped runs read the rule from the author's installed `CLAUDE.md`. The freeze records model `claude-sonnet-5-5` and CLI `2.1.329`.
20. [verified: `probe/bodies/amended-rule.md:1`, `amended-v2-rule.md:1`] Each appended rule file opens "Rule under test", which the reviewer saw.
21. [verified: the main checkout's `packed-refs` names the source commit as the head of local branch `comment-rule-false-angle-fix`, and no `origin` ref names it] [unverified] Whether `4d2d6ea16136` is reachable from `origin/main`. This repo squash-merges, so it may not be. Verification step 7 decides the pin.
22. [engineer-verified: "Publish unchanged (Recommended)"] `go-no-go.md` lines 8 and 14 carry three dollar figures: a stage-1 cost estimate, a per-run mean and a stage-2 estimate. The engineer selected that label on 2026-11-21 against the question whether those figures may be published. The plan publishes them unchanged, which keeps that file's freeze match. The tag covers those three figures in `go-no-go.md` only. Row 28 covers the Context's spend figure, and row 42 the same spend in `stage1-results.md`.
23. [verified: staff-platform-engineer's byte count of the scratch sources, this session] `evidence/` is about 1.2 MB. Verification step 6 measures the copy.
24. [verified: `.claude/plans/drop-remaining-home-paths.md` § "Verification" step 5] A dry-run probe feeds a staged commit payload to `deny-private-project-refs.sh` and `deny-pii-in-commits.sh`. It carries a home-rooted positive control, a count-only tally of blocklist entries and a reader that prints categories only. Its first sub-step, the origin-URL check, halts in this checkout (G1), so this plan arms the gate with the marker instead (M9).
25. [verified: every cell's frozen module in the scratch tree sits under `claude/.claude/scripts/`, the six controls under its `probe_synthetic/`] The evidence derives from this repository's own files and synthetic controls, so it carries no private-corpus provenance. The report's figures are counts over committed files.

26. [engineer-verified: "Proceed anyway"] The engineer was asked whether to split this plan, which projects about 16,090 changed lines, and selected that label. The tag covers only that answer: the plan stays one PR.
27. [engineer-verified: "findings.md report, Decision-record section, README index row"] The engineer selected all three labels against the question which authored additions (the findings.md report, a section in `prose-restating-code-is-deleted.md`, a `docs/reports/README.md` row) they want in the same PR.
28. Two answers, each with its own coverage:
    - [engineer-verified: "Both confirmed"] The engineer selected that label on 2026-11-21 against the question whether they confirm the `Ask:` line's handoff-relayed quote and the Context's stage-1 spend figure. This tag covers the quote only, because the second answer covers the spend.
    - [engineer-verified: "Yes, keep it in the plan"] On 2026-11-21 the engineer selected that label against the question whether the plan's Context, which ships in this PR, may keep the stage-1 spend value, as the results file does under row 42. This tag covers the spend in the plan's Context only, not in any other artifact (row 42).

    Row 4's `[unverified]` stays only as a record that the quote was relayed.
29. [engineer-verified: "You do realize that review-pr doesn’t need to be run on this PR right? It goes through the code review gates"] This PR's review is `/code-review` per commit and `/ready-for-review`. No `/review-pr` step runs, so `review-pr-diff.sh`'s 300-file ceiling does not bear on this PR.
30. [engineer-verified: "Add to .rgignore (Recommended)"] The engineer selected that label against the question how to keep `evidence/` out of content search. The tag covers listing the evidence path in `.rgignore`.
31. [engineer-verified: "Add the marker, don't commit it (Recommended)"] The engineer selected that label against the question how to arm the redaction gate for this checkout. The tag covers creating `.claude/private-projects-optin` in this worktree and never staging it.
32. [unverified] The option descriptions behind rows 30 and 31 were the session's proposals: the one-sentence edit to `plans-hidden-from-grep-not-deleted.md`, and creating the marker before the gate probe, whose reader prints the blocklist entry count.
32a. [engineer-verified: "Yes, append it (Recommended)"] The engineer selected that label against the question whether to append the marker's path to this checkout's shared `info/exclude` file (M9), which every worktree of the checkout shares. The `info/exclude` entry was plan-architect's addition.
33. [engineer-verified: "Ask the architect. Do we really need a test here?"] The engineer asked whether a test is needed and passed the question to plan-architect. The quote decides nothing. Plan-architect advised no test, because no report has one and the freeze digests and `git log` already show a later edit. The engineer then selected "Agree, no test (Recommended)" against the question whether they agree with that advice, so M7 stands: this plan adds no test. [engineer-verified: "Agree, no test (Recommended)"]
34. [verified: `deny-private-project-refs.sh:478`, `:485`; `docs/private-project-redaction.md:646-647`; `.gitignore` read] A regular file at `.claude/private-projects-optin` under the worktree root arms the gate whatever it holds, and the hook reads it from the working tree. `.gitignore` does not list that path.
35. [verified: `deny-pii-in-commits.sh:10`; ciso-reviewer's check that `pii-patterns.md` is absent, this session] `deny-pii-in-commits.sh` runs only its credential tier on this machine, so its `allow` says nothing about names, emails or other personal data.
36. [verified: `findings-path-suffix.sh:27`; `_review-ledger-lib.sh:1109`; `ready-for-review/SKILL.md:43`] The repo already appends `agent-reviews/` to the file `git rev-parse --git-path info/exclude` names, and tells the session to add that line by hand when the script cannot. `/ready-for-review` step 1 requires a working tree with no untracked file.
37. [unverified] The Context's hand-read outcomes are session relays: that R1's deleted clause was an unsourced claim, and that no DELETE-row harm was confirmed beyond one P17c1 run. `stage1-results.md` lists the candidates but records no hand read. Verification step 8 re-reads every candidate's run files.
38. [verified: `key.json:204-208`] `key.json`'s `listed_only_rows` names P10c3, P21c3 and P26c3. P05c2, P22c3 and P29c4 are CONTESTED in `labels.json` only.
39. [verified: the rule table at `select-tests.py:742-1066`, `:1110-1111`, `:1167`; a grep of the repo for `rgignore`] No rule names `.rgignore`, so a change to it selects the full suite with reason `unmatched-path`. Untracked files count unless the standard excludes hide them. Only `evals/README.md:465` and `plans-hidden-from-grep-not-deleted.md` mention `.rgignore`, and no test reads it.
40. [verified: `code-review/SKILL.md:38-52`, `:404-410`; `ready-for-review/SKILL.md:68`, `:87-91`; `pr-diff-against-base.sh:21`] In a staged-diff `/code-review` on this branch, the comment-discipline row does not spawn. It runs in `/ready-for-review` step 3, which reviews the whole PR diff with no narrowing, and `pr-diff-against-base.sh` takes no pathspec. The closed DEFER list has no criterion for a finding on a preserved record. `/ready-for-review` step 2 skips a diff with no executable code.
41. [engineer-verified: "Exclude evidence/ for this PR (Recommended)"] The engineer selected that label against the question how the final whole-PR review treats `evidence/`. The tag covers applying M8's exclusion of `evidence/` in `/ready-for-review`'s cumulative pass for this PR only (row 40); the session records it on the `Spawn decisions` line.
42. [engineer-verified: "Yes, publish it (Recommended)"] The engineer selected that label against the question whether `stage1-results.md` may be published with the stage-1 spend at four decimals on its line 8. It is a fresh ask per row 45, answered in this session on 2026-11-21; `findings.md` cites it beside the figure by file and line, not by value.
42a. [engineer-verified: "Keep it, run the full suite once (Recommended)"] The engineer selected that label against the question whether to keep the `.rgignore` change given that `select-tests.py` then selects the full suite (row 39). The tag covers keeping the change and running the full suite once before the commit. The plan reads "once" as one local run after the last edit to any staged file, with any later edit, `/ready-for-review` fix commits included, left to CI's full-suite run (Verification step 16). That reading is plan-architect's, flagged here for the engineer.
43. [verified: `require-diff-size-prompt.sh:4-10`, `:47-49`, `:99-102`] The diff-size gate denies a commit whose cumulative diff, `.claude/plans/` excluded, reaches 400 changed lines. It keeps denying until the engineer answers `Proceed anyway` and `diff-size-ack.sh` writes the branch's latch. A `code-writer` running the ack is denied. The prompt comes after the `/code-review` round, and a question asked in prose rather than through `AskUserQuestion` can be pushed past.
44. [verified: a Glob of the scratch `probe/` ordered by modification time; staff-platform-engineer's timestamps, this session] The scratch tree is still being written. After `freeze-stage1.txt`, `probe/` gained `manifest-stage1.json`, `stage1-run.log`, `record_stage1_results.py` and `stage1-results.md`, and only the last is a record this plan publishes.
45. [verified: `docs/private-project-redaction.md:199-230`] A figure the owner releases is cited beside it, naming the proposal and the time of an in-session yes. The same figure in a different artifact is a fresh ask, and each figure is cited on its own.
46. [verified: the 31 scratch `probe/cells/P*/meta.json` files read; staff-sdet's read-only `git` runs, this session] The 31 real cells reviewed 18 distinct modules under `claude/.claude/scripts/`, and each cell records its module's `module_sha256`. `4d2d6ea16136` is not an ancestor of `origin/main`. The `origin/main` commit that added the study's plan differs from it in three scripts outside those 18 and in none of the 18. [unverified] Each recorded digest equals its module at the pinned commit; Verification step 7 checks it.
47. [verified: `code-review/SKILL.md:303`; `ready-for-review/SKILL.md:83`, `:91`, `:106-107`; `pr-diff-against-base.sh:29-37`; `comment-discipline-reviewer.md:30`, `:32`; `skill-fidelity-reviewer.md:20`] `/code-review` reviews whatever path follows `unrouted`, and `/ready-for-review` step 4 hands `skill-fidelity-reviewer` a literal diff path. Both reviewers read only that file, and `comment-discipline-reviewer` sets aside a prompt-text exclusion. `--record` records the whole cumulative diff as the `cumulative-review` subject, whatever file the reviewers read.
48. [verified: `.github/workflows/tests.yml:43`, `:228`, `:233`; `README.md:589-595`; `select-tests.py:1111`, `:1180`, and no `timing` in it] CI caps its parallel leg at 30 minutes and runs the `timing` tests in a separate `-n0` leg. `select-tests.py` applies no `timing` filter, sizes `PYTEST_XDIST_AUTO_NUM_WORKERS` from the 1-minute load average unless the variable is set, and gives its full-suite fallback the reason `unmatched-path`.
49. [verified: a Grep of the four modified repo files and this plan for URL- and email-shaped tokens, this session] `prose-restating-code-is-deleted.md` already holds 7 matches and the others none, so the staged scan reads a modified file's added lines only.
50. [unverified] This machine has GNU `env -C` (coreutils 8.28 or later) and GNU `xargs -a` and `-d`. A missing option fails Verification step 0's first such call, which stops the plan.
51. [engineer-verified: "Yes, one account"] On 2026-11-21 the engineer selected that label, which `findings.md` cites as confirming that every run behind the four published figures used one account on this repository's own files. This plan does not record the question text. The composition check that `docs/private-project-redaction.md` § "The owner can authorize one figure, case by case" requires found no composition path, because the four figures are run cost, not review-round share. [verified: ciso-reviewer's read of that section and of the four figures, this session]

**Mechanisms:**
- **M1. Copy the 508-file allowlist into `evidence/`, keeping scratch-relative paths.** anchors: root, row1, row3, row6, row12, row13, row25, row44.
- **M2. Make three literal substitutions, each count-asserted.** anchors: G1, row8, row9, row10, row12, row22.
- **M3. Fix the sources with a manifest and a backup before any script runs, build the copy from the backup under a temporary name, check it against the manifest once before commit, and give readers two recipes that need only committed files.** anchors: G2, row2, row7, row10, row24, row44, row46, row50.
- **M4. `findings.md` maps the layout and records the result, the disputes, the limits and each published figure's authorization.** anchors: row5, row7, row11, row12, row13, row19, row20, row21, row22, row25, row28, row37, row38, row42, row45, row51.
- **M5. Add one section to `prose-restating-code-is-deleted.md`, with no figure.** anchors: row5, row14.
- **M6. Add one `docs/reports/README.md` row.** anchors: row13.
- **M7. Add no test, script, `select-tests.py` rule, `pyproject.toml` change or changelog entry.** anchors: row2, row3, row15, row16, row17, row33, row39, row42a, row48.
- **M8. Keep `evidence/` out of per-commit `/code-review` scope, and out of the cumulative pass through an evidence-excluded diff file.** anchors: row18, row29, row40, row41, row47.
- **M9. Arm the redaction gate with an untracked marker that an `info/exclude` entry hides, probe the gate, and scan the staged bytes directly.** anchors: G1, row24, row31, row32, row34, row35, row36, row49.
- **M10. List the evidence path in `.rgignore` and correct one sentence of the plans record.** anchors: row30, row32, row39.

## Critical files

- **Create** `docs/reports/2026-11-19-comment-docstring-study/evidence/`, exactly these 508 files (M1), 11 of them changed per M2 (dispatch 1):
  - `labels-v4.md`;
  - `probe/labels.json`;
  - `probe/go-no-go.md`, `probe/v2-diff.md`, `probe/freeze-stage1.txt`, `probe/score-report-full.txt`, `probe/adjudication.md` and `probe/stage1-results.md`;
  - `probe/bodies/` `shipped.md`, `amended.md`, `ablation.md`, `amended-v2.md`, `amended-rule.md` and `amended-v2-rule.md`;
  - `probe/cells/*/diff.patch`, 37 files;
  - `probe/out/{shipped,amended,ablation}/*/run{1,2,3}.md`, 315 files;
  - `probe/out-v2/amended-v2/*/run*.md`, 77 files;
  - `probe/adjudication/packets/p*.md` and `probe/adjudication/verdicts/p*.json`, 32 each;
  - `probe/adjudication-key/key.json`.
- **Create** `docs/reports/2026-11-19-comment-docstring-study/findings.md` (M4, dispatch 2).
- **Modify** `docs/reports/README.md`: one table row (M6, dispatch 2).
- **Modify** `docs/design-decisions/prose-restating-code-is-deleted.md`: one section before its Sources section (M5, dispatch 2).
- **Modify** `.rgignore`: one added line (M10, dispatch 2).
- **Modify** `docs/design-decisions/plans-hidden-from-grep-not-deleted.md`: one sentence on line 5 (M10, dispatch 2).
- **Not modified:** `CHANGELOG.md`, `claude/.claude/scripts/select-tests.py`, `claude/.claude/scripts/tests/test_select_tests.py`, `pyproject.toml`, `claude/.claude/CLAUDE.md`, `claude/.claude/agents/comment-discipline-reviewer.md`, `claude/.claude/hooks/deny-private-project-refs.sh`, and every test.
- **Not created in the repo, never staged:**
  - the copy script, the direct scan `scan.py` and its control fixture, the pin check's `at-<candidate>/` extract and the evidence-excluded cumulative diff file (M8), under `~/.local/state/comment-cells-2026-11-19-publish/`;
  - the backup, with its `paths.txt`, `manifest.sha256` and `modules.sha256`, under `~/.local/state/comment-cells-2026-11-19-backup/`;
  - the gate-probe payloads;
  - `.claude/private-projects-optin`, which the `info/exclude` entry keeps out of `git status` (M9).
- **Reuse:**
  - the gate probe in `.claude/plans/drop-remaining-home-paths.md` § "Verification" step 5;
  - the `<username>` placeholder from `docs/private-project-redaction.md`;
  - the marker comment in `docs/private-project-redaction.md` § "Opting in another repository";
  - the `info/exclude` append that `findings-path-suffix.sh:27` makes;
  - the scratch `probe/adjudication_score.py`, run read-only against the committed key and verdicts as a cross-check (Verification step 10);
  - the existing `docs/**` rule in `select-tests.py`.
- **Dispatch: the session's step 0, then two sequential `code-writer` dispatches (`model: sonnet`), then the session.**
  - **The session runs Verification step 0 first**, so the manifest and backup exist before any script written for this change runs. A denied write there stops the plan with a report, because a dispatch would inherit the denial.
  - **Dispatch 1 covers `evidence/` only (M1 to M3).** Its inputs are this plan and the backup path. It writes the copy script and `scan.py`, runs Verification steps 1 to 6, and returns their outputs. It never `Read`s a run file and prints only counts, booleans and paths. Its self-review uses `git status` counts for `evidence/`, because 392 run files would flood its context. A denied write, inside or outside the repository, stops it with the denial reported verbatim.
  - **Dispatch 2 covers the five authored edits (M4 to M6, M10).** Its inputs are this plan and dispatch 1's return, which the session relays. It runs Verification steps 7 and 8 before writing the header and the result, then steps 9 and 10.
  - The two file sets are disjoint, and each prompt can be written without the other's background: dispatch 1 needs the allowlist and the substitution rules, and dispatch 2 needs the study's result, disputes and limits. Dispatch 2 consumes dispatch 1's counts and check results, so the two run in sequence.
  - **The session** runs Verification steps 11 to 18, M9 included.

Projected diff: about 16,180 changed lines: 16,040 added in `evidence/` (row 6; the substitutions change no line count), about 130 in `findings.md`, about 5 in the record section, 1 each in `docs/reports/README.md` and `.rgignore`, and 2 in `plans-hidden-from-grep-not-deleted.md`, one line replaced.

## Verification

- Every Bash call is one statement with no `$(...)`, brace group or shell loop, run from the worktree root. A command that must run in another directory uses `env -C <dir>` with absolute paths, so no call relies on a persisted cwd.
- `<report>` stands for `docs/reports/2026-11-19-comment-docstring-study`, `<scratch>` for `~/.local/state/comment-cells-2026-11-19`, `<backup>` for `~/.local/state/comment-cells-2026-11-19-backup` and `<tools>` for `~/.local/state/comment-cells-2026-11-19-publish`.
- Steps 0 to 6 and 13 to 15 print only counts, booleans, paths or category labels, never a removed value.
- The engineer's answers on rows 33, 41 and 42 are recorded. G3 covers the commit, push and PR. One live answer is pending: the figures' in-session yes in the executing session (step 17).

0. **Manifest and backup** (session, before dispatch 1, M3). Each bullet is its own Bash call, and a denial or nonzero exit stops the plan with a report. No script runs in this step (row 50).
   - `mkdir <backup>`, which fails if it already exists.
   - `find <scratch> -type f -printf '%P\n'`, filtered by an anchored `grep -E` of the Critical files patterns and sorted, writes `<backup>/paths.txt`. Its per-category counts are 315 under `probe/out/`, 77 under `probe/out-v2/`, 37 under `probe/cells/`, 32 packets, 32 verdicts, 6 under `probe/bodies/` and 9 single files, 508 in all. Any other count stops before dispatch 1, because the scratch tree changed (row 44).
   - `env -C <scratch> xargs -d '\n' -a <backup>/paths.txt sha256sum > <backup>/manifest.sha256` writes the manifest, with paths relative to `<scratch>`.
   - `env -C <scratch> xargs -d '\n' -a <backup>/paths.txt cp --parents -t <backup>` makes a plain copy with no links.
   - `env -C <backup> sha256sum -c --quiet manifest.sha256` exits 0.
   - `jq -r` over `<scratch>/probe/cells/P*/meta.json`, printing each cell's `module_sha256`, two spaces and `module`, piped through `sort -u`, writes `<backup>/modules.sha256`. It holds 18 lines, one per module (row 46). More lines mean two cells recorded different digests for one module, which stops the plan.
1. **Freeze pre-check** (dispatch 1, inside the copy script, before copying). For the 29 freeze lines that name a file this plan publishes (lines 1 to 6, 15 to 35, 38 and 39), each backup file's sha256 equals its frozen digest. A mismatch stops the copy and goes into the return: that file changed after the freeze, and `findings.md` must say so.
2. **Copy and substitute** (dispatch 1, M1 to M3). The script reads `<backup>` only and builds under `<report>/evidence.tmp/`. Every count assertion passes: 8 home-prefix matches across 8 files, 1 source-commit match in each of 2 files, and 41 digest lines. Only then does it rename `evidence.tmp/` to `<report>/evidence/`.
3. **Inventory.** The set of file paths under `<report>/evidence/`, relative to it, equals the manifest's path set. Equality rules out every stream, cost file, `meta.json`, script and `frozen/` path.
4. **Fidelity.** Against the manifest, 497 `evidence/` files have equal digests and exactly the 11 M2 files differ. Each of the 11 differs from its backup copy on 1 line, except `freeze-stage1.txt`, which differs on 41. Then `sha256sum -c --quiet` of the manifest, run through `env -C`, exits 0 from both `<scratch>` and `<backup>`, so neither source changed.
5. **Direct scan of the copy** (dispatch 1). `<tools>/scan.py` reads a directory's files, the staged index (step 13), every commit and commit message in a range (`--range <base>..<tip>`, step 18), or one text file or stdin. In range mode it reads each commit's own added lines (a created file whole, a modified file's added lines only) and its message. It prints counts, paths and line numbers, never matched text, and the number of files it read. An unreadable or undecodable file fails the run instead of being skipped. Its classes:
   - the five `_lib.sh` structural regexes (`:4940`, `:4950`, `:4953`, `:4956`, `:4981`), read at run time from the installed `~/.claude/hooks/_lib.sh` the hooks run, and matched with `grep -E`;
   - whole-word, case-insensitive occurrences of the account's username, which it asserts equals the home directory's basename;
   - email-shaped and URL-shaped tokens;
   - `[A-Z]{2,}-[0-9]+` tokens outside the hook's `OSS_ALLOWLIST`;
   - a dollar sign followed by a digit, allowed only at `probe/go-no-go.md` lines 8 and 14, `probe/stage1-results.md` line 8, and this plan's Context (rows 22, 28, 42). Any other location stops the run.

   No zero count is accepted until two controls pass. Over `<backup>`, it reads 508 files and reports exactly row 8's hits: 8 home-rooted lines in 8 files, with the username on those 8 lines; long hex at `labels.json:4`, `score-report-full.txt:1` and `freeze-stage1.txt` lines 1 to 41; no off-allowlist tracker token; and the three allowed dollar lines. Over a fixture under `<tools>` holding one positive for each other class, it reports 1 per class. Range mode has its own control: a scratch repository under `<tools>` with an add-then-remove commit, a message-only hit, a hit in a non-tip commit and a merge commit. It must report each hit, stop on the merge, and read a commit count equal to `git rev-list --count` of the range. Then over `evidence/` it reads 508 files and reports 0 in every class but the allowed dollar lines. It reads files, not diff lines, so it also covers the lines both gates drop (G1).
6. **Size.** `du -sh` of `evidence/` goes into dispatch 1's return (row 23).
7. **Pin** (dispatch 2, row 46). Each command is its own Bash call, and a hash passes between calls as a literal.
   - Run `git fetch origin`, then `git merge-base --is-ancestor 4d2d6ea16136 origin/main`. Exit 0 makes `4d2d6ea16136` the candidate. Otherwise `git log origin/main --diff-filter=A --format=%h -- .claude/plans/comment-rule-false-angle-fix.md` prints the `origin/main` commit that added that plan, which becomes the candidate.
   - `mkdir <tools>/at-<candidate>`, then `git archive <candidate> claude/.claude/scripts | tar -x -C <tools>/at-<candidate>`, then `env -C <tools>/at-<candidate> sha256sum -c --quiet <backup>/modules.sha256`. Exit 0 shows each module the real cells reviewed is byte-identical at the candidate, so the header pins the candidate, and a main commit pin also names `4d2d6ea16136` as the commit the study recorded. The check covers those 18 modules, not the whole scripts directory, where unrelated files differ between the two commits.
   - Any other result stops dispatch 2 with a report to the session, because the pin is then the engineer's call.
8. **Candidate reads** (dispatch 2, rows 12, 37). It first confirms, from the scratch `probe/stage1_compare.py` read-only, which run tree the file lists at `stage1-results.md:33-49` are relative to. Then it reads every candidate's run files, in their `evidence/` copies:
   - Condition b: P01c1, P01c2, P01c4 and P17c1 from their listed files, and the other flips P08c1, P08c2 and P08c3 from the P08 cell's runs 1 to 3.
   - Condition c: the one K1 edit, and R1's runs 1 to 3. For R1 it records each run's finding line that deletes the clause and the reason that run gives. Without those, `findings.md` states only the count of 3 of 3 deleting runs.
   - Condition d: P27c1 and P27c5 from their listed files.

   The return lists, per condition, the candidates, the confirmed ones and each unconfirmed one by run file. `findings.md` reports "candidates N, confirmed M" in the same terms and claims no more. A reading that contradicts the Context's relayed outcome stops the dispatch with a report before the result is written.
9. **Authored text** (dispatch 2). The session reruns steps 9 and 10 after the last edit to `findings.md`, the README row, the record section or `.rgignore`.
   - Every `evidence/` path and file:line that `findings.md` cites exists, each line number within its file.
   - The disputed and CONTESTED ids in `findings.md` equal those at `adjudication.md:109` and in `labels.json`. Its listed-only ids equal `key.json`'s `listed_only_rows`. Any label tally counts CONTESTED as a flag on six of the 101 rows, not a category of its own.
   - `scan.py`'s dollar class finds nothing in `findings.md`, which carries one authorization line per engineer answer (M4).
   - The record section has no count, rate or study label, and its link is exactly `../reports/2026-11-19-comment-docstring-study/findings.md`.
   - The README row's link resolves to `findings.md`, and the row sits immediately above the existing 2026-11-19 row.
   - `.rgignore` gains exactly one line, and `plans-hidden-from-grep-not-deleted.md` differs on one line.
   - After step 17's rewrite, and not at dispatch 2's first run, each figure line in `findings.md`'s "Published figures" section cites exactly one answer, given in the executing session, with a date and time.
10. **Recipes** (dispatch 2). It copies each recipe from `findings.md` word for word into one Bash call and runs it from the worktree root. If the guard refuses one, the form that runs replaces it in `findings.md`, so the file carries the text that last ran.
    - The freeze recipe reports 27 matching, 2 differing and 12 unpublished lines.
    - The `jq` recipe reports P17c7 passing 3 of 10 at p008, p022 and p028, and P26c4 passing 3 of 10 at p011, p013 and p031.
    - As a cross-check, `python3 -I ~/.local/state/comment-cells-2026-11-19/probe/adjudication_score.py --key <report>/evidence/probe/adjudication-key/key.json --verdicts <report>/evidence/probe/adjudication/verdicts --threshold 7` prints a line beginning `[amended-v2] P17c7: FAIL  pass 3, fail 7, pending 0` and a line beginning `[amended-v2] P26c4: FAIL  pass 3, fail 7, pending 0`. It prints no "Verdict files with problems" block and ends with `REWRITE bar (amended-v2): FAIL`, as `stage1-results.md` lines 18, 19 and 27 record.
11. **Grep check** (session, M10). The Grep tool, rooted at the worktree, finds no file under `evidence/` for `"packet_id": "p008"`. Rooted at `<report>/evidence`, its results include `probe/adjudication/verdicts/p008.json`.
12. **Stage and review** (session). Each `git add` is its own call: `<report>`, `docs/reports/README.md`, `docs/design-decisions/prose-restating-code-is-deleted.md`, `docs/design-decisions/plans-hidden-from-grep-not-deleted.md`, `.rgignore` and `.claude/plans/comment-reviewer-docstring-fixtures.md`.
    - `git diff --cached --name-only | wc -l` prints 514.
    - `git diff --cached --numstat -- . ':(exclude)docs/reports/2026-11-19-comment-docstring-study/evidence'` lists exactly the six authored files.
    - Run `/code-review` on the staged diff with M8's scope text. Restage any fix by path and repeat both counts.
13. **Direct scan of the staged index** (session, M9). `scan.py` reads index blobs, not the working tree: each created file whole, and each modified file's added lines only (row 49). It reads 514 files and reports what step 5 reports for `evidence/`, plus the plan's one allowed dollar location, its Context. A nonzero count elsewhere stops the commit, and the report names only the class and the path. This step and the step-15 probe rerun after any restage and before every commit, `/ready-for-review` fix commits included.
14. **Marker** (session, M9). Each bullet is its own call, and a denied write stops with a report.
    - Create `.claude/private-projects-optin` holding the comment from `docs/private-project-redaction.md` § "Opting in another repository".
    - `git rev-parse --git-path info/exclude` prints the exclude file's path. `tail -c1` on that path, piped to `od -An -tx1`, prints `0a`; otherwise the session first appends a newline, as `findings-path-suffix.sh:31-32` does. It then appends the line `.claude/private-projects-optin`.
    - `git status --porcelain --ignored -- .claude/private-projects-optin` shows the marker as ignored (`!!`), and `git diff --cached --name-only | wc -l` still prints 514.
    - Both stay until the PR merges, so fix commits and `gh pr create` stay scanned. The marker then leaves with the worktree when the engineer removes it. The `info/exclude` line is deliberately left, because it hides one file name and a stale marker can only add denies.
15. **Gate probe** (session, row 24). Run the probe from `.claude/plans/drop-remaining-home-paths.md` § "Verification" step 5 against this staged set, for `deny-private-project-refs.sh` and `deny-pii-in-commits.sh`. Step 14's marker replaces its origin-URL check. Keep its scratch payloads, home-rooted positive control, category-only reader and blocklist entry tally.
    - The positive control returns `deny` with label `home-rooted path`. Otherwise halt, because the gate is not armed.
    - Both hooks return `allow` on the real payload. `deny-pii-in-commits.sh`'s `allow` counts for credentials only (row 35). Each hook's wall time on the real payload is recorded with the result.
    - The reader prints the blocklist's entry count, read from the file the hook reads (`deny-private-project-refs.sh:946-949`).
    - Stop before any commit and report "blocklist tier unverified" unless the reader prints a positive integer. A missing or unreadable blocklist file, a reader error and a missing count each stop it too. The reader runs with the same `CLAUDE_CONFIG_DIR` that the commit's Bash call has.
    - Then wait for the engineer's in-session reply.
    - The reply may accept proceeding for the `evidence/` files, because those records derive from this repo's own files (row 25). The authored files rest on the engineer's reply alone, because the blocklist is the only detector for private names in prose.
    - On a `blocklist`, `tracker-ID` or structural result, stop and report the category only.
16. **Tests** (session, once, after the last edit to any staged file, row 42a). `select-tests.py` selects the full suite with reason `unmatched-path`, naming `.rgignore` (row 39), so nobody narrows or widens the run by hand.
    - Run `timeout 30m scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py` in the background. The bound is CI's 30-minute cap on its parallel leg (`.github/workflows/tests.yml:43`). `PYTEST_XDIST_AUTO_NUM_WORKERS` stays unset, so the selector sizes workers from the 1-minute load average (`README.md:589`). Record the worker count and reason line it prints on stderr with the result.
    - On hitting the bound, report that and defer to CI's full-suite run.
    - On red, list the failing test ids. A failing `timing`-marked test reruns its file alone with `-m timing -n0`, CI's shape at `tests.yml:233`, which is not a second full run. Any other failure is reproduced at the merge-base before it is claimed or fixed.
    - An edit after this run is covered by CI's full-suite run, not a second local run (row 42a).
    - Report the missing `.rgignore` rule to the engineer as a rule-table gap.
17. **Commit** (session). G3 applies: the commit runs under autonomous shipping.
    - The diff-size gate denies the first attempt, because the staged diff is far above 400 changed lines (row 43). The session, not a dispatch, asks the engineer through `AskUserQuestion`. On `Proceed anyway` it runs `~/.claude/scripts/diff-size-ack.sh` itself, then retries the commit.
    - In the same `AskUserQuestion` call, and before the first commit, the session asks one more question: may each of the figures at rows 22, 28 and 42 be published. For each figure, the question shows the engineer its value, its file and line, and the command that produced it, and it carries one answer option set per figure rather than one combined yes. `docs/private-project-redaction.md` counts only a live answer in the current session, and the answers behind those rows came from the planning session. The engineer's reply is the live yes. Without it, the commit does not run.
    - Before the commit, the session replaces the engineer's-answer clause on each figure line of `findings.md`'s "Published figures" section with that figure's live answer: its label and the date and time of the yes.
    - The Context's figure (row 28) is covered by the same live question, and the session records its live answer in that same section.
    - Those lines name the file and line and no value, as they do now.
    - The session then restages `findings.md` by path and reruns steps 9, 10 and 13, so the commit holds the rewritten bytes.
    - The commit message quotes no removed value: not the home prefix, the full study commit or a full digest. It carries no dollar figure from this study, which rows 22, 28 and 42 authorize only at their named locations. It keeps absolute paths out of the command line (`.claude/plans/drop-remaining-home-paths.md` M-6).
    - The message avoids the words `source`, `eval` and `xargs` and the phrases `bash -c` and `python -c`, which `deny-invisible-commit-content.sh:289-297` denies anywhere in a commit command.
18. **Push and PR** (session). G3 applies: a plain push of this branch, never a force-push. In order:
    1. Run the pre-push check below.
    2. Push the branch, and stop with a report if the push is denied.
    3. Run `/ready-for-review`, which opens the PR.
    - A hold the engineer states before the push stops this step, because a hold outranks G3 (G3 lists the forms).
    - **Pre-push check.** Print `git rev-parse HEAD` as `<sha>`, then run `scan.py --range origin/main..<sha>` with step 13's classes and dollar locations (step 5 lists them).
      - The push names that commit, as `<sha>:refs/heads/<branch>`. If HEAD has moved, the check reruns.
      - Range mode reads each non-merge commit's own added lines and its message, so a commit that adds content and a later one that removes it are both read.
      - A merge commit in the range stops with a report, because its conflict lines sit in no parent. This plan makes none.
      - Range mode ignores the harness-required `Co-Authored-By` trailer line with a `noreply` address in a message. Every other email or URL hit stops.
      - Paths and author and committer headers are not read. An undecodable file fails the run (step 5).
      - On any hit, stop before the push with a report naming only the class and location. The engineer decides the remedy, whether or not the commit was pushed.
    - The check runs before every push from this worktree: the first push, each `/ready-for-review` step 6 fix push (the session runs it just before that step), and every later push, `/respond-pr` pushes included.
    - The push is the point of no return (M3).
    - `/ready-for-review` step 2 skips, because the diff holds no executable code (row 40).
    - Its steps 3 and 4 read M8's file. Write `<tools>/cumulative-no-evidence.diff` after step 3's `pr-diff-against-base.sh --record --diff-file > /dev/null`, with these two commands in order:
      1. `git diff --shortstat origin/main...HEAD -- <report>/evidence > <tools>/cumulative-no-evidence.diff`
      2. `git diff origin/main...HEAD -- . ':(exclude)<report>/evidence' >> <tools>/cumulative-no-evidence.diff`
    - The file's path goes to `/code-review` as `unrouted <path>`.
    - The same path goes to `skill-fidelity-reviewer` as the diff path.
    - The `Spawn decisions` line names the file's path and row 41.
    - A fix commit follows steps 13 and 17 before `/ready-for-review` step 6 pushes it.
    - The PR body and the review-ledger block follow step 17's rules on removed values and dollar figures. Before every PR create and PR body edit, from this worktree and `/respond-pr` included, `scan.py` reads the body file and the output of `~/.claude/scripts/review-ledger.sh render`, with the harness-required `Generated with Claude Code` link line ignored. A hit stops with a report naming its class and location.
    - Both checks run for as long as `.claude/private-projects-optin` exists.

## Out of scope

- **Stream logs, per-run cost files, run prompts, manifests and run logs** (row 1), `manifest-stage1.json` and `stage1-run.log` included. Each prompt names only a diff path and an output path.
- **Every study script**, including `adjudication/scripts/mk.py`, `record_stage1_results.py`, the copy script and `scan.py` (row 2).
- **A test that reads `evidence/`** (Alternatives set aside, rows 3, 33). If the engineer asks for one, the hash-pin `test_design_decision_files.py` applies to `paragraph-readability.json` is its smallest template.
- **`/review-pr` and its 300-file ceiling** (row 29).
- **A `select-tests.py` rule for `.rgignore`.** Verification step 16 reports the gap, because a rule and its test case would widen this change into the selector (M7).
- **The redaction gate's origin-URL scope test, which misses this checkout.** It is the gate owner's to fix (G1), and the marker covers this worktree only.
- **Scan classes for SSN-, card- or phone-shaped digit runs.** No active detector covers them on this machine (row 35), and the records derive from this repository's own files and synthetic controls (row 25).
- **`claude/.claude/CLAUDE.md:116` and `comment-discipline-reviewer.md`** (row 5).
- **Frozen module copies, `snapshot/` and each cell's `meta.json`.** The real modules are at the pinned commit (Verification step 7). The six synthetic modules are 3 to 13 lines, and their diffs show most of each. `meta.json` repeats the cell directory name and the diff's path, and adds a 64-character module digest.
- **The labellers' and reviewers' drafts, the pilot and cost notes, `labels-v3.md`, and the unfrozen `labels-*.json` copies.** `labels-v4.md` carries each labeller's verdict per row and names its four relabels, and `probe/labels.json` is the frozen copy.
- **Stage 2 and the unused `ablation-v2.md` body.** Stage 2 never ran.
- **A changelog entry** (row 16).
- **Re-scoring or re-running anything.** The result is recorded as measured.
- **The plan's Context**, which this region does not edit. Row 28 covers its spend figure.
