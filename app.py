import os
import json
import uuid
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

from logger_config import setup_logger
from config import (
    MAX_UPLOAD_SIZE, ALLOWED_DOC_EXTENSIONS, get_model_config
)
from services.document_parser import parse_document
from services.llm_service import parse_shots, generate_prompts
from services.image_generator import generate_image
from services.tts_service import generate_narration
from services.composer import compose_video

load_dotenv()

logger = setup_logger('app')
logger.info("=" * 60)
logger.info("智演助手 1.0 启动")
logger.info("=" * 60)

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_SIZE

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def _session_dir(session_id):
    d = os.path.join(OUTPUT_FOLDER, session_id)
    os.makedirs(d, exist_ok=True)
    return d


def _state_path(session_id):
    return os.path.join(_session_dir(session_id), 'state.json')


def _load_state(session_id):
    p = _state_path(session_id)
    if os.path.exists(p):
        with open(p, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def _save_state(session_id, state):
    with open(_state_path(session_id), 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _update_state(session_id, status, **kwargs):
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


# --- Session API ---
@app.route('/api/session/create', methods=['POST'])
def session_create():
    if 'file' not in request.files:
        return jsonify({'error': '没有文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_DOC_EXTENSIONS:
        return jsonify({'error': f'不支持的文件格式: {file_ext}，仅支持 .docx / .txt'}), 400

    session_id = uuid.uuid4().hex[:12]
    safe_name = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    filename = f"{timestamp}_{safe_name}"
    filepath = os.path.join(_session_dir(session_id), filename)
    file.save(filepath)

    config = {
        'style_template': request.form.get('style_template', '3d_cartoon'),
        'duration_mode': request.form.get('duration_mode', 'uniform'),
        'consistency_strategy': request.form.get('consistency_strategy', 'generic'),
        'resolution': request.form.get('resolution', '1920x1080'),
        'auto_subtitle': request.form.get('auto_subtitle', 'yes'),
        'auto_sfx': request.form.get('auto_sfx', 'no'),
        'bgm_volume': int(request.form.get('bgm_volume', 20))
    }

    _save_state(session_id, {
        'status': 'UPLOADED',
        'session_id': session_id,
        'filename': filename,
        'filepath': filepath,
        'config': config,
        'created_at': datetime.now().isoformat()
    })

    logger.info(f"Session 创建: {session_id}")
    return jsonify({'session_id': session_id, 'status': 'UPLOADED', 'config': config})


@app.route('/api/session/<session_id>/parse', methods=['POST'])
def session_parse(session_id):
    state = _load_state(session_id)
    if not state:
        return jsonify({'error': 'Session 不存在'}), 404

    try:
        content = parse_document(state['filepath'])
        shots = parse_shots(content)

        mode = state['config']['duration_mode']
        for s in shots:
            orig = s.get('original_duration')
            if mode == 'strict':
                if orig is None:
                    return jsonify({'error': f'镜头 {s["id"]} 缺少时长，但模式为严格按脚本'}), 400
                s['final_duration'] = orig
            elif mode == 'uniform':
                s['final_duration'] = 5
            else:
                s['final_duration'] = orig if orig and orig <= 8 else 8

        _update_state(session_id, 'PARSED', shots=shots)
        logger.info(f"Session {session_id}: 解析完成, {len(shots)} 个镜头")
        return jsonify({'status': 'PARSED', 'shot_count': len(shots), 'shots': shots})

    except Exception as e:
        logger.error(f"解析失败: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/session/<session_id>/prompts', methods=['POST'])
def session_prompts(session_id):
    state = _load_state(session_id)
    if not state or 'shots' not in state:
        return jsonify({'error': '请先完成文档解析'}), 400

    try:
        prompts = generate_prompts(state['shots'], state['config'])

        shots = state['shots']
        for shot in shots:
            for p in prompts:
                if p['shot_id'] == shot['id']:
                    shot['image_prompt'] = p['image_prompt']
                    shot['video_prompt'] = p['video_prompt']
                    break

        _update_state(session_id, 'PROMPTS_READY', shots=shots)
        logger.info(f"Session {session_id}: Prompt 生成完成")
        return jsonify({'status': 'PROMPTS_READY', 'shot_count': len(shots)})

    except Exception as e:
        logger.error(f"Prompt 生成失败: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/session/<session_id>/images', methods=['POST'])
def session_images(session_id):
    state = _load_state(session_id)
    if not state or 'shots' not in state:
        return jsonify({'error': '请先完成 Prompt 生成'}), 400

    model_config = get_model_config('seedream')
    resolution = state['config']['resolution']
    sdir = _session_dir(session_id)
    failed = []

    max_image_retries = 3

    try:
        for shot in state['shots']:
            for attempt in range(max_image_retries):
                try:
                    output_path = os.path.join(sdir, f"{shot['id']}_frame.png")
                    generate_image(model_config, shot.get('image_prompt', ''), resolution, output_path)
                    shot['image_path'] = output_path
                    logger.info(f"  {shot['id']}: 图片完成" + (f" (重试{attempt}次后成功)" if attempt > 0 else ""))
                    break
                except Exception as e:
                    if attempt < max_image_retries - 1:
                        logger.warning(f"  {shot['id']}: 第{attempt+1}次失败, 重试中...")
                        time.sleep(2)
                    else:
                        logger.warning(f"  {shot['id']}: 重试{max_image_retries}次全部失败 - {str(e)}")
                        failed.append(shot['id'])

        _update_state(session_id, 'IMAGES_GENERATED', shots=state['shots'], failed_shots=failed)
        return jsonify({'status': 'IMAGES_GENERATED', 'total': len(state['shots']), 'failed': failed})

    except Exception as e:
        logger.error(f"图片生成失败: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/session/<session_id>/videos', methods=['POST'])
def session_videos(session_id):
    state = _load_state(session_id)
    if not state or 'shots' not in state:
        return jsonify({'error': '请先完成图片生成'}), 400

    model_config = get_model_config('seedance')
    resolution = state['config']['resolution']
    sdir = _session_dir(session_id)
    failed = []

    # 收集有图片的镜头
    valid_shots = [(s, os.path.join(sdir, f"{s['id']}.mp4"))
                   for s in state['shots'] if s.get('image_path')]
    for s in state['shots']:
        if not s.get('image_path'):
            failed.append(s['id'])

    if not valid_shots:
        return jsonify({'error': '没有可用的关键帧图片'}), 400

    try:
        api_key = model_config.get('api_key')
        api_url = model_config['api_url']
        model = model_config['model']

        # Phase 1: 并行创建所有任务
        logger.info(f"并行创建 {len(valid_shots)} 个 Seedance 任务...")
        task_map = {}  # task_id -> (shot, output_path)

        def create_task(shot, output_path):
            import requests, base64
            res_info = __import__('config').RESOLUTIONS.get(resolution, __import__('config').RESOLUTIONS['1920x1080'])
            with open(shot['image_path'], 'rb') as f:
                b64 = base64.b64encode(f.read()).decode()
            mime_map = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}
            ext = os.path.splitext(shot['image_path'])[1].lower()
            mime = mime_map.get(ext, 'image/png')
            data_url = f"data:{mime};base64,{b64}"

            payload = {
                'model': model,
                'content': [
                    {'type': 'text', 'text': shot.get('video_prompt', '')},
                    {'type': 'image_url', 'image_url': {'url': data_url}, 'role': 'reference_image'}
                ],
                'generate_audio': True,
                'ratio': res_info['ratio'],
                'watermark': False
            }
            headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}
            r = requests.post(api_url, json=payload, headers=headers, timeout=(10, 60))
            if r.status_code == 200:
                task_id = r.json().get('id')
                if task_id:
                    return (task_id, shot, output_path)
            return (None, shot, output_path)

        with ThreadPoolExecutor(max_workers=min(len(valid_shots), 5)) as executor:
            futures = [executor.submit(create_task, s, p) for s, p in valid_shots]
            for f in as_completed(futures):
                tid, shot, output_path = f.result()
                if tid:
                    task_map[tid] = (shot, output_path)
                    logger.info(f"  {shot['id']}: 任务创建 -> {tid}")
                else:
                    failed.append(shot['id'])
                    logger.warning(f"  {shot['id']}: 任务创建失败")

        # Phase 2: 并行轮询所有任务
        if task_map:
            logger.info(f"并行轮询 {len(task_map)} 个任务...")

            def poll_and_download(tid, shot, output_path):
                import requests as req
                h = {'Authorization': f'Bearer {api_key}'}
                for _ in range(120):  # max 20 min per task
                    try:
                        r = req.get(f"{api_url}/{tid}", headers=h, timeout=30)
                        if r.status_code != 200:
                            time.sleep(10)
                            continue
                        result = r.json()
                        status = result.get('status', '').lower()
                        if status == 'succeeded':
                            video_url = result.get('content', {}).get('video_url')
                            if video_url:
                                vr = req.get(video_url, timeout=120)
                                if vr.status_code == 200:
                                    with open(output_path, 'wb') as vf:
                                        vf.write(vr.content)
                                    return (shot['id'], True)
                            return (shot['id'], False)
                        if status == 'failed':
                            return (shot['id'], False)
                        time.sleep(10)
                    except Exception:
                        time.sleep(10)
                return (shot['id'], False)

            with ThreadPoolExecutor(max_workers=min(len(task_map), 5)) as executor:
                futures = [executor.submit(poll_and_download, tid, s, p)
                           for tid, (s, p) in task_map.items()]
                for f in as_completed(futures):
                    shot_id, success = f.result()
                    if success:
                        for s in state['shots']:
                            if s['id'] == shot_id:
                                s['video_path'] = os.path.join(sdir, f"{shot_id}.mp4")
                                break
                        logger.info(f"  {shot_id}: 视频完成")
                    else:
                        failed.append(shot_id)
                        logger.warning(f"  {shot_id}: 视频失败")

        _update_state(session_id, 'VIDEOS_GENERATED', shots=state['shots'], failed_shots=failed)
        return jsonify({'status': 'VIDEOS_GENERATED', 'total': len(state['shots']), 'failed': failed})

    except Exception as e:
        logger.error(f"视频生成失败: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/session/<session_id>/compose', methods=['POST'])
def session_compose(session_id):
    state = _load_state(session_id)
    if not state or 'shots' not in state:
        return jsonify({'error': '请先完成视频生成'}), 400

    sdir = _session_dir(session_id)

    try:
        for shot in state['shots']:
            if shot.get('narration') and shot['narration'] != '无':
                try:
                    audio_path = os.path.join(sdir, f"{shot['id']}_narration.mp3")
                    generate_narration(shot['narration'], audio_path)
                    shot['narration_path'] = audio_path
                except Exception as e:
                    logger.warning(f"  {shot['id']}: TTS 失败 - {str(e)}")

        output_path = compose_video(sdir, state['shots'], state['config'])

        _update_state(session_id, 'COMPOSED', final_video=output_path)
        logger.info(f"Session {session_id}: 合成完成 -> {output_path}")
        return jsonify({
            'status': 'COMPOSED',
            'videoUrl': f'/api/session/{session_id}/download'
        })

    except Exception as e:
        logger.error(f"合成失败: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/session/<session_id>/download', methods=['GET'])
def session_download(session_id):
    state = _load_state(session_id)
    if not state or not state.get('final_video'):
        return jsonify({'error': '视频尚未合成'}), 404
    return send_file(state['final_video'], as_attachment=True, download_name='final_video.mp4')


@app.route('/api/session/<session_id>/status', methods=['GET'])
def session_status(session_id):
    state = _load_state(session_id)
    if not state:
        return jsonify({'error': 'Session 不存在'}), 404
    return jsonify({
        'session_id': session_id,
        'status': state.get('status'),
        'shot_count': len(state.get('shots', [])),
        'failed_shots': state.get('failed_shots', []),
        'config': state.get('config'),
        'created_at': state.get('created_at')
    })


app = app

if __name__ == '__main__':
    if os.environ.get('FLASK_ENV') != 'production':
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        app.run()


