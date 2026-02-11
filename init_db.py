import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB = BASE_DIR / "databasez.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    product_id TEXT NOT NULL,
    product_name TEXT NOT NULL,
    rating INTEGER NOT NULL,
    comment TEXT NOT NULL,
    date TEXT NOT NULL,
    status TEXT NOT NULL
)
""")

# Reset demo data (comment out these 2 lines if you want to keep existing reviews)
cur.execute("DELETE FROM reviews")
cur.execute("DELETE FROM sqlite_sequence WHERE name='reviews'")

cur.executemany("""
INSERT INTO reviews (username, product_id, product_name, rating, comment, date, status)
VALUES (?, ?, ?, ?, ?, ?, ?)
""", [
    ("sarahtan", "1", "Blueberry Granola", 5, "Crunchy and yummy. Would buy again.", "2026-02-11", "Approved"),
    ("johnlim", "2", "Strawberry Jam", 4, "Sweet but still nice on toast.", "2026-02-11", "Pending"),
    ("marychen", "3", "Broccoli", 5, "Fresh and crisp, not soggy at all.", "2026-02-11", "Approved"),
])

conn.commit()
conn.close()

print("✅ database.db created/updated at:", DB)
