#!/usr/bin/env python3
import os
import re
import sys
import time
import requests
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin

from tqdm import tqdm


DOWNLOAD_PAGE = "https://www.marktstammdatenregister.de/MaStR/Datendownload"
BASE_URL = "https://download.marktstammdatenregister.de"


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            for k, v in attrs:
                if k == "href":
                    self.links.append(v)


def MaStrDownloader(output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)

    print("Fetching download page...")
    resp = requests.get(DOWNLOAD_PAGE, timeout=20)
    resp.raise_for_status()

    parser = LinkParser()
    parser.feed(resp.text)

    pattern = re.compile(r"Gesamtdatenexport_(\d{8}).*\.zip")
    candidates = []

    for href in parser.links:
        match = pattern.search(href)
        if match:
            date_str = match.group(1)
            try:
                date = datetime.strptime(date_str, "%Y%m%d").date()
                full_url = urljoin(BASE_URL + "/", href.lstrip("/"))
                candidates.append((date, full_url))
            except ValueError:
                pass

    if not candidates:
        raise ValueError("No valid Gesamtdatenexport ZIP files found.")

    candidates.sort(key=lambda x: x[0], reverse=True)
    latest_date, latest_url = candidates[0]

    filename = latest_url.split("/")[-1]
    local_path = os.path.join(output_dir, filename)

    print(f"Latest export: {filename} ({latest_date})")
    print(f"Downloading: {latest_url}")

    head = requests.head(latest_url, allow_redirects=True, timeout=10)
    head.raise_for_status()
    total_size = int(head.headers.get("Content-Length", 0))

    resp = requests.get(latest_url, stream=True, timeout=60)
    resp.raise_for_status()

    with tqdm(
        total=total_size,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        desc=filename,
        file=sys.stdout,
    ) as pbar:
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))

    print(f"\nSaved: {local_path}")
    return local_path


# if __name__ == "__main__":
#     try:
#         file_path = MaStrDownloader(output_dir=os.path.expanduser("~/Downloads/mastr"))
#         print(f"\nDownloaded successfully:\n→ {file_path}")
#         sys.exit(0)
#     except Exception as e:
#         print(f"\nError: {e}")
#         sys.exit(1)
