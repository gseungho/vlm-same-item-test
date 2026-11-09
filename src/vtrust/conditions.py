"""The 17 conditions of one anchor and the request each becomes (spec section 5). No API call here."""

import json

OPTION_TEXT = {"same": "Yes, the same", "different": "No, different", "unknown": "Cannot tell"}
QUESTIONS = {
    "q1": "Are these two listings for the same product?",
    "q2": "Apart from the brand name, are these two listings for the same item?",
}
LETTERS = ("A", "B", "C")
ANSWER_FORMAT = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {"answer": {"type": "string", "enum": list(LETTERS)}},
        "required": ["answer"],
        "additionalProperties": False,
    },
}
CONDITIONS = [
    {"relation": relation, "name": name, "question": question}
    for relation in ("same", "different")
    for name in ("none", "same", "different", "famous")
    for question in ("q1", "q2")
] + [{"relation": "same", "name": "seller", "question": "q1"}]


def _name_lines(anchor, name):
    """The name line of the anchor listing and of the other listing; None when no name is shown."""
    if name == "none":
        return None, None
    if name == "seller":
        return f"Seller: {anchor['brand']}", f"Seller: {anchor['other_brand']}"
    other = {"same": anchor["brand"], "different": anchor["other_brand"], "famous": anchor["famous_brand"]}[name]
    return f"Brand: {anchor['brand']}", f"Brand: {other}"


def _content(anchor, condition, image_data):
    anchor_line, other_line = _name_lines(anchor, condition["name"])
    other_photo = anchor["a2"] if condition["relation"] == "same" else anchor["c"]
    listings = [(anchor["a1"], anchor_line), (other_photo, other_line)]
    if not anchor["anchor_first"]:
        listings.reverse()
    blocks, lines = [], []
    for number, (photo, line) in enumerate(listings, start=1):
        lines.append(f"Listing {number}")
        if line and anchor["name_line_first"]:
            lines.append(line)
        blocks.append({"type": "text", "text": "\n".join(lines)})
        blocks.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": image_data(photo)},
        })
        lines = [line] if line and not anchor["name_line_first"] else []
    options = [f"{letter}. {OPTION_TEXT[m]}" for letter, m in zip(LETTERS, anchor["option_order"], strict=True)]
    lines += [QUESTIONS[condition["question"]], *options]
    blocks.append({"type": "text", "text": "\n".join(lines)})
    return blocks


def custom_id(model, anchor, condition):
    return "-".join([model, anchor["pair_id"], condition["relation"], condition["name"], condition["question"]])


def parse_id(value):
    model, pair_id, relation, name, question = value.split("-")
    return {"model": model, "pair_id": pair_id, "relation": relation, "name": name, "question": question}


def build_request(anchor, condition, model, config, image_data):
    return {
        "custom_id": custom_id(model, anchor, condition),
        "params": {
            "model": config["models"][model],
            "max_tokens": config["max_tokens"],
            # The same setting for every model: Opus 5.5 cannot turn thinking off (spec section 5).
            "thinking": {"type": "adaptive", "display": "summarized"},
            "output_config": {"effort": config["effort"], "format": ANSWER_FORMAT},
            "messages": [{"role": "user", "content": _content(anchor, condition, image_data)}],
        },
    }


def reply_meaning(message, anchor):
    """same, different or unknown; None for a refusal, a cut-off reply or an unreadable one."""
    if message.get("stop_reason") != "end_turn":
        return None
    for block in message.get("content", []):
        if block.get("type") == "text":
            try:
                letter = json.loads(block["text"])["answer"]
            except (ValueError, KeyError, TypeError):
                return None
            if letter in LETTERS:
                return anchor["option_order"][LETTERS.index(letter)]
    return None
