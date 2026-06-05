# 剪辑趋势爬虫系统 — 设计文档

> 状态：待实现 | 日期：2026-06-02

## 1. 目标

构建独立爬虫子项目 `clip_trends/`，每日从 4 个 CC0 免版权视频网站（Pexels、Pixabay、Coverr、Mixkit）爬取热门视频，通过 Qwen-VL 抽帧分析提取 7 维剪辑手法标签，存入 MySQL，供智演助手在 Prompt 生成时自动注入最新剪辑趋势，同时提供前端"剪辑趋势"浏览面板。

## 2. 核心决策汇总

| 决策点 | 选择 |
|--------|------|
| 目标站点 | Pexels + Pixabay + Coverr + Mixkit，每站日限 15 个 |
| 分类引擎 | Qwen-VL 抽帧分析为主（ffmpeg 完整下载 → 每 3s 抽 1 帧 → 帧间对比），规则匹配 + DeepSeek 文本兜底 |
| 数据库 | MySQL 8.0 via Docker |
| 项目结构 | `clip_trends/` 独立子项目，与智演助手通过 MySQL 通信 |
| 集成方式 | Prompt 自动注入（全自动模式）+ `/api/trends` 前端面板查询 |
| 抽帧策略 | 完整视频下载 → 每 3 秒 1 帧 → 文件大小上限 50MB |
| 调度方式 | APScheduler，每天凌晨 2:00 |
| 限速 | 请求间隔可配（默认 1s），每次爬取间隔可配 |

## 3. 文件结构

```
d:\PYTHON\simple_webpage\
├── app.py                       # 智演助手（新增 /api/trends 路由）
├── services/
│   ├── llm_service.py           # 修改：Prompt 动态注入剪辑趋势
│   └── trend_service.py         # 新增：MySQL 读查询接口
├── index.html                   # 修改：新增"剪辑趋势"面板
├── script.js                    # 修改：趋势面板交互
├── styles.css                   # 修改：趋势面板样式
│
└── clip_trends/                 # 爬虫子项目（独立）
    ├── main.py                  # 入口：命令行 + 调度编排
    ├── scheduler.py             # APScheduler 每日定时
    ├── config.py                # 爬取配置 + API 密钥
    ├── db.py                    # MySQL 连接池 + CRUD 封装
    ├── taxonomy.py              # 7维分类体系定义（keywords + 描述）
    ├── classifier.py            # 分类编排：Qwen-VL 抽帧 → 规则 → LLM 降级
    ├── video_analyzer.py        # ffmpeg 下载 + 抽帧 + ffprobe 音频分析
    ├── qwen_client.py           # Qwen-VL API 封装（逐帧分析 + 帧间对比）
    ├── crawlers/
    │   ├── base.py              # 抽象基类（请求头/重试/限速/HEAD探测）
    │   ├── pexels.py            # Pexels API
    │   ├── pixabay.py           # Pixabay API
    │   ├── coverr.py            # Coverr HTML 解析
    │   └── mixkit.py            # Mixkit HTML 解析
    ├── sql/
    │   └── schema.sql           # 6 张表建表语句
    └── requirements.txt         # 独立依赖
```

## 4. 数据库设计（6 张表）

### 4.1 technique_taxonomy（分类体系元数据）

预填完整的 7 维分类树，每行是一个叶子节点（subcategory）。

```sql
CREATE TABLE technique_taxonomy (
    id INT PRIMARY KEY AUTO_INCREMENT,
    dimension VARCHAR(20) NOT NULL,       -- 时间/空间/叙事/节奏/视听/表现/技术
    category VARCHAR(30) NOT NULL,        -- 如：压缩、连贯剪辑、快剪
    subcategory VARCHAR(40) NOT NULL,     -- 如：跳切、180度轴线、紧张激烈
    detail TEXT,                          -- 详细解释（供 LLM 匹配用）
    keywords JSON NOT NULL,               -- ["jump cut","jumpcut","跳切"]
    weight DECIMAL(3,2) DEFAULT 1.00,     -- 趋势排序权重
    UNIQUE KEY uk_dim_cat_sub (dimension, category, subcategory)
);
```

预填数据示例：
```
时间 / 压缩 / 跳切        keywords: ["jump cut","jumpcut","跳切","skip cut"]
时间 / 压缩 / 蒙太奇      keywords: ["montage","蒙太奇","sequence","assembly edit"]
时间 / 延长 / 慢动作      keywords: ["slow motion","slow-mo","慢动作","slo-mo"]
空间 / 连贯剪辑 / 180度轴线 keywords: ["180 degree","180°","axis line","轴线"]
...
```

### 4.2 videos（爬取视频）

```sql
CREATE TABLE videos (
    id INT PRIMARY KEY AUTO_INCREMENT,
    site VARCHAR(20) NOT NULL,            -- pexels/pixabay/coverr/mixkit
    source_url VARCHAR(500) NOT NULL,
    source_id VARCHAR(100),               -- API 返回的原始 ID
    title VARCHAR(300),
    thumbnail_url VARCHAR(500),
    duration_sec DECIMAL(8,2),
    resolution VARCHAR(20),               -- 1920x1080
    tags_json JSON,                       -- 原始标签数组
    description TEXT,
    popularity_score DECIMAL(10,2) DEFAULT 0,
    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_site_source (site, source_id),
    INDEX idx_site (site),
    INDEX idx_popularity (popularity_score DESC),
    INDEX idx_crawled_at (crawled_at)
);
```

### 4.3 video_techniques（核心桥表）

```sql
CREATE TABLE video_techniques (
    id INT PRIMARY KEY AUTO_INCREMENT,
    video_id INT NOT NULL,
    taxonomy_id INT NOT NULL,
    confidence DECIMAL(3,2) DEFAULT 0.70,  -- 0-1
    evidence TEXT,                          -- 分类依据（匹配到的 tag/LLM 分析摘要/帧分析描述）
    method ENUM('rule','llm','qwen-vl','hybrid') DEFAULT 'rule',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_video_taxonomy (video_id, taxonomy_id),
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
    FOREIGN KEY (taxonomy_id) REFERENCES technique_taxonomy(id) ON DELETE CASCADE,
    INDEX idx_taxonomy (taxonomy_id),
    INDEX idx_method (method)
);
```

### 4.4 daily_trends（每日趋势快照）

```sql
CREATE TABLE daily_trends (
    id INT PRIMARY KEY AUTO_INCREMENT,
    date DATE NOT NULL,
    taxonomy_id INT NOT NULL,
    video_count INT DEFAULT 0,
    avg_popularity DECIMAL(10,2) DEFAULT 0,
    avg_duration DECIMAL(8,2),
    sample_video_ids JSON,                 -- [12, 45, 78]
    trending_direction ENUM('rising','stable','declining') DEFAULT 'stable',
    -- 对比前一天同 taxonomy_id 的 video_count：±20% 以上 = rising/declining，否则 stable
    UNIQUE KEY uk_date_taxonomy (date, taxonomy_id),
    FOREIGN KEY (taxonomy_id) REFERENCES technique_taxonomy(id),
    INDEX idx_date (date),
    INDEX idx_trending (trending_direction)
);
```

### 4.5 crawl_logs（爬取日志）

```sql
CREATE TABLE crawl_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    site VARCHAR(20) NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    videos_total INT DEFAULT 0,
    videos_new INT DEFAULT 0,
    errors TEXT,
    status ENUM('running','success','partial','failed') DEFAULT 'running'
);
```

### 4.6 editing_templates（剪辑模板）

```sql
CREATE TABLE editing_templates (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    taxonomy_ids_json JSON NOT NULL,       -- [1, 5, 12] 引用 taxonomy.id
    prompt_snippet TEXT NOT NULL,          -- 可直接注入 LLM prompt 的文案
    use_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 5. 7 维分类体系

完整定义在 `clip_trends/taxonomy.py`，结构如下：

```python
TAXONOMY = [
    {
        "dimension": "时间",
        "categories": [
            {
                "category": "压缩",
                "subcategories": [
                    {"sub": "跳切",      "keywords": ["jump cut","jumpcut","跳切","skip cut"]},
                    {"sub": "蒙太奇",    "keywords": ["montage","蒙太奇","sequence","assembly edit"]},
                    {"sub": "省略",      "keywords": ["ellipsis","time skip","省略","temporal skip"]},
                ]
            },
            {
                "category": "延长",
                "subcategories": [
                    {"sub": "慢动作",    "keywords": ["slow motion","slow-mo","慢动作","slo-mo","slow down"]},
                    {"sub": "多角度",    "keywords": ["multi-angle","multi angle","多角度","multi-cam"]},
                    {"sub": "插入镜头",  "keywords": ["insert shot","cutaway","插入","cut-in"]},
                ]
            },
            {
                "category": "颠倒",
                "subcategories": [
                    {"sub": "闪回",      "keywords": ["flashback","闪回","回忆"]},
                    {"sub": "闪前",      "keywords": ["flashforward","flash forward","闪前","预演"]},
                    {"sub": "非线性叙事", "keywords": ["nonlinear","non-linear","非线性","fragmented"]},
                ]
            },
            {
                "category": "并行",
                "subcategories": [
                    {"sub": "平行剪辑",  "keywords": ["parallel editing","parallel","平行","cross edit"]},
                    {"sub": "交叉剪辑",  "keywords": ["cross cutting","cross-cutting","交叉","intercut"]},
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
                    {"sub": "180度轴线",  "keywords": ["180 degree","180°","axis line","轴线"]},
                    {"sub": "30度原则",   "keywords": ["30 degree","30° rule","角度变化"]},
                    {"sub": "匹配剪辑",   "keywords": ["match cut","match-cut","匹配剪辑","graphic match"]},
                    {"sub": "正反打",     "keywords": ["shot reverse shot","shot-reverse-shot","正反打","OTS"]},
                ]
            },
            {
                "category": "解构剪辑",
                "subcategories": [
                    {"sub": "越轴",      "keywords": ["cross axis","越轴","跳轴","axis break"]},
                    {"sub": "碎片化空间", "keywords": ["fragmented space","碎片化","disorienting","空间混乱"]},
                ]
            },
            {
                "category": "空间转场",
                "subcategories": [
                    {"sub": "淡入淡出",  "keywords": ["fade in","fade out","淡入","淡出","渐显","渐隐"]},
                    {"sub": "叠化",      "keywords": ["dissolve","叠化","溶接","cross dissolve"]},
                    {"sub": "相似体转场", "keywords": ["match dissolve","shape match","相似体","形体匹配"]},
                    {"sub": "动作转场",  "keywords": ["action match","动作匹配","动作转场","whip pan"]},
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
                    {"sub": "事件逻辑",  "keywords": ["cause effect","因果","逻辑剪辑","continuity"]},
                ]
            },
            {
                "category": "动机剪辑",
                "subcategories": [
                    {"sub": "视觉驱动",  "keywords": ["visual driven","视觉驱动","eyeline match"]},
                    {"sub": "声音驱动",  "keywords": ["sound driven","声音驱动","audio lead"]},
                    {"sub": "情绪驱动",  "keywords": ["emotion driven","情绪驱动","emotional cut"]},
                ]
            },
            {
                "category": "视点剪辑",
                "subcategories": [
                    {"sub": "客观视点",  "keywords": ["objective","客观","omniscient"]},
                    {"sub": "主观POV",   "keywords": ["POV","point of view","主观","第一人称"]},
                    {"sub": "上帝视角",  "keywords": ["god view","上帝视角","aerial","俯瞰"]},
                ]
            },
            {
                "category": "悬念剪辑",
                "subcategories": [
                    {"sub": "延迟揭示",  "keywords": ["delayed reveal","延迟揭示","slow reveal"]},
                    {"sub": "信息差",    "keywords": ["dramatic irony","信息差","观众知道更多"]},
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
                    {"sub": "紧张激烈",  "keywords": ["fast cutting","fast-paced","快剪","rapid","intense"]},
                    {"sub": "动作快剪",  "keywords": ["action cutting","动作剪辑","fight scene","追逐"]},
                ]
            },
            {
                "category": "慢剪",
                "subcategories": [
                    {"sub": "舒缓长镜",  "keywords": ["long take","长镜头","slow pace","舒缓","lingering"]},
                    {"sub": "沉重凝滞",  "keywords": ["heavy","weight","沉重","stillness","静态"]},
                ]
            },
            {
                "category": "节奏变化",
                "subcategories": [
                    {"sub": "加速",      "keywords": ["accelerating","加速","渐快","building"]},
                    {"sub": "减速",      "keywords": ["decelerating","减速","渐慢","winding down"]},
                    {"sub": "停顿对比",  "keywords": ["pause","停顿","freeze frame","静帧","beat"]},
                ]
            },
            {
                "category": "音乐节拍",
                "subcategories": [
                    {"sub": "节拍精准对齐","keywords": ["beat sync","节拍对齐","cut to beat","rhythm edit"]},
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
                    {"sub": "声画同步",  "keywords": ["sync sound","声画同步","diegetic","lip sync"]},
                    {"sub": "声画分立",  "keywords": ["sound separation","声画分立","off-screen sound"]},
                    {"sub": "声画对位",  "keywords": ["counterpoint","对位","讽刺","contrast sound"]},
                ]
            },
            {
                "category": "声音转场",
                "subcategories": [
                    {"sub": "先声夺人",  "keywords": ["sound advance","先声","J cut","audio lead"]},
                    {"sub": "声音延续",  "keywords": ["sound linger","声音延续","L cut","audio tail"]},
                    {"sub": "声音桥",    "keywords": ["sound bridge","声音桥","audio bridge"]},
                ]
            },
            {
                "category": "画面匹配",
                "subcategories": [
                    {"sub": "色彩连贯",  "keywords": ["color match","色彩匹配","color continuity"]},
                    {"sub": "光影连贯",  "keywords": ["lighting match","光影匹配"]},
                    {"sub": "构图对比",  "keywords": ["composition contrast","构图对比"]},
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
                    {"sub": "对比蒙太奇","keywords": ["contrast montage","对比","juxtaposition"]},
                    {"sub": "隐喻蒙太奇","keywords": ["metaphor montage","隐喻","symbolic"]},
                    {"sub": "象征蒙太奇","keywords": ["symbol montage","象征","symbolism"]},
                    {"sub": "重复蒙太奇","keywords": ["repetition","重复","recurring","motif"]},
                ]
            },
            {
                "category": "情绪剪辑",
                "subcategories": [
                    {"sub": "特写放大",  "keywords": ["close-up emotion","特写","表情","reaction shot"]},
                    {"sub": "空镜抒情",  "keywords": ["establishing shot emotion","空镜头","景观抒情","breathing room"]},
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
                    {"sub": "遮挡转场",  "keywords": ["wipe transition","遮挡","object wipe"]},
                    {"sub": "运动模糊转场","keywords": ["motion blur transition","运动模糊","smear"]},
                    {"sub": "数字特效转场","keywords": ["digital transition","数字转场","morph","glitch"]},
                ]
            },
            {
                "category": "数字合成",
                "subcategories": [
                    {"sub": "分屏",      "keywords": ["split screen","分屏","split-screen"]},
                    {"sub": "叠印",      "keywords": ["superimpose","叠印","double exposure","双重曝光"]},
                    {"sub": "绿幕抠像",  "keywords": ["green screen","chroma key","绿幕","抠像","keying"]},
                ]
            },
            {
                "category": "AI辅助",
                "subcategories": [
                    {"sub": "自动剪辑",  "keywords": ["AI editing","auto edit","自动剪辑"]},
                    {"sub": "智能转场",  "keywords": ["AI transition","智能转场"]},
                    {"sub": "画质修复",  "keywords": ["upscale","超分","画质修复","enhance"]},
                ]
            },
        ]
    },
]
```

## 6. 爬虫设计

### 6.1 基类（base.py）

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class RawVideo:
    site: str
    source_url: str
    source_id: Optional[str]
    title: str
    thumbnail_url: Optional[str]
    duration_sec: Optional[float]
    resolution: Optional[str]
    tags: list[str]
    description: Optional[str]
    popularity_score: float

class BaseCrawler:
    def __init__(self, config):
        self.max_per_site = config['max_per_site']          # 15
        self.request_interval = config['request_interval']    # 1.0
        self.request_timeout = config['request_timeout']      # 30
        self.retry_times = config['retry_times']              # 3
        self.retry_backoff = config['retry_backoff']          # [5,10,20]

    def _head_content_length(self, url) -> Optional[int]:
        """HEAD 请求探测文件大小，用于超大文件过滤"""
        ...

    def _download_video(self, url, dest_path, max_size_mb=50, timeout=120):
        """下载完整视频到临时路径，超时/超限抛异常"""
        ...

    def _rate_limit(self):
        """请求间隔控制"""
        ...

    def crawl(self) -> list[RawVideo]:
        raise NotImplementedError
```

### 6.2 四站策略

| 站点 | 数据源 | 认证 | 解析方式 |
|------|--------|------|----------|
| Pexels | `api.pexels.com/videos/popular` | 免费 API Key（需注册） | JSON 解析 |
| Pixabay | `pixabay.com/api/videos/` | 免费 API Key（需注册） | JSON 解析 |
| Coverr | `coverr.co` 首页 | 无需认证 | BS4 + 瀑布流 JSON |
| Mixkit | `mixkit.co/free-stock-video/` | 无需认证 | BS4 + JSON 数据 |

### 6.3 去重策略

- Pexels/Pixabay：API 返回唯一 ID → `source_id` 去重
- Coverr/Mixkit：`source_url` SHA256 → `source_id` 去重
- 已存在的视频只更新 `popularity_score`，不新增行，不重复分析

**popularity_score 跨站归一化：** 各站热度指标不同（Pexels 有 view_count、Pixabay 有 downloads/favorites、Coverr/Mixkit 无公开指标仅按首页排序），统一按站点内排名倒序换算为 0-100 分值（排名第1=100，第15=6.7），跨站可比。

## 7. 分类器设计（classifier.py）

### 7.1 主流程

```
classify(videos: list[RawVideo]) → 写入 video_techniques

For each video:
  1. HEAD 探测文件大小 → > 50MB 跳过下载，降级为纯文本标签分析
  2. 下载完整视频（超时 120s，超限抛异常）
  3. ffprobe 提取：时长、分辨率、帧率、音频码率、响度曲线
  4. ffmpeg 抽帧：fps=1/3 → N 张 jpg（≈ 时长/3 张）
  5. Qwen-VL 逐帧画面分析 → 帧描述 JSON
  6. Qwen-VL 帧间对比 → 转场类型、节奏判断
  7. 综合帧描述 + 音频特征 + 原始标签 → 映射 taxonomy → video_techniques
  8. 删除临时视频 + 抽帧 jpg
```

### 7.2 降级策略

| 异常 | 降级行为 |
|------|----------|
| 文件超 50MB | 跳过下载，仅用原始标签规则匹配 |
| 下载超时 (120s) | 跳过该视频，记 crawl_logs |
| Qwen-VL API 错误 | 降级到规则匹配 + DeepSeek 文本兜底 |
| 规则+LLM 也失败 | 跳过该视频分类，记 errors |

### 7.3 Qwen-VL 分析 Prompt 设计

**帧画面分析（每帧独立）：**
```
分析这张视频关键帧，描述以下视觉要素：
1. 景别：远景/全景/中景/近景/特写/大特写/中全景
2. 拍摄角度：平视/俯拍/仰拍/鸟瞰
3. 构图：三分法/对称/引导线/框架/负空间/中央
4. 色调：暖/冷/中性，色温估算
5. 灯光：高调/低调/剪影/自然光/人工主光方向
6. 主体：人物数量/位置/动作状态
7. 景深：浅/深/正常
输出JSON，仅JSON。
```

**帧间对比（相邻帧）：**
```
以下是两张连续关键帧（间隔3秒）的描述。
对比分析两帧之间的变化：
1. 转场类型（如果可判断）：硬切/淡入淡出/叠化/滑入/闪白/无转场
2. 机位变化：同角度/30度以上变化/越轴
3. 景别变化：推进/拉远/同景别/跳级
4. 主体移动：方向/速度/进出画
5. 节奏感知：快/中/慢
输出JSON。
```

**综合标签映射（汇总所有帧 + 音频数据 + 原始标签后）：**
```
根据以下多帧画面分析、音频特征和原始标签，从 7 个维度中匹配适用的剪辑技法标签。
7维定义：[完整 taxonomy JSON]
要求：
- 每个维度可匹配 0-N 个 subcategory
- 每项附带 evidence（为什么匹配）
- confidence 0-1
输出JSON: [{"taxonomy_id": 3, "evidence": "...", "confidence": 0.9}, ...]
```

## 8. 智演助手集成

### 8.1 trend_service.py（只读查询）

```python
def get_trending_techniques(dimension=None, limit=10) -> list[dict]:
    """本周最热技法，按 daily_trends 聚合"""

def search_techniques(keywords: str, dimensions=None) -> list[dict]:
    """模糊搜索 taxonomy category/subcategory"""

def get_weekly_trend_context() -> str:
    """返回可直接注入 LLM System Prompt 的文案片段"""
    # 格式: "- 时间/压缩/跳切: YouTube博主风快节奏 (↑3day)"
```

### 8.2 LLM Prompt 注入

在 `llm_service.py` 的 `SHOT_DESIGN_AUTO_SYSTEM` 末尾追加：

```
=== 本周热点剪辑趋势 ===
{trending_context}

在分镜设计中参考以上趋势，融入适合本故事风格的流行技法。
```

### 8.3 前端趋势面板

- 位置：`index.html` 配置面板下方，可折叠区域
- 内容：Top 10 热点技法，按维度分组，展示趋势箭头
- 交互：维度筛选 + 关键词搜索
- API：`GET /api/trends?dimension=时间&limit=10`，Token 鉴权

### 8.4 新 Flask 路由

```python
@app.route('/api/trends')
@require_token
def api_trends():
    dim = request.args.get('dimension')
    limit = min(int(request.args.get('limit', 10)), 50)
    return jsonify(get_trending_techniques(dim, limit))
```

## 9. 调度设计（scheduler.py）

```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

@scheduler.scheduled_job('cron', hour=2, minute=0)
def daily_crawl():
    """每日凌晨2点执行"""
    for site in ['pexels', 'pixabay', 'coverr', 'mixkit']:
        crawler = get_crawler(site)
        raw_videos = crawler.crawl()           # ≤15条/站
        new_videos = db.upsert_videos(raw_videos)  # 去重写入
        for v in new_videos:
            techniques = classifier.classify(v)    # Qwen-VL 分析
            db.save_techniques(techniques)
    db.refresh_daily_trends()                   # 生成今日快照
    db.extract_editing_templates()              # 沉淀高频组合模板

# editing_templates 提取规则：
# 同一 taxonomy_id 组合（≥2个）出现在 ≥3 个不同视频中 → 自动生成模板
# 模板 prompt_snippet 由 LLM 生成：描述该组合的适用场景和使用方法
```

## 10. 边界情况

| 场景 | 处理 |
|------|------|
| Qwen-VL API Key 未配 | 全量降级规则+DeepSeek，日志告警 |
| 视频 404/无法下载 | 跳过该视频，记录 crawl_logs.errors |
| 视频 > 50MB | 跳过下载，仅文本标签分析 |
| 抽帧为 0 帧（视频损坏） | 跳过该视频 |
| MySQL 不可达 | 爬虫报错退出，不写本地文件（避免数据不一致） |
| 每日重复运行 | `source_id` + `crawled_at` 双重去重 |
| 数据库膨胀 | 超过 90 天的 `daily_trends` 定期清理 |
| QWen 分析超时 | 单视频分析超时 60s，超时跳过并降级 |
| 爬虫站挂掉 | 单站失败不影响其他站，crawl_logs 独立记录 |

## 11. 环境变量（.env 新增）

```bash
# MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=clip_trends
MYSQL_PASSWORD=<random>
MYSQL_DATABASE=clip_trends

# Qwen-VL (DashScope)
DASHSCOPE_API_KEY=sk-...

# Pexels API
PEXELS_API_KEY=...

# Pixabay API
PIXABAY_API_KEY=...
```

## 12. 验证方式

1. `docker-compose up mysql` 启动数据库
2. 执行 `sql/schema.sql` 建表 + `taxonomy.py` 预填分类数据
3. `python clip_trends/main.py --once` 手动跑一次完整流程
4. 检查 `videos` 表有数据，`video_techniques` 表有分类结果
5. 启动智演助手，检查全自动模式 Prompt 中包含趋势文案
6. 访问前端，展开"剪辑趋势"面板确认数据展示
7. 检查 `scheduler.py` 定时任务注册成功
