#!/usr/bin/env python3
"""按代码打印刷新后的指标，供写稿核对。用法：tmp/.venv/bin/python tmp/show_codes.py 510880 515450 ..."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import refresh_lib as R  # noqa: E402


def main() -> None:
    codes = sys.argv[1:]
    for code in codes:
        d = R.detail(code)
        m = R.metrics(code)
        if not m:
            print(f"{code} {d.get('name')} 无净值数据")
            continue
        vol = f"{m['3y']['vol'] * 100:.2f}%" if m["3y"] and m["3y"]["vol"] else "—"
        print(f"{code} {d.get('name')} | {d.get('index')} | 成立 {d.get('estab')} | "
              f"规模 {R.yi(d.get('nav'))}亿 ({d.get('scale_date')}) | 费率 {R.fee(d)}")
        print(f"  近1年 {R.pct(m['1y']['ann'] if m['1y'] else None)} | "
              f"近3年 {R.pct(m['3y']['ann'] if m['3y'] else None)} | "
              f"近5年 {R.pct(m['5y']['ann'] if m['5y'] else None)} | "
              f"成立以来 {R.pct(m['since']['ann'] if m['since'] else None)} | "
              f"近3年波动 {vol} | 近1年回撤 {R.pct(m['1y']['mdd'] if m['1y'] else None)} | "
              f"近3年回撤 {R.pct(m['3y']['mdd'] if m['3y'] else None)} | 净值截至 {m['last']}")


if __name__ == "__main__":
    main()
