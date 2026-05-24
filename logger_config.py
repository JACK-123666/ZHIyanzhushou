import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

# 创建logs目录
LOGS_DIR = os.path.join(os.path.dirname(__file__), 'logs')
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# 日志文件路径
LOG_FILE = os.path.join(LOGS_DIR, f'app_{datetime.now().strftime("%Y%m%d")}.log')

# 配置日志格式
LOG_FORMAT = '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

def setup_logger(name='app'):
    """配置并返回一个logger实例"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # 避免重复添加handler
    if logger.handlers:
        return logger

    # 文件处理器 - 所有日志
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

    # 文件处理器 - 仅错误日志
    error_file_handler = RotatingFileHandler(
        os.path.join(LOGS_DIR, f'error_{datetime.now().strftime("%Y%m%d")}.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(error_file_handler)
    logger.addHandler(console_handler)

    return logger

# 创建默认logger
logger = setup_logger()
