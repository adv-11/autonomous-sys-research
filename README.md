# Threshold Transfer Under Distribution Shift

Personal research by **Advait Shinde** on whether confidence thresholds selected on clear-day images preserve pedestrian recall under night and adverse-weather shift.

This project studies real-time object detectors, their operating points, and object-detection calibration. The aim is a rigorous, reproducible research contribution. Novelty, detector comparisons, and safety implications remain hypotheses until verified against primary sources and real experiments. Detection recall alone does not establish driving safety.

## Research questions

1. How much recall and false-positive burden change when a clear-day threshold is frozen and transferred to a shifted condition?
2. Do calibration metrics add predictive value beyond accuracy and attainable recall?
3. Which apparent improvements survive independent evaluation, class-policy controls, and uncertainty estimates?

The original [research plan](RESEARCH_PLAN.md) is a starting document whose literature claims require verification. The project is personal research without a course timeline; the course-specific requirements in the original plan are superseded by [the project charter](docs/PROJECT_CHARTER.md).

## Collaboration

- `main`: reviewed work, integrated through PRs.
- `gpt-research`: GPT evidence, methodology, and reproducibility work.
- `claude-research`: independent Claude evidence and critique.

The two research subagents exchange findings and discuss disagreements before opening PRs. PRs include a compact summary, source-backed decisions, and relevant images or SVG diagrams. Advait reviews and explicitly approves them on GitHub; integration is sequential: GPT first, then Claude after updating against `main`. AI review is recorded separately from Advait's approval.

## Status

Phase 0: source verification, protocol design, and environment inventory. No training, dataset evaluation, or empirical findings have been produced. See [the gate log](docs/gate_log.md) and [workflow](CONTRIBUTING.md).
