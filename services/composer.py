"""
视频合成 — ffmpeg 驱动: 字幕叠加 + 旁白混音 + 音轨统一 + xfade拼接
"""

import os, subprocess, logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _norm(path):
    return os.path.abspath(path).replace('\\', '/')  # ffmpeg 兼容正斜杠


def compose_video(session_dir, shots, config, global_tone=''):
    """主线: 逐镜头处理(字幕+混音) → 统一音轨 → xfade拼接 → 回退硬切。"""
    processed, temps = [], []
    auto_sub = config.get('auto_subtitle', 'yes') == 'yes'
    vid_vol = int(config.get('original_audio_level', 20)) / 100.0
    # 按语言选字幕字体
    from config import LANGUAGES, DEFAULT_LANGUAGE
    lang = config.get('language', DEFAULT_LANGUAGE)
    subtitle_font = LANGUAGES.get(lang, LANGUAGES[DEFAULT_LANGUAGE]).get('font', '')

    for shot in shots:
        vp = shot.get('video_path') or os.path.join(session_dir, f"{shot['id']}.mp4")
        if not vp or not os.path.exists(vp): continue

        cur = vp

        # 字幕叠加
        sub_text = shot.get('on_screen_text', '')
        if auto_sub and sub_text:
            sp = os.path.join(session_dir, f"{shot['id']}_subbed.mp4")
            _burn_subtitle(cur, sub_text, sp, subtitle_font)
            cur = sp; temps.append(sp)

        # 旁白混音（original_audio_level控制原视频音量，值越高原音越低）
        nar = shot.get('narration_path')
        if nar and os.path.exists(nar):
            mp = os.path.join(session_dir, f"{shot['id']}_mixed.mp4")
            _mix_audio(cur, nar, mp, narration_volume=0.72,
                       video_volume=max(0.08, 1.0 - vid_vol))
            cur = mp; temps.append(mp)

        processed.append(cur)

    if not processed:
        raise RuntimeError("没有可用的视频片段")

    # 统一音轨：无音轨的补静音，避免 concat/xfade 崩溃
    normalized = []
    for p in processed:
        if _has_audio(p): normalized.append(p)
        else:
            sp = os.path.join(session_dir, f"silent_{len(normalized)}.mp4")
            _add_silent_audio(p, sp)
            normalized.append(sp); temps.append(sp)

    # === 时长修正 ===
    # 中文 TTS ~4字/秒；英文 narration ~3词/秒（保守估计）
    import re as _re
    nar_total = 0.0
    for s in shots:
        nar = s.get('narration', '')
        if not nar:
            continue
        # 剥离 SSML 标签，只计算实际文本字数
        nar_clean = _re.sub(r'<[^>]+>', '', nar).strip()
        if not nar_clean:
            continue
        # 判断语言：含中文字符按 4字/秒，否则按英文词速
        if any('\u4e00' <= c <= '\u9fff' for c in nar_clean):
            nar_total += len(nar_clean) / 4.0
        else:
            nar_total += len(nar_clean.split()) / 3.0

    vid_total = sum(max(_get_duration(p), 0.5) for p in normalized)  # 每段至少0.5s

    if nar_total > vid_total and len(normalized) > 0 and nar_total > 1.0:
        last = normalized[-1]
        diff = nar_total - vid_total
        loops = int(diff / (_get_duration(last) or 5)) + 1
        looped = os.path.join(session_dir, 'last_looped.mp4')
        r_loop = subprocess.run(['ffmpeg', '-y', '-stream_loop', str(loops), '-i', _norm(last),
            '-t', str(diff), '-c', 'copy', _norm(looped)],
            capture_output=True, text=True)
        if r_loop.returncode != 0:
            logger.warning(f"视频循环扩展失败: {r_loop.stderr[:300]}")
        concatted = os.path.join(session_dir, 'last_extended.mp4')
        r_concat = subprocess.run(['ffmpeg', '-y',
            '-i', _norm(last), '-i', _norm(looped),
            '-filter_complex', '[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]',
            '-map', '[outv]', '-map', '[outa]',
            '-c:v', 'libx264', '-c:a', 'aac', _norm(concatted)],
            capture_output=True, text=True)
        if r_concat.returncode != 0:
            logger.warning(f"视频拼接失败: {r_concat.stderr[:300]}")
        normalized[-1] = concatted
        temps.extend([looped, concatted])

    # === BGM 混音 ===
    bgm_enabled = config.get('bgm_enabled', 'no') == 'yes'
    if bgm_enabled:
        bgm_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resource', 'bgm')
        if os.path.exists(bgm_dir):
            bgm_files = [f for f in os.listdir(bgm_dir) if f.endswith(('.mp3', '.wav'))]
            if bgm_files:
                bgm_vol = int(config.get('bgm_volume', 10)) / 100.0
                bgm_path = _pick_bgm(bgm_dir, bgm_files, global_tone, session_dir)
                for i, clip_path in enumerate(normalized):
                    dur = _get_duration(clip_path)
                    bgm_clip = os.path.join(session_dir, 'bgm_{}.mp4'.format(i))
                    r_bgm = subprocess.run(['ffmpeg', '-y',
                        '-i', _norm(clip_path),
                        '-stream_loop', '-1', '-i', _norm(bgm_path),
                        '-filter_complex',
                        '[1:a]volume={},aformat=sample_fmts=fltp:channel_layouts=stereo,atrim=0:{},afade=t=out:st={}:d=3[bgm];'
                        '[0:a]volume={}[orig];'
                        '[bgm][orig]amix=inputs=2:duration=first[outa]'.format(
                            bgm_vol, dur, max(0,dur-3), 1.0 - bgm_vol),
                        '-map', '0:v', '-map', '[outa]',
                        '-c:v', 'copy', '-c:a', 'aac', _norm(bgm_clip)],
                        capture_output=True, text=True)
                    if r_bgm.returncode != 0:
                        logger.warning(f"BGM 混音失败 (shot {i}): {r_bgm.stderr[:300]}")
                    normalized[i] = bgm_clip
                    temps.append(bgm_clip)

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out = os.path.join(session_dir, f"{ts}_final.mp4")

    if len(normalized) == 1:
        r = subprocess.run(['ffmpeg', '-y', '-i', _norm(normalized[0]), '-c', 'copy', _norm(out)],
                          capture_output=True, text=True)
        if r.returncode != 0: raise RuntimeError(f"拼接失败: {r.stderr[:500]}")
        _cleanup(temps); return out

    # xfade 交叉淡入淡出（0.3s过渡）
    dur = 0.3
    inputs = []
    for p in normalized: inputs.extend(['-i', _norm(p)])
    durations = [_get_duration(p) for p in normalized]
    fs = _xfade_filter(len(normalized), dur, durations)

    r = subprocess.run(['ffmpeg', '-y'] + inputs +
        ['-filter_complex', fs, '-map', '[outv]', '-map', '[outa]',
         '-c:v', 'libx264', '-c:a', 'aac', '-preset', 'fast',
         '-pix_fmt', 'yuv420p', _norm(out)], capture_output=True, text=True)

    if r.returncode != 0:
        import logging
        logging.getLogger('composer').warning(f"xfade失败，回退硬切: {r.stderr[-200:]}")
        return _hard_concat(normalized, session_dir)

    _cleanup(temps); return out


def _hard_concat(clips, sdir):
    """硬切拼接（xfade 回退方案）。"""
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out = os.path.join(sdir, f"{ts}_final.mp4")
    inputs = []; n = len(clips)
    for p in clips: inputs.extend(['-i', _norm(p)])
    fs = ''.join(f'[{i}:v:0][{i}:a:0]' for i in range(n)) + f'concat=n={n}:v=1:a=1[outv][outa]'
    r = subprocess.run(['ffmpeg', '-y'] + inputs +
        ['-filter_complex', fs, '-map', '[outv]', '-map', '[outa]',
         '-c:v', 'libx264', '-c:a', 'aac', '-preset', 'fast', _norm(out)],
        capture_output=True, text=True)
    if r.returncode != 0: raise RuntimeError(f"硬切失败: {r.stderr[-500:]}")
    return out


def _get_duration(fp):
    """ffprobe 获取时长，失败返回5s兜底"""
    import json as _json
    try:
        r = subprocess.run(['ffprobe', '-v', 'quiet', '-print_format', 'json',
                           '-show_format', _norm(fp)], capture_output=True, text=True)
        return float(_json.loads(r.stdout)['format'].get('duration', 5)) if r.returncode == 0 else 5
    except Exception: return 5


def _xfade_filter(n, dur, durations):
    """xfade + acrossfade 滤镜链。
    acrossfade 只支持 2 路输入，多路需两两链式渐入。
    视觉: xfade 串联渐入淡出。
    """
    if n <= 1:
        return f'[0:v][0:a]concat=n=1:v=1:a=1[outv][outa]'
    if n == 2:
        return (f'[0:a][1:a]acrossfade=d={dur}:c1=tri:c2=tri[outa];'
                f'[0:v][1:v]xfade=transition=fade:duration={dur}:offset={durations[0]-dur}[outv]')

    # n > 2: 音频两两链式渐入，最后一步直接输出 [outa]
    ac_parts = []
    ac_parts.append(f'[0:a][1:a]acrossfade=d={dur}:c1=tri:c2=tri[a0]')
    for i in range(2, n - 1):
        ac_parts.append(f'[a{i-2}][{i}:a]acrossfade=d={dur}:c1=tri:c2=tri[a{i-1}]')
    ac_parts.append(f'[a{n-3}][{n-1}:a]acrossfade=d={dur}:c1=tri:c2=tri[outa]')
    ac = ';'.join(ac_parts)

    # 视频 xfade 串联
    accum = durations[0]
    vc = f'[0:v][1:v]xfade=transition=fade:duration={dur}:offset={durations[0]-dur}[v0]'
    for i in range(2, n):
        accum += durations[i-1] - dur
        vc += f';[v{i-2}][{i}:v]xfade=transition=fade:duration={dur}:offset={accum-dur}[v{i-1}]'
    last = f'v{n-2}'
    return f'{ac};{vc};[{last}]copy[outv]'


def _burn_subtitle(vp, text, out, font_path=None):
    """ffmpeg drawtext 烧录硬字幕到底部。按语言选字体，支持中日韩英。"""
    import re, os as _os
    safe = re.sub(r"[^一-鿿぀-ゟ゠-ヿ가-힯"
                  r"a-zA-Z0-9\s.,!?;:()（）【】《》、。，！？；：\"'%@#$&*+=~\[\]{{}}<>/|\\\\-]",
                  '', text).replace("'", "\\'").replace(":", "\\:")

    lines, cur = [], ''
    for c in safe:
        cur += c
        if len(cur) >= 20: lines.append(cur); cur = ''
    if cur: lines.append(cur)
    txt = '\\n'.join(lines)

    vf = (f"drawtext=text='{txt}':fontsize=28:fontcolor=white:borderw=2:"
          f"bordercolor=black@0.6:x=(w-text_w)/2:y=h-th-60")
    # 按语言选字体。优先项目本地 resource/fonts/ 避免 Windows 路径冒号问题
    font_list = []
    if font_path and _os.path.exists(font_path):
        font_list.append(font_path)
    # 项目自带字体（优先，路径无冒号）
    _project_fonts = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), 'resource', 'fonts')
    for _fn in ['simhei.ttf', 'msyh.ttc', 'NotoSansCJK-Regular.ttc']:
        _fp = _os.path.join(_project_fonts, _fn)
        if _os.path.exists(_fp):
            font_list.append(_fp)
    # 系统字体 fallback (Linux/macOS 无冒号路径安全)
    font_list.extend([
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/System/Library/Fonts/PingFang.ttc',
    ])
    for font in font_list:
        r = subprocess.run(['ffmpeg', '-y', '-i', _norm(vp), '-vf',
            vf + f":fontfile={font}",
            '-c:v', 'libx264', '-c:a', 'copy', '-preset', 'fast', '-pix_fmt', 'yuv420p', _norm(out)],
            capture_output=True, text=True)
        if r.returncode == 0:
            return out
    # 最终回退
    r = subprocess.run(['ffmpeg', '-y', '-i', _norm(vp), '-vf', vf,
        '-c:v', 'libx264', '-c:a', 'copy', '-preset', 'fast', '-pix_fmt', 'yuv420p', _norm(out)],
        capture_output=True, text=True)
    if r.returncode != 0: raise RuntimeError(f"字幕失败: {r.stderr[:300]}")
    return out


def _mix_audio(vp, ap, out, narration_volume=1.0, video_volume=0.3):
    """混音: 旁白apad对齐视频时长 + amix混合。旁白短→补静音，旁白长→截断。"""
    vid_dur = _get_duration(vp)
    r = subprocess.run(['ffmpeg', '-y', '-i', _norm(vp), '-i', _norm(ap),
        '-filter_complex',
        f'[1:a]volume={narration_volume},apad=whole_dur={vid_dur}[nar];'
        f'[0:a]volume={video_volume}[vid];'
        f'[nar][vid]amix=inputs=2:duration=first:dropout_transition=2[outa]',
        '-map', '0:v', '-map', '[outa]', '-c:v', 'copy', '-c:a', 'aac', _norm(out)],
        capture_output=True, text=True)
    if r.returncode != 0: raise RuntimeError(f"混音失败: {r.stderr[:500]}")
    return out


def add_audio_to_video(vp, ap, out):
    """简单音频叠加（外部BGM等）。"""
    r = subprocess.run(['ffmpeg', '-y', '-i', _norm(vp), '-i', _norm(ap),
        '-c:v', 'copy', '-c:a', 'aac', '-shortest', _norm(out)],
        capture_output=True, text=True)
    if r.returncode != 0: raise RuntimeError(f"音频叠加失败: {r.stderr[:500]}")
    return out


def _has_audio(fp):
    """ffprobe 检查是否有音轨。"""
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a:0',
        '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', _norm(fp)],
        capture_output=True, text=True)
    return r.returncode == 0 and 'audio' in r.stdout


def _add_silent_audio(vp, out):
    """为无音轨视频添加静音流（anullsrc 生成），保证 concat 音轨一致。"""
    r = subprocess.run(['ffmpeg', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo',
        '-i', _norm(vp), '-c:v', 'copy', '-c:a', 'aac', '-shortest',
        '-map', '1:v', '-map', '0:a', _norm(out)], capture_output=True, text=True)
    if r.returncode != 0: raise RuntimeError(f"静音轨失败: {r.stderr[:300]}")
    return out


def _pick_bgm(bgm_dir, bgm_files, global_tone, session_dir):
    """根据视频情绪匹配 BGM，不回退到 hash 取模。"""
    import os as _os
    tone_lower = (global_tone or '').lower()

    # 情绪 → bgm 文件名关键词映射
    mood_map = {
        'cinematic': ['cinematic', 'epic', 'dramatic'],
        'upbeat': ['upbeat', 'happy', 'bright'],
        'gentle': ['gentle', 'soft', 'warm'],
        'calm': ['calm', 'peaceful', 'ambient'],
    }

    # 按情绪匹配
    for mood, keywords in mood_map.items():
        if any(kw in tone_lower for kw in keywords + [mood]):
            matches = [f for f in bgm_files
                       if any(kw in f.lower() for kw in keywords + [mood])]
            if matches:
                return _os.path.join(bgm_dir, matches[0])

    # 回退：选与 tone 中任何关键词有交集的 bgm
    tone_words = set(tone_lower.replace(',', ' ').split())
    for f in bgm_files:
        f_words = set(f.lower().replace('.mp3', '').replace('.wav', '').split('_'))
        if tone_words & f_words:
            return _os.path.join(bgm_dir, f)

    # 最终回退
    return _os.path.join(bgm_dir, bgm_files[hash(session_dir) % len(bgm_files)])


def _cleanup(files):
    for f in files:
        try:
            if os.path.exists(f): os.remove(f)
        except OSError: pass
