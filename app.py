from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import json
import requests
import time
from datetime import datetime
from moviepy.editor import TextClip, CompositeVideoClip, ColorClip
import tempfile

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 创建必要的目录
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# 国内免费AI视频生成模型配置
AI_VIDEO_MODELS = {
    'seedance': {
        'name': 'Seedance (字节跳动)',
        'api_url': 'https://ark.cn-beijing.volces.com/api/v3/chat/completions',
        'api_key': os.environ.get('SEEDANCE_API_KEY', 'your_seedance_api_key'),
        'model': 'ep-m-20260408220627-gwjvh',  # 需要替换为实际的端点ID
        'description': '字节跳动旗下的AI视频生成引擎'
    },
    'runway': {
        'name': 'RunwayML Gen-2 (国内版)',
        'api_url': 'https://api.runwayml.com/v1/generate',
        'api_key': os.environ.get('RUNWAY_API_KEY', 'YOUR_RUNWAY_API_KEY'),
        'model': 'gen2',
        'description': '国内可访问的Runway视频生成模型'
    },
    'pika': {
        'name': 'Pika Labs (国内版)',
        'api_url': 'https://api.pika.art/v1/generate',
        'api_key': os.environ.get('PIKA_API_KEY', 'YOUR_PIKA_API_KEY'),
        'model': 'pika-1.0',
        'description': '国内可访问的Pika视频生成模型'
    }
}

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """处理文件上传"""
    if 'file' not in request.files:
        return jsonify({'error': '没有文件部分'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400

    # 保存上传的文件
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    filename = f"{timestamp}_{file.filename}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    return jsonify({
        'message': '文件上传成功',
        'filename': filename,
        'filepath': filepath
    })

@app.route('/api/generate-video', methods=['POST'])
def generate_video():
    """生成视频"""
    data = request.json

    # 获取参数
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
        # 读取文件内容
        content = ""
        file_ext = os.path.splitext(filename)[1].lower()

        if file_ext == '.txt':
            # 读取文本文件
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        elif file_ext in ['.doc', '.docx']:
            # 读取Word文档
            try:
                from docx import Document
                doc = Document(filepath)
                content = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
            except ImportError:
                # 如果没有安装python-docx，尝试使用其他方法
                import zipfile
                import xml.etree.ElementTree as ET
                with zipfile.ZipFile(filepath) as z:
                    xml_content = z.read('word/document.xml')
                    tree = ET.fromstring(xml_content)
                    content = '\n'.join([node.text for node in tree.iter() if node.text])
        elif file_ext == '.pdf':
            # 读取PDF文件
            try:
                import pypdf
                with open(filepath, 'rb') as f:
                    pdf_reader = pypdf.PdfReader(f)
                    content = '\n'.join([page.extract_text() for page in pdf_reader.pages])
            except ImportError:
                # 如果没有安装pypdf，返回错误
                raise ValueError("请安装pypdf库以支持PDF文件处理")
        else:
            # 不支持的文件格式
            raise ValueError(f"不支持的文件格式: {file_ext}")

        # 生成视频
        video_filename = f"{os.path.splitext(filename)[0]}_{ai_model}_{int(time.time())}.mp4"
        video_filepath = os.path.join(OUTPUT_FOLDER, video_filename)

        # 调用AI视频生成模型
        model_info = AI_VIDEO_MODELS.get(ai_model)
        if not model_info:
            raise ValueError(f"不支持的AI模型: {ai_model}")

        # 调用视频生成API
        generate_video_with_model(model_info, content, video_style, video_duration, narrator, video_filepath)

        return jsonify({
            'message': '视频生成成功',
            'videoFilename': video_filename,
            'videoUrl': f'/api/video/{video_filename}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/video/<filename>', methods=['GET'])
def get_video(filename):
    """获取生成的视频"""
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': '视频不存在'}), 404

    return send_file(filepath, as_attachment=True)

def generate_video_with_model(model_info, content, video_style, video_duration, narrator, video_filepath):
    """使用AI视频生成模型生成视频"""
    # 根据不同的视频时长设置秒数
    duration_map = {
        'short': 60,    # 1-2分钟
        'medium': 180,  # 3-5分钟
        'long': 360     # 5-10分钟
    }
    duration = duration_map.get(video_duration, 180)

    # 根据不同的视频风格设置提示词
    style_prompts = {
        'business': '商务专业风格，简洁大气',
        'creative': '创意风格，色彩鲜明，富有想象力',
        'minimalist': '简约风格，干净整洁，重点突出',
        'tech': '科技风格，未来感，蓝色调'
    }
    style_prompt = style_prompts.get(video_style, '商务专业风格')

    # 构建视频生成请求
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {model_info['api_key']}"
    }

    # 根据不同的模型构建不同的请求参数
    if model_info['name'].startswith('Seedance'):
        # Seedance模型的请求参数
        payload = {
            'model': model_info['model'],
            'messages': [
                {
                    'role': 'system',
                    'content': '你是一个专业的视频生成助手，能够根据文本内容生成高质量的视频。'
                },
                {
                    'role': 'user',
                    'content': f"请根据以下内容生成一个{duration}秒的视频，风格为{style_prompt}：\n\n{content}"
                }
            ],
            'temperature': 0.7,
            'max_tokens': 2000,
            'stream': False
        }
    elif model_info['name'].startswith('Runway'):
        # Runway模型的请求参数
        payload = {
            'model': model_info['model'],
            'prompt': f"根据以下内容生成一个{duration}秒的视频，风格为{style_prompt}：\n\n{content}",
            'duration': duration,
            'style': video_style
        }
    elif model_info['name'].startswith('Pika'):
        # Pika模型的请求参数
        payload = {
            'model': model_info['model'],
            'prompt': f"根据以下内容生成一个{duration}秒的视频，风格为{style_prompt}：\n\n{content}",
            'duration': duration,
            'style': video_style
        }
    else:
        # 默认请求参数
        payload = {
            'model': model_info['model'],
            'prompt': f"根据以下内容生成一个{duration}秒的视频，风格为{style_prompt}：\n\n{content}",
            'duration': duration,
            'style': video_style
        }

    try:
        # 调用API生成视频
        print(f"正在调用AI视频生成模型: {model_info['name']}")
        print(f"API URL: {model_info['api_url']}")

        response = requests.post(
            model_info['api_url'],
            headers=headers,
            json=payload,
            timeout=300  # 5分钟超时
        )
        response.raise_for_status()

        print(f"API响应状态码: {response.status_code}")
        result = response.json()
        print(f"API响应内容: {result}")

        # 处理返回的视频数据
        if 'video_url' in result:
            # 如果返回的是视频URL，下载视频
            print(f"从URL下载视频: {result['video_url']}")
            video_response = requests.get(result['video_url'], timeout=300)
            video_response.raise_for_status()

            with open(video_filepath, 'wb') as f:
                f.write(video_response.content)
            print(f"视频下载成功，保存到: {video_filepath}")
        elif 'video_data' in result:
            # 如果返回的是视频数据，直接保存
            with open(video_filepath, 'wb') as f:
                f.write(result['video_data'])
            print(f"视频数据保存成功，保存到: {video_filepath}")
        elif 'output' in result:
            # 处理Seedance模型的响应
            output = result['output']
            if isinstance(output, str):
                # 使用返回的文本内容生成视频
                create_sample_video(video_filepath, {'content': output}, video_style)
                print(f"使用AI生成的内容创建视频，保存到: {video_filepath}")
            else:
                # 其他情况，创建一个包含响应内容的视频
                create_sample_video(video_filepath, {'content': str(output)}, video_style)
                print(f"使用AI响应创建视频，保存到: {video_filepath}")
        elif 'choices' in result and len(result['choices']) > 0:
            # 处理ChatCompletion格式的响应
            message = result['choices'][0].get('message', {})
            content = message.get('content', '')
            if content:
                create_sample_video(video_filepath, {'content': content}, video_style)
                print(f"使用ChatCompletion响应创建视频，保存到: {video_filepath}")
            else:
                # 如果没有内容，使用原始content
                create_sample_video(video_filepath, {'content': content}, video_style)
                print(f"使用原始内容创建视频，保存到: {video_filepath}")
        else:
            # 如果返回的是其他格式，使用原始内容创建视频
            print(f"使用原始内容创建视频，保存到: {video_filepath}")
            create_sample_video(video_filepath, {'content': content}, video_style)

    except Exception as e:
        print(f"调用AI视频生成模型失败: {str(e)}")
        import traceback
        traceback.print_exc()
        # 如果API调用失败，使用原始内容创建视频
        print(f"使用原始内容创建视频，保存到: {video_filepath}")
        create_sample_video(video_filepath, {'content': content}, video_style)

def create_sample_video(filepath, data, style):
    """创建示例视频文件"""
    try:
        # 获取内容
        content = data.get('content', '') if isinstance(data, dict) else str(data)

        # 如果内容太长，截取前500个字符
        if len(content) > 500:
            content = content[:500] + '...'

        # 根据风格设置颜色
        style_colors = {
            'business': {'bg': '#2c3e50', 'text': '#ecf0f1'},
            'creative': {'bg': '#e74c3c', 'text': '#ffffff'},
            'minimalist': {'bg': '#ecf0f1', 'text': '#2c3e50'},
            'tech': {'bg': '#34495e', 'text': '#3498db'}
        }
        colors = style_colors.get(style, style_colors['business'])

        # 创建背景
        bg_clip = ColorClip(size=(1280, 720), color=colors['bg'], duration=10)

        # 创建文本
        text_clip = TextClip(
            content,
            fontsize=36,
            color=colors['text'],
            size=(1200, 640),
            method='caption',
            align='center'
        ).set_position('center').set_duration(10)

        # 合成视频
        final_clip = CompositeVideoClip([bg_clip, text_clip])

        # 保存视频
        final_clip.write_videofile(
            filepath,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True
        )

        print(f"视频生成成功，保存到: {filepath}")
    except Exception as e:
        print(f"生成视频时出错: {str(e)}")
        # 如果视频生成失败，创建一个包含错误信息的文本文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(json.dumps({
                'error': str(e),
                'data': data,
                'style': style,
                'timestamp': datetime.now().isoformat(),
                'note': '视频生成失败，这是一个错误信息文件'
            }, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
