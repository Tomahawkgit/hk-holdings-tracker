# -*- coding: utf-8 -*-
"""港交所 CCASS 持股纪录直取模块（低频查询用途）。

返回 dict: {date, code, stock_name, issued, ccass_total_pct, intermediaries_pct,
            rows: [(participant_code, name, shares, pct), ...]}
日期传月末自然日即可，官网对非交易日自动回退到最后交易日，返回的 date 为实际持股日期。
"""
import re, time, json
import requests
from bs4 import BeautifulSoup

BASE = "https://www3.hkexnews.hk/sdw/search/searchsdw_c.aspx"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Origin": "https://www3.hkexnews.hk",
    "Referer": BASE,
}


def fetch_ccass(code, date, retries=2):
    """code='01024', date='2026/09/30' -> dict | None(该日期无记录，如上市前)"""
    for attempt in range(retries + 1):
        try:
            return _fetch_once(code, date)
        except Exception:
            if attempt >= retries:
                raise
            time.sleep(3 * (attempt + 1))


def _fetch_once(code, date):
    s = requests.Session()
    s.headers.update(HEADERS)
    r = s.get(BASE, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    def f(name):
        el = soup.find("input", {"name": name})
        return el.get("value", "") if el else ""

    payload = {
        "__EVENTTARGET": "btnSearch", "__EVENTARGUMENT": "",
        "__VIEWSTATE": f("__VIEWSTATE"), "__VIEWSTATEGENERATOR": f("__VIEWSTATEGENERATOR"),
        "__EVENTVALIDATION": f("__EVENTVALIDATION"), "today": f("today"),
        "sortBy": "shareholding", "sortDirection": "desc",
        "originalShareholdingDate": "", "alertMsg": "",
        "txtShareholdingDate": date, "txtStockCode": code,
        "txtStockName": "", "txtParticipantID": "", "txtParticipantName": "", "txtSelPartID": "",
    }
    r2 = s.post(BASE, data=payload, timeout=60)
    soup2 = BeautifulSoup(r2.text, "html.parser")
    text = soup2.get_text(" ", strip=True)

    m_date = re.search(r"持股日期\s*[::]?\s*(\d{4}/\d{2}/\d{2})", text)
    m_total = re.search(r"總數\s*於中央結算系統的持股量\s*([\d,]+)\s*參與者數目\s*(\d+)\s*佔已發行股份/權證/單位百分比\s*([\d.]+)%", text)
    m_issued = re.search(r"已發行股份/權證/單位\s*\(最近更新數目\)\s*([\d,]+)", text)
    m_inter = re.search(r"市場中介者\s*於中央結算系統的持股量\s*([\d,]+)\s*參與者數目\s*(\d+)\s*佔已發行股份/權證/單位百分比\s*([\d.]+)%", text)

    table = soup2.find("table", class_=lambda c: c and "table-mobile-list" in c)
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


if __name__ == "__main__":
    d = fetch_ccass("01024", "2026/09/30")
    print(json.dumps({k: (v if k != "rows" else len(v)) for k, v in d.items()}, ensure_ascii=False))
    print(d["rows"][0])
