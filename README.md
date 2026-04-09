# 智演助手 - AI视频生成平台

智演助手是一个基于人工智能技术的视频生成工具，帮助用户快速将文档内容转换为精美的视频。

## 功能特点

- 支持多种文档格式：PDF、PPT、PPTX、DOC、DOCX、TXT
- 集成国内免费AI视频生成模型：Seedance、RunwayML Gen-2、Pika Labs
- 多种视频风格：商务风格、创意风格、简约风格、科技风格
- 多种视频时长：短(1-2分钟)、中(3-5分钟)、长(5-10分钟)
- 实时进度显示：清晰展示视频生成进度
- 视频预览与下载：生成完成后可直接预览和下载

## 项目结构

```
simple_webpage/
├── index.html          # 前端页面
├── styles.css          # 样式表
├── script.js           # 前端脚本
├── app.py              # 后端服务
├── requirements.txt    # Python依赖
├── README.md           # 项目说明
├── uploads/            # 上传文件目录（自动创建）
└── outputs/            # 输出视频目录（自动创建）
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
        'api_key': os.environ.get('SEEDANCE_API_KEY', 'YOUR_SEEDANCE_API_KEY'),
        'model': 'ep-20240601111111-xxxxx',  # 需要替换为实际的端点ID
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
