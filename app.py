from flask import Flask, render_template, request, jsonify
import sqlite3
from pathlib import Path

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DB = BASE_DIR / "database.db"


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def admin_reviews():
    conn = get_db()
    rows = conn.execute("SELECT * FROM reviews ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("admin_reviews.html", reviews=rows)


@app.route("/update-status", methods=["POST"])
def update_status():
    data = request.get_json(force=True)
    review_id = data.get("id")
    new_status = data.get("status")

    if not review_id or not new_status:
        return jsonify(success=False, error="Missing id/status"), 400

    conn = get_db()
    conn.execute("UPDATE reviews SET status=? WHERE id=?", (new_status, review_id))
    conn.commit()
    conn.close()

    return jsonify(success=True)


if __name__ == "__main__":
    app.run(debug=True)
