# Rewrite test-conventions § 6 and align the rule texts that disagree with it

## Context

Goal: rewrite section 6 ("Test data") of the `test-conventions` skill and align the three other rule texts that disagree with it, so a copied named constant, or a value the code under test emits or parses, is no longer read as acceptable test-code repetition.

Ask: the engineer approved the final § 6 wording and the boundary it draws, in the prior session's words: "yes to both" (on variant 2 as the final wording and on ruling a builder-default stand-in value may repeat across files), and earlier "this wording sounds good to me" (on the boundary). The wording lives in a local file outside the repo and is reproduced verbatim in the plan's Approach so the plan survives without that file. The engineer later said a mechanical check and an edit pass over existing comments are "a separate follow-up", so neither belongs here.

Why now: today the four texts disagree. `test-conventions` § 6 says repeating test data is fine and shared fixtures are for expensive setup only. `code-review` item 9 carves test code out as DAMP and covers only a copied named helper. `claude/.claude/CLAUDE.md`'s "Single source of truth" bullet lists "DAMP test code" and "a small duplicated value that beats a bad abstraction" as unqualified exceptions. `test-evaluation` line 68 says "Duplicating production code in tests ... Import or call via integration", which conflicts with spelling out emitted values in a shared test module. A blind-reader test of four candidate wordings scored variant 2 best and the current § 6 worst.

Edits in scope (seven; item 7 added on the engineer's "Add CHANGELOG bullet" answer):
1. `claude-skills/skills/test-conventions/SKILL.md`: replace § 6's five bullets with variant 2. Net zero lines; the file is at the 200-line default cap. The length hook (`claude/.claude/hooks/check-skill-length.sh`) denies only a file that is over its limit and longer than the committed version, so net zero passes. Keep the heading `## 6. Test data` exactly, because other files cite it.
2. `claude/.claude/CLAUDE.md`, "Single source of truth" bullet (line 25): qualify exceptions (1) and (3) so a helper or a value the code under test emits or parses, copied into a second test file, is not covered. The clause must stand alone because the skill does not load in most sessions. Point to `test-conventions/SKILL.md` § "6. Test data"; a bare `test-conventions` target fails the citation-grammar test.
3. `claude-skills/skills/code-review/SKILL.md` item 9: replace everything from "Carve-out:" to the end of the item with the three-sentence carve-out in M3, which states the same boundary. Delete the old named-helper sub-clauses.
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

The exact edits:

- **M1, `claude-skills/skills/test-conventions/SKILL.md`.** Replace lines 107-110 with the first four bullets of Context's variant 2 block, byte for byte. Line 111 and the heading at line 105 stay.
- **M2, `claude/.claude/CLAUDE.md` line 25.** Insert these two sentences between "...a small duplicated value that beats a bad abstraction." and "Absent a named exception, duplication is a defect.", keeping the bullet on one line:

```markdown
Neither (1) nor (3) covers a helper that a second test file copies, or a value that two test files must keep equal, such as text or a number the code under test emits or parses. Define it once in a shared test module (spell a value out there, never derive it from the code under test), per `test-conventions/SKILL.md` § "6. Test data".
```

- **M3, `claude-skills/skills/code-review/SKILL.md` line 113.** Replace everything from `Carve-out:` to the end of the line, the trailing "(see `test-conventions` §6)." included, with:

```markdown
Carve-out: test code is DAMP, so do not flag repeated inline arrange/assert blocks unless they obscure the test's intent. Flag at two sites, whatever its size, a second test file's copy of a helper or of setup its assertions do not depend on, and a value two test files must keep equal, such as text or a number the code under test emits or parses, even when each file spells it inline. Point to one shared definition, with a value spelled out there rather than derived from the code under test, per `test-conventions/SKILL.md` § "6. Test data".
```

- **M4, `claude-skills/skills/test-evaluation/SKILL.md` line 68.** Replace the row with:

```markdown
| Duplicating production logic in tests | Test passes with stale copy, drift | Call the code or use integration; spell out expected values instead of importing them from the code under test, and define a value two test files must keep equal once in a shared test module, per `test-conventions/SKILL.md` § "6. Test data" |
```

- **M5, `claude-skills/skills/test-conventions/REFERENCES.md`.** After line 57, add one blank line and a section headed `## Test data: repetition in tests and values shared across test files`, followed by a blank line and this body:

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

- **M6, `docs/design-decisions/single-source-of-truth-rule.md`.** After the provenance line (line 3), insert a blank line and:

```markdown
**Corrected (2026-11-20):** DAMP is not a mid-2010s term. Jay Fields's 2006 post "DRY code, DAMP DSLs" uses it for domain-specific languages, and Google applied it to tests in a 2019 Testing on the Toilet post and in *Software Engineering at Google* ch. 12, which calls DAMP "complementary" to DRY, not a replacement for it. Exceptions (1) and (3) also no longer cover a helper that a second test file copies, or a value that two test files must keep equal. See `claude-skills/skills/test-conventions/SKILL.md` § "6. Test data" for the rule and `claude-skills/skills/test-conventions/REFERENCES.md` for the sources.
```

- **M7, `CHANGELOG.md`.** Insert as the first bullet under `## [Unreleased]`'s `### Changed`, above the current line 9:

```markdown
- **A test file may no longer copy a value that another test file must keep equal, such as text or a number the code under test emits or parses.** Under `test-conventions/SKILL.md` § "6. Test data", such a value, like a copied helper, is defined once in a shared test module, and a stand-in value the scenario does not depend on may still repeat across files. The global `CLAUDE.md` single-source-of-truth exceptions, `/code-review` item 9 and `test-evaluation`'s anti-pattern table now agree with that section.
```

Alternatives weighed:
- **CLAUDE.md, deleting exception (1).** Rejected: § 6's second bullet and ch. 12 still sanction repetition inside a test.
- **CLAUDE.md, a bare pointer to § 6.** Rejected: most sessions never load the skill (G1), so the clause must state the boundary itself.
- **CLAUDE.md, restating § 6's full list.** Rejected: it is a second copy of the list that can drift, which breaks the bullet's own rule. It also spends bytes against the 30,720-byte cap (row 6).
- **Item 9, keeping the named-helper sub-clauses and appending values.** Rejected: Context directs their deletion, and the two-site rule plus the one-fact test say the same thing in one sentence.
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
- G2. Two commit gates bind this change. `check-skill-length.sh` caps a SKILL.md at 200 lines by default. `check-claude-md-length.sh` caps a CLAUDE.md at 200 lines and 30,720 bytes. Each denies only a staged file that is over its limit and larger than its base. Reason: changing a cap is a separate decision with its own logged basis (`check-claude-md-length.sh:56-58`).
- G3. The quoted sources say what they say, including the tension between Meszaros and the Google chapter. Reason: their authors own them.

**Mechanisms:**
- M1. § 6 lines 107-110 become variant 2's first four bullets; line 111 and the heading stay. anchors: row1, row4, row5.
- M2. A stand-alone exclusion of two sentences, the second carrying the citation, inside the CLAUDE.md bullet. A pointer alone fails G1, and the full list duplicates § 6. anchors: root, row2, row6, row7, row9, row10.
- M3. A three-sentence carve-out in item 9 that keeps the two-site, any-size rule and the one-fact test. anchors: root, row2, row9, row11.
- M4. Relabel the test-evaluation row and replace its fix cell with the spell-out wording row 12 chose, closed by a clause that points to the shared test module and § 6 so the row cannot be read as per-file spelling. anchors: row9, row12, row13, row22.
- M5. A new REFERENCES.md section with verbatim quotes and the draft caveat. anchors: row16, row17, row18, row19.
- M6. An in-place correction note under the design record's provenance line. anchors: row14, row15, row16.
- M7. One CHANGELOG bullet. anchors: row20.
- M8. One `code-writer` dispatch for all seven files. anchors: root, row21.

**Rows:**
1. Variant 2 is § 6's final wording, and a builder-default stand-in value may repeat across files. [engineer-verified: "yes to both"] The quote answered both questions in the prior session, and the Ask line records it. It covers only those two points.
2. The engineer approved the boundary variant 2 draws: two items are one fact "when a change to one would have to be made to the other". [engineer-verified: "this wording sounds good to me"] The compact restatements in M2, M3, M6 and M7 are this plan's wording, not the engineer's.
3. A mechanical check and an edit pass over existing comments are excluded. [engineer-verified: "a separate follow-up"]
4. § 6 is the heading at line 105 and five bullets at lines 107-111. Line 111 equals variant 2's fifth bullet byte for byte, so four lines change and the line count holds. [verified: test-conventions/SKILL.md:105-111]
5. The file sits at its 200-line cap, and the skill gate's default limit is 200. [verified: dispatch evidence for the count; check-skill-length.sh:143 for the default] A net-zero edit passes, because the gate denies only growth past the limit. [verified: _lib.sh:3237-3243]
6. The CLAUDE.md gate also covers `claude/.claude/CLAUDE.md` with a 30,720-byte ratchet. [verified: check-claude-md-length.sh:59,131; _lib.sh:3244-3253]
7. `claude/.claude/CLAUDE.md` is 30,368 bytes. M2 adds 337 as reworded after the blind reads and the first review round. The result, 30,705, sits 15 bytes under the 30,720 cap. [verified: `wc -c claude/.claude/CLAUDE.md` printed 30,368 before the M2 edit and 30,637 with the 269-byte M2] The added parenthetical, "(spell a value out there, never derive it from the code under test)" with its leading space, is 68 bytes by `len(...encode())`. [unverified: 30,637 + 68 = 30,705 is a projection until the code-writer reports `wc -c`] A review edit that grows M2 by more than 15 bytes needs a matching deletion elsewhere in the bullet, not a cap change (G2). Verification step 1 re-measures before and after the edit.
8. No test or eval pins any wording this plan replaces. [verified: grep of `**/*.py` and `test-conventions/evals/trigger-cases.json` for the old § 6 phrases, "Carve-out", "test code is DAMP", "named test helper", "Import or call via integration", "Duplicating production", "Named exceptions" and "bad abstraction"; the only hits are test docstrings using the word DAMP] This closes Context's pending checks (a) and (c).
9. Every new citation names a `SKILL.md` file as its target, never a bare `test-conventions`. Outside the skill's directory the target is `test-conventions/SKILL.md`. Inside it (M5) the target is the sibling `SKILL.md`. A citation in a SKILL.md or its REFERENCES.md must resolve, and a target with no `/` resolves only as a same-directory sibling. So `` `test-conventions` `` fails, while `` `test-conventions/SKILL.md` `` resolves through the skill-directory branch. The citation pattern is not anchored to a line start, so M4's citation inside a table cell is extracted too. "6. Test data" survives heading normalization. [verified: test_skill_citation_grammar.py:76-97; _skill_md_helpers.py:229,290-330; claude/.claude/tests/helpers.py:157-191]
10. CLAUDE.md files, rule files and the doc corpus get an extraction check only. A hard-wrapped or no-space citation there fails the suite, but an unresolvable target does not. `CHANGELOG.md` is outside the doc corpus and is neither a CLAUDE.md nor a rule file, so M7's citation gets no check at all. [verified: test_skill_citation_grammar.py:136-172, 481-499; _skill_md_helpers.py:543-567] Verification step 3 pins the M2, M6 and M7 citations to the plan's exact text instead.
11. Item 9's base threshold is three sites. Today's carve-out flags a cross-file test-helper copy at two sites whatever its size, including a copy whose body differs when a fix to one would have to be made to the other. [verified: code-review/SKILL.md:113] M3 keeps both rules; without the two-site clause, the three-site default would govern test copies. M3 takes M2's grammar. Its helper and setup clauses carry no "when a change to one copy ..." condition. Its value clause says "must keep equal". Its value clause also says "even when each file spells it inline". The original trailing "when a change to one copy ..." let two of four readers pass a delimiter spelled inline in two test files. The reworded text matched the key on every fixture in two fresh reads. [verified: Verification step 5's item 9 reads]
12. Line 68's fix cell spells out expected values instead of importing them from the code under test, rather than the earlier draft's "assert expected literals inline". [engineer-verified: "Spell out values, don't import (Recommended)"] The tag covers only that choice between the two wordings. The choice settles both conflicts with variant 2. Today's "Import" contradicts its fourth bullet. The draft's "inline" contradicts its third bullet, which forbids a value "named or pasted inline" in a second test file. [verified: Context's variant 2 block]
13. test-evaluation's row reads "Duplicating production code in tests | Test passes with stale copy, drift | Import or call via integration". [verified: test-evaluation/SKILL.md:68] This closes the line-68 part of pending check (b).
14. Line 3 of a design record is its italic provenance line. A record that a later change overturns gets a note immediately under that line. Tests check line 3, reject a stray "Formerly" fragment anywhere else, and resolve relative markdown links. [verified: .claude/rules/design-decisions.md:16-32; test_design_decision_files.py:268-338, 484] M6 carries no "Formerly" and no markdown link.
15. The record calls test code DAMP "rather than DRY" (line 9) and DAMP "a mid-2010s community term with no single canonical author" (line 14). Its exceptions paragraph also lists the small-duplicated-value exception that M2 narrows. [verified: docs/design-decisions/single-source-of-truth-rule.md:9,14] This closes the rest of pending check (b).
16. Every quote in M5 and M6 is verbatim from the copies Context's edit 5 calls "grep-checked local text copies of the pages". Non-breaking spaces and HTML entities are normalized, and one footnote marker is dropped. [verified: swe-ch12.txt:587,672,707,837; tott-damp.txt:1081,1089,1135; jf-dry-damp.txt:861,875; xu-LiteralValue.txt:78,136-137; xu-root.txt:122-124]
17. The Literal Value page links to itself as `Literal Value.html`, and `/LiteralValue.html` returned 404. [verified: xu-LiteralValue.html:363; 404-xu-LiteralValue.txt:6] The ToTT and Fields URLs come from each page's own Blogger widget path. [verified: tott-damp.txt:6189; jf-dry-damp.txt:3194] The ch. 12 URL is the one REFERENCES.md already cites. [verified: REFERENCES.md:27]
18. The xunitpatterns.com pages say they are out of step with the printed book, and the Literal Value page points to page 714. [verified: xu-root.txt:122-124; xu-LiteralValue.txt:78] REFERENCES.md's earlier sections cite four such pages with no caveat. [verified: REFERENCES.md:10,15,18,37] M5's caveat covers every such page in the file, so those sibling citations need no edit.
19. § 2 lists test infrastructure as a recognized test-first exception, while ch. 12 says shared test infrastructure "must always have its own tests". [verified: test-conventions/SKILL.md:35; swe-ch12.txt:837] M5 records the caution, and Out of scope says why § 2 stays.
20. A CHANGELOG bullet belongs in this PR. [engineer-verified: "Add CHANGELOG bullet (Recommended)"] The tag covers only adding the bullet. M7's text is this plan's wording (row 2). The precedent is that `### Changed` under `## [Unreleased]` records rule changes to review skills and prose rules. [verified: CHANGELOG.md:5-7,131,221] Entries run newest first: the entries at lines 29 and 36 match the subjects of #1543 and #1541, in that order. [verified: CHANGELOG.md:29,36 against the recent commit list]
21. No other skill, agent or doc restates the boundary. `code-review/REFERENCES.md:18` maps item 9 to the single-source-of-truth bullet by name only. `staff-sdet.md:60` cites § 6 by number, which the unchanged heading keeps valid. [verified: grep of `*.md` outside `.claude/plans/` for "DAMP", "bad abstraction" and the § 6 phrases]
22. M4's exact row text, closing clause included, stays as written rather than being trimmed or paired with a new row. [engineer-verified: "A: keep row, fix key (Recommended)"] The question showed the full row text and the blind-read results for both options. The tag covers only keeping that row as written, and the row's wording is this plan's. Verification step 5's test-evaluation key follows what the row flags.
23. § 6's variant 2 wording is kept as approved after the first review round. [engineer-verified: "Keep as approved (Recommended)"] The question asked whether to reopen § 6 over an overlap between its stand-in and copied-builder rules. The tag covers only keeping § 6.
24. Two edits are applied. M2 and M3 gain a clause that a shared test value is spelled out there, never derived from the code under test. M5's Meszaros note names helpers and setup as well as values. [engineer-verified: "Apply both (Recommended)"] The question described both as accuracy fixes. The wording of the M2 and M3 clause and of the M5 sentence is this plan's, not the engineer's.

## Critical files

One `code-writer` dispatch covers all seven files in one phase. Every replacement text is prescribed in Approach, and all of them rest on the same boundary wording (rows 1-2). The dispatch runs Verification steps 1-4 and reports each result, with the path of step 3's script. The dispatching session runs step 5 itself, because the agent that writes M2-M4 cannot also be their blind reader.

- `claude-skills/skills/test-conventions/SKILL.md`: lines 107-110 (M1).
- `claude/.claude/CLAUDE.md`: line 25 (M2).
- `claude-skills/skills/code-review/SKILL.md`: line 113, from `Carve-out:` to the end of the line (M3).
- `claude-skills/skills/test-evaluation/SKILL.md`: line 68 (M4).
- `claude-skills/skills/test-conventions/REFERENCES.md`: a new section after line 57 (M5).
- `docs/design-decisions/single-source-of-truth-rule.md`: a note after line 3 (M6).
- `CHANGELOG.md`: the first bullet under `## [Unreleased]`'s `### Changed` (M7).

Reuse: nothing to call. `test_skill_citation_grammar.py` already guards the new citations in M3, M4 and M5 (row 9), so no new test is needed.

Projected diff: about 62 changed lines. That is 8 in `test-conventions/SKILL.md`, 2 each in `CLAUDE.md`, `code-review/SKILL.md` and `test-evaluation/SKILL.md`, about 45 added in `REFERENCES.md`, 2 in the design record and 1 in `CHANGELOG.md`.

## Verification

1. Size checks, one per gate (G2):
   - CLAUDE.md bytes: run `wc -c claude/.claude/CLAUDE.md` before and after the M2 edit, so the report carries both numbers. After the edit it must print at most 30,720. Rows 6 and 7 give the gate and the projection.
     - If it prints more than 30,720, stop and report both numbers. Do not trim other bullets or shorten M2 yourself; row 7 says what a fix needs.
   - SKILL.md lines: `wc -l` on each edited SKILL.md prints the same count before and after its edit.
2. `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py` passes. The selection should include `claude-skills/skills/tests/test_skill_citation_grammar.py` and `claude/.claude/hooks/tests/test_design_decision_files.py`. If it omits either, report that as a `select-tests.py` rule-table bug, per the repo `CLAUDE.md`, rather than widening the run by hand.
3. Identity check, keyed by content. Write one script to a scratchpad outside the repository. It takes this plan's path as its only argument and runs from the worktree root. It finds each block in the plan by content, never by line number: variant 2 between Context's "Variant 2, the § 6 replacement text" line and its "Public-repo constraint" line, and each fenced block after its `**M<n>,` lead line. The code-writer runs it and returns its path, and the dispatching session re-runs it, and the seeded control below, before staging. Rules for the script itself:
   - It asserts the extracted counts and exits non-zero on a mismatch: variant 2 is 5 lines, M2, M3, M4, M6 and M7 are 1 line each, and M5 is its expected non-blank line count. A pass prints one result line with those counts, so empty extraction cannot pass silently.
   - Seeded control: before the real run, run it against a scratch copy of one target with one word of one block altered. It must report the alteration.
   - For M2 it also asserts that the text just before the inserted sentences ends "a bad abstraction." and the text just after begins " Absent a named exception".

   Its checks:
   - Variant 2: its five `- ` lines, `diff`ed against the `- ` lines under `## 6. Test data` in `test-conventions/SKILL.md` up to the next `## ` heading, give no diff output.
   - Whole-line blocks: for each of the M4, M5, M6 and M7 blocks, `grep -Fxv -f <target> <the block's non-blank lines>` prints nothing, so every line appears verbatim as a whole line of its target.
   - Inline inserts: for each of the M2 and M3 blocks, which are one line each, `grep -cF -- "<that line>" <target>` prints 1.
   - M7's citation: `` grep -cF -- '`test-conventions/SKILL.md` § "6. Test data"' CHANGELOG.md `` prints 1, so the citation has one space before its opening quote and sits on one line. No citation test scans `CHANGELOG.md` (row 10), so this is its only guard.
4. Removal and leak checks, one per sub-item:
   - `git grep -n -e 'Import or call via integration' -e 'named test helper' -- claude claude-skills` prints nothing.
   - Every non-blank line that `git diff HEAD -U0 -- claude-skills/skills/test-conventions/REFERENCES.md` adds, its `+++` header excluded, is M5's heading or a line of M5's block: `grep -Fxv -f <heading and block> <added lines>` prints nothing. M5's block holds URLs and no filesystem path, so no added line can hold one. Step 3's script runs this check too.
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
   - On a mismatch, do not stage. The dispatching session revises the text in this plan's block, applies the revised block to its target file, then re-runs step 3 and that text's reads with fresh agents. If a key entry itself looks wrong, ask the engineer before changing it, because the key carries the boundary rows 1 and 2 record.

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
   - The edited `claude/.claude/CLAUDE.md` "Single source of truth" bullet, with a verdict of covered by a named exception or not:
     - Not covered: a named constant for a size limit the production stub enforces, defined in one test file and copied into a second.
     - Not covered: an identical builder pasted into a second test file.
     - Not covered: a builder in a second test file that differs from the first in one field default, where the stub makes the two change together.
     - Covered: the same literal as the first, as a stand-in, defaulted by two distinct builders in two test files. The builders share a name pattern and field list, differ in body, and the stub shows their other fields diverging.
     - Covered: a shared test module spells out the value, two test files import it, and the production stub holds the same literal.
   - test-evaluation's whole anti-pattern table with M4's row in place, with a verdict of the row applies or not:
     - Applies: a test recomputes its expected value with its own re-implementation of the production stub's parser.
     - Does not apply: a test spells out its expected literal.
     - Applies: two test files each define the same constant, such as a size limit the stub enforces or a delimiter it parses.
     - Does not apply: two test files each spell out the same literal inline, in the assertion of a different test. That is a value each test chose beside its assertion, which § 6 lets repeat.
     - Does not apply: two test files each default a stand-in value the stub neither parses nor limits.
     - Does not apply: a shared test module spells out the value and two test files import it.
     - Applies: a test imports the production stub's constant to build both its input and its expected value.
6. In the review phase:
   - `/code-review` runs `/skill-review` on the three SKILL.md files, which the commit hook enforces.
   - Run `/ai-instruction-and-memory-files` on the `claude/.claude/CLAUDE.md` diff.
   - A review edit to any prescribed text lands in this plan's block first, then step 3's script re-runs.
   - An edit to M2, M3 or M4 also re-runs that text's step 5 reads.

## Out of scope

- A mechanical check for cross-file copies. The engineer called it "a separate follow-up" (row 3).
- A presence tripwire for the § 6 pointer that M2-M6 add. The citation tests check that a present citation resolves, not that it is present. The tripwire belongs with the mechanical-check follow-up (row 3), as a check of its own.
- Re-scoring the wording study's whole fixture corpus against M2, M3 and M4. Verification step 5's targeted fixture sets check each shipped text instead.
- An edit pass over existing comments and docstrings that justify a cross-file copy as DAMP, such as `claude/.claude/hooks/tests/test_require_plan_review.py:2463`, `claude/.claude/hooks/tests/test_require_skill_review.py:1897` and `claude/.claude/scripts/tests/test_transcript_denials.py:1011,1109`. This is the same "separate follow-up" (row 3).
- Wording for the one-character-constant edge that Context names. Context leaves it alone on purpose.
- Reconciling § 2's test-infrastructure exemption with ch. 12's "must always have its own tests" (row 19). § 2 exempts infrastructure from test-first, not from tests, and changing it is a rule change outside the Ask.
- The design record's Pragmatic Programmer quote at line 13. Context bars quoting the 20th-anniversary wording as unverified. The record, though, says the quote was checked against the publisher's extract, and correcting it needs a disproof this plan does not have.
- Plans under `.claude/plans/` that quote the old § 6 wording. They are preserved records.
