# Research collaboration and integration

1. Work on `gpt-research` and `claude-research`; never push research changes directly to `main`.
2. Keep evidence URLs, access dates, exact versions, and verification limitations in research documents. Do not overwrite the original plan's uncertain claims as verified facts.
3. Commit reproducible configs and meaningful tests with code. Keep datasets, credentials, papers, and weights out of Git.
4. Before opening a PR, exchange GPT and Claude findings, discuss substantive disagreements, and record the discussion with each model's response, evidence, resolutions, and remaining objections. Do not present one model's synthesis as a conversation that did not occur.
5. Have the other model review the actual diff and underlying evidence. Record reviewer model, reviewed commit, objections, fixes, and disposition. A model review is not a formal human GitHub approval. Every new delegated review or re-check is a separate review task.
6. After discussion and review, open a PR to `main` with a compact summary, moderate detail on evidence and decisions, validation and limitations, and relevant embedded images or SVG architecture/protocol diagrams. Distinguish conceptual diagrams from measured results and cite borrowed material.
7. Advait reviews the PRs directly on GitHub. **Do not merge a research PR without Advait's explicit approval**, even when AI reviewers agree. If GitHub prevents an owner from formally approving their own PR, an explicit approval comment from Advait or an explicit instruction in this conversation can record that decision.
8. Integrate sequentially: GPT PR first; then update Claude's branch against the merged `main`, resolve conflicts, and review substantive changes before seeking approval and merging Claude's PR. Checks must pass and substantive objections must be resolved.
9. Log the resulting gate state. Never declare a research gate passed merely because a PR merged.
