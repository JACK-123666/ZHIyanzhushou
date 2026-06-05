# clip_trends/config.py
import os
from dotenv import load_dotenv

load_dotenv()

CRAWL_CONFIG = {
    'max_per_site': 15,
    'request_interval': 1.0,
    'request_timeout': 30,
    'retry_times': 3,
    'retry_backoff': [5, 10, 20],
}

VIDEO_ANALYSIS = {
    'max_file_size_mb': 50,
    'download_timeout': 120,
    'frame_interval': 3,
    'download_dir': 'clip_trends/temp_videos/',
    'qwen_model': 'qwen-vl-max',
}

MYSQL_CONFIG = {
    'host': os.environ.get('MYSQL_HOST', 'localhost'),
    'port': int(os.environ.get('MYSQL_PORT') or 3306),
    'user': os.environ.get('MYSQL_USER', 'clip_trends'),
    'password': os.environ.get('MYSQL_PASSWORD', ''),
    'database': os.environ.get('MYSQL_DATABASE', 'clip_trends'),
    'charset': 'utf8mb4',
}

DASHSCOPE_API_KEY = os.environ.get('DASHSCOPE_API_KEY', '')
PEXELS_API_KEY = os.environ.get('PEXELS_API_KEY', '')
PIXABAY_API_KEY = os.environ.get('PIXABAY_API_KEY', '')

# NOTE: 与根目录 config.py 重复定义，后续考虑抽取共享常量模块
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_BASE_URL = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
