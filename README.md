# kimi 投资笔记本 · 数据与站点仓库

三条数据管线 + 一个静态站，服务公共站点 <https://invest-notebook.ok.kimi.link/>。

## 目录地图

| 目录 | 内容 | 自动任务 |
|---|---|---|
| `hshare/` | 港股持仓资金结构管线（CCASS + 港股通，6 只标的），详见 `hshare/README.md` | `weekly-update.yml` 每周一 09:30（北京） |
| `ashare/` | A股五层资金结构管线（2 只标的），详见 `ashare/README.md` | `ashare-weekly.yml` 每周一 10:30（北京） |
| `site/` | 网站全部文件：5 个页面 + 共享 `assets/`（CSS/JS）+ 2 个数据 JSON（发布到 Kimi 静态站的同源副本） | 代码手动回传，数据由管线自动同步 |

## 数据流

1. 管线在 GitHub Actions 运行，产出 `hshare/widget_data.json` / `ashare/ashare_data.json`，并自动同步到 `site/` 同名文件后一起提交回本仓库；
2. 网页按两级链拉取：raw.githubusercontent → jsDelivr → 站内同名 JSON；页面先渲染"加载中"占位，全部失败时提示重试；
3. 网站代码改动后回传 `site/`，保持本仓库为唯一事实源；数据 JSON 无需手工回传。

## 历史

- 2026-10-21：港股管线上云（此前在用户本地设备跑）
- 2026-10-26：A股管线建立（ashare/）
- 2026-10-28：仓库重组——港股脚本与 data/ 从根目录迁入 hshare/，与 ashare/ 平级
- 2026-11-03：网站重构——共享 assets/、侧栏 JS 注入、数据单点化（移除内联兜底，site/ JSON 自动同步）
