# Rewrite test-conventions § 6 and align the rule texts that disagree with it

## Context

Goal: rewrite section 6 ("Test data") of the `test-conventions` skill and align the three other rule texts that disagree with it, so a copied named constant, or a value the code under test emits or parses, is no longer read as acceptable test-code repetition.

Ask: the engineer approved the final § 6 wording and the boundary it draws, in the prior session's words: "yes to both" (on variant 2 as the final wording and on ruling a builder-default stand-in value may repeat across files), and earlier "this wording sounds good to me" (on the boundary). The wording lives in a local file outside the repo and is reproduced verbatim in the plan's Approach so the plan survives without that file. The engineer later said a mechanical check and an edit pass over existing comments are "a separate follow-up", so neither belongs here. After an adversarial review of the shipped wording, the engineer widened the request: "I really don't want to ship something that has conflicting data, or it's not conflicting data, conflicting guidelines. And I know that some of the conflicts are pre-existing, but I think now is the time to fix it, even if it takes a little longer for us to do that." They also said "Yeah, sure. Verify the finding five against the vendor page." Any new § 6 wording from that widening is a proposal until the engineer approves it.

Why now: today the four texts disagree. `test-conventions` § 6 says repeating test data is fine and shared fixtures are for expensive setup only. `code-review` item 9 carves test code out as DAMP and covers only a copied named helper. `claude/.claude/CLAUDE.md`'s "Single source of truth" bullet lists "DAMP test code" and "a small duplicated value that beats a bad abstraction" as unqualified exceptions. `test-evaluation` line 68 says "Duplicating production code in tests ... Import or call via integration", which conflicts with spelling out emitted values in a shared test module. A blind-reader comparison favoured variant 2 over the current § 6.

Edits in scope (fourteen files, the last being the one-number `code-file-size-exceptions.toml` change in Critical files; item 9, REFERENCES.md for the Codex row, added on the engineer's "Add it (Recommended)" answer; item 7 added on the engineer's "Add CHANGELOG bullet" answer):
1. `claude-skills/skills/test-conventions/SKILL.md`: replace § 6's five bullets with variant 2, then this round's M1 replaces variant 2's middle three bullets (rows 30-33). Net zero lines; the file is at the 200-line default cap. The length hook (`claude/.claude/hooks/check-skill-length.sh`) denies only a file that is over its limit and longer than the committed version, so net zero passes. Keep the heading `## 6. Test data` exactly, because other files cite it.
2. `claude/.claude/CLAUDE.md`, "Single source of truth" bullet (line 25): qualify exceptions (1) and (3) so a helper, setup whose details its assertions do not depend on, or a value two test files must keep equal, copied into a second test file, is not covered. The clause must stand alone because the skill does not load in most sessions. Point to `test-conventions/SKILL.md` § "6. Test data"; a bare `test-conventions` target fails the citation-grammar test. The same file's "Discriminator literals where a canonical symbol exists" bullet (line 42) gains an exception clause (M2a), so it no longer tells a test to import a production symbol when the import would make the test pass whatever the value.
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
9. `claude-skills/skills/ai-instruction-and-memory-files/REFERENCES.md` (M2c): a vendor URL and quote for the Codex row of the size table (rows 34-35).

Commit sequencing and PR body:
- The commit gate that runs in this session is the main checkout's copy of `check-claude-md-length.sh`, which still caps `CLAUDE.md` at 30,720 bytes until the main checkout pulls the raised hook (row 28). M2 and M2a grow `CLAUDE.md` past that cap and past its committed size (row 7), so that gate denies the commit.
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

§ 6 becomes the canonical statement of the boundary. Line 107 keeps variant 2's first bullet and line 111 its fifth. Lines 108-110 take M1, this plan's proposed revision of variant 2's middle three bullets, after an adversarial review found them in conflict with each other (rows 30-33). Each other text that states the boundary gains sentences that state it on their own and cite `test-conventions/SKILL.md` § "6. Test data". The other edits:
- REFERENCES.md records the sources.
- The design record gets an in-place correction.
- A CHANGELOG bullet tells stow consumers about the change.
- The byte-cap texts state Codex's combined-size limit from its source (row 34).

The exact edits. The dispatch applies only what differs from HEAD, and step 3 checks the result. HEAD holds every block below as it stood before this round, except item 9a, whose base is the uncommitted working-tree text M3a names.
- Changed this round, each a proposal until the engineer approves it (row 31):
  - M1, because § 6's middle bullets disagreed on an expected value two test files both assert, on a test that takes its expected value from the code under test, and on shared fixtures.
  - M2 and M3, which take M1's tiebreak, its source rule and its boundary phrase "emits or parses outside its process" (row 33). M4 takes the source rule and the boundary phrase and points to § 6 for the rest (row 41).
  - M3 also puts its flag sentence before its DAMP sentence, because the DAMP sentence came first and gave the opposite verdict on setup copied across files.
  - M2a and M3a, because their exception reached values that never leave the process.
  - M7, which takes the same boundary phrase.
  - M2b's hook comment and cap bullet, and the new M2c, because the byte-cap texts called Codex's combined-size behavior unverified though the vendor states it.
  - Added in this revision:
    - M1's bullet 2 limits only a fixture built once for many tests to expensive setup, and its bullet 4 lets setup be a fixture (row 39).
    - M1's bullet 2, M2, M3 and M7 allow a value taken from a source the code under test does not read (row 40).
    - M7 gains a sentence on fixtures (row 39).
    - M1's bullet 2 puts its examples of the boundary in parentheses, so the source allowance after them cannot attach to "a display".
    - M7 states the spell-out rule and the define-once rule in two sentences.
- Verify-only, already at HEAD: M5, M6 and every other M2b edit.

- **M1, `claude-skills/skills/test-conventions/SKILL.md`.** Replace lines 108-110, variant 2's second to fourth bullets, with the three lines below. Line 107, line 111 and the heading at line 105 stay.
  - Bullet 2 defines a chosen value and lets it repeat across files. It carries the spell-out rule for every test, which also allows a source the code under test does not read (row 40), and the only statement of the boundary's examples (row 33), set in parentheses.
    - Its last sentence keeps variant 2's fixture sentence in its approved place. It now limits only a fixture built once for many tests to expensive setup, and it lets a fixture return a builder for a simple data object but never the object itself (rows 39 and 41).
  - Bullet 3 adds the asserted case and the tiebreak sentence (row 32), and uses the boundary phrase without the examples.
  - Bullet 4 keeps variant 2's define-once sentence word for word and adds that setup or a builder may instead be a fixture (rows 39 and 41). Bullet 2 now carries the spell-out rule that variant 2 put here.
  - Each of the three questions a shared definition raises is stated once. Bullet 3 says when two items are one fact. Bullet 4 says which form the definition takes. Bullet 2 says when a fixture may be built once for many tests.

```markdown
- Write a value the test chooses in the test body, beside the assertion that depends on it, and make its meaning clear there (name `status: 3` or say why 3 matters). A result the test works out from its own input, such as `"3 items"` from `render(3)`, is a chosen value, but fixed text or a fixed number set in the code under test, with none of that input in it, is not. A chosen value may repeat across tests and files. Spell out every value the code under test emits or parses outside its process (such as through a file, a stream, an exit status or a display) or take it from a source that code does not read, rather than deriving it from that code or from where that code gets it, so a change in the code still fails a test. A fixture built once for many tests, rather than fresh for each test, is for expensive setup (DB schemas, server instances), and a fixture may return a builder for a simple data object, never the object itself. The test body passes that builder every value its assertions depend on.
- A second test file never copies, named or pasted inline, a helper (function, builder, stub script), setup steps whose details its assertions do not depend on, fixed text or a fixed number the code under test emits or parses outside its process, even one a test only asserts, or any other value two test files must keep equal (a delimiter, a message, a size limit). A chosen value is not one of these. Two values or helpers that merely look alike are not one fact. They are one fact when a change to one would have to be made to the other.
- Define each such item once, in a plain module that every consuming test imports from the project's shared test-helper location, or from a new test-only directory if the project has none. Setup or a builder may instead be a fixture that every consuming test uses.
```

- **M2, `claude/.claude/CLAUDE.md` line 25.** Replace the two sentences between "...a small duplicated value that beats a bad abstraction." and "Absent a named exception, duplication is a defect." with these, keeping the bullet on one line. Against HEAD, they add:
  - "steps" (row 29);
  - the tiebreak, in parentheses after the value it limits (row 32);
  - "Define each once" in place of "Define it once", whose "it" had three antecedents;
  - M1's source rule, limited by the boundary phrase (rows 31 and 33);
  - the source allowance ", or taking it from a source that code does not read," (row 40).

  "A shared test module" stays. A fixture file such as `conftest.py` is itself a shared test module, and step 5's second verdict on N14 tests that reading.

```markdown
Neither (1) nor (3) covers a second test file's copy of a helper or of setup steps whose details its assertions do not depend on, or a value two test files must keep equal, such as a delimiter, a size limit, or fixed text or a fixed number set in the code under test, even one the tests only assert. A result each test works out from its own input is not such a value. Define each once in a shared test module, spelling out a value the code under test emits or parses outside its process, or taking it from a source that code does not read, rather than deriving it from that code or from where that code gets it, per `test-conventions/SKILL.md` § "6. Test data".
```

  The first blind read missed the delimiter fixture (F1) and the fixed-text and fixed-number cases N2, N17 and N18. The clause after "keep equal" now names "a delimiter, a size limit, or fixed text or a fixed number set in the code under test, even one the tests only assert" and states the exclusion as its own sentence (row 41). A re-read watches P1, since "such as a delimiter" may wrongly catch its stand-in value.
- **M2a, `claude/.claude/CLAUDE.md` line 42.** In the "Discriminator literals where a canonical symbol exists" bullet, replace HEAD's clause `, unless importing it would make a test pass whatever the value` with the clause below.
  - It keeps the engineer's words "importing ... would make the test pass whatever the value" (row 25).
  - It names the site, a test, so it no longer reaches production code.
  - It names the subject, "that symbol": the canonical symbol the bullet's heading names.
  - It adds the boundary phrase (row 33), so it no longer reaches a value that never leaves the process.
  - HEAD already opens the next sentence with `Otherwise reach for`, and nothing else in that sentence changes.

  After the change, the end of the edited sentence reads:

```markdown
an enum, status, or code defined elsewhere, except in a test of a value the code under test emits or parses outside its process, since importing it from that code would make the test pass whatever the value.
```

- **M3, `claude-skills/skills/code-review/SKILL.md` line 113.** Replace everything from `Carve-out:` to the end of the line, the trailing citation included, with the text below. Against HEAD:
  - The flag sentence comes first, with its two-site threshold ahead of the verb so the verb meets its object without splitting the sentence.
  - The DAMP sentence comes last and opens with "Outside those cases", so the two no longer give opposite verdicts on setup copied across files.
  - It adds "steps", "fixed", "or only asserts it", the boundary phrase and the tiebreak sentence.
  - It takes M1's source rule for "such fixed text or number", with row 40's source allowance.
  - The allowance names "the code under test" in full, because that sentence holds no earlier antecedent for "that code".
  - "One shared definition" stays, because a fixture is one (row 39).

```markdown
Carve-out: in test code, at two sites and whatever the size, flag a second test file's copy of a helper or of setup steps whose details its assertions do not depend on, and a value two test files must keep equal, such as fixed text or a fixed number the code under test emits or parses outside its process, even when each file spells it inline or only asserts it. A result each test works out from its own input, such as `"3 items"` from `render(3)`, is not such a value. Point to one shared definition, spelling out such fixed text or number there, or taking it from a source the code under test does not read, rather than deriving it from that code or from where that code gets it, per `test-conventions/SKILL.md` § "6. Test data". Outside those cases test code is DAMP, so do not flag repeated inline arrange/assert blocks unless they obscure the test's intent.
```

- **M3a, `claude-skills/skills/code-review/SKILL.md` line 115 (item 9a).** Replace item 9a's text from `at 3 or more sites` to the end of the line with the block below. The block's last sentence carries M2a's site and boundary phrase, and the rest of the block matches the working tree's text.
  - The base is the working tree, not HEAD. There, item 9a's question ends `without a shared named type?`, the "Flag and suggest ... with call sites replaced by the named type." sentence follows, and an unreviewed sentence from an earlier review round ends the line. That sentence reads `Neither count nor replace a test's use when importing the type would make the test pass whatever the value.`, and the block's last sentence replaces it. [verified: plan-architect's read of the working tree's line 115]
  - HEAD's question instead ends `without a shared named type, unless importing it would make a test pass whatever the value?`, and nothing follows the "Flag and suggest" sentence. [verified: the platform review's `git diff HEAD`, relayed; plan-architect read only the working tree] The replaced span starts before that clause, so the edit gives the block's text from either state, and step 3 checks the result.

  The result reads:

```markdown
at 3 or more sites without a shared named type? Flag and suggest the language's idiomatic named-type construct (TypeScript string-literal union, Java/Kotlin/C# enum, Python `Literal[...]` or `Enum`, Rust enum, Go typed-string constant set) declared at the canonical module for that domain, with call sites replaced by the named type. Neither count nor replace a test's use of a value the code under test emits or parses outside its process, since importing the type from that code would make the test pass whatever the value.
```

- **M4, `claude-skills/skills/test-evaluation/SKILL.md` line 68.** Replace the row with the one below. Against HEAD, the fix cell takes M1's term "emits or parses" with the boundary phrase and its source rule, and points to § 6 for the rest. It carries neither the define-once half nor the tiebreak, because the row's label and symptom ("Test passes with stale copy") describe a test that copies production logic, not a value two test files must keep equal (row 41). The label and symptom stay (Out of scope). M4 takes neither row 40's source allowance nor a fixture (Alternatives).

```markdown
| Duplicating production logic in tests | Test passes with stale copy, drift | Call the code or use integration; spell out an expected value the code under test emits or parses outside its process instead of deriving it from that code or from where that code gets it, per `test-conventions/SKILL.md` § "6. Test data" |
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

- **M7, `CHANGELOG.md`.** Replace the committed M7 bullet with this one, in place, directly above the cap bullet of M2b (row 20). Against HEAD, it:
  - states the spell-out rule § 6 now gives every test, with the boundary phrase and the source allowance (row 40);
  - states the define-once rule, and that a second test file's copy of setup steps its assertions do not depend on is flagged the same way, in a sentence of its own;
  - states the tiebreak and the narrowed exception;
  - drops the claim that the discriminator-literal rule tells a test to spell a value out;
  - gains a sentence on when a shared fixture may hold setup (row 39), because a cheap per-test fixture that test files share was not plainly allowed before.

```markdown
- **A test may no longer take a value the code under test emits or parses outside its process from that code, and a test file may no longer copy a value another test file must keep equal.** Under `test-conventions/SKILL.md` § "6. Test data", a test spells out a value the code under test emits or parses outside its process, or takes it from a source that code does not read. A value two test files must keep equal is defined once in a shared test module, like a copied helper, and a second test file's copy of setup steps its assertions do not depend on is flagged the same way. Setup or a builder that test files share may be a fixture built fresh for each test, and only expensive setup may be built once for many tests. A result a test works out from its own input, and a stand-in value the scenario does not depend on, may still repeat across files. The global `CLAUDE.md` single-source-of-truth exceptions, `/code-review` item 9 and `test-evaluation`'s anti-pattern table now agree with that section. The `CLAUDE.md` discriminator-literal rule and `/code-review` item 9a now let a test of such a value spell it out instead of importing the production symbol.
```

- **M2b, the byte cap.** M2a's clause does not fit under 30,720 bytes. HEAD already holds every M2b edit except two: the hook's comment paragraph and the CHANGELOG cap bullet. The dispatch changes those two. Each other item below is verify-only: step 3 checks it, and the dispatch edits nothing there.
  - Change, `claude/.claude/hooks/check-claude-md-length.sh`: replace the comment paragraph from `# Byte limit:` through `# A raise past 32,768 bytes` (lines 47-54) with the block below.
    - The two Codex lines state the combined-size limit in place of "not verified" (row 34). They say "default", because `project_doc_max_bytes` is a consumer setting.
    - Line 48's "truncation" becomes "default", so the comment says nothing about Codex that M2c's quote does not, and step 4's re-fetch covers every such word.
    - The citation names both the size table and the `### OpenAI` entry, because the table's Codex row has no source link and the vendor's sentence is in that entry. The reflowed citation moves the wrap of the lines after it, and no other word of those lines changes.
    - No row of that table names a source entry, the Codex row after M2c included. A reader finds that row's source, M2c's entry, under the `### OpenAI` heading of the same file. [verified: `ai-instruction-and-memory-files/REFERENCES.md:120-133`]

```bash
# Byte limit: 31,744 bytes = 31 KiB (binary reading), a repo-owned ceiling
# under the 32 KiB Codex project_doc_max_bytes default
# (claude-skills/skills/ai-instruction-and-memory-files/REFERENCES.md's
# "Cross-vendor size table" and "OpenAI" sections; "OpenAI" quotes the vendor).
# Applies to every stow consumer's CLAUDE.md/AGENTS.md, the same scope the
# 200-line check above already has. The 31,744 figure is checked per file, but
# Codex stops adding files once an AGENTS.md chain's combined size reaches that
# 32 KiB default.
# A raise past 32,768 bytes needs a new basis, not only a log line below.
```

  - Verify only, the same file: `GLOBAL_CLAUDE_MD_BYTE_LIMIT=31744`, and the dated log's line below after the 2026-10-17 line. HEAD holds the line once, so do not append it again.

```bash
# 2026-11-21: 30720 -> 31744; the global CLAUDE.md needed room to state when a test spells out a value instead of importing it.
```

  - Verify only, `claude/.claude/hooks/tests/test_check_claude_md_length.py`: `BYTE_LIMIT = 31744`. The test that cross-checks the hook source keeps the two in step.
  - Verify only, `docs/hooks.md`: the `check-claude-md-length.sh` entry says "31,744-byte cap".
  - Verify only, `docs/design-decisions/global-claude-md-agent-core-and-main-session-groups.md`: lines 60, 141 and 164, which describe the current gate, say "31,744-byte", and line 141 carries no "(GH-1267)", because that issue set the previous figure. [verified: grep of that file this round]
    - A line that records a past event stays as written, and step 3 reports it to the engineer.
  - Verify only, `claude/.claude/hooks/tests/test_check_skill_length.py`: `test_byte_limit_never_fires_for_this_caller` (line 752) has no docstring, so delete nothing there. Its 40,000-byte fixture still exceeds the cap. [verified: read of lines 752-755 this round]
    - The removed docstring restated how the shell hook calls the shared gate, which the test name and the code already show, and it carried the cap figure.
    - [engineer-verified: "Fix by deletion. Do you see how the docstrijg is repeating how the code works?"] The tag covers deleting the docstring, not the choice of which docstring facts to keep.
  - Change, `CHANGELOG.md`: replace the committed cap bullet with this one, in place, directly below M7's bullet.
    - Against HEAD, its third sentence states Codex's combined-size limit in place of "not verified" (row 34). It names `ai-instruction-and-memory-files/REFERENCES.md` § "OpenAI" as where that limit is recorded, because `.claude/rules/changelog-entries.md` sends a reader to a living doc for how something behaves now.
    - A fifth sentence gives the room left to a chain of more than one file, as the gate's worst case ("one of them at the cap").
    - The older 25,600-to-30,720 bullet in that section stays as written.
    - The bullet:

```markdown
- **The `CLAUDE.md`/`AGENTS.md` byte cap that `check-claude-md-length.sh` enforces rises from 30,720 to 31,744 bytes for every stow consumer.** A denial needs the staged size to exceed both the limit and the committed size, so the raise only removes denials: a file that grows to a size between 30,721 and 31,744 bytes is no longer denied. The cap is checked per file, but Codex stops adding files once the combined size of the files it loads reaches its 32 KiB `project_doc_max_bytes` default, which `ai-instruction-and-memory-files/REFERENCES.md` § "OpenAI" records with the vendor's wording. The new figure is 31 KiB, leaving a single file 1,024 bytes below that limit. A consumer whose Codex chain has more than one file, one of them at the cap, now has 1,024 bytes below that limit for the rest of the chain, not 2,048.
```

- **M2c, `claude-skills/skills/ai-instruction-and-memory-files/REFERENCES.md`.** Approved by the engineer's answer on row 35. Two edits give the size table that the hook comment cites a vendor source (row 34):
  - Insert the entry below as the last bullet under `### OpenAI`, after the GPT-4.1 prompting guide entry and its closing paragraph, before `### Google`.
  - In the "Cross-vendor size table", replace the OpenAI Codex row (line 127) with the row below.

```markdown
- [OpenAI Codex — AGENTS.md guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
  — official vendor docs, fetched 2026-11-23. The page shows no
  last-updated date, and `developers.openai.com/codex/guides/agents-md`
  redirects to it. The limit covers the loaded files combined:

  > Codex "stops adding files once the combined size reaches the limit
  > defined by `project_doc_max_bytes` (32 KiB by default)"
```

```markdown
| OpenAI Codex — `project_doc_max_bytes` | 32 KiB (default), across the loaded files combined | Hard limit (Codex stops adding files) |
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
- **Two dispatches, the cap and Codex edits ahead of the engineer's answer on row 31.** Rejected: that group and M7 both edit `CHANGELOG.md`, so the file sets do not partition, which `plan-it`'s split rule requires. Waiting delays a comment correction and changes no behavior.
- **Verification, the code-writer applying item 9 to fixtures it built.** Rejected: the author of M3 would grade its own text with the key in its prompt, which shows nothing about what a fresh reader decides (Verification step 5).
- **§ 6 tiebreak, every asserted value inline.** Rejected: the engineer chose the shared-definition side (row 32). It would also narrow variant 2's approved "fixed text or a number the code under test emits", which reaches most tests through their assertions.
- **§ 6 bullet 2's fixture sentence, the earlier revision's "A shared fixture holds setup".** Rejected: that sentence states no cost limit, so cheap setup built once for many tests (N21) would pass, against variant 2's approved "expensive setup (DB schemas, server instances)", which M1 keeps for a fixture built once for many tests.
- **§ 6 bullet 2's fixture sentence, kept as variant 2 wrote it.** Rejected: a reader takes a fixture that tests in two files use as a shared fixture, so "Shared fixtures are for expensive setup" bars N14, which the engineer allowed (row 39). M1 keeps the sentence's limit on state that many tests share and its bar on simple data objects.
- **§ 6 bullet 2, a clause letting cheap setup be built once for many tests when no test changes it (N21).** Rejected (row 39): pytest builds a fixture for each test by default and gives cost as the reason to widen its scope, and § 4 already covers shared state that tests change.
- **§ 6 bullet 4, a rule that setup needing teardown goes in a fixture and anything else in a module.** Rejected: N7's imported `make_repo(tmp_path)` and N14's fixture hold the same setup, so a reader could not tell which form such a rule demands. Bullet 4 lets setup take either form.
- **M2, M3 and M4, renaming "shared test module" and "one shared definition" so each names a fixture, as the dispatching session proposed.** Set aside:
  - M3's "one shared definition" already covers a fixture.
  - M4's phrase governs only a value, and § 6 keeps values out of fixtures.
  - A fixture file such as `conftest.py` is itself a shared test module, so M2 needs no new bytes unless readers disagree. Step 5's second verdict on N14 tests M2 and M3, and a miss on M2 takes the fallback step 5 names.
- **M4, adding row 40's source allowance.** Rejected: the cell names the fix for a test that duplicates production logic, and a value taken from a source the code does not read duplicates none. Row 12's choice of "spell out" neither requires nor bars the allowance. Step 5's test-evaluation entries for N20 and N22 test this reading.
- **The independent review's key, "anything the code under test reads", at every site in place of "emits or parses outside its process".** Rejected, with its "prefer a canonical source", for the reasons row 40 gives.
- **§ 6, moving the spell-out sentence to bullet 4 instead of restoring that wording.** Rejected: bullet 4 describes the shared module, so the move would limit the spell-out rule to that module again, the conflict M1 removes.
- **§ 6 tiebreak, the reviewer's "a value the test did not choose for its scenario".** Rejected: a reader cannot tell whether a test chose the deny message it expects, while "set in the code under test" can be checked against the code.
- **Item 9, limiting the DAMP sentence to one test file, as the reviewer suggested.** Rejected: base item 9 would then flag, at three files, an arrange block whose details the assertions read, which § 6's bullet 2 lets repeat. Putting the flag sentence first and opening the DAMP sentence with "Outside those cases" removes the conflict without that gap.
- **Line 42 and item 9a, the reviewer's "a test asserting a value the code emits across a boundary spells that value out; every other site uses the named constant".** Rejected: it replaces the words row 25 records as the engineer's. M2a keeps them and adds the site, the symbol and the boundary.
- **The boundary as "wire, storage, display".** Rejected: an exit status, which this repo's hook tests assert, fits none of the three plainly.
- **The boundary as the list "through a file, a stream, an exit status or a display" at each site.** Rejected: three sites repeated the list while M1's bullet 3, line 25, item 9 and the test-evaluation row used the bare term, so their readers could not tell whether an in-process value was covered. An HTTP response, a stored row or a queue message also fits none of the list's items plainly. The phrase "outside its process" states the rule, and § 6 bullet 2 alone gives the list as examples.
- **Line 25's tiebreak as one word ("a fixed value two test files must keep equal").** Rejected: a test's own literal is fixed in the plain sense, so a reader who never loads § 6 could not apply the word. The explicit clause costs 54 more bytes.
- **New Codex sentences saying the limit truncates the chain.** Rejected: the page says "truncation" but not that content is dropped, so the new sentences use its words "stops adding files" (row 34).

**Assumption ledger.**

**Root:** Four rule texts disagree on whether test code may copy a helper or a value into a second test file (Context, "Why now"), so a copied named constant, or a value the code under test emits or parses, passes as acceptable repetition. The first shipped revision of those texts still conflicted, on the points the Approach's list of changed blocks names.

**Givens:**
- G1. The `test-conventions` skill loads only when its description's triggers match, so most sessions never read § 6. Reason: the harness's skill loading owns this, driven by the description at `test-conventions/SKILL.md:3-9`.
- G2. Two commit gates bind this change. `check-skill-length.sh` caps a SKILL.md at 200 lines by default. `check-claude-md-length.sh` caps a CLAUDE.md at 200 lines and, after M2b, 31,744 bytes (30,720 before). Each denies only a staged file that is over its limit and larger than its base. Reason: changing a cap is a separate decision with its own logged basis (`check-claude-md-length.sh:56-58`).
- G3. The quoted sources say what they say, including the tension between Meszaros and the Google chapter. Reason: their authors own them.
- G4. Codex stops adding instruction files once their combined size reaches `project_doc_max_bytes`, 32 KiB by default. Reason: OpenAI owns that limit (row 34).

**Mechanisms:**
- M1. § 6 lines 108-110 become M1's three bullets, whose roles M1's lead-in gives; lines 107 and 111 and the heading stay. anchors: row1, row4, row5, row30, row31, row32, row33, row39, row40.
- M2. A stand-alone exclusion of two sentences, the second carrying the citation, inside the CLAUDE.md bullet, now with M1's tiebreak, source rule and boundary phrase. A pointer alone fails G1, and the full list duplicates § 6. anchors: root, row2, row6, row7, row9, row10, row31, row32, row33, row40.
- M2a and M3a. A one-clause exception to the discriminator-literal rule (CLAUDE.md line 42) and to item 9a: a test of a value the code under test emits or parses outside its process need not import the symbol, when the import would make the test pass whatever the value. Naming the site keeps production code under the rule, and the boundary phrase keeps an in-process enum under it. anchors: row7, row25, row26, row31, row33, row38.
- M2b. Raise the CLAUDE.md byte cap so M2a fits, update every site that states the current cap, and state Codex's combined-size limit where the hook comment and the CHANGELOG bullet called it unverified, with the bullet citing where the limit is recorded. anchors: row7, row26, row28, row34.
- M2c. Give the size table the hook comment cites a vendor URL and quote for its Codex row. anchors: row34, row35.
- M3. A carve-out in item 9 that keeps the two-site, any-size rule, states the boundary as "must keep equal" in place of § 6's one-fact test (row 11), carries M1's tiebreak and boundary phrase, and puts the DAMP sentence last so it covers only what the flag sentence leaves. anchors: root, row2, row9, row11, row31, row32, row33, row40.
- M4. Relabel the test-evaluation row and replace its fix cell with the spell-out wording row 12 chose, now with M1's term, boundary phrase and source rule, closed by a pointer to § 6 that carries the rest (row 41). anchors: row9, row12, row13, row22, row31, row33, row41.
- M5. A new REFERENCES.md section with verbatim quotes and the draft caveat. anchors: row16, row17, row18, row19.
- M6. An in-place correction note under the design record's provenance line. anchors: row14, row15, row16.
- M7. One CHANGELOG bullet. anchors: row20, row31, row33, row39, row40.
- M8. One `code-writer` dispatch for all fourteen files, eight changed and six verify-only, after the engineer approves this round's texts. anchors: root, row21, row31, row35.

**Rows:**
1. Variant 2 is § 6's final wording, and a builder-default stand-in value may repeat across files. [engineer-verified: "yes to both"] The quote answered both questions in the prior session, and the Ask line records it. It covers only those two points.
2. The engineer approved the boundary variant 2 draws: two items are one fact "when a change to one would have to be made to the other". [engineer-verified: "this wording sounds good to me"] The compact restatements in M2, M3, M6 and M7 are this plan's wording, not the engineer's.
3. A mechanical check and an edit pass over existing comments are excluded. [engineer-verified: "a separate follow-up"]
4. § 6 is the heading at line 105 and five bullets at lines 107-111. Line 111 equals variant 2's fifth bullet byte for byte, so four lines change and the line count holds. [verified: `git show origin/main:claude-skills/skills/test-conventions/SKILL.md`, lines 105-111]
5. The file sits at its 200-line cap, and the skill gate's default limit is 200. [verified: dispatch evidence for the count; check-skill-length.sh:143 for the default] A net-zero edit passes, because the gate denies only growth past the limit. [verified: _lib.sh:3237-3243]
6. The CLAUDE.md gate also covers `claude/.claude/CLAUDE.md` with a byte ratchet, 30,720 before M2b and 31,744 after. The hook that runs in this session is the main checkout's copy, which stays at 30,720 until the main checkout pulls the raised hook (row 28). [verified: the main checkout's check-claude-md-length.sh:59,131; _lib.sh:3244-3253]
7. `claude/.claude/CLAUDE.md` byte figures, against the cap M2b raises to 31,744. Verification step 1 re-measures before and after the edit.
   - A review edit that pushes the file past 31,744 needs a matching deletion elsewhere in the bullet, not another cap change.
   - A review edit that grows the file past HEAD goes to the engineer's terminal (row 28).
   - The reason for the second rule: until the raised hook reaches the main checkout, the session's own gate denies any staged edit that grows the file past HEAD and past 30,720 bytes.
   - The branch adds 838 bytes to `claude/.claude/CLAUDE.md` over its merge-base blob. After the rebase onto origin/main the merge-base blob is 30,709 and the committed file is 31,547, which is 197 under the 31,744 cap. [verified: `git cat-file -s` on `origin/main:claude/.claude/CLAUDE.md` and on `HEAD:claude/.claude/CLAUDE.md`]
   - Step 5's N14 and N23 fallback for M2, " or, for setup, a fixture", would add 25.
8. No test or eval pins any wording this plan replaces. Two searches back this, each over `**/*.py` and `test-conventions/evals/trigger-cases.json`:
   - Old § 6 phrases "Carve-out", "test code is DAMP", "named test helper", "Import or call via integration", "Duplicating production", "Named exceptions" and "bad abstraction". The only hits are test docstrings using the word DAMP. [verified: the grep]
   - M2a and M3a phrases "never embed a raw", "canonical symbol", "domain discriminant", "3 or more sites" and "Discriminator literals". The only hits are the two edited lines and `code-review/SKILL.md:487`. [verified: the grep]
   - `code-review/REFERENCES.md:19` also matches the second search and maps item 9a to the bullet by name only.
   - This closes Context's pending checks (a) and (c).
   - The phrases the last two revisions replace or add ("Spell out a value", "shared test-helper location", "whatever the value", "Hard truncation", "combined-size", "is not verified here", "Define it once", "project_doc_max_bytes truncation", "a file, a stream", "outside its process", "whatever its size") have no hit in any `.py`, `.json` or `.sh` file except the hook comment M2b replaces. [verified: plan-architect's grep this round for the last five; an earlier grep for the rest]
9. Every new citation names a `SKILL.md` file as its target, never a bare `test-conventions`. Outside the skill's directory the target is `test-conventions/SKILL.md`. Inside it (M5) the target is the sibling `SKILL.md`. A citation in a SKILL.md or its REFERENCES.md must resolve, and a target with no `/` resolves only as a same-directory sibling. So `` `test-conventions` `` fails, while `` `test-conventions/SKILL.md` `` resolves through the skill-directory branch. The citation pattern is not anchored to a line start, so M4's citation inside a table cell is extracted too. "6. Test data" survives heading normalization. [verified: test_skill_citation_grammar.py:76-97; _skill_md_helpers.py:229,290-330; claude/.claude/tests/helpers.py:157-191]
10. CLAUDE.md files, rule files and the doc corpus get an extraction check only. A hard-wrapped or no-space citation there fails the suite, but an unresolvable target does not. `CHANGELOG.md` is outside the doc corpus and is neither a CLAUDE.md nor a rule file, so M7's citation gets no check at all. [verified: test_skill_citation_grammar.py:136-172, 481-499; _skill_md_helpers.py:543-567] Verification step 3 pins the M2, M6 and M7 citations to the plan's exact text instead.
11. Item 9's base threshold is three sites. Today's carve-out flags a cross-file test-helper copy at two sites whatever its size, including a copy whose body differs when a fix to one would have to be made to the other. [verified: `git show origin/main:claude-skills/skills/code-review/SKILL.md`, line 113]
   - M3 keeps the two-site threshold for test copies. Without it the three-site default would govern them.
   - M3 drops the differing-body rule. Its helper and setup clauses take M2's grammar and carry no "when a change to one copy ..." condition.
   - M3's value clause says "must keep equal" and "even when each file spells it inline". The original trailing "when a change to one copy ..." let a blind reader pass a delimiter spelled inline in two test files.
   - The reworded text matched the key on every fixture. [verified: Verification step 5's item 9 reads, run before row 29 changed the setup clause and the F3 and P3 cases] Step 5 re-runs the item 9 reads on M3 as this round leaves it.
12. Line 68's fix cell spells out expected values instead of importing them from the code under test, rather than the earlier draft's "assert expected literals inline". [engineer-verified: "Spell out values, don't import (Recommended)"] The tag covers only that choice between the two wordings. The choice settles both conflicts with variant 2. Today's "Import" contradicts its fourth bullet. The draft's "inline" contradicts its third bullet, which forbids a value "named or pasted inline" in a second test file. [verified: Context's variant 2 block]
13. test-evaluation's row reads "Duplicating production code in tests | Test passes with stale copy, drift | Import or call via integration". [verified: `git show origin/main:claude-skills/skills/test-evaluation/SKILL.md`, line 68] This closes the line-68 part of pending check (b).
14. Line 3 of a design record is its italic provenance line. A record that a later change overturns gets a note immediately under that line. Tests check line 3, reject a stray "Formerly" fragment anywhere else, and resolve relative markdown links. [verified: .claude/rules/design-decisions.md:16-32; test_design_decision_files.py:268-338, 484] M6 carries no "Formerly" and no markdown link.
15. The record calls test code DAMP "rather than DRY" (line 9) and DAMP "a mid-2010s community term with no single canonical author" (line 14). Its exceptions paragraph also lists the small-duplicated-value exception that M2 narrows. [verified: `git show origin/main:docs/design-decisions/single-source-of-truth-rule.md`, lines 9 and 14] This closes the rest of pending check (b).
16. Every quote in M5 and M6 is verbatim from the copies Context's edit 5 calls "grep-checked local text copies of the pages". Non-breaking spaces and HTML entities are normalized, and one footnote marker is dropped. [verified: swe-ch12.txt:587,672,707,837; tott-damp.txt:1081,1089,1135; jf-dry-damp.txt:861,875; xu-LiteralValue.txt:78,136-137; xu-root.txt:122-124]
17. The Literal Value page links to itself as `Literal Value.html`, and `/LiteralValue.html` returned 404. [verified: xu-LiteralValue.html:363; 404-xu-LiteralValue.txt:6] The ToTT and Fields URLs come from each page's own Blogger widget path. [verified: tott-damp.txt:6189; jf-dry-damp.txt:3194] The ch. 12 URL is the one REFERENCES.md already cites. [verified: REFERENCES.md:27]
18. The xunitpatterns.com pages say they are out of step with the printed book, and the Literal Value page points to page 714. [verified: xu-root.txt:122-124; xu-LiteralValue.txt:78] REFERENCES.md's earlier sections cite four such pages with no caveat. [verified: REFERENCES.md:10,15,18,37] M5's caveat covers every such page in the file, so those sibling citations need no edit.
19. § 2 lists test infrastructure as a recognized test-first exception, while ch. 12 says shared test infrastructure "must always have its own tests". [verified: test-conventions/SKILL.md:35; swe-ch12.txt:837] M5 records the caution, and Out of scope says why § 2 stays.
20. A CHANGELOG bullet belongs in this PR. [engineer-verified: "Add CHANGELOG bullet (Recommended)"] The tag covers only adding the bullet. M7's text is this plan's wording (row 2). The precedent is that `### Changed` under `## [Unreleased]` records rule changes to review skills and prose rules. [verified: CHANGELOG.md:145,172,186] Entries run newest first. Entries merged from main after this branch's bullets landed now sit above M7's bullet, at lines 9 and 17 of the working tree's file. [verified: CHANGELOG.md:5-24] M7's bullet therefore stays in place, directly above the cap bullet, and no step checks its position among main's entries.
21. No other skill, agent or doc restates the boundary. `code-review/REFERENCES.md:18` maps item 9 to the single-source-of-truth bullet by name only. `staff-sdet.md:60` cites § 6 by number, which the unchanged heading keeps valid. [verified: grep of `*.md` outside `.claude/plans/` for "DAMP", "bad abstraction" and the § 6 phrases]
22. M4's exact row text, closing clause included, stays as written rather than being trimmed or paired with a new row. [engineer-verified: "A: keep row, fix key (Recommended)"] The question showed the full row text and the blind-read results for both options. The tag covers only keeping that row as written, and the row's wording is this plan's. Verification step 5's test-evaluation key follows what the row flags.
23. § 6's variant 2 wording is kept as approved after the first review round. [engineer-verified: "Keep as approved (Recommended)"] The question asked whether to reopen § 6 over an overlap between its stand-in and copied-builder rules. The tag covers only keeping § 6.
24. Two edits are applied. M2 and M3 gain a clause that a shared test value is spelled out there, never derived from the code under test. M5's Meszaros note names helpers and setup as well as values. [engineer-verified: "Apply both (Recommended)"] The question described both as accuracy fixes. The wording of the M2 and M3 clause and of the M5 sentence is this plan's, not the engineer's.
25. Flag the exception clause of M2a and of M3a in the PR description. It narrows a rule in the always-loaded `CLAUDE.md`.
    - The `CLAUDE.md` discriminator-literal bullet (line 42) and `/code-review` item 9a told a test to import the production symbol, which contradicts § 6's rule to spell out a value the code under test emits or parses.
    - The round-3 review raised the contradiction.
    - The engineer handed the scoping decision to the plan-architect: "Ask the architect please. I am concerned about internal contradictions among prose rules".
    - The architect first chose the scope phrase "outside test code". The engineer asked for the reason, a test that would be vacuous, to be stated in place of a scope phrase, and the architect's second consult proposed the clause. [verified: both architect consult returns]
    - Keeping both edits in this PR is the engineer's call. [engineer-verified: "Keep both, quote is mine (Recommended)"] The tag covers only keeping M2a and M3a.
    - The engineer chose the clause's wording. [engineer-verified: "Yeah, I think you should use when importing. It would make the test pass whatever the value."] The tag covers the idea and its words. "A test" for "the test" and the placement are this plan's.
    - The engineer decided that scoping the bullet's next sentence belongs in this PR. [engineer-verified: "I actually think it's within scope of this PR because the change this PR introduces exposes the defect of the preexisting prose"] The tag covers that scope decision. A later architect consult advised leaving the sentence unchanged, and the engineer decided otherwise. The one word "Otherwise" is this plan's wording.
    - This round's M2a and M3a keep the engineer's words "importing ... would make the test pass whatever the value" and add the site, the symbol and the boundary (row 33). That revision goes to the engineer first, per step 5.
26. The CLAUDE.md byte cap rises from 30,720 to 31,744 bytes (M2b). [engineer-verified: "Yes, I agree that number of bytes that you suggest is reasonable. Okay, let's go with that."] The tag covers the 31,744 figure, which the engineer had been offered with its 31 KiB basis.
   - The change list (the hook, its test, `docs/hooks.md`, the two other sites that state the cap, and a CHANGELOG bullet) is this plan's.
   - The engineer also gave the reason for accepting the raise. [engineer-verified: "I'm honestly okay with you also increasing the claude.md cap, because we're just talking about a handful of bytes, and I'm already working on a huge reduction in another session to offload the main session text."] [engineer-verified: "this is not the time to worry about the claude.md limit. I would raise it."]
   - The two tags cover only that statement and that direction. They do not show that the reduction exists or lands.
   - The engineer was shown a path-scoped rules file as the alternative to keeping the line 25 clause in `CLAUDE.md`, and kept it in `CLAUDE.md` with the 31,744 cap. [verified: the SETTLED row for `claude/.claude/CLAUDE.md:25` in this branch's review history] [engineer-verified: "I kept the claude in CLAUDE.md"]
   - The engineer's reason: [engineer-verified: "it wasn't a good idea to keep a rule in a different place than its exception"]. The two tags cover keeping that clause in `CLAUDE.md` and that reason.
27. The docstring in `test_consume_durable_continuity_file_on_read.py` stays unchanged. The test derives the event name from the registry (`settings.json`), not from the code under test, so deriving is not vacuous and the discriminator-literal rule it cites still applies after M2a. [engineer-verified: "Leave it alone (Recommended)"] The tag covers only leaving it. The session's earlier claim that the citation would go stale was wrong. This round's M2a leaves that unchanged, because deriving the name from the registry does not make the test pass whatever the value.
    - That claim was checked against M2a only, before M1 put the spell-out rule on every test.
    - The hook prints its own hardcoded event name and never reads `settings.json`. [verified: consume-durable-continuity-file-on-read.sh:145; test_consume_durable_continuity_file_on_read.py:32-43] So by M1's words the registry is neither the code under test nor where that code gets the value, and M1 does not bar the derivation.
    - The engineer agreed that N20 is allowed under § 6 (row 39), and M1's bullet 2 now says a source the code under test does not read is allowed (row 40). Fixture N20 reads that shape under § 6 and M2a.
28. The session's gate denies this round's `CLAUDE.md` commit, and the engineer makes that commit outside the gated session. [engineer-verified: "You commit it (Recommended)"] The tag covers only who commits. The evidence for the denial:
    - The installed hook `~/.claude/hooks/check-claude-md-length.sh` resolves to the main checkout's copy, which reads `GLOBAL_CLAUDE_MD_BYTE_LIMIT=30720`. [verified: `readlink -f` and `grep -n '^GLOBAL_CLAUDE_MD_BYTE_LIMIT'` on that path]
    - That copy still reads that limit this round. [verified: grep of the main checkout's `check-claude-md-length.sh`, line 59, this round]
    - The gate denies a staged file that is over the limit and larger than HEAD. [verified: `_lib.sh:3115-3118,3250`]
    - The committed `CLAUDE.md` is over 30,720 bytes after the engineer's earlier commit, and this round's result is larger than that (row 7).
29. The setup clause in M2 and M3 reads "setup steps whose details its assertions do not depend on", with "whose details" restored. [engineer-verified: "Restore 'whose details' (Recommended)"] The tag covers the choice to restore the phrase at both sites. The exact clause is this plan's wording, drawn from an architect consult. So are the code-shaped key cases F3, P3 and their M2 counterparts, which replace the earlier cases that described the setup in abstract terms.
    - The engineer chose to judge setup dependence per step. [engineer-verified: "Switch to per step (Recommended)"] The tag covers only that choice. It replaces an earlier answer, "Judge the whole paste (Recommended)", which answered a narrower question about one assertion reading back one value. [unverified: the question's exact text]
    - Per step is the literal reading of § 6's bullet 3, which says "steps". M2 and M3 now say "setup steps" too, so they carry the same reading. The per-step choice changes no § 6 text. These readings are this plan's, drawn from an architect consult, not the engineer's.
    - Before this round, two fresh `general-purpose` agents each read § 6's bullet 3 (`test-conventions/SKILL.md:109`, "setup steps whose details ...") against the earlier F3 and P3 fixtures, and both matched the earlier key. [verified: two fresh `general-purpose` reads in that session] Step 5 now reads M1's § 6 on its own key. Fixture N6 probes per-step judgment with unread steps, and N19 with prerequisite steps the stub needs but never inspects.
30. After an adversarial review of the shipped wording, the engineer widened the Ask to fix conflicting guidelines among these texts, pre-existing ones included. [engineer-verified: "I think now is the time to fix it, even if it takes a little longer for us to do that."] The tag covers that direction and approves no wording. This plan takes the review's points on § 6's internal conflicts, the source of a spelled-out value, the setup rule, the discriminator-literal exception and the Codex limit. The dispatching session takes the review's other points to the engineer separately (Out of scope).
31. M1 and this round's M2, M2a, M3, M3a, M4 and M7 are this plan's proposal. [engineer-verified: "Approve wording (Recommended)"] The tag covers approving the wording as the engineer saw it after the blind reads in row 42, M7's text excepted, which the engineer was not shown. All but M7 reopen text that rows 1, 22, 23 and 25 record as the engineer's decisions. The review ledger also records the item 9, `CLAUDE.md` line 25 and 42, and test-evaluation fix-cell texts as settled. [verified: the SETTLED rows for those four sites in this branch's review history] The dispatching session routes a change to any of them to the engineer. Critical files gates the dispatch on that answer.
    - M7 is in scope because it restates M1's boundary phrase and source allowance to every stow consumer. A change the engineer makes to either carries into M7 in the same edit.
    - Step 5's changed key entries go to the engineer with this answer. So do its new N16, N17, N18 and N23 entries (step 5).
32. The tiebreak between § 6's bullets 2 and 3: fixed text or a fixed number set in the code under test falls under bullet 3 even when tests only assert it, and a result each test works out from its own input falls under bullet 2 and may repeat. The engineer selected this side. [engineer-verified: "Shared definition (Recommended)"] The tag covers the choice of side and approves no wording.
    - Variant 2's bullet 3 names "fixed text or a number the code under test emits or parses" and "a message", which reach most tests through their assertions. [verified: Context's variant 2 block]
    - Under this side, two test files of one hook that each assert its exit code share one definition. The hook tests hold 223 `returncode == 2` assertions across 23 files. [verified: a grep of `claude/.claude/hooks/tests` this round] The one-fact test leaves out files that test different hooks, and moving the rest belongs to the row 3 follow-up. [unverified: how many of those files test the same hook]
    - Reversing the side would flip N2, N17 and N18 in every step 5 key and change the texts to match.
33. The boundary phrase "emits or parses outside its process" is this plan's wording. So is the example list "(such as through a file, a stream, an exit status or a display)", which only § 6 bullet 2 carries. Every other site that names the boundary uses the phrase alone.
    - The phrase keeps § 6's term "emits or parses".
    - It states the rule the list illustrates, so an enum compared inside the process keeps its named constant.
    - For the same reason, a channel the list does not name, such as an HTTP response, a stored row or a queue message, still counts.
    - [unverified: that fresh readers apply the phrase consistently; step 5's N5, N5r, N11, N12, N13 and N18 entries test it]
34. Codex "stops adding files once the combined size reaches the limit defined by" `project_doc_max_bytes` "(32 KiB by default)". [verified: the dispatching session's fetch of https://learn.chatgpt.com/docs/agent-configuration/agents-md, the 308 redirect target of https://developers.openai.com/codex/guides/agents-md, relayed to plan-architect, which did not fetch the page] [engineer-verified: "Yeah, sure. Verify the finding five against the vendor page."] The engineer's tag covers verifying against the page.
    - The page shows no last-updated date. It says "truncation" but not that content is dropped, so the new texts say "stops adding files". The hook comment's own "truncation" becomes "default" (M2b) for the same reason.
    - With one file at the 31,744 cap, the rest of a chain has 32,768 - 31,744 = 1,024 bytes before that limit, against 2,048 under the old cap.
    - This supersedes the last review round's deferral of the unsourced Codex row, per the dispatching session.
35. `claude-skills/skills/ai-instruction-and-memory-files/REFERENCES.md` is outside the approved file list, so adding it needs the engineer's answer first. The engineer answered yes. [engineer-verified: "Add it (Recommended)"] The hook comment cites that file's size table as its source, and the table's Codex row has no URL or quote. [verified: check-claude-md-length.sh:47-50; REFERENCES.md:120-127] Row 34's tag covers verifying the claim, not editing this file.
36. This round's changed scope (M1, M2, M2a, M3, M3a, M4, M2b's comment, M2c and the three changed fixture answers) goes to review. [engineer-verified: "Proceed on this scope (Recommended)"] The tag covers proceeding to review and approves no wording; row 31 still gates the wording.
37. The Ask line's two quotes from the earlier session are the engineer's words. [engineer-verified: "Yes, my words"]
38. Step 5's role-label fixture L1, a label defined only in test helpers, not in production code, takes the shared-definition verdict: line 42 requires importing the helper's constant, and item 9a flags the raw uses. [engineer-verified: "let's go with your recommendaion"] The tag covers choosing the dispatching session's recommendation for that fixture. The reason is the dispatching session's, not the engineer's: importing the label from a helper module cannot make a test pass whatever the value, so the exception M2a and M3a add does not excuse repeating it inline.
39. The step 5 verdicts on the fixture and registry cases. The engineer answered the plan's three verdicts, N14 not allowed, N15 allowed and N20 allowed. [engineer-verified: "I think I agree with #1-#3"] The engineer then asked for an independent check. On the one case where that check disagreed with the plan, N14, the engineer selected a label. [engineer-verified: "Allow function-scoped fixture (Recommended)"] The second tag covers that choice only and replaces the first answer for N14. The wording that carries it is this plan's and stays a proposal (row 31).
    - N14, a `conftest.py` fixture with the default per-test scope that runs a two-line `git init` in a fresh temporary directory, used by tests in two files: allowed under § 6.
      - The reason is the dispatching session's proposal, not the engineer's. Cost limits a fixture built once for many tests, not whether a fixture built fresh for each test may hold a shared definition. Variant 2's bullet 4, "a plain module that every consuming test imports", cannot cover a fixture file. [unverified: the reason as the option described it]
      - M1 carries it in two places. Bullet 2's fixture sentence limits only a fixture built once for many tests to expensive setup, and bullet 4 lets setup be a fixture.
    - N15, a `conftest.py` fixture creating a database schema once per test session for tests in two files: allowed under § 6, by bullet 2's fixture sentence. The first tag covers this verdict.
    - N20, a value taken from a registry the code under test never reads: allowed under § 6. Line 42 does not require importing a symbol for it (row 41, which replaces the earlier "required under line 42"). The first tag covers the § 6 verdict. M1's bullet 2 now says such a source is allowed (row 40).
    - N21, new: the same cheap `git init` in a fixture built once per test session, with tests in two files sharing that one repository and no test or stub changing it: not allowed under § 6. Bullet 2 gains no clause for it. The engineer handed the verdict to plan-architect's consult, whose recommendation this plan adopts. [engineer-verified: "Ask the architect. What is best practice here. I want to follow standard practice and not guess"] The tag covers that delegation and approves no wording (row 31). The verdict follows standard practice as these sources state it:
      - pytest gives each test its own fixture result by default, so "each test gets its own fresh batch of data and is starting from a clean state". It gives cost as the reason to widen a fixture's scope: fixtures that need network access are "usually time-expensive to create", and one instance shared across a module's tests is "thus saving time". Its wider-scope example shares state once "the tests are free to make as many non-state-changing queries as they want without risking stepping on the toes of the other tests". [verified: the dispatching session's re-fetch of https://docs.pytest.org/en/stable/how-to/fixtures.html, which confirmed each quote verbatim, relayed to plan-architect, which did not fetch the page]
      - Meszaros's Obscure Test page, on a fixture built for many tests' needs, puts a fresh fixture first and a shared one second: "This can best be done by using a Fresh Fixture for each test. If we must use a Shared Fixture we should consider applying the Make Resource Unique (page X) refactoring". URL: http://xunitpatterns.com/Obscure%20Test.html, the name the page's own links use. [verified: xu-ObscureTest.txt:372; xu-ObscureTest.html:858] [unverified: the printed book's wording, because the page is a pre-publication draft (row 18)]
      - N21's description says no test or stub changes the repository, so the fixture tests cost alone. Shared state that tests change is already § 4's concern: "Tests must be independent" says each test "creates its own data", and "Parallel-safe tests" bars a test that mutates module-level state from running in parallel. [verified: test-conventions/SKILL.md:68-71,83]
      - A strict reading of "expensive" also flags existing fixtures. The repository holds 23 `scope=` declarations wider than function across 17 Python files, and some are cheap and read-only, such as the two locale-probe booleans at `test_respond_pr_lib.py:56-63`. [verified: plan-architect's grep of `*.py` for `scope=` set to session, module, class or package, this round, and a read of those lines] Changing existing tests is the row 3 follow-up, and step 8 puts the count in the PR body.
    - N10, a `conftest.py` fixture returning a simple dict that tests in two files use, keeps its "not allowed" verdict. Bullet 2 keeps simple data objects out of every fixture, per-test ones included, so N14's change does not reach it.
40. An independent read-only review of HEAD's texts, not of this plan, suggested keying the tautology guard on whether the code under test reads the test's source: "never take an expected value from anything the code under test reads; prefer a canonical source it does not read". Those words are the reviewer's, not the engineer's. [unverified: relayed by the dispatching session; plan-architect did not read the review]
    - Its under-forbid case, a value the code imports from a module that is not itself the code under test, holds against HEAD's § 6 bullet 4, which bars only "importing it from the code under test". [verified: test-conventions/SKILL.md:110] M1's "or from where that code gets it" already closes it, and N9 probes it.
    - Its over-forbid case, N20, holds against M1 as last drafted. That draft's head verb "Spell out" barred a value taken from a registry the code never reads, which line 42 requires and the engineer allowed (row 39). This revision adopts that half. M1's bullet 2, M2, M3 and M7 add "or take it from a source that code does not read" in each site's grammar.
      - It extends the clause row 24 records, so it goes to the engineer with row 31. [unverified: the engineer's answer]
      - M4 does not take it (Alternatives).
    - Its key, applied to every expected value in place of "emits or parses outside its process", is rejected. Every site keeps the boundary phrase and the source allowance. The engineer handed the choice to plan-architect's consult, whose recommendation this plan adopts. [engineer-verified: "Ask the architect"] The tag covers that delegation and approves no wording (row 31).
      - The key would bar a test from importing an in-process enum member the code reads (N5, and N5r under line 42). A wrong member still fails that test, so the import does not "make the test pass whatever the value", the engineer's trigger for line 42's exception (row 25). Line 42 therefore requires that import, and § 6 would forbid it.
      - The key would also bar a round-trip test, because its expected value is the test's own input, which the code under test reads. A change in the code still fails such a test.
      - The review's word "prefer" is not adopted either. It would rank a canonical source above spelling the value out, while ch. 12 puts spelling out first: once Example 12-16 writes the expected URL out in full, the chapter calls duplicating the base URL "a small price to pay for making the test more descriptive and meaningful". [verified: swe-ch12.txt:505-532, Examples 12-15 and 12-16 of https://abseil.io/resources/swe-book/html/ch12.html] M1 keeps "Spell out" as its head verb and allows the source as the alternative.
      - Agreeing with line 42 leaves a gap that Out of scope records: no edited text bars a test from deriving, with logic, an expected value the code under test keeps inside its process.
    - The review also separated three questions the texts fused: whether two items are one fact, whether a shared definition is a fixture or an imported module, and how long a fixture lives. M1 states each once, in bullet 3, bullet 4 and bullet 2's fixture sentence.
41. Blind-read round one failed three texts, and the engineer answered three decisions on a plan-architect consult. [engineer-verified: "Change key (Recommended)"] [engineer-verified: "Pointer to § 6 (Recommended)"] [engineer-verified: "Allow builder (Recommended)"] Each tag covers its choice only and approves no wording (row 31).
    - Line 42's key for N20 becomes "does not require it". All four reads said so, because the test holds no raw literal. Fable's review found the entry then tests nothing, so N24 and N26 were added (row 42, below).
    - M4 becomes a pointer to § 6 and drops the define-once half and the tiebreak. This supersedes row 22's "keep row as written" for the fix cell, and reopens the test-evaluation fix-cell texts the review ledger records as settled. The label and symptom are unchanged. The test-evaluation key's N2, N17, N18 and two-file-constant entries become "does not apply".
    - § 6 bullet 2 allows a fixture to return a builder for a simple data object, never the object itself. Bullet 4 lets setup or a builder be a fixture. N10, a fixture that returns a dict, stays not allowed. N23 becomes allowed.
    - M2 gets the tiebreak and the delimiter example as its own clause (the plan-architect consult's wording, this plan's proposal). The first reads showed line 25 missing N2, N17, N18 and F1.
    - Row 27 leaves the docstring in `test_consume_durable_continuity_file_on_read.py` unchanged. It stays accurate under M2a's changed connective (row 42), so no docstring change goes to the engineer.
42. Fable's adversarial review of row 41's choices and a second plan-architect consult led to these answers. [engineer-verified: "Add twin fixture (Recommended)"] [engineer-verified: "State the limit (Recommended)"] [engineer-verified: "Finish this round, then freeze (Recommended)"] [engineer-verified: "Allowed (Recommended)"] [engineer-verified: "Change connective (Recommended)"] [engineer-verified: "Re-describe as a control (Recommended)"] [engineer-verified: "Build N26, keep N24 control (Recommended)"] Each tag covers its choice only and approves no wording (row 31).
    - N24, the raw-literal control for N20: one test asserts the raw event name `"document.saved"` the stub prints, with no registry file. Under M2a's changed connective, line 42 does not require importing a symbol (the stub is the only definition of the name, so importing is value-blind), and § 6 allows it. The consult's reason: M2a's exception now rests on the tautology as its reason, not as a condition, so line 42 no longer ranks a registry above spelling the value out (row 40). Recorded as a control, not a twin: it cannot detect a connective revert. [engineer-verified: "Re-describe as a control (Recommended)"] The tag covers recording N24 as a control, read against the question that showed it.
    - M2a and M3a swap one connective. M2a's plan-drafted `where importing that symbol would` becomes `since importing it from that code would` (HEAD's own text reads `unless importing it would make a test pass whatever the value`), and `when importing the type would` becomes `since importing the type from that code would`. The engineer's words "importing ... would make the test pass whatever the value" stay (row 25).
    - N25, a no-argument builder fixture (`make_user()`) whose default the assertion depends on: not allowed under § 6. The consult's reason is that bullets 1 and 2 already bar it, so the fixture probes a reading risk. Bullet 2 now adds "The test body passes that builder every value its assertions depend on."
    - N16 stays allowed. Bullet 2 adds "with none of that input in it" to the fixed-text clause, so a result that contains the test's own input stays a chosen value, as `"3 items"` from `render(3)` does.
    - Blind-read results for this round (the key and splits live in the scratchpad's `results/proposed4.json`, with the HEAD baseline in `head2.json`): both reads matched the key on the 30 § 6 fixtures read (N26's § 6 verdict was not read). Splits on item 9 (P3, F5, N18), line 25 (N16, N19) and line 42 (N11) were each broken by one more fresh read that matched the key, run in-session. [unverified: the third reads ran in-session and were not saved; the scratchpad results files show the splits and the final scoring only] The HEAD baseline differs from the key on N2, N17, N18 (line 25), N16, N14, N23 (§ 6) and N11 (line 42). N24 and N25 read the same at HEAD and are controls.
    - N26 was built as the twin of N20 and read four times, two at HEAD's `unless` text and two on the proposed `since` text. All four said "does not require" on line 42. The readers took the stub's own `EVENTS` dict as the only definition, so importing it is value-blind under either wording, and treated the test-side registry file as not the canonical symbol. No fixture in the key separates M2a's old condition from its new reason, so that swap is argued, not measured. [verified: four fresh reads on `fixtures/c54`, saved in the scratchpad's `results/n26_line42.json`] The same gap holds for M3a's swap. N26 differs from N24 only by a registry file no test or stub reads, so it proved a second control, not a discriminating twin, and no fixture in the key discriminates; step 8 puts that in the PR body. The wording stays as approved, because the engineer chose the connective (this row) and the swap narrows nothing the key measures.
    - The wording is frozen after this round. Making § 6 the only statement, with item 9, 9a, line 42 and test-evaluation as pointers, goes to the engineer as a separate decision afterward. M2's omission of "outside its process" in its tiebreak clause stays, because N18 is in-process.

## Critical files

One `code-writer` dispatch covers all fourteen files in one phase. It waits for the engineer's answer on this round's texts (row 31). Every replacement text is prescribed in Approach, and all of them rest on the same boundary wording (rows 1-2 and 31-33).
- Eight files change this round: `test-conventions/SKILL.md`, `claude/.claude/CLAUDE.md`, `code-review/SKILL.md`, `test-evaluation/SKILL.md`, the hook, `CHANGELOG.md`, `ai-instruction-and-memory-files/REFERENCES.md` and `code-file-size-exceptions.toml`.
- The dispatch prompt names the other six as step 3 checks only, so the code-writer edits none of them (M2b).

The dispatching session runs Verification step 5 before that dispatch, on texts it assembles from this plan's blocks, so the engineer answers row 31 with the read results in hand. Step 5 stays with the dispatching session because the agent that writes the texts cannot also be their blind reader. The dispatch runs Verification steps 1-4 and reports each result, with the path of step 3's script.

- `claude-skills/skills/test-conventions/SKILL.md`: lines 108-110 (M1).
- `claude/.claude/CLAUDE.md`: line 25 (M2) and line 42 (M2a). The engineer commits this file from their own terminal, because the session's gate still caps it at 30,720 bytes (row 28, Verification step 7).
- The cap files, per M2b. This round changes only the hook's comment paragraph; the rest are verify-only.
  - `claude/.claude/hooks/check-claude-md-length.sh`
  - `claude/.claude/hooks/tests/test_check_claude_md_length.py`
  - `docs/hooks.md`
  - `docs/design-decisions/global-claude-md-agent-core-and-main-session-groups.md`
  - `claude/.claude/hooks/tests/test_check_skill_length.py`
- `code-file-size-exceptions.toml`: the `ceiling` for `claude/.claude/hooks/tests/test_check_skill_length.py` goes from 1472 to 1468. `test_code_file_size.py` printed 1468 after the rebase onto origin/main. [engineer-verified: "Add it to the PR (Recommended)"] The tag covers only adding this file to the PR as a one-number change; the value and its source are the session's own.
- `claude-skills/skills/ai-instruction-and-memory-files/REFERENCES.md`: an entry under `### OpenAI` and the Codex row of the size table, line 127 (M2c). The engineer's answer is recorded on row 35, and the file is in Context's edit list.
- `claude-skills/skills/code-review/SKILL.md`: line 113, from `Carve-out:` to the end of the line (M3), and line 115 (M3a).
- `claude-skills/skills/test-evaluation/SKILL.md`: line 68 (M4).
- `claude-skills/skills/test-conventions/REFERENCES.md`: the committed section after line 57 (M5), unchanged this round.
- `docs/design-decisions/single-source-of-truth-rule.md`: the committed note after line 3 (M6), unchanged this round.
- `CHANGELOG.md`: M7's bullet and the cap bullet under `## [Unreleased]`'s `### Changed`.

Reuse: nothing to call. `test_skill_citation_grammar.py` already guards the citations in M3, M4 and M5 (row 9), so no new test is needed.

Projected diff: about 95 changed lines against origin/main. That is 8 in `test-conventions/SKILL.md`, 4 each in `CLAUDE.md` and `code-review/SKILL.md`, 2 in `test-evaluation/SKILL.md`, about 45 added in `test-conventions/REFERENCES.md`, 2 in the design record, 4 in `CHANGELOG.md`, about 15 in the cap files, 1 in `code-file-size-exceptions.toml`, and about 10 in `ai-instruction-and-memory-files/REFERENCES.md`.

## Verification

1. Size checks, one per gate (G2):
   - CLAUDE.md bytes: run `wc -c claude/.claude/CLAUDE.md` before and after the M2 and M2a edits, so the report carries both numbers. After minus before must equal row 7's 838-byte delta, with "before" read from the merge-base blob on a re-run (25 more when step 5 applies the N14 and N23 fallback). Rows 6 and 7 give the gate and the measurement. A `CLAUDE.md` edit staged after the engineer's commit must not grow past that commit's size (row 7).
     - On any other figure, stop and report both numbers. This is the one stop condition for the byte count; step 3 does not restate it. Do not trim other bullets or shorten M2 yourself; row 7 says what a fix needs.
     - 31,744 stays the outer bound for any later review edit (row 7).
   - SKILL.md lines: `wc -l` on each edited SKILL.md prints the same count before and after its edit.
2. `scripts/venv-run.sh python3 claude/.claude/scripts/select-tests.py` passes when the one killed test, `test_all_discovered_files_pass_shellcheck`, also passes on an isolated re-run by the dispatching session; the 36,148/177/1 counts are the code-writer's report [unverified: not re-derived]. Recorded result after the dispatch (it ran, with one SIGTERM failure, so it did not pass outright): 36,148 passed, 177 skipped and 1 failed, the failure being `test_shellcheck.py::TestRepoIsClean::test_all_discovered_files_pass_shellcheck` with `shellcheck` killed by SIGTERM [unverified: attributed to machine load]; `test_shellcheck.py` re-run alone with `-n0` passed 16 tests. The selection should include `claude-skills/skills/tests/test_skill_citation_grammar.py` and `claude/.claude/hooks/tests/test_design_decision_files.py`. If it omits either, report that as a `select-tests.py` rule-table bug, per the repo `CLAUDE.md`, rather than widening the run by hand.
3. Identity check, keyed by content. Write one Python script that meets these requirements:
   - It lives in a directory under `~/.local/state/` named for this branch, outside the repository and outside `/tmp`, so it survives between review rounds. If the script is gone when a step re-runs it, rebuild it from this plan's blocks.
   - It takes this plan's path and a repository root (default: the current directory) as arguments.
   - It finds each block in the plan by content, never by line number: variant 2 between Context's "Variant 2, the § 6 replacement text" line and its "Public-repo constraint" line, and every fenced block after each `**M<n>,` lead line, whatever the fence's language tag.
   - It compares exact strings in-process and never builds a shell grep from a block, because the blocks hold backticks and double quotes.
   - The code-writer runs it and returns its path. The dispatching session re-runs it before staging.

   The script checks:
   - HEAD holds M5, M6 and the unchanged parts of M2b as written, and this round's other blocks replace committed text. So presence is not enough: each check below also asserts exactly-once and that the superseded text is gone.
   - Exactly-once: each block, joined as one string, occurs exactly once in its target. M5's heading, taken from its lead line, a blank line and M5's block occur together exactly once, in that order.
   - § 6: the `- ` lines under `## 6. Test data` in `test-conventions/SKILL.md`, up to the next `## ` heading, equal variant 2's first bullet, M1's three lines and variant 2's fifth bullet, in that order.
   - The boundary's example list is stated once: `a file, a stream, an exit status or a display` occurs once in `test-conventions/SKILL.md` and zero times in `claude/.claude/CLAUDE.md`, `code-review/SKILL.md`, `test-evaluation/SKILL.md` and `CHANGELOG.md`.
   - Superseded text, each as a bare string, occurs zero times in its target. Each string is marked with where it comes from: the base text, an earlier revision or round, or a plan draft that was never applied.
     - `test-conventions/SKILL.md`:
       - base: variant 2's second, third and fourth bullets;
       - earlier revision: `A shared fixture holds setup`;
       - an earlier plan revision, never applied: `Shared fixtures are for expensive setup` and `or a display, rather than deriving it`;
       - a draft of this revision, never applied: `outside its process, such as through a file`.
     - `claude/.claude/CLAUDE.md`:
       - base: `of setup whose details`, `not derived from the code under test)`, `Define it once` and `, unless importing it would make a test pass whatever the value`;
       - earlier revision: `, other than a result each test works out from its own input` and `importing the symbol`;
       - an earlier plan revision, never applied: `outside its process rather than deriving it`;
       - earlier rounds: `setup its assertions do not depend on`, and the M2 sentence starting `Neither (1) nor (3) covers a helper that a second test file copies`.
     - `claude-skills/skills/code-review/SKILL.md`:
       - base: `Carve-out: test code is DAMP`, `of setup whose details` and `Neither count nor replace a test's use when importing`;
       - HEAD's item 9a clause, for a dispatch that starts from HEAD (M3a): `unless importing it would make a test pass whatever the value?`;
       - earlier revision: `at two sites, whatever its size`;
       - an earlier plan revision, never applied: `number there rather than deriving it`;
       - earlier rounds: `setup its assertions do not depend on`.
     - `claude-skills/skills/test-evaluation/SKILL.md`:
       - base: `instead of importing them from the code under test`;
       - earlier revision: `, other than a result each test works out from its own input,`;
       - a draft of this revision, never applied: `(not a result each test works out from its own input) once in a shared test module`.
     - `CHANGELOG.md`:
       - base: `may no longer copy a value that another test file must keep equal, such as`, `so that test spells out the status or code value`, `combined-size behavior for an AGENTS.md chain is not verified` and `Codex truncation point that the hook's comment names`;
       - earlier revision: `` `project_doc_max_bytes` default. The new figure ``;
       - an earlier plan revision, never applied: `outside its process, and a value two test files must keep equal`;
       - a draft of this revision, never applied: `does not read, and a value two test files must keep equal`.
     - The hook:
       - base: `combined-size behavior is not verified here` and `project_doc_max_bytes truncation`;
       - earlier revision: `reaches that 32 KiB limit`.
     - `claude-skills/skills/ai-instruction-and-memory-files/REFERENCES.md`, base: `| 32 KiB (default) | Hard truncation |`.
     - The design record, earlier rounds: the M6 note's `which calls DAMP "complementary" to DRY, not a replacement for it`.
   - Counts the script asserts against literals written in the script from this plan, not read back from its own extraction:
     - variant 2 is 5 lines and M1 is 3;
     - M2, M2a, M3, M3a, M4, M6 and M7 are 1 line each, and M5 is 28 non-blank lines;
     - M2b's hook comment block is 8 lines, and its hook log line and CHANGELOG bullet are 1 line each;
     - M2c's entry is 6 non-blank lines and its table row is 1.
     - A pass prints one result line with those counts.
   - M2a's second edit, on the "Discriminator literals where a canonical symbol exists" bullet of `claude/.claude/CLAUDE.md`:
     - `since importing it from that code would make the test pass whatever the value. Otherwise reach for the language or framework's named constant first;` occurs once, and `. Reach for the language or framework's named constant first;` zero times.
     - The unchanged tail `if the discriminator is project-defined and the project ships a registry or named-type module, use that.` occurs once, and `if the project defines the discriminator` zero times.
   - M2b, each its own assertion:
     - The hook holds `GLOBAL_CLAUDE_MD_BYTE_LIMIT=31744` once and `GLOBAL_CLAUDE_MD_BYTE_LIMIT=30720` zero times. Its comment paragraph is M2b's 8-line block, checked by exactly-once above.
     - The hook's dated log holds the 2026-11-21 line once.
     - The test holds `BYTE_LIMIT = 31744` once and `BYTE_LIMIT = 30720` zero times.
     - `docs/hooks.md` holds "31,744-byte" once and "30,720-byte" zero times.
     - A search of the tracked files (`git ls-files`, so gitignored files are not read) for `30,720` and `30720`, outside the records (`CHANGELOG.md`, `.claude/plans/`, `docs/cost-levers-considered.md`, `docs/reports/`, `docs/case-studies/`), prints every hit and marks each allowed or not.
       - The search fails on any hit that is not allowed.
       - The two dated-log lines in the hook (the 2026-10-17 line and the 2026-11-21 line) are allowed, and the search also fails if either is missing from the hits. That makes the required hits a check inside the real run: a failed `git ls-files` or a wrong root drops them.
       - A line elsewhere that records a past event is reported to the engineer and is not allowed by default.
     - `CHANGELOG.md` is checked two ways. The older 25,600-to-30,720 entry sits in the same `### Changed` section and stays as written.
       - "rises from 30,720 to 31,744" occurs once in the file, and so does "not 2,048".
       - The superseded sentence "so the raise cannot add a denial for any consumer" occurs once in the file, in the older entry, and not in the cap bullet or its sub-bullets.
     - `test_check_skill_length.py` holds "omitting BYTE_LIMIT" and "well over" zero times, and holds `def test_byte_limit_never_fires_for_this_caller` once.
   - When a review edit changes an M-block, the text it replaces, committed or from an earlier revision, joins the superseded list before the script re-runs.
   - Step 3 is a one-off fidelity check. Each absence assertion is paired with a presence assertion on the same read, so it carries no seeded controls.
4. Removal, leak and source checks, one per sub-item:
   - `git grep -n -e 'Import or call via integration' -e 'named test helper' -- claude claude-skills` prints nothing.
   - Neither REFERENCES.md holds a filesystem path: `git grep -n -e '/tmp/' -e '/home/' -- claude-skills/skills/test-conventions/REFERENCES.md claude-skills/skills/ai-instruction-and-memory-files/REFERENCES.md` prints nothing. M5 is already committed, so a `git diff HEAD` over its file would show nothing and prove nothing.
   - The dispatching session re-fetches the Codex page and checks every claim M2c's entry relays:
     - The blockquote, with its line breaks joined, matches the page's sentence word for word.
     - `developers.openai.com/codex/guides/agents-md` answers with a redirect whose `Location` is the cited URL. The session records the status code and the `Location`.
     - The page shows no last-updated date.
     - The entry's "fetched" date is the date of this re-fetch.
     - On any difference, it corrects M2c's block from the re-fetch, re-runs step 3, and reports the change to the engineer.
     - Result of the 2026-11-23 re-fetch: the page answers HTTP 200 with no redirect. The sentence "Codex skips empty files and stops adding files once the combined size reaches the limit defined by `project_doc_max_bytes` (32 KiB by default)" matches the entry's quoted clause, "(32 KiB by default)" included. The page shows no date. A HEAD request to the `developers.openai.com` URL printed 308 with a `location` equal to the cited URL. The one difference is the fetched date, 2026-11-22 against 2026-11-23, so the block's date is corrected to 2026-11-23, and the entry in `REFERENCES.md` already carries the corrected 2026-11-23 date. [verified: re-fetch and a HEAD request, 2026-11-23]
5. Blind reads, run by the dispatching session, not the code-writer, before the engineer answers row 31 and before the code-writer dispatch. Per `.claude/rules/skill-and-agent-self-review.md`, the fixtures stay in a scratchpad outside the repository: a directory under `~/.local/state/` named for this branch, not `/tmp`, so they survive between review rounds.
   - Texts under test, each assembled in the scratchpad from HEAD's file with this plan's block applied, so step 3 later shows the files hold what was read:
     - § 6 as M1 leaves it, its heading and five bullets;
     - item 9 as M3 leaves it;
     - the `claude/.claude/CLAUDE.md` "Single source of truth" bullet as M2 leaves it;
     - the `claude/.claude/CLAUDE.md` "Discriminator literals where a canonical symbol exists" bullet as M2a leaves it;
     - item 9a as M3a leaves it;
     - test-evaluation's whole anti-pattern table with M4's row in place.
   - Fixtures:
     - Write each from its key entry below, not from the wording of any block.
     - Ship a production stub with each, so the fixture alone shows whether the code under test emits or parses a value outside its process, and whether the code sets that value or computes it from its input.
     - Name and order them so nothing hints at the key.
   - Dispatch, for each text under test: two fresh `general-purpose` agents with `model: sonnet`.
     - Each receives only that text and its fixtures, unlabeled, with no plan, Context or key.
     - Tell each to judge by the supplied text alone, because its own loaded `CLAUDE.md` carries HEAD's wording.
     - Tell each to read nothing except the named fixture and stub files in the scratchpad, because the plan and its key sit in the worktree.
     - Each returns one verdict per fixture on the text's own scale. A fixture that holds two sites is split into two fixtures, so no fixture needs two verdicts on that scale.
     - A reader of line 25 or item 9 also returns a second verdict, meets the text or does not, on each fixture whose test files share one definition: N4, N14, N22, N23 and P2's shape. This second verdict reaches M2's and M3's source clause and their word for a shared definition, which the first verdict cannot.
     - Tell each reader of line 25 or item 9 what each verdict judges:
       - The first judges only what the test files copy or repeat, a shared test module or fixture file included.
       - Under line 25, "covered" also fits test files that copy or repeat nothing.
       - The second judges only whether the shared definition takes the form and the source the text names.
   - Scoring:
     - The key gives each verdict its own entry. A first verdict is keyed under the text's scale, and a second verdict under "Second verdict". Each verdict is scored against its own entry.
     - A verdict passes when both reads match its entry, and fails when both miss it.
     - When the two reads split on a verdict, one more fresh agent reads that fixture against that text before any wording changes. The verdict passes if that read matches its entry, and fails otherwise.
     - A text passes when every verdict passes.
   - Fixture shape for the setup cases (F3, P3, N6, N14, N19, N21, N23 and their M2 counterparts):
     - In F3, the production stub's allow or deny reads only that a repository exists, never its contents.
     - P3's paste is built so some assertion reads each of its steps, so "no flag" is reachable under per-step judgment.
     - In N6, the stub's behavior depends on the one step an assertion reads and on neither other step, so the other two steps are dead.
     - In N19, the stub needs all three steps to run, and its output depends only on the step one assertion reads.
     - In N14 and N21, the fixture's code shows its scope, and the stub reads only that a repository exists. N14's fixture declares no scope, so it takes pytest's per-test default, and N21's declares session scope.
     - In N23, the fixture declares no scope and returns its builder, and the stub reads only that each directory the builder made exists.
     - One case is not probed by any fixture: a paste whose only added assertion checks that a file exists.
   - Fail-first baseline, against HEAD:
     - Run each text's entries marked "new" or "changed" in the key below against that text at HEAD, two fresh reads per fixture, because a single read cannot be told from reader variance. Every § 6 entry is new. Item 9a's HEAD text is item 9a in `git show HEAD:claude-skills/skills/code-review/SKILL.md`, not the working tree's unreviewed sentence.
     - Report to the engineer, per fixture, how many of the two HEAD reads differ from the key. A single difference is compatible with reader variance.
     - If a text's new and changed entries show no difference at HEAD, report that to the engineer. Do not drop the edit or strengthen the fixtures without the engineer.
     - This baseline replaces the earlier ones against the pre-row-29 setup clause and against origin/main's item 9a, because this round changes the texts both measured.
     - Measured at HEAD (`head2.json`): HEAD bars N14 and N23 more than the key allows and splits on N21, so N21 is not a clean control. HEAD's N22 reads allowed on both reads, so the earlier expectation that HEAD's "Spell out a value ... in that module" bars N22 did not hold. N4's and N22's second verdicts match the proposed text. Item 9a and the test-evaluation row have no HEAD read on the final fixtures; their earlier baselines are in the scratchpad's `head.json`. No clause-deleted reads were run, so no claim that deleting a clause would flip a fixture is measured.
     - These are controls that guard this revision's wording against over-allowing or under-allowing:
       - the § 6 entries for N10, N21, N24 and N25;
       - the first verdicts on N4, N14, N22 and N23 for line 25 and item 9;
       - the second verdicts on N14 and N23 for those two texts.

       None is expected to differ at HEAD, and none counts toward the no-difference report above.
   - On a verdict that fails under the scoring rules on a proposed text, apply nothing. The dispatching session revises the block in this plan, re-assembles the text, and re-runs that text's reads with fresh agents.
   - If a key entry itself looks wrong, ask the engineer before changing it, because the key carries the boundary rows 1, 2 and 32 record.
   - These entries go to the engineer with row 31's question:
     - The entries marked "changed", which are this plan's changes.
     - The new N16, N17 and N18 entries, which place row 32's tiebreak for a result with fixed text around its input. The question shows N16 and N17 side by side in plain words.
     - The new N23 entries, which decide whether a fixture may hold a builder.
   - A revision to the M2a or M3a clause goes to the engineer first, because row 25 records the clause's core as the engineer's words.

   Fixtures added in the last revisions, each used in the keys below by its label:
   - N1: two test files each assert that the stub prints `5` for the inputs 2 and 3, and the stub prints the sum of its integer arguments. Unlike the earlier N1, its shape is not the example M1 and M3 quote.
   - N2: two test files of the same stub each assert, inline, the exit code 2 the stub sets for a denial.
   - N3: one test file imports `DENY_TEXT` from the stub and asserts `out == DENY_TEXT` on the text the stub prints.
   - N4: a shared test module sets its expected header by calling the stub's `format_header()`, which returns fixed header text that the stub prints, and two test files import it.
   - N5: two test files each assert `order.status is OrderStatus.SHIPPED`, importing the stub's enum, and the stub never writes the member's value out or reads it in.
   - N5r: three tests in one test file compare an order's status to the raw string `"shipped"`, and the stub never writes that value out or reads it in.
   - N6: a second test file pastes the first file's three-step setup. One assertion reads the value one step wrote, and the other two steps go unread.
   - N7: a shared test-helper module defines `make_repo(tmp_path)`, a two-line `git init`, and two test files import and call it, with assertions that check only that the call is allowed or denied.
   - N8a: production code in one module compares a raw status string at several sites. The stub's enum defines that string, and the stub prints it.
   - N8b: a test asserts that printed status string, spelled out, against N8a's stub's output.
   - N9: one test file imports the delimiter from the config module the stub reads it from, and builds its input with it.
   - N10: a `conftest.py` fixture returns a simple dict that tests in two files use as input.
   - N11: the stub's request handler sends its own constant `NOT_FOUND = 404` as an HTTP response status, and a test imports `NOT_FOUND` from the stub and asserts `resp.status_code == NOT_FOUND`.
   - N12: the stub stores its constant `SHIPPED`, `"shipped"`, in a database row, and three tests in one test file each read the row back and assert `"shipped"` spelled out.
   - N13: the stub publishes a queue message whose type field it sets from its constant `ORDER_PLACED`, and a test imports that constant and asserts that the published message's type equals it.
   - N14: a `conftest.py` fixture with the default per-test scope runs a two-line `git init` in a fresh temporary directory for each test, and tests in two files use it.
   - N15: a `conftest.py` fixture creates a database schema once per test session, and tests in two files use it.
   - N16: the stub prints `"Hello, "` followed by its name argument, and two test files each assert `"Hello, Ann"` for the name `"Ann"`.
   - N17: the same stub prints the fixed text `"Nobody to greet"` when its name argument is empty, and two test files each assert that text for an empty name.
   - N18: the stub's `validate()` returns the fixed message `"name required"`, written inline in the stub with no named constant and never written out of the process, and two test files each assert it inline.
   - N19: a second test file pastes the first file's three-step setup: create a repository, configure a user, commit a file. One assertion reads the committed file's name, and the other two steps are prerequisites the stub needs but never inspects.
   - N20: a test takes the event name the stub must print from a registry file that maps each hook to its event. The stub prints its own hardcoded copy of the name and never reads the registry.
   - N21: a `conftest.py` fixture with session scope runs N14's two-line `git init` once, tests in two files share that one repository, and no test or stub changes the repository.
   - N22: a shared test module sets the event name the stub prints from N20's registry file, which the stub never reads, and two test files import that name and assert it.
   - N23: a `conftest.py` fixture with the default per-test scope returns a builder function. Tests in two files call that builder with the names they need, and each call creates a directory tree under the test's temporary directory. The shape is that of `fake_config_dir_factory` at `claude/.claude/scripts/tests/conftest.py:1594-1604`. [verified: plan-architect's read of those lines]
   - N24: a control, not a twin. One test asserts the raw event name `"document.saved"` the stub prints, with no registry file. It reads "does not require" under any connective, so it cannot detect a revert of M2a's connective swap (row 42).
   - N25: a `conftest.py` fixture returns a builder `make_user()` with defaults for every field. Two test files call it with no arguments and assert only the suffix `"<ann@example.com>"` of what those defaults produce.
   - N26: N20's stub and registry file unchanged (the registry sits in the tests directory), with the test asserting the raw `"document.saved"` instead of reading it from the registry. It reads as a second control, because it differs from N24 only by a registry file nothing reads (row 42).
   - L1, the role label: a role label defined only in test helpers, not in production code. A test-helper module defines it as a constant, and three tests in one test file pass the raw literal as an input and select behavior by it. M2a's and item 9a's keys both use this one description (row 38).

   The key, per text under test (entries without a mark are unchanged from earlier rounds):
   - § 6 as M1 leaves it, with a verdict of allowed or not allowed (every entry new):
     - Not allowed: the shapes of F1, F2, F3, F4 and F5 in item 9's key.
     - Allowed: the shapes of P1 and P3 in item 9's key.
     - Allowed: N1, N5, N7, N15, N16, N20 and N23 (N15 and N20 per row 39, N23 per row 41).
     - Allowed (new): N24, the raw-literal control for N20, and N26, a second raw-literal control, its § 6 verdict unread [unverified] (row 42).
     - Not allowed (new): N25. The test body passes its builder none of the values its assertions depend on. N25 reads the same on the original text, so it is a control with no measured flip (row 42).
     - Allowed (changed, was "not allowed"): N14 (row 39).
     - Allowed (new): N22 (row 40).
     - (N23 appears above.) Each call of its builder creates setup the test runs against, and bullet 4's "Setup may instead be a fixture that every consuming test uses" lets that setup be a fixture. Bullet 2's expensive-setup limit reaches only a fixture built once for many tests.
     - Not allowed: N2, N3, N4, N6, N9, N10, N11, N13, N17, N18 and N19.
     - Not allowed (new): N21 (row 39).
   - Item 9 as M3 leaves it, with a verdict of flag or no flag:
     - F1, flag: two test files each spell out the delimiter the production stub parses.
     - F2, flag: a second test file holds a pasted copy of an identical named builder.
     - F3, flag: a second test file pastes the same inline temporary-repository setup as the first, and its assertions check only that the call is allowed or denied.
     - P1, no flag: the production stub parses F1's delimiter but stores a free-text field without parsing it, and two distinct builders in two test files each default that field to the delimiter's literal.
     - P2, no flag: a shared test module spells out the delimiter, two test files import it, and the production stub holds the same literal.
     - P3, no flag: the same paste, plus assertions that compare the values the setup wrote, so every step is read.
     - P4, no flag: one test file repeats inline arrange blocks across its tests.
     - F4, flag: a second test file copies a named builder with one field default changed, and the two must be edited together.
     - P5, no flag: one test file reuses a helper across many of its tests.
     - F5, flag: a named size-limit constant the production stub enforces, defined in one test file and copied into a second.
     - F4 and P1 rest on the "must keep equal" clause and on M3 never defining a stand-in, not on the dropped one-fact test (row 11). Treat a miss on either as a wording finding on M3.
     - No flag (new): N1 and N16.
     - Flag (new): N2, N6, N17, N18 and N19.
     - P6, no flag (new): in three test files, a test's inline six-line arrange block, the same in each, builds the scenario its assertions read, and an assertion reads the value each of the six lines sets. So per-step judgment reaches "no flag", and P6 differs from P3 by its three files, which reach item 9's base threshold. It guards the reordered DAMP sentence and is not expected to differ at HEAD.
     - No flag (new): N4, N14, N22 and N23. In each, the test files use one shared definition and copy nothing.
     - Second verdict (new): N4's shared definition does not meet item 9's text, and P2's does. Deleting M3's source clause is expected to flip N4's second verdict, so N4 is that clause's control. [unverified: no clause-deleted read was run]
     - Second verdict (new): N14's fixture, N22's shared module and N23's fixture each meet item 9's text. Deleting M3's source allowance is expected to flip N22. [unverified: no clause-deleted read was run] A miss on N14 or N23 goes to the engineer as a wording finding on M3's "one shared definition".
   - The edited `claude/.claude/CLAUDE.md` "Single source of truth" bullet, with a verdict of covered by a named exception or not:
     - Not covered: a named constant for a size limit the production stub enforces, defined in one test file and copied into a second.
     - Not covered: an identical builder pasted into a second test file.
     - Not covered: a builder in a second test file that differs from the first in one field default, where the stub makes the two change together.
     - Not covered: a delimiter the production stub parses, spelled out in two test files.
     - Covered: the same literal as the first, as a stand-in, defaulted by two distinct builders in two test files. The builders share a name pattern and field list, differ in body, and the stub shows their other fields diverging.
     - Covered: a shared test module spells out the value, two test files import it, and the production stub holds the same literal.
     - Not covered: a second test file pastes inline temporary-repository setup, and its assertions check only that the call is allowed or denied.
     - Covered: the same paste, plus assertions that compare the values the setup wrote, so every step is read.
     - Covered: N1 and N16 (new).
     - Not covered: N2, N6, N17, N18 and N19 (new).
     - Covered (new): N4, N14, N22 and N23, whose test files copy or repeat nothing.
     - Second verdict (new): N4's shared definition does not meet line 25's text, and P2's shape, the shared-module entry above, does. Deleting M2's source clause is expected to flip N4's second verdict, so N4 is that clause's control. [unverified: no clause-deleted read was run]
     - Second verdict (new): N14's fixture, N22's shared module and N23's fixture each meet line 25's text. Deleting M2's source allowance is expected to flip N22. [unverified: no clause-deleted read was run]
     - On a miss on N14 or N23, insert " or, for setup, a fixture" after "in a shared test module" in M2 (25 bytes, row 7), re-assemble the text and re-run line 25's reads with fresh agents. The insertion matches § 6's bullet 4, so it goes to the engineer with row 31 rather than as a new rule.
   - The `claude/.claude/CLAUDE.md` "Discriminator literals where a canonical symbol exists" bullet as M2a leaves it, with a verdict of requires importing the canonical symbol or does not:
     - Does not require it: a test asserts the `Status.FAILED` wire value, in two test files. Importing the production constant would make the test pass whatever the value, so spell it out.
     - Does not require it: a test parses a delimiter and spells it out.
     - Requires it (changed, was "does not require it"): a test asserts an in-process error code the stub never writes out.
     - Requires it (changed, was "does not require it"): L1.
     - Requires it (control): production code in one module compares a raw status string at several sites, though another production module defines the enum with that member.
     - Requires it (new): N5r and N8a.
     - Does not require it (new): N26. All four reads at HEAD and on the proposed text said so, so N26 does not separate the old connective from the new one (row 42).
     - Does not require it (new): N24. N24 reads the same on the original text, so it is a control with no measured flip (row 42).
     - Does not require it (changed, was "requires it"): N20. The test holds no raw literal, so there is nothing for line 42 to replace (row 41).
     - Does not require it (new): N8b, N11, N12 and N13.
   - Item 9a as M3a leaves it, with a verdict of flag or no flag:
     - Flag: production code compares a raw status string at 3 sites with no named type.
     - Flag: three production sites compare the raw status string with no named type, and one test asserts the status production emits; the test keeps its literal.
     - No flag: one test file asserts, in 3 tests, the status string the production stub prints. This revision pins the stub's printing, which the entry left open. N5r is the case where the stub never writes the value out.
     - No flag: two production sites and two test sites compare the status string, four in all. The test sites assert the status that production code emits, so importing the symbol there would make them pass whatever the value, and the clause excuses them. That leaves two sites.
     - Flag (changed, was "no flag"): L1.
     - Flag (new): N5r.
     - No flag (new): N12.
   - test-evaluation's whole anti-pattern table with M4's row in place, with a verdict of the row applies or not:
     - Applies: a test recomputes its expected value with its own re-implementation of the production stub's parser.
     - Does not apply: a test spells out its expected literal.
     - Does not apply (changed): N1, in place of the earlier entry with two test files each spelling out the same literal inline, which did not say whether the literal was set in the code.
     - Does not apply: two test files each default a stand-in value the stub neither parses nor limits.
     - Does not apply: a shared test module spells out the value and two test files import it.
     - Applies: a test imports the production stub's constant to build both its input and its expected value.
     - Applies (new): N3, N4 and N9.
     - Does not apply (changed, was "applies"): N2, N17 and N18, and the entry with two test files each defining the same constant. M4's row is a pointer to § 6 and names neither the tiebreak nor define-once (row 41).
     - Does not apply (new): N5 and N16.
     - Does not apply (new): N20 and N22. Neither duplicates production logic, which is why M4 takes no source allowance (Alternatives). A miss on either means M4 needs the allowance, and that goes to the engineer with row 31.
   - Not probed by these keys:
     - An imported symbol fed to production code that holds its own raw literal, a test-side case where importing is not value-blind. N20 is the only test-side entry of that kind, and it takes its value from a registry rather than from a symbol fed to production code. The PR body says what the clause covers in the clause's own terms.
     - A `conftest.py` fixture that returns a builder of simple data objects and creates no setup: allowed under § 6 (row 41). N23 probes it.
6. In the review phase:
   - `/code-review` runs `/skill-review` on the three SKILL.md files, which the commit hook enforces.
   - Run `/ai-instruction-and-memory-files` on the `claude/.claude/CLAUDE.md` diff.
   - A review edit to any prescribed text lands in this plan's block first, then step 3's script re-runs.
   - An edit to M1, M2, M2a, M3, M3a, M4 or M7 goes to the engineer, because row 31 gates those texts on the engineer's approval. An edit to any of them but M7, which has no step 5 read, also re-runs that text's step 5 reads with fresh agents. A review edit to M2a or M3a follows step 5's engineer-first rule.
7. Commits, after steps 1-6 pass:
   - The session runs the staged-diff `/code-review` and commits every changed file except `claude/.claude/CLAUDE.md`.
   - It then stages `claude/.claude/CLAUDE.md` alone and records two values:
     - the blob ID, from `git rev-parse :claude/.claude/CLAUDE.md`;
     - the staged size, from `git cat-file -s :claude/.claude/CLAUDE.md`.
   - The size change must equal step 1's delta. Any other change is a stop-and-report.
   - It then runs the staged-diff `/code-review` on that file, so a marker covers the bytes the engineer commits.
   - Any later edit to `claude/.claude/CLAUDE.md`, from that review or from the engineer, re-stages the file and re-records both values. The size check then compares against step 1's delta for the edited text, and the staged-diff `/code-review` runs again on the new staged state.
   - The session does not attempt that commit. Its last message holds, with the latest recorded pair:
     - the staged state and both recorded values;
     - the command `git -C <absolute worktree path> commit`, with no `-a` and no pathspec;
     - the expected branch, shown by `git -C <absolute worktree path> branch --show-current`;
     - the commit message.
   - The session ends there. The message carries the two values so the post-commit check can run in a later session.
   - After the engineer's commit, the session checks in that worktree that:
     - `git rev-parse HEAD:claude/.claude/CLAUDE.md` equals the recorded blob ID;
     - `git cat-file -s HEAD:claude/.claude/CLAUDE.md` equals the recorded size;
     - `git diff --stat HEAD~1 HEAD` lists only that file;
     - `git log -1 --format=%B HEAD` matches the message it gave.
   - `/ready-for-review` restarts only after those checks pass.
8. PR body: it carries the three items under Context's "Commit sequencing and PR body", stated in plain words with no row or round identifier. It also states:
   - that no blind-read fixture discriminates the `since`-for-condition connective swap in line 42 and item 9a, so that change is argued, not measured (row 42);
   - that a consumer whose Codex chain has more than one file gets 1,024 bytes below that limit for the rest of the chain under the raised cap, not 2,048;
   - how many bytes the global `CLAUDE.md` sits under the 31,744 cap after this change, re-derived from `git cat-file -s HEAD:claude/.claude/CLAUDE.md` when the body is written (197 after the rebase onto origin/main);
   - the engineer's planned reduction of `CLAUDE.md` as intent, not as a landed change, if the body mentions it (row 26);
   - that the repository holds 23 `scope=` declarations wider than function across 17 Python files (row 39). Some are cheap and read-only, so a strict reading of § 6's "expensive setup" would flag them. Changing existing tests is a separate follow-up (row 3). Re-derive both counts by grep when writing the body.

## Out of scope

- A mechanical check for cross-file copies. The engineer called it "a separate follow-up" (row 3).
- A presence tripwire for the § 6 pointer that M2-M6 add. The citation tests check that a present citation resolves, not that it is present. The tripwire belongs with the mechanical-check follow-up (row 3), as a check of its own.
- Re-scoring the whole fixture corpus against M2, M3 and M4. Verification step 5's targeted fixture sets check each shipped text instead.
- An edit pass over existing comments and docstrings that justify a cross-file copy as DAMP, such as `claude/.claude/hooks/tests/test_require_plan_review.py:2463`, `claude/.claude/hooks/tests/test_require_skill_review.py:1897` and `claude/.claude/scripts/tests/test_transcript_denials.py:1011,1109`. This is the same "separate follow-up" (row 3). It also covers existing test files that the revised § 6 flags, such as hook test files that each assert one hook's exit code (row 32), and fixtures built once for many tests over cheap setup (row 39).
- The in-process derived-value gap. No edited text bars a test from deriving, with logic, an expected value the code under test keeps inside its process. Two examples:
  - ch. 12's Example 12-15, whose expected URL `baseUrl + "/albums"` hides the bug that Example 12-16's written-out URL shows;
  - `with_tax(100) == 100 * TAX_RATE`, with `TAX_RATE` imported from the code under test.

  The gap is the price of keeping the boundary at "outside its process", which agrees with line 42's rule that a test imports an in-process enum member (row 40). Closing it would rewrite the boundary in M1, M2, M3, M4 and M7.
- Wording for the one-character-constant edge that Context names. Context leaves it alone on purpose.
- Reconciling § 2's test-infrastructure exemption with ch. 12's "must always have its own tests" (row 19). § 2 exempts infrastructure from test-first, not from tests, and changing it is a rule change outside the Ask.
- The design record's Pragmatic Programmer quote at line 13. Context bars quoting the 20th-anniversary wording as unverified. The record, though, says the quote was checked against the publisher's extract, and correcting it needs a disproof this plan does not have.
- Plans under `.claude/plans/` that quote the old § 6 wording. They are preserved records.
- The adversarial review's other points: the unexplained 40,000 left in `test_check_skill_length.py` once its docstring is gone, the test-evaluation row's label and symptom, and the xunitpatterns citation instruction in `test-conventions/REFERENCES.md`. The dispatching session takes them to the engineer separately (row 30).
- A dated-log line marking the 31,744 raise as temporary. The offsetting reduction is the engineer's stated intent only (row 26), so the line would record a plan nobody has confirmed.
- Moving the `CLAUDE.md` line 25 clause to a path-scoped rules file. The engineer kept it in `CLAUDE.md` because a rule and its exception belong in one place (row 26).
- A size or step floor for sharing setup. § 6 has none, so adding one would be a new rule rather than a fix of a conflict. Its "expensive setup" sentence decides only when a fixture may be built once for many tests, not whether setup is worth sharing (row 39).
