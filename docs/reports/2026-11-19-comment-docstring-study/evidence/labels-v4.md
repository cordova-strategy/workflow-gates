# Per-clause labels v4, 31 thin-wrapper docstrings, under the engineer's adopted working rule

v4 is v3 with four relabels (P01c3, P21c3, P26c2, P26c3), each noted in its row's reason cell. labels-v3.md is unchanged and is the ruler for the first measurement. P21c3 was relabelled after that measurement and is recorded as post-hoc.

Legend. Restating = the clause says what the code, tests, or stdlib already show (delete). False-or-unsourced = the clause claims something its subject does not support, or cites no source (narrow or delete). Keep = the clause states a design decision with a reason static analysis cannot find.

Rule applied: a docstring states the non-obvious design decisions behind the function, each naming what was decided and a reason static analysis cannot find (why it is this way, or what outside the repository forces it). Everything else is deleted, even if true and even if it takes several files to find.

Verdict values: KEEP; DELETE; REWRITE (clause survives in changed form); KEEP AS SUBJECT (the clause is DELETE on its own, but a KEEP clause depends on it grammatically, so its words survive as the subject of the kept reason). "silent" in an Opus or Fable column means that labeler's file does not address the clause, so no verdict is attributed to it. Clause text is keyed verbatim from labels-final-draft.md; nothing was missing from it. P30c3 is corrected to OBVIOUS per verify-architect-claims.md (T/test_transcript_analysis_branch_attribution.py:398-402). Opus and Fable are abbreviated Op and Fa.

| id | clause | draft | Op | Fa | NEW | angle | CONTESTED | reason |
|---|---|---|---|---|---|---|---|---|
| P01 | "Return the path declared_roots_matching() reads" | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: caller/callee relation found by grep. |
| P01 | "TRANSCRIPT_CONFIG_DIRS_FILE if set, else ~/.claude/transcript-config-dirs" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: the body and direct tests show it. |
| P01 | "(a test seam mirroring cleanup-merged-branches.sh's CLEANUP_MERGED_BRANCHES_ROOTS_FILE)" | NON-OBVIOUS | SPLIT: keep "a test seam", drop mirroring | silent | DELETE | Restating |  | Trim to "a test seam" (intent that the variable exists for tests); the mirrored sibling is a grep-findable other-file fact. v4: DELETE. The same words ("a test seam mirroring cleanup-merged-branches.sh's") already stand at _config_dir.py:91, so the clause repeats a second site. The v3 ground, "no reason stated", is not used because it would also delete P10c3, whose testability reason has the same shape. |
| P01 | "Unlike TRANSCRIPT_CONFIG_DIRS_LABEL, this DOES follow the seam." | NON-OBVIOUS | DELETE | silent | DELETE | Restating |  | Sibling constant and the body show the contrast; Fable did not address it. |
| P02 | "Return the config dirs listed in ~/.claude/transcript-config-dirs" | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: callee behavior, _config_dir.py. |
| P02 | "(or TRANSCRIPT_CONFIG_DIRS_FILE)" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: tests assert it directly. |
| P02 | "that contain a `projects/` subdirectory" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: lambda in the statement. |
| P02 | "See declared_roots_matching() for the parsing contract this builds on." | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: names a visible callee. |
| P03 | "Remove fenced code blocks and inline code spans" | OBVIOUS | DELETE | DELETE | KEEP AS SUBJECT | Restating |  | Subject of the kept clause below ("the natural way..." describes these spans); words survive as its subject. |
| P03 | "the natural way a draft would quote a literal string it's citing rather than proposing as a real next step" | NON-OBVIOUS | KEEP | KEEP | KEEP | Keep |  | Both agree: why spans are stripped; reason also in a plan, which the engineer ruled is fine. |
| P03 | "so a placeholder or anchor-shape scan does not fire on it" | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: caller purpose, found at the call sites. |
| P04 | "The record's text with NUL removed" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: the statement. |
| P04 | "so the closer and emptiness checks judge the text the block emits" | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree and matches the architect hint: caller fact. |
| P05 | "`uninstall` removes the install record right after the state directory" | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: caller code at the call site. |
| P05 | "so a re-run cannot retry the removal" | NON-OBVIOUS | DELETE | KEEP | DELETE | Restating | CONTESTED | Readings: (A, Fable) a consequence of an ordering the author chose, so a decision; (B, Opus and architect hint) derivable from the missing-record branch, a caller fact. Chose B. |
| P06 | "True when `mapping` holds a key outside `known`" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: the statement. |
| P06 | "or a known key of another type" | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: callee type check; the engineer agreed it is obvious from code. |
| P06 | "A null value counts as absent." | FALSE-PARTIAL | DELETE | DELETE | DELETE | False-or-unsourced |  | Both agree: false as written; the narrowed form restates the statement, so nothing is left. |
| P07 | "True when any entry in `entries` carries indeterminate liveness under `source_name` in `liveness`" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: statement and direct test. |
| P07 | "used to withhold Confirmed-clean-exit promotion when a same-session sibling from the other evidence source hasn't resolved" | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: caller purpose. |
| P08 | "Declared roots from ~/.claude/transcript-config-dirs" | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: callee behavior. |
| P08 | "(or TRANSCRIPT_CONFIG_DIRS_FILE)" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: tests assert it. |
| P08 | "validated against this script's own looser sessions/-or-projects/ check" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: lambda in the statement. |
| P08 | "(main()'s --config-dir validation, below)" | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: sibling/other-site fact found by grep. |
| P08 | "instead of declared_transcript_roots()'s projects/-only requirement" | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: names the alternative, not a reason; the requirement is at _config_dir.py. |
| P08 | "the latter would silently drop a sessions-only root" | FALSE-PARTIAL | DELETE | DELETE | KEEP AS SUBJECT | False-or-unsourced |  | "Silently" is false (callee warns by index), so narrow to "a sessions-only root"; that noun phrase is the subject of the kept crashed-fresh-account reason below. |
| P08 | "the crashed-fresh-account case this tool exists for" | NON-OBVIOUS | KEEP | KEEP | KEEP | Keep |  | Both agree: purpose and reason not in code; also stated in a plan and a test docstring, which does not delete it. |
| P09 | "Every ledger file directly under ledger_dir" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: `glob("*.jsonl")`. |
| P09 | "sorted by filename for a deterministic read order" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: `sorted` names the reason. |
| P09 | "[] when the directory does not exist" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: direct test. |
| P09 | "This is the index's only directory listing, so a test can stand in for a file that vanishes between the listing and the read." | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree and engineer ruling: "only directory listing" is a grep-checkable invariant; the monkeypatch sites show the seam. |
| P10 | "CLI entry point for the cost-trend subcommand" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: name and Namespace parameter. |
| P10 | "Reads the wall-clock date exactly once, here, then delegates to _cost_trend_report, which takes `today` as an explicit parameter" | OBVIOUS | DELETE | DELETE | KEEP AS SUBJECT | Restating |  | The kept reason below ("the same split... so the label doesn't depend on a live clock read") is about this split; words survive as its subject. |
| P10 | "the same split _cost_report uses so the \"(partial)\" label doesn't depend on a live clock read inside a function under test" | NON-OBVIOUS | SPLIT: drop sibling half, keep rationale | KEEP | REWRITE | Restating | CONTESTED | Readings: (A, Fable) keep whole, reason not duplicated anywhere; (B, Opus) the "same split _cost_report uses" half is a grep-findable sibling fact. Chose B: keep the testability reason, drop the sibling half. |
| P11 | "The unavailable kind for a non-empty _gh_pr_list status." | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: caller fact. |
| P11 | "A status this table does not know is reported as an unexpected payload" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: `.get` default and a direct test. |
| P11 | "rather than aborting the run" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: names the alternative, not a reason. |
| P12 | "Collapse every whitespace run (U+2028 and U+2029 included) to one space" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: direct test id. |
| P12 | "then delete Cc and Cf characters" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: callee name and test. |
| P12 | "The collapse runs first because \n, \t, and U+0085 are themselves Cc: stripping first would join the words around them." | NON-OBVIOUS | KEEP | KEEP | KEEP | Keep |  | Both agree: ordering reason not visible in code; also in a plan, which is fine. |
| P12 | "A deleted non-whitespace character can leave a doubled, leading" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: pinned by test assertions. |
| P12 | "or trailing space" | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: derivable runtime behavior. |
| P12 | "so the result is not idempotent" | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: a consequence derivable from the body. |
| P13 | "The synthetic report `--sample` prints" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: constants and tests. |
| P13 | "and the docs show" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: a test compares it to the docs block. |
| P13 | "it reads no transcript and runs no subprocess" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: a test asserts it. |
| P14 | "Integer micro-dollars" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: `-> int`, `scaleb(6)`, test. |
| P14 | "the ledger's own six-decimal rendering of `dollars` denotes" | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: other-file fact at pr_cost_ledger.py. |
| P15 | "The one" | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree and engineer ruling: sole-`json.dumps` invariant is grep-checkable. |
| P15 | "canonical encoding of a decoded JSON-cell value" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: `sort_keys`, separators, parameter type. |
| P15 | "(model_breakdown or review_rounds)" | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: decoder keys in the ledger module. |
| P16 | "See docs/transcript-analysis.md's `read-cost` section for the flags, the unit, and the publication scope." | NON-OBVIOUS | KEEP | KEEP | KEEP | Keep |  | Both agree and engineer ruling: pointers are kept. |
| P17 | "Collapse a project label or a raw project-dir slug to its base-repo \"family\" key." | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: name and substitution. |
| P17 | "Strips the `--claude-worktrees-<branch>` suffix" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: direct test. |
| P17 | "that a linked worktree's project-dir slug already carries (see `_WORKTREE_SUFFIX_RE` above)" | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: module comment states it. |
| P17 | "`_derive_proj_label`'s output preserves that suffix unchanged, so the same match applies to either input shape." | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: sibling function, found by tracing. |
| P17 | "A project literally named with that substring would falsely merge into another family" | NON-OBVIOUS | DELETE | DELETE | KEEP AS SUBJECT | Restating |  | Both delete on its own (a test pins it), but it is the subject of the kept "accepted risk" clause; rewrite must still name the suffix ("that substring" has its antecedent in the deleted Strips clause). |
| P17 | "an accepted risk at current scale" | NON-OBVIOUS | KEEP | KEEP | KEEP | Keep |  | Both agree: recorded decision; also in a plan and a test docstring, which is fine. |
| P17 | "If cost --by-project, buckets' Proj count, or user-input's Scope project count ever shows an unexpected merge, re-evaluate." | NON-OBVIOUS | KEEP | DELETE | REWRITE | Keep |  | Flipped KEEP to REWRITE 2026-11-20 (engineer approved Fable's flip): the three consumers at redaction.py:42-44 are complete and grep-findable (cost.py:906, buckets.py:49, user_input.py:164), so the rule deletes the enumeration and keeps only the revisit trigger. A finding must suggest the trigger without the list. |
| P18 | "Apply a run-scoped session-id redact map" | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: caller builds the map. |
| P18 | "fails closed to a fixed token on a miss" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: statement and test. |
| P19 | "value/total as a percentage string" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: name and `-> str`. |
| P19 | "0.0% (not an undefined dash) when total is zero" | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: callee behavior at render.py. |
| P20 | "Strip ASCII control characters" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: direct test. |
| P20 | "from a --deny-summary table cell value" | FALSE-PARTIAL | DELETE | DELETE | DELETE | False-or-unsourced |  | Both agree and engineer ruling: callers are discoverable; the narrowed form restates the name. |
| P21 | "Elementwise-sum a list of _PooledBranchTotals into one pooled total" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: signature and direct test. |
| P21 | "reused identically for the true sample (point estimate) and for every bootstrap resample's own draw" | NON-OBVIOUS | DELETE | DELETE | KEEP AS SUBJECT | Restating |  | Both delete on its own (caller fact), but it is the subject of the kept "computed the same way" reason. |
| P21 | "so every reported statistic is computed the same way regardless of which list it was handed" | NON-OBVIOUS | KEEP | KEEP | REWRITE | Restating | CONTESTED | Both keep; architect hint (not engineer) says rewrite to its statistical reason, and the current wording is vague. Followed the hint. v4: CONTESTED. Decided after the first measurement saw both arms delete this clause in all 3 runs, so the label moved after the outcome was known; it is excluded from pass/fail to avoid a fitted figure. |
| P22 | "compute_review_round_costs, routed through _pooled_filtered_stderr_call." | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: the statement. |
| P22 | "--pooled must never print the resolved root count" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree and engineer ruling: an invariant a test already catches. |
| P22 | "(see _pooled_resolved_scope_header)" | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating | CONTESTED | Readings: (A) engineer kept P16 as a pointer, so keep; (B, Opus and Fable) it dangles once the test-caught invariant it explains is deleted. Chose B; the engineer's ruling names only P16. |
| P23 | "ASCII-only" | OBVIOUS | DELETE | DELETE | KEEP AS SUBJECT | Restating |  | Test-asserted on its own, but it is the subject of the kept locale reason below. |
| P23 | "so the text encodes the same under any locale" | NON-OBVIOUS | KEEP | KEEP | KEEP | Keep |  | Both agree: external reason (locale); also in a plan, which is fine. |
| P24 | "`logged_at` is floored" | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: whole-second pattern and writer hook are in the repo. |
| P24 | "so a row follows an event only past the event's whole second" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: the comparison is the reason. |
| P25 | "Map an absolute path to Claude Code's project-directory slug." | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: name. |
| P25 | "Claude Code names each project dir under ~/.claude/projects/ by taking the session's cwd and replacing every '/' and '.' with '-'." | FALSE-PARTIAL | KEEP (narrowed) | KEEP (narrowed) | REWRITE | False-or-unsourced |  | Engineer ruling: ends in a rewrite; Claude Code replaces every non-alphanumeric character and truncates long slugs, an outside-the-repo fact no repo file states, so qualify it as outside the repo. |
| P25 | "Verified against real dirs: /home/<user>/repo -> -home-<user>-repo; /home/<user>/repo/.claude/worktrees/b -> -home-<user>-repo--claude-worktrees-b." | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: a test asserts both mappings. |
| P26 | "Same exception type" | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: stdlib errno-to-subclass behavior. |
| P26 | "with any embedded absolute path removed from the message" | OBVIOUS | DELETE | DELETE | KEEP AS SUBJECT | Restating |  | Both agree: name and statement. v4: KEEP AS SUBJECT, paired with P26c4. DELETE on its own, but the kept sentence about the path depends on it as its subject. |
| P26 | "Mirrors _iter_scoped_sessions' own root-level diagnostic, which uses `exc.strerror or 'permission denied'` rather than `str(exc)`." | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating | CONTESTED | Both agree: sibling fact at scope.py. v4: CONTESTED. A sibling-function pointer, contested on the same question as P22c3 and P29c4. |
| P26 | "`str(exc)` can embed the offending path." | NON-OBVIOUS | DELETE | DELETE | REWRITE | Restating |  | Engineer ruling: P26 ends in a rewrite stating the function's own design choice (keep the engagement path out of the message). Both labelers deleted every P26 clause; hosting the rewrite in this clause, the only one about why the function exists, is my placement. |
| P26 | "`OSError(errno, strerror)` reconstructs the correct subclass (e.g. `PermissionError`) from `errno`." | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: stdlib behavior. |
| P26 | "A caller matching on subclass still sees the same type." | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: restates the first clause. |
| P27 | "Print the one-line resolved-scope header" | OBVIOUS | DELETE | DELETE | KEEP AS SUBJECT | Restating |  | Name and statement on its own, but it is the subject of the kept "never scope-ambiguous" reason. |
| P27 | "cmd_skill_invocation already uses" | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: caller fact, incomplete (engineer ruling: scored Restating). |
| P27 | "so machine-wide vs. --this-repo output is never scope-ambiguous" | NON-OBVIOUS | KEEP | KEEP | KEEP | Keep |  | Both agree: the reason for the header; also in test prose, which is a minor point. |
| P27 | "`file` defaults to stdout" | OBVIOUS | DELETE | DELETE | KEEP AS SUBJECT | Restating |  | `file or sys.stdout` on its own, but it is the subject of the kept call-time-resolution reason. |
| P27 | "(resolved at call time, not import time — a `sys.stdout` default value would bind the stream object process startup captured, bypassing test capture and any later reassignment)" | NON-OBVIOUS | KEEP | KEEP | KEEP | Keep |  | Both agree: reason for the None idiom, not duplicated. |
| P27 | "audit-routing-samples routes it to stderr instead" | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree and engineer ruling: incomplete caller list (other callers use stderr), scored Restating. |
| P27 | "since its stdout is a JSON (or curation-markdown) data stream a header line would corrupt" | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: the caller's own rationale, in the caller's comment. |
| P28 | "A subcommand calling this must also be in _SUBCOMMANDS_REFUSING_TOP_LEVEL_CONFIG_DIR." | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree and engineer ruling: an invariant a test already catches. |
| P29 | "Resolve one record's branch for --branches filtering" | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree and engineer ruling: too narrow (other consumers exist), scored Restating. |
| P29 | "the timeline step (_timeline_entry) followed by the pre-branch step (_attribute_pre_branch)" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: the statement. |
| P29 | "Returns None for a main-thread record with no gitBranch, and for a sidechain record in a session with no branch-bearing main-thread record" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: tests assert both. |
| P29 | "the \"?\" sentinel (see cmd_review_trace's docstring for the carry-forward convention this parallels)" | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating | CONTESTED | Readings: (A) engineer kept the P16 pointer, so keep; (B, Opus and Fable) the sentinel is a caller convention and a pointer between docstrings. Chose B: the sentinel is visible in the code and the pointer states no reason. |
| P30 | "Apply only the pre-branch step to a branch a positional consumer carried forward from the main thread" | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: statement plus a caller fact. |
| P30 | "using the record's own timestamp" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: `_parse_ts(rec.get("timestamp"))`. |
| P30 | "so a record with none is never remapped" | NON-OBVIOUS (draft wrong) | DELETE | DELETE | DELETE | Restating |  | Corrected to OBVIOUS: test_record_without_a_timestamp_is_never_remapped (test_transcript_analysis_branch_attribution.py:398-402) calls the function by name and asserts it. Both labelers also delete. |
| P31 | "Return True iff any segment of `command` invokes a mutating git subcommand (see _command_segment_is_mutating_git)" | OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: statement and direct tests. |
| P31 | "&&/;/\|/\|\|-chained" | NON-OBVIOUS | DELETE | DELETE | DELETE | Restating |  | Both agree: callee behavior at corpus.py. |

## Totals (counted from the 101 rows above)

- Rows: 101.
- KEEP: 8.
- REWRITE: 5 (P10c3, P17c7, P21c3, P25c2, P26c4). P10c3 and P21c3 are also CONTESTED; P25c2 is scored alone as an external-fact row.
- KEEP AS SUBJECT: 9 (P03c1, P08c6, P10c2, P17c5, P21c2, P23c1, P26c2, P27c1, P27c4).
- DELETE: 79.
- Check: 101 = 101.
- CONTESTED: 6 (P05c2, P10c3, P21c3, P22c3, P26c3, P29c4).
