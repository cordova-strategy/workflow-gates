# comment-discipline-reviewer

Scope note: the Python-environment-conventions reminder that arrived mid-session concerns dependency installs and does not bear on this review, so I set it aside. I applied the replacement "Don't restate the code" bullet from the task prompt.

## R1 [CONCERN] Prose restating the code

File: `claude/.claude/scripts/cursor-adapter/cursor-adapter.py:2266` (added in the diff at `report_state_dir_left`)

Offending text: `"""`uninstall` removes the install record right after the state directory, so a re-run cannot retry the removal."""`

Issue: the docstring has one clause, and it describes the caller instead of the function. Static analysis of this repository finds what it says. `uninstall` calls `remove_runtime_state` at line 2197, then unlinks the install record unconditionally at line 2206. A re-run then takes the "install record is missing" branch at line 2200 and never reaches `remove_runtime_state`. That takes reading two functions, but the rule deletes anything the repository's code finds, however many files it takes. The claim is true, so this is not a False or unsourced claim finding. `reach("after-state")` sits between the two steps, so "right after" is slightly loose.

Production failure mode: the docstring documents `uninstall`'s control flow from inside a three-line print helper. It goes stale when `uninstall` changes and gives the helper's reader nothing about the helper.

Required property: delete the docstring, so `report_state_dir_left` has none. The print text "The engineer deletes it by hand." already tells the reader what to do. No clause qualifies as a kept design decision, so nothing replaces it.

Prior decisions: none were handed to me.
