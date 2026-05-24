import os
import time
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

from logger_config import setup_logger
from config import MAX_UPLOAD_SIZE, ALLOWED_DOC_EXTENSIONS, get_model_config
from services.document_parser import parse_document
from services.prompt_generator import generate_prompt
from services.video_generator import generate_video

load_dotenv()

logger = setup_logger('app')
logger.info("=" * 60)
logger.info("应用启动")
logger.info("=" * 60)

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_SIZE

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/styles.css')
def styles():
    return send_from_directory('.', 'styles.css')


@app.route('/script.js')
def script():
    return send_from_directory('.', 'script.js')


@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': '没有文件部分'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_DOC_EXTENSIONS:
        return jsonify({'error': f'不支持的文件格式: {file_ext}'}), 400

    safe_name = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    filename = f"{timestamp}_{safe_name}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    logger.info(f"文件上传成功: {filename} ({os.path.getsize(filepath)} bytes)")

    return jsonify({
        'message': '文件上传成功',
        'filename': filename,
        'filepath': filepath,
        'fileSize': os.path.getsize(filepath),
        'fileType': 'document'
    })


@app.route('/api/generate-video', methods=['POST'])
def generate_video_route():
    data = request.json
    logger.info(f"开始生成视频请求: aiModel={data.get('aiModel')}, style={data.get('videoStyle')}")

    ai_model = data.get('aiModel', 'seedance')
    video_style = data.get('videoStyle', 'business')
    video_duration = data.get('videoDuration', 'medium')
    narrator = data.get('narrator', 'female1')
    filename = data.get('filename')

    if not filename:
        return jsonify({'error': '缺少文件名'}), 400

    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': '文件不存在'}), 400

    try:
        # Phase 1: 解析文档
        logger.info("解析文档内容...")
        content = parse_document(filepath)
        logger.info(f"文档解析完成，{len(content)} 字符")

        # Phase 2: 生成 prompt
        logger.info("生成 AI 视频 prompt...")
        prompt = generate_prompt(content, video_style, video_duration, narrator)
        logger.info(f"Prompt 生成完成，{len(prompt)} 字符")

        # Phase 3: 调用 Seedance API
        model_config = get_model_config(ai_model)
        if not model_config:
            return jsonify({'error': f'不支持的 AI 模型: {ai_model}'}), 400

        video_filename = f"{os.path.splitext(filename)[0]}_{ai_model}_{int(time.time())}.mp4"
        video_filepath = os.path.join(OUTPUT_FOLDER, video_filename)

        logger.info(f"调用 {model_config['name']} 生成视频...")
        video_data = {
            'content': content,
            'style': video_style,
            'duration': video_duration,
        }
        generate_video(model_config, prompt, video_data, video_filepath)
        logger.info(f"视频生成完成: {video_filename}")

        return jsonify({
            'message': '视频生成成功',
            'videoFilename': video_filename,
            'videoUrl': f'/api/video/{video_filename}',
            'prompt': prompt
        })

    except Exception as e:
        logger.error(f"视频生成失败: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/video/<filename>', methods=['GET'])
def get_video(filename):
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': '视频不存在'}), 404
    return send_file(filepath, as_attachment=True)


app = app

if __name__ == '__main__':
    if os.environ.get('FLASK_ENV') != 'production':
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        app.run()
