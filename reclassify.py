# -*- coding: utf-8 -*-
"""重归类：清空字典后，从已落盘的快照 CSV 重建 participant_map、monthly.csv 与 widget_data.json。
仅在调整归类规则后使用；不访问网络。
"""
import csv, json, os
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(BASE, "config.json"), encoding="utf-8"))

# 清空字典与复核日志，强制全量重归类
for fn in ("participant_map.csv", "unmapped_review.log"):
    p = os.path.join(BASE, fn)
    if os.path.exists(p):
        os.remove(p)

import classify  # noqa: E402  须在清空后加载
import build_dataset as bd  # noqa: E402

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
        buckets = defaultdict(float)
        entries = []
        with open(snap_path, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                entries.append(r)
        for r in entries:
            cat = classify.classify(r["participant_code"], r["name"])
            buckets[cat] += float(r["pct"])
            r["category"] = cat
        with open(snap_path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["participant_code", "name", "category", "shares", "pct"])
            w.writeheader()
            w.writerows(entries)
        ccass_total = float(row["ccass_total_pct"])
        buckets["other_ccass"] = round(max(ccass_total - sum(buckets.values()), 0), 2)
        buckets["non_ccass"] = round(max(100 - ccass_total, 0), 2)
        new_rows.append({
            "date": date, "issued": row["issued"], "ccass_total_pct": row["ccass_total_pct"],
            "southbound": round(buckets["southbound"], 2), "foreign": round(buckets["foreign"], 2),
            "chinese": round(buckets["chinese"], 2), "local": round(buckets["local"], 2),
            "mainland": round(buckets["mainland"], 2),
            "other_ccass": buckets["other_ccass"], "non_ccass": buckets["non_ccass"],
        })
    with open(monthly_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(new_rows[0].keys()))
        w.writeheader()
        w.writerows(new_rows)
    print(f"{s['name']}: 重归类完成，{len(new_rows)} 个月度点")

print("现在跑 combine_offline.py 重建 widget_data.json")
