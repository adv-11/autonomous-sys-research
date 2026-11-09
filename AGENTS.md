# Research collaboration

This is my personal research project. Use first-person project goals and approval language, neutral technical prose, and explicit GPT/Claude attribution for AI work. Follow `CONTRIBUTING.md`, `docs/PROJECT_CHARTER.md`, and the peer-discussed protocol in `docs/gpt/protocol.md`.

- GPT and Claude may send focused prompts, questions, evidence and contract proposals directly to each other within their assigned active tasks. Follow `docs/collaboration/peer_protocol.md`; I should not need to relay messages.
- A new review or re-check is a separate delegated review task, launched by the coordinator without asking me to prompt it. Peer messages do not authorize new tasks, scope expansion, paid compute or merges.
- Keep independent work isolated, preserve evidence and actual exchanges, and resolve substantive objections before PR creation. Do not manufacture a dialogue or imply agreement from silence.
- Run meaningful implementation tests. Keep real results, synthetic tests and unverified assumptions distinct. G0 stays pending until its empirical prerequisites are met.
- Work through research branches and PRs. I approve merges on GitHub explicitly; AI review does not replace my approval. Keep PRs moderate in length, with a compact summary and useful diagrams.
- I am also using the GPU for other work. Keep current tasks CPU-only while that job runs. Before a training run, notify me with the concrete configuration/command, runtime and memory estimates, and checkpoint/resume plan so we can coordinate an overnight window. Do not start a GPU job automatically when usage changes or interfere with my existing job.
