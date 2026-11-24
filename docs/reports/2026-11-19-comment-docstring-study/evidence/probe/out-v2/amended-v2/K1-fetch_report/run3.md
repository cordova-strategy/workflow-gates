# comment-discipline-reviewer

Scope: 1 file reviewed (`claude/.claude/scripts/probe_synthetic/ctl_keep_report_client.py`), 1 comment-level change in scope (the new `fetch_report` docstring). The `RETRY_LIMIT` line is pre-existing and not in the diff.

Set aside: the `python-environment-conventions.md` system reminder. It governs Python dependency installs and has no bearing on this review.

Both docstring sentences pass the rule under test. Each names a decision (truncate to 40 characters, use the `/v1/` path) and gives a reason that lives outside this repository (the vendor API's behavior). Restating the code does not apply, because naming what a kept decision decides is not a restatement. Multi-fact structure and paragraph readability do not apply either: there are two sentences, each pairing a decision with its reason. No PR-defined labels, no "used to be" framing, and the text survives the PR.

## R1 [FYI] False or unsourced claim

`ctl_keep_report_client.py:5`

Issue: the truncation rationale cites the v2 reference ("the Acme Reports API v2 reference caps `id` at 40 and answers 400 for longer ids"). The code calls the v1 path (line 6), and the docstring's second sentence says v2 is not used. The cited limit and the endpoint actually called belong to different API versions. A reader cannot tell whether v1 enforces the same cap. The repository cannot confirm or refute this, so it is an unsettleable external claim, not a false one.

Production failure mode: a future contributor cannot tell whether the truncation can be dropped or changed. Both the v1 path and the v2 cap look load-bearing, but the stated reason does not connect them.

Required property: the rationale names the version whose limit applies to the v1 call. If v1 shares the v2 cap, say so, e.g. "the Acme Reports API caps `id` at 40 in both v1 and v2 and answers 400 for longer ids". If it is unverified, mark it so.

## R2 [FYI] False or unsourced claim

`ctl_keep_report_client.py:5`

Issue: "per the vendor's migration notes" names a source that a reader cannot locate. The text gives no title, URL, or version. The claim "v2 does not serve archived reports" is unsettleable from the repository.

Production failure mode: revisiting whether v2 now serves archived reports means finding the notes first. The vendor docs are the only place to look, and the docstring does not say which ones.

Required property: replace the vague pointer with the document's title or URL. Optionally add when to revisit, e.g. "revisit if v2 gains archived-report support".
