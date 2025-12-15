from flask import Flask, render_template, request, redirect, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
from groq import Groq
from flask import jsonify

load_dotenv()

print("Groq key loaded:", os.getenv("GROQ_API_KEY"))  # TEMP DEBUG

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)
app = Flask(__name__)
app.secret_key = "careconnect_secret"

# MySQL connection
db = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    port=int(os.getenv("DB_PORT", 3306))
)

cursor = db.cursor()

@app.route("/")
def home():
    return redirect("/register")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nationality = request.form["nationality"]
        initial = request.form["initial"]
        full_name = request.form["name"]
        gender = request.form["gender"]
        dob = request.form["dob"]
        mobile = request.form["mobile"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        cursor.execute("""
            INSERT INTO users
            (nationality, initial, full_name, gender, date_of_birth, mobile, email, password)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            nationality,
            initial,
            full_name,
            gender,
            dob,
            mobile,
            email,
            password
        ))

        db.commit()
        return redirect("/login")

    return render_template("register.html")

from werkzeug.security import check_password_hash

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        cursor.execute(
            "SELECT id, full_name, password FROM users WHERE email=%s",
            (email,)
        )
        user = cursor.fetchone()

        if user and check_password_hash(user[2], password):
            session["user_id"] = user[0]
            session["user_name"] = user[1]
            return redirect("/dashboard")

        else:
            return "Invalid email or password"

    return render_template("login.html")

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

@app.route("/wellness")
def wellness():
    if "user_id" not in session:
        return redirect("/login")

    tips = [
        "Drink at least 8 glasses of water today to stay hydrated.",
        "Take a 10-minute walk to refresh your mind and body.",
        "Practice deep breathing for 5 minutes to reduce stress.",
        "Limit screen time before bed for better sleep quality.",
        "Eat at least one fruit or vegetable today.",
        "Maintain good posture while sitting or working.",
        "Take short breaks during work to avoid fatigue.",
        "Get at least 7–8 hours of sleep for optimal health.",
        "Spend a few minutes in sunlight for vitamin D.",
        "Talk to someone you trust if you feel overwhelmed."
    ]

    import random
    daily_tip = random.choice(tips)

    return render_template("wellness.html", tip=daily_tip)

@app.route("/yoga")
def yoga():
    if not session.get("user_id"):
        return redirect("/login")

    return render_template("yoga.html")

def get_chatbot_reply(user_message):
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a calm, supportive wellness assistant. "
                        "You help users with stress, anxiety, loneliness, and motivation. "
                        "You must NOT give medical diagnosis or prescribe treatments. "
                        "Keep answers short, kind, and supportive."
                    )
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            temperature=0.6,
            max_tokens=200
        )

        return response.choices[0].message.content

    except Exception as e:
        print("❌ CHATBOT ERROR:", e)
        return "I'm here with you. Please try again in a moment."
    
@app.route("/chat", methods=["POST"])
def chat():
    if "user_id" not in session:
        return jsonify({"reply": "Please login first."})

    data = request.get_json()
    user_message = data.get("message", "")

    if not user_message.strip():
        return jsonify({"reply": "Please tell me what's on your mind."})

    reply = get_chatbot_reply(user_message)

    return jsonify({"reply": reply})

@app.route("/chatbot")
def chatbot():
    if "user_id" not in session:
        return redirect("/login")

    return render_template("chatbot.html")



if __name__ == "__main__":
    app.run(debug=True)
