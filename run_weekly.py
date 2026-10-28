# 兼容垫片：管线本体在 hshare/run_weekly.py。
# 因当前 PAT 未含 Workflows 权限，.github/workflows/weekly-update.yml 暂无法改路径，
# 保留本文件使旧 workflow（python run_weekly.py）照常工作。
import os
import sys
import runpy

HERE = os.path.dirname(os.path.abspath(__file__))
HK = os.path.join(HERE, "hshare")
sys.path.insert(0, HK)          # hshare/ 内脚本互相 import 依赖此路径
runpy.run_path(os.path.join(HK, "run_weekly.py"), run_name="__main__")
