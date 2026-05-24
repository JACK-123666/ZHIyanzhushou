import os
from dotenv import load_dotenv

load_dotenv()

# --- 密钥 ---
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_BASE_URL = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')
SEEDREAM_API_KEY = os.environ.get('SEEDREAM_API_KEY', '')
SEEDREAM_ENDPOINT = os.environ.get('SEEDREAM_ENDPOINT', '')
SEEDANCE_API_KEY = os.environ.get('SEEDANCE_API_KEY', '')
SEEDANCE_ENDPOINT = os.environ.get('SEEDANCE_ENDPOINT', '')

# --- 上传限制 ---
MAX_UPLOAD_SIZE = 50 * 1024 * 1024
MAX_CONTENT_LENGTH = 100000
ALLOWED_DOC_EXTENSIONS = {'.docx', '.txt'}

# --- 前端配置选项定义 ---
STYLE_TEMPLATES = {
    '3d_cartoon': {
        'label': '3D卡通',
        'prompt': '3D animation, cartoon shading, vibrant colors, non-photorealistic rendering, Pixar-style'
    },
    '2d_flat': {
        'label': '2D扁平',
        'prompt': '2D flat vector style, clean outlines, uniform lighting, minimalist flat design'
    },
    'semi_realistic': {
        'label': '写实简化',
        'prompt': 'semi-realistic, soft lighting, minimal details, no photo-realism, stylized realism'
    },
    'pencil_sketch': {
        'label': '素描线稿',
        'prompt': 'pencil sketch, black and white, rough lines, artistic hand-drawn style'
    }
}

DURATION_MODES = {
    'strict': {'label': '严格按脚本', 'default_seconds': 5},
    'uniform': {'label': '统一5秒', 'default_seconds': 5},
    'auto_split': {'label': '自动拆分(>8s)', 'default_seconds': 8, 'max_seconds': 8}
}

CONSISTENCY_STRATEGIES = {
    'generic': {'label': '通用无面孔模型', 'value': 'generic'},
    'reference': {'label': '参考图驱动', 'value': 'reference'},
    'random': {'label': '随机生成', 'value': 'random'}
}

RESOLUTIONS = {
    '1920x1080': {'label': '1920x1080 (16:9)', 'width': 1920, 'height': 1080},
    '1024x1024': {'label': '1024x1024 (1:1)', 'width': 1024, 'height': 1024},
    '1080x1920': {'label': '1080x1920 (9:16)', 'width': 1080, 'height': 1920}
}

# --- 模型配置 ---
AI_MODELS = {
    'deepseek': {
        'name': 'DeepSeek V4',
        'api_url': f"{DEEPSEEK_BASE_URL}/chat/completions",
        'api_key': DEEPSEEK_API_KEY,
        'model': 'deepseek-chat'
    },
    'seedream': {
        'name': 'Seedream (豆包文生图)',
        'api_url': 'https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks',
        'api_key': SEEDREAM_API_KEY,
        'model': SEEDREAM_ENDPOINT or 'doubao-seedream-5-0-260128'
    },
    'seedance': {
        'name': 'Seedance 2.0 Flash (豆包图生视频)',
        'api_url': 'https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks',
        'api_key': SEEDANCE_API_KEY,
        'model': SEEDANCE_ENDPOINT or 'seedance-2.0-flash'
    }
}

# --- 状态定义 ---
PIPELINE_STATES = ['UPLOADED', 'PARSED', 'PROMPTS_READY', 'IMAGES_GENERATED', 'VIDEOS_GENERATED', 'COMPOSED']

# --- 重试配置 ---
MAX_RETRIES = 3
RETRY_BASE_DELAY = 5
RETRY_MAX_DELAY = 30


def get_model_config(model_key):
    return AI_MODELS.get(model_key)
