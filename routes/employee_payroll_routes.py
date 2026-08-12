# ==========================================================
# FILE : routes/employee_payroll_routes.py
# PURPOSE : Employee - Apne khud ke Payslips dekhna
# ==========================================================

from flask import (
    Blueprint, render_template, redirect,
    url_for, flash, session
)

from db import salary, employees
from utils.decorators import role_required


employee_payroll_bp = Blueprint(
    "employee_payroll",
    __name__,
    url_prefix="/employee/payroll"
)


def get_current_employee():
    email = session.get("email")
    if not email:
        return None
    return employees.find_one({"email": email, "is_deleted": {"$ne": True}})


# ==========================================================
# ROUTE 1 : APNI SAARI PAYSLIPS KI LIST
# URL : /employee/payroll/
# ==========================================================

@employee_payroll_bp.route("/")
@role_required("employee")
def list_payslips():

    emp = get_current_employee()

    if not emp:
        flash("Employee profile not found.", "danger")
        return redirect(url_for("employee_dashboard"))

    # Sirf isi employee ki payslips, naye se purane order mein
    my_payslips = list(salary.find(
        {"employee_id": emp["employee_id"]}
    ).sort("month", -1))

    return render_template(
        "employee/payroll/list.html",
        employee=emp,
        payslips=my_payslips,
        username=session["username"],
        role=session["role"],
    )


# ==========================================================
# ROUTE 2 : EK PAYSLIP KA DETAIL VIEW
# URL : /employee/payroll/view/<payslip_id>
# ==========================================================

@employee_payroll_bp.route("/view/<payslip_id>")
@role_required("employee")
def view_payslip(payslip_id):

    from bson import ObjectId

    emp = get_current_employee()

    if not emp:
        flash("Employee profile not found.", "danger")
        return redirect(url_for("employee_dashboard"))

    try:
        slip = salary.find_one({"_id": ObjectId(payslip_id)})
    except Exception:
        flash("Invalid payslip.", "danger")
        return redirect(url_for("employee_payroll.list_payslips"))

    if not slip:
        flash("Payslip not found.", "danger")
        return redirect(url_for("employee_payroll.list_payslips"))

    # ==========================================================
    # SECURITY CHECK - SABSE IMPORTANT LINE
    #
    # Bina ye check kiye, koi bhi logged-in employee URL mein
    # payslip_id badal-badal ke KISI AUR employee ki salary
    # slip dekh sakta tha (Insecure Direct Object Reference -
    # "IDOR" bug kehte hain isko).
    #
    # Isliye confirm kar rahe hain ki ye payslip usi employee
    # ki hai jo abhi login hai, warna access deny.
    # ==========================================================
    if slip.get("employee_id") != emp.get("employee_id"):
        flash("You are not authorized to view this payslip.", "danger")
        return redirect(url_for("employee_payroll.list_payslips"))

    return render_template(
        "employee/payroll/view.html",
        slip=slip,
        employee=emp,
        username=session["username"],
        role=session["role"],
    )