#!/usr/bin/env bash
# _lib-source-cost-lib.sh — the testable logic of lib-source-cost.sh.
#
# Sourced by lib-source-cost.sh; nothing runs it directly.
#
# Data shapes, all newline-separated text passed as arguments or printed:
#   row   <psv-line-number>|<cluster>|<file>|<first-function>|<last-function>
#   span  <psv-line-number>|<cluster>|<file>|<start>|<end>|<line-count>|<functions>
#   range <start>-<end>
# <file> is _lib.sh or _config.sh. Times are integer microseconds until formatted.
#
# Stops print `lib-source-cost: <stage>: <message>` to stderr and return 1.
# A function that prints data prints nothing on a stop.
#
# lsc_index_definitions, lsc_resolve_span, lsc_partition_lines, lsc_fold_sample
# and lsc_arm_minimums take a caller's array by name through a nameref.
# lsc_noise_floor_micros and lsc_report_arm_lines pass a name on to
# lsc_arm_minimums.
# A caller's array must not share a name with any local or nameref of the functions its name reaches.
# The nameref would read that local instead.
# Bash warns of a circular name reference when the local is the nameref itself.
# A caller's array may use any of these names:
#   sample_minimums, which no lsc_ function declares
#   lib_lines, config_lines, lib_definitions, config_definitions,
#   lib_definition_lines and config_definition_lines, which only
#   lsc_resolve_spans declares (it takes no array by name)

lsc_stop() {
  printf 'lib-source-cost: %s: %s\n' "$1" "$2" >&2
  return 1
}

# lsc_flag_value_ok <value> [<minimum>] — minimum defaults to 1.
# The nine-digit cap keeps the comparison inside bash's integer range.
lsc_flag_value_ok() {
  # Bracket ranges follow the locale's collation order, so the match is pinned to C.
  local LC_ALL=C
  local value=${1-} minimum=${2:-1}
  [[ $value =~ ^[1-9][0-9]{0,8}$ ]] || return 1
  (( value >= minimum ))
}

# ---------------------------------------------------------------------------
# Cluster file
# ---------------------------------------------------------------------------

# lsc_parse_clusters <cluster-file> — prints one row per data line, in file order.
lsc_parse_clusters() {
  # Bracket ranges follow the locale's collation order, so the match is pinned to C.
  local LC_ALL=C
  local cluster_file=$1
  local line line_number=0 pipes cluster file first last
  local label_pattern='^[a-z0-9-]+$' name_pattern='^[A-Za-z_][A-Za-z0-9_]*$'
  local -a parsed_rows=()
  if [[ ! -r $cluster_file ]]; then
    lsc_stop cluster-file "$cluster_file: cannot read"
    return 1
  fi
  while IFS= read -r line || [[ -n $line ]]; do
    line_number=$((line_number + 1))
    if [[ $line == '#'* || $line =~ ^[[:space:]]*$ ]]; then
      continue
    fi
    pipes=${line//[!|]/}
    if (( ${#pipes} != 3 )); then
      lsc_stop cluster-file "$cluster_file:$line_number: expected 4 fields, found $(( ${#pipes} + 1 ))"
      return 1
    fi
    IFS='|' read -r cluster file first last <<<"$line"
    if [[ -z $cluster || -z $file || -z $first || -z $last ]]; then
      lsc_stop cluster-file "$cluster_file:$line_number: empty field"
      return 1
    fi
    if [[ $file != _lib.sh && $file != _config.sh ]]; then
      lsc_stop cluster-file "$cluster_file:$line_number: file must be _lib.sh or _config.sh, found $file"
      return 1
    fi
    if [[ ! $cluster =~ $label_pattern ]]; then
      lsc_stop cluster-file "$cluster_file:$line_number: cluster label must match [a-z0-9-]+"
      return 1
    fi
    if [[ ! $first =~ $name_pattern || ! $last =~ $name_pattern ]]; then
      lsc_stop cluster-file "$cluster_file:$line_number: function names must be shell identifiers"
      return 1
    fi
    parsed_rows+=("$line_number|$cluster|$file|$first|$last")
  done < "$cluster_file"
  if (( ${#parsed_rows[@]} == 0 )); then
    lsc_stop cluster-file "$cluster_file: no rows"
    return 1
  fi
  printf '%s\n' "${parsed_rows[@]}"
}

# ---------------------------------------------------------------------------
# Start lines and spans
# ---------------------------------------------------------------------------

# lsc_check_syntax <dir> — dir holds _lib.sh and _config.sh.
# A source with a syntax error defines only the functions above the error and
# shows no cause, so this runs before the lookup.
lsc_check_syntax() {
  local source_dir=$1 file message
  for file in _lib.sh _config.sh; do
    if ! message=$("$BASH" -n "$source_dir/$file" 2>&1 </dev/null); then
      lsc_stop syntax "$file: $message"
      return 1
    fi
  done
}

# lsc_lookup_starts <dir> <rows> — prints `<name> <start-line> <file>` once per
# distinct anchor, in first-appearance order. dir holds _lib.sh, which sources
# _config.sh beside it, so one child reports both files' anchors.
# Source health is judged by the pre-flight, not here.
lsc_lookup_starts() {
  # Bracket ranges follow the locale's collation order, so the match is pinned to C.
  local LC_ALL=C
  local source_dir=$1 rows=$2
  local line_number file first last name start path reported lookup_script
  local -a anchors=()
  local -A is_anchor=() start_of=() file_of=()
  while IFS='|' read -r line_number _ _ first last; do
    [[ -n $line_number ]] || continue
    for name in "$first" "$last"; do
      if [[ -z ${is_anchor[$name]+set} ]]; then
        is_anchor[$name]=1
        anchors+=("$name")
      fi
    done
  done <<<"$rows"
  lookup_script=$(cat <<'LOOKUP_EOF'
shopt -s extdebug
. "$1" >/dev/null 2>&1 || true
shift
for name; do declare -F "$name" || true; done
LOOKUP_EOF
  )
  reported=$(LC_ALL=C "$BASH" -c "$lookup_script" lookup "$source_dir/_lib.sh" "${anchors[@]}" </dev/null) || true
  while read -r name start path; do
    if [[ $name =~ ^[A-Za-z_][A-Za-z0-9_]*$ && -n ${is_anchor[$name]+set} && $start =~ ^[0-9]+$ ]]; then
      start_of[$name]=$start
      file_of[$name]=${path##*/}
    fi
  done <<<"$reported"
  while IFS='|' read -r line_number _ file first last; do
    [[ -n $line_number ]] || continue
    for name in "$first" "$last"; do
      if [[ -z ${start_of[$name]+set} ]]; then
        lsc_stop lookup "PSV line $line_number: $name is not defined after sourcing _lib.sh"
        return 1
      fi
      if [[ ${file_of[$name]} != "$file" ]]; then
        lsc_stop lookup "PSV line $line_number: $name is defined in ${file_of[$name]}, not $file"
        return 1
      fi
    done
  done <<<"$rows"
  for name in "${anchors[@]}"; do
    printf '%s %s %s\n' "$name" "${start_of[$name]}" "${file_of[$name]}"
  done
}

# lsc_index_definitions <lines-array-name> <by-name-array-name> <all-lines-array-name>
# Fills the associative array with each name's definition line numbers,
# space-separated, and the indexed array with every definition line number in
# file order. A definition line reads exactly `<name>() {` or `<name>() (`.
# shellcheck disable=SC2004  # shellcheck reads the nameref as an indexed array; an associative subscript needs its $.
lsc_index_definitions() {
  # Bracket ranges follow the locale's collation order, so the match is pinned to C.
  local LC_ALL=C
  local -n index_source_lines=$1
  local -n index_by_name=$2
  local -n index_all_lines=$3
  local definition_pattern='^([A-Za-z_][A-Za-z0-9_]*)\(\) [{(]$'
  local index defined_name existing
  index_by_name=()
  index_all_lines=()
  for index in "${!index_source_lines[@]}"; do
    if [[ ${index_source_lines[index]} =~ $definition_pattern ]]; then
      defined_name=${BASH_REMATCH[1]}
      existing=${index_by_name[$defined_name]-}
      index_by_name[$defined_name]="${existing:+$existing }$((index + 1))"
      index_all_lines+=("$((index + 1))")
    fi
  done
}

# lsc_resolve_span <psv-line-number> <lines-array-name> <first> <first-start> <last> <last-start>
#   [<by-name-array-name> <all-lines-array-name>]
# Prints `<start>|<end>|<line-count>|<functions>`. The lines array holds the
# file's lines, one element per line. A span ends at the last function's first
# later line reading exactly `}` or `)` to match its opener. The last two
# arguments are the arrays lsc_index_definitions filled for that file, so a
# caller resolving many rows indexes the file once. Without both, the file is
# indexed for this call. Passing only one is a stop.
# shellcheck disable=SC2034  # The own_ arrays are read through a nameref when the caller passes no index.
lsc_resolve_span() {
  local line_number=$1 first=$3 first_start=$4 last=$5 last_start=$6
  local -n span_file_lines=$2
  local by_name_array=${7-} all_lines_array=${8-}
  local -A own_definitions_by_name=()
  local -a own_definition_lines=()
  local index text first_line last_line closer_line closer opener count=0 line
  local -a first_definitions=() last_definitions=()
  if [[ -z $by_name_array && -n $all_lines_array ]] || [[ -n $by_name_array && -z $all_lines_array ]]; then
    lsc_stop span "PSV line $line_number: pass both index arrays or neither"
    return 1
  fi
  if [[ -z $by_name_array ]]; then
    lsc_index_definitions "$2" own_definitions_by_name own_definition_lines
    by_name_array=own_definitions_by_name
    all_lines_array=own_definition_lines
  fi
  local -n definitions_by_name=$by_name_array
  local -n all_definitions=$all_lines_array
  read -r -a first_definitions <<<"${definitions_by_name[$first]-}"
  read -r -a last_definitions <<<"${definitions_by_name[$last]-}"
  if (( ${#first_definitions[@]} != 1 )); then
    lsc_stop span "PSV line $line_number: $first has ${#first_definitions[@]} definition lines, expected 1"
    return 1
  fi
  if (( ${#last_definitions[@]} != 1 )); then
    lsc_stop span "PSV line $line_number: $last has ${#last_definitions[@]} definition lines, expected 1"
    return 1
  fi
  first_line=${first_definitions[0]}
  last_line=${last_definitions[0]}
  if (( first_line != first_start )); then
    lsc_stop span "PSV line $line_number: $first is defined at line $first_line but bash reports line $first_start"
    return 1
  fi
  if (( last_line != last_start )); then
    lsc_stop span "PSV line $line_number: $last is defined at line $last_line but bash reports line $last_start"
    return 1
  fi
  if (( last_line < first_line )); then
    lsc_stop span "PSV line $line_number: $last is defined before $first"
    return 1
  fi
  opener=${span_file_lines[last_line - 1]: -1}
  closer='}'
  if [[ $opener == '(' ]]; then
    closer=')'
  fi
  closer_line=0
  for (( index = last_line; index < ${#span_file_lines[@]}; index++ )); do
    if [[ ${span_file_lines[index]} == "$closer" ]]; then
      closer_line=$((index + 1))
      break
    fi
  done
  if (( closer_line == 0 )); then
    lsc_stop span "PSV line $line_number: no closer after $last at line $last_line"
    return 1
  fi
  for line in "${all_definitions[@]}"; do
    if (( line > last_line && line < closer_line )); then
      text=${span_file_lines[line - 1]}
      lsc_stop span "PSV line $line_number: ${text%%\(*} is defined at line $line between $last and its closer at line $closer_line"
      return 1
    fi
    if (( line >= first_line && line <= closer_line )); then
      count=$((count + 1))
    fi
  done
  printf '%s|%s|%s|%s\n' "$first_line" "$closer_line" "$((closer_line - first_line + 1))" "$count"
}

# lsc_check_span_overlap <spans> — covers overlap, nesting and a repeated row.
lsc_check_span_overlap() {
  local spans=$1
  local line_number file start end i j
  local -a numbers=() files=() starts=() ends=()
  while IFS='|' read -r line_number _ file start end _; do
    [[ -n $line_number ]] || continue
    numbers+=("$line_number")
    files+=("$file")
    starts+=("$start")
    ends+=("$end")
  done <<<"$spans"
  for (( i = 0; i < ${#numbers[@]}; i++ )); do
    for (( j = i + 1; j < ${#numbers[@]}; j++ )); do
      if [[ ${files[i]} == "${files[j]}" ]] && (( starts[i] <= ends[j] && starts[j] <= ends[i] )); then
        lsc_stop span "PSV lines ${numbers[i]} and ${numbers[j]} share lines in ${files[i]} (${starts[i]}-${ends[i]} and ${starts[j]}-${ends[j]})"
        return 1
      fi
    done
  done
}

# lsc_resolve_spans <dir> <rows> — prints one span per row, in row order.
# Stages run in order: syntax, lookup, then span.
# shellcheck disable=SC2034  # The line and definition arrays are read through namerefs in lsc_resolve_span.
lsc_resolve_spans() {
  local source_dir=$1 rows=$2
  local starts name start line_number cluster file first last resolved spans=''
  local -A start_of=() lib_definitions=() config_definitions=()
  local -a lib_lines=() config_lines=() lib_definition_lines=() config_definition_lines=()
  lsc_check_syntax "$source_dir" || return 1
  starts=$(lsc_lookup_starts "$source_dir" "$rows") || return 1
  while read -r name start _; do
    start_of[$name]=$start
  done <<<"$starts"
  mapfile -t lib_lines < "$source_dir/_lib.sh" || return 1
  mapfile -t config_lines < "$source_dir/_config.sh" || return 1
  lsc_index_definitions lib_lines lib_definitions lib_definition_lines
  lsc_index_definitions config_lines config_definitions config_definition_lines
  while IFS='|' read -r line_number cluster file first last; do
    [[ -n $line_number ]] || continue
    if [[ $file == _lib.sh ]]; then
      resolved=$(lsc_resolve_span "$line_number" lib_lines "$first" "${start_of[$first]}" "$last" "${start_of[$last]}" \
        lib_definitions lib_definition_lines) || return 1
    else
      resolved=$(lsc_resolve_span "$line_number" config_lines "$first" "${start_of[$first]}" "$last" "${start_of[$last]}" \
        config_definitions config_definition_lines) || return 1
    fi
    spans+="$line_number|$cluster|$file|$resolved"$'\n'
  done <<<"$rows"
  spans=${spans%$'\n'}
  lsc_check_span_overlap "$spans" || return 1
  printf '%s\n' "$spans"
}

# ---------------------------------------------------------------------------
# Arms
# ---------------------------------------------------------------------------

# lsc_arm_labels <spans> — a minus- arm appears once per cluster, in order of its first row.
lsc_arm_labels() {
  local spans=$1
  local cluster
  local -A seen=()
  printf '%s\n' full
  while IFS='|' read -r _ cluster _; do
    [[ -n $cluster ]] || continue
    if [[ -z ${seen[$cluster]+set} ]]; then
      seen[$cluster]=1
      printf 'minus-%s\n' "$cluster"
    fi
  done <<<"$spans"
  printf '%s\n' total-deletion tail-cut control baseline dirname-fork param-expansion
}

# lsc_arm_entry <label> — the file name in the arm's directory that its child sources.
lsc_arm_entry() {
  case $1 in
    baseline | dirname-fork | param-expansion) printf '%s\n' entry.sh ;;
    full | control | total-deletion | tail-cut | minus-*) printf '%s\n' _lib.sh ;;
    *)
      lsc_stop arm "unknown arm label: $1"
      return 1
      ;;
  esac
}

# lsc_arm_reference <label> — prints an empty line for baseline, which has no reference.
lsc_arm_reference() {
  case $1 in
    baseline) printf '\n' ;;
    full | dirname-fork) printf '%s\n' baseline ;;
    param-expansion) printf '%s\n' dirname-fork ;;
    control | total-deletion | tail-cut | minus-*) printf '%s\n' full ;;
    *)
      lsc_stop arm "unknown arm label: $1"
      return 1
      ;;
  esac
}

lsc_arm_kind() {
  case $1 in
    baseline) printf '%s\n' none ;;
    full | dirname-fork) printf '%s\n' cost ;;
    control | total-deletion | tail-cut | param-expansion | minus-*) printf '%s\n' saving ;;
    *)
      lsc_stop arm "unknown arm label: $1"
      return 1
      ;;
  esac
}

# lsc_arm_ranges <spans> <file> [<cluster>] — prints each matching span as a
# range, in span order. Without a cluster, every cluster matches.
lsc_arm_ranges() {
  local spans=$1 wanted_file=$2 wanted_cluster=${3-}
  local cluster file start end
  while IFS='|' read -r _ cluster file start end _; do
    [[ -n $cluster ]] || continue
    if [[ $file == "$wanted_file" && ( -z $wanted_cluster || $cluster == "$wanted_cluster" ) ]]; then
      printf '%s-%s\n' "$start" "$end"
    fi
  done <<<"$spans"
}

# lsc_copy_measured_files <source-dir> <dest-dir>
# A caller that runs this under `|| exit` has -e off in here, so the returns are explicit.
lsc_copy_measured_files() {
  local source_dir=$1 dest_dir=$2 file
  mkdir -p -- "$dest_dir" || return 1
  for file in _lib.sh _config.sh config-keys.psv; do
    cp -- "$source_dir/$file" "$dest_dir/$file" || return 1
  done
}

# lsc_write_lines <dest> [<line>...] — one line per argument, and an empty file for none.
# printf '%s\n' with no arguments would write one newline.
lsc_write_lines() {
  local dest=$1
  shift
  if (( $# > 0 )); then
    printf '%s\n' "$@" > "$dest"
  else
    : > "$dest"
  fi
}

# lsc_partition_lines <file> <kept-array-name> <moved-array-name> <range>...
# Fills the first array with the lines outside every range and the second with
# the lines inside, each in file order.
lsc_partition_lines() {
  # Bracket ranges follow the locale's collation order, so the match is pinned to C.
  local LC_ALL=C
  local source_file=$1
  local -n kept_lines=$2
  local -n moved_lines=$3
  shift 3
  local range start end index
  local -a all_lines=() in_range=()
  mapfile -t all_lines < "$source_file" || return 1
  for range in "$@"; do
    if [[ ! $range =~ ^[1-9][0-9]*-[0-9]+$ ]]; then
      lsc_stop arm "bad range: $range"
      return 1
    fi
    start=${range%-*}
    end=${range#*-}
    for (( index = start; index <= end; index++ )); do
      in_range[index]=1
    done
  done
  kept_lines=()
  moved_lines=()
  for index in "${!all_lines[@]}"; do
    if [[ -n ${in_range[index + 1]+set} ]]; then
      moved_lines+=("${all_lines[index]}")
    else
      kept_lines+=("${all_lines[index]}")
    fi
  done
}

# lsc_delete_spans <source-file> <dest-file> <range>...
# Rewrites the file through a line array, with no sed -i, head or tail form:
# their flags differ between GNU and BSD.
lsc_delete_spans() {
  local source_file=$1 dest_file=$2
  shift 2
  local -a kept=() moved=()
  lsc_partition_lines "$source_file" kept moved "$@" || return 1
  lsc_write_lines "$dest_file" "${kept[@]}"
}

# lsc_tail_cut_spans <source-file> <dest-file> <range>...
# The ranges' lines move, in file order, behind a bare top-level `return 0`.
lsc_tail_cut_spans() {
  local source_file=$1 dest_file=$2
  shift 2
  local -a kept=() moved=()
  lsc_partition_lines "$source_file" kept moved "$@" || return 1
  lsc_write_lines "$dest_file" "${kept[@]}" 'return 0' "${moved[@]}"
}

# lsc_write_light_arm <label> <dest-file>
lsc_write_light_arm() {
  local label=$1 dest_file=$2
  case $label in
    baseline)
      : > "$dest_file"
      ;;
    dirname-fork)
      cat > "$dest_file" <<'ARM_EOF'
arm_directory="$(dirname "${BASH_SOURCE[0]}")"
ARM_EOF
      ;;
    param-expansion)
      cat > "$dest_file" <<'ARM_EOF'
arm_directory="${BASH_SOURCE[0]%/*}"
ARM_EOF
      ;;
    *)
      lsc_stop arm "not a light arm: $label"
      return 1
      ;;
  esac
}

# lsc_build_arm <label> <spans> <source-dir> <arm-dir>
# Fills arm-dir for the label: a light arm's entry file, or copies of the three
# measured files with the arm's edit applied to each file that holds its spans.
lsc_build_arm() {
  local label=$1 spans=$2 source_dir=$3 arm_dir=$4
  local file edit cluster='' edited_files=0
  local -a ranges=()
  mkdir -p -- "$arm_dir" || return 1
  case $label in
    baseline | dirname-fork | param-expansion)
      lsc_write_light_arm "$label" "$arm_dir/entry.sh"
      return
      ;;
    full | control)
      lsc_copy_measured_files "$source_dir" "$arm_dir"
      return
      ;;
    minus-*)
      edit=delete
      cluster=${label#minus-}
      ;;
    total-deletion) edit=delete ;;
    tail-cut) edit=tail-cut ;;
    *)
      lsc_stop arm "unknown arm label: $label"
      return 1
      ;;
  esac
  lsc_copy_measured_files "$source_dir" "$arm_dir" || return 1
  for file in _lib.sh _config.sh; do
    mapfile -t ranges < <(lsc_arm_ranges "$spans" "$file" "$cluster")
    if (( ${#ranges[@]} == 0 )); then
      continue
    fi
    edited_files=$((edited_files + 1))
    if [[ $edit == delete ]]; then
      lsc_delete_spans "$source_dir/$file" "$arm_dir/$file" "${ranges[@]}" || return 1
    else
      lsc_tail_cut_spans "$source_dir/$file" "$arm_dir/$file" "${ranges[@]}" || return 1
    fi
  done
  if (( edited_files == 0 )); then
    lsc_stop arm "$label removes no spans"
    return 1
  fi
}

# ---------------------------------------------------------------------------
# Rounds and the per-repetition minimum
# ---------------------------------------------------------------------------

# lsc_rotated_indexes <round> <arm-count> — prints the order the arms run in <round>,
# space-separated, starting at index <round> mod <arm-count> and wrapping.
lsc_rotated_indexes() {
  local round=$1 arm_count=$2 offset index
  local -a order=()
  if (( arm_count < 1 )); then
    lsc_stop rotation "arm count must be at least 1"
    return 1
  fi
  offset=$((round % arm_count))
  for (( index = 0; index < arm_count; index++ )); do
    order+=("$(( (offset + index) % arm_count ))")
  done
  printf '%s\n' "${order[*]}"
}

# lsc_round_repetition <round> <iterations> — rounds count from 0, repetitions from 1.
lsc_round_repetition() {
  printf '%s\n' "$(( $1 / $2 + 1 ))"
}

# lsc_fold_sample <assoc-array-name> <arm-index> <repetition> <micros>
# Keeps the smallest sample per arm and repetition in the caller's associative array.
# shellcheck disable=SC2004  # shellcheck reads the nameref as an indexed array; an associative subscript needs its $.
lsc_fold_sample() {
  local -n fold_target=$1
  local key="$2,$3" micros=$4 current
  if [[ -z ${fold_target[$key]+set} ]]; then
    fold_target[$key]=$micros
    return 0
  fi
  current=${fold_target[$key]}
  if (( micros < current )); then
    fold_target[$key]=$micros
  fi
}

# lsc_arm_minimums <assoc-array-name> <arm-index> <repetitions> — prints the
# per-repetition minimums, space-separated, for repetitions 1 to N.
lsc_arm_minimums() {
  local -n minimums_source=$1
  local arm_index=$2 repetitions=$3 repetition
  local -a collected_minimums=()
  for (( repetition = 1; repetition <= repetitions; repetition++ )); do
    if [[ -z ${minimums_source[$arm_index,$repetition]+set} ]]; then
      lsc_stop fold "arm $arm_index has no sample in repetition $repetition"
      return 1
    fi
    collected_minimums+=("${minimums_source[$arm_index,$repetition]}")
  done
  printf '%s\n' "${collected_minimums[*]}"
}

# ---------------------------------------------------------------------------
# Arithmetic and formatting
# ---------------------------------------------------------------------------

lsc_figure() {
  local smallest=$1 value
  for value in "$@"; do
    if (( value < smallest )); then
      smallest=$value
    fi
  done
  printf '%s\n' "$smallest"
}

lsc_spread() {
  local smallest=$1 largest=$1 value
  for value in "$@"; do
    if (( value < smallest )); then
      smallest=$value
    fi
    if (( value > largest )); then
      largest=$value
    fi
  done
  printf '%s\n' "$((largest - smallest))"
}

# lsc_delta_micros <cost|saving> <arm-figure> <reference-figure>
lsc_delta_micros() {
  case $1 in
    cost) printf '%s\n' "$(( $2 - $3 ))" ;;
    saving) printf '%s\n' "$(( $3 - $2 ))" ;;
    *)
      lsc_stop delta "kind must be cost or saving, found $1"
      return 1
      ;;
  esac
}

# lsc_applied_floor <noise> <arm-label> <arm-spread> <reference-label> <reference-spread>
# Prints `<micros> <label>`: the largest of the three spreads and the label that
# owns it, taking baseline, then the arm, then its reference on a tie.
lsc_applied_floor() {
  local floor=$1 from=baseline
  if (( $3 > floor )); then
    floor=$3
    from=$2
  fi
  if (( $5 > floor )); then
    floor=$5
    from=$4
  fi
  printf '%s %s\n' "$floor" "$from"
}

# lsc_verdict <delta-micros> <floor-micros>
lsc_verdict() {
  local delta=$1 floor=$2
  if (( delta < 0 )); then
    delta=$((-delta))
  fi
  if (( delta < floor )); then
    printf '%s\n' below
  else
    printf '%s\n' above
  fi
}

# lsc_format_ms <micros> <signed|unsigned>
lsc_format_ms() {
  local micros=$1 mode=$2 sign=''
  if (( micros < 0 )); then
    sign='-'
    micros=$((-micros))
  elif [[ $mode == signed ]]; then
    sign='+'
  elif [[ $mode != unsigned ]]; then
    lsc_stop format "mode must be signed or unsigned, found $mode"
    return 1
  fi
  printf '%s%d.%03d\n' "$sign" "$((micros / 1000))" "$((micros % 1000))"
}

lsc_format_span_line() {
  local cluster file start end line_count functions
  IFS='|' read -r _ cluster file start end line_count functions <<<"$1"
  printf 'span cluster=%s file=%s lines=%s-%s line_count=%s functions=%s\n' \
    "$cluster" "$file" "$start" "$end" "$line_count" "$functions"
}

# lsc_format_arm_line <label> <mins-micros-csv> <figure> <spread>
#   [<reference> <cost|saving> <delta> <floor> <floor-from> <verdict>]
# All times are microseconds. The last six arguments are present for every arm but baseline.
lsc_format_arm_line() {
  local label=$1 mins_csv=$2 figure=$3 spread=$4 minimum mins_ms=''
  local -a minimums=()
  if (( $# != 4 && $# != 10 )); then
    lsc_stop format "arm line takes 4 or 10 arguments, found $#"
    return 1
  fi
  IFS=, read -r -a minimums <<<"$mins_csv"
  for minimum in "${minimums[@]}"; do
    mins_ms+="${mins_ms:+,}$(lsc_format_ms "$minimum" unsigned)"
  done
  printf 'arm label=%s mins_ms=%s figure_ms=%s spread_ms=%s' \
    "$label" "$mins_ms" "$(lsc_format_ms "$figure" unsigned)" "$(lsc_format_ms "$spread" unsigned)"
  if (( $# == 10 )); then
    printf ' ref=%s %s_ms=%s floor_ms=%s floor_from=%s verdict=%s' \
      "$5" "$6" "$(lsc_format_ms "$7" signed)" "$(lsc_format_ms "$8" unsigned)" "$9" "${10}"
  fi
  printf '\n'
}

lsc_label_index() {
  local wanted=$1 index
  shift
  local -a labels=("$@")
  for index in "${!labels[@]}"; do
    if [[ ${labels[index]} == "$wanted" ]]; then
      printf '%s\n' "$index"
      return 0
    fi
  done
  lsc_stop report "no arm labeled $wanted"
  return 1
}

# lsc_noise_floor_micros <assoc-array-name> <repetitions> <label>... — baseline's spread.
lsc_noise_floor_micros() {
  local folded_name=$1 repetitions=$2 baseline_index minimums_text
  local -a baseline_minimums=()
  shift 2
  baseline_index=$(lsc_label_index baseline "$@") || return 1
  minimums_text=$(lsc_arm_minimums "$folded_name" "$baseline_index" "$repetitions") || return 1
  read -r -a baseline_minimums <<<"$minimums_text"
  lsc_spread "${baseline_minimums[@]}"
}

# lsc_report_arm_lines <assoc-array-name> <repetitions> <label>...
# Prints one `arm` line per label, in list order, from the folded minimums.
# A label's position in the list is its arm index.
lsc_report_arm_lines() {
  local folded_name=$1 repetitions=$2
  shift 2
  local -a labels=("$@")
  local -A mins_of=() figure_of=() spread_of=()
  local index label reference kind delta applied floor floor_from noise minimums_text arm_line verdict
  local -a label_minimums=() arm_lines=()
  for index in "${!labels[@]}"; do
    label=${labels[index]}
    minimums_text=$(lsc_arm_minimums "$folded_name" "$index" "$repetitions") || return 1
    read -r -a label_minimums <<<"$minimums_text"
    mins_of[$label]=$minimums_text
    figure_of[$label]=$(lsc_figure "${label_minimums[@]}")
    spread_of[$label]=$(lsc_spread "${label_minimums[@]}")
  done
  if [[ -z ${spread_of[baseline]+set} ]]; then
    lsc_stop report "no arm labeled baseline"
    return 1
  fi
  noise=${spread_of[baseline]}
  for label in "${labels[@]}"; do
    kind=$(lsc_arm_kind "$label") || return 1
    if [[ $kind == none ]]; then
      arm_line=$(lsc_format_arm_line "$label" "${mins_of[$label]// /,}" "${figure_of[$label]}" "${spread_of[$label]}") || return 1
      arm_lines+=("$arm_line")
      continue
    fi
    reference=$(lsc_arm_reference "$label") || return 1
    if [[ -z ${figure_of[$reference]+set} ]]; then
      lsc_stop report "no arm labeled $reference, the reference of $label"
      return 1
    fi
    delta=$(lsc_delta_micros "$kind" "${figure_of[$label]}" "${figure_of[$reference]}") || return 1
    applied=$(lsc_applied_floor "$noise" "$label" "${spread_of[$label]}" "$reference" "${spread_of[$reference]}")
    read -r floor floor_from <<<"$applied"
    verdict=$(lsc_verdict "$delta" "$floor")
    arm_line=$(lsc_format_arm_line "$label" "${mins_of[$label]// /,}" "${figure_of[$label]}" "${spread_of[$label]}" \
      "$reference" "$kind" "$delta" "$floor" "$floor_from" "$verdict") || return 1
    arm_lines+=("$arm_line")
  done
  printf '%s\n' "${arm_lines[@]}"
}
