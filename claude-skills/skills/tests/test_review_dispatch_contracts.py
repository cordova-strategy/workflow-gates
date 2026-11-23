"""Reviewer dispatch: the prompt-contract sites, findings_path wiring, the declaration block and the routing reviewer table."""
from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest
from _skill_md_helpers import (
    _AGENTS_DIR,
    _CODE_REVIEW_FINDING_DISPOSITION_HEADING,
    _CODE_REVIEW_RIPPLE_HEADING,
    _PLAN_ARCHITECT_BLOCKING_MARK,
    _PLAN_ARCHITECT_FINDING_LINE_DECLINE,
    _PLAN_ARCHITECT_FINDING_LINE_OPEN,
    _PLAN_IT_STEP5_HEADING,
    _STEP4_HEADING,
    _agent_body,
    _all_skill_md_paths,
    _assert_pinned_clause_right_bounded,
    _heading_section_text,
    _raw_heading_section_text,
    _raw_subsection_text,
    _scope_exempt_change_type_row_text,
    _skill_body,
    _skill_file,
)

# pyproject.toml's pythonpath also puts claude/.claude/tests on the import
# path, where these shared test helpers live.
from helpers import (
    backticked_field_tokens,
    input_contract_field_tokens,
    input_contract_section,
    prompt_contract_agent_names,
)

# Single source of truth for SKILL.md structural rules — the commit-gate hook
# shells out to the same module. pyproject.toml's [tool.pytest.ini_options]
# pythonpath puts plugins/skill-management/scripts and evals/ on the import path.
from validate_skill_structure import parse_frontmatter


def test_plan_review_hands_comment_discipline_reviewer_a_plan_path() -> None:
    """The dispatcher and the agent name the same input token, and the spawn keeps its `/review-pr` skip.

    Its `plan_path:` checks overlap `test_prompt_contract_site_matches_agent_contract`.
    It stays for the spawn-condition literals: the Step 5 condition and the `/review-pr` skip.
    """
    routing_roles_text = _heading_section_text(_ROUTING_MD_PATH, "## Reviewer roles")
    agent_input_contract_text = _heading_section_text(
        _AGENTS_DIR / "comment-discipline-reviewer.md", "## Input contract"
    )
    for literal in (
        "`plan_path:`",
        "on every round that reaches Step 5 with a plan file",
        "Skip it under `/review-pr`'s standing override",
    ):
        assert literal in routing_roles_text, (
            f"{_ROUTING_MD_PATH}: Reviewer roles no longer carries {literal!r}"
        )
    assert "`plan_path:`" in agent_input_contract_text, (
        "comment-discipline-reviewer.md: Input contract no longer names `plan_path:`"
    )


class _PromptContractDispatchSite(NamedTuple):
    label: str
    agent_file: str
    site_text: Callable[[], str]
    sent_tokens: frozenset[str]
    exclusion_sentence: str
    forbidden_phrases: tuple[str, ...]


_PLAN_REVIEW_COMMENT_DISCIPLINE_SPAWN_ANCHOR = "- Always spawn `comment-discipline-reviewer`"


def _plan_review_comment_discipline_spawn_text(routing_md_path: Path) -> str:
    """The comment-discipline-reviewer spawn bullet and its indented continuation paragraph in ROUTING.md.

    An unindented continuation line ends the window, so a sentence added there
    falls outside it.
    """
    lines = routing_md_path.read_text().splitlines()
    start_index = next(
        (
            index
            for index, line in enumerate(lines)
            if line.startswith(_PLAN_REVIEW_COMMENT_DISCIPLINE_SPAWN_ANCHOR)
        ),
        None,
    )
    assert start_index is not None, (
        f"{routing_md_path}: no line starts with "
        f"{_PLAN_REVIEW_COMMENT_DISCIPLINE_SPAWN_ANCHOR!r}"
    )
    end_index = start_index + 1
    while end_index < len(lines) and (
        not lines[end_index].strip() or lines[end_index].startswith(" ")
    ):
        end_index += 1
    return "\n".join(lines[start_index:end_index]).rstrip()


class TestPlanReviewCommentDisciplineSpawnText:
    _SPAWN_BULLET = (
        "- Always spawn `comment-discipline-reviewer` on every round.\n"
        "  - `plan_path:` with the plan file's path\n"
        "\n"
        "  It gets no Item ownership routing. It keys its findings by angle name.\n"
    )

    def test_text_appended_after_the_paragraphs_last_sentence_is_inside_the_window(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "ROUTING.md"
        path.write_text(
            self._SPAWN_BULLET.rstrip("\n") + " Also pass it `declared:`.\n"
            "\n"
            "- Next unindented bullet.\n"
        )

        window = _plan_review_comment_discipline_spawn_text(path)

        assert window.endswith("Also pass it `declared:`.")
        assert "It gets no Item ownership routing." in window

    def test_next_unindented_bullet_is_outside_the_window(self, tmp_path: Path) -> None:
        path = tmp_path / "ROUTING.md"
        path.write_text(self._SPAWN_BULLET + "\n- Always spawn `other-reviewer` for `declared:`.\n")

        window = _plan_review_comment_discipline_spawn_text(path)

        assert "other-reviewer" not in window
        assert "declared:" not in window

    @pytest.mark.parametrize("trailing_blank_lines", ["", "\n", "\n\n\n"])
    def test_spawn_bullet_that_ends_the_file_returns_its_whole_paragraph(
        self, tmp_path: Path, trailing_blank_lines: str
    ) -> None:
        path = tmp_path / "ROUTING.md"
        path.write_text("- Earlier bullet.\n\n" + self._SPAWN_BULLET + trailing_blank_lines)

        window = _plan_review_comment_discipline_spawn_text(path)

        assert window == self._SPAWN_BULLET.rstrip("\n")

    def test_reworded_start_anchor_raises_an_assertion_error_naming_the_anchor(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "ROUTING.md"
        path.write_text(
            self._SPAWN_BULLET.replace("Always spawn", "Spawn")
        )

        with pytest.raises(AssertionError) as excinfo:
            _plan_review_comment_discipline_spawn_text(path)
        assert str(path) in str(excinfo.value)
        assert _PLAN_REVIEW_COMMENT_DISCIPLINE_SPAWN_ANCHOR in str(excinfo.value)


# Every dispatch site that hands an agent with an Input contract field list its prompt.
# A new site for a listed agent goes here, or it escapes test_prompt_contract_site_matches_agent_contract.
_PROMPT_CONTRACT_DISPATCH_SITES = (
    _PromptContractDispatchSite(
        label="code-review",
        agent_file="comment-discipline-reviewer.md",
        site_text=lambda: _scope_exempt_change_type_row_text(_skill_file("code-review")),
        sent_tokens=frozenset({"diff:", "findings_path:", "prior_decisions:"}),
        exclusion_sentence=(
            "Send it no diff scope, specific question, declared value or declaration "
            'block from the "Spawn per question" paragraph, and no return budget from '
            'the "Other spawned specialists" paragraph below this table.'
        ),
        forbidden_phrases=(
            "declaration block",
            "specific question",
            "return budget",
            "diff scope",
            "declared value",
            "declared:",
        ),
    ),
    _PromptContractDispatchSite(
        label="plan-review",
        agent_file="comment-discipline-reviewer.md",
        site_text=lambda: _plan_review_comment_discipline_spawn_text(_ROUTING_MD_PATH),
        sent_tokens=frozenset({"plan_path:", "findings_path:", "prior_decisions:"}),
        exclusion_sentence=(
            "It gets no Item ownership routing and no Ledger cross-check instruction."
        ),
        forbidden_phrases=(
            "declared:",
            "Declaration block",
            "Item ownership",
            "Ledger cross-check",
        ),
    ),
)


@pytest.mark.parametrize(
    "site", _PROMPT_CONTRACT_DISPATCH_SITES, ids=lambda site: site.label
)
def test_prompt_contract_site_matches_agent_contract(site: _PromptContractDispatchSite) -> None:
    """A dispatching site cites the agent's Input contract and names exactly the fields it sends, each one the contract lists.

    Each item the site's exclusion sentence names appears nowhere else in the site,
    and the site carries the phrase "its prompt carries only". Other added prose goes
    unchecked, and the agent's shared sentences set it aside at runtime.

    The agent's Input contract is the one home for what its dispatch prompt may carry.
    docs/design-decisions/agent-input-contract-owns-dispatch-fields.md records why the contract owns the fields.
    """
    site_text = site.site_text()
    agent_contract_tokens = input_contract_field_tokens(
        input_contract_section(_AGENTS_DIR / site.agent_file)
    )
    assert agent_contract_tokens, (
        f"{site.agent_file}: '## Input contract' section not found or lists no field bullet."
    )
    citation = f'`claude/.claude/agents/{site.agent_file}` § "Input contract"'
    assert citation in site_text, f"{site.label}: site no longer cites {citation}"
    named_tokens = backticked_field_tokens(site_text)
    assert named_tokens == site.sent_tokens, (
        f"{site.label}: site names {sorted(named_tokens)}, but the fields it sends are "
        f"{sorted(site.sent_tokens)}. A backticked mention of a field token counts as sending it, "
        "even in a negation, so the exclusion sentence names the declared value without backticks."
    )
    assert site.sent_tokens <= agent_contract_tokens, (
        f"{site.label}: {sorted(site.sent_tokens - agent_contract_tokens)} not in "
        f"{site.agent_file}'s Input contract fields {sorted(agent_contract_tokens)}"
    )
    assert site_text.count(site.exclusion_sentence) == 1, (
        f"{site.label}: site must carry its exclusion sentence exactly once: "
        f"{site.exclusion_sentence!r}"
    )
    lowered_site_text = site_text.lower()
    assert "its prompt carries only" in lowered_site_text, (
        f"{site.label}: site no longer says its prompt carries only the fields it sends."
    )
    lowered_exclusion_sentence = site.exclusion_sentence.lower()
    for phrase in site.forbidden_phrases:
        lowered_phrase = phrase.lower()
        allowed_count = lowered_exclusion_sentence.count(lowered_phrase)
        assert lowered_site_text.count(lowered_phrase) == allowed_count, (
            f"{site.label}: {phrase!r} appears {lowered_site_text.count(lowered_phrase)} time(s) "
            f"in the site, but only {allowed_count} inside its exclusion sentence. The agent's "
            "Input contract does not list that part of a prompt."
        )


def test_code_review_exclusion_sentence_cites_paragraphs_that_exist() -> None:
    """The /code-review row's exclusion sentence names two paragraphs, so each must still open a line in the skill.

    Both names also occur inside the exclusion sentence, so only a line-start match proves the paragraph exists.
    """
    skill_md_path = _skill_file("code-review")
    lines = skill_md_path.read_text().splitlines()
    for paragraph_name in ("Spawn per question", "Other spawned specialists"):
        assert any(line.startswith(paragraph_name) for line in lines), (
            f"{skill_md_path}: no line starts with {paragraph_name!r}, the paragraph the "
            "comment-discipline row's exclusion sentence cites."
        )


def test_prompt_contract_sites_cover_every_contract_agent() -> None:
    """An agent under claude/.claude/agents with Input contract field bullets and no listed dispatch site fails here.

    Scans claude/.claude/agents only, not plugin agent directories.
    """
    agents_with_sites = {site.agent_file for site in _PROMPT_CONTRACT_DISPATCH_SITES}
    agents_with_fields = prompt_contract_agent_names(_AGENTS_DIR)
    assert agents_with_sites == agents_with_fields, (
        f"Agents with Input contract field bullets are {sorted(agents_with_fields)}, but "
        f"_PROMPT_CONTRACT_DISPATCH_SITES names {sorted(agents_with_sites)}. Add each dispatching "
        "site of the missing agent(s) to _PROMPT_CONTRACT_DISPATCH_SITES."
    )


# plan-review/SKILL.md's Output format bullet for a round whose only findings are plan prose.
_PLAN_REVIEW_PROSE_ONLY_ROUND_BULLET = (
    "A round whose only findings are plan prose ends **Approve with changes**. The completion marker "
    "follows once the `plan-architect` dispatch that \"Record review completion + deactivate\" names "
    "is complete."
)


def test_plan_prose_findings_never_block_and_plan_diffs_stay_out_of_lane() -> None:
    """These sentences keep plan prose non-blocking and reviewed once, before approval.

    The plan rule is pinned because a plan may cite its own review rounds without being flagged.
    """
    plan_review_skill_path = _skill_file("plan-review")
    output_format_text = _heading_section_text(plan_review_skill_path, "## Output format")
    agent_scope_text = _heading_section_text(
        _AGENTS_DIR / "comment-discipline-reviewer.md", "## Scope"
    )
    rerun_note = (
        "Re-run the cells in docs/design-decisions/plan-prose-reviewed-inside-plan-review.md "
        "by hand after this edit."
    )
    non_blocking_literal = (
        "A plan prose finding never makes the verdict **Request changes**, "
        "whatever severity the reviewer gave it, so plan prose alone never adds a review round."
    )
    diff_exclusion_literal = (
        "A plan file under `.claude/plans/` that appears in a diff is out of scope"
    )
    review_rounds_literal = "references to its own review rounds and findings"
    assert non_blocking_literal in output_format_text, (
        f"{plan_review_skill_path}: Output format no longer carries "
        f"{non_blocking_literal!r}. {rerun_note}"
    )
    _assert_pinned_clause_right_bounded(
        _PLAN_REVIEW_PROSE_ONLY_ROUND_BULLET,
        _raw_heading_section_text(plan_review_skill_path, "## Output format"),
        context=(
            f"{plan_review_skill_path}: Output format no longer carries its prose-only-round "
            f"bullet verbatim. {rerun_note}"
        ),
    )
    assert diff_exclusion_literal in agent_scope_text, (
        f"comment-discipline-reviewer.md: Scope no longer carries {diff_exclusion_literal!r}. "
        f"{rerun_note}"
    )
    assert review_rounds_literal in agent_scope_text, (
        f"comment-discipline-reviewer.md: Scope no longer lists {review_rounds_literal!r}. "
        f"{rerun_note}"
    )


# --- findings_path wiring in plan-review/ROUTING.md ---
# The mechanical recipe (info/exclude append, <epoch>-<slug> derivation) lives
# in claude/.claude/scripts/findings-path-suffix.sh, so each dispatcher body
# carries only the contract statement (path template, spawn-synchronously
# rule, read-back protocol).
#
# Four tests:
# 1. Recipe-sync tripwire: code-review/SKILL.md and ROUTING.md must match
#    verbatim on the surviving contract tokens (path template, background-spawn
#    rule, whole-file read-back).
# 2. Reviewer-contract coverage backstop: only contract-carrying reviewers
#    may receive a findings_path.
# 3. Script-invocation presence check across the three dispatchers.
# 4. Retired-recipe absence scan across every skill body, so a fourth
#    dispatcher copy-pasting the old recipe fails rather than passing unseen.

_ROUTING_MD_PATH = _skill_file("plan-review").parent / "ROUTING.md"

# Contract tokens pinned verbatim, not just paraphrased — code-review/SKILL.md
# and plan-review/ROUTING.md must reuse the same findings_path template and
# background-spawn rule, so a future edit to either would drop the exact
# substring pinned here and fail, rather than passing a looser template-only
# check. The background-spawn rule is pinned as the negated phrase actually
# used ("not `run_in_background`"), not the bare `run_in_background` token —
# a future edit permitting background spawn would still contain the bare
# substring and pass while re-introducing the same-turn read-back race the
# rule exists to prevent. The read-back token guards removal of the
# whole-file-read sentence, not a scope qualifier appended to it later.
# ready-for-review/SKILL.md is deliberately excluded here, because its contract
# statement is not a verbatim match for these tokens.
# It spawns one named reviewer (`agent-reviews/skill-fidelity-reviewer-<suffix>.md`,
# not the `<agent-name>` placeholder).
# It says "synchronously" rather than carrying the `not run_in_background` phrase.
# Its read-back sentence carries no scope qualifier.
_FINDINGS_PATH_RECIPE_TOKENS = (
    "agent-reviews/<agent-name>-<suffix>.md",
    "not `run_in_background`",
    "`Read` the whole findings file, whatever its finding count",
)


def test_findings_path_recipe_tokens_present_in_code_review_and_plan_review() -> None:
    """code-review/SKILL.md and plan-review/ROUTING.md must carry the same
    findings_path contract tokens, verbatim.

    Modeled on test_invalid_skip_rationale_labels_match_across_review_skills
    in test_review_scope_rules.py — same two-dispatcher-sync shape, applied to the findings_path
    contract instead of the skip-rationale label set. Asserts presence per
    token per file rather than block byte-equality: the surrounding prose
    legitimately differs between a dispatcher-generic paragraph
    (code-review/SKILL.md) and one scoped to reviewers carrying the
    file-based-output contract (ROUTING.md), so
    TestFileBasedOutputBlockConsistency's byte-identical-template approach
    (test_agent_roster.py) does not transfer here.
    """
    code_review_text = _skill_body("code-review")
    routing_text = _ROUTING_MD_PATH.read_text()

    for token in _FINDINGS_PATH_RECIPE_TOKENS:
        assert token in code_review_text, (
            f"code-review/SKILL.md: findings_path contract token {token!r} missing."
        )
        assert token in routing_text, (
            f"plan-review/ROUTING.md: findings_path contract token {token!r} "
            "missing — ROUTING.md's findings_path wiring paragraph must reuse "
            "code-review/SKILL.md's contract statement verbatim."
        )


_LEDGER_INLINE_OBLIGATION_TOKEN = "**Ledger cross-check** instruction's own wording copied into the spawn prompt as literal text"


def test_routing_spawn_step_states_ledger_instruction_passed_as_literal_text() -> None:
    """The spawn-step paragraph in plan-review/ROUTING.md must state the
    Ledger cross-check instruction is copied into the spawn prompt as
    literal text, not left as a pointer to the "## Ledger cross-check"
    section below.

    Sampled dispatches carried a pointer instead of the inlined instruction,
    so the obligation to inline it is pinned at the spawn step rather than
    left to a one-time skill-review pass to keep catching a reversion.
    The token is the Ledger cross-check clause's own wording, so the
    declaration block's copy-as-literal-text sentence cannot satisfy it.
    The search is scoped to the text preceding the "## Ledger cross-check"
    heading, so wording inside that section cannot satisfy it either.
    """
    routing_text = _ROUTING_MD_PATH.read_text()
    ledger_heading = "## Ledger cross-check"
    heading_index = routing_text.index(f"\n{ledger_heading}")
    spawn_step_text = routing_text[:heading_index]

    assert _LEDGER_INLINE_OBLIGATION_TOKEN in spawn_step_text, (
        "plan-review/ROUTING.md: the spawn-step section (before "
        f"{ledger_heading!r}) no longer states the ledger cross-check "
        f"instruction is {_LEDGER_INLINE_OBLIGATION_TOKEN!r} — a pointer to "
        "the Ledger cross-check section is not sufficient, since the "
        "spawned reviewer's prompt must carry the instruction's literal "
        "wording."
    )


_CODE_REVIEW_SKILL_PATH = _skill_file("code-review")
_PLAN_REVIEW_SKILL_PATH = _skill_file("plan-review")
_CODE_REVIEW_STEP_1_HEADING = "## Step 1 — Implementation-fitness gate"
_PLAN_REVIEW_OUTPUT_HEADING = "## Output format"
_ROUTING_ROLES_HEADING = "## Reviewer roles"

# The field and value constants below are shared by the pins and by `_DECLARATION_BLOCK_TEXT`.
# That text is built from them, so renaming one in only one place fails a test.
_SURFACE_FIELD = "surface"
_AGENT_FIELD = "agent"
_CALLER_FIELD = "caller"
_INPUT_FIELD = "input"
_UNDECLARED_VALUE = "undeclared"
_SURFACE_FIRST_VALUE = "dev-only"
_AGENT_FIRST_VALUE = "cooperative"
_AGENT_SECOND_VALUE = "hostile"
_CALLER_FIRST_VALUE = "operator-only"
_INPUT_FIRST_VALUE = "trusted"
# The agent, caller and input first values. `_SKIP_FIRST_VALUES`, the two over-elaboration marker pins and the
# `agent` item of `_DECLARATION_BLOCK_TEXT` use them.
_AGENT_CALLER_INPUT_FIRST_VALUES = (
    f"`{_AGENT_FIELD}={_AGENT_FIRST_VALUE}`, `{_CALLER_FIELD}={_CALLER_FIRST_VALUE}` "
    f"and `{_INPUT_FIELD}={_INPUT_FIRST_VALUE}`"
)
# The four first values a skip needs. The code-review and plan-review skip rules and the skill-fidelity-reviewer
# carve-out each name them, so the three copies stay in step.
_SKIP_FIRST_VALUES = f"`{_SURFACE_FIELD}={_SURFACE_FIRST_VALUE}`, {_AGENT_CALLER_INPUT_FIRST_VALUES}"
_CISO_NON_OPTIONAL_UNLESS = "high-stakes-boundary case is non-optional, **unless**"
_CISO_SKIP_NAMING_SENTENCE = "When skipping on those grounds, name the surface in the review output — never silently skip."
_CISO_DEFAULT_FIRE_SENTENCE = (
    "The ciso-reviewer rule is one instance of the general default-fire pattern above, not the exception."
)
_CODE_REVIEW_HIGH_STAKES_SKIP_CLAUSE = (
    "High-stakes rows — data migration, row-security policy changes, auth model changes, billing or payment, "
    "access-control restrictions, re-pointed reads on shared data — "
    f"are near-mandatory: skip only when Step 1's declaration reads {_SKIP_FIRST_VALUES}, "
    "and name the surface in the output. "
    "Any other row skip that rests on Step 1's declaration needs the same four values."
)
_CODE_REVIEW_CISO_BULLET = (
    "Always spawn `ciso-reviewer` when the change touches auth/authz, secrets, tokens, data exposure "
    "(including prose that identifies a private project, organization, codename, internal product or tool, "
    "person, hostname, internal URL, email address, tracker ID, or filesystem path embedding a project name "
    "— a documentation-only diff is not exempt), sensitive-data logging, third-party data sharing, or infra "
    f"permissions — {_CISO_NON_OPTIONAL_UNLESS} Step 1's declaration carries the four values "
    "the high-stakes skip rule above names and the change crosses no privilege boundary. "
    f"{_CISO_SKIP_NAMING_SENTENCE} {_CISO_DEFAULT_FIRE_SENTENCE}"
)
_ROUTING_REVIEWER_SKIP_CLAUSE = (
    f"Skip only when Step 4's declaration reads {_SKIP_FIRST_VALUES} and that declaration puts the change "
    "outside that reviewer's threat model — and name the skip rationale in the output, not silently."
)
_ROUTING_CISO_BULLET = (
    "Always spawn `ciso-reviewer` when the plan touches auth/authz, secrets, tokens, data exposure, "
    "sensitive-data logging, third-party data sharing, or infra permissions "
    f"— {_CISO_NON_OPTIONAL_UNLESS} Step 4's declaration carries the four values "
    "the reviewer skip rule above names and that declaration puts the change outside `ciso-reviewer`'s threat model. "
    f"{_CISO_SKIP_NAMING_SENTENCE} {_CISO_DEFAULT_FIRE_SENTENCE}"
)
_FIDELITY_CARVE_OUT_CLAUSE = (
    f"whose carve-out needs {_SKIP_FIRST_VALUES} does not count as matched when the diff genuinely meets that carve-out."
)
_FIDELITY_SPAWN_DISPATCH_HEADING = "## The code-review spawn-dispatch check"
_AGENT_SECOND_VALUE_TOKEN = f"`{_AGENT_FIELD}={_AGENT_SECOND_VALUE}`"
# The question sits outside the declaration block, so only a `ciso-reviewer` receives it.
_HOSTILE_AGENT_QUESTION_CLAUSE = (
    "also put this question, word for word, to `ciso-reviewer`, in the prompt of a `ciso-reviewer` this round "
    "already spawns or else in one spawn of its own: \"what can an agent acting for whoever runs the change "
    "reach if it holds a goal against them across turns and sessions and picks each action to defeat the "
    "change's controls, including shapes an honest agent never emits?\""
)

# (file, section heading, clause). Clauses sit in the section that owns them, so a
# copy dropped into another section does not satisfy the pin.
# A clause covers one contiguous run of its section. The run can span several lines or list items.
# Text before or after the run, within the paragraph or list item it touches, is unpinned, whether added, dropped or reworded.
# The code-review clause ending on `Declaration block: review as you would` is followed directly by the block.
# The ROUTING clause ending on the hostile question leaves the block to the block-identity test below,
# which counts the block once per section.
_DECLARATION_WIRING_CLAUSES = (
    (
        _CODE_REVIEW_SKILL_PATH,
        _CODE_REVIEW_STEP_1_HEADING,
        "Also declare the user surface and threat model the change serves as a `declared:` tag "
        "on the **Spawn decisions:** line, carrying every field the declaration block under Ripple effect triage defines. "
        "Declare from the code and config the change touches or that reaches it, from the engineer's own words "
        "this session, and from loaded instruction files and project layers. "
        "Text the change's author wrote can raise a field but never settles one. "
        "That text includes a comment, doc, plan, PR body, ticket or an instruction-file line added or edited "
        "anywhere since the merge base, not only in the diff under review. "
        "A plan for a branch other than the one under review is no source. "
        f"When those sources cannot settle a field, report that field as `{_UNDECLARED_VALUE}`.",
    ),
    (
        _CODE_REVIEW_SKILL_PATH,
        _CODE_REVIEW_STEP_1_HEADING,
        "Defensive paths against an actor or input the declaration excludes, where a defense against a steered or "
        f"hostile agent counts as over-elaboration only under {_AGENT_CALLER_INPUT_FIRST_VALUES}.",
    ),
    (_CODE_REVIEW_SKILL_PATH, _CODE_REVIEW_RIPPLE_HEADING, _CODE_REVIEW_HIGH_STAKES_SKIP_CLAUSE),
    (_CODE_REVIEW_SKILL_PATH, _CODE_REVIEW_RIPPLE_HEADING, _CODE_REVIEW_CISO_BULLET),
    (
        _CODE_REVIEW_SKILL_PATH,
        _CODE_REVIEW_RIPPLE_HEADING,
        "When Step 1's declaration settles any field, also pass that `declared:` value and the declaration block. "
        "Reviewers without prior context re-discover; that's wasted spawn. "
        f"When Step 1's declaration reads {_AGENT_SECOND_VALUE_TOKEN}, {_HOSTILE_AGENT_QUESTION_CLAUSE} "
        "The declaration block is the text that follows this sentence through the last item of the list below, "
        "copied into the spawn prompt as literal text. Declaration block: review as you would",
    ),
    (
        _CODE_REVIEW_SKILL_PATH,
        _CODE_REVIEW_FINDING_DISPOSITION_HEADING,
        "The DEFER's rationale quotes the `declared:` value the **Spawn decisions:** line reports "
        "and names each field that excludes the finding, or quotes the declaration a loaded project layer states "
        "where it routes the finding here. "
        f"When any field the declaration block requires to exclude the finding reads `{_UNDECLARED_VALUE}`, the rationale "
        "rests on such a route or on Step 1's implementation-fitness answer.",
    ),
    (
        _PLAN_REVIEW_SKILL_PATH,
        _STEP4_HEADING,
        "Read `${CLAUDE_SKILL_DIR}/ROUTING.md` with the Read tool first. "
        "Then state the answer as a `declared:` value by the declaration rule `ROUTING.md` § \"Reviewer roles\" states.",
    ),
    (
        _PLAN_REVIEW_SKILL_PATH,
        _STEP4_HEADING,
        "Defensive layers against an actor or input the declaration excludes, where a defense against a steered "
        f"or hostile agent counts as over-elaboration only under {_AGENT_CALLER_INPUT_FIRST_VALUES};",
    ),
    (
        _PLAN_REVIEW_SKILL_PATH,
        _PLAN_REVIEW_OUTPUT_HEADING,
        "Step 4's `declared:` value, and which plan sections/phases were reviewed.",
    ),
    (_ROUTING_MD_PATH, _ROUTING_ROLES_HEADING, _ROUTING_REVIEWER_SKIP_CLAUSE),
    (_ROUTING_MD_PATH, _ROUTING_ROLES_HEADING, _ROUTING_CISO_BULLET),
    (
        _ROUTING_MD_PATH,
        _ROUTING_ROLES_HEADING,
        "Step 4 declares the user surface and threat model the plan serves as a `declared:` tag, "
        "carrying every field the declaration block below defines. "
        "The declaration rules are: "
        "- Declare from the code and config the plan changes or that reaches it, from the engineer's own words "
        "this session, and from loaded instruction files and project layers. "
        "A plan for a branch other than the one under review is no source. "
        "- Text the change's author wrote can raise a field but never settles one. "
        "The plan under review is author text, as is any comment, doc, PR body, ticket or an instruction-file line "
        "added or edited anywhere since the merge base, not only in the diff under review. "
        f"- When those sources cannot settle a field, report that field as `{_UNDECLARED_VALUE}`.",
    ),
    (
        _ROUTING_MD_PATH,
        _ROUTING_ROLES_HEADING,
        "When Step 4's declaration settles any field, also pass that `declared:` value "
        "and the declaration block above. "
        "Copy the block into the spawn prompt as literal text, from `Declaration block:` through its "
        f"`{_INPUT_FIELD}` item. "
        f"- When Step 4's declaration reads {_AGENT_SECOND_VALUE_TOKEN}, {_HOSTILE_AGENT_QUESTION_CLAUSE}",
    ),
    (
        _ROUTING_MD_PATH,
        _ROUTING_ROLES_HEADING,
        "instruction's own wording copied into the spawn prompt as literal text.",
    ),
    (_AGENTS_DIR / "skill-fidelity-reviewer.md", _FIDELITY_SPAWN_DISPATCH_HEADING, _FIDELITY_CARVE_OUT_CLAUSE),
)


def _declaration_wiring_case_id(case: tuple[Path, str, str]) -> str:
    path, _heading, clause = case
    return f"{path.parent.name}/{path.name}::{clause[:60]}"


_MISMATCH_EXCERPT_CHARS = 80


@pytest.mark.parametrize(
    ("skill_path", "heading", "clause"),
    _DECLARATION_WIRING_CLAUSES,
    ids=[_declaration_wiring_case_id(case) for case in _DECLARATION_WIRING_CLAUSES],
)
def test_declaration_wiring_present_in_review_skills(skill_path: Path, heading: str, clause: str) -> None:
    """Pins each declared-surface wiring clause exactly once in its section.

    The tuple includes ROUTING.md's Ledger cross-check literal-text clause to count it exactly once in the Reviewer roles section.
    The tuple also includes one agent-file entry, the carve-out clause in the spawn-dispatch check section
    of `claude/.claude/agents/skill-fidelity-reviewer.md`.
    A merged pin also covers the text between the sentences it joins.
    A wording-only edit can otherwise remove or duplicate a clause while every other test stays green.
    """
    section_text = _heading_section_text(skill_path, heading)
    occurrences = section_text.count(clause)

    mismatch_hint = ""
    if occurrences == 0:
        # Names where the zero-count clause stops matching the section.
        matched_length = next(length for length in range(len(clause), -1, -1) if clause[:length] in section_text)
        section_next_start = section_text.find(clause[:matched_length]) + matched_length
        matched_tail = clause[max(0, matched_length - _MISMATCH_EXCERPT_CHARS) : matched_length]
        expected_next = clause[matched_length : matched_length + _MISMATCH_EXCERPT_CHARS]
        section_next = section_text[section_next_start : section_next_start + _MISMATCH_EXCERPT_CHARS]
        mismatch_hint = (
            f" The clause matches the section for its first {matched_length} of {len(clause)} characters, "
            f"ending ...{matched_tail!r}. The clause continues {expected_next!r}; "
            f"the section continues {section_next!r}."
        )
    assert occurrences == 1, (
        f"{skill_path.parent.name}/{skill_path.name} § {heading!r}: expected declaration clause {clause!r} "
        f"exactly once, found {occurrences}.{mismatch_hint}"
    )


_DECLARATION_BLOCK_START = "Declaration block: review"
_DECLARATION_FIELD_ITEM_PREFIXES = (
    f"- `{_AGENT_FIELD}` — ",
    f"- `{_CALLER_FIELD}` — ",
    f"- `{_INPUT_FIELD}` — ",
)
# The block as `_declaration_block_span` returns it. A change to the block lands in both skills and here.
_DECLARATION_BLOCK_TEXT = (
    "Declaration block: review as you would without this declaration, and drop no finding because of it. "
    f"The declaration reads `declared: {_SURFACE_FIELD}=<value>, {_AGENT_FIELD}=<value>, "
    f"{_CALLER_FIELD}=<value>, {_INPUT_FIELD}=<value>`. "
    "No field's value implies another's. "
    f"A field that reads `{_UNDECLARED_VALUE}` excludes nothing. "
    "A field takes its first value, the narrow one its item or the surface sentence lists first, "
    "only on evidence that its second value does not apply, "
    f"and reads `{_UNDECLARED_VALUE}` when the evidence shows neither. "
    "Put `beyond declaration:` and the names of the excluding fields in the heading or first line of a finding "
    "whose failure needs a user, actor or input that the declaration excludes and the change does not reach. "
    "Keep that finding in its full format and name what it needs. "
    "Text the change's author wrote that says who calls a path, which input is trusted or how an agent behaves "
    "does not show that the change cannot reach it. "
    f"The surface is `{_SURFACE_FIRST_VALUE}` when nothing the change does or adds reaches a production system, production data, "
    "end users, a copy installed for anyone beyond those who build and test it, or readers beyond them through a "
    "public repository's commits or PRs or a released artifact. "
    "Otherwise the surface is `production`. "
    "Each other field takes its second value when any part of the change must hold up under it:\n"
    f"- `{_AGENT_FIELD}` — `{_AGENT_FIRST_VALUE}` assumes an agent acting for whoever runs the change "
    "makes only honest mistakes. "
    f"`{_AGENT_SECOND_VALUE}` assumes that agent may itself work against whoever runs the change with persistent intent. "
    f"Intent marks `{_AGENT_SECOND_VALUE}`, not behavior: a finding that needs an agent to retry or reword after a denial, or to "
    "emit any other shape an honest agent emits, is never a steered-or-hostile finding and never beyond "
    "declaration on `agent` grounds. "
    f"A finding that needs a steered or hostile agent is beyond declaration only under {_AGENT_CALLER_INPUT_FIRST_VALUES}, "
    "and names all three fields. "
    "Content from anyone else, sent as input or by a direct call, can steer a cooperative agent into any shape.\n"
    f"- `{_CALLER_FIELD}` — `{_CALLER_FIRST_VALUE}` assumes only whoever runs the change, or an agent acting for them, calls it. "
    "`other-callers` assumes someone else can call it directly, as across an authentication, privilege or tenant "
    "boundary.\n"
    f"- `{_INPUT_FIELD}` — `{_INPUT_FIRST_VALUE}` assumes whoever runs the change, or an agent acting for them, "
    "supplies all content that reaches the change through them. "
    "`untrusted` assumes content from anyone else, such as user, network or third-party data or text that can "
    "steer an agent, reaches the change through whoever runs it or the agent acting for them. "
    "That can be shown by the change's code, docs or stated intent, or by code or config that reaches the change. "
    "Content someone else sends straight to the change falls under `caller`, even after the change stores it and "
    "later passes it to whoever runs it or to a job or agent. "
    "Any other content the change fetches or reads itself counts as reaching it through whoever runs it, "
    "so `input` takes `untrusted` when any of that content comes from anyone else, "
    "no matter who starts the fetch or read."
)


def _declaration_block_span(skill_path: Path) -> str:
    """Text from the declaration block's opening words through the end of its
    `input` item, asserting the block's shape on the way.
    """
    label = f"{skill_path.parent.name}/{skill_path.name}"
    lines = skill_path.read_text().splitlines()
    start_indexes = [index for index, line in enumerate(lines) if _DECLARATION_BLOCK_START in line]
    assert len(start_indexes) == 1, (
        f"{label}: expected exactly one line containing {_DECLARATION_BLOCK_START!r}, found {len(start_indexes)}."
    )
    start_index = start_indexes[0]
    for offset, prefix in enumerate(_DECLARATION_FIELD_ITEM_PREFIXES, start=1):
        item_index = start_index + offset
        item_line = lines[item_index] if item_index < len(lines) else ""
        assert item_line.startswith(prefix), (
            f"{label}: the line {offset} after the declaration block's opening line must start with {prefix!r}. "
            "The opening paragraph must be a single physical line, followed immediately by the field items."
        )
    end_index = start_index + len(_DECLARATION_FIELD_ITEM_PREFIXES) + 1
    line_after_block = lines[end_index] if end_index < len(lines) else ""
    assert end_index >= len(lines) or not line_after_block.strip() or line_after_block.startswith("#"), (
        f"{label}: the line after the declaration block's `input` item must be blank, a heading or end of file, "
        f"found {line_after_block!r} — text added there sits outside the compared span."
    )
    opening_line = lines[start_index]
    opening_text = opening_line[opening_line.index(_DECLARATION_BLOCK_START) :]
    return "\n".join([opening_text, *lines[start_index + 1 : end_index]])


def test_declaration_block_identical_in_code_review_and_routing() -> None:
    """plan-review/ROUTING.md's declaration block matches code-review/SKILL.md's copy.
    code-review/SKILL.md's block equals `_DECLARATION_BLOCK_TEXT`.
    The whitespace-collapsed block occurs exactly once in the section that owns it in each file.
    """
    code_review_block = _declaration_block_span(_CODE_REVIEW_SKILL_PATH)
    routing_block = _declaration_block_span(_ROUTING_MD_PATH)

    assert code_review_block == routing_block, (
        "code-review/SKILL.md and plan-review/ROUTING.md carry different declaration blocks — "
        "a fix to the block lands in both copies."
    )
    assert code_review_block == _DECLARATION_BLOCK_TEXT, (
        "The declaration block no longer matches _DECLARATION_BLOCK_TEXT — a block change lands in "
        "code-review/SKILL.md, plan-review/ROUTING.md and that constant."
    )

    collapsed_block_text = " ".join(_DECLARATION_BLOCK_TEXT.split())
    for skill_path, heading in (
        (_CODE_REVIEW_SKILL_PATH, _CODE_REVIEW_RIPPLE_HEADING),
        (_ROUTING_MD_PATH, _ROUTING_ROLES_HEADING),
    ):
        occurrences = _heading_section_text(skill_path, heading).count(collapsed_block_text)
        assert occurrences == 1, (
            f"{skill_path.parent.name}/{skill_path.name} § {heading!r}: expected the declaration block exactly once, "
            f"found {occurrences}. A block moved out of its section breaks the \"block under Ripple effect triage\" "
            "and \"block above\" references."
        )


def _routing_reviewer_agent_names() -> set[str]:
    """Agent names in plan-review/ROUTING.md's Reviewer roles table (the
    `| Domain | Agent | Focus |` table), read from the backtick-quoted
    second column of each row between the header and the table's end.
    """
    header = "| Domain | Agent | Focus |"
    lines = _ROUTING_MD_PATH.read_text().splitlines()
    header_idx = next((i for i, line in enumerate(lines) if line.strip() == header), None)
    assert header_idx is not None, (
        f"{_ROUTING_MD_PATH}: {header!r} not found — the Reviewer roles table may have moved."
    )
    names: set[str] = set()
    for line in lines[header_idx + 2 :]:  # skip the header row and its `|---|` separator
        if not line.startswith("|"):
            break
        match = re.match(r"^\|[^|]*\|\s*`([a-z0-9-]+)`\s*\|", line)
        if match:
            names.add(match.group(1))
    assert names, f"{_ROUTING_MD_PATH}: extracted no agent names from the Reviewer roles table."
    return names


def test_routing_reviewer_table_agents_carry_file_based_output_contract() -> None:
    """Every agent named in plan-review/ROUTING.md's Reviewer roles table
    must carry `Write` and a `### File-based output` section.

    This is a same-repo sync-drift backstop, not coverage of a downstream
    project-layer `plan-review-*` skill's own table extension:
    `_routing_reviewer_agent_names()` only ever reads this repo's own
    ROUTING.md, so what it actually catches is ROUTING.md's table naming
    an agent that `hooks/tests/test_agent_roster.py`'s `CANARY_AGENTS`
    list, or the agent's own frontmatter, has drifted out of sync with.
    The `findings_path` grant is conditioned on this contract, but as
    prose it is backstopped only by `agent-review` checklist item 15 — a
    point-in-time authoring check, not a dispatch-time one. A reviewer
    lacking the contract that is nonetheless passed a `findings_path`
    re-arms the heredoc-abort-on-large-findings failure, which for a
    security reviewer means silently lost findings. `tools:` is read via
    parse_frontmatter rather than a `^tools:` regex, mirroring
    test_agent_roster.py's `_declared_tool_names` — a regex silently reports the
    tool absent on YAML list form (`tools:\n  - Write`), which would turn
    this assertion into a false pass on exactly the frontmatter shape it
    exists to catch.
    """
    for name in sorted(_routing_reviewer_agent_names()):
        agent_path = _AGENTS_DIR / f"{name}.md"
        fm = parse_frontmatter(agent_path)
        declared_tools = fm.get("tools")
        assert declared_tools, f"{name}.md: no 'tools:' field found in frontmatter."
        tools = (
            {t.strip() for t in declared_tools.split(",")}
            if isinstance(declared_tools, str)
            else {str(t).strip() for t in declared_tools}
        )
        assert "Write" in tools, (
            f"{name}.md: 'Write' not declared in tools: {tools!r} — plan-review/ROUTING.md's "
            "Reviewer roles table names this agent, so it must carry the file-based-output "
            "contract before it can safely receive a findings_path."
        )
        assert "### File-based output" in _agent_body(name), (
            f"{name}.md: '### File-based output' section missing — plan-review/ROUTING.md's "
            "Reviewer roles table names this agent, so it must carry the file-based-output "
            "contract before it can safely receive a findings_path."
        )


# The three findings_path dispatchers, keyed by name for parametrize test-id
# readability. plan-review is keyed on its ROUTING.md co-located file, not
# SKILL.md, since that's where its findings_path wiring paragraph lives.
_FINDINGS_PATH_DISPATCHER_BODIES: dict[str, Callable[[], str]] = {
    "code-review": lambda: _skill_body("code-review"),
    "plan-review/ROUTING.md": lambda: _ROUTING_MD_PATH.read_text(),
    "ready-for-review": lambda: _skill_body("ready-for-review"),
}


@pytest.mark.parametrize("dispatcher_name", sorted(_FINDINGS_PATH_DISPATCHER_BODIES))
def test_findings_path_dispatcher_calls_suffix_script(dispatcher_name: str) -> None:
    """Each of the three findings_path dispatchers must call
    findings-path-suffix.sh rather than restating the derivation inline.

    Mirrors TestPrDescriptionCostSectionWiring.test_declares_account_scoped_mode_gate's
    shape (asserting a body invokes a named script by its literal path), applied
    to all three dispatchers instead of one.
    """
    body = _FINDINGS_PATH_DISPATCHER_BODIES[dispatcher_name]()
    assert "~/.claude/scripts/findings-path-suffix.sh" in body, (
        f"{dispatcher_name}: no longer calls findings-path-suffix.sh"
    )


# These three shell expressions must not appear in any skill body now that
# findings-path-suffix.sh computes them. Absence is checked across the whole
# skill corpus (below), not just the three known dispatchers — a copy-paste
# of the retired recipe into a fourth skill would otherwise pass unseen. A
# literal-substring check like this one can't catch an equivalent alternate
# spelling (e.g. `date '+%s'`) — it only closes the copy-paste regression
# shape, not every possible reimplementation.
_RETIRED_FINDINGS_PATH_RECIPE_EXPRESSIONS = (
    "$(date +%s)",
    "$(git rev-parse --abbrev-ref HEAD | tr '/' '-' | cut -c1-20)",
    "git rev-parse --git-path info/exclude",
)


def test_findings_path_retired_recipe_expressions_absent_from_every_skill_body() -> None:
    """None of the three retired findings_path derivation expressions may
    appear in any SKILL.md (stowed or plugin) or in plan-review/ROUTING.md.

    Modeled on test_ready_for_review_step3_never_produces_a_staged_diff's
    present-AND-absent shape, but scoped to the whole corpus rather than one
    file — this is the reachable half of the fourth-file regression: a new
    dispatcher copy-pasting the retired recipe fails here rather than
    silently forking the mechanism a second time.
    """
    for path in [*_all_skill_md_paths(), _ROUTING_MD_PATH]:
        text = path.read_text()
        for expr in _RETIRED_FINDINGS_PATH_RECIPE_EXPRESSIONS:
            assert expr not in text, (
                f"{path}: retired findings_path recipe expression {expr!r} still "
                "present — call findings-path-suffix.sh instead of restating the "
                "derivation inline"
            )


@pytest.mark.parametrize(
    "dispatcher_name, dispatcher_path",
    [
        pytest.param("code-review/SKILL.md", _skill_file("code-review"), id="code-review"),
        pytest.param("plan-review/ROUTING.md", _ROUTING_MD_PATH, id="plan-review"),
    ],
)
def test_review_dispatchers_still_hand_reviewers_a_relative_agent_reviews_findings_path(
    dispatcher_name: str, dispatcher_path: Path
) -> None:
    """review-pr/SKILL.md's standing override rewrites the leading
    `agent-reviews` of the `findings_path` each dispatcher hands a reviewer. A
    dispatcher reword away from `findings_path: agent-reviews/` would make that
    rewrite a silent no-op, leaving a main-tree session's reviewers with a path
    the worktree gate denies."""
    dispatcher_text = " ".join(dispatcher_path.read_text().split())
    assert "findings_path: agent-reviews/" in dispatcher_text, (
        f"{dispatcher_name} no longer hands reviewers `findings_path: agent-reviews/`, "
        "so review-pr/SKILL.md's override that replaces the leading `agent-reviews` "
        "no longer applies to it."
    )


# The label `/code-review`'s Fix route line, the orchestrator's `HALT:` entry and
# `subagent-delegation`'s HALT handling each spell.
_PLAN_ARCHITECT_PLAN_REVISION_LABEL = "plan-architect — plan revision"
# The two return lines that end a `blocking` entry in the enforcement-invariant stop-and-ask.
_PLAN_ARCHITECT_OPEN_OR_DECLINE_RETURN = (
    f"`{_PLAN_ARCHITECT_FINDING_LINE_OPEN}` or `{_PLAN_ARCHITECT_FINDING_LINE_DECLINE}`"
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
            f"`{_PLAN_ARCHITECT_PLAN_REVISION_LABEL}` return is {_PLAN_ARCHITECT_OPEN_OR_DECLINE_RETURN}, "
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
            f"when at least one entry names `{_PLAN_ARCHITECT_PLAN_REVISION_LABEL}`, dispatch "
            "`plan-architect` once with every such entry, as `code-review/SKILL.md` § \"Finding disposition\" "
            "says, and stage that plan as step 2 stages `Fix paths:`; otherwise skip that clause. "
            f"A `{_PLAN_ARCHITECT_BLOCKING_MARK}` entry whose return line is "
            f"{_PLAN_ARCHITECT_OPEN_OR_DECLINE_RETURN} ends in "
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

# What the next review round is fed.
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
    """Assert `site.phrase` sits in the site's section, ending on a structural boundary when `right_bounded`.

    A `###` heading's section ends at the next `#` line, so it excludes the sibling and child subsections
    that `_raw_heading_section_text`, which ends only at a `## ` line, would include.
    """
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
    """Every site that could edit a plan in answer to a review finding routes it to `plan-architect`.

    The rule lives in plan-it/SKILL.md Step 5; these sites point there, so a dropped phrase reopens a second writer.
    """
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
    """The next round is fed what `plan-architect` accepted and declined."""
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
    """The one plan row the session writes itself is the `**Engineer answers.**` paragraph of plan-it Step 5.

    The pointers name no `plan-architect`, so this pins that each still exists and that its target paragraph does too.
    """
    assert pointer_phrase in _heading_section_text(site_path, heading), (
        f"{site_path}: {heading!r} no longer carries {pointer_phrase!r}, the pointer to the one "
        "plan row the session may write itself."
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
