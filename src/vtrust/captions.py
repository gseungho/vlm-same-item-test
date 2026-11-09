"""The ten conditions of one caption item and the request each becomes (caption pilot spec section 5).

No API call here. Answers to the yes/no conditions mean yes, no or unknown; answers to the two-caption
choices mean true, false or unknown (which caption was picked).
"""

import json

from vtrust.conditions import ANSWER_FORMAT, LETTERS

QUESTIONS = {"qm": "Does the photo match the caption?", "qa": "Is the caption accurate?"}
CHOICE_QUESTIONS = {"choose_img": "Which caption describes this photo?", "choose_text": "Which caption is accurate?"}
OPTION_TEXT = {"yes": "Yes", "no": "No", "unknown": "Cannot tell"}
CHOICE_OPTIONS = ("Caption 1", "Caption 2", "Cannot tell")
# condition: (photo slot or None, caption, question)
SINGLE = {
    "true_qm": ("photo", "true", "qm"), "true_qa": ("photo", "true", "qa"),
    "mc_qm": ("photo", "false", "qm"), "mc_qa": ("photo", "false", "qa"),
    "ooc_qm": ("other_photo", "true", "qm"), "ooc_qa": ("other_photo", "true", "qa"),
    "text_true": (None, "true", "qa"), "text_mc": (None, "false", "qa"),
    # Wording spec 2026-11-09: QC asks only for a contradiction, so its "yes" rejects and its "no" accepts.
    "true_qc": ("photo", "true", "qc"), "mc_qc": ("photo", "false", "qc"), "ooc_qc": ("other_photo", "true", "qc"),
}
CHOICE = {"choose_img": "photo", "choose_text": None}
CONDITIONS = ["true_qm", "true_qa", "mc_qm", "mc_qa", "ooc_qm", "ooc_qa",
              "choose_img", "choose_text", "text_true", "text_mc"]
QC = "Does anything in the photo contradict the caption?"
WORDING_CONDITIONS = ["true_qm", "mc_qm", "ooc_qm", "true_qc", "mc_qc", "ooc_qc"]


def item_conditions(item, conditions=CONDITIONS):
    """VERITE items without an out-of-context photo skip the two ooc conditions (spec section 4.1)."""
    return [c for c in conditions if item["other_photo"] is not None or not c.startswith("ooc")]


def _image(photo, image_data):
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_data(photo)}}


def _content(item, condition, image_data, questions=QUESTIONS):
    blocks = []
    if condition in SINGLE:
        slot, caption, question = SINGLE[condition]
        options = [OPTION_TEXT[m] for m in item["option_order"]]
        lines = [f"Caption: {item[caption + '_caption']}", questions[question]]
    else:
        slot = CHOICE[condition]
        first, second = (("true", "false") if item["true_first"] else ("false", "true"))
        options = CHOICE_OPTIONS
        lines = [f"Caption 1: {item[first + '_caption']}", f"Caption 2: {item[second + '_caption']}",
                 CHOICE_QUESTIONS[condition]]
    if slot:
        blocks.append(_image(item[slot], image_data))
    lines += [f"{letter}. {option}" for letter, option in zip(LETTERS, options, strict=True)]
    blocks.append({"type": "text", "text": "\n".join(lines)})
    return blocks


def custom_id(model, item, condition):
    return "-".join([model, item["item_id"], condition])


def parse_id(value):
    model, item_id, condition = value.split("-")
    return {"model": model, "item_id": item_id, "condition": condition}


def build_request(item, condition, model, config, image_data):
    """r1 configs add a system line with the date and their own question wording (spec r1)."""
    params = {
        "model": config["models"][model],
        "max_tokens": config["max_tokens"],
        "thinking": {"type": "adaptive", "display": "summarized"},
        "output_config": {"effort": config["effort"], "format": ANSWER_FORMAT},
        "messages": [{"role": "user", "content": _content(item, condition, image_data,
                                                           config.get("questions", QUESTIONS))}],
    }
    if "system" in config:
        params["system"] = config["system"]
    return {"custom_id": custom_id(model, item, condition), "params": params}


def reply_meaning(message, item, condition):
    """yes, no or unknown (or true, false, unknown for a choice); None when the reply has no usable answer."""
    if message.get("stop_reason") != "end_turn":
        return None
    for block in message.get("content", []):
        if block.get("type") == "text":
            try:
                letter = json.loads(block["text"])["answer"]
            except (ValueError, KeyError, TypeError):
                return None
            if letter not in LETTERS:
                return None
            position = LETTERS.index(letter)
            if condition in SINGLE:
                return item["option_order"][position]
            if position == 2:
                return "unknown"
            return "true" if (position == 0) == item["true_first"] else "false"
    return None
