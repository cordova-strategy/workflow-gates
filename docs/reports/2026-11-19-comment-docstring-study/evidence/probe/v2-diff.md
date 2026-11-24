# v2 wording: exact before and after (scratch; no repo file edited)

Files: `bodies/amended-v2-rule.md` (the rule), `bodies/amended-v2.md` (the body), `bodies/ablation-v2.md` (amended-v2 plus the delete-all line). The rule bullet is split one sentence per line below, for reading only; the file keeps it on one line.

## 1. Rule bullet: amended (v1) -> amended-v2

```diff
--- a/amended-rule.md (bullet only)
+++ b/amended-rule.md (bullet only)
@@ -1,2 +1,2 @@
-**Don't restate the code.** A comment or docstring states only the non-obvious design decisions behind its subject, each naming what was decided and giving a reason static analysis cannot find: why it is this way, or what outside this repository forces it.
+**Don't restate the code.** A comment or docstring states only the non-obvious design decisions behind its subject, each naming what was decided and giving a reason static analysis cannot find: why it is this way, or what outside this repository forces it, or when to revisit it.
 Delete every other clause, including anything static analysis of this repository's code and tests, or the standard library, finds, even if it is true and takes several files to find.
@@ -5,2 +5,3 @@
 Delete a restatement: a shorter or corrected restatement still restates.
+When a clause mixes a decision or trigger with restated detail, keep the decision or trigger half and delete the restated half; if no reason is stated, keep the decision with a pointer to where its reason lives, otherwise delete.
 Naming what a kept decision decides is not a restatement.
```

- Added: "or when to revisit it" ends the list of what a docstring may state.
- Added: one compress-only sentence after "a shorter or corrected restatement still restates.", which is kept word for word.
- Kept: "Naming what a kept decision decides is not a restatement." The new sentence tells the reviewer to keep the decision half of a mixed clause, but says nothing about a clause that is purely a decision and only names what it decides, so it does not cover this sentence and the sentence stays.

## 2. Body: shipped -> amended-v2 (the full edit set)

```diff
--- a/comment-discipline-reviewer.md
+++ b/comment-discipline-reviewer.md
@@ -13,4 +13,4 @@
 prose" bullets, and §Working Style's "Be precise" bullet. You do not write code — you name every
-violating site and the concrete fix it needs, you do not rewrite the text
-yourself. The tree under review is read-only: the only write you make into
+violating site and the concrete fix it needs, you do not edit the file
+yourself, and you propose the replacement sentence in your finding. The tree under review is read-only: the only write you make into
 it is the `findings_path` file.
@@ -149,4 +149,5 @@
 what the code already shows, per CLAUDE.md §Durable text's "Don't restate the
-code" bullet. The fix is deletion, even where the passage also sits at the
-wrong altitude.
+code" bullet. The fix is one sentence per decision the passage states, naming its subject so the reason still says
+what it explains, with the rest deleted. When the passage states no decision, the fix is deletion,
+even where the passage also sits at the wrong altitude.
 
@@ -216,6 +217,6 @@
 - Any other unsettleable claim draws no finding.
-- A comment or docstring repeating what reading the code shows, or a doc
-  passage on how the code works, is a Prose restating the code finding with
-  deletion as its fix, whether true or false, and draws none here.
-- These stay in this angle:
+- A comment or docstring repeating what static analysis of the repository's code and tests, or the
+  standard library, finds, or a doc passage on how the code works, is a Prose restating the code
+  finding with deletion as its fix, whether true or false, and draws none here.
+- These stay in this angle, in a doc (not in a comment or docstring):
   - A feature doc's account of what the code does for its user or how to use
```

## 3. Body: amended (v1) -> amended-v2 (the v2 change alone)

```diff
--- a/comment-discipline-reviewer.md
+++ b/comment-discipline-reviewer.md
@@ -13,4 +13,4 @@
 prose" bullets, and §Working Style's "Be precise" bullet. You do not write code — you name every
-violating site and the concrete fix it needs, you do not rewrite the text
-yourself. The tree under review is read-only: the only write you make into
+violating site and the concrete fix it needs, you do not edit the file
+yourself, and you propose the replacement sentence in your finding. The tree under review is read-only: the only write you make into
 it is the `findings_path` file.
@@ -149,6 +149,5 @@
 what the code already shows, per CLAUDE.md §Durable text's "Don't restate the
-code" bullet. The fix is deletion, even where the passage also sits at the
-wrong altitude, unless the clause is the subject of a kept decision, which stays inside the decision
-sentence. When a kept decision's subject clause is deleted, keep the subject inside the decision
-sentence, so the reason still names what it explains.
+code" bullet. The fix is one sentence per decision the passage states, naming its subject so the reason still says
+what it explains, with the rest deleted. When the passage states no decision, the fix is deletion,
+even where the passage also sits at the wrong altitude.
 
```

- "Prose restating the code" fix: from deletion, plus two sentences about folding a subject (edits 2a and the revision (d) clause), to one sentence per decision the passage states, naming its subject, with deletion when no decision is left. The two subject-folding sentences collapse into the "naming its subject" phrase.
- Edits 2b and 2c (the False-angle hand-off and the doc-only stay-list) are unchanged from v1.
- The opening (body lines 13-15) said "you do not rewrite the text yourself", which conflicts with a fix that is a one-sentence replacement per decision. It now says the reviewer does not edit the file and proposes the replacement sentence in the finding (the exact lines are in the diff above). The tree-is-read-only sentence after it is unchanged.
- Checked and left unchanged: Output format item 5 ("Concrete fix" lists compression, relocation target, deletion or the durable fact to keep, which a proposed sentence satisfies), the Input contract, and the `findings_path` file rules. No other line says the reviewer must not write replacement text.
