import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import requests
import openai

# Initialize Flask
app = Flask(__name__)

# Enable CORS for your domains
CORS(app, origins=["https://ashtavinayak.net", "https://www.ashtavinayak.net"])

# Set OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# ---------------------- DATABASE CONNECTION ---------------------- #
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

# ---------------------- SEARCH TRIPS ---------------------- #
def search_trips(keyword):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    like_kw = f"%{keyword}%"
    query = """
        SELECT id, name, duration, cost, inclusions, start_day, contact
        FROM trips
        WHERE name LIKE %s OR duration LIKE %s OR inclusions LIKE %s OR cost LIKE %s
    """
    cursor.execute(query, (like_kw, like_kw, like_kw))
    results = cursor.fetchall()
    conn.close()
    return results

# ---------------------- SEARCH NEARBY TEMPLES ---------------------- #
def search_nearby_temples(lat, lng):
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    url = (
        f"https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        f"?location={lat},{lng}&radius=5000&type=hindu_temple&key={api_key}"
    )
    try:
        response = requests.get(url)
        data = response.json()
        temples = []
        if data.get("results"):
            for place in data["results"]:
                temples.append({
                    "name": place.get("name"),
                    "address": place.get("vicinity"),
                    "latitude": place["geometry"]["location"]["lat"],
                    "longitude": place["geometry"]["location"]["lng"]
                })
        return temples
    except Exception as e:
        return [{"error": str(e)}]

# ---------------------- GET OPENAI RESPONSE ---------------------- #
def get_openai_response(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful travel assistant for Ashtavinayak tours."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200
        )
        return response.choices[0].message["content"].strip()
    except Exception as e:
        return f"Error with OpenAI API: {str(e)}"

# ---------------------- CHAT ENDPOINT ---------------------- #
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "").strip()
    lat = data.get("lat")
    lng = data.get("lng")

    if not user_message:
        return jsonify({"reply": "Please enter a message."})

    # 1. Search trips
    trips = search_trips(user_message)
    if trips:
        trip_list = "\n".join([f"{t['name']} - {t['duration']} (₹{t['cost']} - {t['inclusions']} - {t['start_day']} - {t['contact']})" for t in trips])
        return jsonify({"reply": f"Here are some trips matching your search:\n{trip_list}"})

    # 2. Search temples nearby if lat/lng provided
    if lat and lng:
        temples = search_nearby_temples(lat, lng)
        if temples:
            temple_list = "\n".join([f"{t['name']} - {t['address']}" for t in temples])
            return jsonify({"reply": f"Nearby temples:\n{temple_list}"})

    # 3. Fallback to OpenAI
    openai_reply = get_openai_response(user_message)
    return jsonify({"reply": openai_reply})

# ---------------------- HEALTH CHECK ---------------------- #
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok", "message": "Travel chatbot is running."})

# Gunicorn entry point
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
