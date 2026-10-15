"""MizanIQ-Next V0-01A local CI check entrypoint (genuine, failure-enforcing).

Runs formatter/lint/type/test checks with real exit codes and enforces the
SOFTWARE_FACTORY.md CI evidence gate over a deterministic candidate identity:

* Candidate identity is a reproducible SHA-256 digest over relevant source,
  configuration, test, dependency and CI-workflow bytes (tracked and untracked
  alike). Generated evidence itself is excluded from the digest.
* Evidence binds the candidate digest, base revision, required-test inventory
  version/digest, per-file inventory, JUnit case identities/outcomes and counts.
* Verify-only recomputes everything from disk: candidate bytes, inventory,
  JUnit XML cases/outcomes/counts and required suites/cases. Recorded JSON
  counts are never trusted as proof of execution. Timestamps are informational
  only and never the sole integrity signal.

Usage:
    python scripts/check.py [--root PATH] [--min-tests N]
        [--evidence PATH] [--junit PATH]
    python scripts/check.py --verify-only [--root PATH] [--evidence PATH]
        [--min-tests N]
    python scripts/check.py --docs-only [--base REV]

No continue-on-error, no swallowed exit status, no paid services.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

REPO_ROOT = Path(__file__).resolve().parents[1]
# Historical fact, not trust: the initial main commit carries no required-test
# inventory. The ONLY permitted bootstrap compares the verified remote main
# SHA against this exact value; anything else without an inventory fails closed.
INITIAL_MAIN_SHA = "e5af075fb4e741936354c083ee1a7e9b1a5359df"
# Trust may only resolve through main refs. Arbitrary refs, branch names or
# candidate-supplied SHAs are rejected so a candidate cannot point the gate at
# a baseline it controls.
TRUST_REFS_ALLOWLIST: tuple[str, ...] = (
    "origin/main",
    "refs/remotes/origin/main",
    "main",
    "refs/heads/main",
)
DEFAULT_TRUST_REF = "origin/main"
INVENTORY_REL = "tests/required_inventory.json"
# Proposed FIRST inventory (V0-01A-3, reviewed proposal, not approval).
# Bootstrap requires the candidate manifest to exactly equal this set:
# missing AND extra suites/cases both fail as bootstrap-incomplete.
# This constant is reviewable checker logic covered by the candidate digest;
# real trust comes from independent review plus merge into main, never from
# this list alone.
PROPOSED_INITIAL_SUITES: tuple[str, ...] = (
    "tests.test_artifacts",
    "tests.test_ci_gate",
    "tests.test_ci_gate_integration",
    "tests.test_config",
    "tests.test_health",
)
PROPOSED_INITIAL_CASES: frozenset[str] = frozenset(
    {
        "tests.test_artifacts::test_generated_evidence_is_gitignored",
        "tests.test_artifacts::test_placeholder_is_trackable",
        "tests.test_artifacts::test_workflow_gates_only_supported_event_contexts",
        "tests.test_artifacts::test_workflow_resolves_trusted_main_base",
        "tests.test_artifacts::test_workflow_uploads_evidence_as_artifacts",
        "tests.test_ci_gate::test_docs_only_flags_behavioral_changes",
        "tests.test_ci_gate::test_min_tests_threshold_is_positive",
        "tests.test_ci_gate::test_missing_case_detection",
        "tests.test_ci_gate::test_missing_suite_detection",
        "tests.test_ci_gate::test_no_missing_when_all_suites_present",
        "tests.test_ci_gate::test_stale_mtime_helper_is_supplementary_only",
        "tests.test_ci_gate_integration::test_adding_workflow_invalidates_evidence",
        "tests.test_ci_gate_integration::test_aggregate_cli_verify_pass_on_isolated_copies",
        "tests.test_ci_gate_integration::test_aggregate_verify_pass_on_isolated_copies",
        "tests.test_ci_gate_integration::test_docs_only_detects_behavioral_change",
        "tests.test_ci_gate_integration::test_evidence_reuse_from_different_candidate_fails",
        "tests.test_ci_gate_integration::test_failed_test_fails",
        "tests.test_ci_gate_integration::test_junit_tamper_without_evidence_update_fails",
        "tests.test_ci_gate_integration::test_missing_required_individual_case_fails",
        "tests.test_ci_gate_integration::test_missing_required_suite_fails",
        "tests.test_ci_gate_integration::test_modifying_workflow_invalidates_evidence",
        "tests.test_ci_gate_integration::test_removing_workflow_invalidates_evidence",
        "tests.test_ci_gate_integration::test_source_edit_preserving_mtime_detected_in_isolated_workspace",
        "tests.test_ci_gate_integration::test_trust_bootstrap_exact_initial_pending_review",
        "tests.test_ci_gate_integration::test_trust_bootstrap_rejected_on_other_sha",
        "tests.test_ci_gate_integration::test_trust_bootstrap_rejects_incomplete_proposal",
        "tests.test_ci_gate_integration::test_trust_bootstrap_when_base_has_no_inventory",
        "tests.test_ci_gate_integration::test_trust_extension_passes",
        "tests.test_ci_gate_integration::test_trust_forged_evidence_sha_rejected",
        "tests.test_ci_gate_integration::test_trust_invalid_base_fails_closed",
        "tests.test_ci_gate_integration::test_trust_main_advance_invalidates_evidence",
        "tests.test_ci_gate_integration::test_trust_present_clean_when_nothing_removed",
        "tests.test_ci_gate_integration::test_trust_reduction_fails",
        "tests.test_ci_gate_integration::test_trust_regen_does_not_authorize_reduction",
        "tests.test_ci_gate_integration::test_trust_rename_detected_as_removal",
        "tests.test_ci_gate_integration::test_trust_unresolvable_ref_fails_closed",
        "tests.test_ci_gate_integration::test_unchanged_workflows_preserve_evidence",
        "tests.test_ci_gate_integration::test_unexpected_skip_fails",
        "tests.test_ci_gate_integration::test_workflow_files_all_included_in_candidate",
        "tests.test_ci_gate_integration::test_zero_collected_tests_fails",
        "tests.test_config::test_allows_loopback_hosts_only",
        "tests.test_config::test_default_mode_is_development_demo",
        "tests.test_config::test_mode_is_case_insensitive_but_normalized",
        "tests.test_config::test_rejects_production_mode",
        "tests.test_config::test_rejects_public_listeners",
        "tests.test_config::test_rejects_real_world_mode_variants",
        "tests.test_config::test_rejects_unknown_settings_keys",
        "tests.test_health::test_build_app_refuses_non_synthetic_settings_object",
        "tests.test_health::test_complete_route_inventory_is_healthz_only",
        "tests.test_health::test_documentation_endpoints_are_disabled",
        "tests.test_health::test_health_payload_builder_is_typed_and_non_sensitive",
        "tests.test_health::test_healthz_payload_contains_no_sensitive_keys",
        "tests.test_health::test_healthz_returns_ok_with_synthetic_marker",
        "tests.test_health::test_no_business_endpoints_exist",
        "tests.test_health::test_only_healthz_is_application_route",
    }
)

REQUIRED_FILES: tuple[str, ...] = (
    "app/__init__.py",
    "app/config.py",
    "app/main.py",
    "tests/__init__.py",
    "tests/test_config.py",
    "tests/test_health.py",
    "tests/test_ci_gate.py",
    "tests/test_ci_gate_integration.py",
    "tests/test_artifacts.py",
    "tests/required_inventory.json",
    "scripts/check.py",
    "scripts/__init__.py",
    "requirements.txt",
    "pyproject.toml",
    ".env.example",
    ".github/workflows/ci.yml",
    "evidence/.gitkeep",
)

REQUIRED_SUITES: tuple[str, ...] = (
    "tests.test_config",
    "tests.test_health",
    "tests.test_ci_gate",
    "tests.test_ci_gate_integration",
    "tests.test_artifacts",
)

CANDIDATE_DIRS: tuple[str, ...] = ("app", "tests", "scripts")
CANDIDATE_WORKFLOW_DIRS: tuple[str, ...] = (".github/workflows",)
CANDIDATE_TOP_FILES: tuple[str, ...] = (
    "requirements.txt",
    "pyproject.toml",
    ".env.example",
    ".gitignore",
)
EXCLUDE_DIR_NAMES: frozenset[str] = frozenset(
    {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
)
EXCLUDE_SUFFIXES: tuple[str, ...] = (".pyc", ".pyo")

DEFAULT_MIN_TESTS = 12
DEFAULT_EVIDENCE = REPO_ROOT / "evidence" / "ci-evidence.json"
DEFAULT_JUNIT = REPO_ROOT / "evidence" / "junit.xml"

CODE_OWNING_PREFIXES: tuple[str, ...] = (
    "app/",
    "tests/",
    "scripts/",
    "requirements.txt",
    "pyproject.toml",
    ".github/",
    ".env.example",
)


class JunitCounts(TypedDict):
    total: int
    failures: int
    errors: int
    skipped: int


@dataclass(frozen=True)
class JunitCase:
    case_id: str
    outcome: str  # one of: passed, failure, error, skipped


@dataclass(frozen=True)
class StepResult:
    name: str
    command: list[str]
    exit_code: int
    passed: bool


def _run(cmd: list[str], cwd: Path) -> StepResult:
    proc = subprocess.run(cmd, cwd=cwd)
    return StepResult(
        name=" ".join(cmd),
        command=cmd,
        exit_code=proc.returncode,
        passed=proc.returncode == 0,
    )


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_candidate_files(root: Path) -> list[str]:
    """Deterministic inventory of candidate files (posix rel paths, sorted).

    Covers relevant source/config/tests/deps bytes plus every workflow file
    under .github/workflows/, tracked or untracked alike. Generated evidence
    under evidence/ (except .gitkeep) and bytecode/caches are always excluded.
    """
    rels: set[str] = set()
    for dirname in (*CANDIDATE_DIRS, *CANDIDATE_WORKFLOW_DIRS):
        base = root / dirname
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix in EXCLUDE_SUFFIXES:
                continue
            if any(part in EXCLUDE_DIR_NAMES for part in path.parts):
                continue
            rels.add(path.relative_to(root).as_posix())
    for rel in (*CANDIDATE_TOP_FILES, INVENTORY_REL):
        if (root / rel).is_file():
            rels.add(rel)
    return sorted(rels)


def compute_candidate_identity(root: Path) -> tuple[str, dict[str, str]]:
    """Return (candidate_digest, {rel: sha256}) over candidate file bytes."""
    inventory: dict[str, str] = {}
    for rel in collect_candidate_files(root):
        inventory[rel] = _sha256_file(root / rel)
    digest = hashlib.sha256()
    for rel in sorted(inventory):
        digest.update(rel.encode("utf-8"))
        digest.update(b"\x00")
        digest.update(bytes.fromhex(inventory[rel]))
        digest.update(b"\x00")
    return digest.hexdigest(), inventory


def parse_junit_cases(path: Path) -> tuple[JunitCounts, dict[str, int], list[JunitCase]]:
    """Parse pytest JUnit XML into counts, per-suite counts and case outcomes."""
    tree = ET.parse(path)
    root = tree.getroot()
    total = failures = errors = skipped = 0
    per_suite: dict[str, int] = {}
    cases: list[JunitCase] = []
    for case in root.iter("testcase"):
        total += 1
        classname = str(case.attrib.get("classname", "unknown") or "unknown")
        name = str(case.attrib.get("name", "unknown") or "unknown")
        case_id = f"{classname}::{name}"
        if case.find("failure") is not None:
            outcome = "failure"
            failures += 1
        elif case.find("error") is not None:
            outcome = "error"
            errors += 1
        elif case.find("skipped") is not None:
            outcome = "skipped"
            skipped += 1
        else:
            outcome = "passed"
        per_suite[classname] = per_suite.get(classname, 0) + 1
        cases.append(JunitCase(case_id=case_id, outcome=outcome))
    cases.sort(key=lambda c: c.case_id)
    return (
        JunitCounts(total=total, failures=failures, errors=errors, skipped=skipped),
        per_suite,
        cases,
    )


def parse_junit_xml(path: Path) -> tuple[JunitCounts, dict[str, int]]:
    """Backward-compatible counts-only JUnit parse."""
    counts, per_suite, _ = parse_junit_cases(path)
    return counts, per_suite


def compute_junit_digest(cases: list[JunitCase]) -> str:
    """Deterministic digest over sorted case identities and outcomes."""
    digest = hashlib.sha256()
    for case in sorted(cases, key=lambda c: c.case_id):
        digest.update(case.case_id.encode("utf-8"))
        digest.update(b"\x00")
        digest.update(case.outcome.encode("utf-8"))
        digest.update(b"\x00")
    return digest.hexdigest()


def load_required_inventory(root: Path) -> dict[str, object]:
    """Load the explicit mandatory test inventory manifest."""
    path = root / INVENTORY_REL
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("required inventory must be a JSON object")
    return payload


def inventory_lists(payload: dict[str, object]) -> tuple[str, list[str], list[str]]:
    """Return (version, required_suites, required_cases) from inventory payload."""
    version = str(payload.get("version", ""))
    suites_raw = payload.get("required_suites", [])
    cases_raw = payload.get("required_cases", [])
    if not isinstance(suites_raw, list) or not isinstance(cases_raw, list):
        raise ValueError("required inventory lists are malformed")
    suites = sorted(str(item) for item in suites_raw)
    cases = sorted(str(item) for item in cases_raw)
    return version, suites, cases


def missing_required_suites(
    per_suite: dict[str, int], required: tuple[str, ...] = REQUIRED_SUITES
) -> list[str]:
    """Return required suite module prefixes with zero collected tests."""
    missing: list[str] = []
    for suite in required:
        found = any(name == suite or name.startswith(suite + ".") for name in per_suite)
        if not found:
            missing.append(suite)
    return missing


def missing_required_cases(
    actual_ids: set[str], required: list[str] | tuple[str, ...]
) -> list[str]:
    """Return required individual case IDs absent from the actual JUnit run."""
    return [case for case in sorted(required) if case not in actual_ids]


@dataclass(frozen=True)
class InventoryDiff:
    removed_suites: list[str]
    removed_cases: list[str]
    added_suites: list[str]
    added_cases: list[str]


def diff_inventories(
    trusted_suites: list[str],
    trusted_cases: list[str],
    candidate_suites: list[str],
    candidate_cases: list[str],
) -> InventoryDiff:
    """Compare a trusted base inventory against the candidate inventory."""
    trusted_suite_set = set(trusted_suites)
    candidate_suite_set = set(candidate_suites)
    trusted_case_set = set(trusted_cases)
    candidate_case_set = set(candidate_cases)
    return InventoryDiff(
        removed_suites=sorted(trusted_suite_set - candidate_suite_set),
        removed_cases=sorted(trusted_case_set - candidate_case_set),
        added_suites=sorted(candidate_suite_set - trusted_suite_set),
        added_cases=sorted(candidate_case_set - trusted_case_set),
    )


def resolve_trust_ref(root: Path, ref: str) -> tuple[str | None, str | None]:
    """Resolve a trusted main ref to an exact commit SHA through local Git.

    Returns (sha, problem); exactly one is meaningful. Only allowlisted main
    refs are accepted and the commit object must exist locally, so a missing
    or stale fetch fails closed instead of silently trusting something else.
    A candidate-supplied SHA is never accepted here: there is deliberately no
    --trust-sha flag, only a ref name resolved through Git objects.
    """
    if ref not in TRUST_REFS_ALLOWLIST:
        return (
            None,
            f"unsupported trust ref {ref!r}; allowed: {', '.join(TRUST_REFS_ALLOWLIST)}",
        )
    rev = subprocess.run(
        ["git", "rev-parse", "--verify", ref],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if rev.returncode != 0:
        return (None, f"trusted ref {ref!r} does not resolve locally; fetch main first")
    sha = rev.stdout.strip()
    if len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha):
        return (None, f"trusted ref {ref!r} resolved to invalid SHA {sha!r}")
    exists = subprocess.run(
        ["git", "cat-file", "-e", f"{sha}^{{commit}}"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if exists.returncode != 0:
        return (None, f"trusted commit {sha[:12]} from {ref!r} is not present locally")
    return (sha, None)


def load_trusted_base_inventory(
    root: Path, base_sha: str
) -> tuple[str, dict[str, object] | None, str]:
    """Load the required-test inventory from the verified trusted base SHA.

    Returns (status, payload, detail) with status one of:
    - "no-inventory": base SHA is valid but carries no inventory file.
    - "present": base inventory loaded; candidate must not narrow it.
    - "invalid-base": SHA does not resolve; fail closed.
    - "error": git or parse failure; fail closed, do not pretend to verify.
    """
    probe = subprocess.run(
        ["git", "cat-file", "-e", f"{base_sha}^{{commit}}"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if probe.returncode != 0:
        return ("invalid-base", None, f"base SHA {base_sha[:12]!r} does not resolve")
    show = subprocess.run(
        ["git", "show", f"{base_sha}:{INVENTORY_REL}"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if show.returncode != 0:
        return ("no-inventory", None, "trusted base carries no required inventory")
    try:
        payload = json.loads(show.stdout)
    except json.JSONDecodeError as exc:
        return ("error", None, f"trusted base inventory unparsable: {exc}")
    if not isinstance(payload, dict):
        return ("error", None, "trusted base inventory is not a JSON object")
    return ("present", payload, "trusted base inventory loaded")


ENFORCEMENT_PATHS: tuple[str, ...] = (
    "scripts/check.py",
    "tests/test_ci_gate.py",
    "tests/test_ci_gate_integration.py",
)


def _enforcement_changed_vs_base(root: Path, base_rev: str) -> list[str]:
    """List inventory-enforcement files differing between base and candidate.

    Compares working-tree bytes against the base revision (tracked content).
    Untracked candidate files count as changed. Never fails the gate by
    itself; it only annotates a coincident coverage reduction.
    """
    changed: list[str] = []
    for rel in ENFORCEMENT_PATHS:
        candidate = root / rel
        show = subprocess.run(
            ["git", "show", f"{base_rev}:{rel}"],
            cwd=root,
            capture_output=True,
            text=True,
        )
        if show.returncode != 0:
            if candidate.is_file():
                changed.append(f"{rel} (new since base)")
            continue
        if not candidate.is_file():
            changed.append(f"{rel} (deleted since base)")
            continue
        base_bytes = show.stdout.encode("utf-8", errors="surrogateescape")
        if _sha256_bytes(base_bytes) != _sha256_file(candidate):
            changed.append(rel)
    return changed


def check_trusted_inventory(
    root: Path,
    base_sha: str,
    initial_sha: str = INITIAL_MAIN_SHA,
    proposed_suites: tuple[str, ...] | list[str] = PROPOSED_INITIAL_SUITES,
    proposed_cases: frozenset[str] | set[str] = PROPOSED_INITIAL_CASES,
) -> tuple[str, list[str], str]:
    """Enforce the independent trust boundary for the required inventory.

    `base_sha` must be a commit SHA resolved through Git (see
    resolve_trust_ref), never a candidate-supplied string. Returns (status,
    problems, detail). A candidate can never approve its own reduced
    inventory: reductions versus a present trusted base always fail, and no
    candidate-controlled digest, flag or JSON field can override that.
    Reductions become acceptable only after the reviewed inventory is merged
    into main, at which point the trusted base itself carries the new list.

    The strict first-inventory bootstrap is allowed ONLY when the verified
    base SHA is exactly the initial main commit, the candidate manifest
    exactly equals the complete proposed set (no missing and no extra
    suites/cases), and the evidence is labeled
    BOOTSTRAP_PENDING_INDEPENDENT_REVIEW. It confers no approval.
    """
    try:
        candidate_payload = load_required_inventory(root)
        _, cand_suites, cand_cases = inventory_lists(candidate_payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return ("error", [f"candidate inventory unreadable: {exc}"], "candidate invalid")
    status, trusted_payload, detail = load_trusted_base_inventory(root, base_sha)
    if status == "no-inventory":
        if base_sha != initial_sha:
            return (
                "missing-trusted-inventory",
                [
                    "trusted main has no required inventory and is not the initial "
                    "commit; failing closed instead of falling back to a bootstrap. "
                    "Independent review required."
                ],
                detail,
            )
        missing_suites = sorted(set(proposed_suites) - set(cand_suites))
        extra_suites = sorted(set(cand_suites) - set(proposed_suites))
        missing_cases = sorted(set(proposed_cases) - set(cand_cases))
        extra_cases = sorted(set(cand_cases) - set(proposed_cases))
        if (
            not cand_suites
            or not cand_cases
            or missing_suites
            or extra_suites
            or missing_cases
            or extra_cases
        ):
            problems = [
                "bootstrap proposal differs from the proposed initial set "
                "(exact equality required)"
            ]
            if missing_suites:
                problems.append("missing proposed suite(s): " + ", ".join(missing_suites))
            if extra_suites:
                problems.append(
                    "extra suite(s) vs proposed initial set: " + ", ".join(extra_suites)
                )
            if missing_cases:
                shown = ", ".join(missing_cases[:5])
                suffix = f" (+{len(missing_cases) - 5} more)" if len(missing_cases) > 5 else ""
                problems.append(f"missing proposed case(s): {shown}{suffix}")
            if extra_cases:
                shown = ", ".join(extra_cases[:5])
                suffix = f" (+{len(extra_cases) - 5} more)" if len(extra_cases) > 5 else ""
                problems.append(f"extra case(s) vs proposed initial set: {shown}{suffix}")
            return ("bootstrap-incomplete", problems, detail)
        return (
            "BOOTSTRAP_PENDING_INDEPENDENT_REVIEW",
            [],
            "candidate proposes the FIRST inventory; independent review and merge "
            "into main required before it becomes trusted. CI claims no approval.",
        )
    if status == "invalid-base":
        return (
            status,
            [f"trusted base invalid ({detail}); failing closed, independent review required"],
            detail,
        )
    if status != "present" or trusted_payload is None:
        return (
            status,
            [f"trusted inventory check INCONCLUSIVE ({detail}); independent review required"],
            detail,
        )
    try:
        _, trusted_suites, trusted_cases = inventory_lists(trusted_payload)
    except ValueError as exc:
        return ("error", [f"trusted base inventory malformed: {exc}"], detail)
    diff = diff_inventories(trusted_suites, trusted_cases, cand_suites, cand_cases)
    reduction_problems: list[str] = []
    if diff.removed_suites:
        reduction_problems.append(
            "unapproved inventory reduction vs trusted base: removed suite(s) "
            + ", ".join(diff.removed_suites)
        )
    if diff.removed_cases:
        shown = ", ".join(diff.removed_cases[:5])
        extra = f" (+{len(diff.removed_cases) - 5} more)" if len(diff.removed_cases) > 5 else ""
        reduction_problems.append(
            f"unapproved inventory reduction vs trusted base: removed case(s) {shown}{extra}"
        )
    if reduction_problems:
        changed = _enforcement_changed_vs_base(root, base_sha)
        if changed:
            reduction_problems.append(
                "inventory enforcement mechanism also changed vs base: " + ", ".join(changed)
            )
        reduction_problems.append(
            "candidate cannot self-approve a reduced inventory; requires independent "
            "review and merge of the new inventory into main first"
        )
    detail = (
        f"trusted base inventory compared ({len(trusted_cases)} cases); "
        f"candidate lists {len(cand_cases)} cases"
    )
    return (
        "trusted-clean" if not reduction_problems else "trusted-reduction",
        reduction_problems,
        detail,
    )


def is_evidence_stale(evidence_mtime: float, source_mtimes: list[float]) -> bool:
    """Supplementary mtime helper only; content digests own gate integrity."""
    if not source_mtimes:
        return False
    return evidence_mtime < max(source_mtimes)


def docs_only_violations(changed_paths: list[str]) -> list[str]:
    """Return changed paths that prove a docs-only claim is false."""
    bad: list[str] = []
    for raw in changed_paths:
        normalized = raw.replace("\\", "/").strip()
        for prefix in CODE_OWNING_PREFIXES:
            if normalized == prefix.rstrip("/") or normalized.startswith(prefix):
                bad.append(normalized)
                break
    return bad


def _git(cwd: Path, args: list[str]) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return "unknown"
    return proc.stdout.strip()


def _changed_paths(base: str | None, root: Path) -> list[str]:
    lines: list[str] = []
    if base:
        out = _git(root, ["diff", "--name-only", f"{base}...HEAD"])
        if out not in ("", "unknown"):
            lines.extend(line.strip() for line in out.splitlines() if line.strip())
    else:
        tracked = _git(root, ["diff", "--name-only", "HEAD"])
        if tracked not in ("", "unknown"):
            lines.extend(line.strip() for line in tracked.splitlines() if line.strip())
    untracked = _git(root, ["ls-files", "--others", "--exclude-standard"])
    if untracked not in ("", "unknown"):
        for line in untracked.splitlines():
            candidate = line.strip()
            if candidate and candidate not in lines:
                lines.append(candidate)
    status = _git(root, ["status", "--porcelain"])
    if status not in ("", "unknown"):
        for line in status.splitlines():
            parts = line.strip().split(maxsplit=1)
            if len(parts) == 2:
                candidate = parts[1].replace('"', "").strip()
                if " -> " in candidate:
                    candidate = candidate.split(" -> ")[-1].strip()
                if candidate and candidate not in lines:
                    lines.append(candidate)
    return lines


def _resolve(p: Path, root: Path) -> Path:
    return p if p.is_absolute() else root / p


def verify_candidate_and_junit(
    root: Path, evidence_path: Path, min_tests: int, trust_ref: str = DEFAULT_TRUST_REF
) -> tuple[bool, list[str]]:
    """Deterministically verify evidence against live candidate bytes and JUnit.

    Recomputes the candidate digest, file inventory, required-inventory binding
    and JUnit case identities/outcomes/counts from disk, and revalidates the
    dynamically resolved trusted main base. Never trusts recorded JSON counts,
    SHAs or status flags as proof of execution.
    """
    problems: list[str] = []
    if not evidence_path.is_file():
        return False, [f"missing evidence artifact: {evidence_path}"]
    try:
        payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, [f"unreadable evidence artifact: {exc}"]
    if not isinstance(payload, dict):
        return False, ["evidence artifact must be a JSON object"]

    # Required inventory binding (manifest changes invalidate evidence).
    try:
        inventory_payload = load_required_inventory(root)
        inv_version, inv_suites, inv_cases = inventory_lists(inventory_payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return False, [f"required inventory unreadable: {exc}"]
    inventory_file = root / INVENTORY_REL
    current_inventory_digest = (
        _sha256_file(inventory_file) if inventory_file.is_file() else "missing"
    )
    if not inv_version:
        problems.append("required inventory has no version")
    recorded_inv_version = str(payload.get("inventory_version", ""))
    recorded_inv_digest = str(payload.get("inventory_digest", ""))
    if recorded_inv_version != inv_version:
        problems.append(
            f"inventory mismatch: evidence {recorded_inv_version!r} != "
            f"current {inv_version!r} (manifest change requires re-review)"
        )
    if recorded_inv_digest != current_inventory_digest:
        problems.append("inventory digest mismatch: manifest changed since evidence")

    # Independent trust boundary: resolve the trusted main base dynamically
    # through Git and revalidate it. A regenerated evidence file can never
    # authorize its own reduced manifest, and a recorded SHA is compared,
    # never trusted.
    trust_sha, trust_err = resolve_trust_ref(root, trust_ref)
    if trust_err is not None or trust_sha is None:
        problems.append(f"trusted base unresolvable ({trust_ref!r}): {trust_err}; failing closed")
        trust_status, trust_detail = "unresolved-trust-ref", trust_err or "unknown"
    else:
        recorded_sha = str(payload.get("trusted_base_sha", payload.get("base", "")))
        if not recorded_sha:
            problems.append("evidence lacks trusted_base_sha")
        elif recorded_sha != trust_sha:
            problems.append(
                "trusted main moved since evidence: recorded "
                f"{recorded_sha[:12]} != current {trust_sha[:12]}; regenerate evidence"
            )
        trust_status, trust_problems, trust_detail = check_trusted_inventory(root, trust_sha)
        problems.extend(trust_problems)
    recorded_trust_status = str(payload.get("trusted_inventory_status", ""))
    if recorded_trust_status and recorded_trust_status != trust_status:
        problems.append(
            f"trusted-inventory status mismatch: evidence {recorded_trust_status!r} "
            f"!= live {trust_status!r}"
        )

    # Candidate content binding (mtime-independent).
    current_digest, current_files = compute_candidate_identity(root)
    recorded_digest = str(payload.get("candidate_digest", ""))
    if not recorded_digest:
        problems.append("evidence lacks candidate_digest")
    elif recorded_digest != current_digest:
        problems.append("candidate digest mismatch: sources changed since evidence")
    recorded_files = payload.get("file_inventory", {})
    if not isinstance(recorded_files, dict):
        problems.append("evidence file_inventory is malformed")
        recorded_files = {}
    for rel in sorted(set(current_files) | set(str(k) for k in recorded_files)):
        current_hash = current_files.get(rel)
        recorded_hash = recorded_files.get(rel)
        if current_hash is None:
            problems.append(f"required file deleted since evidence: {rel}")
        elif recorded_hash is None:
            problems.append(f"candidate file added since evidence: {rel}")
        elif str(recorded_hash) != current_hash:
            problems.append(f"candidate file modified since evidence: {rel}")

    # Checkout identity (informational; trust comes from the resolved base).
    recorded_head = str(payload.get("head", ""))
    current_head = _git(root, ["rev-parse", "HEAD"])
    if recorded_head not in ("unknown", "") and current_head not in ("unknown", ""):
        if recorded_head != current_head:
            problems.append(
                f"stale/mismatched revision: evidence head {recorded_head[:12]} "
                f"!= current {current_head[:12]}"
            )

    # JUnit artifact: recompute everything from the actual XML.
    junit_raw = str(payload.get("junit_path", str(DEFAULT_JUNIT)))
    junit_path = _resolve(Path(junit_raw), root)
    # An explicit --junit override lives beside the evidence; prefer the recorded
    # path but fall back to a sibling junit.xml when the recorded one is absent
    # (supports isolated tmp evidence copies whose recorded path is absolute).
    if not junit_path.is_file():
        problems.append(f"missing junit artifact: {junit_path}")
        actual_counts: JunitCounts = JunitCounts(total=0, failures=0, errors=0, skipped=0)
        actual_cases: list[JunitCase] = []
        actual_per_suite: dict[str, int] = {}
    else:
        try:
            actual_counts, actual_per_suite, actual_cases = parse_junit_cases(junit_path)
        except ET.ParseError as exc:
            return False, problems + [f"unreadable junit artifact: {exc}"]
        actual_digest = compute_junit_digest(actual_cases)
        recorded_junit_digest = str(payload.get("junit_digest", ""))
        if not recorded_junit_digest:
            problems.append("evidence lacks junit_digest")
        elif recorded_junit_digest != actual_digest:
            problems.append("junit digest mismatch: test results changed since evidence")
        recorded_counts = payload.get("counts", {})
        if isinstance(recorded_counts, dict):
            expected: list[tuple[str, int]] = [
                ("total", actual_counts["total"]),
                ("failures", actual_counts["failures"]),
                ("errors", actual_counts["errors"]),
                ("skipped", actual_counts["skipped"]),
            ]
            for key, actual_val in expected:
                try:
                    recorded_val = int(recorded_counts.get(key, -9999))
                except (ValueError, TypeError):
                    problems.append(f"evidence counts.{key} is malformed")
                    continue
                if recorded_val != actual_val:
                    problems.append(f"evidence counts.{key} {recorded_val} != actual {actual_val}")
        recorded_cases = payload.get("junit_cases", [])
        if isinstance(recorded_cases, list):
            recorded_ids = sorted(
                str(item.get("case_id", "")) for item in recorded_cases if isinstance(item, dict)
            )
            actual_ids_sorted = sorted(c.case_id for c in actual_cases)
            if recorded_ids != actual_ids_sorted:
                problems.append("junit case identity mismatch vs evidence")

    # Required coverage from the ACTUAL run (not recorded JSON).
    if "actual_counts" in locals():
        if actual_counts["total"] <= 0:
            problems.append("zero tests collected")
        if actual_counts["total"] < min_tests:
            problems.append(f"collected {actual_counts['total']} < minimum {min_tests}")
        if actual_counts["failures"] > 0 or actual_counts["errors"] > 0:
            problems.append("failing required test(s) in actual junit")
        if actual_counts["skipped"] > 0:
            problems.append(f"unexpected skipped test(s): {actual_counts['skipped']}")
        actual_ids = {c.case_id for c in actual_cases}
        suite_missing = missing_required_suites(actual_per_suite, tuple(inv_suites))
        if suite_missing:
            problems.append("missing required suite(s): " + ", ".join(suite_missing))
        case_missing = missing_required_cases(actual_ids, inv_cases)
        if case_missing:
            shown = ", ".join(case_missing[:5])
            extra = f" (+{len(case_missing) - 5} more)" if len(case_missing) > 5 else ""
            problems.append(f"missing required test case(s): {shown}{extra}")
        # Failing/skipped required cases fail even when present.
        by_id = {c.case_id: c.outcome for c in actual_cases}
        bad_required = [c for c in inv_cases if by_id.get(c, "missing") != "passed"]
        if bad_required and not case_missing:
            problems.append(f"required test case(s) not passing: {', '.join(bad_required[:5])}")

    if payload.get("aggregate_pass") is not True:
        problems.append("evidence aggregate_pass is not true")

    return (len(problems) == 0), problems


def build_parser() -> argparse.ArgumentParser:
    """Build the check CLI parser."""
    parser = argparse.ArgumentParser(description="V0-01A genuine local CI gate.")
    parser.add_argument("--root", type=str, default=str(REPO_ROOT))
    parser.add_argument("--min-tests", type=int, default=DEFAULT_MIN_TESTS)
    parser.add_argument("--evidence", type=str, default=str(DEFAULT_EVIDENCE))
    parser.add_argument("--junit", type=str, default=str(DEFAULT_JUNIT))
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--docs-only", action="store_true")
    parser.add_argument("--base", type=str, default="")
    parser.add_argument(
        "--trust-ref",
        type=str,
        default=DEFAULT_TRUST_REF,
        help="Allowlisted main ref resolved through Git as the trusted inventory base.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the full gate or verify-only against live bytes."""
    args = build_parser().parse_args(argv)
    root = Path(args.root)
    evidence_path = _resolve(Path(args.evidence), root)
    junit_path = _resolve(Path(args.junit), root)
    min_tests: int = int(args.min_tests)
    trust_ref: str = str(args.trust_ref)

    if args.verify_only:
        ok, problems = verify_candidate_and_junit(root, evidence_path, min_tests, trust_ref)
        if ok:
            print(f"VERIFY PASS: evidence bound to candidate at {evidence_path}")
            return 0
        print("VERIFY FAIL:")
        for item in problems:
            print(f"  - {item}")
        return 1

    failures: list[str] = []

    if args.docs_only:
        base = args.base.strip() or None
        changed = _changed_paths(base, root)
        bad = docs_only_violations(changed)
        if bad:
            print("DOCS-ONLY FAIL: behavioral change disguised as documentation:")
            for item in bad:
                print(f"  - {item}")
            return 1
        print("DOCS-ONLY PASS: no code/config/test changes detected.")

    for rel in REQUIRED_FILES:
        if not (root / rel).is_file():
            failures.append(f"missing required file: {rel}")

    try:
        inventory_payload = load_required_inventory(root)
        inv_version, inv_suites, inv_cases = inventory_lists(inventory_payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        failures.append(f"required inventory unreadable: {exc}")
        inv_version, inv_suites, inv_cases = "missing", [], []

    trust_sha, trust_err = resolve_trust_ref(root, trust_ref)
    if trust_err is not None or trust_sha is None:
        failures.append(f"trusted base unresolvable ({trust_ref!r}): {trust_err}")
        trust_status, trust_detail = "unresolved-trust-ref", trust_err or "unknown"
        trust_sha = "unresolved"
    else:
        trust_status, trust_problems, trust_detail = check_trusted_inventory(root, trust_sha)
        failures.extend(trust_problems)
    if trust_status == "BOOTSTRAP_PENDING_INDEPENDENT_REVIEW":
        print(f"BOOTSTRAP_PENDING_INDEPENDENT_REVIEW: {trust_detail}")
        print(
            "BOOTSTRAP_PENDING_INDEPENDENT_REVIEW: candidate proposes the FIRST required "
            "inventory; it becomes trusted only after independent review and merge into "
            "main. CI does not claim a protected baseline where none exists."
        )
    else:
        print(f"trusted-inventory: {trust_status}: {trust_detail} (base {trust_sha[:12]})")

    steps: list[StepResult] = []
    steps.append(_run([sys.executable, "-m", "ruff", "check", "app", "tests", "scripts"], root))
    steps.append(_run([sys.executable, "-m", "black", "--check", "app", "tests", "scripts"], root))
    steps.append(_run([sys.executable, "-m", "mypy", "app", "scripts"], root))
    for step in steps:
        mark = "PASS" if step.passed else "FAIL"
        print(f"{mark}: {step.name} (exit {step.exit_code})")
        if not step.passed:
            failures.append(f"static check failed: {step.name}")

    junit_path.parent.mkdir(parents=True, exist_ok=True)
    if junit_path.is_file():
        junit_path.unlink()
    pytest_cmd = [sys.executable, "-m", "pytest", "-v", f"--junitxml={junit_path}"]
    pytest_proc = subprocess.run(pytest_cmd, cwd=root)
    print(
        f"{'PASS' if pytest_proc.returncode == 0 else 'FAIL'}: "
        f"{' '.join(pytest_cmd)} (exit {pytest_proc.returncode})"
    )

    counts: JunitCounts = JunitCounts(total=0, failures=0, errors=1, skipped=0)
    per_suite: dict[str, int] = {}
    cases: list[JunitCase] = []
    if not junit_path.is_file():
        failures.append(f"missing junit artifact after pytest: {junit_path}")
    else:
        try:
            counts, per_suite, cases = parse_junit_cases(junit_path)
        except ET.ParseError as exc:
            failures.append(f"unreadable junit artifact: {exc}")
        else:
            print(
                f"collected={counts['total']} failures={counts['failures']} "
                f"errors={counts['errors']} skipped={counts['skipped']}"
            )
            suite_missing = missing_required_suites(per_suite, tuple(inv_suites))
            if suite_missing:
                failures.append("missing required suite(s): " + ", ".join(suite_missing))
            if counts["total"] <= 0:
                failures.append("zero tests collected")
            if counts["total"] < min_tests:
                failures.append(f"collected {counts['total']} < minimum {min_tests}")
            if counts["failures"] > 0 or counts["errors"] > 0:
                failures.append("failing required test(s)")
                if pytest_proc.returncode == 0:
                    failures.append("pytest exit 0 despite junit failures")
            if pytest_proc.returncode != 0 and not any(
                "failing required" in item for item in failures
            ):
                failures.append("pytest execution error/timeout")
            if counts["skipped"] > 0:
                failures.append(f"unexpected skipped test(s): {counts['skipped']}")
            actual_ids = {c.case_id for c in cases}
            case_missing = missing_required_cases(actual_ids, inv_cases)
            if case_missing:
                shown = ", ".join(case_missing[:5])
                extra = f" (+{len(case_missing) - 5} more)" if len(case_missing) > 5 else ""
                failures.append(f"missing required test case(s): {shown}{extra}")

    aggregate_pass = len(failures) == 0
    candidate_digest, file_inventory = compute_candidate_identity(root)
    junit_digest = compute_junit_digest(cases) if junit_path.is_file() else "missing"
    inventory_file = root / INVENTORY_REL
    evidence = {
        "package": "V0-01A",
        "mode": "DEVELOPMENT/DEMO (synthetic-only)",
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "branch": _git(root, ["rev-parse", "--abbrev-ref", "HEAD"]),
        "head": _git(root, ["rev-parse", "HEAD"]),
        "base": trust_sha,
        "trust_ref": trust_ref,
        "trusted_base_sha": trust_sha,
        "min_tests": min_tests,
        "inventory_version": inv_version,
        "inventory_digest": _sha256_file(inventory_file) if inventory_file.is_file() else "missing",
        "trusted_inventory_status": trust_status,
        "trusted_inventory_detail": trust_detail,
        "candidate_digest": candidate_digest,
        "file_inventory": file_inventory,
        "static_steps": [
            {"name": step.name, "exit_code": step.exit_code, "passed": step.passed}
            for step in steps
        ],
        "pytest_exit": pytest_proc.returncode,
        "counts": dict(counts),
        "per_suite": per_suite,
        "junit_cases": [{"case_id": c.case_id, "outcome": c.outcome} for c in cases],
        "junit_digest": junit_digest,
        "aggregate_pass": aggregate_pass,
        "problems": failures,
        "junit_path": (
            str(junit_path.relative_to(root))
            if junit_path.is_relative_to(root)
            else str(junit_path)
        ),
    }
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"evidence: {evidence_path} aggregate_pass={aggregate_pass}")
    print(f"candidate_digest: {candidate_digest}")
    if not aggregate_pass:
        print("CI FAIL:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("CI PASS: all required checks genuinely passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
