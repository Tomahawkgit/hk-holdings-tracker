# -*- coding: utf-8 -*-
"""A 股五层资金结构聚合：原始接口数据 → 看板 JSON（ashare_data.json）。

五层：industrial 产业资本 / foreign 外资 / institution 境内机构 / hot 游资大户 / retail 散户
每层产出：状态卡数值 + 环比 + 信号(signal: pos/neg/watch/neu) + 口径说明。
分类优先级：config.layer_map 手工字典 > 关键词规则 > unknown（记入 unmapped_holders.log）。
"""
import json
import os
import re
from datetime import date as dt_date

import em_fetch

BASE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(BASE, "config.json"), encoding="utf-8"))
REVIEW_LOG = os.path.join(BASE, "unmapped_holders.log")

LAYER_LABEL = {"industrial": "产业资本", "foreign": "外资", "institution": "境内机构",
               "hot": "游资/大户", "retail": "散户", "unknown": "未归类"}

# ---- 关键词规则（兜底，优先级低于手工字典） ----
FOREIGN_KEYS = ["香港中央结算", "阿布达比", "科威特", "新加坡政府", "淡马锡", "挪威中央银行",
                "摩根士丹利国际", "摩根大通", "高盛国际", "美林国际", "UBS", "巴克莱", "汇丰",
                "魁北克储蓄", "安大略", "比尔及梅林达", "盖茨基金", "澳门金融管理局", "香港金融管理局"]
INSTITUTION_KEYS = ["基金", "ETF", "保险", "社保", "资管", "信托", "年金", "养老金", "理财",
                    "证券", "资产管理计划", "企业年金", "券商"]
INDUSTRIAL_KEYS = ["集团", "控股", "投资有限公司", "回购专用", "员工持股", "国有资产", "国资",
                   "财政局", "管委会", "开发区", "产业投资", "创投"]


def classify_holder(code, name):
    """十大股东行 → 五层之一。unknown 记入复核日志。"""
    manual = (CFG.get("layer_map") or {}).get(code) or {}
    if name in manual:
        return manual[name], False
    for k in FOREIGN_KEYS:
        if k in name:
            return "foreign", False
    for k in INSTITUTION_KEYS:
        if k in name:
            return "institution", False
    for k in INDUSTRIAL_KEYS:
        if k in name:
            return "industrial", False
    # 纯个人名（2-4 个汉字，无机构后缀特征）→ 散户/牛散
    if re.fullmatch(r"[一-龥]{2,4}", name or ""):
        return "retail", False
    with open(REVIEW_LOG, "a", encoding="utf-8") as f:
        f.write(f"{code}\t{name}\t请复核归类\n")
    return "unknown", True


def _pct_change_str(v):
    """HOLD_NUM_CHANGE 字段规整：不变/新进/数值。"""
    if v is None or v == "":
        return None
    return str(v)


def build_structure(stock):
    """季度结构层：十大流通股东（主）+ 十大股东（辅）+ 机构分类汇总。返回 (structure, compare)。"""
    code, secucode = stock["code"], stock["secucode"]
    free = em_fetch.fetch_top_holders(secucode, free=True, periods=2)
    total = em_fetch.fetch_top_holders(secucode, free=False, periods=2)
    orgs = em_fetch.fetch_org_holdings(secucode, periods=2)
    if not free and not total:
        return None, None

    def rows_to_items(rows, total_pct_map, is_free):
        items = []
        for r in rows:
            name = r.get("HOLDER_NAME") or ""
            layer, need_review = classify_holder(code, name)
            pct_float = r.get("FREE_HOLDNUM_RATIO") if is_free else None
            pct_total = r.get("HOLD_NUM_RATIO") if not is_free else r.get("HOLD_RATIO")
            if not is_free:
                pct_float = (total_pct_map or {}).get(name)
            items.append({
                "rank": r.get("HOLDER_RANK"), "name": name, "layer": layer,
                "shares": r.get("HOLD_NUM"),
                "pct_total": pct_total, "pct_float": pct_float,
                "change": _pct_change_str(r.get("HOLD_NUM_CHANGE") or r.get("HOLDER_STATE")),
                "holder_type": r.get("HOLDER_TYPE"),
            })
        return items

    # 总股本口径名册用于补充 pct_total；流通口径 pct_total 字段为 HOLD_RATIO
    dates = sorted(set(list(free.keys()) + list(total.keys())), reverse=True)
    cur, prev = dates[0], (dates[1] if len(dates) > 1 else None)

    cur_items = rows_to_items(free.get(cur) or total.get(cur) or [], None, bool(free.get(cur)))
    prev_items = rows_to_items(free.get(prev) or total.get(prev) or [], None, bool(free.get(prev))) if prev else []

    def layer_sum(items):
        s = {k: 0.0 for k in LAYER_LABEL}
        for it in items:
            pct = it.get("pct_float") if it.get("pct_float") is not None else it.get("pct_total")
            if pct is None:
                continue
            k = it["layer"] if it["layer"] in s else "unknown"
            s[k] = round(s[k] + float(pct), 2)
        return s

    cur_sum, prev_sum = layer_sum(cur_items), layer_sum(prev_items)
    layer_delta = {k: round(cur_sum.get(k, 0) - prev_sum.get(k, 0), 2) for k in LAYER_LABEL}

    # 北向：流通股东里的香港中央结算
    nb_cur = next((i for i in cur_items if "香港中央结算" in i["name"]), None)
    nb_prev = next((i for i in prev_items if "香港中央结算" in i["name"]), None)

    structure = {
        "as_of": cur, "prev_as_of": prev,
        "top10": cur_items,
        "layer_sum": cur_sum, "layer_delta": layer_delta,
        "northbound": {
            "pct_float": (nb_cur or {}).get("pct_float"),
            "pct_total": (nb_cur or {}).get("pct_total"),
            "delta": (round((nb_cur or {}).get("pct_float", 0) - (nb_prev or {}).get("pct_float", 0), 2)
                      if nb_cur and nb_prev and nb_cur.get("pct_float") is not None and nb_prev.get("pct_float") is not None else None),
        },
        "org_holdings": orgs.get(cur) or orgs.get(sorted(orgs.keys(), reverse=True)[0]) if orgs else [],
        "org_as_of": sorted(orgs.keys(), reverse=True)[0] if orgs else None,
    }
    compare = {"cur": cur, "prev": prev, "cur_items": cur_items, "prev_items": prev_items}
    return structure, compare


def build_events(stock):
    """事件层：增减持 + 解禁（近一年 + 未来）合并时间线。回购为缺口（外部补）。"""
    code = stock["code"]
    today = dt_date.today().isoformat()
    year_ago = dt_date.fromordinal(dt_date.today().toordinal() - 365).isoformat()
    events = []
    for c in em_fetch.fetch_holder_changes(code):
        if c["date"] < year_ago:
            continue
        direction = c.get("direction") or ""
        nature = "pos" if direction == "增持" else "neg"
        # 注意：接口 CHANGE_RATE 口径不可靠（增持也可能为负），只用股数与均价
        note = f"{direction} {c.get('change_num_wan')}万股"
        if c.get("avg_price"):
            note += f"，均价 {c.get('avg_price')}元"
        events.append({
            "date": c["date"], "type": direction or "增减持",
            "actor": c.get("holder"),
            "note": note,
            "nature": nature,
        })
    lifts_future, lifts_past = [], []
    for l in em_fetch.fetch_lifts(code):
        item = {"date": l["date"], "shares": l.get("shares"), "mkt_cap": l.get("mkt_cap"),
                "type": l.get("type"), "total_ratio": l.get("total_ratio")}
        if l["date"] >= today:
            lifts_future.append(item)
            events.append({"date": l["date"], "type": "解禁(未来)", "actor": None,
                           "note": f"{l.get('type')}，占总股本 {l.get('total_ratio')}%", "nature": "watch"})
        elif l["date"] >= year_ago:
            lifts_past.append(item)
            events.append({"date": l["date"], "type": "解禁", "actor": None,
                           "note": f"{l.get('type')}，占总股本 {l.get('total_ratio')}%", "nature": "neu"})
    events.sort(key=lambda e: e["date"], reverse=True)
    return events, sorted(lifts_future, key=lambda x: x["date"])


def build_signals(stock, structure, holder_num, margin, lhb, events):
    """按手册解读规则生成五层信号：pos 积极 / neg 压力 / watch 警示 / neu 中性。"""
    sig = {}
    # 产业资本
    ind_ev = [e for e in events if e["type"] in ("增持", "减持")]
    buy = sum(1 for e in ind_ev if e["type"] == "增持")
    sell = sum(1 for e in ind_ev if e["type"] == "减持")
    future_lift = [e for e in events if e["type"] == "解禁(未来)"]
    if buy > sell:
        sig["industrial"] = ("pos", "产业资本净增持/回购对冲")
    elif sell > buy:
        sig["industrial"] = ("neg", "存在减持记录")
    elif future_lift:
        sig["industrial"] = ("watch", "未来有解禁供给")
    else:
        sig["industrial"] = ("neu", "底仓稳定，无显著增减持")
    # 外资
    nb = (structure or {}).get("northbound") or {}
    d = nb.get("delta")
    if d is None:
        sig["foreign"] = ("neu", "北向季度披露，暂无环比")
    elif d <= -0.5:
        sig["foreign"] = ("neg", f"北向环比 {d}pct，边际撤退")
    elif d >= 0.5:
        sig["foreign"] = ("pos", f"北向环比 +{d}pct，边际增持")
    else:
        sig["foreign"] = ("neu", f"北向环比 {d}pct，基本持平")
    # 境内机构（用十大股东内机构占比变化近似；主动/被动拆分为外部补位项）
    di = (structure or {}).get("layer_delta", {}).get("institution")
    if di is None:
        sig["institution"] = ("neu", "机构持仓季度披露")
    elif di >= 0.5:
        sig["institution"] = ("pos", f"十大股东内机构占比 +{di}pct")
    elif di <= -0.5:
        sig["institution"] = ("neg", f"十大股东内机构占比 {di}pct")
    else:
        sig["institution"] = ("neu", "机构占比变化不大")
    # 游资/大户
    n_lhb = len(lhb)
    if n_lhb == 0:
        sig["hot"] = ("neu", "近一年未上龙虎榜，游资非主导")
    else:
        sig["hot"] = ("watch", f"近一年上榜 {n_lhb} 次，注意席位性质")
    # 散户：户数 + 两融
    hn_latest = holder_num[0] if holder_num else None
    parts = []
    neg = False
    if hn_latest and hn_latest.get("change_pct") is not None:
        cp = hn_latest["change_pct"]
        parts.append(f"户数环比 {cp:+.1f}%")
        if cp >= 20:
            neg = True
    if len(margin) >= 20:
        m0, m20 = margin[0].get("rzye"), margin[19].get("rzye")
        if m0 and m20:
            chg = (m0 - m20) / m20 * 100
            parts.append(f"融资余额 20 日 {chg:+.1f}%")
            if chg >= 30:
                neg = True
    sig["retail"] = ("neg" if neg else "neu",
                     ("；".join(parts) if parts else "户数/两融暂无更新") + ("，散户拥挤" if neg else ""))
    return sig


def process_stock(stock):
    name = stock["name"]
    print(f"=== {name} ({stock['code']}) ===", flush=True)
    structure, _ = build_structure(stock)
    holder_num = em_fetch.fetch_holder_num(stock["code"], CFG.get("holder_num_points", 16))
    margin = em_fetch.fetch_margin(stock["code"], CFG.get("margin_days", 250))
    lhb = em_fetch.fetch_lhb(stock["code"], CFG.get("lhb_days", 365))
    lhb_seats = {}
    for rec in lhb[:5]:  # 席位明细只取最近 5 次上榜
        lhb_seats[rec["date"]] = em_fetch.fetch_lhb_seats(stock["code"], rec["date"])
    main_force = em_fetch.fetch_main_force(stock["code"], stock["secucode"])
    events, lifts_future = build_events(stock)
    signals = build_signals(stock, structure, holder_num, margin, lhb, events)
    return {
        "code": stock["code"], "secucode": stock["secucode"], "name": name,
        "structure": structure, "holder_num": holder_num, "margin": margin,
        "lhb": lhb, "lhb_seats": lhb_seats, "main_force": main_force,
        "events": events, "lifts_future": lifts_future, "signals": signals,
    }


def build_all():
    em_fetch.set_interval(CFG.get("request_interval_sec", 1.5))
    stocks = [process_stock(s) for s in CFG["stocks"]]
    out = {"updated": dt_date.today().isoformat(), "stocks": stocks}
    path = os.path.join(BASE, "ashare_data.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    print(f"ashare_data.json written, {os.path.getsize(path)} bytes")
    return out


if __name__ == "__main__":
    build_all()
