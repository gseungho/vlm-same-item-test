"""The sample is fixed before any model call, so its balance is checked here (spec sections 5, 7)."""

from collections import Counter

from vtrust.sample import FAMOUS, MEANINGS, build_config


def make_sets():
    brands = ["Klepe", "Eden & Ivy", "Sixth & Love", "206 Collective", "Flavia", "Symbol"]
    kinds = ["SHOES"] * 55 + ["HANDBAG"] * 15 + ["BOOT"] * 10
    sets = []
    for number, kind in enumerate(kinds, start=1):
        sets.append({
            "pair_id": f"p{number:03d}", "sheet": f"s{number:03d}", "kind": kind,
            "brand": brands[number % len(brands)], "listing": f"L{number}", "other_listing": f"O{number}",
            "a1": f"a1_{number}", "a2": f"a2_{number}", "c": f"c_{number}",
            "views": {"a1": "side", "a2": "side", "c": "side"}, "closeness": "close", "note": "", "check_note": "",
        })
    return sets


def info(photo):
    return {"sha256": f"hash_{photo}", "width": 1000, "height": 700}


def anchors(**kwargs):
    return build_config(make_sets(), info, **kwargs)["anchors"]


def test_excluded_pairs_leave_the_sample():
    ids = {a["pair_id"] for a in anchors(excluded={"p001", "p013"})}
    assert "p001" not in ids and "p013" not in ids and len(ids) == 78


def test_same_seed_gives_the_same_sample():
    assert anchors(seed=7) == anchors(seed=7)


def test_other_seed_changes_the_sample():
    assert anchors(seed=7) != anchors(seed=8)


def test_other_brand_shares_no_word_with_the_real_brand():
    for a in anchors():
        assert a["other_brand"] != a["brand"]
        words = {w.lower() for w in a["brand"].split() if w != "&"}
        assert not words & {w.lower() for w in a["other_brand"].split() if w != "&"}


def test_other_brand_comes_from_the_sample():
    sample = anchors()
    brands = {a["brand"] for a in sample}
    assert {a["other_brand"] for a in sample} <= brands


def test_famous_brands_are_balanced():
    counts = Counter(a["famous_brand"] for a in anchors())
    assert set(counts) == set(FAMOUS) and max(counts.values()) - min(counts.values()) <= 1


def test_placement_is_split_in_half():
    sample = anchors()
    half = len(sample) / 2
    assert abs(sum(a["anchor_first"] for a in sample) - half) <= 1
    assert abs(sum(a["name_line_first"] for a in sample) - half) <= 1


def test_option_orders_are_balanced():
    sample = anchors()
    counts = Counter(tuple(a["option_order"]) for a in sample)
    assert all(sorted(order) == sorted(MEANINGS) for order in counts)
    assert len(counts) == 6 and max(counts.values()) - min(counts.values()) <= 1


def test_every_prefix_keeps_the_kinds_in_proportion():
    sample = anchors()
    total = Counter(a["kind"] for a in sample)
    for size in (6, 60):
        head = Counter(a["kind"] for a in sample[:size])
        for kind, count in total.items():
            assert abs(head[kind] - count * size / len(sample)) <= 1


def test_photos_carry_their_hash_and_size():
    config = build_config(make_sets(), info)
    assert config["photos"]["a1_1"] == info("a1_1")
    assert set(config["photos"]) == {
        a[slot] for a in config["anchors"] for slot in ("a1", "a2", "c")
    }


def test_famous_brands_can_be_given_for_another_domain():
    furniture = ("IKEA", "West Elm", "Pottery Barn")
    counts = Counter(a["famous_brand"] for a in anchors(famous=furniture))
    assert set(counts) == set(furniture) and max(counts.values()) - min(counts.values()) <= 1


def test_confirmation_config_names_its_results_and_has_no_smoke_run():
    config = build_config(make_sets(), info, seed=20261104, results_name="confirm_fashion", confirm_claims=True,
                          smoke_anchors=0)
    assert config["results_name"] == "confirm_fashion" and config["confirm_claims"] is True
    assert config["smoke_anchors"] == 0 and config["seed"] == 20261104


def test_pilot_config_keeps_its_fields():
    config = build_config(make_sets(), info)
    assert "results_name" not in config and "confirm_claims" not in config and config["smoke_anchors"] == 6
