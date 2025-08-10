from flask import Flask, request, jsonify
from flask_cors import CORS
import pymysql
import requests
import os

app = Flask(__name__)
CORS(app)

# -------------------
# CONFIGURATION
# -------------------
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_API_KEY")

# -------------------
# DB CONNECTION
# -------------------
def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

# -------------------
# SEARCH TRIPS
# -------------------
def search_trip_info(query):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM trips
        WHERE name LIKE %s OR inclusions LIKE %s
    """, (f"%{query}%", f"%{query}%"))
    trips = cursor.fetchall()
    conn.close()
    return trips

# -------------------
# SEARCH NEAREST PICKUP POINT
# -------------------
def find_nearest_pickup(user_location_name):
    # Get coordinates for user's location
    geocode_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={user_location_name}&key={GOOGLE_MAPS_API_KEY}"
    geocode_data = requests.get(geocode_url).json()

    if not geocode_data.get("results"):
        return None

    user_lat = geocode_data["results"][0]["geometry"]["location"]["lat"]
    user_lng = geocode_data["results"][0]["geometry"]["location"]["lng"]

    # Get pickup points from DB
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pickuppoints")
    pickup_points = cursor.fetchall()
    conn.close()

    # Calculate nearest using Google Distance Matrix API
    nearest_point = None
    min_distance = float("inf")

    for point in pickup_points:
        distance_url = (
            f"https://maps.googleapis.com/maps/api/distancematrix/json?"
            f"origins={user_lat},{user_lng}&destinations={point['latitude']},{point['longitude']}"
            f"&key={GOOGLE_MAPS_API_KEY}"
        )
        distance_data = requests.get(distance_url).json()

        if distance_data["rows"] and distance_data["rows"][0]["elements"][0]["status"] == "OK":
            distance_meters = distance_data["rows"][0]["elements"][0]["distance"]["value"]
            if distance_meters < min_distance:
                min_distance = distance_meters
                nearest_point = point

    return nearest_point

# -------------------
# CHATBOT ENDPOINT
# -------------------
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "").lower()

    # Trip search
    if "trip" in user_message or "tour" in user_message:
        trips = search_trip_info(user_message)
        if trips:
            return jsonify({"response": trips})
        else:
            return jsonify({"response": "No matching trips found."})

    # Pickup point search
    if "pickup nearby" in user_message:
        location_name = user_message.replace("pickup nearby", "").strip()
        nearest_point = find_nearest_pickup(location_name)
        if nearest_point:
            return jsonify({
                "response": f"Nearest pickup point to {location_name} is {nearest_point['name']} - {nearest_point['description']}"
            })
        else:
            return jsonify({"response": "No pickup point found near that location."})

    return jsonify({"response": "I can help with trips or finding nearest pickup points. Please ask accordingly."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
