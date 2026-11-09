"""Send the conditions, save the replies and write the report (spec sections 6, 7, 11).

    python -m vtrust.run plan                 # counts only, no API call
    python -m vtrust.run smoke                # paid: the first anchors of the fixed order
    python -m vtrust.run main [--limit N]     # paid: refuses to start before the smoke run exists
    python -m vtrust.run report smoke|main    # no API call
"""

import argparse
import base64
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

from vtrust import analysis
from vtrust.conditions import CONDITIONS, build_request, parse_id, reply_meaning

# Dollars per million tokens at Batch prices (input, output); checked against the official page 2026-11-02.
BATCH_PRICES = {"haiku": (0.05, 0.25), "sonnet": (1.0, 5.0), "opus": (2.0, 10.0)}
MAX_MAIN_COST = 40.0
LABELS = {"haiku": "Haiku", "sonnet": "Sonnet", "opus": "Opus"}
NAMES = ("none", "same", "different", "famous")
QUESTIONS = ("q1", "q2")


def stage_anchors(config, stage, limit=None):
    if stage == "smoke":
        return config["anchors"][: config["smoke_anchors"]]
    return config["anchors"][:limit] if limit else config["anchors"]


def build_requests(anchors, model, config, image_data):
    return [build_request(a, c, model, config, image_data) for a in anchors for c in CONDITIONS]


def split_by_size(requests, limit_bytes):
    """Greedy chunks whose JSON stays under the limit; a Batch is limited by size as well as count."""
    chunks, current, used = [], [], 2
    for request in requests:
        size = len(json.dumps(request)) + 2
        if size + 2 > limit_bytes:
            raise ValueError(f"request {request['custom_id']} alone exceeds {limit_bytes} bytes")
        if used + size > limit_bytes:
            chunks.append(current)
            current, used = [], 2
        current.append(request)
        used += size
    if current:
        chunks.append(current)
    return chunks


def image_reader(photo_dir, photos):
    """Base64 of a photo, checked against the hash fixed in the config, cached after the first read."""
    cache = {}

    def read(photo):
        if photo not in cache:
            data = (Path(photo_dir) / f"{photo}.jpg").read_bytes()
            if hashlib.sha256(data).hexdigest() != photos[photo]["sha256"]:
                raise ValueError(f"photo {photo} differs from the fixed sample")
            cache[photo] = base64.b64encode(data).decode("ascii")
        return cache[photo]

    return read


def _write_jsonl(path, mapping, value_key):
    with open(path, "w", encoding="utf-8") as f:
        for key, value in mapping.items():
            f.write(json.dumps({"custom_id": key, value_key: value}, ensure_ascii=False) + "\n")


def load_replies(path):
    with open(path, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f]
    return {row["custom_id"]: row["message"] for row in rows}


def _write_manifest(stage_dir, stage, config, anchors, revision, conditions=None):
    path = stage_dir / "manifest.json"
    if path.exists():
        return
    try:
        sdk = metadata.version("anthropic")
    except metadata.PackageNotFoundError:
        sdk = None
    path.write_text(json.dumps({
        "stage": stage, "started": datetime.now(timezone.utc).isoformat(), "revision": revision,
        "config_sha256": hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest(),
        "seed": config["seed"], "models": config["models"], "effort": config["effort"],
        "max_tokens": config["max_tokens"], "anchors": len(anchors),
        "conditions": len(CONDITIONS) if conditions is None else conditions,
        "anthropic_sdk": sdk, "compute": "Message Batches API, no GPU",
    }, indent=1), encoding="utf-8")


def stage_folder(config, stage):
    """results/<folder>: later configs name their own folders so the pilot's results stay apart."""
    if stage == "smoke":
        return config.get("smoke_name", "smoke")
    return config.get("results_name", "main") if stage == "main" else stage


def smoke_required(config):
    return config.get("smoke_anchors", 0) > 0


def run_stage(stage, config, out_dir, api, image_data, revision=None, limit=None, wait=True,
              build=build_requests, units=None, conditions=None):
    """Send every model first, cheapest first, then wait. Safe to rerun: a batch is never sent twice.

    With wait=False, a model whose batches have not all ended is left for a later run instead of waited on.
    Another experiment passes its own `build`, `units` and number of `conditions` (the caption pilot).
    """
    stage_dir = Path(out_dir) / stage_folder(config, stage)
    stage_dir.mkdir(parents=True, exist_ok=True)
    anchors = stage_anchors(config, stage, limit) if units is None else units
    _write_manifest(stage_dir, stage, config, anchors, revision, conditions)
    state_path = stage_dir / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    limit_bytes = config["batch_limit_mb"] * 1_000_000
    pending = {}
    for model in config["models"]:
        out_path = stage_dir / f"{model}.jsonl"
        if out_path.exists():
            print(f"[{stage}/{model}] 이미 받은 결과가 있어 다시 보내지 않습니다.", flush=True)
            continue
        chunks = split_by_size(build(anchors, model, config, image_data), limit_bytes)
        batch_ids = state.setdefault(model, [])
        for chunk in chunks[len(batch_ids):]:
            batch_ids.append(api.submit(chunk))
            # Saved after every submission so an interrupted run never pays for a chunk twice.
            state_path.write_text(json.dumps(state, indent=1), encoding="utf-8")
        print(f"[{stage}/{model}] 요청 {sum(len(c) for c in chunks)}개, 묶음 {len(batch_ids)}개.", flush=True)
        pending[model] = (out_path, batch_ids)
    # Waiting only after every model is sent lets the models' batches be processed at the same time.
    for model, (out_path, batch_ids) in pending.items():
        running = [] if wait else [b for b in batch_ids if not api.ended(b)]
        if running:
            print(f"[{stage}/{model}] 처리 중인 묶음 {len(running)}개. 나중에 다시 실행하면 받습니다.", flush=True)
            continue
        replies, failures = {}, {}
        for batch_id in batch_ids:
            api.wait(batch_id)
            ok, bad = api.collect(batch_id)
            replies |= ok
            failures |= bad
        _write_jsonl(out_path, replies, "message")
        if failures:
            _write_jsonl(stage_dir / f"{model}_failures.jsonl", failures, "result")
        print(f"[{stage}/{model}] 성공 {len(replies)}개, 실패 {len(failures)}개.", flush=True)


def usage_summary(replies, model):
    input_tokens = sum(r["usage"].get("input_tokens", 0) for r in replies.values())
    output_tokens = sum(r["usage"].get("output_tokens", 0) for r in replies.values())
    input_price, output_price = BATCH_PRICES[model]
    calls = len(replies)
    return {
        "calls": calls, "input": input_tokens, "output": output_tokens,
        "input_per_call": input_tokens / calls if calls else 0,
        "output_per_call": output_tokens / calls if calls else 0,
        "cost": (input_tokens * input_price + output_tokens * output_price) / 1_000_000,
    }


def smoke_gate(config, stage_dir, main_anchors):
    """Measured cost of the smoke run and the main run it implies; spec section 11's stop condition."""
    models = {m: usage_summary(load_replies(Path(stage_dir) / f"{m}.jsonl"), m) for m in config["models"]}
    total_smoke = sum(s["cost"] for s in models.values())
    total_main = total_smoke * main_anchors / config["smoke_anchors"]
    return {"models": models, "total_smoke": total_smoke, "total_main": total_main, "stop": total_main > MAX_MAIN_COST}


def plan(config):
    size = len(CONDITIONS) * len(config["models"])
    return {"smoke_calls": config["smoke_anchors"] * size, "main_calls": len(config["anchors"]) * size}


def answer_tables(config, replies):
    """{model: {pair_id: {(relation, name, question): meaning}}} from the saved replies."""
    anchors = {a["pair_id"]: a for a in config["anchors"]}
    tables = {}
    for model, messages in replies.items():
        table = {}
        for key, message in messages.items():
            info = parse_id(key)
            cell = (info["relation"], info["name"], info["question"])
            table.setdefault(info["pair_id"], {})[cell] = reply_meaning(message, anchors[info["pair_id"]])
        tables[model] = table
    return tables


def _percent(value):
    return "없음" if value is None else f"{100 * value:.1f}%"


def _points(value):
    return "없음" if value is None else f"{100 * value:+.1f}%p"


def _row(label, values, judged=True):
    point, low, high = values
    if point is None:
        return f"| {label} | 없음 | | |"
    reading = analysis.verdict(point, low, high) if judged else "판정 없음 (구별력이 0.2보다 작음)"
    return f"| {label} | {_points(point)} | [{_points(low)}, {_points(high)}] | {reading} |"


def _effects(table, n_boot):
    """Every named quantity of spec section 3, for one model."""
    t = {q: (("same", "none", q), ("same", "different", q)) for q in QUESTIONS}
    u = {q: (("different", "same", q), ("different", "none", q)) for q in QUESTIONS}
    v = {q: (("same", "different", q), ("same", "famous", q)) for q in QUESTIONS}
    d = {q: (("same", "none", q), ("different", "none", q)) for q in QUESTIONS}
    seller = (("same", "none", "q1"), ("same", "seller", "q1"))
    out = {}
    for q in QUESTIONS:
        label = q.upper()
        out[f"T {label}"] = (analysis.effect(table, *t[q], n_boot=n_boot), q)
        out[f"U {label}"] = (analysis.effect(table, *u[q], n_boot=n_boot), q)
        out[f"V {label}"] = (analysis.effect(table, *v[q], n_boot=n_boot), q)
    out["P Q1"] = (analysis.effect(table, *seller, n_boot=n_boot), "q1")
    return out, {q: analysis.effect(table, *d[q], n_boot=n_boot) for q in QUESTIONS}


def _breakdown(config, table, label, key):
    groups = {}
    for anchor in config["anchors"]:
        if anchor["pair_id"] in table:
            groups.setdefault(key(anchor), set()).add(anchor["pair_id"])
    rows = []
    for value in sorted(groups, key=str):
        part = analysis.subset(table, groups[value])
        cells = [
            analysis.effect(part, ("same", "none", q), ("same", "different", q), n_boot=1)[0] for q in QUESTIONS
        ] + [analysis.effect(part, ("different", "same", "q1"), ("different", "none", "q1"), n_boot=1)[0]]
        shown = " | ".join(_points(cell) for cell in cells)
        rows.append(f"| {label}: {value} | {len(part)} | {shown} |")
    return rows


def _claims_lines(tables, n_boot):
    lines = ["## 확인 주장", "",
             f"설계서 `specs/2026-11-04-same-item-confirm.md` 2절의 판정이다. 구간은 Bonferroni로 보정한 "
             f"{100 * analysis.BONFERRONI_LEVEL:.2f}% 구간이다(다시 뽑기 {n_boot:,}번).", "",
             "| 주장 | 모델 | 값 | 차이 | 보정 구간 | 판정 |", "| --- | --- | --- | --- | --- | --- |"]
    for row in analysis.confirm_claims(tables, n_boot=n_boot):
        span = "" if row["point"] is None else f"[{_points(row['low'])}, {_points(row['high'])}]"
        lines.append(f"| {row['claim']} | {row['model']} | {row['value']} | {_points(row['point'])} | {span} | "
                     f"{row['verdict'] or '없음'} |")
    return lines + ["", "아래 표는 모두 탐색으로 읽는다.", ""]


def report_text(config, replies, n_boot=analysis.N_BOOT, claims_n_boot=analysis.CONFIRM_N_BOOT):
    tables = answer_tables(config, replies)
    lines = ["# 결과 표", "", "탐색 결과다. 확인된 결과로 쓰지 않는다. T, U, V, P의 정의는 설계서 3절에 있다.", ""]
    if config.get("confirm_claims"):
        lines = ["# 결과 표", ""] + _claims_lines(tables, claims_n_boot)
    for model, table in tables.items():
        given = sum(v is not None for row in table.values() for v in row.values())
        total = sum(len(row) for row in table.values())
        lines += [f"## {LABELS[model]}", "", f"앵커 {len(table)}개, 호출 {total}번, 답 없음 {total - given}번.", ""]
        lines += ["| 값 | 차이 | 95% 구간 | 판정 |", "| --- | --- | --- | --- |"]
        effects, discrimination = _effects(table, n_boot)
        for question, values in discrimination.items():
            lines.append(_row(f"구별력 D (이름 없음, {question.upper()})", values))
        for name, (values, question) in effects.items():
            point = discrimination[question][0]
            lines.append(_row(name, values, judged=point is not None and point >= 0.2))
        for q in QUESTIONS:
            lines.append(_row(f"교호작용 {q.upper()}", analysis.double_difference(
                table, ("same", "same", q), ("same", "different", q),
                ("different", "same", q), ("different", "different", q), n_boot=n_boot)))
        lines.append(_row("T Q1 - T Q2", analysis.double_difference(
            table, ("same", "none", "q1"), ("same", "different", "q1"),
            ("same", "none", "q2"), ("same", "different", "q2"), n_boot=n_boot)))
        lines.append(_row("T Q1 - P Q1", analysis.double_difference(
            table, ("same", "none", "q1"), ("same", "different", "q1"),
            ("same", "none", "q1"), ("same", "seller", "q1"), n_boot=n_boot)))
        lines += ["", "| 번복 | 비율 | 분모 |", "| --- | --- | --- |"]
        for q in QUESTIONS:
            share, count = analysis.flip_rate(table, ("same", "none", q), ("same", "different", q))
            lines.append(f"| 이름이 다를 때 {q.upper()} | {_percent(share)} | {count} |")
        share, count = analysis.flip_rate(table, ("same", "none", "q1"), ("same", "seller", "q1"))
        lines.append(f"| 판매자 이름이 다를 때 Q1 | {_percent(share)} | {count} |")
        lines += ["", "| 조건 (사진, 이름, 문장) | 같다 | 알 수 없다 |", "| --- | --- | --- |"]
        for condition in CONDITIONS:
            cell = (condition["relation"], condition["name"], condition["question"])
            same_share = _percent(analysis.rate(table, cell))
            lines.append(f"| {' '.join(cell)} | {same_share} | {_percent(analysis.unknown_rate(table, cell))} |")
        lines += ["", "판정 없이 적는 값이다.", ""]
        lines += ["| 묶음 | 앵커 | T Q1 | T Q2 | U Q1 |", "| --- | --- | --- | --- | --- |"]
        lines += _breakdown(config, table, "유형", lambda a: a["kind"])
        lines += _breakdown(config, table, "비슷한 정도", lambda a: a["closeness"])
        lines += _breakdown(config, table, "이름 줄이 사진 앞", lambda a: a["name_line_first"])
        lines += _breakdown(config, table, "앵커가 첫째", lambda a: a["anchor_first"])
        lines += _breakdown(config, table, "유명 브랜드", lambda a: a["famous_brand"])
        lines.append("")
    lines += ["## 모델 비교", "", "| 비교 | 차이 | 95% 구간 | 판정 |", "| --- | --- | --- | --- |"]
    pairs = [("haiku", "opus"), ("haiku", "sonnet"), ("sonnet", "opus")]
    for first, second in pairs:
        if first in tables and second in tables:
            for q in QUESTIONS:
                values = analysis.model_difference(
                    tables[first], tables[second], ("same", "none", q), ("same", "different", q), n_boot=n_boot
                )
                lines.append(_row(f"{LABELS[first]} - {LABELS[second]} (T {q.upper()})", values))
    return "\n".join(lines) + "\n"


def _revision(root):
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True)
    dirty = subprocess.run(["git", "-C", str(root), "status", "--porcelain"], capture_output=True, text=True)
    return head.stdout.strip() + ("-dirty" if dirty.stdout.strip() else "")


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["plan", "smoke", "main", "report"])
    parser.add_argument("stage", nargs="?", choices=["smoke", "main"])
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--config", default="configs/same_item_v1.json")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--no-wait", action="store_true", help="보내고 끝난 것만 받은 뒤 바로 끝낸다")
    args = parser.parse_args(argv)
    config = json.loads((args.root / args.config).read_text(encoding="utf-8"))
    results = args.root / "results"

    if args.command == "plan":
        print(plan(config), "앵커", len(config["anchors"]))
    elif args.command == "report":
        stage_dir = results / stage_folder(config, args.stage)
        saved = [m for m in config["models"] if (stage_dir / f"{m}.jsonl").exists()]
        replies = {m: load_replies(stage_dir / f"{m}.jsonl") for m in saved}
        text = report_text(config, replies)
        (stage_dir / "report.md").write_text(text, encoding="utf-8")
        print(text)
    else:
        from vtrust.batches import BatchApi

        if args.command == "main" and smoke_required(config) and not (results / "smoke" / "manifest.json").exists():
            raise SystemExit("시험 실행 결과가 없어 본 실행을 시작하지 않습니다.")
        reader = image_reader(args.root / "data" / "pairs" / "photos", config["photos"])
        run_stage(args.command, config, results, BatchApi(), reader, _revision(args.root), args.limit, not args.no_wait)
        received = all((results / stage_folder(config, args.command) / f"{m}.jsonl").exists() for m in config["models"])
        if args.command == "smoke" and received:
            gate = smoke_gate(config, results / "smoke", len(config["anchors"]))
            print(json.dumps(gate, ensure_ascii=False, indent=1))
            over = "본 실행 어림이 $40를 넘습니다. 멈추고 다시 정합니다."
            print(over if gate["stop"] else "본 실행 어림이 $40 이하입니다.")


if __name__ == "__main__":
    main()
