from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import requests
import mysql.connector

app = Flask(__name__)
CORS(app, origins=["https://ashtavinayak.net", "https://amitpadhye1977.github.io"])



# Database configuration from environment variables
db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}

# RapidAPI configuration
rapidapi_key = os.getenv("RAPIDAPI_KEY")
rapidapi_host = os.getenv("RAPIDAPI_HOST")  # e.g., api-ninjas.p.rapidapi.com

# Function to fetch trip details from MySQL
def fetch_trip_details():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT name, duration, cost, inclusions, start_day, contact FROM trips")
        results = cursor.fetchall()
        conn.close()

        trips = []
        for row in results:
            trips.append({
                'name': row[0],
                'duration': row[1],
                'cost': row[2],
                'inclusions': row[3],
                'start_day': row[4],
                'contact': row[5]
            })
        return trips
    except mysql.connector.Error as e:
        return f"Database error: {e}"

# Function to get response from RapidAPI GPT endpoint
def get_gpt_reply(user_message):
    url = f"https://{rapidapi_host}/chat"
    payload = {"message": user_message}
    headers = {
        "content-type": "application/json",
        "X-RapidAPI-Key": rapidapi_key,
        "X-RapidAPI-Host": rapidapi_host
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        return result.get("reply", "No reply received.")
    except Exception as e:
        return f"Error: {str(e)}"

# Home route to serve index.html
@app.route("/")
def home():
    return render_template("index.html")

# Chat route to handle user messages
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_message = data.get("message")

        if "trip" in user_message.lower():
            trips = fetch_trip_details()
            if isinstance(trips, str):  # Error occurred
                return jsonify({"reply": trips})
            reply = "Here are some available trips:\n"
            for trip in trips:
                reply += f"\n{trip['name']} ({trip['duration']}) - {trip['cost']}\nInclusions: {trip['inclusions']}\nStarts: {trip['start_day']}\nContact: {trip['contact']}\n"
            return jsonify({"reply": reply})
        else:
            reply = get_gpt_reply(user_message)
            return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"reply": f"Sorry, something went wrong. Error: {str(e)}"})

# Main entry point
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
