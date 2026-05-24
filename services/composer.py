import os
import subprocess


def compose_video(session_dir, shots, config):
    """拼接所有视频片段为最终视频（使用 ffmpeg concat filter）"""
    clip_paths = []
    for shot in shots:
        video_path = os.path.join(session_dir, f"{shot['id']}.mp4")
        if os.path.exists(video_path):
            clip_paths.append(os.path.abspath(video_path).replace('\\', '/'))

    if not clip_paths:
        raise RuntimeError("没有可用的视频片段")

    if len(clip_paths) == 1:
        # 单文件直接复制
        output_path = os.path.join(session_dir, "final_video.mp4")
        cmd = ['ffmpeg', '-y', '-i', clip_paths[0], '-c', 'copy', output_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"视频拼接失败: {result.stderr[:500]}")
        return output_path

    # 多文件使用 concat filter
    output_path = os.path.join(session_dir, "final_video.mp4")
    inputs = []
    for p in clip_paths:
        inputs.extend(['-i', p])

    n = len(clip_paths)
    filter_parts = [f'[{i}:v:0][{i}:a:0]' for i in range(n)]
    filter_str = ''.join(filter_parts) + f'concat=n={n}:v=1:a=1[outv][outa]'

    cmd = ['ffmpeg', '-y'] + inputs + [
        '-filter_complex', filter_str,
        '-map', '[outv]', '-map', '[outa]',
        '-c:v', 'libx264', '-c:a', 'aac',
        '-preset', 'fast',
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"视频拼接失败: {result.stderr[-500:]}")

    return output_path


def add_audio_to_video(video_path, audio_path, output_path):
    """将音频叠加到视频上"""
    cmd = [
        'ffmpeg', '-y',
        '-i', video_path.replace('\\', '/'),
        '-i', audio_path.replace('\\', '/'),
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-shortest',
        output_path.replace('\\', '/')
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"音频叠加失败: {result.stderr[:500]}")
    return output_path
