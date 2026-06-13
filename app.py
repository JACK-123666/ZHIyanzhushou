"""Zhiyan — 故事文档 → AI视频，6步全自动"""

import os, json, uuid, time, hashlib, threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, send_file, send_from_directory, redirect
from flask_cors import CORS
from dotenv import load_dotenv
load_dotenv()  # ⚠️ 必须在所有 config 导入之前加载 .env

from logger_config import setup_logger
from config import (MAX_UPLOAD_SIZE, ALLOWED_DOC_EXTENSIONS, get_model_config,
                     AUTO_MODE_DEFAULTS, AUTO_DURATION_OPTIONS, LANGUAGES, DEFAULT_LANGUAGE,
                     STYLE_TEMPLATES)
from services.document_parser import parse_document
from services.llm_service import generate_prompts, design_shots_from_document
from services.image_generator import generate_image
from services.tts_service import generate_narration
from services.composer import compose_video
from services.trend_service import get_trending_techniques, search_techniques
from agent import ZhiyanAgent, WorkingMemory

logger = setup_logger('app')
logger.info("Zhiyan 1.5 启动")

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

# 开发模式下不强制 auth，生产环境若未设 Token 则自动生成
if not ACCESS_TOKEN and os.environ.get('FLASK_ENV') != 'development':
    import secrets
    ACCESS_TOKEN = secrets.token_urlsafe(16)
    logger.warning('=' * 50)
    logger.warning(f'未设置 ACCESS_TOKEN，已生成随机密码: {ACCESS_TOKEN}')
    logger.warning(f'请将 ACCESS_TOKEN={ACCESS_TOKEN} 添加到 .env 文件')
    logger.warning('=' * 50)


def _sanitize_error(e):
    """生产模式脱敏错误信息，防止泄漏 API 端点/密钥"""
    msg = str(e)
    # 服务端记录真实错误
    logger.error(f"请求异常: {msg[:500]}")
    if os.environ.get('FLASK_ENV') == 'development':
        return msg[:500]
    # 生产环境始终返回通用提示，避免黑名单遗漏
    return '服务暂时不可用，请稍后重试'


def _login_page(error=''):
    """极简登录页，零依赖"""
    err_html = f'<p style="color:#e74c3c;text-align:center;margin-bottom:12px">{error}</p>' if error else ''
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>登录 - Zhiyan</title>
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
<body><div class="box"><h1>Zhiyan</h1>{err_html}
<form method="post" action="/login"><input type="password" name="token" placeholder="访问密码" autofocus>
<button type="submit">登 录</button></form></div></body></html>'''


@app.before_request
def _gate():
    # 开发/测试模式：不拦截，直接放行
    if os.environ.get('FLASK_ENV') == 'development':
        return
    if not ACCESS_TOKEN:
        return
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


# --- 速率限制：防止 API 滥用（每 IP 每小时最多 5 个会话） ---

_rate_log = {}  # {ip: [timestamp, ...]}
_rate_lock = threading.Lock()

def _check_rate_limit():
    ip = request.remote_addr or '127.0.0.1'
    now = time.time()
    window = now - 3600
    with _rate_lock:
        entries = _rate_log.get(ip, [])
        entries = [t for t in entries if t > window]
        if not entries:
            _rate_log.pop(ip, None)  # 清理过期 IP，防止内存泄漏
        if len(entries) >= 5:
            _rate_log[ip] = entries
            return False
        entries.append(now)
        _rate_log[ip] = entries
        return True


# --- 会话管理：每个 session 一个文件夹，状态存 state.json ---

def _session_dir(session_id):
    d = os.path.join(OUTPUT_FOLDER, session_id)
    os.makedirs(d, exist_ok=True)
    return d

def _state_path(session_id):
    return os.path.join(_session_dir(session_id), 'state.json')

def _load_state(session_id):
    p = _state_path(session_id)
    if not os.path.exists(p):
        return None
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)

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
    if filename in ('styles.css', 'script.js') or filename.startswith('i18n/'):
        return send_from_directory('.', filename)
    return jsonify({'error': 'Not found'}), 404


# --- 上传 + 创建会话 ---

@app.route('/api/session/create', methods=['POST'])
def session_create():
    if not _check_rate_limit():
        return jsonify({'error': '请求过于频繁，请稍后再试 (每小时最多 5 次)'}), 429

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
    session_dir = _session_dir(session_id)
    filepath = os.path.join(session_dir, f"{ts}_{safe_name}")
    # 检查磁盘剩余空间（至少需要 500MB）
    import shutil
    free_mb = shutil.disk_usage(session_dir).free / (1024 * 1024)
    if free_mb < 500:
        return jsonify({'error': '磁盘空间不足，请联系管理员清理'}), 507
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
            'tts_voice': request.form.get('tts_voice') or
                        LANGUAGES.get(request.form.get('language', DEFAULT_LANGUAGE),
                                      LANGUAGES[DEFAULT_LANGUAGE])['tts_voice']
        }

    _save_state(session_id, {
        'status': 'UPLOADED', 'session_id': session_id,
        'filename': f"{ts}_{safe_name}", 'filepath': filepath,
        'config': config, 'created_at': datetime.now().isoformat()
    })
    logger.info(f"会话创建: {session_id}")
    return jsonify({'session_id': session_id, 'status': 'UPLOADED', 'config': config})


# --- 分镜设计 ---

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

        # LLM 已按剧本节奏分配时长，不再硬编码覆盖
        for s in shots:
            s['final_duration'] = s.get('original_duration') or 5

        # 成本控制：超过上限则截断
        from config import MAX_SHOTS_FOR_COST, MAX_SHOT_DURATION, COST_PER_IMAGE, COST_PER_VIDEO_SEC
        if len(shots) > MAX_SHOTS_FOR_COST:
            logger.warning(f"镜头数 {len(shots)} 超过成本上限 {MAX_SHOTS_FOR_COST}，截断")
            shots = shots[:MAX_SHOTS_FOR_COST]
        for s in shots:
            if s.get('final_duration', 5) > MAX_SHOT_DURATION:
                s['final_duration'] = MAX_SHOT_DURATION

        total_sec = sum(s.get('final_duration', 5) for s in shots)
        est_cost = len(shots) * COST_PER_IMAGE + total_sec * COST_PER_VIDEO_SEC
        state['estimated_cost_usd'] = round(est_cost, 2)
        logger.info(f"预估成本: ${est_cost:.2f} ({len(shots)}镜 {total_sec}秒)")

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
            'estimated_cost_usd': state.get('estimated_cost_usd', 0),
            'shots_preview': [{'id': s['id'], 'duration': s.get('final_duration', 5),
                               'camera': s.get('camera_hint', ''), 'mood': s.get('mood', ''),
                               'location': s.get('location', ''),
                               'action': s.get('action_summary', '')[:60]}
                              for s in shots]
        })
    except Exception as e:
        logger.error(f"分镜失败: {e}", exc_info=True)
        return jsonify({'error': '分镜设计失败，请重试'}), 500


# --- Prompt 生成 ---

@app.route('/api/session/<session_id>/prompts', methods=['POST'])
def session_prompts(session_id):
    state = _load_state(session_id)
    if not state or 'shots' not in state:
        return jsonify({'error': '请先完成分镜设计'}), 400

    try:
        prompts = generate_prompts(state['shots'], state['config'],
                                    character_summary=state.get('character_summary'))
        prompt_map = {p['shot_id']: p for p in prompts}
        for shot in state['shots']:
            p = prompt_map.get(shot['id'])
            if p:
                shot['image_prompt'] = p['image_prompt']
                shot['video_prompt'] = p['video_prompt']
            else:
                logger.warning(f"镜头 {shot['id']} 未收到 LLM prompt，使用默认值")

        _update_state(session_id, 'PROMPTS_READY', shots=state['shots'])
        logger.info(f"Prompt 完成: {len(state['shots'])}镜头")
        return jsonify({'status': 'PROMPTS_READY', 'shot_count': len(state['shots'])})
    except Exception as e:
        logger.error(f"Prompt 失败: {e}", exc_info=True)
        return jsonify({'error': 'Prompt生成失败，请重试'}), 500


# --- 图片生成 (Seedream) ---

@app.route('/api/session/<session_id>/images', methods=['POST'])
def session_images(session_id):
    state = _load_state(session_id)
    if not state or 'shots' not in state:
        return jsonify({'error': '请先完成 Prompt 生成'}), 400

    model_config = get_model_config('seedream')
    sdir = _session_dir(session_id)
    failed = []
    max_image_retries = 3
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')

    # === Phase 0: 角色设定图（每个角色一张正面全身参考图）===
    character_summary = state.get('character_summary', {})
    char_sheet_paths = {}  # {角色名: 设定图路径}
    if character_summary:
        style_prefix = STYLE_TEMPLATES.get(
            state['config'].get('style_template', '3d_cartoon'),
            STYLE_TEMPLATES['3d_cartoon']
        )['prompt']
        for char_name, appearance in character_summary.items():
            try:
                sheet_path = os.path.join(sdir, f'char_{char_name}_sheet.png')
                from services.image_generator import generate_character_sheet
                generate_character_sheet(model_config, char_name, appearance,
                                         style_prefix, state['config']['resolution'],
                                         sheet_path)
                if os.path.exists(sheet_path) and os.path.getsize(sheet_path) > 0:
                    char_sheet_paths[char_name] = sheet_path
                    logger.info(f"  角色设定图: {char_name} → char_{char_name}_sheet.png")
            except Exception as e:
                logger.warning(f"  角色设定图 {char_name} 失败: {e}")

        # 将设定图视觉锚点注入每个镜头的 image_prompt
        if char_sheet_paths:
            for shot in state['shots']:
                for char_info in shot.get('characters', []):
                    cname = char_info.get('name', '')
                    if cname in char_sheet_paths:
                        # 在 prompt 末尾追加角色一致性锚点
                        anchor = (f" CRITICAL CONSISTENCY: Characters in this scene must match "
                                  f"their character reference sheet. Same face, same clothing, "
                                  f"same proportions as the reference.")
                        if 'image_prompt' in shot and anchor not in shot['image_prompt']:
                            shot['image_prompt'] = shot['image_prompt'].rstrip() + anchor

    state['char_sheet_paths'] = char_sheet_paths

    # === 同场景首帧复用策略 ===
    # 同一 location 的镜头共享第一镜的图片（仅运镜不同），保持角色外观一致
    # 排除无角色的抽象镜头（图标动画/黑屏/纯字幕），这些各出各图
    ABSTRACT_LOCATIONS = {'图标动画场景', '抽象示意图场景', '黑屏', '数据流动画'}
    scene_groups = {}  # {location: [shot, shot, ...]}
    for s in state['shots']:
        loc = s.get('location', '')
        if loc in ABSTRACT_LOCATIONS:
            continue  # 抽象镜头独立出图
        scene_groups.setdefault(loc, []).append(s)

    # 收集中每个 scene 的第一镜 + 所有抽象镜头 → 需要实际生成的镜头
    lead_shots = []  # 每个场景的第一镜
    follow_shots = []  # 同场景的后续镜（复用首帧）
    seen_locs = set()
    for loc, group in scene_groups.items():
        if loc in seen_locs:
            continue
        seen_locs.add(loc)
        if group:
            lead_shots.append(group[0])
            for s in group[1:]:
                follow_shots.append((s, group[0]['id']))

    # 抽象镜头独立生成
    abstract_shots = [s for s in state['shots']
                      if s.get('location', '') in ABSTRACT_LOCATIONS and s.get('image_prompt')]
    valid_shots = lead_shots + abstract_shots

    if not valid_shots:
        return jsonify({'error': '没有可用的 image_prompt'}), 400

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
        import shutil
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

        # === 同场景后续镜：复制首帧图片 ===
        reused = 0
        for follow, lead_id in follow_shots:
            lead_path = None
            for s in state['shots']:
                if s['id'] == lead_id:
                    lead_path = s.get('image_path')
                    break
            if lead_path and os.path.exists(lead_path):
                follow_path = os.path.join(sdir, f"{ts}_{follow['id']}_kf.png")
                shutil.copy2(lead_path, follow_path)
                follow['image_path'] = follow_path
                follow['image_reused_from'] = lead_id  # 标记来源
                reused += 1
                logger.info(f"  {follow['id']} 复用 {lead_id} 关键帧（同场景）")

        # === 动作关键帧：有 peak_prompts 的镜头生成额外帧 ===
        peak_count = 0
        for shot in state['shots']:
            peaks = shot.get('peak_prompts', [])
            if not peaks or not shot.get('image_path'):
                continue
            for pi, peak in enumerate(peaks):
                try:
                    peak_path = os.path.join(sdir, f"{ts}_{shot['id']}_peak{pi}_frame.png")
                    generate_image(model_config, peak.get('image_prompt', ''),
                                  state['config']['resolution'], peak_path)
                    if os.path.exists(peak_path) and os.path.getsize(peak_path) > 0:
                        peak['frame_path'] = peak_path
                        peak_count += 1
                        logger.info(f"  {shot['id']} 动作帧{pi}: {peak.get('label','')}")
                except Exception as e:
                    logger.warning(f"  {shot['id']} 动作帧{pi} 失败: {e}")

        scene_count = len(scene_groups)
        _update_state(session_id, 'IMAGES_GENERATED', shots=state['shots'],
                       failed_shots=failed, scene_groups=list(scene_groups.keys()))
        logger.info(f"图片: {len(valid_shots)-len(failed)}/{len(valid_shots)} 成功, "
                     f"{scene_count}场景, {reused}镜复用首帧, {peak_count}动作帧")
        return jsonify({'status': 'IMAGES_GENERATED', 'total': len(valid_shots),
                       'failed': failed, 'scenes': scene_count, 'reused': reused})
    except Exception as e:
        logger.error(f"图片失败: {e}", exc_info=True)
        return jsonify({'error': '图片生成失败，请重试'}), 500


# --- 视频生成 (Seedance) ---

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
    action_peak_chains = []  # 有动作峰值的镜头，需要首尾帧链式生成
    for i, shot in enumerate(all_shots):
        if not shot.get('image_path'):
            failed.append(shot['id'])
            continue
        ts_v = datetime.now().strftime('%Y%m%d_%H%M%S')
        out = os.path.join(sdir, f"{ts_v}_{shot['id']}.mp4")

        # 检查是否有可用的动作峰值帧
        peaks = shot.get('peak_prompts', [])
        valid_peaks = [p for p in peaks if p.get('frame_path') and os.path.exists(p['frame_path'])]

        if valid_peaks:
            # 有动作峰值：构建首尾帧链 main→peak[0]→peak[1]→...
            action_peak_chains.append((shot, out, ts_v, valid_peaks))
            # 仍然加入 valid_shots 做正常生成（动作链在后续单独处理）
            valid_shots.append((shot, out, None))
        else:
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
        from services.pipeline import (
            image_to_base64_dataurl, build_seedance_payload,
            create_seedance_task, poll_seedance_task, download_video,
        )
        api_key = model_config['api_key']
        api_url = model_config['api_url']
        model_name = model_config['model']
        result_lock = threading.Lock()

        def _submit_and_poll(shot_entry):
            """提交任务 → 立即轮询，一线到底，不拆两阶段"""
            shot, out, last = shot_entry
            try:
                payload = build_seedance_payload(
                    model=model_name,
                    first_frame_path=shot['image_path'],
                    video_prompt=shot.get('video_prompt', ''),
                    duration=shot.get('final_duration', 5),
                    resolution=video_quality,
                    seed_session_id=f"{session_id}_{shot['id']}",
                    last_frame_path=last,
                )
                tid = create_seedance_task(api_url, api_key, payload)
                if not tid:
                    with result_lock:
                        failed.append(shot['id'])
                    return

                poll_result = poll_seedance_task(api_url, api_key, tid)
                if poll_result['status'] == 'succeeded' and poll_result['video_url']:
                    if download_video(poll_result['video_url'], out):
                        shot['video_path'] = out
                        logger.info(f"  {shot['id']} 视频完成")
                        return
                with result_lock:
                    failed.append(shot['id'])
            except Exception as e:
                logger.warning(f"  {shot['id']} 异常: {e}")
                with result_lock:
                    failed.append(shot['id'])

        # 20 线程并行：提交+轮询一步到位
        MAX_VIDEO_WORKERS = 20
        with ThreadPoolExecutor(max_workers=min(len(valid_shots), MAX_VIDEO_WORKERS)) as ex:
            list(ex.map(_submit_and_poll, valid_shots))

        # === 动作峰值链 — 并行化 ===
        if action_peak_chains:
            import subprocess as _sp
            def _norm(p):
                return os.path.abspath(p).replace('\\', '/')

            def _gen_peak_chain(shot, out, ts_v, peaks):
                """每个峰值段也是提交→立即轮询"""
                chain_clips = []
                prev_frame = shot['image_path']
                for pi, peak in enumerate(peaks):
                    try:
                        peak_out = os.path.join(sdir, f"{ts_v}_{shot['id']}_peak{pi}.mp4")
                        payload = build_seedance_payload(
                            model=model_name,
                            first_frame_path=prev_frame,
                            video_prompt=peak.get('video_prompt', shot.get('video_prompt', '')),
                            duration=max(2, shot.get('final_duration', 5) // len(peaks)),
                            resolution=video_quality,
                            seed_session_id=f"{session_id}_{shot['id']}_p{pi}",
                            last_frame_path=peak['frame_path'],
                        )
                        tid = create_seedance_task(api_url, api_key, payload)
                        if not tid:
                            continue
                        poll_result = poll_seedance_task(api_url, api_key, tid)
                        if poll_result['status'] == 'succeeded' and poll_result['video_url']:
                            if download_video(poll_result['video_url'], peak_out):
                                chain_clips.append(peak_out)
                                logger.info(f"  {shot['id']} peak{pi} 完成")
                        prev_frame = peak['frame_path']
                    except Exception as e:
                        logger.warning(f"  {shot['id']} peak{pi} 失败: {e}")

                if chain_clips:
                    concat_list = os.path.join(sdir, f"{ts_v}_{shot['id']}_concat.txt")
                    with open(concat_list, 'w') as cf:
                        for cp in chain_clips:
                            cf.write(f"file '{_norm(cp)}'\n")
                    r_cat = _sp.run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                                    '-i', _norm(concat_list), '-c', 'copy', _norm(out)],
                                   capture_output=True, text=True)
                    if r_cat.returncode == 0:
                        shot['video_path'] = out
                        shot['peak_frames_used'] = len(chain_clips)
                        logger.info(f"  {shot['id']} 动作链 {len(chain_clips)}段 完成")
                    else:
                        logger.warning(f"  {shot['id']} 拼接失败: {r_cat.stderr[:200]}")
                return shot

            # 所有动作链并行
            peak_futures = []
            with ThreadPoolExecutor(max_workers=min(len(action_peak_chains), 8)) as ex:
                for shot, out, ts_v, peaks in action_peak_chains:
                    peak_futures.append(ex.submit(_gen_peak_chain, shot, out, ts_v, peaks))
                for f in as_completed(peak_futures):
                    try:
                        f.result()
                    except Exception as e:
                        logger.warning(f"动作链异常: {e}")

        _update_state(session_id, 'VIDEOS_GENERATED', shots=state['shots'],
                       failed_shots=failed)
        return jsonify({'status': 'VIDEOS_GENERATED', 'total': len(all_shots),
                       'failed': failed})
    except Exception as e:
        logger.error(f"视频失败: {e}", exc_info=True)
        return jsonify({'error': '视频生成失败，请重试'}), 500


# --- 配音 + 合成 ---

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
        out = compose_video(sdir, state['shots'], state['config'],
                            global_tone=state.get('global_tone', ''))
        _update_state(session_id, 'COMPOSED', final_video=out)
        logger.info(f"合成完成: {out}")
        return jsonify({'status': 'COMPOSED',
                       'videoUrl': f'/api/session/{session_id}/download'})
    except Exception as e:
        logger.error(f"合成失败: {e}", exc_info=True)
        return jsonify({'error': '视频合成失败，请重试'}), 500


# --- 重试 / 下载 / 状态 ---

@app.route('/api/session/<session_id>/retry-failed', methods=['POST'])
def session_retry_failed(session_id):
    state = _load_state(session_id)
    if not state: return jsonify({'error': 'Session 不存在'}), 404

    # 支持单镜重试: ?shot_id=SC03
    target_shot = request.args.get('shot_id', '')
    if target_shot:
        failed_shots = [target_shot] if any(
            s['id'] == target_shot for s in state.get('shots', [])
        ) else []
    else:
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
                    if ok:
                        retried += 1
                    else:
                        still.append(sid)

    elif status == 'COMPOSED':
        # 重试合成（BGM/TTS/拼接可能有瞬时错误）
        try:
            for shot in state['shots']:
                if shot.get('narration') and shot['narration'] != '无' and not shot.get('narration_path'):
                    path = os.path.join(sdir, f"{shot['id']}_narration.mp3")
                    try:
                        generate_narration(shot['narration'], path,
                                          voice=state['config'].get('tts_voice', 'zh-CN-XiaoxiaoNeural'))
                        shot['narration_path'] = path
                    except Exception as e:
                        logger.warning(f"  {shot['id']} TTS重试失败: {e}")
            out = compose_video(sdir, state['shots'], state['config'],
                               global_tone=state.get('global_tone', ''))
            state['final_video'] = out
            retried = 1
        except Exception as e:
            logger.error(f"合成重试失败: {e}")
            still.append('compose')

    _update_state(session_id, status, shots=state['shots'],
                   failed_shots=still, final_video=state.get('final_video'))
    return jsonify({'status': 'RETRIED', 'retried': retried, 'still_failed': still})


# --- 重跑流水线 ---

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
                for s in shots:
                    s['final_duration'] = s.get('original_duration') or 5
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
        logger.error('rerun 失败: {}'.format(_sanitize_error(e)))
        return jsonify({'error': _sanitize_error(e)}), 500


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

    est_cost = state.get('estimated_cost_usd', 0)
    return jsonify({
        'session_id': session_id, 'status': status, 'progress': progress,
        'step_detail': step_detail,
        'stats': {'shots_done': sum(1 for s in shots if s.get('image_path')),
                  'shots_total': total},
        'estimated_cost_usd': est_cost,
    })


# --- 剪辑趋势 API ---

@app.route('/api/trends')
def api_trends():
    """剪辑趋势查询 — Token 鉴权"""
    token = request.headers.get('X-Access-Token', '')
    if token != ACCESS_TOKEN:
        return jsonify({'error': 'Unauthorized'}), 401

    dim = request.args.get('dimension')
    limit = min(int(request.args.get('limit', 10)), 50)
    search = request.args.get('search', '').strip()

    if search:
        results = search_techniques(search, [dim] if dim else None, limit)
    else:
        results = get_trending_techniques(dim, limit)

    # 序列化 JSON 字段
    for r in results:
        if 'sample_video_ids' in r and isinstance(r['sample_video_ids'], str):
            try:
                r['sample_video_ids'] = json.loads(r['sample_video_ids'])
            except (json.JSONDecodeError, TypeError):
                pass

    return jsonify(results)


# --- Agent API ---

def _load_agent_memory(session_id):
    """加载 Agent Memory，优先新格式，兼容旧 state.json。
    返回 (mem, sdir, old_state) — 其中 mem 或 old_state 至少一个非空。"""
    sdir = _session_dir(session_id)
    mem = WorkingMemory.load(session_id, sdir)
    if mem:
        return mem, sdir, None
    old_state = _load_state(session_id)
    return None, sdir, old_state


@app.route('/api/agent/<session_id>/state', methods=['GET'])
def agent_state(session_id):
    """查询 Agent 当前记忆状态"""
    mem, sdir, old_state = _load_agent_memory(session_id)
    if not mem:
        if not old_state:
            return jsonify({'error': 'Session 不存在'}), 404
        return jsonify({
            'session_id': session_id,
            'phase': old_state.get('status', 'unknown'),
            'note': '旧版 session，请使用 /api/session/* 端点',
        })
    return jsonify({
        'session_id': session_id,
        'phase': mem.phase,
        'state': mem.get_state_for_llm(),
        'thought_history': mem.thought_history[-20:],
        'shots': [ss.to_dict() for ss in mem.shots.values()],
    })


@app.route('/api/agent/<session_id>/stream', methods=['GET'])
def agent_stream(session_id):
    """
    SSE 流式端点 — 启动 Agent 循环，实时推送思考过程。

    事件类型:
    - thinking: Agent 正在分析
    - tool_call: 调用工具
    - tool_result: 工具执行结果
    - eval: 质量评估
    - replan: 重规划
    - error: 异常
    - complete: 完成
    """
    mem, sdir, old_state = _load_agent_memory(session_id)
    if not mem:
        if not old_state:
            return jsonify({'error': 'Session 不存在，请先上传文档'}), 404

        mem = WorkingMemory(session_id, sdir, old_state.get('config', {}))
        mem.phase = 'init'
        mem.config['filepath'] = old_state.get('filepath', '')
        mem.config['filename'] = old_state.get('filename', '')
        mem.save()  # 写入 agent_state.json，不影响管线 state.json
        """SSE 生成器，在后台线程运行 Agent 并通过队列推送事件"""
        import queue
        import threading as _th
        event_queue = queue.Queue(maxsize=200)  # 有界队列防内存溢出
        stop_event = _th.Event()  # 客户端断开时通知 Agent 停止

        def on_thought(event_type, data):
            event_queue.put({'event': event_type, 'data': data})

        def run_agent():
            try:
                agent = ZhiyanAgent(mem, sdir)
                agent.run(on_thought=on_thought, stop_event=stop_event)
            except Exception as e:
                event_queue.put({'event': 'error',
                                'data': {'content': f'Agent 崩溃: {str(e)[:300]}'}})

        t = _th.Thread(target=run_agent, daemon=True)
        t.start()

        # 从队列读取事件并写入 SSE
        timeout_count = 0
        try:
            while True:
                try:
                    evt = event_queue.get(timeout=2)
                    timeout_count = 0
                    event_type = evt['event']
                    data = evt['data']
                    yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

                    if event_type == 'complete':
                        yield f"event: final_state\ndata: {json.dumps({'phase': mem.phase, 'session_id': session_id}, ensure_ascii=False)}\n\n"
                        break
                    if event_type == 'error' and 'Agent 崩溃' in str(data.get('content', '')):
                        break

                except queue.Empty:
                    timeout_count += 1
                    # 发送心跳保持连接
                    yield f": heartbeat\n\n"
                    sse_timeout = int(os.environ.get('AGENT_SSE_TIMEOUT', '60'))
                    if timeout_count > sse_timeout:
                        yield f"event: error\ndata: {json.dumps({'content': 'Agent 超时'}, ensure_ascii=False)}\n\n"
                        break

                # Agent 线程已结束且队列空
                if not t.is_alive() and event_queue.empty():
                    break
        finally:
            # 客户端断开或生成器被回收时，通知 Agent 停止
            stop_event.set()

    return app.response_class(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
            'Access-Control-Allow-Origin': '*',
        }
    )


@app.route('/api/agent/<session_id>/run', methods=['POST'])
def agent_run_sync(session_id):
    """同步运行 Agent（非流式），返回最终状态。适合调试"""
    mem, sdir, old_state = _load_agent_memory(session_id)
    if not mem:
        if not old_state:
            return jsonify({'error': 'Session 不存在'}), 404
        mem = WorkingMemory(session_id, sdir, old_state.get('config', {}))
        mem.config['filepath'] = old_state.get('filepath', '')
        mem.save()

    try:
        agent = ZhiyanAgent(mem, sdir)
        result = agent.run()
        return jsonify({
            'result': result,
            'phase': mem.phase,
            'thought_history': mem.thought_history[-30:],
        })
    except Exception as e:
        logger.error(f"Agent 同步运行失败: {e}", exc_info=True)
        return jsonify({'error': str(e)[:500]}), 500


if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    # debug 模式仅绑定 localhost，防止 Werkzeug 调试控制台暴露到公网
    host = '127.0.0.1' if debug_mode else '0.0.0.0'
    app.run(debug=debug_mode, host=host, port=5000)
