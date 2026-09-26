import os
from flask import (
    Blueprint, render_template, redirect, url_for, flash, request,
    send_from_directory, abort, current_app
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from extensions import db
from models import User, Classroom, Enrollment, Material, Rating

main_bp = Blueprint("main", __name__)


def allowed_file(filename, allowed_set):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_set


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.is_teacher:
        classrooms = (
            Classroom.query.filter_by(teacher_id=current_user.id)
            .order_by(Classroom.created_at.desc())
            .all()
        )
        return render_template("dashboard_teacher.html", classrooms=classrooms)
    else:
        enrollments = (
            Enrollment.query.filter_by(student_id=current_user.id)
            .join(Classroom)
            .order_by(Classroom.created_at.desc())
            .all()
        )
        classrooms = [e.classroom for e in enrollments]
        return render_template("dashboard_student.html", classrooms=classrooms)


@main_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        bio = request.form.get("bio", "").strip()
        institution = request.form.get("institution", "").strip()

        if name:
            current_user.name = name
        current_user.bio = bio[:300]
        current_user.institution = institution[:150]

        file = request.files.get("profile_pic")
        if file and file.filename:
            if allowed_file(file.filename, current_app.config["ALLOWED_IMAGE_EXTENSIONS"]):
                filename = secure_filename(f"user{current_user.id}_{file.filename}")
                path = os.path.join(current_app.config["PROFILE_PIC_FOLDER"], filename)
                file.save(path)
                current_user.profile_pic = filename
            else:
                flash("Profile picture must be a PNG, JPG, GIF or WEBP file.", "error")
                return redirect(url_for("main.profile"))

        db.session.commit()
        flash("Your profile has been updated.", "success")
        return redirect(url_for("main.profile"))

    return render_template("profile.html")


@main_bp.route("/uploads/profile_pics/<filename>")
def profile_pic_file(filename):
    return send_from_directory(current_app.config["PROFILE_PIC_FOLDER"], filename)


def _can_access_material(material):
    classroom = material.classroom
    if current_user.is_teacher:
        return classroom.teacher_id == current_user.id
    return Enrollment.query.filter_by(
        classroom_id=classroom.id, student_id=current_user.id
    ).first() is not None


@main_bp.route("/material/<int:material_id>/download")
@login_required
def download_material(material_id):
    material = db.session.get(Material, material_id) or abort(404)
    if not _can_access_material(material):
        abort(403)
    material.download_count = (material.download_count or 0) + 1
    db.session.commit()
    return send_from_directory(
        current_app.config["MATERIAL_FOLDER"],
        material.file_path,
        as_attachment=True,
        download_name=material.original_filename,
    )


@main_bp.route("/material/<int:material_id>/rate", methods=["POST"])
@login_required
def rate_material(material_id):
    material = db.session.get(Material, material_id) or abort(404)
    classroom = material.classroom

    if not current_user.is_student:
        flash("Only students can rate materials.", "error")
        return redirect(url_for("main.dashboard"))

    if not _can_access_material(material):
        abort(403)

    try:
        stars = int(request.form.get("stars", 0))
    except ValueError:
        stars = 0
    if stars < 1 or stars > 5:
        flash("Please choose a rating between 1 and 5 stars.", "error")
        return redirect(url_for("student.view_classroom", classroom_id=classroom.id))

    comment = request.form.get("comment", "").strip()[:300]

    rating = Rating.query.filter_by(material_id=material.id, student_id=current_user.id).first()
    if rating:
        rating.stars = stars
        rating.comment = comment
    else:
        rating = Rating(
            material_id=material.id, student_id=current_user.id, stars=stars, comment=comment
        )
        db.session.add(rating)

    db.session.commit()
    flash("Thanks for rating this material!", "success")
    return redirect(url_for("student.view_classroom", classroom_id=classroom.id))
