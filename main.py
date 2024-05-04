# import random
# from string import ascii_letters

import pyttsx3  # Import pyttsx3 library for text-to-speech
from deepl import Translator
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room, send

from utils import generate_room_code

app = Flask(__name__)
deepl_api_key = (
    "e6f1d062-5229-463b-b11f-6945aa2b969f:fx"  # Replace with your actual DeepL API key
)
translator = Translator(deepl_api_key)
app.config["SECRET_KEY"] = "SDKFJSDFOWEIOF"
socketio = SocketIO(app)

rooms = {}


# Function for translating text
def translate_text(text, target_language):
    translation = translator.translate_text(text, target_lang=target_language)
    return translation.text


# Function to set target language
@socketio.on("set_output_language")
def set_output_language(language):
    session["target_language"] = language


# Function for speaking incoming message
def speak_message(message):
    engine = pyttsx3.init()  # Initialize the text-to-speech engine
    engine.say(message)  # Speak the message
    engine.runAndWait()  # Wait for the speech to finish


# Handle incoming message
@socketio.on("message")
def handle_message(text):
    room = session.get("room")
    name = session.get("name")
    target_language = session.get(
        "target_language", "ja"
    )  # Default to Japanese if not set

    if room not in rooms:
        return

    original_message = text["message"]

    # Speak the incoming message
    speak_message(original_message)

    # Translate the message to the target language
    translated_message = translate_text(original_message, target_language)

    message = {
        "sender": name,
        "message": translated_message,
    }

    send(message, to=room)
    rooms[room]["messages"].append(message)


# Route for the home page
@app.route("/", methods=["GET", "POST"])
def home():
    session.clear()

    if request.method == "POST":
        name = request.form.get("name")
        create = request.form.get("create", False)
        code = request.form.get("code")
        join = request.form.get("join", False)

        if not name:
            return render_template("home.html", error="Name is required", code=code)

        if create != False:
            room_code = generate_room_code(6, list(rooms.keys()))
            new_room = {"members": 0, "messages": []}
            rooms[room_code] = new_room

        if join != False:
            # no code
            if not code:
                return render_template(
                    "home.html",
                    error="Please enter a room code to enter a chat room",
                    name=name,
                )
            # invalid code
            if code not in rooms:
                return render_template(
                    "home.html", error="Room code invalid", name=name
                )

            room_code = code

        session["room"] = room_code
        session["name"] = name
        return redirect(url_for("room"))
    else:
        return render_template("home.html")


# Route for the chat room
@app.route("/room")
def room():
    room = session.get("room")
    name = session.get("name")

    if name is None or room is None or room not in rooms:
        return redirect(url_for("home"))

    messages = rooms[room]["messages"]
    return render_template("room.html", room=room, user=name, messages=messages)


# Function to handle user connection
@socketio.on("connect")
def handle_connect():
    name = session.get("name")
    room = session.get("room")

    if name is None or room is None:
        return
    if room not in rooms:
        leave_room(room)

    join_room(room)
    send({"sender": "", "message": f"{name} has entered the chat"}, to=room)
    rooms[room]["members"] += 1


# Function to handle user disconnection
@socketio.on("disconnect")
def handle_disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]

    send({"message": f"{name} has left the chat", "sender": ""}, to=room)


if __name__ == "__main__":
    socketio.run(app, debug=True)
