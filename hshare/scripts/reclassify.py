# -*- coding: utf-8 -*-
"""重归类：清空字典后，从已落盘的快照 CSV 重建 participant_map、monthly.csv 与 widget_data.json。
仅在调整归类规则后使用；不访问网络。
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import build_dataset as bd
import classify
from config import BASE, load_config

CFG = load_config()


def main():
    # 清空字典与复核日志，强制全量重归类
    for fn in ("participant_map.csv", "unmapped_review.log"):
        p = os.path.join(BASE, fn)
        if os.path.exists(p):
            os.remove(p)
    classify.reload_map()

    for s in CFG["stocks"]:
        code = s["code"]
        d = os.path.join(BASE, "data", code)
        monthly_path = os.path.join(d, "monthly.csv")
        if not os.path.exists(monthly_path):
            continue
        monthly = {r["date"]: r for r in bd.read_monthly(code)}
        new_rows = []
        for date, row in sorted(monthly.items()):
            snap_path = os.path.join(d, f"ccass_{date}.csv")
            if not os.path.exists(snap_path):
                continue
            cat_pcts = []
            entries = []
            with open(snap_path, encoding="utf-8-sig") as f:
                for r in csv.DictReader(f):
                    entries.append(r)
            for r in entries:
                cat = classify.classify(r["participant_code"], r["name"])
                cat_pcts.append((cat, float(r["pct"])))
                r["category"] = cat
            with open(snap_path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, fieldnames=["participant_code", "name", "category", "shares", "pct"])
                w.writeheader()
                w.writerows(entries)
            buckets = bd.aggregate_buckets(cat_pcts, float(row["ccass_total_pct"]))
            new_rows.append({
                "date": date, "issued": row["issued"], "ccass_total_pct": row["ccass_total_pct"],
                "southbound": buckets["southbound"], "foreign": buckets["foreign"],
                "chinese": buckets["chinese"], "local": buckets["local"],
                "mainland": buckets["mainland"],
                "other_ccass": buckets["other_ccass"], "non_ccass": buckets["non_ccass"],
            })
        with open(monthly_path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(new_rows[0].keys()))
            w.writeheader()
            w.writerows(new_rows)
        print(f"{s['name']}: 重归类完成，{len(new_rows)} 个月度点")

    print("现在跑 combine_offline.py 重建 widget_data.json")


if __name__ == "__main__":
    main()
