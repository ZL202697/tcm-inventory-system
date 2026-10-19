# 本草智管平台 - 中医门诊药材库存管理系统

## 项目简介

本项目为信息系统开发综合应用实训完整项目，面向中小型中医门诊、中医馆的药材库存管理系统。
基于 Python Flask + SQLite/MySQL + 原生 HTML/Tailwind CSS + ECharts 技术栈开发，
包含完整的药材管理、处方开具审核发药、采购管理、库存预警、智能补货、数据可视化等核心业务功能。

## 技术架构

```
前端 (HTML + Tailwind CSS + ECharts + Font Awesome)
    │
    ├── fetch (REST API)
    │
后端 (Python Flask)
    │
    ├── pymysql / sqlite3
    │
数据库 (SQLite 默认 / MySQL 可选)
```

## 功能模块

### 一、控制面板 (dashboard.html)
- 药材总数、总库存量、库存预警统计
- 各药材库存量分布柱状图
- 单药材库存变化趋势图（SVG 动态绘制）
- 库存预警提醒弹窗
- 快捷操作入口

### 二、处方管理 (prescriptions.html)
- 处方列表（按状态筛选、关键词搜索）
- 新建处方（患者信息、药材明细动态行、自动计算金额）
- 处方详情查看
- 处方审核（通过/拒绝）
- 处方发药（自动扣减库存、记录库存流水）
- 处方删除
- 权限控制（医生只能查看自己的处方）

### 三、数据看板 (data-board.html)
基于 ECharts 5.4 的专业数据可视化：
- 总览统计卡片
- 处方数量与金额趋势图（双Y轴，支持7/14/30天切换）
- 处方状态分布环形饼图
- 药材消耗排行 TOP10 横向柱状图
- 医生工作量统计（柱状图+折线图组合）
- 药材类别分布南丁格尔玫瑰图
- 处方处理效率漏斗图

### 四、药材管理 (herbs.html)
- 药材列表（搜索、分类筛选）
- 新增/编辑/删除药材
- 库存快速调整
- 药材别名、多单位支持
- 预警阈值设置

### 五、采购管理 (purchase.html) ★ 新增
- 采购单列表（状态筛选、搜索）
- 新建采购单（选择供应商、药材明细、自动计算金额）
- 采购单审核（通过/拒绝）
- 采购入库（自动增加库存、记录库存流水）
- 采购单删除
- 供应商管理

### 六、库存预警与智能补货 (replenish.html) ★ 新增
- 库存预警列表（紧急缺货、库存不足）
- 基于历史消耗的智能补货推荐算法
- 日均消耗量、可维持天数计算
- 建议补货量、预计采购金额
- 优先级分级（紧急/高/中/低）
- 支持7/14/30/60/90天消耗数据分析

### 七、库存流水 (stock-flow.html) ★ 新增
- 所有库存变动明细记录
- 按类型筛选（入库/出库）
- 按药材筛选
- 关联单据显示（采购单/处方）
- 变动后库存余额
- 操作人记录

### 八、用户管理 (users.html)
- 用户列表
- 新增/编辑/删除用户
- 角色管理（管理员/医生）
- 账号启用/禁用

### 九、操作日志 (logs.html)
- 药材操作日志（新增/编辑/删除）
- 操作人、时间、变更明细
- 按药材筛选

## 数据库设计

### 核心表（9张表）

| 表名 | 说明 | 关键字段 |
|---|---|---|
| users | 用户表 | username, password, role, name, phone, status |
| herbs | 药材表 | code, name, category, price, quantity, warning_threshold |
| prescriptions | 处方主表 | prescription_no, patient_name, doctor_username, total_amount, status |
| prescription_items | 处方明细表 | prescription_id, herb_code, dosage, quantity, price, subtotal |
| suppliers | 供应商表 ★新增 | name, contact_person, phone, address |
| purchase_orders | 采购单表 ★新增 | order_no, supplier_id, total_amount, status |
| purchase_items | 采购明细表 ★新增 | purchase_id, herb_code, quantity, price, received_quantity |
| stock_transactions | 库存流水表 ★新增 | herb_code, type, quantity, balance_after, reference_type |
| operation_logs | 操作日志表 | herb_code, action, changes, operator, timestamp |

### 处方状态流转
```
pending（待审核）
    │
    ├── approve → approved（已审核）
    │                   │
    │                   └── dispense → dispensed（已发药，自动扣库存）
    │
    └── reject → rejected（已拒绝）
```

### 采购单状态流转
```
pending（待审核）
    │
    ├── approve → approved（已审核）
    │                   │
    │                   └── in-stock → completed（已入库，自动加库存）
    │
    └── reject → rejected（已拒绝）
```

## 快速启动

### 环境要求
- Python 3.8+
- 现代浏览器（Chrome / Edge / Firefox）
- （可选）MySQL 5.7+ 或 8.0+

### 启动步骤

**方式一：一键启动（推荐，Windows）**

双击 `start.bat`，脚本会自动安装依赖、初始化数据库并启动服务，同时自动打开浏览器。

**方式二：手动启动**

```bash
# 1. 进入后端目录
cd backend

# 2. 安装依赖
pip install -r requirements.txt

# 3. 初始化数据库（首次运行）
python init_db.py

# 4. 启动服务
python app.py
```

启动后浏览器访问 **http://127.0.0.1:5000**

### 默认账号

| 用户名 | 密码 | 角色 | 权限 |
|---|---|---|---|
| admin | 123456 | 管理员 | 全部权限（审核/发药/采购/用户管理/日志） |
| doctor | 123456 | 医生 | 开具处方、查看自己的处方、药材管理、采购 |
| doctor2 | 123456 | 医生 | 同上（示例数据中的另一位医生） |

## API 接口清单

### 认证接口
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /api/login | 登录 |
| POST | /api/register | 注册 |

### 药材接口
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/herbs | 药材列表/搜索 |
| POST | /api/herbs | 新增药材 |
| PUT | /api/herbs/{code} | 编辑药材 |
| DELETE | /api/herbs/{code} | 删除药材 |

### 处方接口
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/prescriptions | 处方列表（筛选） |
| GET | /api/prescriptions/{id} | 处方详情 |
| POST | /api/prescriptions | 创建处方 |
| PUT | /api/prescriptions/{id}/audit | 审核处方 |
| PUT | /api/prescriptions/{id}/dispense | 发药（自动扣库存） |
| DELETE | /api/prescriptions/{id} | 删除处方 |

### 采购接口 ★新增
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/purchase-orders | 采购单列表 |
| GET | /api/purchase-orders/{id} | 采购单详情 |
| POST | /api/purchase-orders | 创建采购单 |
| PUT | /api/purchase-orders/{id}/audit | 审核采购单 |
| PUT | /api/purchase-orders/{id}/in-stock | 采购入库（自动加库存） |
| DELETE | /api/purchase-orders/{id} | 删除采购单 |

### 供应商接口 ★新增
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/suppliers | 供应商列表 |
| POST | /api/suppliers | 新增供应商 |
| PUT | /api/suppliers/{id} | 编辑供应商 |
| DELETE | /api/suppliers/{id} | 删除供应商 |

### 库存接口 ★新增
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/stock/warnings | 库存预警列表 |
| GET | /api/stock/replenish-suggestions | 智能补货建议 |
| GET | /api/stock-transactions | 库存流水记录 |

### 数据统计接口
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/stats/overview | 总览统计 |
| GET | /api/stats/prescription-trend | 处方趋势 |
| GET | /api/stats/status-distribution | 状态分布 |
| GET | /api/stats/herb-consumption | 药材消耗排行 |
| GET | /api/stats/doctor-workload | 医生工作量 |
| GET | /api/stats/category-distribution | 类别分布 |
| GET | /api/stats/purchase-overview | 采购统计 ★新增 |

### 其他接口
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/dashboard | 仪表盘数据 |
| GET | /api/users | 用户列表（管理员） |
| POST | /api/users | 添加用户（管理员） |
| PUT | /api/users/{username} | 编辑用户（管理员） |
| DELETE | /api/users/{username} | 删除用户（管理员） |
| GET | /api/logs | 操作日志（管理员） |

**接口统一返回格式：** `{"code": 0, "message": "...", "data": ...}`，code 非 0 表示失败。
**除登录/注册外，请求需携带请求头 `X-User: <当前登录用户名>`。**

## 目录结构

```
tcm-inventory-system/
├── frontend/                  # 前端页面（9个页面）
│   ├── index.html             # 登录/注册页
│   ├── dashboard.html         # 控制面板
│   ├── prescriptions.html     # 处方管理
│   ├── data-board.html        # 数据看板（ECharts）
│   ├── herbs.html             # 药材管理
│   ├── purchase.html          # 采购管理 ★新增
│   ├── replenish.html         # 库存预警/智能补货 ★新增
│   ├── stock-flow.html        # 库存流水 ★新增
│   ├── users.html             # 用户管理
│   └── logs.html              # 操作日志
├── backend/                   # 后端服务
│   ├── app.py                 # Flask 主程序（REST API + 业务逻辑）
│   ├── db.py                  # 数据库连接工具（智能双模式）
│   ├── init_db.py             # 数据库初始化脚本（建表+示例数据）
│   ├── requirements.txt       # Python 依赖
│   └── herb_management.db     # SQLite 数据库文件（运行后生成）
├── start.bat                  # Windows 一键启动脚本
├── README.md                  # 项目说明文档（本文件）
├── DEPLOY.md                  # 部署文档
├── 演示指南.md                # 演示指南
└── 代码结构说明.md            # 代码结构详细说明
```

## 智能补货算法说明

智能补货推荐基于以下逻辑：

1. **日均消耗量**：统计近 N 天（默认30天）已发药处方中该药材的总消耗量，除以天数
2. **可维持天数**：当前库存 ÷ 日均消耗量
3. **建议补货量**：30天目标库存量 - 当前库存（仅当结果为正时建议）
4. **优先级分级**：
   - 紧急（critical）：库存为 0
   - 高（high）：可维持 ≤ 7 天
   - 中（medium）：可维持 ≤ 15 天
   - 低（low）：有补货建议但可维持 > 15 天

## 注意事项

1. 必须通过 `http://127.0.0.1:5000` 访问，不能直接双击 HTML 文件（否则接口跨域失败）
2. 默认使用 SQLite 数据库，无需安装 MySQL，即开即用
3. 如需使用 MySQL，设置环境变量 `USE_MYSQL=1`，并在 `db.py` 中配置数据库连接
4. 已发药的处方不能删除，发药后库存自动扣减并记录流水
5. 已入库的采购单不能删除，入库后库存自动增加并记录流水
6. 医生角色只能查看和管理自己开具的处方
7. 示例数据包含 10 种常用药材、3 个供应商、3 张采购单、4 张不同状态的处方

## 技术亮点

1. **前后端分离架构**：前端纯 HTML/JS，通过 fetch 调用后端 REST API
2. **数据库抽象层**：智能双模式（SQLite/MySQL），上层代码零改动
3. **处方业务闭环**：开具 → 审核 → 发药 → 库存扣减 → 流水记录，全流程贯通
4. **采购业务闭环**：创建 → 审核 → 入库 → 库存增加 → 流水记录，全流程贯通
5. **细粒度权限控制**：前端菜单和按钮级别 + 后端 API 双重校验
6. **智能补货算法**：基于历史消耗数据，自动计算日均消耗、可维持天数、建议补货量
7. **数据可视化**：ECharts 7 大图表 + SVG 动态趋势图，覆盖多维度分析
8. **库存流水审计**：所有库存变动均有记录，可追溯来源单据和操作人

---

*项目版本：v3.0*
*开发团队：李奔、姚明、熊威翔、张恩泽、张浩冉*
*指导教师：束建华*
