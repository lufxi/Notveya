import random
import string
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db


def generate_classroom_code(length=7):
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(190), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)  # null if google-only signup
    role = db.Column(db.String(20), nullable=False)  # 'teacher' or 'student'

    google_id = db.Column(db.String(190), unique=True, nullable=True)
    profile_pic = db.Column(db.String(255), nullable=False, default="default.png")
    bio = db.Column(db.String(300), nullable=True, default="")
    institution = db.Column(db.String(150), nullable=True, default="")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Teacher side: classrooms they own
    classrooms = db.relationship(
        "Classroom", backref="teacher", lazy=True, foreign_keys="Classroom.teacher_id"
    )
    # Student side: classrooms they've joined
    enrollments = db.relationship("Enrollment", backref="student", lazy=True)
    ratings = db.relationship("Rating", backref="student", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    @property
    def is_teacher(self):
        return self.role == "teacher"

    @property
    def is_student(self):
        return self.role == "student"

    @property
    def initials(self):
        parts = self.name.strip().split()
        if not parts:
            return "?"
        if len(parts) == 1:
            return parts[0][0].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class Classroom(db.Model):
    __tablename__ = "classrooms"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(100), nullable=True, default="")
    description = db.Column(db.String(400), nullable=True, default="")
    code = db.Column(db.String(10), unique=True, nullable=False, default=generate_classroom_code)

    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    materials = db.relationship(
        "Material", backref="classroom", lazy=True, cascade="all, delete-orphan"
    )
    enrollments = db.relationship(
        "Enrollment", backref="classroom", lazy=True, cascade="all, delete-orphan"
    )

    @property
    def student_count(self):
        return len(self.enrollments)


class Enrollment(db.Model):
    __tablename__ = "enrollments"
    __table_args__ = (db.UniqueConstraint("classroom_id", "student_id", name="uq_class_student"),)

    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey("classrooms.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)


class Material(db.Model):
    __tablename__ = "materials"

    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey("classrooms.id"), nullable=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(400), nullable=True, default="")
    file_path = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)  # 'note' or 'video'
    original_filename = db.Column(db.String(255), nullable=False)

    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    download_count = db.Column(db.Integer, default=0)

    ratings = db.relationship(
        "Rating", backref="material", lazy=True, cascade="all, delete-orphan"
    )

    @property
    def average_rating(self):
        if not self.ratings:
            return 0
        return round(sum(r.stars for r in self.ratings) / len(self.ratings), 1)

    @property
    def rating_count(self):
        return len(self.ratings)


class Rating(db.Model):
    __tablename__ = "ratings"
    __table_args__ = (db.UniqueConstraint("material_id", "student_id", name="uq_material_student"),)

    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey("materials.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    stars = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.String(300), nullable=True, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
