from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db, oauth
from models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        role = request.form.get("role", "")

        if not name or not email or not password:
            flash("Please fill in every field.", "error")
            return render_template("register.html")
        if role not in ("teacher", "student"):
            flash("Please choose whether you're a teacher or a student.", "error")
            return render_template("register.html")
        if password != confirm:
            flash("Passwords don't match.", "error")
            return render_template("register.html")
        if len(password) < 6:
            flash("Password should be at least 6 characters.", "error")
            return render_template("register.html")

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("An account with that email already exists. Try logging in.", "error")
            return render_template("register.html")

        user = User(name=name, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash(f"Welcome to Notveya, {user.name.split()[0]}!", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash(f"Welcome back, {user.name.split()[0]}.", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("main.dashboard"))

        flash("Incorrect email or password.", "error")

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You've been logged out.", "info")
    return redirect(url_for("main.index"))


@auth_bp.route("/google/login")
def google_login():
    # Where a fresh Google sign-up should default the role to, if we need to ask.
    session["pending_role"] = request.args.get("role", "student")
    redirect_uri = url_for("auth.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route("/google/callback")
def google_callback():
    try:
        token = oauth.google.authorize_access_token()
    except Exception:
        flash("Google sign-in was cancelled or failed. Please try again.", "error")
        return redirect(url_for("auth.login"))

    userinfo = token.get("userinfo")
    if not userinfo:
        flash("Couldn't read your Google profile. Please try again.", "error")
        return redirect(url_for("auth.login"))

    google_id = userinfo.get("sub")
    email = userinfo.get("email", "").lower()
    name = userinfo.get("name", email.split("@")[0] if email else "New user")

    user = User.query.filter_by(google_id=google_id).first()
    if not user:
        user = User.query.filter_by(email=email).first()

    if user:
        if not user.google_id:
            user.google_id = google_id
            db.session.commit()
        login_user(user)
        flash(f"Welcome back, {user.name.split()[0]}.", "success")
        return redirect(url_for("main.dashboard"))

    # Brand new account via Google - role was chosen on the landing page button.
    role = session.pop("pending_role", "student")
    if role not in ("teacher", "student"):
        role = "student"

    user = User(name=name, email=email, role=role, google_id=google_id)
    db.session.add(user)
    db.session.commit()
    login_user(user)
    flash(f"Welcome to Notveya, {user.name.split()[0]}!", "success")
    return redirect(url_for("main.dashboard"))
