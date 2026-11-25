#!/usr/bin/env bash
set -uo pipefail

# Writes one config key to claude-config.toml and reads it back.
# Usage: config-set.sh <key> <value>
# VALUE is passed bare (`dollars`, never `"dollars"`); the file's own row
# quotes an enum literal. See docs/config-file.md § "Writing a value".
#
# Exit 0 = the key now resolves to VALUE. Prints the resolved value on stdout.
# Exit 1 = the arguments were valid, but the script could not confirm the key
# resolves to VALUE:
#   - nothing was written: a line outside the grammar, or a failed write.
#   - the row was written, but the key still resolves to another value.
# Exit 2 = usage, a key absent from a populated config-keys.psv, or a value
# the key's type rejects.
# Exit 3 = environment failure:
#   - _config.sh fails to source.
#   - the config dir is unresolvable (a relative CLAUDE_CONFIG_DIR, the
#     filesystem root, or an empty HOME).
#   - config-keys.psv is missing, unreadable or has no key rows.
#   - KEY's row has an empty `type` column.
#   - the state path exists and is not a readable regular file, or is a
#     symlink that does not resolve to one (including a dangling one).
#   - KEY's row is truncated after the `type` column. The script writes the
#     row first and exits 3 at the read-back.
#
# Exits 1 and 3 do not imply an unchanged file. The stderr `wrote` line marks
# every run that replaced the file. No nonzero exit prints anything on stdout.
#
# The write goes through _config.sh's _config_set, the only writer.
# No confirmation or TTY check; see docs/config-file.md § "The four
# enforcement-critical keys".
#
# Omits `-e` because every status maps to its own exit code, as config-get.sh
# does.
# shellcheck source=../hooks/_config.sh
. "$(dirname "$0")/../hooks/_config.sh" || exit 3

# _exit_unresolvable_config_dir
# Exits 3 with the message for a config dir that does not resolve to a usable path.
_exit_unresolvable_config_dir() {
  echo "config-set.sh: could not resolve a usable Claude Code config directory (CLAUDE_CONFIG_DIR is set to a relative path or resolves to the filesystem root, or \$HOME is unset/empty)" >&2
  exit 3
}

# _exit_partial_install DETAIL
# Exits 3 with DETAIL and the cause every schema failure here shares.
_exit_partial_install() {
  echo "config-set.sh: $1 -- a partial stow-relink or interrupted git pull, not a typo'd key name" >&2
  exit 3
}

if [ "$#" -ne 2 ]; then
  echo "config-set.sh: usage: config-set.sh <key> <value> — exactly two arguments, VALUE bare (see docs/config-file.md)" >&2
  exit 2
fi

KEY="$1"
VALUE="$2"

KEY_TYPE=$(_config_schema_field "$KEY" type)
SCHEMA_FIELD_STATUS=$?
case "$SCHEMA_FIELD_STATUS" in
  0) ;;
  3) _exit_partial_install "schema file not found or unreadable: $_CONFIG_SCHEMA_FILE" ;;
  4)
    # Status 4 covers a schema with no rows, a key absent from a populated
    # schema, and a key whose `type` column is empty.
    KNOWN_KEYS=$(_config_schema_known_keys) \
      || _exit_partial_install "schema file has no key rows: $_CONFIG_SCHEMA_FILE"
    # The list is space-joined, so a KEY holding whitespace could match a span
    # of two adjacent entries. Only a whitespace-free KEY is looked up.
    case "$KEY" in
      *[[:space:]]*) ;;
      *)
        case "$KNOWN_KEYS" in
          *" $KEY "*) _exit_partial_install "schema row for '$KEY' present but truncated" ;;
        esac
        ;;
    esac
    echo "config-set.sh: unknown key '$KEY'" >&2
    exit 2
    ;;
  *)
    echo "config-set.sh: unexpected status $SCHEMA_FIELD_STATUS reading the schema type of '$KEY'" >&2
    exit 3
    ;;
esac

if ! _config_type_accepts "$KEY_TYPE" "$VALUE"; then
  case "$KEY_TYPE" in
    bool) ACCEPTED_VALUES="true or false" ;;
    enum:*) ACCEPTED_VALUES="false or ${KEY_TYPE#enum:}" ;;
    *) ACCEPTED_VALUES="nothing (its schema type '$KEY_TYPE' is not writable)" ;;
  esac
  echo "config-set.sh: '$KEY' accepts $ACCEPTED_VALUES, passed bare without quotes; got '$VALUE'" >&2
  exit 2
fi

CONFIG_DIR=$(_lib_config_dir) || _exit_unresolvable_config_dir
case "$CONFIG_DIR" in
  ""|/) _exit_unresolvable_config_dir ;;
esac
STATE_FILE="$CONFIG_DIR/$_CONFIG_STATE_FILENAME"

_config_set "$KEY" "$VALUE" "$CONFIG_DIR"
SET_STATUS=$?
case "$SET_STATUS" in
  0) ;;
  1)
    # The reader prints its `skipping malformed line` warning naming the line.
    _config_value "$KEY" >/dev/null
    echo "config-set.sh: nothing was written. The cause is the \`skipping malformed line\` warning above, or a failed-write error. One malformed line in $STATE_FILE blocks every write, whichever key it names. An agent reports this to the engineer and does not edit or replace $STATE_FILE. The engineer fixes the line the warning names, or the write error, by hand, then re-runs the command." >&2
    exit 1
    ;;
  2) _exit_unresolvable_config_dir ;;
  3)
    echo "config-set.sh: $STATE_FILE exists but is not a readable regular file, or is a symlink that does not resolve to one (including a dangling link); nothing was written. An agent reports this to the engineer and leaves $STATE_FILE alone. The engineer fixes the path by hand, then re-runs" >&2
    exit 3
    ;;
  *)
    echo "config-set.sh: _config_set returned unexpected status $SET_STATUS; whether $STATE_FILE changed is unknown" >&2
    exit 3
    ;;
esac

echo "config-set.sh: wrote $STATE_FILE" >&2

if _config_enforcement_critical_safe_value "$KEY" && [ "$VALUE" != "$_CONFIG_SAFE_VALUE" ]; then
  HUMAN_NAME=$(_config_schema_field "$KEY" human-name) || HUMAN_NAME=""
  HUMAN_NAME="${HUMAN_NAME:-$KEY}"
  # An empty CDPATH keeps `cd` from printing the directory it found through a search path.
  SCRIPT_PATH="$(CDPATH='' cd "$(dirname "$0")" && pwd)/$(basename "$0")"
  RESTORE_COMMAND=$(printf '%q %q %q' "$SCRIPT_PATH" "$KEY" "$_CONFIG_SAFE_VALUE")
  if [ -n "${CLAUDE_CONFIG_DIR:-}" ]; then
    RESTORE_COMMAND="CLAUDE_CONFIG_DIR=$(printf '%q' "$CLAUDE_CONFIG_DIR") $RESTORE_COMMAND"
  fi
  echo "config-set.sh: notice: $KEY is enforcement-critical, and $VALUE relaxes $HUMAN_NAME for every session that uses $CONFIG_DIR once nothing else overrides this row. To restore it: $RESTORE_COMMAND" >&2
fi

RESOLVED=$(_config_value "$KEY")
RESOLVE_STATUS=$?
case "$RESOLVE_STATUS" in
  0) ;;
  2) _exit_unresolvable_config_dir ;;
  3) _exit_partial_install "schema file not found or unreadable: $_CONFIG_SCHEMA_FILE" ;;
  4) _exit_partial_install "schema row for '$KEY' present but truncated" ;;
  *)
    echo "config-set.sh: unexpected status $RESOLVE_STATUS reading '$KEY' back from $STATE_FILE" >&2
    exit 3
    ;;
esac

if [ "$RESOLVED" != "$VALUE" ]; then
  KEY_RESOLUTION=$(_config_schema_field "$KEY" resolution) || KEY_RESOLUTION=""
  case "$KEY_RESOLUTION" in
    config-dir-or-home)
      HOME_CLAUDE_DIR="${HOME:-}/.claude"
      OVERRIDE_CAUSE="a \`true\` in either $CONFIG_DIR or \$HOME/.claude wins, so check for a \`true\` row in $HOME_CLAUDE_DIR/$_CONFIG_STATE_FILENAME"
      LEGACY_FILENAME=$(_config_schema_field "$KEY" legacy-filename) || LEGACY_FILENAME=""
      if [ -n "$LEGACY_FILENAME" ]; then
        OVERRIDE_CAUSE="$OVERRIDE_CAUSE, or for the legacy file $HOME_CLAUDE_DIR/$LEGACY_FILENAME, which counts only while that $_CONFIG_STATE_FILENAME has no row for '$KEY'"
      fi
      OVERRIDE_CAUSE="$OVERRIDE_CAUSE. An agent reports this to the engineer and does not edit or remove either file"
      ;;
    *) OVERRIDE_CAUSE="another writer may have replaced the row, so re-run the command to check" ;;
  esac
  echo "config-set.sh: the row was written, but '$KEY' still resolves to '$RESOLVED' -- $OVERRIDE_CAUSE; see docs/config-file.md § \"Resolution precedence\"" >&2
  exit 1
fi

printf '%s\n' "$RESOLVED"
