from flask import Flask, render_template, redirect, url_for, request, session
from flask_socketio import SocketIO, join_room, leave_room, emit
import random, string, time
from db import db, Room, Member, Message
from datetime import datetime

# app setup
app = Flask(__name__)
app.config["SECRET_KEY"] = "secretkey"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///chat.db"

# initialize socketio and sqlalchemy
socketio = SocketIO(app)
db.init_app(app)

# create fresh database every start // db.drop_all is only here for testing purposes 
with app.app_context():
    db.drop_all()
    db.create_all()

# generate room codes 
def gen_room_code(length: int, existing_codes: list[str]) -> str:
    while True:
        code_chars = [random.choice(string.ascii_letters) for _ in range(length)]
        room_code = "".join(code_chars)
        if room_code not in existing_codes:
            return room_code

@app.route("/", methods=["GET", "POST"])
def home():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name-input")
        code = request.form.get("room-code")
        create = request.form.get("createchatroombutton", False)
        join = request.form.get("joinchatroombutton", False)

        if not name:
            return render_template("home.html", error="Name is required")

        session["name"] = name
        # create new room
        if create == "true":
            room_code = code if code and code.strip() else gen_room_code(6, [room.id for room in Room.query.all()])
            if not db.session.get(Room, room_code):
                new_room = Room(id=room_code, member_count=0)
                db.session.add(new_room)
                db.session.commit()
            session["room"] = room_code
            return render_template("redirect.html")

        # join room
        elif join == "true":
            if not code:
                return render_template("home.html", error="You must enter a room code to join a room", name=name)
            room = db.session.get(Room, code)
            if not room:
                return render_template("home.html", error="Invalid room code", name=name)
            session["room"] = code
            return render_template("redirect.html")
    return render_template("home.html")


@app.route("/room")
def room():
    room_code = session.get("room")
    name = session.get("name")
    member_id = request.args.get("member_id")

    if not room_code or not name or not member_id:
        return redirect(url_for("home"))

    # recreate the room if deleted
    room = db.session.get(Room, room_code)
    if not room:
        room = Room(id=room_code, member_count=1)
        db.session.add(room)
        db.session.commit()

    # create member if missing
    if not db.session.get(Member, member_id):
        new_member = Member(id=member_id, room_id=room_code, name=name)
        db.session.add(new_member)
        db.session.commit()

    # checks the amount of members in a room
    rooms = socketio.server.manager.rooms.get("/", {})
    participants = rooms.get(room_code, set())
    room.member_count = len(participants)
    db.session.commit()

    # serializes messages in JSON format
    messages = Message.query.filter_by(room_id=room_code).all()
    serialized_messages = [
        {"message": m.content, "sender": m.sender, "member_id": str(m.sender_id), "timestamp": m.timestamp} for m in messages
    ]
    return render_template("room.html", room=room, user_name=name, user_id=str(member_id), messages=serialized_messages)


@socketio.on("connect")
def handle_connect():
    room_code = request.args.get("room")
    name = request.args.get("name")
    member_id = request.args.get("sender_id")

    if not room_code or not name or not member_id:
        return

    session["room"] = room_code
    session["name"] = name
    session["member_id"] = member_id

    join_room(room_code)

    

    room = db.session.get(Room, room_code)
    participants = socketio.server.manager.rooms.get("/", {}).get(room_code, set())

    # update member count and render messages
    if room:
        room.member_count = len(participants)
        db.session.commit()
        for msg in room.messages:
            emit("chat_message", {
                "sender": msg.sender,
                "member_id": str(msg.sender_id),
                "message": msg.content,
                "timestamp": msg.timestamp
            }, to=request.sid)


@socketio.on("disconnect")
def handle_disconnect():
    room_code = session.get("room")
    name = session.get("name")
    if not room_code or not name:
        return

    leave_room(room_code)
    # check if user just reloaded or actually left
    socketio.start_background_task(handle_reload, room_code, name)

def handle_reload(room_code, name):
    with app.app_context():
        # waits for one second so socketio won't automatically think user left
        time.sleep(1)

        room = db.session.get(Room, room_code)
        participants = socketio.server.manager.rooms.get("/", {}).get(room_code, set())

        if room:
            if not participants:
                db.session.delete(room)
                db.session.commit()
            else:
                # skip "user left the chat" message if room is not empty
                room.member_count = len(participants)
                db.session.commit()
                return  

            # send "user left the chat" message if user didnt reload 
            socketio.emit("chat_message", {
                "sender": "",
                "message": f"{name} has left the chat"
            }, to=room_code)


@socketio.on("message")
def handle_message(data):
    # create timestamp
    dt = datetime.now()
    time_str = dt.strftime("%I:%M:%S %p").lstrip("0")

    room_code = data["room"]
    sender = data["sender"]
    user_id = data["sender_id"]
    content = data["message"]

    # save message in db
    message = Message(
        room_id=room_code,
        sender=sender,
        sender_id=user_id,
        content=content,
        timestamp=time_str
    )
    db.session.add(message)
    db.session.commit()

    # send message to room
    emit("chat_message", {
        "room": room_code,
        "sender": sender,
        "message": content,
        "member_id": str(user_id),
        "timestamp": time_str
    }, to=room_code)

if __name__ == "__main__":
    socketio.run(app)