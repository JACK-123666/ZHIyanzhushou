# Zhiyan

文档上传 → AI 全自动生成视频。LLM 导演 + 多模型编排，从剧本到成片一气呵成。

## Demo

上传一篇故事（愚公移山、小红帽……），几分钟后得到一部带配音、字幕、BGM 的完整短片。

```
《愚公移山》.txt  ──→  8 镜头 × 38 秒  ──→  愚公移山.mp4
```

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env    # 编辑填入 API Key
python app.py           # http://localhost:5000
```

**前置依赖**：ffmpeg（视频合成），需系统安装。

## 需要哪些 API Key

| 平台 | 用途 | 获取方式 |
|------|------|---------|
| 火山引擎 ARK | Seedream 出图 + Seedance 生视频 | [console.volcengine.com](https://console.volcengine.com) → 方舟平台 |
| DeepSeek | 内容理解、分镜设计、Prompt 生成 | [platform.deepseek.com](https://platform.deepseek.com) |

两个 Key 写入 `.env` 即可启动。

## 使用

### 浏览器操作

1. 打开 `http://localhost:5000`
2. 选择模式（半自动手动配置 / 全自动 AI 接管）
3. 拖入 `.txt` 或 `.docx` 文档
4. 点击「开始生成」
5. 等待 6 步流水线完成，下载视频

### 半自动 vs 全自动

| | 半自动 | 全自动 |
|------|--------|--------|
| 风格 | 手动选（3D卡通/2D扁平/写实/素描） | AI 读完文档自己判断 |
| 时长 | 每镜 5 秒或 AI 分配 | 按总目标时长反推 |
| 分辨率 | 手动选 | 1920×1080 |
| 适合 | 想精确控制画面风格 | 丢文档就走 |

### Agent 模式

勾选「Agent 自主模式」后，Zhiyan 的 LLM Agent 接管一切决策——自己决定先做什么、出了错怎么补救、哪些镜头可以跳过。可在右侧面板实时观察 Agent 的思考过程。

### API

| 端点 | 说明 |
|------|------|
| `POST /api/session/create` | 上传文档，创建会话 |
| `POST /api/session/<id>/design-shots` | LLM 分镜设计 |
| `POST /api/session/<id>/prompts` | 生成图/视频 Prompt |
| `POST /api/session/<id>/images` | 并发出图 |
| `POST /api/session/<id>/videos` | 并发生视频 |
| `POST /api/session/<id>/compose` | TTS 配音 + ffmpeg 合成 |
| `GET /api/session/<id>/download` | 下载成品视频 |
| `GET /api/session/<id>/status` | 进度 + 成本预估 |
| `GET /api/agent/<id>/stream` | Agent SSE 思考流 |

## 工作流

```
文档 (.txt/.docx)
    │
    ▼
[1] 文档解析 ─── 提取全文，截断保护
    │
    ▼
[2] 分镜设计 ─── DeepSeek 通读全文 → 输出镜号/场景/运镜/灯光/角色体系
    │
    ▼
[3] Prompt 生成 ─ 视觉圣经（全片风格锚点）+ 逐镜 image_prompt / video_prompt
    │
    ▼
[4] 图片生成 ─── Seedream 出图，同场景复用，5 线程并行
    │
    ▼
[5] 视频生成 ─── Seedance 图生视频，原生音频，10 线程并行
    │
    ▼
[6] 合成输出 ─── Edge TTS 配音 + ffmpeg 字幕/混音/xfade 拼接 → .mp4
```

## 模型

| 步骤 | 模型 |
|------|------|
| 分镜 + Prompt | DeepSeek V4 |
| 图片生成 | Seedream 5.0（火山引擎 ARK） |
| 视频生成 | Seedance 2.0（火山引擎 ARK） |
| 配音 | Edge TTS（免费） |
| 合成 | ffmpeg |

## 项目结构

```
├── app.py                # Flask 主程序
├── config.py             # 模型配置、风格/分辨率/多语言定义
├── agent/                # Agent 模式
│   ├── core.py           #   ZhiyanAgent — ReAct 决策循环
│   ├── tools.py          #   10 个工具的注册与实现
│   ├── memory.py         #   镜头状态机 + 工作记忆
│   ├── planner.py        #   失败重规划 + 决策反思
│   ├── execution_plan.py #   多阶段执行计划
│   └── state_summary.py  #   智能状态摘要（瓶颈/分级/成本）
├── services/             # 核心服务
│   ├── llm_service.py    #   DeepSeek 调用 + Prompt 工程
│   ├── image_generator.py#   Seedream 文生图
│   ├── pipeline.py       #   Seedance API 封装
│   ├── tts_service.py    #   Edge TTS 配音
│   ├── composer.py       #   ffmpeg 视频合成
│   └── document_parser.py#   .txt/.docx 解析
├── index.html            # 前端 SPA
├── script.js             # 前端逻辑（含 Agent SSE 客户端）
└── styles.css            # UI 样式
```

## 成本

以愚公移山为例（8 镜头 × 38 秒，720p）：

| 项目 | 费用 |
|------|------|
| 图片生成 | 5 次 × ~$0.02 = $0.10 |
| 视频生成 | 38 秒 × ~$0.12 = $4.56 |
| LLM 调用 | 3 次 × ~$0.005 = $0.02 |
| **合计** | **~$4.68** |

> 实际费用取决于文档长度、镜头数量和视频画质。启动后可在分镜设计阶段看到预估成本。

## License

MIT
