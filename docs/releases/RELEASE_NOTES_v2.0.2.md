# NetworkFixer v2.0.2

发布日期：2026-02-23

## 亮点

- 修复高分屏（2.5K 等）下界面发糊问题：新增 Windows DPI 感知与 Tk 缩放适配。
- 放大“执行日志与结果”区域：默认窗口高度提升，日志可见行数增加。
- 整理文档结构：历史过程文档迁移到 `docs/archive/`，发布说明集中在 `docs/releases/`。

## 技术说明

- 入口文件新增高 DPI 处理：
  - `SetProcessDpiAwarenessContext`（优先 Per Monitor v2）
  - `SetProcessDpiAwareness` / `SetProcessDPIAware`（兼容兜底）
  - Tk `scaling` 按实际 DPI 自动设置

## 兼容性

- 运行时仍为 Python 标准库，无新增外部依赖。
- 支持 Windows（Python 3.8+）。

## 下载

请前往 GitHub Releases 获取本版本构建产物。
