from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import openai
import os
import mysql.connector

app = Flask(__name__)
CORS(app)

# API Keys
openai.api_key = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# MySQL Connection
db = mysql.connector.connect(
    host=os.getenv("MYSQL_HOST"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DB")
)
cursor = db.cursor(dictionary=True)

def get_coordinates(place_name):
    """Get lat/lng from Google Maps API"""
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": place_name, "key": GOOGLE_API_KEY}
    response = requests.get(url, params=params).json()
    if response['status'] == 'OK':
        location = response['results'][0]['geometry']['location']
        return location['lat'], location['lng']
    return None, None

def find_nearest_temple(user_location):
    """Find nearest temple from MySQL DB"""
    user_lat, user_lng = get_coordinates(user_location)
    if not user_lat:
        return "Sorry, I couldn't find your location."

    cursor.execute("SELECT * FROM pickuppoints")
    temples = cursor.fetchall()

    nearest_temple = None
    shortest_distance = float("inf")

    for temple in temples:
        if not temple['latitude'] or not temple['longitude']:
            continue

        # Distance Matrix API
        url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        params = {
            "origins": f"{user_lat},{user_lng}",
            "destinations": f"{temple['latitude']},{temple['longitude']}",
            "key": GOOGLE_API_KEY
        }
        dist_data = requests.get(url, params=params).json()

        if dist_data['rows'] and dist_data['rows'][0]['elements'][0]['status'] == 'OK':
            distance = dist_data['rows'][0]['elements'][0]['distance']['value']  # meters
            if distance < shortest_distance:
                shortest_distance = distance
                nearest_temple = temple

    if nearest_temple:
        return f"Nearest temple is {nearest_temple['name']} at {nearest_temple['address']} ({shortest_distance/1000:.2f} km away)."
    else:
        return "No temples found nearby."

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message")

    # Temple search
    if "nearest temple" in user_message.lower():
        location_name = user_message.replace("nearest temple from", "").strip()
        result = find_nearest_temple(location_name)
        return jsonify({"reply": result})

    # Default ChatGPT response
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": user_message}]
    )
    bot_reply = response.choices[0].message.content.strip()
    return jsonify({"reply": bot_reply})

if __name__ == "__main__":
    app.run(debug=True)
