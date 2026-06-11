var ALLOWED_EXTENSIONS = ['.docx', '.txt'];
var FORMAT_SIZES = ['Bytes', 'KB', 'MB', 'GB'];
var PIPELINE_STEPS = ['UPLOADED', 'SHOTS_DESIGNED', 'PROMPTS_READY', 'IMAGES_GENERATED', 'VIDEOS_GENERATED', 'COMPOSED'];
var currentSessionId = null;
var currentMode = 'semi_auto';
var i18nData = {};
var currentLang = 'zh';

function t(key) {
    return (i18nData[currentLang] && i18nData[currentLang][key]) || key;
}

async function setLanguage(lang) {
    currentLang = lang;
    if (!i18nData[lang]) {
        try {
            var resp = await fetch('i18n/' + lang + '.json');
            i18nData[lang] = await resp.json();
        } catch (e) { return; }
    }
    localStorage.setItem('lang', lang);
    // 更新所有 data-i18n 元素
    document.querySelectorAll('[data-i18n]').forEach(function(el) {
        var key = el.getAttribute('data-i18n');
        if (i18nData[lang][key]) el.textContent = i18nData[lang][key];
    });
    // 更新文档语言属性
    document.documentElement.lang = lang === 'zh' ? 'zh-CN' : lang === 'ja' ? 'ja-JP' : lang === 'ko' ? 'ko-KR' : 'en-US';
    // 更新select标签的语言特定选项
    if (lang !== 'zh') {
        document.querySelector('option[value="ai_design"]').textContent = lang === 'en' ? 'Smart (Rec)' : lang === 'ja' ? 'スマート(推奨)' : '스마트(권장)';
    }
}

function showToast(msg, type) {
    type = type || 'info';
    var c = document.getElementById('toastContainer');
    var t = document.createElement('div');
    t.className = 'toast ' + type;
    t.textContent = msg;
    c.appendChild(t);
    setTimeout(function () { t.remove(); }, 3000);
}

function switchMode(mode) {
    currentMode = mode;
    var tabSemi = document.getElementById('tabSemi');
    var tabAuto = document.getElementById('tabAuto');
    var configSemi = document.getElementById('configSemi');
    var configAuto = document.getElementById('configAuto');

    if (mode === 'auto') {
        tabSemi.className = 'mode-tab';
        tabAuto.className = 'mode-tab active';
        configSemi.style.display = 'none';
        configAuto.style.display = 'block';
    } else {
        tabSemi.className = 'mode-tab active';
        tabAuto.className = 'mode-tab';
        configSemi.style.display = 'block';
        configAuto.style.display = 'none';
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    var k = 1024;
    var i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + FORMAT_SIZES[i];
}

// --- DOM ---
var uploadArea = document.getElementById('uploadArea');
var fileInput = document.getElementById('fileInput');
var fileInfo = document.getElementById('fileInfo');
var fileName = document.getElementById('fileName');
var fileSize = document.getElementById('fileSize');
var removeFileBtn = document.getElementById('removeFile');
var configPanel = document.getElementById('configPanel');
var generateButton = document.getElementById('generateButton');
var progressContainer = document.getElementById('progressContainer');
var progressTitle = document.getElementById('progressTitle');
var progressText = document.getElementById('progressText');
var pipelineStats = document.getElementById('pipelineStats');
var statShots = document.getElementById('statShots');
var statScenes = document.getElementById('statScenes');
var statChars = document.getElementById('statChars');
var videoResult = document.getElementById('videoResult');
var resultVideo = document.getElementById('resultVideo');
var downloadBtn = document.getElementById('downloadBtn');
var newVideoBtn = document.getElementById('newVideoBtn');

document.addEventListener('DOMContentLoaded', function () {
    // 多语言初始化
    var savedLang = localStorage.getItem('lang') || (navigator.language.startsWith('zh') ? 'zh' : navigator.language.startsWith('ja') ? 'ja' : navigator.language.startsWith('ko') ? 'ko' : 'en');
    document.getElementById('langSwitcher').value = savedLang;
    setLanguage(savedLang);
    document.getElementById('langSwitcher').addEventListener('change', function () {
        setLanguage(this.value);
    });

    var cta = document.getElementById('ctaButton');
    if (cta) cta.addEventListener('click', function () {
        document.querySelector('#workspace').scrollIntoView({ behavior: 'smooth' });
    });

    uploadArea.addEventListener('click', function () { fileInput.click(); });

    uploadArea.addEventListener('dragover', function (e) {
        e.preventDefault();
        uploadArea.style.borderColor = '#3498db';
    });
    uploadArea.addEventListener('dragleave', function (e) {
        e.preventDefault();
        uploadArea.style.borderColor = '';
    });
    uploadArea.addEventListener('drop', function (e) {
        e.preventDefault();
        uploadArea.style.borderColor = '';
        if (e.dataTransfer.files.length > 0) handleFile(e.dataTransfer.files[0]);
    });

    fileInput.addEventListener('change', function () {
        if (fileInput.files.length > 0) handleFile(fileInput.files[0]);
    });

    removeFileBtn.addEventListener('click', resetAll);
    generateButton.addEventListener('click', startPipeline);
    downloadBtn.addEventListener('click', function () {
        if (currentSessionId) window.open('/api/session/' + currentSessionId + '/download', '_blank');
    });
    newVideoBtn.addEventListener('click', resetAll);

    document.getElementById('bgmVolume').addEventListener('input', function () {
        document.getElementById('bgmVolumeLabel').textContent = this.value + '%';
    });

    // 模式切换 Tab
    document.getElementById('tabSemi').addEventListener('click', function () { switchMode('semi_auto'); });
    document.getElementById('tabAuto').addEventListener('click', function () { switchMode('auto'); });

    // BGM controls
    document.getElementById('bgmEnabled').addEventListener('change', function () {
        document.getElementById('bgmVolumeGroup').style.display = this.value === 'yes' ? 'block' : 'none';
    });
    document.getElementById('bgmVolumeSlider').addEventListener('input', function () {
        document.getElementById('bgmVolumeLabel').textContent = this.value + '%';
    });

    document.getElementById('retryAllBtn').addEventListener('click', retryAllFailed);
});

function handleFile(file) {
    var ext = '.' + file.name.split('.').pop().toLowerCase();
    if (ALLOWED_EXTENSIONS.indexOf(ext) === -1) {
        showToast(t('toast_upload_fail'), 'error');
        return;
    }
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    uploadArea.style.display = 'none';
    fileInfo.style.display = 'flex';
    configPanel.style.display = 'block';
    videoResult.style.display = 'none';
}

function renderShotsPreview(data) {
    var panel = document.getElementById('shotsPreview');
    var grid = document.getElementById('shotsGrid');
    if (!panel || !grid || !data.shots_preview) return;
    panel.style.display = 'block';
    grid.innerHTML = '';
    data.shots_preview.forEach(function(s) {
        var card = document.createElement('div');
        card.className = 'shot-card';
        card.id = 'shotCard_' + s.id;
        card.innerHTML =
            '<div class="shot-card-header">' +
                '<span class="shot-id">' + s.id + '</span>' +
                '<span class="shot-status pending">' + t('shot_pending') + '</span>' +
            '</div>' +
            '<div class="shot-card-thumb" id="thumb_' + s.id + '">' +
                '<div class="shot-card-placeholder">' +
                    '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>' +
                '</div>' +
            '</div>' +
            '<div class="shot-card-body">' +
                '<span class="shot-action">' + (s.action || s.id) + '</span>' +
                '<span class="shot-meta">' +
                    '<span class="shot-tag duration">' + s.duration + 's</span>' +
                    '<span class="shot-tag camera">' + (s.camera || '') + '</span>' +
                    '<span class="shot-tag mood">' + (s.mood || '') + '</span>' +
                '</span>' +
            '</div>' +
            '<button class="shot-retry-btn" id="retry_' + s.id + '" style="display:none" onclick="retryShot(\'' + s.id + '\')">' +
                '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>' +
                t('shot_retry') +
            '</button>';
        grid.appendChild(card);
    });
}

function updateShotStatus(shotId, status) {
    var card = document.getElementById('shotCard_' + shotId);
    if (!card) return;
    var statusEl = card.querySelector('.shot-status');
    if (statusEl) {
        statusEl.className = 'shot-status ' + status;
        var labels = { 'pending': t('shot_pending'), 'generating': t('shot_generating'), 'done': t('shot_done'), 'failed': t('shot_failed') };
        statusEl.textContent = labels[status] || status;
    }
    var retryBtn = document.getElementById('retry_' + shotId);
    if (retryBtn) {
        retryBtn.style.display = status === 'failed' ? 'inline-flex' : 'none';
    }
}

function updateShotThumb(shotId, imageUrl) {
    var thumb = document.getElementById('thumb_' + shotId);
    if (!thumb) return;
    thumb.innerHTML = '<img src="' + imageUrl + '" alt="' + shotId + '" class="shot-thumb-img" loading="lazy">';
}

async function retryShot(shotId) {
    if (!currentSessionId) return;
    var btn = document.getElementById('retry_' + shotId);
    if (btn) { btn.disabled = true; btn.textContent = t('shot_retrying'); }
    updateShotStatus(shotId, 'generating');
    try {
        var resp = await fetch('/api/session/' + currentSessionId + '/retry-failed?shot_id=' + shotId, { method: 'POST' });
        var data = await resp.json();
        if (data.still_failed && data.still_failed.indexOf(shotId) >= 0) {
            updateShotStatus(shotId, 'failed');
        } else {
            updateShotStatus(shotId, 'done');
        }
    } catch (e) {
        updateShotStatus(shotId, 'failed');
    }
    if (btn) { btn.disabled = false; btn.textContent = t('shot_retry'); }
    updateRetryAllBtn();
}

async function retryAllFailed() {
    if (!currentSessionId) return;
    var btn = document.getElementById('retryAllBtn');
    if (btn) { btn.disabled = true; btn.textContent = t('retrying'); }
    try {
        var resp = await fetch('/api/session/' + currentSessionId + '/retry-failed', { method: 'POST' });
        var data = await resp.json();
        if (data.still_failed) {
            data.still_failed.forEach(function(sid) { updateShotStatus(sid, 'failed'); });
        }
        if (data.retried > 0) {
            showToast(data.retried + ' ' + t('toast_retried'), 'success');
        }
    } catch (e) {
        showToast(t('toast_retry_fail'), 'error');
    }
    if (btn) { btn.disabled = false; btn.textContent = t('retry_all_failed'); }
    updateRetryAllBtn();
}

function updateRetryAllBtn() {
    var btn = document.getElementById('retryAllBtn');
    if (!btn) return;
    var anyFailed = document.querySelectorAll('.shot-status.failed').length > 0;
    btn.style.display = anyFailed ? 'inline-flex' : 'none';
}

function resetAll() {
    fileInput.value = '';
    uploadArea.style.display = 'block';
    fileInfo.style.display = 'none';
    configPanel.style.display = 'none';
    progressContainer.style.display = 'none';
    pipelineStats.style.display = 'none';
    var shotsPreview = document.getElementById('shotsPreview');
    if (shotsPreview) shotsPreview.style.display = 'none';
    videoResult.style.display = 'none';
    currentSessionId = null;
    currentMode = 'semi_auto';
    switchMode('semi_auto');
    for (var i = 1; i <= 6; i++) {
        var s = document.getElementById('pstep' + i);
        if (s) { s.className = 'pipeline-step'; }
    }
    updatePipelineStat(statShots, '-');
    updatePipelineStat(statScenes, '-');
    updatePipelineStat(statChars, '-');
}

function updatePipelineStat(el, val) {
    if (!el) return;
    el.querySelector('.chip-val').textContent = val;
}

function showStats(shots, scenes, chars) {
    pipelineStats.style.display = 'flex';
    updatePipelineStat(statShots, shots);
    updatePipelineStat(statScenes, scenes);
    updatePipelineStat(statChars, chars);
}

function updatePipelineStep(status) {
    var idx = PIPELINE_STEPS.indexOf(status);
    if (idx < 0) return;
    for (var i = 0; i < 6; i++) {
        var s = document.getElementById('pstep' + (i + 1));
        if (!s) continue;
        s.className = 'pipeline-step';
        if (i < idx) s.classList.add('done');
        else if (i === idx) s.classList.add('active');
    }
    // 更新进度条
    var bar = document.getElementById('progressBar');
    if (bar) {
        var pcts = [5, 15, 30, 55, 85, 100];
        bar.style.width = pcts[Math.min(idx, 5)] + '%';
    }
    // 更新百分比文字
    var pctEl = document.getElementById('progressPct');
    if (pctEl && idx >= 0) {
        pctEl.textContent = pcts[Math.min(idx, 5)] + '%';
    }
}

async function startPipeline() {
    var file = fileInput.files[0];
    if (!file) return showToast(t('toast_no_file'), 'error');

    configPanel.style.display = 'none';
    progressContainer.style.display = 'block';
    videoResult.style.display = 'none';

    var formData = new FormData();
    formData.append('file', file);
    formData.append('mode', currentMode);

    if (currentMode === 'auto') {
        formData.append('total_duration', document.getElementById('totalDuration').value);
    } else {
        formData.append('style_template', document.getElementById('styleTemplate').value);
        formData.append('duration_mode', document.getElementById('durationMode').value);
        formData.append('resolution', document.getElementById('resolution').value);
        formData.append('video_quality', document.getElementById('videoQuality').value);
        formData.append('auto_subtitle', document.getElementById('autoSubtitle').value);
        formData.append('auto_sfx', document.getElementById('autoSfx').value);
        formData.append('original_audio_level', document.getElementById('bgmVolume').value);
        formData.append('bgm_enabled', document.getElementById('bgmEnabled').value);
        formData.append('bgm_volume', document.getElementById('bgmVolumeSlider').value);
    }

    try {
        progressTitle.textContent = '正在上传...';
        progressText.textContent = '创建会话';
        updatePipelineStep('UPLOADED');

        var res = await fetch('/api/session/create', { method: 'POST', body: formData });
        var data = await res.json();
        if (!res.ok) throw new Error(data.error);
        currentSessionId = data.session_id;

        progressTitle.textContent = currentMode === 'auto' ? 'AI 全自动设计分镜...' : 'AI 分析文档、设计分镜...';
        progressText.textContent = currentMode === 'auto' ? 'DeepSeek V4 通读文档 → 完全自主设计镜头/风格/运镜/节奏'
            : 'DeepSeek V4 通读文档 → 自主设计镜头/时长/景别';
        updatePipelineStep('SHOTS_DESIGNED');
        res = await fetch('/api/session/' + currentSessionId + '/design-shots', { method: 'POST' });
        data = await res.json();
        if (!res.ok) throw new Error(data.error);
        showStats(data.shot_count, data.scene_count || '-', data.character_count || '-');
        // 保存分镜预览数据供后续步骤更新状态
        var shotsPreview = data.shots_preview || [];
        if (shotsPreview.length) renderShotsPreview(data);

        progressTitle.textContent = '生成 Prompts...';
        progressText.textContent = currentMode === 'auto' ? 'AI 自选风格 + 角色锚定 · 情绪弧线 · 叙事链'
            : '视觉圣经 + 角色锚定 · 情绪弧线 · 叙事链';
        updatePipelineStep('PROMPTS_READY');
        res = await fetch('/api/session/' + currentSessionId + '/prompts', { method: 'POST' });
        data = await res.json();
        if (!res.ok) throw new Error(data.error);

        progressTitle.textContent = '并行生成关键帧...';
        progressText.textContent = 'Seedream 5.0 文生图 · 场景级关键帧共享 · 并行加速';
        updatePipelineStep('IMAGES_GENERATED');
        // 标记所有镜头为"生成中"
        if (shotsPreview.length) {
            shotsPreview.forEach(function(s) { updateShotStatus(s.id, 'generating'); });
        }
        res = await fetch('/api/session/' + currentSessionId + '/images', { method: 'POST' });
        data = await res.json();
        if (!res.ok) throw new Error(data.error);
        // 更新镜头状态
        var failedIds = data.failed || [];
        shotsPreview.forEach(function(s) {
            updateShotStatus(s.id, failedIds.indexOf(s.id) >= 0 ? 'failed' : 'done');
        });
        if (data.failed.length > 0) showToast(data.failed.length + ' ' + t('toast_images_failed'), 'error');
        updateRetryAllBtn();

        progressTitle.textContent = '并行生成视频片段...';
        progressText.textContent = 'Seedance 2.0 图生视频 · 并行轮询下载';
        updatePipelineStep('VIDEOS_GENERATED');
        res = await fetch('/api/session/' + currentSessionId + '/videos', { method: 'POST' });
        data = await res.json();
        if (!res.ok) throw new Error(data.error);
        // 更新视频阶段失败的镜头
        (data.failed || []).forEach(function(sid) { updateShotStatus(sid, 'failed'); });
        if (data.failed.length > 0) showToast(data.failed.length + ' ' + t('toast_videos_failed'), 'error');
        updateRetryAllBtn();

        progressTitle.textContent = '合成最终视频...';
        progressText.textContent = 'Edge TTS 中文配音 + ffmpeg 合成';
        updatePipelineStep('COMPOSED');
        res = await fetch('/api/session/' + currentSessionId + '/compose', { method: 'POST' });
        data = await res.json();
        if (!res.ok) throw new Error(data.error);

        progressContainer.style.display = 'none';
        videoResult.style.display = 'block';
        resultVideo.src = data.videoUrl;
        resultVideo.load();
        showToast(t('toast_success'), 'success');

    } catch (err) {
        showToast(t('toast_generate_fail') + err.message, 'error');
        configPanel.style.display = 'block';
        progressContainer.style.display = 'none';
    }
}

// === 剪辑趋势面板 ===

var trendsToggle = document.getElementById('trendsToggle');
var trendsBody = document.getElementById('trendsBody');
var trendsChevron = document.getElementById('trendsChevron');

if (trendsToggle) {
  trendsToggle.addEventListener('click', function () {
    var isOpen = trendsBody.style.display !== 'none';
    trendsBody.style.display = isOpen ? 'none' : 'block';
    trendsChevron.style.transform = isOpen ? 'rotate(0deg)' : 'rotate(180deg)';
    if (!isOpen) loadTrends();
  });
}

async function loadTrends() {
  var dim = document.getElementById('trendsDimFilter')?.value || '';
  var search = document.getElementById('trendsSearch')?.value.trim() || '';
  var list = document.getElementById('trendsList');
  var badge = document.getElementById('trendsBadge');
  if (!list) return;

  list.innerHTML = '<div class="trends-empty">' + t('trends_loading') + '</div>';

  try {
    var url = '/api/trends?limit=12';
    if (dim) url += '&dimension=' + encodeURIComponent(dim);
    if (search) url += '&search=' + encodeURIComponent(search);

    var resp = await fetch(url, {
      headers: { 'X-Access-Token': localStorage.getItem('access_token') || '' }
    });

    if (!resp.ok) {
      list.innerHTML = '<div class="trends-empty">' + t('trends_error') + '</div>';
      return;
    }

    var data = await resp.json();

    if (badge) badge.textContent = data.length || '0';

    if (!data.length) {
      list.innerHTML = '<div class="trends-empty">' + t('trends_empty') + '</div>';
      return;
    }

    list.innerHTML = data.map(function(item) {
      var arrow = { rising: '↑', declining: '↓', stable: '→' }[item.trending_direction] || '→';
      var cls = item.trending_direction || 'stable';
      return '<div class="trend-card">' +
        '<div class="trend-card-dim">' + (item.dimension || '') + '</div>' +
        '<div class="trend-card-name">' + (item.category || '') + ' · ' + (item.subcategory || '') + '</div>' +
        '<div class="trend-card-meta">' +
          '<span class="trend-arrow ' + cls + '">' + arrow + '</span>' +
          '<span class="trend-count">' + (item.total_videos || 0) + ' ' + t('trends_videos') + '</span>' +
        '</div>' +
      '</div>';
    }).join('');

  } catch (e) {
    list.innerHTML = '<div class="trends-empty">' + t('trends_error') + '</div>';
  }
}

// 筛选变化监听
document.getElementById('trendsDimFilter')?.addEventListener('change', loadTrends);
var trendsSearchTimer;
document.getElementById('trendsSearch')?.addEventListener('input', function () {
  clearTimeout(trendsSearchTimer);
  trendsSearchTimer = setTimeout(loadTrends, 400);
});
