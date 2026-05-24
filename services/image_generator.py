import os
import time
import requests
from config import RESOLUTIONS, MAX_RETRIES, RETRY_BASE_DELAY, RETRY_MAX_DELAY


def generate_image(model_config, image_prompt, resolution_key, output_path):
    """调用 Seedream 5.0 Lite 文生图 API（同步接口）"""
    api_key = model_config.get('api_key')
    api_url = model_config.get('api_url')
    model = model_config.get('model')

    if not api_key or not model:
        raise ValueError("Seedream API 配置不完整")

    res = RESOLUTIONS.get(resolution_key, RESOLUTIONS['1920x1080'])

    payload = {
        'model': model,
        'prompt': image_prompt,
        'sequential_image_generation': 'disabled',
        'response_format': 'url',
        'size': res['size'],
        'stream': False,
        'watermark': True
    }

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }

    image_url = _call_api(api_url, headers, payload)
    if not image_url:
        raise RuntimeError("Seedream 图片生成失败")

    _download_file(image_url, output_path)

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError("下载的图片为空")

    return output_path


def _call_api(api_url, headers, payload):
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.post(api_url, json=payload, headers=headers, timeout=(10, 120))
            if r.status_code == 429:
                time.sleep(min(RETRY_BASE_DELAY * (2 ** attempt) * 2, RETRY_MAX_DELAY))
                continue
            if 500 <= r.status_code < 600 and attempt < MAX_RETRIES - 1:
                time.sleep(min(RETRY_BASE_DELAY * (2 ** attempt), RETRY_MAX_DELAY))
                continue
            if r.status_code != 200:
                return None
            result = r.json()
            # 同步接口直接返回 url
            return result.get('data', [{}])[0].get('url') if 'data' in result else result.get('url')
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            if attempt < MAX_RETRIES - 1:
                time.sleep(min(RETRY_BASE_DELAY * (2 ** attempt), RETRY_MAX_DELAY))
        except Exception:
            if attempt < MAX_RETRIES - 1:
                time.sleep(min(RETRY_BASE_DELAY * (2 ** attempt), RETRY_MAX_DELAY))
    return None


def _download_file(url, filepath, max_retries=3):
    for attempt in range(max_retries):
        try:
            r = requests.get(url, timeout=120)
            if r.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(r.content)
                return
            if attempt < max_retries - 1:
                time.sleep(5)
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(5)
    raise RuntimeError(f"下载失败，已重试 {max_retries} 次")
