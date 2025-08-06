from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import openai
import mysql.connector
import os

app = Flask(__name__)
CORS(app)

import os
import requests

rapidapi_key = os.getenv("RAPIDAPI_KEY")  # Get from environment

def get_gpt_reply(user_message):
    url = "https://your-api-host.p.rapidapi.com/chat"
    
    payload = {"message": user_message}
    headers = {
        "content-type": "application/json",
        "X-RapidAPI-Key": rapidapi_key,
        "X-RapidAPI-Host": "chatgpt-42.p.rapidapi.com"
    }

    response = requests.post(url, json=payload, headers=headers)
    result = response.json()
    return result.get("reply", "No reply received.")


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    try:
        user_message = request.json.get("message", "")
        if not user_message:
            return jsonify({"reply": "Please ask a valid question."})

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM trips")
        trips = cursor.fetchall()
        cursor.close()
        conn.close()

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

        prompt = (
            f"Customer asked: {user_message}\n"
            f"Here are available trips:\n{trip_info}\n"
            f"Reply politely using the trip details."
        )

        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful trip assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        bot_reply = response.choices[0].message.content


    except Exception as e:
        error_msg = str(e)
        print("Error:", error_msg)
        return jsonify({"reply": f"Error: {error_msg}"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
