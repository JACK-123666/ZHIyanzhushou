"""
LLM 服务 — DeepSeek V4 Pro 驱动分镜设计 + Prompt 生成
核心: 角色身份证(占位符替换) + 角色主镜锚定 + 情绪弧线 + 叙事链
"""

import json, re, time
from openai import OpenAI
from config import (DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL,
                    STYLE_TEMPLATES, DURATION_MODES, CAMERA_INSTRUCTIONS,
                    AUTO_DURATION_OPTIONS)

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

=== 时代风格锁定（最高优先级） ===
- 根据文档内容判断时代背景，锁定服装/建筑/道具风格
- 古代中国→汉服交领/布衣短褐/木屐草鞋/夯土建筑/青铜铁器/烛火油灯
- 所有角色服装必须符合同一时代。禁止混入现代元素（T恤/西装/眼镜/手机/电子屏）
- 所有场景道具必须符合同一时代。禁止现代建筑/电器/交通工具
- 所有 on_screen_text 字幕必须用纯中文，禁止英文

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

=== 旁白约束 ===
中文TTS语速约4字/秒。旁白字数 ≤ 镜头时长×4（3s镜头≤12字，5s≤20字）。
旁白为纯文本，不使用任何 SSML/HTML 标签。直接写朗读文本即可。

=== raw_visual 格式 (中文50-100字) ===
"[光影氛围]. [角色+位置+姿势]. [动作关键瞬间]. [构图: 景别+角度+景深]"

=== 输出JSON ===
{"title":"标题","genre":"类型","global_tone":"基调",
 "emotion_curve":"情绪弧线: 平静→紧张→高潮→坚定",
 "spatial_axis":"空间轴线: 柜台画右,门口画左,轴线为门-柜台连线",
 "shots":[{"id":"SC01","raw_visual":"50-100字","narration":"旁白",
   "sfx":"音效","original_duration":秒数(2-8),
   "characters":[{"name":"角色名","role":"身份","detailed_appearance":"枚举外貌≤100字,逗号分隔: 年龄,性别,身高,体型,发色,上装,下装,鞋,配饰"}],
   "location":"场景名","location_detail":"具体位置",
   "action_summary":"谁做什么+怎么做+力度(15-30字)",
   "action_peaks":[{"label":"动作名(必须包含动词)","description":"该动作最戏剧化瞬间的视觉描述(大幅动作)50-80字"}] (每镜必须有! 建立镜头1个峰值，有角色的镜头必填2个峰值; 动作必须大幅度——'举起→砸下'而非'抬手→放下'),
   "camera_hint":"建立远景/中景/过肩OTS/单人特写/插入特写/跟拍/POV/俯拍/仰拍/手持",
   "camera_movement":"push-in/pull-out/pan/track/orbit/crane/static/handheld 选一",
   "lighting":"主光方向+色温+光比",
   "on_screen_text":"字幕","mood":"情绪标签",
   "axis_note":"A左B右/门外侧/主观POV"}],
 "scene_map":{"场景名":["SC01","SC03"]},
 "character_summary":{"角色名":"枚举外貌(≤100字): 年龄,性别,身高,体型,发色,上装(色/款/质),下装,鞋,配饰"}}
只输出JSON。"""

SHOT_DESIGN_USER = """请阅读以下文档，通盘分析内容后，设计专业的分镜脚本：

=== 文档内容 ===
{document}

=== 参数 ===
视觉风格: {style_label}
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
   "appearance":"枚举外貌≤100字,逗号分隔: 年龄,性别,身高,体型,发色,上装(色/款/质),下装,鞋,配饰"}}],
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
中文TTS语速约4字/秒。旁白字数 ≤ 镜头时长×4。纯文本，不使用任何标签。

=== 输出JSON ===
{{"title":"标题","global_tone":"基调","visual_style_directive":"你选的风格（英文2-3句）",
 "emotion_curve":"情绪弧线",
 "shots":[{{"id":"SC01","raw_visual":"50-100字中文","narration":"旁白",
   "sfx":"音效","original_duration":秒数,
   "characters":[{{"name":"角色名(从分析报告取)","role":"身份",
     "detailed_appearance":"从分析报告逐字复制外貌"}}],
   "location":"场景名(从分析报告取)","location_detail":"具体位置",
   "action_summary":"谁做什么+怎么做+力度(15-30字)",
   "action_peaks":[{{"label":"动作名(必须含动词)","description":"大幅动作视觉描述50-80字"}}] (每镜必有! 建立镜头1个，有角色2个; 动作大幅度——'举起→砸下'),
   "camera_hint":"景别","camera_movement":"运镜","lighting":"灯光",
   "on_screen_text":"字幕","mood":"情绪标签"}}],
 "scene_map":{{"场景名":["SC01"]}},
 "character_summary":{{"角色名":"从分析报告逐字复制外貌"}}}}
只输出JSON。

=== 本周热点剪辑趋势 ===
{trending_context}

在分镜设计中参考以上趋势，融入适合本故事风格的流行技法。"""

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

输出JSON数组: [{"shot_id":"SC01","image_prompt":"...","video_prompt":"...","peak_prompts":[...]}]

peak_prompts 可选。仅当分镜数据中该镜头有 action_peaks 时才生成。
peak_prompts 格式: [{"label":"动作名","image_prompt":"英文","video_prompt":"英文"}]
- 每个 action_peak 生成一对 prompt
- image_prompt: 描述该动作瞬间的静态画面（角色在该动作高潮点的姿态）
- video_prompt: 描述从上一个状态过渡到该动作瞬间的运动（从起始帧→该峰值帧）
- 第一个 peak 的起始帧是该镜的主 image_prompt，后续 peak 的起始帧是上一个 peak 的 image_prompt
- 纯建立/过渡镜头不生成 peak_prompts

=== Seedance 核心 ===
- first_frame I2V: 每镜头独立关键帧作为起始画面
- video_prompt 英文 80-120 words（越短越稳定），每镜一种运动一种动作
- 追求"几乎不动"的微运动: 4-8s干净片段 > 10s复杂运动
- 运镜写节奏词不写技术参数（"slow smooth push-in"，不写 "24fps f/2.8"）
- video_prompt 中角色引用用 {CHAR:角色名} 占位符，系统自动替换为英文外表描述

=== 规则 ===

规则0 — {CHAR:角色名} 占位符（最高优先级）
  image_prompt 中只写占位符，不写角色外貌。系统自动替换。

规则1 — 角色主镜锚定
  非主镜镜头追加: "CRITICAL: [角色名] must be IDENTICAL to master shot XX."

规则2 — LOCATION LOCK: 场景描述从分镜数据逐字复制，不得改写

规则3 — STYLE LOCK: 所有镜头以相同全局风格描述开头。同时锁定时代背景：古代中国场景禁用 modern/contemporary/electronic/neon/glass-skyscraper 等现代词汇。所有文字/字幕/标识必须是中文。

规则4 — EMOTION ARC: 情绪决定光线/色调/角色姿态，过渡平滑不突变

规则5 — CAMERA: image_prompt 含 camera_hint 关键词
  video_prompt 从 camera_movement 取运动

规则6 — 动作量化: 幅度量化为具体数字
  "抬杯约5cm" "转头约30度" "推镜2-5%"
  写明不动部分: "仅右手和前臂运动，躯干和头部保持静止"

规则7 — NARRATIVE CHAIN: 从前镜结束状态开始，结束后镜可承接的干净定格

=== video_prompt 格式 (英文 80-120 words, for Seedance, 5 sections required) ===

[Subject] Character name {CHAR:Name} + screen position + posture (from reference image)
  e.g. "{CHAR:Protagonist} stands at frame left, holding a document in right hand, eyes focused on the paper."

[Action] Single micro-motion + amplitude + speed + what stays still
  For static shots: "Subject has subtle breathing motion, no large movements."

[Camera] Movement type + direction + speed + quantified amplitude (one per shot)
  static:  "Tripod-locked static shot, no camera movement."
  push-in: "Slow smooth push-in 2-5%, horizon locked."
  handheld: "Subtle handheld wobble, documentary immediacy, shake under 3% of frame."
  orbit: "Slow orbit around subject ~10 degrees, subject stays centered."
  pan: "Smooth horizontal pan, constant speed, no vertical drift."
  tracking: "Lateral tracking alongside subject, background parallax, constant speed."
  crane: "Slow vertical crane rise/lower, smooth elevation, no sudden stops."
  pull-out: "Slow pull-out 2-5%, revealing environment."

[Style] Lighting + color tone anchor (from visual bible)

[Negatives] Movement-specific negatives (from mapping below) + universal negatives

=== 运镜-负面词映射 ===
push-in / pull-out: no jitter, no speed change, no edge wobble
handheld: no excessive shake, no motion blur, no focus drift
orbit / crane: no background warp, no perspective shift, no distortion
static: no camera movement, no frame drift, no subtle shift
pan / tracking: no vertical drift, no speed variation, no rolling shutter

=== 通用禁止词（所有 video_prompt 必须包含） ===
no face drift, no limb warp, no texture flicker, no added objects, no color shift

=== 时代禁止词（所有 image_prompt 和 video_prompt 必须包含） ===
no modern clothing, no modern architecture, no modern technology, no English text, no electronic devices

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

为每个镜头生成 image_prompt(英文) 和 video_prompt(英文)。

image_prompt: 英文 200-300词，7段式（主体/姿态/场景/构图/光影/风格/品质）。
  第1段(主体)放最重要元素，词序=权重。第3、5段从分镜数据逐字复制，不得改写。
  禁止使用 "high quality, masterpiece, 8K, ultra-detailed" 空泛词。
严格使用 {{{{CHAR}}:角色名}} 占位符（image_prompt 和 video_prompt 都用）。
video_prompt: 英文 80-120 words, 5段(Subject/Action/Camera/Style/Negatives)缺一不可，禁止词根据运镜从映射表选取。

如果分镜数据中有 action_peaks（非空数组），必须生成 peak_prompts。
peak_prompts 中每个 peak 的 image_prompt 描述该动作高潮点的静态画面；
video_prompt 描述从上一状态过渡到该峰值的运动。
主 image_prompt 是该镜起始帧，peak_prompts[0] 描述从起始→第一个动作峰值，
peak_prompts[1] 描述从 peak[0]→peak[1]，以此类推。"""


# ================================================================
# 函数实现
# ================================================================

def _call_llm(client, messages, temperature, max_tokens, max_retries=3):
    """调用 DeepSeek API，自动重试 3 次（指数退避 5s→10s→20s）"""
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="deepseek-v4-pro", messages=messages,
                timeout=120, temperature=temperature, max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            if attempt < max_retries - 1:
                delay = min(5 * (2 ** attempt), 30)
                time.sleep(delay)
            else:
                raise RuntimeError(
                    f"LLM 调用失败，已重试 {max_retries} 次: {e}") from e


def design_shots_from_document(document_text, config=None):
    """从文档设计分镜。auto 模式=完全创作自由，semi_auto=遵循用户配置。"""
    if config is None:
        config = {}
    mode = config.get('mode', 'semi_auto')
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
            [{"role": "system", "content": ANALYZE_SYSTEM},
             {"role": "user", "content": ANALYZE_USER.format(document=document_text)}],
            0.3, 16000)
        analysis = _extract_json(content)

        # === Phase 2: 导演设计 — 基于分析报告做创作决策 ===
        analysis_json = json.dumps(analysis, ensure_ascii=False, indent=2)
        # 注入剪辑趋势上下文
        try:
            from services.trend_service import get_weekly_trend_context
            trending_context = get_weekly_trend_context()
        except Exception:
            trending_context = "（暂无趋势数据）"
        system_prompt = SHOT_DESIGN_AUTO_SYSTEM.format(
            duration_note=duration_note, trending_context=trending_context)
        content = _call_llm(client,
            [{"role": "system", "content": system_prompt},
             {"role": "user", "content": SHOT_DESIGN_AUTO_USER.format(
                 analysis=analysis_json, dur_goal=dur_goal)}],
            0.6, 32000)
        result = _extract_json(content)
        # 将分析结果也注入返回，供上游使用
        result['analysis'] = analysis
        if isinstance(result, list):
            result = {'title': '未命名', 'shots': result, 'scene_map': {}, 'character_summary': {}}
        result['shots'] = _enforce_camera_variety(result.get('shots', []))
        return result

    # semi_auto 模式：单次调用
    duration_mode = config.get('duration_mode', 'uniform')
    style_key = config.get('style_template', '3d_cartoon')
    style_label = STYLE_TEMPLATES.get(style_key, STYLE_TEMPLATES['3d_cartoon'])['label']
    system = SHOT_DESIGN_SYSTEM
    user = SHOT_DESIGN_USER.format(document=document_text, duration_mode=duration_mode, style_label=style_label)
    content = _call_llm(client,
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        0.5, 32000)
    result = _extract_json(content)
    if isinstance(result, list):
        result = {'title': '未命名', 'shots': result, 'scene_map': {}, 'character_summary': {}}
    result['shots'] = _enforce_camera_variety(result.get('shots', []))
    return result


def generate_prompts(shots, config, character_summary=None):
    """两轮生成: R1视觉圣经 → R2逐镜头Prompt → 占位符替换 → 主镜锚定 → 验证。"""
    mode = config.get('mode', 'semi_auto')
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
        {"role": "system", "content": BIBLE_SYSTEM},
        {"role": "user", "content": BIBLE_USER.format(
            style_prefix=style_prefix, character_summary=char_summary_text,
            shots_json=shots_basic_json)}
    ], 0.4, 16000))

    # === 后验证: 强制 Bible 角色外貌 = 原始 character_summary（代码保证，不靠 LLM 承诺）===
    if character_summary:
        bible_chars = bible.get('characters', {})
        for char_name, orig_desc in character_summary.items():
            bible_desc = bible_chars.get(char_name, {}).get('appearance', '')
            if bible_desc and bible_desc.strip() != orig_desc.strip():
                import logging
                log = logging.getLogger('llm_service')
                log.warning(f"Bible 改写了角色[{char_name}]外貌，已强制恢复原文")
                log.debug(f"  Bible: {bible_desc[:80]}...")
                log.debug(f"  Original: {orig_desc[:80]}...")
                if char_name not in bible_chars:
                    bible_chars[char_name] = {}
                bible_chars[char_name]['appearance'] = orig_desc
        # 同时确保 Bible 不漏掉任何角色
        for char_name, orig_desc in character_summary.items():
            if char_name not in bible_chars:
                bible_chars[char_name] = {'appearance': orig_desc}
        bible['characters'] = bible_chars

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
            'location_colors': bible.get('locations', {}).get(s.get('location', ''), {}).get('color_palette', ''),
            'action_peaks': s.get('action_peaks', [])  # 动作关键帧列表
        })
    shots_ctx_json = json.dumps(shots_with_context, ensure_ascii=False, indent=2)

    # === Round 2: 逐镜头 Prompt ===
    global_style = bible.get('global_style', style_prefix)
    character_bible = json.dumps(bible.get('characters', {}), ensure_ascii=False, indent=2)
    location_bible = json.dumps(bible.get('locations', {}), ensure_ascii=False, indent=2)
    shot_connections = '\n'.join(bible.get('shot_connections', []))

    prompts = _extract_json(_call_llm(client, [
        {"role": "system", "content": PROMPT_GEN_SYSTEM},
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
    """验证: 占位符残留/角色完整性/prompt长度/防错关键词。
    WARNING级=记录但继续，ERROR级=抛异常中断流水线。"""
    import logging
    log = logging.getLogger('llm_service')
    shot_map = {s['id']: s for s in shots}
    errors = []

    for prompt in prompts:
        sid = prompt.get('shot_id', 'UNKNOWN')
        img = prompt.get('image_prompt', '')
        vid = prompt.get('video_prompt', '')

        # --- WARNING: 占位符残留 → 自动清理，不中断 ---
        residual = re.findall(r'\{CHAR:[^}]+\}', img + vid)
        if residual:
            for rp in residual:
                prompt['image_prompt'] = prompt['image_prompt'].replace(rp, '')
                prompt['video_prompt'] = prompt.get('video_prompt', '').replace(rp, '')
            log.warning(f"  {sid}: 清理了未匹配的占位符: {residual}")

        # --- ERROR: 缺少角色身份证 ---
        shot = shot_map.get(sid)
        if shot and shot.get('characters') and character_summary:
            missing_chars = []
            for char in shot.get('characters', []):
                cn = char.get('name', '')
                if cn and cn in character_summary and f"Character Model [{cn}]" not in img:
                    missing_chars.append(cn)
                    # 自动补全
                    prompt['image_prompt'] += f"\nCharacter Model [{cn}]: {character_summary[cn]}"
            if missing_chars:
                log.warning(f"  {sid}: 缺少角色身份证: {missing_chars}，已自动补全")

        # --- ERROR: image_prompt 过短 ---
        if len(img) < 80:
            errors.append(f"{sid}: image_prompt 过短({len(img)}字符)，无法生成有效图片")

        # --- WARNING: video_prompt 质量 ---
        if vid:
            if len(vid) < 40:
                log.warning(f"  {sid}: video_prompt 过短({len(vid)}字符)")
            if len(vid) > 300:
                log.warning(f"  {sid}: video_prompt 过长({len(vid)}字符)")

            # 英文 prompt 必备负面词检查
            neg_required = ['no face drift', 'no limb warp', 'no texture flicker']
            for kw in neg_required:
                if kw.lower() not in vid.lower():
                    log.warning(f"  {sid}: video_prompt 缺少防错词 '{kw}'，自动追加")
                    prompt['video_prompt'] = vid + f", {kw}"

            # 运镜相关负面词检查
            cam_movement = shot.get('camera_movement', 'static') if shot else 'static'
            movement_negatives = {
                'push-in': ['no jitter', 'no speed change'],
                'pull-out': ['no jitter', 'no speed change'],
                'handheld': ['no excessive shake', 'no motion blur'],
                'orbit': ['no background warp', 'no distortion'],
                'crane': ['no background warp', 'no distortion'],
                'static': ['no camera movement', 'no frame drift'],
                'pan': ['no vertical drift', 'no speed variation'],
                'tracking': ['no vertical drift', 'no speed variation'],
            }
            for kw in movement_negatives.get(cam_movement, []):
                if kw.lower() not in vid.lower():
                    log.warning(f"  {sid}: video_prompt 缺少运镜防错词 '{kw}'，自动追加")
                    prompt['video_prompt'] = prompt['video_prompt'] + f", {kw}"

    if errors:
        raise ValueError(f"Prompt 验证失败 ({len(errors)} 项):\n" + '\n'.join(errors))


def _enforce_camera_variety(shots):
    """强制运镜多样性：确保非静态运镜占 >40%，相邻镜头运镜不重复。"""
    import logging, random
    log = logging.getLogger('llm_service')
    if not shots or len(shots) < 3:
        return shots

    # 情绪→运镜优先级映射
    mood_movements = {
        '紧张': ['handheld', 'push-in', 'tracking'],
        '恐惧': ['handheld', 'push-in'],
        '悲伤': ['pull-out', 'static', 'pan'],
        '温馨': ['pan', 'static', 'orbit'],
        '振奋': ['crane', 'orbit', 'push-in'],
        '激昂': ['crane', 'push-in', 'tracking'],
        '悬疑': ['handheld', 'pan', 'push-in'],
        '平和': ['pan', 'static', 'orbit'],
        '庄严': ['crane', 'static', 'pull-out'],
        '轻松': ['pan', 'orbit', 'handheld'],
    }
    all_movements = ['push-in', 'pull-out', 'pan', 'tracking', 'orbit', 'crane', 'handheld', 'static']

    movements = [s.get('camera_movement', 'static') for s in shots]
    static_count = movements.count('static')
    static_ratio = static_count / len(movements)

    if static_ratio <= 0.4:
        # 已经够多样了，只修复相邻重复
        for i in range(1, len(shots)):
            if movements[i] == movements[i-1] and movements[i] != 'static':
                alt = [m for m in all_movements if m not in (movements[i-1],
                       movements[i+1] if i+1 < len(shots) else '')]
                new_m = random.choice(alt) if alt else 'static'
                shots[i]['camera_movement'] = new_m
                movements[i] = new_m
                log.info(f"  运镜修复: {shots[i]['id']} {movements[i-1]}→{new_m} (去重)")
        return shots

    # static 过多：按情绪替换其中一部分
    log.info(f"  运镜多样性: static={static_count}/{len(shots)} ({static_ratio:.0%}), 强制多样化")
    replaced = 0
    target_replace = max(1, int(static_count * 0.5))  # 替换 50% 的 static

    for i, s in enumerate(shots):
        if replaced >= target_replace:
            break
        if s.get('camera_movement', 'static') != 'static':
            continue
        mood = s.get('mood', '平和')
        preferred = mood_movements.get(mood, ['pan', 'orbit'])
        # 排除相邻镜头的运镜
        adj = set()
        if i > 0: adj.add(shots[i-1].get('camera_movement', ''))
        if i < len(shots)-1: adj.add(shots[i+1].get('camera_movement', ''))
        candidates = [m for m in preferred if m not in adj and m != 'static']
        if not candidates:
            candidates = [m for m in all_movements if m not in adj and m != 'static']
        if candidates:
            new_m = candidates[0]
            s['camera_movement'] = new_m
            replaced += 1
            log.info(f"  {s['id']}: static→{new_m} (情绪: {mood})")

    if replaced:
        log.info(f"  运镜多样性: 已替换 {replaced} 个 static 镜头")
    return shots


def _get_client():
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY 环境变量未设置，请在 .env 中配置")
    return OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)


def _extract_json(text):
    text = text.strip()
    match = re.search(r'\{[\s\S]*\}|\[[\s\S]*\]', text)
    if not match:
        raise ValueError(f"LLM 响应中未找到 JSON 结构，原始内容: {text[:200]}")
    return json.loads(match.group())
