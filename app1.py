from flask import Flask, render_template, request, jsonify
import sqlite3

app = Flask(__name__)
app.secret_key = "meod-secret-key"

DB_NAME = "database.db"

# ---------- DATABASE CONNECTION ----------
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# ---------- INITIALIZE DATABASE ----------
def init_db():
    conn = get_db()
    cur = conn.cursor()

    # Accounts table (LOGIN / AUTH)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            system_role TEXT NOT NULL,  -- customer / employee / admin
            staff_id TEXT
        )
    """)

    # Employees table (PROFILE / MANAGEMENT)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id TEXT UNIQUE,
            full_name TEXT,
            department TEXT,
            role TEXT,
                
            work_email TEXT
        )
    """)

    conn.commit()
    conn.close()

# ---------- BASIC TEST ROUTE ----------
@app.route("/")
def index():
    return "Group Flask App is running"

# ---------- RUN ----------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
