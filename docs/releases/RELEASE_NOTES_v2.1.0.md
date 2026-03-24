# NetworkFixer v2.1.0 Release Notes

发布日期：2026-03-24

## 🌟 重大新功能：幽灵代理专杀 (Proxy Ghost Killer)

### 功能概述

v2.1.0 版本引入了全新的"幽灵代理专杀"功能，专门解决开发者在本地开发中的常见痛点：

**问题场景**：
- 关闭代理软件（如 Clash、V2Ray、Shadowsocks）后，系统或终端残留了 `http_proxy` 或 `https_proxy` 环境变量
- 底层 HTTP 客户端（curl、请求库）依然尝试向未监听的本地端口（如 127.0.0.1:7890）发送请求
- 导致 `500 Internal Server Error`、`Connection refused` 或请求超时

**解决方案**：
NetworkFixer v2.1.0 新增的幽灵代理专杀功能可以：
1. 自动扫描所有级别的代理环境变量
2. 智能检测代理是否真正存活
3. 一键清除失效的"幽灵代理"配置

### 核心特性

#### 1. 环境变量全景扫描 (Env Var Scanner)
- **三级扫描**：进程级 (Process)、用户级 (User)、系统级 (Machine)
- **全面覆盖**：检测所有代理相关变量
  - `http_proxy` / `HTTP_PROXY`
  - `https_proxy` / `HTTPS_PROXY`
  - `all_proxy` / `ALL_PROXY`
- **兼容大小写**：同时检查大小写变体，确保不遗漏任何配置

#### 2. 代理健康度靶向测试 (Proxy Health Check)
- **TCP 连接测试**：解析代理 URL，提取 IP 和端口
- **快速检测**：仅进行 TCP 握手测试，2 秒超时
- **精准判断**：
  - 🟢 连接成功 → 代理已配置且运行正常
  - 🔴 连接失败 → 检测到失效的幽灵代理死胡同

#### 3. 一键排雷与修复 (One-Click Remediation)
- **临时急救**：清空当前运行上下文（Process 级别）的代理环境变量
- **彻底清理**：
  - **用户级**：删除注册表 `HKEY_CURRENT_USER\Environment` 中的残留项
  - **系统级**：删除注册表 `HKEY_LOCAL_MACHINE\SYSTEM\...\Environment` 中的残留项
- **权限处理**：
  - 用户级清理：无需特殊权限
  - 系统级清理：需要管理员权限，会优雅地捕获权限错误并提示

#### 4. 友好的 CLI 输出
- **状态表情符号**：
  - 🔍 扫描中
  - ✅ 无问题
  - 🟢 代理正常
  - 🔴 检测到死代理
  - ⚠️ 修复中
  - 🚀 修复成功
- **清晰的结果展示**：按级别（Process/User/Machine）分类显示
- **中英双语**：完整支持中文和英文界面

## 📋 使用方法

### 在 GUI 中使用

1. 启动 NetworkFixer（以管理员身份运行）
2. 在主界面找到"检测幽灵代理"按钮（位于按钮区第二行）
3. 点击按钮开始扫描
4. 查看扫描结果：
   - 如果没有检测到代理环境变量，会显示"未检测到代理环境变量"
   - 如果检测到正常运行的代理，会显示代理详情
   - 如果检测到失效的代理，会询问是否清除
5. 确认清除后，系统会自动清理失效的代理配置
6. 重启终端和相关应用使更改生效

### 技术实现

新增的核心模块：
- `networkfixer/core/proxy_env.py`
  - `ProxyGhostKiller` - 主控制类
  - `ProxyEnvScanner` - 环境变量扫描器
  - `ProxyHealthChecker` - TCP 健康检查器
  - `ProxyEnvInfo` - 代理信息数据类

集成点：
- `NetworkOperations` 类新增 `scan_proxy_env()` 和 `fix_proxy_env()` 方法
- UI 新增独立的扫描和修复流程

## 🔧 技术细节

### 扫描逻辑
```python
# 进程级别：读取当前环境变量
os.environ.get(var_name)

# 用户级别：读取注册表
winreg.OpenKey(HKEY_CURRENT_USER, "Environment")

# 系统级别：读取注册表
winreg.OpenKey(HKEY_LOCAL_MACHINE, "SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment")
```

### 健康检查
```python
# TCP 端口连接测试
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(2.0)
result = sock.connect_ex((host, port))
# result == 0 表示连接成功
```

### 修复操作
```python
# 进程级：直接删除环境变量
del os.environ[var_name]

# 用户/系统级：删除注册表值
winreg.DeleteValue(key, var_name)
```

## 🎯 适用场景

这个功能特别适合以下用户：
- 经常使用代理软件（Clash/V2Ray/SSR）的开发者
- 需要在有/无代理之间频繁切换的用户
- 遇到"代理已关闭但请求仍然失败"问题的用户
- 使用命令行工具（curl、git、npm、pip 等）的开发者

## 🔄 兼容性

- **Windows 版本**：Windows 7 及以上
- **Python 版本**：Python 3.8+
- **依赖**：无新增运行时依赖，继续保持纯标准库

## 📦 升级说明

从 v2.0.x 升级到 v2.1.0：
1. 下载最新的可执行文件或更新源代码
2. 运行即可，无需额外配置
3. 新功能向后兼容，不影响现有功能

## 🐛 已知问题

无

## 🙏 致谢

感谢所有提出代理环境变量问题的用户反馈。

---

**下载地址**：[GitHub Releases](https://github.com/HYGUO1993/NetworkFixer/releases/tag/v2.1.0)

**问题反馈**：[GitHub Issues](https://github.com/HYGUO1993/NetworkFixer/issues)
