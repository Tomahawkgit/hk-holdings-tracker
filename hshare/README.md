# 港股持仓结构周度跟踪 · 工具包说明（hshare/ 目录）

跟踪 6 只港股的 CCASS 持仓资金结构（南向 / 外资 / 中资 / 香港本地 / 境内股东H股），
每周自动更新，结果推送到 Kimi Work「港股持仓结构看板」。

> 本目录为仓库内 `hshare/`，脚本均按自身所在目录解析路径，整体可搬移。

## 跟踪名单（config.json）

| 代码 | 名称 | 备注 |
|---|---|---|
| 01024 | 快手-W | |
| 02026 | 小马智行-W | 2025-11 上市，2026-06 入港股通 |
| 00700 | 腾讯控股 | |
| 01211 | 比亚迪股份 | H 股几乎全额托管于 CCASS |
| 02513 | 智谱 | 2026-01 上市，境内股东H股占约 62% |
| 00100 | MINIMAX-W | 2026-01 上市，2026-07 全流通入托管 |

## 数据来源与归类口径

1. **CCASS 持股纪录**（港交所披露易）：`ccass_fetch.py` 直连查询表单，
   按「参与者」逐行解析持股比例。CCASS 网页只保留近 12 个月，
   本工具包每周落盘快照（`data/{code}/ccass_{date}.csv`），即自建历史档案。
2. **南向持股**（东方财富港股通接口）：`southbound_fetch.py`，日频全历史。
3. **参与者归类**（`classify.py` + `participant_map.csv` 字典，452 条已归类）：
   - `southbound` 南向资金：中国结算（港股通）A00003/A00004
   - `mainland` 境内股东H股：中国结算香港托管的境内股东持股（A00005，非交易性）
   - `foreign` 外资：汇丰、花旗、摩根大通、高盛等国际托管行/券商
   - `chinese` 中资：中银香港、国泰君安国际、招银国际等
   - `local` 香港本地：本地券商及银行
   - `other_ccass` / `non_ccass`：未归类中介、未入 CCASS 托管部分
   - 新出现的参与者编号会自动归入并记入 `unmapped_review.log`，**定期人工复核该文件**。

## 文件清单

| 文件 | 作用 |
|---|---|
| `config.json` | 跟踪名单 |
| `ccass_fetch.py` | CCASS 快照抓取（POST 回传表单） |
| `southbound_fetch.py` | 东财南向持股日频抓取 |
| `classify.py` | 参与者归类规则 + 字典持久化 |
| `participant_map.csv` | 参与者归类字典（可手工修订后跑 reclassify.py） |
| `build_dataset.py` | 全量回填 / 单票处理 / 合并产出 |
| `combine_offline.py` | 离线重建 widget_data.json（不访问 CCASS） |
| `reclassify.py` | 改归类规则后重建全部汇总 |
| `run_weekly.py` | 每周增量更新核心逻辑（失败自动回退本地数据） |
| `weekly_job.py` | **定时任务入口**（自动化运行器调用，输出 artifact） |
| `widget_data.json` | 小组件数据文件（当前+月度序列+南向日频+中介明细） |
| `data/{code}/` | 每股快照 CSV 与月度汇总 monthly.csv |
| `run_log.txt` | 每周运行日志 |
| `unmapped_review.log` | 新参与者待复核清单 |

## 定时任务

- 名称：港股持仓结构每周更新（`automation_28e3ac67-2b70-46d6-bae9-258ea890be77`）
- 触发：**每周一 09:17（Asia/Shanghai）**，cron `17 9 * * 1`
- 链路：运行 `weekly_job.py` → 重建 `widget_data.json` → 经绑定推送到小组件
  「港股持仓结构周度跟踪」（`widget_0c8a2d2b-a9fd-4a16-b4f8-36ede5037007`）→
  看板「港股持仓结构看板」（`canvas_efb2a932-24e5-40da-805f-29cf3863de7f`）
- 每次运行每股仅 1 次 CCASS 请求（往前探 4 天），低频友好。

## 手动操作

```bash
cd hk-holdings-tracker
python weekly_job.py            # 等价于一次定时任务
python run_weekly.py            # 只做增量更新，不产出 artifact
python combine_offline.py       # 离线重建 widget_data.json
python build_dataset.py 01024   # 单票全量回填（12 个月）
python reclassify.py            # 改归类规则后重建
```

依赖：Python 3.8+，`requests`、`beautifulsoup4`（Kimi Work 托管 Python 已自带）。

## 跨设备迁移

1. 整体复制 `hk-holdings-tracker/` 目录到新设备（`data/` 历史快照一并带走，否则历史无法重建——CCASS 只留 12 个月）。
2. 修改 `weekly_job.py` 顶部 `TRACKER_DIR` 为新设备的绝对路径。
3. 在 Kimi Work 中重建定时任务（入口指向新路径的 `weekly_job.py`）与小组件绑定；
   小组件页面 `index.html` 内联了一份数据兜底，迁移后跑一次任务即可刷新。

## 口径与免责说明

- CCASS 日期标签查周末时可能显示周末日期，数据实为最后交易日。
- 中介席位变动 ≠ 真实买卖（如腾讯 2026-07 高盛骤降/汇丰骤升属大宗席位搬家），
  解读趋势时以「类别汇总」为准，单个中介异动需谨慎。
- 港交所 CCASS 网页条款禁止程序化批量抓取；本工具保持每周每票 1 次的最低频率，
  请勿自行提高频率。
- 数据归类基于名称规则，仅供参考，不构成投资建议。
