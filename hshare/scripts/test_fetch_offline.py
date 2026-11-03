# -*- coding: utf-8 -*-
"""离线回归测试：用本地保存的 CCASS HTML / 南向 JSON fixture 锁住 fetch 的解析函数。

不访问网络。fixture 为真实抓取快照（01024 / 2026-10-30）。
用法：python scripts/test_fetch_offline.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetch import parse_ccass_html, parse_southbound_result

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def test_ccass_parse():
    with open(os.path.join(FIXTURES, "ccass_01024.html"), encoding="utf-8") as f:
        html = f.read()
    d = parse_ccass_html(html, "01024", "2026/10/30")
    assert d is not None, "应能解析出记录"
    assert d["date"] == "2026-10-30", d["date"]
    assert d["code"] == "01024"
    assert d["issued"] == 4304151598
    assert d["ccass_total_pct"] == 84.09
    assert d["intermediaries_pct"] == 84.07
    assert len(d["rows"]) == 366, len(d["rows"])
    assert d["rows"][0] == ("C00019", "香港上海匯豐銀行有限公司", 967350534, 22.47)
    assert d["rows"][1] == ("A00004", "中國証券登記結算有限責任公司", 564231092, 13.1)


def test_southbound_parse():
    with open(os.path.join(FIXTURES, "southbound_01024.json"), encoding="utf-8") as f:
        payload = json.load(f)
    data = payload["result"]["data"]
    rows = parse_southbound_result(data)
    assert len(rows) == len(data)
    assert rows[0] == {"date": "2024-11-04", "shares": 544432289, "ratio": 12.61}
    assert rows[-1] == {"date": "2025-11-20", "shares": 678559535, "ratio": 15.68}
    for r in rows:
        assert set(r) == {"date", "shares", "ratio"}


if __name__ == "__main__":
    test_ccass_parse()
    test_southbound_parse()
    print("OK: 离线回归测试通过")
