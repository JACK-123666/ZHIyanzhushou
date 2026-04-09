# GitHub 部署和更新指南

## 一、首次部署到 GitHub

### 1. 创建 GitHub 仓库

1. 访问 https://github.com
2. 登录您的账号
3. 点击右上角的 "+" 号，选择 "New repository"
4. 填写仓库信息：
   - Repository name: `simple_webpage`（或您喜欢的名字）
   - Description: AI视频生成平台
   - 选择 Public（公开）或 Private（私有）
5. 点击 "Create repository"

### 2. 初始化本地 Git 仓库

在项目目录下打开命令行，执行：

```bash
cd d:/PYTHON/simple_webpage
git init
```

### 3. 添加文件到 Git

```bash
git add .
```

### 4. 创建首次提交

```bash
git commit -m "Initial commit: AI视频生成平台"
```

### 5. 连接到 GitHub 仓库

将下面的 `YOUR_USERNAME` 替换为您的 GitHub 用户名，`simple_webpage` 替换为您的仓库名：

```bash
git remote add origin https://github.com/YOUR_USERNAME/simple_webpage.git
```

### 6. 推送到 GitHub

```bash
git branch -M main
git push -u origin main
```

## 二、更新仓库

### 方法一：使用命令行更新

1. 查看修改的文件：
```bash
git status
```

2. 添加修改的文件：
```bash
git add .
```

3. 提交修改：
```bash
git commit -m "更新描述"
```

4. 推送到 GitHub：
```bash
git push
```

### 方法二：使用 GitHub Desktop（推荐新手）

1. 下载并安装 GitHub Desktop：https://desktop.github.com/
2. 登录您的 GitHub 账号
3. File -> Add Local Repository，选择项目目录
4. 在左侧面板查看修改
5. 填写提交描述，点击 "Commit to main"
6. 点击 "Push origin" 推送到 GitHub

## 三、自动化部署方案

### 方案一：使用 Vercel 部署（推荐）

1. 访问 https://vercel.com
2. 使用 GitHub 账号登录
3. 点击 "Add New..." -> "Project"
4. 选择您的 GitHub 仓库
5. 配置项目设置：
   - Framework Preset: Python
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python app.py`
6. 点击 "Deploy"

**自动更新**：
- 每次推送到 GitHub，Vercel 会自动重新部署
- 无需手动操作

### 方案二：使用 Render 部署

1. 访问 https://render.com
2. 使用 GitHub 账号登录
3. 点击 "New +" -> "Web Service"
4. 连接您的 GitHub 仓库
5. 配置：
   - Name: simple-webpage
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python app.py`
6. 点击 "Create Web Service"

**自动更新**：
- 推送到 GitHub 后，Render 会自动检测并重新部署
- 也可以在控制台手动触发部署

### 方案三：使用 Railway 部署

1. 访问 https://railway.app
2. 使用 GitHub 账号登录
3. 点击 "New Project" -> "Deploy from GitHub repo"
4. 选择您的仓库
5. Railway 会自动检测 Python 项目
6. 点击 "Deploy Now"

**自动更新**：
- 推送到 GitHub 后，Railway 会自动部署

## 四、常见问题

### Q1: 推送时提示 "Authentication failed"

A: 需要配置 Git 凭证：
```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### Q2: 如何查看提交历史？

A: 使用命令：
```bash
git log --oneline
```

### Q3: 如何回退到之前的版本？

A: 使用命令：
```bash
git log --oneline  # 查看提交历史
git reset --hard <commit-hash>  # 回退到指定版本
git push -f  # 强制推送（谨慎使用）
```

### Q4: 如何删除远程仓库？

A: 在 GitHub 网站上：
1. 进入仓库页面
2. 点击 "Settings"
3. 滚动到底部，找到 "Danger Zone"
4. 点击 "Delete this repository"

### Q5: 如何配置环境变量？

A: 在部署平台（Vercel/Render/Railway）中：
1. 进入项目设置
2. 找到 "Environment Variables"
3. 添加您的 API 密钥

## 五、最佳实践

1. **提交信息规范**：
   - 使用清晰、简洁的提交信息
   - 例如：`"优化大文件处理"`、`"添加新功能"`

2. **分支管理**：
   - main 分支用于生产环境
   - 开发新功能时创建新分支
   - 完成后合并到 main

3. **定期更新**：
   - 定期推送代码到 GitHub
   - 保持代码备份

4. **版本标签**：
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

## 六、快速参考

```bash
# 初始化仓库
git init

# 添加文件
git add .

# 提交
git commit -m "提交信息"

# 连接远程仓库
git remote add origin <仓库URL>

# 推送
git push -u origin main

# 拉取更新
git pull

# 查看状态
git status

# 查看历史
git log --oneline
```

祝您使用愉快！