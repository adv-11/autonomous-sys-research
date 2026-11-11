# Research collaboration and integration

I use first-person prose for my project goals and decisions, and neutral technical prose where it reads better. Keep GPT and Claude contributions explicitly attributed; first-person writing must not imply I personally performed an AI-assisted source check or experiment.

Researchers can prompt each other directly within their active assignments, following [the peer protocol](docs/collaboration/peer_protocol.md). My current preference is GPT Sol only, with separate independent Sol tasks for review. Earlier GPT/Claude/Astra work keeps its original attribution. The coordinator handles review tasks; I do not need to relay prompts.

1. Work on research/topic branches such as `gpt-research` and `gpt-colab-research`; preserve the queued legacy `claude-research` contribution. Never push research changes directly to `main`.
2. Keep evidence URLs, access dates, exact versions, and verification limitations in research documents. Do not overwrite the original plan's uncertain claims as verified facts.
3. Commit reproducible configs and meaningful tests with code. Keep datasets, credentials, papers, and weights out of Git.
4. Before opening a PR, record researcher/reviewer findings, actual responses, evidence, resolutions and remaining objections. Active peers may discuss directly. Do not present a synthesis as a conversation that did not occur or infer assent from silence.
5. Have a separate independent reviewer task inspect the actual diff and underlying evidence; currently use Sol only. Record reviewer model, reviewed commit, objections, fixes, and disposition. An AI review is not a formal human GitHub approval. Every new delegated review or re-check is a separate review task.
6. After discussion and review, open a PR to `main` with a compact summary, moderate detail on evidence and decisions, validation and limitations, and relevant embedded images or SVG architecture/protocol diagrams. Distinguish conceptual diagrams from measured results and cite borrowed material.
7. I review the PRs directly on GitHub. **Do not merge a research PR without my explicit approval**, even when AI reviewers agree. If GitHub prevents me from formally approving my own PR, my explicit approval comment or instruction in the project conversation records that decision.
8. Integrate sequentially. Preserve the queued GPT/legacy-Claude order; update each branch against the merged `main`, resolve conflicts, and review substantive changes before seeking approval and merging. Subsequent Sol topic PRs also integrate one at a time. Checks must pass and substantive objections must be resolved; no new Claude task is implied by legacy authorship.
9. Log the resulting gate state. Never declare a research gate passed merely because a PR merged.

## Coordinator drift checks

I want periodic reports on whether the agents are moving the research forward. At task launch, define the deliverable, scope and stopping condition. Check scope and evidence at meaningful progress updates, on completion and before PR publication. For longer active tasks, aim for a check roughly every 15 minutes when new evidence is available; use actual messages, diffs and artifacts rather than repeatedly polling task status.

Report unsupported claims, work beyond the assignment, stalled dependencies, and repeated testing or optimization without a new failure or research decision. Distinguish an observed error from a suspected hallucination. Redirect active work with a focused prompt when needed; stop unnecessary tasks and do not create replacement or review loops merely to stay busy. Each report should state the finding, evidence, corrective action and next milestone. Keep an attributed record in [the drift log](docs/collaboration/task_drift_log.md). My approval still governs research merges.
