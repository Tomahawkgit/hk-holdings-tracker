# -*- coding: utf-8 -*-
"""数据集构建：回填近12个月月末 CCASS 快照 + 南向全历史，生成 widget_data.json。

用法：
  python3 build_dataset.py            # 全部股票回填（首次）
  python3 build_dataset.py 01024      # 单只
"""
import csv, json, os, sys, time
from datetime import date as dt_date

import classify
from ccass_fetch import fetch_ccass
from southbound_fetch import fetch_southbound_daily

BASE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(BASE, "config.json"), encoding="utf-8"))
INTERVAL = CFG.get("request_interval_sec", 2.0)


def data_dir(code):
    d = os.path.join(BASE, "data", code)
    os.makedirs(d, exist_ok=True)
    return d


def month_ends(n=12):
    """近 n 个月的月末自然日（不含当月）。"""
    today = dt_date.today()
    y, m = today.year, today.month
    out = []
    for _ in range(n):
        m -= 1
        if m == 0:
            m, y = 12, y - 1
        if m == 12:
            nxt = dt_date(y + 1, 1, 1)
        else:
            nxt = dt_date(y, m + 1, 1)
        out.append((nxt.toordinal() and dt_date.fromordinal(nxt.toordinal() - 1)).strftime("%Y/%m/%d"))
    return list(reversed(out))


def save_snapshot(code, snap):
    """快照原始行落盘 + 归类汇总，返回 bucket dict。"""
    d = data_dir(code)
    path = os.path.join(d, f"ccass_{snap['date']}.csv")
    buckets = {"southbound": 0.0, "foreign": 0.0, "chinese": 0.0, "local": 0.0, "mainland": 0.0}
    top = []
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["participant_code", "name", "category", "shares", "pct"])
        for pcode, name, shares, pct in snap["rows"]:
            cat = classify.classify(pcode, name)
            buckets[cat] += pct
            w.writerow([pcode, name, cat, shares, pct])
            top.append({"name": name, "cat": cat, "pct": pct, "shares": shares})
    ccass_total = snap["ccass_total_pct"] or sum(buckets.values())
    buckets["other_ccass"] = round(max(ccass_total - sum(buckets.values()), 0), 2)
    buckets["non_ccass"] = round(max(100 - ccass_total, 0), 2)
    for k in ("southbound", "foreign", "chinese", "local", "mainland"):
        buckets[k] = round(buckets[k], 2)
    return buckets, sorted(top, key=lambda x: -x["pct"])[:12]


def update_monthly_csv(code, snap, buckets):
    path = os.path.join(data_dir(code), "monthly.csv")
    rows = []
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
    rows = [r for r in rows if r["date"] != snap["date"]]
    rows.append({
        "date": snap["date"], "issued": snap["issued"], "ccass_total_pct": snap["ccass_total_pct"],
        "southbound": buckets["southbound"], "foreign": buckets["foreign"],
        "chinese": buckets["chinese"], "local": buckets["local"], "mainland": buckets["mainland"],
        "other_ccass": buckets["other_ccass"], "non_ccass": buckets["non_ccass"],
    })
    rows.sort(key=lambda r: r["date"])
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def load_snapshot_from_csv(code, date):
    """从已落盘的快照 CSV 重建 buckets 与 top（用于 latest 已存在时）。"""
    path = os.path.join(data_dir(code), f"ccass_{date}.csv")
    buckets = {"southbound": 0.0, "foreign": 0.0, "chinese": 0.0, "local": 0.0, "mainland": 0.0}
    top = []
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            buckets[r["category"]] += float(r["pct"])
            top.append({"name": r["name"], "cat": r["category"], "pct": float(r["pct"]), "shares": int(r["shares"])})
    row = next((r for r in read_monthly(code) if r["date"] == date), None)
    if row:
        buckets["other_ccass"] = float(row["other_ccass"])
        buckets["non_ccass"] = float(row["non_ccass"])
    for k in ("southbound", "foreign", "chinese", "local", "mainland"):
        buckets[k] = round(buckets[k], 2)
    return buckets, sorted(top, key=lambda x: -x["pct"])[:12]


def process_stock(stock, backfill=True):
    code, name = stock["code"], stock["name"]
    print(f"=== {name} ({code}) ===", flush=True)
    sb_daily = fetch_southbound_daily(code)
    time.sleep(INTERVAL)

    dates = month_ends(CFG["months_back"]) if backfill else []
    latest = None
    for d in dates:
        snap = fetch_ccass(code, d)
        time.sleep(INTERVAL)
        if not snap:
            print(f"  {d}: 无记录（上市前/非交易日），跳过")
            continue
        buckets, top = save_snapshot(code, snap)
        update_monthly_csv(code, snap, buckets)
        snap["_buckets"], snap["_top"] = buckets, top
        latest = snap
        print(f"  {snap['date']}: CCASS={snap['ccass_total_pct']}% 南向={buckets['southbound']}%")

    # 最新快照：从今天往前最多探 4 天（当日盘后才有数据）
    existing = {r["date"] for r in read_monthly(code)}
    for k in range(0, 5):
        probe = dt_date.fromordinal(dt_date.today().toordinal() - k).strftime("%Y/%m/%d")
        snap = fetch_ccass(code, probe)
        time.sleep(INTERVAL)
        if snap:
            if snap["date"] not in existing:
                buckets, top = save_snapshot(code, snap)
                update_monthly_csv(code, snap, buckets)
                snap["_buckets"], snap["_top"] = buckets, top
                print(f"  最新 {snap['date']}: CCASS={snap['ccass_total_pct']}% 南向={buckets['southbound']}%")
            else:
                buckets, top = load_snapshot_from_csv(code, snap["date"])
                snap["_buckets"], snap["_top"] = buckets, top
            latest = snap
            break

    # 校验：CCASS 南向合计 vs 东财同月最后一个交易日（只校验每月最后一个快照点，
    # 月中周度点与月末东财值存在合理差异，不参与校验）
    verif = []
    em_by_date = {r["date"]: r["ratio"] for r in sb_daily}
    em_sorted = sorted(em_by_date.items())
    for r in pick_period_rows(read_monthly(code), lambda d: d[:7]):
        ym = r["date"][:7]
        em_month = [v for d2, v in em_sorted if d2.startswith(ym)]
        if em_month:
            em_val = em_month[-1]
            verif.append({"date": r["date"], "ccass_sb": float(r["southbound"]),
                          "em_sb": em_val, "ok": abs(float(r["southbound"]) - em_val) < 0.05})

    return {"code": code, "name": name, "listed": stock.get("listed"),
            "lockups": stock.get("lockups", []),
            "sb_daily": sb_daily, "latest": latest, "verif": verif}


def read_monthly(code):
    path = os.path.join(data_dir(code), "monthly.csv")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def series_point(r):
    return {
        "date": r["date"], "ccass_total": float(r["ccass_total_pct"]),
        "southbound": float(r["southbound"]), "foreign": float(r["foreign"]),
        "chinese": float(r["chinese"]), "local": float(r["local"]), "mainland": float(r.get("mainland") or 0),
        "other_ccass": float(r["other_ccass"]), "non_ccass": float(r["non_ccass"]),
    }


def pick_period_rows(rows, key_fn):
    """每个周期（月/ISO周）保留日期最晚的一行，按月/周排序返回。"""
    out = {}
    for r in rows:
        out[key_fn(r["date"])] = r
    return [out[k] for k in sorted(out)]


def iso_week_key(dstr):
    y, w, _ = dt_date.fromisoformat(dstr).isocalendar()
    return f"{y}-W{w:02d}"


def build_widget_data(results):
    stocks = []
    for res in results:
        code = res["code"]
        rows = read_monthly(code)
        # 月度序列：每月最后一个快照点
        series = [series_point(r) for r in pick_period_rows(rows, lambda d: d[:7])]
        # 周度序列：以最新快照为锚，近 12 周（84 天窗口）内每个 ISO 周最后一个点
        if rows:
            anchor = max(dt_date.fromisoformat(r["date"]).toordinal() for r in rows)
            wrows = [r for r in rows if dt_date.fromisoformat(r["date"]).toordinal() >= anchor - 83]
        else:
            wrows = []
        weekly = [series_point(r) for r in pick_period_rows(wrows, iso_week_key)]
        latest = res["latest"]
        current = None
        if latest:
            current = {"date": latest["date"], "issued": latest["issued"],
                       "ccass_total_pct": latest["ccass_total_pct"],
                       "buckets": latest["_buckets"], "top": latest["_top"]}
        sb = res["sb_daily"]
        stocks.append({
            "code": code, "name": res["name"], "listed": res["listed"],
            "lockups": res.get("lockups", []),
            "current": current, "series": series, "weekly_series": weekly,
            "southbound_daily": sb[::7] + ([sb[-1]] if sb and (len(sb) % 7) else []),
            "in_stock_connect": bool(sb),
            "verification_ok": all(v["ok"] for v in res["verif"]) if res["verif"] else None,
        })
    out = {"updated": dt_date.today().isoformat(), "stocks": stocks}
    path = os.path.join(BASE, "widget_data.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    print("widget_data.json written,", os.path.getsize(path), "bytes")
    return out


if __name__ == "__main__":
    only = sys.argv[1] if len(sys.argv) > 1 else None
    results = []
    for s in CFG["stocks"]:
        if only and s["code"] != only:
            continue
        results.append(process_stock(s, backfill=True))
    if results:
        build_widget_data(results)
