import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import requests
import openai

# ---------------------- FLASK SETUP ---------------------- #
app = Flask(__name__)

# Enable CORS for both domains and allow preflight OPTIONS requests
CORS(app, resources={r"/*": {"origins": [
    "https://ashtavinayak.net",
    "https://www.ashtavinayak.net"
]}}, supports_credentials=True)

# Set your OpenAI API key from environment variable
openai.api_key = os.environ.get("OPENAI_API_KEY")

# MySQL database configuration (read from environment variables)
db_config = {
    'host': os.environ.get("DB_HOST"),
    'user': os.environ.get("DB_USER"),
    'password': os.environ.get("DB_PASSWORD"),
    'database': os.environ.get("DB_NAME"),
    'ssl_disabled': True  # Disable SSL if not using Planetscale or similar
}

@app.route('/')
def index():
    return render_template('index.html')  # Load chatbot UI

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json['message']

    # Default empty trip info
    trip_info = "No trip information found."

    try:
        # Connect to MySQL and fetch trip details
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, duration, cost, inclusions, start_day, contact 
            FROM trips 
            WHERE name LIKE %s 
            LIMIT 1
        """, ("%Ashtavinayak%",))  # Example: filter for Ashtavinayak trip
        trip = cursor.fetchone()
        conn.close()

        if trip:
            trip_info = f"""
Trip Name: {trip[0]}
Duration: {trip[1]}
Cost: {trip[2]}
Includes: {trip[3]}
Start Day: {trip[4]}
Contact: {trip[5]}
"""

    except Exception as e:
        trip_info = f"Error fetching trip info: {str(e)}"

    # Build prompt for GPT
    prompt = f"""
You are a helpful travel assistant. Use the following trip details to answer questions.

Trip Details:
{trip_info}

User: {user_message}
Assistant:
"""

    # Generate reply using OpenAI GPT-3.5 or GPT-4
    response = openai.Completion.create(
        engine="text-davinci-003",  # Use GPT-3.5
        prompt=prompt,
        max_tokens=150,
        temperature=0.7
    )

    bot_reply = response.choices[0].text.strip()
    return jsonify({'reply': bot_reply})

if __name__ == '__main__':
    app.run(debug=True)
