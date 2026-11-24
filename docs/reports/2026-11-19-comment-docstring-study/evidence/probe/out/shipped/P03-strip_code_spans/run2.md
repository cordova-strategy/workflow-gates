# comment-discipline-reviewer

## R1 [CONCERN] Restating the code
- File:line: `claude/.claude/scripts/check-handoff.py:95-98` (the docstring added to `strip_code_spans`).
- Issue: The docstring opens with "Remove fenced code blocks and inline code spans". The function name, its two regex constants (`_FENCED_BLOCK_RE`, `_INLINE_CODE_RE`) and the one-line body already show this. Only the trailing rationale is non-obvious: quoted literals must not trip the placeholder scan (`check_placeholder_text`, line 165) or the §3.5 anchor-shape scan (line 191). The sentence also chains the restatement, a characterization of drafts, and the purpose into one dash-joined run.
- Failure mode: A future reader parses a restatement to reach the one useful fact. The restated half goes stale if the regexes change.
- Required property: Delete the restatement and keep only the why, as one sentence. For example: "Quoted literals in a draft (a cited placeholder or anchor shape) must not trigger the placeholder and §3.5 anchor-shape scans." Keep both scans named, since the fix must not lose a fact.

Other angles checked and clear:
- No PR-defined labels.
- No "used to be" framing.
- No false claim: both callers at lines 165 and 191 are the scans the docstring names.
- Not verbose beyond that sentence.

Files reviewed: 1. Files with an in-scope comment change: 1.
