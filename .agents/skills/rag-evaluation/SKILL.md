---
name: rag-evaluation
description: Design or assess MizanIQ-Next OCR, retrieval, citation and bilingual E2E evaluations, sealed-gold custody, forecast cutoffs and real AI performance measurements.
---

# RAG and AI evaluation

Use [ARCHITECTURE.md](../../../docs/ARCHITECTURE.md) §§6, 8 for scoring/custody/cutoffs and [SOFTWARE_FACTORY.md](../../../docs/SOFTWARE_FACTORY.md) for phase metrics, DEV floors and exact release scorecard. Follow [AGENTS.md](../../../AGENTS.md) authorization and evidence rules.

- Before a run freeze eligible scope, answerability, language/task strata, corpus/component grouping, gold/relevance sets, scorer, candidate/model/index/limits, timeout and permitted rerun policy. Do not relabel failures or tune thresholds after observing them.
- Retrieve authorized version-bound chunks/cells with headers; score all necessary operands and claim agreement separately from ranking relevance. Wrong cell/year/unit/status fails the task even with a valid document link.
- Report full answerable denominator including false abstention/timeouts/tool failure, separate unanswerable handling, AR/EN/mixed floors, Recall@10 macro/micro, all-required-evidence coverage, citation/claim false acceptance and real latency/resources. OCR reports numeric/identifier/header/scale accuracy and review load independently.
- Keep observed 95% point targets distinct from unchanged Wilson E2E and Hoeffding fractional-recall release gates. Read exact expressions from the plan/architecture rather than rounding cutoffs or treating fractional recall as binary trials.
- Gold/custodian must be genuinely independent for FINAL; connected duplicates stay in one split. Demo scorer/custody simulations and mocked outputs are DEV evidence only. Final feedback used for tuning retires FINAL.
- Forecast evaluation uses eligible received-and-approved data/policies at each rolling origin, separate validation/test and explicit undefined WAPE on zero denominator; no future revisions or test-selected predictor.

Return actual integer counts/denominators or fractional recall distribution, subgroup results/confidence, manifests, commands/environment and error cases. Missing actual runtime/measurement/independent custody is NOT_RUN/BLOCKED, never invented accuracy; model/GPU/service execution requires applicable authorization.
