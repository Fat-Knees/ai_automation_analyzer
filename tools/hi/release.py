#!/usr/bin/env python3
"""Testable first-install transaction engine used by the PowerShell wrappers.

The live adapter intentionally exposes only a handful of allowlisted SSH
operations.  It never reads or writes Home Assistant's core storage, and it
does not claim that ``ha core check`` proves integration readiness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Protocol
from urllib.parse import urlparse

from build import BuildError, validate_archive

COMPONENT = "ai_automation_suggester"
COMPONENT_REL = "custom_components/ai_automation_suggester"
COMPONENT_PATH = "/config/custom_components/ai_automation_suggester"
STAGING_ROOT = "/config/.hi-staging"
QUARANTINE_ROOT = "/config/.hi-quarantine"
LOCK_ROOT = "/config/.hi-deploy-lock"
DEFAULT_HOST = "homeassistant-ai"
DEFAULT_HA_VERSION = "2026.9.3"
DEFAULT_SSH_PORT = "2222"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{7,63}$")
SAFE_SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class ReleaseError(RuntimeError):
    """A release gate or remote operation failed safely."""


class RemoteOperationUnknown(ReleaseError):
    """The SSH transport timed out after an operation may have taken effect."""


class Remote(Protocol):
    """The narrow adapter surface used by :class:`DeploymentEngine`."""

    def preflight(self, expected_version: str) -> dict[str, Any]: ...

    def verify_backup(self, slug: str, expected_version: str) -> None: ...

    def acquire_lock(self, session_id: str) -> None: ...

    def release_lock(self) -> None: ...

    def ensure_space(self, bytes_required: int) -> None: ...

    def stage(self, artifact: Path, name: str, digest: str) -> str: ...

    def validate_candidate(self, staged: str, manifest: dict[str, Any]) -> None: ...

    def install_candidate(self, staged: str) -> None: ...

    def verify_installed(self, manifest: dict[str, Any]) -> None: ...

    def quarantine_installed(self, session_id: str) -> None: ...

    def core_check(self) -> bool: ...

    def restart(self) -> bool: ...


@dataclass(frozen=True)
class Approval:
    """All values that must be repeated for a particular deployment session."""

    build_sha256: str
    backup_slug: str
    session_id: str
    confirm_session_id: str
    confirm_host: str = DEFAULT_HOST
    confirm_path: str = COMPONENT_PATH
    confirm_window: str = ""
    max_restarts: int = 1
    allow_rollback_restart: bool = False
    confirm_first_install: bool = False

    def validate(self, artifact_sha256: str) -> None:
        if not SHA256.fullmatch(self.build_sha256) or self.build_sha256 != artifact_sha256:
            raise ReleaseError("approved build digest does not match the local artifact")
        if not SAFE_SLUG.fullmatch(self.backup_slug):
            raise ReleaseError("backup slug contains unsupported characters")
        if not SAFE_ID.fullmatch(self.session_id) or self.session_id != self.confirm_session_id:
            raise ReleaseError("session-specific confirmation does not match")
        if self.confirm_host != DEFAULT_HOST:
            raise ReleaseError("deployment host confirmation must be homeassistant-ai")
        if self.confirm_path != COMPONENT_PATH:
            raise ReleaseError("deployment path confirmation is not the integration path")
        if not self.confirm_window.strip():
            raise ReleaseError("a non-empty maintenance window confirmation is required")
        if self.max_restarts != 1:
            raise ReleaseError("first install permits exactly one normal restart")
        if not self.confirm_first_install:
            raise ReleaseError("explicit first-install confirmation is required")


@dataclass(frozen=True)
class DeploymentResult:
    status: str
    artifact_sha256: str
    restarted: int = 0
    rollback_attempted: bool = False
    detail: str = ""


def _archive_manifest(artifact: Path, digest: str) -> dict[str, Any]:
    checked = validate_archive(artifact, digest)
    return checked["marker"]


def _marker_digest(manifest: dict[str, Any]) -> str:
    persistent = {key: value for key, value in manifest.items() if not key.startswith("_")}
    payload = (json.dumps(persistent, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return hashlib.sha256(payload).hexdigest()


def _validate_remote_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("component") != COMPONENT or manifest.get("format_version") != 1:
        raise ReleaseError("artifact marker is not a supported component build")
    if not re.fullmatch(r"[0-9a-f]{40}", str(manifest.get("commit", ""))):
        raise ReleaseError("artifact marker does not contain a full commit")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ReleaseError("artifact marker has no file hashes")
    for relative, digest in files.items():
        if (
            not isinstance(relative, str)
            or not relative
            or relative.startswith("/")
            or ".." in PurePosixPath(relative).parts
            or "\\" in relative
            or ":" in relative
        ):
            raise ReleaseError("artifact marker contains an unsafe path")
        if not SHA256.fullmatch(str(digest)):
            raise ReleaseError("artifact marker contains an invalid file digest")


class DeploymentEngine:
    """Run the bounded first-install state machine against a fake or SSH remote."""

    def __init__(self, remote: Remote, *, expected_ha_version: str = DEFAULT_HA_VERSION):
        self.remote = remote
        self.expected_ha_version = expected_ha_version

    def deploy(self, artifact: Path, approval: Approval) -> DeploymentResult:
        artifact = artifact.resolve()
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest() if artifact.is_file() else ""
        approval.validate(digest)
        manifest = _archive_manifest(artifact, digest)
        _validate_remote_manifest(manifest)
        manifest = {**manifest, "_archive_sha256": digest, "_marker_sha256": _marker_digest(manifest)}
        preflight = self.remote.preflight(self.expected_ha_version)
        if preflight.get("component_exists"):
            raise ReleaseError("first-install gate refused: integration path already exists")
        if preflight.get("component_symlink"):
            raise ReleaseError("first-install gate refused: integration path is a symlink")
        self.remote.verify_backup(approval.backup_slug, self.expected_ha_version)
        self.remote.acquire_lock(approval.session_id)
        lock_held = True
        rollback_attempted = False
        installed = False
        restart_attempted = False
        try:
            self.remote.ensure_space(artifact.stat().st_size * 2 + 10 * 1024 * 1024)
            staged = self.remote.stage(artifact, artifact.name, digest)
            self.remote.validate_candidate(staged, manifest)
            try:
                self.remote.install_candidate(staged)
            except Exception as install_exc:
                try:
                    installed = bool(self.remote.preflight(self.expected_ha_version).get("component_exists"))
                except Exception as reconcile_exc:
                    raise ReleaseError("install outcome is unknown; inspect the component before retrying") from reconcile_exc
                if not installed:
                    raise install_exc
                raise
            installed = True
            self.remote.verify_installed(manifest)
            if not self.remote.core_check():
                # A check failure is before restart.  Quarantine the exact files
                # so the component path immediately returns to ABSENCE.
                self.remote.verify_installed(manifest)
                self.remote.quarantine_installed(approval.session_id)
                installed = False
                return DeploymentResult("preflight-validation-failed-absent", digest, detail="ha core check failed")
            try:
                restart_attempted = True
                restarted = self.remote.restart()
            except RemoteOperationUnknown:
                return DeploymentResult(
                    "restart-outcome-unknown-manual-recovery-required",
                    digest,
                    restarted=1,
                    detail="restart transport timed out; no automatic rollback was attempted",
                )
            except ReleaseError:
                restarted = False
            if not restarted:
                if approval.allow_rollback_restart:
                    rollback_attempted = True
                    self.remote.verify_installed(manifest)
                    self.remote.quarantine_installed(approval.session_id)
                    installed = False
                    try:
                        rollback_restarted = self.remote.restart()
                    except RemoteOperationUnknown:
                        return DeploymentResult(
                            "rollback-restart-outcome-unknown-manual-recovery-required",
                            digest,
                            restarted=2,
                            rollback_attempted=True,
                        )
                    if rollback_restarted:
                        return DeploymentResult(
                            "rolled-back-after-restart-failure",
                            digest,
                            restarted=2,
                            rollback_attempted=True,
                        )
                    return DeploymentResult("rollback-quarantined-restart-failed", digest,
                                            restarted=2, rollback_attempted=True)
                return DeploymentResult(
                    "installed-restart-failed-manual-recovery-required",
                    digest,
                    restarted=1,
                    rollback_attempted=rollback_attempted,
                )
            # This is deliberately not a ready result.  Readiness requires an
            # authenticated integration endpoint after the user's HA setup.
            return DeploymentResult("installed-awaiting-user-setup", digest, restarted=1)
        except Exception as exc:
            if installed and not restart_attempted:
                try:
                    self.remote.verify_installed(manifest)
                    self.remote.quarantine_installed(approval.session_id)
                except Exception as recovery_exc:
                    raise ReleaseError(
                        "post-install failure left the component in place because exact hash verification failed"
                    ) from recovery_exc
            raise exc
        finally:
            if lock_held:
                self.remote.release_lock()

    def rollback(self, artifact: Path, approval: Approval) -> DeploymentResult:
        """Quarantine a verified first-install component without touching its store."""

        artifact = artifact.resolve()
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest() if artifact.is_file() else ""
        approval.validate(digest)
        manifest = _archive_manifest(artifact, digest)
        _validate_remote_manifest(manifest)
        manifest = {**manifest, "_archive_sha256": digest, "_marker_sha256": _marker_digest(manifest)}
        preflight = self.remote.preflight(self.expected_ha_version)
        if not preflight.get("component_exists"):
            raise ReleaseError("rollback refused: installed component path is absent")
        if preflight.get("component_symlink"):
            raise ReleaseError("rollback refused: installed component path is a symlink")
        self.remote.verify_backup(approval.backup_slug, self.expected_ha_version)
        self.remote.acquire_lock(approval.session_id)
        try:
            self.remote.verify_installed(manifest)
            self.remote.quarantine_installed(approval.session_id)
            if approval.allow_rollback_restart:
                try:
                    restarted = self.remote.restart()
                except RemoteOperationUnknown:
                    return DeploymentResult(
                        "rollback-restart-outcome-unknown-manual-recovery-required",
                        digest,
                        restarted=1,
                        rollback_attempted=True,
                    )
                if not restarted:
                    return DeploymentResult(
                        "rollback-quarantined-restart-failed",
                        digest,
                        restarted=1,
                        rollback_attempted=True,
                    )
                return DeploymentResult(
                    "rollback-complete-awaiting-user-setup",
                    digest,
                    restarted=1,
                    rollback_attempted=True,
                )
            return DeploymentResult("rollback-quarantined-awaiting-approved-restart", digest)
        finally:
            self.remote.release_lock()


class SSHRemote:
    """Allowlisted operations for the configured SSH alias."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        *,
        expected_address: str | None = None,
        expected_port: str = DEFAULT_SSH_PORT,
        timeout: int = 30,
    ):
        if host != DEFAULT_HOST:
            raise ReleaseError("only the configured homeassistant-ai host is allowed")
        self.host = host
        self.expected_address = expected_address or self._address_from_local_config()
        if not self.expected_address:
            raise ReleaseError("expected Home Assistant address is required; pass --expected-address or configure home-intelligence.local.json")
        self.expected_port = expected_port
        self.timeout = timeout
        self._verify_alias()

    @staticmethod
    def _address_from_local_config() -> str | None:
        config = Path(__file__).resolve().parents[2] / "home-intelligence.local.json"
        try:
            raw = json.loads(config.read_text(encoding="utf-8"))
            url = str(raw.get("ha_url") or "")
            parsed = urlparse(url if "://" in url else f"//{url}")
            return parsed.hostname
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
            return None

    def _verify_alias(self) -> None:
        """Ensure the configured alias still points at the approved HA target."""

        try:
            result = subprocess.run(
                ["ssh", "-G", self.host],
                text=True,
                capture_output=True,
                timeout=self.timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ReleaseError(f"SSH alias verification failed: {type(exc).__name__}") from exc
        if result.returncode != 0:
            raise ReleaseError("SSH alias verification failed")
        options = {
            parts[0]: parts[1]
            for line in result.stdout.splitlines()
            if len(parts := line.split(None, 1)) == 2
        }
        if options.get("hostname") != self.expected_address or options.get("port") != self.expected_port or options.get("user") != "root":
            raise ReleaseError("SSH alias does not match the configured Home Assistant target")
        if options.get("stricthostkeychecking", "").lower() != "yes":
            raise ReleaseError("SSH alias must enforce strict host key checking")

    def _run(self, script: str, *, timeout: int | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
        try:
            result = subprocess.run(
                ["ssh", self.host, script],
                text=True,
                capture_output=True,
                timeout=timeout or self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RemoteOperationUnknown("SSH operation timed out after it may have taken effect") from exc
        except OSError as exc:
            raise ReleaseError(f"SSH operation failed: {type(exc).__name__}") from exc
        if result.returncode == 255:
            raise RemoteOperationUnknown("SSH connection lost; remote outcome is unknown")
        if check and result.returncode != 0:
            raise ReleaseError(f"remote operation failed with exit code {result.returncode}")
        return result

    def _scp(self, source: Path, destination: str, digest: str) -> None:
        try:
            result = subprocess.run(
                ["scp", str(source), f"{self.host}:{destination}"],
                text=True,
                capture_output=True,
                timeout=self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RemoteOperationUnknown("artifact transfer timed out after it may have taken effect") from exc
        except OSError as exc:
            raise ReleaseError(f"artifact transfer failed: {type(exc).__name__}") from exc
        if result.returncode != 0:
            raise ReleaseError("artifact transfer failed")

    def preflight(self, expected_version: str) -> dict[str, Any]:
        try:
            raw = json.loads(self._run("ha core info --raw-json", check=True).stdout)
            version = raw.get("data", raw).get("version")
        except (ValueError, AttributeError) as exc:
            raise ReleaseError("Invalid Home Assistant version response") from exc
        if expected_version != version:
            raise ReleaseError("Home Assistant version does not match the configured release target")
        existence = self._run(
            f"test -e {shlex.quote(COMPONENT_PATH)}", check=False
        ).returncode == 0
        symlink = self._run(f"test -L {shlex.quote(COMPONENT_PATH)}", check=False).returncode == 0
        if self._run("test -L /config/custom_components", check=False).returncode == 0:
            raise ReleaseError("component parent is a symlink")
        for path, label in ((STAGING_ROOT, "release staging root"), (QUARANTINE_ROOT, "quarantine root"), (LOCK_ROOT, "deployment lock")):
            if self._run(f"test -L {shlex.quote(path)}", check=False).returncode == 0:
                raise ReleaseError(f"{label} is a symlink")
        space = self._run("df -Pk /config", check=True).stdout
        available = 0
        for line in space.splitlines()[1:]:
            fields = line.split()
            if len(fields) >= 4 and fields[0].startswith("/"):
                available = int(fields[3]) * 1024
                break
        return {"component_exists": existence, "component_symlink": symlink, "free_bytes": available}

    def verify_backup(self, slug: str, expected_version: str = DEFAULT_HA_VERSION) -> None:
        qslug = shlex.quote(slug)
        # jq normalizes the CLI JSON; Python parses timestamps so fractional
        # seconds and timezone offsets are handled consistently on Windows.
        expression = (
            f"ha backups info {qslug} --raw-json | jq -c --arg slug {qslug} "
            "'(.data // .) | select((.slug == $slug) or (.slug_id == $slug) or (.backup_id == $slug))'"
        )
        result = self._run(expression, check=True)
        try:
            backup = json.loads(result.stdout)
            backup_slug = backup.get("slug") or backup.get("slug_id") or backup.get("backup_id")
            status = str(backup.get("status", "completed")).lower()
            homeassistant = backup.get("homeassistant", backup.get("home_assistant"))
            timestamp = backup.get("date") or backup.get("created") or backup.get("timestamp")
            if backup_slug != slug or status != "completed" or homeassistant != expected_version:
                raise ValueError("backup metadata does not match target")
            if isinstance(timestamp, (int, float)):
                created = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            elif isinstance(timestamp, str):
                created = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                created = created.astimezone(timezone.utc)
            else:
                raise ValueError("backup timestamp missing")
            age = (datetime.now(timezone.utc) - created).total_seconds()
            if age < 0 or age >= 86400:
                raise ValueError("backup is older than 24 hours")
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise ReleaseError("backup is not a recent completed Home Assistant backup") from exc

    def acquire_lock(self, session_id: str) -> None:
        qid = shlex.quote(session_id)
        self._run(
            f"set -eu; mkdir {shlex.quote(LOCK_ROOT)}; printf '%s\\n' {qid} > {shlex.quote(LOCK_ROOT + '/session')}",
            check=True,
        )
        self._lock_session = session_id

    def release_lock(self) -> None:
        session_id = getattr(self, "_lock_session", "")
        if not session_id:
            return
        qid = shlex.quote(session_id)
        self._run(
            f"if test -f {shlex.quote(LOCK_ROOT + '/session')} && test \"$(cat {shlex.quote(LOCK_ROOT + '/session')})\" = {qid}; "
            f"then rm -f {shlex.quote(LOCK_ROOT + '/session')}; rmdir {shlex.quote(LOCK_ROOT)}; fi",
            check=False,
        )
        self._lock_session = ""

    def ensure_space(self, bytes_required: int) -> None:
        result = self._run("df -Pk /config", check=True)
        available = 0
        for line in result.stdout.splitlines()[1:]:
            fields = line.split()
            if len(fields) >= 4 and fields[0].startswith("/"):
                available = int(fields[3]) * 1024
                break
        if available < bytes_required:
            raise ReleaseError("insufficient free space on /config")

    def stage(self, artifact: Path, name: str, digest: str) -> str:
        if not re.fullmatch(r"ai_automation_suggester-[0-9a-f]{40}\.tar\.gz", name):
            raise ReleaseError("artifact filename is not a build filename")
        remote = f"{STAGING_ROOT}/{name}"
        self._run(f"set -eu; mkdir -p {shlex.quote(STAGING_ROOT)}; test ! -e {shlex.quote(remote)}", check=True)
        self._scp(artifact, remote, digest)
        observed = self._run(f"sha256sum {shlex.quote(remote)}", check=True).stdout.split()[0]
        if observed != digest:
            raise ReleaseError("transferred artifact digest mismatch")
        return remote

    def validate_candidate(self, staged: str, manifest: dict[str, Any]) -> None:
        candidate = f"{STAGING_ROOT}/candidate-{manifest['commit']}-{manifest['_archive_sha256'][:16]}"
        self._run(f"set -eu; test ! -e {shlex.quote(candidate)}; mkdir {shlex.quote(candidate)}", check=True)
        listing = self._run(f"tar -tzf {shlex.quote(staged)}", check=True).stdout.splitlines()
        prefix = f"{COMPONENT_REL}/"
        expected = {prefix + path for path in manifest["files"]} | {prefix + "_build.json", prefix.rstrip("/"), "LICENSE"}
        actual = set()
        for name in listing:
            normalized = name.rstrip("/")
            if normalized != name and not name.endswith("/"):
                raise ReleaseError("remote archive listing contains an unsafe path")
            if name in actual or "\\" in name or ":" in name:
                raise ReleaseError("remote archive listing contains a duplicate or non-portable path")
            if name == "LICENSE":
                actual.add(name)
                continue
            if name.startswith("./") or ".." in PurePosixPath(name).parts or not name.startswith(prefix):
                raise ReleaseError("remote archive listing contains an unsafe path")
            actual.add(normalized if name.endswith("/") else name)
        if actual != expected:
            raise ReleaseError("remote archive listing does not exactly match the approved component files")
        self._run(
            f"set -eu; tar --no-same-owner --no-same-permissions -xzf {shlex.quote(staged)} -C {shlex.quote(candidate)}; "
            f"test ! -L {shlex.quote(candidate + '/' + COMPONENT_REL)}; "
            f"test -f {shlex.quote(candidate + '/' + COMPONENT_REL + '/_build.json')}; "
            f"test -f {shlex.quote(candidate + '/LICENSE')}; "
            f"test \"$(sha256sum {shlex.quote(candidate + '/LICENSE')} | awk '{{print $1}}')\" = {shlex.quote(str(manifest['license_sha256']))}",
            check=True,
        )
        source = candidate + "/" + COMPONENT_REL
        self._run(f"set -eu; test ! -e {shlex.quote(source + '/LICENSE')}; mv {shlex.quote(candidate + '/LICENSE')} {shlex.quote(source + '/LICENSE')}")
        self._verify_tree(source, manifest)
        self._candidate = candidate

    def install_candidate(self, staged: str) -> None:
        del staged
        candidate = getattr(self, "_candidate", "")
        if not candidate:
            raise ReleaseError("candidate was not validated")
        source = candidate + "/" + COMPONENT_REL
        self._run(
            f"set -eu; test ! -e {shlex.quote(COMPONENT_PATH)}; test ! -L {shlex.quote(COMPONENT_PATH)}; mv {shlex.quote(source)} {shlex.quote(COMPONENT_PATH)}",
            check=True,
        )

    def verify_installed(self, manifest: dict[str, Any]) -> None:
        self._verify_tree(COMPONENT_PATH, manifest)

    def _verify_tree(self, root: str, manifest: dict[str, Any]) -> None:
        # Check the complete tree before any quarantine.  This refuses to move
        # a component after a user has edited or added files.
        expected_commit = shlex.quote(str(manifest["commit"]))
        self._run(
            f"set -eu; test -d {shlex.quote(root)}; test ! -L {shlex.quote(root)}; "
            f"test \"$(jq -r '.commit' {shlex.quote(root + '/_build.json')})\" = {expected_commit}",
            check=True,
        )
        if self._run(f"find {shlex.quote(root)} -type l -print -quit", check=True).stdout.strip():
            raise ReleaseError("installed component contains a symlink")
        expected_files = {
            root + "/_build.json",
            root + "/LICENSE",
            *(root + "/" + relative for relative in manifest["files"]),
        }
        observed_files = {
            value
            for value in self._run(f"find {shlex.quote(root)} -type f -print0", check=True).stdout.split("\0")
            if value
        }
        extra_files = observed_files - expected_files
        source_files = set(manifest["files"])
        for value in extra_files:
            relative = value[len(root) + 1 :]
            parts = PurePosixPath(relative).parts
            if "__pycache__" not in parts or not relative.endswith(".pyc"):
                raise ReleaseError("installed component contains unexpected or missing files")
            cache_index = parts.index("__pycache__")
            if cache_index == len(parts) - 1 or len(parts) != cache_index + 2:
                raise ReleaseError("installed component contains an unsafe bytecode path")
            bytecode_name = parts[-1]
            source_relative = "/".join((*parts[:cache_index], bytecode_name.split(".", 1)[0] + ".py"))
            if source_relative not in source_files:
                raise ReleaseError("installed component contains bytecode for an unknown source file")
        if observed_files - extra_files != expected_files:
            raise ReleaseError("installed component contains unexpected or missing files")
        expected_dirs = {root}
        for value in expected_files:
            parent = PurePosixPath(value).parent
            while str(parent).startswith(root) and str(parent) != root:
                expected_dirs.add(str(parent))
                parent = parent.parent
        for value in extra_files:
            parent = PurePosixPath(value).parent
            expected_dirs.add(str(parent))
        observed_dirs = {
            value
            for value in self._run(f"find {shlex.quote(root)} -type d -print0", check=True).stdout.split("\0")
            if value
        }
        if observed_dirs != expected_dirs:
            raise ReleaseError("installed component contains unexpected directories")
        marker_result = self._run(f"sha256sum {shlex.quote(root + '/_build.json')}", check=True)
        if marker_result.stdout.split()[0] != manifest["_marker_sha256"]:
            raise ReleaseError("installed build marker changed after validation")
        license_result = self._run(f"sha256sum {shlex.quote(root + '/LICENSE')}", check=True)
        if license_result.stdout.split()[0] != manifest["license_sha256"]:
            raise ReleaseError("installed LICENSE changed after validation")
        for relative, digest in manifest["files"].items():
            path = root + "/" + relative
            result = self._run(f"sha256sum {shlex.quote(path)}", check=True)
            observed = result.stdout.split()[0]
            if observed != digest:
                raise ReleaseError("installed component changed after validation")

    def quarantine_installed(self, session_id: str) -> None:
        destination = f"{QUARANTINE_ROOT}/{COMPONENT}-{session_id}"
        self._run(
            f"set -eu; mkdir -p {shlex.quote(QUARANTINE_ROOT)}; test ! -e {shlex.quote(destination)}; "
            f"mv {shlex.quote(COMPONENT_PATH)} {shlex.quote(destination)}",
            check=True,
        )

    def core_check(self) -> bool:
        return self._run("ha core check", check=False).returncode == 0

    def restart(self) -> bool:
        result = self._run("ha core restart", timeout=90, check=False)
        if result.returncode != 0:
            raise RemoteOperationUnknown("restart command returned an indeterminate SSH result")
        # This is only an HA process check.  It is intentionally not the
        # integration's authenticated readiness endpoint.
        return self._run("ha core info", timeout=90, check=False).returncode == 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("deploy", "rollback"))
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--expected-address", default=None)
    parser.add_argument("--approve-build", required=True)
    parser.add_argument("--backup-slug", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--confirm-session-id", required=True)
    parser.add_argument("--confirm-host", default=DEFAULT_HOST)
    parser.add_argument("--confirm-path", default=COMPONENT_PATH)
    parser.add_argument("--confirm-window", required=True)
    parser.add_argument("--max-restarts", type=int, default=1)
    parser.add_argument("--confirm-first-install", action="store_true")
    parser.add_argument("--allow-rollback-restart", action="store_true")
    parser.add_argument("--expected-ha-version", default=DEFAULT_HA_VERSION)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    approval = Approval(
        build_sha256=args.approve_build,
        backup_slug=args.backup_slug,
        session_id=args.session_id,
        confirm_session_id=args.confirm_session_id,
        confirm_host=args.confirm_host,
        confirm_path=args.confirm_path,
        confirm_window=args.confirm_window,
        max_restarts=args.max_restarts,
        allow_rollback_restart=args.allow_rollback_restart,
        confirm_first_install=args.confirm_first_install,
    )
    try:
        engine = DeploymentEngine(
            SSHRemote(args.host, expected_address=args.expected_address), expected_ha_version=args.expected_ha_version
        )
        result = getattr(engine, args.operation)(args.artifact, approval)
    except (BuildError, ReleaseError, OSError) as exc:
        print(f"release failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result.__dict__, sort_keys=True))
    successful = {
        "installed-awaiting-user-setup",
        "rollback-quarantined-awaiting-approved-restart",
        "rollback-complete-awaiting-user-setup",
    }
    return 0 if result.status in successful else 1


if __name__ == "__main__":
    raise SystemExit(main())
