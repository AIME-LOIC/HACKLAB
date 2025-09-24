# ...existing code...

# app.py
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os, hashlib
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from models import db, User, Message, Team, CodeShare, Lesson
from models import TeamJoinRequest, TeamMemberRole
app = Flask(__name__)
import uuid



app.secret_key = 'hacklab.com'
app.permanent_session_lifetime = timedelta(days=30)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Always set DB config and initialize SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'hacklab.db'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Only create tables and run server if running locally
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='hacklab.com', port=2000)

UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {'png', 'jpeg', 'jpg', 'gif', 'mp4', 'mp3', 'wav', 'ogg', 'pdf', 'docx', 'pptx', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def hash_pass(p):
    return hashlib.sha1(p.encode()).hexdigest()

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = hash_pass('hacklab@2025')

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form['username']
        password = hash_pass(request.form['password'])
        session.permanent = True

        if uname == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['user'] = ADMIN_USERNAME
            session['is_admin'] = True
            return redirect(url_for('admin'))

        user = User.query.filter_by(username=uname, password=password).first()
        if user:
            if not user.approved:
                return render_template('wait.html')
            session['user'] = user.username
            session['is_admin'] = False
            return redirect(url_for('dashboard'))
        return render_template('wrong.html')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = hash_pass(request.form['password'])
        bio = request.form['bio']

        if User.query.filter_by(username=username).first():
            return render_template('user_taken.html')

        new_user = User(username=username, password=password, bio=bio,
                        approved=False, profile_pic='',
                        joined=datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    if session.get('is_admin'):
        return redirect(url_for('admin'))

    current_user = User.query.filter_by(username=session['user']).first()
    if not current_user:
        session.clear()
        return redirect(url_for('login'))
    # Use same logic as admin: get all users, but only show approved for chat/search
    all_users = User.query.all()
    approved_users = [u for u in all_users if u.approved and u.username != current_user.username]

    query = request.args.get('q', '').strip().lower()
    search_results = [u for u in approved_users if query in u.username.lower()] if query else []

    serialized_users = []
    for u in approved_users:
        serialized_users.append({
            'username': u.username,
            'bio': u.bio,
            'profile_pic': u.profile_pic,
        })

    messages = Message.query.all()
    chat_data = {}
    for msg in messages:
        if msg.sender == current_user.username:
            partner = msg.recipient
        elif msg.recipient == current_user.username:
            partner = msg.sender
        else:
            continue

        msg_dict = {
            'id': msg.id,
            'sender': msg.sender,
            'recipient': msg.recipient,
            'message': msg.message,
            'reply_to': msg.reply_to,
            'media_type': msg.media_type,
            'media_filename': msg.media_filename,
            'timestamp': msg.timestamp
        }

        if partner not in chat_data:
            chat_data[partner] = []
        chat_data[partner].append(msg_dict)

    courses = Lesson.query.order_by(Lesson.created_at.desc()).all()
    return render_template('dashboard.html',
                           user=current_user,
                           users=serialized_users,
                           search_results=search_results,
                           chat_data=chat_data,
                           courses=courses)

@app.route('/admin')
def admin():
    if 'user' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))

    users = User.query.all()
    teams = Team.query.all()
    courses = Lesson.query.order_by(Lesson.created_at.desc()).all()
    return render_template('admin.html', users=users, teams=teams, courses=courses)


# Add route for admin to add a course (with file upload)
@app.route('/add_course', methods=['POST'])
def add_course():
    if 'user' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    title = request.form.get('title')
    content = request.form.get('content')
    file = request.files.get('course_file')
    file_name = None
    file_type = None
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        file_type = ext
        safe_name = secure_filename(f"course_{datetime.now().timestamp()}_{file.filename}")
        file.save(os.path.join(UPLOAD_FOLDER, safe_name))
        file_name = safe_name
    lesson = Lesson(title=title, content=content, file_name=file_name, file_type=file_type)
    db.session.add(lesson)
    db.session.commit()
    return redirect(url_for('admin'))

# Admin: Delete course
@app.route('/delete_course/<int:course_id>', methods=['POST'])
def delete_course(course_id):
    if 'user' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    lesson = Lesson.query.get(course_id)
    if lesson:
        # Optionally delete file from disk
        if lesson.file_name:
            try:
                os.remove(os.path.join(UPLOAD_FOLDER, lesson.file_name))
            except Exception:
                pass
        db.session.delete(lesson)
        db.session.commit()
    return redirect(url_for('admin'))

# Admin: Delete user
@app.route('/delete_user/<username>', methods=['POST'])
def delete_user(username):
    if 'user' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    user = User.query.filter_by(username=username).first()
    if user:
        db.session.delete(user)
        db.session.commit()
    return redirect(url_for('admin'))


@app.route('/approve/<username>')
def approve_user(username):
    if 'user' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    user = User.query.filter_by(username=username).first()
    if user:
        user.approved = True
        db.session.commit()
    return redirect(url_for('admin'))

# Restore send_message route
@app.route('/send_message', methods=['POST'])
def send_message():
    if 'user' not in session:
        return jsonify({'error': 'unauthorized'}), 403

    sender = session['user']
    recipient = request.form['recipient']
    text = request.form.get('message', '')
    reply_to = request.form.get('reply_to')

    media_file = request.files.get('media')
    media_type = 'text'
    media_filename = ''

    if media_file and allowed_file(media_file.filename):
        filename = secure_filename(f"{sender}_{datetime.now().timestamp()}_{media_file.filename}")
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        media_file.save(filepath)
        media_filename = filename

        ext = filename.rsplit('.', 1)[1].lower()
        if ext in ['png', 'jpg', 'jpeg', 'gif']:
            media_type = 'image'
        elif ext == 'mp4':
            media_type = 'video'
        elif ext in ['mp3', 'wav', 'ogg']:
            media_type = 'audio'

    new_msg = Message(
        sender=sender,
        recipient=recipient,
        message=text,
        reply_to=int(reply_to) if reply_to else None,
        media_type=media_type,
        media_filename=media_filename,
        timestamp=datetime.now().strftime('%d-%m-%Y %H:%M:%S')
    )
    db.session.add(new_msg)
    db.session.commit()

    return jsonify({k: getattr(new_msg, k) for k in ['id', 'sender', 'recipient', 'message', 'reply_to', 'media_type', 'media_filename', 'timestamp']})

@app.route('/api/get_messages/<username>')
def get_messages(username):
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 403

    current_user = session['user']
    messages = Message.query.filter(
        ((Message.sender == current_user) & (Message.recipient == username)) |
        ((Message.sender == username) & (Message.recipient == current_user))
    ).all()

    return jsonify([{k: getattr(m, k) for k in ['id', 'sender', 'recipient', 'message', 'reply_to', 'media_type', 'media_filename', 'timestamp']} for m in messages])

@app.route('/create_team', methods=['POST'])
def create_team():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 403

    team_name = request.form.get('team_name')
    if not team_name:
        return jsonify({'error': 'Team name required'}), 400

    current_user = User.query.filter_by(username=session['user']).first()

    invite_code = str(uuid.uuid4())

    team = Team(name=team_name, owner_username=current_user.username, invite_code=invite_code)
    team.members.append(current_user)

    db.session.add(team)
    db.session.commit()

    invite_link = url_for('join_team', invite_code=invite_code, _external=True)

    return jsonify({'message': 'Team created', 'invite_link': invite_link})

@app.route('/join_team/<invite_code>')
def join_team(invite_code):
    if 'user' not in session:
        return redirect(url_for('login'))

    current_user = User.query.filter_by(username=session['user']).first()
    team = Team.query.filter_by(invite_code=invite_code).first()

    if not team:
        return "Invalid invite link", 404

    if current_user not in team.members:
        team.members.append(current_user)
        db.session.commit()

    return redirect(url_for('dashboard'))

@app.route('/send_code_share', methods=['POST'])
def send_code_share():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 403

    sender = session['user']
    recipient = request.form.get('recipient')
    code = request.form.get('code')

    if not recipient or not code:
        return jsonify({'error': 'Recipient and code required'}), 400

    recipient_user = User.query.filter_by(username=recipient).first()
    if not recipient_user:
        return jsonify({'error': 'Recipient user not found'}), 404

    new_share = CodeShare(
        sender_username=sender,
        recipient_username=recipient,
        code=code,
        timestamp=datetime.utcnow()
    )
    db.session.add(new_share)
    db.session.commit()

    return jsonify({'message': 'Code shared successfully'})

@app.route('/api/share_code')
def get_code_shares():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 403

    current_user = session['user']
    shares = CodeShare.query.filter_by(recipient_username=current_user).order_by(CodeShare.timestamp.desc()).all()

    result = [{
        'id': s.id,
        'sender': s.sender_username,
        'code': s.code,
        'timestamp': s.timestamp.strftime('%d-%m-%Y %H:%M:%S')
    } for s in shares]

    return jsonify(result)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/upload_profile_pic', methods=['POST'])
def upload_profile_pic():
    if 'user' not in session or session.get('is_admin'):
        return redirect(url_for('login'))
    file = request.files.get('profile_pic')
    if file and allowed_file(file.filename):
        filename = secure_filename(f"{session['user']}_profile.{file.filename.rsplit('.', 1)[1].lower()}")
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        user = User.query.filter_by(username=session['user']).first()
        user.profile_pic = filename
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('wrong.html'), 400

if __name__ == '__main__':
    app.run(debug=True, host='hacklab.com', port=2000)
