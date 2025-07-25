from flask_sqlalchemy import SQLAlchemy
import uuid
from sqlalchemy.dialects.postgresql import UUID

db = SQLAlchemy()


class Room(db.Model):
    id = db.Column(db.String(10), primary_key=True)
    member_count = db.Column(db.Integer, default=0)
    messages = db.relationship("Message", backref="room", lazy=True)    

    def __repr__(self):
        return self.id


class Member(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    room_id = db.Column(db.String(10), db.ForeignKey("room.id"))
    name = db.Column(db.String(50))


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.String(10), db.ForeignKey("room.id"))
    sender = db.Column(db.String(50))
    sender_id = db.Column(db.String(36))
    content = db.Column(db.Text)
    timestamp = db.Column(db.String(50))

    def __repr__(self):
        return f"<Message from {self.sender}: {self.content}>"
