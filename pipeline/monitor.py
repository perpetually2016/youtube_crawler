import os
import time
import psutil
import redis
import subprocess
from datetime import datetime
import sys

# --- 配置区 ---
MAIN_SCRIPT = "download_work.py"
PORT = 80  # 建议用 8080，如果用 80 记得 sudo 运行

# 获取脚本所在的绝对路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.path.join(BASE_DIR, "index.html")

try:
    from config import VIDEO_TODO, VIDEO_DOING, VIDEO_DONE, VIDEO_FAILED
    from output.redis_db import get_default_redis
except ImportError:
    VIDEO_TODO = "video:todo"
    VIDEO_DOING = "video:doing"
    VIDEO_DONE = "video:done"
    VIDEO_FAILED = "video:failed"

    def get_default_redis():
        return redis.Redis(host='127.0.0.1', port=6379, db=0, decode_responses=True)

def draw_progress_bar(percent, width=30):
    filled_width = int(width * percent / 100)
    bar = "█" * filled_width + "░" * (width - filled_width)
    return f"|{bar}| {percent:.2f}%"

def format_time(seconds):
    if seconds <= 0 or seconds > 9999999: return "计算中..."
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    if days > 0: return f"{days}天 {hours}小时"
    return f"{hours}小时 {minutes}分钟"

def monitor_all_in_one():
    r = get_default_redis()
    last_done_count = 0
    last_time = time.time()
    rpm = 0

    # 启动 Web 服务器 (指定当前目录为工作目录)
    print(f"🌐 正在启动 Web 服务... 端口: {PORT}")
    subprocess.Popen([sys.executable, "-m", "http.server", str(PORT)],
                     cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"✅ 监控已就绪！访问地址：http://127.0.0.1:{PORT}")

    while True:
        # --- 1. 数据采集 ---
        target_procs = []
        master_pid = None
        for p in psutil.process_iter(['pid', 'cmdline']):
            try:
                cmd = " ".join(p.info['cmdline'] or [])
                if MAIN_SCRIPT in cmd and p.pid != os.getpid():
                    master_pid = p.pid
                    target_procs.append(p)
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied): continue

        if master_pid:
            try:
                parent = psutil.Process(master_pid)
                target_procs.extend(parent.children(recursive=True))
            except: pass

        num_procs = len(target_procs)
        total_cpu, total_mem, proc_details = 0, 0, []
        for p in target_procs:
            try:
                p_cpu = p.cpu_percent(interval=None)
                p_mem_rss = p.memory_info().rss / (1024 * 1024)
                total_cpu += p_cpu
                total_mem += p_mem_rss
                proc_details.append({'pid': p.pid, 'cpu': p_cpu, 'mem': p_mem_rss})
            except: continue

        # --- 2. Redis 统计 ---
        try:
            todo, doing, done, failed = r.scard(VIDEO_TODO), r.scard(VIDEO_DOING), r.scard(VIDEO_DONE), r.scard(VIDEO_FAILED)
            total = todo + doing + done + failed
            percent = (done / total * 100) if total > 0 else 0
            now = time.time()
            if last_done_count > 0:
                diff_done, diff_time = done - last_done_count, now - last_time
                if diff_time >= 1: rpm = (diff_done / diff_time) * 60
            last_done_count, last_time = done, now
            eta_str = format_time(todo / (rpm / 60)) if rpm > 0 else "计算中..."
        except:
            todo = doing = done = failed = total = rpm = percent = 0; eta_str = "N/A"

        # --- 3. 网络测量 (1秒采样) ---
        net1 = psutil.net_io_counters().bytes_recv
        time.sleep(1)
        net_speed = (psutil.net_io_counters().bytes_recv - net1) * 8 / (1024 * 1024)

        # --- 4. 渲染文本内容 ---
        info_text = f"""=================================================================
📊 YT 集群监控 | {datetime.now().strftime('%H:%M:%S')} | 文件: {MAIN_SCRIPT}
=================================================================
总进度: {draw_progress_bar(percent)}  预计剩余: {eta_str}
任务总量: {total:<10} 瞬时速度: {rpm:>8.1f} 视频/分钟
-----------------------------------------------------------------
 [待处理]: {todo:<10} | [进行中]: {doing:<10}
 [已完成]: {done:<10} | [已失败]: {failed:<10}
-----------------------------------------------------------------
🚀 总进程数: {num_procs:<5} | 🌐 下行带宽: {net_speed:>8.2f} Mbps
🔥 总 CPU: {total_cpu:>7.1f}% | 🧠 总内存: {total_mem:>10.1f} MB
-----------------------------------------------------------------
PID 详情 (Top 10):
"""
        sorted_procs = sorted(proc_details, key=lambda x: x['mem'], reverse=True)
        for d in sorted_procs[:10]:
            tag = "[MASTER]" if d['pid'] == master_pid else "[WORKER]"
            info_text += f"  - PID {d['pid']:<7} {tag:<9}: CPU {d['cpu']:>5.1f}% | Mem {d['mem']:>6.1f}MB\n"

        # --- 5. 写入 HTML ---
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8"><meta http-equiv="refresh" content="5">
    <title>监控看板</title>
    <style>
        body {{ background-color: #000; color: #00FF41; font-family: monospace; padding: 20px; }}
        pre {{ background: #111; padding: 15px; border-radius: 8px; border: 1px solid #333; line-height: 1.5; }}
    </style>
</head>
<body>
    <pre>{info_text}</pre>
    <div style="font-size: 12px; color: #666;">自动刷新中: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
</body>
</html>"""

        with open(HTML_PATH, "w", encoding="utf-8") as f:
            f.write(html_content)

        # 终端逻辑判断：如果是前台终端运行，则清屏刷新；如果是 nohup 后台运行，则只打印到日志
        if sys.stdout.isatty():
            os.system('clear' if os.name == 'posix' else 'cls')
            print(info_text)
        else:
            # 后台运行时，每轮打印一行简要日志，防止日志文件过大
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Progress: {percent:.2f}% | Done: {done} | RPM: {rpm:.1f}")

if __name__ == "__main__":
    try:
        monitor_all_in_one()
    except KeyboardInterrupt:
        print("\n监控已停止。")