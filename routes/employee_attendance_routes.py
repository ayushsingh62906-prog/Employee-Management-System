# ==========================================================
# FILE : routes/employee_attendance_routes.py
# PURPOSE : Employee side - Check In / Check Out + 
#           Apni Attendance History dekhna
# ==========================================================

from datetime import datetime, date
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, session
)

from db import attendance, employees
from utils.decorators import role_required


# ==========================================================
# BLUEPRINT
# URL prefix -> /employee/attendance
# ==========================================================

employee_attendance_bp = Blueprint(
    "employee_attendance",
    __name__,
    url_prefix="/employee/attendance"
)


def get_today():
    return date.today().strftime("%Y-%m-%d")


# ==========================================================
# HELPER : Current logged-in employee ka data nikalna
# ==========================================================

def get_current_employee():
    """
    Session me email se employee record nikalte hain.
    Agar nahi milta to None return.
    """
    email = session.get("email").strip().lower()
    if not email:
        return None
    return employees.find_one({
        "email": email,
        "is_deleted": {"$ne": True}
    })


# ==========================================================
# ROUTE 1 : Attendance Dashboard (Check-In / Check-Out)
# URL : /employee/attendance/
# ==========================================================

@employee_attendance_bp.route("/")
@role_required("employee")
def attendance_home():

    emp = get_current_employee()
    if not emp:
        flash("Employee profile not found.", "danger")
        return redirect(url_for("employee_dashboard"))

    today = get_today()

    # Aaj ka attendance record
    today_record = attendance.find_one({
        "employee_id": emp["employee_id"],
        "date": today
    })

    return render_template(
        "employee/attendance/home.html",
        employee=emp,
        today_record=today_record,
        today=today,
        username=session["username"],
        role=session["role"],
    )


# ==========================================================
# ROUTE 2 : CHECK IN
# ==========================================================

@employee_attendance_bp.route("/check-in", methods=["POST"])
@role_required("employee")
def check_in():

    emp = get_current_employee()
    if not emp:
        flash("Employee profile not found.", "danger")
        return redirect(url_for("employee_dashboard"))

    today = get_today()
    now_time = datetime.now().strftime("%H:%M")

    # Pehle se check-in to nahi hua?
    existing = attendance.find_one({
        "employee_id": emp["employee_id"],
        "date": today
    })

    if existing and existing.get("check_in"):
        flash("You have already checked in today.", "warning")
        return redirect(url_for("employee_attendance.attendance_home"))

    if existing:
        # Agar record hai lekin check-in nahi hai to update
        attendance.update_one(
            {"_id": existing["_id"]},
            {"$set": {
                "check_in": now_time,
                "status": "Present",
                "updated_at": datetime.utcnow()
            }}
        )
    else:
        # Naya record
        attendance.insert_one({
            "employee_id": emp["employee_id"],
            "date": today,
            "check_in": now_time,
            "check_out": None,
            "status": "Present",
            "remarks": "Self Check-In",
            "marked_by": emp["full_name"],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })

    flash(f"Checked in successfully at {now_time}", "success")
    return redirect(url_for("employee_attendance.attendance_home"))


# ==========================================================
# ROUTE 3 : CHECK OUT
# ==========================================================

@employee_attendance_bp.route("/check-out", methods=["POST"])
@role_required("employee")
def check_out():

    emp = get_current_employee()
    if not emp:
        flash("Employee profile not found.", "danger")
        return redirect(url_for("employee_dashboard"))

    today = get_today()
    now_time = datetime.now().strftime("%H:%M")

    existing = attendance.find_one({
        "employee_id": emp["employee_id"],
        "date": today
    })

    if not existing or not existing.get("check_in"):
        flash("Please check-in first.", "warning")
        return redirect(url_for("employee_attendance.attendance_home"))

    if existing.get("check_out"):
        flash("You have already checked out today.", "warning")
        return redirect(url_for("employee_attendance.attendance_home"))

    # Check-out update
    attendance.update_one(
        {"_id": existing["_id"]},
        {"$set": {
            "check_out": now_time,
            "updated_at": datetime.utcnow()
        }}
    )

    flash(f"Checked out successfully at {now_time}", "success")
    return redirect(url_for("employee_attendance.attendance_home"))


# ==========================================================
# ROUTE 4 : MY ATTENDANCE HISTORY (Monthly view)
# ==========================================================

@employee_attendance_bp.route("/history")
@role_required("employee")
def attendance_history():

    emp = get_current_employee()
    if not emp:
        flash("Employee profile not found.", "danger")
        return redirect(url_for("employee_dashboard"))

    # Last 60 days ke records
    records = list(attendance.find(
        {"employee_id": emp["employee_id"]}
    ).sort("date", -1).limit(60))

    # Simple stats
    present_count = sum(1 for r in records if r.get("status") in ["Present", "Late", "Half Day"])
    absent_count = sum(1 for r in records if r.get("status") == "Absent")

    return render_template(
        "employee/attendance/history.html",
        employee=emp,
        records=records,
        present_count=present_count,
        absent_count=absent_count,
        username=session["username"],
        role=session["role"],
    )