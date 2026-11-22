#!/usr/bin/env bash
# Canonical source for ~/.claude/scripts/relocate-claude-config.sh (stowed)
# and for ~/.local/bin/relocate-claude-config (installed as a REAL FILE COPY
# by install.sh, not a stow-managed symlink like every other ~/.local/bin/*
# wrapper — this script's whole purpose is to keep working when the exact
# symlink chain it repairs has already failed, and a stow-managed wrapper
# would inherit that same failure).
#
# The single supported command to relocate this claude-config checkout, or
# to repair ~/.claude after it was already moved outside any Claude Code
# session — unstows, moves, and re-stows so every symlink under ~/.claude/
# and ~/.local/bin/ keeps resolving. Deliberately does NOT source _lib.sh or
# otherwise depend on ~/.claude/ being intact: repairing that dependency is
# exactly this script's job. Both modes also re-point links in each config dir
# listed in ~/.claude/transcript-config-dirs. See README "Repo relocation" and
# docs/scripts.md.
#
# Threat model: <new-path> is semi-trusted, not only a deliberate human
# argument — deny-repo-relocation.sh's own denial message names this script
# as the sanctioned escape hatch, so a prompt-injected agent could be
# steered into invoking it with an attacker-influenced destination.
# Destination validation (validate_destination_common below) is where this
# script's actual security investment goes: canonicalize <new-path>'s
# parent, refuse an already-existing or dangling-symlink destination,
# refuse a destination outside $HOME without an explicit opt-in, and pass
# `--` before every positional path argument handed to mv/stow/install so a
# dash-prefixed path can never be parsed as a flag.
# A --repair destination that passes only the canary check reaches every
# account listed in ~/.claude/transcript-config-dirs, not only ~/.claude.
#
# Usage:
#   relocate-claude-config <new-path>
#   relocate-claude-config --repair <new-path>
#   relocate-claude-config [--repair] --allow-outside-home <new-path>
#
# Exit codes:
#   0  success
#   1  a precondition failed (bad current-repo state, failed validation,
#      claude-config not found, an unusable backup dir), or --repair could not
#      move a dangling link into the backup dir (`could not move ... into ...`).
#      That move fails mid-run, so entries moved before it stay in the backup
#      dir and the output names each.
#      A failing `claude` stow or write after the move exits with that
#      command's own status, which can be any code, 1, 2 and 3 included.
#      Stow 2.4.1 was observed to return 1 for a conflict and 2 for a missing
#      package directory.
#      Neither code is defined by this script or documented by Stow.
#      The status alone therefore does not identify the cause.
#      A 3 from that stow or write comes with no closing --repair line.
#      The last `unstowing`, `moving`, `mv failed`, `re-stowing at` or
#      `stowing at` line the output printed identifies it, and README "Repo
#      relocation" maps each to the state it leaves.
#      After a move the retry is
#      `relocate-claude-config --repair [--allow-outside-home] <new-path>`, with
#      the flag when the primary run passed it.
#      After --repair's `stowing at`, the retry is re-running the same command.
#   2  bad arguments
#   3  the checkout moved, or --repair linked the `claude` package, but
#      linking a package, or re-pointing a listed config dir, named on stderr
#      failed. Fix it, then run the --repair command the output ends with. A
#      checkout with no claude-skills/ directory is the exception: update it to
#      a commit that has one, then run ./install.sh from it, because the run
#      already installed the checkout's own copy of this script.

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
MANIFEST="$HOME/.claude-config-source"
BACKUP_DIR="$HOME/.claude-config-relocate-backup"
# Rows in stow-packages.sh's format for every package it lists except `claude`.
# A test keeps this equal to that script's rows.
RELINK_PACKAGES=($'claude-skills\t.claude')
RELINK_FAILURES=()
DECLARED_DIRS_FILE="$HOME/.claude/transcript-config-dirs"
DECLARED_CONFIG_DIRS=()

usage() {
  cat >&2 <<EOF
Usage:
  $SCRIPT_NAME <new-path>              Relocate this checkout to <new-path>
  $SCRIPT_NAME --repair <new-path>     Repair ~/.claude after an out-of-band move to <new-path>
  Both modes also re-point links in each config dir listed in ~/.claude/transcript-config-dirs.

Flags:
  --allow-outside-home   Permit a destination outside \$HOME (either mode)
  --                     End of flags; everything after is the destination
                         path verbatim (needed for a dash-prefixed path)
EOF
}

err() {
  printf '%s: %s\n' "$SCRIPT_NAME" "$*" >&2
}

# ---------------------------------------------------------------------------
# Small, independently testable helper functions. Kept separate from the
# stow/claude/mv call-outs below so each can be sourced and exercised
# directly (mirrors _lib.sh's own testing convention).
# ---------------------------------------------------------------------------

# True iff ~/.claude is itself a symlink — the legacy tree-folded form an
# older stow run (predating install.sh's mkdir -p guard) can leave behind,
# where the whole ~/.claude directory is one symlink into
# <repo>/claude/.claude, rather than a real directory whose individual
# entries are symlinks.
claude_is_tree_folded() {
  [ -L "$HOME/.claude" ]
}

# Canary check: does $1 look like a legitimate claude-config checkout?
repo_looks_legitimate() {
  [ -f "$1/.claude-plugin/marketplace.json" ]
}

# Print the single-line repo path recorded in the manifest, or fail (return
# 1, no stdout) when the manifest is absent, empty, or unreadable.
read_manifest() {
  [ -f "$MANIFEST" ] || return 1
  local value
  value=$(head -n 1 -- "$MANIFEST" 2>/dev/null | tr -d '[:space:]') || value=""
  [ -n "$value" ] || return 1
  printf '%s' "$value"
}

write_manifest() {
  printf '%s\n' "$1" > "$MANIFEST"
}

# Canonicalize $1 to an absolute, symlink-resolved path, printing nothing
# and returning 1 on failure. Same readlink -f + cd/pwd -P fallback pattern
# as deny-repo-relocation.sh's _relocation_resolve_source; duplicated rather
# than sourced from _lib.sh per this script's header (must keep working even
# when ~/.claude is broken).
_readlink_f() {
  local target="$1" resolved
  if command -v readlink >/dev/null 2>&1; then
    resolved=$(readlink -f -- "$target" 2>/dev/null) || return 1
  else
    resolved=$(cd -- "$(dirname -- "$target")" 2>/dev/null \
      && printf '%s/%s' "$(pwd -P)" "$(basename -- "$target")") || return 1
  fi
  [ -n "$resolved" ] || return 1
  printf '%s' "$resolved"
}

# Print the canonicalized form of $1, or $1 itself unchanged when it cannot
# be resolved (e.g. it no longer exists) — comparison callers treat a
# resolution failure as "not equal to anything real" naturally, with no
# separate unresolved state to handle.
canonicalize_for_comparison() {
  local resolved
  resolved=$(_readlink_f "$1") || resolved=""
  if [ -n "$resolved" ]; then
    printf '%s' "$resolved"
  else
    printf '%s' "$1"
  fi
}

# Resolve the LIVE ~/.claude symlink target, handling both the fresh
# per-entry-symlink form stow leaves today and the legacy tree-folded form.
# Prints the resolved repo dir, or fails (return 1, no stdout) when neither
# form yields a usable, existing directory. Shared by resolve_current_repo_dir
# below as both its cross-validation signal and its own fallback candidate.
_resolve_live_claude_repo_dir() {
  local candidate

  if claude_is_tree_folded; then
    candidate=$(_readlink_f "$HOME/.claude") || candidate=""
    candidate="${candidate%/claude/.claude}"
    if [ -n "$candidate" ] && [ -d "$candidate" ]; then
      printf '%s' "$candidate"
      return 0
    fi
    return 1
  fi

  if [ -d "$HOME/.claude" ] && [ -L "$HOME/.claude/hooks" ]; then
    candidate=$(_readlink_f "$HOME/.claude/hooks") || candidate=""
    candidate="${candidate%/claude/.claude/hooks}"
    if [ -n "$candidate" ] && [ -d "$candidate" ]; then
      printf '%s' "$candidate"
      return 0
    fi
  fi

  return 1
}

# Resolve the current claude-config checkout's absolute path. Tries the
# manifest first, cross-validated against a LIVE ~/.claude symlink
# resolution whenever one is available. The manifest alone is not a
# trustworthy root of trust — it's a bare dotfile at $HOME, outside any git
# repo and unrestricted by this repo's hooks, so a prompt-injected agent
# could point it at an attacker-built directory. Requiring agreement with
# the live symlink closes that: an attacker would also need to control the
# live symlink target. No live probe available (e.g. ~/.claude isn't
# stow-managed yet) is not itself a mismatch — the manifest is used alone.
#
# Return codes:
#   0  resolved (stdout: the repo path)
#   1  neither source available — no message printed, caller reports its own
#   2  both sources available but disagree — fails closed; this function has
#      already printed the explanation via err(), caller should not also
#      print its generic "could not locate" message
#
# "Live" is load-bearing: only the primary (non-repair) mode calls this,
# where symlinks are expected to still resolve; --repair mode never does,
# since the old location is already gone by definition.
resolve_current_repo_dir() {
  local manifest_candidate="" live_candidate=""

  if manifest_candidate=$(read_manifest) && [ -d "$manifest_candidate" ]; then
    :
  else
    manifest_candidate=""
  fi

  live_candidate=$(_resolve_live_claude_repo_dir) || live_candidate=""

  if [ -n "$manifest_candidate" ] && [ -n "$live_candidate" ]; then
    local manifest_real live_real
    manifest_real=$(canonicalize_for_comparison "$manifest_candidate")
    live_real=$(canonicalize_for_comparison "$live_candidate")
    if [ "$manifest_real" != "$live_real" ]; then
      err "$MANIFEST records '$manifest_candidate', which disagrees with the live ~/.claude symlink target '$live_candidate' — refusing to trust either one over the other. If $MANIFEST is stale, fix or remove it; if ~/.claude itself may have been tampered with, investigate before re-running."
      return 2
    fi
    printf '%s' "$manifest_candidate"
    return 0
  fi

  if [ -n "$manifest_candidate" ]; then
    printf '%s' "$manifest_candidate"
    return 0
  fi

  if [ -n "$live_candidate" ]; then
    printf '%s' "$live_candidate"
    return 0
  fi

  return 1
}

# Checks shared by both modes: <new-path> is not itself a dangling symlink,
# its parent directory exists, and (absent --allow-outside-home) it resolves
# under $HOME. Existence of <new-path> ITSELF is a mode-specific question —
# primary mode requires it to NOT yet exist (mv creates it); --repair mode
# requires it to already exist as the already-relocated checkout, verified
# separately by the canary check — so that check is not here.
validate_destination_common() {
  local new_path="$1"

  if [ -L "$new_path" ] && [ ! -e "$new_path" ]; then
    err "destination '$new_path' is a dangling symlink — remove it first or choose a different destination"
    return 1
  fi

  local parent parent_real
  parent="$(dirname -- "$new_path")"
  parent_real=$(_readlink_f "$parent") || parent_real=""
  if [ -z "$parent_real" ]; then
    err "destination's parent directory '$parent' does not exist or is unreachable — create it first"
    return 1
  fi

  # Resolved separately from parent_real above: --repair mode allows
  # new_path to already exist, and a LIVE symlink there (unlike the dangling
  # case above) would pass both the dangling check and a parent-only outside-
  # $HOME check while still pointing somewhere the parent check never sees.
  local new_path_real=""
  if [ -e "$new_path" ]; then
    new_path_real=$(_readlink_f "$new_path") || new_path_real=""
  fi

  if ! $ALLOW_OUTSIDE_HOME; then
    local home_real
    home_real=$(_readlink_f "$HOME") || home_real="$HOME"

    case "$parent_real" in
      "$home_real"|"$home_real"/*) ;;
      *)
        err "destination '$new_path' resolves outside \$HOME ('$home_real') — pass --allow-outside-home to permit this deliberately"
        return 1
        ;;
    esac

    if [ -n "$new_path_real" ]; then
      case "$new_path_real" in
        "$home_real"|"$home_real"/*) ;;
        *)
          err "destination '$new_path' is a symlink resolving outside \$HOME ('$home_real') to '$new_path_real' — pass --allow-outside-home to permit this deliberately"
          return 1
          ;;
      esac
    fi
  fi
}

validate_destination_for_relocate() {
  local new_path="$1"
  if [ -e "$new_path" ]; then
    err "destination '$new_path' already exists — refusing to overwrite it"
    return 1
  fi
  validate_destination_common "$new_path"
}

validate_destination_for_repair() {
  validate_destination_common "$1"
}

# Refuse a pre-planted symlink, or anything that is not a directory, at the
# fixed, predictable BACKUP_DIR path — quarantined entries must land in a real
# directory this script creates and the user can find, not wherever a symlink
# there happens to already point.
_ensure_backup_dir_is_usable() {
  if [ -L "$BACKUP_DIR" ]; then
    err "'$BACKUP_DIR' already exists as a symlink — refusing to quarantine into it. Remove it or replace it with a real directory first."
    exit 1
  fi
  if [ -e "$BACKUP_DIR" ] && [ ! -d "$BACKUP_DIR" ]; then
    err "'$BACKUP_DIR' exists and is not a directory — refusing to quarantine into it. Remove it or replace it with a real directory first."
    exit 1
  fi
}

# Create a new empty file named <stem>.<random suffix> in $BACKUP_DIR and print
# its path. Callers run it in $(...), so the unusable-dir refusal's exit ends
# only that substitution and the caller sees a failed status.
_new_backup_path() {
  _ensure_backup_dir_is_usable
  mkdir -p -- "$BACKUP_DIR" || return 1
  mktemp "$BACKUP_DIR/$1.XXXXXX"
}

# Quarantine-move (never delete) $1 when it is a symlink whose target does not
# exist, and return 1 without touching anything for any other path.
# Quarantine instead of delete because a dangling-symlink check alone can
# false-positive on a target that's merely temporarily unreachable (unmounted
# volume, offline share, mid-sync cloud path), not genuinely broken —
# quarantining keeps a wrongly-triggered repair reversible.
# Callers run it with errexit off, so a failed move exits here instead of
# returning a status.
_quarantine_if_dangling() {
  local dangling_path="$1" backup_path
  if [ ! -L "$dangling_path" ] || [ -e "$dangling_path" ]; then
    return 1
  fi
  if ! backup_path=$(_new_backup_path "$(basename -- "$dangling_path")"); then
    err "could not move $dangling_path into $BACKUP_DIR"
    exit 1
  fi
  echo "[relocate-claude-config] quarantining dangling $dangling_path -> $backup_path"
  if ! mv -f -- "$dangling_path" "$backup_path"; then
    rm -f -- "$backup_path"
    err "could not move $dangling_path into $BACKUP_DIR"
    exit 1
  fi
}

# Quarantine every dangling symlink directly inside $1; a live symlink or real
# file/directory is left untouched. Returns 0 when something was quarantined,
# 1 when nothing was.
_quarantine_dangling_children() {
  local dir="$1" found=false
  _ensure_backup_dir_is_usable
  local nullglob_was_set=0
  if shopt -q nullglob; then nullglob_was_set=1; fi
  shopt -s nullglob
  local entry
  for entry in "$dir"/*; do
    if _quarantine_if_dangling "$entry"; then
      found=true
    fi
  done
  if [ "$nullglob_was_set" -eq 0 ]; then shopt -u nullglob; fi
  $found
}

# --repair only. Quarantine-moves every dangling symlink under BOTH
# ~/.claude (handling both the tree-folded and per-entry forms) AND
# ~/.local/bin — `stow --adopt` refuses outright when a dangling entry is in
# its way, so leaving ~/.local/bin unquarantined would make --repair's own
# re-stow step fail. No tree-folded form applies to ~/.local/bin
# (install.sh's mkdir -p always precedes stow), so only the per-entry case
# is relevant there.
quarantine_dangling_claude_entries() {
  local quarantined_any=false
  _ensure_backup_dir_is_usable

  if claude_is_tree_folded; then
    if [ ! -e "$HOME/.claude" ]; then
      _quarantine_if_dangling "$HOME/.claude" && quarantined_any=true
    fi
  elif [ -d "$HOME/.claude" ]; then
    _quarantine_dangling_children "$HOME/.claude" && quarantined_any=true
  fi

  if [ -d "$HOME/.local/bin" ]; then
    _quarantine_dangling_children "$HOME/.local/bin" && quarantined_any=true
  fi

  if ! $quarantined_any; then
    echo "[relocate-claude-config] no dangling stow-managed entries found to quarantine"
  fi
}

# Determine the marketplace's current registration state for claude-config
# by comparing the canonicalized recorded .path (from `claude plugin
# marketplace list --json` — not .repo, which is github-source-only) against
# the canonicalized new repo path: no-op if already correct, remove+add if
# registered under a different path, add if not registered at all — three
# distinct idempotent states, not a blind remove-then-add.
sync_marketplace_registration() {
  local new_repo_path="$1"

  if ! command -v claude >/dev/null 2>&1; then
    err "'claude' CLI not found on PATH — skipping marketplace registration sync. Once it's available, run: claude plugin marketplace add \"$new_repo_path\" --scope user"
    return 0
  fi

  local new_repo_real
  new_repo_real=$(canonicalize_for_comparison "$new_repo_path")

  local recorded_path
  recorded_path=$(claude plugin marketplace list --json 2>/dev/null \
    | jq -r '.[] | select(.name == "claude-config") | .path // empty' 2>/dev/null) || recorded_path=""

  if [ -z "$recorded_path" ]; then
    echo "[relocate-claude-config] registering claude-config marketplace at $new_repo_real"
    if ! claude plugin marketplace add --scope user -- "$new_repo_real"; then
      err "marketplace registration failed adding '$new_repo_real' — the relocation itself still succeeded. Run manually once resolved: claude plugin marketplace add \"$new_repo_real\" --scope user"
    fi
    return 0
  fi

  local recorded_real
  recorded_real=$(canonicalize_for_comparison "$recorded_path")

  if [ "$recorded_real" = "$new_repo_real" ]; then
    echo "[relocate-claude-config] claude-config marketplace already registered at the correct path"
    return 0
  fi

  echo "[relocate-claude-config] re-registering claude-config marketplace: $recorded_path -> $new_repo_real"
  if ! claude plugin marketplace remove claude-config; then
    err "marketplace re-registration failed removing the stale entry at '$recorded_path' — the relocation itself still succeeded. Run manually once resolved: claude plugin marketplace remove claude-config && claude plugin marketplace add \"$new_repo_real\" --scope user"
    return 0
  fi
  if ! claude plugin marketplace add --scope user -- "$new_repo_real"; then
    err "marketplace re-registration failed adding '$new_repo_real' after removing the stale entry — the relocation itself still succeeded. Run manually: claude plugin marketplace add \"$new_repo_real\" --scope user"
  fi
}

finish_relocation() {
  local new_path="$1"
  sync_marketplace_registration "$new_path"
  write_manifest "$new_path"
  install -m 755 -- "$new_path/claude/.claude/scripts/relocate-claude-config.sh" "$HOME/.local/bin/relocate-claude-config"
}

# Re-link package $2 of the checkout at $1 into directory $3. The stow runs
# only once every top-level path of the package passed its check and every
# move succeeded. The body is a subshell, so an exit or shopt change ends with
# it. Callers run it as an `if` condition, where errexit is off, so each step
# checks its own status.
_relink_package() (
  local new_path="$1" package="$2" target_dir="$3"

  if [ -L "$target_dir" ]; then
    local link_text
    link_text=$(readlink -- "$target_dir") || link_text="unreadable"
    err "$target_dir is a symlink, such as the legacy tree-folded form that points into the checkout (link text: $link_text), so stowing $package would write through it into the checkout. Outside a Claude Code session, replace the link with a real directory, move into it the untracked content the folded directory holds, then run the --repair command this output ends with."
    exit 1
  fi

  shopt -s nullglob dotglob
  local entry entry_path
  for entry in "$new_path/$package"/*; do
    entry_path="$target_dir/$(basename -- "$entry")"
    if [ -d "$entry_path" ] && [ ! -L "$entry_path" ]; then
      err "$entry_path is a real directory, so $package is not merged into it. Move it aside, then run the --repair command this output ends with."
      exit 1
    fi
    _quarantine_if_dangling "$entry_path" || true
  done

  # The .DS_Store ignore matches install.sh's stow of a non-claude package.
  cd -- "$new_path" && stow -v --ignore='(^|/)\.DS_Store$' -t "$target_dir" "$package"
)

# Re-link every RELINK_PACKAGES row from the checkout at $1. A failed package
# is reported and recorded in RELINK_FAILURES, never aborts the run.
relink_packages() {
  local new_path="$1" row package target
  RELINK_FAILURES=()
  for row in "${RELINK_PACKAGES[@]}"; do
    package="${row%%$'\t'*}"
    target="${row#*$'\t'}"
    echo "[relocate-claude-config] linking $package at $new_path"
    if ! _relink_package "$new_path" "$package" "$HOME/$target"; then
      err "re-linking $package failed"
      RELINK_FAILURES+=("$package")
    fi
  done
  return 0
}

# Warn that line $1 of the roots file is skipped. It names the line only, because
# a path can identify an engagement.
_warn_unusable_declared_line() {
  err "line $1 of ~/.claude/transcript-config-dirs is not an absolute path to an existing directory, so that dir is not re-linked"
}

# Fill DECLARED_CONFIG_DIRS with a `<line number><TAB><physical path>` row for
# each usable dir in ~/.claude/transcript-config-dirs.
# _config_dir.py's declared_roots_matching owns the line grammar, and
# test_reader_matches_config_dir_parser compares the two on a fixed set of lines.
# That test does not cover a lone CR, VT, FF or U+2028, which split lines differently.
# It also does not cover the whitespace trim, which follows the locale's [:space:]
# where the Python parser trims a fixed ASCII set.
read_declared_config_dirs() {
  DECLARED_CONFIG_DIRS=()
  [ -f "$DECLARED_DIRS_FILE" ] && [ -r "$DECLARED_DIRS_FILE" ] || return 0

  local raw_line line line_number=0 physical_path row
  while IFS= read -r raw_line || [ -n "$raw_line" ]; do
    line_number=$((line_number + 1))
    line="${raw_line#"${raw_line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [ -z "$line" ] && continue
    case "$line" in '#'*) continue ;; esac
    if [ "$line" = "~" ]; then
      line="$HOME"
    elif [[ "$line" == \~/* ]]; then
      line="${HOME}${line#\~}"
    fi
    if [[ "$line" != /* ]]; then
      _warn_unusable_declared_line "$line_number"
      continue
    fi
    echo "[relocate-claude-config] checking line $line_number of ~/.claude/transcript-config-dirs"
    physical_path=""
    if [ -d "$line" ]; then
      physical_path=$(_readlink_f "$line") || physical_path=""
    fi
    if [ -z "$physical_path" ]; then
      _warn_unusable_declared_line "$line_number"
      continue
    fi
    for row in "${DECLARED_CONFIG_DIRS[@]}"; do
      [ "${row#*$'\t'}" = "$physical_path" ] && continue 2
    done
    DECLARED_CONFIG_DIRS+=("$line_number"$'\t'"$physical_path")
  done < "$DECLARED_DIRS_FILE" || return 0
}

# Print the relative path from directory $1 to path $2. Callers must pass
# physical absolute paths with no trailing slash.
_relative_path() {
  local from_dir="$1" to_path="$2" climb="" prefix rest=""
  while :; do
    prefix="${from_dir%/}"
    if [[ "$to_path" == "$prefix" || "$to_path" == "$prefix"/* ]]; then
      break
    fi
    from_dir=$(dirname -- "$from_dir")
    climb+="../"
  done
  if [[ "$to_path" != "$prefix" ]]; then
    rest="${to_path#"$prefix"/}"
  fi
  rest="${climb}${rest}"
  rest="${rest%/}"
  printf '%s' "${rest:-.}"
}

# The next three helpers run inside _repoint_declared_dir and share its locals
# (new_real, dir_real, line_number, roots and the counters) through bash's
# dynamic scope. They sit above it so shellcheck reports no SC2030 or SC2031.

# Count position $1 as a link that could not be re-pointed, for the cause $2.
_fail_declared_link() {
  err "could not re-point $1 in the dir on line $line_number of ~/.claude/transcript-config-dirs: $2"
  failed_links=$((failed_links + 1))
}

# Replace the dangling link at position $1 with relative text into
# $new_real/$2/$1, and keep its old text $3 in a backup copy. The old link
# stays in place until the final rename, so a failed step leaves it for a retry.
_repoint_declared_link() {
  local position="$1" root="$2" old_text="$3"
  local link_path="$dir_real/$position" link_name parent temp_link new_text backup_path
  link_name="${link_path##*/}"
  parent="${link_path%/*}"
  temp_link="$parent/.$link_name.relocate-claude-config.$$"

  if [ -e "$temp_link" ] || [ -L "$temp_link" ]; then
    _fail_declared_link "$position" "its temporary name is taken"
    return 0
  fi
  # The x sentinel keeps a newline ending the text, which $(...) would drop.
  new_text=$(_relative_path "$parent" "$new_real/$root/$position"; printf x)
  new_text=${new_text%x}
  if ! ln -s -- "$new_text" "$temp_link" 2>/dev/null; then
    _fail_declared_link "$position" "could not create the new link"
    return 0
  fi
  if [ ! -e "$temp_link" ]; then
    rm -f -- "$temp_link" 2>/dev/null
    _fail_declared_link "$position" "the new link does not resolve"
    return 0
  fi
  if ! backup_path=$(_new_backup_path "$link_name.L$line_number"); then
    rm -f -- "$temp_link" 2>/dev/null
    _fail_declared_link "$position" "could not copy it into the backup dir"
    return 0
  fi
  if ! ln -sf -- "$old_text" "$backup_path" 2>/dev/null; then
    rm -f -- "$temp_link" "$backup_path" 2>/dev/null
    _fail_declared_link "$position" "could not copy it into the backup dir"
    return 0
  fi
  if [ ! -L "$link_path" ] || [ -e "$link_path" ]; then
    rm -f -- "$temp_link" 2>/dev/null
    _fail_declared_link "$position" "it changed during the run"
    return 0
  fi
  if ! mv -f -- "$temp_link" "$link_path" 2>/dev/null; then
    rm -f -- "$temp_link" 2>/dev/null
    _fail_declared_link "$position" "could not rename the new link over it"
    return 0
  fi
  repointed=$((repointed + 1))
  echo "[relocate-claude-config] re-pointed $position in the dir on line $line_number of ~/.claude/transcript-config-dirs; its old link is in $backup_path"
}

# Visit each name the checkout's package roots hold at position $1 under the
# listed dir ("." is the dir itself). It never lists the account's own tree.
# Past a root the checkout side is entered only through a real directory.
_walk_declared_position() {
  local position="$1" account_dir="$dir_real"
  if [ "$position" != . ]; then
    account_dir="$dir_real/$position"
  fi
  if [ ! -x "$account_dir" ]; then
    err "could not search $position in the dir on line $line_number of ~/.claude/transcript-config-dirs"
    unsearched=$((unsearched + 1))
    return 0
  fi

  local root checkout_dir entry child earlier_root held_by_earlier_root
  local child_path old_text matched_root candidate_root
  local -a walked_roots=()
  for root in "${roots[@]}"; do
    checkout_dir="$new_real/$root"
    if [ "$position" != . ]; then
      checkout_dir="$checkout_dir/$position"
      [ ! -L "$checkout_dir" ] || continue
    fi
    [ -d "$checkout_dir" ] || continue

    for entry in "$checkout_dir"/*; do
      child="${entry##*/}"
      if [ "$position" != . ]; then
        child="$position/$child"
      fi
      held_by_earlier_root=false
      for earlier_root in "${walked_roots[@]}"; do
        if [ -e "$new_real/$earlier_root/$child" ] || [ -L "$new_real/$earlier_root/$child" ]; then
          held_by_earlier_root=true
          break
        fi
      done
      if $held_by_earlier_root; then
        continue
      fi

      child_path="$dir_real/$child"
      if [ -L "$child_path" ]; then
        # The x sentinel keeps a newline ending the text, which $(...) would drop.
        if ! old_text=$(readlink -n -- "$child_path" 2>/dev/null && printf x); then
          _fail_declared_link "$child" "could not read its text"
          continue
        fi
        old_text=${old_text%x}
        if [ -e "$child_path" ]; then
          continue
        fi
        matched_root=""
        for candidate_root in "${roots[@]}"; do
          if [ -e "$new_real/$candidate_root/$child" ] && [[ "$old_text" == *"/$candidate_root/$child" ]]; then
            matched_root="$candidate_root"
            break
          fi
        done
        if [ -n "$matched_root" ]; then
          _repoint_declared_link "$child" "$matched_root" "$old_text"
        else
          left_alone=$((left_alone + 1))
          echo "[relocate-claude-config] left $child alone in the dir on line $line_number of ~/.claude/transcript-config-dirs: it does not resolve and is not recognized as this repo's link"
        fi
      elif [ -d "$child_path" ]; then
        _walk_declared_position "$child"
      fi
    done
    walked_roots+=("$root")
  done
}

# Re-point every dangling link of this repo's layout in the listed dir $2 (a
# physical path) to its position under the checkout $1. $3 is the dir's line in
# the roots file, and the package roots follow. The body is a subshell, so the
# shopt change and the counters end with it. Callers run it as an `if`
# condition, where errexit is off, so each step checks its own status.
_repoint_declared_dir() (
  local new_real="$1" dir_real="$2" line_number="$3"
  shift 3
  local -a roots=("$@")
  local repointed=0 failed_links=0 left_alone=0 unsearched=0

  shopt -s nullglob dotglob
  _walk_declared_position .
  echo "[relocate-claude-config] the dir on line $line_number of ~/.claude/transcript-config-dirs: re-pointed $repointed, could not re-point $failed_links, left $left_alone alone, could not search $unsearched"
  if [ "$failed_links" -gt 0 ] || [ "$unsearched" -gt 0 ]; then
    return 1
  fi
  return 0
)

# Re-point links in each dir listed in ~/.claude/transcript-config-dirs, other
# than ~/.claude and dirs inside the checkout at $1. A failed dir is recorded in
# RELINK_FAILURES, never aborts the run.
relink_declared_dirs() {
  local new_path="$1"
  if ! command -v readlink >/dev/null 2>&1; then
    if [ -f "$DECLARED_DIRS_FILE" ] && [ -r "$DECLARED_DIRS_FILE" ]; then
      err "readlink is not available, so no dir listed in ~/.claude/transcript-config-dirs is re-linked"
    fi
    return 0
  fi
  read_declared_config_dirs
  if [ "${#DECLARED_CONFIG_DIRS[@]}" -eq 0 ]; then
    return 0
  fi

  local new_real claude_real row package target line_number dir_real
  local -a roots=("claude/.claude")
  for row in "${RELINK_PACKAGES[@]}"; do
    package="${row%%$'\t'*}"
    target="${row#*$'\t'}"
    if [ "$target" = ".claude" ]; then
      roots+=("$package")
    fi
  done
  new_real=$(canonicalize_for_comparison "$new_path")
  claude_real=$(canonicalize_for_comparison "$HOME/.claude")

  for row in "${DECLARED_CONFIG_DIRS[@]}"; do
    line_number="${row%%$'\t'*}"
    dir_real="${row#*$'\t'}"
    if [ "$dir_real" = "$claude_real" ]; then
      echo "[relocate-claude-config] the dir on line $line_number of ~/.claude/transcript-config-dirs is ~/.claude, which the stows above cover"
      continue
    fi
    if [ "$dir_real" = "$new_real" ] || [[ "$dir_real" == "$new_real"/* ]]; then
      echo "[relocate-claude-config] the dir on line $line_number of ~/.claude/transcript-config-dirs lies inside the checkout, which this command never re-links"
      continue
    fi
    echo "[relocate-claude-config] walking the dir on line $line_number of ~/.claude/transcript-config-dirs"
    if ! _repoint_declared_dir "$new_real" "$dir_real" "$line_number" "${roots[@]}"; then
      err "re-pointing the dir on line $line_number of ~/.claude/transcript-config-dirs failed"
      RELINK_FAILURES+=("transcript-config-dirs:line-$line_number")
    fi
  done
  return 0
}

print_primary_reminders() {
  cat <<EOF
Reminders:
  - Other open shells or Claude Code sessions still have the OLD path as
    their working directory — reopen them, or 'cd $1' manually.
  - Do not run this command while other Claude Code sessions are active:
    every hook under ~/.claude/hooks/ is briefly absent between the unstow
    and re-stow steps above, and a concurrent session's tool call in that
    window gets a hard deny (fails closed, but visibly disruptive).
EOF
}

# Steps this command leaves to the user.
print_manual_steps() {
  cat <<'EOF'
Not done by this command:
  - Config dirs not listed in ~/.claude/transcript-config-dirs, or listed there and reported above as not re-linked, keep their links into the old location.
    A session under such an account loads none of this repo's settings, hooks or skills until its dir is re-linked.
    To have this command re-link one, list its absolute path in that file (which also adds it to the transcript tools' scan when it holds `projects/`), or correct the line a warning above names, or make its dir reachable.
    Then run `relocate-claude-config --repair [--allow-outside-home] <new-path>`, with the flag when this run passed it.
    Listing a dir there gives this command write access to its links, whether or not the transcript tools scan it, so list one only if you want that.
    This command did not touch a link reported above as left alone, so re-link or remove it yourself.
  - Any other account that registered this repo's marketplace, listed or not, still records it at the old location.
    `CLAUDE_CONFIG_DIR=<dir> register-marketplace` re-points it once that account's `settings.json` resolves.
  - Every linked worktree still records the old location: run `git worktree repair` in the moved checkout, naming each linked worktree's current path.
  - Anything outside this repo that names the old path, such as a scheduled job or a shell startup file, still names it.
  See README "Repo relocation".
EOF
}

# Print the closing text for the run's outcome: stdout when every package and
# listed dir re-linked, stderr with a --repair retry line when a package or
# listed dir failed. $2 is "primary" or "repair".
report_relink_outcome() {
  local new_path="$1" mode="$2"

  if [ "${#RELINK_FAILURES[@]}" -eq 0 ]; then
    if [ "$mode" = primary ]; then
      printf '\nDone. This checkout now lives at: %s\n\n' "$new_path"
      print_primary_reminders "$new_path"
      echo
    else
      cat <<EOF

Done. ~/.claude and ~/.local/bin now point at: $new_path

EOF
    fi
    print_manual_steps
    return 0
  fi

  local retry_path retry_allow_flag=""
  retry_path=$(canonicalize_for_comparison "$new_path")
  if $ALLOW_OUTSIDE_HOME; then
    retry_allow_flag=" --allow-outside-home"
  fi

  {
    echo
    if [ "$mode" = primary ]; then
      echo "The checkout moved to $new_path and the claude package is linked, but re-linking failed for: ${RELINK_FAILURES[*]}"
    else
      echo "The claude package is linked from $new_path, but re-linking failed for: ${RELINK_FAILURES[*]}"
    fi
    echo "The primary form must not be re-run."
    if [ "$mode" = primary ]; then
      print_primary_reminders "$new_path"
    fi
    print_manual_steps
    echo "The --repair retry also moves other dangling entries (those whose name does not start with a dot) directly under ~/.claude and ~/.local/bin into $BACKUP_DIR, not only those the move broke."
    echo "Resolve each failure named above first, because the retry fails the same way until then: a symlinked ~/.claude needs the replacement its error describes. Anything else at ~/.claude/skills that is not this checkout's link must be moved aside, and a failed move into $BACKUP_DIR needs that directory fixed."
    echo "A transcript-config-dirs:line-<N> entry is the dir on line <N> of ~/.claude/transcript-config-dirs. The errors above it name each link it could not re-point, with the cause, and each directory it could not search. Fix that cause, such as a dir this command cannot search or write, or delete the dir's line from ~/.claude/transcript-config-dirs so this command leaves it alone, which also drops it from the transcript tools' scan."
    echo "A missing claude-skills/ directory is the exception: update the checkout to a commit that has it, then run ./install.sh from it. This run already replaced the installed script with the checkout's own, so a retry before then runs that script and links nothing."
    printf 'relocate-claude-config --repair%s %q\n' "$retry_allow_flag" "$retry_path"
  } >&2
}

relocate_repo() {
  local new_path="$1"

  _ensure_backup_dir_is_usable
  validate_destination_for_relocate "$new_path" || exit 1

  local current_repo
  if current_repo=$(resolve_current_repo_dir); then
    :
  else
    local resolve_status=$?
    # resolve_status 2: resolve_current_repo_dir already printed the
    # specific mismatch explanation via err() — printing the generic
    # "could not locate" message on top would be misleading (the checkout
    # WAS located, twice, disagreeingly).
    if [ "$resolve_status" -ne 2 ]; then
      err "could not locate the current claude-config checkout ($MANIFEST is missing or stale, and no live ~/.claude symlink was found). Nothing to relocate — if the checkout has already been moved outside a Claude Code session, use '$SCRIPT_NAME --repair <new-path>' instead."
    fi
    exit 1
  fi

  if ! repo_looks_legitimate "$current_repo"; then
    err "'$current_repo' does not look like a claude-config checkout (missing .claude-plugin/marketplace.json) — refusing to unstow it."
    exit 1
  fi

  echo "[relocate-claude-config] unstowing $current_repo"
  ( cd -- "$current_repo" && stow -D -t "$HOME" claude )

  echo "[relocate-claude-config] moving $current_repo -> $new_path"
  if ! mv -- "$current_repo" "$new_path"; then
    err "mv failed while relocating '$current_repo' -> '$new_path' — restoring the previous stow state at '$current_repo' so ~/.claude and ~/.local/bin keep working. Diagnose the failure (disk space, permissions, a cross-device rename) and re-run once resolved."
    mkdir -p "$HOME/.claude" "$HOME/.local/bin"
    ( cd -- "$current_repo" && stow -v --adopt -t "$HOME" claude )
    exit 1
  fi

  mkdir -p "$HOME/.claude" "$HOME/.local/bin"
  echo "[relocate-claude-config] re-stowing at $new_path"
  ( cd -- "$new_path" && stow -v --adopt -t "$HOME" claude )

  relink_packages "$new_path"
  finish_relocation "$new_path"
  relink_declared_dirs "$new_path"
  report_relink_outcome "$new_path" primary
  if [ "${#RELINK_FAILURES[@]}" -gt 0 ]; then
    exit 3
  fi
}

repair_repo() {
  local new_path="$1"

  validate_destination_for_repair "$new_path" || exit 1

  if ! repo_looks_legitimate "$new_path"; then
    err "'$new_path' does not look like a claude-config checkout (missing .claude-plugin/marketplace.json) — refusing to repair ~/.claude against it. Move the real checkout there first, or point --repair at its actual location."
    exit 1
  fi

  quarantine_dangling_claude_entries

  mkdir -p "$HOME/.claude" "$HOME/.local/bin"
  echo "[relocate-claude-config] stowing at $new_path"
  ( cd -- "$new_path" && stow -v --adopt -t "$HOME" claude )

  relink_packages "$new_path"
  finish_relocation "$new_path"
  relink_declared_dirs "$new_path"
  report_relink_outcome "$new_path" repair
  if [ "${#RELINK_FAILURES[@]}" -gt 0 ]; then
    exit 3
  fi
}

main() {
  REPAIR_MODE=false
  ALLOW_OUTSIDE_HOME=false
  NEW_PATH=""
  local end_of_flags=false

  while [ "$#" -gt 0 ]; do
    if $end_of_flags; then
      [ -z "$NEW_PATH" ] && NEW_PATH="$1"
      shift
      continue
    fi
    case "$1" in
      --repair) REPAIR_MODE=true; shift ;;
      --allow-outside-home) ALLOW_OUTSIDE_HOME=true; shift ;;
      --) end_of_flags=true; shift ;;
      -h|--help) usage; exit 0 ;;
      -*)
        err "unknown flag '$1'"
        usage
        exit 2
        ;;
      *)
        [ -z "$NEW_PATH" ] && NEW_PATH="$1"
        shift
        ;;
    esac
  done

  if [ -z "$NEW_PATH" ]; then
    usage
    exit 2
  fi

  if $REPAIR_MODE; then
    repair_repo "$NEW_PATH"
  else
    relocate_repo "$NEW_PATH"
  fi
}

# Only run when executed, not when sourced — lets tests source this file to
# exercise the helper functions above directly, the same way _lib.sh is
# tested, without also triggering argument parsing and the live mv/stow/
# claude call-outs.
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  main "$@"
fi
