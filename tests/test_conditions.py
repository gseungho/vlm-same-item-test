"""What the model sees in each condition (spec section 5). Each test names one rule of the spec."""

import base64
import json

import pytest

from vtrust.conditions import CONDITIONS, build_request, parse_id, reply_meaning

ANCHOR = {
    "pair_id": "p003", "brand": "Klepe", "other_brand": "Bourge", "famous_brand": "Gucci",
    "a1": "A1", "a2": "A2", "c": "C", "anchor_first": True, "name_line_first": True,
    "option_order": ["different", "same", "unknown"],
}
CONFIG = {"models": {"haiku": "claude-haiku-5-5", "opus": "claude-opus-5-5"}, "effort": "medium", "max_tokens": 8000}


def b64(photo):
    return base64.b64encode(photo.encode()).decode()


def build(condition, anchor=ANCHOR, model="haiku"):
    return build_request(anchor, condition, model, CONFIG, b64)


def shape(request):
    """The content blocks as text, with photos shown as [photo id]."""
    parts = []
    for block in request["params"]["messages"][0]["content"]:
        if block["type"] == "image":
            parts.append("[" + base64.b64decode(block["source"]["data"]).decode() + "]")
        else:
            parts.append(block["text"])
    return "\n".join(parts)


def condition(relation, name, question):
    return {"relation": relation, "name": name, "question": question}


def test_there_are_seventeen_conditions():
    assert len(CONDITIONS) == 17
    assert len({(c["relation"], c["name"], c["question"]) for c in CONDITIONS}) == 17


def test_seller_is_asked_only_on_same_item_pairs_with_q1():
    sellers = [c for c in CONDITIONS if c["name"] == "seller"]
    assert sellers == [condition("same", "seller", "q1")]


def test_full_factorial_covers_every_other_cell():
    cells = {(c["relation"], c["name"], c["question"]) for c in CONDITIONS if c["name"] != "seller"}
    assert cells == {
        (r, n, q) for r in ("same", "different") for n in ("none", "same", "different", "famous") for q in ("q1", "q2")
    }


def test_no_name_condition_has_no_name_line():
    text = shape(build(condition("same", "none", "q1")))
    assert "Brand:" not in text and "Seller:" not in text


def test_different_names_go_on_the_two_listings():
    text = shape(build(condition("same", "different", "q1")))
    assert text == (
        "Listing 1\nBrand: Klepe\n[A1]\nListing 2\nBrand: Bourge\n[A2]\n"
        "Are these two listings for the same product?\nA. No, different\nB. Yes, the same\nC. Cannot tell"
    )


def test_same_name_goes_on_both_listings():
    text = shape(build(condition("same", "same", "q1")))
    assert text.count("Brand: Klepe") == 2


def test_famous_name_goes_on_the_other_listing():
    text = shape(build(condition("same", "famous", "q1")))
    assert "Brand: Klepe" in text and "Brand: Gucci" in text


def test_different_item_pairs_use_the_lookalike_photo():
    text = shape(build(condition("different", "none", "q1")))
    assert "[A1]" in text and "[C]" in text and "[A2]" not in text


def test_seller_condition_uses_the_same_names_on_seller_lines():
    text = shape(build(condition("same", "seller", "q1")))
    assert "Seller: Klepe" in text and "Seller: Bourge" in text and "Brand:" not in text


def test_q2_asks_apart_from_the_brand_name():
    text = shape(build(condition("same", "none", "q2")))
    assert "Apart from the brand name, are these two listings for the same item?" in text


def test_anchor_can_come_second():
    text = shape(build(condition("same", "different", "q1"), {**ANCHOR, "anchor_first": False}))
    assert text.startswith("Listing 1\nBrand: Bourge\n[A2]\nListing 2\nBrand: Klepe\n[A1]")


def test_name_line_can_follow_the_photo():
    text = shape(build(condition("same", "different", "q1"), {**ANCHOR, "name_line_first": False}))
    assert text.startswith("Listing 1\n[A1]\nBrand: Klepe\nListing 2\n[A2]\nBrand: Bourge\nAre these")


def test_all_models_think_at_the_same_effort_and_answer_one_letter():
    params = build(condition("same", "none", "q1"), model="opus")["params"]
    assert params["model"] == "claude-opus-5-5"
    assert params["thinking"] == {"type": "adaptive", "display": "summarized"}
    assert params["output_config"]["effort"] == "medium"
    schema = params["output_config"]["format"]["schema"]
    assert schema["properties"]["answer"]["enum"] == ["A", "B", "C"]
    assert "fallbacks" not in params


def test_custom_id_round_trips_and_fits_the_api_limit():
    request = build(condition("different", "famous", "q2"))
    assert len(request["custom_id"]) <= 64
    assert parse_id(request["custom_id"]) == {
        "model": "haiku", "pair_id": "p003", "relation": "different", "name": "famous", "question": "q2",
    }


def message(text, stop="end_turn"):
    return {"stop_reason": stop, "content": [{"type": "thinking", "thinking": ""}, {"type": "text", "text": text}]}


@pytest.mark.parametrize(
    ("letter", "meaning"), [("A", "different"), ("B", "same"), ("C", "unknown")]
)
def test_letter_maps_through_the_anchor_option_order(letter, meaning):
    assert reply_meaning(message(json.dumps({"answer": letter})), ANCHOR) == meaning


def test_refusal_counts_as_no_answer():
    assert reply_meaning(message('{"answer": "A"}', stop="refusal"), ANCHOR) is None


def test_cut_off_reply_counts_as_no_answer():
    assert reply_meaning(message('{"answer": "A"}', stop="max_tokens"), ANCHOR) is None


def test_unreadable_reply_counts_as_no_answer():
    assert reply_meaning(message("I think they are the same"), ANCHOR) is None
