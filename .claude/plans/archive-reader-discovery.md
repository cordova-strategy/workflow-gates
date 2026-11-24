# Read archived review data in the analysis tools

## Context

Goal: make the data that `agent_branch_records` archives (review-ledger copies now, `agent-reviews/` snapshots now, transcripts once the transcript archive lands) readable by the analysis tools, so a past branch's rounds, costs and dispositions can still be analyzed after the live files are swept or removed.

Ask: "you need to make sure that anything that the agent branch archive (I forget what it's called) config key on archives (I think it touches ledgers, agent reviews, and trasncripts soon) is made known to agents when agents would look for those types of files in their normal location, for the purposes of analysis. I think that's more complicated than it seems." Later, on the archive's purpose: "the reason we don't delete is because the archive files are useful for analysis" and "It's needed for analysis after the fact." On scope: "readers should read the archive after the key's turned off", "archive routes should be on by default", "smaller PRs are better", and "I don't really care so much about restoring agent reviews automatically". Selected labels: "Small resolver PR first, then ledger reader (Recommended)" for sequencing, "Include it" for a read-only viewer of archived ledger rows, and "Generic contract, defer transcript reader (Recommended)" for transcripts.

Today nothing reads the archive. The retention sweep deletes a ledger file after 30 idle days, and `review-ledger.sh show` then prints "no ledger for this branch" with `max_round=0`. The archive added by the earlier ledger-archiving change keeps a copy, but its plan put reading copies back out of scope. Agents cannot be relied on to look in the archive themselves, so the analysis tools must read it as part of their normal corpus.

Evidence behind the design, from this session's exploration and two independent design reviews:

- Only two analysis commands read ledger rows: `author-outcome` and `reviewer-reads`. Every other analysis the engineer named (round duration, cost, round counts, trace) is a transcript command.
- No analysis reads `agent-reviews/`: findings and disposition records are written with the `Write` tool and are read from transcripts. Archiving it is relocation, and retiring that snapshot is a separate later change.
- A live-tool fallback in `show` or `render` would change round numbers and decision counts per account, undo a Reset, and could publish archived verbatim quotes. The live tools stay live-only.
- Each reader looks in one ledger directory only, and `author_outcome.py` parses everything after a file name's first dot as the session id, so a copy named with a timestamp suffix would be keyed wrongly.
- Ledger copies are segments: a stem's copies are concatenated in stamp order, skipping a copy that is a byte prefix of the next, and a kept source can coexist with its copy.
- `reviewer-reads` is a single-account publication instrument, so any archive lookup must be per account and never a glob of the archive root.
- A separate session is planning the transcript archive in four PRs (writer, readers' slug rule, readers scan `<account dir>/projects/`, verified-original deletion). Its PR 3 is not yet designed. It edits most sections of `docs/agent-branch-records.md`, so this work adds only a new section after "Ledger copies".

Sequencing the engineer selected: a small first PR adds a Python config-dir to archive-account-directory resolver with a parity test against the bash encoding. A second PR adds the ledger-copy reader for the two commands, plus a read-only viewer of archived ledger rows.

## Approach

`author-outcome` and `reviewer-reads`, the only analysis commands that read review-ledger rows (row 12), read the archived ledger copies of every account they scan. They always do, whatever `agent_branch_records` says, and no flag turns that off (rows 3, 42). Each stem's copies and live file are read as one history before anything is counted, and a counts-only line reports what the archive contributed. A read-only viewer prints one stem's history the way `show` prints a live branch's (row 54). Five PRs deliver it, in this order (M15):

- **A.** A Python archive resolver, pinned to the bash writer by a parity test.
- **B.** The one-stem history reader, as a library no command calls yet.
- **C.** A read-only viewer, `transcript-analysis.py review-ledger-history <stem>`, the reader's first caller.
- **D.** The reader in `author-outcome`.
- **E.** The reader in `reviewer-reads`, which also finds this repo's removed worktrees through snapshot manifests.

**PR A: the resolver.** A new `claude/.claude/scripts/_branch_records.py` locates archive directories the way `branch_records_status` computes them (row 22). It never reads `claude-config.toml` (row 1).
- `encode_component(path)` replaces `%` with `%25`, then `/` with `%2F`.
- `archive_root(home)` returns `<home>/.local/state/agent-branch-records`, or None unless `home` is a non-empty absolute path (M18).
- `account_directory(config_dir, home)` returns None for a relative `config_dir` (M18). Otherwise it canonicalizes `config_dir` with `os.path.realpath(config_dir, strict=True)` and requires a directory. It returns `archive_root(home) / encode_component(<canonical path>)`, or None when any step fails.
- `archive_subtree(config_dir, name, home)` returns `ArchiveSubtree(state, directory)` for a subtree named by one path component. `directory` is set only for `present`. It raises ValueError for a name that is empty, `.` or `..`, or that holds `/` or NUL. It takes the first state that applies, in this order, so it never reads a subtree under an unmarked root (M18):
  1. `unresolvable`: `account_directory` returned None.
  2. `unmarked`: a stat of the root's readiness marker finds nothing, or finds something other than a regular file. The stat follows a link, as the writer's `test -f` does (row 59). Finding nothing includes the not-a-directory error that a root that is a file gives, and a dangling root link gives the same result. The archive was never set up, or its volume is not mounted.
  3. `unreadable`: a stat of the marker or the subtree failed in any other way, such as a permission error on the root or the account directory. The subtree is also `unreadable` when it is not a directory, or when its real path does not lie under the account directory's real path. The account directory itself is `unreadable` when it is a link, because a link there could name a sibling account's directory. It is also `unreadable` when it exists as anything but a directory, so the not-a-directory error a file there gives never reads as `absent`.
  4. `absent`: the subtree does not exist.
  5. `present`: none of the above.

Every function takes `home` from its caller, and none writes, lists or globs the archive root. The root path and the sentinel name repeat the lib's values, a small duplicated value that the parity test pins. The sibling session's transcript readers can call `archive_subtree(config_dir, "projects", home)`, the generic contract row 9 names.

**PR B: the history of one stem.** A new `claude/.claude/scripts/transcript_analysis/review_ledger_copies.py` owns it:
- `REVIEW_LEDGER_DIRNAME` and `SESSION_ID_PATTERN` move here from `author_outcome.py`, which keeps `_REVIEW_LEDGER_DIRNAME` and `_SESSION_ID_PATTERN` as aliases for its existing readers. The archive's subtree has the same name (`_branch-records-lib.sh:418`). `event_time_sort_key` moves here from `author_outcome._event_time_sort_key`, whose one call site then calls it here, because PR C's viewer sorts by it (row 60). The aliases make `author_outcome` reach `_branch_records` from this PR on, so PR B carries M22's `select-tests.py` rows.
- `group_ledger_files(live_files, copy_files)` returns one `LedgerFile(name, copies, live)` per stem, sorted by `name`, plus a count of skipped copy names.
  - `name` is `<stem>.jsonl`, `copies` holds the stem's copies in stamp order, and `live` is its live file or None.
  - Every live file is the live member of its own stem, whatever its name holds.
  - A copy's stem is its name without `.jsonl` and without a final `.<YYYYmmddTHHMMSSZ>`. A copy name with no such stamp, or whose stem does not hold exactly one `.`, is skipped (row 15).
  - Readers key on `name`, so `author_outcome`'s first-dot session parse reads the session slot, never `<session>.<stamp>` (row 16).
- `read_ledger_file(ledger_file, read_member)` reads the copies in stamp order and the live file last. Each goes through `read_member`, the caller's own one-file reader, which returns `(rows, opened)`. A copy that `lstat` does not show as a regular file counts as not opened, and `read_member` never sees it. A member whose `read_member` raises `ValueError` or `RecursionError` counts as not opened too, as `ledger_dispositions._read_file_rows` treats one, so no member's content aborts a run (row 27).
  1. A copy whose rows are a leading run of the next opened member's rows is skipped. This is the row form of the byte-prefix rule in `docs/agent-branch-records.md` § "Ledger copies" (row 35), and it removes every overlap the writer makes, id-bearing or not (rows 18, 45). An empty copy with an opened member after it is skipped too.
  2. The kept members' rows are concatenated in that order. A row repeated outside a leading run is kept, and only a member changed by hand or by another writer gives one (row 45).
  3. The result carries each kept row with its member's copy stamp, None for the live file, in history order, so the copies' rows lead. It also carries whether any member opened, the members that did not open, and the skip count.
- Every stem goes through `read_ledger_file`, a live-only one included, whether or not a caller passes an archive. A one-member history is that member's rows unchanged, so the existing reader tests cover the new path (M21). The one difference is that a live file whose reader raises now counts as not opened instead of aborting `author-outcome`.
  - That live member prints nothing on stderr, because `author_outcome`'s reader prints only for an `OSError` (`author_outcome.py:290-294`). PR D's index then re-reads it on every refresh, as it retries any live member that did not open.
  - The doc states both, and no count shows them. A count would need the shared reader to report why each member failed, so the index could tell this deterministic failure from the transient `OSError` its retry exists for. That would widen the shared reader's result for one failure kind of one command.
- Every read lists the live files before the copies, so a file the sweep copies and removes between the two listings is still found as its copy. Its live member then counts as not opened.
- `LedgerArchive(home=None)` holds one run's lookups.
  - `home` defaults to a one-line `_archive_home()` that returns `os.environ.get("HOME", "")`. An unset HOME thus reads as empty, as the writer's `${HOME:-}` reads it, and gives `unresolvable` (row 22). A test passes `home` to build a `present` or `absent` archive, and PR C's conftest pin covers every command test from then on (M7).
  - It resolves each config-dir root's `review-narrative-ledger` subtree once, through `archive_subtree`.
  - It lists a `present` subtree's `.jsonl` entries with `scope._list_dir_recording_gaps`, because `Path.glob` returns nothing for a directory it cannot list (row 49). A failed listing turns that root's state into `unreadable`.
  - It keeps each root's state and each stem's latest copy counts, so a stem read again mid-run counts once.
  - Each reading command builds one with `LedgerArchive()` per run. No flag skips it, and a library caller that passes no archive reads live files alone.

**PR C: the viewer.** A new `claude/.claude/scripts/transcript_analysis/review_ledger_history.py` registers `review-ledger-history STEM`, handled by `cmd_review_ledger_history` in the same module (row 30). It prints a stem's whole history as `show` prints a live branch's rows (rows 29, 54, M12):
- STEM must `fullmatch` `[0-9a-f]{64}\.[A-Za-z0-9_-]+`. Otherwise the command exits 2 before it builds a `LedgerArchive` or reads anything, so no argument reaches outside the two directories.
- It reads `<config-dir>/review-narrative-ledger/STEM.jsonl` and the account's copies of STEM as one `LedgerFile`. `<config-dir>` is `scope.PROJECTS_DIR.parent`, which follows the top-level `--config-dir`.
- Each member goes through a new `ledger_dispositions._read_member`, which returns `(rows or [], rows is not None)` from `_read_file_rows`. PR E reuses it.
- It takes the copies from `group_ledger_files` over the archive subtree's listing. A copy belongs to STEM only when its parsed stem equals STEM exactly, never by prefix or glob.
- Before it reads, it exits 2 when the live path or any copy of STEM exists as a symlink or as anything but a regular file, as `show`'s check at `review-ledger.sh:857` does (rows 29, 64). Its stderr line names the path and says to report it and not remove it, as `show`'s refusal does.
- It is repo-unscoped on purpose. The operator names a stem, and the command lists nothing. The branches it serves often have no worktree left, which a scope from `git worktree list` would exclude (M11).
- stdout carries every row, one per line, as `json.dumps({**row, "source_copy_stamp": stamp}, ensure_ascii=True)`.
  - Rows are stable-sorted by `event_time` over history order, as `show` sorts them (rows 29, 64). The key is `event_time_sort_key`, which sorts a non-string value as an empty string. jq's `// ""` maps only null and false to an empty string, so the two orders can differ for any other non-string `event_time`. The writer never stores one.
  - Every stored field prints, as in `show`.
  - `source_copy_stamp` is the row's copy stamp, or null for a live row. It is a display-time field, as `show`'s `source_repo_hash` is, and it replaces a stored key of that name, as `show`'s tag does.
  - It prints no `source_repo_hash`, because every row of one stem carries the same one and STEM already names it (row 65).
  - `ensure_ascii` escapes every character outside printable ASCII, control and format characters included, which `show`'s `clean` replaces (row 29).
  - No flag, cap or paging changes what prints.
- stderr carries `scope._DO_NOT_PUBLISH_BANNER`, then one header line: `review-ledger-history: archive=<state> live=<present|absent> copies=<N> unread=<N> rows=<N> leading_copies_skipped=<N>`.
- Its exit status follows `show`'s (M20):
  - 2 for a STEM that fails the grammar, or a member path that is not a regular file;
  - 1 when a member did not read;
  - 0 otherwise, whatever the archive state, including a stem with no files.
- Its `--help` and its doc section say three things:
  - it prints verbatim text for any repo or account it is pointed at;
  - archived rows are past records, not live decisions or approvals;
  - `rows=0` under `unmarked`, `unreadable` or `unresolvable` is not evidence of an empty history.
- It keeps no round state, has no `--out`, and writes nothing.

PR C also pins `_archive_home` in the scripts conftest (M7), because the viewer is the first command that builds `LedgerArchive()` with no home.

**PR D: `author-outcome`.**
- `ledger_file_signature(ledger_file)` in `review_ledger_copies` is each member's `(mtime_ns, size)`, or None when a stat fails. It replaces `author_outcome._file_signature`.
- `archive_summary_line(archive, *, scope_label)` in `review_ledger_copies` builds the line under "What the commands print". PR E adds its `past_worktrees` parameter.
- `LedgerIndex(ledger_dir, archive, *, list_live, read_member)` is `author_outcome._LedgerIndex` moved into `review_ledger_copies` with the helpers only it uses: `_ledger_file_session_component` and `_row_session_id` (row 60, M14).
- In `claude/.claude/scripts/transcript_analysis/author_outcome.py`, `_LedgerIndex(ledger_dir, archive=None)` becomes a subclass of `review_ledger_copies.LedgerIndex`. It passes `_list_ledger_files` and `_read_ledger_rows_from_file` through lambdas that look each name up at call time, so the tests that monkeypatch them or construct `ao._LedgerIndex(<dir>)` keep their seams (row 26).
- The index lists a root's copies once per run, after its first live listing, because only a sweep adds one. It re-lists live files on every refresh, as today (row 36, M8).
  - It caches by `LedgerFile.name`. It re-reads a `LedgerFile` whose signature changed or whose live member exists and did not open, so a live file that failed beside an opened copy is retried (rows 27, 36). A copy-only stem has no live member to retry, so an unchanged one is read once per run.
  - A copy that did not open is not retried, because nothing but a hand edit changes one mid-run. A copy whose reader raises therefore costs one read per run.
  - It records each stem's read in the archive.
- Only an opened live member marks a session-keyed file as opened. A copy counts through its rows alone, so a session whose only file is an empty or rowless copy can still count as possibly swept (row 46, M17).
- A new data-quality key, "sessions with a code-review round whose ledger rows all came from archived copies", counts sessions with rows of which none came from a live member. It sits before the orchestrator key, which stays last (row 26). Those sessions stay in the headline (M17).
  - The index records, from each row's copy stamp, the sessions that have a row from a live member. A new `_ledger_rows_only_from_copies(jsonl, ledger_indexes)` reads that from the index the session's lookup just refreshed.
  - `entries_for_session` and `_read_ledger_row_entries_for_session` keep their `(list[(file_index, row)], bool)` return, and rows stay as stored. The tests that unpack either shape or build the pairs keep their seams (row 26).
- `_ledger_file_session_component` and `_row_session_id` read only `.name`, which a `LedgerFile` carries. Attribution and the session-keyed-file check keep their logic.
- `_read_ledger_row_entries_for_session` and `compute_author_outcomes` gain `archive=None`, so a library caller reads live files alone.
- `cmd_author_outcome` passes `LedgerArchive()`. `_print_author_outcome_report` prints the archive line, with `scope=all-repos`, as its own block before `Data quality` when it is given one.
- The file has 996 lines (row 25). After PRs B and D it has about 950, and the size check holds it at or under 1,000.

The possibly-swept counter needs no other change. A session whose archived copy yields its rows no longer counts.

**PR E: `reviewer-reads`.** PR E keeps a manifest lookup (row 43), so `reviewer-reads` counts the ledger files of this repo's removed worktrees. It reads ledger data and manifests only, never a worktree. The reasons:
- `reviewer-reads` keeps to this repo by path identity, with the limit below: it selects only the files whose name starts with the hash of a path the current `git worktree list` prints (rows 19, 20).
- A worktree the cleanup scripts removed has left that list, so its archived copies would match nothing.
- A file name holds only the path's hash, and a row holds no worktree path. Among the ledger data and the archive, a snapshot manifest is the only path-bearing record that ties a removed worktree to this repo (rows 21, 44).

The pieces:
- `_branch_records.snapshot_manifests(config_dir, home)` returns `SnapshotManifests(state, manifests)`, reached through `archive_subtree(config_dir, "branches", home)` (M19). `state` is that subtree's state, and `manifests` holds a `SnapshotManifest(key_directory, fields)` for each `branches/<key>/<snapshot>/manifest.json` of the account.
  - It follows no symlink below the subtree. It enters a key or snapshot directory only when `lstat` shows a directory, and opens a manifest only when `lstat` shows a regular file, as `ledger_dispositions._read_file_rows` does.
  - A listing below the subtree that fails other than as not found turns `state` into `unreadable`. The scan continues with the next directory, so every manifest it can reach is returned.
  - It reads at most 1 MiB and skips a larger file (row 56).
  - It skips a file that raises `OSError`, `UnicodeDecodeError`, `RecursionError` or `ValueError`, which covers `json.JSONDecodeError` and the integer digit limit. It also skips one that does not parse as an object. It prints nothing.
- `publication_scope._past_worktree_repo_hashes(manifests, worktree_paths)` returns the distinct repo hashes of the manifests it accepts, less the current worktrees' own hashes. It accepts a manifest only when all of these hold (row 47, M9):
  - its string `main_worktree_path`, as written, equals a current worktree path as printed or as resolved (row 21);
  - `ledger_repo_root` and `ledger_key` are strings, and `_ledger_repo_hash(ledger_repo_root)` equals the part of `ledger_key` before its first `.`;
  - its key directory's name equals `ledger_key`.
- That hash is of `ledger_repo_root` as written, never resolved, because the manifest stores git's own toplevel (row 47). It covers the removed worktree's branch-keyed and session-keyed stems alike (row 19).
- A manifest whose test raises `ValueError` is skipped, and the rest are still tested. `json.loads` accepts a lone surrogate in `ledger_repo_root`, and `os.fsencode` in `_ledger_repo_hash` then raises `UnicodeEncodeError`, a `ValueError` (`publication_scope.py:59-61`). The rest of the test only compares and splits strings, which cannot raise.
- `publication_scope._this_repo_ledger_files` gains `extra_repo_hashes=()`, matched as given.
- `review_ledger_copies.archive_summary_line` gains `past_worktrees=None`, which appends ` past_worktrees=<N>` when given.
- `ledger_dispositions.count_ledger_dispositions(..., archive=None)`:
  - adds the past repo hashes when given an archive;
  - selects live files, and copies when given an archive, with the same `_this_repo_ledger_files` (row 34);
  - lists copies only through the archive. `LedgerArchive`'s copy listing gains an optional `select_copies(directory, gaps)`, and `count_ledger_dispositions` passes one that calls `_this_repo_ledger_files`. The archive then lists only this repo's copies and records only the stems grouped from them, so every count on the line but `roots` and the five state fields comes from the selected set. `author-outcome` and the viewer pass none and list every copy;
  - records copy-listing gaps in their own counter, so the live `directory_state` is unaffected. A copy-listing gap turns that root's archive state into `unreadable`, and so does a `branches` state of `unreadable`;
  - groups them and reads every `LedgerFile` through PR C's `_read_member`.
- A `LedgerFile` with any member that did not read counts as unreadable and adds no rows, as an unreadable file does today (M16). `files_read` and `unreadable_files` then count stems, which equal files when no copies exist.
- `reviewer_reads.py` passes `LedgerArchive()` and prints the archive line, with `scope=this-repo` and `past_worktrees`, in the ledger section after its `ledger files:` line. `_print_report` and `_print_ledger` take the line as a defaulted keyword, so the golden report test and the direct `LedgerDispositionCounts` constructions stay valid (row 26). The file has 974 lines and about 986 after PR E (row 25). It grows that little because the line's text comes whole from `archive_summary_line`, so it stays at or under 1,000.
- What the archive line may carry in `reviewer-reads`:
  - Every count but `roots` and the five state fields covers only the files selected as this repo's by path identity, because selection runs before grouping and counting.
  - It names no path, stem or hash.
  - It has no count of other repos' stems or of skipped manifests, because each would be a figure over other projects' data on the account (G4).
  - A failed listing under `branches/` shows only as the root's `unreadable` state.

PR E states the path-identity limit in one place, the path-identity sentence of `docs/private-project-redaction.md` (`:158-166`). It reduces the matching "Known limits" bullet of `docs/transcript-analysis.md` (`:1772`) to a pointer to that sentence. The limit is documented, not closed (row 67): identity stays the path string, so a path that another repository's checkout occupied before or after this repo's worktree is not told apart. Two other effects follow:
- The manifest hashes widen live files as well as copies, which keeps a stem's live file and its copies in one history. They also count a removed worktree's unswept live file as this repo's, which the existing path-string identity already implies (`publication_scope.py:69`).
- The transcript half still reads only the current worktrees' project directories. The ledger half therefore covers sessions the transcript scan does not, and `covered by the transcript scan` shows that gap (row 53).

**What the commands print.** Each reading command prints one line with fixed fields and counts only (M10):

```text
ledger archive: scope=<all-repos|this-repo> roots=<N> present=<N> absent=<N> unmarked=<N> unreadable=<N> unresolvable=<N> copies_read=<N> copies_unread=<N> copy_names_skipped=<N> stems_only_in_archive=<N>
```

- `roots` counts the config-dir roots the run looked up, and the five state fields count them by archive state, so they sum to `roots`.
  - A root's state is its `review-narrative-ledger` subtree's.
  - A failed copy listing turns it into `unreadable`, and in `reviewer-reads` so does a `branches` state of `unreadable`.
- `copies_read` counts copies that opened, a copy skipped as a leading run included. `copies_unread` counts copies that did not open.
- `copy_names_skipped` counts `.jsonl` names in a copy directory that fail the copy-name rule.
- `stems_only_in_archive` counts stems with at least one copy and no live file.
- `roots` and the five state fields describe each root's archive as a whole, so in `reviewer-reads` an `unreadable` can come from another repository's directory under `branches/` or from a failed copy listing. Every other count covers only the files the command selects, and counts a stem once however often a run reads it.
- `author-outcome` prints `scope=all-repos`. Its index reads every ledger file and copy of each scanned account, whatever `--this-repo` selects, so its counts are corpus-wide.
- `reviewer-reads` prints `scope=this-repo` and appends ` past_worktrees=<N>`.
- A sample of the line in a doc elides every count to `N`. A real `author-outcome` line's `roots` and state counts give the account cardinality that `docs/private-project-redaction.md` § "Account cardinality" bars, and the header sample at `docs/transcript-analysis.md:989` elides its root count for that reason.
- No archive state changes either command's exit status. An archive that is not `present` leaves the command reading live files alone.
- Archive reads, the viewer's included, have no time cap and no off switch. A stalled archive volume hangs the command, a known limit the doc states (M13).
- Archive reads have no size bound (row 57).
  - Nothing prunes the archive, so each run lists every copy made so far on each scanned account, and `reviewer-reads` reads every manifest too.
  - `author-outcome` parses every copy and holds its rows for the run.
  - No run skips copies to stay within a bound, so growth costs time and memory and never changes a figure silently.
  - Only a prune by hand bounds it.

**Docs.** `docs/agent-branch-records.md` gains one section, "Reading the archive", after "Ledger copies", because the sibling session edits most other sections (row 32 relays it). PR C writes the section, and PRs D and E each add their part. It states:
- (PR C) the history rule, as a pointer to the "Ledger copies" section plus the live-file-last step, and that the skip removes every overlap the writer makes, so only a member changed by hand can repeat rows;
- (PR C) the five states, that an unmarked root is never read, and that `unreadable` covers an account directory that is a link or a regular file, although the writer follows a link there (row 74). The check guards the linking account's own readers and is not authentication: copies the writer deposits through such a link sit in the target account's directory, and that account's readers read them;
- (PR C) the stall sentence above;
- (PR C) that the live tools and the review-history hook read only `<config-dir>/review-narrative-ledger/`, and that no analysis reads `agent-reviews/` snapshots;
- (PR C) the viewer, its output, its order, its exit statuses and the three things its `--help` says;
- (PR D) which commands read copies, that they read with the key off, that each reads only the account directory of a config dir it scans, and that no flag turns the read off. PR E adds `reviewer-reads` to that list;
- (PR D) the size bullet above;
- (PR D) the truncation bias: a session whose rows all come from copies is classified from them, a truncated copy can lose its last rows, and the data-quality key counts those sessions;
- (PR E) how `reviewer-reads` finds removed worktrees through manifests and why it needs them;
- (PR E) that the manifest check is a consistency check, not authentication, because any process of the same OS user can write a manifest (row 47);
- (PR E) the ways a removed worktree stays out:
  - it has no manifest;
  - its manifest's main path is a linked worktree that is also gone, the cleanup scripts' fallback (row 48);
  - its repository moved after the manifest was written;
  - its manifest was skipped as non-regular, oversized or unparseable, or failed the consistency check, which no count shows.

`docs/transcript-analysis-architecture.md` updates the import lines of each changed module, and PRs C, D and E each add one `CHANGELOG.md` `[Unreleased]` entry (rows 31, 41). PRs A and B change no command's behavior, so they add none. Critical files gives each PR's other doc edits.

**Judgment calls.**
- Round numbers restart at 1 in the segment after a sweep, so a session whose rows span a sweep reads as rounds such as 1, 2, 1 in one history. `_round_number_mismatch` then counts it as a mismatch of the other kind, not "fewer blocks", and keeps it out of the headline (row 51). No row stores an offset to renumber by, so PR D tests this outcome rather than renumbering.
- M16 drops a whole stem in `reviewer-reads` when any member did not read. Only an unread later member can leave an earlier row wrongly terminal (row 52), so this also hides live rows today's run counts when an old copy is unreadable. Counting only the members after the last unread one would be exact. It needs per-member results from the shared reader for one command, and an unreadable copy shows in `copies_unread` and `unreadable`.
- A copy that fails to open in `author-outcome` prints its path on stderr, through the line a live file's failure prints today (`author_outcome.py:290-294`), and the doc states it. Holding that stderr as `ledger_dispositions._read_file_rows` does (`ledger_dispositions.py:140`) would need `author_outcome` to import `ledger_dispositions`, which imports it (`:30`), or a second copy of the hold. Holding it for copies alone would give one command two failure behaviors for one kind of file. The command has no scope refusal, so it is not a publication instrument (`docs/private-project-redaction.md:169-170`). A copy's path holds what the live path holds, the config dir, repo hash and session id, plus the archive root and a stamp.

**Alternatives set aside.**
- Feeding copies to the readers as extra files: the first-dot parse would key a copy by `<session>.<stamp>`, and both readers would repeat rows (rows 16, 17).
- A row-id drop across members, alone or beside the skip.
  - Alone, it keeps each row in the earliest member that holds it. A complete copy beside its kept live file would then put every row under the copy's stamp and count the session as served only by copies (M17). It would also repeat the id-less rows of a pre-id session-keyed stem whose copy failed while its source stayed (row 18).
  - Beside the skip, no writer path reaches it (row 45), and the engineer approved cutting it (row 68). A member restored or edited by hand can therefore count its rows twice, which the doc states.
- A byte-prefix comparison in code: it needs a second read of every member, since both readers' one-file functions return rows (row 27).
- A fallback in `show` or `render`: Out of scope records why.
- Reading the archive only under an opt-in flag: row 2 asks for the opposite default.
- An opt-out flag for live-only figures: the engineer never wants archive reads turned off (row 42).
- The resolver in `_config_dir.py`: that module resolves config dirs and the declared-roots file, while the archive layout's home is `_branch-records-lib.sh` and `docs/agent-branch-records.md`.
- The resolver in `transcript_analysis/scope.py`: it is a 1,235-line split-pending file (row 25), and a caller outside the transcript package would import that package for it.
- Reading a subtree that exists under an unmarked root: the writer refuses without the marker (row 59), so nothing vouches for data under an unmarked root.
- A parity test against `_branch_records_encode_component` alone, as the dispatch worded it: it would miss a canonicalization or root difference.
- Comparing the module with the test helpers' own formula: that compares Python with Python (row 23).
- Pinning HOME for the whole scripts suite: it changes every test's home, and with it git's global config lookup, for one lookup.
- An environment override of the archive root that only Python reads: a reader and the writer could then disagree.
- A conftest tripwire that fails a test passing `_branch_records.archive_root` a home outside `tmp_path`: every archive lookup this plan adds goes through `LedgerArchive`, whose default home is the pinned seam, and a subprocess test sets HOME itself (row 24). A tripwire would guard only a caller the plan does not add, as a second layer over the pin.
- Re-listing copies on every session lookup: only a sweep adds a copy, and copies have no deletion bound (`docs/agent-branch-records.md:110`), so every lookup would stat a growing set again.
- Re-listing copies when a live name disappears mid-run: today's index already loses the rows of a live file swept between two lookups, so reading copies adds no new gap. Out of scope records the race.
- `leading_copies_skipped` on the commands' line: it describes one stem's merge, which the viewer's header shows, and a corpus-wide total points at no stem.
- Keeping `_LedgerIndex` in `author_outcome.py` and moving only the signature helper: the file would pass 1,000 lines (row 25).
- A separate module for the index: it would need its own test file and architecture section, for code whose subject `review_ledger_copies` already holds.
- Matching `reviewer-reads` copies by current worktree hashes only: a removed worktree's files would never count (rows 20, 43).
- Counting every copy on the account in `reviewer-reads`: it counts other repositories' copies (G4).
- The session's two-way lookup between `ledger_key` stems and session-id stems: a repo hash already covers both stem kinds (row 19).
- Widening only copies by the manifest hashes: a stem could lose its live tail.
- Hashing a manifest's `ledger_repo_root` as resolved as well: resolving it at read time can map a path that has since become a symlink onto another repo's hash (row 47).
- A guard against a reused path, by the architect consult's root-commit manifest field or by dropping a manifest whose `ledger_repo_root` exists now and is not a current worktree.
  - The engineer judged the reuse "not a real case" (row 69) and chose a documented limit (row 67). Row 70 records an earlier typed remark, "I really don't want to do another migration there", whose question this plan cannot show, so it does not support this decision alone.
  - The root-commit field is a change to the writer's manifest, outside this plan (G1).
  - The stat guards only while the other repository's directory exists, and adds a stat outside the archive for each accepted manifest.
- A second identity signal for a manifest, such as its `tip_sha` resolving in this repo: `tip_sha` can be empty (row 48), and `git gc` can drop the tip of a squash-merged branch once the branch is deleted, which would leave out a real removed worktree. It also costs a git call per manifest.
- Tying a removed worktree to this repo through a row's `reviewed_head` or `reviewed_tree`, or through its `session_id` joined to a transcript's `cwd`: older rows lack the reviewed-state fields, `gc` can drop unreachable objects, and transcripts age out after `cleanupPeriodDays` (row 44).
- Counting the readable members of a `LedgerFile` whose other member failed, in `reviewer-reads`: Judgment calls gives the reason.
- Excluding sessions served only by copies from author-outcome's headline: a complete copy, the case the sweep's compare step aims at (`docs/agent-branch-records.md:116`), would lose the rows the archive keeps for analysis (row 11).
- Carrying the copy-only flag as a stamp key in each row or as a third element of each entry: a stored key of that name would collide with the viewer's display field, and a third element breaks the tests that unpack either shape (row 26).
- A time cap on archive reads, by a thread or a subprocess timeout: neither bounds a read blocked in uninterruptible I/O, which the writer's cap cannot bound either (row 28). An ejected volume leaves a dangling root link, which needs no cap.
- A torn-line count: a copy cut at a row boundary has no torn line (`docs/agent-branch-records.md:118`), so the count would understate truncation.
- An unmatched-stems count in `reviewer-reads`: it counts other repos' files (G4).
- The viewer as `review-ledger.sh show --archived <stem>` (row 8): bash would need the history rule a second time or a call into Python, plus a key-free account resolver, all inside the live `show` arm.
- The viewer as a standalone script: it would need its own output escaping, docs entry and config-dir handling, which the CLI already has.
- A free-text opt-in flag, a row cap or a past-record reminder line in the viewer, and a separate exit status when it could not consult the archive: `show` has none of them, and rows 54 and 55 give the viewer `show`'s shape.
- Scoping the viewer to this repo's worktree hashes: the branches it serves often have no worktree left.
- Two PRs, with the second holding both commands and the viewer (row 6), or four, with the library and `author-outcome` in one PR: row 62 selects five.

### Assumption ledger

**Root:** The two analysis commands that read review-ledger rows read only `<config-dir>/review-narrative-ledger/` (`author_outcome.py:440`, `ledger_dispositions.py:202`). Once the retention sweep removes a file, its rows leave every analysis, although the archive holds a copy (`docs/agent-branch-records.md:86-93`).

**Givens:**
- G1. The archive's root, sentinel, account encoding, copy names and manifest fields are the shipped writer contract that `docs/agent-branch-records.md` publishes, so changing any of them is a writer change outside this plan. [verified: `_branch-records-lib.sh:16-17`, `:54-61`, `:139-146`, `:369-382`, `:411-429`]
- G2. `_lib_review_ledger_path` and `_lib_reviewer_round_state_key_for_branch` own ledger file names, which the round gate and the dashboard share, so this plan reads names as they are. [verified: `claude/.claude/hooks/_lib.sh:5422-5428`, `:5851-5869`]
- G3. Another session owns the transcript archive and its readers, including an undesigned PR 3, and edits most sections of `docs/agent-branch-records.md`. [unverified: relayed by the dispatching session]
- G4. A published figure must be computed over this repository's own corpus on a single account, a rule the repo owner set and `reviewer-reads` exists to meet. [verified: `CLAUDE.md` § "Redact private-project-identifying content"; `publication_scope.py:1-5`]

**Rows:**
1. [engineer-verified: "readers should read the archive after the key's turned off"] No reader reads `agent_branch_records`.
2. [engineer-verified: "archive routes should be on by default"]
3. Row 2 means the reading commands read the archive by default, and the key's own default stays unchanged. [engineer-verified: "Readers read archive by default (Recommended)"] That option's description was the session's. [unverified: not the engineer's words] Turning the key's default on would make every stow consumer's sweep keep due files and warn wherever no sentinel exists. [verified: `docs/agent-branch-records.md:74`]
4. [engineer-verified: "smaller PRs are better"]
5. [engineer-verified: "Small resolver PR first, then ledger reader (Recommended)"], the selected sequencing label.
6. That option's description, and the Context's placing of the viewer in the second PR, were the session's. [unverified: not the engineer's words] This plan keeps the resolver first and splits the rest into four PRs on rows 4 and 62.
7. [engineer-verified: "Include it"], the selected label for including a read-only viewer of archived ledger rows.
8. The viewer shape `review-ledger.sh show --archived <stem>` was the session's proposal. [unverified: not the engineer's words] M11 places the viewer elsewhere.
9. [engineer-verified: "Generic contract, defer transcript reader (Recommended)"], the selected transcripts label. Its description was the session's. [unverified: not the engineer's words] This plan reads "generic contract" as a subtree-agnostic resolver, and adds no transcript reader.
10. [engineer-verified: "I don't really care so much about restoring agent reviews automatically"]
11. [engineer-verified: "the reason we don't delete is because the archive files are useful for analysis"] and [engineer-verified: "It's needed for analysis after the fact."]
12. Among the Python scripts, only `author_outcome.py` and `ledger_dispositions.py` read the ledger directory, the latter reached from `reviewer_reads.py:953-955`. `routing_guard.py` imports `author_outcome` for transcript helpers only. [verified: Grep of `claude/.claude/scripts/**/*.py` for `review-narrative-ledger` and `_REVIEW_LEDGER_DIRNAME`; Grep of `author_outcome\.\w+` in `transcript_analysis/`]
13. No `transcript_analysis` module reads `agent-reviews/`. The one mention is a tokenizer comment. [verified: Grep; `reviewer_yield.py:266`]
14. No command breaks ledger dispositions down by reviewer agent. No Python module reads a row's `reviewers` field, `ledger_dispositions` reads six fields and `author_outcome` five. [verified: Grep for `"reviewers"`; `ledger_dispositions.py:6-9`; `author_outcome.py:50-52`]
15. A copy is `<account directory>/review-narrative-ledger/<stem>.<stamp>.jsonl`, and the stamp is the source's mtime in `%Y%m%dT%H%M%SZ` form. [verified: `_branch-records-lib.sh:411-429`] Every stem holds exactly one `.`. [verified in `.claude/plans/archive-ledger-before-sweep.md` row 14; not re-traced here]
16. `author_outcome` takes a file's session slot as everything after the first dot. [verified: `author_outcome.py:313-317`]
17. `author_outcome` forms round blocks from runs of one (file position, round) pair, and `ledger_dispositions` supersedes rows within one file, in file order. [verified: `author_outcome.py:445-466`; `ledger_dispositions.py:166-179`] A copy and its source read as two files would repeat rows and split blocks. [unverified: inferred from the code, not run]
18. A row's id is the first 12 hex digits of the sha256 of the row's own JSON line. The one append path writes it on every row, and writes nothing when the row does not parse back with its id. [verified: `_review-ledger-lib.sh:604-610`; `review-ledger.sh:708-721`; `:771` is the only caller of `_lib_append_json_line_locked`] The id field arrived in the change that keyed ledgers by branch, and before that change every ledger file was keyed by session. [verified: `CHANGELOG.md:545`, `:548`, `:551`, which record that change; `docs/design-decisions/branch-scoped-review-ledger.md:107`] So the writer's id-less rows exist only in session-keyed files that took rows before that change. [verified by those sources; `git log -S` was not run, because this session has no shell] Such a stem has overlapping members only when a copy failed or mismatched while its source stayed (row 45).
19. The repo hash is the sha256 of `git rev-parse --show-toplevel` in the tree the writer ran in, and both stem kinds start with it. [verified: `review-ledger.sh:251`; `_lib.sh:654-658`, `:5422-5428`, `:5851-5869`] So each linked worktree has its own hash. [unverified: git behavior, not run; `publication_scope.py:64-75` already relies on it]
20. `reviewer-reads` selects ledger files by hashing the paths `git worktree list` prints, as printed and as resolved, so a removed worktree's files are not selected today. [verified: `reviewer_reads.py:938`, `:953-955`; `publication_scope.py:64-88`; `scope.py:124-140`]
21. A snapshot manifest holds `main_worktree_path`, `worktree_path`, `ledger_repo_root` and `ledger_key`, at `<account directory>/branches/<ledger_key>/<stamp>.<pid>.<n>/manifest.json`. Both cleanup scripts pass the main worktree path. [verified: `_branch-records-lib.sh:301-320`, `:344`, `:369-387`; `docs/agent-branch-records.md:79`, `:82`; `cleanup-merged-branches.sh:1120`; `cleanup-idle-open-pr-worktrees.sh:404`] A worktree removed any other way has no manifest. [verified: `docs/agent-branch-records.md:120`]
22. The writer's account directory is `${HOME:-}/.local/state/agent-branch-records/` plus the config dir canonicalized by `cd -P` and `pwd -P`, encoded `%` first. [verified: `_branch-records-lib.sh:47-61`, `:139-146`] With HOME empty the writer's root is `/.local/state/agent-branch-records`, where this plan's reader resolves nothing. [verified: `:144`; the divergence is this plan's choice]
23. The archive tests already compute the account directory in Python, and `run_status` reports the lib's `BRANCH_RECORDS_ACCOUNT_DIR` from a confined HOME and config dir. [verified: `claude/.claude/scripts/tests/_branch_records_helpers.py:86-142`, `:255-306`]
24. The scripts tests pin `CLAUDE_CONFIG_DIR` and `TRANSCRIPT_CONFIG_DIRS_FILE` but not HOME. [verified: `claude/.claude/scripts/tests/conftest.py:1742-1776`] Unpinned, a command test's archive lookup would stat the developer's real archive root, and its state would differ by machine. The one subprocess `reviewer-reads` test sets HOME under `tmp_path`. [verified: `test_transcript_reviewer_reads_command.py:628-637`] A monkeypatch cannot reach a child process. [unverified: Python behavior, not run]
25. The size budget. [verified: `author_outcome.py` and `reviewer_reads.py` read to their end, the others counted with a line-anchored Grep; `docs/design-decisions/code-file-line-limit.md:24`, `:47-50`; `code-file-size-exceptions.toml:251-264`, `:366-367`, `:471-472`]
    - The limit is 1,000 lines, for test files too.
    - An exception row's ceiling is the file's exact count, so a PR that grows an exception file sets its ceiling to the new count.
    - Under the limit: `author_outcome.py` 996 lines, `reviewer_reads.py` 974, `test_transcript_ledger_dispositions.py` 931, `test_transcript_reviewer_reads_command.py` 708 and `test_transcript_cli.py` 598.
    - Exceptions: `test_author_outcome.py` 3998, `claude/.claude/scripts/tests/conftest.py` 2039, `scope.py` 1235, `select-tests.py` 1557 and `test_select_tests.py` 4396.
26. Tests depend on these seams, so the change keeps each. [verified: the cited lines]
    - `test_author_outcome.py` monkeypatches `author_outcome._list_ledger_files` (`:547`, `:569`, `:2636`) and `_read_ledger_rows_from_file` (`:1427`, `:1468`).
    - `TestLedgerIndex` constructs `ao._LedgerIndex(<dir>)` with one argument (`test_author_outcome.py:1457`).
    - `test_transcript_ledger_dispositions.py` monkeypatches `author_outcome._read_ledger_rows_from_file` (`:782`, `:835`).
    - `test_author_outcome.py` unpacks `_read_ledger_row_entries_for_session`'s `(entries, bool)` return and builds the `(file_index, row)` pairs `_round_blocks` takes (`:73`, `:407-620`, `:1241-1333`).
    - Tests build `LedgerDispositionCounts` directly and compare a whole `reviewer-reads` report (`test_transcript_reviewer_reads_report.py:221-230`, `:440-447`).
    - A test reads the last line of author-outcome's Data quality block, and another pins the orchestrator key as the last key (`test_author_outcome.py:3516-3530`).
27. `_read_ledger_rows_from_file` opens with a plain `open` and catches only `json.JSONDecodeError` and `UnicodeDecodeError` per line, so the `ValueError` of an over-limit integer and a `RecursionError` escape it. `ledger_dispositions._read_file_rows` wraps it with an lstat regular-file check, held stderr and a catch of those two, and returns None for a file it cannot read. [verified: `author_outcome.py:265-296`; `ledger_dispositions.py:125-150`]
28. The writer's 5-second cap does not bound a call blocked in uninterruptible I/O. [verified: `docs/agent-branch-records.md:73`] No Python primitive these commands could use bounds one either. [unverified: not tested] A dangling root link reads as a missing sentinel. [verified: `docs/agent-branch-records.md:45`] A stat through a dangling link fails at once. [unverified: tool behavior, not run]
29. `show`'s no-ledger notice prints on stdout when `--out` is absent. `show` prints every stored field, `engineer_quote` included, after a `clean` that replaces control and format characters. It tags each row with a display-time `source_repo_hash` that the write schema never carries, and the tag replaces a stored key of that name. Before reading, it exits 2 when a ledger path exists as a symlink or anything but a regular file. It sorts rows by `event_time // ""`, which its comment calls stable in practice but not guaranteed by jq. It exits 0 with no ledger, 1 when its read or summary fails, and 2 on a usage error. [verified: `review-ledger.sh:136-147`, `:772`, `:805-807`, `:857`, `:860-867`, `:869-878`, `:885`, `:889-891`, `:906-914`; `_review-ledger-lib.sh:619-625`, `:642`, `:659`]
30. The package prints `_DO_NOT_PUBLISH_BANNER` for local-only output. [verified: `scope.py:747-749`] Three CLI walks pin every subcommand. [verified: `test_transcript_cli.py:351-443`]
    - `_SUBCOMMANDS_LACKING_A_SCOPE_FLAG` must list exactly the subcommands without `--projects` or `--this-repo`.
    - Every other subcommand must refuse both flags together.
    - Each handler must be named `cmd_<name>` in the module that defines `_add_<name>_subparser`, and `cli` must expose that registrar.
31. `CHANGELOG.md` records analysis-command changes under `[Unreleased]`. [verified: `CHANGELOG.md:422-424`, `:770`]
32. The dispatching session's design conclusions came from two design reviews, not from the engineer, and so did the report that the sibling session edits most sections of `docs/agent-branch-records.md` and accepts either candidate resolver home. [unverified: relayed] The Alternatives and the M rows record where this plan keeps or departs from each conclusion.
33. `os.path.realpath(..., strict=True)` needs Python 3.10, which the package already needs. [verified: `author_outcome.py:515` uses `zip(..., strict=False)`] That it resolves a path as `cd -P` and `pwd -P` do is what PR A's parity test checks. [unverified until that test runs]
34. `_this_repo_ledger_files` takes a name's repo hash from before its first dot, so it selects a copy by the same rule as a live file. [verified: `publication_scope.py:78-80`]
35. A ledger file only grows, so a copy taken while its source stayed is a byte prefix of every later copy and of the live file. [verified in `.claude/plans/archive-ledger-before-sweep.md` rows 29 and 38; not re-traced here] The rows parsed from a byte prefix are a leading run of the longer file's rows, a torn last line aside. [unverified: inferred, not tested]
36. `author_outcome`'s index re-lists a root's live files on every session lookup, so a file that grows mid-run is seen. [verified: `author_outcome.py:349-381`; `docs/transcript-analysis.md:1802`]
37. A transcript-package change selects the scripts tests, the ticket-reference test and three hooks tests that import or run the package. [verified: `test_select_tests.py:1905-1921`] Those hooks tests are selected only by rows that name the package directory, `transcript-analysis.py`, `_config.py`, `_config_dir.py` or `compaction-context.py`, so a change to `_branch_records.py` alone would select neither `test_review_ledger_script.py` nor `test_nudge_error_mode_analysis.py`. [verified: `select-tests.py:346-351`, `:1013-1036`] `compaction-context.py` imports only `render`, `review_rounds`, `scope` and `user_input`, which never reach `_branch_records`. [verified: `compaction-context.py:29`] A literal path in a rule needs an entry in `_EXACT_MATCH_LITERAL_PATH_CONSTANTS`. [verified: `test_select_tests.py:2544-2556`]
38. [engineer-verified: "Analysis commands only (Recommended)"], the selected label on this change's scope, which the Out of scope item on hooks, skill-body lines, rule files and `CLAUDE.md` lines rests on.
39. [engineer-verified: "Proceed anyway"], the selected label on the size question, asked at a projection of about 1,340 changed lines in four PRs. Superseded by row 66.
40. [engineer-verified: "Four PRs, not two"] Superseded by row 62.
41. [engineer-verified: "Architecture doc and CHANGELOG entries"]
42. [engineer-verified: "Also we would never want to turn off archive reads."]
43. [engineer-verified: "Keep lookup, drop flag (Recommended)"], the selected label on whether `reviewer-reads` keeps the manifest lookup for removed worktrees and this plan drops an earlier draft's opt-out flag.
44. A ledger file name carries its writer's worktree path only as a sha256, and no field a row stores is a worktree path. [verified: `publication_scope.py:59-61`, `:67`; `review-ledger.sh:684-703`, the row's fields] So among the ledger files and the archive, a snapshot manifest is the only path-bearing record that ties a removed worktree to this repo. [unverified: inferred; archived snapshot files other than manifests were not read] Two weaker ties exist: a row's `reviewed_head` or `reviewed_tree` checked against this repo's object store, and a row's `session_id` joined to a transcript whose records carry `cwd`. [verified: the two row fields at `review-ledger.sh:690`, `:703`; the transcript `cwd` field relayed from review, not read]
45. On every writer path, a stem's members overlap only as leading runs. A ledger file only grows (row 35), and the sweep's copy step removes nothing under the archive. So a failed or cap-killed `cp`, a `cmp` mismatch and a copy rewritten in place each leave a copy that is a byte prefix of its source and of every later copy of it. [verified: `_branch-records-lib.sh:395-457`; `docs/agent-branch-records.md:91`, `:117-118`] A `cmp` mismatch means the source changed during the copy, and the only change the writer makes to a ledger file is an append. [verified: `review-ledger.sh:771`] So the leading-run skip removes every overlap a writer path makes, and across members only a member changed by hand or by another writer repeats a row outside a leading run. [unverified: inferred; PR B's real-writer mismatch case checks it]
46. A truncated copy can be empty, cut mid-row or cut at a row boundary, and nothing proves a copy complete. [verified: `docs/agent-branch-records.md:118`] The index marks a session's file as opened even when it yields no row, and an opened session-keyed file keeps the session out of the possibly-swept count. [verified: `author_outcome.py:383-395`, `:552`] A session classified from a truncated copy can lose its last ADDRESS row and read as PASS. [unverified: inferred from `author_outcome.py:580-594`]
47. Any process of the same OS user can write a manifest. [verified: `docs/agent-branch-records.md:84`] `ledger_repo_root` is `git rev-parse --show-toplevel` run in the removed worktree, `ledger_key` is the sha256 of `ledger_repo_root`, a `.`, and the sha256 of the branch, and the manifest sits under `branches/<ledger_key>/`. [verified: `_branch-records-lib.sh:303`, `:311`, `:318-319`, `:344`; `hooks/_lib.sh:654-658`, `:5422-5428`] So a manifest can be checked against its own location. That catches corruption and a mismatched hand edit, not a forger who writes both. [unverified: inferred] Git prints the toplevel already resolved. [unverified: git behavior, not run]
48. Both cleanup scripts fall back to `MAIN_WORKTREE_PATH="$REPO_ROOT"` when `git worktree list` fails, and `REPO_ROOT` can be a linked worktree. [verified: `cleanup-merged-branches.sh:411`; `cleanup-idle-open-pr-worktrees.sh:164-167`] A manifest's `tip_sha` is empty when the branch ref does not resolve. [verified: `_branch-records-lib.sh:316`]
49. `Path.glob` returns no matches for a directory it cannot list, and `scope._list_dir_recording_gaps` records a gap for one instead. [verified: `scope.py:314-329`]
50. A test file that imports `transcript_analysis` without the shim must be in `TEST_FILES`, and a module in `PRODUCTION_MODULES` must bind its siblings by an unaliased `from transcript_analysis import <m>`. [verified: `test_transcript_package_module_prefixes.py:27-65`, `:324-336`, `:538-549`]
51. A sweep leaves the next `append` to start a new segment. [verified: `docs/agent-branch-records.md:92`] That segment's rounds restart at 1. [unverified: relayed from review at `review-ledger.sh:865`, not re-read] `_round_number_mismatch` returns `_MISMATCH_OTHER` when block round values do not strictly increase. [verified: `author_outcome.py:514-516`]
52. A row is superseded only by a later row that names it as `ref`. [verified: `ledger_dispositions.py:166-179`] So only an unread later member can leave an earlier row wrongly terminal. [unverified: inferred]
53. `docs/transcript-analysis.md:1659` says the transcript and ledger halves of `reviewer-reads` see one worktree set, and the transcript half takes its project slugs from the current worktrees only. [verified: that line; `reviewer_reads.py:938-941`]
54. [engineer-verified: "Yes, match show (Recommended)"], the selected label on the viewer's shape.
55. That option's description was the session's relay of a design review's advice: the viewer prints every stored field with no cap, flag or reminder line, and exits as `show` does. [unverified: not the engineer's words] So the viewer prints `finding`, `rationale` and `engineer_quote`, which a copy holds for every repo on the account. [verified: `docs/agent-branch-records.md:110`] As the session relays them, the engineer's answers on matching `show` covered its exit status and its `event_time` sort (row 64). [unverified: the session's relay] Row 73 records the engineer's answer on the viewer's two other departures from `show`: it prints no `source_repo_hash` (row 65), and it escapes with `ensure_ascii` where `show` applies `clean` (row 29). The viewer's section in `docs/transcript-analysis.md` states both.
56. A manifest holds ten fields, three of them paths and one a branch name. [verified: `_branch-records-lib.sh:369-382`] Linux's `PATH_MAX` is 4,096 bytes, and jq writes a character in at most six bytes, so a writer's manifest stays far below 1 MiB. [unverified: `PATH_MAX` not read this session; a branch name has no such bound, and a manifest over the cap is skipped]
57. Nothing prunes the archive, and a copy has no deletion bound. [verified: `docs/agent-branch-records.md:110`, `:122`] The comment on `ledger_dispositions._read_file_rows` bounds held rows by the 30-day sweep. [verified: `ledger_dispositions.py:148-149`]
58. CI runs on `ubuntu-24.04` only. [verified: `.github/workflows/tests.yml:28`, `:244`] A case-insensitive or normalizing volume can make `realpath` and `pwd -P` spell one path differently. [unverified]
59. The writer refuses unless the root's marker passes `test -f`, which follows a link and requires a regular file. [verified: `_branch-records-lib.sh:148-157`]
60. Only `author_outcome.py` reads `_file_signature`, `_row_session_id`, `_ledger_file_session_component` and `_event_time_sort_key`, no test names them, and `_event_time_sort_key` has one call site. `_LedgerIndex` has one non-test constructor. [verified: Grep of `claude/.claude/scripts/` for those names; `author_outcome.py:415`, `:440`]
61. [engineer-verified: "Keep show live-only (Recommended)"], the selected label on whether `show` reads the archive. The reasons the Context gives for keeping the live tools live-only are the design reviews' (row 32), not the engineer's, and this plan did not re-trace them. [unverified: relayed]
62. [engineer-verified: "Five PRs (Recommended)"], the selected label on the PR count, with the typed note [engineer-verified: "at least I’ll learn if splitting up into five PR’s actually makes this whole process easier"].
63. That option's description, including the PR order, was the session's relay of a design review's advice. [unverified: not the engineer's words] The order puts the viewer before both commands because it adds `_read_member`, which PR E reuses, and the conftest pin, which PRs D and E rely on.
64. [engineer-verified: "Match show on both (Recommended)"], the selected label on whether the viewer takes `show`'s exit status for a ledger path that is not a regular file and `show`'s `event_time` sort.
65. That option's description was the session's: the viewer exits 2 for a symlink, FIFO or directory at a ledger path, as `show` does, sorts rows by `event_time` with `show`'s stable sort, keeps `source_copy_stamp`, and adds no `source_repo_hash`, because it takes a stem and not a branch. [unverified: not the engineer's words]
66. [engineer-verified: "Yes, proceed at this size (Recommended)"], the selected label on the size question, asked at a projection of about 2,350 changed lines in five PRs. That option's description was the session's. [unverified: not the engineer's words] Later review rounds grew the estimate to about 2,850 before row 68's cuts, and the estimate after them was about 2,650. Superseded by rows 68 and 72.
67. [engineer-verified: "Documented limit, follow-up later (Recommended)"], the selected label on how to treat ledger files at a reused path: a removed worktree's path that later becomes another repository's toplevel, or a current path that another repository used earlier. That option's description, that the row-identity change is a follow-up this plan does not schedule, was the session's. [unverified: not the engineer's words]
68. [engineer-verified: "Approve the cuts and the size (Recommended)"], the selected label on an architect consult's proposed cuts and its size figure. The question carried an estimate of about 2,800 to 2,950 changed lines with a writer PR, which the engineer then declined. [unverified: the estimate was the architect consult's, shown to the engineer in the question text] Row 72 supersedes it on size. The cuts, as the session relayed them [unverified: the session's relay of the consult, not the engineer's words]:
    - no cross-member id drop, and with it no `duplicate_rows_dropped` field, its tests, its Judgment-calls paragraph, its Alternatives entries, the fixture rule that exists only because both mechanisms exist, or PR E's drop case;
    - the malformed-input tests, PR E's manifest cases and PR A's state cases, folded into parametrized tests;
    - PR E's `TestOutputInvariant` additions and its byte-identical foreign-data case merged into one corpus;
    - `archive_summary_line`, `ledger_file_signature` and the `past_worktrees` parameter each moved into the PR of its first caller.
69. [engineer-verified: "Whoa, the concern was using the same folder path for a different repo? Like, okay, I'm laughing because that would, a human would never do that, right? ... that's not a real case. So that would fall under, I wouldn't, it's not even like gold plating. It's like something that's not, that a human wouldn't do."], typed on whether the reused-path case is real.
70. [engineer-verified: "I really don't want to do another migration there."], typed earlier in the session. The question it answered was not relayed to this plan's author. [unverified]
71. From rows 67-70 the session concluded: no writer PR, no root-commit manifest field, no row-schema work, five PRs, and `reviewer-reads` accepting a manifest by its main path as M9 has it. [unverified: the session's conclusions, not the engineer's words] The root-commit field was the architect consult's proposal. [unverified: relayed]
72. [engineer-verified: "Accept about 3,000 (Recommended)"], the selected label on the size question asked at a projection of about 3,000 changed lines in five PRs, after review round 3. That option's description was the session's. [unverified: not the engineer's words] This row supersedes rows 66 and 68 on size.
73. [engineer-verified: "Fine, state them in docs (Recommended)"], the selected label on the viewer's two remaining differences from `show`: it prints no `source_repo_hash`, and it escapes characters with JSON escaping where `show` replaces them. That option's description was the session's. [unverified: not the engineer's words]
74. The writer follows a link at the account directory: `branch_records_status` tests it with `[ -d ]`, `_branch_records_make_archive_dirs` skips `mkdir` when that holds, and `chmod 700` follows the link. [verified: `_branch-records-lib.sh:161`, `:245`, `:252`]

**Mechanisms:**
- M1. `_branch_records.py` as the resolver's home, with `home` passed in explicitly. anchors: row1, row9, row22, row25, row32. `_config_dir.py` and `scope.py`, the two candidates the dispatch relayed, are set aside under Alternatives.
- M2. A parity test that runs `branch_records_status` with the key on and compares `BRANCH_RECORDS_ACCOUNT_DIR` with `account_directory` as `Path` objects. anchors: row22, row23, row33, row58. An encoding-only test and a helper-formula comparison are set aside under Alternatives.
- M3. Five subtree states, where `unmarked` covers both "nothing archived" and "volume not mounted" and `absent` means the root is set up and the subtree does not exist, and only a marker stat that finds nothing or a non-regular file gives it. anchors: row1, row28, row59.
- M4. One `LedgerFile` per stem: copies in stamp order, the live file last, and a leading-run skip that removes every writer-path overlap. anchors: row15, row16, row17, row18, row35, row45, row68. Extra files, a row-id drop across members and a byte comparison are set aside under Alternatives.
- M5. Members read through each command's own one-file reader, so each keeps its failure policy, `author-outcome`'s stderr line for a file that fails to open included, after one shared regular-file check on copies, and a reader's `ValueError` or `RecursionError` counts its member as not opened. anchors: row26, row27.
- M6. The reading commands always read the archive, with no flag that turns it off, and library callers default to `archive=None`. anchors: row2, row3, row24, row26, row42. An opt-out flag is set aside under Alternatives.
- M7. An `_archive_home()` seam that the scripts conftest pins under `tmp_path` from PR C on, and a `home` parameter for tests that build an archive. anchors: row24, row25. A suite-wide HOME pin, a Python-only root override and a tripwire on `archive_root` are set aside under Alternatives.
- M8. Copies listed once per root per run, after the live files, and live files re-listed as today. anchors: row36, row49. Re-listing copies per lookup or when a live name disappears is set aside under Alternatives.
- M9. Repo hashes from manifests that agree with their own location, hashed as written and fed into `_this_repo_ledger_files` for both directories. anchors: row19, row20, row21, row34, row43, row44, row47, row67, row69, row71. Current hashes only, every copy on the account, the two-way stem lookup, copy-only widening, resolved hashing, a `tip_sha` check, and a reused-path guard by a root-commit field or a stat are set aside under Alternatives.
- M10. One counts-only archive line per command, labelled with the scope its counts cover, with `roots` and the five state fields describing each root's whole archive and every other field defined over the files that command selects, with each stem's skip count left to the viewer's header and every count elided to `N` in a doc sample. anchors: root, row11, row26. A per-stem merge count on the line is set aside under Alternatives.
- M11. The viewer as a repo-unscoped transcript-analysis subcommand that selects copies by exact stem equality. anchors: row7, row8, row29, row30. `review-ledger.sh show --archived`, a standalone script and a repo-scoped viewer are set aside under Alternatives.
- M12. Viewer rows as `show` prints them: every stored field, stable-sorted by `event_time` over history order, as ASCII-escaped JSON with a display-time `source_copy_stamp` that replaces any stored key of that name, under the banner and one stderr header. anchors: row29, row54, row55, row64, row65, row73. A free-text opt-in, a row cap and a reminder line are set aside under Alternatives.
- M13. No time cap and no off switch on archive reads, with a doc sentence that states the stall as a known limit. anchors: row28, row42. The heavier thread and subprocess caps are set aside under Alternatives.
- M14. `author_outcome.py` held at or under 1,000 lines by moving `_LedgerIndex` and its helpers into `review_ledger_copies.py`, a seam-named test file for `ledger_dispositions`, and exact ceilings for the four exception files the diff grows, each set in the PR that grows it. anchors: row25, row26, row60. Keeping the index in place and a separate index module are set aside under Alternatives.
- M15. Five PRs, A, then B, C, D and E. anchors: row4, row5, row6, row62, row63, row66, row68, row71, row72. Two or four PRs are set aside under Alternatives.
- M16. In `reviewer-reads`, a `LedgerFile` with an unread member counts as unreadable and adds no rows, a judgment call the Approach states. anchors: row17, row27, row52.
- M17. A data-quality key for sessions served only by copies, carried by a per-session flag on the index so the entry shapes stay, and only a live member's open marking a session-keyed file opened. anchors: row11, row26, row46. Excluding those sessions from the headline, and a stamp key or a third entry element, are set aside under Alternatives.
- M18. A resolver that classifies by the marker first, requires an absolute home and config dir, and keeps a subtree inside its account directory's real path. The account directory itself must be a directory and not a link, so a link or a regular file there is `unreadable`. anchors: row22, row59, row74. Reading under an unmarked root is set aside under Alternatives.
- M19. Manifest reads that follow no symlink below `branches/`, behind an `lstat` regular-file check and a 1 MiB cap, with every parse failure skipped silently and a failed listing reported as `unreadable`. anchors: row47, row49, row56.
- M20. Viewer exit statuses as `show`'s: 2 for a bad stem or a member path that is not a regular file, 1 for a member that did not read, and 0 otherwise, with the archive state in the stderr header. anchors: row29, row54, row55, row64, row65. A separate status for an archive it could not consult is set aside under Alternatives.
- M21. Every stem read through `read_ledger_file`, live-only ones included. anchors: row26, row45.
- M22. `_branch_records.py` added to the `select-tests.py` rows whose importers reach it, in PR B, from which `author_outcome` reaches it. anchors: row37.

## Critical files

Each PR is one `code-writer` dispatch on its own branch, started from a base that holds the PRs before it. Paths are under the repository root.

From PR C on, a command test lays out an archive with `build_archive_env(tmp_path)` for the root and its marker. It builds each account's directory as `archive_root(env) / account_component(<config dir>)` from `_branch_records_helpers`, never through `_branch_records`, and PR A's parity test ties the module to the bash writer. It passes `build_archive_env` no `config_dir`, because `fake_projects` makes the active account's config dir `tmp_path` itself, which the helper's confinement assertion refuses (`_branch_records_helpers.py:121-122`).

**PR A.** Verify with `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py`.

Create:
- `claude/.claude/scripts/_branch_records.py`: the four functions, `ArchiveSubtree`, the five state constants, the root path and the sentinel name. Its docstring names `docs/agent-branch-records.md` § "Snapshots" as the layout's home and says the module never reads the key.
- `claude/.claude/scripts/tests/test__branch_records.py`, which puts the scripts directory on `sys.path` as `test__config_dir.py:9` does. Reuse `build_archive_env`, `run_status` and `SENTINEL_NAME` from `._branch_records_helpers`. Every marker comes from `build_archive_env`, never from the module's constant, so the `absent` and `present` cases tie the module's sentinel name to the lib's. The None cases, the state cases and the ValueError names are each one test parametrized over its inputs, with an id per case and the `requires_non_root` cases as marked parameters. Cases:
  - Parity, one case per config dir: a plain name, a name with a space, a name with `%`, a name holding a literal `%2F`, a non-ASCII name, a config dir reached through a symlink, and a root that is a resolving symlink, from `root_symlink_target`. Each asserts `ready` and compares `Path(run_status(...).account_dir)` with `account_directory(Path(env["CLAUDE_CONFIG_DIR"]), env["HOME"])` as `Path` objects. The test's docstring says it covers case-sensitive, non-normalizing filesystems only (row 58).
  - `archive_root` returns None for None, an empty home and a relative home.
  - `account_directory` returns None for an empty home, a relative config dir, a missing config dir and a config dir that is a file.
  - `present`:
    - a plain subtree;
    - a subtree for a config dir whose `claude-config.toml` sets the key to false (row 1);
    - a subtree under a root that is a resolving symlink, from `root_symlink_target` with `create_symlink_target=True`;
    - a subtree under a root whose marker is a symlink to a regular file, which the writer's `test -f` accepts (row 59).
  - `absent`: the marker exists and the subtree does not.
  - `unmarked`, built with `build_archive_env`:
    - no root, from `create_root=False`;
    - a dangling root link, from `root_symlink_target` with `create_symlink_target=False`;
    - a root that is a file, from `create_root=False` and a file written at the root path;
    - a root without its marker that still holds the subtree, from `create_sentinel=False`.
  - `unreadable`:
    - a subtree that is a file;
    - a subtree that is a symlink to a directory outside the account directory;
    - an account directory that is a symlink to a sibling account's directory;
    - an account directory that is a regular file;
    - a subtree symlinked into a sibling account whose encoded name extends this account directory's name as a string prefix;
    - a mode-0 root and a mode-0 account directory, each marked `requires_non_root`. Their docstring says that only a marker stat that finds nothing or a non-regular file gives `unmarked`, so a permission error gives `unreadable`.
  - `unresolvable`: a missing config dir.
  - ValueError for an empty name, `.`, `..`, a name holding `/`, and a name holding NUL.

**PR B.** Verify with the same command.

Create:
- `claude/.claude/scripts/transcript_analysis/review_ledger_copies.py`, as the Approach describes for PR B. It imports `_branch_records` and `scope` by module.
- `claude/.claude/scripts/tests/test_transcript_review_ledger_copies.py`. Every `read_ledger_file` case asserts `leading_copies_skipped` as well as the rows and their copy stamps. The file is about 340 lines after PR B and about 550 after PR E, under the 1,000-line limit (row 25). Cases:
  - copy-name parsing: a bad stamp and a stem without exactly one `.`, each skipped and counted;
  - grouping: a live-only stem, a copy-only stem, a stem with both with its copies in stamp order, and a live file with a two-dot name kept as its own stem;
  - a copy that is a leading run of the live file, skipped;
  - a copy that shares only its first row with the live file and then diverges, kept;
  - a copy whose rows overlap the live file in its middle, and one that overlaps at its end, each kept;
  - disjoint segments, concatenated in stamp order;
  - an empty copy before the live file, skipped;
  - an empty copy alone, and a copy-only stem's last copy, each kept with nothing to compare;
  - a copy cut mid-row and a copy cut at a row boundary, each skipped as a leading run;
  - an unread middle member, compared past;
  - a symlink and a FIFO named like a copy, each counted unread and never passed to `read_member`;
  - a `read_member` that raises `ValueError`, and one that raises `RecursionError`, each leave that member counted unread and the other members' rows kept;
  - `event_time_sort_key` returns a string `event_time` as it is, and `""` for a missing or non-string one;
  - `LedgerArchive`:
    - it maps each `archive_subtree` state, resolves a root once, and counts a stem read twice once;
    - two cases, each built with `build_archive_env`, where the stem has no live file but a copy of it exists under the root. In the first the state is `unmarked`, and in the second it is `unreadable` because the account directory is linked to a sibling account's directory. In each, `group_ledger_files` over the archive's listing and `read_ledger_file` give no copy and no row;
    - an unlistable copy directory turns the root into `unreadable`, marked `requires_non_root`;
    - with HOME unset, `_archive_home` returns `""` and a `LedgerArchive` built from it gives `unresolvable`. The test binds `_archive_home` at its module's import, before PR C's conftest pin replaces it for each test.
  - Real writer: `run_archive_ledger(..., in_ready_account=True)` archives a ledger file, the file grows, `os.utime` gives it a later stamp, and it is archived again. `LedgerArchive(home=env["HOME"])` then finds both copies under the right stem and reads one history with no repeats.
  - Real writer, mismatch: a `write_cp_shim` body, put on PATH with `shim_path_env`, runs the real `cp` and then appends one id-bearing row to the source.
    - `run_archive_ledger(..., in_ready_account=True)` reports the `LEDGER_COPY_MISMATCH` reason from `reason_variables()`, and its copy stays.
    - `os.utime` gives the grown source a later stamp, and a second call with the real `cp` archives it.
    - The stem then reads every row once, with `leading_copies_skipped=2`, so the skip handles the mismatch path (row 45).

Modify:
- `claude/.claude/scripts/transcript_analysis/author_outcome.py`: `_REVIEW_LEDGER_DIRNAME` and `_SESSION_ID_PATTERN` become aliases of the moved constants, `_event_time_sort_key` leaves for `review_ledger_copies.event_time_sort_key`, which its one call site calls, and the module imports `review_ledger_copies` by module.
- `claude/.claude/scripts/tests/test_transcript_package_module_prefixes.py`: `test_transcript_review_ledger_copies.py` in `TEST_FILES`, and `review_ledger_copies.py` in `PRODUCTION_MODULES` (row 50).
- `claude/.claude/scripts/select-tests.py` (M22, row 37):
  - a `BRANCH_RECORDS_MODULE` constant for `claude/.claude/scripts/_branch_records.py`, with a comment naming the import path through `review_ledger_copies`;
  - that constant in the predicates of the `HOOKS_TESTS_IMPORTING_TRANSCRIPT_ANALYSIS` row (`:1026`) and the `NUDGE_ERROR_MODE_ANALYSIS_TEST_PATH` row (`:1027-1031`);
  - the compaction row stays as it is, because `compaction-context.py` never imports the module.
- `claude/.claude/scripts/tests/test_select_tests.py`: `BRANCH_RECORDS_MODULE` in `_EXACT_MATCH_LITERAL_PATH_CONSTANTS` (`:2550`) and in the error-mode closure's parameters (`:1923-1932`), plus a case that it selects `test_review_ledger_script.py`.
- `code-file-size-exceptions.toml`: the ceilings of `claude/.claude/scripts/select-tests.py` and `claude/.claude/scripts/tests/test_select_tests.py`, set to the counts the check prints.
- `docs/transcript-analysis-architecture.md`: a `review_ledger_copies.py` section, and the `author_outcome.py` section's imports.

**PR C.** Verify with the same command.

Create:
- `claude/.claude/scripts/transcript_analysis/review_ledger_history.py`, as the Approach describes. Reuse `review_ledger_copies.group_ledger_files`, `read_ledger_file`, `event_time_sort_key` and `LedgerArchive`, and `scope._DO_NOT_PUBLISH_BANNER`. Its subparser's help text carries the three things the Approach lists.
- `claude/.claude/scripts/tests/test_transcript_review_ledger_history.py`. Cases:
  - rows print as JSON lines with every stored field, `finding`, `rationale` and `engineer_quote` included, and each carries `source_copy_stamp`, its copy's stamp or null for a live row;
  - two rows whose history order and `event_time` order disagree print in `event_time` order, and two rows with equal `event_time` keep history order;
  - a field holding `\n`, `\r`, U+2028 and a C1 control prints exactly one stdout line per row, counted with `str.splitlines()`;
  - a row holding ESC, U+202E, U+200B, U+FEFF, U+E0041 and U+1F600, once in a copy and once in the live file, gives stdout in which every character but the `\n` line terminator is printable ASCII (0x20-0x7e);
  - a stored `source_copy_stamp` of null and of a forged stamp, each in a copy row and in a live row, prints as the row's true stamp, or null for the live row;
  - stderr carries the banner and the header;
  - each of these stems exits 2, and a spy shows no `LedgerArchive` was built and no member read: `../x`, uppercase hex, no `.`, an extra `.`, a trailing newline, an embedded NUL, a glob character and fullwidth digits;
  - the grammar accepts a branch-keyed and a session-keyed stem taken from files a real `review-ledger.sh append` wrote, run as `TestReviewLedgerSubprocessIntegration._run_append` runs it (`test_author_outcome.py:1202`), with HOME under `tmp_path`;
  - copies of `<h>.abc-2` are not read for `<h>.abc`, and `<stem>.notastamp.jsonl` is skipped;
  - `cli.main()` with a top-level `--config-dir` naming an account other than the pinned one, each account holding distinct rows and copies, prints only the named account's rows;
  - a stem with no files prints `rows=0` and exits 0, with the archive `present`, `absent`, `unmarked` and `unresolvable`, and the header names each state. `unresolvable` comes from `_archive_home` returning an empty string;
  - a mode-0 copy directory, marked `requires_non_root`, prints `archive=unreadable` and the live rows, and exits 0;
  - a dangling copy symlink, a FIFO named like a copy, a directory named like a copy, and a FIFO and a symlink at the live path each exit 2 with no stdout. The FIFO cases run the command through conftest's FIFO deadline guard, so a regression that opens a FIFO fails the test instead of hanging it;
  - a mode-0 copy, marked `requires_non_root`, exits 1;
  - `review-ledger-history --help` holds one key phrase from each of the three statements the Approach lists, a presence check only.

Modify:
- `claude/.claude/scripts/transcript_analysis/ledger_dispositions.py`: `_read_member`, as the Approach describes. Rewrite the comment at `:148-149`, which bounds the rows held at once by the 30-day sweep, to say that an archived copy has no deletion bound (row 57). It changes in this PR because the viewer is the first caller to read copies through `_read_file_rows`.
- `claude/.claude/scripts/tests/test_transcript_ledger_dispositions.py`: `_read_member` returns a regular file's rows with True, and `([], False)` for a FIFO and for a symlink. Its FIFO deadline pattern (`:38-39`, `:750-759`) moves to `conftest.py`, and its existing FIFO case and the `_read_member` FIFO case call it there. The file stays under 1,000 lines (row 25).
- `claude/.claude/scripts/transcript_analysis/cli.py`: import and register `_add_review_ledger_history_subparser`.
- `claude/.claude/scripts/tests/test_transcript_cli.py`: `"review-ledger-history": {"--projects", "--this-repo"}` in `_SUBCOMMANDS_LACKING_A_SCOPE_FLAG` (`:351-357`, row 30).
- `claude/.claude/scripts/tests/test_transcript_package_module_prefixes.py`: `test_transcript_review_ledger_history.py` in `TEST_FILES`, and `review_ledger_history.py` in `PRODUCTION_MODULES` (row 50).
- `claude/.claude/scripts/tests/conftest.py`:
  - `_pin_transcript_corpus_lookups` also pins `review_ledger_copies._archive_home` under `tmp_path`, and its docstring says so;
  - a FIFO deadline guard, moved from `test_transcript_ledger_dispositions.py` with its 10-second deadline. It runs a call on a daemon thread, and when the call outlives the deadline it opens the FIFO's write end with `O_NONBLOCK` to release the reader and fails the test. It sits here because two test families use it, the viewer's and the dispositions' (`.claude/rules/transcript-analysis-tests.md`).
- `claude/.claude/scripts/tests/test_transcript_shared_fixtures.py`:
  - the pin test at `:13` also asserts the archive home lies under `tmp_path`;
  - `TestAutouseIsolationAppliesTheCorpusPin` (`:27`) asserts the same through the autouse path.
- `code-file-size-exceptions.toml`: the ceiling of `claude/.claude/scripts/tests/conftest.py`, set to the count the check prints.
- `docs/agent-branch-records.md`: the new § "Reading the archive", with the PR C parts the Approach lists. It writes `<config-dir>`, never a literal home path under `.claude`.
- `docs/transcript-analysis.md`:
  - a `## review-ledger-history` section with the stem grammar, the output, its order and its `source_copy_stamp` field, the header, the exit statuses, why it is repo-unscoped, and the three things its `--help` says. It also states the viewer's two departures from `show`: it prints no `source_repo_hash`, and it escapes with `ensure_ascii` where `show` applies `clean` (rows 55, 73);
  - a bullet in § "Corpus scope: the declared-roots file": it reads one stem from the active account's ledger directory and that account's archive, or from the account a top-level `--config-dir` names.
- `docs/transcript-analysis-architecture.md`: a `review_ledger_history.py` section, and `_read_member` in the `ledger_dispositions.py` section.
- `CHANGELOG.md`: one entry. `review-ledger-history` prints one ledger stem's live and archived rows.

**PR D.** Verify with the same command.

Modify:
- `claude/.claude/scripts/transcript_analysis/review_ledger_copies.py`: `LedgerIndex` and its helpers, moved from `author_outcome.py`, and `ledger_file_signature` and `archive_summary_line`, as the Approach describes for PR D.
- `claude/.claude/scripts/tests/test_transcript_review_ledger_copies.py`: `ledger_file_signature` changes when a copy is added, the summary line's exact text for `scope=all-repos`, and `LedgerIndex` cases, built with stub `list_live` and `read_member`:
  - a copy that opens beside a live file whose open fails is re-read on the next refresh, and the live rows then arrive once;
  - an unchanged `LedgerFile` with a copy is read once across two sessions, one read per member;
  - an unchanged copy-only `LedgerFile`, with `live` None, is read once across two refreshes, one read per member, so an absent live member is not retried as one that did not open;
  - a live file that grows mid-run is seen, and a copy added mid-run is not;
  - a session whose only file is an empty copy is not marked as having an opened file;
  - a copy whose reader raises is read once across two refreshes and stays counted unread.
- `claude/.claude/scripts/transcript_analysis/author_outcome.py`: as the Approach describes for PR D. Reuse `_list_ledger_files` and `_read_ledger_rows_from_file`. `_file_signature` and the moved helpers leave the file. Its module docstring's import sentence and ledger paragraph name the new module.
- `claude/.claude/scripts/tests/test_author_outcome.py`. Cases:
  - a session whose only file is an archived copy, `<repo hash>.<session>.<stamp>.jsonl`, gets its rows, is not counted as possibly swept, and counts under the copy-only key. The same corpus with no archive root counts it as possibly swept.
  - a session whose only file is an empty archived copy still counts as possibly swept;
  - the grouping control: with conftest's shared `event_time`, a copy that is a leading run of the live file gives one block per round and no mismatch;
  - with distinct, increasing `event_time`s, a copy that is a leading run of the live file and an `authoring_agent` the transcript contradicts count one inconsistency, not two;
  - a session with rounds 1 and 2 in a copy and round 1 in the live file counts under the round-number mismatch and not under "fewer blocks";
  - a command run with `_archive_home` monkeypatched to a `build_archive_env` home prints the archive line with `scope=all-repos present=1` before `Data quality`;
  - one test parametrized over `absent`, `unreadable` (a mode-0 copy directory, marked `requires_non_root`) and `unresolvable` (`_archive_home` returning `""`). Each gives the same outcomes and exit status as the run with the archive `unmarked`, and that state's field on the line is 1;
  - two declared roots under one archive root, each with a distinct copy-only session in its own account's directory: each session gets its rows only from its own account's copy, and the line prints `roots=2` with the five state counts summing to 2;
  - the copy-only key is not the last data-quality key;
  - a session whose rows come from a kept copy segment and a live file counts 0 under the copy-only key;
  - a copy-only session's round enters the outcomes, as FAILURE or PASS;
  - an archived copy holding an integer over the digit limit, under the `default_int_str_digit_limit` fixture, and one holding a deeply nested line each leave the command to complete, with both counted in `copies_unread`;
  - the same two contents in a live file instead each leave the command to complete with nothing on stderr, and the session counts as it would with no readable file;
  - a mode-0 copy, marked `requires_non_root`, prints one `author-outcome: couldn't read ledger file` line on stderr naming the copy, counts in `copies_unread`, and leaves the command to complete, the behavior Judgment calls chooses;
  - one command run whose corpus gives `copies_read`, `copies_unread`, `copy_names_skipped` and `stems_only_in_archive` four distinct values, with a copy skipped as a leading run among those read, asserted as parsed `key=value` pairs.
  Also update any exact-output assertion that the new line or key moves.
- `code-file-size-exceptions.toml`: the ceiling of `claude/.claude/scripts/tests/test_author_outcome.py`, set to the count the check prints.
- `docs/agent-branch-records.md`: the PR D parts the Approach lists.
- `docs/transcript-analysis.md`:
  - the pointer line in § "Corpus scope: the declared-roots file";
  - the `author-outcome` section's archive line, with every count in its sample elided to `N` as "What the commands print" gives, and what `scope=all-repos` means;
  - that a ledger file whose open raises `OSError`, an archived copy included, prints its path on stderr;
  - that a live file whose content raises `ValueError` or `RecursionError` prints nothing, adds no rows and is re-read on every session lookup;
  - its "Ledger lookup." paragraph (`:1802`): copies join each stem and are listed once per run;
  - its "Ledger-possibly-swept check." paragraph (`:1890`): a copy's rows clear a session, and an empty copy does not;
  - the copy-only data-quality key and the truncation bias it bounds.
- `docs/transcript-analysis-architecture.md`: `LedgerIndex` in the `review_ledger_copies.py` section, and the `author_outcome.py` section's imports.
- `CHANGELOG.md`: one entry. `author-outcome` reads archived ledger copies, with the key off too, and prints a `ledger archive:` line and a copy-only data-quality count.

**PR E.** Verify with the same command.

Create:
- `claude/.claude/scripts/tests/_ledger_dispositions_helpers.py`, the dispositions family's shared helpers (`.claude/rules/transcript-analysis-tests.md`). `_row`, `_terminal`, `_left_out`, `_BASELINE`, `_expect`, `_Ledger`, the `ledger` fixture and the window and disposition constants they use move here from `test_transcript_ledger_dispositions.py` (`:42-48` and `:121-159` on the base), keeping their names. Both dispositions test files import them, as `test_branch_records_archive.py` imports fixtures from `_branch_records_helpers.py`.
- `claude/.claude/scripts/tests/test_transcript_ledger_dispositions_archive.py`, the archive seam of a test file at 931 lines before PR C adds to it (row 25). Cases:
  - a copy that is a leading run of its live file counts each row once, through the skip;
  - a removed worktree's copy counts when a consistent manifest names this repo's main worktree, and another repo's copy does not;
  - a `LedgerFile` with an unread member counts as unreadable and adds no rows;
  - supersession across members: a copy holds an id-bearing disposition row X and the live file a row whose `ref` is X, so X is not terminal. A per-member `_tally_file` over the same two members counts X as terminal, the control;
  - the converse: when the live file holding the `ref` row is a FIFO, the stem counts as unreadable and X is not counted. It runs through conftest's FIFO deadline guard;
  - `archive=None` and a `present`, empty archive give equal counts;
  - real writer: `archive_successfully` writes a manifest for a worktree, its `ledger_repo_root` hashes to the file name `review-ledger.sh` writes there, and that file's copy counts, as `TestWriterToReader` does for live files (`test_transcript_ledger_dispositions.py:884`);
  - an unlistable copy directory leaves the live counts unchanged and turns the root into `unreadable`, marked `requires_non_root`.

Modify:
- `claude/.claude/scripts/_branch_records.py`: `snapshot_manifests`, `SnapshotManifests` and `SnapshotManifest`.
- `claude/.claude/scripts/tests/test__branch_records.py`: `snapshot_manifests` returns each manifest with its key directory. It returns `unreadable` and no manifest for an account directory linked to a sibling account's directory that holds a valid manifest. It returns `state` `unreadable` for a mode-0 `branches/` and for a mode-0 key directory, each marked `requires_non_root`. The mode-0 key directory sits between two key directories that each hold a valid manifest, one sorting before it and one after, and both come back. One test parametrized over these shapes, with an id per shape, puts each beside one valid manifest in a sibling key directory. It asserts that exactly the valid manifest comes back, and that nothing raises or prints on any stream:
  - a non-object manifest and an unparseable one;
  - invalid UTF-8;
  - a deeply nested document;
  - an over-limit integer, under the `default_int_str_digit_limit` fixture;
  - a file over 1 MiB;
  - a FIFO, a symlinked manifest, a symlinked key directory, a symlinked snapshot directory and a directory named `manifest.json`.
- `claude/.claude/scripts/transcript_analysis/review_ledger_copies.py`: `LedgerArchive` reads manifests per root through its own home, counts `past_worktrees`, takes the optional `select_copies` the Approach names, and marks a root `unreadable` on a copy-listing gap or a `branches` state of `unreadable`. `archive_summary_line` gains `past_worktrees`.
- `claude/.claude/scripts/tests/test_transcript_review_ledger_copies.py`: the `past_worktrees` field, the `scope=this-repo` line, a `branches` state of `unreadable` turning the root `unreadable`, and a `select_copies` that keeps one of two stems, after which every copy and stem count covers that stem alone.
- `claude/.claude/scripts/transcript_analysis/ledger_dispositions.py`: as the Approach describes for PR E.
  - Its module docstring says copies join each stem, supersession runs in history order, and a stem's whole history is held at once.
- `claude/.claude/scripts/transcript_analysis/publication_scope.py`: `_past_worktree_repo_hashes`, `_this_repo_ledger_files`'s `extra_repo_hashes`, and the identity sentence at `:69` extended to manifests.
- `claude/.claude/scripts/tests/test_transcript_publication_scope.py`. Cases:
  - a stored main path that equals a current path as printed, and one that equals it as resolved;
  - another repo's manifest, excluded;
  - this repo's main path with a foreign `ledger_repo_root` whose hash does not match its `ledger_key`, contributing nothing;
  - a key directory that differs from its `ledger_key`, contributing nothing;
  - a symlinked `ledger_repo_root`, contributing its hash as written only;
  - non-string fields skipped, duplicates collapsed, and current hashes not repeated;
  - a `ledger_repo_root` holding a lone surrogate that `os.fsencode` rejects, such as U+D800 (U+DC80 to U+DCFF encode under `surrogateescape` and would not exercise the skip), on a manifest that names this checkout's main path, skipped without raising, beside a consistent manifest that still contributes its hash.
- `claude/.claude/scripts/transcript_analysis/reviewer_reads.py`: the archive argument and the line in `_print_ledger`.
- `claude/.claude/scripts/tests/test_transcript_reviewer_reads_command.py`:
  - `TestOutputInvariant` (`:262-355`) gains one archive corpus in two layers.
    - This repo's layer holds a sentinel-named copy, a dangling copy symlink and a sentinel-valued manifest. Against a run with no archive, it moves the archive line's `copies_read`, `copies_unread` and `past_worktrees`, the positive controls.
    - The foreign layer holds another repo's malformed copy names, orphan copies, unreadable copies and manifest, and an unparseable manifest. Adding it leaves the archive line byte-identical.
    - In every run no sentinel reaches stdout, stderr, the log or warnings, and the line holds no path, stem or hash.
  - `test_a_declared_second_root_is_seen_by_no_reader` (`:176-210`) also gives the active account a marked, empty archive and the declared account an archive holding a copy named for this checkout's worktree hash and a consistent manifest naming this checkout's main path. Its count assertions stay. It also asserts the archive line whole, with `roots=1`, `copies_read=0` and `past_worktrees=0`, and that stderr equals a run of the same corpus without the declared account's archive.
  - A `present` archive prints the line after `ledger files:`.
  - A mode-0 `branches/`, marked `requires_non_root`, prints `present=0` and `unreadable=1` and leaves the live and copy counts unchanged.
  - One run whose corpus gives `copies_read`, `copies_unread`, `copy_names_skipped`, `stems_only_in_archive` and `past_worktrees` distinct values prints them, asserted as parsed `key=value` pairs.
  - A new subprocess case, if any, sets HOME under `tmp_path`, as `:628-637` does, because the conftest pin cannot reach a child process (row 24).
- `claude/.claude/scripts/tests/test_transcript_package_module_prefixes.py`: `test_transcript_ledger_dispositions_archive.py` in `TEST_FILES`.
- `docs/agent-branch-records.md`: the `reviewer-reads` parts the Approach lists.
- `docs/private-project-redaction.md`, the `reviewer-reads --this-repo` entry (`:148-168`):
  - it reads the active config directory and that account's archive directory alone, and the writer follows a link at an account directory, so a linked account's archive directory can hold this repository's copies for another account (row 74). In the archive it reads ledger copies and opens every snapshot manifest on the account, other repositories' included, and prints nothing from any manifest;
  - its ledger section also opens archived copies, by the same `lstat` check. It selects files named for a current worktree path, or for the `ledger_repo_root` of a manifest that agrees with its own location and whose stored main path equals a current worktree path of this checkout, as printed or as resolved;
  - the entry also says that manifests are unauthenticated same-user files, so a hand-written self-consistent manifest can add any repository's hash, and that the manifest opens carry the same point-in-time `lstat`-to-open limit as the ledger files;
  - the archive line's `roots` and five state fields describe the account's archive as a whole, so `unreadable` can come from another repository's directory under `branches/` or from a failed copy listing. The resolver's containment check is point-in-time, as the `lstat` check is. Every other count on the line covers only the selected files;
  - the path-identity sentence (`:158-166`) also names a removed worktree found through a manifest. Either that worktree's own path or the manifest's stored main path can have been another repository's checkout before or after this one. That sentence becomes the docs' one statement of the path-identity limit (row 67).
- `docs/transcript-analysis.md`:
  - the `reviewer-reads` bullet in § "Corpus scope: the declared-roots file" (`:92`) adds the account's archived ledger copies and snapshot manifests;
  - the section's description of what it reads (`:1657`);
  - the **Scope.** sentence at `:1659`, rewritten to say the ledger half also counts removed worktrees found through manifests, whose transcripts the transcript half does not read;
  - the "Review-ledger dispositions." paragraph (`:1751-1756`): copies join each stem, supersession runs in history order, a stem with an unread member is unreadable, and `read` and `unreadable` count stems;
  - its archive line, with every count in its sample elided to `N` and a note that `roots` and the five state fields describe the account's archive as a whole while every other count covers the selected files, the removed-worktree rule with its reason, and the skipped-manifest cause beside that rule;
  - its "Known limits" paragraph (`:1771-1774`). The path-identity bullet (`:1772`) becomes a pointer to the redaction doc's path-identity sentence. The removed-worktree bullet (`:1773`) says a removed worktree's ledger files count when a consistent manifest ties it to this checkout, and its sessions still do not. `docs/case-studies/reviewer-read-field-baseline.md:253` already sends readers to both docs, so the dated case study stays unchanged.
- `docs/transcript-analysis-architecture.md`: the `ledger_dispositions.py`, `publication_scope.py` and `reviewer_reads.py` sections.
- `CHANGELOG.md`: one entry. `reviewer-reads` counts this repo's archived copies and its removed worktrees' files when a consistent snapshot manifest names them.

Projected diff: about 3,000 changed lines, additions plus deletions. It is an estimate derived from the planned edits, not counted from a diff: PR A about 280, PR B about 580, PR C about 615, PR D about 745 and PR E about 790. About 180 of those lines move existing test code, the FIFO deadline guard into `conftest.py` and the dispositions helpers into `_ledger_dispositions_helpers.py`. Row 72 approved this size, superseding rows 66 and 68 on size.

## Verification

For every PR:
- `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py`:
  - it passes, and its selection includes the PR's new test files;
  - from PR B on, a change to `_branch_records.py` also selects `test_review_ledger_script.py` and `test_nudge_error_mode_analysis.py` (M22);
  - if it reports a path it cannot map, stop and raise it, because that is a rule-table bug outside each PR's file list (row 37).
- `scripts/venv-run.sh ruff check claude/.claude/ claude-skills/ plugins/ evals/` passes.
- `claude/.claude/tests/test_code_file_size.py` passes, so every file the PR grows is under 1,000 lines or on its exact ceiling (row 25).

PR A:
- The parity cases include a config dir name holding a literal `%2F`, whose expected value changes if the two replacements run in the other order, and a config dir reached through a symlink.
- On an account with `agent_branch_records` on, `account_directory` for the active config dir equals the directory `review-ledger.sh clear-stale --dry-run` prints in its `Archive: ready (...)` line. Run it locally only, and paste no path into a commit, PR body or plan.

PR B:
- No command builds a `LedgerArchive` yet: a Grep of `claude/.claude/scripts/transcript_analysis/` for `LedgerArchive(` matches no file but `review_ledger_copies.py`.

PR C:
- Give a scratch HOME an archive root with its marker and one stamped copy of a stem, laid out as `build_archive_env` lays them out, and give the scratch config dir a live file for the same stem whose rows are newer than the copy's.
  - `review-ledger-history <stem>` prints the copy's rows with its stamp and then the live rows with `source_copy_stamp` null, every stored field included, and exits 0.
  - `review-ledger-history ../x` exits 2.
  - The same stem with HOME at a scratch directory that holds no archive root prints `archive=unmarked` in its header and only the live rows, and exits 0.

PR D:
- `author_outcome.py` has at most 1,000 lines, about 950 by the Approach's estimate.
- Build a synthetic corpus as `docs/transcript-analysis.md` § "Testing against a synthetic corpus" describes, with HOME set to a scratch directory that holds an archive root and its sentinel. Give one session a code-review round older than 30 days, and leave its ledger file only as a stamped copy in the archive.
  - `author-outcome` prints `scope=all-repos`, `present=1` and `stems_only_in_archive=1`. It counts 0 possibly-swept sessions and 1 session under the copy-only key.
  - Run again with HOME at a scratch directory that holds no archive root: it prints `unmarked=1`, counts 1 possibly-swept session and 0 under the copy-only key.
  - Empty the copy and run again with the archive: it counts 1 possibly-swept session.

PR E:
- In a scratch repository, give the scratch archive a copy named for a removed worktree's path and a consistent manifest whose `main_worktree_path` is the repository's own.
  - `reviewer-reads --this-repo` prints `scope=this-repo`, `past_worktrees=1` and `copies_read=1`, and its ledger figures include the copy's rows.
  - Change the manifest's `ledger_repo_root` to another path and run again: it prints `past_worktrees=0` and leaves those rows out.
  - Run again with HOME at a scratch directory that holds no archive root: it prints `unmarked=1` and `copies_read=0`, and its ledger figures leave those rows out.
- `test_transcript_reviewer_reads_report.py`'s whole-report test passes unchanged.

## Out of scope

- Reading `agent-reviews/` snapshots: no analysis reads `agent-reviews/` (row 13), so no reader exists to extend.
- Retiring the `agent-reviews/` snapshot: a separate later change, as the Context records.
- Restoring archived files when a worktree is recreated (row 10).
- Any change to `show`, `render`, `/code-review`, the dashboard or the review-history hook (row 61). That includes a pointer to the archive in `show`'s no-ledger notice, which prints on `show`'s stdout (row 29). The Context records what a live-tool fallback would break, as the design reviews reported it.
- A hook, skill-body line, rule file or `CLAUDE.md` line that points an agent's ad hoc reads of `<config-dir>/review-narrative-ledger/` at the archive. This plan makes the analysis commands read copies without any agent action, and the new doc section names them (row 38).
- Transcript readers and the sibling session's PR 3 (G3, row 9). Those readers can call `archive_subtree(config_dir, "projects", home)`.
- Widening `reviewer-reads`' transcript half to removed worktrees' project directories. Those transcripts are not archived until the sibling session's work lands (G3), and the doc states the gap (row 53).
- Relabelling `reviewer-reads`' ledger-section heading or its `ledger files:` line. The golden report test pins both, and the doc states that the counts now include removed worktrees and count stems.
- Renumbering rounds across segments, for the reason Judgment calls gives.
- Closing the mid-run sweep race in `author-outcome`'s index. A live file swept between two session lookups already loses its rows for the later lookups, and the copies listed at the run's start do not hold the copy that sweep makes. A re-run counts the stem through that copy.
- A regular-file check on `author-outcome`'s live ledger files. The archive does not change how it reads them.
- A parity case on a case-insensitive or normalizing filesystem. CI runs on Linux only (row 58), so the parity test's docstring states the limit.
- Windowing `left_out_by_field` or `reviewer-reads`' other un-windowed counts. Their label already says they cover every row whatever its date, and windowing them would change the command's published output apart from the archive.
- A time cap on archive reads, or a flag that turns them off (M13, row 42).
- A torn-line count, and counts of other repos' stems or of skipped manifests in `reviewer-reads`. The Alternatives give each reason.
- Moving the existing `TestLedgerIndex` tests out of `test_author_outcome.py`. They reach the moved class through `ao._LedgerIndex`, and moving them is a refactor this change does not need.
- Splitting `test_author_outcome.py`, `scope.py`, `select-tests.py` or `test_select_tests.py`, which the exception table already lists as split pending.
- Pruning the archive, which stays manual (`docs/agent-branch-records.md:122`).
- Telling apart a path another repository's checkout occupied before or after this repo's worktree, by a root-commit manifest field or a row-identity change. The engineer selected "Documented limit, follow-up later (Recommended)" (row 67), and a manifest field is a writer change (G1).
