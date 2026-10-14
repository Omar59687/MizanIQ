---
name: secure-development
description: Implement or review MizanIQ-Next authentication, tenant and document isolation, protected effects, parser/tool containment, privacy and recovery safeguards.
---

# Secure development

Use [AGENTS.md](../../../AGENTS.md), [ARCHITECTURE.md](../../../docs/ARCHITECTURE.md) §§2–4, 7–8, and the applicable security/regression gates in [SOFTWARE_FACTORY.md](../../../docs/SOFTWARE_FACTORY.md).

- Inventory every changed identity/table/view/function/worker/file/cache/tool path against §3 before granting access. Unclassified privilege stays blocked; no owner/BYPASSRLS runtime, writable-GUC authority or context-free data read.
- Enforce current tenant/document/transitive dependency rights at protected read and delivery, transaction-bound capabilities, pool cleanup, lease/fence and revision checks. Mask denied existence and ensure revocation overrides historical/cache access.
- Keep the selected HTTPS/session/CSRF/Host/Origin profile intact. Test the actual browser and DB boundaries, not only mocked authorization predicates.
- Protected effects bind exact intent/versions and consume once under current requester/approver rights. Demo may simulate distinct identities with explicit labels and a real healthy fixture journal; real actions retain two-human authority and actual custody/recovery readiness.
- Treat source/model/tool text as data; forbid authority creation, arbitrary execution/network/file access and raw source/secret traces. Restore stays closed without latest trusted deletion/revocation/receipt proof, in demo as well as real-world mode.

For each changed path return a concrete allowed/denied scenario, expected safe state and genuine security/regression evidence. Missing required boundary tests or recovery/rights proof is BLOCKED; isolate the affected path and use the plan's correction/re-review procedure.
