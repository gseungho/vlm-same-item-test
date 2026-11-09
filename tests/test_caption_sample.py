"""Fixing the caption items before any model call (caption pilot spec sections 4, 5 and 7)."""

from collections import Counter

from PIL import Image

from vtrust import caption_sample


def verite_rows(n, missing=()):
    rows = []
    for k in range(n):
        rows.append({"caption": f"Photograph shows event {k}.", "image_path": f"images/true_{k}.jpg", "label": "true"})
        rows.append({"caption": f"Photograph shows wrong {k}.", "image_path": f"images/true_{k}.jpg",
                     "label": "miscaptioned"})
        if k not in missing:
            rows.append({"caption": f"Photograph shows event {k}.", "image_path": f"images/false_{k}.jpg",
                         "label": "out-of-context"})
    return rows


def test_verite_rows_become_one_item_per_true_photo():
    items = caption_sample.verite_items(verite_rows(4, missing={2}))
    assert [i["item_id"] for i in items] == ["v000", "v001", "v002", "v003"]
    first = items[0]
    assert first["true_caption"] == "Photograph shows event 0."
    assert first["false_caption"] == "Photograph shows wrong 0."
    assert first["photo"] == "vt000" and first["other_photo"] == "vf000"
    assert first["sources"] == {"vt000": "images/true_0.jpg", "vf000": "images/false_0.jpg"}
    assert items[2]["other_photo"] is None and items[2]["sources"] == {"vt002": "images/true_2.jpg"}


def raw_items(n, changed=None):
    kinds = changed or [None] * n
    return [{"item_id": f"c{k:03d}", "photo": f"p{k}", "other_photo": f"o{k}", "true_caption": f"T{k}",
             "false_caption": f"F{k}", "changed": kinds[k]} for k in range(n)]


def info(photo):
    return {"sha256": photo * 2, "width": 10, "height": 10}


def config_of(items, **kw):
    return caption_sample.build_config(items, info, dataset="commons", results_name="caption_commons",
                                       smoke_name="caption_smoke_commons", **kw)


def test_the_order_is_fixed_by_the_seed():
    first = [i["item_id"] for i in config_of(raw_items(30))["items"]]
    again = [i["item_id"] for i in config_of(raw_items(30))["items"]]
    other = [i["item_id"] for i in config_of(raw_items(30), seed=7)["items"]]
    assert first == again != other and sorted(first) == [f"c{k:03d}" for k in range(30)]


def test_option_orders_and_caption_positions_are_balanced():
    items = config_of(raw_items(60))["items"]
    orders = Counter(tuple(i["option_order"]) for i in items)
    assert len(orders) == 6 and set(orders.values()) == {10}
    assert all(sorted(o) == ["no", "unknown", "yes"] for o in orders)
    assert Counter(i["true_first"] for i in items) == {True: 30, False: 30}


def test_a_prefix_keeps_the_changed_fact_in_proportion():
    kinds = ["event"] * 10 + ["place"] * 10 + ["date"] * 10
    items = config_of(raw_items(30, kinds))["items"]
    assert Counter(i["changed"] for i in items[:6]) == {"event": 2, "place": 2, "date": 2}


def test_config_names_its_own_folders_and_photos():
    config = config_of(raw_items(3))
    assert config["results_name"] == "caption_commons" and config["smoke_name"] == "caption_smoke_commons"
    assert config["seed"] == 20261105 and config["smoke_items"] == 6 and config["dataset"] == "commons"
    assert set(config["photos"]) == {"p0", "p1", "p2", "o0", "o1", "o2"}
    assert config["photos"]["p1"]["sha256"] == "p1p1"


def test_missing_other_photo_is_not_listed():
    items = raw_items(2)
    items[1]["other_photo"] = None
    assert set(config_of(items)["photos"]) == {"p0", "o0", "p1"}


def test_labels_are_copied_into_the_items():
    config = config_of(raw_items(2), labels={"c001": {"text_in_photo": True}})
    by_id = {i["item_id"]: i for i in config["items"]}
    assert by_id["c001"]["text_in_photo"] is True and "text_in_photo" not in by_id["c000"]


def test_photos_are_shrunk_to_1000_pixels_and_saved_as_jpeg(tmp_path):
    big, small = tmp_path / "big.png", tmp_path / "small.jpg"
    Image.new("RGBA", (2000, 1500), (10, 20, 30, 255)).save(big)
    Image.new("RGB", (300, 200)).save(small)
    caption_sample.prepare_photo(big, tmp_path / "a.jpg")
    caption_sample.prepare_photo(small, tmp_path / "b.jpg")
    with Image.open(tmp_path / "a.jpg") as a, Image.open(tmp_path / "b.jpg") as b:
        assert a.format == "JPEG" and a.size == (1000, 750) and a.mode == "RGB"
        assert b.size == (300, 200)


def test_r1_keeps_the_items_and_changes_only_the_wording_and_folders():
    v1 = config_of(raw_items(12))
    r1 = caption_sample.revise_r1(v1)
    assert r1["items"] == v1["items"] and r1["photos"] == v1["photos"] and r1["seed"] == v1["seed"]
    assert r1["revision"] == "r1" and r1["main_from"] == v1["smoke_items"] == r1["smoke_items"]
    assert r1["system"] == "Today's date is 8 November 2026."
    assert r1["questions"] == {"qm": "Does the photo show what the caption describes?",
                               "qa": "Is the caption accurate?"}
    assert r1["results_name"] == "caption_r1_commons" and r1["smoke_name"] == "caption_r1_smoke_commons"
    assert "revision" not in v1


def test_r2_keeps_the_r1_requests_and_measures_rejection():
    r1 = caption_sample.revise_r1(config_of(raw_items(12)))
    r2 = caption_sample.revise_r2(r1)
    assert {k: v for k, v in r2.items() if k not in ("revision", "measure", "results_name", "smoke_name")} == \
        {k: v for k, v in r1.items() if k not in ("revision", "results_name", "smoke_name")}
    assert r2["revision"] == "r2" and r2["measure"] == "no" and "measure" not in r1
    assert r2["smoke_name"] == r1["smoke_name"] == "caption_r1_smoke_commons"  # same requests, same smoke
    assert r2["results_name"] == "caption_r2_commons"


def test_confirm_config_uses_r2_measures_and_the_day_it_is_fixed():
    from datetime import date

    base = caption_sample.build_config(raw_items(12), info, dataset="commons_confirm", results_name="caption_confirm",
                                       smoke_name="caption_confirm_smoke", seed=20261108, smoke_items=0)
    config = caption_sample.revise_confirm(base, date(2026, 11, 20))
    assert config["seed"] == 20261108 and config["smoke_items"] == 0 and config["main_from"] == 0
    assert config["measure"] == "no" and config["confirm"] is True and config["revision"] == "confirm-v1"
    assert config["system"] == "Today's date is 20 November 2026."
    assert config["questions"] == caption_sample.R1["questions"]
    assert config["results_name"] == "caption_confirm" and config["fixed_on"] == "2026-11-20"


def test_wording_config_joins_both_commons_runs_with_prefixed_ids():
    from datetime import date

    explore = {**config_of(raw_items(8)), "main_from": 2, "questions": caption_sample.R1["questions"]}
    confirm = {**config_of(raw_items(5)), "main_from": 0, "seed": 20261108,
               "questions": caption_sample.R1["questions"]}
    config = caption_sample.build_wording(explore, confirm, date(2026, 11, 9))
    ids = [i["item_id"] for i in config["items"]]
    assert len(ids) == 6 + 5 == len(set(ids))
    assert ids[:6] == ["x" + i["item_id"] for i in explore["items"][2:]]
    assert ids[6:] == ["k" + i["item_id"] for i in confirm["items"]]
    first = config["items"][0]
    assert first["source"] == "explore" and first["option_order"] == explore["items"][2]["option_order"]
    assert config["items"][6]["source"] == "confirm"
    assert config["conditions"] == ["true_qm", "mc_qm", "ooc_qm", "true_qc", "mc_qc", "ooc_qc"]
    assert config["questions"] == {"qm": "Does the photo show what the caption describes?",
                                   "qc": "Does anything in the photo contradict the caption?"}
    assert config["system"] == "Today's date is 9 November 2026." and config["wording"] is True
    assert config["smoke_items"] == 0 and config["main_from"] == 0 and config["results_name"] == "caption_wording"
    assert set(config["previous"]) == {"x", "k"} and config["previous"]["k"]["results"] == "caption_confirm"
    used = {p for i in explore["items"][2:] + confirm["items"] for p in (i["photo"], i["other_photo"])}
    assert set(config["photos"]) == used  # the photos of the two smoke items stay out
