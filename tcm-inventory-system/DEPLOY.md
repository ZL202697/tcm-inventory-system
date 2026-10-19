# 本草智管平台 - 部署文档

## 目录
- [本地部署](#本地部署)
- [云服务器部署（推荐，支持移动端访问）](#云服务器部署)
- [移动端访问说明](#移动端访问说明)
- [常见问题](#常见问题)

---

## 本地部署

### 1. 环境准备
- Python 3.8+
- （可选）MySQL 5.7+ / 8.0+，默认使用 SQLite 无需安装

### 2. 安装依赖
```bash
cd backend
pip install -r requirements.txt
```

### 3. 初始化数据库
```bash
python init_db.py
```

成功后会创建：
- 9张数据表（用户、药材、处方、采购、库存流水、操作日志等）
- 默认账号：admin/123456, doctor/123456
- 示例数据：10种药材 + 4张处方

### 4. 启动服务
```bash
python app.py
```

访问 http://127.0.0.1:5000

### 一键启动（Windows）
双击项目根目录下的 `start.bat`，自动完成依赖安装、数据库初始化和服务启动。

---

## 云服务器部署

支持部署到阿里云、腾讯云、华为云等任意 Linux 云服务器，实现手机端访问、多人同时在线使用。

### 方案一：简单部署（适合演示和小规模使用）

#### 1. 购买云服务器
- 推荐配置：2核4G内存、40G系统盘、CentOS 7.9 或 Ubuntu 20.04
- 开放安全组端口：5000（或80/443）

#### 2. 上传项目到服务器
```bash
# 本地打包
zip -r tcm-system.zip tcm-inventory-system/

# 上传到服务器（使用 scp 或 FTP 工具）
scp tcm-system.zip root@你的服务器IP:/opt/

# 服务器上解压
cd /opt/
unzip tcm-system.zip
cd tcm-inventory-system/backend
```

#### 3. 安装 Python 环境
```bash
# CentOS
yum install python3 python3-pip -y

# Ubuntu
apt update && apt install python3 python3-pip -y

# 安装依赖
pip3 install -r requirements.txt
```

#### 4. 初始化数据库并启动
```bash
python3 init_db.py
python3 app.py
```

访问 http://你的服务器IP:5000

#### 5. 后台常驻运行（使用 nohup）
```bash
nohup python3 app.py > app.log 2>&1 &
# 查看日志
tail -f app.log
# 停止服务
pkill -f "python3 app.py"
```

### 方案二：生产级部署（推荐正式使用）

使用 Nginx + Gunicorn + SQLite/MySQL，支持高并发和域名访问。

#### 1. 安装 Gunicorn
```bash
pip3 install gunicorn
```

#### 2. 启动 Gunicorn 服务
```bash
cd /opt/tcm-inventory-system/backend
gunicorn -w 4 -b 127.0.0.1:5000 app:app --daemon --pid app.pid
```

#### 3. 安装配置 Nginx
```bash
# CentOS
yum install nginx -y
# Ubuntu
apt install nginx -y
```

创建 Nginx 配置文件 `/etc/nginx/conf.d/tcm.conf`：
```nginx
server {
    listen 80;
    server_name 你的域名或服务器IP;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

重启 Nginx：
```bash
nginx -t && systemctl restart nginx
```

#### 4. 配置 HTTPS（可选，推荐）
使用 Let's Encrypt 免费证书：
```bash
# 安装 certbot
yum install certbot python3-certbot-nginx -y  # CentOS
# apt install certbot python3-certbot-nginx -y  # Ubuntu

# 申请证书并自动配置
certbot --nginx -d 你的域名
```

#### 5. 配置开机自启
创建 systemd 服务文件 `/etc/systemd/system/tcm.service`：
```ini
[Unit]
Description=TCM Inventory System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/tcm-inventory-system/backend
ExecStart=/usr/bin/python3 app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启用服务：
```bash
systemctl daemon-reload
systemctl enable tcm
systemctl start tcm
```

### 使用 MySQL 数据库（可选，适合大规模数据）

1. 安装 MySQL 并创建数据库：
```sql
CREATE DATABASE herb_management_system DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. 设置环境变量启用 MySQL 模式：
```bash
export USE_MYSQL=1
export DB_HOST=127.0.0.1
export DB_PORT=3306
export DB_USER=root
export DB_PASSWORD=你的MySQL密码
```

3. 重新初始化数据库：
```bash
python3 init_db.py
```

---

## 面向全社会注册审核机制

系统采用三级用户注册审核机制，部署到云服务器后面向全社会开放使用：

### 用户角色与注册策略

| 角色 | 注册方式 | 审核要求 | 注册后状态 | 说明 |
|------|---------|---------|-----------|------|
| **医生** | 公开注册 | 管理员审核 | 待审核（pending） | 需填写科室和执业证号，审核通过后可用 |
| **管理员** | 禁止公开注册 | 只能后台创建 | - | 由现有管理员在用户管理页面创建 |

### 医生注册与审核流程
1. 访问系统登录页，点击「注册」标签
2. 选择「医生」角色
3. 填写信息：用户名、密码、真实姓名、联系电话、**所属科室**、**执业医师证号**
4. 点击「注册」按钮
5. 系统提示"账号正在审核中，请等待管理员审核通过后再登录"
6. 管理员登录系统 → 用户管理 → 筛选"待审核"状态 → 点击「通过」或「拒绝」
7. 审核通过后，医生即可正常登录使用

### 管理员创建流程
1. 现有管理员登录系统
2. 进入「用户管理」页面
3. 点击「添加用户」按钮
4. 选择角色为「管理员」
5. 填写用户名、密码、真实姓名等信息
6. 点击保存，新管理员账号创建完成

### 待审核用户管理
- **查看待审核列表**：用户管理页面 → 状态筛选选择"待审核"
- **审核通过**：点击「通过」按钮，用户状态变为active，可正常登录
- **审核拒绝**：点击「拒绝」按钮，可填写拒绝原因，用户账号被删除
- **待审核用户登录**：系统提示"账号正在审核中，请等待管理员审核通过后再登录"

### 面向全社会部署建议
1. **域名配置**：建议使用易记的域名（如 `tcm.example.com`）
2. **HTTPS加密**：生产环境必须配置HTTPS，保护用户隐私和登录安全
3. **备案要求**：国内服务器需完成ICP备案
4. **用户协议**：建议在注册页添加《用户服务协议》和《隐私政策》链接
5. **数据备份**：定期备份SQLite数据库文件（或使用MySQL主从复制）
6. **访问统计**：可接入百度统计等工具了解用户访问情况

---

## 移动端访问说明

系统已全面适配移动端，医护人员可通过手机浏览器直接访问使用。

### 访问方式
1. **手机浏览器直接访问**：在手机浏览器输入服务器地址（http://你的域名或IP），即可使用全部功能
2. **添加到桌面**：在手机浏览器中选择「添加到主屏幕」，可像APP一样打开使用
3. **微信内置浏览器**：可直接在微信中打开链接使用

### 移动端功能
- **响应式布局**：侧边栏自动变为抽屉式菜单，底部导航栏方便快速切换
- **处方管理**：表格自动适配，支持横向滚动查看
- **数据看板**：图表自适应屏幕大小
- **触摸优化**：按钮和输入框尺寸适合手指点击

### 推荐使用场景
- **医生端**：手机查房时查看患者处方、快捷开方
- **管理员端**：手机审核处方、查看库存预警、审批采购单

---

## 常见问题

### Q: 云服务器部署后外部无法访问
A: 检查以下几点：
1. 云服务器安全组是否开放了对应端口（5000或80）
2. 服务器防火墙是否放行：`firewall-cmd --add-port=5000/tcp --permanent && firewall-cmd --reload`
3. 服务是否正常运行：`ps aux | grep python`
4. SELinux 是否阻止（CentOS）：`setenforce 0` 临时关闭测试

### Q: 移动端访问页面排版错乱
A: 确保通过 `http://` 协议访问，不要直接打开 HTML 文件。清除浏览器缓存后重试。

### Q: 如何修改管理员注册密钥
A: 编辑 `frontend/index.html` 中的 `ADMIN_REGISTER_KEY` 变量，以及 `backend/app.py` 注册接口中的密钥校验。

### Q: SQLite 数据库文件在哪里
A: 默认在 `backend/herb_management.db`，定期备份此文件即可备份全部数据。

### Q: 如何重置所有数据
A: 删除 `backend/herb_management.db` 文件，重新运行 `python init_db.py`。MySQL 模式下执行 `DROP DATABASE herb_management_system;` 后重新初始化。

### Q: 支持多少人同时在线
A: SQLite 模式支持 50-100 人同时在线（适合中小型门诊）；MySQL + Gunicorn 模式支持 500+ 人同时在线。

### Q: 数据安全如何保障
A: 
1. 定期备份数据库文件
2. 生产环境使用 HTTPS 加密传输
3. 密码使用 SHA256 加密存储
4. 配置 Nginx 访问日志和错误日志
5. 重要操作（删除、审核）记录操作日志

---

*文档版本：v3.0*
*更新日期：2026-09-14*
