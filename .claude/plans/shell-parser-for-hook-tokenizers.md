# Shell parser for the hook command tokenizers

## Context

Decide whether a real shell parser should replace the hand-rolled command tokenizers behind the hooks, and if one should, which one and how every stow consumer gets it.

Ask: "if prsing commands would be more robust with a proper shell parser, that might be worth the extra install. we'd jsut add it to install.sh rather than install-dev.sh" and "you'll consider the various alternatives?"

**Problem.** Two scripts tokenize the Bash command a hook is judging: `claude/.claude/hooks/split-command-words.py` and `claude/.claude/hooks/parse-git-command.py`. Both build on stdlib `shlex` plus their own heredoc, comment, and quote handling. The splitter's docstring lists valid bash it rejects (an over-deny) and words it drops that bash keeps (a miss). A miss hides a flag from the calling gate, and the callers include the redaction gates that guard a public repository.

**Why now.** A benchmark plan in another session raised whether shell parsing in this repo should stay hand-rolled. That plan keeps bash's own `declare -F` for function spans. The same question applied to the hooks has a different answer shape, because the hooks run on every stow consumer's machine and their failures can leak.

**Intended outcome.** A plan that compares the alternatives against the splitter's documented residual cases and picks one. The alternatives are a parser binary, a parser library, patching the `shlex` tokenizers, and narrowing what the gates need to read. If a parser wins, the plan names how `install.sh` requires it, which tokenizer code it replaces, and what stays.

## Approach

Replace both hand-rolled tokenizers with shfmt's bash parser, in three ordered PRs: PR 1a adds the parser module with no caller, PR 1b switches the three redaction gates to it, and PR 2 switches the worktree gate and the evaluator (row 131). Every command that reaches `_lib_command_words` or the worktree gate's parser then goes through `shfmt -ln bash --to-json`. One stdlib-only Python module checks the syntax tree strictly and projects it into the flag words the three redaction gates read and the CD/GIT records the worktree gate reads. "Three PRs" below lists what each PR carries.

Two guards deny where the parse could show the gates something other than what bash runs:
- A command holding a carriage return denies before shfmt runs, because shfmt reads one as a blank where bash does not (row 118).
- A tree the module does not recognize denies, so a re-encoded tree cannot project to no words (row 24). The check does not see a shfmt that stops writing a key a valid command can omit. The engineer accepted that limit as the session's explanation stated it, and accepted its worktree-gate consequence by a second answer (row 24, Design item 10).

No guard covers the cut residual. Each gate's header records it in one Known-gaps line under the cooperative tier (rows 128-130, 135). Each of its classes can show the gates a command other than the one bash runs, one class per item:
- Odd heredoc delimiters.
- A heredoc inside a backtick substitution.
- An extglob pattern holding bash 5.3's `${ cmd; }` or `${| cmd; }`.
- Standard input fed to a shell or another interpreter.
- The backslash-newline hides.
- A `#` with no whitespace after the end of a word part, which shfmt reads as a comment where bash keeps it in the word (the flush-comment class).

The engineer cut the guards of the first five classes (row 128). The engineer chose to record the flush-comment class as a gap rather than guard it, for the triggers the questions named (row 135). Design item 10 lists the members. Each needs a construction a cooperative agent does not write (row 130). Out of scope says why a Bash tool running a bash below the repo's 5.2 floor adds no member.

The gates parse bash only. The Bash tool can run zsh (row 15), and the engineer accepted that gap as a recorded residual (row 106).

At run time, a missing shfmt, an oversized command, or a tree the module does not recognize denies, and the deny names the cause. The diagnosis and the lockout, one fact per item:
- One warn-only SessionStart hook diagnoses the parse path's dependencies, python3 and shfmt alike, so no gate header restates them (rows 76-77, 94).
- That hook is `check-python-floor.sh`, renamed `check-hook-dependencies.sh` and extended to shfmt.
- It also warns when neither `timeout` nor `gtimeout` is on PATH, because a hung parse tool then stalls each gated command until the harness's hook timeout (row 111).
- Under Cursor, the adapter's sessionStart report runs the same shfmt check (row 95).
- A consumer who pulls before installing shfmt is locked out of the commands these gates parse until they install it. The engineer accepted that lockout (row 6).
- From PR 1b, the notice names the cause at the next session start or resume.

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
- **A `shfmt --from-json` round trip beside the strict check.** It would feed the tree to shfmt's own decoder, reprint it, and compare the reprint with `shfmt -ln bash` on the original text. It is named as a later option, not adopted. One fact per item:
  - shfmt's decoder rejects an unknown key. Each key deletion a reviewer tried that lost words changed the reprint or made the decoder fail. An unmodified tree reprinted as the canonical print on every command tried [verified: staff-backend-engineer code-review round 5 R2, plan-review round 18 R4, on a local build that prints no version].
  - A deleted `CallExpr.Args` makes the decoder panic rather than reprint, so a round trip reads a nonzero decoder status as a mismatch [verified: staff-backend-engineer plan-review round 18 R4].
  - So it would see a dropped key a valid command can omit, which no presence table can list (row 24).
  - It does not replace the strict check's key table, for two reasons:
    - The module reads keys by name, and a rename that shfmt's encoder and decoder make together passes the round trip while it still empties the projection. The table's unknown-key check catches that rename.
    - A position key, such as `Block.Lbrace` or `Lit.ValuePos`, can be deleted with the reprint unchanged [verified: staff-backend-engineer plan-review round 18 R4].
  - It costs two more shfmt runs and a comparison per command, against the parse's 5-second cap (Design item 1). A review finding deferred to Dispatch 2 already says the module's cost nears that cap, and no run measured the round trip [unverified].
  - It needs the tree and the original text twice, and each form weighed changes the parse path's shape [verified: staff-backend-engineer plan-review round 18 R4, round 19 R5]:
    - Python spawning shfmt goes against row 21's no-spawn pin and the interpreter-isolation test.
    - bash holding the JSON in a variable or a temp file goes against Design item 1's rule that no shell variable holds it.
    - bash's `tee` into process substitutions, with a comparison across two pipes, holds no variable and no temp file. It makes a larger pipeline for Design item 1's `PIPESTATUS` classification to cover.
  - The engineer accepted the dropped-key limit for now, as the session's explanation stated it [engineer-verified: "Accept, revisit later (Recommended)"]. The engineer accepted its worktree-gate consequence by a second answer (row 24). Design item 10 records the limit.
  - The revisit condition is a shfmt release that changes its output.
  - That condition is the option's description.
  - The option's description and the question's wording are the session's [unverified].
- **A key-deletion test on the SessionStart probe.** A CI test would delete each non-position key from the probe's parsed tree and require the strict check to deny or the projected words to change. Word-neutral keys would sit on an exclusion list, and any construct the probe lacks would join it, starting with a single-quoted word. It is named as a later option beside the round trip, not adopted. One fact per item:
  - The engineer chose not to add it now [engineer-verified: "Keep as is (Recommended)"]. The quote covers that choice alone. The question's options were "Keep as is (Recommended)" and "Add the probe test", and their descriptions are the session's [unverified].
  - The architect's consult found the realistic drift path is a consumer's newer shfmt build, for which the probe is the only tripwire [unverified: the consult's reasoning].
  - The consult's reason a drop is unlikely: shfmt's encoder writes every non-zero exported field by reflection, so a key vanishes only through a visible upstream change [unverified: the consult's reading].

### Three PRs

The engineer first chose two ordered PRs, one per tokenizer (row 46), then split the first into a module-only PR 1a and a gate-switch PR 1b, with PR 2 unchanged (row 131). Each PR projects 400 or more changed lines (row 72). Asked whether to split further at those sizes, the engineer answered "Proceed anyway" (row 134). PR 1a's commit-time size prompt cites that answer, and PR 1b and PR 2 each ask again on their own branch (Critical files).

- **PR 1a, the module.** It carries Design item 2's strict check, walker, word flattening and `words` projection, `_LIB_SHFMT_ARGV`, the module's tests and test helpers, and Design item 7's pin step and version report. No gate calls the module, and `split-command-words.py` and `test_split_command_words.py` stay, because the splitter still runs.
  - Its first push follows the pin step's commit, so CI's first contact with the pinned shfmt and with CI's bash comes before any gate depends on either.
  - This plan file ships in it.
- **PR 1b, the redaction gates.** It carries Design items 1, 3, 6, 8, 11 and 12, item 7's floor check, and PR 1b's parts of items 9 and 10. It deletes `split-command-words.py` and `test_split_command_words.py`.
  - The marked rows of the `words` differential table, verdict and path-string changes alike, go to the engineer after Dispatch 1 and before PR 1a's first push, and PR 1b's expectation changes follow that answer (Verification 1, row 108).
  - Status 8 lands here, because `_lib_shell_parse` is the first shfmt caller and must classify every shfmt exit.
  - The install check, the SessionStart check, and the Cursor adapter's PATH and shfmt check land here, because this is the first PR whose gates call shfmt (row 75).
  - It branches from the default tip once PR 1a merges, because it builds on PR 1a's module and pin, and PR 1a's review can still change them.
- **PR 2, the worktree gate and the evaluator.** It carries item 2's `git-records` projection and evaluator interface, items 4 and 5, and PR 2's parts of items 9 and 10. It deletes `parse-git-command.py`.
  - Its first step builds the table of changed worktree-parser cases for the engineer to review.
  - It branches from the default tip once PR 1b merges, because it builds on PR 1b's `_lib_shell_parse`, and PR 1b's review can still change it. It does not wait for PR 1b to gain field time (row 107).
- **Between the PRs**, one fact per item:
  - After PR 1a, every gate still runs its old tokenizer, so a consumer needs no shfmt.
  - A contributor without shfmt sees the cause, one way per item:
    - The module tests skip locally with a reason naming the pin in `.github/workflows/tests.yml`.
    - The report-header line names the cause on a run that names a path under `claude/.claude/hooks`.
    - A full-suite run shows it through the skip text.
  - No text in PR 1a points ahead to PR 1b. One site per item, with the dispatch that adds its pointer:
    - The skip reason and the report-header line name the pin in `.github/workflows/tests.yml`. Their `README.md` § "Requirements" citation arrives with PR 1b's shfmt bullet (Dispatch 5).
    - The `flatten_word` docstring names no decision file. Dispatch 5, which creates the file, adds that pointer.
    - PR 1a's other shfmt wording says only what PR 1a does. Dispatch 2 widens it to the gates (Dispatch 1's amendment).
  - After PR 1b, the repo runs two tokenizers, as it does today. The redaction gates parse with shfmt, and the worktree gate and the evaluator keep `parse-git-command.py`.
  - The module holds no git-records code until PR 2 moves the classifiers into it, so on the default branch they sit in one file at every point.
  - A consumer who installed shfmt for PR 1b needs nothing new for PR 2.

### Design

1. **One parse path in `claude/.claude/hooks/_lib.sh` (PR 1b).** It adds a parse function, two functions that word a failure and the deny reason's composition. PR 1a adds its one named array.
   - **`_lib_shell_parse CMD PROJECTION [CAP_SECONDS]`.** PROJECTION names one of the module's projections and reaches the module unchanged, so PR 2 adds `git-records` without editing `_lib.sh`. CAP_SECONDS defaults to `_lib_capped`'s 5 (`_lib.sh:50-51`), so the gates pass two arguments and only the shared shfmt check passes a third (Design item 12, row 110). It runs these steps in order:
     1. It returns `_LIB_SHELL_PARSE_OVERSIZE_STATUS` (7) when CMD exceeds `_LIB_SHELL_PARSE_MAX_BYTES` (65536). It counts bytes under `local LC_ALL=C`, the function-local form `_lib.sh:590` uses (rows 30-31). The pipeline's children can inherit it harmlessly, because the module reads bytes (Design item 2).
     2. It returns 3 when CMD holds a carriage return, matched as the byte 0x0D under the same `LC_ALL=C` (row 118). Its one-line comment says shfmt reads a carriage return as a blank and bash does not.
     3. It returns `_LIB_SHELL_PARSE_NO_PYTHON3_STATUS` (127) when `command -v python3` fails. It checks python3 before shfmt, so for a command that passes the cap and carriage-return checks, every gate and the SessionStart hook name the same tool on a machine missing both (row 109). 127 is what the python3 call itself returns when python3 is absent, so one clause and one recovery item cover both.
     4. It returns `_LIB_SHELL_PARSE_NO_SHFMT_STATUS` (6) when `command -v shfmt` fails.
     5. It keeps the existing not-linked check, retargeted at the module through `_lib_shell_syntax_tree_path`. That is today's `_lib_command_words_tokenizer_path`, renamed, with its readlink hop kept.
     6. It runs one pipeline: `printf '%s' "$CMD" | _lib_capped_for CAP shfmt | _lib_capped_for CAP python3 -I -S <module> PROJECTION`, where `shfmt` stands for `"${_LIB_SHFMT_ARGV[@]}"` (row 59).
        - Every stage discards stderr, because shfmt's parse message can quote the command.
        - The JSON goes straight from shfmt to python3. No shell variable holds it, and no here-string writes it to a temp file.
        - Both caps start with the pipeline, and python3 cannot finish before shfmt does, so the whole parse shares one cap rather than two in sequence.
     7. It reads shfmt's and python3's statuses from `PIPESTATUS`. The first case that matches gives the status it returns (row 59):
        1. shfmt 0: python3's status, unchanged.
        2. shfmt 141, death by SIGPIPE, beside a nonzero python3 status: python3's status, because python3 closed the pipe first.
        3. A shfmt cap-kill status: that status, unchanged.
        4. shfmt 1, its syntax error: 3.
        5. Any other nonzero shfmt status, a 141 beside python3's 0 included: `_LIB_SHELL_PARSE_SHFMT_FAULT_STATUS` (8).

        Mapping exit 1 to 3 keeps 3's "could not be tokenized" lead.

     One rule orders the steps. The checks that read the command text alone, the byte cap (7) and the carriage return (3), come before the tool checks (127, 6) and the parse, so a command gets the same input-shape deny on every machine (rows 30-31, 118).
   - **Its stdout.** python3 can print words before shfmt's status is known, so the output holds usable words only on status 0. Every caller captures it with `$(...)` and discards it on a nonzero status. `_lib_command_words` prints what it captured only on status 0, so its "nonzero with nothing printed" contract (`_lib.sh:2561`) still holds.
   - **`_LIB_SHFMT_ARGV`** is a named array, which PR 1a adds. Every test that runs real shfmt takes its argv by sourcing `_lib.sh`, so no test parses with a command the gates do not run. PR 2's Python copy is Design item 2's.
   - **`_lib_shell_parse_failure_clause STATUS`** gives each status its wording. It is today's `_lib_command_words_failure_clause`, renamed in PR 1b because the worktree gate uses it from PR 2 on. Every clause names a cause, so no parse failure denies without one (row 76).
     - A clause states the cause only. It carries no instruction, no "this gate" wording and no citation, so the SessionStart hook and the Cursor report reuse it unchanged (row 103). Today's not-linked clause at `_lib.sh:2600` loses its "stop and ask" tail.
     - The clause for 3 says shfmt rejected the command as invalid bash, or that the command holds a carriage return, which shfmt reads differently from bash (row 118). It drops today's xargs and 2 MiB wording.
     - The oversize clause, for 7, names the cap.
     - The clause for 8 says the parse step failed: shfmt exited with an error, or the parse rejected a command known to be valid bash. The second covers the session-start probe's 3, which shfmt's exit 1 can give (Design item 12).
     - The clauses for 5 and 6 name a tree the module does not recognize and a shfmt not on PATH.
     - The clauses for 2 and 127 also name the extraction step's awk, because the source-path extractors return awk's own status through the same deny reason (`_lib.sh:2643-2648`, `:2661-2666`). The clause for 2 names a fault in the projection module or awk. The clause for 127 names a python3 or awk not on PATH or not runnable.
     - The cap-kill clause says shfmt or python3 was killed by the parse cap or a signal.
     - The clause for 9, the probe's mismatch (Design item 12), says shfmt's tree for a known command no longer projects to the expected words.
     - Any other status takes the default clause: a tool in the parse or extraction step failed, with its exit status. It names python3, its cap wrapper, awk, and the temp file awk's here-string can need, as today's default arm names python3, awk and that temp file (`_lib.sh:2608`). It drops that arm's "check that each runs" instruction.
   - **`_lib_shell_parse_deny_tail STATUS WORKAROUND`** prints the instruction that follows a clause in a deny. WORKAROUND is `with-file-workaround` or `without-file-workaround`. It is the one home of the status-to-tail mapping: `_lib_command_words_deny_reason` and PR 2's worktree gate both call it, and neither holds a case statement of its own (staff-platform-engineer round 10 R3).
     - One precedence rule comes first. When the module is not linked, the tail is the tool-fault sentence alone, whatever the status, 3 and 7 included. `_lib_shell_parse` returns those two before it consults the link, and the clause then names the unlinked module, which no rewrite of the command fixes. Today's reason omits the workaround in that case too (`_lib.sh:2625`).
     - Otherwise the tail follows the status, one status per item:
       - 3: the file workaround under `with-file-workaround`, and nothing under `without-file-workaround`. Content moved to a file takes a carriage return out of the command, and the clause names the cause.
       - 7: the file workaround under `with-file-workaround`, and nothing under `without-file-workaround`. Content moved to a file brings an oversized command back under the cap.
       - 4: nothing, as today.
       - Every other status: the tool-fault sentence. One reason per status it covers:
         - 127 and the module's own 2, which it now covers: without the `xargs -n1` fast path, python3 runs on every parsed command (row 59).
         - A cap kill: a hung tool is the likelier cause than the command itself (row 102).
         - An unlisted status, such as python3's own 1, 126 or 139: `_lib_capped_for`'s header reads any status a caller does not recognise as the child's or the wrapper's own failure, and requires the caller to fail closed on it (`_lib.sh:117-120`).
     - The tool-fault sentence tells the agent to stop and ask, and cites `docs/hooks.md` § "Gate deadlock recovery".
     - The recovery entry gives the human a diagnostic and a fix for each listed status, and one for the default arm (Design item 9).
   - **`_lib_command_words_deny_reason`** composes its lead, the clause, and `_lib_shell_parse_deny_tail STATUS with-file-workaround`. Only the redaction gates compose their reason here, so the workaround reaches them alone (Design item 4). Three rules hold:
     - When the module is not linked, the lead is "could not be checked" at every status, 3 included, the same precedence the tail follows (staff-platform-engineer round 11 R2).
     - The file workaround keeps today's sentence (`_lib.sh:2631` in the staged tree) minus its "multi-line or nested-quoted" wording, because shfmt parses both: write the content to a file in an earlier Bash call and pass it with the flag, or split the command into separate Bash calls.
     - No clause or reason echoes the command or a tool's stderr, as the comment above `_lib_command_words_deny_reason` guarantees today.
2. **The projection module `claude/.claude/hooks/shell-syntax-tree.py`.** PR 1a adds it with no caller, and it replaces `split-command-words.py` in PR 1b and `parse-git-command.py` in PR 2.
   - **Interface.** It reads shfmt's JSON on stdin, and its one argument picks the projection. It exits 0 on success, 2 on an internal fault or bad usage, and 5 when the tree is not recognized. It never exits 1, as today. PR 1a ships `words` only, so `git-records` is bad usage until PR 2 adds it.
     - It keeps the staged one-argument interface and usage line (`shell-syntax-tree.py:412-414`).
     - It prints nothing on stdout unless it exits 0. The projection buffers its output, because the conservation count runs after it.
     - On stderr, exit 5 prints one line of fixed text naming the failed condition, and exit 2 names only the exception type. No exit prints tree or command text.
     - It reads `sys.stdin.buffer` and decodes it as UTF-8, and it writes its words to `sys.stdout.buffer` as UTF-8, so the locale changes neither. The docstring states both.
       - The module never receives a tree built from a non-UTF-8 byte or a carriage return, by one upstream guarantee each. Dispatch 2 adds both to the docstring, because the second needs `_lib_shell_parse`, which PR 1b adds:
         - shfmt exits 1 on a non-UTF-8 byte (row 113).
         - `_lib_shell_parse`, and the evaluator's closure, return before shfmt starts on a carriage return (row 118, Design item 5).
     - A top-level handler maps a `RecursionError` from `json.loads` on deep nesting, and any other exception, to 2.
     - The walker uses an explicit stack, not recursion.
     - `main` runs the strict check, the projection, then the conservation count, as staged (`shell-syntax-tree.py:416-421`). PR 2 moves that order into one function, which `main` and the evaluator both call, so it keeps one home.
     - The strict check raises `TreeNotRecognized`, which the command line maps to 5.
     - PR 2 adds `SHFMT_ARGV`, `MAX_COMMAND_BYTES`, `FIELD_SEP` and the `git-records` projection to the module.
     - `SHFMT_ARGV` and `MAX_COMMAND_BYTES` are the second copies of `_LIB_SHFMT_ARGV` and `_LIB_SHELL_PARSE_MAX_BYTES`, which the evaluator needs from Python. A PR 2 test pins each pair equal, under CLAUDE.md's small-duplicated-value exception.
     - The carriage-return rule is a predicate, not a value, so a parity test holds its two copies together instead (Design item 5).
   - **Strict check.** The module exits 5 unless all of these hold, the conditions the staged module checks (row 24, `shell-syntax-tree.py:26-37`):
     - The root is an object of type `File`.
     - Every `Type` is in `KNOWN_NODE_TYPES`.
     - Every `BinaryCmd` operator is in `KNOWN_BINARY_OPERATORS`.
     - Every object's keys fall within the key set of the Go struct it encodes. A typed object is matched by its `Type`, and an untyped one by the type and field that hold it.
     - Every key in its struct's `ALWAYS_PRESENT_KEYS` entry is present (row 24).
     - No `ExtGlob` pattern holds `$(`, a backtick, `<(` or `>(`, the staged `EXTGLOB_SUBSTITUTION_MARKERS` (`shell-syntax-tree.py:237`).
     - The number of `CallExpr` nodes the projection visited equals a raw count of `CallExpr` objects in the tree. This condition is checked after the projection runs.

     Under Given 2, a renamed field shows up as an unknown key whenever it holds a value. A new construct, or a re-encoded `BinaryCmd` operator, denies instead of projecting to no words.

     What the check does not detect is a shfmt that stops writing a key a valid command can omit. Row 24 gives the evidence, and Design item 10 states the limit and its acceptance.

     The extglob condition is a command-text condition inside a tree check, so its deny takes status 5's clause and tool-fault sentence. Exit 5 cannot tell it from a re-encoded tree, so the clause does not name it. The recovery entry's status-5 item names it, and the two empty-`Lit` shapes row 24 records, as rare causes that depend on the command (Design item 9). It stays as staged. Row 125's move to a status-3 check of its own went with the cut (row 128).

     Where the check's sets come from, and its scope:
     - **Sources**, one per set:
       - The operators and per-struct key sets come from the published `mvdan.cc/sh/v3/syntax` package at v3.14.0.
       - `KNOWN_NODE_TYPES` holds the types shfmt can write as a `Type` value, `File` and every implementer of the `Command`, `WordPart`, `ArithmExpr`, `TestExpr` and `Loop` interfaces, minus `BASH_REJECTED_NODE_TYPES`. It leaves out `BraceExp`, because only `syntax.SplitBraces` builds one and shfmt never calls it.
       - `BASH_REJECTED_NODE_TYPES` is `TestDecl` and `FlagsArithm`, the dialect-only types that `-ln bash` rejects (row 86).
       - `ALWAYS_PRESENT_KEYS`, defined in row 24, one fact per item:
         - Row 24 states the table's definition, its four exceptions and the `Lit.Value` caveat.
         - Its evidence is Dispatch 1's dump of each struct's smallest input and the conformance corpus.
         - For `File`, the smallest inputs are an empty command and a comment-only command (row 26).
       - The conformance corpus confirms every set against real shfmt.
     - **Scope.** The whole check lands in PR 1a, including node types only `git-records` reads. The engineer kept it as it stands (row 74).
   - **No command-text checks.** The module holds no delimiter, placement, extglob-widening or interpreter check, because the engineer cut them (row 128). Design item 10's cut residual records the shapes they denied.
   - **Word flattening, shared by both projections.**
     - A `Lit` part contributes its value, decoded as the last bullet below says.
     - A `SglQuoted` part without `Dollar` contributes its value verbatim.
     - A `DblQuoted` part without `Dollar` contributes its `Lit` parts, and each other part inside it as the placeholder bullet below says.
     - A part of any other kind, inside double quotes or not, contributes a fixed placeholder that begins with `$`. The literal parts on both sides of it keep their text (row 27).
       - The other kinds are parameter, command, arithmetic and process substitutions, `$'...'`, `$"..."` and extglobs.
       - An extglob whose pattern holds a substitution marker never reaches flattening, because the strict check denies it.
       - So `--body-file="$F"` yields `--body-file=` and the placeholder, `-f body=@"$F"` yields `body=@` and the placeholder, and `$HOME/bin/git` keeps its `/git` suffix (row 9).
       - A caller extracts a path holding the placeholder and denies it as unreadable, as it denies a literal `$F` today (row 28).
       - `_needs_expansion` reads the `$` as needing expansion.
     - `Lit` values keep their backslashes (row 26), so the module always decodes them by bash's two rules: the unquoted escape character and the double-quote escapes. Quote the Bash Reference Manual sections in the code comment.
       - Dispatch 1's dump runs on the session's shfmt, a build that prints no version, and confirms the raw form there. CI's pinned 3.14.0 settles it at PR 1a's first CI run, where the real-bash comparison runs. A run that shows decoded values contradicts row 26 and stops the session.
       - Dispatch 1's commit message justifies hand-rolling the decoder, naming the standard-library alternatives checked and why each fails, per `claude/.claude/CLAUDE.md` § "Engineering Judgment" ("Hand-rolled logic in non-trivial domains").
         - Per code-review round 4, the message names shlex's four failing behaviours and the `re.sub` alternative the decoder was kept over. The four behaviours, one per item:
           - A trailing backslash raises.
           - It keeps the backslash pair, in `"\$x"` and in a double-quoted backslash-newline.
           - An unquoted backslash-newline becomes a newline.
           - It reads quotes as delimiters.
   - **Traversal, shared by both projections.** The walker descends every list and object value of every node, not a field allow-list (row 56). It therefore reaches a command nested in an assignment value, a declaration argument, a redirect target, an unquoted heredoc body, a process substitution, a `for` word list, `[[ ]]`, `(( ))`, a parameter default or an array element (row 57). What the walker cannot reach, one per item, the last two recorded in the decision file's cut residual (rows 128, 135):
     - Quoted heredoc bodies and comments hold no command nodes.
     - A `#` that shfmt reads as a comment where bash reads it as part of a word hides what follows it.
     - A heredoc fed to a shell holds commands bash runs that no node carries.
   - **`words` (PR 1a).** Each `CallExpr`, in the order the JSON lists them, contributes its `Args` words, then one blank line (row 29). Assignments, redirect words and heredoc bodies contribute no words of their own, only the commands nested in them. A newline inside a word becomes a space, as today.
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
     - Under these rules no `cd` shape turns from deny to allow against the old parser, apart from the cut residual's continuation hides, such as `cd /x # c \<LF>git push` (row 129). Verification 3's differential table checks that.
     - A simple command's nested statements emit before its own record, in the order bash runs them.
     - `classify_cd_segment`, `classify_git_segment`, `_needs_expansion`, `_contains_wire_delimiter`, `_is_literal_git_version_query`, `GIT_FLAGS_WITH_ARG`, `FIELD_SEP` and `emit_segment` carry over verbatim. The in-group-1 CD records the rules above add go through `emit_segment` too, so the record grammar does not change.
     - The unbalanced-quote, unbalanced-group and unterminated-heredoc SENTINELs give way to shfmt's syntax-error exit, which `_lib_shell_parse` turns into status 3.
   - **Isolation.** The splitter's interpreter-isolation and capability-pin tests carry over to the module. `json` is stdlib and outside the pin. The module's copies live in the contract test file, which needs no shfmt, so they never skip. The splitter's own copies go with its test file in PR 1b.
3. **`_lib_command_words` (PR 1b)** becomes `_lib_shell_parse "$1" words` plus the existing no-words check (status 4), which now counts only non-blank words. It prints the words it captured only on status 0 (Design item 1). The `xargs -n1` fast path goes (rows 18-20), so the output carries no xargs prefix. The extractors and the gh-api callers do not change, because they already skip a blank path (row 28).
4. **The worktree gate (PR 2).** The parser call at `require-worktree-for-git-writes.sh:293-309` becomes `_lib_shell_parse "$COMMAND" git-records`. Its deny is the shared clause followed by `_lib_shell_parse_deny_tail STATUS without-file-workaround` (Design item 1).
   - Its tail per status is the `without-file-workaround` column of `_lib_shell_parse_deny_tail`'s list in Design item 1. The file workaround reaches only the redaction gates.
   - The status-3 clause names its causes, invalid bash or a carriage return, so the agent can fix the command line.
   - The existing python3 presence check stays first, matching `_lib_shell_parse`'s own order (row 109). So for a command that passes the cap and carriage-return checks, every gate tells a machine missing both tools about python3. A command that fails one gets the python3 deny here and status 7 or 3 from a redaction gate.
   - For status 6, the deny adds the self-locked-worktree escape hatch that the python3 deny names.
   - The fast path's relocation check at :273 matches `pushd` and `popd` as well as `cd`, so a worktree session's `pushd /main && git push` reaches the parser (row 104).
     - It does not send a command to the parser for holding a backslash-newline alone. A cooperative agent never splits `cd` or `-C` with one. The gate's tier omits `untrusted-input`, so `docs/hooks.md:13` waives the shape.
     - The fast path decides only while the session's lock is held and the collision guard allows (`require-worktree-for-git-writes.sh:278-279`). With the lock absent, or the guard denying, every command holding a contiguous `git` falls through to the parser, as in a main-tree session (staff-platform-engineer round 11 R1).
   - The write deny at :396 adds a `cd` whose effect is uncertain to its list of causes. Its remedy, a literal `cd <worktree-path> && git ...`, stays.
   - The header changes in the places below. None of them lists the parse path's tools or how to repair one, because the SessionStart notice and the recovery entry hold that diagnosis (rows 77, 84).
     - The Mechanism paragraph says the gate parses through `_lib_shell_parse`, and cites the module for the record grammar and the in-group rules. Its list of what keeps a resolution from being clean adds a `cd` whose effect is uncertain.
     - The precondition paragraph becomes one line: any parse failure denies with a reason that names the cause, and `docs/hooks.md` § "Gate deadlock recovery" gives the recovery.
     - Known gaps close: the newline, same-line-heredoc and no-size-cap gaps. The same-line-heredoc gap's substitution forms, such as a quoted delimiter that is itself a `git push` line, stay open as part of the cut residual line below (row 128).
     - Known gaps added, one line each:
       - An over-cap command denies.
       - A quote-split or continuation-split `git`, such as `g\it`, `gi""t` or `gi\<LF>t`, leaves the command without a contiguous `git`, so the prefilter at :223 allows it before any parse (row 105).
       - With the session's lock held, a quote-split or continuation-split `cd`, `pushd`, `popd` or `-C`, such as `c\d /main && git push`, `c\<LF>d /main && git push` or `git -\<LF>C /main push`, skips the parse at :273-276, so its write is judged at the session's cwd. This pre-dates the change [verified: ciso-reviewer round 7 R3, cited in row 121].
       - The gate reads none of `--git-dir`, `--work-tree`, `GIT_DIR=` or `env -C` as a relocation, so a write they point elsewhere is judged at the running cwd. The parser reads `--git-dir` and `--work-tree` only as flags that consume the next word (`parse-git-command.py:71-84`). This pre-dates the change.
       - A command the Bash tool runs as zsh is judged on bash's reading of it. The line cites the decision file's zsh residual (Design item 10, row 114).
       - The cut residual, beside the zsh line: the members of Design item 10's list, whose tree can show a command other than the one bash runs. The line cites the decision file's cut residual (Design item 10, rows 128-130). For this gate the heredoc classes pre-date the change, because the base parser dropped every heredoc body, and the continuation members the base denied are regressions the engineer accepted (row 129). The line names the flush-comment class among the classes, which the engineer cut for this gate too (row 135).
       - A shfmt that stops writing a key a valid command can omit leaves an empty record list, which this gate reads as nothing to judge and allows. The line cites the decision file's dropped-key limit (Design item 10, row 24).
       - Quoted text a builtin runs as shell, such as `bash -c`, `eval` or `trap`, holds a command the parse does not read. The base parser kept quoted text whole too. The line cites the decision file's quoted-text residual (Design item 10).
     - Known gaps changed: the three python3-less entries name a machine where the parse path cannot run, not python3, and keep their §32 citations. The capped-calls entry counts `_lib_shell_parse`'s two capped calls, which run together in one pipeline.
5. **The self-review evaluator (PR 2)**, a dependent of row 1's scope (row 52). `load_git_record_builder()` loads the module by path, as it loads `parse-git-command.py` today. It returns a `build_records(command)` closure and `FIELD_SEP`, so `assess` and `runs_git_diff` keep their parameters.
   - **The closure's return** is one `GitRecordsResult(records, unparsed)` value, the single carrier of a withheld or credited reason from the closure to `run` (staff-sdet round 11 R3):
     - `records` is the record list. It is empty in every withheld case.
     - `unparsed` is `None` when the closure read the command, or an `UnparsedReread(outcome, reason)` whose outcome is `withheld` or `credited` and whose reason is one of the names below.
     - `runs_git_diff` returns a `DiffReread(found, unparsed)`. `found` is true for a `git diff` record or a credited command, and `unparsed` passes the closure's value on.
     - `_is_diff_reread` returns the same type, `DiffReread(found, None)` for a Read. `assess`'s loop tests `found`, never the value itself, because a two-field tuple is always true.
     - `assess` collects each `unparsed` that is not `None`, in call order, into a new `Assessment` field, `unparsed_rereads`.
     - `run` reads `assessment.unparsed_rereads` and logs one line per entry before its verdict line.
     - The `Workspace` fixture's injected builder returns the same type.
     - So PR 2's parity test asserts a reason on the closure's `unparsed`, and Verification 7's log-line cases assert it through `run`, both on one carrier. No module global holds a reason, so none leaks between cases in one process.
   - The closure returns no records, and spawns nothing, unless the command text holds both `git` and `diff` (row 54).
   - Otherwise it runs `SHFMT_ARGV` through `subprocess` with the command on stdin and stderr discarded, and projects the tree in-process.
   - When shfmt exits 1, the closure returns no records, matching today's SENTINEL result. The writer can change the command, so withholding credit is right here. Row 89's credit path is for faults the writer cannot repair.
   - A command holding a carriage return also returns no records, and spawns nothing, because `_lib_shell_parse` gives it status 3 before shfmt starts (row 118).
     - The test reads the closure's argument, the command text as the transcript holds it, before any join, split or strip.
     - It runs after the byte cap, in `_lib_shell_parse`'s order. An over-cap command holding a carriage return therefore earns `oversize` credit, where `_lib_shell_parse` returns 7.
     - The closure and `_lib_shell_parse` both implement the rule as a predicate. No value pin holds a predicate equal, so a PR 2 parity test runs one shared list through both instead (Verification 7).
   - Each withheld case above logs its cause, so a human reading the log can tell a withheld re-read from a missing one (staff-platform-engineer round 10 R5).
     - `run` logs one `reread-withheld-unparsed=<reason>` line per withheld command, before its verdict line, as the credit path below logs its own.
     - The reasons: `shfmt-exit-1` and `carriage-return`.
     - The prefilter's no-records result is not a withheld case and logs nothing, because the command holds no `git diff`.
   - Every other failure earns the command R5 credit instead of raising (row 89). A parse fault then degrades R5 alone, and the evaluator's other checks still run.
     - The guard covers the UTF-8 encode for the byte count and for shfmt's stdin, as well as the shfmt call and the in-process projection.
     - A lone surrogate, which a transcript's escape such as `\udcff` decodes to, makes that encode raise.
     - `run` then logs a `reread-credited-unparsed=<reason>` line before its own verdict line, as an evaluator error logs a pair today.
     - The reasons, each with its trigger:
       - `shfmt-missing`: shfmt does not resolve.
       - `shfmt-start-failed`: any other `OSError` from starting shfmt (a non-executable or wrong-architecture file).
       - `shfmt-exit-N`: shfmt exits N, for any N other than 0 and 1.
       - `oversize`: the command is over the module's `MAX_COMMAND_BYTES`.
       - `tree-unrecognized`: the projection raises `TreeNotRecognized`.
       - `parse-fault`: any other exception, `JSONDecodeError`, `RecursionError` and a lone surrogate's `UnicodeEncodeError` included.
     - `MAX_COMMAND_BYTES` equals `_LIB_SHELL_PARSE_MAX_BYTES`. The PR 2 test that pins `SHFMT_ARGV` pins it too.
   - Fail posture: the evaluator stays fail-open, as its wrapper's header states (row 90). It is a workflow nudge for a cooperative writer, not a gate.
     - The credit path keeps it from sending the writer back for a fault the writer cannot repair, which would also spend the cycle's one send-back (row 89).
     - The log line records the cause. The SessionStart notice is the early warning: it shows the human a cause present at session start (Design item 11). A fault that starts mid-session reaches only the log (row 91).
   - The closure carries no timeout of its own, because the wrapper's 5 s cap bounds the whole run.
   - `runs_git_diff` hands the closure the command exactly as the transcript holds it, and the closure parses it once (`evaluate-code-writer-self-review.py:393-407` today).
     - Its per-line split and blank-line skip go, because they existed only for the old parser's newline gap.
     - Both continuation joins go with them, the backslash-CR-LF join and the backslash-LF join at :400, one reason per join:
       - The backslash-CR-LF join would remove the carriage return before the closure's carriage-return test could read it.
       - shfmt reads a continuation itself, so the backslash-LF join would only change text inside single quotes and quoted heredoc bodies, where bash keeps both characters.
     - So `git diff \<LF>--stat` still earns credit, through shfmt's own join.
     - `git dif\<LF>f` holds no `diff`, so the prefilter now withholds its credit, which the base's join gave it. That is the evaluator's safe direction (staff-sdet round 10 R3).
     - Its docstring, which explains the split, gives way to one line: the command reaches the closure unnormalized, because the carriage-return test and shfmt must read the text bash runs.
   - Behavior changes, one per item:
     - `# check git diff later` stops earning R5 credit, because the parser drops comments.
     - `git dif\<LF>f` stops earning it, because the prefilter reads the unjoined text.
     - `echo git diff` keeps earning it, because `classify_git_segment` takes the first `git` word in any position (row 55).
   - `docs/design-decisions/code-writer-self-review-send-back.md` § "Log verdicts" gains the two new verdicts and their reasons, because it is the vocabulary's single home (row 71). Its table and notes change in these places (staff-platform-engineer round 11 R4):
     - `reread-withheld-unparsed=<reason>`: the command earned no R5 credit, because bash and the parse may read it differently. Degradation: No, because withholding credit is the safe direction. Operator action: None. The writer earns credit by writing the command as its reason says, one fix per reason (comment-discipline-reviewer round 13 R4):
       - `carriage-return`: without a carriage return.
       - `shfmt-exit-1`: as valid bash.
     - `reread-credited-unparsed=<reason>`: the parse could not run, so the command earned R5 credit unread. Degradation: Yes, because R5 counted a re-read it never read. Operator action: for a `shfmt-*`, `tree-unrecognized` or `parse-fault` reason, `docs/hooks.md` § "Gate deadlock recovery". For `oversize`, none.
     - The note at :118, one line per invocation that reaches a verdict, gains a second exception: these lines come before the same run's verdict line, one per command they name.
6. **`install.sh` and the shared floor (PR 1b).**
   - `claude/.claude/hooks/_config.sh` holds the floor beside the python3 floor, because `install.sh` and the shared shfmt check (Design item 12) both compare with it (row 81).
     - It adds `_SHFMT_FLOOR_MAJOR`, `_SHFMT_FLOOR_MINOR` and `_SHFMT_FLOOR_PATCH` (3, 14, 0), `_shfmt_version_meets_floor` and `_shfmt_floor_status [RUNNER...]`, modeled on `_python_version_meets_floor` and `_python3_floor_status` (`_config.sh:70-113`).
     - `_shfmt_floor_status` reads the first `X.Y.Z` in `shfmt --version`, with or without a leading `v`, and compares it field by field. It returns 0 at or above the floor and 1 below it, printing the validated version for both. It returns 2, printing nothing, when shfmt is missing or prints no readable version.
     - Each field is 1 to 9 digits and compared in base 10, as the python3 and git checks do.
   - A new `shfmt-floor-check` block in `install.sh` goes between INSTALL_TEST_FIXTURE markers, after the git floor block and before the first `$HOME` mutation at `install.sh:138`. It calls `_shfmt_floor_status`.
   - A missing shfmt exits 1 with these install routes, and the message notes that distro packages can be older:
     - Homebrew.
     - The mvdan/sh release binary. The message names the floor release and says what holds for it, so a bump updates it beside the CI comment (Design item 7, row 40):
       - The release carries no checksum file.
       - `gh release verify v<floor> -R mvdan/sh` confirms its GitHub release attestation, which lists each asset's digest to compare a download's hash with.
       - That match shows the asset is the one the release published, not how it was built, and its root of trust is GitHub.
     - `go install mvdan.cc/sh/v3/cmd/shfmt@v<floor>`, never `@latest`, with `$(go env GOPATH)/bin` on the PATH Claude Code starts with.
   - A version below the floor exits 1.
   - When no version is readable, a notice names the resolved shfmt, says its version could not be read, and says the hooks deny any syntax tree they do not recognize. The install then continues (rows 33-34).
   - Every failure prints `shfmt resolved on PATH: <path>`, or "none found".
   - Every failure tells the human to re-run `./install.sh` and restart Claude Code, so its hooks resolve the same shfmt.
   - Every failure cites `README.md` § "Requirements". The python3 and git blocks set that precedent (`install.sh:84-99`, `:125-135`).
   - Success prints one line naming the resolved shfmt and the same restart advice, as the bash floor check does at `install.sh:31`.
   - shfmt stays out of the generic presence loop at `install.sh:35-43`. That loop's "system package manager" advice would send apt users below the floor (Given 3).
   - The missing-cap-tool warning at `install.sh:1052`, which names only jq and git checks, adds that the hooks' command parse then runs uncapped, so a hung shfmt or python3 stalls each gated command until the harness's hook timeout (row 111).
7. **CI (PR 1a, with its floor check in PR 1b).**
   - An "Install the pinned shfmt binary" step, id `pin-shfmt`, runs in both legs after the stow step, under `if: steps.detect.outputs.changed == 'true'`. Its env holds `CI_SHFMT_VERSION: "3.14.0"`, the floor build (row 62), and `CI_SHFMT_SHA256`, an in-repo literal digest (row 38).
     - A one-line comment says why it runs in both legs, unlike the zsh step, `pin-zsh`: a `timing` case that parses with shfmt then finds the pinned build, as a parallel-leg case does. The cost is one download per leg (staff-platform-engineer round 15 R2).
   - The step body does the following:
     - It runs under `set -euo pipefail` and fails naming the key when either env value is empty.
     - It downloads the linux amd64 asset, its URL built from `CI_SHFMT_VERSION`, into a fresh `mktemp -d` directory with `curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' --retry <n> --retry-max-time <s> --max-time <s>`.
     - The `--retry`, `--retry-max-time` and `--max-time` values each carry a comment that cites the curl manual's entry for its flag and says no vendor value applies. `--retry-max-time` bounds the retries' total time (staff-platform-engineer code-review round 4 R1). It exceeds `--max-time`, so an attempt that `--max-time` ends still leaves time for a retry.
     - It checks the file with `sha256sum -c` against a line built from the literal and the downloaded file's own name.
     - Its install directory is `CI_SHFMT_INSTALL_DIR` when set and `/usr/local/bin` otherwise. That variable is a test-only seam: the step-body test sets it to a stub directory, and no workflow, job or step env sets it, so the runner installs into `/usr/local/bin`.
       - The seam's design is the session's decision [unverified]. The engineer kept it in PR 1a's scope (row 136).
       - Its guard has two limits, accepted by the session's decision, not an engineer answer [unverified], one per item:
         - The test that no env sets the seam scans only the workflow's, each job's and each step's `env:` block, so a `$GITHUB_ENV` write in an earlier step's `run:` would set the seam unseen.
         - `test_ci_shfmt_equals_the_pin`, which requires `command -v shfmt` to be `/usr/local/bin/shfmt`, carries no `timing` mark, so it runs only in the parallel leg. The timing leg has only the step's own resolved-path check, which follows the seam.
     - It installs the binary with `sudo install -m 0755` only after the check passes, and never runs it before then.
     - After the install, it checks the installed file against the same digest, because the first check covers only the downloaded file. The re-check's design is the session's decision [unverified]. The engineer kept it in PR 1a's scope (row 136).
     - It checks that `command -v shfmt` is the `shfmt` it installed, so a same-version shfmt earlier on PATH cannot stand in for the pinned bytes (ciso-reviewer code-review round 4 R6).
     - It prints `shfmt --version`.
     - On failure it says whether the fetch, the downloaded file's hash, the installed file's hash or the resolved path failed.
       - The fetch, downloaded-file hash and resolved-path messages also say where the pin came from.
       - The installed-file message names `CI_SHFMT_SHA256` but not where the pin came from. It says the file changed between the digest check and the install, or the install wrote other bytes.
   - Its comments follow the pinned-git step's. They are the spec for the staged comment's rewrite (Dispatch 1's CI part):
     - They say the digest was computed locally by hashing the release's linux amd64 asset with `shasum -a 256`, and that it equals the attested release digest (row 40).
     - They state what each source proves for v3.14.0, one per item (row 40):
       - The release carries no checksum file asset.
       - Its GitHub release attestation verifies and lists the pinned digest. That shows the asset is the one the release published, and its root of trust is GitHub.
       - It carries no build-provenance attestation, so nothing ties the binary to a source build.
       - A Go checksum database match proves the tag's source, not the binary, so it is never a comparison for the asset's digest. A source build (row 38) would prove the tag's source, which the release attestation does not.
     - They say the binary's build is unproven, because nothing stronger held at the pin.
     - They say a bump runs `gh release verify` and `gh attestation verify` again, updates the `install.sh` message (Design item 6) beside this comment, and moves the floor too.
   - The version-report step at `tests.yml:205-211` adds `bash --version | head -n 1`, and its name and comment name bash. With the pin step's `shfmt --version`, a CI-only failure names both builds.
   - `test_shfmt_floor.py`, modeled on `test_git_floor.py`, checks these. PR 1a creates it with every check but the first, and PR 1b adds the first with the floor it reads:
     - The pin equals the floor in `_config.sh`.
     - Under `GITHUB_ACTIONS`, `command -v shfmt` is `/usr/local/bin/shfmt` and its `--version` matches the pin, which shows the step ran.
     - The pin step precedes every pytest step in each leg.
     - No workflow, job or step env sets `CI_SHFMT_INSTALL_DIR`.
     - The step body runs in the pattern of `TestPinStepRunBody` in `test_git_floor.py`, with `curl` and `sudo` stubbed and `install` wrapped by a stub that logs its call and the digest of the file it was handed, then runs the real `install`. The `curl` stub writes known bytes and logs its argv. The `sudo` stub logs nothing itself: it runs the `install` stub with `STUB_VIA_SUDO` set, so that stub's log line starts with `sudo`. The real `sha256sum` does both checks. The test skips locally when `sha256sum` is absent and fails under `GITHUB_ACTIONS`.
     - The stub `curl`'s argv log holds `--fail`, `--location`, `--silent` and `--show-error`, the bounding flags `--retry`, `--retry-max-time` and `--max-time`, each with a numeric value, and `--proto '=https'` and `--proto-redir '=https'`. The `--retry-max-time` value exceeds the `--max-time` value.
     - The step-body outcomes it checks are the ones Verification 6's "Install and CI" group lists.
     - The version fixture differs from the pin, and the logged URL contains it, so a version hard-coded in the step body fails, as `_FIXTURE_PACKAGE_VERSION` in `test_git_floor.py` does for git.
8. **Cursor adapter parity (PR 1b).** The adapter records shfmt, and its `check` command and sessionStart report run the same shfmt check as the SessionStart hook (rows 95-96).
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
     - From PR 1b, the three redaction gates deny every command that reaches their parse (row 20):
       - Every `git commit` inside a work tree, through `deny-pii-in-commits.sh`, and through `deny-private-project-refs.sh` too when the staged diff is non-empty.
       - `gh pr create` and `gh pr edit`, through `deny-private-project-refs.sh` and `deny-escaped-backticks-in-pr-body.sh`.
       - `gh issue create`, `gh issue comment` and `gh issue edit`, through `deny-private-project-refs.sh`.
       - A mutating `gh api` call, through `deny-private-project-refs.sh`.

       Read-only commands such as `gh pr view` and a GET `gh api` call never reach the parse.
     - From PR 1b, a machine without python3 denies the same commands, not only those xargs cannot split.
     - From PR 2, the worktree gate also denies every git command it parses. In a main-tree session with enforcement active, that is every git command, `git pull`, `git revert` and `git status` included, because the parse runs before the read-only allowlist that reads its records (row 51).
   - **What warns.** From PR 1b, the SessionStart check (Design item 11) names a missing, below-floor or failing shfmt at the next session start or resume. Under Cursor, the adapter's sessionStart report and `check` name the same causes (Design item 8).
     - The same check names a machine with neither `timeout` nor `gtimeout` on PATH. There a hung shfmt or python3 stalls each gated command for the harness's hook timeout, 600 seconds by default, and the harness's deny names no cause (row 111).
   - **Recovery.** The human installs shfmt in a separate terminal, re-runs `./install.sh`, and restarts Claude Code. A Cursor user also re-runs the adapter's `install` and relaunches Cursor.
   - **No fallback.** Nothing falls back to the old tokenizers (row 35).
   - **Text changes.** PR 1b makes three that carry the warning (row 49):
     - `README.md:134` widens from a change that raises the bash or Claude Code floor to any change that raises a floor or adds a required tool. A new `shfmt` bullet in § "Requirements" states the floor, the install routes, that the hooks which parse commands deny without it, and that `check-hook-dependencies.sh` warns at session start, as the Python bullet at :116 says for python3. It names no gate and cites the recovery entry, so PR 2 leaves `README.md` alone.
       - The bullet also gives the zsh note (row 106). The hooks parse commands as bash, so a zsh-only command denies, and a command zsh reads differently can be judged on words zsh never runs. It cites the decision file for the rest.
       - The `timeout` bullet at :115 gains one sentence (row 111): without `timeout` or `gtimeout`, a hung shfmt or python3 stalls each command a hook parses for the harness's 600-second hook timeout, and `check-hook-dependencies.sh` warns at session start.
     - The CHANGELOG entry follows `CHANGELOG.md:666-678`: a bold lead, behavior bullets, then a `**Migration:**` bullet.
       - Its behavior bullets, one fact each:
         - The zsh note, as the README bullet states it.
         - The cap-tool warning and the 600-second stall, as the README's `timeout` sentence states them.
         - A command the gates parse denies when it holds any carriage return, a CRLF line ending, one in quotes and one in a heredoc body included. Removing it, or moving the text that holds it to a file, is the way through. The bullet cites `docs/hooks.md` § "Gate deadlock recovery" and carries no plan row cite.
         - The gates no longer read some text the old tokenizer read, such as a heredoc fed to a shell. These shapes need a construction a cooperative agent does not write. The bullet cites `docs/design-decisions/tokenizing-gates-parse-with-shfmt.md`'s cut residual, which lists them, and carries no plan row cite and no figure.
       - Its migration note follows `CHANGELOG.md:673-678`: a "Before pulling" step, an "If you have already pulled" step, and the headless caveat `docs/hooks.md:560` gives for jq. It says "any `git commit`", not only one with staged changes, names the gated `gh` subcommands rather than whole command families, and names the session-start notice.
       - One more migration step: a Cursor user re-runs the adapter's `install` and relaunches Cursor, because PR 1b changes `RECORDED_TOOLS` and the entry timeout.
     - `docs/hooks.md` § "Gate deadlock recovery" replaces the python3 paragraph at :592, which covers only the splitter, with an entry for the parse path, described next.
   - **The recovery entry** is the one home of the parse path's diagnosis (row 77). The SessionStart notice, the Cursor report's shfmt finding and every parse-failure deny cite it. Its text carries no plan row cite, as the CHANGELOG bullets carry none, so the row cites in the items below are this plan's alone (staff-platform-engineer round 12 R7). Per status, it gives the diagnostic a human runs in a separate terminal, from the shell that launches Claude Code, and the fix:
     - 6, shfmt missing: `command -v shfmt`. Install shfmt at the floor, re-run `./install.sh`, and restart Claude Code.
     - 5, tree not recognized: `command -v shfmt`, `shfmt --version` and `printf 'echo a\n' | shfmt -ln bash --to-json`. Install the mvdan/sh release binary at the floor, because Homebrew installs only its current shfmt, or pull a claude-config fix. When that diagnostic passes, the failure depends on the command. Its rare causes, one per item, each with its way through:
       - An extglob pattern holding `$(`, a backtick, `<(` or `>(`, which the strict check also rejects: write the pattern without it (Design item 2).
       - An unquoted heredoc whose body holds a line-ending backslash continuation followed directly by an expansion: quote the heredoc delimiter, or keep an expansion, such as a dollar sign, a backtick substitution or a braced parameter, off the first character of the continued line (row 24, ciso-reviewer code-review round 7 R2).
       - An extglob holding only a continuation: remove the continuation (row 24).
     - 8, the parse step failed: the status-5 diagnostic followed by `echo $?`. A nonzero exit shows shfmt's own error, such as a shim with no version set or a wrong-architecture binary. Exit 0 there means the failure depends on the command, as when the session-start probe's valid command is rejected: install the mvdan/sh release binary at the floor, or pull a claude-config fix.
     - 3 on a command that is plainly valid bash: run the status-8 diagnostic. Its outcomes:
       - It shows shfmt failing: fix it as for 8. Exit 1 is not unique to a syntax error: a BusyBox `timeout` usage error also exits 1, so the cap wrapper or shfmt itself can be failing (row 59).
       - It passes, and the command is valid zsh but not bash. The hooks parse bash only, so rewrite the command in bash syntax (row 106).
       - It passes, and the command holds a carriage return, such as a CRLF line ending. Remove it, or move the text that holds it to a file. The hooks deny any command holding one, because shfmt reads it as a blank where bash does not (row 118).
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
   - PR 1b writes the first and third ways out. PR 2 adds the second, and names `git pull` and `git revert` in the first.
   - The rollback sentence, one fact per item:
     - PR 1b's wording, a revert of its one merge, holds until PR 2 changes it.
     - After PR 2, it says to revert PR 2 first and PR 1b second, because PR 2's worktree gate calls PR 1b's `_lib_shell_parse`.
     - After PR 2, it says the opt-out route is for when `git revert` itself is denied.
     - Reverting PR 1a is never needed for recovery, because no gate calls its module without PR 1b.
   - PR 2 adds a CHANGELOG entry with four facts:
     - Without shfmt, an enforced main-tree session can run no git command.
     - The evaluator's two behavior changes apply, the comment form and a `git diff` whose word a continuation splits (Design item 5).
     - A `cd` whose effect is uncertain leaves the cwd unresolved, so a later write denies, in a linked-worktree session too (row 85). These deny: `{ cd /wt && git push; }`, `if [ -d x ]; then cd x; fi; git commit`, `[ -d /wt ] && cd /wt; git push` and `pushd /wt && git push`. The way through is a plain `cd <worktree> && git ...`.
     - The worktree gate denies, and the evaluator gives no R5 credit to, a command holding a carriage return. The gate's deny names the carriage return, so the way through is to remove it from the command line.
10. **Records.**
    - PR 1b creates `docs/design-decisions/tokenizing-gates-parse-with-shfmt.md`. It follows the `bats-core-adoption-declined.md` precedent for a dependency decision, and scopes the decision to the three redaction gates. It records these:
      - The choice and the alternatives above.
      - The fail-closed posture and the accepted lockout.
      - `check-hook-dependencies.sh` as the one place that diagnoses the parse path's dependencies (rows 76-77, 94), and the shared shfmt check it and the Cursor report both call (row 96).
      - The strict check as the only guard against a re-encoded tree.
      - An accepted residual: the gates run whichever shfmt the hooks' PATH resolves, so a shim or an earlier PATH entry can substitute a build `install.sh` never approved. The strict check bounds the tree's shape, not its fidelity to the command. `docs/hooks.md:538` accepts the same exposure for python3.
      - Fidelity, one fact per item:
        - `_lib_shell_parse`'s carriage-return check covers a byte shfmt and bash read differently in every context (row 118).
        - The strict check's extglob condition denies a pattern holding `$(`, a backtick, `<(` or `>(`, because shfmt holds a pattern as text and the walker cannot reach a command inside it.
        - No other guard covers a text the two read differently. The cut residual below records the shapes left without one: those whose guards the engineer cut, and the flush-comment shape, which the engineer chose to record as a gap rather than guard (row 135).
        - The dropped-key limit, one fact per item (row 24):
          - The rule: the strict check cannot see a shfmt that stops writing any key a valid command can omit.
          - Examples, not a full list: `CaseItem.Stmts`, `CmdSubst.Stmts`, `ProcSubst.Stmts`, `Stmt.Cmd`, `CallExpr.Args`, `IfClause.Cond`, `IfClause.Else`, `TimeClause.Stmt`, `CaseClause.Items`, `DblQuoted.Parts` and `SglQuoted.Value`.
          - `SglQuoted.Value` holds no command, yet its drop loses a word: `git commit '-F' x` then projects `git`, `commit`, an empty word and `x` [verified: staff-backend-engineer plan-review round 19 R3].
          - In the redaction gates, a drop that empties part of a command leaves its other words, so a flag under the dropped key goes unread. A drop that empties the whole command leaves no words, which `_lib_command_words` denies with status 4.
          - In the worktree gate, from PR 2, a drop that empties the record list reads as "nothing to judge" and allows (`require-worktree-for-git-writes.sh:46-50`), on a gate whose tier lists `irreversible`.
          - Two checks narrow the window at the pinned build. The child-position matrix asserts a flag surfaces from each command-bearing child position it lists, and the real-bash comparison checks the words, so a drop under one of those positions fails CI (Verification 6).
          - The SessionStart probe compares the expected words of each construct it holds, so a drop under one of them names status 9 at the next session start (Design item 12).
          - For a key that holds no command, such as `SglQuoted.Value`, neither the child-position matrix nor the probe reaches it, because the probe holds no single-quoted word. The real-bash comparison may, through row 132's `-f body='a reply'` shape [unverified] (staff-backend-engineer plan-review round 20 R3).
          - The drift this limit exists for is a consumer's newer build, which CI does not run. What stays open is a drop in such a build under a construct the probe does not hold, or a shfmt that changes mid-session.
          - A `--from-json` round trip would see it and is named as a later option (Alternatives weighed).
          - The engineer accepted the limit for now, as the session's plain-words explanation stated it [engineer-verified: "Accept, revisit later (Recommended)"] (row 24).
          - The engineer accepted the worktree-gate consequence too [engineer-verified: "Yes, accept for it too (Recommended)"] (row 24).
          - For this class, the engineer chose that those later answers govern over row 76's rule that hooks never silently fail, which still applies everywhere else [engineer-verified: "Later answers govern (Recommended)"] (row 24).
          - The revisit condition is a shfmt release that changes its output.
          - That condition is the session's wording [unverified].
          - Nothing watches for such a release, because the drift job is cut (row 60). A pin bump's CI run sees only the release the pin lands on (Design item 7). A release the floor skips is a human's to watch.
          - The decision file gives the limit its own heading, holding every item above, the acceptances and the revisit condition included. Each gate's Known-gaps line cites that heading.
        - The empty-`Lit` over-deny, from the `Lit.Value` caveat, a separate limit beside the dropped-key one, one fact per item (row 24):
          - `ALWAYS_PRESENT_KEYS` lists `Lit.Value`, although shfmt omits it for an empty `Lit`.
          - So two valid shapes exit 5 and deny: an unquoted heredoc whose body holds a line-ending backslash continuation followed directly by an expansion, and an extglob that holds only a continuation, such as `echo @(\<LF>)` [verified: ciso-reviewer code-review round 6 R1; staff-backend-engineer code-review round 6 R1, plan-review round 21 R4].
          - The deny fails closed, so nothing hides.
          - The engineer's rule is to guard only shapes agents emit (row 135).
          - For the heredoc shape, a session scan run this session found no agent emitting it. Its pattern was a regex over agents' Bash tool inputs for an unquoted heredoc whose body has a backslash-newline directly before a `$` or a backtick [verified: session transcript scan, run this session].
          - The extglob shape was not scanned. It is accepted without a scan, because shfmt accepts an empty extglob only through a continuation and no agent writes extglob continuations [unverified].
          - Accepting the over-deny by shape is the session's decision, not an engineer answer [unverified].
          - Any closure of the over-deny must keep a missing `Value` on a non-empty `Lit` denying with exit 5. `Lit.Value` carries every literal word, so removing it from the table alone would let a shfmt that stops writing it hide every word with exit 0 (ciso-reviewer plan-review round 21 R1).
          - The module test `TestEmptyLitOverDeny` pins both shapes (Verification 6).
        - The real-bash comparison of Verification 6 establishes shfmt's fidelity on literal words at CI's pinned build only.
        - A later divergence in a shape a cooperative agent writes is a reconsideration trigger below.
      - A second accepted residual, the SessionStart check's working directory (row 101):
        - The check runs `shfmt --version` and the probe from the session's working directory at every startup and resume.
        - Under `claude -p`, the SDK, or a trusted parent folder, that directory can be a clone the user never reviewed.
        - The probe's stdin is a fixed string.
        - Whether a shfmt shim can select a repository-supplied binary is unconfirmed.
        - A repository or one agent `Write` can set a version-manager pin file that makes a shfmt shim fail, as `docs/security-hardening.md:346-351` records for python3. Every parsing gate then denies, and the check warns at the next start.
      - A third accepted residual, the zsh gap (rows 15, 106). The Bash tool can run zsh, and the gates parse bash only:
        - zsh-only syntax such as `${(f)x}` is invalid bash, so shfmt exits 1 and the gate denies with the status-3 wording.
        - A construct that parses as bash but means something else in zsh can yield words zsh never sees.
        - A per-shell dialect is a follow-up (Out of scope).
        - The miss is accepted on implementation scope, not under `docs/hooks.md`'s cooperative-agent waiver, because nothing shows that a cooperative agent never emits a shape bash and zsh read differently (row 114).
      - A fourth accepted residual, beside the zsh gap, the cut residual (rows 128-130). Its heading is the one each gate's Known-gaps line cites. Its member list below is the cut residual's one list, and other plan sites point to it. The decision file carries the list less the plan-row pointers in parentheses. One fact per item:
        - In each member below, shfmt's tree can show the gates a command other than the one bash runs, so a source flag or a git write bash runs can stay unread.
        - Each entry gives the shape, its trigger and the builds it was seen on. A member hides from the three redaction gates and the worktree gate unless its entry says otherwise. For the worktree gate a heredoc member pre-dates the change, because the base parser dropped every heredoc body. The pins' first run settles each entry on CI's shfmt (Verification 6).
        - The members, one class per item:
          - Delimiter mismatch. shfmt decides a heredoc delimiter's quoting from its last part, and keeps a backslash in a double-quoted delimiter where bash's quote removal drops it. Spellings whose last part decides as bash does agree, such as `EO"F"`, `EOF""`, `E\OF`, `\EOF`, `"EOF"` and `'EOF'`. Each member was seen on bash 5.3.20, and also on 3.2.57, which is below the repo's floor and recorded as an observation only (row 121, Out of scope):
            - A delimiter quoted in a part other than its last, such as `E"O"F`, `"E"OF`, `E'O'F`, `-E"O"F` or `""EOF`. bash keeps the body as written, and shfmt reads the body as unquoted.
            - A double-quoted delimiter holding a backslash, such as `"E\$F"`. The two end the heredoc at different lines.
            - An ANSI-C delimiter whose escape decodes to the terminator, such as `$'E\x4fF'` or `$'E\117F'`. bash decodes the escape and ends the heredoc at the `EOF` line, while shfmt keeps the escape text and reads on (ciso-reviewer code-review round 6 R2, plan-review round 21 R3).
            - A locale delimiter holding a backslash, such as `$"E\$F"`, the double-quoted member's spelling with a `$` prefix (the same reviews).
          - `$'EOF\n'` is not a member, because it hides nothing. Its decoded delimiter keeps the newline, so no line ends the heredoc in bash, and the lines after the opener stay body text. shfmt shows at most more than bash runs (ciso-reviewer plan-review round 21 R3; staff-sdet plan-review round 21 R4).
          - A heredoc inside a backtick substitution. bash binds a heredoc to the substitution its redirect sits in, and ends a backtick substitution by a raw-text scan at the next bare backtick, where shfmt ends it by its parse. The members, each under backticks (row 122):
            - A backtick substitution that closes on its heredoc's opener line, as in `` x=`: <<EOF` ``, on both builds.
            - A quoted delimiter that is itself a command line, as in `` x=`: <<'cmd'` `` then `cmd`, on both builds.
            - A backtick body holding a bare backtick, on both builds.
          - An extglob pattern holding bash 5.3's `${ cmd; }` or `${| cmd; }`, which the strict check's markers do not name. Only bash 5.3 has the form (row 125).
          - Standard input fed to a command interpreter, each seen on both builds (row 126):
            - A heredoc or a `<( )` fed directly to a shell, `source`, `.` or `eval`, such as `bash <<'EOF'`, `. /dev/stdin <<'EOF'` or `cat <<'EOF' | bash`.
            - A hand-off across statements, such as `exec 3<<'EOF'` then `bash <&3`, `exec <<'EOF'` then `bash`, a function that runs a shell, `read -r -d '' c <<'EOF'` then `eval "$c"`, or a script one statement writes and a later one runs.
            - An interpreter other than a shell that runs its input as commands, such as `make -f -`.
          - The backslash-newline hides (row 121):
            - A continuation that splits a heredoc terminator, closed by a later literal one.
            - A heredoc body whose first line is a lone backslash.
            - A comment ending in a backslash on a heredoc's opener line.
            - A quoted heredoc inside backticks whose terminator a continuation splits.
            - A single-quoted word a continuation splits inside backticks.
            - `$\<LF>(`, as in `"$\<LF>(…)"` or `${x:-$\<LF>(git push)}`.
            - `$\<LF>` before a quoted part of a flag, as in `git commit -$\<LF>'F' /dirty.md` or `-$\<LF>"F"`, seen on bash 5.3.20 and 3.2.57 (staff-sdet round 17 R2). The words show the flag as `-$F` while bash passes `-F`, so an exact-match flag test misses the flag name (ciso-reviewer code-review round 4 R4). BSD `xargs -n1` at the merge base splits the single-quoted spelling into `-$` and `F`, so the base never read `-F` either [verified: session ran BSD `xargs -n1` on it; GNU `xargs` not run]. Its reach in the worktree gate's records, as in `git -$\<LF>'C' /main push`, was not run [unverified].
            - A trailing comment ending in a backslash, as in `cd /x # c \<LF>git push`. shfmt reads the two lines as one command, so the redaction gates still see the next line's flag and path. It hides only from the worktree gate.
          - A flush `#`. shfmt reads a `#` that begins with no whitespace after the end of a word part, such as a quote, an expansion, an extglob pattern or an array literal's closing paren, as a comment, where bash keeps it in the word. In shfmt's tree the `Comment`'s `Hash` offset then equals the preceding node's end offset (row 135, ciso-reviewer code-review round 8 R1):
            - shfmt's comment takes the rest of the line, later commands and flags included, out of the tree. bash runs what follows.
            - The triggers below are examples of that mechanism, not a closed list. A newly found trigger of it is a member already, and needs only a fixture entry.
            - Seen hiding on bash 5.3.20: inside `( )`, `$( )`, `<( )` and backticks, and in a `case` arm, where the `)` of the pattern is enough. An example is `case x in a) git commit -m "x"# -F /dirty.md` with `;; esac` on a later line [verified: ciso-reviewer code-review round 5 R1, plan-review round 18 R2].
            - In an array literal, the hide reaches what the gates read only when a later element holds a substitution, as in `x=( "a"# $(…)` or `declare -a x=( "a"# $(…)`. The substitution then leaves the tree while bash runs it [verified: ciso-reviewer plan-review round 19 R3; staff-sdet plan-review round 20 R1].
            - An array literal of plain words, as in `x=( foo -m "x"# -F /dirty.md` or `declare -a x=( "x"# -F /dirty.md`, hides nothing the gates read. The module projects no words from an array's plain elements, or from a declaration's own words, with or without the `#`, and bash runs no command there [verified: staff-sdet plan-review round 19 R4, round 20 R1].
            - In a `case` arm, the hidden text can also hold a `cd` that bash runs in the parent shell, so a later visible command runs in a directory the tree does not show. Of the containers seen hiding, only the `case` arm runs its body in the parent shell. An example is `cd /w && case x in x) echo "a"#; cd /m` with `;; esac; git push` on a later line [verified: ciso-reviewer plan-review round 20 R1].
            - A same-line `;; esac` makes shfmt exit 1, so that form denies [verified: ciso-reviewer plan-review round 18 R2].
            - Seen agreeing with bash for a quote, expansion or extglob trigger: top level, `{ }`, `if`, `elif`, `while`, `until`, `select` and a brace function body [verified: the same R2; ciso-reviewer code-review round 8 R1]. Cases pin the top-level and `{ }` forms. The rest is a one-time observation no case pins.
            - A quote, `$x`, `${x}`, `$(…)`, a backtick substitution or `$((…))` before the `#` triggers it. `x#`, `"q"a#` and `"q"\#` do not [verified: ciso-reviewer code-review round 5 R1].
            - An extglob pattern's closing `)` triggers it too, for all five operators, in the same hiding containers. An example is a subshell holding `git commit -m @(a|b)# -F /dirty.md` with `)` on a later line, after `shopt -s extglob` on its own earlier line. Seen on bash 5.3.20 [verified: ciso-reviewer code-review round 8 R1].
            - The `)` that closes an array literal also triggers it, as in `x=(a)# ; git commit -F /dirty.md`. That trigger hides at top level and in `{ }`, `if`, `while` and function bodies too, so the agreement above does not hold after an array-literal closer. It covers the assignment, `+=`, empty-array and declaration-command forms, such as `declare -a x=(a)` and `local -a x=(a)`. Seen on bash 5.3.20 [verified: ciso-reviewer code-review round 7 R1].
            - For the subshell form, BSD `xargs -n1` at the merge base read the `-F` and the path the tree drops, so the cut is a deny-to-allow change there [verified: ciso-reviewer code-review round 5 R1; GNU `xargs` not run].
        - Every member needs a construction a cooperative agent does not write, so the gates' cooperative tier waives it (`docs/hooks.md:13`, `:55`, row 130).
        - Shapes that hide only under a bash below the 5.2 floor are not members, because the repo supports no such bash (`README.md` § "Requirements", `docs/hooks.md` § "Bash version", row 130).
        - Two joins differ from bash without hiding anything, so they are not members: `$\<LF>$` and `$\<LF>#`. The module keeps `$$` and `$#` as written while bash expands them, and the kept `$` makes the gates read each word as needing expansion, an over-deny. One words case pins them (Verification 6).
        - For the three redaction gates, the merge base read the hidden line of the continuation, substitution, extglob and shell members its reviews ran, through `xargs -n1`, so the cut is a regression (row 129).
        - `docs/hooks.md:26` makes a regression ADDRESS or stop-and-ask, never deferred.
        - The acceptance, one member group per item:
          - The five classes row 128 named:
            - The engineer's answer to that stop-and-ask named the cut by class, "the backslash-newline hides" among them, and is the acceptance for those classes (row 128).
            - With row 128's selection, the engineer accepted the risk of the counter-reading of `docs/hooks.md:47` for those classes: on an `irreversible` gate, the cut deliberately admits shapes that carry the gate's denied semantics, which that line says the tier blocks from being waived.
          - The `$\<LF>` quoted-part flag member:
            - It was found after row 128's answer.
            - The base never read the single-quoted spelling's `-F`, so the cut is no deny-to-allow change for that spelling on BSD `xargs` (row 129).
            - Its acceptance is the engineer's answer on it by name (PR 1a's session steps).
          - The flush-comment class:
            - It is no class row 128's answer named.
            - Its acceptance is the engineer's choice to record it as a gap rather than add a deny [engineer-verified: "Cut it, record as gap (Recommended)"], and to cut it for the worktree gate too [engineer-verified: "Cut it there too (Recommended)"] (row 135).
            - Those answers' questions did not state the `docs/hooks.md:47` counter-reading, so the plan claims no acceptance of it for that class.
        - For the worktree gate, whose old parser dropped every heredoc body, the heredoc classes pre-date the change. Its continuation members the base denied are regressions under the same acceptance.
        - Ordinary continuations, such as a multi-line `gh api` call, parse into the words bash sees, so the residual is the hides, not every backslash-newline (row 132).
        - Every member has a committed pin on shfmt's reading of it. No committed case runs a member under bash, so each member's bash side rests on the review runs its entry cites (Verification 6 and 7).
        - The file carries no count of how often agents write such commands.
      - A fifth accepted residual, a machine with neither `timeout` nor `gtimeout` on PATH (row 111):
        - A hung shfmt or python3 then stalls each command a gate parses for the harness's default hook timeout, 600 seconds (`docs/hooks.md:580`).
        - The deny that follows is the harness's, which names no cause.
        - `check-hook-dependencies.sh` names the missing cap tool at each session start.
      - A sixth accepted residual, memory on nested input (rows 115, 117):
        - A few KB of nested input can make shfmt emit about 100 MB of JSON (row 66), which python3 reads whole.
        - Only time is capped, and no byte bound limits the JSON.
        - The gate still denies the command.
        - The residual stands only if Verification 8's nested case peaks under that step's memory threshold. A peak over it puts a byte bound to the engineer instead.
      - A seventh accepted residual, brace-built flags (Out of scope):
        - The gates' words carry a brace word as written, not the words bash's brace expansion builds from it.
        - So the real-bash comparison, which leaves braces out, does not prove the words equal what bash passes.
      - An eighth accepted residual, the redaction gates' prefilter (row 123):
        - Each gate decides from the command's lines whether it is a command the gate parses (`deny-pii-in-commits.sh:268-299`, `_lib.sh:3086-3104`).
        - A continuation split of the gated command word or subcommand, such as `git \<LF>commit` or `gh \<LF>pr create`, leaves no line the prefilter matches, so the gate allows before its parse can deny.
        - A quote split does not, because each prefilter strips quotes before it matches (`deny-pii-in-commits.sh:292`, `_lib.sh:3092`).
        - The gap pre-dates the change.
        - The gates' tier lines omit `untrusted-input`, and the waiver rests on a cooperative agent not splitting a command word from its subcommand.
        - Closing it would take a raw-text check for a backslash-newline beside a gated word, ahead of each prefilter.
      - A ninth accepted residual, quoted text a builtin runs as shell (ciso-reviewer code-review round 5 R3):
        - A builtin or an option that evaluates a quoted string or a variable's value as shell runs a command that sits in a word no parser reads.
        - The family includes `bash -c` and `eval`, and also `let`, `printf -v`, `[[ -v ]]`, `declare -n`, `PS4` under `set -x`, `${x@P}`, `compgen -W` and `trap`, each seen on bash 5.3.20.
        - The base tokenizers did not read inside quotes either, so the gap pre-dates the change and no shape in it is a deny-to-allow change.
        - The gates' tier lines omit `untrusted-input`, and the waiver rests on a cooperative agent not putting a gated command inside such a string [unverified].
      - The reconsideration triggers, one per item, each a point at which the parser foundation is weighed again rather than given one more guard (staff-platform-engineer round 11 R8):
        - A divergence between shfmt's tree and bash, found after merge, on an axis no existing guard covers.
        - The vendor exposing a parsed form of the Bash command to hooks (Given 1).
        - A shfmt release that drops `--to-json` or re-encodes its output.
        - Evidence that cooperative agents write one of the cut residual's members.
    - PR 1b adds a scope note to `command-text-gates-accept-quoted-text-over-deny.md` under its provenance line, not a supersession. The note says the redaction gates parse with shfmt and the quote-stripping command-text gates it covers are unchanged.
    - PR 2 widens both files to the worktree gate and the evaluator. The note gains one sentence: its nested-git argument does not reach the worktree gate, because shlex already kept quoted text whole (row 9).
    - Each affected gate's header Known-gaps records its waived residuals in the PR that introduces them, as `docs/hooks.md:43` and `:55` require. Each record is one line citing its residual's heading in the decision file. A PR 1b test resolves that heading (Dispatch 5).
      - PR 1b: the zsh residual, the cut residual beside it with its flush-comment class named, the placeholder decoy (Out of scope), the prefilter's continuation split, the quoted-text residual and the dropped-key limit in `deny-pii-in-commits.sh`, `deny-private-project-refs.sh` and `deny-escaped-backticks-in-pr-body.sh`. The prefilter line lands in PR 1b, the PR that waives that pre-existing gap (row 123).
      - The cut-residual line is one line per header, one fact per item:
        - It names each class, the flush-comment class included, and cites the decision file's list, which holds the members. It lists no member, because that list is their one home.
        - It says every member needs a construction a cooperative agent does not write (row 130).
        - It names the regression part as one the engineer accepted, for row 128's five classes by that selection and for the flush-comment class by row 135's answer. A Known-gaps line cannot legalize a deny-to-allow change on its own (`docs/hooks.md:26`), and those answers are the acceptance (rows 128, 129, 135).
      - PR 2: the zsh residual, the cut residual with its flush-comment class named, the quoted-text residual and the dropped-key limit in `require-worktree-for-git-writes.sh` (Design item 4).
    - PR 1b's body carries the zsh and cut-residual acceptances (Critical files).
11. **The SessionStart check, `claude/.claude/hooks/check-hook-dependencies.sh` (PR 1b).** It is `check-python-floor.sh` renamed and extended to shfmt, so the hooks' dependencies have one SessionStart home (rows 79, 94). It names a broken dependency at the next session start or resume, before that session's first deny (rows 76-80). A session already running learns of it at its first deny (row 61).
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
      - Only tools that each answer just under their caps can add up past the 10-second timeout. The harness's cancel is then one of the silent cases below. Each gate still denies with its own reason.
      - With neither tool on PATH, every call runs uncapped (`_lib.sh:136-138`). A hung tool then stalls session start until the harness cancels the hook, the case `docs/hooks.md:549` documents for python3. The hook then prints nothing, the cap-tool line included.
    - A machine where python3 and shfmt both fail sees only the python3 notice until python3 is fixed. In the meantime each parse deny for a command that passes the cap and carriage-return checks names python3 too, because `_lib_shell_parse` checks python3 before shfmt (Design item 1, row 109).
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
    - PR 2 does not change it. The probe holds every type the child-position matrix lists as holding a command and every `KNOWN_BINARY_OPERATORS` entry, and a PR 1b test pins both (Design item 12).
12. **The shared shfmt check in `claude/.claude/hooks/_lib.sh` (PR 1b).** The SessionStart hook (Design item 11) and the Cursor adapter's report (Design item 8) both call it, so the shfmt check has one implementation (rows 80, 96).
    - `_lib_shell_parse_probe PARSE_CAP` runs `_lib_shell_parse` once on a fixed probe command with the `words` projection and PARSE_CAP as its cap, and compares the output with the expected words. It returns 0 on a match and `_LIB_SHELL_PARSE_PROBE_MISMATCH_STATUS` (9) on a mismatch. Otherwise it returns `_lib_shell_parse`'s status, with 3 turned into 8, because the probe is valid bash and holds no carriage return (row 59). Clause 8 covers every cause of that status (Design item 1), so the SessionStart notice never names a command-text cause (staff-sdet round 10 R8).
    - The probe command holds at least one of each of these:
      - A `git commit -F` with a literal path, and a `gh pr create --body-file "$F"`.
      - A command substitution, backticks and a process substitution, each holding a command, and a heredoc at the top level.
      - `&&`, `||`, `|`, `|&`, `;` and a backgrounded statement.
      - A subshell, `{ }`, `time` and `!`, each holding a `cd`.
      - `if` with `elif` and `else`, `while`, `until`, `for`, `select` and `case`, a function declaration, and a coprocess.
      - `[[ ]]`, `(( ))`, an assignment-prefixed `cd`, `builtin cd` and `pushd`.
    - Constraints on the probe, one per item:
      - The command and its expected words are literals beside the function, their one home.
      - The probe is parsed and never run.
      - It holds no carriage return and no extglob pattern with a substitution marker.
      - Its heredocs use the plain delimiter `EOF` and sit at the top level, so its expected words do not rest on a shape the cut residual names.
      - A test requires its parsed node types to include every type the child-position matrix lists as holding a command, and its operators every `KNOWN_BINARY_OPERATORS` entry (Verification 6).
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
      - A shfmt that changes after the session starts, through an upgrade or a PATH change. If it renames, retypes or adds a node or key, the next parse denies and names the cause.
      - A renamed, retyped or new node or key under a construct the probe does not hold. The strict check denies it at run time.
      - A dropped key a valid command can omit, under a construct the probe does not hold. Neither the probe nor the strict check sees it (Design item 10, row 24).
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
  "Alternatives weighed":
  - Patching the shlex pre-passes, which is a hand-rolled bash lexer.
  - Narrowing what the gates read, which leaves rows 17 and 19 open.
  - bash itself (row 13).

Row 13 [assumption]: canonicalizing a command through real bash runs its
  command substitutions inside the hook [verified:
  docs/security-hardening.md:844-848] — anchors: row12

Row 14 [assumption]: shfmt's project health, one fact per item:
  - It is BSD-3-Clause [unverified: research summary].
  - It released v3.14.1 on 2026-09-06, its seventh release in two years
    [unverified: research summary].
  - It has no published GitHub security advisory [unverified: research
    summary].
  - CVE databases are unchecked. Verification 9 checks OSV before PR 1a
    [unverified].
  — anchors: row12

Row 15 [assumption]: Claude Code's Bash tool runs bash or zsh. It runs the
  shell CLAUDE_CODE_SHELL names, or else one auto-detected from $SHELL,
  then the first working zsh, then bash [unverified: relayed by a research
  agent's report, a secondary source, from
  https://code.claude.com/docs/en/env-vars.md, the CLAUDE_CODE_SHELL row,
  and https://code.claude.com/docs/en/tools-reference.md, "Bash tool
  behavior". The session confirms both lines before Dispatch 5, which
  writes the zsh note into README.md and CHANGELOG.md].
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
  sets. Every key in its struct's ALWAYS_PRESENT_KEYS entry must be there.
  The projection's CallExpr count must equal a raw count. Otherwise the module
  exits 5 and the gate denies — anchors: root — under Given 2 a re-encoded
  tree must fail closed. Projecting it to no words would read as "no
  source file", and an empty record list reads as "nothing to judge" in
  the worktree gate (require-worktree-for-git-writes.sh:47-50). One fact
  per item:
  - The table's definition, its one home in this plan: a struct's
    ALWAYS_PRESENT_KEYS entry lists every key real shfmt writes on every
    instance of the struct, less the four exceptions below, and with the
    Lit.Value caveat below. "Listed" and "unlisted" mean table
    membership alone.
  - The four exceptions, which stay unlisted: CaseItem.Op,
    ForClause.DoPos, ForClause.DonePos and IfClause.FiPos. Each holds no
    command, and no check reads it.
  - Those four stay out by name, because listing them would add only a
    deny on shfmt drift that hides nothing. That choice is the
    architect's [unverified].
  - The Lit.Value caveat: Lit.Value is listed, although shfmt omits it
    for an empty Lit. It is the one such key found, not one proven
    alone [verified: ciso-reviewer code-review round 6 R1;
    staff-backend-engineer code-review round 6 R1, plan-review round 21
    R3].
  - So a valid command exits 5 when it holds an unquoted heredoc whose
    body has a line-ending backslash continuation followed directly by
    an expansion, or an extglob holding only a continuation, such as
    `echo @(\<LF>)` [verified: the same R1s; staff-sdet plan-review
    round 21 R1].
  - The over-deny, one fact per item:
    - The deny fails closed, an over-deny accepted by shape.
    - The engineer's rule is to guard only shapes agents emit (row 135).
      Design item 10 gives the scan behind the heredoc shape and why the
      extglob shape was accepted without one.
    - Accepting it is the session's decision, not an engineer answer
      [unverified].
    - Any closure of it must keep a missing Value on a non-empty Lit
      denying with exit 5 (ciso-reviewer plan-review round 21 R1).
    - Design item 10 records it, and TestEmptyLitOverDeny pins both
      shapes (Verification 6).
  - This row's earlier list left out five keys, ExtGlob.Pattern among
    them, and is reopened and corrected: the extglob condition reads
    ExtGlob.Pattern, so a tree without it would pass that condition with
    exit 0 [verified: ciso-reviewer plan-review round 18 R3;
    staff-backend-engineer plan-review round 18 R1].
  - The staged table left out seven keys that Dispatch 1 now lists: the
    six command-bearing body keys Block.Stmts, Subshell.Stmts,
    IfClause.Then, WhileClause.Cond, WhileClause.Do and ForClause.Do,
    and ExtGlob.Pattern. Unlisted, a shfmt that dropped a
    body key would hide the body's commands with exit 0 [verified:
    staff-sdet code-review round 5 R3; staff-backend-engineer code-review
    round 5 R1].
  - Real shfmt rejects the empty forms that make those seven keys
    non-omittable, each exiting 1 under the production argv, one form
    group per key [verified: staff-sdet code-review round 5 R3,
    plan-review round 18 R4; staff-backend-engineer plan-review round 18
    R5; each on a local build that prints no version]:
    - Block.Stmts: `{ }`, and `{ # c` then `}`.
    - Subshell.Stmts: `( )`, and `( # c` then `)`.
    - IfClause.Then: `if a; then ; fi`, `if a; then b; else ; fi`,
      `if a; then b; elif c; then ; fi`, and `if a; then # c` then `fi`.
    - WhileClause.Cond: `while ; do a; done` and `until ; do a; done`.
    - WhileClause.Do: `while a; do ; done`, `until a; do ; done`, and
      `while a; do # c` then `done`.
    - ForClause.Do: `for i; do done`, `select x in a; do done` and
      `for ((;;)); do done`.
    - ExtGlob.Pattern: `echo @()`, in argument position. The case pins
      its exit 1, not a cause: the local build reports a generic
      command-structure error, because an empty `@()` does not lex as an
      extglob [verified: staff-backend-engineer plan-review round 19 R6].
      The bare `@()` fails as a function declaration instead, so it shows
      nothing about the pattern.
    - No context on the local build yields an empty ExtGlob node, which
      supports the premise: `${x#@()}`, `${x//@()/b}` and `${x:-@()}`
      parse with no ExtGlob node [verified: the same R6].
  - A premise case pins each of those forms on CI's build
    (Verification 6).
  - No presence table closes the keys a valid command can omit, the
    limit Design item 10 states. CaseItem.Stmts, CmdSubst.Stmts and
    ProcSubst.Stmts are legitimately absent on valid input, as in
    `case x in a) ;; esac`, `echo $()` and `cat <()`. So a shfmt that
    drops one from a node holding commands is not detected [verified:
    staff-sdet code-review round 5 R3].
  - The same holds for other keys a valid command can omit, Stmt.Cmd,
    CallExpr.Args, IfClause.Cond, IfClause.Else, TimeClause.Stmt,
    CaseClause.Items and DblQuoted.Parts among them [verified:
    staff-backend-engineer code-review round 5 R1, plan-review round 18
    R2; ciso-reviewer plan-review round 18 R4]. Alternatives weighed
    names the round trip that would close it.
  - The engineer accepted the limit for now, as the session's
    explanation stated it [engineer-verified: "Accept, revisit later
    (Recommended)"]. The quote covers that limit and no wider claim.
  - That explanation, in the session's wording [unverified], one fact
    per item:
    - It said the strict check denies an unknown node type or key, and a
      missing key the list requires.
    - It said a future shfmt that stops writing a key that held
      commands makes those commands vanish, so the gate never sees them.
    - It named as examples a `case` branch's commands, the inside of
      `$( )` and `<( )`, a statement's command and a command's words,
      and said `echo $()` shows why no list can require them.
    - It gave the `--from-json` round trip and its cost as the other
      option, and recommended accepting for now.
    - It did not state the worktree gate's consequence, an empty record
      list read as nothing to judge and allowed.
  - The engineer then accepted that consequence too [engineer-verified:
    "Yes, accept for it too (Recommended)"], answering the session's
    question whether the first acceptance stands for the worktree gate,
    where an empty parser result reads as nothing to judge and allows.
    The quote covers the limit's acceptance for the worktree gate with
    that consequence. The question's explanation is the session's
    [unverified].
  - Both answers are in hand, so the plan carries no branch for a no.
  - Row 76 records "hooks should never silently fail.", and the limit is
    a silent miss by construction (staff-backend-engineer plan-review
    round 20 R1). The session asked whether, for the dropped-key class,
    the later acceptances govern over row 76's rule, which still applies
    everywhere else. The engineer answered [engineer-verified: "Later
    answers govern (Recommended)"]. The quote covers that choice alone,
    and row 76's quote stands unedited. The question's wording is the
    session's [unverified].
  - The PR bodies carry the three answers. PR 1b's body quotes "Accept,
    revisit later (Recommended)", because PR 1b is the first PR whose
    gates parse with shfmt. PR 2's body quotes "Yes, accept for it too
    (Recommended)". PR 1a's body quotes "Later answers govern
    (Recommended)" (Critical files).
  - SglQuoted.Value is a key of the same kind, one that loses a word and
    holds no command (Design item 10).
  - The revisit condition is a shfmt release that changes its output.
  - That condition and the option descriptions are the session's wording
    [unverified].
  - The seven added keys are the session's decision after code-review
    round 5 and plan-review round 18, which no engineer answer covers
    [unverified]. They only add a deny on shfmt drift.
  - The strict check holds no condition for a `#` shfmt reads as a
    comment where bash reads it as part of a word. Design item 10's cut
    residual records that shape (row 135).

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
    always omitted, except Lit.Value, which shfmt omits for an empty Lit
    (row 24's Lit.Value caveat). That fixes the keys present on every
    instance of each struct, which the smallest input and the conformance
    corpus confirm, the source row 24 defines the table from.
  - The dump shows which objects carry a `Type` key, and so which untyped
    objects the strict check matches by the field that holds them.
  - An unterminated heredoc makes shfmt exit 1 with no JSON, as an
    unbalanced quote does (row 32).
  - A plan reviewer saw an empty command yield a `File` that carries
    `Type` alone, with no `Pos`, `End` or `Stmts`, on the row 7 build.
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
  (row 24) holds every build at run time to the known node types, the
  known keys and the listed always-present keys. A drop of a key a valid
  command can omit is the limit Design item 10 states. Set aside:
  - An install-time shape probe, which repeated what row 24 checks on
    every call and needed install.sh to source the hooks' _lib.sh in a
    child bash.
  - Exiting 1 on an unreadable version, which rejects a working build
    (row 34).

Row 34 [assumption]: a MacPorts build of shfmt 3.14.1 prints an empty line
  for `--version` [verified: spike] — anchors: row33

Row 35 [mechanism]: a missing shfmt denies with a stop-and-ask reason, and
  nothing falls back to the old tokenizers — anchors: row6 — a fallback
  keeps both tokenizers and their tests alive with no point at which to
  remove them.

Row 36 [mechanism]: the self-review evaluator runs shfmt itself through
  subprocess and reuses the git-records projection — anchors: row37,
  row52. Lighter primitives set aside:
  - Keeping shlex build_records for the evaluator alone, which keeps the
    retired tokenizer alive for one caller.
  - Dropping its git-diff detection, which drops R5's Bash arm.

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
  Alternatives set aside, one per item:
  - apt's build, a lighter primitive, which is below the floor.
  - `go install` at the floor tag, which is heavier than the download,
    not lighter. That judgment is the architect's [unverified], one
    reason per item:
    - It needs a Go toolchain on the runner and a compile in each leg.
    - It makes proxy.golang.org and sum.golang.org network dependencies
      of the required check.
    - The digest freezes shfmt to one artifact.
    A rebuttal, not a reason: the route's checksum-database match proves
    the tag's source, which neither the digest nor the release
    attestation does (row 40). That source proof does not raise the
    required check's trust level, because CI installs pytest and the
    other dev packages from PyPI by floating specifier with no hashes
    [verified: requirements-dev.txt:1-5; tests.yml:119].
    Whether the runner's Go toolchain meets shfmt's go.mod go line, or
    fetches one as go.dev/doc/toolchain describes, is [unverified]. No
    reason above rests on it.
  - A third-party setup action, which adds one more action to trust for
    a three-line download.

Row 39 [assumption]: CI's tool provisioning at the merge base, one fact
  per item:
  - It runs only on ubuntu-24.04 [verified: .github/workflows/tests.yml:28,
    and :238 at the merge base].
  - It installs stow and direnv from apt [verified: tests.yml:131-132].
  - It pins git and zsh by apt version [verified: tests.yml:149-157,
    :184-189].
  - No step downloads a binary [verified: tests.yml holds no curl, wget or
    download step].
  — anchors: row38

Row 40 [assumption]: the v3.14.0 release's assets and attestations, one
  fact per item. The session was to confirm each before Dispatch 1's CI
  part, so before PR 1a opens (row 131), and each was [unverified] until
  then. Each negative holds for v3.14.0, and a later release can change
  it:
  - It publishes eight binaries, among them a linux amd64 asset whose
    name derives from the version [verified: the session's read of the
    release's asset list through the GitHub API].
  - It publishes no checksum file asset. This row first expected one
    [unverified], and the asset-list read settled it [verified: that
    read].
  - It carries a GitHub release attestation that binds the eight asset
    digests to the tag's commit. The linux amd64 digest it lists equals
    the pin literal [verified: session ran `gh release verify v3.14.0 -R
    mvdan/sh`, exit 0, "Release v3.14.0 verified!"].
  - This row once said no attestation existed, from the asset-list read
    alone, which cannot see one (ciso-reviewer and
    staff-platform-engineer round 17 R1).
  - It carries no build-provenance attestation for the linux amd64 asset
    [verified: session ran `gh attestation verify
    shfmt_v3.14.0_linux_amd64 -R mvdan/sh`, exit 1, HTTP 404 from the
    SLSA build-provenance lookup].
  - The session's own hash of the linux amd64 asset equals GitHub's
    server-side digest for it [verified: the session's hash and the
    asset-list read].
  - The official binary prints its version for `--version` [unverified].
  What each source proves, and the fallback:
  - GitHub's server-side digest proves only that the asset did not
    change after upload, because GitHub hosts both.
  - The release attestation shows the pinned digest is the one the
    release published for the tag's commit. It comes from GitHub, so the
    root of trust is still GitHub.
  - With no build-provenance attestation, nothing ties the binary to a
    source build.
  - The Go checksum database records module source hashes, not release
    asset digests, so it proves the tag's source and is never compared
    with the asset's digest. A source build, row 38's `go install`
    route, would prove the tag's source, which the release attestation
    does not.
  - So the step comment says the pin carries the attested release digest
    and that the binary's build is unproven (Design item 7).
  - PR 1a's body raises that build-provenance limit, naming row 38's
    `go install` route and its cost, so the engineer's acceptance covers
    the route by name.
  Who took the digest, one fact per item:
  - The session took it. The engineer authorized that
    [engineer-verified: "Yes you can do it"], answering the session's
    question whether the session could hash the asset. The question's
    wording is the session's [unverified].
  - The session fetched the linux amd64 asset with curl into a fresh
    empty directory, never ran it, and hashed it with `shasum -a 256`.
    No summarizing fetch tool touched the bytes. The asset's URL is
    recorded beside the digest.
  - The engineer did not hash it in a separate terminal.
  - That a separate re-hash by the engineer is optional, not a
    precondition of the pin, is the session's decision [unverified].
  - Its reasons: PR 1a's first CI run fetches the asset independently,
    from another network, and compares it with the same literal. The
    digest also equals the attested release digest.
  - The step before PR 1a's first push puts that waiver to the engineer
    by name. PR 1a's body records the answer and whether a re-hash ran.
  - The quote above authorizes the session to hash the asset, and
    nothing more.
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
  SUPERSEDED in shape by row 131: the engineer later split the first PR,
  so the plan ships as three PRs. This row's quote stays as the record of
  the earlier answer, and the split by tokenizer still holds between PR 1b
  and PR 2. Neither answer stated a size. Row 134 records the answer to
  the question that did, which kept the three PRs with no further split.

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
  the module recognizes or pulls a fix. From PR 1b, the SessionStart probe
  (row 80) names the failure at the next session start when the
  re-encoding touches a construct the probe holds. A session already
  running learns of it at its first deny [unverified: follows from Given
  2, row 24 and row 80]. Re-encoding here means a renamed, retyped or new
  node or key. A release that drops a key a valid command can omit makes no
  deny, the limit Design item 10 states (row 24) — anchors: row60

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

Row 67 [assumption]: on the local shfmt build probed, which prints no
  version, a session directory's `.editorconfig` did not change the
  dialect or the tree the gates read, because that build consulted one
  only when given `--filename`. _LIB_SHFMT_ARGV passes no `--filename`
  [verified: claude/.claude/hooks/_lib.sh:2531]. One fact per item:
  - On that build, a working-directory `.editorconfig` left the stdin
    tree unchanged under the production argv. It changed the tree only
    with `--filename` and no `-ln bash` [verified: the session's probe,
    staff-sdet code-review round 4 R9, ciso-reviewer code-review round 4
    R2].
  - CI's 3.14.0 build behaves the same [unverified until the contract
    file's `.editorconfig` case first runs on CI].
  - The row's earlier premise was that any parser flag makes shfmt
    ignore the file. It held only with `--filename`, where `-ln bash`
    kept the tree identical [verified: ciso-reviewer code-review round 4
    R2].
  - The contract file keeps one `.editorconfig` case, the tripwire for a
    shfmt that begins reading the file for stdin. The argv-equality test
    names no `.editorconfig` consequence, as two reviewers found
    (staff-sdet round 17 R1, staff-platform-engineer round 17 R3).
    Verification 6 gives the case.
  — anchors: row12

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

Row 72 [assumption]: each of the three PRs projects 400 or more changed
  lines [unverified: the architect's bottom-up estimate in Critical
  files' `Projected diff:` line, the figures' one home]. The engineer's
  plan-time answers on how to split are rows 46 and 131, neither of
  which answered a question that stated a size (staff-platform-engineer
  round 14 R1). The 400-line question, which stated the three sizes, is
  row 134's. PR 1a's commit-time size prompt cites row 134, and PR 1b's
  and PR 2's each ask on their own branch — anchors: row46, row131

Row 73 [assumption]: which PR goes first and what each carries is the
  session's proposal, backed by an architect consult, in the session's
  wording rather than the engineer's [unverified]. PR 1 carries the
  redaction gates, the shared parse path, the install check, CI's pinned
  build, the Cursor adapter's PATH and the shared docs. PR 2 carries the
  git-records projection, the worktree gate, the evaluator, SHFMT_ARGV and
  the deletion of parse-git-command.py. Row 131 later split PR 1 into
  PR 1a and PR 1b — anchors: row46

Row 74 [assumption]: the strict check keeps its per-type key sets, its
  unknown-key rejection and its CallExpr conservation count as Design item
  2 states them [engineer-verified: "Keep key sets (Recommended)"]
  — anchors: row24

Row 75 [mechanism]: PR 1b carries every change that makes shfmt a
  requirement for a consumer: the install check, the SessionStart check,
  and the Cursor adapter's PATH and shfmt check (row 95). CI's pinned
  build lands earlier, in PR 1a, because PR 1a's module tests fail under
  GITHUB_ACTIONS without shfmt (row 68) — anchors: row48, row73,
  row131 — PR 1b's gates are the first to call shfmt, and they go live
  on `git pull` (row 48), so a consumer must be able to install, resolve
  and diagnose shfmt from that PR on. PR 1a's module has no caller, so
  it needs none of these. PR 2 carries all git-records code, so the moved
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
    its 3.14.0 floor, and lands in PR 1b. Row 94 makes it one hook.
  - Each gate's deny keeps naming its cause. The dependency diagnosis
    lives in the SessionStart notice and the one recovery entry, not in
    each gate's comments or header.
  - The self-review evaluator keeps its credit-on-fault path.
  - For the dropped-key class, the engineer's later acceptances govern
    over row 76, which still applies everywhere else (row 24).
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
  once at install. Lighter primitives set aside:
  - `command -v shfmt` alone, which sees only absence.
  - The version compare alone, which misses a build with no version and a
    re-encoding at or above the floor.

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
  from deny to allow against the old parser, apart from the cut
  residual's continuation hides, which row 129 accepts. Set aside:
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
  them. Landing them in PR 1b follows row 75 — anchors: row42

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
  the likelier cause, and moving content to a file cannot fix it. The
  likelihood is not a bound. On the one machine row 31 measured, a flat
  command at the byte cap took about 2.35 s. python3 shares the same cap
  (Design item 1), so a loaded machine can push a near-cap command past
  it. The recovery entry's cap-kill item covers that case (Design item
  9). Status 7 keeps the workaround, because content moved to a file
  brings the command under the byte cap.

Row 103 [mechanism]: _lib_shell_parse_failure_clause returns the cause
  only, and each caller adds its own tail — anchors: row77, row79, row96
  — the deny reasons add the tail _lib_shell_parse_deny_tail prints, the
  tool-fault sentence or the file workaround (Design item 1), and the
  SessionStart notice and the Cursor report add their own
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
  `-ln bash`, and record these as an accepted residual in the decision
  file, the README's Requirements note and the CHANGELOG, one item each:
  - zsh-only syntax denies with the status-3 wording.
  - A construct bash and zsh read differently can yield words zsh never
    sees.
  - CLAUDE_CODE_SHELL set to a bash path forces bash. The plan dropped
    this item and no longer records it. The session dropped it when the
    shapes that hide only under a below-floor bash left the cut residual
    (row 130). One fact per item:
    - The plan adds no README guidance on CLAUDE_CODE_SHELL
      [engineer-verified: "Keep it dropped (Recommended)"], answering
      the session's question whether to keep that README sentence
      dropped or restore it. The question's wording and the option
      descriptions are the session's [unverified].
    - The decision file, the CHANGELOG and the recovery entry's status-3
      item (Design item 9) drop it too. That extension is the session's,
      because the question named the README sentence alone [unverified].
    - The architect recommended the drop because the claim that
      CLAUDE_CODE_SHELL forces bash rests on row 15's secondary source
      [unverified].
  - A per-shell dialect is a follow-up.
  — anchors: row15

Row 107 [assumption]: PR 2 does not wait for PR 1 to gain field time
  [engineer-verified: "Don't wait (Recommended)"], answering the
  session's question whether PR 2 should wait for field time. What that
  option proposed is the session's, restated here in the plan's words
  [unverified]: PR 2 branches from the default tip once the PR before it
  merges, rather than after a period of that PR in use. Since row 131's
  split, that PR is PR 1b, as "Three PRs" sequences it — anchors: row46

Row 108 [mechanism]: a differential table compares today's
  _lib_command_words with the new `words` projection before Dispatch 2
  changes any gate test's expectation, and the session puts every row
  whose gate verdict or extracted path strings change to the engineer
  — anchors: row18, row56, row113 — the full descent (row 56) emits the
  words of a command nested in a quoted `$(...)` or in an unquoted
  heredoc's backticks, so a source flag inside them now reaches the
  extractors and can deny. Dropping the fast path (row 18) changes
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
  gate and the notice name the same tool on a machine missing both, for
  a command that passes the cap and carriage-return checks. A command
  that fails one gets status 7 or 3 from a redaction gate and the python3
  deny from the worktree gate, by Design item 1's order rule.

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

Row 113 [assumption]: a non-UTF-8 byte in a command never reaches a gate's
  words, one fact per item:
  - shfmt exits 1 on a non-UTF-8 byte anywhere in the command, a word, a
    comment or a heredoc body included, and prints no tree [verified:
    Dispatch 1's real-shfmt run, pinned by
    test_non_utf8_byte_anywhere_in_the_command_makes_shfmt_reject_it_with_exit_1
    in test_shell_syntax_tree_words.py].
  - That contradicts this row's earlier form, which expected shfmt to keep
    the byte or write U+FFFD in its place. The engineer accepted Dispatch
    1's outcome [engineer-verified: "I'd say accept and re-review."],
    answering the session's question on that contradiction.
  - _lib_shell_parse turns that exit 1 into status 3, so a command passed
    straight to it with such a byte, as a test does, denies with the
    status-3 clause and the file workaround (Design item 1).
  - jq writes U+FFFD in place of an invalid UTF-8 byte in its input
    [verified: jq run this session].
  - The gates take the command from their payload through `_lib_jq -r`
    [verified: _lib.sh:533, in this worktree and in the main checkout].
  - So through a gate the byte arrives as U+FFFD, valid UTF-8, which the
    module carries as its three bytes [unverified: Verification 6 pins it].
  - The base commit's gates read the command the same way, so no gate's
    verdict on such a byte changes.
  - The CHANGELOG therefore says nothing of it.
  - The splitter's round-trip of a raw byte
    (test_split_command_words.py:228-231 at the base commit) ran only on
    direct calls.
  — anchors: row26, row108

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
  PR 1a's body records (Verification 8), with a byte bound decided only if that number is
  large. The case, its commands and the threshold that counts as large
  are the session's too, in Verification 8 — anchors: row66

Row 118 [mechanism]: _lib_shell_parse returns 3 for any command holding a
  carriage return, matched as a byte under LC_ALL=C [engineer-verified:
  "Add the CR check (Recommended)"], answering the session's question how
  to handle shfmt's reading of a carriage return. What that option
  proposed is the session's, restated here in the plan's words
  [unverified]: the check as this row's first sentence states it. One
  fact per item:
  - shfmt reads a lone carriage return as a blank, so in
    `echo x<CR># --flag /dirty.md` the flag and path are a Comment's text
    [verified: shfmt run this session].
  - bash reads a carriage return as an ordinary word character, so it
    passes `x<CR>#`, `--flag` and `/dirty.md` to echo [unverified: the Bash
    Reference Manual's metacharacter list, not reread this session;
    Dispatch 1 settles it against real bash, and Verification 6 pins it].
  - Without the check, the words projection drops a flag and path bash
    passes on, a miss.
  - The check runs after the byte cap and before the tool checks, by
    Design item 1's order rule: both input checks depend on the command
    alone.
  - Status 3 fits, because the command, not a tool, is the cause.
  - The file workaround reaches the redaction gates only, because only
    their deny reason composes it (Design item 1).
  - The worktree gate's status-3 deny is the clause alone, with no file
    workaround (Design items 1 and 4).
  - The clause names the carriage return, so the agent can fix the
    command line.
  - The evaluator runs shfmt without _lib_shell_parse, so its closure
    returns no records for such a command itself, as for shfmt's exit 1
    (Design item 5).
  - Outside bash's syntax set, no single character but the carriage
    return makes shfmt and bash disagree on a word, comment or statement
    boundary [verified: sweeps by two reviewers this round, shfmt build
    without a printed version, bash 3.2.57 and 5.3.20].
  - The claim covers single characters only. A sequence can disagree: a
    backslash-newline does in some placements (row 121), which the cut
    residual records (row 128).
  - That fidelity is established at CI's pinned shfmt only, by
    Verification 6's real-bash comparison, which Dispatch 1 adds.
  - A later divergence in a shape a cooperative agent writes widens the
    guard that can see it, through a plan revision. A byte the two read
    differently in every context widens this text check, in
    _lib_shell_parse and the evaluator's closure alike. A shape that
    depends on context widens the strict check.
  Set aside:
  - Removing or replacing the carriage return before shfmt runs, which
    judges a command other than the one bash runs.
  - Checking Comment positions against the raw command after the parse,
    which catches the comment shape only, while a carriage return
    elsewhere still splits a word bash keeps whole.
  - A status of its own, which adds a clause, a tail and a recovery item
    to say what status 3 already says.
  — anchors: row7, row12

Row 119 [mechanism]: Dispatch 1 also creates
  `claude/.claude/hooks/tests/_shell_syntax_tree_runners.py` and
  `claude/.claude/tests/test_stub_shfmt.py`
  [engineer-verified: "Add both (Recommended)"], answering the session's
  question whether to add both files to the file list. Why the session
  proposed them, in the session's words [unverified]: the runners file
  holds helpers the two new test files share, and the second file tests
  the stub-shfmt writer that every stub test in both PRs uses — anchors:
  row108

Row 120 [mechanism]: PR 2's evaluator returns no records for a command
  holding a carriage return (Design item 5), and the CHANGELOG carries a
  carriage-return bullet (Design item 9)
  [engineer-verified: "Keep both (Recommended)"], answering the session's
  question whether to keep those two consequences of row 118 — anchors:
  row118

Row 121 [mechanism]: SUPERSEDED by row 128, and kept, trimmed to what
  live text cites, as the evidence for the cut residual's
  backslash-newline and delimiter classes. The engineer's answers
  recorded below, "sure, close the hole", "I agree.",
  "Unconditional (Recommended)" and
  "Accept the over-deny (Recommended)", gave way to
  "Yes, cut them (Recommended)" for these shapes. Nothing below is delivered: no status 11, no byte test, no
  delimiter check. The row as it stood:
  _lib_shell_parse returns status 11 for any command
  holding a backslash immediately before a newline, before python3 or
  shfmt runs, and PR 2's evaluator closure returns no records for one
  (Design items 1 and 5). The module's delimiter check exits 3, so the
  command denies with status 3, for a heredoc delimiter outside four
  shapes, on every command (Design item 2). The class, commands whose
  backslash-newline or delimiter shfmt's tree may read differently from
  bash, is closed, not accepted
  [engineer-verified: "sure, close the hole"], answering the session's
  question whether to close or accept it. It superseded the engineer's
  earlier "Accept as a residual". One fact per item:
  - The blanket deny [engineer-verified: "I agree."] answers the
    session's proposal to deny any command holding a backslash-newline.
    The question's exact wording and the option's description are the
    session's [unverified].
  - The proposal followed review rounds 6 to 9, each of which found a
    further place where shfmt's tree differs from bash's reading of a
    backslash-newline. Round 9 found a comment ending in a backslash on
    a heredoc opener line, and a quoted heredoc or a single-quoted word
    inside backticks [verified: ciso-reviewer round 9 R1 and R2,
    staff-sdet round 9 R1, a shfmt build that prints no version and
    bash 5.3.20].
  - shfmt reads `cd /x # c \<LF>git push` as one command, `cd /x git
    push` [verified: ciso-reviewer round 9 R2].
  - The earlier answer on the worktree gate was "Yes, extend it
    (Recommended)" [engineer-verified: "Yes, extend it (Recommended)"],
    answering whether the class's acceptance extends to
    require-worktree-for-git-writes.sh. Row 128's cut covers that gate
    too (Design item 4).
  - Design item 4's two continuation-split Known-gaps lines no longer
    rest on the "Yes, extend it (Recommended)" relay, and stand on their
    own, one reason per item:
    - Each records a gap the merge base already has: the `git` prefilter
      at require-worktree-for-git-writes.sh:223 (row 105) and the fast
      path at :273-276 (ciso-reviewer round 7 R3, below). Neither is a
      regression under docs/hooks.md:26.
    - docs/hooks.md:20, as row 129 reads it, records with no blocking
      stop-and-ask a later-found gap that needs a shape a cooperative
      agent would never emit.
    - A continuation split of `git`, `cd` or `-C` is such a shape
      [unverified: Design item 4 states it for `cd` and `-C` alone].
  - The delimiter rule runs on every command, not only a continued one
    [engineer-verified: "Unconditional (Recommended)"], answering the
    session's question whether it applies always or only with a
    backslash-newline [unverified: the question's wording, as the session
    relayed it].
  - A delimiter can hide a line with no continuation. shfmt keeps a
    backslash in a double-quoted delimiter's text where bash's quote
    removal drops it, so `<<"E\$F"` ends at a different line in each
    [verified: staff-sdet round 10's answers, a shfmt build that prints
    no version, bash 5.3.20 and 3.2.57].
  - shfmt decides a heredoc delimiter's quoting from its last part
    [verified: staff-sdet round 8 R1, both bash builds]. `E"O"F`, `"E"OF`,
    `E'O'F`, `-E"O"F` and `""EOF` are quoted for bash and unquoted for
    shfmt. `EO"F"`, `EOF""`, `E\OF`, `\EOF`, `"EOF"` and `'EOF'` agree.
  - With no continuation in the text, that mismatch makes shfmt expand a
    body bash keeps as written, so the tree can show a command bash
    never runs [verified: staff-sdet round 10's answers, the same builds].
  - The delimiter rule therefore passes four shapes only.
  - No delimiter a cooperative agent writes falls outside those four
    shapes [unverified: the conformance corpus and the realistic smoke
    set run through project_checked].
  - The worktree gate's prefilter and fast path read the raw text first,
    so `gi\<LF>t push` and, with the lock held, `c\<LF>d /main && git
    push` skip the parse, as their quote-split forms do [verified:
    ciso-reviewer round 7 R3; require-worktree-for-git-writes.sh:223,
    :273-276].
  - The merge base has the same two regexes, so that gap pre-dates the
    change. Design item 4 records it in Known gaps.
  - The merge base denied part of the class, so the cut regresses it
    (row 129):
    - The base `xargs -n1` fast path read `-F /p.md` on a line after a
      split heredoc terminator [verified: CISO review round 6 R1, run
      under BSD xargs against base _lib.sh:2564-2575 and :2661-2666; GNU
      xargs not run].
    - The base source-path extractor captured the path, so the base
      scanned the file [verified: the same R1]. Base caught it only when
      xargs exits 0.
    - The base fast path also read `-F /p.md` after a lone-backslash body
      line [verified: ciso-reviewer round 8 R1, BSD xargs].
    - Base parse-git-command.py ended that heredoc at the raw terminator
      [verified: the same round 8 R1].
    - Behind a comment ending in a backslash on a quoted heredoc's opener
      line, base xargs yields `-F` and `/dirty.md`, and base
      strip_heredocs ends the heredoc at the raw terminator [verified:
      ciso-reviewer round 9 R1, BSD xargs, parse-git-command.py:126-132].
    - Base parse-git-command.py reads `echo ${x:-$\<LF>(git push)}` as an
      in-group git write, which the consumer denies
      (require-worktree-for-git-writes.sh:395) [verified: ciso-reviewer
      round 8 R1 run].
    - shfmt reads each hidden line as heredoc body or drops the command,
      so PR 1b, without the cut test, does not scan the file [verified:
      CISO review round 6 R1, citing round 3's shfmt run; ciso-reviewer
      round 8 R1 and round 9 R1].
    - docs/hooks.md:26 makes each a regression, which a Known-gaps line
      in the same change cannot legalize [verified: docs/hooks.md:26].
      Row 128's selection is the engineer's answer to that stop-and-ask
      (row 129).
  - The answers on the enumerated rules rounds 6 to 9 carried before the
    blanket rule, the `$` rule and the unquoted-heredoc rule, one per
    item. Each question's wording is the session's [unverified]:
    - [engineer-verified: "Approve the fallback (Recommended)"]: the
      heredoc rule as the fallback for the heredoc half.
    - [engineer-verified: "Accept the over-deny (Recommended)"]: its
      over-deny on a multi-line `gh pr create` whose body holds an
      unquoted heredoc, a shape the blanket rule would have denied too.
    - [engineer-verified: "Deny it (Recommended)"]: the `$` rule
      extended to a quote after the continuation.
    - [engineer-verified: "Conservative deny (Recommended)"]: a heredoc
      rule reading continuation evidence in the tree, which gave way when
      both its premises failed on shfmt 3.14.1.
  — anchors: row12, row118

Row 122 [mechanism]: SUPERSEDED by row 128, and kept, trimmed to what
  live text cites, as the evidence for the cut residual's
  heredoc-in-a-substitution class. The engineer's
  answer recorded below, "Add the span check (Recommended)", and the
  placement rule that replaced it both gave way to "Yes, cut them
  (Recommended)". Nothing below is delivered: no placement check, no
  placement or route sentence, no deny-text rewords, no flipped guard
  tests. The row as it stood:
  the module's placement check exits 3, so the
  command denies with status 3, for any heredoc whose redirect sits
  inside a command or process substitution, `$( )`, backticks, `<( )`
  and `>( )` alike, whether or not shfmt gives the redirect an Hdoc, on
  every command (Design item 2). The rule is the session's decision
  [unverified]. It supersedes the span check this row carried, which
  the engineer chose [engineer-verified: "Add the span check
  (Recommended)"], after ciso-reviewer round 11 found further members
  of the same axis that passed the span check. At that round the
  engineer gave a process directive, not an answer to this question,
  which the session paraphrases [unverified: the session's paraphrase]:
  judge whether to deny a shape from how agents actually write
  commands, rather than ask the engineer. Row 130 answers it. One fact
  per item:
  - bash binds a heredoc to the substitution its redirect sits in, and
    ends some substitutions by scanning raw text rather than by its
    parse: a backtick substitution at the next bare backtick, and on
    bash 3.2.57 a `$( )` or `<( )` at a `)`, heredoc bodies included
    [verified: ciso-reviewer round 10 R1 and round 11 R2 and R3, a shfmt
    build that prints no version, bash 5.3.20 and 3.2.57].
  - shfmt's tree shows the substitution ending where its own parse ends
    it. Where bash's scan ends it earlier, the tree holds as heredoc
    body the lines bash runs as commands, and no CallExpr carries them
    [verified: the same reviews].
  - The axis's members found so far, one per item [verified: the same
    reviews]:
    - A substitution that closes on the opener line, as in the three
      lines x=`: <<EOF`, a marker and EOF. bash gives the heredoc an
      empty body and runs line 2, on both builds under backticks, and
      under `$( )` and `<( )` on 3.2.57 but not 5.3.20 (round 10 R1).
    - The same with an empty body and a quoted delimiter that is itself
      a command line, as in x=`: <<'cmd'` then cmd. bash runs line 2,
      shfmt reads it as the terminator and writes the redirect with no
      Hdoc, and two delimiters hide two lines, on both builds (round 11
      R1).
    - A backtick substitution whose heredoc body holds a bare backtick.
      bash closes the substitution there and runs the lines after it,
      while shfmt keeps the whole body inside the substitution, on both
      builds (round 11 R2).
    - On bash 3.2.57 but not 5.3.20, a `$( )`, `<( )`, parameter default
      or array element whose heredoc body holds an unbalanced `)`, `}` or `]`,
      such as markdown's `1)` (round 11 R3). ciso-reviewer round 15 R1
      ran it again in the unquoted assignment `BODY=$(cat <<'EOF'`:
      bash 3.2.57 ran a body line after `1)`, bash 5.3.20 did not, the
      tree carried no CallExpr for that line, and BSD `xargs -n1` split
      it into its words. The double-quoted `"$(cat <<'EOF'` form ran
      nothing on either build. Design item 10 lists no member for this
      shape, or for the opener-line shape's `$( )` and `<( )` form,
      because each hid on bash 3.2.57, below the repo's 5.2 floor, and
      not on 5.3.20 (row 130, Out of scope). No 5.2.x build was run, so
      that the floor build agrees is [unverified] until the cut-residual
      fixture list's agreement cases run (Dispatch 1's amendment).
  - A heredoc at the top level, or inside a subshell, `{ }`, `if`,
    `case`, `while`, a function body, a pipe or an `&&` list, agrees
    with bash on both builds, so the check passes those [verified:
    ciso-reviewer round 10 R1 and round 11's answers].
  - The merge base caught each member's plain form: base `xargs -n1`
    splits the text into `-F` and the path, and the base extractor
    captures the path, so the cut regresses them for the redaction gates
    (row 129) [verified for round 11's members: ciso-reviewer round 11 R1
    and R2, BSD xargs; unverified for round 10's: ciso-reviewer round 10
    R1 traced the base by reading, not by a run].
  - Base parse-git-command.py's strip_heredocs also drops the line, so
    for the worktree gate the class pre-dates the change [verified:
    ciso-reviewer round 10 R1 and round 11 R1, by reading
    parse-git-command.py:100-132].
  — anchors: row121

Row 123 [assumption]: each redaction gate's header records, as a Known
  gap, that a continuation split of the gated command word or
  subcommand skips the gate before its parse runs [engineer-verified:
  "Record as Known gap (Recommended)"], answering the session's question
  whether to record or close that gap. The question's wording and the
  option's description are the session's [unverified]. One fact per
  item:
  - For `git \<LF>commit -F /dirty.md`, deny-pii-in-commits.sh's
    fragments are `git \` and `commit -F /dirty.md`, so it finds no
    commit and exits before any scan, the staged-diff scan included. The
    other two gates' `gh` prefilters miss `gh \<LF>pr create --body-file`
    the same way [verified: ciso-reviewer round 10 R2, by reading
    deny-pii-in-commits.sh:268-296 and _lib.sh:2932, :3086].
  - A quote split, such as `gi""t commit`, does not skip a gate, because
    each prefilter strips quotes before it matches [verified: read this
    session, deny-pii-in-commits.sh:292 and _lib.sh:3092]. The header
    line names the continuation split alone.
  - The gap pre-dates the change, so it is no regression [verified:
    ciso-reviewer round 10 R2].
  - The waiver rests on the gates' tier lines, which omit
    `untrusted-input`, and on a cooperative agent not splitting a
    command word from its subcommand [unverified].
  - So the CHANGELOG, Design item 9 and PR 1b's body say every command
    the gates parse, not every command.
  - One gate-level case per gate pins the allow (Verification 6).
  - The gap stands unchanged by row 128's cut: it lies before the parse,
    where no cut guard ran.
  Set aside: a raw-text check for a backslash-newline beside a gated
  word, ahead of each prefilter, which would close the gap.
  — anchors: row20

Row 124 [mechanism]: SUPERSEDED by row 128. With status 11 and the
  placement check cut, no repo example meets a new deny, so none of this
  row's edits, its tripwire or its pre-PR searches is delivered. The row
  as it stood: the PR that brings the blanket continuation deny to a
  command shape puts the repo's own examples of that shape on one line,
  so an agent that follows a skill's example does not meet the deny
  every time. Its added scope, the skill edits, the pseudo-file
  deny-text rewords and the flipped gate tests, was kept
  [engineer-verified: "Keep all in scope (Recommended)"]. The question
  was put after the engineer asked why existing examples are denied, and
  its wording and the option's description are the session's
  [unverified]. One fact per item:
  - That the cut superseded this scope, so the answer now covers
    nothing, is the session's inference from row 128, not an engineer
    answer [unverified: not put to the engineer].
  - PR 1b's body quotes the selection and states that inference in the
    session's words.
  — anchors: row121

Row 125 [mechanism]: SUPERSEDED by row 128, and kept, trimmed to what
  live text cites, as the evidence for the cut residual's extglob class.
  The session's decision below, which no engineer answer covered, gave
  way to "Yes, cut them (Recommended)".
  The staged EXTGLOB_SUBSTITUTION_MARKERS condition stays in the strict
  check with exit 5, as row 24 states it. Nothing below is delivered: no
  widened markers, no exit-3 extglob check. The row as it stood: the
  module's extglob check, moved out of the strict check, exits 3, so the
  command denies with status 3, when an ExtGlob pattern holds `$`, a backtick,
  `<(` or `>(` (Design item 2). The rule is the session's decision
  [unverified: the session's judgment that agents do not write an
  expansion inside an extglob pattern, not a figure. Row 130's
  repo-local grep, its one repo check, covered heredocs and pipes fed to
  a shell, not extglob patterns]. It applies ciso-reviewer
  round 12 R1 and R6. One fact per item:
  - shfmt holds an extglob pattern as one raw Lit, so the walker cannot
    reach a command inside it, while bash runs it [verified:
    ciso-reviewer round 10 R3 and round 12 R1, a shfmt build that prints
    no version, bash 5.3.20].
  - bash 5.3.20 runs `${ cmd; }` and `${| cmd; }` inside a pattern, as
    in `[[ x == @(a|${ cmd; }) ]]` with no `shopt`, and after a `shopt -s
    extglob` line in an argument or an assignment value. The four staged
    markers miss both, and bash 3.2.57 has no such form [verified:
    ciso-reviewer round 12 R1].
  - The base `xargs -n1` read the funsub's words and its extractor
    captured the path, so with the staged markers alone the change
    regresses the shape (row 129) [verified: the same R1, BSD xargs; GNU
    xargs not run].
  — anchors: row24, row122

Row 126 [mechanism]: SUPERSEDED by row 128, and kept, trimmed to what
  live text cites, as the evidence for the cut residual's
  heredoc-fed-to-a-shell class. The engineer's answer
  recorded below, "Direct-only, record the rest (Recommended)", gave way
  to "Yes, cut them (Recommended)": the direct forms join the hand-offs
  as one accepted class. Nothing below is delivered: no interpreter
  check, no SHELL_READER_NAMES, no interpreter sentence. The row as it
  stood:
  the module's interpreter check exits 3, so the
  command denies with status 3, when a heredoc or a `<( )` is fed
  directly to a shell reader (Design item 2). Directly means the reader
  is the heredoc's own command, a command nested in it, or a later stage
  of a pipe it feeds. A reader in another statement is outside the
  check. That scope is the engineer's
  [engineer-verified: "Direct-only, record the rest (Recommended)"],
  answering the session's question how to treat a heredoc handed to a
  shell across a statement boundary [unverified: the question's wording
  and the option's description are the session's]. The session's
  grounds: its judgment that agents do not feed a heredoc to a shell, in
  a direct form or a hand-off, resting on row 130's repo-local grep, not
  a figure [unverified]. It
  applies ciso-reviewer round 12 R2 and round 13 R1. One fact per item:
  - `bash <<'EOF'` with the body `git commit -F /dirty.md` runs the body
    as commands, while shfmt's tree holds it as heredoc text, so the
    tree has one CallExpr, `bash` [verified: ciso-reviewer round 12 R2].
  - The base `xargs -n1` read the body's words and its extractor
    captured the path, so the cut regresses the shape for the redaction
    gates (row 129) [verified: the same R2, BSD xargs; GNU xargs not
    run].
  - Base parse-git-command.py's strip_heredocs drops the body, so for the
    worktree gate the class pre-dates the change [verified: the same R2,
    by reading parse-git-command.py:100-132].
  - A shell reader was a command whose words name a shell, or whose first
    word is `source`, `.` or `eval`.
  - The residual the direct-only selection accepted, one class per item
    [verified: ciso-reviewer round 13 R1 and R2 ran the hand-offs and
    `make -f -` on bash 3.2.57 and 5.3.20]:
    - Cross-statement hand-offs: `exec 3<<'EOF'` then `bash <&3`, `exec
      <<'EOF'` then `bash`, a function that runs a shell, as in `f() {
      bash; }` then `f <<'EOF'` or `cat <<'EOF' | f`, `read -r -d ''
      c <<'EOF'` then `eval "$c"` or `bash -c "$c"`, and a script one
      statement writes and a later one runs, as in `cat > s.sh <<'EOF'`
      then `bash s.sh`.
    - Other interpreters, which run their standard input as commands
      with no shell name among their words, such as `make -f -`.
  - The base `xargs -n1` read each of those shapes' body, so for the
    three redaction gates each is a deny-to-allow change, which
    docs/hooks.md:26 makes a regression (row 129) [verified:
    ciso-reviewer round 13 R1, BSD xargs; GNU xargs not run].
  — anchors: row122

Row 127 [mechanism]: SUPERSEDED by row 128. The closed Redirect-operator
  set existed only so the delimiter, placement and interpreter checks
  could find a heredoc. With all three cut, no check finds a heredoc by
  its operator, and the words projection reads no operator, so the set
  guards nothing and is not delivered. The row, trimmed to what live text
  cites: the strict check held every Redirect operator to
  KNOWN_REDIRECT_OPERATORS and exited 5 otherwise, so a shfmt that wrote
  an operator as a number or a renamed token could not leave those three
  checks passing every tree. The rule was the session's decision
  [unverified], applying ciso-reviewer round 12 R3.
  — anchors: row24

Row 128 [assumption]: the plan cuts the guards for odd heredoc
  delimiters, a heredoc inside a substitution, extglob substitutions
  beyond the staged markers, a heredoc fed to a shell, and the
  backslash-newline hides, the classes of Design item 10's cut-residual
  list [engineer-verified: "Yes, cut them (Recommended)"], answering the
  session's confirmation question. The question's wording and the
  option's description are the session's [unverified]. One fact per
  item:
  - The engineer's typed words before that question
    [engineer-verified: "Hm I'm now inclined to cut the ones that a
    cooperative agent wouldn't make. That isn't parity but it seems
    correct to me. What does the architect think and why"]. The session
    relayed row 129's reading between the two.
  - What stays, as the session's option listed it [unverified: the
    session's relay]: the module and the gate switch, split into PR 1a
    and PR 1b (row 131), the carriage-return check (row 118), the
    strict check's existing conditions (row 24), and the deny on any
    shfmt failure (row 59). The shapes go on each gate's header as one
    Known-gaps line under the cooperative tier.
  - The selection is the stop-and-ask answer docs/hooks.md:26 requires
    for the regression part (row 129).
  - The selection named the class "the backslash-newline hides", not
    each member.
  - Code-review round 4 found the `$\<LF>` quoted-part flag member after
    the selection (Design item 10). That the selection covers it, as a
    sibling of the backslash-newline class it cut, is the session's
    reading [unverified].
  - So the session puts that member to the engineer by name, with the
    table's base readings, before PR 1a's first push (PR 1a's session
    steps). Until that answer no row presents it as accepted. PR 1b's
    body records the answer (Critical files).
  - The reversal, one superseded answer per item, each the engineer's
    earlier word on these shapes:
    - "sure, close the hole" (row 121): the class closed, now cut.
    - "I agree." (row 121): the blanket continuation deny, now cut.
    - "Unconditional (Recommended)" (row 121): the delimiter rule on
      every command, now cut.
    - "Accept the over-deny (Recommended)" (row 121): the heredoc rule's
      over-deny, already replaced by the blanket rule, now cut.
    - "Add the span check (Recommended)" (row 122): already replaced by
      the placement rule, now cut.
    - "Direct-only, record the rest (Recommended)" (row 126): the
      interpreter check's scope, now cut, with the direct forms joining
      the recorded rest.
  - Superseded rows: 121, 122, 124, 125, 126 and 127. Each keeps its
    findings as the evidence for the cut residual (Design item 10).
  - Still standing: the engineer's process directive row 122
    paraphrases, which row 130 answers, and row 124's "Keep all in scope
    (Recommended)", whose scope the session infers the cut superseded
    [unverified: the session's inference, row 124].
  — anchors: root

Row 129 [assumption]: the tier reading row 128's selection rests on,
  the architect's, which the session relayed to the engineer, one line
  per item [verified: docs/hooks.md:13, :14, :20, :26, :47, :55, read
  this session]:
  - :13: a finding that requires a shape a cooperative agent would never
    emit is not a defect in a gate, unless the gate also lists
    `untrusted-input`. None of the four gates lists it (root).
  - :55: deny-pii-in-commits.sh and deny-private-project-refs.sh stay
    `cooperative, irreversible` by deliberate choice. A finding needing
    such a shape may be waived, and each gate's header Known-gaps
    section is where a waived finding is recorded.
  - :14: even on an `untrusted-input` gate, such a finding is live only
    when the change introduces or widens the gap. This change widens it,
    so the line would bind an `untrusted-input` gate, and none of the
    four is one.
  - :20: a later-found gap that needs a shape a cooperative agent would
    never emit is recorded with no blocking stop-and-ask. One that needs
    a shape a cooperative agent does emit counts as recorded debt only
    once the human's answer to a blocking stop-and-ask accepts it as
    permanent debt, with the rationale in the commit message or PR body.
  - :26: an input a gate denied at the merge base and allows after the
    change is a regression, "always ADDRESS or stop-and-ask, never
    deferred", and a Known-gaps line in the same change cannot legalize
    it. For the redaction gates the base read the hidden line of the
    continuation, substitution, extglob and shell members rows 121, 122,
    125 and 126 ran, through `xargs -n1` (BSD xargs; GNU xargs not run).
    No run checked the base on the delimiter members [unverified]. So
    the cut is a regression there. Row 128's selection named the classes,
    "the backslash-newline hides" among them, and answers the
    stop-and-ask for those classes.
  - :26, the `$\<LF>` quoted-part flag member, found after that
    selection: BSD `xargs -n1` at the base splits
    `git commit -$\<LF>'F' /dirty.md` into `git`, `commit`, `-$`, `F` and
    `/dirty.md` [verified: session ran BSD xargs -n1; GNU xargs not run].
    The base never read that spelling's `-F`, so the cut is not a
    deny-to-allow change for it on BSD xargs. The double-quoted spelling
    and the worktree gate's `-C` form are read by Verification 1's table
    before PR 1a's first push. The session puts the member to the
    engineer by name with those readings (row 128).
  - :26, the flush-comment member, which no class of row 128's selection
    names: for the subshell form the base read the flag the tree drops,
    so the cut is a deny-to-allow change there [verified: ciso-reviewer
    code-review round 5 R1; GNU xargs not run]. The base worktree parser
    read its worktree form as a git write too. Row 135's two answers, for
    the redaction gates and for the worktree gate, are its stop-and-ask
    answers.
  - :47, first clause: repairing a miss of a shape a cooperative agent
    does emit stays in scope for every tier. The cut therefore rests on
    row 130's claim that no member is such a shape.
  - :47, the counter-reading: "only a deliberate admission of a shape
    carrying the gate's denied semantics is what `irreversible` blocks
    from being waived". The cut deliberately admits shapes that hide a
    source flag, or a git write, the gate denies. Under that reading no
    waiver reaches deny-pii-in-commits.sh, deny-private-project-refs.sh
    or require-worktree-for-git-writes.sh, all three `irreversible`
    (root). The engineer accepted that risk with row 128's selection, for
    the five classes it named, and the decision file and PR 1b's body
    name it. The flush-comment class's questions did not state this
    reading, so no acceptance of it is claimed for that class (row 135).
  — anchors: row128

Row 130 [assumption]: every member of Design item 10's cut-residual
  list needs a construction a cooperative agent does not write
  [unverified: the session's judgment, resting on the repo-local grep
  below, not a figure]. One fact per item:
  - Design item 10's list is the members' one home, with each member's
    trigger and builds. This row restates none of them.
  - A repo-local check agrees: a Grep of claude-skills/,
    claude/.claude/agents/, plugins/, docs/ and README.md found no
    instruction that teaches a heredoc or a pipe fed to a shell
    [verified: ciso-reviewer round 15 R4].
  - For the flush-comment member, a scan of agents' Bash calls found no
    emission of the shape (row 135).
  - The list holds no shape that hides only under a bash below the
    repo's 5.2 floor. Out of scope holds the statement. Each such shape
    pairs a container with its own closer in a heredoc body: an ordinary
    `)` inside an unquoted `$( )` or `<( )`, a `}` inside `${x:-$( )}`,
    or a `]` inside `a[$( )]`. Each hid body lines on bash 3.2.57 and
    not on 5.3.20 (row 122).
  - No 5.2.x build was run, so that the floor build reads them as
    5.3.20 does is [unverified] until the cut-residual fixture list's
    agreement cases run on CI's bash (Dispatch 1's amendment).
  - The engineer wrote [engineer-verified: "Remember that Bash 3.2 is
    not supported by this repo, and install.sh, if I'm not mistaken,
    forces people to upgrade, users to upgrade to Bash 5.2. Please
    check."]. The session's check found the repo's floor at bash 5.2,
    one source per item:
    - README.md:111 sets the shell floor at bash 5.2, first on the PATH
      Claude Code starts with, and says macOS's /bin/bash is 3.2
      [verified: README.md:111].
    - _config.sh's floor constants are 5 and 2, and its check returns 1
      below them [verified: claude/.claude/hooks/_config.sh:26-28,
      :40-67].
    - install.sh sources that check before any mutation, so a
      below-floor bash ends the run there [verified: install.sh:13-32].
    - A below-floor bash fails the check, so every gate denies through
      its _lib.sh bootstrap [verified: docs/hooks.md:508-519].
    - The CHANGELOG says macOS system bash 3.2 is no longer supported
      [verified: CHANGELOG.md:666].
    - bash 3.2 portability is not a review finding, beyond the code
      above a floor check [verified: .claude/rules/shell-floor.md].
  - That a Bash tool whose executing shell is below the floor is
    therefore an unsupported environment, whose heredoc readings need no
    engineer acceptance, is the architect's reading [unverified: no
    cited source names the Bash tool's executing shell, and
    README.md:111 states the floor for the PATH Claude Code starts
    with].
  - SUPERSEDED: the engineer earlier accepted the list's bash 3.2
    member as permanent debt [engineer-verified: "Accept as permanent
    debt (Recommended)"].
    - That answered the session's question whether the cut accepts it.
      The question's wording and the option's description are the
      session's [unverified].
    - After the engineer's note above and the answer below, the plan
      removed the shape from the list.
    - That the answer therefore accepts nothing, and was withdrawn, is
      the session's conclusion [unverified].
    - No Known-gaps line names the shape.
  - The session then asked whether to edit this plan through the
    architect or keep that answer, and the engineer answered
    [engineer-verified: "Yes please"]. The question's wording and its
    options are the session's [unverified].
  - Critical files gives PR 1b's body obligation for these answers and
    row 106's.
  - The ordinary forms beside the members parse as bash reads them, so
    the cut allows them again: a top-level heredoc whose delimiter is a
    plain word, `\EOF`, `'EOF'` or `"EOF"` [verified: ciso-reviewer
    round 10 R1 and round 11's answers, staff-sdet round 8 R1, cited in
    rows 121 and 122], and an ordinary multi-line continuation
    [unverified: row 132's precondition settles it].
  — anchors: row128

Row 131 [assumption]: the plan ships as three PRs, PR 1a the module and
  its proof, PR 1b the redaction gates' switch, and PR 2 unchanged
  [engineer-verified: "Split 1a / 1b (Recommended)"], answering the
  session's question whether to split the first PR into a module-only
  PR 1a and a gate-switch PR 1b, with PR 2 unchanged. The question's
  wording and the option's description are the session's [unverified].
  Two placements are the architect's, which no engineer answer covers
  [unverified]:
  - CI's pin step and version report land in PR 1a, because PR 1a's
    module tests fail under GITHUB_ACTIONS without shfmt (row 68).
  - test_split_command_words.py stays in PR 1a and goes in PR 1b with
    split-command-words.py, because the splitter still runs until then.
  — anchors: row46, row75

Row 132 [mechanism]: with status 11 cut, every ordinary continuation
  reaches shfmt, so Dispatch 1's amendment first shows, through the real
  module, that row 132's shapes yield the words bash passes, and stops
  on any difference — anchors: row128, row130 — the cut rests on the
  members needing a construction a cooperative agent does not write,
  which holds only if the continuations agents do write parse
  faithfully. The shapes, one per item:
  - A multi-line `gh api` call whose lines end in a backslash, carrying
    `-X POST`, `-f body=...` and `-F in_reply_to=...`.
  - `git commit \` with a flag on the next line.
  - A `cd x && \` chain.
  - The four usage-snippet shapes ciso-reviewer round 15 R5 ran, whose
    outer `gh` command holds `--body-file /x` beside a
    `"$(cat <<'EOF'` argument: a quoted heredoc whose last body line
    ends in a backslash, the same with a blank line before the
    terminator, an unquoted heredoc holding snippet lines, and a pipe
    followed by a continuation.
  - A continuation inside double quotes, which the same review ran.
  What the reviews ran, one item per review:
  - staff-sdet round 15 R1 found the first three equal to bash's
    arguments on bash 5.3.20 and 3.2.57 with the session's shfmt, after
    dropping command names and command boundaries [verified:
    staff-sdet round 15 R1]. The precondition keeps the command names
    and the boundaries.
  - ciso-reviewer round 15 R5 found the tree of each of the last five
    holding the words bash sees [verified: ciso-reviewer round 15 R5,
    shfmt alone]. No run compared the module's words with bash on them
    [unverified: the precondition settles it].
  The staged words tests cover a backslash-newline between words and a
  trailing one (test_shell_syntax_tree_words.py:117, :205), not these
  shapes. Set aside: a generated real-bash differential over
  continuations, which tests more than the cut rests on. The shapes
  join the words test as one real-bash comparison under the
  precondition's rules instead, so CI's builds run it on every push.
  The same comparison runs the cut-residual fixture list's agreement
  cases, the floor-build check behind Out of scope's below-floor item
  (Dispatch 1's amendment).

Row 133 [mechanism]: each PR body holds the engineer's answers in their
  words, each [unverified] item's one-line settlement and one line per
  step outcome. Each table goes in a PR comment the body links, split
  across comments when one would pass the cap — anchors: row108, row131
  — the plan makes the body the record for answers and settlements, and
  a table of one row per differing input can outgrow it
  (staff-platform-engineer round 14 R2). GitHub caps a PR body and a
  comment at 65,536 characters [unverified: staff-platform-engineer
  round 14 R2's recollection of the API's validation error, not run].
  Set aside, one per item:
  - A committed file, which would ship scratch output.
  - The decision file, which carries no per-corpus figures.

Row 134 [assumption]: the three PRs keep their boundaries at their
  projected sizes, with no further split [engineer-verified: "Proceed anyway"],
  answering the session's question whether to split them. The question
  stated PR 1a at about 2,400 projected changed lines, PR 1b at about
  4,100 and PR 2 at about 2,850, against the 400-line threshold. Its
  wording and the option descriptions are the session's [unverified].
  One fact per item:
  - Before answering, the engineer typed
    [engineer-verified: "Ask the architect"] and then
    [engineer-verified: "Ask the architect to advise on split and size"].
  - The architect's two consults on those words advised against any
    further split, one reason per PR [unverified: the architect's
    advice, as its consult reports gave it]:
    - PR 1a's only separable piece is CI's pin step, about 170 lines.
    - PR 1b's cuts fail on the pull-before-install lockout (row 6) and
      the Cursor adapter's PATH (row 95), because PR 1b carries every
      change that makes shfmt a requirement (row 75).
    - PR 2 must move the classifiers whole ("Three PRs").
  - On PR 1a's branch, the commit-time size prompt cites this row. It
    does not stand in for that prompt, which require-diff-size-prompt.sh
    has the agent put to the engineer on each branch
    (require-diff-size-prompt.sh:4-11).
  - The answer is not taken to cover PR 1b's or PR 2's branch. Each asks
    on its own branch, at that PR's size, and PR 1b's ask states that 656
    of its lines are whole-file deletions (PR 1b's session steps).
  - The projection moved after this answer, when the cut residual's
    pins, row 132's added shapes and the continued-flag twins joined
    the plan. Each size step states the current figure beside this
    row's (Critical files).
  — anchors: row72, row131

Row 135 [assumption]: the plan records a `#` flush against the end of a
  quote or expansion, which shfmt reads as a comment and bash as part of
  the word, as a cut Known gap rather than adding a deny
  [engineer-verified: "Cut it, record as gap (Recommended)"]. The quote
  covers that choice alone. One fact per item:
  - The question stated these, in the session's wording [unverified],
    one per item:
    - The base `xargs` readers saw the `-F`.
    - The shape hides inside `( )`, `$( )`, `<( )`, backticks and a
      `case` arm.
    - Top level and `{ }` agree with bash.
    - A scan of agents' Bash calls found only embedded Python source and
      the reviewers' own probes, with no agent emission.
  - The option's description is the session's too [unverified].
  - That question stated no worktree-gate reading. The base worktree
    parser has no comment handling, so it reads `( echo "x"#; git push`
    with `)` on a later line as a git write, which a main-tree session
    denies. The new tree holds `echo "x"` alone, so the gate allows it, a
    deny-to-allow change on an `irreversible` gate [verified:
    staff-sdet plan-review round 19 R1; ciso-reviewer plan-review round
    19 R1, traced from parse-git-command.py:268-270].
  - So the session asked again, for the worktree gate, and the engineer
    answered [engineer-verified: "Cut it there too (Recommended)"]. The
    quote covers the cut's reach to the worktree gate as well as the
    redaction gates. The question stated the hidden-write example and
    the scan's result, in the session's wording [unverified].
  - In a `case` arm the hide can also remove a `cd` that bash runs in the
    parent shell, so a later visible write is judged in a directory the
    tree does not show [verified: ciso-reviewer plan-review round 20 R1].
    Only the `case` arm runs its body in the parent shell. The base
    worktree parser reads that form as a SENTINEL deny, so this too is a
    deny-to-allow change [unverified: traced from
    parse-git-command.py:317-320 and :337, not run].
  - The session reads "Cut it there too (Recommended)" as covering this
    consequence, because the answer cut the shape for the gate and the
    scan was shape-level [unverified: the session's reading]. Dispatch
    6's table shows the row to the engineer through the step between
    Dispatches 6 and 7, and a rejected row stops the session.
  - A further trigger was found after both answers: the `)` that closes
    an array literal, as in `x=(a)# ; git commit -F /dirty.md`. It hides
    at top level and in `{ }`, `if`, `while` and function bodies too, so
    the questions' "top level and `{ }` agree" holds for quote and
    expansion triggers only [verified: ciso-reviewer code-review round 7
    R1].
  - Neither answer names this trigger, because both questions named a
    quote or expansion. The plan claims no engineer acceptance of it.
  - A session scan run this session found no agent emitting it. Its
    pattern was a regex lexer over agents' Bash tool inputs for a `#`
    directly after a `)` outside quotes, across main and subagent
    transcripts. It found no shell command with that shape [verified:
    session transcript scan].
  - Recording the trigger as part of the cut class, under the
    engineer's rule to guard only shapes agents emit, is the session's
    decision [unverified]. PR 1a's pre-first-push step shows it to the
    engineer as a session-decided row.
  - A third trigger was found later: the `)` that closes an extglob
    pattern, for all five operators, in the containers where the quote
    and expansion triggers hide [verified: ciso-reviewer code-review
    round 8 R1]. Neither answer names it, and the plan claims no
    engineer acceptance of it.
  - The same scan covers it, because its pattern, a `#` directly after a
    `)` outside quotes, matches an extglob's closing `)` too. It found no
    shell command with that shape [verified: session transcript scan].
  - Recording the extglob trigger in the cut class under the engineer's
    rule is the session's decision [unverified], shown to the engineer
    in the same pre-first-push row.
  - So the plan states the class by its mechanism, which Design item 10
    gives, and treats its listed triggers as examples. A newly found
    trigger of the same mechanism is a member already and needs only a
    fixture entry, not a new engineer question or plan edit. That rule
    is the session's decision [unverified].
  - Before the first question, the engineer wrote [engineer-verified: "we
    should only guard against shapes that agents emit"] and
    [engineer-verified: "if you're worried about a shape and fixing it
    scan the transcripts see what agents do"]. Those quotes state the
    rule: guard only shapes agents emit, and settle a worrying shape
    from what agents do.
  - The scan, one fact per item [verified: session transcript scan,
    agents' Bash calls, no emission of the shape]:
    - Its pattern was a `#` directly after a closing quote, and a `#`
      directly after an expansion, in the text of agents' Bash calls.
    - It matched those shapes in any container, `case` arms included.
    - It read main-session and subagent transcripts under one account's
      set of config roots, as the session read them.
    - Every hit was Python source text inside a python3 heredoc, or a
      reviewer's own probe, and none was a shell command an agent ran.
  - shfmt and bash read the shape differently, and for the subshell form
    the base read the flag the tree drops [verified: ciso-reviewer
    code-review round 5 R1]. Design item 10's entry holds the readings
    and the containers seen hiding.
  - The guard the session planned for the shape after code-review round 5
    is withdrawn. No engineer answer covered it.
  — anchors: row128, row130

Row 136 [assumption]: PR 1a keeps three additions the session made to
  its CI part: the `CI_SHFMT_INSTALL_DIR` test-only seam and the
  installed-file digest re-check (Design item 7), and the move of
  `test_git_floor.py`'s pin-step helpers into `helpers.py` (Dispatch 1's
  CI part). Asked about that added scope, the engineer selected
  [engineer-verified: "Keep all three (Recommended)"]. The quote covers
  keeping the three in PR 1a alone. One fact per item:
  - The question's wording and its option descriptions are the
    session's [unverified].
  - Each addition's design is the session's decision [unverified]. No
    engineer answer covers how it is built or what it guards.
  - The seam guard's two limits (Design item 7) are accepted by the
    session's decision, not an engineer answer [unverified].
  - PR 1a's pre-first-push step shows the three to the engineer as
    session-decided rows, and PR 1a's body records them (Critical files).
  — anchors: row38, row131

Row 137 [assumption]: `code-file-size-exceptions.toml` joins this
  plan's Critical files, because PR 1a passes the file-size check in
  `claude/.claude/tests/test_code_file_size.py` by editing it, not by
  moving code out. Asked how to fix that check's failure on PR 1a's
  first CI run, the engineer selected
  [engineer-verified: "Raise ceilings, mark split pending (Recommended)"].
  The quote covers that choice of fix for PR 1a alone. One fact per
  item:
  - The question's wording and its option descriptions are the
    session's [unverified].
  - The edit raises the `claude/.claude/hooks/_lib.sh` and
    `claude/.claude/tests/helpers.py` rows' ceilings and adds a "split
    pending" row for
    `claude/.claude/hooks/tests/test_shell_syntax_tree_contract.py`
    [verified: code-file-size-exceptions.toml in the working tree].
    That row's seam names its test-class families by concern [verified:
    code-file-size-exceptions.toml in the working tree]. Each ceiling
    equals its file's line count in the working tree [verified:
    working-tree line counts, staff-platform-engineer round 23 R3; the
    check itself was not run].
  - It is the check's third remedy, which adds or raises the file's row
    "with a seam or a reason", under the heading "If this branch changed
    the file, take the first remedy that fits:" [verified:
    claude/.claude/tests/code_file_size.py:37, :418].
  - The first remedy moves the new code into a new module or test file
    [verified: code_file_size.py:416]. Here it would move the new shfmt
    and pin-step helpers into a module local to
    `claude/.claude/hooks/tests/` and split the contract file along its
    seam. That the engineer set it aside for PR 1a, as the follow-up
    split (Out of scope), is the session's account of the question
    [unverified].
  - `helpers.py`'s row gives as its reason that a helper used by one
    test tree goes in that tree's local module, not in `helpers.py`
    [verified: code-file-size-exceptions.toml]. The pin-step helpers
    serve `claude/.claude/hooks/tests/` alone (Dispatch 1's `helpers.py`
    bullet), so until the follow-up the raised ceiling holds helpers
    that reason places elsewhere. Whether the question stated that
    reason is [unverified].
  - A row's ceiling must equal its file's count, so a later edit to any
    of the three files fails the check until its row is re-synced
    [verified: claude/.claude/tests/test_code_file_size.py:1]. A PR 1a
    commit that changes one of them re-syncs its row in the same
    commit, which the session reads as within this answer [unverified].
    A merge from `main` can move one of these rows too, and the toml
    header's conflict rule settles it [verified:
    code-file-size-exceptions.toml:19-24].
  - The answer is not taken to cover PR 1b's or PR 2's branch. Each of
    those PRs meets the same check, which fails a rowed file whose count
    differs from its ceiling and an unrowed file past the line limit
    [verified: claude/.claude/tests/code_file_size.py:337-352]. The
    check's printed output on that PR's branch decides which files need
    a row edit. The rowed files each PR's dispatch lists edit today, one
    PR per item [verified: code-file-size-exceptions.toml, Critical
    files]:
    - PR 1b, one file per item:
      - `_lib.sh`, Dispatches 2 and 3.
      - `helpers.py`, Dispatches 2 and 5.
      - `claude/.claude/hooks/_config.sh`, Dispatches 3 and 5.
      - `install.sh`, Dispatch 3.
      - `claude/.claude/scripts/select-tests.py`, Dispatch 4.
      - `claude/.claude/scripts/tests/test_select_tests.py`, Dispatch 4,
        if that dispatch edits it.
      - `claude/.claude/hooks/tests/test_hook_alignment.py`, Dispatches
        2 and 5.
      - `claude/.claude/hooks/tests/test_deny_pii_in_commits.py`,
        Dispatch 2.
      - `claude/.claude/hooks/tests/test_deny_private_project_refs.py`,
        Dispatch 2.
    - PR 2, one file per item:
      - The contract file, Dispatches 6 and 7.
      - `claude/.claude/hooks/tests/test_ask_new_dependency_disclosure.py`,
        Dispatch 6. Its docstring edit may leave its count unchanged.
      - `claude/.claude/hooks/tests/test_require_worktree_for_git_writes.py`,
        Dispatch 7.
      - `claude/.claude/hooks/tests/test_send_back_skipped_self_review.py`,
        Dispatch 7.
      - `test_hook_alignment.py`, Dispatch 7.
    An unrowed file a dispatch takes past the limit needs a new row.
    `claude/.claude/hooks/deny-private-project-refs.sh` and
    `claude/.claude/hooks/tests/_cursor_payloads.py`, which PR 1b
    edits, sit just under it [verified: working-tree line counts].
    `test_shell_syntax_tree_git_records.py`, which PR 2 creates by a
    move and grows, may cross it [unverified].
    Neither PR's file list holds the toml. PR 1b's first session step
    puts that addition to the engineer (Critical files).
  — anchors: row131
```

## Critical files

There are seven `code-writer` dispatches. Dispatch 1 builds PR 1a, Dispatches 2-5 build PR 1b, and Dispatches 6-7 build PR 2, so each PR's dispatches are contiguous and each PR leaves every gate wholly on one tokenizer. The pin step and version report, which Dispatch 3 carried, move into Dispatch 1, so PR 1a holds them (row 131). Each dispatch ends with `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py`. Every dispatch runs after the one before it, and a later dispatch may edit a file an earlier one edited.

This plan file ships in PR 1a, so its lines count toward PR 1a's review surface, though the `Projected diff:` line leaves them out. Each session step's outcome lands in its PR's body, not in this file, so `require-plan-review.sh` does not re-fire before Dispatch 1.
- Each of these stays `[unverified]` here, and the named PR's body records how it settled, one PR per item:
  - PR 1a: row 26, row 40, row 57, row 67, row 86, row 113's `[unverified]` items, row 118's `[unverified]` items and row 132's precondition.
  - PR 1b: row 15's vendor lines, row 59's SIGPIPE item, row 98 and row 101.
- These items stay unsettled by any step, one group per item (comment-discipline-reviewer round 13 R1):
  - Row 15's other `[unverified]` part, what the vendor pages do not state.
  - The `[unverified]` items of rows 121, 122, 125 and 126, which row 128 superseded and which stay as evidence only.
  - The option descriptions of rows 128 and 131, which are the session's.
  - Row 130's `[unverified]` items, among them its judgment that agents do not write the cut residual's members and its reading that a Bash tool running a below-floor bash is an unsupported environment.
- PR 1b's body states the zsh acceptance rationale beside row 106's quoted answer (row 114).
- PR 1b's body states the cut residual's five classes that row 128 named as a regression the engineer accepted, beside row 128's typed words and selected label, with row 129's reading and its line-47 counter-reading for those classes. That selection is the stop-and-ask answer `docs/hooks.md:26` requires, and the body is its record (row 133).
- PR 1b's body quotes "Cut it, record as gap (Recommended)" for the flush-comment class. It says the `docs/hooks.md:47` counter-reading was not put to the engineer for that class, so PR 1b's reviewer meets it as an open item, not as accepted (row 135). The body names the `$\<LF>` quoted-part flag member, says the selection named its class and not the member, and quotes the engineer's answer on it by name (rows 128, 129).
- PR 1b's body quotes row 124's "Keep all in scope (Recommended)" and states, in the session's words, that the edits it kept dropped with the cut rules (row 124).
- PR 1b's body quotes together "Accept as permanent debt (Recommended)", the engineer's note beginning "Remember that Bash 3.2 is not supported by this repo", "Yes please" and "Keep it dropped (Recommended)" (rows 106, 130). In the session's words, it states each of these:
  - The acceptance was treated as withdrawn.
  - Shapes that hide only under a bash below the 5.2 floor are out of scope (Out of scope).
  - The `CLAUDE_CODE_SHELL` drop beyond the README sentence is the session's extension (row 106).
- Before any table, timing or command output goes into a PR body or comment, the session replaces temp-directory, user, tool, home and checkout paths with placeholders, because the redaction detectors cover only home-rooted paths and the gate tests build commands from temp paths that embed the OS username.
- The Dispatch 1 commit carries the 64-hex digest literal in `tests.yml`, one fact per item (ciso-reviewer round 17 R3):
  - The redaction gate's long-hex detector, a run of 32 or more hex characters (`docs/private-project-redaction.md:73`), may deny that commit.
  - `tests.yml` already carries 40-hex action SHAs at the merge base (`tests.yml:51`, `:109`), so a long hex literal in that file has precedent.
  - If the gate denies, the session stops and reports the denial, and the engineer commits it from their own terminal. The opt-in marker is never removed.
  - PR bodies and comments cite the digest by file and line, never by value.
  - `TestPinLiterals` keeps the 64-hex expectation.
- An outcome that contradicts a row stops the session, which then edits this file and re-runs `/plan-review`.
- PR 1b and PR 2 start with this file committed and do not edit it.

What a PR body holds (row 133, staff-platform-engineer round 14 R2), one rule per item:
- The ceiling: the engineer's answers in their words, each `[unverified]` item's one-line settlement, one line per session-step outcome, and the dependency rationale. Before `gh pr create` or `gh pr edit`, the session measures the assembled body with `wc -m` and keeps it under row 133's cap, leaving room for the blocks `pr-description` manages.
- The overflow home: each table goes in a PR comment the body links, one comment per table, split across comments when one would pass the cap. The tables are the `words` differential table, PR 2's changed-case table, the dump's forms, the timings and the rehearsal outcomes.
- Each table row's answer and verdict stays in the body as one line, whatever moves.
- The obligations, one group per PR, one obligation per item:
  - PR 1a:
    - Verification 9's dependency rationale.
    - Row 40's source proofs.
    - The build-provenance limit, with row 38's `go install` route and its cost (row 40).
    - The engineer's answer on the re-hash waiver, by name, and whether a re-hash ran (row 40).
    - The engineer's answer on the `$\<LF>` quoted-part flag member, by name, with its base readings (row 129).
    - The engineer's answer on the flush-comment member, "Cut it, record as gap (Recommended)", beside the rule they typed and the question's wording as the session's (row 135).
    - The engineer's answer that, for the dropped-key class, the later acceptances govern over row 76, "Later answers govern (Recommended)", with the question's wording as the session's (row 24).
    - The session-decided rows the pre-first-push step showed the engineer: the empty-`Lit` over-deny and the array-literal-closer and extglob-closer triggers, each as the session's decision (rows 24, 135).
    - The three session-decided CI additions the pre-first-push step showed the engineer, each as the session's decision: the `CI_SHFMT_INSTALL_DIR` seam with its guard's two limits, the installed-file digest re-check and the `test_git_floor.py` helper move. Beside them, the engineer's scope answer "Keep all three (Recommended)", with the question's wording and option descriptions as the session's (row 136).
    - Row 132's precondition outcome, with its build lines.
    - The agreement cases' outcomes on the session's bash and on CI's, with each build line (PR 1a's session steps).
    - The `words` table's answer in the engineer's words, with a linked comment carrying the table (Verification 1).
    - The dump's forms, as provisional (Verification 2).
    - PR 1a's settlements above.
    - Its first CI run's outcomes, and the parallel leg's wall time as the baseline.
    - The file-size fix's answer, "Raise ceilings, mark split pending (Recommended)", with the question's wording and option descriptions as the session's, and the follow-up it leaves, the helper move and the contract-file split (row 137, Out of scope).
    - Verification 8's memory measurement.
    - Its size answer.
  - PR 1b:
    - The `words` table's answer, quoted from PR 1a's body with a link to PR 1a's table comment, and the table's re-run on PR 1b's head (Verification 1).
    - A cite of PR 1a's dependency rationale (Verification 9).
    - The deleted splitter cases, with their reasons.
    - PR 1b's settlements above.
    - The zsh and cut-residual acceptances, the latter for row 128's five classes.
    - The flush-comment answer, with the open `docs/hooks.md:47` reading for that class (above).
    - The dropped-key limit's first acceptance, "Accept, revisit later (Recommended)", with the explanation's wording as the session's (row 24).
    - The engineer's bash 3.2 note, with the below-floor statement and the answers quoted beside it (above).
    - Row 124's selection, with the session's inference.
    - Its first CI run's parallel-leg wall time, beside PR 1a's.
    - Verification 8's timings.
    - Verification 10 and 11's outcomes.
    - The file-size fix's answer for PR 1b and PR 2, in the engineer's words, with the question's wording as the session's (row 137, PR 1b's session steps).
    - Its size answer.
  - PR 2:
    - The changed-case table and the engineer's answer (Verification 3).
    - PR 1b's file-size fix's answer, quoted with a link to PR 1b's body (row 137).
    - The engineer's answers on the dropped-key limit for the worktree gate, "Yes, accept for it too (Recommended)", and on the flush-comment cut there, "Cut it there too (Recommended)", with each question's wording as the session's (rows 24, 135).
    - Verification 8, 10 and 11's PR 2 parts.
    - Its size answer.

### PR 1a — the module

The order, one reason per step:
- Dispatch 1's amendment starts with row 132's precondition, because its outcome decides whether the cut stands.
- Its CI part comes last in the same dispatch. PR 1a's first push follows the pin step's commit and the engineer's answers on the marked rows, so a rejection changes the module or this plan before review. The reasons for that push order, one per item:
  - CI runs only on a pull request or a push to `main` (`tests.yml:12-15`), so CI's first run means opening PR 1a.
  - Dispatch 1's `require_shfmt()` fails CI until the pin step exists.
  - No gate calls the module in PR 1a, so CI's first contact with the pinned shfmt and with CI's bash comes before any gate depends on either.

A failure at that first run costs one of five things (comment-discipline-reviewer round 14 R6):
- A pin-step failure, a failed fetch, a downloaded-file digest mismatch or a wrong resolved path takes a pin or URL change in a fix-up commit.
- An installed-file digest mismatch takes a re-run and an inspection of the install, not a pin change, because its message names a file that changed between the digest check and the install, or an install that wrote other bytes.
- A conformance case that fails on CI takes CI's form in a fix-up commit, which updates any hand-built tree that copies it.
- A real-bash comparison that fails, one consequence per kind of case:
  - Row 132's shapes and the carriage-return cases: the failure contradicts row 118 or row 132 and stops the session.
  - An agreement case of the cut-residual fixture list: its shape goes back into Design item 10's list, and the session revises this plan. No fix-up commit edits the case to match CI.
- A cut-residual pin that fails shows its Design item 10 entry wrong on CI's shfmt. The entry is the record the engineer accepted, so the failure stops the session, which revises this plan.

One session step comes with the first commit that takes a branch to 400 changed lines, on each PR's own branch. On this branch it is Dispatch 1's first commit (staff-platform-engineer round 13 R3, round 14 R1):
- `require-diff-size-prompt.sh` denies that commit until the engineer answers `Proceed anyway`, once per branch (`require-diff-size-prompt.sh:4-11`).
- The step cites the engineer's plan-time answers on the split, rows 46 and 131. On PR 1a's branch it also cites row 134, the engineer's plan-time "Proceed anyway" at the three PRs' projected sizes. Row 134 is not taken to cover PR 1b's or PR 2's branch, so the step on each of those asks afresh at that PR's size (row 72).
- The question states the PR's `Projected diff:` size and, for PR 1a, this plan file's lines beside it, because the reviewer meets both. It also gives the earlier figures that line records for the plan as first committed on this branch, and row 134's figure where the projection has moved from it.
- On `Split now`, the session stops, moves the PR boundary in "Three PRs" with the engineer, and re-runs `/plan-review` before the next commit.
- That PR's body records the answer, in the engineer's words.

Three more session steps, one per item:
- The pin's digest, taken before Dispatch 1. A bump repeats these steps, in order:
  - The session confirmed row 40's items: the release's asset list, `gh release verify v3.14.0 -R mvdan/sh`, and `gh attestation verify` on the linux amd64 asset.
  - The session fetched that asset with curl into a fresh empty directory, never ran it, and hashed it with `shasum -a 256`. The asset's URL is recorded beside the digest.
  - The hash equals GitHub's digest for the asset and the attested release digest (row 40).
  - Dispatch 1's prompt carried that digest as the CI literal, because a `code-writer` dispatch cannot pause for it.
  - PR 1a's body records what each source proved (Design item 7).
  - The engineer authorized the session to take the digest (row 40).
  - A separate re-hash by the engineer is optional by the session's decision [unverified], which the next step puts to the engineer (row 40).
- After Dispatch 1 and before PR 1a's first push, put these to the engineer, one per item:
  - Every marked row of Dispatch 1's `words` differential table (Verification 1). A rejected row then changes the module before review.
  - The `$\<LF>` quoted-part flag member, by name, with the table's base readings of its spellings and its `-C` form (row 129). Until the answer, no row presents it as accepted.
  - The waiver of a separate human re-hash of the pinned asset, by name (row 40).
  - The empty-`Lit` over-deny, shown as a session-decided row with its two shapes and their allow-to-deny table rows, not as a question (row 24, Verification 1).
  - The flush-comment class's array-literal-closer and extglob-closer triggers, shown as a session-decided row with their scan, not as a question and not as an engineer acceptance (row 135).
  - The `CI_SHFMT_INSTALL_DIR` seam with its guard's two limits, the installed-file digest re-check and the `test_git_floor.py` helper move, each shown as a session-decided row, not as a question (row 136, Design item 7). The engineer's only answer on them is the scope answer "Keep all three (Recommended)".
  PR 1a's body records each answer in the engineer's words and links a comment carrying the table (row 133). PR 1b's expectation changes follow the table's answer, and PR 1b's body quotes it and links PR 1a's comment.
- At PR 1a's first CI run, one step per item, in order:
  - Read the pin step's exit and its printed `shfmt --version`.
  - Read the real-shfmt cases' and the real-bash comparisons' outcomes. The forms the session's build printed are the baseline.
  - Record in PR 1a's body each case whose outcome differs from it.
  - Record in PR 1a's body the agreement cases' outcome on CI's bash, with the version-report step's `bash --version` first line, beside the session's outcome and build line.
  - Record the parallel leg's wall time beside the last `main` run's, as the baseline PR 1b's first run compares with.
  - Confirm the 30-minute job cap at `tests.yml:34-43` against it, or re-derive it in a fix-up commit, as that comment requires (staff-platform-engineer round 10 R6).

**Dispatch 1 — the projection module and `words` (PR 1a).** The staged tree holds its first implementation, described by the items up to the amendment, and the amendment is what remains. Its first step dumps `shfmt -ln bash --to-json` for a corpus covering every construct in Design item 2. The corpus includes `git-records` constructs, a word holding the byte 0xFF, and a carriage return before `#`. It settles rows 26 and 113 from that dump. Before it ends, it settles row 118's premises and its other-character question against real shfmt and real bash (Verification 2). It reads `mvdan.cc/sh/v3/syntax` at v3.14.0 for the node types, operators and struct key sets, and settles row 86.
- Create `claude/.claude/hooks/shell-syntax-tree.py` with the strict check, `BASH_REJECTED_NODE_TYPES`, the walker, word flattening with its backslash decoder, the `words` projection, and UTF-8 stdin and stdout. The commit that adds the decoder justifies hand-rolling it in its message (Design item 2).
- `claude/.claude/hooks/_lib.sh`: `_LIB_SHFMT_ARGV` (Design item 1), so every real-shfmt test in every PR runs the production argv from the start.
- `claude/.claude/hooks/tests/test_shell_syntax_tree_words.py`, tests on real shfmt behind `require_shfmt()`. The staged tree built it by a `git mv` of `test_split_command_words.py` and a rewrite, and the amendment restores the old file beside it:
  - Convert each xargs-divergence and pre-pass case to the words bash sees. A splitter case with no counterpart here tests deleted code alone, and PR 1b's body lists each with its reason when PR 1b deletes the splitter's test file.
  - Rewrite `TestResidualShapes` to assert the words bash sees.
  - Add the attached-flag matrix, the realistic smoke set, and the backslash cases of Verification 6, the real-bash comparison included.
  - Add Verification 6's U+FFFD case, its carriage-return premise case, and the comparison's widened character set (rows 113, 118).
  - No case asserts on shfmt's stderr text. The non-UTF-8 case asserts exit 1 and empty stdout, which prove the cause on otherwise valid bash.
- Create `claude/.claude/hooks/tests/test_shell_syntax_tree_contract.py`. It never skips as a whole:
  - Behind `require_shfmt()`: the conformance corpus, the `BASH_REJECTED_NODE_TYPES` samples, the shebang cases with their flag-removed controls, the `.editorconfig` case with its `--filename` control (row 67), and the child-position matrix. The matrix is one fixture table of construct, child position and command kind, a git write or a `cd`, parametrized over projections. PR 1a ships its `words` assertion.
  - Without shfmt: the hand-built-tree cases, the module's exit-path and encoding cases, and the interpreter-isolation and capability-pin tests carried over from the old splitter test file.
  - The completeness tests: `KNOWN_NODE_TYPES` against the corpus's `Type` values in both directions, and every `KNOWN_NODE_TYPES` entry either in the matrix or in a named set of types that hold no command.
- `claude/.claude/tests/helpers.py`:
  - `require_shfmt()`, which skips with a reason naming the pin in `.github/workflows/tests.yml` and fails under `GITHUB_ACTIONS` (row 68). Its `README.md` § "Requirements" citation arrives with PR 1b's shfmt bullet (Dispatch 5).
  - `production_shfmt_argv()`, which sources `_lib.sh` and returns `_LIB_SHFMT_ARGV`. The conformance corpus, the child-position matrix, the shebang cases and the `.editorconfig` case run shfmt with it, and their controls run it with one flag changed.
  - One stub-shfmt writer, `write_stub_shfmt`, placed after `write_prewarmed_stub`. It prints a given tree or a given version line, or exits with a given status, optionally after a given stderr line or a hang. It logs its argv, its stdin and its working directory. Every stub-shfmt test in both PRs uses it.
  - With the CI part below, the workflow readers and pin-step helpers that `test_shfmt_floor.py` and `test_git_floor.py` share. Each is new in this change. Of the workflow readers, the base holds only `ci_tests_workflow_jobs` and `ci_test_slice_job`. One helper per item:
    - `ci_tests_workflow`, the parsed workflow. `ci_tests_workflow_jobs` is refactored to read it.
    - `ci_test_slice_step`, which finds one `test-slice` step by id and asserts that exactly one matches.
    - `PIN_STEP_LOGGING_STUB`, the logging base of every pin-step stub.
    - `pin_step_sudo_stub`, which writes a `sudo` stub that runs the sibling stub of each accepted command.
    - `pin_step_calls_to`, which reads one command's lines from a stub log.
- Create `claude/.claude/hooks/tests/_shell_syntax_tree_runners.py`, the helpers the two new test files share, and `claude/.claude/tests/test_stub_shfmt.py`, the tests of the stub-shfmt writer (row 119).
  - The runners file reads `production_shfmt_argv()` once per session through `functools.cache`, as `claude/.claude/hooks/tests/conftest.py:54` caches its probe, because each call sources `_lib.sh` in a fresh bash.
  - `test_stub_shfmt.py`'s production-argv test asserts that the argv holds `-ln`, `bash` and `--to-json`, not only `shfmt` first.
- `claude/.claude/hooks/tests/conftest.py`: a `pytest_report_header` line when shfmt is not on PATH, one fact per item:
  - pytest calls that hook only for initial conftests, so the line prints on a run that names a path under `claude/.claude/hooks`, not on the full-suite command (code-review round 4).
  - A full-suite run shows the cause through `require_shfmt()`'s skip text, which the `-ra` in `pyproject.toml:24`'s `addopts` prints.
  - A conftest initial for both runs would be a tracked `claude/.claude/conftest.py`.
  - `test_pytest_collection_config.py` rejects that file as a second bare `conftest` module beside `evals/conftest.py`.
  - The session accepted the header for scoped runs only.
  - One unit case calls the hook function with `shutil.which` monkeypatched to each outcome. It asserts the line is present when shfmt is missing and absent when shfmt is found, and that the line names `shfmt`. It does not assert the sentence, which Dispatch 2 widens.
- Leave `split-command-words.py`, `parse-git-command.py` and `test_parse_git_command.py` untouched. PR 1b deletes the first, and PR 2 moves the other two.
- Deliverable to the session: the `words` differential table of Verification 1. A scratch script outside the repository, which is not committed, runs the base commit's `_lib_command_words` from a scratch worktree against `shfmt` piped into the module's `words`, and applies each gate's source-path extraction to both word streams. Verification 1 gives its inputs and its two `xargs` builds. PR 1a's body carries the answer, and a comment it links carries the table (row 133).
- Reuse: the shape of `require_direnv()` and `require_zsh()` at `claude/.claude/scripts/tests/conftest.py:133-159` for `require_shfmt()`.
- The amendment, after Dispatch 1's first implementation. It lands before the marked-row step that follows Dispatch 1, beside Dispatch 1's remaining review fixes, which it leaves unchanged. One step or edit per item, in this order:
  - First, row 132's precondition, as an explicit step before any edit. The first three shapes are these, each line ending in a backslash but the last, and the other five take the forms row 132 describes:
    - `gh api repos/o/r/pulls/1/comments \`, then `-X POST \`, then `-f body='a reply' \`, then `-F in_reply_to=1`, each on its own line.
    - `git commit \`, then `-m x` on the next line.
    - `cd x && \`, then `git status` on the next line.
  - The precondition's rules, one per item. The committed comparison below reuses them:
    - The module side gets the shape's text as written, through shfmt under `production_shfmt_argv()` and the real module's `words`.
    - The bash side gets the prelude `w() { printf '%s\0' "$@"; printf '\n'; }; cat() { :; }`, then the shape's text with `w ` before each command name outside a substitution. It runs as `/usr/bin/env -i PATH=<dir> <bash> --norc --noprofile -c <text>` from `<dir>`, a fresh empty `mktemp -d` directory, so only builtins and the prelude's functions run.
    - `<bash>` is the absolute path `command -v bash` gives, a bash at or above the repo's 5.2 floor (Out of scope). shfmt is the session's.
    - When that bash is below the floor, the session runs a bash at or above it by its absolute path, or reports and stops when the machine has none.
    - How the two outputs split, one side per item:
      - The module's output splits at blank lines into commands and each command at newlines into words. The commands nested in a substitution drop out, and each shape names them.
      - bash's output splits at newlines into commands and each command at NUL bytes into words.
      - Every substitution in row 132's shapes sits inside double quotes and no top-level word holds a newline, so the two splits line up. Each agreement case is written to line up the same way (the fixture list below).
    - A difference is a different number of commands, a different number of words in one command, or two words that differ. A module word holding the placeholder matches any bash word in its place.
    - On a difference, stop, make no further edit, and report the shape, the bash build and both split lists, because the cut rests on these parsing faithfully (row 132).
    - PR 1a's body records the outcome, the bash's `bash --version` first line, and shfmt's `--version` output, an empty one included.
  - Restore `claude/.claude/hooks/tests/test_split_command_words.py` at its merge-base content, because the splitter still runs until PR 1b deletes both (row 131). `test_shell_syntax_tree_words.py` stays a new file beside it. Run the restored file once, so a helper it imports that the staged `helpers.py` changed shows at once.
  - `claude/.claude/hooks/tests/_shell_syntax_tree_runners.py`, one edit per item:
    - `run_shfmt` gains the hang guard Verification 6 specifies (staff-platform-engineer round 10 R6).
    - One real-bash helper under the same guard. Every real-bash call in the two new test files goes through it, `test_bash_passes_the_carriage_return_hash_flag_and_path_as_three_words` included (staff-sdet round 15 R5). When its bash reports a version below the floor `_config.sh` defines, it fails with a floor message naming that version, not a comparison diff.
    - The cut-residual fixture list: one entry per member of Design item 10's list except two, each with its input, its stated outcome and an id naming its class. The two exceptions are the `$\<LF>` quoted-part flag member, with two entries, and the flush-comment member, with one entry per form listed below. A comment says closing a member flips its case in every suite that reads the list. Dispatch 5 adds the decision file's heading to that comment.
      - The heredoc-in-a-substitution class's ids name the backtick form, as Design item 10 does.
      - Each member entry states one of three named outcomes, one per item:
        - HIDDEN: `-F` and `/dirty.md` are absent.
        - SHOWN: both are present in one command.
        - RENAMED_FLAG: `-$F` and `/dirty.md` are in one command, and `-F` is absent.
      - The `$\<LF>` quoted-part flag member is RENAMED_FLAG, with one entry per spelling, single-quoted and double-quoted, because each reaches a different flatten branch. Its entries record seen on bash 5.3.20 and 3.2.57 (staff-sdet round 17 R2).
      - The flush-comment member has one HIDDEN entry per form seen hiding, so each flips on its own (row 135, staff-sdet plan-review round 18 R3). Each records seen on bash 5.3.20 and 3.2.57, the second build an observation below the repo's floor, not a supported build (staff-sdet plan-review round 21 R3). The first five each put `git commit -m "x"# -F /dirty.md` in their container, with the closer on a later line:
        - A subshell, `( … )`.
        - `"$( … )"`.
        - `<( … )`.
        - Backticks.
        - A `case` arm, `case x in x) …` with `;; esac` on a later line.
      - The others state their own input:
        - A subshell holding `git commit -m $x# -F /dirty.md`, for a flush after an expansion.
        - An array literal whose later element holds the command, `x=( "a"# $(git commit -F /dirty.md)` with `)` on a later line (ciso-reviewer plan-review round 19 R3).
        - Its declaration form, `declare -a x=( "a"# $(git commit -F /dirty.md)` with `)` on a later line (staff-sdet plan-review round 20 R1).
        - An array-literal closer at top level, `x=(a)# ; git commit -F /dirty.md`, id `flush-comment-after-array-literal-closer`. It records seen on bash 5.3.20, the build its finding ran (ciso-reviewer code-review round 7 R1).
        - An extglob closer, id `flush-comment-after-extglob-closer`: `shopt -s extglob` on its own first line, then a subshell holding `git commit -m @(a|b)# -F /dirty.md` with `)` on a later line. It records seen on bash 5.3.20, the build its finding ran (ciso-reviewer code-review round 8 R1).
      - Each array entry has an unflushed twin as its flip control: the same text without the `#` projects `-F` and `/dirty.md` in one command (staff-sdet plan-review round 20 R1).
      - The array-literal-closer entry has the unflushed twin `x=(a); git commit -F /dirty.md`, whose words hold `-F` and `/dirty.md` in one command (ciso-reviewer code-review round 8 R3).
      - The extglob-closer entry has an unflushed twin, the same text without the `#`, whose words hold `-F` and `/dirty.md` (ciso-reviewer code-review round 8 R1).
      - The array-literal-closer entry's spaced twin, `x=(a) # ; git commit -F /dirty.md`, runs nothing in bash, which the flush check reads (Verification 6). The extglob-closer entry's spaced twin, the same text with a space before the `#`, runs nothing in bash either.
      - The subshell entry also records the base reading: BSD `xargs -n1` read `-F` and the path [verified: ciso-reviewer code-review round 5 R1; GNU `xargs` not run].
      - Each flush-comment entry whose visible part is a command also asserts the visible head words, `git`, `commit` and `-m`, in one command, so a shfmt change that dropped the whole container fails the pin too (staff-sdet plan-review round 19 R3). The extglob-closer entry is one of them.
      - The two array entries and the array-literal-closer entry assert absence alone, because their visible part holds no command. The module projects no words from an array's plain elements, or from a declaration's own words (staff-sdet plan-review round 20 R1, R3).
      - Three agreement cases pin the class's boundary, each with `-F /dirty.md` after the flush `#` and the module's words equal to bash's, `-F` and the path included (staff-sdet plan-review round 18 R2, round 19 R3):
        - `git commit -m "x"# -F /dirty.md` at top level.
        - The same inside `{ }`, with `}` on a later line.
        - `git commit -m $x# -F /dirty.md` at top level, for a flush after an expansion.
      - The same list holds the floor-build agreement cases, each labeled as an agreement case and none a member. They check Out of scope's below-floor item, one per container and closer pair that item covers (staff-sdet round 16 R1):
        - `$( )` with `)`, in an unquoted assignment and in an `export` form.
        - `<( )` with `)`.
        - `${x:-$( )}` with `}`.
        - `a[$( )]` with `]`.
        - The one-line opener `x=$(: <<EOF)`.
      - In each floor-build agreement case, the heredoc body's first line holds the closer, and a following line is a `w` call carrying a flag and a path. Each case ends in a command whose words the module carries. The case's other text lines up under the precondition's rules on a bash that does not hide it.
      - A bash that hides that line runs it, so the comparison fires on a differing command count or word list [verified: staff-sdet code-review round 4 R6, round 17 R4]. On bash 3.2.57, the two groups, one per item:
        - The process-substitution case and the one-line opener differ in command count. bash runs the exposed call and then the rest of the script, so it prints one command more than the module.
        - The other four differ in words. bash runs the exposed call, then a syntax error at the stray closer ends the script before the trailing `echo done`. Each side then holds one command, the module's `echo done` against bash's exposed call.
      - Row 132's real-bash comparison runs the agreement cases. The member pins read the member entries alone (Verification 6).
      - A unit check on the list replaces the tautological label test, one condition per item (staff-sdet round 17 R3):
        - Every entry's kind is MEMBER or AGREEMENT.
        - Ids are unique.
        - The id set equals a named expected set, one group per item:
          - One entry for each member of Design item 10's list other than the two below.
            - The delimiter class's entries include `delimiter-mismatch-ansi-c-delimiter-decoding-to-the-terminator` and `delimiter-mismatch-locale-delimiter-holding-a-backslash`. Each records seen on bash 5.3.20 and 3.2.57, the second build an observation only.
          - Two for the `$\<LF>` quoted-part flag member, one per spelling.
          - For the flush-comment member, one per entry its list above names, each by its container, `flush-comment-after-array-literal-closer` and `flush-comment-after-extglob-closer` included.
          - One for each agreement case above.
        - Each container and closer pair of Out of scope's below-floor item has an agreement case.
        - The flush-comment class's three boundary forms each have an agreement case.
  - `claude/.claude/hooks/tests/test_shell_syntax_tree_words.py`, one edit per item:
    - Every real-bash call moves onto the guarded helper.
    - Row 132's shapes and the fixture list's agreement cases, as one parametrized real-bash comparison under the precondition's rules.
    - The cut-residual pins and the extglob boundary cases of Verification 6. The RENAMED_FLAG pin asserts the word `-$F`, so a flag dropped outright fails it.
    - The `$\<LF>$` and `$\<LF>#` case of Verification 6.
    - The same-line `case` control of Verification 6.
    - The flush-comment bash check of Verification 6 (staff-sdet code-review round 6 R2). Its spaced half also asserts exit status 0 (staff-sdet code-review round 7 R3).
    - The real-bash half of Verification 6 for each HIDDEN member whose text bash runs directly (staff-sdet code-review round 7 R1).
    - Verification 6's divergence checks for the three members outside that half: the trailing-comment SHOWN member, and the funsub-extglob and `make` HIDDEN members. The test comment that says shfmt and bash read the trailing-comment member alike is corrected (staff-sdet code-review round 8 R1).
  - `claude/.claude/hooks/tests/test_shell_syntax_tree_contract.py`, one edit per item:
    - The `unknown-projection` bad-usage case drops its `["git-records"]` parameter, which PR 2 makes a valid projection. `["bogus"]` already covers an unknown name (staff-sdet round 15 R7).
    - The `.editorconfig` case is rewritten as Verification 6 gives it: a command whose result depends on the dialect, and a control that must differ (row 67, staff-sdet code-review round 5 R1).
    - Verification 6's cases, one kind per item:
      - The empty-forms premise case (staff-sdet code-review round 5 R3, plan-review round 18 R4).
      - The seven key-deletion cases (staff-sdet code-review round 5 R3).
      - The five-operator extglob cases (staff-sdet code-review round 5 R2).
      - The data-driven unknown-key cases over `NODE_FIELDS` (staff-sdet code-review round 5 R4, plan-review round 18 R5).
      - The four hand-built rejection cases (staff-sdet code-review round 5 R4).
      - The hand-built dropped-key pin (ciso-reviewer plan-review round 20 R2).
      - The `Lit.Value` deletion case on a non-empty `Lit` (ciso-reviewer plan-review round 21 R1).
    - The test constant that names the keys left out of `ALWAYS_PRESENT_KEYS` shrinks to the four exceptions, and its comment says why (row 24).
    - The premise comment lists `echo @()`, not the bare `@()` (staff-backend-engineer plan-review round 19 R6).
    - The comment-before-closer, funsub and brace-form corpus entries (staff-sdet code-review round 6 R1).
    - Verification 6's field-coverage test (staff-sdet code-review round 6 R1).
    - The `DIALECT_ONLY_FIELDS` premise, stated per entry as Verification 6 gives it (staff-sdet code-review round 7 R2).
    - The set of fields whose writer is `None` is asserted equal to `{IfClause.ThenLast}` (staff-sdet code-review round 8 R2).
    - `TestEmptyLitOverDeny`, Verification 6's pin of the empty-`Lit` over-deny. The staged class holds the heredoc shape, and this edit adds the extglob form `echo @(\<LF>)` (row 24, staff-sdet plan-review round 21 R1). Its docstring states the closure invariant: any closure must keep a missing `Value` on a non-empty `Lit` denying (ciso-reviewer plan-review round 21 R1).
  - Wording true in PR 1a, one site per item. Dispatch 2 widens each to the gates but the last, which its own item covers (staff-platform-engineer round 15 R3):
    - The report-header line in `claude/.claude/hooks/tests/conftest.py` says the shell-syntax-tree tests skip without shfmt.
    - The `_LIB_SHFMT_ARGV` comment in `_lib.sh`, and `production_shfmt_argv()`'s docstring in `helpers.py` with any test that pins it, say the argv is the one the module's tests run.
    - The module docstring's last paragraph drops "runs inside the gates".
    - The `flatten_word` docstring names no decision file, because `docs/design-decisions/tokenizing-gates-parse-with-shfmt.md` does not exist in PR 1a. It points at the `backslash-newline-` entries of the runners file's cut-residual fixture list instead. Dispatch 5, which creates the decision file, adds the pointer to it (ciso-reviewer round 17 R7).
  - The scratch table script gives status 3 to any input holding a carriage return, before shfmt, as `_lib_shell_parse` will (Verification 1).
  - `claude/.claude/hooks/shell-syntax-tree.py`, one code edit and no other (Design item 2, row 24):
    - `ALWAYS_PRESENT_KEYS` lists seven more keys: the six command-bearing body keys, `Block.Stmts`, `Subshell.Stmts`, `IfClause.Then`, `WhileClause.Cond`, `WhileClause.Do` and `ForClause.Do`, and `ExtGlob.Pattern`, which the extglob condition reads. The four exceptions stay out by name (row 24).
    - Beside that edit, the module docstring and the table's comment state the table's definition, its four exceptions and the `Lit.Value` caveat, and that a dropped key a valid command can omit is not detected (row 24, Design item 10).
    - The docstring names the rule the `Lit.Value` caveat breaks: the every-instance rule, and the sentence that a key a valid command can leave at zero is not listed. It does not point at "the first sentence" (staff-backend-engineer plan-review round 21 R3).
    - The docstring's sentence that a comment holds no command nodes adds that a `#` bash reads as part of a word can still hide what follows it. It states the mechanism, not a trigger list: a `#` with no whitespace after the end of a word part, such as a quote, an expansion, an extglob pattern or an array literal's closing paren, is a comment to shfmt and part of the word to bash, and its `Comment`'s `Hash` offset equals the preceding node's end offset (row 135, staff-backend-engineer code-review round 7 R3, ciso-reviewer code-review round 8 R1).
    - The docstring and comments follow three rules, one per item (staff-backend-engineer code-review round 7 R1-R4):
      - Declaration commands are named by a rule, the commands `-ln bash` parses to `DeclClause`, not by a closed list.
      - The module's own refusal takes one name throughout.
      - No module comment carries a plan-defined term, or points to a file that does not exist yet.
    - The staged extglob marker condition, the exit codes and the one-argument interface stand (row 128).
- Then the CI part, in the same dispatch (Design item 7, row 131), one file per item:
  - `.github/workflows/tests.yml`: the pin step and the version-report line. The pin step's comment is rewritten to Design item 7's comment spec, and its body gains that item's `--retry-max-time` bound, `--proto` flags, installed-file digest re-check, `CI_SHFMT_INSTALL_DIR` seam and resolved-path check. The 30-minute job cap at :34-43 stays until PR 1a's first CI run confirms or re-derives it (PR 1a's session steps).
  - Create `claude/.claude/hooks/tests/test_shfmt_floor.py` with Design item 7's CI checks but the pin-equals-floor check, which Dispatch 3 adds with the floor it reads.
  - `claude/.claude/hooks/tests/test_git_floor.py` drops its copies of the pin-step helpers and uses the ones Dispatch 1 adds to `claude/.claude/tests/helpers.py`, with no change to what it asserts. The move's design is the session's decision, made so that no second test file keeps a copy of a helper (`claude/.claude/CLAUDE.md` § "Engineering Judgment") [unverified]. The engineer kept it in PR 1a's scope (row 136). One copy and its replacement per item:
    - `_LOGGING_STUB` becomes `PIN_STEP_LOGGING_STUB`.
    - `_SUDO_STUB` becomes `pin_step_sudo_stub("apt-get", "apt-mark")`.
    - `_calls_to` becomes `pin_step_calls_to`.
    - `_pin_step()`'s id lookup and single-match assertion become a call to `ci_test_slice_step`, and `_pin_step_env()` reads the step through it, as `test_shfmt_floor.py`'s two wrappers do.
  - Reuse, one source per item:
    - `TestPinStepRunBody`'s stub pattern in `test_git_floor.py`, through the pin-step helpers in Dispatch 1's `helpers.py` bullet.
    - `ci_test_slice_job` in `helpers.py`, which `ci_test_slice_step` reads.
    - The pinned-git step's comment pattern in `tests.yml`.
- `code-file-size-exceptions.toml`: the `_lib.sh` and `helpers.py` rows' ceilings rise to their files' counts, and `test_shell_syntax_tree_contract.py` gains a "split pending" row (row 137).
  - The reason: `claude/.claude/tests/test_code_file_size.py` fails a file whose count differs from its row's ceiling. It also fails a file past the line limit with no row.
  - The edit fixes the failure PR 1a's first CI run showed. A later PR 1a commit that changes one of the three files re-syncs its row in that same commit (row 137).

### PR 1b — the redaction gates

PR 1b starts once PR 1a merges, on a new branch from the default tip ("Three PRs").

The order, one reason per step:
- Dispatch 2 comes first, because it wires the gates to PR 1a's module.
- Dispatch 3 follows Dispatch 2, because its shared shfmt check calls Dispatch 2's `_lib_shell_parse`.
- Dispatch 4 follows Dispatch 3, because the Cursor report calls Dispatch 3's shared check.
- Dispatch 5 runs last, because the renamed hook calls the same check and Dispatch 5 edits files Dispatches 3 and 4 edit.
- PR 1b opens after Dispatch 5. Each push to an open PR runs `/ready-for-review` first (`claude/.claude/CLAUDE.md` § "Pre-Handoff Review"), and a PR opened earlier would be reviewed without Dispatch 5's CHANGELOG, migration note and recovery entry, which the lockout makes required (row 6).

Session steps, one per item:
- Before Dispatch 2, the first PR 1b dispatch that edits a file with a row in `code-file-size-exceptions.toml`, put the file-size check to the engineer, because row 137's answer covers PR 1a alone. One part per item:
  - Whether the toml joins PR 1b's and PR 2's dispatch file lists, as a Critical-files addition. Until the answer, no dispatch prompt lists it.
  - The fix for each PR, the check's third remedy or its first, with the rowed and unrowed files row 137 names. The `_lib.sh` row's reason says the issue it names governs that file's ceiling, and whether that issue bounds PR 1b's raise is [unverified].
  - The session's proposal, marked as the session's: each dispatch re-syncs, at its end, the rows of the files it changed, and its `code-writer` makes the edit. Each dispatch ends with `select-tests.py`, which selects the size check for any changed `.py` or `.sh` path (`select-tests.py:1105-1116`), so a re-sync left to the PR's end leaves each earlier dispatch red.
  PR 1b's body records the answer in the engineer's words, with the question's wording as the session's. On a yes, each dispatch prompt of the two PRs lists the toml, and PR 1b's body, not this file, records the addition. An answer that moves code out instead changes the dispatches' files, so it stops the session, as an outcome that contradicts a row does.
- PR 1b's first commit past 400 changed lines meets `require-diff-size-prompt.sh` for its own branch, and the session asks as PR 1a's size step says, with PR 1b's projected size. The question also states that 656 of those lines are whole-file deletions, `split-command-words.py`'s 171 and `test_split_command_words.py`'s 485 (`Projected diff:`, row 134).
- Before Dispatch 4, settle row 98 from Cursor's hooks documentation.
- Before Dispatch 5, confirm row 101's quoted lines and row 15's two vendor lines on their pages, and record them in PR 1b's body.
- At PR 1b's first CI run, record the parallel leg's wall time beside PR 1a's, and confirm the 30-minute job cap at `tests.yml:34-43` against it or re-derive it in a fix-up commit. This is the PR whose gate suites start running shfmt and python3 for each command that reaches a parse, where the base ran `xargs -n1` (staff-platform-engineer round 15 R2).
- Before PR 1b merges, re-run the `words` table on PR 1b's head (Verification 1). Nothing committed carries the scratch script or its corpus across PR 1a's merge, so the session rebuilds both from Verification 1's spec.

**Dispatch 2 — wire the redaction gates.**
- `claude/.claude/hooks/_lib.sh`, one item per function (Design items 1 and 3):
  - `_lib_shell_parse` and `_lib_shell_syntax_tree_path`.
  - `_lib_shell_parse_failure_clause`. Its status-3 clause names invalid bash and a carriage return (row 118).
  - `_lib_shell_parse_deny_tail`, with its precedence rule.
  - `_lib_command_words_deny_reason`'s call to it, its unlinked lead, and its workaround sentence without the "multi-line or nested-quoted" wording.
  - The `_lib_command_words` cutover.
- `claude/.claude/hooks/shell-syntax-tree.py`: the docstring's two upstream guarantees (Design item 2) and the gate wording below. Its only other edit in PR 1b is Dispatch 5's `flatten_word` pointer.
- The wording Dispatch 1's amendment kept to the module, widened to the gates, one site per item:
  - The report-header line in `claude/.claude/hooks/tests/conftest.py`, and its unit case, which asserts presence and `shfmt` only and so needs no edit unless that changes.
  - The `_LIB_SHFMT_ARGV` comment in `_lib.sh`.
  - `production_shfmt_argv()`'s docstring in `claude/.claude/tests/helpers.py`, and any test in `claude/.claude/tests/test_stub_shfmt.py` that pins it.
  - The module docstring's last paragraph.
- Delete `claude/.claude/hooks/split-command-words.py` and `claude/.claude/hooks/tests/test_split_command_words.py`. PR 1b's body lists each splitter case with no counterpart in `test_shell_syntax_tree_words.py`, with its reason.
- Header comments: `claude/.claude/hooks/deny-escaped-backticks-in-pr-body.sh`, `claude/.claude/hooks/deny-pii-in-commits.sh` and `claude/.claude/hooks/deny-private-project-refs.sh`. Each replaces its splitter and `xargs` lines with one line: a parse failure denies with a reason that names the cause, and `docs/hooks.md` § "Gate deadlock recovery" gives the recovery. None lists the parse path's tools (row 84). The gates' code does not change.
- Tests under `claude/.claude/hooks/tests/`:
  - `test_lib_command_words.py`:
    - The carriage-return, non-UTF-8 and check-order cases of Verification 6, each carriage-return positive with its twin, and the backslash-`r` case.
    - The tail table of Verification 6 over `_lib_shell_parse_deny_tail`, the unlinked-lead case, and the cut-residual pins over the runners file's fixture list (row 128).
    - `_run_lib_helper_on_command` takes `str | bytes`, writes bytes with `write_bytes`, and takes an `env` override. Its `write_text` (`test_lib_command_words.py:74`) cannot write a lone 0xFF byte, so the raw-byte and locale cases need this path.
    - The shfmt status matrix, the status-distinctness check, the argv check, and the clause and deny-reason parametrizations at :555-572 extended to 2, 5, 6, 7, 8, 127, the cap kills and the default arm's unlisted statuses. The xargs fast-path cases go.
    - The pipe-status cases of Verification 6, under `set -uo pipefail` as the gates run.
    - The per-stage stderr cases, the python3-first order, and the zsh-only case of Verification 6.
    - The `timing` cap cases, with `write_scaled_timeout_shim` and `assert_cap_engaged` keyed by command: a hung shfmt, and a hung python3 behind a printing shfmt stub, each return the cap-kill status with empty stdout. The python3 hang case at :655-678 is retargeted to the second.
    - The real-shfmt invalid-shape cases of Verification 6, and the status-4 and both-tools-absent cases.
    - The old status-4 cases, such as the one at :324, re-pointed from the python3 shim to a stub shfmt whose tree holds no command.
    - Each tool-fault sentence cites a heading `heading_texts` (`helpers.py`) finds in `docs/hooks.md`, as `test_bash_floor.py:414-421` checks its citations.
  - `test_hook_alignment.py`: the module docstring at :36-55 and the bare-xargs docstrings at :113-118 and :1634-1635.
  - An existing expectation in `test_lib_command_words.py` or a gate test changes only after the engineer answers on Verification 1's table, and each change maps to a row of it.
  - `test_deny_pii_in_commits.py`, `test_deny_private_project_refs.py` and `test_deny_escaped_backticks_in_pr_body.py`: rename the xargs-specific cases. Per gate, add the missing-shfmt, unrecognized-tree, parse-failure-text, carriage-return and tree-then-nonzero-exit cases, and the shfmt-absent allow cases of Verification 6, which replace the xargs-specific python3-absent allow cases (`test_deny_private_project_refs.py:4583`, `test_deny_escaped_backticks_in_pr_body.py:322`).
    - The silent-python3 cases (`test_deny_pii_in_commits.py:1352`, `test_deny_private_project_refs.py:4511`, `test_deny_escaped_backticks_in_pr_body.py:299`) move to a stub shfmt whose tree holds no command, behind real python3, and assert the status-4 wording. A python3 stub that exits at once behind a shfmt that can still write races shfmt's SIGPIPE, so no case uses one outside the SIGPIPE cases of Verification 6.
    - One gate keeps a case on the SIGPIPE-exception outcome, and one gate runs the per-stage stderr case.
    - One gate runs the raw-0xFF payload case of Verification 6 through the raw-payload runner below. Its assertion message names jq's U+FFFD substitution as the premise. A jq that passes the byte through yields the status-3 wording and fails the case, and that failure is the intended trip.
    - The carriage-return case per gate takes the command shape and precondition Verification 6 names for that gate.
    - Row 123's prefilter-allow cases of Verification 6, one per gate, each pinning its header's line.
    - Verification 6's continued-flag twins, one allow and one deny per gate (row 132).
    - The `heredoc_substitution` callers keep their expectations: the three over-deny guards that assert an allow (`test_deny_escaped_backticks_in_pr_body.py:340-344`, `test_deny_pii_in_commits.py:1371-1376`, `test_deny_private_project_refs.py:4530-4535`) and the scan-deny cases that build a command with it stay as they are, because no cut guard denies the shape (row 128).
  - `_cursor_payloads.py`: `recorded_tool_paths` at :591 gains `shfmt` (Design item 8).
  - `test_cursor_adapter_gate_matrix.py`, only if its rows for the three redaction gates still fail.
  - `test_scaled_timeout_shim.py`, only if its exact-count assertions at :351-424 change with the two new capped calls.
- `claude/.claude/tests/helpers.py`:
  - Remove `xargs_is_gnu`, whose last callers go with `test_split_command_words.py` and Dispatch 2's test edits.
  - Add `run_hook_reason_for_raw_payload`, which writes a raw byte payload to the hook's stdin and returns the deny reason as `run_hook_reason` does. `run_hook` and its siblings serialize a `dict` through `json.dumps` with `text=True` (`helpers.py:622-626`), which cannot carry a raw byte.
- Reuse: `_lib_capped`, `_lib_status_consistent_with_cap_kill`, the readlink hop in today's `_lib_command_words_tokenizer_path`, the `build_path_without` and `write_prewarmed_stub` helpers that the worktree gate's python3-absent tests already use, and `write_scaled_timeout_shim` and `assert_cap_engaged` from the existing cap tests.

**Dispatch 3 — install, the shared floor and the shared shfmt check.**
- `claude/.claude/hooks/_config.sh`: the shfmt floor constants, `_shfmt_version_meets_floor` and `_shfmt_floor_status`, with a one-line comment naming `install.sh` and `_lib_shfmt_dependency_cause` as its callers, as the python3 floor's comment at :70 does (Design item 6). Dispatch 5 renames the hook and updates :70.
- `claude/.claude/hooks/_lib.sh`, one item per function or constant (Design item 12, row 110):
  - `_lib_shell_parse_probe`, with its mapping of 3 to 8.
  - The probe command, under Design item 12's constraints. It holds every command-holding type of Dispatch 1's child-position matrix and every `KNOWN_BINARY_OPERATORS` entry.
  - The probe's expected words.
  - `_LIB_SHELL_PARSE_PROBE_MISMATCH_STATUS`, and the clause for it.
  - `_LIB_SHFMT_BELOW_FLOOR_STATUS`.
  - `_lib_shfmt_dependency_cause`, with its two cap arguments.
- Create `claude/.claude/hooks/tests/test_lib_shfmt_dependency_cause.py`, which sources `_lib.sh` and calls the two functions directly. It holds the shared check's status matrix of Verification 6, so the hook and adapter tests keep one case per branch. Its probe-coverage case reads the command-holding types from the contract test's matrix table, so the two cannot drift.
- `claude/.claude/hooks/tests/test_scaled_timeout_shim.py`, only if its exact-count assertions at :351-424 change with the shared check's capped version call.
- `install.sh`: the `shfmt-floor-check` block, and the cap-tool warning at :1052 (Design item 6).
- `claude/.claude/hooks/tests/test_shfmt_floor.py`, which Dispatch 1 created: the pin-equals-floor check, and direct tests of the two `_config.sh` functions, run by sourcing `_config.sh`, over the version spellings of Verification 6.
- `claude/.claude/hooks/tests/test_git_floor.py`: `run_install_sh_in_tmp_repo` gains an optional shfmt stub that reports the floor by default, because the run's PATH is the stub directory plus `/usr/bin:/bin` (`test_git_floor.py:278`). `test_python_floor.py` imports it and needs no change, because the new parameter has a default.
- Reuse: `_python_version_meets_floor` and `_python3_floor_status` as the model, the git floor block at `install.sh:105-130`, and `run_install_sh_in_tmp_repo` and the INSTALL_TEST_FIXTURE extraction helpers in `test_git_floor.py`, imported rather than copied.

**Dispatch 4 — Cursor adapter parity (Design item 8).**
- `claude/.claude/scripts/cursor-adapter/cursor_adapter/core.py`, one edit per item:
  - `RECORDED_TOOLS` with `shfmt` last.
  - The shfmt check's fixed bash program, beside `PROBE_BASH_PROGRAM` (:219). The program takes the hooks directory and caps of half `PROBE_BOUND_SECONDS` as positional parameters.
  - `CHECK_ENTRY_TIMEOUT_SECONDS` at 12, with its comment at :23 rewritten.
  - The probe count in the comment at :25-26.
- `claude/.claude/scripts/cursor-adapter/cursor_adapter/tools.py`: the shfmt check's probe call through `run_probe`, and its stall text naming shfmt.
- `claude/.claude/scripts/cursor-adapter/cursor_adapter/check.py`: `tool_findings`, which runs the shfmt check only after python3 and bash pass their floors, reads the probe's result as Design item 8 says, and adds the `install`-and-relaunch sentence.
- `claude/.claude/scripts/select-tests.py`: `HOOK_HELPERS_RUN_BY_SCRIPTS_TESTS` (:49-51) gains `claude/.claude/hooks/shell-syntax-tree.py`, and its comment names the adapter's shfmt probe. The hooks' `.sh` files already select the scripts tests (`select-tests.py:640-641`, `:1023`), so `_lib.sh` and `_config.sh` need no row.
- `claude/.claude/scripts/tests/test_select_tests.py`, only if its path-fidelity tests need the new entry listed.
- `claude/.claude/scripts/tests/_cursor_install_helpers.py`: a shfmt stub in the test world's recorded tools.
- `claude/.claude/scripts/tests/test_cursor_adapter_install_prerequisites.py`: the worst-case budget case at :535-558 asserts that the recorded probe calls include the shfmt check's, by its program text, and number exactly four against 12 seconds. It also holds the shfmt cases of Verification 6.
- `claude/.claude/scripts/tests/test_cursor_adapter_install_roundtrip.py`
- `claude/.claude/scripts/tests/test_cursor_adapter_install_session_start.py`: the sessionStart report's shfmt findings, and the elapsed bound at :770, which reads the raised constant.
- `docs/cursor-adapter.md`, one edit per item:
  - The tools bullet at :117 gains a sub-bullet saying the report also runs the shfmt check, from `~/.cursor/` rather than the workspace, so a version manager that picks shfmt by directory can pass it and give a hook another build.
  - The shadowing sentence at :114-117 extends to shfmt's directory, and says a user-writable one, such as `go install`'s, is a trust decision.
  - In § "Limitations", the timeout line at :306 says 12 s.
- Reuse: `run_probe`, `find_tool`, `stall_text`'s wording pattern, `record_environment`, and Dispatch 3's `_lib_shfmt_dependency_cause`.

**Dispatch 5 — the renamed dependency check, and PR 1b's docs and records.**
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
- `claude/.claude/hooks/tests/test_hook_alignment.py`:
  - A test that every `docs/design-decisions/tokenizing-gates-parse-with-shfmt.md` § citation in a hook header names a heading `heading_texts` finds in that file, so a deleted or retyped heading fails CI. It covers PR 2's worktree-gate line with no edit.
  - The renamed hook, only if its registration or header checks need it listed.
- Header Known-gaps only: `claude/.claude/hooks/deny-escaped-backticks-in-pr-body.sh`, `claude/.claude/hooks/deny-pii-in-commits.sh` and `claude/.claude/hooks/deny-private-project-refs.sh` each gain the zsh, cut-residual, placeholder-decoy, prefilter, quoted-text and dropped-key lines. The cut-residual line names the flush-comment class. Each line cites its residual's heading in the decision file this dispatch creates (Design item 10, rows 123, 128). The cut-residual line is one line under the cooperative tier, worded as Design item 10's Known-gaps items say.
- `claude/.claude/hooks/tests/_shell_syntax_tree_runners.py`: the cut-residual fixture list's comment cites the decision file's cut-residual heading.
- `claude/.claude/hooks/shell-syntax-tree.py`: the `flatten_word` docstring adds a pointer to the decision file this dispatch creates, beside its pointer to the fixture list (Dispatch 1's amendment).
- `claude/.claude/tests/helpers.py` and `claude/.claude/hooks/tests/conftest.py`: `require_shfmt()`'s skip reason and the report-header line cite the new `README.md` § "Requirements" bullet in place of the pin in `.github/workflows/tests.yml` (Dispatch 1's amendment).
- `claude/.claude/tests/test_stub_shfmt.py`: `test_skips_outside_ci_naming_the_workflow_that_pins_the_build` matches the `README.md` § "Requirements" citation and is renamed for it, because it matches the PR 1a skip reason's `tests.yml` text and would fail on the edit above.
- `README.md`:
  - :116 names `check-hook-dependencies.sh`.
  - The `timeout` bullet at :115 gains the cap-tool sentence (Design item 9).
  - The line at :134.
  - A `shfmt` bullet in § "Requirements", which says the same hook warns at session start and gives the zsh note (Design item 9).
- `docs/hooks.md`:
  - § "Utility hooks": the bullet at :204, one edit per item:
    - It is renamed `check-hook-dependencies.sh` and covers both checks.
    - It gives the order, what the probe cannot catch, and that the silent cases and hazards listed in § "Python version" apply to both checks.
    - It cites § "Python version" for python3 and the recovery entry for shfmt.
    - Its registration switch now silences both checks.
  - § "Python version": the hook's name at :523 and :528.
  - § "Python version": the hazard bullets at :538-539 settle their working-directory and pre-trust premises from row 101's vendor lines, cited to the pages. The bullets then state these, one per sub-bullet:
    - Interactive sessions hold settings hooks until the trust dialog is accepted.
    - `claude -p`, the SDK and a trusted parent folder run them in a clone the user never reviewed.
    - The hazards apply to the shfmt version call and probe as well as to python3.
    - What stays unconfirmed (row 101).
    - A repository or one agent `Write` can set a pin file that makes a shfmt shim fail, citing `docs/security-hardening.md:346-351`.
  - § "Python version": the sentence at :551, which says each hook running python3 through `_lib_command_words` states its python3 failure in its header, a statement Dispatch 2's header edits make false (row 84). Its new wording names no gate, so PR 2 leaves it alone, and says these, one per item:
    - A hook that parses through `_lib_shell_parse` denies on any parse failure with a reason naming the cause.
    - § "Gate deadlock recovery" gives the recovery.
    - Each other stowed hook that runs python3 directly keeps the header duty.
  - § "Gate deadlock recovery": replace the :592 paragraph with PR 1b's part of the recovery entry (Design item 9).
- `docs/cursor-adapter.md` § "Limitations": the report bullet at :302-303 names `check-hook-dependencies` for both mentions, and its lead covers python3 and shfmt.
- `docs/memory-audit-nudge.md`: the flag-order bullet at :137-142 cites the deleted splitter's docstring. State that the parser finds `--body-file` in any position.
- `CHANGELOG.md`: an `[Unreleased]` entry with the behavior bullets and migration note Design item 9 lists. It says `check-python-floor.sh` is now `check-hook-dependencies.sh` and also checks shfmt.
- Create `docs/design-decisions/tokenizing-gates-parse-with-shfmt.md`.
- `docs/design-decisions/command-text-gates-accept-quoted-text-over-deny.md`
- Reuse: the hook's own `.source` filter, `_lib_jq` notice and exit-0 shape, the moved test file's rig, payload and registration helpers, Dispatch 1's `require_shfmt()` and stub-shfmt writer, Dispatch 3's `_lib_shfmt_dependency_cause`, and `TestNoRepositoryChosenTextReachesTheNotice` (`test_check_python_floor.py:336-356`) as the hostile-fixture pattern.

### PR 2 — the worktree gate and the evaluator

PR 2 starts once PR 1b merges, on a new branch from the default tip. Dispatches 6 and 7 run in sequence. One session step sits between them: put every row of Dispatch 6's table that changes a gate verdict, deny-to-allow and allow-to-deny alike, to the engineer. Dispatch 7 edits the moved cases' expectations only after the engineer answers (Verification 3). The dropped-key limit's worktree-gate consequence is already answered (row 24).

PR 2's first commit past 400 changed lines meets `require-diff-size-prompt.sh` for its own branch. The session asks as PR 1a's size step says, with PR 2's projected size (staff-platform-engineer round 13 R3).

**Dispatch 6 — the `git-records` projection and the differential table.**
- `claude/.claude/hooks/shell-syntax-tree.py`: add `git-records` with Design item 2's in-group rules, the carried-over classifiers, `SHFMT_ARGV`, `MAX_COMMAND_BYTES`, `FIELD_SEP`, and the projection's `PROJECTIONS` entry. `main`'s check order moves into one function, which `main` and the evaluator both call (Design item 2). The module docstring states the record grammar and both meanings of in-group.
- `git mv` `claude/.claude/hooks/tests/test_parse_git_command.py` to `claude/.claude/hooks/tests/test_shell_syntax_tree_git_records.py` as the dispatch's first commit, with no other edit.
  - Its moved cases keep testing `parse-git-command.py` through this dispatch, so no expectation changes before the engineer answers.
  - New test classes in the same file call `git-records` on real shfmt behind `require_shfmt()`: the realistic smoke set, and Verification 7's git-word, wrapper, placeholder and in-group cases, a `$HOME/bin/git push` case included.
- `claude/.claude/hooks/tests/test_ask_new_dependency_disclosure.py:4`: the docstring's citation of the renamed test file.
- `claude/.claude/hooks/tests/test_shell_syntax_tree_contract.py`:
  - The child-position matrix gains its `git-records` cells. Each cell's expected in-group, for a git write and for a `cd`, comes from Design item 2's rules in the fixture table.
  - The real-bash `cd` check of Verification 7, which tests the threaded cells against bash itself rather than against the rules that wrote them.
  - `_LIB_SHFMT_ARGV` equals `SHFMT_ARGV`, and `_LIB_SHELL_PARSE_MAX_BYTES` equals `MAX_COMMAND_BYTES`, each printed by sourcing `_lib.sh`.
- Deliverable to the session: the changed-case table. A scratch script outside the repository, which is not committed, runs old `build_records` against new `git-records` over these inputs:
  - Every moved case.
  - A compound matrix (comment-discipline-reviewer round 12 R2):
    - Its constructs: `{ }`, `time`, `!`, `if`, `while`, `until`, `for`, `select`, `case`, a subshell, a function body, a coprocess, a backgrounded statement, a pipe side, the right operand of `&&`, the right operand of `||`, a `;` after an `&&` list, a process substitution, an assignment value and a redirect target.
    - A command substitution and backticks, each quoted and unquoted.
    - Each construct is crossed with a `cd`, a git write, and a `cd` then a write.
    - The `cd` forms add `FOO=x cd`, `builtin cd`, `command cd`, `pushd` and `popd`.
  - Shapes bash and zsh read differently, each beside a git write: `=git push`, `cd old new`, an inline `#` comment, `rcquotes` quoting and a glob qualifier.
  - One input per member of Design item 10's cut-residual list, each holding `git push` in place of the source-flag command. Each row shows its verdict in all three columns. One rule or form per item:
    - Three members take named forms. The trailing-comment member is `cd <main> # c \<LF>git push`, the `$\<LF>(` member is `echo ${x:-$\<LF>(git push)}`, and the delimiter-is-a-command form takes `git push` as its delimiter and its second line.
    - The `$\<LF>` quoted-part flag member's input is the `-C` form `git -$\<LF>'C' /main push`. Its row counts as accepted only under the engineer's answer on it by name (row 129).
    - The flush-comment member hides the rest of a line, not a whole line, so its input is the worktree form a visible non-write head command gives it: `( echo "x"#; git push` with the `)` on a later line. shfmt's tree holds `echo "x"` alone, and bash runs both (staff-sdet plan-review round 18 R1). Its row shows as accepted by the engineer's answer for this gate, "Cut it there too (Recommended)" (row 135).
    - The flush-comment member takes a second row, for a hidden `cd` in a `case` arm: `cd <wt> && case x in x) echo "a"#; cd <main>` with `;; esac; git push` on a later line. The row gives its base verdict, a SENTINEL deny, and its new verdict in all three columns (ciso-reviewer plan-review round 20 R1). It shows as covered by "Cut it there too (Recommended)", the session's reading of that answer (row 135).
    - Every other deny-to-allow row among them is the accepted regression of row 129, and the session step shows it as accepted, not as a question.
  - Row 132's shapes. Each row says whether the new records follow bash's reading, and one that does not contradicts row 132 and stops the session.
  - The two empty-`Lit` shapes, each beside a read-only `git status`. Each is an expected allow-to-deny row, shown as the session's accepted over-deny (row 24).
- The table has one row per input whose records change, one rule per item:
  - Each row gives the old records, the new records, the reason, and the gate verdict each record stream yields under the consumer from `require-worktree-for-git-writes.sh:311` onward.
  - It gives both verdicts in three sessions: a main-tree one, a linked-worktree one holding its lock, and a linked-worktree one whose lock is absent (staff-platform-engineer round 11 R1).
  - Both verdicts follow Verification 3's order. The linked-worktree columns apply the prefilter and the fast path first, and the new column applies `_lib_shell_parse`'s text checks, the byte cap and the carriage return, before any records.
  - It marks every verdict change, deny-to-allow or allow-to-deny.
  - Each zsh-shape row also says whether the new records follow bash's reading or zsh's.
  - A comment PR 2's body links carries it (row 133).
- Every `cd` row is allow-to-deny or unchanged. A `cd` row that turns from deny to allow contradicts row 85, so the session stops and revises this plan. The cut residual's rows are the one exception, because row 129 accepts them.
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
- `claude/.claude/hooks/require-worktree-for-git-writes.sh` (Design item 4), its deny through `_lib_shell_parse_deny_tail`, the :273 widening and the header's added Known gaps included.
- `claude/.claude/hooks/evaluate-code-writer-self-review.py` (Design item 5), its `GitRecordsResult` and `DiffReread` carrier, the `Assessment.unparsed_rereads` field, and `run`'s withheld and credited log lines included.
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
    - Verification 7's carriage-return case: in a main-tree session, `git status` followed by a carriage return denies with the status-3 clause alone, and no file workaround.
    - Verification 7's cut-residual pins, its unlinked-module cases, and its continuation-split relocation and `git` pins (rows 105, 128).
  - `test_shell_syntax_tree_contract.py`: Verification 7's carriage-return parity test, beside Dispatch 6's argv and byte-cap pins.
  - `test_send_back_skipped_self_review.py`:
    - The `Workspace` fixture (:894-909) injects a fake builder by default, so the verdict matrix never spawns shfmt. A named handful of end-to-end cases run real shfmt behind `require_shfmt()`.
    - The loader-failure cases at :1825-1858, and the `PARSE_GIT_COMMAND_PATH` constant at :36, move to the new module's path and required names.
    - The known-gap test at :268-274 splits, as Design item 5 says.
    - The `runs_git_diff` cases run on an injected builder, plus a few real-shfmt cases.
    - The prefilter, exit-1, credit-verdict, other-rule-still-fires and argv cases of Verification 7 are added.
    - Verification 7's carriage-return cases, one per item:
      - `git diff` with a carriage return gives no credit and logs `reread-withheld-unparsed=carriage-return`, with an empty stub call log.
      - `git diff \<CR><LF> --stat`, as the transcript holds it, gives the same outcome, so no join removes the carriage return first.
      - An over-cap command holding a carriage return earns R5 credit and logs `oversize`.
      - A command holding `git diff` and a lone surrogate earns R5 credit and logs `parse-fault`.
    - Verification 7's continuation cases, on real shfmt behind `require_shfmt()`.
    - The fake builder the `Workspace` fixture injects returns `GitRecordsResult`, so the verdict matrix runs on the same carrier as the real closure (Design item 5).
  - `test_hook_alignment.py`: the `_SECOND_DIRNAME_SITE_HOOKS` entry at :2859-2861, which quotes the gate's `PARSER=` line.
  - `test_cursor_adapter_gate_matrix.py`, only if its worktree-gate rows fail.
  - `test_scaled_timeout_shim.py`, only if its exact-count assertions at :351-424 change.
- `docs/design-decisions/code-writer-self-review-send-back.md` § "Log verdicts": both new verdicts, `reread-withheld-unparsed` and `reread-credited-unparsed`, each with its reasons and its Degradation and Operator-action cells, and the amended note on one line per invocation (Design item 5).
- `docs/hooks.md` § "Gate deadlock recovery": PR 2's part of the recovery entry, the rollback order included (Design item 9).
- `CHANGELOG.md`: PR 2's line (Design item 9).
- `docs/design-decisions/tokenizing-gates-parse-with-shfmt.md` and `docs/design-decisions/command-text-gates-accept-quoted-text-over-deny.md`: PR 2's widening (Design item 10).
- Reuse: `_lib_shell_parse` and `_lib_shell_parse_failure_clause` from PR 1b, the stub-shfmt writer from Dispatch 1, and the `build_path_without` and `write_prewarmed_stub` helpers.

Projected diff: PR 1a about 2,500 changed lines, PR 1b about 4,150 and PR 2 about 2,850, about 9,500 in all (row 72). Row 134's answer was given at about 2,400, 4,100 and 2,850. The plan as first committed on this branch projected PR 1 at about 4,800 and PR 2 at about 2,750. The differential tables are scratch output and add no lines. Each bucket is named by its deliverable, and the dispatch it cites lists what it holds (comment-discipline-reviewer round 12 R5).
- This plan file, one fact per item:
  - Per the plan-it rule, the count leaves out this plan file.
  - The plan file ships in PR 1a, so its lines add to PR 1a's review surface, as the size step states.
  - Its length is about 3,000 lines.
  - With it, PR 1a's review surface is about 5,500 lines.
- The figures' sources, one per item:
  - The staged count is staff-platform-engineer's.
  - Every other figure is the architect's estimate. It starts from the previous revision's buckets, subtracts what row 128 cut, moves what row 131 moved, and adds the cut-residual pins, row 132's added shapes and the continued-flag twins.
- PR 1a's parts, one per item:
  - The staged module work, about 2,160. The staged diff holds 2,643 lines, by staff-platform-engineer round 10 R7's count, which round 11 R6 and round 14 R1 confirmed: 2,157 added and 486 deleted. Restoring `test_split_command_words.py` removes its 485 deleted lines.
  - The amendment's test edits (Dispatch 1), about 180: row 132's comparison over eight shapes, the guarded real-bash helper, the cut-residual fixture list and its pins, the extglob boundary cases, and the PR 1a wording.
  - The CI part (Dispatch 1), about 170: the pin step and version report, and `test_shfmt_floor.py`'s CI checks.
- PR 1b's parts, one per item:
  - The command-word and gate tests (Dispatch 2), about 1,030: the previous 1,400 less about 450 for the continuation, placement, extglob, interpreter, route-sentence and flipped-guard cases, plus about 80 for the continued-flag twins and the shared-helper pins.
  - The `_lib.sh` parse path (Dispatch 2), about 375: the new functions and the cutover, about 205 once status 11, the route sentence and the tail sentences go, and the 171-line deletion of `split-command-words.py` (staff-platform-engineer round 11 R6).
  - Deleting `test_split_command_words.py`, 485 lines.
  - The shared shfmt check, the renamed hook and the `_config.sh` floor (Dispatches 3 and 5), about 670: the previous 840 less about 50 of cut probe cases and about 120 of CI checks moved to PR 1a.
  - The Cursor port (Dispatch 4), about 410.
  - Install, header and doc text (Dispatches 2, 3 and 5), about 1,200: the previous 1,380 less about 140 for the deny-text rewords, the skill examples, the six CHANGELOG bullets and the cut recovery items, less about 50 for the pin step moved to PR 1a, plus about 10 for widening PR 1a's wording to the gates.
- PR 2's parts, one per item:
  - Deleting `parse-git-command.py`, 356 lines.
  - The `git-records` projection and its tests (Dispatch 6), about 950.
  - The gate and evaluator tests (Dispatch 7), about 1,010: the previous 1,210 less about 210 for the cut checks' cases and the byte-test half of the parity test, plus about 10 for the worktree gate's parametrized cut-residual pins.
  - The remainder (Dispatch 7), about 530: the gate's and the evaluator's code, header and doc text, less the cut byte test, catch, reasons and skill examples.
- The estimate counts each rename by its changed lines. If the hook's edits leave `check-hook-dependencies.sh` below git's default 50% rename similarity, the diff shows it as a delete and an add, about 100 lines more.
- No PR is under 400 changed lines. Rows 46 and 131 record how the engineer split the work, and row 134 the plan-time answer at the sizes it states, which PR 1a's size step cites and PR 1b's and PR 2's size steps put again (row 72).

## Verification

1. Dispatch 1 builds the `words` differential table from a run of the base commit's `_lib_command_words` against `shfmt` piped into the new `words` projection (row 108).
   - Its inputs, one group per item:
     - Every moved splitter case.
     - Every command string `_lib_command_words` receives while the three gates' suites and `test_lib_command_words.py` run on the base commit. A logging line added only in the scratch worktree captures them, so the corpus holds the commands the tests build at run time, not literals scraped from source.
     - `gh pr create --body "$(grep -F foo notes.txt)"`, and a `git commit -m` whose quoted `$(...)` holds `-F`.
     - A `gh pr create` and a `git commit`, each taking an unquoted heredoc whose body holds backticks around a command with a source flag.
     - Shapes bash and zsh read differently, each holding a source flag: an inline `#` comment such as `git commit -m x # -F /dirty.md`, an `=cmd` word, `rcquotes` quoting such as `'it''s'`, and a glob qualifier.
     - A carriage return before `#` and a source flag, such as `git commit -m x<CR># -F /dirty.md`.
     - One input per member entry of the cut-residual fixture list, each built on `git commit -F /dirty.md`. These rows follow that list and add no member of their own, one rule per item:
       - Each hiding member is expected to be a deny-to-allow row the engineer accepted, by row 128's selection for its five classes and by row 135's answer for the flush-comment class, the `$\<LF>` quoted-part flag member aside (rows 128, 129, 135).
       - The `$\<LF>` quoted-part flag member's two spellings are not yet accepted. Their rows go to the engineer by name with the base reading, not as accepted (row 129). The single-quoted spelling's base reading on BSD `xargs` is already run, and holds no `-F` (row 129).
       - The `$\<LF>` quoted-part flag member also gets one input in the worktree gate's form, `git -$\<LF>'C' /main push`. The old column runs the base `parse-git-command.py` on it, the worktree gate's base reader, beside the base `_lib_command_words`.
       - The trailing-comment member's flag and path stay in the words, so its verdict is expected unchanged for the redaction gates.
       - The extglob member's `$(` form is a deny in both columns, through the staged strict check.
     - Row 132's shapes. A row for one shows a change from the base's reading, and its new words must equal bash's (row 132).
     - The two empty-`Lit` shapes, each beside a source flag. Each is an expected allow-to-deny row, shown as the session's accepted over-deny, not as an engineer acceptance (row 24).
   - Dispatch 1's new column gives status 3 to any input holding a carriage return, rather than piping it to shfmt. That is the scratch script's rule, because `_lib_shell_parse` does not exist yet (row 118).
   - The moved splitter case holding the byte 0xFF shows new status 3, and its row notes that a gate receives that byte as U+FFFD (row 113).
   - A table built before the scratch script had its carriage-return rule, or before the 0xFF note, is rebuilt before its rows go to the engineer. A table built with the cut status-11 rule is rebuilt too.
   - The old column runs under GNU `xargs`, which CI and Linux consumers run, and under BSD `xargs`. The table names both builds and marks every row whose old status or old extraction differs between them. When one build is not reachable, the table says so, and PR 1a's body names the build the old column lacks.
   - The table has one row per input whose status or extracted path strings differ. Each row gives the old and new words and status, the source paths each gate's extraction returns from each stream, and the verdict each yields with every extracted path a missing file, so any path denies.
   - It marks every verdict change, deny-to-allow and allow-to-deny, and every row whose path strings differ while the modeled verdict does not. Each zsh-shape row also says whether the new words follow bash's reading or zsh's.
   - After Dispatch 1 and before PR 1a's first push, the session puts every marked row to the engineer. PR 1a's body carries the answer, with the table in a comment it links (row 133). Dispatch 2 changes an existing expectation only per that answer, each change mapping to a row, and PR 1b's body quotes the answer and links that comment.
   - The cut residual's rows go with one plain sentence: they are deny-to-allow regressions the engineer accepted with "Yes, cut them (Recommended)" (row 128), or for the flush-comment class with "Cut it, record as gap (Recommended)" (row 135), shown so the engineer sees each one, not asked again. The `$\<LF>` quoted-part flag member's rows are the exception, put as a question by name (row 129).
   - Any other deny-to-allow row reaches the engineer through that step as a question. `docs/hooks.md:26` makes it a regression, which listing it as a known gap in the same change cannot legalize.
   - Before PR 1b merges, the session re-runs the table on PR 1b's head, taking the new column from the real `_lib_command_words`, and records the date and head commit in PR 1b's body. It rebuilds the scratch script and the corpus from this item's spec, because nothing committed carries them across PR 1a's merge. A newly marked row goes to the engineer the same way.
   - The table notes, per row, whether its new status came from the scratch script's rule or from the real `_lib_command_words`.
   - A row the engineer rejects stops the session, which revises this plan and re-runs `/plan-review`.
2. Dispatch 1's shape dump, its first step, settles rows 26 and 113 on the session's shfmt.
   - Before it ends, it runs row 118's premise case and the widened real-bash comparison of Verification 6.
   - PR 1a's body records which row-26, row-86, row-113 and row-118 items held, and what changed where one did not.
   - A row-118 item that did not hold stops the session before Dispatch 2, as Critical files describes.
   - Dispatch 1's amendment runs row 132's precondition before any other edit, and a difference stops the session.
   - PR 1a's body records the form each dumped shape took, provisional on the session's build until CI's first run settles it (Critical files).
3. Dispatch 6 builds the changed-case table from a differential run of old `build_records` against new `git-records`, over the moved cases, the compound matrix of every `cd` shape and container, the zsh-differing shapes, the cut residual's members and row 132's shapes (Dispatch 6). Each row gives both verdicts in each of three sessions: a main-tree one, and a linked-worktree one with its lock held and with it absent. Each zsh-shape row says whether the new records follow bash's reading or zsh's.
   - Every `cd` row is allow-to-deny or unchanged. A `cd` row that turns from deny to allow stops the session, which revises this plan and re-runs `/plan-review`. The cut residual's rows are the one exception, because row 129 accepts them.
   - The new column applies `_lib_shell_parse`'s order before it builds records (staff-platform-engineer round 10 R2):
     - The byte cap gives status 7 and a carriage return status 3, each with no records and no shfmt run (row 118).
     - Every other input runs through real shfmt and the module.
     - So the moved `git\r--version` case at :307 is an allow-to-deny row wherever the gate parses it.
   - Both linked-worktree columns apply the gate's prefilter at :223 first, in both builds (staff-platform-engineer round 11 R1):
     - With the lock held, the fast path at :273-279 then decides. A command it lets through unparsed is allow in both builds there, so that column marks no change for it.
     - With the lock absent, the fast path skips its exit at :278, so every command holding a contiguous `git` reaches the parser, as in the main-tree column. A row whose two linked-worktree columns differ shows a verdict that depends on the lock state.
   - The cut residual's inputs show their verdict in all three columns, one class per item:
     - The heredoc classes are expected unchanged, because the base parser dropped every heredoc body.
     - A continuation member the base denied shows as the accepted regression of row 129.
     - The `$\<LF>` quoted-part flag member's `-C` row counts as accepted only under the engineer's answer on it by name.
     - The flush-comment member's rows, the hidden write and the `case` arm's hidden `cd`, show as accepted by the engineer's answer for this gate, "Cut it there too (Recommended)" (row 135).
   - After Dispatch 6, before any moved expectation changes, the session puts every verdict-changing row, deny-to-allow and allow-to-deny alike, to the engineer.
   - Dispatch 7 edits the moved expectations only after the answer, each edit mapping to a row. PR 2's body carries the engineer's answer, with the table in a comment it links (row 133).
4. After each dispatch, run `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py`. After Dispatches 2, 3 and 7, also run `test_scaled_timeout_shim.py` by name.
   - Dispatches 1 and 2 edit `claude/.claude/tests/helpers.py`, and Dispatch 4 edits `select-tests.py` itself, both in `GLOBAL_TRIGGER_PATHS` (`select-tests.py:562-566`, `:1102`). So every dispatch-end run and every `/ready-for-review` run in PR 1a and PR 1b is the full suite, and that run is then the documented one.
   - PR 2's dispatches edit no path in that set, so PR 2's runs select by domain.
5. In each PR, lint with `scripts/venv-run.sh ruff check claude/.claude/ claude-skills/ plugins/ evals/` and `scripts/list-shell-files.sh | xargs -0 scripts/venv-run.sh shellcheck`.
6. PR 1a's and PR 1b's suites must contain these cases, and they must pass. The two module groups and the "Install and CI" group's pin-step cases land in PR 1a, and every other case lands in PR 1b.
   - **Module, with real shfmt behind `require_shfmt()`:**
     - Each of the nine residual shapes projects to the words bash sees.
     - Each attached form keeps its prefix and yields a path holding the placeholder, which its extractor hands to the caller's deny. The forms are `--body-file=`, `--template=`, `-F=`, `-T=`, `--file=`, `--input=`, and `-f`, `-F`, `--field` and `--raw-field` with `key=@`. Each is crossed with a parameter, a command substitution, an arithmetic expansion, `$'...'`, and double quotes holding an expansion.
     - Every `KNOWN_NODE_TYPES` entry has a conformance case. Every corpus tree passes the strict check and the `words` projection through the module's command line. The completeness test fails on an entry with no case, and on a corpus `Type` missing from the set.
     - The field-coverage test: the `NODE_FIELDS` fields of structs shfmt encodes for bash, less the fields some corpus tree holds, equal the named `DIALECT_ONLY_FIELDS` set. The equality also fails when a listed field gets covered. The corpus holds comment-before-closer, funsub and brace-form entries for the fields only those shapes reach (staff-sdet code-review round 6 R1, plan-review round 21 R3).
     - The `DIALECT_ONLY_FIELDS` premise, stated per entry: each entry names the dialect, or the `--filename` input, whose tree writes it. `IfClause.ThenLast` is written by none of the dialects tried, so its entry says no writer was found, though the Go struct holds the field (staff-sdet code-review round 7 R2). The set of fields with no writer is asserted equal to `{IfClause.ThenLast}`, so a new one is a deliberate edit (staff-sdet code-review round 8 R2).
     - `TestEmptyLitOverDeny` pins both shapes, each through real shfmt and the module's command line (row 24, staff-sdet plan-review round 21 R1):
       - An unquoted heredoc whose body holds a line-ending backslash continuation followed directly by an expansion.
       - The extglob form `echo @(\<LF>)`.
       - For each, shfmt exits 0, and the module exits 5 with the diagnostic `a Lit object lacks the key Value`.
       - The case flips when a closure of the over-deny lands, or when shfmt starts writing an empty `Value`. Any closure must keep a missing `Value` on a non-empty `Lit` denying (ciso-reviewer plan-review round 21 R1).
     - The `Lit.Value` deletion case, independent of the table: in a real tree, `Value` deleted from a non-empty `Lit` exits 5. The case names the key itself, so it survives any change to `ALWAYS_PRESENT_KEYS` (ciso-reviewer plan-review round 21 R1).
     - Each `BASH_REJECTED_NODE_TYPES` entry has a sample that real shfmt rejects with exit 1 under `-ln bash`.
     - For each type that can hold a command, `gh pr create --body-file /y` in each child position surfaces in `words`. Every `KNOWN_NODE_TYPES` entry is in the matrix or in the named set of types that hold no command.
     - The realistic smoke set, as staged (`test_shell_syntax_tree_words.py:395-401`), exits 0 through `words`: `gh pr create --title t --body "$(cat <<'EOF'` with a multi-line body, `git commit -F - <<'EOF'`, an `&&` chain, a `for` loop and a `[[ ]]` guard. The gates still deny the commit's `-` as a pseudo-file, which the gate cases pin.
     - Row 132's shapes and the fixture list's agreement cases each match real bash under the precondition's rules, compared live through the guarded real-bash helper, so CI holds them to its own bash and shfmt (Dispatch 1's amendment).
     - The cut-residual pins, over the runners file's fixture list's member entries, one case per member entry. Each exits 0 and shows its entry's stated outcome in `words`, one outcome per item:
       - HIDDEN: `-F` and `/dirty.md` are absent. A flush-comment entry whose visible part is a command, and the ANSI-C and locale delimiter entries, also hold their head words in one command: `git`, `commit` and `-m` for the flush entries, `cat` for the delimiter entries (Dispatch 1's amendment, staff-sdet plan-review round 21 R3).
       - SHOWN: the trailing-comment member's `-F` and `/dirty.md` are present in one command.
       - RENAMED_FLAG: the words hold `-$F` and `/dirty.md` in one command, with `-F` absent.
     - What the pins do and do not establish, one per item:
       - A case that fails on its first run shows its entry wrong, which stops the session (Critical files).
       - These pin shfmt's reading on CI's build.
       - Real-bash checks below run members under bash: the flush-comment bash check, the real-bash half for every other HIDDEN member whose text bash runs directly, and the trailing-comment SHOWN member's check.
       - The funsub-extglob member needs bash 5.3, which no CI leg runs, and the member fed to `make` is not run by bash directly. Each asserts instead that its fixture text holds the flag-and-path line, taken from the constant the fixtures use, so a fixture that no longer holds the line fails (staff-sdet code-review round 8 R1).
     - `echo $\<LF>$ x $\<LF># y` projects `$$` and `$#`, each keeping its `$`, where bash expands them, so the gates over-deny rather than miss (Design item 10).
     - The same-line `case x in x) git commit -m "x"# -F /dirty.md ;; esac` makes real shfmt exit 1, the flush-comment class's control that denies. Its no-`#` twin exits 0 and projects `-F` and `/dirty.md` in one command, both on the production argv, so the flush `#` is shown as the cause (ciso-reviewer plan-review round 19 R3; staff-sdet plan-review round 20 R2).
     - The flush-comment bash check: for each flush-comment member, real bash through the guarded helper, under `env -i` with an empty `PATH`, gives the flush form's text different words from its spaced form's. bash prints `-F` and `/dirty.md` for the flush form, so each pin records a divergence and not a plain comment (staff-sdet code-review round 6 R2). The spaced form also exits 0, so a spaced text bash cannot parse fails the check, and for the head-word members it makes the visible `commit -m` call (staff-sdet code-review round 7 R3). The array-literal-closer member is among the flush members. The check is held to the bash on CI's PATH. Its evidence is bash 5.3.20 and 3.2.57, the latter an observation only, and 5.2.x stays [unverified] until PR 1a's first CI run. A failure on its first run takes the pins' first-run rule above (staff-sdet plan-review round 21 R2).
     - The real-bash half for the other members: for each HIDDEN member whose text bash runs directly, the bash on PATH, through the guarded helper under `env -i` with an empty `PATH`, makes the `-F /dirty.md` call while the module hides it. For the SHOWN `delimiter-quoted-in-a-non-last-part` member, bash makes no such call, the over-show direction. No deny is wanted, and a first-run failure takes the same rule (staff-sdet code-review round 7 R1).
     - The trailing-comment SHOWN member: shfmt and bash do not read it alike. The module projects one command, `cd /x` with the flag and path, while bash runs two, `cd /x` and then the tool call. So the module side asserts the command holding `-F` and `/dirty.md` has head `cd`, and the bash side asserts bash makes the tool call as its own command (staff-sdet code-review round 8 R1).
     - `[[ x == @($x|b) ]]` and `[[ x == @(${x}|b) ]]` exit 0, so a parameter expansion in an extglob pattern stays outside the strict check's markers and an over-wide marker fails a case [verified: both exit 0 on the staged module, staff-sdet round 15 R4].
     - An empty command, and a comment-only command that mentions `git`, each exit 0 and pass the strict check.
     - Each backslash form yields the word bash sees, one case per form:
       - An unquoted `\-F /y` yields `-F` and `/y`.
       - An unquoted `\a` yields `a`.
       - Inside double quotes, `"b\"c"` yields `b"c`.
       - Inside double quotes, `"\$x"` yields `$x`.
       - Inside double quotes, `"\a"` keeps its backslash.
     - Over a generated set of literal-only words, the module's words equal what real bash prints for the same text through `printf '%s\0'`. The set places backslashes unquoted, inside double quotes and in mixed words, and covers `\\`, an escaped backtick inside double quotes and a backslash before a multibyte character. It keeps the staged set's backslash-newline, because the module now receives one. Its text holds no `$`, backtick, glob character or brace that a backslash does not escape, and no leading `~`, so bash expands nothing.
       - The set also places each character of a wider domain at four positions: mid-word, at a word's start, at its end, and just before a `#`, as in `x<c># -F /y`. A character shfmt reads differently from bash then fails the comparison (row 118).
       - The domain is every code point from U+0001 through U+00FF outside bash's syntax set, and every code point in the Unicode categories Zs, Zl, Zp and Cf.
       - Bash's syntax set here is its metacharacters, quotes, `\`, `$`, backtick and `#`, the glob and brace characters the set already leaves out, and the carriage return, which `_lib_shell_parse` denies.
       - This part guards no current defect. It is a tripwire against a shfmt build that reads one of these characters differently, and CI's pinned build is the only build it is held to.
     - With the module's text streams patched in-process to latin-1, a word holding a multibyte UTF-8 character projects to its UTF-8 bytes, from escaped and raw JSON alike. That case is the encoding pin, because CPython runs `LC_ALL=C` with UTF-8 stdio, so a C-locale run cannot show a text-mode stdio. Its subprocess twin, under an installed locale whose stdio is not UTF-8, skips when `locale -a` lists none, as on CI.
     - A non-UTF-8 byte in a word, a comment or a heredoc body makes real shfmt exit 1 with no tree (row 113). The case asserts the exit and the empty stdout, not shfmt's stderr text.
     - `production_shfmt_argv()` holds `-ln`, `bash` and `--to-json`.
     - A word holding U+FFFD, the character jq writes for such a byte, projects to its three UTF-8 bytes (row 113).
     - Real shfmt puts the flag and path of `echo x<CR># -F /dirty.md` inside a `Comment`, and real bash prints `x<CR>#`, `-F` and `/dirty.md` as three words. The case pins row 118's two premises.
     - Under `production_shfmt_argv()`, a leading `#!/usr/bin/env bats` or `#!/bin/sh` shebang does not change the dialect, and each case's control, the argv without `-ln bash`, shows that the shebang otherwise would.
     - Under `production_shfmt_argv()`, a working directory holding an `.editorconfig` with another `shell_variant` yields the tree a clean working directory yields, for a command whose result depends on the dialect, a process substitution. It is the tripwire for a shfmt that begins reading the file for stdin, because the argv-equality test names no `.editorconfig` consequence (row 67). Its control, one fact per item (staff-sdet code-review round 5 R1):
       - The control runs `--filename x.sh` without `-ln bash` in the hostile and the clean directory, and asserts the two results differ by exit status or stdout.
       - A control that does not differ fails under `GITHUB_ACTIONS` and skips only locally, so the case cannot pass vacuously.
     - The premise case: each empty form row 24 lists, one group per added key, makes real shfmt exit 1 under `production_shfmt_argv()`. It keeps the seven added keys non-omittable on CI's build. The extglob form is `echo @()`, in argument position. The case pins each form's exit 1, not the error text (row 24).
     - For each of the seven added keys, `ExtGlob.Pattern` included, a real tree with that key removed exits 5, in the style of the staged per-key case. Each asserts the diagnostic names the missing key (row 24).
     - Data-driven over `NODE_FIELDS` less the structs no corpus tree encodes, which the staged test already names, a seeded unknown key on the first corpus instance of each struct exits 5. The seeded key is the staged `CANARY`, so no key text can appear in the message by accident (staff-sdet plan-review round 20 R3). Each asserts the exact diagnostic `a <struct> object has an unknown key` for the struct it seeded, taken from the parametrization, and that the key's text is absent from stderr. The module names the struct and the condition, never the key, as the staged canary test requires (staff-sdet code-review round 5 R4, plan-review round 18 R5, round 19 R2).
     - The extglob deny under each of `?(`, `*(`, `+(`, `@(` and `!(`, with one marker in one position, exits 5 with empty stdout and runs nothing (staff-sdet code-review round 5 R2).
     - Each real-bash call in the two new test files goes through the runners file's one guarded real-bash helper, and each shfmt run through the shared `run_shfmt` helper. Both run under a 60-second hang guard (staff-platform-engineer round 10 R6). Its one-line comment says no vendor value applies and that the guard only ends a hung run, far above a real run's length.
     - The real-bash cases run the bash on PATH, and each failure message names its `bash --version` line. CI's bash is the build the cases are held to. It is bash 5.2.21 on `ubuntu-24.04`, by staff-sdet round 11 R4's reading of `tests.yml:28`, unverified until PR 1a's first CI run.
   - **Module, with no shfmt:**
     - A hand-built tree exits 5 for each of these:
       - An unknown type.
       - A `BASH_REJECTED_NODE_TYPES` type.
       - An unknown `BinaryCmd` operator.
       - An unknown key.
       - A missing always-present key.
       - A renamed `Args`.
       - A renamed `Background`.
       - A renamed `Dollar` on `SglQuoted`.
       - A renamed `Dollar` on `DblQuoted`.
       - A conservation mismatch.
       - An `ExtGlob` pattern holding `$(`, a backtick, `<(` or `>(`, as staged, with its clean-pattern twin exiting 0.
     - On hand-built trees, one case each exits 5: a null where a scalar belongs, a non-string `Type`, a position with an extra key, and a `Pos` that is not a position. Each asserts the diagnostic names the intended condition, not exit 5 alone (staff-sdet code-review round 5 R4, plan-review round 18 R5).
     - A hand-built tree with an omittable key removed from a statement holding a git write exits 0 and projects no words. PR 2 extends the case to `git-records`, which yields no records. The case is labeled as pinning the header's dropped-key line, and it flips when the gap closes (ciso-reviewer plan-review round 20 R2).
     - The staged bad-usage cases (`test_shell_syntax_tree_contract.py:287`) exit 2 and print nothing on stdout, and they include a second argument, so the module stays one-argument.
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
     - One table keyed by status runs `_lib_shell_parse_deny_tail` under both WORKAROUND values, asserting the named tail present and the others absent:
       - 3 and 7: the file workaround under `with-file-workaround`, and nothing under `without-file-workaround`.
       - 4: nothing under either value.
       - The cap kills, 2, 5, 6, 8, 9, 127 and the unlisted 1, 126 and 139: the tool-fault sentence under either value.
       - The module not linked, at 3, 7 and each status above: the tool-fault sentence alone under either value.
     - For one status per row of that table, `_lib_command_words_deny_reason` carries the tail `_lib_shell_parse_deny_tail` prints under `with-file-workaround`.
     - With the module unlinked, `_lib_command_words_deny_reason` at 3 and 7 leads with "could not be checked", carries the not-linked clause and the tool-fault sentence alone, and holds no file workaround (staff-platform-engineer round 11 R2).
     - No clause holds the tool-fault sentence, the word "gate" or a citation.
     - The clauses for 2 and 127 and the default clause name awk.
     - Each tool-fault sentence cites a heading that exists in `docs/hooks.md`.
     - With real shfmt, an unbalanced quote, an unclosed `$(`, an unclosed backtick, and an unterminated heredoc if Dispatch 1's dump shows shfmt rejects it, each return status 3 through `_lib_command_words`. Each deny reason carries the invalid-bash clause and the file workaround.
     - With real shfmt, a comment-only command returns status 4 with its own wording and no workaround.
     - Through `_lib_command_words` with a stub shfmt, two cases pin the header's dropped-key line and flip when the gap closes (ciso-reviewer plan-review round 20 R2):
       - A tree with a partial drop returns the command's other words and not the flag.
       - A tree with a whole-command drop returns status 4.
     - With real shfmt, the zsh-only `echo ${(f)x}` returns status 3 through `_lib_command_words`, pinning row 106's residual.
     - With real shfmt, a command holding a non-UTF-8 byte returns status 3 through `_lib_command_words` (row 113).
     - `deny-escaped-backticks-in-pr-body.sh` denies `gh pr create --title t --body-file - <<'EOF'` with its pseudo-file reason, not a parse-failure reason. So the parse passes a top-level heredoc, and the pseudo-file check still decides it.
     - The same gate allows `gh pr create --title t --body-file <file>` with the same body in a clean file at a literal path under the test's temp directory, outside `$HOME`.
     - With real shfmt, each redaction gate has an allow and a deny twin of one multi-line command whose source flag stands alone on a continuation line (row 132). The allow names a clean file and the deny a file holding the gate's trigger, so the deny shows the extractor read the continued flag. Each file sits at a literal path under the test's temp directory, outside `$HOME`. One gate per item:
       - `deny-pii-in-commits.sh`: `git commit \`, then `-F <file>` on the next line, inside a work tree. The deny's file holds a PII token.
       - `deny-private-project-refs.sh`: row 132's `gh api` shape with `-F body=@<file>` alone on one of its continuation lines. The deny's file holds a tracker ID the gate denies.
       - `deny-escaped-backticks-in-pr-body.sh`: `gh pr create --title t \`, then `--body-file <file>` on the next line. The deny's file holds an escaped backtick.
     - Each redaction gate allows a command whose gated word or subcommand a continuation splits, pinned as its header's prefilter known gap (row 123), one gate per item:
       - `deny-pii-in-commits.sh`: `git \<LF>commit -F /dirty.md` inside a work tree.
       - `deny-private-project-refs.sh`: the same command, with a non-empty staged diff.
       - `deny-escaped-backticks-in-pr-body.sh`: `gh \<LF>pr create --body-file /dirty.md`.
     - With real shfmt, through `_lib_command_words`, one case per member entry of the runners file's cut-residual fixture list returns the status and words the entry states, such as status 0 with no `-F` word for a hiding member. The list's comment names the decision file's cut residual, so closing a member flips a named case (row 128).
     - The carriage-return check, with a stub shfmt that prints a valid tree and exits 0, so a status 3 can come only from the check (row 118):
       - Each positive returns status 3 through `_lib_command_words` and leaves the stub's call log empty, and its deny reason carries the status-3 clause and the file workaround. Status 3's clause is one fixed string, so each positive's twin below is the case's discriminator, not the clause text (staff-sdet round 14 R7).
       - The positives, one per item:
         - A carriage return before `#`, as in `git commit -m x<CR># -F /dirty.md`.
         - A CRLF line ending.
         - A carriage return inside single quotes.
         - A carriage return inside a heredoc body.
       - Each positive's twin differs only in that byte: a space in its place, or for the CRLF case a bare LF line ending. Each twin returns status 0 and leaves one stub call whose stdin equals the twin.
       - A command holding the two characters backslash and `r`, as `tr -d '\r'` does, returns status 0 with one stub call.
     - The carriage-return check's order and bytes:
       - An over-cap command holding a carriage return returns 7.
       - With python3 and shfmt both off PATH, a command holding one returns 3.
       - A command holding the byte 0xFF then a carriage return returns 3 and leaves the stub's call log empty. It runs under the locale `helpers.installed_locale_where` gives for the condition `! [[ $1 =~ $'\r' ]]` over a probe argument holding the raw byte 0xFF then a carriage return. That is a locale where an unpinned regex test misses the carriage return.
     - Each redaction gate denies, with the status-3 wording, a payload command whose source flag follows a carriage return and `#`. Each case uses the shape and precondition under which that gate reaches its parse, one gate per item:
       - `deny-pii-in-commits.sh`: `git commit -m x<CR># -F /dirty.md` inside a work tree. Its parse at `:496` runs for every `git commit`, so no staged change is needed.
       - `deny-private-project-refs.sh`: the same `git commit`, with a non-empty staged diff, because its parse at `:644` runs only inside the `if [ -n "$STAGED_DIFF" ]` block at `:625`.
       - `deny-escaped-backticks-in-pr-body.sh`: `gh pr create --title x<CR># --body-file /dirty.md`, its only shape, which reaches the parse at `:106`.
     - One gate's payload holds a raw 0xFF byte inside a `-F` path, sent through the raw-payload runner (Dispatch 2). The gate parses the command, because jq hands it U+FFFD, and denies with the unreadable-path wording, not the status-3 clause (row 113). A jq that passed the byte through would fail the case, the intended trip.
     - With both python3 and shfmt off PATH, `_lib_shell_parse` returns 127 for a command that passes the cap and carriage-return checks, and each gate's deny names python3.
     - Marked `timing`, a hung shfmt stub and a hung python3 behind a printing shfmt stub each return a cap-kill status with empty stdout, and `assert_cap_engaged` with a production cap of 5 shows the default cap acted on that command.
     - A stub shfmt that prints a tree with an unknown type makes each of the three gates deny with the shape wording.
     - With shfmt off PATH:
       - Each of the three gates denies a command it parses, with the stop-and-ask wording that cites the recovery entry and carries no file workaround.
       - Each gate allows a command it does not parse, such as `gh pr view` or `ls`.
       - `deny-private-project-refs.sh` allows a `git commit` with an empty staged diff, and `deny-pii-in-commits.sh` denies it (row 20).
     - A parse-failure deny reason holds none of the command's text and none of shfmt's stderr.
     - A marker written to stderr by a stub shfmt, by a stub python3, and by a module that crashes appears in neither the stdout nor the stderr of `_lib_command_words`, nor of one gate's run.
     - The three gates' silent-python3 cases use a stub shfmt whose tree holds no command, behind real python3, and deny with the status-4 wording.
     - The size cap, under the locale `helpers.installed_locale_where` gives for a condition that holds only where `${#1}` counts characters, such as `[[ ${#1} -eq 1 ]]` over one two-byte character:
       - One word of 32,768 two-byte characters (65,536 bytes) reaches shfmt.
       - One word of 32,769 denies with the size wording.
       - The oversize deny leaves a stub shfmt's call log empty.
       - The oversize check runs before the missing-shfmt check.
       - One boundary case enters through a gate's JSON payload.
     - The python3-absent cases now deny single-line commands too, without the file workaround.
     - Every `docs/design-decisions/tokenizing-gates-parse-with-shfmt.md` § citation in a hook header names a heading in that file, and a retyped heading fails the test (Dispatch 5).
   - **Shared shfmt check, `test_lib_shfmt_dependency_cause.py`:**
     - Behind `require_shfmt()`, with real python3, the probe passes, and `_lib_shfmt_dependency_cause` prints nothing and returns 0.
     - Behind `require_shfmt()`, with real python3, `_lib_shell_parse_probe 5` returns 0.
     - The probe command the check sends, captured from a stub shfmt's stdin log, is that log's one parse call.
     - Parsed with real shfmt under `production_shfmt_argv()`, the probe exits 0 through the module's `words`. It holds every type the contract test's child-position matrix lists as holding a command and every `KNOWN_BINARY_OPERATORS` entry. A trimmed probe fails the case, and so does a type or operator added to a set that the probe lacks.
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
     - Under `GITHUB_ACTIONS`, `command -v shfmt` is `/usr/local/bin/shfmt` and it reports the pin, from PR 1a. The CI pin equals the floor, from PR 1b.
     - The pin step precedes every pytest step in each leg, from PR 1a.
     - No workflow, job or step env sets `CI_SHFMT_INSTALL_DIR`, from PR 1a.
     - The step body, from PR 1a, with `curl` and `sudo` stubbed, `install` wrapped by a logging stub that runs the real `install`, and the real `sha256sum`:
       - passes `curl` `--fail`, `--location`, `--silent` and `--show-error`, the bounding flags `--retry`, `--retry-max-time` and `--max-time` with numeric values, `--proto '=https'` and `--proto-redir '=https'`, as its argv log shows;
       - passes a `--retry-max-time` value above the `--max-time` value, so an attempt that `--max-time` ends can still retry;
       - never reaches `install` on a digest mismatch or a failed fetch;
       - reaches `install` after the check on a match, and installs the checked bytes;
       - exits 1 naming the installed file when the installed bytes differ from the checked bytes;
       - exits 1 naming the other shfmt's path when that shfmt precedes the install directory on PATH, and exits 1 saying none was found when the install directory is off PATH;
       - installs into `/usr/local/bin` when `CI_SHFMT_INSTALL_DIR` is unset;
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
     - The realistic smoke set gives the same outcomes through `git-records` as through `words`.
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
     - In a main-tree session, the gate allows a stub shfmt's tree with an omittable key removed from a statement holding a git write. The case is labeled as pinning the header's dropped-key line, and it flips when the gap closes (ciso-reviewer plan-review round 20 R2).
     - In a main-tree session, `git status` followed by a carriage return denies with the status-3 clause alone. The reason holds neither the file workaround nor the tool-fault sentence (row 118, Design item 4).
     - In a main-tree session, one case per member entry of the runners file's cut-residual fixture list, with `git push` in place of the hidden line as Dispatch 6's table writes it, allows. One fact per item:
       - The RENAMED_FLAG entries hide no line, so this rule exempts them by name. Their `-C` form is a row of Dispatch 6's table instead.
       - The flush-comment entries hide the rest of a line, not a whole line, so this rule exempts them by name too. One case takes their worktree form, `( echo "x"#; git push` with the `)` on a later line, and allows. A second takes the `case` arm's hidden `cd`, `cd <wt> && case x in x) echo "a"#; cd <main>` with `;; esac; git push` on a later line, and allows (ciso-reviewer plan-review round 20 R1). The engineer cut the shape for this gate, "Cut it there too (Recommended)" (row 135, staff-sdet plan-review round 18 R1).
       - The cases pin the header's cut-residual line, and the list's comment names the decision file's residual (row 128).
       - Dispatch 6's table shows each one's base verdict.
       - The base allowed the heredoc members too, because `strip_heredocs` dropped the body.
     - In a linked-worktree session holding its own lock, `git commit -m "$(cat <<'EOF'`, with a multi-line message, `EOF`, and then `)"` on the next line, reaches the parser through the fast path's `(` match and allows.
     - In a main-tree session, row 132's `git commit \` shape denies as a main-tree write, and `cd <worktree> && \` then `git push` on the next line allows, so an ordinary continuation reaches the consumer as bash runs it.
     - With the module unlinked, the gate denies an over-cap command and a command holding a carriage return, each with the not-linked clause and the tool-fault sentence (staff-platform-engineer round 10 R3).
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
     - In a linked-worktree session holding its own lock, `c\d <main> && git push`, `c\<LF>d <main> && git push` and `git -\<LF>C <main> push` each allow, pinned as the header's relocation known gap.
     - In a main-tree session, the git-word spellings the prefilter admits, and the wrappers above, deny as writes. The placeholder cases deny through the UNRESOLVED status, the empty `cd` target or the placeholder subcommand.
     - `g\it push`, `gi""t push` and `gi\<LF>t push` allow in a main-tree session, pinned as the header's known gap (row 105).
     - An over-cap command denies with the size wording.
     - The stub's logged argv equals `SHFMT_ARGV`.
   - **Evaluator:**
     - The `Workspace` fixture's default builder spawns nothing. A real-shfmt end-to-end case on the `clean` path logs no `reread-credited-unparsed` line.
     - A command without both `git` and `diff` leaves a stub shfmt's call log empty.
     - Each withheld case below logs its `reread-withheld-unparsed=<reason>` line before the verdict line, and no `reread-credited-unparsed` line (staff-platform-engineer round 10 R5). These cases assert the reason through `run`'s log, read from `Assessment.unparsed_rereads`, the carrier the parity test asserts on the closure (Design item 5).
     - A withheld command with no later re-read still fails R5, so a loop that tested the `DiffReread` value rather than its `found` field would fail this case.
     - A stub shfmt that exits 1 gives no credit and logs `shfmt-exit-1`.
     - A command holding `git diff` and a carriage return gives no credit, logs `carriage-return`, and leaves a stub shfmt's call log empty (row 118).
     - `git diff \<CR><LF> --stat`, as the transcript holds it, gives the same outcome, so no join in `runs_git_diff` removes the carriage return first.
     - With real shfmt, `git diff \<LF>--stat`, as the transcript holds it, earns R5 credit through shfmt's own join (Design item 5).
     - `git dif\<LF>f`, as the transcript holds it, gives no credit, logs no withheld line and leaves the call log empty. The prefilter withholds it, so the case covers only the removed join (staff-sdet round 10 R3).
     - Each failure earns R5 credit and logs its reason before the verdict line:
       - shfmt off PATH logs `shfmt-missing`.
       - A non-executable stub logs `shfmt-start-failed`.
       - Stubs exiting 2 and 126 log `shfmt-exit-2` and `shfmt-exit-126`.
       - A stub printing an unknown-type tree logs `tree-unrecognized`.
       - A stub printing truncated JSON, and one printing a deeply nested tree, each log `parse-fault`.
       - A command over `MAX_COMMAND_BYTES` logs `oversize`.
       - A command over `MAX_COMMAND_BYTES` that also holds a carriage return logs `oversize`, because the byte cap runs first.
       - A command holding `git diff` and a lone surrogate logs `parse-fault`, and nothing raises out of `assess`.
     - With shfmt off PATH, and with a stub printing an unknown-type tree, a transcript that also breaks another rule still gets that rule's send-back, with the credit line logged before it.
     - `# check git diff later` earns no R5 credit.
     - `echo git diff` keeps R5 credit, under a renamed known-gap test.
     - The stub's logged argv equals `SHFMT_ARGV`.
   - **Carriage-return parity, in the contract test file:**
     - One shared byte list runs through `_lib_shell_parse` and through the evaluator's closure. The closure receives each entry decoded with `errors="replace"`, as the evaluator reads a transcript. Each entry holds `git diff`, and a stub shfmt that prints a valid tree serves each side.
     - For every entry, both sides stop at the same check, one entry per item:
       - A carriage return: status 3, and no records, each with an empty stub call log.
       - Its carriage-return-free twin: both sides reach shfmt, with one stub call each, and the shell side returns status 0.
       - Over-cap plus a carriage return: status 7, and `oversize` credit, each with an empty stub call log.
       - The byte 0xFF then a carriage return: status 3, and no records, each with an empty stub call log.
       - `\<CR><LF>`: status 3, and no records, each with an empty stub call log.
8. Locally, time each of these end to end:
   - A 64 KiB command of two-byte words, through `_lib_command_words` in PR 1b and through the worktree gate in PR 2.
   - A multi-KB heredoc commit message, through the same paths.
   - In PR 1b, one `git commit` with staged changes through both commit gates.
   - In PR 1b, the SessionStart check, and the Cursor adapter's sessionStart entry.
   - In PR 1b, the SessionStart check with a stub shfmt that hangs on the parse and ignores SIGTERM, against the 10-second registration timeout.

   Report each in that PR's body as a one-machine measurement beside the 100 ms per-fire budget in `plugins/claude-hook-review/skills/claude-hook-review/SKILL.md` § "7. Performance budget". They are not committed tests. The plan claims no time bound from the byte cap.

   In PR 1a, also measure one nested-input case's peak memory, as a scratch measurement, not a committed test (rows 115, 117). It needs only shfmt and the module.
   - Input: row 66's shape, 1,200 nested `{ }` groups around `true`, 6,004 bytes. Write it into a `mktemp -d` directory with `python3 -c "import sys; sys.stdout.write('{ ' * 1200 + 'true' + '; }' * 1200)"` redirected to a file.
   - Commands: run each stage on its own, so each figure belongs to one process, under `/usr/bin/time -l` on macOS or `/usr/bin/time -v` on Linux.
     - `shfmt -ln bash --to-json`, the argv `_LIB_SHFMT_ARGV` holds, reads the input file and writes its JSON to a second scratch file.
     - `python3 -I -S claude/.claude/hooks/shell-syntax-tree.py words` reads that JSON on stdin. That is the module's whole interface (Design item 2). A usage line on its stderr means the stage measured bad usage, not the parse, so the figure is void and the session runs the stage again.
     - Each run's maximum resident set size line gives that stage's peak. Take the line's unit, bytes or kilobytes, from that machine's `man 1 time`.
   - PR 1a's body states the input's and the JSON's byte counts, each stage's peak resident memory, wall time and exit status, and the machine's OS, as a one-machine measurement. It also states whether either peak passed the threshold below.
   - Threshold: a peak over 512 MiB in either stage contradicts row 115. The session then stops, as Critical files describes, and asks the engineer whether to bound shfmt's output in bytes.
     - The figure is the session's proposal, because no vendor or repo figure bounds a hook's memory.
     - The session's rationale: row 66 has this case finishing in about 2.1 s, under half the 5 s parse cap, so a deeper command inside the byte cap can run more than twice as long before the cap ends it. If memory grows with run time as the JSON does, a 512 MiB peak here puts that command past 1 GiB, which the session judges large for one hook process on a stow consumer's machine.
9. Before PR 1a, look up `mvdan.cc/sh/v3` in a CVE database such as OSV. Record the dependency rationale in PR 1a's description, which PR 1b's body cites, per `claude/.claude/CLAUDE.md` § "Engineering Judgment" ("New third-party dependencies"): vulnerability history, maintenance health, pinning strategy, and why shfmt over the alternatives.
10. Run the branch's own hook scripts by path, not the stowed ones, because a session runs the hooks its `~/.claude/hooks` link resolves to, and that checkout changes only on `git pull` (row 48). Each run feeds a PreToolUse or SessionStart JSON payload on stdin, once with real shfmt on PATH and once with shfmt off it. Record the outcomes in that PR's body.
    - PR 1b: each redaction gate with a `git commit -F <path>` and a `gh pr create --body-file <path>` payload, each file at a literal path outside `$HOME` holding clean text, and each allows with real shfmt on PATH.
    - PR 1b also: `deny-private-project-refs.sh` with row 132's multi-line `gh api` payload, which reaches the parse and allows, `deny-pii-in-commits.sh` with `git commit -m "$(cat <<'EOF'`, `EOF` and then `)"` on the next line, which allows, and `check-hook-dependencies.sh` with a `startup` payload.
    - PR 2: the worktree gate with a `git -C <worktree> status` payload, whose `-C` sends it past the fast path to the parser (`require-worktree-for-git-writes.sh:274`), and with a main-tree `git commit` payload.
11. Once per PR, in a scratch worktree, rehearse the recovery entry and record each outcome in that PR's body.
    - PR 1b: run each diagnostic the entry gives against the broken state it names: shfmt off PATH, a stub that exits 2, a stub that prints an unknown-type tree, a stub that hangs, python3 off PATH, and an unlinked module.
    - PR 1b also, each with a working shfmt, takes these inputs through their items to an outcome (staff-platform-engineer round 11 R3, comment-discipline-reviewer round 13 R7), one recovery item per sub-item:
      - The status-3 item: a command holding a carriage return.
      - The status-5 item, one input per cause it names: an extglob pattern holding `$(`, an unquoted heredoc whose continuation is followed directly by an expansion, and `echo @(\<LF>)`. The continuation cause takes one input per leading expansion kind: a dollar sign, a backtick substitution and a braced parameter (ciso-reviewer code-review round 8 R2).
      - The status-2 item: a module fault.
    - PR 2: the same for the worktree gate, plus a revert of PR 1b's merge alone on a copy of the PR 2 tree, recording the gate's deny, which shows why the rollback order reverts PR 2 first.

## Out of scope

- **Avoiding the pull-before-install lockout.** A rollout staged to avoid the lockout is within the plan's reach, and the plan declines one. The engineer wrote "I'd say accept the lockout because consumers know they may need to run ./install.sh after a git pull, and CHANGELOG should tell them, yes? The alternative is a ton of extra instrumentation which jI don't think is a good idea." (row 6). Considered and declined:
  - A rollout that keeps either old tokenizer behind a missing-shfmt fallback until a later PR removes it. PR 1b and PR 2 each retire a tokenizer with no fallback.
  - Keeping the `xargs -n1` fast path in the first release.
- **The other sixteen Bash gates, as an intended follow-up.** They include `_lib_commit_fragment_has_worktree_target`'s `xargs -n1` tokenizer and the gates built on `_lib_strip_shell_quotes`. Row 1 scopes this plan to the four tokenizing hooks. The engineer wrote "we may even consider moving more hooks to it because understanding quoted commands may not be necessary to be honest, or maybe the shell parser can extract the quote and can parse what's in the quote?" and later "great let's keep the other hooks in mind for a follow-up". The follow-up's own plan answers three questions:
  - Which wrapper commands, such as `bash -c` or `eval`, a gate re-parses the quoted argument of.
  - Whether the inner command of `bash -c "$cmd"`, opaque to any parser, should still deny.
  - Whether a cooperative agent emits nested shell commands at all, settled from evidence the follow-up can publish.

  The follow-up's plan also covers a string a shell runs as commands, such as `echo '...' | bash`, a heredoc fed to a shell, or a script file passed to `bash`. Separately, the base read a heredoc body a shell runs, and this change does not. The engineer accepted that regression, which Design item 10's cut-residual list records (row 128).
- **The plugin `_lib.sh` copies under `plugins/*/hooks/`.** None of them tokenizes a command.
- **Scoping flag reads to the `gh` or `git` simple command itself.** That would end the `ssh -T` and `tar -T` over-deny, but it changes the gates' behavior beyond swapping the tokenizer. The full descent changes verdicts too, so Verification 1's table puts each such change to the engineer instead (row 108), and a scoping change can follow from what that table shows.
- **Patching `parse-git-command.py`'s two gaps and deferring PR 2.** A newline split and a heredoc-tail fix could close row 17's misses inside shlex. "Alternatives weighed" sets aside patching the shlex tokenizers as the wrong foundation, the engineer chose PRs by tokenizer (row 46), which row 131 split further, and PR 2 does not wait for field time (row 107).
- **The flag-order rule in memory-store-audit Step 4.** The rule loses its reason once the parser lands. Removing it is a skill change with its own review.
- **A per-call shfmt version check.** A gate's parse never reads shfmt's version. `install.sh` and the SessionStart check (Design item 11) compare it with the floor. On every parse, the strict check holds every build to the known node types, the known keys and the listed always-present keys, with the dropped-key limit Design item 10 states.
- **Dependency commentary in hooks this plan does not otherwise edit.** Rows 77 and 84 apply to the four gates this plan edits. Other hooks' headers that describe their own python3 failures stay as they are until a follow-up applies row 77 repo-wide.
- **An on-screen notice from the evaluator for a parse fault that starts mid-session.** The evaluator logs the cause and credits R5. The engineer wrote "SessionStart notice is the early warning." (row 91).
- **A decoy file named the placeholder.** A file whose name equals the fixed placeholder, holding clean content, would be scanned in place of a variable's real target, such as `--body-file "$F"`. A literal `$F` path has the same exposure today, and only a steered agent creates such a file. The three redaction gates' tier lines omit `untrusted-input`, so their tiers waive it. Each of their headers' Known gaps records it (Design item 10), as `docs/hooks.md:43` requires of a waived finding.
- **Brace-built flags.** bash expands `{-F,/path}` into `-F` and `/path`, while shfmt's tree holds it as one `Lit`, so the gates' words never show the flag. Today's splitter and `xargs` path miss it the same way, so this change neither opens nor closes it. Only a steered agent writes such a word, and the three redaction gates' tier lines omit `untrusted-input`, so their tiers waive it. The decision file records it as an accepted residual (Design item 10), so the real-bash comparison is not read as proof that the words equal what bash passes.
- **A scheduled job that tests newer shfmt releases.** No job tests a release newer than CI's floor pin, so nothing warns of upstream drift before it reaches a consumer. The strict check then denies a tree with a renamed, retyped or new node or key, and the SessionStart probe names it at the next session start when it touches a construct the probe holds (row 61). A release that drops a key a valid command can omit makes no deny, the limit Design item 10 states. The engineer selected "Cut it (Recommended)" and wrote "Hold on this seems very overengineered" about adding a drift job (row 60).
- **Mentions of the retired scripts and the old hook name in dated records.** Past `CHANGELOG.md` entries, `docs/case-studies/worktree-enforcement.md`, `docs/reports/2026-08-22-discovery-audit/findings.md` and the dated `docs/design-decisions/git-native-commit-hooks-declined.md` keep them, because each records what held when it was written. For `check-python-floor.sh`, that is the entry at `CHANGELOG.md:649` and the earlier plans `.claude/plans/cursor-adapter.md`, `.claude/plans/hooks-doc-python-floor-list.md` and `.claude/plans/python-floor-3-14.md`.
- **An evaluator spawn budget separate from the wrapper's cap.** The prefilter limits spawns to commands that hold both `git` and `diff`, and the first diff ends the scan. A cap kill already logs `allowed-evaluator-exit=124` (`send-back-skipped-self-review.sh:78-82`). A hung shfmt therefore ends the whole evaluator run, not R5 alone.
- **Bounding shfmt's output or python3's memory for deeply nested input.** The gate still denies such a command, so the cost is availability, not a bypass. `_lib_capped` bounds the time where a cap tool exists. Verification 8 measures one nested case's peak memory, and a peak over that step's threshold puts a byte bound to the engineer (row 117). Below it, Design item 10 records the cost as an accepted residual (rows 66, 115).
- **Denying a parse when neither `timeout` nor `gtimeout` is on PATH.** `_lib_capped_for` runs every hook's capped calls uncapped then (`_lib.sh:136-138`), and requiring a cap tool for this one parse path would set it apart from every other capped call. The engineer chose a SessionStart warning instead (row 111). Design item 11 and row 82 state their bounds as holding only with a cap tool.
- **A shfmt check in `install-dev.sh`, or skipping the redaction gates' existing tests without shfmt.** `install.sh` holds the check, and `CLAUDE.md` § "Commands" lists it as first-time setup. Those gate tests fail without shfmt because the gates deny without it. Dispatch 1's report-header line names the cause on a run that names a path under `claude/.claude/hooks`, and a full-suite run shows it through the module tests' skip text.
- **Decoding `$'...'` and `$"..."` words.** They stay placeholders.
- **A per-shell dialect, as an intended follow-up.** Parsing a command in the dialect of the shell the Bash tool runs, such as zsh, is left to a later change. The engineer accepted the zsh gap as a recorded residual (row 106), and Design item 10 records it.
- **`install.sh` downloading shfmt itself.** The engineer selected "Check only (Recommended)" (row 3).
- **A heredoc fed to an interpreter other than a shell.** `python3 <<'EOF'` or `node <<'EOF'` runs its body in another language, which is not shell commands the gates parse. An interpreter that runs its body as commands, such as `make -f -`, is a member of Design item 10's cut-residual list (row 128).
- **Scanning a top-level heredoc on standard input as the message or body.** With shfmt's tree, `git commit -F - <<'EOF'` and `gh pr create --body-file - <<'EOF'` carry their text in the command, so the redaction gates could scan it instead of denying `-` as a pseudo-file. It changes what the gates scan, beyond swapping the tokenizer.
- **The guards the engineer cut, and what came with them.** The engineer typed "Hm I'm now inclined to cut the ones that a cooperative agent wouldn't make. That isn't parity but it seems correct to me. What does the architect think and why", then selected "Yes, cut them (Recommended)" (row 128). That reverses "sure, close the hole", "I agree.", "Unconditional (Recommended)" and "Accept the over-deny (Recommended)" (row 121), "Add the span check (Recommended)" (row 122) and "Direct-only, record the rest (Recommended)" (row 126) for these shapes. Each cut rule's findings stay in its superseded row as the evidence for Design item 10's cut-residual list, which holds the members each cut guard covered. Cut, one reason per item:
  - The status-11 continuation deny, `_lib_shell_parse_has_continuation`, its byte test and byte-test tables, its tail sentence, its recovery item and its CHANGELOG bullet. The hides it closed need a construction a cooperative agent does not write (row 130), and ordinary continuations parse as bash reads them (row 132).
  - The delimiter rule, its differential and its control. A delimiter whose quoting shfmt reads differently from bash is one a cooperative agent does not write (row 130).
  - The placement check, the real-bash container comparison and its controls, the placement sentence, and the three over-deny guard tests it would flip. Every member it covered needs a construction a cooperative agent does not write (row 130). A shape it covered that hides only under a below-floor bash is no member (this section's below-floor item).
  - The extglob widening to any `$` and its exit-3 check. Only a funsub inside an extglob pattern escapes the staged markers (row 125).
  - The interpreter check, `SHELL_READER_NAMES`, the interpreter sentence and its limiter clause. Feeding standard input to a command interpreter is a construction a cooperative agent does not write (row 130).
  - The closed Redirect-operator set and the probe's one-redirect-per-operator coverage. No remaining check finds a heredoc by its operator (row 127).
  - The `NODE_FIELDS` reach test. It tested the reach of the three cut walkers, and the staged walker's full descent keeps its own tests (row 56).
  - `_lib_file_route_sentence`, the route sentence and the `$(mktemp)` route cases. Today's file workaround, minus one phrase, serves the statuses that remain (Design item 1).
  - The seven pseudo-file rewords, the fourteen sibling rewords and the `deny-escaped-backticks-in-pr-body.sh:146` reword, with the deny-text route check. Each existed so no deny sent the agent to a heredoc in a substitution, which no gate now denies (row 122).
  - The `respond-pr`, `git-feature-branch-sync` and `git-state-safety` skill edits, the instruction tripwire and the pre-PR instruction searches. No example they touched meets a new deny (row 124). That the cut superseded the scope "Keep all in scope (Recommended)" kept is the session's inference, not an engineer answer [unverified] (row 124).
- **Repointing the stale `'Backtick hygiene'` citation in `deny-escaped-backticks-in-pr-body.sh`.** It names a heading `ready-for-review/SKILL.md` no longer holds (staff-platform-engineer round 12 R1). The fix rode with the cut rewords, and it pre-dates this change, so it is a follow-up of its own.
- **A Bash tool that runs a bash below the repo's 5.2 floor.** The repo supports no bash below 5.2 (`README.md:111`, `CHANGELOG.md:666`), and the engineer noted that it does not support bash 3.2 (row 130). That a Bash tool whose executing shell is such a bash is therefore an unsupported environment is the architect's reading, because no source names the Bash tool's executing shell [unverified] (row 130). Under that reading, a difference in how such a bash scans a heredoc body inside `$( )`, `<( )`, `${ }` or `a[ ]` is not a gap this plan records. bash 3.2.57 showed such differences, and 5.3.20 did not (row 122). That no 5.2.x build shows them is [unverified] until the cut-residual fixture list's agreement cases run on CI's bash (Dispatch 1's amendment). So Design item 10's cut-residual list and the gates' Known-gaps lines hold no member for them. The hooks' own bash floor still governs the gates, unchanged (`docs/hooks.md` § "Bash version").
- **Moving PR 1a's new test helpers out of `helpers.py` and splitting `test_shell_syntax_tree_contract.py`, as an intended follow-up.** That is the file-size check's first remedy. `helpers.py`'s row in `code-file-size-exceptions.toml` gives the rule that a helper used by one test tree goes in that tree's local module. For PR 1a the engineer selected "Raise ceilings, mark split pending (Recommended)" instead. The contract file's "split pending" row names the seam its split follows (row 137).
