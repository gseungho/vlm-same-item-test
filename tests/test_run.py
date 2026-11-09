"""Sending, resuming and reporting, with a fake API so no money is spent."""

import json

import pytest

from vtrust import run
from vtrust.conditions import CONDITIONS, custom_id

MODELS = {"haiku": "claude-haiku-5-5", "sonnet": "claude-sonnet-5-5", "opus": "claude-opus-5-5"}


def make_anchor(number, kind="SHOES", closeness="close"):
    return {
        "pair_id": f"p{number:03d}", "kind": kind, "brand": "Klepe", "other_brand": "Bourge", "famous_brand": "Gucci",
        "a1": f"a1_{number}", "a2": f"a2_{number}", "c": f"c_{number}", "closeness": closeness,
        "anchor_first": number % 2 == 0, "name_line_first": number % 3 == 0,
        "option_order": ["same", "different", "unknown"],
    }


def make_config(size=8, limit_mb=200):
    anchors = [make_anchor(n) for n in range(1, size + 1)]
    photos = {a[s]: {"sha256": "x", "width": 1000, "height": 700} for a in anchors for s in ("a1", "a2", "c")}
    return {
        "seed": 1, "models": MODELS, "effort": "medium", "max_tokens": 8000, "smoke_anchors": 6,
        "batch_limit_mb": limit_mb, "anchors": anchors, "photos": photos,
    }


def fake_image(_photo):
    return "x" * 1000


class FakeApi:
    def __init__(self, answer="A", done=True):
        self.answer = answer
        self.done = done
        self.batches = {}

    def submit(self, requests):
        batch_id = f"batch_{len(self.batches)}"
        self.batches[batch_id] = [r["custom_id"] for r in requests]
        return batch_id

    def ended(self, batch_id):
        return self.done

    def wait(self, batch_id):
        if not self.done:
            raise AssertionError("waited on a batch that is still running")

    def collect(self, batch_id):
        replies = {
            custom: {
                "stop_reason": "end_turn",
                "content": [{"type": "text", "text": json.dumps({"answer": self.answer})}],
                "usage": {"input_tokens": 2000, "output_tokens": 300},
            }
            for custom in self.batches[batch_id]
        }
        return replies, {}


def test_stage_anchors_take_the_fixed_prefix():
    config = make_config()
    assert [a["pair_id"] for a in run.stage_anchors(config, "smoke")] == [f"p{n:03d}" for n in range(1, 7)]
    assert len(run.stage_anchors(config, "main")) == 8


def test_main_can_be_cut_to_the_front_of_the_fixed_order():
    assert [a["pair_id"] for a in run.stage_anchors(make_config(), "main", limit=2)] == ["p001", "p002"]


def test_requests_cover_every_condition_for_every_model():
    requests = run.build_requests(make_config(size=2)["anchors"], "opus", make_config(size=2), fake_image)
    assert len(requests) == 2 * 17
    assert len({r["custom_id"] for r in requests}) == 2 * 17


def test_chunks_stay_under_the_size_limit():
    requests = [{"custom_id": str(n), "params": {"blob": "x" * 400_000}} for n in range(10)]
    chunks = run.split_by_size(requests, limit_bytes=1_000_000)
    assert sum(len(c) for c in chunks) == 10
    assert len(chunks) == 5
    assert all(len(json.dumps(c)) <= 1_000_000 for c in chunks)


def test_single_request_above_the_limit_is_an_error():
    with pytest.raises(ValueError):
        run.split_by_size([{"custom_id": "1", "params": {"blob": "x" * 2000}}], limit_bytes=1000)


def test_stage_saves_replies_without_photo_data(tmp_path):
    config = make_config(size=2)
    run.run_stage("smoke", config, tmp_path, FakeApi(), fake_image)
    saved = (tmp_path / "smoke" / "opus.jsonl").read_text(encoding="utf-8")
    assert len(saved.splitlines()) == 2 * 17
    assert "xxxx" not in saved


def test_rerun_does_not_send_again(tmp_path):
    config = make_config(size=2)
    first = FakeApi()
    run.run_stage("smoke", config, tmp_path, first, fake_image)
    second = FakeApi()
    run.run_stage("smoke", config, tmp_path, second, fake_image)
    assert len(first.batches) == 3 and second.batches == {}


def test_every_model_is_sent_before_any_wait(tmp_path):
    events = []

    class Recording(FakeApi):
        def submit(self, requests):
            events.append("submit")
            return super().submit(requests)

        def wait(self, batch_id):
            events.append("wait")

    run.run_stage("smoke", make_config(size=2), tmp_path, Recording(), fake_image)
    assert events == ["submit"] * 3 + ["wait"] * 3


def test_interrupted_run_resumes_without_paying_twice(tmp_path):
    config = make_config(size=2)

    class Failing(FakeApi):
        def wait(self, batch_id):
            raise KeyboardInterrupt

    api = Failing()
    with pytest.raises(KeyboardInterrupt):
        run.run_stage("smoke", config, tmp_path, api, fake_image)
    assert len(api.batches) == 3

    resumed = FakeApi()
    resumed.batches = dict(api.batches)
    run.run_stage("smoke", config, tmp_path, resumed, fake_image)
    assert len(resumed.batches) == 3
    assert all((tmp_path / "smoke" / f"{m}.jsonl").exists() for m in MODELS)


def test_no_wait_sends_everything_and_leaves_running_batches(tmp_path):
    api = FakeApi(done=False)
    run.run_stage("smoke", make_config(size=2), tmp_path, api, fake_image, wait=False)
    assert len(api.batches) == 3
    assert not any((tmp_path / "smoke" / f"{m}.jsonl").exists() for m in MODELS)


def test_no_wait_rerun_collects_ended_batches_without_sending_again(tmp_path):
    config = make_config(size=2)
    api = FakeApi(done=False)
    run.run_stage("smoke", config, tmp_path, api, fake_image, wait=False)
    api.done = True
    run.run_stage("smoke", config, tmp_path, api, fake_image, wait=False)
    assert len(api.batches) == 3
    assert all((tmp_path / "smoke" / f"{m}.jsonl").exists() for m in MODELS)


def test_manifest_records_what_ran(tmp_path):
    run.run_stage("smoke", make_config(size=2), tmp_path, FakeApi(), fake_image, revision="abc123")
    manifest = json.loads((tmp_path / "smoke" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["revision"] == "abc123"
    assert manifest["seed"] == 1
    assert manifest["models"] == MODELS
    assert manifest["anchors"] == 2
    assert "started" in manifest and "config_sha256" in manifest


def test_usage_cost_uses_batch_prices():
    replies = {"a": {"usage": {"input_tokens": 1_000_000, "output_tokens": 1_000_000}}}
    assert run.usage_summary(replies, "opus")["cost"] == pytest.approx(12.0)
    assert run.usage_summary(replies, "sonnet")["cost"] == pytest.approx(6.0)
    assert run.usage_summary(replies, "haiku")["cost"] == pytest.approx(0.30)


def test_scaled_cost_projects_the_main_run_from_the_smoke_run(tmp_path):
    config = make_config(size=6)
    run.run_stage("smoke", config, tmp_path, FakeApi(), fake_image)
    table = run.smoke_gate(config, tmp_path / "smoke", main_anchors=60)
    assert table["total_main"] == pytest.approx(table["total_smoke"] * 10)
    assert table["stop"] is (table["total_main"] > 40)


def answer_replies(config, model, meaning_by_condition):
    out = {}
    for anchor in config["anchors"]:
        for condition in CONDITIONS:
            meaning = meaning_by_condition(condition)
            letter = "ABC"[anchor["option_order"].index(meaning)]
            out[custom_id(model, anchor, condition)] = {
                "stop_reason": "end_turn",
                "content": [{"type": "text", "text": json.dumps({"answer": letter})}],
                "usage": {"input_tokens": 1, "output_tokens": 1},
            }
    return out


def test_report_shows_each_effect_and_its_verdict():
    config = make_config(size=20)

    def believes_the_name(condition):
        if condition["name"] in ("different", "famous", "seller"):
            return "different"
        return "same" if condition["relation"] == "same" or condition["name"] == "same" else "different"

    replies = {m: answer_replies(config, m, believes_the_name) for m in MODELS}
    text = run.report_text(config, replies, n_boot=200)
    assert "T Q1" in text and "T Q2" in text and "U Q1" in text and "V Q1" in text and "P Q1" in text
    assert "차이가 있음" in text
    assert "Haiku - Opus" in text
    assert "교호작용" in text


def test_report_marks_a_model_that_cannot_tell_items_apart():
    config = make_config(size=20)
    replies = {m: answer_replies(config, m, lambda _c: "same") for m in MODELS}
    assert "구별력이 0.2보다 작음" in run.report_text(config, replies, n_boot=50)


def test_report_breaks_values_down_by_closeness_and_kind():
    config = make_config(size=20)
    config["anchors"][0]["closeness"] = "medium"
    replies = {m: answer_replies(config, m, lambda _c: "same") for m in MODELS}
    text = run.report_text(config, replies, n_boot=50)
    assert "비슷한 정도: close" in text and "비슷한 정도: medium" in text and "유형: SHOES" in text


def test_image_reader_returns_base64_of_the_checked_file(tmp_path):
    import base64
    import hashlib

    (tmp_path / "a.jpg").write_bytes(b"photo")
    photos = {"a": {"sha256": hashlib.sha256(b"photo").hexdigest()}}
    assert base64.b64decode(run.image_reader(tmp_path, photos)("a")) == b"photo"


def test_image_reader_refuses_a_changed_file(tmp_path):
    (tmp_path / "a.jpg").write_bytes(b"changed")
    with pytest.raises(ValueError):
        run.image_reader(tmp_path, {"a": {"sha256": "other"}})("a")


def test_plan_counts_calls_for_each_stage():
    plan = run.plan(make_config(size=80))
    assert plan["smoke_calls"] == 6 * 17 * 3
    assert plan["main_calls"] == 80 * 17 * 3


def test_main_stage_of_a_named_config_goes_to_its_own_folder(tmp_path):
    config = {**make_config(size=2), "results_name": "confirm_fashion"}
    run.run_stage("main", config, tmp_path, FakeApi(), fake_image)
    assert (tmp_path / "confirm_fashion" / "opus.jsonl").exists()
    assert not (tmp_path / "main").exists()


def test_pilot_config_still_uses_the_main_folder(tmp_path):
    run.run_stage("main", make_config(size=2), tmp_path, FakeApi(), fake_image)
    assert (tmp_path / "main" / "opus.jsonl").exists()


def test_smoke_run_is_required_only_when_the_config_has_one():
    assert run.smoke_required(make_config()) is True
    assert run.smoke_required({**make_config(), "smoke_anchors": 0}) is False


def test_confirmation_report_starts_with_the_claims(tmp_path):
    config = {**make_config(size=4), "results_name": "confirm_fashion", "confirm_claims": True}
    run.run_stage("main", config, tmp_path, FakeApi(answer="A"), fake_image)
    replies = {m: run.load_replies(tmp_path / "confirm_fashion" / f"{m}.jsonl") for m in MODELS}
    text = run.report_text(config, replies, n_boot=50, claims_n_boot=50)
    assert text.index("## 확인 주장") < text.index("## Haiku")
    assert "C4" in text and "opus - sonnet" in text


def test_pilot_report_has_no_claims(tmp_path):
    config = make_config(size=4)
    run.run_stage("main", config, tmp_path, FakeApi(answer="A"), fake_image)
    replies = {m: run.load_replies(tmp_path / "main" / f"{m}.jsonl") for m in MODELS}
    assert "## 확인 주장" not in run.report_text(config, replies, n_boot=50)
