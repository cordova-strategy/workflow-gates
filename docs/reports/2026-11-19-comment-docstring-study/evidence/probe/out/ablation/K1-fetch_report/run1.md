# comment-discipline-reviewer

Reviewed 1 file, 1 carrying an in-scope change: the new docstring on `fetch_report` in `claude/.claude/scripts/probe_synthetic/ctl_keep_report_client.py`. No prompt text contradicted the agent file, so none was set aside.

## R1 [CONCERN] Prose restating the code

File: `claude/.claude/scripts/probe_synthetic/ctl_keep_report_client.py:5`, first docstring clause.

Issue: "The id is truncated to 40 characters" restates `report_id[:40]` on line 6. The agent file requires a deletion finding for every docstring clause, so this clause is flagged.

Production failure mode: none. The cost is a docstring that repeats the code.

Required property: delete the standalone restatement. The clause is also the subject of a kept decision, so the decision sentence keeps its subject and its reason. The kept sentence says the id is cut to 40 characters because the Acme Reports API v2 reference caps `id` at 40 and answers 400 for longer ids. The reason clause stays: it is an outside constraint no file in this repository shows.

## R2 [CONCERN] Prose restating the code

File: `claude/.claude/scripts/probe_synthetic/ctl_keep_report_client.py:5`, third docstring clause (the sentence beginning "Requests use the v1 path").

Issue: "Requests use the v1 path" restates the `/v1/reports/...` literal on line 6. The agent file requires a deletion finding for every docstring clause, so this clause is flagged.

Production failure mode: none. The cost is a docstring that repeats the code.

Required property: delete the standalone restatement. The clause is also the subject of a kept decision, so the decision sentence keeps its subject and its reason. The kept sentence says v1 is used because v2 does not serve archived reports, per the vendor's migration notes. The reason clause stays: it is an outside constraint, and it cites a source.

## Checked, no finding

- **False or unsourced claim:** The API v2 id cap, the 400 response and the archived-report gap are about an external vendor. `Grep` for `Acme`, `migration notes` and `archived` found no in-repo subject that confirms or contradicts them, so they are unsettleable. The archived-reports claim names its source (the vendor's migration notes). The 40-character cap names its source (the v2 reference).
- **Comment verbosity, Multi-fact comment structure, Paragraph readability:** Each of the two sentences carries one decision and its reason, with the decision stated first.
- **PR-defined terminology, "Used to be X" framing:** No hits. `v1` and `v2` are vendor API versions, not PR labels.
- **Wrong altitude:** A docstring is the right place for a constraint on this function's code.
