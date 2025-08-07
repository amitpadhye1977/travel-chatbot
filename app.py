from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import mysql.connector
import openai

app = Flask(__name__)
CORS(app, origins=["https://ashtavinayak.net"])

# Load secrets from environment
openai.api_key = os.getenv("OPENAI_API_KEY")

# Database config
db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}

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

# Function to get GPT reply using OpenAI
def get_gpt_reply(prompt_message):
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt_message}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {str(e)}"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_message = data.get("message")

        trips = fetch_trip_details()
        if isinstance(trips, str):  # error message
            return jsonify({"reply": trips})

        # Prepare trip summary
        trip_info = ""
        for trip in trips:
            trip_info += (
                f"{trip['name']} - {trip['duration']} - {trip['cost']}. "
                f"Starts: {trip['start_day']}. Includes: {trip['inclusions']}. "
                f"Contact: {trip['contact']}\n"
            )

        prompt = (
            f"User asked: {user_message}\n\n"
            f"Available trips:\n{trip_info}\n\n"
            f"Suggest the most relevant trip(s) based on the user's question. "
            f"Reply clearly and concisely."
        )

        reply = get_gpt_reply(prompt)
        return jsonify({"reply": reply})

    except Exception as e:
        print(f"Chat Error: {str(e)}")
        return jsonify({"reply": f"Sorry, something went wrong. Error: {str(e)}"})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
