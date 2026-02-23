#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NetworkFixer - Entry Point

Handles administrator privilege elevation and delegates to networkfixer package.
"""

import ctypes
import sys
import os


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except (AttributeError, OSError):
        return False


def _quote_arg(arg: str) -> str:
    if any(ch in arg for ch in [' ', '\t', '"']):
        return '"' + arg.replace('"', '\\"') + '"'
    return arg


def _elevate_privileges() -> None:
    ctypes.windll.user32.MessageBoxW(
        None,
        "本工具需要管理员权限以修改网络配置。即将请求权限，请选择\"是\"。\n\n"
        "This tool requires administrator privileges to modify network settings. "
        "Permission request will appear shortly.\n\n"
        "如果未弹出窗口，请右键以管理员身份运行，或在命令行执行：\n"
        "powershell -Command \"Start-Process python fix_network.py -Verb runAs\"",
        "需要管理员权限 / Administrator Required",
        0x40
    )

    if getattr(sys, "frozen", False):
        target = sys.executable
        params = " ".join(_quote_arg(p) for p in sys.argv[1:])
    else:
        script_path = os.path.abspath(sys.argv[0])
        target = sys.executable
        params = " ".join([_quote_arg(script_path)] + [_quote_arg(p) for p in sys.argv[1:]])

    ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", target, params, None, 1)

    if ret <= 32:
        ctypes.windll.user32.MessageBoxW(
            None,
            "无法自动获取管理员权限，已退出。\n"
            "请右键以管理员身份运行，或在命令行使用 Start-Process 提权后再试。\n\n"
            "Failed to obtain administrator privileges.\n"
            "Please right-click and 'Run as administrator'.",
            "启动失败 / Launch Failed",
            0x10
        )
    sys.exit()


def _enable_high_dpi_awareness() -> None:
    """启用 Windows 高 DPI 感知，减少高分屏下的界面发糊。"""
    try:
        user32 = ctypes.windll.user32
        shcore = getattr(ctypes.windll, "shcore", None)

        # Windows 10+: Per Monitor v2（最佳）
        # -4 == DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
        try:
            user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
            return
        except Exception:
            pass

        # Windows 8.1+: Per Monitor Aware
        if shcore is not None:
            try:
                # 2 == PROCESS_PER_MONITOR_DPI_AWARE
                shcore.SetProcessDpiAwareness(2)
                return
            except Exception:
                pass

        # Windows Vista+: System DPI Aware（兜底）
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass
    except Exception:
        pass


def _configure_tk_scaling(root) -> None:
    """根据实际 DPI 调整 Tk 缩放，保证文字和控件清晰度。"""
    try:
        dpi = float(root.winfo_fpixels("1i"))
        scaling = dpi / 72.0

        if 1.0 <= scaling <= 4.0:
            root.tk.call("tk", "scaling", scaling)
    except Exception:
        pass


def main() -> None:
    if not is_admin():
        _elevate_privileges()

    _enable_high_dpi_awareness()

    import tkinter as tk
    from networkfixer.ui import NetworkFixerApp

    root = tk.Tk()
    _configure_tk_scaling(root)
    app = NetworkFixerApp(root)

    def on_closing():
        app.cleanup()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
