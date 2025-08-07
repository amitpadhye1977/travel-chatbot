from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import openai
import mysql.connector

app = Flask(__name__)
CORS(app)

# Set your OpenAI API key here
openai.api_key = 'OPENAI_API_KEY'

# MySQL configuration
db_config = {
    'host': 'DB_HOST',        # or your remote DB host
    'user': 'DB_USER',
    'password': 'DB_PASSWORD',
    'database': 'DB_NAME'
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_message = request.json.get('message')
        if not user_message:
            return jsonify({'reply': 'No message received.'}), 400

        # Connect to MySQL
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT place_name, description FROM trips")
        results = cursor.fetchall()
        cursor.close()
        conn.close()

        # Prepare context for OpenAI
        context = "Here is the travel information:\n"
        for row in results:
            context += f"{row['place_name']}: {row['description']}\n"

        context += f"\nUser: {user_message}\nAI:"

        # Send to OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful travel assistant."},
                {"role": "user", "content": context}
            ]
        )

        reply = response['choices'][0]['message']['content'].strip()
        return jsonify({'reply': reply})

    except Exception as e:
        return jsonify({'reply': f"Error: {str(e)}"})

if __name__ == '__main__':
    app.run(debug=True)
