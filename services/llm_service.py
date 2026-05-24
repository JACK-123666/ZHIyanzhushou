import json
import re
from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, STYLE_TEMPLATES, DURATION_MODES

SHOT_PARSE_SYSTEM = """你是顶级影视剧本解析AI。深度理解分镜脚本文档，提取所有视觉元素构建完整的场景描述。

输出JSON格式:
{
  "title": "剧本标题",
  "genre": "题材类型",
  "global_tone": "整体基调(紧张/温馨/严肃/轻松等)",
  "shots": [
    {
      "id": "SC01",
      "raw_visual": "原文镜头描述（完整保留）",
      "narration": "旁白文本（无则空字符串）",
      "sfx": "音效描述",
      "original_duration": 数字秒数或null,
      "characters": [
        {
          "name": "角色名",
          "role": "身份(保安/顾客/经理等)",
          "detailed_appearance": "从文档中提取或根据上下文推断的完整外貌：年龄、服装(颜色+款式+材质)、体型、身高、发型发色、面部特征、标志性配饰。如果文档没有明确描述，根据角色身份合理推断——保安穿制服，经理穿西装等。"
        }
      ],
      "location": "场景位置(统一命名，同场景使用相同名称)",
      "location_detail": "该镜头的具体位置描述(如'大厅左侧'、'门口近景')",
      "action_summary": "主要动作(谁做什么，用什么方式)",
      "camera_hint": "镜头类型提示(广角/中景/特写/跟拍/推近等)",
      "on_screen_text": "屏幕叠加文字",
      "mood": "该镜头情绪(紧张/平静/急促/温馨)"
    }
  ],
  "scene_map": {
    "场景名1": ["SC01", "SC03", "SC05"],
    "场景名2": ["SC02", "SC04"]
  },
  "character_summary": {
    "角色名": "全局外貌总结(综合所有镜头信息，给出该角色在整个视频中的固定外貌描述，50-100字)"
  }
}

重要规则:
1. scene_map 必须正确分组——同一物理场景的所有镜头归到同一组
2. character_summary 中每个角色的外貌必须覆盖所有镜头中该角色的出现，确保一致性
3. 如果文档是分镜表格格式(有表头行)，自动识别列对应关系
4. 如果文档是自由文本格式，按段落/标记符(##、--、等)分割镜头
5. 所有描述提取必须尽可能详细，从文档原文中逐字提取视觉细节

只输出JSON，不要任何其他文字。"""

SHOT_PARSE_USER = """深度解析以下分镜脚本文档，提取所有视觉元素和角色细节:

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
    """使用DeepSeek深度解析文档，返回完整的剧本结构"""
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
    result = _extract_json(response.choices[0].message.content)

    # 兼容旧格式：如果是数组直接包一层
    if isinstance(result, list):
        result = {'title': '未命名', 'shots': result, 'scene_map': {}, 'character_summary': {}}

    return result


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
