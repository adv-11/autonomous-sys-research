# Threshold Transfer Under Distribution Shift

I'm studying whether confidence thresholds selected on clear-day images preserve pedestrian recall under night and adverse-weather shift.

My focus is real-time object detectors, their operating points, and object-detection calibration. I want a rigorous, reproducible research contribution. Novelty, detector comparisons, and safety implications remain hypotheses until verified against primary sources and real experiments. Detection recall alone does not establish driving safety.

## Research questions

1. How much recall and false-positive burden change when a clear-day threshold is frozen and transferred to a shifted condition?
2. Do calibration metrics add predictive value beyond accuracy and attainable recall?
3. Which apparent improvements survive independent evaluation, class-policy controls, and uncertainty estimates?

My original [research plan](RESEARCH_PLAN.md) is a starting point whose literature claims require verification. This is personal research without a course timeline; [my project charter](docs/PROJECT_CHARTER.md) supersedes the original course requirements.

## Collaboration

- `main`: reviewed work, integrated through PRs.
- `gpt-research`: GPT evidence, methodology, and reproducibility work.
- `claude-research`: independent Claude evidence and critique.

I'm using two research subagents, GPT and Claude, to investigate independently and discuss disagreements before opening PRs. Each PR includes a compact summary, source-backed decisions, and relevant images or SVG diagrams. I review and explicitly approve the PRs on GitHub before they merge: GPT first, then Claude after updating against `main`. AI review is recorded separately from my approval.

## Status

Phase 0: source verification, protocol design, and environment inventory. No training, dataset evaluation, or empirical findings have been produced. See [the gate log](docs/gate_log.md) and [workflow](CONTRIBUTING.md).
