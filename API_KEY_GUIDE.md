# AI视频生成模型API密钥配置指南

本文档详细介绍了如何获取和配置国内免费AI视频生成模型的API密钥。

## 目录

1. [Seedance (字节跳动)](#seedance-字节跳动)
2. [RunwayML Gen-2 (国内版)](#runwayml-gen-2-国内版)
3. [Pika Labs (国内版)](#pika-labs-国内版)

---

## Seedance (字节跳动)

### 获取API密钥步骤

1. 访问火山引擎：https://www.volcengine.com/
2. 注册/登录火山引擎账号
3. 进入"火山引擎控制台"
4. 选择"模型推理"服务
5. 创建推理端点：
   - 点击"创建推理端点"按钮
   - 选择模型：Seedance
   - 填写端点名称和描述
   - 点击"确定"创建
6. 获取API Key和端点ID

### 配置方法

在`app.py`文件中，找到Seedance的配置部分：

```python
'seedance': {
    'name': 'Seedance (字节跳动)',
    'api_url': 'https://ark.cn-beijing.volces.com/api/v3/chat/completions',
    'api_key': os.environ.get('SEEDANCE_API_KEY', 'YOUR_SEEDANCE_API_KEY'),
    'model': 'ep-20240601111111-xxxxx',  # 需要替换为实际的端点ID
    'description': '字节跳动旗下的AI视频生成引擎'
},
```

将`YOUR_SEEDANCE_API_KEY`替换为您从火山引擎获取的API密钥，将`ep-20240601111111-xxxxx`替换为实际的端点ID。

### 注意事项

- Seedance API需要指定端点ID，这是在创建推理端点时生成的
- 首次使用可能需要申请试用额度
- API调用有频率限制和计费标准

---

## RunwayML Gen-2 (国内版)

### 获取API密钥步骤

1. 访问RunwayML官网：https://runwayml.com/
2. 注册/登录RunwayML账号
3. 进入"API Keys"页面
4. 创建API Key：
   - 点击"Create API Key"按钮
   - 填写API Key名称和描述
   - 点击"Create"创建
5. 复制生成的API Key

### 配置方法

在`app.py`文件中，找到RunwayML的配置部分：

```python
'runway': {
    'name': 'RunwayML Gen-2 (国内版)',
    'api_url': 'https://api.runwayml.com/v1/generate',
    'api_key': os.environ.get('RUNWAY_API_KEY', 'YOUR_RUNWAY_API_KEY'),
    'model': 'gen2',
    'description': '国内可访问的Runway视频生成模型'
},
```

将`YOUR_RUNWAY_API_KEY`替换为您从RunwayML获取的API密钥。

### 注意事项

- RunwayML API通常有免费额度，但超过免费额度后需要付费
- 首次使用可能需要验证邮箱
- API调用有频率限制和计费标准

---

## Pika Labs (国内版)

### 获取API密钥步骤

1. 访问Pika Labs官网：https://pika.art/
2. 注册/登录Pika Labs账号
3. 进入"API Keys"页面
4. 创建API Key：
   - 点击"Create API Key"按钮
   - 填写API Key名称和描述
   - 点击"Create"创建
5. 复制生成的API Key

### 配置方法

在`app.py`文件中，找到Pika Labs的配置部分：

```python
'pika': {
    'name': 'Pika Labs (国内版)',
    'api_url': 'https://api.pika.art/v1/generate',
    'api_key': os.environ.get('PIKA_API_KEY', 'YOUR_PIKA_API_KEY'),
    'model': 'pika-1.0',
    'description': '国内可访问的Pika视频生成模型'
},
```

将`YOUR_PIKA_API_KEY`替换为您从Pika Labs获取的API密钥。

### 注意事项

- Pika Labs API通常有免费额度，但超过免费额度后需要付费
- 首次使用可能需要验证邮箱
- API调用有频率限制和计费标准

---

## 通用配置建议

### 1. 使用环境变量存储API密钥

为了安全起见，建议使用环境变量存储API密钥，而不是直接写在代码中：

```python
import os

AI_VIDEO_MODELS = {
    'seedance': {
        'name': 'Seedance (字节跳动)',
        'api_url': 'https://ark.cn-beijing.volces.com/api/v3/chat/completions',
        'api_key': os.environ.get('SEEDANCE_API_KEY', 'YOUR_SEEDANCE_API_KEY'),
        'model': 'ep-20240601111111-xxxxx',  # 需要替换为实际的端点ID
        'description': '字节跳动旗下的AI视频生成引擎'
    },
    # ... 其他模型配置
}
```

然后创建一个`.env`文件：

```
SEEDANCE_API_KEY=your_actual_api_key_here
RUNWAY_API_KEY=your_actual_api_key_here
PIKA_API_KEY=your_actual_api_key_here
```

### 2. 安装python-dotenv

```bash
pip install python-dotenv
```

然后在app.py开头添加：

```python
from dotenv import load_dotenv
load_dotenv()
```

### 3. 更新.gitignore

确保`.env`文件不被提交到版本控制系统：

```
.env
```

### 4. API密钥安全注意事项

- 不要将API密钥硬编码在代码中
- 不要将API密钥提交到版本控制系统
- 定期更换API密钥
- 限制API密钥的权限和访问范围
- 监控API密钥的使用情况

---

## 测试API密钥配置

配置完API密钥后，您可以通过以下方式测试配置是否正确：

1. 启动后端服务：
```bash
python app.py
```

2. 在网页中上传一个文档
3. 选择对应的AI视频生成模型
4. 点击"生成视频"按钮
5. 查看控制台输出，确认API调用是否成功

---

## 常见问题

### Q1: API密钥无效怎么办？

A: 请检查以下几点：
- API密钥是否正确复制
- API密钥是否已过期
- API密钥是否有足够的权限
- API密钥是否已激活

### Q2: API调用失败怎么办？

A: 请检查以下几点：
- 网络连接是否正常
- API URL是否正确
- 请求参数是否符合API文档要求
- API调用频率是否超限

### Q3: 如何获取更多API调用额度？

A: 不同平台有不同的方式：
- 查看平台的免费额度政策
- 联系平台客服申请更多额度
- 根据平台计费标准购买更多额度

---

## 参考链接

- Seedance API文档：https://www.volcengine.com/docs/82379
- RunwayML API文档：https://runwayml.com/docs
- Pika Labs API文档：https://pika.art/docs
