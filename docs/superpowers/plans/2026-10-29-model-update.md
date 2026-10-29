# Ozon model update implementation plan

> For agentic workers: execute inline with superpowers:executing-plans; obtain a fresh whole-project code review before publishing.

Goal: update the supplied Excel in place conceptually, preserve its original control calculation, and publish a reproducible research repository.

Architecture: keep the existing workbook as an immutable baseline and patch a working copy using Artifact Tool. A portable Python model reads explicit JSON inputs, computes unique daily buyers and guardrails, and regenerates scenario CSV/results. A small supported-formula evaluator refreshes existing OOXML cells/caches without rebuilding workbook structure; fail on unsupported functions. Colab produces only user aggregates and small summaries from Drive data.

Spec: the user's request of 2026-10-29 authorizes scenario decisions, workbook editing, GitHub publication, and proceeding without coefficient approvals. Preserve UX Discovery, +10% initial relative uplift, four case gaps and separate H6 alternatives. Treat DAU/MAU, events/stocks and GMV/revenue separately.

Global constraints: no raw dataset or user-level identifiers in GitHub; all existing correct formulas and 45 checks retained; real audience scale only from verified public sources; 20.1% remains a control assumption. March DAU is not known quarterly mean; orders/DAU is a conditional intensity diagnostic, not measured daily CR.

Review focus: invalid shares and probabilities; cross-chunk deduplication; unsupported formula/cache failures; scenario comparison freshness; external scenario validity versus Ozon calibration. Each must have an executable test.

1. [ ] Extract original inputs and freeze baseline; add failing unit tests for model parity, unique users, zero/negative effects, cohort constraints, aggregation and formula round trips.
2. [ ] Implement Python model, Taobao aggregation/Drive-Colab pipeline, scenarios, source register and source-limited intensity checks. Run tests, compare original outputs.
3. [ ] Patch existing workbook with selector-driven scenarios, source annotations, saved scenario comparison and stale-state warning; run original 45 tests and extended parity checks; render changed/new views.
4. [ ] Write README, source audit, analytical conclusions, requirements and CI; run from clean packaged inputs without Drive/raw data; obtain fresh review and resolve material findings.
5. [ ] Publish one reviewed commit through connected GitHub tools; verify remote commit/tree and workbook blobs. Report results, risks and limitations.

Decisions: use an isolated project subfolder because the current workspace is not a Git checkout. Original file remains byte-identical. User explicitly waived additional design/plan approval. Native Excel execution is not guaranteed: engine and cache validation will be reported accurately. Public Python recalculation uses only the workbook's documented supported formula subset and zip/XML preservation; it is not a general Excel implementation. Final workbook authoring/visual QA uses bundled Artifact Tool.
