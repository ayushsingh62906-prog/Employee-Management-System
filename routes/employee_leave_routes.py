# ==========================================================
# FILE : routes/employee_leave_routes.py
# PURPOSE : Employee - Leave Apply + Apni Leave History
# ==========================================================

from datetime import datetime, date
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, session
)

from db import leave_requests, employees
from utils.decorators import role_required


employee_leave_bp = Blueprint(
    "employee_leave",
    __name__,
    url_prefix="/employee/leave"
)

LEAVE_TYPES = ["Casual Leave", "Sick Leave", "Earned Leave", "Unpaid Leave"]


def get_current_employee():
    email = session.get("email").strip().lower()
    if not email:
        return None
    return employees.find_one({"email": email, "is_deleted": {"$ne": True}})


# ==========================================================
# ROUTE 1 : Leave Home (Apply + History)
# ==========================================================

@employee_leave_bp.route("/")
@role_required("employee")
def leave_home():

    emp = get_current_employee()
    if not emp:
        flash("Employee profile not found.", "danger")
        return redirect(url_for("employee_dashboard"))

    # Apni saari leave requests
    my_leaves = list(leave_requests.find(
        {"employee_id": emp["employee_id"]}
    ).sort("created_at", -1))

    return render_template(
        "employee/leave/home.html",
        employee=emp,
        my_leaves=my_leaves,
        leave_types=LEAVE_TYPES,
        username=session["username"],
        role=session["role"],
    )


# ==========================================================
# ROUTE 2 : Apply Leave
# ==========================================================

@employee_leave_bp.route("/apply", methods=["POST"])
@role_required("employee")
def apply_leave():

    emp = get_current_employee()
    if not emp:
        flash("Employee profile not found.", "danger")
        return redirect(url_for("employee_dashboard"))

    leave_type = request.form.get("leave_type", "")
    from_date = request.form.get("from_date", "")
    to_date = request.form.get("to_date", "")
    reason = request.form.get("reason", "").strip()

    if not leave_type or not from_date or not to_date:
        flash("Please fill all required fields.", "danger")
        return redirect(url_for("employee_leave.leave_home"))

    # Simple days calculation
    try:
        d1 = datetime.strptime(from_date, "%Y-%m-%d")
        d2 = datetime.strptime(to_date, "%Y-%m-%d")
        total_days = (d2 - d1).days + 1
        if total_days < 1:
            flash("To Date must be after From Date.", "danger")
            return redirect(url_for("employee_leave.leave_home"))
    except:
        flash("Invalid dates.", "danger")
        return redirect(url_for("employee_leave.leave_home"))

    leave_requests.insert_one({
        "employee_id": emp["employee_id"],
        "leave_type": leave_type,
        "from_date": from_date,
        "to_date": to_date,
        "total_days": total_days,
        "reason": reason,
        "status": "Pending",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    })

    flash("Leave request submitted successfully.", "success")
    return redirect(url_for("employee_leave.leave_home"))