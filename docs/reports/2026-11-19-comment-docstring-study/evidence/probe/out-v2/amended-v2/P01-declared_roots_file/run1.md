# comment-discipline-reviewer

Scope: 1 file in the diff (`claude/.claude/scripts/_config_dir.py`), 1 carrying an in-scope change (the new `declared_roots_file()` docstring). Verified against the read file: `declared_roots_matching()` does read `declared_roots_file()` (`_config_dir.py:123`), `CLEANUP_MERGED_BRANCHES_ROOTS_FILE` is a test seam (`cleanup-merged-branches.sh:251-255`), and the default path matches `_config_dir.py:50`. No false claims found.

## R1 [CONCERN] Restating the code

`claude/.claude/scripts/_config_dir.py:45-47` (added docstring, sentence 1)

Issue: "Return the path declared_roots_matching() reads: TRANSCRIPT_CONFIG_DIRS_FILE if set (...), else ~/.claude/transcript-config-dirs." restates the one-line body at line 50 (env var, else default path) and the caller at line 123. Static analysis of the repository finds all of it. Only the parenthetical carries a decision: the env var exists as a test seam, mirroring the cleanup-merged-branches.sh seam.

Production failure mode: the default path and fallback logic are now stated twice. A change to either one requires editing the docstring too, and the two can drift apart.

Required property / fix: keep only the decision, with its pointer, and delete the rest. Replacement docstring (one sentence):

`"""TRANSCRIPT_CONFIG_DIRS_FILE is a test seam, mirroring cleanup-merged-branches.sh's CLEANUP_MERGED_BRANCHES_ROOTS_FILE."""`

Note: `declared_roots_matching()`'s docstring (lines 90-92, pre-existing, out of scope) already states the same seam sentence. Once this one is added, the knowledge has two homes. Make one site point to the other instead of repeating it. The seam sentence is best kept here, where the env var is read.

## R2 [CONCERN] Restating the code / duplicated canonical statement

`claude/.claude/scripts/_config_dir.py:48` (added docstring, sentence 2)

Issue: "Unlike TRANSCRIPT_CONFIG_DIRS_LABEL, this DOES follow the seam." restates line 50 (the function reads the env var) and the existing comment at lines 13-16, which already holds this decision with its reason ("an operator-facing message must always name the real path"). The new sentence gives no reason of its own. It is a second statement of a decision whose canonical home is the LABEL comment.

Production failure mode: if the LABEL policy changes, the two sites disagree.

Required property / fix: delete the sentence. The LABEL comment already points here by name ("unlike declared_roots_file() below"), so the reader reaches the contrast from the LABEL side.
