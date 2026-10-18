# tmp 目录说明

临时脚本与本地依赖，均不入库（`tmp/.venv/`、`tmp/data/` 已在 `.gitignore` 中）。

## 榜单复现步骤

`金牌基金经理排行.md` 的数据由下面这条流水线生成，按顺序执行：

```bash
tmp/.venv/bin/python tmp/fetch_managers.py     # 全量经理列表 → tmp/data/managers_raw.json
tmp/.venv/bin/python tmp/filter_candidates.py  # 从业 ≥5 年、规模 ≥50 亿，剔除货币 → candidates.json
tmp/.venv/bin/python tmp/fetch_details.py      # 逐个经理详情页 → tmp/data/mgr/*.json
tmp/.venv/bin/python tmp/summarize.py          # 现任基金、任职年化、代表基金 → metrics.json
tmp/.venv/bin/python tmp/fetch_nav.py          # 代表基金近 3 年净值 → tmp/data/nav/*.json
tmp/.venv/bin/python tmp/rank.py               # 六维打分 → ranked.json
tmp/.venv/bin/python tmp/dump_table.py         # 输出 Markdown 表格，供写稿校对
```

## 口径要点

- 数据源：天天基金经理列表（`FundDataPortfolio_Interface.aspx?dt=14`）、经理详情页、`pingzhongdata/{code}.js` 净值序列。
- 近 3 年收益与最大回撤：用日涨跌幅复利还原复权净值，窗口取 `max(经理任职起始日, 3 年前)`。
- 得分是同档内百分位加权，权重见《金牌基金经理评定标准》。
- 中间产物（`tmp/data/`）可随时删除，重跑脚本会重新抓取；全流程约 5 分钟。
