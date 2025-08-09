from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import openai
import googlemaps
import math

app = Flask(__name__)
CORS(app)

# OpenAI API Key
openai.api_key = "YOUR_OPENAI_API_KEY"

# Google Maps API Key
gmaps = googlemaps.Client(key="YOUR_GOOGLE_MAPS_API_KEY")

# MySQL Connection
db = mysql.connector.connect(
    host="YOUR_MYSQL_HOST",
    user="YOUR_MYSQL_USER",
    password="YOUR_MYSQL_PASSWORD",
    database="YOUR_MYSQL_DATABASE"
)
cursor = db.cursor(dictionary=True)

# Function to calculate distance (Haversine formula)
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "")

    # First, check MySQL for matching trip info
    cursor.execute("SELECT * FROM trips WHERE trip_name LIKE %s", (f"%{user_message}%",))
    trip_result = cursor.fetchall()

    if trip_result:
        return jsonify({"reply": f"Found trip info: {trip_result}"})

    # If no match, fallback to OpenAI chatbot
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": user_message}]
    )
    bot_reply = response.choices[0].message.content.strip()
    return jsonify({"reply": bot_reply})

@app.route("/nearest-temple", methods=["POST"])
def nearest_temple():
    data = request.json
    location_name = data.get("location", "")

    # Get coordinates for current location
    geocode_result = gmaps.geocode(location_name)
    if not geocode_result:
        return jsonify({"reply": "Could not find your location."})

    lat1 = geocode_result[0]["geometry"]["location"]["lat"]
    lon1 = geocode_result[0]["geometry"]["location"]["lng"]

    # Fetch temples from MySQL
    cursor.execute("SELECT name, latitude, longitude FROM pickuppoints")
    temples = cursor.fetchall()

    # Find nearest temple
    nearest = None
    min_distance = float("inf")
    for temple in temples:
        distance = calculate_distance(lat1, lon1, temple["latitude"], temple["longitude"])
        if distance < min_distance:
            min_distance = distance
            nearest = temple

    if nearest:
        return jsonify({"reply": f"The nearest temple is {nearest['name']} ({min_distance:.2f} km away)."})
    else:
        return jsonify({"reply": "No temples found in the database."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
