# clip_trends/db.py
"""MySQL 连接池 + 6表 CRUD 封装"""
import json, hashlib
from datetime import date
from contextlib import contextmanager
import pymysql
from dbutils.pooled_db import PooledDB
from config import MYSQL_CONFIG


# 连接池（线程安全）
pool = PooledDB(
    creator=pymysql,
    maxconnections=5,
    mincached=1,
    maxcached=3,
    blocking=True,
    **MYSQL_CONFIG
)


@contextmanager
def get_conn():
    conn = pool.connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# --- videos ---

def upsert_videos(raw_videos: list) -> list[int]:
    """批量 upsert 视频，返回新增的视频 ID 列表"""
    new_ids = []
    with get_conn() as conn:
        cur = conn.cursor()
        for rv in raw_videos:
            source_id = rv.source_id or hashlib.sha256(
                rv.source_url.encode()).hexdigest()[:32]
            cur.execute(
                "SELECT id FROM videos WHERE site=%s AND source_id=%s",
                (rv.site, source_id)
            )
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    "UPDATE videos SET popularity_score=%s, updated_at=NOW() WHERE id=%s",
                    (rv.popularity_score, existing[0])
                )
            else:
                cur.execute(
                    """INSERT INTO videos
                       (site, source_url, source_id, title, thumbnail_url,
                        duration_sec, resolution, tags_json, description, popularity_score)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (rv.site, rv.source_url, source_id, rv.title,
                     rv.thumbnail_url, rv.duration_sec, rv.resolution,
                     json.dumps(rv.tags, ensure_ascii=False),
                     rv.description, rv.popularity_score)
                )
                new_ids.append(cur.lastrowid)
    return new_ids


# --- video_techniques ---

def save_techniques(video_id: int, techniques: list[dict]):
    """写入技法标签。techniques: [{"taxonomy_id":1,"confidence":0.9,"evidence":"...","method":"qwen-vl"},...]"""
    if not techniques:
        return
    with get_conn() as conn:
        cur = conn.cursor()
        for t in techniques:
            cur.execute(
                """INSERT INTO video_techniques (video_id, taxonomy_id, confidence, evidence, method)
                   VALUES (%s,%s,%s,%s,%s)
                   ON DUPLICATE KEY UPDATE confidence=%s, evidence=%s, method=%s""",
                (video_id, t["taxonomy_id"], t["confidence"], t["evidence"], t["method"],
                 t["confidence"], t["evidence"], t["method"])
            )


# --- daily_trends ---

def refresh_daily_trends():
    """根据 video_techniques 聚合生成今日趋势快照"""
    today = date.today()
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO daily_trends (date, taxonomy_id, video_count, avg_popularity, avg_duration,
                                       sample_video_ids, trending_direction)
            SELECT
                CURDATE() as date,
                vt.taxonomy_id,
                COUNT(DISTINCT vt.video_id) as video_count,
                AVG(v.popularity_score) as avg_popularity,
                AVG(v.duration_sec) as avg_duration,
                JSON_ARRAYAGG(v.id LIMIT 5) as sample_video_ids,
                CASE
                    WHEN COALESCE(
                        (SELECT video_count FROM daily_trends dt2
                         WHERE dt2.taxonomy_id = vt.taxonomy_id AND dt2.date = CURDATE() - INTERVAL 1 DAY),
                        0
                    ) = 0 THEN 'stable'
                    WHEN COUNT(DISTINCT vt.video_id) >
                         (SELECT video_count FROM daily_trends dt2
                          WHERE dt2.taxonomy_id = vt.taxonomy_id AND dt2.date = CURDATE() - INTERVAL 1 DAY) * 1.2
                    THEN 'rising'
                    WHEN COUNT(DISTINCT vt.video_id) <
                         (SELECT video_count FROM daily_trends dt2
                          WHERE dt2.taxonomy_id = vt.taxonomy_id AND dt2.date = CURDATE() - INTERVAL 1 DAY) * 0.8
                    THEN 'declining'
                    ELSE 'stable'
                END as trending_direction
            FROM video_techniques vt
            JOIN videos v ON vt.video_id = v.id
            WHERE DATE(vt.created_at) = CURDATE()
            GROUP BY vt.taxonomy_id
            ON DUPLICATE KEY UPDATE
                video_count = VALUES(video_count),
                avg_popularity = VALUES(avg_popularity),
                avg_duration = VALUES(avg_duration),
                sample_video_ids = VALUES(sample_video_ids),
                trending_direction = VALUES(trending_direction)
        """)
        # 清理 90 天前的旧趋势数据
        cur.execute(
            "DELETE FROM daily_trends WHERE date < CURDATE() - INTERVAL 90 DAY"
        )


# --- crawl_logs ---

def start_crawl_log(site: str) -> int:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO crawl_logs (site, status) VALUES (%s, 'running')",
            (site,)
        )
        return cur.lastrowid


def finish_crawl_log(log_id: int, videos_total: int, videos_new: int, errors: str = None):
    status = 'success'
    if errors and videos_total > 0:
        status = 'partial'
    elif errors:
        status = 'failed'
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """UPDATE crawl_logs SET ended_at=NOW(), videos_total=%s,
               videos_new=%s, errors=%s, status=%s WHERE id=%s""",
            (videos_total, videos_new, errors, status, log_id)
        )


# --- editing_templates ---

def extract_editing_templates():
    """同一 taxonomy_id 组合（≥2个）出现在 ≥3 个不同视频中 → 生成模板"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT GROUP_CONCAT(DISTINCT vt.taxonomy_id ORDER BY vt.taxonomy_id) as combo,
                   COUNT(DISTINCT vt.video_id) as cnt
            FROM video_techniques vt
            WHERE DATE(vt.created_at) >= CURDATE() - INTERVAL 7 DAY
            GROUP BY vt.video_id
        """)
        combo_counts = {}
        for row in cur.fetchall():
            combo = row[0]
            if combo:
                combo_counts[combo] = combo_counts.get(combo, 0) + 1

        for combo, count in combo_counts.items():
            if count >= 3:
                tax_ids = [int(x) for x in combo.split(',')]
                tax_ids_json = json.dumps(tax_ids)
                cur.execute(
                    "SELECT id FROM editing_templates WHERE taxonomy_ids_json=%s",
                    (tax_ids_json,)
                )
                if not cur.fetchone():
                    placeholders = ','.join(['%s'] * len(tax_ids))
                    cur.execute(
                        f"SELECT CONCAT(dimension,'/',category,'/',subcategory) as full_name "
                        f"FROM technique_taxonomy WHERE id IN ({placeholders})",
                        tax_ids
                    )
                    names = [r[0] for r in cur.fetchall()]
                    template_name = " + ".join(names[:3])
                    cur.execute(
                        """INSERT INTO editing_templates (name, description, taxonomy_ids_json, prompt_snippet)
                           VALUES (%s, %s, %s, %s)""",
                        (template_name, f"高频组合(周出现{count}次)",
                         tax_ids_json,
                         f"结合以下技法: {template_name}")
                    )
