import os
import math
import mysql.connector
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

# Flask app
app = Flask(__name__)

# Allow CORS only from your domain
CORS(app, resources={r"/chat": {"origins": "https://www.ashtavinayak.net"}})

# Load environment variables
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_API_KEY")

# Connect to MySQL
def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

# Search trips table
def search_trip_info(message):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM trips WHERE name LIKE %s", (f"%{message}%",))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results

# Haversine formula to calculate distance between two coordinates
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# Search nearest pickup point
def find_nearest_pickup(location_name):
    # Get location coordinates from Google Maps API
    geo_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={location_name}&key={GOOGLE_MAPS_API_KEY}"
    geo_data = requests.get(geo_url).json()

    if not geo_data["results"]:
        return None

    user_lat = geo_data["results"][0]["geometry"]["location"]["lat"]
    user_lng = geo_data["results"][0]["geometry"]["location"]["lng"]

    # Fetch pickup points from DB
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM pickuppoints")
    pickup_points = cursor.fetchall()
    cursor.close()
    conn.close()

    # Find nearest point
    nearest_point = None
    min_distance = float("inf")
    for point in pickup_points:
        dist = calculate_distance(user_lat, user_lng, point["latitude"], point["longitude"])
        if dist < min_distance:
            min_distance = dist
            nearest_point = point

    return nearest_point

# Chat endpoint
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "").lower()

    # Search Trips
    trips = search_trip_info(user_message)
    if trips:
        response = "Here are the trips matching your query:\n"
        for trip in trips:
            response += f"- {trip['name']} ({trip['duration']}) - ₹{trip['cost']}\n  Inclusions: {trip['inclusions']}\n  Start Day: {trip['start_day']}\n  Contact: {trip['contact']}\n\n"
        return jsonify({"response": response.strip()})

    # Search Pickup points
    if "pickup" in user_message and "near" in user_message:
        location_name = user_message.split("near")[-1].strip()
        nearest_point = find_nearest_pickup(location_name)
        if nearest_point:
            return jsonify({"response": f"Nearest pickup point to {location_name} is {nearest_point['name']} - {nearest_point['description']}."})
        else:
            return jsonify({"response": "Sorry, I couldn't find a nearby pickup point."})

    return jsonify({"response": "Sorry, I don't have information on that. Please try asking about trips or pickup points."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
