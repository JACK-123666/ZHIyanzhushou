import os
import time
import requests
from config import RESOLUTIONS, MAX_RETRIES, RETRY_BASE_DELAY, RETRY_MAX_DELAY


def generate_video(model_config, video_prompt, image_path, duration, resolution_key, output_path):
    """Seedance 2.0 Fast 图生视频：参考图 + 文本 -> 视频"""
    api_key = model_config.get('api_key')
    api_url = model_config.get('api_url')
    model = model_config.get('model')

    if not api_key or not model:
        raise ValueError("Seedance API 配置不完整")

    res = RESOLUTIONS.get(resolution_key, RESOLUTIONS['1920x1080'])

    # 先上传图片获取 URL（如果需要的话，用 data URL 方式）
    # Seedance 支持 image_url 格式
    payload = {
        'model': model,
        'content': [
            {
                'type': 'text',
                'text': video_prompt
            },
            {
                'type': 'image_url',
                'image_url': {'url': _file_to_data_url(image_path)},
                'role': 'reference_image'
            }
        ],
        'generate_audio': True,
        'ratio': res['ratio'],
        'watermark': False
    }

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }

    task_id = _create_task(api_url, headers, payload)
    if not task_id:
        raise RuntimeError("无法创建 Seedance 视频生成任务")

    video_url = _poll_task(api_url, headers, task_id)
    if not video_url:
        raise RuntimeError("Seedance 视频生成任务未完成")

    _download_file(video_url, output_path)

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError("下载的视频为空")

    return output_path


def _file_to_data_url(filepath):
    import base64
    ext = os.path.splitext(filepath)[1].lower()
    mime_map = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp'}
    mime = mime_map.get(ext, 'image/png')
    with open(filepath, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{b64}"


def _create_task(api_url, headers, payload):
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.post(api_url, json=payload, headers=headers, timeout=(10, 60))
            if r.status_code == 429:
                time.sleep(min(RETRY_BASE_DELAY * (2 ** attempt) * 2, RETRY_MAX_DELAY))
                continue
            if 500 <= r.status_code < 600 and attempt < MAX_RETRIES - 1:
                time.sleep(min(RETRY_BASE_DELAY * (2 ** attempt), RETRY_MAX_DELAY))
                continue
            if r.status_code != 200:
                return None
            result = r.json()
            task_id = result.get('id')
            if task_id:
                return task_id
            if attempt < MAX_RETRIES - 1:
                time.sleep(min(RETRY_BASE_DELAY * (2 ** attempt), RETRY_MAX_DELAY))
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            if attempt < MAX_RETRIES - 1:
                time.sleep(min(RETRY_BASE_DELAY * (2 ** attempt), RETRY_MAX_DELAY))
        except Exception:
            if attempt < MAX_RETRIES - 1:
                time.sleep(min(RETRY_BASE_DELAY * (2 ** attempt), RETRY_MAX_DELAY))
    return None


def _poll_task(api_url, headers, task_id, max_attempts=60, interval=10):
    for _ in range(max_attempts):
        try:
            r = requests.get(f"{api_url}/{task_id}", headers=headers, timeout=30)
            if r.status_code != 200:
                time.sleep(interval)
                continue
            result = r.json()
            status = result.get('status', '').lower()
            if status == 'succeeded':
                return result.get('content', {}).get('video_url')
            if status == 'failed':
                return None
            time.sleep(interval)
        except Exception:
            time.sleep(interval)
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
