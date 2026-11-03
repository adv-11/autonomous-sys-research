# Project charter

## Authority and scope

This is my **personal research project at PhD depth**, with no course timeline. This scope, clarified on 2026-11-03, supersedes the course deadlines, grading deliverables, professor approval, and six-/ten-week schedules in `RESEARCH_PLAN.md`.

I authorized initializing Git in this directory, creating a GitHub repository, conducting GPT and Claude research on separate branches, collaboration, and sequential integration after PRs and approvals. This supersedes the original plan's instruction against unrequested commits or pushes. The repository is public.

I want two research subagents, GPT and Claude, to discuss their findings **before** PR creation. Review materials should have moderate detail, a compact summary, and relevant images or SVG architecture diagrams. I'll review the PRs directly on GitHub. Publication is authorized; research merges require my explicit approval.

## Research standard

- Verify paper identity, version, full text, code, dataset access, and licensing against primary sources. Search snippets do not establish a paper's methodology or absence of prior work.
- Distinguish source evidence, inference, preregistered hypotheses, toy validation, and real empirical results.
- Record disconfirming evidence and negative results. Never invent dataset counts, benchmark results, or completed GPU checks.
- Preserve the core question of threshold transfer. Architectural explanations require controls and cannot follow from comparing a handful of differently trained models alone.
- Keep calibration, threshold selection, and final test data separate. Report infeasible recall targets explicitly.
- No paid cloud runs without an estimate in the run log. Retain my original $20–30 ceiling unless I revise it. Downloads requiring accounts or acceptance of dataset terms remain gated on lawful access.
- Advancement through experimental gates requires adequate evidence, not the passage of calendar time.

## Immediate scope

Finish a source-backed Phase 0 audit and a reviewable protocol/tooling foundation. Dataset acquisition, full GPU compatibility tests, model training, and measured comparisons are separate milestones and remain pending until their prerequisites are met.
