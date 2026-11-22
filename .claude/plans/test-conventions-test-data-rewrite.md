# Rewrite test-conventions § 6 and align the rule texts that disagree with it

## Context

Goal: rewrite section 6 ("Test data") of the `test-conventions` skill and align the three other rule texts that disagree with it, so a copied named constant, or a value the code under test emits or parses, is no longer read as acceptable test-code repetition.

Ask: the engineer approved the final § 6 wording and the boundary it draws, in the prior session's words: "yes to both" (on variant 2 as the final wording and on ruling a builder-default stand-in value may repeat across files), and earlier "this wording sounds good to me" (on the boundary). The wording lives in a local file outside the repo and is reproduced verbatim in the plan's Approach so the plan survives without that file. The engineer later said a mechanical check and an edit pass over existing comments are "a separate follow-up", so neither belongs here.

Why now: today the four texts disagree. `test-conventions` § 6 says repeating test data is fine and shared fixtures are for expensive setup only. `code-review` item 9 carves test code out as DAMP and covers only a copied named helper. `claude/.claude/CLAUDE.md`'s "Single source of truth" bullet lists "DAMP test code" and "a small duplicated value that beats a bad abstraction" as unqualified exceptions. `test-evaluation` line 68 says "Duplicating production code in tests ... Import or call via integration", which conflicts with spelling out emitted values in a shared test module. A blind-reader comparison favoured variant 2 over the current § 6.

Edits in scope (twelve files; item 7 added on the engineer's "Add CHANGELOG bullet" answer):
1. `claude-skills/skills/test-conventions/SKILL.md`: replace § 6's five bullets with variant 2. Net zero lines; the file is at the 200-line default cap. The length hook (`claude/.claude/hooks/check-skill-length.sh`) denies only a file that is over its limit and longer than the committed version, so net zero passes. Keep the heading `## 6. Test data` exactly, because other files cite it.
2. `claude/.claude/CLAUDE.md`, "Single source of truth" bullet (line 25): qualify exceptions (1) and (3) so a helper, setup its assertions do not depend on, or a value two test files must keep equal, copied into a second test file, is not covered. The clause must stand alone because the skill does not load in most sessions. Point to `test-conventions/SKILL.md` § "6. Test data"; a bare `test-conventions` target fails the citation-grammar test. The same file's "Discriminator literals where a canonical symbol exists" bullet (line 42) gains an exception clause (M2a), so it no longer tells a test to import a production symbol when the import would make the test pass whatever the value.
3. `claude-skills/skills/code-review/SKILL.md` item 9: replace everything from "Carve-out:" to the end of the item with the three-sentence carve-out in M3, which states the same boundary. Delete the old named-helper sub-clauses. Item 9a (line 115) gains the same clause (M3a).
4. `claude-skills/skills/test-evaluation/SKILL.md` line 68: label "Duplicating production logic in tests"; the fix cell tells the reader to call the code or use integration and to spell out expected values instead of importing them from the code under test. The engineer chose that direction with the answer "Spell out values, don't import". The earlier draft's "inline" conflicts with § 6's third bullet.
5. `claude-skills/skills/test-conventions/REFERENCES.md`: add a section recording the verified sources, with exact quotes and URLs from grep-checked local text copies of the pages. The section records:
   - that define-once-across-test-files is this repo's own policy, not a source's statement;
   - from the Software Engineering at Google book (ch. 12): a little duplication is fine when it makes the test simpler and clearer;
   - from the same chapter: DAMP is "complementary" to DRY;
   - from the same chapter: shared constants are an anti-pattern, with builders preferred;
   - from the same chapter: cross-suite test infrastructure needs its own tests;
   - that the Meszaros xunitpatterns pages are web drafts superseded by the printed book;
   - that Meszaros's Literal Value page recommends a symbolic constant for the same literal across several tests, which is in tension with the book.

   The section must not:
   - cite Jay Fields for test code, because that post is about DSLs;
   - quote the 20th-anniversary Pragmatic Programmer wording or Fowler's Rule of Three, because both are unverified.
6. `docs/design-decisions/single-source-of-truth-rule.md`: add a correction note under its provenance line. The record calls DAMP "a mid-2010s community term with no single canonical author" and says test code is DAMP "rather than DRY". Both claims are wrong, and M6 carries the correction text. The supersession rule in `.claude/rules/design-decisions.md` allows the note.
7. `CHANGELOG.md`: one bullet under `## [Unreleased]`'s `### Changed`.
8. The byte cap (M2b): `claude/.claude/hooks/check-claude-md-length.sh` rises from 30,720 to 31,744 bytes, with `claude/.claude/hooks/tests/test_check_claude_md_length.py`, `docs/hooks.md`, the design record `docs/design-decisions/global-claude-md-agent-core-and-main-session-groups.md`, a docstring removed from `claude/.claude/hooks/tests/test_check_skill_length.py` and a second `CHANGELOG.md` bullet following. The M2a clause does not fit under the old cap.

Commit sequencing and PR body:
- The commit gate that runs in this session is the main checkout's copy of `check-claude-md-length.sh`, which still caps `CLAUDE.md` at 30,720 bytes until the main checkout pulls the raised hook (row 28). M2 and M2a grow `CLAUDE.md` to about 30,735 bytes, so that gate denies the commit.
- The session commits every changed file except `claude/.claude/CLAUDE.md`. The engineer commits `CLAUDE.md` from a separate terminal, outside the gated session. The session does not retry the denial or route around it.
- The PR body states:
  - who made the `CLAUDE.md` commit;
  - that the byte-cap raise reaches every stow consumer;
  - the exception clause of M2a and M3a (row 25).

Variant 2, the § 6 replacement text (five bullets, verbatim):

- Use factory/builder helpers that supply sensible defaults; tests override only the fields relevant to the scenario. A stand-in is a value the scenario does not depend on, so any other valid value would do (an id, a branch name, a model name). It is a builder default or a constant in the file that uses it, and may repeat across files.
- Write a value the test chooses in the test body, beside the assertion that depends on it, and make its meaning clear there (name `status: 3` or say why 3 matters). Repeating such a value across tests is fine. Shared fixtures are for expensive setup (DB schemas, server instances), not simple data objects.
- A second test file never copies, named or pasted inline, a helper (function, builder, stub script), setup steps whose details its assertions do not depend on, fixed text or a number the code under test emits or parses, or any other value two test files must keep equal (a delimiter, a message, a size limit). Two values or helpers that merely look alike are not one fact. They are one fact when a change to one would have to be made to the other.
- Define each such item once, in a plain module that every consuming test imports from the project's shared test-helper location, or from a new test-only directory if the project has none. Spell out a value the code under test emits or parses in that module rather than importing it from the code under test, so a change in the code still fails a test.
- For tests against shared databases, use unique prefixes/suffixes (run ID, timestamp) so parallel runs and stale data don't collide

Public-repo constraint for every artifact in the PR (commit message, PR body, REFERENCES.md, this plan): cite only what the repo itself shows (the disagreeing rule texts) and the verified public sources. Never include:
- study counts;
- row or finding identifiers;
- per-account or per-project figures;
- transcript paths;
- a filesystem path to the local source copies of the pages (REFERENCES.md cites URLs only).

Known edge left alone on purpose: a one-character constant is flagged by one reader tier and allowed by the other under variant 2. Do not add wording to chase it.

Pending checks (a), (b) and (c) from the prior session are closed in the Approach's assumption ledger. Rows 8, 13 and 15 each name the check they close.

## Approach

§ 6 becomes the canonical statement of the boundary. Lines 107-110 take variant 2's first four bullets verbatim, and line 111 already equals its fifth. Each of the three texts that disagree gains sentences that state the same boundary on their own and cite `test-conventions/SKILL.md` § "6. Test data". REFERENCES.md records the sources, the design record gets an in-place correction, and a CHANGELOG bullet tells stow consumers about the change.

The exact edits. State of the tree: the committed branch already holds the first-round M1, M3, M4 and M5 as written below. It holds older wording of M2, M6 and M7, which these blocks replace. M2a, M3a and M2b are new. The dispatch applies only what differs, and step 3 checks the result.

- **M1, `claude-skills/skills/test-conventions/SKILL.md`.** Replace lines 107-110 with the first four bullets of Context's variant 2 block, byte for byte. Line 111 and the heading at line 105 stay.
- **M2, `claude/.claude/CLAUDE.md` line 25.** Replace the two sentences between "...a small duplicated value that beats a bad abstraction." and "Absent a named exception, duplication is a defect." with these, keeping the bullet on one line:

```markdown
Neither (1) nor (3) covers a second test file's copy of a helper or of setup its assertions do not depend on, or a value two test files must keep equal. Define it once in a shared test module (a value spelled out, not derived from the code under test), per `test-conventions/SKILL.md` § "6. Test data".
```

  If the blind reads miss the delimiter or size-limit fixture of the single-source key, add ", such as a delimiter or a size limit" after "keep equal" (37 bytes).
- **M2a, `claude/.claude/CLAUDE.md` line 42.** In the "Discriminator literals where a canonical symbol exists" bullet, insert `, unless importing it would make a test pass whatever the value` after `defined elsewhere`, before the period, so the end of that sentence reads:

```markdown
an enum, status, or code defined elsewhere, unless importing it would make a test pass whatever the value.
```

- **M3, `claude-skills/skills/code-review/SKILL.md` line 113.** Replace everything from `Carve-out:` to the end of the line, the trailing "(see `test-conventions` §6)." included, with:

```markdown
Carve-out: test code is DAMP, so do not flag repeated inline arrange/assert blocks unless they obscure the test's intent. Flag at two sites, whatever its size, a second test file's copy of a helper or of setup its assertions do not depend on, and a value two test files must keep equal, such as text or a number the code under test emits or parses, even when each file spells it inline. Point to one shared definition, with a value spelled out there rather than derived from the code under test, per `test-conventions/SKILL.md` § "6. Test data".
```

- **M3a, `claude-skills/skills/code-review/SKILL.md` line 115 (item 9a).** Insert `, unless importing it would make a test pass whatever the value` after `without a shared named type`, before the question mark, so the result reads:

```markdown
at 3 or more sites without a shared named type, unless importing it would make a test pass whatever the value?
```

- **M4, `claude-skills/skills/test-evaluation/SKILL.md` line 68.** Replace the row with:

```markdown
| Duplicating production logic in tests | Test passes with stale copy, drift | Call the code or use integration; spell out expected values instead of importing them from the code under test, and define a value two test files must keep equal once in a shared test module, per `test-conventions/SKILL.md` § "6. Test data" |
```

- **M5, `claude-skills/skills/test-conventions/REFERENCES.md`.** The section below is already committed after line 57. Leave it in place unless step 3 reports a difference, and never add a second copy. Its heading is `## Test data: repetition in tests and values shared across test files`, followed by a blank line and this body:

```markdown
Grounds `SKILL.md` § "6. Test data". Defining a helper or value once for every test file that must keep it equal is this repository's own policy. None of the sources below states it as a rule.

**Software Engineering at Google, ch. 12 "Unit Testing" — "Tests and Code Sharing: DAMP, Not DRY"**
Erik Kuefler; CC BY-NC-ND 4.0. URL: https://abseil.io/resources/swe-book/html/ch12.html

Verbatim:
> "A little bit of duplication is OK in tests so long as that duplication makes the test simpler and clearer."
>
> "DAMP is not a replacement for DRY; it is complementary to it."

From "Shared Values" (footnote marker omitted):
> "Engineers are usually drawn to using shared constants because constructing individual values in each test can be verbose. A better way to accomplish this goal is to construct data using helper methods (see Shared values using helper methods) that require the test author to specify only values they care about, and setting reasonable defaults for all other values."

From "Defining Test Infrastructure", on code shared across test suites:
> "Test infrastructure needs to be treated as its own separate product, and accordingly, test infrastructure must always have its own tests."

**Applies to the rule as:** § 6's builder bullet and its repeat-a-chosen-value bullet follow the chapter, which prefers builders with defaults over shared constants. The shared test module § 6 prescribes is test infrastructure in the chapter's sense, so a helper placed there carries the chapter's caution about its own tests.

**Google Testing Blog — "Testing on the Toilet: Tests Too DRY? Make Them DAMP!"**
Derek Snyder and Erik Kuefler, 2019-12-03. URL: https://testing.googleblog.com/2019/12/testing-on-toilet-tests-too-dry-make.html

Verbatim:
> "Note that the DRY principle is still relevant in tests; for example, using a helper function for creating value objects can increase clarity by removing redundant details from the test body."
>
> "When writing unit tests and faced with a choice between the DRY and DAMP principles, lean more heavily toward DAMP."

**Jay Fields — "DRY code, DAMP DSLs"**
2006-05-09. URL: http://blog.jayfields.com/2006/05/dry-code-damp-dsls.html

Verbatim: "A well designed Domain Specific Language will appear as Descriptive And Meaningful Phrases."

**Applies to the rule as:** the post applies DAMP to domain-specific languages, not tests. It dates the term; never cite it for a test-code rule.

**Gerard Meszaros, *xUnit Test Patterns* (Addison-Wesley, 2007) — Literal Value, "Variation: Symbolic Constant"**
URL: http://xunitpatterns.com/Literal%20Value.html (page 714 of the printed book, per the web page)

Verbatim:
> "When we need to use the same Literal Value in several places in a single Test Method (page X) or within several distinct tests, it is a good practice to use a symbol constant instead of a Literal Value."

Every xunitpatterns.com page this file cites is a pre-publication draft. The site's home page says: "Note that the material here is now somewhat out of step with the book content because it hasn't been updated based on the results of copy editing." Cite the printed book for a rule, and treat a page quote as the draft's wording.

**Applies to the rule as:** this recommendation is in tension with the Google chapter's preference for builders over shared constants. § 6 sides with the chapter for a stand-in value and uses one shared definition only for what a second test file would otherwise copy: a helper, setup, or a value two test files must keep equal.
```

- **M6, `docs/design-decisions/single-source-of-truth-rule.md`.** Replace the committed `**Corrected (2026-11-20):**` note, which sits after the provenance line (line 3), with this one:

```markdown
**Corrected (2026-11-20):** DAMP is not a mid-2010s term. Jay Fields's 2006 post "DRY code, DAMP DSLs" uses DAMP for domain-specific languages. Google applied it to tests in the 2019 Testing on the Toilet post and in *Software Engineering at Google* ch. 12. That chapter calls DAMP "complementary" to DRY, not a replacement, which corrects the record's "rather than DRY". Exceptions (1) and (3) also no longer cover what § 6 bars a second test file from copying. See `claude-skills/skills/test-conventions/SKILL.md` § "6. Test data" for the rule and `claude-skills/skills/test-conventions/REFERENCES.md` for the sources.
```

- **M7, `CHANGELOG.md`.** Replace the committed M7 bullet with this one, and place it as the first bullet under `## [Unreleased]`'s `### Changed`, above the current entry for `git-feature-branch-sync`:

```markdown
- **A test file may no longer copy a value that another test file must keep equal, such as text or a number the code under test emits or parses.** Under `test-conventions/SKILL.md` § "6. Test data", such a value, like a copied helper, is defined once in a shared test module, and a stand-in value the scenario does not depend on may still repeat across files. The global `CLAUDE.md` single-source-of-truth exceptions, `/code-review` item 9 and `test-evaluation`'s anti-pattern table now agree with that section. The `CLAUDE.md` discriminator-literal rule and `/code-review` item 9a now excuse a test from importing a production symbol when the import would make the test pass whatever the value, so that test spells out the status or code value.
```

- **M2b, the byte cap.** M2a's clause does not fit under 30,720 bytes. Five edits and one bullet:
  - `claude/.claude/hooks/check-claude-md-length.sh`: set `GLOBAL_CLAUDE_MD_BYTE_LIMIT=31744`. In the comment above it, change "30,720 bytes = 30 KiB" to "31,744 bytes = 31 KiB" and "The 30,720 figure" to "The 31,744 figure". Append this line to the dated log, after the 2026-10-17 line:

```markdown
# 2026-11-21: 30720 -> 31744; the global CLAUDE.md needed room to state when a test spells out a value instead of importing it.
```

  - `claude/.claude/hooks/tests/test_check_claude_md_length.py`: set `BYTE_LIMIT = 31744`. The test that cross-checks the hook source keeps the two in step.
  - `docs/hooks.md`: in the `check-claude-md-length.sh` entry, change "30,720-byte cap" to "31,744-byte cap".
  - `docs/design-decisions/global-claude-md-agent-core-and-main-session-groups.md`: every line that describes the current gate (lines 60, 141 and 164 do) changes "30,720-byte" to "31,744-byte".
    - A line that records a past event stays as written, and step 3 reports it to the engineer.
    - Line 141 also drops its "(GH-1267)" parenthetical, because that issue set the previous figure, not this one.
  - `claude/.claude/hooks/tests/test_check_skill_length.py`: delete the docstring of `test_byte_limit_never_fires_for_this_caller` (near line 753). The 40,000-byte fixture still exceeds the cap.
    - The docstring restates how the shell hook calls the shared gate, which the test name and the code already show, and it carried the cap figure.
    - [engineer-verified: "Fix by deletion. Do you see how the docstrijg is repeating how the code works?"] The tag covers deleting the docstring, not the choice of which docstring facts to keep.
  - `CHANGELOG.md`: if a bullet raising the cap from 30,720 to 31,744 is already in the file, replace it with this one.
    - The result has this bullet as the second bullet under `## [Unreleased]`'s `### Changed`, directly below M7's bullet.
    - The older 25,600-to-30,720 bullet in that section stays as written.
    - The bullet:

```markdown
- **The `CLAUDE.md`/`AGENTS.md` byte cap that `check-claude-md-length.sh` enforces rises from 30,720 to 31,744 bytes for every stow consumer.** A denial needs the staged size to exceed both the limit and the committed size, so the raise only removes denials: a file that grows to a size between 30,721 and 31,744 bytes is no longer denied. The cap is checked per file, and the hook's comment says Codex's combined-size behavior for an AGENTS.md chain is not verified. The new figure is 31 KiB, leaving a single file 1,024 bytes to the 32 KiB Codex truncation point that the hook's comment names.
```


Alternatives weighed:
- **CLAUDE.md, deleting exception (1).** Rejected: § 6's second bullet and ch. 12 still sanction repetition inside a test.
- **CLAUDE.md, a bare pointer to § 6.** Rejected: most sessions never load the skill (G1), so the clause must state the boundary itself.
- **CLAUDE.md, restating § 6's full list.** Rejected: it is a second copy of the list that can drift, which breaks the bullet's own rule. It also spends bytes against the byte cap (row 6).
- **Item 9, keeping the named-helper sub-clauses and appending values.** Rejected: Context directs their deletion, and the two-site rule plus the "must keep equal" clause say the same thing in one sentence.
- **Item 9, a pointer only.** Rejected: a reviewer applies item 9 without loading `test-conventions`, so the item must stand alone (CLAUDE.md exception (2)).
- **test-evaluation, the earlier draft's "assert expected literals inline".** Rejected: the engineer chose the spell-out wording over it (row 12).
- **test-evaluation, the fix cell without its closing § 6 clause.** Rejected: read alone, "spell out expected values" invites spelling a value out in each test file, which § 6's third bullet forbids for a value two test files must keep equal.
- **Design record, a new superseding decision file.** Rejected as heavier than needed. Two lighter primitives were checked. The in-place note that `.claude/rules/design-decisions.md` prescribes (chosen) is one. Leaving the record untouched is the other, and it fails because the record would silently contradict the narrowed exceptions (row 14).
- **REFERENCES.md, folding the sources into the existing "Regex and logic" section, which already cites ch. 12.** Rejected: that section grounds a different rule, and its heading names that rule.
- **Two dispatches, edits 1-4 apart from 5-7.** Rejected: every text is prescribed above, so a split saves nothing. Both halves also rest on the same boundary wording, which `plan-it`'s split rule bars restating in two prompts.
- **Verification, the code-writer applying item 9 to fixtures it built.** Rejected: the author of M3 would grade its own text with the key in its prompt, which shows nothing about what a fresh reader decides (Verification step 5).

### Assumption ledger

**Root:** Four rule texts disagree on whether test code may copy a helper or a value into a second test file. `test-conventions` § 6 and `code-review` item 9 cover only a copied named helper. `claude/.claude/CLAUDE.md` exempts DAMP test code and small duplicated values outright. `test-evaluation` line 68 says to import production code. So a copied named constant, or a value the code under test emits or parses, passes as acceptable repetition.

**Givens:**
- G1. The `test-conventions` skill loads only when its description's triggers match, so most sessions never read § 6. Reason: the harness's skill loading owns this, driven by the description at `test-conventions/SKILL.md:3-9`.
- G2. Two commit gates bind this change. `check-skill-length.sh` caps a SKILL.md at 200 lines by default. `check-claude-md-length.sh` caps a CLAUDE.md at 200 lines and, after M2b, 31,744 bytes (30,720 before). Each denies only a staged file that is over its limit and larger than its base. Reason: changing a cap is a separate decision with its own logged basis (`check-claude-md-length.sh:56-58`).
- G3. The quoted sources say what they say, including the tension between Meszaros and the Google chapter. Reason: their authors own them.

**Mechanisms:**
- M1. § 6 lines 107-110 become variant 2's first four bullets; line 111 and the heading stay. anchors: row1, row4, row5.
- M2. A stand-alone exclusion of two sentences, the second carrying the citation, inside the CLAUDE.md bullet. A pointer alone fails G1, and the full list duplicates § 6. anchors: root, row2, row6, row7, row9, row10.
- M2a and M3a. Add a one-clause exception to the discriminator-literal rule (CLAUDE.md line 42) and to item 9a: a test need not import a production symbol when the import would make the test pass whatever the value. The clause states the reason, so it grants no licence to skip an import that would catch a renamed value. anchors: row7, row25, row26.
- M2b. Raise the CLAUDE.md byte cap so M2a fits, and update every site that states the current cap. anchors: row7, row26, row28.
- M3. A three-sentence carve-out in item 9 that keeps the two-site, any-size rule and states the boundary as "must keep equal" in place of § 6's one-fact test (row 11). anchors: root, row2, row9, row11.
- M4. Relabel the test-evaluation row and replace its fix cell with the spell-out wording row 12 chose, closed by a clause that points to the shared test module and § 6 so the row cannot be read as per-file spelling. anchors: row9, row12, row13, row22.
- M5. A new REFERENCES.md section with verbatim quotes and the draft caveat. anchors: row16, row17, row18, row19.
- M6. An in-place correction note under the design record's provenance line. anchors: row14, row15, row16.
- M7. One CHANGELOG bullet. anchors: row20.
- M8. One `code-writer` dispatch for all twelve files. anchors: root, row21.

**Rows:**
1. Variant 2 is § 6's final wording, and a builder-default stand-in value may repeat across files. [engineer-verified: "yes to both"] The quote answered both questions in the prior session, and the Ask line records it. It covers only those two points.
2. The engineer approved the boundary variant 2 draws: two items are one fact "when a change to one would have to be made to the other". [engineer-verified: "this wording sounds good to me"] The compact restatements in M2, M3, M6 and M7 are this plan's wording, not the engineer's.
3. A mechanical check and an edit pass over existing comments are excluded. [engineer-verified: "a separate follow-up"]
4. § 6 is the heading at line 105 and five bullets at lines 107-111. Line 111 equals variant 2's fifth bullet byte for byte, so four lines change and the line count holds. [verified: `git show origin/main:claude-skills/skills/test-conventions/SKILL.md`, lines 105-111]
5. The file sits at its 200-line cap, and the skill gate's default limit is 200. [verified: dispatch evidence for the count; check-skill-length.sh:143 for the default] A net-zero edit passes, because the gate denies only growth past the limit. [verified: _lib.sh:3237-3243]
6. The CLAUDE.md gate also covers `claude/.claude/CLAUDE.md` with a byte ratchet, 30,720 before M2b and 31,744 after. The hook that runs in this session is the main checkout's copy, which stays at 30,720 until the main checkout pulls the raised hook (row 28). [verified: the main checkout's check-claude-md-length.sh:59,131; _lib.sh:3244-3253]
7. `claude/.claude/CLAUDE.md` byte figures, against the cap M2b raises to 31,744. A review edit that pushes the file past 31,744 needs a matching deletion elsewhere in the bullet, not another cap change. A review edit that grows the file past HEAD goes to the engineer's terminal (row 28). Until the raised hook reaches the main checkout, the session's own gate denies any staged edit that grows the file past HEAD and past 30,720 bytes. Verification step 1 re-measures before and after the edit.
   - Baseline before this change: 30,368. [verified: `wc -c claude/.claude/CLAUDE.md` before the M2 edit]
   - The earlier M2 text (337 bytes with its leading space) brought it to 30,705, 15 under the old cap. [verified: `wc -c` at the start of the round-3 fixes]
   - The reworded M2 is 304 bytes with its leading space, 33 fewer. [verified: `len(...encode())` printed 336 and 303 for the old and new text, before the leading space]
   - M2a adds 63 bytes. [verified: `len(...encode())` on the inserted clause]
   - The projected result is 30735, 15 over the old cap and 1009 under the new one. [unverified: a projection until the code-writer reports `wc -c`]
   - The optional ", such as a delimiter or a size limit" adds 37 and would land at 30772.
8. No test or eval pins any wording this plan replaces. Two searches back this, each over `**/*.py` and `test-conventions/evals/trigger-cases.json`:
   - Old § 6 phrases "Carve-out", "test code is DAMP", "named test helper", "Import or call via integration", "Duplicating production", "Named exceptions" and "bad abstraction". The only hits are test docstrings using the word DAMP. [verified: the grep]
   - M2a and M3a phrases "never embed a raw", "canonical symbol", "domain discriminant", "3 or more sites" and "Discriminator literals". The only hits are the two edited lines and `code-review/SKILL.md:487`. [verified: the grep]
   - `code-review/REFERENCES.md:19` also matches the second search and maps item 9a to the bullet by name only.
   - This closes Context's pending checks (a) and (c).
9. Every new citation names a `SKILL.md` file as its target, never a bare `test-conventions`. Outside the skill's directory the target is `test-conventions/SKILL.md`. Inside it (M5) the target is the sibling `SKILL.md`. A citation in a SKILL.md or its REFERENCES.md must resolve, and a target with no `/` resolves only as a same-directory sibling. So `` `test-conventions` `` fails, while `` `test-conventions/SKILL.md` `` resolves through the skill-directory branch. The citation pattern is not anchored to a line start, so M4's citation inside a table cell is extracted too. "6. Test data" survives heading normalization. [verified: test_skill_citation_grammar.py:76-97; _skill_md_helpers.py:229,290-330; claude/.claude/tests/helpers.py:157-191]
10. CLAUDE.md files, rule files and the doc corpus get an extraction check only. A hard-wrapped or no-space citation there fails the suite, but an unresolvable target does not. `CHANGELOG.md` is outside the doc corpus and is neither a CLAUDE.md nor a rule file, so M7's citation gets no check at all. [verified: test_skill_citation_grammar.py:136-172, 481-499; _skill_md_helpers.py:543-567] Verification step 3 pins the M2, M6 and M7 citations to the plan's exact text instead.
11. Item 9's base threshold is three sites. Today's carve-out flags a cross-file test-helper copy at two sites whatever its size, including a copy whose body differs when a fix to one would have to be made to the other. [verified: `git show origin/main:claude-skills/skills/code-review/SKILL.md`, line 113]
   - M3 keeps the two-site threshold for test copies. Without it the three-site default would govern them.
   - M3 drops the differing-body rule. Its helper and setup clauses take M2's grammar and carry no "when a change to one copy ..." condition.
   - M3's value clause says "must keep equal" and "even when each file spells it inline". The original trailing "when a change to one copy ..." let a blind reader pass a delimiter spelled inline in two test files.
   - The reworded text matched the key on every fixture. [verified: Verification step 5's item 9 reads]
12. Line 68's fix cell spells out expected values instead of importing them from the code under test, rather than the earlier draft's "assert expected literals inline". [engineer-verified: "Spell out values, don't import (Recommended)"] The tag covers only that choice between the two wordings. The choice settles both conflicts with variant 2. Today's "Import" contradicts its fourth bullet. The draft's "inline" contradicts its third bullet, which forbids a value "named or pasted inline" in a second test file. [verified: Context's variant 2 block]
13. test-evaluation's row reads "Duplicating production code in tests | Test passes with stale copy, drift | Import or call via integration". [verified: `git show origin/main:claude-skills/skills/test-evaluation/SKILL.md`, line 68] This closes the line-68 part of pending check (b).
14. Line 3 of a design record is its italic provenance line. A record that a later change overturns gets a note immediately under that line. Tests check line 3, reject a stray "Formerly" fragment anywhere else, and resolve relative markdown links. [verified: .claude/rules/design-decisions.md:16-32; test_design_decision_files.py:268-338, 484] M6 carries no "Formerly" and no markdown link.
15. The record calls test code DAMP "rather than DRY" (line 9) and DAMP "a mid-2010s community term with no single canonical author" (line 14). Its exceptions paragraph also lists the small-duplicated-value exception that M2 narrows. [verified: `git show origin/main:docs/design-decisions/single-source-of-truth-rule.md`, lines 9 and 14] This closes the rest of pending check (b).
16. Every quote in M5 and M6 is verbatim from the copies Context's edit 5 calls "grep-checked local text copies of the pages". Non-breaking spaces and HTML entities are normalized, and one footnote marker is dropped. [verified: swe-ch12.txt:587,672,707,837; tott-damp.txt:1081,1089,1135; jf-dry-damp.txt:861,875; xu-LiteralValue.txt:78,136-137; xu-root.txt:122-124]
17. The Literal Value page links to itself as `Literal Value.html`, and `/LiteralValue.html` returned 404. [verified: xu-LiteralValue.html:363; 404-xu-LiteralValue.txt:6] The ToTT and Fields URLs come from each page's own Blogger widget path. [verified: tott-damp.txt:6189; jf-dry-damp.txt:3194] The ch. 12 URL is the one REFERENCES.md already cites. [verified: REFERENCES.md:27]
18. The xunitpatterns.com pages say they are out of step with the printed book, and the Literal Value page points to page 714. [verified: xu-root.txt:122-124; xu-LiteralValue.txt:78] REFERENCES.md's earlier sections cite four such pages with no caveat. [verified: REFERENCES.md:10,15,18,37] M5's caveat covers every such page in the file, so those sibling citations need no edit.
19. § 2 lists test infrastructure as a recognized test-first exception, while ch. 12 says shared test infrastructure "must always have its own tests". [verified: test-conventions/SKILL.md:35; swe-ch12.txt:837] M5 records the caution, and Out of scope says why § 2 stays.
20. A CHANGELOG bullet belongs in this PR. [engineer-verified: "Add CHANGELOG bullet (Recommended)"] The tag covers only adding the bullet. M7's text is this plan's wording (row 2). The precedent is that `### Changed` under `## [Unreleased]` records rule changes to review skills and prose rules. [verified: CHANGELOG.md:145,172,186] Entries run newest first, so M7's bullet goes above the current top entry. That entry, at line 9, matches #1553, the newest commit on origin/main. [verified: CHANGELOG.md:9 against `git log origin/main`] The rebase left the committed M7 bullet second, at line 13, so M7 moves it to first place.
21. No other skill, agent or doc restates the boundary. `code-review/REFERENCES.md:18` maps item 9 to the single-source-of-truth bullet by name only. `staff-sdet.md:60` cites § 6 by number, which the unchanged heading keeps valid. [verified: grep of `*.md` outside `.claude/plans/` for "DAMP", "bad abstraction" and the § 6 phrases]
22. M4's exact row text, closing clause included, stays as written rather than being trimmed or paired with a new row. [engineer-verified: "A: keep row, fix key (Recommended)"] The question showed the full row text and the blind-read results for both options. The tag covers only keeping that row as written, and the row's wording is this plan's. Verification step 5's test-evaluation key follows what the row flags.
23. § 6's variant 2 wording is kept as approved after the first review round. [engineer-verified: "Keep as approved (Recommended)"] The question asked whether to reopen § 6 over an overlap between its stand-in and copied-builder rules. The tag covers only keeping § 6.
24. Two edits are applied. M2 and M3 gain a clause that a shared test value is spelled out there, never derived from the code under test. M5's Meszaros note names helpers and setup as well as values. [engineer-verified: "Apply both (Recommended)"] The question described both as accuracy fixes. The wording of the M2 and M3 clause and of the M5 sentence is this plan's, not the engineer's.
25. Flag the exception clause of M2a and M3a ("unless importing it would make a test pass whatever the value") in the PR description. It narrows a rule in the always-loaded `CLAUDE.md`.
    - The `CLAUDE.md` discriminator-literal bullet (line 42) and `/code-review` item 9a told a test to import the production symbol, which contradicts § 6's rule to spell out a value the code under test emits or parses.
    - The round-3 review raised the contradiction.
    - The engineer handed the scoping decision to the plan-architect: "Ask the architect please. I am concerned about internal contradictions among prose rules".
    - The architect first chose the scope phrase "outside test code". The engineer asked for the reason, a test that would be vacuous, to be stated in place of a scope phrase, and the architect's second consult proposed the clause. [verified: both architect consult returns]
    - Keeping both edits in this PR is the engineer's call. [engineer-verified: "Keep both, quote is mine (Recommended)"] The tag covers only keeping M2a and M3a.
    - The engineer chose the clause's wording. [engineer-verified: "Yeah, I think you should use when importing. It would make the test pass whatever the value."] The tag covers the idea and its words. "A test" for "the test" and the placement are this plan's.
    - The M2 reword and the M6 correction note also come from that consult and are this plan's wording.
26. The CLAUDE.md byte cap rises from 30,720 to 31,744 bytes (M2b). [engineer-verified: "Yes, I agree that number of bytes that you suggest is reasonable. Okay, let's go with that."] The tag covers the 31,744 figure, which the engineer had been offered with its 31 KiB basis.
   - The change list (the hook, its test, `docs/hooks.md`, the two other sites that state the cap, and a CHANGELOG bullet) is this plan's.
   - The engineer also gave the reason for accepting the raise. [engineer-verified: "I'm honestly okay with you also increasing the claude.md cap, because we're just talking about a handful of bytes, and I'm already working on a huge reduction in another session to offload the main session text."] [engineer-verified: "this is not the time to worry about the claude.md limit. I would raise it."]
   - The two tags cover only that statement and that direction. They do not show that the reduction exists or lands.
   - The engineer was not offered a path-scoped rule in place of the raise. [unverified: whether one would have been preferred]
27. The docstring in `test_consume_durable_continuity_file_on_read.py` stays unchanged. The test derives the event name from the registry (`settings.json`), not from the code under test, so deriving is not vacuous and the discriminator-literal rule it cites still applies after M2a. [engineer-verified: "Leave it alone (Recommended)"] The tag covers only leaving it. The session's earlier claim that the citation would go stale was wrong.
28. The engineer makes the `CLAUDE.md`-growing commit outside the gated session. [engineer-verified: "You commit it (Recommended)"] The tag covers only who commits. The installed hook `~/.claude/hooks/check-claude-md-length.sh` resolves to the main checkout's copy, which reads `GLOBAL_CLAUDE_MD_BYTE_LIMIT=30720`. [verified: `readlink -f` and `grep -n '^GLOBAL_CLAUDE_MD_BYTE_LIMIT'` on that path] The gate denies a staged file that is over the limit and larger than HEAD. [verified: `_lib.sh:3115-3118,3250`] HEAD's `CLAUDE.md` is 30,705 bytes and the M2 plus M2a result is about 30,735 (row 7).

## Critical files

One `code-writer` dispatch covers all twelve files in one phase. Every replacement text is prescribed in Approach, and all of them rest on the same boundary wording (rows 1-2). The dispatch runs Verification steps 1-4 and reports each result, with the path of step 3's script. The dispatching session runs step 5 itself, because the agent that writes M2-M4 cannot also be their blind reader.

- `claude-skills/skills/test-conventions/SKILL.md`: lines 107-110 (M1).
- `claude/.claude/CLAUDE.md`: line 25 (M2) and line 42 (M2a).
- `claude/.claude/hooks/check-claude-md-length.sh`, `claude/.claude/hooks/tests/test_check_claude_md_length.py`, `docs/hooks.md`, `docs/design-decisions/global-claude-md-agent-core-and-main-session-groups.md` (lines 60, 141 and 164) and `claude/.claude/hooks/tests/test_check_skill_length.py` (one docstring removed): the cap (M2b).
- `claude-skills/skills/code-review/SKILL.md`: line 113, from `Carve-out:` to the end of the line (M3), and line 115 (M3a).
- `claude-skills/skills/test-evaluation/SKILL.md`: line 68 (M4).
- `claude-skills/skills/test-conventions/REFERENCES.md`: a new section after line 57 (M5).
- `docs/design-decisions/single-source-of-truth-rule.md`: a note after line 3 (M6).
- `CHANGELOG.md`: the first bullet under `## [Unreleased]`'s `### Changed` (M7).

Reuse: nothing to call. `test_skill_citation_grammar.py` already guards the new citations in M3, M4 and M5 (row 9), so no new test is needed.

Projected diff: about 80 changed lines. That is 8 in `test-conventions/SKILL.md`, 4 each in `CLAUDE.md` and `code-review/SKILL.md`, 2 in `test-evaluation/SKILL.md`, about 45 added in `REFERENCES.md`, 2 in the design record, 4 in `CHANGELOG.md`, and about 11 in the cap files.

## Verification

1. Size checks, one per gate (G2):
   - CLAUDE.md bytes: run `wc -c claude/.claude/CLAUDE.md` before and after the M2 and M2a edits, so the report carries both numbers. After the edit it must print at most 31,744. Rows 6 and 7 give the gate and the projection. A `CLAUDE.md` edit staged after the engineer's commit must not grow past that commit's size (row 7).
     - If it prints more than 31,744, stop and report both numbers. Do not trim other bullets or shorten M2 yourself; row 7 says what a fix needs.
   - SKILL.md lines: `wc -l` on each edited SKILL.md prints the same count before and after its edit.
2. `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py` passes. The selection should include `claude-skills/skills/tests/test_skill_citation_grammar.py` and `claude/.claude/hooks/tests/test_design_decision_files.py`. If it omits either, report that as a `select-tests.py` rule-table bug, per the repo `CLAUDE.md`, rather than widening the run by hand.
3. Identity check, keyed by content. Write one Python script to a scratchpad outside the repository. It takes this plan's path and a repository root (default: the current directory) as arguments. It finds each block in the plan by content, never by line number: variant 2 between Context's "Variant 2, the § 6 replacement text" line and its "Public-repo constraint" line, and each fenced block after its `**M<n>,` lead line. It compares exact strings in-process and never builds a shell grep from a block, because the blocks hold backticks and double quotes. The code-writer runs it and returns its path. The dispatching session re-runs it before staging.
   - HEAD already holds the first-round version of M1, M3, M4 and M5, and older versions of M2, M6 and M7. So presence is not enough: each check below also asserts exactly-once and that the superseded text is gone.
   - Exactly-once: each block, joined as one string, occurs exactly once in its target. M5's heading, taken from its lead line, a blank line and M5's block occur together exactly once, in that order.
   - Superseded text absent: the committed M2 sentences (starting "Neither (1) nor (3) covers a helper that a second test file copies"), the committed M6 note (containing "which calls DAMP \"complementary\" to DRY, not a replacement for it") and the committed M7 bullet's last sentence (ending "now agree with that section.") each occur zero times in their target as a bare string. The committed M7 sentence is the exception: the new M7 block contains it, so it occurs exactly once in `CHANGELOG.md`, inside that block.
   - Counts the script asserts against literals written in the script from this plan, not read back from its own extraction: variant 2 is 5 lines, M2, M2a, M3, M3a, M4, M6 and M7 are 1 line each, and M5 is 28 non-blank lines. M2b's two blocks are 1 line each: the hook log line occurs once in the hook, and the CHANGELOG bullet occurs once in `CHANGELOG.md`. A pass prints one result line with those counts.
   - Variant 2: its five `- ` lines equal the `- ` lines under `## 6. Test data` in `test-conventions/SKILL.md`, up to the next `## ` heading.
   - M2b, each its own assertion:
     - The hook holds `GLOBAL_CLAUDE_MD_BYTE_LIMIT=31744` once and `GLOBAL_CLAUDE_MD_BYTE_LIMIT=30720` zero times, and its comment holds "31,744 bytes = 31 KiB" once.
     - The hook's dated log holds the 2026-11-21 line once.
     - The test holds `BYTE_LIMIT = 31744` once and `BYTE_LIMIT = 30720` zero times.
     - `docs/hooks.md` holds "31,744-byte" once and "30,720-byte" zero times.
     - A search of the tracked files (`git ls-files`, so gitignored files are not read) for `30,720` and `30720`, outside the records (`CHANGELOG.md`, `.claude/plans/`, `docs/cost-levers-considered.md`, `docs/reports/`, `docs/case-studies/`), prints every hit and marks each allowed or not.
       - The search fails on any hit that is not allowed.
       - The two dated-log lines in the hook (the 2026-10-17 line and the 2026-11-21 line) are allowed, and the search also fails if either is missing from the hits. That makes the required hits a check inside the real run: a failed `git ls-files` or a wrong root drops them.
       - A line elsewhere that records a past event is reported to the engineer and is not allowed by default.
     - `CHANGELOG.md` is checked two ways. The older 25,600-to-30,720 entry sits in the same `### Changed` section and stays as written.
       - "rises from 30,720 to 31,744" occurs once in the file.
       - The superseded sentence "so the raise cannot add a denial for any consumer" occurs once in the file, in the older entry, and not in the cap bullet or its sub-bullets.
     - `test_check_skill_length.py` holds "omitting BYTE_LIMIT" and "well over" zero times, and holds `def test_byte_limit_never_fires_for_this_caller` once.
   - When a review edit changes an M-block, the text it replaces, committed or from an earlier revision, joins the superseded list before the script re-runs.
   - Step 3 is a one-off fidelity check. Each absence assertion is paired with a presence assertion on the same read, so it carries no seeded controls.
4. Removal and leak checks, one per sub-item:
   - `git grep -n -e 'Import or call via integration' -e 'named test helper' -- claude claude-skills` prints nothing.
   - REFERENCES.md holds no filesystem path from the source copies: `git grep -n -e '/tmp/' -e '/home/' -- claude-skills/skills/test-conventions/REFERENCES.md` prints nothing. M5 is already committed, so a `git diff HEAD` over that file would show nothing and prove nothing.
5. Blind reads, run by the dispatching session, not the code-writer, after steps 1-4 pass and before staging. Per `.claude/rules/skill-and-agent-self-review.md`, the fixtures stay in a scratchpad outside the repository.
   - Fixtures:
     - Write each from its key entry below, not from the wording of M2, M3 or M4.
     - Ship a production stub with each, so whether the code under test emits or parses a value can be decided from the fixture alone.
     - Name and order them so nothing hints at the key.
   - Dispatch, for each text under test: two fresh `general-purpose` agents with `model: sonnet`.
     - Each receives only that text and its fixtures, unlabeled, with no plan, Context or key.
     - Tell each to judge by the supplied text alone, because its own loaded `CLAUDE.md` still carries the old exceptions.
     - Tell each to read nothing except the named fixture and stub files in the scratchpad, because the plan and its key sit in the worktree.
     - Each returns one verdict per fixture.
   - A text passes when both reads match the key on every fixture.
   - Fail-first baseline for M2a and M3a: also run each one's fixture set once against the pre-edit text (`git show HEAD:<path>`, the one line or bullet). At least one fixture must flip, or the edit shows nothing.
   - If no fixture flips against the pre-edit text, report that to the engineer and keep the edit on the textual-contradiction rationale in row 25. Do not drop it or strengthen the fixtures without the engineer.
   - On a mismatch, do not stage. The dispatching session revises the text in this plan's block, applies the revised block to its target file, then re-runs step 3 and that text's reads with fresh agents.
   - If a key entry itself looks wrong, ask the engineer before changing it, because the key carries the boundary rows 1 and 2 record.
   - A revision to the M2a or M3a clause goes to the engineer first, because row 25 records the clause as the engineer's words.

   The key, per text under test:
   - Item 9 as M3 leaves it, with a verdict of flag or no flag:
     - F1, flag: two test files each spell out the delimiter the production stub parses.
     - F2, flag: a second test file holds a pasted copy of an identical named builder.
     - F3, flag: a second test file copies setup steps whose details its assertions do not depend on.
     - P1, no flag: the production stub parses F1's delimiter but stores a free-text field without parsing it, and two distinct builders in two test files each default that field to the delimiter's literal.
     - P2, no flag: a shared test module spells out the delimiter, two test files import it, and the production stub holds the same literal.
     - P3, no flag: a second test file copies setup steps whose details its assertions depend on.
     - P4, no flag: one test file repeats inline arrange blocks across its tests.
     - F4, flag: a second test file copies a named builder with one field default changed, and the two must be edited together.
     - P5, no flag: one test file reuses a helper across many of its tests.
     - F5, flag: a named size-limit constant the production stub enforces, defined in one test file and copied into a second.
     - F4 and P1 rest on the "must keep equal" clause and on M3 never defining a stand-in, not on the dropped one-fact test (row 11). Treat a miss on either as a wording finding on M3.
   - The edited `claude/.claude/CLAUDE.md` "Single source of truth" bullet, with a verdict of covered by a named exception or not:
     - Not covered: a named constant for a size limit the production stub enforces, defined in one test file and copied into a second.
     - Not covered: an identical builder pasted into a second test file.
     - Not covered: a builder in a second test file that differs from the first in one field default, where the stub makes the two change together.
     - Not covered: a delimiter the production stub parses, spelled out in two test files.
     - Covered: the same literal as the first, as a stand-in, defaulted by two distinct builders in two test files. The builders share a name pattern and field list, differ in body, and the stub shows their other fields diverging.
     - Covered: a shared test module spells out the value, two test files import it, and the production stub holds the same literal.
     - Not covered: a second test file copies setup steps whose details its assertions do not depend on.
     - Covered: a second test file copies setup steps whose details its assertions depend on.
   - The `claude/.claude/CLAUDE.md` "Discriminator literals where a canonical symbol exists" bullet as M2a leaves it, with a verdict of requires importing the production symbol or does not:
     - Does not require it: a test asserts the `Status.FAILED` wire value, in two test files. Importing the production constant would make the test pass whatever the value, so spell it out.
     - Does not require it: a test parses a delimiter and spells it out.
     - Does not require it: a test asserts an in-process error code.
     - Does not require it: a role label that only test helpers define. Three tests in one test file pass it as an input and select behavior by it, and no production code reads or emits it. Importing the helper's own constant would make each test pass whatever the value.
     - Requires it (control): production code in one module compares a raw status string at several sites, though another production module defines the enum with that member.
   - Item 9a as M3a leaves it, with a verdict of flag or no flag:
     - Flag: production code compares a raw status string at 3 sites with no named type.
     - No flag: one test file asserts that status string in 3 tests.
     - No flag: two production sites and two test sites compare the status string, four in all. The test sites assert the status that production code emits, so importing the symbol there would make them pass whatever the value, and the clause excuses them. That leaves two sites.
     - No flag: a role label that only test helpers define. Three tests in one test file pass it as an input and select behavior by it, with no named type, and no production code reads or emits it. Importing the helper's own constant would make each test pass whatever the value.
   - test-evaluation's whole anti-pattern table with M4's row in place, with a verdict of the row applies or not:
     - Applies: a test recomputes its expected value with its own re-implementation of the production stub's parser.
     - Does not apply: a test spells out its expected literal.
     - Applies: two test files each define the same constant, such as a size limit the stub enforces or a delimiter it parses.
     - Does not apply: two test files each spell out the same literal inline, in the assertion of a different test. That is a value each test chose beside its assertion, which § 6 lets repeat.
     - Does not apply: two test files each default a stand-in value the stub neither parses nor limits.
     - Does not apply: a shared test module spells out the value and two test files import it.
     - Applies: a test imports the production stub's constant to build both its input and its expected value.
   - Not probed by this key: a test-side case where importing the symbol is not value-blind, such as an imported symbol fed to production code that holds its own raw literal. Every test-side entry resolves to "does not require" or "no flag", and the production-side control is the only entry the clause leaves binding. The PR body says what the clause covers in the clause's own terms.
6. In the review phase:
   - `/code-review` runs `/skill-review` on the three SKILL.md files, which the commit hook enforces.
   - Run `/ai-instruction-and-memory-files` on the `claude/.claude/CLAUDE.md` diff.
   - A review edit to any prescribed text lands in this plan's block first, then step 3's script re-runs.
   - An edit to M2, M2a, M3, M3a or M4 also re-runs that text's step 5 reads. The M3 and M4 reads do not re-run for the round-3 fixes, which edit neither text. A review edit to M2a or M3a follows step 5's engineer-first rule.
7. Commits, after steps 1-6 pass:
   - The session runs the staged-diff `/code-review` and commits every changed file except `claude/.claude/CLAUDE.md`.
   - It then stages `claude/.claude/CLAUDE.md` alone, records `git rev-parse :claude/.claude/CLAUDE.md`, and runs the staged-diff `/code-review` on it, so a marker covers the bytes the engineer commits.
   - The session does not attempt that commit. Its last message names the staged state, gives `git -C <absolute worktree path> commit` with no `-a` and no pathspec, names the expected branch (shown by `git -C <absolute worktree path> branch --show-current`), and gives the commit message. It ends there.
   - After the engineer's commit, the session checks in that worktree that `git rev-parse HEAD:claude/.claude/CLAUDE.md` equals the blob ID it recorded, that `git diff --stat HEAD~1 HEAD` lists only that file, and that `git log -1 --format=%B HEAD` matches the message it gave.
   - `/ready-for-review` restarts only after those checks pass.
8. PR body: it carries the three items under Context's "Commit sequencing and PR body", stated in plain words with no row or round identifier.

## Out of scope

- A mechanical check for cross-file copies. The engineer called it "a separate follow-up" (row 3).
- A presence tripwire for the § 6 pointer that M2-M6 add. The citation tests check that a present citation resolves, not that it is present. The tripwire belongs with the mechanical-check follow-up (row 3), as a check of its own.
- Re-scoring the whole fixture corpus against M2, M3 and M4. Verification step 5's targeted fixture sets check each shipped text instead.
- An edit pass over existing comments and docstrings that justify a cross-file copy as DAMP, such as `claude/.claude/hooks/tests/test_require_plan_review.py:2463`, `claude/.claude/hooks/tests/test_require_skill_review.py:1897` and `claude/.claude/scripts/tests/test_transcript_denials.py:1011,1109`. This is the same "separate follow-up" (row 3).
- Wording for the one-character-constant edge that Context names. Context leaves it alone on purpose.
- Reconciling § 2's test-infrastructure exemption with ch. 12's "must always have its own tests" (row 19). § 2 exempts infrastructure from test-first, not from tests, and changing it is a rule change outside the Ask.
- The design record's Pragmatic Programmer quote at line 13. Context bars quoting the 20th-anniversary wording as unverified. The record, though, says the quote was checked against the publisher's extract, and correcting it needs a disproof this plan does not have.
- Plans under `.claude/plans/` that quote the old § 6 wording. They are preserved records.
