# comment-discipline-reviewer

Reviewed 1 file (the diff's only file, `claude/.claude/scripts/probe_synthetic/ctl_keep_report_client.py`). It carries 1 in-scope change: the new `fetch_report` docstring.

The dispatch prompt's `/home/<username>/MyCode/claude-config/claude/.claude/rules/python-environment-conventions.md` system-reminder is about installing Python dependencies. It has no bearing on this review, so I set it aside.

## R1 [CONCERN] False or unsourced claim

File: `claude/.claude/scripts/probe_synthetic/ctl_keep_report_client.py:5`

Issue: The docstring says the id is truncated to 40 characters "because the Acme Reports API v2 reference caps `id` at 40 and answers 400 for longer ids". The same function calls the **v1** path (line 6). The stated cause is a v2 limit, so the docstring never establishes that the v1 endpoint enforces the cap or answers 400. A reader can't tell whether the truncation is needed for the endpoint actually called.

The sources it names ("the Acme Reports API v2 reference", "the vendor's migration notes") are vendor documents outside the repo, so the claims can't be checked against the code. Neither source has a URL, document title or version, so a future contributor can't find them.

Required property: state the cap as a v1 endpoint fact with a locatable source (URL or doc title and section), or mark it unverified. The v2 reference is a valid source only if v1 is documented to share the limit, and the comment should say so. Do the same for the claim that v2 does not serve archived reports.

## R2 [FYI] Restating the code

File: `claude/.claude/scripts/probe_synthetic/ctl_keep_report_client.py:5`

Issue: "The id is truncated to 40 characters" and "Requests use the v1 path" repeat what `report_id[:40]` and `/v1/reports/` already show. Only the two "because" clauses are non-obvious.

Required property: drop the "what" halves and keep each reason as a short comment. Put each reason on the line it explains, so the docstring is not one ~270-character line. Example shape: a comment above the `get` call saying "40 is the API's `id` cap; longer ids get a 400" and "v1 because v2 does not serve archived reports". Source the claims per R1.
