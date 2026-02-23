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


def main() -> None:
    if not is_admin():
        _elevate_privileges()

    import tkinter as tk
    from networkfixer.ui import NetworkFixerApp

    root = tk.Tk()
    app = NetworkFixerApp(root)

    def on_closing():
        app.cleanup()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
