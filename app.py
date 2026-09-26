import os
from flask import Flask
from config import Config
from extensions import db, login_manager, oauth


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(app.config["PROFILE_PIC_FOLDER"], exist_ok=True)
    os.makedirs(app.config["MATERIAL_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    oauth.init_app(app)
    oauth.register(
        name="google",
        client_id=app.config["GOOGLE_CLIENT_ID"],
        client_secret=app.config["GOOGLE_CLIENT_SECRET"],
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from routes.main import main_bp
    from routes.auth import auth_bp
    from routes.teacher import teacher_bp
    from routes.student import student_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(teacher_bp, url_prefix="/teacher")
    app.register_blueprint(student_bp, url_prefix="/student")

    @app.template_filter("timeago")
    def timeago(dt):
        from datetime import datetime
        if dt is None:
            return ""
        diff = datetime.utcnow() - dt
        seconds = diff.total_seconds()
        if seconds < 60:
            return "just now"
        minutes = seconds / 60
        if minutes < 60:
            return f"{int(minutes)}m ago"
        hours = minutes / 60
        if hours < 24:
            return f"{int(hours)}h ago"
        days = hours / 24
        if days < 30:
            return f"{int(days)}d ago"
        return dt.strftime("%b %d, %Y")

    from flask import render_template

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("403.html"), 403

    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
