import os
import subprocess
import tempfile


def compose_video(session_dir, shots, config):
    """拼接所有视频片段为最终视频（使用 ffmpeg 命令行）"""
    # 收集有效视频片段
    clip_paths = []
    for shot in shots:
        shot_id = shot['id']
        video_path = os.path.join(session_dir, f"{shot_id}.mp4")
        if os.path.exists(video_path):
            clip_paths.append(video_path)

    if not clip_paths:
        raise RuntimeError("没有可用的视频片段")

    # 生成 concat 文件列表
    concat_list_path = os.path.join(session_dir, "concat_list.txt")
    with open(concat_list_path, 'w', encoding='utf-8') as f:
        for p in clip_paths:
            f.write(f"file '{p}'\n")

    output_path = os.path.join(session_dir, "final_video.mp4")

    # ffmpeg 拼接
    cmd = [
        'ffmpeg', '-y',
        '-f', 'concat', '-safe', '0',
        '-i', concat_list_path,
        '-c', 'copy',
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"视频拼接失败: {result.stderr[:500]}")

    return output_path


def add_audio_to_video(video_path, audio_path, output_path):
    """将音频叠加到视频上"""
    cmd = [
        'ffmpeg', '-y',
        '-i', video_path,
        '-i', audio_path,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-shortest',
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"音频叠加失败: {result.stderr[:500]}")
    return output_path
