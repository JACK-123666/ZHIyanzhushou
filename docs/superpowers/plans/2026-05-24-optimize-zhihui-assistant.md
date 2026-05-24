# 智演助手优化 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 1122 行单体 app.py 拆分为 config/services 分层架构，删除无用文件，加固安全性，优化前端。

**Architecture:** Flask 入口（app.py）→ 服务层（document_parser / prompt_generator / video_generator）→ 外部 API（Seedance）。配置集中在 config.py，所有密钥从环境变量读取。

**Tech Stack:** Python 3.13, Flask 2.3.3, python-docx, pypdf, python-pptx, requests

---

### Task 0: 删除无用文件

**Files:**
- Delete: 多个文件（见下方列表）

- [ ] **Step 1: 删除 Node 相关文件**

```bash
rm -rf "d:/PYTHON/simple_webpage/node_modules"
rm "d:/PYTHON/simple_webpage/package.json"
rm "d:/PYTHON/simple_webpage/package-lock.json"
```

- [ ] **Step 2: 删除 PPT 生成脚本**

```bash
rm "d:/PYTHON/simple_webpage/create_ppt.js"
rm "d:/PYTHON/simple_webpage/create_ppt_v2.js"
```

- [ ] **Step 3: 删除测试残留文件**

```bash
rm "d:/PYTHON/simple_webpage/test_video_generation.py"
rm "d:/PYTHON/simple_webpage/test_output.mp4"
```

- [ ] **Step 4: 删除过时文档**

```bash
rm "d:/PYTHON/simple_webpage/API_KEY_GUIDE.md"
rm "d:/PYTHON/simple_webpage/DEPLOYMENT.md"
rm "d:/PYTHON/simple_webpage/GITHUB_GUIDE.md"
rm "d:/PYTHON/simple_webpage/GITHUB_PAGES_DEPLOYMENT.md"
rm "d:/PYTHON/simple_webpage/INSTALL_GUIDE.md"
rm "d:/PYTHON/simple_webpage/使用指南.md"
```

- [ ] **Step 5: 清理 outputs 和 uploads 目录（保留目录本身）**

```bash
rm -f "d:/PYTHON/simple_webpage/outputs/"*.mp4
rm -f "d:/PYTHON/simple_webpage/uploads/"*
```

- [ ] **Step 6: 提交**

```bash
cd "d:/PYTHON/simple_webpage"
git add -A
git commit -m "$(cat <<'EOF'
chore: 删除无用文件（PPT脚本、Node依赖、测试残留、过时文档、历史产物）
EOF
)"
```

---

### Task 1: 修复 .gitignore 和安全配置

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: 重写 .gitignore**

```bash
cat > "d:/PYTHON/simple_webpage/.gitignore" << 'EOF'
# 环境变量（含密钥）
.env

# Python
__pycache__/
*.pyc
*.pyo

# 运行时目录
uploads/
outputs/
logs/

# IDE
.vscode/
.idea/

# Vercel
.vercel

# OS
.DS_Store
Thumbs.db
EOF
```

- [ ] **Step 2: 确认 .env 已在 .gitignore 中，从 git 跟踪中移除**

```bash
cd "d:/PYTHON/simple_webpage"
git rm --cached .env 2>/dev/null || true
```

- [ ] **Step 3: 更新 .env.example 为干净模板**

Write `d:\PYTHON\simple_webpage\.env.example`:

```
SEEDANCE_API_KEY=your_api_key_here
SEEDANCE_ENDPOINT=your_endpoint_id_here
FLASK_ENV=development
```

- [ ] **Step 4: 提交**

```bash
cd "d:/PYTHON/simple_webpage"
git add .gitignore .env.example
git commit -m "$(cat <<'EOF'
chore: 补全 .gitignore，清理 .env 追踪，更新 .env.example 模板
EOF
)"
```

---

### Task 2: 创建 config.py

**Files:**
- Create: `config.py`

- [ ] **Step 1: 创建 config.py**

Write `d:\PYTHON\simple_webpage\config.py`:

```python
import os
from dotenv import load_dotenv

load_dotenv()

# --- 密钥（仅从环境变量读取，无硬编码） ---
SEEDANCE_API_KEY = os.environ.get('SEEDANCE_API_KEY', '')
SEEDANCE_ENDPOINT = os.environ.get('SEEDANCE_ENDPOINT', '')

# --- 上传限制 ---
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB
MAX_CONTENT_LENGTH = 100000  # 文档解析字符上限

# --- 允许的文件扩展名 ---
ALLOWED_DOC_EXTENSIONS = {'.pdf', '.pptx', '.docx', '.txt'}

# --- AI 模型配置 ---
AI_VIDEO_MODELS = {
    'seedance': {
        'name': 'Seedance 1.5 Pro (字节跳动)',
        'api_url': 'https://ark.cn-beijing.volces.com/api/v3/chat/completions',
        'video_api_url': 'https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks',
        'api_key': SEEDANCE_API_KEY,
        'model': SEEDANCE_ENDPOINT,
        'video_model': 'seedance-1.5-pro',
        'description': '字节跳动 Seedance 1.5 Pro AI视频生成引擎'
    },
    'runway': {
        'name': 'RunwayML Gen-2',
        'api_url': 'https://api.runwayml.com/v1/generate',
        'api_key': os.environ.get('RUNWAY_API_KEY', ''),
        'model': 'gen2',
        'description': 'RunwayML 视频生成模型'
    },
    'pika': {
        'name': 'Pika Labs',
        'api_url': 'https://api.pika.art/v1/generate',
        'api_key': os.environ.get('PIKA_API_KEY', ''),
        'model': 'pika-1.0',
        'description': 'Pika Labs 视频生成模型'
    }
}

# --- 视频风格映射 ---
STYLE_DESCRIPTIONS = {
    'business': '专业商务风格，简洁大方，适合企业文档介绍，使用蓝色和灰色调，清晰的排版',
    'creative': '创意艺术风格，充满活力，适合创意文档，使用鲜艳色彩和动态效果',
    'minimalist': '极简风格，干净整洁，突出核心信息，使用白色背景和黑色文字，留白充足',
    'tech': '科技风格，现代感强，适合技术文档，使用深色背景和霓虹色点缀'
}

# --- 时长映射 ---
DURATION_MAPS = {
    'short': {'seconds': 30, 'scenes': 2, 'desc': '30秒短视频', 'words_per_scene': 15},
    'medium': {'seconds': 60, 'scenes': 3, 'desc': '60秒中等视频', 'words_per_scene': 20},
    'long': {'seconds': 100, 'scenes': 4, 'desc': '100秒长视频', 'words_per_scene': 25}
}

# --- Seedance 时长映射 ---
SEEDANCE_DURATION_MAP = {'short': 5, 'medium': 8, 'long': 12}

# --- 旁白描述 ---
NARRATOR_DESCRIPTIONS = {
    'female1': '温柔专业的女声，语速适中，适合商务文档介绍',
    'female2': '活泼亲切的女声，语速稍快，适合创意内容',
    'male1': '沉稳权威的男声，语速稳健，适合技术文档',
    'male2': '温和友好的男声，语速适中，适合通用场景'
}

# --- Seedance 风格 prompt ---
SEEDANCE_STYLE_PROMPTS = {
    'business': '专业商务风格，简洁大方，适合企业宣传',
    'creative': '创意艺术风格，充满想象力，视觉冲击力强',
    'minimalist': '极简风格，干净简约，突出核心信息',
    'tech': '科技感风格，现代科技元素，未来感设计'
}


def get_model_config(model_key):
    """获取模型配置，不存在则返回 None"""
    return AI_VIDEO_MODELS.get(model_key)
```

- [ ] **Step 2: 验证语法**

```bash
cd "d:/PYTHON/simple_webpage"
python -c "import config; print('config OK, models:', list(config.AI_VIDEO_MODELS.keys()))"
```

Expected output: `config OK, models: ['seedance', 'runway', 'pika']`

- [ ] **Step 3: 提交**

```bash
cd "d:/PYTHON/simple_webpage"
git add config.py
git commit -m "feat: 添加 config.py，集中管理密钥、模型配置、常量和风格映射"
```

---

### Task 3: 创建 services/document_parser.py

**Files:**
- Create: `services/__init__.py`
- Create: `services/document_parser.py`

- [ ] **Step 1: 创建 services/__init__.py**

Write `d:\PYTHON\simple_webpage\services\__init__.py`:

```python
```

- [ ] **Step 2: 创建 document_parser.py**

Write `d:\PYTHON\simple_webpage\services\document_parser.py`:

```python
import os
from config import MAX_CONTENT_LENGTH


def parse_document(filepath):
    """解析文档，根据扩展名分发到对应解析器"""
    file_ext = os.path.splitext(filepath)[1].lower()
    file_size = os.path.getsize(filepath)

    content = _parse_by_extension(filepath, file_ext, file_size)

    if len(content) > MAX_CONTENT_LENGTH:
        content = content[:MAX_CONTENT_LENGTH]

    return content


def _parse_by_extension(filepath, file_ext, file_size):
    if file_ext == '.txt':
        return _parse_txt(filepath)
    elif file_ext == '.docx':
        return _parse_docx(filepath)
    elif file_ext == '.pdf':
        return _parse_pdf(filepath)
    elif file_ext == '.pptx':
        return _parse_pptx(filepath)
    else:
        raise ValueError(f"不支持的文件格式: {file_ext}")


def _parse_txt(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read(MAX_CONTENT_LENGTH)


def _parse_docx(filepath):
    from docx import Document
    doc = Document(filepath)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    max_paragraphs = 500
    if len(paragraphs) > max_paragraphs:
        paragraphs = paragraphs[:max_paragraphs]
    return '\n'.join(paragraphs)


def _parse_pdf(filepath):
    import pypdf
    with open(filepath, 'rb') as f:
        reader = pypdf.PdfReader(f)
        max_pages = min(len(reader.pages), 50)
        pages = reader.pages[:max_pages]
        return '\n'.join([page.extract_text() or '' for page in pages])


def _parse_pptx(filepath):
    from pptx import Presentation
    presentation = Presentation(filepath)
    slides_text = []
    max_slides = min(len(presentation.slides), 50)
    slides = list(presentation.slides)[:max_slides]
    for slide in slides:
        for shape in slide.shapes:
            if hasattr(shape, 'text') and shape.text.strip():
                slides_text.append(shape.text.strip())
    return '\n'.join(slides_text)
```

- [ ] **Step 3: 验证语法**

```bash
cd "d:/PYTHON/simple_webpage"
python -c "from services.document_parser import parse_document; print('parser OK')"
```

Expected output: `parser OK`

- [ ] **Step 4: 提交**

```bash
cd "d:/PYTHON/simple_webpage"
git add services/__init__.py services/document_parser.py
git commit -m "feat: 添加 document_parser 服务，支持 TXT/DOCX/PDF/PPTX 解析"
```

---

### Task 4: 创建 services/prompt_generator.py

**Files:**
- Create: `services/prompt_generator.py`

- [ ] **Step 1: 创建 prompt_generator.py**

Write `d:\PYTHON\simple_webpage\services\prompt_generator.py`:

```python
from config import STYLE_DESCRIPTIONS, DURATION_MAPS, NARRATOR_DESCRIPTIONS

MAX_KEY_POINTS = 8
MAX_POINTS_PER_SCENE = 2


def generate_prompt(content, video_style, video_duration, narrator):
    """根据文档内容生成 AI 视频 prompt"""
    style_desc = STYLE_DESCRIPTIONS.get(video_style, STYLE_DESCRIPTIONS['business'])
    duration_info = DURATION_MAPS.get(video_duration, DURATION_MAPS['medium'])
    narrator_desc = NARRATOR_DESCRIPTIONS.get(narrator, NARRATOR_DESCRIPTIONS['female1'])

    content_lines = content.strip().split('\n')

    structure = _analyze_document_structure(content_lines)
    document_title = structure['title']
    key_points = structure['key_points']

    selected_points = _select_content_for_duration(
        key_points, duration_info['scenes'], duration_info['words_per_scene']
    )

    scene_descriptions = _build_scene_descriptions(
        document_title, selected_points, style_desc, duration_info
    )

    return f"""【文档介绍视频生成】

视频主题：{document_title}

【场景设计】
{scene_descriptions}

【视觉风格】
{style_desc}

【配音要求】
{narrator_desc}

【技术规格】
- 总时长：{duration_info['desc']}
- 场景数量：{duration_info['scenes']}个
- 每个场景约{duration_info['seconds'] // duration_info['scenes']}秒
- 文字叠加：清晰易读，突出关键信息
- 转场效果：平滑自然的场景切换
- 背景音乐：轻柔的背景音，不干扰配音

【内容要求】
- 简洁明了，突出文档核心价值
- 每个场景聚焦一个主要观点
- 使用图表、图标等视觉元素辅助说明
- 保持一致的视觉风格和配色
- 确保信息传达清晰准确"""


def _analyze_document_structure(content_lines):
    """智能分析文档结构：提取标题、要点、摘要"""
    structure = {'title': '文档介绍', 'key_points': [], 'summary': '', 'sections': []}

    for line in content_lines:
        if line.strip() and len(line.strip()) > 5:
            structure['title'] = line.strip()
            break

    for line in content_lines:
        line = line.strip()
        if line and len(line) > 10:
            if any(marker in line[:3] for marker in ['•', '-', '*', '1.', '2.', '3.']):
                structure['key_points'].append(line)
            elif len(structure['key_points']) < MAX_KEY_POINTS:
                structure['key_points'].append(line)

    if structure['key_points']:
        structure['summary'] = ' '.join(structure['key_points'][:3])

    return structure


def _select_content_for_duration(key_points, num_scenes, words_per_scene):
    """根据视频时长选择合适的内容量"""
    if not key_points:
        return []

    selected = []
    points_per_scene = max(1, len(key_points) // num_scenes)

    for i in range(num_scenes):
        start_idx = i * points_per_scene
        end_idx = start_idx + points_per_scene
        if start_idx < len(key_points):
            scene_points = key_points[start_idx:end_idx]
            if scene_points:
                combined = ' '.join(scene_points[:MAX_POINTS_PER_SCENE])
                selected.append(combined)

    while len(selected) < num_scenes and len(selected) < len(key_points):
        selected.append(key_points[len(selected)])

    return selected[:num_scenes]


def _build_scene_descriptions(document_title, selected_points, style_desc, duration_info):
    """构建分场景描述"""
    scenes = []
    scene_duration = duration_info['seconds'] // duration_info['scenes']
    style_parts = style_desc.split('，')
    style_keyword = style_parts[0] if style_parts else '专业'
    font_keyword = style_parts[1] if len(style_parts) > 1 else '专业'

    # 场景1：开场
    scenes.append(f"""场景1（开场，{scene_duration}秒）：
- 画面：文档标题"{document_title}"以大字体居中显示
- 背景：{style_keyword}的渐变背景
- 动画：标题从下方淡入，配合光效
- 文字：标题文字清晰，使用{font_keyword}字体
- 配音：介绍文档主题和目的（约{scene_duration * 3}字）""")

    # 场景2-N：核心内容
    for i, point in enumerate(selected_points, 2):
        if i > duration_info['scenes']:
            break
        scenes.append(f"""场景{i}（内容展示，{scene_duration}秒）：
- 画面：展示要点内容"{point[:30]}..."
- 布局：左侧文字，右侧配图或图标
- 动画：文字逐行显示，配合图标动画
- 颜色：使用{style_keyword}配色
- 配音：详细说明要点内容（约{scene_duration * 3}字）""")

    # 结尾场景
    scenes.append(f"""场景{len(scenes) + 1}（结尾，{scene_duration}秒）：
- 画面：文档标题再次出现，下方显示"谢谢观看"
- 背景：与开场呼应的渐变效果
- 动画：标题和文字同时淡入
- 文字：简洁明了，突出重点
- 配音：总结文档价值，感谢观看（约{scene_duration * 3}字）""")

    return '\n\n'.join(scenes)
```

- [ ] **Step 2: 验证语法**

```bash
cd "d:/PYTHON/simple_webpage"
python -c "from services.prompt_generator import generate_prompt; p = generate_prompt('测试内容\n要点1\n要点2', 'business', 'short', 'female1'); print('prompt OK, length:', len(p))"
```

Expected: `prompt OK, length: <number>`

- [ ] **Step 3: 提交**

```bash
cd "d:/PYTHON/simple_webpage"
git add services/prompt_generator.py
git commit -m "feat: 添加 prompt_generator 服务，文档结构分析 + AI prompt 生成"
```

---

### Task 5: 创建 services/video_generator.py

**Files:**
- Create: `services/video_generator.py`

- [ ] **Step 1: 创建 video_generator.py**

Write `d:\PYTHON\simple_webpage\services\video_generator.py`:

```python
import os
import time
import requests
from config import SEEDANCE_API_KEY, SEEDANCE_ENDPOINT, SEEDANCE_STYLE_PROMPTS, SEEDANCE_DURATION_MAP


def generate_video(model_config, prompt, video_data, video_filepath):
    """调用 Seedance API 生成视频：创建任务 → 轮询 → 下载"""
    api_key = model_config.get('api_key')
    video_api_url = model_config.get('video_api_url')
    endpoint = model_config.get('model')

    if not api_key or not endpoint or not video_api_url:
        raise ValueError("Seedance API 配置不完整：缺少 api_key、endpoint 或 video_api_url")

    original_content = video_data.get('content', '')
    style = video_data.get('style', 'business')
    duration = video_data.get('duration', 'medium')

    # 构建文本 prompt
    content_lines = [l.strip() for l in original_content.split('\n') if l.strip() and len(l.strip()) > 10]
    key_content = '\n'.join(content_lines[:5])

    style_desc = SEEDANCE_STYLE_PROMPTS.get(style, SEEDANCE_STYLE_PROMPTS['business'])
    video_duration = SEEDANCE_DURATION_MAP.get(duration, 8)

    final_prompt = f"{key_content}\n{style_desc}\n{prompt}"
    if len(final_prompt) > 500:
        final_prompt = final_prompt[:500]

    payload = {
        'model': endpoint,
        'content': [{
            'type': 'text',
            'text': f"{final_prompt} --duration {video_duration} --camerafixed false --watermark true"
        }]
    }

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }

    task_id = _create_task(video_api_url, headers, payload)
    if not task_id:
        raise RuntimeError("无法创建 Seedance 视频生成任务")

    video_url = _poll_task(video_api_url, headers, task_id)
    if not video_url:
        raise RuntimeError("Seedance 任务未完成或未返回视频 URL")

    _download_video(video_url, video_filepath)

    file_size = os.path.getsize(video_filepath)
    if file_size == 0:
        raise RuntimeError("下载的视频文件为空")

    return video_filepath


def _create_task(api_url, headers, payload, max_retries=3, base_delay=5, max_delay=30):
    """创建 Seedance 视频生成任务（带重试）"""
    for attempt in range(max_retries):
        try:
            response = requests.post(api_url, json=payload, headers=headers, timeout=(10, 60))

            if response.status_code == 429:
                delay = min(base_delay * (2 ** attempt) * 2, max_delay)
                time.sleep(delay)
                continue

            if 500 <= response.status_code < 600:
                if attempt < max_retries - 1:
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    time.sleep(delay)
                    continue
                return None

            if response.status_code != 200:
                return None

            result = response.json()
            task_id = result.get('id')
            if task_id:
                return task_id

            if attempt < max_retries - 1:
                delay = min(base_delay * (2 ** attempt), max_delay)
                time.sleep(delay)

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            if attempt < max_retries - 1:
                delay = min(base_delay * (2 ** attempt), max_delay)
                time.sleep(delay)

        except Exception:
            if attempt < max_retries - 1:
                delay = min(base_delay * (2 ** attempt), max_delay)
                time.sleep(delay)

    return None


def _poll_task(api_url, headers, task_id, max_attempts=30, interval=10):
    """轮询任务状态直到完成或失败"""
    for attempt in range(max_attempts):
        try:
            query_url = f"{api_url}/{task_id}"
            response = requests.get(query_url, headers=headers, timeout=30)

            if response.status_code != 200:
                time.sleep(interval)
                continue

            result = response.json()
            status = result.get('status', '').lower()

            if status == 'succeeded':
                return result.get('result', {}).get('video_url')

            if status == 'failed':
                return None

            # pending / processing / running
            time.sleep(interval)

        except (requests.exceptions.Timeout, Exception):
            time.sleep(interval)

    return None


def _download_video(video_url, filepath, max_retries=3):
    """下载视频文件（带重试）"""
    for attempt in range(max_retries):
        try:
            response = requests.get(video_url, timeout=120)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return
            if attempt < max_retries - 1:
                time.sleep(5)
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(5)

    raise RuntimeError(f"视频下载失败，已重试 {max_retries} 次")
```

- [ ] **Step 2: 验证语法**

```bash
cd "d:/PYTHON/simple_webpage"
python -c "from services.video_generator import generate_video; print('video_generator OK')"
```

Expected output: `video_generator OK`

- [ ] **Step 3: 提交**

```bash
cd "d:/PYTHON/simple_webpage"
git add services/video_generator.py
git commit -m "feat: 添加 video_generator 服务，Seedance API 任务创建/轮询/下载"
```

---

### Task 6: 重写 app.py

**Files:**
- Modify: `app.py`（完全重写）

- [ ] **Step 1: 重写 app.py**

Write `d:\PYTHON\simple_webpage\app.py`:

```python
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
```

- [ ] **Step 2: 验证 app.py 可以正确加载**

```bash
cd "d:/PYTHON/simple_webpage"
python -c "from app import app; print('app OK, routes:', [r.rule for r in app.url_map.iter_rules()])"
```

Expected output: 列出所有路由，无 import 错误

- [ ] **Step 3: 启动 Flask 并测试上传端点**

```bash
cd "d:/PYTHON/simple_webpage"
python -c "
from app import app
client = app.test_client()
# 测试无文件上传
resp = client.post('/api/upload')
assert resp.status_code == 400
print('upload test OK:', resp.get_json())
"
```

Expected: `upload test OK: {'error': '没有文件部分'}`

- [ ] **Step 4: 提交**

```bash
cd "d:/PYTHON/simple_webpage"
git add app.py
git commit -m "refactor: 重写 app.py 为精简 Flask 入口，委托给 services 层"
```

---

### Task 7: 清理 requirements.txt

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: 更新 requirements.txt**

Write `d:\PYTHON\simple_webpage\requirements.txt`:

```
flask==2.3.3
flask-cors==4.0.0
requests==2.31.0
python-docx==1.1.0
pypdf==3.17.4
werkzeug==2.3.7
python-pptx==0.6.23
python-dotenv==1.0.0
```

- [ ] **Step 2: 提交**

```bash
cd "d:/PYTHON/simple_webpage"
git add requirements.txt
git commit -m "chore: 移除无用依赖 moviepy/imageio/imageio-ffmpeg/Pillow"
```

---

### Task 8: 优化前端 script.js

**Files:**
- Modify: `script.js`
- Modify: `index.html`（添加 toast 元素）

- [ ] **Step 1: 更新 index.html 添加 toast 容器**

在 `d:\PYTHON\simple_webpage\index.html` 的 `<body>` 开头（`<nav>` 之前）添加：

```html
<div class="toast-container" id="toastContainer"></div>
```

- [ ] **Step 2: 在 styles.css 末尾添加 toast 样式**

Append to `d:\PYTHON\simple_webpage\styles.css`:

```css
/* Toast 提示 */
.toast-container {
    position: fixed;
    top: 80px;
    right: 20px;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.toast {
    background: var(--text-primary);
    color: var(--bg-white);
    padding: 12px 24px;
    border-radius: var(--radius-md);
    font-size: 0.95rem;
    font-weight: 500;
    box-shadow: var(--shadow-lg);
    animation: toastIn 0.3s ease, toastOut 0.3s ease 2.7s forwards;
    max-width: 400px;
}

.toast.error {
    background: var(--accent-color);
}

.toast.success {
    background: var(--success-color);
}

@keyframes toastIn {
    from { opacity: 0; transform: translateX(100%); }
    to { opacity: 1; transform: translateX(0); }
}

@keyframes toastOut {
    from { opacity: 1; transform: translateX(0); }
    to { opacity: 0; transform: translateX(100%); }
}
```

- [ ] **Step 3: 重写 script.js**

Write `d:\PYTHON\simple_webpage\script.js`:

```javascript
// --- 常量 ---
const ALLOWED_EXTENSIONS = ['.pdf', '.pptx', '.docx', '.txt'];
const FORMAT_SIZES = ['Bytes', 'KB', 'MB', 'GB'];

// --- Toast ---
function showToast(message, type) {
    type = type || 'info';
    var container = document.getElementById('toastContainer');
    var toast = document.createElement('div');
    toast.className = 'toast ' + type;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(function () { toast.remove(); }, 3000);
}

// --- 工具函数 ---
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    var k = 1024;
    var i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + FORMAT_SIZES[i];
}

// --- DOM 引用 ---
var uploadArea = document.getElementById('uploadArea');
var fileInput = document.getElementById('fileInput');
var fileInfo = document.getElementById('fileInfo');
var fileName = document.getElementById('fileName');
var fileSize = document.getElementById('fileSize');
var removeFileBtn = document.getElementById('removeFile');
var uploadOptions = document.getElementById('uploadOptions');
var generateButton = document.getElementById('generateButton');
var progressContainer = document.getElementById('progressContainer');
var progressFill = document.getElementById('progressFill');
var progressText = document.getElementById('progressText');
var progressPercentage = document.getElementById('progressPercentage');
var videoResult = document.getElementById('videoResult');
var resultVideo = document.getElementById('resultVideo');
var downloadButton = document.querySelector('.download-button');
var shareButton = document.querySelector('.share-button');
var newVideoButton = document.querySelector('.new-video-button');

// --- 事件绑定 ---
document.addEventListener('DOMContentLoaded', function () {
    // CTA 按钮
    var ctaButton = document.getElementById('ctaButton');
    if (ctaButton) ctaButton.addEventListener('click', scrollToUpload);

    // 平滑滚动
    document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            var target = document.querySelector(this.getAttribute('href'));
            if (target) window.scrollTo({ top: target.offsetTop - 70, behavior: 'smooth' });
        });
    });

    // 导航栏阴影
    var navbar = document.querySelector('.navbar');
    window.addEventListener('scroll', function () {
        navbar.style.boxShadow = window.scrollY > 50
            ? '0 4px 12px rgba(0, 0, 0, 0.15)'
            : '0 2px 5px rgba(0, 0, 0, 0.1)';
    });

    // 特性卡片动画
    var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

    document.querySelectorAll('.feature-card').forEach(function (card) {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(card);
    });

    // 上传区域点击
    uploadArea.addEventListener('click', function () { fileInput.click(); });

    // 拖拽上传
    uploadArea.addEventListener('dragover', function (e) {
        e.preventDefault();
        uploadArea.style.backgroundColor = 'rgba(52, 152, 219, 0.05)';
        uploadArea.style.borderColor = '#3498db';
    });
    uploadArea.addEventListener('dragleave', function (e) {
        e.preventDefault();
        uploadArea.style.backgroundColor = '';
        uploadArea.style.borderColor = '';
    });
    uploadArea.addEventListener('drop', function (e) {
        e.preventDefault();
        uploadArea.style.backgroundColor = '';
        uploadArea.style.borderColor = '';
        if (e.dataTransfer.files.length > 0) handleFile(e.dataTransfer.files[0]);
    });

    // 文件选择
    fileInput.addEventListener('change', function () {
        if (fileInput.files.length > 0) handleFile(fileInput.files[0]);
    });

    // 移除文件
    removeFileBtn.addEventListener('click', resetUpload);

    // 生成视频
    generateButton.addEventListener('click', generateVideoHandler);

    // 下载
    downloadButton.addEventListener('click', function () {
        if (!resultVideo.src) return showToast('没有可下载的视频', 'error');
        var link = document.createElement('a');
        link.href = resultVideo.src;
        link.download = 'generated_video_' + Date.now() + '.mp4';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    });

    // 分享
    shareButton.addEventListener('click', function () {
        if (!resultVideo.src) return showToast('没有可分享的视频', 'error');
        navigator.clipboard.writeText(window.location.origin + resultVideo.src)
            .then(function () { showToast('视频链接已复制到剪贴板', 'success'); })
            .catch(function () { showToast('复制失败，请手动复制链接', 'error'); });
    });

    // 生成新视频
    newVideoButton.addEventListener('click', resetAll);
});

// --- 文件处理 ---
function handleFile(file) {
    var ext = '.' + file.name.split('.').pop().toLowerCase();
    if (ALLOWED_EXTENSIONS.indexOf(ext) === -1) {
        showToast('不支持的文件格式，请上传 PDF/PPTX/DOCX/TXT', 'error');
        return;
    }
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    uploadArea.style.display = 'none';
    fileInfo.style.display = 'flex';
    uploadOptions.style.display = 'block';
    videoResult.style.display = 'none';
}

function resetUpload() {
    fileInput.value = '';
    uploadArea.style.display = 'block';
    fileInfo.style.display = 'none';
    uploadOptions.style.display = 'none';
    videoResult.style.display = 'none';
    progressContainer.style.display = 'none';
}

function resetAll() {
    resetUpload();
    for (var i = 1; i <= 4; i++) {
        var step = document.getElementById('step' + i);
        if (step) step.classList.remove('active');
    }
}

// --- 视频生成 ---
function generateVideoHandler() {
    var file = fileInput.files[0];
    if (!file) return showToast('请先选择一个文件', 'error');

    var aiModel = document.getElementById('aiModel').value;
    var videoStyle = document.getElementById('videoStyle').value;
    var videoDuration = document.getElementById('videoDuration').value;
    var narrator = document.getElementById('narrator').value;

    uploadOptions.style.display = 'none';
    progressContainer.style.display = 'block';
    updateProgress(0, '正在上传文件...');
    updateStep(1);

    var formData = new FormData();
    formData.append('file', file);

    fetch('/api/upload', { method: 'POST', body: formData })
        .then(function (res) {
            if (!res.ok) return res.json().then(function (d) { throw new Error(d.error || '上传失败'); });
            return res.json();
        })
        .then(function (uploadData) {
            updateProgress(30, '正在生成专业的AI视频prompt...');
            updateStep(2);

            return fetch('/api/generate-video', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    aiModel: aiModel,
                    videoStyle: videoStyle,
                    videoDuration: videoDuration,
                    narrator: narrator,
                    filename: uploadData.filename,
                    fileType: 'document'
                })
            });
        })
        .then(function (res) {
            if (!res.ok) return res.json().then(function (d) { throw new Error(d.error || '视频生成失败'); });
            return res.json();
        })
        .then(function (data) {
            updateProgress(100, '视频生成完成！');
            updateStep(4);

            setTimeout(function () {
                progressContainer.style.display = 'none';
                videoResult.style.display = 'block';
                resultVideo.src = data.videoUrl;
                resultVideo.load();
            }, 500);
        })
        .catch(function (err) {
            showToast('生成视频时出错：' + err.message, 'error');
            progressContainer.style.display = 'none';
            uploadOptions.style.display = 'block';
        });
}

// --- 进度条 ---
function updateProgress(percentage, text) {
    progressFill.style.width = percentage + '%';
    progressPercentage.textContent = percentage + '%';
    if (text) progressText.textContent = text;
}

function updateStep(stepNumber) {
    for (var i = 1; i <= 4; i++) {
        var step = document.getElementById('step' + i);
        if (step) step.classList.remove('active');
    }
    var current = document.getElementById('step' + stepNumber);
    if (current) current.classList.add('active');
}

// --- 滚动 ---
function scrollToUpload() {
    var section = document.querySelector('#upload');
    if (section) window.scrollTo({ top: section.offsetTop - 70, behavior: 'smooth' });
}
```

- [ ] **Step 4: 验证前端无 JS 语法错误**

用浏览器打开 `index.html`，检查控制台无 JS 报错。

- [ ] **Step 5: 提交**

```bash
cd "d:/PYTHON/simple_webpage"
git add script.js index.html styles.css
git commit -m "refactor: 前端优化 - toast 替换 alert，移除 console.log，提取常量"
```

---

### Task 9: 更新 README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 更新 README 项目结构部分**

将 README 中的项目结构一节替换为：

```
simple_webpage/
├── app.py                  # Flask 入口 + 路由
├── config.py               # 集中配置（密钥、模型、常量）
├── services/
│   ├── document_parser.py  # 文档解析（TXT/DOCX/PDF/PPTX）
│   ├── prompt_generator.py # AI 视频 prompt 生成
│   └── video_generator.py  # Seedance API 视频生成
├── logger_config.py        # 日志系统
├── index.html              # 前端页面
├── styles.css              # 样式表
├── script.js               # 前端脚本
├── requirements.txt        # Python 依赖
├── api/index.py            # Vercel Serverless 入口
├── vercel.json             # Vercel 部署配置
├── uploads/                # 上传文件目录
└── outputs/                # 输出视频目录
```

- [ ] **Step 2: 提交**

```bash
cd "d:/PYTHON/simple_webpage"
git add README.md
git commit -m "docs: 更新 README 项目结构说明"
```

---

### Task 10: 端到端验证

- [ ] **Step 1: 启动 Flask 开发服务器**

```bash
cd "d:/PYTHON/simple_webpage"
python app.py &
sleep 2
```

- [ ] **Step 2: 测试静态文件路由**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/styles.css
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/script.js
```

Expected: 全部返回 `200`

- [ ] **Step 3: 测试上传 API**

```bash
echo "测试内容：这是一个测试文档" > /tmp/test_doc.txt
curl -s -X POST -F "file=@/tmp/test_doc.txt" http://localhost:5000/api/upload
```

Expected: JSON 返回 `fileType: "document"`，`message: "文件上传成功"`

- [ ] **Step 4: 停止服务器**

```bash
kill %1 2>/dev/null || true
```

- [ ] **Step 5: 提交（如有修正）**

```bash
cd "d:/PYTHON/simple_webpage"
git status
```
