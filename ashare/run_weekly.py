# -*- coding: utf-8 -*-
"""每周更新入口：刷新全部股票五层数据，重建 ashare_data.json。

周频实测有效项：两融、龙虎榜、增减持/解禁事件；季度结构项（十大股东/机构持仓/户数）
每次也全量拉取——接口返回即最新披露，幂等无副作用。
"""
import build_widget

if __name__ == "__main__":
    build_widget.build_all()
