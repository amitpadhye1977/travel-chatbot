from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import os
import requests
import math

app = Flask(__name__)

# Allow CORS for both main and www domain
CORS(app, resources={
    r"/*": {
        "origins": [
            "https://ashtavinayak.net",
            "https://www.ashtavinayak.net"
        ]
    }
})

# Get DB and API keys from environment variables
DB_HOST = os.environ.get("DB_HOST")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_NAME = os.environ.get("DB_NAME")
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_API_KEY")


# ---------- MySQL connection helper ----------
def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )


# ---------- Trip search ----------
def search_trip_info(query):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        sql = """
            SELECT name, duration, cost, inclusions, start_day, contact
            FROM trips
            WHERE LOWER(name) LIKE %s
               OR LOWER(inclusions) LIKE %s
        """
        keyword = f"%{query.lower()}%"
        cursor.execute(sql, (keyword, keyword))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        trips_list = []
        for row in rows:
            trips_list.append({
                "name": row[0],
                "duration": row[1],
                "cost": row[2],
                "inclusions": row[3],
                "start_day": row[4],
                "contact": row[5]
            })

        return trips_list
    except Exception as e:
        print("Error in search_trip_info:", e)
        return []


# ---------- Haversine formula to calculate distance ----------
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in KM
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


# ---------- Pickup search using Google Maps ----------
def get_coordinates_from_place(place_name):
    try:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"address": place_name, "key": GOOGLE_MAPS_API_KEY}
        res = requests.get(url, params=params).json()
        if res["status"] == "OK":
            location = res["results"][0]["geometry"]["location"]
            return location["lat"], location["lng"]
        return None, None
    except Exception as e:
        print("Error in get_coordinates_from_place:", e)
        return None, None


def find_nearest_pickup(user_place):
    try:
        user_lat, user_lon = get_coordinates_from_place(user_place)
        if user_lat is None or user_lon is None:
            return None

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name, description, latitude, longitude FROM pickuppoints")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        nearest = None
        min_dist = float("inf")
        for row in rows:
            dist = haversine_distance(user_lat, user_lon, row[2], row[3])
            if dist < min_dist:
                min_dist = dist
                nearest = {
                    "name": row[0],
                    "description": row[1],
                    "latitude": row[2],
                    "longitude": row[3],
                    "distance_km": round(dist, 2)
                }

        return nearest
    except Exception as e:
        print("Error in find_nearest_pickup:", e)
        return None


# ---------- Chat endpoint ----------
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_message = data.get("message", "").lower()

        response = ""

        # If "pickup nearby" in message
        if "pickup nearby" in user_message:
            place = user_message.replace("pickup nearby", "").strip()
            nearest_pickup = find_nearest_pickup(place)
            if nearest_pickup:
                response += f"Nearest pickup point to {place}:\n"
                response += f"- {nearest_pickup['name']} ({nearest_pickup['description']})\n"
                response += f"  Distance: {nearest_pickup['distance_km']} km\n"
                response += f"  Location: https://maps.google.com/?q={nearest_pickup['latitude']},{nearest_pickup['longitude']}\n"
            else:
                response += "Sorry, I couldn't find a nearby pickup point.\n"

        # Trip search
        elif any(word in user_message for word in ["trip", "tour", "yatra"]):
            trips = search_trip_info(user_message)
            if trips:
                response += "Here are some matching trips:\n"
                for trip in trips:
                    response += f"- {trip['name']} ({trip['duration']}) - ₹{trip['cost']}\n"
                    response += f"  Inclusions: {trip['inclusions']}\n"
                    response += f"  Start Day: {trip['start_day']}\n"
                    response += f"  Contact: {trip['contact']}\n\n"
            else:
                response += "Sorry, I couldn't find any trips matching your query.\n"

        else:
            response += "I can help you with trip details or nearest pickup points. Try asking something like:\n"
            response += '"Tell me about Ashtavinayak yatra" or "Pickup nearby Dahisar".\n'

        return jsonify({"response": response})

    except Exception as e:
        print("Error in /chat:", e)
        return jsonify({"response": "An error occurred while processing your request."}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)


# Flask app
app = Flask(__name__)

# CORS fix: allow both domains, all methods, credentials support
CORS(
    app,
    resources={r"/*": {"origins": [
        "https://ashtavinayak.net",
        "https://www.ashtavinayak.net"
    ]}},
    supports_credentials=True,
    allow_headers=["Content-Type"],
    methods=["GET", "POST", "OPTIONS"]
)

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
def search_trip_info(query):
    try:
        conn = mysql.connector.connect(
            host=os.environ.get("DB_HOST"),
            user=os.environ.get("DB_USER"),
            password=os.environ.get("DB_PASSWORD"),
            database=os.environ.get("DB_NAME")
        )
        cursor = conn.cursor()

        # Flexible keyword search across multiple columns
        sql = """
            SELECT name, duration, cost, inclusions, start_day, contact
            FROM trips
            WHERE LOWER(name) LIKE %s
               OR LOWER(inclusions) LIKE %s
        """
        keyword = f"%{query.lower()}%"
        cursor.execute(sql, (keyword, keyword))

        results = cursor.fetchall()
        cursor.close()
        conn.close()

        if not results:
            return "No matching trips found."

        # Format results nicely
        reply_parts = []
        for trip in results:
            trip_name, duration, cost, inclusions, start_day, contact = trip
            reply_parts.append(
                f"Trip: {trip_name}\n"
                f"Duration: {duration}\n"
                f"Cost: {cost}\n"
                f"Inclusions: {inclusions}\n"
                f"Start Day: {start_day}\n"
                f"Contact: {contact}"
            )

        return "\n\n".join(reply_parts)

    except Exception as e:
        print("Error in search_trip_info:", e)
        return "Error fetching trip details."

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
