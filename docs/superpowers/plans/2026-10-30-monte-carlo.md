# Monte Carlo uncertainty analysis

**Goal:** Add an auditable Monte Carlo extension and presentation charts after a verified local backup, without overwriting the deterministic workbook or its 35 scenarios.

**Architecture:** A separate NumPy engine reuses the original cohort/state equations. Shared audience draws and hypothesis-specific uplift/reach/risk draws are evaluated jointly, preserving unique-user counting and all case constraints. H6 variants share one modeled alternative because their inputs are identical. Original inputs and workbook remain unchanged.

**Files:** data/monte_carlo_assumptions.json; src/monte_carlo.py; scripts/run_monte_carlo.py; scripts/plot_monte_carlo.py; tests/test_monte_carlo.py; docs/monte_carlo_methodology.md; results/monte_carlo/.

**Constraints:** Probability laws and bounds are explicitly illustrative expert assumptions, not measured priors. Three profiles (triangular, uniform, low_effect), 100,000 accepted worlds each, fixed seeds. Reject and count infeasible cohort draws; report the resulting conditional input distribution. Never call simulation quantiles confidence intervals or winner frequency real success probability. Guardrails retain the current proxy definitions pending Ozon clarification. Negative utility and no safe action remain visible. Backups/raw user aggregates never go to GitHub.

**Validation:** Reproducible seeds; vector/scalar parity; fixed case totals and CR gaps; zero effect; deterministic ties; invalid configs; Spearman direction/constant inputs; CLI output metadata; original full suite; independent review.

- [x] Verified workspace backup: 228 files, archive plus SHA-256 manifest.
- [x] Write failing regressions and implement the simulator; scalar/vector parity, zero/ties and no-change regret verified.
- [x] Generate three profiles, sensitivity/rank diagnostics and convergence checks: 300,000 accepted worlds total.
- [x] Generate and visually inspect four standalone PNG/SVG figures; fix annotation overlaps; provide methodology and speaker notes.
- [x] Full suite: 47/47. Independent source/saved-result review: no blocking findings; its independent test invocation was timeboxed, so execution evidence is the parent suite. Local deliverables synchronized and a separate PR branch prepared.
