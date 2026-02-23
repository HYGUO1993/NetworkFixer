# NetworkFixer 重构方案

> 版本: v2.0.0 重构草案（审阅修订版）
> 日期: 2026-02-23
> 状态: 进行中（M1/M2 已完成，M3/M4 待执行）

---

## 0、审阅结论与修订摘要

本版在不改变工具核心能力的前提下，优先将重构目标收敛到 **安全性、稳定性、可维护性** 三条主线，并对执行节奏做了降风险调整。主要修订如下：

1. 将“高风险问题修复（线程安全、命令执行、安全异常处理）”明确为第一里程碑，要求先可运行再拆分模块。[^1]
2. 删除/弱化对“精确代码行号”的依赖，避免后续迭代后文档失真。[^2]
3. 将执行计划由“小时级一次性重构”调整为“里程碑+验收门槛”的渐进策略，降低回归风险。[^3]
4. 将 CI/CD 定位为第二优先级：先完成本地可验证测试基线，再接入 GitHub Actions。[^4]
5. 保持运行时零新增依赖，仅在开发依赖中引入测试与静态检查工具。[^5]

---

## 一、项目现状分析

### 1.1 项目概述

NetworkFixer 是一个 Windows 网络修复工具，主要用于解决 VPN/代理软件关闭后无法上网的问题。

**技术栈**：
- Python 3.8+
- Tkinter (GUI)
- 标准库: subprocess, winreg, ctypes, threading, socket, urllib

**当前文件结构**：
```
NetworkFixer/
├── fix_network.py          # 主程序 (449行，所有逻辑)
├── test_optimizations.py   # 性能测试
├── requirements.txt        # 依赖 (仅 pyinstaller)
├── README.md
├── CHANGELOG.md
├── PERFORMANCE_OPTIMIZATIONS.md
└── NetworkFixer.png        # 截图
```

### 1.2 功能清单

| 功能 | 实现方式 | 状态 |
|------|----------|------|
| 关闭系统代理 | winreg 操作注册表 | ✅ |
| 刷新 DNS 缓存 | ipconfig /flushdns | ✅ |
| 重置 Winsock | netsh winsock reset | ✅ |
| 重置 IP 地址 | ipconfig /release && /renew | ✅ |
| 重置 TCP/IP | netsh int ip reset | ✅ |
| 重启网卡 | netsh interface set interface | ✅ |
| 连通性测试 | ping + HTTP | ✅ |
| 日志导出 | 文件保存 | ✅ |

### 1.3 已识别问题

#### P0 - 严重问题（必须修复）

| 问题 | 严重程度 | 位置 | 影响 |
|------|----------|------|------|
| Tkinter 线程不安全 | 🔴 严重 | fix_network_logic(), connectivity_only() | 随机崩溃/卡死 |
| subprocess shell=True 注入风险 | 🔴 严重 | run_command(), restart_adapter() | 命令注入漏洞 |
| 全局 socket 超时副作用 | 🟡 中等 | test_connectivity() | 影响其他 socket 操作 |
| 裸露 except | 🟡 中等 | is_admin() | 隐藏真实错误 |

#### P1 - 架构问题

| 问题 | 严重程度 | 影响 |
|------|----------|------|
| GUI 与业务逻辑耦合 | 🟡 中等 | 难以测试、难以扩展 |
| 缺少类型注解 | 🟢 低 | IDE 支持差 |
| 缺少结构化日志 | 🟡 中等 | 排查问题困难 |
| 无国际化支持 | 🟡 中等 | 仅支持中文用户 |

---

## 二、重构目标

### 2.1 核心目标

1. **稳定性**：消除线程安全问题，避免随机崩溃
2. **安全性**：消除命令注入风险
3. **可维护性**：GUI 与业务逻辑解耦
4. **国际化**：支持中英文切换
5. **可测试性**：单元测试覆盖核心逻辑

### 2.2 非目标

- 不引入额外运行时依赖（保持纯标准库）
- 不改变现有功能行为（用户无感知）
- 不增加自动更新功能（简化架构）
- 不在本轮引入跨平台适配（维持 Windows 专注）
- 不在本轮引入 asyncio/多进程重构（避免复杂度失控）

---

## 三、架构设计

### 3.1 新目录结构

```
NetworkFixer/
├── fix_network.py              # 入口文件 + 提权逻辑
├── networkfixer/
│   ├── __init__.py             # 版本信息
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── app.py              # Tkinter 主窗口
│   │   ├── widgets.py          # 自定义控件
│   │   └── styles.py           # 样式配置
│   ├── core/
│   │   ├── __init__.py
│   │   ├── executor.py         # 命令执行器（安全封装）
│   │   ├── operations.py       # 网络操作实现
│   │   ├── connectivity.py     # 连通性测试
│   │   ├── adapters.py         # 网卡检测与缓存
│   │   └── registry.py         # 注册表操作
│   ├── models/
│   │   ├── __init__.py
│   │   ├── result.py           # StepResult 数据结构
│   │   └── config.py           # 配置常量
│   ├── i18n/
│   │   ├── __init__.py
│   │   ├── base.py             # 翻译框架
│   │   ├── zh_CN.py            # 中文翻译
│   │   └── en_US.py            # 英文翻译
│   └── utils/
│       ├── __init__.py
│       ├── logger.py           # 日志系统
│       ├── admin.py            # 管理员权限检查
│       └── thread.py           # 线程安全工具
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # pytest 配置
│   ├── test_executor.py
│   ├── test_operations.py
│   ├── test_connectivity.py
│   ├── test_adapters.py
│   └── test_i18n.py
├── resources/
│   └── app.manifest            # UAC 提权清单
├── requirements.txt            # 运行依赖（空）
├── requirements-dev.txt        # 开发依赖
├── pyproject.toml              # 项目配置
├── NetworkFixer.spec           # PyInstaller 配置
├── README.md
├── README_EN.md                # 英文文档
└── CHANGELOG.md
```

### 3.2 模块职责

```
┌─────────────────────────────────────────────────────────────┐
│                      fix_network.py                          │
│                    (入口 + 提权检查)                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     ui/app.py                                │
│                   (Tkinter GUI)                              │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │   widgets.py    │  │    styles.py    │                   │
│  │  (自定义控件)    │  │   (样式配置)    │                   │
│  └─────────────────┘  └─────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
                    ▼                   ▼
┌───────────────────────┐   ┌───────────────────────┐
│     i18n/base.py      │   │   utils/logger.py     │
│    (国际化翻译)        │   │    (日志系统)         │
└───────────────────────┘   └───────────────────────┘
                    │                   │
                    └─────────┬─────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     core/operations.py                       │
│                    (网络操作业务逻辑)                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  executor.py │ registry.py │ adapters.py │ conn.py │    │
│  │  (命令执行)   │ (注册表)    │ (网卡检测)  │ (连通性) │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     models/result.py                         │
│                    (数据结构定义)                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 四、核心模块详细设计

### 4.1 数据模型 (models/result.py)

```python
"""数据结构定义"""
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class LogLevel(Enum):
    """日志级别"""
    INFO = "info"
    SUCCESS = "success"
    WARN = "warn"
    ERROR = "error"


@dataclass
class StepResult:
    """单个操作步骤的结果"""
    ok: bool
    title: str
    output: str = ""
    error: Optional[Exception] = None
    return_code: int = 0
    duration_ms: float = 0.0
    
    def __str__(self) -> str:
        status = "✓" if self.ok else "✗"
        return f"{status} {self.title}"


@dataclass
class ConnectivityResult:
    """连通性测试结果"""
    ping_114: bool = False
    ping_google: bool = False
    http_test: bool = False
    
    @property
    def all_ok(self) -> bool:
        return self.ping_114 and self.http_test


@dataclass
class AdapterInfo:
    """网卡信息"""
    name: str
    is_connected: bool = True


@dataclass
class ProxyStatus:
    """代理状态"""
    enabled: bool
    server: str = ""


@dataclass
class AppConfig:
    """应用配置"""
    # 超时配置
    ping_timeout_ms: int = 2000
    http_timeout_sec: int = 3
    adapter_cache_ttl_sec: int = 5
    
    # 日志配置
    log_to_file: bool = True
    log_file_name: str = "networkfixer.log"
    
    # UI 配置
    window_width: int = 560
    window_height: int = 600
    
    # 语言
    language: str = "zh_CN"
```

### 4.2 命令执行器 (core/executor.py)

```python
"""安全的命令执行器"""
import subprocess
import time
import logging
from typing import Tuple, List, Union, Optional

from ..models.result import StepResult

logger = logging.getLogger(__name__)

# Windows 常量
CREATE_NO_WINDOW = 0x08000000


class CommandExecutor:
    """安全的命令执行器，避免 shell 注入"""
    
    def __init__(self, hide_window: bool = True):
        self.hide_window = hide_window
    
    def run(
        self,
        command: Union[str, List[str]],
        shell: bool = False,
        timeout: Optional[float] = None,
        check: bool = True
    ) -> StepResult:
        """
        执行命令并返回结果
        
        Args:
            command: 命令字符串或参数列表
            shell: 是否使用 shell（尽量避免）
            timeout: 超时时间（秒）
            check: 是否检查返回码
        
        Returns:
            StepResult 对象
        """
        start_time = time.time()
        
        # 构造 creationflags
        creationflags = CREATE_NO_WINDOW if self.hide_window else 0
        
        try:
            if isinstance(command, str) and not shell:
                # 字符串命令转为参数列表
                args = self._parse_command(command)
            else:
                args = command
            
            logger.debug(f"Executing: {args}")
            
            proc = subprocess.run(
                args,
                shell=shell,
                check=check,
                creationflags=creationflags,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                text=False  # 手动处理编码
            )
            
            output = self._decode_output(proc.stdout)
            duration_ms = (time.time() - start_time) * 1000
            
            return StepResult(
                ok=True,
                title="",
                output=output,
                return_code=proc.returncode,
                duration_ms=duration_ms
            )
            
        except subprocess.CalledProcessError as e:
            output = self._decode_output(e.stdout) if e.stdout else str(e)
            return StepResult(
                ok=False,
                title="",
                output=output,
                error=e,
                return_code=e.returncode
            )
            
        except subprocess.TimeoutExpired as e:
            logger.error(f"Command timeout: {command}")
            return StepResult(
                ok=False,
                title="",
                output="Command timed out",
                error=e
            )
            
        except Exception as e:
            logger.exception(f"Command execution failed: {e}")
            return StepResult(
                ok=False,
                title="",
                output=str(e),
                error=e
            )
    
    def run_chain(self, commands: List[Union[str, List[str]]]) -> StepResult:
        """
        顺序执行多个命令（替代 shell 的 &&）
        
        Args:
            commands: 命令列表
        
        Returns:
            最后一个命令的结果，或第一个失败的命令结果
        """
        for cmd in commands:
            result = self.run(cmd)
            if not result.ok:
                return result
        return result  # 返回最后一个成功结果
    
    @staticmethod
    def _parse_command(command: str) -> List[str]:
        """将命令字符串解析为参数列表"""
        # 简单实现，处理带空格的参数
        import shlex
        return shlex.split(command)
    
    @staticmethod
    def _decode_output(data: bytes) -> str:
        """解码命令输出，处理编码问题"""
        if not data:
            return ""
        
        # 优先尝试 mbcs (Windows 默认)
        for encoding in ['mbcs', 'utf-8', 'gbk']:
            try:
                return data.decode(encoding).strip()
            except (UnicodeDecodeError, LookupError):
                continue
        
        # 最后使用替换模式
        return data.decode('utf-8', errors='replace').strip()


# 全局执行器实例
_executor: Optional[CommandExecutor] = None


def get_executor() -> CommandExecutor:
    """获取全局执行器实例"""
    global _executor
    if _executor is None:
        _executor = CommandExecutor()
    return _executor
```

### 4.3 网络操作 (core/operations.py)

```python
"""网络操作业务逻辑"""
import time
import logging
from typing import List, Callable, Tuple

from .executor import get_executor
from .registry import ProxyRegistry
from .adapters import AdapterManager
from .connectivity import ConnectivityTester
from ..models.result import StepResult, AppConfig
from ..models.config import get_config

logger = logging.getLogger(__name__)


class Step:
    """操作步骤定义"""
    
    def __init__(self, title_key: str, func: Callable[[], StepResult]):
        self.title_key = title_key  # i18n key
        self.func = func


class NetworkOperations:
    """网络操作业务逻辑（纯业务，无 GUI 依赖）"""
    
    def __init__(self, config: AppConfig = None):
        self.config = config or get_config()
        self.executor = get_executor()
        self.proxy_registry = ProxyRegistry()
        self.adapter_manager = AdapterManager(
            cache_ttl=self.config.adapter_cache_ttl_sec
        )
        self.connectivity_tester = ConnectivityTester(
            ping_timeout_ms=self.config.ping_timeout_ms,
            http_timeout_sec=self.config.http_timeout_sec
        )
    
    # ========== 代理操作 ==========
    
    def get_proxy_status(self) -> Tuple[bool, str]:
        """获取系统代理状态"""
        return self.proxy_registry.get_status()
    
    def disable_proxy(self) -> StepResult:
        """关闭系统代理"""
        return self.proxy_registry.disable()
    
    # ========== 网络重置操作 ==========
    
    def flush_dns(self) -> StepResult:
        """刷新 DNS 缓存"""
        result = self.executor.run("ipconfig /flushdns")
        result.title = "flush_dns"
        return result
    
    def reset_winsock(self) -> StepResult:
        """重置 Winsock"""
        result = self.executor.run("netsh winsock reset")
        result.title = "reset_winsock"
        return result
    
    def reset_ip(self) -> StepResult:
        """重置 IP 地址（release + renew）"""
        # 使用顺序执行替代 shell 链式命令
        result = self.executor.run_chain([
            ["ipconfig", "/release"],
            ["ipconfig", "/renew"]
        ])
        result.title = "reset_ip"
        return result
    
    def reset_tcpip(self) -> StepResult:
        """重置 TCP/IP 协议栈"""
        result = self.executor.run("netsh int ip reset")
        result.title = "reset_tcpip"
        return result
    
    # ========== 网卡操作 ==========
    
    def list_adapters(self) -> List[str]:
        """获取网卡列表"""
        return self.adapter_manager.list_names()
    
    def refresh_adapters(self, force: bool = False) -> List[str]:
        """刷新网卡列表"""
        return self.adapter_manager.refresh(force)
    
    def restart_adapter(self, adapter_name: str) -> StepResult:
        """重启指定网卡"""
        # 验证网卡名称安全性
        if not self.adapter_manager.validate_name(adapter_name):
            return StepResult(
                ok=False,
                title="restart_adapter",
                output="Invalid adapter name"
            )
        
        # 使用顺序执行替代 shell 链式命令
        result = self.executor.run_chain([
            ["netsh", "interface", "set", "interface", 
             adapter_name, "admin=disabled"],
            ["netsh", "interface", "set", "interface", 
             adapter_name, "admin=enabled"]
        ])
        result.title = "restart_adapter"
        return result
    
    # ========== 连通性测试 ==========
    
    def test_connectivity(self) -> dict:
        """测试网络连通性"""
        return self.connectivity_tester.test()
    
    # ========== 步骤构建 ==========
    
    def build_steps(
        self,
        do_proxy: bool,
        do_dns: bool,
        do_winsock: bool,
        do_ip: bool,
        do_tcpip: bool,
        do_adapter: bool,
        adapter_name: str = ""
    ) -> List[Step]:
        """构建操作步骤列表"""
        steps = []
        
        if do_proxy:
            steps.append(Step("step.disable_proxy", self.disable_proxy))
        if do_dns:
            steps.append(Step("step.flush_dns", self.flush_dns))
        if do_winsock:
            steps.append(Step("step.reset_winsock", self.reset_winsock))
        if do_ip:
            steps.append(Step("step.reset_ip", self.reset_ip))
        if do_tcpip:
            steps.append(Step("step.reset_tcpip", self.reset_tcpip))
        
        if do_adapter and adapter_name:
            steps.append(Step(
                "step.restart_adapter",
                lambda: self.restart_adapter(adapter_name)
            ))
        
        return steps
    
    def execute_steps(
        self,
        steps: List[Step],
        progress_callback: Callable[[int, int, str], None] = None,
        cancel_check: Callable[[], bool] = None
    ) -> List[StepResult]:
        """
        执行步骤列表
        
        Args:
            steps: 步骤列表
            progress_callback: 进度回调 (current, total, title)
            cancel_check: 取消检查函数
        
        Returns:
            结果列表
        """
        results = []
        total = len(steps)
        
        for i, step in enumerate(steps):
            # 检查是否取消
            if cancel_check and cancel_check():
                logger.info("Operation cancelled by user")
                break
            
            # 进度回调
            if progress_callback:
                progress_callback(i + 1, total, step.title_key)
            
            # 执行步骤
            result = step.func()
            results.append(result)
            
            logger.info(f"Step {i+1}/{total}: {result}")
        
        return results
```

### 4.4 注册表操作 (core/registry.py)

```python
"""Windows 注册表操作"""
import winreg
import logging
from typing import Tuple

from ..models.result import StepResult

logger = logging.getLogger(__name__)


class ProxyRegistry:
    """系统代理注册表操作"""
    
    REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    
    def get_status(self) -> Tuple[bool, str]:
        """
        获取代理状态
        
        Returns:
            (是否启用, 服务器地址)
        """
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.REGISTRY_PATH,
                0,
                winreg.KEY_READ
            ) as key:
                try:
                    enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
                except FileNotFoundError:
                    enable = 0
                
                try:
                    server, _ = winreg.QueryValueEx(key, "ProxyServer")
                except FileNotFoundError:
                    server = ""
                
                return bool(enable), server
                
        except Exception as e:
            logger.error(f"Failed to get proxy status: {e}")
            return False, ""
    
    def disable(self) -> StepResult:
        """
        关闭系统代理
        
        Returns:
            操作结果
        """
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.REGISTRY_PATH,
                0,
                winreg.KEY_WRITE
            ) as key:
                winreg.SetValueEx(
                    key, "ProxyEnable", 0, winreg.REG_DWORD, 0
                )
                winreg.SetValueEx(
                    key, "ProxyServer", 0, winreg.REG_SZ, ""
                )
            
            logger.info("System proxy disabled")
            return StepResult(ok=True, title="disable_proxy")
            
        except PermissionError as e:
            logger.error(f"Permission denied: {e}")
            return StepResult(
                ok=False,
                title="disable_proxy",
                error=e,
                output="Permission denied"
            )
        except Exception as e:
            logger.exception(f"Failed to disable proxy: {e}")
            return StepResult(
                ok=False,
                title="disable_proxy",
                error=e,
                output=str(e)
            )
```

### 4.5 网卡管理 (core/adapters.py)

```python
"""网卡检测与管理"""
import re
import time
import logging
from typing import List, Optional

from .executor import get_executor
from ..models.result import AdapterInfo

logger = logging.getLogger(__name__)


# 危险字符，禁止出现在网卡名称中
DANGEROUS_CHARS = set('"\'&|;()`$\\n\\r')


class AdapterManager:
    """网卡管理器"""
    
    def __init__(self, cache_ttl: int = 5):
        self.cache_ttl = cache_ttl
        self._cache: Optional[List[str]] = None
        self._cache_time: float = 0
        self.executor = get_executor()
    
    def list_names(self) -> List[str]:
        """获取所有网卡名称列表"""
        result = self.executor.run(
            ["netsh", "interface", "show", "interface"]
        )
        
        if not result.ok:
            logger.error(f"Failed to list adapters: {result.output}")
            return []
        
        return self._parse_output(result.output)
    
    def refresh(self, force: bool = False) -> List[str]:
        """
        刷新网卡列表（带缓存）
        
        Args:
            force: 是否强制刷新
        
        Returns:
            网卡名称列表
        """
        current_time = time.time()
        
        if not force and self._cache:
            if current_time - self._cache_time < self.cache_ttl:
                return self._cache
        
        self._cache = self.list_names()
        self._cache_time = current_time
        
        return self._cache
    
    def validate_name(self, name: str) -> bool:
        """
        验证网卡名称是否安全
        
        Args:
            name: 网卡名称
        
        Returns:
            是否安全
        """
        if not name:
            return False
        
        # 检查危险字符
        if any(c in DANGEROUS_CHARS for c in name):
            logger.warning(f"Invalid adapter name: {name}")
            return False
        
        return True
    
    @staticmethod
    def _parse_output(output: str) -> List[str]:
        """
        解析 netsh 输出
        
        示例输出:
        Admin State    Type          Interface Name
        -----------------------------------------
        Enabled        Dedicated     Ethernet
        Enabled        Dedicated     Wi-Fi
        
        Args:
            output: netsh 命令输出
        
        Returns:
            网卡名称列表
        """
        names = []
        
        for line in output.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            
            # 跳过分隔线和表头
            if stripped.startswith('-'):
                continue
            if 'Admin' in stripped or '管理员' in stripped:
                continue
            
            # 按空白分割，最后一列是网卡名称
            parts = stripped.split()
            if len(parts) >= 4:
                # 第4列开始是网卡名称（可能包含空格）
                name = ' '.join(parts[3:])
                names.append(name)
        
        logger.debug(f"Parsed adapters: {names}")
        return names
```

### 4.6 连通性测试 (core/connectivity.py)

```python
"""网络连通性测试"""
import socket
import urllib.request
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict

from ..models.result import ConnectivityResult, AppConfig

logger = logging.getLogger(__name__)


class ConnectivityTester:
    """连通性测试器"""
    
    # 测试端点
    PING_TARGETS = [
        ("ping_114", "114.114.114.114"),
        ("ping_google", "8.8.8.8"),
    ]
    
    HTTP_TARGET = "http://www.msftconnecttest.com/redirect"
    
    def __init__(
        self,
        ping_timeout_ms: int = 2000,
        http_timeout_sec: int = 3
    ):
        self.ping_timeout_ms = ping_timeout_ms
        self.http_timeout_sec = http_timeout_sec
        self.executor = get_executor()
    
    def test(self, parallel: bool = True) -> ConnectivityResult:
        """
        执行连通性测试
        
        Args:
            parallel: 是否并行执行
        
        Returns:
            测试结果
        """
        if parallel:
            return self._test_parallel()
        else:
            return self._test_sequential()
    
    def _test_sequential(self) -> ConnectivityResult:
        """顺序测试"""
        result = ConnectivityResult()
        
        # Ping 测试
        result.ping_114 = self._ping(self.PING_TARGETS[0][1])
        result.ping_google = self._ping(self.PING_TARGETS[1][1])
        
        # HTTP 测试
        result.http_test = self._http_test()
        
        return result
    
    def _test_parallel(self) -> ConnectivityResult:
        """并行测试"""
        result = ConnectivityResult()
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {}
            
            # 提交 ping 任务
            for key, target in self.PING_TARGETS:
                future = executor.submit(self._ping, target)
                futures[future] = key
            
            # 提交 HTTP 任务
            future = executor.submit(self._http_test)
            futures[future] = "http"
            
            # 收集结果
            for future in as_completed(futures):
                key = futures[future]
                try:
                    value = future.result()
                    if key == "ping_114":
                        result.ping_114 = value
                    elif key == "ping_google":
                        result.ping_google = value
                    elif key == "http":
                        result.http_test = value
                except Exception as e:
                    logger.error(f"Test {key} failed: {e}")
        
        return result
    
    def _ping(self, target: str) -> bool:
        """
        执行 ping 测试
        
        Args:
            target: 目标地址
        
        Returns:
            是否可达
        """
        cmd = [
            "ping",
            "-n", "1",
            "-w", str(self.ping_timeout_ms),
            target
        ]
        
        result = self.executor.run(cmd, check=False)
        return result.return_code == 0
    
    def _http_test(self) -> bool:
        """
        执行 HTTP 测试
        
        Returns:
            是否可达
        """
        try:
            # 使用局部超时，不设置全局超时
            with urllib.request.urlopen(
                self.HTTP_TARGET,
                timeout=self.http_timeout_sec
            ) as response:
                return 200 <= response.getcode() < 400
        except Exception as e:
            logger.debug(f"HTTP test failed: {e}")
            return False


# 延迟导入避免循环依赖
def get_executor():
    from .executor import get_executor as _get
    return _get()
```

### 4.7 线程安全工具 (utils/thread.py)

```python
"""线程安全工具"""
import queue
import logging
from typing import Callable, Any
from tkinter import Tk

logger = logging.getLogger(__name__)


class UISafeCaller:
    """
    UI 线程安全调用器
    
    Tkinter 不是线程安全的，所有 UI 操作必须在主线程执行。
    此工具提供安全的跨线程 UI 更新机制。
    """
    
    def __init__(self, root: Tk, poll_interval_ms: int = 50):
        """
        初始化
        
        Args:
            root: Tkinter 根窗口
            poll_interval_ms: 轮询间隔（毫秒）
        """
        self.root = root
        self.poll_interval_ms = poll_interval_ms
        self._queue: queue.Queue[Callable] = queue.Queue()
        self._running = True
        self._start_polling()
    
    def _start_polling(self):
        """开始轮询队列"""
        self._poll()
    
    def _poll(self):
        """处理队列中的回调"""
        if not self._running:
            return
        
        # 处理所有待执行的回调
        processed = 0
        while True:
            try:
                callback = self._queue.get_nowait()
                try:
                    callback()
                except Exception as e:
                    logger.error(f"UI callback error: {e}")
                processed += 1
            except queue.Empty:
                break
        
        # 继续轮询
        self.root.after(self.poll_interval_ms, self._poll)
    
    def call(self, func: Callable, *args, **kwargs) -> None:
        """
        安全调用 UI 函数
        
        Args:
            func: 要调用的函数
            *args: 位置参数
            **kwargs: 关键字参数
        """
        def wrapper():
            func(*args, **kwargs)
        self._queue.put(wrapper)
    
    def stop(self):
        """停止轮询"""
        self._running = False


class CancellationToken:
    """取消操作令牌"""
    
    def __init__(self):
        self._cancelled = False
    
    def cancel(self):
        """请求取消"""
        self._cancelled = True
    
    @property
    def is_cancelled(self) -> bool:
        """是否已取消"""
        return self._cancelled
    
    def reset(self):
        """重置"""
        self._cancelled = False
```

### 4.8 日志系统 (utils/logger.py)

```python
"""日志系统"""
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


def setup_logging(
    log_file: Optional[str] = None,
    level: int = logging.DEBUG,
    console: bool = True
) -> logging.Logger:
    """
    设置日志
    
    Args:
        log_file: 日志文件路径
        level: 日志级别
        console: 是否输出到控制台
    
    Returns:
        根日志器
    """
    # 创建日志器
    root_logger = logging.getLogger("networkfixer")
    root_logger.setLevel(level)
    
    # 日志格式
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # 文件处理器
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(
            log_file,
            encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # 控制台处理器
    if console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    return root_logger


class GUIHandler(logging.Handler):
    """
    GUI 日志处理器
    
    将日志输出到 Tkinter 文本控件
    """
    
    # 日志级别到标签的映射
    LEVEL_TAGS = {
        logging.DEBUG: "info",
        logging.INFO: "info",
        logging.WARNING: "warn",
        logging.ERROR: "error",
        logging.CRITICAL: "error",
    }
    
    def __init__(self, log_callback):
        """
        初始化
        
        Args:
            log_callback: 日志回调函数 log(text, level)
        """
        super().__init__()
        self.log_callback = log_callback
    
    def emit(self, record: logging.LogRecord):
        """输出日志记录"""
        try:
            msg = self.format(record)
            tag = self.LEVEL_TAGS.get(record.levelno, "info")
            self.log_callback(msg, tag)
        except Exception:
            self.handleError(record)
```

### 4.9 国际化模块 (i18n/base.py)

```python
"""国际化框架"""
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


# 翻译字典缓存
_translations: Dict[str, Dict[str, str]] = {}


def register_translations(lang: str, translations: Dict[str, str]):
    """
    注册翻译
    
    Args:
        lang: 语言代码 (如 zh_CN, en_US)
        translations: 翻译字典
    """
    _translations[lang] = translations
    logger.debug(f"Registered translations for {lang}")


def t(key: str, lang: str = "zh_CN", **kwargs) -> str:
    """
    获取翻译文本
    
    Args:
        key: 翻译键
        lang: 语言代码
        **kwargs: 格式化参数
    
    Returns:
        翻译后的文本
    """
    lang_dict = _translations.get(lang, {})
    text = lang_dict.get(key, key)
    
    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError:
            pass
    
    return text


def get_available_languages() -> list:
    """获取可用语言列表"""
    return list(_translations.keys())


def detect_system_language() -> str:
    """
    检测系统语言
    
    Returns:
        语言代码
    """
    import locale
    
    try:
        lang = locale.getdefaultlocale()[0]
        if lang:
            # 转换为我们的格式
            lang = lang.replace("-", "_")
            if lang in _translations:
                return lang
            # 尝试主语言
            main_lang = lang.split("_")[0]
            for available in _translations:
                if available.startswith(main_lang):
                    return available
    except Exception:
        pass
    
    return "zh_CN"  # 默认中文
```

### 4.10 中文翻译 (i18n/zh_CN.py)

```python
"""中文翻译"""
from .base import register_translations

TRANSLATIONS = {
    # 应用信息
    "app.title": "网络修复工具",
    "app.version": "v{version}",
    "app.description": "VPN/代理后网络修复工具",
    
    # 窗口标题
    "window.main": "网络连接修复（VPN/代理后常用）",
    
    # 操作区
    "section.options": "修复选项",
    "section.adapters": "网卡选择（重启网卡时使用）",
    "section.log": "执行日志与结果",
    
    # 选项
    "option.disable_proxy": "关闭系统代理",
    "option.flush_dns": "刷新DNS缓存",
    "option.reset_winsock": "重置Winsock",
    "option.reset_ip": "重置IP地址",
    "option.reset_tcpip": "重置TCP/IP协议栈",
    "option.restart_adapter": "重启指定网卡",
    
    # 按钮
    "btn.fix": "开始修复",
    "btn.test": "仅连通性测试",
    "btn.refresh_adapters": "刷新网卡列表",
    "btn.export_log": "导出日志",
    "btn.cancel": "取消",
    
    # 步骤标题
    "step.disable_proxy": "关闭系统代理",
    "step.flush_dns": "刷新 DNS 缓存",
    "step.reset_winsock": "重置 Winsock",
    "step.reset_ip": "重置 IP 地址",
    "step.reset_tcpip": "重置 TCP/IP 协议栈",
    "step.restart_adapter": "重启网卡",
    "step.test_connectivity": "连通性测试",
    
    # 状态
    "status.ready": "就绪",
    "status.fixing": "正在修复...",
    "status.testing": "正在测试...",
    "status.cancelled": "已取消",
    "status.done": "修复完成！请尝试上网。",
    "status.error": "发生错误: {error}",
    
    # 进度
    "progress.step": "[{current}/{total}] 正在{action}...",
    
    # 日志前缀
    "log.info": "[INFO]",
    "log.warn": "[WARN]",
    "log.error": "[ERROR]",
    "log.success": "[OK]",
    
    # 结果
    "result.success": "成功",
    "result.failed": "失败",
    "result.ping_ok": "{target}：可达",
    "result.ping_fail": "{target}：不可达",
    "result.http_ok": "HTTP 检测：可用",
    "result.http_fail": "HTTP 检测：不可用",
    
    # 网卡
    "adapter.detected": "已检测到网卡 {count} 个",
    "adapter.selected": "当前选择：{name}",
    "adapter.none": "未检测到网卡",
    "adapter.invalid_name": "无效的网卡名称",
    
    # 代理
    "proxy.status": "当前系统代理：{status}，服务器：{server}",
    "proxy.enabled": "开启",
    "proxy.disabled": "关闭",
    "proxy.no_server": "（无）",
    
    # 消息框
    "msg.fix_done.title": "成功",
    "msg.fix_done.content": "网络修复完成！\n建议重启浏览器或相关应用。",
    "msg.fix_error.title": "错误",
    "msg.fix_error.content": "修复过程中出错: {error}",
    "msg.no_selection.title": "提示",
    "msg.no_selection.content": "未勾选任何修复选项，是否仅进行连通性测试？",
    "msg.export_done.title": "已导出",
    "msg.export_done.content": "日志已保存到：\n{path}",
    "msg.export_error.title": "导出失败",
    "msg.export_error.content": "无法写入文件：{error}",
    
    # 提示
    "tips.line1": "使用指引：",
    "tips.line2": "1) 以管理员身份运行（已自动尝试提权）；",
    "tips.line3": "2) 断开 VPN/代理后再修复；",
    "tips.line4": "3) 勾选所需步骤后开始修复，完成后可单独运行连通性测试；",
    "tips.line5": "4) 如仍异常，尝试重启路由器/电脑或联系网络管理员。",
    
    # 权限
    "admin.required.title": "需要管理员权限",
    "admin.required.content": (
        "本工具需要管理员权限以修改网络配置。即将请求权限，请选择"是"。\n\n"
        "如果未弹出窗口，请右键以管理员身份运行，或在命令行执行：\n"
        "powershell -Command \"Start-Process python fix_network.py -Verb runAs\""
    ),
    "admin.failed.title": "启动失败",
    "admin.failed.content": (
        "无法自动获取管理员权限，已退出。\n"
        "请右键以管理员身份运行，或在命令行使用 Start-Process 提权后再试。"
    ),
    
    # 欢迎消息
    "welcome.line1": "欢迎使用网络修复工具！",
    "welcome.line2": "勾选需要的操作后点击开始修复；也可单独运行连通性测试。",
    "welcome.line3": "提示：操作会修改网络配置，需管理员权限；代理/VPN 关闭后效果更佳。",
    
    # 警告
    "warn.no_selection": "未勾选任何操作，已取消。",
    "warn.adapter_not_selected": "已勾选重启网卡，但未选择网卡，已跳过。",
}

register_translations("zh_CN", TRANSLATIONS)
```

### 4.11 英文翻译 (i18n/en_US.py)

```python
"""English Translations"""
from .base import register_translations

TRANSLATIONS = {
    # App info
    "app.title": "Network Fixer",
    "app.version": "v{version}",
    "app.description": "Network repair tool for VPN/Proxy issues",
    
    # Window titles
    "window.main": "Network Connection Repair (Common after VPN/Proxy)",
    
    # Sections
    "section.options": "Repair Options",
    "section.adapters": "Adapter Selection (for restarting adapter)",
    "section.log": "Execution Log & Results",
    
    # Options
    "option.disable_proxy": "Disable System Proxy",
    "option.flush_dns": "Flush DNS Cache",
    "option.reset_winsock": "Reset Winsock",
    "option.reset_ip": "Reset IP Address",
    "option.reset_tcpip": "Reset TCP/IP Stack",
    "option.restart_adapter": "Restart Selected Adapter",
    
    # Buttons
    "btn.fix": "Start Repair",
    "btn.test": "Test Connectivity Only",
    "btn.refresh_adapters": "Refresh Adapter List",
    "btn.export_log": "Export Log",
    "btn.cancel": "Cancel",
    
    # Step titles
    "step.disable_proxy": "Disabling system proxy",
    "step.flush_dns": "Flushing DNS cache",
    "step.reset_winsock": "Resetting Winsock",
    "step.reset_ip": "Resetting IP address",
    "step.reset_tcpip": "Resetting TCP/IP stack",
    "step.restart_adapter": "Restarting adapter",
    "step.test_connectivity": "Testing connectivity",
    
    # Status
    "status.ready": "Ready",
    "status.fixing": "Repairing...",
    "status.testing": "Testing...",
    "status.cancelled": "Cancelled",
    "status.done": "Repair complete! Please try browsing.",
    "status.error": "Error occurred: {error}",
    
    # Progress
    "progress.step": "[{current}/{total}] {action}...",
    
    # Log prefixes
    "log.info": "[INFO]",
    "log.warn": "[WARN]",
    "log.error": "[ERROR]",
    "log.success": "[OK]",
    
    # Results
    "result.success": "Success",
    "result.failed": "Failed",
    "result.ping_ok": "{target}: Reachable",
    "result.ping_fail": "{target}: Unreachable",
    "result.http_ok": "HTTP Test: Available",
    "result.http_fail": "HTTP Test: Unavailable",
    
    # Adapters
    "adapter.detected": "Detected {count} adapter(s)",
    "adapter.selected": "Selected: {name}",
    "adapter.none": "No adapters detected",
    "adapter.invalid_name": "Invalid adapter name",
    
    # Proxy
    "proxy.status": "Current proxy: {status}, Server: {server}",
    "proxy.enabled": "Enabled",
    "proxy.disabled": "Disabled",
    "proxy.no_server": "(None)",
    
    # Message boxes
    "msg.fix_done.title": "Success",
    "msg.fix_done.content": "Network repair complete!\nPlease restart your browser or related applications.",
    "msg.fix_error.title": "Error",
    "msg.fix_error.content": "Error during repair: {error}",
    "msg.no_selection.title": "Notice",
    "msg.no_selection.content": "No repair options selected. Run connectivity test only?",
    "msg.export_done.title": "Exported",
    "msg.export_done.content": "Log saved to:\n{path}",
    "msg.export_error.title": "Export Failed",
    "msg.export_error.content": "Cannot write file: {error}",
    
    # Tips
    "tips.line1": "Instructions:",
    "tips.line2": "1) Run as Administrator (auto-elevation will be attempted);",
    "tips.line3": "2) Disconnect VPN/Proxy before repair;",
    "tips.line4": "3) Select desired options and start repair; test connectivity afterward;",
    "tips.line5": "4) If issues persist, try restarting router/computer or contact network admin.",
    
    # Admin
    "admin.required.title": "Administrator Required",
    "admin.required.content": (
        "This tool requires administrator privileges to modify network settings. "
        "Permission request will appear shortly.\n\n"
        "If no window appears, please right-click and 'Run as administrator', "
        "or run in command line:\n"
        "powershell -Command \"Start-Process python fix_network.py -Verb runAs\""
    ),
    "admin.failed.title": "Launch Failed",
    "admin.failed.content": (
        "Failed to obtain administrator privileges.\n"
        "Please right-click and 'Run as administrator'."
    ),
    
    # Welcome
    "welcome.line1": "Welcome to Network Fixer!",
    "welcome.line2": "Select options and click Start Repair, or run connectivity test only.",
    "welcome.line3": "Note: Administrator privileges required; close VPN/Proxy for best results.",
    
    # Warnings
    "warn.no_selection": "No options selected, cancelled.",
    "warn.adapter_not_selected": "Adapter restart selected but no adapter chosen, skipped.",
}

register_translations("en_US", TRANSLATIONS)
```

### 4.12 UI 主程序 (ui/app.py)

```python
"""Tkinter GUI 主程序"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText
import threading
import logging
from typing import Optional, List

from ..core.operations import NetworkOperations
from ..core.adapters import AdapterManager
from ..models.result import StepResult, ConnectivityResult, AppConfig
from ..models.config import get_config
from ..utils.thread import UISafeCaller, CancellationToken
from ..utils.logger import GUIHandler, setup_logging
from ..i18n.base import t, detect_system_language
from ..i18n import zh_CN  # 注册中文翻译
from ..i18n import en_US  # 注册英文翻译

logger = logging.getLogger(__name__)


class NetworkFixerApp:
    """主应用类"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.config = get_config()
        
        # 设置语言
        self.lang = detect_system_language()
        
        # 初始化窗口
        self._setup_window()
        
        # 初始化业务逻辑
        self.operations = NetworkOperations(self.config)
        
        # 线程安全工具
        self.ui_caller = UISafeCaller(root)
        self.cancel_token: Optional[CancellationToken] = None
        
        # 设置日志
        self._setup_logging()
        
        # 创建 UI
        self._setup_styles()
        self._create_widgets()
        
        # 加载网卡列表
        self._refresh_adapters()
        
        # 显示欢迎消息
        self._log(t("welcome.line1", self.lang), "success")
        self._log(t("welcome.line2", self.lang))
        self._log(t("welcome.line3", self.lang))
        self._log("-" * 50)
    
    def _setup_window(self):
        """设置窗口属性"""
        self.root.title(f"{t('app.title', self.lang)} v1.1.0")
        self.root.geometry(f"{self.config.window_width}x{self.config.window_height}")
        self.root.resizable(False, False)
    
    def _setup_logging(self):
        """设置日志系统"""
        if self.config.log_to_file:
            setup_logging(
                log_file=self.config.log_file_name,
                console=False
            )
        
        # GUI 日志处理器
        gui_handler = GUIHandler(self._log)
        gui_handler.setLevel(logging.DEBUG)
        logging.getLogger("networkfixer").addHandler(gui_handler)
    
    def _setup_styles(self):
        """设置样式"""
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        
        style.configure("TButton", font=("Microsoft YaHei", 9), padding=5)
        style.configure("TLabel", font=("Microsoft YaHei", 9))
        style.configure("Header.TLabel", font=("Microsoft YaHei", 12, "bold"))
    
    def _create_widgets(self):
        """创建所有控件"""
        # 标题
        header = ttk.Label(
            self.root,
            text=t("window.main", self.lang),
            style="Header.TLabel"
        )
        header.pack(pady=12)
        
        # 提示文本
        tips_text = (
            f"{t('tips.line1', self.lang)}\n"
            f"{t('tips.line2', self.lang)}\n"
            f"{t('tips.line3', self.lang)}\n"
            f"{t('tips.line4', self.lang)}\n"
            f"{t('tips.line5', self.lang)}"
        )
        ttk.Label(
            self.root,
            text=tips_text,
            justify=tk.LEFT,
            wraplength=510,
            foreground="#444"
        ).pack(fill=tk.X, padx=12)
        
        # 修复选项区
        self._create_options_frame()
        
        # 网卡选择区
        self._create_adapter_frame()
        
        # 按钮区
        self._create_buttons_frame()
        
        # 状态和进度
        self._create_status_frame()
        
        # 日志区
        self._create_log_frame()
    
    def _create_options_frame(self):
        """创建选项区"""
        frame = ttk.LabelFrame(self.root, text=t("section.options", self.lang))
        frame.pack(fill=tk.X, padx=12, pady=8)
        
        # 选项变量
        self.var_proxy = tk.BooleanVar(value=True)
        self.var_dns = tk.BooleanVar(value=True)
        self.var_winsock = tk.BooleanVar(value=True)
        self.var_ip = tk.BooleanVar(value=True)
        self.var_tcpip = tk.BooleanVar(value=False)
        self.var_adapter = tk.BooleanVar(value=False)
        
        # 选项控件
        ttk.Checkbutton(
            frame, text=t("option.disable_proxy", self.lang),
            variable=self.var_proxy
        ).grid(row=0, column=0, sticky=tk.W, padx=8, pady=6)
        
        ttk.Checkbutton(
            frame, text=t("option.flush_dns", self.lang),
            variable=self.var_dns
        ).grid(row=0, column=1, sticky=tk.W, padx=8, pady=6)
        
        ttk.Checkbutton(
            frame, text=t("option.reset_winsock", self.lang),
            variable=self.var_winsock
        ).grid(row=1, column=0, sticky=tk.W, padx=8, pady=6)
        
        ttk.Checkbutton(
            frame, text=t("option.reset_ip", self.lang),
            variable=self.var_ip
        ).grid(row=1, column=1, sticky=tk.W, padx=8, pady=6)
        
        ttk.Checkbutton(
            frame, text=t("option.reset_tcpip", self.lang),
            variable=self.var_tcpip
        ).grid(row=2, column=0, sticky=tk.W, padx=8, pady=6)
        
        ttk.Checkbutton(
            frame, text=t("option.restart_adapter", self.lang),
            variable=self.var_adapter
        ).grid(row=2, column=1, sticky=tk.W, padx=8, pady=6)
    
    def _create_adapter_frame(self):
        """创建网卡选择区"""
        frame = ttk.LabelFrame(
            self.root,
            text=t("section.adapters", self.lang)
        )
        frame.pack(fill=tk.X, padx=12, pady=8)
        
        ttk.Label(
            frame,
            text=t("adapter.selected", self.lang).replace("{name}", "")
        ).grid(row=0, column=0, padx=8, pady=6, sticky=tk.W)
        
        self.adapter_var = tk.StringVar(value="")
        self.combo_adapter = ttk.Combobox(
            frame,
            textvariable=self.adapter_var,
            state="readonly",
            width=32
        )
        self.combo_adapter.grid(row=0, column=1, padx=8, pady=6, sticky=tk.W)
    
    def _create_buttons_frame(self):
        """创建按钮区"""
        frame = ttk.Frame(self.root)
        frame.pack(fill=tk.X, padx=12, pady=6)
        
        self.btn_fix = ttk.Button(
            frame,
            text=t("btn.fix", self.lang),
            width=18,
            command=self._start_fix
        )
        self.btn_fix.pack(side=tk.LEFT, padx=4)
        
        self.btn_test = ttk.Button(
            frame,
            text=t("btn.test", self.lang),
            width=18,
            command=self._start_test
        )
        self.btn_test.pack(side=tk.LEFT, padx=4)
        
        self.btn_refresh = ttk.Button(
            frame,
            text=t("btn.refresh_adapters", self.lang),
            width=18,
            command=self._refresh_adapters
        )
        self.btn_refresh.pack(side=tk.LEFT, padx=4)
        
        self.btn_export = ttk.Button(
            frame,
            text=t("btn.export_log", self.lang),
            width=12,
            command=self._export_log
        )
        self.btn_export.pack(side=tk.RIGHT, padx=4)
    
    def _create_status_frame(self):
        """创建状态和进度区"""
        self.status_label = ttk.Label(
            self.root,
            text=t("status.ready", self.lang),
            font=("Microsoft YaHei", 9)
        )
        self.status_label.pack(padx=12, pady=4, anchor=tk.W)
        
        self.progress = ttk.Progressbar(self.root, mode="determinate")
        self.progress.pack(fill=tk.X, padx=12, pady=4)
    
    def _create_log_frame(self):
        """创建日志区"""
        frame = ttk.LabelFrame(
            self.root,
            text=t("section.log", self.lang)
        )
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        
        self.log_text = ScrolledText(
            frame,
            height=12,
            font=("Consolas", 10)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        
        # 日志着色
        self.log_text.tag_config("info", foreground="#1f1f1f")
        self.log_text.tag_config("success", foreground="#2d7a1f")
        self.log_text.tag_config("warn", foreground="#a65d00")
        self.log_text.tag_config("error", foreground="#b00020")
    
    # ========== UI 操作 ==========
    
    def _log(self, text: str, level: str = "info"):
        """添加日志（线程安全）"""
        prefix_map = {
            "info": t("log.info", self.lang),
            "warn": t("log.warn", self.lang),
            "error": t("log.error", self.lang),
            "success": t("log.success", self.lang),
        }
        line = f"{prefix_map.get(level, '[INFO]')} {text}"
        
        # 确保在主线程执行
        self.ui_caller.call(self._insert_log, line, level)
    
    def _insert_log(self, line: str, level: str):
        """插入日志文本（必须在主线程）"""
        self.log_text.insert(tk.END, line + "\n", level)
        self.log_text.see(tk.END)
    
    def _set_status(self, text: str, color: str = "black"):
        """设置状态文本（线程安全）"""
        self.ui_caller.call(
            lambda: self.status_label.config(text=text, foreground=color)
        )
    
    def _set_progress(self, value: float):
        """设置进度（线程安全）"""
        self.ui_caller.call(lambda: self.progress.config(value=value))
    
    def _refresh_adapters(self):
        """刷新网卡列表"""
        adapters = self.operations.refresh_adapters(force=True)
        self.combo_adapter.config(values=adapters)
        
        if adapters:
            self.combo_adapter.current(0)
            self._log(t("adapter.detected", self.lang, count=len(adapters)))
        else:
            self._log(t("adapter.none", self.lang), "warn")
    
    def _export_log(self):
        """导出日志"""
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            title=t("btn.export_log", self.lang)
        )
        
        if not path:
            return
        
        try:
            content = self.log_text.get("1.0", tk.END)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo(
                t("msg.export_done.title", self.lang),
                t("msg.export_done.content", self.lang, path=path)
            )
        except Exception as e:
            messagebox.showerror(
                t("msg.export_error.title", self.lang),
                t("msg.export_error.content", self.lang, error=str(e))
            )
    
    # ========== 修复操作 ==========
    
    def _start_fix(self):
        """开始修复"""
        steps = self.operations.build_steps(
            do_proxy=self.var_proxy.get(),
            do_dns=self.var_dns.get(),
            do_winsock=self.var_winsock.get(),
            do_ip=self.var_ip.get(),
            do_tcpip=self.var_tcpip.get(),
            do_adapter=self.var_adapter.get(),
            adapter_name=self.adapter_var.get()
        )
        
        if not steps:
            result = messagebox.askyesno(
                t("msg.no_selection.title", self.lang),
                t("msg.no_selection.content", self.lang)
            )
            if result:
                self._start_test()
            return
        
        # 禁用按钮
        self.btn_fix.config(state=tk.DISABLED)
        self.btn_test.config(state=tk.DISABLED)
        
        # 创建取消令牌
        self.cancel_token = CancellationToken()
        
        # 启动后台线程
        thread = threading.Thread(
            target=self._fix_thread,
            args=(steps,),
            daemon=True
        )
        thread.start()
    
    def _fix_thread(self, steps):
        """修复线程（后台执行）"""
        try:
            # 显示代理状态
            enabled, server = self.operations.get_proxy_status()
            status = t("proxy.enabled", self.lang) if enabled else t("proxy.disabled", self.lang)
            server = server or t("proxy.no_server", self.lang)
            self._log(t("proxy.status", self.lang, status=status, server=server))
            
            # 进度回调
            def progress_callback(current, total, title_key):
                title = t(title_key, self.lang)
                self._set_status(
                    t("progress.step", self.lang, current=current, total=total, action=title),
                    "#0057b7"
                )
                progress = (current / (total + 1)) * 100
                self._set_progress(progress)
            
            # 取消检查
            def cancel_check():
                return self.cancel_token.is_cancelled
            
            # 执行步骤
            results = self.operations.execute_steps(
                steps,
                progress_callback=progress_callback,
                cancel_check=cancel_check
            )
            
            # 检查是否取消
            if self.cancel_token.is_cancelled:
                self._set_status(t("status.cancelled", self.lang), "orange")
                return
            
            # 连通性测试
            self._set_status(t("step.test_connectivity", self.lang), "#4b8b3b")
            conn = self.operations.test_connectivity()
            
            # 显示测试结果
            self._log(
                f"114DNS: {t('result.ping_ok' if conn.ping_114 else 'result.ping_fail', self.lang, target='114')}",
                "success" if conn.ping_114 else "error"
            )
            self._log(
                f"8.8.8.8: {t('result.ping_ok' if conn.ping_google else 'result.ping_fail', self.lang, target='8.8.8.8')}",
                "success" if conn.ping_google else "error"
            )
            self._log(
                t("result.http_ok" if conn.http_test else "result.http_fail", self.lang),
                "success" if conn.http_test else "error"
            )
            
            # 完成
            self._set_progress(100)
            self._set_status(t("status.done", self.lang), "#4b8b3b")
            
            # 显示成功消息（在主线程）
            self.ui_caller.call(
                lambda: messagebox.showinfo(
                    t("msg.fix_done.title", self.lang),
                    t("msg.fix_done.content", self.lang)
                )
            )
            
        except Exception as e:
            logger.exception("Fix failed")
            self._set_status(t("status.error", self.lang, error=str(e)), "red")
            self.ui_caller.call(
                lambda e=e: messagebox.showerror(
                    t("msg.fix_error.title", self.lang),
                    t("msg.fix_error.content", self.lang, error=str(e))
                )
            )
        
        finally:
            # 重新启用按钮
            self.ui_caller.call(lambda: self.btn_fix.config(state=tk.NORMAL))
            self.ui_caller.call(lambda: self.btn_test.config(state=tk.NORMAL))
    
    def _start_test(self):
        """开始连通性测试"""
        self.btn_fix.config(state=tk.DISABLED)
        self.btn_test.config(state=tk.DISABLED)
        
        thread = threading.Thread(target=self._test_thread, daemon=True)
        thread.start()
    
    def _test_thread(self):
        """测试线程"""
        try:
            self._set_status(t("status.testing", self.lang), "#4b8b3b")
            self._log("-" * 50)
            self._log(t("status.testing", self.lang))
            
            conn = self.operations.test_connectivity()
            
            self._log(
                f"114DNS: {t('result.ping_ok' if conn.ping_114 else 'result.ping_fail', self.lang, target='114')}",
                "success" if conn.ping_114 else "error"
            )
            self._log(
                f"8.8.8.8: {t('result.ping_ok' if conn.ping_google else 'result.ping_fail', self.lang, target='8.8.8.8')}",
                "success" if conn.ping_google else "error"
            )
            self._log(
                t("result.http_ok" if conn.http_test else "result.http_fail", self.lang),
                "success" if conn.http_test else "error"
            )
            
            self._set_status(t("status.done", self.lang), "#4b8b3b")
            
        except Exception as e:
            logger.exception("Test failed")
            self._set_status(t("status.error", self.lang, error=str(e)), "red")
        
        finally:
            self.ui_caller.call(lambda: self.btn_fix.config(state=tk.NORMAL))
            self.ui_caller.call(lambda: self.btn_test.config(state=tk.NORMAL))
```

### 4.13 入口文件 (fix_network.py)

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NetworkFixer - Windows Network Repair Tool
Entry point with privilege elevation
"""
import ctypes
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))


def is_admin() -> bool:
    """
    检查是否以管理员权限运行
    
    Returns:
        是否有管理员权限
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except (AttributeError, OSError) as e:
        # 记录错误以便调试
        import logging
        logging.debug(f"Admin check failed: {e}")
        return False


def run_as_admin():
    """
    请求管理员权限重新运行
    """
    # 获取目标程序和参数
    if getattr(sys, "frozen", False):
        # 打包后的 exe
        target = sys.executable
        params = " ".join(_quote_arg(p) for p in sys.argv[1:])
    else:
        # Python 脚本
        target = sys.executable
        script_path = os.path.abspath(sys.argv[0])
        params = " ".join([_quote_arg(script_path)] + [_quote_arg(p) for p in sys.argv[1:]])
    
    # 显示提示
    from networkfixer.i18n.base import t
    from networkfixer.i18n import zh_CN, en_US
    lang = "zh_CN"  # 默认中文
    
    ctypes.windll.user32.MessageBoxW(
        None,
        t("admin.required.content", lang),
        t("admin.required.title", lang),
        0x40
    )
    
    # 请求提权
    ret = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", target, params, None, 1
    )
    
    if ret <= 32:
        ctypes.windll.user32.MessageBoxW(
            None,
            t("admin.failed.content", lang),
            t("admin.failed.title", lang),
            0x10
        )
    
    sys.exit()


def _quote_arg(arg: str) -> str:
    """
    安全引用参数
    
    Args:
        arg: 命令行参数
    
    Returns:
        引用后的参数
    """
    if any(ch in arg for ch in [' ', '\t', '"']):
        return '"' + arg.replace('"', '\\"') + '"'
    return arg


def main():
    """主函数"""
    # 检查管理员权限
    if not is_admin():
        run_as_admin()
        return
    
    # 初始化日志
    from networkfixer.utils.logger import setup_logging
    setup_logging(console=False)
    
    # 启动 GUI
    import tkinter as tk
    from networkfixer.ui.app import NetworkFixerApp
    
    root = tk.Tk()
    app = NetworkFixerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
```

---

## 五、测试策略

### 5.1 单元测试

```python
# tests/test_executor.py
"""命令执行器测试"""
import pytest
from unittest.mock import patch, MagicMock
from networkfixer.core.executor import CommandExecutor
from networkfixer.models.result import StepResult


class TestCommandExecutor:
    
    def test_run_simple_command(self):
        """测试简单命令"""
        executor = CommandExecutor()
        result = executor.run(["echo", "test"])
        assert result.ok
        assert "test" in result.output
    
    def test_run_failed_command(self):
        """测试失败命令"""
        executor = CommandExecutor()
        result = executor.run(["cmd", "/c", "exit", "1"])
        assert not result.ok
    
    def test_run_chain_success(self):
        """测试链式命令成功"""
        executor = CommandExecutor()
        result = executor.run_chain([
            ["echo", "first"],
            ["echo", "second"]
        ])
        assert result.ok
        assert "second" in result.output
    
    def test_run_chain_stops_on_failure(self):
        """测试链式命令在失败时停止"""
        executor = CommandExecutor()
        result = executor.run_chain([
            ["cmd", "/c", "exit", "1"],
            ["echo", "should not run"]
        ])
        assert not result.ok
    
    def test_decode_output_mbcs(self):
        """测试 mbcs 编码解码"""
        # 模拟 Windows 中文输出
        data = "测试输出".encode('gbk')
        output = CommandExecutor._decode_output(data)
        assert "测试" in output or "输出" in output


# tests/test_adapters.py
"""网卡管理测试"""
import pytest
from networkfixer.core.adapters import AdapterManager


class TestAdapterManager:
    
    def test_parse_output_english(self):
        """测试英文系统输出解析"""
        output = """
Admin State    Type          Interface Name
-----------------------------------------
Enabled        Dedicated     Ethernet
Enabled        Dedicated     Wi-Fi
Disabled       Dedicated     Bluetooth Network Connection
"""
        names = AdapterManager._parse_output(output)
        assert "Ethernet" in names
        assert "Wi-Fi" in names
        assert "Bluetooth Network Connection" in names
    
    def test_parse_output_chinese(self):
        """测试中文系统输出解析"""
        output = """
管理员状态    类型          接口名称
-----------------------------------------
已启用        专用          以太网
已启用        专用          WLAN
"""
        names = AdapterManager._parse_output(output)
        assert "以太网" in names
        assert "WLAN" in names
    
    def test_validate_name_safe(self):
        """测试安全的网卡名称"""
        assert AdapterManager.validate_name("Ethernet")
        assert AdapterManager.validate_name("Wi-Fi")
        assert AdapterManager.validate_name("Local Area Connection 2")
    
    def test_validate_name_dangerous(self):
        """测试危险的网卡名称"""
        assert not AdapterManager.validate_name("Test\"Adapter")
        assert not AdapterManager.validate_name("Test&Adapter")
        assert not AdapterManager.validate_name("Test;Adapter")


# tests/test_connectivity.py
"""连通性测试"""
import pytest
from unittest.mock import patch, MagicMock
from networkfixer.core.connectivity import ConnectivityTester


class TestConnectivityTester:
    
    @patch('networkfixer.core.connectivity.get_executor')
    def test_ping_success(self, mock_get_executor):
        """测试 ping 成功"""
        mock_executor = MagicMock()
        mock_executor.run.return_value = MagicMock(
            ok=True, return_code=0
        )
        mock_get_executor.return_value = mock_executor
        
        tester = ConnectivityTester()
        result = tester._ping("8.8.8.8")
        
        assert result is True
        mock_executor.run.assert_called_once()
    
    @patch('networkfixer.core.connectivity.urllib.request.urlopen')
    def test_http_success(self, mock_urlopen):
        """测试 HTTP 成功"""
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        tester = ConnectivityTester()
        result = tester._http_test()
        
        assert result is True


# tests/test_i18n.py
"""国际化测试"""
import pytest
from networkfixer.i18n.base import t, detect_system_language
from networkfixer.i18n import zh_CN, en_US


class TestI18n:
    
    def test_chinese_translation(self):
        """测试中文翻译"""
        text = t("app.title", "zh_CN")
        assert text == "网络修复工具"
    
    def test_english_translation(self):
        """测试英文翻译"""
        text = t("app.title", "en_US")
        assert text == "Network Fixer"
    
    def test_format_with_kwargs(self):
        """测试带参数的翻译"""
        text = t("adapter.detected", "zh_CN", count=3)
        assert "3" in text
        assert "网卡" in text
    
    def test_fallback_to_key(self):
        """测试未知键回退"""
        text = t("unknown.key", "zh_CN")
        assert text == "unknown.key"
```

### 5.2 开发依赖 (requirements-dev.txt)

```
# Testing
pytest>=7.0.0
pytest-cov>=4.0.0

# Type checking
mypy>=1.0.0

# Linting
ruff>=0.1.0

# Building
pyinstaller>=6.0.0
```

---

## 六、CI/CD 配置

> 调整说明：CI/CD 作为“稳定后增强项”，不阻塞前两阶段交付；优先确保本地可重复测试通过。[^4]

### 6.1 GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt
      
      - name: Run linting
        run: ruff check networkfixer/ tests/
      
      - name: Run type checking
        run: mypy networkfixer/
      
      - name: Run tests
        run: pytest tests/ -v --cov=networkfixer --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

  build:
    needs: test
    runs-on: windows-latest
    if: startsWith(github.ref, 'refs/tags/')
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install PyInstaller
        run: pip install pyinstaller
      
      - name: Build executable
        run: pyinstaller NetworkFixer.spec
      
      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: NetworkFixer
          path: dist/NetworkFixer.exe

  release:
    needs: build
    runs-on: ubuntu-latest
    if: startsWith(github.ref, 'refs/tags/')
    steps:
      - name: Download artifact
        uses: actions/download-artifact@v4
        with:
          name: NetworkFixer
          path: dist/
      
      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          files: dist/NetworkFixer.exe
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## 七、执行计划

### 7.1 阶段划分

| 阶段 | 目标 | 预计时间 | 交付物 |
|------|------|----------|--------|
| **阶段1** | P0 修复与回归验证 | 1-2天 | 线程安全、命令执行安全、异常处理修复 + 冒烟验证清单 |
| **阶段2** | 模块拆分（最小可运行） | 2-3天 | 新目录结构、核心模块迁移、入口兼容 |
| **阶段3** | 国际化与文档对齐 | 1天 | 中英文翻译、语言检测、README 补充 |
| **阶段4** | 测试基线与静态检查 | 1天 | 单元测试骨架、pytest/ruff/mypy 本地可运行 |
| **阶段5** | 打包与 CI/CD 增强 | 1天 | PyInstaller spec、可选 GitHub Actions 流水线 |

### 7.2 详细任务清单

#### 阶段1: P0 修复

- [ ] 1.1 创建 `utils/thread.py` 实现 `UISafeCaller`
- [ ] 1.2 创建 `core/executor.py` 实现安全命令执行
- [ ] 1.3 修复 `socket.setdefaulttimeout` 使用局部超时
- [ ] 1.4 修复 `is_admin()` 的裸露 except
- [ ] 1.5 验证修复后的稳定性

#### 阶段2: 模块拆分

- [ ] 2.1 创建新目录结构
- [ ] 2.2 创建 `models/result.py` 数据结构
- [ ] 2.3 创建 `core/registry.py` 注册表操作
- [ ] 2.4 创建 `core/adapters.py` 网卡管理
- [ ] 2.5 创建 `core/connectivity.py` 连通性测试
- [ ] 2.6 创建 `core/operations.py` 业务逻辑
- [ ] 2.7 创建 `ui/app.py` GUI 层
- [ ] 2.8 更新入口文件 `fix_network.py`
- [ ] 2.9 为所有模块添加类型注解

#### 阶段3: 国际化

- [ ] 3.1 创建 `i18n/base.py` 翻译框架
- [ ] 3.2 创建 `i18n/zh_CN.py` 中文翻译
- [ ] 3.3 创建 `i18n/en_US.py` 英文翻译
- [ ] 3.4 实现系统语言检测
- [ ] 3.5 更新 UI 使用翻译

#### 阶段4: 测试覆盖

- [ ] 4.1 创建测试目录结构
- [ ] 4.2 编写 `test_executor.py`
- [ ] 4.3 编写 `test_adapters.py`
- [ ] 4.4 编写 `test_connectivity.py`
- [ ] 4.5 编写 `test_i18n.py`
- [ ] 4.6 配置 pytest
- [ ] 4.7 创建 `pyproject.toml`

#### 阶段5: 打包优化

- [ ] 5.1 创建 `NetworkFixer.spec`
- [ ] 5.2 创建 UAC manifest
- [ ] 5.3 配置 GitHub Actions CI
- [ ] 5.4 配置 GitHub Actions Release
- [ ] 5.5 更新 README

### 7.3 里程碑验收门槛（新增）

- **M1（阶段1结束）**：默认修复路径可完整执行，且 GUI 不出现线程相关异常弹窗/卡死。[^1]
- **M2（阶段2结束）**：主流程已迁移到新包结构，`fix_network.py` 仅保留入口与提权编排。
- **M3（阶段4结束）**：关键模块具备最小单元测试，至少覆盖命令执行、网卡解析、连通性测试。
- **M4（阶段5结束）**：可稳定生成可执行文件，且文档与实际运行方式一致。[^4]

---

## 八、风险评估

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| 线程安全修复引入新 bug | 中 | 高 | 充分测试、代码审查 |
| 网卡解析在不同 Windows 版本失败 | 中 | 中 | 添加单元测试、收集用户反馈 |
| 打包后体积过大 | 低 | 低 | 使用 --onedir 或压缩 |
| 用户不适应新版 UI | 低 | 低 | 保持界面布局一致 |
| 管理员提权被系统策略拦截 | 中 | 中 | 保留失败提示与手动提权指引 |
| 重构期间行为偏离当前文档 | 中 | 中 | 每阶段结束同步 README/CHANGELOG 与回归清单 |

---

## 九、附录

### A. PyInstaller Spec 文件

```python
# NetworkFixer.spec
# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['fix_network.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'networkfixer',
        'networkfixer.core',
        'networkfixer.ui',
        'networkfixer.i18n',
        'networkfixer.i18n.zh_CN',
        'networkfixer.i18n.en_US',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='NetworkFixer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,  # 请求管理员权限
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='NetworkFixer',
)
```

### B. pyproject.toml

```toml
[project]
name = "networkfixer"
version = "2.0.0"
description = "Windows network repair tool for VPN/Proxy issues"
readme = "README.md"
requires-python = ">=3.8"
license = {text = "MIT"}
authors = [
    {name = "HYGUO1993"}
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Environment :: Win32 (MS Windows)",
    "Intended Audience :: End Users/Desktop",
    "License :: OSI Approved :: MIT License",
    "Operating System :: Microsoft :: Windows",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "mypy>=1.0.0",
    "ruff>=0.1.0",
]
build = [
    "pyinstaller>=6.0.0",
]

[tool.ruff]
line-length = 100
target-version = "py38"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "C4"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --tb=short"
```

---

**文档结束**

---

## 脚注

[^1]: 依据当前实现，`fix_network_logic()` 与 `connectivity_only()` 由后台线程直接更新 Tk 组件，存在典型 Tkinter 线程安全风险。
[^2]: 当前 `fix_network.py` 总行数为 450 行，且内容处于持续迭代中，固定行号会快速失效。
[^3]: 本方案包含大规模目录拆分、模块迁移、测试与打包配置，按经验属于多阶段改造，不宜以连续 14 小时一次完成。
[^4]: 当前仓库已可通过 `python fix_network.py` 直接运行，建议先确保本地测试基线，再将流程固化到 GitHub Actions。
[^5]: 当前 `requirements.txt` 仅包含 `pyinstaller`，与“运行时保持标准库”目标一致；测试工具应放入开发依赖。

*请其他 AI 审阅此方案，重点关注：*
1. *线程安全方案是否完善*
2. *命令执行安全措施是否足够*
3. *模块划分是否合理*
4. *测试覆盖是否充分*
5. *有任何遗漏或改进建议*
