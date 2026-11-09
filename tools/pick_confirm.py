"""Candidate sheets for the confirmation run (spec 2026-11-04 section 3). No model call.

    python -I pick_confirm.py <project_dir> fashion     # new fashion anchors and lookalikes, without pilot products
    python -I pick_confirm.py <project_dir> furniture   # furniture anchors from 360-degree spins
    python -I pick_confirm.py <project_dir> shortlist fashion|furniture   # agent choices, 1000 px photos, check lists
    python -I pick_confirm.py <project_dir> final fashion|furniture       # 1000 px checks to sets.json
    python -I pick_confirm.py <project_dir> review      # one page for the user with both samples

Photos share the pilot's caches: thumbnails in data/pairs/small, 1000 px photos in data/pairs/photos,
keyed by ABO image id (spin frames have their own image ids). Sheets and indexes go to data/confirm/<domain>/.
"""

import csv
import html
import gzip
import io
import json
import random
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_candidates import EXCLUDE  # noqa: E402
from pick_pairs import (  # noqa: E402
    LOOKALIKES, NOT_UNKNOWN, PAGE_STYLE, canonical_brand, draw_sheet, features, fetch_small, get, group_products,
    model_words_by_listing, small_path, text,
)

SEED = 20261104
DRAW_CAP = 20  # per (brand, kind) when drawing anchors, above the final cap of 10 so rejected sets can be replaced
FASHION_DRAW = {"SHOES": 220, "HANDBAG": 60, "BOOT": 29}
FURNITURE_DRAW = {"CHAIR": 50, "SOFA": 30, "TABLE": 30, "LAMP": 20, "LIGHT_FIXTURE": 10, "OTTOMAN": 10,
                  "STOOL_SEATING": 10}
FRAMES = (0, 9, 18)  # spin frame numbers: 0, 45 and 90 degrees (5 degrees per frame)
# Spec section 3: kind targets. A fashion kind that falls short is filled with shoes; furniture is not filled.
TARGETS = {"fashion": {"SHOES": 55, "HANDBAG": 15, "BOOT": 10},
           "furniture": {"CHAIR": 25, "SOFA": 15, "TABLE": 15, "LAMP": 10, "LIGHT_FIXTURE": 5, "OTTOMAN": 5,
                         "STOOL_SEATING": 5}}
CHECK_CAP = 13  # sets per cap group sent to the 1000 px check, above the final cap so rejections can be absorbed
FINAL_CAP = 10  # per brand for fashion, per (brand, kind) for furniture
# Sheets where the agent took a C row of another kind of item because no row matched, or said its choice
# stretched "same kind" (agent notes, pass 1). The other two furniture agents rejected such sheets.
OTHER_KIND = {"h114", "h117", "h119", "h124", "h136", "h140", "h142", "h145", "h146", "h153",
              "h000", "h026", "h105",
              "f264",  # kids ballet flat paired with a sandal
              "f296"}  # a single-shoe view paired with a pair view, so the angles do not match
RANK = {"close": 0, "medium": 1, "far": 2}
CHECK_LINES = 45  # sets per check list, one list per agent


def draw(pool, want):
    rng = random.Random(SEED)
    order = sorted(pool, key=lambda p: p["listing"])
    rng.shuffle(order)
    left, used, anchors = Counter(want), Counter(), []
    for product in order:
        kind, brand = product["kind"], product["brand"]
        if left[kind] > 0 and used[brand, kind] < DRAW_CAP:
            anchors.append(product)
            left[kind] -= 1
            used[brand, kind] += 1
    return anchors, {k: v for k, v in left.items() if v > 0}


def pick_lookalikes(anchors, groups, feats, face):
    """Closest products of the same brand and kind by outline and colour, skipping shared model words."""
    words = {}
    for members in groups.values():
        words.update(model_words_by_listing(members))
    picks = []
    for anchor in anchors:
        if face(anchor) not in feats:
            continue
        shape_a, hist_a = feats[face(anchor)]
        scored = []
        for other in groups[anchor["brand"], anchor["kind"]]:
            if other["listing"] == anchor["listing"] or face(other) not in feats:
                continue
            if words[anchor["listing"]] & words[other["listing"]]:
                continue
            shape_b, hist_b = feats[face(other)]
            scored.append((float(np.sum((shape_a - shape_b) ** 2) + 3 * np.sum((hist_a - hist_b) ** 2)), other))
        scored.sort(key=lambda item: (item[0], item[1]["listing"]))
        picks.append({"anchor": anchor, "lookalikes": [item[1] for item in scored[:LOOKALIKES]]})
    return picks


def write_sheets(root, out, picks, got, per_row, prefix):
    sheet_dir = out / "sheets"
    sheet_dir.mkdir(parents=True, exist_ok=True)
    index = []
    for number, pick in enumerate(picks):
        rows = [{**r, "photos": r["photos"][:per_row]} for r in [pick["anchor"], *pick["lookalikes"]]]
        name = f"{prefix}{number:03d}"
        draw_sheet(root, sheet_dir / f"{name}.jpg", name, rows, got)
        index.append({"sheet": name, "kind": pick["anchor"]["kind"], "brand": pick["anchor"]["brand"],
                      "rows": [{"listing": r["listing"], "name": r["name"][:80], "colour": r.get("colour", ""),
                                # Positions match the red numbers on the sheet; a photo that failed to load is None.
                                "photos": [p if got.get(p) else None for p in r["photos"]]} for r in rows]})
    (out / "sheet_index.json").write_text(json.dumps(index, ensure_ascii=False, indent=0), encoding="utf-8")
    print("sheets", len(index), "| without a lookalike", sum(not p["lookalikes"] for p in picks))
    print("by kind", Counter(i["kind"] for i in index).most_common())
    print("by brand", Counter(i["brand"] for i in index).most_common())


def image_paths(root):
    data = gzip.decompress((root / "data/abo/images.csv.gz").read_bytes()).decode("utf-8")
    return {r["image_id"]: r["path"] for r in csv.DictReader(io.StringIO(data))}


def fashion(root):
    out = root / "data" / "confirm" / "fashion"
    pool = [p for p in json.loads((root / "data/pairs/pool.json").read_text(encoding="utf-8"))
            if p["brand"].lower() not in NOT_UNKNOWN]
    pilot = json.loads((root / "data/pairs/sets.json").read_text(encoding="utf-8"))
    seen_listings = {s["listing"] for s in pilot} | {s["other_listing"] for s in pilot}
    seen_photos = {s[k] for s in pilot for k in ("a1", "a2", "c")}
    pool = [p for p in pool if not set(p["listings"]) & seen_listings and not set(p["photos"]) & seen_photos]
    anchors, short = draw(pool, FASHION_DRAW)
    print("pool without pilot products", len(pool), "| anchors", len(anchors), "| unmet", short)
    groups = defaultdict(list)
    for product in pool:
        groups[product["brand"], product["kind"]].append(product)
    paths = image_paths(root)
    keys = {(a["brand"], a["kind"]) for a in anchors}
    needed = sorted({p["main"] for key in keys for p in groups[key]})
    with ThreadPoolExecutor(16) as executor:
        got = dict(executor.map(fetch_small, [(root, photo, paths) for photo in needed]))
    feats = {photo: features(small_path(root, photo)) for photo, ok in got.items() if ok}
    picks = pick_lookalikes(anchors, groups, feats, lambda p: p["main"])
    photos = sorted({photo for pick in picks for r in [pick["anchor"], *pick["lookalikes"]] for photo in r["photos"][:6]})
    with ThreadPoolExecutor(16) as executor:
        got = dict(executor.map(fetch_small, [(root, photo, paths) for photo in photos]))
    write_sheets(root, out, picks, got, per_row=6, prefix="f")


def fetch_spin_small(args):
    root, image_id, path = args
    target = small_path(root, image_id)
    if target.exists():
        return image_id, True
    try:
        with Image.open(io.BytesIO(get(f"spins/original/{path}"))) as image:
            image = image.convert("RGB")
            image.thumbnail((256, 256))
            image.save(target, quality=90)
    except OSError:
        return image_id, False
    return image_id, True


def furniture_pool(root):
    """Single-brand products of the spec's types that have a spin with frames 0, 9 and 18."""
    frames = defaultdict(dict)
    data = gzip.decompress((root / "data/abo/spins.csv.gz").read_bytes()).decode()
    for r in csv.DictReader(io.StringIO(data)):
        if int(r["azimuth"]) in FRAMES:
            frames[r["spin_id"]][int(r["azimuth"])] = (r["image_id"], r["path"])
    rows = {}
    for f in sorted((root / "data/abo").glob("listings_*.json.gz")):
        for line in gzip.decompress(f.read_bytes()).decode("utf-8").splitlines():
            r = json.loads(line)
            kind = (r.get("product_type") or [{}])[0].get("value")
            raw = text(r.get("brand"))
            spin = r.get("spin_id")
            if kind not in FURNITURE_DRAW or not raw or not r.get("main_image_id") or len(frames.get(spin, {})) < 3:
                continue
            brand = canonical_brand(raw)
            low = brand.lower()
            if low in EXCLUDE or low in NOT_UNKNOWN or "amazon" in low:
                continue
            rows[r["item_id"]] = {"listing": r["item_id"], "kind": kind, "brand": brand,
                                  "name": text(r.get("item_name")) or "", "colour": text(r.get("color")) or "",
                                  "main": r["main_image_id"], "photos": [r["main_image_id"], *(r.get("other_image_id") or [])],
                                  "spin": spin}
    products = []
    for product in group_products(rows):
        if len(product["brands_in_group"]) != 1:
            continue
        spin = frames[product["spin"]]
        products.append({**product, "photos": [spin[a][0] for a in FRAMES], "spin_paths": [spin[a][1] for a in FRAMES]})
    counts = Counter((p["brand"], p["kind"]) for p in products)
    return [p for p in products if counts[p["brand"], p["kind"]] >= 5]


def furniture(root):
    out = root / "data" / "confirm" / "furniture"
    pool = furniture_pool(root)
    print("furniture pool", len(pool), Counter(p["kind"] for p in pool).most_common())
    anchors, short = draw(pool, FURNITURE_DRAW)
    print("anchors", len(anchors), "| unmet", short)
    groups = defaultdict(list)
    for product in pool:
        groups[product["brand"], product["kind"]].append(product)
    keys = {(a["brand"], a["kind"]) for a in anchors}
    # Lookalikes are scored on the 45 degree frame, the angle of a2 and c.
    jobs = [(root, p["photos"][1], p["spin_paths"][1]) for key in keys for p in groups[key]]
    with ThreadPoolExecutor(16) as executor:
        got = dict(executor.map(fetch_spin_small, jobs))
    feats = {photo: features(small_path(root, photo)) for photo, ok in got.items() if ok}
    picks = pick_lookalikes(anchors, groups, feats, lambda p: p["photos"][1])
    jobs = {(root, photo, path) for pick in picks for r in [pick["anchor"], *pick["lookalikes"]]
            for photo, path in zip(r["photos"], r["spin_paths"], strict=True)}
    with ThreadPoolExecutor(16) as executor:
        got = dict(executor.map(fetch_spin_small, sorted(jobs)))
    write_sheets(root, out, picks, got, per_row=3, prefix="h")
    spins = {p["photos"][i]: p["spin_paths"][i] for p in pool for i in range(len(FRAMES))}
    (out / "spin_paths.json").write_text(json.dumps(spins), encoding="utf-8")


def cap_group(domain, item):
    return item["brand"] if domain == "fashion" else (item["brand"], item["kind"])


def fetch_large(args):
    root, photo, path = args
    target = root / "data" / "pairs" / "photos" / f"{photo}.jpg"
    if target.exists():
        return photo, True
    try:
        with Image.open(io.BytesIO(get(path))) as image:
            image = image.convert("RGB")
            image.thumbnail((1000, 1000))
            image.save(target, quality=90)
    except OSError:
        return photo, False
    return photo, True


def shortlist(root, domain):
    """Agent choices within the check caps, closer lookalikes first; fetch their photos at 1000 px."""
    out = root / "data" / "confirm" / domain
    index = {s["sheet"]: s for s in json.loads((out / "sheet_index.json").read_text(encoding="utf-8"))}
    choices = [c for f in sorted(out.glob("pass1_part*.json")) for c in json.loads(f.read_text(encoding="utf-8"))
               if c.get("use") and c["sheet"] not in OTHER_KIND]
    # Scarce fashion kinds first, so shoes of the same brand do not use up the brand cap (spec: boots 10).
    first = {kind for kind in TARGETS[domain] if domain == "fashion" and kind != "SHOES"}
    choices.sort(key=lambda c: (index[c["sheet"]]["kind"] not in first, RANK[c["closeness"]], c["sheet"]))
    kind_cap = {kind: int(target * 1.6) + 1 for kind, target in TARGETS[domain].items()}
    used, per_kind, kept = Counter(), Counter(), []
    for choice in choices:
        sheet = index[choice["sheet"]]
        anchor, other = sheet["rows"][0], sheet["rows"][choice["c_row"]]
        if domain == "fashion":
            photos = {"a1": anchor["photos"][choice["a1"]], "a2": anchor["photos"][choice["a2"]],
                      "c": other["photos"][choice["c"]]}
            views = choice["views"]
        else:
            photos = {"a1": anchor["photos"][0], "a2": anchor["photos"][1], "c": other["photos"][1]}
            views = {"a1": "0 degrees", "a2": "45 degrees", "c": "45 degrees"}
        item = {"sheet": choice["sheet"], "kind": sheet["kind"], "brand": sheet["brand"],
                "listing": anchor["listing"], "other_listing": other["listing"], **photos, "views": views,
                "closeness": choice["closeness"], "note": choice.get("note", "")}
        group = cap_group(domain, item)
        if None in photos.values() or used[group] >= CHECK_CAP:
            continue
        if per_kind[item["kind"]] >= kind_cap[item["kind"]]:
            continue
        used[group] += 1
        per_kind[item["kind"]] += 1
        kept.append(item)
    kept.sort(key=lambda k: k["sheet"])
    (out / "shortlist.json").write_text(json.dumps(kept, ensure_ascii=False, indent=0), encoding="utf-8")
    print("agent sets", len(choices), "| kept for the 1000 px check", len(kept))
    print("kind", Counter(k["kind"] for k in kept).most_common())
    print("closeness", Counter(k["closeness"] for k in kept).most_common())
    photos = sorted({k[slot] for k in kept for slot in ("a1", "a2", "c")})
    (root / "data" / "pairs" / "photos").mkdir(parents=True, exist_ok=True)
    if domain == "fashion":
        paths = image_paths(root)
        jobs = [(root, photo, f"images/original/{paths[photo]}") for photo in photos]
    else:
        spins = json.loads((out / "spin_paths.json").read_text(encoding="utf-8"))
        jobs = [(root, photo, f"spins/original/{spins[photo]}") for photo in photos]
    with ThreadPoolExecutor(8) as executor:
        got = dict(executor.map(fetch_large, jobs))
    print("photos", len(photos), "| fetched", sum(got.values()))
    for old in out.glob("check_part*.txt"):
        old.unlink()
    for start in range(0, len(kept), CHECK_LINES):
        lines = [f"{k['sheet']} a1={k['a1']} a2={k['a2']} c={k['c']}\n" for k in kept[start:start + CHECK_LINES]]
        (out / f"check_part{start // CHECK_LINES + 1}.txt").write_text("".join(lines), encoding="utf-8")


def final(root, domain):
    """Sets that passed the 1000 px check, within the final cap and the kind targets."""
    out = root / "data" / "confirm" / domain
    items = {k["sheet"]: k for k in json.loads((out / "shortlist.json").read_text(encoding="utf-8"))}
    passed = {}
    for f in sorted(out.glob("pass2_part*.json")):
        for result in json.loads(f.read_text(encoding="utf-8")):
            if result["ok"]:
                passed[result["sheet"]] = {**items[result["sheet"]], "check_note": result.get("note", "")}
    first = {kind for kind in TARGETS[domain] if domain == "fashion" and kind != "SHOES"}
    ordered = sorted(passed.values(), key=lambda k: (k["kind"] not in first, RANK[k["closeness"]], k["sheet"]))
    targets = dict(TARGETS[domain])
    if domain == "fashion":
        available = Counter(k["kind"] for k in ordered)
        targets["SHOES"] += sum(max(0, n - available[kind]) for kind, n in targets.items() if kind != "SHOES")
    used, per_kind, kept = Counter(), Counter(), []
    for item in ordered:
        group = cap_group(domain, item)
        if used[group] < FINAL_CAP and per_kind[item["kind"]] < targets[item["kind"]]:
            used[group] += 1
            per_kind[item["kind"]] += 1
            kept.append(item)
    kept.sort(key=lambda k: k["sheet"])
    prefix = "cf" if domain == "fashion" else "ch"
    for number, item in enumerate(kept, start=1):
        item["pair_id"] = f"{prefix}{number:03d}"
    (out / "sets.json").write_text(json.dumps(kept, ensure_ascii=False, indent=0), encoding="utf-8")
    print("passed", len(passed), "| kept", len(kept), "| targets", targets)
    print("kind", Counter(k["kind"] for k in kept).most_common())
    print("brand", Counter(k["brand"] for k in kept).most_common())
    print("closeness", Counter(k["closeness"] for k in kept).most_common())
    photos = Counter(k[slot] for k in kept for slot in ("a1", "a2", "c"))
    print("photos", len(photos), "| used more than once", sum(v > 1 for v in photos.values()))
    anchors = {k["listing"] for k in kept}
    print("anchor products also used as a lookalike", len(anchors & {k["other_listing"] for k in kept}))


def review(root):
    """One page for the user with every fashion and furniture set (spec section 3: the user sees every set)."""
    def figure(photo, label):
        return (f'<figure><a href="../pairs/photos/{photo}.jpg" target="_blank">'
                f'<img loading="lazy" src="../pairs/photos/{photo}.jpg" alt="{label}"></a><figcaption>{label}</figcaption></figure>')

    sections, total = [], 0
    for domain, title in (("fashion", "패션 (확인)"), ("furniture", "가구와 조명 (탐색)")):
        kept = json.loads((root / "data" / "confirm" / domain / "sets.json").read_text(encoding="utf-8"))
        total += len(kept)
        cards = "".join(
            f'<section class="card"><h2>{html.escape(k["pair_id"])} <small>{html.escape(k["brand"])} · '
            f'{html.escape(k["kind"])}</small></h2><div class="row">{figure(k["a2"], "같은 물건이어야 함")}'
            f'{figure(k["a1"], "기준")}{figure(k["c"], "다른 물건이어야 함")}</div></section>' for k in kept)
        sections.append(f"<h1>{title} ({len(kept)}개)</h1>{cards}")
    page = (
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>확인 실험 사진 쌍</title><style>{PAGE_STYLE}</style></head><body><main>"
        f"<p>확인 실험의 사진 쌍 {total}개입니다. 가운데가 기준 사진입니다. 세 가지를 봐 주세요. 왼쪽이 기준과 같은 "
        "물건인가, 오른쪽이 기준과 모양이 다른 물건인가(색이나 천만 다른 것은 안 됩니다), 세 사진 어디에도 브랜드 "
        "글자나 로고가 보이지 않는가. 사진을 누르면 모델이 볼 크기(긴 변 1000픽셀)로 열립니다. 하나라도 아니면 "
        "번호(cf001, ch001 등)만 알려 주세요. 그 번호는 통째로 뺍니다. 가구는 360도 회전 사진의 0도와 45도입니다. "
        "사진 출처: Amazon Berkeley Objects (CC BY 4.0).</p>" + "".join(sections) + "</main></body></html>"
    )
    target = root / "data" / "confirm" / "review.html"
    target.write_text(page, encoding="utf-8")
    print("wrote", target, "| sets", total)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    root, command = Path(sys.argv[1]), sys.argv[2]
    (root / "data" / "pairs" / "small").mkdir(parents=True, exist_ok=True)
    if command == "review":
        review(root)
    elif command in ("shortlist", "final"):
        {"shortlist": shortlist, "final": final}[command](root, sys.argv[3])
    else:
        {"fashion": fashion, "furniture": furniture}[command](root)


if __name__ == "__main__":
    main()
