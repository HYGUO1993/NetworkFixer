# 网络修复工具（增强版）

一个用于在 Windows 上快速修复网络连接问题的图形化小工具（Tkinter）。支持关闭系统代理、刷新 DNS、重置 Winsock、重置 IP、重置 TCP/IP 协议栈、重启指定网卡，并可在完成后或单独进行网络连通性测试。提供彩色日志、进度条、日志导出和自动管理员提权提示。

## 功能特点
- 一键执行常见网络修复步骤（勾选控制，按顺序执行）
- 查看与关闭系统代理配置（当前用户）
- 刷新 DNS 缓存、重置 Winsock、重置 IP 地址
- 可选重置 TCP/IP 协议栈（`netsh int ip reset`）
- 可选重启指定网卡（`netsh interface set interface`）
- 连通性测试：Ping 114.114.114.114、8.8.8.8 和 HTTP 测试（可单独运行）
- 彩色日志与进度条实时反馈，支持一键导出日志
- 自动管理员提权提示（阻止 UAC 取消后直接闪退）

## 运行环境
- Windows 10/11
- Python 3.8+（自带 Tkinter）

## 使用指引

### 直接运行（不打包）
```powershell
# 进入项目目录
cd "c:\Users\guoho\OneDrive\小工具开发\NetworkFixer"

# 运行（将弹出管理员授权提示）
python fix_network.py
```

如果想在命令行直接以管理员启动：
```powershell
powershell -Command "Start-Process python fix_network.py -Verb runAs"
```

### 基础操作步骤
- 勾选需要的修复项 → 点击“开始修复”。
- 仅想检测网络连通性可直接点“仅连通性测试”。
- 如需把执行记录发给他人排查，点击“导出日志”。

## 打包为 EXE（使用 PyInstaller）
```powershell
# 安装 PyInstaller（仅需一次）
pip install pyinstaller

# 进入项目目录
cd "c:\Users\guoho\OneDrive\小工具开发\NetworkFixer"

# 打包为无控制台窗口的可执行文件
pyinstaller --noconfirm --clean --windowed --name NetworkFixer fix_network.py
```
- 打包完成后，EXE 位于：`dist/NetworkFixer/NetworkFixer.exe`
- 首次运行会触发管理员授权（UAC），请允许以便执行网络命令。

管理员启动 EXE 的命令行示例：
```powershell
powershell -Command "Start-Process .\dist\NetworkFixer\NetworkFixer.exe -Verb runAs"
```

## 使用步骤（GUI）
- 默认勾选：关闭系统代理、刷新 DNS、重置 Winsock、重置 IP；如需更彻底可勾选“重置 TCP/IP 协议栈”。
- 若要重启网卡，先在下拉框选择网卡名称（来源 `netsh interface show interface`）再勾选。
- 点击“开始修复”按顺序执行勾选步骤；完成后自动连通性测试。
- 仅需测试时，可点击“仅连通性测试”。
- 日志可随时点击“导出日志”保存为 txt 便于反馈。

## 常见说明
- 勾选“重置 TCP/IP 协议栈”后通常需要重启系统。
- 关闭系统代理作用于当前用户的注册表 `Internet Settings`。
- HTTP 测试使用微软连接性测试地址：`http://www.msftconnecttest.com/redirect`。
- 部分公司/受管设备可能有策略阻止 `netsh`/`ipconfig`，若执行失败请联系 IT 管理员。

## 常见问题 (Troubleshooting)
- 运行即退出/未见窗口：请确认以管理员身份启动；若 UAC 被安全软件拦截，请在信任后重试。
- UAC 未弹出：在管理员 PowerShell 中执行上面的 Start-Process 提权命令，或右键“以管理员身份运行”。
- 无法导出日志：确认目标目录写入权限，或导出到桌面再尝试。
- 重置 TCP/IP 后仍无网：尝试重启电脑/路由器，或联系网络管理员；如为受管设备可能被策略限制。
- Ping 不通但 HTTP 可用：可能被 ICMP 屏蔽，重点关注 HTTP 结果。

## 目录结构
- `fix_network.py`：主程序
- `README.md`：使用说明
- `NetworkFixer.spec`：PyInstaller 打包配置（可按需调整图标、文件收集）

## 免责声明
- 本工具仅执行常见网络修复命令，使用前请确保了解其效果；若为公司或受管设备，请遵循相关IT策略。
