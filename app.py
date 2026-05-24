import os
import json
import uuid
from datetime import datetime
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
from services.video_generator import generate_video
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

    try:
        for shot in state['shots']:
            try:
                output_path = os.path.join(sdir, f"{shot['id']}_frame.png")
                generate_image(model_config, shot.get('image_prompt', ''), resolution, output_path)
                shot['image_path'] = output_path
                logger.info(f"  {shot['id']}: 图片完成")
            except Exception as e:
                logger.warning(f"  {shot['id']}: 图片失败 - {str(e)}")
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

    try:
        for shot in state['shots']:
            if not shot.get('image_path'):
                failed.append(shot['id'])
                continue

            try:
                output_path = os.path.join(sdir, f"{shot['id']}.mp4")
                duration = shot.get('final_duration', 5)
                generate_video(
                    model_config,
                    shot.get('video_prompt', ''),
                    shot['image_path'],
                    duration,
                    resolution,
                    output_path
                )
                shot['video_path'] = output_path
                logger.info(f"  {shot['id']}: 视频完成")
            except Exception as e:
                logger.warning(f"  {shot['id']}: 视频失败 - {str(e)}")
                failed.append(shot['id'])

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
