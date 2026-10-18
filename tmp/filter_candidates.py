#!/usr/bin/env python3
"""从经理列表里筛候选，输出 tmp/data/candidates.json。"""

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "tmp" / "data"
rows = json.loads((DATA / "managers_raw.json").read_text(encoding="utf-8"))

MM = ("货币", "现金", "理财", "存单", "活期")


def scale(s: str) -> float:
    s = (s or "").replace("亿元", "").replace("--", "0")
    try:
        return float(s)
    except ValueError:
        return 0.0


cands = []
for r in rows:
    days = int(float(r[6] or 0))
    sc = scale(r[10])
    if days < 5 * 365 or sc < 50:
        continue
    codes = [c for c in (r[4] or "").split(",") if c]
    names = [n for n in (r[5] or "").split(",") if n]
    if not codes:
        continue
    mm_share = sum(1 for n in names if any(k in n for k in MM)) / len(names)
    if mm_share > 0.6:
        continue
    cands.append({
        "id": r[0], "name": r[1], "company": r[3],
        "days": days, "scale": sc, "codes": codes, "names": names,
        "best": r[7], "nfund": len(codes),
    })

cands.sort(key=lambda x: -x["scale"])
(DATA / "candidates.json").write_text(
    json.dumps(cands, ensure_ascii=False, indent=1), encoding="utf-8"
)
print("candidates", len(cands))
