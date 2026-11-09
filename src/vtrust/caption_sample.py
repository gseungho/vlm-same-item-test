"""Fix the caption items before any model call (caption pilot spec sections 4, 5 and 7). No API call.

    python -m vtrust.caption_sample <project_dir> verite    # VERITE photos and configs/caption_v1_verite.json
    python -m vtrust.caption_sample <project_dir> commons   # reviewed Commons items to configs/caption_v1_commons.json
    python -m vtrust.caption_sample <project_dir> verite|commons --revision r1   # spec r1 from the v1 config
    python -m vtrust.caption_sample <project_dir> verite|commons --revision r2   # spec r2 from the r1 config
    python -m vtrust.caption_sample <project_dir> confirm   # confirmation items to configs/caption_confirm_v1.json
"""

import argparse
import csv
import hashlib
import json
import random
import sys
from collections import Counter
from itertools import permutations
from pathlib import Path

from PIL import Image

from vtrust.captions import QC, WORDING_CONDITIONS
from vtrust.sample import MODELS, _balanced

SEED = 20261105
MEANINGS = ("yes", "no", "unknown")
LONG_SIDE = 1000


def verite_items(rows):
    """One item per true photo: its true and miscaptioned rows, and the out-of-context row when there is one."""
    items = {}
    for row in rows:
        name = row["image_path"].split("/")[-1].rsplit(".", 1)[0]
        side, number = name.split("_")
        item = items.setdefault(int(number), {"sources": {}})
        photo = f"v{side[0]}{int(number):03d}"
        item["sources"][photo] = row["image_path"]
        if row["label"] == "true":
            item["true_caption"], item["photo"] = row["caption"], photo
        elif row["label"] == "miscaptioned":
            item["false_caption"] = row["caption"]
        else:
            item["other_photo"] = photo
    out = []
    for number in sorted(items):
        item = items[number]
        out.append({"item_id": f"v{number:03d}", "photo": item["photo"], "other_photo": item.get("other_photo"),
                    "true_caption": item["true_caption"], "false_caption": item["false_caption"],
                    "sources": item["sources"]})
    return out


def prepare_photo(source, target, long_side=LONG_SIDE):
    """RGB JPEG whose long side is at most `long_side`; smaller photos keep their size."""
    with Image.open(source) as image:
        image = image.convert("RGB")
        scale = long_side / max(image.size)
        if scale < 1:
            image = image.resize((round(image.width * scale), round(image.height * scale)), Image.LANCZOS)
        image.save(target, "JPEG", quality=92)


def _interleave(items, key, rng):
    """Shuffle within each group, then interleave so any prefix keeps the groups in proportion."""
    groups = {}
    for item in sorted(items, key=lambda i: i["item_id"]):
        groups.setdefault(str(item.get(key)), []).append(item)
    for group in groups.values():
        rng.shuffle(group)
    totals, taken, ordered = {g: len(v) for g, v in groups.items()}, Counter(), []
    for position in range(1, len(items) + 1):
        group = max(sorted(groups), key=lambda g: totals[g] * position / len(items) - taken[g])
        ordered.append(groups[group][taken[group]])
        taken[group] += 1
    return ordered


def build_config(raw_items, photo_info, dataset, results_name, smoke_name, seed=SEED, smoke_items=6, labels=None):
    rng = random.Random(seed)
    ordered = _interleave(raw_items, "changed", rng)
    size = len(ordered)
    orders = _balanced([list(p) for p in permutations(MEANINGS)], size, rng)
    true_first = _balanced([True, False], size, rng)
    items = []
    for index, raw in enumerate(ordered):
        item = {k: v for k, v in raw.items() if k != "sources"}
        item |= {"option_order": orders[index], "true_first": true_first[index]}
        item |= (labels or {}).get(raw["item_id"], {})
        items.append(item)
    photos = {p: photo_info(p) for i in items for p in (i["photo"], i["other_photo"]) if p is not None}
    return {"seed": seed, "dataset": dataset, "models": MODELS, "effort": "medium", "max_tokens": 8000,
            "smoke_items": smoke_items, "batch_limit_mb": 200, "results_name": results_name,
            "smoke_name": smoke_name, "items": items, "photos": photos}


R1 = {"system": "Today's date is 8 November 2026.",
      "questions": {"qm": "Does the photo show what the caption describes?", "qa": "Is the caption accurate?"}}


def revise_r1(config):
    """Spec r1 (2026-11-08): same items and order; the date in a system line, a new QM wording, and a main run
    that leaves out the smoke items the wording was chosen on."""
    dataset = config["dataset"]
    return {**config, "revision": "r1", **R1, "main_from": config["smoke_items"],
            "results_name": f"caption_r1_{dataset}", "smoke_name": f"caption_r1_smoke_{dataset}"}


def revise_r2(config):
    """Spec r2 (2026-11-08): the r1 requests unchanged; R, M and the precondition read the "no" share. The r1
    smoke replies stand for r2, since the requests are the same."""
    dataset = config["dataset"]
    return {**config, "revision": "r2", "measure": "no", "results_name": f"caption_r2_{dataset}"}


MONTH_NAMES = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
               "November", "December")


def revise_confirm(config, today):
    """Confirmation spec 2026-11-08: the r1 requests with the date the config is fixed, r2 measures, the
    judgments of section 2, no smoke run."""
    return {**config, "revision": "confirm-v1", **R1, "measure": "no", "confirm": True, "main_from": 0,
            "system": f"Today's date is {today.day} {MONTH_NAMES[today.month - 1]} {today.year}.",
            "fixed_on": today.isoformat()}


WORDING_SOURCES = {"x": ("configs/caption_v1r2_commons.json", "caption_r2_commons", "explore"),
                   "k": ("configs/caption_confirm_v1.json", "caption_confirm", "confirm")}


def build_wording(explore, confirm, today):
    """Wording spec 2026-11-09: the main items of both Commons runs as they were (photos, captions, option order),
    ids prefixed x and k because 54 ids repeat, asked QM again and QC on six conditions. Nothing is drawn at random."""
    items, known = [], {}
    for prefix, config in (("x", explore), ("k", confirm)):
        source = WORDING_SOURCES[prefix][2]
        items += [{**i, "item_id": prefix + i["item_id"], "source": source}
                  for i in config["items"][config.get("main_from", 0):]]
        known |= config["photos"]
    photos = {p: known[p] for i in items for p in (i["photo"], i["other_photo"]) if p is not None}
    return {"seed": 20261109, "dataset": "commons_wording", "revision": "wording-v1", "models": MODELS,
            "effort": "medium", "max_tokens": 8000, "smoke_items": 0, "batch_limit_mb": 200,
            "results_name": "caption_wording", "smoke_name": "caption_wording_smoke", "measure": "no",
            "wording": True, "main_from": 0, "conditions": list(WORDING_CONDITIONS),
            "questions": {"qm": confirm["questions"]["qm"], "qc": QC},
            "system": f"Today's date is {today.day} {MONTH_NAMES[today.month - 1]} {today.year}.",
            "fixed_on": today.isoformat(),
            "previous": {p: {"config": c, "results": r} for p, (c, r, _) in WORDING_SOURCES.items()},
            "items": items, "photos": photos}


def _photo_info(photo_dir):
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
    parser.add_argument("dataset", choices=["verite", "commons", "confirm", "wording"])
    parser.add_argument("--revision", choices=["r1", "r2"], help="앞 설정에서 설계서 r1, r2의 설정을 만든다")
    args = parser.parse_args(argv)
    fixed = {"confirm": "caption_confirm_v1.json", "wording": "caption_wording_v1.json"}
    target = args.root / "configs" / fixed.get(args.dataset, f"caption_v1{args.revision or ''}_{args.dataset}.json")
    if target.exists():
        raise SystemExit(f"{target} 이미 있습니다. 설정 파일은 고치지 않고 새 버전을 만듭니다.")
    if args.dataset == "wording":
        from datetime import date

        explore, confirm = (json.loads((args.root / WORDING_SOURCES[p][0]).read_text(encoding="utf-8"))
                            for p in ("x", "k"))
        config = build_wording(explore, confirm, date.today())
        target.write_text(json.dumps(config, ensure_ascii=False, indent=1), encoding="utf-8")
        print("문항", len(config["items"]), "| 사진", len(config["photos"]), "|", target)
        print("묶음", Counter(i["source"] for i in config["items"]).most_common())
        return
    if args.revision:
        before = {"r1": "", "r2": "r1"}[args.revision]
        base = json.loads((args.root / "configs" / f"caption_v1{before}_{args.dataset}.json").read_text(
            encoding="utf-8"))
        revise = {"r1": revise_r1, "r2": revise_r2}[args.revision]
        target.write_text(json.dumps(revise(base), ensure_ascii=False, indent=1), encoding="utf-8")
        print(target)
        return
    photo_dir = args.root / "data" / "captions" / "photos"
    photo_dir.mkdir(parents=True, exist_ok=True)
    if args.dataset == "verite":
        base = args.root / "data" / "verite" / "VERITE"
        with open(base / "VERITE.csv", encoding="utf-8") as f:
            raw = verite_items(list(csv.DictReader(f)))
        for item in raw:
            for photo, source in item["sources"].items():
                if not (photo_dir / f"{photo}.jpg").exists():
                    prepare_photo(base / source, photo_dir / f"{photo}.jpg")
        labels_path = args.root / "data" / "captions" / "verite_labels.json"
    elif args.dataset == "confirm":
        from datetime import date

        today = date.today()
        raw = json.loads((args.root / "data" / "captions" / "commons_confirm" / "items.json").read_text(
            encoding="utf-8"))
        late = [i["item_id"] for i in raw if i["taken"] >= today.isoformat()]
        if late:
            raise SystemExit(f"오늘이나 그 뒤에 찍은 사진이 있습니다(설계서 3절): {late}")
        config = build_config(raw, _photo_info(photo_dir), "commons_confirm", "caption_confirm",
                              "caption_confirm_smoke", seed=20261108, smoke_items=0)
        target.write_text(json.dumps(revise_confirm(config, today), ensure_ascii=False, indent=1), encoding="utf-8")
        print("문항", len(config["items"]), "| 사진", len(config["photos"]), "|", target)
        print("바꾼 사실", Counter(i.get("changed") for i in config["items"]).most_common())
        return
    else:
        raw = json.loads((args.root / "data" / "captions" / "commons" / "items.json").read_text(encoding="utf-8"))
        labels_path = None
    labels = json.loads(labels_path.read_text(encoding="utf-8")) if labels_path else None
    config = build_config(raw, _photo_info(photo_dir), args.dataset, f"caption_{args.dataset}",
                          f"caption_smoke_{args.dataset}", labels=labels)
    target.write_text(json.dumps(config, ensure_ascii=False, indent=1), encoding="utf-8")
    print("문항", len(config["items"]), "| 사진", len(config["photos"]), "|", target)
    print("바꾼 사실", Counter(i.get("changed") for i in config["items"]).most_common())


if __name__ == "__main__":
    main()
