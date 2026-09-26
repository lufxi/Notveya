from functools import wraps

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from extensions import db
from models import Classroom, Enrollment, Material

student_bp = Blueprint("student", __name__)


def student_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_student:
            abort(403)
        return f(*args, **kwargs)
    return wrapped


@student_bp.route("/classroom/join", methods=["GET", "POST"])
@login_required
@student_required
def join_classroom():
    if request.method == "POST":
        code = request.form.get("code", "").strip().upper()
        classroom = Classroom.query.filter_by(code=code).first()

        if not classroom:
            flash("That classroom code doesn't match anything. Double-check it with your teacher.", "error")
            return render_template("join_classroom.html")

        existing = Enrollment.query.filter_by(
            classroom_id=classroom.id, student_id=current_user.id
        ).first()
        if existing:
            flash(f"You're already enrolled in {classroom.name}.", "info")
            return redirect(url_for("student.view_classroom", classroom_id=classroom.id))

        enrollment = Enrollment(classroom_id=classroom.id, student_id=current_user.id)
        db.session.add(enrollment)
        db.session.commit()
        flash(f"You've joined {classroom.name}!", "success")
        return redirect(url_for("student.view_classroom", classroom_id=classroom.id))

    return render_template("join_classroom.html")


@student_bp.route("/classroom/<int:classroom_id>")
@login_required
@student_required
def view_classroom(classroom_id):
    classroom = db.session.get(Classroom, classroom_id) or abort(404)
    enrollment = Enrollment.query.filter_by(
        classroom_id=classroom.id, student_id=current_user.id
    ).first()
    if not enrollment:
        abort(403)

    materials = (
        Material.query.filter_by(classroom_id=classroom.id)
        .order_by(Material.uploaded_at.desc())
        .all()
    )

    my_ratings = {
        r.material_id: r for r in current_user.ratings if r.material.classroom_id == classroom.id
    }

    return render_template(
        "classroom_student.html", classroom=classroom, materials=materials, my_ratings=my_ratings
    )
