# MoneyPrinterTurbo 特性借鉴 — 设计规格

## 目标

借鉴 MoneyPrinterTurbo 的 4 个实用特性，低成本适配到智演助手，提升完整度。

## 特性清单

| # | 特性 | 来源 | 状态 |
|---|------|------|------|
| 1 | BGM 系统 | MPT `resource/songs/` | Pro 模式专属 |
| 2 | 时长修正 | MPT 素材循环策略 | composer 内部 |
| 3 | 进度追踪 | MPT `/tasks/{id}` | 状态接口增强 |
| 4 | `/rerun` 端点 | MPT `stop_at` 简化版 | 新增端点 |

---

## 特性 1：BGM 系统

### 触发条件
- 仅 Pro 模式，前端提供"背景音乐"开关（默认关闭）
- 全自动模式不加 BGM

### 数据流
```
resource/bgm/*.mp3（3-5 首免费 BGM）
  → compose 端点从 config 读取 bgm_enabled/bgm_volume
  → composer.py 下载/随机选曲 → ffmpeg 混音
```

### ffmpeg 混音链
```
BGM mp3 → volume=bgm_vol → stream_loop(若短于视频) → afade 淡出3s
                                                              ↓
旁白 mp3 → ─────────────────────────────→ amix=inputs=2:duration=first → 背景音轨
                                                              ↓
视频 → ─── 原视频音轨(original_audio_level 控制) ──→ amix → 最终输出
```

### 配置项（Pro 模式 config）
```
bgm_enabled: 'yes' | 'no'  （默认 'no'）
bgm_volume: 5-30            （默认 10，偏低不抢旁白）
```

### 改动文件
| 文件 | 改动 |
|------|------|
| `resource/bgm/` | 新建，放 3-5 首 CC0 免费 BGM |
| `services/composer.py` | `compose_video()` 内嵌 BGM 混音 ~25 行 |
| `index.html` | Pro 面板加 bgm_enabled 开关 + bgm_volume 滑块 |
| `script.js` | startPipeline 发送 bgm_enabled/bgm_volume |
| `app.py` | session_create 存储 bgm 配置 |

---

## 特性 2：时长自动修正

### 触发条件
composer 内部，每次合成时自动执行，用户无感。

### 逻辑
```
旁白总时长 = sum(每镜旁白字数 / 4字/秒)
视频总时长 = sum(每镜实际视频时长)

if 旁白 > 视频:
    最后一镜 → stream_loop 循环补足差值
if 视频 > 旁白:
    最后一镜 → ffmpeg -t 截断到旁白结束
```

### 改动文件
| 文件 | 改动 |
|------|------|
| `services/composer.py` | `compose_video()` 开头计算 nar_total → 末尾修正最后一镜 ~20 行 |

---

## 特性 3：进度百分比

### API 增强
`GET /api/session/<id>/status` 当前返回:
```json
{"status": "VIDEOS_GENERATED", "progress": null}
```

改为:
```json
{
  "status": "VIDEOS_GENERATED",
  "progress": 72,
  "step_detail": "正在生成视频 (8/12)...",
  "stats": {"shots_done": 8, "shots_total": 12, "shots_failed": 1}
}
```

### 进度计算
```
UPLOADED:        5%
SHOTS_DESIGNED: 15%
PROMPTS_READY:  30%
IMAGES...       45% + (done/total) * 20%  = 45-65%
VIDEOS...       65% + (done/total) * 30%  = 65-95%
COMPOSED:       100%
```

### 改动文件
| 文件 | 改动 |
|------|------|
| `app.py` | `session_status()` 增强 ~20 行 |
| `script.js` | 进度条从阶梯跳动改为平滑过渡 ~10 行 |

---

## 特性 4：/rerun 端点

### API
```
POST /api/session/<id>/rerun?from=<step>
```
`step` 可选值: `design` | `prompts` | `images` | `videos` | `compose`

### 逻辑
1. 加载 state.json
2. 根据 `from` 参数，跳过前面的步骤（已缓存的结果直接用）
3. 从指定步骤开始执行，沿用现有 `_update_state` 机制
4. 返回 `{"status": "rerunning", "from_step": "images"}`

### 示例
```
# 从出图开始重跑（跳过上传/分镜/prompt）
POST /api/session/abc/rerun?from=images

# 从视频开始重跑（跳过所有，只重新生成视频+合成）
POST /api/session/abc/rerun?from=videos
```

### 改动文件
| 文件 | 改动 |
|------|------|
| `app.py` | 新增 `/rerun` 路由 + 分发逻辑 ~30 行 |

---

## 总改动

| 文件 | 改动量 | 新增特性 |
|------|--------|---------|
| `services/composer.py` | ~45 行 | BGM 混音 + 时长修正 |
| `app.py` | ~50 行 | bgm 配置 + progress 增强 + /rerun |
| `index.html` | ~15 行 | BGM 开关 + 滑块 |
| `script.js` | ~15 行 | BGM 参数 + 进度平滑 |
| `resource/bgm/` | 新建 | 3-5 个 mp3 |

API 调用增量：零。ffmpeg 增量：一个混音 pass（~5秒）。
