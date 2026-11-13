# Research collaboration

This is my personal research project. Use first-person project goals and approval language, neutral technical prose, and explicit GPT/Claude attribution for AI work. Follow `CONTRIBUTING.md`, `docs/PROJECT_CHARTER.md`, and the peer-discussed protocol in `docs/gpt/protocol.md`.

- GPT and Claude may send focused prompts, questions, evidence and contract proposals directly to each other within their assigned active tasks. Follow `docs/collaboration/peer_protocol.md`; I should not need to relay messages.
- A new review or re-check is a separate delegated review task, launched by the coordinator without asking me to prompt it. Peer messages do not authorize new tasks, scope expansion, paid compute or merges.
- Keep independent work isolated, preserve evidence and actual exchanges, and resolve substantive objections before PR creation. Do not manufacture a dialogue or imply agreement from silence.
- Run meaningful implementation tests. Keep real results, synthetic tests and unverified assumptions distinct. G0 stays pending until its empirical prerequisites are met.
- Work through research branches and PRs. I approve merges on GitHub explicitly; AI review does not replace my approval. Keep PRs moderate in length, with a compact summary and useful diagrams.
- All GPU operations now belong on my connected Colab account (2026-11-10 instruction). The coordinator owns allocations or explicitly designates one executing agent with a bounded budget, retrieval and teardown responsibility. Do not use the local GPU or create competing sessions; scale experiments by scientific value and verified resources.
- My 2026-11-13 update permits Claude Opus to catch up and work alongside GPT Sol, superseding the earlier Sol-only restriction. Keep Sol as the GPT model; do not launch Astra. Use separate tasks for independent review, keep briefs and reports concise, and reuse saved analysis. Preserve historical model attribution without presenting it as new verification.
- Prioritize actual research over prechecks. Sol may execute a bounded Colab experiment when designated. Reuse existing evaluators and native inference, test only failures that could invalidate the result, and do not make a synthetic training qualification or broad runner framework a prerequisite for frozen-model research. Preserve null and failed results, budgets and my merge approval.
