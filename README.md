# kimi 投资笔记本 · 数据与站点仓库

三条数据管线 + 一个静态站，服务公共站点 <https://invest-notebook.ok.kimi.link/>。

## 目录地图

| 目录 | 内容 | 自动任务 |
|---|---|---|
| `hshare/` | 港股持仓资金结构管线（CCASS + 港股通，6 只标的），详见 `hshare/README.md` | `weekly-update.yml` 每周一 09:30（北京） |
| `ashare/` | A股五层资金结构管线（2 只标的），详见 `ashare/README.md` | `ashare-weekly.yml` 每周一 10:30（北京） |
| `site/` | 网站全部文件：5 个页面 + 2 个兜底 JSON（发布到 Kimi 静态站的同源副本） | 手动回传 |

## 数据流

1. 管线在 GitHub Actions 运行，产出 `hshare/widget_data.json` / `ashare/ashare_data.json` 并提交回本仓库；
2. 网页按三级链拉取：raw.githubusercontent → jsDelivr → 站内同名 JSON → 页内 FALLBACK_DATA；
3. 网站文件改动后回传 `site/`，保持本仓库为唯一事实源。

## 历史

- 2026-10-21：港股管线上云（此前在用户本地设备跑）
- 2026-10-26：A股管线建立（ashare/）
- 2026-10-28：仓库重组——港股脚本与 data/ 从根目录迁入 hshare/，与 ashare/ 平级
