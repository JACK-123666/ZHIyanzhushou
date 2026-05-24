// --- 常量 ---
const ALLOWED_EXTENSIONS = ['.pdf', '.pptx', '.docx', '.txt'];
const FORMAT_SIZES = ['Bytes', 'KB', 'MB', 'GB'];

// --- Toast ---
function showToast(message, type) {
    type = type || 'info';
    var container = document.getElementById('toastContainer');
    var toast = document.createElement('div');
    toast.className = 'toast ' + type;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(function () { toast.remove(); }, 3000);
}

// --- 工具函数 ---
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    var k = 1024;
    var i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + FORMAT_SIZES[i];
}

// --- DOM 引用 ---
var uploadArea = document.getElementById('uploadArea');
var fileInput = document.getElementById('fileInput');
var fileInfo = document.getElementById('fileInfo');
var fileName = document.getElementById('fileName');
var fileSize = document.getElementById('fileSize');
var removeFileBtn = document.getElementById('removeFile');
var uploadOptions = document.getElementById('uploadOptions');
var generateButton = document.getElementById('generateButton');
var progressContainer = document.getElementById('progressContainer');
var progressFill = document.getElementById('progressFill');
var progressText = document.getElementById('progressText');
var progressPercentage = document.getElementById('progressPercentage');
var videoResult = document.getElementById('videoResult');
var resultVideo = document.getElementById('resultVideo');
var downloadButton = document.querySelector('.download-button');
var shareButton = document.querySelector('.share-button');
var newVideoButton = document.querySelector('.new-video-button');

// --- 事件绑定 ---
document.addEventListener('DOMContentLoaded', function () {
    // CTA 按钮
    var ctaButton = document.getElementById('ctaButton');
    if (ctaButton) ctaButton.addEventListener('click', scrollToUpload);

    // 平滑滚动
    document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            var target = document.querySelector(this.getAttribute('href'));
            if (target) window.scrollTo({ top: target.offsetTop - 70, behavior: 'smooth' });
        });
    });

    // 导航栏阴影
    var navbar = document.querySelector('.navbar');
    window.addEventListener('scroll', function () {
        navbar.style.boxShadow = window.scrollY > 50
            ? '0 4px 12px rgba(0, 0, 0, 0.15)'
            : '0 2px 5px rgba(0, 0, 0, 0.1)';
    });

    // 特性卡片动画
    var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

    document.querySelectorAll('.feature-card').forEach(function (card) {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(card);
    });

    // 上传区域点击
    uploadArea.addEventListener('click', function () { fileInput.click(); });

    // 拖拽上传
    uploadArea.addEventListener('dragover', function (e) {
        e.preventDefault();
        uploadArea.style.backgroundColor = 'rgba(52, 152, 219, 0.05)';
        uploadArea.style.borderColor = '#3498db';
    });
    uploadArea.addEventListener('dragleave', function (e) {
        e.preventDefault();
        uploadArea.style.backgroundColor = '';
        uploadArea.style.borderColor = '';
    });
    uploadArea.addEventListener('drop', function (e) {
        e.preventDefault();
        uploadArea.style.backgroundColor = '';
        uploadArea.style.borderColor = '';
        if (e.dataTransfer.files.length > 0) handleFile(e.dataTransfer.files[0]);
    });

    // 文件选择
    fileInput.addEventListener('change', function () {
        if (fileInput.files.length > 0) handleFile(fileInput.files[0]);
    });

    // 移除文件
    removeFileBtn.addEventListener('click', resetUpload);

    // 生成视频
    generateButton.addEventListener('click', generateVideoHandler);

    // 下载
    downloadButton.addEventListener('click', function () {
        if (!resultVideo.src) return showToast('没有可下载的视频', 'error');
        var link = document.createElement('a');
        link.href = resultVideo.src;
        link.download = 'generated_video_' + Date.now() + '.mp4';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    });

    // 分享
    shareButton.addEventListener('click', function () {
        if (!resultVideo.src) return showToast('没有可分享的视频', 'error');
        navigator.clipboard.writeText(window.location.origin + resultVideo.src)
            .then(function () { showToast('视频链接已复制到剪贴板', 'success'); })
            .catch(function () { showToast('复制失败，请手动复制链接', 'error'); });
    });

    // 生成新视频
    newVideoButton.addEventListener('click', resetAll);
});

// --- 文件处理 ---
function handleFile(file) {
    var ext = '.' + file.name.split('.').pop().toLowerCase();
    if (ALLOWED_EXTENSIONS.indexOf(ext) === -1) {
        showToast('不支持的文件格式，请上传 PDF/PPTX/DOCX/TXT', 'error');
        return;
    }
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    uploadArea.style.display = 'none';
    fileInfo.style.display = 'flex';
    uploadOptions.style.display = 'block';
    videoResult.style.display = 'none';
}

function resetUpload() {
    fileInput.value = '';
    uploadArea.style.display = 'block';
    fileInfo.style.display = 'none';
    uploadOptions.style.display = 'none';
    videoResult.style.display = 'none';
    progressContainer.style.display = 'none';
}

function resetAll() {
    resetUpload();
    for (var i = 1; i <= 4; i++) {
        var step = document.getElementById('step' + i);
        if (step) step.classList.remove('active');
    }
}

// --- 视频生成 ---
function generateVideoHandler() {
    var file = fileInput.files[0];
    if (!file) return showToast('请先选择一个文件', 'error');

    var aiModel = document.getElementById('aiModel').value;
    var videoStyle = document.getElementById('videoStyle').value;
    var videoDuration = document.getElementById('videoDuration').value;
    var narrator = document.getElementById('narrator').value;

    uploadOptions.style.display = 'none';
    progressContainer.style.display = 'block';
    updateProgress(0, '正在上传文件...');
    updateStep(1);

    var formData = new FormData();
    formData.append('file', file);

    fetch('/api/upload', { method: 'POST', body: formData })
        .then(function (res) {
            if (!res.ok) return res.json().then(function (d) { throw new Error(d.error || '上传失败'); });
            return res.json();
        })
        .then(function (uploadData) {
            updateProgress(30, '正在生成专业的AI视频prompt...');
            updateStep(2);

            return fetch('/api/generate-video', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    aiModel: aiModel,
                    videoStyle: videoStyle,
                    videoDuration: videoDuration,
                    narrator: narrator,
                    filename: uploadData.filename,
                    fileType: 'document'
                })
            });
        })
        .then(function (res) {
            if (!res.ok) return res.json().then(function (d) { throw new Error(d.error || '视频生成失败'); });
            return res.json();
        })
        .then(function (data) {
            updateProgress(100, '视频生成完成！');
            updateStep(4);

            setTimeout(function () {
                progressContainer.style.display = 'none';
                videoResult.style.display = 'block';
                resultVideo.src = data.videoUrl;
                resultVideo.load();
            }, 500);
        })
        .catch(function (err) {
            showToast('生成视频时出错：' + err.message, 'error');
            progressContainer.style.display = 'none';
            uploadOptions.style.display = 'block';
        });
}

// --- 进度条 ---
function updateProgress(percentage, text) {
    progressFill.style.width = percentage + '%';
    progressPercentage.textContent = percentage + '%';
    if (text) progressText.textContent = text;
}

function updateStep(stepNumber) {
    for (var i = 1; i <= 4; i++) {
        var step = document.getElementById('step' + i);
        if (step) step.classList.remove('active');
    }
    var current = document.getElementById('step' + stepNumber);
    if (current) current.classList.add('active');
}

// --- 滚动 ---
function scrollToUpload() {
    var section = document.querySelector('#upload');
    if (section) window.scrollTo({ top: section.offsetTop - 70, behavior: 'smooth' });
}
