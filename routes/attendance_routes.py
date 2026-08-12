# ==========================================================
# FILE : routes/attendance_routes.py
# PURPOSE : Admin - Attendance Management Module
#           Daily Attendance List / Mark Attendance /
#           Search & Filter / View Employee Attendance /
#           Late Entries / Soft Delete (optional)
# ==========================================================

from datetime import datetime, date, timedelta
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, session
)

# db.py se collections import
from db import attendance, employees, departments

# Role based access control
from utils.decorators import role_required


# ==========================================================
# BLUEPRINT SETUP
# URL prefix -> /admin/attendance
# ==========================================================

attendance_bp = Blueprint(
    "attendance",
    __name__,
    url_prefix="/admin/attendance"
)


# ==========================================================
# HELPER FUNCTION : Aaj ki date string me return karta hai
# Format : YYYY-MM-DD
# ==========================================================

def get_today():
    return date.today().strftime("%Y-%m-%d")


# ==========================================================
# ROUTE 1 : DAILY ATTENDANCE LIST
# URL : GET /admin/attendance/
# Filter by date, department, status
# ==========================================================

@attendance_bp.route("/")
@role_required("admin")
def list_attendance():

    # -----------------------------
    # Query parameters nikalna
    # -----------------------------
    selected_date = request.args.get("date", get_today())
    department_filter = request.args.get("department", "")
    status_filter = request.args.get("status", "")

    # -----------------------------
    # MongoDB query banana
    # -----------------------------
    query = {"date": selected_date}

    if status_filter:
        query["status"] = status_filter

    # Agar department filter hai to pehle us department ke employees nikalenge
    if department_filter:
        emp_ids = [
            emp["employee_id"]
            for emp in employees.find(
                {"department": department_filter, "is_deleted": {"$ne": True}},
                {"employee_id": 1}
            )
        ]
        query["employee_id"] = {"$in": emp_ids}

    # Final attendance records
    attendance_list = list(attendance.find(query).sort("check_in", 1))

    # Har record ke saath employee details bhi attach kar rahe hain
    for record in attendance_list:
        emp = employees.find_one({"employee_id": record.get("employee_id")})
        if emp:
            record["full_name"] = emp.get("full_name", "-")
            record["department"] = emp.get("department", "-")
            record["designation"] = emp.get("designation", "-")
            record["photo"] = emp.get("photo")
        else:
            record["full_name"] = "Unknown"
            record["department"] = "-"
            record["designation"] = "-"
            record["photo"] = None

    # Department dropdown ke liye list
    departments_list = employees.distinct("department", {"is_deleted": {"$ne": True}})
    departments_list = [d for d in departments_list if d]

    return render_template(
        "admin/attendance/list.html",
        attendance_list=attendance_list,
        selected_date=selected_date,
        department_filter=department_filter,
        status_filter=status_filter,
        departments_list=departments_list,
        username=session["username"],
        role=session["role"],
    )


# ==========================================================
# ROUTE 2 : MARK ATTENDANCE (Admin manually mark kare)
# URL : GET + POST /admin/attendance/mark
# ==========================================================

@attendance_bp.route("/mark", methods=["GET", "POST"])
@role_required("admin")
def mark_attendance():

    if request.method == "POST":

        employee_id = request.form.get("employee_id", "").strip()
        att_date = request.form.get("date", get_today())
        status = request.form.get("status", "Present")
        check_in = request.form.get("check_in", "")
        check_out = request.form.get("check_out", "")
        remarks = request.form.get("remarks", "").strip()

        # Validation
        if not employee_id:
            flash("Please select an employee.", "danger")
            return redirect(url_for("attendance.mark_attendance"))

        # Employee exist karta hai ya nahi
        emp = employees.find_one({
            "employee_id": employee_id,
            "is_deleted": {"$ne": True}
        })
        if not emp:
            flash("Employee not found.", "danger")
            return redirect(url_for("attendance.mark_attendance"))

        # Same date pe already attendance hai to update kar denge, nahi to insert
        existing = attendance.find_one({
            "employee_id": employee_id,
            "date": att_date
        })

        data = {
            "employee_id": employee_id,
            "date": att_date,
            "status": status,
            "check_in": check_in if check_in else None,
            "check_out": check_out if check_out else None,
            "remarks": remarks,
            "marked_by": session.get("username"),
            "updated_at": datetime.utcnow(),
        }

        if existing:
            # Update existing record
            attendance.update_one(
                {"_id": existing["_id"]},
                {"$set": data}
            )
            flash(f"Attendance updated for {emp['full_name']}.", "success")
        else:
            # Naya record insert
            data["created_at"] = datetime.utcnow()
            attendance.insert_one(data)
            flash(f"Attendance marked for {emp['full_name']}.", "success")

        return redirect(url_for("attendance.list_attendance", date=att_date))

    # GET request -> form dikhana
    # Active employees ki list
    employee_list = list(employees.find(
        {"is_deleted": {"$ne": True}},
        {"employee_id": 1, "full_name": 1, "department": 1}
    ).sort("full_name", 1))

    return render_template(
        "admin/attendance/mark.html",
        employee_list=employee_list,
        today=get_today(),
        username=session["username"],
        role=session["role"],
    )


# ==========================================================
# ROUTE 3 : VIEW SINGLE EMPLOYEE ATTENDANCE HISTORY
# URL : /admin/attendance/employee/<employee_id>
# ==========================================================

@attendance_bp.route("/employee/<employee_id>")
@role_required("admin")
def employee_attendance(employee_id):

    # Employee details
    emp = employees.find_one({"employee_id": employee_id})
    if not emp:
        flash("Employee not found.", "danger")
        return redirect(url_for("attendance.list_attendance"))

    # Us employee ke saare attendance records (latest pehle)
    records = list(attendance.find(
        {"employee_id": employee_id}
    ).sort("date", -1).limit(60))   # last 60 days

    return render_template(
        "admin/attendance/employee_history.html",
        employee=emp,
        records=records,
        username=session["username"],
        role=session["role"],
    )


# ==========================================================
# ROUTE 4 : DELETE ATTENDANCE RECORD (Soft style - actual delete)
# ==========================================================

@attendance_bp.route("/delete/<record_id>", methods=["POST"])
@role_required("admin")
def delete_attendance(record_id):

    from bson import ObjectId

    try:
        attendance.delete_one({"_id": ObjectId(record_id)})
        flash("Attendance record deleted.", "success")
    except Exception:
        flash("Invalid record.", "danger")

    # Wapas usi date pe bhej do
    return redirect(request.referrer or url_for("attendance.list_attendance"))