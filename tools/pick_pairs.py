"""Build candidate photo pairs for the same-item pilot from ABO metadata and small photos. No model call.

    python -I pick_pairs.py <project_dir> pool     # count what is usable and write data/pairs/pool.json
    python -I pick_pairs.py <project_dir> sheets   # draw anchors, find lookalikes, write review sheets
    python -I pick_pairs.py <project_dir> more     # draw more anchors from brands the first round left short
    python -I pick_pairs.py <project_dir> shortlist  # merge the agent's choices and fetch those photos at 1000 px
    python -I pick_pairs.py <project_dir> rescue     # list replacement photos and unchecked sets for a last check
    python -I pick_pairs.py <project_dir> final      # merge every check, apply the brand cap, write the review page

A product here is a group of listings joined by a shared photo, so sizes and other-language listings
of one product stay together. Lookalikes come from the same brand and kind but another product.
"""

import csv
import gzip
import html
import io
import json
import random
import re
import sys
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_candidates import EXCLUDE, MERGE  # noqa: E402

BASE = "https://amazon-berkeley-objects.s3.amazonaws.com"
SEED = 20261102
KINDS = {"SHOES", "BOOT", "SANDAL", "HANDBAG", "BACKPACK", "LUGGAGE"}
# Names that carry a famous word, so they cannot stand for an unknown brand (spec section 4).
NOT_UNKNOWN = {"amazon essentials", "amazonbasics", "care of by puma", "concept 3 by skechers",
               "simple joys by carter's", "bugatti", "amazon gear", "amazon basics", "starter"}
ANCHORS_TO_DRAW = {"SHOES": 100, "BOOT": 25, "SANDAL": 25, "HANDBAG": 30, "BACKPACK": 12, "LUGGAGE": 12}
BRAND_KIND_DRAW_CAP = 25
LOOKALIKES = 4
PHOTOS_PER_ROW = 6
MIN_PRODUCTS = 5
# Second round. Logos removed most of some brands, so these are drawn again to meet the cap of 10 per brand.
MORE_ANCHORS = {"Arthur Harvey": 8, "Nubeno": 8, "Inkast Denim Co.": 8, "House & Shields": 8, "Chadstone": 8,
                "Solefit": 8, "Eden & Ivy": 8, "Nia & Nicole": 8, "Teen Mix By Catwalk": 8, "Sixth & Love": 8,
                "Burwood": 8, "Acteo": 8, "Fusefit": 8, "Centrino": 6, "Franklin & Freeman": 4,
                "SOCIETY NEW YORK": 4}


# Lookalikes the agent flagged as the same base shape with only an ornament changed. The spec bars the same mould.
SAME_BASE_SHEETS = {"s257", "s263", "s268", "s282"}
# Above the final cap of 10 per brand, so a photo rejected at 1000 px can be replaced without new draws.
BRAND_CHECK_CAP = 13
FINAL_BRAND_CAP = 10
PAGE_STYLE = """
:root { --ink: #1f2328; --muted: #5d6670; --line: #d8dde3; --surface: #ffffff; --page: #f6f7f8; }
@media (prefers-color-scheme: dark) {
  :root { --ink: #e8eaed; --muted: #a3acb6; --line: #3a4048; --surface: #22262b; --page: #16191c; }
}
* { box-sizing: border-box; }
body { margin: 0; padding: 24px 16px 64px; background: var(--page); color: var(--ink);
       font: 15px/1.6 "Malgun Gothic", system-ui, sans-serif; }
main { max-width: 1100px; margin: 0 auto; }
h1 { font-size: 24px; margin: 0 0 8px; }
p { margin: 0 0 16px; color: var(--muted); max-width: 72ch; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 12px; margin-top: 12px; }
h2 { font-size: 16px; margin: 0 0 8px; }
small { font-weight: 400; color: var(--muted); }
.row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
figure { margin: 0; }
figure a { display: block; background: #fff; border-radius: 4px; }
img { display: block; width: 100%; height: 280px; object-fit: contain; }
figcaption { margin-top: 4px; font-size: 13px; color: var(--muted); text-align: center; }
@media (max-width: 640px) { img { height: 150px; } }
"""
# Unchecked sets to check in the last round, from brands still under the cap. Boots and sandals come first
# because the checked sample has few boots and no sandals.
RESERVE_TO_CHECK = {("206 Collective", "BOOT"): 8, ("206 Collective", "SANDAL"): 6, ("Symbol", "SHOES"): 4,
                    ("Flavia", "HANDBAG"): 1, ("Flavia", "SHOES"): 1}


def get(path):
    with urllib.request.urlopen(f"{BASE}/{path}", timeout=120) as reply:
        return reply.read()


def text(values):
    for value in values or []:
        if value.get("language_tag", "").startswith("en"):
            return value.get("value")
    return values[0].get("value") if values else None


def canonical_brand(raw):
    brand = MERGE.get(raw.strip().lower(), raw.strip())
    return re.sub(r"^(amazon )?brand\s*-\s*", "", brand, flags=re.I).strip()


def read_listings():
    rows = {}
    for shard in "0123456789abcdef":
        data = gzip.decompress(get(f"listings/metadata/listings_{shard}.json.gz"))
        for line in data.decode("utf-8").splitlines():
            row = json.loads(line)
            kind = (row.get("product_type") or [{}])[0].get("value")
            raw = text(row.get("brand"))
            if kind not in KINDS or not raw or not row.get("main_image_id") or not row.get("other_image_id"):
                continue
            brand = canonical_brand(raw)
            if brand.lower() in EXCLUDE or brand.lower() in NOT_UNKNOWN:
                continue
            rows[row["item_id"]] = {
                "listing": row["item_id"], "kind": kind, "brand": brand, "name": text(row.get("item_name")) or "",
                "colour": text(row.get("color")) or "", "main": row["main_image_id"],
                "photos": [row["main_image_id"], *row["other_image_id"]],
            }
    return rows


def group_products(rows):
    """Join listings that share a photo. Each group is treated as one product."""
    parent = {key: key for key in rows}

    def find(key):
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    by_photo = defaultdict(list)
    for key, row in rows.items():
        for photo in row["photos"]:
            by_photo[photo].append(key)
    for members in by_photo.values():
        for other in members[1:]:
            parent[find(other)] = find(members[0])
    groups = defaultdict(list)
    for key in sorted(rows):
        groups[find(key)].append(rows[key])
    products = []
    for members in groups.values():
        # Keep the listing with the most photos as the face of the product.
        face = max(members, key=lambda r: (len(r["photos"]), r["listing"]))
        words = " ".join(r["name"] for r in members)
        products.append({**face, "listings": sorted(r["listing"] for r in members), "all_names": words,
                         "brands_in_group": sorted({r["brand"] for r in members})})
    return products


def write_pool(root):
    rows = read_listings()
    products = [p for p in group_products(rows) if len(p["brands_in_group"]) == 1]
    counts = Counter((p["brand"], p["kind"]) for p in products)
    usable = {key for key, count in counts.items() if count >= MIN_PRODUCTS}
    pool = [p for p in products if (p["brand"], p["kind"]) in usable]
    out = root / "data" / "pairs"
    out.mkdir(parents=True, exist_ok=True)
    (out / "pool.json").write_text(json.dumps(pool, ensure_ascii=False), encoding="utf-8")
    print("listings", len(rows), "| products", len(products), "| in usable groups", len(pool))
    print("by kind", Counter(p["kind"] for p in pool).most_common())
    by_brand = defaultdict(Counter)
    for p in pool:
        by_brand[p["brand"]][p["kind"]] += 1
    for brand, kinds in sorted(by_brand.items(), key=lambda kv: -sum(kv[1].values())):
        print(f"  {brand}: {sum(kinds.values())} {dict(kinds)}")


GENERIC = set("""amazon brand marke marque marca women womens men mens girl girls boy boys kids kid unisex adult
child children shoes shoe sneaker sneakers sandal sandals boot boots backpack bag bags handbag luggage suitcase
for with and the de para pour en von mit und with size color colour black white blue red green grey gray brown navy
beige pink tan taupe gold silver yellow orange purple multicolor multicolour running sports casual formal
leather fashion sneakers uk us eu""".split())


def name_words(product):
    words = re.findall(r"[a-z0-9][a-z0-9\-]{2,}", product["all_names"].lower())
    return {w for w in words if w not in GENERIC and not w.isdigit()}


def model_words_by_listing(members):
    """Keep the words that few products of a group use. Those name a model; the rest name the brand or type."""
    counts = Counter(word for product in members for word in name_words(product))
    limit = max(3, len(members) // 50)
    return {p["listing"]: {w for w in name_words(p) if counts[w] <= limit} for p in members}


def small_path(root, photo):
    return root / "data" / "pairs" / "small" / f"{photo}.jpg"


def fetch_small(args):
    root, photo, paths = args
    target = small_path(root, photo)
    if target.exists():
        return photo, True
    if photo not in paths:
        return photo, False
    try:
        target.write_bytes(get(f"images/small/{paths[photo]}"))
    except OSError:
        return photo, False
    return photo, True


def features(path):
    """Colour histogram and outline, after trimming the white background."""
    with Image.open(path) as image:
        image = image.convert("RGB")
    gray = ImageOps.grayscale(image)
    box = ImageOps.invert(gray).point(lambda v: 255 if v > 20 else 0).getbbox() or (0, 0, *image.size)
    crop = image.crop(box)
    outline = np.asarray(ImageOps.grayscale(crop).resize((24, 24)), dtype=float).ravel() / 255
    hist = np.asarray(crop.resize((48, 48)).convert("HSV").histogram(), dtype=float)
    return outline / np.linalg.norm(outline), hist / np.linalg.norm(hist)


def draw_anchors(pool):
    rng = random.Random(SEED)
    order = sorted(pool, key=lambda p: p["listing"])
    rng.shuffle(order)
    used = Counter()
    want = Counter(ANCHORS_TO_DRAW)
    anchors = []
    for product in order:
        kind, brand = product["kind"], product["brand"]
        if want[kind] > 0 and used[brand, kind] < BRAND_KIND_DRAW_CAP:
            anchors.append(product)
            want[kind] -= 1
            used[brand, kind] += 1
    return anchors, want


def draw_more(pool, seen):
    rng = random.Random(SEED + 1)
    order = sorted((p for p in pool if p["listing"] not in seen), key=lambda p: p["listing"])
    rng.shuffle(order)
    want = Counter(MORE_ANCHORS)
    anchors = []
    for product in order:
        if want[product["brand"]] > 0:
            anchors.append(product)
            want[product["brand"]] -= 1
    return anchors, want


def build_sheets(root, more=False):
    out = root / "data" / "pairs"
    pool = json.loads((out / "pool.json").read_text(encoding="utf-8"))
    pool = [p for p in pool if p["brand"].lower() not in NOT_UNKNOWN]
    (out / "small").mkdir(exist_ok=True)
    sheet_dir = out / "sheets"
    sheet_dir.mkdir(exist_ok=more)
    earlier = json.loads((out / "sheet_index.json").read_text(encoding="utf-8")) if more else []
    paths = {r["image_id"]: r["path"] for r in csv.DictReader(
        io.StringIO(gzip.decompress(get("images/metadata/images.csv.gz")).decode("utf-8")))}
    if more:
        anchors, short = draw_more(pool, {sheet["rows"][0]["listing"] for sheet in earlier})
    else:
        anchors, short = draw_anchors(pool)
    print("anchors drawn", len(anchors), "| unmet", {k: v for k, v in short.items() if v > 0})
    print("by brand", Counter(a["brand"] for a in anchors).most_common())

    groups = defaultdict(list)
    for product in pool:
        groups[(product["brand"], product["kind"])].append(product)
    needed = {p["main"] for members in groups.values() for p in members
              if (members[0]["brand"], members[0]["kind"]) in {(a["brand"], a["kind"]) for a in anchors}}
    with ThreadPoolExecutor(16) as executor:
        got = dict(executor.map(fetch_small, [(root, photo, paths) for photo in sorted(needed)]))
    print("main photos", len(needed), "| fetched", sum(got.values()))

    feats = {}
    for photo, ok in got.items():
        if ok:
            try:
                feats[photo] = features(small_path(root, photo))
            except OSError:
                pass

    model_words = {}
    for members in groups.values():
        model_words.update(model_words_by_listing(members))

    picks = []
    for anchor in anchors:
        if anchor["main"] not in feats:
            continue
        shape_a, hist_a = feats[anchor["main"]]
        tokens_a = model_words[anchor["listing"]]
        scored = []
        for other in groups[(anchor["brand"], anchor["kind"])]:
            if other["listing"] == anchor["listing"] or other["main"] not in feats:
                continue
            if tokens_a & model_words[other["listing"]]:
                continue  # shares a model word, so likely the same model in another colour or language
            shape_b, hist_b = feats[other["main"]]
            scored.append((float(np.sum((shape_a - shape_b) ** 2) + 3 * np.sum((hist_a - hist_b) ** 2)), other))
        scored.sort(key=lambda item: (item[0], item[1]["listing"]))
        picks.append({"anchor": anchor, "lookalikes": [item[1] for item in scored[:LOOKALIKES]]})

    photos = {photo for pick in picks for product in [pick["anchor"], *pick["lookalikes"]]
              for photo in product["photos"][:PHOTOS_PER_ROW]}
    with ThreadPoolExecutor(16) as executor:
        got = dict(executor.map(fetch_small, [(root, photo, paths) for photo in sorted(photos)]))
    print("sheet photos", len(photos), "| fetched", sum(got.values()))

    index = list(earlier)
    for number, pick in enumerate(picks, start=len(earlier)):
        rows = [pick["anchor"], *pick["lookalikes"]]
        name = f"s{number:03d}"
        draw_sheet(root, sheet_dir / f"{name}.jpg", name, rows, got)
        index.append({
            "sheet": name, "kind": pick["anchor"]["kind"], "brand": pick["anchor"]["brand"],
            "rows": [{"listing": r["listing"], "name": r["name"][:80], "colour": r["colour"],
                      "photos": [p for p in r["photos"][:PHOTOS_PER_ROW] if got.get(p)]} for r in rows],
        })
    (out / "sheet_index.json").write_text(json.dumps(index, ensure_ascii=False, indent=0), encoding="utf-8")
    print("sheets", len(index), "| new", len(picks), "| without a lookalike", sum(not p["lookalikes"] for p in picks))
    print("by kind", Counter(i["kind"] for i in index[len(earlier):]).most_common())


def draw_sheet(root, target, name, rows, got):
    cell, label = 170, 16
    sheet = Image.new("RGB", (cell * PHOTOS_PER_ROW + 40, (cell + label) * len(rows)), "white")
    draw = ImageDraw.Draw(sheet)
    for y, row in enumerate(rows):
        tag = "A" if y == 0 else f"C{y}"
        top = y * (cell + label)
        draw.text((2, top + 2), f"{name} {tag} {row['brand'][:20]} {row['listing']}", fill="black")
        for x, photo in enumerate(row["photos"][:PHOTOS_PER_ROW]):
            left = 40 + x * cell
            if got.get(photo):
                with Image.open(small_path(root, photo)) as image:
                    image = image.convert("RGB")
                    image.thumbnail((cell - 6, cell - 6))
                    sheet.paste(image, (left + 3, top + label))
                draw.text((left + 3, top + label), str(x), fill="red")
    sheet.save(target, quality=85)


def fetch_photo(args):
    root, photo, paths = args
    target = root / "data" / "pairs" / "photos" / f"{photo}.jpg"
    if target.exists():
        return photo, True
    with Image.open(io.BytesIO(get(f"images/original/{paths[photo]}"))) as image:
        image = image.convert("RGB")
        image.thumbnail((1000, 1000))
        image.save(target, quality=90)
    return photo, True


def shortlist(root):
    """Keep the agent's sets per brand up to the check cap: closer lookalikes first, then sheet order."""
    out = root / "data" / "pairs"
    index = {s["sheet"]: s for s in json.loads((out / "sheet_index.json").read_text(encoding="utf-8"))}
    choices = [c for f in sorted(out.glob("pass1_*.json"))
               for c in json.loads(f.read_text(encoding="utf-8")) if c.get("use")]
    rank = {"close": 0, "medium": 1, "far": 2}
    choices = [c for c in choices if c["sheet"] not in SAME_BASE_SHEETS]
    choices.sort(key=lambda c: (rank[c["closeness"]], c["sheet"]))
    used = Counter()
    kept = []
    for choice in choices:
        sheet = index[choice["sheet"]]
        if used[sheet["brand"]] >= BRAND_CHECK_CAP:
            continue
        used[sheet["brand"]] += 1
        anchor, other = sheet["rows"][0], sheet["rows"][choice["c_row"]]
        kept.append({
            "sheet": choice["sheet"], "kind": sheet["kind"], "brand": sheet["brand"],
            "listing": anchor["listing"], "other_listing": other["listing"],
            "a1": anchor["photos"][choice["a1"]], "a2": anchor["photos"][choice["a2"]], "c": other["photos"][choice["c"]],
            "views": choice["views"], "closeness": choice["closeness"], "note": choice.get("note", ""),
        })
    kept.sort(key=lambda k: k["sheet"])
    (out / "shortlist.json").write_text(json.dumps(kept, ensure_ascii=False, indent=0), encoding="utf-8")
    print("agent sets", len(choices), "| kept", len(kept))
    print("kind", Counter(k["kind"] for k in kept).most_common())
    print("closeness", Counter(k["closeness"] for k in kept).most_common())
    print("brand", Counter(k["brand"] for k in kept).most_common())
    (out / "photos").mkdir(exist_ok=True)
    paths = {r["image_id"]: r["path"] for r in csv.DictReader(
        io.StringIO(gzip.decompress(get("images/metadata/images.csv.gz")).decode("utf-8")))}
    photos = sorted({k[slot] for k in kept for slot in ("a1", "a2", "c")})
    with ThreadPoolExecutor(8) as executor:
        got = dict(executor.map(fetch_photo, [(root, photo, paths) for photo in photos]))
    print("photos", len(photos), "| fetched", sum(got.values()))


def rescue(root):
    """List sets rejected for a mark on one photo, with other photos for that slot, and unchecked sets with room."""
    out = root / "data" / "pairs"
    index = {s["sheet"]: s for s in json.loads((out / "sheet_index.json").read_text(encoding="utf-8"))}
    short = {k["sheet"]: k for k in json.loads((out / "shortlist.json").read_text(encoding="utf-8"))}
    results = [r for f in sorted(out.glob("pass2_part*.json")) for r in json.loads(f.read_text(encoding="utf-8"))]
    lines, photos = [], set()
    for result in results:
        flagged = [slot for slot, text_ in result["marks"].items() if text_]
        if result["ok"] or result["failed"] != [1] or len(flagged) != 1:
            continue
        slot, chosen = flagged[0], short[result["sheet"]]
        rows = {r["listing"]: r for r in index[result["sheet"]]["rows"]}
        row = rows[chosen["other_listing"]] if slot == "c" else rows[chosen["listing"]]
        taken = {chosen["a1"], chosen["a2"], chosen["c"]}
        others = [photo for photo in row["photos"] if photo not in taken]
        if others:
            kept = [f"{name}={chosen[name]}" for name in ("a1", "a2", "c") if name != slot]
            lines.append(f"{result['sheet']} replace={slot} rejected={chosen[slot]} {' '.join(kept)} options={','.join(others)}")
            photos.update(others)
    half = (len(lines) + 1) // 2
    (out / "rescue_part1.txt").write_text("".join(line + "\n" for line in lines[:half]), encoding="utf-8")
    (out / "rescue_part2.txt").write_text("".join(line + "\n" for line in lines[half:]), encoding="utf-8")

    rank = {"close": 0, "medium": 1, "far": 2}
    choices = [c for f in sorted(out.glob("pass1_*.json")) for c in json.loads(f.read_text(encoding="utf-8")) if c.get("use")]
    unchecked = sorted((c for c in choices if c["sheet"] not in short and c["sheet"] not in SAME_BASE_SHEETS),
                       key=lambda c: (rank[c["closeness"]], c["sheet"]))
    want = Counter(RESERVE_TO_CHECK)
    extra = []
    for choice in unchecked:
        sheet = index[choice["sheet"]]
        if want[sheet["brand"], sheet["kind"]] > 0:
            want[sheet["brand"], sheet["kind"]] -= 1
            anchor, other = sheet["rows"][0], sheet["rows"][choice["c_row"]]
            item = {"sheet": choice["sheet"], "kind": sheet["kind"], "brand": sheet["brand"],
                    "listing": anchor["listing"], "other_listing": other["listing"],
                    "a1": anchor["photos"][choice["a1"]], "a2": anchor["photos"][choice["a2"]],
                    "c": other["photos"][choice["c"]], "views": choice["views"], "closeness": choice["closeness"],
                    "note": choice.get("note", "")}
            extra.append(item)
            photos.update({item["a1"], item["a2"], item["c"]})
    (out / "shortlist_extra.json").write_text(json.dumps(extra, ensure_ascii=False, indent=0), encoding="utf-8")
    (out / "check_part4.txt").write_text(
        "".join(f"{x['sheet']} a1={x['a1']} a2={x['a2']} c={x['c']}\n" for x in extra), encoding="utf-8")
    print("rescue sets", len(lines), "| extra sets", len(extra), Counter((x["brand"], x["kind"]) for x in extra).most_common())
    paths = {r["image_id"]: r["path"] for r in csv.DictReader(
        io.StringIO(gzip.decompress(get("images/metadata/images.csv.gz")).decode("utf-8")))}
    with ThreadPoolExecutor(8) as executor:
        got = dict(executor.map(fetch_photo, [(root, photo, paths) for photo in sorted(photos)]))
    print("photos", len(photos), "| fetched", sum(got.values()))


def final_sets(root):
    """Merge the 1000 px checks and photo replacements, then keep at most FINAL_BRAND_CAP sets per brand."""
    out = root / "data" / "pairs"
    items = {k["sheet"]: k for name in ("shortlist.json", "shortlist_extra.json")
             for k in json.loads((out / name).read_text(encoding="utf-8"))}
    sets = {}
    for f in sorted(out.glob("pass2_part*.json")):
        for result in json.loads(f.read_text(encoding="utf-8")):
            if result["ok"]:
                sets[result["sheet"]] = {**items[result["sheet"]], "check_note": result.get("note", "")}
    replaced = []
    for f in sorted(out.glob("pass3_part*.json")):
        for result in json.loads(f.read_text(encoding="utf-8")):
            if result["ok"]:
                item = {**items[result["sheet"]], "check_note": result.get("note", ""), "views": result["views"]}
                item[result["slot"]] = result["photo"]
                sets[result["sheet"]] = item
                replaced.append(result["sheet"])
    rank = {"close": 0, "medium": 1, "far": 2}
    used = Counter()
    kept = []
    for item in sorted(sets.values(), key=lambda k: (rank[k["closeness"]], k["sheet"])):
        if used[item["brand"]] < FINAL_BRAND_CAP:
            used[item["brand"]] += 1
            kept.append(item)
    kept.sort(key=lambda k: k["sheet"])
    for number, item in enumerate(kept, start=1):
        item["pair_id"] = f"p{number:03d}"
    (out / "sets.json").write_text(json.dumps(kept, ensure_ascii=False, indent=0), encoding="utf-8")
    print("passed", len(sets), "| replaced", len(replaced), "| kept", len(kept))
    print("kind", Counter(k["kind"] for k in kept).most_common())
    print("brand", Counter(k["brand"] for k in kept).most_common())
    print("closeness", Counter(k["closeness"] for k in kept).most_common())
    print("a2 view equals c view", sum(k["views"]["a2"] == k["views"]["c"] for k in kept), "of", len(kept))
    photos = Counter(k[slot] for k in kept for slot in ("a1", "a2", "c"))
    print("photos", len(photos), "| used more than once", sum(v > 1 for v in photos.values()))
    anchors = {k["listing"] for k in kept}
    print("anchor products also used as a lookalike", len(anchors & {k["other_listing"] for k in kept}))
    missing = [p for p in photos if not (out / "photos" / f"{p}.jpg").exists()]
    assert not missing, missing
    write_review_page(out, kept)


def write_review_page(out, kept):
    def figure(photo, label):
        return (f'<figure><a href="../photos/{photo}.jpg" target="_blank">'
                f'<img loading="lazy" src="../photos/{photo}.jpg" alt="{label}"></a><figcaption>{label}</figcaption></figure>')

    cards = "".join(
        f'<section class="card"><h2>{html.escape(k["pair_id"])} <small>{html.escape(k["brand"])} · {html.escape(k["kind"])}</small></h2>'
        f'<div class="row">{figure(k["a2"], "같은 물건이어야 함")}{figure(k["a1"], "기준")}{figure(k["c"], "다른 물건이어야 함")}</div></section>'
        for k in kept)
    page = (
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>사진 쌍 확인</title><style>{PAGE_STYLE}</style></head><body><main>"
        f"<h1>사진 쌍 확인 ({len(kept)}개)</h1>"
        "<p>가운데가 기준 사진입니다. 세 가지를 봐 주세요. 왼쪽이 기준과 같은 물건인가, 오른쪽이 기준과 모양이 다른 물건인가"
        "(색만 다른 것은 안 됩니다), 세 사진 어디에도 브랜드 글자나 로고가 보이지 않는가. 사진을 누르면 모델이 볼 크기"
        "(긴 변 1000픽셀)로 열립니다. 하나라도 아니면 번호(p001 등)만 알려 주세요. 그 번호는 통째로 뺍니다. "
        "사진 출처: Amazon Berkeley Objects (CC BY 4.0).</p>" + cards + "</main></body></html>"
    )
    (out / "review").mkdir(exist_ok=True)
    (out / "review" / "index.html").write_text(page, encoding="utf-8")
    print("wrote", out / "review" / "index.html")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    root, command = Path(sys.argv[1]), sys.argv[2]
    if command == "pool":
        write_pool(root)
    elif command == "sheets":
        build_sheets(root)
    elif command == "more":
        build_sheets(root, more=True)
    elif command == "shortlist":
        shortlist(root)
    elif command == "rescue":
        rescue(root)
    elif command == "final":
        final_sets(root)
    else:
        raise SystemExit("usage: pick_pairs.py <project_dir> pool|sheets|more|shortlist|rescue|final")


if __name__ == "__main__":
    main()
