# NetworkFixer v2.0.1

发布日期：2026-02-23

## 亮点

- 修复主按钮在部分 Windows 主题下文字不可见的问题。
- 修复按钮区最后一个按钮过窄的问题，统一为四列等宽布局。
- 选项区升级为更紧凑的两栏卡片布局（基础修复 / 高级修复）。
- 新增顶部状态徽标，实时显示执行状态（就绪/执行中/测试中/已完成/异常/已取消）。

## 文档与发布一致性

- 同步更新 `README.md`、`CHANGELOG.md`、`IMPLEMENTATION_LOG.md`、`PERFORMANCE_OPTIMIZATIONS.md`、`REFACTOR_PLAN.md`。
- 版本号统一升级为 `2.0.1`：
  - `networkfixer/__init__.py`
  - `networkfixer/ui/app.py`
  - `pyproject.toml`

## 兼容性

- 运行时仍为 Python 标准库，无新增外部依赖。
- 支持 Windows 环境（Python 3.8+）。

## 升级建议

- 普通用户：下载 `v2.0.1` Release 附件并覆盖旧版本。
- 开发者：拉取最新代码后重新打包。

## 打包命令

```powershell
pip install -r requirements.txt
pyinstaller --noconfirm --clean --windowed --name NetworkFixer fix_network.py
```

## Git 标签与发布建议

```powershell
git add .
git commit -m "release: v2.0.1"
git tag -a v2.0.1 -m "NetworkFixer v2.0.1"
git push origin main
git push origin v2.0.1
```

发布 GitHub Release 时可直接粘贴本文件内容。
