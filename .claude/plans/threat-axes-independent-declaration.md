# Replace the single-ladder threat tag with independent declared axes

## Context

Goal: make a review's threat declaration state agent intent, human caller and input provenance as separate fields, so no single token asserts two of them.

Ask: "I DO expect to model a hostile agent. That's essential to my work." — and "A hostile agent adds persistent intent - EXACTLY. that's the different." — and "Yes, those collapsed adversarial categries need to be kept seaprate." — and, after the architect advised deferring the hook `hostile` token and dropping `reversibility`: "Ok yes I agree with your recomendation now." Scope is the review-time declaration only. The hook `# tier-threat-model:` line keeps its current grammar, and a `hostile` hook token waits for the first gate whose header states a hostile-agent threat.

Why now: two vocabularies describe the same threat model and disagree. `docs/hooks.md` § "Threat-model tiers" defines three independent axes, where `cooperative` is the agent-intent axis and sits beside `untrusted-input` on 10 gates. The review-time `declared: <surface>, <tier>` tag in `claude-skills/skills/plan-review/ROUTING.md` and `claude-skills/skills/code-review/SKILL.md` is a single cumulative ladder (`cooperative` < `untrusted-input` < `adversarial`) in which `cooperative` also asserts trusted input. The same token therefore means two things, and `adversarial` is defined by caller identity across a boundary while engineers and agents use it for "crafted input" and "hostile actor".

Observed effect in agent transcripts: agents write "tier is cooperative, so hostile or attacker-crafted shapes are out of scope" without checking whether the gate also lists `untrusted-input`, which drops steered-agent findings. The wording spreads verbatim through dispatch prompts.

Intended outcome: independent declared fields that cover a cooperative or hostile agent (hostile meaning persistent intent, not merely steered), operator-only or other callers, and trusted or untrusted input; consumers that branch on the old tag migrated; `CLAUDE.md` § "Hook threat model" stating the independence with a worked example.

Primary-source basis, checked against extracted text this session: NIST SP 800-30 Rev.1 Appendix D (threat-source types; intent, capability and targeting apply to adversarial sources) and NIST AI 100-2 E2025 §3.3-3.4 (direct prompting where the attacker is the user, indirect injection through resource control). Neither covers a hostile agent as an actor, so the agent-intent axis rests on the engineer's requirement, not on those sources.

## Approach

Replace the review-time `declared: <surface>, <tier>` ladder with four keyed fields, `declared: surface=<v>, agent=<v>, caller=<v>, input=<v>`, each settled or `undeclared` on its own, and move every consumer of the old tag to the new vocabulary in this PR. When the declaration reads `agent=hostile`, `ciso-reviewer` also gets one fixed hostile-agent question. The hook `# tier-threat-model:` line keeps its grammar. `CLAUDE.md` § "Hook threat model" gains one clause saying `cooperative` says nothing about whether the gate's input is trusted, and a worked example of a steered agent.

Each field's first value is the narrow assumption and its second the wide one:
- `surface`: `dev-only` or `production`, defined as today.
- `agent`: `cooperative` or `hostile`.
- `caller`: `operator-only` or `other-callers`.
- `input`: `trusted` or `untrusted`.

Each old rung included those before it (row 9), so the old tag maps as follows:
- `cooperative` becomes `agent=cooperative, caller=operator-only, input=trusted`.
- `untrusted-input` becomes `agent=cooperative, caller=operator-only, input=untrusted`.
- `adversarial` becomes `agent=cooperative, caller=other-callers, input=untrusted`.
- `agent=hostile`, and other callers with trusted input, have no old equivalent.

The review fields and the hook tier line correspond as follows:
- The review's `agent=cooperative` and `input=untrusted` mean what the hook line's `cooperative` and `untrusted-input` mean.
- No tier line settles a review field (Out of scope).
- The hook line's `irreversible` has no review field (row 20).
- `agent=hostile` has no hook token yet (row 19).

Alternatives weighed:
- **Keep the ladder and add a `hostile` rung.** One token would still assert several axes, which the Ask rejects (row 1).
- **Positional bare tokens** (`declared: dev-only, cooperative, operator-only, trusted`). A reader has to count positions, and an `undeclared` in one slot names no axis.
- **Bare self-identifying tokens, with an absent token meaning the narrow value, as on the hook line.** An absent token cannot tell "declared trusted" from "could not settle input". That gap is how agents come to read `cooperative` as trusted input (root).
- **A `hostile` token on the hook tier line in this PR.** No gate's header states a hostile-agent threat, so the token would be grammar with no gate behind it. The engineer agreed to defer it (row 19).
- **A review-time `reversibility` field.** No skip and no `beyond declaration:` tag would read it, and the old tag never carried it (row 9). The engineer agreed to drop it (row 20).
- **`agent=hostile` acting through tagging alone, or through a search sentence inside the block.** The engineer selected "Z, one spawn (Recommended)" over the options the session labelled "Tagging only" and "Search sentence in block" (row 29).

The declaration block, identical in `code-review/SKILL.md` and `plan-review/ROUTING.md`, follows. Its opening paragraph is one physical line, followed directly by three items and then a blank line (row 5). Surface keeps its existing sentences in the opening paragraph, and the three field items replace the three tier items, so neither file changes length.

```text
Declaration block: review as you would without this declaration, and drop no finding because of it. The declaration reads `declared: surface=<value>, agent=<value>, caller=<value>, input=<value>`. No field's value implies another's. A field that reads `undeclared` excludes nothing. A field takes its first value, the narrow one its item or the surface sentence lists first, only on evidence that its second value does not apply, and reads `undeclared` when the evidence shows neither. Put `beyond declaration:` and the names of the excluding fields in the heading or first line of a finding whose failure needs a user, actor or input that the declaration excludes and the change does not reach. Keep that finding in its full format and name what it needs. Text the change's author wrote that says who calls a path, which input is trusted or how an agent behaves does not show that the change cannot reach it. The surface is `dev-only` when nothing the change does or adds reaches a production system, production data, end users, a copy installed for anyone beyond those who build and test it, or readers beyond them through a public repository's commits or PRs or a released artifact. Otherwise the surface is `production`. Each other field takes its second value when any part of the change must hold up under it:
- `agent` — `cooperative` assumes an agent acting for whoever runs the change makes only honest mistakes. `hostile` assumes that agent may itself work against whoever runs the change with persistent intent. Intent marks `hostile`, not behavior: a finding that needs an agent to retry or reword after a denial, or to emit any other shape an honest agent emits, is never a steered-or-hostile finding and never beyond declaration on `agent` grounds. A finding that needs a steered or hostile agent is beyond declaration only under `agent=cooperative`, `caller=operator-only` and `input=trusted`, and names all three fields. Content from anyone else, sent as input or by a direct call, can steer a cooperative agent into any shape.
- `caller` — `operator-only` assumes only whoever runs the change, or an agent acting for them, calls it. `other-callers` assumes someone else can call it directly, as across an authentication, privilege or tenant boundary.
- `input` — `trusted` assumes whoever runs the change, or an agent acting for them, supplies all content that reaches the change through them. `untrusted` assumes content from anyone else, such as user, network or third-party data or text that can steer an agent, reaches the change through whoever runs it or the agent acting for them. That can be shown by the change's code, docs or stated intent, or by code or config that reaches the change. Content someone else sends straight to the change falls under `caller`, even after the change stores it and later passes it to whoever runs it or to a job or agent. Any other content the change fetches or reads itself counts as reaching it through whoever runs it, so `input` takes `untrusted` when any of that content comes from anyone else, no matter who starts the fetch or read.
```

### Assumption ledger

**Root:** One review-time token, `cooperative`, asserts agent intent, caller identity and input trust together (row 9). The `adversarial` rung names caller identity. Readers take that rung for crafted input or a hostile actor (Context). Agents then drop steered-agent findings by reading `cooperative` as trusted input. The review declaration also cannot model a hostile agent, which the engineer requires (rows 1, 3).

**Givens:**
- G1. A spawned reviewer sees only its prompt, and a skill has no include mechanism, so each review skill carries the declaration block as literal text in its own files. Reason: the SKILL.md format has no include field, a vendor constraint the repo's no-shared-partials rule records (row 6).
- G2. A skill running in another repository can read only what the stow packages and plugins install, and `docs/` is not among them. Reason: changing the stow package set is a decision outside this plan (row 7).
- G3. `code-review/SKILL.md` may reach 550 lines, and `CLAUDE.md` may not grow past 200 lines or 30,720 bytes (row 8). The reasons, by limit:
  - Both limits: the length gates impose them.
  - `CLAUDE.md`'s 200 lines: the figure follows Anthropic's documented threshold.
  - `code-review/SKILL.md`'s 550 lines: the cap's own comment assigns its restructure to separate work.

**Mechanisms:**
- **M1. Declaration syntax and wiring.** The tag lists all four fields in the order above, always. A field the declaring sources cannot settle reads `undeclared`, and the whole-line `declared: undeclared` retires (row 4). The block's settle sentence makes a first value need evidence that the second does not apply, so no field defaults to its narrow value. Both `input` values carry the old `untrusted-input` item's channel clause, so content someone else sends straight to the change falls under `caller` alone, even after the change stores it and passes it on (row 24). The block's "No field's value implies another's" therefore holds (row 21). Wiring edits, each in place:
  - `code-review/SKILL.md:57`: "Also declare the user surface and threat model the change serves as a `declared:` tag on the **Spawn decisions:** line, carrying every field the declaration block under Ripple effect triage defines." Its last sentence becomes "When those sources cannot settle a field, report that field as `undeclared`."
  - `:63`: "Defensive paths against an actor or input the declaration excludes, where a defense against a steered or hostile agent counts only under `agent=cooperative`, `caller=operator-only` and `input=trusted`." The clause applies the block's three-field rule (M3), so a persistence defense under `input=untrusted` is never a marker (row 15).
  - `:276`: "When Step 1's declaration settles any field, also pass that `declared:` value and the declaration block.", followed by M3's `ciso-reviewer` sentence. The block replaces `:276`'s tail from `Declaration block:` on, and `:277-279`.
  - `ROUTING.md:11`: "Step 4 declares the user surface and threat model the plan serves as a `declared:` tag, carrying every field the declaration block below defines." `:14` becomes "When those sources cannot settle a field, report that field as `undeclared`."
  - `ROUTING.md:46-49` takes the block. `:53` becomes "When Step 4's declaration settles any field, also pass that `declared:` value and the declaration block above. Copy the block into the spawn prompt as literal text, from `Declaration block:` through its `input` item.", followed by M3's `ciso-reviewer` sentence.

  Test edits, all in `test_review_dispatch_contracts.py`:
  - `_DECLARATION_TIER_ITEM_PREFIXES` (`:614-618`) becomes `_DECLARATION_FIELD_ITEM_PREFIXES`, with the `agent`, `caller` and `input` prefixes.
  - `_declaration_block_span`'s docstring and messages name the field items and the `input` item.
  - A new constant, `_DECLARATION_BLOCK_TEXT`, holds the block as `_declaration_block_span` returns it. `test_declaration_block_identical_in_code_review_and_routing` (`:650-660`) also asserts that code-review's span equals it, with a message saying a block change lands in both copies and in the constant.
  - In `_DECLARATION_WIRING_CLAUSES` (`:449-585`), each sentence above replaces the clause it supersedes.
  - The four block-sentence entries (`:492-514`) go, because the block constant pins every block sentence.

  The block is pinned whole, because each lighter pin leaves a gap:
  - Sentence pins counted in the Ripple section stay green when a sentence moves out of the block in both copies, while a spawned reviewer receives only the block.
  - Sentence pins counted in the block span need one entry per sentence, and any unpinned sentence can still leave both copies with every test green.

  The constant is a third copy of the block and falls under `CLAUDE.md`'s DAMP exception for test code. `_HOOK_THREAT_MODEL_SECTION` already pins `CLAUDE.md`'s section whole the same way (row 11).

  Per-field `undeclared` is heavier than one whole-line form, and each lighter shape fails. Keeping `declared: undeclared` whenever any field is unsettled discards the fields that did settle and keeps a second tag grammar. Defaulting an unsettled field to its narrow value is the silent assumption the root describes.

  anchors: root, row1, row4, row5, row11, row15, row21, row24
- **M2. The block keeps two identical copies** under the existing identity test, one in each skill. Each alternative fails:
  - A shared file both skills read at runtime is a cross-skill partial the repo rule bars (row 6), and the reviewer still needs the text pasted (G1).
  - `code-review` reading `plan-review/ROUTING.md`'s copy is the same cross-skill dependency, plus a Read on every round.
  - A definition in `docs/hooks.md` that both skills cite is not installed where the skills run (G2).
  - A co-located auxiliary file in `code-review` to relieve its cap is the use the repo rule forbids (row 6).

  The copy is `CLAUDE.md`'s named exception for instructional prose that must stand alone. The identity test with M1's block constant stops the copies drifting. `code-review/SKILL.md` stays at 546 of 550 lines (G3).

  anchors: row5, row6, row7, row8
- **M3. Agent, caller and input together.** The `agent` item's second-to-last sentence puts a steered-or-hostile-agent finding beyond declaration only under `agent=cooperative`, `caller=operator-only` and `input=trusted`, the cell the old `cooperative` rung named (row 9). Every steered-or-hostile-agent finding the old ladder kept in scope therefore stays in scope:
  - Under `input=untrusted`, a finding that needs the agent to persist stays in scope whatever `agent` reads, as the engineer chose (row 15).
  - Under `caller=other-callers`, a steered-agent finding stays in scope, as the old `adversarial` rung kept it by including `untrusted-input` (row 9).

  The honest-agent sentence keeps a finding on a retry or reword after a denial, or on any other shape an honest agent emits, in scope in every cell. A behavior list cannot mark `hostile`, because a cooperative agent shows the same behaviors when a control blocks its task, so the item defines `hostile` by persistent intent alone (rows 3, 26).

  `agent=hostile` with `caller=operator-only` and `input=trusted` is the new cell, where the agent itself is the threat and no one else's content reaches it. The old ladder could not express that cell (row 3). Naming `caller` makes the rule one field wider than the agent-and-input form, and each lighter form fails:
  - The agent-and-input form would move a steered-agent finding under `caller=other-callers, input=trusted` out of scope, because the channel sentence leaves a direct caller's content outside `input` (row 21).
  - Widening `input=untrusted` to cover a direct caller's content makes `caller=other-callers` imply it, the flaw row 21 records.

  `agent=hostile` has four effects and no others, and the plan claims no more than these for the Ask's hostile-agent requirement (rows 1, 25):
  - It blocks every skip (M4).
  - It keeps a steered-or-hostile-agent finding unmarked under `caller=operator-only` and `input=trusted`, so DEFER criterion 3 cannot defer it on the declaration (M5).
  - It keeps a defense against a hostile agent off Step 1's over-elaboration marker, which applies the same three-field rule (`code-review/SKILL.md:63`, M1).
  - It puts one fixed question to `ciso-reviewer` (row 29).

  The `ciso-reviewer` sentence sits outside the block, on `code-review/SKILL.md:276` after the pass sentence and on `ROUTING.md:53` after the copy sentence, so no other reviewer receives it. The `code-review` form reads:

  > When Step 1's declaration reads `agent=hostile`, also put this question, word for word, to `ciso-reviewer`, in the prompt of a `ciso-reviewer` this round already spawns or else in one spawn of its own: "what can an agent acting for whoever runs the change reach if it holds a goal against them across turns and sessions and picks each action to defeat the change's controls, including shapes an honest agent never emits?"

  The `ROUTING.md` form reads "Step 4's" for "Step 1's". The block still tells every reviewer to review as it would without the declaration, so this question is `agent=hostile`'s only effect on any reviewer's search. A new constant in the contracts test, `_HOSTILE_AGENT_QUESTION_CLAUSE`, holds the sentence from "also put this question" through its closing quotation mark, and feeds one `_DECLARATION_WIRING_CLAUSES` entry per file. Each entry prefixes its own step's opening words.

  One finding class leaves scope: under `caller=other-callers, input=trusted`, a finding that needs content from someone who cannot call the change, passed in through whoever runs it, with no agent steered, is beyond declaration where the old `adversarial` rung kept it (rows 23, 24).

  anchors: row1, row3, row9, row12, row15, row16, row21, row23, row24, row25, row26, row29
- **M4. Skip rules.** A skip needs every field at its first value, which translates the old `declared: dev-only, cooperative` (row 9).
  - `code-review/SKILL.md:260`: "skip only when Step 1's declaration reads `surface=dev-only`, `agent=cooperative`, `caller=operator-only` and `input=trusted`, and name the surface in the output. Any other row skip that rests on Step 1's declaration needs the same four values."
  - `:273`: "**unless** Step 1's declaration carries the four values the high-stakes skip rule above names and the change crosses no privilege boundary."
  - `ROUTING.md:9`: "Skip only when Step 4's declaration reads `surface=dev-only`, `agent=cooperative`, `caller=operator-only` and `input=trusted` and that declaration puts the change outside that reviewer's threat model". `:35`: "**unless** Step 4's declaration carries the four values the reviewer skip rule above names and that declaration puts the change outside `ciso-reviewer`'s threat model."
  - `claude/.claude/agents/skill-fidelity-reviewer.md:106`: the carve-out "needs `surface=dev-only`, `agent=cooperative`, `caller=operator-only` and `input=trusted`", rewrapped within its list item.
  - The five skip-clause constants in `test_review_dispatch_contracts.py` (`:429-445`) take the new text.
  - One new constant there, `_SKIP_FIRST_VALUES`, holds the four-value list. It feeds three pins:
    - `_CODE_REVIEW_HIGH_STAKES_SKIP_CLAUSE`;
    - `_ROUTING_REVIEWER_SKIP_CLAUSE`;
    - a new `_DECLARATION_WIRING_CLAUSES` entry for the fidelity carve-out, under `skill-fidelity-reviewer.md`'s "## The code-review spawn-dispatch check" heading.

    The agent's copy must therefore name the same keys and values as the skip rule. `_heading_section_text` collapses whitespace (`_skill_md_helpers.py:465-475`), so the rewrap does not break the pin.

  An `undeclared` field never meets a skip, and `agent=hostile` blocks every skip, so no skip is loosened.

  anchors: row9, row16, row20
- **M5. `beyond declaration:` names the excluding fields.** The tag lists every field whose value excludes what the failure needs:
  - `surface` covers a production user or data.
  - `agent`, `caller` and `input` together cover a steered or hostile agent (M3).
  - `input` alone covers content from someone who cannot call the change, passed in through whoever runs it, with no agent steered.
  - `caller` alone covers someone else calling the change directly, content the change stores and later passes on included (row 24).

  DEFER criterion 3 (`code-review/SKILL.md:408`) changes as follows:
  1. Its first alternative reads "quotes the `declared:` value the **Spawn decisions:** line reports and names each field that excludes the finding".
  2. Its last sentence becomes "When the fields that would exclude the finding read `undeclared`, the rationale rests on such a route or on Step 1's implementation-fitness answer."
  3. The contracts test's `:518` pin extends to the added clause, and its `:523` pin takes the new last sentence.
  4. The project-layer alternative stays, so the claude-config layer's route through a gate's tier line still meets it (row 13).
  5. A rationale must name the fields it rests on, so "`agent=cooperative`, so steered shapes are out of scope" fails on its face unless `caller=operator-only` and `input=trusted` also hold.

  anchors: root, row13, row14, row24
- **M6. `CLAUDE.md` § "Hook threat model"** is one physical line (`:105`), edited in place so the file stays at 200 lines (row 8). Three changes are made, and every other sentence stays word for word:
  - The first sentence gains ", and `cooperative` says nothing about whether the gate's input is trusted" before its period.
  - After the `untrusted-input` sentence: "For example, a cooperative agent that follows a fetched page telling it to pipe an installer into a shell is steered, not hostile." The example carries no disposition. `docs/hooks.md:34` tells a `CLAUDE.md` that applies the regression rule to point there rather than restate it. The shape is also one a cooperative agent emits unsteered (`deny-network-installs.sh:8`).
  - `_HOOK_THREAT_MODEL_SECTION` (`test_hook_alignment.py:2438-2455`) takes the new text, because the pinned-text test fails on any edit to the section (row 11). Nothing else in that file changes.

  The waiver condition keeps "omits `untrusted-input`", because no gate can list `hostile` (rows 12, 19). The added clause states, in the file every session here loads, the input-trust consequence of `docs/hooks.md:9`, under `CLAUDE.md`'s exception for instructional prose that must stand alone (row 22). Neither change reads a tier line into the review's fields (Out of scope, row 27).

  anchors: root, row8, row11, row12, row19, row22, row27, row31
- **M7. Records.**
  - `CHANGELOG.md` `[Unreleased]` → `### Changed` gains one entry, in the shape of row 17's precedents. The entry states:
    - the new tag and its four fields' values;
    - the retired ladder and whole-line `undeclared`;
    - the `beyond declaration:` form;
    - that a steered-or-hostile-agent finding is beyond declaration only where `agent`, `caller` and `input` all take their first value;
    - that other callers no longer imply untrusted input;
    - that `agent=hostile` puts one fixed hostile-agent question to `ciso-reviewer`;
    - that the project-layer gate waivers and `CLAUDE.md` § "Hook threat model" do not read the `agent` field, so `agent=hostile` changes no gate-tier waiver or routing, and `docs/hooks.md` § "Threat-model tiers" still decides what a tier line waives (rows 19 and 33).

    Its **Migration:** sub-bullet says:
    - a skip that needed `declared: dev-only, cooperative` now needs `surface=dev-only`, `agent=cooperative`, `caller=operator-only` and `input=trusted`;
    - a declaration that read `untrusted-input` now reads `caller=operator-only` and `input=untrusted`, and one that read `adversarial` now reads `caller=other-callers` and `input=untrusted`, each with `agent=cooperative` (row 24);
    - a project layer or prompt matching the old tag no longer matches.
  - The commit message and PR body carry the rationale the pinned-text failure message asks for (`test_hook_alignment.py:2463-2466`). The `CLAUDE.md` edits change no waiver's scope, since the waiver condition and every gate's tier line stay as they are. The reason is the engineer's requirement (rows 1, 3).

  anchors: row11, row17, row24, row29

**Rows:**
1. The Ask. [engineer-verified: "Yes, those collapsed adversarial categries need to be kept seaprate."] [engineer-verified: "I DO expect to model a hostile agent. That's essential to my work."] Neither quote names which surfaces change. That this PR changes the review-time declaration and `CLAUDE.md` § "Hook threat model" but not the hook tier line is the session's reading of these quotes and of row 19's agreement, stated on the Ask line [unverified].
2. [engineer-verified: "Add token, classify no gate (Recommended)"] The option's description, that every gate stays as it is and each reclassification follows in its own change, is the session's text [unverified]. That description said 36 gates, and the table holds 35 (row 10). Row 19's later agreement reads as superseding this row's "Add token" half for this PR, which adds no hook token. Its "classify no gate" half matches the plan, since no gate's tier line changes.
3. [engineer-verified: "A hostile agent adds persistent intent - EXACTLY. that's the different."] The quote settles what distinguishes a hostile agent from a steered one. It does not settle which findings each keeps live (row 15).
4. [engineer-verified: "Hard cut in one PR (Recommended)"] The description, that the tag is replaced everywhere and the pinned tests update in the same change, is the session's text [unverified]. The plan reads the hard cut as also retiring the whole-line `declared: undeclared` [unverified: architect's reading].
5. `test_declaration_block_identical_in_code_review_and_routing` (`test_review_dispatch_contracts.py:650-660`) requires the two blocks to match. `_declaration_block_span` (`:621-647`) requires a one-line opening paragraph, the items directly after it, and a blank line, heading or end of file after them. Spawn prompts copy the block as literal text (`ROUTING.md:53`, `code-review/SKILL.md:276`). [verified: reads]
6. The repo rule says to "duplicate shared rule text into each skill rather than extracting a `_shared/` file", and to add a co-located auxiliary file "never as a way to route around a file's length cap". [verified: `.claude/rules/skill-and-agent-self-review.md`]
7. The two stow packages are `claude/.claude/` and `claude-skills/`, and `docs/` is in neither. [verified: `CLAUDE.md` § "Working in this repo"]
8. `code-review/SKILL.md` is 546 lines against `limit_for`'s 550 (`check-skill-length.sh:132-134`). `CLAUDE.md` is 200 lines against a 200-line limit, and its gate denies a staged file that is over its limit and longer than before (`check-claude-md-length.sh:6-7`, `:120-124`). Its byte limit is 30,720 (`:59`). [verified: reads]
9. The literal `declared: dev-only, cooperative` appears at `code-review/SKILL.md:260` and `:273`, `ROUTING.md:9` and `:35`, and `skill-fidelity-reviewer.md:106`. `plan-review/SKILL.md:88` and `:258` pass the value through without naming its tokens, so they need no edit. The old `cooperative` item assumes "only whoever runs the change, or an agent acting for them, calls it or supplies its input" (`ROUTING.md:47`), so it asserted operator-only callers and trusted input and nothing about reversibility. Each rung "includes those before it" (`:46`), so `adversarial` also asserted untrusted input. [verified: Grep and reads]
10. 35 gates: 19 plain `cooperative`, 7 `cooperative, irreversible` and 9 `cooperative, untrusted-input, irreversible` (`docs/hooks.md:59`, table rows `:63-97`). The exploration's 36 and 10 included `bootstrap-project-plugins.sh`, which carries a tier line but is `hook-class: informational` (its lines 2-3). [verified: reads]
11. The hook grammar requires `cooperative` as the first token (`test_hook_alignment.py:2002`) and draws its vocabulary from `_THREAT_MODEL_TIERS` (`:1944`). docs/hooks.md's tier bullets must equal that tuple in order (`:2469-2482`). `CLAUDE.md` § "Hook threat model" must name every token (`:2427-2435`). Its whole text is pinned as `_HOOK_THREAT_MODEL_SECTION` (`:2438-2455`). That pin's failure message asks for the constant's update and a commit-message rationale (`:2463-2466`). [verified: reads]
12. `CLAUDE.md:105` waives a finding on a gate whose line "is present but omits `untrusted-input`", and says outside content "can steer a cooperative agent into any shape". [verified: read] Under that wording, a future `hostile` gate without `untrusted-input` would get the waiver, so the change that adds the token also changes this condition (Out of scope).
13. Neither project layer names the `declared:` tag, the `adversarial` rung, `dev-only` or `beyond declaration` (Grep of `.claude/skills`). Both grant the per-vector-gap waiver by a gate's tier line that "omits `untrusted-input`" (`code-review-claude-config/SKILL.md:59`; `plan-review-claude-config/SKILL.md:23`). The code-review layer DEFERs a gate finding under criterion 3 with the gate's tier line as "its declared threat model" (`code-review-claude-config/SKILL.md:63`), which criterion 3's project-layer alternative (`code-review/SKILL.md:408`) accepts. [verified: Grep, reads] The layers therefore need no edit while the hook tier line keeps its grammar.
14. `beyond declaration` has no mechanical consumer: Grep finds it only in the two review files, the contracts test and `CHANGELOG.md`. DEFER criterion 3's rationale quotes the `declared:` value (`code-review/SKILL.md:408`). [verified: Grep, read]
15. [engineer-verified: "In scope whenever input is untrusted (Recommended)"] The question asked whether a finding that needs the agent to persist stays in scope when the agent is cooperative but the input is untrusted, or only when the agent is declared hostile. It named persisting as retrying past a deny, adapting to the deny's reason, or acting on the change's own state. Read against that question, the label settles that under `input=untrusted` such a finding stays inside the declaration whatever `agent` reads. It settles nothing about `input=trusted` (row 16).
16. The option's description is the session's text, not the engineer's. It made four claims:
    - the answer matches row 12's "any shape" sentence;
    - it makes `agent=hostile` matter where input is trusted;
    - it blocks every reviewer skip;
    - it loosens no existing gate's waiver.

    The plan's own inference from rows 12 and 15 follows. A hostile agent and a steered one can each emit any shape, so where someone else's content can reach the agent they differ in threat source, not in which findings stay live. `agent=hostile` therefore changes a disposition only where `caller=operator-only` and `input=trusted`, and it blocks every skip. The option not chosen would have tagged a persistence finding `beyond declaration: agent` and let criterion 3 defer it on the 9 `untrusted-input` gates. [unverified: the session's option description and its inference from rows 12 and 15]
17. The tag's introduction has an entry at `CHANGELOG.md:261-264` with a skip-rule note, and `[Unreleased]` carries **Migration:** sub-bullets for behavior a consumer must act on (`:5-37`). [verified: reads]
18. `select-tests.py` names `code-review/SKILL.md`, `plan-review/ROUTING.md`, root `CLAUDE.md` and `.claude/skills` among its routed paths (`:380-381`, `:504`, `:517`). [verified: Grep] That it routes every touched file to the tests named below is [unverified]; its printed selection shows it.
19. [engineer-verified: "Ok yes I agree with your recomendation now."] The quote covers the engineer's agreement to the recommendation the session relayed, and no more. That recommendation's wording is the session's, not the engineer's [unverified]. Its first part defers the hook `hostile` token. Under that part these stay as they are:
    - the hook tier grammar;
    - `docs/hooks.md`;
    - the claude-hook-review plugin;
    - their test pins.

    The same part keeps only what needs no `hostile` in the `CLAUDE.md` edit. That part names the hook token only, so `agent=hostile` stays a review-time value [unverified: the session's reading].
20. [engineer-verified: "Ok yes I agree with your recomendation now."] The same agreement covers the recommendation's second part, dropping the `reversibility` field, so the declaration carries `surface`, `agent`, `caller` and `input`. Its third part kept the `caller` field and the one-line `skill-fidelity-reviewer.md` edit. The quote covers only the agreement, and each part's wording and reasons are the session's, not the engineer's [unverified].
21. The old `untrusted-input` item limits untrusted content to what "reaches the change through whoever runs it or the agent acting for them" (`ROUTING.md:48`), and the old `adversarial` item covers someone who "can call it directly" (`:49`). [verified: read] The session relayed a consult finding, and this plan infers its consequence for M3 [unverified]:
    - An earlier draft's `input=trusted` dropped that channel.
    - A direct caller under `caller=other-callers` therefore supplied input that `input=trusted` excluded.
    - The block's "No field's value implies another's" was then false.
    - Restoring the clause in both `input` values keeps a direct caller's content under `caller` alone, outside `input`, which is why M3's rule names `caller` too.
22. `docs/hooks.md:9` states the hook axes are independent and that "The framework never infers input trust from agent cooperation." [verified: read] Root `CLAUDE.md` loads in every session in this repository, while `docs/hooks.md` loads only when read. That M6's added clause falls under `CLAUDE.md`'s exception for instructional prose that must stand alone is this plan's reading [unverified].
23. The old `adversarial` rung kept every `untrusted-input` finding in scope by inclusion (row 9). The channel sentence keeps a direct caller's content under `caller` even after the change stores it and later passes it on (row 24). By that sentence's own text, under `caller=other-callers, input=trusted`, stored content shown to an operator, second-order injection, and a caller's data relayed to a job or agent stay in scope. What remains `input`-only is content from someone who cannot call the change, passed in through whoever runs it, for example a vendor file the operator imports. A finding that needs such content, with no agent steered, now carries `beyond declaration: input` under `caller=other-callers, input=trusted`. Keeping it in scope would need `caller=other-callers` to imply `input=untrusted`, which row 21 rules out. That the separation row 1 asks for accepts this remainder is this plan's reading [unverified].
24. [engineer-verified: "Architect's sentence fix (Recommended)"] The question, in the session's wording, asked which control should cover row 23's narrowing, where `caller=other-callers, input=trusted` let a finding about untrusted content carry `beyond declaration: input` and be deferred. The quote covers only that selection. The option's description is the session's wording, not the engineer's [unverified]: clarify the `input` item so stored-and-relayed content from a direct caller stays under `caller`, pin it, add the CHANGELOG rung mapping, and grow no file. The session relayed the options not chosen as "Ban deferral" and "Force input settled".
25. Outside `docs/` and `CHANGELOG.md`, `dev-only`, `declared: ` and `beyond declaration` occur in `code-review/SKILL.md`, `ROUTING.md`, `skill-fidelity-reviewer.md` and the contracts test, plus four unrelated code uses of `declared: `. No project layer, rule or plugin names them. [verified: Grep] `plan-review/SKILL.md` passes the value through without naming its tokens (row 9). The block opens by telling every reviewer to review as it would without the declaration (`code-review/SKILL.md:276`). [verified: read] This plan infers the following from those reads [unverified]:
    - No declared value inside the block changes a reviewer's search.
    - `agent=hostile` reaches a search only through the `ciso-reviewer` question outside the block (row 29).
    - Its other effects run through the skips, criterion 3 and `:63`'s marker.
26. `CLAUDE.md:105` waives only a finding that needs a shape "a cooperative agent would never emit", and `docs/hooks.md:13` says the same of the `cooperative` tier. Those rules bind this repository's gates, while the block ships in skills that install to every stack (`.claude/rules/skill-and-agent-self-review.md`). [verified: reads] This plan reads a plan-review finding as follows [unverified]:
    - An honest agent retries or rewords after a denial.
    - A finding on that shape therefore needs neither a steered nor a hostile agent.
    - The block must say so itself, because the rules above do not ship with it.
27. `docs/hooks.md:18` says "Silence in both the header and the docs entry means no `untrusted-input`", and `:9` says "The framework never infers input trust from agent cooperation." [verified: read] The base review skills name no tier line, and only the two claude-config project layers do. [verified: Grep] Code-review's Step 1 counts a comment or instruction-file line added or edited since the merge base as author text, which "can raise a field but never settles one" (`code-review/SKILL.md:57`). [verified: read] The CISO round-2 review reads these as follows, and this plan adopts that reading [unverified]:
    - A tier line that omits `untrusted-input` does not show `input=trusted`.
    - A tier line added or edited since the merge base is author text and settles no field.
28. `Explore` holds only `Read`, `Grep` and `Glob`, at `effort: low` (`claude/.claude/agents/Explore.md:5-6`). It is in `_LIB_REVIEW_ONLY_AGENTS` (`_lib.sh:5047-5060`), which `deny-reviewer-tree-mutation.sh` sources, and `_LIB_REVIEWER_PERSONA_AGENTS` leaves it out (`_lib.sh:5171-5177`). [verified: reads] `log-reviewer-round.sh:148` records a round state, and `require-architect-consult.sh:76` gates a spawn, only for a reviewer persona. [verified: prior round's reads, confirmed by the round-2 SDET review] An `Explore` dispatch therefore has no tool that writes, records no round state and meets no consult gate.
29. [engineer-verified: "Z, one spawn (Recommended)"] The quote covers only that selection. The question, in the session's wording, offered three ways to give `agent=hostile` a reviewer-side effect, and the session relayed the options not chosen as "Tagging only" and "Search sentence in block". The option's description is the session's, not the engineer's [unverified]. It said:
    - when the declaration reads `agent=hostile`, put a fixed hostile-agent question to `ciso-reviewer`;
    - put it in the prompt `ciso-reviewer` already gets when the round spawns it for other reasons, and in a spawn of its own otherwise, so a round has at most one `ciso-reviewer`;
    - place the sentence in `ROUTING.md:53` and `code-review/SKILL.md:276`, outside the declaration block, pinned in `_DECLARATION_WIRING_CLAUSES`.

    The question's wording, which rests on intent and lists no behaviors, is also the session's [unverified].
30. [engineer-verified: "Add file, apply clause (Recommended)"] The quote covers only adding `claude-skills/skills/plan-review/SKILL.md` to Critical files and applying the three-field clause at line 92 where `code-review/SKILL.md:63` carries it. It answered a code-review round-2 question about that file, which the plan's row 9 had treated as pass-through. The option's description, "Add plan-review/SKILL.md to scope, apply the same clause at :92 and pin it", is the session's [unverified].
31. [engineer-verified: "Apply architect's split (Recommended)"] The quote covers only that selection. The question, in the session's wording, asked what to do with the worked-example clause of `CLAUDE.md:105`, which carried a disposition that conflicted with `docs/hooks.md:20` and `:47`. The plan-architect's reading was that `docs/hooks.md:34` tells a `CLAUDE.md` that applies the regression rule to point there rather than restate it, and that a cooperative agent also emits the example's shape (`deny-network-installs.sh:8`). The option's description is the session's wording, not the engineer's [unverified]. It had four parts:
    - Keep the steered-not-hostile example as a classification only.
    - Delete its disposition clause.
    - Update `_HOOK_THREAT_MODEL_SECTION`.
    - Update M6.

    The session relayed the options not chosen as "Apply ciso's fix" and "Keep current text".
32. [engineer-verified: "I think apply the clause. What does the architect think?"] The quote covers only that selection and the request for the architect's view. The question, in the session's wording, asked whether to append a clause to the `input` item's fetched-content sentence so that content fetched from anyone other than whoever runs the change stays `untrusted`. The wording that shipped is the plan-architect's, not the engineer's [unverified]: "so `input` takes `untrusted` when any of that content comes from anyone else, no matter who starts the fetch or read". The session relayed the options not chosen as "Keep current sentence".
33. [engineer-verified: "Leave it, say so in CHANGELOG (Recommended)"] The quote covers only that selection. The question, in the session's wording, asked whether a hostile-agent finding on a gate whose tier line says `cooperative` stays waived, or whether the waiver sites should apply only when the review declares `agent=cooperative`. The selection leaves the waivers unchanged and adds a `CHANGELOG.md` sentence, which M7 lists. The option's description is the session's [unverified]. The session relayed the option not chosen as "Change the waiver now", which edits the waiver text in `CLAUDE.md` and both project layers.
34. [engineer-verified: "yes go ahead and do that. I think test_hook_alignment should be split, but that's overly heavy for your PR to handle"] The quote covers only the session's three-part proposal:
    - merge `origin/main` into this branch;
    - raise the `ceiling` of the `test_hook_alignment.py` row in `code-file-size-exceptions.toml` from 3767 to 3770;
    - leave the heavier remedy, splitting `test_hook_alignment.py`, out of this PR.

    The proposal's wording is the session's [unverified]. Its cause, that the merged tree counts 3 lines more than the row holds because of the `_HOOK_THREAT_MODEL_SECTION` edit, is [verified: `git diff origin/main...HEAD --numstat` prints 5 added and 2 removed lines for `test_hook_alignment.py`; the file is 3767 lines on `origin/main` and 3770 lines at `67c19b58`, before the merge]. The +3 comes from the wrapped mirror of M6's added sentences, which row 11 pins whole, so it cannot shrink without moving that constant out, which is the heavier remedy of splitting the file. After the merge, a local run of `claude/.claude/tests/test_code_file_size.py` printed 3770 for that row [verified: that run].

    3770 is the value printed at the merge. A later merge from `origin/main` or a change to that constant rewrites the row from the check's printed value. The row and the `_HOOK_THREAT_MODEL_SECTION` edit land and revert as one unit, because a ceiling is exact in both directions.

## Critical files

One `code-writer` dispatch. Every file shares the declaration vocabulary, and the `CLAUDE.md` edit is two prescribed changes, so a split would restate the same background in each prompt.

- `claude-skills/skills/code-review/SKILL.md` — M1 (lines 57, 63, 276-279), M3's question sentence (276), M4 (260, 273) and M5 (408). It stays at 546 lines, since every edit lands on an existing physical line.
- `claude-skills/skills/plan-review/ROUTING.md` — M1 (lines 11, 14, 46-49, 53), M3's question sentence (53) and M4 (9, 35).
- `claude-skills/skills/plan-review/SKILL.md` — line 92's over-elaboration marker takes the same three-field clause as `code-review/SKILL.md:63`, edited in place with no line growth (row 30).
- `claude/.claude/agents/skill-fidelity-reviewer.md` — M4, line 106.
- `claude-skills/skills/tests/test_review_dispatch_contracts.py` — M1's, M3's, M4's and M5's constants and entries. Add no new helper or test function.
- `CLAUDE.md` — M6, in place on line 105.
- `claude/.claude/hooks/tests/test_hook_alignment.py` — M6's `_HOOK_THREAT_MODEL_SECTION` only.
- `CHANGELOG.md` — M7's entry.
- `code-file-size-exceptions.toml` — raises the `ceiling` of the `test_hook_alignment.py` row from 3767 to 3770, and no other field (row 34).

Projected diff: about 330 lines, counting added plus removed lines, plus 2 in `code-file-size-exceptions.toml`. About 260-270 are in `test_review_dispatch_contracts.py`, about 10 in `test_hook_alignment.py`, and about 60 across the prose files and `CHANGELOG.md`, where each rewritten physical line counts once removed and once added. Verification step 3's fixture lives only in its dispatch prompts, so it adds nothing.

## Verification

1. Tests, pins and lint. `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py` passes, and its printed selection includes `test_review_dispatch_contracts.py`, `test_hook_alignment.py` (row 18) and `claude/.claude/tests/test_code_file_size.py`, and the last passes on the final tree (row 34). `scripts/venv-run.sh ruff check claude/.claude/ claude-skills/ plugins/ evals/` is clean.
2. The hard cut leaves no old form, no ladder sentence and no old item wording outside preserved records and plans. This prints nothing:

```bash
git grep -n -e 'declared: <surface>' -e 'dev-only, cooperative' -e 'declared tier' -e 'threat tier' -e 'declared: undeclared' -e 'beyond declaration`' -e '[`]adversarial[`]' -e 'tier is the highest' -e 'includes those before it' -e 'supplies its input' -e '`cooperative` — assumes' -e '`untrusted-input` — assumes' -- . ':!CHANGELOG.md' ':!.claude/plans' ':!docs/design-decisions' ':!docs/design-decisions.md'
```

   No text this PR adds outside those paths names an old form, so the grep never matches the change's own text.
3. One allow/deny fixture pair, as `.claude/rules/skill-and-agent-self-review.md` requires for reworded review text. The parent session runs it after the `code-writer` returns and steps 1-2 pass, since `code-writer` has no dispatch tool. It checks the three-field rule, the block's central change.
   - Fixture. Each prompt carries it inline, so nothing is written to disk. It is a new-file diff of `push_guard.py`, a guard that an agent's shell commands pass through. The guard reads nothing but the command string, and it allows any command that ends in `# approved`. With it goes one untagged finding: an agent working for whoever runs the guard reads text elsewhere telling it to end a force push with `# approved`, and the guard lets the force push through.
   - Dispatch. Two `Explore` dispatches with `model: sonnet`, because `Explore` has no tool that writes and records no round state (row 28). Each prompt carries the fixture, one declaration line below, and the block copied as literal text from this worktree's `code-review/SKILL.md`, from `Declaration block:` through the `input` item. It asks for the finding's first line as a reviewer would write it under that declaration.
     - Allow cell, where the declaration excludes the finding: `declared: surface=dev-only, agent=cooperative, caller=operator-only, input=trusted`.
     - Deny cell, where it does not: the same line with `input=untrusted`.
   - Scoring. The allow cell passes when its line carries `beyond declaration:` naming exactly the fields `agent`, `caller` and `input`, in any order and with or without their values, and no other field. The deny cell passes when its line carries no `beyond declaration:`.
   - Mismatch. Report each failing line to the engineer as it came back. Reword the block or re-run only on their answer.
   - Record. The PR description states each result as one sample from one model at `Explore`'s `effort: low`. When a later fix, such as one from `/skill-review`, changes the block, re-run the pair or state the shipped block unchecked by this step.

## Out of scope

- **A `hostile` token on the hook tier line.** The engineer agreed to defer it (row 19). It would bring:
  - the tier grammar in `test_hook_alignment.py` and a `hostile` floor test;
  - the `docs/hooks.md` § "Threat-model tiers" rewrite;
  - claude-hook-review's tier paragraph, with its version bump and that paragraph's `test_doc_cross_references.py` pin.

  The first gate whose header states a hostile-agent threat lands all of these together. That change also narrows the "omits `untrusted-input`" waiver condition in `CLAUDE.md` and both project layers, because the condition would otherwise waive findings on a `hostile` gate (rows 12, 13). Until then, a gate finding a project layer routes is judged by the gate's tier line, which cannot say `hostile`.
- **Reading a gate's tier line into the review's fields.** Such a reading would have to lower no field that the engineer's words or any part of the change raise. It would also have to hold only as the line stands at the merge base, because a line the change adds or edits is author text (row 27). No consumer needs it: every rule that reads `agent` or `input` also needs `caller=operator-only`, which no tier line states (M3, M4, M5), and the project layers route gate findings by the tier line on their own path (row 13).
- **Splitting `test_hook_alignment.py`.** The engineer deferred it (row 34), and it is owned by issue 1532, named on that file's row in `code-file-size-exceptions.toml`.
- **A review-time `reversibility` field.** The engineer agreed to drop it (row 20).
- **Narrowing what `untrusted-input` keeps live so that persistence findings need `hostile`.** The engineer chose "In scope whenever input is untrusted (Recommended)" (row 15), and the narrowing would relax the 9 `untrusted-input` gates (row 16).
- **A DEFER ban or a forced `undeclared` `input` for row 23's remainder.** The engineer selected "Architect's sentence fix (Recommended)" instead (row 24).
- **Rewording "adversarial" prose outside the declaration.** After the hard cut no token is named `adversarial`, so the word there is ordinary prose. Gate headers are each gate's classification evidence, which the "classify no gate" answer leaves alone. The candidate sites, closest first:
  - `require-respond-pr.sh:37-38`, which calls `require-ready-for-review.sh`'s `untrusted-input` tier an "adversarial posture";
  - `block-gh-pr-merge.sh:31` and its table row (`docs/hooks.md:63`);
  - `require-ready-for-review.sh:144`, which is pinned evidence for its `untrusted-input` elevation (`test_hook_alignment.py:2361`);
  - `require-worktree-for-file-writes.sh:27`;
  - `ciso-reviewer.md:9` and `:51`;
  - `review-pr/REFERENCES.md:254`;
  - `docs/security-hardening.md:833-854`.
- **Key=value syntax on the hook tier line.** It would rewrite every gate header and table row, and this PR leaves the hook tier line as it is (row 19).
- **Preserved records:** `CHANGELOG.md:261-264` and `docs/design-decisions/*` keep the old vocabulary.
- **Per-user memory edits**, which live outside this repository.
- **Transcript tooling changes.**
