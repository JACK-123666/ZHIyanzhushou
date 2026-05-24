# 智演助手优化 — 设计文档

日期：2026-05-24 | 状态：待审阅

## 目标

优化智演助手项目（Flask + 原生前端）的架构、安全性和代码质量，保留核心链路：**上传文档 → AI 提取内容 → 生成 Prompt → 调用 Seedance API 生成视频**。

## 核心链路（不可变）

文档上传（PDF/DOCX/PPTX/TXT）→ 内容解析 → AI Prompt 生成 → Seedance API 视频生成 → 返回视频

## 移除清单

| 类别 | 文件 / 模块 |
|------|------------|
| PPT 脚本 | `create_ppt.js`, `create_ppt_v2.js` |
| Node | `node_modules/`, `package.json`, `package-lock.json` |
| 测试残留 | `test_video_generation.py`, `test_output.mp4` |
| 产物 | `outputs/*.mp4`, `uploads/*`（保留目录结构） |
| 过时文档 | `API_KEY_GUIDE.md`, `DEPLOYMENT.md`, `GITHUB_GUIDE.md`, `GITHUB_PAGES_DEPLOYMENT.md`, `INSTALL_GUIDE.md`, `使用指南.md` |
| 非核心功能 | 音频上传 + `transcribe_audio`() |
| 本地降级 | `create_intelligent_video`(), `create_placeholder_video`(), `wrap_text`() |

## 新文件结构

```
simple_webpage/
├── app.py                  # Flask 入口 + 路由（~60行）
├── config.py               # 配置：密钥、模型、常量、允许扩展名
├── services/
│   ├── __init__.py
│   ├── document_parser.py  # 解析 PDF/DOCX/PPTX/TXT
│   ├── prompt_generator.py # AI prompt 结构分析 + 生成
│   └── video_generator.py  # Seedance API：创建任务、轮询、下载
├── logger_config.py        # 日志系统（保持现有）
├── index.html / styles.css / script.js
├── api/index.py            # Vercel 入口（保留不动）
├── vercel.json             # 保留不动
├── requirements.txt        # 移除 moviepy, imageio, imageio-ffmpeg
└── .gitignore              # 补全：.env, __pycache__, uploads/, outputs/, logs/
```

## 模块设计

### config.py

- 从环境变量读取所有密钥，无硬编码
- 集中管理：允许的文件扩展名、风格映射、时长映射、模型配置
- 提供 `get_model_config(model_key)` 工厂函数

### services/document_parser.py

- `parse_document(filepath)` → 根据扩展名分发到对应解析器
- `parse_txt()`, `parse_docx()`, `parse_pdf()`, `parse_pptx()`
- 每个解析器独立处理内容截断逻辑
- 不再支持 `.doc` 二进制格式

### services/prompt_generator.py

- `generate_prompt(content, style, duration, narrator)` → 返回 prompt 字符串
- 从 `app.py` 中提取 `analyze_document_structure`, `select_content_for_duration`, `build_scene_descriptions`, `generate_video_prompt` 并重构
- 消除 magic numbers，提取为模块级常量

### services/video_generator.py

- `generate_video(model_config, prompt, video_data)` → 返回生成结果
- 封装 Seedance API：创建任务 → 轮询 → 下载
- 重试逻辑抽取为独立的 `_retry_create_task`, `_poll_task`, `_download_video` 方法
- 使用早返回模式替代深层嵌套

### app.py

- 缩减至：Flask 初始化、CORS 配置、路由定义
- `/api/upload` — 文件上传（添加文件名安全校验）
- `/api/generate-video` — 编排 document_parser → prompt_generator → video_generator
- `/api/video/<filename>` — 视频下载
- 静态文件路由
- 移除 `app.config['MAX_CONTENT_LENGTH']` 降为 50MB

## 安全优化

1. 移除 app.py 中硬编码的 API Key
2. `.gitignore` 补全：`.env`, `__pycache__/`, `uploads/`, `outputs/`, `logs/`
3. 上传统一使用 `secure_filename` 防止路径穿越
4. 上传大小限制降为 50MB

## 前端优化

- `script.js`：提取常量 `ALLOWED_EXTENSIONS`、`FORMAT_SIZES`，移除调试 `console.log`
- 错误处理：`alert()` 替换为页面内 toast 提示
- HTML/CSS 保持不变

## 依赖清理

从 `requirements.txt` 移除不再需要的包：
- `moviepy`, `imageio`, `imageio-ffmpeg`（本地视频生成用）
- （保留 `opencv-python` 若 Seedance 响应处理需要；否则一并移除）

## 不改变

- Flask 框架版本
- 前端 UI（HTML/CSS 结构）
- API 接口签名
- Vercel 部署配置
- 日志系统
