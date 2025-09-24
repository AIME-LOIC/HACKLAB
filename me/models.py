# Team join request model for Discord-like workflow
  # owner, staff, member
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# Association table for many-to-many relationship between users and teams
class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    invite_code = db.Column(db.String(36), unique=True, nullable=False)
    owner_username = db.Column(db.String(100), db.ForeignKey('user.username'))
    members = db.relationship('User', secondary='team_members', back_populates='teams')

team_members = db.Table('team_members',
    db.Column('team_id', db.Integer, db.ForeignKey('team.id'), primary_key=True),
    db.Column('user_username', db.String(100), db.ForeignKey('user.username'), primary_key=True)
)



class CodeShare(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_username = db.Column(db.String(100), db.ForeignKey('user.username'), nullable=False)
    recipient_username = db.Column(db.String(100), db.ForeignKey('user.username'), nullable=False)
    code = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class User(db.Model):
    username = db.Column(db.String(100), primary_key=True)
    password = db.Column(db.String(200), nullable=False)
    bio = db.Column(db.Text)
    approved = db.Column(db.Boolean, default=False)
    profile_pic = db.Column(db.String(200))
    joined = db.Column(db.String(50))

    # Relationships
    uploads = db.relationship('Upload', backref='user', lazy=True)
    messages_sent = db.relationship('Message', foreign_keys='Message.sender', backref='sender_user', lazy=True)
    messages_received = db.relationship('Message', foreign_keys='Message.recipient', backref='recipient_user', lazy=True)
    teams = db.relationship('Team', secondary=team_members, back_populates='members')
    code_shares_sent = db.relationship('CodeShare', foreign_keys='CodeShare.sender_username', backref='sender', lazy=True)
    code_shares_received = db.relationship('CodeShare', foreign_keys='CodeShare.recipient_username', backref='recipient', lazy=True)

class Upload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    user_username = db.Column(db.String(100), db.ForeignKey('user.username'), nullable=False)



class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    file_name = db.Column(db.String(200))  # For uploaded file (pdf/docx/etc)
    file_type = db.Column(db.String(20))   # pdf, docx, etc
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


class TeamJoinRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_username = db.Column(db.String(100), db.ForeignKey('user.username'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, denied
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Add team role support (owner, staff, member)
class TeamMemberRole(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_username = db.Column(db.String(100), db.ForeignKey('user.username'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    role = db.Column(db.String(20), default='member')