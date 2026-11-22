# Shell parser for the hook command tokenizers

## Context

Decide whether a real shell parser should replace the hand-rolled command tokenizers behind the hooks, and if one should, which one and how every stow consumer gets it.

Ask: "if prsing commands would be more robust with a proper shell parser, that might be worth the extra install. we'd jsut add it to install.sh rather than install-dev.sh" and "you'll consider the various alternatives?"

**Problem.** Two scripts tokenize the Bash command a hook is judging: `claude/.claude/hooks/split-command-words.py` and `claude/.claude/hooks/parse-git-command.py`. Both build on stdlib `shlex` plus their own heredoc, comment, and quote handling. The splitter's docstring lists valid bash it rejects (an over-deny) and words it drops that bash keeps (a miss). A miss hides a flag from the calling gate, and the callers include the redaction gates that guard a public repository.

**Why now.** A benchmark plan in another session raised whether shell parsing in this repo should stay hand-rolled. That plan keeps bash's own `declare -F` for function spans. The same question applied to the hooks has a different answer shape, because the hooks run on every stow consumer's machine and their failures can leak.

**Intended outcome.** A plan that compares the alternatives against the splitter's documented residual cases and picks one. The alternatives are a parser binary, a parser library, patching the `shlex` tokenizers, and narrowing what the gates need to read. If a parser wins, the plan names how `install.sh` requires it, which tokenizer code it replaces, and what stays.

## Approach

Replace both hand-rolled tokenizers with shfmt's bash parser, in two ordered PRs, one per tokenizer. Every command that reaches `_lib_command_words` or the worktree gate's parser goes through `shfmt -ln bash --to-json`. One stdlib-only Python module checks the syntax tree strictly, then projects it into the flag words the three redaction gates read and the CD/GIT records the worktree gate reads. "Two PRs" below lists what each PR carries. The gates parse bash only. The Bash tool can run zsh (row 15), and the engineer accepted that gap as a recorded residual (row 106).

At run time, a missing shfmt, an oversized command, or a tree the module does not recognize denies, and the deny names the cause. One warn-only SessionStart hook diagnoses the parse path's dependencies, python3 and shfmt alike, so no gate header restates them (rows 76-77, 94). That hook is `check-python-floor.sh`, renamed `check-hook-dependencies.sh` and extended to shfmt. It also warns when neither `timeout` nor `gtimeout` is on PATH, because a hung parse tool then stalls each gated command until the harness's hook timeout (row 111). Under Cursor, the adapter's sessionStart report runs the same shfmt check (row 95). A consumer who pulls before installing shfmt is locked out of the commands these gates parse until they install it, and the engineer accepted that lockout (row 6). From PR 1, the notice names the cause at the next session start or resume.

### Alternatives weighed

Each candidate was judged against three things: the nine shapes `TestResidualShapes` pins (`claude/.claude/hooks/tests/test_split_command_words.py:363`), the worktree parser's newline and heredoc misses (row 17), and the cost to every stow consumer.

- **Parser binary: shfmt (chosen).** It exits nonzero on invalid bash, ships as one static binary, and parsed all nine shapes into the words bash sees (rows 7-9). The plan carries each of its costs:
  - It is a hard dependency that Debian stable and Ubuntu 24.04 do not package at the floor (Given 3).
  - Its JSON carries no stability promise (Given 2).
  - It costs about 30 ms per parse (row 20).
  - A consumer who pulls before installing it is locked out of the commands these gates parse (row 6, Design item 9).
- **Parser library: tree-sitter-bash.** Set aside.
  - It is error-tolerant: it returns a tree with ERROR nodes instead of failing, so every gate would have to find them.
  - Its open heredoc mis-parses are the residual class this change exists to close.
  - Its compiled wheels are not importable by a gate that runs `python3 -I -S` without path plumbing (rows 10-11).
- **Parser library: bashlex.** Set aside. It is licensed GPL version 3 or later and has had no commit since 2024-04-08. Its README and issues exclude `$((..))` and `$'...'`, two of the nine shapes (row 10).
- **Parser binary: Oils `osh`.** Set aside. No primary source confirmed a parse-only tree output, and consumers would build it from a tarball (row 10).
- **bash itself.** Set aside. `bash -n` prints no tree, and canonicalizing through bash runs command substitutions inside the gate (row 13).
- **Patching the shlex tokenizers.** Set aside as a wrong foundation. The splitter's docstring (`claude/.claude/hooks/split-command-words.py:24-63`) lists the divergences and residuals the earlier pre-pass patches left. Every remaining residual comes from a pre-pass that runs before quote state is known. Closing them means tracking quotes, comments, heredocs, `$(...)`, backticks and `$((...))` in one pass. That is a hand-rolled bash lexer, which `claude/.claude/CLAUDE.md` § "Engineering Judgment" ("Hand-rolled logic in non-trivial domains") steers away from.
- **Narrowing what the gates read.** Its strongest form denies whenever `xargs -n1` fails and the raw text holds a source-flag word. Set aside:
  - It turns the splitter's misses into denies, but keeps the fast path's own miss (row 19).
  - It does nothing for the worktree gate's misses (row 17).
  - It stacks one more quote-blind matcher on xargs.
  - It denies any multi-line commit or PR value that mentions `-F` or `--body-file`.

### Two PRs

The engineer chose two ordered PRs, one per tokenizer (row 46). Neither projects under 400 changed lines (row 72).

- **PR 1, the redaction gates.** It carries Design items 1, 3, 6, 7, 8, 11 and 12, item 2's strict check, walker, word flattening and `words` projection, and PR 1's parts of items 9 and 10. It deletes `split-command-words.py`.
  - Its session step after Dispatch 1 puts the marked rows of the `words` differential table, verdict and path-string changes alike, to the engineer (Verification 1, row 108).
  - Status 8 lands here, because `_lib_shell_parse` is the first shfmt caller and must classify every shfmt exit.
  - The install check, the SessionStart check, CI's pinned build, and the Cursor adapter's PATH and shfmt check land here, because this is the first PR whose gates call shfmt (row 75).
- **PR 2, the worktree gate and the evaluator.** It carries item 2's `git-records` projection and evaluator interface, items 4 and 5, and PR 2's parts of items 9 and 10. It deletes `parse-git-command.py`.
  - Its first step builds the table of changed worktree-parser cases for the engineer to review.
  - It branches from the default tip once PR 1 merges, because it builds on PR 1's `_lib_shell_parse`, module and CI pin, and PR 1's review can still change them. It does not wait for PR 1 to gain field time (row 107).
- **Between the PRs**, the repo runs two tokenizers, as it does today.
  - The redaction gates parse with shfmt, and the worktree gate and the evaluator keep `parse-git-command.py`.
  - The module holds no git-records code until PR 2 moves the classifiers into it, so on the default branch they sit in one file at every point.
  - A consumer who installed shfmt for PR 1 needs nothing new for PR 2.

### Design

1. **One parse path in `claude/.claude/hooks/_lib.sh` (PR 1).** It adds a parse function, two functions that word a failure, the deny reason's composition, and one named array.
   - **`_lib_shell_parse CMD PROJECTION [CAP_SECONDS]`.** PROJECTION names one of the module's projections and reaches the module unchanged, so PR 2 adds `git-records` without editing `_lib.sh`. CAP_SECONDS defaults to `_lib_capped`'s 5 (`_lib.sh:50-51`), so the gates pass two arguments and only the shared shfmt check passes a third (Design item 12, row 110). It runs these steps in order:
     1. It returns `_LIB_SHELL_PARSE_OVERSIZE_STATUS` (7) when CMD exceeds `_LIB_SHELL_PARSE_MAX_BYTES` (65536). It counts bytes under `LC_ALL=C` before any process starts (rows 30-31).
     2. It returns `_LIB_SHELL_PARSE_NO_PYTHON3_STATUS` (127) when `command -v python3` fails. It checks python3 before shfmt, so every gate and the SessionStart hook name the same tool on a machine missing both (row 109). 127 is what the python3 call itself returns when python3 is absent, so one clause and one recovery item cover both.
     3. It returns `_LIB_SHELL_PARSE_NO_SHFMT_STATUS` (6) when `command -v shfmt` fails.
     4. It keeps the existing not-linked check, retargeted at the module through `_lib_shell_syntax_tree_path`. That is today's `_lib_command_words_tokenizer_path`, renamed, with its readlink hop kept.
     5. It runs one pipeline: `printf '%s' "$CMD" | _lib_capped_for CAP shfmt | _lib_capped_for CAP python3 -I -S <module> PROJECTION`, where `shfmt` stands for `"${_LIB_SHFMT_ARGV[@]}"` (row 59).
        - Every stage discards stderr, because shfmt's parse message can quote the command.
        - The JSON goes straight from shfmt to python3. No shell variable holds it, and no here-string writes it to a temp file.
        - Both caps start with the pipeline, and python3 cannot finish before shfmt does, so the whole parse shares one cap rather than two in sequence.
     6. It reads shfmt's and python3's statuses from `PIPESTATUS`. The first case that matches gives the status it returns (row 59):
        1. shfmt 0: python3's status, unchanged.
        2. shfmt 141, death by SIGPIPE, beside a nonzero python3 status: python3's status, because python3 closed the pipe first.
        3. A shfmt cap-kill status: that status, unchanged.
        4. shfmt 1, its syntax error: 3.
        5. Any other nonzero shfmt status, a 141 beside python3's 0 included: `_LIB_SHELL_PARSE_SHFMT_FAULT_STATUS` (8).

        Mapping exit 1 to 3 keeps 3's "could not be tokenized" lead.
   - **Its stdout.** python3 can print words before shfmt's status is known, so the output holds usable words only on status 0. Every caller captures it with `$(...)` and discards it on a nonzero status. `_lib_command_words` prints what it captured only on status 0, so its "nonzero with nothing printed" contract (`_lib.sh:2561`) still holds.
   - **`_LIB_SHFMT_ARGV`** is a named array. Every test that runs real shfmt takes its argv by sourcing `_lib.sh`, so no test parses with a command the gates do not run. PR 2's Python copy is Design item 2's.
   - **`_lib_shell_parse_failure_clause STATUS`** gives each status its wording. It is today's `_lib_command_words_failure_clause`, renamed in PR 1 because the worktree gate uses it from PR 2 on. Every clause names a cause, so no parse failure denies without one (row 76).
     - A clause states the cause only. It carries no instruction, no "this gate" wording and no citation, so the SessionStart hook and the Cursor report reuse it unchanged (row 103). Today's not-linked clause at `_lib.sh:2600` loses its "stop and ask" tail.
     - The clause for 3 says shfmt rejected the command as invalid bash. It drops today's xargs and 2 MiB wording.
     - The oversize clause, for 7, names the cap.
     - The clause for 8 says shfmt failed in the parse step.
     - The clauses for 5 and 6 name a tree the module does not recognize and a shfmt not on PATH.
     - The clauses for 2 and 127 also name the extraction step's awk, because the source-path extractors return awk's own status through the same deny reason (`_lib.sh:2643-2648`, `:2661-2666`). The clause for 2 names a fault in the projection module or awk. The clause for 127 names a python3 or awk not on PATH or not runnable.
     - The cap-kill clause says shfmt or python3 was killed by the parse cap or a signal.
     - The clause for 9, the probe's mismatch (Design item 12), says shfmt's tree for a known command no longer projects to the expected words.
     - Any other status takes the default clause: a tool in the parse or extraction step failed, with its exit status. It names python3, its cap wrapper, awk, and the temp file awk's here-string can need, as today's default arm names python3, awk and that temp file (`_lib.sh:2608`). It drops that arm's "check that each runs" instruction.
   - **`_lib_shell_parse_tool_fault_sentence STATUS`** prints one sentence that tells the agent to stop and ask and cites `docs/hooks.md` § "Gate deadlock recovery".
     - It prints it for every status except 3, 4 and 7. `_lib_capped_for`'s header reads any status a caller does not recognise as the child's or the wrapper's own failure, and requires the caller to fail closed on it (`_lib.sh:117-120`). An unlisted status, such as python3's own 1, 126 or 139, is therefore a tool fault by default.
     - It also prints it, whatever the status, when the module is not linked.
     - The recovery entry gives the human a diagnostic and a fix for each listed status, and one for the default arm (Design item 9).
   - **`_lib_command_words_deny_reason`** composes the clause with one of three tails:
     - The file workaround, for statuses 3 and 7, because the command can cause them. Content moved to a file brings an oversized command back under the cap.
     - Neither the workaround nor the tool-fault sentence, for status 4, as today.
     - The tool-fault sentence and no workaround, for every other status and for the not-linked case at any status, as today's reason omits the workaround then (`_lib.sh:2625`). That now covers 127 and the module's own 2, because without the `xargs -n1` fast path python3 runs on every parsed command (row 59). It covers a cap kill, because a hung tool is the likelier cause than the command itself (row 102).

     Two rules hold across the tails:
     - The workaround sentence drops its "multi-line or nested-quoted" wording, because shfmt parses both.
     - No clause or reason echoes the command or a tool's stderr, as the comment above `_lib_command_words_deny_reason` guarantees today.
2. **The projection module `claude/.claude/hooks/shell-syntax-tree.py`** replaces `split-command-words.py` in PR 1 and `parse-git-command.py` in PR 2.
   - **Interface.** It reads shfmt's JSON on stdin, and `argv[1]` picks the projection. It exits 0 on success, 2 on an internal fault or bad usage, and 5 when the tree is not recognized. It never exits 1, as today. PR 1 ships `words` only, so `git-records` is bad usage until PR 2 adds it.
     - It prints nothing unless it exits 0. The projection buffers its output, because the conservation count runs after it.
     - It reads `sys.stdin.buffer` and decodes it as UTF-8, and it writes its words to `sys.stdout.buffer` as UTF-8, so the locale changes neither. The docstring states both. Whether shfmt's JSON keeps a non-UTF-8 byte of a word is row 113's question.
     - A top-level handler maps a `RecursionError` from `json.loads` on deep nesting, and any other exception, to 2.
     - The walker uses an explicit stack, not recursion.
     - The strict check raises `TreeNotRecognized`, which the command line maps to 5.
     - For the evaluator, PR 2 adds `SHFMT_ARGV`, `MAX_COMMAND_BYTES`, `FIELD_SEP` and a pure `git-records` function over a parsed tree. `SHFMT_ARGV` and `MAX_COMMAND_BYTES` are the second copies of `_LIB_SHFMT_ARGV` and `_LIB_SHELL_PARSE_MAX_BYTES`, which the evaluator needs from Python. A PR 2 test pins each pair equal, under CLAUDE.md's small-duplicated-value exception.
   - **Strict check.** The module exits 5 unless all of these hold (row 24), so under Given 2 a renamed field shows up as an unknown key whenever it holds a value, and a new construct or a re-encoded operator denies instead of projecting to no words. Every condition but the last is checked before either projection runs, and the last after it.
     - The root is an object of type `File`.
     - Every `Type` is in `KNOWN_NODE_TYPES`.
     - Every `BinaryCmd` operator is in `KNOWN_BINARY_OPERATORS`.
     - Every object's keys fall within the key set of the Go struct it encodes. A typed object is matched by its `Type`, and an untyped one by the type and field that hold it.
     - Every key its struct always carries is present.
     - The number of `CallExpr` nodes the projection visited equals a raw count of `CallExpr` objects in the tree.

     Where the check's sets come from, and its scope:
     - **Sources**, one per set:
       - The operators and per-struct key sets come from the published `mvdan.cc/sh/v3/syntax` package at v3.14.0.
       - `KNOWN_NODE_TYPES` is that package's type list minus `BASH_REJECTED_NODE_TYPES`.
       - `BASH_REJECTED_NODE_TYPES` is a named set of dialect-only types that `-ln bash` rejects, such as `TestDecl` (row 86).
       - Each struct's always-present keys come from Dispatch 1's dump of that struct's smallest input. For `File`, the smallest inputs are an empty command and a comment-only command (row 26).
       - The conformance corpus confirms every set against real shfmt.
     - **Scope.** The whole check lands in PR 1, including node types only `git-records` reads. The engineer kept it as it stands (row 74).
   - **Word flattening, shared by both projections.**
     - A `Lit` part contributes its value, decoded as the last bullet below says.
     - A `SglQuoted` part without `Dollar` contributes its value verbatim.
     - A `DblQuoted` part without `Dollar` contributes its `Lit` parts, and each other part inside it as the placeholder bullet below says.
     - A part of any other kind, inside double quotes or not, contributes a fixed placeholder that begins with `$`. The literal parts on both sides of it keep their text (row 27).
       - The other kinds are parameter, command, arithmetic and process substitutions, `$'...'`, `$"..."` and extglobs.
       - So `--body-file="$F"` yields `--body-file=` and the placeholder, `-f body=@"$F"` yields `body=@` and the placeholder, and `$HOME/bin/git` keeps its `/git` suffix (row 9).
       - A caller extracts a path holding the placeholder and denies it as unreadable, as it denies a literal `$F` today (row 28).
       - `_needs_expansion` reads the `$` as needing expansion.
     - `Lit` values keep their backslashes (row 26), so the module always decodes them by bash's two rules: the unquoted escape character and the double-quote escapes. Quote the Bash Reference Manual sections in the code comment.
       - Dispatch 1's dump at 3.14.0 confirms the raw form. A dump that shows decoded values contradicts row 26 and stops the session.
       - Dispatch 1's commit message justifies hand-rolling the decoder, naming the standard-library alternatives checked and why each fails, per `claude/.claude/CLAUDE.md` § "Engineering Judgment" ("Hand-rolled logic in non-trivial domains").
   - **Traversal, shared by both projections.** The walker descends every list and object value of every node, not a field allow-list (row 56). It therefore reaches a command nested in an assignment value, a declaration argument, a redirect target, an unquoted heredoc body, a process substitution, a `for` word list, `[[ ]]`, `(( ))`, a parameter default or an array element (row 57). Quoted heredoc bodies and comments hold no command nodes.
   - **`words` (PR 1).** Each `CallExpr`, in the order the JSON lists them, contributes its `Args` words, then one blank line (row 29). Assignments, redirect words and heredoc bodies contribute no words of their own, only the commands nested in them. A newline inside a word becomes a space, as today.
   - **`git-records` (PR 2).** The record grammar stays byte-identical, so the bash consumer from `require-worktree-for-git-writes.sh:311` onward does not change.
     - A newline inside a word stays, so `_contains_wire_delimiter` still yields a SENTINEL.
     - A simple command's segment is its `Args` words. Assignments and redirects are no longer tokens of it, which is the source of the deny-to-allow rows in Dispatch 6's table.
     - Top-level statements, taken in order, are plain segments. The first gets preceding-op `START`. A later one gets `;` after a newline or `;`, and `&` after a backgrounded statement.
     - A `BinaryCmd` passes its incoming op to its left side and its own op to its right. `|&` reads as `|`.
     - In-group has one meaning per record type, and the module docstring states both (row 85):
       - On a GIT record, 1 means the write's cwd cannot be judged, so the consumer denies any non-read (`require-worktree-for-git-writes.sh:395-397`).
       - On a CD record, 1 means "not threaded". The consumer stops resolving the cwd at that record, so every later write denies (`:354-360`, row 65). The consumer ignores such a record's target.
     - GIT records:
       - A git command keeps in-group 0, and is judged at the running cwd, inside `{ }`, `time`, `!`, a pipe side, and the condition or body of `if`, `while`, `until`, `for`, `select` and `case` (rows 64, 87).
       - Subshells, coprocesses, command and process substitutions, backticks and function bodies give every nested record in-group 1.
     - CD records. A `cd` is threaded only where the old parser threaded it and bash certainly ran it in the parent shell:
       - A plain `cd`, one with no assignment prefix, that is a top-level statement or the leftmost operand of a top-level `&&` or `||` list threads for the rest of the command.
       - A plain `cd` that is a later `&&` operand of a top-level list threads for the rest of that list. Where the list ends, the projection emits an in-group-1 CD record, so the statements after it see an unresolved cwd.
       - Every other `cd` emits in-group 1:
         - List operators: the right operand of `||`.
         - Pipes and background: a pipe side, and a backgrounded statement with everything nested in it.
         - Grouping: a subshell, a command or process substitution, backticks, a function body, and anything inside `{ }`, `time` or `!`.
         - Conditionals and loops: anything inside an `if`, `while`, `until`, `for`, `select` or `case`.
       - `FOO=x cd`, `builtin cd`, `command cd`, `pushd` and `popd` emit an in-group-1 CD record wherever they stand.
       - A loop whose condition or body holds any `cd` form emits an in-group-1 CD record before its own first record, because a later iteration starts at the cwd an earlier one left.
     - Under these rules no `cd` shape turns from deny to allow against the old parser. Verification 3's differential table checks that.
     - A simple command's nested statements emit before its own record, in the order bash runs them.
     - `classify_cd_segment`, `classify_git_segment`, `_needs_expansion`, `_contains_wire_delimiter`, `_is_literal_git_version_query`, `GIT_FLAGS_WITH_ARG`, `FIELD_SEP` and `emit_segment` carry over verbatim. The in-group-1 CD records the rules above add go through `emit_segment` too, so the record grammar does not change.
     - The unbalanced-quote, unbalanced-group and unterminated-heredoc SENTINELs give way to shfmt's syntax-error exit, which `_lib_shell_parse` turns into status 3.
   - **Isolation.** The splitter's interpreter-isolation and capability-pin tests carry over to the module. `json` is stdlib and outside the pin. They move to the contract test file, which needs no shfmt, so they never skip.
3. **`_lib_command_words` (PR 1)** becomes `_lib_shell_parse "$1" words` plus the existing no-words check (status 4), which now counts only non-blank words. It prints the words it captured only on status 0 (Design item 1). The `xargs -n1` fast path goes (rows 18-20), so the output carries no xargs prefix. The extractors and the gh-api callers do not change, because they already skip a blank path (row 28).
4. **The worktree gate (PR 2).** The parser call at `require-worktree-for-git-writes.sh:293-309` becomes `_lib_shell_parse "$COMMAND" git-records`. Its deny pairs the shared clause with the tool-fault sentence (Design item 1).
   - The existing python3 presence check stays first, matching `_lib_shell_parse`'s own order (row 109), so every gate tells a machine missing both tools about python3.
   - For status 6, the deny adds the self-locked-worktree escape hatch that the python3 deny names.
   - The fast path's relocation check at :273 matches `pushd` and `popd` as well as `cd`, so a worktree session's `pushd /main && git push` reaches the parser (row 104).
   - The write deny at :396 adds a `cd` whose effect is uncertain to its list of causes. Its remedy, a literal `cd <worktree-path> && git ...`, stays.
   - The header changes in the places below. None of them lists the parse path's tools or how to repair one, because the SessionStart notice and the recovery entry hold that diagnosis (rows 77, 84).
     - The Mechanism paragraph says the gate parses through `_lib_shell_parse`, and cites the module for the record grammar and the in-group rules. Its list of what keeps a resolution from being clean adds a `cd` whose effect is uncertain.
     - The precondition paragraph becomes one line: any parse failure denies with a reason that names the cause, and `docs/hooks.md` § "Gate deadlock recovery" gives the recovery.
     - Known gaps close: the newline, same-line-heredoc and no-size-cap gaps.
     - Known gaps added, one line each:
       - An over-cap command denies.
       - A quote-split `git`, such as `g\it` or `gi""t`, leaves the command without a contiguous `git`, so the prefilter at :223 allows it before any parse (row 105).
       - With the session's lock held, a quote-split `cd`, `pushd`, `popd` or `-C`, such as `c\d /main && git push`, skips the parse at :273-276, so its write is judged at the session's cwd. This pre-dates the change.
       - The gate reads none of `--git-dir`, `--work-tree`, `GIT_DIR=` or `env -C` as a relocation, so a write they point elsewhere is judged at the running cwd. The parser reads `--git-dir` and `--work-tree` only as flags that consume the next word (`parse-git-command.py:71-84`). This pre-dates the change.
       - A command the Bash tool runs as zsh is judged on bash's reading of it. The line cites the decision file's zsh residual (Design item 10, row 114).
     - Known gaps changed: the three python3-less entries name a machine where the parse path cannot run, not python3, and keep their §32 citations. The capped-calls entry counts `_lib_shell_parse`'s two capped calls, which run together in one pipeline.
5. **The self-review evaluator (PR 2)**, a dependent of row 1's scope (row 52). `load_git_record_builder()` loads the module by path, as it loads `parse-git-command.py` today. It returns a `build_records(command)` closure and `FIELD_SEP`, so `assess` and `runs_git_diff` keep their signatures.
   - The closure returns no records, and spawns nothing, unless the command text holds both `git` and `diff` (row 54).
   - Otherwise it runs `SHFMT_ARGV` through `subprocess` with the command on stdin and stderr discarded, and projects the tree in-process.
   - When shfmt exits 1, the closure returns no records, matching today's SENTINEL result.
   - Every other failure of the shfmt call or of the in-process projection earns the command R5 credit instead of raising (row 89). A parse fault then degrades R5 alone, and the evaluator's other checks still run.
     - `run` then logs a `reread-credited-unparsed=<reason>` line before its own verdict line, as an evaluator error logs a pair today.
     - The reasons, each with its trigger:
       - `shfmt-missing`: shfmt does not resolve.
       - `shfmt-start-failed`: any other `OSError` from starting shfmt (a non-executable or wrong-architecture file).
       - `shfmt-exit-N`: shfmt exits N, for any N other than 0 and 1.
       - `oversize`: the command is over the module's `MAX_COMMAND_BYTES`.
       - `tree-unrecognized`: the projection raises `TreeNotRecognized`.
       - `parse-fault`: any other exception, `JSONDecodeError` and `RecursionError` included.
     - `MAX_COMMAND_BYTES` equals `_LIB_SHELL_PARSE_MAX_BYTES`. The PR 2 test that pins `SHFMT_ARGV` pins it too.
   - Fail posture: the evaluator stays fail-open, as its wrapper's header states (row 90). It is a workflow nudge for a cooperative writer, not a gate.
     - The credit path keeps it from sending the writer back for a fault the writer cannot repair, which would also spend the cycle's one send-back (row 89).
     - The log line records the cause. The SessionStart notice is the early warning: it shows the human a cause present at session start (Design item 11). A fault that starts mid-session reaches only the log (row 91).
   - The closure carries no timeout of its own, because the wrapper's 5 s cap bounds the whole run.
   - `runs_git_diff` parses the whole command once. Its per-line split existed only for the old parser's newline gap.
   - Behavior change: `# check git diff later` stops earning R5 credit, because the parser drops comments. `echo git diff` keeps earning it, because `classify_git_segment` takes the first `git` word in any position (row 55).
   - `docs/design-decisions/code-writer-self-review-send-back.md` § "Log verdicts" gains the new verdict and its reasons, because it is the vocabulary's single home (row 71).
6. **`install.sh` and the shared floor (PR 1).**
   - `claude/.claude/hooks/_config.sh` holds the floor beside the python3 floor, because `install.sh` and the shared shfmt check (Design item 12) both compare with it (row 81).
     - It adds `_SHFMT_FLOOR_MAJOR`, `_SHFMT_FLOOR_MINOR` and `_SHFMT_FLOOR_PATCH` (3, 14, 0), `_shfmt_version_meets_floor` and `_shfmt_floor_status [RUNNER...]`, modeled on `_python_version_meets_floor` and `_python3_floor_status` (`_config.sh:70-113`).
     - `_shfmt_floor_status` reads the first `X.Y.Z` in `shfmt --version`, with or without a leading `v`, and compares it field by field. It returns 0 at or above the floor and 1 below it, printing the validated version for both. It returns 2, printing nothing, when shfmt is missing or prints no readable version.
     - Each field is 1 to 9 digits and compared in base 10, as the python3 and git checks do.
   - A new `shfmt-floor-check` block in `install.sh` goes between INSTALL_TEST_FIXTURE markers, after the git floor block and before the first `$HOME` mutation at `install.sh:138`. It calls `_shfmt_floor_status`.
   - A missing shfmt exits 1 with these install routes, and the message notes that distro packages can be older:
     - Homebrew.
     - The mvdan/sh release binary, checked against the release's published checksums, a check the message says shows only that the asset did not change after publication.
     - `go install mvdan.cc/sh/v3/cmd/shfmt@v<floor>`, never `@latest`, with `$(go env GOPATH)/bin` on the PATH Claude Code starts with.
   - A version below the floor exits 1.
   - When no version is readable, a notice names the resolved shfmt, says its version could not be read, and says the hooks deny any syntax tree they do not recognize. The install then continues (rows 33-34).
   - Every failure prints `shfmt resolved on PATH: <path>`, or "none found".
   - Every failure tells the human to re-run `./install.sh` and restart Claude Code, so its hooks resolve the same shfmt.
   - Every failure cites `README.md` § "Requirements". The python3 and git blocks set that precedent (`install.sh:84-99`, `:125-135`).
   - Success prints one line naming the resolved shfmt and the same restart advice, as the bash floor check does at `install.sh:31`.
   - shfmt stays out of the generic presence loop at `install.sh:35-43`. That loop's "system package manager" advice would send apt users below the floor (Given 3).
   - The missing-cap-tool warning at `install.sh:1052`, which names only jq and git checks, adds that the hooks' command parse then runs uncapped, so a hung shfmt or python3 stalls each gated command until the harness's hook timeout (row 111).
7. **CI (PR 1).**
   - An "Install the pinned shfmt binary" step, id `pin-shfmt`, runs in both legs after the stow step, under `if: steps.detect.outputs.changed == 'true'`. Its env holds `CI_SHFMT_VERSION: "3.14.0"`, the floor build (row 62), and `CI_SHFMT_SHA256`, an in-repo literal digest (row 38).
   - The step body does the following:
     - It runs under `set -euo pipefail` and fails naming the key when either env value is empty.
     - It downloads the linux amd64 asset, its URL built from `CI_SHFMT_VERSION`, into a fresh `mktemp -d` directory with `curl --fail --silent --show-error --location --retry <n> --max-time <s>`.
     - The `--retry` and `--max-time` values each carry a one-line comment that cites its source or says no vendor value applies, as `tests.yml:239` does.
     - It checks the file with `sha256sum -c` against a line built from the literal and the downloaded file's own name.
     - It installs the binary with `sudo install -m 0755` only after the check passes, and never runs it before then.
     - It prints `shfmt --version`.
     - On failure it says whether the fetch or the hash failed, and where the pin came from.
   - Its comments follow the pinned-git step's.
     - They say the engineer took the digest by hashing the downloaded asset in a separate terminal (row 40).
     - They state what each available source proves. A match with the release's own checksum file proves only that the asset did not change after publication, because the same release publishes both. A Go checksum database match proves the tag's source, not the binary, so it is never a comparison for the asset's digest. Nothing here proves the binary was built from that source.
     - They say which of these held at the pin, and record the digest as trust-on-first-use when nothing stronger did.
     - They say a bump repeats the same checks and moves the floor too.
   - `test_shfmt_floor.py`, modeled on `test_git_floor.py`, checks these:
     - The pin equals the floor in `_config.sh`.
     - Under `GITHUB_ACTIONS`, the runner's `shfmt --version` matches the pin, which shows the step ran.
     - The step body runs in the pattern of `TestPinStepRunBody` (`test_git_floor.py:471-514`), with only `curl`, `sudo` and `install` stubbed. The `curl` stub writes known bytes and logs its URL, `sudo` and `install` log their calls, and the real `sha256sum` does the check. The test skips locally when `sha256sum` is absent and fails under `GITHUB_ACTIONS`.
     - A digest that differs from the stub's bytes, and a failed fetch, never reach `install`. A digest equal to their hash reaches it after the check. An empty key is named.
     - The version fixture differs from the pin, and the logged URL contains it, so a version hard-coded in the step body fails, as `test_git_floor.py:390-391` does for git.
8. **Cursor adapter parity (PR 1).** The adapter records shfmt, and its `check` command and sessionStart report run the same shfmt check as the SessionStart hook (rows 95-96).
   - `RECORDED_TOOLS` (`claude/.claude/scripts/cursor-adapter/cursor_adapter/core.py:222`) gains `shfmt` as its last entry, so the hooks' PATH under Cursor holds shfmt's directory (row 43). An existing Cursor install re-runs `install`, and `check` names that fix.
   - `tool_findings` (`check.py:340-378`), which `check` and the sessionStart entry share (`check.py:402`, `:595`), reports a shfmt missing from the hooks' PATH.
   - When shfmt resolves and the hooks' python3 and bash both passed their floors, `tool_findings` runs `_lib_shfmt_dependency_cause` (Design item 12) through one bash probe that sources the hooks' `_lib.sh`. So the floor compare, the probe and their wording each keep one home.
     - Requiring python3's pass mirrors the SessionStart hook, so one python3 fault yields one finding (row 82).
     - The probe's program text is a fixed constant beside `PROBE_BASH_PROGRAM`. The hooks directory and the two caps reach it as positional parameters, never inside the text.
     - The program sources `_lib.sh` with that source's output discarded, and exits nonzero when the source fails.
     - Any nonzero exit, or any printed line, becomes a finding. Its text is the first line, or a fixed line naming the shfmt check and its exit status when that line is empty. A broken hooks directory therefore yields a finding, not a pass (row 76).
     - A finding for a below-floor shfmt or a failed probe cites `docs/hooks.md` § "Gate deadlock recovery", then tells the user to re-run the adapter's `install` and relaunch Cursor once shfmt is fixed. The hooks' PATH holds only the directories `install` recorded, so a fix that moves shfmt reaches the hooks only through `install`.
   - That probe runs through `run_probe` (`tools.py:55-74`), from the adapter's probe directory under `PROBE_BOUND_SECONDS`, as the python3 and bash probes do.
     - It passes a parse cap and a version cap of half `PROBE_BOUND_SECONDS` each, computed from that constant in code. A hang in either call whose child honors SIGTERM then ends with its cause line inside the bound (row 110).
     - A stall past the bound, such as a child that ignores SIGTERM through the 2-second kill grace, reports that the shfmt check did not answer, naming shfmt rather than bash.
   - Budget: today the entry's worst case is the 2-second stdin read, three probes at 2 seconds, the 1-second host walk and 1 second of headroom, exactly its 10-second `timeout` (row 97). The shfmt probe makes it 12, so `CHECK_ENTRY_TIMEOUT_SECONDS` rises to 12 (row 98).
     - The inner caps do not remove the bump, because `run_probe` still bounds the fourth probe at `PROBE_BOUND_SECONDS`, and the entry's worst case counts that bound (row 110).
     - Its comment at `core.py:23` then derives the value from that sum, instead of naming the hook's registration, whose `timeout` stays 10.
     - The comment at `core.py:25-26` counts four probes.
     - An existing install's hooks.json then differs from the generated one until the same `install` re-run.
   - Under Cursor, `check-hook-dependencies.sh`'s registration stays declined, because the sessionStart report stands in for both of its checks (row 93).
   - The report gains no cap-tool line, because the adapter already refuses and reports a missing cap tool (row 112).
   - The test helper `recorded_tool_paths` gains `shfmt` in Dispatch 2, because the gate-matrix rows for the three redaction gates run on that PATH from Dispatch 2 on.
9. **A consumer who pulls before installing shfmt** (row 6).
   - **What denies.** Each deny names its cause, tells the agent to stop and ask, and cites the recovery entry below. Other gates and tools are unaffected.
     - From PR 1, the three redaction gates deny every command that reaches their parse (row 20): every `git commit` inside a work tree, through `deny-pii-in-commits.sh`; `gh pr create` and `gh pr edit`; `gh issue create`, `gh issue comment` and `gh issue edit`; and a mutating `gh api` call. Read-only commands such as `gh pr view` and a GET `gh api` call never reach the parse.
     - From PR 1, a machine without python3 denies the same commands, not only those xargs cannot split.
     - From PR 2, the worktree gate also denies every git command it parses. In a main-tree session with enforcement active, that is every git command, `git pull`, `git revert` and `git status` included, because the parse runs before the read-only allowlist that reads its records (row 51).
   - **What warns.** From PR 1, the SessionStart check (Design item 11) names a missing, below-floor or failing shfmt at the next session start or resume. Under Cursor, the adapter's sessionStart report and `check` name the same causes (Design item 8).
     - The same check names a machine with neither `timeout` nor `gtimeout` on PATH. There a hung shfmt or python3 stalls each gated command for the harness's hook timeout, 600 seconds by default, and the harness's deny names no cause (row 111).
   - **Recovery.** The human installs shfmt in a separate terminal, re-runs `./install.sh`, and restarts Claude Code. A Cursor user also re-runs the adapter's `install` and relaunches Cursor.
   - **No fallback.** Nothing falls back to the old tokenizers (row 35).
   - **Text changes.** PR 1 makes three that carry the warning (row 49):
     - `README.md:134` widens from a change that raises the bash or Claude Code floor to any change that raises a floor or adds a required tool. A new `shfmt` bullet in § "Requirements" states the floor, the install routes, that the hooks which parse commands deny without it, and that `check-hook-dependencies.sh` warns at session start, as the Python bullet at :116 says for python3. It names no gate and cites the recovery entry, so PR 2 leaves `README.md` alone.
       - The bullet also gives the zsh note (row 106). The hooks parse commands as bash, so a zsh-only command denies, and a command zsh reads differently can be judged on words zsh never runs. Setting `CLAUDE_CODE_SHELL` to a bash path makes the Bash tool run bash. It cites the decision file for the rest.
       - The `timeout` bullet at :115 gains one sentence (row 111): without `timeout` or `gtimeout`, a hung shfmt or python3 stalls each command a hook parses for the harness's 600-second hook timeout, and `check-hook-dependencies.sh` warns at session start.
     - The CHANGELOG entry's migration note follows `CHANGELOG.md:673-678`: a "Before pulling" step, an "If you have already pulled" step, and the headless caveat `docs/hooks.md:560` gives for jq. It says "any `git commit`", not only one with staged changes, names the gated `gh` subcommands rather than whole command families, and names the session-start notice. Further lines, one fact each:
       - The zsh note, as the README bullet states it.
       - The cap-tool warning and the 600-second stall, as the README's `timeout` sentence states them.
       - A Cursor user re-runs the adapter's `install` and relaunches Cursor, because PR 1 changes `RECORDED_TOOLS` and the entry timeout.
       - If row 113 settles that shfmt replaces a non-UTF-8 byte, a path holding one now denies as unreadable.
     - `docs/hooks.md` § "Gate deadlock recovery" replaces the python3 paragraph at :592, which covers only the splitter, with an entry for the parse path, described next.
   - **The recovery entry** is the one home of the parse path's diagnosis (row 77). The SessionStart notice, the Cursor report's shfmt finding and every parse-failure deny cite it. Per status, it gives the diagnostic a human runs in a separate terminal, from the shell that launches Claude Code, and the fix:
     - 6, shfmt missing: `command -v shfmt`. Install shfmt at the floor, re-run `./install.sh`, and restart Claude Code.
     - 5, tree not recognized: `command -v shfmt`, `shfmt --version` and `printf 'echo a\n' | shfmt -ln bash --to-json`. Install the mvdan/sh release binary at the floor, because Homebrew installs only its current shfmt, or pull a claude-config fix.
     - 8, shfmt failed: the status-5 diagnostic followed by `echo $?` shows shfmt's own error, such as a shim with no version set or a wrong-architecture binary.
     - 3 on a command that is plainly valid bash: run the status-8 diagnostic. Its outcomes:
       - It shows shfmt failing. Exit 1 is not unique to a syntax error: a BusyBox `timeout` usage error also exits 1, so the cap wrapper or shfmt itself can be failing (row 59). Fix it as for 8.
       - It passes, and the command is valid zsh but not bash. The hooks parse bash only (row 106), and `README.md` § "Requirements" gives the setting that makes the Bash tool run bash.
     - 124, 137 or 143, a cap kill: time `printf 'echo a\n' | shfmt -ln bash --to-json` from that shell. The hooks cap the parse at 5 seconds, and the Cursor report caps it at half of the adapter's probe bound, 1 second. Its outcomes:
       - The run does not finish within the cap: a hung shim or binary. Fix the shim, or install the release binary at the floor, then restart Claude Code.
       - The run finishes, and the finding came once from a session start or the Cursor report and did not repeat: a slow first start, such as the first run after boot or a security scan of a new binary, can pass the cap once. Nothing needs fixing.
       - The run finishes, and denies keep coming: run the status-2 diagnostic, which tests python3 and the module.
       - The denied command is near the byte cap: it can run past the cap on a loaded machine. Move its content to a file in an earlier Bash call and pass it with the flag (row 102).

       A hang ends in this named deny only with `timeout` or `gtimeout` on PATH. Without either, the harness ends it at its 600-second hook timeout, with a deny that names no cause (row 111).
     - 127, python3 or awk missing or not runnable: `command -v python3` and `command -v awk`. The fix for python3 is the one `docs/hooks.md` § "Python version" gives.
     - 2, the module or the extraction step's awk faulted: the status-5 diagnostic piped into the hooks directory's `shell-syntax-tree.py words` under `python3 -I -S`, then `echo $?`. A nonzero exit is a module fault, so pull a claude-config fix. Exit 0 points at awk.
     - Any other status comes from python3, its cap wrapper, or the extraction step's awk and its here-string: run the status-2 diagnostic, and if it passes, check that awk runs and that `TMPDIR` is writable (`docs/hooks.md:590`).
     - 9, the session-start probe's words changed: run the status-5 diagnostic. Install the mvdan/sh release binary at the floor, or pull a claude-config fix.
     - The module not linked: re-run `./install.sh` from the claude-config checkout, the route the :592 paragraph gives today for the splitter.
     - The entry says the hooks and the SessionStart check run whichever shfmt the PATH Claude Code starts with resolves, from the session's working directory. A version-manager shim can therefore pick a different build per directory, as `docs/hooks.md:538` says for python3. § "Python version"'s hazards apply to the shfmt version call and probe too (Dispatch 5).
   - **Three ways out.** The entry gives these:
     - A denied command runs from a terminal outside Claude Code.
     - In a repo without the committed sentinel, the worktree gate's `.claude/worktree-optout` lifts its machine-level enforcement.
     - Rollback reverts the merge from such a terminal.
   - PR 1 writes the first and third ways out. PR 2 adds the second, and names `git pull` and `git revert` in the first.
   - After PR 2, the rollback sentence says to revert PR 2 first and PR 1 second, because PR 2's worktree gate calls PR 1's `_lib_shell_parse`. It says the opt-out route is for when `git revert` itself is denied. PR 1's wording, a revert of its one merge, holds until PR 2 changes it.
   - PR 2 adds a CHANGELOG entry with three facts:
     - Without shfmt, an enforced main-tree session can run no git command.
     - The evaluator's comment-form change applies (Design item 5).
     - A `cd` whose effect is uncertain leaves the cwd unresolved, so a later write denies, in a linked-worktree session too (row 85). These deny: `{ cd /wt && git push; }`, `if [ -d x ]; then cd x; fi; git commit`, `[ -d /wt ] && cd /wt; git push` and `pushd /wt && git push`. The way through is a plain `cd <worktree> && git ...`.
10. **Records.**
    - PR 1 creates `docs/design-decisions/tokenizing-gates-parse-with-shfmt.md`. It follows the `bats-core-adoption-declined.md` precedent for a dependency decision, and scopes the decision to the three redaction gates. It records these:
      - The choice and the alternatives above.
      - The fail-closed posture and the accepted lockout.
      - `check-hook-dependencies.sh` as the one place that diagnoses the parse path's dependencies (rows 76-77, 94), and the shared shfmt check it and the Cursor report both call (row 96).
      - The strict check as the only guard against a re-encoded tree.
      - An accepted residual: the gates run whichever shfmt the hooks' PATH resolves, so a shim or an earlier PATH entry can substitute a build `install.sh` never approved. The strict check bounds the tree's shape, not its fidelity to the command. `docs/hooks.md:538` accepts the same exposure for python3.
      - A second accepted residual: the SessionStart check runs `shfmt --version` and the probe from the session's working directory at every startup and resume. Under `claude -p`, the SDK, or a trusted parent folder, that directory can be a clone the user never reviewed (row 101). The probe's stdin is a fixed string. Whether a shfmt shim can select a repository-supplied binary is unconfirmed. A repository or one agent `Write` can set a version-manager pin file that makes a shfmt shim fail, as `docs/security-hardening.md:346-351` records for python3. Every parsing gate then denies, and the check warns at the next start.
      - A third accepted residual, the zsh gap (rows 15, 106). The Bash tool can run zsh, and the gates parse bash only:
        - zsh-only syntax such as `${(f)x}` is invalid bash, so shfmt exits 1 and the gate denies with the status-3 wording.
        - A construct that parses as bash but means something else in zsh can yield words zsh never sees.
        - Setting `CLAUDE_CODE_SHELL` to a bash path, such as `/path/to/bash`, forces the Bash tool to run bash.
        - A per-shell dialect is a follow-up (Out of scope).
        - The miss is accepted on implementation scope, not under `docs/hooks.md`'s cooperative-agent waiver, because nothing shows that a cooperative agent never emits a shape bash and zsh read differently (row 114).
      - A fourth accepted residual, a machine with neither `timeout` nor `gtimeout` on PATH (row 111). A hung shfmt or python3 then stalls each command a gate parses for the harness's default hook timeout, 600 seconds (`docs/hooks.md:580`), and the deny that follows is the harness's, which names no cause. `check-hook-dependencies.sh` names the missing cap tool at each session start.
      - A fifth accepted residual, memory on nested input (rows 115, 117). A few KB of nested input can make shfmt emit about 100 MB of JSON (row 66), which python3 reads whole. Only time is capped, and no byte bound limits the JSON. The gate still denies the command. The residual stands only if Verification 8's nested case peaks under that step's memory threshold. A peak over it puts a byte bound to the engineer instead.
      - The reconsideration triggers.
    - PR 1 adds a scope note to `command-text-gates-accept-quoted-text-over-deny.md` under its provenance line, not a supersession. The note says the redaction gates parse with shfmt and the quote-stripping command-text gates it covers are unchanged.
    - PR 2 widens both files to the worktree gate and the evaluator. The note gains one sentence: its nested-git argument does not reach the worktree gate, because shlex already kept quoted text whole (row 9).
    - Each affected gate's header Known-gaps records its waived residuals in the PR that introduces them, as `docs/hooks.md:43` and `:55` require, one line each citing the decision file:
      - PR 1: the zsh residual and the placeholder decoy (Out of scope) in `deny-pii-in-commits.sh`, `deny-private-project-refs.sh` and `deny-escaped-backticks-in-pr-body.sh`.
      - PR 2: the zsh residual in `require-worktree-for-git-writes.sh` (Design item 4).
    - PR 1's body states the zsh acceptance rationale beside row 106's quoted answer (row 114).
11. **The SessionStart check, `claude/.claude/hooks/check-hook-dependencies.sh` (PR 1).** It is `check-python-floor.sh` renamed and extended to shfmt, so the hooks' dependencies have one SessionStart home (rows 79, 94). It names a broken dependency at the next session start or resume, before that session's first deny (rows 76-80). A session already running learns of it at its first deny (row 61).
    - The python3 check keeps today's probe, 2-second cap, notice texts and § "Python version" citation unchanged (row 83). Only the cap-tool line below can join its notice.
    - `# hook-class: informational`. Every path exits 0, because SessionStart cannot refuse a session.
    - Its `settings.json` registration at :211-219 keeps its place, `matcher: startup|resume` and `timeout` of 10. Only the command path changes. The script's `.source` filter matches the matcher, and the header says the two stay in sync.
    - **The cap-tool line (row 111).** Before either check, the hook runs `command -v timeout` and `command -v gtimeout`, the pair `_lib_capped_for` probes (`_lib.sh:132-135`). The hook is their only caller, so the two calls stay in the hook rather than in `_lib.sh`.
      - When neither resolves, the notice carries one more line, after any cause line, or alone when both checks pass.
      - The line says that neither tool is on the PATH Claude Code started with, so a hung shfmt or python3 stalls each command a hook parses until the harness's hook timeout, 600 seconds by default, with a deny that names no cause.
      - It names no gate and no command. The screen text cites `README.md` § "Requirements" for the install route, and the agent text limits the agent to telling the engineer, as for the other notices.
    - It checks python3 first, through `_python3_floor_status _lib_capped_for 2`, as today. Status 1 or 2 prints today's python3 notice, and the hook never runs shfmt (row 82).
    - Otherwise it calls `_lib_shfmt_dependency_cause 5 2` (Design item 12), passing today's `_lib_capped` value as the parse cap and today's python3-probe cap as the version cap. A cause line it prints becomes the shfmt notice. One fault therefore yields one notice (row 82).
    - Budget. The bounds below hold only with `timeout` or `gtimeout` on PATH. Under `_lib_capped_for`'s documented bound, a capped call then returns by its cap plus 2 seconds when its child ignores SIGTERM (`_lib.sh:69-72`).
      - A hung python3 at its version call ends the hook within about 4 seconds.
      - A hung shfmt, or a python3 that hangs inside the probe, ends it within about 7 seconds, because a cap kill in the probe skips the version call (Design item 12).
      - Only tools that each answer just under their caps can add up past the 10-second timeout. The harness's cancel is then one of the silent cases below, and each gate still denies with its own reason.
      - With neither tool on PATH, every call runs uncapped (`_lib.sh:136-138`). A hung tool then stalls session start until the harness cancels the hook, the case `docs/hooks.md:549` documents for python3, and the hook prints nothing, the cap-tool line included.
    - A machine where python3 and shfmt both fail sees only the python3 notice until python3 is fixed. In the meantime each parse deny names python3 too, because `_lib_shell_parse` checks python3 before shfmt (Design item 1, row 109).
    - A shfmt notice goes to the screen as `systemMessage` and to the agent as `additionalContext`, built by `_lib_jq`, as the python3 notice is built today.
      - The screen text gives the cause line, says that hooks which parse commands deny them until it is fixed, and cites `docs/hooks.md` § "Gate deadlock recovery".
      - It names no gate and no command, so it stays true after PR 2 widens the set of denied commands.
      - The agent text gives the same cause line and limits the agent to telling the engineer in its next reply. It carries no remedy sentence from the screen text, as the python3 notice's agent text does not.
      - Only fixed text, the floor, a digit-validated version and a status number reach either text. No path, shfmt output or stderr does.
    - The header comment changes in these places, and keeps its other facts (`check-python-floor.sh:2-14`):
      - Line 3's purpose names both dependencies, python3 and shfmt, and the cap-tool warning.
      - Line 5's silence condition adds the cap-tool line.
      - Line 7's output invariant adds the status number.
      - Line 12's cap line covers the shared check's caps, and says the hook warns when neither cap tool resolves.
      - Line 14's budget line says the hook starts jq, python3 twice and shfmt twice, and still fires only at startup and resume.
      - It cites `docs/hooks.md` § "Gate deadlock recovery" for the shfmt conditions beside the § "Python version" citation, and lists no repair steps.
    - It prints nothing in the cases its header lists today, for either check: a bash below the floor, a missing or hung `jq`, and a harness cancel at the timeout. In each, a gate that parses still denies with a reason of its own, so the failure is not silent. The exception is a hung tool on a machine with neither cap tool: each gated command then stalls for 600 seconds, and the harness's deny names no cause (Design item 10).
    - PR 2 does not change it. The probe holds every type the child-position matrix lists as holding a command and every `KNOWN_BINARY_OPERATORS` entry, and a PR 1 test pins both (Design item 12).
12. **The shared shfmt check in `claude/.claude/hooks/_lib.sh` (PR 1).** The SessionStart hook (Design item 11) and the Cursor adapter's report (Design item 8) both call it, so the shfmt check has one implementation (rows 80, 96).
    - `_lib_shell_parse_probe PARSE_CAP` runs `_lib_shell_parse` once on a fixed probe command with the `words` projection and PARSE_CAP as its cap, and compares the output with the expected words. It returns 0 on a match and `_LIB_SHELL_PARSE_PROBE_MISMATCH_STATUS` (9) on a mismatch. Otherwise it returns `_lib_shell_parse`'s status, with 3 turned into 8, because the probe is valid bash (row 59).
    - The probe command and its expected words are literals beside the function, their one home. The probe is parsed and never run. A test requires its parsed node types to include every type the child-position matrix lists as holding a command, and its operators every `KNOWN_BINARY_OPERATORS` entry (Verification 6). The matrix's types decide the rest of the probe. It holds at least one of each of these:
      - A `git commit -F` with a literal path, and a `gh pr create --body-file "$F"`.
      - A heredoc inside a command substitution, backticks, and a process substitution.
      - `&&`, `||`, `|`, `|&`, `;` and a backgrounded statement.
      - A subshell, `{ }`, `time` and `!`, each holding a `cd`.
      - `if` with `elif` and `else`, `while`, `until`, `for`, `select` and `case`, a function declaration, and a coprocess.
      - `[[ ]]`, `(( ))`, an assignment-prefixed `cd`, `builtin cd` and `pushd`.
    - The shared check does not look for a cap tool. The SessionStart hook does that itself (Design item 11), and the Cursor adapter already refuses and reports a missing one (row 112).
    - `_lib_shfmt_dependency_cause PARSE_CAP VERSION_CAP` takes both caps as required arguments, so each caller states its own (row 110). The SessionStart hook passes 5 and 2 (Design item 11), and the Cursor probe passes caps that fit its bound (Design item 8).
    - It prints nothing and returns 0 when shfmt passes. Otherwise it prints one cause line and returns the status that decided it. It runs in this order (row 82):
      1. The probe, under PARSE_CAP. A cap-kill status ends the check with that status's clause, so a hung shfmt costs one capped call, not two.
      2. `_shfmt_floor_status _lib_capped_for VERSION_CAP`. Status 1 ends the check with a line naming the found version and the floor, and returns `_LIB_SHFMT_BELOW_FLOOR_STATUS` (10). Status 0 or 2 goes on, so a build that prints no version (row 34) is judged by the probe alone.
      3. A nonzero probe status ends the check with its clause. Status 6 is the missing-shfmt case, and 9 the changed-words case.
    - Every probe status's line comes from `_lib_shell_parse_failure_clause`, so the cause wording has one home (row 103). Only fixed text, the floor, a digit-validated version and a status number reach the line.
    - What the probe catches:
      - A missing or failing shfmt, and a shfmt that exits 1 on valid bash.
      - An unlinked module, and a python3 that fails inside the parse.
      - A tree the strict check rejects for a construct the probe holds.
      - A projection that changed for those constructs.
    - What it cannot catch:
      - A shfmt that changes after the session starts, through an upgrade or a PATH change. The next parse denies and names the cause.
      - A re-encoding of a construct the probe does not hold. The strict check denies it at run time.
      - A per-command failure, such as an oversized command or invalid bash.
      - A shim that resolves a different build in a directory other than the one the check ran in.

### Assumption ledger

```text
Root: four gates tokenize the Bash command they judge —
  deny-escaped-backticks-in-pr-body.sh, deny-pii-in-commits.sh and
  deny-private-project-refs.sh through _lib_command_words, and
  require-worktree-for-git-writes.sh through parse-git-command.py. They use
  `xargs -n1` and stdlib shlex behind quote-blind pre-passes, whose documented
  residuals include misses. Three of the four list `irreversible` on their
  tier line (deny-pii-in-commits.sh:3, deny-private-project-refs.sh:3,
  require-worktree-for-git-writes.sh:3), and
  deny-escaped-backticks-in-pr-body.sh:3 lists `cooperative` only. The plan
  replaces both tokenizers with a real bash parser that every stow consumer
  installs.

Given 1: Claude Code hands a PreToolUse hook the Bash command as a string
  with no parsed form — the vendor owns the payload, and
  docs/design-decisions/command-text-gates-accept-quoted-text-over-deny.md
  lists a parsed form only as a reconsideration trigger.
Given 2: shfmt's --to-json output carries no stability promise and changed
  shape in v3.11.0 and v3.14.0 [unverified: research summary of the mvdan/sh
  project pages, fetched 2026-11-20] — upstream owns the format.
Given 3: Debian stable and Ubuntu 24.04 package shfmt 3.8.0, Ubuntu 26.04
  packages 3.12.0, and Homebrew has 3.14.1 [unverified: same research
  summary] — the distributions own their package versions.

Row 1 [assumption]: the plan covers the four hooks above and no other gate
  [engineer-verified: "Four tokenizing hooks (Recommended)"] — anchors: root

Row 2 [assumption]: that option's description is the session's wording, not
  the engineer's: only those four hooks, consistent with the 2026-10-18
  decision, adding a note to it rather than overturning it [unverified]
  — anchors: row1

Row 3 [assumption]: install.sh checks for shfmt and does not download it
  [engineer-verified: "Check only (Recommended)"] — anchors: root

Row 4 [assumption]: shfmt's floor is 3.14.0 [engineer-verified: "Floor at
  3.14.0 (Recommended)"] — anchors: root

Row 5 [assumption]: that option's description is the session's wording: one
  JSON shape to read, Linux apt users take the release binary or
  `go install`, and CI needs a pinned download [unverified] — anchors: row4

Row 6 [assumption]: a consumer who pulls before installing shfmt is locked
  out of the commands the four gates parse until they install it, and the
  plan accepts that lockout instead of staging the rollout
  [engineer-verified: "I'd say accept the lockout because consumers know
  they may need to run ./install.sh after a git pull, and CHANGELOG should
  tell them"] — anchors: root

Row 7 [assumption]: shfmt 3.14.1, run as `-ln bash --to-json` on stdin,
  exits 0 on all nine TestResidualShapes inputs
  (test_split_command_words.py:363-428). The four over-denies parse, and the
  five misses keep the flags and paths the splitter drops (/y, /hidden,
  /tmp/body.md) [verified: spike this session against a MacPorts build of
  shfmt 3.14.1, synthetic inputs] — anchors: row12

Row 8 [assumption]: on that build, one fact per item:
  - A real heredoc body yields no command words [verified: same spike].
  - A backslash-newline joins the words around it [verified: same spike].
  - `cd /a && git -C /b status; (cd /c; git push) | cat` yields five
    simple commands [verified: same spike].
  — anchors: row12, row16

Row 9 [assumption]: `bash -c "git checkout -- x"` yields one word and no
  inner git command [verified: same spike]. parse-git-command.py's shlex
  also keeps quoted text as one token [verified: parse-git-command.py:57-58].
  Its `_is_git_token` matches a word that is `git` or ends in `/git`, so
  `/usr/bin/git` and an unquoted `$HOME/bin/git` both count as git
  [verified: parse-git-command.py:165-166]. Both tokenizers hand that
  classifier the same quoted word, so the worktree gate gains no false
  allow for nested git — anchors: row16, row44

Row 10 [assumption]: the set-aside parser candidates have these
  properties, one item per candidate:
  - tree-sitter-bash 0.25.1 is error-tolerant, with ERROR nodes and no
    failure signal. It has eight open heredoc mis-parse issues, a
    quadratic-time issue and a SIGSEGV issue [unverified: research summary
    of its project pages, fetched 2026-11-20 through a summarizing fetch
    tool].
  - bashlex 0.18 is licensed GPL version 3 or later and was last committed 2024-04-08.
    Its README calls `$((..))` unsupported, and an issue on `$'...'` is
    open [unverified: the same research summary, for bashlex's pages].
  - Oils osh's parse-only tree output is unconfirmed [unverified: the same
    research summary, for the Oils pages].
  — anchors: row12

Row 11 [assumption]: the gate runs its Python under `python3 -I -S`, so a
  pip-installed parser library is not importable inside the gate without
  extra path plumbing [verified: _lib.sh:2577-2579] — anchors: row12

Row 12 [mechanism]: shfmt as the parser — anchors: root — it is the one
  candidate that fails loudly on invalid bash, ships as one static binary,
  and parsed all nine residual shapes. Lighter primitives, each set aside in
  "Alternatives weighed": patching the shlex pre-passes (a hand-rolled bash
  lexer), narrowing what the gates read (leaves rows 17 and 19 open), and
  bash itself (row 13).

Row 13 [assumption]: canonicalizing a command through real bash runs its
  command substitutions inside the hook [verified:
  docs/security-hardening.md:844-848] — anchors: row12

Row 14 [assumption]: shfmt's project health, one fact per item:
  - It is BSD-3-Clause [unverified: research summary].
  - It released v3.14.1 on 2026-09-06, its seventh release in two years
    [unverified: research summary].
  - It has no published GitHub security advisory [unverified: research
    summary].
  - CVE databases are unchecked. Verification 9 checks OSV before PR 1
    [unverified].
  — anchors: row12

Row 15 [assumption]: Claude Code's Bash tool runs bash or zsh. It runs the
  shell CLAUDE_CODE_SHELL names, or else one auto-detected from $SHELL,
  then the first working zsh, then bash [unverified: relayed by a research
  agent's report, a secondary source, from
  https://code.claude.com/docs/en/env-vars.md, the CLAUDE_CODE_SHELL row,
  and https://code.claude.com/docs/en/tools-reference.md, "Bash tool
  behavior". The session confirms both lines before Dispatch 5, which
  writes the CLAUDE_CODE_SHELL instruction into README.md and
  CHANGELOG.md].
  The pages do not state whether the shell that runs a command parses the
  same string the hook sees, whether it runs as a login shell, or whether
  `claude -p` or the SDK differ [unverified]. So a user whose $SHELL is
  zsh can have commands run as zsh while the gates parse them as bash.
  Row 106 accepts that gap — anchors: row12

Row 16 [mechanism]: replace parse-git-command.py as well as the splitter
  — anchors: row1, row17 — once shfmt is required, keeping shlex in the
  worktree gate keeps two misses that the parser closes.

Row 17 [assumption]: the worktree parser does not split segments at a
  newline, and it drops the rest of a line after a same-line heredoc opener,
  so a git write in either position is never judged [verified:
  require-worktree-for-git-writes.sh:69-74] — anchors: row16

Row 18 [mechanism]: drop the `xargs -n1` fast path, so shfmt parses every
  command that reaches _lib_command_words — anchors: row19, row20 — the
  fast path has its own miss. The cost is one shfmt and one python3 start
  per parse, on every `git commit` and on the gh commands of row 20.
  Verification 8 measures it against the 100 ms per-fire budget.

Row 19 [assumption]: `xargs -n1` exits 0 on a backslash-newline between a
  source flag and its path and yields a blank value, which the caller skips
  [verified: _lib.sh:2565; deny-private-project-refs.sh:652]
  — anchors: row18

Row 20 [assumption]: the redaction gates reach the parse on these command
  shapes, one gate per item:
  - deny-pii-in-commits.sh: every `git commit` inside a work tree, with or
    without staged changes [verified: deny-pii-in-commits.sh:321-350,
    :378-415, :459-499, where every exit between the work-tree probe and
    the extractor is a deny].
  - deny-private-project-refs.sh: a `git commit` with a non-empty staged
    diff, `gh pr create` and `gh pr edit`, `gh issue create`, `gh issue
    comment` and `gh issue edit`, and a mutating `gh api` call. Read-only
    `gh` commands never reach the parse [verified:
    deny-private-project-refs.sh:4-5, :79, :327-331 and :369 for the
    surfaces; :602-650, :680-690, :718-730 and :758-772 for the parse
    calls].
  - deny-escaped-backticks-in-pr-body.sh: `gh pr create` and `gh pr edit`
    [verified: deny-escaped-backticks-in-pr-body.sh:81-109].
  - A commit with staged changes therefore parses once in each commit gate
    [verified: the first two items].
  - shfmt took a median 29.6 ms and a maximum of 56.3 ms over 30 runs on a
    50-byte command [verified: spike, one macOS machine].
  — anchors: row18

Row 21 [mechanism]: bash runs shfmt and pipes its JSON into a stdlib-only
  projection under `python3 -I -S` — anchors: row22 — the gate-side Python
  stays free of process spawning. Having Python spawn shfmt would break
  that pin.

Row 22 [assumption]: the splitter's tests pin that it imports no process,
  network, filesystem or dynamic-code module [verified:
  test_split_command_words.py:447-478] — anchors: row21

Row 23 [mechanism]: one module, shell-syntax-tree.py, holds both
  projections and replaces both scripts — anchors: row24 — both
  projections need the same strict tree check, and two copies of a
  security-relevant type list drift apart.

Row 24 [mechanism]: strict tree check. Every node Type, every BinaryCmd
  operator and every object's keys must fall within the module's known
  sets, every always-present key must be there, and the projection's
  CallExpr count must equal a raw count. Otherwise the module exits 5 and
  the gate denies — anchors: root — under Given 2 a re-encoded tree must
  fail closed. Projecting it to no words would read as "no source file",
  and an empty record list reads as "nothing to judge" in the worktree
  gate (require-worktree-for-git-writes.sh:47-50).

Row 25 [assumption]: the spike's flattener reads `Type`, `CallExpr.Args`,
  `Word.Parts` and the values of `Lit`, `SglQuoted` and `DblQuoted` parts,
  and produced the words row 7 reports [verified: the session's spike
  script] — anchors: row23, row24

Row 26 [assumption]: these properties of shfmt's output, which no spike
  read, hold as the design expects [unverified: Dispatch 1 dumps them
  first]:
  - `BinaryCmd.Op` is a string, or an integer the module can map onto
    KNOWN_BINARY_OPERATORS.
  - `Stmt.Background` exists under that name.
  - `SglQuoted` and `DblQuoted` carry a `Dollar` flag.
  - `Lit.Value` keeps raw backslashes. A plan reviewer saw `"b\"c"`
    yield `b\"c` and `\a` yield `\a` on the row 7 build, so the design
    decodes them unconditionally (Design item 2).
  - Each struct field holding its zero value is either always present or
    always omitted, which fixes each struct's always-present key set.
  - The dump shows which objects carry a `Type` key, and so which untyped
    objects the strict check matches by the field that holds them.
  - An unterminated heredoc makes shfmt exit 1 with no JSON, as an
    unbalanced quote does (row 32).
  - Each struct's always-present key set comes from its smallest input. A
    plan reviewer saw an empty command yield a `File` that carries `Type`
    alone, with no `Pos`, `End` or `Stmts`, on the row 7 build.
  - On that build `ParamExp.Dollar` is a position object, a different
    field from the flag the design expects on `SglQuoted` and `DblQuoted`.
  — anchors: row23, row24, row27

Row 27 [mechanism]: each non-literal part of a word becomes a fixed
  placeholder that begins with `$`, and the literal parts on both sides of
  it keep their text — anchors: row9, row28, row58 — a flag prefix such as
  `--body-file=` or `key=@` survives, so the caller extracts a path holding
  the placeholder and denies it as unreadable, as it denies a literal `$F`
  today. `$HOME/bin/git` keeps the `/git` suffix that row 9's classifier
  matches. Ending the word at its first non-literal part was set aside: it
  drops that suffix, so `$HOME/bin/git push` in an enforced main tree would
  yield no GIT record and turn from a deny into an allow. The gate does no
  expansion and no ANSI-C decoding.

Row 28 [assumption]: every caller denies a source path that is not a
  readable regular file and skips a blank one [verified:
  deny-private-project-refs.sh:652-660, :697-706, :785-794;
  deny-pii-in-commits.sh:503-511; deny-escaped-backticks-in-pr-body.sh:113-121].
  A plan reviewer also read the `gh issue` loop at
  deny-private-project-refs.sh:737-745 and the field-at loop at :819-827
  [unverified: not reread by the architect] — anchors: row27, row29

Row 29 [mechanism]: a blank line after each simple command's words
  — anchors: row28 — a flag that ends one command cannot then take the next
  command's first word as its path.

Row 30 [mechanism]: a 64 KiB byte cap checked before shfmt starts
  — anchors: row31, row66 — it bounds the input a flat command hands
  shfmt. Row 31's one-machine run is an observation, not a time bound
  (Verification 8). It does not bound nested input, whose JSON grows with
  depth.
  Only _lib_capped bounds shfmt's time, and a machine with neither timeout
  nor gtimeout relies on the harness's hook timeout (_lib.sh:87-95).

Row 31 [assumption]: 1 MB of 500,000 two-byte words took 35.85 s and
  produced 324,831,219 bytes of JSON, about 72 µs and 650 bytes per word.
  At the cap that makes 32,768 words, about 2.35 s and 21 MB, which is
  inside _lib_capped's 5 s [verified: spike, one macOS machine, synthetic
  input; per-word figures derived from it]. Under the pipe, python3 reads
  that JSON whole within the same cap (Design item 1). No run has
  measured python3's share, and Verification 8 times the whole parse
  — anchors: row30

Row 32 [assumption]: on an unbalanced quote, shfmt exits 1 with a
  line:column message on stderr and prints no JSON [verified: spike]
  — anchors: row21

Row 33 [mechanism]: install.sh compares a readable `shfmt --version` with
  3.14.0 and exits 1 below it. When no version is readable it prints a
  notice and continues — anchors: row4, row24, row34 — the version compare
  enforces the floor wherever a build reports one, and the strict check
  (row 24) holds every build to the tree shape at run time. Set aside: an
  install-time shape probe, which repeated what row 24 checks on every call
  and needed install.sh to source the hooks' _lib.sh in a child bash; and
  exiting 1 on an unreadable version, which rejects a working build
  (row 34).

Row 34 [assumption]: a MacPorts build of shfmt 3.14.1 prints an empty line
  for `--version` [verified: spike] — anchors: row33

Row 35 [mechanism]: a missing shfmt denies with a stop-and-ask reason, and
  nothing falls back to the old tokenizers — anchors: row6 — a fallback
  keeps both tokenizers and their tests alive with no point at which to
  remove them.

Row 36 [mechanism]: the self-review evaluator runs shfmt itself through
  subprocess and reuses the git-records projection — anchors: row37,
  row52. Lighter primitives set aside: keeping shlex build_records for the
  evaluator alone keeps the retired tokenizer alive for one caller, and
  dropping its git-diff detection drops R5's Bash arm.

Row 37 [assumption]: the evaluator's use of the old parser, one fact per
  item:
  - It imports build_records by path [verified:
    evaluate-code-writer-self-review.py:381-390].
  - It calls build_records on Bash calls after the last edit until the
    first diff [verified: evaluate-code-writer-self-review.py:510-521].
  - It splits each command per line for the old parser's newline gap
    [verified: evaluate-code-writer-self-review.py:393-408].
  - Its wrapper fails open on any evaluator failure under _lib_capped
    [verified: send-back-skipped-self-review.sh:11, :78].
  — anchors: row36

Row 38 [mechanism]: CI downloads the floor build's release binary, checks
  it against an in-repo SHA-256 literal before installing it, and a CI-only
  test compares the running binary with the pin — anchors: row39, row40.
  Lighter primitives set aside: apt's build is below the floor, `go
  install` compiles on a runner Go toolchain whose version against shfmt's
  go.mod is unchecked, and a third-party setup action is one more action to
  trust for a three-line download.

Row 39 [assumption]: CI's tool provisioning, one fact per item:
  - It runs only on ubuntu-24.04 [verified: .github/workflows/tests.yml:28,
    :238].
  - It installs stow and direnv from apt [verified: tests.yml:131-132].
  - It pins git and zsh by apt version [verified: tests.yml:149-157,
    :184-189].
  - No step downloads a binary [verified: tests.yml holds no curl, wget or
    download step].
  — anchors: row38

Row 40 [assumption]: the v3.14.0 release's assets, one fact per item. The
  session confirms each on the release page before Dispatch 3:
  - It publishes a linux amd64 asset whose name derives from the version
    [unverified].
  - It publishes a checksum asset to compare the digest with [unverified].
  - Whether it also publishes an attestation or signature that ties the
    binary to its source is unknown [unverified].
  - The official binary prints its version for `--version` [unverified].
  What each source proves, and the fallback:
  - The release's own checksum file proves only that the asset did not
    change after publication, because the same release publishes both.
  - The Go checksum database records module source hashes, not release
    asset digests, so it proves the tag's source and is never compared
    with the asset's digest.
  - With nothing that ties the binary to its source, the step comment
    says the digest is trust-on-first-use, and PR 1's body raises it.
  In every case the engineer takes the digest by hashing the downloaded
  asset in a separate terminal, not through a summarizing fetch tool
  — anchors: row38

Row 41 [assumption]: README.md already sends users to Homebrew or pyenv for
  the Python 3.14 floor rather than to a distro package [verified:
  README.md:116; _config.sh:73-74] — anchors: row5 — precedent for a
  non-distro requirement.

Row 42 [mechanism]: the Cursor adapter records shfmt among the tools whose
  directories make up the hooks' PATH — anchors: row43

Row 43 [assumption]: the adapter's hooks PATH, one fact per item:
  - It is built from the recorded tools' directories plus /usr/bin, /bin,
    /usr/sbin and /sbin [verified: docs/cursor-adapter.md:114].
  - `install` records each RECORDED_TOOLS entry in order [verified:
    cursor_adapter/core.py:222; cursor_adapter/tools.py:484-491].
  - .claude/rules/cursor-adapter-parity.md requires parity wherever the
    vendor allows [verified: that rule file].
  — anchors: row42

Row 44 [mechanism]: a new decision file records this choice, and the
  2026-10-18 decision gets a scope note rather than a supersession
  — anchors: row2, row9

Row 45 [assumption]: row 3's option description is the session's wording,
  not the engineer's: install.sh refuses to continue when shfmt is missing
  or below 3.14.0 and prints install routes, matching how it treats every
  other tool [unverified]. That precedent holds for the presence loop and
  the python3 and git floors, which exit 1, but the claude floor only warns
  [verified: install.sh:39-42, :84-98, :125-134, :50-72] — anchors: row3

Row 46 [assumption]: this plan ships as two PRs, one per tokenizer
  [engineer-verified: "Two PRs by tokenizer (Recommended)"] — anchors: root

Row 47 [assumption]: Dispatch 4 (Cursor adapter parity) stays in this plan
  [engineer-verified: "Keep Dispatch 4"] — anchors: row42

Row 48 [assumption]: edits under claude/.claude/** go live on `git pull`,
  before a consumer re-runs install.sh [verified: CLAUDE.md "Working in
  this repo"] — anchors: row6

Row 49 [assumption]: the lockout's three text changes are the consult's
  proposal, in the session's wording: widen README.md:134 to a newly
  required tool, model the CHANGELOG migration note on CHANGELOG.md:673-678
  with the docs/hooks.md:560 headless caveat, and give per-status recovery
  in docs/hooks.md § "Gate deadlock recovery" [engineer-verified: "yes,
  keep the architect's approach"] — anchors: row6

Row 50 [assumption]: the precedents for a lockout's text, one fact per
  item:
  - The bash-floor change shipped "Before pulling" and "If you have
    already pulled" steps [verified: CHANGELOG.md:673-678].
  - It shipped a README line [verified: README.md:134].
  - It shipped a runbook [verified: docs/hooks.md:572-578].
  - A missing jq already hard-blocks every gate [verified:
    docs/hooks.md:560; _lib.sh:429-441].
  — anchors: row49

Row 51 [assumption]: in an enforced main-tree session the worktree gate
  parses every git command before its read-only allowlist, which reads the
  parser's records, so a failing parse denies `git pull` and `git revert`
  too [verified: require-worktree-for-git-writes.sh:52-55, :293-316, :384]
  — anchors: row6

Row 52 [assumption]: the self-review evaluator, a turn-gate outside row 1's
  four gates, imports parse-git-command.py by path, so deleting that script
  forces it to change. It is a dependent of row 1's scope, not an addition
  to it [verified: evaluate-code-writer-self-review.py:54, :381-390;
  send-back-skipped-self-review.sh:2] — anchors: row1, row16

Row 53 [assumption]: the evaluator keeps its Bash `git diff` detection by
  running shfmt and reusing the git-records projection [engineer-verified:
  "I really like the evaluator as well"] — anchors: row36

Row 54 [assumption]: three evaluator details are the session's proposals,
  which the engineer's row-53 line approved, in the session's wording
  [unverified]:
  - The closure spawns shfmt only when the command holds both `git` and
    `diff`.
  - A missing shfmt or an unrecognized tree earns R5 credit and logs a
    distinct verdict instead of raising. The plan extends this to every
    other nonzero shfmt exit except 1.
  - The plan lists the behavior change that `# check git diff later` and
    `echo git diff` stop earning R5 credit. Row 55 corrects the echo half.
  — anchors: row53

Row 55 [assumption]: classify_git_segment, carried over verbatim, takes the
  first `git` word in any position of a segment, so `echo git diff` still
  yields a GIT diff record and keeps R5 credit. Only the comment form
  flips [verified: parse-git-command.py:186-194;
  test_send_back_skipped_self_review.py:268-274] — anchors: row54

Row 56 [mechanism]: the walker descends every list and object value of
  every node — anchors: row57 — a field allow-list drops any child position
  it does not name, which is the miss class this change exists to close.

Row 57 [assumption]: an assignment value, a declaration's arguments, a
  redirect target, a heredoc body, a `for` word list, `[[ ]]`, `(( ))`, a
  parameter default and an array element sit outside CallExpr.Args, so
  only a full descent reaches a command nested in them [unverified:
  Dispatch 1's child-position matrix confirms each] — anchors: row56

Row 58 [assumption]: every source-path extractor anchors on a literal flag
  prefix, so a word that loses its prefix yields no path and no deny
  [verified: _lib.sh:2646-2647, :2664-2665;
  deny-private-project-refs.sh:537-538, :564-567] — anchors: row27

Row 59 [mechanism]: _lib_shell_parse pipes shfmt straight into the module
  and maps the two PIPESTATUS values by Design item 1's ordered list
  — anchors: row21, row32 — one reason per item:
  - A broken shfmt fails on every command, so only its syntax-error exit
    becomes 3. Blaming the command for any other exit sends the agent into
    file workarounds that cannot succeed.
  - Without the 141 exception, a python3 that fails at once, such as a
    shim with no version set, would read as a shfmt fault whenever shfmt's
    write found the pipe closed.
  - Exit 1 is still not unique to a syntax error: a BusyBox `timeout`
    usage error also exits 1 [verified: _lib.sh:117-118]. The SessionStart
    probe, whose command is valid bash, reports a persistent one (row 80),
    and the recovery entry tells the two apart (Design item 9).
  - shfmt, a Go binary, dies of SIGPIPE when its stdout's reader has gone,
    rather than exiting with an error status [unverified: two plan
    reviewers saw 141 on the row 7 build; Dispatch 2's real-shfmt case
    confirms it in the repository].
  Set aside: capturing the JSON in a shell variable and handing it to
  python3 through a here-string. A here-string can need a writable temp
  directory, and docs/hooks.md:590 documents its failure as a cause the
  stowed hooks' deny messages do not name.

Row 60 [assumption]: the plan adds no scheduled workflow that tests newer
  shfmt releases [engineer-verified: "Cut it (Recommended)"] — anchors: root

Row 61 [assumption]: with no such workflow, a shfmt release that
  re-encodes the tree reaches a consumer through a package upgrade with no
  install.sh run and no advance warning. The strict check (row 24) then
  denies every parse on that machine until the consumer installs a build
  the module recognizes or pulls a fix. From PR 1, the SessionStart probe
  (row 80) names the failure at the next session start when the
  re-encoding touches a construct the probe holds. A session already
  running learns of it at its first deny [unverified: follows from Given
  2, row 24 and row 80] — anchors: row60

Row 62 [mechanism]: CI pins shfmt at the floor build, 3.14.0, and no job
  tests a newer release (row 60) — anchors: row4, row63 — the floor build
  is the oldest one install.sh accepts, so CI must show it works. A
  contributor's local run tests whatever newer build they have, because
  the module tests run on real shfmt (row 68).

Row 63 [assumption]: CI already pins git at the floor's major.minor and
  checks the runner's git against the pin under GITHUB_ACTIONS [verified:
  test_git_floor.py:344-387] — anchors: row62

Row 64 [mechanism]: a `cd` on either side of a pipe gets in-group 1
  — anchors: row65 — bash runs each pipe side in a subshell, so that `cd`
  never moves the parent's cwd. A git write on a pipe side keeps in-group
  0, so `git push 2>&1 | tail` still resolves.

Row 65 [assumption]: the consumer marks the cwd unresolvable after an
  in-group CD record, so every later write denies [verified:
  require-worktree-for-git-writes.sh:354-360, :395] — anchors: row64

Row 66 [assumption]: nested input grows shfmt's JSON with depth. A 6 KB
  command of 1,200 nested `{ }` groups produced 102.6 MB in 2.1 s, and a
  15 KB command at depth 3,000 was still running at an 8 s kill
  [unverified: a plan reviewer's measurement on one macOS machine, not
  rerun by the session] — anchors: row30

Row 67 [assumption]: shfmt ignores EditorConfig files once any parser flag
  is given, so `-ln bash` keeps a session directory's `.editorconfig` from
  changing the dialect [unverified: Dispatch 1's hostile-.editorconfig
  case confirms] — anchors: row12

Row 68 [mechanism]: the module tests run on real shfmt behind a shared
  require_shfmt(), which skips locally and fails under GITHUB_ACTIONS
  — anchors: row69 — a skip-only guard turns a CI run whose install step
  did not run green. Committed tree fixtures were set aside: they pin one
  build's output, need a regeneration step, and repeat what a real-shfmt
  run already checks. The hand-built trees, the module's exit-path cases,
  and the interpreter-isolation and capability-pin tests run without
  shfmt, so they never skip.

Row 69 [assumption]: require_direnv() and require_zsh() already skip
  locally and fail under GITHUB_ACTIONS [verified:
  claude/.claude/scripts/tests/conftest.py:133-159] — anchors: row68

Row 70 [assumption]: the worktree gate already spawns python3 for every
  command it parses, so shfmt's cost, about 30 ms (row 20), adds to it
  [verified: require-worktree-for-git-writes.sh:304] — anchors: row18

Row 71 [assumption]: code-writer-self-review-send-back.md § "Log verdicts"
  is the single home of the evaluator's log vocabulary [verified:
  docs/design-decisions/code-writer-self-review-send-back.md:88]
  — anchors: row54

Row 72 [assumption]: PR 1 projects about 4,800 changed lines and PR 2
  about 2,750, so neither falls under 400. The engineer chose two PRs of
  that size, not a split that brings each below 400 [unverified: the
  session's bottom-up estimate in Critical files' `Projected diff:` line]
  — anchors: row46

Row 73 [assumption]: which PR goes first and what each carries is the
  session's proposal, backed by an architect consult, in the session's
  wording rather than the engineer's [unverified]. PR 1 carries the
  redaction gates, the shared parse path, the install check, CI's pinned
  build, the Cursor adapter's PATH and the shared docs. PR 2 carries the
  git-records projection, the worktree gate, the evaluator, SHFMT_ARGV and
  the deletion of parse-git-command.py — anchors: row46

Row 74 [assumption]: the strict check keeps its per-type key sets, its
  unknown-key rejection and its CallExpr conservation count as Design item
  2 states them [engineer-verified: "Keep key sets (Recommended)"]
  — anchors: row24

Row 75 [mechanism]: PR 1 carries every change that makes shfmt a
  requirement: the install check, the SessionStart check, CI's pinned
  build, and the Cursor adapter's PATH and shfmt check (row 95)
  — anchors: row48, row73 — PR 1's
  gates are the first to call shfmt, and they go live on `git pull` (row
  48), so a consumer must be able to install, resolve and diagnose shfmt
  from that PR on. PR 2 carries all git-records code, so the moved
  classifiers never sit in two files on the default branch.

Row 76 [assumption]: a hook never fails silently [engineer-verified:
  "hooks should never silently fail."] — anchors: root

Row 77 [assumption]: a SessionStart check, not each hook's own comments,
  is where the hooks' dependencies are checked [engineer-verified: "It's
  wrong foundation for each individual hook to comment on their
  dependencies.", "sessionstart as the place to make sure"] — anchors: root

Row 78 [assumption]: how the plan applies rows 76 and 77 is the session's
  reading, relayed in the session's wording [unverified]:
  - A warn-only SessionStart check verifies python3, shfmt's presence and
    its 3.14.0 floor, and lands in PR 1. Row 94 makes it one hook.
  - Each gate's deny keeps naming its cause. The dependency diagnosis
    lives in the SessionStart notice and the one recovery entry, not in
    each gate's comments or header.
  - The self-review evaluator keeps its credit-on-fault path.
  — anchors: row76, row77

Row 79 [mechanism]: one informational SessionStart hook,
  check-hook-dependencies.sh, which is check-python-floor.sh renamed and
  extended to shfmt — anchors: row77, row78, row83, row94 — it names a
  broken parse path at session start instead of at the first deny, and
  python3 and shfmt, both dependencies of the parse path, share one home.
  The rename moves the hook's registration, Cursor parity key, test file
  and citations, and Critical files names each. Set aside:
  - Deny-time reasons alone, which already name the cause but put the
    first signal at a denied commit, where row 77 puts it at SessionStart.
  - A second hook, check-shell-parser.sh, beside check-python-floor.sh,
    which splits the parse path's dependencies across two SessionStart
    homes (row 94).
  - Extending check-python-floor.sh without renaming it, which leaves a
    hook named for python3 checking shfmt.

Row 80 [mechanism]: the probe is one compound command, held in _lib.sh
  beside its expected words, parsed once through _lib_shell_parse and
  compared with those words — anchors: row79, row24, row96 — it runs the
  gates' own path, so it catches what a version compare cannot. Design
  item 12 lists what it catches and what holds it complete. One parse
  keeps the cost to one shfmt and one python3 start. Row 33 set aside an install-time probe because
  install.sh would have to source the hooks' _lib.sh in a child bash.
  This hook already sources it, and it runs at every session start, not
  once at install. Lighter primitives set aside: `command -v shfmt` alone
  sees only absence, and the version compare alone misses a build with no
  version and a re-encoding at or above the floor.

Row 81 [mechanism]: the shfmt floor and its compare live in _config.sh
  beside the python3 floor — anchors: row4, row79 — install.sh and the
  shared shfmt check, which the SessionStart hook and the Cursor report
  both call, compare with it, so the floor has one home.
  install.sh and check-python-floor.sh already share _PYTHON_FLOOR_*,
  _python_version_meets_floor and _python3_floor_status that way
  [verified: _config.sh:70-113; install.sh:30, :80-83;
  check-python-floor.sh:32].

Row 82 [mechanism]: check-hook-dependencies.sh checks python3 first and
  runs the shared shfmt check only when python3 passes. The shared check
  runs the probe before the version compare, and a cap kill in the probe
  ends it — anchors: row79, row80 — one reason per item:
  - The probe runs python3, so a python3 fault would also fail the probe,
    and one cause would print two notices.
  - Probing first means a hung shfmt costs one capped call, not two. A
    version compare that ran first would read a hung shfmt as no version
    and then run the probe on the same binary: about 11 seconds, past the
    10-second registration timeout, where probing first takes about 7.
    Design item 11 gives the bounds and the cap-tool condition they hold
    under [verified: _lib.sh:69-72, :136-138].
  - A below-floor version still wins over a probe failure, because it
    names the likelier cause.
  The cost: a machine where both python3 and shfmt fail learns of shfmt
  at the first session start after python3 is fixed.

Row 83 [assumption]: check-python-floor.sh is an informational
  SessionStart hook, one fact per item:
  - Every path exits 0 [verified: check-python-floor.sh:4-5].
  - Its registration's startup|resume matcher and its in-script .source
    filter stay in sync [verified: check-python-floor.sh:6, :24-27;
    claude/.claude/settings.json:211-219].
  - Only the floor constants and a digit-validated version reach its
    output [verified: check-python-floor.sh:7].
  - Its header records that it may exceed the 100 ms budget [verified:
    check-python-floor.sh:14].
  — anchors: row79

Row 84 [mechanism]: each gate's header states its fail posture in one line
  and cites docs/hooks.md § "Gate deadlock recovery". No gate header lists
  the parse path's tools or how to repair one — anchors: row77 — the
  diagnosis has one home, and the SessionStart notice and every deny cite
  it. The worktree gate's three python3-less known gaps name a machine
  where the parse path cannot run instead (Design item 4).

Row 85 [mechanism]: in-group on a CD record means "not threaded", and a
  `cd` is threaded only where the old parser threaded it and bash
  certainly ran it in the parent shell. Every other `cd` form emits
  in-group 1, so later writes deny. On a GIT record, in-group 1 means the
  write cannot be judged — anchors: row64, row65, row87, row88, row99,
  row100 — the gate's own threat model denies rather than guesses when a
  write's cwd is ambiguous (require-worktree-for-git-writes.sh:21-26),
  and the cooperative way through, a plain `cd <worktree> && git ...`,
  still threads. Design item 2 lists the rules, and no `cd` shape turns
  from deny to allow against the old parser. Set aside:
  - Marking every compound construct's GIT records in-group 1. The
    consumer denies any non-read GIT record with in-group 1
    (require-worktree-for-git-writes.sh:395-397), so honest writes in
    `{ }`, `time` and `if` bodies, which run in the parent shell, would
    turn from allow to deny.
  - Passing a `cd` through `{ }`, `time` and `!` as if at top level. It
    would turn `{ cd /wt && git push; }` in a main-tree session from deny
    to allow, because the old parser recorded no CD for it (row 87).
  - Threading a `cd` right of `&&` past the end of its list, as the old
    parser does. When the left operand fails, the `cd` never runs, and a
    later statement runs in the original cwd.

Row 86 [assumption]: `-ln bash` rejects dialect-only node types.
  `@test "x" { echo hi; }` exits 1 under `-ln bash` and yields a TestDecl
  under `-ln bats` [unverified: a plan reviewer's run on the row 7 build;
  Dispatch 1 re-checks it at 3.14.0] — anchors: row24

Row 87 [assumption]: the old parser's behavior, scoped by record type:
  - It sets in-group only inside parentheses and backticks, and finds
    `git` at any position of a segment, so `time git commit -m x` yields
    a GIT record at in-group 0 today [verified:
    parse-git-command.py:298-302; test_parse_git_command.py:411-415].
    This supports "as the old parser did" for git detection only.
  - It records a CD only for a segment whose first token is `cd`, so a
    `cd` after `{`, `time`, `!`, an assignment or a keyword yields no CD
    record today [verified: parse-git-command.py:237-245].
  — anchors: row85

Row 88 [assumption]: in a linked-worktree session, a command with no `cd`
  word, `-C`, `(` or backtick skips the parser once the held lock passes
  the collision guard. The in-group rules therefore reach a worktree
  session only for a command that carries one of those, or while its lock
  is absent [verified: require-worktree-for-git-writes.sh:272-286]
  — anchors: row85

Row 89 [mechanism]: the evaluator credits R5 and logs a reason on every
  failure of its shfmt call or its projection, and caps the command at
  MAX_COMMAND_BYTES — anchors: row53, row90 — a parse fault then degrades
  R5 alone. An exception out of assess would fail the whole send-back
  open, logged only as an evaluator exit status
  (send-back-skipped-self-review.sh:78-82). Sending the writer back with
  a visible reason was set aside: the writer cannot repair shfmt, and the
  send-back would spend the cycle's one send-back.

Row 90 [assumption]: send-back-skipped-self-review.sh is fail-open by its
  own header, one fact per item [verified:
  send-back-skipped-self-review.sh:2-4, :11, :18; the architect did not
  map each fact to one line]:
  - Every failure allows.
  - Only the once-per-cycle send-back blocks.
  - The second return of a cycle goes through.
  - It is a workflow check for a cooperative writer, not a security
    boundary.
  — anchors: row89

Row 91 [assumption]: the SessionStart notice is the early warning for a
  parse fault the evaluator credits [engineer-verified: "SessionStart
  notice is the early warning."], answering whether the evaluator's
  log-only credit verdict meets row 76. The plan reads this as keeping
  the evaluator fail-open and log-only (rows 89-90), so a fault that
  starts mid-session reaches only the log — anchors: row76, row89

Row 92 [assumption]: the Cursor adapter's handling of the python3 check,
  one fact per item:
  - Its sessionStart entry and its `check` command share tool_findings
    [verified: cursor_adapter/check.py:340-378, :402, :595].
  - It declines check-python-floor.sh's registration [verified:
    parity-exceptions.json:18; test_cursor_adapter_gate_matrix.py:1368-1375].
  - The reason it declines is that the entry probes the hooks' python3
    against the same floor [verified: parity-exceptions.json:18].
  — anchors: row93

Row 93 [mechanism]: under Cursor, check-hook-dependencies.sh's
  registration stays declined. Its parity-exceptions.json:18 entry is
  re-keyed to the new name, and its detail says the adapter's
  sessionStart entry probes python3 against the same floor and runs the
  same shfmt check (Design item 8) — anchors: row42, row92, row96 — the
  sessionStart report stands in for both of the hook's checks, so
  registering the hook too would report each fault twice.

Row 94 [assumption]: the SessionStart dependency check is one hook named
  check-hook-dependencies.sh, not a second hook beside
  check-python-floor.sh [engineer-verified: "check-hook-dependencies is
  obviously the correct thing to do."], answering the session's question
  whether the check should be one renamed hook or two — anchors: row77

Row 95 [assumption]: the Cursor adapter gets the shfmt floor check and
  the probe, at parity with Claude Code [engineer-verified: "uhh we need
  to make sure we are shipping features with Cursor and Claude Code
  parity... why would we not do that"], answering whether Cursor gets
  them. Landing them in PR 1 follows row 75 — anchors: row42

Row 96 [mechanism]: the adapter's tool_findings, which `check` and the
  sessionStart entry share, runs _lib_shfmt_dependency_cause through one
  bash probe that sources the hooks' _lib.sh — anchors: row95, row80,
  row81 — the floor compare, the probe literal and the cause wording then
  each keep one home, shared with the SessionStart hook. Set aside:
  - A Python floor reader beside python_floor_status, plus a Python copy
    of the probe command and its expected words. The probe has to run
    _lib_shell_parse anyway, and a second copy of a security-relevant
    literal drifts.
  - Registering check-hook-dependencies.sh under Cursor. Its python3
    check repeats the report row 92 stands in for, and its caps (row 82)
    exceed the entry's per-probe bound.
  - A presence check alone, which misses a below-floor build and a
    re-encoded tree.

Row 97 [assumption]: the adapter's sessionStart entry budgets its worst
  case against CHECK_ENTRY_TIMEOUT_SECONDS, one term per item:
  - The stdin read, MIN_DEADLINE_SECONDS, 2 seconds [verified:
    hook-shim.py:43].
  - Each probe at PROBE_BOUND_SECONDS, 2 seconds [verified:
    cursor_adapter/core.py:22].
  - Three probes today [verified: cursor_adapter/check.py:340-378].
  - The host walk, HOST_WALK_BOUND_SECONDS, 1 second [verified:
    cursor_adapter/core.py:27].
  - 1 second of headroom, so the sum is exactly CHECK_ENTRY_TIMEOUT_SECONDS,
    10 [verified: cursor_adapter/core.py:24;
    test_cursor_adapter_install_prerequisites.py:535-558].
  A fourth probe makes 12 — anchors: row96

Row 98 [assumption]: Cursor honors a 12-second `timeout` on the
  sessionStart hooks.json entry as it honors 10 [unverified: the session
  confirms it from Cursor's hooks documentation before Dispatch 4]
  — anchors: row97

Row 99 [assumption]: the engineer delegated the rule for a `cd` inside a
  compound shape [engineer-verified: "Ask the architect - what fits the
  threat model of a cooperative agent?"], answering how such a `cd`
  should be judged — anchors: root

Row 100 [assumption]: the architect consult's recommendation, in the
  architect's wording, not the engineer's: deny when the effect of a `cd`
  is uncertain, and thread a `cd` only where the old parser threaded it
  and bash certainly ran it in the parent shell, so no `cd` shape flips
  from deny to allow. Design item 2 lists the rules, with the list-end
  and loop records the session added [unverified: the session applies it
  under row 99's delegation; the engineer has not reviewed it]
  — anchors: row99

Row 101 [assumption]: Claude Code's workspace trust for hooks, one fact
  per item [unverified: quoted from the round-3 ciso-reviewer finding,
  which fetched both pages on 2026-11-21. The architect fetched neither,
  and the session confirms the lines before Dispatch 5]:
  - code.claude.com/docs/en/hooks.md, "Security considerations >
    Workspace trust": in an interactive session Claude Code "holds back
    hooks from every settings file, including your own
    `~/.claude/settings.json`, until you accept the workspace trust
    dialog".
  - The same section: in `-p` or SDK sessions it "never shows the dialog
    and treats the folder as trusted".
  - The same page: "Handlers run in the current directory with Claude
    Code's environment."
  - code.claude.com/docs/en/permissions.md, "What runs before you trust a
    folder": settings-file hooks are "Used" both when only a parent
    folder is trusted and under `claude -p` in a never-trusted folder.
  These settle docs/hooks.md:538's working-directory premise and :539's
  pre-trust premise. Whether a repository's settings `env` block can
  override PATH for hooks, and whether a shfmt shim can select a
  repository-supplied binary, stay unconfirmed — anchors: row79

Row 102 [mechanism]: a cap kill takes the tool-fault sentence and no file
  workaround — anchors: row30, row31, row66 — a hung shim or binary is
  the likelier cause, and moving content to a file cannot fix it. That is
  a likelihood, not a bound: on the one machine row 31 measured, a flat
  command at the byte cap took about 2.35 s, but python3 shares the same
  cap (Design item 1), and a loaded machine can push a near-cap command
  past it. The recovery entry's cap-kill item covers that case (Design
  item 9). Status 7 keeps the workaround, because content moved to a file
  brings the command under the byte cap.

Row 103 [mechanism]: _lib_shell_parse_failure_clause returns the cause
  only, and each caller adds its own tail — anchors: row77, row79, row96
  — the deny reason adds the tool-fault sentence or the file workaround,
  and the SessionStart notice and the Cursor report add their own
  reporting duty. The cause wording keeps one home, and no session-start
  text carries a gate's stop-and-ask instruction, which the notice's
  reporting-only agent text would contradict (check-python-floor.sh:46).

Row 104 [mechanism]: the worktree gate's fast-path relocation check
  matches `pushd` and `popd` as well as `cd` — anchors: row85, row88 — a
  linked-worktree session's `pushd /main && git push` otherwise skips the
  parser, so row 85's rules never see it. `builtin cd` and `command cd`
  already carry the `cd` word.

Row 105 [assumption]: the worktree gate exits 0 before any parse unless
  the command holds `git` with a non-alphanumeric character or a string
  edge on each side, so `g\it push` and `gi""t push` are allowed today
  and after PR 2. The shlex-era gate has the same prefilter [verified:
  require-worktree-for-git-writes.sh:223]. The header lists it as a known
  gap, and module-level tests still pin those spellings' GIT records
  — anchors: row16

Row 106 [assumption]: the gates parse bash only, and the plan accepts and
  records the zsh gap row 15 describes [engineer-verified: "Accept and
  record (Recommended)"], answering the session's question how the plan
  should handle the zsh/bash gap. What that option proposed is the
  session's, restated here in the plan's words [unverified]: keep
  `-ln bash`, and record as an accepted residual, in the decision file,
  the README's Requirements note and the CHANGELOG, that zsh-only syntax
  denies with the status-3 wording, that a construct bash and zsh read
  differently can yield words zsh never sees, that CLAUDE_CODE_SHELL set
  to a bash path forces bash, and that a per-shell dialect is a follow-up
  — anchors: row15

Row 107 [assumption]: PR 2 does not wait for PR 1 to gain field time
  [engineer-verified: "Don't wait (Recommended)"], answering the
  session's question whether PR 2 should wait for field time. What that
  option proposed is the session's, restated here in the plan's words
  [unverified]: PR 2 branches from the default tip once PR 1 merges, as
  "Two PRs" sequences it, rather than after a period of PR 1 in use
  — anchors: row46

Row 108 [mechanism]: a differential table compares today's
  _lib_command_words with the new `words` projection before Dispatch 2
  changes any gate test's expectation, and the session puts every row
  whose gate verdict or extracted path strings change to the engineer
  — anchors: row18, row56, row113 — the full descent (row 56) emits the
  words of a command nested in a quoted `$(...)` or in an unquoted
  heredoc's backticks, so a source flag inside them now reaches the
  extractors and can deny, and dropping the fast path (row 18) changes
  which tokenizer judges every command. A changed path string can hide
  behind an unchanged modeled verdict, because the model treats every
  path as missing. Set aside:
  - Relying on Dispatch 2's test failures, which show a changed verdict
    only where an existing test pins that command.
  - Scoping flag reads to the gh or git simple command, which changes
    the gates' behavior beyond the tokenizer swap (Out of scope).

Row 109 [mechanism]: _lib_shell_parse checks python3 before shfmt
  — anchors: row76, row82 — the SessionStart hook checks python3 first
  (row 82), and the worktree gate's own python3 check runs before its
  parse (Design item 4). The shared path in the same order makes every
  gate and the notice name the same tool on a machine missing both.

Row 110 [mechanism]: _lib_shfmt_dependency_cause takes its parse and
  version caps as required arguments, and _lib_shell_parse takes an
  optional cap that defaults to _lib_capped's 5 s. The SessionStart hook
  passes 5 and 2, and the Cursor probe passes half of
  PROBE_BOUND_SECONDS for each — anchors: row96, row97 — run_probe ends
  only the child it started, at PROBE_BOUND_SECONDS [verified:
  cursor_adapter/tools.py:59-71]. Caps above that bound leave timeout and
  shfmt running past the entry and turn a hang the caps would name into
  the generic stall finding. The fourth probe still counts
  PROBE_BOUND_SECONDS in the entry's worst case, so the inner caps do not
  remove row 97's 12-second sum

Row 111 [assumption]: on a machine with neither `timeout` nor `gtimeout`,
  check-hook-dependencies.sh warns at session start [engineer-verified:
  "Warn at SessionStart (Recommended)"], answering the session's question
  how to handle a hung shfmt or python3 stalling each gated command for
  the harness's 600 s default on such a machine. What that option
  proposed is the session's, restated here in the plan's words
  [unverified]:
  - One line in the check-hook-dependencies notice when neither tool is
    on PATH.
  - The 600 s stall listed as an accepted residual in the decision file
    and the README.
  The plan places the two `command -v` calls in the hook, and the line
  names no gate (Design item 11) — anchors: row76, row79

Row 112 [assumption]: under Cursor, a missing cap tool is already caught,
  one fact per item:
  - `install` refuses a machine whose `timeout` or `gtimeout` is not GNU
    coreutils [verified: cursor_adapter/tools.py:522-526].
  - tool_findings reports an install record that names neither [verified:
    cursor_adapter/check.py:347-349].
  — anchors: row111

Row 113 [assumption]: shfmt's JSON may not carry a word's non-UTF-8 byte,
  one fact per item:
  - Go's `encoding/json` replaces invalid UTF-8 with U+FFFD [unverified:
    two plan reviewers inferred it from Go's documentation, and neither
    ran shfmt on such a byte].
  - The splitter round-trips such a byte today [verified:
    test_split_command_words.py:228-231].
  Dispatch 1's dump settles the first item with a word holding the byte
  0xFF. If shfmt replaces it, a path holding such a byte denies as
  unreadable, and the CHANGELOG says so (Design item 9) — anchors: row26,
  row108

Row 114 [assumption]: the zsh miss rests on row 106's acceptance, not on
  docs/hooks.md's cooperative-agent waiver, one fact per item:
  - That waiver covers only a shape a cooperative agent would never emit
    [verified: docs/hooks.md:13, :55].
  - Repairing a miss of a shape a cooperative agent does emit stays in
    scope for every tier [verified: docs/hooks.md:47].
  - A waived finding is recorded on the gate's header in the same PR, and
    for these gates their Known-gaps section is that place [verified:
    docs/hooks.md:43, :55].
  - Nothing in this plan shows that a cooperative agent whose Bash tool
    runs zsh (row 15) never emits a shape bash and zsh read differently.
    The zsh-shape rows of Verification 1 and 3 show which shapes change
    words, not whether an agent emits them [unverified: no transcript was
    checked].
  — anchors: row106

Row 115 [assumption]: nested input's memory cost stays an accepted
  residual, recorded in the decision file, only while the one nested case
  Verification 8 measures peaks under that step's threshold. A peak over
  it puts a byte bound to the engineer (row 117). The case and the
  threshold are the session's proposal, not an engineer answer
  [unverified] — anchors: row66, row117

Row 116 [assumption]: the plan accepts the zsh miss row 114 describes as
  the engineer's own exception [engineer-verified: "Accept as my exception
  (Recommended)"], answering the session's question about that miss on
  the gates whose tier line lists `irreversible`, which no tier waiver
  covers. What that option proposed is the session's, restated here in
  the plan's words [unverified], one fact per item:
  - Row 106's acceptance stands as the engineer's own exception to
    docs/hooks.md:47's rule that repairing a miss of a shape a
    cooperative agent does emit stays in scope for every tier (row 114).
  - A per-shell dialect stays a listed follow-up (Out of scope).
  — anchors: row114

Row 117 [assumption]: Verification 8 measures nested input's memory cost
  [engineer-verified: "Measure in Verification 8"], answering the
  session's question how to treat that cost, which rests on row 66's JSON
  of about 17,000 times the command's size and which no step measured
  (row 115). What that option proposed is the session's, restated here in
  the plan's words [unverified]: one nested-input case whose peak memory
  PR 1's body records, with a byte bound decided only if that number is
  large. The case, its commands and the threshold that counts as large
  are the session's too, in Verification 8 — anchors: row66
```

## Critical files

There are seven `code-writer` dispatches. Dispatches 1-5 build PR 1 and Dispatches 6-7 build PR 2, so each PR's dispatches are contiguous and each PR leaves every gate wholly on one tokenizer. Each dispatch ends with `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py`. Every dispatch runs after the one before it, and a later dispatch may edit a file an earlier one edited.

This plan file ships in PR 1. Each session step's outcome lands in its PR's body, not in this file, so `require-plan-review.sh` does not re-fire before Dispatch 1.
- Row 15's vendor lines and rows 26, 40, 57, 59's SIGPIPE item, 67, 86, 98, 101 and 113 stay `[unverified]` here, and PR 1's body records how each settled. Row 15's other `[unverified]` part records what the vendor pages do not state, and no step settles it.
- PR 1's body also states the zsh acceptance rationale beside row 106's quoted answer (row 114).
- Before any table, timing or command output goes into a PR body, the session replaces temp-directory, user, tool, home and checkout paths with placeholders, because the redaction detectors cover only home-rooted paths and the gate tests build commands from temp paths that embed the OS username.
- An outcome that contradicts a row stops the session, which then edits this file and re-runs `/plan-review`.
- PR 2 starts with this file committed and does not edit it. PR 2's body records the engineer's answer on the changed-case table, in their words.

### PR 1 — the redaction gates

The order, one reason per step:
- Dispatch 2 follows Dispatch 1, because it wires the gates to Dispatch 1's module.
- Dispatch 3 follows Dispatch 2, because its shared shfmt check calls Dispatch 2's `_lib_shell_parse`.
- Dispatch 4 follows Dispatch 3, because the Cursor report calls Dispatch 3's shared check.
- Dispatch 5 runs last, because the renamed hook calls the same check and Dispatch 5 edits files Dispatches 3 and 4 edit.
- PR 1's branch is first pushed after Dispatch 5, because Dispatch 1's `require_shfmt()` fails CI until Dispatch 3's pin step exists.

Four session steps sit between the dispatches:
- After Dispatch 1, put every marked row of Dispatch 1's `words` differential table to the engineer (Verification 1).
- Before Dispatch 3, confirm row 40's items on the release page. The engineer then downloads the asset in a separate terminal, hashes it, and compares the hash with the release's checksum file where one exists. The digest the engineer reports becomes the CI literal, and PR 1's body records what each source proved (Design item 7).
- Before Dispatch 4, settle row 98 from Cursor's hooks documentation.
- Before Dispatch 5, confirm row 101's quoted lines and row 15's two vendor lines on their pages, and record them in PR 1's body.

**Dispatch 1 — the projection module and `words`.** Its first step dumps `shfmt -ln bash --to-json` for a corpus that covers every construct in Design item 2, `git-records` constructs included, and a word holding the byte 0xFF, and settles rows 26 and 113 from that dump. It reads `mvdan.cc/sh/v3/syntax` at v3.14.0 for the node types, operators and struct key sets, and settles row 86.
- Create `claude/.claude/hooks/shell-syntax-tree.py` with the strict check, `BASH_REJECTED_NODE_TYPES`, the walker, word flattening with its backslash decoder, the `words` projection, and UTF-8 stdin and stdout. The commit that adds the decoder justifies hand-rolling it in its message (Design item 2).
- `claude/.claude/hooks/_lib.sh`: `_LIB_SHFMT_ARGV` only (Design item 1), so every real-shfmt test in both PRs runs the production argv from the start.
- `git mv` `claude/.claude/hooks/tests/test_split_command_words.py` to `claude/.claude/hooks/tests/test_shell_syntax_tree_words.py`, then rewrite it as tests on real shfmt behind `require_shfmt()`:
  - Convert each xargs-divergence and pre-pass case to the words bash sees. Delete a case only when it tests deleted code alone, and list each deleted case with its reason in PR 1's body.
  - Rewrite `TestResidualShapes` to assert the words bash sees.
  - Add the attached-flag matrix, the realistic smoke set, and the backslash cases of Verification 6, the real-bash comparison included.
- Create `claude/.claude/hooks/tests/test_shell_syntax_tree_contract.py`. It never skips as a whole:
  - Behind `require_shfmt()`: the conformance corpus, the `BASH_REJECTED_NODE_TYPES` samples, the hostile-`.editorconfig` case, and the child-position matrix. The matrix is one fixture table of construct, child position and command kind, a git write or a `cd`, parametrized over projections. PR 1 ships its `words` assertion.
  - Without shfmt: the hand-built-tree cases, the module's exit-path and encoding cases, and the interpreter-isolation and capability-pin tests moved from the old splitter test file.
  - The completeness tests: `KNOWN_NODE_TYPES` against the corpus's `Type` values in both directions, and every `KNOWN_NODE_TYPES` entry either in the matrix or in a named set of types that hold no command.
- `claude/.claude/tests/helpers.py`:
  - `require_shfmt()`, which skips with a reason naming `README.md` § "Requirements" and fails under `GITHUB_ACTIONS` (row 68).
  - `production_shfmt_argv()`, which sources `_lib.sh` and returns `_LIB_SHFMT_ARGV`. The conformance corpus, the child-position matrix and the hostile-`.editorconfig` case run shfmt with it.
  - One stub-shfmt writer beside `write_prewarmed_stub` (`helpers.py:3111`). It prints a given tree or a given version line, or exits with a given status, optionally after a given stderr line or a hang. It logs its argv, its stdin and its working directory. Every stub-shfmt test in both PRs uses it.
- `claude/.claude/hooks/tests/conftest.py`: a `pytest_report_header` line when shfmt is not on PATH, so a local run names the cause once before any gate test fails.
- Leave `parse-git-command.py` and `test_parse_git_command.py` untouched. PR 2 moves them.
- Deliverable to the session: the `words` differential table of Verification 1. A scratch script outside the repository, which is not committed, runs the base commit's `_lib_command_words` from a scratch worktree against `shfmt` piped into the module's `words`, and applies each gate's source-path extraction to both word streams. Verification 1 gives its inputs and its two `xargs` builds. PR 1's body carries the table.
- Reuse: the shape of `require_direnv()` and `require_zsh()` at `claude/.claude/scripts/tests/conftest.py:133-159` for `require_shfmt()`.

**Dispatch 2 — wire the redaction gates.**
- `claude/.claude/hooks/_lib.sh`: `_lib_shell_parse`, `_lib_shell_syntax_tree_path`, `_lib_shell_parse_failure_clause`, `_lib_shell_parse_tool_fault_sentence`, the deny reason's three tails and the `_lib_command_words` cutover (Design items 1 and 3).
- Delete `claude/.claude/hooks/split-command-words.py`.
- Header comments only: `claude/.claude/hooks/deny-escaped-backticks-in-pr-body.sh`, `claude/.claude/hooks/deny-pii-in-commits.sh` and `claude/.claude/hooks/deny-private-project-refs.sh`. Each replaces its splitter and `xargs` lines with one line: a parse failure denies with a reason that names the cause, and `docs/hooks.md` § "Gate deadlock recovery" gives the recovery. None lists the parse path's tools (row 84).
- Tests under `claude/.claude/hooks/tests/`:
  - `test_lib_command_words.py`:
    - The shfmt status matrix, the status-distinctness check, the argv check, and the clause and deny-reason parametrizations at :555-572 extended to 2, 5, 6, 7, 8, 127, the cap kills and the default arm's unlisted statuses. The xargs fast-path cases go.
    - The pipe-status cases of Verification 6, run under `set -uo pipefail` as the gates run: shfmt's nonzero status deciding, a tree printed before a nonzero shfmt exit, a python3 that exits first behind a shfmt that dies of SIGPIPE with a real-shfmt case that confirms row 59's SIGPIPE item, and a self-SIGPIPE stub behind a python3 that exits 0.
    - The per-stage stderr cases, the python3-first order, and the zsh-only case of Verification 6.
    - The `timing` cap cases, with `write_scaled_timeout_shim` and `assert_cap_engaged` keyed by command: a hung shfmt, and a hung python3 behind a printing shfmt stub, each return the cap-kill status with empty stdout. The python3 hang case at :655-678 is retargeted to the second.
    - The real-shfmt invalid-shape cases of Verification 6, and the status-4 and both-tools-absent cases.
    - The old status-4 cases, such as the one at :324, re-pointed from the python3 shim to a stub shfmt whose tree holds no command.
    - Each tool-fault sentence cites a heading `heading_texts` (`helpers.py`) finds in `docs/hooks.md`, as `test_bash_floor.py:414-421` checks its citations.
  - `test_hook_alignment.py`: the module docstring at :36-55 and the bare-xargs docstrings at :113-118 and :1634-1635.
  - An existing expectation in `test_lib_command_words.py` or a gate test changes only after the engineer answers on Verification 1's table, and each change maps to a row of it.
  - `test_deny_pii_in_commits.py`, `test_deny_private_project_refs.py` and `test_deny_escaped_backticks_in_pr_body.py`: rename the xargs-specific cases. Per gate, add the missing-shfmt, unrecognized-tree, parse-failure-text and tree-then-nonzero-exit cases, and the shfmt-absent allow cases of Verification 6, which replace the xargs-specific python3-absent allow cases (`test_deny_private_project_refs.py:4583`, `test_deny_escaped_backticks_in_pr_body.py:322`).
    - The silent-python3 cases (`test_deny_pii_in_commits.py:1352`, `test_deny_private_project_refs.py:4511`, `test_deny_escaped_backticks_in_pr_body.py:299`) move to a stub shfmt whose tree holds no command, behind real python3, and assert the status-4 wording. A python3 stub that exits at once behind a shfmt that can still write races shfmt's SIGPIPE, so no case uses one outside the SIGPIPE cases of Verification 6.
    - One gate keeps a case on the SIGPIPE-exception outcome, and one gate runs the per-stage stderr case.
  - `_cursor_payloads.py`: `recorded_tool_paths` at :591 gains `shfmt` (Design item 8).
  - `test_cursor_adapter_gate_matrix.py`, only if its rows for the three redaction gates still fail.
  - `test_scaled_timeout_shim.py`, only if its exact-count assertions at :351-424 change with the two new capped calls.
- `claude/.claude/tests/helpers.py`: remove `xargs_is_gnu`, whose last callers go in Dispatches 1 and 2.
- Reuse: `_lib_capped`, `_lib_status_consistent_with_cap_kill`, the readlink hop in today's `_lib_command_words_tokenizer_path`, the `build_path_without` and `write_prewarmed_stub` helpers that the worktree gate's python3-absent tests already use, and `write_scaled_timeout_shim` and `assert_cap_engaged` from the existing cap tests.

**Dispatch 3 — install, CI, the shared floor and the shared shfmt check.**
- `claude/.claude/hooks/_config.sh`: the shfmt floor constants, `_shfmt_version_meets_floor` and `_shfmt_floor_status`, with a one-line comment naming `install.sh` and `_lib_shfmt_dependency_cause` as its callers, as the python3 floor's comment at :70 does (Design item 6). Dispatch 5 renames the hook and updates :70.
- `claude/.claude/hooks/_lib.sh`: `_lib_shell_parse_probe` with its probe command and expected words, `_LIB_SHELL_PARSE_PROBE_MISMATCH_STATUS` and its clause, `_LIB_SHFMT_BELOW_FLOOR_STATUS`, and `_lib_shfmt_dependency_cause` with its two cap arguments (Design item 12, row 110). The probe holds every command-holding type of Dispatch 1's child-position matrix.
- Create `claude/.claude/hooks/tests/test_lib_shfmt_dependency_cause.py`, which sources `_lib.sh` and calls the two functions directly. It holds the shared check's status matrix of Verification 6, so the hook and adapter tests keep one case per branch. Its probe-coverage case reads the command-holding types from the contract test's matrix table, so the two cannot drift.
- `claude/.claude/hooks/tests/test_scaled_timeout_shim.py`, only if its exact-count assertions at :351-424 change with the shared check's capped version call.
- `install.sh`: the `shfmt-floor-check` block, and the cap-tool warning at :1052 (Design item 6).
- Create `claude/.claude/hooks/tests/test_shfmt_floor.py`. It holds Design item 7's CI checks, and direct tests of the two `_config.sh` functions, run by sourcing `_config.sh`, over the version spellings of Verification 6.
- `claude/.claude/hooks/tests/test_git_floor.py`: `run_install_sh_in_tmp_repo` gains an optional shfmt stub that reports the floor by default, because the run's PATH is the stub directory plus `/usr/bin:/bin` (`test_git_floor.py:278`). `test_python_floor.py` imports it and needs no change, because the new parameter has a default.
- `.github/workflows/tests.yml`
- Reuse: `_python_version_meets_floor` and `_python3_floor_status` as the model, the git floor block at `install.sh:105-130`, `run_install_sh_in_tmp_repo` and the INSTALL_TEST_FIXTURE extraction helpers in `test_git_floor.py`, imported rather than copied, `TestPinStepRunBody`'s stub pattern, and the pinned-git step's comment pattern.

**Dispatch 4 — Cursor adapter parity (Design item 8).**
- `claude/.claude/scripts/cursor-adapter/cursor_adapter/core.py`: `RECORDED_TOOLS` with `shfmt` last, the shfmt check's fixed bash program beside `PROBE_BASH_PROGRAM` (:219), which takes the hooks directory and caps of half `PROBE_BOUND_SECONDS` as positional parameters, `CHECK_ENTRY_TIMEOUT_SECONDS` at 12 with its comment at :23 rewritten, and the probe count in the comment at :25-26.
- `claude/.claude/scripts/cursor-adapter/cursor_adapter/tools.py`: the shfmt check's probe call through `run_probe`, and its stall text naming shfmt.
- `claude/.claude/scripts/cursor-adapter/cursor_adapter/check.py`: `tool_findings`, which runs the shfmt check only after python3 and bash pass their floors, reads the probe's result as Design item 8 says, and adds the `install`-and-relaunch sentence.
- `claude/.claude/scripts/select-tests.py`: `HOOK_HELPERS_RUN_BY_SCRIPTS_TESTS` (:49-51) gains `claude/.claude/hooks/shell-syntax-tree.py`, and its comment names the adapter's shfmt probe. The hooks' `.sh` files already select the scripts tests (`select-tests.py:640-641`, `:1023`), so `_lib.sh` and `_config.sh` need no row.
- `claude/.claude/scripts/tests/test_select_tests.py`, only if its path-fidelity tests need the new entry listed.
- `claude/.claude/scripts/tests/_cursor_install_helpers.py`: a shfmt stub in the test world's recorded tools.
- `claude/.claude/scripts/tests/test_cursor_adapter_install_prerequisites.py`: the worst-case budget case at :535-558 asserts that the recorded probe calls include the shfmt check's, by its program text, and number exactly four against 12 seconds. It also holds the shfmt cases of Verification 6.
- `claude/.claude/scripts/tests/test_cursor_adapter_install_roundtrip.py`
- `claude/.claude/scripts/tests/test_cursor_adapter_install_session_start.py`: the sessionStart report's shfmt findings, and the elapsed bound at :770, which reads the raised constant.
- `docs/cursor-adapter.md`: the tools bullet at :117, and in § "Limitations" the timeout line at :306 says 12 s. That bullet gains a sub-bullet: the report also runs the shfmt check, from `~/.cursor/` rather than the workspace, so a version manager that picks shfmt by directory can pass it and give a hook another build. The shadowing sentence at :114-117 extends to shfmt's directory, and says a user-writable one, such as `go install`'s, is a trust decision.
- Reuse: `run_probe`, `find_tool`, `stall_text`'s wording pattern, `record_environment`, and Dispatch 3's `_lib_shfmt_dependency_cause`.

**Dispatch 5 — the renamed dependency check, and PR 1's docs and records.**
- The dispatch's first commit holds two `git mv`s and no other edit, so review and `git log --follow` see the renames:
  - `claude/.claude/hooks/check-python-floor.sh` to `claude/.claude/hooks/check-hook-dependencies.sh`.
  - `claude/.claude/hooks/tests/test_check_python_floor.py` to `claude/.claude/hooks/tests/test_check_hook_dependencies.py`.
- `claude/.claude/hooks/check-hook-dependencies.sh`: the call to `_lib_shfmt_dependency_cause`, the shfmt notice, the cap-tool line and the header changes (Design item 11).
- `claude/.claude/hooks/tests/test_check_hook_dependencies.py`:
  - `HOOK`, `REGISTERED_COMMAND` and the module docstring name the new file and both checks.
  - The module-scoped PATH mirrors also drop shfmt, as the no-timeout mirror drops `timeout` at :84-87, so each case places shfmt itself.
  - The python3 cases that are silent after a passing probe now reach the shfmt check with shfmt off PATH. They are `TestAtOrAboveTheFloor` (:176) with its case at :181, the case at :271, and the case at :321. Each asserts that the one notice is the shfmt-missing one and holds no python3 condition, and each case and the class are renamed for that outcome.
  - The real-interpreter case at :190 links real shfmt behind `require_shfmt()` and stays silent.
  - One below-floor python3 case and one no-python3 case place a stub shfmt and assert its call log stays empty.
  - Every case whose check reaches the module links real python3 with `rig.link_real_python3()`, as :190 does, because the rig's stub python3 (:110-111) cannot run the module.
  - The SessionStart cases of Verification 6, written with Dispatch 1's stub-shfmt writer.
- `claude/.claude/hooks/tests/test_shfmt_floor.py`: the README `shfmt` bullet's floor case, which lands with the bullet.
- `claude/.claude/settings.json:216`: the registration's command path. Its group, matcher and timeout stay.
- `claude/.claude/scripts/cursor-adapter/parity-exceptions.json:18`: the `declined` entry re-keyed to `SessionStart|startup|resume|check-hook-dependencies.sh`, and its detail extended to the shared shfmt check (row 93).
- `claude/.claude/hooks/tests/test_cursor_adapter_gate_matrix.py:1374`: the declined set names `check-hook-dependencies.sh`.
- `claude/.claude/scripts/cursor-adapter/cursor_adapter/core.py`: the comment at :21 names `check-hook-dependencies.sh`. Dispatch 4 already rewrote :23.
- `claude/.claude/hooks/_config.sh:70`: the python3 floor comment names `check-hook-dependencies.sh`.
- `claude/.claude/hooks/tests/test_bash_floor.py:406`: the docstring names the renamed hook and test file.
- `claude/.claude/hooks/tests/test_hook_alignment.py`, only if its registration or header checks need the renamed hook listed.
- Header Known-gaps only: `claude/.claude/hooks/deny-escaped-backticks-in-pr-body.sh`, `claude/.claude/hooks/deny-pii-in-commits.sh` and `claude/.claude/hooks/deny-private-project-refs.sh` each gain the zsh and placeholder-decoy lines, citing the decision file this dispatch creates (Design item 10).
- `README.md`:
  - :116 names `check-hook-dependencies.sh`.
  - The `timeout` bullet at :115 gains the cap-tool sentence (Design item 9).
  - The line at :134.
  - A `shfmt` bullet in § "Requirements", which says the same hook warns at session start and gives the zsh note (Design item 9).
- `docs/hooks.md`:
  - § "Utility hooks": the bullet at :204 is renamed `check-hook-dependencies.sh` and covers both checks. It gives the order, what the probe cannot catch, and that the silent cases and hazards listed in § "Python version" apply to both checks. It cites § "Python version" for python3 and the recovery entry for shfmt. Its registration switch now silences both checks.
  - § "Python version": the hook's name at :523 and :528.
  - § "Python version": the hazard bullets at :538-539 settle their working-directory and pre-trust premises from row 101's vendor lines, cited to the pages. Interactive sessions hold settings hooks until the trust dialog is accepted. `claude -p`, the SDK and a trusted parent folder run them in a clone the user never reviewed. The hazards apply to the shfmt version call and probe as well as to python3, and the bullets name what stays unconfirmed (row 101). They also say a repository or one agent `Write` can set a pin file that makes a shfmt shim fail, citing `docs/security-hardening.md:346-351`.
  - § "Python version": the sentence at :551, which says each hook running python3 through `_lib_command_words` states its python3 failure in its header, a statement Dispatch 2's header edits make false (row 84). It now says a hook that parses through `_lib_shell_parse` denies on any parse failure with a reason naming the cause, cites § "Gate deadlock recovery", and keeps the header duty for each other stowed hook that runs python3 directly. It names no gate, so PR 2 leaves it alone.
  - § "Gate deadlock recovery": replace the :592 paragraph with PR 1's part of the recovery entry (Design item 9).
- `docs/cursor-adapter.md` § "Limitations": the report bullet at :302-303 names `check-hook-dependencies` for both mentions, and its lead covers python3 and shfmt.
- `docs/memory-audit-nudge.md`: the flag-order bullet at :137-142 cites the deleted splitter's docstring. State that the parser finds `--body-file` in any position.
- `CHANGELOG.md`: an `[Unreleased]` entry with migration notes and the further lines Design item 9 lists. It says `check-python-floor.sh` is now `check-hook-dependencies.sh` and also checks shfmt.
- Create `docs/design-decisions/tokenizing-gates-parse-with-shfmt.md`.
- `docs/design-decisions/command-text-gates-accept-quoted-text-over-deny.md`
- Reuse: the hook's own `.source` filter, `_lib_jq` notice and exit-0 shape, the moved test file's rig, payload and registration helpers, Dispatch 1's `require_shfmt()` and stub-shfmt writer, Dispatch 3's `_lib_shfmt_dependency_cause`, and `TestNoRepositoryChosenTextReachesTheNotice` (`test_check_python_floor.py:336-356`) as the hostile-fixture pattern.

### PR 2 — the worktree gate and the evaluator

PR 2 starts once PR 1 merges, on a new branch from the default tip. Dispatches 6 and 7 run in sequence. One session step sits between them: put every row of Dispatch 6's table that changes a gate verdict, deny-to-allow and allow-to-deny alike, to the engineer. Dispatch 7 edits the moved cases' expectations only after the engineer answers (Verification 3).

**Dispatch 6 — the `git-records` projection and the differential table.**
- `claude/.claude/hooks/shell-syntax-tree.py`: add `git-records` with Design item 2's in-group rules, the carried-over classifiers, `SHFMT_ARGV`, `MAX_COMMAND_BYTES`, `FIELD_SEP` and the pure function the evaluator calls. The module docstring states the record grammar and both meanings of in-group.
- `git mv` `claude/.claude/hooks/tests/test_parse_git_command.py` to `claude/.claude/hooks/tests/test_shell_syntax_tree_git_records.py` as the dispatch's first commit, with no other edit.
  - Its moved cases keep testing `parse-git-command.py` through this dispatch, so no expectation changes before the engineer answers.
  - New test classes in the same file call `git-records` on real shfmt behind `require_shfmt()`: the realistic smoke set, and Verification 7's git-word, wrapper, placeholder and in-group cases, a `$HOME/bin/git push` case included.
- `claude/.claude/hooks/tests/test_ask_new_dependency_disclosure.py:4`: the docstring's citation of the renamed test file.
- `claude/.claude/hooks/tests/test_shell_syntax_tree_contract.py`:
  - The child-position matrix gains its `git-records` cells. Each cell's expected in-group, for a git write and for a `cd`, comes from Design item 2's rules in the fixture table.
  - The real-bash `cd` check of Verification 7, which tests the threaded cells against bash itself rather than against the rules that wrote them.
  - `_LIB_SHFMT_ARGV` equals `SHFMT_ARGV`, and `_LIB_SHELL_PARSE_MAX_BYTES` equals `MAX_COMMAND_BYTES`, each printed by sourcing `_lib.sh`.
- Deliverable to the session: the changed-case table. A scratch script outside the repository, which is not committed, runs old `build_records` against new `git-records` over three inputs:
  - Every moved case.
  - A compound matrix: each of `{ }`, `time`, `!`, `if`, `while`, `until`, `for`, `select`, `case`, a subshell, a function body, a coprocess, a backgrounded statement, a pipe side, the right operand of `&&`, the right operand of `||`, a `;` after an `&&` list, a command substitution and backticks, each quoted and unquoted, a process substitution, an assignment value, and a redirect target. Each is crossed with a `cd`, a git write, and a `cd` then a write. The `cd` forms add `FOO=x cd`, `builtin cd`, `command cd`, `pushd` and `popd`.
  - Shapes bash and zsh read differently, each beside a git write: `=git push`, `cd old new`, an inline `#` comment, `rcquotes` quoting and a glob qualifier.
- The table has one row per input whose records change. Each row gives the old records, the new records, the reason, and the gate verdict each record stream yields under the consumer from `require-worktree-for-git-writes.sh:311` onward, in a main-tree session and in a linked-worktree session. It marks every verdict change, deny-to-allow or allow-to-deny. Each zsh-shape row also says whether the new records follow bash's reading or zsh's. PR 2's body carries it.
- Every `cd` row is allow-to-deny or unchanged. A `cd` row that turns from deny to allow contradicts row 85, so the session stops and revises this plan.
- The table covers at least these moved cases in `test_parse_git_command.py`:
  - The SENTINEL cases at :139, :142, :171 and :182.
  - The heredoc-opener tail case at :296.
  - The `git\r--version` row at :307.
  - The stray-dollar rows at :340.
  - The literal-then-newline-then-write case at :346.
  - The `GIT_DIR=x git --version` row at :380.
  - The redirect rows at :401.
  - `test_write_preceded_by_ampersand_marks_op` at :441, whose `cd` record turns in-group 1 while its verdict stays deny.
  - Not the `time` row at :411, which passes unchanged under the in-group rules (row 87).
- Reuse: `parse-git-command.py`'s segment classifiers and record grammar, verbatim (Design item 2).

**Dispatch 7 — wire the worktree gate and the evaluator.**
- `claude/.claude/hooks/tests/test_shell_syntax_tree_git_records.py`: the moved cases move onto `git-records`. Each expectation edit maps to a row of the engineer-reviewed table.
  - A case that exercises only `classify_cd_segment`, `classify_git_segment` or the record encoding calls those functions on word lists, with no shfmt, so the classifier keeps a fast pure layer that never skips.
  - The other moved cases, which exercise the walker, the in-group rules or the step from command to words, run on real shfmt behind `require_shfmt()`.
- `claude/.claude/hooks/require-worktree-for-git-writes.sh` (Design item 4), the :273 widening and the header's added Known gaps included.
- `claude/.claude/hooks/evaluate-code-writer-self-review.py` (Design item 5).
- Delete `claude/.claude/hooks/parse-git-command.py`.
- Header comment only: the `parse-git-command.py` mention at `claude/.claude/hooks/deny-repo-relocation.sh:20`.
- Tests under `claude/.claude/hooks/tests/`:
  - `test_require_worktree_for_git_writes.py`:
    - The curated-PATH helpers at :707-719, :724-752, :791-808 and :1541-1548 link shfmt in.
    - The abnormal-exit shim at :749 matches the module path in any argument position, and also covers exits 2 and 5.
    - The deny tests assert on reason text, not a bare deny.
    - The shfmt-absent escape-hatch cases join the python3-absent ones at :1566-1622.
    - The shfmt-absent allow case for a non-git command, and the gate-level in-group, `cd`, fast-path, `popd`, relocation known-gap, git-word, wrapper and placeholder cases of Verification 7.
    - One gate-level case per verdict-changing row of the engineer-reviewed table.
  - `test_send_back_skipped_self_review.py`:
    - The `Workspace` fixture (:894-909) injects a fake builder by default, so the verdict matrix never spawns shfmt. A named handful of end-to-end cases run real shfmt behind `require_shfmt()`.
    - The loader-failure cases at :1825-1858, and the `PARSE_GIT_COMMAND_PATH` constant at :36, move to the new module's path and required names.
    - The known-gap test at :268-274 splits, as Design item 5 says.
    - The `runs_git_diff` cases run on an injected builder, plus a few real-shfmt cases.
    - The prefilter, exit-1, credit-verdict, other-rule-still-fires and argv cases of Verification 7 are added.
  - `test_hook_alignment.py`: the `_SECOND_DIRNAME_SITE_HOOKS` entry at :2859-2861, which quotes the gate's `PARSER=` line.
  - `test_cursor_adapter_gate_matrix.py`, only if its worktree-gate rows fail.
  - `test_scaled_timeout_shim.py`, only if its exact-count assertions at :351-424 change.
- `docs/design-decisions/code-writer-self-review-send-back.md` § "Log verdicts": the new verdict and its reasons.
- `docs/hooks.md` § "Gate deadlock recovery": PR 2's part of the recovery entry, the rollback order included (Design item 9).
- `CHANGELOG.md`: PR 2's line (Design item 9).
- `docs/design-decisions/tokenizing-gates-parse-with-shfmt.md` and `docs/design-decisions/command-text-gates-accept-quoted-text-over-deny.md`: PR 2's widening (Design item 10).
- Reuse: `_lib_shell_parse` and `_lib_shell_parse_failure_clause` from PR 1, the stub-shfmt writer from Dispatch 1, and the `build_path_without` and `write_prewarmed_stub` helpers.

Projected diff: PR 1 about 4,800 changed lines and PR 2 about 2,750, about 7,550 in all (row 72). Per the plan-it rule, the count leaves out this plan file, which ships in PR 1. The differential tables are scratch output and add no lines.
- PR 1's largest parts:
  - The module with its moved and new tests, the unconditional backslash decoder, its real-bash comparison and the encoding cases included, about 1,600.
  - The command-word and gate tests, the new cap, invalid-shape, status-4, pipe-status, tree-then-nonzero-exit, per-stage stderr, tail-table, unlisted-status, python3-first and zsh cases included, about 900.
  - The shared shfmt check with its cap arguments, probe coverage and tests, the renamed hook with its cap-tool line and its moved and extended tests, the rename's citations and the `_config.sh` floor, about 810.
  - The Cursor port: the adapter's shfmt check with its caps, python3 and bash conditions and probe seam, the raised entry timeout, the `select-tests.py` entry, their tests and the doc lines, about 410.
  - The rest is install, CI, header and doc text, the zsh, cap-tool and Known-gaps lines and the `docs/hooks.md:551` rewrite included, about 1,080.
- The estimate counts each rename by its changed lines. If the hook's edits leave it below git's default 50% rename similarity, the diff shows a delete and an add, about 100 lines more.
- PR 2's largest parts are deleting `parse-git-command.py` (356 lines), the `git-records` projection with its moved tests, `cd` matrix cells and real-bash `cd` check (about 950), and the gate and evaluator tests, the relocation and `popd` cases included (about 910).
- Neither PR is under 400 changed lines. The engineer chose two PRs by tokenizer (row 46), not a split below 400 (row 72).

## Verification

1. Dispatch 1 builds the `words` differential table from a run of the base commit's `_lib_command_words` against `shfmt` piped into the new `words` projection (row 108).
   - Its inputs, one group per item:
     - Every moved splitter case.
     - Every command string `_lib_command_words` receives while the three gates' suites and `test_lib_command_words.py` run on the base commit. A logging line added only in the scratch worktree captures them, so the corpus holds the commands the tests build at run time, not literals scraped from source.
     - `gh pr create --body "$(grep -F foo notes.txt)"`, and a `git commit -m` whose quoted `$(...)` holds `-F`.
     - A `gh pr create` and a `git commit`, each taking an unquoted heredoc whose body holds backticks around a command with a source flag.
     - Shapes bash and zsh read differently, each holding a source flag: an inline `#` comment such as `git commit -m x # -F /dirty.md`, an `=cmd` word, `rcquotes` quoting such as `'it''s'`, and a glob qualifier.
   - The old column runs under GNU `xargs`, which CI and Linux consumers run, and under BSD `xargs`. The table names both builds and marks every row whose old status or old extraction differs between them. When one build is not reachable, the table says so, and PR 1's body names the build the old column lacks.
   - The table has one row per input whose status or extracted path strings differ. Each row gives the old and new words and status, the source paths each gate's extraction returns from each stream, and the verdict each yields with every extracted path a missing file, so any path denies.
   - It marks every verdict change, deny-to-allow and allow-to-deny, and every row whose path strings differ while the modeled verdict does not. Each zsh-shape row also says whether the new words follow bash's reading or zsh's.
   - After Dispatch 1, before any existing expectation changes, the session puts every marked row to the engineer. Dispatch 2 changes an existing expectation only after the answer, each change mapping to a row, and PR 1's body carries the table and the answer.
   - Before PR 1 merges, the session re-runs the table on PR 1's head and records the date and head commit in PR 1's body. A newly marked row goes to the engineer the same way.
   - A row the engineer rejects stops the session, which revises this plan and re-runs `/plan-review`.
2. Dispatch 1 runs the shape dump before writing projection code. PR 1's body records which row-26, row-86 and row-113 items held and what changed where one did not.
3. Dispatch 6 builds the changed-case table from a differential run of old `build_records` against new `git-records`, over the moved cases, the compound matrix of every `cd` shape and container, and the zsh-differing shapes (Dispatch 6). Each row gives both verdicts, in a main-tree and a linked-worktree session, and each zsh-shape row says whether the new records follow bash's reading or zsh's.
   - Every `cd` row is allow-to-deny or unchanged. A `cd` row that turns from deny to allow stops the session, which revises this plan and re-runs `/plan-review`.
   - After Dispatch 6, before any moved expectation changes, the session puts every verdict-changing row, deny-to-allow and allow-to-deny alike, to the engineer.
   - Dispatch 7 edits the moved expectations only after the answer, each edit mapping to a row. PR 2's body carries the table and the engineer's answer.
4. After each dispatch, run `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py`. After Dispatches 2, 3 and 7, also run `test_scaled_timeout_shim.py` by name. PR 1's diff touches `install.sh` and `.github/workflows/`, so `select-tests.py` may widen to the full suite on its own, and that run is then the documented one.
5. In each PR, lint with `scripts/venv-run.sh ruff check claude/.claude/ claude-skills/ plugins/ evals/` and `scripts/list-shell-files.sh | xargs -0 scripts/venv-run.sh shellcheck`.
6. PR 1's suites must contain these cases, and they must pass.
   - **Module, with real shfmt behind `require_shfmt()`:**
     - Each of the nine residual shapes projects to the words bash sees.
     - Each attached form keeps its prefix and yields a path holding the placeholder, which its extractor hands to the caller's deny. The forms are `--body-file=`, `--template=`, `-F=`, `-T=`, `--file=`, `--input=`, and `-f`, `-F`, `--field` and `--raw-field` with `key=@`. Each is crossed with a parameter, a command substitution, an arithmetic expansion, `$'...'`, and double quotes holding an expansion.
     - Every `KNOWN_NODE_TYPES` entry has a conformance case that exits 0 and passes the strict check. The completeness test fails on an entry with no case, and on a corpus `Type` missing from the set.
     - Each `BASH_REJECTED_NODE_TYPES` entry has a sample that real shfmt rejects with exit 1 under `-ln bash`.
     - For each type that can hold a command, `gh pr create --body-file /y` in each child position surfaces in `words`. Every `KNOWN_NODE_TYPES` entry is in the matrix or in the named set of types that hold no command.
     - The realistic smoke set exits 0 through `words`: `gh pr create --body "$(cat <<'EOF' ... EOF)"`, a heredoc commit message, an `&&` chain, a `for` loop and a `[[ ]]` guard.
     - An empty command, and a comment-only command that mentions `git`, each exit 0 and pass the strict check.
     - Each backslash form yields the word bash sees, one case per form:
       - An unquoted `\-F /y` yields `-F` and `/y`.
       - An unquoted `\a` yields `a`.
       - Inside double quotes, `"b\"c"` yields `b"c`.
       - Inside double quotes, `"\$x"` yields `$x`.
       - Inside double quotes, `"\a"` keeps its backslash.
     - Over a generated set of literal-only words, the module's words equal what real bash prints for the same text through `printf '%s\0'`. The set places backslashes unquoted, inside double quotes and in mixed words, and covers `\\`, a backslash-newline, an escaped backtick inside double quotes and a backslash before a multibyte character. Its text holds no `$`, backtick, glob character or brace that a backslash does not escape, and no leading `~`, so bash expands nothing.
     - Under `LC_ALL=C`, a word holding a multibyte UTF-8 character projects to the same bytes as under a UTF-8 locale.
     - A word holding the byte 0xFF projects as row 113 settled, the byte itself or U+FFFD, pinned either way.
     - Under `production_shfmt_argv()`, a working directory holding an `.editorconfig` that sets another dialect yields an identical tree.
   - **Module, with no shfmt:**
     - A hand-built tree exits 5 for each of these:
       - An unknown type.
       - A `BASH_REJECTED_NODE_TYPES` type.
       - An unknown operator.
       - An unknown key.
       - A missing always-present key.
       - A renamed `Args`.
       - A renamed `Background`.
       - A renamed `Dollar` on `SglQuoted`.
       - A renamed `Dollar` on `DblQuoted`.
       - A conservation mismatch.
     - A deeply nested tree exits 2, not 1.
     - Garbage, empty and truncated JSON on stdin each exit 2.
     - Exits 5 and 2 print nothing on stdout.
     - The interpreter-isolation and capability-pin tests pass.
   - **Redaction gates and `_lib_command_words`:**
     - Through `_lib_command_words`, the late path in the residual shapes prints.
     - A stub shfmt's exit maps as Design item 1 says:
       - Exit 1 yields status 3.
       - Exits 2, 126 and 127 get the shfmt-fault wording, with no "could not be tokenized" and no file workaround.
       - Exits 124, 137 and 143 pass through unchanged.
     - A stub shfmt that prints a valid tree for a clean command and then exits 1, 2, 126, 124 or 137, behind real python3, returns 3, 8, 8, 124 or 137, never 0. One case per redaction gate denies for the exit-2 stub.
     - A stub shfmt that prints a full valid tree and then exits 139 returns 8 through `_lib_command_words`, with empty stdout.
     - The pipe statuses map as Design item 1 says. These cases run under `set -uo pipefail`, as the gates do:
       - A stub shfmt exiting 1 beside a stub python3 exiting 2 yields 3, so shfmt's nonzero status wins.
       - A stub python3 that exits 2 without reading stdin, behind a stub shfmt that writes a tree larger than a pipe buffer, yields 2, not 8. The tree's size, not start order, decides the outcome.
       - The same stub python3 behind real shfmt, on a command whose tree is larger than a pipe buffer, yields 2, which confirms row 59's SIGPIPE item.
       - A stub shfmt that kills itself with SIGPIPE, behind real python3 exiting 0, yields 8.
       - One gate-level case runs the SIGPIPE-exception outcome.
     - No case places a python3 stub that exits without reading stdin behind a shfmt that can still write, outside the SIGPIPE cases above.
     - A stub python3 exiting 1, 126 or 139 behind a printing shfmt stub passes that status through, with the default clause and the tool-fault sentence.
     - The status constants are pairwise distinct, 9 and 10 included.
     - The stub's logged argv equals `_LIB_SHFMT_ARGV`.
     - One table keyed by status gives each deny reason's tail, asserting the named tail present and the other absent:
       - The file workaround: 3 and 7.
       - Neither tail: 4.
       - The tool-fault sentence: the cap kills, 2, 5, 6, 8, 9, 127 and the unlisted 1, 126 and 139.
       - The tool-fault sentence for the not-linked case at any status.
     - No clause holds the tool-fault sentence, the word "gate" or a citation.
     - The clauses for 2 and 127 and the default clause name awk.
     - Each tool-fault sentence cites a heading that exists in `docs/hooks.md`.
     - With real shfmt, an unbalanced quote, an unclosed `$(`, an unclosed backtick, and an unterminated heredoc if Dispatch 1's dump shows shfmt rejects it, each return status 3 through `_lib_command_words`. Each deny reason carries the invalid-bash clause and the file workaround.
     - With real shfmt, a comment-only command returns status 4 with its own wording and no workaround.
     - With real shfmt, the zsh-only `echo ${(f)x}` returns status 3 through `_lib_command_words`, pinning row 106's residual.
     - With both python3 and shfmt off PATH, `_lib_shell_parse` returns 127, and each gate's deny names python3.
     - Marked `timing`, a hung shfmt stub and a hung python3 behind a printing shfmt stub each return a cap-kill status with empty stdout, and `assert_cap_engaged` with a production cap of 5 shows the default cap acted on that command.
     - A stub shfmt that prints a tree with an unknown type makes each of the three gates deny with the shape wording.
     - With shfmt off PATH:
       - Each of the three gates denies a command it parses, with the stop-and-ask wording that cites the recovery entry and carries no file workaround.
       - Each gate allows a command it does not parse, such as `gh pr view` or `ls`.
       - `deny-private-project-refs.sh` allows a `git commit` with an empty staged diff, and `deny-pii-in-commits.sh` denies it (row 20).
     - A parse-failure deny reason holds none of the command's text and none of shfmt's stderr.
     - A marker written to stderr by a stub shfmt, by a stub python3, and by a module that crashes appears in neither the stdout nor the stderr of `_lib_command_words`, nor of one gate's run.
     - The three gates' silent-python3 cases use a stub shfmt whose tree holds no command, behind real python3, and deny with the status-4 wording.
     - The size cap, under an explicit UTF-8 locale:
       - One word of 32,768 two-byte characters (65,536 bytes) reaches shfmt.
       - One word of 32,769 denies with the size wording.
       - The oversize deny leaves a stub shfmt's call log empty.
       - The oversize check runs before the missing-shfmt check.
       - One boundary case enters through a gate's JSON payload.
     - The python3-absent cases now deny single-line commands too, without the file workaround.
   - **Shared shfmt check, `test_lib_shfmt_dependency_cause.py`:**
     - Behind `require_shfmt()`, with real python3, the probe passes, and `_lib_shfmt_dependency_cause` prints nothing and returns 0.
     - The probe command the check sends, captured from a stub shfmt's stdin log and parsed with real shfmt under `production_shfmt_argv()`, holds every type the contract test's child-position matrix lists as holding a command, and every `KNOWN_BINARY_OPERATORS` entry. A trimmed probe fails it, and so does a type added to the matrix that the probe lacks.
     - Each probe status class yields a cause line equal to the text `_lib_shell_parse_failure_clause` prints for its status, holding none of the other statuses' texts:
       - shfmt off PATH, 6.
       - A stub exiting 1, which the probe reads as 8.
       - Stubs exiting 2 and 126, 8.
       - A stub printing an unknown-type tree, with real python3, 5.
       - A stub printing a valid tree whose words differ, with real python3, 9.
     - A below-floor version line yields one line, the below-floor one naming the found version and the floor, even when the probe also fails.
     - A stub that prints no version and passes the probe yields nothing, and its call log holds both the parse call and the version call.
     - Marked `timing`, a stub that hangs on the parse returns a cap-kill status with the cap-kill clause, and its call log holds no version call. A stub that answers the parse and hangs on `--version` reads as no version under the version cap, so the check yields nothing.
     - Marked `timing`, `assert_cap_engaged` shows each of those calls was capped at the cap passed as its argument, with the 5 and 2 the SessionStart hook passes.
     - A marker in a below-floor version line, in a failing stub's stderr, and in a mismatch tree's words reaches no cause line.
   - **SessionStart check, `test_check_hook_dependencies.py`, one case per branch:**
     - With real python3 and real shfmt at or above their floors, the hook prints nothing.
     - Every moved python3 case passes under the new file name. The silent-after-a-passing-probe cases are renamed and assert the shfmt-missing notice instead, as Dispatch 5 says.
     - A below-floor python3, and no python3, each print the python3 notice alone, and a stub shfmt's call log stays empty.
     - A python3 at the floor with shfmt off PATH prints the shfmt-missing notice, which holds no python3 condition.
     - A below-floor shfmt, and an unknown-type tree with real python3, each print one notice on screen and to the agent and exit 0. Each carries the cause line the shared check prints for that state, taken by sourcing `_lib.sh`.
     - In each silent case, a stub shfmt's call log holds the parse call.
     - No notice names a gate hook or a command such as `git commit` or `gh pr`, and neither text holds a path or any of shfmt's output.
     - The agent text carries the cause line and no remedy sentence from the screen text.
     - The stub shfmt's logged working directory equals the hook's start directory, for the parse call and the version call.
     - Marked `timing`, a stub shfmt that hangs on the parse yields the cap-kill notice, and `assert_cap_engaged` shows the cap acted on shfmt.
     - The cap-tool line, one case per branch:
       - With neither `timeout` nor `gtimeout` on PATH and both checks passing, the notice carries the cap-tool line alone, on screen and to the agent.
       - With neither on PATH and shfmt off PATH, the notice carries the shfmt-missing cause line, then the cap-tool line.
       - With `timeout` or `gtimeout` on PATH, no notice carries the cap-tool line.
     - The notice's citation of `docs/hooks.md` § "Gate deadlock recovery" names a heading `heading_texts` finds.
     - A non-SessionStart payload, and a `compact` or `clear` source, print nothing.
     - The registration names `check-hook-dependencies.sh`, its matcher equals the script's `.source` filter, and the gate-matrix declined set and the parity key name the renamed hook.
     - `git grep -n check-python-floor` matches only this plan file, the new CHANGELOG entry's rename note and the dated records Out of scope names.
   - **Install and CI:**
     - `install.sh`'s fixture covers the allow path at or above the floor, a missing shfmt, and a version below the floor.
     - `_shfmt_floor_status`, sourced from `_config.sh`, reads the spellings `v3.14.1`, a pseudo-version, `3.100.0` and `3.13.9`.
     - An unreadable version prints the notice and does not exit 1.
     - Each failure names the resolved path, the restart step and `README.md` § "Requirements".
     - A whole-script run with a below-floor shfmt stub exits 1 and leaves the temporary `$HOME` empty.
     - The README's `shfmt` bullet states the floor `_config.sh` holds, checked in `test_shfmt_floor.py` from Dispatch 5 on.
     - The CI pin equals the floor, and under `GITHUB_ACTIONS` the runner's shfmt reports the pin.
     - The step body, with only `curl`, `sudo` and `install` stubbed and the real `sha256sum`:
       - never reaches `install` on a digest mismatch or a failed fetch;
       - reaches `install` after the check on a match;
       - names a missing key;
       - fetches a URL holding the fixture version, which differs from the pin.
   - **Cursor:**
     - The adapter's `install` requires and records shfmt, as the last recorded tool.
     - `check` and the sessionStart entry each report a shfmt missing from the hooks' PATH.
     - They report a below-floor shfmt, and a probe failure for one stubbed status per class, with the cause line `_lib_shfmt_dependency_cause` prints for it and the `install`-and-relaunch sentence.
     - The shfmt finding's citation names a heading `heading_texts` finds in `docs/hooks.md`.
     - A passing shfmt adds no finding.
     - A python3 below its floor or missing, and a bash below its floor, each add their own finding and no shfmt finding, and a stub shfmt's call log stays empty.
     - The probe's seam, one case each, asserted on the finding text:
       - A hooks `_lib.sh` that fails to source yields the fixed finding naming the shfmt check and its status.
       - A nonzero exit with no output yields the same fixed finding.
       - A zero exit with a printed line yields a finding with that line.
       - A hooks `_lib.sh` that prints a line when sourced still yields the cause line as the finding.
       - A hooks directory path holding a `'` and a `$(` still yields the cause line.
     - With `PROBE_BOUND_SECONDS` raised in the test, so the caps computed from it scale and the margin does not rest on 1 second:
       - A stub shfmt that hangs on the parse and honors SIGTERM yields the cap-kill finding inside the bound, not the stall finding.
       - A stub shfmt that hangs and ignores SIGTERM stalls past the bound and reports a finding that names shfmt.
     - The worst-case budget case asserts that the recorded probe calls include the shfmt check's, by its program text, and number exactly four, then fits `CHECK_ENTRY_TIMEOUT_SECONDS` of 12.
7. PR 2's suites must contain these cases, and they must pass.
   - **Module, with real shfmt behind `require_shfmt()`:**
     - For each type that can hold a command, a `git commit` and a `cd` in each child position each yield a record whose in-group follows Design item 2's rules for its kind.
     - The realistic smoke set exits 0 through `git-records`.
     - Each git-word spelling yields a GIT record with subcommand `push`: `$HOME/bin/git push`, as the shlex token did (row 27), `\git push`, `g\it push`, `gi""t push`, `"git" push`, `'git' push`, `"$HOME"/bin/git push` and `$(brew --prefix)/bin/git push`.
     - Each wrapper keeps a GIT record: `command git push`, `env X=1 git push` and `xargs git push`.
     - No placeholder emits `FIELD_SEP` or a newline inside a record: `git -C "$X" push`, `git -C /a"$X" push`, `cd /a"$X" && git push`, `git "$X" push` and `git $X`.
     - In-group:
       - A git command inside `{ }`, `time`, `!`, a pipe side, and a conditional or loop body keeps in-group 0.
       - A top-level `cd`, and the leftmost `cd` of a top-level `&&` or `||` list, keep in-group 0.
       - In `[ -d /wt ] && cd /wt && git push; git commit -m x`, the `cd` keeps in-group 0 for the push, and an in-group-1 CD record precedes the commit.
       - Each of these emits an in-group-1 CD record, one case each:
         - List operators: a `cd` right of `||`.
         - Pipes and background: a `cd` on a pipe side, backgrounded, or nested in a backgrounded `{ }`.
         - Grouping: a `cd` inside `{ }`, `time` or `!`.
         - Conditionals and loops: a `cd` in the condition or body of each conditional and loop construct.
         - Wrapper forms: `FOO=x cd`, `builtin cd`, `command cd`, `pushd` and `popd`.
       - A loop whose body ends with a `cd` emits an in-group-1 CD record before its first git record.
     - Against real bash, the threaded cells hold. Wherever the projection emits an in-group-0 CD record for a child-position matrix cell, or for one of three depth-2 nestings (an `&&` list inside `{ }`, a `cd` in an `if` condition inside a function body, and a `cd` list inside a subshell inside `{ }`), the test runs that cell in bash:
       - The `cd` targets a temporary directory, and `pwd` stands in for the git write.
       - It runs each outcome the cell can take: a condition or left operand true and false, a `case` that matches and one that does not, and a loop of zero and one iterations.
       - Each `pwd` that stands in for a write the records resolve to the `cd`'s target must, in every run where it runs, print the temporary directory.
       - The runs execute only `cd`, `pwd`, `true` and `false`, with stdin closed and under a short timeout.
   - **Worktree gate:**
     - A stub shfmt that prints a tree with an unknown type makes the gate deny with the shape wording.
     - With shfmt off PATH, the gate denies a git command with the stop-and-ask wording that cites the recovery entry, and allows a non-git command.
     - With shfmt off a curated PATH:
       - The gate's opt-out file allows.
       - A held self-lock allows a plain write through the fast path.
       - A foreign lock still denies, with its misleading reason pinned as a known gap, as the python3 cases at `test_require_worktree_for_git_writes.py:1566-1622` do.
       - With both python3 and shfmt absent, the deny names python3.
     - The changed worktree-parser cases match the engineer-reviewed table, and every other moved case passes unchanged, the `time` row at :411 included.
     - An unbalanced quote and an unterminated heredoc each deny with the status-3 wording.
     - `cd /w | cat; git reset --hard` denies in a main-tree session.
     - For a command that reaches the parser, a write inside `for`, `if`, `{ }` or `time` is judged at the running cwd. It allows after `cd <worktree> &&` and denies in the main tree.
     - `cd <worktree> && git push` allows in a main-tree session.
     - In a main-tree session these deny, with `<worktree>` a real linked worktree:
       - `{ cd <worktree>; } & echo x; git push`, `{ cd <worktree>; } | cat; git push` and `time cd <worktree> | cat; git push`.
       - `{ cd <worktree> && git push; }` and `time cd <worktree> && git push`.
       - `[ -d <worktree> ] && cd <worktree>; git push`.
       - `cd <worktree> && for i in 1 2; do git commit -qm x; cd ..; done`.
     - One case per `cd`-bearing class denies a write after the construct: a `cd` in a conditional condition, a conditional body, a loop condition, a loop body, a `case` item, a function body and a pipe side.
     - In a linked-worktree session holding its own lock, these deny: `if [ -d x ]; then cd x; fi; git commit -m y`, `pushd <main> && git push` and `popd && git push` through the widened fast path, and `builtin cd <main> && git push`.
     - In a linked-worktree session holding its own lock, `c\d <main> && git push` allows, pinned as the header's relocation known gap.
     - In a main-tree session, the git-word spellings the prefilter admits, and the wrappers above, deny as writes. The placeholder cases deny through the UNRESOLVED status, the empty `cd` target or the placeholder subcommand.
     - `g\it push` and `gi""t push` allow in a main-tree session, pinned as the header's known gap (row 105).
     - An over-cap command denies with the size wording.
     - The stub's logged argv equals `SHFMT_ARGV`.
   - **Evaluator:**
     - The `Workspace` fixture's default builder spawns nothing. A real-shfmt end-to-end case on the `clean` path logs no `reread-credited-unparsed` line.
     - A command without both `git` and `diff` leaves a stub shfmt's call log empty.
     - A stub shfmt that exits 1 gives no credit and no `reread-credited-unparsed` line.
     - Each failure earns R5 credit and logs its reason before the verdict line:
       - shfmt off PATH logs `shfmt-missing`.
       - A non-executable stub logs `shfmt-start-failed`.
       - Stubs exiting 2 and 126 log `shfmt-exit-2` and `shfmt-exit-126`.
       - A stub printing an unknown-type tree logs `tree-unrecognized`.
       - A stub printing truncated JSON, and one printing a deeply nested tree, each log `parse-fault`.
       - A command over `MAX_COMMAND_BYTES` logs `oversize`.
     - With shfmt off PATH, and with a stub printing an unknown-type tree, a transcript that also breaks another rule still gets that rule's send-back, with the credit line logged before it.
     - `# check git diff later` earns no R5 credit.
     - `echo git diff` keeps R5 credit, under a renamed known-gap test.
     - The stub's logged argv equals `SHFMT_ARGV`.
8. Locally, time each of these end to end:
   - A 64 KiB command of two-byte words, through `_lib_command_words` in PR 1 and through the worktree gate in PR 2.
   - A multi-KB heredoc commit message, through the same paths.
   - In PR 1, one `git commit` with staged changes through both commit gates.
   - In PR 1, the SessionStart check, and the Cursor adapter's sessionStart entry.
   - In PR 1, the SessionStart check with a stub shfmt that hangs on the parse and ignores SIGTERM, against the 10-second registration timeout.

   Report each in that PR's body as a one-machine measurement beside the 100 ms per-fire budget in `plugins/claude-hook-review/skills/claude-hook-review/SKILL.md` § "7. Performance budget". They are not committed tests. The plan claims no time bound from the byte cap.

   In PR 1, also measure one nested-input case's peak memory, as a scratch measurement, not a committed test (rows 115, 117).
   - Input: row 66's shape, 1,200 nested `{ }` groups around `true`, 6,004 bytes. Write it into a `mktemp -d` directory with `python3 -c "import sys; sys.stdout.write('{ ' * 1200 + 'true' + '; }' * 1200)"` redirected to a file.
   - Commands: run each stage on its own, so each figure belongs to one process, under `/usr/bin/time -l` on macOS or `/usr/bin/time -v` on Linux.
     - `shfmt -ln bash --to-json`, the argv `_LIB_SHFMT_ARGV` holds, reads the input file and writes its JSON to a second scratch file.
     - `python3 -I -S claude/.claude/hooks/shell-syntax-tree.py words` reads that JSON on stdin.
     - Each run's maximum resident set size line gives that stage's peak. Take the line's unit, bytes or kilobytes, from that machine's `man 1 time`.
   - PR 1's body states the input's and the JSON's byte counts, each stage's peak resident memory, wall time and exit status, and the machine's OS, as a one-machine measurement. It also states whether either peak passed the threshold below.
   - Threshold: a peak over 512 MiB in either stage contradicts row 115. The session then stops, as Critical files describes, and asks the engineer whether to bound shfmt's output in bytes.
     - The figure is the session's proposal, because no vendor or repo figure bounds a hook's memory.
     - The session's rationale: row 66 has this case finishing in about 2.1 s, under half the 5 s parse cap, so a deeper command inside the byte cap can run more than twice as long before the cap ends it. If memory grows with run time as the JSON does, a 512 MiB peak here puts that command past 1 GiB, which the session judges large for one hook process on a stow consumer's machine.
9. Before PR 1, look up `mvdan.cc/sh/v3` in a CVE database such as OSV. Record the dependency rationale in PR 1's description, per `claude/.claude/CLAUDE.md` § "Engineering Judgment" ("New third-party dependencies"): vulnerability history, maintenance health, pinning strategy, and why shfmt over the alternatives.
10. Run the branch's own hook scripts by path, not the stowed ones, because a session runs the hooks its `~/.claude/hooks` link resolves to, and that checkout changes only on `git pull` (row 48). Each run feeds a PreToolUse or SessionStart JSON payload on stdin, once with real shfmt on PATH and once with shfmt off it. Record the outcomes in that PR's body.
    - PR 1: each redaction gate with a `git commit -F <file>` and a `gh pr create --body-file <file>` payload, and `check-hook-dependencies.sh` with a `startup` payload.
    - PR 2: the worktree gate with a `git -C <worktree> status` payload, whose `-C` sends it past the fast path to the parser (`require-worktree-for-git-writes.sh:274`), and with a main-tree `git commit` payload.
11. Once per PR, in a scratch worktree, rehearse the recovery entry and record each outcome in that PR's body.
    - PR 1: run each diagnostic the entry gives against the broken state it names: shfmt off PATH, a stub that exits 2, a stub that prints an unknown-type tree, a stub that hangs, python3 off PATH, and an unlinked module.
    - PR 2: the same for the worktree gate, plus a revert of PR 1's merge alone on a copy of the PR 2 tree, recording the gate's deny, which shows why the rollback order reverts PR 2 first.

## Out of scope

- **Avoiding the pull-before-install lockout.** A rollout staged to avoid the lockout is within the plan's reach, and the plan declines one. The engineer wrote "I'd say accept the lockout because consumers know they may need to run ./install.sh after a git pull, and CHANGELOG should tell them, yes? The alternative is a ton of extra instrumentation which jI don't think is a good idea." (row 6). Considered and declined:
  - A rollout that keeps either old tokenizer behind a missing-shfmt fallback until a later PR removes it. Each of this plan's two PRs retires its tokenizer with no fallback.
  - Keeping the `xargs -n1` fast path in the first release.
- **The other sixteen Bash gates, as an intended follow-up.** They include `_lib_commit_fragment_has_worktree_target`'s `xargs -n1` tokenizer and the gates built on `_lib_strip_shell_quotes`. Row 1 scopes this plan to the four tokenizing hooks. The engineer wrote "we may even consider moving more hooks to it because understanding quoted commands may not be necessary to be honest, or maybe the shell parser can extract the quote and can parse what's in the quote?" and later "great let's keep the other hooks in mind for a follow-up". The follow-up's own plan answers three questions:
  - Which wrapper commands, such as `bash -c` or `eval`, a gate re-parses the quoted argument of.
  - Whether the inner command of `bash -c "$cmd"`, opaque to any parser, should still deny.
  - Whether a cooperative agent emits nested shell commands at all, which transcripts can answer.
- **The plugin `_lib.sh` copies under `plugins/*/hooks/`.** None of them tokenizes a command.
- **Scoping flag reads to the `gh` or `git` simple command itself.** That would end the `ssh -T` and `tar -T` over-deny, but it changes the gates' behavior beyond swapping the tokenizer. The full descent changes verdicts too, so Verification 1's table puts each such change to the engineer instead (row 108), and a scoping change can follow from what that table shows.
- **Patching `parse-git-command.py`'s two gaps and deferring PR 2.** A newline split and a heredoc-tail fix could close row 17's misses inside shlex. "Alternatives weighed" sets aside patching the shlex tokenizers as the wrong foundation, the engineer chose two PRs by tokenizer (row 46), and PR 2 does not wait for field time (row 107).
- **The flag-order rule in memory-store-audit Step 4.** The rule loses its reason once the parser lands. Removing it is a skill change with its own review.
- **A per-call shfmt version check.** A gate's parse never reads shfmt's version. `install.sh` and the SessionStart check (Design item 11) compare it with the floor, and the strict check holds every build to the tree shape on every parse.
- **Dependency commentary in hooks this plan does not otherwise edit.** Rows 77 and 84 apply to the four gates this plan edits. Other hooks' headers that describe their own python3 failures stay as they are until a follow-up applies row 77 repo-wide.
- **An on-screen notice from the evaluator for a parse fault that starts mid-session.** The evaluator logs the cause and credits R5. The engineer wrote "SessionStart notice is the early warning." (row 91).
- **A decoy file named the placeholder.** A file whose name equals the fixed placeholder, holding clean content, would be scanned in place of a variable's real target, such as `--body-file "$F"`. A literal `$F` path has the same exposure today, and only a steered agent creates such a file. The three redaction gates' tier lines omit `untrusted-input`, so their tiers waive it. Each of their headers' Known gaps records it (Design item 10), as `docs/hooks.md:43` requires of a waived finding.
- **A scheduled job that tests newer shfmt releases.** No job tests a release newer than CI's floor pin, so nothing warns of upstream drift before it reaches a consumer. The strict check then denies a re-encoded tree, and the SessionStart probe names it at the next session start when it touches a construct the probe holds (row 61). The engineer selected "Cut it (Recommended)" and wrote "Hold on this seems very overengineered" about adding a drift job (row 60).
- **Mentions of the retired scripts and the old hook name in dated records.** Past `CHANGELOG.md` entries, `docs/case-studies/worktree-enforcement.md`, `docs/reports/2026-08-22-discovery-audit/findings.md` and the dated `docs/design-decisions/git-native-commit-hooks-declined.md` keep them, because each records what held when it was written. For `check-python-floor.sh`, that is the entry at `CHANGELOG.md:649` and the earlier plans `.claude/plans/cursor-adapter.md`, `.claude/plans/hooks-doc-python-floor-list.md` and `.claude/plans/python-floor-3-14.md`.
- **An evaluator spawn budget separate from the wrapper's cap.** The prefilter limits spawns to commands that hold both `git` and `diff`, and the first diff ends the scan. A cap kill already logs `allowed-evaluator-exit=124` (`send-back-skipped-self-review.sh:78-82`). A hung shfmt therefore ends the whole evaluator run, not R5 alone.
- **Bounding shfmt's output or python3's memory for deeply nested input.** The gate still denies such a command, so the cost is availability, not a bypass. `_lib_capped` bounds the time where a cap tool exists. Verification 8 measures one nested case's peak memory, and a peak over that step's threshold puts a byte bound to the engineer (row 117). Below it, Design item 10 records the cost as an accepted residual (rows 66, 115).
- **Denying a parse when neither `timeout` nor `gtimeout` is on PATH.** `_lib_capped_for` runs every hook's capped calls uncapped then (`_lib.sh:136-138`), and requiring a cap tool for this one parse path would set it apart from every other capped call. The engineer chose a SessionStart warning instead (row 111). Design item 11 and row 82 state their bounds as holding only with a cap tool.
- **A shfmt check in `install-dev.sh`, or skipping the redaction gates' existing tests without shfmt.** `install.sh` holds the check, and `CLAUDE.md` § "Commands" lists it as first-time setup. Those gate tests fail without shfmt because the gates deny without it, and Dispatch 1's report-header line names the cause once before any of them fails.
- **Decoding `$'...'` and `$"..."` words.** They stay placeholders.
- **A per-shell dialect, as an intended follow-up.** Parsing a command in the dialect of the shell the Bash tool runs, such as zsh, is left to a later change. The engineer accepted the zsh gap as a recorded residual (row 106), and Design item 10 records it.
- **`install.sh` downloading shfmt itself.** The engineer selected "Check only (Recommended)" (row 3).
