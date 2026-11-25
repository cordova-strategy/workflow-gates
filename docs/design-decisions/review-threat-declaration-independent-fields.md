# Review threat declaration: four independent fields

*2026-11-23.*

A reviewer's threat-model declaration is four independent fields, `surface`, `agent`, `caller` and `input`, not one ladder of tiers. The field definitions live in `claude-skills/skills/code-review/SKILL.md` § "Ripple effect triage" and are pinned verbatim in `claude-skills/skills/plan-review/ROUTING.md` § "Reviewer roles". This file records what the split rests on, so an editor of either skill can check the grounding without the plan that introduced it.

## What the sources ground

- **Intent marks `hostile`, not behavior.** NIST SP 800-30 Rev. 1 characterizes only adversarial threat sources by capability, intent and targeting. Accidental, structural and environmental sources carry only a range of effects. The `agent` field's rule that intent marks `hostile` follows that split.
- **`caller` and `input` are different attackers.** NIST AI 100-2 E2025 separates a direct prompting attack, where the attacker is the system's primary user, from an indirect prompt injection, where a third party acts through control of resources the system ingests. The first is the `caller` field and the second is the `input` field.
- **Content from anyone else can steer a cooperative agent.** AI 100-2 describes a hijacked agent performing an attacker-specified task. The `agent` field's clause that such content steers a cooperative agent into any shape rests on that.

## What the sources do not ground

Neither source models a software agent as a threat source with its own intent. SP 800-30 lists no agent or AI actor. AI 100-2 treats the agent as the victim that is hijacked, never as the attacker.

The `agent: hostile` value therefore rests on a maintainer requirement, not on these sources. The requirement is recorded as the `Ask:` line of `.claude/plans/threat-axes-independent-declaration.md`, which opens with the maintainer's words "I DO expect to model a hostile agent. That's essential to my work."

A future edit that cites NIST as backing `agent: hostile` is wrong. Dropping the field would need that requirement withdrawn, not a source found to contradict it.

## Sources

Each quotation was checked on 2026-11-23 against text extracted from the PDF at the URL given. A page number is the printed label, with the PDF page index in brackets.

- NIST Special Publication 800-30 Revision 1, *Guide for Conducting Risk Assessments* (September 2012) — https://doi.org/10.6028/NIST.SP.800-30r1, which redirects to https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-30r1.pdf.
  - Appendix D, "TABLE D-2: TAXONOMY OF THREAT SOURCES", page D-2 [PDF page 66]. The ADVERSARIAL row reads "Individuals, groups, organizations, or states that seek to exploit the organization's dependence on cyber resources" with the characteristics cell "Capability, Intent, Targeting". The ACCIDENTAL, STRUCTURAL and ENVIRONMENTAL rows carry the characteristics cell "Range of effects".
- NIST AI 100-2 E2025, *Adversarial Machine Learning: A Taxonomy and Terminology of Attacks and Mitigations* (March 2025) — https://doi.org/10.6028/NIST.AI.100-2e2025, which redirects to https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-2e2025.pdf.
  - Section 3.3, "Direct Prompting Attacks and Mitigations", page 43 [PDF page 56]: "DIRECT PROMPTING ATTACK attacks arise when the attacker is the primary user of the system, interacting with the model through query access."
  - Section 3.4, "Indirect Prompt Injection Attacks and Mitigations", page 50 [PDF page 63]: "INDIRECT PROMPT INJECTION attacks are enabled by RESOURCE CONTROL that allows an attacker to indirectly (or remotely) inject system prompts without directly interacting with the application." The next page adds that, unlike direct attacks, indirect ones are "mounted not by the primary user of a model but instead by a third party".
  - Section 3.4.2, "Integrity Attacks", the agent-hijacking passage: attackers can hijack a GenAI AGENT, "causing it to perform a malicious, attacker-specified task instead of (or in addition to) its intended, user-provided task".
