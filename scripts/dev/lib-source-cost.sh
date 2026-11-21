#!/usr/bin/env bash
# lib-source-cost.sh — prices sourcing the shared hook shell library, per cluster and for a tail cut.
#
# Usage: lib-source-cost.sh [--iterations N] [--repetitions N]
# --iterations defaults to 200 and --repetitions to 3, and repetitions must be at least 2.
# Run time is about arms x iterations x repetitions x the cost of one child bash, plus one untimed pass.
# It measures the checkout it runs in, including that checkout's scripts/dev/lib-source-cost-clusters.psv.
#
# Reading a before/after pair taken from two runs that no loop interleaves:
#   Compare full's cost_ms across the two runs, never its figure_ms.
#   Count the change as a saving only when it exceeds the larger of the two full rows' floor_ms.
#   The before run's minus-<cluster> or param-expansion row is the interleaved estimate of the same change, so cite it when the cross-run change misses it by more than that floor.
set -euo pipefail
checkout_root=$(git rev-parse --show-toplevel) || exit 1
# Sourcing the checkout's _config.sh is the bash floor gate: a below-floor bash stops here with its fix text.
# shellcheck source=../../claude/.claude/hooks/_config.sh
. "$checkout_root/claude/.claude/hooks/_config.sh" || exit 1

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=_lib-source-cost-lib.sh
. "$script_dir/_lib-source-cost-lib.sh"
cd "$checkout_root"
# A contributor's BASH_ENV would otherwise be sourced into every child.
unset BASH_ENV

default_iterations=200
default_repetitions=3
iterations=$default_iterations
repetitions=$default_repetitions

print_usage_and_exit() {
  printf 'usage: lib-source-cost.sh [--iterations N] [--repetitions N]  (defaults %d and %d, repetitions at least 2; run time is about arms x iterations x repetitions x one child bash)\n' \
    "$default_iterations" "$default_repetitions" >&2
  exit 2
}

while (( $# > 0 )); do
  case $1 in
    --iterations | --repetitions)
      if (( $# < 2 )); then
        print_usage_and_exit
      fi
      flag=$1
      value=$2
      shift 2
      if [[ $flag == --iterations ]]; then
        lsc_flag_value_ok "$value" 1 || print_usage_and_exit
        iterations=$value
      else
        lsc_flag_value_ok "$value" 2 || print_usage_and_exit
        repetitions=$value
      fi
      ;;
    *) print_usage_and_exit ;;
  esac
done

hooks_dir="$checkout_root/claude/.claude/hooks"
cluster_file="$checkout_root/scripts/dev/lib-source-cost-clusters.psv"
# shellcheck disable=SC2016  # Each child bash expands "$1", not this shell, and double quotes would expand it here.
child_command='. "$1"'

for measured_file in _lib.sh config-keys.psv; do
  if [[ ! -r $hooks_dir/$measured_file ]]; then
    lsc_stop input "$hooks_dir/$measured_file: cannot read" || exit 1
  fi
done

rows=$(lsc_parse_clusters "$cluster_file") || exit 1

scratch_root=$(mktemp -d "${TMPDIR:-/tmp}/lib-source-cost.XXXXXX")
trap 'rm -rf -- "$scratch_root"' EXIT

# One snapshot per run: the spans, the arm copies and the header's blob ids all come from these bytes.
snapshot_dir="$scratch_root/lookup"
lsc_copy_measured_files "$hooks_dir" "$snapshot_dir" || exit 1
# commit= describes the live tree when git describe runs, not the snapshot. The blob ids identify the measured bytes.
commit=$(git describe --always --dirty 2>/dev/null) || commit=none
lib_blob=$(git hash-object -- "$snapshot_dir/_lib.sh")
config_blob=$(git hash-object -- "$snapshot_dir/_config.sh")
spans=$(lsc_resolve_spans "$snapshot_dir" "$rows") || exit 1

mapfile -t arm_labels < <(lsc_arm_labels "$spans")
arm_count=${#arm_labels[@]}
arm_entry_paths=()
for index in "${!arm_labels[@]}"; do
  lsc_build_arm "${arm_labels[index]}" "$spans" "$snapshot_dir" "$scratch_root/$index" || exit 1
  entry_file=$(lsc_arm_entry "${arm_labels[index]}") || exit 1
  arm_entry_paths[index]="$scratch_root/$index/$entry_file"
done

# Pre-flight: every arm sources once, untimed, with exit 0 and no output.
# A top-level call into a deleted function prints on stderr while the source still exits 0.
preflight_stdout="$scratch_root/preflight.stdout"
preflight_stderr="$scratch_root/preflight.stderr"
for index in "${!arm_labels[@]}"; do
  child_status=0
  "$BASH" -c "$child_command" "${arm_labels[index]}" "${arm_entry_paths[index]}" \
    >"$preflight_stdout" 2>"$preflight_stderr" || child_status=$?
  if (( child_status != 0 )) || [[ -s $preflight_stdout || -s $preflight_stderr ]]; then
    lsc_stop pre-flight "arm ${arm_labels[index]}: exit status $child_status, output below" || true
    printf 'child stdout:\n' >&2
    cat -- "$preflight_stdout" >&2
    printf 'child stderr:\n' >&2
    cat -- "$preflight_stderr" >&2
    exit 1
  fi
done

# shellcheck disable=SC2034  # The lib functions read and write it through a nameref, which shellcheck does not follow.
declare -A sample_minimums=()
total_rounds=$((iterations * repetitions))
for (( round = 0; round < total_rounds; round++ )); do
  repetition=$(lsc_round_repetition "$round" "$iterations")
  if (( round % iterations == 0 )); then
    printf 'lib-source-cost: repetition %d of %d\n' "$repetition" "$repetitions" >&2
  fi
  order_text=$(lsc_rotated_indexes "$round" "$arm_count") || exit 1
  read -r -a round_order <<<"$order_text"
  for index in "${round_order[@]}"; do
    child_status=0
    started_micros=${EPOCHREALTIME//[!0-9]/}
    "$BASH" -c "$child_command" "${arm_labels[index]}" "${arm_entry_paths[index]}" >/dev/null 2>&1 || child_status=$?
    finished_micros=${EPOCHREALTIME//[!0-9]/}
    if (( child_status != 0 )); then
      lsc_stop timed "arm ${arm_labels[index]}, repetition $repetition, round $round: exit status $child_status" || exit 1
    fi
    lsc_fold_sample sample_minimums "$index" "$repetition" "$((finished_micros - started_micros))"
  done
done

# The report is built before anything prints, so a stop leaves stdout empty.
span_lines=''
while IFS= read -r span; do
  span_lines+="$(lsc_format_span_line "$span")"$'\n'
done <<<"$spans"
report_arm_lines=$(lsc_report_arm_lines sample_minimums "$repetitions" "${arm_labels[@]}") || exit 1
noise_micros=$(lsc_noise_floor_micros sample_minimums "$repetitions" "${arm_labels[@]}") || exit 1

printf 'header bash=%s system=%s machine=%s commit=%s lib_blob=%s config_blob=%s iterations=%d repetitions=%d\n' \
  "$BASH_VERSION" "$(uname -s)" "$(uname -m)" "$commit" "$lib_blob" "$config_blob" "$iterations" "$repetitions"
printf '%s' "$span_lines"
printf '%s\n' "$report_arm_lines"
printf 'noise-floor ms=%s\n' "$(lsc_format_ms "$noise_micros" unsigned)"
