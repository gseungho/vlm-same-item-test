"""Fetch candidate ABO photos for the pilot and write numbered contact sheets. No API call.

    python -I fetch_candidates.py <project_dir>

Saves resized photos under data/candidates/ (git-ignored) and a metadata file. The candidates are
drawn per brand with a fixed seed, before any model sees them.
"""

import csv
import gzip
import io
import json
import random
import re
import sys
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw

BASE = "https://amazon-berkeley-objects.s3.amazonaws.com"
TYPES = {"SHOES", "BOOT", "SANDAL", "HANDBAG", "HAT", "BACKPACK", "LUGGAGE"}
# Spellings of one brand, and names that do not read as a brand name.
MERGE = {
    "starter": "Starter", "amazonbasics": "AmazonBasics", "amazon basics": "AmazonBasics",
    "amazonベーシック(amazonbasics)": "AmazonBasics", "amazonbasics licensing": "AmazonBasics",
    "care of by puma": "Care of by Puma", "red wagon": "Red Wagon", "find": "find.",
    "bugatti": "Bugatti", "eono": "Eono", "eono essentials": "Eono", "eono(イオーノ)": "Eono",
    "truth & fable": "Truth & Fable", "umi.": "Umi", "umi": "Umi", "umi.(ウミ)": "Umi",
    "amazon brand - symactive": "Symactive", "brand - symactive": "Symactive",
    "amazon brand - symbol": "Symbol", "amazon brand - inkast denim co.": "Inkast Denim Co.",
    "amazon brand - house & shields": "House & Shields", "amazon brand - eden & ivy": "Eden & Ivy",
    "amazon brand - arthur harvey": "Arthur Harvey", "amazon brand - solimo": "Solimo",
    "sixth + love": "Sixth & Love", "michelsons": "Michelson's", "skechers": "Concept 3 by Skechers",
    "moon & back by hanna andersson": "Moon and Back", "moon and back by hanna andersson": "Moon and Back",
}
EXCLUDE = {"find.", "handbag", "générique", "the fix", "the drop", "jenny", "elise", "mae", "blink",
           "blink-182", "whole foods market", "stanton", "buttoned down"}
PER_BRAND = 24
MIN_LISTINGS = 8


def get(path):
    with urllib.request.urlopen(f"{BASE}/{path}", timeout=120) as reply:
        return reply.read()


def english(values):
    for value in values or []:
        if value.get("language_tag", "").startswith("en"):
            return value.get("value")
    return values[0].get("value") if values else None


def listings():
    rows = []
    for shard in "0123456789abcdef":
        data = gzip.decompress(get(f"listings/metadata/listings_{shard}.json.gz"))
        for line in data.decode("utf-8").splitlines():
            row = json.loads(line)
            kind = (row.get("product_type") or [{}])[0].get("value")
            brand, image = english(row.get("brand")), row.get("main_image_id")
            if kind in TYPES and brand and image:
                key = brand.strip().lower()
                brand = MERGE.get(key, brand.strip())
                if brand.lower() not in EXCLUDE:
                    rows.append({"listing": row["item_id"], "kind": kind, "brand": brand,
                                 "image": image, "name": english(row.get("item_name")) or ""})
    return rows


def draw(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row["brand"]].append(row)
    rng = random.Random(20261102)
    chosen = []
    for brand in sorted(groups):
        members = groups[brand]
        if len(members) < MIN_LISTINGS:
            continue
        # One photo per product style, judged by the name without size and colour words.
        styles = {}
        for row in sorted(members, key=lambda r: r["listing"]):
            style = re.sub(r"[^a-z ]", " ", row["name"].lower())
            styles.setdefault(" ".join(style.split()[:6]), row)
        pool = list(styles.values())
        rng.shuffle(pool)
        chosen += pool[:PER_BRAND]
    return chosen


def fetch(args):
    k, row, meta, out = args
    data = get(f"images/original/{meta['path']}")
    with Image.open(io.BytesIO(data)) as image:
        image = image.convert("RGB")
        image.thumbnail((1000, 1000))
        name = f"c{k:04d}.jpg"
        image.save(out / name, quality=90)
    return {**row, "file": name, "width": image.width, "height": image.height}


def sheets(rows, photos, out, per_sheet=20, cell=330):
    cols = 5
    for start in range(0, len(rows), per_sheet):
        part = rows[start : start + per_sheet]
        lines = (len(part) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cell, lines * (cell + 22)), "white")
        draw_ = ImageDraw.Draw(sheet)
        for k, row in enumerate(part):
            x, y = (k % cols) * cell, (k // cols) * (cell + 22)
            with Image.open(photos / row["file"]) as image:
                image.thumbnail((cell - 8, cell - 8))
                sheet.paste(image, (x + 4, y + 20))
            draw_.text((x + 4, y + 4), f"{row['file'][:-4]} {row['brand'][:30]}", fill="black")
        sheet.save(out / f"sheet{start // per_sheet:02d}.jpg", quality=88)


def main(root):
    sys.stdout.reconfigure(encoding="utf-8")
    root = Path(root)
    photos = root / "data" / "candidates"
    photos.mkdir(parents=True, exist_ok=False)
    rows = listings()
    chosen = draw(rows)
    meta = {
        row["image_id"]: row
        for row in csv.DictReader(
            io.StringIO(gzip.decompress(get("images/metadata/images.csv.gz")).decode("utf-8"))
        )
    }
    jobs = [(k, r, meta[r["image"]], photos) for k, r in enumerate(chosen) if r["image"] in meta]
    with ThreadPoolExecutor(8) as pool:
        saved = list(pool.map(fetch, jobs))
    (root / "data" / "candidates.json").write_text(
        json.dumps(saved, ensure_ascii=False, indent=0), encoding="utf-8"
    )
    sheet_dir = root / "data" / "sheets"
    sheet_dir.mkdir()
    sheets(saved, photos, sheet_dir)
    brands = defaultdict(int)
    for row in saved:
        brands[row["brand"]] += 1
    print("listings after filters", len(rows), "candidates", len(saved), "brands", len(brands))
    print(sorted(brands.items(), key=lambda kv: -kv[1]))
    print("sheets", len(list(sheet_dir.glob("*.jpg"))))


if __name__ == "__main__":
    main(sys.argv[1])
