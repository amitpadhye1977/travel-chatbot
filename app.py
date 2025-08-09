from flask import Flask, request, jsonify
import os
import mysql.connector
import openai
import googlemaps

app = Flask(__name__)

# Load environment variables
openai.api_key = os.environ.get("OPENAI_API_KEY")
gmaps = googlemaps.Client(key=os.environ.get("GOOGLE_API_KEY"))

db_config = {
    'host': os.environ.get("DB_HOST"),
    'user': os.environ.get("DB_USER"),
    'password': os.environ.get("DB_PASSWORD"),
    'database': os.environ.get("DB_NAME")
}

# Helper: Get MySQL connection
def get_db_connection():
    return mysql.connector.connect(**db_config)

# Helper: Search trip info from MySQL
def search_trip_info(user_query):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM trips WHERE description LIKE %s", ("%" + user_query + "%",))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results

# Helper: Find nearest temple from MySQL using Google Maps
def find_nearest_temple(user_location_name):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT name, address, latitude, longitude FROM pickuppoints")
    temples = cursor.fetchall()
    cursor.close()
    conn.close()

    # Get coordinates for user location
    geocode_result = gmaps.geocode(user_location_name)
    if not geocode_result:
        return "Could not find your location."

    user_lat = geocode_result[0]['geometry']['location']['lat']
    user_lng = geocode_result[0]['geometry']['location']['lng']

    # Find nearest temple by distance
    nearest_temple = None
    shortest_distance = float("inf")

    for temple in temples:
        temple_lat = float(temple['latitude'])
        temple_lng = float(temple['longitude'])
        distance_result = gmaps.distance_matrix(
            origins=(user_lat, user_lng),
            destinations=(temple_lat, temple_lng),
            mode="driving"
        )

        distance_text = distance_result['rows'][0]['elements'][0]['distance']['text']
        distance_value = distance_result['rows'][0]['elements'][0]['distance']['value']  # meters

        if distance_value < shortest_distance:
            shortest_distance = distance_value
            nearest_temple = {
                "name": temple['name'],
                "address": temple['address'],
                "distance": distance_text
            }

    if nearest_temple:
        return f"The nearest temple is {nearest_temple['name']} located at {nearest_temple['address']} ({nearest_temple['distance']} away)."
    else:
        return "No temples found in the database."

# Chatbot endpoint
@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "")

    # Step 1: Check if user is asking about nearest temple
    if "pickup" in user_message.lower():
        # Try to extract location (default Borivali if none given)
        if "in " in user_message.lower():
            location = user_message.lower().split("in ")[1]
        else:
            location = "Borivali"
        temple_info = find_nearest_temple(location)
        return jsonify({"reply": temple_info})

    # Step 2: Check trip info in MySQL
    trip_results = search_trip_info(user_message)
    if trip_results:
        reply = "I found these trips:\n" + "\n".join([t['description'] for t in trip_results])
        return jsonify({"reply": reply})

    # Step 3: Fallback to OpenAI chatbot
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a helpful travel assistant."},
                      {"role": "user", "content": user_message}]
        )
        bot_reply = response.choices[0].message.content.strip()
        return jsonify({"reply": bot_reply})
    except Exception as e:
        return jsonify({"reply": f"Error: {str(e)}"})

# Root route
@app.route("/")
def home():
    return "Chatbot API is running."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
