"""Send the caption pilot, save the replies and write the report (caption pilot spec sections 3, 6, 7 and 11).

    python -m vtrust.caption_run plan --config configs/caption_v1_verite.json     # counts only
    python -m vtrust.caption_run smoke --config <config>                           # paid: first items of the order
    python -m vtrust.caption_run gate --config <verite> <commons>                  # smoke cost, main estimate, sum
    python -m vtrust.caption_run main --config <config> [--limit N] [--no-wait]    # paid: needs the smoke replies
    python -m vtrust.caption_run report smoke|main --config <config>               # no API call

Sending, resuming and batch sizes are the same-item code (`run.run_stage`); results go to the folders the
config names, so they never mix with the same-item results.
"""

import argparse
import json
import sys
from pathlib import Path

from vtrust import analysis, run
from vtrust.captions import CONDITIONS, build_request, item_conditions, parse_id, reply_meaning

MAX_TOTAL_COST = 40.0  # spec section 11, both datasets together
PRECONDITION = 0.5  # spec section 6: A(true, QM) below this withholds the verdicts on R and M
H8_LINE, H10_LINE = 0.30, 0.05
MEANINGS = {"single": ("yes", "no", "unknown"), "choice": ("true", "false", "unknown")}


def stage_items(config, stage, limit=None):
    """Smoke is the fixed prefix; an r1 main run starts after it (main_from), since r1 was chosen on it."""
    if stage == "smoke":
        return config["items"][: config["smoke_items"]]
    items = config["items"][config.get("main_from", 0):]
    return items[:limit] if limit else items


def config_conditions(config):
    """The wording config names its six conditions; every earlier config asks the ten of the pilot spec."""
    return config.get("conditions", CONDITIONS)


def build_requests(items, model, config, image_data):
    conditions = config_conditions(config)
    return [build_request(i, c, model, config, image_data) for i in items for c in item_conditions(i, conditions)]


def calls(items, config):
    return sum(len(item_conditions(i, config_conditions(config))) for i in items) * len(config["models"])


def plan(config):
    return {"smoke_calls": calls(stage_items(config, "smoke"), config),
            "main_calls": calls(stage_items(config, "main"), config)}


def send(stage, config, out_dir, api, image_data, revision=None, limit=None, wait=True):
    run.run_stage(stage, config, out_dir, api, image_data, revision, limit, wait, build=build_requests,
                  units=stage_items(config, stage, limit), conditions=len(config_conditions(config)))


def smoke_gate(config, stage_dir):
    """Measured smoke cost and the main run it implies, scaled by the number of calls."""
    models = {m: run.usage_summary(run.load_replies(Path(stage_dir) / f"{m}.jsonl"), m) for m in config["models"]}
    total_smoke = sum(s["cost"] for s in models.values())
    smoke_calls = plan(config)["smoke_calls"]
    return {"models": models, "total_smoke": total_smoke,
            "total_main": total_smoke * plan(config)["main_calls"] / smoke_calls}


def answer_tables(config, replies):
    """{model: {item_id: {condition: meaning}}} from the saved replies."""
    items = {i["item_id"]: i for i in config["items"]}
    tables = {}
    for model, messages in replies.items():
        table = {}
        for key, message in messages.items():
            info = parse_id(key)
            item = items[info["item_id"]]
            table.setdefault(item["item_id"], {})[info["condition"]] = reply_meaning(message, item, info["condition"])
        tables[model] = table
    return tables


def quantities(table, n_boot=analysis.N_BOOT, measure="yes"):
    """The named values of spec section 3 for one model, each as (point, low, high).

    measure "yes" (v1, r1): R and M are drops in "yes". measure "no" (spec r2): R is the rise in "no" that the
    false caption or the other photo brings, and M is how much less often QM rejects the false caption than QA.
    Both read positive in the direction of H6 and H7. "base" is the share the precondition looks at.
    """
    c = analysis.contrast
    sign = 1 if measure == "yes" else -1

    def drop(before, after):
        return [(before, measure, sign), (after, measure, -sign)]

    out = {"base": c(table, [("true_qm", measure, 1)], n_boot=n_boot)}
    for w in ("qm", "qa"):
        out[f"R_MC {w.upper()}"] = c(table, drop(f"true_{w}", f"mc_{w}"), n_boot=n_boot)
        out[f"R_OOC {w.upper()}"] = c(table, drop(f"true_{w}", f"ooc_{w}"), n_boot=n_boot)
    out["M"] = c(table, drop("mc_qm", "mc_qa"), n_boot=n_boot)  # yes(QM) - yes(QA), or no(QA) - no(QM)
    g_img = [("choose_img", "true", 1), ("choose_img", "false", -1)]
    g_text = [("choose_text", "true", 1), ("choose_text", "false", -1)]
    out["G image"] = c(table, g_img, n_boot=n_boot)
    out["G text"] = c(table, g_text, n_boot=n_boot)
    out["G image - G text"] = c(table, g_img + [(cell, m, -w) for cell, m, w in g_text], n_boot=n_boot)
    out["K"] = analysis.conditional_share(table, "choose_img", "true", "mc_qm", "yes", n_boot=n_boot)
    return out


def unknown_share(table, items, n_boot=analysis.N_BOOT, cell="mc_qa", seed=0, level=0.95):
    """N of spec section 3: "cannot tell" on the items whose changed fact the photo cannot check."""
    ids = {i["item_id"] for i in items if i.get("checkable") is False}
    return analysis.contrast(analysis.subset(table, ids), [(cell, "unknown", 1)], n_boot=n_boot, seed=seed,
                             level=level)


# Confirmation spec 2026-11-08-caption-confirm section 2: sixteen judgments under one Bonferroni level.
CAPTION_JUDGMENTS = 16
CAPTION_LEVEL = 1 - 0.05 / CAPTION_JUDGMENTS
CONFIRM_MODELS = ("haiku", "sonnet", "opus")


def share_verdict(low, high, line=H8_LINE):
    """C4 predicts a share above the line (30%, the H8 line of the exploration spec)."""
    if low > line:
        return "확인"
    if high <= line:
        return "반증"
    return "판정 못 함"


def _withheld(point, low, high):
    return "판정 못 함"


def confirm_claims(items, tables, n_boot=analysis.CONFIRM_N_BOOT, seed=0, level=CAPTION_LEVEL):
    """C1 and C2: rise in "no" (R) per model and question; C3: U for Haiku and Sonnet; C4: N for both."""
    c, rows = analysis.contrast, []

    def add(claim, model, value, result, judge):
        point, low, high = result
        rows.append({"claim": claim, "model": model, "value": value, "point": point, "low": low, "high": high,
                     "verdict": None if point is None else judge(point, low, high)})

    for claim, kind, label in (("C1", "mc", "R_MC"), ("C2", "ooc", "R_OOC")):
        for model in CONFIRM_MODELS:
            base = c(tables[model], [("true_qm", "no", 1)], n_boot=1)[0]
            judge = analysis.claim_verdict if base is not None and base < PRECONDITION else _withheld
            for w in ("qm", "qa"):
                terms = [(f"{kind}_{w}", "no", 1), (f"true_{w}", "no", -1)]
                add(claim, model, f"{label} {w.upper()}", c(tables[model], terms, n_boot=n_boot, seed=seed,
                                                             level=level), judge)
    for model in ("haiku", "sonnet"):
        add("C3", model, "U", c(tables[model], [("true_qm", "unknown", 1), ("true_qm", "yes", -1)],
                                n_boot=n_boot, seed=seed, level=level), analysis.claim_verdict)
    for model in ("haiku", "sonnet"):
        add("C4", model, "N", unknown_share(tables[model], items, n_boot=n_boot, seed=seed, level=level),
            lambda point, low, high: share_verdict(low, high))
    assert len(rows) == CAPTION_JUDGMENTS
    return rows


def _confirm_lines(config, tables, n_boot):
    lines = ["## 확인 판정", "",
             "설계서 `specs/2026-11-08-caption-confirm.md` 2절의 판정이다. 구간은 Bonferroni로 보정한 "
             f"{100 * CAPTION_LEVEL:.2f}% 구간이고 문항을 {n_boot:,}번 다시 뽑았다. C1과 C2는 맞는 캡션을 QM에서 "
             "\"아니다\"로 거른 비율이 50% 이상인 모델에서 판정하지 않는다.", "",
             "| 주장 | 모델 | 값 | 점추정 | 보정 구간 | 판정 |", "| --- | --- | --- | --- | --- | --- |"]
    for r in confirm_claims(config["items"], tables, n_boot=n_boot):
        fmt = _percent if r["value"] == "N" else _points
        lines.append(f"| {r['claim']} | {run.LABELS[r['model']]} | {r['value']} | {fmt(r['point'])} | "
                     f"[{fmt(r['low'])}, {fmt(r['high'])}] | {r['verdict'] or '없음'} |")
    return lines + [""]


def _points(value):
    return "없음" if value is None else f"{100 * value:+.1f}%p"


def _percent(value):
    return "없음" if value is None else f"{100 * value:.1f}%"


def _row(label, values, judged=True):
    point, low, high = values
    if point is None:
        return f"| {label} | 없음 | | |"
    reading = analysis.verdict(point, low, high) if judged else "판정 없음"
    return f"| {label} | {_points(point)} | [{_points(low)}, {_points(high)}] | {reading} |"


def _small_or_below(values):
    """Spec section 2: the interval lies inside ±5%p, or below -5%p."""
    point, low, high = values
    return point is not None and ((-analysis.MIN_EFFECT < low and high < analysis.MIN_EFFECT)
                                  or high < -analysis.MIN_EFFECT)


def _share_row(label, values, line):
    point, low, high = values
    if point is None:
        return f"| {label} | 없음 | | {line} |"
    return f"| {label} | {_percent(point)} | [{_percent(low)}, {_percent(high)}] | {line} |"


def _split_rows(config, table, key, label, n_boot):
    rows = []
    for value in (True, False):
        ids = {i["item_id"] for i in config["items"] if i.get(key) is value}
        part = analysis.subset(table, ids)
        if not part:
            continue
        q = quantities(part, n_boot=n_boot, measure=config.get("measure", "yes"))
        cells = " | ".join(f"{_points(q[name][0])} [{_points(q[name][1])}, {_points(q[name][2])}]"
                           if q[name][0] is not None else "없음" for name in ("R_MC QM", "R_MC QA", "M"))
        rows.append(f"| {label}: {value} | {len(part)} | {cells} |")
    return rows


def _model_lines(config, model, table, n_boot):
    given = sum(v is not None for row in table.values() for v in row.values())
    total = sum(len(row) for row in table.values())
    measure = config.get("measure", "yes")
    q = quantities(table, n_boot=n_boot, measure=measure)
    base = q["base"][0]
    # v1 and r1: true captions accepted at least half the time. r2: true captions rejected less than half the time.
    passed = base is not None and (base >= PRECONDITION if measure == "yes" else base < PRECONDITION)
    word = "그렇다" if measure == "yes" else "아니다"
    lines = [f"## {run.LABELS[model]}", "", f"문항 {len(table)}개, 호출 {total}번, 답 없음 {total - given}번.", "",
             f"사전 조건: 맞는 캡션에 QM으로 \"{word}\"고 한 비율 {_percent(base)}. "
             + ("사전 조건 충족." if passed else "사전 조건을 충족하지 못함. R과 M은 판정 없이 적는다."), "",
             "| 값 | 차이 | 95% 구간 | 판정 |", "| --- | --- | --- | --- |"]
    names = ("R_MC QM", "R_MC QA", "R_OOC QM", "R_OOC QA", "M")
    for name in names:
        lines.append(_row(name, q[name], judged=passed))
    if measure == "no":
        yes = quantities(table, n_boot=n_boot)
        for name in names:
            lines.append(_row(f"{name} (그렇다 기준)", yes[name], judged=False))
    for name in ("G image", "G text", "G image - G text"):
        lines.append(_row(name, q[name]))
    lines += ["", "| 비율 | 값 | 95% 구간 | 가설의 기준 |", "| --- | --- | --- | --- |"]
    k = q["K"]
    lines.append(_share_row("K", k, "H10: 상한이 5%보다 낮으면 반증"
                            + (" → 반증" if k[0] is not None and k[2] < H10_LINE else "")))
    hypotheses = [  # H6 and H7 read R and M, so they are not judged when the precondition fails (section 6)
        ("H6", any(_small_or_below(q[n]) for n in ("R_MC QM", "R_MC QA", "R_OOC QM", "R_OOC QA")) if passed
         else None),
        ("H7", _small_or_below(q["M"]) if passed else None),
        ("H10", k[0] is not None and k[2] < H10_LINE),
    ]
    if config["dataset"].startswith("commons"):  # commons and commons_confirm
        n = unknown_share(table, config["items"], n_boot=n_boot)
        lines.append(_share_row("N (확인할 수 없는 문항, 틀림 QA의 알 수 없다)", n,
                                "H8: 하한이 30%보다 높으면 반증"
                                + (" → 반증" if n[0] is not None and n[1] > H8_LINE else "")))
        lines.append(_share_row("참 QA의 알 수 없다 (확인할 수 없는 문항)",
                                unknown_share(table, config["items"], n_boot=n_boot, cell="true_qa"), "판정 없음"))
        for value in (True, False):  # schedule mark of the confirmation date items (spec 2026-11-08 section 3)
            marked = [i for i in config["items"] if i.get("scheduled") is value]
            if marked:
                lines.append(_share_row(f"N (일정 표시: {value})", unknown_share(table, marked, n_boot=n_boot),
                                        "판정 없음"))
        hypotheses.insert(2, ("H8", n[0] is not None and n[1] > H8_LINE))
    else:
        g_text = q["G text"]
        hypotheses.insert(2, ("H9", g_text[0] is not None and -analysis.MIN_EFFECT < g_text[1]
                              and g_text[2] < analysis.MIN_EFFECT))
    lines += ["", "가설의 반증 기준(설계서 2절)에 닿았는가: "
              + ", ".join(f"{h} {'판정 없음' if hit is None else '닿음' if hit else '닿지 않음'}"
                          for h, hit in hypotheses)
              + ". H6은 네 값 가운데 하나라도 닿으면 닿음으로 적는다.", ""]
    lines += ["판정 없이 적는 값이다.", "", "| 묶음 | 문항 | R_MC QM | R_MC QA | M |",
              "| --- | --- | --- | --- | --- |"]
    lines += _split_rows(config, table, "checkable", "사진으로 확인할 수 있음", n_boot)
    lines += _split_rows(config, table, "text_in_photo", "사진에 글자", n_boot)
    lines += _split_rows(config, table, "scheduled", "일정 표시", n_boot)
    lines += ["", "| 조건 | 첫째 답 | 둘째 답 | 알 수 없다 |", "| --- | --- | --- | --- |"]
    for condition in CONDITIONS:
        first, second, unknown = MEANINGS["choice" if condition.startswith("choose") else "single"]
        shares = [analysis.contrast(table, [(condition, m, 1)], n_boot=1)[0] for m in (first, second, unknown)]
        lines.append(f"| {condition} | {first} {_percent(shares[0])} | {second} {_percent(shares[1])} | "
                     f"{_percent(shares[2])} |")
    return lines + [""]


# Wording spec 2026-11-09-caption-wording section 3: which answer accepts and which rejects under each question.
ACCEPT = {"qm": "yes", "qc": "no"}
REJECT = {"qm": "no", "qc": "yes"}
RETEST = ("true_qm", "mc_qm", "ooc_qm")


def wording_quantities(table, items, n_boot=analysis.N_BOOT):
    """U, ΔU, R and F of the wording spec for one model, each as (point, low, high)."""
    c = analysis.contrast

    def u(w, sign=1):
        return [(f"true_{w}", "unknown", sign), (f"true_{w}", ACCEPT[w], -sign)]

    def r(pair, w, sign=1):
        return [(f"{pair}_{w}", REJECT[w], sign), (f"true_{w}", REJECT[w], -sign)]

    def f(w, sign=1):
        return [(f"mc_{w}", ACCEPT[w], sign)]

    hidden = analysis.subset(table, {i["item_id"] for i in items if i.get("checkable") is False})
    out = {"base QC": c(table, [("true_qc", REJECT["qc"], 1)], n_boot=n_boot),
           "U QM": c(table, u("qm"), n_boot=n_boot), "U QC": c(table, u("qc"), n_boot=n_boot),
           "dU": c(table, u("qm") + u("qc", -1), n_boot=n_boot)}
    for pair in ("mc", "ooc"):
        name = f"R_{pair.upper()}"
        out[f"{name} QM"] = c(table, r(pair, "qm"), n_boot=n_boot)
        out[f"{name} QC"] = c(table, r(pair, "qc"), n_boot=n_boot)
        out[f"{name} QM - QC"] = c(table, r(pair, "qm") + r(pair, "qc", -1), n_boot=n_boot)
    out["F QM"] = c(hidden, f("qm"), n_boot=n_boot)
    out["F QC"] = c(hidden, f("qc"), n_boot=n_boot)
    out["F QC - F QM"] = c(hidden, f("qc") + f("qm", -1), n_boot=n_boot)
    return out


def retest(table, previous, n_boot=analysis.N_BOOT):
    """S_c: share of items whose answer to the asked-again QM condition equals the earlier run's answer.

    Each value is (point, low, high, items compared)."""
    out = {}
    for cell in RETEST:
        same = {k: {"same": "yes" if row[cell] == previous[k][cell] else "no"} for k, row in table.items()
                if row.get(cell) is not None and previous.get(k, {}).get(cell) is not None}
        out[cell] = analysis.contrast(same, [("same", "yes", 1)], n_boot=n_boot) + (len(same),)
    return out


def retest_drift(table, previous, n_boot=analysis.N_BOOT):
    """This run minus the earlier run, item by item, for U and R_MC under QM."""
    joined = {k: {**row, **{f"old_{c}": previous[k].get(c) for c in RETEST}} for k, row in table.items()
              if k in previous}
    u = [("true_qm", "unknown", 1), ("true_qm", "yes", -1), ("old_true_qm", "unknown", -1), ("old_true_qm", "yes", 1)]
    r = [("mc_qm", "no", 1), ("true_qm", "no", -1), ("old_mc_qm", "no", -1), ("old_true_qm", "no", 1)]
    return {"U QM": analysis.contrast(joined, u, n_boot=n_boot), "R_MC QM": analysis.contrast(joined, r, n_boot=n_boot)}


WORDING_LABELS = {"U QM": "U (QM)", "U QC": "U (QC)", "dU": "ΔU", "R_MC QM": "R_MC (QM)", "R_MC QC": "R_MC (QC)",
                  "R_MC QM - QC": "R_MC (QM - QC)", "R_OOC QM": "R_OOC (QM)", "R_OOC QC": "R_OOC (QC)",
                  "R_OOC QM - QC": "R_OOC (QM - QC)", "F QC - F QM": "F (QC - QM)"}
WORDING_SPLITS = (("checkable", True, "확인할 수 있음"), ("checkable", False, "확인할 수 없음"),
                  ("source", "explore", "탐색 문항"), ("source", "confirm", "확인 문항"))


def _wording_lines(config, model, table, previous, n_boot):
    given = sum(v is not None for row in table.values() for v in row.values())
    total = sum(len(row) for row in table.values())
    q = wording_quantities(table, config["items"], n_boot=n_boot)
    base = q["base QC"][0]
    passed = base is not None and base < PRECONDITION
    lines = [f"## {run.LABELS[model]}", "", f"문항 {len(table)}개, 호출 {total}번, 답 없음 {total - given}번.", "",
             f"사전 조건: 맞는 캡션에 QC로 \"어긋난다\"(Yes)고 한 비율 {_percent(base)}. "
             + ("사전 조건 충족." if passed else "사전 조건을 충족하지 못함. QC 값은 판정 없이 적는다."), "",
             "| 값 | 차이 | 95% 구간 | 판정 |", "| --- | --- | --- | --- |"]
    for name, label in WORDING_LABELS.items():
        lines.append(_row(label, q[name], judged=passed or name in ("U QM", "R_MC QM", "R_OOC QM")))
    lines += ["", "| 비율 | 값 | 95% 구간 | 기준 |", "| --- | --- | --- | --- |",
              _share_row("F (QM), 확인할 수 없는 틀린 캡션을 받아들임", q["F QM"], "판정 없음"),
              _share_row("F (QC), 확인할 수 없는 틀린 캡션을 받아들임", q["F QC"], "판정 없음")]
    du = q["dU"]
    hit = None if not passed or du[0] is None else du[2] < analysis.MIN_EFFECT
    lines += ["", "H11의 반증 기준(ΔU의 95% 구간 전체가 +5%p 아래)에 닿았는가: "
              + ("판정 없음" if hit is None else "닿음" if hit else "닿지 않음") + ".", ""]
    lines += ["판정 없이 적는 값이다.", "", "| 묶음 | 문항 | U (QM) | U (QC) | ΔU | R_MC (QC) |",
              "| --- | --- | --- | --- | --- | --- |"]
    for key, value, label in WORDING_SPLITS:
        ids = {i["item_id"] for i in config["items"] if i.get(key) == value}
        part = analysis.subset(table, ids)
        if not part:
            continue
        s = wording_quantities(part, config["items"], n_boot=n_boot)
        cells = " | ".join(f"{_points(s[n][0])} [{_points(s[n][1])}, {_points(s[n][2])}]"
                           if s[n][0] is not None else "없음" for n in ("U QM", "U QC", "dU", "R_MC QC"))
        lines.append(f"| {label} | {len(part)} | {cells} |")
    if previous is not None:
        lines += ["", "다시 묻기: 앞선 실행(탐색 문항은 시스템 문장의 날짜가 하루 앞섬)과 "
                  "답이 같은 문항의 비율이다.", "",
                  "| 조건 | 문항 | 같은 답 | 95% 구간 |", "| --- | --- | --- | --- |"]
        for cell, (point, low, high, n) in retest(table, previous, n_boot=n_boot).items():
            lines.append(f"| {cell} | {n} | {_percent(point)} | [{_percent(low)}, {_percent(high)}] |")
        lines += ["", "| 값 (이번 빼기 앞선 실행) | 차이 | 95% 구간 | 판정 |", "| --- | --- | --- | --- |"]
        for name, values in retest_drift(table, previous, n_boot=n_boot).items():
            lines.append(_row(name, values))
    lines += ["", "| 조건 | yes | no | 알 수 없다 |", "| --- | --- | --- | --- |"]
    for condition in config_conditions(config):
        shares = [analysis.contrast(table, [(condition, m, 1)], n_boot=1)[0] for m in MEANINGS["single"]]
        lines.append(f"| {condition} | {' | '.join(_percent(s) for s in shares)} |")
    return lines + ["QC에서는 yes가 거름(어긋난다), no가 받아들임이다.", ""]


def previous_tables(root, config):
    """{model: {wording item id: {condition: meaning}}} from the earlier runs the wording items came from."""
    out = {m: {} for m in config["models"]}
    for prefix, source in config["previous"].items():
        old = json.loads((root / source["config"]).read_text(encoding="utf-8"))
        folder = root / "results" / source["results"]
        replies = {m: run.load_replies(folder / f"{m}.jsonl") for m in config["models"]}
        for model, table in answer_tables(old, replies).items():
            out[model].update({prefix + key: row for key, row in table.items()})
    return out


def report_text(config, replies, n_boot=analysis.N_BOOT, confirm_boot=analysis.CONFIRM_N_BOOT, previous=None):
    tables = answer_tables(config, replies)
    if config.get("wording"):
        lines = ["# 결과 표", "", "설계서 `specs/2026-11-09-caption-wording.md` 3절의 값이다. "
                 "탐색 결과이고 확인된 결과로 쓰지 않는다. 구간은 문항을 다시 뽑은 95% 구간이다.", ""]
        for model, table in tables.items():
            lines += _wording_lines(config, model, table, None if previous is None else previous[model], n_boot)
        return "\n".join(lines) + "\n"
    lines = ["# 결과 표", ""]
    if config.get("confirm"):
        lines += _confirm_lines(config, tables, confirm_boot)
        lines += ["아래 모델별 표는 탐색 설계서와 같은 값이다. 판정 없이 탐색으로 읽는다.", ""]
    lines += [f"데이터: {config['dataset']}. 탐색 결과다. 확인된 결과로 쓰지 않는다. "
              "값의 정의는 설계서 `specs/2026-11-04-caption-pilot.md` 3절에 있다.", ""]
    for model, table in tables.items():
        lines += _model_lines(config, model, table, n_boot)
    return "\n".join(lines) + "\n"


def smoke_needed(config):
    """The confirmation config has no smoke run (spec 2026-11-08 section 6); every other config does."""
    return config["smoke_items"] > 0


def _received(results, config, stage):
    folder = results / run.stage_folder(config, stage)
    return all((folder / f"{m}.jsonl").exists() for m in config["models"])


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["plan", "smoke", "gate", "main", "report"])
    parser.add_argument("stage", nargs="?", choices=["smoke", "main"])
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--config", nargs="+", required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--no-wait", action="store_true", help="보내고 끝난 것만 받은 뒤 바로 끝낸다")
    args = parser.parse_args(argv)
    configs = [json.loads((args.root / c).read_text(encoding="utf-8")) for c in args.config]
    if args.command != "gate" and len(configs) != 1:
        raise SystemExit("gate 말고는 설정 파일을 하나만 줍니다.")
    config, results = configs[0], args.root / "results"

    if args.command == "plan":
        print(plan(config), "문항", len(config["items"]))
    elif args.command == "gate":
        total = 0.0
        for path, each in zip(args.config, configs, strict=True):
            gate = smoke_gate(each, results / run.stage_folder(each, "smoke"))
            total += gate["total_main"]
            print(path, json.dumps(gate, ensure_ascii=False, indent=1))
        print(f"본 실행 어림 합계 ${total:.2f}.",
              "$40를 넘습니다. 멈추고 VERITE 문항 수를 줄입니다." if total > MAX_TOTAL_COST else "$40 이하입니다.")
    elif args.command == "report":
        folder = results / run.stage_folder(config, args.stage)
        saved = [m for m in config["models"] if (folder / f"{m}.jsonl").exists()]
        previous = previous_tables(args.root, config) if config.get("wording") else None
        text = report_text(config, {m: run.load_replies(folder / f"{m}.jsonl") for m in saved}, previous=previous)
        (folder / "report.md").write_text(text, encoding="utf-8")
        print(text)
    else:
        from vtrust.batches import BatchApi

        if args.command == "main" and smoke_needed(config) and not _received(results, config, "smoke"):
            raise SystemExit("시험 실행 결과가 없어 본 실행을 시작하지 않습니다.")
        reader = run.image_reader(args.root / "data" / "captions" / "photos", config["photos"])
        send(args.command, config, results, BatchApi(), reader, run._revision(args.root), args.limit,
             not args.no_wait)
        if args.command == "smoke" and _received(results, config, "smoke"):
            print(json.dumps(smoke_gate(config, results / run.stage_folder(config, "smoke")), ensure_ascii=False,
                             indent=1))


if __name__ == "__main__":
    main()
