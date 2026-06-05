# 剪辑趋势爬虫系统 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建独立爬虫子项目 `clip_trends/`，每日爬取 4 个 CC0 站热门视频，Qwen-VL 抽帧分析 7 维剪辑技法，存入 MySQL，智演助手 Prompt 自动注入 + 前端面板查询。

**Architecture:** 爬虫独立 Python 项目，通过 MySQL 与智演助手通信。爬虫端：APScheduler 每日调度 → 4 站并行爬取 → ffmpeg 下载+抽帧 → Qwen-VL 多模态分析 → 写库。智演助手端：trend_service 只读 MySQL → 注入 LLM Prompt + 前端 /api/trends。

**Tech Stack:** Python 3.13, MySQL 8.0 (Docker), APScheduler, requests+BS4, ffmpeg/ffprobe, Qwen-VL (DashScope), DeepSeek API, Flask, vanilla JS

---

## File Map

**新建文件 (14):**
| 文件 | 职责 |
|------|------|
| `clip_trends/config.py` | 爬取配置 + API 密钥读取 |
| `clip_trends/db.py` | MySQL 连接池 + 6 表 CRUD |
| `clip_trends/taxonomy.py` | 7 维分类体系定义 + 预填 SQL 生成 |
| `clip_trends/crawlers/__init__.py` | 爬虫注册表 |
| `clip_trends/crawlers/base.py` | 抽象基类：UA/限速/重试/HEAD/下载 |
| `clip_trends/crawlers/pexels.py` | Pexels API 爬虫 |
| `clip_trends/crawlers/pixabay.py` | Pixabay API 爬虫 |
| `clip_trends/crawlers/coverr.py` | Coverr HTML 爬虫 |
| `clip_trends/crawlers/mixkit.py` | Mixkit HTML 爬虫 |
| `clip_trends/video_analyzer.py` | ffmpeg 下载+抽帧 + ffprobe 音频 |
| `clip_trends/qwen_client.py` | Qwen-VL API 封装 |
| `clip_trends/classifier.py` | 分类编排 + 降级策略 |
| `clip_trends/scheduler.py` | APScheduler 每日定时 |
| `clip_trends/main.py` | CLI 入口 (--once / --daemon) |
| `clip_trends/sql/schema.sql` | 6 表建表语句 |
| `clip_trends/requirements.txt` | 独立依赖 |
| `services/trend_service.py` | 智演助手侧只读查询 |

**修改文件 (4):**
| 文件 | 改动 |
|------|------|
| `app.py` | 新增 `/api/trends` 路由 |
| `services/llm_service.py` | SHOT_DESIGN_AUTO_SYSTEM 追加趋势占位 |
| `index.html` | 可折叠"剪辑趋势"面板 |
| `script.js` | 趋势面板交互 |
| `styles.css` | 趋势面板样式 |

---

### Task 1: Docker MySQL 环境 + 建表 + taxonomy 预填

**Files:**
- Create: `clip_trends/sql/schema.sql`
- Create: `clip_trends/config.py`
- Create: `clip_trends/taxonomy.py`

- [ ] **Step 1: 创建 schema.sql（6 张表）**

```sql
-- clip_trends/sql/schema.sql
CREATE DATABASE IF NOT EXISTS clip_trends
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE clip_trends;

CREATE TABLE technique_taxonomy (
    id INT PRIMARY KEY AUTO_INCREMENT,
    dimension VARCHAR(20) NOT NULL,
    category VARCHAR(30) NOT NULL,
    subcategory VARCHAR(40) NOT NULL,
    detail TEXT,
    keywords JSON NOT NULL,
    weight DECIMAL(3,2) DEFAULT 1.00,
    UNIQUE KEY uk_dim_cat_sub (dimension, category, subcategory)
) ENGINE=InnoDB;

CREATE TABLE videos (
    id INT PRIMARY KEY AUTO_INCREMENT,
    site VARCHAR(20) NOT NULL,
    source_url VARCHAR(500) NOT NULL,
    source_id VARCHAR(100),
    title VARCHAR(300),
    thumbnail_url VARCHAR(500),
    duration_sec DECIMAL(8,2),
    resolution VARCHAR(20),
    tags_json JSON,
    description TEXT,
    popularity_score DECIMAL(10,2) DEFAULT 0,
    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_site_source (site, source_id),
    INDEX idx_site (site),
    INDEX idx_popularity (popularity_score DESC),
    INDEX idx_crawled_at (crawled_at)
) ENGINE=InnoDB;

CREATE TABLE video_techniques (
    id INT PRIMARY KEY AUTO_INCREMENT,
    video_id INT NOT NULL,
    taxonomy_id INT NOT NULL,
    confidence DECIMAL(3,2) DEFAULT 0.70,
    evidence TEXT,
    method ENUM('rule','llm','qwen-vl','hybrid') DEFAULT 'rule',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_video_taxonomy (video_id, taxonomy_id),
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
    FOREIGN KEY (taxonomy_id) REFERENCES technique_taxonomy(id) ON DELETE CASCADE,
    INDEX idx_taxonomy (taxonomy_id),
    INDEX idx_method (method)
) ENGINE=InnoDB;

CREATE TABLE daily_trends (
    id INT PRIMARY KEY AUTO_INCREMENT,
    date DATE NOT NULL,
    taxonomy_id INT NOT NULL,
    video_count INT DEFAULT 0,
    avg_popularity DECIMAL(10,2) DEFAULT 0,
    avg_duration DECIMAL(8,2),
    sample_video_ids JSON,
    trending_direction ENUM('rising','stable','declining') DEFAULT 'stable',
    UNIQUE KEY uk_date_taxonomy (date, taxonomy_id),
    FOREIGN KEY (taxonomy_id) REFERENCES technique_taxonomy(id),
    INDEX idx_date (date),
    INDEX idx_trending (trending_direction)
) ENGINE=InnoDB;

CREATE TABLE crawl_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    site VARCHAR(20) NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    videos_total INT DEFAULT 0,
    videos_new INT DEFAULT 0,
    errors TEXT,
    status ENUM('running','success','partial','failed') DEFAULT 'running'
) ENGINE=InnoDB;

CREATE TABLE editing_templates (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    taxonomy_ids_json JSON NOT NULL,
    prompt_snippet TEXT NOT NULL,
    use_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;
```

- [ ] **Step 2: 创建 docker-compose.yml 追加 MySQL 服务**

读取现有 `docker-compose.yml`，追加 MySQL 容器：

```yaml
# 在现有 docker-compose.yml 的 services: 下追加
  mysql:
    image: mysql:8.0
    container_name: clip_trends_mysql
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:?required}
      MYSQL_DATABASE: clip_trends
      MYSQL_USER: ${MYSQL_USER:-clip_trends}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD:?required}
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
      - ./clip_trends/sql/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql
    restart: unless-stopped

# 在 volumes: 下追加
  mysql_data:
```

- [ ] **Step 3: 创建 config.py**

```python
# clip_trends/config.py
import os
from dotenv import load_dotenv

load_dotenv()

CRAWL_CONFIG = {
    'max_per_site': 15,
    'request_interval': 1.0,
    'request_timeout': 30,
    'retry_times': 3,
    'retry_backoff': [5, 10, 20],
}

VIDEO_ANALYSIS = {
    'max_file_size_mb': 50,
    'download_timeout': 120,
    'frame_interval': 3,        # 每 3 秒抽 1 帧
    'download_dir': 'clip_trends/temp_videos/',
    'qwen_model': 'qwen-vl-max',
}

MYSQL_CONFIG = {
    'host': os.environ.get('MYSQL_HOST', 'localhost'),
    'port': int(os.environ.get('MYSQL_PORT', 3306)),
    'user': os.environ.get('MYSQL_USER', 'clip_trends'),
    'password': os.environ.get('MYSQL_PASSWORD', ''),
    'database': os.environ.get('MYSQL_DATABASE', 'clip_trends'),
    'charset': 'utf8mb4',
}

DASHSCOPE_API_KEY = os.environ.get('DASHSCOPE_API_KEY', '')
PEXELS_API_KEY = os.environ.get('PEXELS_API_KEY', '')
PIXABAY_API_KEY = os.environ.get('PIXABAY_API_KEY', '')

# DeepSeek 复用主项目的 .env 变量
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_BASE_URL = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
```

- [ ] **Step 4: 创建 taxonomy.py（7 维分类体系 + 预填函数）**

```python
# clip_trends/taxonomy.py
"""
7 维剪辑技法分类体系
每次插入 taxonomy 前先检查已存在则跳过，保证幂等
"""

TAXONOMY = [
    {
        "dimension": "时间",
        "categories": [
            {
                "category": "压缩",
                "subcategories": [
                    {"sub": "跳切",      "detail": "省略中间过程，直接切到关键动作，制造跳跃感",
                     "keywords": ["jump cut","jumpcut","跳切","skip cut"]},
                    {"sub": "蒙太奇",    "detail": "多个短镜头组合传达一个概念或时间段",
                     "keywords": ["montage","蒙太奇","sequence","assembly edit"]},
                    {"sub": "省略",      "detail": "刻意省略部分时间，让观众自行脑补",
                     "keywords": ["ellipsis","time skip","省略","temporal skip"]},
                ]
            },
            {
                "category": "延长",
                "subcategories": [
                    {"sub": "慢动作",    "detail": "放慢画面速度，强调细节/情绪/力量感",
                     "keywords": ["slow motion","slow-mo","慢动作","slo-mo","slow down"]},
                    {"sub": "多角度",    "detail": "同一动作从多个机位反复呈现",
                     "keywords": ["multi-angle","multi angle","多角度","multi-cam"]},
                    {"sub": "插入镜头",  "detail": "在主动作中插入相关联的短镜头",
                     "keywords": ["insert shot","cutaway","插入","cut-in"]},
                ]
            },
            {
                "category": "颠倒",
                "subcategories": [
                    {"sub": "闪回",      "detail": "突然插入过去发生的画面",
                     "keywords": ["flashback","闪回","回忆"]},
                    {"sub": "闪前",      "detail": "突然插入未来将发生的画面",
                     "keywords": ["flashforward","flash forward","闪前","预演"]},
                    {"sub": "非线性叙事","detail": "不按时间顺序组织故事，打破线性结构",
                     "keywords": ["nonlinear","non-linear","非线性","fragmented"]},
                ]
            },
            {
                "category": "并行",
                "subcategories": [
                    {"sub": "平行剪辑",  "detail": "两条或多条故事线交替呈现",
                     "keywords": ["parallel editing","parallel","平行","cross edit"]},
                    {"sub": "交叉剪辑",  "detail": "两条时间线逼近同一时刻（如最后一分钟营救）",
                     "keywords": ["cross cutting","cross-cutting","交叉","intercut"]},
                ]
            },
        ]
    },
    {
        "dimension": "空间",
        "categories": [
            {
                "category": "连贯剪辑",
                "subcategories": [
                    {"sub": "180度轴线","detail": "所有机位在轴线同一侧，角色A始终画左B画右",
                     "keywords": ["180 degree","180°","axis line","轴线"]},
                    {"sub": "30度原则",  "detail": "相邻镜头机位变化至少30度防止跳切",
                     "keywords": ["30 degree","30° rule","角度变化"]},
                    {"sub": "匹配剪辑",  "detail": "利用画面内形状/颜色/运动的相似性做转场",
                     "keywords": ["match cut","match-cut","匹配剪辑","graphic match"]},
                    {"sub": "正反打",    "detail": "对话场景交替拍摄两个角色，OTS过肩→特写→反应",
                     "keywords": ["shot reverse shot","shot-reverse-shot","正反打","OTS"]},
                ]
            },
            {
                "category": "解构剪辑",
                "subcategories": [
                    {"sub": "越轴",      "detail": "故意跨过轴线拍摄，制造空间混乱或戏剧张力",
                     "keywords": ["cross axis","越轴","跳轴","axis break"]},
                    {"sub": "碎片化空间","detail": "刻意不建立连续的地理空间关系",
                     "keywords": ["fragmented space","碎片化","disorienting","空间混乱"]},
                ]
            },
            {
                "category": "空间转场",
                "subcategories": [
                    {"sub": "淡入淡出",  "detail": "画面渐黑渐亮，表示时间/空间间隔",
                     "keywords": ["fade in","fade out","淡入","淡出","渐显","渐隐"]},
                    {"sub": "叠化",      "detail": "前一画面渐隐同时后一画面渐显",
                     "keywords": ["dissolve","叠化","溶接","cross dissolve"]},
                    {"sub": "相似体转场","detail": "利用形状相似的物体做转场过渡",
                     "keywords": ["match dissolve","shape match","相似体","形体匹配"]},
                    {"sub": "动作转场",  "detail": "利用动作的连续性连接两个空间",
                     "keywords": ["action match","动作匹配","动作转场","whip pan"]},
                ]
            },
        ]
    },
    {
        "dimension": "叙事",
        "categories": [
            {
                "category": "因果剪辑",
                "subcategories": [
                    {"sub": "事件逻辑",  "detail": "按因果关系组织镜头，清晰展现事件链条",
                     "keywords": ["cause effect","因果","逻辑剪辑","continuity"]},
                ]
            },
            {
                "category": "动机剪辑",
                "subcategories": [
                    {"sub": "视觉驱动",  "detail": "画面内视觉元素引导剪辑点（视线/动作/颜色）",
                     "keywords": ["visual driven","视觉驱动","eyeline match"]},
                    {"sub": "声音驱动",  "detail": "声音变化引导画面切换",
                     "keywords": ["sound driven","声音驱动","audio lead"]},
                    {"sub": "情绪驱动",  "detail": "以角色情绪作为剪辑点的依据",
                     "keywords": ["emotion driven","情绪驱动","emotional cut"]},
                ]
            },
            {
                "category": "视点剪辑",
                "subcategories": [
                    {"sub": "客观视点",  "detail": "上帝般的中立观察视角",
                     "keywords": ["objective","客观","omniscient"]},
                    {"sub": "主观POV",   "detail": "镜头即角色眼睛所见",
                     "keywords": ["POV","point of view","主观","第一人称"]},
                    {"sub": "上帝视角",  "detail": "高空俯瞰的宏观叙事视点",
                     "keywords": ["god view","上帝视角","aerial","俯瞰"]},
                ]
            },
            {
                "category": "悬念剪辑",
                "subcategories": [
                    {"sub": "延迟揭示",  "detail": "延后呈现关键信息，让观众等待答案",
                     "keywords": ["delayed reveal","延迟揭示","slow reveal"]},
                    {"sub": "信息差",    "detail": "观众比剧中人知道更多，制造戏剧反讽",
                     "keywords": ["dramatic irony","信息差","观众知道更多"]},
                ]
            },
        ]
    },
    {
        "dimension": "节奏",
        "categories": [
            {
                "category": "快剪",
                "subcategories": [
                    {"sub": "紧张激烈",  "detail": "短镜头快速切换（≤2s/镜），制造紧迫感",
                     "keywords": ["fast cutting","fast-paced","快剪","rapid","intense"]},
                    {"sub": "动作快剪",  "detail": "打斗/追逐场景的密集剪辑",
                     "keywords": ["action cutting","动作剪辑","fight scene","追逐"]},
                ]
            },
            {
                "category": "慢剪",
                "subcategories": [
                    {"sub": "舒缓长镜",  "detail": "长镜头（≥6s），给观众呼吸空间",
                     "keywords": ["long take","长镜头","slow pace","舒缓","lingering"]},
                    {"sub": "沉重凝滞",  "detail": "极慢剪辑或静态构图，传达沉重情绪",
                     "keywords": ["heavy","weight","沉重","stillness","静态"]},
                ]
            },
            {
                "category": "节奏变化",
                "subcategories": [
                    {"sub": "加速",      "detail": "镜头渐次缩短，节奏越来快",
                     "keywords": ["accelerating","加速","渐快","building"]},
                    {"sub": "减速",      "detail": "镜头渐次延长，节奏放缓",
                     "keywords": ["decelerating","减速","渐慢","winding down"]},
                    {"sub": "停顿对比",  "detail": "快剪中插入一个极长的静默镜头",
                     "keywords": ["pause","停顿","freeze frame","静帧","beat"]},
                ]
            },
            {
                "category": "音乐节拍",
                "subcategories": [
                    {"sub": "节拍精准对齐","detail": "剪接点精准卡在音乐节拍上",
                     "keywords": ["beat sync","节拍对齐","cut to beat","rhythm edit"]},
                ]
            },
        ]
    },
    {
        "dimension": "视听",
        "categories": [
            {
                "category": "声画关系",
                "subcategories": [
                    {"sub": "声画同步",  "detail": "画面与声音来源一致，所见即所听",
                     "keywords": ["sync sound","声画同步","diegetic","lip sync"]},
                    {"sub": "声画分立",  "detail": "画面外的声音，观众看不到声源",
                     "keywords": ["sound separation","声画分立","off-screen sound"]},
                    {"sub": "声画对位",  "detail": "声音与画面表达相反情绪（欢乐画面+忧伤音乐）",
                     "keywords": ["counterpoint","对位","讽刺","contrast sound"]},
                ]
            },
            {
                "category": "声音转场",
                "subcategories": [
                    {"sub": "先声夺人",  "detail": "下一镜头的声音提前进入（J-cut）",
                     "keywords": ["sound advance","先声","J cut","audio lead"]},
                    {"sub": "声音延续",  "detail": "上一镜头的声音延续到下一镜头（L-cut）",
                     "keywords": ["sound linger","声音延续","L cut","audio tail"]},
                    {"sub": "声音桥",    "detail": "用持续的声音连接不同空间/时间的画面",
                     "keywords": ["sound bridge","声音桥","audio bridge"]},
                ]
            },
            {
                "category": "画面匹配",
                "subcategories": [
                    {"sub": "色彩连贯",  "detail": "相邻镜头色调一致，视觉流畅",
                     "keywords": ["color match","色彩匹配","color continuity"]},
                    {"sub": "光影连贯",  "detail": "光线方向和强度在相邻镜头中保持一致",
                     "keywords": ["lighting match","光影匹配"]},
                    {"sub": "构图对比",  "detail": "用构图的大反差制造视觉冲击",
                     "keywords": ["composition contrast","构图对比"]},
                ]
            },
        ]
    },
    {
        "dimension": "表现",
        "categories": [
            {
                "category": "表现蒙太奇",
                "subcategories": [
                    {"sub": "对比蒙太奇","detail": "穷/富、战争/和平等强烈对比画面并置",
                     "keywords": ["contrast montage","对比","juxtaposition"]},
                    {"sub": "隐喻蒙太奇","detail": "用意象画面暗示某种含义",
                     "keywords": ["metaphor montage","隐喻","symbolic"]},
                    {"sub": "象征蒙太奇","detail": "用具体画面代表抽象概念",
                     "keywords": ["symbol montage","象征","symbolism"]},
                    {"sub": "重复蒙太奇","detail": "反复出现同一画面/动作，强化主题",
                     "keywords": ["repetition","重复","recurring","motif"]},
                ]
            },
            {
                "category": "情绪剪辑",
                "subcategories": [
                    {"sub": "特写放大",  "detail": "关键时刻切到面部特写，放大微表情",
                     "keywords": ["close-up emotion","特写","表情","reaction shot"]},
                    {"sub": "空镜抒情",  "detail": "景物空镜头作为情绪延伸和呼吸空间",
                     "keywords": ["establishing shot emotion","空镜头","景观抒情","breathing room"]},
                ]
            },
        ]
    },
    {
        "dimension": "技术",
        "categories": [
            {
                "category": "无缝转场",
                "subcategories": [
                    {"sub": "遮挡转场",  "detail": "用物体遮挡镜头完成场景切换",
                     "keywords": ["wipe transition","遮挡","object wipe"]},
                    {"sub": "运动模糊转场","detail": "利用快速运动产生的模糊做转场",
                     "keywords": ["motion blur transition","运动模糊","smear"]},
                    {"sub": "数字特效转场","detail": "用morph/glitch等数字特效完成转场",
                     "keywords": ["digital transition","数字转场","morph","glitch"]},
                ]
            },
            {
                "category": "数字合成",
                "subcategories": [
                    {"sub": "分屏",      "detail": "同一画面中同时展示多个场景",
                     "keywords": ["split screen","分屏","split-screen"]},
                    {"sub": "叠印",      "detail": "透明叠加两层或多层画面",
                     "keywords": ["superimpose","叠印","double exposure","双重曝光"]},
                    {"sub": "绿幕抠像",  "detail": "色键抠像替换背景",
                     "keywords": ["green screen","chroma key","绿幕","抠像","keying"]},
                ]
            },
            {
                "category": "AI辅助",
                "subcategories": [
                    {"sub": "自动剪辑",  "detail": "AI 算法驱动的自动化剪辑",
                     "keywords": ["AI editing","auto edit","自动剪辑"]},
                    {"sub": "智能转场",  "detail": "AI 自动选择/生成最适合的转场效果",
                     "keywords": ["AI transition","智能转场"]},
                    {"sub": "画质修复",  "detail": "AI 超分/降噪/去模糊提升画质",
                     "keywords": ["upscale","超分","画质修复","enhance"]},
                ]
            },
        ]
    },
]


def get_all_taxonomy_entries():
    """展平 7 维分类树为行列表"""
    rows = []
    for dim in TAXONOMY:
        for cat in dim["categories"]:
            for sub in cat["subcategories"]:
                rows.append({
                    "dimension": dim["dimension"],
                    "category": cat["category"],
                    "subcategory": sub["sub"],
                    "detail": sub["detail"],
                    "keywords": sub["keywords"],
                })
    return rows


def seed_taxonomy(db_config):
    """预填 taxonomy 表到 MySQL，已存在的跳过（幂等）"""
    import pymysql
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()
    entries = get_all_taxonomy_entries()
    count = 0
    for e in entries:
        cursor.execute(
            "SELECT id FROM technique_taxonomy WHERE dimension=%s AND category=%s AND subcategory=%s",
            (e["dimension"], e["category"], e["subcategory"])
        )
        if cursor.fetchone() is None:
            cursor.execute(
                """INSERT INTO technique_taxonomy (dimension, category, subcategory, detail, keywords)
                   VALUES (%s, %s, %s, %s, %s)""",
                (e["dimension"], e["category"], e["subcategory"],
                 e["detail"], json.dumps(e["keywords"], ensure_ascii=False))
            )
            count += 1
    conn.commit()
    conn.close()
    return count
```

在 taxonomy.py 顶部加上 `import json`。

- [ ] **Step 5: 启动 MySQL 并建表**

```bash
docker-compose up -d mysql
```

等 10 秒 MySQL 就绪后验证：

```bash
docker exec clip_trends_mysql mysql -u clip_trends -p"$MYSQL_PASSWORD" -e "SHOW TABLES;" clip_trends
```

Expected: 看到 6 张表。

- [ ] **Step 6: 提交**

```bash
git add clip_trends/sql/schema.sql clip_trends/config.py clip_trends/taxonomy.py docker-compose.yml
git commit -m "feat(clip_trends): MySQL schema + taxonomy + config foundation"
```

---

### Task 2: 数据库连接池 + CRUD 封装

**Files:**
- Create: `clip_trends/db.py`

- [ ] **Step 1: 创建 db.py**

```python
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
        # 聚合当天的技法统计
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
    status = 'failed' if errors else ('success' if videos_new > 0 else 'success')
    if errors and videos_total > 0:
        status = 'partial'
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
        # 找高频技法组合
        cur.execute("""
            SELECT GROUP_CONCAT(DISTINCT vt.taxonomy_id ORDER BY vt.taxonomy_id) as combo,
                   COUNT(DISTINCT vt.video_id) as cnt
            FROM video_techniques vt
            WHERE DATE(vt.created_at) >= CURDATE() - INTERVAL 7 DAY
            GROUP BY vt.video_id
            HAVING cnt >= 2
        """)
        # 按 combo 聚合，找出出现 ≥3 次的组合
        combo_counts = {}
        for row in cur.fetchall():
            combo = row[0]
            combo_counts[combo] = combo_counts.get(combo, 0) + 1

        for combo, count in combo_counts.items():
            if count >= 3:
                tax_ids = [int(x) for x in combo.split(',')]
                # 检查模板是否已存在
                tax_ids_json = json.dumps(tax_ids)
                cur.execute(
                    "SELECT id FROM editing_templates WHERE taxonomy_ids_json=%s",
                    (tax_ids_json,)
                )
                if not cur.fetchone():
                    # 拼接模板名称
                    cur.execute(
                        "SELECT CONCAT(dimension,'/',category,'/',subcategory) as full_name FROM technique_taxonomy WHERE id IN (%s)" % combo,
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
```

- [ ] **Step 2: 提交**

```bash
git add clip_trends/db.py
git commit -m "feat(clip_trends): MySQL connection pool + CRUD"
```

---

### Task 3: 爬虫基类 + 四站爬虫

**Files:**
- Create: `clip_trends/crawlers/__init__.py`
- Create: `clip_trends/crawlers/base.py`
- Create: `clip_trends/crawlers/pexels.py`
- Create: `clip_trends/crawlers/pixabay.py`
- Create: `clip_trends/crawlers/coverr.py`
- Create: `clip_trends/crawlers/mixkit.py`

- [ ] **Step 1: 创建 `__init__.py`**

```python
# clip_trends/crawlers/__init__.py
from .pexels import PexelsCrawler
from .pixabay import PixabayCrawler
from .coverr import CoverrCrawler
from .mixkit import MixkitCrawler

CRAWLERS = {
    'pexels': PexelsCrawler,
    'pixabay': PixabayCrawler,
    'coverr': CoverrCrawler,
    'mixkit': MixkitCrawler,
}
```

- [ ] **Step 2: 创建 base.py**

```python
# clip_trends/crawlers/base.py
import time, requests, hashlib, os
from dataclasses import dataclass
from typing import Optional
from config import CRAWL_CONFIG, VIDEO_ANALYSIS


@dataclass
class RawVideo:
    site: str
    source_url: str
    source_id: Optional[str]
    title: str
    thumbnail_url: Optional[str]
    duration_sec: Optional[float]
    resolution: Optional[str]
    tags: list
    description: Optional[str]
    popularity_score: float


class BaseCrawler:
    site_name: str = "base"

    def __init__(self, config: dict = None):
        cfg = config or CRAWL_CONFIG
        self.max_per_site = cfg['max_per_site']
        self.request_interval = cfg['request_interval']
        self.request_timeout = cfg['request_timeout']
        self.retry_times = cfg['retry_times']
        self.retry_backoff = cfg['retry_backoff']
        self._last_request = 0

    def _rate_limit(self):
        elapsed = time.time() - self._last_request
        if elapsed < self.request_interval:
            time.sleep(self.request_interval - elapsed)
        self._last_request = time.time()

    def _get(self, url, params=None, headers=None):
        """带限速+重试的 GET"""
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        if headers:
            default_headers.update(headers)

        last_error = None
        for attempt in range(self.retry_times + 1):
            self._rate_limit()
            try:
                resp = requests.get(
                    url, params=params, headers=default_headers,
                    timeout=self.request_timeout
                )
                resp.raise_for_status()
                return resp
            except requests.RequestException as e:
                last_error = e
                if attempt < self.retry_times:
                    time.sleep(self.retry_backoff[attempt])
        raise last_error

    def _head_content_length(self, url: str) -> Optional[int]:
        """HEAD 请求探测文件大小"""
        try:
            resp = requests.head(url, timeout=10)
            length = resp.headers.get('Content-Length')
            return int(length) if length else None
        except Exception:
            return None

    def _download_video(self, url: str, dest_path: str,
                        max_size_mb: int = None, timeout: int = None) -> bool:
        """下载视频到临时路径，返回是否成功"""
        max_size_mb = max_size_mb or VIDEO_ANALYSIS['max_file_size_mb']
        timeout = timeout or VIDEO_ANALYSIS['download_timeout']

        # 检查文件大小
        size = self._head_content_length(url)
        if size and size > max_size_mb * 1024 * 1024:
            return False

        try:
            resp = requests.get(url, stream=True, timeout=timeout)
            resp.raise_for_status()
            downloaded = 0
            max_bytes = max_size_mb * 1024 * 1024
            with open(dest_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if downloaded > max_bytes:
                        f.close()
                        os.remove(dest_path)
                        return False
            return True
        except Exception:
            if os.path.exists(dest_path):
                os.remove(dest_path)
            return False

    def crawl(self) -> list:
        raise NotImplementedError
```

- [ ] **Step 3: 创建 pexels.py**

```python
# clip_trends/crawlers/pexels.py
from .base import BaseCrawler, RawVideo
from config import PEXELS_API_KEY


class PexelsCrawler(BaseCrawler):
    site_name = "pexels"

    def crawl(self) -> list[RawVideo]:
        videos = []
        headers = {'Authorization': PEXELS_API_KEY}
        resp = self._get(
            'https://api.pexels.com/videos/popular',
            params={'per_page': self.max_per_site},
            headers=headers
        )
        data = resp.json()
        for i, v in enumerate(data.get('videos', [])):
            # 取分辨率最高的视频文件
            video_files = sorted(v.get('video_files', []),
                                 key=lambda x: x.get('width', 0) or 0, reverse=True)
            video_url = video_files[0]['link'] if video_files else v.get('url', '')
            resolution = f"{video_files[0].get('width',0)}x{video_files[0].get('height',0)}" if video_files else None

            videos.append(RawVideo(
                site='pexels',
                source_url=video_url,
                source_id=str(v.get('id')),
                title=v.get('url', '').split('/')[-2].replace('-', ' ').title(),
                thumbnail_url=v.get('image'),
                duration_sec=v.get('duration'),
                resolution=resolution,
                tags=[t.lower() for t in v.get('tags', [])] if isinstance(v.get('tags', []), list)
                     else [v.get('tags', '')],
                description=v.get('url', ''),
                popularity_score=100 * (1 - i / max(self.max_per_site, 1)),
            ))
        return videos
```

- [ ] **Step 4: 创建 pixabay.py**

```python
# clip_trends/crawlers/pixabay.py
from .base import BaseCrawler, RawVideo
from config import PIXABAY_API_KEY


class PixabayCrawler(BaseCrawler):
    site_name = "pixabay"

    def crawl(self) -> list[RawVideo]:
        videos = []
        resp = self._get('https://pixabay.com/api/videos/', params={
            'key': PIXABAY_API_KEY,
            'order': 'popular',
            'per_page': self.max_per_site,
            'safesearch': 'true',
        })
        data = resp.json()
        for i, v in enumerate(data.get('hits', [])):
            # 取最高分辨率
            video_size = v.get('videos', {}).get('large') or v.get('videos', {}).get('medium')
            video_url = video_size.get('url', '') if video_size else ''
            resolution = f"{video_size.get('width',0)}x{video_size.get('height',0)}" if video_size else None

            tags = v.get('tags', '').split(', ') if isinstance(v.get('tags'), str) else v.get('tags', [])

            videos.append(RawVideo(
                site='pixabay',
                source_url=video_url,
                source_id=str(v.get('id')),
                title=v.get('tags', '').split(',')[0].strip() if v.get('tags') else '',
                thumbnail_url=v.get('videos', {}).get('large', {}).get('thumbnail'),
                duration_sec=v.get('duration'),
                resolution=resolution,
                tags=[t.lower().strip() for t in tags] if tags else [],
                description=v.get('tags', ''),
                popularity_score=100 * (1 - i / max(self.max_per_site, 1)),
            ))
        return videos
```

- [ ] **Step 5: 创建 coverr.py**

```python
# clip_trends/crawlers/coverr.py
from bs4 import BeautifulSoup
from .base import BaseCrawler, RawVideo


class CoverrCrawler(BaseCrawler):
    site_name = "coverr"

    def crawl(self) -> list[RawVideo]:
        videos = []
        resp = self._get('https://coverr.co/')
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Coverr 用 JS 渲染，尝试从页面内嵌 JSON 提取
        scripts = soup.find_all('script')
        import re, json
        for script in scripts:
            if script.string and 'window.__INITIAL_STATE__' in (script.string or ''):
                # 提取 JSON
                match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', script.string, re.DOTALL)
                if match:
                    try:
                        state = json.loads(match.group(1))
                        all_videos = (state.get('videos', {}).get('list', []) or
                                      state.get('videos', {}).get('popular', []))
                        for i, v in enumerate(all_videos[:self.max_per_site]):
                            videos.append(RawVideo(
                                site='coverr',
                                source_url=v.get('url', '') or v.get('videoUrl', ''),
                                source_id=v.get('id', '') or v.get('_id', ''),
                                title=v.get('title', ''),
                                thumbnail_url=v.get('poster', '') or v.get('thumbnail', ''),
                                duration_sec=float(v.get('duration', 0)) if v.get('duration') else None,
                                resolution=None,
                                tags=[t.lower().strip() for t in (v.get('tags', []) or [])],
                                description=v.get('description', ''),
                                popularity_score=100 * (1 - i / max(self.max_per_site, 1)),
                            ))
                    except (json.JSONDecodeError, KeyError):
                        pass
                    break

        return videos
```

- [ ] **Step 6: 创建 mixkit.py**

```python
# clip_trends/crawlers/mixkit.py
from bs4 import BeautifulSoup
from .base import BaseCrawler, RawVideo


class MixkitCrawler(BaseCrawler):
    site_name = "mixkit"

    def crawl(self) -> list[RawVideo]:
        videos = []
        resp = self._get('https://mixkit.co/free-stock-video/')
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Mixkit 视频卡片
        cards = soup.select('div.item-grid__card, a[href*="/free-stock-video/"]')
        seen_urls = set()
        count = 0
        for card in cards:
            if count >= self.max_per_site:
                break

            # 找到视频链接
            link = card.get('href', '') if card.name == 'a' else ''
            if not link:
                a_tag = card.find('a', href=True)
                if a_tag:
                    link = a_tag['href']

            if not link or '/free-stock-video/' not in link:
                continue

            full_url = link if link.startswith('http') else f'https://mixkit.co{link}'
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            # 获取缩略图和标题
            img = card.find('img')
            title = img.get('alt', '') if img else ''
            thumbnail = img.get('src', '') or img.get('data-src', '') if img else ''

            # 获取标签
            tags_el = card.select('.item-grid-card__tags span, .tags span, [class*="tag"]')
            tags = [t.get_text(strip=True).lower() for t in tags_el if t.get_text(strip=True)]

            videos.append(RawVideo(
                site='mixkit',
                source_url=full_url,
                source_id=None,  # 用 URL SHA256
                title=title,
                thumbnail_url=thumbnail,
                duration_sec=None,
                resolution=None,
                tags=tags,
                description=title,
                popularity_score=100 * (1 - count / max(self.max_per_site, 1)),
            ))
            count += 1

        return videos
```

- [ ] **Step 7: 提交**

```bash
git add clip_trends/crawlers/
git commit -m "feat(clip_trends): 4-site crawler base + implementations"
```

---

### Task 4: 视频分析器（ffmpeg + ffprobe）

**Files:**
- Create: `clip_trends/video_analyzer.py`

- [ ] **Step 1: 创建 video_analyzer.py**

```python
# clip_trends/video_analyzer.py
"""ffmpeg 下载+抽帧 + ffprobe 音频分析"""
import os, glob, subprocess, json, tempfile
from config import VIDEO_ANALYSIS


def analyze_video(video_url: str, download_func) -> dict | None:
    """
    完整视频分析流水线，返回:
    {
        'frames': ['/path/frame_001.jpg', ...],
        'duration': 30.5,       # 秒
        'resolution': '1920x1080',
        'fps': 24.0,
        'audio': {'has_audio': True, 'rms_db': -18.5, 'peak_db': -3.2},
        'frame_analyses': [...], # Qwen-VL 填充
    }
    失败返回 None
    """
    temp_dir = tempfile.mkdtemp(dir=VIDEO_ANALYSIS.get('download_dir', 'clip_trends/temp_videos/'))
    try:
        video_path = os.path.join(temp_dir, 'video.mp4')

        # 1. 下载完整视频
        success = download_func(video_url, video_path)
        if not success:
            return None

        # 2. ffprobe 提取元数据
        duration, resolution, fps = _ffprobe_meta(video_path)
        if duration is None or duration <= 0:
            return None

        # 3. ffprobe 提取音频特征
        audio_info = _ffprobe_audio(video_path)

        # 4. ffmpeg 抽帧：每 3 秒 1 帧
        frame_pattern = os.path.join(temp_dir, 'frame_%03d.jpg')
        subprocess.run([
            'ffmpeg', '-y', '-i', video_path,
            '-vf', f'fps=1/{VIDEO_ANALYSIS["frame_interval"]}',
            '-qscale:v', '2',
            frame_pattern
        ], capture_output=True, timeout=120)

        frames = sorted(glob.glob(os.path.join(temp_dir, 'frame_*.jpg')))

        # 5. 删除原始视频（保留抽帧 jpg）
        if os.path.exists(video_path):
            os.remove(video_path)

        return {
            'frames': frames,
            'duration': duration,
            'resolution': resolution,
            'fps': fps,
            'audio': audio_info,
            'temp_dir': temp_dir,
        }
    except Exception:
        return None


def _ffprobe_meta(video_path: str) -> tuple:
    """返回 (duration_sec, resolution_str, fps)"""
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', video_path
        ], capture_output=True, text=True, timeout=30)
        data = json.loads(result.stdout)

        duration = float(data.get('format', {}).get('duration', 0))

        video_stream = None
        for s in data.get('streams', []):
            if s.get('codec_type') == 'video':
                video_stream = s
                break

        if video_stream:
            width = video_stream.get('width', 0)
            height = video_stream.get('height', 0)
            resolution = f'{width}x{height}' if width and height else 'unknown'
            # fps: 分数形式 "24/1" 或 "30000/1001"
            fps_str = video_stream.get('r_frame_rate', '0/1')
            num, den = fps_str.split('/')
            fps = float(num) / float(den) if float(den) != 0 else 0
        else:
            resolution = 'unknown'
            fps = 0

        return duration, resolution, fps
    except Exception:
        return None, 'unknown', 0


def _ffprobe_audio(video_path: str) -> dict:
    """提取音频特征"""
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_streams', video_path
        ], capture_output=True, text=True, timeout=30)
        data = json.loads(result.stdout)

        has_audio = any(s.get('codec_type') == 'audio' for s in data.get('streams', []))
        if not has_audio:
            return {'has_audio': False, 'rms_db': None, 'peak_db': None}

        # 用 ffmpeg volumedetect 获取响度
        result2 = subprocess.run([
            'ffmpeg', '-i', video_path,
            '-af', 'volumedetect',
            '-vn', '-sn', '-dn',
            '-f', 'null', 'NUL' if os.name == 'nt' else '/dev/null'
        ], capture_output=True, text=True, timeout=60)

        import re
        mean_match = re.search(r'mean_volume:\s*(-?[\d.]+)', result2.stderr + result2.stdout)
        max_match = re.search(r'max_volume:\s*(-?[\d.]+)', result2.stderr + result2.stdout)

        return {
            'has_audio': True,
            'rms_db': float(mean_match.group(1)) if mean_match else None,
            'peak_db': float(max_match.group(1)) if max_match else None,
        }
    except Exception:
        return {'has_audio': False, 'rms_db': None, 'peak_db': None}


def cleanup_temp(temp_dir: str):
    """清理临时目录"""
    import shutil
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)
```

- [ ] **Step 2: 提交**

```bash
git add clip_trends/video_analyzer.py
git commit -m "feat(clip_trends): ffmpeg video download + frame extraction + audio analysis"
```

---

### Task 5: Qwen-VL 客户端

**Files:**
- Create: `clip_trends/qwen_client.py`

- [ ] **Step 1: 创建 qwen_client.py**

```python
# clip_trends/qwen_client.py
"""Qwen-VL API 封装：逐帧分析 + 帧间对比 + 综合标签映射"""
import json, base64, time
from openai import OpenAI
from config import DASHSCOPE_API_KEY, VIDEO_ANALYSIS


client = OpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
)

QWEN_MODEL = VIDEO_ANALYSIS.get('qwen_model', 'qwen-vl-max')


def _encode_image(path: str) -> str:
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode()


def analyze_frame(frame_path: str) -> dict:
    """分析单帧画面 → 视觉要素 JSON"""
    prompt = """分析这张视频关键帧，描述以下视觉要素，仅输出JSON：
{
  "shot_size": "远景/全景/中景/近景/特写/大特写",
  "camera_angle": "平视/俯拍/仰拍/鸟瞰",
  "composition": "三分法/对称/引导线/框架/负空间/中央 选一",
  "color_tone": "暖/冷/中性",
  "color_temp_k": 5600,
  "lighting": "高调/低调/剪影/自然光",
  "main_light_direction": "左/右/上/正面/背光/无",
  "subject_count": 1,
  "subject_action": "简短描述主体在做什么（中文10字以内）",
  "depth_of_field": "浅/深/正常"
}"""
    try:
        resp = client.chat.completions.create(
            model=QWEN_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_encode_image(frame_path)}"}},
                    {"type": "text", "text": prompt},
                ]
            }],
            max_tokens=500,
            temperature=0.1,
        )
        content = resp.choices[0].message.content.strip()
        # 清理 markdown ```json 包裹
        if content.startswith('```'):
            content = content.split('\n', 1)[1]
            if content.endswith('```'):
                content = content[:-3]
        return json.loads(content)
    except Exception as e:
        return {"error": str(e)}


def compare_frames(frame_a_desc: dict, frame_b_desc: dict) -> dict:
    """帧间对比 → 转场类型 + 节奏感知"""
    prompt = f"""以下两张关键帧（间隔3秒）的视觉分析：
帧A: {json.dumps(frame_a_desc, ensure_ascii=False)}
帧B: {json.dumps(frame_b_desc, ensure_ascii=False)}

对比分析两张帧之间的变化，仅输出JSON：
{{
  "transition": "硬切/淡入淡出/叠化/滑入/闪白/无明显转场",
  "camera_change": "同角度/30度以上变化/越轴/无明显变化",
  "shot_size_change": "推进/拉远/同景别/跳级/无明显变化",
  "subject_movement": "左移/右移/前移/后移/静止/画外移动",
  "pace_perception": "快/中/慢",
  "analysis": "一句话描述帧间变化（中文15字以内）"
}}"""
    try:
        resp = client.chat.completions.create(
            model=QWEN_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.1,
        )
        content = resp.choices[0].message.content.strip()
        if content.startswith('```'):
            content = content.split('\n', 1)[1]
            if content.endswith('```'):
                content = content[:-3]
        return json.loads(content)
    except Exception as e:
        return {"error": str(e)}


def map_to_taxonomy(frame_analyses: list, comparisons: list,
                    audio_info: dict, tags: list,
                    taxonomy_entries: list) -> list[dict]:
    """综合所有数据 → 7维 taxonomy 标签映射"""
    prompt = f"""你是电影剪辑分析专家。请根据以下视频多帧分析数据，从7个维度匹配适用的剪辑技法标签。

=== 多帧画面分析 ===
{json.dumps(frame_analyses, ensure_ascii=False, indent=2)[:2000]}

=== 帧间对比 ===
{json.dumps(comparisons, ensure_ascii=False, indent=2)[:1000]}

=== 音频特征 ===
{json.dumps(audio_info, ensure_ascii=False)}

=== 原始标签 ===
{tags[:20]}

=== 7维分类体系（完整 taxonomy）===
{json.dumps([{
    "id": t["id"],
    "dimension": t["dimension"],
    "category": t["category"],
    "subcategory": t["subcategory"],
    "detail": t["detail"]
} for t in taxonomy_entries], ensure_ascii=False)}

请根据以上数据，匹配适用的 clip_trends taxonomy。仅输出JSON数组：
[{{"taxonomy_id": 3, "evidence": "基于帧2→帧3的分析发现跳切特征", "confidence": 0.85}}, ...]
confidence 0-1。每个维度最多匹配3个最相关的 subcategory。
如果没有足够证据，不要硬匹配。只输出有把握的。"""
    try:
        resp = client.chat.completions.create(
            model='deepseek-v4-pro',  # 转发给 DeepSeek 做综合推理
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.2,
        )
        content = resp.choices[0].message.content.strip()
        if content.startswith('```'):
            content = content.split('\n', 1)[1]
            if content.endswith('```'):
                content = content[:-3]
        results = json.loads(content)
        for r in results:
            r['method'] = 'qwen-vl'
        return results
    except Exception:
        return []


def analyze_video_frames(analysis_result: dict, taxonomy_entries: list) -> list[dict]:
    """
    完整的 Qwen-VL 视频分析：
    1. 逐帧分析
    2. 帧间对比
    3. 综合映射 taxonomy
    返回 video_techniques 列表
    """
    frames = analysis_result.get('frames', [])
    if not frames:
        return []

    # 1. 逐帧分析（每帧之间隔 1 秒避免 API 限流）
    frame_analyses = []
    for fp in frames:
        result = analyze_frame(fp)
        if 'error' not in result:
            frame_analyses.append(result)
        time.sleep(0.5)

    if not frame_analyses:
        return []

    # 2. 帧间对比
    comparisons = []
    for i in range(len(frame_analyses) - 1):
        cmp = compare_frames(frame_analyses[i], frame_analyses[i + 1])
        if 'error' not in cmp:
            comparisons.append(cmp)
        time.sleep(0.3)

    # 3. 综合映射 taxonomy
    techniques = map_to_taxonomy(
        frame_analyses, comparisons,
        analysis_result.get('audio', {}),
        analysis_result.get('tags', []),
        taxonomy_entries
    )

    return techniques
```

- [ ] **Step 2: 提交**

```bash
git add clip_trends/qwen_client.py
git commit -m "feat(clip_trends): Qwen-VL frame analysis + taxonomy mapping"
```

---

### Task 6: 分类编排器（classifier.py）

**Files:**
- Create: `clip_trends/classifier.py`

- [ ] **Step 1: 创建 classifier.py**

```python
# clip_trends/classifier.py
"""分类编排：Qwen-VL 主路径 → 规则降级 → LLM 兜底"""
import json
from config import DASHSCOPE_API_KEY
from db import get_conn, save_techniques
from taxonomy import TAXONOMY, get_all_taxonomy_entries
from video_analyzer import analyze_video, cleanup_temp
from qwen_client import analyze_video_frames


# 预加载 taxonomy entries 列表（含 id）
_taxonomy_cache = None


def _get_taxonomy_with_ids():
    global _taxonomy_cache
    if _taxonomy_cache is not None:
        return _taxonomy_cache
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, dimension, category, subcategory, detail, keywords FROM technique_taxonomy")
        rows = cur.fetchall()
        _taxonomy_cache = [
            {"id": r[0], "dimension": r[1], "category": r[2],
             "subcategory": r[3], "detail": r[4], "keywords": json.loads(r[5]) if isinstance(r[5], str) else r[5]}
            for r in rows
        ]
    return _taxonomy_cache


def classify_by_rules(tags: list, title: str = '', description: str = '') -> list[dict]:
    """规则引擎：关键词匹配 taxonomy"""
    entries = _get_taxonomy_with_ids()
    text = ' '.join((tags or []) + [title, description or '']).lower()
    results = []
    for entry in entries:
        keywords = entry.get('keywords', [])
        for kw in keywords:
            if kw.lower() in text:
                results.append({
                    'taxonomy_id': entry['id'],
                    'confidence': 0.7,
                    'evidence': f'关键词匹配: "{kw}"',
                    'method': 'rule',
                })
                break  # 一个 entry 只记录一次
    return results


def classify_by_llm_text(video_info: dict) -> list[dict]:
    """DeepSeek 文本兜底：基于 tags + title + description"""
    try:
        from openai import OpenAI
        from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        entries = _get_taxonomy_with_ids()

        prompt = f"""你是剪辑分析专家。根据视频标签和描述，从以下分类体系匹配适用的剪辑技法。
视频信息: title={video_info.get('title')}, tags={video_info.get('tags', [])}, description={video_info.get('description', '')}
分类体系: {json.dumps([{{
    "id": e["id"], "dimension": e["dimension"],
    "category": e["category"], "subcategory": e["subcategory"],
    "detail": e["detail"]
}} for e in entries], ensure_ascii=False)}

输出JSON数组: [{{"taxonomy_id": 1, "evidence": "...", "confidence": 0.8}}, ...]"""

        resp = client.chat.completions.create(
            model='deepseek-v4-pro',
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.1,
        )
        content = resp.choices[0].message.content.strip()
        if content.startswith('```'):
            content = content.split('\n', 1)[1].split('```')[0]
        results = json.loads(content)
        for r in results:
            r['method'] = 'llm'
        return results
    except Exception:
        return []


def classify(video_record: dict, download_func) -> int:
    """
    主分类编排，返回命中的技法数。
    video_record: {'id': 123, 'source_url': '...', 'tags': [...], 'title': '...', 'description': '...'}
    """
    video_id = video_record['id']
    techniques = []
    temp_dir = None

    # 路径1: Qwen-VL 抽帧分析（优先）
    if DASHSCOPE_API_KEY:
        try:
            analysis = analyze_video(video_record['source_url'], download_func)
            if analysis:
                analysis['tags'] = video_record.get('tags', [])
                temp_dir = analysis.get('temp_dir')
                techniques = analyze_video_frames(analysis, _get_taxonomy_with_ids())
        except Exception:
            pass

    # 路径2: 若 Qwen-VL 无结果，尝试规则匹配
    if not techniques:
        techniques = classify_by_rules(
            video_record.get('tags', []),
            video_record.get('title', ''),
            video_record.get('description', '')
        )

    # 路径3: 规则也没结果，LLM 文本兜底
    if not techniques:
        techniques = classify_by_llm_text(video_record)

    # 保存
    if techniques:
        save_techniques(video_id, techniques)

    # 清理临时文件
    if temp_dir:
        cleanup_temp(temp_dir)

    return len(techniques)
```

- [ ] **Step 2: 提交**

```bash
git add clip_trends/classifier.py
git commit -m "feat(clip_trends): classification orchestrator with 3-tier fallback"
```

---

### Task 7: 调度器 + CLI 入口

**Files:**
- Create: `clip_trends/scheduler.py`
- Create: `clip_trends/main.py`
- Create: `clip_trends/requirements.txt`

- [ ] **Step 1: 创建 scheduler.py**

```python
# clip_trends/scheduler.py
"""APScheduler 每日定时任务"""
from apscheduler.schedulers.background import BackgroundScheduler
from crawlers import CRAWLERS
from db import upsert_videos, start_crawl_log, finish_crawl_log
from classifier import classify
from crawlers.base import BaseCrawler
from config import CRAWL_CONFIG


scheduler = BackgroundScheduler()


def run_crawl_job():
    """每日全量爬取 + 分析"""
    print(f"[scheduler] 开始每日爬取...")
    for site_name, crawler_cls in CRAWLERS.items():
        log_id = start_crawl_log(site_name)
        errors = []
        try:
            crawler: BaseCrawler = crawler_cls(CRAWL_CONFIG)
            raw_videos = crawler.crawl()
            new_ids = upsert_videos(raw_videos)

            # 建立 source_id → RawVideo 映射，匹配新插入的视频
            rv_map = {}
            for rv in raw_videos:
                sid = rv.source_id or __import__('hashlib').sha256(
                    rv.source_url.encode()).hexdigest()[:32]
                rv_map[sid] = rv

            for vid_id in new_ids:
                # 从数据库回查 source_id
                from db import get_conn
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
    from db import refresh_daily_trends, extract_editing_templates
    refresh_daily_trends()
    extract_editing_templates()
    print(f"[scheduler] 每日趋势更新完成")


def start_scheduler():
    scheduler.add_job(run_crawl_job, 'cron', hour=2, minute=0, id='daily_crawl')
    scheduler.start()
    print("[scheduler] 定时任务已注册: 每天凌晨 2:00")
```

- [ ] **Step 2: 创建 main.py**

```python
# clip_trends/main.py
"""CLI 入口: python main.py --once  |  python main.py --daemon"""
import sys, os
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
```

- [ ] **Step 3: 创建 requirements.txt**

```
requests>=2.31
beautifulsoup4>=4.12
pymysql>=1.1
dbutils>=3.1
apscheduler>=3.10
openai>=1.55
python-dotenv>=1.0
```

- [ ] **Step 4: 安装依赖**

```bash
pip install -r clip_trends/requirements.txt
```

- [ ] **Step 5: 提交**

```bash
git add clip_trends/scheduler.py clip_trends/main.py clip_trends/requirements.txt
git commit -m "feat(clip_trends): scheduler + CLI entry + dependencies"
```

---

### Task 8: 智演助手集成 — trend_service + 路由 + Prompt 注入

**Files:**
- Create: `services/trend_service.py`
- Modify: `app.py`
- Modify: `services/llm_service.py`

- [ ] **Step 1: 创建 services/trend_service.py**

```python
# services/trend_service.py
"""智演助手侧 — MySQL 只读查询接口"""
import pymysql, os, json
from dbutils.pooled_db import PooledDB
from dotenv import load_dotenv

load_dotenv()

_mysql_config = {
    'host': os.environ.get('MYSQL_HOST', 'localhost'),
    'port': int(os.environ.get('MYSQL_PORT', 3306)),
    'user': os.environ.get('MYSQL_USER', 'clip_trends'),
    'password': os.environ.get('MYSQL_PASSWORD', ''),
    'database': os.environ.get('MYSQL_DATABASE', 'clip_trends'),
    'charset': 'utf8mb4',
}

# 懒加载连接池
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
    except Exception:
        return []


def get_trending_techniques(dimension=None, limit=10):
    """本周最热技法"""
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
    """关键词搜索技法"""
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
    """返回可注入 LLM System Prompt 的文案片段"""
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
```

- [ ] **Step 2: app.py 添加 /api/trends 路由**

在 `app.py` 的 import 区域添加：

```python
from services.trend_service import get_trending_techniques, search_techniques
```

在 app.py 的路由区域（如 `/api/upload` 附近）添加：

```python
@app.route('/api/trends')
def api_trends():
    """剪辑趋势查询 — Token 鉴权"""
    token = request.headers.get('X-Access-Token', '')
    if token != ACCESS_TOKEN:
        return jsonify({'error': 'Unauthorized'}), 401

    dim = request.args.get('dimension')
    limit = min(int(request.args.get('limit', 10)), 50)
    search = request.args.get('search', '').strip()

    if search:
        results = search_techniques(search, [dim] if dim else None, limit)
    else:
        results = get_trending_techniques(dim, limit)

    # 序列化 JSON 字段
    for r in results:
        if 'sample_video_ids' in r and isinstance(r['sample_video_ids'], str):
            r['sample_video_ids'] = json.loads(r['sample_video_ids'])

    return jsonify(results)
```

- [ ] **Step 3: llm_service.py 注入趋势文案**

在 `SHOT_DESIGN_AUTO_SYSTEM` 字符串末尾的 `只输出JSON。"""` 之前追加：

```python
=== 本周热点剪辑趋势 ===
{trending_context}

在分镜设计中参考以上趋势，融入适合本故事风格的流行技法。
```

在 `design_shots_from_document()` 函数中，调用 LLM 前动态填充：

```python
# 在 design_shots_from_document() 函数中，调用 LLM 前动态填充：
try:
    from trend_service import get_weekly_trend_context
    trending_context = get_weekly_trend_context()
except Exception:
    trending_context = "（暂无趋势数据）"

if mode == 'auto':
    system_prompt = SHOT_DESIGN_AUTO_SYSTEM.replace('{trending_context}', trending_context)
else:
    system_prompt = SHOT_DESIGN_SYSTEM  # 半自动模式不注入趋势
```

- [ ] **Step 4: 提交**

```bash
git add services/trend_service.py app.py services/llm_service.py
git commit -m "feat: trend_service + /api/trends route + LLM prompt injection"
```

---

### Task 9: 前端"剪辑趋势"面板

**Files:**
- Modify: `index.html`
- Modify: `script.js`
- Modify: `styles.css`

- [ ] **Step 1: index.html 添加趋势面板**

在配置面板下方（`config-panel` 结束标签后）添加：

```html
<!-- 剪辑趋势面板 -->
<div class="trends-section" id="trendsSection">
  <div class="trends-header" id="trendsToggle">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
      <polyline points="17 6 23 6 23 12"/>
    </svg>
    <span data-i18n="trends_title">剪辑趋势</span>
    <span class="trends-badge" id="trendsBadge">--</span>
    <svg class="trends-chevron" id="trendsChevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <polyline points="6 9 12 15 18 9"/>
    </svg>
  </div>
  <div class="trends-body" id="trendsBody" style="display:none;">
    <div class="trends-filters">
      <select id="trendsDimFilter">
        <option value="" data-i18n="trends_all_dim">全部维度</option>
        <option value="时间">时间</option>
        <option value="空间">空间</option>
        <option value="叙事">叙事</option>
        <option value="节奏">节奏</option>
        <option value="视听">视听</option>
        <option value="表现">表现</option>
        <option value="技术">技术</option>
      </select>
      <input type="text" id="trendsSearch" data-i18n-placeholder="trends_search_placeholder" placeholder="搜索技法..." />
    </div>
    <div class="trends-list" id="trendsList">
      <div class="trends-empty" data-i18n="trends_loading">加载中...</div>
    </div>
  </div>
</div>
```

- [ ] **Step 2: script.js 添加趋势面板交互**

```javascript
// === 剪辑趋势面板 ===

const trendsToggle = document.getElementById('trendsToggle');
const trendsBody = document.getElementById('trendsBody');
const trendsChevron = document.getElementById('trendsChevron');

if (trendsToggle) {
  trendsToggle.addEventListener('click', () => {
    const isOpen = trendsBody.style.display !== 'none';
    trendsBody.style.display = isOpen ? 'none' : 'block';
    trendsChevron.style.transform = isOpen ? 'rotate(0deg)' : 'rotate(180deg)';
    if (!isOpen) loadTrends();
  });
}

async function loadTrends() {
  const dim = document.getElementById('trendsDimFilter')?.value || '';
  const search = document.getElementById('trendsSearch')?.value.trim() || '';
  const list = document.getElementById('trendsList');
  const badge = document.getElementById('trendsBadge');
  if (!list) return;

  list.innerHTML = `<div class="trends-empty">${t('trends_loading')}</div>`;

  try {
    let url = `/api/trends?limit=12`;
    if (dim) url += `&dimension=${encodeURIComponent(dim)}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;

    const resp = await fetch(url, {
      headers: { 'X-Access-Token': localStorage.getItem('access_token') || '' }
    });

    if (!resp.ok) {
      list.innerHTML = `<div class="trends-empty">${t('trends_error')}</div>`;
      return;
    }

    const data = await resp.json();

    if (badge) badge.textContent = data.length || '0';

    if (!data.length) {
      list.innerHTML = `<div class="trends-empty">${t('trends_empty')}</div>`;
      return;
    }

    list.innerHTML = data.map(item => {
      const arrow = { rising: '↑', declining: '↓', stable: '→' }[item.trending_direction] || '→';
      const cls = item.trending_direction || 'stable';
      return `
        <div class="trend-card">
          <div class="trend-card-dim">${item.dimension || ''}</div>
          <div class="trend-card-name">${item.category || ''} · ${item.subcategory || ''}</div>
          <div class="trend-card-meta">
            <span class="trend-arrow ${cls}">${arrow}</span>
            <span class="trend-count">${item.total_videos || 0} ${t('trends_videos')}</span>
          </div>
        </div>`;
    }).join('');

  } catch (e) {
    list.innerHTML = `<div class="trends-empty">${t('trends_error')}</div>`;
  }
}

// 筛选变化监听
document.getElementById('trendsDimFilter')?.addEventListener('change', loadTrends);
let trendsSearchTimer;
document.getElementById('trendsSearch')?.addEventListener('input', () => {
  clearTimeout(trendsSearchTimer);
  trendsSearchTimer = setTimeout(loadTrends, 400);
});
```

- [ ] **Step 3: styles.css 添加趋势面板样式**

```css
/* 剪辑趋势面板 */
.trends-section {
  margin-top: 24px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
}

.trends-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  cursor: pointer;
  user-select: none;
  font-weight: 600;
  font-size: 15px;
  color: var(--foreground);
  transition: background 0.15s;
}

.trends-header:hover {
  background: var(--muted);
}

.trends-badge {
  margin-left: auto;
  background: var(--primary);
  color: white;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 999px;
  font-weight: 500;
}

.trends-chevron {
  transition: transform 0.2s;
  opacity: 0.5;
}

.trends-body {
  border-top: 1px solid var(--border);
  padding: 16px 18px;
}

.trends-filters {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}

.trends-filters select,
.trends-filters input {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 13px;
  background: var(--background);
  color: var(--foreground);
  outline: none;
}

.trends-filters select:focus,
.trends-filters input:focus {
  border-color: var(--primary);
}

.trends-filters input {
  flex: 1;
}

.trends-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.trends-empty {
  width: 100%;
  text-align: center;
  color: var(--muted-foreground);
  font-size: 13px;
  padding: 20px;
}

.trend-card {
  flex: 0 0 calc(33.333% - 7px);
  min-width: 160px;
  background: var(--background);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px;
  transition: border-color 0.15s;
}

.trend-card:hover {
  border-color: var(--primary);
}

.trend-card-dim {
  font-size: 11px;
  color: var(--primary);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}

.trend-card-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--foreground);
  margin-bottom: 6px;
}

.trend-card-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--muted-foreground);
}

.trend-arrow.rising { color: #22c55e; }
.trend-arrow.declining { color: #ef4444; }
.trend-arrow.stable { color: var(--muted-foreground); }

@media (max-width: 768px) {
  .trend-card {
    flex: 0 0 calc(50% - 5px);
  }
}

@media (max-width: 480px) {
  .trend-card {
    flex: 1 1 100%;
  }
}
```

- [ ] **Step 4: 更新 i18n 文件（4 个语言各追加 5 个 key）**

在 `i18n/zh.json` 末尾（`}` 前）追加：

```json
  "trends_title": "剪辑趋势",
  "trends_all_dim": "全部维度",
  "trends_search_placeholder": "搜索技法...",
  "trends_loading": "加载中...",
  "trends_error": "加载失败，请稍后重试",
  "trends_empty": "暂无趋势数据",
  "trends_videos": "个视频"
```

同样为 `en.json`、`ja.json`、`ko.json` 追加对应的英文/日文/韩文翻译。

- [ ] **Step 5: 提交**

```bash
git add index.html script.js styles.css i18n/
git commit -m "feat: trending techniques frontend panel + i18n"
```

---

### Task 10: 端到端验证

- [ ] **Step 1: 启动 MySQL**

```bash
docker-compose up -d mysql
```

Expected: `clip_trends_mysql` 容器运行中。

- [ ] **Step 2: 手动执行一次爬取**

```bash
python clip_trends/main.py --once
```

Expected: 看到 4 站爬取日志，`videos` + `video_techniques` + `daily_trends` 表有数据。

- [ ] **Step 3: 验证趋势 API**

```bash
curl http://localhost:5000/api/trends -H "X-Access-Token: <your_token>"
```

Expected: 返回 JSON 数组，包含分类标签和趋势方向。

- [ ] **Step 4: 启动智演助手，验证前端面板**

访问 `http://localhost:5000`，点击"剪辑趋势"折叠面板，确认数据加载正常。

- [ ] **Step 5: 验证 Prompt 注入**

全自动模式跑一次视频生成，查看 `state.json` 中的系统 Prompt 是否包含趋势文案。

- [ ] **Step 6: 提交**

```bash
git add -A
git commit -m "chore: final integration verification"
```
