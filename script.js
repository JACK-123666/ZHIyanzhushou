var ALLOWED_EXTENSIONS = ['.docx', '.txt'];
var FORMAT_SIZES = ['Bytes', 'KB', 'MB', 'GB'];
var PIPELINE_STEPS = ['UPLOADED', 'PARSED', 'PROMPTS_READY', 'IMAGES_GENERATED', 'VIDEOS_GENERATED', 'COMPOSED'];
var currentSessionId = null;

function showToast(msg, type) {
    type = type || 'info';
    var c = document.getElementById('toastContainer');
    var t = document.createElement('div');
    t.className = 'toast ' + type;
    t.textContent = msg;
    c.appendChild(t);
    setTimeout(function () { t.remove(); }, 3000);
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
var videoResult = document.getElementById('videoResult');
var resultVideo = document.getElementById('resultVideo');
var downloadBtn = document.getElementById('downloadBtn');
var newVideoBtn = document.getElementById('newVideoBtn');

document.addEventListener('DOMContentLoaded', function () {
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
});

function handleFile(file) {
    var ext = '.' + file.name.split('.').pop().toLowerCase();
    if (ALLOWED_EXTENSIONS.indexOf(ext) === -1) {
        showToast('仅支持 .docx 或 .txt 格式', 'error');
        return;
    }
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    uploadArea.style.display = 'none';
    fileInfo.style.display = 'flex';
    configPanel.style.display = 'block';
    videoResult.style.display = 'none';
}

function resetAll() {
    fileInput.value = '';
    uploadArea.style.display = 'block';
    fileInfo.style.display = 'none';
    configPanel.style.display = 'none';
    progressContainer.style.display = 'none';
    videoResult.style.display = 'none';
    currentSessionId = null;
    for (var i = 1; i <= 6; i++) {
        var s = document.getElementById('pstep' + i);
        if (s) { s.className = 'pipeline-step'; }
    }
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
}

async function startPipeline() {
    var file = fileInput.files[0];
    if (!file) return showToast('请先选择文件', 'error');

    configPanel.style.display = 'none';
    progressContainer.style.display = 'block';
    videoResult.style.display = 'none';

    var formData = new FormData();
    formData.append('file', file);
    formData.append('style_template', document.getElementById('styleTemplate').value);
    formData.append('duration_mode', document.getElementById('durationMode').value);
    formData.append('consistency_strategy', document.getElementById('consistencyStrategy').value);
    formData.append('resolution', document.getElementById('resolution').value);
    formData.append('auto_subtitle', document.getElementById('autoSubtitle').value);
    formData.append('auto_sfx', document.getElementById('autoSfx').value);
    formData.append('bgm_volume', document.getElementById('bgmVolume').value);

    try {
        progressTitle.textContent = '正在上传...';
        progressText.textContent = '创建会话';
        updatePipelineStep('UPLOADED');

        var res = await fetch('/api/session/create', { method: 'POST', body: formData });
        var data = await res.json();
        if (!res.ok) throw new Error(data.error);
        currentSessionId = data.session_id;

        progressTitle.textContent = 'AI 解析分镜脚本...';
        progressText.textContent = 'DeepSeek 正在提取分镜结构';
        updatePipelineStep('PARSED');
        res = await fetch('/api/session/' + currentSessionId + '/parse', { method: 'POST' });
        data = await res.json();
        if (!res.ok) throw new Error(data.error);

        progressTitle.textContent = '生成 Prompts...';
        progressText.textContent = '为 ' + data.shot_count + ' 个镜头生成图文 Prompt';
        updatePipelineStep('PROMPTS_READY');
        res = await fetch('/api/session/' + currentSessionId + '/prompts', { method: 'POST' });
        data = await res.json();
        if (!res.ok) throw new Error(data.error);

        progressTitle.textContent = '生成关键帧图片...';
        progressText.textContent = 'Seedream 文生图 (场景级共享，减少消耗)';
        updatePipelineStep('IMAGES_GENERATED');
        res = await fetch('/api/session/' + currentSessionId + '/images', { method: 'POST' });
        data = await res.json();
        if (!res.ok) throw new Error(data.error);
        if (data.failed.length > 0) showToast(data.failed.length + ' 个场景生成失败', 'error');

        progressTitle.textContent = '生成视频片段...';
        progressText.textContent = 'Seedance 图生视频';
        updatePipelineStep('VIDEOS_GENERATED');
        res = await fetch('/api/session/' + currentSessionId + '/videos', { method: 'POST' });
        data = await res.json();
        if (!res.ok) throw new Error(data.error);
        if (data.failed.length > 0) showToast(data.failed.length + ' 个镜头视频生成失败', 'error');

        progressTitle.textContent = '合成最终视频...';
        progressText.textContent = 'TTS 配音 + 拼接';
        updatePipelineStep('COMPOSED');
        res = await fetch('/api/session/' + currentSessionId + '/compose', { method: 'POST' });
        data = await res.json();
        if (!res.ok) throw new Error(data.error);

        progressContainer.style.display = 'none';
        videoResult.style.display = 'block';
        resultVideo.src = data.videoUrl;
        resultVideo.load();
        showToast('视频生成完成！', 'success');

    } catch (err) {
        showToast('生成失败: ' + err.message, 'error');
        configPanel.style.display = 'block';
        progressContainer.style.display = 'none';
    }
}
