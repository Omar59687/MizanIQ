"""V0-01A CI-gate unit tests (evidence-gate logic, no mocks of boundaries)."""

from pathlib import Path

from scripts.check import (
    DEFAULT_MIN_TESTS,
    REQUIRED_SUITES,
    docs_only_violations,
    is_evidence_stale,
    missing_required_cases,
    missing_required_suites,
)


def test_missing_suite_detection(tmp_path: Path) -> None:
    per_suite = {"tests.test_config": 5}
    missing = missing_required_suites(per_suite)
    assert "tests.test_health" in missing
    assert "tests.test_ci_gate" in missing
    assert set(REQUIRED_SUITES) >= {"tests.test_config", "tests.test_health", "tests.test_ci_gate"}


def test_no_missing_when_all_suites_present() -> None:
    per_suite = {suite: 5 for suite in REQUIRED_SUITES}
    assert missing_required_suites(per_suite) == []


def test_missing_case_detection() -> None:
    required = ["tests.test_config::test_a", "tests.test_config::test_b"]
    assert missing_required_cases({"tests.test_config::test_a"}, required) == [
        "tests.test_config::test_b"
    ]
    assert missing_required_cases(set(required), required) == []


def test_stale_mtime_helper_is_supplementary_only(tmp_path: Path) -> None:
    # Timestamps are informational only; content digests own integrity.
    assert is_evidence_stale(100.0, [101.0, 99.0]) is True
    assert is_evidence_stale(102.0, [101.0, 99.0]) is False


def test_docs_only_flags_behavioral_changes() -> None:
    bad = docs_only_violations(["app/main.py", "docs/ARCHITECTURE.md"])
    assert bad == ["app/main.py"]
    assert docs_only_violations(["docs/ARCHITECTURE.md"]) == []
    assert docs_only_violations(["tests/test_config.py"]) != []


def test_min_tests_threshold_is_positive() -> None:
    assert DEFAULT_MIN_TESTS >= 12
