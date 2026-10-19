# -*- coding: utf-8 -*-
"""
本草智管平台 - 后端服务（Flask + MySQL）
4号模块：处方管理 + 数据看板

启动方式：
    cd backend
    python app.py
浏览器访问 http://127.0.0.1:5000
"""
import hashlib
import json
import os
import time


from flask import Flask, jsonify, request, send_from_directory

from db import execute, query, is_mysql

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")
DEFAULT_WARNING_THRESHOLD = 200

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")


# ============ 工具函数 ============
def sha256_pwd(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def ok(data=None, message="success"):
    return jsonify({"code": 0, "message": message, "data": data})


def fail(message, code=1, http=200):
    return jsonify({"code": code, "message": message, "data": None}), http


def get_current_user():
    username = request.headers.get("X-User", "").strip()
    if not username:
        return None
    return query("SELECT * FROM users WHERE username = %s", (username,), one=True)


def require_login():
    user = get_current_user()
    if not user:
        return None, fail("未登录或账号不存在", code=401, http=401)
    if user["status"] != "active":
        return None, fail("该账号已被禁用", code=403, http=403)
    return user, None


def require_admin():
    user, err = require_login()
    if err:
        return None, err
    if user["role"] != "admin":
        return None, fail("无权限：仅管理员可执行此操作", code=403, http=403)
    return user, None


def require_doctor_or_admin():
    user, err = require_login()
    if err:
        return None, err
    if user["role"] not in ("admin", "doctor"):
        return None, fail("无权限：仅医生或管理员可执行此操作", code=403, http=403)
    return user, None


def herb_to_camel(row):
    return {
        "code": row["code"], "name": row["name"], "category": row["category"],
        "origin": row["origin"], "storage": row["storage"], "unit": row["unit"],
        "price": float(row["price"]) if row["price"] is not None else None,
        "quantity": row["quantity"], "warningThreshold": row["warning_threshold"],
        "description": row["description"],
    }


def prescription_to_camel(row, items=None):
    return {
        "id": row["id"],
        "prescriptionNo": row["prescription_no"],
        "patientName": row["patient_name"],
        "patientPhone": row["patient_phone"],
        "patientGender": row["patient_gender"],
        "patientAge": row["patient_age"],
        "doctorUsername": row["doctor_username"],
        "doctorName": row["doctor_name"],
        "department": row["department"],
        "diagnosis": row["diagnosis"],
        "advice": row["advice"],
        "totalAmount": float(row["total_amount"]) if row["total_amount"] is not None else 0,
        "status": row["status"],
        "auditRemark": row["audit_remark"],
        "auditor": row["auditor"],
        "auditorName": row["auditor_name"],
        "auditTime": row["audit_time"],
        "dispenser": row["dispenser"],
        "dispenserName": row["dispenser_name"],
        "dispenseTime": row["dispense_time"],
        "createdAt": str(row["created_at"]) if row["created_at"] else None,
        "items": items or [],
    }


def item_to_camel(row):
    return {
        "id": row["id"],
        "herbCode": row["herb_code"],
        "herbName": row["herb_name"],
        "dosage": row["dosage"],
        "usage": row["usage"],
        "quantity": row["quantity"],
        "price": float(row["price"]) if row["price"] is not None else 0,
        "subtotal": float(row["subtotal"]) if row["subtotal"] is not None else 0,
    }


def add_log(herb_code, herb_name, action, changes, operator, operator_name):
    try:
        now_ms = int(time.time() * 1000)
        time_str = time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(now_ms / 1000 + 8 * 3600))
        execute(
            """INSERT INTO operation_logs
               (herb_code, herb_name, action, changes, operator, operator_name, timestamp, time_str)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (herb_code, herb_name, action, json.dumps(changes, ensure_ascii=False, default=str),
             operator, operator_name, now_ms, time_str),
        )
    except Exception:
        pass


def add_stock_transaction(herb_code, herb_name, tx_type, quantity, reference_type=None,
                          reference_id=None, remark=None, operator=None, operator_name=None):
    """记录库存流水"""
    herb = query("SELECT quantity FROM herbs WHERE code = %s", (herb_code,), one=True)
    balance = herb["quantity"] if herb else 0
    execute(
        """INSERT INTO stock_transactions
           (herb_code, herb_name, type, quantity, balance_after, reference_type, reference_id,
            remark, operator, operator_name, created_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (herb_code, herb_name, tx_type, quantity, balance, reference_type, reference_id,
         remark, operator, operator_name, time.strftime("%Y/%m/%d %H:%M:%S")),
    )


def _day_start_ms(days_ago=0):
    import datetime as _dt
    bj = _dt.timezone(_dt.timedelta(hours=8))
    d = (_dt.datetime.now(bj) - _dt.timedelta(days=days_ago)).replace(hour=0, minute=0, second=0, microsecond=0)
    return int(d.astimezone(_dt.timezone.utc).timestamp() * 1000)


def _log_row(r):
    try:
        changes = json.loads(r["changes"]) if r["changes"] else {}
    except Exception:
        changes = {}
    return {
        "id": f"log_{r['id']}", "herbCode": r["herb_code"], "herbName": r["herb_name"],
        "action": r["action"], "changes": changes,
        "operator": r["operator"], "operatorName": r["operator_name"],
        "timestamp": r["timestamp"], "timeStr": r["time_str"],
    }


# ============ 页面路由 ============
@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


# ============ 认证接口 ============
@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return fail("请填写用户名和密码")
    user = query("SELECT * FROM users WHERE username = %s", (username,), one=True)
    if not user or user["password"] != sha256_pwd(password):
        return fail("用户名或密码错误")
    if user["status"] == "inactive":
        return fail("该账号已被禁用，请联系管理员")
    if user["status"] == "pending":
        return fail("账号正在审核中，请等待管理员审核通过后再登录")
    add_log(None, None, "login", {"summary": "登录账号：%s（%s）" % (user["username"], user["name"])}, user["username"], user["name"])
    return ok({"username": user["username"], "role": user["role"], "name": user["name"], "phone": user["phone"]})


@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    role = data.get("role") or "doctor"
    if not username or not password or not name or not phone:
        return fail("请填写所有必填字段")
    if role != "doctor":
        return fail("仅支持医生注册，管理员请联系系统管理员创建")
    department = (data.get("department") or "").strip()
    license_no = (data.get("license") or "").strip()
    if not department or not license_no:
        return fail("医生注册需填写所属科室和执业医师证号")
    if query("SELECT 1 FROM users WHERE username = %s", (username,), one=True):
        return fail("用户名已存在")
    execute(
        """INSERT INTO users (username, password, role, name, phone, status, department, license, create_time)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (username, sha256_pwd(password), role, name, phone, "pending", department, license_no,
         time.strftime("%Y/%m/%d %H:%M:%S")),
    )
    add_log(None, None, "register", {"summary": "医生注册申请：%s（%s）" % (name, username)}, username, name)
    return ok(None, "注册成功，您的账号正在审核中，请等待管理员审核通过后再登录")


# ============ 药材接口 ============
@app.route("/api/herbs", methods=["GET"])
def list_herbs():
    user, err = require_login()
    if err:
        return err
    keyword = (request.args.get("q") or "").strip()
    if keyword:
        like = f"%{keyword}%"
        rows = query("""SELECT * FROM herbs WHERE name LIKE %s OR code LIKE %s OR category LIKE %s
                         ORDER BY created_at DESC, code ASC""", (like, like, like))
    else:
        rows = query("SELECT * FROM herbs ORDER BY created_at DESC, code ASC")
    return ok([herb_to_camel(r) for r in rows])


@app.route("/api/herbs", methods=["POST"])
def add_herb():
    user, err = require_login()
    if err:
        return err
    d = request.get_json(silent=True) or {}
    code = (d.get("code") or "").strip()
    name = (d.get("name") or "").strip()
    if not code or not name:
        return fail("请填写药材编码和名称")
    if query("SELECT 1 FROM herbs WHERE code = %s", (code,), one=True):
        return fail("已存在相同编码的药材")
    execute(
        """INSERT INTO herbs (code, name, category, origin, storage, unit, price, quantity, warning_threshold, description)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (code, name, d.get("category"), d.get("origin"), d.get("storage"), d.get("unit"),
         d.get("price", 0), d.get("quantity", 0), d.get("warningThreshold", 200), d.get("description")),
    )
    add_log(code, name, "add", {"summary": "新增药材：%s（%s）" % (name, code), **d}, user["username"], user["name"])
    return ok(None, "药材添加成功")


@app.route("/api/herbs/<code>", methods=["PUT"])
def update_herb(code):
    user, err = require_login()
    if err:
        return err
    d = request.get_json(silent=True) or {}
    old = query("SELECT * FROM herbs WHERE code = %s", (code,), one=True)
    if not old:
        return fail("药材不存在")
    execute(
        """UPDATE herbs SET name=%s, category=%s, origin=%s, storage=%s, unit=%s,
           price=%s, quantity=%s, warning_threshold=%s, description=%s WHERE code=%s""",
        (d.get("name", old["name"]), d.get("category", old["category"]), d.get("origin", old["origin"]),
         d.get("storage", old["storage"]), d.get("unit", old["unit"]),
         d.get("price", old["price"]), d.get("quantity", old["quantity"]),
         d.get("warningThreshold", old["warning_threshold"]), d.get("description", old["description"]), code),
    )
    add_log(code, old["name"], "edit", {"summary": "编辑药材：%s（%s）" % (old["name"], code), **d}, user["username"], user["name"])
    return ok(None, "药材更新成功")


@app.route("/api/herbs/<code>", methods=["DELETE"])
def delete_herb(code):
    user, err = require_login()
    if err:
        return err
    old = query("SELECT * FROM herbs WHERE code = %s", (code,), one=True)
    if not old:
        return fail("药材不存在")
    execute("DELETE FROM herbs WHERE code = %s", (code,))
    add_log(code, old["name"], "delete", {"summary": "删除药材：%s（%s）" % (old["name"], code), **old}, user["username"], user["name"])
    return ok(None, "药材删除成功")


# ============ 用户接口 ============
@app.route("/api/users", methods=["GET"])
def list_users():
    _, err = require_admin()
    if err:
        return err
    rows = query("SELECT * FROM users ORDER BY create_time DESC")
    return ok([{
        "username": r["username"], "role": r["role"], "name": r["name"], "phone": r["phone"],
        "status": r["status"], "department": r["department"], "license": r["license"],
        "createTime": r["create_time"],
    } for r in rows])


@app.route("/api/users/pending", methods=["GET"])
def list_pending_users():
    _, err = require_admin()
    if err:
        return err
    rows = query("SELECT * FROM users WHERE status = 'pending' ORDER BY create_time DESC")
    return ok([{
        "username": r["username"], "role": r["role"], "name": r["name"], "phone": r["phone"],
        "status": r["status"], "department": r["department"], "license": r["license"],
        "createTime": r["create_time"],
    } for r in rows])


@app.route("/api/users/<username>/approve", methods=["POST"])
def approve_user(username):
    admin, err = require_admin()
    if err:
        return err
    user = query("SELECT * FROM users WHERE username = %s", (username,), one=True)
    if not user:
        return fail("用户不存在")
    if user["status"] != "pending":
        return fail("该用户不是待审核状态")
    execute("UPDATE users SET status = 'active' WHERE username = %s", (username,))
    add_log(None, None, "user_approve", {"summary": "医生注册审核通过：%s（%s）" % (user["name"], username)}, admin["username"], admin["name"])
    return ok(None, "审核通过，用户已激活")


@app.route("/api/users/<username>/reject", methods=["POST"])
def reject_user(username):
    admin, err = require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    reason = (data.get("reason") or "").strip()
    user = query("SELECT * FROM users WHERE username = %s", (username,), one=True)
    if not user:
        return fail("用户不存在")
    if user["status"] != "pending":
        return fail("该用户不是待审核状态")
    # 拒绝后删除用户（或改为inactive，这里选择删除避免垃圾数据）
    execute("DELETE FROM users WHERE username = %s", (username,))
    add_log(None, None, "user_reject", {"summary": "驳回医生注册：%s（%s）" % (user["name"], username)}, admin["username"], admin["name"])
    return ok(None, "已拒绝该注册申请" + (f"，原因：{reason}" if reason else ""))


@app.route("/api/users/<username>/toggle-status", methods=["POST"])
def toggle_user_status(username):
    admin, err = require_admin()
    if err:
        return err
    user = query("SELECT * FROM users WHERE username = %s", (username,), one=True)
    if not user:
        return fail("用户不存在")
    if user["role"] == "admin" and user["username"] == "admin":
        return fail("不能禁用超级管理员账号")
    new_status = "inactive" if user["status"] == "active" else "active"
    execute("UPDATE users SET status = %s WHERE username = %s", (new_status, username))
    add_log(None, None, "user_toggle", {"summary": "%s用户：%s（%s）" % ("禁用" if new_status == "inactive" else "启用", user["name"], username)}, admin["username"], admin["name"])
    return ok({"status": new_status}, "已" + ("禁用" if new_status == "inactive" else "启用") + "该账号")


@app.route("/api/users", methods=["POST"])
def create_user():
    admin, err = require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    name = (data.get("name") or "").strip()
    role = (data.get("role") or "doctor").strip()
    phone = (data.get("phone") or "").strip()
    status = (data.get("status") or "active").strip()
    department = (data.get("department") or "").strip()
    license_no = (data.get("license") or "").strip()

    if not username or not password or not name:
        return fail("用户名、密码、真实姓名为必填项")
    if role not in ("admin", "doctor"):
        return fail("角色类型无效")
    if status not in ("active", "inactive", "pending"):
        return fail("账号状态无效")

    existing = query("SELECT username FROM users WHERE username = %s", (username,), one=True)
    if existing:
        return fail("该用户名已存在")

    sql_insert = (
        "INSERT INTO users (username, password, role, name, phone, status, department, "
        "license, create_time) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
    )
    execute(sql_insert, (username, sha256_pwd(password), role, name, phone, status,
                         department, license_no,
                         time.strftime("%Y/%m/%d %H:%M:%S")))
    add_log(None, None, "user_add", {"summary": "新增用户：%s（%s，%s）" % (name, username, role)}, admin["username"], admin["name"])
    return ok(None, "用户添加成功")


@app.route("/api/users/<username>", methods=["PUT"])
def update_user(username):
    admin, err = require_admin()
    if err:
        return err
    data = request.get_json(silent=True) or {}

    user = query("SELECT * FROM users WHERE username = %s", (username,), one=True)
    if not user:
        return fail("用户不存在")

    fields = []
    vals = []

    if data.get("password"):
        fields.append("password = %s")
        vals.append(sha256_pwd(data["password"]))
    if data.get("name"):
        fields.append("name = %s")
        vals.append(data["name"].strip())
    if data.get("role"):
        role = data["role"].strip()
        if role not in ("admin", "doctor"):
            return fail("角色类型无效")
        fields.append("role = %s")
        vals.append(role)
    if "phone" in data:
        fields.append("phone = %s")
        vals.append((data.get("phone") or "").strip())
    if data.get("status"):
        status = data["status"].strip()
        if status not in ("active", "inactive", "pending"):
            return fail("账号状态无效")
        fields.append("status = %s")
        vals.append(status)
    if "department" in data:
        fields.append("department = %s")
        vals.append((data.get("department") or "").strip())
    if "license" in data:
        fields.append("license = %s")
        vals.append((data.get("license") or "").strip())

    if not fields:
        return fail("没有需要更新的字段")

    vals.append(username)
    sql = "UPDATE users SET " + ", ".join(fields) + " WHERE username = %s"
    execute(sql, tuple(vals))
    add_log(None, None, "user_edit", {"summary": "编辑用户：%s（%s）" % (user["name"], username)}, admin["username"], admin["name"])
    return ok(None, "用户信息更新成功")


@app.route("/api/users/<username>", methods=["DELETE"])
def delete_user(username):
    admin, err = require_admin()
    if err:
        return err
    if username == "admin":
        return fail("不能删除超级管理员账号")

    user = query("SELECT * FROM users WHERE username = %s", (username,), one=True)
    if not user:
        return fail("用户不存在")

    execute("DELETE FROM users WHERE username = %s", (username,))
    add_log(None, None, "user_delete", {"summary": "删除用户：%s（%s）" % (user["name"], username)}, admin["username"], admin["name"])
    return ok(None, "用户删除成功")


# ============ 日志接口 ============
@app.route("/api/logs", methods=["GET"])
def list_logs():
    _, err = require_admin()
    if err:
        return err
    herb = (request.args.get("herb") or "").strip()
    action = (request.args.get("action") or "").strip()
    time_filter = (request.args.get("time") or "").strip()
    keyword = (request.args.get("keyword") or "").strip()
    sql = "SELECT * FROM operation_logs WHERE 1=1"
    args = []
    if herb:
        sql += " AND herb_name = %s"
        args.append(herb)
    if action:
        sql += " AND action = %s"
        args.append(action)
    now_ms = int(time.time() * 1000)
    if time_filter == "today":
        sql += " AND timestamp >= %s"
        args.append(_day_start_ms(0))
    elif time_filter == "week":
        sql += " AND timestamp >= %s"
        args.append(now_ms - 7 * 86400000)
    elif time_filter == "month":
        sql += " AND timestamp >= %s"
        args.append(now_ms - 30 * 86400000)
    elif time_filter == "quarter":
        sql += " AND timestamp >= %s"
        args.append(now_ms - 90 * 86400000)
    if keyword:
        like = f"%{keyword}%"
        sql += " AND (operator LIKE %s OR operator_name LIKE %s OR changes LIKE %s OR herb_name LIKE %s)"
        args += [like, like, like, like]
    sql += " ORDER BY timestamp DESC LIMIT 500"
    rows = query(sql, tuple(args))
    return ok([_log_row(r) for r in rows])


# ============ 仪表盘 ============
@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    user, err = require_login()
    if err:
        return err
    herbs = query("SELECT * FROM herbs ORDER BY created_at DESC")
    herb_list = [herb_to_camel(r) for r in herbs]
    total_quantity = sum(h["quantity"] or 0 for h in herb_list)
    low_stock = [h for h in herb_list if (h["quantity"] or 0) <= (h["warningThreshold"] or 200)]
    logs = query("SELECT * FROM operation_logs ORDER BY timestamp DESC LIMIT 100")
    return ok({
        "herbs": herb_list, "totalCount": len(herb_list),
        "totalQuantity": total_quantity, "lowStock": low_stock,
        "logs": [_log_row(r) for r in logs],
    })


# ============ 处方接口（4号核心） ============
STATUS_MAP = {"pending": "待审核", "approved": "已审核", "rejected": "已拒绝", "dispensed": "已发药"}


@app.route("/api/prescriptions", methods=["GET"])
def list_prescriptions():
    user, err = require_login()
    if err:
        return err
    status = (request.args.get("status") or "").strip()
    keyword = (request.args.get("keyword") or "").strip()
    doctor = (request.args.get("doctor") or "").strip()

    sql = "SELECT * FROM prescriptions WHERE 1=1"
    args = []
    if status and status in STATUS_MAP:
        sql += " AND status = %s"
        args.append(status)
    if keyword:
        like = f"%{keyword}%"
        sql += " AND (patient_name LIKE %s OR prescription_no LIKE %s OR diagnosis LIKE %s)"
        args += [like, like, like]
    # 医生只能看自己的处方
    if user["role"] == "doctor":
        sql += " AND doctor_username = %s"
        args.append(user["username"])
    elif doctor:
        sql += " AND doctor_username = %s"
        args.append(doctor)
    sql += " ORDER BY created_at DESC LIMIT 200"

    rows = query(sql, args)
    result = []
    for r in rows:
        items = query("SELECT * FROM prescription_items WHERE prescription_id = %s ORDER BY id", (r["id"],))
        result.append(prescription_to_camel(r, [item_to_camel(i) for i in items]))
    return ok(result)


@app.route("/api/prescriptions/<int:rx_id>", methods=["GET"])
def get_prescription(rx_id):
    user, err = require_login()
    if err:
        return err
    row = query("SELECT * FROM prescriptions WHERE id = %s", (rx_id,), one=True)
    if not row:
        return fail("处方不存在")
    if user["role"] == "doctor" and row["doctor_username"] != user["username"]:
        return fail("无权限查看他人处方", code=403, http=403)
    items = query("SELECT * FROM prescription_items WHERE prescription_id = %s ORDER BY id", (rx_id,))
    return ok(prescription_to_camel(row, [item_to_camel(i) for i in items]))


@app.route("/api/prescriptions", methods=["POST"])
def create_prescription():
    user, err = require_doctor_or_admin()
    if err:
        return err
    d = request.get_json(silent=True) or {}
    patient_name = (d.get("patientName") or "").strip()
    items = d.get("items") or []
    if not patient_name:
        return fail("请填写患者姓名")
    if not items or len(items) == 0:
        return fail("请至少添加一味药材")

    # 生成处方编号
    rx_no = "RX" + time.strftime("%Y%m%d%H%M%S")
    total = 0
    for item in items:
        try:
            dosage_val = float(str(item.get("dosage", "0")).replace("g", "").replace("G", ""))
        except (ValueError, TypeError):
            dosage_val = 0
        qty = int(item.get("quantity", 1))
        price = float(item.get("price", 0))
        total += dosage_val * qty * price

    _, rx_id = execute(
        """INSERT INTO prescriptions
           (prescription_no, patient_name, patient_phone, patient_gender, patient_age,
            doctor_username, doctor_name, department, diagnosis, advice, total_amount, status)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending')""",
        (rx_no, patient_name, d.get("patientPhone"), d.get("patientGender"), d.get("patientAge"),
         user["username"], user["name"], d.get("department") or user.get("department"),
         d.get("diagnosis"), d.get("advice"), round(total, 2)),
    )
    for item in items:
        try:
            dosage_val = float(str(item.get("dosage", "0")).replace("g", "").replace("G", ""))
        except (ValueError, TypeError):
            dosage_val = 0
        qty = int(item.get("quantity", 1))
        price = float(item.get("price", 0))
        subtotal = round(dosage_val * qty * price, 2)
        execute(
            """INSERT INTO prescription_items
               (prescription_id, herb_code, herb_name, dosage, `usage`, quantity, price, subtotal)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (rx_id, item.get("herbCode"), item.get("herbName"), item.get("dosage"),
             item.get("usage"), qty, price, subtotal),
        )
    add_log(None, None, "rx_create", {"summary": "新建处方 %s：患者 %s，%d 味药材" % (rx_no, patient_name, len(items))}, user["username"], user["name"])
    return ok({"id": rx_id, "prescriptionNo": rx_no}, "处方创建成功，等待审核")


@app.route("/api/prescriptions/<int:rx_id>/audit", methods=["PUT"])
def audit_prescription(rx_id):
    user, err = require_admin()
    if err:
        return err
    d = request.get_json(silent=True) or {}
    action = (d.get("action") or "").strip()  # approve / reject
    remark = (d.get("remark") or "").strip()
    if action not in ("approve", "reject"):
        return fail("审核操作不合法")
    row = query("SELECT * FROM prescriptions WHERE id = %s", (rx_id,), one=True)
    if not row:
        return fail("处方不存在")
    if row["status"] != "pending":
        return fail("该处方已审核，不能重复审核")
    new_status = "approved" if action == "approve" else "rejected"
    execute(
        "UPDATE prescriptions SET status=%s, audit_remark=%s, auditor=%s, auditor_name=%s, audit_time=%s WHERE id=%s",
        (new_status, remark, user["username"], user["name"], time.strftime("%Y/%m/%d %H:%M:%S"), rx_id),
    )
    add_log(None, None, "rx_audit", {"summary": "审核处方 #%s（患者 %s）→%s" % (rx_id, row["patient_name"], "通过" if action == "approve" else "拒绝")}, user["username"], user["name"])
    return ok(None, f"处方已{'通过' if action == 'approve' else '拒绝'}")


@app.route("/api/prescriptions/<int:rx_id>/dispense", methods=["PUT"])
def dispense_prescription(rx_id):
    user, err = require_login()
    if err:
        return err
    row = query("SELECT * FROM prescriptions WHERE id = %s", (rx_id,), one=True)
    if not row:
        return fail("处方不存在")
    if row["status"] != "approved":
        return fail("只有已审核的处方才能发药")
    items = query("SELECT * FROM prescription_items WHERE prescription_id = %s", (rx_id,))
    # 扣减库存
    for item in items:
        herb = query("SELECT * FROM herbs WHERE code = %s", (item["herb_code"],), one=True)
        if herb:
            try:
                dosage_val = float(str(item["dosage"]).replace("g", ""))
            except (ValueError, TypeError):
                dosage_val = 0
            deduct = int(dosage_val * item["quantity"])
            new_qty = max(0, herb["quantity"] - deduct)
            execute("UPDATE herbs SET quantity=%s WHERE code=%s", (new_qty, item["herb_code"]))
            add_stock_transaction(
                item["herb_code"], item["herb_name"], "out", -deduct,
                reference_type="prescription", reference_id=str(rx_id),
                remark=f"处方发药扣减: {row['prescription_no']}",
                operator=user["username"], operator_name=user["name"]
            )
    execute(
        "UPDATE prescriptions SET status='dispensed', dispenser=%s, dispenser_name=%s, dispense_time=%s WHERE id=%s",
        (user["username"], user["name"], time.strftime("%Y/%m/%d %H:%M:%S"), rx_id),
    )
    add_log(None, None, "rx_dispense", {"summary": "处方发药 #%s（患者 %s），扣减 %d 味药材库存" % (rx_id, row["patient_name"], len(items))}, user["username"], user["name"])
    return ok(None, "处方发药成功，库存已扣减")


@app.route("/api/prescriptions/<int:rx_id>", methods=["DELETE"])
def delete_prescription(rx_id):
    user, err = require_admin()
    if err:
        return err
    row = query("SELECT * FROM prescriptions WHERE id = %s", (rx_id,), one=True)
    if not row:
        return fail("处方不存在")
    if row["status"] == "dispensed":
        return fail("已发药的处方不能删除")
    execute("DELETE FROM prescription_items WHERE prescription_id = %s", (rx_id,))
    execute("DELETE FROM prescriptions WHERE id = %s", (rx_id,))
    add_log(None, None, "rx_delete", {"summary": "删除处方 #%s（患者 %s）" % (rx_id, row["patient_name"])}, user["username"], user["name"])
    return ok(None, "处方删除成功")


# ============ 数据统计接口（4号核心 - ECharts数据看板） ============
@app.route("/api/stats/overview", methods=["GET"])
def stats_overview():
    user, err = require_login()
    if err:
        return err
    # 处方统计
    total_rx = query("SELECT COUNT(*) as cnt FROM prescriptions", one=True)["cnt"]
    pending_rx = query("SELECT COUNT(*) as cnt FROM prescriptions WHERE status='pending'", one=True)["cnt"]
    approved_rx = query("SELECT COUNT(*) as cnt FROM prescriptions WHERE status='approved'", one=True)["cnt"]
    dispensed_rx = query("SELECT COUNT(*) as cnt FROM prescriptions WHERE status='dispensed'", one=True)["cnt"]
    rejected_rx = query("SELECT COUNT(*) as cnt FROM prescriptions WHERE status='rejected'", one=True)["cnt"]
    total_amount = query("SELECT COALESCE(SUM(total_amount),0) as amt FROM prescriptions WHERE status IN ('approved','dispensed')", one=True)["amt"]

    # 药材统计
    total_herbs = query("SELECT COUNT(*) as cnt FROM herbs", one=True)["cnt"]
    total_stock = query("SELECT COALESCE(SUM(quantity),0) as qty FROM herbs", one=True)["qty"]
    low_stock = query("SELECT COUNT(*) as cnt FROM herbs WHERE quantity <= warning_threshold", one=True)["cnt"]

    # 用户统计
    total_users = query("SELECT COUNT(*) as cnt FROM users", one=True)["cnt"]
    doctor_count = query("SELECT COUNT(*) as cnt FROM users WHERE role='doctor'", one=True)["cnt"]

    return ok({
        "prescriptions": {"total": total_rx, "pending": pending_rx, "approved": approved_rx,
                           "dispensed": dispensed_rx, "rejected": rejected_rx,
                           "totalAmount": float(total_amount)},
        "herbs": {"total": total_herbs, "totalStock": total_stock, "lowStock": low_stock},
        "users": {"total": total_users, "doctors": doctor_count},
    })


@app.route("/api/stats/prescription-trend", methods=["GET"])
def stats_prescription_trend():
    user, err = require_login()
    if err:
        return err
    days = int(request.args.get("days", 7))
    import datetime
    today = datetime.date.today()
    start_date = (today - datetime.timedelta(days=days - 1)).strftime("%Y-%m-%d")
    # 兼容 MySQL 和 SQLite：用日期字符串比较
    rows = query("""
        SELECT DATE(created_at) as dt, COUNT(*) as cnt, COALESCE(SUM(total_amount),0) as amt
        FROM prescriptions
        WHERE DATE(created_at) >= %s
        GROUP BY DATE(created_at)
        ORDER BY dt ASC
    """, (start_date,))
    date_map = {str(r["dt"]): {"count": r["cnt"], "amount": float(r["amt"])} for r in rows}
    import datetime
    dates = []
    counts = []
    amounts = []
    today = datetime.date.today()
    for i in range(days - 1, -1, -1):
        d = today - datetime.timedelta(days=i)
        ds = d.strftime("%Y-%m-%d")
        dates.append(ds)
        counts.append(date_map.get(ds, {}).get("count", 0))
        amounts.append(round(date_map.get(ds, {}).get("amount", 0), 2))
    return ok({"dates": dates, "counts": counts, "amounts": amounts})


@app.route("/api/stats/status-distribution", methods=["GET"])
def stats_status_distribution():
    user, err = require_login()
    if err:
        return err
    rows = query("SELECT status, COUNT(*) as cnt FROM prescriptions GROUP BY status")
    return ok([{"name": STATUS_MAP.get(r["status"], r["status"]), "value": r["cnt"]} for r in rows])


@app.route("/api/stats/herb-consumption", methods=["GET"])
def stats_herb_consumption():
    user, err = require_login()
    if err:
        return err
    # 已发药处方中的药材消耗排行
    rows = query("""
        SELECT pi.herb_name, SUM(CAST(REPLACE(pi.dosage,'g','') AS REAL) * pi.quantity) as total_usage
        FROM prescription_items pi
        JOIN prescriptions p ON pi.prescription_id = p.id
        WHERE p.status = 'dispensed'
        GROUP BY pi.herb_name
        ORDER BY total_usage DESC
        LIMIT 10
    """)
    return ok([{"name": r["herb_name"], "value": float(r["total_usage"])} for r in rows])


@app.route("/api/stats/doctor-workload", methods=["GET"])
def stats_doctor_workload():
    user, err = require_login()
    if err:
        return err
    rows = query("""
        SELECT doctor_name, COUNT(*) as cnt, COALESCE(SUM(total_amount),0) as amt
        FROM prescriptions
        WHERE doctor_name IS NOT NULL
        GROUP BY doctor_name
        ORDER BY cnt DESC
    """)
    return ok([{"name": r["doctor_name"], "count": r["cnt"], "amount": float(r["amt"])} for r in rows])


@app.route("/api/stats/category-distribution", methods=["GET"])
def stats_category_distribution():
    user, err = require_login()
    if err:
        return err
    rows = query("""
        SELECT category, COUNT(*) as cnt, COALESCE(SUM(quantity),0) as qty
        FROM herbs
        WHERE category IS NOT NULL AND category != ''
        GROUP BY category
        ORDER BY cnt DESC
    """)
    return ok([{"name": r["category"], "count": r["cnt"], "stock": r["qty"]} for r in rows])


# ============ 供应商管理 API ============
@app.route("/api/suppliers", methods=["GET"])
def list_suppliers():
    user, err = require_login()
    if err:
        return err
    keyword = (request.args.get("q") or "").strip()
    if keyword:
        like = f"%{keyword}%"
        rows = query("SELECT * FROM suppliers WHERE name LIKE %s OR contact_person LIKE %s ORDER BY id DESC", (like, like))
    else:
        rows = query("SELECT * FROM suppliers ORDER BY id DESC")
    return ok([{
        "id": r["id"], "name": r["name"], "contactPerson": r["contact_person"],
        "phone": r["phone"], "address": r["address"], "description": r["description"],
        "status": r["status"], "createdAt": str(r["created_at"]) if r["created_at"] else None,
    } for r in rows])


@app.route("/api/suppliers", methods=["POST"])
def add_supplier():
    user, err = require_admin()
    if err:
        return err
    d = request.get_json(silent=True) or {}
    name = (d.get("name") or "").strip()
    if not name:
        return fail("请填写供应商名称")
    execute(
        """INSERT INTO suppliers (name,contact_person,phone,address,description,status)
           VALUES (%s,%s,%s,%s,%s,%s)""",
        (name, d.get("contactPerson"), d.get("phone"), d.get("address"),
         d.get("description"), d.get("status", "active"))
    )
    add_log(None, None, "supplier_add", {"summary": "新增供应商：%s" % name}, user["username"], user["name"])
    return ok(None, "供应商添加成功")


@app.route("/api/suppliers/<int:sid>", methods=["PUT"])
def update_supplier(sid):
    user, err = require_admin()
    if err:
        return err
    d = request.get_json(silent=True) or {}
    old = query("SELECT * FROM suppliers WHERE id = %s", (sid,), one=True)
    if not old:
        return fail("供应商不存在")
    execute(
        """UPDATE suppliers SET name=%s, contact_person=%s, phone=%s, address=%s,
           description=%s, status=%s WHERE id=%s""",
        (d.get("name", old["name"]), d.get("contactPerson", old["contact_person"]),
         d.get("phone", old["phone"]), d.get("address", old["address"]),
         d.get("description", old["description"]), d.get("status", old["status"]), sid)
    )
    add_log(None, None, "supplier_edit", {"summary": "编辑供应商：%s（#%s）" % (old["name"], sid)}, user["username"], user["name"])
    return ok(None, "供应商更新成功")


@app.route("/api/suppliers/<int:sid>", methods=["DELETE"])
def delete_supplier(sid):
    user, err = require_admin()
    if err:
        return err
    old = query("SELECT * FROM suppliers WHERE id = %s", (sid,), one=True)
    execute("DELETE FROM suppliers WHERE id = %s", (sid,))
    add_log(None, None, "supplier_delete", {"summary": "删除供应商：%s（#%s）" % (old["name"] if old else sid, sid)}, user["username"], user["name"])
    return ok(None, "供应商删除成功")


# ============ 采购管理 API ============
PO_STATUS_MAP = {"pending": "待审核", "approved": "已审核", "completed": "已入库", "rejected": "已拒绝", "cancelled": "已取消"}


@app.route("/api/purchase-orders", methods=["GET"])
def list_purchase_orders():
    user, err = require_login()
    if err:
        return err
    status = (request.args.get("status") or "").strip()
    keyword = (request.args.get("keyword") or "").strip()
    sql = "SELECT * FROM purchase_orders WHERE 1=1"
    args = []
    if status and status in PO_STATUS_MAP:
        sql += " AND status = %s"
        args.append(status)
    if keyword:
        like = f"%{keyword}%"
        sql += " AND (order_no LIKE %s OR supplier_name LIKE %s)"
        args += [like, like]
    sql += " ORDER BY created_at DESC LIMIT 200"
    rows = query(sql, args)
    result = []
    for r in rows:
        items = query("SELECT * FROM purchase_items WHERE purchase_id = %s ORDER BY id", (r["id"],))
        result.append({
            "id": r["id"], "orderNo": r["order_no"], "supplierId": r["supplier_id"],
            "supplierName": r["supplier_name"], "totalAmount": float(r["total_amount"]) if r["total_amount"] else 0,
            "status": r["status"], "statusText": PO_STATUS_MAP.get(r["status"], r["status"]),
            "remark": r["remark"], "creator": r["creator"], "creatorName": r["creator_name"],
            "auditor": r["auditor"], "auditorName": r["auditor_name"], "auditTime": r["audit_time"],
            "inStockTime": r["in_stock_time"], "createdAt": str(r["created_at"]) if r["created_at"] else None,
            "items": [{
                "id": i["id"], "herbCode": i["herb_code"], "herbName": i["herb_name"],
                "quantity": i["quantity"], "unit": i["unit"], "price": float(i["price"]) if i["price"] else 0,
                "subtotal": float(i["subtotal"]) if i["subtotal"] else 0,
                "receivedQuantity": i["received_quantity"],
            } for i in items],
        })
    return ok(result)


@app.route("/api/purchase-orders/<int:po_id>", methods=["GET"])
def get_purchase_order(po_id):
    user, err = require_login()
    if err:
        return err
    row = query("SELECT * FROM purchase_orders WHERE id = %s", (po_id,), one=True)
    if not row:
        return fail("采购单不存在")
    items = query("SELECT * FROM purchase_items WHERE purchase_id = %s ORDER BY id", (po_id,))
    return ok({
        "id": row["id"], "orderNo": row["order_no"], "supplierId": row["supplier_id"],
        "supplierName": row["supplier_name"], "totalAmount": float(row["total_amount"]) if row["total_amount"] else 0,
        "status": row["status"], "statusText": PO_STATUS_MAP.get(row["status"], row["status"]),
        "remark": row["remark"], "creator": row["creator"], "creatorName": row["creator_name"],
        "auditor": row["auditor"], "auditorName": row["auditor_name"], "auditTime": row["audit_time"],
        "inStockTime": row["in_stock_time"], "createdAt": str(row["created_at"]) if row["created_at"] else None,
        "items": [{
            "id": i["id"], "herbCode": i["herb_code"], "herbName": i["herb_name"],
            "quantity": i["quantity"], "unit": i["unit"], "price": float(i["price"]) if i["price"] else 0,
            "subtotal": float(i["subtotal"]) if i["subtotal"] else 0,
            "receivedQuantity": i["received_quantity"],
        } for i in items],
    })


@app.route("/api/purchase-orders", methods=["POST"])
def create_purchase_order():
    user, err = require_login()
    if err:
        return err
    d = request.get_json(silent=True) or {}
    items = d.get("items") or []
    supplier_id = d.get("supplierId")
    supplier_name = d.get("supplierName") or ""
    if not items or len(items) == 0:
        return fail("请至少添加一味药材")
    if not supplier_name and not supplier_id:
        return fail("请选择供应商")
    if supplier_id and not supplier_name:
        sup = query("SELECT name FROM suppliers WHERE id = %s", (supplier_id,), one=True)
        supplier_name = sup["name"] if sup else ""

    po_no = "PO" + time.strftime("%Y%m%d%H%M%S")
    total = 0
    for item in items:
        total += float(item.get("quantity", 0)) * float(item.get("price", 0))

    _, po_id = execute(
        """INSERT INTO purchase_orders
           (order_no,supplier_id,supplier_name,total_amount,status,remark,creator,creator_name)
           VALUES (%s,%s,%s,%s,'pending',%s,%s,%s)""",
        (po_no, supplier_id, supplier_name, round(total, 2), d.get("remark"),
         user["username"], user["name"])
    )
    for item in items:
        qty = int(item.get("quantity", 0))
        price = float(item.get("price", 0))
        subtotal = round(qty * price, 2)
        execute(
            """INSERT INTO purchase_items
               (purchase_id,herb_code,herb_name,quantity,unit,price,subtotal,received_quantity)
               VALUES (%s,%s,%s,%s,%s,%s,%s,0)""",
            (po_id, item.get("herbCode"), item.get("herbName"), qty,
             item.get("unit", "g"), price, subtotal)
        )
    add_log(None, None, "po_create", {"summary": "创建采购单 %s：供应商 %s，%d 项，总额 %.2f" % (po_no, supplier_name, len(items), total)}, user["username"], user["name"])
    return ok({"id": po_id, "orderNo": po_no}, "采购单创建成功，等待审核")


@app.route("/api/purchase-orders/<int:po_id>/audit", methods=["PUT"])
def audit_purchase_order(po_id):
    user, err = require_admin()
    if err:
        return err
    d = request.get_json(silent=True) or {}
    action = (d.get("action") or "").strip()
    if action not in ("approve", "reject"):
        return fail("审核操作不合法")
    row = query("SELECT * FROM purchase_orders WHERE id = %s", (po_id,), one=True)
    if not row:
        return fail("采购单不存在")
    if row["status"] != "pending":
        return fail("该采购单已审核，不能重复审核")
    new_status = "approved" if action == "approve" else "rejected"
    execute(
        "UPDATE purchase_orders SET status=%s, auditor=%s, auditor_name=%s, audit_time=%s WHERE id=%s",
        (new_status, user["username"], user["name"], time.strftime("%Y/%m/%d %H:%M:%S"), po_id)
    )
    add_log(None, None, "po_audit", {"summary": "审核采购单 %s →%s" % (row["order_no"], "通过" if action == "approve" else "拒绝")}, user["username"], user["name"])
    return ok(None, f"采购单已{'通过' if action == 'approve' else '拒绝'}")


@app.route("/api/purchase-orders/<int:po_id>/in-stock", methods=["PUT"])
def purchase_order_in_stock(po_id):
    user, err = require_login()
    if err:
        return err
    row = query("SELECT * FROM purchase_orders WHERE id = %s", (po_id,), one=True)
    if not row:
        return fail("采购单不存在")
    if row["status"] != "approved":
        return fail("只有已审核的采购单才能入库")
    items = query("SELECT * FROM purchase_items WHERE purchase_id = %s", (po_id,))
    # 入库：增加库存
    for item in items:
        herb = query("SELECT * FROM herbs WHERE code = %s", (item["herb_code"],), one=True)
        if herb:
            new_qty = herb["quantity"] + item["quantity"]
            execute("UPDATE herbs SET quantity=%s WHERE code=%s", (new_qty, item["herb_code"]))
            add_stock_transaction(
                item["herb_code"], item["herb_name"], "in", item["quantity"],
                reference_type="purchase", reference_id=str(po_id),
                remark=f"采购入库: {row['order_no']}",
                operator=user["username"], operator_name=user["name"]
            )
        execute("UPDATE purchase_items SET received_quantity = %s WHERE id = %s",
                (item["quantity"], item["id"]))
    execute(
        "UPDATE purchase_orders SET status='completed', in_stock_time=%s WHERE id=%s",
        (time.strftime("%Y/%m/%d %H:%M:%S"), po_id)
    )
    add_log(None, None, "po_in_stock", {"summary": "采购入库 %s：%d 项药材，库存已增加" % (row["order_no"], len(items))}, user["username"], user["name"])
    return ok(None, "采购入库成功，库存已更新")


@app.route("/api/purchase-orders/<int:po_id>", methods=["DELETE"])
def delete_purchase_order(po_id):
    user, err = require_admin()
    if err:
        return err
    row = query("SELECT * FROM purchase_orders WHERE id = %s", (po_id,), one=True)
    if not row:
        return fail("采购单不存在")
    if row["status"] == "completed":
        return fail("已入库的采购单不能删除")
    execute("DELETE FROM purchase_items WHERE purchase_id = %s", (po_id,))
    execute("DELETE FROM purchase_orders WHERE id = %s", (po_id,))
    add_log(None, None, "po_delete", {"summary": "删除采购单 %s" % row["order_no"]}, user["username"], user["name"])
    return ok(None, "采购单删除成功")


# ============ 库存流水 API ============
@app.route("/api/stock-transactions", methods=["GET"])
def list_stock_transactions():
    user, err = require_login()
    if err:
        return err
    herb_code = (request.args.get("herbCode") or "").strip()
    tx_type = (request.args.get("type") or "").strip()
    sql = "SELECT * FROM stock_transactions WHERE 1=1"
    args = []
    if herb_code:
        sql += " AND herb_code = %s"
        args.append(herb_code)
    if tx_type:
        sql += " AND type = %s"
        args.append(tx_type)
    sql += " ORDER BY created_at DESC LIMIT 500"
    rows = query(sql, args)
    return ok([{
        "id": r["id"], "herbCode": r["herb_code"], "herbName": r["herb_name"],
        "type": r["type"], "typeText": "入库" if r["type"] == "in" else "出库" if r["type"] == "out" else r["type"],
        "quantity": r["quantity"], "balanceAfter": r["balance_after"],
        "referenceType": r["reference_type"], "referenceId": r["reference_id"],
        "remark": r["remark"], "operator": r["operator"], "operatorName": r["operator_name"],
        "createdAt": str(r["created_at"]) if r["created_at"] else None,
    } for r in rows])


# ============ 库存预警 API ============
@app.route("/api/stock/warnings", methods=["GET"])
def stock_warnings():
    user, err = require_login()
    if err:
        return err
    rows = query("""
        SELECT * FROM herbs
        WHERE quantity <= warning_threshold
        ORDER BY (quantity * 1.0 / warning_threshold) ASC
    """)
    return ok([{
        "code": r["code"], "name": r["name"], "category": r["category"],
        "quantity": r["quantity"], "warningThreshold": r["warning_threshold"],
        "unit": r["unit"], "price": float(r["price"]) if r["price"] else 0,
        "shortage": max(0, r["warning_threshold"] - r["quantity"]),
        "status": "critical" if r["quantity"] == 0 else "warning",
    } for r in rows])


# ============ 智能补货推荐 API ============
@app.route("/api/stock/replenish-suggestions", methods=["GET"])
def replenish_suggestions():
    user, err = require_login()
    if err:
        return err
    days = int(request.args.get("days", 30))
    # 基于历史消耗计算日均消耗量
    import datetime
    start_date = (datetime.date.today() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")

    # 获取所有药材
    herbs = query("SELECT * FROM herbs ORDER BY code")
    suggestions = []

    for herb in herbs:
        # 统计该药材在指定时间段内的消耗量（从已发药处方中计算）
        rows = query("""
            SELECT COALESCE(SUM(CAST(REPLACE(pi.dosage,'g','') AS REAL) * pi.quantity), 0) as total_usage
            FROM prescription_items pi
            JOIN prescriptions p ON pi.prescription_id = p.id
            WHERE p.status = 'dispensed'
              AND pi.herb_code = %s
              AND DATE(p.dispense_time) >= %s
        """, (herb["code"], start_date))
        total_usage = float(rows[0]["total_usage"]) if rows else 0
        daily_avg = round(total_usage / days, 1) if days > 0 else 0

        # 计算可维持天数
        days_remaining = round(herb["quantity"] / daily_avg, 1) if daily_avg > 0 else 999

        # 建议补货量 = 30天消耗量 - 当前库存（如果为正）
        suggest_qty = max(0, int(daily_avg * 30) - herb["quantity"])

        # 优先级判断
        if herb["quantity"] <= 0:
            priority = "critical"
        elif days_remaining <= 7:
            priority = "high"
        elif days_remaining <= 15:
            priority = "medium"
        elif suggest_qty > 0:
            priority = "low"
        else:
            continue

        suggestions.append({
            "code": herb["code"], "name": herb["name"], "category": herb["category"],
            "currentStock": herb["quantity"], "warningThreshold": herb["warning_threshold"],
            "dailyAvgUsage": daily_avg, "daysRemaining": days_remaining,
            "suggestedQuantity": suggest_qty, "unit": herb["unit"],
            "price": float(herb["price"]) if herb["price"] else 0,
            "estimatedCost": round(suggest_qty * float(herb["price"] or 0), 2),
            "priority": priority,
        })

    # 按优先级排序
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    suggestions.sort(key=lambda x: (priority_order.get(x["priority"], 9), x["daysRemaining"]))

    return ok({
        "days": days,
        "totalSuggestions": len(suggestions),
        "totalEstimatedCost": round(sum(s["estimatedCost"] for s in suggestions), 2),
        "items": suggestions,
    })


# ============ 采购统计 API ============
@app.route("/api/stats/purchase-overview", methods=["GET"])
def stats_purchase_overview():
    user, err = require_login()
    if err:
        return err
    total_po = query("SELECT COUNT(*) as cnt FROM purchase_orders", one=True)["cnt"]
    pending_po = query("SELECT COUNT(*) as cnt FROM purchase_orders WHERE status='pending'", one=True)["cnt"]
    completed_po = query("SELECT COUNT(*) as cnt FROM purchase_orders WHERE status='completed'", one=True)["cnt"]
    total_amount = query("SELECT COALESCE(SUM(total_amount),0) as amt FROM purchase_orders WHERE status='completed'", one=True)["amt"]
    total_in = query("SELECT COALESCE(SUM(quantity),0) as qty FROM stock_transactions WHERE type='in'", one=True)["qty"]
    total_out = query("SELECT COALESCE(SUM(ABS(quantity)),0) as qty FROM stock_transactions WHERE type='out'", one=True)["qty"]
    return ok({
        "purchaseOrders": {"total": total_po, "pending": pending_po, "completed": completed_po,
                           "totalAmount": float(total_amount)},
        "stockFlow": {"totalIn": total_in, "totalOut": total_out},
    })


if __name__ == "__main__":
    print("=" * 50)
    print("  本草智管平台 - 4号模块（处方管理 + 数据看板）")
    print("=" * 50)
    print(f"前端目录: {os.path.abspath(FRONTEND_DIR)}")
    print("访问地址: http://127.0.0.1:5000")
    print("默认账号: admin/123456 (管理员)")
    print("          doctor/123456 (医生)")
    print("=" * 50)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
