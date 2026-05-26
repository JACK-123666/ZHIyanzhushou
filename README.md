# 智演助手 - AI视频生成平台

智演助手是一个基于人工智能技术的视频生成工具，帮助用户快速将文档内容转换为精美的视频。

## 功能特点

- **统一素材输入**：支持文档作为原始素材
  - 📄 **文档格式**：PDF、PPT(.pptx)、Word(.docx)、TXT
- **AI智能分析**：自动分析原始素材，提取核心内容
- **专业Prompt生成**：根据素材内容和用户要求，生成专业的AI视频生成prompt
- **多风格模板**：商务风格、创意风格、简约风格、科技风格
- **多时长选择**：短(1-2分钟)、中(3-5分钟)、长(5-10分钟)
- **AI视频生成**：集成国内免费AI视频生成模型：Seedance、RunwayML Gen-2、Pika Labs
- **实时进度显示**：清晰展示视频生成进度
- **视频预览与下载**：生成完成后可直接预览和下载

### 📌  文件格式说明

| 类型 | 支持格式 | 说明 |
|------|--------|------|
| 文档 | .docx | ✅ 完全支持 |
| 文档 | .pdf | ✅ 支持 |
| 文档 | .pptx | ✅ 支持 |
| 文档 | .txt | ✅ 支持 |

## 工作流程

1. **上传原始素材**：用户可以上传文档文件
2. **选择视频参数**：选择AI模型、视频风格、时长等参数
3. **AI分析与Prompt生成**：系统分析原始素材，生成专业的视频生成prompt
4. **视频制作**：使用生成的prompt调用AI视频生成服务
5. **预览与下载**：完成视频生成后，用户可以预览并下载

## 项目结构

```
simple_webpage/
├── app.py                  # Flask 入口 + 6步流水线路由
├── config.py               # 配置中心（密钥/模型/风格/镜头）
├── logger_config.py        # 日志系统（双文件输出 + 轮转）
├── services/
│   ├── llm_service.py      # DeepSeek V4 Pro 分镜设计 + Prompt生成
│   ├── image_generator.py  # Seedream 5.0 Lite 文生图
│   ├── composer.py         # ffmpeg 视频合成（字幕/混音/拼接）
│   ├── document_parser.py  # .txt / .docx 文档解析
│   └── tts_service.py      # Edge TTS 中文语音合成
├── index.html / script.js / styles.css  # 前端
├── api/index.py / vercel.json           # Vercel 部署
├── requirements.txt
├── uploads/                # 上传文件（gitignore）
├── outputs/                # 生成视频（gitignore）
└── logs/                   # 运行日志（gitignore）
```

## 安装与运行

### 1. 安装Python依赖

```bash
pip install -r requirements.txt
```

### 2. 配置AI模型API密钥

在`app.py`文件中，找到`AI_VIDEO_MODELS`字典，将`YOUR_*_API_KEY`替换为实际的API密钥：

```python
AI_VIDEO_MODELS = {
    'seedance': {
        'name': 'Seedance (字节跳动)',
        'api_url': 'https://ark.cn-beijing.volces.com/api/v3/chat/completions',
        'api_key': os.environ.get('SEEDANCE_API_KEY') or os.environ.get('ARK_API_KEY', ''),
        'model': 'your_deepseek_endpoint',  # 需要替换为实际的端点ID
        'description': '字节跳动旗下的AI视频生成引擎'
    },
    # ... 其他模型配置
}
```

### 3. 启动后端服务

```bash
python app.py
```

后端服务将在 `http://localhost:5000` 启动。

### 4. 访问前端页面

在浏览器中打开 `index.html` 文件，或使用以下方式：

#### 方法一：直接打开
双击 `index.html` 文件，用浏览器打开。

#### 方法二：使用Python内置服务器
```bash
python -m http.server 8000
```
然后在浏览器中访问 `http://localhost:8000`

## 使用说明

1. **上传文档**：点击上传区域或拖拽文件上传
2. **选择AI视频生成模型**：从下拉菜单中选择您偏好的AI视频生成模型
3. **设置视频参数**：选择视频风格和时长
4. **生成视频**：点击"生成视频"按钮，等待视频生成完成
5. **预览与下载**：生成完成后，可以预览视频并下载

## API接口

### 上传文件
- **接口**：`POST /api/upload`
- **参数**：`file`（文件）
- **返回**：JSON对象，包含文件名和文件路径

### 生成视频
- **接口**：`POST /api/generate-video`
- **参数**：
  - `aiModel`：AI视频生成模型（seedance、runway、pika）
  - `videoStyle`：视频风格（business、creative、minimalist、tech）
  - `videoDuration`：视频时长（short、medium、long）
  - `filename`：文件名
- **返回**：JSON对象，包含视频文件名和视频URL

### 获取视频
- **接口**：`GET /api/video/<filename>`
- **参数**：`filename`（视频文件名）
- **返回**：视频文件

## 技术栈

- **前端**：HTML5、CSS3、JavaScript
- **后端**：Python Flask
- **AI视频生成模型**：Seedance、RunwayML Gen-2、Pika Labs

## 注意事项

1. 确保已正确配置AI视频生成模型的API密钥
2. 上传文件大小限制取决于服务器配置
3. 视频生成时间取决于文档大小和AI模型响应速度
4. 当前版本为演示版本，视频生成功能为模拟实现
5. 实际部署时，请考虑添加用户认证和权限管理

## 许可证

本项目仅供学习和演示使用。
