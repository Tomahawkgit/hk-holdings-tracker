# -*- coding: utf-8 -*-
"""港股取数层：CCASS 持股快照 + 东方财富南向持股。

统一重试/退避/超时模式（_retry），两个数据源各保留"构造请求 + 纯解析函数"。
纯解析函数 parse_ccass_html / parse_southbound_result 不依赖网络，可离线回归测试。

行为与原 ccass_fetch.py / southbound_fetch.py 保持一致：
- CCASS：retries=2、退避 3s、GET 超时 30 / POST 超时 60；
- 南向：无重试（retries=0），失败直接抛出。
"""
import re
import time

import requests
from bs4 import BeautifulSoup

from config import load_config

CFG = load_config()
CCASS_URL = CFG["ccass_url"]
SB_URL = CFG["eastmoney_url"]

CCASS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Origin": "https://www3.hkexnews.hk",
    "Referer": CCASS_URL,
}
SB_HEADERS = {
    "Referer": "https://data.eastmoney.com/",
    "User-Agent": "Mozilla/5.0",
}


def _retry(fn, retries=0, backoff=3.0):
    """按次重试 + 线性退避。retries=0 表示只跑一次、失败即抛出（保持南向原行为）。"""
    for attempt in range(retries + 1):
        try:
            return fn()
        except Exception:
            if attempt >= retries:
                raise
            time.sleep(backoff * (attempt + 1))


# ---------- CCASS ----------

def _ccass_form_values(soup, code, date):
    def f(name):
        el = soup.find("input", {"name": name})
        return el.get("value", "") if el else ""

    return {
        "__EVENTTARGET": "btnSearch", "__EVENTARGUMENT": "",
        "__VIEWSTATE": f("__VIEWSTATE"), "__VIEWSTATEGENERATOR": f("__VIEWSTATEGENERATOR"),
        "__EVENTVALIDATION": f("__EVENTVALIDATION"), "today": f("today"),
        "sortBy": "shareholding", "sortDirection": "desc",
        "originalShareholdingDate": "", "alertMsg": "",
        "txtShareholdingDate": date, "txtStockCode": code,
        "txtStockName": "", "txtParticipantID": "", "txtParticipantName": "", "txtSelPartID": "",
    }


def _fetch_ccass_html(code, date):
    def call():
        s = requests.Session()
        s.headers.update(CCASS_HEADERS)
        r = s.get(CCASS_URL, timeout=30)
        soup = BeautifulSoup(r.text, "html.parser")
        payload = _ccass_form_values(soup, code, date)
        r2 = s.post(CCASS_URL, data=payload, timeout=60)
        return r2.text

    return _retry(call, retries=2, backoff=3.0)


def parse_ccass_html(html, code, date):
    """纯函数：CCASS 返回 HTML -> dict。无网络依赖，可离线测试。

    返回 dict: {date, code, stock_name, issued, ccass_total_pct, intermediaries_pct,
                rows: [(participant_code, name, shares, pct), ...]}
    无记录时返回 None。
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    m_date = re.search(r"持股日期\s*[::]?\s*(\d{4}/\d{2}/\d{2})", text)
    m_total = re.search(r"總數\s*於中央結算系統的持股量\s*([\d,]+)\s*參與者數目\s*(\d+)\s*佔已發行股份/權證/單位百分比\s*([\d.]+)%", text)
    m_issued = re.search(r"已發行股份/權證/單位\s*\(最近更新數目\)\s*([\d,]+)", text)
    m_inter = re.search(r"市場中介者\s*於中央結算系統的持股量\s*([\d,]+)\s*參與者數目\s*(\d+)\s*佔已發行股份/權證/單位百分比\s*([\d.]+)%", text)

    table = soup.find("table", class_=lambda c: c and "table-mobile-list" in c)
    if not table or len(table.find_all("tr")) <= 1:
        return None

    rows = []
    for tr in table.find_all("tr")[1:]:
        tds = tr.find_all("td")
        if len(tds) < 5:
            continue
        code_m = re.search(r"([A-Z]\d{5})", tds[0].get_text())
        if not code_m:
            continue
        name = re.sub(r"^.*\):", "", tds[1].get_text(strip=True)).strip()
        shares = int(re.sub(r"[^\d]", "", tds[3].get_text()) or 0)
        pct = float(re.search(r"([\d.]+)%", tds[4].get_text()).group(1)) if re.search(r"([\d.]+)%", tds[4].get_text()) else 0.0
        rows.append((code_m.group(1), name, shares, pct))

    return {
        "date": (m_date.group(1).replace("/", "-") if m_date else date.replace("/", "-")),
        "code": code,
        "issued": int(m_issued.group(1).replace(",", "")) if m_issued else None,
        "ccass_total_pct": float(m_total.group(3)) if m_total else None,
        "intermediaries_pct": float(m_inter.group(3)) if m_inter else None,
        "rows": rows,
    }


def fetch_ccass(code, date):
    """code='01024', date='2026/09/30' -> dict | None(该日期无记录，如上市前)。"""
    html = _fetch_ccass_html(code, date)
    return parse_ccass_html(html, code, date)


# ---------- 南向（东方财富港股通） ----------

def _southbound_page(code, page):
    params = {
        "reportName": "RPT_MUTUAL_STOCK_HOLDRANKS",
        "columns": "HOLD_DATE,HOLD_SHARES,HOLD_SHARES_RATIO",
        "filter": f'(SECURITY_CODE="{code}")',
        "sortColumns": "HOLD_DATE", "sortTypes": "1",
        "pageSize": "500", "pageNumber": str(page),
        "source": "WEB", "client": "WEB",
    }
    return _retry(
        lambda: requests.get(SB_URL, params=params, headers=SB_HEADERS, timeout=30).json(),
        retries=0,
    )


def parse_southbound_result(data):
    """纯函数：东财南向接口 result.data -> [{date, shares, ratio}]。"""
    out = []
    for r in data:
        out.append({
            "date": r["HOLD_DATE"][:10],
            "shares": r.get("HOLD_SHARES"),
            "ratio": r.get("HOLD_SHARES_RATIO"),
        })
    return out


def fetch_southbound_daily(code):
    """日频全历史，升序返回 [{date, shares, ratio}]。非港股通标的返回空列表。"""
    out, page = [], 1
    while True:
        d = _southbound_page(code, page)
        result = d.get("result")
        if not result or not result.get("data"):
            break
        out.extend(parse_southbound_result(result["data"]))
        if page >= result.get("pages", 1):
            break
        page += 1
    return out


if __name__ == "__main__":
    import json

    d = fetch_ccass("01024", "2026/09/30")
    print(json.dumps({k: (v if k != "rows" else len(v)) for k, v in d.items()}, ensure_ascii=False))
    print(d["rows"][0])

    sb = fetch_southbound_daily("01024")
    print(len(sb), sb[0] if sb else None, sb[-1] if sb else None)
