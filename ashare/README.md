# A股资金结构五层跟踪（ashare-tracker）

仿照 hk-holdings-tracker 的云端管线，用东方财富公开免密接口产出 `ashare_data.json`，
供「A股资金结构五层面板」页面远程拉取。

## 部署步骤

1. 把本文件夹整体复制到 `hk-holdings-tracker` 仓库根目录，目录名保持 `ashare/`
   （页面拉取路径已写死为 `ashare/ashare_data.json`）。
2. 把 `ashare-weekly.yml` 放到仓库的 `.github/workflows/` 目录下。
3. 推送后到 Actions 页面对 `ashare-weekly-update` 点一次 `Run workflow` 手动试跑，
   确认 `ashare/ashare_data.json` 出现在仓库里即完成。
4. 之后每周一 10:30（北京时间）自动更新；季报期会自动吸收新的股东/机构/户数数据。

## 股票池与层级映射

- `config.json` → `stocks`：跟踪标的列表，照格式加票即可（code/secucode/name）。
- `config.json` → `layer_map`：股东名→五层的人工映射（控股股东、回购专户、
  主权基金等关键词盖不住的特例）。脚本跑完会把没归类的股东写进
  `unmapped_holders.log`，按提示补进 `layer_map` 即可。

## 五层口径

产业资本（控股股东/员工持股/回购专户）· 外资（香港中央结算/QFII/主权基金）·
境内机构（公募/私募/保险/社保/券商）· 游资（龙虎榜席位）· 散户（其余个人，
以户数+两融为代理）。A 股无全量席位登记，不画全量饼图，各层卡片标注自己的
数据频率与期日。

## 已知缺口（外部季度补位，不阻塞周更）

- 回购明细、主动/被动公募拆分：公开免密接口不可用，由外部数据源季度补。
- 主力资金日频：push2his 接口在部分网络不可达，失败自动降级为空并标注。
- 北向：2024-08 起仅季度披露（香港中央结算），页面只做季频边际对比。
