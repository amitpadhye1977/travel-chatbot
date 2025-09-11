"""
Comprehensive single-file Flask backend for Trip Chatbot
- Contains DBService, ScraperService, HotelService (Google Places optional)
- Integrates OpenAI for fallback answers

Endpoints:
  - GET /trips                -> returns list of trips (for dropdown)
  - GET /trip                 -> returns trip details by name (query param: name)
  - GET /pickups              -> returns nearest pickup to lat & lng (query params: lat,lng)
  - POST /chat                -> main chat endpoint

CONFIG: set environment variables:
  DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
  GOOGLE_MAPS_API_KEY (optional)
  OPENAI_API_KEY (required for OpenAI fallback)

Run locally for testing:
  FLASK_APP=app.py FLASK_ENV=development flask run

Deploy on Render.com: push repo, add environment variables, and use Gunicorn.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import re
import math
import mysql.connector
from mysql.connector import pooling
import requests
from bs4 import BeautifulSoup

# Optional google maps client
try:
    import googlemaps
    HAS_GMAPS = True
except Exception:
    HAS_GMAPS = False

# OpenAI client
try:
    from openai import OpenAI
    HAS_OPENAI = True
except Exception:
    HAS_OPENAI = False

# ---------------------- Configuration ----------------------
DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
ASHTA_BASE = os.getenv('ASHTA_BASE', 'https://www.ashtavinayak.net')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

openai_client = None
if HAS_OPENAI and OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------------- App Init ---------------------------
app = Flask(__name__)
CORS(app)

# ---------------------- DB Service -------------------------
cnxpool = None

def init_db_pool():
    global cnxpool
    if cnxpool is None:
        cnxpool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="trip_pool",
            pool_size=5,
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset='utf8mb4'
        )

def get_conn():
    init_db_pool()
    return cnxpool.get_connection()

# ---------------------- Helpers ----------------------------
def rows_to_table(rows, cols):
    return [dict(zip(cols, r)) for r in rows]

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2.0)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2.0)**2
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# ---------------------- Trip / Pickup ----------------------
@app.route('/trips', methods=['GET'])
def api_trips():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT trip_name, cost, duration, details, trip_date, contact FROM trips")
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    cur.close(); conn.close()
    return jsonify({'ok': True, 'trips': rows_to_table(rows, cols)})

@app.route("/trip/<string:trip_name>", methods=["GET"])
def trip_details(trip_name):
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"ok": False, "error": "DB connection failed"}), 500

        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT trip_name, duration, cost, details, trip_date, contact FROM TRIPs WHERE trip_name = %s",
            (trip_name,)
        )
        trip = cursor.fetchone()
        conn.close()

        if not trip:
            return jsonify({"ok": False, "error": f\"Trip '{trip_name}' not found\"}), 404

        #-- return jsonify({"ok": True, "type": "trip_details", "trip": trip}) ---
        return jsonify({'ok': True, 'trip': rows_to_table(rows, cols)})
    except Exception as e:
        print("Trip details error:", e)
        return jsonify({"ok": False, "error": str(e)}), 500

    

@app.route('/pickups', methods=['GET'])
def api_pickups_nearest():
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    trip_id = request.args.get('trip_id', type=int)
    if lat is None or lng is None:
        return jsonify({'ok': False, 'error': 'lat and lng parameters are required'}), 400
    conn = get_conn()
    cur = conn.cursor()
    if trip_id:
        cur.execute("SELECT trip_id, pickuppoint, address, pickup_lat, pickup_long FROM pickuppoints WHERE trip_id = %s", (trip_id,))
    else:
        cur.execute("SELECT trip_id, pickuppoint, address, pickup_lat, pickup_long FROM pickuppoints")
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    cur.close(); conn.close()
    best = None; best_dist = float('inf')
    for r in rows:
        pr = dict(zip(cols, r))
        try:
            plat = float(pr.get('pickup_lat') or 0)
            plong = float(pr.get('pickup_long') or 0)
        except Exception:
            continue
        d = haversine(lat, lng, plat, plong)
        pr['distance_km'] = round(d, 3)
        if d < best_dist:
            best_dist = d; best = pr
    if not best:
        return jsonify({'ok': False, 'error': 'no pickup points found'}), 404
    return jsonify({'ok': True, 'nearest': best})

# ---------------------- Scraper ----------------------------
class ScraperService:
    def __init__(self, base_url=ASHTA_BASE, max_pages=20):
        self.base = base_url.rstrip('/')
        self.max_pages = max_pages

    def crawl_pages(self):
        to_visit = [self.base]
        visited = set()
        pages = []
        while to_visit and len(visited) < self.max_pages:
            url = to_visit.pop(0)
            if url in visited:
                continue
            try:
                r = requests.get(url, timeout=8)
                if r.status_code != 200:
                    visited.add(url)
                    continue
                visited.add(url)
                soup = BeautifulSoup(r.text, 'html.parser')
                pages.append({'url': url, 'title': soup.title.string if soup.title else '', 'text': soup.get_text(separator=' ', strip=True)})
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if href.startswith('/'):
                        full = self.base + href
                    elif href.startswith(self.base):
                        full = href
                    else:
                        continue
                    if full not in visited and full not in to_visit:
                        to_visit.append(full)
            except Exception:
                visited.add(url)
                continue
        return pages

    def search(self, query):
        pages = self.crawl_pages()
        q = query.lower()
        results = []
        for p in pages:
            text = p.get('text','').lower()
            if q in text:
                idx = text.find(q)
                start = max(0, idx-200)
                end = min(len(text), idx+200)
                snippet = p.get('text','')[start:end]
                results.append({'url': p['url'], 'title': p['title'], 'snippet': snippet})
        return results

scraper = ScraperService()

# ---------------------- Hotel Service -----------------------
class HotelService:
    def __init__(self, gmaps_api_key=''):
        self.key = gmaps_api_key
        if HAS_GMAPS and self.key:
            self.client = googlemaps.Client(key=self.key)
        else:
            self.client = None

    def extract_hotel_names(self, text):
        hotels = []
        for m in re.finditer(r'([A-Z][\w\s,&-]{1,60}Hotel|Hotel\s+[A-Z][\w\s,&-]{1,60})', text):
            hotels.append(m.group(0).strip())
        return list(dict.fromkeys(hotels))

    def lookup_hotel(self, hotel_name, location=None):
        if self.client:
            try:
                res = self.client.places(query=hotel_name)
                if res.get('results'):
                    r0 = res['results'][0]
                    info = {
                        'name': r0.get('name'),
                        'address': r0.get('formatted_address') if 'formatted_address' in r0 else r0.get('vicinity'),
                        'place_id': r0.get('place_id'),
                        'rating': r0.get('rating'),
                        'user_ratings_total': r0.get('user_ratings_total'),
                    }
                    try:
                        det = self.client.place(r0['place_id'])
                        pd = det.get('result', {})
                        info['website'] = pd.get('website')
                        info['photos'] = []
                        for ph in pd.get('photos', [])[:3]:
                            info['photos'].append({'photo_reference': ph.get('photo_reference')})
                        info['reviews'] = pd.get('reviews', [])[:3]
                    except Exception:
                        pass
                    return info
            except Exception:
                pass
        return {'name': hotel_name, 'search': f'https://www.google.com/search?q={requests.utils.quote(hotel_name)}'}

hotel_service = HotelService(GOOGLE_MAPS_API_KEY)

# ---------------------- Chat Endpoint ----------------------
@app.route('/chat', methods=['POST'])
def api_chat():
    data = request.get_json(force=True)
    q = (data.get('q') or '').strip()
    lat = data.get('lat')
    lng = data.get('lng')
    lang = data.get('lang', 'en')

    if not q:
        return jsonify({'ok': False, 'error': 'empty query'}), 400

    # Pickup queries
    if any(k in q.lower() for k in ['pickup', 'pick up', 'nearby', 'nearest', 'pickup point']):
        if lat is None or lng is None:
            if HAS_GMAPS and GOOGLE_MAPS_API_KEY:
                try:
                    gm = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
                    ge = gm.geocode(q)
                    if ge:
                        loc = ge[0]['geometry']['location']
                        lat = loc['lat']; lng = loc['lng']
                except Exception:
                    pass
        if lat is None or lng is None:
            return jsonify({'ok': False, 'error': 'latitude & longitude required for pickup nearest query'}), 400
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT trip_id, pickuppoint, address, pickup_lat, pickup_long FROM pickuppoints")
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            cur.close()
        best = None; best_dist = float('inf')
        for r in rows:
            pr = dict(zip(cols, r))
            try:
                plat = float(pr.get('pickup_lat') or 0); plong = float(pr.get('pickup_long') or 0)
            except Exception:
                continue
            d = haversine(lat, lng, plat, plong)
            pr['distance_km'] = round(d,3)
            if d < best_dist:
                best_dist = d; best = pr
        if best:
            return jsonify({'ok': True, 'type': 'pickup_nearest', 'nearest': best})
        else:
            return jsonify({'ok': False, 'error': 'no pickup points found'}), 404

    # Trip DB search
    keywords = q.split()
    like_clause = '%' + '%'.join(keywords) + '%'
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT trip_name, cost, duration, details, trip_date, contact FROM trips WHERE trip_name LIKE %s OR details LIKE %s", (like_clause, like_clause))
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    cur.close(); conn.close()
    if rows:
        trips = rows_to_table(rows, cols)
        for t in trips:
            hotels = hotel_service.extract_hotel_names(t.get('details','') or '')
            if hotels:
                t['hotels'] = []
                for h in hotels:
                    t['hotels'].append(hotel_service.lookup_hotel(h))
        return jsonify({'ok': True, 'type': 'trips_found', 'trips': trips})

    # Scraper fallback
    results = scraper.search(q)
    if results:
        return jsonify({'ok': True, 'type': 'scraped', 'results': results})

    # OpenAI fallback
    if openai_client:
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful trip assistant specialized in Ashtavinayak tours."},
                    {"role": "user", "content": q}
                ]
            )
            answer = response.choices[0].message.content
            return jsonify({'ok': True, 'type': 'openai', 'answer': answer})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500

    return jsonify({'ok': False, 'error': 'no information found for query'}), 404

# ---------------------- Main -------------------------------
if __name__ == '__main__':
    try:
        init_db_pool()
        print('DB pool initialized')
    except Exception as e:
        print('Warning: DB pool init failed -', e)
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
