# clip_trends/scheduler.py
"""APScheduler 每日定时任务"""
import hashlib
from apscheduler.schedulers.background import BackgroundScheduler
from crawlers import CRAWLERS
from db import upsert_videos, start_crawl_log, finish_crawl_log, get_conn, refresh_daily_trends, extract_editing_templates
from classifier import classify
from config import CRAWL_CONFIG


scheduler = BackgroundScheduler()


def run_crawl_job():
    """每日全量爬取 + 分析"""
    print(f"[scheduler] 开始每日爬取...")
    for site_name, crawler_cls in CRAWLERS.items():
        log_id = start_crawl_log(site_name)
        errors = []
        try:
            crawler = crawler_cls(CRAWL_CONFIG)
            raw_videos = crawler.crawl()
            new_ids = upsert_videos(raw_videos)

            # 建立 source_id → RawVideo 映射
            rv_map = {}
            for rv in raw_videos:
                sid = rv.source_id or hashlib.sha256(
                    rv.source_url.encode()).hexdigest()[:32]
                rv_map[sid] = rv

            for vid_id in new_ids:
                # 从数据库回查 source_id
                with get_conn() as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT source_id FROM videos WHERE id=%s", (vid_id,))
                    row = cur.fetchone()
                source_id = row[0] if row else None
                rv = rv_map.get(source_id) if source_id else None

                if rv and rv.source_url:
                    video_record = {
                        'id': vid_id,
                        'source_url': rv.source_url,
                        'tags': rv.tags,
                        'title': rv.title,
                        'description': rv.description or '',
                    }
                    try:
                        classify(video_record, crawler._download_video)
                    except Exception as e:
                        errors.append(f"classify vid={vid_id}: {e}")

            finish_crawl_log(log_id, len(raw_videos), len(new_ids),
                             '; '.join(errors) if errors else None)
            print(f"[scheduler] {site_name}: {len(new_ids)} new / {len(raw_videos)} total")
        except Exception as e:
            finish_crawl_log(log_id, 0, 0, str(e))
            print(f"[scheduler] {site_name} FAILED: {e}")

    # 更新每日趋势 + 提取模板
    refresh_daily_trends()
    extract_editing_templates()
    print(f"[scheduler] 每日趋势更新完成")


def start_scheduler():
    scheduler.add_job(run_crawl_job, 'cron', hour=2, minute=0, id='daily_crawl')
    scheduler.start()
    print("[scheduler] 定时任务已注册: 每天凌晨 2:00")
