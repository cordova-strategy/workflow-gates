# Concise ships as the default output style in the stow-source settings file

*2026-11-20.*

`claude/.claude/settings.json` now sets `"outputStyle": "Concise"`, Claude Code's built-in Concise output style. Stow installs that file as every consumer's user-scope `~/.claude/settings.json`, so every stow user's main conversation and forks default to Concise, per Claude Code's output-styles page. This repository expects the default to apply in sessions started after `git pull`. Delivery through user scope is unmeasured, as "Not measured" says. Per the output-styles page, the value is case-sensitive and a value that matches no style falls back to Default. See [ui-notification-defaults-in-stow-source.md](ui-notification-defaults-in-stow-source.md) for why a personal preference and a shipped default are the same bytes under this layout.

The maintainer's aim was "hoping that the concise option will produce fewer words, make it easier for a human to read, but will keep like quality output". The measurements below show the replies to read-only prompts are shorter, the readability proxies showed no gain, and exploratory counts suggest Concise dropped content a reader may need, such as findings lists, per-option trade-offs and some caveats. They do not show that nothing a reader needs is lost.

## Why the default lives in the tracked file

The local-settings route in `claude/.claude/rules/settings-json-conventions.md` § "Settings.json conventions" has no user-scope counterpart under this layout, because Claude Code documents no user-scope local settings file. A user-wide default can therefore ship only in the tracked file.

## No per-user override ships

The maintainer's position is that output style is a user preference, not a repository preference. Per-user settings overrides belong to separate base/overlay settings work, PR #744. Its open status was read with `gh pr view` before 2026-11-20 and was not re-read.

No supported user-wide override of `outputStyle` ships. An uncommitted edit of the tracked line works on one machine and dirties the checkout. A per-project style also works, because a project's settings take precedence over the user-wide value. A supported user-wide override exists only if the base/overlay work admits the key.

Commit `acfbd96d` is on the PR's branch, `settings-base-render`. Its overlay allows only `autoMode`, `env`, `skillListingBudgetFraction` and `permissions.defaultMode` as keys, and `outputStyle` is none of them. That is from the script's source, read on 2026-11-20 and not run. It is that branch's behavior, not this tree's. Whichever of the two changes lands second rebases and decides where `outputStyle` sits. Asking that work to admit the key is a separate decision.

## Reach

The style applies to the main conversation and to forks. Other subagents run their own system prompt, so they follow `claude/.claude/CLAUDE.md` § "Prose and Output Format", which applies to every session and subagent. Claude Code's output-styles page says CLAUDE.md stays loaded whichever style is picked. The page does not say which wins when the two conflict. Output preferences reaches the session through a CLAUDE.md instruction, so the same unranked relation applies. `README.md` § "Concise output style by default" states that relation.

## Why CLAUDE.md does not name the style

`claude/.claude/CLAUDE.md` already states the concision rules every agent follows. A line saying the main session runs Concise would restate `settings.json`. It would also be false in any project whose own settings pick another style, because a project's settings take precedence over the user-wide value.

## Version floor

The output-styles page lists Concise as built in from Claude Code 2.1.237. `install.sh` sets `CLAUDE_CODE_MINIMUM_VERSION="2.1.295"`, and the README's Requirements section states the same floor. A supported install therefore always has Concise, and `install.sh` does not change. A build older than 2.1.237 probably reads `"Concise"` as a non-matching value and gives Default. That behavior is unverified and sits below the floor. Whether such a build still loads the rest of the stowed file, which holds the hook registrations and the permission deny entries, is also unverified and sits below the floor.

## Why `outputStyle` is not a guarded session key

`guard-settings-session-keys.sh` guards keys that hold one machine's own state. `docs/hooks.md` describes the class as session-scoped or Claude-Code-auto-written preferences. The page says `/output-style` and `/config` save the style to a project's `.claude/settings.local.json`. This repo gitignores that file.

A scripted probe confirmed the `/output-style` half: the stowed file's hash was unchanged across every run. The `/config` half is unverified.

Whether Claude Code writes `outputStyle` into the stowed file is the criterion that decides, not whether the setting is a personal preference. If `/config` does, the key falls inside the guard's class and a guard entry becomes mandatory. A guard entry added after this change lands has no bootstrap problem, because the guard compares staged settings with the default branch, which then already holds the staged value.

`test_output_style_stays_concise_in_stow_source_settings` in `claude/.claude/hooks/tests/test_hook_alignment.py` pins the declared value. It fails on:

- a removal;
- a duplicated `outputStyle` key, which a merge can leave in the file;
- any change, including a case change, which the output-styles page treats as a non-matching value that falls back to Default.

A hand edit of the tracked file that changes or removes the `outputStyle` value, or duplicates the key, fails this pin test when the suite runs. The guard does not cover the key. A commit that changes the line and the test together passes every mechanical check. It shows only as two deliberate hunks in review.

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

The scripted runs could not observe the approach walk-through. `claude -p` under `acceptEdits` has nobody to walk through to. In every completed edit and refactor run, neither style wrote text before the first edit. The main-session rule to walk the user through a proposed approach before acting therefore stays unobserved until ordinary use after the pull.

## Not measured

- Written artifacts beyond subagent briefs and commit messages, such as PR bodies, plan files and handoff notes.
- Models other than the Sonnet and Opus models probed.
- Claude Code builds other than 2.1.329, the one probed.
- Multi-turn sessions.
- Skill-driven relays, such as the main session relaying review findings, and the questions the main session asks the maintainer. The relay reported in "What Concise dropped" came from a plain prompt asking the session to delegate a review to a subagent and relay what it finds, with no skill driving the relay, at three samples per style.
- Whether Concise still runs its own edit to check it. In the one completed refactor pair, Default tried to run the code after its edit and Concise did not. That is one sample.
- Destructive-action confirmation and risk-disclosure text. The output-styles page says Concise keeps full length for destructive-action confirmations. No probe observed it.
- Whether Concise keeps Claude Code's built-in software-engineering instructions. The [output styles page](https://code.claude.com/docs/en/output-styles) says "Each of the four other built-in styles keeps those instructions and adds its own", and its four non-Default styles include Concise. No probe observed it.
- Whether replies stay accurate. Reply accuracy was not assessed, so "What Concise kept" covers content, not the correctness of computed values.
- Delivery through user scope, the path this change ships.

## Surfaces calibrated on Default output

- The commit-stall hook, `advance-past-commit-stall.sh`, fires only when the final sentence matches a fixed permission-verb phrase followed by a commit, push or PR object. Its only rewording signal is the `phrasing-drift` log line, which needs the verb half to match. Whether Concise rewords the commit offer is unmeasured.
- Headless `claude -p` harnesses probably run under a user-scope Concise unless they set a style of their own. That reach is unverified, because user-scope delivery itself is unmeasured. The harnesses are at least the skill evals in `evals/run_skill_evals.py`, the review bench in `evals/review_bench/runner.py` and the subagent-model-resolution measurement in `evals/measure_subagent_model_resolution.py`. Figures those harnesses recorded before this change come from sessions without the shipped style.
  - The skill evals write a project `settings.json` holding only `{"hooks": {}}`, so nothing at project scope overrides a user-scope `outputStyle` there.
  - The launch commands of the review bench and the subagent-model-resolution measurement were checked for a style override and none was found. Neither `evals/review_bench/runner.py` nor `evals/measure_subagent_model_resolution.py` mentions `outputStyle`, and neither passes `--settings`, `--setting-sources` or `--bare`.
  - The skill-eval disposition gate has a headless main session write a review that a judge then classifies. Concise shifted review text in the probes, with numbered findings and the closing priority line dropped. The number that can move is the treatment block rate, which the gate compares with the fixed 0.8 threshold in `evals/run_skill_evals.py` and `evals/README.md`. No `disposition-cases.json` ships in this tree, so any discrimination figure kept in a case's `note` field is the operator's own and was taken under Default if recorded before this change.
  - Beyond that launch-command check, the settings handling and reply parsers of every harness other than the skill evals were not read. That covers the review bench, the subagent-model-resolution measurement and the further launchers `evals/measure_main_session_rule_adherence.py`, `evals/measure_explore_recall.py` and `evals/run_replay_bench.py`. Whether a style change shifts what they measure is unknown.

## Maintainer rollback

Under the symlinked layout, a commit that deletes the line from the stowed file is live on `git pull` for every stow consumer. The rollback touches the full set:

- the `outputStyle` line in `claude/.claude/settings.json`;
- the pin test in `claude/.claude/hooks/tests/test_hook_alignment.py`;
- the README subsection "Concise output style by default" and its table-of-contents entry;
- the CHANGELOG, with a bullet announcing the rollback, or the removal of this change's bullet while it is still under `[Unreleased]`;
- a supersession note in this record, the one in-place edit a decision file allows.

Under the base/overlay layout, the deletion may not reach a machine that already rendered the key. Commit `acfbd96d` on the `settings-base-render` branch holds `render-settings.sh`, which this tree does not contain. That script carries forward every top-level key that base and overlay leave out and that is not base-owned or overlay-allowed. `outputStyle` is neither base-owned nor overlay-allowed there. That is from the script's source, read on 2026-11-20 and not run, and it is that branch's behavior, not this tree's. The pin test checks only the tracked source, so it cannot see that. The deletion route then depends on how that work places the key. One route is making it a base-owned key, which a render deletes once base no longer defines it. That deletion behavior is unverified.

## Sources

- [Claude Code output styles](https://code.claude.com/docs/en/output-styles) — Concise as a built-in style from 2.1.237, the case-sensitive `outputStyle` key, the user-wide default in `~/.claude/settings.json`, the main-conversation and fork reach, and the `/output-style` and `/config` write location.
- [Claude Code settings](https://code.claude.com/docs/en/settings) — settings scopes and precedence.
- PR #744, "Split settings.json into base and overlay files" — its open status was read with `gh pr view` before 2026-11-20 and was not re-read.
- The `settings-base-render` branch at commit `acfbd96d` — `claude/.claude/scripts/render-settings.sh`, read from source on 2026-11-20 and not run.
