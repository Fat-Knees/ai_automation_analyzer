#!/usr/bin/env python3
"""Create a deterministic, source-controlled first-install artifact.

The release artifact is intentionally limited to the custom integration.  It is
created from a git commit (never from the working tree) so a deployment can be
reproduced later without copying development files, local settings, or secrets.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

COMPONENT = "ai_automation_suggester"
COMPONENT_PATH = f"custom_components/{COMPONENT}"
FORMAT_VERSION = 1
_HEX40 = re.compile(r"^[0-9a-f]{40}$")


class BuildError(RuntimeError):
    """A source or artifact safety check failed."""


@dataclass(frozen=True)
class SourceFile:
    """A regular file read from the requested git commit."""

    path: str
    data: bytes
    mode: int


def _git(repo: Path, *args: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", b"")
        if isinstance(detail, bytes):
            detail = detail.decode("utf-8", "replace").strip()
        raise BuildError(f"git command failed: {detail or exc}") from exc
    return result.stdout


def resolve_commit(repo: Path, requested: str | None = None) -> str:
    """Resolve and validate an exact commit object."""

    ref = requested or "HEAD"
    commit = _git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}").decode().strip()
    if not _HEX40.fullmatch(commit):
        raise BuildError("git did not resolve to a full 40-character commit")
    return commit


def _assert_clean_component(repo: Path, commit: str) -> None:
    """Refuse changed component files so the commit is the build source of truth."""

    status = _git(repo, "status", "--porcelain=v1", "--untracked-files=all", "--", COMPONENT_PATH)
    if status.strip():
        lines = status.decode("utf-8", "replace").splitlines()
        raise BuildError(f"component worktree is dirty; build the committed source: {lines[0]}")
    del commit


def _tree_entries(repo: Path, commit: str) -> list[tuple[str, str, str, str]]:
    raw = _git(repo, "ls-tree", "-r", "-z", "--full-tree", commit, "--", COMPONENT_PATH)
    entries: list[tuple[str, str, str, str]] = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            left, path_bytes = record.split(b"\t", 1)
            mode, kind, object_id = left.decode("ascii").split(" ")
            path = path_bytes.decode("utf-8")
        except (UnicodeDecodeError, ValueError) as exc:
            raise BuildError("invalid git tree entry") from exc
        if not path.startswith(f"{COMPONENT_PATH}/"):
            raise BuildError(f"tree escaped component path: {path}")
        relative = path[len(COMPONENT_PATH) + 1 :]
        if not relative or relative.startswith("/") or ".." in PurePosixPath(relative).parts:
            raise BuildError(f"unsafe component path: {path}")
        if relative == "_build.json":
            raise BuildError("source component must not contain generated _build.json")
        if "\\" in relative or ":" in relative:
            raise BuildError(f"non-portable component path: {path}")
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise BuildError(f"component contains unsupported git entry: {mode} {kind} {path}")
        entries.append((path, relative, object_id, mode))
    if not entries:
        raise BuildError("component has no tracked files")
    return sorted(entries, key=lambda item: item[1])


def read_source(repo: Path, commit: str) -> list[SourceFile]:
    """Read regular tracked files from git without following working-tree links."""

    files: list[SourceFile] = []
    for path, relative, _object_id, mode_text in _tree_entries(repo, commit):
        data = _git(repo, "show", f"{commit}:{path}")
        # Preserve normal executable metadata if a future integration file needs
        # it, while rejecting executable scripts from accidentally widening the
        # package surface.
        mode = 0o755 if mode_text == "100755" else 0o644
        files.append(SourceFile(relative, data, mode))
    return files


def _canonical_files(files: Iterable[SourceFile]) -> dict[str, str]:
    return {item.path: hashlib.sha256(item.data).hexdigest() for item in sorted(files, key=lambda x: x.path)}


def _payload_digest(files: dict[str, str]) -> str:
    encoded = json.dumps(files, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _manifest(commit: str, files: list[SourceFile], license_data: bytes) -> bytes:
    hashes = _canonical_files(files)
    payload_digest = _payload_digest(hashes)
    marker = {
        "artifact_sha256": payload_digest,
        "component": COMPONENT,
        "commit": commit,
        "files": hashes,
        "format_version": FORMAT_VERSION,
        "license_sha256": hashlib.sha256(license_data).hexdigest(),
        "sha256_scope": "tracked-component-files",
    }
    return (json.dumps(marker, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _safe_member_name(name: str) -> None:
    if "\\" in name or "\x00" in name or re.match(r"^[A-Za-z]:", name):
        raise BuildError(f"archive path traversal: {name}")
    path = PurePosixPath(name)
    if path.is_absolute() or name.startswith("/") or ".." in path.parts:
        raise BuildError(f"archive path traversal: {name}")
    if name == "LICENSE":
        return
    if name.rstrip("/") == COMPONENT_PATH:
        return
    if not name.startswith(f"{COMPONENT_PATH}/"):
        raise BuildError(f"archive path outside component: {name}")


def validate_archive(archive: Path, expected_sha256: str | None = None) -> dict:
    """Validate archive shape and its provenance marker before a transfer."""

    if not archive.is_file():
        raise BuildError(f"artifact does not exist: {archive}")
    actual = hashlib.sha256(archive.read_bytes()).hexdigest()
    if expected_sha256 and actual != expected_sha256:
        raise BuildError("artifact sha256 does not match the approved digest")
    try:
        with tarfile.open(archive, mode="r:gz") as source:
            members = source.getmembers()
            marker_member = None
            seen_names: set[str] = set()
            for member in members:
                _safe_member_name(member.name)
                if member.name in seen_names:
                    raise BuildError(f"archive contains a duplicate entry: {member.name}")
                seen_names.add(member.name)
                if member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
                    raise BuildError(f"archive contains unsupported entry: {member.name}")
                if member.isdir() and member.name.rstrip("/") != COMPONENT_PATH:
                    raise BuildError(f"archive contains an unexpected directory: {member.name}")
                if member.name == f"{COMPONENT_PATH}/_build.json":
                    if marker_member is not None:
                        raise BuildError("archive contains duplicate _build.json marker")
                    marker_member = member
            if marker_member is None:
                raise BuildError("archive does not contain the component _build.json marker")
            marker_raw = source.extractfile(marker_member)
            if marker_raw is None:
                raise BuildError("cannot read _build.json marker")
            marker = json.loads(marker_raw.read().decode("utf-8"))
            if not isinstance(marker, dict):
                raise BuildError("build marker must be a JSON object")
            if marker.get("format_version") != FORMAT_VERSION or marker.get("component") != COMPONENT:
                raise BuildError("unsupported or mismatched build marker")
            if not _HEX40.fullmatch(str(marker.get("commit", ""))):
                raise BuildError("build marker commit is not a full git commit")
            if not re.fullmatch(r"[0-9a-f]{64}", str(marker.get("license_sha256", ""))):
                raise BuildError("build marker has no valid LICENSE hash")
            files = marker.get("files")
            if not isinstance(files, dict) or not files:
                raise BuildError("build marker has no file hashes")
            for relative, digest in files.items():
                if (
                    not isinstance(relative, str)
                    or not relative
                    or ".." in PurePosixPath(relative).parts
                    or "\\" in relative
                    or ":" in relative
                ):
                    raise BuildError("build marker contains an unsafe file path")
                if not re.fullmatch(r"[0-9a-f]{64}", str(digest)):
                    raise BuildError("build marker contains an invalid file hash")
            expected_paths = {f"{COMPONENT_PATH}/{path}" for path in files} | {"LICENSE"}
            actual_paths = {
                member.name for member in members if member.isfile() and member.name != f"{COMPONENT_PATH}/_build.json"
            }
            if actual_paths != expected_paths:
                raise BuildError("archive files do not match the build marker")
            for relative, expected_digest in files.items():
                member = next(member for member in members if member.name == f"{COMPONENT_PATH}/{relative}")
                payload = source.extractfile(member)
                if payload is None or hashlib.sha256(payload.read()).hexdigest() != expected_digest:
                    raise BuildError(f"archive content hash mismatch: {relative}")
            license_member = next(member for member in members if member.name == "LICENSE")
            license_payload = source.extractfile(license_member)
            if license_payload is None or hashlib.sha256(license_payload.read()).hexdigest() != marker.get("license_sha256"):
                raise BuildError("LICENSE content hash mismatch")
            if marker.get("artifact_sha256") != _payload_digest(files):
                raise BuildError("build marker payload digest mismatch")
            return {"archive_sha256": actual, "marker": marker, "size": archive.stat().st_size}
    except (OSError, UnicodeDecodeError, tarfile.TarError, json.JSONDecodeError) as exc:
        raise BuildError(f"invalid release archive: {exc}") from exc


def create_artifact(repo: Path, output_dir: Path, requested_commit: str | None = None) -> dict:
    repo = repo.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    commit = resolve_commit(repo, requested_commit)
    _assert_clean_component(repo, commit)
    files = read_source(repo, commit)
    license_data = _git(repo, "show", f"{commit}:LICENSE")
    marker = _manifest(commit, files, license_data)

    entries = [*files, SourceFile("_build.json", marker, 0o644)]
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
        root = f"{COMPONENT_PATH}/"
        root_info = tarfile.TarInfo(root)
        root_info.type = tarfile.DIRTYPE
        root_info.mode = 0o755
        root_info.mtime = 0
        root_info.uid = root_info.gid = 0
        root_info.uname = root_info.gname = ""
        tar.addfile(root_info)
        for item in sorted(entries, key=lambda x: x.path):
            name = f"{COMPONENT_PATH}/{item.path}"
            _safe_member_name(name)
            info = tarfile.TarInfo(name)
            info.size = len(item.data)
            info.mode = item.mode
            info.mtime = 0
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            tar.addfile(info, io.BytesIO(item.data))
        license_info = tarfile.TarInfo("LICENSE")
        license_info.size = len(license_data)
        license_info.mode = 0o644
        license_info.mtime = 0
        license_info.uid = license_info.gid = 0
        license_info.uname = license_info.gname = ""
        tar.addfile(license_info, io.BytesIO(license_data))
    compressed_buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=compressed_buffer, mode="wb", filename="", mtime=0, compresslevel=9) as gzip_stream:
        gzip_stream.write(tar_buffer.getvalue())
    compressed = compressed_buffer.getvalue()

    artifact = output_dir / f"{COMPONENT}-{commit}.tar.gz"
    artifact.write_bytes(compressed)
    archive_sha = hashlib.sha256(compressed).hexdigest()
    sidecar = artifact.with_suffix(artifact.suffix + ".sha256")
    sidecar.write_text(f"{archive_sha}  {artifact.name}\n", encoding="ascii", newline="\n")
    validated = validate_archive(artifact, archive_sha)
    return {
        "artifact": str(artifact),
        "archive_sha256": archive_sha,
        "commit": commit,
        "component": COMPONENT,
        "files": validated["marker"]["files"],
        "format_version": FORMAT_VERSION,
        "size": artifact.stat().st_size,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--commit", default=None, help="full or resolvable git commit-ish")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    output_dir = args.output_dir or args.repo_root / "dist"
    try:
        result = create_artifact(args.repo_root, output_dir, args.commit)
    except BuildError as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
