# 复现说明

环境为 Python 3.12，只使用标准库和随包的上游实现。直接运行不需要联网、Git、第三方库或 GPU。Windows 可用 `python`，Linux/macOS 可用已安装的 `python3.12`。

所有顶层命令从项目根目录执行。每次生成新的 `reproductions/时间戳-后缀/`，也可用 `--output "一个尚不存在的目录"` 指定位置。已有目录会被拒绝，冻结结果不会被覆盖。

## 默认核验

```text
python reproduce.py
```

默认执行以下工作：

1. 核验包内清单、48 个未修改的原研究文件以及 3 项已记录的公开整理修改。
2. 从全部 581 个历史样本重新计算中位数、四分位数、配对差值和配对百分比，检查样本的判断结果和回退次数。
   对 `validation/20261022/` 中另存的 581 个本次样本执行相同核查，两套结果分别保存。
3. 从全部 31,392 条辅助位置安排重算同一成本账单，运行 8 个主分析组合及 2 个较高目标组合。
4. 运行 17 项语义控制、12 项继承控制，重放原方案完整算术结果，包括 47 条外层严格不等式。
5. 运行 4 项来源或结果篡改检查，确认启用 Python 优化选项时也能拒绝错误记录。
6. 再次核对原文件未改变，并写出 `validation.json` 和 `logs/`。

这里的控制是已存在的具体输入和判断检查，不是穷尽证明。两套精确计算只覆盖原有算术阶段；底层线路、精度、空间安排和任意规模推广的其他义务沿用上游范围。

要排除当前目录和已安装第三方库对顶层入口的影响，可执行：

```text
python -I -S -B reproduce.py
```

## 只核查保存的历史证据

```text
python reproduce.py --mode audit
```

这个入口不重跑精确算术。它核验散列、计时代码与历史归档的对应关系，并重算两套保存样本的统计摘要。它验证的是文件和摘要的一致性，不能替代默认入口。

## 重新计时

```text
python reproduce.py --mode benchmark
```

此模式先完成默认核验，再按保留的研究流程顺序运行三个计时程序：

| 程序 | 日程 | 新进程数 |
| --- | --- | ---: |
| `study/benchmark.py` | 50 个组合 × 7 次重复，固定打乱顺序 | 350 |
| `study/paired_benchmark.py` | 4 种情况 × 21 对，相邻交替次序 | 168 |
| `study/competitive_target.py` | 较高目标，21 组三方法轮换次序 | 63 |
| 合计 | 同一固定旧账单 | 581 |

运行时尽量保持电脑负载稳定。没有清空操作系统文件缓存，不能把进程新启动称为冷磁盘测试。不同电脑、解释器版本或后台负载会改变耗时；**历史约 15% 的收益不是通过标准**。

新样本写入本次输出目录的 `TIMINGS.json`、`PAIRED-TIMINGS.json` 和 `COMPETITIVE-TIMINGS.json`。新的 `new-timing-summary.json` 与历史 `historical-timing-summary.json` 分别保存，避免混合计算。新计时元数据的解释器绝对路径会被移除，不改变数值样本。

## 直接使用原研究程序

需要分步核查时，在本包根目录运行：

```text
python -I -B study/verify.py
python -I -B study/competitive_target.py
python -I -B study/test_receipts.py
```

预期标识分别为 `PASS_PENDING2260_QUADRATIC_SCREEN`、`PASS_PUBLISHED_COMPETITIVE_THRESHOLD` 和 `PASS_PENDING2260_SOURCE_RECEIPT_CONTROLS`。其中 `test_receipts.py` 对故意修改的临时副本进行检查。

保留的低层程序提供 `--write` 或默认计时输出到研究目录等选项。日常复现优先使用顶层入口；它始终指定新输出位置，避免改写历史证据。

## 来源和计时口径

`study/INPUTS.json` 固定 18 个原始输入；`study/COMPETITIVE-SOURCE.json` 另固定较高目标及其说明。改变输入后不能继续沿用旧结果。

`BENCHMARK-HARNESS.zip` 保存实际历史计时代码。历史计时后，原整理仅调整了自有 Python 文件末尾空行，语法树未改变；本次入口会重新核对四个核心计时文件的语法树一致性。文件身份以清单为准，计时值不作为数学判断条件。

`study/` 中的上游 README 保留来源仓库上下文，部分链接和命令需要在完整上游仓库中使用。本页列出的命令全部针对当前独立包。本次实际运行平台和检查范围见 [VALIDATION.md](VALIDATION.md)。

