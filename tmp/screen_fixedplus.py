#!/usr/bin/env python3
"""固收+（二级债基 + 偏债混合）全量重筛，按近 3 年波动率分档。

口径与文档一致：
- 剔除 C/E/后端等重复份额；成立满 3 年；规模 ≥ 2 亿（2026-09-30）；
- 名称含转债/可转/定开/定期开放/封闭/持有 的剔除；
- 近 3 年波动率 > 15% 视为实质权益仓位，不纳入；
- 低波 ≤3%、中波 3%-6%、高波 6%-15%，各档按近 3 年年化取前 15。
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import refresh_lib as R  # noqa: E402

TYPES = ("债券型-混合二级", "混合型-偏债")
BAD_NAME = ("转债", "可转", "定开", "定期开放", "封闭", "持有", "后端")
SUFFIX = re.compile(r"(?:A|B|C|D|E|F|I|H|Y|R|O|后端)$")


def base_name(name: str) -> str:
    n = name.replace("A/B", "A")
    return SUFFIX.sub("", n)


def share_rank(name: str) -> int:
    if name.endswith("A") or name.endswith("A/B"):
        return 0
    if not SUFFIX.search(name):
        return 1
    if name.endswith("C"):
        return 2
    if name.endswith("E"):
        return 3
    return 4


def dedup(pool: list[dict]) -> list[dict]:
    best: dict[str, dict] = {}
    for f in pool:
        k = base_name(f["name"])
        old = best.get(k)
        if old is None or share_rank(f["name"]) < share_rank(old["name"]):
            best[k] = f
    return list(best.values())


def main() -> None:
    cat = R.catalog()
    raw = [f for f in cat if f["type"] in TYPES]
    print("初始份额", len(raw))
    pool = dedup(raw)
    print("去重后", len(pool))

    codes = [f["code"] for f in pool]
    dets = dict(zip(codes, R.parallel(R.detail, codes, workers=8)))

    step = {"dedup": len(pool)}
    todo3 = []
    for f in pool:
        d = dets[f["code"]]
        estab = d.get("estab") or ""
        scale = (d.get("nav") or 0) / 1e8
        if not estab or estab > "2023-10-30":
            continue
        todo3.append((f, d, scale))
    step["3y"] = len(todo3)

    todo_scale = [(f, d, s) for f, d, s in todo3 if s >= 2]
    step["scale"] = len(todo_scale)

    todo_name = [(f, d, s) for f, d, s in todo_scale
                 if not any(k in f["name"] for k in BAD_NAME)]
    step["name"] = len(todo_name)

    codes = [f["code"] for f, _, _ in todo_name]
    mets = dict(zip(codes, R.parallel(R.metrics, codes, workers=8)))
    todo_nav = [(f, d, s) for f, d, s in todo_name if mets[f["code"]] and mets[f["code"]]["3y"]]
    step["nav"] = len(todo_nav)

    rows = []
    dropped_vol = []
    for f, d, s in todo_nav:
        m = mets[f["code"]]
        vol = m["3y"]["vol"]
        if vol is None:
            continue
        if vol > 0.15:
            dropped_vol.append((f["code"], f["name"], vol))
            continue
        rows.append({
            "code": f["code"], "name": f["name"], "type": d.get("type") or f["type"],
            "estab": d.get("estab"), "scale": round(s, 2), "fee": R.fee(d),
            "m1": m["1y"]["ann"] if m["1y"] else None,
            "m3": m["3y"]["ann"], "m5": m["5y"]["ann"] if m["5y"] else None,
            "vol3": vol,
            "mdd1": m["1y"]["mdd"] if m["1y"] else None,
            "mdd3": m["3y"]["mdd"],
            "since": m["since"]["ann"] if m["since"] else None,
        })
    step["vol"] = len(rows)

    for r in rows:
        r["tier"] = "低波" if r["vol3"] <= 0.03 else ("中波" if r["vol3"] <= 0.06 else "高波")

    stats = {"steps": step, "counts": {}, "medians": {}, "ranges": {}}
    for tier in ("低波", "中波", "高波"):
        b = [r for r in rows if r["tier"] == tier]
        stats["counts"][tier] = len(b)
        vals = sorted(r["m3"] for r in b)
        stats["medians"][tier] = vals[len(vals) // 2] if vals else None
        stats["ranges"][tier] = {
            "m3_min": min(vals), "m3_max": max(vals),
            "vol_min": min(r["vol3"] for r in b),
            "vol_max": max(r["vol3"] for r in b),
            "mdd_min": min(r["mdd1"] for r in b if r["mdd1"] is not None),
            "mdd_max": max(r["mdd1"] for r in b if r["mdd1"] is not None),
        }
    full5 = [r for r in rows if r["m5"] is not None and r["m3"] is not None]
    stats["n5"] = len(full5)
    stats["n5_3gt5"] = sum(1 for r in full5 if r["m3"] > r["m5"])
    high5 = [r for r in full5 if r["tier"] == "高波"]
    stats["high5_n"] = len(high5)
    stats["high5_3gt5"] = sum(1 for r in high5 if r["m3"] > r["m5"])
    stats["dropped_vol"] = dropped_vol

    out = {"stats": stats, "rows": rows}
    (R.CACHE / "fixedplus.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print(json.dumps(stats, ensure_ascii=False, indent=1, default=str))
    for tier in ("低波", "中波", "高波"):
        print(f"\n===== {tier} 前 15 =====")
        b = sorted([r for r in rows if r["tier"] == tier],
                   key=lambda r: -r["m3"])[:15]
        for i, r in enumerate(b, 1):
            print(f"| {i} | **{r['name']}（{r['code']}）** | {r['type']} | "
                  f"{(r['estab'] or '')[:7]} | {r['scale']:.1f} | "
                  f"{R.pct(r['m1'])} | **{R.pct(r['m3'])}** | {R.pct(r['m5'])} | "
                  f"{r['vol3']*100:.2f}% | {R.pct(r['mdd1'])} | "
                  f"{(r['fee'] or 0):.2f}% |")
    print("\n===== 各档近 5 年前 5 =====")
    for tier in ("低波", "中波", "高波"):
        b = sorted([r for r in rows if r["tier"] == tier and r["m5"] is not None],
                   key=lambda r: -r["m5"])[:5]
        print(f"-- {tier}")
        for r in b:
            print(f"| {tier} | **{r['name']}（{r['code']}）** | {R.pct(r['m5'])} | "
                  f"{R.pct(r['m3'])} | {r['vol3']*100:.2f}% | {r['scale']:.1f} | "
                  f"{(r['fee'] or 0):.2f}% |")


if __name__ == "__main__":
    main()
