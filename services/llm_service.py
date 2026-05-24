import json
import re
from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, STYLE_TEMPLATES, DURATION_MODES

SHOT_PARSE_SYSTEM = """你是一个专业的分镜脚本解析器。解析用户提供的分镜脚本表格，输出JSON数组。
每个分镜对象必须包含这些字段：
- id: 镜头编号 (如 "SC01")
- raw_visual: 镜头描述与AI视觉提示原文
- narration: 旁白文本
- sfx: 音效描述（无则填"无"）
- original_duration: 标注时长秒数（无则填null）
- characters: 角色列表，每个角色需包含 name 和 detailed_appearance（详细外貌：年龄/服装颜色款式/体型/发型/面部特征/身高/配饰）
- location: 场景位置
- action_summary: 主要动作摘要
- on_screen_text: 屏幕图文（无则填"无"）

只输出JSON，不要任何其他文字。"""

SHOT_PARSE_USER = """解析以下分镜脚本文档，输出JSON分镜数组:

{document}"""

# === 两轮 Prompt 生成 ===

BIBLE_SYSTEM = """你是顶级影视美术指导。分析所有分镜，输出"视觉圣经"以确保整个视频的角色、场景、风格完全一致。

输出JSON格式:
{
  "global_style": "2-3句话描述全局视觉风格、色调、光线、氛围",
  "characters": {
    "角色名": "固定外貌描述(50-80词)：精确的年龄、服装(颜色/款式/材质每个细节)、体型身高、发型发色、面部特征、标志性配饰。这段文字会被复制到每个镜头的prompt中。"
  },
  "locations": {
    "场景名": "场景描述(30-50词)：空间布局、标志性道具、光线条件、色调"
  },
  "shot_connections": [
    "SC01->SC02 的衔接：场景如何过渡，角色位置关系，视觉连续性说明"
  ]
}

角色描述必须极其精确到可以当模板复制——同一角色在20个镜头里必须穿一模一样、长一模一样。"""

BIBLE_USER = """风格前缀: {style_prefix}
分镜数据:
{shots_json}

生成视觉圣经。角色描述要极其精确，能跨镜头直接复制使用。"""

PROMPT_GEN_SYSTEM = """你是顶级AI视频Prompt工程师。使用提供的"视觉圣经"确保20个镜头完全视觉连贯。

输出JSON数组，每个元素: {"shot_id": "SC01", "image_prompt": "...", "video_prompt": "..."}

=== 核心规则 ===

1. CHARACTER LOCK: 每个镜头的image_prompt必须原样复制视觉圣经中该角色的描述文字。不同镜头中同一角色的外貌描述必须逐字相同。

2. LOCATION LOCK: 同一场景在不同镜头中，布局和道具位置必须一致。

3. STYLE LOCK: 所有镜头使用相同的全局风格描述。

4. SHOT CONTINUITY: 相邻镜头之间要有视觉连续性——前一个镜头的结尾状态是下一个镜头的起始状态。

=== image_prompt 格式 (250-400词) ===
[全局风格描述]
[场景描述 - 从视觉圣经复制]
[角色描述 - 从视觉圣经逐字复制Character Model: [角色名] = 完整外貌]
[构图: 镜头类型/角度/景深]
[静态状态描述 - 用standing/holding/positioned等]
[画质: high quality, consistent character design, identical appearance to all other shots, detailed textures]

=== video_prompt 格式 (100-150词) ===
"Animate the scene from the reference image. [角色名] [具体动作，从哪个状态到哪个状态]. Camera: [镜头运动类型]. This shot transitions from [前一镜结束状态] to [下一镜起始状态]. Duration: [时长]s. Maintain the exact same character appearance, clothing colors, art style, and scene layout as the reference image and all other shots."

只输出JSON，不要任何其他文字。"""

PROMPT_GEN_USER = """=== 视觉圣经 ===
全局风格: {global_style}

角色圣经:
{character_bible}

场景圣经:
{location_bible}

镜头衔接:
{shot_connections}

=== 参数 ===
风格前缀: {style_prefix}
分辨率: {resolution}
镜头时长: {duration}s

=== 分镜列表 ===
{shots_json}

为每个镜头生成 image_prompt 和 video_prompt。严格遵守CHARACTER LOCK规则——同一角色的外貌描述必须逐字复制视觉圣经。"""


def parse_shots(document_text):
    """使用DeepSeek解析文档，返回分镜数组"""
    client = _get_client()
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": SHOT_PARSE_SYSTEM},
            {"role": "user", "content": SHOT_PARSE_USER.format(document=document_text)}
        ],
        temperature=0.3,
        max_tokens=8000
    )
    return _extract_json(response.choices[0].message.content)


def generate_prompts(shots, config):
    """两轮生成：先建视觉圣经，再为每个镜头生成一致prompt"""
    style_key = config.get('style_template', '3d_cartoon')
    style_info = STYLE_TEMPLATES.get(style_key, STYLE_TEMPLATES['3d_cartoon'])
    style_prefix = style_info['prompt']

    resolution = config.get('resolution', '1920x1080')

    duration_mode = config.get('duration_mode', 'uniform')
    duration_info = DURATION_MODES.get(duration_mode, DURATION_MODES['uniform'])
    duration = duration_info['default_seconds']

    shots_json = json.dumps([{
        'id': s['id'],
        'raw_visual': s.get('raw_visual', ''),
        'narration': s.get('narration', ''),
        'action_summary': s.get('action_summary', ''),
        'characters': s.get('characters', []),
        'location': s.get('location', ''),
        'on_screen_text': s.get('on_screen_text', ''),
        'original_duration': s.get('original_duration')
    } for s in shots], ensure_ascii=False, indent=2)

    client = _get_client()

    # --- Round 1: 生成视觉圣经 ---
    bible_response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": BIBLE_SYSTEM},
            {"role": "user", "content": BIBLE_USER.format(
                style_prefix=style_prefix,
                shots_json=shots_json
            )}
        ],
        temperature=0.4,
        max_tokens=8000
    )
    bible = _extract_json(bible_response.choices[0].message.content)

    # --- Round 2: 用圣经生成每镜头 prompt ---
    global_style = bible.get('global_style', style_prefix)
    character_bible = json.dumps(bible.get('characters', {}), ensure_ascii=False, indent=2)
    location_bible = json.dumps(bible.get('locations', {}), ensure_ascii=False, indent=2)
    shot_connections = '\n'.join(bible.get('shot_connections', []))

    prompt_response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": PROMPT_GEN_SYSTEM},
            {"role": "user", "content": PROMPT_GEN_USER.format(
                global_style=global_style,
                character_bible=character_bible,
                location_bible=location_bible,
                shot_connections=shot_connections,
                style_prefix=style_prefix,
                resolution=resolution,
                duration=duration,
                shots_json=shots_json
            )}
        ],
        temperature=0.4,
        max_tokens=16000
    )
    return _extract_json(prompt_response.choices[0].message.content)


def _get_client():
    return OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)


def _extract_json(text):
    text = text.strip()
    match = re.search(r'\{[\s\S]*\}|\[[\s\S]*\]', text)
    if match:
        return json.loads(match.group())
    return json.loads(text)
