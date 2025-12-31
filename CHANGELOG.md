# 更新日志 (Changelog)

## [v1.0.1] - 2025-12-31

### 🐛 修复 (Fixes)
- **修复编码问题**：解决了在某些系统上执行 `netsh` 或 `ipconfig` 命令时因非标准字符输出导致的 `UnicodeDecodeError` 崩溃问题。现在程序能正确处理 GBK/ANSI 编码的命令输出。
- **修复网卡识别**：优化了 `netsh interface show interface` 的解析逻辑，现在可以正确识别名称中包含空格的网卡（例如 "Ethernet 2" 或 "本地连接 2"），修复了网卡列表为空的问题。

## [v1.0.0] - 2025-12-31
- 初始版本发布。
- 支持关闭系统代理、刷新 DNS、重置 Winsock、重置 IP 等基础功能。
- 支持连通性测试 (Ping/HTTP)。
