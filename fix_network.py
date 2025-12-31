import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText
import subprocess
import ctypes
import sys
import winreg
import threading
import urllib.request
import socket
import os

class NetworkFixerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("网络修复工具 v1.0.1")
        self.root.geometry("560x600")
        self.root.resizable(False, False)
        
        self.setup_style()
        self.create_widgets()
        
        self.log("欢迎使用网络修复工具！", "success")
        self.log("勾选需要的操作后点击开始修复；也可单独运行连通性测试。")
        self.log("提示：操作会修改网络配置，需管理员权限；代理/VPN 关闭后效果更佳。")
        self.log("-" * 50)

    def setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TButton", font=("Microsoft YaHei", 9), padding=5)
        style.configure("TLabel", font=("Microsoft YaHei", 9))
        style.configure("Header.TLabel", font=("Microsoft YaHei", 12, "bold"))

    def create_widgets(self):
        # 顶部标题
        header = ttk.Label(self.root, text="网络连接修复（VPN/代理后常用）", style="Header.TLabel")
        header.pack(pady=12)

        tips_text = (
            "使用指引：\n"
            "1) 以管理员身份运行（已自动尝试提权）；\n"
            "2) 断开 VPN/代理后再修复；\n"
            "3) 勾选所需步骤后开始修复，完成后可单独运行连通性测试；\n"
            "4) 如仍异常，尝试重启路由器/电脑或联系网络管理员。"
        )
        ttk.Label(self.root, text=tips_text, justify=tk.LEFT, wraplength=510, foreground="#444").pack(fill=tk.X, padx=12)

        # 操作区容器框架
        frame_ops = ttk.LabelFrame(self.root, text="修复选项")
        frame_ops.pack(fill=tk.X, padx=12, pady=8)

        # 选项变量
        self.var_proxy = tk.BooleanVar(value=True)
        self.var_dns = tk.BooleanVar(value=True)
        self.var_winsock = tk.BooleanVar(value=True)
        self.var_ip = tk.BooleanVar(value=True)
        self.var_tcpip = tk.BooleanVar(value=False)
        self.var_adapter = tk.BooleanVar(value=False)

        # 勾选项控件
        ttk.Checkbutton(frame_ops, text="关闭系统代理", variable=self.var_proxy).grid(row=0, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Checkbutton(frame_ops, text="刷新DNS缓存", variable=self.var_dns).grid(row=0, column=1, sticky=tk.W, padx=8, pady=6)
        ttk.Checkbutton(frame_ops, text="重置Winsock", variable=self.var_winsock).grid(row=1, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Checkbutton(frame_ops, text="重置IP地址", variable=self.var_ip).grid(row=1, column=1, sticky=tk.W, padx=8, pady=6)
        ttk.Checkbutton(frame_ops, text="重置TCP/IP协议栈", variable=self.var_tcpip).grid(row=2, column=0, sticky=tk.W, padx=8, pady=6)
        ttk.Checkbutton(frame_ops, text="重启指定网卡", variable=self.var_adapter).grid(row=2, column=1, sticky=tk.W, padx=8, pady=6)

        # 网卡选择区
        frame_adapter = ttk.LabelFrame(self.root, text="网卡选择（重启网卡时使用）")
        frame_adapter.pack(fill=tk.X, padx=12, pady=8)
        
        self.adapter_var = tk.StringVar(value="")
        ttk.Label(frame_adapter, text="选择网卡：").grid(row=0, column=0, padx=8, pady=6, sticky=tk.W)
        
        self.combo_adapter = ttk.Combobox(frame_adapter, textvariable=self.adapter_var, state="readonly", width=32)
        self.combo_adapter.grid(row=0, column=1, padx=8, pady=6, sticky=tk.W)
        
        # 操作按钮区
        frame_run = ttk.Frame(self.root)
        frame_run.pack(fill=tk.X, padx=12, pady=6)
        
        self.btn_fix = ttk.Button(frame_run, text="开始修复", width=18, command=self.start_fix_thread)
        self.btn_fix.pack(side=tk.LEFT, padx=4)

        self.btn_test = ttk.Button(frame_run, text="仅连通性测试", width=18, command=self.start_test_thread)
        self.btn_test.pack(side=tk.LEFT, padx=4)
        
        self.btn_refresh = ttk.Button(frame_run, text="刷新网卡列表", width=18, command=self.refresh_adapters)
        self.btn_refresh.pack(side=tk.LEFT, padx=4)

        self.btn_export = ttk.Button(frame_run, text="导出日志", width=12, command=self.export_log)
        self.btn_export.pack(side=tk.RIGHT, padx=4)

        # 状态与进度区
        self.status_label = ttk.Label(self.root, text="就绪", font=("Microsoft YaHei", 9))
        self.status_label.pack(padx=12, pady=4, anchor=tk.W)
        
        self.progress = ttk.Progressbar(self.root, mode="determinate")
        self.progress.pack(fill=tk.X, padx=12, pady=4)

        # 日志输出区
        frame_log = ttk.LabelFrame(self.root, text="执行日志与结果")
        frame_log.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        
        self.log_text = ScrolledText(frame_log, height=12, font=("Consolas", 10))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # 日志着色配置
        self.log_text.tag_config("info", foreground="#1f1f1f")
        self.log_text.tag_config("success", foreground="#2d7a1f")
        self.log_text.tag_config("warn", foreground="#a65d00")
        self.log_text.tag_config("error", foreground="#b00020")

        # 初始化加载网卡列表（需在日志控件创建后调用）
        self.refresh_adapters()

    def log(self, text, level="info"):
        prefix_map = {
            "info": "[INFO]",
            "warn": "[WARN]",
            "error": "[ERROR]",
            "success": "[OK]",
        }
        line = f"{prefix_map.get(level, '[INFO]')} {text}"
        self.log_text.insert(tk.END, line + "\n", level)
        self.log_text.see(tk.END)

    def run_command(self, command):
        """运行系统命令并隐藏黑框，返回(成功与否, 输出文本)"""
        try:
            proc = subprocess.run(
                command,
                shell=True,
                check=True,
                creationflags=0x08000000,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=False  # Capture bytes to handle encoding manually
            )
            # Try decoding with system default encoding (mbcs), fallback to utf-8, ignore errors if must
            try:
                out = proc.stdout.decode('mbcs', errors='replace')
            except Exception:
                out = proc.stdout.decode('utf-8', errors='replace')
            
            return True, out.strip()
        except subprocess.CalledProcessError as e:
            # Decode stderr/stdout from exception if available
            raw_out = e.stdout if e.stdout else b""
            try:
                out = raw_out.decode('mbcs', errors='replace')
            except Exception:
                out = raw_out.decode('utf-8', errors='replace')
            return False, out.strip()
        except Exception as e:
            return False, str(e)

    def list_adapters(self):
        ok, out = self.run_command('netsh interface show interface')
        names = []
        if ok and out:
            for line in out.splitlines():
                # Split by whitespace, max 3 splits to preserve spaces in interface name (4th column)
                parts = line.strip().split(maxsplit=3)
                if len(parts) >= 4:
                    # Filter out header/separator lines
                    # Header usually starts with "Admin State" / "管理员状态"
                    # Separator usually starts with "---"
                    p0 = parts[0]
                    if p0.startswith('-') or p0 in ["Admin", "管理员状态"]:
                        continue
                    
                    name = parts[3]
                    names.append(name)
        return names

    def refresh_adapters(self):
        adapters = self.list_adapters()
        self.combo_adapter.config(values=adapters)
        if adapters:
            self.combo_adapter.current(0)
        self.log(f"已检测到网卡 {len(adapters)} 个" + (f"，当前选择：{self.adapter_var.get() or adapters[0]}" if adapters else ""))

    def get_proxy_status(self):
        try:
            path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ)
            enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
            try:
                server, _ = winreg.QueryValueEx(key, "ProxyServer")
            except FileNotFoundError:
                server = ""
            winreg.CloseKey(key)
            return bool(enable), server
        except Exception:
            return False, ""

    def disable_system_proxy(self):
        try:
            path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_WRITE)
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, "")
            winreg.CloseKey(key)
            return True
        except Exception:
            return False

    def restart_adapter(self, adapter_name):
        ok1, out1 = self.run_command(f'netsh interface set interface "{adapter_name}" admin=disabled')
        ok2, out2 = self.run_command(f'netsh interface set interface "{adapter_name}" admin=enabled')
        return (ok1 and ok2), (out1 + "\n" + out2).strip()

    def test_connectivity(self):
        results = {}
        ok114, _ = self.run_command('ping -n 2 114.114.114.114')
        ok88, _ = self.run_command('ping -n 2 8.8.8.8')
        results['ping_114'] = ok114
        results['ping_88'] = ok88
        
        try:
            socket.setdefaulttimeout(5)
            with urllib.request.urlopen('http://www.msftconnecttest.com/redirect') as resp:
                code = resp.getcode()
                results['http'] = (200 <= code < 400)
        except Exception:
            results['http'] = False
        return results

    def start_fix_thread(self):
        self.status_label.config(text="准备开始...", foreground="black")
        threading.Thread(target=self.fix_network_logic, daemon=True).start()

    def start_test_thread(self):
        self.status_label.config(text="正在进行连通性测试...", foreground="#4b8b3b")
        threading.Thread(target=self.connectivity_only, daemon=True).start()

    def build_steps(self):
        steps = []
        if self.var_proxy.get():
            steps.append(("关闭系统代理", self.step_disable_proxy))
        if self.var_dns.get():
            steps.append(("刷新 DNS 缓存", self.step_flush_dns))
        if self.var_winsock.get():
            steps.append(("重置 Winsock", self.step_reset_winsock))
        if self.var_ip.get():
            steps.append(("重置 IP 地址", self.step_reset_ip))
        if self.var_tcpip.get():
            steps.append(("重置 TCP/IP 协议栈", self.step_reset_tcpip))

        adapter = self.adapter_var.get()
        if self.var_adapter.get():
            if adapter:
                steps.append((f"重启网卡：{adapter}", lambda: self.restart_adapter(adapter)))
            else:
                self.log("已勾选重启网卡，但未选择网卡，已跳过。", "warn")
        return steps

    def step_disable_proxy(self):
        ok = self.disable_system_proxy()
        return ok, ""

    def step_flush_dns(self):
        return self.run_command("ipconfig /flushdns")

    def step_reset_winsock(self):
        return self.run_command("netsh winsock reset")

    def step_reset_ip(self):
        ok1, out1 = self.run_command("ipconfig /release")
        ok2, out2 = self.run_command("ipconfig /renew")
        merged = "\n".join(filter(None, [out1, out2]))
        return (ok1 and ok2), merged

    def step_reset_tcpip(self):
        return self.run_command("netsh int ip reset")

    def handle_step_result(self, title, ok, details):
        self.log(f"{title}：{'成功' if ok else '失败'}", "success" if ok else "error")
        if details:
            self.log(details, "info" if ok else "warn")

    def fix_network_logic(self):
        self.btn_fix.config(state=tk.DISABLED)
        self.btn_test.config(state=tk.DISABLED)
        self.progress.config(value=0, maximum=100)
        
        try:
            enabled, server = self.get_proxy_status()
            self.log(f"当前系统代理：{'开启' if enabled else '关闭'}，服务器：{server or '（无）'}")

            steps = self.build_steps()
            total = len(steps) + 1  # +1 for connectivity test
            if total == 0:
                self.log("未勾选任何操作，已取消。", "warn")
                return

            per_step = 100 / total
            progress_val = 0

            for idx, (title, fn) in enumerate(steps, start=1):
                self.status_label.config(text=f"[{idx}/{len(steps)}] 正在{title}...", foreground="#0057b7")
                ok, details = fn()
                self.handle_step_result(title, ok, details)
                progress_val += per_step
                self.progress.config(value=progress_val)

            self.status_label.config(text="正在进行网络连通性测试...", foreground="#4b8b3b")
            conn = self.test_connectivity()
            self.log(f"Ping 114DNS：{'可达' if conn['ping_114'] else '不可达'}", "success" if conn['ping_114'] else "error")
            self.log(f"Ping 8.8.8.8：{'可达' if conn['ping_88'] else '不可达'}", "success" if conn['ping_88'] else "error")
            self.log(f"HTTP 检测：{'可用' if conn['http'] else '不可用'}", "success" if conn['http'] else "error")
            self.progress.config(value=100)

            self.status_label.config(text="修复完成！请尝试上网。", foreground="#4b8b3b")
            messagebox.showinfo("成功", "网络修复完成！\n建议重启浏览器或相关应用。")

        except Exception as e:
            self.status_label.config(text=f"发生错误: {str(e)}", foreground="red")
            messagebox.showerror("错误", f"修复过程中出错: {str(e)}")
        
        finally:
            self.btn_fix.config(state=tk.NORMAL)
            self.btn_test.config(state=tk.NORMAL)

    def connectivity_only(self):
        self.btn_fix.config(state=tk.DISABLED)
        self.btn_test.config(state=tk.DISABLED)
        self.progress.config(mode="indeterminate")
        self.progress.start(10)
        try:
            self.log("-" * 50)
            self.log("仅连通性测试开始", "info")
            conn = self.test_connectivity()
            self.log(f"Ping 114DNS：{'可达' if conn['ping_114'] else '不可达'}", "success" if conn['ping_114'] else "error")
            self.log(f"Ping 8.8.8.8：{'可达' if conn['ping_88'] else '不可达'}", "success" if conn['ping_88'] else "error")
            self.log(f"HTTP 检测：{'可用' if conn['http'] else '不可用'}", "success" if conn['http'] else "error")
            self.status_label.config(text="连通性测试完成", foreground="#4b8b3b")
        except Exception as e:
            self.status_label.config(text=f"测试错误: {str(e)}", foreground="red")
            messagebox.showerror("错误", f"连通性测试出错: {str(e)}")
        finally:
            self.progress.stop()
            self.progress.config(mode="determinate", value=0)
            self.btn_fix.config(state=tk.NORMAL)
            self.btn_test.config(state=tk.NORMAL)

    def export_log(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            title="导出日志"
        )
        if not path:
            return
        try:
            content = self.log_text.get("1.0", tk.END)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("已导出", f"日志已保存到：\n{path}")
        except Exception as e:
            messagebox.showerror("导出失败", f"无法写入文件：{e}")

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def _quote_arg(arg: str) -> str:
    # Basic Windows-safe quoting for args containing spaces or quotes
    if any(ch in arg for ch in [' ', '\t', '"']):
        return '"' + arg.replace('"', '\\"') + '"'
    return arg

if __name__ == "__main__":
    if not is_admin():
        # Ask for elevation; if user cancels, show a friendly message instead of直接闪退。
        ctypes.windll.user32.MessageBoxW(
            None,
            "本工具需要管理员权限以修改网络配置。即将请求权限，请选择“是”。\n\n"
            "如果未弹出窗口，请右键以管理员身份运行，或在命令行执行：\n"
            "powershell -Command \"Start-Process python fix_network.py -Verb runAs\"",
            "需要管理员权限",
            0x40
        )
        
        # 构造安全的参数，处理空格/中文路径；兼容脚本与打包 exe
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
                "请右键以管理员身份运行，或在命令行使用 Start-Process 提权后再试。",
                "启动失败",
                0x10
            )
        sys.exit()

    root = tk.Tk()
    app = NetworkFixerApp(root)
    root.mainloop()


