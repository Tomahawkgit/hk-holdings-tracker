# -*- coding: utf-8 -*-
"""hshare 配置与路径单点：统一 BASE 与 config.json 加载，避免各模块重复实现。"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))


def load_config():
    with open(os.path.join(BASE, "config.json"), encoding="utf-8") as f:
        return json.load(f)
