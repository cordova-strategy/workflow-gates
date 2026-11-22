# Mine transcripts for corrections of the main agent

## Context

Add a `transcript-analysis` command that extracts the exchanges where the engineer may have corrected the main agent or could not answer its question, as structured records a model can classify.

Ask: "Agents tend to use internal jargon that I don't understand, or ask me a highly specific question where I don't have context to weigh in, and I often get around this with repeated corrections." "coming up with a plugin that mines transcripts for instances where human has corrected the agent, get patterns, and perhaps propose changes" "do it as an extension of" `transcript-analysis` "semantic analysis of models to really get a good set of results" "you can keep your analysis to just workflow-gates and claude-config (pre-rename)"

**Problem.** The main agent's questions and summaries often assume vocabulary and context the engineer does not have. The engineer repairs each one by hand, and nothing records which shapes recur. The existing `struggle` and `user-input` commands detect corrections by a fixed phrase list, which misses a reply such as "what does that mean?" and never looks at an `AskUserQuestion` exchange.

**Why now.** A second change will revise how the main agent phrases questions to the engineer. That change needs evidence of which shapes actually fail, and this command supplies it.

**Intended outcome.** One command extracts candidate exchanges from main-session transcripts as structured records, written to a local file outside the repository. The same command runs unchanged on another machine once this change has merged, so the engineer can extract from the transcripts held there.

Two changes follow this one, each with its own plan. The first is a skill that hands the records to a model, which classifies each one and groups the results into patterns. The engineer chose this order with the label "Extractor first (Recommended)". The second is the revision to how the main agent phrases questions.

## Approach

Add a `correction-candidates` subcommand to `transcript-analysis.py`. It writes every main-session `AskUserQuestion` exchange and every typed prompt, the words typed after a slash command included, each with the agent text around it, as JSON Lines to one owner-only file the caller names with `--out`. A `--preview` run first lists the project families a scope matches and writes nothing. This plan delivers the extractor alone (row 50), and the engineer runs it on each machine per the runbook below.

### Subcommand: `correction-candidates`

**Placement.** A new module, `claude/.claude/scripts/transcript_analysis/correction_candidates.py`, holds `cmd_correction_candidates`, its helpers, and `_add_correction_candidates_subparser`. `cli.py` imports the registrar and calls it right after `_add_judgment_pair_subparser(sub)`. The module imports `corpus`, `ledger_common`, `pricing`, `redaction`, `render`, `review_rounds`, `scope`, `skill_invocation` and `user_input` by module, and otherwise the standard library only.

**Pure seam.** `cmd_correction_candidates` resolves scope, loops sessions, publishes, and prints. Everything else is a function of in-memory records, so tests drive it without files:
- `_prompt_verdict(rec, origin_seen)` returns a skip kind, or `typed`.
- `_slash_command_args(text)` returns a slash prompt's command name and its args text, or `None`.
- `_session_candidates(records, session_id, family, *, truncate_chars, since_ts, until_epoch)` returns one file's candidates and counts.
- `_answer_is_free_text(answer, labels, multi_select)` returns a bool or `None`.
- `_dedup_and_order(candidates)` returns the kept candidates in output order and the duplicate counts.
- `_counts_and_checks(kept, scan_counts)` returns the scope record's `counts` and `checks` from the kept candidates and the scan's skip counts, the duplicate counts included.
- `_failed_relations(counts, checks)` returns the sorted names of the failing relations under "Reading the counts".
- `_scope_record(..., generated_at)` takes the generation time as an argument, so a test fixes it.
- `_jsonl_text(records)` returns the file's text.

**Flags.**
- `--projects GLOB` / `--this-repo`, through `scope._add_project_scope_args`. Sessions come from `scope.resolve_scan_roots(args)` and `scope._resolve_project_scope(args, "correction-candidates", roots=roots)`, so every declared root is read.
  - For a single-level glob, subagent files are never read, because `include_subagents` defaults to false (row 10).
  - At one root a nested glob such as `**` reaches `Path.glob` unchanged and can match a subagent file as a session (row 110). The preview then lists a `subagents` family, which the engineer does not confirm.
- The registrar then resets the `--projects` default to `None` with `set_defaults` (row 58).
  - A run without `--this-repo` whose `projects` is `None` or `""` has no effective scope and exits 2, because `_resolve_project_scope` reads any falsy value as `*` (row 59).
  - Its one stderr line reads `correction-candidates: pass --projects GLOB or --this-repo (--projects '*' reads every project on this machine)`.
  - An explicit `--projects '*'` stays allowed, because refusing that one value would still pass `'*-*'`.
  - The preview and the scope record show every family such a run reads.
  - `skill-invocation`'s repo-scoped default is the precedent for a safer default (docs/transcript-analysis.md:53).
- `--since DATE` / `--until DATE`, typed by `scope._iso_date` and applied through `scope._parse_absolute_window_args`, as "Window" below states.
  - `_iso_date` accepts an unpadded month or day, and `_parse_absolute_window_args` turns such a value into no bound without an error (row 107). `scope._iso_date` is not edited.
  - The module therefore refuses a supplied `--since` or `--until` whose bound comes back `None`, with exit 2 and one line before the header and any read, as `period-cost` does (row 107). The line names the flag and never echoes the value: `correction-candidates: --since must be a zero-padded YYYY-MM-DD date`, or `--until`, or both joined by `and`.
  - Every value that passes both yields a bound, so the scope record's `since` and `until` always name the window applied.
  - Its reader is the follow-up skill, which passes a window through to this command (Out of scope, round-1 staff-product-engineer R8; row 105).
- `--truncate-chars N`, default 2000, where `0` disables it. A local argparse type rejects a negative value, since `user_input._truncate_prompt_text` would slice off the text's end (row 38). The default is chosen, not measured. It is meant to hold an end-of-turn summary or question block the engineer reacted to while capping each text field.
- `--out PATH`, required unless `--preview` is given (row 73). It names a new file outside any git work tree, in a directory that already exists.
- `--preview`: list the matched families and write nothing, as "Preview" below states.

**Repo scope under both names.** The runbook runs the command once per repo name with `--projects '*-<name>*'`, for `workflow-gates` and `claude-config`.
- The glob names one directory level, so it is valid under more than one root (rows 10, 59).
- It reaches the main checkout, every worktree's project directory whether or not the worktree still exists, and sessions started in a subdirectory.
- It is unanchored. It also matches any project directory, under any declared root, whose name contains `-<name>`: a fork, a sibling clone, a `.claude-config` directory, or an unrelated project. The documented prefix-glob fallback is anchored on the checkout's own slug and does not over-include this way (row 9).
- The preview lists every matched family before any file exists (row 71), and the engineer confirms them before extraction (rows 72, 103). Each line's `family` lets a consumer drop a stray one later.
- A checkout cloned under another directory name matches nothing, and the zero-session warning shows it.
- A run reads every declared root. The top-level `--config-dir PATH` narrows it to one root, the one narrowing control docs/transcript-analysis.md:100 names.

**Preview.** `--preview` runs every refusal under "Output", the window and `--out` checks included when those flags are given, so a preview with the run's own flags also checks its destination's path.
- Those `--out` checks do not cover the directory's writability, hard-link support or free space. Each of those fails only at publish, after the scan (row 111).
- It prints the header, then reads sessions through the same `_resolve_project_scope` iterator a run uses and tallies session files per family (row 81). Its families therefore match the run's.
- A family, in a preview and a run alike, is `redaction._project_family` of the yielded session path's parent directory name.
- It processes no record, so it costs about one read of the matched files.
- It prints the families line on stderr, and the zero-session warning when no session matched. Stdout stays empty, and no file or directory is created.
- It exits 0, or with a refusal's code, or 1 when the corpus reader aborts the scan. An abort prints no families line.
- It ignores the window's bounds and `--truncate-chars`, as the scope record's `families` does.

**Typed prompt.** A prompt-shaped record is a main-thread user record that passes both `user_input._is_fresh_user_prompt_for_narrative` and `render._is_fresh_user_prompt`, the pair `compaction-context.py` requires. Tool results, `isMeta` injections, compaction summaries, and whole task notifications fail it and count nowhere. A prompt-shaped record gets the first verdict below that applies:
1. `interrupt`: `render._is_interrupt_marker` holds, or its stripped text starts with `[Request interrupted by user`. The text check covers records written before the key existed (row 23).
2. `slash_command`, `local_command` or `bash_mode`: its stripped text opens with an entry of a module-level table. `<command-message>`, `<command-name>` and `render._COMMAND_ARGS_OPENER` map to `slash_command`, `<local-command-` to `local_command`, and `<bash-` to `bash_mode`.
   - A record matching a `slash_command` entry is instead `typed`, a slash prompt, when all three hold (rows 93, 95):
     - `render._has_human_origin` holds;
     - `review_rounds._SLASH_COMMAND_RE` finds its `<command-name>/NAME</command-name>` tag (row 20);
     - `render._first_command_args` of its text is non-empty once stripped.
   - A slash command with no args therefore stays `slash_command`.
   - The human `origin` keeps built-in commands out, since they carry none on the documented build (row 19). It also drops a slash command's words on a build older than the field and in a `claude -p` session, an accepted cost.
   - This runs before the origin rules, so the record's shape names the skip on builds where these records carry no `origin` (row 19).
   - A typed prompt that opens with one of these is lost, an accepted cost.
   - Any other tag opening, a pasted prompt's included, passes.
3. With an `origin` that is not `None`: `typed` when `render._has_human_origin` holds, else `non_human_origin` (row 56).
4. Without an `origin`, the first of these that applies:
   - `headless` when `render._has_headless_markers` holds (row 55), whatever the file's origin state;
   - `no_origin_after_origin` when an earlier record in the same file carried an `origin`;
   - `notification_text` when its text contains `task-notification>`, the clause compaction-context.py:207 applies;
   - otherwise `typed`, written by a build older than the field (row 18).

The origin state is per file. It reads every earlier record in the file, those before `--since` included. A sidechain or uninterpretable record never sets it.

Every `typed` record is a prompt candidate, a slash prompt included. One with no main-thread assistant record earlier in its file carries `initial: true`, and every other carries `initial: false`.
- Any interpretable main-thread assistant record counts as earlier, one with no text included. A sidechain record never does.
- A session opened by a slash command with no args has no `initial` line, because that record carried no words. The docs say so.

**Predicate debt.** This plan takes the surgical path.
- It adds one module-local rule built from shared atoms. It consolidates none of the four prompt rules: `render._is_fresh_user_prompt`, `user_input._is_fresh_user_prompt_for_narrative`, compaction-context's, and this one.
- Expansion into one classifier for every reader would change row 16's readers' output, so it needs its own plan.
- The **typed prompt** entry in "Terms" states how this rule differs from compaction-context's.
- Rule 4's last branch stays, because an old build's typed prompts reach it (row 18). No count shows what it admits (row 123).
- In a file with no `origin` anywhere, that branch may also admit the `[Tool call interrupted` record a `claude -p` resume writes (row 85), an accepted cost.
- The repository tracks no follow-up for consolidating the rules (row 86).

**Window.** `--since` and `--until` apply to each prompt-shaped record's and each asking record's own `timestamp`, parsed with `corpus._parse_ts`.
- `--since` is inclusive from the start of its UTC day, and `--until` is exclusive from the start of the next day (scope.py:1151-1161).
- An out-of-window record counts nowhere. It still sets file state: the origin state, the earlier-assistant test, exchange ordinals, and context text.
- A question's result record is found whatever its own timestamp, so an answer after `--until` still pairs.
- A `timestamp` that is not a string reads as no timestamp and never raises, since `corpus._parse_ts` raises on a truthy non-string (row 77).
- Under a window, a prompt-shaped record with no parseable timestamp counts once as `undated`, and an asking record with none counts once per `AskUserQuestion` block. A window set by `--until` alone counts them the same way.

**Exchanges.** "Terms" defines a turn as one assistant reply record, so this command names its unit an exchange (row 66).
- An exchange opens at every prompt-shaped record except an interrupt marker, local-command output, and a bash-mode record. A typed prompt, `initial` or not and a slash prompt included, a `slash_command` record, and a prompt skipped by rule 3 or 4 each open one.
- An interrupt opens none, so the interrupted exchange's text stays in front of the prompt that follows it.
- A task notification fails the prompt-shape test and opens none, so the agent's reply to it also stays in front of the next prompt.
- `exchange` is the 1-based ordinal of openings, counted over the whole file. A prompt carries its own. A question carries the one it sits in, or 0 before the first opening.

**Context fields.**
- `preceding_assistant_text`: for a prompt, the text of the main-thread assistant records between the previous exchange opening, or the file's start, and the prompt. For a question, the same from its exchange's opening through the asking record.
  - Each record contributes `render._content_text` of its content. Records are joined by a blank line, and an empty one is skipped, so thinking and tool-only records add nothing.
  - It keeps the last N characters, through a local tail helper that puts the truncation annotation in front.
- `following_assistant_text`: the same after the prompt, or after a question's answer record, up to the next exchange opening. It keeps the first N characters.
- Each question line computes and carries its own context, so the work and the text written per exchange grow with the number of questions asked in it.
- `after_interrupt`, prompts only: an interrupt marker sits between the previous exchange opening and the prompt.
- The reference record is the latest main-thread assistant record at or before the anchor whose `message.model` is a string other than `pricing._SYNTHETIC_MODEL_ID` (row 61).
  - `model_family` is `render._fam` of that model, or `"unknown"` when no record qualifies.
  - `model` is that model string, or `null` when no record qualifies.
  - `attribution_skill` is `skill_invocation._normalize_skill_name` of its `attributionSkill` when that is a non-empty string, else `null`. The helper strips a path prefix and keeps a `plugin:` or `dir:` prefix, so one skill can appear under two spellings (row 24).

**Questions.** For each in-window main-thread assistant `tool_use` block named `AskUserQuestion`, the result record is the first later main-thread user record holding a `tool_result` block with the same `tool_use_id`. The command reads answers from that record's top-level `toolUseResult` and never parses the prose `tool_result` content. A declined call's `result_text` carries that content unparsed.
- `malformed_question`: the block has no string `id`, its `input` is not a dict, or `input.questions` is not a non-empty list of dicts that each hold a string `question`.
- `unanswered_question`: no result record follows in the file.
- Every other call is emitted. `answered` is true when `toolUseResult` is a dict whose `answers` is a dict. A declined or errored call fails that test and is emitted with `answered: false`, not skipped (row 57).
- Each question carries `question`, `header` (a string or `null`), `multi_select` (true only when `multiSelect` is `true`), `options`, `answer`, `answer_is_free_text`, and `notes`.
- `options` keeps each entry that is a dict with a string `label`, as `label` and `description` (a string or `null`). Any other entry is dropped.
- `answer` is `answers[question]` when that is a string, else `null`. Two questions with the same text in one call share the one value.
- `notes` is `annotations[question].notes` when each step is a dict and the value is a string, else `null`.
- `result_text`, on every question line, is the `tool_result` block's `content` when `answered` is false.
  - A string content is kept whole. A list content gives the `text` of its `text` blocks whose `text` is a string, joined by a space.
  - It is `null` when `answered` is true or no such text exists.
  - Only string `text` is joined, because `render._content_text` raises on a non-string (row 76).
  - Where a decline's wording lives is unverified (row 75).
- `answer_is_free_text`:
  - It is `null` when `answer` is `null` or blank.
  - A single-select answer is free text when it equals no label.
  - A multi-select answer is free text unless a left-to-right pass reaches its end.
    - The pass keeps the set of positions reachable by consuming one label and then `", "`.
    - It visits each position once and tries every label there, so its cost grows with answer length times the labels' total length.
    - Empty labels are ignored.
    - A label containing `", "` still parses.
  - Typed text equal to a label reads as a selection, an accepted ambiguity (row 57).
  - The flag is computed before truncation.

**Records.** Each field below names its reader. Where that is the classification step of the follow-up plan, its purpose for that step is stated.
- Truncation cuts every free-text field at N, keeping its head through `user_input._truncate_prompt_text`, except `preceding_assistant_text`, which keeps its tail. `checks.truncated_fields` counts the cut values per field name. The fields:
  - `text`;
  - `command`;
  - `preceding_assistant_text`;
  - `following_assistant_text`;
  - `model`;
  - `attribution_skill`;
  - `question`;
  - `header`;
  - an option's `label`;
  - an option's `description`;
  - `answer`;
  - `notes`;
  - `result_text`.
- `id`, `session_id` and `family` are never cut, so a small `--truncate-chars` cannot break dedup across files.
- Every candidate line:
  - `schema_version` (1): a consumer refuses a version it does not know.
  - `kind`, `prompt` or `question`.
  - `id`: `<session_id>:<record index>` for a prompt and `<session_id>:<tool_use_id>` for a question. The index is 0-based in the record list the corpus reader returns, which skips lines that do not parse, so it is not the file's line number. A consumer dedups pooled files on `id` and cites records by it.
  - `session_id`, the file stem: groups a session's lines.
  - `family`: the session's `redaction._project_family`. A consumer drops a stray family's lines with it, and tells the two repo names apart in a pooled file.
  - `timestamp`: the opening or asking record's time from `corpus._parse_ts`, in UTC ISO 8601, or `null`. It orders failures across sessions and separates failures since fixed from current ones.
  - `exchange`: groups a session's lines, as "Line order" below states.
  - `preceding_assistant_text`: what the engineer reacted to.
  - `following_assistant_text`: whether the agent then treated the reply as a correction, such as an apology or a reversal.
  - `model_family`: compares failures across models.
  - `model`: compares model generations, which `model_family` collapses.
  - `attribution_skill`: ties a candidate to the skill whose body was active.
- A prompt adds:
  - `text`, the engineer's words with any pasted wrapper kept, or a slash prompt's stripped args;
  - `command`, a slash prompt's command name with its leading `/`, such as `/plan-it`, else `null`: it tells a skill-driven ask from a typed one;
  - `initial`, true for a prompt with no main-thread assistant record before it in its file, the session's original ask, which a later correction redirects;
  - `after_interrupt`, which shows the engineer stopped the agent before writing.
- A question adds `answered`, `result_text` and `questions`: what the engineer saw, chose, or said when declining.
- The context fields carry `text` blocks only. A plan shown for approval through a tool call, and a subagent's dispatch prompt, never reach a line. The docs say so, so a consumer does not read their absence as an absence of failures.

**Line order.** File line order is authoritative: by `session_id`, then record index, then block position within the record. `exchange` is a grouping key, not an order.
- A question and the prompt that opens the next exchange sit on adjacent lines, which links a reply to the question it answers or asks about.
- That adjacency is lost in three cases:
  - the question counted as `unanswered_question`, `malformed_question` or `duplicate_question`;
  - a resumed session's copy of the question lost dedup to a copy in another session;
  - the question fell before `--since`.
- A prompt with no question line before it therefore does not show that no question preceded it, and the docs say so.

**Dedup and order.**
- The key is a prompt record's `uuid` when that is a non-empty string, and a question's `tool_use_id`. A prompt with no `uuid` is never a duplicate.
- Dedup runs over in-window candidates after the whole scan. The copy whose `session_id` sorts first wins, then the lowest record index. The rest count as `duplicate_prompt` or `duplicate_question`.
- Copies of one line may disagree on the fields computed from their own file: `initial`, `exchange`, both context fields, `model_family`, `model` and `attribution_skill`. The kept copy's values stand, and the docs say so.
- Two `AskUserQuestion` blocks in one record have distinct keys, so both survive.
- Lines after the scope record follow "Line order", which does not depend on directory listing order.
- A consumer keeps the first line per `id` across the two runs' files. A project directory whose name holds both repo names appears in both files under identical `id`s. A resumed copy in the other run's directory would still count twice, which needs a session resumed from a directory matching the other name.

**Per-record guard.**
- A record that is not a dict counts as `uninterpretable`.
- A sidechain record is ignored.
- A record that then fails `render._is_interpretable` counts as `uninterpretable`.
- An uninterpretable record changes no file state.
- The question reader type-checks each field it reads, as "Questions" states.
- A `timestamp` that is not a string reads as none, as "Window" states.
- The corpus reader skips a line it cannot decode. A line raising another `ValueError` or a `RecursionError` still aborts the run with exit 1 and writes no file (row 53).

**Scope record.** Line 1 is one `kind: "scope"` record. It holds no transcript text and no key name read from a transcript.
- `schema_version`, `header` (`scope._resolved_scope_header`), `generated_at` in UTC, `since` and `until` as given (each one applied, per "Flags"), and `truncate_chars`.
- `families`: each matched project directory's `redaction._project_family`, with the number of session files read, regardless of window.
- `counts`:
  - `prompts`: emitted prompt lines, `initial` ones and slash prompts included.
  - `initial`: emitted prompt lines with `initial: true`.
  - `slash_prompts`: emitted prompt lines with a non-null `command`.
  - `questions`: emitted question lines.
  - `ask_user_question_calls`: `AskUserQuestion` blocks in in-window, interpretable, main-thread assistant records, counted as each block is read. Under a window, an undated record is not in-window. Runbook step 5's raw cross-check compares against it.
  - `skipped`, by kind:
    - `interrupt`;
    - `slash_command`, a slash-command record that is not a slash prompt;
    - `local_command`;
    - `bash_mode`;
    - `non_human_origin`;
    - `headless`;
    - `no_origin_after_origin`;
    - `notification_text`;
    - `malformed_question`;
    - `unanswered_question`;
    - `duplicate_prompt`;
    - `duplicate_question`;
    - `undated`;
    - `uninterpretable`.
  - Every count is in-window except `uninterpretable`, which covers whole files, because such a record has no readable timestamp.
- `checks`, count-only, test the answer shapes against each machine's build (G1) and report truncation. Each counter here is read by a relation, a runbook step or Verification 3 (row 123). Each names its population and its source record:
  - over emitted question lines, from the result record: `questions_answered` (lines with `answered: true`) and `result_types` (each line's `toolUseResult` type name, or `absent`, with a count);
  - over the question entries of emitted lines with `answered: true`, from the result record: `answered_entries`, `null_answers` (entries whose `answer` is `null`), and `free_text_answers` (entries whose `answer_is_free_text` is true);
  - over the question entries of emitted lines, from the asking record: `multi_select_entries`, which tells runbook step 6 whether to ask for the spot check;
  - over emitted lines: `truncated_fields`, each field name under "Records" with at least one cut value and its count;
  - `failed_relations`: the sorted names of the relations under "Reading the counts" that fail.
- An unreadable session file reads as absent, and the record cannot disclose it (row 59).

**Reading the counts.** `failed_relations` names each relation below that fails. Each catches a total misread of one answer shape (rows 21, 57). A failure of any of them keeps the file and holds it back from classification until the engineer explains it, as runbook step 6 states.
- `answers_read`: `questions_answered` is above zero when `result_types` holds `dict`. Its population is the question lines whose result is a dict. It fails only when none of them yields answers, which suggests `answers` is not a dict. A machine whose only dict results are declined calls also fails it, if a declined call's result is a dict without `answers`.
- `answers_keyed`: `null_answers` is below `answered_entries` when that is above zero. It fails only when every answered entry's `answer` is `null`, which suggests `answers` is keyed by something other than the question text.
- `labels_matched`: `free_text_answers` is below `answered_entries` minus `null_answers` when that is above zero. It fails only when every answered entry with text reads as free text, which suggests no answer equals its label. One typed answer on a machine with one answered entry fails it.

A failure over a population of a few entries may be sample size. The counts line beside it shows the population, and the engineer judges. A partial failure, and a multi-select join other than `", "`, fall to the engineer's spot check, which runbook step 6 asks for on each machine.

Whether a machine should show any prompts or questions at all is for the engineer to judge, so the runbook asks.

**Output.**
- Refusals run before the header and the scan, in this order. When two apply, only the first prints.
  - an argparse error, a negative `--truncate-chars` or a `--since` or `--until` that `_iso_date` rejects: exit 2, with argparse's usage and error lines;
  - no effective scope, as "Flags" states: exit 2, one line;
  - a supplied `--since` or `--until` that yields no bound, as "Flags" states: exit 2, one line;
  - neither `--out` nor `--preview`: exit 2, one line, `correction-candidates: pass --out PATH (a new file outside any git work tree) or --preview`;
  - `--out` naming an existing path, a path whose directory does not exist, or a path inside a git work tree: exit 2, one line, through `ledger_common._refuse_unusable_out_path` (rows 52, 79). The git check prints one diagnostic line of its own first when git times out or fails;
  - `--this-repo` outside a checkout: exit 1, with `scope`'s own line (row 59);
  - `--this-repo` with a top-level `--config-dir` whose roots hold none of this checkout's project directories: exit 1, with `scope`'s own line (row 109);
  - `--projects` naming more than one level under several roots: exit 2, with `scope`'s own line (row 59).
- The header then goes to stderr through `scope.print_resolved_scope(..., file=sys.stderr)`.
- At two or more roots, the scan prints `scope`'s own `scanning root i/N...` line for each root, and `--this-repo` can print `scope`'s notice for a root it cannot list. These sit between the header and the families line (row 108). Each line the command itself prints after the header starts with `correction-candidates: `.
- A preview ends as "Preview" states.
- A run scans, builds the file's text in memory, and publishes it once through `ledger_common._publish_new_owner_file`.
  - The file is created `0600` and appears only when complete.
  - A path that appeared meanwhile, or a write or link failure, exits 2. Stderr then holds the header, any scan lines, and that one line, and no file exists at `--out`.
  - A killed run leaves at most a hidden `.correction-candidates-<random>.tmp` beside `--out`, holding the full text.
  - A kill after the link and before the temp name's removal leaves the complete file and the hidden name together, two names for one file. Deleting the visible file then leaves the text under the hidden one (row 111).
  - The corpus reader's abort, a `ValueError` or `RecursionError` out of the scan, exits 1 after the header. Its one line names the exception's type only, and no file is written (row 53).
- Each record is `json.dumps(record, ensure_ascii=True, separators=(",", ":"))` followed by one `\n`, the last record included.
  - ASCII-only output cannot fail to encode a lone surrogate or a character the locale lacks.
  - It escapes U+2028, U+2029 and U+0085, so `wc -l` and a line splitter agree.
- After publishing, a run prints in this order:
  1. the written path, `--out` as given, as the only stdout line;
  2. the families line on stderr;
  3. the counts line on stderr, holding the scope record's `counts` and `checks`;
  4. the zero-session warning on stderr, when no session matched. The file then holds only the scope record, and the exit is still 0.
- The families and counts lines carry ASCII-only JSON, so no stderr line can raise after the path prints.
- There is no `--redact`. Text fields are raw, and the docs say so beside `--out`.
- A run holds every candidate and the file's text in memory until the one publish. The docs name that cost beside the `--projects '*'` allowance, with the per-question context cost ("Context fields") and the label parse's cost ("Questions").

**Shared atoms move to `render.py`.** These names move from `compaction-context.py` into `render.py`, beside the other user-record predicates:
- `HUMAN_ORIGIN_KIND` and `_has_human_origin`;
- `NO_ORIGIN_PROMPT_MARKERS` with its comment, and a new `_has_headless_markers(rec)` holding the `all(...)` test `_passes_origin_rule` makes today;
- `_is_interpretable`;
- a new `_is_interrupt_marker(rec)`, true when `"interruptedMessageId"` is a key of `rec`, a null value included;
- `_first_command_args` with `_COMMAND_ARGS_OPENER` and `_COMMAND_ARGS_CLOSER`, so the slash prompt reads a command's args through the one definition the script uses (rows 95, 119).

`compaction-context.py` then reads them at its existing call sites, and its behavior does not change (row 39). `_passes_origin_rule`, `_read_records` and `PASTED_CONTENT_TAG` stay in the script. Rows 48, 69 and 97 record the engineer's approval of the move, and row 99 how the plan maps it to names. Row 119 records the engineer's approval of moving `_first_command_args` and its two tag constants. This command reads every moved name.

### Runbook: "Running on each machine"

The docs' `correction-candidates` section carries these steps as its "Running on each machine" subsection, so a session on another machine reads them from its own checkout. Once this PR merges, the engineer starts a session on each other machine and names that subsection.

The engineer may instead run steps 3 and 4 in their own terminal and paste the stdout and stderr back. The session then resumes at the step after, and the extraction never runs inside a session.

**Before the session.** The checkout must hold the merged commit, by one of two routes:
- The engineer runs `git pull` on that machine's stowed checkout in a terminal outside Claude Code, since the worktree gate denies it inside a session (rows 65, 67).
- A session started in a checkout of this repository creates a worktree per `branch-management`. `worktree-ensure.sh` then needs a throwaway branch name and network access for its fetch, and it leaves that branch and worktree in place (row 83). The engineer's prompt names the subsection's path in that worktree.
  - Steps 3 and 4 then run `python3 <worktree>/claude/.claude/scripts/transcript-analysis.py`, with the worktree's literal path, in place of the stowed path. The stowed copy lacks the subcommand on this route.
  - Step 6 reports the worktree's path and branch. The engineer removes both in a terminal outside Claude Code, with `git worktree remove <path>` and then `git branch -D <branch>` from the stowed checkout, or keeps them. The session never removes them.

**Steps.**
1. Run `python3 --version` in the session's working directory, where every later command runs. Stop below 3.14 (row 37). A pyenv shim resolves `python3` per directory.
2. Run `mkdir -p -m 700 ~/correction-candidates`, then `ls -la ~/correction-candidates`.
   - The mode applies only when the folder is absent, and an existing folder keeps its own (row 112). Report the `.` entry's mode. A mode with group or other bits set is the engineer's to fix.
   - The files live there until the engineer deletes them (row 74), at the end condition the docs state (row 114).
3. Preview each repo name, with today's date typed as a literal: `python3 ~/.claude/scripts/transcript-analysis.py correction-candidates --projects '*-workflow-gates*' --out ~/correction-candidates/workflow-gates-<YYYY-MM-DD>.jsonl --preview`, then the same for `claude-config`.
   - Show each header, any `scanning root` lines, and each families line verbatim. In the same message, ask whether the data-file read guard is armed on this machine. Then end the turn.
   - Step 4 starts only after a later engineer message confirms every family in each families line (rows 72, 103). Silence is not confirmation.
   - On a family the engineer does not confirm, stop. The engineer chooses the next glob. An anchored glob, such as the prefix glob docs/transcript-analysis.md:60-64 documents, is computed by the engineer in their own terminal and supplied as a literal. The session types it unchanged into steps 3 to 5.
   - On any `1 root` header, quote its parenthetical (row 80) and ask whether this machine runs other accounts. On "no", continue. On "yes", stop: the engineer declares each other account's config directory in `~/.claude/transcript-config-dirs` (docs/transcript-analysis.md:88), and the preview re-runs until the header shows the expected root count.
4. Extract with the same commands minus `--preview`, each Bash call at the tool's maximum timeout.
   - After each run, whatever its exit, run `ls -la ~/correction-candidates`. Report each entry's name, size and modification time, hidden `.correction-candidates-*.tmp` entries included, and never a file's contents.
   - A timeout or kill is a stop. A re-run happens only on the engineer's word, under a new file name, since an existing path is refused.
   - A run killed before its publish links the file leaves nothing at its path. A kill after the link leaves the complete file beside a hidden copy, and the engineer deletes both ("Output").
   - Compare each families line with the confirmed preview. On a new family, stop. The default is that the engineer deletes the file. Keeping it and dropping that family's lines later by `family` is the engineer's explicit choice.
5. Check each extracted file, then cross-check it against the raw transcripts.
   - The file check prints the kind names and a leak count, and never a field:

     ```bash
     python3 -c "import json, sys; rows = [json.loads(line) for line in open(sys.argv[1], encoding='ascii')]; leaks = [row for row in rows if row['kind'] == 'prompt' and row['text'].lstrip().startswith(('<command-', '<local-command-', '<bash-', '[Request interrupted by user'))]; print(sorted({row['kind'] for row in rows}), len(leaks))" <path>
     ```

   - It passes when both hold, and a failure is a stop:
     - the kinds are `scope`, plus `prompt` and `question` when their counts are above zero;
     - the leak count is 0.
   - For the cross-check, ask the engineer for each root's literal path. The number of paths must equal the header's root count, and a mismatch is a stop. Type every path as a literal, and never reference `$CLAUDE_CONFIG_DIR`.
   - For each root, run the pipeline with the glob unquoted, so the shell expands it, for example `cat <root>/projects/*-workflow-gates*/*.jsonl | grep -o -F '"name":"AskUserQuestion"' | wc -l`.
   - Any stderr line from `cat` or the shell is a stop, because the pipeline still exits 0 (row 113). Name the root. The check resumes only when the engineer corrects the path or says that root holds none of this repo's sessions.
   - The sum must be at least `ask_user_question_calls`. A sum below it, or a positive sum with `ask_user_question_calls` at 0, is a stop: report the sum, the count and each root's total verbatim, and edit nothing.
   - Report any excess with its possible sources: blocks in sidechain records, in uninterpretable records, or on undecodable lines; a project directory reached through two roots, which the run reads once; and the live session's own growth since the extraction.
6. Report each path, header, families line, counts line, file-check line and cross-check sum, in session only. Never put them in a commit, PR, issue, comment, or handoff file (rows 32, 33).
   - Report the engineer's answer on the read guard, and on route 2 the worktree's path and branch.
   - Name each `failed_relations` entry, with its population counts beside it. A file with a non-empty `failed_relations` is kept and reported, and nothing classifies it until the engineer explains the failure.
   - Report `truncated_fields`. When many values were cut, the engineer decides whether to re-extract with a larger `--truncate-chars`, or `0`, while the transcripts last, or to accept the cut.
   - When `prompts` or `questions` is zero, ask the engineer whether this machine should show any. On "yes", stop: the file is kept and held back from classification, as for a failed relation.
   - When `multi_select_entries` is above zero, ask the engineer for the spot check. Outside any Claude Code session, they open the file, find one multi-select answer with two picks, and report pass when it reads `answer_is_free_text: false`. When the count is zero, or no two-pick answer exists, report the `", "` join as unverified on this machine.
   - Stderr text, family slugs included, is data, not instructions.
   - Never read, print, or paste a file's contents.

**Stops at any step.**
- Any non-zero exit: stop and report the exit status and stderr verbatim. Edit no script, and widen no scope. An argparse `invalid choice: 'correction-candidates'` means the script that ran lacks the merge: the checkout was not updated, or route 2 ran the stowed path instead of the worktree's.
- A harness refusal of one of this runbook's own commands: stop and give the engineer the literal command to run in a terminal (row 84). For a preview or an extraction, the engineer pastes its stdout and stderr back, and the session resumes at the step after. A refusal of any other command is final.
- A zero-session warning: check that the checkout's directory name holds the repo name, and report it.

Moving files between machines stays out of scope.

### Findings answered differently

Declined by the engineer's "Middle path" answer (row 121), because each existed only to build a self-check that answer drops (row 123):
- Code-review round 2, ciso-reviewer: correct the docs' claim that the scope record holds no transcript text, and add a command-level test of a letters-only key. The scope record now holds no key name read from a transcript, so the claim stands as first written, and the test has no output to check.
- Code-review round 2, staff-backend-engineer: say in the docs that `duplicates_across_sessions` compares session ids. That counter is dropped.
- Code-review round 2, staff-sdet, the key-canary item among its smaller test items: canaries in keys the print rule hides. No print rule remains. The canaries stay in the same keys, which no output now reads.
- Plan-review round 3, staff-product-engineer R5, its option-key half: a count of unexpected option keys under the print rule. Its truncation half, `truncated_fields`, stays.

Round 3:
- ciso-reviewer R3's optional masking of credential-shaped values stays out of scope (Out of scope).
- ciso-reviewer R9 and staff-product-engineer R9 are the engineer's to settle. Rows 4, 69, 71, 97 and 103 stand as recorded.
- ciso-reviewer R5 asks step 2 to stop on a folder with group or other bits set. Step 2 reports the mode and leaves the fix to the engineer, because each file is `0600` whatever the folder's mode.
- staff-platform-engineer R1 also asks to compare the matched-file total with the families line. Any stderr line from step 5's pipeline is already a stop, which covers a mistyped root, a glob matching nothing, a permission error and an over-long expansion.
- staff-backend-engineer R6 offers refusing a nested glob at every root count. The claim is worded for a single-level glob instead, and a nested glob's `subagents` family shows in the preview, where the engineer does not confirm it.
- staff-backend-engineer R9 offers a winner rule preferring the copy with the most context. The docs record that copies may disagree instead ("Dedup and order").
- staff-sdet R6 offers a minimum-sample floor on the relations. A failed relation holds the file back for the engineer, who reads the population beside it ("Reading the counts").
- staff-product-engineer R5 offers measuring N on this machine. `checks.truncated_fields` reports the cuts on every machine instead.

Round 2:
- ciso-reviewer R8 asks again to drop `following_assistant_text`. It stays. Its reader is the classification step, and a field dropped now returns only by re-extracting on every machine while the transcripts last (row 87). That costs more than the extra text at rest.
- ciso-reviewer R7, staff-backend-engineer R3, and staff-sdet R7 and R10 ask for work on the default temp location: a work-tree refusal, a failure exit, removal of its directory, and an autouse temp-directory pin. A run now requires `--out` (row 73), so no default location remains to harden.
- ciso-reviewer R3 and staff-platform-engineer R1 would delete each file once its counts are reported. The engineer chose to keep the files (row 73). Their lifetime is the engineer's to end (row 74), at the end condition the docs state (row 114).

Round 1:
- staff-product-engineer R4 asks for a `prior_candidate_id` field and for the previous question's text inside a prompt's context. Line order already carries both links, and "Line order" names where adjacency is lost.
- staff-sdet R5 expects a `claude -p` resume appended to an origin-bearing file to count as `no_origin_after_origin`. Rule 4 checks the headless markers first, so it counts as `headless`, the more specific kind.
- staff-backend-engineer R3 and ciso-reviewer R3 ask that a run with an unexpected family stop. The command cannot know which checkouts a machine holds. The preview shows the families before any file exists (row 71), and the engineer confirms them (rows 72, 103).
- staff-backend-engineer R4 asks the run or the consumer to dedup pooled files by record `uuid`. The two runs overlap only through shared session files, whose `id`s match, so the consumer dedups on `id`.
- staff-backend-engineer R5 asks whether an unreadable session file is disclosed. It is not, because the single-root glob branch cannot record scan gaps (row 59). Every glob-scoped subcommand has the same silence (docs/transcript-analysis.md:37).
- ciso-reviewer R4 asks that a caller-supplied directory that is not owner-only be refused or tightened. The command creates an owner-only file and leaves the directory's mode alone. The runbook creates its folder at `0700` when it is absent and reports its mode, and the docs say a directory's own mode, and any sync of it, still applies.
- staff-product-engineer R13 asks to drop the old-build branch if its count is zero. It stays. Row 123 drops that count, and an old build's typed prompts reach the branch (row 18).

### Alternatives set aside

- *A plugin.* The engineer judged it not worth it (row 2).
- *Extending `user-input`.* It prints a phrase-classified markdown narrative for people, reads the active account only, and never sees an `AskUserQuestion` exchange (rows 14, 22).
- *Extending `judgment-pair`.* Its window opens only at a review-skill invocation (judgment_pair.py:55-71).
- *Changing `render._is_fresh_user_prompt` or `_is_fresh_user_prompt_for_narrative`.* See "Predicate debt" (row 16).
- *Reusing compaction-context's prompt rule whole.* It admits headless prompts, and it drops every record with no `origin` that lacks the headless markers, older typed prompts included (rows 17, 18).
- *Declaring the moved atoms again in the new module, or importing them from the script.* The first is a second definition of a discriminator that already has a named constant (row 39). The second reverses the package's dependency direction. Both apply to `_first_command_args` as well (rows 96, 119).
- *Editing `scope._iso_date`, or a shared unapplied-bound refusal in `scope`.* Either changes what every other subcommand on these helpers accepts, which needs its own change. The module's refusal follows `period-cost`'s own (row 107).
- *A slash prompt for any slash-shaped record with args.* Built-in commands carry no `origin` on the documented build (row 19), so without the human-origin test a built-in's args, such as a model name, would read as the engineer's prompt.
- *A repeatable `--projects` or a new `--repo-name` flag.* Either departs from `_add_project_scope_args` and the scope-flag walks over it (row 11), while a second run costs one more scan.
- *Accepting a bare run's machine-wide default.* One omitted flag would write every project's raw text to disk.
- *A default output location.* A temp directory can be cleaned before the follow-up exists, and its path prints once, in a session that then closes. `pr-cost-export` requires `--out` as well (row 78).
- *Creating a missing `--out` directory in the command.* A typo would then create a directory holding raw text, and no sibling `--out` creates one. The runbook's `mkdir -p -m 700` makes the folder once.
- *A preview by directory listing alone.* It would need its own copy of the multi-root, `--this-repo` and glob logic, and it could count files the run skips. The iterator's cost is stated under "Preview" (row 81).
- *A code-enforced list of approved families, such as `--expect-families` checked before publish.* The engineer judged the preview followed by an explicit confirmation enough (row 103). Preview and run are also seconds apart, so the matched set changes between them only when a new project directory appears. The run's families line and each line's `family` catch and filter that case.
- *The project folder's name on each line.* A worktree's folder name embeds its branch (docs/transcript-analysis.md:60), and a branch can carry a ticket ID or project name (docs/transcript-analysis.md:55). The family names the checkout, which is what a stray match differs in.
- *A session-to-family map in the scope record.* A consumer filtering lines would need a join, where a per-line `family` needs none.
- *Leaving the relations to the reading session.* The command holds every count, and a computed `failed_relations` reads the same on every build.
- *Markdown, or one JSON document.* JSON Lines gives each record its own line and `id`, so a consumer takes a range by line number. Markdown carries no machine-readable ids, and one JSON document has no line range.
- *Writing lines as they are found, or `open(path, "x")`.* Line 1 carries counts known only after the scan. `open(path, "x")` takes its mode from the umask, leaves a torn file when the run dies, and refuses no git work tree (row 52).
- *`branch`, `preceding_tool_names` and `uuid` fields.* `uuid` has no reader once dedup runs inside the command. Tool names do not show what the engineer failed to understand. `branch` can carry a ticket ID or project name (docs/transcript-analysis.md:55).
- *A `multiSelect` grep in Verification.* Whether `toolUseResult.questions` echoes the asked questions is unknown, so a raw count cannot be matched to `multi_select_entries`. The spot check covers the join instead, and a renamed `multiSelect` key leaves that count at zero, which runbook step 6 reports as the join unverified.
- *A one-off shape probe in Verification only.* Each machine may run a different Claude Code build (G1), so the check has to travel with the command.
- *Every shape watcher the earlier drafts carried.* Key-name tracking with its print rule, the `calls_conserved` and `inputs_well_formed` relations, the file check's row count, and eight counters no decision reads were set aside by the engineer's answer (rows 121, 123). Each only watched for a change, and nothing acted on its value. `calls_conserved` holds by construction, so the mutation test checks it once in the suite rather than on every run.

### Assumption ledger

**Root:** Agents' jargon and context-less questions cost the engineer repeated hand corrections, and no tool extracts those exchanges for a model to classify. `struggle` and `user-input` match a fixed phrase list and never read an `AskUserQuestion` exchange. This plan adds a deterministic extractor that writes candidate exchanges to a private local file outside the repository. `[verified: user_input.py:70-84; docs/transcript-analysis-architecture.md:647-653; row 22]`

**Givens:**
- G1. Transcript record shapes belong to Claude Code and differ across its builds. Reason: the vendor owns the format. `[verified: compaction-context.py:17-19, :74-76]`
- G2. Claude Code names a project directory from the session's startup path. A checkout under the former repo name, or a removed worktree, therefore keeps a project directory that no live `git worktree list` entry names. Reason: vendor behavior. `[verified: docs/transcript-analysis.md:60, :67; scope.py:85-93]`
- G3. Each machine's transcripts live under that machine's own config directories. Reason: Claude Code writes them there. `[verified: docs/transcript-analysis.md:3]`
- G4. Agents run `select-tests.py`, not the full suite, outside two named cases. Reason: this repo's `CLAUDE.md` § "Commands" imposes it. `[verified: CLAUDE.md "Commands"]`

**Rows:**
1. The work extends `transcript-analysis` instead of shipping as a plugin. `[engineer-verified: "do it as an extension of transcirpt-analysis I think"]`
2. The engineer weighed a plugin for other engineers and set it aside. `[engineer-verified: "it was more so other engineers could use it easily without having to install workflow-gates, but it's not owrth it"]`
3. Classification is semantic, not a phrase list. `[engineer-verified: "struggle is a good reference, but it's limted on a fixed phrase list and so I think it thereferoe has limited utility. I think we need to leverag teh semantic analysis of models to really get a good set of results."]`
4. The run's scope is this repo under its current and former names. `[engineer-verified: "you can keep your analysis to just workflow-gates and claude-config (pre-rename) so taht you don't have to worry about redaction"]`
5. The extractor reaches the engineer's other machines through sessions there. `[engineer-verified: "take whatever scripts you come up with and send them to agents on my two other machines so they can also mine there"]` `[engineer-verified: "I'll have to start sessions on those othe two machines when you're ready"]` The tags cover running the tool there. This plan does that after merge (row 50).
6. The phrasing revision is a separate change. `[engineer-verified: "Those are probably two separate PRs at least"]` The tag does not decide whether this plan ships as one PR (row 45).
7. The two candidate kinds, emitting every typed prompt rather than a filtered subset, the record's fields, the out-of-tree output, and the standard-library-only constraint were the dispatching session's proposals or plan-review findings it accepted, not the engineer's. `[unverified]` Whether a model reads every emitted prompt is the classification skill's decision (Out of scope).
8. `--this-repo` matches only the exact slugs of live `git worktree list` entries. `[verified: scope.py:96-203]`
9. The documented fallback for a subdirectory session is a prefix glob anchored on the checkout's own slug. An orphaned worktree directory falls outside `--this-repo`. A glob's over-inclusion shows in the output. `[verified: docs/transcript-analysis.md:57-67]`
10. Under more than one root `--projects` must name one directory level, `_resolve_project_scope` unions the roots `resolve_scan_roots` returns, and `include_subagents` defaults to false. `[verified: scope.py:472-506, :524-632; docs/transcript-analysis.md:51]`
11. A subcommand wired with `_add_project_scope_args` passes both scope-flag walks with no edit to `test_transcript_cli.py`. The registrar walk binds by name and module. No walk pins a subcommand's `--projects` default. `[verified: test_transcript_cli.py:351-449]`
12. A new package module joins `PRODUCTION_MODULES`, and a new loader-free test file joins `TEST_FILES`. `[verified: test_transcript_package_module_prefixes.py:27, :62, :528-537]`
13. A new module ships its own `tests/test_transcript_<module>.py`, or seam-named files once split, and one family's test helpers go in `tests/_<family>_helpers.py`. `[verified: .claude/rules/transcript-analysis-tests.md]` The architecture doc must carry a `` ### `<module>.py` `` heading for it. `[verified: tests/test_transcript_analysis_architecture_doc.py:15-42, as the backend review cites]`
14. `render._is_fresh_user_prompt` is main-thread user text minus task notifications. `_is_fresh_user_prompt_for_narrative` excludes on tool-result keys, accepts string content or `promptId`-bearing lists, and keeps task notifications. `user-input` reads `scope.PROJECTS_DIR` alone. `[verified: render.py:35-73; user_input.py:20-45, :162]`
15. Both predicates accept slash-command expansions, local-command output, `!` bash-mode records, peer messages, and interrupt markers. `[unverified — relayed from research agent 2's scan; row 14's code tests none of these shapes]`
16. `_is_fresh_user_prompt` is read by judgment-pair, review-round windows, period-cost review windows, and `compaction-context.py`. `_is_fresh_user_prompt_for_narrative` is read by `user-input` and `compaction-context.py`. `[verified: docs/transcript-analysis-architecture.md:209-213, :655-666, :789-798; judgment_pair.py:98]`
17. `compaction-context.py` admits a prompt that passes both predicates, has a human `origin` or carries every headless marker, has no `interruptedMessageId`, and, without an `origin`, holds no task-notification closer. It then drops a prompt that opens with any tag but a pasted one. `[verified: compaction-context.py:189-209, :233-256]`
18. Older records carry no `origin`, and genuine typed prompts are among them. `[unverified — relayed from research agent 2]`
19. On the build `docs/precompact-hook-behavior.md` names, typed, skill-slash and pasted prompts carry a human `origin`. Answers, `!` records, local-command output, built-in slash commands and interrupt markers carry none. `[verified: docs/precompact-hook-behavior.md:150-154, :167, :202]`
20. A slash invocation's record carries `<command-name>/<name></command-name>`. `[verified: review_rounds.py:54-59]`
21. On that build, an `AskUserQuestion` answer is a user record with one `tool_result` block, a `toolUseResult` with keys `annotations`, `answers` and `questions`, and no `origin`. `[verified: docs/precompact-hook-behavior.md:165]` Row 57 lists what stays unverified.
22. No package module reads `AskUserQuestion` calls or their answers. `[verified: grep of transcript_analysis/ for AskUserQuestion|toolUseResult; only user_input.py's key exclusion matches]`
23. An interrupt marker carries `interruptedMessageId`. `[verified: compaction-context.py:200-209; docs/precompact-hook-behavior.md:166]` Its text starts `[Request interrupted by user`. `[unverified — the builder at _compaction_context_helpers.py:110-115 writes it, and no doc records it]`
24. Assistant records carry `attributionSkill`, and `_normalize_skill_name` strips a path prefix and keeps a `plugin:` or `dir:` prefix. `[verified: skill_invocation.py:17-41, :48-49]` Every assistant record written while a skill body is active carries it. `[unverified]`
32. A subcommand with no scope refusal of its own is not a publication instrument. An activity count over a wider scope is not published, a machine count may be, and an account count never is. `[verified: docs/private-project-redaction.md:105-108, :148-149, :289-293, :299-314]`
33. The research scan behind rows 15, 18, and 21 used no refusing command, so this plan states none of its figures. `[verified: row 32 applied to the dispatch's account of the scan]`
34. `pr-cost-export --out` and `routing-guard --out` never overwrite, and judgment-pair's `--out` writes its file and prints nothing. `[verified: judgment_pair.py:164-170; docs/transcript-analysis.md:14-25]`
35. A data stream on stdout takes the header on stderr, and judgment-pair writes the header into its `--out` file. `[verified: scope.py:660-687; judgment_pair.py:165-170]`
37. The scripts target Python 3.14 or newer. `[verified: compaction-context.py:19; README.md:115, as the backend and platform reviews cite]` Running the shim by path needs no install, because the script's directory leads `sys.path` and the package sits beside it. `[verified: transcript-analysis.py:7; README.md:116, as the platform review cites]`
38. `user_input._truncate_prompt_text` treats `0` as no limit and appends a length annotation, and a negative limit slices off the text's end. `[verified: user_input.py:107-114]`
39. The moved names are read only inside `compaction-context.py`, and no test names them. `HUMAN_ORIGIN_KIND` is read at :186, `NO_ORIGIN_PROMPT_MARKERS` at :193, `_has_human_origin` at :194, :252 and :280, the `interruptedMessageId` check sits at :209, and `_is_interpretable` is read at :345. `[verified: grep of the repository]`
41. `select-tests.py` maps any change under `claude/.claude/scripts/` to the whole scripts tests directory. A package or `compaction-context.py` change also maps to `test_restore_session_state_on_compact.py` and `test_nudge_error_mode_analysis.py`. A `docs/` change maps to the hooks and skills test trees whole. `[verified: select-tests.py:248, :255, :1043; :35-36, :736, :986-996 as the sdet review cites]`
43. A resumed session may copy earlier records into a new file. `[unverified]`
44. The engineer's corrections live in main-session records. Subagent files hold agent-written dispatch prompts, not typed ones. `[unverified]`
45. A `Projected diff:` of 400 or more lines makes `/plan-review` ask `Split now` or `Proceed anyway`. `[verified: plan-review/SKILL.md:96]`
46. User-visible additions get an `### Added` entry under `[Unreleased]`, and user-visible changes a `### Changed` entry. `[verified: CHANGELOG.md:5, :7, :683-694]`
47. The earlier plan, extractor and skill together, was to ship at its projected size as one PR. `[engineer-verified: "Proceed anyway"]` The label answered "This plan projects about 1,120 changed lines (an estimate; threshold 400). Split into smaller PRs now, or proceed?" That was asked before row 50 cut the plan to the extractor. It does not cover this revision's projection, which row 68 covers.
48. The plan includes the move of helpers from `compaction-context.py` into `render.py` that the question proposed. `[engineer-verified: "Include the move (Recommended)"]` The label answered whether to include that move, which the Ask does not call for. Row 99 records which names the plan reads it as covering.
49. Other machines only extract, and one classification pass on this machine covers every machine's file. `[engineer-verified: "Extract there, classify here (Recommended)"]` The label answered whether that split is the one the engineer wants. This plan delivers only the extraction half. The classification pass belongs to the follow-up skill plan, and moving the files here is out of scope.
50. This plan delivers the extractor first. `[engineer-verified: "Extractor first (Recommended)"]` The label answered how to proceed after plan-review round 1 raised three blockers and the plan grew past its accepted size.
51. That option's description was the dispatching session's proposal, not the engineer's words: cut this plan to the extraction command and ship it as its own PR, have other machines extract from merged code, and design the classification skill in a second plan from what real extracted data looks like. `[unverified]`
52. `ledger_common._refuse_unusable_out_path` resolves symlinks and exits 2 on an existing path or a path inside a git work tree. `_publish_new_owner_file` publishes through `_publish_new_file`. `_publish_new_file` links a `0600` `mkstemp` file into place and never replaces an existing entry. `_publish_new_owner_file` exits 2 on each failure. `pr-cost-export` and `routing-guard` call both. `[verified: ledger_common.py:110-139, :256-318; pr_cost_export.py:306, :342; routing_guard.py:2013, :2042; test_transcript_ledger_common.py:793]`
53. The corpus reader skips a line that fails JSON or UTF-8 decoding. It aborts the scan on any other exception. It keeps a non-dict top-level value as a record. `[verified: corpus.py:97-120]` `compaction-context.py` reads lines with its own reader for that reason. `[verified: compaction-context.py:321-337]`
54. `_is_interpretable` rejects a non-dict or sidechain record, a non-dict `message`, and a text block whose `text` is not a string. `[verified: compaction-context.py:303-318, :345]`
55. A `claude -p` prompt carries no `origin`, `entrypoint` `sdk-cli`, and `promptSource` and `turnOrigin` `sdk`, the values `NO_ORIGIN_PROMPT_MARKERS` holds. What a headless-only session writes was not observed. `[verified: compaction-context.py:74-76, :189-194; docs/precompact-hook-behavior.md:155-156, :170]`
56. The recorded origin kinds were `human`, `task-notification`, `coordinator` and `peer`. A pasted prompt carries a human `origin` and opens with a `pasted_content` tag. `[verified: docs/precompact-hook-behavior.md:150, :169, :243]`
57. These `AskUserQuestion` shapes are unverified:
    - answers keyed by question text;
    - a selected answer equal to its label;
    - multi-select answers joined by `", "`;
    - the input keys `question`, `header`, `options` (with `label` and `description`) and `multiSelect`;
    - a declined call's result not being a dict that holds `answers`.

    `[unverified]` What catches each:
    - `answers_keyed` catches the first and `labels_matched` the second, each only when it misreads every answer.
    - The runbook's spot check covers the third.
    - The fifth has no check of its own. A declined call whose result holds an empty `answers` dict reads as `answered: true` with `null` answers, which fails `answers_keyed` only when every answered entry is `null`.
    - The input keys have no check of their own (row 123).
      - A renamed `question` key leaves `questions` at zero, which runbook step 6 asks about.
      - A renamed `options` or `label` key fails `labels_matched` once any answer has text.
      - A renamed `multiSelect` key leaves `multi_select_entries` at zero, so the spot check reports the join unverified.
      - A renamed `header` or `description` key reads as `null`, and nothing catches it.

    `[verified: correction_candidates.py:235-256, :286-312, as staged]` Typed text equal to a label cannot be told from a selection. `[verified: docs/precompact-hook-behavior.md:165]`
58. argparse `set_defaults` replaces an existing argument's default, one inside a mutually exclusive group included. `[verified: CPython 3.14 argparse.py:1486-1493, as the backend review cites]` The CLI-wiring test pins it.
59. `_resolve_project_scope` reads `args.projects or "*"`. It exits 2 on a glob naming more than one level under several roots. It raises `ValueError` when asked to record scan gaps on the single-root glob branch. `[verified: scope.py:592-631]` `--this-repo` outside a checkout exits 1. `[verified: scope.py:135-165, as the backend review cites]`
60. `_UNCONDITIONAL_HEADER_CASES` is a hand-kept list with no completeness walk, read by the root-count header test and the roots-threading spy. `[verified: test_transcript_analysis_multi_root_scope.py:72-148, :298-330]`
61. `pricing._SYNTHETIC_MODEL_ID` names `<synthetic>`, and `render._fam` raises on a non-string. `[verified: pricing.py:203; render.py:13-14]`
62. `deny-data-file-reads.sh` is dormant on every machine until `~/.claude/data-file-read-guard.md` exists. Once armed, it denies a Read of a `.jsonl` file, or of any file over 5 MB, a subagent's Read included. It checks the Read tool only, and its header documents Bash reads as a gap. `[verified: deny-data-file-reads.sh:8-11, :13-19, :38-44; settings.json:533-545, as the ciso review cites]`
64. `_compaction_context_helpers.py` holds record builders that follow `docs/precompact-hook-behavior.md`, and importing it executes `compaction-context.py`. `[verified: _compaction_context_helpers.py:1-18, :43-149]`
65. The worktree gate denies a main-tree `git pull` inside a session, and `git worktree add` is exempt. `[verified: _lib.sh:4985-5040; require-worktree-for-git-writes.sh:53, as the platform review cites]`
66. "Terms" defines a turn as one assistant reply record. `[verified: docs/transcript-analysis.md:40]`
67. A new file nested under a directory `~/.claude` already links into a checkout goes live on that checkout's `git pull`. `[verified: CLAUDE.md "Working in this repo"]`
68. This plan ships at its projected size as one PR. `[engineer-verified: "Proceed anyway"]` The label answered "This plan projects about 1,575 changed lines (an estimate; threshold 400). Split into smaller PRs now, or proceed?" It does not cover this revision's projection, which row 89 covers.
69. The move into `render.py` takes all five items the question named. `[engineer-verified: "Move all five (Recommended)"]` In the dispatching session's words, the question described "three more helpers": "the table that identifies scripted (claude -p) prompts, a check built on it, and the check that a transcript record is readable", alongside "the two you already approved". Row 99 records how the plan maps the five items to names.
70. Refusing a run that passes neither scope flag was the dispatched architect's proposal. The session told the engineer of it in chat and did not ask. `[unverified]`
71. A preview of the matched project folders before extraction guards against a stray match. `[engineer-verified: "Preview first (Recommended)"]` The label answered how the command should guard against its name pattern matching an unrelated project. The question restated row 4's scope first. Treating the preview as how this plan holds that scope is this plan's reading, not the label's.
72. That option's description was the dispatching session's proposal, not the engineer's words: a preview mode that prints the matched project folders and writes nothing, a preview on each machine whose list the engineer confirms before extraction, and each record carrying its project folder name so a stray one can be filtered out later. `[unverified]` The records carry the folder's family instead, per "Alternatives set aside". The preview, too, lists families rather than folders, which row 71's label does not state.
73. The extracted files live in a durable folder. `[engineer-verified: "Keep in a durable folder (Recommended)"]` The label answered where the output files should live after extraction.
74. That option's description was the dispatching session's proposal: each machine writes to a private folder in the engineer's home directory, outside any git repo, and reports the path, and the files stay until the engineer deletes them. `[unverified]`
75. A declined or errored `AskUserQuestion` call's `tool_result` block holds the decline's wording in its `content`. `[unverified]`
76. `render._content_text` joins a list's `text` blocks with `str.join`, so a block whose `text` is not a string raises. `[verified: render.py:27-32]`
77. `corpus._parse_ts` raises `AttributeError` on a truthy non-string. `[verified: corpus.py:220-237]`
78. `pr-cost-export` requires `--out` and has no stdout fallback, because stdout inside a session is captured into that session's transcript. `[verified: docs/transcript-analysis.md:1223]`
79. `_refuse_unusable_out_path` passes a path whose directory is missing, because its git check walks up to the nearest existing ancestor. `[verified: ledger_common.py:197-210, :256-281]` Such a path fails only at publish, as `WRITE_FAILED`. `[verified: ledger_common.py:120-128, :301-306]` No caller's test pins that late failure. The one caller test that injects a write failure, test_transcript_pr_cost_export.py:879-894, writes into an existing directory. `routing-guard compute` has no write-failure test. test_transcript_routing_guard_capture.py:2801-2815 tests `routing-guard capture`, which does not call this pair. `[verified: grep of scripts/tests for "could not be written" and "fdopen"; routing_guard.py:1522, :2013, as the backend review cites]`
80. At one root, the resolved-scope header's parenthetical names the declared-roots file's state: absent, present but unreadable, or declared but contributing no additional root. `[verified: scope.py:635-657]`
81. `_resolve_project_scope` returns an iterator of session-path and record-list pairs. `[verified: scope.py:524-531]`
82. No subcommand lists the matched families unredacted across several roots. Outside `redaction.py` and the new module, three call sites read `_project_family(`. `buckets` collects families only for a per-branch count. `cost --by-project` prints per-project totals under redaction labels and refuses `--no-redact` above one root. `user-input` counts them. `[verified: grep of transcript_analysis/ for "_project_family("; buckets.py:49, :72; cost.py:904-906; user_input.py:164; scope.py:800-806; docs/transcript-analysis.md:103]`
83. `worktree-ensure.sh` takes a branch name, fetches the default branch, and creates that new branch with `worktree add --no-track -b`. `[verified: worktree-ensure.sh:1-29]`
84. The harness refuses some Bash command shapes in a worktree-anchored session, and its refusals do not reproduce on demand. `[verified: docs/worktree-bash-guard.md:3-9, :122]` Whether it refuses a command naming a home-rooted path is `[unverified]`.
85. A `claude -p` resume can write a `[Tool call interrupted` user record with `entrypoint` `sdk-cli` and no `promptSource`. `[verified: docs/precompact-hook-behavior.md:235, as the backend review cites]`
86. The repository tracks no item for folding the prompt rules into one classifier. `[verified: grep of the repository for consolidation wording; no match concerns the prompt predicates]`
87. Transcripts age out on a default 30-day clock, which the engineer's `cleanupPeriodDays` setting changes, so an extracted file can outlive its sources. `[verified: docs/cost-ledger.md:5-7, as the ciso review cites; period-cost-report/SKILL.md:18, as the platform review cites]`
88. `restore-session-state-on-compact.sh` runs `compaction-context.py` and fails open, exiting 0 with no output on any error. `[verified: restore-session-state-on-compact.sh:1-23, as the platform review cites]`
89. This plan ships at its projected size as one PR. `[engineer-verified: "Proceed anyway"]` The label answered "This plan projects about 2,090 changed lines (an estimate; threshold 400). Split into smaller PRs now, or proceed?"
90. The missing-directory refusal goes in the helper `pr-cost-export --out` and `routing-guard --out` share, so it changes those two commands as well. `[engineer-verified: "Include it (Recommended)"]` The label answered whether to include that change to the two existing commands, which the Ask does not call for.
91. `claude/.claude/scripts/tests/test_transcript_correction_candidates_counts.py` joins Critical files. `[engineer-verified: "Keep it (Recommended)"]` The label answered whether to keep a third test file that the implementation split out to stay under the repository's per-file line limit.
92. The change ships as one PR at its built size. `[engineer-verified: "One PR as built (Recommended)"]` The label answered how to ship an implementation of about 2,990 changed lines against the 2,090 row 89 covers.
93. The extractor captures the text the engineer types after a slash command. `[engineer-verified: "Capture it (Recommended)"]` In the dispatching session's account, the label answered whether the extractor should capture that text, such as the request after `/plan-it`, which it skipped before.
94. That option's description was the dispatching session's wording, not the engineer's: "the text typed after a slash command is written as one of the engineer's prompts, marked with the command name". The design that implements it was not asked of the engineer: the human-origin test, the `command` field, a command with no args staying skipped, and `initial` computed as for any prompt. `[unverified]`
95. `compaction-context.py`'s `_first_command_args` returns the text between the first `<command-args>` and the first closer after it, or `""`, through `str.find`. It and its two tag constants are read only by that script's `_slash_invocation_quote`, and no test names them. A bare slash invocation carries no `<command-args>` tag. `[verified: grep of claude/ for "_first_command_args|_COMMAND_ARGS_"; docs/precompact-hook-behavior.md:147]`
96. Moving `_first_command_args` and its two tag constants into `render.py` was the dispatched architect's proposal, which rows 48, 69 and 97 do not cover. `[unverified]` Row 119 records the engineer's answer.
97. The move as this plan specifies it is what the engineer approved. `[engineer-verified: "Yes, that's fine (Recommended)"]` In the dispatching session's account, the label answered whether row 69's move is what the engineer approved, given six names: four moved as they are, and two new small wrapper functions for checks written inline before.
98. That option's description was the dispatching session's wording, not the engineer's: "behavior unchanged, all shared by the compaction script and the new command". `[unverified]`
99. The plan maps the approved items to six names. `[unverified]`
    - Row 48's two items are `_has_human_origin`, which comes with its constant `HUMAN_ORIGIN_KIND`, and the interrupt check `_is_interrupt_marker`.
    - Row 69's three are `NO_ORIGIN_PROMPT_MARKERS`, `_has_headless_markers` and `_is_interpretable`.
    - `_has_headless_markers` and `_is_interrupt_marker` are new functions around checks the script wrote inline, not moves.
100. The engineer accepts the earlier refusal's effect on the two existing commands. `[engineer-verified: "Accept (Recommended)"]` In the dispatching session's account, the label answered whether to accept that, with `--out` in a missing directory, a `pr-cost-export` config fault changes from exit 1 to 2 and a `routing-guard compute` NOT RUN from exit 3 to 2. It extends row 90.
101. That option's description was the dispatching session's wording, not the engineer's: "the changelog and docs state the exit-code difference for those two cases". The caller-level tests come from review findings, not the label. `[unverified]`
102. `routing-guard compute` reaches the shared refusal before its NOT RUN exit 3, and `pr-cost-export` before its config-fault exit 1. `[verified: routing_guard.py:1959-1962, :2010-2013, :2042; pr_cost_export.py:173-190, :306, as the backend review cites]`
103. The preview followed by the engineer's explicit confirmation is the guard for the unanchored glob, and no list of approved families is enforced in code. `[engineer-verified: "Confirm first is enough (Recommended)"]` In the dispatching session's account, the label answered whether that guard is enough or a code-enforced approved-families list is needed as well.
104. That option's description was the dispatching session's wording, not the engineer's: "the session stops after the preview and waits for the engineer's explicit OK; an unconfirmed folder writes nothing". `[unverified]`
105. The `--since` and `--until` flags were the dispatching session's proposal, and the engineer was not asked. Their reader is the follow-up skill's window pass-through, from round-1 staff-product-engineer R8. `[unverified]`
106. The count-only `checks`, the computed `failed_relations`, the file check and the raw cross-check were the dispatching session's proposals or review findings it accepted. `[unverified]` Row 121 records the engineer's answer on how many self-checks to keep.
107. `scope._iso_date` validates with `strptime`, which accepts an unpadded month or day. `_parse_absolute_window_args` then returns `None` for that bound with no error. `[verified: scope.py:1121-1127, :1151-1161]` `fromisoformat` rejects such a date, and every zero-padded real date from `0001-01-01` to `9999-12-31` yields a bound. `[verified: as the backend and ciso reviews' Python 3.14 probes show]` `period-cost` refuses a supplied flag whose bound comes back `None`. `[verified: period_cost.py:153-169]`
108. At two or more roots, both scope iterators print `scanning root i/N...` on stderr as they reach each root. `_iter_scoped_sessions` also prints a notice starting `_iter_scoped_sessions:` for a root it cannot list. `[verified: scope.py:408-431, :458-464; docs/transcript-analysis.md:100]`
109. `--this-repo` with a top-level `--config-dir` whose roots hold none of this checkout's project directories exits 1 when `_resolve_project_scope` is called. `[verified: scope.py:592-606]`
110. At one root, `_resolve_project_scope` passes the glob to `corpus.iter_sessions` unchanged, so a nested glob such as `**` can match a subagent file as a session. `[verified: scope.py:611-624; corpus.py:214, as the backend review cites]`
111. `_refuse_unusable_out_path` checks that `--out` does not exist, that its parent resolves to an existing directory, and that the nearest existing ancestor is outside a git work tree. Writability, free space and hard-link support fail only inside `_publish_new_file`. That function links the temp file into place and removes the temp name in a `finally` block, so a kill between the two leaves both names. `[verified: ledger_common.py:110-139, :256-288 in this worktree]`
112. `mkdir -p -m 700` leaves an existing directory's mode unchanged. `[verified: as the platform review observed on this machine]`
113. Under bash, `cat` of a glob matching nothing prints its error on stderr, the pipeline prints `0`, and the call exits 0. `[verified: as the platform review observed with bash 5.3]` Under zsh an unmatched glob aborts the call with an error instead. `[unverified]`
114. Each file's end condition, deletion once the classification pass has consumed it or once the engineer decides no follow-up exists, was the ciso review's proposal, which the dispatching session accepted. The engineer was not asked. `[unverified]`
115. The hook test file's tests skip when `jq` is absent. `[verified: claude/.claude/hooks/tests/conftest.py:41; test_restore_session_state_on_compact.py:108, :141, :212, :308, :448]` CI runs the full suite on every push. `[verified: CLAUDE.md "Commands"]`
116. `test_transcript_pr_cost_export.py` and `test_transcript_routing_guard_compute.py` join Critical files for one caller-level test each, which staff-backend-engineer R3 and staff-sdet R16 require. `[unverified]` Row 120 records the engineer's answer, which a file added after approval needs (plan-it/SKILL.md Step 5, "Critical files"). `test_transcript_routing_guard_compute.py` already runs past the 1,000-line limit, which no check enforces yet. `[verified: line count of that file; docs/design-decisions/code-file-line-limit.md:19, :50-57]`
117. This plan's `docs/transcript-analysis.md` line cites match the main checkout's copy: :3, :37, :40, :51, :53, :55, :57-67, :88, :100, :103 and :1223. `[verified: Read of that copy]` That copy is this branch's merge base. `[unverified]`
118. This plan ships at its projected size as one PR. `[engineer-verified: "Proceed anyway"]` The label answered "This plan projects about 4,000 changed lines (an estimate; threshold 400). Split into smaller PRs now, or proceed?" This revision projects about 3,700, below that figure.
119. The move into `render.py` takes `_first_command_args` and its two tag constants as well. `[engineer-verified: "Move it (Recommended)"]` In the dispatching session's account, the label answered whether to move that slash-command-args reader from `compaction-context.py` into `render.py`. It extends rows 48, 69 and 97.
120. `test_transcript_pr_cost_export.py` and `test_transcript_routing_guard_compute.py` each take one caller-level test and join Critical files. `[engineer-verified: "Add both (Recommended)"]` In the dispatching session's account, the label answered whether to add those two tests.
121. The output's self-checks follow the middle path. `[engineer-verified: "Middle path"]` In the dispatching session's account, the label answered how many of the output's self-checks to keep.
122. That option's description was the dispatching session's wording, not the engineer's: "keep checks that catch empty or misread output after a Claude Code format change; drop the ones that only watch for change." `[unverified]`
123. Which checks the middle path keeps and drops is the dispatching session's mapping, and the eight dropped counters are this plan's reading of it. `[unverified]`
     - Kept: every `counts` entry; the `answers_read`, `answers_keyed` and `labels_matched` relations and the counters they read; `multi_select_entries`; `truncated_fields`; the runbook's zero-count stop, raw cross-check and spot check.
     - Dropped: key-name tracking, with its print rule and the option-key map; the `calls_conserved`, `keys_expected` and `inputs_well_formed` relations; the file check's row count.
     - Dropped as read by no relation, runbook step or Verification step: `prompts_without_origin`, `prompts_without_uuid`, `interrupts_by_text_only`, `duplicates_across_sessions`, `declined_with_text`, `options_dropped`, `with_attribution_skill` and `model_family_unknown`. `[verified: correction_candidates.py:591-660, as staged]`

**Mechanisms:**
- M1: A new module and registrar, called from `cli.py`, with a pure extraction seam. `anchors: row1, row11, row12, row13`. Lighter alternatives fail, per "Alternatives set aside" (`user-input`, `judgment-pair`).
- M2: The shared scope flags with a run lacking an effective scope refused, and one run per `*-<name>*` glob. `anchors: G2, row4, row8, row9, row10, row11, row58, row59, row109, row110`.
- M3: The typed-prompt rule, in stated precedence, with per-file origin state and a slash prompt for a human slash command with args. `anchors: G1, row14, row15, row16, row17, row18, row19, row20, row23, row55, row56, row85, row93, row94, row95`.
- M4: Six atoms in `render.py`, plus `_first_command_args` with its two tag constants. `anchors: row17, row39, row48, row54, row55, row69, row95, row96, row97, row98, row99, row119`. Lighter alternatives fail, per "Alternatives set aside".
- M5: Question pairing by `tool_use_id`, a declined call emitted with its result text, and a bounded label parse. `anchors: row21, row22, row57, row75, row76`.
- M6: Context and record fields, each with a named reader, and identifiers exempt from truncation. `anchors: row24, row61, row66, row87`.
- M7: Dedup on `uuid` or `tool_use_id`, with a deterministic winner and line order. `anchors: row43`.
- M8: Count-only answer-shape checks with named populations, three computed relation failures, and truncation counts, each read by a relation, a runbook step or Verification 3. `anchors: G1, row21, row33, row57, row106, row121, row122, row123`. This is heavier than a one-off probe, and both lighter primitives fail, per "Alternatives set aside".
- M9: A per-record guard. `anchors: row53, row54, row77`.
- M10: ASCII JSON Lines, built in memory and published once through `ledger_common` to a required `--out`, with a missing directory refused before any work in the shared helper. `anchors: row34, row35, row52, row73, row78, row79, row90, row100, row101, row102, row111`. The lighter `open(path, "x")` fails, per "Alternatives set aside".
- M11: `--preview`, reusing the run's session iterator, followed by the engineer's explicit confirmation. `anchors: row71, row72, row81, row82, row103, row104, row108`. Both lighter primitives fail. No existing subcommand lists the families (row 82), and a directory listing would copy the scope logic, per "Alternatives set aside".
- M12: The runbook in the docs. `anchors: G3, row5, row37, row49, row50, row65, row67, row73, row74, row80, row83, row84, row112, row113`.
- M13: The file stays private, and no figure from it is published. `anchors: row32, row33, row62, row87, row114`.
- M14: One `code-writer` dispatch, atom move first. `anchors: row45, row46, row88, row89, row92, row115, row116, row118, row120`.
- M15: A window refused when a supplied bound does not apply, read through the shared helper. `anchors: row105, row107`. The lighter primitive, `scope._iso_date` alone, fails because it passes a value that yields no bound (row 107).

## Critical files

**One `code-writer` dispatch, in two ordered stages.** The module imports the moved atoms, and the architecture doc takes edits from both stages, so a second dispatch would restate the first one's context.
- Stage 1 moves the atoms, `_first_command_args` and its two tag constants included (row 119): `render.py`, `compaction-context.py`, `test_transcript_render.py`, and the architecture doc's `render.py` and "Sibling scripts" edits.
  - It ends with `scripts/venv-run.sh pytest -rs claude/.claude/scripts/tests/test_transcript_render.py claude/.claude/scripts/tests/test_compaction_context_*.py claude/.claude/hooks/tests/test_restore_session_state_on_compact.py` passing with no skip reported for the hook test file, whose tests skip without `jq` (row 115).
  - The hook that runs `compaction-context.py` fails open with no output (row 88), so these tests are the detector this stage runs. CI's full suite runs them again on every push.
- Stage 2 writes every other file below. Verification 1 to 3 check the whole.

The files:
- `claude/.claude/scripts/transcript_analysis/correction_candidates.py` (new). Its docstring follows `judgment_pair.py`'s shape. It defers the typed-prompt definition to `docs/transcript-analysis.md` § "Terms" and the record schema to that doc's `correction-candidates` section. The staged module's self-checks that row 123 drops come out, with `_bounded_key_counts`, its key constants, and the `_Candidate` fields that only fed them. It reuses these:
  - from `scope`: `_add_project_scope_args`, `resolve_scan_roots`, `_resolve_project_scope`, `_parse_absolute_window_args`, `_iso_date`, `_resolved_scope_header`, and `print_resolved_scope`;
  - from `render`: `_content_text`, `_is_fresh_user_prompt`, `_fam`, the six moved or new atoms, `_first_command_args` and `_COMMAND_ARGS_OPENER`;
  - from `user_input`: `_is_fresh_user_prompt_for_narrative` and `_truncate_prompt_text`;
  - from `ledger_common`: `_refuse_unusable_out_path` and `_publish_new_owner_file`;
  - `corpus._parse_ts`, `pricing._SYNTHETIC_MODEL_ID`, `review_rounds._SLASH_COMMAND_RE`, `skill_invocation._normalize_skill_name`, and `redaction._project_family`.
- `claude/.claude/scripts/transcript_analysis/cli.py`: import and call the registrar.
- `claude/.claude/scripts/transcript_analysis/render.py`: the six atoms, and `_first_command_args` with its two tag constants.
- `claude/.claude/scripts/compaction-context.py`: delete the moved definitions, and read `render`'s at :193, :194, :209, :252, :280 and :345, and `render._first_command_args` in `_slash_invocation_quote`.
- `claude/.claude/scripts/transcript_analysis/ledger_common.py`: `_refuse_unusable_out_path` also exits 2 when the resolved parent of `--out` is not an existing directory.
  - Its one stderr line names the operator's literal `--out`, like the other two refusals.
  - The check runs after the existing-path test and before the git check.
  - `pr-cost-export --out` and `routing-guard --out` then refuse a missing directory before their work instead of after it (row 79).
- `claude/.claude/scripts/tests/test_transcript_ledger_common.py`: a missing parent and a parent that is a file each exit 2 with that line and run no git command.
  - Each refusal runs once with a relative `--out` under a changed working directory and once under a symlinked parent, so the literal and resolved paths differ. Its line names the literal `--out` only.
  - The missing directory is still absent afterwards.
- `claude/.claude/scripts/tests/test_transcript_pr_cost_export.py` (row 116): a config-schema fault with `--out` in a missing directory exits 2 with the missing-directory line, not 1, and reads no ledger.
- `claude/.claude/scripts/tests/test_transcript_routing_guard_compute.py` (row 116): a NOT RUN fixture with `--out` in a missing directory exits 2, not 3, and prints no NOT RUN reasons on stdout.
- `claude/.claude/scripts/tests/_correction_candidates_helpers.py` (new). It imports the docs-grounded record builders from `._compaction_context_helpers` knowingly (row 64). It adds:
  - `with_fields(record, **fields)`: a deep copy with top-level keys set, so `uuid` or `timestamp` reaches the six builders that take no overrides, and no test mutates the `HUMAN_ORIGIN` dict those builders share;
  - an assistant-record builder taking a list of content blocks, with `uuid`, `timestamp`, `message.model` and `attributionSkill`, each removable;
  - `ask_user_question_block(questions, *, tool_use_id, raw_input)`, returning one `tool_use` block, so two blocks can share a record and a malformed `input` can be built;
  - an answer-record builder taking `tool_use_id`, `answers`, `annotations`, a raw `toolUseResult` or its absence, and the `tool_result` content;
  - `field_mutations(record)`: walks the record, descending into dict values and list elements by index, and yields each path with a deep copy whose value there is `None`, a string, an int, a list or a dict;
  - an args builder carrying `projects`, `this_repo`, `since`, `until`, `truncate_chars`, `out` and `preview`, like `_skill_helpers._judgment_pair_args`;
  - `stub_git_check(monkeypatch, tracked=False)`: replaces `ledger_common._ledger_path_is_git_tracked`, so allow-path and preview tests never run `git`;
  - a stream recorder that replaces both `sys.stdout` and `sys.stderr` and appends tagged writes to one shared list, so a test asserts order across the two streams.
  - Window fixtures use `Z`-suffixed timestamps, because `corpus._parse_ts` reads a naive one as local time.
  - The shared multi-root test does not import this module, so that test's collection never depends on `compaction-context.py`.
- `claude/.claude/scripts/tests/test_transcript_correction_candidates_extraction.py` (new), table-driven at the seam:
  - Verdicts. Each shape gets its exact verdict with no earlier `origin` in its file and with one, and whether it opens an exchange. The opening is asserted through the next prompt's `exchange`, and through whether an earlier assistant text reaches that prompt's `preceding_assistant_text`. "None" means the record is not prompt-shaped and counts nowhere.

    | Shape | No earlier `origin` | Earlier `origin` | Opens an exchange |
    |---|---|---|---|
    | typed prompt | `typed` | `typed` | yes |
    | pasted prompt | `typed` | `typed` | yes |
    | typed prompt opening with another tag | `typed` | `typed` | yes |
    | skill slash invocation with args | `typed`, a slash prompt | `typed`, a slash prompt | yes |
    | bare skill slash invocation | `slash_command` | `slash_command` | yes |
    | skill slash invocation with args and no `origin` | `slash_command` | `slash_command` | yes |
    | skill slash invocation with an args opener and no closer | `slash_command` | `slash_command` | yes |
    | skill slash invocation whose args are whitespace | `slash_command` | `slash_command` | yes |
    | built-in command | `slash_command` | `slash_command` | yes |
    | hand-built record opening with `<command-args>`, with a human `origin` | `slash_command` | `slash_command` | yes |
    | slash-shaped record with a peer `origin` | `slash_command` | `slash_command` | yes |
    | local-command output | `local_command` | `local_command` | no |
    | local-command output with a human `origin` | `local_command` | `local_command` | no |
    | `!` input | `bash_mode` | `bash_mode` | no |
    | `!` output | `bash_mode` | `bash_mode` | no |
    | interrupt by key | `interrupt` | `interrupt` | no |
    | interrupt by a null-valued key | `interrupt` | `interrupt` | no |
    | interrupt by text alone | `interrupt` | `interrupt` | no |
    | interrupt text with a human `origin` | `interrupt` | `interrupt` | no |
    | headless prompt | `headless` | `headless` | yes |
    | task notification | none | none | no |
    | peer-origin record | `non_human_origin` | `non_human_origin` | yes |
    | plain no-origin prompt | `typed` | `no_origin_after_origin` | yes |
    | no-origin prompt holding `task-notification>` | `notification_text` | `no_origin_after_origin` | yes |
    | list content with `promptId` and a human `origin` | `typed` | `typed` | yes |
    | list content without `promptId` | none | none | no |

  - A slash prompt's line carries its stripped args as `text` and `/` plus its name as `command`.
  - Origin state is per file:
    - in one run, an origin-bearing file then an origin-less one, whose first non-initial prompt is emitted;
    - an origin-bearing record before `--since` makes an in-window no-origin prompt `no_origin_after_origin`;
    - a sidechain or an uninterpretable origin-bearing record before a no-origin prompt leaves that prompt `typed`.
  - `initial`:
    - a main-thread assistant record with no text before the first prompt gives `initial: false`;
    - a sidechain assistant record before it gives `initial: true`.
  - Scripted sessions. Each asserts every candidate's `kind`, `id`, `session_id`, `exchange`, both text fields exactly, `initial`, `after_interrupt`, `model_family`, `model`, `attribution_skill`, `family` and `timestamp`, and a question's `answered`. Each record list holds an uninterpretable record, so `id`'s record index is pinned past one.
    - Session one runs a bare slash command, prompt, assistant text, interrupt, prompt, question and answer, assistant text, and prompt. The bare slash command opens exchange 1 and emits nothing. The first prompt, with no assistant record before it, is emitted with `initial: true` at exchange 2. An interrupt opens none. Sidechain, thinking and tool-only records add no text.
    - Session two runs a slash prompt with args, its skill-load record, assistant text, and a typed prompt. The slash prompt is emitted at exchange 1 with `initial: true`. The typed prompt is emitted with `initial: false`, and its `preceding_assistant_text` is that assistant text.
  - Window, with `Z`-suffixed timestamps:
    - a prompt whose preceding assistant record falls before `--since` is emitted with that text and `initial: false`;
    - 23:59:59.999 on the `--until` day is in;
    - 00:00:00 the next day is out;
    - an undated record counts `undated` under a window, and without one it is emitted with `timestamp: null`;
    - a non-string `timestamp` under a window counts `undated` and raises nothing;
    - a question asked in window and answered after `--until` is emitted with `answered: true`, and its `following_assistant_text` spans the edge;
    - a question asked before `--since` and answered in window counts nowhere;
    - every surviving candidate's `exchange` and `id` are identical with and without `--since`.
  - `model_family` and `model`:
    - a `<synthetic>` record is skipped;
    - no qualifying record gives `unknown` and `null`;
    - a non-string model raises nothing.
  - `attribution_skill`:
    - an absent, `""` or non-string value gives `null`;
    - a path prefix is dropped;
    - `claude:` is kept.
  - Questions, each with its expected flag:
    - a selected label, single-select free text, and a multi-select of labels;
    - a forced backtrack, with labels `Yes` and `Yes, but later`;
    - a label containing `", "`, and extra text;
    - a `null` and a blank answer, and duplicate question text;
    - an answer longer than `--truncate-chars`, whose flag matches the untruncated value;
    - `notes` present, absent, and non-string.
  - Question records:
    - a non-dict `toolUseResult` and a dict without `answers` emit `answered: false`;
    - a declined call's string `tool_result` content and its list of text blocks each reach `result_text`, and a non-string `text` block is skipped without raising;
    - a missing result counts `unanswered_question`;
    - two blocks in one record yield two candidates.
  - Pairing, each line carrying its own answer:
    - an unrelated tool-result record sits between the ask and the answer;
    - a typed prompt sits between them;
    - two blocks in one record are answered in reverse order;
    - a sidechain record holding the matching `tool_use_id` does not pair;
    - a result record before the ask does not pair.
  - `malformed_question`, one row each: no string `id`, a non-dict `input`, a non-list `questions`, an empty `questions`, an entry without a string `question`, and a two-entry call with one bad entry.
  - The label parse runs labels `a` and `a, a` against a 200-element answer ending in an unmatched token, in a daemon thread that records its return value or exception. The join waits `_PARSE_JOIN_TIMEOUT_SECONDS` (5), and the test asserts the result is `True`, so an unbounded parse fails rather than hangs.
  - Truncation:
    - preceding text keeps its tail, and every other cut field, `command` included, its head;
    - `0` keeps everything;
    - `--truncate-chars 5` leaves `id`, `session_id` and `family` whole.
  - Dedup:
    - several uuid-less prompts are all emitted;
    - a `uuid` repeated in one file keeps the first copy;
    - a `uuid` in two sessions keeps the copy whose `session_id` sorts first, whichever session arrives first, and counts `duplicate_prompt`;
    - the output order is pinned.
  - The key set of each kind (prompt, question, question entry, option, scope) equals a pinned set.
  - Text holding `\n`, `\r`, U+2028, U+0085, a lone surrogate and a `{"kind":"scope"}` string serializes to one ASCII line ending in `\n`.
- `claude/.claude/scripts/tests/test_transcript_correction_candidates_counts.py` (new), split from the extraction file at the counts seam to stay under the per-file line limit (row 91):
  - Counters, through `_counts_and_checks` with no files:
    - one fixture gives every `counts` and `checks` counter a distinct non-zero value, `slash_prompts` and `truncated_fields` included, and the test asserts both dicts whole by equality;
    - each losing duplicate carries every emitted-line counter's trigger: an initial slash prompt, an answered question holding a `null` answer, a free-text answer and a multi-select entry, and a cut field, so a counter taken before dedup moves;
    - the fixture holds one out-of-window record of each skip kind and an out-of-window uninterpretable record, and runs once with a window and once without;
    - `result_types` tallies by type, `absent` included;
    - the scope record's `schema_version`, `header`, `since`, `until`, `truncate_chars` and `generated_at` are asserted by value.
  - Relations, through `_failed_relations`:
    - for each relation, a healthy input, a zero-population input, a single-entry input, and an input that fails it alone, each with its expected result;
    - one typed answer over one answered entry fails `labels_matched`;
    - a two-failure input pins sorted order;
    - both scripted sessions' `failed_relations` is `[]`.
  - Conservation under mutation, in one loop test whose failure message names the path and the replacement value:
    - `field_mutations` runs over each prompt, assistant, asking and answer record, once with a window and once without;
    - each mutation runs the whole seam path, `_session_candidates`, `_dedup_and_order`, `_counts_and_checks`, `_scope_record` and `_jsonl_text`, and none raises;
    - the test counts on its own the `AskUserQuestion` blocks in the mutated input's in-window, interpretable, main-thread records, through `render._is_interpretable` and the window bounds, never through the function under test;
    - that count equals `ask_user_question_calls`, which equals `questions` plus the three question skip kinds;
    - a call that leaves through `undated`, `uninterpretable` or a sidechain record is in neither count;
    - a non-dict record or `message` counts `uninterpretable`.
- `claude/.claude/scripts/tests/test_transcript_correction_candidates.py` (new), at the command. Allow-path and preview tests stub the git check to "not a repository" through `stub_git_check`.
  - CLI wiring: `--truncate-chars` defaults to 2000, `--projects` to `None`, `--preview` to false, and `func` to `cmd_correction_candidates`.
  - Allow paths, through the real parser and `main()`:
    - `--this-repo` alone, with `scope._repo_scoped_project_slugs` stubbed, exits 0 and writes the scope record, after `test_transcript_cli.py::test_read_cost_this_repo_runs_to_a_report_through_main`;
    - an explicit `--projects '*'` parses to `"*"` and runs;
    - `--since 0001-01-01` and `--until 9999-12-31` each run, and the scope record names them.
  - Refusals. Each pins its exit code and stderr lines, prints no header, and leaves no file at `--out`. Each case but the `--out`-or-`--preview` one also fires under `--preview` and prints no families line.

    | Case | Exit | Stderr |
    |---|---|---|
    | neither scope flag | 2 | the scope line |
    | `--projects ''` | 2 | the scope line |
    | `--projects=` | 2 | the scope line |
    | neither scope flag nor `--out` | 2 | the scope line only |
    | a negative `--truncate-chars` | 2 | argparse's usage and error |
    | `--since 2026-02-30` | 2 | argparse's usage and error |
    | `--since 2026-5-09` | 2 | the `--since` line |
    | `--until 2026-05-9` | 2 | the `--until` line |
    | both of the last two | 2 | one line naming both flags |
    | neither `--out` nor `--preview` | 2 | the `--out`-or-`--preview` line |
    | an existing `--out`, left unchanged | 2 | the helper's line |
    | an `--out` inside a real repository from `helpers.init_git_repo_with_commit`, with no stub | 2 | the helper's line |
    | an `--out` in a missing directory | 2 | the helper's line |
    | `--this-repo` outside a checkout | 1 | `scope`'s line |
    | `--this-repo` with a `--config-dir` holding none of its directories | 1 | `scope`'s line |
    | `--projects` naming two levels under two roots | 2 | `scope`'s line |

  - Publish failures each exit 2, leave no file at `--out`, and leave stderr holding the header and one line, at one root:
    - a write failure after the scan;
    - a destination that appears mid-scan: the session iterator creates a file at `--out` after yielding its first session, and that file is left unchanged with no `.correction-candidates-*.tmp` beside it.
  - Corpus abort, in-process: `scope._resolve_project_scope` is patched to return an iterator that yields one session and then raises a `ValueError` whose text holds a canary, and in a second case a `RecursionError`.
    - Each run exits 1, stdout is empty, and stderr holds the header and one line naming the exception's type, without the canary.
    - The `--out` directory holds no file and no `.correction-candidates-*.tmp`.
    - Under `--preview` it exits 1 with no families line.
  - Preview:
    - stdout is empty, stderr holds the header and the families line, and no file or directory appears;
    - its families equal the scope record's `families` from a run over the same fixture, run with a `--since` that excludes every record and holding a family whose files have no prompt or question;
    - a preview with a window or `--truncate-chars 5` prints the same families as one without;
    - a zero-session preview warns once.
  - A run:
    - stdout is one line, the path, and the file is `0600`;
    - through the stream recorder, the first stdout write precedes the families line, and the families and counts lines follow the publish call, which the test patches to append to the same list;
    - at one root, stderr holds exactly the header, the families line and the counts line;
    - with `_two_declared_roots`, stderr holds the header, one `scanning root i/2...` line per root, then the families and counts lines, and a session in the second root matched by `--projects '*-name*'` is emitted and its family counted;
    - with cross-session duplicates in the fixture, the emitted line count per kind equals `counts.prompts` and `counts.questions`;
    - `failed_relations` is `[]` for a healthy fixture and for a zero-session run;
    - `--truncate-chars 5` cuts a long prompt's `text`, leaves its `id` whole, and the scope record holds `truncate_chars: 5`;
    - a record at 00:00:00.000Z on the `--since` day is emitted, and one a millisecond earlier is not;
    - `--until` alone counts an undated record as `undated`;
    - a record timestamped `9999-12-31T23:59:59-14:00`, past `datetime`'s range in UTC, emits `timestamp: null` and the run exits 0;
    - non-ASCII prompt text round-trips through `json.loads` of its line, and the file is ASCII.
  - Canaries:
    - a distinct canary sits in every transcript-derived string field: prompt text, slash args, assistant text, model, `attributionSkill`, question, header, option label, option description, answer, notes, and `tool_result` content;
    - canaries also sit in a key of `answers`, a key of `annotations`, an extra question-entry key, an extra option key and an extra `toolUseResult` top-level key;
    - none appears on stdout, on stderr, or in the scope record, on the success path, the preview, and the publish-failure exit 2;
    - a project directory name holding a newline and an ESC byte gives a families line that is one ASCII line.
  - A zero-session run exits 0, prints the warning's exact text once on stderr, and writes only the scope record.
  - The scope record's `generated_at` parses as UTC, and a main and a worktree project directory group under one family.
  - A file that would cross the 1,000-line limit splits at a named seam, and the new file needs the engineer's answer before it joins this list.
- `claude/.claude/scripts/tests/test_transcript_render.py`:
  - `_has_human_origin` for a human origin, another kind, none, and a non-dict;
  - `_has_headless_markers` with all three markers and with one missing;
  - `_is_interrupt_marker` with the key, a null-valued key, and none;
  - `_is_interpretable` for a non-dict, a sidechain record, a non-dict `message`, a non-string text block, and a plain record;
  - `_first_command_args` for args between the tags, two openers, an opener with no closer, and no opener.
- `claude/.claude/scripts/tests/test_transcript_analysis_multi_root_scope.py`: one `_UNCONDITIONAL_HEADER_CASES` row (row 60). It builds an inline namespace like the `buckets` row's, with `projects="*"`, `this_repo=False`, `preview=True` and `out=None`, plus the other flags' defaults. A preview writes nothing, so neither parametrized test changes otherwise.
- `claude/.claude/scripts/tests/test_transcript_cli_bootstrap.py`, after the judgment-pair pair, proving the fresh-interpreter path no in-process test exercises:
  - `--help` lists `--out` and `--preview`;
  - a seeded run under a `--config-dir`, with `--projects '*'` and `--out` under `tmp_path`, exits 0, prints exactly the `--out` path on stdout, and writes a first line that parses as the scope record, then one prompt line and one question line from the seeded session. It runs the real git check.
- `claude/.claude/scripts/tests/test_transcript_package_module_prefixes.py`: the module joins `PRODUCTION_MODULES`, and all three new test files join `TEST_FILES`.
- `docs/transcript-analysis.md`:
  - Add `correction-candidates --out` to "Subcommands that write to disk": it writes the one file it names and never overwrites it, and `--preview` writes nothing.
  - At line 53, state that `correction-candidates` has no default scope and refuses a run without `--this-repo` or a non-empty `--projects`. Its `--this-repo` leaves out removed worktrees and checkouts under another name, so the runbook uses one glob per repo name.
  - Add **typed prompt** to "Terms", the definition's one home. It states how the rule differs from a fresh user prompt and from `compaction-context.py`'s rule, and that a human slash command with args counts as one, written as its args.
  - The `pr-cost-export --out` entry and `routing-guard`'s exit-code table each state that an `--out` in a missing directory is refused before any work, so a config fault that exited 1, or a `compute` NOT RUN that exited 3, exits 2 when `--out` names a missing directory (row 100).
  - Add a `correction-candidates` section after `judgment-pair`, the schema's one home. It holds:
    - purpose, flags, refusals, and every exit code, the window refusal and `--this-repo` with a `--config-dir` matching nothing included;
    - the preview, that its `--out` checks do not cover writability, hard-link support or free space, and that its corpus abort exits 1 with no families line;
    - the stderr lines: the header, `scope`'s `scanning root` and unreadable-root lines at two or more roots, and the command's own prefixed lines;
    - beside the `--projects '*'` allowance, three costs: a run holds every candidate in memory until the one publish, each question line carries its own context so an exchange's cost grows with its questions, and the label parse grows with answer length times the labels' total length;
    - that a `--projects '*'` run's stderr and scope record list every project family of every declared account, which stays in the session;
    - the unanchored glob's over-inclusion, and `--config-dir` for one root;
    - exchanges, the window, and every field with its reader, `command` and the slash prompt included;
    - that a session opened by a slash command with no args has no `initial` line;
    - that only `text` blocks reach the context fields;
    - "Line order", with the cases where adjacency is lost;
    - the scope record's `counts` and `checks`, each with its population, and that the scope record holds no transcript text;
    - "Reading the counts": each relation, its population, what its failure suggests, that a failure over a few entries may be sample size, and that a file with any failed relation is kept and not classified until the engineer explains it;
    - that the multi-select `answer_is_free_text` is verified only on machines where the runbook's spot check passed;
    - dedup, including the consumer's `id` dedup across files, and that copies of one line may disagree on the fields computed from their own file;
    - one hand-written synthetic line per kind, with placeholder family slugs such as `-home-example-src-workflow-gates`, and a header that elides the root count as `<N> roots`;
    - "Running on each machine", the runbook above.
  - The section's privacy note, beside `--out`, states:
    - the file holds raw text, which may include credentials a person pasted or an agent echoed;
    - no skill in this repository reads the file, and reading it in a session copies its text into that session's transcript;
    - the data-file read guard is opt-in and off until armed, so an unarmed machine has no guard (row 62);
    - an armed guard covers the Read tool only, matching `.jsonl` and the other listed extensions and any file over 5 MB, so a hidden `.correction-candidates-<random>.tmp` matches only by size;
    - Grep, Bash and every other route are barred by instruction only, and a Read denial is final;
    - in a session, only the runbook's file check and raw cross-check may open a `.jsonl` file, each printing counts and kind names only, and no other command may;
    - the engineer may run the extraction in their own terminal instead of a session;
    - the file is `0600`, the folder is created `0700` only when absent, the command never sets a folder's mode, and a folder under a cloud-sync or shared mount copies the file whatever its mode;
    - the file outlives the transcripts it came from, and deleting those transcripts does not delete it;
    - the engineer deletes each file once the classification pass has consumed it, or once they decide no follow-up exists (row 114);
    - a killed run's hidden `.correction-candidates-<random>.tmp` goes with it, and deleting the visible file does not delete a hidden name left beside it.
  - It points to `docs/private-project-redaction.md` § "Publishing a tooling measurement", since the subcommand is not a publication instrument.
- `docs/transcript-analysis-architecture.md`:
  - a `` ### `correction_candidates.py` `` entry after `judgment_pair.py`'s, naming the seam functions and what it imports;
  - the `render.py` entry names the moved and new names without naming their readers, so it holds in either split shape;
  - "Sibling scripts" adds them to the names `compaction-context.py` reads.
- `CHANGELOG.md` (row 46):
  - one `### Added` entry for the subcommand;
  - one `### Changed` entry for the earlier missing-directory refusal of `pr-cost-export --out` and `routing-guard --out`, stating that a `pr-cost-export` config fault (exit 1) and a `routing-guard compute` NOT RUN (exit 3) now exit 2 when `--out` names a missing directory (row 100).

Projected diff: about 3,700 changed lines, within the about 4,000 that row 118 covers. That is the staged implementation's about 2,990, plus about 1,025 for the previous revision, less about 300 for the self-checks row 123 drops: module 85, tests 155, docs 60.

## Verification

1. `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py` passes. It prints directory targets, so the check is containment (row 41):
   - `claude/.claude/scripts/tests/`, by the rule for any change under `claude/.claude/scripts/`, which holds every new and edited scripts test file;
   - `claude/.claude/hooks/tests/` and the skills test tree, whole, by the rule for a `docs/` change;
   - the rule table's own rows for `test_restore_session_state_on_compact.py` and `test_nudge_error_mode_analysis.py`, which the hooks tree already contains.

   A missing directory is a rule-table bug to report (row 41), not a reason to widen the run by hand. The run is larger than the files this change edits.
2. `scripts/venv-run.sh ruff check claude/.claude/ claude-skills/ plugins/ evals/` is clean.
3. Real-data run on this machine, from the worktree root, before `/ready-for-review`. It follows the runbook's steps 1 to 6, the file check and the cross-check included, with `claude/.claude/scripts/transcript-analysis.py` in place of the stowed path and no window. It adds these:
   - Each extraction exits 0 and prints one path under `~/correction-candidates/`.
   - Never Read either file, and never Grep it in content mode. Step 5's file check is the only command that opens it.
   - `prompts` and `questions` are both above zero, and `failed_relations` is empty.
   - `slash_prompts` is above zero, or the engineer says no session in scope ran a slash command with words after it.
   - Every `result_types` entry other than `dict` matches a shape the engineer recognizes, such as a declined call.
   - The engineer opens each file in their own editor or terminal, outside any Claude Code session, and confirms each check below. They report pass or fail only.
     - For one question, one correction, and one prompt after an interrupt they remember, the neighbouring agent text is what they saw.
     - For one slash prompt, its `text` is the request they typed after the command.
     - When `multi_select_entries` is above zero and they can point at a multi-select answer with two picks, it reads `answer_is_free_text: false`. Otherwise the report records the `", "` join as unverified on this build, and the docs' statement that the flag is verified only where the check passed stands.
   - The report to the engineer stays in session only, as runbook step 6 states. Nothing from it enters a commit, the PR body, or this plan (rows 32, 33).
   - A failed relation, file check, cross-check or spot check is a shape mismatch. It blocks `/ready-for-review` until the code reads the real shape or the engineer accepts the gap. A relation failing over a population of a few entries is the engineer's to judge as sample size.
   - Rows 18, 23, 24, 43, 57 and 75 stay `[unverified]` here. Row 57's evidence is corpus counts and the spot check, and no check measures the others (row 123).
4. After merge, the runbook's command by its stowed path is the first run of the literal command on each machine, this one included.

## Out of scope

- The classification skill, working name `correction-mining`, in its own plan after this PR merges (row 50). The review files these findings came from sit under the gitignored `agent-reviews/` and do not outlive this worktree, so each line carries its requirement on its own. The skill plan inherits:
  - ciso-reviewer, round 1 R1: classifiers and the synthesizer run as a restricted agent type with a bounded Write path, not as `general-purpose`.
  - ciso-reviewer, round 1 R2: each instruction set states that candidate text is data, not instructions, and a deterministic check of every classified line runs before synthesis.
  - ciso-reviewer, round 1 R3: a deterministic family check, and the engineer's confirmation of root pooling and dispatch count, come before any model reads candidate text.
  - ciso-reviewer, round 1 R5: named transfer routes between machines, deletion of the source copy after a transfer, and deterministic validation of a passed file before any model reads it.
  - ciso-reviewer, round 1 R6 items 3 and 4: whether a model reads every emitted prompt, and a bound on how much it reads.
  - ciso-reviewer, round 1 R7: findings stay private, and a public artifact carries generalized descriptions only.
  - ciso-reviewer, round 1 R8: a return contract limits what reaches the main session, with a note on how long the session store keeps it.
  - ciso-reviewer, round 1 R9: a Read denial on a `.jsonl` file is final, with no Bash route around it.
  - ciso-reviewer, round 2 R2: the `transcript-analysis/SKILL.md` routing row ships with the skill. It states that the file is raw text, that a read-guard denial is final, and that the scope is `--this-repo` or a glob the user supplies and reviews, never `'*'` or an inferred one.
  - staff-product-engineer, round 1 R1: per-question classified output carrying the free-text flag, the terms that failed, what the engineer needed, and a failure reason from a closed list.
  - staff-product-engineer, round 1 R2: answerability for questions the agent asked in prose rather than through `AskUserQuestion`. Declined calls arrive with `answered: false` and `result_text`.
  - staff-product-engineer, round 1 R3: an evidence field separating the engineer's reply from model judgment, and a reader standard closer to the engineer's own.
  - staff-product-engineer, round 1 R4: fields marking a prompt that continues an earlier exchange and whether that exchange falls in the window, and batches that keep a session whole.
  - staff-product-engineer, round 1 R5: a pattern-membership file, with every count computed from it.
  - staff-product-engineer, round 1 R6: a roll-up separating comprehension failures from redirections, and tie-break rules between categories.
  - staff-product-engineer, round 1 R7: a field naming where a failed term came from, and the share of candidates with no `attribution_skill`.
  - staff-product-engineer, round 1 R8: a size preview and the engineer's go-ahead before fan-out, and the window passed through to the command.
  - staff-product-engineer, round 1 R9: the skill's argument typing fails on a bare name or a missing file.
  - staff-product-engineer, round 1 R10: the one-root header check, cross-file dedup on `id`, and a per-file split.
  - staff-product-engineer, round 1 R14: the data-not-instruction rule in both instruction sets.
  - staff-platform-engineer, round 1 R2: coverage checks by `id`, and a new output path for each re-dispatch.
  - staff-platform-engineer, round 1 R4: a stated bound on fan-out and on synthesis input.
  - staff-platform-engineer, round 1 R5: a durable copy of the findings file, and disposal of the raw files once classified.
  - staff-platform-engineer, round 1 R6: a stop on a data-file read-guard denial.
  - staff-sdet, round 1 R10: a deterministic smoke run on a synthetic file with a planted canary.
  - staff-sdet, round 1 R13, second half: the classifier's list of fields to copy, and a test tying the docs' synthetic sample lines to the pinned key sets.
  - staff-backend-engineer, round 1 R5: a stop on a file holding only the scope record, before any classifier is dispatched.
  - staff-backend-engineer, round 1 R11: refusing a pooled file whose `schema_version` the skill does not know.
  - staff-product-engineer, round 3 R1: the skill reads `checks.failed_relations` and holds back a file with any entry, before any model reads it, until the engineer explains the failure.
  - staff-product-engineer, round 3 R3: the multi-select `answer_is_free_text` flag is trusted only for files from machines where the spot check passed.
- The change that revises how the main agent phrases questions and summaries (row 6).
- Changing `render._is_fresh_user_prompt` or `_is_fresh_user_prompt_for_narrative`, or folding the four prompt rules into one classifier ("Predicate debt"; rows 16, 86).
- Moving the unapplied-bound refusal into `scope` for every caller of `_parse_absolute_window_args`, or tightening `scope._iso_date` (row 107).
- Widening the corpus reader's per-line catch to the digit-limit `ValueError` and `RecursionError` (row 53). Every subcommand shares that abort, so the fix changes them all and needs its own change.
- Disclosing unreadable session files in the scope record. The single-root glob branch cannot record scan gaps (row 59).
- A plugin for engineers who do not install this repo (row 2).
- Redacting message text, a `--redact` flag, or making the subcommand a publication instrument. No figure from its files is published (row 32).
- Masking credential-shaped values in the file. A file outlives its transcripts (row 87), so its raw text, credentials included, stays on disk until its end condition (row 114). Whether that retention calls for masking is the engineer's decision, and this plan does not mask.
- Moving files between machines. No transfer route is authorized.
- Subagent transcripts as a candidate source (row 44).
- A repeatable `--projects` or a `--repo-name` flag (row 11).
