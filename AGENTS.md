# MizanIQ-Next Software Factory

## Authority and repository boundaries

- Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) completely before first project work or after architecture changes. It is the single canonical design; approved owner requirements remain intact, detailed methods/thresholds remain proposed, and architecture is not independently approved or frozen.
- Read the applicable phase in [docs/SOFTWARE_FACTORY.md](docs/SOFTWARE_FACTORY.md). This file governs collaboration; that plan governs tests, CI and evidence; the architecture governs product/security/financial behavior. Skills route specialized work rather than redefining these contracts. Report contradictions with exact references; do not resolve them by silently weakening a gate.
- Default scope is factory preparation only: Markdown instructions/skills/plan. The owner separately authorized the initial documented baseline, origin setup for `https://github.com/Omar59687/MizanIQ.git`, one initial commit and publication of `main` only. This bounded authorization covers AGENTS.md, docs/ARCHITECTURE.md, docs/SOFTWARE_FACTORY.md, the six repository-local SKILL.md files and a minimal .gitignore. Product code, databases, installations, model/GPU execution, paid services, further commits/pushes and deployment require separate authorization covering those actions. Instructions are not authorization. Preserve existing user files and uncommitted work.
- Work only in this repository/explicitly authorized repository workspace, never the old MizanIQ repository. No versioned architecture copies, ZIPs, review folders, unnecessary agent configurations or generated scaffold placeholders.
- No direct work on `main`. Verify branch/status before editing; use `factory/<task>` or `phase/vN-<package>` branches. An unborn repository may switch to a named branch without committing. No initial baseline commit, staging, merge or push is inferred from preparation permission.
- Preserve the modular monolith, approved financial fact store, deterministic calculations, local protected sources, bilingual evidence, versioned snapshots and bounded workers. No GL/posting/statutory certification, remote deployment, cloud inference fallback or out-of-scope feature expansion.
- V0–V3 DEVELOPMENT/DEMO is synthetic-only under architecture §2.1–2.2, with real authentication/isolation/revocation/deletion checks and a durable fixture journal. Simulated identities/approvals/custodians are labeled, never real independent human approval or professional certification. Real protected effects retain two-human control and verified recovery/custody prerequisites.
- Zero paid services: no billed API/model/GPU, subscription, paid runner, storage or hosting; no credentials/finance data sent to services. Do not assume a free tier, trial or quota is available. Future checks default to local execution; permission for one action never permits automatic paid/cloud fallback.

## Responsibilities

| Role | Responsibility and limits |
|---|---|
| Orchestrator | Confirm authorization/mode/phase, map dependencies, define bounded packages and exclusive file ownership, allocate 1–5 logical implementers adaptively, reserve review/integration capacity, maintain acceptance/evidence status. Does not approve its own implementation as independent review |
| Implementer | Read assigned contracts; change only leased files on assigned branch/workspace; add meaningful required tests and record genuine results when authorized. Return a reviewable diff and concise evidence; no unassigned shared-file edits or integration |
| Independent reviewer | Separate agent/person who did not author the change; inspect exact candidate/base diff against contracts and required tests, form findings independently, verify evidence and scope. Read-only review with severity/location/counterexample; PASS, CHANGES_REQUIRED or BLOCKED. Code review is not accounting sign-off, real two-human action approval or independent gold custody |
| Integrator | Only role allowed to assemble reviewed packages or operate shared Git/index state during an implementation wave; verify review binds exact candidate and base, resolve conflicts deliberately, rerun affected plus previous-phase checks, obtain re-review for changed content. Integrates into a non-main integration branch first; merges/releases only within explicit authorization |

One agent may orchestrate and integrate sequentially, but cannot independently review changes it authored. No reviewer available means integration remains BLOCKED; simulated accounts do not create an independent code reviewer.

## Owner-selected model policy

| Role | Model | Reasoning effort |
|---|---|---|
| Orchestrator | SOL | Medium |
| Implementer | Muse 1.3 | X-High |
| Independent reviewer | Luna | Medium |
| Integrator | Coordinated by SOL | Medium for SOL |

Never increase SOL or Luna above Medium. These are owner-selected requirements, not evidence of tested platform configuration. Verify the actual model and effort when assigning each role; record unavailable selections as BLOCKED/unverified and do not silently substitute a different model. This policy does not authorize paid services or implementation.

## Adaptive parallelism and ownership

1. Start with one implementer for a narrow/shared dependency. Use 2–3 for independent interfaces/modules with disjoint files; use 4–5 only when that many independent packages, resource capacity and tooling slots actually exist. Five is a ceiling, not a target.
2. Active implementers = minimum of ready independent packages, five, tool concurrency remaining after orchestrator/reviewer capacity, and measured local resource capacity. With four total active-agent slots and an active orchestrator, at most three implementers may run; reserve/reuse a slot for review, or use waves. Never configure unavailable slots or parallel model/OCR jobs to match agent count.
3. Before delegation record, in the task's coordination message/PR body, `package ID; mode/phase; owner; branch/workspace; exact files/globs; base revision/digest; inputs/interfaces; acceptance cases; commands/evidence; blocked dependencies`. One writer per file including tests/fixtures/docs. Lockfiles, root config, shared schemas/interfaces and CI belong to a designated owner/integrator.
4. If work shares a file, serialize or split at an agreed interface first. If separate worktrees are available and authorized, give each package its own non-main branch/worktree; otherwise use exclusive leases in the shared checkout with **no concurrent branch/index/Git mutation**. Implementers return diffs; only integrator handles shared Git state. Do not overwrite another agent/user change.
5. Ownership transfer requires the previous writer to stop and hand off its diff/evidence; orchestrator records the new owner. New files within another lease count as conflicts. Pause the affected package on conflict, preserve both changes, resolve against contracts, then re-review the resulting candidate.
6. Independent review precedes integration. New edits/rebases/conflict resolutions invalidate affected review and measurements; review/check the exact resulting content, not a previously passing branch name. Never turn CHANGES_REQUIRED/BLOCKED into PASS by deleting tests or narrowing eligibility after results.

## Context, skills and reporting

After the first full architecture read, load only relevant sections/diffs and one applicable skill at a time; refresh changed contracts before work. Delegate minimum raw context: package, relevant architecture/plan references, owned files, base/candidate identity and interfaces, not the entire chat/history or all six skills. Reviewer receives raw candidate and contracts, not a suggested verdict; implementation explanations may be consulted after initial assessment.

Repository skills reside in `.agents/skills/<name>/SKILL.md`:

| Skill | Route |
|---|---|
| project-conventions | Scope, mode, package/interfaces and repository workflow |
| secure-development | Authentication, isolation, approvals, parser/tool privacy and recovery safeguards |
| financial-correctness | Financial eligibility, deterministic math, provenance, revisions and certification status |
| rag-evaluation | Retrieval, citation/claim scoring, OCR/AI experiments, split/custody and forecasting evaluation |
| test-and-review | Required checks, independent review, no false-green evidence and corrections |
| integration-and-release | Reviewed candidate assembly, regression, phase status and authorized release |

Report `outcome; exact files/candidate; tests/measurements with command, count and result; review verdict; remaining blocker/next action`. Use PASS/FAIL/BLOCKED/NOT_RUN/NOT_APPLICABLE precisely, with mode and applicability rationale. Link evidence rather than dumping logs; never log secrets/source snippets. Unperformed checks, mocked model outputs and simulated approvals cannot establish achieved quality, independent approval or production certification. Mandatory PR checks and phase regressions are defined in the factory plan; sealed FINAL is never a development test.
