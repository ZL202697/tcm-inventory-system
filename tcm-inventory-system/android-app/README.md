# 本草智管 Android APP 构建说明

## 项目概述

本项目是"本草智管 - 中医门诊药材库存管理系统"的Android客户端，采用WebView包装方式，将现有Web系统打包为原生Android APP。

**APP特性：**
- ✅ 真正的APK安装包，像普通APP一样安装使用
- ✅ 独立图标，全屏运行，无浏览器地址栏
- ✅ 支持下拉刷新
- ✅ 支持文件下载
- ✅ 支持JS对话框（alert/confirm）
- ✅ 支持外部链接跳转浏览器
- ✅ 双击返回键退出
- ✅ 无网络时显示友好提示
- ✅ 适配Android 5.0+（API 21+）

## 项目结构

```
android-app/
├── app/
│   ├── build.gradle              # 应用级构建配置
│   ├── proguard-rules.pro        # 代码混淆规则
│   └── src/
│       └── main/
│           ├── AndroidManifest.xml    # 应用清单（权限、组件配置）
│           ├── java/com/bencao/zhiguan/
│           │   └── MainActivity.java  # 主Activity（WebView核心代码）
│           └── res/
│               ├── drawable/           # 图片资源（按钮、图标等）
│               ├── layout/             # 布局文件
│               │   └── activity_main.xml
│               ├── mipmap-*/           # 应用图标（各分辨率）
│               ├── values/             # 值资源
│               │   ├── strings.xml     # 字符串
│               │   ├── colors.xml      # 颜色
│               │   └── themes.xml      # 主题
│               └── xml/                # XML配置
│                   ├── backup_rules.xml
│                   ├── data_extraction_rules.xml
│                   └── file_paths.xml
├── build.gradle                   # 项目级构建配置
├── settings.gradle                # 项目设置
├── gradle.properties              # Gradle属性
├── gradle/wrapper/
│   └── gradle-wrapper.properties  # Gradle Wrapper配置
└── .gitignore
```

## 环境要求

### 必需软件
1. **Android Studio**（推荐最新稳定版，如 Hedgehog | 2023.1.1 或更高）
   - 下载地址：https://developer.android.com/studio
2. **JDK 17**（Android Studio自带，无需单独安装）
3. **Android SDK**（Android Studio会自动下载）
   - compileSdk: 34
   - minSdk: 21（Android 5.0）
   - targetSdk: 34

### 硬件要求
- 内存：至少8GB RAM（推荐16GB）
- 磁盘：至少10GB可用空间（Android SDK + 构建缓存）

## 构建步骤

### 方法一：使用Android Studio（推荐）

#### 1. 打开项目
1. 启动Android Studio
2. 选择 `File` → `Open`
3. 选择 `android-app` 文件夹
4. 等待Gradle同步完成（首次可能需要几分钟下载依赖）

#### 2. 配置服务器地址
打开 `app/src/main/java/com/bencao/zhiguan/MainActivity.java`，修改第42行：

```java
// 服务器地址 - 部署到公网后修改为你的域名
// 本地测试：http://10.0.2.2:5000 （Android模拟器访问电脑本地）
// 局域网测试：http://电脑IP:5000 （如 http://192.168.1.100:5000）
// 公网部署：https://your-domain.com
private static final String BASE_URL = "http://10.0.2.2:5000";
```

**地址说明：**
- `10.0.2.2`：Android模拟器访问宿主机（电脑）的特殊地址
- `192.168.x.x`：局域网内电脑的IP地址（手机和电脑需在同一WiFi）
- `your-domain.com`：公网服务器域名（推荐使用HTTPS）

#### 3. 连接手机或启动模拟器
**方式A：使用真实手机**
1. 手机开启"开发者选项"和"USB调试"
2. 用USB线连接电脑
3. 手机上允许USB调试

**方式B：使用模拟器**
1. Android Studio → `Tools` → `Device Manager`
2. 点击 `Create Device` 创建虚拟设备
3. 选择手机型号（推荐Pixel 5）
4. 选择系统镜像（推荐API 34）
5. 完成创建并启动模拟器

#### 4. 运行APP
1. 在Android Studio顶部工具栏选择目标设备
2. 点击绿色运行按钮（▶）或按 `Shift+F10`
3. 等待构建完成，APP会自动安装并启动

#### 5. 生成APK安装包
**Debug版本（测试用）：**
1. `Build` → `Build Bundle(s) / APK(s)` → `Build APK(s)`
2. 构建完成后点击通知中的 `locate` 找到APK
3. APK路径：`app/build/outputs/apk/debug/app-debug.apk`

**Release版本（发布用）：**
1. `Build` → `Generate Signed Bundle / APK`
2. 选择 `APK`，点击Next
3. 创建或选择签名密钥（.jks文件）
4. 选择 `release` 构建类型
5. 点击Finish，等待构建完成
6. APK路径：`app/build/outputs/apk/release/app-release.apk`

### 方法二：使用命令行（Gradle）

#### 1. 安装Gradle
确保已安装Gradle 8.0+，或使用项目自带的Gradle Wrapper。

#### 2. 配置SDK路径
在项目根目录创建 `local.properties` 文件：
```properties
sdk.dir=C\:\\Users\\YourName\\AppData\\Local\\Android\\Sdk
```

#### 3. 构建Debug APK
```bash
cd android-app
./gradlew assembleDebug
```
Windows下使用：
```cmd
gradlew.bat assembleDebug
```

#### 4. 构建Release APK
```bash
./gradlew assembleRelease
```

#### 5. 安装到手机
```bash
adb install app/build/outputs/apk/debug/app-debug.apk
```

## 签名密钥创建（发布必需）

发布到应用商店或正式分发需要签名密钥：

### 使用Android Studio创建
1. `Build` → `Generate Signed Bundle / APK`
2. 点击 `Create new...`
3. 填写密钥信息：
   - Key store path：密钥保存路径
   - Password：密钥库密码
   - Alias：密钥别名
   - Password：密钥密码
   - Validity (years)：有效期（建议25年）
   - Certificate：证书信息（姓名、组织、城市等）
4. 点击OK完成创建

### 使用命令行创建
```bash
keytool -genkeypair -v -keystore my-release-key.jks -keyalg RSA -keysize 2048 -validity 10000 -alias my-key-alias
```

## 部署到公网的完整流程

### 1. 准备服务器
- 购买云服务器（阿里云、腾讯云、华为云等）
- 配置安全组，开放80/443/5000端口
- 安装Python 3.8+、Nginx

### 2. 部署后端服务
```bash
# 上传项目到服务器
scp -r tcm-inventory-system user@your-server:/opt/

# 安装依赖
cd /opt/tcm-inventory-system/backend
pip install -r requirements.txt

# 初始化数据库
python init_db.py

# 启动服务（推荐使用gunicorn或uwsgi）
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 3. 配置Nginx反向代理 + HTTPS
```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 4. 修改APP服务器地址
将 `MainActivity.java` 中的 `BASE_URL` 修改为：
```java
private static final String BASE_URL = "https://your-domain.com";
```

### 5. 重新构建APK
按照上述步骤重新构建Release APK，签名后分发。

## 常见问题

### Q: APP打开后显示白屏或无法加载？
A: 可能原因：
1. 服务器地址配置错误 → 检查 `BASE_URL` 是否正确
2. 服务器未启动 → 确认后端服务正在运行
3. 网络不通 → 手机和服务器需在同一网络，或服务器已部署到公网
4. 未允许HTTP明文传输 → 已在AndroidManifest中配置 `usesCleartextTraffic="true"`

### Q: 如何在模拟器中访问电脑本地的服务？
A: 使用 `http://10.0.2.2:5000`，这是Android模拟器访问宿主机的特殊地址。

### Q: 如何在真实手机上访问电脑本地的服务？
A: 
1. 手机和电脑连接同一WiFi
2. 查看电脑的局域网IP（Windows: `ipconfig`，Mac/Linux: `ifconfig`）
3. 将 `BASE_URL` 改为 `http://电脑IP:5000`
4. 确保电脑防火墙允许5000端口入站

### Q: 构建时报错 "SDK location not found"？
A: 在项目根目录创建 `local.properties` 文件，内容：
```properties
sdk.dir=你的Android SDK路径
```
Windows示例：`sdk.dir=C\:\\Users\\YourName\\AppData\\Local\\Android\\Sdk`

### Q: 构建时报错 "Could not resolve com.android.tools.build:gradle"？
A: 检查网络连接，确保能访问Google Maven仓库。国内用户可配置阿里云镜像：
在 `build.gradle` 中添加：
```gradle
repositories {
    maven { url 'https://maven.aliyun.com/repository/google' }
    maven { url 'https://maven.aliyun.com/repository/public' }
    google()
    mavenCentral()
}
```

### Q: 安装APK时提示"解析包错误"？
A: 可能原因：
1. APK文件损坏 → 重新构建
2. 手机Android版本过低 → 确保手机系统Android 5.0+
3. 未开启"未知来源应用安装" → 在手机设置中开启

### Q: 如何修改APP名称和图标？
A: 
- APP名称：修改 `res/values/strings.xml` 中的 `app_name`
- APP图标：替换 `res/mipmap-*/ic_launcher.png` 图片

### Q: 如何添加启动页（Splash Screen）？
A: 
1. 创建 `SplashActivity.java`
2. 在 `AndroidManifest.xml` 中将启动页设为启动Activity
3. 启动页显示2-3秒后自动跳转到MainActivity

## 技术规格

| 项目 | 说明 |
|------|------|
| 应用ID | com.bencao.zhiguan |
| 应用名称 | 本草智管 |
| 版本号 | 5.0.0 (versionCode: 1) |
| 最低Android版本 | Android 5.0 (API 21) |
| 目标Android版本 | Android 14 (API 34) |
| 编译SDK版本 | API 34 |
| Java版本 | Java 8 |
| 构建工具 | Gradle 8.0 + Android Gradle Plugin 8.1.0 |
| UI框架 | Material Components + AndroidX |
| 核心组件 | WebView + SwipeRefreshLayout |

## 后续优化建议

1. **添加启动页**：提升APP启动体验
2. **集成推送**：使用极光推送、个推等实现消息推送
3. **添加更新检查**：APP启动时检查新版本并提示更新
4. **集成统计**：使用友盟、百度统计等分析用户行为
5. **原生功能扩展**：调用相机扫码、定位、蓝牙等原生功能
6. **离线数据缓存**：使用SQLite缓存核心数据，支持完全离线使用
7. **多渠道打包**：使用友盟多渠道打包，统计不同渠道下载量

## 联系方式

如有问题，请参考项目文档或联系开发团队。
