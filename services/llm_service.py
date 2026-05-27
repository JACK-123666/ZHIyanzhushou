"""
LLM 服务 — DeepSeek V4 Pro 驱动分镜设计 + Prompt 生成
核心: 角色身份证(占位符替换) + 角色主镜锚定 + 情绪弧线 + 叙事链
"""

import json, re, time
from openai import OpenAI
from config import (DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL,
                    STYLE_TEMPLATES, DURATION_MODES, CAMERA_INSTRUCTIONS,
                    AUTO_DURATION_OPTIONS, LANGUAGES, DEFAULT_LANGUAGE)

# ================================================================
# System Prompt 1: 分镜设计师 — 文档 → 完整分镜表
# 包含电影导演知识：180度规则、30度定律、正反打、灯光物理级描述
# ================================================================

SHOT_DESIGN_SYSTEM = """你是资深电影导演兼摄影指导(DP)。用户给你故事文档，你需要从零设计专业分镜脚本——不仅是"拍什么"，更是"怎么拍"。

=== 电影语法 (铁的规则) ===

[180度轴线规则]
- 对话/对峙场景：在两个角色之间画一条假想的"轴线"，所有机位必须在轴线同一侧
- 角色A始终在画左，角色B始终在画右——不能跳轴导致观众空间错乱

[30度定律]
- 同主体相邻镜头之间机位必须改变至少30度角，否则产生跳切
- 解决方案: 改变景别(全→中→近→特)或改变角度(正面→3/4侧→侧面)

[镜头覆盖策略]
- 每场景: 建立镜头(Master) → 中景覆盖(Coverage) → 特写强调(Insert)
- 对话用正反打: OTS过肩→单人特写→反应镜头→回OTS

=== 镜头运动 (每镜只用一种，不叠加) ===
push-in(推向主体) / pull-out(拉远) / pan(水平摇) / tracking(跟拍)
orbit(环绕) / crane(升降) / handheld(手持抖动)

=== 摄影技法 ===
- 浅景深(shallow DOF): 特写和情绪镜头
- 深景深(deep focus): 建立镜头和群像
- 低调光(low-key): 悬疑/紧张，大面积阴影
- 高调光(high-key): 日常/轻松/培训

=== 情绪弧线 ===
- 读全文后先画情绪曲线: 起始→发展→转折→高潮→回落→收束
- 紧张场景: 低角度、手持、短镜头(2-3s)、低调光
- 温馨场景: 眼平、固定机位、长镜头(4-6s)、暖色温3200K

=== 动作动词 (电影级词汇) ===
不是"走路"而是"大步流星/缓步踱行/踉跄前行"
不是"看"而是"凝视/扫视/怒目而视/偷瞄"
动词前加力度: 缓慢/急速/有力/轻柔/果断地

=== 灯光描述 (物理级精确) ===
写成: "主光从画左45度打来，色温3200K暖黄，辅光从画右反射补光，光比4:1"
不写: "温暖的光线"

=== 旁白时长约束 ===
中文TTS语速约4字/秒。旁白字数 ≤ 镜头时长×4（3s镜头≤12字，5s≤20字）

=== raw_visual 格式 (中文50-100字) ===
"[光影氛围]. [角色+位置+姿势]. [动作关键瞬间]. [构图: 景别+角度+景深]"

=== 输出JSON ===
{"title":"标题","genre":"类型","global_tone":"基调",
 "emotion_curve":"情绪弧线: 平静→紧张→高潮→坚定",
 "spatial_axis":"空间轴线: 柜台画右,门口画左,轴线为门-柜台连线",
 "shots":[{"id":"SC01","raw_visual":"50-100字","narration":"旁白",
   "sfx":"音效","original_duration":秒数(2-8),
   "characters":[{"name":"角色名","role":"身份","detailed_appearance":"枚举式外貌"}],
   "location":"场景名","location_detail":"具体位置",
   "action_summary":"谁做什么+怎么做+力度(15-30字)",
   "camera_hint":"建立远景/中景/过肩OTS/单人特写/插入特写/跟拍/POV/俯拍/仰拍/手持",
   "camera_movement":"push-in/pull-out/pan/track/orbit/crane/static/handheld 选一",
   "lighting":"主光方向+色温+光比",
   "on_screen_text":"字幕","mood":"情绪标签",
   "axis_note":"A左B右/门外侧/主观POV"}],
 "scene_map":{"场景名":["SC01","SC03"]},
 "character_summary":{"角色名":"固定外貌50-80字"}}
只输出JSON。"""

SHOT_DESIGN_USER = """请阅读以下文档，通盘分析内容后，设计专业的分镜脚本：

=== 文档内容 ===
{document}

=== 参数 ===
视觉风格: 3D卡通
时长模式: {duration_mode}

请根据文档内容，自主决定镜头数量、每镜内容和时长，输出完整的分镜JSON。"""


# ================================================================
# System Prompt 1b: 全自动 — Phase 1 内容分析 → Phase 2 导演设计
# ================================================================

ANALYZE_SYSTEM = """你是资深剧本分析师。通读故事文档，提取内容本质，不做创作决策。

=== 分析维度 ===

[题材/类型]
判断文档属于什么类型：悬疑/喜剧/爱情/科幻/奇幻/动作/历史/职场/教育/儿童/广告/宣传
用一句话概括核心故事。

[情绪曲线]
标记情绪走向: 起始→发展→转折→高潮→回落→收束
标注每个关键节点的情绪标签（紧张/温馨/悲伤/振奋/悬疑/轻松）

[角色体系]
列出所有有名字的角色，每个角色：
- 姓名+身份
- 在故事中的作用（推动者/阻碍者/旁观者/导师）
- 性格关键词（3-5个）
- 外貌固定描述（年龄+性别+身高+体型+发色+上装+下装+配饰）

[场景清单]
列出所有场景地点，每个场景:
- 场景名称
- 空间布局简述
- 在此发生的核心事件

[节奏分析]
整体节奏：快节奏/慢节奏/张弛交替
标记哪里该快（多镜短切）、哪里该慢（长镜抒情）

[调性建议]
基于以上分析，给出全局视觉调性建议（不是具体风格，是感受方向）：
- 色调倾向（暖/冷/中性）
- 光线倾向（明亮高调/昏暗低调/自然柔和）
- 氛围关键词（3-5个英文词）

=== 输出JSON ===
{{"genre":"题材","core_story":"一句话核心故事",
 "emotion_curve":"起始→发展→转折→高潮→回落→收束，标注情绪",
 "characters":[{{"name":"名","role":"身份","function":"作用","personality":"性格",
   "appearance":"外貌50-80字"}}],
 "scenes":[{{"name":"场景名","layout":"空间布局","event":"核心事件"}}],
 "pacing":"节奏分析，快慢标注",
 "tone_advice":"调性建议（英文2-3句）"}}
只输出JSON。"""

ANALYZE_USER = """请分析以下文档，提取内容本质，不做创作决策：

=== 文档内容 ===
{document}"""


SHOT_DESIGN_AUTO_SYSTEM = """你是资深电影导演。你收到的不是原始文档，而是剧本分析师提取好的内容分析报告。你的工作是基于这份分析报告，做出所有导演层面的创作决策。

=== 导演决策清单 ===

[风格选择]
根据分析报告中的"调性建议"，自主选择最合适的视觉风格:
- 3D卡通: Pixar-style 3D animation, vibrant colors, soft lighting
- 2D扁平: flat vector illustration, minimalist, clean lines
- 写实简化: semi-realistic, stylized realism, cinematic lighting
- 素描线稿: pencil sketch, black and white, hand-drawn
可以混合创造，输出到 visual_style_directive。

[时长分配]
总时长约束: {duration_note}
根据分析报告的"节奏分析"分配每镜时长:
- 快节奏段落: 2-4秒/镜，密集短切
- 正常叙事: 4-6秒/镜
- 抒情慢镜: 6-8秒/镜
所有镜头时长之和必须在约束范围内。

[镜头设计]
根据分析报告的"情绪曲线"和"场景清单"设计镜头:
- 紧张→低角度、手持、短镜、低调光
- 温馨→眼平、固定、长镜、暖色温3200K
- 高潮→快速推近、多镜连切

[运镜选择]
每镜只选一种: push-in / pull-out / pan / tracking / orbit / crane / handheld / static

[灯光设计]
每镜写明: 主光方向+色温+光比

=== 电影语法（必须遵守） ===
[180度轴线规则] 对话场景所有机位在轴线同侧，A左B右不能跳轴
[30度定律] 同主体相邻镜头机位改变≥30度
[镜头覆盖] 每场景: Master建立 → Coverage中景 → Insert特写

=== 旁白约束 ===
中文TTS语速约4字/秒。旁白字数 ≤ 镜头时长×4。

=== 输出JSON ===
{{"title":"标题","global_tone":"基调","visual_style_directive":"你选的风格（英文2-3句）",
 "emotion_curve":"情绪弧线",
 "shots":[{{"id":"SC01","raw_visual":"50-100字中文","narration":"旁白",
   "sfx":"音效","original_duration":秒数,
   "characters":[{{"name":"角色名(从分析报告取)","role":"身份",
     "detailed_appearance":"从分析报告逐字复制外貌"}}],
   "location":"场景名(从分析报告取)","location_detail":"具体位置",
   "action_summary":"谁做什么+怎么做+力度(15-30字)",
   "camera_hint":"景别","camera_movement":"运镜","lighting":"灯光",
   "on_screen_text":"字幕","mood":"情绪标签"}}],
 "scene_map":{{"场景名":["SC01"]}},
 "character_summary":{{"角色名":"从分析报告逐字复制外貌"}}}}
只输出JSON。"""

SHOT_DESIGN_AUTO_USER = """=== 剧本分析报告 ===
{analysis}

=== 时长约束 ===
总时长目标: {dur_goal}

基于以上分析报告，做出所有导演创作决策，输出完整分镜JSON。"""


# ================================================================
# System Prompt 2: 视觉圣经 — Round 1，建立全片风格锚点
# ================================================================

BIBLE_SYSTEM = """你是影视美术指导。分析所有分镜，输出"视觉圣经"确保全片视觉一致。
若提供了 CHARACTER_SUMMARY（角色身份证），必须逐字复制，不得改写。

=== 角色外貌模板（枚举格式，逗号分隔） ===
"年龄,性别,身高,体型,发色,上装(色/款/质),下装,鞋,配饰"
例: "30岁,男,178cm,瘦高,黑色短发,白色棉质衬衫,深蓝牛仔裤,棕色皮鞋,银框眼镜"

=== 场景模板（3个字段，不可省略） ===
每个场景必须包含:
- layout: 空间大小+道具位置+标志物（30-50词英文）
  例: "Modern office lobby, 8x10m, reception desk at center back, floor-to-ceiling windows on left wall, marble floor"
- lighting: 主光方向+色温+光比（固定格式）
  例: "Key light from window-left at 45°, 5600K daylight, fill from right bounce, ratio 4:1"
- color_palette: 3-4色 英文
  例: "warm beige, deep navy, sage green, brass accent"

=== 输出JSON ===
{{"global_style":"色温+主色调+光线质量（2-3句英文）",
 "characters":{{"角色名":{{"appearance":"枚举模板","anchor_shot":"首次出场镜头ID"}}}},
 "locations":{{"场景名":{{"layout":"布局","lighting":"灯光","color_palette":"配色"}}}},
 "shot_connections":["SC01→SC02: 过渡说明（约15字）"]}}
只输出JSON。"""

BIBLE_USER = """风格前缀: {style_prefix}

=== CHARACTER_SUMMARY（角色身份证，按枚举模板格式，不可修改） ===
{character_summary}

分镜数据:
{shots_json}

按模板格式生成视觉圣经。角色外貌从 CHARACTER_SUMMARY 逐字复制。
每个场景必须包含 layout / lighting / color_palette 三个字段。"""


# ================================================================
# System Prompt 4: Prompt 生成器 — Round 2，每镜头 image+video prompt
# 核心: 占位符{CHAR:name}、6类错误预防、4段强制结构
# ================================================================

PROMPT_GEN_SYSTEM = """你是AI视频Prompt工程师+摄影指导，专精 Seedance 2.0 首帧生视频。

输出JSON数组: [{"shot_id":"SC01","image_prompt":"...","video_prompt":"..."}]

=== Seedance 核心 ===
- first_frame I2V: 每镜头独立关键帧作为起始画面
- video_prompt 中文 50-80字（越短越稳定），每镜一种运动一种动作
- 追求"几乎不动"的微运动: 4-8s干净片段 > 10s复杂运动
- 运镜写节奏词不写技术参数（"slow smooth push-in" 不写 "24fps f/2.8"）

=== 规则 ===

规则0 — {CHAR:角色名} 占位符（最高优先级）
  image_prompt 中只写占位符，不写角色外貌。系统自动替换。

规则1 — 角色主镜锚定
  非主镜镜头追加: "CRITICAL: [角色名] must be IDENTICAL to master shot XX."

规则2 — LOCATION LOCK: 场景描述从分镜数据逐字复制，不得改写

规则3 — STYLE LOCK: 所有镜头以相同全局风格描述开头

规则4 — EMOTION ARC: 情绪决定光线/色调/角色姿态，过渡平滑不突变

规则5 — CAMERA: image_prompt 含 camera_hint 关键词
  video_prompt 从 camera_movement 取运动

规则6 — 动作量化: 幅度量化为具体数字
  "抬杯约5cm" "转头约30度" "推镜2-5%"
  写明不动部分: "仅右手和前臂运动，躯干和头部保持静止"

规则7 — NARRATIVE CHAIN: 从前镜结束状态开始，结束后镜可承接的干净定格

=== video_prompt 格式 (中文 50-80字，给 Seedance，5段缺一不可) ===

[主体] 角色名 + 画面位置 + 姿势（从参考图出）
  例: "主角A，画左站立，右手持文件，目光注视文件内容"

[动作] 单一微动作 + 幅度 + 速度 + 不动部分
  static运镜时: "主体微呼吸感，无大幅动作"

[镜头] 运镜类型 + 方向 + 速度 + 量化幅度（每镜只用一种运镜）
  static:  "三脚架固定镜头，无相机移动"
  push-in: "慢速平滑推镜2-5%，水平线锁定"
  handheld: "微手持晃动，纪录片临场感，幅度不超过画面3%"
  orbit: "缓慢环绕主体约10度，保持主体居中"
  pan: "平滑水平摇镜，速度均匀，无垂直漂移"
  tracking: "侧向跟拍，背景视差，速度恒定"
  crane: "缓慢垂直升降，匀速无顿挫"
  pull-out: "缓慢拉远2-5%，揭示环境"

[风格] 光线+色调锚点（从视觉圣经取）

[禁止] 运镜专属负面词（从下方映射表选取）+ 通用禁止词

=== 运镜-负面词映射 ===
push-in / pull-out: no jitter, no speed change, no edge wobble
handheld: no excessive shake, no motion blur, no focus drift
orbit / crane: no background warp, no perspective shift, no distortion
static: no camera movement, no frame drift, no subtle shift
pan / tracking: no vertical drift, no speed variation, no rolling shutter

=== 通用禁止词（所有 video_prompt 必须包含） ===
no face drift, no limb warp, no texture flicker, no added objects, no color shift

=== image_prompt 格式 (英文 200-300词，给 Seedream，7段式) ===

词序=权重，最重要元素放最前。每段之间用句号分隔，形成自然段落。
禁止使用 "high quality, masterpiece, 8K, ultra-detailed" 等空泛修饰词。

1. [主体] 角色身份证 + 姿势 + 画面位置（权重最高，放最前）
   例: "Character Model [主角A]: male,30,178cm,slim,black short hair,white cotton shirt,dark blue jeans,brown leather shoes. Standing at counter left, holding a document, eyes fixed on paper."

2. [姿态] 静态起始帧。写镜头开始瞬间的定格状态。
   例: "Frozen mid-gesture, right hand extended toward document, body still, left hand resting on counter."

3. [场景] 从分镜数据逐字复制 location_layout + location_colors。不得改写。
   例: "{location_layout}. Color palette: {location_colors}."

4. [构图] camera_hint + 焦距 + 景深。用摄影术语。
   例: "Medium shot, waist-up framing, 85mm lens, shallow depth of field, bokeh background."

5. [光影] 从分镜数据逐字复制 location_lighting。不得改写。
   例: "{location_lighting}."

6. [风格] style_prefix + global_style
   例: "{style_prefix}. {global_style}."

7. [品质] 精简一行
   "sharp focus, consistent character design, clean background, cinematic lighting."

只输出JSON。"""

PROMPT_GEN_USER = """=== 视觉圣经 ===
全局风格: {global_style}
角色圣经: {character_bible}
场景圣经: {location_bible}
镜头衔接: {shot_connections}

=== 参数 ===
风格前缀: {style_prefix}
比例: adaptive  分辨率: 720p

=== 情绪弧线 ===
{emotion_arc}

=== 分镜列表（含叙事链、相机指令、时长、场景模板） ===
{shots_with_context}

为每个镜头生成 image_prompt(英文) 和 video_prompt(中文)。

image_prompt: 英文 200-300词，7段式（主体/姿态/场景/构图/光影/风格/品质）。
  第1段(主体)放最重要元素，词序=权重。第3、5段从分镜数据逐字复制，不得改写。
  禁止使用 "high quality, masterpiece, 8K, ultra-detailed" 空泛词。
严格使用 {{{{CHAR}}:角色名}} 占位符。
video_prompt: 中文 50-80字，5段(主体/动作/镜头/风格/禁止)缺一不可，禁止词根据运镜从映射表选取。"""


# ================================================================
# 函数实现
# ================================================================

def _call_llm(client, messages, temperature, max_tokens, max_retries=3):
    """调用 DeepSeek API，自动重试 3 次（指数退避 5s→10s→20s）"""
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="deepseek-v4-pro", messages=messages,
                timeout=120, temperature=temperature, max_tokens=max_tokens,
                thinking={"type": "enabled"}, reasoning_effort="high"
            )
            return response.choices[0].message.content
        except Exception as e:
            if attempt < max_retries - 1:
                delay = min(5 * (2 ** attempt), 30)
                time.sleep(delay)
            else:
                raise


def design_shots_from_document(document_text, config=None):
    """从文档设计分镜。auto 模式=完全创作自由，semi_auto=遵循用户配置。"""
    if config is None:
        config = {}
    mode = config.get('mode', 'semi_auto')
    lang = config.get('language', DEFAULT_LANGUAGE)
    lang_word = LANGUAGES.get(lang, LANGUAGES[DEFAULT_LANGUAGE])['prompt']

    client = _get_client()

    if mode == 'auto':
        total_sec = config.get('total_duration', 0)
        if total_sec > 0:
            duration_note = f'所有镜头时长之和必须在{total_sec}秒以内（±10%）。'
            dur_goal = f'{total_sec} 秒（±10%可接受）'
        else:
            duration_note = '总时长由你根据故事自然节奏自主决定。'
            dur_goal = '由你自主决定'

        # === Phase 1: 剧本分析 — 提取内容本质，不做创作决策 ===
        content = _call_llm(client,
            [{"role": "system", "content": f"输出语言: {lang_word}\n\n{ANALYZE_SYSTEM}"},
             {"role": "user", "content": ANALYZE_USER.format(document=document_text)}],
            0.3, 16000)
        analysis = _extract_json(content)

        # === Phase 2: 导演设计 — 基于分析报告做创作决策 ===
        analysis_json = json.dumps(analysis, ensure_ascii=False, indent=2)
        content = _call_llm(client,
            [{"role": "system", "content": f"输出语言: {lang_word}\n\n{SHOT_DESIGN_AUTO_SYSTEM.format(duration_note=duration_note)}"},
             {"role": "user", "content": SHOT_DESIGN_AUTO_USER.format(
                 analysis=analysis_json, dur_goal=dur_goal)}],
            0.6, 32000)
        result = _extract_json(content)
        # 将分析结果也注入返回，供上游使用
        result['analysis'] = analysis
        if isinstance(result, list):
            result = {'title': '未命名', 'shots': result, 'scene_map': {}, 'character_summary': {}}
        return result

    # semi_auto 模式：单次调用
    duration_mode = config.get('duration_mode', 'uniform')
    system = f"输出语言: {lang_word}\n\n{SHOT_DESIGN_SYSTEM}"
    user = SHOT_DESIGN_USER.format(document=document_text, duration_mode=duration_mode)
    content = _call_llm(client,
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        0.5, 32000)
    result = _extract_json(content)
    if isinstance(result, list):
        result = {'title': '未命名', 'shots': result, 'scene_map': {}, 'character_summary': {}}
    return result


def generate_prompts(shots, config, character_summary=None):
    """两轮生成: R1视觉圣经 → R2逐镜头Prompt → 占位符替换 → 主镜锚定 → 验证。"""
    mode = config.get('mode', 'semi_auto')
    lang = config.get('language', DEFAULT_LANGUAGE)
    lang_word = LANGUAGES.get(lang, LANGUAGES[DEFAULT_LANGUAGE])['prompt']
    if mode == 'auto':
        # 全自动: 使用 LLM 自主选择的风格
        style_prefix = config.get('visual_style_directive',
                                   STYLE_TEMPLATES['3d_cartoon']['prompt'])
    else:
        style_key = config.get('style_template', '3d_cartoon')
        style_prefix = STYLE_TEMPLATES.get(style_key, STYLE_TEMPLATES['3d_cartoon'])['prompt']
    duration = DURATION_MODES.get(config.get('duration_mode', 'uniform'),
                                   DURATION_MODES['uniform'])['default_seconds']
    char_summary_text = json.dumps(character_summary or {}, ensure_ascii=False, indent=2)

    # 构建镜头基础数据
    shots_basic = [{
        'id': s['id'], 'raw_visual': s.get('raw_visual', ''),
        'narration': s.get('narration', ''), 'action_summary': s.get('action_summary', ''),
        'characters': [{'name': c.get('name', '')} for c in s.get('characters', [])],
        'location': s.get('location', ''), 'on_screen_text': s.get('on_screen_text', ''),
        'original_duration': s.get('original_duration'),
        'mood': s.get('mood', ''), 'camera_hint': s.get('camera_hint', ''),
        'camera_movement': s.get('camera_movement', 'static'),
        'lighting': s.get('lighting', ''), 'axis_note': s.get('axis_note', '')
    } for s in shots]
    shots_basic_json = json.dumps(shots_basic, ensure_ascii=False, indent=2)

    # 角色主镜映射: 记录每个角色首次出场的镜头
    character_master_refs = {}
    for s in shots:
        for char in s.get('characters', []):
            name = char.get('name', '')
            if name and name not in character_master_refs:
                character_master_refs[name] = s['id']

    client = _get_client()

    # === Round 1: 视觉圣经 ===
    bible = _extract_json(_call_llm(client, [
        {"role": "system", "content": f"输出语言: {lang_word}\n\n{BIBLE_SYSTEM}"},
        {"role": "user", "content": BIBLE_USER.format(
            style_prefix=style_prefix, character_summary=char_summary_text,
            shots_json=shots_basic_json)}
    ], 0.4, 16000))

    # === 情绪弧线: 前→当前→后 情绪流向 ===
    mood_pairs = []
    for i, s in enumerate(shots):
        prev_m = shots[i-1].get('mood', '起始') if i > 0 else '起始'
        next_m = shots[i+1].get('mood', '结束') if i < len(shots)-1 else '结束'
        mood_pairs.append(f"  {s['id']}: [{prev_m}] → **{s.get('mood','未指定')}** → [{next_m}]")
    emotion_arc = "情绪弧线:\n" + '\n'.join(mood_pairs)

    # === 叙事链 + 相机 + 角色锚定 ===
    shots_with_context = []
    for i, s in enumerate(shots):
        prev_desc = f"[{shots[i-1]['id']}] {shots[i-1].get('raw_visual','')[:120]}" if i > 0 else '[开头]'
        next_desc = f"[{shots[i+1]['id']}] {shots[i+1].get('raw_visual','')[:120]}" if i < len(shots)-1 else '[结尾]'
        cam_hint = s.get('camera_hint', '')
        cam_instr = CAMERA_INSTRUCTIONS.get(cam_hint, 'medium shot')

        # 角色主镜标注
        char_notes = []
        for char in s.get('characters', []):
            nm = char.get('name', '')
            if nm and character_master_refs.get(nm) != s['id']:
                master = character_master_refs.get(nm, '')
                if master:
                    char_notes.append(f"{nm}: 主镜={master}(外貌锚定该镜)")
        char_refs = '; '.join(char_notes) if char_notes else '所有角色均为首次出场(主镜)'

        shots_with_context.append({
            'id': s['id'], 'raw_visual': s.get('raw_visual', ''),
            'action_summary': s.get('action_summary', ''),
            'narration': s.get('narration', ''),
            'characters': [{'name': c.get('name', '')} for c in s.get('characters', [])],
            'location': s.get('location', ''), 'mood': s.get('mood', ''),
            'duration': s.get('final_duration', duration),
            'camera_hint': cam_hint, 'camera_movement': s.get('camera_movement', 'static'),
            'camera_instruction': cam_instr, 'lighting': s.get('lighting', ''),
            'axis_note': s.get('axis_note', ''),
            'character_master_refs': char_refs,
            'narrative_chain': f"前: {prev_desc} → 当前: {s.get('action_summary','')[:100]} → 后: {next_desc}",
            'on_screen_text': s.get('on_screen_text', ''),
            'location_layout': bible.get('locations', {}).get(s.get('location', ''), {}).get('layout', ''),
            'location_lighting': bible.get('locations', {}).get(s.get('location', ''), {}).get('lighting', ''),
            'location_colors': bible.get('locations', {}).get(s.get('location', ''), {}).get('color_palette', '')
        })
    shots_ctx_json = json.dumps(shots_with_context, ensure_ascii=False, indent=2)

    # === Round 2: 逐镜头 Prompt ===
    global_style = bible.get('global_style', style_prefix)
    character_bible = json.dumps(bible.get('characters', {}), ensure_ascii=False, indent=2)
    location_bible = json.dumps(bible.get('locations', {}), ensure_ascii=False, indent=2)
    shot_connections = '\n'.join(bible.get('shot_connections', []))

    prompts = _extract_json(_call_llm(client, [
        {"role": "system", "content": f"输出语言: {lang_word}\n\n{PROMPT_GEN_SYSTEM}"},
        {"role": "user", "content": PROMPT_GEN_USER.format(
            global_style=global_style, character_bible=character_bible,
            location_bible=location_bible, shot_connections=shot_connections,
            style_prefix=style_prefix, duration=duration,
            emotion_arc=emotion_arc, shots_with_context=shots_ctx_json,
            resolution=config.get('resolution', '1920x1080'))}
    ], 0.4, 32000))

    # 后处理
    all_chars = character_summary or bible.get('characters', {})
    prompts = _inject_character_cards(prompts, all_chars)
    prompts = _inject_master_references(prompts, shots, character_master_refs)
    _validate_prompts(prompts, shots, all_chars)
    return prompts


# ================================================================
# 后处理函数
# ================================================================

def _inject_character_cards(prompts, character_summary):
    """{CHAR:角色名} → "Character Model [角色名]: 外貌描述"。
    同一角色所有镜头100%逐字一致——代码保证，不靠LLM记忆。"""
    for prompt in prompts:
        for name, desc in character_summary.items():
            placeholder = f"{{CHAR:{name}}}"
            replacement = f"Character Model [{name}]: {desc}"
            prompt['image_prompt'] = prompt['image_prompt'].replace(placeholder, replacement)
            prompt['video_prompt'] = prompt.get('video_prompt', '').replace(placeholder, replacement)
    return prompts


def _inject_master_references(prompts, shots, character_master_refs):
    """非主镜镜头自动追加锚定: 'CRITICAL: 该角色外貌必须与主镜XX完全一致'。"""
    shot_map = {s['id']: s for s in shots}
    for prompt in prompts:
        sid = prompt.get('shot_id', '')
        shot = shot_map.get(sid)
        if not shot: continue
        for char in shot.get('characters', []):
            name = char.get('name', '')
            if not name: continue
            master = character_master_refs.get(name, '')
            if master and master != sid:
                anchor = (f"\n\nCRITICAL MASTER REFERENCE: [{name}] was first established in "
                          f"shot {master}. The appearance MUST be IDENTICAL — same facial features, "
                          f"body proportions, clothing colors and details. "
                          f"This is the SAME person from a different camera angle. Zero deviation.")
                if anchor not in prompt['image_prompt']:
                    prompt['image_prompt'] += anchor
    return prompts


def _validate_prompts(prompts, shots, character_summary):
    """验证: 占位符残留/角色完整性/prompt长度/中文占比/防错关键词。"""
    import logging
    log = logging.getLogger('llm_service')
    shot_map = {s['id']: s for s in shots}

    for prompt in prompts:
        sid = prompt.get('shot_id', 'UNKNOWN')
        img = prompt.get('image_prompt', '')
        vid = prompt.get('video_prompt', '')

        # 占位符残留
        residual = re.findall(r'\{CHAR:[^}]+\}', img + vid)
        if residual:
            log.warning(f"  {sid}: 未替换的占位符: {residual}")

        # 角色完整性
        shot = shot_map.get(sid)
        if shot and character_summary:
            for char in shot.get('characters', []):
                cn = char.get('name', '')
                if cn and cn in character_summary and f"Character Model [{cn}]" not in img:
                    log.warning(f"  {sid}: 缺少角色[{cn}]身份证，自动补全")
                    prompt['image_prompt'] += f"\nCharacter Model [{cn}]: {character_summary[cn]}"

        # 长度
        if len(img) < 100:
            log.warning(f"  {sid}: image_prompt 过短({len(img)}字)")

        # 中文占比 + 防错词
        if vid:
            cn_chars = len(re.findall(r'[一-鿿]', vid))
            total = len(vid.replace(' ', '').replace('\n', ''))
            if cn_chars / max(total, 1) < 0.3:
                log.warning(f"  {sid}: video_prompt 中文占比过低({cn_chars/max(total,1):.0%})")
            if len(vid) > 300:
                log.warning(f"  {sid}: video_prompt 过长({len(vid)}字)")
            for kw in ['禁止', 'smooth', 'steady', 'stabilized', '无抖动']:
                if kw not in vid:
                    log.warning(f"  {sid}: 缺少防错词 '{kw}'")


def _get_client():
    return OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)


def _extract_json(text):
    text = text.strip()
    match = re.search(r'\{[\s\S]*\}|\[[\s\S]*\]', text)
    return json.loads(match.group()) if match else json.loads(text)
