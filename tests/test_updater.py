"""Tests for the GitHub Release updater."""

import os
import zipfile

import pytest

from networkfixer.core.updater import (
    UpdateError,
    build_apply_script,
    compare_versions,
    extract_release_zip,
    file_sha256,
    is_allowed_download_url,
    is_allowed_transfer_url,
    parse_release_payload,
    parse_sha256_text,
    ps_single_quote,
    stage_release,
)


PACKAGE_URL = (
    "https://github.com/HYGUO1993/NetworkFixer/releases/download/"
    "v2.2.0/NetworkFixer-v2.2.0-windows.zip"
)
CHECKSUM_URL = PACKAGE_URL + ".sha256"


class _Body:
    def __init__(self, payload, headers=None):
        self._data = payload if isinstance(payload, bytes) else payload.encode("utf-8")
        self.headers = headers or {}

    def read(self, size=-1):
        if size is None or size < 0:
            chunk, self._data = self._data, b""
            return chunk
        chunk, self._data = self._data[:size], self._data[size:]
        return chunk

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class _Opener:
    def __init__(self, routes):
        self.routes = routes

    def open(self, request, timeout=None):
        if request.full_url not in self.routes:
            raise AssertionError(request.full_url)
        payload, headers = self.routes[request.full_url]
        return _Body(payload, headers)


def _release_payload():
    return {
        "tag_name": "v2.2.0",
        "html_url": "https://github.com/HYGUO1993/NetworkFixer/releases/tag/v2.2.0",
        "body": "Microsoft diagnostics",
        "assets": [
            {
                "name": "NetworkFixer-v2.2.0-windows.zip",
                "browser_download_url": PACKAGE_URL,
                "size": 10,
            },
            {
                "name": "NetworkFixer-v2.2.0-windows.zip.sha256",
                "browser_download_url": CHECKSUM_URL,
                "size": 10,
            },
        ],
    }


def test_compare_versions_ignores_leading_v():
    assert compare_versions("2.1.0", "v2.2.0") == -1
    assert compare_versions("v2.2.0", "2.2.0") == 0
    assert compare_versions("2.3.0", "v2.2.1") == 1


def test_download_url_stays_on_this_repository():
    assert is_allowed_download_url(PACKAGE_URL) is True
    assert is_allowed_download_url("http://github.com/HYGUO1993/NetworkFixer/releases/download/v1/a.zip") is False
    assert is_allowed_download_url("https://github.com/other/NetworkFixer/releases/download/v1/a.zip") is False
    assert is_allowed_transfer_url("https://objects.githubusercontent.com/abc") is True
    assert is_allowed_transfer_url("https://example.com/NetworkFixer.exe") is False


def test_parse_release_requires_windows_zip_and_checksum():
    info = parse_release_payload(_release_payload())
    assert info.tag == "v2.2.0"
    assert info.package.name.endswith(".zip")
    assert info.checksum.name.endswith(".sha256")

    payload = _release_payload()
    payload["assets"] = payload["assets"][:1]
    with pytest.raises(UpdateError) as caught:
        parse_release_payload(payload)
    assert caught.value.key == "update.error.no_checksum"


def test_parse_sha256_text_reads_published_line():
    text = "ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789  NetworkFixer.zip\r\n"
    assert parse_sha256_text(text) == "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
    with pytest.raises(UpdateError):
        parse_sha256_text("not-a-hash")


def test_extract_release_zip_rejects_parent_paths(tmp_path):
    archive_path = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../evil.txt", "nope")
    with pytest.raises(UpdateError) as caught:
        extract_release_zip(str(archive_path), str(tmp_path / "out"))
    assert caught.value.key == "update.error.unsafe_zip"


def test_stage_release_checks_hash_and_finds_executable(tmp_path):
    package_path = tmp_path / "NetworkFixer-v2.2.0-windows.zip"
    with zipfile.ZipFile(package_path, "w") as archive:
        archive.writestr("NetworkFixer.exe", b"MZ")
        archive.writestr("_internal/app.dll", b"x")
    package = package_path.read_bytes()
    digest = file_sha256(str(package_path))
    opener = _Opener({
        CHECKSUM_URL: (f"{digest}  NetworkFixer-v2.2.0-windows.zip\n", {}),
        PACKAGE_URL: (package, {"Content-Length": str(len(package))}),
    })
    info = parse_release_payload(_release_payload())
    payload_dir = stage_release(info, work_dir=str(tmp_path / "work"), opener=opener)
    assert os.path.isfile(os.path.join(payload_dir, "NetworkFixer.exe"))


def test_stage_release_rejects_checksum_mismatch(tmp_path):
    opener = _Opener({
        CHECKSUM_URL: ("a" * 64 + "  package.zip\n", {}),
        PACKAGE_URL: (b"not-the-package", {"Content-Length": "15"}),
    })
    info = parse_release_payload(_release_payload())
    with pytest.raises(UpdateError) as caught:
        stage_release(info, work_dir=str(tmp_path / "work"), opener=opener)
    assert caught.value.key == "update.error.checksum"


def test_apply_script_quotes_paths_and_waits_for_pid(tmp_path):
    source = tmp_path / "payload"
    install = tmp_path / "install"
    source.mkdir()
    install.mkdir()
    (source / "NetworkFixer.exe").write_bytes(b"MZ")
    script = build_apply_script(4321, str(source), str(install))
    assert "Wait-Process -Id 4321" in script
    assert "'" + str(install) + "'" in script
    assert "NetworkFixer.exe" in script


def test_ps_quote_escapes_single_quotes():
    assert ps_single_quote(r"C:\Program Files\O'Hare") == r"'C:\Program Files\O''Hare'"


def test_apply_script_rejects_overlapping_directories(tmp_path):
    install = tmp_path / "app"
    install.mkdir()
    source = install / "payload"
    source.mkdir()
    (source / "NetworkFixer.exe").write_bytes(b"MZ")
    with pytest.raises(UpdateError) as caught:
        build_apply_script(1, str(source), str(install))
    assert caught.value.key == "update.error.unsafe_path"
