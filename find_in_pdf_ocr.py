#!/usr/bin/env python3

import argparse
import json
import os
import shutil
import sys
import time
import hashlib
import tempfile
import functools
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from pdf2image import convert_from_path
import pytesseract

# Unbuffered output
print = functools.partial(print, flush=True)

# Use a project-local temp dir. Tesseract is spawned as a subprocess and on some
# systems (sandboxed macOS) it can't read files written to the system /tmp, which
# made pytesseract fail silently on every page. Keeping temp files inside the
# project sidesteps that. Runs at import so ProcessPoolExecutor workers inherit it.
TMP_DIR = Path(__file__).resolve().parent / ".ocr_tmp"
TMP_DIR.mkdir(exist_ok=True)
os.environ["TMPDIR"] = str(TMP_DIR)
tempfile.tempdir = str(TMP_DIR)

parser = argparse.ArgumentParser(description="Search text in PDF files via OCR")
parser.add_argument("query", help="Search query")
parser.add_argument("source", nargs="?", default="source", help="PDF folder (default: source)")
parser.add_argument("--copy", action="store_true", help="Copy matched files to output/")
parser.add_argument("--lang", default="rus", help="OCR language (default: rus). Examples: eng, rus+eng")
args = parser.parse_args()

SEARCH_TERM = args.query.lower()
SOURCE_DIR = args.source
COPY_RESULTS = args.copy
LANG = args.lang
WORKERS = os.cpu_count() or 4
CACHE_FILE = "ocr_cache.json"
OUTPUT_DIR = "output"


def file_hash(path):
    """Calculate MD5 hash of a file."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_cache():
    """Load cache from file."""
    if Path(CACHE_FILE).exists():
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    """Save cache to file."""
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def ocr_pdf(pdf_path):
    """Process a single PDF. Returns (path, page_texts, found_pages, error)."""
    path_str = str(pdf_path)
    try:
        images = convert_from_path(path_str)
    except Exception as e:
        return (path_str, {}, [], f"Conversion error: {e}")

    pages_text = {}
    found_pages = []

    for page_num, image in enumerate(images, start=1):
        try:
            text = pytesseract.image_to_string(image, lang=LANG)
            pages_text[str(page_num)] = text
            if SEARCH_TERM in text.lower():
                found_pages.append(page_num)
        except Exception as e:
            pages_text[str(page_num)] = ""

    return (path_str, pages_text, found_pages, None)


def search_cached(cached_texts):
    """Search for matches in cached texts."""
    found_pages = []
    for page_str, text in cached_texts.items():
        if SEARCH_TERM in text.lower():
            found_pages.append(int(page_str))
    return found_pages


def main():
    start = time.time()

    pdf_files = sorted(Path(SOURCE_DIR).rglob("*.pdf"))
    total = len(pdf_files)

    print(f"{'='*50}")
    print(f"  PDF OCR Search: \"{SEARCH_TERM}\"")
    print(f"  Folder: {SOURCE_DIR}")
    print(f"  OCR lang: {LANG}")
    print(f"  PDF files: {total}")
    print(f"  Workers: {WORKERS}")
    print(f"{'='*50}")

    # Load cache
    cache = load_cache()
    cached_count = 0
    print(f"\n[CACHE] Loaded: {len(cache)} entries")

    # Split into cached and new
    to_process = []
    results = []

    print(f"[HASH]  Computing file hashes...")
    hashes = {}
    for pdf_path in pdf_files:
        h = file_hash(pdf_path)
        hashes[str(pdf_path)] = h

    for pdf_path in pdf_files:
        path_str = str(pdf_path)
        h = hashes[path_str]
        if h in cache:
            cached_count += 1
            found = search_cached(cache[h]["texts"])
            if found:
                results.append((path_str, found))
        else:
            to_process.append(pdf_path)

    print(f"[CACHE] From cache: {cached_count} files")
    print(f"[OCR]   Need OCR: {len(to_process)} files")

    if not to_process:
        print(f"\n[OK]    All files cached, no OCR needed!")
    else:
        # Time estimate
        est_pages = len(to_process) * 5
        est_seconds = est_pages * 1.5 / WORKERS
        print(f"[EST]   ~{est_pages} pages, ~{est_seconds:.0f}s ({est_seconds/60:.1f} min)")
        print(f"\n[OCR]   Starting...\n")

        done = 0
        errors = 0
        ocr_start = time.time()

        with ProcessPoolExecutor(max_workers=WORKERS) as executor:
            futures = {executor.submit(ocr_pdf, p): p for p in to_process}

            for future in as_completed(futures):
                done += 1
                path_str, pages_text, found_pages, error = future.result()
                h = hashes[path_str]

                elapsed = time.time() - ocr_start
                speed = done / elapsed if elapsed > 0 else 0
                remaining = len(to_process) - done
                eta = remaining / speed if speed > 0 else 0

                if error:
                    errors += 1
                    print(f"  [{done}/{len(to_process)}] x ERROR {Path(path_str).name}: {error}")
                else:
                    page_count = len(pages_text)
                    cache[h] = {"path": path_str, "texts": pages_text}

                    if found_pages:
                        pages_str = ", ".join(str(p) for p in sorted(found_pages))
                        print(f"  [{done}/{len(to_process)}] + FOUND {Path(path_str).name} — p. {pages_str}")
                        results.append((path_str, found_pages))
                    else:
                        print(f"  [{done}/{len(to_process)}] . {Path(path_str).name} ({page_count} p.)")

                # Progress every 20 files
                if done % 20 == 0 or done == len(to_process):
                    pct = done * 100 // len(to_process)
                    print(f"\n  --- Progress: {done}/{len(to_process)} ({pct}%) | "
                          f"{elapsed:.0f}s | {speed:.1f} f/s | "
                          f"ETA: ~{eta:.0f}s ({eta/60:.1f} min) | "
                          f"Errors: {errors} ---\n")

                # Save cache every 50 files
                if done % 50 == 0:
                    save_cache(cache)
                    print(f"  [CACHE] Saved ({len(cache)} entries)")

        # Final cache save
        save_cache(cache)
        print(f"\n[CACHE] Saved ({len(cache)} entries)")

    elapsed = time.time() - start

    print(f"\n{'='*50}")
    print(f"  RESULTS")
    print(f"{'='*50}")
    if results:
        for pdf_path, pages in sorted(results):
            pages_str = ", ".join(str(p) for p in sorted(pages))
            print(f"  [FOUND] {pdf_path} — p. {pages_str}")
        print(f"\n  Total files with matches: {len(results)}")

        if COPY_RESULTS:
            out = Path(OUTPUT_DIR)
            out.mkdir(exist_ok=True)
            print(f"\n[COPY] Copying to {OUTPUT_DIR}/...")
            for pdf_path, _ in sorted(results):
                src = Path(pdf_path)
                dst = out / src.name
                shutil.copy2(src, dst)
                print(f"  -> {dst}")
            print(f"[COPY] Copied {len(results)} files")
    else:
        print("  No matches found.")

    print(f"\n  Files: {total} (cache: {cached_count}, OCR: {len(to_process)})")
    print(f"  Time: {elapsed:.0f}s ({elapsed/60:.1f} min)")
    if elapsed > 0:
        print(f"  Speed: {total / elapsed:.1f} files/s")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()