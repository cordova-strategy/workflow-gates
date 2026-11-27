"""Rate tables, per-turn pricing, token counts, context windows, and
requestId-run deduplication -- no dependency on any cmd_* subcommand, scope
resolution, or redaction.

Module-level flags such as _usage_drift_warned rate-limit stderr diagnostics per
process, and only test fixtures reset them. Per-call drift results come from the
return values of _dedup_session and the _warn_if_* functions.
"""
from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from typing import NamedTuple

from transcript_analysis.corpus import SUBAGENT_SUBDIR

# Labels persist in pr-cost ledger model_breakdown and review_rounds cells; never rename or remove one.
# A new label needs a routing_guard._CAPTURE_REVISION decision and a CHANGELOG Migration line,
# because older checkouts do not tolerate it:
# - the routing-guard capture validator rejects it and the whole sample reports NOT RUN;
# - pr-cost-export drops it from review_rounds;
# - review-cost-by-size cannot price its group.
# A new class also needs a mapping in _token_counts and a rate in _rates_from_base.
_TOKEN_CLASSES: tuple[str, ...] = ("cache_read", "cache_write_5m", "cache_write_1h", "output", "input")

_PRICING_SOURCE_URL = "https://platform.claude.com/docs/en/about-claude/pricing"
_PRICING_FETCH_DATE = date(2026, 9, 5)

# Multipliers vs. a model's base input rate, per the pricing page's stated ratios.
_OUTPUT_RATE_MULTIPLIER = 5
_CACHE_WRITE_5M_MULTIPLIER = 1.25
_CACHE_WRITE_1H_MULTIPLIER = 2
_CACHE_READ_MULTIPLIER = 0.1

# Cache-read multiplier for the model IDs the pricing page states a reduced
# cache-hit rate for, overriding _CACHE_READ_MULTIPLIER -- every other class
# still derives from its own sibling multiplier above via _rates_from_base.
# Claude Mythos 5.1 shares the fable-5-1 exception on the pricing page too
# but has no row in _MODEL_BASE_INPUT_RATES, so it stays unpriced rather
# than gaining a cache-read-only entry here.
_CACHE_READ_MULTIPLIER_OVERRIDES: dict[str, float] = {
    "claude-fable-5-1": 0.025,
    "claude-fable-5-2": 0.025,
    "claude-opus-5-5": 0.05,
}

# Multipliers applied to every dollar class when usage.speed/usage.inference_geo
# report that outcome, per platform.claude.com/docs/en/build-with-claude/fast-mode
# and .../about-claude/pricing's data-residency section.
# A new multiplier condition needs a _VariantTerms field and a _PRICING_VARIANT_TERMS label for every combination,
# or pr-cost ledger cells file its turns under the wrong variant.
# context_composition._context_composition_turn_rate_scale reads speed and inference_geo itself and needs the same condition.
_FAST_MODE_RATE_MULTIPLIER = 2
_INFERENCE_GEO_US_RATE_MULTIPLIER = 1.1


class _VariantTerms(NamedTuple):
    """The three conditions a pricing-variant label names."""

    fast: bool
    us_geo: bool
    long_prompt: bool


# Same persistence rule as _TOKEN_CLASSES.
_PRICING_VARIANT_TERMS: dict[str, _VariantTerms] = {
    "standard": _VariantTerms(fast=False, us_geo=False, long_prompt=False),
    "fast": _VariantTerms(fast=True, us_geo=False, long_prompt=False),
    "us_geo": _VariantTerms(fast=False, us_geo=True, long_prompt=False),
    "fast_us_geo": _VariantTerms(fast=True, us_geo=True, long_prompt=False),
    "long_prompt": _VariantTerms(fast=False, us_geo=False, long_prompt=True),
    "fast_long_prompt": _VariantTerms(fast=True, us_geo=False, long_prompt=True),
    "us_geo_long_prompt": _VariantTerms(fast=False, us_geo=True, long_prompt=True),
    "fast_us_geo_long_prompt": _VariantTerms(fast=True, us_geo=True, long_prompt=True),
}
_PRICING_VARIANTS: tuple[str, ...] = tuple(_PRICING_VARIANT_TERMS)
_VARIANT_BY_TERMS: dict[_VariantTerms, str] = {terms: label for label, terms in _PRICING_VARIANT_TERMS.items()}

_DEFAULT_REVERIFY_BY = _PRICING_FETCH_DATE + timedelta(days=90)

# Base input $/MTok per model ID, keyed on the exact string Claude Code writes
# to message.model. Source: _PRICING_SOURCE_URL, fetched _PRICING_FETCH_DATE.
# Output/cache-write/cache-read rates are derived from this one base rate per
# model by _rates_from_base, so each model needs only its base rate kept current,
# plus a _LONG_PROMPT_TIERS row when the pricing page prices it by prompt length.
# Key rules, each with its consequence:
# - Keys persist verbatim in pr-cost ledger rows and exports, so add vendor-published model IDs only.
# - A key must match pr_cost_ledger._MODEL_BREAKDOWN_KEY_RE, or the ledger cannot read back any row that carries it.
# - Removing or renaming a key leaves every recorded round that holds that model unpriceable
#   (see ledger_rounds.EXCLUDED_UNPRICEABLE_ROUND).
_MODEL_BASE_INPUT_RATES: dict[str, float] = {
    "claude-opus-5-5": 4.00,
    "claude-opus-5": 5.00,
    "claude-opus-4-8": 5.00,
    "claude-sonnet-5-5": 2.00,
    "claude-sonnet-5": 2.00,
    "claude-sonnet-4-6": 3.00,
    # Claude Haiku 5.5's up-to-100,000-token row, fetched 2026-11-20; its higher tier is in _LONG_PROMPT_TIERS.
    "claude-haiku-5-5": 0.10,
    "claude-haiku-4-5-20251001": 1.00,
    # Exact-match only, unlike _context_window_for_model's prefix match on
    # this same string -- a dated-snapshot variant like
    # "claude-sonnet-4-5-20260115" still 200k-buckets correctly but prices as
    # unpriced here.
    "claude-sonnet-4-5": 3.00,
    # claude-fable-5 / -5-1 / -5-2: the vendor's published claude-api model ID
    # for each generation (platform.claude.com/docs/en/models/fable-5/overview,
    # .../fable-5-1/overview, and about-claude/models/overview for 5.2).
    # claude-fable-5-2 is confirmed as the string Claude Code writes to
    # message.model; the 5 and 5-1 strings remain [unverified]. See
    # _reportable_unpriced_model_ids for the loud-on-miss backstop. Pricing
    # this family means its usage appears by name in every published --summary
    # Cost block, not folded into an anonymous unpriced-ID count.
    "claude-fable-5": 10.00,
    "claude-fable-5-1": 10.00,
    # Fable 5.2 base input $8 per the pricing page's Fable 5.2 row.
    "claude-fable-5-2": 8.00,
}


class _LongPromptTier(NamedTuple):
    threshold_tokens: int
    base_input_rate: float


# A turn whose _context_at_turn is over threshold_tokens pays base_input_rate in place of its _MODEL_BASE_INPUT_RATES row.
# Remove a model's _LONG_PROMPT_TIERS row only together with its _MODEL_BASE_INPUT_RATES row. Removing only the tier row:
# - leaves its stored long-prompt groups unpriceable;
# - prices its over-threshold turns at the lower tier with no notice.
# Adding a tier row for a model that already has captured groups leaves those groups under non-long-prompt labels,
# repriced at the lower tier with no notice.
# A new row therefore needs a routing_guard._CAPTURE_REVISION decision
# or the remedy in "Known gaps" of the routing-guard section of docs/transcript-analysis.md.
_LONG_PROMPT_TIERS: dict[str, _LongPromptTier] = {
    # Claude Haiku 5.5's over-100,000-token row, fetched 2026-11-20.
    "claude-haiku-5-5": _LongPromptTier(threshold_tokens=100_000, base_input_rate=0.50),
}

# Re-verify-by date per model ID: fetch-date+90d for every model, since none
# has a vendor-stated rate-change date today.
_MODEL_RATE_EXPIRES: dict[str, date] = dict.fromkeys(_MODEL_BASE_INPUT_RATES, _DEFAULT_REVERIFY_BY)

_CONTEXT_BUCKET_THRESHOLD = 200_000  # inclusive edge of the "≥200k" finding
_CONTEXT_BUCKET_UNDER = "<200k"
_CONTEXT_BUCKET_OVER = ">=200k"

# Context window in tokens per model ID, mirroring
# nudge-handoff-near-context-cap.sh's own CONTEXT_WINDOW case statement
# exactly (same prefix list, same trailing-dash dated-snapshot match), so
# _CONTEXT_DISTRIBUTION_THRESHOLD_PCTS resolves to the window the hook
# multiplies by for the same model ID. A fixed percentage of that window
# still resolves to a different absolute token count on a 200k model than
# on a 1M one — see _CONTEXT_DISTRIBUTION_THRESHOLD_ABS for the sibling
# table expressed directly in absolute tokens instead. Source:
# https://platform.claude.com/docs/en/about-claude/models/overview, fetched
# 2026-08-03; re-verify by 2026-11-03. Verified 200k: Haiku 4.5, Sonnet 4.5,
# Opus 4.5, Opus 4.1. Verified 1M: Fable 5, Mythos 5, Opus 5, Opus
# 4.8/4.7/4.6, Sonnet 5, Sonnet 4.6. An unlisted ID takes the 1M default.
_200K_CONTEXT_MODEL_PREFIXES: tuple[str, ...] = (
    "claude-haiku-4-5",
    "claude-sonnet-4-5",
    "claude-opus-4-5",
    "claude-opus-4-1",
)
_200K_CONTEXT_WINDOW = 200_000
_DEFAULT_CONTEXT_WINDOW = 1_000_000

# Candidate threshold percentages of a model's context window, for
# context-distribution's crossing-count/session-share/dollar-share table.
_CONTEXT_DISTRIBUTION_THRESHOLD_PCTS: tuple[int, ...] = (30, 40, 50, 60)

# Candidate absolute-token thresholds, in the hook's own ESTIMATE unit (input
# + cache_read + cache_creation + output — see _session_peak_context), for
# context-distribution's own crossing-count/session-share/dollar-share table.
# A candidate-threshold sweep like _CONTEXT_DISTRIBUTION_THRESHOLD_PCTS, but
# fixed rather than scaled per model's window. Not the same thing as
# _CONTEXT_BUCKET_THRESHOLD above, which is a fixed *reporting* bucket edge
# consumed by cost/cost-trend, not a candidate-threshold sweep. Spans the
# 200k-model effective floor (80_000, 40% of 200k) through the 1M-model's
# uncapped 40%-of-window value (400_000) and beyond, into the range where
# 1M-model sessions have actually been observed firing. 150_000 is included
# because it is the live 1M-model effective threshold today
# (nudge-handoff-near-context-cap.sh's HANDOFF_NUDGE_ABS_CAP default) — a
# re-run of this report must be able to show the value the hook is actually
# configured to fire at, not just candidates for a future change.
_CONTEXT_DISTRIBUTION_THRESHOLD_ABS: tuple[int, ...] = (
    80_000, 135_000, 150_000, 180_000, 250_000, 400_000, 600_000, 800_000,
)


def _context_window_for_model(model: str) -> int:
    """Context window in tokens for one model ID.

    A prefix requires an exact match or a trailing "-" (dated-snapshot
    suffix), not a bare trailing wildcard, so a longer numeral
    (claude-opus-4-10) can't collide with a shorter one (claude-opus-4-1) by
    string prefix alone — the same collision guard as the bash hook this
    mirrors.
    """
    for prefix in _200K_CONTEXT_MODEL_PREFIXES:
        if model == prefix or model.startswith(prefix + "-"):
            return _200K_CONTEXT_WINDOW
    return _DEFAULT_CONTEXT_WINDOW


def _rates_from_base(model: str, base_input: float) -> dict[str, float]:
    """Return per-MTok dollar rates for one model ID at one base input rate.

    Every class but cache_read derives from the base rate for every model.
    cache_read uses _CACHE_READ_MULTIPLIER_OVERRIDES' per-model value instead
    of _CACHE_READ_MULTIPLIER when the model has one -- the one class the
    pricing page states per-model exceptions for.
    """
    cache_read_multiplier = _CACHE_READ_MULTIPLIER_OVERRIDES.get(model, _CACHE_READ_MULTIPLIER)
    return {
        "input": base_input,
        "output": base_input * _OUTPUT_RATE_MULTIPLIER,
        "cache_write_5m": base_input * _CACHE_WRITE_5M_MULTIPLIER,
        "cache_write_1h": base_input * _CACHE_WRITE_1H_MULTIPLIER,
        "cache_read": base_input * cache_read_multiplier,
    }


def _model_rates(model: str) -> dict[str, float] | None:
    """Return per-MTok dollar rates for one model ID, or None if unpriced or priced by prompt length.

    A model in _LONG_PROMPT_TIERS has no single rate set, so a caller holding a usage uses _turn_rates.
    """
    base = _MODEL_BASE_INPUT_RATES.get(model)
    if base is None or model in _LONG_PROMPT_TIERS:
        return None
    return _rates_from_base(model, base)


def _rates_for_variant(model: str, variant: str) -> dict[str, float] | None:
    """Return per-MTok dollar rates for one model ID under one _PRICING_VARIANTS label.

    None for an unpriced model, an unknown label, or a long-prompt label on a model with no tier.
    """
    terms = _PRICING_VARIANT_TERMS.get(variant)
    base = _MODEL_BASE_INPUT_RATES.get(model)
    if terms is None or base is None:
        return None
    if terms.long_prompt:
        tier = _LONG_PROMPT_TIERS.get(model)
        if tier is None:
            return None
        base = tier.base_input_rate
    multiplier = (_FAST_MODE_RATE_MULTIPLIER if terms.fast else 1) * (
        _INFERENCE_GEO_US_RATE_MULTIPLIER if terms.us_geo else 1
    )
    return {cls: rate * multiplier for cls, rate in _rates_from_base(model, base).items()}


def _turn_rates(model: str, usage: dict) -> dict[str, float] | None:
    """Return the per-MTok dollar rates _price_turn applies to one turn's usage, or None when the turn is unpriced."""
    return _rates_for_variant(model, _pricing_variant(model, usage))


def _cache_read_equivalent_weights() -> dict[str, float]:
    """Each _TOKEN_CLASSES entry's price as a multiple of one cache-read token's price.

    Derived from the base multipliers alone, so one ratio applies to every model:
    _CACHE_READ_MULTIPLIER_OVERRIDES' per-model cache-read exceptions are not reflected.
    """
    class_multipliers = {
        "cache_read": _CACHE_READ_MULTIPLIER,
        "cache_write_5m": _CACHE_WRITE_5M_MULTIPLIER,
        "cache_write_1h": _CACHE_WRITE_1H_MULTIPLIER,
        "output": _OUTPUT_RATE_MULTIPLIER,
        "input": 1,
    }
    return {cls: multiplier / _CACHE_READ_MULTIPLIER for cls, multiplier in class_multipliers.items()}


# The model-ID key _price_turn's unpriced path (cost.py's unpriced_tokens
# dict) uses for a turn whose real model was never recorded, e.g. a
# synthesized/error record with no message.model of its own.
_SYNTHETIC_MODEL_ID = "<synthetic>"


def _reportable_unpriced_model_ids(unpriced_tokens: dict[str, int]) -> list[str]:
    """Every unpriced model-ID key that represents real excluded spend a PR
    reader should be told about, from cost.py's per-model unpriced_tokens
    accumulator.

    Every key qualifies except _SYNTHETIC_MODEL_ID at exactly zero tokens --
    a corpus with no synthetic records at all still seeds that key at 0 in
    some callers, and a $0 entry is not spend excluded from anything. This is
    a forward-looking guard: no observed real corpus has produced a
    nonzero-token synthetic record, so this branch is contract-pinning, not a
    regression reproduction.
    """
    return [
        model_id for model_id, tokens in unpriced_tokens.items()
        if model_id != _SYNTHETIC_MODEL_ID or tokens != 0
    ]


_CACHE_CREATION_SPLIT_KEYS = ("ephemeral_1h_input_tokens", "ephemeral_5m_input_tokens")


def _cache_write_split(usage: dict) -> tuple[int, int]:
    """Return (ephemeral_1h_tokens, ephemeral_5m_tokens) for one usage record.

    Prices the nested cache_creation.{ephemeral_1h,ephemeral_5m}_input_tokens
    block when present. Falls back to the flat cache_creation_input_tokens
    field as 5m-only when the nested block is absent — never counts both,
    since the nested block's own two fields sum exactly to the flat field on
    every real record that carries one.
    """
    nested = usage.get("cache_creation")
    if nested is not None:
        ephemeral_1h_key, ephemeral_5m_key = _CACHE_CREATION_SPLIT_KEYS
        return int(nested.get(ephemeral_1h_key, 0)), int(nested.get(ephemeral_5m_key, 0))
    return 0, int(usage.get("cache_creation_input_tokens", 0))


def _context_at_turn(usage: dict) -> int:
    """Total input-side tokens resident in the context at one assistant turn.

    input_tokens + cache_read_input_tokens + ephemeral_1h + ephemeral_5m. This is
    an absolute per-turn snapshot, not a turn-to-turn delta -- read-scope
    differences consecutive snapshots within one context sequence to derive
    prompt-token growth, which is why the sum lives here rather than inline in
    _price_turn's pricing path.
    """
    eph_1h, eph_5m = _cache_write_split(usage)
    return int(usage.get("input_tokens", 0)) + int(usage.get("cache_read_input_tokens", 0)) + eph_1h + eph_5m


def _context_bucket(context_at_turn: int) -> str:
    return _CONTEXT_BUCKET_OVER if context_at_turn >= _CONTEXT_BUCKET_THRESHOLD else _CONTEXT_BUCKET_UNDER


def dedup_turns_by_request_id(records: Sequence[dict]) -> list[dict]:
    """Collapse each run of same-requestId assistant records into one turn each.

    Claude Code writes one JSONL record per assistant content block (thinking
    / text / tool_use); every record from one API call shares one requestId,
    but a run's own records are not always contiguous -- the harness
    sometimes interleaves a tool_result record between two same-requestId
    assistant records while it executes one multi-tool_use response's tool
    calls one at a time. A contiguous group always merges; a non-contiguous
    group merges only when _non_contiguous_run_usage_matches agrees. A
    merging group's turn is built by _merge_assistant_run and emitted at the
    group's first member's original position; later members are dropped. A
    missing/null/empty requestId never merges with another missing one,
    since real transcripts carry requestId-less synthetic error records that
    must not collapse into each other. Non-assistant records always pass
    through unchanged in their own position. Grouping is on requestId
    equality alone (not also isSidechain/type). Callers must never
    concatenate records from different sessions before calling this:
    requestId is unique per API call, so concatenating one session's main
    transcript with its own subagent transcripts is safe, but mixing in
    another session's records is not -- a non-contiguous group can span the
    entire input, so safety now rests on the usage-corroboration bar
    (_non_contiguous_run_usage_matches) rather than on a contiguity-only
    bound. A merged turn's --since timestamp is its first block's, so a
    non-contiguous group's staleness window can span the entire input too.
    """
    return _dedup_turns_reporting_usage_drift(records)[0]


def _dedup_turns_reporting_usage_drift(records: Sequence[dict]) -> tuple[list[dict], bool]:
    """dedup_turns_by_request_id's turns, plus whether any merged run's input or cache usage drifted."""
    groups: dict[str, list[int]] = {}
    for idx, rec in enumerate(records):
        if rec.get("type") != "assistant":
            continue
        request_id = rec.get("requestId")
        if not request_id:
            continue
        groups.setdefault(request_id, []).append(idx)

    merge_start_idx: dict[int, str] = {}
    skip_idx: set[int] = set()
    for request_id, idxs in groups.items():
        if len(idxs) == 1:
            continue
        is_contiguous = idxs == list(range(idxs[0], idxs[0] + len(idxs)))
        if not is_contiguous:
            run = [records[i] for i in idxs]
            if not _non_contiguous_run_usage_matches(run):
                _log_non_contiguous_merge_decision(request_id, len(idxs), merged=False)
                continue
            _log_non_contiguous_merge_decision(request_id, len(idxs), merged=True)
        merge_start_idx[idxs[0]] = request_id
        skip_idx.update(idxs[1:])

    turns: list[dict] = []
    usage_drift = False
    for idx, rec in enumerate(records):
        if idx in skip_idx:
            continue
        request_id = merge_start_idx.get(idx)
        if request_id is None:
            turns.append(rec)
        else:
            run = [records[i] for i in groups[request_id]]
            # Called before the `or` so a short-circuit never skips the canary's print.
            run_drifted = _warn_if_run_usage_drift(run)
            usage_drift = usage_drift or run_drifted
            turns.append(_merge_assistant_run(run))

    return turns, usage_drift


def _merge_assistant_run(run: list[dict]) -> dict:
    """Merge one requestId run of assistant records into a single synthetic record.

    message.content is the concatenation of every record's own content blocks,
    in original order. message.usage and message.model both come from the last
    record _usage_bearing_records keeps, so a turn is priced under the model of
    the record that supplies its usage. Every other field (uuid, parentUuid,
    timestamp) is taken from the run's first record. timestamp and gitBranch come
    from that record even when _usage_bearing_records skips it, so it decides the
    turn's --since and --branches scope. input_tokens and the
    cache_* classes are identical across the kept records, but output_tokens
    ascends within the run and only reaches its billed value on the last one
    (see _USAGE_DRIFT_INVARIANT_KEYS).
    """
    merged = dict(run[0])
    merged_message = dict(merged.get("message") or {})
    merged_content: list = []
    for rec in run:
        merged_content.extend((rec.get("message") or {}).get("content") or [])
    merged_message["content"] = merged_content
    usage_source_message = _usage_bearing_records(run)[-1].get("message") or {}
    merged_message["usage"] = usage_source_message.get("usage")
    # No model on that record yields "", which subagent-mix skips; no evidence one request's records differ in that.
    merged_message["model"] = usage_source_message.get("model", "")
    merged["message"] = merged_message
    return merged


def _usage_is_all_zero(usage: object) -> bool:
    """Any shape it does not recognize as zero returns False, so the record still reaches the drift canary
    instead of being skipped.
    """
    if not isinstance(usage, dict):
        return False
    nested = usage.get("cache_creation")
    if nested is None:
        nested = {}
    if not isinstance(nested, dict):
        return False
    return all(usage.get(key) == 0 for key in _NON_CONTIGUOUS_MERGE_REQUIRED_MATCH_KEYS) and all(
        nested.get(key, 0) == 0 for key in _CACHE_CREATION_SPLIT_KEYS
    )


def _is_synthetic_zero_usage_record(rec: dict) -> bool:
    message = rec.get("message") or {}
    return message.get("model") == _SYNTHETIC_MODEL_ID and _usage_is_all_zero(message.get("usage"))


def _usage_bearing_records(run: list[dict]) -> list[dict]:
    """The run's records minus its `<synthetic>` all-zero-usage ones; the whole run when every record is one.

    Such a record is observed trailing the record that holds the real usage of a
    refusal-ended request. A skipped record carries no tokens to price. A refusal
    that arrives before any output is not billed in some categories, so recorded
    usage can overstate such a request
    (https://platform.claude.com/docs/en/build-with-claude/refusals-and-fallback#how-refusals-are-billed).
    An all-zero record under any other model is kept, so the drift canary still
    sees it. _merge_assistant_run, _warn_if_run_usage_drift and
    _non_contiguous_run_usage_matches all read usage through this one filter
    so they cannot disagree about which records count.
    """
    bearing = [rec for rec in run if not _is_synthetic_zero_usage_record(rec)]
    return bearing or run


def _cache_miss_reason(message: dict) -> str | None:
    """message.diagnostics.cache_miss_reason.type for one assistant turn's own
    (possibly merged) record, or None when absent/malformed.

    _merge_assistant_run takes every field except message.content,
    message.usage and message.model from a requestId run's first record
    unchanged, so a merged turn's "diagnostics" already reflects the run's own
    opening call with no extra collapsing logic needed here.
    cache_miss_reason is always a dict shaped
    {"type": <str>, "cache_missed_input_tokens": <int>} across a 3,926-record
    survey of real transcripts, with "cache_missed_input_tokens" absent only
    for reason types "previous_message_not_found" and "unavailable" -- no
    bare-string form was observed, so this does not fall back to one. Returns
    None when "diagnostics" is missing or not a dict, or "cache_miss_reason"
    is missing or not a dict, or its "type" is missing or not a string.
    """
    diagnostics = message.get("diagnostics")
    if not isinstance(diagnostics, dict):
        return None
    reason = diagnostics.get("cache_miss_reason")
    if not isinstance(reason, dict):
        return None
    reason_type = reason.get("type")
    return reason_type if isinstance(reason_type, str) else None


# Names the usage keys _warn_if_run_usage_drift treats as required-invariant
# across a requestId run. output_tokens is deliberately excluded -- it ascends
# within a run by design, completing on the last record, so divergence there is
# the documented norm, not drift.
# cache_creation's nested ephemeral_1h/5m_input_tokens need no separate entry:
# both were observed invariant, with a cache_creation block on each observed
# run's first and last record.
_USAGE_DRIFT_INVARIANT_KEYS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")

# Usage keys a non-contiguous same-requestId run must agree on before
# dedup_turns_by_request_id merges it: _USAGE_DRIFT_INVARIANT_KEYS plus
# output_tokens. A genuinely once-billed non-contiguous run carries
# byte-identical usage (including output_tokens) across every record --
# unlike a contiguous run, where output_tokens ascends (12/12 observed
# non-contiguous pairs).
_NON_CONTIGUOUS_MERGE_REQUIRED_MATCH_KEYS = _USAGE_DRIFT_INVARIANT_KEYS + ("output_tokens",)

# Rate-limits _warn_if_run_usage_drift to one line per process, mirroring
# _warn_if_subagent_format_drift's pattern -- a whole-corpus scan should
# surface one signal that the format changed, not one per occurrence.
_usage_drift_warned = False


def _warn_if_run_usage_drift(run: list[dict]) -> bool:
    """Emit one stderr warning per process when a requestId run's records
    disagree on an input/cache usage class that it treats as invariant across
    a run (see _USAGE_DRIFT_INVARIANT_KEYS).

    _merge_assistant_run relies on these classes being identical across every
    record of one API call to price a merged turn correctly regardless of
    which record's value it reads; this is the runtime canary for that
    assumption. Records that _usage_bearing_records skips are not compared.
    Drift prints a warning rather than raising. A truthy non-dict message.usage
    raises AttributeError when it sits on a compared record at or before the
    first drifting one and at least two records are compared; records after
    that are never read.

    Returns whether this run drifted, even after the per-process warning has printed.
    """
    global _usage_drift_warned
    run = _usage_bearing_records(run)
    first_usage = (run[0].get("message") or {}).get("usage") or {}
    for rec in run[1:]:
        rec_usage = (rec.get("message") or {}).get("usage") or {}
        if any(rec_usage.get(key) != first_usage.get(key) for key in _USAGE_DRIFT_INVARIANT_KEYS):
            if not _usage_drift_warned:
                print(
                    f"WARNING: requestId {run[0].get('requestId')!r} has non-identical "
                    "input/cache usage across its own records — _merge_assistant_run's "
                    "invariant-usage assumption may no longer hold (further occurrences "
                    "this run of the CLI are suppressed). The Claude Code transcript "
                    "format may have changed.",
                    file=sys.stderr,
                )
                _usage_drift_warned = True
            return True
    return False


def _non_contiguous_run_usage_matches(run: list[dict]) -> bool:
    """Whether every record in a non-contiguous same-requestId run agrees with
    the first record on all of _NON_CONTIGUOUS_MERGE_REQUIRED_MATCH_KEYS.

    dedup_turns_by_request_id gates a non-contiguous merge on this: bare
    requestId equality alone would also merge two distinct API calls that
    happen to share a requestId (e.g. a hook-denial retry), so this compares
    every member (not just adjacent pairs) against the run's first record.
    A record with no usage dict at all has no evidence to corroborate on, so
    it fails the match rather than vacuously agreeing with another empty one.
    Records that _usage_bearing_records skips are not compared. A skipped
    record carries no tokens to price, while a missing usage dict is an
    unrecognized shape.
    """
    run = _usage_bearing_records(run)
    first_usage = (run[0].get("message") or {}).get("usage") or {}
    if not first_usage:
        return False
    for rec in run[1:]:
        rec_usage = (rec.get("message") or {}).get("usage") or {}
        if not rec_usage or any(
            rec_usage.get(key) != first_usage.get(key) for key in _NON_CONTIGUOUS_MERGE_REQUIRED_MATCH_KEYS
        ):
            return False
    return True


# Rate-limits _log_non_contiguous_merge_decision to one NOTICE per process
# per decision kind ("merged" vs. "rejected"), mirroring _usage_drift_warned
# generalized to two independently-rate-limited kinds.
_non_contiguous_merge_notices_logged: set[str] = set()


def _log_non_contiguous_merge_decision(request_id: str, record_count: int, *, merged: bool) -> None:
    """Emit one stderr NOTICE per process per decision kind when
    dedup_turns_by_request_id resolves a non-contiguous same-requestId run,
    so a later audit can tell whether the usage-corroboration bar
    (_NON_CONTIGUOUS_MERGE_REQUIRED_MATCH_KEYS) is miscalibrated without
    re-deriving the empirical basis for its match keys from scratch.
    """
    kind = "merged" if merged else "rejected"
    if kind in _non_contiguous_merge_notices_logged:
        return
    outcome = (
        "merged into one turn (usage matched on every compared record)"
        if merged
        else "left as separate turns (usage did not match on every compared record)"
    )
    print(
        f"NOTICE: non-contiguous requestId run {kind} -- requestId {request_id!r} has "
        f"{record_count} non-contiguous assistant records, {outcome} (further "
        f"{kind} occurrences this run of the CLI are suppressed).",
        file=sys.stderr,
    )
    _non_contiguous_merge_notices_logged.add(kind)


# Subagent spawn tool_use names, corpus-wide across every command that
# cross-checks spawns against isSidechain turns read.
_SPAWN_TOOL_NAMES = ("Agent", "Task")


def _count_subagent_spawns(records: list[dict]) -> int:
    """Count main-thread subagent spawn tool_uses (Agent/Task) across all records.

    Used corpus-wide (ignoring branch filter) as one side of the format-drift
    cross-check: spawns > 0 with zero isSidechain turns read is the drift signature.
    Note: isSidechain records (from subagent files) are excluded by design — nested
    subagent spawns are not counted here.
    """
    count = 0
    for rec in records:
        if rec.get("type") != "assistant" or bool(rec.get("isSidechain")):
            continue
        for block in ((rec.get("message") or {}).get("content") or []):
            if (
                isinstance(block, dict)
                and block.get("type") == "tool_use"
                and block.get("name") in _SPAWN_TOOL_NAMES
            ):
                count += 1
    return count


class _DedupedSession(NamedTuple):
    """One session's deduplicated turns plus the drift-canary inputs taken from them, before any caller-side filter."""

    turns: list[dict]
    subagent_spawns: int
    sidechain_assistant_turns: int
    usage_drift: bool


def _dedup_session(records: Sequence[dict]) -> _DedupedSession:
    """Deduplicate one session's records and collect its drift-canary inputs, for callers that filter turns afterward."""
    turns, usage_drift = _dedup_turns_reporting_usage_drift(records)
    sidechain_assistant_turns = sum(
        1 for turn in turns if turn.get("type") == "assistant" and bool(turn.get("isSidechain"))
    )
    return _DedupedSession(
        turns=turns,
        subagent_spawns=_count_subagent_spawns(turns),
        sidechain_assistant_turns=sidechain_assistant_turns,
        usage_drift=usage_drift,
    )


# Records that _warn_if_subagent_format_drift's drift signature fired this
# process, mirroring _usage_drift_warned's role for the other drift canary --
# consulted (never set) by _format_drift_detected below. Unlike
# _usage_drift_warned, this flag does not gate the warning print: the
# function is called once per corpus scan (not once per requestId run), so
# no per-process rate-limiting is needed here.
_subagent_format_drift_detected = False


def _warn_if_subagent_format_drift(total_spawns: int, total_sidechain_turns: int) -> bool:
    """Emit a stderr warning when the drift signature is detected.

    Drift signature: spawns recorded in the main thread but zero isSidechain
    assistant turns read after include_subagents merge. Catches both failure
    modes — the subagents/ path relocating (files never read → 0 turns) and a
    field rename (files read but the filter matches 0).

    This is the runtime half of the two-layer guard:
      - Contract test (CI): pins what our code expects from fixtures.
      - This canary (runtime): validates expectation against live on-disk data.

    Returns whether the drift signature matched.
    """
    global _subagent_format_drift_detected
    if total_spawns > 0 and total_sidechain_turns == 0:
        _subagent_format_drift_detected = True
        print(
            "WARNING: subagent spawns detected in main thread but zero isSidechain "
            f"assistant turns were read from '{SUBAGENT_SUBDIR}/' subdirectories. "
            "The Claude Code transcript format may have drifted — check that "
            f"subagent files still live under <session>/{SUBAGENT_SUBDIR}/*.jsonl "
            "and that records still carry 'isSidechain': true.",
            file=sys.stderr,
        )
        return True
    return False


def _format_drift_detected() -> bool:
    """True once either runtime drift canary has fired this process --
    _usage_drift_warned (a requestId run's usage disagreed with itself) or
    _subagent_format_drift_detected (spawns recorded with no isSidechain
    turns read) -- the single flag cost.py's PRICING INTEGRITY banner reads."""
    return _usage_drift_warned or _subagent_format_drift_detected


def _rate_expired(model: str, as_of: date) -> bool:
    """Whether as_of is past a priced model's re-verify-by date."""
    return as_of > _MODEL_RATE_EXPIRES[model]


def _price_turn(model: str, usage: dict) -> tuple[dict[str, float] | None, int, int]:
    """Price one assistant turn's usage at the rates _pricing_variant's label implies.

    Returns (dollars_by_class, context_at_turn, unpriced_tokens):
    - dollars_by_class holds one raw (unrounded) dollar amount per
      _TOKEN_CLASSES entry when the model has a price-table entry, else
      None — callers must check for None rather than treating a zero total
      as "priced at $0".
    - context_at_turn is input_tokens + cache_read_input_tokens + ephemeral_1h
      + ephemeral_5m tokens for this turn, computed regardless of pricing.
    - unpriced_tokens is the turn's total token count (input + output +
      cache_read + ephemeral_1h + ephemeral_5m) when the model is unpriced,
      else 0.
    """
    token_counts = _token_counts(usage)
    context_at_turn = _context_at_turn(usage)
    dollars = _price_token_counts(model, _pricing_variant(model, usage), token_counts)
    if dollars is None:
        return None, context_at_turn, sum(token_counts.values())
    return dollars, context_at_turn, 0


def _pricing_variant(model: str, usage: dict) -> str:
    """The _PRICING_VARIANTS label for the rates _price_turn applies to this usage.

    usage.speed and usage.inference_geo report the API's settled outcome, not an echo of the request,
    so no per-model eligibility list is needed.
    The match is exact: "fast" speed and "us" inference_geo, with no case-folding.
    Neither field is in _USAGE_DRIFT_INVARIANT_KEYS, so a non-run-invariant value on either gets no runtime drift canary,
    a known and accepted gap.
    The long-prompt condition reads the record's top-level fields.
    When usage.iterations is present, the top-level input_tokens sums the non-compaction iterations,
    and whether the cache fields do is unconfirmed. The vendor's compaction page states the input sum:
    https://platform.claude.com/docs/en/build-with-claude/compaction-threshold
    """
    tier = _LONG_PROMPT_TIERS.get(model)
    return _VARIANT_BY_TERMS[
        _VariantTerms(
            fast=usage.get("speed") == "fast",
            us_geo=usage.get("inference_geo") == "us",
            long_prompt=tier is not None and _context_at_turn(usage) > tier.threshold_tokens,
        )
    ]


def _token_counts(usage: dict) -> dict[str, int]:
    """Per-class raw token counts for one turn's usage, keyed like _TOKEN_CLASSES.

    _price_turn prices these same counts, so cost's Tokens column sums the
    same fields its $ column prices.
    """
    eph_1h, eph_5m = _cache_write_split(usage)
    return {
        "input": int(usage.get("input_tokens", 0)),
        "output": int(usage.get("output_tokens", 0)),
        "cache_read": int(usage.get("cache_read_input_tokens", 0)),
        "cache_write_1h": eph_1h,
        "cache_write_5m": eph_5m,
    }


def _price_token_counts(model: str, variant: str, counts_by_class: Mapping[str, int]) -> dict[str, float] | None:
    """Raw dollars per _TOKEN_CLASSES entry for `counts_by_class` under `variant`, a missing class counting as 0.

    None when _rates_for_variant is None or a class label is one this checkout does not know.
    """
    rates = _rates_for_variant(model, variant)
    if rates is None or not set(counts_by_class) <= set(_TOKEN_CLASSES):
        return None
    return {cls: counts_by_class.get(cls, 0) / 1_000_000 * rates[cls] for cls in _TOKEN_CLASSES}


def _reprice_token_splits(token_splits: dict[str, dict[str, dict[str, int]]]) -> float | None:
    """Dollars for a stored `{model: {variant: {class: int}}}` token object at the current rate table, or None when
    any group's model, variant or class is one this checkout cannot price."""
    total_dollars = 0.0
    for model, counts_by_variant in token_splits.items():
        for variant, counts_by_class in counts_by_variant.items():
            dollars_by_class = _price_token_counts(model, variant, counts_by_class)
            if dollars_by_class is None:
                return None
            total_dollars += sum(dollars_by_class.values())
    return total_dollars


def _session_peak_context(main_thread_turns: Sequence[tuple[int, int, int]]) -> tuple[float, int]:
    """Track a session's peak context two ways over the same main-thread turns.

    Each element of main_thread_turns is one turn's
    (context_at_turn, output_tokens, context_window) — context_at_turn from
    _price_turn (input + cache_read + ephemeral_1h + ephemeral_5m).

    Returns (peak_pct, peak_abs_tokens):
    - peak_pct is the session's maximum context_at_turn / context_window.
    - peak_abs_tokens is the session's maximum context_at_turn + output_tokens
      — the hook's own four-field ESTIMATE unit.

    The two are tracked as independent per-turn maxima, never one derived
    from the other (peak_abs_tokens != peak_pct * window): on a session that
    mixes a 200k-window turn with a 1M-window turn, the turn with the
    highest percentage of its own window is not necessarily the turn with
    the highest absolute token count.
    """
    peak_pct = 0.0
    peak_abs_tokens = 0
    for context_at_turn, output_tokens, context_window in main_thread_turns:
        pct = context_at_turn / context_window
        if pct > peak_pct:
            peak_pct = pct
        abs_tokens = context_at_turn + output_tokens
        if abs_tokens > peak_abs_tokens:
            peak_abs_tokens = abs_tokens
    return peak_pct, peak_abs_tokens
