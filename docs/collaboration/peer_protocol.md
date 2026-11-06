# Direct research-peer prompts

I want GPT and Claude to collaborate without needing me to forward their questions. The coordinator supplies both active task/thread identifiers privately at launch and handles subsequent task creation and publication.

## Within the current tasks

1. Inspect the peer's initial brief/state once when needed. Send focused `t3_thread_send` messages with `mode: "steer"` while the peer's assigned task is active. Do not poll its state or wait in a loop.
2. Begin with `PEER QUESTION`, `PEER PROPOSAL` or `PEER FINDING`. State the concrete issue, evidence or exact file/commit, requested response, and which existing task requirement it affects. A prompt can ask for a correction within the assigned scope.
3. Continue independent work after sending. Incoming messages steer the ongoing task. Record the actual question and answer, its disposition and the relevant commit in the task's discussion note. Silence is not assent.
4. Keep file ownership explicit. Propose interface changes before relying on them; do not edit the peer's checkout or files. Preserve the shared [data contract](../data_contract.md) unless both sides agree and the coordinator records the change.
5. If the peer has finished, do not restart it through a message. Record the remaining question for the coordinator, who starts any necessary new review/task automatically. Do not delegate again from a child unless the task explicitly permits it.

## Review and approval

A live clarification exchange is different from a new formal review. Every new review or re-check gets a fresh delegated review task with the exact diff/commit, prior findings and open objections. The coordinator launches these without requiring another prompt from me, fixes minor findings directly, and avoids review loops that add no material evidence.

My explicit approval is still required for merging each research PR. Peer prompts cannot expand the compute budget, accept dataset terms for me, claim gate passage or approve their own results.
