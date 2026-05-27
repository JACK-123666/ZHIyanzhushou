"""
智演助手 1.5 — 配置中心
密钥 | 模型端点 | 风格模板 | 镜头语言映射 | 重试策略
"""

import os

# --- API 密钥 ---

ARK_API_KEY = os.environ.get('ARK_API_KEY', '')          # 豆包 ARK（Seedream+Seedance 共用）
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')  # DeepSeek（分镜+Prompt）
DEEPSEEK_BASE_URL = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')

# --- 上传限制 ---

MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100MB
MAX_CONTENT_LENGTH = 200000          # 文档截断：20万字
ALLOWED_DOC_EXTENSIONS = {'.docx', '.txt'}

# --- 视觉风格（前端下拉 → 英文 prompt 前缀） ---

STYLE_TEMPLATES = {
    '3d_cartoon':   {'label': '3D卡通',  'prompt': '3D animation, Pixar-style'},
    '2d_flat':      {'label': '2D扁平',  'prompt': '2D flat vector style, minimalist'},
    'semi_realistic': {'label': '写实简化', 'prompt': 'semi-realistic, stylized realism'},
    'pencil_sketch':  {'label': '素描线稿', 'prompt': 'pencil sketch, black and white'},
}

# --- 时长模式 ---

DURATION_MODES = {
    'ai_design':  {'label': 'AI智能分配（推荐）', 'default_seconds': 5},
    'uniform':    {'label': '统一5秒',           'default_seconds': 5},
    'auto_split': {'label': '自动拆分(>8s)',     'default_seconds': 8, 'max_seconds': 8},
}

# --- 图片分辨率（Seedream 出图尺寸） ---

RESOLUTIONS = {
    '1920x1080': {'label': '1920x1080 (16:9)', 'width': 1920, 'height': 1080, 'ratio': '16:9', 'size': '2K'},
    '1024x1024': {'label': '1024x1024 (1:1)',  'width': 1024, 'height': 1024, 'ratio': '1:1',  'size': '1K'},
    '1080x1920': {'label': '1080x1920 (9:16)', 'width': 1080, 'height': 1920, 'ratio': '9:16', 'size': '2K'},
}

# --- AI 模型配置 ---

AI_MODELS = {
    'deepseek': {
        'name': 'DeepSeek V4 Pro [1M]',
        'api_url': f"{DEEPSEEK_BASE_URL}/chat/completions",
        'api_key': DEEPSEEK_API_KEY,
        'model': 'deepseek-v4-pro',
    },
    'seedream': {
        'name': 'Seedream 5.0 Lite（文生图）',
        'api_url': 'https://ark.cn-beijing.volces.com/api/v3/images/generations',
        'api_key': ARK_API_KEY,
        'model': os.environ.get('SEEDREAM_ENDPOINT', 'your_seedream_endpoint'),
    },
    'seedance': {
        'name': 'Seedance 2.0 Fast（图生视频）',
        'api_url': 'https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks',
        'api_key': ARK_API_KEY,
        'model': os.environ.get('SEEDANCE_ENDPOINT', 'your_seedance_endpoint'),
    },
}

# --- 镜头语言：中文 → 英文构图指令（注入 image_prompt） ---

CAMERA_INSTRUCTIONS = {
    # 景别
    '建立远景': 'wide establishing shot, full environment, deep depth of field',
    '中景':   'medium shot, waist-up framing, balanced composition',
    '过肩OTS': 'over-the-shoulder shot, foreground character as soft frame',
    '单人特写': 'tight close-up, face filling 60% of frame, shallow DOF, bokeh',
    '插入特写': 'extreme close-up insert, single detail, razor-thin DOF',
    '跟拍':   'tracking shot, camera follows subject, background parallax',
    'POV':    'point-of-view shot, camera as character eyes, first-person',
    '俯拍':   'high-angle shot looking down, characters appear vulnerable',
    '仰拍':   'low-angle shot looking up, characters appear powerful',
    '手持':   'handheld camera, organic shake, documentary realism',
    '推近':   'dolly-in from medium to close-up, increasing dramatic intensity',
    '拉远':   'dolly-out from subject, revealing environment, isolation feel',
    # Seedance 8 种原生运动
    'push-in':  'slow dolly push-in, smooth steady, no abrupt stops',
    'pull-out': 'slow dolly pull-out, smooth steady retreat',
    'pan':      'horizontal pan, smooth scan, no vertical drift',
    'tracking': 'lateral tracking alongside subject, background parallax',
    'orbit':    'orbital arc around subject, circular movement',
    'crane':    'vertical crane rise/lower, smooth elevation change',
    'static':   'fixed camera, locked tripod, intentional stillness',
    'handheld': 'subtle organic instability, documentary immediacy',
}

# --- 流水线状态 & 重试 ---

MAX_RETRIES = 3
RETRY_BASE_DELAY = 5
RETRY_MAX_DELAY = 30


# --- 全自动模式：固定配置（用户只选时长，其余系统接管） ---

AUTO_MODE_DEFAULTS = {
    'resolution': '1920x1080',
    'video_quality': '480p',
    'auto_subtitle': 'yes',
    'auto_sfx': 'no',
    'original_audio_level': 20,
}

# 总时长选项：0 = AI 自主决定
AUTO_DURATION_OPTIONS = {
    'auto':  {'label': 'AI 自主决定', 'seconds': 0},
    'short': {'label': '1 分钟',     'seconds': 60},
    'medium':{'label': '3 分钟',     'seconds': 180},
    'long':  {'label': '5 分钟',     'seconds': 300},
}

# --- 多语言 & TTS ---

LANGUAGES = {
    'zh': {'label': '中文', 'tts_voice': 'zh-CN-XiaoxiaoNeural',
           'font': '/Windows/Fonts/simhei.ttf', 'prompt': '中文'},
    'en': {'label': 'English', 'tts_voice': 'en-US-JennyNeural',
           'font': '/Windows/Fonts/segoeui.ttf', 'prompt': 'English'},
    'ja': {'label': '日本語', 'tts_voice': 'ja-JP-NanamiNeural',
           'font': 'resource/fonts/msgothic.ttc', 'prompt': '日本語'},
    'ko': {'label': '한국어', 'tts_voice': 'ko-KR-SunHiNeural',
           'font': '/Windows/Fonts/malgun.ttf', 'prompt': '한국어'},
}

DEFAULT_LANGUAGE = 'zh'


def get_model_config(key):
    return AI_MODELS.get(key)
