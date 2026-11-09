"""Quantities of spec section 3 and the reading rule of section 6.

Answers are {pair_id: {(relation, name, question): meaning}}, one table per model. A meaning is
same, different, unknown or None when the reply had no usable answer.
"""

import random

MIN_EFFECT = 0.05
N_BOOT = 10000
# Confirmation spec (2026-11-04) section 2: eleven judgments share 5%, and more resamples for the narrow tails.
CONFIRM_JUDGMENTS = 11
BONFERRONI_LEVEL = 1 - 0.05 / CONFIRM_JUDGMENTS
CONFIRM_N_BOOT = 100_000


def rate(answers, cell):
    """Share of anchors answering "same" in `cell`, among those that gave an answer."""
    given = [row[cell] for row in answers.values() if row.get(cell) is not None]
    return sum(meaning == "same" for meaning in given) / len(given) if given else None


def unknown_rate(answers, cell):
    given = [row[cell] for row in answers.values() if row.get(cell) is not None]
    return sum(meaning == "unknown" for meaning in given) / len(given) if given else None


def _interval(values, n_boot, seed, level=0.95):
    """Mean with a percentile interval at `level`, resampling anchors with replacement."""
    if not values:
        return None, None, None
    rng = random.Random(seed)
    size = len(values)
    draws = sorted(sum(rng.choices(values, k=size)) / size for _ in range(n_boot))
    # Rounded so that level 0.95 picks exactly the pilot's positions (0.025 and 0.975 of n_boot).
    tail = round((1 - level) / 2, 12)
    low = draws[int(tail * n_boot)]
    high = draws[min(n_boot - 1, int((1 - tail) * n_boot))]
    return sum(values) / size, low, high


def _is_same(row, cell):
    return row[cell] == "same"


def effect(answers, plus, minus, n_boot=N_BOOT, seed=0, level=0.95):
    """S(plus) - S(minus) on the anchors answering both, as (difference, low, high)."""
    values = [
        _is_same(row, plus) - _is_same(row, minus)
        for row in answers.values()
        if row.get(plus) is not None and row.get(minus) is not None
    ]
    return _interval(values, n_boot, seed, level)


def contrast(answers, terms, n_boot=N_BOOT, seed=0, level=0.95):
    """Mean over anchors of sum(weight * [answer in cell == meaning]) for (cell, meaning, weight) terms.

    Only anchors answering every cell count. W and K of the confirmation spec are contrasts of this form.
    """
    cells = {cell for cell, _, _ in terms}
    values = [
        sum(weight * (row[cell] == meaning) for cell, meaning, weight in terms)
        for row in answers.values()
        if all(row.get(cell) is not None for cell in cells)
    ]
    return _interval(values, n_boot, seed, level)


def conditional_share(answers, given, given_meaning, cell, meaning, n_boot=N_BOOT, seed=0, level=0.95):
    """Among anchors answering `given_meaning` in `given`, the share answering `meaning` in `cell`."""
    values = [
        row[cell] == meaning
        for row in answers.values()
        if row.get(given) == given_meaning and row.get(cell) is not None
    ]
    return _interval(values, n_boot, seed, level)


def model_difference(first, second, plus, minus, n_boot=N_BOOT, seed=0, level=0.95):
    """The effect in `first` minus the effect in `second`, anchor by anchor."""
    values = []
    for pair, row in first.items():
        other = second.get(pair, {})
        cells = [row.get(plus), row.get(minus), other.get(plus), other.get(minus)]
        if all(cell is not None for cell in cells):
            values.append(
                (_is_same(row, plus) - _is_same(row, minus)) - (_is_same(other, plus) - _is_same(other, minus))
            )
    return _interval(values, n_boot, seed, level)


def double_difference(answers, a, b, c, d, n_boot=N_BOOT, seed=0):
    """(S(a) - S(b)) - (S(c) - S(d)) on the anchors answering all four, as (difference, low, high)."""
    values = [
        (_is_same(row, a) - _is_same(row, b)) - (_is_same(row, c) - _is_same(row, d))
        for row in answers.values()
        if all(row.get(cell) is not None for cell in (a, b, c, d))
    ]
    return _interval(values, n_boot, seed)


def flip_rate(answers, without_name, with_name):
    """Among anchors answering "same" without a name, the share that changed; and their number."""
    eligible = [
        row[with_name]
        for row in answers.values()
        if row.get(without_name) == "same" and row.get(with_name) is not None
    ]
    changed = sum(meaning != "same" for meaning in eligible)
    return (changed / len(eligible) if eligible else None), len(eligible)


def subset(answers, pair_ids):
    return {pair: row for pair, row in answers.items() if pair in pair_ids}


def verdict(point, low, high):
    """The table of spec section 6, read from the top."""
    if -MIN_EFFECT < low and high < MIN_EFFECT:
        return "차이가 작음"
    if abs(point) >= MIN_EFFECT and (low > 0 or high < 0):
        return "차이가 있음"
    return "알 수 없음"


def claim_verdict(point, low, high):
    """Confirmation spec section 2: every claim predicts a value above zero."""
    if point >= MIN_EFFECT and low > 0:
        return "확인"
    if high < MIN_EFFECT:
        return "반증"
    return "판정 못 함"


_NONE_Q1, _DIFF_Q1 = ("same", "none", "q1"), ("same", "different", "q1")
_NONE_Q2, _DIFF_Q2 = ("same", "none", "q2"), ("same", "different", "q2")
_SELLER = ("same", "seller", "q1")
_T_Q1 = [(_NONE_Q1, "same", 1), (_DIFF_Q1, "same", -1)]
_T_Q2 = [(_NONE_Q2, "same", 1), (_DIFF_Q2, "same", -1)]
# W = T_Q1 - 2 T_Q2 and W_P = T_Q1 - 2 P: positive when more than half of the Q1 effect is gone.
_W_Q2 = _T_Q1 + [(_NONE_Q2, "same", -2), (_DIFF_Q2, "same", 2)]
_W_P = _T_Q1 + [(_NONE_Q1, "same", -2), (_SELLER, "same", 2)]
# K: rise in "cannot tell" minus rise in "different" when the name changes.
_K_Q2 = [(_DIFF_Q2, "unknown", 1), (_NONE_Q2, "unknown", -1), (_DIFF_Q2, "different", -1), (_NONE_Q2, "different", 1)]
_K_P = [(_SELLER, "unknown", 1), (_NONE_Q1, "unknown", -1), (_SELLER, "different", -1), (_NONE_Q1, "different", 1)]
CLAIMS = [
    ("C1", "haiku", "T_Q1", _T_Q1), ("C1", "sonnet", "T_Q1", _T_Q1), ("C1", "opus", "T_Q1", _T_Q1),
    ("C2", "sonnet", "W_Q2", _W_Q2), ("C2", "sonnet", "W_P", _W_P),
    ("C2", "opus", "W_Q2", _W_Q2), ("C2", "opus", "W_P", _W_P),
    ("C3", "haiku", "T_Q2", _T_Q2), ("C3", "haiku", "K_Q2", _K_Q2), ("C3", "haiku", "K_P", _K_P),
]


def confirm_claims(tables, n_boot=CONFIRM_N_BOOT, seed=0, level=BONFERRONI_LEVEL):
    """The eleven judgments of the confirmation spec, in its order, each with a Bonferroni interval."""
    out = []
    for claim, model, value, terms in CLAIMS:
        point, low, high = contrast(tables[model], terms, n_boot=n_boot, seed=seed, level=level)
        out.append({"claim": claim, "model": model, "value": value, "point": point, "low": low, "high": high})
    point, low, high = model_difference(tables["opus"], tables["sonnet"], _NONE_Q1, _DIFF_Q1,
                                        n_boot=n_boot, seed=seed, level=level)
    out.append({"claim": "C4", "model": "opus - sonnet", "value": "T_Q1", "point": point, "low": low, "high": high})
    assert len(out) == CONFIRM_JUDGMENTS
    for row in out:
        row["verdict"] = None if row["point"] is None else claim_verdict(row["point"], row["low"], row["high"])
    return out
