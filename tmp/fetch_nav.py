#!/usr/bin/env python3
"""抓取代表基金全量净值（pingzhongdata），计算近 3 年年化、最大回撤、波动率、Calmar。

用 equityReturn（日涨跌幅）复利还原复权净值，与项目口径一致。
输出 tmp/data/nav/{code}.json 缓存。
"""

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import json
import math
import statistics
import time
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "tmp" / "data"
CACHE = DATA / "nav"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
TODAY = date(2026, 10, 18)
START_3Y = TODAY - timedelta(days=365 * 3)


def fetch(code: str) -> list:
    url = f"https://fund.eastmoney.com/pingzhongdata/{code}.js"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                txt = r.read().decode("utf-8", "ignore")
            break
        except Exception:  # noqa: BLE001
            if attempt == 2:
                return []
            time.sleep(1 + attempt)
    i = txt.find("Data_netWorthTrend = ")
    if i < 0:
        return []
    start = i + len("Data_netWorthTrend = ")
    depth = 0
    end = -1
    for k in range(start, len(txt)):
        ch = txt[k]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                end = k + 1
                break
    if end < 0:
        return []
    raw = txt[start:end]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def metrics(rows: list, start: str) -> dict | None:
    lo = date.fromisoformat(start)
    rows = [r for r in rows if r.get("equityReturn") is not None
            and date.fromtimestamp(r["x"] / 1000) >= lo]
    if len(rows) < 60:
        return None
    nav, peak, mdd = 1.0, 1.0, 0.0
    rets = []
    for r in rows:
        x = float(r["equityReturn"]) / 100
        nav *= 1 + x
        rets.append(x)
        peak = max(peak, nav)
        mdd = min(mdd, nav / peak - 1)
    d0 = date.fromtimestamp(rows[0]["x"] / 1000)
    d1 = date.fromtimestamp(rows[-1]["x"] / 1000)
    n = (d1 - d0).days
    if n < 300:
        return None
    ann = nav ** (365 / n) - 1
    vol = statistics.stdev(rets) * math.sqrt(252)
    return {
        "start": d0.isoformat(), "end": d1.isoformat(), "days": n,
        "ann": ann, "mdd": mdd, "vol": vol,
        "calmar": ann / abs(mdd) if mdd < 0 else None,
        "cum": nav - 1,
    }


def work(item: tuple) -> None:
    code, start = item
    p = CACHE / f"{code}.json"
    if p.exists():
        old = json.loads(p.read_text(encoding="utf-8"))
        if old.get("m"):
            return
    m = metrics(fetch(code), start)
    p.write_text(json.dumps({"code": code, "m": m}, ensure_ascii=False),
                 encoding="utf-8")


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    ms = json.loads((DATA / "metrics.json").read_text(encoding="utf-8"))
    items = []
    for x in ms:
        rep = x.get("rep")
        if not rep:
            continue
        # 近 3 年窗口；若经理任职不足 3 年，则从其任职日算起
        start = max(date.fromisoformat(rep["start"]), START_3Y).isoformat()
        items.append((rep["code"], start))
    items = list(dict.fromkeys(items))
    print("rep funds", len(items))
    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(work, items))
    ok = sum(1 for p in CACHE.glob("*.json")
             if json.loads(p.read_text(encoding="utf-8")).get("m"))
    print("with metrics", ok, "of", len(items))


if __name__ == "__main__":
    main()
