"""Read-only: real cross-brand photo sharing in ABO listings, with a sample sheet. No model call.

    python -I abo_cross_brand.py <new_output_dir>
"""
import csv, gzip, io, json, random, re, sys, urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8")
BASE = "https://amazon-berkeley-objects.s3.amazonaws.com"
TYPES = {"SHOES", "BOOT", "SANDAL", "HANDBAG", "HAT", "BACKPACK", "LUGGAGE"}
ALIAS = {"sixth love": "sixth & love", "amazonamazonbasics": "amazonbasics", "franklin": "franklin & freeman"}
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=False)

def get(p):
    with urllib.request.urlopen(f"{BASE}/{p}", timeout=120) as r:
        return r.read()

def text(v):
    for x in v or []:
        if x.get("language_tag", "").startswith("en"):
            return x.get("value")
    return v[0].get("value") if v else None

def key(name):
    n = re.sub(r"^(amazon )?brand\s*-\s*", "", name.strip().lower())
    n = " ".join(re.sub(r"[^a-z0-9& ]", "", n).split())
    return ALIAS.get(n, n)

rows = {}
for s in "0123456789abcdef":
    for line in gzip.decompress(get(f"listings/metadata/listings_{s}.json.gz")).decode("utf-8").splitlines():
        r = json.loads(line)
        kind = (r.get("product_type") or [{}])[0].get("value")
        b = text(r.get("brand"))
        if kind in TYPES and b and r.get("main_image_id"):
            rows[r["item_id"]] = {"id": r["item_id"], "kind": kind, "brand": b, "key": key(b), "name": text(r.get("item_name")) or "",
                                  "main": r["main_image_id"], "imgs": {r["main_image_id"], *(r.get("other_image_id") or [])},
                                  "market": r.get("country"), "domain": r.get("domain_name")}
by_img = defaultdict(set)
for r in rows.values():
    for i in r["imgs"]:
        by_img[i].add(r["id"])
cross = {i: m for i, m in by_img.items() if len({rows[x]["key"] for x in m}) >= 2}
print("listings", len(rows), "| images shared by 2+ brands after merging spellings", len(cross))
print("listings with another photo", sum(len(r["imgs"]) >= 2 for r in rows.values()), "| median photos", sorted(len(r["imgs"]) for r in rows.values())[len(rows) // 2])

# Connected groups of listings joined by a shared photo across brands.
parent = {}
def find(x):
    parent.setdefault(x, x)
    while parent[x] != x:
        parent[x] = parent[parent[x]]; x = parent[x]
    return x
for m in cross.values():
    m = sorted(m)
    for a in m[1:]:
        parent[find(a)] = find(m[0])
groups = defaultdict(set)
for x in list(parent):
    groups[find(x)].add(x)
print("cross-brand listing groups", len(groups), "| listings in them", sum(len(g) for g in groups.values()))
pairs = Counter()
for g in groups.values():
    pairs[" + ".join(sorted({rows[x]["key"] for x in g}))] += 1
print("groups by brand set:")
for p, c in pairs.most_common(40):
    print(f"  {c:4d}  {p}")
print("kinds", Counter(rows[next(iter(g))]["kind"] for g in groups.values()).most_common())
print("markets", Counter(rows[x]["domain"] for g in groups.values() for x in g).most_common(8))

# Does each brand side keep a photo that the other side does not use?
usable = []
for g in groups.values():
    sides = defaultdict(set)
    for x in g:
        sides[rows[x]["key"]] |= rows[x]["imgs"]
    keys = sorted(sides)
    a, b = keys[0], keys[1]
    if sides[a] - sides[b] and sides[b] - sides[a]:
        usable.append(g)
print("groups where both brands also hold their own unshared photo", len(usable))

meta = {r["image_id"]: r["path"] for r in csv.DictReader(io.StringIO(gzip.decompress(get("images/metadata/images.csv.gz")).decode("utf-8")))}
rng = random.Random(20261102)
chosen, seen = [], Counter()
order = sorted(groups.values(), key=lambda g: sorted(g)[0]); rng.shuffle(order)
for g in order:
    p = " + ".join(sorted({rows[x]["key"] for x in g}))
    if seen[p] < 2 and len(chosen) < 8:
        seen[p] += 1; chosen.append(g)
cell = 230
sheet = Image.new("RGB", (cell * 4, (cell + 34) * len(chosen)), "white")
d = ImageDraw.Draw(sheet)
for y, g in enumerate(chosen):
    byk = defaultdict(list)
    for x in sorted(g):
        byk[rows[x]["key"]].append(rows[x])
    k = sorted(byk)[:2]
    a, b = byk[k[0]][0], byk[k[1]][0]
    sa = set().union(*(r["imgs"] for r in byk[k[0]])); sb = set().union(*(r["imgs"] for r in byk[k[1]]))
    shown = [a["main"], b["main"], sorted(sa - sb)[0] if sa - sb else None, sorted(sb - sa)[0] if sb - sa else None]
    print(f"row {y}: A {a['id']} [{a['brand']}] {a['name'][:80]}\n       B {b['id']} [{b['brand']}] {b['name'][:80]}\n       shared {len(sa & sb)} only-A {len(sa - sb)} only-B {len(sb - sa)}")
    Y = y * (cell + 34)
    d.text((4, Y + 2), f"{y} A={a['brand'][:18]} B={b['brand'][:18]}", fill="black")
    d.text((4, Y + 16), "main A | main B | only A | only B", fill="gray")
    for x, img in enumerate(shown):
        if img and img in meta:
            with Image.open(io.BytesIO(get(f"images/small/{meta[img]}"))) as im:
                im = im.convert("RGB"); im.thumbnail((cell - 8, cell - 8))
                sheet.paste(im, (x * cell + 4, Y + 32))
sheet.save(out / "cross.jpg", quality=85)
print("saved", out / "cross.jpg")
