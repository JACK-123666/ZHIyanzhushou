"""
LLM 服务 — DeepSeek V4 Pro 驱动分镜设计 + Prompt 生成
核心: 角色身份证(占位符替换) + 角色主镜锚定 + 情绪弧线 + 叙事链
"""

import json, re
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
# System Prompt 1b: 全自动分镜设计 — 完全创作自由，仅总时长约束
# ================================================================

SHOT_DESIGN_AUTO_SYSTEM = """你是资深电影导演。用户给你故事文档和总时长目标，你拥有完全创作自由。

=== 核心原则 ===
你自主决定一切：镜头数量、每镜时长、视觉风格、运镜方式、灯光、节奏、情绪弧线。
唯一约束：{duration_note}
根据故事内容选择最合适的视觉风格——动作片用动态镜头、文艺片用舒缓节奏、悬疑片用紧张运镜。

=== 电影语法（必须遵守） ===
[180度轴线规则] 对话场景所有机位在轴线同侧，A左B右不能跳轴
[30度定律] 同主体相邻镜头机位改变≥30度，通过景别变化避免跳切
[镜头覆盖] 每场景: Master建立 → Coverage中景 → Insert特写

=== 镜头运动（每镜一种） ===
push-in / pull-out / pan / tracking / orbit / crane / handheld / static

=== 视觉风格自选 ===
读文档后你自主选择最合适的风格，英文描述2-3句：
- 3D卡通: Pixar-style 3D animation, vibrant colors, soft lighting
- 2D扁平: flat vector illustration, minimalist, clean lines
- 写实简化: semi-realistic, stylized realism, cinematic lighting
- 素描线稿: pencil sketch, black and white, hand-drawn
你也可以混合创造自己的风格描述。

=== 灯光描述 ===
写成: "主光从画左45度打来，色温3200K暖黄，光比4:1"

=== 旁白时长约束 ===
中文TTS语速约4字/秒。旁白字数 ≤ 镜头时长×4。

=== raw_visual 格式 (中文50-100字) ===
"[光影氛围]. [角色+位置+姿势]. [动作关键瞬间]. [构图: 景别+角度+景深]"

=== 输出JSON ===
{{"title":"标题","genre":"类型","global_tone":"基调","visual_style_directive":"你自主选择的风格（英文2-3句，用于图片生成）",
 "emotion_curve":"情绪弧线",
 "spatial_axis":"空间轴线",
 "shots":[{{"id":"SC01","raw_visual":"50-100字","narration":"旁白",
   "sfx":"音效","original_duration":秒数({duration_note}),
   "characters":[{{"name":"角色名","role":"身份","detailed_appearance":"枚举式外貌"}}],
   "location":"场景名","location_detail":"具体位置",
   "action_summary":"谁做什么+怎么做+力度(15-30字)",
   "camera_hint":"景别","camera_movement":"运镜","lighting":"灯光",
   "on_screen_text":"字幕","mood":"情绪标签","axis_note":"轴线"}}],
 "scene_map":{{"场景名":["SC01"]}},
 "character_summary":{{"角色名":"固定外貌50-80字"}}}}
只输出JSON。"""

SHOT_DESIGN_AUTO_USER = """请阅读以下文档，自主设计完整分镜脚本：

=== 文档内容 ===
{document}

=== 约束 ===
总时长目标: {dur_goal}
风格: 你自主选择最合适的视觉风格
镜头数量: 你自主决定
每镜时长: 你根据叙事节奏自主分配（2-8秒/镜）

请自主决定一切创作参数，输出完整的分镜JSON。"""


# ================================================================
# System Prompt 2: 视觉圣经 — Round 1，建立全片风格锚点
# ================================================================

BIBLE_SYSTEM = """你是影视美术指导。分析所有分镜，输出"视觉圣经"确保全片视觉一致。
若提供了 CHARACTER_SUMMARY（角色身份证），必须逐字复制，不得改写。

输出JSON:
{"global_style":"2-3句: 色温+主色调+光线质量",
 "characters":{"角色名":"若CHARACTER_SUMMARY已提供则逐字复制，否则写50-80词精确外貌"},
 "locations":{"场景名":"30-50词: 空间布局+标志道具+光线色调"},
 "shot_connections":["SC01->SC02 的衔接说明"]}
只输出JSON。"""

BIBLE_USER = """风格前缀: {style_prefix}

=== CHARACTER_SUMMARY（角色身份证，不可修改） ===
{character_summary}

分镜数据:
{shots_json}

生成视觉圣经。角色描述从 CHARACTER_SUMMARY 逐字复制。"""


# ================================================================
# System Prompt 4: Prompt 生成器 — Round 2，每镜头 image+video prompt
# 核心: 占位符{CHAR:name}、6类错误预防、4段强制结构
# ================================================================

PROMPT_GEN_SYSTEM = """你是AI视频Prompt工程师+摄影指导，专精 Seedance 2.0 首帧生视频。

输出JSON数组: [{"shot_id":"SC01","image_prompt":"...","video_prompt":"..."}]

=== 错误预防（每条 video_prompt 必须设防） ===
1. 身份漂移: 面部变形 → "面部特征与参考图完全一致，五官不位移不变形"
2. 肢体变形: 手臂拉长 → "肢体只在自然关节范围内运动，手指保持正常比例"
3. 背景闪烁: 墙壁忽明忽暗 → "背景和固定物体保持绝对静止，光线亮度恒定"
4. 物体闪现: 东西突然出现/消失 → "不增加也不减少任何物体或角色"
5. 运镜抖动: 帧间微颤 → 必须包含"smooth, steady, stabilized"
6. 动作超速: 幅度失控 → 精确约束"幅度不超过画面宽度的X%"

=== Seedance 核心 ===
- first_frame I2V: 每镜头独立关键帧作为起始画面
- video_prompt 中文 80-150字（越短越稳定），每镜一种运动
- 运镜写节奏词不写技术参数（"slow smooth push-in" 不写 "24fps f/2.8"）

=== 规则 ===

规则0 — {CHAR:角色名} 占位符（最高优先级）
  image_prompt 中只写占位符，不写角色外貌。系统自动替换。

规则1 — 角色主镜锚定
  非主镜镜头追加: "CRITICAL: [角色名] must be IDENTICAL to master shot XX."
  同级角色在不同镜头中占位符写法完全一致。

规则2 — LOCATION LOCK: 同场景布局和道具位置一致，场景描述从视觉圣经逐字复制

规则3 — STYLE LOCK: 所有镜头以相同全局风格描述开头

规则4 — EMOTION ARC: 情绪决定光线/色调/角色姿态，过渡平滑不突变

规则5 — CAMERA: image_prompt 含 camera_hint 关键词
  video_prompt 从 camera_movement 取运动，精确写: 类型+方向+速度+幅度

规则6 — 动作量化: 不是"转头"而是"头部从正面缓慢转向左侧约30度"
  写明哪些部分完全不动: "仅右手和前臂运动，身体躯干保持静止"

规则7 — NARRATIVE CHAIN: 从前镜结束状态开始，结束后镜可承接的干净定格

=== image_prompt 格式 (英文 250-400词，给 Seedream) ===
[全局风格: 色温+主色调+光线质量]
[场景: 从视觉圣经逐字复制]
{CHAR:角色名1} {CHAR:角色名2}
[构图: camera_hint + 情绪灯光]
[静态状态: standing/holding/positioned/sitting — 这是视频的起始帧]
[品质: high quality, consistent character design, identical appearance, detailed textures, clean background, cinematic lighting]

=== video_prompt 格式 (中文 80-150字，给 Seedance，4段缺一不可) ===
[动作] 角色名+身体部位+方向+幅度+速度+力度。写明哪些部分完全不动。
[运镜] 镜头类型+方向+速度，幅度不超过X%，smooth steady stabilized 无抖动。
[不变] 背景、道具、光线、角色外观与参考图完全一致。
[禁止] 逐条列出6项。

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

=== 分镜列表（含叙事链、相机指令、时长） ===
{shots_with_context}

为每个镜头生成 image_prompt(英文) 和 video_prompt(中文)。
严格使用 {{{{CHAR}}:角色名}} 占位符。video_prompt 中文 80-150字，4段(动作/运镜/不变/禁止)缺一不可。"""


# ================================================================
# 函数实现
# ================================================================

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
        system = SHOT_DESIGN_AUTO_SYSTEM.format(duration_note=duration_note)
        user = SHOT_DESIGN_AUTO_USER.format(document=document_text, dur_goal=dur_goal,
                                             total_duration=total_sec)
        temp = 0.6
    else:
        duration_mode = config.get('duration_mode', 'uniform')
        system = SHOT_DESIGN_SYSTEM
        user = SHOT_DESIGN_USER.format(document=document_text, duration_mode=duration_mode)
        temp = 0.5

    response = client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        timeout=120, temperature=temp, max_tokens=32000,
        thinking={"type": "enabled"}, reasoning_effort="high"
    )
    result = _extract_json(response.choices[0].message.content)
    if isinstance(result, list):
        result = {'title': '未命名', 'shots': result, 'scene_map': {}, 'character_summary': {}}
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
    bible = _extract_json(client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[
            {"role": "system", "content": BIBLE_SYSTEM},
            {"role": "user", "content": BIBLE_USER.format(
                style_prefix=style_prefix, character_summary=char_summary_text,
                shots_json=shots_basic_json)}
        ],
        timeout=120, temperature=0.4, max_tokens=16000,
        thinking={"type": "enabled"}, reasoning_effort="high"
    ).choices[0].message.content)

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
            'on_screen_text': s.get('on_screen_text', '')
        })
    shots_ctx_json = json.dumps(shots_with_context, ensure_ascii=False, indent=2)

    # === Round 2: 逐镜头 Prompt ===
    global_style = bible.get('global_style', style_prefix)
    character_bible = json.dumps(bible.get('characters', {}), ensure_ascii=False, indent=2)
    location_bible = json.dumps(bible.get('locations', {}), ensure_ascii=False, indent=2)
    shot_connections = '\n'.join(bible.get('shot_connections', []))

    prompts = _extract_json(client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[
            {"role": "system", "content": PROMPT_GEN_SYSTEM},
            {"role": "user", "content": PROMPT_GEN_USER.format(
                global_style=global_style, character_bible=character_bible,
                location_bible=location_bible, shot_connections=shot_connections,
                style_prefix=style_prefix, duration=duration,
                emotion_arc=emotion_arc, shots_with_context=shots_ctx_json,
                resolution=config.get('resolution', '1920x1080'))}
        ],
        timeout=120, temperature=0.4, max_tokens=32000,
        thinking={"type": "enabled"}, reasoning_effort="high"
    ).choices[0].message.content)

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
