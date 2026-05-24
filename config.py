import os
from dotenv import load_dotenv

load_dotenv()

# --- 密钥（仅从环境变量读取，无硬编码） ---
SEEDANCE_API_KEY = os.environ.get('SEEDANCE_API_KEY', '')
SEEDANCE_ENDPOINT = os.environ.get('SEEDANCE_ENDPOINT', '')

# --- 上传限制 ---
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB
MAX_CONTENT_LENGTH = 100000  # 文档解析字符上限

# --- 允许的文件扩展名 ---
ALLOWED_DOC_EXTENSIONS = {'.pdf', '.pptx', '.docx', '.txt'}

# --- AI 模型配置 ---
AI_VIDEO_MODELS = {
    'seedance': {
        'name': 'Seedance 1.5 Pro (字节跳动)',
        'api_url': 'https://ark.cn-beijing.volces.com/api/v3/chat/completions',
        'video_api_url': 'https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks',
        'api_key': SEEDANCE_API_KEY,
        'model': SEEDANCE_ENDPOINT,
        'video_model': 'seedance-1.5-pro',
        'description': '字节跳动 Seedance 1.5 Pro AI视频生成引擎'
    },
    'runway': {
        'name': 'RunwayML Gen-2',
        'api_url': 'https://api.runwayml.com/v1/generate',
        'api_key': os.environ.get('RUNWAY_API_KEY', ''),
        'model': 'gen2',
        'description': 'RunwayML 视频生成模型'
    },
    'pika': {
        'name': 'Pika Labs',
        'api_url': 'https://api.pika.art/v1/generate',
        'api_key': os.environ.get('PIKA_API_KEY', ''),
        'model': 'pika-1.0',
        'description': 'Pika Labs 视频生成模型'
    }
}

# --- 视频风格映射 ---
STYLE_DESCRIPTIONS = {
    'business': '专业商务风格，简洁大方，适合企业文档介绍，使用蓝色和灰色调，清晰的排版',
    'creative': '创意艺术风格，充满活力，适合创意文档，使用鲜艳色彩和动态效果',
    'minimalist': '极简风格，干净整洁，突出核心信息，使用白色背景和黑色文字，留白充足',
    'tech': '科技风格，现代感强，适合技术文档，使用深色背景和霓虹色点缀'
}

# --- 时长映射 ---
DURATION_MAPS = {
    'short': {'seconds': 30, 'scenes': 2, 'desc': '30秒短视频', 'words_per_scene': 15},
    'medium': {'seconds': 60, 'scenes': 3, 'desc': '60秒中等视频', 'words_per_scene': 20},
    'long': {'seconds': 100, 'scenes': 4, 'desc': '100秒长视频', 'words_per_scene': 25}
}

# --- Seedance 时长映射 ---
SEEDANCE_DURATION_MAP = {'short': 5, 'medium': 8, 'long': 12}

# --- 旁白描述 ---
NARRATOR_DESCRIPTIONS = {
    'female1': '温柔专业的女声，语速适中，适合商务文档介绍',
    'female2': '活泼亲切的女声，语速稍快，适合创意内容',
    'male1': '沉稳权威的男声，语速稳健，适合技术文档',
    'male2': '温和友好的男声，语速适中，适合通用场景'
}

# --- Seedance 风格 prompt ---
SEEDANCE_STYLE_PROMPTS = {
    'business': '专业商务风格，简洁大方，适合企业宣传',
    'creative': '创意艺术风格，充满想象力，视觉冲击力强',
    'minimalist': '极简风格，干净简约，突出核心信息',
    'tech': '科技感风格，现代科技元素，未来感设计'
}


def get_model_config(model_key):
    """获取模型配置，不存在则返回 None"""
    return AI_VIDEO_MODELS.get(model_key)
