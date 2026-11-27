---
paths:
  - "evals/**"
---

## Bench data kept outside the repo

Bench working data and human labels may live in `~/.local/share/replay-bench-data/` or `~/.local/share/review-bench-data/`, outside any checkout.

- If either directory exists, read the `README.txt` at its root before using anything in it. It describes layout and handling limits.
- Check the unit records, label records and candidate lists there before asking the engineer to relabel units or re-collect candidates. Open nothing the README restricts.
