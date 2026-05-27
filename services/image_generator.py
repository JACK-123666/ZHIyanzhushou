"""Seedream 5.0 Lite 文生图 — 同步API，指数退避重试"""

import os, time, requests
from config import RESOLUTIONS, MAX_RETRIES, RETRY_BASE_DELAY, RETRY_MAX_DELAY


def generate_image(model_config, image_prompt, resolution_key, output_path):
    """调用 Seedream 生成图片 → 下载到本地。失败自动重试3次。"""
    api_key = model_config.get('api_key')
    api_url = model_config.get('api_url')
    model = model_config.get('model')

    if not api_key or not model:
        raise ValueError("Seedream 配置不完整")
    if not image_prompt or len(image_prompt.strip()) < 20:
        raise ValueError(f"image_prompt 过短({len(image_prompt)}字)")

    # 截断保护: Seedream 限制 800 字符
    MAX_PROMPT = 800
    if len(image_prompt) > MAX_PROMPT:
        cut = image_prompt.rfind('.', 0, MAX_PROMPT)
        image_prompt = image_prompt[:max(cut, MAX_PROMPT//2) + 1]

    res = RESOLUTIONS.get(resolution_key, RESOLUTIONS['1920x1080'])

    payload = {'model': model, 'prompt': image_prompt,
               'sequential_image_generation': 'disabled',
               'response_format': 'url', 'size': res['size'],
               'stream': False, 'watermark': False}

    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}
    url = _call_api(api_url, headers, payload)
    if not url: raise RuntimeError("Seedream 返回空URL")

    _download_file(url, output_path)
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError("下载的图片为空")
    return output_path


def _call_api(api_url, headers, payload):
    """指数退避重试: 429限流→长等, 5xx→短等, timeout→短等"""
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.post(api_url, json=payload, headers=headers, timeout=(10, 120))
            if r.status_code == 429:
                time.sleep(min(RETRY_BASE_DELAY * (2**attempt) * 2, RETRY_MAX_DELAY)); continue
            if 500 <= r.status_code < 600 and attempt < MAX_RETRIES - 1:
                time.sleep(min(RETRY_BASE_DELAY * (2**attempt), RETRY_MAX_DELAY)); continue
            if r.status_code != 200: return None
            result = r.json()
            return result.get('data', [{}])[0].get('url') if 'data' in result else result.get('url')
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            if attempt < MAX_RETRIES - 1:
                time.sleep(min(RETRY_BASE_DELAY * (2**attempt), RETRY_MAX_DELAY))
        except Exception:
            if attempt < MAX_RETRIES - 1:
                time.sleep(min(RETRY_BASE_DELAY * (2**attempt), RETRY_MAX_DELAY))
    return None


def _download_file(url, filepath, max_retries=3):
    for attempt in range(max_retries):
        try:
            r = requests.get(url, timeout=120)
            if r.status_code == 200:
                with open(filepath, 'wb') as f: f.write(r.content)
                return
            if attempt < max_retries - 1: time.sleep(5)
        except Exception:
            if attempt < max_retries - 1: time.sleep(5)
    raise RuntimeError(f"下载失败(重试{max_retries}次): {url}")
