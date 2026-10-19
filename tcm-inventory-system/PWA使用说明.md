# 本草智管 PWA 应用使用说明

## 什么是 PWA？

PWA（Progressive Web App，渐进式Web应用）是一种可以像原生App一样使用的网页应用。用户无需从应用商店下载，直接通过浏览器即可安装到手机主屏幕，体验接近原生App。

## 功能特性

- ✅ **无需下载安装**：浏览器打开即可用
- ✅ **添加到主屏幕**：一键安装，像App一样使用
- ✅ **跨平台支持**：Android、iOS、Windows、macOS均可使用
- ✅ **离线访问**：核心页面支持离线缓存
- ✅ **自动更新**：新版本自动检测并提示更新
- ✅ **全屏体验**：独立窗口，无浏览器地址栏
- ✅ **推送通知**：支持系统通知（需HTTPS环境）

## 手机端安装方法

### Android（Chrome浏览器）
1. 用Chrome浏览器打开系统地址
2. 浏览器会自动弹出"添加到主屏幕"提示
3. 点击"添加"，即可在桌面看到"本草智管"图标
4. 点击图标即可像App一样全屏使用

如果没有自动弹出提示：
1. 点击浏览器右上角菜单（三个点）
2. 选择"添加到主屏幕"或"安装应用"
3. 确认安装

### iOS（Safari浏览器）
1. 用Safari浏览器打开系统地址
2. 点击底部的"分享"按钮（方框带向上箭头）
3. 选择"添加到主屏幕"
4. 点击"添加"，即可在桌面看到"本草智管"图标
5. 点击图标即可全屏使用

## 电脑端安装方法

### Windows / macOS（Chrome / Edge浏览器）
1. 用Chrome或Edge浏览器打开系统地址
2. 地址栏右侧会出现"安装"图标（电脑屏幕带向下箭头）
3. 点击"安装"，确认后即可在桌面/开始菜单看到"本草智管"
4. 应用会以独立窗口运行，无浏览器地址栏

## 离线使用说明

### 支持离线的功能
- 登录/注册页面
- 所有业务页面（控制面板、药材管理、处方管理等）
- 静态资源（CSS、JS、图标、字体）

### 不支持离线的功能
- 所有需要后端API的操作（数据查询、提交、修改等）
- 实时数据更新

### 离线时的表现
- 已缓存的页面可以正常打开
- API请求会提示"网络连接失败，请检查网络后重试"
- 恢复网络后自动恢复正常功能

## 版本更新说明

当系统有新版本发布时：
1. 应用会自动检测新版本
2. 弹出提示"发现新版本，是否立即更新？"
3. 点击"确定"后自动更新并刷新页面
4. 也可以手动清除浏览器缓存后刷新

## 部署到公网的要求

要让PWA功能完整可用（特别是离线缓存和安装功能），需要满足：

### 必须条件
1. **HTTPS协议**：Service Worker要求HTTPS环境（localhost除外）
2. **正确的MIME类型**：manifest.json需要返回 `application/manifest+json` 类型
3. **Service Worker路径**：sw.js需要放在网站根目录

### 推荐配置
- 使用Nginx反向代理Flask后端
- 配置正确的缓存策略
- 配置HTTPS证书（可使用Let's Encrypt免费证书）

### Nginx配置示例
```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # 前端静态文件
    location / {
        root /path/to/tcm-inventory-system/frontend;
        index index.html;
    }
    
    # API代理
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # manifest.json正确的MIME类型
    location = /manifest.json {
        types { }
        default_type application/manifest+json;
        root /path/to/tcm-inventory-system/frontend;
    }
    
    # Service Worker不缓存
    location = /sw.js {
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        root /path/to/tcm-inventory-system/frontend;
    }
}
```

## 常见问题

### Q: 为什么没有"添加到主屏幕"的提示？
A: 可能原因：
1. 不是HTTPS环境（localhost除外）
2. 已经安装过了
3. 浏览器不支持PWA（建议使用Chrome、Edge、Safari）

### Q: 安装后如何卸载？
A: 
- Android：长按图标，拖到"卸载"
- iOS：长按图标，点击"移除App"
- Windows：设置 → 应用 → 找到"本草智管" → 卸载
- macOS：启动台 → 长按图标 → 点击"×"

### Q: 数据会保存在本地吗？
A: 
- 页面静态资源会缓存到本地（离线访问用）
- 业务数据保存在服务器数据库中
- 登录状态保存在浏览器sessionStorage中

### Q: 如何确认PWA是否正常工作？
A: 
1. 打开浏览器开发者工具（F12）
2. 切换到"Application"标签
3. 左侧选择"Service Workers"，查看是否已激活
4. 选择"Manifest"，查看应用清单是否正确加载
5. 选择"Cache Storage"，查看缓存的资源

## 技术规格

- **应用名称**：本草智管 - 中医门诊药材库存管理系统
- **应用版本**：v5.0.0
- **PWA版本**：1.0
- **支持平台**：Android、iOS、Windows、macOS、Linux
- **推荐浏览器**：Chrome 90+、Edge 90+、Safari 14+、Firefox 89+
- **缓存策略**：缓存优先，网络更新
- **离线支持**：核心页面静态资源
