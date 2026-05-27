# Docker 部署 + 多语言支持 — 设计规格

## 目标

支持 Docker 一键部署 + 前端 4 语言 i18n + 视频生成 4 语言自适应。

## Part 1: Docker 部署

### 文件

| 文件 | 用途 |
|------|------|
| `Dockerfile` | 构建镜像：Python 3.13 + ffmpeg + 中文字体 + 依赖 |
| `docker-compose.yml` | 一键启动，挂载 outputs/uploads/.env |

### 关键决策

- 基础镜像用 `python:3.13-slim`（体积小）
- ffmpeg 和字体通过 apt 安装
- `resource/bgm/` 和 `resource/fonts/` 打包进镜像
- outputs/uploads 用 volume 挂载（不丢数据）
- 端口 5000，`restart: unless-stopped`（异常自动重启）

## Part 2: 多语言 i18n

### 支持语言：中文、English、日本語、한국어

### 文件

| 文件 | 用途 |
|------|------|
| `i18n/zh.json` | 中文翻译表 |
| `i18n/en.json` | English translation |
| `i18n/ja.json` | 日本語翻訳 |
| `i18n/ko.json` | 한국어 번역 |

### 前端改动

- `index.html`: 导航栏右侧加语言选择器（下拉），所有硬编码中文加 `data-i18n` 属性
- `script.js`: `t(key)` 翻译函数 + `setLanguage(lang)` 切换函数 + 页面初始化加载浏览器语言
- `styles.css`: 语言选择器样式

### LLM 层改动

- `services/llm_service.py`: 所有 System Prompt 加 `输出语言: {language}` 指令
- language 从 config 读取（session_create 存储）

### TTS 层改动

- `services/tts_service.py`: voice 参数从 config 读取，支持 4 种语言音色
- `index.html`: Pro 面板加 TTS 语音下拉框
- 默认值保持 zh-CN-XiaoxiaoNeural

### 字幕字体

- `resource/fonts/`: 存放字体文件
- `services/composer.py`: `_burn_subtitle` 按语言选择字体路径

| 语言 | 字体 | 路径 |
|------|------|------|
| zh | 黑体 | /Windows/Fonts/simhei.ttf |
| en | Segoe UI | /Windows/Fonts/segoeui.ttf |
| ja | MS Gothic | resource/fonts/msgothic.ttc |
| ko | Malgun Gothic | /Windows/Fonts/malgun.ttf |

Linux/Docker 环境统一用文泉驿微米黑（已打包进 Dockerfile）

### API/config 新增字段

```
config.language: 'zh' | 'en' | 'ja' | 'ko'  (默认 'zh')
config.tts_voice: 'zh-CN-XiaoxiaoNeural' | ...  (默认第一个)
```

## 改动清单

| 文件 | 操作 | 改动量 |
|------|------|--------|
| `Dockerfile` | 新建 | ~15 行 |
| `docker-compose.yml` | 新建 | ~10 行 |
| `i18n/{zh,en,ja,ko}.json` | 新建 | 各 ~30 行 |
| `index.html` | 修改 | +15 行 |
| `script.js` | 修改 | +60 行 |
| `styles.css` | 修改 | +15 行 |
| `services/llm_service.py` | 修改 | +5 行 |
| `services/tts_service.py` | 修改 | ~5 行 |
| `services/composer.py` | 修改 | ~10 行 |
| `app.py` | 修改 | +10 行 |
| `config.py` | 修改 | +8 行 |
| `resource/fonts/` | 新建 | 1 个字体文件 |
