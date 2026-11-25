# Rewrite legacy-sentinel prose to point at config-set.sh

## Context

Goal: prose that tells a reader to `touch` or `rm` a legacy sentinel file to switch a config key points at `~/.claude/scripts/config-set.sh` instead, finishing what the setter adoption started.

Ask: "/handoff to rewrite the legacy sentinel prose" — the engineer's request that produced the handoff this work resumes from; confirmed in this session via label "Yes, that is my ask".

Why now: the setter (#1579), its newline and lease fix (#1561) and the doc swaps for `printf >>` and three README `touch` sites (#1610) are merged. Sentinel-touching prose remains in `docs/` and in `claude/.claude/hooks/*.sh` header comments. `docs/config-file.md` is the canonical home for legacy-sentinel semantics. Scope:
- Changes: only prose that tells a reader a legacy file is the way to switch a key.
- Stays: prose that explains the still-live fallback.
- Stays: records under `docs/design-decisions/`, `docs/reports/` and `docs/case-studies/`.
- Stays: the per-repo `worktree-optout` marker in `README.md`, because the setter does not own it.

Intended outcome: every non-record instruction to flip a key points at the setter, with `test_config_set_doc_call_sites.py` still passing. `claude/` installs to every stow consumer, so the surface is every stow user.

## Approach

Eleven sites tell a reader that a legacy file switches a config key: six in five hook header comments and five in `docs/hooks.md` entries. Each now names the key instead. The two sites that are their key's `docs-anchor` (the `config-keys.psv` column) carry the literal `~/.claude/scripts/config-set.sh` command in backticks, and `EXPECTED_SITES` pins them. The other nine name the key and point at the `docs-anchor` section that already holds the command. The fallback explanations, the per-repo markers and the `pr_cost_disclosure` descriptions stay.

Alternatives weighed:
- **A literal setter command at every site, with each file added to `EXPECTED_SITES`** (the dispatching session's default, row 14). Set aside for the hook headers and three of the `docs/hooks.md` entries. Those keys' commands already live at their `docs-anchor` in both directions under a named section (row 3), so a literal there would be a second or third copy of one command. No hook header comment and no `docs/hooks.md` entry carries one today (rows 2, 5). It would also add six files to `EXPECTED_SITES` to pin comment text.
- **Point every site at `docs/config-file.md` § "Writing a value".** Set aside: that section gives only the generic `<key> <value>` form, while each `docs-anchor` section gives the exact command and the value that turns the feature on or off.
- **Name the key with no pointer.** Set aside: the reader then has no path to the command. `docs/hooks.md:209`, the closest precedent, pairs the key with a link.
- **A permanent drift-test rule that flags a `touch` of a legacy file.** Set aside as heavier than this change needs. The site set is closed and enumerated (row 6), and Verification step 4 re-checks it once for this PR. A permanent rule would need its own grammar and controls in `test_config_set_doc_call_sites.py`. `.claude/plans/config-setter.md` made the same call for its own `touch` sites.

### Assumption ledger

**Root:** Eleven sites in five hook headers and five `docs/hooks.md` entries tell a reader that touching a legacy file, or its presence or absence, switches a config key. Once the key has a row in `claude-config.toml`, the legacy file is never consulted (`docs/config-file.md:109-112`). `install.sh`'s opt-in prompt, its `migrate-legacy-config.sh` step and `config-set.sh` all write rows (row 1). So for every stow consumer whose key has a row, following the instruction silently changes nothing.

**Givens:**
- G1. Every legacy file stays readable permanently, because the fallback has no removal date (`config-keys.psv:65-68`). Prose that explains the fallback therefore stays true, and it stays. Reason: the schema design owns the fallback's lifetime, and removing the fallback needs a decision outside this plan.
- G2. Rule 4's docstring in `test_config_set_doc_call_sites.py` and the pointer in `docs/handoff-nudge.md` stay as they are. Reason: the handoff records both as decisions settled in the prior branch's review, outside this plan. The dispatching session relayed this, and I did not read the handoff.

**Mechanisms:**
- **M1.** Five hook header comments name the key and say which doc holds its `config-set.sh` command. None carries a literal command, and Critical files gives each one's text. Three further edits ride along in the same files:
  - Two cross-references to `.handoff-nudge-disabled` as a "convention" are removed, because the convention they cite is the legacy file.
  - "globally" and "machine-global" are dropped from the rewritten sentences, because each key resolves per config dir (row 8). The two further "machine-global" mentions in `set-session-title-from-branch.sh` (`:8` and the `:81` banner) change to match.
  - The "See CONTRIBUTING.md" pointer in `nudge-error-mode-analysis.sh` goes straight to `docs/error-mode-nudge.md`, which `CONTRIBUTING.md` defers to (row 11).

  Two headers point at their `docs/hooks.md` entry, which M3 gives the literal: `consume-durable-continuity-file-on-read.sh` and `set-session-title-from-branch.sh`. The other three point at their feature doc's section.

  anchors: root, row2, row3, row4, row8, row11, row13, row14
- **M2.** Three `docs/hooks.md` entries whose key has its own feature doc name the key and cite that doc's section, in the form line 209 uses. They are line 206 (`handoff_nudge`), line 208 (`error_mode_nudge`) and line 430 (`permission_prompt_tracking`). Lines 208 and 430 state a condition ("Dormant unless … exists") rather than give an instruction, but they name the legacy file as the switch, as line 206 does, so they change too.

  anchors: root, row3, row5, row6, row12, row14
- **M3.** The two `docs/hooks.md` entries that are their key's `docs-anchor` carry the literal command in backticks: line 350 (`session_title_from_branch`) and line 428 (`consume_durable_continuity`). Line 350 keeps the per-repo `.claude/session-title-disabled` file, which has no key (row 18). Line 350 was not in the discovery list, and it has the same shape as line 208 (row 6).

  anchors: root, row4, row6, row7, row14, row18
- **M4.** `EXPECTED_SITES` gains `docs/hooks.md` with its two pairs, so rule 4 reports either site if it is lost or changed. Nothing fails without the entry (row 7), so the entry adds protection rather than fixing a failure.

  anchors: row7, row14
- **M5.** No `# tier-threat-model:` line is added, and no other test changes. The tier framework and its test cover only `hook-class: gate` hooks, and none of the five is one (row 9). No test pins the replaced prose (row 10). Edits under `claude/.claude/hooks/` reach every stow consumer on `git pull`, but these are comments, so no consumer's hook behavior changes.

  anchors: row9, row10
- **M6.** Every other site stays: the fallback explanations (G1), the per-repo markers (row 18) and the `pr_cost_disclosure` descriptions (rows 16, 17). Out of scope lists them.

  anchors: root, row15, row16, row17, row18

**Rows:**
1. A conforming row is authoritative, and a legacy file re-created or edited after the key has a row never wins (`docs/config-file.md:102-112`). `install.sh`'s opt-in prompt writes a row on either answer (`install.sh:544`, `:582`). `install.sh` also runs `migrate-legacy-config.sh`, which imports legacy values as rows (`install.sh:788`). [verified: reads]
   (Correction from review: the opt-in prompt writes a row only when the answer changes the state, at `install.sh:544` for N and `:582` for Y, and it reaches only `permission_prompt_tracking` and `error_mode_nudge`. For the three presence-disables keys a consumer with no import and no setter call has no row, so the legacy file still works for them. The rewrite is still right, because the instruction is wrong for every consumer whose key has a row.)
2. Three hook headers already name their key: `advance-past-commit-stall.sh:26-28`, `nudge-memory-store-audit.sh:22-26` and `restore-authorization-boundary-on-compact.sh:25-26`. The last two point at a doc for the details. No hook header comment carries a literal setter command. The one literal in a hook is the runtime Stop reason at `advance-past-commit-stall.sh:259`. [verified: reads, Grep of `claude/.claude/hooks/*.sh` for `config-set.sh`]
3. The feature doc for each of three keys holds its setter command in both directions under a named section: `docs/handoff-nudge.md` § "How to disable" (`:103-114`), `docs/error-mode-nudge.md` § "How to enable" (`:7-18`), and `docs/permission-prompt-tracking.md` § "Activation" (`:3-6`) with its "How to disable" section (`:23-28`). Each doc is that key's `docs-anchor` (`config-keys.psv:87, 88, 93`), and `EXPECTED_SITES` pins those sites (`test_config_set_doc_call_sites.py:101-111`). [verified: reads]
4. `consume_durable_continuity` and `session_title_from_branch` have the `docs-anchor` `docs/hooks.md § Utility hooks` (`config-keys.psv:95, 97`). Both entries sit under that heading, which runs from `docs/hooks.md:200` to `:433`. `docs/hooks.md` carries no `config-set` text today. So for these two keys the `docs/hooks.md` entry is the only user-facing home. [verified: reads, Grep]
5. `docs/hooks.md` names a key and points at a doc at lines 170, 173, 209 and 244, and it holds no literal setter command. [verified: Grep]
6. The site set is closed. A case-insensitive Grep for `touch` within 60 characters of any of the 15 legacy file names (`config-keys.psv:86-100`) runs over the repo minus records, tests, plans, `.gitignore` and `CHANGELOG.md`. It matches only `consume-durable-continuity-file-on-read.sh:31`, `nudge-error-mode-analysis.sh:37`, `nudge-handoff-near-context-cap.sh:20`, `track-permission-prompts.sh:32` and `docs/hooks.md:428`. A Grep for "exists", "absence", "remov", "delet" and "creat" near those names adds `track-permission-prompts.sh:6`, `docs/hooks.md:208` and `docs/hooks.md:430`. Reading every match of the names adds the sites that name the file as the switch: `set-session-title-from-branch.sh:40-41`, `track-permission-prompts.sh:31`, `docs/hooks.md:206` and `docs/hooks.md:350`. Skills, plugins, agents, rules, `CONTRIBUTING.md`, `install.sh` and `claude/.claude/scripts/` hold no `touch` instruction. [verified: Grep]
7. A site is the literal `~/.claude/scripts/config-set.sh`, a lowercase key and a value word on one line. A closing backtick ends the value word, so no trailing word is reported (`test_config_set_doc_call_sites.py:72-79`, `:199-214`). Rule 4 checks only files listed in `EXPECTED_SITES`, and it compares order only among one key's sites (`:260-273`). `docs/config-file.md:261-264` carries sites in an unlisted file, so listing a file is not needed to pass. Both new keys are `bool` (`config-keys.psv:95, 97`) and neither is enforcement-critical (`config-keys.psv:81-82`), so rule 2 skips them (`:228`). [verified: reads]
8. `handoff_nudge`, `consume_durable_continuity` and `session_title_from_branch` default to `true`, so `false` turns each off. `error_mode_nudge` and `permission_prompt_tracking` default to `false`, so `true` turns each on. All five resolve `config-dir`, which is per config dir, not machine-wide (`config-keys.psv:87, 88, 93, 95, 97`). [verified: read]
9. The tier framework covers `hook-class: gate` hooks only (`docs/hooks.md:7`). `test_hook_alignment.py:148` selects hooks for the tier-line test by `hook-class == "gate"`, and `:2138-2160` requires the line only of those. Four of the five hooks are `informational`. `nudge-handoff-near-context-cap.sh:2` is `batch-gate`, which is not `gate` (`test_nudge_handoff_near_context_cap.py:1189`). The edits are comments only, so no matcher, registration or exit path changes, and the regression-only rule has no behavior to compare. [verified: reads]
10. No test reads the five hooks' header comments or the five `docs/hooks.md` sentences. The legacy file names in hook tests are fixtures the tests create. [verified: Grep of `claude/.claude/**/tests/*.py`]
11. `CONTRIBUTING.md:23` defers to `docs/error-mode-nudge.md` for enabling and disabling the nudge. [verified: read]
12. No test resolves a citation in `docs/` to its heading. `test_skill_citation_grammar.py:76-90` resolves only skill-tree citations. `:136-158` checks only that a citation in `docs/` is extracted, which needs the whole citation on one line. [verified: read]
13. A `#` comment block states each non-obvious fact in one sentence and cites `docs/` by path for elaboration (`claude/.claude/rules/shell-script-conventions.md`). [verified: read]
14. The dispatching session's default (1), which is that session's choice and not the engineer's: literal `config-set.sh` commands in backticks, with matching `EXPECTED_SITES` entries. This plan keeps the default only at the two sites that are a key's `docs-anchor` (M3, M4), and it points the other nine at the `docs-anchor` (M1, M2). [unverified]
15. The dispatching session's default (2): leave the fallback explanations and the per-repo markers alone. This plan keeps it (G1, row 18). [unverified]
16. The dispatching session's default (3): `docs/private-project-redaction.md:174`, `docs/transcript-analysis.md:801` and `claude-skills/skills/pr-description/SKILL.md:110` stay. This plan keeps it, because each describes the `pr_cost_disclosure` gate as a file and none tells the reader to touch one. [unverified]
17. `pr-cost-section.sh:23` reads `_config_value pr_cost_disclosure`, so its own header (`:2-11`), `pr-description/SKILL.md:87, 102, 110-113` and the two docs in row 16 describe the gate inaccurately for a reader whose key has a row. [verified: reads]
18. The per-repo `.claude/session-title-disabled` file is a direct `[ -f ]` check with no schema key (`set-session-title-from-branch.sh:147`), so the setter cannot switch it. [verified: read]
19. The `Ask:` line's wording is the engineer's own for this task. [engineer-verified: "Yes, that is my ask"]
20. The `EXPECTED_SITES` entry for `docs/hooks.md` (M4, about 4 lines, not needed to pass) stays in this PR. [engineer-verified: "Keep it (Recommended)"]

## Critical files

One `code-writer` dispatch covers all seven files. Every edit applies one rule: the literal command goes at a key's `docs-anchor`, and every other site names the key and points there. Split dispatches would each restate that rule and could apply it differently. Its verification is Verification steps 1-5.

`claude/.claude/hooks/consume-durable-continuity-file-on-read.sh`: replace lines 31-37 with:

```text
# Kill switch: the consume_durable_continuity config key, on by default.
# docs/hooks.md's entry for this hook has the config-set.sh command.
# It is the local opt-out lever, since the hook (unlike its plugin-scoped
# precedent, consume-migration-token.sh) ships in the globally-stowed
# claude/.claude/hooks/ and fires for every stow user unconditionally.
```

`claude/.claude/hooks/nudge-handoff-near-context-cap.sh`: replace lines 20-22 with:

```text
# Kill switch: the handoff_nudge config key set to false suppresses all
# nudges, including the hard block above (useful when running automated
# pipelines).
# docs/handoff-nudge.md "How to disable" has the config-set.sh command.
```

`claude/.claude/hooks/nudge-error-mode-analysis.sh`: replace lines 37-39 with:

```text
# Opt-in: dormant by default. Until the error_mode_nudge config key is true,
# every invocation exits 0 before reading the transcript.
# docs/error-mode-nudge.md "How to enable" has the config-set.sh command.
```

`claude/.claude/hooks/set-session-title-from-branch.sh`: replace lines 40-43 with:

```text
# Kill switches:
# - the session_title_from_branch config key; docs/hooks.md's entry for this
#   hook has the config-set.sh command.
# - the per-repo <main-worktree-root>/.claude/session-title-disabled file,
#   resolved against the main worktree root this hook already computes, never cwd.
```

In the same file, line 8 changes "a kill switch is present (machine-global or per-repo)" to "a kill switch is present (config key or per-repo)", and the line 81 banner changes "machine-global kill switch" to "config kill switch".

`claude/.claude/hooks/track-permission-prompts.sh`: replace line 6 so that lines 5-6 end "…JSONL log, when the permission_prompt_tracking config key is true." Replace lines 31-32 with:

```text
# Opt-in: the permission_prompt_tracking config key, off by default.
# docs/permission-prompt-tracking.md "Activation" and "How to disable" have
# the config-set.sh commands.
```

`docs/hooks.md`: replace one sentence inside each of five one-line entries, and leave the rest of each line unchanged:

```text
206 old: Opt-out via `<config-dir>/.handoff-nudge-disabled`.
206 new: Opt out with the `handoff_nudge` config key (`docs/handoff-nudge.md` § "How to disable").
208 old: Dormant unless `<config-dir>/.error-mode-nudge-enabled` exists.
208 new: Dormant until the `error_mode_nudge` config key is `true` (`docs/error-mode-nudge.md` § "How to enable").
350 old: Kill switches: machine-global `<config-dir>/.session-title-disabled` and per-repo `<main-worktree-root>/.claude/session-title-disabled`.
350 new: Kill switches: `~/.claude/scripts/config-set.sh session_title_from_branch false` for the config dir, and a per-repo `<main-worktree-root>/.claude/session-title-disabled` file.
428 old: On-by-default; opt out per-machine by touching `<config-dir>/.consume-durable-continuity-disabled`, mirroring `nudge-handoff-near-context-cap.sh`'s kill-switch convention.
428 new: On by default; opt out with `~/.claude/scripts/config-set.sh consume_durable_continuity false`.
430 old: Dormant unless `<config-dir>/track-permission-prompts` exists.
430 new: Dormant until the `permission_prompt_tracking` config key is `true` (`docs/permission-prompt-tracking.md` § "Activation" and § "How to disable").
```

`claude/.claude/hooks/tests/test_config_set_doc_call_sites.py`: in `EXPECTED_SITES`, add this entry between `"docs/handoff-nudge.md"` and `"docs/memory-audit-nudge.md"`. Leave the module docstring unchanged (G2).

```python
    "docs/hooks.md": (
        ("session_title_from_branch", "false"),
        ("consume_durable_continuity", "false"),
    ),
```

Reuse: the `docs-anchor` column of `config-keys.psv` decides where each literal goes. `docs/hooks.md:209` is the form for an entry, and `restore-authorization-boundary-on-compact.sh:25-26` is the form for a header.

Projected diff: about 58 lines: about 44 across the five hooks, 10 in `docs/hooks.md` and 4 in the test.

## Verification

1. `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py` passes. Which domains it selects for this diff is unverified. If its selection leaves out `claude/.claude/hooks/tests/`, report that as a rule-table bug rather than widening the run.
2. `scripts/venv-run.sh pytest claude/.claude/hooks/tests/test_config_set_doc_call_sites.py` passes. A pass of `test_each_documented_file_carries_its_expected_sites` shows both new `docs/hooks.md` sites parse as exactly the two listed pairs. A pass of `test_every_site_names_a_schema_key_and_a_value_its_type_accepts` shows the setter accepts both.
3. `scripts/venv-run.sh ruff check claude/.claude/hooks/tests/test_config_set_doc_call_sites.py` is clean, and `scripts/venv-run.sh shellcheck` on the five hook paths is clean.
4. A one-time closure check for this PR, not an ongoing guard. Build the alternation `NAMES` from the 15 non-empty legacy-filename values in `config-keys.psv:86-100`. Search `docs/`, `README.md`, `claude/.claude/` (excluding its `tests/` directories), `claude-skills/`, `plugins/`, `install.sh` and `scripts/`, skipping `docs/design-decisions/`, `docs/reports/`, `docs/case-studies/` and `CHANGELOG.md`.
   - `touch` pass: `git grep -n -i -E "touch.{0,60}(NAMES)|(NAMES).{0,60}touch"` returns no line. Both directions run.
   - Existence pass: the same two-direction form with `exist|absen|remov|delet|creat` in place of `touch` returns only sites the Out of scope section lists.
   - In the seven changed files, the pattern `\.handoff-nudge-disabled|\.error-mode-nudge-enabled|\.consume-durable-continuity-disabled|\.session-title-disabled|track-permission-prompts($|[^.]|\.($|[^s]))` returns no line. The final alternative catches a sentence-ending period after the name and still skips `track-permission-prompts.sh`.
   - Closure: every remaining hit of `NAMES` is a hook-filename mention, a code line, or listed under Out of scope.
5. Each cited heading exists verbatim: `## How to disable` in `docs/handoff-nudge.md`, `## How to enable` in `docs/error-mode-nudge.md`, and both `## Activation` and `## How to disable` in `docs/permission-prompt-tracking.md`. Each of the five key names also appears in column 1 of `config-keys.psv`. Both are checked by hand because no test resolves a citation in `docs/` or a key name in prose (row 12).

## Out of scope

- Belongs in a separate change: the `pr_cost_disclosure` descriptions in `claude-skills/skills/pr-description/SKILL.md:87, 102, 110-113`, `docs/private-project-redaction.md:174`, `docs/transcript-analysis.md:801` and `claude/.claude/scripts/pr-cost-section.sh:2-11`.
  - They describe the gate as the `pr-cost-disclosure` file while the script reads the key (row 17), so they are stale descriptions, not instructions to touch a file, and fall outside the Ask.
  - A `SKILL.md` edit needs the hook-enforced `/skill-review`.
  - The dispatching session reports that `tests/test_pr_lifecycle_skills.py:563` asserts `pr-cost-disclosure` in that body. This is its report, not checked here.
- Descriptions that name the sentinel files or a machine scope but give no instruction: `docs/hooks.md:160` ("same sentinel files"), `require-worktree-for-git-writes.sh:6-7`, `require-worktree-for-file-writes.sh:6-7`, `install.sh:643, 645`, `migrate-legacy-config.sh:41, 164`, `config-keys.psv:97` ("machine-wide"), and "per machine" in `docs/error-mode-nudge.md:19` and `docs/permission-prompt-tracking.md:9`. `config-keys.psv` is a schema file with its own review path.
- The fallback explanations (G1): `docs/commit-stall-block.md:47, 77`, `docs/hooks.md:170, 173, 244, 257, 445`, `docs/memory-audit-nudge.md:125`, `docs/config-file.md:125, 205, 301`, `docs/pr-cost.md:373, 400`, `README.md:296, 350`, `claude/.claude/hooks/_lib.sh:3354, 3359-3361`, `advance-past-commit-stall.sh:27` and `nudge-memory-store-audit.sh:25`. I re-read every one of these except `README.md` and `_lib.sh`, whose classification comes from the discovery pass.
- Per-repo markers with no schema key, which the setter does not own: `.claude/session-title-disabled` (row 18), the repo-committed `.claude/worktree-required` and the `worktree-optout` marker (`README.md:310-356`), and `docs/agent-branch-records.md:15`.
- Comments that describe the code rather than tell a reader how to switch a key, such as `set-session-title-from-branch.sh:7-8, 81-85` and `consume-durable-continuity-file-on-read.sh:108`.
- A permanent drift-test rule for `touch` instructions (Approach, alternatives weighed).
- Records under `docs/design-decisions/`, `docs/reports/` and `docs/case-studies/` (Context).
