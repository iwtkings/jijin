#!/usr/bin/env python3
"""红利 / 红利低波 主题基金全量重筛。

用法：
    tmp/.venv/bin/python tmp/screen_theme.py dividend
    tmp/.venv/bin/python tmp/screen_theme.py lowvol
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import refresh_lib as R  # noqa: E402

EXCLUDE_COMMON = ("港股", "恒生", "香港", "沪港深", "沪深港", "QDII",
                  "美元", "现汇", "现钞", "消费", "医药", "银行", "金融",
                  "地产", "科技", "互联网")


def pick(mode: str) -> list[dict]:
    cat = R.catalog()
    out = []
    for f in cat:
        n = f["name"]
        if not f["type"].startswith("指数型"):
            continue
        if "红利" not in n:
            continue
        if any(k in n for k in EXCLUDE_COMMON):
            continue
        if mode == "lowvol":
            if "低波" not in n and "低波动" not in n:
                continue
        else:
            if "低波" in n or "低波动" in n:
                continue
        out.append(f)
    return out


def enrich(funds: list[dict], mode: str) -> list[dict]:
    codes = [f["code"] for f in funds]
    dets = dict(zip(codes, R.parallel(R.detail, codes, workers=8)))
    mets = dict(zip(codes, R.parallel(R.metrics, codes, workers=8)))
    rows = []
    for f in funds:
        c = f["code"]
        d = dets[c]
        m = mets[c]
        if not m:
            continue
        idx = d.get("index") or ""
        if mode == "dividend" and ("低波" in idx or "低波" in f["name"]):
            continue
        if mode == "lowvol" and not ("低波" in idx or "低波" in f["name"]):
            continue
        rows.append({
            "code": c,
            "name": d.get("name") or f["name"],
            "cat_name": f["name"],
            "type": d.get("type") or f["type"],
            "index": d.get("index") or "",
            "estab": d.get("estab") or "",
            "scale_date": d.get("scale_date"),
            "scale": round((d.get("nav") or 0) / 1e8, 2),
            "fee": R.fee(d),
            "m1": m["1y"]["ann"] if m["1y"] else None,
            "m3": m["3y"]["ann"] if m["3y"] else None,
            "m5": m["5y"]["ann"] if m["5y"] else None,
            "since": m["since"]["ann"] if m["since"] else None,
            "vol3": m["3y"]["vol"] if m["3y"] else None,
            "mdd1": m["1y"]["mdd"] if m["1y"] else None,
            "mdd3": m["3y"]["mdd"] if m["3y"] else None,
            "last": m["last"],
        })
    rows.sort(key=lambda x: (x["m3"] is None, -(x["m3"] or 0)))
    return rows


def show(rows: list[dict], mode: str) -> None:
    print(f"\n{'='*120}\n{mode}  共 {len(rows)} 只\n{'='*120}")
    hdr = (f"{'代码':<7}{'名称':<34}{'跟踪指数':<24}{'成立':<11}"
           f"{'规模':>7}{'费率':>6}{'近1年':>9}{'近3年':>9}{'近5年':>9}{'成立来':>9}{'波动':>7}{'回撤1y':>8}")
    print(hdr)
    for r in rows:
        name = r["name"][:32]
        idx = (r["index"] or "")[:22]
        vol = f"{r['vol3'] * 100:.2f}%" if r["vol3"] else "—"
        print(f"{r['code']:<9}{name:<34}{idx:<24}{r['estab']:<11}"
              f"{r['scale']:>7.1f}{(r['fee'] or 0):>6.2f}"
              f"{R.pct(r['m1']):>9}{R.pct(r['m3']):>9}{R.pct(r['m5']):>9}"
              f"{R.pct(r['since']):>9}{vol:>7}"
              f"{R.pct(r['mdd1']):>8}")


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "dividend"
    funds = pick(mode)
    print("候选份额", len(funds))
    rows = enrich(funds, mode)
    (R.CACHE / f"theme_{mode}.json").write_text(
        __import__("json").dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    show(rows, mode)


if __name__ == "__main__":
    main()
