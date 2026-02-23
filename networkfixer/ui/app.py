# -*- coding: utf-8 -*-
"""NetworkFixer 主界面模块

提供图形用户界面，包括：
- 线程安全的 UI 更新（通过 UISafeCaller）
- 国际化支持（中文/英文）
- 网络修复操作（通过 NetworkOperations）
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText
import threading
import logging
from typing import Optional

from ..utils.thread import UISafeCaller, CancellationToken
from ..utils.admin import is_admin
from ..core.operations import NetworkOperations, Step
from ..models.result import StepResult, ConnectivityResult, AppConfig
from ..models.config import get_config
from ..i18n import t, detect_system_language

logger = logging.getLogger(__name__)

__version__ = "2.0.0"


class NetworkFixerApp:
    """NetworkFixer 主应用类
    
    线程安全设计：所有后台线程的 UI 更新都通过 UISafeCaller
    投递到主线程执行，避免 Tkinter 线程安全问题。
    """

    def __init__(self, root: tk.Tk, config: Optional[AppConfig] = None):
        self.root = root
        self.config = config or get_config()
        # 检测系统语言，默认中文
        self.lang = self.config.language or detect_system_language()

        # 初始化线程安全的 UI 调用器
        self.ui_caller = UISafeCaller(root, poll_interval_ms=50)

        # 取消令牌，用于中断长时间操作
        self.cancel_token: Optional[CancellationToken] = None

        # 业务逻辑处理器
        self.operations = NetworkOperations(self.config)

        # 初始化界面
        self._setup_window()
        self._setup_style()
        self._create_widgets()

        # 显示欢迎信息
        self._log_welcome()

        # 加载网卡列表
        self._refresh_adapters()

    def _setup_window(self) -> None:
        """配置主窗口属性"""
        # 窗口标题：网络修复工具 v2.0.0
        title = f"{t('app.title', self.lang)} {t('app.version', self.lang, version=__version__)}"
        self.root.title(title)
        self.root.geometry(f"{self.config.window_width}x{self.config.window_height}")
        self.root.resizable(False, False)
        self.root.configure(background="#f3f6fb")

    def _setup_style(self) -> None:
        """配置界面样式"""
        style = ttk.Style()
        try:
            style.theme_use("vista")
        except tk.TclError:
            try:
                style.theme_use("clam")
            except tk.TclError:
                pass

        bg_main = "#f3f6fb"
        bg_card = "#ffffff"
        text_primary = "#1f2937"
        accent = "#2563eb"
        accent_active = "#1d4ed8"
        border = "#dbe3ef"

        # 使用微软雅黑字体
        style.configure("TFrame", background=bg_main)
        style.configure("TLabel", font=("Microsoft YaHei", 9), background=bg_main, foreground=text_primary)
        style.configure("Header.TLabel", font=("Microsoft YaHei", 13, "bold"), background=bg_main, foreground="#0f172a")

        style.configure("Card.TLabelframe", background=bg_card, borderwidth=1, relief="solid")
        style.configure("Card.TLabelframe.Label", background=bg_main, foreground="#334155", font=("Microsoft YaHei", 9, "bold"))

        style.configure("TButton", font=("Microsoft YaHei", 9), padding=(10, 6))
        style.configure("Primary.TButton", font=("Microsoft YaHei", 9, "bold"), padding=(12, 7), foreground="#0f172a", background=accent)
        style.map(
            "Primary.TButton",
            background=[("active", accent_active), ("pressed", accent_active)],
            foreground=[("active", "#0f172a"), ("pressed", "#0f172a"), ("disabled", "#94a3b8")]
        )
        style.configure("Secondary.TButton", padding=(10, 6))

        style.configure("TProgressbar", troughcolor="#e2e8f0", background=accent, bordercolor=border, lightcolor=accent, darkcolor=accent)

    def _create_widgets(self) -> None:
        """创建并布局所有界面组件"""
        # 顶部标题与状态徽标
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill=tk.X, padx=12, pady=10)

        header = ttk.Label(
            header_frame,
            text=t("window.main", self.lang),
            style="Header.TLabel"
        )
        header.pack(side=tk.LEFT)

        self.badge_label = tk.Label(
            header_frame,
            text=t("badge.ready", self.lang),
            bg="#dcfce7",
            fg="#166534",
            font=("Microsoft YaHei", 9, "bold"),
            padx=10,
            pady=3,
            bd=0
        )
        self.badge_label.pack(side=tk.RIGHT)

        # 使用提示区域
        self._create_tips_section()

        # 修复选项区域
        self._create_options_section()

        # 网卡选择区域
        self._create_adapter_section()

        # 操作按钮区域
        self._create_button_section()

        # 状态和进度区域
        self._create_status_section()

        # 日志输出区域
        self._create_log_section()

    def _create_tips_section(self) -> None:
        """创建使用提示区域"""
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

    def _create_options_section(self) -> None:
        """创建修复选项区域"""
        frame_ops = ttk.LabelFrame(self.root, text=t("section.options", self.lang), style="Card.TLabelframe")
        frame_ops.pack(fill=tk.X, padx=12, pady=8)

        # 选项变量
        self.var_proxy = tk.BooleanVar(value=True)     # 关闭系统代理
        self.var_dns = tk.BooleanVar(value=True)       # 刷新DNS缓存
        self.var_winsock = tk.BooleanVar(value=True)   # 重置Winsock
        self.var_ip = tk.BooleanVar(value=True)        # 重置IP地址
        self.var_tcpip = tk.BooleanVar(value=False)    # 重置TCP/IP协议栈
        self.var_adapter = tk.BooleanVar(value=False)  # 重启指定网卡

        # 两栏紧凑卡片布局
        options_grid = ttk.Frame(frame_ops)
        options_grid.pack(fill=tk.X, padx=8, pady=6)
        options_grid.columnconfigure(0, weight=1)
        options_grid.columnconfigure(1, weight=1)

        basic_card = ttk.LabelFrame(options_grid, text=t("section.options.basic", self.lang), style="Card.TLabelframe")
        basic_card.grid(row=0, column=0, padx=(0, 6), pady=0, sticky="nsew")

        advanced_card = ttk.LabelFrame(options_grid, text=t("section.options.advanced", self.lang), style="Card.TLabelframe")
        advanced_card.grid(row=0, column=1, padx=(6, 0), pady=0, sticky="nsew")

        # 左列卡片：基础修复
        ttk.Checkbutton(
            basic_card,
            text=t("option.disable_proxy", self.lang),
            variable=self.var_proxy
        ).grid(row=0, column=0, sticky=tk.W, padx=8, pady=4)

        ttk.Checkbutton(
            basic_card,
            text=t("option.flush_dns", self.lang),
            variable=self.var_dns
        ).grid(row=1, column=0, sticky=tk.W, padx=8, pady=4)

        ttk.Checkbutton(
            basic_card,
            text=t("option.reset_winsock", self.lang),
            variable=self.var_winsock
        ).grid(row=2, column=0, sticky=tk.W, padx=8, pady=4)

        # 右列卡片：高级修复
        ttk.Checkbutton(
            advanced_card,
            text=t("option.reset_ip", self.lang),
            variable=self.var_ip
        ).grid(row=0, column=0, sticky=tk.W, padx=8, pady=4)

        ttk.Checkbutton(
            advanced_card,
            text=t("option.reset_tcpip", self.lang),
            variable=self.var_tcpip
        ).grid(row=1, column=0, sticky=tk.W, padx=8, pady=4)

        ttk.Checkbutton(
            advanced_card,
            text=t("option.restart_adapter", self.lang),
            variable=self.var_adapter
        ).grid(row=2, column=0, sticky=tk.W, padx=8, pady=4)

    def _create_adapter_section(self) -> None:
        """创建网卡选择区域"""
        frame_adapter = ttk.LabelFrame(
            self.root,
            text=t("section.adapters", self.lang),
            style="Card.TLabelframe"
        )
        frame_adapter.pack(fill=tk.X, padx=12, pady=8)

        self.adapter_var = tk.StringVar(value="")

        ttk.Label(frame_adapter, text=t("adapter.selected", self.lang, name="")).grid(
            row=0, column=0, padx=8, pady=6, sticky=tk.W
        )

        self.combo_adapter = ttk.Combobox(
            frame_adapter,
            textvariable=self.adapter_var,
            state="readonly",
            width=32
        )
        self.combo_adapter.grid(row=0, column=1, padx=8, pady=6, sticky=tk.W)

    def _create_button_section(self) -> None:
        """创建操作按钮区域"""
        frame_run = ttk.Frame(self.root)
        frame_run.pack(fill=tk.X, padx=12, pady=6)
        frame_run.columnconfigure(0, weight=1)
        frame_run.columnconfigure(1, weight=1)
        frame_run.columnconfigure(2, weight=1)
        frame_run.columnconfigure(3, weight=1)

        # 开始修复按钮
        self.btn_fix = ttk.Button(
            frame_run,
            text=t("btn.fix", self.lang),
            width=12,
            style="Primary.TButton",
            command=self._start_fix_thread
        )
        self.btn_fix.grid(row=0, column=0, padx=4, sticky="ew")

        # 仅连通性测试按钮
        self.btn_test = ttk.Button(
            frame_run,
            text=t("btn.test", self.lang),
            width=12,
            style="Secondary.TButton",
            command=self._start_test_thread
        )
        self.btn_test.grid(row=0, column=1, padx=4, sticky="ew")

        # 刷新网卡列表按钮
        self.btn_refresh = ttk.Button(
            frame_run,
            text=t("btn.refresh_adapters", self.lang),
            width=12,
            style="Secondary.TButton",
            command=self._refresh_adapters
        )
        self.btn_refresh.grid(row=0, column=2, padx=4, sticky="ew")

        # 导出日志按钮
        self.btn_export = ttk.Button(
            frame_run,
            text=t("btn.export_log", self.lang),
            width=12,
            style="Secondary.TButton",
            command=self._export_log
        )
        self.btn_export.grid(row=0, column=3, padx=4, sticky="ew")

    def _create_status_section(self) -> None:
        """创建状态和进度区域"""
        # 状态标签
        self.status_label = ttk.Label(
            self.root,
            text=t("status.ready", self.lang),
            font=("Microsoft YaHei", 9)
        )
        self.status_label.pack(padx=12, pady=4, anchor=tk.W)
        self._set_top_badge("ready")

        # 进度条
        self.progress = ttk.Progressbar(self.root, mode="determinate")
        self.progress.pack(fill=tk.X, padx=12, pady=4)

    def _create_log_section(self) -> None:
        """创建日志输出区域"""
        frame_log = ttk.LabelFrame(self.root, text=t("section.log", self.lang), style="Card.TLabelframe")
        frame_log.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        self.log_text = ScrolledText(
            frame_log,
            height=12,
            font=("Consolas", 10)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.log_text.configure(
            background="#0f172a",
            foreground="#e2e8f0",
            insertbackground="#e2e8f0",
            selectbackground="#334155",
            relief="flat",
            bd=0
        )

        # 配置日志标签颜色
        self.log_text.tag_config("info", foreground="#cbd5e1")       # 普通信息：浅灰
        self.log_text.tag_config("success", foreground="#86efac")    # 成功：浅绿
        self.log_text.tag_config("warn", foreground="#fdba74")       # 警告：橙色
        self.log_text.tag_config("error", foreground="#fca5a5")      # 错误：浅红

    def _log_welcome(self) -> None:
        """显示欢迎信息"""
        self.log(t("welcome.line1", self.lang), "success")
        self.log(t("welcome.line2", self.lang))
        self.log(t("welcome.line3", self.lang))
        self.log("-" * 50)

    def log(self, text: str, level: str = "info") -> None:
        """写入日志消息
        
        参数:
            text: 日志文本
            level: 日志级别 (info, success, warn, error)
        """
        prefix_map = {
            "info": t("log.info", self.lang),
            "warn": t("log.warn", self.lang),
            "error": t("log.error", self.lang),
            "success": t("log.success", self.lang),
        }
        line = f"{prefix_map.get(level, t('log.info', self.lang))} {text}"
        self.log_text.insert(tk.END, line + "\n", level)
        self.log_text.see(tk.END)

    def log_safe(self, text: str, level: str = "info") -> None:
        """线程安全的日志写入方法（通过 UISafeCaller）
        
        参数:
            text: 日志文本
            level: 日志级别 (info, success, warn, error)
        """
        self.ui_caller.call(self.log, text, level)

    def _set_status(self, text: str, color: str = "black") -> None:
        """更新状态标签（线程安全）"""
        self.ui_caller.call(
            lambda: self.status_label.config(text=text, foreground=color)
        )

        if color == "red":
            self._set_top_badge("error")
        elif color == "orange":
            self._set_top_badge("cancelled")
        elif text == t("status.testing", self.lang):
            self._set_top_badge("testing")
        elif text == t("status.done", self.lang):
            self._set_top_badge("done")
        elif text == t("status.ready", self.lang):
            self._set_top_badge("ready")
        else:
            self._set_top_badge("running")

    def _set_top_badge(self, state: str) -> None:
        """更新顶部状态徽标（线程安全）"""
        badge_style = {
            "ready": ("#dcfce7", "#166534"),
            "running": ("#dbeafe", "#1d4ed8"),
            "testing": ("#e0f2fe", "#075985"),
            "done": ("#dcfce7", "#166534"),
            "error": ("#fee2e2", "#b91c1c"),
            "cancelled": ("#ffedd5", "#c2410c"),
        }

        bg, fg = badge_style.get(state, ("#e2e8f0", "#334155"))
        text = t(f"badge.{state}", self.lang)

        if not hasattr(self, "badge_label"):
            return

        self.ui_caller.call(lambda: self.badge_label.config(text=text, bg=bg, fg=fg))

    def _set_progress(self, value: float) -> None:
        """更新进度条（线程安全）"""
        self.ui_caller.call(lambda: self.progress.config(value=value))

    def _set_buttons_state(self, enabled: bool) -> None:
        """启用或禁用操作按钮（线程安全）"""
        state = tk.NORMAL if enabled else tk.DISABLED
        self.ui_caller.call(
            lambda: (
                self.btn_fix.config(state=state),
                self.btn_test.config(state=state)
            )
        )

    def _refresh_adapters(self) -> None:
        """刷新网卡列表"""
        adapters = self.operations.refresh_adapters(force=True)
        self.combo_adapter.config(values=adapters)

        if adapters:
            self.combo_adapter.current(0)
            msg = t("adapter.detected", self.lang, count=len(adapters))
            selected = self.adapter_var.get() or adapters[0]
            if selected:
                msg += f"，{t('adapter.selected', self.lang, name=selected)}"
        else:
            msg = t("adapter.none", self.lang)

        self.log(msg)

    def _export_log(self) -> None:
        """导出日志到文件"""
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
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

    def _start_fix_thread(self) -> None:
        """启动修复线程"""
        self._set_buttons_state(False)
        self.progress.config(value=0, maximum=100)
        self.cancel_token = CancellationToken()
        self._set_top_badge("running")

        threading.Thread(
            target=self._fix_network_logic,
            daemon=True
        ).start()

    def _start_test_thread(self) -> None:
        """启动连通性测试线程"""
        self._set_buttons_state(False)
        self.progress.config(mode="indeterminate")
        self.progress.start(10)
        self.cancel_token = CancellationToken()
        self._set_top_badge("testing")

        threading.Thread(
            target=self._connectivity_only,
            daemon=True
        ).start()

    def _build_steps(self) -> list:
        """根据选中的选项构建修复步骤列表"""
        adapter_name = self.adapter_var.get()

        steps = self.operations.build_steps(
            do_proxy=self.var_proxy.get(),
            do_dns=self.var_dns.get(),
            do_winsock=self.var_winsock.get(),
            do_ip=self.var_ip.get(),
            do_tcpip=self.var_tcpip.get(),
            do_adapter=self.var_adapter.get(),
            adapter_name=adapter_name
        )

        # 如果勾选了重启网卡但未选择网卡，给出警告
        if self.var_adapter.get() and not adapter_name:
            self.log_safe(t("warn.adapter_not_selected", self.lang), "warn")

        return steps

    def _handle_step_result(self, title_key: str, result: StepResult) -> None:
        """处理并记录修复步骤的结果"""
        status = t("result.success", self.lang) if result.ok else t("result.failed", self.lang)
        level = "success" if result.ok else "error"
        self.log_safe(f"{t(title_key, self.lang)}：{status}", level)

        # 如果有输出信息，也记录下来
        if result.output:
            self.log_safe(result.output, "info" if result.ok else "warn")

    def _log_connectivity_result(self, conn: ConnectivityResult) -> None:
        """记录连通性测试结果"""
        # Ping 114DNS
        if conn.ping_114:
            self.log_safe(t("result.ping_ok", self.lang, target="114DNS"), "success")
        else:
            self.log_safe(t("result.ping_fail", self.lang, target="114DNS"), "error")

        # Ping 8.8.8.8
        if conn.ping_google:
            self.log_safe(t("result.ping_ok", self.lang, target="8.8.8.8"), "success")
        else:
            self.log_safe(t("result.ping_fail", self.lang, target="8.8.8.8"), "error")

        # HTTP 测试
        if conn.http_test:
            self.log_safe(t("result.http_ok", self.lang), "success")
        else:
            self.log_safe(t("result.http_fail", self.lang), "error")

    def _fix_network_logic(self) -> None:
        """主修复逻辑（在后台线程运行）"""
        try:
            # 显示当前代理状态
            enabled, server = self.operations.get_proxy_status()
            status_str = t("proxy.enabled", self.lang) if enabled else t("proxy.disabled", self.lang)
            server_str = server or t("proxy.no_server", self.lang)
            self.log_safe(t("proxy.status", self.lang, status=status_str, server=server_str))

            # 构建修复步骤
            steps = self._build_steps()
            total = len(steps) + 1  # +1 为最后的连通性测试

            if total == 1:  # 没有选中任何操作
                self.log_safe(t("warn.no_selection", self.lang), "warn")
                self._set_status(t("status.ready", self.lang), "black")
                self._set_buttons_state(True)
                return

            per_step = 100 / total
            progress_val = 0.0

            # 逐步执行修复
            for idx, step in enumerate(steps, start=1):
                # 检查是否被取消
                if self.cancel_token and self.cancel_token.is_cancelled:
                    self._set_status(t("status.cancelled", self.lang), "orange")
                    break

                # 更新状态显示
                action = t(step.title_key, self.lang)
                self._set_status(
                    t("progress.step", self.lang, current=idx, total=len(steps), action=action),
                    "#0057b7"
                )

                # 执行当前步骤
                result = step.func()
                self._handle_step_result(step.title_key, result)

                # 更新进度条
                progress_val += per_step
                self._set_progress(progress_val)

            # 最后进行连通性测试
            self._set_status(
                t("progress.step", self.lang, current=total, total=total, action=t("step.test_connectivity", self.lang)),
                "#4b8b3b"
            )

            conn = self.operations.test_connectivity()
            self._log_connectivity_result(conn)
            self._set_progress(100)

            # 完成
            self._set_status(t("status.done", self.lang), "#4b8b3b")
            self.ui_caller.call(
                lambda: messagebox.showinfo(
                    t("msg.fix_done.title", self.lang),
                    t("msg.fix_done.content", self.lang)
                )
            )

        except Exception as e:
            logger.exception("修复失败")
            self._set_status(t("status.error", self.lang, error=str(e)), "red")
            self.ui_caller.call(
                lambda: messagebox.showerror(
                    t("msg.fix_error.title", self.lang),
                    t("msg.fix_error.content", self.lang, error=str(e))
                )
            )

        finally:
            self._set_buttons_state(True)

    def _connectivity_only(self) -> None:
        """仅运行连通性测试（后台线程）"""
        try:
            self.log_safe("-" * 50)
            self.log_safe(t("step.test_connectivity", self.lang))
            self._set_status(t("status.testing", self.lang), "#4b8b3b")

            conn = self.operations.test_connectivity()
            self._log_connectivity_result(conn)

            self._set_status(t("status.done", self.lang), "#4b8b3b")

        except Exception as e:
            logger.exception("连通性测试失败")
            self._set_status(t("status.error", self.lang, error=str(e)), "red")
            self.ui_caller.call(
                lambda: messagebox.showerror(
                    t("msg.fix_error.title", self.lang),
                    t("msg.fix_error.content", self.lang, error=str(e))
                )
            )

        finally:
            self.ui_caller.call(lambda: self.progress.stop())
            self.ui_caller.call(lambda: self.progress.config(mode="determinate", value=0))
            self._set_buttons_state(True)

    def cleanup(self) -> None:
        """清理资源，在关闭窗口前调用"""
        self.ui_caller.stop()


def main() -> None:
    """独立运行的入口函数"""
    import tkinter as tk
    root = tk.Tk()
    app = NetworkFixerApp(root)

    def on_closing():
        app.cleanup()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
