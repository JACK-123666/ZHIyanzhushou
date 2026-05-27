# Prompt 算法重写 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 重写 BIBLE/PROMPT_GEN System Prompt，升级 video_prompt + image_prompt 格式，增强全局一致性

**Architecture:** 单文件改动 `services/llm_service.py`，3 个顺序 Task，零额外 API 调用

**Tech Stack:** Python 3.13, DeepSeek V4 Pro

---

### Task 1: video_prompt 5 段式重写（优先级 B）

**Files:**
- Modify: `services/llm_service.py` (PROMPT_GEN_SYSTEM + PROMPT_GEN_USER)

将 PROMPT_GEN_SYSTEM 中 video_prompt 部分从 4 段式改为 5 段式，加入运镜-负面词映射表。

**当前 PROMPT_GEN_SYSTEM 中 video_prompt 部分：**

```
=== video_prompt 格式 (中文 80-150字，给 Seedance，4段缺一不可) ===
[动作] 角色名+身体部位+方向+幅度+速度+力度。写明哪些部分完全不动。
[运镜] 镜头类型+方向+速度，幅度不超过X%，smooth steady stabilized 无抖动。
[不变] 背景、道具、光线、角色外观与参考图完全一致。
[禁止] 逐条列出6项。
```

**替换为：**

```
=== video_prompt 格式 (中文 50-80字，给 Seedance，5段缺一不可) ===

[主体] 角色名 + 画面位置 + 姿势（从参考图出）
  例: "主角A，画左站立，右手持文件，目光注视文件内容"

[动作] 单一微动作 + 幅度 + 速度 + 不动部分
  追求"几乎不动"的微运动，不追求大幅复杂动作。
  幅度量化为具体数字: "抬杯约5cm" "转头约30度" "推镜2-5%"
  必须写明不动部分: "仅右手和前臂运动，躯干和头部保持静止"
  static运镜时写: "主体微呼吸感，无大幅动作"

[镜头] 运镜类型 + 方向 + 速度 + 量化幅度
  每镜只用一种运镜。
  static:  "三脚架固定镜头，无相机移动"
  push-in: "慢速平滑推镜2-5%，水平线锁定"
  handheld: "微手持晃动，纪录片临场感，幅度不超过画面3%"
  orbit: "缓慢环绕主体约10度，保持主体居中"
  pan: "平滑水平摇镜，速度均匀，无垂直漂移"
  tracking: "侧向跟拍，背景视差，速度恒定"
  crane: "缓慢垂直升降，匀速无顿挫"
  pull-out: "缓慢拉远2-5%，揭示环境"

[风格] 光线+色调锚点（从视觉圣经取）
  例: "柔暖侧窗光，色温3200K，低饱和色调，商业清洁感"

[禁止] 运镜专属负面词 + 通用负面词
  根据所选运镜，从下方映射表选取专属禁止词，并追加通用禁止词。

=== 运镜-负面词映射 ===
push-in / pull-out: no jitter, no speed change, no edge wobble
handheld: no excessive shake, no motion blur, no focus drift
orbit / crane: no background warp, no perspective shift, no distortion
static: no camera movement, no frame drift, no subtle shift
pan / tracking: no vertical drift, no speed variation, no rolling shutter

=== 通用禁止词（所有 video_prompt 必须包含） ===
no face drift, no limb warp, no texture flicker, no added objects, no color shift
```

**同步修改 PROMPT_GEN_USER 最后一行：**

```
为每个镜头生成 image_prompt(英文) 和 video_prompt(中文)。
严格使用 {{{{CHAR}}:角色名}} 占位符。
video_prompt: 中文 50-80字，5段(主体/动作/镜头/风格/禁止)缺一不可。
```

**验证：**
```bash
python -m py_compile services/llm_service.py
```

**提交：**
```bash
git add services/llm_service.py
git commit -m "$(cat <<'EOF'
feat: video_prompt 升级为 Seedance 5段式，加入运镜-负面词映射表
EOF
)"
```

---

### Task 2: BIBLE 模板化 + 场景代码级注入（优先级 C）

**Files:**
- Modify: `services/llm_service.py` (BIBLE_SYSTEM + BIBLE_USER + 注入逻辑)

**Step 1: 重写 BIBLE_SYSTEM**

当前 BIBLE_SYSTEM：

```
你是影视美术指导。分析所有分镜，输出"视觉圣经"确保全片视觉一致。
若提供了 CHARACTER_SUMMARY（角色身份证），必须逐字复制，不得改写。

输出JSON:
{"global_style":"2-3句: 色温+主色调+光线质量",
 "characters":{"角色名":"若CHARACTER_SUMMARY已提供则逐字复制，否则写50-80词精确外貌"},
 "locations":{"场景名":"30-50词: 空间布局+标志道具+光线色调"},
 "shot_connections":["SC01->SC02 的衔接说明"]}
只输出JSON。
```

替换为：

```
你是影视美术指导。分析所有分镜，输出"视觉圣经"确保全片视觉一致。
若提供了 CHARACTER_SUMMARY（角色身份证），必须逐字复制，不得改写。

=== 输出格式（严格按模板，字段不可省略） ===

[角色模板 - 枚举格式]
每个角色的外貌必须用逗号分隔的枚举模板:
"姓名,年龄,性别,身高,体型,发色,上装(色/款/质),下装,鞋,配饰"
例: "张三,30岁,男,178cm,瘦高,黑色短发,白色棉质衬衫,深蓝牛仔裤,棕色皮鞋,银框眼镜"

[场景模板 - 3 字段]
每个场景必须包含 layout / lighting / color_palette:
- layout: 空间大小+道具位置+标志物（30-50字英文）
  例: "Modern office lobby, 8x10m, reception desk at center back, floor-to-ceiling windows on left wall, marble floor, potted plants at corners"
- lighting: 主光方向+色温+光比（固定格式）
  例: "Key light from window-left at 45°, 5600K daylight, fill from right bounce, ratio 4:1"
- color_palette: 3-4色（英文）
  例: "warm beige #D4C5B2, deep navy #1B2A4A, sage green #87A878, brass accent"

=== 输出JSON ===
{"global_style":"色温+主色调+光线质量（2-3句英文）",
 "characters":{"角色名":{"appearance":"枚举模板","anchor_shot":"首次出场镜头ID"}},
 "locations":{"场景名":{"layout":"布局","lighting":"灯光","color_palette":"配色"}},
 "shot_connections":["SC01→SC02: 过渡说明（约15字）"]}
只输出JSON。
```

**Step 2: 重写 BIBLE_USER**

当前 BIBLE_USER：

```
风格前缀: {style_prefix}

=== CHARACTER_SUMMARY（角色身份证，不可修改） ===
{character_summary}

分镜数据:
{shots_json}

生成视觉圣经。角色描述从 CHARACTER_SUMMARY 逐字复制。
```

替换为：

```
风格前缀: {style_prefix}

=== CHARACTER_SUMMARY（角色身份证，按枚举模板格式，不可修改） ===
{character_summary}

分镜数据:
{shots_json}

按模板格式生成视觉圣经。角色外貌从 CHARACTER_SUMMARY 逐字复制。
每个场景必须包含 layout / lighting / color_palette 三个字段。
```

**Step 3: 修改场景数据注入逻辑**

在 `generate_prompts()` 的 `shots_with_context` 构建循环中，每镜附加其 location 的模板字段。

找到构建 `shots_with_context.append({...})` 的位置，在 `'on_screen_text': ...` 之后新增三个字段：

```python
'location_layout': bible.get('locations', {}).get(s.get('location', ''), {}).get('layout', ''),
'location_lighting': bible.get('locations', {}).get(s.get('location', ''), {}).get('lighting', ''),
'location_colors': bible.get('locations', {}).get(s.get('location', ''), {}).get('color_palette', ''),
```

**Step 4: 修改 PROMPT_GEN_USER**

在 PROMPT_GEN_USER 的分镜列表描述中，加入场景字段指令：

当前 PROMPT_GEN_USER 末尾：

```
=== 分镜列表（含叙事链、相机指令、时长） ===
{shots_with_context}

为每个镜头生成 image_prompt(英文) 和 video_prompt(中文)。
严格使用 {{{{CHAR}}:角色名}} 占位符。
video_prompt: 中文 50-80字，5段(主体/动作/镜头/风格/禁止)缺一不可。
```

替换为：

```
=== 分镜列表（含叙事链、相机指令、时长、场景模板） ===
{shots_with_context}

为每个镜头生成 image_prompt(英文) 和 video_prompt(中文)。

image_prompt 规则:
- 场景部分必须从分镜数据中的 location_layout / location_lighting / location_colors 逐字复制，不得改写
- 严格使用 {{{{CHAR}}:角色名}} 占位符
- 英文 200-300词

video_prompt 规则:
- 中文 50-80字
- 5段(主体/动作/镜头/风格/禁止)缺一不可
- 禁止词根据运镜类型从映射表选取
```

**验证：**
```bash
python -m py_compile services/llm_service.py
python -c "from services.llm_service import generate_prompts; print('import OK')"
```

**提交：**
```bash
git add services/llm_service.py
git commit -m "$(cat <<'EOF'
feat: BIBLE 模板化输出 + 场景描述代码级逐字注入 + 角色枚举模板
EOF
)"
```

---

### Task 3: image_prompt 7 段式重写（优先级 A）

**Files:**
- Modify: `services/llm_service.py` (PROMPT_GEN_SYSTEM 中 image_prompt 部分)

**当前 PROMPT_GEN_SYSTEM 中 image_prompt 部分：**

```
=== image_prompt 格式 (英文 250-400词，给 Seedream) ===
[全局风格: 色温+主色调+光线质量]
[场景: 从视觉圣经逐字复制]
{CHAR:角色名1} {CHAR:角色名2}
[构图: camera_hint + 情绪灯光]
[静态状态: standing/holding/positioned/sitting — 这是视频的起始帧]
[品质: high quality, consistent character design, identical appearance, detailed textures, clean background, cinematic lighting]
```

**替换为：**

```
=== image_prompt 格式 (英文 200-300词，给 Seedream，7段式) ===

词序=权重，最重要元素放最前。每段之间用句号分隔，形成自然段落。

1. [主体] 角色身份证 + 姿势 + 画面位置
   例: "Character Model [主角A]: male,30,178cm,slim,black short hair,white cotton shirt,dark blue jeans,brown leather shoes,silver glasses. Standing at counter left, holding a document, eyes fixed on paper."

2. [姿态] 静态起始帧描述。写镜头开始瞬间的定格状态。
   例: "Frozen mid-gesture, right hand extended toward document, body still, left hand resting on counter."

3. [场景] 从分镜数据逐字复制 location_layout + location_colors。不得改写。
   例: "{location_layout}. Color palette: {location_colors}."

4. [构图] camera_hint + 焦距 + 景深。用摄影术语。
   例: "Medium shot, waist-up framing, 85mm lens, shallow depth of field, bokeh background."

5. [光影] 从分镜数据逐字复制 location_lighting。不得改写。
   例: "{location_lighting}."

6. [风格] style_prefix + global_style
   例: "{style_prefix}. {global_style}."

7. [品质] 精简一行，不用空泛词（禁止 "high quality, masterpiece, 8K, ultra-detailed"）
   "sharp focus, consistent character design, clean background, cinematic lighting."
```

**同步修改 PROMPT_GEN_USER 末尾 image_prompt 规则：**

```
image_prompt 规则:
- 英文 200-300词，7段式
- 第1段(主体)放最重要的元素，词序=权重
- 第3段和第5段从分镜数据逐字复制，不得改写
- 严格使用 {{{{CHAR}}:角色名}} 占位符
- 禁止使用 "high quality, masterpiece, 8K, ultra-detailed" 等空泛修饰词
```

**验证：**
```bash
python -m py_compile services/llm_service.py
```

**提交：**
```bash
git add services/llm_service.py
git commit -m "$(cat <<'EOF'
feat: image_prompt 升级为 Seedream 7段式 200-300词，场景/光影逐字注入
EOF
)"
```

---

### Task 4: 端到端验证

- [ ] **Step 1: 全量编译**

```bash
python -m py_compile services/llm_service.py && echo "OK"
```

- [ ] **Step 2: 导入验证**

```bash
python -c "from services.llm_service import generate_prompts, design_shots_from_document, BIBLE_SYSTEM, PROMPT_GEN_SYSTEM; print('all imports OK')"
```

- [ ] **Step 3: 检查 Prompt 关键字段**

```bash
python -c "
from services.llm_service import PROMPT_GEN_SYSTEM
assert '5段(主体/动作/镜头/风格/禁止)' in PROMPT_GEN_SYSTEM, 'video prompt 5段 missing'
assert '7段式' in PROMPT_GEN_SYSTEM, 'image prompt 7段 missing'
assert '运镜-负面词映射' in PROMPT_GEN_SYSTEM, 'negative prompt map missing'
print('all prompt checks OK')
"
```

- [ ] **Step 4: 检查 BIBLE 模板字段**

```bash
python -c "
from services.llm_service import BIBLE_SYSTEM
assert 'layout' in BIBLE_SYSTEM, 'layout field missing'
assert 'lighting' in BIBLE_SYSTEM, 'lighting field missing'
assert 'color_palette' in BIBLE_SYSTEM, 'color_palette missing'
assert '枚举模板' in BIBLE_SYSTEM, 'enum template missing'
print('BIBLE checks OK')
"
```

- [ ] **Step 5: 启动 Flask 跑分镜设计**

```bash
python /d/PYTHON/simple_webpage/app.py &
sleep 2
echo "test doc" > /tmp/t.txt
curl -s -X POST http://localhost:5000/api/session/create -F "file=@/tmp/t.txt" -F "mode=auto" -F "total_duration=short"
taskkill //F //IM python.exe 2>/dev/null
```
