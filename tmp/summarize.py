#!/usr/bin/env python3
"""汇总经理指标，输出 tmp/data/metrics.json（不含净值回撤）。"""

from pathlib import Path
import json
import math

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "tmp" / "data"

EQUITY = ("普通股票", "偏股", "灵活", "平衡", "股票指数", "增强指数",
          "QDII-普通股票", "QDII-混合偏股", "混合型-偏股")
FIXED_PLUS = ("混合二级", "偏债")
MONEY = ("货币", "理财", "现金", "存单")


def num(s: str) -> float:
    t = (s or "").replace("%", "").replace(",", "").replace("--", "nan").strip()
    try:
        return float(t)
    except ValueError:
        return float("nan")


def fnum(s: str) -> float:
    try:
        return float((s or "").replace("--", "0"))
    except ValueError:
        return 0.0


def base_name(n: str) -> str:
    return n[:-1] if n[-1:] in "ABCDEFIH" and len(n) > 2 else n


def main() -> None:
    cands = json.loads((DATA / "candidates.json").read_text(encoding="utf-8"))
    out = []
    for c in cands:
        p = DATA / "mgr" / f"{c['id']}.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        funds = d["funds"]
        cur_raw = [f for f in funds if f["current"]]
        if not cur_raw:
            continue
        cur = cur_raw
        # A/C 去重，保留规模大的份额
        best = {}
        for f in cur:
            k = base_name(f["name"])
            sc = fnum(f["scale"])
            if k not in best or sc > fnum(best[k]["scale"]):
                best[k] = f
        cur = list(best.values())

        def ftype(f):
            return f["type"]

        def sc(f):
            return fnum(f["scale"])

        total = sum(sc(f) for f in cur)
        eq = sum(sc(f) for f in cur if any(k in ftype(f) for k in EQUITY))
        fx = sum(sc(f) for f in cur if any(k in ftype(f) for k in FIXED_PLUS))
        mm = sum(sc(f) for f in cur if any(k in ftype(f) for k in MONEY))
        if total <= 0:
            continue
        board = None
        if eq / total >= 0.5:
            board = "equity"
        elif fx / total >= 0.5:
            board = "fixed"
        if not board or mm / total >= 0.5:
            continue

        # 规模加权的任职年化（只含任职满 2 年的现任基金）
        num_w = 0.0
        den_w = 0.0
        for f in cur:
            r = num(f["ret"])
            if f["days"] >= 730 and not math.isnan(r):
                ann = (1 + r / 100) ** (365 / f["days"]) - 1
                w = max(sc(f), 0.01)
                num_w += ann * w
                den_w += w
        wann = num_w / den_w if den_w else None
        # 任职年化中位数，避免单只大产品绑架
        anns = sorted(
            (1 + num(f["ret"]) / 100) ** (365 / f["days"]) - 1
            for f in cur if f["days"] >= 730 and not math.isnan(num(f["ret"]))
        )
        med = anns[len(anns) // 2] if anns else None
        past = [f for f in funds if not f["current"]]
        churn = len(past) / len(funds) if funds else 0
        # 代表基金：从全部现任份额里选（A/C 去重会丢掉老份额），与榜单同类、
        # 任职满 3 年，优先主份额（A 类或无份额后缀），再按规模
        def same_board(f):
            t = f["type"]
            if "美元" in f["name"] or "现汇" in f["name"] or "现钞" in f["name"]:
                return False
            if board == "equity":
                return any(k in t for k in EQUITY)
            return any(k in t for k in FIXED_PLUS)

        cand = [f for f in cur_raw if f["days"] >= 1095 and same_board(f)]
        main = [f for f in cand
                if f["name"].endswith("A") or f["name"][-1:] not in "ABCDEFIH"]
        rep = max(main or cand, key=sc, default=None)
        # 展示用热门基金：老份额、主份额、按规模，按基础名称去重
        disp, seen = [], set()
        for f in sorted((f for f in cur_raw if f["days"] >= 1095 and same_board(f)),
                        key=lambda f: (f["name"].endswith("A")
                                       or f["name"][-1:] not in "ABCDEFIH", sc(f)),
                        reverse=True):
            k = base_name(f["name"])
            if k in seen:
                continue
            seen.add(k)
            disp.append(f)
            if len(disp) == 2:
                break
        out.append({
            **{k: c[k] for k in ("id", "name", "company", "days", "scale", "best")},
            "board": board,
            "n_current": len(cur),
            "scale_cur": round(total, 1),
            "wann": wann,
            "med": med,
            "churn": churn,
            "rep": ({k: rep[k] for k in ("code", "name", "type", "scale",
                                         "start", "days", "ret")} if rep else None),
            "top": [{"code": f["code"], "name": f["name"], "type": f["type"],
                     "scale": f["scale"], "days": f["days"], "ret": f["ret"]}
                    for f in disp],
        })
    (DATA / "metrics.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print(Counter(x["board"] for x in out), "total", len(out))
    print("with wann", sum(1 for x in out if x["wann"] is not None))


if __name__ == "__main__":
    main()
