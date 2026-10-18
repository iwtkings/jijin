#!/usr/bin/env python3
"""按《金牌基金经理评定标准》的六维权重打分，输出 tmp/data/ranked.json。

权重：任职年限 20 / 收益分位 25 / 风险调整 20 / 收益一致性 15 / 稳定性 10 / 规模 10
"""

from pathlib import Path
import json
import math

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "tmp" / "data"


def pct(vals: list, v: float) -> float:
    if v is None:
        return 0.0
    n = len(vals)
    if n <= 1:
        return 50.0
    return 100 * sum(1 for x in vals if x < v) / (n - 1)


def main() -> None:
    ms = json.loads((DATA / "metrics.json").read_text(encoding="utf-8"))
    rows = []
    for x in ms:
        rep = x.get("rep")
        if not rep or x["wann"] is None:
            continue
        p = DATA / "nav" / f"{rep['code']}.json"
        if not p.exists():
            continue
        m = json.loads(p.read_text(encoding="utf-8"))["m"]
        if not m or not m.get("calmar"):
            continue
        x["nav"] = m
        rows.append(x)

    out = []
    for board in ("equity", "fixed"):
        b = [x for x in rows if x["board"] == board]
        wann = [x["wann"] for x in b]
        cal = [x["nav"]["calmar"] for x in b]
        ten = [x["days"] for x in b]
        sc = [math.log(max(x["scale_cur"], 1)) for x in b]
        for x in b:
            gap = abs(x["wann"] - (x["med"] or x["wann"]))
            cons = max(0.0, 1 - gap / max(abs(x["wann"]), 0.05))
            stab = max(0.0, 1 - x["churn"])
            x["parts"] = {
                "tenure": pct(ten, x["days"]),
                "return": pct(wann, x["wann"]),
                "risk": pct(cal, x["nav"]["calmar"]),
                "cons": cons * 100,
                "stab": stab * 100,
                "scale": pct(sc, math.log(max(x["scale_cur"], 1))),
            }
            x["score"] = round(
                0.20 * x["parts"]["tenure"]
                + 0.25 * x["parts"]["return"]
                + 0.20 * x["parts"]["risk"]
                + 0.15 * x["parts"]["cons"]
                + 0.10 * x["parts"]["stab"]
                + 0.10 * x["parts"]["scale"], 1)
            out.append(x)

    out.sort(key=lambda x: (x["board"], -x["score"]))
    (DATA / "ranked.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    for board in ("equity", "fixed"):
        b = [x for x in out if x["board"] == board]
        print(f"\n== {board} {len(b)}")
        for i, x in enumerate(b[:20], 1):
            print(f"{i:2d} {x['score']:5.1f} {x['name']:4s} {x['days']/365:4.1f}y "
                  f"{x['scale_cur']:7.1f}亿 wann{x['wann']*100:6.2f} "
                  f"3y{x['nav']['ann']*100:6.2f} mdd{x['nav']['mdd']*100:7.2f} "
                  f"cal{x['nav']['calmar']:5.2f} {x['company'][:8]:8s} {x['rep']['name'][:16]}")


if __name__ == "__main__":
    main()
