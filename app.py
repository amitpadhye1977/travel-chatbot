import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import pymysql
import openai
import requests

# -----------------------
# Logging setup
# -----------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------
# Flask App
# -----------------------
app = Flask(__name__)

CORS(app, origins=["https://www.ashtavinayak.net"])

# -----------------------
# Environment Variables
# -----------------------
DB_HOST = os.environ.get("DB_HOST")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_NAME = os.environ.get("DB_NAME")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_API_KEY")

openai.api_key = OPENAI_API_KEY

# -----------------------
# Database Connection
# -----------------------
def get_db_connection():
    try:
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )
        logger.info("✅ MySQL Connected")
        return conn
    except Exception as e:
        logger.error(f"❌ DB Connection Error: {e}")
        return None

# -----------------------
# Trip Info Search
# -----------------------
def search_trip_info(keyword):
    conn = get_db_connection()
    import pymysql.cursors
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    query = """
        SELECT * FROM trips
        WHERE name LIKE %s OR inclusions LIKE %s
    """
    like_pattern = f"%{keyword}%"
    cursor.execute(query, (like_pattern, like_pattern))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results

# -----------------------
# Temple Nearest Search
# -----------------------
def find_nearest_temple(user_location_name):
    conn = get_db_connection()
    if not conn:
        return None

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT name, address, latitude, longitude FROM pickuppoints")
            temples = cursor.fetchall()

        # Geocode user location
        geo_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={user_location_name}&key={GOOGLE_MAPS_API_KEY}"
        geo_res = requests.get(geo_url).json()
        if geo_res["status"] != "OK":
            logger.warning("❌ Could not geocode location")
            return None
        user_lat = geo_res["results"][0]["geometry"]["location"]["lat"]
        user_lng = geo_res["results"][0]["geometry"]["location"]["lng"]

        # Find nearest temple
        def distance(lat1, lon1, lat2, lon2):
            from math import radians, sin, cos, sqrt, atan2
            R = 6371
            dlat = radians(lat2 - lat1)
            dlon = radians(lon2 - lon1)
            a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
            return R * 2 * atan2(sqrt(a), sqrt(1-a))

        nearest = min(temples, key=lambda t: distance(user_lat, user_lng, t["latitude"], t["longitude"]))
        logger.info(f"✅ Nearest temple: {nearest}")
        return nearest
    except Exception as e:
        logger.error(f"❌ Nearest Temple Search Error: {e}")
        return None
    finally:
        conn.close()

# -----------------------
# OpenAI Chat Response
# -----------------------
def get_openai_response(user_message):
    try:
        completion = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a travel assistant chatbot."},
                {"role": "user", "content": user_message}
            ]
        )
        return completion.choices[0].message["content"]
    except Exception as e:
        logger.error(f"❌ OpenAI API Error: {e}")
        return "Sorry, I am having trouble answering that."

# -----------------------
# Chatbot Endpoint
# -----------------------
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "").strip()
    logger.info(f"💬 User message: {user_message}")

    # Check for nearest temple query
    if "nearest temple" in user_message.lower():
        location_name = user_message.replace("nearest temple from", "").strip()
        temple = find_nearest_temple(location_name)
        if temple:
            return jsonify({"response": f"The nearest temple is {temple['name']} at {temple['address']}."})
        else:
            return jsonify({"response": "I couldn't find a nearby temple."})

    # Search for trip info
    trips = search_trip_info(user_message)
    if trips:
        trips_info = "\n\n".join([
                f"📍 {t['name']}\n"
                f"⏳ Duration: {t['duration']}\n"
                f"💰 Cost: {t['cost']}\n"
                f"✅ Inclusions: {t['inclusions']}\n"
                f"📅 Start Day: {t['start_day']}\n"
                f"📞 Contact: {t['contact']}"
                for t in results
            ])
        return jsonify({"reply": f"I found these trips:\n\n{trips_info}"})

    # Fallback to OpenAI
    ai_response = get_openai_response(user_message)
    return jsonify({"response": ai_response})

# -----------------------
# Health Check
# -----------------------
@app.route("/")
def home():
    return "Chatbot API is running"

# -----------------------
# Run App
# -----------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
