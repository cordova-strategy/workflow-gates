# comment-discipline-reviewer

Scope: 1 file reviewed, 1 carried an in-scope comment change (new docstring on `strip_code_spans`).

## R1 [CONCERN] Restating the code

File: `claude/.claude/scripts/check-handoff.py:95-98`

Issue: The docstring opens with "Remove fenced code blocks and inline code spans", which restates the function name and its body (`_FENCED_BLOCK_RE.sub` then `_INLINE_CODE_RE.sub`, defined at lines 77-78). It then names "a placeholder or anchor-shape scan", which the call sites at lines 165 and 191 already show. Only one clause is a decision static analysis cannot find: stripped code is a draft quoting a literal it is citing, not proposing as a next step. Under the "Don't restate the code" rule, the restated halves are deleted and the decision half stays.

Production failure mode: The restated half drifts from the code. If a third regex is added, for example indented code blocks, the docstring is silently wrong while still reading as authoritative. It also pads the one fact a reader needs.

Required property: Replace the docstring with one sentence that states the decision and its reason, naming the decision's subject:

> """Strip quoted code because a draft cites literals there rather than proposing them as next steps, so the placeholder and anchor-shape scans must not fire on it."""

This keeps the why and drops the what. The fix is a single sentence, so it adds no Comment verbosity or Multi-fact finding. It names no PR-defined term and uses no prior-version framing.
