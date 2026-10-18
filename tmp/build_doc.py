#!/usr/bin/env python3
"""从项目根目录的 Markdown 生成 docs/ 下的 HTML 文档与目录页。

用法（不要直接 pip install，Homebrew Python 受 PEP 668 限制）：
    python3 -m venv tmp/.venv
    tmp/.venv/bin/pip install -r tmp/requirements.txt
    tmp/.venv/bin/python tmp/build_doc.py
"""

from pathlib import Path
import re
import sys

try:
    import markdown
except ImportError:
    sys.exit(
        "缺少 markdown 依赖，请先在项目根目录运行：\n"
        "  python3 -m venv tmp/.venv\n"
        "  tmp/.venv/bin/pip install -r tmp/requirements.txt\n"
        "  tmp/.venv/bin/python tmp/build_doc.py"
    )

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs"

DOCS = [
    {
        "src": "红利基金年化收益排行.md",
        "out": "红利基金年化收益排行.html",
        "title": "A 股红利基金年化收益排行梳理",
        "tag": "宽基红利",
        "desc": "覆盖央企/国企红利、中证红利、上证红利、深证红利、红利质量、红利潜力等 A 股红利指数基金，按近 3 年、近 5 年年化收益排序，并对比规模与费率。",
        "meta": "16 只主榜 · 近 3 年 / 近 5 年",
    },
    {
        "src": "红利低波基金年化收益排行.md",
        "out": "红利低波基金年化收益排行.html",
        "title": "红利低波基金年化收益排行梳理",
        "tag": "红利低波",
        "desc": "聚焦标普红利低波 50、中证红利低波、红利低波 100 等产品，对比近 3 年/近 5 年年化、规模、费率与跟踪指数差异。",
        "meta": "5 只主榜 · 近 3 年 / 近 5 年",
    },
    {
        "src": "固收+基金年化收益排行.md",
        "out": "固收+基金年化收益排行.html",
        "title": "固收+基金年化收益排行梳理（低波 / 中波 / 高波）",
        "tag": "固收+",
        "desc": "覆盖二级债基与偏债混合基金，按近 3 年波动率分低/中/高三档，对比近 3 年、近 5 年年化、回撤、规模与费率。",
        "meta": "335 只入样 · 低 / 中 / 高波",
    },
    {
        "src": "金牌基金经理评定标准.md",
        "out": "金牌基金经理评定标准.html",
        "title": "金牌基金经理评定标准",
        "tag": "方法论",
        "desc": "从任职年限、收益质量、风险形状、稳定性与规模费率六个维度评定基金经理，附打分表、取数路径与核对清单。",
        "meta": "六层筛法 · 打分表 · 核对清单",
    },
    {
        "src": "金牌基金经理排行.md",
        "out": "金牌基金经理排行.html",
        "title": "金牌基金经理排行（权益 / 固收+）",
        "tag": "经理排行",
        "desc": "按六维打分对 259 位任职满 5 年、在管规模 50 亿以上的经理排序，分权益与固收+两榜，并列出各自管理的热门基金。",
        "meta": "259 位入样 · 权益 / 固收+",
    },
]


def convert(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    # 原文子列表用 2 空格缩进，Python-Markdown 需要 4 空格才会嵌套
    text = re.sub(r"(?m)^  - ", "    - ", text)
    md = markdown.Markdown(
        extensions=["tables", "sane_lists"],
        output_format="html5",
    )
    body = md.convert(text)
    # 让宽表格在窄屏可横向滚动
    body = body.replace("<table>", '<div class="table-wrap"><table>')
    body = body.replace("</table>", "</table></div>")
    return body


PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · 基金理财研究</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<header class="site-header">
  <div class="wrap header-inner">
    <a class="brand" href="index.html">基金理财研究</a>
    <nav class="site-nav"><a href="index.html">文档目录</a></nav>
  </div>
</header>
<main class="wrap">
  <div class="back"><a href="index.html">← 返回目录</a></div>
  <article class="doc">
{body}
  </article>
</main>
<footer class="site-footer">
  <div class="wrap">数据截至 2026-10-16 · 历史收益不代表未来表现 · 仅作数据梳理，不构成投资建议</div>
</footer>
</body>
</html>
"""

INDEX = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>基金理财研究 · 文档目录</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<header class="site-header">
  <div class="wrap header-inner">
    <a class="brand" href="index.html">基金理财研究</a>
    <nav class="site-nav"><span>文档目录</span></nav>
  </div>
</header>
<main class="wrap">
  <section class="hero">
    <p class="eyebrow">基金理财 · 研究文档</p>
    <h1>基金理财研究</h1>
    <p class="lead">A 股红利、红利低波与固收+产品的年化收益、规模、费率对比，基金经理的评定方法、排行与在管产品。收益按复权净值计算，含分红再投资；年化为几何年化。</p>
  </section>

  <section class="cards">
{cards}
  </section>

  <section class="note">
    <h3>阅读说明</h3>
    <ul>
      <li>红利两篇口径不同：宽基红利不含红利低波，红利低波单独成篇；固收+按近 3 年波动率分低/中/高三档，不与红利混排。</li>
      <li>《金牌基金经理评定标准》是方法论文档，《金牌基金经理排行》按该标准对权益与固收+经理分榜排序，两张榜的分数不可跨榜比较。</li>
      <li>收益数据截至 2026-10-16，规模数据截至 2026-06-30；费率 = 管理费 + 托管费，不含申购费与销售服务费。</li>
      <li>“近 3 年年化”是平均每年的复利年化，不是三年收益加总，也不是年度收益的算术平均。</li>
    </ul>
  </section>
</main>
<footer class="site-footer">
  <div class="wrap">历史收益不代表未来表现 · 仅作数据梳理，不构成投资建议</div>
</footer>
</body>
</html>
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    for doc in DOCS:
        body = convert(ROOT / doc["src"])
        page = PAGE.format(title=doc["title"], body=body)
        (OUT / doc["out"]).write_text(page, encoding="utf-8")

    cards = "\n".join(
        f'''      <a class="card" href="{d["out"]}">
        <div class="card-top"><span class="tag">{d["tag"]}</span><span class="arrow">→</span></div>
        <h2>{d["title"]}</h2>
        <p>{d["desc"]}</p>
        <div class="card-meta"><span>{d["meta"]}</span><span>2026-10-16</span></div>
      </a>'''
        for d in DOCS
    )
    (OUT / "index.html").write_text(INDEX.format(cards=cards), encoding="utf-8")

    print("已生成：")
    for name in ["index.html"] + [d["out"] for d in DOCS]:
        print(f"  docs/{name}")


if __name__ == "__main__":
    main()
