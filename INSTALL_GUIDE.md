# 安装和运行指南

## 1. 安装Python依赖

首先，确保您已经安装了Python 3.7或更高版本。然后，在项目目录下运行以下命令安装所需的依赖：

```bash
pip install -r requirements.txt
```

这将安装以下依赖：
- Flask：Web框架
- Flask-CORS：处理跨域请求
- requests：HTTP请求库
- moviepy：视频处理库
- imageio：图像处理库
- imageio-ffmpeg：视频编解码器
- python-docx：处理Word文档
- pypdf：处理PDF文档

## 2. 安装FFmpeg

MoviePy需要FFmpeg来处理视频。请按照以下步骤安装FFmpeg：

### Windows:
1. 下载FFmpeg：https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.7z
2. 解压到某个目录，例如：C:\ffmpeg
3. 将C:\ffmpeg\bin添加到系统环境变量PATH中
4. 在命令行中运行`ffmpeg -version`验证安装是否成功

### macOS:
```bash
brew install ffmpeg
```

### Linux (Ubuntu/Debian):
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

## 3. 运行项目

### 启动后端服务

在项目目录下运行：

```bash
python app.py
```

后端服务将在 `http://localhost:5000` 启动。

### 访问前端页面

有两种方法可以访问前端页面：

**方法一：直接打开**
- 直接双击 `index.html` 文件，用浏览器打开

**方法二：使用Python内置服务器**
```bash
python -m http.server 8000
```
然后在浏览器中访问 `http://localhost:8000`

## 4. 使用项目

1. **上传文档**：点击上传区域或拖拽文件上传（支持PDF、PPT、PPTX、DOC、DOCX、TXT格式）
2. **选择AI视频生成模型**：从下拉菜单中选择您偏好的AI视频生成模型（Seedance、RunwayML、Pika Labs）
3. **设置视频参数**：选择视频风格（商务、创意、简约、科技）和时长（短、中、长）
4. **生成视频**：点击"生成视频"按钮，等待视频生成完成
5. **预览与下载**：生成完成后，可以预览视频并下载

## 5. 视频生成说明

当前实现会：
1. 读取上传的文档内容（支持TXT、DOC、DOCX、PDF格式）
2. 将文档内容发送给AI模型进行处理
3. 如果AI模型返回视频URL或视频数据，直接下载或保存
4. 如果AI模型返回文本内容，使用MoviePy将文本内容转换为视频
5. 生成的视频会保存在`outputs`目录中

## 6. 常见问题

### Q1: 安装依赖时出现错误怎么办？

A: 请确保您使用的是Python 3.7或更高版本，并且有足够的权限安装包。如果遇到权限问题，可以尝试使用`--user`选项：
```bash
pip install --user -r requirements.txt
```

### Q2: FFmpeg安装失败怎么办？

A: 请确保您下载了适合您操作系统的FFmpeg版本，并正确设置了环境变量。在Windows上，您可能需要重启命令行窗口或重新登录才能使环境变量生效。

### Q3: 视频生成失败怎么办？

A: 请检查以下几点：
- 确保已正确安装所有依赖，特别是MoviePy和FFmpeg
- 查看控制台输出的错误信息
- 确保上传的文档格式受支持
- 确保有足够的磁盘空间

### Q4: 如何配置AI模型的API密钥？

A: 请参考`API_KEY_GUIDE.md`文件，了解如何获取和配置各个AI视频生成模型的API密钥。

## 7. 技术支持

如果您遇到任何问题，请查看项目的README.md文件或联系技术支持。
