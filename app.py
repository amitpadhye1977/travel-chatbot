from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import openai
import mysql.connector
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Load OpenAI API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

# Database configuration (update with your MySQL credentials)
db_config = {
    'host': os.getenv("DB_HOST", "your-db-host"),
    'user': os.getenv("DB_USER", "your-db-user"),
    'password': os.getenv("DB_PASSWORD", "your-db-password"),
    'database': os.getenv("DB_NAME", "your-db-name")
}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    try:
        user_message = request.json.get("message", "")
        if not user_message:
            return jsonify({"reply": "Please ask a valid question."})

        # Connect to MySQL and fetch all trip details
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM trips")
        trips = cursor.fetchall()
        cursor.close()
        conn.close()

        # Format trip data for GPT prompt
        trip_info = ""
        for trip in trips:
            trip_info += (
                f"\nTrip Name: {trip['name']}\n"
                f"Duration: {trip['duration']}\n"
                f"Cost: {trip['cost']}\n"
                f"Inclusions: {trip['inclusions']}\n"
                f"Start Day: {trip['start_day']}\n"
                f"Contact: {trip['contact']}\n"
            )

        # Create prompt for GPT
        prompt = (
            f"Customer asked: {user_message}\n"
            f"Here are available trips:\n{trip_info}\n"
            f"Reply politely using the trip details."
        )

        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful trip assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )

        bot_reply = response['choices'][0]['message']['content']
        return jsonify({"reply": bot_reply})
        
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"reply": "Sorry, something went wrong. Please try again later."})


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
