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
- characters: 角色列表，每个角色需包含 name、appearance（外貌描述：年龄/服装/体型/发型等）
- location: 场景位置
- action_summary: 主要动作摘要
- on_screen_text: 屏幕图文（无则填"无"）

只输出JSON，不要任何其他文字。"""

SHOT_PARSE_USER = """解析以下分镜脚本文档，输出JSON分镜数组:

{document}"""

PROMPT_GEN_SYSTEM = """你是顶级AI视频Prompt工程师。根据分镜描述和风格配置，为每个镜头生成高质量prompt。

输出JSON数组，每个元素包含:
- shot_id: 镜头编号
- image_prompt: 文生图prompt（英文，150-300词，极其详细）
- video_prompt: 图生视频prompt（英文，80-150词）

image_prompt必须包含:
1. 风格前缀
2. 场景详细描述：环境、光线、色彩、氛围、道具
3. 每个角色的详细外貌：年龄/服装颜色款式/体型/发型/配饰（标注"Character Model: [角色名]"以便跨镜头保持一致）
4. 构图：镜头类型（广角/中景/特写）、角度、景深
5. 静态状态描述（去除时间性动词，改为"standing""holding""positioned"等）
6. 画质关键词：high quality, detailed textures, consistent character design

video_prompt必须包含:
1. "Animate the scene from the reference image."
2. 每个角色的具体动作（谁做什么，怎么移动）
3. 镜头运动（pan/tilt/zoom/dolly/tracking）
4. 时长和节奏
5. "Maintain the exact same character appearance, art style and scene layout as the reference image."

只输出JSON，不要任何其他文字。"""

PROMPT_GEN_USER = """风格前缀: {style_prefix}
分辨率: {resolution}
镜头时长: {duration}s
分镜数据:
{shots_json}

为每个镜头生成详细的高质量 image_prompt 和 video_prompt。确保角色描述详细且跨镜头一致。"""


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
    """为所有镜头生成 image_prompt 和 video_prompt"""
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
        'on_screen_text': s.get('on_screen_text', '')
    } for s in shots], ensure_ascii=False, indent=2)

    client = _get_client()
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": PROMPT_GEN_SYSTEM},
            {"role": "user", "content": PROMPT_GEN_USER.format(
                style_prefix=style_prefix,
                resolution=resolution,
                duration=duration,
                shots_json=shots_json
            )}
        ],
        temperature=0.5,
        max_tokens=8000
    )
    return _extract_json(response.choices[0].message.content)


def _get_client():
    return OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)


def _extract_json(text):
    text = text.strip()
    match = re.search(r'\[[\s\S]*\]', text)
    if match:
        return json.loads(match.group())
    return json.loads(text)
