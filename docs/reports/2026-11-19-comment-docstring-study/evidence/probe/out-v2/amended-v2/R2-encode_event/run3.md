# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/probe_synthetic/event_encoding.py`); 1 carried an in-scope comment change (the new `encode_event` docstring).

No findings.

Checked against the amended "Don't restate the code" rule:

- "Keys are sorted" names what the decision decides, which the rule says is not a restatement. The same sentence gives an outside-forced reason the code cannot show: the vendor's "Webhook signatures" page defines the signature over a key-sorted body.
- "an unsorted body fails verification" is the direct effect of that reason, so it shares the sentence as a tightly coupled pair. It does not make the sentence multi-fact.
- "Switch to the vendor's SDK serializer once it ships one" is a when-to-revisit trigger, which the rule keeps.
- The verification-failure claim is unsettleable from the repository and names its source (the vendor page), so it draws no False or unsourced claim finding. A Grep of the snapshot for "Webhook signatures", "billing vendor" and `encode_event` found only this docstring and the function definition, so nothing in the repo contradicts it.
- The docstring is two sentences and carries no PR-defined label, prior-version framing or auto-memory citation.
