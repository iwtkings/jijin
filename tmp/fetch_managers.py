#!/usr/bin/env python3
"""抓取天天基金经理列表（dt=14），存为 tmp/data/managers_raw.json。

用法：tmp/.venv/bin/python tmp/fetch_managers.py
"""

from pathlib import Path
import json
import re
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tmp" / "data"
BASE = "https://fund.eastmoney.com/Data/FundDataPortfolio_Interface.aspx"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def fetch(ft: str, page: int, pn: int = 200) -> dict:
    q = urllib.parse.urlencode(
        {"dt": 14, "mc": "returnjson", "ft": ft, "pn": pn, "pi": page,
         "sc": "abbname", "st": "asc"}
    )
    req = urllib.request.Request(f"{BASE}?{q}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        txt = r.read().decode("utf-8")
    # 返回的是 JS 字面量（键不带引号），只取 data 数组
    m = re.search(r"data:(\[\[.*?\]\])", txt, re.S)
    if not m:
        return {"data": [], "pages": 0}
    pages = re.search(r"pages:\"?(\d+)", txt)
    return {"data": json.loads(m.group(1)),
            "pages": int(pages.group(1)) if pages else 0}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    all_rows = []
    page = 1
    while True:
        d = fetch("all", page)
        rows = d.get("data") or []
        all_rows.extend(rows)
        pages = int(d.get("pages") or 0)
        print(f"page {page}/{pages} rows={len(rows)} total={len(all_rows)}")
        if page >= pages or not rows:
            break
        page += 1
        time.sleep(0.3)
    (OUT / "managers_raw.json").write_text(
        json.dumps(all_rows, ensure_ascii=False), encoding="utf-8"
    )
    print("saved", len(all_rows))


if __name__ == "__main__":
    main()
