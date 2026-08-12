"""Lightweight access to the current official Policia Nacional crime files."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin

import requests


SOURCE_PAGE = "https://chat.policia.gov.co/estadistica-delictiva"
DATA_DIR = Path("policia_xlsx")
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/octet-stream",
    "User-Agent": "SISC-Jamundi-Source-Monitor/1.0",
}


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.current_href = None
        self.current_text = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        self.current_href = dict(attrs).get("href")
        self.current_text = []

    def handle_data(self, data):
        if self.current_href:
            self.current_text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self.current_href:
            self.links.append((self.current_href, " ".join(self.current_text).strip()))
            self.current_href = None
            self.current_text = []


def discover_record_files(html: str, base_url: str = SOURCE_PAGE) -> dict[int, str]:
    parser = LinkParser()
    parser.feed(html)
    discovered = {}
    for href, text in parser.links:
        decoded = unquote(f"{href} {text}")
        normalized = "".join(
            character
            for character in unicodedata.normalize("NFKD", " ".join(decoded.split()).casefold())
            if not unicodedata.combining(character)
        )
        if "informacion" not in normalized or "delitos" not in normalized:
            continue
        if "nivel" not in normalized or "registro" not in normalized:
            continue
        match = re.search(r"20\d{2}", decoded)
        if match and ".xlsx" in href.casefold():
            discovered[int(match.group(0))] = urljoin(base_url, href)
    return discovered


def fetch_record_files(session=None, now=None) -> dict[int, str]:
    session = session or requests.Session()
    response = session.get(SOURCE_PAGE, headers=HEADERS, timeout=30)
    response.raise_for_status()
    discovered = discover_record_files(response.text)
    current_year = (now or datetime.now()).year
    selected = {
        year: discovered[year]
        for year in (current_year - 1, current_year)
        if year in discovered
    }
    if len(selected) != 2:
        raise RuntimeError(
            f"La fuente oficial no publico ambos archivos requeridos: {current_year - 1} y {current_year}."
        )
    return selected


def remote_metadata(url: str, session=None) -> dict[str, str]:
    session = session or requests.Session()
    response = session.get(
        url,
        headers={**HEADERS, "Range": "bytes=0-4095"},
        timeout=30,
        stream=True,
        allow_redirects=True,
    )
    response.raise_for_status()
    sample = bytearray()
    for chunk in response.iter_content(chunk_size=4096):
        sample.extend(chunk)
        if len(sample) >= 4096:
            break
    content_range = (response.headers.get("Content-Range") or "").strip()
    total_match = re.search(r"/(\d+)$", content_range)
    metadata = {
        "url": response.url,
        "etag": (response.headers.get("ETag") or "").strip(),
        "last_modified": (response.headers.get("Last-Modified") or "").strip(),
        "content_length": (
            total_match.group(1)
            if total_match
            else (response.headers.get("Content-Length") or "").strip()
        ),
        "prefix_sha256": hashlib.sha256(bytes(sample)).hexdigest(),
    }
    response.close()
    return metadata


def calculate_fingerprint(files: dict[int, str], session=None) -> tuple[str, dict]:
    session = session or requests.Session()
    details = {
        str(year): remote_metadata(url, session=session)
        for year, url in sorted(files.items())
    }
    payload = json.dumps(details, ensure_ascii=True, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest(), details


def download_file(url: str, destination: Path, session=None) -> int:
    session = session or requests.Session()
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    with session.get(url, headers=HEADERS, timeout=240, stream=True) as response:
        response.raise_for_status()
        with partial.open("wb") as output:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    output.write(chunk)
    with partial.open("rb") as downloaded_file:
        signature = downloaded_file.read(2)
    if partial.stat().st_size < 10_000 or signature != b"PK":
        partial.unlink(missing_ok=True)
        raise RuntimeError(f"La descarga de {url} no es un XLSX valido.")
    partial.replace(destination)
    return destination.stat().st_size


def download_selected(files: dict[int, str], session=None) -> dict:
    session = session or requests.Session()
    downloaded = {}
    for year, url in sorted(files.items()):
        destination = DATA_DIR / f"registro_delitos_{year}.xlsx"
        size = download_file(url, destination, session=session)
        downloaded[str(year)] = {
            "url": url,
            "path": str(destination),
            "bytes": size,
        }
        print(f"[OK] {year}: {size:,} bytes -> {destination}")
    manifest = {
        "source_page": SOURCE_PAGE,
        "checked_at": datetime.now().astimezone().isoformat(),
        "files": downloaded,
    }
    (DATA_DIR / "fuente_oficial.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fingerprint", action="store_true")
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    files = fetch_record_files()
    if args.fingerprint:
        fingerprint, details = calculate_fingerprint(files)
        print(json.dumps(details, ensure_ascii=False, sort_keys=True))
        print(fingerprint)
        return
    if args.download:
        download_selected(files)
        return
    parser.error("Use --fingerprint or --download")


if __name__ == "__main__":
    main()
