"""
剪辑趋势查询 — MySQL 只读接口
"""

import pymysql, os
from dbutils.pooled_db import PooledDB
from dotenv import load_dotenv

load_dotenv()

_mysql_config = {
    'host': os.environ.get('MYSQL_HOST', 'localhost'),
    'port': int(os.environ.get('MYSQL_PORT') or 3306),
    'user': os.environ.get('MYSQL_USER', 'clip_trends'),
    'password': os.environ.get('MYSQL_PASSWORD', ''),
    'database': os.environ.get('MYSQL_DATABASE', 'clip_trends'),
    'charset': 'utf8mb4',
}

_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        _pool = PooledDB(creator=pymysql, maxconnections=3, mincached=1, maxcached=2,
                         blocking=False, **_mysql_config)
    return _pool


def _query(sql, params=None):
    try:
        conn = _get_pool().connection()
        cur = conn.cursor()
        cur.execute(sql, params)
        columns = [col[0] for col in cur.description]
        rows = [dict(zip(columns, row)) for row in cur.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        import logging
        logging.getLogger('trend_service').error(f"数据库查询失败: {e}")
        return []


def get_trending_techniques(dimension=None, limit=10):
    sql = """
        SELECT t.dimension, t.category, t.subcategory, t.detail,
               SUM(dt.video_count) as total_videos,
               dt.trending_direction,
               dt.sample_video_ids
        FROM daily_trends dt
        JOIN technique_taxonomy t ON dt.taxonomy_id = t.id
        WHERE dt.date >= CURDATE() - INTERVAL 7 DAY
    """
    params = []
    if dimension:
        sql += " AND t.dimension = %s"
        params.append(dimension)
    sql += " GROUP BY dt.taxonomy_id ORDER BY total_videos DESC LIMIT %s"
    params.append(limit)
    return _query(sql, params)


def search_techniques(keywords: str, dimensions=None, limit=20):
    sql = """
        SELECT t.* FROM technique_taxonomy t
        WHERE (t.subcategory LIKE %s OR t.category LIKE %s OR t.dimension LIKE %s)
    """
    kw = f'%{keywords}%'
    params = [kw, kw, kw]
    if dimensions:
        placeholders = ','.join(['%s'] * len(dimensions))
        sql += f" AND t.dimension IN ({placeholders})"
        params.extend(dimensions)
    sql += " LIMIT %s"
    params.append(limit)
    return _query(sql, params)


def get_weekly_trend_context() -> str:
    trends = get_trending_techniques(limit=15)
    if not trends:
        return "（暂无趋势数据）"

    lines = []
    for t in trends:
        arrow = {'rising': '↑', 'declining': '↓', 'stable': '→'}.get(
            t.get('trending_direction'), '→')
        lines.append(
            f"- {t['dimension']}/{t['category']}/{t['subcategory']}: "
            f"{t.get('detail', '')} ({arrow}{t['total_videos']}视频本周)"
        )
    return '\n'.join(lines)
