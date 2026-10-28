# 兼容垫片：管线本体在 hshare/run_weekly.py。
# 因当前 PAT 未含 Workflows 权限，.github/workflows/weekly-update.yml 暂无法改路径，
# 保留本文件使旧 workflow（python run_weekly.py）照常工作。
import runpy
runpy.run_path("hshare/run_weekly.py", run_name="__main__")
