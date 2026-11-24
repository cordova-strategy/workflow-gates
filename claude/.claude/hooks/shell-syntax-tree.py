#!/usr/bin/env python3
"""Project shfmt's typed-JSON syntax tree of a Bash command into the data the hooks read.

Reads the JSON that `shfmt -ln bash --to-json` prints on stdin. `argv[1]` names the
projection, which the module writes to stdout. The only projection is `words`: the Args
words of every `CallExpr`, one per line, each command followed by one blank line.
A command that `-ln bash` parses to a `DeclClause` (`declare` and its kin, such as `export`,
`local`, `readonly`, `typeset` and `nameref`), `let`, `[[ ]]` and `(( ))` are not `CallExpr`
objects, so they emit no words.
The blank line keeps a flag that ends one command from taking the next command's first
word as its value. An empty word is also a blank line, so it reads as a command's end.

Both streams are UTF-8, whatever the locale: stdin is read from `sys.stdin.buffer` and
the words are written to `sys.stdout.buffer`. A newline inside a word is written as a
space, so no multi-line word can equal a flag word.

Exit status contract:
  0  success, projection on stdout (possibly empty).
  5  the tree is not one this module recognizes. Nothing is written to stdout.
  2  any other failure, such as bad usage, unreadable JSON, or a tree nested deeper
     than the JSON reader allows. Nothing is written to stdout.
Status 1 is never used, so CPython's own uncaught-exception status cannot read as a
property of the command.
The statuses above and both "nothing is written to stdout" clauses hold only while stdout and stderr are working.
A broken pipe on stdout or stderr can end the process with status 120.
A write that fails partway leaves its partial output, and a closed stderr sends the diagnostic to stdout.

The tree is checked strictly before the projection runs. shfmt's JSON has no stability
promise, so a renamed field, a new node type or a re-encoded operator must be refused
as not recognized, and not projected to no words. The tree is recognized only when all of these hold:
  - The root is a `File` object.
  - Every `Type` is in KNOWN_NODE_TYPES.
  - Every `BinaryCmd` operator is in KNOWN_BINARY_OPERATORS.
  - Every object's keys fall within the key set of the Go struct it encodes, from
    NODE_FIELDS. A typed object is matched by its `Type`, and an untyped one by the
    struct and field that hold it.
  - Every key in ALWAYS_PRESENT_KEYS for its struct is present.
  - No `ExtGlob` pattern holds `$(`, a backtick, `<(` or `>(`.
  - The number of `CallExpr` objects the projection visited equals a raw count of them.
The sets follow mvdan.cc/sh/v3: `syntax/nodes.go` for the struct fields, `syntax/tokens.go`
for the operators, and `syntax/typedjson/json.go` for the encoding. The conformance
corpus in the tests confirms them against the shfmt on PATH.
The encoder writes a field only when it holds a non-zero value, so a key's absence means
the zero value. ALWAYS_PRESENT_KEYS lists the keys that real shfmt writes on every node of
a struct, less four exceptions that hold no command and that no check reads: CaseItem.Op,
ForClause.DoPos, ForClause.DonePos and IfClause.FiPos.
A key that a valid command can leave at zero is not listed, so a shfmt that drops one,
such as Stmt.Cmd, CallExpr.Args or CmdSubst.Stmts, from a node holding commands is not detected.
The Lit.Value caveat: Lit.Value is listed, although shfmt omits it for an empty `Lit`. That breaks
the rule that a listed key is on every node, and the rule that a key a valid command can leave at
zero is not listed. A valid command that makes an empty `Lit` exits 5, as when an unquoted heredoc line
ends in a backslash directly before an expansion, or an extglob holds only a continuation.
That refusal fails closed and is accepted by shape.

A quoted heredoc body and a comment hold no command nodes. A `#` placed directly after the end of
a word part, with no blank between, is a comment to shfmt and part of the word to bash, so it can
hide what follows it on its line. Quotes, expansions, extglob patterns and array literals end word
parts this way. It hides inside parentheses, a substitution, backticks or a `case` arm, and after
an array literal's closing `)` anywhere. The walker descends every
list and object value of every node, so it reaches a command nested in an assignment
value, a declaration argument, a redirect target, an unquoted heredoc body, a process
substitution, a `for` word list, `[[ ]]`, `(( ))`, a parameter default or an array
element. The walker keeps its own stack, so tree depth cannot reach the recursion limit.
An `ExtGlob` pattern is one raw `Lit`, so the walker cannot reach a command inside it.
The check does not recognize a pattern that holds a substitution marker, for that reason.

A word's non-literal parts become a fixed placeholder that begins with `$`, with the
literal text on both sides kept. `--body-file="$F"` therefore yields the one word
`--body-file=` followed by the placeholder, and `$HOME/bin/git` keeps its `/git` suffix.
The projection does no expansion and no ANSI-C decoding. A file named like the
placeholder would be read in place of a variable's real target.

A test pins the script's own imports to `json` and `sys`. That pin covers imports only,
not builtins such as `open` or `eval`.
"""
import json
import sys

EXIT_INTERNAL_ERROR = 2
EXIT_TREE_NOT_RECOGNIZED = 5

# Stands in for every part of a word that expands at run time. It begins with `$` so
# the callers' path reads and the worktree classifier's `_needs_expansion` both see an expansion.
EXPANSION_PLACEHOLDER = "$(expansion)"

KNOWN_BINARY_OPERATORS = frozenset({"&&", "||", "|", "|&"})

# Dialect-only node types that `-ln bash` rejects with exit 1, so they never reach this
# module from the gates. `TestDecl` is `@test` in bats and `FlagsArithm` is a zsh subscript flag such as `${a[(r)x]}`.
# A tree that holds one is not a bash tree and is not recognized.
BASH_REJECTED_NODE_TYPES = frozenset({"TestDecl", "FlagsArithm"})

# Node types shfmt can write as a `Type` value: the root `File`, and each node held in an
# interface-valued field. typedjson's package comment states that rule.
# `Comment`, `Stmt`, `Assign`, `Redirect`, `CaseItem`, `ArrayExpr`, `ArrayElem`, `Slice`, `Replace`
# and `Expansion` are never held in an interface-valued field, so they never carry a `Type`.
# `BraceExp` is built only by syntax.SplitBraces, which the shfmt command never calls.
_EMITTED_NODE_TYPES = frozenset({
    "File",
    "CallExpr", "IfClause", "WhileClause", "ForClause", "CaseClause", "Block", "Subshell",
    "BinaryCmd", "FuncDecl", "ArithmCmd", "TestClause", "DeclClause", "LetClause",
    "TimeClause", "CoprocClause", "TestDecl",
    "Lit", "SglQuoted", "DblQuoted", "ParamExp", "CmdSubst", "ArithmExp", "ProcSubst", "ExtGlob",
    "BinaryArithm", "UnaryArithm", "ParenArithm", "FlagsArithm", "Word",
    "BinaryTest", "UnaryTest", "ParenTest",
    "WordIter", "CStyleLoop",
})  # fmt: skip

KNOWN_NODE_TYPES = _EMITTED_NODE_TYPES - BASH_REJECTED_NODE_TYPES

# The key set of each Go struct that shfmt encodes, from `syntax/nodes.go` at v3.14.0, besides
# the keys of the encoding itself. `Type` appears on the root and on an object held in an interface-valued field.
# `Pos` and `End` appear on nodes, and the structs `Slice`, `Replace` and `Expansion` carry neither.
# Each field's value is one of:
#   "pos"      a position object with exactly the keys Offset, Line and Col.
#   "scalar"   a string, boolean or number.
#   "typed"    an object that carries a `Type`, such as a field of interface type.
#   "typed[]"  a list of those.
#   "Name"     an object with no `Type`, encoding the struct `Name`.
#   "Name[]"   a list of those.
NODE_FIELDS = {
    "File": {"Name": "scalar", "Stmts": "Stmt[]", "Last": "Comment[]"},
    "Comment": {"Hash": "pos", "Text": "scalar"},
    "Stmt": {
        "Comments": "Comment[]", "Cmd": "typed", "Position": "pos", "Semicolon": "pos",
        "Negated": "scalar", "Background": "scalar", "Coprocess": "scalar", "Disown": "scalar",
        "Redirs": "Redirect[]",
    },
    "Assign": {
        "Append": "scalar", "Naked": "scalar", "Name": "Lit", "Index": "typed", "Value": "Word",
        "Array": "ArrayExpr",
    },
    "Redirect": {"OpPos": "pos", "Op": "scalar", "N": "Lit", "Word": "Word", "Hdoc": "Word"},
    "Word": {"Parts": "typed[]"},
    "Lit": {"ValuePos": "pos", "ValueEnd": "pos", "Value": "scalar"},
    "SglQuoted": {"Left": "pos", "Right": "pos", "Dollar": "scalar", "Value": "scalar"},
    "DblQuoted": {"Left": "pos", "Right": "pos", "Dollar": "scalar", "Parts": "typed[]"},
    "CallExpr": {"Assigns": "Assign[]", "Args": "Word[]"},
    "Subshell": {"Lparen": "pos", "Rparen": "pos", "Stmts": "Stmt[]", "Last": "Comment[]"},
    "Block": {"Lbrace": "pos", "Rbrace": "pos", "Stmts": "Stmt[]", "Last": "Comment[]"},
    "IfClause": {
        "Position": "pos", "ThenPos": "pos", "FiPos": "pos", "Cond": "Stmt[]",
        "CondLast": "Comment[]", "Then": "Stmt[]", "ThenLast": "Comment[]",
        "Else": "IfClause", "Last": "Comment[]",
    },
    "WhileClause": {
        "WhilePos": "pos", "DoPos": "pos", "DonePos": "pos", "Until": "scalar",
        "Cond": "Stmt[]", "CondLast": "Comment[]", "Do": "Stmt[]", "DoLast": "Comment[]",
    },
    "ForClause": {
        "ForPos": "pos", "DoPos": "pos", "DonePos": "pos", "Select": "scalar",
        "Braces": "scalar", "Loop": "typed", "Do": "Stmt[]", "DoLast": "Comment[]",
    },
    "WordIter": {"Name": "Lit", "InPos": "pos", "Items": "Word[]"},
    "CStyleLoop": {"Lparen": "pos", "Rparen": "pos", "Init": "typed", "Cond": "typed", "Post": "typed"},
    "BinaryCmd": {"OpPos": "pos", "Op": "scalar", "X": "Stmt", "Y": "Stmt"},
    "FuncDecl": {
        "Position": "pos", "RsrvWord": "scalar", "Parens": "scalar", "Name": "Lit",
        "Names": "Lit[]", "Body": "Stmt",
    },
    "CmdSubst": {
        "Left": "pos", "Right": "pos", "Stmts": "Stmt[]", "Last": "Comment[]",
        "Backquotes": "scalar", "TempFile": "scalar", "ReplyVar": "scalar",
    },
    "ParamExp": {
        "Dollar": "pos", "Rbrace": "pos", "Short": "scalar", "Flags": "Lit", "Excl": "scalar",
        "Length": "scalar", "Width": "scalar", "IsSet": "scalar", "Split": "scalar",
        "GlobSubst": "scalar", "RcExpand": "scalar", "Param": "Lit", "NestedParam": "typed",
        "Index": "typed", "Modifiers": "Lit[]", "Slice": "Slice", "Repl": "Replace",
        "Names": "scalar", "Exp": "Expansion",
    },
    "Slice": {"Offset": "typed", "Length": "typed"},
    "Replace": {"All": "scalar", "Orig": "Word", "With": "Word"},
    "Expansion": {"Op": "scalar", "Word": "Word"},
    "ArithmExp": {"Left": "pos", "Right": "pos", "Bracket": "scalar", "Unsigned": "scalar", "X": "typed"},
    "ArithmCmd": {"Left": "pos", "Right": "pos", "Unsigned": "scalar", "X": "typed"},
    "BinaryArithm": {"OpPos": "pos", "Op": "scalar", "X": "typed", "Y": "typed"},
    "UnaryArithm": {"OpPos": "pos", "Op": "scalar", "Post": "scalar", "X": "typed"},
    "ParenArithm": {"Lparen": "pos", "Rparen": "pos", "X": "typed"},
    "CaseClause": {
        "Case": "pos", "In": "pos", "Esac": "pos", "Braces": "scalar", "Word": "Word",
        "Items": "CaseItem[]", "Last": "Comment[]",
    },
    "CaseItem": {
        "Op": "scalar", "OpPos": "pos", "Comments": "Comment[]", "Patterns": "Word[]",
        "Stmts": "Stmt[]", "Last": "Comment[]",
    },
    "TestClause": {"Left": "pos", "Right": "pos", "X": "typed"},
    "BinaryTest": {"OpPos": "pos", "Op": "scalar", "X": "typed", "Y": "typed"},
    "UnaryTest": {"OpPos": "pos", "Op": "scalar", "X": "typed"},
    "ParenTest": {"Lparen": "pos", "Rparen": "pos", "X": "typed"},
    "DeclClause": {"Variant": "Lit", "Args": "Assign[]"},
    "ArrayExpr": {"Lparen": "pos", "Rparen": "pos", "Elems": "ArrayElem[]", "Last": "Comment[]"},
    "ArrayElem": {"Index": "typed", "Value": "Word", "Comments": "Comment[]"},
    "ExtGlob": {"OpPos": "pos", "Op": "scalar", "Pattern": "Lit"},
    "ProcSubst": {"OpPos": "pos", "Rparen": "pos", "Op": "scalar", "Stmts": "Stmt[]", "Last": "Comment[]"},
    "TimeClause": {"Time": "pos", "PosixFormat": "scalar", "Stmt": "Stmt"},
    "CoprocClause": {"Coproc": "pos", "Name": "Word", "Stmt": "Stmt"},
    "LetClause": {"Let": "pos", "Exprs": "typed[]"},
    # No tree from `shfmt -ln bash` holds the three structs below, and `check_tree` does not recognize one
    # before it reads its entry.
    # `FlagsArithm` and `TestDecl` are in BASH_REJECTED_NODE_TYPES, and `BraceExp` is built only by SplitBraces.
    "FlagsArithm": {"Flags": "Lit", "X": "typed"},
    "BraceExp": {"Sequence": "scalar", "Elems": "Word[]"},
    "TestDecl": {"Position": "pos", "Description": "Word", "Body": "Stmt"},
}  # fmt: skip

# The keys real shfmt writes on every node of a struct, from the conformance corpus.
# The encoder drops zero values, so a key that a valid command can leave empty is not listed:
# a value, an item list, or `ParamExp.Dollar`, which a bare array subscript in arithmetic omits.
# A body key that no valid command leaves empty is listed, so a shfmt that drops it is not recognized
# instead of hiding the body's commands: Block.Stmts, Subshell.Stmts, IfClause.Then,
# WhileClause.Cond, WhileClause.Do and ForClause.Do. ExtGlob.Pattern is listed because the
# extglob check reads it.
# Four keys hold no command and no check reads them, so they stay unlisted by name:
# CaseItem.Op, ForClause.DoPos, ForClause.DonePos and IfClause.FiPos.
# A dropped key that a valid command can omit, such as Stmt.Cmd or CallExpr.Args, is not detected.
# The Lit.Value caveat: Lit.Value is listed although shfmt omits it for an empty `Lit`, so a valid command that makes one exits 5.
# `Pos` and `End` are not listed because an empty `File` carries neither.
ALWAYS_PRESENT_KEYS = {
    "ArithmCmd": ("Left", "Right", "X"),
    "ArithmExp": ("Left", "Right", "X"),
    "ArrayExpr": ("Lparen", "Rparen"),
    "BinaryArithm": ("Op", "OpPos", "X", "Y"),
    "BinaryCmd": ("Op", "OpPos", "X", "Y"),
    "BinaryTest": ("Op", "OpPos", "X", "Y"),
    "Block": ("Lbrace", "Rbrace", "Stmts"),
    "CStyleLoop": ("Lparen", "Rparen"),
    "CaseClause": ("Case", "Esac", "In", "Word"),
    "CaseItem": ("Patterns",),
    "CmdSubst": ("Left", "Right"),
    "Comment": ("Hash",),
    "CoprocClause": ("Coproc", "Stmt"),
    "DblQuoted": ("Left", "Right"),
    "DeclClause": ("Variant",),
    "Expansion": ("Op",),
    "ExtGlob": ("Op", "OpPos", "Pattern"),
    "ForClause": ("Do", "ForPos", "Loop"),
    "FuncDecl": ("Body", "Name", "Position"),
    "IfClause": ("Position", "Then"),
    "LetClause": ("Exprs", "Let"),
    "Lit": ("Value", "ValueEnd", "ValuePos"),
    "ParamExp": ("Param",),
    "ParenArithm": ("Lparen", "Rparen", "X"),
    "ParenTest": ("Lparen", "Rparen", "X"),
    "ProcSubst": ("Op", "OpPos", "Rparen"),
    "Redirect": ("Op", "OpPos", "Word"),
    "SglQuoted": ("Left", "Right"),
    "Stmt": ("Position",),
    "Subshell": ("Lparen", "Rparen", "Stmts"),
    "TestClause": ("Left", "Right", "X"),
    "TimeClause": ("Time",),
    "UnaryArithm": ("Op", "OpPos", "X"),
    "UnaryTest": ("Op", "OpPos", "X"),
    "WhileClause": ("Cond", "Do", "DoPos", "DonePos", "WhilePos"),
    "WordIter": ("Name",),
    "Word": ("Parts",),
}

POSITION_KEYS = frozenset({"Offset", "Line", "Col"})

EXTGLOB_SUBSTITUTION_MARKERS = ("$(", "`", "<(", ">(")


class TreeNotRecognized(Exception):
    """The tree falls outside what this module checks for. The command line exits 5."""


def _require_position(value):
    if not isinstance(value, dict) or value.keys() != POSITION_KEYS:
        raise TreeNotRecognized("a position object does not have the keys Offset, Line and Col")


def _require_object(value, field_name):
    if not isinstance(value, dict):
        raise TreeNotRecognized(f"field {field_name} holds a value that is not an object")


def _require_list(value, field_name):
    if not isinstance(value, list):
        raise TreeNotRecognized(f"field {field_name} holds a value that is not a list")


def _push_field_value(stack, field_name, field_kind, value):
    """Queue `value` for the object check, or check it now when it is a position or a scalar."""
    if field_kind == "pos":
        _require_position(value)
    elif field_kind == "scalar":
        if isinstance(value, (dict, list)) or value is None:
            raise TreeNotRecognized(f"field {field_name} holds a value that is not a scalar")
    elif field_kind.endswith("[]"):
        _require_list(value, field_name)
        element_kind = "typed" if field_kind == "typed[]" else field_kind[:-2]
        stack.extend((element, element_kind) for element in value)
    else:
        _require_object(value, field_name)
        stack.append((value, field_kind))


def check_tree(tree):
    """Raise TreeNotRecognized unless `tree` meets every condition but the last in the module docstring.

    Returns the raw count of `CallExpr` objects, for the caller's conservation check.
    """
    if not isinstance(tree, dict) or tree.get("Type") != "File":
        raise TreeNotRecognized("the root is not a File object")
    call_expr_count = 0
    stack = [(tree, "typed")]
    while stack:
        node, kind = stack.pop()
        _require_object(node, "(list element)")
        if kind == "typed":
            struct_name = node.get("Type")
            if not isinstance(struct_name, str) or struct_name not in KNOWN_NODE_TYPES:
                raise TreeNotRecognized("an object carries a Type that is not a known node type")
        else:
            if "Type" in node:
                raise TreeNotRecognized(f"an object for the struct {kind} carries a Type")
            struct_name = kind
        fields = NODE_FIELDS[struct_name]
        for key, value in node.items():
            if key == "Type":
                continue
            if key in ("Pos", "End"):
                _require_position(value)
                continue
            field_kind = fields.get(key)
            if field_kind is None:
                raise TreeNotRecognized(f"a {struct_name} object has an unknown key")
            _push_field_value(stack, key, field_kind, value)
        for required_key in ALWAYS_PRESENT_KEYS.get(struct_name, ()):
            if required_key not in node:
                raise TreeNotRecognized(f"a {struct_name} object lacks the key {required_key}")
        if struct_name == "BinaryCmd" and node["Op"] not in KNOWN_BINARY_OPERATORS:
            raise TreeNotRecognized("a BinaryCmd object has an operator that is not known")
        if struct_name == "ExtGlob":
            pattern_text = str(node.get("Pattern", {}).get("Value", ""))
            if any(marker in pattern_text for marker in EXTGLOB_SUBSTITUTION_MARKERS):
                raise TreeNotRecognized("an ExtGlob pattern holds a substitution")
        if struct_name == "CallExpr":
            call_expr_count += 1
    return call_expr_count


def iter_call_exprs(tree):
    """Yield every `CallExpr` object in the order the JSON lists them, descending every list and object value."""
    stack = [tree]
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            if value.get("Type") == "CallExpr":
                yield value
            stack.extend(reversed(list(value.values())))
        elif isinstance(value, list):
            stack.extend(reversed(value))


DOUBLE_QUOTE_ESCAPABLE = frozenset('$`"\\\n')


def _remove_backslash_escapes(literal, escapable_after_backslash=None):
    """Drop each backslash that escapes the character after it, as bash's quote removal does.

    `escapable_after_backslash` holds the characters a backslash may escape, and None means any character.
    Unquoted text escapes any character (Bash Reference Manual § 3.1.2.1 "Escape Character").
    Double-quoted text escapes only `$`, a backtick, `"`, `\\` and a newline (§ 3.1.2.3 "Double Quotes").
    A backslash before any other character stays, and so does a final backslash.
    A backslash-newline pair is a line continuation and vanishes whole.
    shfmt removes most continuations before they reach a `Lit`, but one that follows an escaped backslash stays in the value.
    """
    pieces = []
    index = 0
    while index < len(literal):
        character = literal[index]
        if (
            character == "\\"
            and index + 1 < len(literal)
            and (escapable_after_backslash is None or literal[index + 1] in escapable_after_backslash)
        ):
            index += 1
            character = literal[index]
            if character == "\n":
                index += 1
                continue
        pieces.append(character)
        index += 1
    return "".join(pieces)


def _flatten_double_quoted_parts(parts):
    return "".join(
        _remove_backslash_escapes(part["Value"], DOUBLE_QUOTE_ESCAPABLE)
        if part.get("Type") == "Lit"
        else EXPANSION_PLACEHOLDER
        for part in parts
    )


def flatten_word(word):
    """The text bash would see for `word`, with each run-time expansion replaced by EXPANSION_PLACEHOLDER.

    A backslash-newline that bash removes before it reads an expansion can leave a word here that differs from bash's.
    The cut residual in docs/design-decisions/tokenizing-gates-parse-with-shfmt.md lists those placements.
    A later change adds that file.
    """
    pieces = []
    for part in word.get("Parts", ()):
        part_type = part.get("Type")
        if part_type == "Lit":
            pieces.append(_remove_backslash_escapes(part["Value"]))
        elif part_type == "SglQuoted" and not part.get("Dollar"):
            pieces.append(part.get("Value", ""))
        elif part_type == "DblQuoted" and not part.get("Dollar"):
            pieces.append(_flatten_double_quoted_parts(part.get("Parts", ())))
        else:
            pieces.append(EXPANSION_PLACEHOLDER)
    return "".join(pieces).replace("\n", " ")


def project_words(tree):
    """Return (output text, number of CallExpr objects visited) for the `words` projection."""
    lines = []
    visited_call_exprs = 0
    for call_expr in iter_call_exprs(tree):
        visited_call_exprs += 1
        arg_words = call_expr.get("Args", ())
        if not arg_words:
            continue
        lines.extend(flatten_word(word) for word in arg_words)
        lines.append("")
    return "".join(line + "\n" for line in lines), visited_call_exprs


PROJECTIONS = {"words": project_words}


def main(argv):
    if len(argv) != 2 or argv[1] not in PROJECTIONS:
        print("usage: shell-syntax-tree.py words", file=sys.stderr)
        return EXIT_INTERNAL_ERROR
    try:
        tree = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        raw_call_expr_count = check_tree(tree)
        output, visited_call_exprs = PROJECTIONS[argv[1]](tree)
        if visited_call_exprs != raw_call_expr_count:
            raise TreeNotRecognized("the projection visited a different number of CallExpr objects than the tree holds")
        encoded_output = output.encode("utf-8")
    except TreeNotRecognized as error:
        print("shell-syntax-tree.py: tree not recognized: " + str(error), file=sys.stderr)
        return EXIT_TREE_NOT_RECOGNIZED
    except Exception as error:
        print("shell-syntax-tree.py: internal error: " + type(error).__name__, file=sys.stderr)
        return EXIT_INTERNAL_ERROR
    try:
        sys.stdout.buffer.write(encoded_output)
        sys.stdout.buffer.flush()
    except Exception as error:
        print("shell-syntax-tree.py: internal error: " + type(error).__name__, file=sys.stderr)
        return EXIT_INTERNAL_ERROR
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
