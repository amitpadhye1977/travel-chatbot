from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import openai
import requests
import mysql.connector

app = Flask(__name__)
CORS(app, origins=["https://ashtavinayak.net"])

openai.api_key = os.environ.get("OPENAI_API_KEY")

# MySQL connection details
db_config = {
    'host': os.environ.get("DB_HOST"),
    'user': os.environ.get("DB_USER"),
    'password': os.environ.get("DB_PASSWORD"),
    'database': os.environ.get("DB_NAME"),
    'ssl_disabled': True  # Planetscale needs SSL – use connector settings if needed
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json['message']
    
    # Connect to MySQL
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    
    # Fetch trip info (for simplicity, first matching trip)
    cursor.execute("SELECT name, duration, cost, inclusions, start_day, contact FROM trips WHERE name LIKE '%Ashtavinayak%'")
    trip = cursor.fetchone()
    conn.close()

    if trip:
        trip_info = f"""
Trip: {trip[0]}
Duration: {trip[1]}
Cost: {trip[2]}
Includes: {trip[3]}
Start Day: {trip[4]}
Contact: {trip[5]}
"""
    else:
        trip_info = "No trip information found."

    prompt = f"""
You are a helpful travel assistant. Use the following trip info to answer user questions.

{trip_info}

User: {user_message}
Assistant:"""

    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=150,
        temperature=0.7
    )

    bot_reply = response.choices[0].text.strip()
    return jsonify({'reply': bot_reply})

if __name__ == '__main__':
    app.run(debug=True)
