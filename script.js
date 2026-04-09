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
                    top: targetElement.offsetTop - 70, // 减去导航栏高度
                    behavior: 'smooth'
                });
            }
        });
    });

    // 导航栏滚动效果
    const navbar = document.querySelector('.navbar');
    window.addEventListener('scroll', function() {
        if (window.scrollY > 50) {
            navbar.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.1)';
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
        uploadArea.style.backgroundColor = '#f8f9fa';
        uploadArea.style.borderColor = '#2980b9';
    });

    uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        uploadArea.style.backgroundColor = '#fff';
        uploadArea.style.borderColor = '#3498db';
    });

    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadArea.style.backgroundColor = '#fff';
        uploadArea.style.borderColor = '#3498db';

        if (e.dataTransfer.files.length) {
            handleFile(e.dataTransfer.files[0]);
        }
    });

    // 文件选择处理
    fileInput.addEventListener('change', function() {
        if (this.files.length) {
            handleFile(this.files[0]);
        }
    });

    // 处理选中的文件
    function handleFile(file) {
        // 检查文件类型
        const validTypes = ['application/pdf', 'application/vnd.ms-powerpoint', 
                           'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                           'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                           'text/plain'];

        if (!validTypes.includes(file.type)) {
            alert('请上传PDF、PPT、PPTX、DOC、DOCX或TXT格式的文件');
            return;
        }

        // 显示文件信息
        fileName.textContent = file.name;
        fileSize.textContent = formatFileSize(file.size);

        // 切换显示区域
        uploadArea.style.display = 'none';
        fileInfo.style.display = 'flex';
        uploadOptions.style.display = 'block';
    }

    // 格式化文件大小
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // 移除文件
    removeFileBtn.addEventListener('click', function() {
        fileInput.value = '';
        uploadArea.style.display = 'block';
        fileInfo.style.display = 'none';
        uploadOptions.style.display = 'none';
        progressContainer.style.display = 'none';
        videoResult.style.display = 'none';
    });

    // 生成视频
    generateButton.addEventListener('click', async function() {
        console.log('🎬 生成视频按钮被点击');
        
        // 获取视频设置
        const aiModel = document.getElementById('aiModel').value;
        const videoStyle = document.getElementById('videoStyle').value;
        const videoDuration = document.getElementById('videoDuration').value;

        console.log('参数:', { aiModel, videoStyle, videoDuration });

        // 显示进度条
        uploadOptions.style.display = 'none';
        progressContainer.style.display = 'block';
        progressFill.style.width = '10%';
        progressText.textContent = '正在上传文件...';

        try {
            // 首先上传文件
            console.log('1️⃣  正在上传文件...');
            
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);

            const uploadResponse = await fetch('http://localhost:5000/api/upload', {
                method: 'POST',
                body: formData
            });

            console.log('上传响应状态:', uploadResponse.status);
            
            if (!uploadResponse.ok) {
                throw new Error('文件上传失败: ' + uploadResponse.status);
            }

            const uploadData = await uploadResponse.json();
            console.log('上传成功，文件名:', uploadData.filename);

            // 然后生成视频
            progressFill.style.width = '20%';
            progressText.textContent = '正在调用AI视频生成模型...';
            
            console.log('2️⃣  正在调用生成视频 API...');
            console.log('请求数据:', {
                aiModel: aiModel,
                videoStyle: videoStyle,
                videoDuration: videoDuration,
                filename: uploadData.filename
            });

            const generateResponse = await fetch('http://localhost:5000/api/generate-video', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    aiModel: aiModel,
                    videoStyle: videoStyle,
                    videoDuration: videoDuration,
                    filename: uploadData.filename
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
            progressFill.style.width = '40%';
            progressText.textContent = '正在分析文档内容...';

            // 模拟进度更新
            setTimeout(() => {
                progressFill.style.width = '60%';
                progressText.textContent = '正在生成视频...';
            }, 500);

            setTimeout(() => {
                progressFill.style.width = '80%';
                progressText.textContent = '正在处理视频...';
            }, 1000);

            setTimeout(() => {
                progressFill.style.width = '100%';
                progressText.textContent = '视频生成完成！';
                
                console.log('3️⃣  视频生成完成，显示结果');

                // 显示视频结果
                setTimeout(() => {
                    progressContainer.style.display = 'none';
                    videoResult.style.display = 'block';

                    // 设置视频源
                    resultVideo.src = `http://localhost:5000${generateData.videoUrl}`;
                    resultVideo.load();
                    
                    console.log('✅ 视频已准备就绪:', resultVideo.src);
                }, 300);
            }, 1500);

        } catch (error) {
            console.error('❌ 生成视频时出错:', error);
            alert('生成视频时出错: ' + error.message);

            // 重置界面
            progressContainer.style.display = 'none';
            uploadOptions.style.display = 'block';
        }
    });

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
        alert('在实际应用中，这里会打开分享选项。');
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