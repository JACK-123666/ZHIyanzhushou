# GitHub Pages 部署指南

本指南将帮助您将项目部署到GitHub Pages，实现静态网页部署。

## 前提条件

1. 已创建GitHub账号
2. 已创建GitHub仓库
3. 已安装Git（如果尚未安装，请访问 https://git-scm.com/downloads 下载安装）

## 部署步骤

### 步骤1：初始化Git仓库

在项目目录中打开PowerShell或命令提示符，运行以下命令：

```bash
cd d:/PYTHON/simple_webpage
git init
```

### 步骤2：添加所有文件到Git

```bash
git add .
```

### 步骤3：创建首次提交

```bash
git commit -m "Initial commit"
```

### 步骤4：连接到GitHub仓库

将`YOUR_USERNAME`和`YOUR_REPO_NAME`替换为您的GitHub用户名和仓库名：

```bash
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
```

### 步骤5：推送到GitHub

```bash
git branch -M main
git push -u origin main
```

### 步骤6：启用GitHub Pages

1. 访问您的GitHub仓库页面
2. 点击"Settings"标签
3. 在左侧菜单中找到"Pages"
4. 在"Source"部分，选择"Deploy from a branch"
5. 在"Branch"下拉菜单中，选择"main"分支和"/ (root)"目录
6. 点击"Save"按钮
7. 等待几分钟，GitHub会自动部署您的网站

### 步骤7：访问您的网站

部署完成后，GitHub会提供一个URL，格式如下：
```
https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/
```

您可以通过这个URL访问您的网站。

## 注意事项

### 关于后端API

由于GitHub Pages只支持静态网站托管，不支持后端服务，因此：

1. **前端页面可以部署**：index.html、styles.css和script.js等前端文件可以正常部署
2. **后端服务需要单独部署**：app.py需要部署到支持Python的服务器上，如：
   - Heroku
   - Render
   - Railway
   - PythonAnywhere
   - AWS Elastic Beanstalk
   - Google Cloud Run

### 前后端分离部署

如果您想使用GitHub Pages托管前端，同时使用其他服务托管后端，需要：

1. 修改script.js中的API地址，将：
   ```javascript
   const uploadResponse = await fetch('http://localhost:5000/api/upload', {
   ```
   改为：
   ```javascript
   const uploadResponse = await fetch('YOUR_BACKEND_API_URL/api/upload', {
   ```

2. 确保后端服务配置了CORS，允许来自GitHub Pages的跨域请求

## 完整部署方案

如果您想完整部署整个项目（前端+后端），建议使用以下平台之一：

### 选项1：使用Render（推荐）

1. 创建Render账号：https://render.com/
2. 创建新的"Web Service"
3. 连接您的GitHub仓库
4. 配置以下设置：
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python app.py`
5. 点击"Create Web Service"
6. Render会自动部署您的应用

### 选项2：使用Heroku

1. 创建Heroku账号：https://signup.heroku.com/
2. 安装Heroku CLI
3. 登录Heroku：`heroku login`
4. 创建应用：`heroku create your-app-name`
5. 部署应用：`git push heroku main`

### 选项3：使用PythonAnywhere

1. 创建PythonAnywhere账号：https://www.pythonanywhere.com/
2. 创建新的Web应用
3. 配置Python版本和WSGI文件
4. 上传代码或连接GitHub仓库
5. 安装依赖：`pip install -r requirements.txt`
6. 配置静态文件
7. 启动应用

## 更新部署

当您对代码进行修改后，使用以下命令更新部署：

```bash
git add .
git commit -m "Your commit message"
git push
```

GitHub Pages会自动重新部署您的网站。

## 常见问题

### Q1: 部署后网页无法访问？

A: 请检查：
1. GitHub Pages设置是否正确
2. 是否等待了足够的时间（通常需要几分钟）
3. 仓库是否是公开的

### Q2: 如何自定义域名？

A: 在GitHub Pages设置中，可以添加自定义域名，并按照提示配置DNS记录。

### Q3: 如何查看部署状态？

A: 在仓库的"Actions"标签中，可以查看GitHub Pages的部署状态和日志。

## 参考资源

- GitHub Pages官方文档：https://docs.github.com/en/pages
- Git官方文档：https://git-scm.com/doc
