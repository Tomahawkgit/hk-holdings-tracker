# -*- coding: utf-8 -*-
"""定时任务入口：每周更新 6 只港股持仓结构，把 widget_data.json 作为 artifact 输出（经 Binding 推送到看板小组件）。

自动化运行器可能将本入口复制到其他目录执行，因此这里用绝对路径显式加载
tracker 目录下的 run_weekly 等模块，不依赖 sys.path。

手动验证：python weekly_job.py
"""
import importlib.util
import json
import os
import sys

# tracker 目录的固定位置（跨设备迁移时只需改这一行，或保持目录结构后自动探测）
TRACKER_DIR = "/Users/mt/Desktop/hk-holdings-tracker"


def _resolve_base():
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        if os.path.exists(os.path.join(here, "run_weekly.py")):
            return here
    except Exception:
        pass
    return TRACKER_DIR


def _load(name, base):
    path = os.path.join(base, name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def run(ctx=None):
    base = _resolve_base()
    if base not in sys.path:
        sys.path.insert(0, base)
    # run_weekly 内部 import build_dataset / southbound_fetch，先预加载确保按绝对路径解析
    for mod in ("southbound_fetch", "ccass_fetch", "classify", "build_dataset", "run_weekly"):
        if mod not in sys.modules:
            _load(mod, base)
    sys.modules["run_weekly"].run()
    with open(os.path.join(base, "widget_data.json"), encoding="utf-8") as f:
        data = json.load(f)
    stocks = data.get("stocks", [])
    data["run_summary"] = "；".join(
        "{} {}".format(s["name"], s["current"]["date"])
        for s in stocks if s.get("current")
    )
    return {"artifact": data}


if __name__ == "__main__":
    out = run()
    print(out["artifact"].get("run_summary", ""))
    print("stocks:", len(out["artifact"].get("stocks", [])))
