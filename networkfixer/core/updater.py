"""Check GitHub Releases and stage a Windows package update.

The packaged app downloads the official zip, checks its published SHA256,
then hands the file copy to a helper process. A source checkout only reports
the newer release; it does not overwrite the working tree.
"""

import hashlib
import json
import logging
import os
import stat
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from typing import Callable, Optional, Sequence

logger = logging.getLogger(__name__)

REPO = "HYGUO1993/NetworkFixer"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
DOWNLOAD_PREFIX = f"https://github.com/{REPO}/releases/download/"
REDIRECT_HOSTS = {
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
    "github-releases.githubusercontent.com",
}
MAX_DOWNLOAD_BYTES = 200 * 1024 * 1024
CREATE_NO_WINDOW = 0x08000000

ProgressCallback = Callable[[int, int], None]


class UpdateError(Exception):
    def __init__(self, key: str, **kwargs):
        self.key = key
        self.kwargs = kwargs
        super().__init__(key)


@dataclass
class ReleaseAsset:
    name: str
    download_url: str
    size: int = 0


@dataclass
class ReleaseInfo:
    tag: str
    html_url: str
    body: str
    package: ReleaseAsset
    checksum: ReleaseAsset


class _GuardedRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not is_allowed_transfer_url(newurl):
            raise UpdateError("update.error.redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def is_frozen_app() -> bool:
    return bool(getattr(sys, "frozen", False))


def install_directory() -> str:
    if not is_frozen_app():
        raise UpdateError("update.error.source_mode")
    return os.path.dirname(os.path.abspath(sys.executable))


def parse_version(value: str) -> tuple:
    text = (value or "").strip()
    if text[:1] in ("v", "V"):
        text = text[1:]
    text = text.split("-", 1)[0].split("+", 1)[0]
    if not text:
        raise UpdateError("update.error.bad_version")
    parts = []
    for piece in text.split("."):
        if not piece.isdigit():
            raise UpdateError("update.error.bad_version")
        parts.append(int(piece))
    return tuple(parts)


def compare_versions(left: str, right: str) -> int:
    """Return -1, 0, or 1 when left is older, equal, or newer than right."""
    current = parse_version(left)
    latest = parse_version(right)
    width = max(len(current), len(latest))
    current = current + (0,) * (width - len(current))
    latest = latest + (0,) * (width - len(latest))
    if current < latest:
        return -1
    if current > latest:
        return 1
    return 0


def notes_excerpt(body: str, limit: int = 500) -> str:
    text = "\n".join(line.rstrip() for line in (body or "").splitlines()).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def is_allowed_download_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    return (
        parsed.scheme == "https"
        and (parsed.hostname or "").lower() == "github.com"
        and parsed.path.startswith(f"/{REPO}/releases/download/")
    )


def is_allowed_transfer_url(url: str) -> bool:
    if is_allowed_download_url(url):
        return True
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and host in REDIRECT_HOSTS


def select_release_assets(assets: Sequence[dict]) -> tuple:
    packages = []
    for asset in assets:
        name = str(asset.get("name") or "")
        url = str(asset.get("browser_download_url") or "")
        if not name.lower().endswith(".zip"):
            continue
        if "windows" not in name.lower():
            continue
        if not is_allowed_download_url(url):
            continue
        packages.append(asset)
    if not packages:
        raise UpdateError("update.error.no_asset")

    package = packages[0]
    checksum_name = package["name"] + ".sha256"
    checksum = next(
        (
            asset for asset in assets
            if asset.get("name") == checksum_name
            and is_allowed_download_url(str(asset.get("browser_download_url") or ""))
        ),
        None,
    )
    if checksum is None:
        raise UpdateError("update.error.no_checksum")
    return package, checksum


def parse_release_payload(payload: dict) -> ReleaseInfo:
    tag = str(payload.get("tag_name") or "")
    parse_version(tag)
    package, checksum = select_release_assets(payload.get("assets") or [])
    return ReleaseInfo(
        tag=tag,
        html_url=str(payload.get("html_url") or f"https://github.com/{REPO}/releases/tag/{tag}"),
        body=str(payload.get("body") or ""),
        package=ReleaseAsset(
            name=str(package["name"]),
            download_url=str(package["browser_download_url"]),
            size=int(package.get("size") or 0),
        ),
        checksum=ReleaseAsset(
            name=str(checksum["name"]),
            download_url=str(checksum["browser_download_url"]),
            size=int(checksum.get("size") or 0),
        ),
    )


def build_opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(_GuardedRedirectHandler)


def fetch_latest_release(
    opener: Optional[urllib.request.OpenerDirector] = None,
    timeout: float = 20,
) -> ReleaseInfo:
    if urllib.parse.urlparse(API_URL).scheme != "https":
        raise UpdateError("update.error.network")
    request = urllib.request.Request(
        API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "NetworkFixer",
        },
    )
    client = opener or build_opener()
    try:
        with client.open(request, timeout=timeout) as response:
            raw = response.read(MAX_DOWNLOAD_BYTES + 1)
    except UpdateError:
        raise
    except Exception as exc:
        logger.error(f"Release lookup failed: {exc}")
        raise UpdateError("update.error.network", error=str(exc)) from exc

    if len(raw) > MAX_DOWNLOAD_BYTES:
        raise UpdateError("update.error.too_large")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateError("update.error.network", error=str(exc)) from exc
    return parse_release_payload(payload)


def download_file(
    url: str,
    destination: str,
    opener: Optional[urllib.request.OpenerDirector] = None,
    timeout: float = 120,
    progress: Optional[ProgressCallback] = None,
) -> None:
    if not is_allowed_download_url(url):
        raise UpdateError("update.error.redirect")
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/octet-stream",
            "User-Agent": "NetworkFixer",
        },
    )
    client = opener or build_opener()
    try:
        with client.open(request, timeout=timeout) as response:
            total = int(response.headers.get("Content-Length") or 0)
            if total > MAX_DOWNLOAD_BYTES:
                raise UpdateError("update.error.too_large")
            written = 0
            with open(destination, "wb") as handle:
                while True:
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > MAX_DOWNLOAD_BYTES:
                        raise UpdateError("update.error.too_large")
                    handle.write(chunk)
                    if progress is not None and total > 0:
                        progress(written, total)
    except UpdateError:
        _remove_file(destination)
        raise
    except Exception as exc:
        _remove_file(destination)
        logger.error(f"Download failed: {exc}")
        raise UpdateError("update.error.network", error=str(exc)) from exc


def file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_sha256_text(text: str) -> str:
    parts = text.strip().split()
    if not parts:
        raise UpdateError("update.error.checksum")
    token = parts[0].lower()
    if len(token) != 64 or any(char not in "0123456789abcdef" for char in token):
        raise UpdateError("update.error.checksum")
    return token


def extract_release_zip(zip_path: str, destination: str) -> str:
    os.makedirs(destination, exist_ok=True)
    dest_root = os.path.abspath(destination)
    try:
        with zipfile.ZipFile(zip_path) as archive:
            for info in archive.infolist():
                _ensure_member_inside(dest_root, info.filename)
            archive.extractall(dest_root)
    except UpdateError:
        raise
    except zipfile.BadZipFile as exc:
        raise UpdateError("update.error.bad_zip") from exc

    payload = find_payload_dir(dest_root)
    if not os.path.isfile(os.path.join(payload, "NetworkFixer.exe")):
        raise UpdateError("update.error.missing_exe")
    return payload


def stage_release(
    info: ReleaseInfo,
    work_dir: Optional[str] = None,
    opener: Optional[urllib.request.OpenerDirector] = None,
    progress: Optional[ProgressCallback] = None,
) -> str:
    root = work_dir or tempfile.mkdtemp(prefix="NetworkFixer-update-")
    os.makedirs(root, exist_ok=True)
    package_path = os.path.join(root, info.package.name)
    checksum_path = os.path.join(root, info.checksum.name)
    download_file(info.checksum.download_url, checksum_path, opener=opener, timeout=30)
    with open(checksum_path, "r", encoding="utf-8") as handle:
        expected = parse_sha256_text(handle.read())
    download_file(info.package.download_url, package_path, opener=opener, progress=progress)
    actual = file_sha256(package_path)
    if actual != expected:
        _remove_file(package_path)
        raise UpdateError("update.error.checksum")
    return extract_release_zip(package_path, os.path.join(root, "payload"))


def find_payload_dir(root: str) -> str:
    direct = os.path.join(root, "NetworkFixer.exe")
    if os.path.isfile(direct):
        return root
    for current, _dirs, files in os.walk(root):
        relation = os.path.relpath(current, root)
        depth = 0 if relation == "." else relation.count(os.sep) + 1
        if depth > 2:
            continue
        if "NetworkFixer.exe" in files:
            return current
    raise UpdateError("update.error.missing_exe")


def ps_single_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def build_apply_script(pid: int, source_dir: str, install_dir: str) -> str:
    _ensure_replace_is_safe(source_dir, install_dir)
    source = ps_single_quote(os.path.abspath(source_dir))
    dest = ps_single_quote(os.path.abspath(install_dir))
    exe = ps_single_quote(os.path.join(os.path.abspath(install_dir), "NetworkFixer.exe"))
    return "\n".join([
        "$ErrorActionPreference = 'Stop'",
        f"Wait-Process -Id {int(pid)} -ErrorAction SilentlyContinue",
        "Start-Sleep -Seconds 2",
        f"Copy-Item -Path (Join-Path {source} '*') -Destination {dest} -Recurse -Force",
        f"Start-Process -FilePath {exe}",
        f"Remove-Item -LiteralPath {source} -Recurse -Force -ErrorAction SilentlyContinue",
        "",
    ])


def start_staged_replace(source_dir: str, install_dir: str, pid: Optional[int] = None) -> str:
    _ensure_replace_is_safe(source_dir, install_dir)
    script = build_apply_script(pid if pid is not None else os.getpid(), source_dir, install_dir)
    script_dir = tempfile.mkdtemp(prefix="NetworkFixer-apply-")
    script_path = os.path.join(script_dir, "apply-update.ps1")
    with open(script_path, "w", encoding="utf-8") as handle:
        handle.write(script)
    subprocess.Popen(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            script_path,
        ],
        creationflags=CREATE_NO_WINDOW,
        close_fds=True,
    )
    return script_path


def _ensure_member_inside(root: str, name: str) -> None:
    if not name or name.startswith(("/", "\\")) or ":" in name:
        raise UpdateError("update.error.unsafe_zip")
    target = os.path.abspath(os.path.join(root, name))
    if not _is_inside(root, target):
        raise UpdateError("update.error.unsafe_zip")


def _ensure_replace_is_safe(source_dir: str, install_dir: str) -> None:
    source = os.path.abspath(source_dir)
    install = os.path.abspath(install_dir)
    if source == install or _is_inside(source, install) or _is_inside(install, source):
        raise UpdateError("update.error.unsafe_path")
    exe = os.path.join(source, "NetworkFixer.exe")
    if not os.path.isfile(exe):
        raise UpdateError("update.error.missing_exe")


def _is_inside(parent: str, child: str) -> bool:
    parent_abs = os.path.abspath(parent)
    child_abs = os.path.abspath(child)
    try:
        return os.path.commonpath([parent_abs, child_abs]) == parent_abs and child_abs != parent_abs
    except ValueError:
        return False


def _remove_file(path: str) -> None:
    try:
        os.chmod(path, stat.S_IWRITE)
        os.remove(path)
    except OSError:
        pass
