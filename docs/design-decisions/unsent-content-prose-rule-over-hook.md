# Pointing at unsent content is a prose rule, not an `AskUserQuestion` hook

*2026-11-24.*

The rule is the bullet in `claude/.claude/CLAUDE.md` § "Prose and Output Format" that begins "Point only at content you sent". This record covers why it is a prose rule rather than a display setting or a hook. It targets two shapes of one failure:

- An agent writes content only in its thinking, then asks an `AskUserQuestion` question that depends on it.
- A text reply points at content that no earlier reply held.

## Alternatives declined

- **A display setting.** The documented display controls are `/focus`, which shows only the last prompt, a one-line summary of tool calls and the final response, and the `Ctrl+O` transcript view, which shows detailed tool usage. Neither page describes either control as showing thinking, and the settings page lists no thinking display option.
- **A `PreToolUse` hook on `AskUserQuestion`.** It would read the transcript at the payload's `transcript_path` and deny the call when no assistant text block follows the engineer's last input. It is declined, not deferred, because its signal cannot separate the failure from correct behavior:
  - It fires on a self-contained question. The tool's input carries the question and its options, so a question that depends on nothing earlier rightly follows no text.
  - It passes a question that follows some text but not the text the question depends on. Telling those apart needs a judgment of what the question refers to, which a structural check of the transcript does not make.
  - It cannot see the second shape, because a text reply is not a tool call.
  - A deny reaches Claude before the call runs, since it "blocks the tool call, and shows Claude the reason" (the hooks documentation's "How a hook resolves" section). Every false fire on that route costs a denied call and a turn.
  - The hooks documentation says the transcript "is written asynchronously and may lag the in-memory conversation", so the hook can miss a text block sent just before the call and fire anyway.
- **Back-reference phrases.** Keying the same hook on phrases such as "above" or "that example" narrows its false fires, but a question can lean on unsent content in words no list holds.
- **A line in `nudge-answer-provenance.sh`.** That hook already fires on every `AskUserQuestion` call, at `PostToolUse`. Its context reaches the agent with the engineer's answer, after the engineer has seen the question, so it cannot prevent the first shape.

A read of local session transcripts checked the first two hook bullets against real questions and bore both out. It produced no figure published here, because no command that refuses a wider corpus produced it and the owner authorized none (`docs/private-project-redaction.md` § "Publishing a tooling measurement").

## Limits

- Nothing measures adherence to the bullet. No instrument under `evals/` scores whether an agent sends content before pointing at it. The replay bench measures comment density in `code-writer`'s first drafts (`evals/README.md` § "Replay bench").

## When to reopen

Reopen when both hold:

1. After the bullet ships, an engineer is again seen asking where content is that an agent pointed at.
2. A detector separates those questions from self-contained ones, measured on this repository's own corpus with a command that refuses a wider one.

The nearest existing shape for that measurement is `evals/README.md` § "Main session rule adherence gate", which scores rules from headless samples' tool calls. It is a one-time instrument and scores four other rules. A `PreToolUse` input carrying the agent's latest reply text would remove only the transcript-lag bullet, since the hooks documentation offers `last_assistant_message` only on `Stop` and `SubagentStop`.

## Sources

- https://code.claude.com/docs/en/fullscreen, https://code.claude.com/docs/en/interactive-mode and https://code.claude.com/docs/en/settings — `/focus`, the `Ctrl+O` transcript view, and the `/config` options.
- https://code.claude.com/docs/en/hooks — "Common input fields" for `transcript_path` and `last_assistant_message`, and "How a hook resolves".
- `claude/.claude/hooks/nudge-answer-provenance.sh` — the existing `AskUserQuestion` hook.
- `docs/private-project-redaction.md` § "Publishing a tooling measurement" — the scope bar for publishing a measured figure.
