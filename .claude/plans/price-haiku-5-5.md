# Price claude-haiku-5-5 by prompt length

## Context

Price `claude-haiku-5-5` in `transcript_analysis/pricing.py` so its turns stop landing in every cost report's excluded spend.

Ask: "add support for pricing haiku 5.5" — the engineer, 2026-11-20. Design direction: "Haiku 5.5 is the first model the pricing page prices by prompt length [...] How should I add it?" — accepted via label "Tiered + new variants (Recommended)".

**Problem.** Claude Code now writes `claude-haiku-5-5` to `message.model`, and `_MODEL_BASE_INPUT_RATES` has no row for it. `cost` reports those turns under `EXCLUDED SPEND` as an unpriced model ID, and `pr-cost-section.sh` reports an unrecognized model ID in the PR-body cost block.

**Why a table row is not enough.** The vendor pricing page (`https://platform.claude.com/docs/en/about-claude/pricing`, fetched 2026-11-20) prices this model by prompt length, which no other row in the table does:

- A prompt of up to 100,000 tokens pays $0.10 per MTok base input.
- A prompt over 100,000 tokens pays $0.50 per MTok base input.
- Both tiers keep the standard multipliers: 1.25x for a 5-minute cache write, 2x for a 1-hour cache write, 0.1x for a cache hit, and 5x for output.
- A request's prompt length counts all of its input tokens, cache reads and cache writes included. Each request is priced on its own.
- The 1.1x US `inference_geo` multiplier applies to the over-100,000 prices too.

The models overview page (`https://platform.claude.com/docs/en/about-claude/models/overview`, fetched 2026-11-20) gives `claude-haiku-5-5` as the Claude API ID and a 1M-token context window.

The rate table holds one base rate per model. The pr-cost ledger stores tokens summed per model and pricing variant, so a re-price from stored tokens cannot recover which turns crossed the threshold unless the tier is part of the stored key.

**Intended outcome.** The three outcomes below hold for turns recorded or captured after this change. Ledger rows and routing-guard captures written before it, and checkouts without it, behave as the Approach's assumption ledger states.

- A `claude-haiku-5-5` turn is priced at the tier its own prompt length selects.
- A ledger row that holds such turns re-prices to the same dollars from its stored tokens.
- No report that prices from a turn's own usage lists the model as unpriced.

## Approach

Price `claude-haiku-5-5` at the tier its own turn's prompt length selects, and make that tier part of the turn's pricing-variant label, so every stored token group names the rates it was priced at. Stored groups then re-price from model, label and token counts through one new pricing function. That function replaces the two builders that turn summed tokens back into a usage dict, which would read a sum of many turns as one prompt.

**Design.**
- **Rates.** `_MODEL_BASE_INPUT_RATES` gains `"claude-haiku-5-5": 0.10`, placed directly above `"claude-haiku-4-5-20251001"`. A new `_LONG_PROMPT_TIERS: dict[str, _LongPromptTier]` holds `"claude-haiku-5-5": _LongPromptTier(threshold_tokens=100_000, base_input_rate=0.50)`, where `_LongPromptTier` is a `NamedTuple`. A turn whose prompt length is over `threshold_tokens` pays `base_input_rate` in place of its table row, with every class multiplier unchanged.
- **Labels.** `_PRICING_VARIANT_TERMS: dict[str, _VariantTerms]` maps each label to three conditions, `fast`, `us_geo` and `long_prompt`, held in a `NamedTuple`. It keeps today's four labels first, in today's order, and appends `long_prompt`, `fast_long_prompt`, `us_geo_long_prompt` and `fast_us_geo_long_prompt`. `_PRICING_VARIANTS` becomes `tuple(_PRICING_VARIANT_TERMS)`, and a reverse map derived from the table serves `_pricing_variant`.
- **Tier selection.** `_pricing_variant(model, usage)` gains the `model` parameter. It sets `long_prompt` only when `model` is in `_LONG_PROMPT_TIERS` and `_context_at_turn(usage)` is strictly greater than that model's threshold, so every other model keeps today's four labels. It reads the record's top-level fields, also when `usage.iterations` lists several sampling iterations (row 26).
- **Pricing functions in `pricing.py`.**
  - `_rates_from_base(model, base_input)`: today's `_model_rates` derivation, cache-read override included, extracted.
  - `_rates_for_variant(model, variant)`: the tier's rates times the label's fast and US-geo multipliers. It returns `None` for an unpriced model, an unknown label, or a long-prompt label on a model with no tier.
  - `_price_token_counts(model, variant, counts_by_class)`: dollars for all five classes, a missing class counting as 0. It returns `None` when `_rates_for_variant` does or a class label is unknown.
  - `_turn_rates(model, usage)`: `_rates_for_variant(model, _pricing_variant(model, usage))`.
  - `_price_turn` keeps its three-tuple and takes its dollars from `_price_token_counts(model, _pricing_variant(model, usage), _token_counts(usage))`.
  - `_reprice_token_splits` calls `_price_token_counts` per group. `_USAGE_FIELDS_BY_PRICING_VARIANT` and `_usage_for_token_group` are deleted.
  - `_model_rates(model)` also returns `None` for a model in `_LONG_PROMPT_TIERS`, because no single rate set applies to it.
- **Callers.**
  - `cost.py:135` and `review_rounds.py:296` pass `model` to `_pricing_variant`.
  - `routing_guard._loop_overhead` calls `pricing._price_token_counts`. `_VARIANT_USAGE_FIELDS` and `_usage_from_variant_tokens` are deleted.
  - The three counterfactual functions in `cache_rebuild_rules.py` take `pricing._turn_rates(model, usage)` in place of `pricing._model_rates(model)` and drop their hand-applied fast and US-geo blocks.
  - `routing_guard._loop_carry_rate` keeps its code. A tiered model's later turns now skip as an unpriced model's do and mark the loop degraded, and the key-off arm's `_DEGRADED_NOTICES` entry names that cause.
- **Left as is.**
  - `_PRICING_FETCH_DATE` stays `date(2026, 9, 5)` (row 16).
  - `_CAPTURE_REVISION` stays 1 (rows 19 and 24).
  - The pr-cost write-time check, export, ledger parser and `ledger_rounds` read labels and models through `_PRICING_VARIANTS`, `_MODEL_BASE_INPUT_RATES` and `_reprice_token_splits`, so their code takes the new labels with no edit.
- **Changed only in a comment.** `pr_cost_ledger.py` gains only a comment edit (row 33). `cache_rebuild.py` gains only a comment edit (row 47).

**Alternatives set aside.**
- A flat $0.10 row, with the undercount documented or with over-threshold turns left in excluded spend: the engineer selected the tiered option (row 1).
- Tier selection inside `_price_turn` with no new labels: the ledger sums tokens per model and label, so a re-price could not tell which turns crossed the threshold.
- A separate higher-tier key in `_MODEL_BASE_INPUT_RATES`: keys must be vendor-published model IDs (row 6).
- Carrying the tier into `_price_turn` inside a built usage dict: see M4.
- Storing `later_turns` per label for `_loop_carry_rate`: see M7.
- Moving `_PRICING_FETCH_DATE` to 2026-11-20: see row 16.

**Rollback.** Once any ledger row or capture holds a long-prompt label, rolling back is a forward change, never a plain revert (row 28).
- The rollback keeps all eight labels in `_PRICING_VARIANT_TERMS`, so the ledger parser, export and capture validator still accept them.
- Withdrawing Haiku 5.5's pricing removes its `_MODEL_BASE_INPUT_RATES` row and its `_LONG_PROMPT_TIERS` row together. Its stored groups then become unpriceable, as a removed model key's do (pricing.py:67-68). Removing only the tier row would price the model's new over-threshold turns at the lower tier with no notice.
- A `_LONG_PROMPT_TIERS` row is otherwise permanent. If the vendor drops tiered pricing, the row stays, with `base_input_rate` set to the new flat rate.
- A row kept at a flat rate still makes `_model_rates` return `None` for its model. `_loop_carry_rate` then keeps skipping that model, and key-off loops that carry it stay degraded (routing_guard.py:1861-1865).

**Assumption ledger.**

**Root:** `claude-haiku-5-5` turns land in every cost report's excluded spend because `_MODEL_BASE_INPUT_RATES` has no row for the model. The vendor prices each request at one of two base rates by prompt length, which a one-rate-per-model table and a ledger summed per model and label cannot express. `[verified: pricing.py:69-94, :690-703; G1]`

**Givens:**
- G1. The vendor prices Claude Haiku 5.5 by prompt length. Up to 100,000 tokens: $0.10 base input, $0.125 5-minute write, $0.20 1-hour write, $0.01 cache hit, $0.50 output. Over 100,000: $0.50, $0.625, $1, $0.05, $2.50. Prompt length counts every input token, cache reads and writes included. Each request is priced on its own. The 1.1x US `inference_geo` multiplier applies to the higher prices too. Reason: the vendor sets its prices. `[verified: pricing page fetched 2026-11-20 by the dispatching session, excerpts relayed in the dispatch]`
- G2. Claude Code writes `claude-haiku-5-5` to `message.model`. Reason: Claude Code owns that string. `[verified: the models overview page gives it as the API ID and alias, relayed in the dispatch]`
- G3. Pricing-variant labels persist in pr-cost ledger rows and routing-guard captures that other checkouts and accounts write and read. A label is never renamed or removed, and an older checkout meets a new label as unknown. Reason: rows already written and checkouts already installed lie outside this change's reach. `[verified: pricing.py:18-19, :55; docs/pr-cost.md:63-64, :106]`

**Rows:** line numbers cite the merge-base tree `ab247f0e`, except where a row says it cites the staged tree (row 33, and the `pricing.py:18-21` comment).
1. The engineer selected tier pricing per turn with new variant labels. `[engineer-verified: "Tiered + new variants (Recommended)"]`
2. That option's description (per-turn tier selection in `_price_turn` from the turn's prompt length, plus new long-context variant labels so re-pricing stays exact) is the dispatching session's text, not the engineer's. This plan selects the tier in `_pricing_variant`, which `_price_turn` calls, and names the labels `long_prompt`. `[unverified]`
3. G1's prompt length is `_context_at_turn(usage)`: input plus cache read plus both cache-write classes. The flat `cache_creation_input_tokens` counts only when the nested block is absent, and output is excluded. `[verified: pricing.py:224-249]`
4. The higher tier applies strictly over 100,000 tokens, so a prompt of exactly 100,000 pays the lower tier. `[verified: G1's "up to" and "over" rows]`
5. Both tiers keep the standard multipliers, so `_rates_from_base` derives the higher tier from $0.50 unchanged: 0.625, 1.00, 0.05 and 2.50. Each class's ratio to cache read is therefore the same in both tiers. `_cache_read_equivalent_weights` (pricing.py:184-197) needs no change. `[verified: G1; pricing.py:163-197]`
6. `_MODEL_BASE_INPUT_RATES` keys persist verbatim and must be vendor-published model IDs. `[verified: pricing.py:64-68; test_transcript_pr_cost_ledger.py:638-642]`
7. Three `_price_turn` call sites pass a usage dict the caller built rather than one read from a transcript:
   - pricing.py:699 in `_reprice_token_splits`, from summed tokens. Its only non-test caller is ledger_rounds.py:55-56.
   - routing_guard.py:1848 in `_loop_overhead`, from summed tokens.
   - plan_boundary.py:73, one hypothetical request on `claude-sonnet-5` (plan_boundary.py:20), which is not a sum.

   `[verified: grep of "_price_turn(" and "_reprice_token_splits(" across transcript_analysis/. That every other call site passes one turn's own usage is the exploration report's finding, not reopened]`
8. routing_guard.py:297-303 duplicates pricing.py:664-669, and routing_guard.py:1824-1839 duplicates pricing.py:672-687. `[verified: read]`
9. `_price_turn` prices `usage.speed` and `usage.inference_geo` as reported, with no per-model eligibility list, and a regression test pins that. `_pricing_variant` must therefore label every combination it can meet, fast on a higher-tier Haiku 5.5 prompt included. `[verified: pricing.py:622-629; test_transcript_pricing.py:70-81]`
10. The vendor's fast-mode page lists the models that offer fast mode and does not list Claude Haiku 5.5. The `fast_long_prompt` and `fast_us_geo_long_prompt` labels, and the fast lower-tier labels' Haiku dollars, exist so the label table covers every combination `_price_turn` can meet (row 9). They are not expected for this model, and no shipped text says Haiku 5.5 offers fast mode. `[verified: https://platform.claude.com/docs/en/build-with-claude/fast-mode availability list, fetched 2026-11-20 by the plan-review backend reviewer]`
11. With the compaction beta enabled, every response carries `usage.iterations`, one entry per sampling iteration. The top-level `input_tokens` and `output_tokens` sum every non-compaction iteration and leave out the compaction iteration. A record's top-level fields can therefore sum several sampling iterations. `[verified: platform.claude.com/docs/en/build-with-claude/compaction-threshold, "Understanding usage", fetched 2026-11-20 by the dispatching session, excerpt relayed in the dispatch]`
12. "Context" already names `_context_at_turn` and the `>=200k` reporting bucket, whose threshold and inclusive edge differ from this tier's (pricing.py:100-102, :252-253). The pricing page words the tier by prompt length. `[verified: read; G1]`
13. After this change `_model_rates` has two production callers: plan_boundary.py:59 and :150 on `claude-sonnet-5`, and routing_guard.py:1862, which treats `None` as a skipped model. Its three cache_rebuild_rules.py callers (:294, :322, :361) hold real usage and move to `_turn_rates`. `[verified: grep of "_model_rates("; read of routing_guard.py:1857-1868]`
14. Cache reads and both cache-write classes all count toward prompt length. Each cache-rebuild counterfactual re-prices a write as a read, or one write class as the other, so it keeps the actual turn's prompt length and tier. `[verified: cache_rebuild_rules.py:279-376; row 3]`
15. `_loop_carry_rate` holds only `{model: turn_count}` per loop, built at routing_guard.py:1150. It prices a carried token at each later turn's cache-read rate. It already skips an unpriced model, and the loop then counts as degraded. `[verified: routing_guard.py:1857-1868, :1888]`
16. `_PRICING_FETCH_DATE` stays 2026-09-05.
    - It sets every model's re-verify-by date (pricing.py:24, :58, :98).
    - Only the Haiku 5.5 rows were fetched on 2026-11-20.
    - Moving it would claim a re-verification no one ran and shift every row's date from 2026-12-04 to 2027-02-18.
    - Keeping it gives the new row the earlier date, the conservative direction the three past model-row commits also took.
    - Two rows under one stamp can now differ by Haiku 5.5's dollars, as after every earlier model-row addition. The earlier row's `unpriced_tokens` shows it.

    `[verified: pricing.py:24-98; docs/pr-cost.md:307-322; the dispatch states no other row was re-verified; past commits per the exploration report]`
17. Rows written before this change hold no Haiku 5.5 token group. The writer adds a turn to the ledger splits only once `_price_turn` priced it, and counts an unpriced turn in `unpriced_turns`. A re-price of such a row keeps those turns missing, as docs/transcript-analysis.md:1480 states. `[verified: review_rounds.py:372-378; cost.py:129-141]`
18. Routing-guard captures record every model's overhead tokens, unpriced ones included. A capture written before this change can therefore hold a `claude-haiku-5-5` group under a lower-tier label that sums turns over the threshold. This change prices that group at the lower tier, where compute skipped it before. `[verified: review_rounds.py:379-380; test_transcript_routing_guard_compute.py:920]`
19. Asked whether to bump `_CAPTURE_REVISION` for row 18, under the code's rule to bump "only when a change alters what a stored row means" (routing_guard.py:59-61), the engineer chose to keep revision 1. `[engineer-verified: "Keep revision 1 (Recommended)"]`
20. A checkout without this change meets the new labels as it meets any unknown label:
    - The ledger parser accepts them by key shape (pr_cost_ledger.py:176-179).
    - Export keeps the row and passes its `model_breakdown` through unfiltered. It drops the labels from the `review_rounds` cell's token objects and counts them (pr_cost_export.py:40-91).
    - `review-cost-by-size` excludes a PR whose rounds that are not after-merge hold one (ledger_rounds.py:54-59; docs/transcript-analysis.md:1477).
    - Routing-guard reads a capture holding one as unusable (routing_guard.py:639-640, :733-734), which adds `_REASON_FILE_UNUSABLE` (:258, :1767). Compute then reports NOT RUN for the whole sample, not only that branch. Capture reports the row invalid and exits 3.
    - That checkout cannot rebuild the file, because a capture file is never rebuilt once it exists (docs/transcript-analysis.md:1883). The remedy is to update the checkout that runs compute.

    A lower-tier `claude-haiku-5-5` group fails the same model check on such a checkout (pr_cost_export.py:46). Every earlier model-row addition did the same. `[verified: read of pr_cost_export.py:40-91 and pr_cost_ledger.py:176-179; the whole-sample NOT RUN per the plan-review backend trace of routing_guard.py:1802-1819 and :2018-2019, and the after-merge scope per the code-review backend and product traces of ledger_rounds.py, not reopened]`
21. After code-review round 3, `pricing.py` (733 lines before this change) is about 770 lines, `test_transcript_pricing.py` (769 before) is 809, and the seam file (M11) is about 208. Verification step 9 re-measures them. `[verified: line counts of the working tree after code-review round 3]`
22. Row 19's option description is the dispatching session's text, not the engineer's. It said:
    - standing captures stay readable;
    - the undercount is limited to Haiku 5.5 turns over 100,000 prompt tokens in captures written before this change;
    - a Known-gaps line in `docs/transcript-analysis.md` records it.

    `[unverified]`
23. Asked at plan review "This plan projects about 520 changed lines (an estimate; threshold 400). Split into smaller PRs now, or proceed?", the engineer chose to proceed as one PR. `[engineer-verified: "Proceed anyway"]`
24. The engineer was asked again, with this fact added: compute prints a degraded notice for such a capture today and would print none after this change, so a PASSED or FAILED verdict could rest on a silent undercount. The engineer chose to keep revision 1 with full disclosure. `[engineer-verified: "Keep revision 1, disclose fully (Recommended)"]`
25. Row 24's option description is the dispatching session's text, not the engineer's. It said the Known-gaps line and a CHANGELOG Migration line:
    - name the affected captures;
    - say the degraded notice no longer fires for them;
    - give the remedy of deleting that branch's capture file and re-capturing while its sessions are still retained.

    `[unverified]`
26. The pricing page tiers a request: "Each request is priced on its own", and a request's prompt length "counts all of its input tokens". This plan therefore selects the tier from a record's top-level fields, and `test_a_multi_iteration_usage_selects_its_tier_from_the_top_level_fields` pins that.
    - Row 11's excerpt says only `input_tokens` and `output_tokens` sum a record's non-compaction iterations. Whether the top-level cache-read and cache-write fields sum them too is unconfirmed.
    - Whether the vendor instead tiers each sampling iteration on its own is unknown. If it does, a record's tier can differ from the vendor's in either direction.
    - `pricing._pricing_variant`'s docstring is the one home of the iteration-sum fact and cites the vendor compaction page. No shipped doc states the per-iteration unknown (row 40).

    `[unverified]`
27. The top-level-fields policy (row 26) stands on row 11's vendor excerpt. `[verified: row 11's excerpt; row 26 marks the tiering question unverified]`
28. A plain revert makes the four long-prompt labels and the `claude-haiku-5-5` model key unknown to the reverting checkout, with row 20's consequences, compute's whole-sample NOT RUN included. Removing a `_LONG_PROMPT_TIERS` row leaves that model's stored long-prompt groups unpriceable, because `_rates_for_variant` returns `None` for a long-prompt label on a model with no tier. `[verified: row 20; this plan's _rates_for_variant contract]`
29. This diff grows four test files already over the 1,000-line limit and marked split pending in docs/reports/2026-11-19-code-file-size-offenders/findings.md. After code-review round 3 the first three's net growth is about the following, and Verification step 9 re-measures it:
    - `test_transcript_pr_cost.py` (:235), 3,563 to 3,606 lines, +43;
    - `test_transcript_pr_cost_ledger.py` (:249), 1,985 to 1,994, +9;
    - `test_transcript_routing_guard_compute.py` (:242), 2,164 to about 2,187, about +23.

    The fourth, `test_transcript_routing_guard_capture.py` (:226, 5,483 lines), grows by row 39's two tests and code-review round 3's listing-command test, an amount Verification step 9 measures. No check enforces the limit yet (docs/design-decisions/code-file-line-limit.md:50-57), so the PR body states the growth of all four. `[verified: line counts before implementation and after the fix round; the capture file's size per the plan-review round 4 backend and SDET reads; Verification step 9 re-measures them]`
30. After round 1, this plan projected about 710 changed lines, against the about 520 that row 23's question stated. The engineer was asked whether one PR still stands, and chose to proceed. `[engineer-verified: "Proceed anyway"]`
31. `test_cost_report_prices_both_tiers_and_excludes_nothing` is the evidence for the `EXCLUDED SPEND` behavior. Verification step 10 adds a positive control only when the corpus holds a Haiku 5.5 turn. `[verified: read of the test]`
32. After code review, the engineer was asked whether a test that a Haiku 5.5 `long_prompt` token group survives a pr-cost export should be added. The test-placement rule puts it in `tests/test_transcript_pr_cost_export.py`, which the file list did not name. The engineer chose to add that file. `[engineer-verified: "Add the file to the plan (Recommended)"]`
33. After code review, the engineer was asked whether to edit `pr_cost_ledger.py:178`. Its "checked for key shape only" is true of the ledger parser but can read as contradicting the corrected `pricing.py:18-21` comment, which says an older checkout does not tolerate an added label. The engineer chose to add the file and reword the comment. `[engineer-verified: "Add it to the plan and reword (Recommended)"]`
34. Rows 32 and 33's question wording and option descriptions are the dispatching session's text, not the engineer's. The test and comment wording this plan prescribes for them are this plan's. `[unverified]`
35. The capture disclosure Critical files prescribes carries the three points row 25 records: it names the affected captures, says their degraded notice no longer prints, and points to "The captures directory" for delete and re-capture. It adds these, none contradicting the engineer's choice to keep revision 1 with full disclosure:
    - Row 24's fact: the group's turns over 100,000 prompt tokens price at the lower tier, so a PASSED or FAILED verdict can rest on that undercount.
    - The group was skipped before and is priced now, so a sample's figures can move after upgrading, even where no turn crossed 100,000 tokens.
    - A command that lists the affected captures' file names, which are unsalted branch digests. Where it runs is stated at "The captures directory" (row 45). It runs once per account store the note's rows name.
    - Only a file modified before the upgrade can hold the undercount.
    - The remedy's single home is "The captures directory" (Critical files, `docs/transcript-analysis.md:1883`; row 42).

    `[verified: rows 24 and 25; merge-base and staged routing_guard.py _loop_overhead]`
36. At plan review round 3, asked whether the plan's engineer-verified quotes are the engineer's own words or selections, the engineer answered that all of them are. The other round-3 answers are on rows 37 and 38. `[engineer-verified: "Yes, all of them"]`
37. At plan review round 3, asked which deliverables beyond or unclear against the Ask stay, the engineer kept all three: the `docs/cost-ledger.md:26` clause, the `context_composition.py` docstring, and the `_DEGRADED_NOTICES` rewording in `routing_guard.py`. `[engineer-verified: "docs/cost-ledger.md:26 clause, context_composition.py docstring, Degraded-notice rewording in routing_guard.py"]`
38. At plan review round 3, asked whether to split at about 840 changed lines, the engineer chose to proceed as one PR. `[engineer-verified: "Proceed anyway"]`
39. After code-review round 2, asked whether to add `test_transcript_routing_guard_capture.py` to Critical files with two tests, the engineer chose to add it. The two tests are the dispatching session's proposal, specified under Critical files. `[engineer-verified: "Add the file (Recommended)"]`
40. After a `plan-architect` consult's per-site list of caveat deletions was summarized to the engineer, the engineer chose to apply it. `[engineer-verified: "Yes apply them"]`
41. The list row 40 approves is the dispatching session's summary of that consult, not the engineer's words. Critical files' wording for each deleted or shrunk site is this plan's rendering of that summary. Two clauses the summary did not name were kept after plan-review round 5: the retention clause at "The captures directory", and "a sample's figures can move after upgrading". Both serve row 25's remedy and the notice-stops point. Row 42 settles the retention clause as reworded, not struck. The engineer can still strike the other. `[unverified]`
42. After code-review round 4 held three findings, the engineer answered each. The carry item's finding (`docs/transcript-analysis.md:1922`, in the staged tree as code-review round 4 saw it): keep the row 40 shrink. The capture item's modification-time finding (:1924, same tree) and the retention finding at "The captures directory" (:1883): ask the architect. The engineer then chose the architect's picks with a plan mirror. `[engineer-verified: "Keep the shrink (Recommended)", "Ask the architect", "Architect's picks + plan mirror (Recommended)"]`
43. The architect's picks are to delete only the clause "and the modification-time split", and to reword the retention clause rather than strike it. The architect's reason for rewording is that a strike leaves an unconditional delete-and-recapture instruction. This is the dispatching session's relay of the consult, not the engineer's words. `[unverified]`
44. A re-run of capture over an existing file prints no earliest-record date, and no flag reports without writing. A run that publishes a file prints the date on its `captured` line. The `PRICING INTEGRITY` drift notice is scan-wide: the scan sets the drift flag for every scanned session, so the notice can print in a run that published nothing. Its remedy points to "The captures directory" for every row published by a run that printed the notice, which includes rows an earlier drift-printing run published. The staged clause "a deleted file is not rebuilt" is dropped, because capture does rebuild a deleted file from the surviving sessions. `[verified: routing_guard.py:1391-1401, :1404-1415, :1518-1520, :227-233, :2070-2091, :1094, :1640; pricing.py:393]`
45. After code-review round 5 held four findings, the engineer answered each. The carry item's keep: log it with carry-forward. The remedy chain for an earlier-run capture (`docs/transcript-analysis.md:1883-1885` and the Known-gaps pointer): keep as is. The outside-session qualifier for capture file names: state it once at "The captures directory". The modification-time filter and the test docstring in `test_transcript_pricing_prompt_tiers.py:137`: keep both. `[engineer-verified: "Log with carry-forward (Recommended)", "Keep, settled (Recommended)", "State once at the home (Recommended)", "Keep both (Recommended)"]`
46. The meaning of each row 45 selection is the dispatching session's reading of its option text, not the engineer's words. "Carry-forward" lets a later same-failure-mode repeat on the unchanged block carry the keep. "The home" is the "The captures directory" paragraph. The edit is two sites, which the Dispatch paragraph names. `[unverified]`
47. After code-review round 6 held one finding, on the cache-rebuild margin's stated multipliers at `docs/transcript-analysis.md:1140` and `cache_rebuild.py:392-394`, the engineer chose to fix both sites. `[engineer-verified: "Fix both sites (Recommended)"]`
48. The finding's premise: the margin denominator takes each turn's dollars from `_price_turn`, and the net's three counterfactuals take `_turn_rates`. Both resolve through `_pricing_variant`, so both carry the prompt-length rate with the fast-mode and US-inference-geo multipliers. This change makes the two sites' stated multipliers incomplete, which is why the edit is in scope of the Ask. `[verified: cache_rebuild.py:385, :396, :416; cache_rebuild_rules.py:294, :315, :347; pricing.py:230-247, :675]`
49. `cache_rebuild.py` is added to Critical files for the comment only, and the test docstring at `test_transcript_cache_rebuild_ttl_footing.py:327` is left unedited. Both are the dispatching session's reading of "Fix both sites", not the engineer's words. The docstring's class scopes itself to the fast-mode and US-geo multipliers on a model with no prompt-length tier, so its sentence is true. The engineer can extend the fix to it. `[unverified]`

**Mechanisms:**
- M1: `_LONG_PROMPT_TIERS`, a second table keyed by model ID beside the unchanged `_MODEL_BASE_INPUT_RATES`. `anchors: root, row3, row4, row5, row6`.
- M2: One `_PRICING_VARIANT_TERMS` table covering all eight combinations of three conditions. `anchors: row1, row8, row9, row10, row20`. It replaces three structures rather than adding a fourth: `_pricing_variant`'s if-chain, `_USAGE_FIELDS_BY_PRICING_VARIANT` and routing_guard's copy of it. Building labels by string concatenation and parsing them back was set aside, because the persisted label set would then live in no literal a reviewer can read.
- M3: The `long_prompt` label stem. `anchors: row12`.
- M4: Stored groups price through `_price_token_counts`, so no prompt length is ever derived from a sum. `anchors: row7, row8, row17`. This path removes code. Checked instead:
  - A tier marker field in the built usage dict fails, because `_price_turn` would trust that field on a real record too, and a future vendor field could share its name.
  - An override keyword on `_price_turn` fails, because each summed-token caller must remember to pass it, and an omission silently reads the sum as one prompt.
- M5: `_model_rates` returns `None` for a tiered model. `anchors: row13`. Checked instead: a tier check inside `_loop_carry_rate` alone fails, because `_model_rates` would keep returning the lower tier to any later caller that has no usage.
- M6: `_turn_rates` in the three cache-rebuild counterfactuals. The margin denominator, priced by `_price_turn`, and the net, priced by `_turn_rates`, both resolve through `_pricing_variant`, so they share the prompt-length rate (row 48). `anchors: row3, row14, row47, row48, row49`.
- M7: `_loop_carry_rate` skips a tiered model, and the loop counts as degraded. `anchors: row15`. Checked instead:
  - Storing `later_turns` per label changes a persisted capture shape the validator checks (routing_guard.py:657-659), so captures written by different checkouts refuse each other. A per-token carry rate still could not express a carried token pushing a turn over the threshold.
  - Pricing later turns at the lower tier undercounts silently.
- M8: `_PRICING_FETCH_DATE` unchanged. `anchors: row16`.
- M9: Capture revision 1 kept, disclosed in a Known-gaps line in `docs/transcript-analysis.md` and a CHANGELOG Migration line. `anchors: row18, row19, row22, row24, row25, row35, row40, row41, row42, row43, row44, row45, row46`. A bump was the alternative. It makes every standing capture unreadable, because a reader opens only the current revision (routing_guard.py:59-61). Each must then be re-captured while its sessions are still retained.
- M10: One `code-writer` dispatch, in one PR. `anchors: root, row7, row21, row23, row30`. The reason is under Critical files.
- M11: The tier tests go in a seam file, `test_transcript_pricing_prompt_tiers.py`, decided now rather than after measuring. `anchors: row21, row29`. Kept in `test_transcript_pricing.py`, they would leave that file at roughly 950 to 1,000 lines. `.claude/rules/transcript-analysis-tests.md` splits a file that would cross the limit at a named seam, and `test_transcript_pricing_session_helpers.py` is the precedent for a pricing seam file.
- M12: Row 26's top-level-fields policy, pinned by `test_a_multi_iteration_usage_selects_its_tier_from_the_top_level_fields`, with the iteration-sum fact homed in `pricing._pricing_variant`'s docstring. `anchors: row11, row26, row27, row40`.
- M13: Rollback is a forward change that keeps the eight labels. `anchors: row20, row28`.
- M14: Three files joined after code review: an export test that pins a Haiku 5.5 `long_prompt` group surviving `pr-cost-export` (the model key and one label), a one-line scoping edit to `pr_cost_ledger.py`'s label comment, and `test_transcript_routing_guard_capture.py`, whose second test is the capture validator's pin of the eight-label contract. The ledger parser's pin is the other, and both are independent of Haiku 5.5 staying priced. `anchors: row20, row32, row33, row34, row39`.

## Critical files

**Dispatch: one `code-writer`.** The session dispatches with `model: sonnet` and without `isolation: "worktree"`. This plan is already implemented and staged, code-review round 3's fixes included, and the lists below describe the final state. Row 40's deletions and the edits rows 42, 45 and 47 decide have landed in the staged tree.

The agent runs steps 3-9 once over the whole staged tree and reports each command's result, including step 6's failing tests per mutation and step 9's line counts. The original implementation fit one dispatch because `pricing.py`'s new functions and their caller files are a signature and its consumers, and the tests and docs name the new functions, so no part has inputs disjoint from the rest.

**Create:**
- `claude/.claude/scripts/tests/test_transcript_pricing_prompt_tiers.py` (M11), with these classes and tests:
  - `TestLongPromptTierRates`:
    - `test_each_tier_matches_the_vendor_rows`: both tiers' five rates through `_rates_for_variant`, against G1.
    - `test_us_geo_applies_to_the_higher_tier`: `us_geo_long_prompt` at 1.1 times the higher tier.
    - `test_every_label_prices_a_fixed_input_at_its_literal_dollars`, parametrized over the eight labels. `_price_token_counts("claude-haiku-5-5", label, {"input": 1_000_000})["input"]` equals a literal: $0.10, $0.20, $0.11 and $0.22 for the four lower-tier labels, and $0.50, $1.00, $0.55 and $1.10 for the four long-prompt labels.
    - `test_price_turn_on_a_usage_selecting_each_label_matches_its_literal_dollars`, parametrized over the eight labels. A lower-tier label's usage carries 100,000 input tokens and a long-prompt label's carries 1,000,000, each with that label's speed and geo fields. The input dollars equal a literal: $0.01, $0.02, $0.011 and $0.022 for the four lower-tier labels, and $0.50, $1.00, $0.55 and $1.10 for the four long-prompt labels.
    - `test_model_rates_has_no_single_rate_for_a_tiered_model`.
    - `test_rates_for_variant_returns_none_off_the_table`, parametrized over a long-prompt label on `claude-sonnet-5`, an unpriced model, and an unknown label.
    - `test_every_tiered_model_is_in_the_rate_table`.
  - `TestLongPromptTierSelection`:
    - `test_threshold_is_strictly_greater_than_100k`, parametrized over three prompt compositions, each at 100,000 and at 100,001 tokens: input only; spread across input, cache read and both nested write classes; and the write through `flat_cache_creation`. 100,000 labels `standard` and 100,001 labels `long_prompt`.
    - `test_output_tokens_do_not_count_toward_the_threshold`.
    - `test_a_model_without_a_tier_keeps_its_label_over_the_threshold`: `claude-sonnet-5` at 500,000 prompt tokens labels `standard`.
    - `test_each_fast_and_geo_combination_on_a_long_prompt_gets_its_own_label`, parametrized over the four combinations.
    - `test_variant_terms_hold_each_condition_combination_once`, which takes the number of conditions from `len(pricing._VariantTerms._fields)`, so a new condition fails on a missing label rather than on arity.
    - `test_a_multi_iteration_usage_selects_its_tier_from_the_top_level_fields`: a top-level input of 120,000 with two `message` iterations of 60,000 each labels `long_prompt` (row 26). Its docstring is its one-line summary.
    - `test_a_compaction_iteration_the_top_level_excludes_does_not_count_toward_the_tier`: a top-level input of 90,000, two `message` iterations of 45,000 and a 50,000-token `compaction` iteration label `standard`, where summing every iteration would label `long_prompt` (row 11).
  - `TestTurnRates`:
    - `test_a_usage_selecting_each_label_gets_that_labels_rates`, parametrized over the eight labels: `_turn_rates("claude-haiku-5-5", usage)` equals `_rates_for_variant("claude-haiku-5-5", label)`.
    - `test_a_us_geo_turn_on_a_model_without_a_tier_gets_its_standard_rates_times_the_geo_multiplier`.
  - `TestHaiku55PricedTurns`:
    - `test_turn_at_100k_prompt_tokens_prices_whole_at_the_lower_tier`: priced, `unpriced_tokens` 0, input $0.01.
    - `test_turn_at_100001_prompt_tokens_prices_whole_at_the_higher_tier`: priced, `unpriced_tokens` 0, input $0.0500005, so every token takes the higher rate, not only those past 100,000.
    - `test_cost_report_prices_both_tiers_and_excludes_nothing`: `cost._cost_report`'s full report over a 100,000-token and a 1,000,000-token turn prints no `EXCLUDED SPEND` line and a grand total of $0.51. It follows the Opus 5.5 end-to-end test (test_transcript_cost.py:2327-2341). It has no `--summary` leg. Tier selection happens in `_price_turn`, which both render modes share. Summary mode only renders the unchanged banner path, which `test_silent_on_clean_corpus_summary_mode` (test_transcript_cost.py:3365) already covers.

**Modify, production** (under `claude/.claude/scripts/transcript_analysis/`):
- `pricing.py`: everything under Design's Rates, Labels, Tier selection and Pricing functions. Each prescribed comment is one line:
  - The new `_MODEL_BASE_INPUT_RATES` row: `# Claude Haiku 5.5's up-to-100,000-token row, fetched 2026-11-20; its higher tier is in _LONG_PROMPT_TIERS.`
  - `_LONG_PROMPT_TIERS`, three lines:
    - `# A turn whose _context_at_turn is over threshold_tokens pays base_input_rate in place of its _MODEL_BASE_INPUT_RATES row.`
    - `# Removing a row leaves every stored long-prompt group of that model unpriceable.`
    - `# Removing a row while keeping the model's _MODEL_BASE_INPUT_RATES row prices its over-threshold turns at the lower tier with no notice.`
  - Its Haiku entry: `# Claude Haiku 5.5's over-100,000-token row, fetched 2026-11-20.`
  - :19, which said older checkouts read an added label, becomes three lines. They name the readers that do not tolerate one (the routing-guard capture validator, `pr-cost-export`'s `review_rounds` filter and `review-cost-by-size`), and say a new label needs a `routing_guard._CAPTURE_REVISION` decision and a CHANGELOG Migration line.
  - :20 becomes `# A new class also needs a mapping in _token_counts and a rate in _rates_from_base.`
  - The key-rules comment above `_MODEL_BASE_INPUT_RATES` (:62-63) names `_rates_from_base` and adds that a model the pricing page prices by prompt length also needs a `_LONG_PROMPT_TIERS` row. The cache-read override comment (:34) names `_rates_from_base` too.
  - :47-51 become `# A new multiplier condition needs a _VariantTerms field and a _PRICING_VARIANT_TERMS label for every combination, or pr-cost ledger cells file its turns under the wrong variant.`
  - Below it: `# context_composition._context_composition_turn_rate_scale reads speed and inference_geo itself and needs the same condition.`
  - `_PRICING_VARIANT_TERMS` keeps :55's `# Same persistence rule as _TOKEN_CLASSES.`
  - `_price_turn`'s docstring says its dollars follow the rates `_pricing_variant`'s label implies.
  - `_pricing_variant`'s docstring keeps its top-level-fields and iteration-sum sentences and gains the vendor compaction page's URL, `https://platform.claude.com/docs/en/build-with-claude/compaction-threshold` (row 26).
- `routing_guard.py`:
  - delete :297-303 and :1824-1839;
  - `_loop_overhead` (:1842-1854) calls `pricing._price_token_counts(model, variant, token_counts)`;
  - `_DEGRADED_NOTICES` (:285-291) builds each arm's notice from a new `_DEGRADED_CAUSES_BY_ARM`. The key-on causes stay as today. The key-off causes end `"or a model has no price or is priced by prompt length"`, under a comment that only the key-off arm prices later turns. No test or doc matches the literal text.
- `pr_cost_ledger.py:178`: the comment's last sentence becomes `New variant and class labels need neither here, because this parser checks them for key shape only.`, so it scopes the claim to the ledger parser beside `pricing.py:18-21` (row 33).
- `cache_rebuild_rules.py`: :289-303, :319-336 and :358-376 per M6. The docstrings at :311-313 and :345-347 name `_turn_rates` in place of `_model_rates`.
- `cache_rebuild.py:392-396`: the comment is reworded, with no code change (row 47). Its text becomes: "Reuses _price_turn's own priced classes, so the margin denominator is priced at each turn's own rates, the same ones the net's per-call delta applies: the fast-mode and US-inference-geo multipliers and, for a model priced by prompt length, the higher base rate a turn takes over that model's threshold."
- `cost.py:135` and `review_rounds.py:296`: pass `model`.
- `context_composition.py:107-110`: docstring only. It cites a dollar-scaling step in `_price_turn` that no longer exists, so it names the speed and geo conditions `pricing._pricing_variant` reads instead. It also states that a prompt-length tier is not weighted, which understates Haiku 5.5 turns over 100,000 prompt tokens.

**Modify, tests** (under `claude/.claude/scripts/tests/`):
- `test_transcript_pricing.py`:
  - `TestPricingVariant` calls `_pricing_variant("claude-sonnet-5", usage)`.
  - `TestRepriceTokenSplits`:
    - every label in `_PRICING_VARIANTS` has a source usage, the long-prompt ones on `claude-haiku-5-5` with prompts over 100,000, and :709 passes each source's own model;
    - delete `test_usage_built_for_a_variant_classifies_back_to_that_variant`;
    - add `test_a_haiku_round_whose_lower_tier_turns_sum_past_the_threshold_reprices_per_turn`. Two lower-tier Haiku turns whose prompts sum past 100,000 and one higher-tier turn, filed through `review_rounds._add_turn_tokens`, re-price to the sum of their per-turn prices. It asserts the summed `standard` group's prompt tokens exceed 100,000, so the case exercises the sum;
    - add `test_returns_none_for_a_long_prompt_label_on_a_model_without_a_tier` beside :758;
    - reword the comment at :748.
- `test_transcript_package_module_prefixes.py:130`: add `"test_transcript_pricing_prompt_tiers.py"` to `TEST_FILES` after `"test_transcript_pricing.py"`. The test at :522-537 fails a package-importing test file that `TEST_FILES` omits.
- `test_transcript_pr_cost_ledger.py`:
  - :644-647: the literal lists all eight labels, in order.
  - `test_every_pricing_variant_label_satisfies_the_key_rule`, parametrized over `pricing._PRICING_VARIANTS`, beside the model-ID key-rule tests (:633-642).
- `test_transcript_pr_cost.py`:
  - `TestPrCostBranchTotalsByModel` (:1126) gains `test_haiku_5_5_turns_file_under_the_tier_their_prompt_selects`. A 100,000-token and a 1,000,000-token Haiku turn give `standard` (100,000 tokens, 10,000 micros) and `long_prompt` (1,000,000 tokens, 500,000 micros) groups under `claude-haiku-5-5`, and `_check_model_breakdown_cell` accepts the cell.
  - `TestSeededBreakdownSweep` gains `test_haiku_5_5_cell_holding_every_long_prompt_label_survives_a_ledger_write_and_parse`, a `model_breakdown` cell built from turns, written to a ledger file and parsed back.
- `test_transcript_pr_cost_export.py`: `TestPrCostExportReviewRounds` (:316) gains `test_a_haiku_5_5_long_prompt_group_survives_export_with_its_tokens_and_no_dropped_count` (row 32).
  - Its cell is `_cell_with` a mutation that adds `{"claude-haiku-5-5": {"long_prompt": _tokens(input=1_000_000)}}` to `_first_round(cell)["main_tokens"]`, exported through `_export_one_row`.
  - It asserts that `pr_cost_ledger._decode_review_rounds_cell(row["review_rounds"], 2)` equals that same cell, so the group's tokens survive intact.
  - It asserts that `provenance["review_rounds_dropped_keys"]` is `"0"`, and that `_DROPPED_LINE_PREFIX` is absent from stderr.
- `test_transcript_ledger_rounds.py:600-665`:
  - The first round also holds one Haiku 5.5 turn per long-prompt label and two lower-tier Haiku turns whose prompts sum past 100,000.
  - :659 asserts both models.
  - :660 asserts `claude-sonnet-5`'s four labels as a literal.
  - A new assertion checks that the two models' labels together equal `_PRICING_VARIANTS`.
  - The re-price assertion at :665 then covers the tier end to end.
- `test_transcript_routing_guard_compute.py`:
  - delete the two `_usage_from_variant_tokens` tests (:856-870);
  - `test_a_loops_overhead_equals_the_round_dollars_review_round_cost_prints` (:872) gains two lower-tier Haiku 5.5 turns whose prompts sum past 100,000 and one higher-tier turn;
  - beside `test_a_model_the_table_does_not_price_gives_a_degraded_notice_and_no_crash` (:922), `test_a_group_whose_label_the_model_cannot_take_gives_a_degraded_notice_and_no_crash`: a key-on loop holding a `long_prompt` group on `claude-sonnet-5`, through `_loop`'s `variant` argument;
  - `test_a_model_the_table_does_not_price_gives_a_degraded_notice_and_no_crash` is parametrized over its model only;
  - beside :1025, `test_a_model_priced_by_prompt_length_in_a_key_off_rows_later_turns_is_degraded`: `later={"claude-haiku-5-5": 4}` prints `_DEGRADED_NOTICES["off"]`.
- `test_transcript_routing_guard_capture.py` (row 39). The file already pins the published capture text as a literal in `TestGoldenFile` (:3350-3384), so the first test guards the doc, not the serializer.
  - `test_the_documented_capture_grep_pattern_matches_a_haiku_overhead_group_and_not_a_later_turns_only_loop`: it reads the `grep -F` pattern from the fence in `docs/transcript-analysis.md`'s capture Known-gaps item, as `_documented_capture_loop` (:5351) reads that doc's other fences. It builds each case through `_serialize_capture` with `_Loop(...)` and `_KeyStates` (:3528-3531), never `_capture_file_text`, which is plain `json.dumps`. The pattern matches the output for a Haiku 5.5 overhead group and does not match it for a loop whose only Haiku tokens are later turns.
  - `test_the_capture_validator_accepts_every_pricing_variant_label`: parametrized over `pricing._PRICING_VARIANTS` at module level, as at :3232. Each case builds a `claude-sonnet-5` overhead group through `_capture_loop` and `_capture_file_text` beside the `unknown-variant` case (:3014), and `_parse_capture_bytes` accepts it.
  - Code-review round 3's `test_the_documented_capture_listing_command_lists_only_the_capture_with_a_haiku_overhead_group`: it runs the documented `grep` command, with `<config-dir>` filled in, over a temporary captures directory holding two captures under their production file names, one with a Haiku 5.5 overhead group and one with the model only under later turns. It asserts the command lists only the first.
- `test_transcript_subagent_mix_dollars.py`, beside `test_reprice_as_delta_arithmetic` (:88):
  - `test_reprice_as_a_tiered_model_prices_an_over_threshold_turn_at_the_higher_tier`: the same 1,000,000-input-token `claude-sonnet-4-6` dispatch re-priced as `claude-haiku-5-5` shows Actual $3.00, Counterfactual $0.50 and Delta $2.50.
  - `test_reprice_as_a_tiered_model_tiers_each_turn_not_the_dispatch_sum`: a dispatch of two 60,000-input-token `claude-sonnet-4-6` turns re-priced as `claude-haiku-5-5` shows Actual $0.36, Counterfactual $0.01 and Delta $0.35. A summed 120,000-token prompt would give a $0.06 counterfactual.
- `test_transcript_cache_rebuild.py`:
  - `test_haiku_5_5_warm_read_leg_uses_the_turns_own_tier` for `_cache_rebuild_excess_dollars`. Its turn holds 90,000 cache-read and 20,000 five-minute-write tokens, a 110,000-token prompt whose re-priced write tokens alone sit under the threshold. The excess is 20,000 × ($0.625 − $0.05) / 1,000,000 = $0.0115.
  - The docstring at :62-63 names `_turn_rates`.
- `test_transcript_cache_rebuild_switch_delta.py`:
  - `test_haiku_5_5_switch_delta_uses_the_higher_tier`, a 5-minute write of 1,000,000 tokens, not idle, at $1.00 − $0.625 = $0.375.
  - `test_haiku_5_5_idle_cause_switch_delta_reads_the_higher_tier_cache_read_rate`, the same write with the idle cause, at $0.375 − ($1.00 − $0.05) = −$0.575. A cache-read rate read at the lower tier would give −$0.615.
- `test_transcript_cache_rebuild_ttl_rules.py`:
  - `test_haiku_5_5_1h_to_5m_delta_uses_the_higher_tier`, a 1-hour write of 1,000,000 tokens, not idle, at −$0.375.
  - `test_haiku_5_5_idle_cause_1h_to_5m_delta_reads_the_higher_tier_cache_read_rate`, 1,000,000 cache-read tokens with the idle cause, at $0.625 − $0.05 = $0.575. A cache-read rate read at the lower tier would give $0.615.

The tier tests go in the seam file, not in `test_transcript_cost.py`, where earlier model-row tests sit and which is already 4,459 lines. The `_cost_report` case uses the command only as a driver for the rate row, so it sits with the pricing tests, per `.claude/rules/transcript-analysis-tests.md`.

**Modify, docs:**
- `docs/pr-cost.md`:
  - :52 says the labels name the multipliers and prompt-length tier a turn was priced under.
  - A bullet after :56 covers the four long-prompt labels. The model is in `_LONG_PROMPT_TIERS` and the turn's `_context_at_turn`, input plus cache-read plus both cache-write token classes from the record's top-level `usage`, is over its threshold. The whole turn then takes the model's higher base rate, and the multipliers the label's prefix names apply. The bullet has no sub-bullets and makes no overstate or understate claim (row 40).
  - :58 says a re-price applies the rates the label implies, the higher base rate included. It also says the multipliers, and each tiered model's threshold and higher base rate (`_LONG_PROMPT_TIERS`), live only in `pricing.py`.
  - :240 and :392 list long-prompt labels beside fast-mode and US-geo.
  - :415 adds that a long-prompt label records that a model had turns over its prompt-length threshold.
  - :316-317 become an output-equivalence list of functions that all exist in the earlier stamp's commit. Each gives the same result for every standard and fast label the earlier stamp priced: `_price_turn` the same per-class dollars, `_context_at_turn` the same prompt length, `_token_counts` the same counts, and `_cache_write_split` the same split. For `us_geo` and `fast_us_geo` it gives the same dollars within float rounding, because the rate is now multiplied before the tokens are priced, so a rounded micro-dollar can differ by 1. The model-independent multipliers keep their values.
  - The section ending at :322 gains one sentence: adding a model's row leaves the stamp unchanged, so two rows under one stamp can differ by that model's dollars, and the earlier row's `unpriced_tokens` shows it (row 16).
  - :448 adds that a long-prompt variant exposes the summed tokens of every turn on that model whose prompt crossed its threshold, per PR in `model_breakdown` with micro-dollars and per round in `review_rounds`.
- `docs/transcript-analysis.md`:
  - :1140's parenthetical "(priced with the same fast-mode and US-inference-geo multipliers the net carries)" becomes "(priced at each turn's own rates, the same ones the net carries: the fast-mode and US-inference-geo multipliers and, for a model priced by prompt length, the higher base rate a turn takes over that model's threshold)". "Tier" stays reserved for the cache TTL tier in that section (row 47).
  - :280 gains a clause: a target model priced by prompt length is re-priced per turn, at the tier that turn's own prompt selects.
  - :682 gains one sentence: a model the pricing page prices by prompt length (Claude Haiku 5.5, over 100,000 tokens) takes its higher base rate on a turn whose context-at-turn crosses that threshold, and `_LONG_PROMPT_TIERS` holds the threshold and rate.
  - :960 names `_turn_rates` in place of `_model_rates`.
  - The routing-guard "Known gaps" list (:1911-1921) gains two items:
    - The key-off carry figure leaves out later turns on a model priced by prompt length (`claude-haiku-5-5`), and the loop counts as degraded.
    - A capture written before `claude-haiku-5-5` was priced is affected only when it holds an overhead group for that model, which the pattern `"claude-haiku-5-5": {` finds. The item then states:
      - That group was skipped before and is priced now, so its degraded notice no longer prints and a sample's figures can move after upgrading, even where no turn crossed 100,000 tokens.
      - Its turns over 100,000 prompt tokens price at the lower tier, so a PASSED or FAILED verdict can rest on that undercount.
      - Run the listing below in the owner's terminal outside any agent session, as "The captures directory" states. This bullet holds no second statement of the rule's reason.
      - A `grep -l -F` fence lists the captures that hold the pattern. Its text stays byte-identical, because row 39's grep-pattern test and the listing-command test read it.
      - The listing runs once per account store the note's rows name.
      - Only a file modified before the upgrade can hold the undercount.
      - "The captures directory" above gives the delete and re-capture steps.

      The item carries no move-aside procedure and no re-capture caveat (row 40).
  - `docs/transcript-analysis.md:1883`, "The captures directory": the paragraph ships this new sentence first, ahead of its first command-bearing instruction: "Run any command whose text or output carries a capture file name in the owner's terminal outside any agent session, and make no agent Read, Glob or Grep call that names or returns one." It then keeps the paragraph's text:
    - A file is never rebuilt once it exists.
    - To re-capture a branch, delete that branch's file and run capture again, but only when you already know that every session of the branch is inside `cleanupPeriodDays`, because a re-capture reads only the surviving sessions.
    - Leave an earlier run's file in place, because nothing capture prints before the delete shows this.
    - For a file the current run just wrote, the `earliest record` date on its `captured` line is the evidence to read (the "Output" section).

    Constraints on the writer, not doc text:
    - The staged clause "a deleted file is not rebuilt" is dropped (row 44).
    - The `PRICING INTEGRITY` notice's pointer here (routing_guard.py:227-233, pinned by the cited-heading test in `test_transcript_routing_guard_capture.py`) is unchanged, and so is the heading text "The captures directory".
    - The new sentence is the single statement of where commands that name a capture file run. The `hashlib` paragraph's own clause (:1887) and the statements for other commands (:1798, :1864) stay, because each sits beside a command that prints the digest.
    - The Known-gaps item's earlier bullet "Any command that prints a capture file name runs in a terminal outside any agent session" is replaced by the deferring bullet above (row 45).

    This paragraph is the remedy's single home, so the capture Known-gaps item and the CHANGELOG item point there (row 35).
- `docs/cost-ledger.md:26`: the `rates` row says rows computed under different price tables are not comparable. Its added clause says that adding a model's row changes a week's dollars within one `rates` stamp, from the first row recorded after the model was priced. It carries no pointer to `docs/pr-cost.md`.
- `docs/transcript-analysis-architecture.md`, "Tests" section (:800-817): a clause names `tests/test_transcript_pricing_prompt_tiers.py` as the home of `pricing.py`'s prompt-length tier tests, beside `tests/test_transcript_pricing_session_helpers.py`.
- `CHANGELOG.md`: one bullet in the Unreleased section's first Changed list, beside the Fable 5.2 bullet (:101).
  - It says Haiku 5.5 turns no longer count as excluded spend.
  - It says a turn whose context-at-turn (input plus cache-read plus both cache-write tokens, from the record's top-level usage) is over 100,000 tokens prices at $0.50/MTok base input and any other turn at $0.10/MTok, per the pricing page.
  - It names the four new variant labels the pr-cost ledger and routing-guard captures file the over-threshold turns under.
  - It says nothing about the vendor's tiering of a multi-iteration record (row 40).

  A `**Migration:**` sub-list follows, in the shape CHANGELOG.md:98 uses, one item per cohort:
  - A pre-change routing-guard capture holding a `claude-haiku-5-5` overhead group now prices that group, so its degraded notice no longer prints, a sample's figures can move after upgrading, and its turns over 100,000 tokens price at the lower tier. The capture Known-gaps item in `docs/transcript-analysis.md` lists such captures and gives the remedy.
  - On a checkout without this change, `pr-cost-export` drops the model's and the long-prompt labels' `review_rounds` token keys and counts them, and `review-cost-by-size` excludes a PR whose rounds that are not after-merge hold either. A capture holding a long-prompt label reads as invalid there, so compute reports NOT RUN for the whole sample. The file is valid: keep it and update that checkout.
  - Rolling back takes a forward change that keeps the eight labels, never a plain revert.

  The list has no ledger re-record item, no weekly-ledger item and no later-turns item (row 40).

**Read, no edit:**
- `pr_cost.py`, `pr_cost_export.py` and `ledger_rounds.py`: row 20 and Design's "Left as is".
- `subagent_mix.py`: its `--reprice-as` call at :669 passes the turn's own usage, so the tier follows.
- `plan_boundary.py`: row 13.
- `test_transcript_cache_rebuild_ttl_footing.py:327`: its class docstring says the denominator carries the same fast-mode and US-geo multipliers as the net. It stays unedited because the class scopes itself to those two on a model with no prompt-length tier (row 49).
- `render.py`: `_fam` maps the ID to `haiku` by substring, per the exploration report.
- `test_transcript_cost.py`, `test_transcript_review_rounds.py`, `test_transcript_session_pricing.py` and `test_transcript_period_cost.py`: their hand-listed four-label fixtures stay valid subsets, and none compares against `_PRICING_VARIANTS` or calls a deleted function.
- The hook and its test: Out of scope.

Placing the new row above `claude-haiku-4-5-20251001` keeps `claude-opus-5-5` as the pick at test_transcript_routing_guard_compute.py:66-68. `claude-haiku-4-5-20251001` stays the longest ID at test_transcript_pr_cost.py:3454.

**Reuse:**
- `_context_at_turn`, `_token_counts` and `_cache_write_split` in `pricing.py`.
- `_priced` (conftest.py:1070), whose `flat_cache_creation` emits only the flat write field.
- `_priced_with_classes` (`_review_round_corpus_helpers.py:23`), whose prompt length is 4 × base + 13.
- `review_rounds._add_turn_tokens`, as the splits builder.
- `_loop(later=..., variant=...)` (test_transcript_routing_guard_compute.py:101).
- `_cost_args` and `_extract_grand_total` (conftest.py), which `test_transcript_pricing.py` already imports.

Projected diff: about 840 changed lines, an estimate. It was about 720 before code review. The fix round's tests, comments and docs text add about 100, and row 32's export test and row 33's comment add about 16. Row 39's tests and code-review round 3's fixes add more. Row 40's deletions remove prose this branch added, so the net changed-line total falls from what the tree measures before them. Verification step 9 measures the total.

## Verification

**Before dispatch, the session ran** (both on 2026-11-20):

1. A read-only, count-only scan of assistant records. It counted records whose `message.usage.iterations` is a list with two or more entries whose `type` is not `compaction`, of those the records whose `message.model` is `claude-haiku-5-5`, and of those the records whose top-level prompt length, as `_context_at_turn` sums it, is over 100,000. It printed counts only, never record text or paths. The plan records no result. Row 27 records what the top-level-fields policy rests on.
2. `scripts/venv-run.sh python3 claude/.claude/scripts/transcript-analysis.py cost --this-repo` on the unchanged tree, as step 10's positive control when the corpus holds a Haiku 5.5 turn.

**After implementation, the agent runs:**

3. From the worktree root, `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py` passes. A failure in a file this diff leaves untouched is reproduced at the merge-base before it is treated as in scope.
4. `scripts/venv-run.sh ruff check claude/.claude/scripts/` is clean.
5. `scripts/venv-run.sh pytest --collect-only -q <file>` on the seam file and on each edited test file lists every test Critical files names, so step 3 ran them.
6. Each of three mutations to the tier check in `pricing.py`, applied one at a time, fails a named test in `scripts/venv-run.sh pytest claude/.claude/scripts/tests/test_transcript_pricing_prompt_tiers.py`. Revert each before the next, and record the failing tests:
   - `>` changed to `>=` against the threshold fails `test_threshold_is_strictly_greater_than_100k` at 100,000.
   - Prompt length from `input_tokens` alone fails its spread and flat cases at 100,001.
   - Prompt length plus `cache_creation_input_tokens` on top of the nested block fails its spread case at 100,000.

   A fourth mutation removes the `claude-haiku-5-5` row from `_MODEL_BASE_INPUT_RATES`. It runs against `test_transcript_pr_cost_export.py`, and row 32's test must be among its failures.

   Two more mutations run against `test_transcript_routing_guard_capture.py`: `_serialize_capture` writing compact `separators` must fail the grep-pattern test, and `_validate_overhead_tokens` checking a literal four-label tuple must fail the validator test on exactly the four long-prompt labels.

   Before the first mutation, the agent saves `git diff HEAD` for `pricing.py` and `routing_guard.py`. After the last mutation, the same command for each file matches its saved copy, so the docstring edit survives and no mutation remains. A mutation is reverted by restoring the saved copy, never by `git checkout --`.
7. Nine checks:
   - `same fast-mode` under `docs/` and in `claude/.claude/scripts/transcript_analysis/cache_rebuild.py` finds nothing. `at each turn's own rates` under the same scope finds exactly two hits, one in `docs/transcript-analysis.md` and one in `cache_rebuild.py`. Together they show both row 47 sites were reworded. A third `same fast-mode` hit in `claude/.claude/scripts/tests/test_transcript_cache_rebuild_ttl_footing.py:327` is expected and stays (row 49).
   - `prints a capture file name` under `docs/` and `CHANGELOG.md` finds nothing, which shows the Known-gaps item's old bullet is gone.
   - `carries a capture file name` under `docs/` finds exactly one hit, in "The captures directory".
   - Reading the Known-gaps item shows the deferral bullet and no second where-to-run sentence.
   - `_usage_for_token_group|_USAGE_FIELDS_BY_PRICING_VARIANT|_usage_from_variant_tokens` under `claude/`, `docs/` and `CHANGELOG.md` finds nothing.
   - `_VARIANT_USAGE_FIELDS` finds three hits, all in `TestSeededBreakdownSweep` in `test_transcript_pr_cost.py`, and none elsewhere. That class's test-local table of the four lower-tier labels stays valid.
   - `compaction-threshold` under `claude/`, `docs/` and `CHANGELOG.md` finds one hit, in `_pricing_variant`'s docstring.
   - `tiers each sampling iteration|aside copy|aside directory|multi-iteration record|net reads` under `docs/` and `CHANGELOG.md` finds nothing.
   - `modification-time split|first check that every session|a deleted file is not rebuilt` under `docs/` and `CHANGELOG.md` finds nothing, which shows both row 42 edits landed.
8. Two checks:
   - A search for `_model_rates\(` under `claude/.claude/scripts/transcript_analysis/` finds only `pricing.py`, `plan_boundary.py` and `routing_guard.py`.
   - After the doc deletions, additions and replacements land, `pytest` on `test_transcript_routing_guard_capture.py` with `-k "grep or listing_command or accepts_every_pricing"` passes, which shows the doc fence stayed byte-identical and is still the section's only `grep ` fence line.
9. Two measurements:
   - `wc -l` shows `pricing.py`, `test_transcript_pricing.py`, the seam file and `test_transcript_pr_cost_export.py` (930 lines before row 32's test) under 1,000 lines each (row 21).
   - `git diff HEAD --numstat -- . ':(exclude).claude/plans'` over the whole branch gives the changed-line total, added plus deleted, that the PR body states beside the approved "about 840". The same command limited to row 29's four files gives their net growth.

**Before commit, the session runs:**

10. Step 2's command on the changed tree.
    - If step 2's banner named `claude-haiku-5-5`, this run's banner must not.
    - If it did not, `test_cost_report_prices_both_tiers_and_excludes_nothing` is the evidence.

    No figure from either run goes into a commit, PR body or plan file.
11. A fetch of the pricing page confirms the diff's $0.10, $0.50 and 100,000 against its Claude Haiku 5.5 rows, since every rate test asserts the same relayed numbers (G1).

## Out of scope

- An arm for `claude-haiku-5-5` in `nudge-handoff-near-context-cap.sh`'s `resolve_context_window`, and in `_context_window_for_model`'s verified-1M comment. That arm belongs with a re-verification of the hook's whole model list.
  - Both already resolve the model to the vendor's 1M window by default, so only `--check`'s recognized flag differs.
  - The hook installs to every stow consumer.
  - Its source comment's re-verify-by date, 2026-11-03, has passed.
- Re-verifying the other rate-table rows. Every row, the new one included, reaches its re-verify-by date on 2026-12-04 (row 16).
- Per-turn tier weighting in `context_composition._context_composition_turn_rate_scale`. That report weights each turn by its fast and US-geo multiples and ignores per-model rate differences, such as base rates and `_CACHE_READ_MULTIPLIER_OVERRIDES` (context_composition.py:240-251). A tier is a per-turn base-rate change inside one model, which those multiples do not carry. For Haiku 5.5 sessions past 100,000 prompt tokens the ranking therefore undercounts the post-threshold turns. The report is advisory and aggregate-only, and the docstring edit above states the gap. `pricing.py`'s multiplier comment names that function, so a later multiplier condition still reaches it.
- `_loop_carry_rate` pricing later turns without their fast and US-geo multipliers. That predates this change, and a turn count cannot carry them without the capture-shape change M7 sets aside.
- Re-capturing ledger rows recorded before this change. Their Haiku 5.5 turns stay counted as unpriced (row 17). `pr-cost --record --force --pr N`, while every session of the PR is inside `cleanupPeriodDays`, is the existing path (docs/pr-cost.md:268-282).
- Pricing the compaction iteration's tokens. The top-level fields `_token_counts` reads leave them out (row 11), so no model prices them today, and this change adds no field read.
