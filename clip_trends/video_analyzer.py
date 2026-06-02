"""ffmpeg 下载+抽帧 + ffprobe 音频分析"""
import os, glob, subprocess, json, tempfile
from config import VIDEO_ANALYSIS


def analyze_video(video_url: str, download_func) -> dict | None:
    """
    完整视频分析流水线，返回:
    {
        'frames': ['/path/frame_001.jpg', ...],
        'duration': 30.5,
        'resolution': '1920x1080',
        'fps': 24.0,
        'audio': {'has_audio': True, 'rms_db': -18.5, 'peak_db': -3.2},
        'temp_dir': '/tmp/xxx',
    }
    失败返回 None
    """
    temp_dir = tempfile.mkdtemp(dir=VIDEO_ANALYSIS.get('download_dir', 'clip_trends/temp_videos/'))
    os.makedirs(temp_dir, exist_ok=True)
    try:
        video_path = os.path.join(temp_dir, 'video.mp4')

        # 1. 下载完整视频
        success = download_func(video_url, video_path)
        if not success:
            return None

        # 2. ffprobe 提取元数据
        duration, resolution, fps = _ffprobe_meta(video_path)
        if duration is None or duration <= 0:
            return None

        # 3. ffprobe 提取音频特征
        audio_info = _ffprobe_audio(video_path)

        # 4. ffmpeg 抽帧：每 3 秒 1 帧
        frame_pattern = os.path.join(temp_dir, 'frame_%03d.jpg')
        subprocess.run([
            'ffmpeg', '-y', '-i', video_path,
            '-vf', f'fps=1/{VIDEO_ANALYSIS["frame_interval"]}',
            '-qscale:v', '2',
            frame_pattern
        ], capture_output=True, timeout=120)

        frames = sorted(glob.glob(os.path.join(temp_dir, 'frame_*.jpg')))

        # 5. 删除原始视频（保留抽帧 jpg）
        if os.path.exists(video_path):
            os.remove(video_path)

        return {
            'frames': frames,
            'duration': duration,
            'resolution': resolution,
            'fps': fps,
            'audio': audio_info,
            'temp_dir': temp_dir,
        }
    except Exception:
        return None


def _ffprobe_meta(video_path: str) -> tuple:
    """返回 (duration_sec, resolution_str, fps)"""
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', video_path
        ], capture_output=True, text=True, timeout=30)
        data = json.loads(result.stdout)

        duration = float(data.get('format', {}).get('duration', 0))

        video_stream = None
        for s in data.get('streams', []):
            if s.get('codec_type') == 'video':
                video_stream = s
                break

        if video_stream:
            width = video_stream.get('width', 0)
            height = video_stream.get('height', 0)
            resolution = f'{width}x{height}' if width and height else 'unknown'
            fps_str = video_stream.get('r_frame_rate', '0/1')
            num, den = fps_str.split('/')
            fps = float(num) / float(den) if float(den) != 0 else 0
        else:
            resolution = 'unknown'
            fps = 0

        return duration, resolution, fps
    except Exception:
        return None, 'unknown', 0


def _ffprobe_audio(video_path: str) -> dict:
    """提取音频特征"""
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_streams', video_path
        ], capture_output=True, text=True, timeout=30)
        data = json.loads(result.stdout)

        has_audio = any(s.get('codec_type') == 'audio' for s in data.get('streams', []))
        if not has_audio:
            return {'has_audio': False, 'rms_db': None, 'peak_db': None}

        null_dev = 'NUL' if os.name == 'nt' else '/dev/null'
        result2 = subprocess.run([
            'ffmpeg', '-i', video_path,
            '-af', 'volumedetect',
            '-vn', '-sn', '-dn',
            '-f', 'null', null_dev
        ], capture_output=True, text=True, timeout=60)

        import re
        mean_match = re.search(r'mean_volume:\s*(-?[\d.]+)', result2.stderr + result2.stdout)
        max_match = re.search(r'max_volume:\s*(-?[\d.]+)', result2.stderr + result2.stdout)

        return {
            'has_audio': True,
            'rms_db': float(mean_match.group(1)) if mean_match else None,
            'peak_db': float(max_match.group(1)) if max_match else None,
        }
    except Exception:
        return {'has_audio': False, 'rms_db': None, 'peak_db': None}


def cleanup_temp(temp_dir: str):
    """清理临时目录"""
    import shutil
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)
