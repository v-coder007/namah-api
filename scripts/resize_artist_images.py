#!/usr/bin/env python3
"""
Resize and convert artist images.

Usage:
  python3 scripts/resize_artist_images.py \n
    --input-dir img/artist \n
    --output-dir img/artist_resized \n
    --size 500 \n
    --format webp

The script will:
- Walk `--input-dir` (non-recursive by default), open common image files
- Center-crop them to a square (using the shorter side) and resize to `size`x`size`
- Convert and save as PNG or WebP (or keep original extension when using `auto`)
- Write results into `--output-dir` keeping a slugified filename

Notes:
- Requires Pillow (PIL). If not installed the script prints an install suggestion.
- By default it will overwrite files in the output directory. Use `--skip-existing` to avoid reprocessing.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
import imghdr

try:
    from PIL import Image
except Exception:
    print("Pillow is required. Install with: pip install Pillow", file=sys.stderr)
    raise

COMMON_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff'}


def center_crop_to_square(im: Image.Image) -> Image.Image:
    w, h = im.size
    if w == h:
        return im
    m = min(w, h)
    left = (w - m) // 2
    top = (h - m) // 2
    return im.crop((left, top, left + m, top + m))


def slugify_filename(p: Path) -> str:
    name = p.stem
    # simple slug: keep alnum, replace others with dash
    import re
    s = re.sub(r'[^0-9a-zA-Z]+', '-', name).strip('-').lower()
    if not s:
        s = 'image'
    return s


def process_file(path: Path, out_dir: Path, size: int, out_format: str, skip_existing: bool) -> tuple[bool, str]:
    # return (processed, message)
    try:
        # quick check using imghdr for some files
        if not path.is_file():
            return False, 'not-file'
        if path.suffix.lower() not in COMMON_EXTS:
            # allow reading many types, but skip obvious non-images
            typ = imghdr.what(path)
            if typ is None:
                return False, 'not-image'
        with Image.open(path) as im:
            im = im.convert('RGBA') if out_format == 'webp' else im.convert('RGB')
            imc = center_crop_to_square(im)
            im_resized = imc.resize((size, size), Image.LANCZOS)

            stem = slugify_filename(path)
            ext = out_format.lower()
            if ext == 'png':
                out_name = f"{stem}.png"
                out_path = out_dir / out_name
                if skip_existing and out_path.exists():
                    return False, 'skipped'
                im_resized.save(out_path, format='PNG', optimize=True)
            elif ext == 'webp':
                out_name = f"{stem}.webp"
                out_path = out_dir / out_name
                if skip_existing and out_path.exists():
                    return False, 'skipped'
                # quality 85 by default
                im_resized.save(out_path, format='WEBP', quality=85, method=6)
            else:
                # fallback: preserve original extension but ensure size
                out_name = f"{stem}{path.suffix.lower()}"
                out_path = out_dir / out_name
                if skip_existing and out_path.exists():
                    return False, 'skipped'
                im_resized.save(out_path)
            return True, str(out_path)
    except Exception as e:
        return False, f'error:{e}'


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='Resize and convert artist images to square thumbnails')
    ap.add_argument('--input-dir', '-i', default='img/artist', help='Input directory with artist images')
    ap.add_argument('--output-dir', '-o', default='img/artist_resized', help='Output directory for resized images')
    ap.add_argument('--size', '-s', type=int, default=500, help='Output size in pixels (square). Default: 500')
    ap.add_argument('--format', '-f', choices=['png', 'webp', 'auto'], default='webp', help='Output image format')
    ap.add_argument('--skip-existing', action='store_true', help='Skip processing if output file exists')
    ap.add_argument('--recursive', '-r', action='store_true', help='Recursively walk input dir')
    args = ap.parse_args(argv)

    in_dir = Path(args.input_dir)
    out_dir = Path(args.output_dir)
    size = int(args.size)

    if args.format == 'auto':
        # prefer webp when Pillow supports it
        try:
            Image.new('RGBA', (1, 1)).save if True else None
            out_format = 'webp' if 'WEBP' in Image.registered_extensions().values() or Image.SAVE.keys() else 'png'
        except Exception:
            out_format = 'png'
    else:
        out_format = args.format

    if not in_dir.exists():
        print(f'Input directory does not exist: {in_dir}', file=sys.stderr)
        return 2
    out_dir.mkdir(parents=True, exist_ok=True)

    paths = list(in_dir.rglob('*') if args.recursive else in_dir.iterdir())
    total = 0
    processed = 0
    skipped = 0
    errors = 0
    for p in paths:
        if p.is_dir():
            continue
        total += 1
        ok, msg = process_file(p, out_dir, size, out_format, args.skip_existing)
        if ok:
            processed += 1
            print(f'OK: {p} -> {msg}')
        else:
            if msg == 'skipped':
                skipped += 1
                print(f'SKIP: {p} ({msg})')
            elif msg in ('not-image', 'not-file'):
                print(f'SKIP: {p} ({msg})')
            else:
                errors += 1
                print(f'ERR: {p} ({msg})')

    print('\nSummary:')
    print('  input files scanned:', total)
    print('  processed:', processed)
    print('  skipped:', skipped)
    print('  errors:', errors)
    return 0 if errors == 0 else 3


if __name__ == '__main__':
    raise SystemExit(main())
