from flask import Flask, render_template, request, redirect, session, jsonify
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
from groq import Groq
from urllib.parse import urlparse
import random

load_dotenv()

# just to check if env is loading (remove later)
print(os.getenv("GROQ_API_KEY"))

app = Flask(__name__)
app.secret_key = "careconnect_secret"

# groq client
client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

# ---------- DATABASE SETUP ----------
db_url = os.getenv("DATABASE_URL")

if not db_url:
    raise Exception("DATABASE_URL not found")

parsed = urlparse(db_url)

db = mysql.connector.connect(
    host=parsed.hostname,
    user=parsed.username,
    password=parsed.password,
    database=parsed.path.replace("/", ""),
    port=parsed.port
)

cursor = db.cursor()

# create table if not present
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nationality VARCHAR(50),
    initial VARCHAR(10),
    full_name VARCHAR(100),
    gender VARCHAR(20),
    date_of_birth DATE,
    mobile VARCHAR(20),
    email VARCHAR(100) UNIQUE,
    password VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
db.commit()


@app.route("/")
def home():
    return redirect("/register")


# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nationality = request.form.get("nationality")
        initial = request.form.get("initial")
        full_name = request.form.get("name")
        gender = request.form.get("gender")
        dob = request.form.get("dob")
        mobile = request.form.get("mobile")
        email = request.form.get("email")
        password = generate_password_hash(request.form.get("password"))

        cursor.execute("""
            INSERT INTO users
            (nationality, initial, full_name, gender, date_of_birth, mobile, email, password)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            nationality, initial, full_name,
            gender, dob, mobile, email, password
        ))

        db.commit()
        return redirect("/login")

    return render_template("register.html")


# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        cursor.execute(
            "SELECT id, full_name, password FROM users WHERE email=%s",
            (email,)
        )
        user = cursor.fetchone()

        if user and check_password_hash(user[2], password):
            session["user_id"] = user[0]
            session["user_name"] = user[1]
            return redirect("/dashboard")

        return "Invalid email or password"

    return render_template("login.html")


# ---------- DASHBOARD ----------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    cursor.execute("""
        SELECT nationality, initial, full_name, gender,
               date_of_birth, mobile, email
        FROM users WHERE id=%s
    """, (session["user_id"],))

    user = cursor.fetchone()

    user_data = {
        "nationality": user[0],
        "initial": user[1],
        "full_name": user[2],
        "gender": user[3],
        "date_of_birth": user[4],
        "mobile": user[5],
        "email": user[6]
    }

    return render_template("dashboard.html", user=user_data)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ---------- WELLNESS ----------
@app.route("/wellness")
def wellness():
    if "user_id" not in session:
        return redirect("/login")

    tips = [
        "Drink enough water today.",
        "Take a short walk to clear your head.",
        "Try slow breathing for a few minutes.",
        "Avoid phone usage before sleep.",
        "Eat something healthy today.",
        "Sit straight while working.",
        "Take breaks between tasks.",
        "Sleep for at least 7 hours.",
        "Spend some time in sunlight.",
        "Talk to someone you trust."
    ]

    return render_template("wellness.html", tip=random.choice(tips))


@app.route("/yoga")
def yoga():
    if "user_id" not in session:
        return redirect("/login")

    return render_template("yoga.html")


# ---------- CHATBOT ----------
def get_chatbot_reply(message):
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "You are a friendly wellness assistant. "
                               "Be supportive and calm. "
                               "Do not give medical advice."
                },
                {"role": "user", "content": message}
            ],
            temperature=0.6,
            max_tokens=200
        )

        return response.choices[0].message.content

    except Exception as e:
        print(e)
        return "Something went wrong. Please try again."


@app.route("/chat", methods=["POST"])
def chat():
    if "user_id" not in session:
        return jsonify({"reply": "Please login first."})

    data = request.get_json()
    msg = data.get("message", "")

    if not msg.strip():
        return jsonify({"reply": "Say something first."})

    return jsonify({"reply": get_chatbot_reply(msg)})


@app.route("/chatbot")
def chatbot():
    if "user_id" not in session:
        return redirect("/login")

    return render_template("chatbot.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
