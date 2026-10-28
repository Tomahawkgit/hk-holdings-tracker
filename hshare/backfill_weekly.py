# -*- coding: utf-8 -*-
"""一次性回填：近 12 个 ISO 周每周一个 CCASS 快照。

同一 ISO 周已有快照（含月末回填点、周度任务点）则跳过，支持断点续跑。
用法：
  python backfill_weekly.py          # 全部股票
  python backfill_weekly.py 01024    # 单只（超时可重跑，自动续）
"""
import json, os, sys, time
from datetime import date as dt_date, timedelta

import build_dataset as bd
from ccass_fetch import fetch_ccass

BASE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(BASE, "config.json"), encoding="utf-8"))
INTERVAL = CFG.get("request_interval_sec", 2.0)
WEEKS = 12


def target_saturdays(n):
    """近 n 个周六（含本周）。CCASS 对非交易日自动回退到最后交易日。"""
    today = dt_date.today()
    sat = today + timedelta(days=(5 - today.weekday()) % 7)
    return [sat - timedelta(weeks=k) for k in range(n - 1, -1, -1)]


def run(only=None):
    for s in CFG["stocks"]:
        if only and s["code"] != only:
            continue
        code = s["code"]
        have = {bd.iso_week_key(r["date"]) for r in bd.read_monthly(code)}
        print(f"=== {s['name']} ({code}) ===", flush=True)
        for sat in target_saturdays(WEEKS):
            if bd.iso_week_key(sat.isoformat()) in have:
                print(f"  {sat.isoformat()} 所在周已有快照，跳过", flush=True)
                continue
            d = sat.strftime("%Y/%m/%d")
            try:
                snap = fetch_ccass(code, d)
            except Exception as e:
                print(f"  {d}: 抓取失败 {e!r}，跳过", flush=True)
                time.sleep(INTERVAL)
                continue
            time.sleep(INTERVAL)
            if not snap:
                print(f"  {d}: 无记录（上市前），跳过", flush=True)
                continue
            if bd.iso_week_key(snap["date"]) in have:
                print(f"  {d} -> {snap['date']} 同周已有点，跳过落盘", flush=True)
                continue
            buckets, top = bd.save_snapshot(code, snap)
            bd.update_monthly_csv(code, snap, buckets)
            have.add(bd.iso_week_key(snap["date"]))
            print(f"  回填 {snap['date']}: 南向={buckets['southbound']}% 外资={buckets['foreign']}%", flush=True)


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else None)
