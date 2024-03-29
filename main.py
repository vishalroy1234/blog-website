from flask import Flask, render_template, redirect, url_for, flash, abort, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date, datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from functools import wraps
import os

year = datetime.now().strftime("%Y")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get(
    'SECRET_KEY', '8BYkEfBA6O6donzWlSihBXox7C0sKR6b')
ckeditor = CKEditor(app)
Bootstrap(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)


gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'sqlite:///blog.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# CONFIGURE TABLES


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    name = db.Column(db.String(250), nullable=False)
    posts = db.relationship('BlogPost', backref='user', lazy=True)
    comments = db.relationship('Comment', backref='user', lazy=True)


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(250), nullable=False)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = db.relationship('Comment', backref='blogpost', lazy=True)


class Comment(db.Model):
    __tablename__ = 'comments'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    blogpost_id = db.Column(db.Integer, db.ForeignKey(
        'blog_posts.id'), nullable=False)
    id = db.Column(db.Integer, primary_key=True)
    comment = db.Column(db.Text, nullable=False)


db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, year=year)


@app.route('/register', methods=['GET', 'POST'])
def register():
    register_form = RegisterForm()
    if register_form.validate_on_submit():
        if User.query.filter_by(email=register_form.email.data).first():
            flash(
                'This email already exists in our database.Please login to access your account')
            return redirect('login')
        new_user = User(
            name=register_form.name.data,
            email=register_form.email.data,
            password=generate_password_hash(
                register_form.password.data, method="pbkdf2:sha256", salt_length=8)
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Your credentials have been saved. Please login to access your account')
        return redirect('login')
    return render_template("register.html", form=register_form, year=year)


@app.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm()
    if login_form.validate_on_submit():
        user = User.query.filter_by(email=login_form.email.data).first()
        if not user:
            flash(
                'We did not find this email in our database. Please register to create your private account')
            return redirect(url_for('register'))
        if user:
            if not check_password_hash(user.password, login_form.password.data):
                flash(
                    'You have entered an incorrect password.Please login with your correct credentials')
                return redirect(url_for('login'))
            else:
                login_user(user)
                return redirect(url_for('get_all_posts'))
    return render_template("login.html", form=login_form, year=year)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
def show_post(post_id):
    form = CommentForm()
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash('Please login to comment on our posts')
            return redirect(url_for('login'))
        else:
            comment = Comment(
                user_id=current_user.id,
                comment=form.comment.data,
                blogpost_id=post_id
            )
            db.session.add(comment)
            db.session.commit()
            print(comment.user.name)
            print(comment.blogpost.title)
            print(comment.user.email)
            return redirect(url_for('show_post', post_id=post_id))
    requested_post = BlogPost.query.get(post_id)
    return render_template("post.html", post=requested_post, form=form, year=year)


@app.route("/about")
def about():
    return render_template("about.html", year=year)


@app.route("/contact", methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        flash('We have received your message :)')
        return redirect(url_for('get_all_posts'))
    return render_template("contact.html", year=year)


# Create admin-only decorator
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If id is not 1 then return abort with 403 error
        if current_user.id != 1:
            return abort(403)
        # Otherwise continue with the route function
        return f(*args, **kwargs)
    return decorated_function


@app.route("/new-post", methods=['GET', 'POST'])
@login_required
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user.name,
            date=date.today().strftime("%B %d, %Y"),
            user_id=current_user.id
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, year=year)


@app.route("/edit-post/<int:post_id>", methods=['GET', 'POST'])
@login_required
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user.name
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, year=year)


@app.route("/delete/<int:post_id>")
@login_required
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
