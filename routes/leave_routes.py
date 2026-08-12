# ==========================================================
# FILE : routes/leave_routes.py
# PURPOSE : Admin - Leave Management Module
#           Leave Requests List / Approve / Reject /
#           Leave Types / Leave History
# ==========================================================

from datetime import datetime, date
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, session
)

from db import leave_requests, employees
from utils.decorators import role_required


# ==========================================================
# BLUEPRINT SETUP
# ==========================================================

leave_bp = Blueprint(
    "leave",
    __name__,
    url_prefix="/admin/leave"
)


# ==========================================================
# LEAVE TYPES (simple fixed list)
# Baad me database se bhi laa sakte hain
# ==========================================================

LEAVE_TYPES = ["Casual Leave", "Sick Leave", "Earned Leave", "Unpaid Leave", "Maternity Leave", "Paternity Leave"]


# ==========================================================
# ROUTE 1 : LEAVE REQUESTS LIST
# URL : /admin/leave/
# ==========================================================

@leave_bp.route("/")
@role_required("admin")
def list_leave_requests():

    # Filter parameters
    status_filter = request.args.get("status", "Pending")  # default Pending
    leave_type_filter = request.args.get("leave_type", "")

    query = {}

    if status_filter:
        query["status"] = status_filter

    if leave_type_filter:
        query["leave_type"] = leave_type_filter

    # Latest requests pehle
    requests_list = list(leave_requests.find(query).sort("created_at", -1))

    # Har request ke saath employee details attach karna
    for req in requests_list:
        emp = employees.find_one({"employee_id": req.get("employee_id")})
        if emp:
            req["full_name"] = emp.get("full_name", "Unknown")
            req["department"] = emp.get("department", "-")
            req["photo"] = emp.get("photo")
        else:
            req["full_name"] = "Unknown"
            req["department"] = "-"
            req["photo"] = None

    return render_template(
        "admin/leave/list.html",
        requests_list=requests_list,
        status_filter=status_filter,
        leave_type_filter=leave_type_filter,
        leave_types=LEAVE_TYPES,
        username=session["username"],
        role=session["role"],
    )


# ==========================================================
# ROUTE 2 : APPROVE LEAVE
# ==========================================================

@leave_bp.route("/approve/<request_id>", methods=["POST"])
@role_required("admin")
def approve_leave(request_id):

    from bson import ObjectId

    try:
        leave_requests.update_one(
            {"_id": ObjectId(request_id)},
            {"$set": {
                "status": "Approved",
                "approved_by": session.get("username"),
                "action_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }}
        )
        flash("Leave request approved successfully.", "success")
    except Exception:
        flash("Invalid leave request.", "danger")

    return redirect(url_for("leave.list_leave_requests", status="Pending"))


# ==========================================================
# ROUTE 3 : REJECT LEAVE
# ==========================================================

@leave_bp.route("/reject/<request_id>", methods=["POST"])
@role_required("admin")
def reject_leave(request_id):

    from bson import ObjectId

    reason = request.form.get("reject_reason", "").strip()

    try:
        leave_requests.update_one(
            {"_id": ObjectId(request_id)},
            {"$set": {
                "status": "Rejected",
                "rejected_by": session.get("username"),
                "reject_reason": reason,
                "action_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }}
        )
        flash("Leave request rejected.", "success")
    except Exception:
        flash("Invalid leave request.", "danger")

    return redirect(url_for("leave.list_leave_requests", status="Pending"))


# ==========================================================
# ROUTE 4 : VIEW SINGLE LEAVE REQUEST
# ==========================================================

@leave_bp.route("/view/<request_id>")
@role_required("admin")
def view_leave(request_id):

    from bson import ObjectId

    try:
        req = leave_requests.find_one({"_id": ObjectId(request_id)})
    except Exception:
        flash("Invalid leave request.", "danger")
        return redirect(url_for("leave.list_leave_requests"))

    if not req:
        flash("Leave request not found.", "danger")
        return redirect(url_for("leave.list_leave_requests"))

    # Employee details
    emp = employees.find_one({"employee_id": req.get("employee_id")})

    return render_template(
        "admin/leave/view.html",
        leave=req,
        employee=emp,
        username=session["username"],
        role=session["role"],
    )