from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import sqlite3
import secrets
import string

app = Flask(__name__)
app.secret_key = "meod-secret-key"
DB_NAME = "database.db"


# =========================================================
# Helpers
# =========================================================
def db_conn():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def generate_customer_id():
    alphabet = string.ascii_uppercase + string.digits
    token = "".join(secrets.choice(alphabet) for _ in range(8))
    return f"CUST-{token}"


def logged_in_employee():
    return "employee_staff_id" in session


def logged_in_customer():
    return "customer_id" in session


def is_admin():
    return session.get("employee_role") == "admin"


def require_employee_login():
    if not logged_in_employee():
        return redirect(url_for("employeeloginpage"))
    return None


def get_customer_by_session():
    if "customer_id" not in session:
        return None
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers WHERE id = ?", (session["customer_id"],))
    row = cur.fetchone()
    conn.close()
    return row


def get_employee_by_session():
    if "employee_staff_id" not in session:
        return None
    staff_id = session["employee_staff_id"]
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            u.staff_id, u.full_name, u.department, u.role, u.work_email,
            ea.is_admin, ea.last_seen
        FROM users u
        LEFT JOIN employee_auth ea ON ea.staff_id = u.staff_id
        WHERE u.staff_id = ?
    """, (staff_id,))
    row = cur.fetchone()
    conn.close()
    return row


# =========================================================
# Database init
# =========================================================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # Employee directory table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            department TEXT NOT NULL,
            role TEXT NOT NULL,
            work_email TEXT NOT NULL
        )
    """)

    # Employee login + admin flag + last_seen + mgmt_password (SEPARATE)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS employee_auth (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0,
            mgmt_password TEXT,
            last_seen DATETIME
        )
    """)

    # Customers table (random customer_id)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT,
            email_address TEXT,
            phone_number TEXT,
            address TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Seed employees
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        employees = [
            ("EMP001", "John Doe", "IT", "Developer", "john@meod.com"),
            ("EMP002", "Jane Smith", "HR", "Manager", "jane@meod.com"),
            ("EMP003", "Bob Wilson", "Finance", "Analyst", "bob@meod.com"),
        ]
        cur.executemany("""
            INSERT INTO users (staff_id, full_name, department, role, work_email)
            VALUES (?, ?, ?, ?, ?)
        """, employees)

    # Seed employee logins (EMP001 is admin)
    cur.execute("SELECT COUNT(*) FROM employee_auth")
    if cur.fetchone()[0] == 0:
        # IMPORTANT:
        # - "password123" is NORMAL employee login password
        # - "admin12345" is MANAGEMENT password for EMP001 (separate)
        logins = [
            ("EMP001", "password123", 1, "admin12345"),
            ("EMP002", "password123", 0, None),
            ("EMP003", "password123", 0, None),
        ]
        cur.executemany("""
            INSERT INTO employee_auth (staff_id, password, is_admin, mgmt_password)
            VALUES (?, ?, ?, ?)
        """, logins)

    conn.commit()
    conn.close()


# =========================================================
# Start Page
# =========================================================
@app.route("/")
def root():
    return redirect(url_for("startpage"))

@app.route("/startpage")
def startpage():
    return render_template("startpage.html")


# =========================================================
# Customer Auth + Pages
# =========================================================
@app.route("/customerloginpage")
def customerloginpage():
    success = request.args.get("success", "")
    return render_template("customerloginpage.html", success=success)

@app.route("/customersignup", methods=["GET", "POST"])
def customersignup():
    if request.method == "GET":
        return render_template("customersignup.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not username or not password:
        return render_template("customersignup.html", error="Please fill in all fields.")
    if len(password) < 8:
        return render_template("customersignup.html", error="Password must be at least 8 characters.")

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    for _ in range(10):
        cust_id = generate_customer_id()
        try:
            cur.execute("""
                INSERT INTO customers (customer_id, username, password)
                VALUES (?, ?, ?)
            """, (cust_id, username, password))
            conn.commit()
            conn.close()
            return redirect(url_for("customerloginpage", success="1"))
        except sqlite3.IntegrityError:
            cur.execute("SELECT 1 FROM customers WHERE username = ?", (username,))
            if cur.fetchone():
                conn.close()
                return render_template("customersignup.html", error="Username already exists.")

    conn.close()
    return render_template("customersignup.html", error="System error. Please try again.")

@app.route("/customerlogin", methods=["POST"])
def customerlogin_post():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    conn = db_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers WHERE username = ? AND password = ?", (username, password))
    user = cur.fetchone()
    conn.close()

    if not user:
        return render_template("customerloginpage.html", error="Invalid username or password.")

    session["customer_id"] = user["id"]
    session["customer_username"] = user["username"]
    return redirect(url_for("customerhomepage"))

@app.route("/customerhomepage")
def customerhomepage():
    customer = get_customer_by_session()
    if not customer:
        return redirect(url_for("customerloginpage"))
    return render_template("customerhomepage.html", customer=customer)

@app.route("/customerprofile")
def customerprofile():
    customer = get_customer_by_session()
    if not customer:
        return redirect(url_for("customerloginpage"))
    return render_template("customerprofile.html", customer=customer)

@app.route("/customerlogout")
def customerlogout():
    session.pop("customer_id", None)
    session.pop("customer_username", None)
    return redirect(url_for("startpage"))


# =========================================================
# Employee Auth + Pages
# =========================================================
@app.route("/employeeloginpage")
def employeeloginpage():
    return render_template("employeeloginpage.html")

@app.route("/employeelogin", methods=["POST"])
def employeelogin_post():
    staff_id = request.form.get("staff_id", "").strip().upper()
    password = request.form.get("password", "").strip()

    conn = db_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM employee_auth WHERE staff_id = ? AND password = ?", (staff_id, password))
    emp = cur.fetchone()

    if emp:
        cur.execute("UPDATE employee_auth SET last_seen = CURRENT_TIMESTAMP WHERE staff_id = ?", (staff_id,))
        conn.commit()

    conn.close()

    if not emp:
        return render_template("employeeloginpage.html", error="Invalid Staff ID or password.")

    session["employee_staff_id"] = emp["staff_id"]
    session["employee_role"] = "admin" if emp["is_admin"] == 1 else "employee"

    # reset management locks each time employee logs in
    session.pop("mgmt_user_ok", None)
    session.pop("mgmt_session_ok", None)

    return redirect(url_for("employeehomepage"))

@app.route("/employeehomepage")
def employeehomepage():
    emp = get_employee_by_session()
    if not emp:
        return redirect(url_for("employeeloginpage"))
    return render_template("employeehomepage.html", employee=emp)

@app.route("/employeeprofile")
def employeeprofile():
    emp = get_employee_by_session()
    if not emp:
        return redirect(url_for("employeeloginpage"))
    return render_template("employeeprofile.html", employee=emp)

@app.route("/employeelogout")
def employeelogout():
    session.pop("employee_staff_id", None)
    session.pop("employee_role", None)
    session.pop("mgmt_user_ok", None)
    session.pop("mgmt_session_ok", None)
    return redirect(url_for("startpage"))


# =========================================================
# Access Denied
# =========================================================
@app.route("/accessdenied")
def accessdenied():
    return render_template("accessdenied.html")


# =========================================================
# Management Landing Page
# IMPORTANT: Management login uses MANAGEMENT PASSWORD (mgmt_password), NOT normal login password
# =========================================================
@app.route("/management")
def management():
    need = require_employee_login()
    if need:
        return need
    return render_template("management.html", error_user=None, error_session=None)

def _admin_check_management_password(staff_id, mgmt_password):
    staff_id = (staff_id or "").strip().upper()
    mgmt_password = (mgmt_password or "").strip()

    conn = db_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT staff_id, is_admin, mgmt_password
        FROM employee_auth
        WHERE staff_id = ?
    """, (staff_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return False, "Invalid Staff ID."
    if row["is_admin"] != 1:
        return False, "Access denied: Admin rights required."
    if not row["mgmt_password"]:
        return False, "This admin has no Management Password set yet. Ask an admin to set it."
    if row["mgmt_password"] != mgmt_password:
        return False, "Invalid Management Password."
    return True, None

@app.route("/management/userlogin", methods=["POST"])
def management_userlogin():
    need = require_employee_login()
    if need:
        return need

    staff_id = request.form.get("staff_id")
    mgmt_password = request.form.get("password")  # from form input

    ok, msg = _admin_check_management_password(staff_id, mgmt_password)
    if not ok:
        return render_template("management.html", error_user=msg, error_session=None)

    session["mgmt_user_ok"] = True
    session["employee_role"] = "admin"
    return redirect(url_for("usermanagement"))

@app.route("/management/sessionlogin", methods=["POST"])
def management_sessionlogin():
    need = require_employee_login()
    if need:
        return need

    staff_id = request.form.get("staff_id")
    mgmt_password = request.form.get("password")  # from form input

    ok, msg = _admin_check_management_password(staff_id, mgmt_password)
    if not ok:
        return render_template("management.html", error_user=None, error_session=msg)

    session["mgmt_session_ok"] = True
    session["employee_role"] = "admin"
    return redirect(url_for("sessionmanagement"))


# =========================================================
# User Management Page (Admin + unlocked)
# =========================================================
@app.route("/usermanagement")
def usermanagement():
    need = require_employee_login()
    if need:
        return need
    if not is_admin() or not session.get("mgmt_user_ok"):
        return redirect(url_for("management"))
    return render_template("usermanagement.html")


# =========================================================
# Session Management Page (Admin + unlocked)
# =========================================================
@app.route("/sessionmanagement")
def sessionmanagement():
    need = require_employee_login()
    if need:
        return need
    if not is_admin() or not session.get("mgmt_session_ok"):
        return redirect(url_for("management"))
    return render_template("sessionmanagement.html")


# ============================================================
# EMPLOYEE MANAGEMENT APIs (CRUD + reset login pw + set admin + set mgmt pw)
# ============================================================
@app.route("/api/employees")
def api_get_employees():
    if not is_admin() or not session.get("mgmt_user_ok"):
        return jsonify(success=False, message="Admin only"), 403

    conn = db_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.staff_id, u.full_name, u.department, u.role, u.work_email, ea.is_admin
        FROM users u
        LEFT JOIN employee_auth ea ON ea.staff_id = u.staff_id
        ORDER BY u.staff_id
    """)
    data = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(data)

@app.route("/api/employees", methods=["POST"])
def api_add_employee():
    if not is_admin() or not session.get("mgmt_user_ok"):
        return jsonify(success=False, message="Admin only"), 403

    data = request.json or {}
    staff_id = (data.get("staff_id") or "").strip().upper()
    full_name = (data.get("full_name") or "").strip()
    department = (data.get("department") or "").strip()
    role = (data.get("role") or "").strip()
    work_email = (data.get("work_email") or "").strip()

    if not staff_id or not full_name or not department or not role or not work_email:
        return jsonify(success=False, message="Please fill in all fields.")

    try:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO users (staff_id, full_name, department, role, work_email)
            VALUES (?, ?, ?, ?, ?)
        """, (staff_id, full_name, department, role, work_email))

        # Create login too (default password)
        cur.execute("""
            INSERT INTO employee_auth (staff_id, password, is_admin, mgmt_password)
            VALUES (?, ?, 0, NULL)
        """, (staff_id, "password123"))

        conn.commit()
        conn.close()
        return jsonify(success=True, default_password="password123")

    except sqlite3.IntegrityError:
        return jsonify(success=False, message="Staff ID already exists.")

@app.route("/api/employees/<staff_id>", methods=["PUT"])
def api_update_employee(staff_id):
    if not is_admin() or not session.get("mgmt_user_ok"):
        return jsonify(success=False, message="Admin only"), 403

    data = request.json or {}
    full_name = (data.get("full_name") or "").strip()
    department = (data.get("department") or "").strip()
    role = (data.get("role") or "").strip()
    work_email = (data.get("work_email") or "").strip()

    if not full_name or not department or not role or not work_email:
        return jsonify(success=False, message="Please fill in all fields.")

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        UPDATE users
        SET full_name = ?, department = ?, role = ?, work_email = ?
        WHERE staff_id = ?
    """, (full_name, department, role, work_email, staff_id.strip().upper()))
    conn.commit()
    conn.close()
    return jsonify(success=True)

@app.route("/api/employees/<staff_id>", methods=["DELETE"])
def api_delete_employee(staff_id):
    if not is_admin() or not session.get("mgmt_user_ok"):
        return jsonify(success=False, message="Admin only"), 403

    staff_id = staff_id.strip().upper()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE staff_id = ?", (staff_id,))
    cur.execute("DELETE FROM employee_auth WHERE staff_id = ?", (staff_id,))
    conn.commit()
    conn.close()
    return jsonify(success=True)

@app.route("/api/employees/<staff_id>/resetpassword", methods=["POST"])
def api_reset_employee_password(staff_id):
    if not is_admin() or not session.get("mgmt_user_ok"):
        return jsonify(success=False, message="Admin only"), 403

    staff_id = staff_id.strip().upper()
    data = request.json or {}
    new_password = (data.get("new_password") or "").strip()

    if len(new_password) < 8:
        return jsonify(success=False, message="Password must be at least 8 characters.")

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM employee_auth WHERE staff_id = ?", (staff_id,))
    if not cur.fetchone():
        conn.close()
        return jsonify(success=False, message="Employee not found.")

    cur.execute("UPDATE employee_auth SET password = ? WHERE staff_id = ?", (new_password, staff_id))
    conn.commit()
    conn.close()
    return jsonify(success=True)

# NEW: set/remove admin + set management password
@app.route("/api/employees/<staff_id>/admin", methods=["POST"])
def api_set_employee_admin(staff_id):
    if not is_admin() or not session.get("mgmt_user_ok"):
        return jsonify(success=False, message="Admin only"), 403

    staff_id = staff_id.strip().upper()
    data = request.json or {}
    make_admin = bool(data.get("make_admin"))
    mgmt_password = (data.get("mgmt_password") or "").strip()

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # confirm exists
    cur.execute("SELECT password FROM employee_auth WHERE staff_id = ?", (staff_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return jsonify(success=False, message="Employee not found.")

    login_pw = row[0]  # employee login password

    if make_admin:
        if len(mgmt_password) < 8:
            conn.close()
            return jsonify(success=False, message="Management Password must be at least 8 characters.")
        if mgmt_password == login_pw:
            conn.close()
            return jsonify(success=False, message="Management Password must be different from login password.")

        cur.execute("""
            UPDATE employee_auth
            SET is_admin = 1, mgmt_password = ?
            WHERE staff_id = ?
        """, (mgmt_password, staff_id))
    else:
        # remove admin rights + remove management password
        cur.execute("""
            UPDATE employee_auth
            SET is_admin = 0, mgmt_password = NULL
            WHERE staff_id = ?
        """, (staff_id,))

    conn.commit()
    conn.close()
    return jsonify(success=True)


# ============================================================
# CUSTOMER MANAGEMENT APIs (CRUD + reset password)
# ============================================================
@app.route("/api/customers")
def api_get_customers():
    if not is_admin() or not session.get("mgmt_user_ok"):
        return jsonify(success=False, message="Admin only"), 403

    conn = db_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT customer_id, username, full_name, email_address, phone_number
        FROM customers
        ORDER BY created_at DESC
    """)
    data = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(data)

@app.route("/api/customers", methods=["POST"])
def api_add_customer():
    if not is_admin() or not session.get("mgmt_user_ok"):
        return jsonify(success=False, message="Admin only"), 403

    data = request.json or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    full_name = (data.get("full_name") or "").strip()
    email_address = (data.get("email_address") or "").strip()
    phone_number = (data.get("phone_number") or "").strip()

    if not username or not password:
        return jsonify(success=False, message="Username and password are required.")
    if len(password) < 8:
        return jsonify(success=False, message="Password must be at least 8 characters.")

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    for _ in range(10):
        cust_id = generate_customer_id()
        try:
            cur.execute("""
                INSERT INTO customers (customer_id, username, password, full_name, email_address, phone_number)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (cust_id, username, password, full_name, email_address, phone_number))
            conn.commit()
            conn.close()
            return jsonify(success=True, customer_id=cust_id)
        except sqlite3.IntegrityError:
            cur.execute("SELECT 1 FROM customers WHERE username = ?", (username,))
            if cur.fetchone():
                conn.close()
                return jsonify(success=False, message="Username already exists.")

    conn.close()
    return jsonify(success=False, message="System error. Try again.")

@app.route("/api/customers/<customer_id>", methods=["PUT"])
def api_update_customer(customer_id):
    if not is_admin() or not session.get("mgmt_user_ok"):
        return jsonify(success=False, message="Admin only"), 403

    data = request.json or {}
    username = (data.get("username") or "").strip()
    full_name = (data.get("full_name") or "").strip()
    email_address = (data.get("email_address") or "").strip()
    phone_number = (data.get("phone_number") or "").strip()

    if not username:
        return jsonify(success=False, message="Username is required.")

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("SELECT 1 FROM customers WHERE username = ? AND customer_id != ?", (username, customer_id))
    if cur.fetchone():
        conn.close()
        return jsonify(success=False, message="Username already exists.")

    cur.execute("""
        UPDATE customers
        SET username = ?, full_name = ?, email_address = ?, phone_number = ?
        WHERE customer_id = ?
    """, (username, full_name, email_address, phone_number, customer_id))
    conn.commit()
    conn.close()
    return jsonify(success=True)

@app.route("/api/customers/<customer_id>/resetpassword", methods=["POST"])
def api_reset_customer_password(customer_id):
    if not is_admin() or not session.get("mgmt_user_ok"):
        return jsonify(success=False, message="Admin only"), 403

    data = request.json or {}
    new_password = (data.get("new_password") or "").strip()
    if len(new_password) < 8:
        return jsonify(success=False, message="Password must be at least 8 characters.")

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("UPDATE customers SET password = ? WHERE customer_id = ?", (new_password, customer_id))
    conn.commit()
    conn.close()
    return jsonify(success=True)

@app.route("/api/customers/<customer_id>", methods=["DELETE"])
def api_delete_customer(customer_id):
    if not is_admin() or not session.get("mgmt_user_ok"):
        return jsonify(success=False, message="Admin only"), 403

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM customers WHERE customer_id = ?", (customer_id,))
    conn.commit()
    conn.close()
    return jsonify(success=True)


# ============================================================
# SESSION MANAGEMENT API
# ============================================================
@app.route("/api/sessions")
def api_sessions():
    if not is_admin() or not session.get("mgmt_session_ok"):
        return jsonify(success=False, message="Admin only"), 403

    conn = db_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            u.staff_id,
            u.full_name,
            u.department,
            u.role,
            u.work_email,
            ea.last_seen
        FROM users u
        LEFT JOIN employee_auth ea ON ea.staff_id = u.staff_id
        ORDER BY
            CASE WHEN ea.last_seen IS NULL THEN 1 ELSE 0 END,
            ea.last_seen DESC
    """)
    data = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(data)


# =========================================================
# Run
# =========================================================
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
