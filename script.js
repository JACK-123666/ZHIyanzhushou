// 等待DOM加载完成
document.addEventListener('DOMContentLoaded', function() {
    // CTA按钮点击处理
    const ctaButton = document.getElementById('ctaButton');
    if (ctaButton) {
        ctaButton.addEventListener('click', scrollToUpload);
    }

    // 平滑滚动到锚点
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();

            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);

            if (targetElement) {
                window.scrollTo({
                    top: targetElement.offsetTop - 70,
                    behavior: 'smooth'
                });
            }
        });
    });

    // 导航栏滚动效果
    const navbar = document.querySelector('.navbar');
    window.addEventListener('scroll', function() {
        if (window.scrollY > 50) {
            navbar.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)';
        } else {
            navbar.style.boxShadow = '0 2px 5px rgba(0, 0, 0, 0.1)';
        }
    });

    // 特性卡片动画效果
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    document.querySelectorAll('.feature-card').forEach(card => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(card);
    });

    // 文件上传功能
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const uploadButton = document.querySelector('.upload-button');
    const fileInfo = document.getElementById('fileInfo');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const removeFileBtn = document.getElementById('removeFile');
    const uploadOptions = document.getElementById('uploadOptions');
    const generateButton = document.getElementById('generateButton');
    const progressContainer = document.getElementById('progressContainer');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    const progressPercentage = document.getElementById('progressPercentage');
    const videoResult = document.getElementById('videoResult');
    const resultVideo = document.getElementById('resultVideo');
    const downloadButton = document.querySelector('.download-button');
    const shareButton = document.querySelector('.share-button');
    const newVideoButton = document.querySelector('.new-video-button');

    // 点击上传区域或按钮触发文件选择
    uploadArea.addEventListener('click', function() {
        fileInput.click();
    });

    uploadButton.addEventListener('click', function(e) {
        e.stopPropagation();
        fileInput.click();
    });

    // 拖拽上传
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadArea.style.backgroundColor = 'rgba(52, 152, 219, 0.05)';
        uploadArea.style.borderColor = '#3498db';
    });

    uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        uploadArea.style.backgroundColor = '';
        uploadArea.style.borderColor = '';
    });

    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadArea.style.backgroundColor = '';
        uploadArea.style.borderColor = '';

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFile(files[0]);
        }
    });

    // 文件选择处理
    fileInput.addEventListener('change', function(e) {
        const files = e.target.files;
        if (files.length > 0) {
            handleFile(files[0]);
        }
    });

    // 处理文件
    function handleFile(file) {
        // 验证文件类型
        const allowedTypes = [
            'application/pdf',
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
            'audio/wav',
            'audio/mpeg',
            'audio/ogg',
            'audio/webm'
        ];

        const allowedExtensions = ['.pdf', '.ppt', '.pptx', '.doc', '.docx', '.txt', '.wav', '.mp3', '.ogg', '.webm'];
        const fileExtension = '.' + file.name.split('.').pop().toLowerCase();

        if (!allowedExtensions.includes(fileExtension)) {
            alert('不支持的文件格式。请上传PDF、PPT、Word、TXT或音频文件。');
            return;
        }

        // 显示文件信息
        fileName.textContent = file.name;
        fileSize.textContent = formatFileSize(file.size);
        uploadArea.style.display = 'none';
        fileInfo.style.display = 'flex';
        uploadOptions.style.display = 'block';
        videoResult.style.display = 'none';
    }

    // 格式化文件大小
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    // 移除文件
    removeFileBtn.addEventListener('click', function() {
        fileInput.value = '';
        uploadArea.style.display = 'block';
        fileInfo.style.display = 'none';
        uploadOptions.style.display = 'none';
        videoResult.style.display = 'none';
        progressContainer.style.display = 'none';
    });

    // 生成视频按钮
    generateButton.addEventListener('click', async function() {
        const file = fileInput.files[0];
        if (!file) {
            alert('请先选择一个文件');
            return;
        }

        const aiModel = document.getElementById('aiModel').value;
        const videoStyle = document.getElementById('videoStyle').value;
        const videoDuration = document.getElementById('videoDuration').value;
        const narrator = document.getElementById('narrator').value;

        console.log('1️⃣  开始上传文件...');
        console.log('文件信息:', {
            name: file.name,
            size: file.size,
            type: file.type
        });

        try {
            // 显示进度条
            uploadOptions.style.display = 'none';
            progressContainer.style.display = 'block';
            updateProgress(0, '正在上传文件...');
            updateStep(1);

            // 上传文件
            const formData = new FormData();
            formData.append('file', file);

            const uploadResponse = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            if (!uploadResponse.ok) {
                throw new Error('文件上传失败: ' + uploadResponse.status);
            }

            const uploadData = await uploadResponse.json();
            console.log('上传成功，文件名:', uploadData.filename);

            // 更新进度
            updateProgress(30, '正在生成专业的AI视频prompt...');
            updateStep(2);

            console.log('2️⃣  正在调用生成视频 API...');
            console.log('请求数据:', {
                aiModel: aiModel,
                videoStyle: videoStyle,
                videoDuration: videoDuration,
                narrator: narrator,
                filename: uploadData.filename
            });

            const generateResponse = await fetch('/api/generate-video', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    aiModel: aiModel,
                    videoStyle: videoStyle,
                    videoDuration: videoDuration,
                    narrator: narrator,
                    filename: uploadData.filename,
                    fileType: uploadData.fileType || 'document'
                })
            });

            console.log('生成响应状态:', generateResponse.status);

            if (!generateResponse.ok) {
                const errorText = await generateResponse.text();
                console.error('生成失败响应:', errorText);
                throw new Error('视频生成失败: ' + generateResponse.status + ' - ' + errorText);
            }

            const generateData = await generateResponse.json();
            console.log('视频生成成功:', generateData);

            // 更新进度
            updateProgress(100, '视频生成完成！');
            updateStep(4);

            console.log('3️⃣  视频生成完成，显示结果');

            // 显示视频结果
            setTimeout(() => {
                progressContainer.style.display = 'none';
                videoResult.style.display = 'block';

                // 设置视频源
                resultVideo.src = generateData.videoUrl;
                resultVideo.load();

                // 确保视频控件正确初始化
                resultVideo.addEventListener('loadedmetadata', function() {
                    console.log('✅ 视频元数据已加载，时长:', resultVideo.duration);
                });

                resultVideo.addEventListener('canplay', function() {
                    console.log('✅ 视频可以播放');
                });

                // 修复音频控制按钮
                fixAudioControls();

                console.log('✅ 视频已准备就绪:', resultVideo.src);
            }, 500);

        } catch (error) {
            console.error('❌ 生成视频时出错:', error);

            // 解析错误信息
            let errorMessage = error.message;
            if (errorMessage.includes('不支持旧的 .doc')) {
                errorMessage = '不支持旧的 .doc 二进制格式，请将文件转换为 .docx 格式后重试';
            } else if (errorMessage.includes('无法读取Word')) {
                errorMessage = '无法读取Word文档，请确保文件格式正确（推荐使用 .docx 格式）';
            } else if (errorMessage.includes('500')) {
                errorMessage = '服务器处理出错，请检查文件格式并重试';
            }

            alert('生成视频时出错：' + errorMessage);

            // 重置界面
            progressContainer.style.display = 'none';
            uploadOptions.style.display = 'block';
        }
    });

    // 更新进度条
    function updateProgress(percentage, text) {
        progressFill.style.width = percentage + '%';
        progressPercentage.textContent = percentage + '%';
        if (text) {
            progressText.textContent = text;
        }
    }

    // 更新步骤指示器
    function updateStep(stepNumber) {
        // 移除所有步骤的active类
        for (let i = 1; i <= 4; i++) {
            const step = document.getElementById('step' + i);
            if (step) {
                step.classList.remove('active');
            }
        }
        // 添加当前步骤的active类
        const currentStep = document.getElementById('step' + stepNumber);
        if (currentStep) {
            currentStep.classList.add('active');
        }
    }

    // 修复音频控制按钮
    function fixAudioControls() {
        if (!resultVideo) return;

        // 确保视频控件正确显示
        resultVideo.controls = true;

        // 添加音量控制事件监听
        resultVideo.addEventListener('volumechange', function() {
            console.log('音量已更改:', resultVideo.volume);
        });

        // 添加播放/暂停事件监听
        resultVideo.addEventListener('play', function() {
            console.log('视频开始播放');
        });

        resultVideo.addEventListener('pause', function() {
            console.log('视频暂停');
        });

        // 确保音量控制按钮可用
        const volumeButton = resultVideo.querySelector('button[aria-label*="音量"]') || 
                          resultVideo.querySelector('button[title*="音量"]');
        if (volumeButton) {
            volumeButton.style.display = 'block';
            volumeButton.disabled = false;
        }
    }

    // 下载视频
    downloadButton.addEventListener('click', function() {
        const videoSrc = resultVideo.src;
        if (!videoSrc) {
            alert('没有可下载的视频');
            return;
        }

        // 创建下载链接
        const link = document.createElement('a');
        link.href = videoSrc;
        link.download = `generated_video_${Date.now()}.mp4`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    });

    // 分享视频
    shareButton.addEventListener('click', function() {
        const videoSrc = resultVideo.src;
        if (!videoSrc) {
            alert('没有可分享的视频');
            return;
        }

        // 复制视频链接到剪贴板
        navigator.clipboard.writeText(window.location.origin + videoSrc)
            .then(() => {
                alert('视频链接已复制到剪贴板！');
            })
            .catch(err => {
                console.error('复制失败:', err);
                alert('复制链接失败，请手动复制地址栏中的链接');
            });
    });

    // 生成新视频
    newVideoButton.addEventListener('click', function() {
        // 重置界面
        videoResult.style.display = 'none';
        uploadArea.style.display = 'block';
        fileInfo.style.display = 'none';
        uploadOptions.style.display = 'none';
        progressContainer.style.display = 'none';
        fileInput.value = '';

        // 重置步骤指示器
        for (let i = 1; i <= 4; i++) {
            const step = document.getElementById('step' + i);
            if (step) {
                step.classList.remove('active');
            }
        }
    });
});

// 滚动到上传区域
function scrollToUpload() {
    const uploadSection = document.querySelector('#upload');
    if (uploadSection) {
        window.scrollTo({
            top: uploadSection.offsetTop - 70,
            behavior: 'smooth'
        });
    }
}
