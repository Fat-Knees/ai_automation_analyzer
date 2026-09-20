"""Exact-build UI-only update with preserved prior code and no data migration."""
from __future__ import annotations

import argparse
import hashlib
import json
import shlex
from pathlib import Path

from build import validate_archive
from release import (
    COMPONENT_PATH,
    QUARANTINE_ROOT,
    Approval,
    ReleaseError,
    RemoteOperationUnknown,
    SSHRemote,
    _marker_digest,
)

FRONTEND = "www/ai_automation_suggester/home-intelligence-card.js"


def manifest(path, digest):
    marker = validate_archive(Path(path), digest)["marker"]
    return {**marker, "_archive_sha256": digest, "_marker_sha256": _marker_digest(marker)}


def validate_ui_change(previous, candidate):
    if previous["license_sha256"] != candidate["license_sha256"]:
        raise ReleaseError("UI update must preserve the license")
    old, new = previous["files"], candidate["files"]
    changed = {name for name in old.keys() | new.keys() if old.get(name) != new.get(name)}
    if changed != {FRONTEND}:
        raise ReleaseError("UI update must change only the Home Intelligence frontend")


class FrontendRemote(SSHRemote):
    def preserve_previous(self, session):
        destination = f"{QUARANTINE_ROOT}/ui-previous-{session}"
        self._run(f"set -eu; mkdir -p {shlex.quote(QUARANTINE_ROOT)}; "
                  f"test ! -e {shlex.quote(destination)}; test ! -L {shlex.quote(destination)}; "
                  f"mv {shlex.quote(COMPONENT_PATH)} {shlex.quote(destination)}")
        return destination

    def restore_previous(self, destination, previous):
        self._verify_tree(destination, previous)
        self._run(f"set -eu; test ! -e {shlex.quote(COMPONENT_PATH)}; test ! -L {shlex.quote(COMPONENT_PATH)}; "
                  f"mv {shlex.quote(destination)} {shlex.quote(COMPONENT_PATH)}")

    def inspect_swap(self, destination):
        """Reconcile path existence after a lost SSH reply; never repeat a move."""
        result = self._run(f"if test -d {shlex.quote(destination)} && test ! -L {shlex.quote(destination)}; then echo preserved; fi; "
                           f"if test -d {shlex.quote(COMPONENT_PATH)}; then echo installed; fi")
        return set(result.stdout.splitlines())


def update(remote, artifact, previous, candidate, approval):
    approval.validate(hashlib.sha256(Path(artifact).read_bytes()).hexdigest())
    validate_ui_change(previous, candidate)
    flight = remote.preflight("2026.9.3")
    if not flight["component_exists"] or flight["component_symlink"]:
        raise ReleaseError("UI update requires the verified existing installation")
    remote.verify_backup(approval.backup_slug, "2026.9.3")
    remote.acquire_lock(approval.session_id)
    destination = f"{QUARANTINE_ROOT}/ui-previous-{approval.session_id}"
    preserve_attempted = False
    restart_attempted = False
    try:
        remote.verify_installed(previous)
        remote.ensure_space(Path(artifact).stat().st_size * 3 + 10 * 1024 * 1024)
        staged = remote.stage(Path(artifact), Path(artifact).name, candidate["_archive_sha256"])
        remote.validate_candidate(staged, candidate)
        remote.verify_installed(previous)
        preserve_attempted = True
        remote.preserve_previous(approval.session_id)
        remote.install_candidate(staged)
        remote.verify_installed(candidate)
        if not remote.core_check():
            raise ReleaseError("Home Assistant configuration check failed")
        restart_attempted = True
        if not remote.restart():
            raise RemoteOperationUnknown("Restart readiness unknown; no repeat restart")
        return {"status": "updated-awaiting-browser-verification", "restarts": 1,
                "commit": candidate["commit"], "previous_preserved": destination}
    except Exception:
        # Never roll code back automatically once HA may have restarted.
        # A lost restart response needs inspection, not another restart.
        if preserve_attempted and not restart_attempted:
            state = remote.inspect_swap(destination)
            if "preserved" in state:
                remote._verify_tree(destination, previous)
                if "installed" in state:
                    remote.verify_installed(candidate)
                    remote.quarantine_installed(approval.session_id)
                remote.restore_previous(destination, previous)
        raise
    finally:
        remote.release_lock()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("previous_artifact", type=Path)
    parser.add_argument("--approve-build", required=True)
    parser.add_argument("--previous-sha256", required=True)
    parser.add_argument("--backup-slug", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--confirm-window", required=True)
    parser.add_argument("--expected-address", required=True)
    args = parser.parse_args()
    candidate = manifest(args.artifact, args.approve_build)
    previous = manifest(args.previous_artifact, args.previous_sha256)
    # Reuse strict host/path/session/hash validation; the update-specific gate
    # above requires an existing verified tree, not a first install.
    approval = Approval(build_sha256=args.approve_build, backup_slug=args.backup_slug,
                        session_id=args.session_id, confirm_session_id=args.session_id,
                        confirm_host="homeassistant-ai", confirm_path=COMPONENT_PATH,
                        confirm_window=args.confirm_window, max_restarts=1,
                        allow_rollback_restart=False, confirm_first_install=True)
    result = update(FrontendRemote(expected_address=args.expected_address), args.artifact, previous, candidate, approval)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
