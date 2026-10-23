# -*- coding: utf-8 -*-
"""东方财富公开数据接口（免密、低频用途）。

覆盖 A 股五层资金结构所需数据项：
  十大股东 / 十大流通股东（季度，含北向香港中央结算、QFII）
  F10 机构持仓分类汇总（基金/保险/社保/QFII 家数与占比，多期）
  股东户数多期序列 / 融资融券日频 / 龙虎榜记录与席位 / 限售解禁 / 股东增减持
  主力资金日频（push2his，部分网络环境不可达，失败自动降级为空）

所有函数返回 None/[] 表示该数据项本次不可用，调用方负责降级，不得中断整体流程。
"""
import time
import requests

DC = "https://datacenter-web.eastmoney.com/api/data/v1/get"
F10 = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
PUSH2HIS = "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
    "Referer": "https://data.eastmoney.com/",
}

_interval = 1.5


def set_interval(sec):
    global _interval
    _interval = float(sec)


def _get(url, params, retries=2):
    last = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=30)
            d = r.json()
            time.sleep(_interval)
            return (d.get("result") or {}).get("data") or []
        except Exception as e:
            last = e
            time.sleep(2 * (attempt + 1))
    print(f"  [warn] 接口失败 {params.get('reportName', url)}: {last!r}")
    return []


def _periods(rows, date_key, n=2):
    """取最近 n 个披露期（按日期字符串倒序去重）。"""
    seen = []
    for r in rows:
        d = (r.get(date_key) or "")[:10]
        if d and d not in seen:
            seen.append(d)
        if len(seen) >= n:
            break
    return seen


def fetch_top_holders(secucode, free=False, periods=2):
    """十大股东（free=False）/ 十大流通股东（free=True）。返回 {期日: [rows]} 按 HOLDER_RANK 排序。"""
    report = "RPT_F10_EH_FREEHOLDERS" if free else "RPT_F10_EH_HOLDERS"
    rows = _get(F10, {
        "reportName": report, "columns": "ALL",
        "filter": f'(SECUCODE="{secucode}")',
        "pageSize": str(10 * periods + 10), "pageNumber": "1",
        "sortTypes": "-1", "sortColumns": "END_DATE",
    })
    out = {}
    for r in rows:
        d = (r.get("END_DATE") or "")[:10]
        out.setdefault(d, []).append(r)
    keep = sorted(out.keys(), reverse=True)[:periods]
    return {k: sorted(out[k], key=lambda x: x.get("HOLDER_RANK") or 99) for k in keep}


def fetch_org_holdings(secucode, periods=2):
    """F10 机构持仓分类汇总：{期日: [{org_type, name_type, num, shares_ratio, free_shares, free_change}]}"""
    rows = _get(F10, {
        "reportName": "RPT_F10_MAIN_ORGHOLDDETAILS", "columns": "ALL",
        "filter": f'(SECUCODE="{secucode}")',
        "pageSize": "60", "pageNumber": "1",
        "sortTypes": "-1", "sortColumns": "REPORT_DATE",
    })
    out = {}
    for r in rows:
        d = (r.get("REPORT_DATE") or "")[:10]
        out.setdefault(d, []).append({
            "org_type": r.get("ORG_TYPE"),
            "name": r.get("ORG_NAME_TYPE"),
            "num": r.get("TOTAL_ORG_NUM"),
            "shares_ratio": r.get("TOTAL_SHARES_RATIO"),
            "free_shares": r.get("TOTAL_FREE_SHARES"),
            "free_change": r.get("FREE_SHARES_CHANGE"),
        })
    keep = sorted(out.keys(), reverse=True)[:periods]
    return {k: out[k] for k in keep}


def fetch_holder_num(code, points=16):
    """股东户数多期序列（新→旧）。"""
    rows = _get(DC, {
        "reportName": "RPT_HOLDERNUM_DET", "columns": "ALL",
        "filter": f'(SECURITY_CODE="{code}")',
        "pageSize": str(points), "pageNumber": "1",
        "sortTypes": "-1", "sortColumns": "END_DATE",
    })
    out = []
    for r in rows:
        out.append({
            "date": (r.get("END_DATE") or "")[:10],
            "num": r.get("HOLDER_NUM"),
            "change_pct": r.get("HOLDER_NUM_RATIO"),
            "avg_mkt_cap": r.get("AVG_MARKET_CAP"),
            "total_a_shares": r.get("TOTAL_A_SHARES"),
        })
    return [r for r in out if r["date"]]


def fetch_margin(code, days=250):
    """融资融券日频（新→旧，取近 days 条）。RZYE=融资余额(元) RQYL=融券余量 RZRQYE=两融余额。"""
    rows = _get(DC, {
        "reportName": "RPTA_WEB_RZRQ_GGMX", "columns": "ALL",
        "filter": f'(SCODE="{code}")',
        "pageSize": str(days), "pageNumber": "1",
        "sortTypes": "-1", "sortColumns": "DATE",
    })
    out = []
    for r in rows:
        out.append({
            "date": (r.get("DATE") or "")[:10],
            "rzye": r.get("RZYE"),
            "rqyl": r.get("RQYL"),
            "rzrqye": r.get("RZRQYE"),
        })
    return [r for r in out if r["date"]]


def fetch_lhb(code, days=365):
    """龙虎榜：近 days 天上榜记录（新→旧），每条含买卖金额与原因。"""
    from datetime import date, timedelta
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    rows = _get(DC, {
        "reportName": "RPT_DAILYBILLBOARD_DETAILSNEW", "columns": "ALL",
        "filter": f'(SECURITY_CODE="{code}")',
        "pageSize": "60", "pageNumber": "1",
        "sortTypes": "-1", "sortColumns": "TRADE_DATE",
    })
    out = []
    for r in rows:
        d = (r.get("TRADE_DATE") or "")[:10]
        if not d:
            continue
        if d < cutoff:
            break  # 已按日期倒序，超出窗口即止
        out.append({
            "date": d,
            "reason": r.get("EXPLANATION"),
            "note": r.get("EXPLAIN"),
            "close": r.get("CLOSE_PRICE"),
            "change_rate": r.get("CHANGE_RATE"),
            "buy_amt": r.get("BILLBOARD_BUY_AMT"),
            "sell_amt": r.get("BILLBOARD_SELL_AMT"),
            "deal_ratio": r.get("DEAL_AMOUNT_RATIO"),
        })
    return out[:40]


def fetch_lhb_seats(code, trade_date):
    """某日龙虎榜席位明细。买入/卖出两个榜单按营业部去重合并，side 标记来源。"""
    merged = {}
    for side, report in (("buy", "RPT_BILLBOARD_DAILYDETAILSBUY"), ("sell", "RPT_BILLBOARD_DAILYDETAILSSELL")):
        rows = _get(DC, {
            "reportName": report, "columns": "ALL",
            "filter": f'(SECURITY_CODE="{code}")(TRADE_DATE=\'{trade_date}\')',
            "pageSize": "10", "pageNumber": "1",
        })
        for r in rows:
            dept = r.get("OPERATEDEPT_NAME")
            if not dept:
                continue
            if dept in merged:
                merged[dept]["side"] = "both"
                continue
            merged[dept] = {
                "side": side,
                "dept": dept,
                "buy": r.get("BUY"),
                "sell": r.get("SELL"),
                "net": r.get("NET"),
            }
    return list(merged.values())


def fetch_lifts(code):
    """限售解禁：全部记录（调用方筛未来/近一年）。"""
    rows = _get(DC, {
        "reportName": "RPT_LIFT_STAGE", "columns": "ALL",
        "filter": f'(SECURITY_CODE="{code}")',
        "pageSize": "50", "pageNumber": "1",
        "sortTypes": "-1", "sortColumns": "FREE_DATE",
    })
    out = []
    for r in rows:
        d = (r.get("FREE_DATE") or "")[:10]
        if not d:
            continue
        out.append({
            "date": d,
            "shares": r.get("CURRENT_FREE_SHARES"),
            "mkt_cap": r.get("LIFT_MARKET_CAP"),
            "type": r.get("FREE_SHARES_TYPE"),
            "total_ratio": r.get("TOTAL_RATIO"),
        })
    return out


def fetch_holder_changes(code, limit=30):
    """股东增减持（新→旧）。DIRECTION=增持/减持。"""
    rows = _get(DC, {
        "reportName": "RPT_SHARE_HOLDER_INCREASE", "columns": "ALL",
        "filter": f'(SECURITY_CODE="{code}")',
        "pageSize": str(limit), "pageNumber": "1",
        "sortTypes": "-1,-1", "sortColumns": "NOTICE_DATE,END_DATE",
    })
    out = []
    for r in rows:
        d = (r.get("NOTICE_DATE") or r.get("END_DATE") or "")[:10]
        if not d:
            continue
        out.append({
            "date": d,
            "holder": r.get("HOLDER_NAME"),
            "direction": r.get("DIRECTION"),
            "change_num_wan": r.get("CHANGE_NUM"),
            "change_rate": r.get("CHANGE_RATE"),
            "free_ratio": r.get("FREE_SHARES_RATIO"),
            "avg_price": r.get("TRADE_AVERAGE_PRICE"),
        })
    return out


def fetch_main_force(code, secucode, days=120):
    """主力资金日频净流入（push2his，部分网络不可达；失败返回 []）。
    secid: 深市 0.CODE / 沪市 1.CODE。"""
    market = "1" if secucode.endswith(".SH") else "0"
    try:
        r = requests.get(PUSH2HIS, params={
            "secid": f"{market}.{code}", "klt": "101", "lmt": str(days),
            "fields1": "f1,f2,f3,f7",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
        }, headers=HEADERS, timeout=20)
        d = r.json()
        klines = ((d.get("data") or {}).get("klines")) or []
        out = []
        for line in klines:
            p = line.split(",")
            if len(p) < 7:
                continue
            out.append({
                "date": p[0], "main_net": float(p[1]), "small_net": float(p[2]),
                "mid_net": float(p[3]), "large_net": float(p[4]), "super_net": float(p[5]),
            })
        time.sleep(_interval)
        return out
    except Exception as e:
        print(f"  [warn] 主力资金接口不可用，降级为空: {e!r}")
        return []


if __name__ == "__main__":
    import json
    print(json.dumps(fetch_top_holders("300274.SZ", free=True, periods=1), ensure_ascii=False, default=str)[:800])
