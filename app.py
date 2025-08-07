from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import requests
import mysql.connector

app = Flask(__name__)
CORS(app, origins=["https://ashtavinayak.net"])

db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}

rapidapi_key = os.getenv("RAPIDAPI_KEY")
rapidapi_host = os.getenv("RAPIDAPI_HOST")  # e.g. custom-chatbot-api.p.rapidapi.com
bot_id = os.getenv("BOT_ID")  # Your specific bot ID created via PR Labs dashboard

def fetch_trip_details():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT name, duration, cost, inclusions, start_day, contact FROM trips")
        rows = cursor.fetchall()
        conn.close()
        return [
            {'name': r[0], 'duration': r[1], 'cost': r[2],
             'inclusions': r[3], 'start_day': r[4], 'contact': r[5]}
            for r in rows
        ]
    except Exception as e:
        return f"DB error: {e}"

def get_gpt_reply(prompt_message):
    url = f"https://{rapidapi_host}/chat"
    payload = {
        "bot_id": bot_id,
        "message": prompt_message
    }
    headers = {
        "content-type": "application/json",
        "X-RapidAPI-Key": rapidapi_key,
        "X-RapidAPI-Host": rapidapi_host
    }
    try:
        resp = requests.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        print("GPT API Response:", data)
        return data.get("reply") or data.get("response") or "No reply field."
    except Exception as e:
        print("GPT Error:", e)
        return f"Error: {str(e)}"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    try:
        user_message = request.get_json().get("message", "")
        trips = fetch_trip_details()
        if isinstance(trips, str):
            return jsonify({"reply": trips})

        trip_info = "\n".join(
            f"{t['name']} - {t['duration']} - {t['cost']}. Starts: {t['start_day']}. Includes: {t['inclusions']}. Contact: {t['contact']}"
            for t in trips
        )

        prompt = (
            f"User asked: {user_message}\n\n"
            f"Here are available trips:\n{trip_info}\n\n"
            "Please respond with only the most relevant trips in a friendly way."
        )
        reply = get_gpt_reply(prompt)
        return jsonify({"reply": reply})
    except Exception as e:
        print("Chat Error:", e)
        return jsonify({"reply": f"Sorry, something went wrong. Error: {str(e)}"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
