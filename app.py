from flask import Flask, render_template, request, jsonify
import sqlite3

app = Flask(__name__)
DB = "database.db"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def admin_reviews():
    conn = get_db()
    rows = conn.execute("SELECT * FROM reviews").fetchall()
    conn.close()

    reviews = [dict(row) for row in rows]  
    return render_template("admin_reviews.html", reviews=reviews)

@app.route("/update-status", methods=["POST"])
def update_status():
    data = request.get_json()
    conn = get_db()
    conn.execute(
        "UPDATE reviews SET status=? WHERE id=?",
        (data["status"], data["id"])
    )
    conn.commit()
    conn.close()
    return jsonify(success=True)

if __name__ == "__main__":
    app.run(debug=True)
