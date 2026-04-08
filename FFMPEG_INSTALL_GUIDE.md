# FFmpeg安装指南（Windows）

## 方法一：手动安装（推荐）

### 步骤1：下载FFmpeg

1. 访问FFmpeg官方构建页面：https://www.gyan.dev/ffmpeg/builds/
2. 下载最新版本的"ffmpeg-git-full.7z"（这是一个完整的构建，包含所有功能）
3. 等待下载完成

### 步骤2：解压文件

1. 找到下载的.7z文件
2. 如果您的系统没有安装7-Zip，请先下载安装：https://www.7-zip.org/
3. 使用7-Zip解压文件到一个目录，例如：`C:\ffmpeg`

### 步骤3：配置环境变量

1. 右键点击"此电脑"（或"我的电脑"），选择"属性"
2. 点击"高级系统设置"
3. 点击"环境变量"按钮
4. 在"系统变量"部分，找到"Path"变量，然后点击"编辑"
5. 点击"新建"，然后添加FFmpeg的bin目录路径，例如：`C:\ffmpeg\bin`
6. 点击"确定"保存所有更改

### 步骤4：验证安装

1. 打开一个新的命令提示符窗口（重要：必须打开新的窗口才能使环境变量生效）
2. 输入以下命令：
   ```
   ffmpeg -version
   ```
3. 如果看到FFmpeg的版本信息，说明安装成功

## 方法二：使用Chocolatey安装（如果已安装）

如果您已经安装了Chocolatey包管理器，可以使用以下命令安装FFmpeg：

```powershell
choco install ffmpeg
```

## 方法三：使用Scoop安装（如果已安装）

如果您已经安装了Scoop包管理器，可以使用以下命令安装FFmpeg：

```powershell
scoop install ffmpeg
```

## 常见问题

### Q1: 安装后仍然提示"无法识别ffmpeg命令"怎么办？

A: 请确保：
1. 您添加的是FFmpeg的bin目录路径（例如：C:\ffmpeg\bin），而不是FFmpeg的根目录
2. 您已经打开了新的命令提示符窗口
3. 您没有输入错误的路径

### Q2: 如何找到FFmpeg的bin目录？

A: 解压FFmpeg后，在解压目录中找到名为"bin"的文件夹，这个文件夹的完整路径就是您需要添加到环境变量中的路径。

### Q3: 安装后如何验证FFmpeg是否正常工作？

A: 在命令提示符中运行`ffmpeg -version`，如果看到版本信息，说明安装成功。您也可以尝试运行以下命令测试视频转换功能：

```bash
ffmpeg -version
ffmpeg -formats
```

### Q4: 我需要管理员权限来修改环境变量吗？

A: 是的，修改系统环境变量需要管理员权限。如果您没有管理员权限，可以：
1. 联系您的系统管理员
2. 或者将FFmpeg放在您的项目目录中，并在代码中指定FFmpeg的路径

## 完成安装后的下一步

安装完FFmpeg后，您可以：
1. 运行`pip install -r requirements.txt`安装Python依赖
2. 运行`python app.py`启动项目
3. 在浏览器中打开index.html文件开始使用
