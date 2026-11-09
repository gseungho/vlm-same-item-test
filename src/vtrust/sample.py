"""Fix the sample before any model call (spec sections 5 and 7). Nothing here calls the API.

    python -m vtrust.sample <project_dir> --exclude p001 p013
"""

import argparse
import hashlib
import json
import random
import re
import sys
from collections import Counter
from itertools import permutations
from pathlib import Path

SEED = 20261102
# Known names that sell shoes, boots and handbags, so the name does not vary with the product kind.
FAMOUS = ("Gucci", "Prada", "Coach")
MEANINGS = ("same", "different", "unknown")
MODELS = {"haiku": "claude-haiku-5-5", "sonnet": "claude-sonnet-5-5", "opus": "claude-opus-5-5"}


def _words(brand):
    return set(re.findall(r"[a-z0-9]+", brand.lower()))


def _balanced(values, size, rng):
    """`size` values, each used as evenly as possible, in random order."""
    values = list(values)
    out = (values * (size // len(values) + 1))[:size]
    rng.shuffle(out)
    return out


def _order_by_kind(sets, rng):
    """Shuffle within each kind, then interleave so any prefix keeps the kinds in proportion."""
    groups = {}
    for item in sorted(sets, key=lambda s: s["pair_id"]):
        groups.setdefault(item["kind"], []).append(item)
    for group in groups.values():
        rng.shuffle(group)
    totals = {kind: len(group) for kind, group in groups.items()}
    taken = Counter()
    ordered = []
    for position in range(1, len(sets) + 1):
        kind = max(sorted(groups), key=lambda k: totals[k] * position / len(sets) - taken[k])
        ordered.append(groups[kind][taken[kind]])
        taken[kind] += 1
    return ordered


def build_config(sets, photo_info, excluded=frozenset(), seed=SEED, famous=FAMOUS, results_name=None,
                 confirm_claims=False, smoke_anchors=6):
    rng = random.Random(seed)
    kept = [s for s in sets if s["pair_id"] not in excluded]
    ordered = _order_by_kind(kept, rng)
    brands = sorted({s["brand"] for s in kept})
    size = len(ordered)
    anchor_first = _balanced([True, False], size, rng)
    name_line_first = _balanced([True, False], size, rng)
    orders = _balanced([list(p) for p in permutations(MEANINGS)], size, rng)
    famous = _balanced(famous, size, rng)
    anchors = []
    for index, item in enumerate(ordered):
        others = [b for b in brands if not _words(b) & _words(item["brand"])]
        anchors.append({
            "pair_id": item["pair_id"], "sheet": item["sheet"], "kind": item["kind"], "brand": item["brand"],
            "listing": item["listing"], "other_listing": item["other_listing"],
            "a1": item["a1"], "a2": item["a2"], "c": item["c"],
            "views": item["views"], "closeness": item["closeness"],
            "other_brand": rng.choice(others), "famous_brand": famous[index],
            "anchor_first": anchor_first[index], "name_line_first": name_line_first[index],
            "option_order": orders[index],
        })
    photos = {a[slot]: photo_info(a[slot]) for a in anchors for slot in ("a1", "a2", "c")}
    config = {
        "seed": seed, "models": MODELS, "effort": "medium", "max_tokens": 8000, "smoke_anchors": smoke_anchors,
        "batch_limit_mb": 200, "excluded": sorted(excluded), "anchors": anchors, "photos": photos,
    }
    # Confirmation configs (spec 2026-11-04) keep their results apart and are judged on the claims.
    if results_name:
        config["results_name"] = results_name
    if confirm_claims:
        config["confirm_claims"] = True
    return config


def _photo_info(photo_dir):
    from PIL import Image

    def read(photo):
        path = photo_dir / f"{photo}.jpg"
        with Image.open(path) as image:
            width, height = image.size
        return {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "width": width, "height": height}

    return read


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--exclude", nargs="*", default=[])
    parser.add_argument("--out", default="configs/same_item_v1.json")
    parser.add_argument("--sets", default="data/pairs/sets.json")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--famous", nargs=3, default=list(FAMOUS))
    parser.add_argument("--results-name")
    parser.add_argument("--claims", action="store_true", help="확인 주장을 판정하는 설정")
    parser.add_argument("--smoke-anchors", type=int, default=6)
    args = parser.parse_args(argv)
    target = args.root / args.out
    if target.exists():
        raise SystemExit(f"{target} 이미 있습니다. 설정 파일은 고치지 않고 새 버전을 만듭니다.")
    sets = json.loads((args.root / args.sets).read_text(encoding="utf-8"))
    config = build_config(sets, _photo_info(args.root / "data" / "pairs" / "photos"), set(args.exclude),
                          seed=args.seed, famous=tuple(args.famous), results_name=args.results_name,
                          confirm_claims=args.claims, smoke_anchors=args.smoke_anchors)
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(config, ensure_ascii=False, indent=1), encoding="utf-8")
    print("앵커", len(config["anchors"]), "| 사진", len(config["photos"]), "|", target)
    print("유형", Counter(a["kind"] for a in config["anchors"]).most_common())
    print("브랜드", Counter(a["brand"] for a in config["anchors"]).most_common())
    print("비슷한 정도", Counter(a["closeness"] for a in config["anchors"]).most_common())


if __name__ == "__main__":
    main()
