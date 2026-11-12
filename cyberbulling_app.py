from flask import Flask, request, jsonify, render_template_string,session,redirect
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)

app.secret_key = "cyber123" 

texts = [
    "I hate you",
    "You are stupid",
    "You are ugly",
    "Nobody likes you",
    "Go away idiot",
    "You are worthless",
    "Shut up loser",
    "Everyone hates you",
    "You are a fool",
    "I will make your life miserable",
    "You are amazing",
    "Good job",
    "Have a nice day",
    "Thank you for helping me",
    "You did a great job",
    "Congratulations",
    "I really like your post",
    "That was wonderful",
    "Keep going",
    "You are very talented"
]

labels = [
    "bullying","bullying","bullying","bullying","bullying",
    "bullying","bullying","bullying","bullying","bullying",
    "normal","normal","normal","normal","normal",
    "normal","normal","normal","normal","normal"
]

vectorizer = TfidfVectorizer(
    lowercase=True,
    stop_words="english",
    ngram_range=(1, 2)
)

X = vectorizer.fit_transform(texts)

model = LogisticRegression(max_iter=1000)
model.fit(X, labels)

DATABASE = "cyberbullying.db"


def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def create_database():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            violation_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            blocked_until TEXT,
            permanent_block INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS violations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commenter TEXT,
            target TEXT,
            comment TEXT,
            prediction TEXT,
            confidence REAL,
            violation_number INTEGER,
            action TEXT,
            created_at TEXT
        )
    """)

    db.commit()
    db.close()


create_database()


def get_user(username):
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    )

    user = cursor.fetchone()
    db.close()

    return user


def create_user(username):
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "INSERT OR IGNORE INTO users (username) VALUES (?)",
        (username,)
    )

    db.commit()
    db.close()


def check_block_status(username):
    user = get_user(username)

    if user is None:
        return False, None

    if user["permanent_block"] == 1:
        return True, "permanent"

    if user["blocked_until"]:
        blocked_until = datetime.fromisoformat(
            user["blocked_until"]
        )

        if datetime.now() < blocked_until:
            return True, blocked_until

        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            UPDATE users
            SET status = 'active',
                blocked_until = NULL
            WHERE username = ?
        """, (username,))

        db.commit()
        db.close()

    return False, None


def record_violation(commenter, target, comment, confidence):

    create_user(commenter)

    user = get_user(commenter)

    violation_number = user["violation_count"] + 1

    action = ""
    blocked_until = None
    permanent = 0

    if violation_number == 1:
        action = "WARNING 1"

    elif violation_number == 2:
        action = "WARNING 2"

    elif violation_number == 3:
        action = "TEMPORARY BLOCK - 24 HOURS"
        blocked_until = datetime.now() + timedelta(hours=24)

    elif violation_number == 4:
        action = "TEMPORARY BLOCK - 3 DAYS"
        blocked_until = datetime.now() + timedelta(days=3)

    elif violation_number == 5:
        action = "TEMPORARY BLOCK - 7 DAYS"
        blocked_until = datetime.now() + timedelta(days=7)

    else:
        action = "PERMANENT BLOCK"
        permanent = 1

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        UPDATE users
        SET violation_count = ?,
            status = ?,
            blocked_until = ?,
            permanent_block = ?
        WHERE username = ?
    """, (
        violation_number,
        "blocked" if blocked_until or permanent else "active",
        blocked_until.isoformat() if blocked_until else None,
        permanent,
        commenter
    ))

    cursor.execute("""
        INSERT INTO violations
        (
            commenter,
            target,
            comment,
            prediction,
            confidence,
            violation_number,
            action,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        commenter,
        target,
        comment,
        "bullying",
        confidence,
        violation_number,
        action,
        datetime.now().isoformat()
    ))

    db.commit()
    db.close()

    return violation_number, action, blocked_until


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session["login"] = True
        return redirect("/")
    return render_template_string("""
<style>
body {
    background: linear-gradient(135deg, #080d25, #171044, #003b62);
    color: white;
    font-family: Arial;
    height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
}
.box {
    background: #111b36;
    padding: 35px;
    width: 300px;
    text-align: center;
    border-radius: 18px;
    border: 1px solid #168cff;
    box-shadow: 0 0 25px #168cff;
}
input, button {
    width: 100%;
    padding: 12px;
    margin: 10px 0;
    box-sizing: border-box;
    border-radius: 8px;
    border: none;
}
button {
    background: #168cff;
    color: white;
    font-weight: bold;
}
h2 { color: #55c8ff; }
</style>

<div class="box">
    <h2>🛡 CYBER SHIELD</h2>
    <h3>Cyberbullying Detection System</h3>
    <p>AI Powered Online Safety</p>
    <form method="post">
        <input name="username" placeholder="Username" required>
        <input name="password" type="password"
               placeholder="Password" required>
        <button type="submit">SECURE LOGIN</button>
    </form>
    <p>Protecting Users • Detecting Cyberbullying</p>
</div>
""")
    
@app.route("/")
def home():
    if not session.get("login"):
        return redirect("/login")
    return render_template_string(HTML_PAGE)


@app.route("/predict", methods=["POST"])
def predict():

    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data received"}), 400

        commenter = data.get("commenter", "").strip()
        target = data.get("target", "").strip()
        text = data.get("text", "").strip()

        if not commenter:
            return jsonify({
                "error": "Please enter commenter username"
            }), 400

        if not target:
            return jsonify({
                "error": "Please enter target username"
            }), 400

        if not text:
            return jsonify({
                "error": "Please enter a comment"
            }), 400

        is_blocked, block_info = check_block_status(commenter)

        if is_blocked:

            if block_info == "permanent":
                return jsonify({
                    "prediction": "blocked",
                    "commenter": commenter,
                    "target": target,
                    "message":
                    f"🚫 @{commenter} is permanently blocked."
                })

            return jsonify({
                "prediction": "blocked",
                "commenter": commenter,
                "target": target,
                "message":
                f"🚫 @{commenter} is temporarily blocked.",
                "blocked_until":
                block_info.strftime("%Y-%m-%d %H:%M:%S")
            })

        text_vector = vectorizer.transform([text])

        prediction = model.predict(text_vector)[0]

        probabilities = model.predict_proba(text_vector)[0]

        confidence = max(probabilities) * 100

        if prediction == "normal":

            user = get_user(commenter)

            violation_count = (
                user["violation_count"] if user else 0
            )

            return jsonify({
                "prediction": "normal",
                "commenter": commenter,
                "target": target,
                "confidence": round(confidence, 2),
                "warning_count": violation_count,
                "message": "✅ No Cyberbullying Detected"
            })

        violation_number, action, blocked_until = record_violation(
            commenter,
            target,
            text,
            round(confidence, 2)
        )

        if violation_number == 1:
            message = "⚠️ Cyberbullying Detected!"
            warning_message = (
                "⚠️ Warning 1: "
                "Please do not post abusive comments."
            )

        elif violation_number == 2:
            message = "⚠️ Cyberbullying Detected!"
            warning_message = (
                "⚠️ Warning 2: "
                "This is your final warning."
            )

        elif violation_number == 3:
            message = "🚫 Cyberbullying Detected!"
            warning_message = (
                "🚫 Account temporarily blocked for 24 hours."
            )

        elif violation_number == 4:
            message = "🚫 Repeated Cyberbullying!"
            warning_message = (
                "🚫 Account blocked for 3 days."
            )

        elif violation_number == 5:
            message = "🚫 Repeated Cyberbullying!"
            warning_message = (
                "🚫 Account blocked for 7 days."
            )

        else:
            message = "🔒 Severe Repeated Violation!"
            warning_message = (
                "🔒 Account permanently blocked."
            )

        return jsonify({
            "prediction": "bullying",
            "commenter": commenter,
            "target": target,
            "confidence": round(confidence, 2),
            "warning_count": violation_number,
            "message": message,
            "warning_message": warning_message,
            "action": action,
            "blocked_until":
                blocked_until.strftime("%Y-%m-%d %H:%M:%S")
                if blocked_until else None
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/admin/users")
def admin_users():

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT *
        FROM users
        ORDER BY violation_count DESC
    """)

    users = cursor.fetchall()
    db.close()

    return jsonify([dict(user) for user in users])


@app.route("/admin/violations")
def admin_violations():

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT *
        FROM violations
        ORDER BY id DESC
    """)

    violations = cursor.fetchall()
    db.close()

    return jsonify([dict(v) for v in violations])


HTML_PAGE = """

<!DOCTYPE html>

<html>

<head>

<title>Cyberbullying Detector</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: linear-gradient(135deg, #667eea, #764ba2);
    min-height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
}

.container {
    background: white;
    width: 600px;
    max-width: 95%;
    padding: 30px;
    border-radius: 20px;
    box-shadow: 0 15px 40px rgba(0,0,0,0.25);
}

h1 {
    text-align: center;
    color: #333;
}

.subtitle {
    text-align: center;
    color: #777;
    margin-bottom: 25px;
}

label {
    display: block;
    margin-top: 15px;
    margin-bottom: 6px;
    font-weight: bold;
    color: #444;
}

input,
textarea {
    width: 100%;
    padding: 12px;
    border: 1px solid #ccc;
    border-radius: 8px;
    font-size: 15px;
}

textarea {
    height: 120px;
    resize: none;
}

button {
    width: 100%;
    margin-top: 20px;
    padding: 13px;
    border: none;
    border-radius: 8px;
    background: #667eea;
    color: white;
    font-size: 17px;
    font-weight: bold;
    cursor: pointer;
}

.result {
    margin-top: 25px;
    padding: 20px;
    border-radius: 10px;
    display: none;
}

.bullying {
    background: #ffe5e5;
    border-left: 6px solid red;
}

.normal {
    background: #e5ffe9;
    border-left: 6px solid green;
}

.blocked {
    background: #ffe5cc;
    border-left: 6px solid orange;
}

.info {
    margin-top: 25px;
    padding: 15px;
    background: #f5f5f5;
    border-radius: 10px;
}

</style>

</head>

<body>

<div class="container">

<h1>🛡️ Cyberbullying Detector</h1>

<p class="subtitle">
AI-Based Social Media Comment Moderation
</p>

<label>Commenter Username</label>

<input
    id="commenter"
    placeholder="@Arun"
>

<label>Target Username</label>

<input
    id="target"
    placeholder="@Priya"
>

<label>Comment</label>

<textarea
    id="comment"
    placeholder="Enter social media comment..."
></textarea>

<button onclick="detectBullying()">
🔍 Detect Cyberbullying
</button>

<div id="result" class="result"></div>

<div class="info">

<h3>How It Works</h3>

<p>1️⃣ AI analyzes the comment.</p>

<p>2️⃣ Normal comment → ✅ Allowed</p>

<p>3️⃣ First violation → ⚠️ Warning 1</p>

<p>4️⃣ Second violation → ⚠️ Warning 2</p>

<p>5️⃣ Third violation → 🚫 24-hour block</p>

<p>6️⃣ Repeated violations → longer block</p>

<p>7️⃣ Severe violations → 🔒 Permanent block</p>

<p>8️⃣ History is stored in SQLite.</p>

</div>

</div>

<script>

async function detectBullying() {

    const commenter =
        document.getElementById("commenter")
        .value.trim();

    const target =
        document.getElementById("target")
        .value.trim();

    const comment =
        document.getElementById("comment")
        .value.trim();

    const result =
        document.getElementById("result");

    if (!commenter || !target || !comment) {

        alert("Please fill all fields.");

        return;
    }

    result.style.display = "block";

    result.className = "result";

    result.innerHTML =
        "<h2>⏳ Checking...</h2>";

    try {

        const response = await fetch(
            "/predict",
            {
                method: "POST",

                headers: {
                    "Content-Type":
                    "application/json"
                },

                body: JSON.stringify({
                    commenter: commenter,
                    target: target,
                    text: comment
                })
            }
        );

        const data = await response.json();

        if (data.error) {

            result.className =
                "result blocked";

            result.innerHTML =
                "<h2>❌ Error</h2>" +
                "<p>" +
                data.error +
                "</p>";

            return;
        }

        if (data.prediction === "bullying") {

            result.className =
                "result bullying";

            result.innerHTML =
                "<h2>" +
                data.message +
                "</h2>" +

                "<p><b>Commenter:</b> @" +
                data.commenter +
                "</p>" +

                "<p><b>Target:</b> @" +
                data.target +
                "</p>" +

                "<p><b>Confidence:</b> " +
                data.confidence +
                "%</p>" +

                "<p><b>Violation Count:</b> " +
                data.warning_count +
                "</p>" +

                "<p><b>Action:</b> " +
                data.action +
                "</p>" +

                "<p><b>" +
                data.warning_message +
                "</b></p>";
        }

        else if (data.prediction === "normal") {

            result.className =
                "result normal";

            result.innerHTML =
                "<h2>" +
                data.message +
                "</h2>" +

                "<p><b>Commenter:</b> @" +
                data.commenter +
                "</p>" +

                "<p><b>Target:</b> @" +
                data.target +
                "</p>" +

                "<p><b>Confidence:</b> " +
                data.confidence +
                "%</p>" +

                "<p><b>Previous Violations:</b> " +
                data.warning_count +
                "</p>";
        }

        else if (data.prediction === "blocked") {

            result.className =
                "result blocked";

            result.innerHTML =
                "<h2>" +
                data.message +
                "</h2>" +

                "<p><b>Commenter:</b> @" +
                data.commenter +
                "</p>" +

                "<p><b>Target:</b> @" +
                data.target +
                "</p>" +

                (
                    data.blocked_until
                    ?
                    "<p><b>Blocked Until:</b> " +
                    data.blocked_until +
                    "</p>"
                    :
                    ""
                );
        }

    }

    catch(error) {

        result.className =
            "result blocked";

        result.innerHTML =
            "<h2>❌ Connection Error</h2>" +
            "<p>" +
            error.message +
            "</p>";
    }
}

</script>

</body>

</html>

"""


if __name__ == "__main__":

    print("CYBERBULLYING DETECTOR STARTED")
    print("Open: http://127.0.0.1:5000")

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )
    
