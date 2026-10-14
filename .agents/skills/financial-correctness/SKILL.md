---
name: financial-correctness
description: Implement or review MizanIQ-Next financial facts, metric eligibility, deterministic precision, statement bridges, FX, consolidation and controlled revisions without inventing certification.
---

# Financial correctness

Use [ARCHITECTURE.md](../../../docs/ARCHITECTURE.md) §§2, 5–6.3 for exact method/precision/availability contracts, [SOFTWARE_FACTORY.md](../../../docs/SOFTWARE_FACTORY.md) for phase gold cases, and [AGENTS.md](../../../AGENTS.md) for work/review authority.

- Map every change to retained M-01–M-22 and owner requirements. Resolve concept, attribution, basis/framework, period/calendar, entity/coverage, currency/sign/scale, effective revision and complete source/ACL lineage before calculation.
- Apply the architecture's per-method domains and PP-01 operation/rounding boundaries exactly; preserve source literals and rational division lineage. Missing is not zero; never use a residual plug, sum stocks/YTDs, mix bases or double-count overlapping scopes.
- Keep category cash flows, cash balance movement and equity bridge separate. Check completeness independently from arithmetic balance and extraction verification. Revenue-only consolidation is not a profit/asset method; approved FX evidence still requires purpose/date compatibility.
- Every effective amendment/policy change invalidates current dependents; use fact-level approved supersession and one compatible manifest, never latest-upload precedence.
- Pair each method with independently worked eligible and negative cases and expected status. Deferred/missing methods fail safely and stay on feature coverage; demo fixtures can exercise proposed math with PRELIMINARY/simulated labels, never professional certification.

Return method/case/version coverage, exact outputs/residuals/statuses and reproducible evidence. Qualified accounting review is required where the architecture specifies it; AI/code review or correct example arithmetic cannot manufacture that sign-off.
