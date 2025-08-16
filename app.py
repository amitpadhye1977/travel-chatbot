import os
import re
import math
import json
import requests
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import mysql.connector
from openai import OpenAI

# -------------------- Flask & CORS --------------------
app = Flask(__name__)

# Allow both apex and www on your domain
CORS(app, resources={r"/*": {"origins": ["https://ashtavinayak.net"]}})


# -------------------- OpenAI --------------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -------------------- MySQL --------------------
def get_db_connection():
    """Connect to MySQL using Render env vars. Supports DB_PASS or DB_PASSWORD."""
    password = os.getenv("DB_PASSWORD", os.getenv("DB_PASS"))
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=password,
        database=os.getenv("DB_NAME"),
    )

# --- Fetch Trips ---
@app.route("/trips", methods=["GET"])
def get_trips():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        cursor = conn.cursor()
        cursor.execute("SELECT trip_name FROM trips")
        trips = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return jsonify({"trips": trips})  # wrap inside "trips"
    except Exception as e:
        print("Error fetching trips:", e)  # log for debugging
        return jsonify({"error": str(e)}), 500



# -------------------- Helpers: Trips --------------------
def fetch_all_trips():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, trip_name, details, cost, duration, trip_date FROM trips")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def search_trips(keyword):
    """Keyword search over trips."""
    like = f"%{keyword}%"
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    query = """
        SELECT id, trip_name, details, cost, duration, trip_date
        FROM trips
        WHERE trip_name LIKE %s OR details LIKE %s OR duration LIKE %s
           OR CAST(cost AS CHAR) LIKE %s OR CAST(trip_date AS CHAR) LIKE %s
        ORDER BY trip_date IS NULL, trip_date ASC, trip_name ASC
        LIMIT 20
    """
    cur.execute(query, (like, like, like, like, like))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

# -------------------- Helpers: Pickup points --------------------
def fetch_pickup_points(trip_id=None):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    if trip_id:
        cur.execute("""
            SELECT p.id, p.trip_id, p.pickup_point, p.pickup_lat, p.pickup_lon, t.trip_name
            FROM pickuppoints p
            JOIN trips t ON t.id = p.trip_id
            WHERE p.trip_id = %s
        """, (trip_id,))
    else:
        cur.execute("""
            SELECT p.id, p.trip_id, p.pickup_point, p.pickup_lat, p.pickup_lon, t.trip_name
            FROM pickuppoints p
            JOIN trips t ON t.id = p.trip_id
        """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    c = 2 * math.asin(math.sqrt(a))
    return R * c

# -------------------- Geocoding via Google API --------------------
def geocode_place(place_name):
    """Return (lat, lon, formatted_address) or None."""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return None
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": place_name, "key": api_key}
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if data.get("status") == "OK" and data.get("results"):
            r = data["results"][0]
            loc = r["geometry"]["location"]
            return (loc["lat"], loc["lng"], r.get("formatted_address", place_name))
    except Exception as e:
        print("Geocode error:", e)
    return None

# -------------------- Intent parsing --------------------
COORDS_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)")

def extract_coords(text):
    m = COORDS_RE.search(text or "")
    if not m:
        return None
    try:
        return float(m.group(1)), float(m.group(2))
    except:
        return None

def detect_trip_in_text(text, trips):
    """Return trip_id if a trip name is mentioned inside user text, else None."""
    if not text:
        return None
    text_l = text.lower()
    best = None
    for t in trips:
        name = (t.get("trip_name") or "").lower()
        if name and name in text_l:
            best = t["id"]
            break
    return best

# -------------------- OpenAI answer grounded on trips --------------------
def answer_with_openai(user_message, trips):
    # Prepare a compact catalog for grounding
    catalog = "\n".join([
        f"- {t['trip_name']}: {t['details']} | Cost ₹{t['cost']}, Duration {t['duration']}, Date {t['trip_date']}"
        for t in trips[:40]  # cap to keep prompt small
    ]) or "No trips available."

    system_prompt = (
        "You are a helpful travel assistant for Ashtavinayak Tours. "
        "Answer strictly using the provided trips catalog. "
        "If something isn't in the catalog, say you don't have that info."
    )
    user_prompt = (
        f"Trips catalog:\n{catalog}\n\n"
        f"User ask: {user_message}\n\n"
        "Reply clearly with bullet points; include trip names, cost, duration, and date when relevant."
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=400,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print("OpenAI error:", e)
        return "I couldn't generate an answer right now."

# -------------------- Routes --------------------
@app.route("/", methods=["GET", "HEAD", "OPTIONS"])
def health():
    return jsonify({"ok": True, "service": "ashtavinayak-chatbot"})

# --- inside your /chat route ---
@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == "OPTIONS":
        return ("", 204)

    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    language = data.get("language", "en")  # <-- NEW: default English
    
    body_lat = data.get("lat")
    body_lng = data.get("lng")

    if not user_message:
        return jsonify({"reply": "Please type your question."})

    # ---------------- Pickup logic (unchanged) ----------------
    pickup_intent = any(kw in user_message.lower() for kw in [
        "nearest pickup", "pickup near", "pickup nearby", "closest pickup", "pickup point"
    ])
    if pickup_intent:
        ...
        return jsonify({"reply": reply})

    # ---------------- Trip search logic (unchanged) ----------------
    trips_found = search_trips(user_message)
    if trips_found:
        lines = []
        for t in trips_found:
            line = f"• {t['trip_name']} — ₹{t['cost']} | {t['duration']}"
            if t.get("trip_date") is not None:
                line += f" | Date: {t['trip_date']}"
            if t.get("details"):
                snippet = (t["details"][:120] + "…") if len(t["details"]) > 120 else t["details"]
                line += f"\n   {snippet}"
            lines.append(line)
        # ✅ Translate results via OpenAI if not English
        if language != "en":
            trans_prompt = f"Translate the following response into {language}:\n\n" + "\n".join(lines)
            try:
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a translator."},
                        {"role": "user", "content": trans_prompt},
                    ]
                )
                translated = resp.choices[0].message.content.strip()
                return jsonify({"reply": translated})
            except Exception as e:
                print("Translation error:", e)
        return jsonify({"reply": "Here’s what I found:\n" + "\n".join(lines)})

    # ---------------- Fallback AI grounded on catalog ----------------
    all_trips = fetch_all_trips()
    ai_reply = answer_with_openai(user_message, all_trips)

    # ✅ Translate AI reply if needed
    if language != "en":
        trans_prompt = f"Translate the following response into {language}:\n\n{ai_reply}"
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a translator."},
                    {"role": "user", "content": trans_prompt},
                ]
            )
            ai_reply = resp.choices[0].message.content.strip()
        except Exception as e:
            print("Translation error:", e)

    return jsonify({"reply": ai_reply})


# -------------------- Gunicorn entry --------------------
if __name__ == "__main__":
    # Local run; Render uses gunicorn
    app.run(host="0.0.0.0", port=5000)
