"""
LLM 服务 — DeepSeek 驱动分镜设计 + Prompt 生成
"""

import json, re, time
from openai import OpenAI
from config import (DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL,
                    STYLE_TEMPLATES, DURATION_MODES, CAMERA_INSTRUCTIONS)

# ── System Prompts ──

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


PROMPT_GEN_SYSTEM = """你是 Seedance 2.0 视频 Prompt 工程师。

输出JSON数组: [{"shot_id":"SC01","image_prompt":"...","video_prompt":"...","peak_prompts":[...]}]

=== Seedance 2.0 核心规则 ===
- 图片定义了画面中"有什么"（主体、场景、色彩、构图）
- video_prompt 只描述"怎么动"——主体做什么动作、镜头如何运动
- 绝对禁止在 video_prompt 中重新描述角色外貌、场景、色彩——这些已经在图片里了
- 越短越精准: 20-40 words，2-3 句即可
- 每个镜头只描述一种运动、一种动作

=== video_prompt 写法 (20-40 words, 纯动作描述) ===
格式: [主体动作] + [镜头运动]
- 主体动作: 用具体动词，短句。例: "She turns toward the window. Raises her hand slowly."
- 镜头运动: 一个词。static / slow push-in / slow pull-out / gentle pan / smooth orbit
- 不要描述: 角色长相、衣服、场景、灯光、色彩、画质
- 不要写: Subject/Action/Camera/Style/Negatives 分节标题
- 不要写: no face drift, no limb warp 等否定词
- 不要写: high quality, masterpiece, 8K 等空泛词

✅ 正确: "She turns toward window, raises hand slowly. Gentle breeze moves fabric. Static shot."
✅ 正确: "He walks forward through the gate, cloak swaying. Slow push-in."
❌ 错误: "Character Model [Zhang]: male, 30... stands at frame left... no face drift, no limb warp..."

=== image_prompt 写法 (给 Seedream, 英文 100-200词, 4段) ===
1. [主体] {CHAR:角色名} 占位符 + 姿势 + 画面位置 (权重最高)
2. [场景+构图] 从分镜数据取 location_layout + camera_hint
3. [光影+风格] location_lighting + style_prefix + global_style
4. [品质] 一行: "sharp focus, consistent character design, clean composition."

禁止 "high quality, masterpiece, 8K, ultra-detailed"。

=== 成本控制 ===
- 每个镜头时长 4-8 秒，总镜数 ≤10
- 动作峰值 peak_prompts 仅在动作镜头(打斗/追逐/转折)生成，每镜最多 1 个

只输出JSON。"""

PROMPT_GEN_USER = """=== 参数 ===
风格前缀: {style_prefix}

=== 视觉圣经 ===
全局风格: {global_style}
角色圣经: {character_bible}
场景圣经: {location_bible}

=== 情绪弧线 ===
{emotion_arc}

=== 分镜列表 ===
{shots_with_context}

为每个镜头生成 image_prompt 和 video_prompt。
image_prompt: 英文 100-200词，含 {{{{CHAR}}:角色名}} 占位符。
video_prompt: 英文 20-40词，纯动作+运镜，不含角色外貌、不含负面词。"""


# ── 内部工具 ──

def _get_client():
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY 环境变量未设置，请在 .env 中配置")
    return OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)


def _call_llm(client, messages, temperature, max_tokens, max_retries=3):
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


def _extract_json(text):
    text = text.strip()
    match = re.search(r'\{[\s\S]*\}|\[[\s\S]*\]', text)
    if not match:
        raise ValueError(f"LLM 响应中未找到 JSON 结构，原始内容: {text[:200]}")
    return json.loads(match.group())


# ── 分镜设计 ──

def design_shots_from_document(document_text, config=None):
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

        content = _call_llm(client,
            [{"role": "system", "content": ANALYZE_SYSTEM},
             {"role": "user", "content": ANALYZE_USER.format(document=document_text)}],
            0.3, 16000)
        analysis = _extract_json(content)

        analysis_json = json.dumps(analysis, ensure_ascii=False, indent=2)
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
        result['analysis'] = analysis
        if isinstance(result, list):
            result = {'title': '未命名', 'shots': result, 'scene_map': {}, 'character_summary': {}}
        result['shots'] = _enforce_camera_variety(result.get('shots', []))
        return result

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


# ── Prompt 生成 ──

def generate_prompts(shots, config, character_summary=None):
    mode = config.get('mode', 'semi_auto')
    if mode == 'auto':
        style_prefix = config.get('visual_style_directive',
                                   STYLE_TEMPLATES['3d_cartoon']['prompt'])
    else:
        style_key = config.get('style_template', '3d_cartoon')
        style_prefix = STYLE_TEMPLATES.get(style_key, STYLE_TEMPLATES['3d_cartoon'])['prompt']
    duration = DURATION_MODES.get(config.get('duration_mode', 'uniform'),
                                   DURATION_MODES['uniform'])['default_seconds']
    char_summary_text = json.dumps(character_summary or {}, ensure_ascii=False, indent=2)

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

    character_master_refs = {}
    for s in shots:
        for char in s.get('characters', []):
            name = char.get('name', '')
            if name and name not in character_master_refs:
                character_master_refs[name] = s['id']

    client = _get_client()

    # Round 1: 视觉圣经
    bible = _extract_json(_call_llm(client, [
        {"role": "system", "content": BIBLE_SYSTEM},
        {"role": "user", "content": BIBLE_USER.format(
            style_prefix=style_prefix, character_summary=char_summary_text,
            shots_json=shots_basic_json)}
    ], 0.4, 16000))

    # 强制 Bible 角色外貌 = 原始 character_summary
    if character_summary:
        bible_chars = bible.get('characters', {})
        for char_name, orig_desc in character_summary.items():
            bible_desc = bible_chars.get(char_name, {}).get('appearance', '')
            if bible_desc and bible_desc.strip() != orig_desc.strip():
                import logging
                log = logging.getLogger('llm_service')
                log.warning(f"Bible 改写角色[{char_name}]外貌，已强制恢复原文")
                if char_name not in bible_chars:
                    bible_chars[char_name] = {}
                bible_chars[char_name]['appearance'] = orig_desc
        for char_name, orig_desc in character_summary.items():
            if char_name not in bible_chars:
                bible_chars[char_name] = {'appearance': orig_desc}
        bible['characters'] = bible_chars

    # 情绪弧线: 前→当前→后
    mood_pairs = []
    for i, s in enumerate(shots):
        prev_m = shots[i-1].get('mood', '起始') if i > 0 else '起始'
        next_m = shots[i+1].get('mood', '结束') if i < len(shots)-1 else '结束'
        mood_pairs.append(f"  {s['id']}: [{prev_m}] → **{s.get('mood','未指定')}** → [{next_m}]")
    emotion_arc = "情绪弧线:\n" + '\n'.join(mood_pairs)

    # 叙事链上下文
    shots_with_context = []
    for i, s in enumerate(shots):
        prev_desc = f"[{shots[i-1]['id']}] {shots[i-1].get('raw_visual','')[:120]}" if i > 0 else '[开头]'
        next_desc = f"[{shots[i+1]['id']}] {shots[i+1].get('raw_visual','')[:120]}" if i < len(shots)-1 else '[结尾]'
        cam_hint = s.get('camera_hint', '')
        cam_instr = CAMERA_INSTRUCTIONS.get(cam_hint, 'medium shot')

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
            'action_peaks': s.get('action_peaks', [])
        })
    shots_ctx_json = json.dumps(shots_with_context, ensure_ascii=False, indent=2)

    # Round 2: 逐镜头 Prompt
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

    all_chars = character_summary or bible.get('characters', {})
    prompts = _inject_character_cards(prompts, all_chars)
    prompts = _inject_master_references(prompts, shots, character_master_refs)
    _validate_prompts(prompts, shots, all_chars)
    return prompts


# ── Prompt 后处理 ──

def _inject_character_cards(prompts, character_summary):
    for prompt in prompts:
        for name, desc in character_summary.items():
            placeholder = f"{{CHAR:{name}}}"
            replacement = f"Character Model [{name}]: {desc}"
            prompt['image_prompt'] = prompt['image_prompt'].replace(placeholder, replacement)
            prompt['video_prompt'] = prompt.get('video_prompt', '').replace(placeholder, replacement)
    return prompts


def _inject_master_references(prompts, shots, character_master_refs):
    shot_map = {s['id']: s for s in shots}
    for prompt in prompts:
        sid = prompt.get('shot_id', '')
        shot = shot_map.get(sid)
        if not shot:
            continue
        for char in shot.get('characters', []):
            name = char.get('name', '')
            if not name:
                continue
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
    import logging
    log = logging.getLogger('llm_service')
    shot_map = {s['id']: s for s in shots}
    errors = []

    for prompt in prompts:
        sid = prompt.get('shot_id', 'UNKNOWN')
        img = prompt.get('image_prompt', '')
        vid = prompt.get('video_prompt', '')

        residual = re.findall(r'\{CHAR:[^}]+\}', img + vid)
        if residual:
            for rp in residual:
                prompt['image_prompt'] = prompt['image_prompt'].replace(rp, '')
                prompt['video_prompt'] = prompt.get('video_prompt', '').replace(rp, '')
            log.warning(f"  {sid}: 清理未匹配占位符: {residual}")

        shot = shot_map.get(sid)
        if shot and shot.get('characters') and character_summary:
            for char in shot.get('characters', []):
                cn = char.get('name', '')
                if cn and cn in character_summary and f"Character Model [{cn}]" not in img:
                    prompt['image_prompt'] += f"\nCharacter Model [{cn}]: {character_summary[cn]}"
                    log.warning(f"  {sid}: 自动补全角色 [{cn}]")

        if len(img) < 50:
            errors.append(f"{sid}: image_prompt 过短({len(img)}字)")

        if vid and len(vid) > 80:
            log.warning(f"  {sid}: video_prompt 过长({len(vid)}字，建议20-40)")

    if errors:
        raise ValueError(f"Prompt 验证失败 ({len(errors)} 项):\n" + '\n'.join(errors))


def _enforce_camera_variety(shots):
    """强制非静态运镜占 >40%，相邻镜运镜不重复。"""
    import logging, random
    log = logging.getLogger('llm_service')
    if not shots or len(shots) < 3:
        return shots

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
        for i in range(1, len(shots)):
            if movements[i] == movements[i-1] and movements[i] != 'static':
                alt = [m for m in all_movements if m not in (movements[i-1],
                       movements[i+1] if i+1 < len(shots) else '')]
                new_m = random.choice(alt) if alt else 'static'
                shots[i]['camera_movement'] = new_m
                movements[i] = new_m
                log.info(f"  运镜修复: {shots[i]['id']} {movements[i-1]}→{new_m} (去重)")
        return shots

    log.info(f"  运镜多样性: static={static_count}/{len(shots)} ({static_ratio:.0%}), 强制多样化")
    replaced = 0
    target_replace = max(1, int(static_count * 0.5))

    for i, s in enumerate(shots):
        if replaced >= target_replace:
            break
        if s.get('camera_movement', 'static') != 'static':
            continue
        mood = s.get('mood', '平和')
        preferred = mood_movements.get(mood, ['pan', 'orbit'])
        adj = set()
        if i > 0:
            adj.add(shots[i-1].get('camera_movement', ''))
        if i < len(shots)-1:
            adj.add(shots[i+1].get('camera_movement', ''))
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
