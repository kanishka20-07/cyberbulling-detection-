import sqlite3

db = sqlite3.connect("cyberbullying.db")

cursor = db.cursor()

cursor.execute(
    "UPDATE users SET violation_count = 5, status = 'active', blocked_until = NULL, permanent_block = 0 WHERE username = ?",
    ("dhiva@111",)
)

db.commit()

db.close()

print("dhiva@111 violation count set to 5")
print("Now give one bullying comment to test permanent block.")