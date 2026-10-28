# -*- coding: utf-8 -*-
"""东方财富港股通（南向资金）持股数据。免费公开接口，日频全历史。

fetch_southbound_daily('01024') -> [{date, shares, ratio}, ...] 升序
非港股通标的返回空列表。
"""
import requests

URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
HEADERS = {"Referer": "https://data.eastmoney.com/", "User-Agent": "Mozilla/5.0"}


def fetch_southbound_daily(code):
    out, page = [], 1
    while True:
        params = {
            "reportName": "RPT_MUTUAL_STOCK_HOLDRANKS",
            "columns": "HOLD_DATE,HOLD_SHARES,HOLD_SHARES_RATIO",
            "filter": f'(SECURITY_CODE="{code}")',
            "sortColumns": "HOLD_DATE", "sortTypes": "1",
            "pageSize": "500", "pageNumber": str(page),
            "source": "WEB", "client": "WEB",
        }
        d = requests.get(URL, params=params, headers=HEADERS, timeout=30).json()
        result = d.get("result")
        if not result or not result.get("data"):
            break
        for r in result["data"]:
            out.append({
                "date": r["HOLD_DATE"][:10],
                "shares": r.get("HOLD_SHARES"),
                "ratio": r.get("HOLD_SHARES_RATIO"),
            })
        if page >= result.get("pages", 1):
            break
        page += 1
    return out


if __name__ == "__main__":
    rows = fetch_southbound_daily("01024")
    print(len(rows), rows[0] if rows else None, rows[-1] if rows else None)
