# FlaskChat

FlaskChat is a easy-to-use messaging app using Flask, SocketIO, SQLite and Jinja templates.

## Creating a Room

Enter your name, optionally choose a room code, and click Create.

<p align="center">
  <img src="assets/homepage.png" width="380">
  <img src="assets/create_room.png" width="380">
</p>

After creating the room, you'll receive a unique room code to share.

<p align="center">
  <img src="assets/create_room_2.png" width="500">
</p>

---

## Joining a Room

Another user can join by entering the room code.

<p align="center">
  <img src="assets/join_room.png" width="380">
  <img src="assets/join_room_2.png" width="380">
</p>

## Features include:
- unique user identification using uuid4
- real-time messaging with Flask-SocketIO
- reload-safe sessions
- room auto-cleanup when empty
- server-side message history saved in SQLite
- Minimal UI (Bootstrap based)

