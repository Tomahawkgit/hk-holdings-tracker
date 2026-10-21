# -*- coding: utf-8 -*-
"""每周增量更新：每只股票只取最新一个 CCASS 快照 + 南向最新数据，追加进历史，重建 widget_data.json。

定时任务每周执行本脚本即可。新出现的 CCASS 参与者编号会记入 unmapped_review.log 供人工复核。
"""
import json, os
from datetime import date as dt_date

import build_dataset as bd

BASE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(BASE, "config.json"), encoding="utf-8"))


def run():
    log, results = [], []
    for s in CFG["stocks"]:
        try:
            res = bd.process_stock(s, backfill=False)
            results.append(res)
            if res["latest"]:
                b = res["latest"]["_buckets"]
                log.append(f"{s['name']}: {res['latest']['date']} 南向={b['southbound']}% 外资={b['foreign']}% 中资={b['chinese']}% 本地={b['local']}%")
            else:
                log.append(f"{s['name']}: 本期无新CCASS记录")
        except Exception as e:
            log.append(f"{s['name']}: 抓取失败 {e!r}，回退使用本地最新数据")
            # 回退：用本地已落盘的月末序列和最新快照，保证 widget_data.json 不缺口
            monthly = bd.read_monthly(s["code"])
            if monthly:
                last = monthly[-1]
                buckets, top = bd.load_snapshot_from_csv(s["code"], last["date"])
                latest = {"date": last["date"], "issued": int(last["issued"]),
                          "ccass_total_pct": float(last["ccass_total_pct"]),
                          "_buckets": buckets, "_top": top}
                try:
                    from southbound_fetch import fetch_southbound_daily
                    sb_daily = fetch_southbound_daily(s["code"])
                except Exception:
                    sb_daily = []
            else:
                latest, sb_daily = None, []
            results.append({"code": s["code"], "name": s["name"], "listed": s.get("listed"),
                            "lockups": s.get("lockups", []),
                            "sb_daily": sb_daily, "latest": latest, "verif": []})
    bd.build_widget_data(results)
    with open(os.path.join(BASE, "run_log.txt"), "a", encoding="utf-8") as f:
        f.write(f"\n=== {dt_date.today().isoformat()} ===\n" + "\n".join(log) + "\n")
    print("\n".join(log))


if __name__ == "__main__":
    run()
