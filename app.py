"""
智演助手 1.5 — 故事文档 → AI视频，6步全自动流水线
DeepSeek(剧本) → Seedream(出图) → Seedance(视频) → ffmpeg(合成)
"""

import os, json, uuid, time, hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, send_file, send_from_directory, redirect
from flask_cors import CORS
from dotenv import load_dotenv

from logger_config import setup_logger
from config import (MAX_UPLOAD_SIZE, ALLOWED_DOC_EXTENSIONS, get_model_config,
                     AUTO_MODE_DEFAULTS, AUTO_DURATION_OPTIONS, LANGUAGES, DEFAULT_LANGUAGE)
from services.document_parser import parse_document
from services.llm_service import generate_prompts, design_shots_from_document
from services.image_generator import generate_image
from services.tts_service import generate_narration
from services.composer import compose_video

load_dotenv()  # 加载 .env 里的 API 密钥

logger = setup_logger('app')
logger.info("智演助手 1.5 启动")

# --- Flask 初始化 ---
app = Flask(__name__)
CORS(app, origins=[r'^https?://(localhost|127\.0\.0\.1)(:\d+)?$'])  # 只允许本地访问
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_SIZE  # 100MB

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# --- 访问控制：token 门禁（部署公网时在 .env 设置 ACCESS_TOKEN） ---

ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN', '')


def _login_page(error=''):
    """极简登录页，零依赖"""
    err_html = f'<p style="color:#e74c3c;text-align:center;margin-bottom:12px">{error}</p>' if error else ''
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>登录 - 智演助手</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{display:flex;justify-content:center;align-items:center;min-height:100vh;background:#f0f2f5;font-family:-apple-system,sans-serif}}
.box{{background:#fff;padding:40px;border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,.1);width:380px}}
h1{{text-align:center;margin-bottom:24px;color:#2c3e50;font-size:1.5rem}}
input{{width:100%;padding:12px;border:1px solid #ddd;border-radius:8px;font-size:1rem;margin-bottom:16px;outline:none}}
input:focus{{border-color:#3498db}}
button{{width:100%;padding:12px;background:#3498db;color:#fff;border:none;border-radius:8px;font-size:1rem;cursor:pointer;font-weight:600}}
button:hover{{background:#2980b9}}
</style></head>
<body><div class="box"><h1>智演助手</h1>{err_html}
<form method="post" action="/login"><input type="password" name="token" placeholder="访问密码" autofocus>
<button type="submit">登 录</button></form></div></body></html>'''


@app.before_request
def _gate():
    if not ACCESS_TOKEN:
        return  # 未配置 token → 跳过鉴权
    if request.endpoint in ('login', 'static_files'):
        return
    if request.cookies.get('auth') == ACCESS_TOKEN:
        return
    if request.path.startswith('/api/'):
        return jsonify({'error': '未授权'}), 401
    return _login_page()


@app.route('/login', methods=['POST'])
def login():
    token = request.form.get('token', '')
    if token == ACCESS_TOKEN:
        resp = redirect('/')
        resp.set_cookie('auth', token, max_age=60*60*24*30,
                httponly=True, secure=True, samesite='Lax')
        return resp
    return _login_page('密码错误')


# --- 会话管理：每个 session 一个文件夹，状态存 state.json ---

def _session_dir(session_id):
    d = os.path.join(OUTPUT_FOLDER, session_id)
    os.makedirs(d, exist_ok=True)
    return d

def _state_path(session_id):
    return os.path.join(_session_dir(session_id), 'state.json')

def _load_state(session_id):
    p = _state_path(session_id)
    return json.load(open(p, 'r', encoding='utf-8')) if os.path.exists(p) else None

def _save_state(session_id, state):
    with open(_state_path(session_id), 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def _update_state(session_id, status, **kwargs):
    """更新状态并在 state.json 中写 updated_at 时间戳"""
    state = _load_state(session_id) or {}
    state['status'] = status
    state.update(kwargs)
    state['updated_at'] = datetime.now().isoformat()
    _save_state(session_id, state)
    return state


# --- 静态文件 ---

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    if filename in ('styles.css', 'script.js'):
        return send_from_directory('.', filename)
    return jsonify({'error': 'Not found'}), 404


# =========================================================================
# Step 1: 上传文档 → 创建会话
# =========================================================================

@app.route('/api/session/create', methods=['POST'])
def session_create():
    if 'file' not in request.files:
        return jsonify({'error': '没有文件'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': '没有选择文件'}), 400

    # 白名单：只允许 .docx 和 .txt
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_DOC_EXTENSIONS:
        return jsonify({'error': f'不支持 {ext}，仅支持 .docx / .txt'}), 400

    # 创建会话目录，保存文件
    session_id = uuid.uuid4().hex[:32]
    safe_name = secure_filename(file.filename)
    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    filepath = os.path.join(_session_dir(session_id), f"{ts}_{safe_name}")
    file.save(filepath)

    # 根据 mode 组装配置：全自动用固定默认，半自动读取用户选择
    mode = request.form.get('mode', 'semi_auto')

    if mode == 'auto':
        duration_key = request.form.get('total_duration', 'auto')
        total_duration = AUTO_DURATION_OPTIONS.get(duration_key,
                                                   AUTO_DURATION_OPTIONS['auto'])['seconds']
        config = {**AUTO_MODE_DEFAULTS,
                  'mode': 'auto', 'total_duration': total_duration,
                  'duration_mode': 'ai_design',
                  'language': request.form.get('language', DEFAULT_LANGUAGE),
                  'tts_voice': LANGUAGES.get(request.form.get('language', DEFAULT_LANGUAGE),
                                             LANGUAGES[DEFAULT_LANGUAGE])['tts_voice']}
    else:
        config = {
            'mode': 'semi_auto',
            'style_template': request.form.get('style_template', '3d_cartoon'),
            'duration_mode': request.form.get('duration_mode', 'ai_design'),
            'resolution': request.form.get('resolution', '1920x1080'),
            'video_quality': request.form.get('video_quality', '480p'),
            'auto_subtitle': request.form.get('auto_subtitle', 'yes'),
            'auto_sfx': request.form.get('auto_sfx', 'no'),
            'original_audio_level': int(request.form.get('original_audio_level', 20)),
            'bgm_enabled': request.form.get('bgm_enabled', 'no'),
            'bgm_volume': int(request.form.get('bgm_volume', 10)),
            'language': request.form.get('language', DEFAULT_LANGUAGE),
            'tts_voice': request.form.get('tts_voice',
                        LANGUAGES[DEFAULT_LANGUAGE]['tts_voice'])
        }

    _save_state(session_id, {
        'status': 'UPLOADED', 'session_id': session_id,
        'filename': f"{ts}_{safe_name}", 'filepath': filepath,
        'config': config, 'created_at': datetime.now().isoformat()
    })
    logger.info(f"会话创建: {session_id}")
    return jsonify({'session_id': session_id, 'status': 'UPLOADED', 'config': config})


# =========================================================================
# Step 2: DeepSeek 通读文档 → 自动设计分镜
# =========================================================================

@app.route('/api/session/<session_id>/design-shots', methods=['POST'])
def session_design_shots(session_id):
    state = _load_state(session_id)
    if not state:
        return jsonify({'error': 'Session 不存在'}), 404

    try:
        content = parse_document(state['filepath'])
        result = design_shots_from_document(content, state['config'])

        shots = result.get('shots', [])
        scene_map = result.get('scene_map', {})
        character_summary = result.get('character_summary', {})

        # 全自动模式：提取 LLM 自主选择的视觉风格，存入 config 供后续步骤使用
        if state['config'].get('mode') == 'auto':
            directive = result.get('visual_style_directive', '')
            if directive:
                state['config']['visual_style_directive'] = directive
                logger.info(f"AI 自主风格: {directive[:80]}...")

        # 时长策略: ai_design=AI分配 / uniform=全5s / auto_split=上限8s
        dur_mode = state['config']['duration_mode']
        for s in shots:
            orig = s.get('original_duration')
            s['final_duration'] = (5 if dur_mode == 'uniform'
                                   else (orig if orig and orig <= 8 else 8) if dur_mode == 'auto_split'
                                   else (orig or 5))

        _update_state(session_id, 'SHOTS_DESIGNED', shots=shots,
                       scene_map=scene_map, title=result.get('title', ''),
                       character_summary=character_summary,
                       global_tone=result.get('global_tone', ''),
                       config=state['config'])

        logger.info(f"分镜完成: {len(shots)}镜头 {len(scene_map)}场景 {len(character_summary)}角色")
        return jsonify({
            'status': 'SHOTS_DESIGNED',
            'shot_count': len(shots), 'scene_count': len(scene_map),
            'character_count': len(character_summary),
            'title': result.get('title', ''),
            'shots_preview': [{'id': s['id'], 'duration': s.get('final_duration', 5),
                               'camera': s.get('camera_hint', ''), 'mood': s.get('mood', ''),
                               'location': s.get('location', ''),
                               'action': s.get('action_summary', '')[:60]}
                              for s in shots]
        })
    except Exception as e:
        logger.error(f"分镜失败: {e}", exc_info=True)
        return jsonify({'error': '分镜设计失败，请重试'}), 500


# =========================================================================
# Step 3: 两轮 Prompt — 视觉圣经 + 逐镜头生成
# =========================================================================

@app.route('/api/session/<session_id>/prompts', methods=['POST'])
def session_prompts(session_id):
    state = _load_state(session_id)
    if not state or 'shots' not in state:
        return jsonify({'error': '请先完成分镜设计'}), 400

    try:
        prompts = generate_prompts(state['shots'], state['config'],
                                    character_summary=state.get('character_summary'))
        for shot in state['shots']:
            for p in prompts:
                if p['shot_id'] == shot['id']:
                    shot['image_prompt'] = p['image_prompt']
                    shot['video_prompt'] = p['video_prompt']
                    break

        _update_state(session_id, 'PROMPTS_READY', shots=state['shots'])
        logger.info(f"Prompt 完成: {len(state['shots'])}镜头")
        return jsonify({'status': 'PROMPTS_READY', 'shot_count': len(state['shots'])})
    except Exception as e:
        logger.error(f"Prompt 失败: {e}", exc_info=True)
        return jsonify({'error': 'Prompt生成失败，请重试'}), 500


# =========================================================================
# Step 4: Seedream 文生图 — 每镜头独立关键帧（5线程并行）
# =========================================================================

@app.route('/api/session/<session_id>/images', methods=['POST'])
def session_images(session_id):
    state = _load_state(session_id)
    if not state or 'shots' not in state:
        return jsonify({'error': '请先完成 Prompt 生成'}), 400

    model_config = get_model_config('seedream')
    sdir = _session_dir(session_id)
    failed = []
    max_image_retries = 3
    valid_shots = [s for s in state['shots'] if s.get('image_prompt')]

    if not valid_shots:
        return jsonify({'error': '没有可用的 image_prompt'}), 400

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')

    def _gen_one(shot):
        path = os.path.join(sdir, f"{ts}_{shot['id']}_kf.png")
        for attempt in range(max_image_retries):
            try:
                generate_image(model_config, shot.get('image_prompt', ''),
                              state['config']['resolution'], path)
                logger.info(f"  {shot['id']} 关键帧完成")
                return (shot['id'], path)
            except Exception:
                if attempt < max_image_retries - 1:
                    time.sleep(2)
        logger.warning(f"  {shot['id']} 关键帧失败(已重试{max_image_retries}次)")
        return (shot['id'], None)

    try:
        with ThreadPoolExecutor(max_workers=min(len(valid_shots), 5)) as ex:
            futures = {ex.submit(_gen_one, s): s['id'] for s in valid_shots}
            for f in as_completed(futures):
                sid, path = f.result()
                if path and os.path.exists(path):
                    for s in state['shots']:
                        if s['id'] == sid:
                            s['image_path'] = path
                else:
                    failed.append(sid)

        _update_state(session_id, 'IMAGES_GENERATED', shots=state['shots'],
                       failed_shots=failed)
        logger.info(f"图片: {len(valid_shots)-len(failed)}/{len(valid_shots)} 成功")
        return jsonify({'status': 'IMAGES_GENERATED', 'total': len(valid_shots),
                       'failed': failed})
    except Exception as e:
        logger.error(f"图片失败: {e}", exc_info=True)
        return jsonify({'error': '图片生成失败，请重试'}), 500


# =========================================================================
# Step 5: Seedance 图生视频 — 首帧/首尾帧智能模式（10线程并行）
# =========================================================================

@app.route('/api/session/<session_id>/videos', methods=['POST'])
def session_videos(session_id):
    state = _load_state(session_id)
    if not state or 'shots' not in state:
        return jsonify({'error': '请先完成图片生成'}), 400

    model_config = get_model_config('seedance')
    sdir = _session_dir(session_id)
    failed = []
    all_shots = state['shots']
    video_quality = state['config'].get('video_quality', '480p')

    # 配对: 同场景相邻镜头 → 首尾帧平滑过渡 / 跨场景 → 首帧硬切
    valid_shots = []
    for i, shot in enumerate(all_shots):
        if not shot.get('image_path'):
            failed.append(shot['id'])
            continue
        ts_v = datetime.now().strftime('%Y%m%d_%H%M%S')
        out = os.path.join(sdir, f"{ts_v}_{shot['id']}.mp4")
        # 下一镜同场景 → 用它的首帧做本镜尾帧
        last = None
        if i < len(all_shots)-1:
            nxt = all_shots[i+1]
            if nxt.get('image_path') and shot.get('location') == nxt.get('location'):
                last = nxt['image_path']
        valid_shots.append((shot, out, last))

    if not valid_shots:
        return jsonify({'error': '没有可用的关键帧'}), 400

    try:
        api_key = model_config['api_key']
        api_url = model_config['api_url']

        def _b64(path):
            import base64
            with open(path, 'rb') as f:
                b64 = base64.b64encode(f.read()).decode()
            ext = os.path.splitext(path)[1].lower()
            mime = 'image/png' if ext == '.png' else 'image/jpeg'
            return f"data:{mime};base64,{b64}"

        # Phase 1: 并行创建任务
        task_map = {}

        def _create(shot, out, last):
            import requests as r
            content = [
                {'type': 'text', 'text': shot.get('video_prompt', '')},
                {'type': 'image_url', 'image_url': {'url': _b64(shot['image_path'])},
                 'role': 'first_frame'}
            ]
            if last:
                content.append({'type': 'image_url', 'image_url': {'url': _b64(last)},
                               'role': 'last_frame'})

            payload = {'model': model_config['model'], 'content': content,
                       'duration': shot.get('final_duration', 5),
                       'ratio': 'adaptive', 'resolution': video_quality,
                       'watermark': False,
                       'seed': int(hashlib.md5(
                           f"{session_id}_{shot['id']}".encode()).hexdigest()[:8], 16) % (2**31)}

            resp = r.post(api_url, json=payload,
                         headers={'Content-Type': 'application/json',
                                  'Authorization': f'Bearer {api_key}'},
                         timeout=(10, 60))
            if resp.status_code == 200:
                tid = resp.json().get('id')
                if tid:
                    return (tid, shot, out, '首尾帧' if last else '首帧')
            return (None, shot, out, '')

        with ThreadPoolExecutor(max_workers=min(len(valid_shots), 10)) as ex:
            for f in as_completed([ex.submit(_create, s, o, l) for s, o, l in valid_shots]):
                tid, shot, out, mode = f.result()
                if tid:
                    task_map[tid] = (shot, out)
                    logger.info(f"  {shot['id']}: {mode} -> {tid}")
                else:
                    failed.append(shot['id'])

        # Phase 2: 并行轮询 + 下载
        if task_map:
            def _poll(tid, shot, out):
                import requests as r
                h = {'Authorization': f'Bearer {api_key}'}
                for _ in range(120):  # 最长等20分钟
                    try:
                        resp = r.get(f"{api_url}/{tid}", headers=h, timeout=30)
                        if resp.status_code != 200:
                            time.sleep(10); continue
                        st = resp.json().get('status', '').lower()
                        if st == 'succeeded':
                            vu = resp.json().get('content', {}).get('video_url', '')
                            if vu and r.get(vu, timeout=120).status_code == 200:
                                with open(out, 'wb') as vf:
                                    vf.write(r.get(vu, timeout=120).content)
                                shot['video_path'] = out
                                return (shot['id'], True)
                            return (shot['id'], False)
                        if st == 'failed':
                            return (shot['id'], False)
                        time.sleep(10)
                    except Exception:
                        time.sleep(10)
                return (shot['id'], False)

            with ThreadPoolExecutor(max_workers=min(len(task_map), 10)) as ex:
                for f in as_completed([ex.submit(_poll, tid, s, o)
                                       for tid, (s, o) in task_map.items()]):
                    sid, ok = f.result()
                    (None if ok else failed.append(sid))
                    if ok: logger.info(f"  {sid} 视频完成")

        _update_state(session_id, 'VIDEOS_GENERATED', shots=state['shots'],
                       failed_shots=failed)
        return jsonify({'status': 'VIDEOS_GENERATED', 'total': len(all_shots),
                       'failed': failed})
    except Exception as e:
        logger.error(f"视频失败: {e}", exc_info=True)
        return jsonify({'error': '视频生成失败，请重试'}), 500


# =========================================================================
# Step 6: TTS旁白 + 字幕 + 合成
# =========================================================================

@app.route('/api/session/<session_id>/compose', methods=['POST'])
def session_compose(session_id):
    state = _load_state(session_id)
    if not state or 'shots' not in state:
        return jsonify({'error': '请先完成视频生成'}), 400

    sdir = _session_dir(session_id)
    try:
        # 生成旁白 (Edge TTS, 免费)
        for shot in state['shots']:
            if shot.get('narration') and shot['narration'] != '无':
                try:
                    path = os.path.join(sdir, f"{shot['id']}_narration.mp3")
                    generate_narration(shot['narration'], path)
                    shot['narration_path'] = path
                except Exception as e:
                    logger.warning(f"  {shot['id']} TTS失败: {e}")

        # 合成: 字幕+混音+拼接 (composer.py)
        out = compose_video(sdir, state['shots'], state['config'])
        _update_state(session_id, 'COMPOSED', final_video=out)
        logger.info(f"合成完成: {out}")
        return jsonify({'status': 'COMPOSED',
                       'videoUrl': f'/api/session/{session_id}/download'})
    except Exception as e:
        logger.error(f"合成失败: {e}", exc_info=True)
        return jsonify({'error': '视频合成失败，请重试'}), 500


# =========================================================================
# 失败重试 & 下载 & 状态
# =========================================================================

@app.route('/api/session/<session_id>/retry-failed', methods=['POST'])
def session_retry_failed(session_id):
    state = _load_state(session_id)
    if not state: return jsonify({'error': 'Session 不存在'}), 404
    failed_shots = state.get('failed_shots', [])
    if not failed_shots:
        return jsonify({'status': 'NO_FAILURES'})

    sdir, retried, still = _session_dir(session_id), 0, []
    status = state.get('status', '')

    if status == 'IMAGES_GENERATED':
        mc = get_model_config('seedream')
        for shot in state['shots']:
            if shot['id'] not in failed_shots: continue
            path = os.path.join(sdir, f"{shot['id']}_keyframe.png")
            try:
                generate_image(mc, shot.get('image_prompt', ''),
                              state['config']['resolution'], path)
                if os.path.exists(path) and os.path.getsize(path) > 0:
                    shot['image_path'] = path; retried += 1
                else: still.append(shot['id'])
            except Exception as e:
                logger.warning(f"重试图片 {shot['id']} 失败: {e}")
                still.append(shot['id'])

    elif status == 'VIDEOS_GENERATED':
        mc = get_model_config('seedance')
        vq = state['config'].get('video_quality', '480p')

        def _retry_one(shot):
            if shot['id'] not in failed_shots or not shot.get('image_path'):
                return (shot['id'], False)
            import base64, requests
            with open(shot['image_path'], 'rb') as f:
                b64 = f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
            ts_rt = datetime.now().strftime('%Y%m%d_%H%M%S')
            out = os.path.join(sdir, f"{ts_rt}_{shot['id']}_retry.mp4")
            payload = {'model': mc['model'],
                       'content': [{'type': 'text', 'text': shot.get('video_prompt', '')},
                                   {'type': 'image_url', 'image_url': {'url': b64},
                                    'role': 'first_frame'}],
                       'duration': shot.get('final_duration', 5),
                       'ratio': 'adaptive', 'resolution': vq, 'watermark': False,
                       'seed': int(hashlib.md5(f"{session_id}_{shot['id']}".encode()
                                              ).hexdigest()[:8], 16) % (2**31)}
            try:
                r = requests.post(mc['api_url'], json=payload,
                                 headers={'Content-Type': 'application/json',
                                          'Authorization': f'Bearer {mc["api_key"]}'},
                                 timeout=(10, 60))
                if r.status_code == 200 and r.json().get('id'):
                    tid = r.json()['id']
                    for _ in range(120):
                        time.sleep(10)
                        r2 = requests.get(f"{mc['api_url']}/{tid}",
                                         headers={'Authorization': f'Bearer {mc["api_key"]}'},
                                         timeout=30)
                        if r2.status_code == 200 and r2.json().get('status','').lower() == 'succeeded':
                            vu = r2.json().get('content', {}).get('video_url', '')
                            if vu:
                                vr = requests.get(vu, timeout=120)
                                if vr.status_code == 200:
                                    with open(out, 'wb') as vf: vf.write(vr.content)
                                    shot['video_path'] = out
                                    return (shot['id'], True)
                        if r2.status_code == 200 and r2.json().get('status','').lower() == 'failed':
                            break
                return (shot['id'], False)
            except Exception as e:
                logger.warning(f"重试视频 {shot['id']} 失败: {e}")
                return (shot['id'], False)

        targets = [s for s in state['shots'] if s['id'] in failed_shots]
        if targets:
            with ThreadPoolExecutor(max_workers=min(len(targets), 5)) as ex:
                for f in as_completed([ex.submit(_retry_one, s) for s in targets]):
                    sid, ok = f.result()
                    (retried := retried + 1) if ok else still.append(sid)

    _update_state(session_id, status, shots=state['shots'], failed_shots=still)
    return jsonify({'status': 'RETRIED', 'retried': retried, 'still_failed': still})


# =========================================================================
# /rerun: 从指定步骤重跑流水线 (design / prompts / images)
# =========================================================================

@app.route('/api/session/<session_id>/rerun', methods=['POST'])
def session_rerun(session_id):
    """从指定步骤重跑流水线。from=design|prompts|images"""
    state = _load_state(session_id)
    if not state:
        return jsonify({'error': 'Session 不存在'}), 404

    from_step = request.args.get('from', 'images')
    step_order = ['design', 'prompts', 'images']
    if from_step not in step_order:
        return jsonify({'error': '无效步骤，可选: {}。视频和合成请用 /videos 和 /compose 端点'.format(step_order)}), 400

    start_idx = step_order.index(from_step)
    results = {'rerun_from': from_step, 'steps_executed': []}

    try:
        for step in step_order[start_idx:]:
            if step == 'design':
                content = parse_document(state['filepath'])
                result = design_shots_from_document(content, state['config'])
                shots = result.get('shots', [])
                dur_mode = state['config']['duration_mode']
                for s in shots:
                    orig = s.get('original_duration')
                    s['final_duration'] = (5 if dur_mode == 'uniform'
                        else (orig if orig and orig <= 8 else 8) if dur_mode == 'auto_split'
                        else (orig or 5))
                if state['config'].get('mode') == 'auto':
                    directive = result.get('visual_style_directive', '')
                    if directive:
                        state['config']['visual_style_directive'] = directive
                _update_state(session_id, 'SHOTS_DESIGNED', shots=shots,
                    scene_map=result.get('scene_map', {}), title=result.get('title', ''),
                    character_summary=result.get('character_summary', {}),
                    global_tone=result.get('global_tone', ''), config=state['config'])
                state = _load_state(session_id)
                results['shots_count'] = len(shots)
                results['steps_executed'].append('design')

            elif step == 'prompts':
                shots = state.get('shots', [])
                if not shots:
                    return jsonify({'error': '无分镜数据，请从 design 开始'}), 400
                prompts = generate_prompts(shots, state['config'], state.get('character_summary'))
                for s, p in zip(shots, prompts):
                    s['image_prompt'] = p.get('image_prompt', '')
                    s['video_prompt'] = p.get('video_prompt', '')
                _update_state(session_id, 'PROMPTS_READY', shots=shots, prompts=prompts)
                state = _load_state(session_id)
                results['steps_executed'].append('prompts')

            elif step == 'images':
                shots = state.get('shots', [])
                valid_shots = [s for s in shots if s.get('image_prompt') and len(s.get('image_prompt', '').strip()) >= 20]
                failed_img = []
                with ThreadPoolExecutor(max_workers=5) as pool:
                    futs = {}
                    for s in valid_shots:
                        img_path = os.path.join(_session_dir(session_id), '{}.png'.format(s['id']))
                        futs[pool.submit(generate_image, get_model_config('seedream'),
                            s['image_prompt'], state['config'].get('resolution', '1920x1080'), img_path)] = s
                    for f in as_completed(futs):
                        s = futs[f]
                        try:
                            f.result()
                            s['image_path'] = os.path.join(_session_dir(session_id), '{}.png'.format(s['id']))
                        except Exception:
                            failed_img.append(s['id'])
                _update_state(session_id, 'IMAGES_GENERATED', shots=shots, failed_images=failed_img)
                results['failed_images'] = len(failed_img)
                results['steps_executed'].append('images')

        results['status'] = _load_state(session_id).get('status', 'OK')
        return jsonify(results)

    except Exception as e:
        logger.error('rerun 失败: {}'.format(str(e)))
        return jsonify({'error': str(e)}), 500


@app.route('/api/session/<session_id>/download', methods=['GET'])
def session_download(session_id):
    state = _load_state(session_id)
    if not state or not state.get('final_video'):
        return jsonify({'error': '视频尚未合成'}), 404
    p = state['final_video']
    return send_file(p, as_attachment=True,
                     download_name=os.path.basename(p) if p else 'video.mp4')


@app.route('/api/session/<session_id>/status', methods=['GET'])
def session_status(session_id):
    state = _load_state(session_id)
    if not state:
        return jsonify({'error': 'Session 不存在'}), 404

    status = state.get('status', 'UPLOADED')
    shots = state.get('shots', [])
    total = len(shots) or 1

    # 进度百分比
    progress_map = {
        'UPLOADED': 5, 'SHOTS_DESIGNED': 15, 'PROMPTS_READY': 30,
        'IMAGES_GENERATED': 55, 'VIDEOS_GENERATED': 85, 'COMPOSED': 100
    }
    base = progress_map.get(status, 5)

    if status == 'IMAGES_GENERATED' or status == 'VIDEOS_GENERATED' or status == 'COMPOSED':
        done = sum(1 for s in shots if s.get('video_path' if status != 'IMAGES_GENERATED' else 'image_path') and
                   os.path.exists(s.get('video_path' if status != 'IMAGES_GENERATED' else 'image_path', '')))
        if status == 'IMAGES_GENERATED':
            progress = min(45 + int((done / total) * 20), 64)
        elif status == 'VIDEOS_GENERATED':
            progress = min(65 + int((done / total) * 30), 94)
        else:
            progress = 100
    else:
        progress = base

    step_detail = '{} ({}/{})'.format(status,
        sum(1 for s in shots if s.get('video_path')), total) if status in ('IMAGES_GENERATED','VIDEOS_GENERATED') else status

    return jsonify({
        'session_id': session_id, 'status': status, 'progress': progress,
        'step_detail': step_detail,
        'stats': {'shots_done': sum(1 for s in shots if s.get('image_path')),
                  'shots_total': total}
    })


if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)
