import os
import math
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import mysql.connector
from openai import OpenAI

app = Flask(__name__)
CORS(app)

# OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Database connection
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASS", ""),
        database=os.getenv("DB_NAME", "ashtavinayak")
    )

# Home route
@app.route("/")
def index():
    return render_template("index.html")

# Fetch all trips
@app.route("/trips", methods=["GET"])
def get_trips():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, details, cost, duration, date FROM trips")
        trips = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(trips)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Chat endpoint
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "")
    language = data.get("language", "en")  # <-- NEW: default English

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check if user asked for trip info
        cursor.execute("SELECT name, details, cost, duration, date FROM trips")
        trips = cursor.fetchall()

        cursor.execute("SELECT name, address, latitude, longitude FROM pickuppoints")
        pickuppoints = cursor.fetchall()

        cursor.close()
        conn.close()

        # Send message with DB data to OpenAI
        prompt = f"""
        The user asked: {user_message}
        Answer in {language} language.

        Here are the trips available:
        {trips}

        Here are the pickup points:
        {pickuppoints}

        If user asks for nearest pickup point, calculate by location.
        Otherwise, answer smartly based on trips data.
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful travel assistant."},
                {"role": "user", "content": prompt}
            ]
        )

        reply = response.choices[0].message.content
        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Utility function: Calculate distance (if needed for pickup point queries)
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2) ** 2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(dlon/2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
