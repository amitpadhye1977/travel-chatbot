from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import openai
import mysql.connector
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend-backend communication

# Set your OpenAI API key from environment variable
openai.api_key = os.environ.get("OPENAI_API_KEY")

# MySQL database configuration (read from environment variables)
db_config = {
    'host': os.environ.get("DB_HOST"),
    'user': os.environ.get("DB_USER"),
    'password': os.environ.get("DB_PASSWORD"),
    'database': os.environ.get("DB_NAME"),
    'ssl_disabled': True  # Disable SSL if not using Planetscale or similar
}

@app.route('/')
def index():
    return render_template('i_
