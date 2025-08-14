import os
import mysql.connector
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)

# Allow both domains
CORS(app, resources={r"/*": {"origins": [
    "https://ashtavinayak.net",
    "https://www.ashtavinayak.net"
]}})

# ---------------- Database Connection ---------------- #
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

# ---------------- Search Functions ---------------- #
def search_trips(keyword):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)  # ✅ Dict cursor
    query = """
        SELECT name, duration, cost, inclusions, start_day, contact
        FROM trips
        WHERE name LIKE %s OR inclusions LIKE %s OR description LIKE %s
    """
    like_kw = f"%{keyword}%"
    cursor.execute(query, (like_kw, like_kw, like_kw))
    trips = cursor.fetchall()
    cursor.close()
    conn.close()
    return trips

def search_temples(keyword):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)  # ✅ Dict cursor
    query = """
        SELECT name, location, description
        FROM temples
        WHERE name LIKE %s OR location LIKE %s OR description LIKE %s
    """
    like_kw = f"%{keyword}%"
    cursor.execute(query, (like_kw, like_kw, like_kw))
    temples = cursor.fetchall()
    cursor.close()
    conn.close()
    return temples

# ---------------- Google Maps API ---------------- #
def search_google_maps_nearby(location, keyword="temple", radius=5000):
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": location,  # "lat,lng"
        "radius": radius,
        "keyword": keyword,
        "key": api_key
    }
    r = requests.get(url, params=params)
    data = r.json()
    results = []
    if "results" in data:
        for place in data["results"]:
            results.append({
                "name": place.get("name"),
                "address": place.get("vicinity"),
                "rating": place.get("rating")
            })
    return results

# ---------------- Chat Endpoint ---------------- #
@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "").lower()
    location = request.json.get("location")  # "lat,lng" for Google Maps

    response = ""

    # Trip Search
    if "trip" in user_message or "tour" in user_message:
        trips = search_trips(user_message)
        if trips:
            response += "Here are some trips I found:\n\n"
            for trip in trips:
                response += (
                    f"- {trip['name']} ({trip['duration']}) - ₹{trip['cost']}\n"
                    f"  Inclusions: {trip['inclusions']}\n"
                    f"  Start Day: {trip['start_day']}\n"
                    f"  Contact: {trip['contact']}\n\n"
                )
        else:
            response += "Sorry, I couldn't find any trips matching your request.\n\n"

    # Temple Search in DB
    if "temple" in user_message:
        temples = search_temples(user_message)
        if temples:
            response += "Here are some temples I found in our database:\n\n"
            for temple in temples:
                response += (
                    f"- {temple['name']} ({temple['location']})\n"
                    f"  {temple['description']}\n\n"
                )

    # Nearby Temple Search using Google Maps
    if location and "temple" in user_message:
        gmaps_temples = search_google_maps_nearby(location)
        if gmaps_temples:
            response += "Nearby temples from your location:\n\n"
            for t in gmaps_temples:
                response += (
                    f"- {t['name']} ({t['address']})\n"
                    f"  Rating: {t.get('rating', 'N/A')}\n\n"
                )

    if not response.strip():
        response = "I couldn't find an answer."

    return jsonify({"response": response})

# ---------------- Run ---------------- #
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
