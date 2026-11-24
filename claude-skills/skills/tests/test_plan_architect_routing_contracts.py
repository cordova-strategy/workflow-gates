"""plan-architect is the only writer of review-driven plan edits, and every dispatching site says so."""
from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

import pytest
from _skill_md_helpers import (
    _AGENTS_DIR,
    _CODE_REVIEW_FINDING_DISPOSITION_HEADING,
    _CODE_REVIEW_SKILL_PATH,
    _PLAN_ARCHITECT_BLOCKING_MARK,
    _PLAN_ARCHITECT_FINDING_LINE_ACCEPT,
    _PLAN_IT_STEP5_HEADING,
    _PLAN_REVIEW_SKILL_PATH,
    _ROUTING_MD_PATH,
    _ROUTING_ROLES_HEADING,
    _STEP4_HEADING,
    _assert_pinned_clause_right_bounded,
    _heading_section_text,
    _raw_heading_section_text,
    _raw_subsection_text,
    _skill_file,
)

# The label `/code-review`'s Fix route line, the orchestrator's `HALT:` entry and
# `subagent-delegation`'s HALT handling each spell.
_PLAN_ARCHITECT_PLAN_REVISION_LABEL = "plan-architect — plan revision"
# What ends a `blocking` entry in the enforcement-invariant stop-and-ask: a return with no `accept` line.
# The clause holds whether or not Step 5's re-dispatch ran, because that re-dispatch runs only where a line was missing.
_PLAN_ARCHITECT_NO_ACCEPT_RETURN = (
    f"gives it no `{_PLAN_ARCHITECT_FINDING_LINE_ACCEPT}` line, even after `plan-it` Step 5's re-dispatch "
    "where a line was missing"
)

_PLAN_ARCHITECT_DESIGN_DOC = "docs/design-decisions/plan-architect-decides-review-findings.md"
_NO_BEHAVIOR_CELL_NOTE = (
    f"No behavior cell in {_PLAN_ARCHITECT_DESIGN_DOC} exercises this site, so this pin is its only check."
)
_PLAN_REVIEW_RECORD_COMPLETION_HEADING = "## Record review completion + deactivate"
_PLAN_ARCHITECT_REVISION_DISPATCH_PHRASE = (
    "send every such finding and edit to `plan-architect` in one revision re-dispatch"
)
# The paragraph that makes the dispatch conditional on a finding or a Step 4 follow-on edit.
_PLAN_REVIEW_RECORD_COMPLETION_DISPATCH_PARAGRAPH = (
    "Next, when this run returned any finding or a Step 4 answer needs a follow-on edit, "
    f"{_PLAN_ARCHITECT_REVISION_DISPATCH_PHRASE}, as the **Review findings.** paragraph of "
    "`plan-it/SKILL.md` § \"Step 5 — Architecture design\" says."
)


def _behavior_cell_note(cell_name: str) -> str:
    return f"Re-run Cell {cell_name} in {_PLAN_ARCHITECT_DESIGN_DOC} by hand after this edit."


class _PlanArchitectPinnedPhrase(NamedTuple):
    name: str
    path: Path
    heading: str | None
    phrase: str
    right_bounded: bool
    rerun_note: str


_PLAN_ARCHITECT_ROUTING_SITES = (
    _PlanArchitectPinnedPhrase(
        name="plan-review-record-completion",
        path=_PLAN_REVIEW_SKILL_PATH,
        heading=_PLAN_REVIEW_RECORD_COMPLETION_HEADING,
        phrase=_PLAN_REVIEW_RECORD_COMPLETION_DISPATCH_PARAGRAPH,
        right_bounded=True,
        rerun_note=_behavior_cell_note("V"),
    ),
    _PlanArchitectPinnedPhrase(
        name="plan-review-plan-prose-dispatch",
        path=_PLAN_REVIEW_SKILL_PATH,
        heading="## Output format",
        phrase=(
            "- Send them to `plan-architect` with the round's other findings, in the one revision "
            "re-dispatch that \"Record review completion + deactivate\" names."
        ),
        right_bounded=True,
        rerun_note=_NO_BEHAVIOR_CELL_NOTE,
    ),
    _PlanArchitectPinnedPhrase(
        name="plan-it-step-6",
        path=_skill_file("plan-it"),
        heading="## Step 6 — Hand off to /plan-review",
        phrase=(
            "It sends its findings to `plan-architect` under Step 5's **Review findings.** paragraph. "
            "Re-run it after each **Request changes** verdict, and present the plan only after a round "
            "ends **Approve** or **Approve with changes**."
        ),
        right_bounded=True,
        rerun_note=_NO_BEHAVIOR_CELL_NOTE,
    ),
    _PlanArchitectPinnedPhrase(
        name="code-review-fix-route",
        path=_CODE_REVIEW_SKILL_PATH,
        heading=_CODE_REVIEW_FINDING_DISPOSITION_HEADING,
        phrase=(
            "An ADDRESS row whose fix edits a plan from its `## Approach` heading down, whichever rule "
            "made it ADDRESS, sends that edit to `plan-architect` as `plan-it/SKILL.md` "
            "§ \"Step 5 — Architecture design\" "
            f"says, and this line names `{_PLAN_ARCHITECT_PLAN_REVISION_LABEL}` for it. The rest of its fix "
            "keeps its usual route, which runs first because a plan edit re-arms `require-plan-review.sh`. "
            "An ADDRESS row for a finding the enforcement-invariant rule below covers, whose "
            f"`{_PLAN_ARCHITECT_PLAN_REVISION_LABEL}` return {_PLAN_ARCHITECT_NO_ACCEPT_RETURN}, "
            "ends in that rule's blocking stop-and-ask with the keep logged as that rule says, "
            "and is not left standing as "
            "ADDRESS. DEFER rows carry no route — they produce no fix."
        ),
        right_bounded=False,
        rerun_note=_NO_BEHAVIOR_CELL_NOTE,
    ),
    _PlanArchitectPinnedPhrase(
        name="code-review-replan-verdict",
        path=_CODE_REVIEW_SKILL_PATH,
        heading="### Round-cap architect consult",
        phrase=(
            "Revise the branch's `.claude/plans/<slug>.md` through `plan-it` Step 5's revision "
            "re-dispatch, or run `/plan-it` when the branch has no plan file. The rows enumerated this "
            "round spawn again against the replaced surface."
        ),
        right_bounded=True,
        rerun_note=_NO_BEHAVIOR_CELL_NOTE,
    ),
    _PlanArchitectPinnedPhrase(
        name="orchestrator-halt-carry",
        path=_AGENTS_DIR / "review-orchestrator.md",
        heading=None,
        phrase=(
            "A plan edit the skill's Fix route sends to `plan-architect` goes under `HALT:` with its ADDRESS "
            f"row verbatim, a `{_PLAN_ARCHITECT_BLOCKING_MARK}` mark when the enforcement-invariant rule "
            "covers it or you cannot tell whether it does, and its "
            f"reviewer's findings-file path, naming `{_PLAN_ARCHITECT_PLAN_REVISION_LABEL}` as its rule. The "
            "round goes on as after a stop-and-ask about one finding, and `code-writer` gets only the rest "
            "of its fix. Report any other inline-route row under `HALT:`."
        ),
        right_bounded=False,
        rerun_note=_NO_BEHAVIOR_CELL_NOTE,
    ),
    _PlanArchitectPinnedPhrase(
        name="subagent-delegation-carve-out",
        path=_skill_file("subagent-delegation"),
        heading="### Implementation work → `code-writer`",
        phrase=(
            "Not code (the review-findings PR-body block, a `respond-pr` reply, a plan-file edit) — stays "
            "inline, except a plan-file edit that `plan-it/SKILL.md` § \"Step 5 — Architecture design\" "
            "gives to `plan-architect`."
        ),
        right_bounded=True,
        rerun_note=_behavior_cell_note("C"),
    ),
    _PlanArchitectPinnedPhrase(
        name="subagent-delegation-halt-dispatch",
        path=_skill_file("subagent-delegation"),
        heading="### Exception: gate/review loops stay orchestrator-driven",
        phrase=(
            "- With any `HALT:` entry, first, "
            f"when at least one entry names `{_PLAN_ARCHITECT_PLAN_REVISION_LABEL}`, dispatch "
            "`plan-architect` with every such entry, as `code-review/SKILL.md` § \"Finding disposition\" "
            "says, and stage that plan as step 2 stages `Fix paths:`; otherwise skip that clause. "
            f"A `{_PLAN_ARCHITECT_BLOCKING_MARK}` entry whose return "
            f"{_PLAN_ARCHITECT_NO_ACCEPT_RETURN}, ends in "
            "that section's enforcement-invariant stop-and-ask, asked of the user now, with its keep "
            "logged as that rule says. Then name the paths just staged, including any from your own "
            "dispatch, then run `/code-review` inline in this session at once, invoking the skill with "
            "args \"unrouted\" without the quotation marks, and run the rest of this review loop the "
            "same way until a clean round writes the marker. Each such round asks, logs and carries by "
            # The next bullet's opening is the right edge: a sentence appended to this one breaks the match.
            "the skill's own rules. - With no `HALT:` entry and a fix just staged,"
        ),
        right_bounded=False,
        rerun_note=_NO_BEHAVIOR_CELL_NOTE,
    ),
)

_PLAN_ARCHITECT_ROUTING_FEED_SITES = (
    _PlanArchitectPinnedPhrase(
        name="routing-re-review-feed",
        path=_ROUTING_MD_PATH,
        heading=_ROUTING_ROLES_HEADING,
        phrase=(
            "Each finding `plan-architect` accepted that round, as what's been applied, and each one it "
            "declined, with its reason, stay inline regardless. `marker.sh write plan-review` records only "
            "a content hash of the plan set, so no on-disk artifact holds them."
        ),
        right_bounded=True,
        rerun_note=_behavior_cell_note("RR"),
    ),
)


def _assert_site_carries_pinned_phrase(site: _PlanArchitectPinnedPhrase, *, context: str) -> None:
    assert site.heading is not None or not site.right_bounded, (
        f"{site.name}: right_bounded needs a heading to bound against; with heading=None the whole file is "
        "searched and the bound would be ignored."
    )
    collapsed_phrase = " ".join(site.phrase.split())
    if site.heading is None:
        assert collapsed_phrase in " ".join(site.path.read_text().split()), context
        return
    section_text = (
        _raw_subsection_text(site.path, site.heading)
        if site.heading.startswith("### ")
        else _raw_heading_section_text(site.path, site.heading)
    )
    if site.right_bounded:
        _assert_pinned_clause_right_bounded(collapsed_phrase, section_text, context=context)
    else:
        assert collapsed_phrase in " ".join(section_text.split()), context


@pytest.mark.parametrize(
    "site",
    _PLAN_ARCHITECT_ROUTING_SITES,
    ids=[f"{site.name}-{index}" for index, site in enumerate(_PLAN_ARCHITECT_ROUTING_SITES)],
)
def test_review_finding_plan_edits_route_to_plan_architect_at_every_site(
    site: _PlanArchitectPinnedPhrase,
) -> None:
    """The rule lives in plan-it/SKILL.md Step 5; these sites point there, so a dropped phrase reopens a second writer."""
    _assert_site_carries_pinned_phrase(
        site,
        context=(
            f"{site.path}: no longer carries {site.phrase!r}, which routes a plan edit made in "
            f"answer to a review finding to `plan-architect`. {site.rerun_note}"
        ),
    )


@pytest.mark.parametrize(
    "site",
    _PLAN_ARCHITECT_ROUTING_FEED_SITES,
    ids=[f"{site.name}-{index}" for index, site in enumerate(_PLAN_ARCHITECT_ROUTING_FEED_SITES)],
)
def test_plan_architect_routing_feed_stays_pinned(
    site: _PlanArchitectPinnedPhrase,
) -> None:
    _assert_site_carries_pinned_phrase(
        site,
        context=(
            f"{site.path}: no longer carries {site.phrase!r}, which states what the `plan-architect` "
            f"dispatch feeds the next round. {site.rerun_note}"
        ),
    )


_ENGINEER_ANSWERS_PARAGRAPH_OPENING = "**Engineer answers.**"

_ENGINEER_ANSWERS_POINTER_SITES = (
    pytest.param(
        _PLAN_REVIEW_SKILL_PATH,
        _STEP4_HEADING,
        "as the **Engineer answers.** paragraph",
        id="plan-review-step-4",
    ),
    pytest.param(
        _skill_file("plan-it"),
        _PLAN_IT_STEP5_HEADING,
        "under **Engineer answers.** above",
        id="plan-it-critical-files",
    ),
)


@pytest.mark.parametrize(("site_path", "heading", "pointer_phrase"), _ENGINEER_ANSWERS_POINTER_SITES)
def test_engineer_answers_pointer_resolves_to_a_paragraph_in_plan_it_step_5(
    site_path: Path, heading: str, pointer_phrase: str
) -> None:
    """The `**Engineer answers.**` paragraph of plan-it Step 5 specifies what the session writes itself
    for an engineer's answer: one row per answer, and an added Critical file's path.

    Its two pointers are pinned here, not in `_PLAN_ARCHITECT_ROUTING_SITES`, because they route nothing to `plan-architect`.
    """
    assert pointer_phrase in _heading_section_text(site_path, heading), (
        f"{site_path}: {heading!r} no longer carries {pointer_phrase!r}, the pointer to what the "
        "session may write itself for an engineer's answer."
    )
    plan_it_step5_lines = _raw_heading_section_text(
        _skill_file("plan-it"), _PLAN_IT_STEP5_HEADING
    ).splitlines()
    assert any(line.startswith(_ENGINEER_ANSWERS_PARAGRAPH_OPENING) for line in plan_it_step5_lines), (
        f"plan-it/SKILL.md: no Step 5 line starts with {_ENGINEER_ANSWERS_PARAGRAPH_OPENING!r}, "
        f"so the pointer {pointer_phrase!r} dangles."
    )


# The claim each asking step gives the session to record under `**Engineer answers.**`.
_ENGINEER_ANSWER_ROW_CLAIM_SITES = (
    pytest.param(
        _PLAN_REVIEW_SKILL_PATH,
        _STEP4_HEADING,
        'claiming "<item> stays in this plan\'s scope" for a kept item '
        'or "<item> leaves this plan\'s scope" for a declined one',
        id="plan-review-step-4-kept-and-declined-items",
    ),
    pytest.param(
        _PLAN_REVIEW_SKILL_PATH,
        _STEP4_HEADING,
        'Record `Proceed anyway` as the row "This plan goes ahead at its `Projected diff:` without a split", '
        'tagged `[engineer-verified: "Proceed anyway"]`',
        id="plan-review-step-4-proceed-anyway",
    ),
    pytest.param(
        _PLAN_REVIEW_SKILL_PATH,
        _STEP4_HEADING,
        'Record `Split now` as the row "This plan is cut to a `Projected diff:` below 400 changed lines", '
        'tagged `[engineer-verified: "Split now"]`',
        id="plan-review-step-4-split-now",
    ),
    pytest.param(
        _skill_file("plan-it"),
        _PLAN_IT_STEP5_HEADING,
        "`<path>` joins this plan's Critical files",
        id="plan-it-critical-files-addition",
    ),
)


@pytest.mark.parametrize(("site_path", "heading", "claim_template"), _ENGINEER_ANSWER_ROW_CLAIM_SITES)
def test_engineer_answer_row_claim_template_stays_in_its_asking_step(
    site_path: Path, heading: str, claim_template: str
) -> None:
    """The session writes each answer's ledger row with the claim its asking step gives.

    A reworded claim, or a claim bound to the wrong answer, would make the session and a later `/plan-review` round
    disagree on what the row covers.
    """
    assert claim_template in _heading_section_text(site_path, heading), (
        f"{site_path}: {heading!r} no longer gives the row claim {claim_template!r} that the "
        "**Engineer answers.** paragraph tells the session to record."
    )


# Each phrase belonged to a route that let a writer other than `plan-architect` edit a plan after a review.
_REMOVED_SECOND_PLAN_WRITER_PHRASES = (
    (_PLAN_REVIEW_SKILL_PATH, "Apply each one you accept"),
    (_PLAN_REVIEW_SKILL_PATH, "the plan author revises"),
    (_skill_file("plan-it"), "Address any findings"),
    (_PLAN_REVIEW_SKILL_PATH, "Record each answer on its own ledger row quoting it"),
    (_ROUTING_MD_PATH, "What's been applied stays inline regardless"),
    (_skill_file("plan-it"), "The session then adds it to the list itself"),
)


@pytest.mark.parametrize(
    ("site_path", "removed_phrase"),
    _REMOVED_SECOND_PLAN_WRITER_PHRASES,
    ids=[
        f"{path.parent.name}-{path.stem}-{index}"
        for index, (path, _phrase) in enumerate(_REMOVED_SECOND_PLAN_WRITER_PHRASES)
    ],
)
def test_removed_second_plan_writer_phrase_stays_absent(site_path: Path, removed_phrase: str) -> None:
    """A phrase that let the session or an unnamed actor edit a plan after a review does not come back.

    Presence pins on the `plan-architect` routes stay green when the old route is re-added beside them.
    """
    assert removed_phrase not in " ".join(site_path.read_text().split()), (
        f"{site_path}: carries {removed_phrase!r} again, a route that lets a writer other than "
        "`plan-architect` edit a plan in answer to a review finding."
    )


def test_plan_review_record_completion_deactivates_then_dispatches_plan_architect_then_writes_the_marker() -> None:
    """The completion marker follows the active marker's removal and a finished `plan-architect` dispatch.

    No completion marker is written on **Request changes**, so a round that returns blockers cannot approve an unrevised plan.
    The dispatch paragraph itself is pinned whole, with its right edge, by the `plan-review-record-completion` routing site.
    """
    section_text = _heading_section_text(_PLAN_REVIEW_SKILL_PATH, _PLAN_REVIEW_RECORD_COMPLETION_HEADING)
    raw_section_text = _raw_heading_section_text(_PLAN_REVIEW_SKILL_PATH, _PLAN_REVIEW_RECORD_COMPLETION_HEADING)
    ordered_steps = (
        "deactivate plan-review",
        _PLAN_REVIEW_RECORD_COMPLETION_DISPATCH_PARAGRAPH,
        "marker.sh write plan-review",
    )
    step_positions = [section_text.find(step) for step in ordered_steps]
    assert -1 not in step_positions and step_positions == sorted(step_positions), (
        f"{_PLAN_REVIEW_SKILL_PATH}: {_PLAN_REVIEW_RECORD_COMPLETION_HEADING!r} no longer sequences "
        f"{ordered_steps} in that order; found at {step_positions}."
    )
    _assert_pinned_clause_right_bounded(
        "Then write the completion marker, but only when the verdict is **Approve** or "
        "**Approve with changes** and any such dispatch, with any re-dispatch it led to, is complete. "
        "Do not write it on **Request changes** — write it only after `plan-architect` revises the plan "
        "and a clean re-review completes.",
        raw_section_text,
        context=(
            f"{_PLAN_REVIEW_SKILL_PATH}: the completion-marker paragraph no longer writes the marker "
            "only after an approving verdict and a complete `plan-architect` dispatch."
        ),
    )
