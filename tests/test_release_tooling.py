from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_tool(name: str):
    path = ROOT / "tools" / "hi" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"hi_{name}", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


build = _load_tool("build")
sys.modules["build"] = build
release = _load_tool("release")
sys.modules["release"] = release
frontend_update = _load_tool("update_frontend")
logs = _load_tool("logs")


@pytest.mark.parametrize("strict", ["yes", "true", "no", "false", "ask", "accept-new"])
def test_ssh_strict_host_key_spellings(monkeypatch, strict):
    output = f"hostname test-host\nport 2222\nuser root\nstricthostkeychecking {strict}\n"
    monkeypatch.setattr(release.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess([], 0, output))
    if strict in {"yes", "true"}:
        release.SSHRemote(expected_address="test-host")
    else:
        with pytest.raises(release.ReleaseError, match="strict host key"):
            release.SSHRemote(expected_address="test-host")


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _fixture_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    component = repo / "custom_components" / "ai_automation_suggester"
    component.mkdir(parents=True)
    (component / "manifest.json").write_text('{"domain":"ai_automation_suggester"}\n', encoding="utf-8")
    (component / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo / "LICENSE").write_text("fixture license\n", encoding="utf-8")
    _git(repo, "init", "--quiet")
    _git(repo, "config", "user.name", "fixture")
    _git(repo, "config", "user.email", "fixture@example.invalid")
    _git(repo, "add", ".")
    env = {"GIT_AUTHOR_NAME": "fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid", "GIT_COMMITTER_NAME": "fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid"}
    subprocess.run(["git", "commit", "--quiet", "-m", "fixture"], cwd=repo, check=True, env={**__import__("os").environ, **env})
    return repo


def _approval(artifact: Path, *, allow_rollback_restart: bool = False) -> release.Approval:
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    return release.Approval(
        build_sha256=digest,
        backup_slug="backup-2026-09-20",
        session_id="session-123456",
        confirm_session_id="session-123456",
        confirm_window="2026-09-20T22:00Z/2026-09-20T22:30Z",
        max_restarts=1,
        allow_rollback_restart=allow_rollback_restart,
        confirm_first_install=True,
    )


class FakeRemote:
    def __init__(self, *, exists: bool = False, check_ok: bool = True, restarts: list[bool] | None = None):
        self.exists = exists
        self.check_ok = check_ok
        self.restarts = list(restarts or [True])
        self.calls: list[str] = []

    def preflight(self, expected_version: str):
        self.calls.append(f"preflight:{expected_version}")
        return {"component_exists": self.exists, "component_symlink": False, "free_bytes": 10**9}

    def verify_backup(self, slug: str, expected_version: str):
        self.calls.append(f"backup:{slug}:{expected_version}")

    def acquire_lock(self, session_id: str):
        self.calls.append(f"lock:{session_id}")

    def release_lock(self):
        self.calls.append("unlock")

    def ensure_space(self, bytes_required: int):
        self.calls.append("space")

    def stage(self, artifact: Path, name: str, digest: str):
        self.calls.append("stage")
        return "/config/.hi-staging/artifact.tar.gz"

    def validate_candidate(self, staged: str, manifest: dict):
        self.calls.append("candidate")

    def install_candidate(self, staged: str):
        self.calls.append("install")
        self.exists = True

    def verify_installed(self, manifest: dict):
        self.calls.append("verify-installed")

    def quarantine_installed(self, session_id: str):
        self.calls.append(f"quarantine:{session_id}")
        self.exists = False

    def core_check(self):
        self.calls.append("core-check")
        return self.check_ok

    def restart(self):
        self.calls.append("restart")
        return self.restarts.pop(0) if self.restarts else False


@pytest.mark.parametrize("failure", [None, "check", "install", "preserve-lost", "restart-lost", "changed-old"])
def test_ui_update_preserves_prior_code_and_bounds_restart(tmp_path, failure):
    artifact = tmp_path / "ui.tar.gz"
    artifact.write_bytes(b"synthetic archive")
    previous = {"license_sha256": "license", "files": {frontend_update.FRONTEND: "old", "backend.py": "unchanged"}}
    candidate = {"commit": "new", "license_sha256": "license", "files": {frontend_update.FRONTEND: "new", "backend.py": "unchanged"},
                 "_archive_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()}

    class Remote(FakeRemote):
        preserved = False

        def preserve_previous(self, session):
            self.calls.append("preserve")
            self.preserved, self.exists = True, False
            if failure == "preserve-lost":
                raise release.RemoteOperationUnknown("preserve reply lost")

        def install_candidate(self, staged):
            super().install_candidate(staged)
            if failure == "install":
                raise release.RemoteOperationUnknown("install reply lost")

        def _verify_tree(self, destination, marker):
            assert marker is previous
            self.calls.append("verify-preserved")

        def verify_installed(self, marker):
            if failure == "changed-old":
                raise release.ReleaseError("prior files changed")
            super().verify_installed(marker)

        def inspect_swap(self, destination):
            return ({"preserved"} if self.preserved else set()) | ({"installed"} if self.exists else set())

        def restore_previous(self, destination, marker):
            self.calls.append("restore")
            self.preserved, self.exists = False, True

        def restart(self):
            self.calls.append("restart")
            if failure == "restart-lost":
                raise release.RemoteOperationUnknown("restart reply lost")
            return True

    remote = Remote(exists=True, check_ok=failure != "check")
    if failure:
        with pytest.raises(release.ReleaseError):
            frontend_update.update(remote, artifact, previous, candidate, _approval(artifact))
        assert remote.calls.count("restart") == (1 if failure == "restart-lost" else 0)
        assert ("restore" in remote.calls) == (failure in {"check", "install", "preserve-lost"})
    else:
        result = frontend_update.update(remote, artifact, previous, candidate, _approval(artifact))
        assert result["status"] == "updated-awaiting-browser-verification"
        assert remote.preserved and remote.exists
        assert remote.calls.count("restart") == 1
    assert remote.calls[-1] == "unlock"


def test_ui_update_refuses_backend_or_schema_changes():
    old = {"files": {frontend_update.FRONTEND: "old", "store.py": "schema1"}, "license_sha256": "same"}
    new = {"files": {frontend_update.FRONTEND: "new", "store.py": "schema2"}, "license_sha256": "same"}
    with pytest.raises(release.ReleaseError, match="only"):
        frontend_update.validate_ui_change(old, new)


def test_build_is_deterministic_and_validates_marker(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    first = build.create_artifact(repo, tmp_path / "dist-a")
    second = build.create_artifact(repo, tmp_path / "dist-b")
    first_bytes = Path(first["artifact"]).read_bytes()
    second_bytes = Path(second["artifact"]).read_bytes()
    assert first["archive_sha256"] == second["archive_sha256"]
    assert first_bytes == second_bytes
    marker = build.validate_archive(Path(first["artifact"]))["marker"]
    assert marker["commit"] == first["commit"]
    assert marker["format_version"] == 1
    assert marker["license_sha256"]
    assert "LICENSE" not in marker["files"]


def test_archive_content_hash_and_traversal_are_rejected(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    artifact = Path(build.create_artifact(repo, tmp_path / "dist")["artifact"])
    tampered = tmp_path / "tampered.tar.gz"
    import gzip
    import io
    import tarfile

    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as archive:
        info = tarfile.TarInfo("custom_components/ai_automation_suggester/../escape")
        info.size = 1
        archive.addfile(info, io.BytesIO(b"x"))
    tampered.write_bytes(gzip.compress(output.getvalue(), mtime=0))
    with pytest.raises(build.BuildError):
        build.validate_archive(tampered)
    assert artifact.exists()


def test_core_check_failure_quarantines_before_restart(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    artifact = Path(build.create_artifact(repo, tmp_path / "dist")["artifact"])
    remote = FakeRemote(check_ok=False)
    result = release.DeploymentEngine(remote).deploy(artifact, _approval(artifact))
    assert result.status == "preflight-validation-failed-absent"
    assert "restart" not in remote.calls
    assert "quarantine:session-123456" in remote.calls
    assert remote.calls[-1] == "unlock"


def test_existing_component_is_rejected_before_mutation(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    artifact = Path(build.create_artifact(repo, tmp_path / "dist")["artifact"])
    remote = FakeRemote(exists=True)
    with pytest.raises(release.ReleaseError, match="first-install"):
        release.DeploymentEngine(remote).deploy(artifact, _approval(artifact))
    assert remote.calls == ["preflight:2026.9.3"]


def test_restart_failure_can_use_one_explicit_rollback_restart(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    artifact = Path(build.create_artifact(repo, tmp_path / "dist")["artifact"])
    remote = FakeRemote(restarts=[False, True])
    result = release.DeploymentEngine(remote).deploy(
        artifact, _approval(artifact, allow_rollback_restart=True)
    )
    assert result.status == "rolled-back-after-restart-failure"
    assert remote.calls.count("restart") == 2
    assert remote.calls.count("quarantine:session-123456") == 1


def test_rollback_refuses_changed_or_missing_install_and_leaves_store_unmentioned(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    artifact = Path(build.create_artifact(repo, tmp_path / "dist")["artifact"])
    remote = FakeRemote(exists=True)
    result = release.DeploymentEngine(remote).rollback(artifact, _approval(artifact))
    assert result.status == "rollback-quarantined-awaiting-approved-restart"
    assert any(call.startswith("quarantine:") for call in remote.calls)
    assert all("storage" not in call for call in remote.calls)


def test_post_install_validation_exception_quarantines_only_after_reverification(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    artifact = Path(build.create_artifact(repo, tmp_path / "dist")["artifact"])

    class VerifyOnceRemote(FakeRemote):
        def __init__(self):
            super().__init__()
            self.verify_count = 0

        def verify_installed(self, manifest: dict):
            self.verify_count += 1
            self.calls.append("verify-installed")
            if self.verify_count == 1:
                raise release.ReleaseError("simulated post-install check failure")

    remote = VerifyOnceRemote()
    with pytest.raises(release.ReleaseError, match="simulated post-install"):
        release.DeploymentEngine(remote).deploy(artifact, _approval(artifact))
    assert remote.calls.count("quarantine:session-123456") == 1
    assert remote.calls[-1] == "unlock"


def test_backup_parser_requires_recent_completed_matching_home_assistant(monkeypatch: pytest.MonkeyPatch):
    remote = object.__new__(release.SSHRemote)
    now = datetime.now(timezone.utc)
    payload = {
        "slug": "backup-2026-09-20",
        "status": "completed",
        "homeassistant": "2026.9.3",
        "date": (now - timedelta(hours=1, minutes=2)).isoformat(),
    }
    calls: list[str] = []

    def run(script: str, **kwargs):
        calls.append(script)
        return subprocess.CompletedProcess(["ssh"], 0, json.dumps(payload), "")

    monkeypatch.setattr(remote, "_run", run)
    remote.verify_backup("backup-2026-09-20", "2026.9.3")
    assert "--raw-json" in calls[0]
    payload["date"] = (now - timedelta(days=2)).isoformat()
    with pytest.raises(release.ReleaseError, match="recent completed"):
        remote.verify_backup("backup-2026-09-20", "2026.9.3")


@pytest.mark.parametrize("phase", ["verify_backup", "acquire_lock", "ensure_space", "stage", "validate_candidate"])
def test_pre_swap_failure_never_installs_or_restarts(tmp_path, phase):
    artifact = Path(build.create_artifact(_fixture_repo(tmp_path), tmp_path / "dist")["artifact"])
    remote = FakeRemote()

    def fail(*args):
        raise release.ReleaseError("injected failure")

    setattr(remote, phase, fail)
    with pytest.raises(release.ReleaseError):
        release.DeploymentEngine(remote).deploy(artifact, _approval(artifact))
    assert "install" not in remote.calls
    assert "restart" not in remote.calls


def test_install_disconnect_reconciles_and_restores_absence(tmp_path):
    artifact = Path(build.create_artifact(_fixture_repo(tmp_path), tmp_path / "dist")["artifact"])

    class Disconnected(FakeRemote):
        def install_candidate(self, staged):
            super().install_candidate(staged)
            raise release.RemoteOperationUnknown("connection lost after move")

    remote = Disconnected()
    with pytest.raises(release.RemoteOperationUnknown):
        release.DeploymentEngine(remote).deploy(artifact, _approval(artifact))
    assert not remote.exists
    assert "restart" not in remote.calls


def test_unknown_restart_outcome_never_retries_or_moves_running_code(tmp_path):
    artifact = Path(build.create_artifact(_fixture_repo(tmp_path), tmp_path / "dist")["artifact"])

    class TimedOut(FakeRemote):
        def restart(self):
            self.calls.append("restart")
            raise release.RemoteOperationUnknown("timeout")

    remote = TimedOut()
    result = release.DeploymentEngine(remote).deploy(artifact, _approval(artifact, allow_rollback_restart=True))
    assert result.status == "restart-outcome-unknown-manual-recovery-required"
    assert remote.calls.count("restart") == 1
    assert remote.exists
    assert not any(call.startswith("quarantine") for call in remote.calls)


def test_failed_recovery_reports_both_restart_attempts(tmp_path):
    artifact = Path(build.create_artifact(_fixture_repo(tmp_path), tmp_path / "dist")["artifact"])
    remote = FakeRemote(restarts=[False, False])
    result = release.DeploymentEngine(remote).deploy(artifact, _approval(artifact, allow_rollback_restart=True))
    assert result.restarted == 2
    assert result.status == "rollback-quarantined-restart-failed"
    assert not remote.exists


def test_log_summary_never_returns_household_message_content():
    raw = "ERROR [custom_components.ai_automation_suggester.observation] ValueError token=private-token coordinates=12.34,56.78\nERROR [unrelated] private-password"
    result = logs.summarize(raw)
    assert result["component_lines"] == 1
    assert result["exception_types"] == ["ValueError"]
    assert "private" not in json.dumps(result)
    assert "12.34" not in json.dumps(result)


def test_restart_timeout_does_not_trigger_an_immediate_second_restart(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    artifact = Path(build.create_artifact(repo, tmp_path / "dist")["artifact"])

    class UnknownRestartRemote(FakeRemote):
        def restart(self):
            self.calls.append("restart")
            raise release.RemoteOperationUnknown("transport timeout")

    remote = UnknownRestartRemote()
    result = release.DeploymentEngine(remote).deploy(
        artifact, _approval(artifact, allow_rollback_restart=True)
    )
    assert result.status == "restart-outcome-unknown-manual-recovery-required"
    assert remote.calls.count("restart") == 1
    assert "quarantine:session-123456" not in remote.calls


def test_swap_failure_reconciles_and_quarantines_if_component_was_moved(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    artifact = Path(build.create_artifact(repo, tmp_path / "dist")["artifact"])

    class SwapFailureRemote(FakeRemote):
        def install_candidate(self, staged: str):
            self.calls.append("install")
            self.exists = True
            raise release.ReleaseError("simulated post-swap cleanup failure")

    remote = SwapFailureRemote()
    with pytest.raises(release.ReleaseError, match="post-swap"):
        release.DeploymentEngine(remote).deploy(artifact, _approval(artifact))
    assert "preflight:2026.9.3" in remote.calls[remote.calls.index("install") + 1 :]
    assert remote.calls.count("quarantine:session-123456") == 1
