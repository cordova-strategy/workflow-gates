# Config setter: a sanctioned CLI for writing `claude-config.toml`

## Context

Goal: replace the raw `printf '\nkey = value\n' >> .../claude-config.toml` one-liner, the documented write path today, with a sanctioned setter command.

Ask: "yeah I think a setter is the way to go. and yeah you should do a follow-up." Scope answers, as selected labels: "Allow, with notice (Recommended)" for writing the permissive value of the four enforcement-critical keys, and "Setter command (Recommended)" for what the Stop hook's block reason hands the agent. Widened in plan review round 1, as selected labels: "Add four ask rules (Recommended)", "Add supersession note (Recommended)", "Add the qualifier (Recommended)" and "Add both (Recommended)".

Why now: the previous PR patched the symptom of an unterminated last line in each of the 15 executable one-liners. A setter fixes the cause, since no copy has to stay correct by hand. The Root line under `## Approach` states the cause in full.

Intended outcome: one script that every doc, README section and hook block reason points at, so no documented path appends to the file by hand.

Evidence: the ledger rows under `## Approach` hold each fact with its source. Facts no row holds: `docs/design-decisions/sentinel-config-consolidation.md` says "five" critical keys in places and names `autonomous_shipping`, while the schema and the migrator list four, and this plan treats the schema as authoritative.

The cause to state in prose is an "unterminated last line", and the plan does not describe the current warning behavior as silent, since `_config.sh` prints a `skipping malformed line` warning.

Threat framing: `claude/` installs to every stow consumer, so the user surface is every stow consumer. A new documented write path to enforcement-critical keys needs a classification stated in the plan, and the tier convention is silent on non-hook scripts (row 19).

## Approach

Add `claude/.claude/scripts/config-set.sh <key> <value>`, a thin CLI over the existing `_config_set` writer, and point every documented write path at the one command `~/.claude/scripts/config-set.sh <key> <value>`. Those paths are the 15 `printf … >>` one-liners, the Stop hook's block reason, and `migrate-legacy-config.sh`'s hint for a deferred permissive value. The script writes any schema key in either direction and names the file it wrote on stderr. When it writes the permissive value of one of the four enforcement-critical keys, it also prints a `notice:` line, and the exact command for each of those four writes carries a declared `permissions.ask` rule whose prompt is unobserved (M10). It exits 0 only when the key then resolves to the requested value.

`_config_set` already reads an unterminated last line correctly and rewrites the whole file with a newline after every line (rows 1, 4). So the setter removes, from every documented path, the joined row that an append onto an unterminated last line produces, with no reader change. Two moves into `_config.sh` keep the setter from adding a third copy of a rule: the value-type check `_config_set` holds today (M2), and the enforcement-critical key list with its fail-closed values, which `migrate-legacy-config.sh` holds today (M3). Both `_config.sh` writers also stop replacing a state file they cannot read (M13). The design record's rule for enforcement-critical write paths gets an in-place note saying the setter relaxes it (M14). A permanent test keeps every documented call site valid, and holds every documented permissive command to the spelling its ask rule names (M15).

Alternatives weighed:
- **Keep the append, patched with a leading `\n`.** Rejected: each of the 15 copies stays correct only while it keeps that `\n`, and an append adds a second row for a key that already has one instead of rewriting it (`docs/config-file.md:249-251`).
- **A `set` verb on `config-get.sh`.** Rejected: that script is read-only by contract and rejects `set` (`config-get.sh:30-34, 48-51`), and `test_config_py.py:553-557` pins the rejection.
- **Tell readers to edit the file in an editor, with no command.** Rejected: the Stop reason has to hand the agent a runnable command (row 12).
- **A Python twin in `_config.py`.** Rejected: nothing in Python writes the file (row 9).
- **A louder reader warning, or a last-byte check in the reader.** Rejected in M7.
- **Refuse, confirm, or TTY-gate the permissive direction inside the script.** Rejected: the engineer chose to allow it with a notice (row 10) and chose harness ask rules (row 30), and a check inside the script cannot show that a human answered (G2).

### Assumption ledger

**Root:** The documented way to change a `claude-config.toml` key is a `printf '\nkey = value\n' >> …` one-liner, copied into 15 places, the Stop hook's block reason among them (row 18). Each copy is correct only while it keeps its leading `\n`: an append onto an unterminated last line joins two rows, which `_config.sh` warns about and skips (`_config.sh:369`). An append also adds a second row for a key that already has one, so every documented "set it back" step leaves a duplicate row behind (`docs/handoff-nudge.md:111-115`).

**Givens:**
- G1. Whether Claude Code's own permission prompt fires for an agent's Bash write to `claude-config.toml` that no ask rule names is unverified (`docs/config-file.md:230-233`). Reason: Claude Code owns the permission system, and this repo cannot observe or change when it prompts.
- G2. A `[ -t 0 ]` check cannot show that a human answered a prompt, because one Bash call can allocate its own pseudo-terminal. The bullet at `docs/design-decisions/sentinel-config-consolidation.md:29` reads, whole:

  > **`[ -t 0 ]` is not a security boundary:** a single Bash call can self-allocate a pseudo-terminal (`script -qc "..." /dev/null`) and satisfy the check with no human involved, since the check runs inside the very subprocess it is meant to constrain. A TTY check cannot mechanically prove a human is at the other end of a prompt — every enforcement-critical write path must therefore be one where impersonating the human buys nothing, or must not exist.

  Reason: the operating system's pseudo-terminal mechanism imposes the fact. The bullet's closing rule is not a given, and this plan relaxes it for the setter (row 11, M14).

**Mechanisms:**
- **M1.** New `claude/.claude/scripts/config-set.sh`, mode 755. Its header states the usage, the exit-code table, that it writes through `_config_set`, and that only `set` and comments precede the source line. It omits `-e` because it maps every status to its own exit code, as `config-get.sh:2` does. The header is the table's only home, as `config-get.sh:7-14` is for reads. The script runs in this order:
  1. `set -uo pipefail`, then the `# shellcheck source=../hooks/_config.sh` line and `. "$(dirname "$0")/../hooks/_config.sh" || exit 3`, as `config-get.sh:2, 38-39` do (row 3).
  2. Not exactly two arguments: a usage line on stderr that names `docs/config-file.md`, then exit 2.
  3. `key_type=$(_config_schema_field "$KEY" type)`. Status 3: `config-get.sh`'s schema-unreadable message, exit 3. Any other nonzero status: `unknown key '<key>'`, exit 2. This mapping is `config-get.sh:58-71`'s, kept identical on purpose. So a truncated `type` column (status 4) also reports as an unknown key. `_config.sh` prints its own truncated-row warning for that row. The mapping is repeated rather than shared, because it is three arms whose messages each name their own script.
  4. `_config_type_accepts "$key_type" "$VALUE"` (M2) fails: name the values the key accepts (`true` or `false`, or `false` or the enum literal) and say VALUE is passed bare, then exit 2.
  5. `config_dir=$(_lib_config_dir)`. Nonzero status: `config-get.sh`'s unresolvable-config-dir message (`config-get.sh:76`), exit 3.
  6. `_config_set "$KEY" "$VALUE" "$config_dir"`, so the file written is the one step 5 resolved. By status:
     - 2: the unresolvable-config-dir message, exit 3.
     - 3: say `<config-dir>/claude-config.toml` exists but cannot be read and nothing was written, then exit 3 (M13).
     - 1: run `_config_value "$KEY" >/dev/null`, so the reader prints its `skipping malformed line` warning naming the line (`_config.sh:369`). Then say nothing was written to the named file, and exit 1. The cause is a line outside the grammar or a failed write.
  7. Status 0: print `config-set.sh: wrote <config-dir>/claude-config.toml` on stderr, then the notice (M3) when it applies.
  8. `resolved=$(_config_value "$KEY")`. Status 2, 3 or 4: exit 3. A `resolved` that differs from VALUE: say the row was written but the key still resolves to `resolved`, point at `docs/config-file.md` § "Resolution precedence", and exit 1 (row 5).
  9. The resolved value on stdout, as `config-get.sh` prints it, then exit 0. No nonzero exit prints anything on stdout.

  The exit codes:
  - 0: the key now resolves to VALUE.
  - 1: the arguments were valid, but the key does not resolve to VALUE. Either nothing was written, or the row was written and another source overrides it.
  - 2: usage, an unknown key, or a value the key's type rejects.
  - 3: environment.

  2 and 3 keep `config-get.sh`'s meanings. The header states that exits 1 and 3 do not imply an unchanged file, names the override case, and says the stderr `wrote` line marks every run that replaced the file. The script reuses `_config_set`'s validation, in-place rewrite and `mktemp`+`mv` (row 1). It adds only argument checks, the written-path line, a read-back and the notice.

  anchors: root, row1, row2, row3, row4, row5, row9, row13, row42
- **M2.** Move `_config_set`'s value-type `case` (`_config.sh:1139-1153`) into a new `_config_type_accepts KEY_TYPE VALUE`, placed beside `_config_quote_value_for_write` (`:1067-1084`). `_config_set` calls it and returns 1 when it fails, so `_config_set`'s results do not change (row 2). The setter calls it before writing, so a rejected value gets its own message and exit 2. The reader's own copy of the rule stays as it is (row 7).

  anchors: row2, row7
- **M3.** Move `_MIGRATE_ENFORCEMENT_CRITICAL_KEYS` and `_migrate_enforcement_critical_safe_value` (`migrate-legacy-config.sh:30-61`) into `_config.sh` as `_CONFIG_ENFORCEMENT_CRITICAL_KEYS` and `_config_enforcement_critical_safe_value`. The function first sets `_CONFIG_SAFE_VALUE=""`, as the migrator's version does (`:53`), then sets the key's fail-closed value, and returns 1 for any other key. `_MIGRATE_SAFE_VALUE` becomes `_CONFIG_SAFE_VALUE` at its two readers. One is `migrate-legacy-config.sh:293`. The other, `test_migrate_legacy_config.py:826`, sits in a class that moves into `test_config_lib.py` as `TestEnforcementCriticalSafeValues`, which reads `_CONFIG_SAFE_VALUE` there. Each moved comment keeps only its one-line facts: the list matches the schema's header comment, and the safe value is deliberately not the `legacy-probe-on-resolution-failure` column. The migrator calls the moved names at `:283-293` and keeps no copy.

  After `_config_set` returns 0, when the function returns 0 and VALUE differs from `_CONFIG_SAFE_VALUE`, the setter prints `config-set.sh: notice: <key> is enforcement-critical, and <value> relaxes <human-name> for every session that uses <config-dir> once nothing else overrides this row. To restore it: <$0> <key> <safe value>`. The notice prints before the read-back, so it also prints when another source still overrides the row and the setter exits 1 (row 5). `<human-name>` comes from the schema's `human-name` column through `_config_schema_field`, and `<config-dir>` is M1 step 5's value. The notice never changes the exit code. The four-key list stays in two places, the schema's header comment and `_config.sh` (row 8).

  Alternatives checked:
  - A third copy in the setter. It duplicates a rule, against CLAUDE.md's "Single source of truth".
  - Sourcing the migrator for its variable. It ties the CLI to the migrator's internal names and to its `set -euo pipefail` (`migrate-legacy-config.sh:20`).
  - A schema column, the heavier option. It changes every 11-field `IFS='|' read` of `config-keys.psv` in both readers, and a `config-keys.psv` change triggers `claude-hook-review` (`.claude/rules/review-pipeline-dispatch.md`).

  anchors: row6, row8, row10, row11
- **M4.** The script itself asks for no confirmation, checks no TTY and refuses no permissive write. The engineer chose a notice (row 10). A check inside the script would claim a human answered when it cannot know (G2). A refusal would leave agents only the append they can already make (row 26). The human prompt the engineer chose is the harness's own, through the four ask rules (M10). Claude Code's documentation says an ask rule prompts before the command runs, outside the script's process, and this plan has not observed that for these rules (row 33).

  anchors: row10, row11, row26, row30
- **M5.** The Stop reason (`advance-past-commit-stall.sh:254`) keeps its text through "or say what is blocked." It then adds the sentence `Run the following command only when the engineer tells you to, and do not offer or ask to run it.` (row 38). The sentence keeps the reason's own rule: the agent still continues or says what is blocked, and does not stall on asking whether to disable the hook. The unchanged literal `To disable this on this machine: ` follows, and the reason ends with `~/.claude/scripts/config-set.sh commit_stall_block false`, the exact command one of the four ask rules names (M10). The reason tests assert that match against `claude/.claude/settings.json`.

  The literal `~/.claude/scripts/` form is the repo's form for agent-run scripts. The hook itself runs from the literal `~/.claude/hooks/` path. So the scripts directory sits beside any hook that fires (row 14).

  The command acts on the config dir its own shell resolves from `CLAUDE_CONFIG_DIR` and `HOME`, as `docs/config-file.md` § "Querying a value" says of reads. Today's reason instead embeds the hook's resolved path (row 15). The setter's stderr `wrote` line names the file it changed, and that line is how the agent and the engineer see which config dir the command reached (M1 step 7). One reason test runs the hook and the command under different config dirs, and pins that the command writes its own shell's while the hook keeps blocking (row 47).

  Two other forms were set aside:
  - `${0%/*}/../scripts/config-set.sh`, the form 2 hooks use to run a sibling script (`bootstrap-project-plugins.sh:107`, `restore-session-state-on-compact.sh:42`). It would print a `hooks/../scripts` path that carries the user's home directory.
  - `$CONFIG_DIR/scripts/config-set.sh`, the form 4 hooks use (`activate-handoff-bypass.sh:89`, `announce-branch-review-history.sh:59`, `consume-durable-continuity-file-on-read.sh:130`, `nudge-error-mode-analysis.sh:144`). It prints a per-account path, unlike the `~/.claude/scripts/` form every doc site uses. It works only where that config dir is itself a stow target, which `README.md:94` does not promise.

  anchors: row12, row14, row15, row16, row37, row38, row47
- **M6.** For a deferred permissive value, `migrate-legacy-config.sh:296-298` prints a lead line ending `To accept it, run this command only on the engineer's explicit instruction:` and then the line `  ~/.claude/scripts/config-set.sh <key> <value>`, in place of a line to add by hand (row 38). The comment at `:290-291` says the value is printed as that command. The import still never writes that value itself (row 17). Every value it defers is a critical key's `false`, so the printed command is one an ask rule names (M10). The hint test asserts that match against `claude/.claude/settings.json`.

  anchors: row17, row37, row38
- **M7.** No reader change. An unterminated last line is harmless to every reader and to the setter (row 4). The joined row arises only from an append, and no documented path appends once M9 lands. A hand append stays possible: the reader's existing `skipping malformed line` warning reports the joined row, and the setter refuses to write until it is fixed (M1 step 6). A last-byte check would add a read to the path every hook takes, for a case the setter removes from the docs.

  anchors: row4, row18
- **M8.** `config-get.sh` stays read-only. Its header (`:30-37`), usage message (`:42`) and `set` rejection (`:49`) name `config-set.sh` as the write command. The `set` message keeps the phrase "no set subcommand" (row 24).

  anchors: row3, row24
- **M9.** `docs/config-file.md` § "Writing a value" becomes the one home for the setter's usage and behavior, and it lands in Dispatch 1 with the script. Every other site shows one `~/.claude/scripts/config-set.sh <key> <value>` line and keeps its existing link to `docs/config-file.md`. The section states:
  - the command, with VALUE passed bare, and that the exit-code table is in the script's header;
  - that `<config-dir>` resolves from the invoking shell's `CLAUDE_CONFIG_DIR`, as § "Querying a value" describes, so the Stop reason's command acts on the shell's config dir, not the hook's;
  - that a permissive value for another account is written from inside that account's session, because a `CLAUDE_CONFIG_DIR=…`-prefixed command is a spelling no ask rule is shown to match (M10);
  - that the setter names the file it wrote on stderr, as an absolute path that reaches the transcript, so the agent and the engineer see which config dir the command reached;
  - the in-place rewrite, which rewrites every row for the key, keeps comments, blank lines between rows and key order, and leaves the file newline-terminated;
  - that the write replaces the file rather than appending to it, so the new file has `mktemp`'s mode 0600 and a symlinked file becomes a regular file, as § "Per-account isolation" already advises;
  - the refusals, which write nothing: a line outside the grammar, and an existing file the setter cannot read (M13);
  - that exit 127, 126 or 3 from the Stop reason's command means fixing the install, or hand-editing per the hand-edit contract;
  - the notice for the four enforcement-critical keys, which prints whenever one of their permissive values is written, even while another source overrides the row;
  - that the notice is the only per-call record of such a write, because nothing logs setter calls. `docs/session-config-keys-log.md` records the resulting value at the next session start, resume, `/clear` or compaction, in rows that are advisory and unauthenticated (row 48);
  - that the notice's key set is exactly the schema header's four, the keys whose permissive value turns off an enforcement mechanism rather than a nudge, a disclosure or a pilot, so every other key, including those that publish data or whose `true` tightens a round cap, gets neither the notice nor an ask rule;
  - the four ask rules (M10):
    - their prompt is documented, not observed, as `docs/hooks.md:189` states the diff-size ack's;
    - the section links to `docs/security-hardening.md` for the documented behavior rather than restating it (row 33);
    - each rule names one exact spelling of one command;
    - no other spelling of the command is shown to match a rule;
    - any other write path meets no rule;
  - that the setter knowingly does not meet the design record's rule that every enforcement-critical write path be one where impersonating the human buys nothing, on row 26's argument, with a link to the record's note (M14);
  - the three entry points into `_config_set` (`install.sh`'s prompt, `migrate-legacy-config.sh`'s import and `config-set.sh`), of which only the import is direction-aware;
  - in place of `:230-232`'s "no `permissions.ask` rule":
    - the four ask rules name four exact command strings, not the file;
    - no hook gates a write to the file;
    - "the Stop reason's setter command" replaces "the Stop reason's Bash append";
  - the lock note, widened to three entry points, with "human-driven" dropped as its reason:
    - the Stop reason directs agents to run the setter, so two sessions on one config dir can overlap;
    - exit 0 and the read-back do not detect a concurrent lost update;
    - the later `mv` wins, so a restored enforcement key can silently revert to its permissive value;
  - for a hand edit, that an editor stays fine and a one-line change should use `config-set.sh`, not an append, because an append onto an unterminated last line joins two rows that the reader skips;
  - the classification in M10.

  Two other edits land in the same file: `:39-40` says no writer removes an unknown-key row, and `:176-178` says the deferred value is printed as a `config-set.sh` command to run only on the engineer's explicit instruction.

  anchors: root, row15, row18, row33, row42, row43, row44, row48
- **M10.** Classification: `config-set.sh` is a convention, not a gate, because it adds no write an agent's Bash tool could not already make (row 26). Its notice is a record in the transcript, not a control. The plan frames it for a cooperative agent and for every stow consumer. Every stow consumer receives the setter, the ask rules and the new Stop reason on the same `git pull` (row 14). Outcomes:
  - No `# tier-threat-model:` line, because that framework covers `hook-class: gate` hooks only (row 19).
  - Four exact-match entries under `permissions.ask` in `claude/.claude/settings.json`, one `Bash(~/.claude/scripts/config-set.sh <key> false)` per enforcement-critical key, placed after `:45` in the shape `claude/.claude/rules/settings-json-conventions.md` and the entries at `:37-45` show (rows 30-32). Each names the one spelling `~/.claude/scripts/config-set.sh <key> false`. No other spelling is shown to match:
    - a `CLAUDE_CONFIG_DIR=… ` or other env prefix, the form a reader would take from `docs/config-file.md` § "Querying a value" to reach another account;
    - a `bash ` prefix;
    - an absolute or `$HOME` path;
    - a quoted argument;
    - a redirect or pipe after the value.

    Whether Claude Code strips an env prefix before matching is unverified (row 33). An editor or an append meets no rule at all. The plan claims a declared rule with documented behavior, not an observed prompt (row 33). M15 holds every documented permissive command to the exact spelling.
  - No `permissions.allow` entry (row 20).
  - `docs/config-file.md` states the classification (M9), and `docs/hooks.md` needs no change.
  - One `docs/scripts.md` bullet for `config-set.sh`. It names `config-get.sh` as its read counterpart and the four ask entries, and points at `docs/config-file.md` § "Writing a value".

  anchors: row14, row19, row20, row26, row30, row31, row32, row33
- **M11.** `CHANGELOG.md` gets two bullets under `[Unreleased]`. The `### Added` bullet names the script, its four ask rules, the repointed one-liners and Stop reason, and the migrator's hint. Its **Migration** line says a `printf … >>` one-liner copied earlier is correct only on a newline-terminated file, so use the setter. The `### Fixed` bullet says `_config.sh`'s two writers, which `install.sh`'s prompt and the migrator call, no longer replace a state file they cannot read (M13). It also says the migrator's messages for that case no longer suggest deleting the file. It claims nothing of its own about `install.sh`'s handling, which rests on row 42's trace. The `:9-11` entry stays as recorded (row 21).

  anchors: row21, row42
- **M12.** Tests keep one subprocess case per branch and put input matrices in direct `_config.sh` tests (`.claude/rules/bash-unit-test-seams.md`, `claude/.claude/rules/shell-script-conventions.md`). Two CLI cases run once per input, because the property each pins exists only at the CLI: a rejected argument leaves the file byte-identical, and each critical key gets its notice. The isolated-layout helpers private to `test_config_get.py` move to one shared module that the getter and setter tests both import (rows 23, 40). Every new case is written and seen failing before the code it guards (Verification 1 and 4). Critical files lists each case.

  anchors: row16, row22, row23, row25, row39, row40
- **M13.** A new `_config_state_file_unreadable FILE` in `_config.sh` returns 0 only when FILE is a regular file that cannot be opened for reading. It applies `_config_file_lines`'s two gates in that function's order (row 42):
  - `[ -f "$FILE" ]` first, so an absent path, a directory or a FIFO returns 1 without any open;
  - then the same braced, stderr-silenced redirect open, `{ : <"$FILE"; } 2>/dev/null`.

  So the writers refuse exactly the files the reader skips as unreadable. A `[ -r ]` test was set aside: the point is agreement with the reader, which opens the file, and a permission test is a second predicate that would have to stay in step with that open. `_config_set` and `_config_scaffold` each call the helper after their `mkdir -p`, return 3 with nothing written when it holds, and name that status in their headers. Their callers already treat any nonzero status as a failed write (row 42), and the setter maps status 3 to exit 3 (M1 step 6).

  The migrator's two failure messages (`migrate-legacy-config.sh:320, 422`) name an unreadable file beside a line outside the grammar as the possible cause. `:422` drops "or delete it", so neither message advises deleting a file whose rows a `chmod` would recover. One wording per message covers both causes, so neither call site captures the status. Capturing it would mean restructuring the `&&` list at `:304` and the `if !` at `:421` under the migrator's `set -e`.

  Alternatives checked:
  - A check in the setter alone. It would leave `install.sh`'s prompt and the migrator's import and scaffold replacing an unreadable file with one that holds only their own rows, against CLAUDE.md's "Audit structural siblings before scoping a fix narrowly".
  - A change to `_config_file_lines`. Every reader shares it on every hook's path, and its header treats an unreadable file as absent by design (`_config.sh:292-296`, M7).

  anchors: row42
- **M14.** `docs/design-decisions/sentinel-config-consolidation.md` gets one note immediately under its provenance line (`:3`), in the form `.claude/rules/design-decisions.md` "Supersession" gives and the partial notes at `branch-scoped-review-ledger.md:7` and `round-cap-consult-rearm.md:5` use: a bold `Superseded in part by <link to docs/config-file.md § "Writing a value"> (<commit date>):` lead. The note states:
  - that `config-set.sh` writes the permissive value of an enforcement-critical key on request, so line 29's closing rule no longer holds for every enforcement-critical write path;
  - why that is accepted: an agent's Bash tool can already append the same row (row 26), which is an equivalence of capability only. Whether the harness treats the setter call differently from an append is unobserved. The four `permissions.ask` entries on the permissive commands are declared, and their prompt is unobserved (`docs/security-hardening.md`). The notice is a record in the transcript, not a control;
  - that the import's deferred permissive value is now printed as a `config-set.sh` command, not as a line to hand-paste (line 30, M6);
  - that everything else in the record stands.

  The note lands in Dispatch 1, in the same commit as § "Writing a value", which links to it. The note leaves the record's "five" keys and `autonomous_shipping` as they are (Out of scope). A section citation in it follows `.claude/rules/citation-grammar.md`. Lighter primitives checked: leaving the record as it is, which the "Supersession" rule forbids for a decision a later change overturns, and the M9 statement alone, which leaves the record silently contradicting the code.

  anchors: row11, row34, row35, row36
- **M15.** New `claude/.claude/hooks/tests/test_config_set_doc_call_sites.py`, modeled on `claude-skills/skills/tests/test_skills.py:911-936`, lands in Dispatch 2. Its corpus is `README.md`, every `docs/**/*.md` outside `docs/design-decisions/`, and every `claude/.claude/hooks/*.sh`, each of which selects the hooks test tree (row 41). "Tracked doc" in row 40 means `README.md` and `docs/` here.

  A site has this grammar:
  - the literal `~/.claude/scripts/config-set.sh`, one or more spaces, a key word matching `[a-z][a-z0-9_]*`, one or more spaces, and a value word;
  - the value word is the longest run of characters other than whitespace, a backtick, `)` and `"`, with a single-quoted span taken whole, so the bare-line, `! `, inline-code, `Bash(…)` and bash-string forms each end where their markup or quoting ends the word;
  - the test reads the value word with `shlex.split`, and a word that does not read as exactly one shell word is reported.

  Prose that names the script without a key word and a value word is not a site, and neither is a placeholder such as `<key> <value>`. Docs state a rejected value in prose without the script path, so no intentional negative example is a site. The test checks four rules:
  1. Valid: every site's key is a schema key, and its value is one the key's type accepts. One bash subprocess runs a fixed script body that sources `_config.sh` and calls `_config_schema_field` and `_config_type_accepts` for each pair. The doc-derived words reach it only as positional arguments after that body, never inside script text. It is not a Python copy of the type rule.
  2. Ask-matched: a site whose key is in `$_CONFIG_ENFORCEMENT_CRITICAL_KEYS` and whose value is not that key's safe value is a permissive command. Its text from the literal through the value word must equal the command inside one `Bash(…)` entry of `permissions.ask`, which the test reads from `claude/.claude/settings.json`. The literal must start the command: it follows the line's start after indentation, a backtick, `Bash(`, `! `, or `: `, the last being the Stop reason's lead-in. The value word must end the command: it is followed by the line's end, a backtick, `)` or `"`. The same subprocess prints the critical keys and their safe values.
  3. No append: no line holds a `>>` or `tee -a` whose target word ends in `claude-config.toml` once any leading quote or backslash characters are skipped. The detector keys on the redirect target, not on the two tokens sharing a line.
  4. Coverage: each of the seven files row 18 names (`README.md`, the five doc pages and `advance-past-commit-stall.sh`) carries at least one site. This replaces a site-count floor. A floor equal to today's 15 sites fails when a duplicate re-enable line is dropped, and a lower one misses a page whose sites all regressed to prose.

  The controls feed the same scanning functions:
  - Positive, one per embedding form, each recognized and passing rules 1-3 with `commit_stall_block false`: a bare line, a `! ` line, inline code, `Bash(…)`, and the bash-string form ending `false"`.
  - Not sites: `config-set.sh <key> <value>` and a bare mention of the script.
  - Rule 1, each reported: an unknown key, `'"dollars"'` for `pr_cost_disclosure`, and `'$(echo false)'` for `handoff_nudge`. The last is reported only while the word reaches bash as an argument. As script text it would evaluate to `false`, which the type accepts. A `$(false)` control cannot tell the two apart, because its evaluated form, the empty string, is rejected too.
  - Rule 2, each reported for `commit_stall_block false`: a `bash ` prefix, a `CLAUDE_CONFIG_DIR=/x ` prefix, a doubled space, and a `2>/dev/null` suffix.
  - Rule 3: the doc one-liners' `>> "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/claude-config.toml"`, the hook's escaped `>> \"$CONFIG_DIR/claude-config.toml\"`, and a `tee -a` form are reported. A prose line holding a backticked `>>` and `claude-config.toml` (the `docs/security-hardening.md:552` shape), `>> .gitignore` and `>> "$LOG_FILE"` are not.

  The docstring names the gaps:
  - a command split across lines, another path form for the script, a double-quoted value, and an append target held in a variable are not seen;
  - skills, plugins, agents, rules, `claude/.claude/scripts/`, `install.sh` and `CLAUDE.md` files are not scanned (Out of scope, row 49).

  The migrator's hint is outside the corpus because it is a runtime format string with no literal key, and its own test pins it (Critical files). Lighter primitives checked: a one-time `git grep`, which can pass vacuously or fail on prose (row 40), and one pin per doc page, which repeats one rule seven times.

  anchors: row18, row39, row40, row41, row49

**Rows:**
1. `_config_set KEY VALUE` validates VALUE against the key's schema type and refuses to write when any existing line is outside the grammar. It rewrites every matching row in place or appends one, and installs the result through a same-directory `mktemp` and `mv` (`_config.sh:1086-1222`). [verified: read]
2. `_config_set` already rejects an unknown key, because `_config_schema_field … || return 1` fails for a key with no schema row (`_config.sh:1138`, `:503-511`). It returns the same status 1 for an unknown key, a value of the wrong type, a malformed line and a failed write, and status 2 for an unresolvable config dir (`_config.sh:1138-1221`). [verified: reads] This corrects the dispatch's premise that `_config_set` does not check for unknown keys. The setter therefore checks the key and the value itself, to report each cause. `test_config_lib.py:1222-1328` pins those refusals, so `_config_set`'s existing statuses stay as they are. M13 adds status 3 for an unreadable file. [verified: read]
3. `config-get.sh` exits 2 for an unknown key and 3 for an environment failure. It maps `_config_schema_field`'s status 3 to exit 3 and any other nonzero status to exit 2 (`config-get.sh:7-14, 58-71`), and it runs under `set -uo pipefail` with no `-e` (`:2`). `_config.sh` is written for callers that do not set `-e` (`_config.sh:14-17, 1109-1110`). [verified: reads]
4. `_config_file_lines` emits an unterminated last line (`_config.sh:311`), and `_config_set` writes a newline after every line it keeps or adds (`_config.sh:1194-1203`). So the setter reads such a file correctly and leaves it newline-terminated. [verified: read] The `test_advance_past_commit_stall.py:841-866` fixture, `handoff_nudge = false` with no trailing newline, exercises exactly this through the Stop reason.
5. `worktree_required` resolves `config-dir-or-home`, so a row written at the resolved config dir does not decide it alone while `$HOME/.claude` still enables it (`config-keys.psv:28-31, 86`). `install.sh:553-568` reads the key back after its own write for this reason. [verified: reads]
6. All four enforcement-critical keys have `true` as their fail-closed value, so `false` is the permissive value of each (`migrate-legacy-config.sh:52-61`, `config-keys.psv:81-85`). [verified: reads]
7. The reader holds a second copy of the type rule in `_config_read_key_from_file` (`_config.sh:383-401`), whose arms each print their own warning, and `_config.py:212-221` mirrors that copy. [verified: reads]
8. The four-key list sits in two places today: the schema's header comment (`config-keys.psv:81-85`) and `migrate-legacy-config.sh:35`, with the fail-closed values at `:52-61`. `test_migrate_legacy_config.py:790-831` pins the script's list against the schema comment and its safe values against `_ENFORCEMENT_CRITICAL_SAFE_VALUES`. `test_doc_counts.py:427-461` sources the migrator to read the list. No other file names `_MIGRATE_ENFORCEMENT_CRITICAL_KEYS` or `_migrate_enforcement_critical_safe_value`. [verified: Grep]
9. No Python code writes `claude-config.toml`. `_config.py` defines only `schema`, `config_value`, `config_enabled` and their read helpers, and the mentions under `transcript_analysis/` are comments and messages. [verified: Grep]
10. The engineer chose to allow writing the permissive value of the four enforcement-critical keys, with a notice. [engineer-verified: "Allow, with notice (Recommended)"]
11. That option's description was the session's wording: the setter writes any schema key in either direction and prints a distinct stderr notice for the permissive value of a critical key. [unverified] This plan adopts it on three grounds:
    - the setter adds no write an agent lacks today (row 26);
    - today's Stop reason already hands an agent the permissive `commit_stall_block` write;
    - a confirmation step inside the script could not show a human answered (G2).

    The design record gives three facts about permissive writes. [verified: read]
    - Line 27 says the import is direction-aware, because promoting a legacy value into a row makes it authoritative and harder to reverse.
    - Line 29 ends with a rule for every enforcement-critical write path, quoted whole under G2.
    - Line 30 says the import never writes a permissive value and prints it "for a human to hand-paste into `claude-config.toml` instead".

    The setter does not meet line 29's rule for every spelling of its command, so this plan relaxes the rule knowingly and records that in the design record (M14).
12. The engineer chose a setter command as what the Stop reason hands the agent. [engineer-verified: "Setter command (Recommended)"] The description, which keeps the literal prefix `To disable this on this machine: ` and ends with a runnable setter invocation, was the session's wording. [unverified] M5 adopts it because both reason tests split on that prefix (`test_advance_past_commit_stall.py:828, 853`). [verified: read]
13. The Ask. [engineer-verified: "yeah I think a setter is the way to go. and yeah you should do a follow-up."] It covers building a setter as a follow-up change.
14. Settings register the hook at `~/.claude/hooks/advance-past-commit-stall.sh` (`claude/.claude/settings.json:299`). `install.sh` links each entry of `claude/.claude/` one by one into a real `$HOME/.claude/` (`README.md:94`), so `~/.claude/scripts/` is linked whenever that hook runs. A new file under it is live on `git pull` (`README.md:98`). `docs/worktree-bash-guard.md:100-110` documents the literal `~/.claude/scripts/<name>` call as the repo's form for agent-run scripts and says it names the same file under every config dir. [verified: reads]
15. The setter resolves `<config-dir>` from its own environment, through `_lib_config_dir` inside `_config_set` and `_config_value` (`_config.sh:155, 1164`), as `config-get.sh` does (`docs/config-file.md:262-264`). [verified: reads] Today's Stop reason instead embeds the hook's resolved path (`advance-past-commit-stall.sh:62, 254`). The agent's Bash tool and the Stop hook resolve the same config dir only if both inherit the session's `CLAUDE_CONFIG_DIR` and `HOME`. [unverified] Every `${CLAUDE_CONFIG_DIR:-$HOME/.claude}` doc one-liner already rests on the same premise, and `docs/worktree-bash-guard.md:96-99` prefers a script that reads the variable from its own environment.
16. The two Stop-reason tests run the command through `bash -c` with no `env` argument (`test_advance_past_commit_stall.py:830, 855`), so the subprocess inherits the test process's environment. There `isolated_home` has set `HOME` through `monkeypatch.setenv` and removed `CLAUDE_CONFIG_DIR` (`claude/.claude/hooks/tests/conftest.py:493-502`), so bash expands `~` to `<isolated_home>`. That fixture links only `_lib.sh`, `_config.sh` and `config-keys.psv` into `<home>/.claude/hooks/`. [verified: reads] The fixture creates no `<home>/.claude/scripts/`. [verified: the sdet reviewer's read, not re-read] So each test creates that directory and links `config-set.sh` into it, and the setter then sources the linked `_config.sh` through its own `dirname "$0"`.
17. `migrate-legacy-config.sh:296-298` prints a deferred permissive value as a line to add by hand, and its import never writes that value (`:282-302`). `test_migrate_legacy_config.py:875-877` asserts the printed `key = value` text, and `:1003` asserts the hand-add sentence is absent in another case. [verified: reads]
18. The append and its writers appear in three groups of sites, and no test pins a README or docs one-liner. [verified: Grep]
    - Fifteen executable `printf … >> …/claude-config.toml` one-liners outside `CHANGELOG.md`: `README.md:347, 384, 430`; `docs/commit-stall-block.md:36, 42`; `docs/error-mode-nudge.md:12, 18`; `docs/handoff-nudge.md:36, 108, 114`; `docs/memory-audit-nudge.md:113, 119`; `docs/permission-prompt-tracking.md:6, 28`; and `advance-past-commit-stall.sh:254`.
    - Prose about the append or the writers: `docs/config-file.md:176-178, 214-251` and `docs/security-hardening.md:552`.
    - The old writers named in `config-get.sh:30-37, 42, 49`.
19. The threat-model tier framework covers `hook-class: gate` hooks only (`docs/hooks.md:7`). [verified: read] No non-hook script carries a `# tier-threat-model:` line. [verified: the dispatch's exploration, not re-read]
20. `config-get.sh` has no `permissions.allow` entry (`claude/.claude/settings.json:3-34`) and no `docs/scripts.md` bullet. [verified: read, Grep] The design record relies on Claude Code's ask-by-default prompt for writes to this file (`sentinel-config-consolidation.md:25`). [verified: read] The four ask rules cover only the permissive commands (M10). An allow entry for the setter would pre-approve, for every stow consumer, every setter command no ask rule names, so M10 adds none.
21. `CHANGELOG.md`'s `[Unreleased]` holds `### Added` at `:707` and `### Fixed` at `:897`, and its `:9-11` entry records the previous change. `.claude/rules/changelog-entries.md` treats entries as records. [verified: reads]
22. `test_bash_floor.py:474-482` lists each script that stops on a failed `_config.sh` source, with `config-get.sh` expecting exit 3. [verified: read]
23. `test_config_get.py:21-54` isolates a script by linking it into a `scripts/` directory beside a `hooks/` directory that holds `_config.sh` and a schema copy, and runs it with only `HOME`, `PATH` and an optional `CLAUDE_CONFIG_DIR`. [verified: read]
24. `test_config_py.py:553-557` requires `config-get.sh set` to print "no set subcommand" or "no writing verb". [verified: read]
25. Which tests `select-tests.py` selects for this diff. [unverified until run] The diff touches `claude/.claude/hooks/`, `claude/.claude/scripts/`, `claude/.claude/settings.json`, `docs/`, `README.md` and `CHANGELOG.md`.
26. At the merge base, no hook and no `permissions.ask` rule in this repo gates an agent's Bash write to `claude-config.toml` (`docs/config-file.md:230-233`). [verified: read] An agent's Bash tool can therefore already append any row the setter writes, which is an equivalence of capability. Whether Claude Code's own prompt treats an append and the setter call alike is unobserved. [unverified] This plan adds no write-gate hook: one was descoped after review did not converge (`docs/design-decisions/sentinel-config-consolidation.md:25`), and it is listed under Out of scope.
27. M2, M3 and M6 stay in this plan, though the Ask does not call for them by name. [engineer-verified: "Keep all three (Recommended)"]
28. This plan ships as one PR of two sequential commits, at a `Projected diff:` of about 670 changed lines. [engineer-verified: "Proceed anyway"]
29. The engineer confirmed that they said the Ask line's quoted words this session. [engineer-verified: "Yes, I said that"]
30. The engineer chose to add ask rules for the permissive writes. [engineer-verified: "Add four ask rules (Recommended)"]
31. The session's reading of that label: four exact-match `Bash(~/.claude/scripts/config-set.sh <key> false)` entries under `permissions.ask` in `claude/.claude/settings.json`, one per enforcement-critical key, plus a test for them. It replaces row 20's reasoning about `permissions.allow`, and the no-allow-entry decision stands. [unverified]
32. Facts about the ask-rule edit. [verified: reads]
    - `claude/.claude/settings.json:37-45` holds nine exact-match Bash ask entries, and `claude/.claude/rules/settings-json-conventions.md` bans globs in `permissions.allow` only.
    - `test_hook_alignment.py:583-609` and `claude-skills/skills/tests/test_skills.py:896-908` pin a declared ask entry and the absence of a matching allow entry, as declared state, not runtime behavior.
    - `review-permissions` triggers on `permissions.allow`, bare `permissions.deny` and `permissions.defaultMode` changes (`claude-skills/skills/review-permissions/SKILL.md:3-8`), and `code-review/SKILL.md:217` invokes it only for allow rules. An ask-only edit is outside its trigger.
    - An Edit of that settings file prompts the engineer through `ask-review-permissions.sh` and the `Edit(//**/.claude/settings*.json)` ask entry (`settings.json:46`).
    - `claude/.claude/scripts/cursor-adapter/parity-exceptions.json` has no kind for an ask entry and lists none of the nine existing ones. The adapter's run-mode precondition has every Shell call prompt (`docs/cursor-adapter.md:119`), so the four entries need no adapter change.
33. Facts from `docs/security-hardening.md`. [verified: read]
    - `:254-258` records three behaviors from Anthropic's documentation: an explicit ask rule prompts in every mode that can prompt, `bypassPermissions` included; auto mode still shows that prompt; and `dontAsk` denies it.
    - The observations at `:240-252` cover an Edit rule only.
    - `:261-271` lists `bypassPermissions` for that rule, Bash-mediated writes and headless `-p` runs as untested.

    Whether these four Bash ask rules prompt in any mode is unknown. Which other spellings of the command they match is unknown, including whether Claude Code strips an env prefix such as `CLAUDE_CONFIG_DIR=… ` before matching. [unverified]
34. The engineer chose to record the setter in the design record. [engineer-verified: "Add supersession note (Recommended)"]
35. The session's reading of that label: one in-place supersession note in `docs/design-decisions/sentinel-config-consolidation.md`, per `.claude/rules/design-decisions.md`, stating that the setter knowingly relaxes line 29's rule on row 26's argument. That file leaves Out of scope's preserved-records entry. [unverified] This plan also has the note cover line 30's hand-paste clause, which M6 changes.
36. `.claude/rules/design-decisions.md` "Supersession" has a decision that a later change overturns edited in place, immediately under its own provenance line. Partial notes that point at a doc other than a decision record exist at `docs/design-decisions/branch-scoped-review-ledger.md:7` and `docs/design-decisions/round-cap-consult-rearm.md:5`. [verified: reads]
37. The engineer chose to qualify the commands the Stop reason and the migrator print. [engineer-verified: "Add the qualifier (Recommended)"]
38. The session's reading of that label: the Stop reason and the migrator hint each say the command is run only on the engineer's explicit instruction. In the reason, the qualifier sits before the unchanged `To disable this on this machine: ` prefix, and a test pins the wording. [unverified] `docs/hooks.md:660` frames another last-resort config step as "the human's to run or direct, not the session's to take unasked". [verified: Grep]
39. The engineer chose both a shared test helper and a drift test. [engineer-verified: "Add both (Recommended)"]
40. The session's reading of that label: [unverified]
    - a shared helper module under `claude/.claude/scripts/tests/`, holding the isolated-layout helpers private to `test_config_get.py`, parameterized by script name and imported relatively by both test files;
    - a permanent drift test modeled on `test_skills.py:911-936`, checking every `config-set.sh <key> <value>` site with a floor of 15, checking that no tracked doc or hook text appends to `claude-config.toml`, and carrying a seeded-violation control per rule shape;
    - the drift test replacing Verification 4's one-time grep, which the sdet reviewer found can pass vacuously or fail on prose;
    - a `Projected diff:` stated honestly past row 28's figure.

    M15 replaces the floor of 15 with a per-file coverage rule, because a floor equal to the real site count fails when one duplicate site is dropped. `test_config_get.py:21-54` holds the helpers, and `_isolated_scripts_dir` links `config-get.sh` by name. `claude/.claude/scripts/tests/` is a package with `_*_helpers.py` modules such as `_routing_guard_helpers.py`, and `.claude/rules/test-tree-packaging.md` requires relative sibling imports there. [verified: reads]
41. `select-tests.py` maps `docs/` and `README.md` to the hooks and skills test trees (`:1051-1052`), `claude/.claude/hooks/` to the hooks test tree (`:742`), and `claude/.claude/settings.json` to the hooks, skills and scripts trees (`:1056`). It maps `claude/.claude/scripts/` to the scripts test tree (`:743`), and a shell script there also to the hooks and skills trees (`_is_scripts_dir_shell_script_change`, `:636-638, 1015`). `TestCrossDomainReadCompleteness` (`test_select_tests.py:372-402`) fails a test whose module-level path constant names a file whose change would not select that test. [verified: reads] So M15's test lives in the hooks test tree. A migrator change selects that tree too, so the migrator stays out of M15's corpus only because its hint is a runtime format string (M15).
42. `_config_file_lines` emits nothing for a file it cannot read (`_config.sh:292-308`). It treats a path that is not a regular file as absent (`[ -f ]`, `:299`), and decides readability by opening the file in a braced, stderr-silenced `$(<file)` read (`:308`). `_config_set` (`:1172-1176`) and `_config_scaffold` (`:1263-1267`) both build the new file from those lines, so each replaces an existing unreadable file with one holding only the rows it adds. [verified: read] The platform reviewer's scratch run reproduced this for `_config_set`. Their callers treat any nonzero status as a failed write (`install.sh:544, 582-585`; `migrate-legacy-config.sh:304, 319-321, 421-424`). [verified: reads] The migrator's messages for those failures name only malformed content, and the scaffold's message suggests deleting the file (`migrate-legacy-config.sh:320, 422`). [verified: read]
43. `_config_set` installs the new file with `mktemp` and `mv` (`_config.sh:1206-1216`), so a symlinked state file is replaced by a regular file. [verified: read] The installed file's mode is `mktemp`'s 0600. [unverified] The absent-file setter case asserts that mode before M9 states it. `docs/config-file.md:278-279` already tells readers to create each account's file as its own regular file. [verified: read]
44. `_config_set`'s header (`_config.sh:1127-1134`) and `docs/config-file.md:235-241` accept the lost-update race because both callers are "human-driven, low-concurrency, typically-singleton local processes", and the Stop reason directs an agent to run the setter. `_config.sh` stays free of `_lib.sh` so `install.sh` can source it alone (`_config.sh:10-12`). [verified: reads]
45. This plan still ships as one PR of two sequential commits at the revised `Projected diff:` of about 1,200 changed lines, replacing row 28's figure. [engineer-verified: "Proceed anyway"]
46. M13 stays in the shared writers, so `_config_set` and `_config_scaffold` both refuse an unreadable state file. [engineer-verified: "Keep in the shared writers (Recommended)"]
47. The Stop hook blocks at most once per `prompt_id` in a session, by comparing the prompt id it last fired on (`advance-past-commit-stall.sh:139-142, 248-250`). So a fire under a new prompt id blocks again unless the key disables the hook. The hook stays silent when its config dir is not a directory (`:62-63`). [verified: read]
48. `record-session-config-keys.sh` adds a row to `<config-dir>/.session-config-keys-log.jsonl` at each startup, resume, `/clear` and compaction, and each row maps every schema key to its value (`docs/session-config-keys-log.md:3, 15`). Its rows are advisory and unauthenticated (`:17`). [verified: read]
49. A `claude-skills/skills/**/SKILL.md` change selects the skills test tree and, of the hooks test tree, only `test_doc_counts.py` (`select-tests.py:745, 1023`). Plugin skills select the skills tree only (`:1012`). So a hooks-tree test that reads skill files needs a `select-tests.py` rule change to stay selected. [verified: read]

## Critical files

Two `code-writer` dispatches run in sequence, one commit each, with `/code-review` before each commit. Dispatch 2 copies the command, the qualifier and the notice text from Dispatch 1's script, so it runs second. Paths are repo-relative, and line numbers are merge-base lines.

**Before Dispatch 1:** the session commits `.claude/plans/config-setter.md` (plan-it Step 7).

**Dispatch 1, commit 1: the script, the `_config.sh` changes, the ask rules, the repointed hook and migrator, `docs/config-file.md`, the design-record note, and their tests.** Verify with Verification steps 1-3. Tell this commit's `/code-review` that the one-liner swaps, the remaining docs and the drift test land in commit 2.
- New `claude/.claude/scripts/config-set.sh`, mode 755 (M1, M3).
- `claude/.claude/hooks/_config.sh`:
  - add `_config_type_accepts` beside `:1067-1084`, and call it from `_config_set` in place of `:1139-1153` (M2);
  - add `_CONFIG_ENFORCEMENT_CRITICAL_KEYS` and `_config_enforcement_critical_safe_value` (M3);
  - add `_config_state_file_unreadable` with M13's two gates, and return 3 from `_config_set` and `_config_scaffold` when it holds, naming that status in each header (M13);
  - name `config-set.sh` among the consumers in the header (`:2-6`) and among `_config_set`'s callers (`:1122-1125`);
  - in the lock note (`:1127-1134`), name three entry points, drop "human-driven" as the reason, and say that exit 0 and the read-back do not detect a concurrent lost update, which can silently revert an enforcement key to its permissive value.
- `claude/.claude/settings.json`: the four ask entries after `:45` (M10). This edit adds `permissions.ask` entries only, which fall outside `review-permissions`' trigger. The Edit prompts the engineer (row 32), and the dispatch prompt names that prompt as expected. If the Edit is denied inside the `code-writer` dispatch, it returns the denial verbatim with no retry through another tool, and the session makes the four-line edit before `/code-review`.
- `claude/.claude/scripts/config-get.sh:30-37, 42, 49` (M8).
- `claude/.claude/scripts/migrate-legacy-config.sh`: delete `:30-61`, call the moved names at `:283-293`, read `_CONFIG_SAFE_VALUE` at `:293`, reword the comment at `:290-291`, print the qualified setter command at `:296-298`, and reword the messages at `:320` and `:422` (M3, M6, M13).
- `claude/.claude/hooks/advance-past-commit-stall.sh:254` (M5).
- `docs/config-file.md:39-40, 176-178, 214-251` (M9, M10).
- `docs/design-decisions/sentinel-config-consolidation.md`: one note under `:3` (M14).
- New `claude/.claude/scripts/tests/_config_script_helpers.py`, holding `test_config_get.py:21-54`'s `_isolated_scripts_dir`, `_path_with_caller_bash_first` and `_run` as public helpers parameterized by script name and argument list (rows 23, 40). `_run` also takes an optional extra-environment mapping, so the failing-`mktemp` case can put its shim directory first on `PATH` without a private `subprocess.run`.
- `claude/.claude/scripts/tests/test_config_get.py`: delete `:21-54`, import those helpers with `from ._config_script_helpers import …`, and update their call sites.
- New `claude/.claude/scripts/tests/test_config_set.py`, built on the shared helpers. Every nonzero-exit case asserts `stdout == ""`. Its cases:
  - exit 0: an absent file is created holding exactly `commit_stall_block = false\n` at mode 0600, stdout is `false\n`, and stderr names the file;
  - exit 0: an existing row is rewritten in place, and the file's exact bytes keep a comment, a blank line and key order, with no second row;
  - exit 0: the old one-liner's output applied twice, `handoff_nudge = false\n\ncommit_stall_block = false\n\ncommit_stall_block = true\n`, becomes exactly `handoff_nudge = false\n\ncommit_stall_block = false\n\ncommit_stall_block = false\n`;
  - exit 0: `handoff_nudge = false` with an unterminated last line becomes exactly `b"handoff_nudge = false\ncommit_stall_block = false\n"`;
  - exit 0: a state file that is a symlink to a file elsewhere leaves that target byte-identical, and the state file becomes a regular file holding the row;
  - exit 0: `pr_cost_disclosure dollars` writes `pr_cost_disclosure = "dollars"`;
  - exit 2: a wrong argument count, an unknown key, and the quoted value `'"dollars"'`;
  - exit 2, once per input, with the file byte-identical: the keys `'handoff_nudge '`, `'handoff_*'` and `'-handoff_nudge'`, and the values `$'true\nworktree_required = false'`, `' true'` and `'*'`;
  - exit 1: a file holding `handoff_nudge = falsecommit_stall_block = false` stays byte-identical, and stderr carries `skipping malformed line`;
  - exit 1: a failing `mktemp` shim, built as `test_config_lib.py:1304-1328` builds one, leaves the file byte-identical, and stderr carries no `skipping malformed line`;
  - exit 1: `worktree_required false`, with `CLAUDE_CONFIG_DIR` set to a second directory and `<HOME>/.claude/worktree-required` present, writes the row there, still resolves `true`, names "Resolution precedence", and prints the notice;
  - exit 3: a relative `CLAUDE_CONFIG_DIR`, the truncated `worktree_required` schema row `test_config_get.py:75-76` builds, and a missing schema file, built as `test_config_py.py:515-541` builds one, so the case holds under root;
  - exit 3: an existing state file at mode 000 stays byte-identical and is named on stderr, skipped under root;
  - once per enforcement-critical key and direction: exit 0 and stdout equal to the resolved value alone. For `false`, stderr carries the notice with its restore command, and for `true` it carries none. `handoff_nudge false` prints no notice.
- `claude/.claude/hooks/tests/test_config_lib.py`:
  - a `_config_type_accepts` matrix with each argument passed through `shlex.quote`. `bool` accepts `true` and `false` and rejects `notabool`, `TRUE`, the empty string, `' true'`, `'true '`, `$'true\nfalse'`, `'t*'`, `'true=1'` and `'true#'`. `enum:dollars` accepts `false` and `dollars` and rejects `true`, `euros` and `"dollars"`. An unknown type rejects every value. An accepted case returns exactly 0, and a rejected case returns exactly 1 with empty stderr;
  - `TestEnforcementCriticalKeySet` and `TestEnforcementCriticalSafeValues`, moved from `test_migrate_legacy_config.py:800-831` and sourcing `_config.sh` directly, with their own four-entry safe-value dict (DAMP test code);
  - one case that the function returns 0 for every key in `$_CONFIG_ENFORCEMENT_CRITICAL_KEYS`, and one where a non-critical key returns 1;
  - the ask rules, each docstring saying the test proves declared state, not a runtime prompt, as `test_hook_alignment.py:583-609` does:
    - for each key in `$_CONFIG_ENFORCEMENT_CRITICAL_KEYS`, `Bash(~/.claude/scripts/config-set.sh <key> <permissive value>)` is in `permissions.ask`, where the permissive value is the boolean opposite of the key's safe value;
    - the `config-set.sh` ask entries are exactly those;
    - no `permissions.allow` entry in `claude/.claude/settings.json` or `.claude/settings.json` names `config-set.sh`;
  - `_config_state_file_unreadable` returns exactly 1 for an absent path, a directory, a FIFO, an empty file and a mode-644 file, and exactly 0 for a mode-000 regular file, skipped under root. The subprocess runs with a timeout, so an open made before the `[ -f ]` gate fails the FIFO case instead of hanging it;
  - `_config_set` and `_config_scaffold` each return exactly 3 on an existing state file at mode 000 and leave it byte-identical, skipped under root.
- `claude/.claude/hooks/tests/test_advance_past_commit_stall.py:814-866`:
  - create `<isolated_home>/.claude/scripts/` and link `config-set.sh` into it before running the command (row 16);
  - in both tests, assert the split tail equals `~/.claude/scripts/config-set.sh commit_stall_block false`, that `Bash(<tail>)` is an entry of `permissions.ask` in `claude/.claude/settings.json`, that the qualifier sentence directly precedes the prefix, and that the reason contains no `>>`;
  - in the first test, assert the whole file reads `commit_stall_block = false\n`, so the row was rewritten in place;
  - in the second test, assert the whole file equals `handoff_nudge = false\ncommit_stall_block = false\n`, and name the cause in the test name and docstring as an unterminated last line;
  - a third test creates two absolute directories A and B, neither `<isolated_home>/.claude`, because the hook stays silent for a missing config dir (row 47). It fires the hook with `CLAUDE_CONFIG_DIR` set to A (`_fire`'s `extra_env`), then runs the command with `CLAUDE_CONFIG_DIR` set to B. B's file then holds the row, the command's stderr names B's file, and neither A nor `<isolated_home>/.claude` holds a `claude-config.toml`. A second fire under A, with prompt `p2`, still blocks. The test then runs the command under A, and a third fire under A, with prompt `p3`, is silent.
- `claude/.claude/hooks/tests/test_bash_floor.py:474-482`: add `config-set.sh`, expecting exit 3 (row 22).
- `claude/.claude/scripts/tests/test_migrate_legacy_config.py`:
  - remove `_migrate_enforcement_critical_keys_from_script` and the two moved classes (`:790-831`);
  - point the comment at `:45-50` at `_config.sh`'s `_config_enforcement_critical_safe_value`;
  - in `:843-877`, reword the class docstring, and assert stderr carries the qualifier and `~/.claude/scripts/config-set.sh <key> <value>`, and that `Bash(<that command>)` is an entry of `permissions.ask` in `claude/.claude/settings.json`;
  - point `:1003`'s negative assertion at the new hint text;
  - one case, skipped under root as `:892-896` skips: a mode-000 `claude-config.toml` holding one row, plus `handoff_nudge`'s legacy file `.handoff-nudge-disabled`, so the import reaches `_config_set` (`:304`) and then `_config_scaffold` (`:421`). The run exits 1, and the state file is byte-identical once its mode is restored. Stderr carries both messages' unreadable wording and no "delete". The legacy file still exists.
- `claude/.claude/hooks/tests/test_doc_counts.py:427-461`: source `claude/.claude/hooks/_config.sh` and read `$_CONFIG_ENFORCEMENT_CRITICAL_KEYS`.

**Dispatch 2, commit 2: the drift test, the one-liner swaps, the remaining docs and the changelog.** Verify with Verification step 4.
- New `claude/.claude/hooks/tests/test_config_set_doc_call_sites.py` (M15), written first.
- `README.md:347, 384, 430`.
- `docs/commit-stall-block.md`:
  - `:36, 42`, keeping the `! ` shell-escape prefix;
  - `:24`, where "It ends with the disable command" becomes the qualifier and the setter command. The sentence says the command acts on the config dir the agent's own shell resolves, which can differ from the hook's. It says the command runs from `~/.claude/scripts/`, which every install that registers the hook links (row 14). It links to `docs/config-file.md` § "Writing a value".
- `docs/error-mode-nudge.md:12, 18`.
- `docs/handoff-nudge.md:36, 108, 114`.
- `docs/memory-audit-nudge.md:113, 119`.
- `docs/permission-prompt-tracking.md:6, 28`.
- `docs/security-hardening.md:552`: the reason prints a `config-set.sh` command, to run only on the engineer's explicit instruction, that an ask rule names, not a Bash append. The bullet names the design-record exception and links to `docs/config-file.md` § "Writing a value" for it (M14).
- `docs/scripts.md`: one bullet (M10).
- `CHANGELOG.md`: two bullets (M11).

The pointer sentence next to each command, "see `docs/config-file.md` for the file's hand-edit contract", stays as it is.

**Reuse:**
- `_config_set` for the write, and `_config_value` for the read-back and the malformed-line warning.
- `_config_schema_field` for the type and `human-name`, and `_lib_config_dir` for the config dir.
- `config-get.sh`'s messages for exits 2 and 3.
- `test_config_get.py`'s isolated layout, moved into `_config_script_helpers.py`, and the `isolated_home` fixture's `symlink_hooks_lib_chain`.
- `test_config_lib.py:1304-1328`'s `mktemp` shim, `test_hook_alignment.py:583-609`'s declared-ask-rule tests, and `test_skills.py:911-936`'s call-site test.

Projected diff: ~1,330 lines across 26 files (about 960 in tests, 245 in shell scripts and `settings.json`, 125 in docs and the changelog). Row 28's figure was about 670 lines across 21 files, and row 45 records the engineer's acceptance of about 1,200. The rise since then comes from M15's site grammar, ask-match and coverage rules and their controls, the divergent-dir and migrator unreadable-file cases, M13's predicate cases, and the two migrator messages.

Split into two stacked PRs, on the engineer's selected label "Two stacked PRs (Recommended)" after an architect consult on trimming and splitting.
- PR 1: Dispatch 1 plus `docs/security-hardening.md:552`, `docs/commit-stall-block.md:24`, the `docs/scripts.md` bullet and its two `CHANGELOG.md` bullets, 2,549 changed lines.
- PR 2: branches from PR 1 with `gh-merge-base` set. It holds M15's drift test, the 14 doc one-liner swaps and its own changelog bullet, about 300 lines.

The PR 1 figure is the staged diff against the merge base `0fdfb29b` (2,261 insertions, 288 deletions, per `git diff --cached --numstat`). 1,596 of those lines are in test files. The code-review rounds widened M13's refusal and the per-cause messages (see "Divergences as built"), which accounts for the rise over the earlier projection. Until PR 2 merges, the 14 swapped-later one-liners still append, and each keeps its leading `\n`, so it stays valid.

## Divergences as built

The code-review rounds changed these plan statements. The code is authoritative.
- M13: the state-path predicate is positive. The writers proceed only for an absent path or a readable regular file, and return 3 for anything else, a directory, a FIFO and a dangling symlink included. M13's text and Critical files line for the predicate's return values describe the earlier negative shape.
- M1 step 3: schema status 4 splits into a truncated-row message and an unknown-key message.
- M1 step 8: the read-back mismatch message names a cause per key class.
- M5: the qualifier is a shared constant in `_config.sh` of several clauses, not one sentence.
- M5: the Stop reason prints `To disable this for the config dir <dir> (...): ` before the command, where M5 and row 12 keep `To disable this on this machine: `. The reason names the hook's config dir because the command resolves its own.
- M8: `config-get.sh`'s usage message and its `set` rejection point at `docs/config-file.md` and omit the script name by design (`TestWritePointerNamesTheDocNotTheCommand`), where M8 has them name `config-set.sh`.
- Both writers remove their temp file and return 1 when `mv` fails. The plan earlier left that temp-file leak out of scope.

## Verification

1. Test-first, in Dispatch 1:
   - Move the helpers into `_config_script_helpers.py`, repoint `test_config_get.py`, and confirm `scripts/venv-run.sh pytest claude/.claude/scripts/tests/test_config_get.py` still passes.
   - Write every other Dispatch 1 test change before any code or settings change. Run `scripts/venv-run.sh pytest` on `test_config_set.py`, `test_config_lib.py`, `test_advance_past_commit_stall.py`, `test_migrate_legacy_config.py`, `test_doc_counts.py` and `test_bash_floor.py`.
   - Confirm each new or changed case fails for its expected cause: the script, the moved and new functions, status 3, the ask entries, the new reason and hint text, or the reworded migrator messages are absent. All pass after the code and settings changes.
2. `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py` passes after each dispatch. After Dispatch 1, its selection includes every test file Dispatch 1 adds or changes, plus `test_config_py.py`, `test_design_decision_files.py` for M14's note, and `claude-skills/skills/tests/test_handoff_and_resume_skills.py`, which checks the new script's executable bit. After Dispatch 2, it includes `test_config_set_doc_call_sites.py`. A missing file is a bug in its rule table to report, not a reason to widen the run by hand (`CLAUDE.md` § "Commands").
3. After `git add claude/.claude/scripts/config-set.sh`, `scripts/venv-run.sh ruff check claude/.claude/` and `scripts/list-shell-files.sh | xargs -0 scripts/venv-run.sh shellcheck` pass, and `git ls-files -s claude/.claude/scripts/config-set.sh` shows mode `100755`.
4. Test-first, in Dispatch 2: write `test_config_set_doc_call_sites.py` and run `scripts/venv-run.sh pytest claude/.claude/hooks/tests/test_config_set_doc_call_sites.py`. Confirm the controls pass, while the no-append rule reports exactly the 14 doc one-liners and the coverage rule reports `README.md` and the five doc pages, since the hook's site landed in commit 1. It passes after the swaps. Then repeat step 2.
5. The four ask rules' prompt is unobserved (G1, row 33). The PR description says so, unless the engineer observes one prompt first and says so there.

## Out of scope

- The legacy `touch` snippets in `README.md:396, 406, 418`. They write legacy sentinel files, not `claude-config.toml`, so an unterminated last line cannot reach them. Steering those keys to the setter is a separate docs-consistency change.
- Prose that names a key's value without a command, such as `docs/hooks.md:244, 664`, `README.md:374`, `transcript_analysis/cost_ledger.py:722` and `transcript_analysis/pr_cost.py:1232`. Each already defers to `docs/config-file.md`.
- The reader's copy of the type rule (row 7) and `_config.py`'s mirror of it. That code is on the path every hook takes, each arm prints its own warning, and `test_config_parser_parity.py` pins the two readers together.
- A schema column marking enforcement-critical keys (M3).
- A write-gate hook. It was descoped (row 26).
- A lock across the three entry points. `_config.sh` stays free of `_lib.sh`, so `_lib.sh`'s locking helpers are out of its reach (row 44). A new lock primitive is a heavier coordination mechanism than a race M9 now documents with its silent-revert direction.
- A log of setter calls. The notice is the only per-call record, and M9 says so. The session config-keys log already records the resulting value at each session event (row 48).
- Widening M15's corpus to skills, plugins, agents, rules, `claude/.claude/scripts/`, `install.sh` and `CLAUDE.md` files. A skill or plugin-skill change does not select the hooks test tree (row 49), so reading them needs a `select-tests.py` rule change, a mechanism past the drift test the engineer selected. A read-only grep of those trees for a `>>` or `tee -a` that targets a `claude-config` path finds none today.
- A `docs/hooks.md` edit for the Stop reason's command. Its entry (`:244`) names no command and defers to `docs/commit-stall-block.md`, whose `:24` states the config-dir difference and the script's location (Critical files).
- An `install.sh`-level unreadable-file case. It would add `test_install_sh_machine_level_opt_ins.py` to the file list. `install.sh`'s prompt reaches `_config_set` only through an `if` (row 42), and M11's `### Fixed` bullet claims the writers' behavior, which the direct cases and the migrator case pin, not an `install.sh` test.
- Writer byte shapes the review traced but no case pins: dropped trailing blank lines, a leading blank line added to an empty file, a CRLF row's `\r` kept on untouched rows, and a stripped BOM. M9 claims only "blank lines between rows".
- A Python setter (row 9).
- A `~/.local/bin` wrapper. `config-get.sh` has none, and `install.sh:480` installs only `relocate-claude-config`.
- The design record's "five" keys and `autonomous_shipping`, which disagree with the schema's four. Correcting them belongs to a note for the change that made autonomous shipping unconditional (`docs/design-decisions/autonomous-shipping-state-in-hook-context.md:5`), not to M14's note.
- `CHANGELOG.md:9-11`, a preserved record (CLAUDE.md Scope discipline, Axis 3; `.claude/rules/changelog-entries.md`).
- A `permissions.allow` entry for the setter (row 20).
- A `docs/scripts.md` bullet of its own for `config-get.sh`. The `config-set.sh` bullet names it.
