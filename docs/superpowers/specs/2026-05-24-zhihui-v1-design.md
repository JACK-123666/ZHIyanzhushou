# 智演助手 1.0 设计文档

日期：2026-05-24 | 状态：已审批

## 目标

将智演助手升级为完整的分镜脚本→视频自动生成流水线。

## 数据流

```
文档(.docx/.txt) → DeepSeek 分镜解析 → shots.json
  → DeepSeek Prompt 生成 → image_prompt + video_prompt
  → Seedream 文生图 → shot_N_frame.png
  → Seedance 2.0 Flash 图+prompt → shot_N.mp4
  → moviepy 拼接 + TTS + BGM → final_video.mp4
```

## 新文件结构

```
simple_webpage/
├── app.py                       # Flask + 路由 + Session 管理
├── config.py                    # API 密钥、模型配置、前端选项定义
├── services/
│   ├── __init__.py
│   ├── document_parser.py       # .docx/.txt 文本提取
│   ├── llm_service.py           # DeepSeek: 分镜解析 + Prompt 生成
│   ├── prompt_generator.py      # 分镜 Prompt 模板引擎（全局风格前缀等）
│   ├── image_generator.py       # Seedream 文生图 API
│   ├── video_generator.py       # Seedance 图生视频 API
│   ├── tts_service.py           # Edge TTS 旁白生成
│   └── composer.py              # moviepy 拼接 + 音频 + BGM
├── logger_config.py
├── index.html / styles.css / script.js
├── api/index.py
└── requirements.txt
```

## 前端配置项（7 个）

| 配置 | 默认值 | 可选值 |
|------|--------|--------|
| style_template | 3D卡通 | 3D卡通/2D扁平/写实简化/素描线稿 |
| duration_mode | 统一5秒 | 严格按脚本/统一5秒/自动拆分(>8s) |
| consistency_strategy | 通用无面孔 | 通用无面孔/参考图驱动/随机生成 |
| resolution | 1920x1080 | 1920x1080/1024x1024/1080x1920 |
| auto_subtitle | 是 | 是/否 |
| auto_sfx | 否 | 是/否 |
| bgm_volume | 20 | 0-100 |

## 状态机

```
UPLOADED → PARSED → PROMPTS_READY → IMAGES_GENERATED → VIDEOS_GENERATED → COMPOSED
```

中间文件存 `outputs/{session_id}/`，每个阶段失败可重试。

## API 端点

| 端点 | 阶段 |
|------|------|
| POST /api/session/create | 上传文档，创建 session |
| POST /api/session/{id}/parse | DeepSeek 解析 + Prompt 生成 |
| POST /api/session/{id}/images | Seedream 文生图 |
| POST /api/session/{id}/videos | Seedance 图生视频 |
| POST /api/session/{id}/compose | TTS + moviepy 合成 |

## API 配置（留接口，后续接入）

- DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL
- SEEDREAM_API_KEY / SEEDREAM_ENDPOINT
- SEEDANCE_API_KEY / SEEDANCE_ENDPOINT（已有）
- TTS: Edge TTS（免费，无需 key）
