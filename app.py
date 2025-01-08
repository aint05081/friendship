from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime

# Flask 앱 초기화
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 비밀번호 보안을 위한 키 (변경 필요)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# 사용자 모델
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    color = db.Column(db.String(20), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)
    comments = db.relationship('Comment', backref='comment_author', lazy=True)

# 게시물 모델
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='post', lazy=True)

# 댓글 모델
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]), lazy=True)

# 메시지 모델
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect('/login')
    posts = Post.query.order_by(Post.date_posted.desc()).all()
    return render_template('home.html', posts=posts, user_id=session['user_id'])

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        color = request.form['color']
        if User.query.filter_by(username=username).first():
            return "Username already exists!"
        new_user = User(username=username, password=password, color=color)
        db.session.add(new_user)
        db.session.commit()
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect('/')
        return "Invalid credentials!"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/login')

@app.route('/create_post', methods=['GET', 'POST'])
def create_post():
    if 'user_id' not in session:
        return redirect('/login')
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        user_id = session['user_id']
        new_post = Post(title=title, content=content, user_id=user_id)
        db.session.add(new_post)
        db.session.commit()
        return redirect('/')
    return render_template('create_post.html')

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'user_id' not in session:
        return redirect('/login')
    if request.method == 'POST':
        content = request.form['content']
        user_id = session['user_id']
        new_message = Message(content=content, user_id=user_id)
        db.session.add(new_message)
        db.session.commit()
    messages = Message.query.order_by(Message.timestamp.asc()).all()
    return render_template('chat.html', messages=messages)

@app.route('/my_page')
def my_page():
    if 'user_id' not in session:
        return redirect('/login')
    user_id = session['user_id']
    user = User.query.get(user_id)
    posts = Post.query.filter_by(user_id=user_id).order_by(Post.date_posted.desc()).all()
    return render_template('my_page.html', user=user, posts=posts)

@app.route('/post/<int:post_id>', methods=['GET', 'POST'])
def view_post(post_id):
    if 'user_id' not in session:
        return redirect('/login')
    post = Post.query.get_or_404(post_id)
    if request.method == 'POST':
        content = request.form['content']
        user_id = session['user_id']
        parent_id = request.form.get('parent_id')
        new_comment = Comment(content=content, post_id=post.id, user_id=user_id, parent_id=parent_id)
        db.session.add(new_comment)
        db.session.commit()
        return redirect(f'/post/{post.id}')
    comments = Comment.query.filter_by(post_id=post_id, parent_id=None).order_by(Comment.date_posted.desc()).all()
    return render_template('view_post.html', post=post, comments=comments)

@app.route('/delete_comment/<int:comment_id>', methods=['POST'])
def delete_comment(comment_id):
    if 'user_id' not in session:
        return redirect('/login')
    comment = Comment.query.get_or_404(comment_id)
    if comment.user_id != session['user_id']:
        return "Unauthorized action!"
    db.session.delete(comment)
    db.session.commit()
    return redirect(f'/post/{comment.post_id}')

@app.route('/edit_comment/<int:comment_id>', methods=['GET', 'POST'])
def edit_comment(comment_id):
    if 'user_id' not in session:
        return redirect('/login')
    comment = Comment.query.get_or_404(comment_id)
    if comment.user_id != session['user_id']:
        return "Unauthorized action!"
    if request.method == 'POST':
        comment.content = request.form['content']
        db.session.commit()
        return redirect(f'/post/{comment.post_id}')
    return render_template('edit_comment.html', comment=comment)

import os

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # 기본 포트를 5000으로 설정
    app.run(host='0.0.0.0', port=port, debug=True)


