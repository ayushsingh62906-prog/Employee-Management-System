# ==========================================================
# FILE : routes/exit_routes.py
# PURPOSE : Exit / Resignation Workflow
#           Employee request kare → HR approve/reject kare
# ==========================================================

from datetime import datetime
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, session
)

from db import employees, recruitment   # resignation records recruitment me type se save
from utils.decorators import role_required


# Blueprint - URL /hr/exit se start hoga
exit_bp = Blueprint(
    "exit",
    __name__,
    url_prefix="/hr/exit"
)


# ==========================================================
# HELPER : Current logged-in employee nikalna (email se)
# ==========================================================
def get_current_employee():
    email = session.get("email")
    if not email:
        return None
    return employees.find_one({
        "email": email,
        "is_deleted": {"$ne": True}
    })


# ==========================================================
# ROUTE 1 : HR - Saari resignation requests list
# URL : /hr/exit/
# ==========================================================
@exit_bp.route("/")
@role_required("hr", "admin")
def list_resignations():

    # Filter (Pending default)
    status_filter = request.args.get("status", "Pending")

    query = {"type": "resignation"}
    if status_filter:
        query["status"] = status_filter

    # Latest pehle
    requests_list = list(recruitment.find(query).sort("created_at", -1))

    # Employee details attach
    for req in requests_list:
        emp = employees.find_one({"employee_id": req.get("employee_id")})
        if emp:
            req["full_name"] = emp.get("full_name", "Unknown")
            req["department"] = emp.get("department", "-")
            req["designation"] = emp.get("designation", "-")
        else:
            req["full_name"] = "Unknown"
            req["department"] = "-"
            req["designation"] = "-"

    return render_template(
        "hr/exit/list.html",
        requests_list=requests_list,
        status_filter=status_filter,
        username=session["username"],
        role=session["role"],
    )

# ==========================================================
# ROUTE (NAYA) : Clearance Checkbox Toggle
# (IT / Finance / HR clearance mark/unmark karna)
# URL : /hr/exit/clearance/<req_id>/<clearance_type>
# ==========================================================

@exit_bp.route("/clearance/<req_id>/<clearance_type>", methods=["POST"])
@role_required("hr", "admin")
def toggle_clearance(req_id, clearance_type):

    from bson import ObjectId

    # Sirf ye 3 valid clearance types allow karenge
    valid_types = {
        "it": "it_clearance",
        "finance": "finance_clearance",
        "hr": "hr_clearance",
    }

    if clearance_type not in valid_types:
        flash("Invalid clearance type.", "danger")
        return redirect(url_for("exit.list_resignations"))

    field_name = valid_types[clearance_type]

    try:
        req = recruitment.find_one({"_id": ObjectId(req_id), "type": "resignation"})

        if not req:
            flash("Request not found.", "danger")
            return redirect(url_for("exit.list_resignations"))

        # Current value ka ULTA kar do (True -> False, False -> True)
        current_value = req.get(field_name, False)

        recruitment.update_one(
            {"_id": ObjectId(req_id)},
            {"$set": {field_name: not current_value}}
        )

    except Exception:
        flash("Something went wrong.", "danger")

    return redirect(url_for("exit.list_resignations", status=request.args.get("status", "Pending")))



# ==========================================================
# ROUTE 2 : HR - Approve Resignation
# ==========================================================
@exit_bp.route("/approve/<req_id>", methods=["POST"])
@role_required("hr", "admin")
def approve_resignation(req_id):

    from bson import ObjectId
    req = recruitment.find_one({"_id": ObjectId(req_id), "type": "resignation"})

    if not req:
        flash("Request not found.", "danger")
        return redirect(url_for("exit.list_resignations"))

    if not (req.get("it_clearance") and req.get("finance_clearance") and req.get("hr_clearance")):
        flash("Cannot approve — all 3 clearances (IT, Finance, HR) must be marked complete first.", "warning")
        return redirect(url_for("exit.list_resignations"))
    try:
        req = recruitment.find_one({"_id": ObjectId(req_id), "type": "resignation"})
        if not req:
            flash("Request not found.", "danger")
            return redirect(url_for("exit.list_resignations"))

        # 1. Resignation status update
        recruitment.update_one(
            {"_id": ObjectId(req_id)},
            {"$set": {
                "status": "Approved",
                "approved_by": session.get("username"),
                "action_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }}
        )

        # 2. Employee ko Inactive mark karo
        employees.update_one(
            {"employee_id": req.get("employee_id")},
            {"$set": {
                "status": "Inactive",
                "exit_date": datetime.utcnow().strftime("%Y-%m-%d"),
                "updated_at": datetime.utcnow(),
            }}
        )

        flash("Resignation approved. Employee marked Inactive.", "success")
    except Exception:
        flash("Something went wrong.", "danger")

    return redirect(url_for("exit.list_resignations", status="Pending"))


# ==========================================================
# ROUTE 3 : HR - Reject Resignation
# ==========================================================
@exit_bp.route("/reject/<req_id>", methods=["POST"])
@role_required("hr", "admin")
def reject_resignation(req_id):

    from bson import ObjectId

    reason = request.form.get("reject_reason", "").strip()

    try:
        recruitment.update_one(
            {"_id": ObjectId(req_id), "type": "resignation"},
            {"$set": {
                "status": "Rejected",
                "rejected_by": session.get("username"),
                "reject_reason": reason,
                "action_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }}
        )
        flash("Resignation request rejected.", "success")
    except Exception:
        flash("Something went wrong.", "danger")

    return redirect(url_for("exit.list_resignations", status="Pending"))