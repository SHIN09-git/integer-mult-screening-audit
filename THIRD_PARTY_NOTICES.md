# 上游来源与贡献归属

| 来源 | 固定版本 | 本项目使用的内容 |
| --- | --- | --- |
| Aaron Wang / navinor，[PR #1669](https://github.com/CrocSwap/integer-mult-bounds/pull/1669) | `b910e86383b2270cf14b7b659a808fa0eb075c7d` | 二次比较界、精确筛选器、12 项继承控制 |
| Dugongue，[PR #2260](https://github.com/CrocSwap/integer-mult-bounds/pull/2260) | `fde6b107e26a14da5bac5b66913c914708ea6901` | 固定旧账单、31,392 条辅助位置安排、完整算术结果及继承来源 |
| Dugongue，[PR #2284](https://github.com/CrocSwap/integer-mult-bounds/pull/2284) | `e71574b92f6af546013c71293cd03ff58742a1e6` | 更高目标 `84179/50000000` 的结果记录和来源说明 |

固定输入的来源路径、提交、Git 对象和 SHA-256 在 [study/SOURCES.json](study/SOURCES.json) 与 [COMPETITIVE-SOURCE.json](study/COMPETITIVE-SOURCE.json)。运行时使用包内输入，不自动改用这些 PR 的最新版本。

主要保留说明：

- [PR #1669 原说明](study/inputs/pr1669/README.md)，含定理和先行方法署名。
- [PR #2260 NOTICE](study/inputs/pr2260/NOTICE.md)，含借用构造、算术实现及外层组装来源。
- [PR #2284 NOTICE](study/competitive-input/NOTICE.md)，含更高目标所属新构造的信用链。
- `study/notices/pr2260/` 中的 PR #1005、#1862、#1972、#1991、#2226 和 FRAME-SA504 原始说明。

这些源文档保留原仓库上下文，个别相对链接或命令指向源仓库内本包未附带的文件。它们是来源证据；本包可直接执行的命令统一见 [REPRODUCING.md](REPRODUCING.md)。无需补齐整个上游仓库即可运行本项目核验。

2026-10-22 已通过 GitHub 连接核对固定版本的 Apache-2.0 许可和相关说明。本次不以 PR 当前是否开放、合并或被替代来推断数学结果，也不声称完成全库新颖性检索。读取来源没有向上游发送消息或创建提交。

项目附带的账单和精确结果不表示本项目作者重新完成了原始底层线路、精度、空间安排和任意规模理论的全部验证。必须同时保留这些适用边界。

