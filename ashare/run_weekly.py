# -*- coding: utf-8 -*-
"""每周更新入口：刷新全部股票五层数据，重建 ashare_data.json，并同步到 site/。

周频实测有效项：两融、龙虎榜、增减持/解禁事件；季度结构项（十大股东/机构持仓/户数）
每次也全量拉取——接口返回即最新披露，幂等无副作用。
"""
import os
import shutil

import build_widget

BASE = os.path.dirname(os.path.abspath(__file__))


def main():
    build_widget.build_all()
    # 同步 A股产出到 site/，供静态站同源兜底（数据不再需要手工回传）
    shutil.copy(os.path.join(BASE, "ashare_data.json"), os.path.join(BASE, "..", "site", "ashare_data.json"))


if __name__ == "__main__":
    main()
