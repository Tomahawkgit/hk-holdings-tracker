# -*- coding: utf-8 -*-
"""离线合并：从本地已落盘的快照/月度 CSV 重建 widget_data.json（不访问 CCASS）。
南向日频数据会重新拉取（东财接口轻量）。
"""
import json, os, sys

import build_dataset as bd
from southbound_fetch import fetch_southbound_daily

BASE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(BASE, "config.json"), encoding="utf-8"))


def main():
    results = []
    for s in CFG["stocks"]:
        code = s["code"]
        monthly = bd.read_monthly(code)
        if not monthly:
            print(f"{s['name']}: 无本地数据，先跑 build_dataset.py {code}")
            continue
        last = monthly[-1]
        buckets, top = bd.load_snapshot_from_csv(code, last["date"])
        latest = {"date": last["date"], "issued": int(last["issued"]),
                  "ccass_total_pct": float(last["ccass_total_pct"]),
                  "_buckets": buckets, "_top": top}
        sb_daily = fetch_southbound_daily(code)
        results.append({"code": code, "name": s["name"], "listed": s.get("listed"),
                        "lockups": s.get("lockups", []),
                        "sb_daily": sb_daily, "latest": latest, "verif": []})
        print(f"{s['name']}: {last['date']} ok")
    bd.build_widget_data(results)


if __name__ == "__main__":
    main()
