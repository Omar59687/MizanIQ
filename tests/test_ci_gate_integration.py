"""V0-01A aggregate CI-gate integration tests (real gate, isolated fixtures).

Destructive negative controls use temporary copies/workspaces only; the real
repository is never modified. Fixtures are synthesized in tmp_path from the
live candidate digest and required inventory, so they never depend on the
gate's own in-progress JUnit artifact.
"""

from __future__ import annotations

import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import scripts.check as check

REPO_ROOT = Path(__file__).resolve().parents[1]


def _git_head() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True
    )
    return proc.stdout.strip() if proc.returncode == 0 else "unknown"


def _inventory() -> tuple[str, list[str], list[str]]:
    payload = check.load_required_inventory(REPO_ROOT)
    return check.inventory_lists(payload)


def _write_junit(junit_path: Path, cases: list[tuple[str, str, str]]) -> None:
    """Write a minimal JUnit file; each item is (classname, name, outcome)."""
    suites_el = ET.Element("testsuite")
    suites_el.set("tests", str(len(cases)))
    failures = sum(1 for _, _, o in cases if o == "failure")
    errors = sum(1 for _, _, o in cases if o == "error")
    skipped = sum(1 for _, _, o in cases if o == "skipped")
    suites_el.set("failures", str(failures))
    suites_el.set("errors", str(errors))
    suites_el.set("skipped", str(skipped))
    root = ET.Element("testsuites")
    root.append(suites_el)
    for classname, name, outcome in cases:
        case_el = ET.SubElement(suites_el, "testcase", classname=classname, name=name)
        if outcome in ("failure", "error", "skipped"):
            ET.SubElement(case_el, outcome, message="intentional negative control")
    tree = ET.ElementTree(root)
    tree.write(junit_path, encoding="utf-8", xml_declaration=True)


def _make_passing_pair(tmp_path: Path, root: Path = REPO_ROOT) -> tuple[Path, Path]:
    """Synthesize a passing tmp evidence+JUnit bound to the given candidate root."""
    payload = check.load_required_inventory(root)
    version, _, required_cases = check.inventory_lists(payload)
    tmp_evidence = tmp_path / "ci-evidence.json"
    tmp_junit = tmp_path / "junit.xml"
    junit_cases = [(c.split("::")[0], c.split("::")[1], "passed") for c in required_cases]
    _write_junit(tmp_junit, junit_cases)
    counts, per_suite, parsed = check.parse_junit_cases(tmp_junit)
    assert counts["total"] == len(required_cases)
    candidate_digest, file_inventory = check.compute_candidate_identity(root)
    inventory_path = root / check.INVENTORY_REL
    trust_ref = "main" if root != REPO_ROOT else "origin/main"
    trust_sha, trust_err = check.resolve_trust_ref(root, trust_ref)
    assert trust_err is None and trust_sha is not None
    trust_status, trust_problems, trust_detail = check.check_trusted_inventory(root, trust_sha)
    assert trust_problems == []
    head_proc = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True
    )
    head = head_proc.stdout.strip() if head_proc.returncode == 0 else "unknown"
    evidence = {
        "package": "V0-01A",
        "mode": "DEVELOPMENT/DEMO (synthetic-only)",
        "generated_at": "test-fixture",
        "branch": "test",
        "head": head,
        "base": trust_sha,
        "trust_ref": trust_ref,
        "trusted_base_sha": trust_sha,
        "min_tests": 12,
        "inventory_version": version,
        "inventory_digest": check._sha256_file(inventory_path),
        "trusted_inventory_status": trust_status,
        "trusted_inventory_detail": trust_detail,
        "candidate_digest": candidate_digest,
        "file_inventory": file_inventory,
        "static_steps": [],
        "pytest_exit": 0,
        "counts": dict(counts),
        "per_suite": per_suite,
        "junit_cases": [{"case_id": c.case_id, "outcome": c.outcome} for c in parsed],
        "junit_digest": check.compute_junit_digest(parsed),
        "aggregate_pass": True,
        "problems": [],
        "junit_path": str(tmp_junit),
    }
    tmp_evidence.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    return tmp_evidence, tmp_junit


def _remove_cases(tmp_junit: Path, victim: str | None, suite: str | None = None) -> int:
    tree = ET.parse(tmp_junit)
    root = tree.getroot()
    removed = 0
    for suite_el in list(root.iter("testsuite")):
        for case in list(suite_el.findall("testcase")):
            classname = str(case.attrib.get("classname", ""))
            name = str(case.attrib.get("name", ""))
            if victim is not None and f"{classname}::{name}" == victim:
                suite_el.remove(case)
                removed += 1
            elif victim is None and suite is not None and classname == suite:
                suite_el.remove(case)
                removed += 1
    tree.write(tmp_junit, encoding="utf-8", xml_declaration=True)
    return removed


def _set_case_outcome(tmp_junit: Path, victim: str, outcome: str) -> None:
    classname, name = victim.split("::", 1)
    tree = ET.parse(tmp_junit)
    root = tree.getroot()
    found = False
    for case in root.iter("testcase"):
        if (
            str(case.attrib.get("classname", "")) == classname
            and str(case.attrib.get("name", "")) == name
        ):
            for tag in ("failure", "error", "skipped"):
                old = case.find(tag)
                if old is not None:
                    case.remove(old)
            ET.SubElement(case, outcome, message="intentional negative control")
            found = True
            break
    assert found, f"case not found: {victim}"
    tree.write(tmp_junit, encoding="utf-8", xml_declaration=True)


def test_aggregate_verify_pass_on_isolated_copies(tmp_path: Path) -> None:
    tmp_evidence, _ = _make_passing_pair(tmp_path)
    ok, problems = check.verify_candidate_and_junit(REPO_ROOT, tmp_evidence, 12)
    assert ok, f"expected PASS, got: {problems}"
    assert problems == []


def test_aggregate_cli_verify_pass_on_isolated_copies(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tmp_evidence, _ = _make_passing_pair(tmp_path)
    rc = check.main(["--verify-only", "--evidence", str(tmp_evidence)])
    assert rc == 0
    assert "VERIFY PASS" in capsys.readouterr().out


def test_missing_required_suite_fails(tmp_path: Path) -> None:
    tmp_evidence, tmp_junit = _make_passing_pair(tmp_path)
    removed = _remove_cases(tmp_junit, None, suite="tests.test_health")
    assert removed >= 1
    ok, problems = check.verify_candidate_and_junit(REPO_ROOT, tmp_evidence, 12)
    assert not ok
    assert any("missing required suite" in p for p in problems)


def test_missing_required_individual_case_fails(tmp_path: Path) -> None:
    _, _, required_cases = _inventory()
    assert len(required_cases) > 12, "inventory must exceed the count floor"
    victim = required_cases[0]
    tmp_evidence, tmp_junit = _make_passing_pair(tmp_path)
    assert _remove_cases(tmp_junit, victim) == 1
    ok, problems = check.verify_candidate_and_junit(REPO_ROOT, tmp_evidence, 12)
    assert not ok
    assert any("missing required test case" in p for p in problems)


def test_zero_collected_tests_fails(tmp_path: Path) -> None:
    tmp_evidence, tmp_junit = _make_passing_pair(tmp_path)
    _write_junit(tmp_junit, [])
    ok, problems = check.verify_candidate_and_junit(REPO_ROOT, tmp_evidence, 12)
    assert not ok
    assert any("zero tests collected" in p for p in problems)


def test_failed_test_fails(tmp_path: Path) -> None:
    _, _, required_cases = _inventory()
    tmp_evidence, tmp_junit = _make_passing_pair(tmp_path)
    _set_case_outcome(tmp_junit, required_cases[1], "failure")
    ok, problems = check.verify_candidate_and_junit(REPO_ROOT, tmp_evidence, 12)
    assert not ok
    assert any("failing required test" in p for p in problems)


def test_unexpected_skip_fails(tmp_path: Path) -> None:
    _, _, required_cases = _inventory()
    tmp_evidence, tmp_junit = _make_passing_pair(tmp_path)
    _set_case_outcome(tmp_junit, required_cases[2], "skipped")
    ok, problems = check.verify_candidate_and_junit(REPO_ROOT, tmp_evidence, 12)
    assert not ok
    assert any("skipped" in p for p in problems)


def test_junit_tamper_without_evidence_update_fails(tmp_path: Path) -> None:
    tmp_evidence, tmp_junit = _make_passing_pair(tmp_path)
    tree = ET.parse(tmp_junit)
    root = tree.getroot()
    first = next(root.iter("testcase"))
    first.set("name", str(first.attrib.get("name", "")) + "_tampered")
    tree.write(tmp_junit, encoding="utf-8", xml_declaration=True)
    ok, problems = check.verify_candidate_and_junit(REPO_ROOT, tmp_evidence, 12)
    assert not ok
    assert any("junit digest mismatch" in p or "case identity" in p for p in problems)


def test_source_edit_preserving_mtime_detected_in_isolated_workspace(
    tmp_path: Path,
) -> None:
    import os

    workspace = tmp_path / "workspace"
    (workspace / "app").mkdir(parents=True)
    target = workspace / "app" / "config.py"
    target.write_text("MODE = 'development-demo'\n", encoding="utf-8")
    digest_before, _ = check.compute_candidate_identity(workspace)
    assert digest_before != check._sha256_bytes(b"")
    mtime = target.stat().st_mtime
    target.write_text("MODE = 'production'\n", encoding="utf-8")
    os.utime(target, (mtime, mtime))
    assert target.stat().st_mtime == mtime
    digest_after, _ = check.compute_candidate_identity(workspace)
    assert digest_before != digest_after


def test_evidence_reuse_from_different_candidate_fails(tmp_path: Path) -> None:
    root_a = tmp_path / "cand_a"
    root_b = tmp_path / "cand_b"
    (root_a / "app").mkdir(parents=True)
    (root_b / "app").mkdir(parents=True)
    (root_a / "app" / "config.py").write_text("MODE = 'development-demo'\n", encoding="utf-8")
    (root_b / "app" / "config.py").write_text("MODE = 'production'\n", encoding="utf-8")
    digest_a, inv_a = check.compute_candidate_identity(root_a)
    digest_b, _ = check.compute_candidate_identity(root_b)
    assert digest_a != digest_b
    assert inv_a != {}


def test_docs_only_detects_behavioral_change() -> None:
    # Pure-function check only: invoking the full CLI here would recurse
    # (a passing docs-only check continues into the full gate/pytest run).
    # CLI-level docs-only behavior is demonstrated in final validation.
    bad = check.docs_only_violations(["app/main.py"])
    assert bad == ["app/main.py"]
    assert check.docs_only_violations(["docs/ARCHITECTURE.md"]) == []


def _workflow_workspace(tmp_path: Path, workflows: dict[str, str]) -> Path:
    root = tmp_path / "wfroot"
    (root / "app").mkdir(parents=True, exist_ok=True)
    (root / "app" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    wf_dir = root / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    for name, content in workflows.items():
        (wf_dir / name).write_text(content, encoding="utf-8")
    return root


def test_workflow_files_all_included_in_candidate(tmp_path: Path) -> None:
    root = _workflow_workspace(tmp_path, {"ci.yml": "name: ci\n", "deploy.yml": "name: deploy\n"})
    collected = check.collect_candidate_files(root)
    assert ".github/workflows/ci.yml" in collected
    assert ".github/workflows/deploy.yml" in collected


def test_adding_workflow_invalidates_evidence(tmp_path: Path) -> None:
    before = _workflow_workspace(tmp_path / "a", {"ci.yml": "name: ci\n"})
    after = _workflow_workspace(tmp_path / "b", {"ci.yml": "name: ci\n", "extra.yml": "x\n"})
    digest_before, _ = check.compute_candidate_identity(before)
    digest_after, _ = check.compute_candidate_identity(after)
    assert digest_before != digest_after


def test_modifying_workflow_invalidates_evidence(tmp_path: Path) -> None:
    import os

    root = _workflow_workspace(tmp_path, {"ci.yml": "name: ci\n"})
    digest_before, _ = check.compute_candidate_identity(root)
    target = root / ".github" / "workflows" / "ci.yml"
    mtime = target.stat().st_mtime
    target.write_text("name: ci-changed\n", encoding="utf-8")
    os.utime(target, (mtime, mtime))
    assert target.stat().st_mtime == mtime
    digest_after, _ = check.compute_candidate_identity(root)
    assert digest_before != digest_after


def test_removing_workflow_invalidates_evidence(tmp_path: Path) -> None:
    root = _workflow_workspace(tmp_path, {"ci.yml": "name: ci\n", "extra.yml": "x\n"})
    digest_before, _ = check.compute_candidate_identity(root)
    (root / ".github" / "workflows" / "extra.yml").unlink()
    digest_after, _ = check.compute_candidate_identity(root)
    assert digest_before != digest_after


def test_unchanged_workflows_preserve_evidence(tmp_path: Path) -> None:
    first = _workflow_workspace(tmp_path / "first", {"ci.yml": "name: ci\n"})
    second = _workflow_workspace(tmp_path / "second", {"ci.yml": "name: ci\n"})
    digest_first, _ = check.compute_candidate_identity(first)
    digest_second, _ = check.compute_candidate_identity(second)
    assert digest_first == digest_second


def _init_git_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "V0-01A Test"],
        cwd=path,
        check=True,
        capture_output=True,
    )


def _git_commit(path: Path, message: str) -> str:
    subprocess.run(["git", "add", "-A"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", message], cwd=path, check=True, capture_output=True)
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=path, check=True, capture_output=True, text=True
    )
    return proc.stdout.strip()


def _write_inventory(path: Path, version: str, cases: list[str]) -> None:
    suites = sorted({c.split("::")[0] for c in cases})
    (path / "tests").mkdir(parents=True, exist_ok=True)
    (path / "tests" / "required_inventory.json").write_text(
        json.dumps(
            {"version": version, "required_suites": suites, "required_cases": sorted(cases)}
        ),
        encoding="utf-8",
    )


def test_trust_bootstrap_when_base_has_no_inventory(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    (repo / "app").mkdir(parents=True)
    (repo / "app" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    initial = _git_commit(repo, "initial main, no inventory yet")
    tiny = ["tests.demo::test_one", "tests.demo::test_two"]
    _write_inventory(repo, "V1", tiny)
    status, payload, _ = check.load_trusted_base_inventory(repo, initial)
    assert status == "no-inventory"
    assert payload is None
    live_status, problems, _ = check.check_trusted_inventory(
        repo,
        initial,
        initial_sha=initial,
        proposed_suites=["tests.demo"],
        proposed_cases=set(tiny),
    )
    assert live_status == "BOOTSTRAP_PENDING_INDEPENDENT_REVIEW"
    assert problems == []


def test_trust_bootstrap_exact_initial_pending_review(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    (repo / "app").mkdir(parents=True)
    (repo / "app" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    initial = _git_commit(repo, "initial main, no inventory yet")
    tiny = ["tests.demo::test_one", "tests.demo::test_two"]
    _write_inventory(repo, "V1", tiny)
    live_status, problems, _ = check.check_trusted_inventory(
        repo,
        initial,
        initial_sha=initial,
        proposed_suites=["tests.demo"],
        proposed_cases=set(tiny),
    )
    assert live_status == "BOOTSTRAP_PENDING_INDEPENDENT_REVIEW"
    assert problems == []
    # Production pinning is exact and honest: only e5af075 bootstraps.
    assert check.INITIAL_MAIN_SHA == "e5af075fb4e741936354c083ee1a7e9b1a5359df"
    # Historical scenario: the exact original initial commit carries no
    # inventory, so the full proposed set bootstraps as pending review.
    hist_status, hist_problems, _ = check.check_trusted_inventory(REPO_ROOT, check.INITIAL_MAIN_SHA)
    assert hist_status == "BOOTSTRAP_PENDING_INDEPENDENT_REVIEW"
    assert hist_problems == []
    # Current trusted origin/main has merged the inventory, so it is trusted-clean.
    prod_sha, prod_err = check.resolve_trust_ref(REPO_ROOT, "origin/main")
    assert prod_err is None and prod_sha is not None
    prod_status, prod_problems, _ = check.check_trusted_inventory(REPO_ROOT, prod_sha)
    assert prod_status == "trusted-clean"
    assert prod_problems == []


def test_trust_bootstrap_rejected_on_other_sha(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    (repo / "app").mkdir(parents=True)
    (repo / "app" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    initial = _git_commit(repo, "initial main, no inventory yet")
    (repo / "app" / "other.py").write_text("y = 2\n", encoding="utf-8")
    later = _git_commit(repo, "still no inventory")
    assert later != initial
    tiny = ["tests.demo::test_one"]
    _write_inventory(repo, "V1", tiny)
    status, problems, _ = check.check_trusted_inventory(
        repo,
        later,
        initial_sha=initial,
        proposed_suites=["tests.demo"],
        proposed_cases=set(tiny),
    )
    assert status == "missing-trusted-inventory"
    assert problems != []
    assert any("fail" in p and "closed" in p for p in problems)


def test_trust_bootstrap_rejects_incomplete_proposal(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    (repo / "app").mkdir(parents=True)
    (repo / "app" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    initial = _git_commit(repo, "initial main, no inventory yet")
    _write_inventory(repo, "V1", ["tests.demo::test_one"])
    status, problems, _ = check.check_trusted_inventory(
        repo,
        initial,
        initial_sha=initial,
        proposed_suites=["tests.demo"],
        proposed_cases={"tests.demo::test_one", "tests.demo::test_missing"},
    )
    assert status == "bootstrap-incomplete"
    assert any("test_missing" in p for p in problems)


def test_trust_present_clean_when_nothing_removed(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    cases = ["tests.demo::test_one", "tests.demo::test_two"]
    _write_inventory(repo, "V1", cases)
    base = _git_commit(repo, "with inventory")
    status, _, _ = check.check_trusted_inventory(repo, base)
    assert status == "trusted-clean"


def test_trust_reduction_fails(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    _write_inventory(repo, "V1", ["tests.demo::test_one", "tests.demo::test_two"])
    base = _git_commit(repo, "with inventory")
    _write_inventory(repo, "V1", ["tests.demo::test_one"])
    status, problems, _ = check.check_trusted_inventory(repo, base)
    assert status == "trusted-reduction"
    assert any("tests.demo::test_two" in p for p in problems)
    assert any("cannot self-approve" in p for p in problems)


def test_trust_regen_does_not_authorize_reduction(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    _write_inventory(repo, "V1", ["tests.demo::test_one", "tests.demo::test_two"])
    base = _git_commit(repo, "with inventory")
    _write_inventory(repo, "V1", ["tests.demo::test_one"])
    _, problems_before, _ = check.check_trusted_inventory(repo, base)
    assert problems_before != []
    # Simulate a self-approved manifest bump plus regenerated digests: the
    # comparison is against the git base, so it must still fail.
    _write_inventory(repo, "V9-SELF-APPROVED", ["tests.demo::test_one"])
    status, problems_after, _ = check.check_trusted_inventory(repo, base)
    assert status == "trusted-reduction"
    assert any("tests.demo::test_two" in p for p in problems_after)


def test_trust_rename_detected_as_removal(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    _write_inventory(repo, "V1", ["tests.demo::test_old"])
    base = _git_commit(repo, "with inventory")
    _write_inventory(repo, "V1", ["tests.demo::test_new"])
    diff = check.diff_inventories(
        ["tests.demo"], ["tests.demo::test_old"], ["tests.demo"], ["tests.demo::test_new"]
    )
    assert diff.removed_cases == ["tests.demo::test_old"]
    assert diff.added_cases == ["tests.demo::test_new"]
    status, problems, _ = check.check_trusted_inventory(repo, base)
    assert status == "trusted-reduction"
    assert any("test_old" in p for p in problems)


def test_trust_invalid_base_fails_closed(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    _write_inventory(repo, "V1", ["tests.demo::test_one"])
    _git_commit(repo, "with inventory")
    status, payload, _ = check.load_trusted_base_inventory(repo, "deadbeef" * 5)
    assert status == "invalid-base"
    assert payload is None
    live_status, problems, _ = check.check_trusted_inventory(repo, "deadbeef" * 5)
    assert live_status == "invalid-base"
    assert problems != []


def test_trust_extension_passes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    _write_inventory(repo, "V1", ["tests.demo::test_one"])
    base = _git_commit(repo, "with inventory")
    _write_inventory(repo, "V2", ["tests.demo::test_one", "tests.demo::test_two"])
    status, problems, _ = check.check_trusted_inventory(repo, base)
    assert status == "trusted-clean"
    assert problems == []


def test_trust_unresolvable_ref_fails_closed(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    sha, err = check.resolve_trust_ref(repo, "origin/main")
    assert sha is None
    assert err is not None
    sha, err = check.resolve_trust_ref(repo, "HEAD")
    assert sha is None
    assert err is not None and "unsupported" in err
    sha, err = check.resolve_trust_ref(REPO_ROOT, "phase/v0-01a-foundation-ci")
    assert sha is None
    assert err is not None and "unsupported" in err


def test_trust_forged_evidence_sha_rejected(tmp_path: Path) -> None:
    tmp_evidence, _ = _make_passing_pair(tmp_path)
    payload = json.loads(tmp_evidence.read_text(encoding="utf-8"))
    payload["trusted_base_sha"] = "0" * 40
    payload["base"] = "0" * 40
    tmp_evidence.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    ok, problems = check.verify_candidate_and_junit(REPO_ROOT, tmp_evidence, 12)
    assert not ok
    assert any("moved" in p for p in problems)


def test_trust_main_advance_invalidates_evidence(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    (repo / "app").mkdir(parents=True)
    (repo / "app" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    cases = ["tests.demo::test_one", "tests.demo::test_two"]
    _write_inventory(repo, "V1", cases)
    _git_commit(repo, "trusted inventory")
    tmp_evidence, _ = _make_passing_pair(tmp_path, root=repo)
    ok, _ = check.verify_candidate_and_junit(repo, tmp_evidence, 1, "main")
    assert ok
    # Advance main without touching any candidate file: only the trusted SHA
    # moves, so a moved-base failure proves H in isolation.
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "advance main"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    ok_after, problems = check.verify_candidate_and_junit(repo, tmp_evidence, 1, "main")
    assert not ok_after
    assert any("moved" in p for p in problems)


FORMERLY_UNPROTECTED_CASES: tuple[str, ...] = (
    "tests.test_artifacts::test_workflow_gates_only_supported_event_contexts",
    "tests.test_artifacts::test_workflow_resolves_trusted_main_base",
    "tests.test_ci_gate_integration::test_trust_bootstrap_exact_initial_pending_review",
    "tests.test_ci_gate_integration::test_trust_bootstrap_rejected_on_other_sha",
    "tests.test_ci_gate_integration::test_trust_bootstrap_rejects_incomplete_proposal",
    "tests.test_ci_gate_integration::test_trust_extension_passes",
    "tests.test_ci_gate_integration::test_trust_forged_evidence_sha_rejected",
    "tests.test_ci_gate_integration::test_trust_main_advance_invalidates_evidence",
    "tests.test_ci_gate_integration::test_trust_unresolvable_ref_fails_closed",
)


def test_bootstrap_proposed_matches_mandatory_inventory() -> None:
    """The checker proposal must exactly equal the 55-case mandatory manifest."""
    _, inv_suites, inv_cases = _inventory()
    assert len(inv_cases) == 55
    assert set(inv_cases) == set(check.PROPOSED_INITIAL_CASES)
    assert sorted(inv_cases) == sorted(check.PROPOSED_INITIAL_CASES)
    assert set(inv_suites) == set(check.PROPOSED_INITIAL_SUITES)
    assert sorted(inv_suites) == sorted(check.PROPOSED_INITIAL_SUITES)
    # Historical bootstrap still offers the exact set as pending review, not approval.
    hist_status, hist_problems, _ = check.check_trusted_inventory(REPO_ROOT, check.INITIAL_MAIN_SHA)
    assert hist_status == "BOOTSTRAP_PENDING_INDEPENDENT_REVIEW"
    assert hist_problems == []
    # Current trusted origin/main has merged the inventory, so it is trusted-clean.
    prod_sha, prod_err = check.resolve_trust_ref(REPO_ROOT, "origin/main")
    assert prod_err is None and prod_sha is not None
    prod_status, prod_problems, _ = check.check_trusted_inventory(REPO_ROOT, prod_sha)
    assert prod_status == "trusted-clean"
    assert prod_problems == []


@pytest.mark.parametrize("victim", FORMERLY_UNPROTECTED_CASES)
def test_bootstrap_rejects_each_formerly_unprotected_removal(tmp_path: Path, victim: str) -> None:
    """Removing any one of the nine formerly-unprotected IDs must fail bootstrap."""
    assert victim in check.PROPOSED_INITIAL_CASES
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    (repo / "app").mkdir(parents=True)
    (repo / "app" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    initial = _git_commit(repo, "initial main, no inventory yet")
    _, _, live_cases = _inventory()
    assert len(live_cases) == 55
    assert victim in live_cases
    reduced = [c for c in live_cases if c != victim]
    assert len(reduced) == 54
    _write_inventory(repo, "V0-01A-3", reduced)
    status, problems, _ = check.check_trusted_inventory(repo, initial, initial_sha=initial)
    assert status == "bootstrap-incomplete"
    assert any(victim in p for p in problems)


def test_bootstrap_rejects_extra_case_and_suite(tmp_path: Path) -> None:
    """Exact equality: unreviewed additions must also fail bootstrap."""
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    (repo / "app").mkdir(parents=True)
    (repo / "app" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    initial = _git_commit(repo, "initial main, no inventory yet")
    _, _, live_cases = _inventory()
    # Extra case in an existing suite.
    _write_inventory(repo, "V0-01A-3", [*live_cases, "tests.test_health::test_extra_case"])
    status, problems, _ = check.check_trusted_inventory(repo, initial, initial_sha=initial)
    assert status == "bootstrap-incomplete"
    assert any("extra case" in p for p in problems)
    # Extra suite plus extra case.
    _write_inventory(repo, "V0-01A-3", [*live_cases, "tests.test_extra::test_one"])
    status, problems, _ = check.check_trusted_inventory(repo, initial, initial_sha=initial)
    assert status == "bootstrap-incomplete"
    assert any("extra" in p for p in problems)


def _regenerate_bootstrap_evidence(
    repo: Path, initial: str, evidence_path: Path, junit_path: Path
) -> tuple[str, list[str]]:
    """Rebuild JUnit+evidence from current disk bytes (simulated regen).

    Trust is evaluated against the isolated ``initial`` commit that carries no
    inventory (``initial_sha=initial``), mirroring the production bootstrap
    where the verified base is the initial main commit. All attacker-controlled
    bytes (inventory, JUnit, digests) are recomputed so a subsequent failure
    proves the trust boundary, not a stale artifact.
    """
    payload = check.load_required_inventory(repo)
    version, _, required_cases = check.inventory_lists(payload)
    junit_cases = [(c.split("::")[0], c.split("::")[1], "passed") for c in required_cases]
    _write_junit(junit_path, junit_cases)
    counts, per_suite, parsed = check.parse_junit_cases(junit_path)
    candidate_digest, file_inventory = check.compute_candidate_identity(repo)
    inventory_path = repo / check.INVENTORY_REL
    trust_status, _, trust_detail = check.check_trusted_inventory(
        repo, initial, initial_sha=initial
    )
    head_proc = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True
    )
    head = head_proc.stdout.strip() if head_proc.returncode == 0 else "unknown"
    evidence = {
        "package": "V0-01A",
        "mode": "DEVELOPMENT/DEMO (synthetic-only)",
        "generated_at": "test-fixture-regen",
        "branch": "test",
        "head": head,
        "base": initial,
        "trust_ref": "main",
        "trusted_base_sha": initial,
        "min_tests": 12,
        "inventory_version": version,
        "inventory_digest": check._sha256_file(inventory_path),
        "trusted_inventory_status": trust_status,
        "trusted_inventory_detail": trust_detail,
        "candidate_digest": candidate_digest,
        "file_inventory": file_inventory,
        "static_steps": [],
        "pytest_exit": 0,
        "counts": dict(counts),
        "per_suite": per_suite,
        "junit_cases": [{"case_id": c.case_id, "outcome": c.outcome} for c in parsed],
        "junit_digest": check.compute_junit_digest(parsed),
        "aggregate_pass": True,
        "problems": [],
        "junit_path": str(junit_path),
    }
    evidence_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    return trust_status, required_cases


def test_bootstrap_regen_does_not_authorize_removal(tmp_path: Path) -> None:
    """Reduced manifest plus fully regenerated artifacts must still fail trust."""
    victim = "tests.test_ci_gate_integration::test_trust_extension_passes"
    assert victim in FORMERLY_UNPROTECTED_CASES
    repo = tmp_path / "repo"
    _init_git_repo(repo)
    (repo / "app").mkdir(parents=True)
    (repo / "app" / "mod.py").write_text("x = 1\n", encoding="utf-8")
    initial = _git_commit(repo, "initial main, no inventory yet")
    _, _, live_cases = _inventory()
    assert len(live_cases) == 55
    _write_inventory(repo, "V0-01A-3", live_cases)
    evidence_path = tmp_path / "ci-evidence.json"
    junit_path = tmp_path / "junit.xml"
    trust_status, _ = _regenerate_bootstrap_evidence(repo, initial, evidence_path, junit_path)
    assert trust_status == "BOOTSTRAP_PENDING_INDEPENDENT_REVIEW"
    # Remove one formerly-unprotected ID, bump the version (simulated
    # self-approval) and regenerate everything an attacker controls:
    # inventory bytes, candidate/inventory/JUnit digests and evidence.
    # The bootstrap trust boundary must still fail closed.
    reduced = [c for c in live_cases if c != victim]
    _write_inventory(repo, "V9-SELF-APPROVED", reduced)
    trust_status, _ = _regenerate_bootstrap_evidence(repo, initial, evidence_path, junit_path)
    assert trust_status == "bootstrap-incomplete"
    status, problems, _ = check.check_trusted_inventory(repo, initial, initial_sha=initial)
    assert status == "bootstrap-incomplete"
    assert any(victim in p for p in problems)
    # Regenerated artifacts are internally consistent: recomputed digests match
    # the evidence, so the failure is the trust boundary, not stale bytes.
    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert payload["trusted_inventory_status"] == "bootstrap-incomplete"
    assert payload["inventory_digest"] == check._sha256_file(repo / check.INVENTORY_REL)
    candidate_digest, _ = check.compute_candidate_identity(repo)
    assert payload["candidate_digest"] == candidate_digest
    _, _, parsed = check.parse_junit_cases(junit_path)
    assert payload["junit_digest"] == check.compute_junit_digest(parsed)
