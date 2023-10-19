import time

from deep_translator import GoogleTranslator
from flask import (
    Flask,
    send_from_directory,
    render_template,
    request,
    url_for,
    session,
    flash,
    redirect,
    Blueprint,
    Response,
    jsonify,
)
from flask_login import login_user, LoginManager, UserMixin
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash
from .fixtures import fixtures

from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_object("project.config.Config")
db = SQLAlchemy(app)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)  # primary keys are required by SQLAlchemy
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100), unique=True)
    posts = db.relationship('Post', backref='author', lazy=True)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    body = db.Column(db.String(5000))
    created_on = db.Column(db.DateTime(timezone=True), server_default=func.now())


@app.route("/static/<path:filename>")
def staticfiles(filename):
    return send_from_directory(app.config["STATIC_FOLDER"], filename)


main = Blueprint('main', __name__)


@main.route('/about')
def about():
    return render_template('about.html')


@main.route('/fixtures')
def fixtures_fill():
    for d in fixtures:
        post = Post(title=d['title'], author_id=1, body=d['body'])
        db.session.add(post)
    db.session.commit()
    return Response("Created", status=201, mimetype='application/json')


@main.route('/')
def articles():
    page = request.args.get('page', 1, type=int)
    lang = request.args.get('lang', 'ru', type=str)
    posts = Post.query.order_by(Post.title.desc()).paginate(page=page, per_page=2)
    if lang == 'en':
        blog_translate = GoogleTranslator(source='ru', target='en')
        for post in posts.items:
            post.body = blog_translate.translate(post.body)
            post.title = blog_translate.translate(post.title)
            time.sleep(0.5)
    lang = 'ru' if lang == 'en' else 'en'
    return render_template('main.html', posts=posts, lang=lang)


@main.route('/blog/<blog>')
def article(blog):
    post = Post.query.filter_by(id=blog).first()
    return render_template('post_detail.html', post=post)


auth = Blueprint('auth', __name__)


@auth.route('/login')
def login():
    return render_template('login.html')


@auth.route('/login', methods=['POST'])
def login_post():
    name = request.form.get('name')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False

    user = User.query.filter_by(name=name).first()

    # check if user actually exists
    # take the user supplied password, hash it, and compare it to the hashed password in database
    if not user or not check_password_hash(user.password, password):
        flash('Please check your login details and try again.')
        return redirect(url_for('auth.login'))  # if user doesn't exist or password is wrong, reload the page

    # if the above check passes, then we know the user has the right credentials
    login_user(user, remember=remember)
    return redirect(url_for('main.articles'))


@auth.route('/registration')
def signup():
    return render_template('registration.html')


@auth.route('/registration', methods=['POST'])
def signup_post():
    email = request.form.get('email')
    name = request.form.get('name')
    password = request.form.get('password')
    password2 = request.form.get('password2')

    if password2 != password:
        flash('Пароли не совпадают')
        return redirect(url_for('auth.registration'))

    user = User.query.filter_by(
        name=name
    ).first()  # if this returns a user, then the email already exists in database

    if user:  # if a user is found, we want to redirect back to signup page so user can try again
        flash('Логин уже зарегистрирован')
        return redirect(url_for('auth.registration'))

    # create new user with the form data. Hash the password so plaintext version isn't saved.
    new_user = User(email=email, name=name, password=generate_password_hash(password, method='sha256'))

    # add the new user to the database
    db.session.add(new_user)
    db.session.commit()

    return redirect(url_for('auth.login'))


@app.route("/login_dialog")
def login_dialog():
    hash = generate_password_hash('skillchen')
    check_hash = check_password_hash(hash, 'skillchen')
    return render_template("login_dialog.html", hash=hash, check_hash=check_hash)


@app.route("/login_modal", methods=["POST", "GET"])
def login_modal():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(name=username).first()
        if not user or not check_password_hash(user.password, password):
            msg = 'Не удалось выполнить вход'
        else:
            session['logged_in'] = True
            session['username'] = username
            msg = 'Вход выполнен'
    return jsonify(msg)


@app.route("/registration_modal", methods=["POST"])
def registration_modal():
    msg = ''
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        password2 = request.form['password2']
        if password2 != password:
            return jsonify(msg)

        user = User.query.filter_by(name=username).first()
        user2 = User.query.filter_by(email=email).first()
        if user:
            msg = 'Логин уже зарегистрирован'
        elif user2:
            msg = 'Почта уже зарегистрирована'
        else:
            new_user = User(
                email=email, name=username, password=generate_password_hash(password, method='sha256')
            )
            db.session.add(new_user)
            db.session.commit()
            session['logged_in'] = True
            session['username'] = username
            msg = 'Регистрация и вход выполнены'

    return jsonify(msg)


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login_dialog')


login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    # since the user_id is just the primary key of our user table, use it in the query for the user
    return User.query.get(int(user_id))

    # blueprint for auth routes in our app


app.register_blueprint(auth)
app.register_blueprint(main)
