from flask import Flask,render_template,request,redirect,url_for,session,jsonify
import os, json,hashlib
from datetime import datetime,timedelta
from werkzeug.utils import secure_filename
from me.models import db, User, Upload, Team, Lesson, Message


app=Flask(__name__)
app.secret_key='hacklab.com'
app.permanent_session_lifetime=timedelta(days=30)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hacklab.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

@app.before_first_request
def create_tables():
    db.create_all()


upload_folder='static/uploads'
if not os.path.exists(upload_folder):
    os.mkdir(upload_folder)

DB_FILE='base.json'
if not os.path.exists(DB_FILE):
    with open(DB_FILE,'w') as file:
        json.dump({"users":[],"teams":[],"lessons":[],"messages":[]},file)

Allowed_exe={'png','jpeg','jpg','gif','mp4','mp3','wav','ogg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in Allowed_exe

def load_db():
    with open(DB_FILE,'r') as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE,'w') as f:
        json.dump(data,f,indent=4)

def hash_pass(p):
    return hashlib.sha1(p.encode()).hexdigest()

ADMIN_USERNAME= 'admin'
ADMIN_PASSWORD=hash_pass('admin123')

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        uname=request.form['username']
        password=hash_pass(request.form['password'])
        session.permanent=True

        if uname==ADMIN_USERNAME and password==ADMIN_PASSWORD:
            session['user']=ADMIN_USERNAME
            session['is_admin']=True
            return redirect(url_for('admin'))
        
        db=load_db()
        for users in db['users']:
            if users['username']== uname and users['password']== password:
                if not users['approved']:
                    return render_template('wait.html')
                session['user']=uname
                session['is_admin']=False
                return redirect(url_for('dashboard'))
        return render_template('wrong.html')
    return render_template('login.html')

@app.route('/register',methods=['GET','POST'])
def register():
    if request.method=='POST':
       username=request.form['username']
       password=hash_pass(request.form['password'])
       bio=request.form['bio']
       db=load_db()
       if any(u['username']== username for u in db['users']):
           return render_template('user_taken.html')
       db['users'].append({
           'username':username,
           'password':password,
           'bio':bio,
           'approved':False,
           'team':'',
           'uploads':[],
           'profile_pic':'',
           'joined':str(datetime.now().strftime('%d/%m/%Y  %H:%M:%S')),
           'messages':[]
       })
       save_db(db)
       return redirect(url_for('login'))
    return render_template('register.html')
@app.route('/dashboard')
def dashboard():
    if 'user' not in session or session.get('is_admin'):
        return redirect(url_for('login'))
    
    db=load_db()
    username=session['user']
    user=next((u for u in db['users'] if u['username']== username), None)
    if not user:
        return redirect(url_for('login'))
    
    users=[u for u in db['users'] if u['username'] != username]
    query=request.args.get('q','').strip().lower()
    search_results=[]
    if query:
        search_results=[u for u in users if query in u['username'].lower()]

    messages=db.get('messages',[])
    chat_data ={}
    for msg in messages:
        if msg['sender']== username:
            partner=msg['recipient']
        elif msg['recipient']== username:
            partner=msg['sender']
        else:
            continue
        chat_data.setdefault(partner,[]).append(msg)
    return render_template('dashboard.html',
                           user=user,
                           users=users,
                           search_results=search_results,
                           chat_data=chat_data)

@app.route('/admin')
def admin():
    if 'user' not in session or  not session.get('is_admin'):
        return redirect(url_for('login'))
    
    db=load_db()
    return render_template('admin.html', users=db['users'], teams=db['teams'])

@app.route('/approve/<username>')
def approve_user(username):
    if 'user' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    db=load_db()
    for u in db['users']:
        if u['username']==username:
            u['approved']=True
            break
    save_db(db)
    return redirect(url_for('admin'))

@app.route('/upload_profile_pic', methods=['POST'])
def upload_profile_pic():
    if 'user' not in session or session.get('is_admin'):
        return redirect(url_for('login'))
    
    file=request.files.get('profile_pic')
    if file and allowed_file(file.filename):
        filename=secure_filename(f"{session['user']}_profile.{file.filename.rsplit('.',1)[1].lower()}")
        filepath=os.path.join(upload_folder,filename)
        file.save(filepath)

        db=load_db()
        for u in db['users']:
            if u['username']==session['user']:
                u['profile_pic']=filename
                break
        save_db(db)
        return redirect(url_for('dashboard'))
    return render_template('wrong.html'),400

@app.route('/update_bio',methods=['POST'])
def update_bio():
    if 'user' not in session or session.get('is_admin'):
        return redirect(url_for('login'))
    new_bio= request.form['bio']
    db=load_db()
    for u in db['users']:
        if u['username']==session['user']:
            u['bio']=new_bio
            break
    save_db(db)
    return redirect(url_for('dashboard'))

@app.route('/send_message',methods=['POST'])
def send_message():
    if 'user' not in session:
        return jsonify({'error':"unauthorized"}),403
    
    sender=session['user']
    recipient=request.form['recipient']
    text=request.form.get('message','')
    reply_to=request.form.get('reply_to')

    media_file= request.files.get('media')
    media_type='text'
    media_filename=''

    if media_file and allowed_file(media_file.filename):
        filename=secure_filename(f"{sender}_{datetime.now().timestamp()}_{media_file.filename}")
        filepath=os.path.join(upload_folder,filename)
        media_file.save(filepath)
        media_filename=filename

        ext= filename.rsplit('.', 1)[1].lower()
        if ext in ['png','jpg','jpeg','gif']:
            media_type='image'
        elif ext in ['mp4']:
            media_type='video'
        elif ext in ['mp3','wav','ogg']:
            media_type='audio'
    db=load_db()
    timestamp=datetime.now().strftime('%d-%m-%Y %H:%M:%S')

    new_message ={
        'id': len(db.get('messages',[]))+1,
        'sender':sender,
        'recipient':recipient,
        'message':text,
        'reply_to':int(reply_to) if reply_to else None,
        'media_type':media_type,
        'media_filename':media_filename,
        'timestamp':timestamp
    }
    db.setdefault('messages',[]).append(new_message)
    save_db(db)

    return jsonify(new_message)

@app.route('/api/get_messages/<username>')
def get_messages(username):
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 403

    current_user = session['user']
    db = load_db()
    messages = db.get('messages', [])

    filtered = [m for m in messages if (m['sender'] == current_user and m['recipient'] == username) or (m['sender'] == username and m['recipient'] == current_user)]
    return jsonify(filtered)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__=='__main__':
    app.run(debug=True,host='hacklab',port=2000)



