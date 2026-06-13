"""图片 → base64, Seedance API 封装, 视频下载"""

import os, time, hashlib, base64, logging

logger = logging.getLogger(__name__)


def image_to_base64_dataurl(image_path: str) -> str:
    with open(image_path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode()
    ext = os.path.splitext(image_path)[1].lower()
    mime = 'image/png' if ext == '.png' else 'image/jpeg'
    return f"data:{mime};base64,{b64}"


def build_seedance_payload(
    model: str, first_frame_path: str, video_prompt: str,
    duration: int, resolution: str, seed_session_id: str,
    last_frame_path: str = None, generate_audio: bool = True,
) -> dict:
    content = [
        {'type': 'text', 'text': video_prompt or ''},
        {'type': 'image_url',
         'image_url': {'url': image_to_base64_dataurl(first_frame_path)},
         'role': 'first_frame'},
    ]
    if last_frame_path:
        content.append({
            'type': 'image_url',
            'image_url': {'url': image_to_base64_dataurl(last_frame_path)},
            'role': 'last_frame',
        })

    seed = int(hashlib.md5(seed_session_id.encode()).hexdigest()[:8], 16) % (2 ** 31)

    return {
        'model': model, 'content': content,
        'duration': duration, 'aspect_ratio': '16:9',
        'resolution': resolution, 'watermark': False, 'seed': seed,
        'generate_audio': generate_audio,
    }


def create_seedance_task(api_url: str, api_key: str, payload: dict) -> str | None:
    import requests as r
    try:
        resp = r.post(api_url, json=payload,
                      headers={'Content-Type': 'application/json',
                               'Authorization': f'Bearer {api_key}'},
                      timeout=(10, 60))
        if resp.status_code == 200:
            tid = resp.json().get('id')
            if tid:
                return tid
        logger.warning(f"Seedance 创建任务失败: HTTP {resp.status_code}")
        return None
    except Exception as e:
        logger.warning(f"Seedance 创建任务异常: {e}")
        return None


def poll_seedance_task(api_url: str, api_key: str, task_id: str,
                      max_wait_sec: int = 600) -> dict:
    """渐进式轮询: 前30s每5s一次, 30-120s每10s, 之后每15s"""
    import requests as r
    headers = {'Authorization': f'Bearer {api_key}'}
    elapsed = 0

    while elapsed < max_wait_sec:
        if elapsed < 30:
            interval = 5
        elif elapsed < 120:
            interval = 10
        else:
            interval = 15

        time.sleep(interval)
        elapsed += interval
        try:
            resp = r.get(f"{api_url}/{task_id}", headers=headers, timeout=30)
            if resp.status_code != 200:
                continue
            data = resp.json()
            st = data.get('status', '').lower()
            if st == 'succeeded':
                vu = data.get('content', {}).get('video_url', '')
                return {'status': 'succeeded', 'video_url': vu}
            if st == 'failed':
                return {'status': 'failed', 'video_url': None}
        except Exception:
            pass
    return {'status': 'timeout', 'video_url': None}


def download_video(video_url: str, output_path: str, timeout: int = 120) -> bool:
    import requests as r
    try:
        resp = r.get(video_url, timeout=timeout)
        if resp.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(resp.content)
            return os.path.exists(output_path) and os.path.getsize(output_path) > 0
    except Exception as e:
        logger.warning(f"视频下载失败: {e}")
    return False
