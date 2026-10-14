---
name: test-and-review
description: Verify MizanIQ-Next changes with required phase tests, previous-phase regression and independent candidate review while preventing missing-test or mock-metric green results.
---

# Tests and independent review

Read [SOFTWARE_FACTORY.md](../../../docs/SOFTWARE_FACTORY.md) applicable phase, CI strategy and correction procedure, [AGENTS.md](../../../AGENTS.md) reviewer rules, and changed contracts in [ARCHITECTURE.md](../../../docs/ARCHITECTURE.md).

- Bind review to exact candidate/base and authorization/mode. Reviewer must not author the change; inspect raw diff/contracts before adopting implementer explanations. This review does not establish architecture approval, gold custody or professional financial sign-off.
- Map changed requirements to meaningful unit, actual boundary integration, security, regression and applicable measurement checks; include all mandatory predecessor suites. An assertion mirroring implementation or a mocked service cannot prove a DB/browser/OCR/model boundary.
- Verify test discovery/counts, exit status, skips/xfails, fixture/scorer identity and result artifacts. Missing/zero/skipped required checks, stale artifacts and absent applicable real measurements fail or block acceptance, even if a runner exits zero.
- Treat genuine docs-only validation distinctly; reviewer must confirm no behavior/config/corpus/scorer change before code tests are NOT_APPLICABLE. This never waives full phase tests. Sealed FINAL stays outside developer access.
- Run only authorized available checks; preparation permits document/skill validation, not application tests/installations. Report unavailable prerequisites instead of fabricating commands/results.

Return PASS/CHANGES_REQUIRED/BLOCKED, findings by severity with exact location and counterexample, evidence inspected/executed, counts/denominators and unresolved gates. Fixes require the owning implementer, reproducing regression, affected/prior-suite rerun and independent re-review; never relax a gate to green.
