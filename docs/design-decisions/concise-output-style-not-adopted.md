# Concise output style not adopted as the stow-wide default

*2026-11-23.*

Claude Code's built-in Concise output style was evaluated as the stow-wide default and not adopted, and `claude/.claude/settings.json` sets no `outputStyle`. The maintainer's aim was "hoping that the concise option will produce fewer words, make it easier for a human to read, but will keep like quality output". Per the output-styles page, it would have reached every stow consumer's main conversation and forks. The recorded reason is the maintainer's: "quality metrics, doesn't meet the bar". The evaluation produced these results:

- On Sonnet, replies across the five probe prompts were about 26% shorter.
- The readability proxies showed neither a clear gain nor a clear regression.
- On exploratory counts at five samples per style, Concise dropped content a reader decides from.

See "What Concise dropped" for those counts, "What Concise kept" for what it kept and "Not measured" for the coverage limits.

## What the scripted probes measured

The probes ran on 2026-11-20 with Claude Code 2.1.329 through `claude -p` under `--permission-mode acceptEdits`. Each ran in a fresh scratch directory holding three small synthetic Python files. Each Concise arm set the style with `/output-style concise`, which wrote that directory's `.claude/settings.local.json`. Each Default arm had no settings of its own. The global `CLAUDE.md` and any instruction file in a parent directory of the scratch directory loaded in both arms, so the Default baseline already carried its concision rules. The probes set Concise at project-local scope.

Samples per style and prompt:

- Sonnet, five each: review, options, tradeoffs, debug and explain.
- Sonnet, three each: a subagent-brief prompt and a commit-message prompt.
- Sonnet, one each: edit, rename and refactor.
- Opus, three each: review, options and tradeoffs.

The five prompts below back only the five-sample cells and the Opus cells. Each of those categories ran one prompt:

- review: "Review util.py and report any problems you find. Do not edit anything."
- options: "I need to store a small config file for this project. Should I use JSON or YAML? I have to pick one."
- tradeoffs: "We are considering caching the results of compute_total. Lay out the tradeoffs for a decision memo. Do not edit anything."
- debug: "A user reports that parse_line crashes on the input line 'apple,,0.5'. Explain why it crashes and how you would fix it. Do not edit anything."
- explain: "Explain to a new teammate what this directory does and how its files depend on each other. Do not edit anything."

The subagent-brief prompt asks the session to delegate a review of `util.py` to a subagent and relay what it finds, with no edit. The commit-message prompt asks for a one-line docstring edit plus a commit message, with no git operation.

Every count below holds on its one prompt and the one fixture. A single reader chose the content markers after reading the replies, so the counts are exploratory, and the markers are a subset of what Concise dropped, not a census.

### Length

On Sonnet the mean reply was 277 words under Default and 205 under Concise, about 26% fewer. That figure is the mean across these five prompts, so it describes this prompt mix, not a workload. Concise replies as a share of Default replies, by prompt: options 45%, review 77%, tradeoffs 74%, debug 79%, explain 84%.

The explain share is inflated, because only the Concise arms held `.claude/settings.local.json`. All five Concise explain replies spent a line of about 15 words on that file. Without it the explain share is about 77%.

On Opus the shares were options 64%, review 86% and tradeoffs 89%. Each Opus cell holds three samples, so these shares show a direction only.

The edit and rename prompts ran one sample each and support no conclusion: 65 words under Default against 60 under Concise for the edit, and 23 against 29 for the rename.

### Readability

The readability measures are proxies for jargon and telegraphic prose. They moved by small amounts in both directions and show neither a clear regression nor a gain. Shorthand words per 100 words rose on both models, from 0.40 to 0.66 on Sonnet and from 0.04 to 0.26 on Opus. Acronyms per 100 prose words and words per sentence rose on Opus. The Sonnet article rate fell from 9.1 to 8.0 articles per 100 words, which can signal telegraphic prose.

### What Concise dropped

On Sonnet, five per style, the counts read Default then Concise. Each marker's classification rule comes first:

- Closing priority line, a closing sentence naming which review findings matter most or come first: 5 of 5 and 1 of 5.
- Numbered findings, review findings written as a numbered list: 4 of 5 and 0 of 5.
- Open-questions list, a tradeoffs reply closing with a list of two or more open questions or unknowns: 3 of 5 and 1 of 5. Two more Default replies posed a single question.
- Tooling caveat, an options reply saying an existing tool convention should decide, or offering to firm up the answer: 4 of 5 and 1 of 5.
- Per-option pros and cons, an options reply giving each format its own list item with its strengths or drawbacks: 4 of 5 and 0 of 5.
- Parser-dependency point, an options reply saying JSON needs no extra parser or dependency in most languages: 5 of 5 and 2 of 5.
- Run-directory note, an explain reply saying to run the scripts from this directory because the imports are flat: 3 of 5 and 0 of 5.
- `ValueError` note, an explain reply saying a non-numeric quantity or price raises `ValueError`: 4 of 5 and 1 of 5.
- Suggested test, a debug reply proposing a test for the crashing input: 2 of 5 and 0 of 5.

At five per style, only the closing priority line, numbered findings and per-option pros and cons reach a two-sided Fisher exact p of about 0.05, before any correction for nine markers. The other six differences cannot be told apart from chance.

On Opus, three per style, numbered review findings appeared in 2 of 3 Default replies and 0 of 3 Concise replies. A closing list of open questions appeared in 2 of 3 Default tradeoffs memos and no Concise memo. One Default review ordered its findings "from most to least important", and no Concise review did. The Opus differences point the same way as Sonnet's. At n=3 per cell they cannot be told apart from chance.

For written artifacts on Sonnet, three per style, each difference shows a direction only:

- All three Default relays of the subagent's review said the session had not checked the subagent's findings itself, against one Concise relay.
- The edit report around the commit message was about a third shorter under Concise, a mean of 35 words against 51. It left out the docstring text it had written in 2 of 3 Concise replies, against 0 of 3 Default.

### What Concise kept

Every options reply in both styles named a recommendation with its reason, 10 of 10 on Sonnet and 6 of 6 on Opus. Every Concise review kept the concrete failing inputs and the main defects. Content naming what would change the recommendation appeared in all five Concise tradeoffs replies, as a list in two and as a sentence in three.

Subagent briefs averaged 64 words under both styles. All six named the file, stated a read-only scope and asked for a report shape. Commit messages carried an equivalent one-line subject in all six replies, and five were identical.

### The approach walk-through

The scripted runs could not observe the approach walk-through. `claude -p` under `acceptEdits` has nobody to walk through to. In every completed edit and refactor run, neither style wrote text before the first edit. The main-session rule to walk the user through a proposed approach before acting therefore stays unobserved.

## Not measured

- Written artifacts beyond subagent briefs and commit messages, such as PR bodies, plan files and handoff notes.
- Models other than the Sonnet and Opus models probed.
- Claude Code builds other than 2.1.329, the one probed.
- Multi-turn sessions.
- Skill-driven relays, such as the main session relaying review findings, and the questions the main session asks the maintainer. The relay reported in "What Concise dropped" came from a plain prompt, not a skill.
- Whether Concise still runs the code to check its own edit. In the one completed refactor pair, Default tried to run the code after its edit and Concise did not. That is one sample.
- Destructive-action confirmation and risk-disclosure text. The output-styles page says Concise keeps full length for destructive-action confirmations. No probe observed it.
- Whether Concise keeps Claude Code's built-in software-engineering instructions. The [output styles page](https://code.claude.com/docs/en/output-styles) says "Each of the four other built-in styles keeps those instructions and adds its own", and its four non-Default styles include Concise. No probe observed it.
- Whether replies stay accurate. Reply accuracy was not assessed, so "What Concise kept" covers content, not the correctness of computed values.
- Delivery through user scope, the path a stow-wide default would use.
- Whether `/config` writes `outputStyle` into `claude/.claude/settings.json`. The probes ran in scratch directories, where `/output-style` wrote that directory's `.claude/settings.local.json`, so none observed the stow-source file. `guard-settings-session-keys.sh` does not list the key, so a written value would pass the guard.

## Sources

- [Claude Code output styles](https://code.claude.com/docs/en/output-styles) — Concise as a built-in style, the main-conversation and fork reach, full-length destructive-action confirmations, and the built-in styles keeping Claude Code's software-engineering instructions.
