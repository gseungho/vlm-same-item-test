"""The quantities of spec section 3 and the reading rule of section 6, on answers made by hand."""

import pytest

from vtrust.analysis import (
    BONFERRONI_LEVEL,
    claim_verdict,
    confirm_claims,
    contrast,
    double_difference,
    effect,
    flip_rate,
    model_difference,
    rate,
    subset,
    unknown_rate,
    verdict,
)


def table(rows):
    """{pair_id: {(relation, name, question): meaning}} from (pair, relation, name, question, meaning)."""
    out = {}
    for pair, relation, name, question, meaning in rows:
        out.setdefault(pair, {})[relation, name, question] = meaning
    return out


NONE, DIFF = ("same", "none", "q1"), ("same", "different", "q1")


def answers(pairs_none_diff):
    rows = []
    for number, (none, diff) in enumerate(pairs_none_diff):
        rows.append((f"p{number}", *NONE, none))
        rows.append((f"p{number}", *DIFF, diff))
    return table(rows)


def test_rate_counts_only_same_answers():
    data = answers([("same", "same"), ("different", "same"), ("unknown", "same"), ("same", "same")])
    assert rate(data, NONE) == 0.5


def test_no_answer_leaves_the_denominator():
    data = answers([("same", "same"), (None, "same"), ("different", "same")])
    assert rate(data, NONE) == 0.5


def test_spec_example_gives_thirty_points():
    data = answers([("same", "same")] * 50 + [("same", "different")] * 30 + [("different", "different")] * 20)
    point, low, high = effect(data, NONE, DIFF, n_boot=200)
    assert point == pytest.approx(0.30)
    assert low <= point <= high


def test_effect_is_taken_only_on_anchors_with_both_answers():
    data = answers([("same", "different"), ("same", None), (None, "different")])
    assert effect(data, NONE, DIFF, n_boot=50)[0] == 1.0


def test_interval_is_zero_width_when_every_anchor_agrees():
    data = answers([("same", "different")] * 10)
    assert effect(data, NONE, DIFF, n_boot=50) == (1.0, 1.0, 1.0)


def test_interval_resamples_anchors_so_it_widens_with_disagreement():
    data = answers([("same", "different")] * 10 + [("same", "same")] * 10)
    point, low, high = effect(data, NONE, DIFF, n_boot=500)
    assert point == 0.5 and low < 0.5 < high


def test_same_seed_gives_the_same_interval():
    data = answers([("same", "different")] * 10 + [("same", "same")] * 10)
    assert effect(data, NONE, DIFF, n_boot=100, seed=3) == effect(data, NONE, DIFF, n_boot=100, seed=3)


def test_flip_rate_uses_anchors_answering_same_without_a_name():
    data = answers([("same", "different"), ("same", "same"), ("different", "different"), ("same", "unknown")])
    assert flip_rate(data, NONE, DIFF) == (2 / 3, 3)


def test_flip_rate_is_none_without_eligible_anchors():
    assert flip_rate(answers([("different", "same")]), NONE, DIFF) == (None, 0)


def test_unknown_rate_counts_cannot_tell():
    assert unknown_rate(answers([("unknown", "same"), ("same", "same")]), NONE) == 0.5


def test_model_difference_compares_the_same_anchors():
    haiku = answers([("same", "different")] * 10)
    opus = answers([("same", "same")] * 10)
    assert model_difference(haiku, opus, NONE, DIFF, n_boot=50) == (1.0, 1.0, 1.0)


def test_subset_keeps_only_named_anchors():
    data = answers([("same", "same"), ("different", "same")])
    assert set(subset(data, {"p1"})) == {"p1"}


@pytest.mark.parametrize(
    ("point", "low", "high", "name"),
    [
        (0.01, -0.04, 0.04, "차이가 작음"),
        (0.10, 0.02, 0.18, "차이가 있음"),
        (-0.10, -0.18, -0.02, "차이가 있음"),
        (0.10, -0.01, 0.20, "알 수 없음"),
        (0.03, 0.01, 0.06, "알 수 없음"),
    ],
)
def test_verdict_follows_the_reading_table(point, low, high, name):
    assert verdict(point, low, high) == name


def test_small_is_checked_before_present():
    # Inside the band and away from zero: the table is read from the top, so it is small.
    assert verdict(0.04, 0.01, 0.049) == "차이가 작음"


def test_double_difference_is_the_interaction_of_two_contrasts():
    a, b = ("same", "same", "q1"), ("same", "different", "q1")
    c, d = ("different", "same", "q1"), ("different", "different", "q1")
    rows = []
    for number in range(10):
        pair = f"p{number}"
        rows += [(pair, *a, "same"), (pair, *b, "different"), (pair, *c, "same"), (pair, *d, "same")]
    assert double_difference(table(rows), a, b, c, d, n_boot=50) == (1.0, 1.0, 1.0)


def test_double_difference_skips_anchors_missing_a_cell():
    a, b, c, d = NONE, DIFF, ("same", "none", "q2"), ("same", "different", "q2")
    rows = [("p0", *a, "same"), ("p0", *b, "different"), ("p0", *c, "same"), ("p0", *d, "same"), ("p1", *a, "same")]
    assert double_difference(table(rows), a, b, c, d, n_boot=50)[0] == 1.0


NONE2, DIFF2 = ("same", "none", "q2"), ("same", "different", "q2")
SELLER = ("same", "seller", "q1")


def four_cells(rows_per_anchor):
    """Anchors with answers for NONE, DIFF, NONE2, DIFF2 given as 4-tuples."""
    rows = []
    for number, answers_ in enumerate(rows_per_anchor):
        for cell, meaning in zip((NONE, DIFF, NONE2, DIFF2), answers_, strict=True):
            rows.append((f"p{number}", *cell, meaning))
    return table(rows)


def test_contrast_with_unit_weights_is_the_effect():
    data = answers([("same", "different")] * 3 + [("same", "same")] * 7)
    terms = [(NONE, "same", 1), (DIFF, "same", -1)]
    assert contrast(data, terms, n_boot=100)[0] == effect(data, NONE, DIFF, n_boot=100)[0]


def test_w_is_the_q1_effect_minus_twice_the_q2_effect():
    # T_Q1 = 0.5 and T_Q2 = 0.1, so W = 0.5 - 2 * 0.1 = 0.3 (spec 2026-11-04 section 2).
    data = four_cells([("same", "different", "same", "same")] * 4
                      + [("same", "different", "same", "different")] * 1
                      + [("same", "same", "same", "same")] * 5)
    terms = [(NONE, "same", 1), (DIFF, "same", -1), (NONE2, "same", -2), (DIFF2, "same", 2)]
    assert contrast(data, terms, n_boot=100)[0] == pytest.approx(0.3)


def test_k_is_the_rise_in_cannot_tell_minus_the_rise_in_different():
    # Three anchors move from same to cannot tell, one from same to different: K = 3/4 - 1/4.
    data = answers([("same", "unknown")] * 3 + [("same", "different")])
    terms = [(DIFF, "unknown", 1), (NONE, "unknown", -1), (DIFF, "different", -1), (NONE, "different", 1)]
    assert contrast(data, terms, n_boot=100)[0] == pytest.approx(0.5)


def test_contrast_skips_anchors_missing_a_cell():
    data = answers([("same", "different"), ("same", None)])
    assert contrast(data, [(NONE, "same", 1), (DIFF, "same", -1)], n_boot=50)[0] == 1.0


def test_wider_level_gives_a_wider_interval():
    data = answers([("same", "different")] * 12 + [("same", "same")] * 8)
    _, low95, high95 = effect(data, NONE, DIFF, n_boot=2000)
    _, low, high = effect(data, NONE, DIFF, n_boot=2000, level=BONFERRONI_LEVEL)
    assert low <= low95 and high95 <= high and (low < low95 or high95 < high)


def test_bonferroni_level_splits_five_percent_over_eleven_judgments():
    assert BONFERRONI_LEVEL == pytest.approx(1 - 0.05 / 11)


@pytest.mark.parametrize(
    ("point", "low", "high", "name"),
    [
        (0.10, 0.02, 0.18, "확인"),
        (0.02, -0.01, 0.04, "반증"),
        (-0.10, -0.18, -0.02, "반증"),
        (0.06, -0.01, 0.13, "판정 못 함"),
        (0.04, 0.01, 0.07, "판정 못 함"),
    ],
)
def test_claim_verdict_follows_the_confirmation_table(point, low, high, name):
    assert claim_verdict(point, low, high) == name


def model_answers(t_q1, t_q2, seller_flips, n=20):
    """Anchors answering same without a name; the first t_q1 / t_q2 / seller_flips change under a name."""
    rows = []
    for number in range(n):
        pair = f"p{number}"
        rows += [(pair, *NONE, "same"), (pair, *DIFF, "different" if number < t_q1 else "same"),
                 (pair, *NONE2, "same"), (pair, *DIFF2, "unknown" if number < t_q2 else "same"),
                 (pair, *SELLER, "unknown" if number < seller_flips else "same")]
    return table(rows)


def test_confirm_claims_gives_eleven_judgments_in_spec_order():
    tables = {"haiku": model_answers(15, 8, 9), "sonnet": model_answers(6, 1, 1), "opus": model_answers(12, 1, 1)}
    result = confirm_claims(tables, n_boot=200)
    assert [(r["claim"], r["model"], r["value"]) for r in result] == [
        ("C1", "haiku", "T_Q1"), ("C1", "sonnet", "T_Q1"), ("C1", "opus", "T_Q1"),
        ("C2", "sonnet", "W_Q2"), ("C2", "sonnet", "W_P"), ("C2", "opus", "W_Q2"), ("C2", "opus", "W_P"),
        ("C3", "haiku", "T_Q2"), ("C3", "haiku", "K_Q2"), ("C3", "haiku", "K_P"),
        ("C4", "opus - sonnet", "T_Q1"),
    ]
    by = {(r["claim"], r["model"], r["value"]): r for r in result}
    assert by["C1", "haiku", "T_Q1"]["point"] == pytest.approx(15 / 20)
    assert by["C2", "opus", "W_Q2"]["point"] == pytest.approx(12 / 20 - 2 * 1 / 20)
    assert by["C3", "haiku", "K_Q2"]["point"] == pytest.approx(8 / 20)
    assert by["C4", "opus - sonnet", "T_Q1"]["point"] == pytest.approx(6 / 20)
    assert all(r["verdict"] in {"확인", "반증", "판정 못 함"} for r in result)
