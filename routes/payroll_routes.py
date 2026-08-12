# ==========================================================
# FILE : routes/payroll_routes.py
# PURPOSE : Admin - Payroll Management
#           Generate Salary / View Payslips / 
#           Deductions (Leave + Half Day)
# ==========================================================

from datetime import datetime, date
from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, session
)

from db import salary, employees, attendance, leave_requests
from utils.decorators import role_required


payroll_bp = Blueprint(
    "payroll",
    __name__,
    url_prefix="/admin/payroll"
)


# ==========================================================
# HELPER : Month ke liye working days nikalna (simple)
# ==========================================================

def get_month_days(year, month):
    """Simple: 30 days maan rahe hain (baad me improve kar sakte hain)"""
    return 30


# ==========================================================
# ROUTE 1 : PAYROLL DASHBOARD / LIST
# ==========================================================

@payroll_bp.route("/")
@role_required("admin")
def list_payroll():

    # Filter
    selected_month = request.args.get("month", date.today().strftime("%Y-%m"))

    # Us month ke saare payslips
    payslips = list(salary.find({"month": selected_month}).sort("created_at", -1))

    # Employee details attach
    for slip in payslips:
        emp = employees.find_one({"employee_id": slip.get("employee_id")})
        if emp:
            slip["full_name"] = emp.get("full_name", "Unknown")
            slip["department"] = emp.get("department", "-")
        else:
            slip["full_name"] = "Unknown"
            slip["department"] = "-"

    return render_template(
        "admin/payroll/list.html",
        payslips=payslips,
        selected_month=selected_month,
        username=session["username"],
        role=session["role"],
    )


# ==========================================================
# ROUTE 2 : GENERATE SALARY (for one employee or all)
# ==========================================================

@payroll_bp.route("/generate", methods=["GET", "POST"])
@role_required("admin")
def generate_salary():

    if request.method == "POST":

        employee_id = request.form.get("employee_id", "").strip()
        month = request.form.get("month", date.today().strftime("%Y-%m"))

        if not employee_id:
            flash("Please select an employee.", "danger")
            return redirect(url_for("payroll.generate_salary"))

        emp = employees.find_one({
            "employee_id": employee_id,
            "is_deleted": {"$ne": True}
        })

        if not emp:
            flash("Employee not found.", "danger")
            return redirect(url_for("payroll.generate_salary"))

        # Pehle se is month ka salary generate to nahi hua?
        existing = salary.find_one({
            "employee_id": employee_id,
            "month": month
        })
        if existing:
            flash("Salary already generated for this employee in selected month.", "warning")
            return redirect(url_for("payroll.list_payroll", month=month))

        # -----------------------------
        # Calculations
        # -----------------------------
        monthly_ctc = float(emp.get("salary", 0))          # Monthly CTC
        per_day_salary = monthly_ctc / 30

        # Us month me kitne Absent / Half Day the
        year, mon = month.split("-")
        start_date = f"{month}-01"
        end_date = f"{month}-31"

        # Absent days
        absent_count = attendance.count_documents({
            "employee_id": employee_id,
            "date": {"$gte": start_date, "$lte": end_date},
            "status": "Absent"
        })

        # Half Day
        halfday_count = attendance.count_documents({
            "employee_id": employee_id,
            "date": {"$gte": start_date, "$lte": end_date},
            "status": "Half Day"
        })

        # Approved Unpaid Leave days (simple)
        unpaid_leaves = list(leave_requests.find({
            "employee_id": employee_id,
            "status": "Approved",
            "leave_type": "Unpaid Leave",
            "from_date": {"$gte": start_date},
            "to_date": {"$lte": end_date}
        }))
        unpaid_days = sum(l.get("total_days", 0) for l in unpaid_leaves)

        # Deductions
        absent_deduction = absent_count * per_day_salary
        halfday_deduction = halfday_count * (per_day_salary / 2)
        unpaid_deduction = unpaid_days * per_day_salary

        total_deduction = absent_deduction + halfday_deduction + unpaid_deduction
        net_salary = monthly_ctc - total_deduction

        if net_salary < 0:
            net_salary = 0

        # Save payslip
        salary.insert_one({
            "employee_id": employee_id,
            "month": month,
            "monthly_ctc": monthly_ctc,
            "per_day_salary": round(per_day_salary, 2),
            "absent_days": absent_count,
            "halfday_days": halfday_count,
            "unpaid_leave_days": unpaid_days,
            "absent_deduction": round(absent_deduction, 2),
            "halfday_deduction": round(halfday_deduction, 2),
            "unpaid_deduction": round(unpaid_deduction, 2),
            "total_deduction": round(total_deduction, 2),
            "net_salary": round(net_salary, 2),
            "generated_by": session.get("username"),
            "created_at": datetime.utcnow(),
        })

        flash(f"Salary generated successfully for {emp['full_name']}. Net: ₹{round(net_salary, 2)}", "success")
        return redirect(url_for("payroll.list_payroll", month=month))

    # GET -> form
    employee_list = list(employees.find(
        {"is_deleted": {"$ne": True}},
        {"employee_id": 1, "full_name": 1, "department": 1, "salary": 1}
    ).sort("full_name", 1))

    return render_template(
        "admin/payroll/generate.html",
        employee_list=employee_list,
        current_month=date.today().strftime("%Y-%m"),
        username=session["username"],
        role=session["role"],
    )


# ==========================================================
# ROUTE 3 : VIEW PAYSLIP
# ==========================================================

@payroll_bp.route("/view/<payslip_id>")
@role_required("admin")
def view_payslip(payslip_id):

    from bson import ObjectId

    try:
        slip = salary.find_one({"_id": ObjectId(payslip_id)})
    except:
        flash("Invalid payslip.", "danger")
        return redirect(url_for("payroll.list_payroll"))

    if not slip:
        flash("Payslip not found.", "danger")
        return redirect(url_for("payroll.list_payroll"))

    emp = employees.find_one({"employee_id": slip.get("employee_id")})

    return render_template(
        "admin/payroll/view.html",
        slip=slip,
        employee=emp,
        username=session["username"],
        role=session["role"],
    )