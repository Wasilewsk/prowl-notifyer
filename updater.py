from __future__ import annotations

import json
import os
import tempfile
import webbrowser
from dataclasses import dataclass
from typing import Optional, Tuple

import requests

from version import APP_VERSION, GITHUB_OWNER, GITHUB_REPO


GITHUB_LATEST_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
GITHUB_RELEASES_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"


@dataclass
class UpdateInfo:
    version: str
    download_url: Optional[str]
    release_url: str


def _normalize(version: str) -> Tuple[int, int, int]:
    v = version.strip()
    if v.startswith("v"):
        v = v[1:]
    parts = v.split(".")
    nums = [0, 0, 0]
    for i, part in enumerate(parts[:3]):
        try:
            nums[i] = int(part)
        except ValueError:
            nums[i] = 0
    return tuple(nums)  # type: ignore[return-value]


def is_newer(remote: str, local: str) -> bool:
    return _normalize(remote) > _normalize(local)


def fetch_latest(timeout_seconds: int = 10) -> UpdateInfo:
    response = requests.get(GITHUB_LATEST_URL, timeout=timeout_seconds)
    response.raise_for_status()
    data = response.json()

    tag = str(data.get("tag_name", "")).strip()
    assets = data.get("assets", [])
    download_url = None

    for asset in assets:
        name = str(asset.get("name", ""))
        if name.lower().endswith(".exe"):
            download_url = asset.get("browser_download_url")
            break

    return UpdateInfo(version=tag, download_url=download_url, release_url=GITHUB_RELEASES_URL)


def download_exe(url: str, filename: Optional[str] = None) -> str:
    if not filename:
        filename = os.path.basename(url) or "ProwlNotifier.exe"

    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(downloads, exist_ok=True)
    target = os.path.join(downloads, filename)

    with requests.get(url, stream=True, timeout=30) as r:
        r.raise_for_status()
        with open(target, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

    return target


def open_release_page() -> None:
    webbrowser.open(GITHUB_RELEASES_URL)


def current_version() -> str:
    return APP_VERSION
