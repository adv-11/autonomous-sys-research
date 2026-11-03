# Research collaboration and integration

1. Work on `gpt-research` and `claude-research`; never push research changes directly to `main`.
2. Keep evidence URLs, access dates, exact versions, and verification limitations in research documents. Do not overwrite the original plan's uncertain claims as verified facts.
3. Commit reproducible configs and meaningful tests with code. Keep datasets, credentials, papers, and weights out of Git.
4. Open a PR to `main` describing the research question, evidence, findings, limitations, and validation performed.
5. Have the other model review the actual diff and underlying evidence. Record reviewer model, reviewed commit, objections, fixes, and disposition. A model review is not a formal human GitHub approval.
6. Integrate sequentially: GPT PR first; then update Claude's branch against the merged `main`, resolve conflicts, review any substantive changes, and merge Claude's PR.
7. Merge only when all required checks pass, substantive objections are resolved, and the review explicitly recommends integration. If an external reviewer is required by GitHub rules, await their approval rather than bypassing it.
8. Log the resulting gate state. Never declare a research gate passed merely because a PR merged.

