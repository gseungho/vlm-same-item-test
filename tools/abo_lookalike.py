"""Read-only prototype: can simple image features find same-brand lookalikes? No model call.

For a few brand-and-kind groups, take small main photos, find the nearest different-style photo,
and save a sheet: anchor photo, another photo of the anchor, nearest lookalike.
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

import numpy as np
from PIL import Image, ImageDraw, ImageOps

sys.stdout.reconfigure(encoding="utf-8")
BASE = "https://amazon-berkeley-objects.s3.amazonaws.com"
GROUPS = {("Bourge", "SHOES"), ("Klepe", "SHOES"), ("Flavia", "HANDBAG"), ("AmazonBasics", "BACKPACK"),
          ("Amazon Essentials", "SHOES"), ("206 Collective", "BOOT")}
out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=False)


def get(path):
    with urllib.request.urlopen(f"{BASE}/{path}", timeout=120) as reply:
        return reply.read()


def text(values):
    for value in values or []:
        if value.get("language_tag", "").startswith("en"):
            return value.get("value")
    return values[0].get("value") if values else None


rows = defaultdict(dict)
for shard in "0123456789abcdef":
    for line in gzip.decompress(get(f"listings/metadata/listings_{shard}.json.gz")).decode("utf-8").splitlines():
        r = json.loads(line)
        kind = (r.get("product_type") or [{}])[0].get("value")
        brand = (text(r.get("brand")) or "").strip()
        if (brand, kind) in GROUPS and r.get("main_image_id") and r.get("other_image_id"):
            style = " ".join(re.sub(r"[^a-z ]", " ", (text(r.get("item_name")) or "").lower()).split()[:6])
            rows[(brand, kind)].setdefault(style, r)
meta = {r["image_id"]: r["path"] for r in csv.DictReader(
    io.StringIO(gzip.decompress(get("images/metadata/images.csv.gz")).decode("utf-8")))}


def small(image_id):
    with Image.open(io.BytesIO(get(f"images/small/{meta[image_id]}"))) as im:
        return im.convert("RGB")


def feature(im):
    """Colour histogram plus the outline of the product, after trimming the white background."""
    gray = ImageOps.grayscale(im)
    box = ImageOps.invert(gray).point(lambda v: 255 if v > 20 else 0).getbbox() or (0, 0, *im.size)
    crop = im.crop(box)
    shape = np.asarray(ImageOps.grayscale(crop).resize((24, 24)), dtype=float).ravel() / 255
    hist = np.asarray(crop.resize((48, 48)).convert("HSV").histogram(), dtype=float)
    hist = hist / hist.sum()
    return np.concatenate([shape / np.linalg.norm(shape), 3 * hist / np.linalg.norm(hist)])


rng = random.Random(20261102)
rows_out = []
for key in sorted(rows):
    styles = list(rows[key].values())
    rng.shuffle(styles)
    styles = [r for r in styles if r["main_image_id"] in meta][:40]
    with ThreadPoolExecutor(8) as pool:
        images = list(pool.map(lambda r: small(r["main_image_id"]), styles))
    feats = np.stack([feature(im) for im in images])
    dist = ((feats[:, None] - feats[None]) ** 2).sum(-1)
    np.fill_diagonal(dist, np.inf)
    order = np.argsort(dist.min(1))[:3]
    print(key, "styles available", len(rows[key]), "used", len(styles))
    for i in order:
        j = int(dist[i].argmin())
        other = [x for x in styles[i]["other_image_id"] if x in meta][0]
        rows_out.append((key, images[i], small(other), images[j]))
        print("  ", styles[i]["item_id"], "|", (text(styles[i]["item_name"]) or "")[:60], "||", (text(styles[j]["item_name"]) or "")[:60])

cell = 200
sheet = Image.new("RGB", (cell * 3, (cell + 16) * len(rows_out)), "white")
draw = ImageDraw.Draw(sheet)
for y, (key, a, a2, b) in enumerate(rows_out):
    Y = y * (cell + 16)
    draw.text((2, Y + 1), f"{y} {key[0]} {key[1]}: anchor | same item | lookalike", fill="black")
    for x, im in enumerate((a, a2, b)):
        im = im.copy()
        im.thumbnail((cell - 6, cell - 6))
        sheet.paste(im, (x * cell + 3, Y + 15))
sheet.save(out / "lookalike.jpg", quality=85)
print("saved", out / "lookalike.jpg")
