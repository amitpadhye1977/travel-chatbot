@app.route("/chat", methods=["POST"])
def chat():
    try:
        user_message = request.json.get("message", "")
        if not user_message:
            return jsonify({"reply": "Please ask a valid question."})

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM trips")
        trips = cursor.fetchall()
        cursor.close()
        conn.close()

        trip_info = ""
        for trip in trips:
            trip_info += (
                f"\nTrip Name: {trip['name']}\n"
                f"Duration: {trip['duration']}\n"
                f"Cost: {trip['cost']}\n"
                f"Inclusions: {trip['inclusions']}\n"
                f"Start Day: {trip['start_day']}\n"
                f"Contact: {trip['contact']}\n"
            )

        prompt = (
            f"Customer asked: {user_message}\n"
            f"Here are available trips:\n{trip_info}\n"
            f"Reply politely using the trip details."
        )

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful trip assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )

        bot_reply = response['choices'][0]['message']['content']
        return jsonify({"reply": bot_reply})

    except Exception as e:
        error_msg = str(e)
        print("Error:", error_msg)
        return jsonify({"reply": f"Error: {error_msg}"})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
