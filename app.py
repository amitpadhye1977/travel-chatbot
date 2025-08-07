from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import pymysql
import os

app = Flask(__name__)
CORS(app)

# Load from Render environment variables
openai.api_key = os.getenv("OPENAI_API_KEY")

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_message = data.get("message", "").strip()

        if not user_message:
            return jsonify({"reply": "Message is empty"}), 400

        # Connect to MySQL
        conn = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
        cursor = conn.cursor()

        cursor.execute("SELECT place_name, description FROM trip_data")
        rows = cursor.fetchall()
        conn.close()

        trip_info = "\n".join([f"{name}: {desc}" for name, desc in rows])

        # Send to OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful travel assistant."},
                {"role": "user", "content": f"User asked: {user_message}\nUse this info:\n{trip_info}"}
            ]
        )

        reply = response.choices[0].message["content"].strip()
        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"reply": f"Error: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)
