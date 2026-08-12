# ==========================================================
# FILE : routes/employee_exit_routes.py
# PURPOSE : Employee - Resignation request bhejna + history
# ==========================================================

from datetime import datetime
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, session
)

from db import employees, recruitment
from utils.decorators import role_required


employee_exit_bp = Blueprint(
    "employee_exit",
    __name__,
    url_prefix="/employee/exit"
)


def get_current_employee():
    email = session.get("email")
    if not email:
        return None
    return employees.find_one({
        "email": email,
        "is_deleted": {"$ne": True}
    })


# ==========================================================
# ROUTE : Employee Exit Home (form + apni requests)
# ==========================================================
@employee_exit_bp.route("/", methods=["GET", "POST"])
@role_required("employee")
def exit_home():

    emp = get_current_employee()
    if not emp:
        flash("Employee profile not found.", "danger")
        return redirect(url_for("employee_dashboard"))

    # POST = naya resignation request
    if request.method == "POST":

        reason = request.form.get("reason", "").strip()
        last_working_day = request.form.get("last_working_day", "").strip()

        if not reason or not last_working_day:
            flash("Reason and last working day are required.", "danger")
            return redirect(url_for("employee_exit.exit_home"))

        # Pehle se koi Pending request to nahi?
        existing = recruitment.find_one({
            "type": "resignation",
            "employee_id": emp["employee_id"],
            "status": "Pending"
        })
        if existing:
            flash("You already have a pending resignation request.", "warning")
            return redirect(url_for("employee_exit.exit_home"))

        recruitment.insert_one({
            "type": "resignation",
            "employee_id": emp["employee_id"],
            "reason": reason,
            "last_working_day": last_working_day,
            "status": "Pending",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })

        flash("Resignation request submitted successfully.", "success")
        return redirect(url_for("employee_exit.exit_home"))

    # GET = form + history
    my_requests = list(recruitment.find({
        "type": "resignation",
        "employee_id": emp["employee_id"]
    }).sort("created_at", -1))

    return render_template(
        "employee/exit/home.html",
        employee=emp,
        my_requests=my_requests,
        username=session["username"],
        role=session["role"],
    )