# MPT 特性借鉴 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 借鉴 MoneyPrinterTurbo 4 个特性：BGM 系统、时长修正、进度百分比、/rerun 端点

**Architecture:** 零 API 调用增量，改动 composer.py + app.py + 前端

**Tech Stack:** Python 3.13, Flask, ffmpeg

---

### Task 1: BGM 系统

**Files:**
- Modify: `services/composer.py`
- Modify: `app.py`
- Modify: `index.html`
- Modify: `script.js`

#### Step 1: composer.py — BGM 混音 + 时长修正

在 `compose_video()` 函数中，在所有视频处理完成后、xfade 拼接之前，加入 BGM 混音。

找到 `compose_video()` 函数中 `if not processed:` 检查之后的 normalized 循环。在 xfade 拼接之前插入：

```python
    # === BGM 混音 ===
    bgm_enabled = config.get('bgm_enabled', 'no') == 'yes'
    if bgm_enabled:
        bgm_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'resource', 'bgm')
        bgm_files = [f for f in os.listdir(bgm_dir) if f.endswith('.mp3')] if os.path.exists(bgm_dir) else []
        if bgm_files:
            bgm_vol = int(config.get('bgm_volume', 10)) / 100.0
            bgm_path = os.path.join(bgm_dir, bgm_files[hash(session_dir) % len(bgm_files)])
            # 为每个 normalized 片段混入 BGM
            for i, clip_path in enumerate(normalized):
                dur = _get_duration(clip_path)
                bgm_clip = os.path.join(session_dir, f"bgm_{i}.mp4")
                r = subprocess.run(['ffmpeg', '-y',
                    '-i', _norm(clip_path),
                    '-stream_loop', '-1', '-i', _norm(bgm_path),
                    '-filter_complex',
                    f'[1:a]volume={bgm_vol},aformat=sample_fmts=fltp:channel_layouts=stereo,atrim=0:{dur},afade=t=out:st={max(0,dur-3)}:d=3[bgm];'
                    f'[0:a]volume={1.0 - bgm_vol}[orig];'
                    f'[bgm][orig]amix=inputs=2:duration=first[outa]',
                    '-map', '0:v', '-map', '[outa]',
                    '-c:v', 'copy', '-c:a', 'aac', _norm(bgm_clip)],
                    capture_output=True, text=True)
                if r.returncode == 0:
                    normalized[i] = bgm_clip
                    temps.append(bgm_clip)
```

#### Step 2: composer.py — 时长自动修正

在同一位置，BGM 处理之前，加入时长修正常量：

```python
    # === 时长修正 ===
    from app import _load_state  # 避免循环引用，改为函数内 import 或直接用 session_dir 参数

    # 计算旁白总时长和视频总时长
    nar_total = 0
    for shot in shots:
        nar_text = shot.get('narration', '')
        nar_total += len(nar_text) / 4  # 中文~4字/秒
    vid_total = sum(_get_duration(p) for p in normalized)

    if nar_total > vid_total and len(normalized) > 0:
        # 最后一镜循环补足
        last = normalized[-1]
        diff = nar_total - vid_total
        loops = int(diff / (_get_duration(last) or 5)) + 1
        looped = os.path.join(session_dir, 'last_looped.mp4')
        r = subprocess.run(['ffmpeg', '-y', '-stream_loop', str(loops), '-i', _norm(last),
            '-t', str(diff), '-c', 'copy', _norm(looped)],
            capture_output=True, text=True)
        if r.returncode == 0:
            # 把循环版拼到原片段后面
            concatted = os.path.join(session_dir, 'last_extended.mp4')
            # 简单方案：直接替换 normalized[-1] 为延长版
            # 用 concat filter 把 last + looped 拼起来
            r2 = subprocess.run(['ffmpeg', '-y',
                '-i', _norm(last), '-i', _norm(looped),
                '-filter_complex', '[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]',
                '-map', '[outv]', '-map', '[outa]',
                '-c:v', 'libx264', '-c:a', 'aac', _norm(concatted)],
                capture_output=True, text=True)
            if r2.returncode == 0:
                normalized[-1] = concatted
                temps.append(looped); temps.append(concatted)
```

#### Step 3: app.py — BGM 配置存储

`session_create` 中 Pro 模式 config 加两个字段：

```python
'bgm_enabled': request.form.get('bgm_enabled', 'no'),
'bgm_volume': int(request.form.get('bgm_volume', 10))
```

`AUTO_MODE_DEFAULTS` 保持不变（全自动不启用 BGM）。

#### Step 4: index.html — BGM UI

Pro 面板的 `options-grid` 末尾，在 `原视频音量` 滑块之后添加：

```html
<div class="option-group">
    <label>背景音乐</label>
    <select id="bgmEnabled" class="modern-select">
        <option value="no">关闭</option>
        <option value="yes">开启</option>
    </select>
    <span class="option-hint">自动匹配免费BGM</span>
</div>
<div class="option-group">
    <label>BGM音量</label>
    <input type="range" id="bgmVolumeSlider" min="5" max="30" value="10" class="volume-slider">
    <span id="bgmVolumeLabel">10%</span>
</div>
```

#### Step 5: script.js — BGM 参数发送

`startPipeline()` 的 FormData 追加：

```javascript
formData.append('bgm_enabled', document.getElementById('bgmEnabled').value);
formData.append('bgm_volume', document.getElementById('bgmVolumeSlider').value);
```

BGM 音量滑块事件绑定：

```javascript
document.getElementById('bgmVolumeSlider').addEventListener('input', function () {
    document.getElementById('bgmVolumeLabel').textContent = this.value + '%';
});
```

#### Step 6: 验证

```bash
python -m py_compile services/composer.py app.py && echo "OK"
```

#### Step 7: 提交

```bash
git add services/composer.py app.py index.html script.js
git commit -m "$(cat <<'EOF'
feat: BGM 系统（Pro模式） + 时长自动修正
EOF
)"
```

---

### Task 2: 进度百分比

**Files:**
- Modify: `app.py`
- Modify: `script.js`

#### Step 1: app.py — session_status 增强

在 `session_status()` 函数中，增加 progress 计算：

```python
@app.route('/api/session/<session_id>/status', methods=['GET'])
def session_status(session_id):
    state = _load_state(session_id)
    if not state:
        return jsonify({'error': 'Session 不存在'}), 404

    status = state.get('status', 'UPLOADED')
    shots = state.get('shots', [])
    total = len(shots) or 1

    # 进度百分比
    progress_map = {
        'UPLOADED': 5, 'SHOTS_DESIGNED': 15, 'PROMPTS_READY': 30,
        'IMAGES_GENERATED': 55, 'VIDEOS_GENERATED': 85, 'COMPOSED': 100
    }
    base = progress_map.get(status, 5)

    # 在 IMAGES 或 VIDEOS 阶段细化
    done = 0
    if status == 'IMAGES_GENERATED' or status == 'VIDEOS_GENERATED' or status == 'COMPOSED':
        done = sum(1 for s in shots if s.get('image_path') and os.path.exists(s.get('image_path', '')))
        if status != 'IMAGES_GENERATED':
            done = sum(1 for s in shots if s.get('video_path') and os.path.exists(s.get('video_path', '')))
            base = 65
        progress = min(base + int((done / total) * 25), 99)
    else:
        progress = base

    step_detail = f'{status} ({done}/{total})' if status in ('IMAGES_GENERATED','VIDEOS_GENERATED') else status

    return jsonify({
        'session_id': session_id, 'status': status, 'progress': progress,
        'step_detail': step_detail,
        'stats': {'shots_done': done, 'shots_total': total}
    })
```

#### Step 2: script.js — 进度条平滑

当前 `startPipeline()` 中 `updatePipelineStep()` 只更新步骤状态。加一个 `updateProgressBar(percent)` 辅助在调用每个 API 后更新前端：

```javascript
function updateProgressBar(percent) {
    // 如果存在进度条元素则更新
    var bar = document.getElementById('progressBar');
    if (bar) { bar.style.width = percent + '%'; }
    var pct = document.getElementById('progressPct');
    if (pct) { pct.textContent = percent + '%'; }
}
```

#### Step 3: 验证

```bash
python -m py_compile app.py && echo "OK"
```

#### Step 4: 提交

```bash
git add app.py script.js
git commit -m "$(cat <<'EOF'
feat: 进度百分比 API + 前端平滑进度条
EOF
)"
```

---

### Task 3: /rerun 端点

**Files:**
- Modify: `app.py`

#### Step 1: 新增路由

在 `/retry-failed` 路由附近，新增 `/rerun` 路由：

```python
@app.route('/api/session/<session_id>/rerun', methods=['POST'])
def session_rerun(session_id):
    """从指定步骤重跑流水线。from=design|prompts|images|videos|compose"""
    state = _load_state(session_id)
    if not state:
        return jsonify({'error': 'Session 不存在'}), 404

    from_step = request.args.get('from', 'images')
    step_order = ['design', 'prompts', 'images', 'videos', 'compose']
    if from_step not in step_order:
        return jsonify({'error': f'无效步骤: {from_step}，可选: {step_order}'}), 400

    start_idx = step_order.index(from_step)
    steps_to_run = step_order[start_idx:]

    # 按需跳过前面的步骤（已有结果直接用）
    results = {'rerun_from': from_step, 'steps_executed': []}

    for step in steps_to_run:
        if step == 'design':
            content = parse_document(state['filepath'])
            result = design_shots_from_document(content, state['config'])
            # ... 同 session_design_shots 逻辑
            _update_state(session_id, 'SHOTS_DESIGNED', shots=result['shots'], ...)
            results['steps_executed'].append('design')

        elif step == 'prompts':
            shots = state.get('shots', [])
            prompts = generate_prompts(shots, state['config'], state.get('character_summary'))
            # ... 同 session_prompts 逻辑
            _update_state(session_id, 'PROMPTS_READY', prompts=prompts)
            results['steps_executed'].append('prompts')

        elif step == 'images':
            # ... 同 session_images 逻辑
            results['steps_executed'].append('images')

        elif step == 'videos':
            # ... 同 session_videos 逻辑
            results['steps_executed'].append('videos')

        elif step == 'compose':
            # ... 同 session_compose 逻辑
            results['steps_executed'].append('compose')

    return jsonify(results)
```

> 注意：`images`/`videos`/`compose` 三步的代码较长，不要复制粘贴。直接在函数内用 `state` 已有的数据调已有端点逻辑。更简洁的做法是：让 `/rerun` 内部转发到已有的子函数，或者让已有路由的逻辑提取为独立函数。

**简化方案** — 把各步骤的核心逻辑提取为内部函数：

```python
def _run_design(state):
    content = parse_document(state['filepath'])
    result = design_shots_from_document(content, state['config'])
    # ... (现有 session_design_shots 逻辑)
    _update_state(state['session_id'], 'SHOTS_DESIGNED', shots=result['shots'], ...)
    return result

# session_rerun 按 step 调用 _run_design / _run_prompts / _run_images / _run_videos / _run_compose
```

#### Step 2: 验证

```bash
python -m py_compile app.py && echo "OK"
```

#### Step 3: 提交

```bash
git add app.py
git commit -m "$(cat <<'EOF'
feat: /rerun 端点，支持从指定步骤重跑流水线
EOF
)"
```

---

### Task 4: 端到端验证

- [ ] **Step 1: 全量编译**

```bash
python -m py_compile services/composer.py app.py && echo "OK"
```

- [ ] **Step 2: 路由验证**

```bash
python -c "from app import app; rules = [r.rule for r in app.url_map.iter_rules()]; assert '/api/session/<session_id>/rerun' in str(rules); print('all routes OK')"
```

- [ ] **Step 3: 启动测试**

```bash
python /d/PYTHON/simple_webpage/app.py &
sleep 2
curl -s http://localhost:5000/ && echo "server OK"
taskkill //F //IM python.exe 2>/dev/null
```
