import sqlite3

conn = sqlite3.connect("databasez.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    product_id TEXT,
    product_name TEXT,
    rating INTEGER,
    comment TEXT,
    date TEXT,
    status TEXT
)
""")

cur.executemany("""
INSERT INTO reviews
(username, product_id, product_name, rating, comment, date, status)
VALUES (?, ?, ?, ?, ?, ?, ?)
""", [
    ("sarahtan", "P001", "Green Lettuce", 5, "Very fresh!", "2026-01-20", "Pending"),
    ("johnlim", "P002", "Red Bak Choy", 4, "Nice crunch.", "2026-01-19", "Approved"),
    ("marychen", "P003", "Cherry Tomatoes", 5, "Sweet and juicy.", "2026-01-18", "Approved")
])

conn.commit()
conn.close()
print("DB ready ")
