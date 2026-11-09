"""Sending, resuming and reporting the caption pilot with a fake API (spec sections 3, 6, 7 and 11)."""

import json

from test_run import FakeApi, fake_image

from vtrust import caption_run, run
from vtrust.captions import CONDITIONS

MODELS = {"haiku": "claude-haiku-5-5", "sonnet": "claude-sonnet-5-5", "opus": "claude-opus-5-5"}


def make_item(number, other=True, checkable=None):
    item = {"item_id": f"c{number:03d}", "photo": f"p{number}", "other_photo": f"o{number}" if other else None,
            "true_caption": f"T{number}", "false_caption": f"F{number}",
            "option_order": ["yes", "no", "unknown"], "true_first": number % 2 == 0}
    if checkable is not None:
        item["checkable"] = checkable
    return item


def make_config(size=8, missing=(), dataset="commons"):
    items = [make_item(n, other=n not in missing) for n in range(1, size + 1)]
    photos = {p: {"sha256": "x"} for i in items for p in (i["photo"], i["other_photo"]) if p}
    return {"seed": 1, "dataset": dataset, "models": MODELS, "effort": "medium", "max_tokens": 8000,
            "smoke_items": 6, "batch_limit_mb": 200, "results_name": f"caption_{dataset}",
            "smoke_name": f"caption_smoke_{dataset}", "items": items, "photos": photos}


def test_calls_are_items_times_conditions_times_models():
    config = make_config(size=8, missing={7})
    assert caption_run.plan(config) == {"smoke_calls": 6 * 10 * 3, "main_calls": (7 * 10 + 8) * 3}
    assert len(caption_run.build_requests(config["items"], "opus", config, fake_image)) == 7 * 10 + 8


def test_smoke_takes_the_fixed_prefix_and_main_can_be_cut():
    config = make_config()
    assert [i["item_id"] for i in caption_run.stage_items(config, "smoke")] == [f"c{n:03d}" for n in range(1, 7)]
    assert len(caption_run.stage_items(config, "main", limit=3)) == 3


def test_smoke_results_go_to_the_config_folder_and_are_not_sent_twice(tmp_path):
    config = make_config(size=2)
    first, second = FakeApi(), FakeApi()
    caption_run.send("smoke", config, tmp_path, first, fake_image)
    caption_run.send("smoke", config, tmp_path, second, fake_image)
    saved = (tmp_path / "caption_smoke_commons" / "opus.jsonl").read_text(encoding="utf-8")
    assert len(saved.splitlines()) == 20 and "xxxx" not in saved
    assert len(first.batches) == 3 and second.batches == {}
    manifest = json.loads((tmp_path / "caption_smoke_commons" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["anchors"] == 2 and manifest["conditions"] == len(CONDITIONS)
    assert not (tmp_path / "smoke").exists()


def test_same_item_folders_are_unchanged():
    assert run.stage_folder({}, "smoke") == "smoke" and run.stage_folder({}, "main") == "main"
    assert run.stage_folder({"smoke_name": "s2"}, "smoke") == "s2"


def row(**cells):
    return {c: cells.get(c) for c in CONDITIONS if c in cells}


def test_quantities_follow_section_3():
    # Four items. True caption always accepted under QM; the false caption accepted twice under QM, once under QA.
    table = {
        "c1": row(true_qm="yes", true_qa="yes", mc_qm="yes", mc_qa="yes", choose_img="true", choose_text="true"),
        "c2": row(true_qm="yes", true_qa="unknown", mc_qm="yes", mc_qa="no", choose_img="true", choose_text="false"),
        "c3": row(true_qm="yes", true_qa="yes", mc_qm="no", mc_qa="no", choose_img="false", choose_text="unknown"),
        "c4": row(true_qm="yes", true_qa="yes", mc_qm="no", mc_qa="unknown", choose_img="true", choose_text="true"),
    }
    q = caption_run.quantities(table, n_boot=200)
    assert q["base"][0] == 1.0
    assert q["R_MC QM"][0] == 0.5 and q["R_MC QA"][0] == 0.5
    assert q["M"][0] == 0.25
    assert q["G image"][0] == 0.5 and q["G text"][0] == 0.25 and q["G image - G text"][0] == 0.25
    # K: of the three items picking the true caption with the photo, two said yes to the false caption under QM.
    assert q["K"][0] == 2 / 3


def test_n_is_the_unknown_share_on_items_the_photo_cannot_check():
    table = {"c001": row(mc_qa="unknown"), "c002": row(mc_qa="no"), "c003": row(mc_qa="unknown")}
    items = [make_item(1, checkable=False), make_item(2, checkable=False), make_item(3, checkable=True)]
    assert caption_run.unknown_share(table, items, n_boot=100)[0] == 0.5


def fake_replies(config, letter_for):
    out = {}
    for model in config["models"]:
        out[model] = {}
        for item in config["items"]:
            for condition in caption_run.item_conditions(item, caption_run.config_conditions(config)):
                key = f"{model}-{item['item_id']}-{condition}"
                out[model][key] = {"stop_reason": "end_turn", "usage": {"input_tokens": 1, "output_tokens": 1},
                                   "content": [{"type": "text", "text": json.dumps({"answer": letter_for(condition)})}]}
    return out


def test_report_withholds_verdicts_when_true_captions_are_rejected():
    config = make_config(size=6)
    # Option order is yes, no, unknown, so B is "no" everywhere: the precondition fails.
    text = caption_run.report_text(config, fake_replies(config, lambda c: "B"), n_boot=100)
    assert "사전 조건을 넘지 못함" in text
    assert "| R_MC QM | +0.0%p | [+0.0%p, +0.0%p] | 판정 없음 |" in text


def test_report_reads_a_clear_effect():
    config = make_config(size=6)
    text = caption_run.report_text(config, fake_replies(config, lambda c: "B" if c.startswith("mc") else "A"),
                                   n_boot=100)
    assert "| R_MC QM | +100.0%p | [+100.0%p, +100.0%p] | 차이가 있음 |" in text


def test_smoke_gate_scales_by_calls(tmp_path):
    config = make_config(size=8, missing={7})
    stage = tmp_path / "caption_smoke_commons"
    stage.mkdir()
    for model in config["models"]:
        lines = [json.dumps({"custom_id": f"{model}-{n}", "message": {"usage": {"input_tokens": 1_000_000,
                                                                                    "output_tokens": 0}}})
                 for n in range(60)]
        (stage / f"{model}.jsonl").write_text("\n".join(lines), encoding="utf-8")
    gate = caption_run.smoke_gate(config, stage)
    smoke = (0.05 + 1.0 + 2.0) * 60
    assert abs(gate["total_smoke"] - smoke) < 1e-9
    assert abs(gate["total_main"] - smoke * 78 / 60) < 1e-9


def test_r1_main_skips_the_smoke_items():
    config = {**make_config(size=8, missing={7}), "main_from": 6}
    assert [i["item_id"] for i in caption_run.stage_items(config, "main")] == ["c007", "c008"]
    assert [i["item_id"] for i in caption_run.stage_items(config, "smoke")] == [f"c{n:03d}" for n in range(1, 7)]
    assert caption_run.plan(config) == {"smoke_calls": 6 * 10 * 3, "main_calls": (8 + 10) * 3}
    assert [i["item_id"] for i in caption_run.stage_items(config, "main", limit=1)] == ["c007"]


def test_r2_measures_rejection():
    # True captions are left as "cannot tell"; false captions are rejected more under QA than under QM.
    table = {
        "c1": row(true_qm="unknown", true_qa="unknown", mc_qm="no", mc_qa="no", ooc_qm="no", ooc_qa="no"),
        "c2": row(true_qm="unknown", true_qa="no", mc_qm="unknown", mc_qa="no", ooc_qm="unknown", ooc_qa="no"),
        "c3": row(true_qm="yes", true_qa="unknown", mc_qm="no", mc_qa="no", ooc_qm="no", ooc_qa="unknown"),
        "c4": row(true_qm="unknown", true_qa="unknown", mc_qm="yes", mc_qa="unknown", ooc_qm="no", ooc_qa="no"),
    }
    q = caption_run.quantities(table, n_boot=200, measure="no")
    assert q["base"][0] == 0.0  # no true caption rejected under QM
    assert q["R_MC QM"][0] == 0.5 and q["R_MC QA"][0] == 0.75 - 0.25
    assert q["R_OOC QM"][0] == 0.75 and q["R_OOC QA"][0] == 0.75 - 0.25
    assert q["M"][0] == 0.75 - 0.5  # QA rejects the false caption more often than QM
    assert caption_run.quantities(table, n_boot=200)["base"][0] == 0.25  # the yes share of v1 and r1


def r2_config(size=6):
    return {**make_config(size=size), "measure": "no"}


def test_r2_report_passes_when_true_captions_are_left_unknown():
    config = r2_config()
    # Option order is yes, no, unknown: C is "cannot tell", B is "no".
    text = caption_run.report_text(config, fake_replies(config, lambda c: "B" if c.startswith("mc") else "C"),
                                   n_boot=100)
    assert "맞는 캡션에 QM으로 \"아니다\"고 한 비율 0.0%. 넘음." in text
    assert "| R_MC QM | +100.0%p | [+100.0%p, +100.0%p] | 차이가 있음 |" in text
    assert "| R_MC QM (그렇다 기준) | +0.0%p | [+0.0%p, +0.0%p] | 판정 없음 |" in text


def test_r2_report_withholds_verdicts_when_true_captions_are_rejected():
    config = r2_config()
    text = caption_run.report_text(config, fake_replies(config, lambda c: "B"), n_boot=100)
    assert "사전 조건을 넘지 못함" in text
    assert "| R_MC QM | +0.0%p | [+0.0%p, +0.0%p] | 판정 없음 |" in text


def test_h6_and_h7_are_not_judged_when_the_precondition_fails():
    config = r2_config()
    text = caption_run.report_text(config, fake_replies(config, lambda c: "B"), n_boot=100)
    assert "H6 판정 없음, H7 판정 없음" in text
    rejects = caption_run.report_text(config, fake_replies(config, lambda c: "B" if c.startswith(("mc", "ooc"))
                                                           else "C"), n_boot=100)
    assert "H6 닿지 않음, H7 닿음" in rejects  # M is exactly 0 here, inside ±5%p


def confirm_table(size=40, true_qm="unknown", checkable=False):
    """Every item: true captions left unknown, false captions and other photos rejected, mc_qa unknown."""
    return {f"c{n:03d}": row(true_qm=true_qm, true_qa="unknown", mc_qm="no", mc_qa="no", ooc_qm="no", ooc_qa="no")
            for n in range(1, size + 1)}


def test_confirm_has_sixteen_judgments_in_the_spec_order():
    items = [make_item(n, checkable=False) for n in range(1, 41)]
    tables = {m: confirm_table() for m in ("haiku", "sonnet", "opus")}
    for table in tables.values():
        for key in table:
            table[key]["mc_qa"] = "unknown"  # N = 100% on the uncheckable items; R_MC QA = 0 then
    rows = caption_run.confirm_claims(items, tables, n_boot=500)
    assert len(rows) == 16 == caption_run.CAPTION_JUDGMENTS
    assert [(r["claim"], r["model"], r["value"]) for r in rows[:2]] == [("C1", "haiku", "R_MC QM"),
                                                                      ("C1", "haiku", "R_MC QA")]
    assert [r["claim"] for r in rows] == ["C1"] * 6 + ["C2"] * 6 + ["C3"] * 2 + ["C4"] * 2
    assert [r["model"] for r in rows[12:]] == ["haiku", "sonnet", "haiku", "sonnet"]
    by = {(r["claim"], r["model"], r["value"]): r for r in rows}
    assert by[("C1", "haiku", "R_MC QM")]["point"] == 1.0 and by[("C1", "haiku", "R_MC QM")]["verdict"] == "확인"
    assert by[("C1", "haiku", "R_MC QA")]["point"] == 0.0 and by[("C1", "haiku", "R_MC QA")]["verdict"] == "반증"
    assert by[("C3", "sonnet", "U")]["point"] == 1.0 and by[("C4", "haiku", "N")]["verdict"] == "확인"
    assert abs(caption_run.CAPTION_LEVEL - (1 - 0.05 / 16)) < 1e-12


def test_confirm_withholds_c1_and_c2_when_true_captions_are_rejected():
    items = [make_item(n, checkable=False) for n in range(1, 41)]
    tables = {m: confirm_table() for m in ("haiku", "sonnet")}
    tables["opus"] = confirm_table(true_qm="no")
    rows = caption_run.confirm_claims(items, tables, n_boot=500)
    opus = [r for r in rows if r["model"] == "opus"]
    assert len(opus) == 4 and all(r["verdict"] == "판정 못 함" for r in opus)
    assert all(r["verdict"] == "확인" for r in rows if r["model"] == "haiku" and r["claim"] in ("C1", "C2")
               and r["value"].endswith("QM"))


def test_share_verdict_uses_the_thirty_percent_line():
    assert caption_run.share_verdict(0.31, 0.9) == "확인"
    assert caption_run.share_verdict(0.1, 0.30) == "반증"
    assert caption_run.share_verdict(0.2, 0.5) == "판정 못 함"


def test_confirm_report_puts_the_judgments_first():
    config = {**make_config(size=6), "measure": "no", "confirm": True}
    for item in config["items"]:
        item["checkable"] = False
    text = caption_run.report_text(config, fake_replies(config, lambda c: "B" if c.startswith(("mc", "ooc"))
                                                        else "C"), n_boot=200, confirm_boot=200)
    assert text.index("## 확인 판정") < text.index("## Haiku")
    assert "| C1 | Haiku | R_MC QM | +100.0%p |" in text


def test_confirm_commons_report_has_n_and_the_schedule_split():
    # The confirmation set is Commons data, so it reports N and H8, not the VERITE H9 (spec 2026-11-08 section 5).
    config = {**make_config(size=6, dataset="commons_confirm"), "measure": "no", "confirm": True}
    for n, item in enumerate(config["items"]):
        item["checkable"] = False
        item["scheduled"] = n < 4
    text = caption_run.report_text(config, fake_replies(config, lambda c: "B" if c.startswith(("mc", "ooc"))
                                                        else "C"), n_boot=200, confirm_boot=200)
    haiku = text[text.index("## Haiku"):text.index("## Sonnet")]
    assert "H8" in haiku and "H9" not in haiku
    assert "| 일정 표시: True | 4 |" in haiku and "| 일정 표시: False | 2 |" in haiku
    assert "| N (일정 표시: True) | 0.0% |" in haiku


def test_main_needs_smoke_replies_only_when_the_config_has_a_smoke_run(tmp_path):
    assert caption_run.smoke_needed(make_config()) is True
    assert caption_run.smoke_needed({**make_config(), "smoke_items": 0}) is False


# Wording spec 2026-11-09: QM again and QC ("Does anything in the photo contradict the caption?") on six conditions.
WORDING = ["true_qm", "mc_qm", "ooc_qm", "true_qc", "mc_qc", "ooc_qc"]
QC = "Does anything in the photo contradict the caption?"


def wording_config(size=4):
    config = make_config(size=size, dataset="commons_wording")
    for n, item in enumerate(config["items"]):
        item["checkable"] = n % 2 == 0
        item["source"] = "explore" if n < size // 2 else "confirm"
    return {**config, "measure": "no", "wording": True, "smoke_items": 0, "conditions": WORDING,
            "questions": {"qm": "Does the photo show what the caption describes?", "qc": QC}}


def test_wording_config_sends_only_its_six_conditions():
    config = wording_config(size=3)
    requests = caption_run.build_requests(config["items"], "opus", config, fake_image)
    assert len(requests) == 3 * 6 and caption_run.plan(config)["main_calls"] == 3 * 6 * 3
    assert [r["custom_id"].split("-")[2] for r in requests[:6]] == WORDING
    texts = {r["custom_id"].split("-")[2]: r["params"]["messages"][0]["content"][-1]["text"] for r in requests[:6]}
    assert QC in texts["mc_qc"] and "Caption: F1" in texts["mc_qc"] and QC not in texts["mc_qm"]
    assert len(caption_run.build_requests(make_config(size=1)["items"], "opus", make_config(size=1),
                                          fake_image)) == 10  # older configs keep their ten conditions


def test_wording_quantities_read_qc_in_the_opposite_direction():
    # c1 can be checked from the photo, c2 cannot. Under QC "no" means nothing contradicts: the caption is accepted.
    table = {
        "c1": {"true_qm": "unknown", "true_qc": "no", "mc_qm": "no", "mc_qc": "yes", "ooc_qm": "no", "ooc_qc": "yes"},
        "c2": {"true_qm": "unknown", "true_qc": "no", "mc_qm": "unknown", "mc_qc": "no", "ooc_qm": "no",
               "ooc_qc": "yes"},
    }
    items = [{"item_id": "c1", "checkable": True}, {"item_id": "c2", "checkable": False}]
    q = caption_run.wording_quantities(table, items, n_boot=200)
    assert q["base QC"][0] == 0.0  # no true caption said to be contradicted
    assert q["U QM"][0] == 1.0 and q["U QC"][0] == -1.0 and q["dU"][0] == 2.0
    assert q["R_MC QM"][0] == 0.5 and q["R_MC QC"][0] == 0.5 and q["R_MC QM - QC"][0] == 0.0
    assert q["R_OOC QM"][0] == 1.0 and q["R_OOC QC"][0] == 1.0
    assert q["F QM"][0] == 0.0 and q["F QC"][0] == 1.0 and q["F QC - F QM"][0] == 1.0  # c2's false caption passes QC


def test_retest_counts_the_same_answer_against_the_earlier_run():
    table = {"x1": {"true_qm": "unknown", "mc_qm": "no", "ooc_qm": "no"},
             "x2": {"true_qm": "yes", "mc_qm": "no", "ooc_qm": None}}
    previous = {"x1": {"true_qm": "unknown", "mc_qm": "unknown", "ooc_qm": "no"},
                "x2": {"true_qm": "unknown", "mc_qm": "no", "ooc_qm": "no"}}
    same = caption_run.retest(table, previous, n_boot=200)
    assert same["true_qm"][0] == 0.5 and same["mc_qm"][0] == 0.5
    assert same["ooc_qm"][0] == 1.0 and same["ooc_qm"][3] == 1  # x2 has no new answer, so only x1 counts
    assert caption_run.retest_drift(table, previous, n_boot=200)["U QM"][0] == (0 + -2) / 2  # new minus earlier


def test_wording_report_judges_h11_and_lists_the_retest():
    config = wording_config(size=6)
    # Option order is yes, no, unknown. QM: true captions unknown (C); QC: true captions accepted ("no", B).
    replies = fake_replies(config, lambda c: "C" if c == "true_qm" else "B")
    previous = {m: {i["item_id"]: {"true_qm": "unknown", "mc_qm": "no", "ooc_qm": "no"} for i in config["items"]}
                for m in config["models"]}
    text = caption_run.report_text(config, replies, n_boot=200, previous=previous)
    haiku = text[text.index("## Haiku"):text.index("## Sonnet")]
    assert "| ΔU | +200.0%p | [+200.0%p, +200.0%p] | 차이가 있음 |" in haiku
    assert "H11의 반증 기준" in haiku and "닿지 않음" in haiku
    assert "| true_qm | 6 | 100.0% |" in haiku and "| mc_qm | 6 | 100.0% |" in haiku
    assert "| 확인할 수 있음 | 3 |" in haiku and "| 탐색 문항 | 3 |" in haiku
