#!/usr/bin/env python3
"""输出入榜经理的表格行（Markdown），供人工写稿使用。"""

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "tmp" / "data"


def pct(v: float) -> str:
    return f"{v*100:+.2f}%"


def main() -> None:
    r = json.loads((DATA / "ranked.json").read_text(encoding="utf-8"))
    for board, n in (("equity", 20), ("fixed", 15)):
        rows = [x for x in r if x["board"] == board][:n]
        print(f"\n### {board} {len(rows)}")
        for i, x in enumerate(rows, 1):
            rep = x["rep"]
            ann = (1 + float(rep["ret"].replace("%", "").replace(",", "")) / 100) ** (
                365 / rep["days"]) - 1
            nav = x["nav"]
            print(
                f"| {i} | **{x['name']}** | {x['company']} | {x['days']/365:.1f}年 | "
                f"{x['scale_cur']:.1f} | **{rep['name']}（{rep['code']}）** | "
                f"{pct(ann)} | {pct(nav['ann'])} | {pct(nav['mdd'])} | "
                f"{nav['calmar']:.2f} | {x['score']:.1f} |")

    print("\n### hot funds")
    for board in ("equity", "fixed"):
        rows = [x for x in r if x["board"] == board][:5]
        for x in rows:
            m = json.loads((DATA / "mgr" / f"{x['id']}.json").read_text(encoding="utf-8"))
            perf = {p["code"]: p for p in m["perf"]}
            for f in x["top"][:2]:
                p = perf.get(f["code"], {})
                ann = (1 + float(f["ret"].replace("%", "").replace(",", "")) / 100) ** (
                    365 / f["days"]) - 1 if f["days"] else 0
                print(f"| **{x['name']}** | **{f['name']}（{f['code']}）** | {f['type']} | "
                      f"{float(f['scale']):.1f} | {f['days']/365:.1f}年 | "
                      f"{p.get('r1y','—')} | {pct(ann)} | {f['ret']} |")


if __name__ == "__main__":
    main()
