# 智演助手 - 国内公网访问部署指南

## 推荐方案：Vercel

Vercel 在国内访问速度较快，且完全免费。

### 步骤：

1. **注册 Vercel 账号**
   - 访问 https://vercel.com
   - 使用 GitHub 或邮箱注册

2. **安装 Vercel CLI**
   ```bash
   npm install -g vercel
   ```

3. **登录 Vercel**
   ```bash
   vercel login
   ```

4. **部署项目**
   - 在项目目录下运行：
   ```bash
   vercel
   ```
   - 按提示操作，选择默认配置即可

5. **获取访问地址**
   - 部署完成后，Vercel 会提供一个 `.vercel.app` 域名
   - 例如：https://zhiyan-zhushou.vercel.app

## 备选方案：Gitee Pages

如果 Vercel 访问较慢，可以使用 Gitee Pages。

### 步骤：

1. **注册 Gitee 账号**
   - 访问 https://gitee.com
   - 注册并登录

2. **创建仓库**
   - 点击右上角 "+" 号
   - 选择"新建仓库"
   - 仓库名：`zhiyan-zhushou`
   - 设置为公开

3. **上传代码**
   - 将项目文件上传到仓库

4. **开启 Gitee Pages**
   - 进入仓库页面
   - 点击"服务" -> "Gitee Pages"
   - 选择分支（通常是 main 或 master）
   - 点击"启动"

5. **获取访问地址**
   - Gitee 会提供一个访问地址
   - 例如：https://你的用户名.gitee.io/zhiyan-zhushou

## 注意事项

- Vercel 部署后可以随时更新，只需重新运行 `vercel --prod`
- Gitee Pages 需要手动更新页面
- 两种方案都完全免费
- 建议优先尝试 Vercel，如访问较慢再考虑 Gitee
