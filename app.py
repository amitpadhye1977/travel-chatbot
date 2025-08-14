from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import os

app = Flask(__name__)
CORS(app)

# --- Database Connection ---
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "YOUR_DB_HOST"),
        user=os.getenv("DB_USER", "YOUR_DB_USER"),
        password=os.getenv("DB_PASS", "YOUR_DB_PASSWORD"),
        database=os.getenv("DB_NAME", "YOUR_DB_NAME")
    )

# --- Search Trips ---
def search_trips(keyword):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    like_kw = f"%{keyword}%"
    query = """
        SELECT name, duration, cost, inclusions, start_day, contact
        FROM trips
        WHERE name LIKE %s OR inclusions LIKE %s OR start_day LIKE %s
    """
    cursor.execute(query, (like_kw, like_kw, like_kw))
    results = cursor.fetchall()

    cursor.close()
    conn.close()
    return results

# --- Search Pickup Points (Temples) ---
def search_temple_locations(keyword):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    like_kw = f"%{keyword}%"
    query = """
        SELECT name, address, latitude, longitude
        FROM pickuppoints
        WHERE name LIKE %s OR address LIKE %s
    """
    cursor.execute(query, (like_kw, like_kw))
    results = cursor.fetchall()

    cursor.close()
    conn.close()
    return results

# --- Chat Endpoint ---
@app.route("/chat", methods=["POST"])
def chat():
    try:
        user_message = request.json.get("message", "").strip()

        if not user_message:
            return jsonify({"response": "Please type something."})

        # Temple search trigger
        if "temple" in user_message.lower() or "pickup" in user_message.lower():
            temples = search_temple_locations(user_message)
            if temples:
                response = "Here are the locations I found:\n\n"
                for t in temples:
                    maps_link = f"https://www.google.com/maps?q={t['latitude']},{t['longitude']}"
                    response += f"- {t['name']} ({t['address']})\n  📍 [View on Google Maps]({maps_link})\n\n"
            else:
                response = "I couldn't find any matching temple or pickup point."

        # Trip search trigger
        elif "trip" in user_message.lower() or "tour" in user_message.lower():
            trips = search_trips(user_message)
            if trips:
                response = "Here are the trips matching your search:\n\n"
                for trip in trips:
                    response += (
                        f"- {trip['name']} ({trip['duration']}) - ₹{trip['cost']}\n"
                        f"  Inclusions: {trip['inclusions']}\n"
                        f"  Start Day: {trip['start_day']}\n"
                        f"  Contact: {trip['contact']}\n\n"
                    )
            else:
                response = "I couldn't find any trips matching your search."

        else:
            response = "I can help you with trips or temple/pickup locations. Please try asking about those."

        return jsonify({"response": response})

    except Exception as e:
        print("Error in /chat:", e)
        return jsonify({"response": f"An error occurred: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
