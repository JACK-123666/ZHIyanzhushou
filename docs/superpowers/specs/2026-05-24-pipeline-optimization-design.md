# 智演助手 流水线优化 — 人物一致性 / 速度 / 剧本贴合

日期: 2026-05-24 | 状态: approved

## 总览

在现有两轮 Bible 架构上做精准增强，不改整体架构。三大维度：程序化硬约束确保人物一致、并行流式管道提速、情绪+镜头上下文增强剧本贴合。

---

## Section 1: 人物一致性 — 角色身份证 + 占位符替换

### 问题
LLM 长文本输出中存在角色外貌描述漂移（第1镜"蓝黑色制服"→第10镜"深蓝色西装"）。

### 方案
1. **parse_shots()** 产出的 `character_summary` 作为"角色身份证"，要求枚举式精确到每个可穿戴物品
2. **generate_prompts()** 中 LLM 不再直接写角色描述，改用 `{CHAR:角色名}` 占位符
3. **Python 代码做字符串替换** — `character_summary` 中的描述逐字注入每个 prompt，同角色 20 镜 100% 一致
4. **后验证** — 检查占位符是否全部替换、角色描述是否完整

### 涉及文件
- `config.py`: 新增 `CHARACTER_PROMPT_EXTRA` 指令常量
- `llm_service.py`: 修改 `parse_shots()` System Prompt 增强外貌提取精度；修改 `generate_prompts()` 实现占位符机制 + 后验证函数
- `app.py`: `session_prompts()` 中注入 `character_summary` 到生成流程

---

## Section 2: 速度优化 — 并行场景图 + 流式管道

### 问题
场景关键帧串行生成 + 图片→视频瀑布等待 + 视频轮询统一阻塞。

### 方案
1. **场景关键帧并行** — `ThreadPoolExecutor(max_workers=5)` 并行调用 Seedream
2. **关键帧即出即发视频** — 每个场景关键帧完成后，立即为该场景所有镜头发起 Seedance 任务（合并 images/videos 阶段）
3. **视频独立轮询+下载** — `as_completed` 时每个任务完成后立刻下载
4. **视频创建并发度 5→10** — 创建任务仅需 2s API 调用，瓶颈在网络而非 CPU

### 涉及文件
- `app.py`: 重构 `session_images()` 和 `session_videos()`，新增流式逻辑

---

## Section 3: 剧本贴合 — 情绪弧线 + 镜头语言 + 叙事链

### 问题
每个镜头 prompt 孤立生成，AI 理解"长什么样"但不懂"为什么要有这个镜头"。

### 方案
1. **情绪弧线注入** — 构建镜头情绪序列 `[紧张→紧张升级→紧迫→镇定]`，每个 prompt 注入前后情绪上下文和目标
2. **camera_hint 精确映射** — 中文镜头类型（广角/中景/特写/推近/跟拍）展开为精确英文构图指令
3. **叙事链** — 从 shots 数组自动构建前后镜头上下文，注入起始/结束状态过渡要求
4. **action_summary 作为动作骨架** — video_prompt 以已提取的动作为核心展开，不自由发挥

### 涉及文件
- `config.py`: 新增 `CAMERA_INSTRUCTIONS` 映射表
- `llm_service.py`: 修改 `PROMPT_GEN_SYSTEM`/`PROMPT_GEN_USER`，新增情绪弧线和叙事链构建逻辑

---

## 不改动范围
- 前端 `script.js`/`index.html`/`styles.css` — 不变
- `document_parser.py` / `tts_service.py` / `composer.py` / `image_generator.py` — 不变
- API 路由签名 — 不变（前端无需改动）
- 文件存储结构 — 不变
