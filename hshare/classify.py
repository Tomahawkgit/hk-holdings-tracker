# -*- coding: utf-8 -*-
"""CCASS 参与者归类：持久字典 + 关键词规则。

participant_map.csv 为持久字典：code,name,category,source(manual/auto)
- 已知编号直接查字典；
- 未知编号按关键词规则自动归类并追加进字典（source=auto），同时记入 unmapped_review.log 供人工复核。
类别：southbound=南向资金(港股通) foreign=外资中介 chinese=中资中介 local=本地及其他中介
"""
import csv, os

BASE = os.path.dirname(os.path.abspath(__file__))
MAP_FILE = os.path.join(BASE, "participant_map.csv")
REVIEW_LOG = os.path.join(BASE, "unmapped_review.log")

FOREIGN_KEYS = ["匯豐", "汇丰", "高盛", "花旗", "MORGAN STANLEY", "渣打", "UBS", "法國巴黎", "法国巴黎", "DBS", "星展",
                "MLFE", "德意志", "盈透", "J.P. MORGAN", "JPMORGAN", "MERRILL", "BARCLAYS", "CREDIT SUISSE",
                "NOMURA", "野村", "MACQUARIE", "HSBC", "CITI", "GOLDMAN", "BNP", "DEUTSCHE", "INTERACTIVE",
                "摩根大通", "摩根士丹利", "瑞銀", "瑞银", "瑞穗", "MIZUHO", "大和", "DAIWA", "荷銀", "ANZ",
                "WELLS FARGO", "STATE STREET", "BANK OF NEW YORK", "NORTHERN TRUST", "CITIBANK",
                "SOCIETE GENERALE", "法興", "法兴", "OCBC", "華僑銀行", "华侨银行", "UOB", "大華",
                "MAYBANK", "馬銀", "马银", "CIMB", "SUSQUEHANNA", "CITADEL", "JANE STREET", "VIRTU",
                "ABN", "ING ", "KBC", "KEB", "SHINHAN", "IBK", "KB ", "SAMSUNG SEC", "MIRAE", "未来资产",
                "未來資產", "NH INVESTMENT", "KOREA INVESTMENT", "MORGAN", "CREDIT AGRICOLE", "NATIXIS",
                "COMMERZBANK", "RAIFFEISEN", "PICTET", "JULIUS", "LGT", "UNION BANCAIRE", "EFG", "BOCOM INT'L".upper()]
CHINESE_KEYS = ["中國銀行", "中国银行", "中銀", "中银", "工銀", "工银", "工商銀行", "建設銀行", "建设银行", "建銀", "建银",
                "交通銀行", "交通银行", "交銀", "交银", "招商", "中信", "國泰君安", "国泰君安", "廣發", "广发",
                "光大", "海通", "華泰", "华泰", "中金", "中國國際金融", "平安", "中泰", "方正", "申萬", "申万",
                "銀河", "银河", "集友", "南洋商業", "南洋商业", "永隆", "民生", "興業", "兴业", "浦發", "浦发",
                "浙商", "渤海", "華夏", "华夏", "東方證券", "东方证券", "國信", "国信", "安信", "長江證券", "长江证券",
                "越秀", "農銀", "农银", "建投", "山證", "山证", "西證", "西证", "天風", "天风", "東北證券", "东北证券",
                "東莞", "东莞", "國元", "国元", "國聯", "国联", "財通", "财通", "首創", "首创", "招銀", "浦銀", "浦银",
                "光銀", "光银", "華融", "华融", "信達", "信达", "中州", "復星恒利", "复星恒利", "六福", "橫華", "横华",
                "永安", "南華", "南华", "創元", "创元", "東證", "东证", "弘業", "弘业", "中輝", "中辉", "瑞達", "瑞达",
                "徽商", "一盈", "利財", "利财", "鼎佩", "華創", "华创", "德邦", "萬聯", "万联", "五礦", "五矿",
                "中航", "開源", "开源", "南京證券", "南京证券", "國海", "国海", "西南證券", "西南证券", "太平洋證券",
                "紅塔", "红塔", "湘財", "湘财", "財信", "财信", "華福", "华福", "華安", "华安", "國金", "国金",
                "西部證券", "西部证券", "山西證券", "山西证券", "第一創業", "第一创业", "東吳", "东吴", "中原",
                "興證", "兴证", "方德", "凱基", "凯基", "元大", "永豐金", "永丰金", "富邦", "群益", "元富",
                "兆豐", "兆丰", "統一", "统一", "台新", "玉山", "中國信託", "中国信托", "華南永昌", "华南永昌",
                "第一金", "國票", "国票", "日盛", "大眾", "大丰", "大豐", "遠東", "远东", "台中銀", "台中银",
                "京城", "陸家嘴", "陆家嘴", "禹洲", "佳兆業", "佳兆业", "潤淼", "润淼", "長虹", "长虹",
                "中國結算", "中国结算", "中証", "中證登", "中投", "中银国际", "中銀國際",
                "農業銀行", "农业银行", "浦東", "浦东", "信銀", "信银", "上銀", "上银", "中國中期",
                "中國北方", "中恆", "中恒", "中昊", "中富", "中達", "中达", "中陽", "中阳", "中順", "中顺",
                "中策", "中融", "中財", "中财", "中發", "中发", "中潤", "中润", "中天證券", "京信",
                "光源資本", "光源资本", "凱銀", "凯银", "信誠", "信诚", "亞丁", "亚丁"]
SOUTHBOUND_CODES = {"A00003", "A00004"}
MAINLAND_CODES = {"A00005"}  # 中国结算(香港)：H股全流通/境内股东H股托管账户


def _load_map():
    m = {}
    if os.path.exists(MAP_FILE):
        with open(MAP_FILE, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                m[row["code"]] = (row["name"], row["category"])
    return m


def _append_map(code, name, category, source="auto"):
    exists = os.path.exists(MAP_FILE)
    with open(MAP_FILE, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["code", "name", "category", "source"])
        w.writerow([code, name, category, source])


def _guess(name):
    u = name.upper()
    if any(k in name or k in u for k in FOREIGN_KEYS):
        return "foreign"
    if any(k in name or k in u for k in CHINESE_KEYS):
        return "chinese"
    return "local"


def classify(code, name):
    """返回类别。已知编号查字典；未知编号规则归类并写入字典+复核日志。"""
    if code in SOUTHBOUND_CODES:
        return "southbound"
    if code in MAINLAND_CODES:
        return "mainland"
    m = _load_map()
    if code in m:
        return m[code][1]
    cat = _guess(name)
    _append_map(code, name, cat)
    if cat == "local":
        with open(REVIEW_LOG, "a", encoding="utf-8") as f:
            f.write(f"{code}\t{name}\tauto->local，请复核\n")
    return cat


CAT_LABEL = {"southbound": "南向资金", "foreign": "外资中介", "chinese": "中资中介", "local": "本地及其他中介", "mainland": "境内股东H股"}
