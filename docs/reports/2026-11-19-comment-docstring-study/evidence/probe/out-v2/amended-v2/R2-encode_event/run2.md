# comment-discipline-reviewer

Reviewed 1 file (`claude/.claude/scripts/probe_synthetic/event_encoding.py`); 1 carried an in-scope comment change (the `encode_event` docstring).

No findings. The docstring states two decisions, and each passes the "Don't restate the code" rule:

- Sorted keys. The reason is an outside constraint: the billing vendor's "Webhook signatures" page defines the signature over a key-sorted body. The clause "an unsorted body fails verification" is that reason's direct effect, so it shares the sentence as a tightly coupled pair.
- Revisit trigger. "Switch to the vendor's SDK serializer once it ships one" says when to revisit.

Other angles checked, no hits:
- The docstring has no PR-defined label, no "used to be X" framing and no auto-memory citation.
- It is not verbose: two sentences, one fact or coupled pair each.
- Both claims are unsettleable from the repository and name their source (the vendor page), so they draw no False or unsourced finding.

Note: the dispatch also attached the `python-environment-conventions.md` rules file as a system reminder. It governs Python dependency installs, has no bearing on this review's scope, and was not applied.
