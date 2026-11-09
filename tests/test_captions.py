"""What the model sees in each caption condition (caption pilot spec section 5). No API call."""

import base64
import json
import re

from vtrust.captions import CONDITIONS, build_request, item_conditions, parse_id, reply_meaning

ITEM = {
    "item_id": "c007", "photo": "P", "other_photo": "O",
    "true_caption": "Photograph shows a music festival in Saint-Cloud, France on 22 August 2026.",
    "false_caption": "Photograph shows a music festival in Lyon, France on 22 August 2026.",
    "option_order": ["no", "unknown", "yes"], "true_first": False,
}
CONFIG = {"models": {"haiku": "claude-haiku-5-5", "opus": "claude-opus-5-5"}, "effort": "medium", "max_tokens": 8000}


def b64(photo):
    return base64.b64encode(photo.encode()).decode()


def build(condition, item=ITEM, model="haiku"):
    return build_request(item, condition, model, CONFIG, b64)


def photos(request):
    return [base64.b64decode(b["source"]["data"]).decode()
            for b in request["params"]["messages"][0]["content"] if b["type"] == "image"]


def text(request):
    return "\n".join(b["text"] for b in request["params"]["messages"][0]["content"] if b["type"] == "text")


def reply(letter, stop="end_turn"):
    return {"stop_reason": stop, "content": [{"type": "text", "text": json.dumps({"answer": letter})}]}


def test_ten_conditions_with_an_other_photo_and_eight_without():
    assert len(item_conditions(ITEM)) == 10 == len(CONDITIONS)
    without = item_conditions({**ITEM, "other_photo": None})
    assert len(without) == 8 and not any(c.startswith("ooc") for c in without)


def test_each_condition_shows_the_right_photo():
    assert photos(build("true_qm")) == photos(build("mc_qa")) == photos(build("choose_img")) == ["P"]
    assert photos(build("ooc_qm")) == photos(build("ooc_qa")) == ["O"]


def test_requests_without_a_photo_have_no_image_block():
    for condition in ("choose_text", "text_true", "text_mc"):
        assert photos(build(condition)) == []


def test_the_photo_comes_before_the_text():
    content = build("true_qm")["params"]["messages"][0]["content"]
    assert [b["type"] for b in content] == ["image", "text"]


def test_each_condition_shows_the_right_caption():
    true, false = ITEM["true_caption"], ITEM["false_caption"]
    for condition in ("true_qm", "true_qa", "ooc_qm", "ooc_qa", "text_true"):
        assert f"Caption: {true}" in text(build(condition)) and false not in text(build(condition))
    for condition in ("mc_qm", "mc_qa", "text_mc"):
        assert f"Caption: {false}" in text(build(condition)) and true not in text(build(condition))


def test_questions_follow_the_spec():
    assert "Does the photo match the caption?" in text(build("true_qm"))
    assert "Is the caption accurate?" in text(build("mc_qa"))
    for condition in ("text_true", "text_mc"):
        assert "Is the caption accurate?" in text(build(condition))
    assert "Which caption describes this photo?" in text(build("choose_img"))
    assert "Which caption is accurate?" in text(build("choose_text"))


def test_yes_no_options_keep_the_item_order_in_every_condition():
    for condition in ("true_qm", "mc_qa", "ooc_qm", "text_true", "text_mc"):
        assert text(build(condition)).endswith("A. No\nB. Cannot tell\nC. Yes")


def test_two_caption_choice_puts_the_true_caption_where_the_item_says():
    shown = text(build("choose_text"))
    assert shown.index(ITEM["false_caption"]) < shown.index(ITEM["true_caption"])
    assert f"Caption 1: {ITEM['false_caption']}\nCaption 2: {ITEM['true_caption']}" in shown
    flipped = text(build("choose_img", {**ITEM, "true_first": True}))
    assert f"Caption 1: {ITEM['true_caption']}\nCaption 2: {ITEM['false_caption']}" in flipped
    assert shown.endswith("A. Caption 1\nB. Caption 2\nC. Cannot tell")


def test_yes_no_reply_is_read_through_the_option_order():
    assert reply_meaning(reply("A"), ITEM, "true_qm") == "no"
    assert reply_meaning(reply("B"), ITEM, "mc_qa") == "unknown"
    assert reply_meaning(reply("C"), ITEM, "text_mc") == "yes"


def test_choice_reply_says_which_caption_was_picked():
    assert reply_meaning(reply("A"), ITEM, "choose_img") == "false"
    assert reply_meaning(reply("B"), ITEM, "choose_text") == "true"
    assert reply_meaning(reply("A"), {**ITEM, "true_first": True}, "choose_img") == "true"
    assert reply_meaning(reply("C"), ITEM, "choose_img") == "unknown"


def test_unusable_replies_have_no_meaning():
    assert reply_meaning(reply("A", stop="max_tokens"), ITEM, "true_qm") is None
    assert reply_meaning({"stop_reason": "end_turn", "content": [{"type": "text", "text": "Yes"}]},
                         ITEM, "true_qm") is None
    assert reply_meaning({"stop_reason": "refusal", "content": []}, ITEM, "true_qm") is None


def test_custom_id_round_trip_and_batch_rules():
    for condition in item_conditions(ITEM):
        request = build(condition, model="opus")
        key = request["custom_id"]
        assert re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", key)
        assert parse_id(key) == {"model": "opus", "item_id": "c007", "condition": condition}


def test_settings_match_the_same_item_runs():
    params = build("true_qm", model="opus")["params"]
    assert params["model"] == "claude-opus-5-5" and params["max_tokens"] == 8000
    assert params["thinking"] == {"type": "adaptive", "display": "summarized"}
    assert params["output_config"]["effort"] == "medium"
    assert params["output_config"]["format"]["schema"]["properties"]["answer"]["enum"] == ["A", "B", "C"]


R1 = {**CONFIG, "system": "Today's date is 8 November 2026.",
      "questions": {"qm": "Does the photo show what the caption describes?", "qa": "Is the caption accurate?"}}


def test_v1_requests_have_no_system_prompt():
    assert "system" not in build("true_qm")["params"]


def test_r1_tells_the_date_and_asks_the_new_qm_question():
    for condition in CONDITIONS:
        params = build_request(ITEM, condition, "haiku", R1, b64)["params"]
        assert params["system"] == "Today's date is 8 November 2026."
    shown = text(build_request(ITEM, "true_qm", "haiku", R1, b64))
    assert "Does the photo show what the caption describes?" in shown and "match" not in shown
    assert "Is the caption accurate?" in text(build_request(ITEM, "mc_qa", "haiku", R1, b64))
    assert text(build_request(ITEM, "true_qm", "haiku", R1, b64)).endswith("A. No\nB. Cannot tell\nC. Yes")
