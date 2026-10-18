#!/usr/bin/env python3
"""抓取候选经理详情页并解析现任/历任基金，结果缓存到 tmp/data/mgr/{id}.json。

用法：tmp/.venv/bin/python tmp/fetch_details.py
"""

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json
import re
import time
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "tmp" / "data"
CACHE = DATA / "mgr"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def to_days(s: str) -> int:
    m = re.match(r"(?:(\d+)年)?(?:又)?(?:(\d+)天)?", s or "")
    y = int(m.group(1) or 0)
    d = int(m.group(2) or 0)
    return y * 365 + d


def parse(html: str) -> dict:
    tables = re.findall(r"<table[^>]*>.*?</table>", html, re.S)
    funds, current = [], []
    if len(tables) >= 3:
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", tables[1], re.S):
            tds = [re.sub(r"<[^>]+>", "", c).strip()
                   for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
            if len(tds) != 8 or tds[0] == "基金代码":
                continue
            rng = tds[5]
            funds.append({
                "code": tds[0], "name": tds[1], "type": tds[3],
                "scale": tds[4], "range": rng,
                "days": to_days(tds[6]), "ret": tds[7],
                "current": rng.endswith("至今"),
                "start": rng.split("~")[0].strip(),
                "end": "" if rng.endswith("至今") else rng.split("~")[1].strip(),
            })
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", tables[2], re.S):
            tds = [re.sub(r"<[^>]+>", "", c).strip()
                   for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
            if len(tds) != 13 or tds[0] == "基金代码":
                continue
            current.append({
                "code": tds[0], "name": tds[1], "type": tds[2],
                "r3m": tds[3], "r6m": tds[5], "r1y": tds[7], "r2y": tds[9],
            })
    return {"funds": funds, "perf": current}


def grab(c: dict) -> None:
    path = CACHE / f"{c['id']}.json"
    if path.exists():
        return
    url = f"https://fund.eastmoney.com/manager/{c['id']}.html"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                html = r.read().decode("utf-8", "ignore")
            break
        except Exception as e:  # noqa: BLE001
            if attempt == 2:
                print("fail", c["id"], e)
                return
            time.sleep(1 + attempt)
    parsed = parse(html)
    parsed["id"] = c["id"]
    path.write_text(json.dumps(parsed, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    cands = json.loads((DATA / "candidates.json").read_text(encoding="utf-8"))
    todo = [c for c in cands if not (CACHE / f"{c['id']}.json").exists()]
    print("total", len(cands), "todo", len(todo))
    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(grab, todo))
    print("done", len(list(CACHE.glob("*.json"))))


if __name__ == "__main__":
    main()
