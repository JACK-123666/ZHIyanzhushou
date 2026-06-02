# clip_trends/main.py
"""CLI 入口: python main.py --once  |  python main.py --daemon"""
import sys, os
# 确保 clip_trends/ 在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from taxonomy import seed_taxonomy
from config import MYSQL_CONFIG


def main():
    # 确保 taxonomy 预填
    print("[init] 检查 taxonomy 预填...")
    count = seed_taxonomy(MYSQL_CONFIG)
    print(f"[init] taxonomy 已就绪 (本次新增 {count})")

    if '--once' in sys.argv:
        from scheduler import run_crawl_job
        print("[once] 手动执行一次完整爬取...")
        run_crawl_job()
        print("[once] 完成")
    elif '--daemon' in sys.argv:
        from scheduler import start_scheduler
        import time
        print("[daemon] 启动守护进程...")
        start_scheduler()
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("[daemon] 已停止")
    else:
        print("用法: python main.py --once    (手动执行一次)")
        print("      python main.py --daemon  (启动定时守护进程)")


if __name__ == '__main__':
    main()
