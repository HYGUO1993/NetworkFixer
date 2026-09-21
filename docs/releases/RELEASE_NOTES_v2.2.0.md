# NetworkFixer v2.2.0 Release Notes

发布日期：2026-09-21

## Microsoft 服务诊断

关闭 Clash 或其他代理后，浏览器和 GitHub 可能已经正常，Microsoft Store 仍提示「初始化失败」。Store、winget 和部分登录窗口使用的网络路径与 Chrome/Edge 不完全相同，容易被残留的 WinHTTP 代理或 PAC 地址挡住。

v2.2.0 在修复前后自动记录：

- `netsh winhttp show proxy`
- 用户代理 `ProxyEnable`、`ProxyServer`、`AutoConfigURL`
- `login.live.com:443` 与 `storeedgefd.dsx.mp.microsoft.com:443` 的 TCP 连通性

日志会给出这样的结论：

```text
Detected:
✓ 互联网可达
✗ 检测到残留系统代理
✗ Microsoft 服务端点不可达

Repair:
✓ 关闭失效代理
✓ 刷新 DNS
✓ 重置 Winsock

Result:
✓ Microsoft 服务端点已恢复
```

「关闭系统代理」现在会同时删除残留 PAC，并执行 `netsh winhttp reset proxy`。也可以只点「微软服务诊断」做复查。

## 从 GitHub Release 更新

打包后的程序主界面有「更新到最新版」。它会读取本仓库最新 Release，下载 Windows 安装包，并用随包发布的 SHA256 校验。校验通过后程序退出，由辅助进程覆盖安装目录并重新启动。

用 `python fix_network.py` 运行时不会覆盖源码目录，只会打开最新 Release 页面。
