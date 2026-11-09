"""Write a local review page for the labelled photos.

    python -I review_page.py <project_dir>
"""

import html
import json
import sys
from collections import Counter
from pathlib import Path

STYLE = """
:root { --ink: #1f2328; --muted: #5d6670; --line: #d8dde3; --surface: #ffffff; --page: #f6f7f8; }
@media (prefers-color-scheme: dark) {
  :root { --ink: #e8eaed; --muted: #a3acb6; --line: #3a4048; --surface: #22262b; --page: #16191c; }
}
* { box-sizing: border-box; }
body { margin: 0; padding: 24px 16px 64px; background: var(--page); color: var(--ink);
       font: 15px/1.6 "Malgun Gothic", system-ui, sans-serif; }
main { max-width: 1400px; margin: 0 auto; }
h1 { font-size: 24px; margin: 0 0 8px; }
h2 { font-size: 19px; margin: 40px 0 8px; }
p { margin: 0 0 8px; color: var(--muted); max-width: 72ch; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px;
        margin-top: 16px; }
figure { margin: 0; padding: 8px; background: var(--surface); border: 1px solid var(--line);
         border-radius: 8px; }
figure a { display: block; background: #fff; border-radius: 4px; }
img { display: block; width: 100%; height: 260px; object-fit: contain; }
.id { font-weight: 700; }
figcaption { margin-top: 6px; font-size: 13px; }
.note { color: var(--muted); }
"""


def card(row):
    name = row["file"][:-4]
    note = f'<div class="note">{html.escape(row["note"])}</div>' if row.get("note") else ""
    return (
        f'<figure><a href="../candidates/{row["file"]}" target="_blank">'
        f'<img loading="lazy" src="../candidates/{row["file"]}" alt="{name}"></a>'
        f'<figcaption><span class="id">{name}</span> · {html.escape(row["brand"])} · '
        f'{html.escape(row["kind"])}{note}</figcaption></figure>'
    )


def main(root):
    sys.stdout.reconfigure(encoding="utf-8")
    root = Path(root)
    rows = json.loads((root / "data" / "labels_draft.json").read_text(encoding="utf-8"))
    meta = {r["file"]: r for r in json.loads((root / "data" / "candidates.json").read_text("utf-8"))}
    assert all((root / "data" / "candidates" / r["file"]).exists() for r in rows)
    assert len({meta[r["file"]]["image"] for r in rows}) == len(rows)
    assert max(Counter(r["brand"] for r in rows).values()) <= 10
    print("counts", Counter(r["label"] for r in rows))
    print("hidden rows checked:", sum(bool(r.get("checked_1000")) for r in rows if r["label"] == "안 보임"))
    sections = []
    intro = {
        "보임": "브랜드 이름이나 로고를 사진에서 읽을 수 있다고 표시한 사진입니다. 읽을 수 없거나 다른 브랜드로 보이는 번호를 알려 주세요.",
        "안 보임": "브랜드 표시가 전혀 보이지 않는다고 표시한 사진입니다. 브랜드를 알 만한 글자나 로고가 보이는 번호를 알려 주세요.",
    }
    for label in ("보임", "안 보임"):
        part = sorted((r for r in rows if r["label"] == label), key=lambda r: r["file"])
        cards = "\n".join(card(r) for r in part)
        sections.append(
            f"<h2>{label} ({len(part)}장)</h2><p>{intro[label]}</p><div class=\"grid\">{cards}</div>"
        )
    page = (
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>사진 표시 확인</title><style>{STYLE}</style></head><body><main>"
        "<h1>파일럿 사진 표시 확인</h1>"
        "<p>사진을 누르면 모델이 볼 크기(긴 변 1000픽셀)로 열립니다. 의견이 다른 사진의 번호만 알려 주시면 "
        "뺍니다. 사진 출처: Amazon Berkeley Objects (CC BY 4.0).</p>"
        + "".join(sections)
        + "</main></body></html>"
    )
    out = root / "data" / "review"
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    print("wrote", out / "index.html")


if __name__ == "__main__":
    main(sys.argv[1])
