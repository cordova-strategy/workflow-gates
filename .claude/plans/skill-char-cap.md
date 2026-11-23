# Skill character cap grounded in post-compaction re-injection

## Context

Goal: replace `check-skill-length.sh`'s line cap with a character cap set by Claude Code's post-compaction skill re-injection limit, so a skill that passes the gate is not cut by the per-skill re-injection limit after a compaction.

Ask: "plan to chagne check-skill-length to a character cap, and explain why that cap is there (the compaction injection thing you found, ground that in a primary source), then have ratchets or whatever for the existing skills so they don't go red immeiately and then a master issue to reduce the length of all of these skills (which may involve splitting them out into sub-skills that require forced reads or something). And I'd like to prioritize the length reduction by how often skills get reinjected."

Why now: When Claude Code compacts a session, it re-attaches each previously invoked skill and cuts any body past 5,000 estimated tokens (chars/4) to exactly 20,000 characters. It also drops whole skills, oldest first, once the re-attached set passes 25,000 estimated tokens. The current line cap does not track this limit. `review-pr/SKILL.md` passes at 199 lines but is 32,814 characters, and five skills are cut on every re-injection today. `/ready-for-review` shows the cost: its "CI watch (out-of-band)" section starts about 25,600 characters into its `SKILL.md`, past the cut, so a session that compacts mid-review loses the steps that launch the watch. `head -n 175 claude-skills/skills/ready-for-review/SKILL.md | LC_ALL=C tr -d '\200-\277' | wc -c` prints 25,584.

Evidence gathered before planning:

- **Bundle reading.** In the Claude Code 2.1.330 bundle, the compaction path defines a 5,000-token per-skill limit and a 25,000-token total budget. Its token estimate is `round(chars/4)`. A first load is never cut.
- **Probe.** A local probe ran a single-process `claude -p --input-format stream-json` session followed by `/compact`.
  - A 40,000-character skill came back as exactly 20,000 characters, ending in the truncation marker.
  - Of six 19,000-character skills, the five newest came back intact and the oldest was dropped.
  - The re-attached text strips the frontmatter and prepends `Base directory for this skill: <abs dir>` plus a blank line, and that prefix counts toward the 20,000.
- **Re-injection frequency.** Nothing in the repository measures how often each skill is re-attached. The `skill-reinjection` subcommand this plan adds is the measurement, and the publication instrument under `docs/private-project-redaction.md` § "Publishing a tooling measurement".

## Approach

`check-skill-length.sh` caps every gated `SKILL.md` at 19,000 characters, counted over the whole file. The 25,000-token total budget can still drop a whole skill, which no per-file cap can prevent. Over-cap files keep today's ratchet: they may shrink or hold, never grow. `plan-review/ROUTING.md` and `pr-description/DEFAULT_TEMPLATE.md` keep their line caps. A new `transcript-analysis.py skill-reinjection --this-repo` subcommand counts how often each skill is re-attached and cut, under the publication scope refusal. A hand-run eval under `evals/` re-measures the cut. After the subcommand merges, the session files one GitHub issue that lists every over-cap skill, those cut today first, each group most re-attached first. The work ships as four PRs, merged one after another (M9).

`_lib_staged_length_gate` learns the unit from `limit_for`'s output, so `check-claude-md-length.sh` needs no edit. One new design-decision file is the only home for why the cap exists and why it is 19,000. `docs/skills.md`, `docs/hooks.md`, `docs/handoff-nudge.md` and the hook header defer to it, and `limit_for` holds the number.

Alternatives weighed:
- **A per-call unit argument to `_lib_staged_length_gate`.** Rejected. One call could not mix units, so the auxiliary files would move to characters or need a second call. A second call resolves the diff base twice, which `_lib.sh:3215-3219` and `test_diff_base_resolved_once_across_multiple_staged_skill_files` rule out.
- **A separate character-gate function.** Rejected: it copies the growth, base and deny logic `_lib_staged_length_gate` owns.
- **The existing `BYTE_LIMIT` path (`git cat-file -s`).** Rejected: it counts bytes, so every em dash (3 bytes, 1 character) overcounts, and the line check would still run beside it.
- **`wc -m` or awk `length()`.** Rejected: both depend on the locale, and in the C locale both count bytes.
- **A `python3` one-liner.** Rejected: `claude/.claude/rules/shell-script-conventions.md` reserves embedded Python for syscalls bash cannot express, and `tr` plus `wc` already count code points with no locale (M1).
- **Moving the auxiliary files to characters too.** Rejected. Their skills Read them at runtime, and the compaction cut applies to invoked skills only (row 10). At 19,000, `ROUTING.md` (20,251 characters, 132 of 500 lines) would lose all headroom for a reason that does not apply to it.
- **Per-skill character overrides above 19,000.** Rejected: a skill allowed past the cut is the failure the cap exists to stop.
- **A reporting mode on `skill-invocation`.** Rejected: that command refuses no wider scope, so it is not a publication instrument (`docs/private-project-redaction.md:169-170`), and the issue's figures need one.
- **Copying the truncation marker into the eval.** Rejected: importing the marker and M6's counter from the instrument means a re-run after a Claude Code release checks the instrument's parser against live output (M7).
- **Counting drops, meaning a skill invoked earlier but absent after a compaction.** Rejected. The invoked set would come from user text and tool calls, which a quoted tag, a failed call, a built-in command or a process restart all inflate. Neither the ranking (rows 8 and 37) nor the gate uses a drop count.
- **Normalizing attachment names with `review_rounds._round_skill_name` before the allowlist.** Rejected: it merges a foreign plugin's same-named skill into a tracked row, and exact matching withholds that skill instead (row 20).
- **A second `claude -p` launcher for M7.** Rejected: `_run_claude_to_completion` already kills the group on any exception, pops `CLAUDECODE`, records the exit status and has tests, and it needs only a `stdin` keyword (row 26).
- **A revert-order note alone for C1.** Rejected: it protects only a reverter who reads it, while M3's guard denies visibly (row 42).
- **A literal `characters` in `check-skill-length.sh`.** Rejected: the unit word is a discriminator `_lib.sh` defines, so the caller prints `_lib.sh`'s constant, which also gives M3's guard its key.

### Assumption ledger

**Root:** `check-skill-length.sh` caps lines, so a skill that passes it can still be cut when Claude Code re-attaches it after a compaction (G1, G2), and nothing in the repository measures which skills are cut or how often.

**Givens:**
- G1. Claude Code re-attaches the most recent invocation of each skill after a compaction and keeps the first 5,000 tokens of each, inside a 25,000-token combined budget filled from the most recently invoked skill. Reason: vendor behavior, stated on the skills docs page (row 16).
- G2. In Claude Code 2.1.330 the per-skill cut lands at exactly 20,000 characters for an ASCII body. The re-attached text drops the frontmatter and prepends `Base directory for this skill: <abs dir>` and a blank line, and that prefix counts toward the 20,000. Reason: vendor implementation, measured by the session's probe (Context). The docs state no character figure, so a release can move it. M7 makes it re-measurable.
- G3. A transcript records a compaction as a `system` record with subtype `compact_boundary`. It records the re-attached skills as an `attachment` record whose `attachment.type` is `invoked_skills`, holding a `skills` list whose entries carry `name`, `path` and `content`. A cut copy ends in `[... skill content truncated for compaction; use Read on the skill path if you need the full text]`. Reason: vendor transcript format, as the probe's `analyze.py` reads it from its synthetic sessions and as `claude/.claude/scripts/tests/_compaction_context_helpers.py:164-167` models the attachment record.

**Mechanisms:**
- **M1. `_lib_staged_length_gate` takes its unit from `limit_for`.**
  - `_lib.sh` defines `_LIB_LENGTH_UNIT_CHARACTERS="characters"`, the one spelling of the unit word, beside its other `_LIB_*` constants.
  - Per staged file, the loop calls `limit_for` before measuring and matches its output with `[[ =~ ]]` against `^([0-9]+)( characters)?$`, built from the constant.
    - A match assigns both `limit` and `unit` on every iteration, so no value carries over to the next file. A bare number means `lines`, so `check-claude-md-length.sh:120-131` behaves as today.
    - Any other output denies with one internal-error message and returns 0 at once, in the shape of `_lib.sh:3235-3238`. A run therefore emits one deny document and measures no later file.
    - "Any other output" covers empty output, a malformed number such as `19,000 characters`, extra tokens, another letter case and an explicit `lines`. This closes the non-integer fail-open that `_lib.sh:3139-3143` documents.
    - The message carries no marker from `_DENIAL_CAUSE_MARKERS` (`denials.py:399-404`).
  - A new helper, `_lib_blob_length REPO_ROOT OBJECT UNIT`, prints one blob's length.
    - Lines keep today's `x`-sentinel capture and `awk 'END{print NR}'` (`_lib.sh:3262-3267`).
    - Characters pipe `_lib_capped git -C "$repo_root" show "$object"` straight into `LC_ALL=C tr -d '\200-\277' | wc -c`, normalized through `$(( ))`.
    - A missing object counts 0 in both units, as today.
  - New and old are measured in the iteration's unit. The deny line reads `<path>: <new> <unit> (was <old>, limit <limit>)` with the numeric limit alone, so the `limit N)` pins at `test_check_claude_md_length.py:315`, `:364` and `:406-409` hold.
  - `BYTE_LIMIT` is untouched.
  - Comments, one fact each:
    - The header's `limit_for` contract names the optional unit word, and says any other output denies.
    - The constant's comment says it is the word a `limit_for` prints after its number to cap characters.
    - The character branch counts UTF-8 code points by deleting continuation bytes under `LC_ALL=C`, so it needs no UTF-8 locale.
    - The character branch pipes instead of capturing, so NUL bytes are counted.
    - The comments that name only lines and bytes also name characters: `_lib_length_ratchet_exceeded`'s (`:3135-3138`), the `BYTE_LIMIT` paragraph (`:3164-3171`), the `limit_for` contract (`:3175-3177`), the `old` paragraph (`:3215-3216`) and the in-loop sentinel comment (`:3255-3261`).

  anchors: root, row5, row6, row12, row13, row30, row42
- **M2. The shared deny states the real way out.** Replace `Reduce to the limit before committing:` (`_lib.sh:3288`) with a sentence telling the reader to bring each listed line back to its `was` figure or its limit, whichever is larger. That is exactly what the predicate allows (`_lib.sh:3146`).
  - The sentence speaks per listed line, so it stays true when `check-claude-md-length.sh` lists one file twice, once for lines and once for bytes.
  - It names the printed `was` figure, not the previous commit, because mid-merge `old` is read at `_lib_gate_diff_base`'s base (`_lib.sh:3215-3229`).
  - Today's text would ask any growing edit to `code-review/SKILL.md` for a cut of about 77,700 characters (row 7).
  - It carries no `_DENIAL_CAUSE_MARKERS` marker, and no classifier keys on the old wording (row 11).

  anchors: row3, row7, row11, row31
- **M3. `check-skill-length.sh` declares one character cap.**
  - `limit_for` returns `500` for `plan-review/ROUTING.md` and `200` for `pr-description/DEFAULT_TEMPLATE.md`, both explicit arms placed before `*)`. Every other path returns `"19000 $_LIB_LENGTH_UNIT_CHARACTERS"`. The four per-skill line overrides go.
  - Just before the `_lib_staged_length_gate` call, a guard denies when `_lib.sh` lacks the character unit. An `_lib.sh` without M1 would otherwise read `19000 characters` as no limit and allow every commit (row 42).
    - It reads `${_LIB_LENGTH_UNIT_CHARACTERS:-}`, because a bare read aborts the hook under `set -u` (`:67`) before any deny.
    - On an empty value it calls `emit_deny "<literal>"` and then `exit 0`, in `:112-115`'s shape, so the run emits one decision.
    - It sits after the commit-shape check and before the path filter, so it denies every commit-concluding call in every repository, as the header's fail-closed posture does. A guard scoped to gated paths would not spare the recovery, since reverting C2 stages a gated `SKILL.md`.
    - The literal names the cause: `_lib.sh` and this hook come from different versions of the checkout. It gives the recovery in `:87`'s form, pointing to `docs/hooks.md` § "Gate deadlock recovery", where the user pulls a fix or reverts the checkout's change from a separate terminal (`docs/hooks.md:580`).
    - The literal names no PR and carries no cause marker.
  - The over-limit literal at `:162` changes in the same commit as `test_transcript_denials.py:728`'s `original_message` and the `:450` docstring, which use it as a mutation anchor (row 11). The new literal:
    - drops "per-skill", since one cap now covers every `SKILL.md`;
    - says in one clause that Claude Code cuts a long skill when it re-attaches it after a compaction, so its later steps are lost;
    - says the count covers the whole file, frontmatter included;
    - states no number, since the deny line prints the limit;
    - carries no cause marker, and keeps the `_lib_staged_length_gate "$REPO_ROOT" '<pattern>' "<literal>"` call shape that `test_transcript_denials.py:533-720` extracts.
  - Header lines 10-29 say three things: every gated `SKILL.md` has one character cap; the new design-decision file holds why; the two runtime auxiliary files keep line caps because their skills Read them. No line-count rationale stays. Lines 147-161 drop their "200-line default" clauses. The "Fail posture" paragraph (`:44-47`) adds the guard's deny.
  - The known-gap line at 51 names `wc` beside awk and grep.
  - `claude/.claude/scripts/_skill_auxiliary_files.py:18-20` adds that a new runtime-read name also needs a line-cap arm in `limit_for`, or it falls to the `SKILL.md` character cap.

  anchors: root, row1, row2, row3, row4, row10, row11, row42
- **M4. Tests.**
  - C1's new `claude/.claude/hooks/tests/test_lib_staged_length_gate.py` holds the input matrix as direct tests, per the extraction rule in `claude/.claude/rules/shell-script-conventions.md`. Each test sources `_lib.sh` in `bash -c` with an inline `limit_for` and a recording `emit_deny`.
    - Counting cases write blobs with `git hash-object -w` into one module-scoped scratch repo and measure them with `_lib_blob_length`:
      - a 1-, 2-, 3- and 4-byte character each count as one, and the 4-byte case pins row 13's undercount against UTF-16;
      - a NUL byte counts, which fails if a refactor captures the content before counting;
      - a stray continuation byte counts zero, pinning row 13's invalid-UTF-8 undercount;
      - in lines, trailing blank lines count, a missing final newline still counts its last line, and an empty blob counts 0;
      - a missing object counts 0 in both units;
      - every character case runs under `LC_ALL=C` and under an ambient UTF-8 locale found with `locale -a`, skipping only when none exists. The test says GNU `tr` cannot witness a dropped `LC_ALL=C`, so the macOS run carries that case (row 12).
    - A differential case checks, for every gated `SKILL.md` that `git ls-files` lists, that `_lib_blob_length` on its `HEAD` blob equals Python's `len()` of the same blob decoded as UTF-8. One `bash -c` call loops over the set. The case first asserts the set holds a non-ASCII file and an astral-bearing file, so it cannot pass vacuously.
    - Gate cases run over a scratch repo:
      - a bare limit counts lines, and the whole deny line reads `<path>: 201 lines (was 200, limit 200)`;
      - with `characters`, a file of multi-byte lines at exactly 19,000 characters allows, and one character more over a committed copy at the cap denies with `<path>: 19001 characters (was 19000, limit 19000)`;
      - reducing an over-cap file whose committed copy is multi-byte allows;
      - one lines file and one characters file staged together, in both path orders, are each judged in their own unit, and the base resolves once, extending `test_diff_base_resolved_once_across_multiple_staged_skill_files`;
      - parametrized bad `limit_for` outputs (empty, `19,000 characters`, `19000 characters extra`, `19000 Characters`, `500 lines`) over two staged files record exactly one `emit_deny` call carrying the internal-error text;
      - an undefined `limit_for` denies with its existing text.
  - C1 adds a `test_transcript_denials.py` case asserting that M1's internal-error text classifies as behavioral. C2 extends it to M2's sentence and M3's guard text.
  - C2 adds a `test_lib_staged_length_gate.py` case asserting that the deny carries M2's sentence.
  - `test_check_skill_length.py`, in C2:
    - `make_skill_content` is retired for `SKILL.md` paths. A character builder serves them, and a renamed line builder serves `ROUTING.md` and `DEFAULT_TEMPLATE.md` only, so a leftover line fixture on a `SKILL.md` path fails visibly.
    - Deny-expecting tests whose line fixture now sits under the cap move to characters: `:129`, `:163`, `:209`, `:237`, `:250`, `:264`, `:322`, `:803`, `:829`, `:1115`, `:1140` and `:1367`.
    - Allow-expecting tests that would otherwise pass vacuously each gain a deny control on the same fixture, or assert the fixture's size against the cap: `:103`, `:230`, `:282`, `:296`, `:848`, `:1013`, `:1036`, `:1070` and `:1094`, plus `:1357`, `:1378` and `:1394` through the builders at `:1201-1350`.
    - The per-skill override tests and their regression guard (`:337-751`, `:768`) give way to one parametrized test over the four formerly overridden paths, one `vendor/` copy and `ai-instruction-and-memory-files/SKILL.md`. Each is committed at the cap, grows by one character, and denies naming `characters`, `limit 19000` and `compaction`, the stable word of M3's reason clause.
    - The `ROUTING.md` and `DEFAULT_TEMPLATE.md` cases stay on lines with their 501- and 201-line deny controls, which catch a fold into `*)`.
    - `test_byte_limit_never_fires_for_this_caller` (`:752`) stages 40,001 characters and asserts a deny that names `characters` and no `bytes` line.
    - The repo-root, plugin and project-layer path tests (`:870-1000`) use 19,000 and 19,001 characters.
    - `test_missing_awk_or_grep_allows_growing_over_limit_file` (`:1172`) stays a known-bug pin, over `grep` and `wc` on a character fixture and over `awk` on `ROUTING.md`.
    - `stub_bin_without_timeout` (`:30`) also links `wc`.
    - A case for M3's guard runs the hook from an isolated hooks directory whose `_lib.sh` sources the real one and then unsets the constant. A commit that stages no gated path gets exactly one JSON deny decision on stdout, naming `Gate deadlock recovery`.
    - New subprocess cases stay at one per branch; the matrix stays in the direct tests.
  - `claude/.claude/scripts/tests/test_transcript_denials.py:449-470` grows its fixture past 19,000 characters.

  anchors: row6, row10, row11, row12, row13, row42
- **M5. One home for the reason; every other site defers.**
  - New `docs/design-decisions/skill-character-cap-for-compaction-reinjection.md`, per `.claude/rules/design-decisions.md`. It holds:
    - the skills-page passage (row 16) verbatim from the raw page body, not a summarizing fetch, with its URL, fetch date and a re-verify-by date three months out, as `docs/handoff-nudge.md:217` does;
    - the context-window passage moved from `docs/handoff-nudge.md:217`, so no source is lost;
    - step 3's result and re-run command, the `claude --version` it ran on, and whether the cut counts code points or UTF-16 units;
    - the 2.1.330 bundle's `round(chars/4)` token estimate, which turns the docs' 5,000 tokens into 20,000 characters. The cap counts what the estimate counts, because a shell gate has no tokenizer. Step 3's measured cut confirms the conversion;
    - the residual's classification, and its text only when it matches the expected shape (M7);
    - the margin: the frontmatter is stripped, so a whole file at 19,000 leaves room for the prefix and the invocation's arguments (row 25);
    - the counting unit, that `wc -m` under a UTF-8 locale agrees with it, and its two undercounts, astral-plane characters and invalid UTF-8 bytes (row 13);
    - what the cap does not cover: total-budget drops, long arguments, and a file a skill Reads. Compaction does not re-attach a Read result, so a split skill keeps working only if its re-attached body re-Reads the file at the step that needs it (row 10);
    - the canary: a truncated-copy length range in M6's output, in the unit step 3 named, other than 20,000 means the cut moved. The session working the master issue re-runs M7 when `claude --version` changes. No one owns either run once the issue closes, and the file says so;
    - a pointer to `docs/precompact-hook-behavior.md` § "What the default summary keeps", which records an earlier observation of the same 20,000-character cut and stays that investigation's record;
    - the master issue's number, as the plan for the files already over the cap (row 38);
    - when to reopen: a Claude Code release that moves the cut.
  - `docs/skills.md`:
    - `:170` becomes one bullet saying every `SKILL.md` has a character cap (`limit_for` holds the number), citing the new file, and naming the master issue as the plan for the files already over it. The sentence beginning "Shorten first, do not extract" stays verbatim.
    - `:171` says "length cap" and drops its one-paragraph-per-line sentence. Its deletion test and its gate-counting sentence stay.
    - `:172`, `:174` and `:175` go, since their overrides no longer exist. `:173` stays.
    - The "Skill architecture notes" heading stays, since `.claude/rules/skill-and-agent-self-review.md` and the hook header cite it.
  - `.claude/rules/skill-and-agent-self-review.md:25` says "At a length cap".
  - `docs/hooks.md:166` says the hook blocks on a character limit (`limit_for` holds the number) and that the two auxiliary files keep line limits. It restates no number.
  - `docs/handoff-nudge.md:216-218` keeps its mitigation sentences: the focus line, the state block and the steering hook. It replaces the cap, its quote, the `wc -c` estimate and the named-skill list with a pointer to the new file.
  - `docs/design-decisions/no-shared-skill-partials.md` gains a "Superseded in part" line under its provenance line, in the form `ready-for-review-fix-loop-convergence.md:7` uses. It says `:7`'s sentence on the 200-line cap no longer holds and points to the new file.
  - The `skill-review` plugin stands alone for plugin consumers, so none of these edits cites a repository path:
    - `SKILL.md:79` says a `SKILL.md` stays under 19,000 characters, counting the whole file, because Claude Code keeps only the first 5,000 tokens of each invoked skill when it re-attaches skills after a compaction, so a longer body loses its later steps. Other files keep the 200-line target and its "diminishing returns past 300". `:141-142` points to `:79`'s target without restating it. The file stays at 200 lines or fewer, because main's line gate judges C2's commits (row 41).
    - `REFERENCES.md:24-25` replaces the 200-line cap clause with the fact that skill-creator's 500-line-body convention allows a body past § 4's character target. It adds the skills-page URL and the measured 20,000-character cut with its Claude Code version.
    - `plugin.json`'s `version` (5.1.1) rises as `/plugin-semver` decides. `.claude-plugin/marketplace.json` carries no version field for the plugin.
  - `claude/.claude/hooks/tests/test_doc_counts.py` gains a fact pinning `skill-review/SKILL.md:79`'s number to `check-skill-length.sh`'s wildcard arm (row 28). It parses the arm's `echo "19000 $_LIB_LENGTH_UNIT_CHARACTERS"` shape and strips the prose number's thousands separator, so neither side matches vacuously.
  - One `CHANGELOG.md` `[Unreleased]` entry states the gate change for every stow consumer:
    - a gated skill that passes is not cut by the per-skill re-injection limit after a compaction, though the total budget can still drop it whole;
    - its `Migration:` bullet states row 27's two effects, that an over-cap file can still shrink or hold, and that no config key turns the gate off;
    - it cites the master issue.

  anchors: row9, row10, row13, row14, row15, row16, row17, row23, row25, row27, row28, row38, row41
- **M6. `transcript-analysis.py skill-reinjection --this-repo`.**
  - New `transcript_analysis/skill_reinjection.py` in `read_cost.py:588-609`'s shape: `cmd_skill_reinjection` reports over `publication_scope._single_account_roots`, calling `_refuse_wider_scope`, then `scope._resolve_project_scope` with subagent files left out, then printing `_scope_header`.
  - It reads only records the harness writes: `compact_boundary` system records and `invoked_skills` attachments, on the main thread, skipping `isSidechain`. It reads no user text and no tool call, so no quoted tag, failed call or built-in command can move a count.
  - Records come from the shared reader, which skips an unparseable line without a count (`corpus.py:97-120`). A compaction whose boundary or attachment line is corrupt therefore drops out or counts as without an attachment, and M6's docs section says so. Every other bad shape skips with a scan gap:
    - a non-object record;
    - an `attachment` or skill entry that is not an object;
    - a missing or non-list `skills`;
    - a missing or non-string `name` or `content`.
  - Per session file, read in sorted path order:
    - Each boundary opens a window that the next boundary closes. The first `invoked_skills` attachment in a window pairs with that window's boundary. A later attachment in the same window, or one before any boundary, pairs with nothing and records a scan gap.
    - A compaction is keyed by its boundary's uuid. A boundary whose uuid an earlier file already counted is skipped, and so is its window's attachment. The skipped boundary still opens and closes its window. Pairing therefore does not shift. A boundary whose uuid is missing or not a string is counted and records a scan gap (row 39).
  - Per skill name, it counts:
    - re-attached: copies in paired attachments;
    - truncated: copies whose `content`, with trailing whitespace stripped, ends in the marker. A marker elsewhere in the body does not count. An unmarked copy over 20,000 in both code points and UTF-16 units records a scan gap, so a reworded marker or a raised limit shows.
  - Totals: sessions, compactions, compactions with and without an attachment, the first and last compaction date, the shortest and longest truncated copy in code points, in UTF-16 units and in UTF-8 bytes, and scan gaps by kind. Lengths encode with `surrogatepass`, so a cut inside a surrogate pair cannot raise.
  - It prints only skill names tracked in this repository.
    - New `redaction._repo_tracked_skill_names()` anchors on this module's resolved repository root, never the cwd, as `_REPO_AGENT_DEFINITIONS_DIR` does (`redaction.py:256-259`). It runs `git -C <root> ls-files -z` with `check=True`, `timeout=10` and the exception set at `redaction.py:296`.
    - It keeps `claude-skills/skills/<d>/SKILL.md` and `.claude/skills/<d>/SKILL.md` as `<d>`, and `plugins/<p>/skills/<d>/SKILL.md` as `<p>:<d>`, the spellings attachments use (row 20). A deeper path yields no name.
    - An attachment `name` prints only when it equals a member of that set. Every other name folds into one withheld row with summed counts, as `read_cost.py:573-585` folds agent types. A foreign `<plugin>:<tracked name>` is withheld too.
    - When git fails, the set is empty and the report prints a line saying every name is withheld because the tracked list is unavailable.
  - Rows sort by re-attached count, then by name. The print function takes only the fold's output. The output carries no session id, project slug, path or skill content. The entry's `path` is never read, and `content` is read only for the marker and the length.
  - With no sessions, it prints the header and zero totals and exits 0.
  - The module exposes the marker, the copy-length function and a per-session counter that runs before the name fold, for M7.
  - Tests, in `tests/test_transcript_skill_reinjection.py` with record builders in `tests/_skill_reinjection_helpers.py`:
    - pairing: `[B1, B2, A]` pairs A with B2 and leaves B1 without one; `[B1, A1, A2, B2]` counts A1 alone and records a gap for A2; an attachment before any boundary records a gap;
    - dedupe: a second file replaying B1 and A1 with the same uuids leaves every count unchanged, and one that replays them and then adds B2 and A2 counts exactly A2. A boundary with no uuid, or a non-string one, counts once and records a gap;
    - a compaction with no attachment raises the "without" total and no skill count;
    - truncation: the marker at the end counts, the marker followed by trailing whitespace counts, and the marker mid-body does not. An unmarked copy over 20,000 records a gap;
    - lengths: an astral character in a cut copy gives different code-point and UTF-16 figures, and a copy ending in a lone high surrogate yields all three lengths;
    - a sidechain boundary or attachment between a main boundary and its attachment changes nothing, and a `subagents/` file under the session is never read;
    - names: a bare tracked name and a `<plugin>:<skill>` tracked name print, while a foreign `<other>:<tracked name>` and an untracked name land in the withheld row with summed counts. With an empty tracked set, the report prints the unavailable-list line, the withheld row and the totals, and no name;
    - order: rows with unequal counts and a tie print by count, then by name;
    - privacy, in `test_transcript_read_cost_report.py:170-225`'s shape: canaries in the session id, the project slug, a home-rooted attachment `path`, a `content` opening with the Base-directory prefix and an untracked name, none of which appears in stdout or stderr;
    - error paths: each bad shape M6 lists records its gap and leaves the other counts unchanged, and a malformed line changes no count. Each fixture carries the privacy case's canaries, and none appears in stdout or stderr;
    - a corpus with no sessions;
    - `TestScopeRefusal`, copied from `test_transcript_read_cost_command.py`.
  - `tests/test_transcript_redaction.py` covers the accessor in the shape of its `:84-135`:
    - a tracked name in each of the three kept shapes is in, and an untracked file in the same tree is out;
    - a nested path yields no name;
    - a git failure yields the empty set;
    - a cwd inside a second repository that tracks `.claude/skills/<canary>/SKILL.md` never yields the canary.
  - Wiring: the `cli.py` registrar (`:59-60`, `:138`), the `scope.py:707` tuple, `tests/test_transcript_cli.py:156`, `test_transcript_package_module_prefixes.py`, and `test_transcript_publication_scope.py`'s `command_label` parametrize.
  - Docs:
    - `docs/transcript-analysis.md` gains a `skill-reinjection` section modeled on its `read-cost` section, an entry in each list at `:78-87` and `:91-96`, and "these four" becomes five at `:91`.
    - That section's Publication paragraph carries `read-cost`'s wording, cites the gaps in `docs/transcript-analysis.md` § "Scoping to this repo: `--this-repo`", a removed worktree's sessions among them (row 40), and says zero sessions is no measurement. The section shows no real figure.
    - `docs/transcript-analysis-architecture.md` gains a level-three heading for `skill_reinjection.py`.
    - `docs/private-project-redaction.md` § "This repository, one account" gains a bullet in `read-cost`'s form.
  - One `CHANGELOG.md` `[Unreleased]` entry for the subcommand, with no figure.

  anchors: root, row8, row18, row19, row20, row21, row29, row37, row39, row40
- **M7. `evals/measure_skill_reinjection.py`, a port of the probe.**
  - Two cases:
    - `per-skill`: one 40,000-character skill of fixed-width sentinel lines. Each line carries one multi-byte BMP character and every tenth line one astral-plane character, so a cut counted in bytes, in code points or in UTF-16 units lands at a different place.
    - `total-budget`: six 19,000-character skills invoked in order.
  - One `claude -p` process per case reads stream-json turns from a file on stdin: `/<skill> Reply with only the word OK.` per skill, then `/compact`.
    - Flags: `--session-id` with a fresh UUID per run, `--setting-sources project`, `--strict-mcp-config`, `--input-format stream-json`, `--output-format stream-json`, `--verbose`, `--max-budget-usd`.
    - The child keeps its built-in tools, and the docstring says why: the probe measured with them, and whether a typed skill command still re-attaches under `--tools ""` is unmeasured.
    - The cwd is a symlink-resolved temp project holding `.claude/skills/<name>/SKILL.md`.
  - It launches through `measure_subagent_model_resolution._run_claude_to_completion`, which gains a keyword-only `stdin` argument defaulting to `subprocess.DEVNULL` (row 26). The group kill on any exception, the `CLAUDECODE` pop and `LaunchOutcome`'s exit status and stderr tail come with it. `main()` maps SIGHUP and SIGTERM to `KeyboardInterrupt` as that module's `main()` does (`:1038-1040`).
  - Analysis runs before the `finally` that removes the temp project and its session store, as `:903-907` does. It maps any analysis exception to INCONCLUSIVE with the exception's type, so a paid run always yields a verdict.
  - Reuse: `run_skill_evals.compute_session_store_dir`; `measure_subagent_model_resolution._resolved_temp_project_dir`, `environment_without_git_local_vars` and `_extract_total_cost_usd`; `skill_reinjection`'s marker, copy-length function and per-session counter.
  - For each copy after the last boundary, it reports:
    - its length in code points, in UTF-16 units and in UTF-8 bytes;
    - whether it was cut, and whether it holds frontmatter;
    - the prefix length;
    - the residual, meaning the text that is neither prefix nor sentinel body. It reports the residual's length, whether it sits before or after the body, whether it matches the expected `ARGUMENTS: <turn argument>` shape, and its text escaped and cut to 200 characters.
  - Each expectation prints PASS, FAIL or INCONCLUSIVE:
    - `per-skill`: the copy is cut, is 20,000 code points or 20,000 UTF-16 units (the report names which), and holds more than 20,000 UTF-8 bytes. M6's counter gives 1 re-attached and 1 truncated.
    - `total-budget`: the five newest skills come back intact and the oldest is absent. M6's counter gives 5 re-attached and 0 truncated.
    - INCONCLUSIVE covers a run that wrote no post-boundary attachment: a timeout, a budget stop, a non-zero exit, or a transcript with no boundary or no attachment (row 24). A run that wrote one is judged on it, whatever its exit status, which the report still prints.
    - `--all` exits nonzero on any FAIL or INCONCLUSIVE.
  - Each case's `--max-budget-usd` and timeout defaults come from step 3's passing run, recorded with its date and command in a comment, since the probe recorded neither (row 43).
  - The CLI follows the precedent: `--list`, `--run CASE`, `--all`, `--budget-cap-usd`, `--timeout-s`, `--json`. It prints `claude --version`, each case's cost and wall time, and whether `ANTHROPIC_API_KEY` is set in the child's environment, never its value.
  - The docstring opens "LOCAL USE ONLY — never run in CI". It says the child inherits the operator's credentials and environment, git variables aside.
  - Tests:
    - `evals/test_measure_skill_reinjection.py` tests the pure functions on synthetic records: skill text, turn building, copy analysis, residual classification and the expectation checks.
    - The generated `per-skill` text is exactly 40,000 code points, with more UTF-16 units and more bytes.
    - Each expectation has synthetic FAIL or INCONCLUSIVE cases: no copy, an intact `per-skill` copy, a 19,999-character copy, six skills present, and the wrong skill absent.
    - One PASS case per unit label pins which unit the report names, using a 20,000-UTF-16-unit copy that holds fewer code points.
    - A table test maps each launch outcome, with and without a post-boundary attachment, to its verdict.
    - A `main()` test over stubbed case results shows `--all` exits nonzero on a FAIL and on an INCONCLUSIVE.
    - `evals/test_measure_subagent_model_resolution.py` gains `stdin` cases. A fake child echoes its stdin, which shows the turns file reaches it. A fake child reading stdin under the default sees EOF. A timeout with file stdin still kills the group.
  - `select-tests.py`:
    - New module and test constants fold into `_is_review_bench_change` and `EVALS_TEST_TARGETS`, as `MEASURE_EXPLORE_RECALL` does (`:107-138`, `:730-744`). The test file also joins `_FILE_TARGETS`.
    - A standalone row selects `test_select_tests.py` for the eval, as `MEASURE_MAIN_SESSION_RULE_ADHERENCE`'s row does (`:1001`). The eval imports `transcript_analysis`, so without it the ground-truth walk would fail only on CI.
    - `_REVIEW_BENCH_SCRIPTS_DEPENDENCIES` (`:146-157`) gains the modules the ground-truth walk at `test_select_tests.py:1071-1134` finds. The platform review projects `skill_reinjection.py` and `publication_scope.py`.
    - `test_select_tests.py` pins the new rows and its hand-audited list (near `:2584-2614`).
  - `evals/README.md` gains a section with the usage lines, and its "Runtime cost" section gains B's measured cost and wall time.

  anchors: row22, row23, row24, row25, row26, row43
- **M8. The master issue.** After A merges, the session branches B's worktree from main's tip. From that worktree it runs M6 and Verification steps 6 and 7, then files one GitHub issue with `gh issue create` (row 38). The issue holds:
  - first lines saying what the four PRs do and do not do: once C2 merges the gate stops growth and the issue ranks the cleanup, but neither stops `/ready-for-review` losing its "CI watch (out-of-band)" section after a compaction;
  - one checklist row per gated `SKILL.md` over 19,000 characters, in two groups (row 37):
    - group 1 holds the skills cut today, by Verification step 6's group-1 test;
    - group 2 holds the rest;
    - membership reads the current files, not M6's counts, which span every compaction in the window whatever the file's size then;
    - each group sorts by re-attached count (row 8), then by size;
  - each row's size in characters and its re-attached and truncated counts. Every count in the issue comes from one M6 run that passes step 4's checks and step 7, with each producing command named beside the table and stated as run from a checkout of this repository:
    - an amendment that publishes counts from a new run replaces every count and the window with that run's values;
    - a skill with no M6 row reads 0 and 0 only when that run's withheld row has a re-attached count of 0, and reads "no named row" otherwise;
  - one line saying any new figure posted to the issue first takes `docs/private-project-redaction.md` § "New figures against the grandfathered set";
  - M6's window, meaning its first and last compaction date, and the corpus limits its docs state, with no root or account count;
  - a callout on `ready-for-review`'s row naming the lost section, wherever that row sorts;
  - a pointer to #1351, which already plans the `code-review` restructure, checked by number, title and state only, with no body or comment read;
  - the reduction routes:
    - shorten first, per `docs/skills.md` § "Skill architecture notes";
    - move the steps a session most needs toward the top, as the vendor passage at `docs/handoff-nudge.md:217` advises;
    - split into forced-read files with `require-routing-read.sh` as the precedent, once row 9's conflict is settled. A split keeps working only if the re-attached body re-Reads the file at the step that needs it, since `require-routing-read.sh`'s 60-minute marker would accept a Read made before the compaction;
  - row 9's conflict, as the issue's first open decision.

  anchors: row7, row8, row9, row10, row18, row19, row29, row32, row37, row38, row40
- **M9. Four PRs, merged in the order A, B, C1, C2.**
  - A carries M6 and this plan.
  - After A merges, the session files the master issue (M8) before B's dispatch, so C2 can cite its number (row 38).
  - B carries M7. M7 imports M6's marker, copy-length function and counter, so B branches from main after A merges. Step 3 runs in B's worktree after B's last code commit and before its PR opens, and B's PR body records the result.
  - C1 carries M1 alone. It is dispatched after B merges, and only once B's PR body shows the cut counts characters, so the unit it adds is the measured one.
  - C2 carries M2-M5. M3 gives M1's character unit its first caller, M5's file records step 3's result, and C2 cites the issue.
  - C2 depends on C1 and B imports A, so a revert takes C2 before C1 and B before A. M3's guard turns a revert of C1 alone into a visible deny (row 42).
  - Critical files gives each PR's files, gating steps and size.

  anchors: row26, row30, row32, row33, row34, row35, row36, row38, row42

**Rows:**
1. The cap is 19,000 over the whole `SKILL.md`. [engineer-verified: "Whole file ≤ 19,000 (Recommended)"]
2. The session's description of that option: count the whole file, frontmatter included, with `wc -m`, keeping about 1,000 characters for the install-path prefix and version drift. [unverified] M1 counts code points, which is what `wc -m` gives under a UTF-8 locale. Row 25 adds the invocation's arguments to what the margin must hold.
3. Over-cap files may shrink but never net-grow. [engineer-verified: "No growth (Recommended)"]
4. The session's description of that option: keep today's policy of denying only a file that is over its cap and grew, with no per-file table. [unverified] It matches `_lib_length_ratchet_exceeded`. [verified: `_lib.sh:3144-3147`]
5. The ratchet predicate compares plain integers whatever their unit. [verified: `_lib.sh:3131-3147`]
6. The gate counts lines with awk and hard-codes `lines` in its deny line. `check-claude-md-length.sh` passes a bare-number `limit_for` and a byte limit. [verified: `_lib.sh:3262-3270`; `check-claude-md-length.sh:120-131`]
7. Seven gated `SKILL.md` files exceed 19,000 characters: `code-review` 96,679, `plan-review` 33,532, `review-pr` 32,814, `ready-for-review` 28,595, `plan-it` 23,222, `handoff` 19,885, `review-loop-cost-audit` 19,447. [verified: the round-2 product review's `LC_ALL=en_US.UTF-8 wc -m`, which the round-2 backend review's count matches] Verification step 6 re-derives the list before the issue cites it.
8. The issue orders the reduction by re-attachment count. [engineer-verified: "prioritize the length reduction by how often skills get reinjected"]
9. The engineer named a route. [engineer-verified: "which may involve splitting them out into sub-skills that require forced reads or something"] It conflicts with two standing rules. A co-located file is added "never as a way to route around a file's length cap" (`.claude/rules/skill-and-agent-self-review.md`), and "cap pressure alone doesn't license that move" (`docs/skills.md:170`). [verified: reads] This plan amends neither, and M8 carries the decision.
10. The skills that own `ROUTING.md` and `DEFAULT_TEMPLATE.md` read them with the Read tool at runtime. [verified: `docs/skills.md:169`] `ROUTING.md` is 132 lines [verified: line count] and 20,251 characters. [unverified: a subagent's `wc -m`, locale not recorded] That a Read result is never re-attached rests on the docs passage naming invoked skills only. [unverified] Keeping both files on lines is the session's unasked default, kept here.
11. The transcript-analysis tests and classifier constrain the deny texts. [verified: reads, a grep of `transcript_analysis/`, and the round-2 CISO review's re-grep]
    - `test_transcript_denials.py` uses the over-limit literal as a mutation anchor (`:727-745`), so the hook and its `original_message` change in one commit.
    - It also expects a 201-line `SKILL.md` to deny (`:449-470`), which a character cap no longer does.
    - `denials.py` classifies a deny's cause by marker substring (`:399-404`).
    - No `transcript_analysis` classifier matches "Reduce to the limit".
    - The fixtures holding that text are frozen legacy strings (`:221-230`, `:1031-1036`, and `test_transcript_review_trace_deny_summary.py:213`).
12. `LC_ALL=C tr -d '\200-\277' | wc -c` counts UTF-8 code points under BSD `tr` and under GNU `tr`. [verified: the round-2 platform and SDET reviews' runs on macOS with BSD `tr` and MacPorts GNU `gtr`] GNU `tr` gives the same count with or without `LC_ALL=C`, while BSD `tr` under a UTF-8 locale counts bytes without it, so only a macOS run catches a dropped prefix. [verified: the round-2 SDET review's scratch run] CI's Ubuntu coreutils have not been run, and C1's direct tests run there.
13. Claude Code runs on JavaScript, whose string length counts UTF-16 code units, one more than code points for each astral-plane character. [unverified] M7 measures which unit the cut counts. M1 can undercount the harness by one per astral character. It also deletes a stray continuation byte that a decoder would likely show as one replacement character. [unverified] Three tracked skills hold astral characters, a difference far below the margin. [verified: the round-2 backend review's count] M5's file states both undercounts.
14. `docs/handoff-nudge.md:216-218` states the 5,000-token cap with its own source, a `wc -c` size estimate and which skills exceed the cap. [verified: read]
15. `docs/skills.md:170-175` hold the 200-line default, a flatten rule justified by line counting, and three per-skill override bullets that become false. [verified: read]
16. The skills page says: "Auto-compaction carries invoked skills forward within a token budget. When the conversation is summarized to free context, Claude Code re-attaches the most recent invocation of each skill after the summary, keeping the first 5,000 tokens of each. Re-attached skills share a combined budget of 25,000 tokens. Claude Code fills this budget starting from the most recently invoked skill, so older skills can be dropped entirely after compaction if you have invoked many in one session." [verified: https://code.claude.com/docs/en/skills.md, fetched this session by the session's subagent; the architect did not re-fetch it] The page states no character figure and no marker text.
17. A design decision is one file named by slug, with an italic provenance line and no index, and it cites rules rather than restating them. [verified: `.claude/rules/design-decisions.md`]
18. `read-cost`'s refusal, header and untracked-name fold are the template a publishable per-name count needs. [verified: `publication_scope.py:26-56`; `read_cost.py:573-609`; `redaction.py:262-303`; `docs/private-project-redaction.md:142-147`, `:169-170`]
19. The mining prototype builds its root list by hand and refuses no wider scope, so its counts cannot be published and are not a source for the issue. [verified: `/tmp/skillcap-mining/mine.py:7-8`]
20. Attachment `name` values spell a plugin skill `<plugin>:<skill>` and every other skill by its directory name. [unverified: no scope-refusing read backs it yet; Verification step 4's run is the first] M6 matches names exactly, so a spelling outside that shape is withheld, never merged into a tracked row. M6's fixtures pin both spellings.
21. A new subcommand needs the registrar and `func=cmd_<snake>` pairing, the `scope.py:707` tuple, the CLI test tuple, the module-prefix lists, a test file named for the module, and the architecture-doc heading. [verified: the dispatch evidence, with `scope.py:707` and `read-cost`'s registrar import and call at `cli.py:59-60` and `:138` reopened]
22. The probe is checked in under `evals/`. [engineer-verified: "Yes, under evals/ (Recommended)"]
23. The session's description of that option: port the probe to a Python eval beside `evals/measure_*.py`, run it by hand, and record the result in docs. [unverified] M5's design-decision file is that record, following `docs/design-decisions/explore-haiku-pin-declined-on-measurement.md`.
24. The probe needs one process for every turn: a two-process run produced no `invoked_skills` attachment. [verified: `/tmp/skillcap-probe/scripts/run-probe.sh:23` and the dispatch evidence]
25. In the total-budget probe each copy was 19,178 characters. The 19,000-character body plus a prefix of about 138 characters leaves about 40 unexplained, which matches a blank line, `ARGUMENTS: ` and the 28-character turn argument. [unverified] If so, an invocation's arguments count toward the 20,000. M7 reports the residual's text and where it sits, and M5's file records what it is.
26. `_run_claude_to_completion` launches with `stdin=subprocess.DEVNULL`, and kills the child's group on timeout or any exception. [verified: `evals/measure_subagent_model_resolution.py:723-801`] A keyword-only `stdin` argument with that default leaves its other callers unchanged. Evals already import `transcript_analysis` after a `sys.path` insert. [verified: `evals/review_bench/mine_review_rounds.py:29-32`]
27. Every consumer's gated skills take the new cap on `git pull` (row 30). A consumer skill under 200 lines but over 19,000 characters can no longer grow, and one over 200 lines but under 19,000 characters now can. [verified: `check-skill-length.sh:129-162`] No `config-keys.psv` key turns the gate off. [verified: a grep of `claude/.claude/hooks/config-keys.psv`] The CHANGELOG entry states all three.
28. `test_doc_counts.py` pins a prose number to the `limit_for` wildcard arm it restates. `ai-instruction-and-memory-files/SKILL.md`'s CLAUDE.md line target is the worked case. [verified: `claude/.claude/hooks/tests/test_doc_counts.py:229-252`, `:564-577`]
29. A figure drawn from this repository's transcripts publishes only beside a command that refuses a wider corpus, and a new figure takes the grandfathered-set check first. [verified: `docs/private-project-redaction.md:99-108`, `:337-347`] Out of scope records that this plan keeps that rule.
30. `claude/` is stowed into every consumer's config directory, so an edit to `check-skill-length.sh` or `_lib.sh` goes live on `git pull` for every consumer's skills under the gated paths. [verified: `CLAUDE.md` § "Working in this repo"]
31. M2's rewrite of the shared deny sentence stays in this plan. [engineer-verified: "Keep it (Recommended)"]
32. The work ships as four PRs merged in order: A (instrument), B (eval), C1 (`_lib.sh` character unit and its direct tests), C2 (cap policy and docs). [engineer-verified: "Four PRs (A, B, C1, C2)"]
33. The session's description of that option, kept as offered: [unverified]
    - A is M6 plus the plan file.
    - B is M7, branched from main after A merges.
    - C1 is M1 alone, with no consumer-visible change and no CHANGELOG entry.
    - C2 is M2-M5 with M5's CHANGELOG entry.
    - M8 follows C2's merge. Row 38 moves M8 to follow A's merge instead.

    C1 changes nothing a consumer sees only if both callers' `limit_for` still print a bare number (row 6) and M1 keeps today's `lines` deny line for a bare number. `check-claude-md-length.sh`'s tests pin that deny line. [verified: `claude/.claude/hooks/tests/test_check_claude_md_length.py:406`] Verification step 1 confirms both callers' tests pass with no edit in C1.
34. A character branch with no production caller in C1 trips no repository dead-code rule.
    - The one mechanical dead-code check, `test_shell_lib_function_liveness.py`, requires each column-0 function in a hooks helper library to have a name reference outside its own definition. A reference inside the same library or in a test file counts, and the check does not look inside a function. [verified: `claude/.claude/hooks/tests/test_shell_lib_function_liveness.py:1-48`, `:196-206`]
    - C1's `_lib_blob_length` is called from `_lib_staged_length_gate`, and C1's direct tests run its character branch.
    - No rule, reviewer agent or review skill flags an unused branch. [verified: greps for dead code, unused, unreachable, no caller, speculative and YAGNI over `.claude/rules/`, `claude/.claude/rules/`, `claude/.claude/agents/`, `code-review/SKILL.md` and `test-conventions/SKILL.md`]
    - `.shellcheckrc` enables no optional check. [verified: `.shellcheckrc`] Whether ShellCheck warns on the branch is [unverified]; Verification step 2 runs it on C1.
35. The plan never merges apart from implementation. `branch-management` says "Don't open a standalone plan-only branch that can merge independently of the implementation — plan and code ship as one PR". `plan-review` B17 flags a plan that sits on a separate branch while implementation is underway. [verified: `claude-skills/skills/branch-management/SKILL.md:168-173`; `claude-skills/skills/plan-review/SKILL.md:168`] Read literally, "plan and code ship as one PR" cannot hold across row 32's four PRs. This plan meets the rule's stated prohibition instead. The plan ships in A beside M6. B, C1 and C2 branch from a main that already holds it. `require-plan-review.sh` passes a committed, unmodified plan, so those three need no plan edit. A PR that revises the plan clears that gate through `/plan-review`. [verified: `claude/.claude/hooks/require-plan-review.sh:4-15`]
36. `require-diff-size-prompt.sh` denies a commit that brings its branch's diff against the base to 400 or more changed lines, files under `.claude/plans/` excluded, until the engineer answers `Proceed anyway`. The stowed `settings.json` registers it. [verified: `claude/.claude/hooks/require-diff-size-prompt.sh:4-14`; `claude/.claude/settings.json:325`] Each of the four PRs projects past 400, so each branch's first commit past it asks the engineer. Row 32's answer settles the split, not those per-branch prompts.
37. The master issue ranks skills in two groups: those cut today first, then those over the gate's cap but not cut today. [engineer-verified: "Two groups (Recommended)"]
38. The master issue is filed after PR A merges. [engineer-verified: "After PR A (Recommended)"]
39. A resumed or forked session can copy earlier records into a new file with their uuids. [unverified] M6's boundary-keyed dedupe changes no count when no uuid repeats.
40. `--this-repo` matches the project directories of the worktrees `git worktree list` prints now, so a removed worktree's sessions drop out of the scope. [verified: `scope.py:96-120`; `docs/transcript-analysis.md:67`] The issue states this limit beside its figures.
41. While C2 is committed, the stowed `check-skill-length.sh` that judges the commit is main's line gate, unless the stowed checkout is C2's branch. `skill-review/SKILL.md` is 199 lines against that gate's 200-line default. [unverified: the round-2 backend review's reading and count]
42. An `_lib.sh` without M1 hands `19000 characters` to `[ "$new" -gt "$limit" ]`, which exits 2, and the caller reads that as not exceeded, so the gate allows every commit. [verified: `_lib.sh:3139-3147`, `:3268-3269`]
43. The probe recorded no cost and no wall time. [verified: a grep of `/tmp/skillcap-probe/` for cost, budget, duration, elapsed and seconds]

## Critical files

Four PRs merge in the order below (M9). Each PR's implementation is one `code-writer` dispatch. The session then runs `/code-review`, commits, runs `/ready-for-review` and opens the PR. Merge is human-only, so the session waits for the engineer to merge each PR before it branches the next from a fresh main tip with `branch-management`. Row 36 covers the diff-size prompt each branch meets. Paths are repo-relative.

**PR bodies.**
- Each names which of the four PRs it is and cites the plan by path, `.claude/plans/skill-char-cap.md`.
- Each ends with one line naming the next step and the input it needs, so a resumed session can find its place from GitHub alone.
- A's and C2's say the work stops growth and ranks the cleanup, but does not stop `/ready-for-review` losing its CI watch section.
- A's says that approving A approves the plan for B, C1 and C2.
- C1's and C2's say a revert takes C2 before C1.
- C2's leads with its user-visible change: the cap, the deny text and the CHANGELOG entry. It names every open PR whose files include an over-cap skill (`gh pr list`), since C2 freezes those files.

**How the plan travels.** The plan file ships in PR A. The session commits it to this branch before A's dispatch (plan-it Step 7). The Context cites no prototype-derived counts (row 19), because the plan ships publicly in A. B, C1 and C2 branch from a main that already holds it. A PR that revises the plan, as step 3's stop condition could, commits the revision in that PR after `/plan-review` (row 35).

**PR A: the instrument (M6), on this branch.** About 1,050 changed lines. Gated by Verification steps 1, 2 and 4. Step 4's output stays in the session: A's docs, CHANGELOG entry and PR body carry no real figure. B's and C2's PR bodies and M5's design-decision file carry no M6-derived figure.
- `.claude/plans/skill-char-cap.md`, this plan.
- New `claude/.claude/scripts/transcript_analysis/skill_reinjection.py`.
- `claude/.claude/scripts/transcript_analysis/redaction.py` (`_repo_tracked_skill_names`).
- `claude/.claude/scripts/transcript_analysis/cli.py`.
- `claude/.claude/scripts/transcript_analysis/scope.py` (`:707`).
- New `claude/.claude/scripts/tests/test_transcript_skill_reinjection.py`, with its `TestScopeRefusal` copied from `test_transcript_read_cost_command.py`.
- New `claude/.claude/scripts/tests/_skill_reinjection_helpers.py`: builders for `compact_boundary` and `invoked_skills` records, and a stub for the tracked-skill allowlist.
- `claude/.claude/scripts/tests/test_transcript_redaction.py`.
- `claude/.claude/scripts/tests/test_transcript_cli.py` (`:156`).
- `claude/.claude/scripts/tests/test_transcript_package_module_prefixes.py`.
- `claude/.claude/scripts/tests/test_transcript_publication_scope.py`.
- `docs/transcript-analysis.md`, `docs/transcript-analysis-architecture.md`, `docs/private-project-redaction.md`.
- `CHANGELOG.md`: M6's entry.

Reuse: `publication_scope._single_account_roots`, `_refuse_wider_scope` and `_scope_header`; `scope._add_project_scope_args` and `_resolve_project_scope`; the shapes of `read_cost._fold_untracked_agent_types` and `redaction._repo_tracked_agent_type_names`; the conftest's `fake_projects` and `_write_jsonl`; `tests/_read_cost_helpers.py`'s preset `--this-repo` slugs; the attachment shape in `tests/_compaction_context_helpers.py:164-167`.

**After A merges: the issue (M8).** The session branches B's worktree from main's tip, runs steps 6 and 7 there, and files the issue. The issue is not a repository file.

**PR B: the eval (M7).** About 700 changed lines. Gated by steps 1, 2 and 3.
- New `evals/measure_skill_reinjection.py`.
- New `evals/test_measure_skill_reinjection.py`.
- `evals/measure_subagent_model_resolution.py`: the `stdin` keyword on `_run_claude_to_completion`.
- `evals/test_measure_subagent_model_resolution.py`.
- `claude/.claude/scripts/select-tests.py`.
- `claude/.claude/scripts/tests/test_select_tests.py`.
- `evals/README.md`.

Reuse: the helpers M7 lists.

**PR C1: the character unit (M1).** About 420 changed lines. Gated by steps 1 and 2. Dispatched after B merges, with B's PR body's step 3 record, once that record shows the cut counts characters.
- `claude/.claude/hooks/_lib.sh`: M1 only. The deny sentence at `:3288` stays as it is.
- New `claude/.claude/hooks/tests/test_lib_staged_length_gate.py`: M4's direct cases, except the one for M2's sentence.
- `claude/.claude/scripts/tests/test_transcript_denials.py`: M4's cause-marker case for M1's internal-error text.

C1 adds no `CHANGELOG.md` entry, because no caller's `limit_for` prints a unit word yet (row 33).

Reuse: `_lib_capped`, `_lib_length_ratchet_exceeded` and `_lib_gate_diff_base`; the `bash -c` sourcing of `_lib.sh` in `claude/.claude/hooks/tests/test_lib_commit_predicates.py:33`; `denials.py`'s cause classifier.

**Before C2.** After C1 merges, the session re-fetches both docs passages M5 quotes from the raw page bodies. It re-runs step 6 and amends the issue's rows and groups to the set C2 will freeze. A row that gains counts takes them only from a new run that replaces the whole table's counts and window (M8). It hands C2's dispatch B's step 3 record, the fetch date and the issue number.

**PR C2: the cap policy and its docs (M2-M5).** About 780 changed lines, most of them deleted override tests. Gated by steps 1, 2 and 5.
- `claude/.claude/hooks/_lib.sh`: M2's sentence at `:3288`.
- `claude/.claude/hooks/check-skill-length.sh`.
- `claude/.claude/scripts/_skill_auxiliary_files.py`.
- `claude/.claude/hooks/tests/test_lib_staged_length_gate.py`: M4's case for M2's sentence.
- `claude/.claude/hooks/tests/test_check_skill_length.py`.
- `claude/.claude/hooks/tests/test_doc_counts.py`.
- `claude/.claude/scripts/tests/test_transcript_denials.py`.
- New `docs/design-decisions/skill-character-cap-for-compaction-reinjection.md`.
- `docs/design-decisions/no-shared-skill-partials.md`.
- `docs/skills.md`, `docs/hooks.md`, `docs/handoff-nudge.md`.
- `.claude/rules/skill-and-agent-self-review.md`.
- `plugins/skill-management/skills/skill-review/SKILL.md`, `plugins/skill-management/skills/skill-review/REFERENCES.md`, `plugins/skill-management/.claude-plugin/plugin.json`.
- `CHANGELOG.md`: M5's entry.

Reuse: the test helpers `run_hook`, `run_hook_reason`, `bash_input`, `build_path_without`, `assert_cap_engaged` and `build_isolated_hook`, and the `git_timeout_shim` fixture; `_count_claude_md_length_hook_limit`'s source-scan shape in `test_doc_counts.py`.

Projected diff: about 2,950 changed lines across the four PRs, leaving out the plan file.

## Verification

1. Gates every PR, before each of its commits: `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py`.
   - A's diff selects the scripts tests, and the evals tests too, since `redaction.py` and `scope.py` sit in `_REVIEW_BENCH_SCRIPTS_DEPENDENCIES`.
   - B's selects every evals test, because it edits `measure_subagent_model_resolution.py`, plus `test_select_tests.py`.
   - C1's includes `test_lib_staged_length_gate.py`, `test_check_skill_length.py` and `test_check_claude_md_length.py`. The two existing suites pass with no edit in C1's diff, and the new direct cases pass, lines cases included. A green existing suite alone does not cover the moved line count.
   - C2's adds the hooks, scripts and plugin tests.
2. Gates every PR, before each of its commits: `scripts/venv-run.sh ruff check claude/.claude/ claude-skills/ plugins/ evals/`. C1 and C2 also run `scripts/list-shell-files.sh | xargs -0 scripts/venv-run.sh shellcheck`.
3. Gates B, and C1's dispatch. It runs by hand, never in CI, in B's worktree after B's last code commit and before B's PR opens.
   - First, the session asks the engineer to approve each case's `--budget-cap-usd` and `--timeout-s` (row 43).
   - Then run `scripts/venv-run.sh python3 evals/measure_skill_reinjection.py --list`, then `--all --json <scratch dir>/skill-reinjection.json` with the approved values as explicit flags. Expected spend is one `--all` run at those caps, plus any re-run.
   - Every expectation prints PASS.
   - The `per-skill` copy is 20,000 code points or 20,000 UTF-16 units, and more than 20,000 UTF-8 bytes, which shows the cut counts characters.
   - If the copy is 20,000 bytes, or any expectation prints FAIL, stop and bring the result to the engineer before any further dispatch. A byte cut reverses the character unit across M1, M3, M4, M5 and row 2, not in C1 alone, and voids the issue's threshold and rows. A FAIL from M6's counter means the issue's figures need a correction. Either way the issue is corrected, by edit or comment, before any further dispatch. Corrected counts come from a new M6 run that step 7 checks first.
   - INCONCLUSIVE means the run failed, not the vendor: fix the run and re-run. After two consecutive INCONCLUSIVE results for one case, stop and bring its exit status and stderr tail to the engineer.
   - After a passing run, a data-only commit records its figures: M7's defaults with their comment, and `evals/README.md`'s runtime cost. That commit does not re-run this step, because the run passed the same values as flags. Any other later commit touching M7 does.
   - B's PR body records, for C1's dispatch and for M5:
     - the PASS lines;
     - the `per-skill` copy's three lengths;
     - the residual's classification and position, and its text when it matches the expected shape;
     - `claude --version`;
     - each case's cost and wall time.

     The API-key line stays in the session, out of the PR body and the README.
4. Gates A. From this checkout, `scripts/venv-run.sh python3 claude/.claude/scripts/transcript-analysis.py skill-reinjection --this-repo` prints the scope header, the totals, and per-skill rows naming only tracked skills. The same command without `--this-repo` exits 2.
   - The compactions-with-an-attachment total is above zero, and at least one truncated copy exists.
   - In code points or in UTF-16 units, the shortest and the longest truncated copy both read 20,000, and the session notes which unit. The longest in UTF-8 bytes is over 20,000, so the range is not all ASCII.
   - The unpaired-attachment, uuid-less-boundary and unmarked-long-copy gaps read zero.
   - If any check fails, stop before A's PR opens and bring the output to the engineer. The output stays in the session.
5. Gates C2. `/code-review` on C2's diff runs `/skill-review` on the `skill-review` edit and `/plugin-semver` on the plugin bump, both hook-enforced at commit. `/skill-review`'s compression audit goes in C2's PR body.
6. Gates M8, after A merges, in B's fresh worktree. Re-derive the over-cap list and its groups.
   - For every path `git ls-files` lists that matches a `SKILL.md` alternative of `check-skill-length.sh:162`'s pattern, count characters with `LC_ALL=C tr -d '\200-\277' < <path> | wc -c`, the pipeline M1 adds. Keep those over 19,000. `wc -m` under a UTF-8 locale serves only as a cross-check.
   - For each kept path, count again without the leading frontmatter block, and add the length of the `Base directory` prefix for the skill's installed directory. A sum over 20,000 puts the skill in group 1.
   - Every kept path must have one of the three shapes M6's tracked-name set keeps. A gated path outside them stops the issue until the engineer decides how to list it.
   - The issue's rows equal the kept set.
7. Gates M8. Before every publication of an M6-derived value in the issue, whether creation, edit or comment, run the check in `docs/private-project-redaction.md` § "New figures against the grandfathered set" on the M6 run it quotes. A re-run's values count as new figures.
   - The session names, for the engineer, each § "Remediation" entry it compared against.
   - If a figure could narrow a grandfathered residual, stop before the publishing `gh` call and ask the engineer, naming what the combination would newly disclose.
   - The body takes its figures only from that run's printed values and step 6's sizes, each beside the command that produced it.

## Out of scope

- Reducing any skill below the cap: the master issue tracks that work.
- Settling row 9's rule conflict: amending a standing rule is the engineer's call, no change here depends on it, and the issue carries it.
- Skills dropped by the 25,000-token total budget: a per-file gate cannot see invocation order, and M6 counts no drops (Approach, Alternatives weighed).
- An invocation's arguments pushing a capped skill past the cut (row 25): the gate cannot see arguments. M7 reports where the residual sits, and M5's file records the margin.
- `agent-review`'s 200-line target: agents are not re-attached after a compaction, and this hook does not gate them.
- `check-claude-md-length.sh`'s caps: M1 leaves its behavior unchanged, and only M2's sentence reaches it.
- The fail-open on a missing awk, grep or wc: an existing known-bug pin, which M4 carries over rather than fixes. A missing `tr` already fails closed at `check-skill-length.sh:112-114`.
- The HEAD-timeout false deny pinned at `test_check_skill_length.py:1140`: existing and separate.
- Splitting `test_check_skill_length.py` under the code-file line limit (`docs/reports/2026-11-19-code-file-size-offenders/findings.md:204`): this change shrinks the file, and the split stays its own work.
- Changing the publication rule in `docs/private-project-redaction.md` (row 29), including widening `--this-repo` to a removed worktree's sessions (row 40): it is the owner's privacy policy, and this plan's figures fit inside it.
- Changing the stow install model (row 30): every `claude/` change ships this way, and the CHANGELOG entry covers the migration.
- Moving the four inline `compact_boundary` checks (`cache_efficiency.py:103`, `context_composition.py:87`, `read_scope.py:165`, `read_cost.py:343`) onto one shared predicate: they work today, and the move is its own refactor.
- `plan-review/REFERENCES.md:28` and the line-cap mentions under `docs/design-decisions/` other than `no-shared-skill-partials.md`: they record why past changes were made (Scope discipline, Axis 3).
