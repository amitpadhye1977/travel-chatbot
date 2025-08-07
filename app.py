from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import requests
import mysql.connector

app = Flask(__name__)
CORS(app, origins=["https://ashtavinayak.net"])

db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}

rapidapi_key = os.getenv("RAPIDAPI_KEY")
rapidapi_host = os.getenv("RAPIDAPI_HOST")  # e.g., chatgpt-42.p.rapidapi.com

def fetch_trip_details():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT name, duration, cost, inclusions, start_day, contact FROM trips")
        results = cursor.fetchall()
        conn.close()

        trips = []
        for row in results:
            trips.append({
                'name': row[0],
                'duration': row[1],
                'cost': row[2],
                'inclusions': row[3],
                's
