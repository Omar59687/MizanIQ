---
name: integration-and-release
description: Assemble independently reviewed MizanIQ-Next packages, resolve ownership conflicts, validate regressions and assess phase or release readiness without unauthorized merge or deployment.
---

# Integration and release

Use [AGENTS.md](../../../AGENTS.md) ownership/branch/integrator rules and [SOFTWARE_FACTORY.md](../../../docs/SOFTWARE_FACTORY.md) evidence, CI, correction and release gates; [ARCHITECTURE.md](../../../docs/ARCHITECTURE.md) remains design authority.

- Confirm exact authorized action: preparing integration is not permission to commit/push/merge/deploy or enable real data/effects. Keep work off main and preserve uncommitted user changes; never initialize an unapproved baseline commit.
- Accept only packages with independent review bound to current base/content, complete required genuine checks and no blocking finding. Verify exclusive ownership/interface compatibility before assembling on a non-main integration branch.
- Resolve conflicts against contracts, never choose one side automatically. Any behavior/conflict/base/config change invalidates affected review/metrics; rerun integration and mandatory previous-phase regressions, then obtain independent review of the resulting candidate.
- Record local demo progress separately from full phase acceptance. Simulated identities/results do not satisfy real-human, qualified accounting, recovery/key/media or sealed FINAL requirements. Required-feature deferral cannot masquerade as V4 completion.
- For release, inspect the exact statistical/feature/security/custody and actual performance/recovery evidence; observed point estimates alone are insufficient. Missing/failed/inconclusive required evidence blocks release. No automatic paid/cloud or deployment fallback.

Return candidate/base identity, integrated file/package scope, review/check evidence, phase/demo/full-release status and remaining blocker. Commit/merge/release only if already explicitly authorized and all applicable gates pass; otherwise deliver the reviewable result without mutating protected Git/deployment state.
