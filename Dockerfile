FROM python:3.13-slim

# 系统依赖: ffmpeg (视频处理) + 中文字体 (字幕渲染)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-wqy-microhei \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 分层缓存: 依赖层 (改动少，缓存命中率高)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 应用层
COPY . .

# 运行时目录
RUN mkdir -p uploads outputs resource/bgm resource/fonts

EXPOSE 5000
CMD ["python", "app.py"]
