import os
import time
import requests
from config import SEEDANCE_STYLE_PROMPTS, SEEDANCE_DURATION_MAP


def generate_video(model_config, prompt, video_data, video_filepath):
    """调用 Seedance API 生成视频：创建任务 → 轮询 → 下载"""
    api_key = model_config.get('api_key')
    video_api_url = model_config.get('video_api_url')
    endpoint = model_config.get('model')

    if not api_key or not endpoint or not video_api_url:
        raise ValueError("Seedance API 配置不完整：缺少 api_key、endpoint 或 video_api_url")

    original_content = video_data.get('content', '')
    style = video_data.get('style', 'business')
    duration = video_data.get('duration', 'medium')

    # 构建文本 prompt
    content_lines = [l.strip() for l in original_content.split('\n') if l.strip() and len(l.strip()) > 10]
    key_content = '\n'.join(content_lines[:5])

    style_desc = SEEDANCE_STYLE_PROMPTS.get(style, SEEDANCE_STYLE_PROMPTS['business'])
    video_duration = SEEDANCE_DURATION_MAP.get(duration, 8)

    final_prompt = f"{key_content}\n{style_desc}\n{prompt}"
    if len(final_prompt) > 500:
        final_prompt = final_prompt[:500]

    payload = {
        'model': endpoint,
        'content': [{
            'type': 'text',
            'text': f"{final_prompt} --duration {video_duration} --camerafixed false --watermark true"
        }]
    }

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }

    task_id = _create_task(video_api_url, headers, payload)
    if not task_id:
        raise RuntimeError("无法创建 Seedance 视频生成任务")

    video_url = _poll_task(video_api_url, headers, task_id)
    if not video_url:
        raise RuntimeError("Seedance 任务未完成或未返回视频 URL")

    _download_video(video_url, video_filepath)

    file_size = os.path.getsize(video_filepath)
    if file_size == 0:
        raise RuntimeError("下载的视频文件为空")

    return video_filepath


def _create_task(api_url, headers, payload, max_retries=3, base_delay=5, max_delay=30):
    """创建 Seedance 视频生成任务（带重试）"""
    for attempt in range(max_retries):
        try:
            response = requests.post(api_url, json=payload, headers=headers, timeout=(10, 60))

            if response.status_code == 429:
                delay = min(base_delay * (2 ** attempt) * 2, max_delay)
                time.sleep(delay)
                continue

            if 500 <= response.status_code < 600:
                if attempt < max_retries - 1:
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    time.sleep(delay)
                    continue
                return None

            if response.status_code != 200:
                return None

            result = response.json()
            task_id = result.get('id')
            if task_id:
                return task_id

            if attempt < max_retries - 1:
                delay = min(base_delay * (2 ** attempt), max_delay)
                time.sleep(delay)

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            if attempt < max_retries - 1:
                delay = min(base_delay * (2 ** attempt), max_delay)
                time.sleep(delay)

        except Exception:
            if attempt < max_retries - 1:
                delay = min(base_delay * (2 ** attempt), max_delay)
                time.sleep(delay)

    return None


def _poll_task(api_url, headers, task_id, max_attempts=30, interval=10):
    """轮询任务状态直到完成或失败"""
    for attempt in range(max_attempts):
        try:
            query_url = f"{api_url}/{task_id}"
            response = requests.get(query_url, headers=headers, timeout=30)

            if response.status_code != 200:
                time.sleep(interval)
                continue

            result = response.json()
            status = result.get('status', '').lower()

            if status == 'succeeded':
                return result.get('result', {}).get('video_url')

            if status == 'failed':
                return None

            # pending / processing / running
            time.sleep(interval)

        except (requests.exceptions.Timeout, Exception):
            time.sleep(interval)

    return None


def _download_video(video_url, filepath, max_retries=3):
    """下载视频文件（带重试）"""
    for attempt in range(max_retries):
        try:
            response = requests.get(video_url, timeout=120)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return
            if attempt < max_retries - 1:
                time.sleep(5)
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(5)

    raise RuntimeError(f"视频下载失败，已重试 {max_retries} 次")
