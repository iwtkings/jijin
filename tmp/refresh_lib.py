#!/usr/bin/env python3
"""数据刷新公共库：复权净值、规模、费率、基金类型。

数据源（天天基金/东方财富）：
- 全市场基金代码/类型：js/fundcode_search.js
- 阶段涨幅与规模：data/rankhandler.aspx（ft=zq / hh / zs / all）
- 复权净值序列：pingzhongdata/{code}.js（equityReturn 为日涨跌幅，复利还原）
- 规模、费率、成立日、类型：fundmobapi FundMNDetailInformation

口径：净值截至 2026-10-30（10-31 为周六），规模取 2026-09-30 三季报。
"""

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
import json
import math
import statistics
import time
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "tmp" / "data"
CACHE = DATA / "refresh"
NAVC = CACHE / "nav"
DETC = CACHE / "detail"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

END = date(2026, 10, 30)
SCALE_END = "2026-09-30"


def get(url: str, timeout: int = 30, retries: int = 4) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Referer": "https://fund.eastmoney.com/",
    })
    last = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(0.8 * (attempt + 1))
    raise RuntimeError(f"fetch failed: {url}: {last}")


def _dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- 基金目录
def catalog() -> list[dict]:
    p = CACHE / "catalog.json"
    if p.exists():
        return _load(p)
    txt = get("https://fund.eastmoney.com/js/fundcode_search.js")
    arr = json.loads(txt[txt.index("["): txt.rindex("]") + 1])
    rows = [{"code": a[0], "py": a[1], "name": a[2], "type": a[3]} for a in arr]
    _dump(p, rows)
    return rows


# ---------------------------------------------------------------- 阶段涨幅
RANK_FIELDS = (
    "code name py date unit acc day r1w r1m r3m r6m r1y r2y r3y "
    "ytd since estab _a _b rate_origin rate_now _c _d _e scale"
).split()


def rank_map(ft: str = "all", refresh: bool = False) -> dict[str, dict]:
    p = CACHE / f"rank_{ft}.json"
    if p.exists() and not refresh:
        return _load(p)
    url = ("https://fund.eastmoney.com/data/rankhandler.aspx?op=ph&dt=kf"
           f"&ft={ft}&rs=&gs=0&sc=1nzf&st=desc"
           f"&sd={END - timedelta(days=365)}&ed={END}"
           "&qdii=&tabSubtype=,,,,,&pi=1&pn=30000&dx=1&v=0.1")
    txt = get(url)
    body = txt[txt.index("["): txt.rindex("]") + 1]
    rows = json.loads(body)
    out = {}
    for r in rows:
        cells = r.split(",")
        if len(cells) < 25:
            continue
        d = dict(zip(RANK_FIELDS, cells))
        d["scale"] = _num(d.get("scale"))
        out[d["code"]] = d
    _dump(p, out)
    return out


def _num(s: str) -> float | None:
    t = (s or "").replace("%", "").replace(",", "").strip()
    if t in ("", "--", "---"):
        return None
    try:
        return float(t)
    except ValueError:
        return None


# ---------------------------------------------------------------- 净值序列
def nav_series(code: str) -> list[list]:
    p = NAVC / f"{code}.json"
    if p.exists():
        return _load(p)
    url = f"https://fund.eastmoney.com/pingzhongdata/{code}.js"
    try:
        txt = get(url, timeout=40)
    except RuntimeError:
        _dump(p, [])
        return []
    i = txt.find("Data_netWorthTrend = ")
    if i < 0:
        _dump(p, [])
        return []
    start = i + len("Data_netWorthTrend = ")
    depth, end = 0, -1
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
        _dump(p, [])
        return []
    try:
        raw = json.loads(txt[start:end])
    except json.JSONDecodeError:
        raw = []
    rows = [[int(r["x"]), r.get("equityReturn")] for r in raw
            if r.get("equityReturn") is not None]
    _dump(p, rows)
    return rows


def _date(ts_ms: int) -> date:
    return datetime.fromtimestamp(ts_ms / 1000).date()


def _window(rows: list[list], years: float) -> list[list]:
    if not rows:
        return []
    end = _date(rows[-1][0])
    # 用日历日回溯，再取区间内第一条
    lo = end - timedelta(days=int(round(365 * years)))
    return [r for r in rows if _date(r[0]) >= lo]


def _stats(sub: list[list]) -> dict | None:
    if len(sub) < 20:
        return None
    nav = peak = 1.0
    mdd = 0.0
    rets = []
    for _, x in sub:
        r = float(x) / 100.0
        nav *= 1 + r
        rets.append(r)
        peak = max(peak, nav)
        mdd = min(mdd, nav / peak - 1)
    d0, d1 = _date(sub[0][0]), _date(sub[-1][0])
    days = (d1 - d0).days
    return {
        "cum": nav - 1,
        "ann": nav ** (365 / days) - 1 if days > 0 else None,
        "mdd": mdd,
        "days": days,
        "start": d0.isoformat(),
        "end": d1.isoformat(),
        "vol": statistics.stdev(rets) * math.sqrt(252) if len(rets) > 2 else None,
    }


def metrics(code: str) -> dict | None:
    rows = nav_series(code)
    if not rows:
        return None
    first = _date(rows[0][0])
    last = _date(rows[-1][0])
    out = {"code": code, "last": last.isoformat()}
    for label, years in (("1y", 1), ("3y", 3), ("5y", 5)):
        # 成立不足对应年限的，不给该窗口年化（避免把“成立以来”当成 3 年）
        if first > last - timedelta(days=int(365 * years) - 10):
            out[label] = None
        else:
            out[label] = _stats(_window(rows, years))
    # 成立以来
    out["since"] = _stats(rows) if len(rows) >= 20 else None
    return out


# ---------------------------------------------------------------- 基金详情
def detail(code: str) -> dict:
    p = DETC / f"{code}.json"
    if p.exists():
        return _load(p)
    url = ("https://fundmobapi.eastmoney.com/FundMNewApi/FundMNDetailInformation"
           f"?FCODE={code}&deviceid=1&plat=Android&product=EFund&version=6.2.8")
    try:
        j = json.loads(get(url))
        d = j.get("Datas") or {}
    except Exception:  # noqa: BLE001
        d = {}
    out = {
        "code": code,
        "name": d.get("SHORTNAME"),
        "type": d.get("FTYPE"),
        "estab": d.get("ESTABDATE"),
        "scale_date": d.get("FEGMRQ"),
        "nav": _num(d.get("ENDNAV")),
        "mgmt": d.get("MGREXP"),
        "trust": d.get("TRUSTEXP"),
        "manager": d.get("JJJL"),
        "index": d.get("INDEXNAME") or d.get("BENCH"),
    }
    _dump(p, out)
    return out


def fee(d: dict) -> float | None:
    a, b = _num(d.get("mgmt")), _num(d.get("trust"))
    if a is None and b is None:
        return None
    return (a or 0) + (b or 0)


def parallel(fn, items, workers: int = 6):
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(fn, items))


def pct(v, digits: int = 2) -> str:
    return "—" if v is None else f"{v * 100:+.{digits}f}%"


def yi(v) -> str:
    return "—" if v is None else f"{v / 1e8:.1f}"
