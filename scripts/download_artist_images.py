#!/usr/bin/env python3
"""
Download representative artist images for the project.

Usage:
  python3 scripts/download_artist_images.py --input api/artists_videos.json --out-dir img/artist --map api/artists_images.json --limit 0

This script tries the following (in order) for each artist:
 1. Look for an English Wikipedia page and extract `og:image` or infobox image.
 2. Fall back to Wikimedia Commons search and get the first File: image.
Downloaded files are saved with a slugified filename under the output directory and a JSON map is written.

The script is defensive and intended to be run locally where network access is available.
"""

import argparse
import json
import os
import re
import time
from urllib.parse import quote
from urllib.request import urlopen, Request, urlretrieve
from urllib.error import HTTPError, URLError


HEADERS = {"User-Agent": "namah-api-image-downloader/1.0 (+https://github.com)"}


def slugify(name: str) -> str:
    return re.sub(r"[^0-9a-zA-Z]+", "-", name).strip("-").lower() or "unknown"


def fetch_url_text(url: str, timeout=20):
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def try_wikipedia_image(artist: str):
    slug = quote(artist.replace(" ", "_"))
    url = f"https://en.wikipedia.org/wiki/{slug}"
    try:
        html = fetch_url_text(url)
    except HTTPError:
        return None
    # og:image meta
    m = re.search(r'<meta property="og:image" content="([^"]+)"', html)
    if m:
        return m.group(1)
    # infobox image
    m = re.search(r'<table[^>]*class="infobox[^>]*".*?</table>', html, re.S)
    if m:
        block = m.group(0)
        mi = re.search(r'<img[^>]+src="([^"]+)"', block)
        if mi:
            src = mi.group(1)
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                src = "https://en.wikipedia.org" + src
            return src
    return None


def try_commons_image(artist: str):
    q = quote(artist)
    url = f"https://commons.wikimedia.org/w/index.php?search={q}&title=Special%3ASearch&go=Go"
    try:
        html = fetch_url_text(url)
    except Exception:
        return None
    m = re.search(r'href="(/wiki/File:[^"]+)"', html)
    if not m:
        return None
    file_page = "https://commons.wikimedia.org" + m.group(1)
    try:
        file_html = fetch_url_text(file_page)
    except Exception:
        return None
    m2 = re.search(r'<meta property="og:image" content="([^"]+)"', file_html)
    if m2:
        return m2.group(1)
    m3 = re.search(r'href="(https?://upload.wikimedia.org/[^"]+)"', file_html)
    if m3:
        return m3.group(1)
    return None


def download_image(url: str, out_path: str):
    if url.startswith("//"):
        url = "https:" + url
    # urlretrieve will follow redirects
    urlretrieve(url, out_path)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="api/artists_videos.json")
    p.add_argument("--out-dir", default="img/artist")
    p.add_argument("--map", default="api/artists_images.json")
    p.add_argument("--limit", type=int, default=0, help="0 means no limit; otherwise number of artists to process")
    p.add_argument("--sleep", type=float, default=0.2, help="sleep seconds between requests")
    args = p.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    with open(args.input, 'r', encoding='utf-8') as f:
        artists_data = json.load(f)

    artists = [a['artist'] for a in artists_data]

    mapping = {}
    processed = 0
    for artist in artists:
        if args.limit and processed >= args.limit:
            break
        print(f"[{processed+1}/{len(artists)}] resolving: {artist}")
        img_url = None
        try:
            img_url = try_wikipedia_image(artist)
        except Exception:
            img_url = None
        if not img_url:
            try:
                img_url = try_commons_image(artist)
            except Exception:
                img_url = None
        # fallback title-case
        if not img_url:
            try:
                img_url = try_wikipedia_image(artist.title())
            except Exception:
                img_url = None

        if not img_url:
            print(f"  -> image not found for: {artist}")
            mapping[artist] = None
            processed += 1
            time.sleep(args.sleep)
            continue

        # guess extension
        mext = re.search(r"\.(jpg|jpeg|png|svg|webp)(?:[\?|$])", img_url, re.I)
        ext = (mext.group(1).lower() if mext else 'jpg')
        slug = slugify(artist)
        fname = f"{slug}.{ext}"
        out_path = os.path.join(args.out_dir, fname)
        try:
            print(f"  -> downloading {img_url} -> {out_path}")
            download_image(img_url, out_path)
            mapping[artist] = out_path
            processed += 1
        except Exception as e:
            print(f"  ! download failed for {artist}: {e}")
            mapping[artist] = None
            processed += 1
        time.sleep(args.sleep)

    with open(args.map, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    found = sum(1 for v in mapping.values() if v)
    total = len(artists)
    print(f"done. processed={processed} total_artists={total} found_images={found}")


if __name__ == '__main__':
    main()
