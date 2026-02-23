# 本地归档与清理建议（2026-02-23）

## 结论摘要

当前仓库没有必须立即归档的“旧核心代码”。
建议优先做两类处理：
1) 清理构建产物（不入库）
2) 将阶段性文档标记为历史文档（按需归档）

## 一、建议清理（构建产物，不归档）

这些文件/目录是可再生成内容，建议保留本地即可，不提交 Git：

- `build/`
- `dist/`
- `__pycache__/`
- `NetworkFixer.spec`（由 PyInstaller 命令自动生成，且 `.gitignore` 已忽略 `*.spec`）

## 二、建议作为“历史文档”归档（可选）

以下文档属于阶段性产物，若后续进入稳定维护期，可移动到 `docs/archive/`：

- `REFACTOR_PLAN.md`（重构规划文档）
- `IMPLEMENTATION_LOG.md`（实施过程日志）
- `PERFORMANCE_OPTIMIZATIONS.md`（阶段优化说明）

建议保留：
- `README.md`（当前主文档）
- `CHANGELOG.md`（版本记录）
- `RELEASE_NOTES_v2.0.1.md`（当前发布说明）

## 三、代码层面归档候选（可选）

- `test_optimizations.py`
  - 当前偏“历史性能验证脚本”，且部分逻辑仍基于早期单文件实现。
  - 若后续使用 pytest 体系，可移动到 `tools/archive/` 或 `docs/archive/scripts/`，并在 README 标注其历史属性。

## 四、建议执行顺序

1. 先发布 `v2.0.1`。
2. 发布后在新分支做文档归档（避免影响本次 Release）。
3. 完成归档后更新 README 的文档索引路径。
