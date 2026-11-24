# Stage 1 results

Output of the frozen tools, run after the stage-1 runs.

## stage1_precheck.py

```
findings files 77/77, cost files 77/77, spend $10.4140, reference model claude-sonnet-5-5
PRECONDITION MET
```

## adjudication_score.py --threshold 7

```
bar: a row passes at 7 of 10 runs; bar source amended-v2
[amended-v1] P17c7: INSUFFICIENT RUNS  pass 0, fail 3, pending 0, failed checklist points {'a': 3, 'b': 2, 'c': 2, 'd': 1}
[amended-v1] P26c4: INSUFFICIENT RUNS  pass 0, fail 3, pending 0, failed checklist points {'d': 3}
[amended-v2] P17c7: FAIL  pass 3, fail 7, pending 0, failed checklist points {'e': 7}
[amended-v2] P26c4: FAIL  pass 3, fail 7, pending 0, failed checklist points {'e': 4, 'd': 2, 'a': 2}

External-fact rows (reported alone, no bar):
[amended-v1] P25c2: pass 2 of 3 adjudicated (0 pending), failed checklist points {'d': 1}
[amended-v2] P25c2: pass 3 of 3 adjudicated (0 pending), failed checklist points {}

Contested rows (listed only, not scored): P10c3, P21c3, P26c3

REWRITE bar (amended-v2): FAIL
```

## stage1_compare.py

```
(b) DELETE rows old amended got right 3 of 3 that v2 got wrong in >= 2 of its 3 runs: ['P01c1', 'P01c2', 'P01c4', 'P17c1']
    NO-GO needs >= 2 such rows, each confirmed by reading the findings: candidates 4 -> READ AND CONFIRM
    read P01c1: ['P01-declared_roots_file/run1.md', 'P01-declared_roots_file/run2.md', 'P01-declared_roots_file/run3.md']
    read P01c2: ['P01-declared_roots_file/run1.md', 'P01-declared_roots_file/run2.md', 'P01-declared_roots_file/run3.md']
    read P01c4: ['P01-declared_roots_file/run1.md', 'P01-declared_roots_file/run2.md', 'P01-declared_roots_file/run3.md']
    read P17c1: ['P17-project_family/run1.md', 'P17-project_family/run2.md', 'P17-project_family/run3.md']
    other flips (old right majority, v2 wrong majority; report each with its cause): ['P08c1', 'P08c2', 'P08c3']
    pointer conversions (P01c3, P22c2, P28c1 wrong in some v2 run; listed apart): ['P01c3', 'P22c2', 'P28c1']
(c) K1, K2, R1, R2 (NO-GO if any run deletes a clause, or a hand-read edit changing a reason or trigger appears in >= 2 of 3 runs):
    K1: runs deleting 0, runs with an edit 1 -> READ the edits; files ['K1-fetch_report/run1.md', 'K1-fetch_report/run2.md', 'K1-fetch_report/run3.md']
    K2: runs deleting 0, runs with an edit 0 -> clean; files ['K2-hash_cache_key/run1.md', 'K2-hash_cache_key/run2.md', 'K2-hash_cache_key/run3.md']
    R1: runs deleting 3, runs with an edit 0 -> NO-GO: a run deleted a clause; files ['R1-schedule_retry/run1.md', 'R1-schedule_retry/run2.md', 'R1-schedule_retry/run3.md']
    R2: runs deleting 0, runs with an edit 0 -> clean; files ['R2-encode_event/run1.md', 'R2-encode_event/run2.md', 'R2-encode_event/run3.md']
(d) KEEP rows and the 7 subject rows with an uncontested pair that old amended got right in >= 2 of 3 runs and v2 deleted in >= 2 of 3: ['P27c1'] -> NO-GO if any is confirmed by reading
    read P27c1: ['P27-print_resolved_scope/run1.md', 'P27-print_resolved_scope/run2.md', 'P27-print_resolved_scope/run3.md']
    KEEP rows v2 edited in some run (hand-read every one): ['P27c5']
    read P27c5: ['P27-print_resolved_scope/run1.md', 'P27-print_resolved_scope/run2.md', 'P27-print_resolved_scope/run3.md']
(report, not gated) runs that do not delete a decision-shaped DELETE row (read each by hand to see whether it keeps a decision sentence):
    old amended: P09c2 2; P11c2 2; P11c3 2; P18c2 0; P19c2 0; P22c2 1; P28c1 2
    amended-v2: P09c2 0; P11c2 2; P11c3 2; P18c2 1; P19c2 0; P22c2 3; P28c1 2
```
