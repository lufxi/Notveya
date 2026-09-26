import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "mysql+pymysql://notveya_user:notveya_pass@localhost:3306/notveya"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    _ca_path = os.path.join(basedir, "certs", "aiven-ca.pem")
    if os.environ.get("DATABASE_URL") and os.path.exists(_ca_path):
        SQLALCHEMY_ENGINE_OPTIONS = {
            "connect_args": {"ssl_ca": _ca_path}
        }

    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

    UPLOAD_FOLDER = os.path.join(basedir, "static", "uploads")
    PROFILE_PIC_FOLDER = os.path.join(UPLOAD_FOLDER, "profile_pics")
    MATERIAL_FOLDER = os.path.join(UPLOAD_FOLDER, "materials")

    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH_MB", 200)) * 1024 * 1024

    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    ALLOWED_NOTE_EXTENSIONS = {"pdf", "doc", "docx", "ppt", "pptx", "txt", "png", "jpg", "jpeg"}
    ALLOWED_VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "mkv", "webm"}