"""Pins on code-review's clean definition and its contradiction-route, defer-invariant and new-primitive rules."""
from __future__ import annotations

from _skill_md_helpers import (
    _CODE_REVIEW_CONTRADICTION_ROUTE_ANCHOR,
    _CODE_REVIEW_DEFER_CRITERIA_HEADING,
    _CODE_REVIEW_DEFER_INVARIANT_ANCHOR,
    _CODE_REVIEW_FINDING_DISPOSITION_HEADING,
    _CODE_REVIEW_NEW_PRIMITIVE_ROUTE_ANCHOR,
    _assert_pinned_clause_right_bounded,
    _heading_section_text,
    _normalized_anchor_text,
    _raw_heading_section_text,
    _skill_file,
)

_CODE_REVIEW_RECORD_COMPLETION_HEADING = "## Step — Record review completion"

# The clean-definition sentence: a finding logged DEFER or SETTLED, by a
# consult, the human, or a carry, counts as resolved, so none of them blocks
# the review-completion marker written by `marker.sh write code-review`.
_PINNED_CLEAN_DEFINITION_CLAUSE = (
    "A finding logged DEFER or SETTLED (by a consult, the human, or a carry) "
    "counts as resolved. If the review is **clean** (no blockers, no "
    "unresolved critical findings, and you reviewed the currently staged "
    "changes), record it by running this command exactly once:"
)


class TestCodeReviewCleanDefinitionCountsSettledAndDefer:
    """Pin code-review/SKILL.md's clean-definition sentence, so a future edit
    can't silently drop the DEFER or SETTLED branch (a consult, human, or
    carry decision) and make a settled-keep finding block the
    review-completion marker.
    """

    def test_clean_definition_clause_matches_live_text(self) -> None:
        raw_section = _raw_heading_section_text(
            _skill_file("code-review"), _CODE_REVIEW_RECORD_COMPLETION_HEADING
        )
        pinned_text = " ".join(_PINNED_CLEAN_DEFINITION_CLAUSE.split())
        _assert_pinned_clause_right_bounded(
            pinned_text,
            raw_section,
            context="code-review/SKILL.md: clean-definition clause no longer matches.",
        )


# The whole contradiction-route region: the consult route, the site definition,
# the settled-site and two-rewrites human stop, the three verdicts, the
# enforcement-invariant carve-out on *keep current text*, the
# no-explicit-verdict blocking stop, and how a keep is logged and carried. It
# is pinned whole so removing or weakening any sentence fails a test. The whole
# region is compared by exact equality, so any added, removed, or reworded text
# inside the anchors fails. The mid-sentence "- " tokens are SKILL.md's
# verdict bullets after whitespace collapse, not typos.
_PINNED_CONTRADICTION_ROUTE_CLAUSE = (
    "**A finding whose fix would undo a fix an earlier round applied "
    "is also a design question, in every round, staged commit-gate "
    "rounds included.** Write `plan-architect — consult` for it on the "
    "`Fix route:` line. Dispatch, verbatim relay, and the disagreement "
    "stop-and-ask follow the heavier-mechanism rule directly above, "
    "and the consult prompt also carries the earlier finding and its "
    "fix (the consult never invokes `review-ledger.sh` or `marker.sh`). A "
    "site is the file plus the contiguous block — paragraph, list "
    "item, table row, or function — that an earlier round's fix "
    "edited, that a live DEFER or SETTLED decision's `--source` names, "
    "or, when the earlier round's outcome was *keep current text* with "
    "nothing edited, the block the settled finding's own cited "
    "location named. A finding's location is matched against that site "
    "via the ledger's `--source` field or the "
    "fix commit's own diff hunk, read generously enough to include an "
    "adjacent or wrapped continuation of the same clause and any "
    "duplicate expression of the same defect elsewhere in the block — "
    "a finding is not a different site merely because its cited "
    "location sits just outside the literal edited or cited range. A "
    "finding against a site an earlier verdict already settled, or "
    "that two earlier rounds' fixes already rewrote, goes straight to "
    "the human as a blocking stop-and-ask, with no consult, unless it "
    "carries as below. Count those rewrites from the ledger, never from "
    "recall: write the branch's rows with "
    "`~/.claude/scripts/review-ledger.sh show --out "
    "agent-reviews/review-history-<suffix>.md`, Grep that file for the "
    "finding's path, and count the earlier rounds holding an ADDRESS row "
    "on that path whose `finding` and `rationale` concern this block. The "
    "path is the key, because a row's range gives its own round's lines "
    "and later fixes shift them, so the range is a hint, never a test. A "
    "row the recorded text cannot place in or out of this block makes the "
    "match uncertain, so that error is over-firing, which stops "
    "for the engineer. The count sees only where findings pointed, so a "
    "fix that landed at another path is not counted, an accepted miss. "
    "`unchanged` writes no file. "
    "It counts zero only when no earlier round of this session logged a "
    "row, and is uncertain otherwise. A non-zero exit makes the match "
    "uncertain. That stop names its trigger — a script "
    "rejection (relay its reason), a different failure mode, an "
    "uncertain match, or an invariant-class finding — and quotes the "
    "earlier decision's words, date and round. The consult's judgment "
    "standard is that the current text wins unless the finding names a "
    "defect, under a stated rule, that the current text actually has. "
    "One consult carries every such finding in the round and returns "
    "exactly one of the three verdicts per finding: - *Keep current "
    "text* resolves it with nothing dispatched, logged as "
    "`--disposition SETTLED --decided-by plan-architect` with the "
    "verdict in `--rationale` and a range-form `--source` naming the "
    "whole block, and is never available to a finding the "
    "enforcement-invariant rule below covers. - *Apply this round's fix* "
    "is an ordinary ADDRESS row on the `code-writer` route. - *Cannot "
    "choose* is a blocking stop-and-ask to the human. A finding with "
    "no explicit per-finding verdict from the consult (failed "
    "dispatch, empty, hedged, or partial coverage) is likewise a "
    "blocking stop-and-ask, never *keep current text*. A human keep is "
    "logged `--disposition SETTLED --decided-by engineer "
    "--engineer-quote '<their words>'` with a range naming the whole "
    "block (widen when unsure). It also carries `--ref <id>` to the "
    "live earlier decision on the same failure mode, if any (take ids "
    "from the digest's Id column; `append` prints none). It "
    "adds `--carry-forward` only when the engineer's answer states no "
    "scope or time limit, neither declines carries nor asks to be asked "
    "again, and the enforcement-invariant rule below does not apply. "
    "A keep \"for now\" or \"just this file\", a decline, or an ask to "
    "be asked again is logged without `--carry-forward`. "
    "Relay the `stored engineer quote:` line. Every "
    "stop-and-ask in this section whose keep is logged this way first "
    "tells the engineer that the answer is quoted in the public "
    "PR body, where tracker IDs, UUIDs, long hex runs, home paths and "
    "blocklisted names block the update, and, except at the "
    "enforcement-invariant stop, that the keep also applies without asking to "
    "same-failure-mode repeats on this unchanged block unless they "
    "decline or limit it. A same-failure-mode repeat at a live DEFER decision, or "
    "at a live engineer SETTLED logged `--carry-forward`, carries "
    "without a stop. Apply the enforcement-invariant rule to the new "
    "finding first, since an invariant-class finding never carries. Then "
    "log it with the decision's disposition, `--decided-by carry --ref "
    "<id>`, `--rationale` naming the shared defect, the reviewer's "
    "`--cited-line`, and a `--source` range reproducing the "
    "decided text at its current lines (rules: `--help`). A DEFER "
    "carry also restates `--defer-criterion` after re-running the "
    "closed list. A "
    "repeat that does not carry takes the stop at a SETTLED site and a "
    "fresh disposition against the closed list at a DEFER site. An "
    "ADDRESS or fresh DEFER of a repeat carries `--ref <id>` so the old "
    "row retires; another finding at the site leaves it live. The "
    "round report relays each `carry of decision` line, and a reopen "
    "is logged `ADDRESS --ref <id> --relog` with the decision's `--source`, "
    "which retires the decision and its carries from the PR block."
)


class TestCodeReviewContradictionRouteRegionPin:
    """Pin code-review/SKILL.md's contradiction-route region whole, so dropping
    any of these rules fails a test instead of drifting silently:

    - the enforcement-invariant carve-out on *keep current text*;
    - the settled-site / two-rewrites human stop;
    - the no-explicit-verdict blocking stop-and-ask;
    - the consent notice before an engineer keep is logged;
    - `--carry-forward` only for an answer with no scope or time limit;
    - the carry rules: the invariant check before a carry, and a `--source`
      range reproducing the decided text at its current lines (the rest of the
      carry rules live in `--help`, pinned by test_review_ledger_script.py);
    - the `--ref` that retires a decision, and the `ADDRESS --ref` reopen;
    - the consult prompt's bar on invoking `review-ledger.sh` or `marker.sh`.

    It also checks the referent and the ordering the region cites. The heavier-mechanism rule must
    still state its disagreement stop-and-ask, and the region must sit after that rule and before
    both the DEFER criteria heading and the defer-invariant region.
    """

    def test_contradiction_route_region_matches_live_text(self) -> None:
        skill_md_path = _skill_file("code-review")
        live_text = _normalized_anchor_text(
            skill_md_path, _CODE_REVIEW_CONTRADICTION_ROUTE_ANCHOR
        )
        pinned_text = " ".join(_PINNED_CONTRADICTION_ROUTE_CLAUSE.split())
        assert live_text == pinned_text, (
            f"{skill_md_path}: {_CODE_REVIEW_CONTRADICTION_ROUTE_ANCHOR} no longer "
            f"matches its pinned text.\n"
            f"  live:   {live_text!r}\n"
            f"  pinned: {pinned_text!r}"
        )

    def test_cited_disagreement_stop_still_exists(self) -> None:
        """The region defers its disagreement stop-and-ask to the heavier-mechanism rule, which must still state it."""
        skill_md_path = _skill_file("code-review")
        disagreement_stop = (
            "A disagreement between the orchestrator and the returned recommendation "
            "is a blocking stop-and-ask to the human"
        )
        heavier_mechanism_text = _normalized_anchor_text(
            skill_md_path, _CODE_REVIEW_NEW_PRIMITIVE_ROUTE_ANCHOR
        )
        assert disagreement_stop in heavier_mechanism_text, (
            f"{skill_md_path}: the heavier-mechanism region must still contain "
            f"{disagreement_stop!r}, which the contradiction-route region cites"
        )

    def test_region_sits_between_new_primitive_route_and_defer_criteria(self) -> None:
        """The region sits after the heavier-mechanism region it cites as 'directly
        above', and before both the DEFER criteria heading and the defer-invariant
        region, which its 'below' citations name as the enforcement-invariant rule."""
        skill_md_path = _skill_file("code-review")
        raw_text = skill_md_path.read_text()
        new_primitive_route_end = raw_text.find(
            f"<!-- {_CODE_REVIEW_NEW_PRIMITIVE_ROUTE_ANCHOR} end -->"
        )
        contradiction_route_start = raw_text.find(
            f"<!-- {_CODE_REVIEW_CONTRADICTION_ROUTE_ANCHOR} start -->"
        )
        contradiction_route_end = raw_text.find(
            f"<!-- {_CODE_REVIEW_CONTRADICTION_ROUTE_ANCHOR} end -->"
        )
        defer_criteria = raw_text.find(_CODE_REVIEW_DEFER_CRITERIA_HEADING)
        defer_invariant_start = raw_text.find(
            f"<!-- {_CODE_REVIEW_DEFER_INVARIANT_ANCHOR} start -->"
        )
        offsets = (
            new_primitive_route_end,
            contradiction_route_start,
            contradiction_route_end,
            defer_criteria,
            defer_invariant_start,
        )
        assert -1 not in offsets, (
            f"{skill_md_path}: placement needs the new-primitive-route end anchor, both "
            f"contradiction-route anchors, {_CODE_REVIEW_DEFER_CRITERIA_HEADING} and the "
            f"{_CODE_REVIEW_DEFER_INVARIANT_ANCHOR} start anchor; offsets found: {offsets}"
        )
        assert new_primitive_route_end < contradiction_route_start, (
            f"{skill_md_path}: {_CODE_REVIEW_CONTRADICTION_ROUTE_ANCHOR} start anchor must "
            f"fall after the {_CODE_REVIEW_NEW_PRIMITIVE_ROUTE_ANCHOR} end anchor"
        )
        assert contradiction_route_end < defer_criteria, (
            f"{skill_md_path}: {_CODE_REVIEW_CONTRADICTION_ROUTE_ANCHOR} end anchor must "
            f"fall before {_CODE_REVIEW_DEFER_CRITERIA_HEADING}"
        )
        assert contradiction_route_end < defer_invariant_start, (
            f"{skill_md_path}: {_CODE_REVIEW_CONTRADICTION_ROUTE_ANCHOR} end anchor must "
            f"fall before the {_CODE_REVIEW_DEFER_INVARIANT_ANCHOR} start anchor"
        )


# The whole defer-invariant region: the enforcement-invariant class definition,
# its never-DEFER-eligible ruling, the ADDRESS-or-blocking-stop disposition,
# the scope of the bar (an invariant break a round notices anywhere in the PR),
# and its precedence over checklist item 14's informational-only route.
# The contradiction-route region's *keep current text* carve-out takes its scope
# from this class, so it is pinned whole by exact equality, like that region.
_PINNED_DEFER_INVARIANT_CLAUSE = (
    "- **\"Enforcement invariant weakened, but disclosed\"** — a "
    "finding that the diff opens a path around an enforcement "
    "invariant (a gate, hook, permission check, required-approval, or "
    "marker guarantee some mechanism currently makes unbypassable) is "
    "never DEFER-eligible, regardless of which criterion above seems "
    "to match. Disposition is ADDRESS (fix the hole) or a blocking "
    "stop-and-ask to the human, whose keep is logged with "
    "`--enforcement-invariant` and without `--carry-forward`: it is "
    "asked again on every re-raise, never carried, and never DEFERred. "
    "Approval of a diff or PR does not function as informed consent "
    "for an invariant-break buried in the body. The bar applies to an "
    "invariant break a round notices anywhere in the PR, not only inside "
    "the diff that round enumerates (the staged diff in a staged round, "
    "the PR against its base in the cumulative pass). Checklist item 14's "
    "informational-only route does not apply to such a break."
)


_ENFORCEMENT_INVARIANT_CONSULT_STOP_SENTENCE = (
    "For a finding the enforcement-invariant rule below covers, Endorsed with "
    "no plan file and Rejected each end in that rule's blocking stop-and-ask, "
    "since neither fixes the hole."
)


class TestCodeReviewDeferInvariantRegionPin:
    """Pin the text that keeps an enforcement-invariant break from being
    deferred or silently accepted, so drifting from it fails a test.

    Whole-region equality against _PINNED_DEFER_INVARIANT_CLAUSE guards:
    - the never-DEFER-eligible ruling;
    - the enforcement-invariant class definition;
    - the ADDRESS-or-blocking-stop-and-ask disposition;
    - the bar covering an invariant break noticed anywhere in the PR, not only
      the diff a round enumerates;
    - the sentence keeping checklist item 14's informational-only route from
      absorbing such a break.

    Two narrower checks guard the rest:
    - The Finding disposition section must contain the walk clause that adds an
      orchestrator-noticed invariant break to the disposition walk. This pins
      the clause's presence in that section, not the walk sentence's structure.
    - The new-primitive-route region must contain
      _ENFORCEMENT_INVARIANT_CONSULT_STOP_SENTENCE, which ends the
      Endorsed-with-no-plan-file and Rejected returns of an enforcement-invariant
      finding's heavier-mechanism consult in the blocking stop-and-ask. The region
      must also keep the `**Rejected` outcome bullet the sentence names.

    On failure, update the pinned text only if the new wording preserves what
    every sentence of the current pinned text guarantees.
    """

    def test_defer_invariant_region_matches_live_text(self) -> None:
        skill_md_path = _skill_file("code-review")
        live_text = _normalized_anchor_text(
            skill_md_path, _CODE_REVIEW_DEFER_INVARIANT_ANCHOR
        )
        pinned_text = " ".join(_PINNED_DEFER_INVARIANT_CLAUSE.split())
        assert live_text == pinned_text, (
            f"{skill_md_path}: {_CODE_REVIEW_DEFER_INVARIANT_ANCHOR} no longer "
            f"matches its pinned text.\n"
            f"  live:   {live_text!r}\n"
            f"  pinned: {pinned_text!r}"
        )

    def test_disposition_walk_covers_orchestrator_noticed_invariant_break(self) -> None:
        """The Finding disposition section carries the clause that routes an
        orchestrator-noticed invariant break into the disposition walk."""
        skill_md_path = _skill_file("code-review")
        walk_clause = (
            "plus any break the orchestrator's own pass noticed that the "
            "enforcement-invariant rule below covers"
        )
        section_text = _heading_section_text(
            skill_md_path, _CODE_REVIEW_FINDING_DISPOSITION_HEADING
        )
        assert " ".join(walk_clause.split()) in section_text, (
            f"{skill_md_path}: the {_CODE_REVIEW_FINDING_DISPOSITION_HEADING} "
            f"section must still contain {walk_clause!r}"
        )

    def test_enforcement_invariant_finding_ends_unfixing_consult_returns_in_human_stop(
        self,
    ) -> None:
        """An enforcement-invariant finding's Endorsed-with-no-plan-file and
        Rejected consult returns still end in the human stop, and the Rejected
        bullet the pinned sentence names still exists."""
        skill_md_path = _skill_file("code-review")
        heavier_mechanism_text = _normalized_anchor_text(
            skill_md_path, _CODE_REVIEW_NEW_PRIMITIVE_ROUTE_ANCHOR
        )
        stop_sentence = " ".join(_ENFORCEMENT_INVARIANT_CONSULT_STOP_SENTENCE.split())
        assert stop_sentence in heavier_mechanism_text, (
            f"{skill_md_path}: the {_CODE_REVIEW_NEW_PRIMITIVE_ROUTE_ANCHOR} region "
            f"must still contain {stop_sentence!r}"
        )
        assert "**Rejected" in heavier_mechanism_text, (
            f"{skill_md_path}: the {_CODE_REVIEW_NEW_PRIMITIVE_ROUTE_ANCHOR} region "
            "must still contain the `**Rejected` outcome bullet the stop sentence names"
        )
