# -*- coding: utf-8 -*-
"""离线合并：从本地已落盘的快照/月度 CSV 重建 widget_data.json（不访问 CCASS）。
南向日频数据会重新拉取（东财接口轻量）。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import build_dataset as bd
from config import load_config

CFG = load_config()


def main():
    results = []
    for s in CFG["stocks"]:
        code = s["code"]
        latest, sb_daily = bd.build_local_latest(code)
        if not latest:
            print(f"{s['name']}: 无本地数据，先跑 build_dataset.py {code}")
            continue
        results.append({"code": code, "name": s["name"], "listed": s.get("listed"),
                        "lockups": s.get("lockups", []),
                        "sb_daily": sb_daily, "latest": latest, "verif": []})
        print(f"{s['name']}: {latest['date']} ok")
    bd.build_widget_data(results)


if __name__ == "__main__":
    main()
