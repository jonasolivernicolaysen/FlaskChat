from flask import Flask, render_template, redirect, url_for, request, session
from flask_socketio import SocketIO, join_room, leave_room, emit
import random, string
from db import db, Room, Members, Message


app = Flask(__name__)
app.config["SECRET_KEY"] = "secretkey"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///chat.db"

socketio = SocketIO(app)
db.init_app(app)

with app.app_context():
    db.drop_all()
    db.create_all()

def gen_code(length: int, existing_codes: list[str]) -> str:
    while True:        
        code_chars = [random.choice(string.ascii_letters) for _ in range(length)]
        room_code = "".join(code_chars)
        if room_code not in existing_codes:
            return room_code

# TODO Build routes

@app.route("/", methods=["GET", "POST"])
def home():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name-input")
        code = request.form.get("room-code")
        create = request.form.get("createchatroombutton", False)
        join = request.form.get("joinchatroombutton", False)

        print("Name:", name)
        print("Code:", type(code), len(code))
        print("Create button clicked:", create)
        print("Join button clicked:", join)

        if not name:
            return render_template("home.html", error="Name is required")
        
        if create == "true":
            if code and code.strip():
                room_code = code
            else:
                room_code = gen_code(6, [room.id for room in Room.query.all()])
            
            new_room = Room(id=room_code, member_count=0)
            
            member_id = gen_code(6, [member.id for member in Members.query.all()])
            room_member = Members(id=member_id, room_id=room_code, member_name=name)
            
            db.session.add(room_member)
            db.session.add(new_room)
            db.session.commit()
            session["room"] = room_code
            session["name"] = name
            return redirect(url_for("room"))
        
        elif join == "true":
            if not code:
                return render_template("home.html", error="You must enter a room code to join a room", name=name)
            room = db.session.get(Room, code)
            if not room:
                return render_template("home.html", error="Invalid room code", name=name)
            session["room"] = code
            session["name"] = name
            return redirect(url_for("room"))
    return render_template("home.html")


@app.route("/room")
def room():
    room_code = session.get("room")
    name = session.get("name")

    if not name or not room_code:
        return redirect(url_for("home"))
    
    room = db.session.get(Room, room_code)
    if not room:
        return redirect(url_for("home"))

    messages = Message.query.filter_by(room_id=room_code).all()
    serialized_messages = [{"message": m.content, "sender": m.sender} for m in messages]
    
    return render_template("room.html", room=room, user=name, messages=serialized_messages)


# handlers for session events which socket io automatically detects
@socketio.on("connect")
def handle_connect():
    room_code = request.args.get("room")
    name = request.args.get("name")
    if not room_code or not name:
        return
    
    

    session["room"] = room_code
    session["name"] = name
    join_room(room_code)

    

    room = db.session.get(Room, room_code)
    if room:
        room.member_count += 1
        db.session.commit()

        messages = room.messages
        # to=request.sid ensures that only the joining user gets the history 
        for msg in messages:
            emit("chat_message", {"sender": msg.sender, "message": msg.content}, to=request.sid)


@socketio.on("disconnect")
def handle_disconnect():
    room_code = session.get("room")
    name = session.get("name")
    if not room_code or not name:
        return
    
    leave_room(room_code)
    room = db.session.get(Room, room_code)

    if room:
        room.member_count -= 1
        if room.member_count <= 0:
            db.session.delete(room)
        db.session.commit()

    message = {
        "sender": "",
        "message": f"{name} has left the chat"
    }
    emit("chat_message", message, to=room_code)


@socketio.on("message")
def handle_message(data):
    room_code = data["room"]
    sender = data["sender"]
    content = data["message"]

    # save the message to the db
    message = Message(room_id=room_code, sender=sender, content=content)
    db.session.add(message)
    db.session.commit()

    message = {
        "room": room_code,
        "sender": sender,
        "message": data["message"]
    }
    emit("chat_message", message, to=room_code)

if __name__ == "__main__":
    socketio.run(app)