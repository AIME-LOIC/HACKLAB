# models.py

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    username = db.Column(db.String(100), primary_key=True)
    password = db.Column(db.String(200), nullable=False)
    bio = db.Column(db.Text)
    approved = db.Column(db.Boolean, default=False)
    team = db.Column(db.String(100))
    profile_pic = db.Column(db.String(200))
    joined = db.Column(db.String(50))
    
    uploads = db.relationship('Upload', backref='user', lazy=True)
    messages_sent = db.relationship('Message', foreign_keys='Message.sender', backref='sender_user', lazy=True)
    messages_received = db.relationship('Message', foreign_keys='Message.recipient', backref='recipient_user', lazy=True)


class Upload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    user_username = db.Column(db.String(100), db.ForeignKey('user.username'), nullable=False)


class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    members = db.Column(db.Text)  # You can improve this by normalizing it later


class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(100), db.ForeignKey('user.username'), nullable=False)
    recipient = db.Column(db.String(100), db.ForeignKey('user.username'), nullable=False)
    message = db.Column(db.Text)
    reply_to = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=True)
    media_type = db.Column(db.String(50), default='text')
    media_filename = db.Column(db.String(200), default='')
    timestamp = db.Column(db.String(50), default=datetime.utcnow().strftime('%d-%m-%Y %H:%M:%S'))
