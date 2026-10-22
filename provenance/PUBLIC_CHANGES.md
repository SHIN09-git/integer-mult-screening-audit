# 公开整理的来源与修改

来源是整数乘法第二轮研究在提交 `701f3acdb5cf656cff72bc0660e09f8cf7b9fc47` 导出的独立包，原分析日期为 2026-10-15。

[ORIGINAL_FILES.csv](ORIGINAL_FILES.csv) 保存原包 51 个文件的路径、大小和散列；[FROZEN_SHA256.csv](FROZEN_SHA256.csv) 对其中 48 个未经修改的文件逐一绑定。三个修改文件在 [PUBLIC_CHANGES.json](PUBLIC_CHANGES.json) 中记录前后散列及原因：

1. `study/TIMINGS.json` 仅移除 `environment.executable` 中的本机用户路径，数值样本、判定、统计摘要全部保留。
2. `study/BENCHMARK-PROVENANCE.json` 增加上述脱敏记录，保留原散列并更新公开文件散列。原输入、精确结果和计时代码散列不变。
3. `study/README.md` 增加公开整理署名和日期说明，把本项目运行命令改成独立包路径，替换仅完整上游仓库才有的启动命令。

上述第 2、3 项已修改文本采用 LF 换行，保证 Git 导出后的字节与清单一致；没有新增第四项原文件修改。

新加入顶层署名、许可说明、引用、中文报告、可移植运行器、标准库计时摘要核查和验证记录。上游算法、31,392 条辅助位置安排、精确结果与历史计时样本没有重写。

历史原包中 `VALIDATION.json` 和任务记录描述当时的研究状态；当前状态以顶层 [VALIDATION.md](../VALIDATION.md) 为准。原工作目录和同步参考资料保持不变。未创建远程仓库、发布版本或向上游发送消息。

