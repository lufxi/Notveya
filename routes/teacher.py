import os
import uuid
from functools import wraps

from flask import (
    Blueprint, render_template, redirect, url_for, flash, request,
    abort, current_app
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from extensions import db
from models import Classroom, Enrollment, Material, User

teacher_bp = Blueprint("teacher", __name__)


def teacher_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_teacher:
            abort(403)
        return f(*args, **kwargs)
    return wrapped


def _get_owned_classroom(classroom_id):
    classroom = db.session.get(Classroom, classroom_id) or abort(404)
    if classroom.teacher_id != current_user.id:
        abort(403)
    return classroom


@teacher_bp.route("/classroom/create", methods=["GET", "POST"])
@login_required
@teacher_required
def create_classroom():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        subject = request.form.get("subject", "").strip()
        description = request.form.get("description", "").strip()

        if not name:
            flash("Give your classroom a name.", "error")
            return render_template("create_classroom.html")

        classroom = Classroom(
            name=name, subject=subject, description=description, teacher_id=current_user.id
        )
        db.session.add(classroom)
        db.session.commit()
        flash(f'"{classroom.name}" is live. Share code {classroom.code} with your students.', "success")
        return redirect(url_for("teacher.view_classroom", classroom_id=classroom.id))

    return render_template("create_classroom.html")


@teacher_bp.route("/classroom/<int:classroom_id>")
@login_required
@teacher_required
def view_classroom(classroom_id):
    classroom = _get_owned_classroom(classroom_id)
    materials = (
        Material.query.filter_by(classroom_id=classroom.id)
        .order_by(Material.uploaded_at.desc())
        .all()
    )
    students = [e.student for e in classroom.enrollments]
    return render_template(
        "classroom_teacher.html", classroom=classroom, materials=materials, students=students
    )


@teacher_bp.route("/classroom/<int:classroom_id>/add_student", methods=["POST"])
@login_required
@teacher_required
def add_student(classroom_id):
    classroom = _get_owned_classroom(classroom_id)
    email = request.form.get("email", "").strip().lower()

    student = User.query.filter_by(email=email, role="student").first()
    if not student:
        flash(f"No student account found for {email}. Ask them to sign up first.", "error")
        return redirect(url_for("teacher.view_classroom", classroom_id=classroom.id))

    existing = Enrollment.query.filter_by(
        classroom_id=classroom.id, student_id=student.id
    ).first()
    if existing:
        flash(f"{student.name} is already in this classroom.", "info")
        return redirect(url_for("teacher.view_classroom", classroom_id=classroom.id))

    enrollment = Enrollment(classroom_id=classroom.id, student_id=student.id)
    db.session.add(enrollment)
    db.session.commit()
    flash(f"{student.name} has been added to {classroom.name}.", "success")
    return redirect(url_for("teacher.view_classroom", classroom_id=classroom.id))


@teacher_bp.route("/classroom/<int:classroom_id>/remove_student/<int:student_id>", methods=["POST"])
@login_required
@teacher_required
def remove_student(classroom_id, student_id):
    classroom = _get_owned_classroom(classroom_id)
    enrollment = Enrollment.query.filter_by(
        classroom_id=classroom.id, student_id=student_id
    ).first_or_404()
    db.session.delete(enrollment)
    db.session.commit()
    flash("Student removed from classroom.", "info")
    return redirect(url_for("teacher.view_classroom", classroom_id=classroom.id))


def _file_type_for(filename, config):
    ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
    if ext in config["ALLOWED_VIDEO_EXTENSIONS"]:
        return "video"
    if ext in config["ALLOWED_NOTE_EXTENSIONS"]:
        return "note"
    return None


@teacher_bp.route("/classroom/<int:classroom_id>/upload", methods=["POST"])
@login_required
@teacher_required
def upload_material(classroom_id):
    classroom = _get_owned_classroom(classroom_id)

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    file = request.files.get("file")

    if not title or not file or not file.filename:
        flash("Give the material a title and choose a file to upload.", "error")
        return redirect(url_for("teacher.view_classroom", classroom_id=classroom.id))

    file_type = _file_type_for(file.filename, current_app.config)
    if not file_type:
        flash("That file type isn't supported. Upload a document, image or video file.", "error")
        return redirect(url_for("teacher.view_classroom", classroom_id=classroom.id))

    original_filename = secure_filename(file.filename)
    ext = original_filename.rsplit(".", 1)[1].lower()
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(current_app.config["MATERIAL_FOLDER"], stored_name))

    material = Material(
        classroom_id=classroom.id,
        uploader_id=current_user.id,
        title=title,
        description=description,
        file_path=stored_name,
        file_type=file_type,
        original_filename=original_filename,
    )
    db.session.add(material)
    db.session.commit()
    flash(f'"{title}" has been uploaded to {classroom.name}.', "success")
    return redirect(url_for("teacher.view_classroom", classroom_id=classroom.id))


@teacher_bp.route("/material/<int:material_id>/delete", methods=["POST"])
@login_required
@teacher_required
def delete_material(material_id):
    material = db.session.get(Material, material_id) or abort(404)
    classroom = material.classroom
    if classroom.teacher_id != current_user.id:
        abort(403)

    file_path = os.path.join(current_app.config["MATERIAL_FOLDER"], material.file_path)
    if os.path.exists(file_path):
        os.remove(file_path)

    db.session.delete(material)
    db.session.commit()
    flash("Material removed.", "info")
    return redirect(url_for("teacher.view_classroom", classroom_id=classroom.id))
