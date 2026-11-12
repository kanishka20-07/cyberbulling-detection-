from flask import Flask
import sqlite3

app = Flask(__name__)

@app.route("/")
def dashboard():
    db = sqlite3.connect("cyberbullying.db")
    db.row_factory = sqlite3.Row

    users = db.execute(
        "SELECT username, violation_count, status FROM users"
    ).fetchall()

    history = db.execute(
        "SELECT commenter, target, comment, prediction, confidence, "
        "violation_number, action, created_at FROM violations ORDER BY id DESC"
    ).fetchall()

    db.close()

    html = "<h1>Cyberbullying Admin Dashboard</h1>"

    html += "<h2>User Status</h2><table border=1>"
    html += "<tr><th>User</th><th>Count</th><th>Status</th></tr>"

    for u in users:
        html += f"<tr><td>{u['username']}</td><td>{u['violation_count']}</td><td>{u['status']}</td></tr>"

    html += "</table><h2>Violation History</h2><table border=1>"
    html += "<tr><th>Commenter</th><th>Target</th><th>Comment</th><th>Prediction</th><th>Confidence</th><th>No.</th><th>Action</th><th>Time</th></tr>"

    for v in history:
        html += f"<tr><td>{v['commenter']}</td><td>{v['target']}</td><td>{v['comment']}</td><td>{v['prediction']}</td><td>{v['confidence']}</td><td>{v['violation_number']}</td><td>{v['action']}</td><td>{v['created_at']}</td></tr>"

    return html + "</table>"

app.run(port=5001)