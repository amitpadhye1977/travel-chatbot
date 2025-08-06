from flask import Flask, render_template, request, jsonify
import openai
import mysql.connector
import os

app = Flask(__name__)
openai.api_key = os.environ.get("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")

# MySQL connection from environment variables (Render supports this)
db_config = {
    'host': os.environ.get("ashtavinayak.net"),
    'user': os.environ.get("ashtavin_user"),
    'password': os.environ.get("cyberamit"),
    'database': os.environ.get("ashtavin_bus"),
    'ssl_disabled': True  # Planetscale needs SSL – use connector settings if needed
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json['message']
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT name, duration, cost, inclusions, start_day, contact FROM trips WHERE name LIKE '%Ashtavinayak%'")
        trip = cursor.fetchone()
        conn.close()
    except Exception as e:
        trip = None

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
You are a helpful travel assistant. Use this trip info to answer user questions.

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
