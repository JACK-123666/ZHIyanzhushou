"""Zhiyan 配置中心"""

import os

# --- API 密钥 ---

ARK_API_KEY = os.environ.get('ARK_API_KEY', '')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
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
    '1920x1080': {'label': '1920x1080 (16:9)', 'width': 2560, 'height': 1440, 'ratio': '16:9', 'size': '2560x1440'},
    '1024x1024': {'label': '1024x1024 (1:1)',  'width': 2048, 'height': 2048, 'ratio': '1:1',  'size': '2048x2048'},
    '1080x1920': {'label': '1080x1920 (9:16)', 'width': 1440, 'height': 2560, 'ratio': '9:16', 'size': '1440x2560'},
}

# --- AI 模型配置 ---

AI_MODELS = {
    'deepseek': {
        'name': 'DeepSeek V4 Pro',
        'api_url': f"{DEEPSEEK_BASE_URL}/chat/completions",
        'api_key': DEEPSEEK_API_KEY,
        'model': 'deepseek-v4-pro',
    },
    'seedream': {
        'name': 'Seedream 5.0',
        'api_url': 'https://ark.cn-beijing.volces.com/api/v3/images/generations',
        'api_key': ARK_API_KEY,
        'model': os.environ.get('SEEDREAM_ENDPOINT', ''),
    },
    'seedance': {
        'name': 'Seedance 2.0',
        'api_url': 'https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks',
        'api_key': ARK_API_KEY,
        'model': os.environ.get('SEEDANCE_ENDPOINT', 'doubao-seedance-2-0-fast-260128'),
    },
}

# 成本估算（USD，参考 2025 年定价）
COST_PER_IMAGE = float(os.environ.get('COST_PER_IMAGE', '0.02'))       # Seedream ~$0.02/image
COST_PER_VIDEO_SEC = float(os.environ.get('COST_PER_VIDEO_SEC', '0.12')) # Seedance Fast 480p ~$0.12/sec
COST_PER_LLM_CALL = float(os.environ.get('COST_PER_LLM_CALL', '0.005'))  # DeepSeek ~$0.005/call

# 成本控制：最大镜数、单镜最长秒数
MAX_SHOTS_FOR_COST = 10
MAX_SHOT_DURATION = 8

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
    'bgm_enabled': 'yes',
    'bgm_volume': 12,
}

# 总时长选项：0 = AI 自主决定
AUTO_DURATION_OPTIONS = {
    'auto':  {'label': 'AI 自主决定', 'seconds': 0},
    'short': {'label': '1 分钟',     'seconds': 60},
    'medium':{'label': '3 分钟',     'seconds': 180},
    'long':  {'label': '5 分钟',     'seconds': 300},
}

# --- 多语言 & TTS ---

def _default_fonts():
    """根据操作系统返回默认字体路径"""
    import platform
    system = platform.system()
    font_env = os.environ.get('FONT_DIR', '')
    if font_env:
        return {
            'zh': os.path.join(font_env, 'simhei.ttf'),
            'en': os.path.join(font_env, 'segoeui.ttf'),
            'ja': os.path.join(font_env, 'msgothic.ttc'),
            'ko': os.path.join(font_env, 'malgun.ttf'),
        }
    if system == 'Windows':
        return {
            'zh': '/Windows/Fonts/simhei.ttf',
            'en': '/Windows/Fonts/segoeui.ttf',
            'ja': 'resource/fonts/msgothic.ttc',
            'ko': '/Windows/Fonts/malgun.ttf',
        }
    # Linux / macOS
    return {
        'zh': '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
        'en': '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        'ja': '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        'ko': '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
    }

_fonts = _default_fonts()

LANGUAGES = {
    'zh': {'label': '中文', 'tts_voice': 'zh-CN-XiaoxiaoNeural',
           'font': _fonts['zh'], 'prompt': '中文'},
    'en': {'label': 'English', 'tts_voice': 'en-US-JennyNeural',
           'font': _fonts['en'], 'prompt': 'English'},
    'ja': {'label': '日本語', 'tts_voice': 'ja-JP-NanamiNeural',
           'font': _fonts['ja'], 'prompt': '日本語'},
    'ko': {'label': '한국어', 'tts_voice': 'ko-KR-SunHiNeural',
           'font': _fonts['ko'], 'prompt': '한국어'},
}

DEFAULT_LANGUAGE = 'zh'


def get_model_config(key):
    return AI_MODELS.get(key)
