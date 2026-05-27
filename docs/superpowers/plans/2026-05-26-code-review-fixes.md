# Code Review 修复计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复代码审查发现的 1 个 Critical + 5 个 Important + 2 个 Minor 问题

**Architecture:** 纯修正，不改架构。涉及 git 清理、命名修正、README 更新、API 加固

**Tech Stack:** Python 3.13, Flask, Git

---

### Task 1: 清理 .pyc 文件 git 追踪 🔴

**Files:**
- Remove tracking: `__pycache__/` (git rm --cached)

- [ ] **Step 1: 移除 git 追踪**

```bash
cd "d:/PYTHON/simple_webpage"
git rm --cached __pycache__/app.cpython-313.pyc
git rm --cached __pycache__/logger_config.cpython-313.pyc
```

- [ ] **Step 2: 确认 .gitignore 已有保护**

```bash
grep -n "__pycache__" .gitignore
```

Expected output: `3:__pycache__/`

- [ ] **Step 3: 提交**

```bash
git add .gitignore
git commit -m "$(cat <<'EOF'
fix: 移除 git 跟踪的 .pyc 文件
EOF
)"
```

---

### Task 2: 修正 bgm_volume 命名 🟡

**Files:**
- Modify: `app.py` (config key defaults 和 session_create)
- Modify: `index.html` (标签文案)
- Modify: `services/composer.py` (变量名)

- [ ] **Step 1: 将 config key 从 `bgm_volume` 改为 `original_audio_level`**

`app.py` — 全自动默认配置:

```python
# AUTO_MODE_DEFAULTS in config.py
AUTO_MODE_DEFAULTS = {
    ...
    'original_audio_level': 20,
}
```

`app.py` — session_create 半自动配置:

```python
config = {
    ...
    'original_audio_level': int(request.form.get('bgm_volume', 20))
}
```

`app.py` — compose 步骤:

```python
# line ~37 in compose_video call
vid_vol = int(config.get('original_audio_level', 20)) / 100.0
```

`services/composer.py` — compose_video 函数签名和内部变量:

```python
def compose_video(session_dir, shots, config):
    ...
    vid_vol = int(config.get('original_audio_level', 20)) / 100.0
    ...
    _mix_audio(cur, nar, mp, narration_volume=1.0,
               video_volume=max(0.1, 1.0 - vid_vol))
```

- [ ] **Step 2: 更新前端标签**

`index.html`:

```html
<label>原视频音量</label>
<input type="range" id="bgmVolume" min="0" max="100" value="20" class="volume-slider">
<span id="bgmVolumeLabel">20%</span>
```

> 注意: 前端 `id="bgmVolume"` 保持不变避免打断 JS，但发送时 key 是 `bgm_volume`，后端转为 `original_audio_level`

- [ ] **Step 3: 验证语法**

```bash
python -m py_compile app.py && python -m py_compile services/composer.py && echo "OK"
```

- [ ] **Step 4: 提交**

```bash
git add app.py services/composer.py index.html
git commit -m "$(cat <<'EOF'
fix: bgm_volume 重命名为 original_audio_level，前端标签改为"原视频音量"
EOF
)"
```

---

### Task 3: 更新 README.md 🟡

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 用当前项目结构替换过时内容**

将 README.md 中的项目结构部分改为:

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

- [ ] **Step 2: 提交**

```bash
git add README.md
git commit -m "docs: 更新 README 项目结构为当前架构"
```

---

### Task 4: DeepSeek API 加 timeout 🟡

**Files:**
- Modify: `services/llm_service.py`

- [ ] **Step 1: 4 处 API 调用加 timeout=120**

`design_shots_from_document()`:

```python
response = client.chat.completions.create(
    model="deepseek-v4-pro",
    messages=[...],
    temperature=temp, max_tokens=32000, timeout=120,
    thinking={"type": "enabled"}, reasoning_effort="high"
)
```

`generate_prompts()` — Round 1 (bible):

```python
bible = _extract_json(client.chat.completions.create(
    model="deepseek-v4-pro",
    messages=[...],
    temperature=0.4, max_tokens=16000, timeout=120,
    thinking={"type": "enabled"}, reasoning_effort="high"
).choices[0].message.content)
```

`generate_prompts()` — Round 2 (prompts):

```python
prompts = _extract_json(client.chat.completions.create(
    model="deepseek-v4-pro",
    messages=[...],
    temperature=0.4, max_tokens=32000, timeout=120,
    thinking={"type": "enabled"}, reasoning_effort="high"
).choices[0].message.content)
```

- [ ] **Step 2: 验证语法**

```bash
python -m py_compile services/llm_service.py && echo "OK"
```

- [ ] **Step 3: 提交**

```bash
git add services/llm_service.py
git commit -m "fix: DeepSeek API 调用添加 timeout=120 防止请求挂起"
```

---

### Task 5: 删除未使用的 PIPELINE_STATES 🟡

**Files:**
- Modify: `config.py`

- [ ] **Step 1: 删除常量定义**

删除 `config.py` 中的:

```python
PIPELINE_STATES = ['UPLOADED', 'SHOTS_DESIGNED', 'PROMPTS_READY',
                    'IMAGES_GENERATED', 'VIDEOS_GENERATED', 'COMPOSED']
```

同时搜索确保没有任何文件 import 它:

```bash
grep -rn "PIPELINE_STATES" . --include="*.py" | grep -v ".venv" | grep -v "__pycache__"
```

- [ ] **Step 2: 验证语法**

```bash
python -m py_compile config.py && echo "OK"
```

- [ ] **Step 3: 提交**

```bash
git add config.py
git commit -m "chore: 移除未使用的 PIPELINE_STATES 常量"
```

---

### Task 6: 修正 .env.example 的 DeepSeek URL 🟢

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: 去掉末尾 /v1**

将 `.env.example` 第 5 行从:

```
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
```

改为:

```
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

> OpenAI SDK 会自动追加 /v1，写 /v1 会导致双写为 /v1/v1

- [ ] **Step 2: 提交**

```bash
git add .env.example
git commit -m "fix: .env.example DeepSeek URL 去掉多余 /v1 后缀"
```

---

### Task 7: 增强 auth cookie 安全性 🟢

**Files:**
- Modify: `app.py`

- [ ] **Step 1: cookie 增加 secure 和 samesite**

`app.py` 第 83 行，将:

```python
resp.set_cookie('auth', token, max_age=60*60*24*30, httponly=True)
```

改为:

```python
resp.set_cookie('auth', token, max_age=60*60*24*30,
                httponly=True, secure=True, samesite='Lax')
```

- [ ] **Step 2: 验证语法**

```bash
python -m py_compile app.py && echo "OK"
```

- [ ] **Step 3: 提交**

```bash
git add app.py
git commit -m "fix: auth cookie 添加 secure 和 samesite 属性"
```

---

### Task 8: 端到端验证

- [ ] **Step 1: 启动 Flask**

```bash
cd "d:/PYTHON/simple_webpage"
python app.py &
sleep 2
```

- [ ] **Step 2: 测试静态资源**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/styles.css
```

Expected: 全部 200

- [ ] **Step 3: 测试 Pro 模式创建会话**

```bash
echo "test" > /tmp/t.txt
curl -s -X POST http://localhost:5000/api/session/create \
  -F "file=@/tmp/t.txt" -F "mode=semi_auto"
```

Expected: JSON 中有 `original_audio_level: 20`

- [ ] **Step 4: 停止服务器**

```bash
taskkill //F //IM python.exe 2>/dev/null
```
