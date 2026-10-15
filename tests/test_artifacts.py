"""V0-01A generated-artifact tests (FIX4: evidence excluded, placeholder kept)."""

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _git_check_ignore(path: Path) -> bool:
    proc = subprocess.run(
        ["git", "check-ignore", "-q", str(path)],
        cwd=REPO_ROOT,
    )
    return proc.returncode == 0


def test_generated_evidence_is_gitignored() -> None:
    assert _git_check_ignore(REPO_ROOT / "evidence" / "ci-evidence.json")
    assert _git_check_ignore(REPO_ROOT / "evidence" / "junit.xml")


def test_placeholder_is_trackable() -> None:
    placeholder = REPO_ROOT / "evidence" / ".gitkeep"
    assert placeholder.is_file()
    assert not _git_check_ignore(placeholder)


def test_workflow_uploads_evidence_as_artifacts() -> None:
    workflow = REPO_ROOT / ".github" / "workflows" / "ci.yml"
    assert workflow.is_file()
    text = workflow.read_text(encoding="utf-8")
    assert "actions/upload-artifact" in text
    assert "evidence/ci-evidence.json" in text
    assert "evidence/junit.xml" in text
    # Generated evidence must not be force-added/committed by the workflow.
    assert "git add evidence" not in text
    assert "git commit" not in text


def test_workflow_resolves_trusted_main_base() -> None:
    workflow = REPO_ROOT / ".github" / "workflows" / "ci.yml"
    text = workflow.read_text(encoding="utf-8")
    # fetch-depth alone is insufficient: main must be fetched explicitly via
    # exact forced refspec (no --prune which can delete/alter trusted refs).
    assert "git fetch" in text
    assert "+refs/heads/main:refs/remotes/origin/main" in text
    assert "git fetch --no-tags origin +refs/heads/main:refs/remotes/origin/main" in text
    fetch_lines = [line for line in text.splitlines() if "git fetch" in line]
    assert fetch_lines
    assert all("--prune" not in line for line in fetch_lines)
    # Both gate invocations resolve trust through Git objects, never through
    # a candidate-supplied SHA or approval flag.
    assert text.count("--trust-ref origin/main") >= 2
    assert "--trust-base-sha" not in text
    assert "--trust-sha" not in text
    assert "approval" not in text.lower()


def test_workflow_gates_only_supported_event_contexts() -> None:
    workflow = REPO_ROOT / ".github" / "workflows" / "ci.yml"
    text = workflow.read_text(encoding="utf-8")
    # Pull requests are gated only when targeting main; any other target has
    # no gate and therefore no green signal.
    assert "pull_request:" in text
    assert "branches:" in text and '["main"]' in text
    assert 'branches: ["phase/v0-01a-foundation-ci"]' in text
